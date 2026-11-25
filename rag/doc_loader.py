"""Index PDF/DOCX sources into the existing PostgreSQL and PGVector collection."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

import psycopg
from psycopg.conninfo import make_conninfo
from psycopg.types.json import Jsonb
from dotenv import load_dotenv
import config

from .source_reader import read_source, source_chunks

load_dotenv()
PGVECTOR_HOST = os.getenv("PGVECTOR_HOST", "127.0.0.1")
PGVECTOR_PORT = int(os.getenv("PGVECTOR_PORT", "5432"))
PGVECTOR_USER = os.getenv("PGVECTOR_USER", "langchain")
PGVECTOR_PASSWORD = os.getenv("PGVECTOR_PASSWORD", "langchain")
PGVECTOR_DB = os.getenv("PGVECTOR_DB", "langchain")


def default_connection():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        if db_url.startswith("postgres://"):
            return db_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif db_url.startswith("postgresql://"):
            return db_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return db_url
    from sqlalchemy import URL
    return URL.create("postgresql+psycopg", username=PGVECTOR_USER, password=PGVECTOR_PASSWORD,
                      host=PGVECTOR_HOST, port=PGVECTOR_PORT, database=PGVECTOR_DB).render_as_string(hide_password=False)


PGVECTOR_CONNECTION = default_connection()


def _connect(connection):
    from sqlalchemy.engine import make_url
    url = make_url(connection)
    return psycopg.connect(
        host=url.host or PGVECTOR_HOST,
        port=url.port or PGVECTOR_PORT,
        dbname=url.database or PGVECTOR_DB,
        user=url.username or PGVECTOR_USER,
        password=url.password or PGVECTOR_PASSWORD,
        connect_timeout=10,
    )


def _initialize(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS documents (id UUID PRIMARY KEY, title TEXT NOT NULL, full_content TEXT NOT NULL)")
    for column, definition in {
        "source_path": "TEXT", "source_sha256": "TEXT", "file_format": "TEXT",
        "structure": "JSONB", "collection_name": "TEXT DEFAULT 'knowledge_base'",
        "is_active": "BOOLEAN NOT NULL DEFAULT TRUE", "indexed_at": "TIMESTAMPTZ DEFAULT now()",
    }.items():
        conn.execute(f"ALTER TABLE documents ADD COLUMN IF NOT EXISTS {column} {definition}")
    conn.commit()


def loader(file_path="./data", connection=PGVECTOR_CONNECTION, *, collection_name="knowledge_base",
           embeddings=None, vector_store=None):
    """Return a per-file report; unchanged files are skipped and failures are isolated."""
    root = Path(file_path).resolve()
    paths = [p for p in sorted(root.iterdir()) if p.is_file() and p.suffix.lower() in {".pdf", ".docx"}
             and not p.name.startswith("~$")] if root.is_dir() else []
    report = {"indexed": [], "skipped": [], "failed": [], "collection": collection_name}
    if not paths:
        return report
    if vector_store is None:
        from langchain_postgres import PGVector
        if embeddings is None:
            from langchain_huggingface import HuggingFaceEmbeddings
            embeddings = HuggingFaceEmbeddings(model_name=config.EMBEDDING_MODEL)
        vector_store = PGVector(embeddings=embeddings, collection_name=collection_name, connection=connection)
    with _connect(connection) as conn:
        _initialize(conn)
        for path in paths:
            ids = []
            try:
                raw_hash = hashlib.sha256(path.read_bytes()).hexdigest()
                # Dedup berdasarkan isi, bukan path: dokumen yang sama bisa di-index dari mesin lain
                # (mis. path Windows di laptop vs /app/data di container) dan tidak boleh tersimpan dobel.
                existing = conn.execute("""
                    SELECT id FROM documents WHERE source_sha256 = %s
                    AND collection_name = %s AND is_active
                """, (raw_hash, collection_name)).fetchone()
                if existing:
                    report["skipped"].append({"filename": path.name, "reason": "isi belum berubah"})
                    continue
                structure = read_source(path)
                chunks = [(text, metadata) for text, metadata in source_chunks({"path": str(path)}, structure) if text.strip()]
                if not chunks:
                    raise ValueError("Tidak ada teks yang dapat diindeks; periksa sumber/OCR.")
                doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{collection_name}:{path}:{raw_hash}"))
                ids = [str(uuid.uuid5(uuid.UUID(doc_id), str(index))) for index in range(len(chunks))]
                year = re.search(r"(?<!\d)(?:19|20)\d{2}(?!\d)", path.name)
                version = re.search(r"\b(?:rev(?:isi)?|versi|v)[ ._-]*(\d+)\b", path.name, re.I)
                base = {"document_id": doc_id, "file_name": path.name, "source_id": raw_hash[:24],
                        "source_sha256": raw_hash, "document_type": "RKS" if "rks" in path.name.lower() else "lainnya",
                        **({"year": int(year[0])} if year else {}),
                        **({"version": version[1]} if version else {})}
                vector_store.add_texts(texts=[text for text, _ in chunks],
                                       metadatas=[{**base, **metadata} for _, metadata in chunks], ids=ids)
                if hashlib.sha256(path.read_bytes()).hexdigest() != raw_hash:
                    raise ValueError("Sumber berubah saat diindeks; jalankan ulang.")
                # Versi lama dicari lewat path ATAU nama file, agar file yang diperbarui dari path lain
                # (laptop vs container) tidak meninggalkan versi lama yang masih aktif.
                previous = conn.execute("""
                    SELECT id FROM documents WHERE collection_name = %s AND is_active AND
                    (source_path = %s OR title = %s) AND id <> %s
                """, (collection_name, str(path), path.name, doc_id)).fetchall()
                for (old_id,) in previous:
                    conn.execute("""
                        DELETE FROM langchain_pg_embedding e USING langchain_pg_collection c
                        WHERE e.collection_id = c.uuid AND c.name = %s AND e.cmetadata->>'document_id' = %s
                    """, (collection_name, str(old_id)))
                    conn.execute("UPDATE documents SET is_active = FALSE WHERE id = %s", (old_id,))
                full_text = "\n".join(block["text"] for block in structure["blocks"])
                conn.execute("""
                    INSERT INTO documents (id, title, full_content, source_path, source_sha256,
                        file_format, structure, collection_name, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                    ON CONFLICT (id) DO UPDATE SET full_content = EXCLUDED.full_content,
                        structure = EXCLUDED.structure, is_active = TRUE, indexed_at = now()
                """, (doc_id, path.name, full_text, str(path), raw_hash, structure["format"], Jsonb(structure), collection_name))
                conn.commit()
                report["indexed"].append({"filename": path.name, "document_id": doc_id,
                                           "chunks": len(chunks), "issues": structure["issues"]})
            except Exception as exc:
                conn.rollback()
                if ids:
                    try:
                        vector_store.delete(ids=ids)
                    except Exception:
                        pass
                report["failed"].append({"filename": path.name, "error": str(exc)})
    return report


def list_active_documents(connection=PGVECTOR_CONNECTION, collection_name="knowledge_base") -> list[dict]:
    """Returns a list of all active documents in the PostgreSQL knowledge base."""
    with _connect(connection) as conn:
        _initialize(conn)
        rows = conn.execute("""
            SELECT id, title, source_path, file_format, indexed_at
            FROM documents
            WHERE collection_name = %s AND is_active
            ORDER BY title ASC
        """, (collection_name,)).fetchall()
        return [
            {
                "id": str(r[0]),
                "title": r[1],
                "source_path": r[2],
                "file_format": r[3],
                "indexed_at": r[4].isoformat() if r[4] else None,
            }
            for r in rows
        ]


def delete_document(target: str, connection=PGVECTOR_CONNECTION, collection_name="knowledge_base", purge: bool = False) -> dict:
    """
    Deactivates or permanently removes a document and its vector embeddings.
    target can be a filename, source_path, or document UUID.
    If purge=True, the row is deleted from the documents table completely.
    """
    with _connect(connection) as conn:
        _initialize(conn)
        rows = conn.execute("""
            SELECT id, title, source_path FROM documents
            WHERE collection_name = %s AND (
                id::text = %s OR title = %s OR source_path = %s OR source_path LIKE %s
            )
        """, (collection_name, target, target, target, f"%{target}")).fetchall()

        if not rows:
            return {"status": "not_found", "message": f"Dokumen '{target}' tidak ditemukan di koleksi '{collection_name}'."}

        deleted_summary = []
        for doc_id, title, source_path in rows:
            cur = conn.execute("""
                DELETE FROM langchain_pg_embedding e USING langchain_pg_collection c
                WHERE e.collection_id = c.uuid AND c.name = %s AND (
                    e.cmetadata->>'document_id' = %s OR e.cmetadata->>'file_name' = %s
                )
            """, (collection_name, str(doc_id), title))
            chunk_count = cur.rowcount

            if purge:
                conn.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
            else:
                conn.execute("UPDATE documents SET is_active = FALSE WHERE id = %s", (doc_id,))

            deleted_summary.append({
                "id": str(doc_id),
                "title": title,
                "deleted_embedding_chunks": chunk_count,
                "action": "purged" if purge else "deactivated"
            })

        conn.commit()
        return {
            "status": "success",
            "collection": collection_name,
            "affected_count": len(deleted_summary),
            "documents": deleted_summary
        }


def main():
    parser = argparse.ArgumentParser(description="Indeks dan kelola knowledge base PDF/DOCX.")
    parser.add_argument("directory", nargs="?", default="./data", help="Direktori berisi file PDF/DOCX untuk diindeks (default: ./data)")
    parser.add_argument("--collection", default="knowledge_base", help="Nama koleksi PGVector (default: knowledge_base)")
    parser.add_argument("--list", action="store_true", help="Tampilkan daftar semua dokumen yang aktif di knowledge base")
    parser.add_argument("--delete", metavar="TARGET", help="Hapus atau nonaktifkan dokumen berdasarkan nama file, path, atau UUID")
    parser.add_argument("--purge", action="store_true", help="Hapus record dari database permanen (digunakan bersama --delete)")

    args = parser.parse_args()

    if args.list:
        docs = list_active_documents(collection_name=args.collection)
        print(json.dumps({"total": len(docs), "documents": docs}, ensure_ascii=False, indent=2))
        return

    if args.delete:
        result = delete_document(args.delete, collection_name=args.collection, purge=args.purge)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    report = loader(args.directory, collection_name=args.collection)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
