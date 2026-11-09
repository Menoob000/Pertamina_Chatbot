"""Browse finalized RKS artifacts and continue from a selected document."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from .service import get_document, list_documents
from .streamlit_view import _continue_to_tender, render_result


_VISIBLE_SCROLLBAR_STYLE = """
<style>
/* Keep the RKS list scrollbar visible, even without hover. */
div[class*="st-key-rks_library_list_scroll"],
div[class*="st-key-rks_library_list_scroll"] [data-testid="stVerticalBlock"] {
    overflow-y: scroll !important;
    scrollbar-width: thin !important;
    scrollbar-color: #94A3B8 transparent !important;
}
div[class*="st-key-rks_library_list_scroll"]::-webkit-scrollbar,
div[class*="st-key-rks_library_list_scroll"] [data-testid="stVerticalBlock"]::-webkit-scrollbar {
    display: block !important;
    width: 8px !important;
    height: 8px !important;
}
div[class*="st-key-rks_library_list_scroll"]::-webkit-scrollbar-track,
div[class*="st-key-rks_library_list_scroll"] [data-testid="stVerticalBlock"]::-webkit-scrollbar-track {
    background: transparent !important;
}
div[class*="st-key-rks_library_list_scroll"]::-webkit-scrollbar-thumb,
div[class*="st-key-rks_library_list_scroll"] [data-testid="stVerticalBlock"]::-webkit-scrollbar-thumb {
    background: #94A3B8 !important;
    border: 0 !important;
    border-radius: 999px !important;
    min-height: 24px !important;
}
div[class*="st-key-rks_library_list_scroll"]::-webkit-scrollbar-button,
div[class*="st-key-rks_library_list_scroll"] [data-testid="stVerticalBlock"]::-webkit-scrollbar-button {
    display: none !important;
    width: 0 !important;
    height: 0 !important;
}
</style>
"""


def _date_label(value: str) -> str:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(ZoneInfo("Asia/Jakarta")).strftime("%d %b %Y, %H:%M WIB")
    except (TypeError, ValueError):
        return value or "Tanggal tidak tersedia"


def render_rks_library() -> None:
    st.html(_VISIBLE_SCROLLBAR_STYLE)
    st.title("Gudang RKS")
    st.caption("RKS hasil generator yang tersimpan di perangkat ini.")
    documents = list_documents(limit=500)
    if not documents:
        st.info("Belum ada RKS yang tersimpan. Buat RKS terlebih dahulu.")
        return

    search_col, status_col, mode_col = st.columns([3, 1, 1])
    search = search_col.text_input("Cari RKS", placeholder="Judul, ID, atau nama sumber", key="rks_library_search").casefold().strip()
    statuses = sorted({item["status"] for item in documents})
    status = status_col.selectbox("Status", ["Semua", *statuses], key="rks_library_status")
    modes = sorted({item["mode"] for item in documents})
    mode = mode_col.selectbox("Sumber", ["Semua", *modes], key="rks_library_mode")

    filtered = [item for item in documents if
                (not search or search in " ".join((item["title"], item["artifact_id"],
                    (item.get("source") or {}).get("filename") or "")).casefold())
                and (status == "Semua" or item["status"] == status)
                and (mode == "Semua" or item["mode"] == mode)]
    st.caption(f"Menampilkan {len(filtered)} dari {len(documents)} RKS tersimpan.")
    if not filtered:
        st.info("Tidak ada RKS yang cocok dengan pencarian atau filter.")
        return

    options = {item["artifact_id"]: item for item in filtered}
    requested = st.query_params.get("rks_artifact", "")
    if requested in options and requested != st.session_state.get("rks_library_selected"):
        st.session_state["rks_library_selected"] = requested
    selected = st.session_state.get("rks_library_selected")
    if selected not in options:
        selected = filtered[0]["artifact_id"]
        st.session_state["rks_library_selected"] = selected

    if "rks_library_show_preview" not in st.session_state:
        st.session_state["rks_library_show_preview"] = True
    title_col, action_col = st.columns([5, 1], vertical_alignment="center")
    title_col.subheader("Daftar RKS")
    if action_col.button(
        "Sembunyikan peninjauan" if st.session_state["rks_library_show_preview"] else "Tampilkan peninjauan",
        key="rks_library_toggle_preview", use_container_width=True,
    ):
        st.session_state["rks_library_show_preview"] = not st.session_state["rks_library_show_preview"]
        st.rerun()

    show_preview = st.session_state["rks_library_show_preview"]
    if show_preview:
        list_col, preview_col = st.columns([1, 2], gap="large", vertical_alignment="top")
    else:
        list_col = st.container()
        preview_col = None
    with list_col:
        visible = st.session_state.get("rks_library_visible", 20)
        # The inner list scrolls. The pagination card remains a sibling below.
        with st.container(height=720, border=True, key="rks_library_list_scroll"):
            for item in filtered[:visible]:
                artifact_id = item["artifact_id"]
                with st.container(border=True):
                    st.markdown(f"**{item['title']}**")
                    source = (item.get("source") or {}).get("filename") or "Template umum, tanpa sumber KB"
                    st.caption(f"{_date_label(item['created_at'])} · {item['status']} · {source} · ID {artifact_id[:8]}")
                    related = item.get("related_documents") or []
                    if related:
                        st.caption(f"{len(related)} dokumen tender terkait")
                    if st.button("Tinjau RKS", key=f"library-open-{artifact_id}", use_container_width=True):
                        st.session_state["rks_library_selected"] = artifact_id
                        st.query_params["rks_artifact"] = artifact_id
                        st.rerun()
                    if item["status"] != "gagal":
                        st.button("Buat Dokumen Tender", key=f"library-tender-{artifact_id}",
                                  on_click=_continue_to_tender, args=(artifact_id,), use_container_width=True)
        if len(filtered) > visible:
            with st.container(border=True):
                st.caption(f"{len(filtered) - visible} RKS lainnya belum ditampilkan.")
                if st.button("Tampilkan RKS berikutnya", key="rks_library_more", use_container_width=True):
                    st.session_state["rks_library_visible"] = visible + 20
                    st.rerun()

    if preview_col is not None:
        with preview_col:
            item = options[selected]
            st.subheader("Peninjauan RKS")
            st.caption(item["title"])
            try:
                render_result(get_document(selected), key=f"library-{selected}", compact=True)
            except (OSError, ValueError, KeyError) as exc:
                st.error(f"RKS tidak dapat dibuka: {exc}")

            related = item.get("related_documents") or []
            if related:
                st.subheader("Dokumen tender terkait")
                for index, document in enumerate(related):
                    try:
                        st.download_button(
                            f"Unduh {document['filename']}", document["path"].read_bytes(),
                            file_name=document["filename"],
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"library-related-{selected}-{index}",
                        )
                    except OSError:
                        st.warning(f"Dokumen tender {document['filename']} tidak tersedia lagi.")
