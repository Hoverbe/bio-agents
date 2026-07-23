"""FastAPI entrypoint exposing the Bio-Agent via HTTP."""

from __future__ import annotations

import json
import re
import shutil
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, List
from urllib.parse import quote, unquote

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
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


class ConversationHistoryResponse(BaseModel):
    """HTTP response for saved conversation history."""

    conversations: List[Dict[str, Any]] = Field(default_factory=list)


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
    attachments: Optional[List["ResearchAttachment"]] = Field(
        default=None,
        description="Parsed upload attachments included with this turn"
    )


class ResearchAttachment(BaseModel):
    """Parsed attachment content sent with a research turn."""

    filename: str = Field(default="attachment", description="Original uploaded filename")
    content: str = Field(default="", description="Extracted text content")
    content_type: Optional[str] = Field(default=None, description="Uploaded file MIME type")
    truncated: bool = Field(default=False, description="Whether extracted content was truncated")
    saved_path: Optional[str] = Field(default=None, description="Server-side saved upload path")
    saved_url: Optional[str] = Field(default=None, description="Server-side saved upload URL")


class AttachmentParseResponse(BaseModel):
    """Response for a parsed chat attachment upload."""

    filename: str
    content: str
    content_type: Optional[str] = None
    size: Optional[int] = None
    chars: int
    truncated: bool = False
    saved_path: Optional[str] = None
    saved_url: Optional[str] = None


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
    cwd: Optional[str] = None
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


class ModelConfigRequest(BaseModel):
    model_name: str = Field(..., min_length=1)
    base_url: str = Field(..., min_length=1)
    api_key: Optional[str] = None
    enabled: bool = True


class ActiveModelRequest(BaseModel):
    name: str = Field(..., min_length=1)


class ResearchResponse(BaseModel):
    """HTTP response containing the generated report and structured tasks."""

    report_markdown: str = Field(
        ..., description="Markdown-formatted research report including sections"
    )
    todo_items: list[TaskItem] = Field(
        default_factory=list,
        description="Structured TODO items with summaries and sources",
    )


MAX_ATTACHMENT_CONTEXT_CHARS = 120_000
BASE_DIR = Path(__file__).resolve().parents[1]
WORK_TEMP_DIR = BASE_DIR / "work_temp"
UPLOAD_DIR = WORK_TEMP_DIR / "uploads"
DOWNLOAD_DIR = WORK_TEMP_DIR / "downloads"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
MCP_WORKSPACE_LOCK = threading.Lock()


def ensure_work_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def safe_filename(filename: str) -> str:
    return Path(filename or "attachment").name.replace("/", "_").replace("\\", "_") or "attachment"


def unique_path(directory: Path, filename: str) -> Path:
    target = directory / safe_filename(filename)
    if not target.exists():
        return target
    stem = target.stem or "file"
    suffix = target.suffix
    counter = 1
    while True:
        candidate = directory / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def safe_session_id(value: str) -> str:
    safe_value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return safe_value.strip("._") or datetime.now().strftime("%Y%m%d%H%M%S%f")


def get_download_session_dir(session_id: str) -> Path:
    return DOWNLOAD_DIR / safe_session_id(session_id)


def rewrite_workspace_arg(values: List[str], workspace: str) -> None:
    try:
        index = values.index("--workspace")
    except ValueError:
        return
    if index + 1 < len(values):
        values[index + 1] = workspace


def quote_download_path(relative: str) -> str:
    return quote(relative, safe="/")


