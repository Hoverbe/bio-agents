from __future__ import annotations

import asyncio
import base64
import io
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional

from openai import OpenAI

from backend.src.agents.bio_agent import BioAgent

VOICE_AGENT_PROMPT = """
你是一名实时语音 Agent，优先响应速度，不做任务规划和深度思考。

要求：
- 默认使用中文回答；除非用户明确要求其他语言。
- 回答要短、直接、适合朗读。
- 可使用 RAG 内部知识库和基础工具。
- 需要工具时只调用一次最必要的工具，不展开复杂计划。
- 如果用户打断或补充，以最新输入为准。
- 不输出 Markdown 表格和长列表。

当前日期：{current_date}
用户问题：{query}
对话历史：{conversation_history}
内部知识库：
{context}

可用工具：
{tools}
"""


@dataclass
class VoiceTurn:
    id: int
    state: str = "listening"
    transcript: str = ""
    answer: str = ""
    played_text: str = ""
    unplayed_text: str = ""
    cancelled: bool = False
    started_at: float = field(default_factory=time.time)


@dataclass
class WarmSession:
    history: str = "无"
    tools: str = "暂无可用工具"
    warmed_at: float = field(default_factory=time.time)


class VoiceAgent:
    """面向实时语音交互的轻量 Agent。"""

    def __init__(self, bio_agent: BioAgent):
        self.bio_agent = bio_agent
        self.audio_client = OpenAI(
            api_key=os.getenv("AUDIO_API_KEY"),
            base_url=os.getenv("AUDIO_BASE_URL"),
            timeout=float(os.getenv("AUDIO_TIMEOUT", "30")),
        )
        self.audio_model = os.getenv("AUDIO_MODEL_ID")
        self.asr_model = os.getenv("AUDIO_ASR_MODEL_ID") or "FunAudioLLM/SenseVoiceSmall"
        self.tts_model = os.getenv("AUDIO_TTS_MODEL_ID") or "FunAudioLLM/CosyVoice2-0.5B"
        self.tts_voice = os.getenv("AUDIO_TTS_VOICE") or f"{self.tts_model}:alex"
        self.tts_format = os.getenv("AUDIO_TTS_FORMAT", "mp3")
        self.tts_sample_rate = int(os.getenv("AUDIO_TTS_SAMPLE_RATE", "32000"))
        self.tts_speed = float(os.getenv("AUDIO_TTS_SPEED", "1"))
        self.turns: Dict[str, VoiceTurn] = {}
        self.sessions: Dict[str, WarmSession] = {}
        self._turn_counter = 0

    def prewarm(self, session_id: str, history: Optional[List[Dict[str, str]]] = None) -> WarmSession:
        tools = "暂无可用工具"
        if getattr(self.bio_agent.automation_agent, "tool_registry", None):
            tools = self.bio_agent.automation_agent.tool_registry.get_tools_description()
        warm = WarmSession(
            history=self.bio_agent._format_history(history or []) or "无",
            tools=tools,
        )
        self.sessions[session_id] = warm
        return warm

    def start_turn(self, session_id: str) -> VoiceTurn:
        self.cancel(session_id)
        self._turn_counter += 1
        turn = VoiceTurn(id=self._turn_counter, state="listening")
        self.turns[session_id] = turn
        return turn

    def cancel(self, session_id: str) -> Optional[VoiceTurn]:
        turn = self.turns.get(session_id)
        if turn:
            turn.cancelled = True
            turn.state = "interrupted"
            turn.unplayed_text = turn.answer[len(turn.played_text):]
        return turn

    def mark_played(self, session_id: str, text: str) -> None:
        turn = self.turns.get(session_id)
        if turn and text:
            turn.played_text += text
            turn.unplayed_text = turn.answer[len(turn.played_text):]

    async def transcribe(self, audio_bytes: bytes, filename: str = "utterance.webm") -> str:
        def _call() -> str:
            with io.BytesIO(audio_bytes) as audio_file:
                audio_file.name = filename
                result = self.audio_client.audio.transcriptions.create(
                    model=self.asr_model,
                    file=audio_file,
                )
                return result if isinstance(result, str) else getattr(result, "text", "")

        return (await asyncio.to_thread(_call)).strip()

    async def prepare_prompt(self, session_id: str, query: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        warm = self.sessions.get(session_id) or self.prewarm(session_id, history)

        def _build_context() -> str:
            rag_config = self.bio_agent.admin_config.get("rag", {})
            if not rag_config.get("enabled", True):
                return ""
            return self.bio_agent.rag_service.build_context(
                query=query,
                namespace=rag_config.get("namespace", "default"),
                top_k=int(rag_config.get("top_k", 3)),
                max_chars=1800,
            )

        context = await asyncio.to_thread(_build_context)
        return VOICE_AGENT_PROMPT.format(
            current_date=time.strftime("%Y-%m-%d"),
            query=query,
            conversation_history=warm.history,
            context=context or "未检索到相关内部知识库内容",
            tools=warm.tools,
        )

    async def stream_reply(self, session_id: str, query: str, prompt_task: asyncio.Task[str]) -> AsyncIterator[str]:
        turn = self.turns[session_id]
        turn.state = "thinking"
        self.bio_agent.automation_agent.system_prompt = await prompt_task

        for chunk in self.bio_agent.automation_agent.stream_run(query, max_tool_iterations=2, temperature=0.3):
            if turn.cancelled:
                return
            turn.answer += chunk
            yield chunk

    async def synthesize(self, text: str) -> bytes:
        if not text.strip():
            return b""

        def _call() -> bytes:
            response = self.audio_client.audio.speech.create(
                model=self.tts_model,
                voice=self.tts_voice,
                input=text,
                response_format=self.tts_format,
                speed=self.tts_speed,
                extra_body={"stream": True, "sample_rate": self.tts_sample_rate},
            )
            return response.read()

        return await asyncio.to_thread(_call)

    async def tts_event(self, text: str, turn_id: int) -> Dict[str, Any]:
        audio = await self.synthesize(text)
        if not audio:
            return {
                "type": "error",
                "detail": "TTS 未返回音频数据",
                "recoverable": True,
                "turn_id": turn_id,
            }
        return {
            "type": "tts_chunk",
            "text": text,
            "audio": base64.b64encode(audio).decode("ascii"),
            "format": self.tts_format,
            "audio_bytes": len(audio),
            "turn_id": turn_id,
        }

    @staticmethod
    def split_speakable(buffer: str) -> tuple[list[str], str]:
        sentences: list[str] = []
        while True:
            match = re.search(r"[。！？!?；;\n]", buffer)
            if not match:
                break
            end = match.end()
            sentence = buffer[:end].strip()
            buffer = buffer[end:]
            if sentence:
                sentences.append(sentence)
        if len(buffer) >= 24:
            sentences.append(buffer.strip())
            buffer = ""
        return sentences, buffer

    @staticmethod
    def stable_prefix(text: str) -> str:
        text = re.sub(r"\s+", "", text or "")
        return text[: min(len(text), 18)]

    @staticmethod
    def is_noise_transcript(text: str) -> bool:
        normalized = re.sub(r"[\s\W_]+", "", text or "").lower()
        if not normalized:
            return True
        noise_words = {
            "hallo", "hello", "hi", "hey", "test", "testing", "嗯", "啊", "喂", "呃", "额", "哦",
            "thankyou", "thanks", "字幕", "音乐", "拜拜", "再见", "哈哈"
        }
        if normalized in noise_words:
            return True
        has_cjk = bool(re.search(r"[\u4e00-\u9fff]", normalized))
        if len(normalized) <= 2 and not has_cjk:
            return True
        return False

    @staticmethod
    def likely_slow_tool(query: str) -> bool:
        return bool(re.search(r"查询|检索|搜索|数据库|计算|执行|调用|工具|文档|文件|分析", query or ""))

    async def drain_ready_tts(self, tasks: list[asyncio.Task[Dict[str, Any]]]) -> AsyncIterator[Dict[str, Any]]:
        while tasks and tasks[0].done():
            yield await tasks.pop(0)

    async def handle_utterance(
        self,
        session_id: str,
        audio_b64: str,
        history: Optional[List[Dict[str, str]]] = None,
        filename: str = "utterance.webm",
    ) -> AsyncIterator[Dict[str, Any]]:
        self.prewarm(session_id, history)
        turn = self.start_turn(session_id)
        yield {"type": "state", "state": "listening", "turn_id": turn.id}

        audio_bytes = base64.b64decode(audio_b64)
        transcript = await self.transcribe(audio_bytes, filename=filename)
        if turn.cancelled:
            return
        turn.transcript = transcript
        if self.is_noise_transcript(transcript):
            yield {"type": "asr_ignored", "text": transcript, "turn_id": turn.id}
            yield {"type": "state", "state": "listening", "turn_id": turn.id}
            return

        prefix = self.stable_prefix(transcript)
        yield {"type": "asr_prefix", "text": prefix, "turn_id": turn.id}
        yield {"type": "intent_preview", "text": prefix, "turn_id": turn.id}
        yield {"type": "asr_final", "text": transcript, "turn_id": turn.id}

        prompt_task = asyncio.create_task(self.prepare_prompt(session_id, transcript, history))
        tts_tasks: list[asyncio.Task[Dict[str, Any]]] = []
        if self.likely_slow_tool(transcript):
            transition = "我先查一下，马上回复。"
            yield {"type": "llm_chunk", "text": transition, "turn_id": turn.id, "transitional": True}
            tts_tasks.append(asyncio.create_task(self.tts_event(transition, turn.id)))

        yield {"type": "state", "state": "thinking", "turn_id": turn.id}
        text_buffer = ""
        async for chunk in self.stream_reply(session_id, transcript, prompt_task):
            if turn.cancelled:
                return
            yield {"type": "llm_chunk", "text": chunk, "turn_id": turn.id}
            text_buffer += chunk
            sentences, text_buffer = self.split_speakable(text_buffer)
            for sentence in sentences:
                turn.state = "speaking"
                yield {"type": "state", "state": "speaking", "turn_id": turn.id}
                tts_tasks.append(asyncio.create_task(self.tts_event(sentence, turn.id)))
            async for event in self.drain_ready_tts(tts_tasks):
                if turn.cancelled:
                    return
                yield event

        if text_buffer.strip() and not turn.cancelled:
            sentence = text_buffer.strip()
            turn.state = "speaking"
            yield {"type": "state", "state": "speaking", "turn_id": turn.id}
            tts_tasks.append(asyncio.create_task(self.tts_event(sentence, turn.id)))

        while tts_tasks and not turn.cancelled:
            yield await tts_tasks.pop(0)

        turn.state = "listening"
        yield {
            "type": "done",
            "turn_id": turn.id,
            "played_text": turn.played_text,
            "unplayed_text": turn.unplayed_text,
        }
