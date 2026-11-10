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
from langchain_openai import ChatOpenAI

from .schema import DOKUMEN_TENDER_JSON_SCHEMA, DokumenTenderData
from .docx import render_tender_to_docx
from .officers import normalize_officer_parameters, apply_officials_to_draft
from .placeholders import (
    NOMOR_TENDER, TANGGAL_DOKUMEN, METODE_PEMENUHAN, JENIS_KONTRAK,
    HPS_PRIME_COST, HPS_TOTAL, RISIKO_CSMS, text_or_placeholder,
    amount_or_placeholder,
)

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
        kwargs = normalize_officer_parameters(kwargs)
        nama_pengadaan = str(kwargs.get("nama_pengadaan") or "").strip()
        if not nama_pengadaan:
            return "Error: nama_pengadaan belum diisi."
        nomor_tender = text_or_placeholder(kwargs.get("nomor_tender"), NOMOR_TENDER)
        tanggal = text_or_placeholder(kwargs.get("tanggal"), TANGGAL_DOKUMEN)
        
        # Financial / HPS
        prime_cost = float(kwargs.get("prime_cost") or 0)
        total_kr = float(kwargs.get("total_dengan_kr") or 0)
        prime_cost_text = amount_or_placeholder(prime_cost, HPS_PRIME_COST, _format_rupiah)
        total_kr_text = amount_or_placeholder(total_kr, HPS_TOTAL, _format_rupiah)
        
        # CSMS & TKDN
        resiko_csms = text_or_placeholder(kwargs.get("resiko_csms"), RISIKO_CSMS)
        tkdn_target = float(kwargs.get("tkdn_minimal", 0))
        
        # Administrative & Procurement Officers
        pejabat_proc_nama = kwargs["pejabat_procurement_nama"]
        pejabat_proc_jabatan = kwargs["pejabat_procurement_jabatan"]
        pejabat_berwenang = kwargs["pejabat_berwenang"]
        pengawas_pekerjaan = kwargs["pengawas_pekerjaan"]
        metode_pemenuhan = text_or_placeholder(kwargs.get("metode_pemenuhan"), METODE_PEMENUHAN)
        jenis_kontrak = text_or_placeholder(kwargs.get("jenis_kontrak"), JENIS_KONTRAK)
        
        # Prebid and Schedules
        prebid_tgl = kwargs.get("prebid_tanggal") or ""
        prebid_waktu = kwargs.get("prebid_waktu") or ""
        prebid_tempat = kwargs.get("prebid_tempat") or ""
        
        pemasukan_mulai = kwargs.get("pemasukan_mulai") or ""
        pemasukan_selesai = kwargs.get("pemasukan_selesai") or ""
        
        # Additional context (e.g. from RKS or BOQ)
        context_summary = kwargs.get("context_summary", "")

        # Call OpenRouter LLM
        llm = ChatOpenAI(model="qwen/qwen3.7-flash", api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1", temperature=0)

        system_prompt = f"""
Kamu adalah Legal & Procurement Specialist PT Pertamina Patra Niaga yang ahli dalam penyusunan Dokumen Tender lengkap (IKPP dan Rancangan Kontrak) berdasarkan Pedoman Pengadaan Barang/Jasa No. A03-001/PNG200000/2024-S9 Revisi ke-1.

Tugas kamu adalah menyusun dynamic data untuk Dokumen Tender berdasarkan parameter berikut:
- Nama Pengadaan               : {nama_pengadaan}
- Nomor Dokumen Tender         : {nomor_tender}
- Tanggal Dokumen              : {tanggal}
- Nilai HPS Prime Cost         : {prime_cost_text}
- Nilai HPS Total (+ K&R)      : {total_kr_text}
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
Gunakan hanya nama/jabatan pejabat pada parameter di atas. Pertahankan placeholder jika belum diisi.
Jadwal kosong harus tetap kosong; jangan mengambil nama atau jadwal dari contoh schema.
Parameter berisi placeholder adalah data yang belum diketahui. Pertahankan placeholder tersebut; jangan menebak nomor, tanggal, HPS, risiko CSMS, metode pemenuhan, atau jenis kontrak dari contoh schema.
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
            kk.setdefault("syarat_kualifikasi_csms", {})["tingkat_risiko"] = resiko_csms
            kk["syarat_kualifikasi_csms"]["kualifikasi_minimal"] = resiko_csms
            kk.setdefault("evaluasi_hsse_plan", {})["tingkat_risiko"] = resiko_csms
            kk.setdefault("evaluasi_tkdn", {})["minimal_persen"] = tkdn_target

            # Ensure HPS figures are deterministic
            hps = kk.setdefault("hps_oe", {})
            hps["prime_cost_str"] = prime_cost_text
            hps["total_dengan_kr_str"] = total_kr_text
            # Do not let example figures in model output imply a known HPS.
            hps["prime_cost"] = prime_cost if prime_cost > 0 else None
            hps["total_dengan_kr"] = total_kr if total_kr > 0 else None

            # Ensure Prebid details are deterministic
            prebid = kk.setdefault("jadwal_prebid", {})
            prebid["hari_tanggal"] = prebid_tgl
            prebid["waktu"] = prebid_waktu
            prebid["tempat"] = prebid_tempat
            pemasukan = kk.setdefault("jadwal_pemasukan", {})
            pemasukan["mulai_hari_tanggal"] = pemasukan_mulai
            pemasukan["selesai_hari_tanggal"] = pemasukan_selesai
            # No separate submission time/place inputs exist yet. Never invent them.
            pemasukan.update(mulai_waktu="", selesai_waktu="", tempat_portal="")
            apply_officials_to_draft(tender_json, kwargs)
            contract = tender_json.setdefault("rancangan_kontrak", {})
            contract["judul_pekerjaan"] = nama_pengadaan
            contract["nomor_kontrak"] = "[Nomor kontrak belum diisi]"

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