def list_download_files(session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    ensure_work_dirs()
    base_dir = get_download_session_dir(session_id) if session_id else DOWNLOAD_DIR
    if not base_dir.exists():
        return []
    files: List[Dict[str, Any]] = []
    for path in sorted(base_dir.rglob("*"), key=lambda item: item.stat().st_mtime, reverse=True):
        if not path.is_file():
            continue
        relative = path.relative_to(DOWNLOAD_DIR).as_posix()
        session_relative = path.relative_to(base_dir).as_posix()
        files.append({
            "name": path.name,
            "path": relative,
            "session_path": session_relative,
            "size": path.stat().st_size,
            "url": f"/downloads/{quote_download_path(relative)}",
            "is_image": path.suffix.lower() in IMAGE_SUFFIXES,
        })
    return files


def normalize_download_relative_path(relative_path: str) -> str:
    decoded = unquote(relative_path or "")
    if not decoded or decoded.startswith("/"):
        raise HTTPException(status_code=404, detail="Download file not found")
    normalized = Path(decoded).as_posix()
    if normalized == "." or normalized.startswith("../") or "/../" in normalized:
        raise HTTPException(status_code=404, detail="Download file not found")
    return normalized


def resolve_download_path(relative_path: str) -> Path:
    ensure_work_dirs()
    normalized = normalize_download_relative_path(relative_path)
    target = (DOWNLOAD_DIR / normalized).resolve()
    if not target.is_file() or DOWNLOAD_DIR.resolve() not in target.parents:
        raise HTTPException(status_code=404, detail="Download file not found")
    return target


def resolve_upload_path(relative_path: str) -> Path:
    ensure_work_dirs()
    target = (UPLOAD_DIR / relative_path).resolve()
    if not target.is_file() or UPLOAD_DIR.resolve() not in target.parents:
        raise HTTPException(status_code=404, detail="Upload file not found")
    return target


def format_download_image_markdown(files: List[Dict[str, Any]]) -> str:
    image_lines = [f"![{item['name']}]({item['url']})" for item in files if item.get("is_image")]
    if not image_lines:
        return ""
    return "\n\n" + "\n\n".join(image_lines)


def format_download_links_markdown(files: List[Dict[str, Any]]) -> str:
    if not files:
        return ""
    lines = ["\n\n### 下载文件"]
    for item in files:
        name = item.get("name") or item.get("path") or "download"
        url = item.get("url")
        if url:
            lines.append(f"- [{name}]({url})")
    return "\n".join(lines) if len(lines) > 1 else ""


def format_attachment_context(
    attachments: Optional[List[ResearchAttachment]],
    output_dir: Optional[Path] = None,
) -> str:
    parts: List[str] = []
    if output_dir:
        parts.append(
            "Output directory for generated files in this turn:\n"
            f"{output_dir}\n"
            "All generated result files, tables, and figures must be written to this directory."
        )

    if not attachments:
        return "\n\n".join(parts)

    for index, attachment in enumerate(attachments, start=1):
        content = (attachment.content or "").strip()
        saved_note = f"\nSaved upload path: {attachment.saved_path}" if attachment.saved_path else ""
        saved_url_note = f"\nSaved upload URL: {attachment.saved_url}" if attachment.saved_url else ""
        if not content and not saved_note:
            continue

        truncated_note = " (truncated)" if attachment.truncated else ""
        parts.append(
            f"Attachment {index}: {attachment.filename}{truncated_note}"
            f"{saved_note}{saved_url_note}\n"
            f"{content[:MAX_ATTACHMENT_CONTEXT_CHARS]}"
        )

    return "\n\n".join(parts)


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

    def mask_secret(value: Optional[str]) -> str:
        if not value:
            return ""
        if len(value) <= 8:
            return "****"
        return f"{value[:4]}...{value[-4:]}"

    def sanitize_model_config(item: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = {key: val for key, val in item.items() if key != "api_key"}
        api_key = item.get("api_key") or ""
        sanitized["has_api_key"] = bool(api_key)
        sanitized["api_key_mask"] = mask_secret(api_key)
        return sanitized

    def current_model_info(config: Dict[str, Any]) -> Dict[str, Any]:
        llm = getattr(getattr(app.state, "bio_agent", None), "llm", None)
        if not llm:
            return {
                "name": config.get("active_model", ""),
                "model_name": "",
                "base_url": "",
                "provider": "",
                "has_api_key": False,
                "api_key_mask": "",
            }
        return {
            "name": config.get("active_model", ""),
            "model_name": getattr(llm, "model", ""),
            "base_url": getattr(llm, "base_url", ""),
            "provider": getattr(llm, "provider", ""),
            "has_api_key": bool(getattr(llm, "api_key", "")),
            "api_key_mask": mask_secret(getattr(llm, "api_key", "")),
        }

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
            "model": current_model_info(config),
            "model_config": [sanitize_model_config(item) for item in config.get("models", [])],
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
                "cwd": payload.cwd,
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

    @app.post("/admin/models")
    def save_model_config(payload: ModelConfigRequest) -> Dict[str, Any]:
        previous_config = load_config()
        config = json.loads(json.dumps(previous_config, ensure_ascii=False))
        models: List[Dict[str, Any]] = list(config.get("models", []))
        name = payload.model_name.strip()
        existing = next((item for item in models if item.get("name") == name), None)
        api_key = (payload.api_key or "").strip()
        if not api_key and existing:
            api_key = existing.get("api_key", "")

        item = {
            "name": name,
            "model_name": name,
            "base_url": payload.base_url.strip(),
            "api_key": api_key,
            "enabled": payload.enabled,
        }
        for index, current in enumerate(models):
            if current.get("name") == name:
                models[index] = item
                break
        else:
            models.append(item)

        config["models"] = models
        if payload.enabled:
            config["active_model"] = name
        elif config.get("active_model") == name:
            next_model = next((model for model in models if model.get("name") != name and model.get("enabled", True)), None)
            config["active_model"] = next_model.get("name", "") if next_model else ""
        try:
            save_config(config)
            reload_agent_config()
            return {"ok": True}
        except Exception as exc:
            save_config(previous_config)
            reload_agent_config()
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/admin/models/active")
    def activate_model_config(payload: ActiveModelRequest) -> Dict[str, Any]:
        previous_config = load_config()
        config = json.loads(json.dumps(previous_config, ensure_ascii=False))
        models = config.get("models", [])
        target = next((item for item in models if item.get("name") == payload.name), None)
        if not target:
            raise HTTPException(status_code=404, detail="Model config not found")
        if target.get("enabled") is False:
            raise HTTPException(status_code=400, detail="Model config is disabled")
        config["active_model"] = payload.name
        try:
            save_config(config)
            reload_agent_config()
            return {"ok": True}
        except Exception as exc:
            save_config(previous_config)
            reload_agent_config()
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.delete("/admin/models/{name}")
    def delete_model_config(name: str) -> Dict[str, Any]:
        previous_config = load_config()
        config = json.loads(json.dumps(previous_config, ensure_ascii=False))
        config["models"] = [item for item in config.get("models", []) if item.get("name") != name]
        if config.get("active_model") == name:
            next_model = next((item for item in config["models"] if item.get("enabled", True)), None)
            config["active_model"] = next_model.get("name", "") if next_model else ""
        try:
            save_config(config)
            reload_agent_config()
            return {"ok": True}
        except Exception as exc:
            save_config(previous_config)
            reload_agent_config()
            raise HTTPException(status_code=400, detail=str(exc)) from exc

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

    @app.get("/conversations/{username}", response_model=ConversationHistoryResponse)
    def get_conversations(username: str, limit: int = 50) -> ConversationHistoryResponse:
        try:
            return ConversationHistoryResponse(
                conversations=app.state.mysql_store.list_conversations(username=username, limit=limit)
            )
        except Exception as exc:
            logger.exception("Conversation history lookup failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.delete("/conversations/{username}/{conversation_id}")
    def delete_conversation(username: str, conversation_id: int) -> Dict[str, Any]:
        try:
            deleted = app.state.mysql_store.delete_conversation(
                username=username,
                conversation_id=conversation_id,
            )
            if not deleted:
                raise HTTPException(status_code=404, detail="Conversation not found")
            return {"deleted": True, "id": conversation_id}
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Conversation delete failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/attachments/parse", response_model=AttachmentParseResponse)
    def parse_chat_attachment(file: UploadFile = File(...)) -> AttachmentParseResponse:
        try:
            ensure_work_dirs()
            filename = safe_filename(file.filename or "attachment")
            saved_file = unique_path(UPLOAD_DIR, filename)
            if hasattr(file.file, "seek"):
                file.file.seek(0)
            with saved_file.open("wb") as output:
                shutil.copyfileobj(file.file, output)
            size = saved_file.stat().st_size

            if hasattr(file.file, "seek"):
                file.file.seek(0)
            content = (app.state.bio_agent.parse_upload(file=file) or "").strip()
            truncated = len(content) > MAX_ATTACHMENT_CONTEXT_CHARS
            if truncated:
                content = content[:MAX_ATTACHMENT_CONTEXT_CHARS]

            relative = saved_file.relative_to(UPLOAD_DIR).as_posix()
            return AttachmentParseResponse(
                filename=filename,
                content=content,
                content_type=file.content_type,
                size=size,
                chars=len(content),
                truncated=truncated,
                saved_path=str(saved_file),
                saved_url=f"/uploads/{quote(relative, safe='/')}",
            )
        except Exception as exc:
            logger.exception("Attachment parsing failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/uploads/{file_path:path}")
    def get_upload_file(file_path: str) -> FileResponse:
        target = resolve_upload_path(file_path)
        return FileResponse(target, filename=target.name)

    @app.get("/downloads")
    def get_downloads(session_id: Optional[str] = None) -> Dict[str, Any]:
        return {"files": list_download_files(session_id)}

    @app.get("/downloads/{file_path:path}")
    def get_download_file(file_path: str) -> FileResponse:
        target = resolve_download_path(file_path)
        return FileResponse(target, filename=target.name)

    @app.post("/chat", response_model=ChatResponse)
    def chat(payload: ChatRequest) -> ChatResponse:
        try:
            response = app.state.bio_agent.run(payload.message)
            app.state.mysql_store.save_conversation(
                username=payload.username,
                request_text=payload.message,
                response_text=response,
                conversation_type="chat",
                history=[
                    {"role": "user", "content": payload.message},
                    {"role": "assistant", "content": response},
                ],
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
            saved = False
            conversation_id = app.state.mysql_store.save_conversation(
                username=payload.username,
                request_text=payload.topic,
                response_text=None,
                conversation_type="research_stream",
                history=payload.history or [],
                status="running",
            )
            session_id = str(conversation_id)
            session_download_dir = get_download_session_dir(session_id)
            session_download_dir.mkdir(parents=True, exist_ok=True)
            file_context = format_attachment_context(payload.attachments, output_dir=session_download_dir)
            try:
                with MCP_WORKSPACE_LOCK:
                    previous_mcp_state: Dict[str, Dict[str, Any]] = {}
                    for item in app.state.bio_agent.admin_config.get("mcp", []):
                        name = item.get("name", "")
                        env = item.get("env") or {}
                        if isinstance(env, dict):
                            previous_mcp_state.setdefault(name, {})["config_project_path"] = env.get("PROJECT_PATH")
                            if "PROJECT_PATH" in env:
                                env["PROJECT_PATH"] = str(session_download_dir)

                        server_args = item.get("server_args") or []
                        if isinstance(server_args, list):
                            previous_mcp_state.setdefault(name, {})["config_server_args"] = list(server_args)
                            rewrite_workspace_arg(server_args, str(session_download_dir))

                        service = app.state.bio_agent.mcp_services.get(name, {})
                        tool = service.get("tool")
                        if not tool:
                            continue

                        previous_mcp_state.setdefault(name, {})["tool_env"] = dict(getattr(tool, "env", {}) or {})
                        previous_mcp_state.setdefault(name, {})["tool_server_command"] = list(getattr(tool, "server_command", []) or [])
                        if hasattr(tool, "env") and "PROJECT_PATH" in tool.env:
                            tool.env["PROJECT_PATH"] = str(session_download_dir)
                        if hasattr(tool, "server_command"):
                            rewrite_workspace_arg(tool.server_command, str(session_download_dir))

                    script_tool = getattr(app.state.bio_agent, "python_script_tool", None)
                    previous_script_output_dir = getattr(script_tool, "output_dir", None) if script_tool else None
                    try:
                        if script_tool:
                            script_tool.set_output_dir(str(session_download_dir))

                        stream_events = app.state.bio_agent.run_research_stream(
                            payload.username,
                            payload.topic,
                            payload.history,
                            file_context=file_context,
                        )
                        for event in stream_events:
                            event_type = event.get("type")
                            content = event.get("content")
                            if event_type in {"message", "message_chunk"} and content:
                                response_parts.append(str(content))
                            if event_type == "error":
                                status = "failed"
                            if event_type == "done":
                                download_files = list_download_files(session_id)
                                image_markdown = format_download_image_markdown(download_files)
                                links_markdown = format_download_links_markdown(download_files)
                                response_text = "".join(response_parts)
                                if links_markdown and links_markdown not in response_text:
                                    response_text = f"{response_text}{links_markdown}"
                                    response_parts.append(links_markdown)
                                    yield f"data: {json.dumps({'type': 'message', 'content': links_markdown, 'agent': 'automation_agent', 'agent_name': '自动化执行专家'}, ensure_ascii=False)}\n\n"
                                if image_markdown and image_markdown not in response_text:
                                    response_text = f"{response_text}{image_markdown}"
                                    response_parts.append(image_markdown)
                                    yield f"data: {json.dumps({'type': 'message', 'content': image_markdown, 'agent': 'automation_agent', 'agent_name': '自动化执行专家'}, ensure_ascii=False)}\n\n"
                                if download_files:
                                    files_payload = {"type": "files", "files": download_files, "session_id": session_id}
                                    yield f"data: {json.dumps(files_payload, ensure_ascii=False)}\n\n"
                                saved_history = [*(payload.history or []), {"role": "assistant", "content": response_text}]
                                app.state.mysql_store.update_conversation(
                                    conversation_id=conversation_id,
                                    response_text=response_text,
                                    history=saved_history,
                                    metadata={"download_session_id": session_id, "download_files": download_files},
                                    status=status,
                                )
                                saved = True
                                saved_payload = {"type": "conversation_saved", "id": conversation_id, "download_session_id": session_id, "download_files": download_files}
                                yield f"data: {json.dumps(saved_payload, ensure_ascii=False)}\n\n"
                            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    finally:
                        for item in app.state.bio_agent.admin_config.get("mcp", []):
                            name = item.get("name", "")
                            state = previous_mcp_state.get(name, {})
                            env = item.get("env") or {}
                            if isinstance(env, dict) and "config_project_path" in state:
                                if state["config_project_path"] is None:
                                    env.pop("PROJECT_PATH", None)
                                else:
                                    env["PROJECT_PATH"] = state["config_project_path"]
                            if isinstance(item.get("server_args"), list) and "config_server_args" in state:
                                item["server_args"] = state["config_server_args"]

                            service = app.state.bio_agent.mcp_services.get(name, {})
                            tool = service.get("tool")
                            if not tool:
                                continue
                            if "tool_env" in state:
                                tool.env = state["tool_env"]
                            if "tool_server_command" in state:
                                tool.server_command = state["tool_server_command"]
                        if script_tool and previous_script_output_dir is not None:
                            script_tool.set_output_dir(str(previous_script_output_dir))
            except GeneratorExit:
                status = "interrupted"
                logger.info("Research stream interrupted by client disconnect")
                raise
            except Exception as exc:
                status = "failed"
                logger.exception("Streaming research failed")
                error_payload = {"type": "error", "detail": str(exc)}
                response_parts.append(str(exc))
                yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
            finally:
                if saved:
                    return
                response_text = "".join(response_parts)
                saved_history = [*(payload.history or []), {"role": "assistant", "content": response_text}]
                download_files = list_download_files(session_id)
                app.state.mysql_store.update_conversation(
                    conversation_id=conversation_id,
                    response_text=response_text,
                    history=saved_history,
                    metadata={"download_session_id": session_id, "download_files": download_files},
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
                        play_audio=payload.get("play_audio", True),
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
