"""Web Search 工具。"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import Tool, ToolParameter


TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class WebSearchTool(Tool):
    """基于 Tavily Search API 的联网搜索工具。"""

    def __init__(self, timeout: int = 10):
        super().__init__(
            name="web_search",
            description="使用 Tavily 联网搜索公开网页信息，返回标题、摘要、链接和相关性分数。",
        )
        self.timeout = timeout

    def run(self, parameters: Dict[str, Any]) -> str:
        query = str(parameters.get("query") or parameters.get("input") or "").strip()
        if not query:
            return "错误：query 不能为空"

        api_key = os.getenv("TAVILY_API_KEY", "").strip().strip('"')
        if not api_key:
            return "错误：TAVILY_API_KEY 未配置"

        limit = self._clamp_int(parameters.get("limit") or parameters.get("max_results") or 5, 1, 20)
        search_depth = str(parameters.get("search_depth") or "basic").strip()
        if search_depth not in {"basic", "advanced", "fast", "ultra-fast"}:
            search_depth = "basic"

        topic = str(parameters.get("topic") or "general").strip()
        if topic not in {"general", "news", "finance"}:
            topic = "general"

        request_payload = {
            "query": query,
            "search_depth": search_depth,
            "max_results": limit,
            "topic": topic,
            "include_answer": bool(parameters.get("include_answer") or False),
            "include_raw_content": False,
            "include_images": False,
            "include_favicon": False,
        }

        try:
            tavily_payload = self._search_tavily(api_key, request_payload)
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            return f"错误：Tavily 搜索失败，HTTP {exc.code}: {detail}"
        except (TimeoutError, URLError, OSError, ValueError) as exc:
            return f"错误：Tavily 搜索失败：{exc}"

        results = [
            {
                "title": item.get("title", ""),
                "summary": item.get("content", ""),
                "url": item.get("url", ""),
                "source": "tavily",
                "score": item.get("score"),
            }
            for item in tavily_payload.get("results", [])
        ]
        payload = {
            "query": tavily_payload.get("query", query),
            "source": "tavily",
            "results": results,
        }
        if tavily_payload.get("answer"):
            payload["answer"] = tavily_payload["answer"]
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _search_tavily(self, api_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            TAVILY_SEARCH_URL,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        with urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _clamp_int(self, value: Any, minimum: int, maximum: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = minimum
        return max(minimum, min(parsed, maximum))

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="query", type="string", description="搜索关键词或问题", required=True),
            ToolParameter(name="limit", type="integer", description="返回结果数量，1-20", required=False, default=5),
            ToolParameter(name="search_depth", type="string", description="搜索深度：basic、advanced、fast、ultra-fast", required=False, default="basic"),
            ToolParameter(name="topic", type="string", description="搜索主题：general、news、finance", required=False, default="general"),
        ]
