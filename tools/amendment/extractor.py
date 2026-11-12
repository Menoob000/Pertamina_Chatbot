"""Context extractor from existing contracts for generating amendment documents."""
from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Any, Dict
from docx import Document


def extract_context_from_contract(contract_record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ekstrak konteks dari record contract_drafts dan siapkan nilai default
    beserta placeholder untuk amandemen.
    """
    project_name = contract_record.get("project_name", "").strip() or "Pembangunan DPPU Nusantara Ibu Kota Negara (IKN) – Penajam Paser Utara"
    docx_bytes = contract_record.get("docx", b"")

    contract_ref = ""
    company_rep = ""
    company_title = ""
    contractor_name = ""
    contractor_rep = ""
    contractor_title = ""
    price_val = 28642900000

    if docx_bytes:
        try:
            doc = Document(io.BytesIO(docx_bytes))
            full_text = "\n".join([p.text for p in doc.paragraphs])

            # Cari nomor kontrak
            m_nomor = re.search(r"NOMOR\s*:\s*([^\n\r]+)", full_text, re.IGNORECASE)
            if m_nomor:
                cand = m_nomor.group(1).strip()
                if cand and "[" not in cand and "…" not in cand:
                    contract_ref = cand

            # Cari kontraktor / mitra jika ada
            m_kontraktor = re.search(r"(?:DENGAN|Kontraktor|Penyedia)\s*:\s*([^\n\r]+)", full_text, re.IGNORECASE)
            if m_kontraktor:
                cand = m_kontraktor.group(1).strip()
                if cand and len(cand) > 3 and "[" not in cand:
                    contractor_name = cand

            # Cari nominal harga jika ada
            m_harga = re.search(r"Rp\s*([\d\.,]+)", full_text)
            if m_harga:
                clean_num = m_harga.group(1).replace(".", "").replace(",", "")
                try:
                    price_val = int(clean_num)
                except ValueError:
                    pass
        except Exception:
            pass

    today_str = datetime.now().strftime("%d %B %Y").replace("January", "Januari").replace("February", "Februari").replace("March", "Maret").replace("May", "Mei").replace("June", "Juni").replace("July", "Juli").replace("August", "Agustus").replace("October", "Oktober").replace("December", "Desember")

    return {
        "project_name": project_name,
        "contract_ref": contract_ref or "SP-068/PND900000/2024-S0",
        "contract_date": "25 April 2024",
        "amendment_level": "Amendemen II",
        "tanggal_amendemen": today_str,
        "prev_amendment_date": "15 Agustus 2025",
        "company_name": "PT Pertamina Patra Niaga",
        "company_office": "Jakarta Selatan dan berkantor pusat di Gedung Wisma Tugu II Lantai 2, Jalan HR. Rasuna Said Kav. C7-9, Kota Administrasi Jakarta Selatan, Provinsi DKI Jakarta",
        "company_rep_name": company_rep or "Riki Madyanto",
        "company_rep_title": company_title or "Sr. Manager Opt. & Maint. Kalimantan",
        "contractor_name": contractor_name or "PT PGAS Solution",
        "contractor_office": "Jakarta Pusat dan berkantor pusat di Jakarta",
        "contractor_rep_name": contractor_rep or "Heru Indriatno",
        "contractor_rep_title": contractor_title or "Direktur Teknik dan Pengembangan",
        "nilai_pekerjaan_baru": price_val if price_val > 0 else 28642900000,
        "tanggal_sp3mk": "14 Maret 2024",
        "nomor_sp3mk": "SP3MK-007/PND900000/2024-S0",
        "durasi_bulan_pemeliharaan": 6,
        "tanggal_berlaku_amendemen": "04 September 2025",
        "portal_autentifikasi": "https://tte.komdigi.go.id/verifyPDF",
        "klausul_lampiran": (
            "Mengubah beberapa ketentuan dalam Lampiran B KONTRAK, Lampiran C KONTRAK, Lampiran D KONTRAK, "
            "Lampiran G KONTRAK, Lampiran D-I AMENDEMEN dan Lampiran G-I AMENDEMEN dengan perubahan yang "
            "masing-masing terdapat dalam Lampiran B-I AMENDEMEN II, Lampiran C-I AMENDEMEN II, "
            "Lampiran D-II AMENDEMEN II, dan Lampiran G-II AMENDEMEN II."
        ),
        "lingkup_pekerjaan": (
            f"2. Pekerjaan yang harus dilaksanakan oleh KONTRAKTOR adalah {project_name} "
            f"dengan ruang lingkup sebagaimana diuraikan dalam Lampiran B-I AMENDEMEN II."
        ),
        "tambahan_pekerjaan": (
            "3. Pekerjaan yang harus dilaksanakan oleh KONTRAKTOR Pengadaan 1 (Satu) Unit Pompa PMK Kap. 3000 GPM "
            "di IT Balikpapan dengan ruang lingkup sebagaimana diuraikan dalam Lampiran B KONTRAK dengan penambahan "
            "terdapat dalam Lampiran B-I AMENDEMEN II dan harus diselesaikan sesuai dengan jadwal yang diuraikan dalam "
            "Lampiran D-I AMENDEMEN II (“PEKERJAAN”)."
        ),
        "dasar_dokumen": [
            f"Surat KONTRAKTOR kepada PERUSAHAAN No.10150.S/DPPU-IKN/PGAS/XI/2025 tanggal 21 November 2025 perihal Revisi Penawaran Harga dan Waktu pada {project_name};",
            f"Notulen Rapat No.NR-794/PND95C000/2025-S5 tanggal 13 Oktober 2025 perihal War Room dan Pembahasan Pengajuan Amendemen Pekerjaan {project_name};",
            f"Notulen Rapat No.NR-950/PND95C000/2025-S5 tanggal 18 November 2025 perihal Pembahasan Pengajuan Amendemen Pekerjaan {project_name};",
            "Berita Acara Klarifikasi dan Negosiasi Amendemen Waktu dan Biaya No.951/PND95C000/2025-S5 tanggal 02 Desember 2025."
        ],
    }
