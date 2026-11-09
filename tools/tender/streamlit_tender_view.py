"""
Streamlit UI View for Dokumen Tender Generator.
Interacts with the dedicated FastAPI service on http://127.0.0.1:8000.
Directly extracts and displays key procurement information without tedious manual forms.
"""

import os
import io
import html
import requests
import pymupdf
from pathlib import Path
from typing import Optional, Dict, Any

import streamlit as st
from tools.rks.service import artifact_file, get_document
from tools.tender.preview import prepare_tender_preview, preview_key

API_HOST = os.getenv("FASTAPI_HOST", "127.0.0.1")
API_PORT = os.getenv("FASTAPI_PORT", "8000")
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", f"http://{API_HOST}:{API_PORT}")


def check_api_status() -> bool:
    try:
        r = requests.get(f"{FASTAPI_BASE_URL}/api/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def _render_preview_and_download(docx_data: bytes, filename: str, key: str) -> None:
    """Show scrollable PDF pages, then offer the exact DOCX used for preview."""
    digest = preview_key(docx_data)
    state_key = f"{key}-render-{digest}"
    st.markdown("#### Pratinjau halaman")
    retry = (st.button("Coba preview lagi", key=f"{key}-retry-{digest}")
             if state_key in st.session_state and not st.session_state[state_key].get("available") else False)
    if retry or state_key not in st.session_state:
        with st.spinner("Menyiapkan preview halaman dari dokumen tender..."):
            try:
                st.session_state[state_key] = prepare_tender_preview(docx_data)
            except (OSError, ValueError) as exc:
                st.session_state[state_key] = {"available": False, "message": str(exc)}

    preview = st.session_state[state_key]
    download_data = docx_data
    if preview.get("available"):
        try:
            pdf_data = preview["pdf"].read_bytes()
            download_data = preview["docx"].read_bytes()
            with pymupdf.open(stream=pdf_data, filetype="pdf") as pdf:
                left, right = st.columns([1, 2])
                page_number = left.number_input("Halaman awal", 1, len(pdf), 1,
                                                key=f"{key}-page-{digest}")
                zoom = right.select_slider("Perbesaran", options=[75, 100, 125, 150],
                                           value=100, key=f"{key}-zoom-{digest}")
                visible_key = f"{key}-visible-{digest}"
                visible = st.session_state.get(visible_key, 8)
                start = int(page_number) - 1
                end = min(start + visible, len(pdf))
                st.caption(f"Halaman {start + 1}–{end} dari {len(pdf)}. Scroll ke bawah untuk melihat halaman berikutnya.")
                with st.container(height=900, border=True):
                    for index in range(start, end):
                        page = pdf[index]
                        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom / 75, zoom / 75), alpha=False)
                        st.caption(f"Halaman {index + 1} dari {len(pdf)}")
                        st.image(pix.tobytes("png"), width=int(page.rect.width * zoom / 100))
                if end < len(pdf) and st.button("Muat halaman berikutnya", key=f"{key}-more-{digest}"):
                    st.session_state[visible_key] = visible + 8
                    st.rerun()
            st.caption("Preview ini berasal dari DOCX yang sama dengan berkas unduhan di bawah.")
        except (OSError, ValueError, RuntimeError) as exc:
            st.warning(f"Preview belum dapat ditampilkan: {exc}")
            download_data = docx_data
    else:
        st.warning(preview.get("message") or "Renderer PDF belum tersedia.")

    st.download_button(
        label=f"📥 Unduh {filename}", data=download_data, file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        key=f"{key}-download-{digest}", type="primary", use_container_width=True,
    )


