"""
LLM Generator & Orchestrator for Dokumen Tender Pertamina Patra Niaga.
Extracts project parameters, prompts LLM for strict JSON schema output,
merges form overrides, and invokes render_tender_to_docx.
"""

import json
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from langchain_core.messages import SystemMessage
from langchain_openrouter import ChatOpenRouter

from tender.schema import DOKUMEN_TENDER_JSON_SCHEMA, DokumenTenderData
from tender.docx import render_tender_to_docx

load_dotenv()

# Global store for active tender draft
_active_tender_store: Dict[str, Any] = {}


def _format_rupiah(val: float) -> str:
    """Format numeric float to Rupiah string (e.g., Rp14.346.100.000,00)."""
    try:
        val_int = int(val)
        formatted = f"{val_int:,}".replace(",", ".")
        return f"Rp{formatted},00"
    except Exception:
        return f"Rp{val}"


class GenerateTenderDocumentTool:
    """Tool that generates a complete Dokumen Tender JSON payload using LLM."""

    def invoke(self, kwargs: dict) -> str:
        nama_pengadaan = kwargs.get("nama_pengadaan", "Pengadaan Jasa / Barang")
        nomor_tender = kwargs.get("nomor_tender", "No.Project/DT/PND970000/2026-S7")
        tanggal = kwargs.get("tanggal", "04 Desember 2025")
        
        # Financial / HPS
        prime_cost = float(kwargs.get("prime_cost", 13283434534.0))
        total_kr = float(kwargs.get("total_dengan_kr", 14346100000.0))
        
        # CSMS & TKDN
        resiko_csms = kwargs.get("resiko_csms", "Tinggi").capitalize()
        tkdn_target = float(kwargs.get("tkdn_minimal", 20.12))
        
        # Administrative & Procurement Officers
        pejabat_proc_nama = kwargs.get("pejabat_procurement_nama", "Rigga Widar Atmagi")
        pejabat_proc_jabatan = kwargs.get("pejabat_procurement_jabatan", "Area Manager Procurement Kalimantan")
        pejabat_berwenang = kwargs.get("pejabat_berwenang", "Sr. Manager Opt. & Maint. Regional Kalimantan")
        pengawas_pekerjaan = kwargs.get("pengawas_pekerjaan", "Region Manager RPD Regional Kalimantan")
        metode_pemenuhan = kwargs.get("metode_pemenuhan", "Tender Terbatas")
        jenis_kontrak = kwargs.get("jenis_kontrak", "Gabungan Harga Satuan & Lumpsum")
        
        # Prebid and Schedules
        prebid_tgl = kwargs.get("prebid_tanggal", "Senin, 08 Desember 2025")
        prebid_waktu = kwargs.get("prebid_waktu", "10.00 WITA")
        prebid_tempat = kwargs.get("prebid_tempat", "Microsoft Teams Meeting dengan link yang disampaikan melalui email Undangan Prebid Meeting")
        
        pemasukan_mulai = kwargs.get("pemasukan_mulai", "Senin, 08 Desember 2025")
        pemasukan_selesai = kwargs.get("pemasukan_selesai", "Senin, 15 Desember 2025")
        
        # Additional context (e.g. from RKS or BOQ)
        context_summary = kwargs.get("context_summary", "")

        # Call OpenRouter LLM
        llm = ChatOpenRouter(model="qwen/qwen3.7-flash", temperature=0)

        system_prompt = f"""
Kamu adalah Legal & Procurement Specialist PT Pertamina Patra Niaga yang ahli dalam penyusunan Dokumen Tender lengkap (IKPP dan Rancangan Kontrak) berdasarkan Pedoman Pengadaan Barang/Jasa No. A03-001/PNG200000/2024-S9 Revisi ke-1.

Tugas kamu adalah menyusun dynamic data untuk Dokumen Tender berdasarkan parameter berikut:
- Nama Pengadaan               : {nama_pengadaan}
- Nomor Dokumen Tender         : {nomor_tender}
- Tanggal Dokumen              : {tanggal}
- Nilai HPS Prime Cost         : {_format_rupiah(prime_cost)}
- Nilai HPS Total (+ K&R)      : {_format_rupiah(total_kr)}
- Risiko HSSE / CSMS           : {resiko_csms}
- Target Minimal TKDN          : {tkdn_target}%
- Metode Pemenuhan Kebutuhan   : {metode_pemenuhan}
- Jenis Kontrak                : {jenis_kontrak}
- Pejabat Procurement          : {pejabat_proc_nama} ({pejabat_proc_jabatan})
- Pejabat Berwenang            : {pejabat_berwenang}
- Pengawas Pekerjaan           : {pengawas_pekerjaan}
- Jadwal Pre-Bid Meeting       : {prebid_tgl} ({prebid_waktu}) di {prebid_tempat}
- Jadwal Pemasukan Penawaran   : {pemasukan_mulai} s.d. {pemasukan_selesai}

Konteks Tambahan (RKS / BOQ):
{context_summary}

Fokus Tugas Khusus LLM:
1. Tentukan Kode Bidang Usaha Pertamina (KBUP) dan KBLI yang relevan dan presisi untuk pekerjaan ini.
2. Buat rincian Lampiran 2A (Syarat dan Kriteria Evaluasi Teknis) yang spesifik untuk jenis pekerjaan ini (minimal 4 kriteria dengan dokumen pembuktian, parameter evaluasi terukur, dan bobot yang berjumlah 100).
3. Rincikan lingkup pekerjaan (scope of work) untuk Pasal 2 Bagian B (Rancangan Kontrak).

Output HARUS berupa JSON valid persis sesuai dengan schema berikut:
{DOKUMEN_TENDER_JSON_SCHEMA}

Jawab HANYA dengan JSON valid, tanpa teks pengantar atau markdown tambahan di luar blok JSON.
"""

        try:
            raw_response = llm.invoke([SystemMessage(content=system_prompt)])
            raw_text = raw_response.content

            # Clean JSON formatting
            clean = raw_text.strip()
            if clean.startswith("```"):
                clean = clean.split("```", 2)[1]
                if clean.startswith("json"):
                    clean = clean[4:]
                clean = clean.rsplit("```", 1)[0]
            
            tender_json = json.loads(clean.strip())

            # Fallback & overwrite crucial deterministic form fields
            cover = tender_json.setdefault("cover_page", {})
            cover["nama_pengadaan"] = nama_pengadaan
            cover["nomor_tender"] = nomor_tender
            cover["tanggal"] = tanggal
            
            pejabat = cover.setdefault("pejabat_procurement", {})
            pejabat["nama"] = pejabat_proc_nama
            pejabat["jabatan_2"] = pejabat_proc_jabatan

            kk = tender_json.setdefault("ketentuan_khusus_ikpp", {})
            kk["metode_pemenuhan"] = metode_pemenuhan
            kk["pejabat_berwenang"] = pejabat_berwenang
            kk["pengawas_pekerjaan"] = pengawas_pekerjaan
            kk["jenis_kontrak"] = jenis_kontrak

            # Ensure HPS figures are deterministic
            hps = kk.setdefault("hps_oe", {})
            hps["prime_cost"] = prime_cost
            hps["prime_cost_str"] = _format_rupiah(prime_cost)
            hps["total_dengan_kr"] = total_kr
            hps["total_dengan_kr_str"] = _format_rupiah(total_kr)

            # Ensure Prebid details are deterministic
            prebid = kk.setdefault("jadwal_prebid", {})
            prebid["hari_tanggal"] = prebid_tgl
            prebid["waktu"] = prebid_waktu
            prebid["tempat"] = prebid_tempat

            # Store in active draft store
            _active_tender_store["current_draft"] = tender_json

            criteria_count = len(tender_json.get("lampiran_2a_evaluasi_teknis", []))
            return f"Draft Dokumen Tender berhasil di-generate! ({criteria_count} kriteria teknis Lampiran 2A disusun)"

        except Exception as e:
            return f"Error saat generate JSON Dokumen Tender: {e}"


class ExportTenderToDocxTool:
    """Tool that exports the active tender draft into a formatted DOCX file."""

    def invoke(self, kwargs: dict) -> str:
        output_filename = kwargs.get("output_filename", "")
        draft = _active_tender_store.get("current_draft")
        if not draft:
            return "Error: Tidak ada draft Dokumen Tender yang aktif. Silakan generate draft terlebih dahulu."

        try:
            output_path = render_tender_to_docx(draft, output_filename)
            return f"📄 File: {output_path}"
        except Exception as e:
            return f"Error saat export Dokumen Tender ke docx: {e}"


# Tool instances ready to be imported
generate_tender_document = GenerateTenderDocumentTool()
export_tender_to_docx = ExportTenderToDocxTool()

