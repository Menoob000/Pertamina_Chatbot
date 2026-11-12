"""Two-way smart delta synchronization between Google Drive and PostgreSQL."""
from __future__ import annotations

import io
import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import psycopg
from googleapiclient.http import MediaIoBaseDownload

from .auth import get_drive_service, get_auth_status
from rag.doc_loader import loader, _connect, PGVECTOR_CONNECTION

CONFIG_PATH = Path("gdrive_config.json")
MANIFEST_PATH = Path("gdrive_sync_manifest.json")


def load_gdrive_config() -> Dict[str, Any]:
    """Load persisted Google Drive settings (folder ID, last sync timestamp)."""
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"folder_id": "", "last_sync": None, "total_synced_files": 0}


def save_gdrive_config(config: Dict[str, Any]) -> None:
    """Save Google Drive settings to local config file."""
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_manifest() -> Dict[str, Any]:
    """Load manifest tracking file_id -> {name, md5, local_path, modified_time}."""
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_manifest(manifest: Dict[str, Any]) -> None:
    """Save manifest tracking file_id -> {name, md5, local_path, modified_time}."""
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def delete_document_from_postgres(file_name: str, connection=PGVECTOR_CONNECTION, collection_name="knowledge_base") -> None:
    """Purge vectors and mark document as inactive in PostgreSQL when removed from Google Drive."""
    try:
        with _connect(connection) as conn:
            # Delete embeddings associated with this file_name
            conn.execute("""
                DELETE FROM langchain_pg_embedding e USING langchain_pg_collection c
                WHERE e.collection_id = c.uuid AND c.name = %s
                AND (e.cmetadata->>'file_name' = %s OR e.cmetadata->>'source_path' LIKE %s)
            """, (collection_name, file_name, f"%{file_name}%"))
            # Deactivate document record
            conn.execute("""
                UPDATE documents SET is_active = FALSE
                WHERE title = %s OR source_path LIKE %s
            """, (file_name, f"%{file_name}%"))
            conn.commit()
    except Exception as exc:
        print(f"Warning: Failed to purge deleted file '{file_name}' from DB: {exc}")


def _list_all_files_recursive(service, root_folder_id: str) -> Dict[str, Dict[str, Any]]:
    """
    Recursively scans root_folder_id and any subfolders (e.g. 'RKS', 'Amandemen').
    Returns a dict mapping file_id -> file metadata dict including 'category' and 'folder_rel_path'.
    """
    remote_files = {}
    queue = [(root_folder_id, "")]  # (folder_id, relative_path)

    while queue:
        current_id, current_rel = queue.pop(0)

        # 1. Look for subfolders
        folder_query = f"'{current_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        page_token = None
        while True:
            resp = service.files().list(
                q=folder_query,
                spaces="drive",
                fields="nextPageToken, files(id, name)",
                pageToken=page_token,
                pageSize=100,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            ).execute()
            for sub in resp.get("files", []):
                sub_path = f"{current_rel}/{sub['name']}".strip("/")
                queue.append((sub["id"], sub_path))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        # 2. Look for PDF files in this folder
        file_query = f"'{current_id}' in parents and mimeType = 'application/pdf' and trashed = false"
        page_token = None
        while True:
            resp = service.files().list(
                q=file_query,
                spaces="drive",
                fields="nextPageToken, files(id, name, modifiedTime, md5Checksum, size)",
                pageToken=page_token,
                pageSize=100,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            ).execute()
            for f in resp.get("files", []):
                # Categorize based on folder name or filename
                lower_path = current_rel.lower()
                lower_name = f["name"].lower()
                if "amandemen" in lower_path or "amendment" in lower_path or "amandemen" in lower_name:
                    category = "Amandemen"
                else:
                    category = "RKS"

                f["folder_rel_path"] = current_rel
                f["category"] = category
                remote_files[f["id"]] = f
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

    return remote_files


