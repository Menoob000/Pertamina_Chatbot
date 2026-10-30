import os
import glob
from pathlib import Path
from typing import Optional, Dict, Any
import fitz  # PyMuPDF
from pdf2docx import Converter

DATA_DIR = Path("./data")
OUTPUT_DIR = Path("./output")

def find_matching_pdf(query_or_title: str) -> Optional[str]:
    """Finds a matching PDF file in the data directory by filename or query."""
    if not query_or_title:
        return None

    # If it's already an existing direct path
    if os.path.exists(query_or_title) and query_or_title.lower().endswith(".pdf"):
        return os.path.abspath(query_or_title)

    clean_target = os.path.basename(query_or_title).strip()
    if not clean_target.lower().endswith(".pdf"):
        clean_target_pdf = clean_target + ".pdf"
    else:
        clean_target_pdf = clean_target

    # Search in DATA_DIR
    all_pdfs = list(DATA_DIR.glob("*.pdf"))
    if not all_pdfs:
        return None

    # 1. Exact case-insensitive filename match
    for p in all_pdfs:
        if p.name.lower() == clean_target_pdf.lower() or p.name.lower() == clean_target.lower():
            return str(p.resolve())

    # 2. Substring match
    search_term = clean_target.replace(".pdf", "").lower()
    for p in all_pdfs:
        if search_term in p.name.lower():
            return str(p.resolve())

    # 3. Match key numbers / identifiers (e.g. 36T102, 041T304, etc.)
    import re
    numbers = re.findall(r"[0-9]+[A-Za-z]+[0-9]+|[0-9]{3,}", search_term)
    if numbers:
        for num in numbers:
            for p in all_pdfs:
                if num.lower() in p.name.lower():
                    return str(p.resolve())

    # 4. Fallback: if query is generic like "rks", return first found RKS
    if "rks" in search_term:
        return str(all_pdfs[0].resolve())

    return None


def get_pdf_metadata(pdf_path: str) -> Dict[str, Any]:
    """Retrieves metadata such as page count, file size, and title from a PDF."""
    if not os.path.exists(pdf_path):
        return {"error": "File not found"}

    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        doc.close()
    except Exception:
        page_count = 1

    file_size_kb = os.path.getsize(pdf_path) / 1024
    return {
        "file_name": os.path.basename(pdf_path),
        "file_path": str(Path(pdf_path).resolve()),
        "page_count": page_count,
        "file_size_kb": round(file_size_kb, 1),
    }


def convert_pdf_to_docx_layout(pdf_path: str, output_filename: str = "") -> str:
    """Performs direct layout conversion from PDF to DOCX using pdf2docx."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not output_filename:
        base_name = Path(pdf_path).stem
        safe_name = "".join(c if c.isalnum() or c in (" ", "-", "_", "+") else "_" for c in base_name)
        output_filename = f"{safe_name}.docx"

    if not output_filename.endswith(".docx"):
        output_filename += ".docx"

    output_path = OUTPUT_DIR / output_filename

    cv = Converter(pdf_path)
    cv.convert(str(output_path))
    cv.close()

    return str(output_path.resolve())

