"""轻量级 MySQL RAG 服务。"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from fastapi import UploadFile

from backend.src.mysql_store import MySQLStore


class RAGService:
    """基于 MySQL 和哈希向量的 RAG 实现。"""

    def __init__(
        self,
        db_path: Optional[str] = None,
        chunk_size: int = 900,
        chunk_overlap: int = 120,
        vector_size: int = 384,
    ):
        self.store = MySQLStore()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.vector_size = vector_size

    def add_text(
        self,
        text: str,
        source: str = "text",
        namespace: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        chunks = self._chunk_text(text)
        if not chunks:
            return 0
        self.delete_document(source=source, namespace=namespace)
        now = int(time.time())
        rows = []
        for index, chunk in enumerate(chunks):
            meta = dict(metadata or {})
            meta.update({"chunk_index": index, "total_chunks": len(chunks)})
            chunk_id = self._chunk_id(namespace, source, index, chunk)
            rows.append((
                chunk_id,
                namespace,
                source,
                chunk,
                json.dumps(meta, ensure_ascii=False),
                json.dumps(self._embed(chunk)),
                now,
            ))

        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO rag_chunks
                    (id, namespace, source, content, metadata, embedding, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        namespace = VALUES(namespace),
                        source = VALUES(source),
                        content = VALUES(content),
                        metadata = VALUES(metadata),
                        embedding = VALUES(embedding),
                        created_at = VALUES(created_at)
                    """,
                    rows,
                )
        return len(rows)

    def add_file(self, file_path: str, namespace: str = "default") -> int:
        path = Path(file_path)
        text = self._load_file(path)
        metadata = {
            "source_path": str(path),
            "file_name": path.name,
            "file_ext": path.suffix.lower(),
            "doc_status": "active",
            "doc_name": path.name,
        }
        return self.add_text(text=text, source=str(path), namespace=namespace, metadata=metadata)

    def add_upload(self, file: UploadFile, namespace: str = "default") -> int:
        filename = file.filename or "upload"
        suffix = Path(filename).suffix.lower()
        text = self._load_upload(file, suffix)
        metadata = {
            "source_path": filename,
            "file_name": filename,
            "file_ext": suffix,
            "doc_status": "active",
            "doc_name": filename,
        }
        return self.add_text(text=text, source=filename, namespace=namespace, metadata=metadata)

    def list_documents(self, namespace: str = "default") -> List[Dict[str, Any]]:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT source, MIN(metadata) AS metadata, MAX(created_at) AS created_at, COUNT(*) AS chunk_count
                    FROM rag_chunks
                    WHERE namespace = %s
                    GROUP BY source
                    ORDER BY created_at DESC
                    """,
                    (namespace,),
                )
                rows = cursor.fetchall()

        documents: List[Dict[str, Any]] = []
        for row in rows:
            metadata = self._json_loads(row["metadata"], {})
            documents.append({
                "source": row["source"],
                "name": metadata.get("doc_name") or metadata.get("file_name") or row["source"],
                "status": metadata.get("doc_status", "active"),
                "chunk_count": row["chunk_count"],
                "created_at": row["created_at"],
                "metadata": metadata,
            })
        return documents

    def set_document_status(self, source: str, namespace: str = "default", status: str = "active") -> int:
        updated = 0
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, metadata
                    FROM rag_chunks
                    WHERE namespace = %s AND source = %s
                    """,
                    (namespace, source),
                )
                rows = cursor.fetchall()
                for row in rows:
                    metadata = self._json_loads(row["metadata"], {})
                    metadata["doc_status"] = status
                    cursor.execute(
                        "UPDATE rag_chunks SET metadata = %s WHERE id = %s",
                        (json.dumps(metadata, ensure_ascii=False), row["id"]),
                    )
                    updated += 1
        return updated

    def delete_document(self, source: str, namespace: str = "default") -> int:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM rag_chunks WHERE namespace = %s AND source = %s",
                    (namespace, source),
                )
                return cursor.rowcount

    def search(self, query: str, namespace: str = "default", top_k: int = 5) -> List[Dict[str, Any]]:
        query_vector = self._embed(query)
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, namespace, source, content, metadata, embedding
                    FROM rag_chunks
                    WHERE namespace = %s
                    """,
                    (namespace,),
                )
                rows = cursor.fetchall()

        results = []
        for row in rows:
            metadata = self._json_loads(row["metadata"], {})
            if metadata.get("doc_status", "active") != "active":
                continue
            embedding = self._json_loads(row["embedding"], [])
            score = self._cosine(query_vector, embedding)
            if score <= 0:
                continue
            results.append(
                {
                    "id": row["id"],
                    "score": score,
                    "source": row["source"],
                    "content": row["content"],
                    "metadata": metadata,
                }
            )

        results.sort(key=lambda item: item["score"], reverse=True)
        return results[: max(1, top_k)]

    def build_context(self, query: str, namespace: str = "default", top_k: int = 5, max_chars: int = 3000) -> str:
        hits = self.search(query=query, namespace=namespace, top_k=top_k)
        parts = []
        total = 0
        for index, hit in enumerate(hits, 1):
            source = hit.get("source") or "知识库"
            text = hit.get("content", "").strip()
            snippet = f"[{index}] 来源：{source}\n{text}"
            if total + len(snippet) > max_chars:
                remain = max_chars - total
                if remain <= 0:
                    break
                snippet = snippet[:remain]
            parts.append(snippet)
            total += len(snippet)
        return "\n\n".join(parts)

    def stats(self) -> Dict[str, Any]:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS c FROM rag_chunks")
                total = cursor.fetchone()["c"]
                cursor.execute(
                    "SELECT namespace, COUNT(*) AS c FROM rag_chunks GROUP BY namespace ORDER BY c DESC"
                )
                namespaces = cursor.fetchall()
        return {
            "database": self.store.database,
            "total_chunks": total,
            "namespaces": {row["namespace"]: row["c"] for row in namespaces},
        }

    def _load_file(self, path: Path) -> str:
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        return self._extract_text(path.suffix.lower(), path.read_bytes())

    def _load_upload(self, file: UploadFile, suffix: str) -> str:
        return self._extract_text(suffix, file.file.read())

    def _extract_text(self, suffix: str, content: bytes) -> str:
        if suffix == ".pdf":
            try:
                import PyPDF2
                from io import BytesIO

                reader = PyPDF2.PdfReader(BytesIO(content))
                return "\n".join(page.extract_text() or "" for page in reader.pages)
            except ImportError as exc:
                raise RuntimeError("解析 PDF 需要安装 PyPDF2") from exc
        if suffix in {".docx", ".doc"}:
            try:
                import docx
                from io import BytesIO

                document = docx.Document(BytesIO(content))
                return "\n".join(paragraph.text for paragraph in document.paragraphs)
            except ImportError as exc:
                raise RuntimeError("解析 Word 需要安装 python-docx") from exc
        if suffix in {".xlsx", ".xls", ".csv"}:
            try:
                import pandas as pd
                from io import BytesIO, StringIO

                if suffix == ".csv":
                    frame = pd.read_csv(StringIO(content.decode("utf-8", errors="ignore")))
                    return frame.to_csv(index=False)
                sheets = pd.read_excel(BytesIO(content), sheet_name=None)
                return "\n\n".join(
                    f"# {name}\n{frame.to_csv(index=False)}"
                    for name, frame in sheets.items()
                )
            except ImportError as exc:
                raise RuntimeError("解析 Excel/CSV 需要安装 pandas 和 openpyxl") from exc
        return content.decode("utf-8", errors="ignore")

    def _chunk_text(self, text: str) -> List[str]:
        clean_text = re.sub(r"\n{3,}", "\n\n", text or "").strip()
        if not clean_text:
            return []
        if len(clean_text) <= self.chunk_size:
            return [clean_text]

        chunks = []
        start = 0
        separators = ["\n\n", "\n", "。", ".", " "]
        while start < len(clean_text):
            end = min(len(clean_text), start + self.chunk_size)
            if end == len(clean_text):
                chunks.append(clean_text[start:end].strip())
                break

            split_at = -1
            search_area = clean_text[start:end]
            for sep in separators:
                pos = search_area.rfind(sep)
                if pos >= int(self.chunk_size * 0.6):
                    split_at = start + pos + len(sep)
                    break
            if split_at == -1:
                split_at = end

            chunk = clean_text[start:split_at].strip()
            if chunk:
                chunks.append(chunk)
            start = max(split_at - self.chunk_overlap, start + 1)
        return chunks

    def _embed(self, text: str) -> List[float]:
        vector = [0.0] * self.vector_size
        tokens = self._tokenize(text)
        for token in tokens:
            digest = hashlib.md5(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.vector_size
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def _tokenize(self, text: str) -> Iterable[str]:
        lowered = text.lower()
        words = re.findall(r"[a-z0-9_\-]+|[\u4e00-\u9fff]", lowered)
        for word in words:
            yield word
        compact = re.sub(r"\s+", "", lowered)
        for size in (2, 3):
            for index in range(max(0, len(compact) - size + 1)):
                yield compact[index:index + size]

    def _cosine(self, left: List[float], right: List[float]) -> float:
        return sum(a * b for a, b in zip(left, right))

    def _chunk_id(self, namespace: str, source: str, index: int, content: str) -> str:
        raw = f"{namespace}|{source}|{index}|{hashlib.md5(content.encode('utf-8')).hexdigest()}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _json_loads(self, value: Any, default: Any) -> Any:
        if value is None:
            return default
        if isinstance(value, (dict, list)):
            return value
        return json.loads(value)