def _render_tender_download(result: dict, render_download_card_fn) -> None:
    """Retrieve the generated DOCX from the API or the local output folder."""
    details = result.get("details") or {}
    filename = os.path.basename(result.get("filename") or "Dokumen_Tender.docx")
    st.divider()
    st.markdown("### 📥 File Dokumen Tender Siap Ditinjau")
    st.write(f"**Nama Pengadaan:** {details.get('nama_pengadaan')}")
    st.write(f"**Nomor Tender:** `{details.get('nomor_tender')}`")
    st.write(f"**Kriteria Teknis Lampiran 2A:** {details.get('kriteria_teknis_count', 0)} kriteria terukur disusun")
    st.write("**Cakupan Dokumen:** Sampul resmi, Bagian A (Tabel IKPP 40 butir, 30 artikel umum), Lampiran 1A-8, Bagian B (Rancangan Kontrak 18 pasal, PI-07, SP3MK).")

    docx_data = None
    download_error = None
    download_url = result.get("download_url")
    if download_url:
        try:
            response = requests.get(f"{FASTAPI_BASE_URL}{download_url}", timeout=30)
            response.raise_for_status()
            docx_data = response.content
        except requests.RequestException as exc:
            download_error = str(exc)
    if docx_data is None:
        local_file = Path(result.get("filepath") or "")
        if not local_file.is_file():
            local_file = Path(__file__).resolve().parents[2] / "output" / filename
        if local_file.is_file():
            docx_data = local_file.read_bytes()
    if docx_data is None:
        st.error(f"File tender tidak tersedia. {download_error or 'Periksa berkas keluaran backend.'}")
        return
    _render_preview_and_download(docx_data, filename, "tender-current")


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
        "RKS dan BOQ digunakan untuk mengisi data yang dapat dibaca. Data yang tidak ditemukan perlu Anda isi sebelum dokumen dibuat."
    )

    col_rks, col_boq = st.columns(2)

    # RKS Selection
    with col_rks:
        st.markdown("##### 📄 Dokumen RKS (Rencana Kerja & Syarat)")
        generated_rks_id = st.session_state.get("tender_rks_artifact_id")
        generated_rks_docx = None
        if generated_rks_id:
            try:
                generated_rks_docx = artifact_file(generated_rks_id, "docx")
                generated_rks = get_document(generated_rks_id)
            except (OSError, ValueError, KeyError):
                st.warning("RKS yang dipilih tidak tersedia atau telah berubah. Pilih RKS lain.")
            else:
                source_name = (generated_rks.get("source") or {}).get("filename") or "Template umum RKS"
                st.success(f"RKS hasil generator aktif: {source_name} ({generated_rks_id[:8]})")
        active_rks_docx = (generated_rks_docx if generated_rks_id else
                           st.session_state.get("last_exported_docx"))
        use_active_rks = False

        if active_rks_docx and os.path.exists(active_rks_docx):
            if generated_rks_docx is None:
                st.success(f"✅ RKS Aktif dari Chat: `{os.path.basename(active_rks_docx)}`")
            use_active_rks = st.checkbox(
                "Gunakan file RKS aktif ini sebagai konteks",
                value=True,
                key="chk_use_generated_rks" if generated_rks_docx else "chk_use_active_rks"
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
    pending_rks_id = st.session_state.pop("tender_rks_pending_artifact_id", None)
    auto_extract = bool(pending_rks_id and pending_rks_id == generated_rks_id and
                        generated_rks_docx and use_active_rks)

    if btn_extract or auto_extract:
        if not api_online:
            st.error("Gagal menghubungkan ke backend FastAPI. Pastikan server API menyala di port 8000.")
        else:
            with st.spinner("Menganalisa dokumen pendukung dan mengekstrak parameter pengadaan..."):
                try:
                    files_payload = {}
                    data_payload = {}

                    if use_active_rks and generated_rks_docx:
                        data_payload["rks_artifact_id"] = generated_rks_id
                        files_payload["rks_file"] = (
                            f"RKS-{generated_rks_id[:8]}.docx", generated_rks_docx.read_bytes(),
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                    elif use_active_rks and active_rks_docx:
                        data_payload["rks_filepath"] = active_rks_docx
                    elif uploaded_rks:
                        files_payload["rks_file"] = (uploaded_rks.name, uploaded_rks.getvalue(), uploaded_rks.type)

                    if uploaded_boq:
                        files_payload["boq_file"] = (uploaded_boq.name, uploaded_boq.getvalue(), uploaded_boq.type)

                    resp = requests.post(
                        f"{FASTAPI_BASE_URL}/api/tender/extract-context",
                        data=data_payload,
                        files=files_payload if files_payload else None,
                        timeout=60
                    )

                    if resp.status_code == 200:
                        extracted = resp.json()
                        for key in list(st.session_state):
                            if key.startswith("tender_field_"):
                                st.session_state.pop(key, None)
                        for key in ("tf_nama_pengadaan", "tf_resiko_csms", "tf_prime_cost", "tf_total_kr",
                                    "tf_context_summary", "tf_boq_items", "tf_sources", "tf_issues"):
                            st.session_state.pop(key, None)
                        st.session_state.tf_nama_pengadaan = extracted.get("nama_pengadaan") or ""
                        st.session_state.tf_resiko_csms = extracted.get("resiko_csms") or ""
                        st.session_state.tf_prime_cost = extracted.get("prime_cost")
                        st.session_state.tf_total_kr = extracted.get("total_dengan_kr")
                        st.session_state.tf_context_summary = extracted.get("combined_context_summary") or ""
                        st.session_state.tf_boq_items = extracted.get("boq_items") or []
                        st.session_state.tf_sources = extracted.get("sources") or {}
                        st.session_state.tf_issues = extracted.get("issues") or []
                        st.session_state.pop("last_generated_tender", None)

                        st.session_state.extraction_done = True
                        st.success("Pembacaan dokumen selesai. Periksa hasil dan lengkapi data yang belum ditemukan.")
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
        info_nama = st.session_state.get("tf_nama_pengadaan") or ""
        info_csms = st.session_state.get("tf_resiko_csms") or ""
        raw_prime = st.session_state.get("tf_prime_cost")
        info_prime = float(raw_prime) if raw_prime and raw_prime > 0 else None
        raw_kr = st.session_state.get("tf_total_kr")
        info_kr = float(raw_kr) if raw_kr and raw_kr > 0 else None
        info_context = st.session_state.get("tf_context_summary") or ""
        info_boq_items = st.session_state.get("tf_boq_items") or []
        sources = st.session_state.get("tf_sources") or {}
        for issue in st.session_state.get("tf_issues") or []:
            st.warning(issue)

        # Display Metrics Cards
        m1, m2, m3 = st.columns([2, 1, 1])
        with m1:
            st.markdown(
                f"""
                <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 16px; margin-bottom:8px;">
                    <span style="font-size:0.75rem; color:#64748B; font-weight:700; text-transform:uppercase;">📌 Nama Pengadaan</span>
                    <div style="font-size:1.05rem; font-weight:700; color:#0F172A; margin-top:4px;">{html.escape(info_nama or 'Belum ditemukan')}</div>
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
                            {html.escape(info_csms or 'Belum ditemukan')}
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
                    <div style="font-size:1.05rem; font-weight:700; color:#002D62; margin-top:4px;">{_format_rupiah(info_kr) if info_kr is not None else 'Belum ditemukan'}</div>
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
                st.write(f"**HPS Prime Cost:** `{_format_rupiah(info_prime) if info_prime is not None else 'Belum ditemukan'}`")
                st.write(f"**Item BOQ Terbaca:** `{len(info_boq_items)} baris rincian`")
                for field, source in sources.items():
                    st.caption(f"{field}: {source.get('filename', '')}, {source.get('location', '')}")
            with col_d2:
                st.markdown("**Data pengadaan lainnya:** lengkapi pada formulir di bawah sesuai dokumen resmi.")

        st.markdown("#### Lengkapi dan periksa data tender")
        st.caption("Nilai yang terisi otomatis berasal dari dokumen sumber. Kosongkan atau ubah bila hasil baca kurang tepat.")
        basic_left, basic_right = st.columns(2)
        with basic_left:
            form_nama = st.text_input("Nama pengadaan", value=info_nama, key="tender_field_nama_pengadaan")
            form_csms = st.selectbox("Risiko CSMS", ["", "Tinggi", "Sedang", "Rendah"],
                                     index=["", "Tinggi", "Sedang", "Rendah"].index(info_csms) if info_csms in ("Tinggi", "Sedang", "Rendah") else 0,
                                     format_func=lambda value: value or "Pilih risiko", key="tender_field_resiko_csms")
            form_prime = st.number_input("HPS Prime Cost (Rp)", min_value=0.0,
                                         value=info_prime or 0.0, step=1000.0, key="tender_field_prime_cost")
            form_total = st.number_input("Total HPS termasuk K&R (Rp)", min_value=0.0,
                                         value=info_kr or 0.0, step=1000.0, key="tender_field_total_dengan_kr")
        with basic_right:
            form_nomor = st.text_input("Nomor tender", key="tender_field_nomor_tender")
            form_tanggal = st.text_input("Tanggal dokumen", key="tender_field_tanggal")
            form_tkdn = st.number_input("Target TKDN minimum (%)", min_value=0.0, max_value=100.0,
                                        value=0.0, key="tender_field_tkdn_minimal")
            form_metode = st.text_input("Metode pemenuhan", key="tender_field_metode_pemenuhan")
            form_kontrak = st.text_input("Jenis kontrak", key="tender_field_jenis_kontrak")
        with st.expander("Pejabat dan jadwal pengadaan", expanded=True):
            text_fields = {
                "pejabat_procurement_nama": "Nama pejabat procurement",
                "pejabat_procurement_jabatan": "Jabatan pejabat procurement",
                "pejabat_berwenang": "Pejabat berwenang",
                "pengawas_pekerjaan": "Pengawas pekerjaan",
                "prebid_tanggal": "Tanggal pre-bid",
                "prebid_waktu": "Waktu pre-bid",
                "prebid_tempat": "Tempat atau media pre-bid",
                "pemasukan_mulai": "Awal pemasukan penawaran",
                "pemasukan_selesai": "Akhir pemasukan penawaran",
            }
            extra_fields = {field: st.text_input(label, key=f"tender_field_{field}")
                            for field, label in text_fields.items()}

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
                required = {
                    "Nama pengadaan": form_nama, "Risiko CSMS": form_csms,
                    "HPS Prime Cost": form_prime, "Total HPS": form_total,
                    "Nomor tender": form_nomor, "Tanggal dokumen": form_tanggal,
                    "Metode pemenuhan": form_metode, "Jenis kontrak": form_kontrak,
                    **{label: extra_fields[field] for field, label in text_fields.items()},
                }
                missing = [label for label, value in required.items() if not value or not str(value).strip()]
                if missing:
                    st.error("Lengkapi data berikut sebelum generate: " + ", ".join(missing))
                    return
                with st.spinner("🤖 AI sedang menyusun Dokumen Tender lengkap (IKPP 40 butir, Kriteria Lampiran 2A terukur, BoQ, dan Rancangan Kontrak 18 Pasal)..."):
                    try:
                        payload = {
                            "nama_pengadaan": form_nama,
                            "nomor_tender": form_nomor,
                            "tanggal": form_tanggal,
                            "prime_cost": form_prime,
                            "total_dengan_kr": form_total,
                            "resiko_csms": form_csms,
                            "tkdn_minimal": form_tkdn,
                            "metode_pemenuhan": form_metode,
                            "jenis_kontrak": form_kontrak,
                            **extra_fields,
                            "context_summary": info_context,
                            "boq_items": info_boq_items,
                            "output_filename": out_filename
                        }

                        res = requests.post(f"{FASTAPI_BASE_URL}/api/tender/generate", json=payload, timeout=90)

                        if res.status_code == 200:
                            gen_result = res.json()
                            st.session_state.last_generated_tender = gen_result
                            st.success(f"🎉 {gen_result.get('message', 'Dokumen Tender berhasil dibuat!')}")
                            _render_tender_download(gen_result, render_download_card_fn)
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
    if last_tender and not st.session_state.get("btn_run_tender_gen", False):
        _render_tender_download(last_tender, render_download_card_fn)
    elif not last_tender:
        output_dir = Path(__file__).resolve().parents[2] / "output"
        saved_tenders = sorted(output_dir.glob("Dokumen_Tender*.docx"),
                               key=lambda path: path.stat().st_mtime, reverse=True)
        if saved_tenders:
            with st.expander("Tinjau Dokumen Tender yang Sudah Dibuat", expanded=True):
                selected = st.selectbox("Pilih dokumen", saved_tenders,
                                        format_func=lambda path: path.name,
                                        key="tender_saved_file")
                _render_preview_and_download(selected.read_bytes(), selected.name, "tender-saved")
