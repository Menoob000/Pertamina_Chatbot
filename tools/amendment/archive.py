"""PostgreSQL archive for generated contract amendment documents."""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from uuid import uuid4

import psycopg

LOCAL_OWNER = "local_single_user"


def initialize_amendment_archive(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS amendment_drafts (
            id TEXT PRIMARY KEY,
            owner_token TEXT NOT NULL,
            contract_draft_id TEXT,
            project_name TEXT NOT NULL,
            amendment_level TEXT NOT NULL,
            amendment_filename TEXT NOT NULL,
            amendment_sha256 TEXT NOT NULL,
            amendment_docx BYTEA NOT NULL,
            metadata JSONB,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS amendment_drafts_owner_created_idx
        ON amendment_drafts (owner_token, created_at DESC)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS amendment_drafts_contract_idx
        ON amendment_drafts (contract_draft_id) WHERE contract_draft_id IS NOT NULL
    """)


class AmendmentArchive:
    def __init__(self, owner_token: str = LOCAL_OWNER):
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

    def initialize(self) -> None:
        with self._connect() as conn:
            initialize_amendment_archive(conn)

    def save(
        self,
        *,
        project_name: str,
        amendment_level: str,
        amendment_docx: bytes,
        contract_draft_id: str | None = None,
        custom_filename: str | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Save an amendment snapshot to DB and write a copy to ./output/amendments."""
        if not project_name.strip() or not amendment_docx:
            raise ValueError("Data amandemen tidak lengkap.")

        amendment_id = uuid4().hex
        clean_proj = re.sub(r"[^\w\s-]", "", project_name).strip()[:30].replace(" ", "_")
        clean_lvl = amendment_level.replace(" ", "_")
        filename = custom_filename or f"{clean_lvl}_{clean_proj}_{amendment_id[:8]}.docx"
        sha256 = hashlib.sha256(amendment_docx).hexdigest()

        # Save to PostgreSQL
        with self._connect() as conn:
            initialize_amendment_archive(conn)
            import json
            meta_json = json.dumps(metadata or {})
            conn.execute("""
                INSERT INTO amendment_drafts
                (id, owner_token, contract_draft_id, project_name, amendment_level,
                 amendment_filename, amendment_sha256, amendment_docx, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (amendment_id, self.owner_token, contract_draft_id, project_name.strip(),
                  amendment_level, filename, sha256, amendment_docx, meta_json))

        # Save copy to ./output/amendments
        try:
            out_dir = Path("./output/amendments")
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / filename).write_bytes(amendment_docx)
            # Also to ./output for generic download viewers
            Path("./output").mkdir(parents=True, exist_ok=True)
            (Path("./output") / filename).write_bytes(amendment_docx)
        except Exception:
            pass

        return amendment_id

    def list(self, limit: int = 500) -> list[dict]:
        with self._connect() as conn:
            initialize_amendment_archive(conn)
            rows = conn.execute("""
                SELECT id, contract_draft_id, project_name, amendment_level,
                       amendment_filename, status, created_at, octet_length(amendment_docx)
                FROM amendment_drafts WHERE owner_token = %s
                ORDER BY created_at DESC, id DESC LIMIT %s
            """, (self.owner_token, max(1, min(limit, 500)))).fetchall()
        return [
            {
                "id": row[0],
                "contract_draft_id": row[1],
                "project_name": row[2],
                "amendment_level": row[3],
                "amendment_filename": row[4],
                "status": row[5],
                "created_at": row[6].isoformat(),
                "size": row[7],
            }
            for row in rows
        ]

    def get(self, amendment_id: str) -> dict:
        if not re.fullmatch(r"[0-9a-f]{32}", amendment_id):
            raise ValueError("ID amandemen tidak valid.")
        with self._connect() as conn:
            row = conn.execute("""
                SELECT project_name, contract_draft_id, amendment_level,
                       amendment_filename, amendment_sha256, amendment_docx,
                       metadata, status, created_at
                FROM amendment_drafts WHERE id = %s AND owner_token = %s
            """, (amendment_id, self.owner_token)).fetchone()
        if not row:
            raise KeyError("Dokumen amandemen tidak ditemukan.")
        docx = bytes(row[5])
        if hashlib.sha256(docx).hexdigest() != row[4]:
            raise ValueError("Isi dokumen amandemen berubah dan tidak cocok dengan hash arsip.")
        return {
            "id": amendment_id,
            "project_name": row[0],
            "contract_draft_id": row[1],
            "amendment_level": row[2],
            "amendment_filename": row[3],
            "amendment_sha256": row[4],
            "docx": docx,
            "metadata": row[6] or {},
            "status": row[7],
            "created_at": row[8].isoformat(),
        }
