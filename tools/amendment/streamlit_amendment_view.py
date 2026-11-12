"""Streamlit UI View for Dokumen Amandemen Generator."""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict

import pymupdf
import streamlit as st

from tools.tender.contract_archive import ContractArchive
from tools.tender.preview import prepare_tender_preview, preview_key
from .archive import AmendmentArchive
from .builder import build_amendment_docx, format_rupiah_lengkap
from .extractor import extract_context_from_contract


def _render_amendment_page_preview(docx_bytes: bytes, filename: str, key_prefix: str = "amend_gen"):
    digest = preview_key(docx_bytes)
    state_key = f"{key_prefix}-render-{digest}"
    st.markdown("#### 📄 Pratinjau Dokumen Amandemen")

    retry = (
        st.button("Coba preview lagi", key=f"{key_prefix}-retry-{digest}")
        if state_key in st.session_state and not st.session_state[state_key].get("available")
        else False
    )
    if retry or state_key not in st.session_state:
        with st.spinner("Menyiapkan pratinjau halaman dokumen amandemen..."):
            try:
                st.session_state[state_key] = prepare_tender_preview(docx_bytes)
            except (OSError, ValueError, RuntimeError) as exc:
                st.session_state[state_key] = {"available": False, "message": str(exc)}

    preview = st.session_state[state_key]
    if preview.get("available"):
        try:
            pdf_data = preview["pdf"].read_bytes()
            with pymupdf.open(stream=pdf_data, filetype="pdf") as pdf:
                left, right = st.columns([1, 2])
                page_number = left.number_input("Halaman awal", 1, len(pdf), 1, key=f"{key_prefix}-page-{digest}")
                zoom = right.select_slider("Perbesaran", options=[75, 100, 125, 150], value=100, key=f"{key_prefix}-zoom-{digest}")
                visible_key = f"{key_prefix}-visible-{digest}"
                visible = st.session_state.get(visible_key, 8)
                start = int(page_number) - 1
                end = min(start + visible, len(pdf))
                st.caption(f"Halaman {start + 1}–{end} dari {len(pdf)}. Scroll ke bawah untuk melihat lembar berikutnya.")
                with st.container(height=850, border=True):
                    for index in range(start, end):
                        page = pdf[index]
                        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom / 75, zoom / 75), alpha=False)
                        st.caption(f"Halaman {index + 1} dari {len(pdf)}")
                        st.image(pix.tobytes("png"), width=int(page.rect.width * zoom / 100))
                if end < len(pdf) and st.button("Muat halaman berikutnya", key=f"{key_prefix}-more-{digest}"):
                    st.session_state[visible_key] = visible + 8
                    st.rerun()
        except Exception as e:
            st.warning(f"Gagal menampilkan pratinjau PDF: {e}")
    else:
        st.info("Pratinjau visual belum tersedia di sistem. Anda tetap dapat langsung mengunduh file DOCX di bawah.")

    st.write("")
    st.download_button(
        label=f"📥 Unduh {filename}",
        data=docx_bytes,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        key=f"{key_prefix}-dl-{digest}",
        type="primary",
        use_container_width=True,
    )


