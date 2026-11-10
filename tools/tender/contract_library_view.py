"""Browse archived contract drafts separately from the RKS and tender pages."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pymupdf
import streamlit as st

from tools.rks.library_view import _VISIBLE_SCROLLBAR_STYLE

from .contract_archive import ContractArchive
from .preview import prepare_tender_preview, preview_key


def _date_label(value: str) -> str:
    try:
        return datetime.fromisoformat(value).astimezone(ZoneInfo("Asia/Jakarta")).strftime("%d %b %Y, %H:%M WIB")
    except (TypeError, ValueError):
        return value or "Tanggal tidak tersedia"


def _render_contract_preview(record: dict) -> None:
    docx_data = record["docx"]
    digest = preview_key(docx_data)
    key = f"contract-preview-{digest}"
    st.caption(f"Rancangan kontrak dari tender: {record['tender_filename']}")
    if record.get("rks_artifact_id"):
        st.caption(f"RKS asal: {record['rks_artifact_id'][:8]}")
        if st.button("Lihat RKS asal", key=f"contract-rks-{record['id']}"):
            st.session_state["show_contract_library"] = False
            st.session_state["show_rks_library"] = True
            st.query_params["rks_artifact"] = record["rks_artifact_id"]
            st.rerun()

    st.download_button(
        "Unduh rancangan kontrak (DOCX)", docx_data,
        file_name=record["contract_filename"],
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        key=f"contract-download-{record['id']}",
    )

    retry = st.button("Coba preview lagi", key=f"contract-retry-{digest}") if (
        key in st.session_state and not st.session_state[key].get("available")) else False
    if retry or key not in st.session_state:
        with st.spinner("Menyiapkan preview rancangan kontrak..."):
            try:
                st.session_state[key] = prepare_tender_preview(docx_data)
            except (OSError, ValueError, RuntimeError) as exc:
                st.session_state[key] = {"available": False, "message": str(exc)}
    preview = st.session_state[key]
    if not preview.get("available"):
        st.warning(preview.get("message") or "Preview belum tersedia. DOCX tetap dapat diunduh.")
        return

    try:
        with pymupdf.open(str(preview["pdf"])) as pdf:
            first_col, zoom_col = st.columns([1, 2])
            first = first_col.number_input("Halaman awal", 1, len(pdf), 1, key=f"contract-page-{digest}")
            zoom = zoom_col.select_slider("Perbesaran", [75, 100, 125, 150], value=100,
                                          key=f"contract-zoom-{digest}")
            visible_key = f"contract-visible-{digest}"
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
            if end < len(pdf) and st.button("Muat halaman berikutnya", key=f"contract-more-{digest}"):
                st.session_state[visible_key] = visible + 8
                st.rerun()
    except (OSError, ValueError, RuntimeError) as exc:
        st.warning(f"Preview belum dapat dibuka: {exc}")


def render_contract_library() -> None:
    st.html(_VISIBLE_SCROLLBAR_STYLE.replace("rks_library_list_scroll", "contract_library_list_scroll"))
    st.title("Gudang Rancangan Kontrak")
    st.caption("Draft kontrak tersimpan di PostgreSQL. Dokumen ini belum masuk knowledge base.")
    archive = ContractArchive()
    try:
        documents = archive.list()
    except Exception as exc:
        st.error(f"Gudang kontrak belum dapat diakses: {exc}")
        return
    if not documents:
        st.info("Belum ada rancangan kontrak tersimpan. Buat dokumen tender terlebih dahulu.")
        return

    search_col, source_col = st.columns([3, 1])
    search = search_col.text_input("Cari rancangan kontrak", placeholder="Nama pekerjaan, tender, atau ID",
                                   key="contract_library_search").casefold().strip()
    source = source_col.selectbox("Asal RKS", ["Semua", "Dengan RKS", "Tanpa RKS"],
                                  key="contract_library_source")
    filtered = [item for item in documents if
                (not search or search in " ".join((item["project_name"], item["id"],
                     item["tender_filename"], item.get("rks_artifact_id") or "")).casefold())
                and (source == "Semua" or (source == "Dengan RKS") == bool(item["rks_artifact_id"]))]
    st.caption(f"Menampilkan {len(filtered)} dari {len(documents)} rancangan kontrak.")
    if not filtered:
        st.info("Tidak ada rancangan kontrak yang cocok.")
        return

    options = {item["id"]: item for item in filtered}
    requested = st.query_params.get("contract_draft", "")
    if requested in options:
        st.session_state["contract_library_selected"] = requested
    selected = st.session_state.get("contract_library_selected")
    if selected not in options:
        selected = filtered[0]["id"]
        st.session_state["contract_library_selected"] = selected
    st.session_state.setdefault("contract_library_show_preview", True)
    head, toggle = st.columns([5, 1], vertical_alignment="center")
    head.subheader("Daftar rancangan kontrak")
    if toggle.button("Sembunyikan peninjauan" if st.session_state["contract_library_show_preview"]
                     else "Tampilkan peninjauan", key="contract_library_toggle", use_container_width=True):
        st.session_state["contract_library_show_preview"] = not st.session_state["contract_library_show_preview"]
        st.rerun()
    show_preview = st.session_state["contract_library_show_preview"]
    if show_preview:
        list_col, preview_col = st.columns([1, 2], gap="large", vertical_alignment="top")
    else:
        list_col, preview_col = st.container(), None

    with list_col:
        visible = st.session_state.get("contract_library_visible", 20)
        with st.container(height=720, border=True, key="contract_library_list_scroll"):
            for item in filtered[:visible]:
                with st.container(border=True):
                    st.markdown(f"**{item['project_name']}**")
                    origin = f"RKS {item['rks_artifact_id'][:8]}" if item["rks_artifact_id"] else "RKS unggahan/tidak tercatat"
                    st.caption(f"{_date_label(item['created_at'])} · {item['status']} · {origin} · ID {item['id'][:8]}")
                    if st.button("Tinjau kontrak", key=f"contract-open-{item['id']}", use_container_width=True):
                        st.session_state["contract_library_selected"] = item["id"]
                        st.query_params["contract_draft"] = item["id"]
                        st.rerun()
        if len(filtered) > visible:
            with st.container(border=True):
                st.caption(f"{len(filtered) - visible} kontrak lainnya belum ditampilkan.")
                if st.button("Tampilkan kontrak berikutnya", key="contract_library_more", use_container_width=True):
                    st.session_state["contract_library_visible"] = visible + 20
                    st.rerun()

    if preview_col is not None:
        with preview_col:
            st.subheader("Peninjauan rancangan kontrak")
            st.caption(options[selected]["project_name"])
            try:
                _render_contract_preview(archive.get(selected))
            except (OSError, ValueError, KeyError) as exc:
                st.error(f"Rancangan kontrak tidak dapat dibuka: {exc}")
