"""PostgreSQL archive for editable contract drafts generated from tender Bagian B."""
from __future__ import annotations

import hashlib
import os
import re
from uuid import uuid4

import psycopg


LOCAL_OWNER = "local_single_user"  # Replace with authenticated identity when enabling multiple users.


def initialize_contract_archive(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contract_drafts (
            id TEXT PRIMARY KEY,
            owner_token TEXT NOT NULL,
            rks_artifact_id TEXT,
            project_name TEXT NOT NULL,
            tender_filename TEXT NOT NULL,
            tender_sha256 TEXT NOT NULL,
            contract_filename TEXT NOT NULL,
            contract_sha256 TEXT NOT NULL,
            contract_docx BYTEA NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS contract_drafts_owner_created_idx
        ON contract_drafts (owner_token, created_at DESC)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS contract_drafts_rks_idx
        ON contract_drafts (rks_artifact_id) WHERE rks_artifact_id IS NOT NULL
    """)


class ContractArchive:
    def __init__(self, owner_token: str = LOCAL_OWNER):
        self.owner_token = owner_token

    def _connect(self):
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            return psycopg.connect(db_url, connect_timeout=10)
        return psycopg.connect(
            host=os.getenv("PGVECTOR_HOST", "127.0.0.1"),
            port=int(os.getenv("PGVECTOR_PORT", "5432")),
            dbname=os.getenv("PGVECTOR_DB", "langchain"),
            user=os.getenv("PGVECTOR_USER", "langchain"),
            password=os.getenv("PGVECTOR_PASSWORD", "langchain"),
            connect_timeout=10,
        )

    def initialize(self) -> None:
        with self._connect() as conn:
            initialize_contract_archive(conn)

    def save(self, *, project_name: str, tender_filename: str, tender_sha256: str,
             contract_docx: bytes, rks_artifact_id: str | None = None) -> str:
        """Save a snapshot; later changes to the tender file cannot alter it."""
        if not project_name.strip() or not contract_docx or not re.fullmatch(r"[0-9a-f]{64}", tender_sha256):
            raise ValueError("Data rancangan kontrak tidak lengkap.")
        if rks_artifact_id and not re.fullmatch(r"[0-9a-f]{32}", rks_artifact_id):
            raise ValueError("ID RKS tidak valid.")
        contract_id = uuid4().hex
        contract_filename = f"Rancangan_Kontrak_{contract_id[:8]}.docx"
        with self._connect() as conn:
            initialize_contract_archive(conn)
            conn.execute("""
                INSERT INTO contract_drafts
                (id, owner_token, rks_artifact_id, project_name, tender_filename,
                 tender_sha256, contract_filename, contract_sha256, contract_docx)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (contract_id, self.owner_token, rks_artifact_id, project_name.strip(),
                  tender_filename, tender_sha256, contract_filename,
                  hashlib.sha256(contract_docx).hexdigest(), contract_docx))
        return contract_id

    def list(self, limit: int = 500) -> list[dict]:
        with self._connect() as conn:
            initialize_contract_archive(conn)
            rows = conn.execute("""
                SELECT id, rks_artifact_id, project_name, tender_filename,
                       contract_filename, status, created_at, octet_length(contract_docx)
                FROM contract_drafts WHERE owner_token = %s
                ORDER BY created_at DESC, id DESC LIMIT %s
            """, (self.owner_token, max(1, min(limit, 500)))).fetchall()
        return [{"id": row[0], "rks_artifact_id": row[1], "project_name": row[2],
                 "tender_filename": row[3], "contract_filename": row[4],
                 "status": row[5], "created_at": row[6].isoformat(), "size": row[7]}
                for row in rows]

    def get(self, contract_id: str) -> dict:
        if not re.fullmatch(r"[0-9a-f]{32}", contract_id):
            raise ValueError("ID rancangan kontrak tidak valid.")
        with self._connect() as conn:
            row = conn.execute("""
                SELECT project_name, rks_artifact_id, tender_filename,
                       tender_sha256, contract_filename, contract_sha256,
                       contract_docx, status, created_at
                FROM contract_drafts WHERE id = %s AND owner_token = %s
            """, (contract_id, self.owner_token)).fetchone()
        if not row:
            raise KeyError("Rancangan kontrak tidak ditemukan.")
        docx = bytes(row[6])
        if hashlib.sha256(docx).hexdigest() != row[5]:
            raise ValueError("Isi rancangan kontrak berubah dan tidak cocok dengan hash arsip.")
        return {"id": contract_id, "project_name": row[0], "rks_artifact_id": row[1],
                "tender_filename": row[2], "tender_sha256": row[3],
                "contract_filename": row[4], "contract_sha256": row[5],
                "docx": docx, "status": row[7], "created_at": row[8].isoformat()}
