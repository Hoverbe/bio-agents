"""Web Search 工具。"""

from __future__ import annotations

import json
import re
from html import unescape
from html.parser import HTMLParser
from typing import Any, Dict, List
from urllib.error import URLError
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

from .base import Tool, ToolParameter


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)


class _BingParser(HTMLParser):
    def __init__(self, limit: int):
        super().__init__(convert_charrefs=True)
        self.limit = limit
        self.results: List[Dict[str, str]] = []
        self._in_result = False
        self._in_title_link = False
        self._in_caption = False
        self._current: Dict[str, str] = {}
        self._title_parts: List[str] = []
        self._summary_parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        attrs_dict = {key: value or "" for key, value in attrs}
        classes = attrs_dict.get("class", "").split()

        if tag == "li" and "b_algo" in classes:
            self._in_result = True
            self._current = {"title": "", "summary": "", "url": ""}
            self._title_parts = []
            self._summary_parts = []
            return

        if not self._in_result:
            return

        if tag == "a" and not self._current.get("url"):
            href = attrs_dict.get("href", "")
            if href.startswith("http"):
                self._current["url"] = href
                self._in_title_link = True
        elif tag == "p":
            self._in_caption = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._in_title_link = False
        elif tag == "p":
            self._in_caption = False
        elif tag == "li" and self._in_result:
            title = _clean_text(" ".join(self._title_parts))
            summary = _clean_text(" ".join(self._summary_parts))
            url = self._current.get("url", "")
            if title and url and len(self.results) < self.limit:
                self.results.append({
                    "title": title,
                    "summary": _truncate(summary),
                    "url": url,
                    "source": "bing",
                })
            self._in_result = False
            self._in_title_link = False
            self._in_caption = False

    def handle_data(self, data: str) -> None:
        if self._in_title_link:
            self._title_parts.append(data)
        elif self._in_caption:
            self._summary_parts.append(data)


class _DuckDuckGoParser(HTMLParser):
    def __init__(self, limit: int):
        super().__init__(convert_charrefs=True)
        self.limit = limit
        self.results: List[Dict[str, str]] = []
        self._capture_title = False
        self._capture_summary = False
        self._current: Dict[str, str] = {}
        self._title_parts: List[str] = []
        self._summary_parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        attrs_dict = {key: value or "" for key, value in attrs}
        classes = attrs_dict.get("class", "").split()

        if tag == "a" and "result__a" in classes:
            self._flush_current()
            href = attrs_dict.get("href", "")
            self._current = {"title": "", "summary": "", "url": _normalize_duckduckgo_url(href)}
            self._title_parts = []
            self._summary_parts = []
            self._capture_title = True
        elif "result__snippet" in classes:
            self._capture_summary = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._capture_title = False
        elif tag in {"a", "div"}:
            self._capture_summary = False

    def handle_data(self, data: str) -> None:
        if self._capture_title:
            self._title_parts.append(data)
        elif self._capture_summary:
            self._summary_parts.append(data)

    def close(self) -> None:
        self._flush_current()
        super().close()

    def _flush_current(self) -> None:
        if len(self.results) >= self.limit or not self._current:
            return
        title = _clean_text(" ".join(self._title_parts))
        url = self._current.get("url", "")
        if title and url:
            self.results.append({
                "title": title,
                "summary": _truncate(_clean_text(" ".join(self._summary_parts))),
                "url": url,
                "source": "duckduckgo",
            })


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _truncate(text: str, max_length: int = 200) -> str:
    return text if len(text) <= max_length else text[:max_length] + "..."


def _normalize_duckduckgo_url(url: str) -> str:
    if url.startswith("//"):
        url = "https:" + url
    parsed = urlparse(url)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        uddg = parse_qs(parsed.query).get("uddg")
        if uddg:
            return unquote(uddg[0])
    return url


def _fetch(url: str, timeout: int) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("content-type", "")
        body = response.read()
    charset_match = re.search(r"charset=([^;\s]+)", content_type, re.I)
    charset = charset_match.group(1) if charset_match else "utf-8"
    return body.decode(charset, errors="ignore")


class WebSearchTool(Tool):
    """联网搜索工具，参考 open_websearch-master 的搜索器设计。"""

    def __init__(self, timeout: int = 10):
        super().__init__(
            name="web_search",
            description="联网搜索公开网页信息，返回标题、摘要、链接和来源。支持 sources=bing,duckduckgo，默认使用 bing。",
        )
        self.timeout = timeout

    def run(self, parameters: Dict[str, Any]) -> str:
        query = str(parameters.get("query") or parameters.get("input") or "").strip()
        if not query:
            return "错误：query 不能为空"

        limit = int(parameters.get("limit") or 5)
        limit = max(1, min(limit, 10))
        sources = self._parse_sources(parameters.get("sources") or "bing")

        results: List[Dict[str, str]] = []
        errors: Dict[str, str] = {}
        for source in sources:
            try:
                if source == "bing":
                    results.extend(self._search_bing(query, limit))
                elif source == "duckduckgo":
                    results.extend(self._search_duckduckgo(query, limit))
            except (TimeoutError, URLError, OSError, ValueError) as exc:
                errors[source] = str(exc)

        payload = {
            "query": query,
            "sources": sources,
            "results": results[: limit * len(sources)],
        }
        if errors:
            payload["errors"] = errors
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _parse_sources(self, value: Any) -> List[str]:
        if isinstance(value, list):
            raw_sources = value
        else:
            raw_sources = str(value).split(",")
        sources = [str(source).strip().lower() for source in raw_sources if str(source).strip()]
        allowed = [source for source in sources if source in {"bing", "duckduckgo"}]
        return allowed or ["bing"]

    def _search_bing(self, query: str, limit: int) -> List[Dict[str, str]]:
        html = _fetch(f"https://cn.bing.com/search?q={quote_plus(query)}&count={limit}", self.timeout)
        parser = _BingParser(limit)
        parser.feed(html)
        parser.close()
        return parser.results

    def _search_duckduckgo(self, query: str, limit: int) -> List[Dict[str, str]]:
        html = _fetch(f"https://html.duckduckgo.com/html/?q={quote_plus(query)}", self.timeout)
        parser = _DuckDuckGoParser(limit)
        parser.feed(html)
        parser.close()
        return parser.results

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="query", type="string", description="搜索关键词或问题", required=True),
            ToolParameter(name="sources", type="string", description="搜索源，逗号分隔：bing,duckduckgo", required=False, default="bing"),
            ToolParameter(name="limit", type="integer", description="每个搜索源返回数量，1-10", required=False, default=5),
        ]
