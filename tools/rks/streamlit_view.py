"""Page-based preview of the exact finalized artifact, independent of the LLM."""
import json

import pymupdf
import streamlit as st

from .catalog import public_source
from .service import search_sources, create_document, artifact_file, get_document


def render_result(result: dict, key: str = "rks"):
    status = result.get("status", "gagal")
    if status == "gagal":
        st.error(result.get("message", "Pembuatan RKS gagal."))
        return
    st.subheader("Draf tertata dari RKS referensi")
    st.write(f"**Sumber:** {result['source']['filename']}")
    st.caption(result.get("message", ""))
    if status == "lengkap":
        st.success("Lengkap berdasarkan pemeriksaan pemindahan isi.")
    else:
        st.warning("Perlu pemeriksaan — lihat catatan bagian yang belum pasti.")
    with st.expander("Sumber dan catatan pemeriksaan", expanded=bool(result.get("issues"))):
        for issue in result.get("issues", []):
            prefix = f"Halaman sumber {issue['page']}: " if issue.get("page") else ""
            st.write(prefix + issue["message"])
        st.caption(result.get("boq_note", ""))
    try:
        docx = artifact_file(result["artifact_id"], "docx")
        st.download_button("Unduh DOCX", docx.read_bytes(), f"RKS-{result['artifact_id'][:8]}.docx",
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"{key}-docx")
        if result.get("preview", {}).get("available"):
            pdf_path = artifact_file(result["artifact_id"], "pdf")
            pdf_data = pdf_path.read_bytes()
            with pymupdf.open(stream=pdf_data, filetype="pdf") as pdf:
                left, right = st.columns([1, 2])
                page_number = left.number_input("Halaman", 1, len(pdf), 1, key=f"{key}-page")
                zoom = right.select_slider("Perbesaran", options=[75, 100, 125, 150], value=100, key=f"{key}-zoom")
                page = pdf[int(page_number) - 1]
                pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom / 75, zoom / 75), alpha=False)
                st.caption(f"Halaman {page_number} dari {len(pdf)} • dirender dari DOCX unduhan yang sama")
                st.image(pix.tobytes("png"), width=int(page.rect.width * zoom / 100))
            st.download_button("Unduh PDF yang dipreview", pdf_data, f"RKS-{result['artifact_id'][:8]}.pdf",
                               "application/pdf", key=f"{key}-pdf")
        else:
            st.info(result.get("preview", {}).get("message", "Preview belum tersedia."))
    except (OSError, ValueError) as exc:
        st.error(f"Dokumen tidak dapat dibuka. Buat ulang RKS. {exc}")


def render_rks_page():
    st.title("Pembuatan RKS")
    st.write("Temukan RKS acuan, tata isinya ke Word, lalu periksa halaman hasilnya.")
    with st.form("rks-search"):
        query = st.text_input("Pekerjaan yang dibutuhkan", placeholder="Buatkan RKS overhaul tangki")
        search = st.form_submit_button("Cari RKS acuan", type="primary")
    if search:
        # Clear a previous result as soon as the source request changes.
        st.session_state.pop("rks_result", None)
        st.session_state.pop("rks_source_choice", None)
        st.session_state["rks_query"] = query
        st.session_state["rks_candidates"] = [public_source(x) for x in search_sources(query)] if query.strip() else []
    candidates = st.session_state.get("rks_candidates", [])
    if candidates:
        def clear_result():
            st.session_state.pop("rks_result", None)
        selected = st.selectbox("RKS acuan", range(len(candidates)),
                                format_func=lambda i: f"{candidates[i]['filename']} ({candidates[i]['pages']} halaman)",
                                key="rks_source_choice", on_change=clear_result)
        if st.button("Buat DOCX dan preview", type="primary"):
            st.session_state.pop("rks_result", None)
            with st.spinner("Memindahkan isi sumber dan merender halaman…"):
                st.session_state["rks_result"] = create_document(st.session_state["rks_query"], candidates[selected]["source_id"])
    elif search:
        st.info("RKS belum ditemukan. Coba jenis pekerjaan atau nomor aset yang lebih spesifik.")
    if st.session_state.get("rks_result"):
        render_result(st.session_state["rks_result"])


def render_tool_result(content, key: str):
    try:
        result = json.loads(content) if isinstance(content, str) else content
        if isinstance(result, dict) and result.get("artifact_id"):
            render_result(get_document(result["artifact_id"]), key)
        elif isinstance(result, dict) and result.get("status") == "pilih sumber":
            st.info(result["message"])
            for candidate in result.get("candidates", []):
                st.write(candidate["filename"])
        elif isinstance(result, dict) and result.get("status") == "gagal":
            st.error(result.get("message", "Pembuatan RKS gagal."))
    except (ValueError, OSError, TypeError):
        return
