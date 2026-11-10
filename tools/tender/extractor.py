"""
Extractor module to parse context and parameters from RKS and BOQ supporting documents.
Supports:
- RKS: DOCX, PDF, and plain text
- BOQ: Excel (.xlsx, .xls), CSV, and PDF
"""

import io
import re
import os
import csv
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

import docx
import pymupdf
from .officer_extraction import extract_officials


def extract_rks_info(file_input: Union[str, Path, bytes, io.BytesIO], filename: str = "") -> Dict[str, Any]:
    """
    Extracts key tender-relevant information from an RKS document:
    - Judul Pekerjaan / Nama Pengadaan
    - Risiko CSMS (Tinggi, Sedang, Rendah)
    - Ringkasan Lingkup Pekerjaan (Scope of Work)
    - Full text snippet for LLM context
    """
    text_content = ""
    title = ""
    csms = None
    sources = {}
    issues = []
    scope_snippets = []

    # 1. Read content
    if isinstance(file_input, (str, Path)) and os.path.exists(str(file_input)):
        fpath = Path(file_input)
        filename = filename or fpath.name
        if fpath.suffix.lower() == ".docx":
            try:
                doc = docx.Document(str(fpath))
                para_text = [p.text for p in doc.paragraphs if p.text.strip()]
                tbl_text = [c.text.strip() for t in doc.tables for row in t.rows for c in row.cells if c.text.strip()]
                text_content = "\n".join(tbl_text + para_text)
            except Exception as e:
                text_content = f"Error reading docx: {e}"
        elif fpath.suffix.lower() == ".pdf":
            try:
                with pymupdf.open(str(fpath)) as pdf:
                    text_content = "\n".join([page.get_text() for page in pdf])
            except Exception as e:
                text_content = f"Error reading pdf: {e}"
        else:
            try:
                text_content = fpath.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass
    elif isinstance(file_input, (bytes, io.BytesIO)):
        raw_bytes = file_input.getvalue() if isinstance(file_input, io.BytesIO) else file_input
        fname_lower = filename.lower()
        if fname_lower.endswith(".docx"):
            try:
                doc = docx.Document(io.BytesIO(raw_bytes))
                para_text = [p.text for p in doc.paragraphs if p.text.strip()]
                tbl_text = [c.text.strip() for t in doc.tables for row in t.rows for c in row.cells if c.text.strip()]
                text_content = "\n".join(tbl_text + para_text)
            except Exception as e:
                text_content = f"Error reading docx bytes: {e}"
        elif fname_lower.endswith(".pdf"):
            try:
                with pymupdf.open(stream=raw_bytes, filetype="pdf") as pdf:
                    text_content = "\n".join([page.get_text() for page in pdf])
            except Exception as e:
                text_content = f"Error reading pdf bytes: {e}"
        else:
            try:
                text_content = raw_bytes.decode("utf-8", errors="ignore")
            except Exception:
                pass

    text_clean = text_content.replace("\xa0", " ").strip()

    # 2. Extract Judul / Nama Pekerjaan
    job_match = re.search(
        r'(?:MELAKSANAKAN\s+PEKERJAAN|PEKERJAAN)\s+([A-Z0-9\s\-\.\/\,\_]+?)(?:PARAF|LAMPIRAN|DAFTAR|PT KILANG|PT PERTAMINA|\n\n)',
        text_clean, re.IGNORECASE
    )
    if job_match:
        extracted = re.sub(r'\s+', ' ', job_match.group(0).strip())
        if 15 < len(extracted) < 250:
            title = extracted

    if title:
        sources["nama_pengadaan"] = {"filename": filename, "location": "teks RKS"}
    else:
        issues.append("Nama pengadaan tidak ditemukan secara pasti dalam RKS; isi manual.")

    # 3. Extract CSMS Risk Level
    risk_match = re.search(r'(?:RISIKO|RESIKO)\s*(?:PEKERJAAN)?\s*\(?ASPEK\s*CSMS\)?\s*[:\-]?\s*(HIGH|MIDDLE|LOW|TINGGI|SEDANG|RENDAH)\b', text_clean, re.I)
    if not risk_match:
        risk_section = re.search(r'(?:RISIKO|RESIKO)\s*(?:PEKERJAAN)?\s*\(?ASPEK\s*CSMS\)?[^\n]{0,100}', text_clean, re.I)
        if risk_section:
            risk_match = re.search(r'[☑☒✓✔]\s*(HIGH|MIDDLE|LOW|TINGGI|SEDANG|RENDAH)\b', risk_section.group(0), re.I)
    if risk_match:
        csms = {"HIGH": "Tinggi", "MIDDLE": "Sedang", "LOW": "Rendah", "TINGGI": "Tinggi", "SEDANG": "Sedang", "RENDAH": "Rendah"}[risk_match.group(1).upper()]
        sources["resiko_csms"] = {"filename": filename, "location": "teks RKS", "label": risk_match.group(0)}
    else:
        issues.append("Kategori CSMS tidak terbaca dengan pasti; isi manual.")

    # 4. Extract Scope of Work snippet
    scope_match = re.search(
        r'(?:BAB\s+[0-9IVXLCDM]+\.?|LINGKUP\s+KERJA|LINGKUP\s+PEKERJAAN|URAIAN\s+PEKERJAAN)[\s\:\-]+([^\n\r]+(?:\n[^\n\r]+){1,30})',
        text_clean, re.IGNORECASE
    )
    if scope_match:
        scope_snippets.append(scope_match.group(0)[:1500].strip())

    summary_text = (
        f"Dokumen RKS: {filename}\n"
        f"Judul: {title or 'belum ditemukan'}\n"
        f"CSMS: {csms or 'belum ditemukan'}\n"
        f"Lingkup Pekerjaan Utama:\n" + ("\n".join(scope_snippets) if scope_snippets else text_clean[:1200])
    )

    officer_data = extract_officials(file_input, filename)
    issues.extend(officer_data.pop("officials_issues"))
    return {
        **officer_data,
        "nama_pengadaan": title,
        "resiko_csms": csms,
        "context_summary": summary_text[:3000],
        "full_text_snippet": text_clean[:4000],
        "sources": sources,
        "issues": issues,
    }


