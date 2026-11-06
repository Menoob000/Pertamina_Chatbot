"""Finalize the downloadable DOCX before deriving its preview."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def finalize_and_preview(docx: Path, heading_count: int) -> dict:
    engine = os.getenv("RKS_RENDERER", "auto").lower()
    report = docx.parent / "render.json"
    failure = "Renderer belum tersedia. Pasang LibreOffice atau gunakan Word dan pywin32 pada Windows."
    if engine in {"auto", "word"} and sys.platform == "win32":
        import importlib.util
        if importlib.util.find_spec("win32com"):
            system_drive = Path(os.environ.get("SystemRoot", "C:/Windows")).anchor
            if system_drive and shutil.disk_usage(system_drive).free < 64 * 1024 * 1024:
                return {"available": False, "message": f"Ruang drive sistem {system_drive} tidak cukup untuk Word. Kosongkan ruang, lalu klik Buat ulang DOCX dan preview."}
            try:
                result = subprocess.run([sys.executable, str(Path(__file__).with_name("office_worker.py")),
                                         str(docx), str(report)], capture_output=True, text=True, timeout=240)
                if result.returncode == 0 and docx.with_suffix(".pdf").exists():
                    info = json.loads(report.read_text(encoding="utf-8"))
                    info["toc_verified"] = not info["toc_mismatches"] and info["toc_entries_checked"] >= heading_count
                    return {**info, "available": True}
                failure = "Word tidak dapat menyelesaikan render DOCX."
            except subprocess.TimeoutExpired:
                failure = "Render Word melebihi batas waktu; preview tidak tersedia."
            if engine == "word":
                return {"available": False, "message": failure}
    executable = os.getenv("SOFFICE_PATH") or shutil.which("soffice") or shutil.which("libreoffice")
    if executable and engine in {"auto", "libreoffice"}:
        try:
            # Re-save to a distinct directory first so updated fields are
            # persisted in the DOCX offered to the user, not only in the PDF.
            final_dir = docx.parent / "office-final"
            final_dir.mkdir(exist_ok=True)
            profile = (docx.parent / "office-profile").resolve().as_uri()
            base = [executable, f"-env:UserInstallation={profile}", "--headless"]
            subprocess.run(base + ["--convert-to", "docx", "--outdir", str(final_dir), str(docx)],
                           check=True, capture_output=True, timeout=180)
            saved = final_dir / docx.name
            if not saved.is_file():
                raise RuntimeError("DOCX final tidak tersimpan.")
            shutil.copyfile(saved, docx)
            subprocess.run(base + ["--convert-to", "pdf", "--outdir", str(docx.parent), str(docx)],
                           check=True, capture_output=True, timeout=180)
            return {"available": docx.with_suffix(".pdf").is_file(), "engine": "libreoffice",
                    "toc_verified": not heading_count,
                    "message": "Nomor halaman daftar isi perlu pemeriksaan pada adapter LibreOffice." if heading_count else ""}
        except (subprocess.SubprocessError, RuntimeError, OSError):
            return {"available": False, "message": "Konversi LibreOffice gagal; tidak ada preview baru."}
    return {"available": False, "message": failure}
