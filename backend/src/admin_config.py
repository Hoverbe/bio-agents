"""后台管理配置持久化。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

CONFIG_PATH = Path(__file__).resolve().parents[1] / "data" / "admin_config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "mcp": [
        {
            "name": "bioinformatics",
            "description": "生物信息学分析服务",
            "server_command": ["uvx", "--from", "bioinformatics-mcp-server", "bioinformatics-server.exe"],
            "server_args": [],
            "env": {},
            "enabled": True,
        }
    ],
    "tools": [
        {
            "name": "terminal",
            "description": "终端命令执行工具",
            "type": "builtin",
            "enabled": True,
            "config": {"timeout": 30, "max_output_size": 10485760},
        },
        {
            "name": "web_search",
            "description": "使用 Tavily 联网搜索公开网页信息，返回标题、摘要、链接和相关性分数",
            "type": "builtin",
            "enabled": True,
            "config": {"timeout": 10},
        }
    ],
    "skills": [],
    "rag": {
        "namespace": "default",
        "top_k": 5,
        "chunk_size": 900,
        "chunk_overlap": 120,
        "enabled": True,
    },
}


def _ensure_config() -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)


def load_config() -> Dict[str, Any]:
    _ensure_config()
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = DEFAULT_CONFIG.copy()
    config = DEFAULT_CONFIG.copy()
    config.update(data)
    for key in ("mcp", "tools", "skills"):
        if not isinstance(config.get(key), list):
            config[key] = []
    if not isinstance(config.get("rag"), dict):
        config["rag"] = DEFAULT_CONFIG["rag"].copy()
    return config


def save_config(config: Dict[str, Any]) -> Dict[str, Any]:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return config


def upsert_item(section: str, item: Dict[str, Any]) -> Dict[str, Any]:
    config = load_config()
    items: List[Dict[str, Any]] = list(config.get(section, []))
    name = item.get("name")
    if not name:
        raise ValueError("name 不能为空")
    for index, current in enumerate(items):
        if current.get("name") == name:
            items[index] = item
            break
    else:
        items.append(item)
    config[section] = items
    return save_config(config)


def delete_item(section: str, name: str) -> Dict[str, Any]:
    config = load_config()
    config[section] = [item for item in config.get(section, []) if item.get("name") != name]
    return save_config(config)


def enabled_items(section: str) -> List[Dict[str, Any]]:
    return [item for item in load_config().get(section, []) if item.get("enabled", True)]


def is_tool_enabled(name: str) -> bool:
    tools = load_config().get("tools", [])
    for tool in tools:
        if tool.get("name") == name:
            return bool(tool.get("enabled", True))
    return True
