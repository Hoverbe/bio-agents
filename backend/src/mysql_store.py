"""MySQL persistence helpers."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import pymysql
from dotenv import load_dotenv
from pymysql.connections import Connection


load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

MYSQL_HOST = os.getenv("MYSQL_HOST", "192.168.100.199")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "bio_agent")
MYSQL_CHARSET = os.getenv("MYSQL_CHARSET", "utf8mb4")


class MySQLStore:
    """Creates schema and stores users/conversations."""

    def __init__(self) -> None:
        self.host = MYSQL_HOST
        self.port = MYSQL_PORT
        self.user = MYSQL_USER
        self.password = MYSQL_PASSWORD
        self.database = MYSQL_DATABASE
        self.charset = MYSQL_CHARSET
        self.init_db()

    def _connect(self, database: Optional[str] = None) -> Connection:
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=database,
            charset=self.charset,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )

    @contextmanager
    def connection(self) -> Iterator[Connection]:
        conn = self._connect(self.database)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{self.database}` "
                    f"CHARACTER SET {self.charset} COLLATE {self.charset}_unicode_ci"
                )
            conn.commit()

        with self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                        username VARCHAR(191) NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (id),
                        UNIQUE KEY uk_users_username (username)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversations (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                        user_id BIGINT UNSIGNED NOT NULL,
                        conversation_type VARCHAR(32) NOT NULL,
                        request_text LONGTEXT NOT NULL,
                        response_text LONGTEXT NULL,
                        history_json JSON NULL,
                        metadata_json JSON NULL,
                        status VARCHAR(32) NOT NULL DEFAULT 'success',
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (id),
                        KEY idx_conversations_user_id (user_id),
                        KEY idx_conversations_type_created (conversation_type, created_at),
                        CONSTRAINT fk_conversations_user_id FOREIGN KEY (user_id) REFERENCES users (id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rag_chunks (
                        id CHAR(32) NOT NULL,
                        namespace VARCHAR(191) NOT NULL,
                        source VARCHAR(1024) NULL,
                        content LONGTEXT NOT NULL,
                        metadata JSON NULL,
                        embedding JSON NOT NULL,
                        created_at BIGINT NOT NULL,
                        PRIMARY KEY (id),
                        KEY idx_rag_namespace (namespace),
                        KEY idx_rag_source (source(191))
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )

    def get_or_create_user(self, username: str) -> int:
        clean_username = username.strip()
        if not clean_username:
            raise ValueError("username cannot be empty")

        with self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (username)
                    VALUES (%s)
                    ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id), updated_at = CURRENT_TIMESTAMP
                    """,
                    (clean_username,),
                )
                return int(cursor.lastrowid)

    def save_conversation(
        self,
        username: str,
        request_text: str,
        response_text: Optional[str],
        conversation_type: str = "chat",
        history: Optional[list[Dict[str, str]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "success",
    ) -> int:
        user_id = self.get_or_create_user(username)
        with self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO conversations
                    (user_id, conversation_type, request_text, response_text, history_json, metadata_json, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        conversation_type,
                        request_text,
                        response_text,
                        json.dumps(history, ensure_ascii=False) if history is not None else None,
                        json.dumps(metadata, ensure_ascii=False) if metadata is not None else None,
                        status,
                    ),
                )
                return int(cursor.lastrowid)

    def list_conversations(self, username: str, limit: int = 50) -> List[Dict[str, Any]]:
        clean_username = username.strip()
        if not clean_username:
            raise ValueError("username cannot be empty")

        with self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        c.id,
                        c.conversation_type,
                        c.request_text,
                        c.response_text,
                        c.history_json,
                        c.metadata_json,
                        c.status,
                        c.created_at,
                        c.updated_at
                    FROM conversations c
                    INNER JOIN users u ON u.id = c.user_id
                    WHERE u.username = %s
                    ORDER BY c.created_at DESC, c.id DESC
                    LIMIT %s
                    """,
                    (clean_username, limit),
                )
                rows = cursor.fetchall()

        for row in rows:
            for key in ("history_json", "metadata_json"):
                value = row.get(key)
                if isinstance(value, str):
                    row[key] = json.loads(value) if value else None
            row["created_at"] = row["created_at"].isoformat() if row.get("created_at") else None
            row["updated_at"] = row["updated_at"].isoformat() if row.get("updated_at") else None
        return rows

    def delete_conversation(self, username: str, conversation_id: int) -> bool:
        clean_username = username.strip()
        if not clean_username:
            raise ValueError("username cannot be empty")

        with self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE c
                    FROM conversations c
                    INNER JOIN users u ON u.id = c.user_id
                    WHERE u.username = %s AND c.id = %s
                    """,
                    (clean_username, conversation_id),
                )
                return cursor.rowcount > 0