def sync_google_drive(
    folder_id: str,
    target_dir: str = "./data",
    collection_name: str = "knowledge_base",
    service=None,
) -> Dict[str, Any]:
    """
    Synchronize PDF documents from Google Drive folder (and subfolders like RKS/ or Amandemen/)
    to local target_dir and PostgreSQL.
    Performs smart delta sync:
      - Recursive subfolders: Scans 'RKS', 'Amandemen', or custom subfolders.
      - New files: Downloaded & ingested into PostgreSQL.
      - Modified files (by MD5): Re-downloaded & re-indexed in vector store.
      - Deleted files: Removed from local directory and purged from PostgreSQL.
      - Unchanged files: Skipped to save API quotas and embedding costs.
    """
    clean_folder_id = folder_id.strip()
    if not clean_folder_id:
        return {"success": False, "message": "Folder ID Google Drive tidak boleh kosong."}

    # Extract ID if user pasted full URL (e.g., https://drive.google.com/drive/folders/1a2B3c...)
    if "folders/" in clean_folder_id:
        clean_folder_id = clean_folder_id.split("folders/")[-1].split("?")[0].split("/")[0]

    if service is None:
        service = get_drive_service(interactive=False)
        if not service:
            return {
                "success": False,
                "message": "Akun Google belum terhubung atau token kadaluarsa. Silakan lakukan otorisasi terlebih dahulu.",
            }

    dest_path = Path(target_dir)
    dest_path.mkdir(parents=True, exist_ok=True)
    amend_dest_path = dest_path / "amendments"
    amend_dest_path.mkdir(parents=True, exist_ok=True)

    # 1. Fetch remote file list recursively (supporting subfolders like RKS and Amandemen)
    try:
        remote_files = _list_all_files_recursive(service, clean_folder_id)
    except Exception as e:
        return {"success": False, "message": f"Gagal membaca folder Google Drive: {str(e)}"}

    manifest = _load_manifest()

    downloaded = []
    updated = []
    skipped = []
    deleted = []

    # 2. Process Remote Files (New & Modified)
    for f_id, f_meta in remote_files.items():
        fname = f_meta["name"]
        remote_md5 = f_meta.get("md5Checksum", "")
        local_file = dest_path / fname

        is_new = f_id not in manifest or not local_file.exists()
        is_modified = False

        if not is_new:
            # Check if MD5 or local file changed
            cached_md5 = manifest[f_id].get("md5", "")
            if remote_md5 and cached_md5 != remote_md5:
                is_modified = True
            elif local_file.exists():
                local_md5 = hashlib.md5(local_file.read_bytes()).hexdigest()
                if remote_md5 and local_md5 != remote_md5:
                    is_modified = True

        if is_new or is_modified:
            # Download file stream
            try:
                request = service.files().get_media(fileId=f_id, supportsAllDrives=True)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

                content = fh.getvalue()
                local_file.write_bytes(content)

                manifest[f_id] = {
                    "name": fname,
                    "md5": remote_md5 or hashlib.md5(content).hexdigest(),
                    "local_path": str(local_file),
                    "modified_time": f_meta.get("modifiedTime"),
                    "synced_at": datetime.now().isoformat(),
                }

                if is_new:
                    downloaded.append(fname)
                else:
                    updated.append(fname)
            except Exception as dl_err:
                print(f"Error downloading {fname}: {dl_err}")
        else:
            skipped.append(fname)

    # 3. Detect and Purge Deleted Files
    known_fids = list(manifest.keys())
    for f_id in known_fids:
        if f_id not in remote_files:
            tracked = manifest[f_id]
            del_name = tracked.get("name")
            del_local = Path(tracked.get("local_path", ""))

            # Remove local file if present
            if del_local.exists():
                try:
                    del_local.unlink()
                except Exception:
                    pass

            # Purge from PostgreSQL
            if del_name:
                delete_document_from_postgres(del_name, collection_name=collection_name)
                deleted.append(del_name)

            del manifest[f_id]

    # Save manifest
    _save_manifest(manifest)

    # 4. Ingest new & modified PDFs into PostgreSQL Vector Store
    indexed_report = {"indexed": [], "failed": []}
    if downloaded or updated:
        try:
            indexed_report = loader(file_path=str(dest_path), collection_name=collection_name)
        except Exception as load_err:
            print(f"Indexing error: {load_err}")

    # 5. Update local config
    now_str = datetime.now().strftime("%d %b %Y, %H:%M WIB")
    cfg = load_gdrive_config()
    cfg["folder_id"] = clean_folder_id
    cfg["last_sync"] = now_str
    cfg["total_synced_files"] = len(remote_files)
    save_gdrive_config(cfg)

    return {
        "success": True,
        "folder_id": clean_folder_id,
        "downloaded": downloaded,
        "updated": updated,
        "deleted": deleted,
        "skipped": skipped,
        "indexed": [x["filename"] for x in indexed_report.get("indexed", [])],
        "failed_index": [x["filename"] for x in indexed_report.get("failed", [])],
        "total_remote": len(remote_files),
        "timestamp": now_str,
        "message": (
            f"Sinkronisasi selesai! "
            f"{len(downloaded)} file baru diunduh, {len(updated)} file diperbarui, "
            f"{len(deleted)} file dihapus, {len(skipped)} file tidak berubah."
        ),
    }
