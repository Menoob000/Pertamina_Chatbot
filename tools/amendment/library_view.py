"""Browse archived contract amendment documents separately from the main pages."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pymupdf
import streamlit as st

from tools.rks.library_view import _VISIBLE_SCROLLBAR_STYLE
from tools.tender.preview import prepare_tender_preview, preview_key
from .archive import AmendmentArchive


def _date_label(value: str) -> str:
    try:
        return datetime.fromisoformat(value).astimezone(ZoneInfo("Asia/Jakarta")).strftime("%d %b %Y, %H:%M WIB")
    except (TypeError, ValueError):
        return value or "Tanggal tidak tersedia"


def _render_amendment_preview(record: dict) -> None:
    docx_data = record["docx"]
    digest = preview_key(docx_data)
    key = f"amendment-preview-{digest}"
    st.caption(f"Dokumen Amandemen: {record['amendment_filename']}")
    st.caption(f"Tingkat: {record['amendment_level']} · ID: {record['id'][:8]}")

    st.download_button(
        "Unduh Dokumen Amandemen (DOCX)",
        docx_data,
        file_name=record["amendment_filename"],
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        key=f"amendment-download-{record['id']}",
        type="primary",
    )

    retry = st.button("Coba preview lagi", key=f"amendment-retry-{digest}") if (
        key in st.session_state and not st.session_state[key].get("available")) else False
    if retry or key not in st.session_state:
        with st.spinner("Menyiapkan pratinjau dokumen amandemen..."):
            try:
                st.session_state[key] = prepare_tender_preview(docx_data)
            except (OSError, ValueError, RuntimeError) as exc:
                st.session_state[key] = {"available": False, "message": str(exc)}
    preview = st.session_state[key]
    if not preview.get("available"):
        st.warning(preview.get("message") or "Preview belum tersedia. DOCX tetap dapat diunduh langsung.")
        return

    try:
        with pymupdf.open(str(preview["pdf"])) as pdf:
            first_col, zoom_col = st.columns([1, 2])
            first = first_col.number_input("Halaman awal", 1, len(pdf), 1, key=f"amendment-page-{digest}")
            zoom = zoom_col.select_slider("Perbesaran", [75, 100, 125, 150], value=100,
                                          key=f"amendment-zoom-{digest}")
            visible_key = f"amendment-visible-{digest}"
            visible = st.session_state.get(visible_key, 8)
            start = int(first) - 1
            end = min(start + visible, len(pdf))
            st.caption(f"Halaman {start + 1}–{end} dari {len(pdf)}. Scroll untuk melihat halaman berikutnya.")
            with st.container(height=900, border=True):
                for index in range(start, end):
                    page = pdf[index]
                    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom / 75, zoom / 75), alpha=False)
                    st.caption(f"Halaman {index + 1} dari {len(pdf)}")
                    st.image(pix.tobytes("png"), width=int(page.rect.width * zoom / 100))
            if end < len(pdf) and st.button("Muat halaman berikutnya", key=f"amendment-more-{digest}"):
                st.session_state[visible_key] = visible + 8
                st.rerun()
    except (OSError, ValueError, RuntimeError) as exc:
        st.warning(f"Preview belum dapat dibuka: {exc}")


def render_amendment_library() -> None:
    st.html(_VISIBLE_SCROLLBAR_STYLE.replace("rks_library_list_scroll", "amendment_library_list_scroll"))
    st.title("Gudang Dokumen Amandemen")
    st.caption("Daftar arsip dokumen amandemen kontrak yang telah digenerate dan tersimpan di PostgreSQL.")
    archive = AmendmentArchive()
    try:
        documents = archive.list()
    except Exception as exc:
        st.error(f"Gudang amandemen belum dapat diakses: {exc}")
        return
    if not documents:
        st.info("Belum ada dokumen amandemen tersimpan. Buat dokumen amandemen terlebih dahulu.")
        return

    search_col, level_col = st.columns([3, 1])
    search = search_col.text_input("Cari dokumen amandemen", placeholder="Nama pekerjaan, nomor, atau ID",
                                   key="amendment_library_search").casefold().strip()
    levels = ["Semua"] + sorted(list({item["amendment_level"] for item in documents}))
    level_filter = level_col.selectbox("Tingkat Amendemen", levels, key="amendment_library_level_filter")

    with st.expander("📤 Unggah Contoh / Template Dokumen Amandemen Baru (DOCX)", expanded=False):
        st.caption("Unggah berkas contoh dokumen amandemen (format .docx) untuk diarsipkan ke PostgreSQL:")
        up_col1, up_col2 = st.columns(2)
        with up_col1:
            up_proj = st.text_input("Nama Pekerjaan / Proyek", key="up_amend_proj_name")
            up_lvl = st.selectbox("Tingkat Amendemen", ["Amendemen I", "Amendemen II", "Amendemen III", "Amendemen IV"], index=1, key="up_amend_lvl")
        with up_col2:
            uploaded_file = st.file_uploader("Pilih Berkas DOCX", type=["docx"], key="up_amend_file_uploader")
        if st.button("Simpan ke Database Gudang Amandemen", key="btn_save_uploaded_amendment", type="primary"):
            if not up_proj.strip():
                st.error("Nama pekerjaan/proyek wajib diisi.")
            elif not uploaded_file:
                st.error("Pilih file DOCX terlebih dahulu.")
            else:
                try:
                    file_bytes = uploaded_file.read()
                    new_id = archive.save(
                        project_name=up_proj.strip(),
                        amendment_level=up_lvl,
                        amendment_docx=file_bytes,
                        custom_filename=uploaded_file.name
                    )
                    st.success(f"✅ Berhasil mengunggah dan menyimpan contoh amandemen ke PostgreSQL (ID: `{new_id[:8]}`)!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menyimpan ke database: {e}")

    filtered = [
        item for item in documents
        if (not search or search in " ".join((item["project_name"], item["id"], item["amendment_filename"], item["amendment_level"])).casefold())
        and (level_filter == "Semua" or item["amendment_level"] == level_filter)
    ]
    st.caption(f"Menampilkan {len(filtered)} dari {len(documents)} dokumen amandemen.")
    if not filtered:
        st.info("Tidak ada dokumen amandemen yang cocok.")
        return

    options = {item["id"]: item for item in filtered}
    requested = st.query_params.get("amendment_draft", "")
    if requested in options:
        st.session_state["amendment_library_selected"] = requested
    selected = st.session_state.get("amendment_library_selected")
    if selected not in options:
        selected = filtered[0]["id"]
        st.session_state["amendment_library_selected"] = selected

    st.session_state.setdefault("amendment_library_show_preview", True)
    head, toggle = st.columns([5, 1], vertical_alignment="center")
    head.subheader("Daftar Dokumen Amandemen")
    if toggle.button("Sembunyikan peninjauan" if st.session_state["amendment_library_show_preview"]
                     else "Tampilkan peninjauan", key="amendment_library_toggle", use_container_width=True):
        st.session_state["amendment_library_show_preview"] = not st.session_state["amendment_library_show_preview"]
        st.rerun()

    show_preview = st.session_state["amendment_library_show_preview"]
    if show_preview:
        list_col, preview_col = st.columns([1, 2], gap="large", vertical_alignment="top")
    else:
        list_col, preview_col = st.container(), None

    with list_col:
        visible = st.session_state.get("amendment_library_visible", 20)
        with st.container(height=720, border=True, key="amendment_library_list_scroll"):
            for item in filtered[:visible]:
                with st.container(border=True):
                    st.markdown(f"**{item['project_name']}**")
                    st.caption(f"**{item['amendment_level']}** · {_date_label(item['created_at'])} · ID {item['id'][:8]}")
                    if st.button("Tinjau amandemen", key=f"amend-open-{item['id']}", use_container_width=True):
                        st.session_state["amendment_library_selected"] = item["id"]
                        st.query_params["amendment_draft"] = item["id"]
                        st.rerun()
        if len(filtered) > visible:
            with st.container(border=True):
                st.caption(f"{len(filtered) - visible} dokumen lainnya belum ditampilkan.")
                if st.button("Tampilkan berikutnya", key="amendment_library_more", use_container_width=True):
                    st.session_state["amendment_library_visible"] = visible + 20
                    st.rerun()

    if preview_col is not None:
        with preview_col:
            st.subheader("Peninjauan Dokumen Amandemen")
            st.caption(options[selected]["project_name"])
            try:
                _render_amendment_preview(archive.get(selected))
            except (OSError, ValueError, KeyError) as exc:
                st.error(f"Dokumen amandemen tidak dapat dibuka: {exc}")
