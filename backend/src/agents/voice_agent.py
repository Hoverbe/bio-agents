from __future__ import annotations

import asyncio
import base64
import io
import os
import re
import tempfile
import time
import wave
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from gradio_client import Client, handle_file

from backend.src.agents.bio_agent import BioAgent

VOICE_AGENT_PROMPT = """
你是专门服务于一阳生生物科技公司的内部员工Agent，你需要优先响应速度，不做任务规划和深度思考。

要求：
- 默认使用中文回答；除非用户明确要求其他语言。
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
        audio_host = os.getenv("LOCAL_AUDIO_HOST", "localhost")
        self.asr_base_url = os.getenv("LOCAL_ASR_BASE_URL", f"http://{audio_host}:8005").rstrip("/")
        self.tts_base_url = os.getenv("LOCAL_TTS_BASE_URL", f"http://{audio_host}:8006").rstrip("/")
        self.asr_language = os.getenv("LOCAL_AUDIO_ASR_LANGUAGE", "Auto")
        self.tts_format = "wav"
        self.asr_client = Client(self.asr_base_url)
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
            suffix = Path(filename or "utterance.webm").suffix or ".webm"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            try:
                result = self.asr_client.predict(
                    audio_upload=handle_file(tmp_path),
                    lang_disp=self.asr_language,
                    api_name="/run",
                )
                if isinstance(result, (list, tuple)):
                    if len(result) >= 2:
                        return str(result[1] or "")
                    if len(result) == 1:
                        return str(result[0] or "")
                    return ""
                return str(result or "")
            finally:
                Path(tmp_path).unlink(missing_ok=True)

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

    @staticmethod
    def pcm_to_wav(pcm_audio: bytes, sample_rate: int = 24000) -> bytes:
        if not pcm_audio:
            return b""
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_audio)
        return wav_buffer.getvalue()

    async def synthesize(self, text: str) -> bytes:
        if not text.strip():
            return b""

        def _call() -> bytes:
            payload = urlencode({"tts_text": text}).encode("utf-8")
            request = Request(
                f"{self.tts_base_url}/inference_zero_shot",
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with urlopen(request, timeout=60) as response:
                pcm_audio = response.read()
            return self.pcm_to_wav(pcm_audio)

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
