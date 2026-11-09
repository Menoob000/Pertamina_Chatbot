"""PostgreSQL persistence for Streamlit conversations and LangGraph messages."""
from __future__ import annotations

import json
import os
from datetime import timedelta, timezone

import psycopg
from psycopg.types.json import Jsonb
from langchain_core.messages import messages_from_dict, messages_to_dict


class ConversationStore:
    def __init__(self, owner_token: str):
        self.owner_token = owner_token

    def _connect(self):
        return psycopg.connect(
            host=os.getenv("PGVECTOR_HOST", "127.0.0.1"),
            port=int(os.getenv("PGVECTOR_PORT", "5432")),
            dbname=os.getenv("PGVECTOR_DB", "langchain"),
            user=os.getenv("PGVECTOR_USER", "langchain"),
            password=os.getenv("PGVECTOR_PASSWORD", "langchain"),
            connect_timeout=3,
        )

    def initialize(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_threads (
                    id TEXT PRIMARY KEY,
                    owner_token TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    thread_id TEXT NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
                    position INTEGER NOT NULL,
                    payload JSONB NOT NULL,
                    PRIMARY KEY (thread_id, position)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS chat_threads_owner_updated_idx
                ON chat_threads (owner_token, updated_at DESC)
            """)

    def list_threads(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT id, title, created_at FROM chat_threads
                WHERE owner_token = %s ORDER BY updated_at DESC
            """, (self.owner_token,)).fetchall()
        jakarta_tz = timezone(timedelta(hours=7))
        return [{"id": thread_id, "title": title,
                 "created_at": created_at.astimezone(jakarta_tz).strftime("%H:%M"),
                 "tool_history": []} for thread_id, title, created_at in rows]

    def create_thread(self, thread_id: str, title: str):
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO chat_threads (id, owner_token, title) VALUES (%s, %s, %s)
            """, (thread_id, self.owner_token, title))

    def ensure_thread(self, thread_id: str, title: str):
        """Register a thread that predates database-backed conversation history."""
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO chat_threads (id, owner_token, title) VALUES (%s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (thread_id, self.owner_token, title))
            owner = conn.execute("SELECT owner_token FROM chat_threads WHERE id = %s",
                                 (thread_id,)).fetchone()
            if not owner or owner[0] != self.owner_token:
                raise ValueError("Identitas percakapan telah digunakan oleh sesi lain.")

    def rename_thread(self, thread_id: str, title: str):
        with self._connect() as conn:
            conn.execute("""
                UPDATE chat_threads SET title = %s, updated_at = now()
                WHERE id = %s AND owner_token = %s
            """, (title, thread_id, self.owner_token))

    def delete_thread(self, thread_id: str):
        with self._connect() as conn:
            conn.execute("""
                DELETE FROM chat_threads WHERE id = %s AND owner_token = %s
            """, (thread_id, self.owner_token))

    def load_messages(self, thread_id: str):
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT m.payload FROM chat_messages AS m
                JOIN chat_threads AS t ON t.id = m.thread_id
                WHERE t.id = %s AND t.owner_token = %s
                ORDER BY m.position
            """, (thread_id, self.owner_token)).fetchall()
        return messages_from_dict([row[0] for row in rows])

    def save_messages(self, thread_id: str, messages):
        # Serialize before opening the transaction so a malformed message
        # cannot replace a previously saved conversation.
        payloads = [Jsonb(json.loads(json.dumps(item, default=str, ensure_ascii=False)))
                    for item in messages_to_dict(messages)]
        with self._connect() as conn:
            exists = conn.execute("""
                SELECT 1 FROM chat_threads WHERE id = %s AND owner_token = %s FOR UPDATE
            """, (thread_id, self.owner_token)).fetchone()
            if not exists:
                raise ValueError("Percakapan tidak ditemukan untuk sesi ini.")
            conn.execute("DELETE FROM chat_messages WHERE thread_id = %s", (thread_id,))
            if payloads:
                with conn.cursor() as cur:
                    cur.executemany("""
                        INSERT INTO chat_messages (thread_id, position, payload)
                        VALUES (%s, %s, %s)
                    """, [(thread_id, index, payload) for index, payload in enumerate(payloads)])
            conn.execute("UPDATE chat_threads SET updated_at = now() WHERE id = %s", (thread_id,))
