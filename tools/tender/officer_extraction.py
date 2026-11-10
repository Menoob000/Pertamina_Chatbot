"""Extract explicitly labelled RKS officials with locations; never infer signers."""
from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

import docx
from docx.table import Table
from docx.text.paragraph import Paragraph
import pymupdf

from .officers import empty_officials


_ROLE = r"(?P<role>pejabat\s+procurement|pejabat\s+pengadaan|pejabat\s+berwenang|pengawas\s+pekerjaan(?:\s*/\s*wakil\s+perusahaan)?)"
_LABEL = re.compile(r"^(?:\d+[.)]?\s+)?(?:(?P<field>nama|jabatan|unit(?:\s+organisasi)?|fungsi)\s+)?" + _ROLE + r"\s*(?::|\t)\s*(?P<value>.*)$", re.I)
_SUBLABEL = re.compile(r"^(nama|jabatan|unit(?:\s+organisasi)?|fungsi)\s*(?::|\t)\s*(.+)$", re.I)
_POSITION = re.compile(r"\b(manager|manajer|kepala|direktur|supervisor|pengawas|fungsi|chief|head|engineer|vice\s+president)\b", re.I)


def _read_blocks(raw: bytes, filename: str):
    if filename.lower().endswith(".pdf"):
        with pymupdf.open(stream=raw, filetype="pdf") as pdf:
            for number, page in enumerate(pdf, 1):
                for line in page.get_text(sort=True).splitlines():
                    yield line, f"halaman {number}"
    elif filename.lower().endswith(".docx"):
        document = docx.Document(io.BytesIO(raw))
        paragraph_number = table_number = 0
        for element in document.element.body.iterchildren():
            if element.tag.endswith("}p"):
                paragraph_number += 1
                yield Paragraph(element, document).text, f"paragraf {paragraph_number}"
            elif element.tag.endswith("}tbl"):
                table_number += 1
                for row_number, row in enumerate(Table(element, document).rows, 1):
                    cells, seen = [], set()
                    for cell in row.cells:
                        if cell._tc in seen:
                            continue
                        seen.add(cell._tc)
                        cells.append(cell.text.strip())
                    yield "\t".join(cells), f"tabel {table_number}, baris {row_number}"
    else:
        for number, line in enumerate(raw.decode("utf-8", errors="replace").splitlines(), 1):
            yield line, f"baris {number}"


def extract_officials(file_input, filename: str = "") -> dict:
    officials = empty_officials()
    issues = []
    if isinstance(file_input, (str, Path)):
        path = Path(file_input)
        filename = filename or path.name
        raw = path.read_bytes()
    else:
        raw = file_input.getvalue() if hasattr(file_input, "getvalue") else file_input
    project_key = "sha256:" + hashlib.sha256(raw).hexdigest()
    active_role = None
    active_location = None
    pending = None
    try:
        for block, location in _read_blocks(raw, filename):
            for line in block.splitlines():
                line = line.strip()
                match = _LABEL.match(line)
                if match:
                    pending = None
                    label = match["role"].lower()
                    role = ("procurement" if re.search(r"procurement|pengadaan", label) else
                            "authorized_officer" if "berwenang" in label else "work_supervisor")
                    value, field = match["value"].strip(" :\t"), (match["field"] or "").lower()
                    active_role, active_location = role, location
                    if not value:
                        pending = (role, field, line)
                        continue
                    nested = _SUBLABEL.match(value)
                    if nested:
                        field, value = nested[1].lower(), nested[2].strip()
                else:
                    sub = _SUBLABEL.match(line)
                    # Bind subordinate labels only within the same table row or adjacent labelled paragraph.
                    same_section = (location == active_location or
                                    (location.startswith("paragraf") and str(active_location).startswith("paragraf")))
                    if sub and active_role and same_section:
                        role, value, field = active_role, sub[2].strip(), sub[1].lower()
                        pending = None
                    elif pending and same_section:
                        role, field, label_line = pending
                        value = line
                        line = label_line + " " + line
                        pending = None
                    else:
                        active_role = None
                        pending = None
                        continue
                target = ("name" if field == "nama" else "position" if field == "jabatan" else
                          "organization_unit" if field.startswith("unit") or field == "fungsi" else
                          "position" if _POSITION.search(value) else "name")
                # Reject prose, placeholders, blank signature lines and ambiguous multi-cell values.
                if (len(value) > 120 or "\t" in value or re.search(r"[\[\]_:;!?]|\b(?:adalah|harus|wajib|ditunjuk|ditetapkan|bertanggung|sesuai|akan|sebagaimana)\b", value, re.I)
                        or not re.search(r"[A-Za-z]", value)):
                    continue
                if target == "name" and not field and (
                        len(value.split()) < 2 or re.search(r"\b(?:PT|perusahaan|pertamina|persero|kontraktor)\b", value, re.I)):
                    continue
                evidence = {"filename": filename, "location": location, "quote": line}
                candidate = {"field": target, "value": value, "source": evidence}
                if candidate not in officials[role]["candidates"]:
                    officials[role]["candidates"].append(candidate)
                officials[role]["evidence"].append(evidence)
                if not officials[role][target]:
                    officials[role][target] = value
                    officials[role]["field_sources"][target] = "rks"
                elif officials[role][target] != value:
                    officials[role][target] = ""
                    officials[role]["field_sources"][target] = "ambiguous"
        for role, official in officials.items():
            for field in ("name", "position", "organization_unit"):
                candidates = {c["value"] for c in official["candidates"] if c["field"] == field}
                if len(candidates) > 1:
                    official[field] = ""
                    official["field_sources"][field] = "ambiguous"
                    issues.append(f"Beberapa kandidat {field} untuk {role}; pilih atau isi manual.")
    except Exception:
        officials = empty_officials()
        issues.append("Nama dan jabatan pejabat belum dapat dibaca dari RKS. Isi manual atau gunakan placeholder draf.")
    return {"officials": officials, "officials_project_key": project_key, "officials_issues": issues}
