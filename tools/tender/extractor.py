"""
Extractor module to parse context and parameters from RKS and BOQ supporting documents.
Supports:
- RKS: DOCX, PDF, and plain text
- BOQ: Excel (.xlsx, .xls), CSV, and PDF
"""

import io
import re
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

import docx
import pymupdf


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
    csms = "Tinggi"
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

    if not title and filename:
        clean_fn = filename.replace(".pdf", "").replace(".docx", "").replace("RKS-", "").replace("RKS+", "").strip()
        title = clean_fn

    if not title:
        title = "PENGADAAN JASA / BARANG"

    # 3. Extract CSMS Risk Level
    if re.search(r'csms.*?(middle|sedang)', text_clean, re.IGNORECASE):
        csms = "Sedang"
    elif re.search(r'csms.*?(low|rendah)', text_clean, re.IGNORECASE):
        csms = "Rendah"
    else:
        csms = "Tinggi"

    # 4. Extract Scope of Work snippet
    scope_match = re.search(
        r'(?:BAB\s+[0-9IVXLCDM]+\.?|LINGKUP\s+KERJA|LINGKUP\s+PEKERJAAN|URAIAN\s+PEKERJAAN)[\s\:\-]+([^\n\r]+(?:\n[^\n\r]+){1,30})',
        text_clean, re.IGNORECASE
    )
    if scope_match:
        scope_snippets.append(scope_match.group(0)[:1500].strip())

    summary_text = (
        f"Dokumen RKS: {filename}\n"
        f"Judul: {title}\n"
        f"CSMS: {csms}\n"
        f"Lingkup Pekerjaan Utama:\n" + ("\n".join(scope_snippets) if scope_snippets else text_clean[:1200])
    )

    return {
        "nama_pengadaan": title,
        "resiko_csms": csms,
        "context_summary": summary_text[:3000],
        "full_text_snippet": text_clean[:4000]
    }


def extract_boq_info(file_input: Union[str, Path, bytes, io.BytesIO], filename: str = "") -> Dict[str, Any]:
    """
    Extracts key financial & item information from a BOQ document:
    - Prime Cost & Total dengan K&R (HPS)
    - List of structured items for Lampiran 5B
    - Context summary for LLM prompt
    """
    prime_cost = 0.0
    total_kr = 0.0
    items: List[Dict[str, Any]] = []
    summary_lines = []

    # Handle Excel (.xlsx, .xls)
    is_excel = filename.lower().endswith((".xlsx", ".xls"))
    is_csv = filename.lower().endswith(".csv")

    try:
        if is_excel or is_csv:
            import pandas as pd
            if isinstance(file_input, (str, Path)):
                df = pd.read_excel(file_input) if is_excel else pd.read_csv(file_input)
            else:
                raw_bytes = file_input.getvalue() if isinstance(file_input, io.BytesIO) else file_input
                buf = io.BytesIO(raw_bytes)
                df = pd.read_excel(buf) if is_excel else pd.read_csv(buf)

            # Search numeric totals in dataframe
            # Convert cells to string to search for TOTAL / GRAND TOTAL / HPS
            for idx, row in df.iterrows():
                row_str = " ".join([str(val) for val in row.values if pd.notna(val)])
                if re.search(r'(total|hps|jumlah|grand total)', row_str, re.IGNORECASE):
                    # extract numbers from this row
                    for val in row.values:
                        if isinstance(val, (int, float)) and val > 1000000:
                            if not prime_cost:
                                prime_cost = float(val)
                            elif val > prime_cost:
                                total_kr = float(val)

            # Sample top items for Lampiran 5B
            col_names = [str(c).lower() for c in df.columns]
            desc_col = None
            vol_col = None
            unit_col = None

            for col in df.columns:
                c_low = str(col).lower()
                if "uraian" in c_low or "deskripsi" in c_low or "item" in c_low or "pekerjaan" in c_low:
                    desc_col = col
                elif "vol" in c_low or "qty" in c_low or "jumlah" in c_low:
                    vol_col = col
                elif "sat" in c_low or "unit" in c_low:
                    unit_col = col

            if desc_col:
                for idx, row in df.head(20).iterrows():
                    d_val = str(row.get(desc_col, "")).strip()
                    if d_val and d_val.lower() != "nan" and not re.search(r'^(total|sub total)', d_val, re.IGNORECASE):
                        items.append({
                            "no": len(items) + 1,
                            "uraian": d_val[:120],
                            "volume": str(row.get(vol_col, "-")) if vol_col else "-",
                            "satuan": str(row.get(unit_col, "-")) if unit_col else "-"
                        })

            summary_lines.append(f"BOQ File ({filename}): Terbaca {len(df)} baris data.")

    except Exception as e:
        summary_lines.append(f"Catatan pembacaan file BOQ: {e}")

    # Fallback / calculation defaults if total_kr missing
    if prime_cost and not total_kr:
        total_kr = round(prime_cost * 1.08, 2)  # assume ~8% K&R margin default
    elif not prime_cost and total_kr:
        prime_cost = round(total_kr / 1.08, 2)

    return {
        "prime_cost": prime_cost,
        "total_dengan_kr": total_kr,
        "items": items,
        "summary": "\n".join(summary_lines) if summary_lines else f"BOQ Lampiran ({filename})"
    }