def render_amendment_generator_page() -> None:
    st.title("📝 Dokumen Amendemen Generator")
    st.caption("Buat dokumen amandemen kontrak resmi berbasis data kontrak tersimpan dengan format pokok-pokok amandemen standar Pertamina.")

    contract_archive = ContractArchive()
    try:
        available_contracts = contract_archive.list()
    except Exception as exc:
        st.error(f"Gagal mengakses database kontrak: {exc}")
        return

    if not available_contracts:
        st.warning("⚠️ Belum ada rancangan kontrak yang tersimpan di Gudang Kontrak. Buat dan simpan rancangan kontrak terlebih dahulu.")
        return

    # 1. Pilih Kontrak
    st.markdown("##### 1. Pilih Kontrak Acuan")
    contract_options = {
        c["id"]: f"{c['project_name'][:65]}... (ID: {c['id'][:8]})"
        if len(c["project_name"]) > 65
        else f"{c['project_name']} (ID: {c['id'][:8]})"
        for c in available_contracts
    }
    selected_contract_id = st.selectbox(
        "Pilih Kontrak Induk",
        options=list(contract_options.keys()),
        format_func=lambda x: contract_options[x],
        key="amend_selected_contract_select",
    )

    # Load contract details
    try:
        contract_data = contract_archive.get(selected_contract_id)
    except Exception as e:
        st.error(f"Gagal memuat data kontrak: {e}")
        return

    # Extract initial context
    extracted = extract_context_from_contract(contract_data)

    st.write("")

    # 2. Informasi yang terekstraksi & Form Pengaturan (di-hide di dalam tag details expander)
    st.markdown("##### 2. Informasi Kontrak & Penyesuaian Klausul")
    st.caption("Informasi hasil ekstraksi dan parameter perubahan disembunyikan secara default. Buka untuk meninjau atau menyesuaikan:")

    with st.expander("📋 Informasi Kontrak & Pengaturan Amandemen", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            project_name = st.text_area("Nama Pekerjaan / Proyek", value=extracted["project_name"], height=80, key="amend_inp_proj_name")
            contract_ref = st.text_input("Referensi Nomor Kontrak Induk", value=extracted["contract_ref"], key="amend_inp_ref")
            contract_date = st.text_input("Tanggal Kontrak Induk", value=extracted["contract_date"], key="amend_inp_cdate")
            amendment_level = st.selectbox("Tingkat Amendemen", ["Amendemen I", "Amendemen II", "Amendemen III", "Amendemen IV"], index=1, key="amend_inp_lvl")
            tanggal_amendemen = st.text_input("Tanggal Amendemen Ditandatangani", value=extracted["tanggal_amendemen"], key="amend_inp_tgl_amend")

        with c2:
            company_name = st.text_input("Nama Perusahaan (Pihak I)", value=extracted["company_name"], key="amend_inp_comp")
            company_rep_name = st.text_input("Pejabat Perusahaan", value=extracted["company_rep_name"], key="amend_inp_comp_rep")
            company_rep_title = st.text_input("Jabatan Pejabat Perusahaan", value=extracted["company_rep_title"], key="amend_inp_comp_title")
            contractor_name = st.text_input("Nama Kontraktor (Pihak II)", value=extracted["contractor_name"], key="amend_inp_kont")
            contractor_rep_name = st.text_input("Pejabat Kontraktor", value=extracted["contractor_rep_name"], key="amend_inp_kont_rep")
            contractor_rep_title = st.text_input("Jabatan Pejabat Kontraktor", value=extracted["contractor_rep_title"], key="amend_inp_kont_title")

        st.divider()
        st.markdown("**Nilai & Waktu Pekerjaan Baru**")
        c_fin1, c_fin2 = st.columns(2)
        with c_fin1:
            nilai_baru = st.number_input("Nilai Pekerjaan Baru (Rp)", value=int(extracted["nilai_pekerjaan_baru"]), step=1000000, key="amend_inp_nilai")
            str_rp, str_terb = format_rupiah_lengkap(nilai_baru)
            st.caption(f"Format: **{str_rp}** {str_terb}")
            tanggal_sp3mk = st.text_input("Tanggal SP3MK", value=extracted["tanggal_sp3mk"], key="amend_inp_sp3mk_date")
        with c_fin2:
            nomor_sp3mk = st.text_input("Nomor SP3MK", value=extracted["nomor_sp3mk"], key="amend_inp_sp3mk_no")
            durasi_mpp = st.number_input("Durasi Masa Pemeliharaan (Bulan)", value=int(extracted["durasi_bulan_pemeliharaan"]), min_value=1, max_value=36, key="amend_inp_mpp")
            tanggal_berlaku = st.text_input("Tanggal Mulai Berlaku Amendemen", value=extracted["tanggal_berlaku_amendemen"], key="amend_inp_tgl_berlaku")

        st.divider()
        st.markdown("**Klausul Perubahan & Dokumen Acuan**")
        dasar_dokumen_text = st.text_area(
            "Dasar Perubahan (Surat / Notulen / Berita Acara - satu per baris)",
            value="\n".join(extracted["dasar_dokumen"]),
            height=120,
            key="amend_inp_dasar_docs",
        )
        lingkup_pekerjaan = st.text_area("Klausul Butir Lingkup Pekerjaan", value=extracted["lingkup_pekerjaan"], height=70, key="amend_inp_lingkup")
        tambahan_pekerjaan = st.text_area("Tambahan Pekerjaan Spesifik (Opsional, kosongkan jika tidak ada)", value=extracted["tambahan_pekerjaan"], height=70, key="amend_inp_tambahan")

    st.write("")

    # 3. Tombol Eksekusi Generate
    if st.button("🚀 Generate Dokumen Amandemen", key="btn_run_generate_amendment", type="primary", use_container_width=True):
        with st.spinner("Menyusun dokumen amandemen resmi berbasis format pokok-pokok kontrak..."):
            dasar_list = [line.strip() for line in dasar_dokumen_text.splitlines() if line.strip()]
            params_to_build = {
                "project_name": project_name.strip(),
                "contract_ref": contract_ref.strip(),
                "contract_date": contract_date.strip(),
                "amendment_level": amendment_level.strip(),
                "tanggal_amendemen": tanggal_amendemen.strip(),
                "company_name": company_name.strip(),
                "company_office": extracted["company_office"],
                "company_rep_name": company_rep_name.strip(),
                "company_rep_title": company_rep_title.strip(),
                "contractor_name": contractor_name.strip(),
                "contractor_office": extracted["contractor_office"],
                "contractor_rep_name": contractor_rep_name.strip(),
                "contractor_rep_title": contractor_rep_title.strip(),
                "nilai_pekerjaan_baru": nilai_baru,
                "tanggal_sp3mk": tanggal_sp3mk.strip(),
                "nomor_sp3mk": nomor_sp3mk.strip(),
                "durasi_bulan_pemeliharaan": durasi_mpp,
                "tanggal_berlaku_amendemen": tanggal_berlaku.strip(),
                "klausul_lampiran": extracted["klausul_lampiran"],
                "lingkup_pekerjaan": lingkup_pekerjaan.strip(),
                "tambahan_pekerjaan": tambahan_pekerjaan.strip() if tambahan_pekerjaan.strip() else None,
                "dasar_dokumen": dasar_list if dasar_list else extracted["dasar_dokumen"],
                "portal_autentifikasi": extracted["portal_autentifikasi"],
            }

            try:
                docx_bytes = build_amendment_docx(params_to_build)
                amend_archive = AmendmentArchive()
                amend_id = amend_archive.save(
                    project_name=project_name.strip(),
                    amendment_level=amendment_level.strip(),
                    amendment_docx=docx_bytes,
                    contract_draft_id=selected_contract_id,
                    metadata=params_to_build,
                )
                filename = f"{amendment_level.replace(' ', '_')}_{project_name[:25].strip().replace(' ', '_')}_{amend_id[:8]}.docx"
                st.session_state["last_generated_amendment"] = {
                    "id": amend_id,
                    "filename": filename,
                    "docx": docx_bytes,
                    "project_name": project_name.strip(),
                }
                st.success(f"✅ Dokumen amandemen berhasil digenerate dan tersimpan di database dengan ID: `{amend_id[:8]}`!")
            except Exception as exc:
                st.error(f"Gagal membuat dokumen amandemen: {exc}")

    # Display generated preview & download
    if st.session_state.get("last_generated_amendment"):
        cur = st.session_state["last_generated_amendment"]
        st.divider()
        _render_amendment_page_preview(cur["docx"], cur["filename"])
