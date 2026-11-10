"""Archive Bagian B from an existing generated tender without running the LLM again."""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from tools.rks.service import artifact_file, list_documents
from tools.tender.contract_archive import ContractArchive


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"


def contract_from_tender(docx_data: bytes) -> bytes:
    """Retain the original Word package and remove content before its Bagian B divider."""
    document = Document(BytesIO(docx_data))
    body = document.element.body
    children = list(body)
    divider = next((index for index, child in enumerate(children)
                    if child.tag == qn("w:tbl") and
                    "BAGIAN BRANCANGAN KONTRAK" in "".join(
                        run.text or "" for run in child.iter(qn("w:t")))[:100]), None)
    if divider is None:
        raise ValueError("Pembatas BAGIAN B - RANCANGAN KONTRAK tidak ditemukan di DOCX tender.")
    for element in children[:divider]:
        body.remove(element)
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def archive_existing(tender_path: Path, project_name: str, rks_artifact_id: str | None) -> str:
    tender_path = tender_path.resolve()
    if not tender_path.is_relative_to(OUTPUT.resolve()) or tender_path.suffix.lower() != ".docx":
        raise ValueError("File tender harus berupa DOCX di folder output proyek.")
    tender_data = tender_path.read_bytes()
    tender_hash = hashlib.sha256(tender_data).hexdigest()
    if rks_artifact_id:
        artifact_file(rks_artifact_id, "docx")
        matches = [item for item in list_documents(limit=500)
                   if item["artifact_id"] == rks_artifact_id]
        if not matches or not any(entry["filename"] == tender_path.name
                                  for entry in matches[0].get("related_documents") or []):
            raise ValueError("File tender tidak tercatat sebagai dokumen terkait pada RKS tersebut.")
    archive = ContractArchive()
    with archive._connect() as conn:
        existing = conn.execute("""
            SELECT id FROM contract_drafts
            WHERE owner_token = %s AND tender_sha256 = %s
              AND rks_artifact_id IS NOT DISTINCT FROM %s
            ORDER BY created_at DESC LIMIT 1
        """, (archive.owner_token, tender_hash, rks_artifact_id)).fetchone()
    if existing:
        return existing[0]
    contract_data = contract_from_tender(tender_data)
    return archive.save(project_name=project_name, tender_filename=tender_path.name,
                        tender_sha256=tender_hash, contract_docx=contract_data,
                        rks_artifact_id=rks_artifact_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tender", type=Path, required=True)
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--rks-artifact-id")
    args = parser.parse_args()
    print(archive_existing(args.tender, args.project_name, args.rks_artifact_id))
