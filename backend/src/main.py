"""FastAPI entrypoint exposing the Bio-Agent via HTTP."""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, Iterator, Optional, List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field
from agents.bio_agent import BioAgent
from admin_config import delete_item, load_config, save_config, upsert_item
from backend.src.agents.voice_agent import VoiceAgent
from backend.src.mysql_store import MySQLStore

logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <4}</level> | <cyan>using_function:{function}</cyan> | <cyan>{file}:{line}</cyan> | <level>{message}</level>",
    colorize=True,
)


logger.add(
    sink=sys.stderr,
    level="ERROR",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <4}</level> | <cyan>using_function:{function}</cyan> | <cyan>{file}:{line}</cyan> | <level>{message}</level>",
    colorize=True,
)


class ChatRequest(BaseModel):
    """Payload for sending a chat message."""

    username: str = Field(..., description="Username of the user")
    message: str = Field(..., description="Message content")


class ChatResponse(BaseModel):
    """HTTP response for chat messages."""

    response: str = Field(..., description="Agent response")


class TaskItem(BaseModel):
    """Individual task item in the task list."""

    id: int = Field(..., description="Task ID")
    step: int = Field(..., description="Step number")
    agent: str = Field(..., description="Agent name")
    task_description: str = Field(..., description="Task description")
    status: str = Field(default="pending", description="Task status: pending, in_progress, completed, error")
    result: Optional[str] = Field(default=None, description="Task result/summary")
    dependency: Optional[int] = Field(default=None, description="Dependency step ID")


class ResearchRequest(BaseModel):
    """Payload for triggering a research run."""

    username: str = Field(..., description="Username of the user")
    topic: str = Field(..., description="Research topic supplied by the user")
    history: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Conversation history as a list of {'role': ..., 'content': ...}"
    )


class RAGTextRequest(BaseModel):
    """Payload for adding text to the RAG knowledge base."""

    text: str = Field(..., description="Text content to index")
    source: str = Field(default="text", description="Source label")
    namespace: str = Field(default="default", description="RAG namespace")


class RAGFileRequest(BaseModel):
    """Payload for adding a local file to the RAG knowledge base."""

    file_path: str = Field(..., description="Local file path to index")
    namespace: str = Field(default="default", description="RAG namespace")


class RAGSearchRequest(BaseModel):
    """Payload for searching the RAG knowledge base."""

    query: str = Field(..., description="Search query")
    namespace: str = Field(default="default", description="RAG namespace")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results")


class MCPConfigRequest(BaseModel):
    name: str
    description: str = ""
    server_command: List[str] | str = Field(default_factory=list)
    server_args: List[str] | str = Field(default_factory=list)
    env: Dict[str, str] | str = Field(default_factory=dict)
    enabled: bool = True


class ToolConfigRequest(BaseModel):
    name: str
    description: str = ""
    type: str = "builtin"
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)


class SkillConfigRequest(BaseModel):
    name: str
    description: str = ""
    body: str = ""
    enabled: bool = True


class RAGConfigRequest(BaseModel):
    namespace: str = "default"
    top_k: int = Field(default=5, ge=1, le=50)
    chunk_size: int = Field(default=900, ge=100, le=10000)
    chunk_overlap: int = Field(default=120, ge=0, le=5000)
    enabled: bool = True


class ResearchResponse(BaseModel):
    """HTTP response containing the generated report and structured tasks."""

    report_markdown: str = Field(
        ..., description="Markdown-formatted research report including sections"
    )
    todo_items: list[TaskItem] = Field(
        default_factory=list,
        description="Structured TODO items with summaries and sources",
    )


