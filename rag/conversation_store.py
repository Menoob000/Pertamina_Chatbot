"""PostgreSQL persistence for Streamlit conversations and LangGraph messages."""
from __future__ import annotations

import json
import os
from datetime import timedelta, timezone

import psycopg
from psycopg.types.json import Jsonb
from langchain_core.messages import messages_from_dict, messages_to_dict


class ConversationStore:
    def __init__(self, owner_token: str, single_user: bool = False):
        self.owner_token = owner_token
        self.single_user = single_user

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
            from tools.tender.contract_archive import initialize_contract_archive
            initialize_contract_archive(conn)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_users (
                    id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
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
                CREATE TABLE IF NOT EXISTS tender_drafts (
                    thread_id TEXT PRIMARY KEY REFERENCES chat_threads(id) ON DELETE CASCADE,
                    payload JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_officials (
                    id BIGSERIAL PRIMARY KEY,
                    owner_token TEXT NOT NULL,
                    project_key TEXT NOT NULL,
                    rks_artifact_id TEXT,
                    role TEXT NOT NULL,
                    name TEXT NOT NULL DEFAULT '',
                    position TEXT NOT NULL DEFAULT '',
                    organization_unit TEXT NOT NULL DEFAULT '',
                    source_type TEXT NOT NULL,
                    source_location JSONB NOT NULL DEFAULT '[]',
                    payload JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(owner_token, project_key, role)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_official_history (
                    id BIGSERIAL PRIMARY KEY,
                    official_id BIGINT NOT NULL REFERENCES project_officials(id),
                    payload JSONB NOT NULL,
                    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS chat_threads_owner_updated_idx
                ON chat_threads (owner_token, updated_at DESC)
            """)
            conn.execute("""
                INSERT INTO chat_users (id, display_name)
                SELECT DISTINCT owner_token, 'Pengguna lama' FROM chat_threads
                ON CONFLICT (id) DO NOTHING
            """)
            conn.execute("""
                INSERT INTO chat_users (id, display_name) VALUES (%s, %s)
                ON CONFLICT (id) DO UPDATE SET last_seen_at = now()
            """, (self.owner_token, "Pengguna lokal" if self.single_user else "Pengguna anonim"))

    def list_threads(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT id, title, created_at FROM chat_threads
                WHERE (%s OR owner_token = %s) ORDER BY updated_at DESC
            """, (self.single_user, self.owner_token)).fetchall()
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
            if not owner or (not self.single_user and owner[0] != self.owner_token):
                raise ValueError("Identitas percakapan telah digunakan oleh sesi lain.")

    def rename_thread(self, thread_id: str, title: str):
        with self._connect() as conn:
            conn.execute("""
                UPDATE chat_threads SET title = %s, updated_at = now()
                WHERE id = %s AND (%s OR owner_token = %s)
            """, (title, thread_id, self.single_user, self.owner_token))

    def delete_thread(self, thread_id: str):
        with self._connect() as conn:
            conn.execute("""
                DELETE FROM chat_threads WHERE id = %s AND (%s OR owner_token = %s)
            """, (thread_id, self.single_user, self.owner_token))

    def load_messages(self, thread_id: str):
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT m.payload FROM chat_messages AS m
                JOIN chat_threads AS t ON t.id = m.thread_id
                WHERE t.id = %s AND (%s OR t.owner_token = %s)
                ORDER BY m.position
            """, (thread_id, self.single_user, self.owner_token)).fetchall()
        return messages_from_dict([row[0] for row in rows])

    def save_messages(self, thread_id: str, messages):
        # Serialize before opening the transaction so a malformed message
        # cannot replace a previously saved conversation.
        payloads = [Jsonb(json.loads(json.dumps(item, default=str, ensure_ascii=False)))
                    for item in messages_to_dict(messages)]
        with self._connect() as conn:
            exists = conn.execute("""
                SELECT 1 FROM chat_threads WHERE id = %s AND (%s OR owner_token = %s) FOR UPDATE
            """, (thread_id, self.single_user, self.owner_token)).fetchone()
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

    def load_tender_draft(self, thread_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("""
                SELECT d.payload FROM tender_drafts AS d
                JOIN chat_threads AS t ON t.id = d.thread_id
                WHERE d.thread_id = %s AND (%s OR t.owner_token = %s)
            """, (thread_id, self.single_user, self.owner_token)).fetchone()
        return row[0] if row else None

    def save_tender_draft(self, thread_id: str, payload: dict) -> None:
        with self._connect() as conn:
            owner = conn.execute("""
                SELECT 1 FROM chat_threads
                WHERE id = %s AND (%s OR owner_token = %s)
            """, (thread_id, self.single_user, self.owner_token)).fetchone()
            if not owner:
                raise ValueError("Percakapan tidak ditemukan untuk menyimpan draf tender.")
            conn.execute("""
                INSERT INTO tender_drafts (thread_id, payload) VALUES (%s, %s)
                ON CONFLICT (thread_id) DO UPDATE
                SET payload = EXCLUDED.payload, updated_at = now()
            """, (thread_id, Jsonb(payload)))

    def load_project_officials(self, project_key: str) -> dict:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT role, payload FROM project_officials
                WHERE owner_token = %s AND project_key = %s
            """, (self.owner_token, project_key)).fetchall()
        return dict(rows)

    def save_project_officials(self, project_key: str, officials: dict) -> None:
        from tools.tender.officers import ROLES

        if not project_key or len(project_key) > 100:
            raise ValueError("Identitas proyek pejabat tidak valid.")
        artifact_id = project_key[4:] if project_key.startswith("rks:") else None
        with self._connect() as conn:
            for role in ROLES:
                official = officials.get(role) or {}
                previous = conn.execute("""
                    SELECT id, payload FROM project_officials
                    WHERE owner_token = %s AND project_key = %s AND role = %s FOR UPDATE
                """, (self.owner_token, project_key, role)).fetchone()
                if previous and previous[1] == official:
                    continue
                sources = set((official.get("field_sources") or {}).values())
                origin = "user" if "user" in sources else "rks" if "rks" in sources else "placeholder"
                row = conn.execute("""
                    INSERT INTO project_officials
                    (owner_token, project_key, rks_artifact_id, role, name, position,
                     organization_unit, source_type, source_location, payload)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (owner_token, project_key, role) DO UPDATE SET
                    name = EXCLUDED.name, position = EXCLUDED.position,
                    organization_unit = EXCLUDED.organization_unit,
                    source_type = EXCLUDED.source_type, source_location = EXCLUDED.source_location,
                    payload = EXCLUDED.payload, updated_at = now()
                    RETURNING id
                """, (self.owner_token, project_key, artifact_id, role,
                      official.get("name") or "", official.get("position") or "",
                      official.get("organization_unit") or "", origin,
                      Jsonb(official.get("evidence") or []), Jsonb(official))).fetchone()
                conn.execute("""
                    INSERT INTO project_official_history (official_id, payload) VALUES (%s, %s)
                """, (row[0], Jsonb(official)))