def extract_boq_info(file_input: Union[str, Path, bytes, io.BytesIO], filename: str = "") -> Dict[str, Any]:
    """Read explicit BOQ totals and all structured item rows with provenance."""
    if isinstance(file_input, (str, Path)):
        path = Path(file_input)
        filename = filename or path.name
        raw = path.read_bytes()
    else:
        raw = file_input.getvalue() if isinstance(file_input, io.BytesIO) else file_input
    extension = Path(filename).suffix.lower()
    result = {"prime_cost": None, "total_dengan_kr": None, "items": [],
              "sources": {}, "issues": [], "summary": ""}

    def money(value):
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value) if value >= 0 else None
        raw_value = str(value).strip()
        if "%" in raw_value or not re.search(r"\d", raw_value):
            return None
        value = re.sub(r"[^\d,.-]", "", raw_value)
        if not value or value.startswith("-"):
            return None
        decimal = None
        if "," in value and "." in value:
            decimal = "," if value.rfind(",") > value.rfind(".") else "."
        elif "," in value and len(value.rsplit(",", 1)[-1]) in (1, 2):
            decimal = ","
        elif "." in value and len(value.rsplit(".", 1)[-1]) in (1, 2):
            decimal = "."
        normalized = value.replace(",", "").replace(".", "") if decimal is None else (
            value.replace(".", "").replace(",", ".") if decimal == "," else value.replace(",", ""))
        try:
            return float(normalized)
        except ValueError:
            return None

    def scan_rows(rows, location):
        header = None
        columns = {}
        for number, row in enumerate(rows, 1):
            cells = [str(cell).strip() if cell is not None else "" for cell in row]
            if not any(cells):
                continue
            labels = " ".join(cells[:-1]).lower() if len(cells) > 1 else cells[0].lower()
            amounts = [(index, money(cell)) for index, cell in enumerate(cells)]
            amounts = [(index, amount) for index, amount in amounts if amount is not None]
            if amounts and re.search(r"\b(prime\s*cost|sub\s*total|subtotal|hps|grand\s*total|total)\b", labels):
                field = ("prime_cost" if re.search(r"prime\s*cost|sub\s*total|subtotal", labels)
                         else "total_dengan_kr" if re.search(r"k\s*&\s*r|keuntungan\s*(?:dan|&)\s*risiko", labels)
                         else None)
                # Only accept a numeric amount to the right of the total label.
                label_positions = [index for index, cell in enumerate(cells)
                                   if re.search(r"\b(prime\s*cost|sub\s*total|subtotal|hps|grand\s*total|total)\b", cell, re.I)]
                amounts = [(index, amount) for index, amount in amounts
                           if index > min(label_positions or [len(cells)])]
                if amounts and field:
                    amount = amounts[-1][1]
                    if amount > 0:
                        result[field] = amount
                        result["sources"][field] = {"filename": filename, "location": f"{location}, baris {number}",
                                                    "label": labels.strip(), "value": amount}
                elif amounts and not field and not any("Total BOQ belum jelas" in issue for issue in result["issues"]):
                    result["issues"].append("Total BOQ belum jelas termasuk K&R; periksa dan isi total HPS manual.")
                continue
            if any(re.search(r"\b(uraian|deskripsi|keterangan|nama pekerjaan)\b", cell, re.I)
                   for cell in cells) and any(re.search(r"\b(vol(?:ume)?|qty|kuantitas|satuan)\b", cell, re.I)
                                         for cell in cells):
                header = number
                columns = {}
                for index, cell in enumerate(cells):
                    if re.search(r"\b(uraian|deskripsi|keterangan|nama pekerjaan)\b", cell, re.I):
                        columns["uraian"] = index
                    elif re.search(r"\b(vol(?:ume)?|qty|kuantitas)\b", cell, re.I):
                        columns["volume"] = index
                    elif re.search(r"\b(satuan|unit)\b", cell, re.I):
                        columns["satuan"] = index
                continue
            if header and number > header and "uraian" in columns:
                def cell_at(field):
                    index = columns.get(field)
                    return cells[index] if index is not None and index < len(cells) else ""
                description = cell_at("uraian")
                if description and not re.match(r"^(total|sub\s*total|jumlah|hps)\b", description, re.I):
                    result["items"].append({"no": len(result["items"]) + 1,
                                            "uraian": description, "volume": cell_at("volume"),
                                            "satuan": cell_at("satuan"),
                                            "source": {"filename": filename,
                                                       "location": f"{location}, baris {number}"}})

    try:
        if extension in {".xlsx", ".xls"}:
            import pandas as pd
            sheets = pd.read_excel(io.BytesIO(raw), sheet_name=None, header=None, dtype=object)
            for sheet, frame in sheets.items():
                scan_rows(frame.where(pd.notna(frame), "").values.tolist(), f"sheet {sheet}")
        elif extension == ".csv":
            decoded = raw.decode("utf-8-sig")
            try:
                dialect = csv.Sniffer().sniff(decoded[:4096], delimiters=",;\t")
            except csv.Error:
                dialect = csv.excel
            scan_rows(list(csv.reader(io.StringIO(decoded), dialect)), "CSV")
        elif extension == ".pdf":
            with pymupdf.open(stream=raw, filetype="pdf") as pdf:
                for index, page in enumerate(pdf, 1):
                    tables = page.find_tables()
                    for table in tables.tables:
                        scan_rows(table.extract(), f"halaman {index}")
                    # Text-only PDF totals are accepted only when explicitly labeled.
                    for line in page.get_text().splitlines():
                        match = re.match(
                            r"^\s*((?:prime\s*cost|sub\s*total|subtotal|hps|grand\s*total|total)\b[^\d\n]{0,90}?)\s*(?:Rp\.?\s*)?([\d][\d.,]*)\s*$",
                            line, re.I)
                        if match:
                            scan_rows([[match.group(1), match.group(2)]], f"halaman {index}")
        else:
            result["issues"].append(f"Format BOQ {extension or 'tanpa ekstensi'} belum didukung.")
    except Exception as exc:
        result["issues"].append(f"BOQ {filename} belum dapat dibaca: {exc}")

    if result["prime_cost"] is None:
        result["issues"].append("Prime Cost tidak ditemukan secara eksplisit di BOQ; isi manual setelah meninjau dokumen.")
    if result["total_dengan_kr"] is None:
        result["issues"].append("Total HPS termasuk keuntungan dan risiko tidak ditemukan secara eksplisit di BOQ; isi manual.")
    if not result["items"]:
        result["issues"].append("Tabel item BOQ belum terbaca; periksa format tabel sumber.")
    result["summary"] = (f"BOQ: {filename}. {len(result['items'])} item terbaca; "
                         f"nilai yang tidak ditemukan tidak dihitung otomatis.")
    return result