def create_app() -> FastAPI:
    app = FastAPI(title="Bio-Agent - 一阳生生物科技智能助手")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def log_startup_configuration() -> None:
        logger.info("Bio-Agent service started successfully")
        # 启动时初始化 BioAgent 单例，避免每次请求重复注册工具
        app.state.mysql_store = MySQLStore()
        app.state.bio_agent = BioAgent()
        app.state.voice_agent = VoiceAgent(app.state.bio_agent)
        logger.info("Bio-Agent 单例初始化完成")

    @app.get("/healthz")
    def health_check() -> Dict[str, str]:
        return {"status": "ok"}

    def reload_agent_config() -> None:
        if hasattr(app.state, "bio_agent"):
            app.state.bio_agent.reload_admin_config()

    def parse_lines(value: List[str] | str) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [line.strip() for line in value.splitlines() if line.strip()]

    def parse_env(value: Dict[str, str] | str) -> Dict[str, str]:
        if isinstance(value, dict):
            return {str(key): str(val) for key, val in value.items()}
        env: Dict[str, str] = {}
        for line in value.splitlines():
            if "=" in line:
                key, val = line.split("=", 1)
                env[key.strip()] = val.strip()
        return env

    @app.get("/admin/config")
    def get_admin_config() -> Dict[str, Any]:
        config = load_config()
        tools = []
        registry = getattr(app.state.bio_agent.automation_agent, "tool_registry", None)
        if registry:
            tools = [
                {"name": name, "description": getattr(tool, "description", ""), "enabled": True}
                for name, tool in registry.tools.items()
            ]
        return {
            "mcp": app.state.bio_agent.list_mcp_services(),
            "tools": tools,
            "mcp_config": config.get("mcp", []),
            "tool_config": config.get("tools", []),
            "skills": config.get("skills", []),
            "rag": app.state.bio_agent.get_rag_stats(),
            "rag_config": config.get("rag", {}),
        }

    @app.post("/admin/mcp")
    def save_mcp_config(payload: MCPConfigRequest) -> Dict[str, Any]:
        try:
            upsert_item("mcp", {
                "name": payload.name,
                "description": payload.description,
                "server_command": parse_lines(payload.server_command),
                "server_args": parse_lines(payload.server_args),
                "env": parse_env(payload.env),
                "enabled": payload.enabled,
            })
            reload_agent_config()
            return {"ok": True}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.delete("/admin/mcp/{name}")
    def delete_mcp_config(name: str) -> Dict[str, Any]:
        delete_item("mcp", name)
        reload_agent_config()
        return {"ok": True}

    @app.post("/admin/tools")
    def save_tool_config(payload: ToolConfigRequest) -> Dict[str, Any]:
        try:
            upsert_item("tools", payload.model_dump())
            reload_agent_config()
            return {"ok": True}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.delete("/admin/tools/{name}")
    def delete_tool_config(name: str) -> Dict[str, Any]:
        delete_item("tools", name)
        reload_agent_config()
        return {"ok": True}

    @app.post("/admin/skills")
    def save_skill_config(payload: SkillConfigRequest) -> Dict[str, Any]:
        try:
            upsert_item("skills", payload.model_dump())
            return {"ok": True}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.delete("/admin/skills/{name}")
    def delete_skill_config(name: str) -> Dict[str, Any]:
        delete_item("skills", name)
        return {"ok": True}

    @app.post("/admin/rag")
    def save_rag_config(payload: RAGConfigRequest) -> Dict[str, Any]:
        config = load_config()
        config["rag"] = payload.model_dump()
        save_config(config)
        reload_agent_config()
        return {"ok": True}

    @app.get("/admin/rag/documents")
    def list_rag_documents(namespace: str = "default") -> Dict[str, Any]:
        try:
            return {"documents": app.state.bio_agent.list_rag_documents(namespace=namespace)}
        except Exception as exc:
            logger.exception("RAG document list failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/admin/rag/upload")
    def upload_rag_document(file: UploadFile = File(...), namespace: str = Form("default")) -> Dict[str, Any]:
        try:
            chunks = app.state.bio_agent.add_rag_upload(file=file, namespace=namespace)
            return {"indexed_chunks": chunks, "namespace": namespace}
        except Exception as exc:
            logger.exception("RAG upload indexing failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/admin/rag/documents/start")
    def start_rag_document(source: str = Form(...), namespace: str = Form("default")) -> Dict[str, Any]:
        try:
            updated = app.state.bio_agent.set_rag_document_status(source=source, namespace=namespace, status="active")
            return {"updated_chunks": updated, "status": "active"}
        except Exception as exc:
            logger.exception("RAG document start failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/admin/rag/documents/stop")
    def stop_rag_document(source: str = Form(...), namespace: str = Form("default")) -> Dict[str, Any]:
        try:
            updated = app.state.bio_agent.set_rag_document_status(source=source, namespace=namespace, status="inactive")
            return {"updated_chunks": updated, "status": "inactive"}
        except Exception as exc:
            logger.exception("RAG document stop failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.delete("/admin/rag/documents")
    def delete_rag_document(source: str, namespace: str = "default") -> Dict[str, Any]:
        try:
            deleted = app.state.bio_agent.delete_rag_document(source=source, namespace=namespace)
            return {"deleted_chunks": deleted}
        except Exception as exc:
            logger.exception("RAG document delete failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/chat", response_model=ChatResponse)
    def chat(payload: ChatRequest) -> ChatResponse:
        try:
            response = app.state.bio_agent.run(payload.message)
            app.state.mysql_store.save_conversation(
                username=payload.username,
                request_text=payload.message,
                response_text=response,
                conversation_type="chat",
            )
            return ChatResponse(response=response)
        except Exception as exc:
            logger.exception("Chat failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/rag/text")
    def add_rag_text(payload: RAGTextRequest) -> Dict[str, Any]:
        try:
            chunks = app.state.bio_agent.add_rag_text(
                text=payload.text,
                source=payload.source,
                namespace=payload.namespace,
            )
            return {"indexed_chunks": chunks, "namespace": payload.namespace}
        except Exception as exc:
            logger.exception("RAG text indexing failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/rag/file")
    def add_rag_file(payload: RAGFileRequest) -> Dict[str, Any]:
        try:
            chunks = app.state.bio_agent.add_rag_file(
                file_path=payload.file_path,
                namespace=payload.namespace,
            )
            return {"indexed_chunks": chunks, "namespace": payload.namespace}
        except Exception as exc:
            logger.exception("RAG file indexing failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/rag/search")
    def search_rag(payload: RAGSearchRequest) -> Dict[str, Any]:
        try:
            results = app.state.bio_agent.search_rag(
                query=payload.query,
                namespace=payload.namespace,
                top_k=payload.top_k,
            )
            return {"results": results}
        except Exception as exc:
            logger.exception("RAG search failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/rag/stats")
    def rag_stats() -> Dict[str, Any]:
        try:
            return app.state.bio_agent.get_rag_stats()
        except Exception as exc:
            logger.exception("RAG stats failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/research/stream")
    def stream_research(payload: ResearchRequest) -> StreamingResponse:

        def event_iterator() -> Iterator[str]:
            response_parts: List[str] = []
            status = "success"
            try:
                for event in app.state.bio_agent.run_research_stream(payload.username, payload.topic, payload.history):
                    event_type = event.get("type")
                    content = event.get("content")
                    if event_type in {"message", "message_chunk"} and content:
                        response_parts.append(str(content))
                    if event_type == "error":
                        status = "failed"
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except Exception as exc:
                status = "failed"
                logger.exception("Streaming research failed")
                error_payload = {"type": "error", "detail": str(exc)}
                response_parts.append(str(exc))
                yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
            finally:
                app.state.mysql_store.save_conversation(
                    username=payload.username,
                    request_text=payload.topic,
                    response_text="".join(response_parts),
                    conversation_type="research_stream",
                    history=payload.history,
                    status=status,
                )

        return StreamingResponse(
            event_iterator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    @app.websocket("/voice/ws/{session_id}")
    async def voice_websocket(websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()
        try:
            while True:
                payload = await websocket.receive_json()
                event_type = payload.get("type")

                if event_type == "interrupt":
                    turn = app.state.voice_agent.cancel(session_id)
                    await websocket.send_json({
                        "type": "interrupted",
                        "state": "interrupted",
                        "turn_id": getattr(turn, "id", None),
                        "played_text": getattr(turn, "played_text", ""),
                        "unplayed_text": getattr(turn, "unplayed_text", ""),
                    })
                    continue

                if event_type == "speech_start":
                    app.state.voice_agent.prewarm(session_id, payload.get("history") or [])
                    await websocket.send_json({"type": "prewarmed", "state": "listening"})
                    continue

                if event_type == "played":
                    app.state.voice_agent.mark_played(session_id, payload.get("text", ""))
                    continue

                if event_type != "audio":
                    await websocket.send_json({"type": "error", "detail": f"未知事件类型: {event_type}"})
                    continue

                try:
                    async for event in app.state.voice_agent.handle_utterance(
                        session_id=session_id,
                        audio_b64=payload.get("audio", ""),
                        history=payload.get("history") or [],
                        filename=payload.get("filename", "utterance.webm"),
                    ):
                        await websocket.send_json(event)
                except Exception as exc:
                    logger.exception("Voice turn failed")
                    await websocket.send_json({
                        "type": "error",
                        "detail": str(exc),
                        "recoverable": True,
                    })
                    await websocket.send_json({"type": "state", "state": "listening"})
        except WebSocketDisconnect:
            app.state.voice_agent.cancel(session_id)
        except Exception as exc:
            logger.exception("Voice websocket failed")
            await websocket.send_json({"type": "error", "detail": str(exc)})

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=7777,
        reload=True,
        log_level="info"
    )