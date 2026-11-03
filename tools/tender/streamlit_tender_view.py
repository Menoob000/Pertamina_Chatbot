"""
Streamlit UI View for Dokumen Tender Generator.
Interacts with the dedicated FastAPI service on http://127.0.0.1:8000.
Directly extracts and displays key procurement information without tedious manual forms.
"""

import os
import io
import requests
from pathlib import Path
from typing import Optional, Dict, Any

import streamlit as st

API_HOST = os.getenv("FASTAPI_HOST", "127.0.0.1")
API_PORT = os.getenv("FASTAPI_PORT", "8000")
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", f"http://{API_HOST}:{API_PORT}")


def check_api_status() -> bool:
    try:
        r = requests.get(f"{FASTAPI_BASE_URL}/api/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def _format_rupiah(val: float) -> str:
    """Format numeric float to Rupiah string (e.g., Rp14.346.100.000,00)."""
    try:
        val_int = int(val)
        formatted = f"{val_int:,}".replace(",", ".")
        return f"Rp{formatted},00"
    except Exception:
        return f"Rp{val}"


def render_tender_generator_page(render_download_card_fn):
    """Renders the simplified and automated Tender Document Generator UI."""
    st.markdown(
        """
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
            <div>
                <h2 style="margin:0; font-size:1.6rem; color:#0F172A; font-weight:800;">
                    📑 Generator Dokumen Tender & Rancangan Kontrak
                </h2>
                <p style="margin:4px 0 0 0; color:#64748B; font-size:0.9rem;">
                    Penyusunan otomatis Dokumen Tender (IKPP & Rancangan Kontrak) berstandar Pedoman Pengadaan Pertamina Patra Niaga No. A03-001/PNG200000/2024-S9 Rev. 1.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # API Backend Healthcheck Badge
    api_online = check_api_status()
    if api_online:
        st.markdown(
            f"<div style='display:inline-block; padding:4px 12px; background:#ECFDF5; border:1px solid #A7F3D0; border-radius:16px; font-size:0.8rem; color:#059669; font-weight:600; margin-bottom:16px;'>"
            f"🟢 FastAPI Backend Terhubung (<code>{FASTAPI_BASE_URL}</code>)</div>",
            unsafe_allow_html=True,
        )
    else:
        st.warning(
            f"⚠️ FastAPI Backend belum aktif di `{FASTAPI_BASE_URL}`. "
            f"Jalankan server API di terminal dengan: `uv run python -m api.main`"
        )

    # ── Section 1: Dokumen Pendukung (RKS & BOQ) ──
    st.markdown("#### 📂 **1. Dokumen Pendukung Pengadaan (RKS & BOQ)**")
    st.caption(
        "Dokumen pendukung bersifat opsional. Informasi penting seperti **Nama Pengadaan, Risiko CSMS, Nilai HPS, dan Lingkup Pekerjaan** "
        "akan diekstrak secara otomatis dari file di bawah untuk menyusun Dokumen Tender. Jika tidak ada file, template akan menggunakan placeholder resmi."
    )

    col_rks, col_boq = st.columns(2)

    # RKS Selection
    with col_rks:
        st.markdown("##### 📄 Dokumen RKS (Rencana Kerja & Syarat)")
        active_rks_docx = st.session_state.get("last_exported_docx")
        use_active_rks = False

        if active_rks_docx and os.path.exists(active_rks_docx):
            st.success(f"✅ RKS Aktif dari Chat: `{os.path.basename(active_rks_docx)}`")
            use_active_rks = st.checkbox(
                "Gunakan file RKS aktif ini sebagai konteks",
                value=True,
                key="chk_use_active_rks"
            )

        uploaded_rks = None
        if not use_active_rks:
            uploaded_rks = st.file_uploader(
                "Unggah File RKS (DOCX / PDF)",
                type=["docx", "pdf"],
                key="uploader_rks_file"
            )

    # BOQ Selection
    with col_boq:
        st.markdown("##### 📊 Dokumen BOQ (Bill of Quantities)")
        uploaded_boq = st.file_uploader(
            "Unggah File BOQ (Excel .xlsx / CSV / PDF)",
            type=["xlsx", "xls", "csv", "pdf"],
            key="uploader_boq_file"
        )

    # Trigger Context Extraction
    btn_extract = st.button("🔍 Analisa & Ekstrak Informasi dari Dokumen", type="secondary", use_container_width=True)

    if btn_extract:
        if not api_online:
            st.error("Gagal menghubungkan ke backend FastAPI. Pastikan server API menyala di port 8000.")
        else:
            with st.spinner("Menganalisa dokumen pendukung dan mengekstrak parameter pengadaan..."):
                try:
                    files_payload = {}
                    data_payload = {}

                    if use_active_rks and active_rks_docx:
                        data_payload["rks_filepath"] = active_rks_docx
                    elif uploaded_rks:
                        files_payload["rks_file"] = (uploaded_rks.name, uploaded_rks.getvalue(), uploaded_rks.type)

                    if uploaded_boq:
                        files_payload["boq_file"] = (uploaded_boq.name, uploaded_boq.getvalue(), uploaded_boq.type)

                    resp = requests.post(
                        f"{FASTAPI_BASE_URL}/api/tender/extract-context",
                        data=data_payload,
                        files=files_payload if files_payload else None,
                        timeout=15
                    )

                    if resp.status_code == 200:
                        extracted = resp.json()
                        if extracted.get("nama_pengadaan"):
                            st.session_state.tf_nama_pengadaan = extracted["nama_pengadaan"]
                        if extracted.get("resiko_csms"):
                            st.session_state.tf_resiko_csms = extracted["resiko_csms"]
                        if extracted.get("prime_cost") and extracted["prime_cost"] > 0:
                            st.session_state.tf_prime_cost = float(extracted["prime_cost"])
                        if extracted.get("total_dengan_kr") and extracted["total_dengan_kr"] > 0:
                            st.session_state.tf_total_kr = float(extracted["total_dengan_kr"])
                        if extracted.get("combined_context_summary"):
                            st.session_state.tf_context_summary = extracted["combined_context_summary"]
                        if extracted.get("boq_items"):
                            st.session_state.tf_boq_items = extracted["boq_items"]

                        st.session_state.extraction_done = True
                        st.success("✅ Informasi penting berhasil diekstrak dari dokumen pendukung!")
                        st.rerun()
                    else:
                        st.error(f"Ekstraksi gagal ({resp.status_code}): {resp.text}")
                except Exception as e:
                    st.error(f"Error saat menghubungi API ekstraksi: {e}")

    # ── Section 2 & 3: Hanya Muncul Setelah Ekstraksi Selesai ──
    if st.session_state.get("extraction_done"):
        st.write("")
        st.markdown("#### 📋 **2. Informasi Pengadaan yang Telah Diekstrak**")

        # Read extracted values
        info_nama = st.session_state.get("tf_nama_pengadaan") or "Pekerjaan Overhaul Tangki 041T304 Area LOC III"
        info_csms = st.session_state.get("tf_resiko_csms") or "Tinggi"
        raw_prime = st.session_state.get("tf_prime_cost")
        info_prime = float(raw_prime) if raw_prime and raw_prime > 0 else 13283434534.0
        raw_kr = st.session_state.get("tf_total_kr")
        info_kr = float(raw_kr) if raw_kr and raw_kr > 0 else 14346100000.0
        info_context = st.session_state.get("tf_context_summary") or "Scope overhaul tangki penyimpanan, perbaikan bottom plate, sandblasting dan coating."
        info_boq_items = st.session_state.get("tf_boq_items") or []

        # Display Metrics Cards
        m1, m2, m3 = st.columns([2, 1, 1])
        with m1:
            st.markdown(
                f"""
                <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 16px; margin-bottom:8px;">
                    <span style="font-size:0.75rem; color:#64748B; font-weight:700; text-transform:uppercase;">📌 Nama Pengadaan</span>
                    <div style="font-size:1.05rem; font-weight:700; color:#0F172A; margin-top:4px;">{info_nama}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m2:
            badge_color = "#DC2626" if info_csms == "Tinggi" else ("#D97706" if info_csms == "Sedang" else "#059669")
            badge_bg = "#FEF2F2" if info_csms == "Tinggi" else ("#FFFBEB" if info_csms == "Sedang" else "#ECFDF5")
            st.markdown(
                f"""
                <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 16px; margin-bottom:8px;">
                    <span style="font-size:0.75rem; color:#64748B; font-weight:700; text-transform:uppercase;">🛡️ Risiko HSSE / CSMS</span>
                    <div style="margin-top:6px;">
                        <span style="background:{badge_bg}; color:{badge_color}; border:1px solid {badge_color}; padding:4px 10px; border-radius:12px; font-weight:700; font-size:0.9rem;">
                            {info_csms} Risk
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m3:
            st.markdown(
                f"""
                <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 16px; margin-bottom:8px;">
                    <span style="font-size:0.75rem; color:#64748B; font-weight:700; text-transform:uppercase;">💰 Total Nilai HPS (+K&R)</span>
                    <div style="font-size:1.05rem; font-weight:700; color:#002D62; margin-top:4px;">{_format_rupiah(info_kr)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Detailed Summary Expander
        with st.expander("🔍 **Detail Spesifikasi & Rincian yang Akan Disusun AI**", expanded=False):
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.markdown("**Lingkup Pekerjaan dari RKS:**")
                st.caption(info_context[:1000] + ("..." if len(info_context) > 1000 else ""))
                st.write(f"**HPS Prime Cost:** `{_format_rupiah(info_prime)}`")
                st.write(f"**Item BOQ Terbaca:** `{len(info_boq_items)} baris rincian`")
            with col_d2:
                st.markdown("**Ketentuan Pengadaan Standar Pertamina:**")
                st.write("• **Metode Pemenuhan:** Tender Terbatas (Single Winner)")
                st.write("• **Jenis Kontrak:** Gabungan Harga Satuan & Lumpsum")
                st.write("• **Target Minimal TKDN:** 20.12%")
                st.write("• **Pejabat Procurement:** Rigga Widar Atmagi (Area Manager Procurement Kalimantan)")
                st.write("• **Jadwal Pre-bid:** Senin, 08 Desember 2025 (10.00 WITA) via MS Teams")

        # Optional Output Filename
        clean_suggest = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in info_nama)[:40].strip()
        out_filename = st.text_input(
            "Nama File Hasil (.docx)",
            value=f"Dokumen_Tender_{clean_suggest}.docx",
            key="inp_final_outname"
        )

        # ── Section 3: Generate Action ──
        st.write("")
        btn_generate = st.button("🚀 Generate Dokumen Tender (.docx)", type="primary", use_container_width=True, key="btn_run_tender_gen")

        if btn_generate:
            if not api_online:
                st.error("Server FastAPI tidak dapat dihubungi. Pastikan backend aktif di port 8000 (`uv run python -m api.main`).")
            else:
                with st.spinner("🤖 AI sedang menyusun Dokumen Tender lengkap (IKPP 40 butir, Kriteria Lampiran 2A terukur, BoQ, dan Rancangan Kontrak 18 Pasal)..."):
                    try:
                        payload = {
                            "nama_pengadaan": info_nama,
                            "nomor_tender": "No.Project/DT/PND970000/2026-S7",
                            "tanggal": "04 Desember 2025",
                            "prime_cost": info_prime,
                            "total_dengan_kr": info_kr,
                            "resiko_csms": info_csms,
                            "tkdn_minimal": 20.12,
                            "pejabat_procurement_nama": "Rigga Widar Atmagi",
                            "pejabat_procurement_jabatan": "Area Manager Procurement Kalimantan",
                            "pejabat_berwenang": "Sr. Manager Opt. & Maint. Regional Kalimantan",
                            "pengawas_pekerjaan": "Region Manager RPD Regional Kalimantan",
                            "metode_pemenuhan": "Tender Terbatas",
                            "jenis_kontrak": "Gabungan Harga Satuan & Lumpsum",
                            "prebid_tanggal": "Senin, 08 Desember 2025",
                            "prebid_waktu": "10.00 WITA",
                            "prebid_tempat": "Microsoft Teams Meeting",
                            "pemasukan_mulai": "Senin, 08 Desember 2025",
                            "pemasukan_selesai": "Senin, 15 Desember 2025",
                            "context_summary": info_context,
                            "boq_items": info_boq_items,
                            "output_filename": out_filename
                        }

                        res = requests.post(f"{FASTAPI_BASE_URL}/api/tender/generate", json=payload, timeout=90)

                        if res.status_code == 200:
                            gen_result = res.json()
                            st.session_state.last_generated_tender = gen_result
                            st.success(f"🎉 {gen_result.get('message', 'Dokumen Tender berhasil dibuat!')}")
                        else:
                            st.error(f"Gagal generate Dokumen Tender ({res.status_code}): {res.text}")

                    except Exception as e:
                        st.error(f"Terjadi kesalahan saat memanggil API: {e}")
    else:
        st.write("")
        st.info(
            "💡 **Petunjuk:** Pilih atau unggah dokumen RKS dan/atau BOQ pada Bagian 1 di atas, "
            "kemudian klik tombol **'🔍 Analisa & Ekstrak Informasi dari Dokumen'**. "
            "Kartu parameter pengadaan penting beserta tombol generate dokumen akan otomatis muncul setelah ekstraksi selesai."
        )

    # Render Download Card if generated
    last_tender = st.session_state.get("last_generated_tender")
    if last_tender and last_tender.get("filepath") and os.path.exists(last_tender["filepath"]):
        fpath = last_tender["filepath"]
        details = last_tender.get("details", {})
        st.divider()
        st.markdown(f"### 📥 File Dokumen Tender Siap Diunduh")
        col_res1, col_res2 = st.columns([2, 1])
        with col_res1:
            st.write(f"**Nama Pengadaan:** {details.get('nama_pengadaan')}")
            st.write(f"**Nomor Tender:** `{details.get('nomor_tender')}`")
            st.write(f"**Kriteria Teknis Lampiran 2A:** {details.get('kriteria_teknis_count', 0)} kriteria terukur disusun")
            st.write(f"**Cakupan Dokumen:** Sampul resmi, Bagian A (Tabel IKPP 40 butir, 30 artikel umum), Lampiran 1A-8, Bagian B (Rancangan Kontrak 18 pasal, PI-07, SP3MK).")
        with col_res2:
            render_download_card_fn(fpath, key="tender_download_card_final")
