"""Page-based preview of the exact finalized artifact, independent of the LLM."""
import json
from pathlib import Path

import pymupdf
import streamlit as st

from .catalog import list_sources
from .service import create_document, artifact_file, get_document, latest_document


def _continue_to_tender(artifact_id: str) -> None:
    """Select a finalized RKS before the next Streamlit rerun."""
    st.session_state["tender_rks_artifact_id"] = artifact_id
    st.session_state["tender_rks_pending_artifact_id"] = artifact_id
    st.session_state["show_rks_page"] = False
    st.session_state["nav_choice"] = "tender"
    st.session_state["app_nav_radio_menu"] = "📑 Dokumen Tender Generator"
    for key in ("extraction_done", "tf_nama_pengadaan", "tf_resiko_csms",
                "tf_prime_cost", "tf_total_kr", "tf_context_summary", "tf_boq_items",
                "last_generated_tender", "uploader_boq_file", "chk_use_generated_rks"):
        st.session_state.pop(key, None)


def render_result(result: dict, key: str = "rks", compact: bool = False):
    status = result.get("status", "gagal")
    if status == "gagal":
        st.error(result.get("message", "Pembuatan RKS gagal."))
        return
    if not compact:
        st.subheader("Template umum RKS" if result.get("mode") == "template umum" else "Draf tertata dari RKS referensi")
    if result.get("source"):
        st.write(f"**Sumber:** {result['source']['filename']}")
        st.caption(f"Dipilih otomatis; skor kecocokan {result.get('selection', {}).get('match_score', '—')}.")
        if result.get("selection", {}).get("note"):
            st.caption(result["selection"]["note"])
    else:
        st.info("Tidak ada sumber knowledge base yang cukup relevan. Dokumen berisi template umum dan placeholder.")
    st.caption(result.get("message", ""))
    csms = result.get("csms_assessment") or {}
    if csms.get("category"):
        st.caption(f"Rekomendasi awal CSMS: {csms['category']} — {csms.get('note', '')}")
    elif csms:
        st.caption(f"CSMS belum dicentang otomatis: {csms.get('note', 'Bukti belum memadai.')}")
    if status == "lengkap":
        st.success("Lengkap berdasarkan pemeriksaan pemindahan isi.")
    else:
        st.warning("Perlu pemeriksaan — lihat catatan bagian yang belum pasti.")
    with st.expander("Sumber dan catatan pemeriksaan", expanded=False):
        for alternative in result.get("selection", {}).get("alternatives", [])[:3]:
            st.caption(f"Alternatif yang tidak dipakai: {alternative['filename']}")
        for section in result.get("evidence", []):
            if section.get("sources"):
                top = section["sources"][0]
                st.caption(f"{section['section']}: {top['filename']}, halaman {top.get('page') or 'tidak tersedia'}, skor {top['score']}")
        for issue in result.get("issues", []):
            prefix = f"Halaman sumber {issue['page']}: " if issue.get("page") else ""
            st.write(prefix + issue["message"])
        st.caption(result.get("boq_note", ""))
    try:
        docx = artifact_file(result["artifact_id"], "docx")
        st.download_button("Unduh DOCX", docx.read_bytes(), f"RKS-{result['artifact_id'][:8]}.docx",
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"{key}-docx")
        st.button("Lanjutkan ke Tender", key=f"{key}-to-tender",
                  on_click=_continue_to_tender, args=(result["artifact_id"],))
        if result.get("preview", {}).get("available"):
            pdf_path = artifact_file(result["artifact_id"], "pdf")
            pdf_data = pdf_path.read_bytes()
            with pymupdf.open(stream=pdf_data, filetype="pdf") as pdf:
                left, right = st.columns([1, 2])
                page_number = left.number_input("Halaman", 1, len(pdf), 1, key=f"{key}-page")
                zoom = right.select_slider("Perbesaran", options=[75, 100, 125, 150], value=100, key=f"{key}-zoom")
                start_page = int(page_number) - 1
                st.caption(f"Halaman {page_number} sampai {len(pdf)} dari {len(pdf)}. Scroll ke bawah untuk melihat halaman berikutnya.")
                with st.container(height=900, border=True):
                    for index in range(start_page, len(pdf)):
                        page = pdf[index]
                        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom / 75, zoom / 75), alpha=False)
                        st.caption(f"Halaman {index + 1} dari {len(pdf)}")
                        st.image(pix.tobytes("png"), width=int(page.rect.width * zoom / 100))
                """
                page = pdf[int(page_number) - 1]
                pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom / 75, zoom / 75), alpha=False)
                st.caption(f"Halaman {page_number} dari {len(pdf)} • dirender dari DOCX unduhan yang sama")
                st.image(pix.tobytes("png"), width=int(page.rect.width * zoom / 100))
                """
            st.download_button("Unduh PDF yang dipreview", pdf_data, f"RKS-{result['artifact_id'][:8]}.pdf",
                               "application/pdf", key=f"{key}-pdf")
        else:
            st.info(result.get("preview", {}).get("message", "Preview belum tersedia."))
    except (OSError, ValueError) as exc:
        st.error(f"Dokumen tidak dapat dibuka. Buat ulang RKS. {exc}")


def render_chat_preview(document: dict, thread_id: str):
    """Render the generated pages in the chat's primary document panel."""
    tool_result = document.get("rks_result")
    if tool_result is not None:
        if not tool_result.get("artifact_id"):
            render_tool_result(tool_result, f"chat-{thread_id}")
            return
        try:
            result = get_document(tool_result["artifact_id"])
            render_result(result, f"chat-{thread_id}-{result['artifact_id']}", compact=True)
        except (OSError, ValueError):
            st.error("Hasil RKS pada percakapan ini tidak tersedia. Buat ulang RKS dari sumbernya.")
        return

    pdf_path = document.get("pdf_path")
    source = next((s for s in list_sources() if pdf_path and
                   Path(s["path"]).resolve() == Path(pdf_path).resolve()), None)
    if source is None:
        st.info("Pilih atau ambil RKS acuan dari knowledge base untuk membuat preview halaman.")
        return
    key = f"chat-rks-{thread_id}-{source['source_id']}"
    retry = st.button("Buat ulang DOCX dan preview", key=f"{key}-retry")
    result = st.session_state.get(key)
    if not retry and (result is None or not result.get("preview", {}).get("available")):
        result = latest_document(source["source_id"]) or result
    if result is None or retry:
        with st.spinner("Menyiapkan DOCX dan preview halaman dari RKS acuan…"):
            result = create_document(source["filename"], source["source_id"])
    st.session_state[key] = result
    render_result(result, f"{key}-{result.get('artifact_id', 'failed')}", compact=True)


def render_rks_page():
    st.title("Pembuatan RKS")
    st.write("Tulis pekerjaan yang dibutuhkan. Sistem memilih sumber secara otomatis atau menyiapkan template umum bila tidak ada sumber yang sesuai.")
    with st.form("rks-search"):
        query = st.text_input("Pekerjaan yang dibutuhkan", placeholder="Buatkan RKS overhaul tangki")
        search = st.form_submit_button("Buat DOCX dan preview", type="primary")
    if search:
        st.session_state.pop("rks_result", None)
        if query.strip():
            with st.spinner("Mencari sumber, membuat DOCX, dan merender preview?"):
                st.session_state["rks_result"] = create_document(query)
        else:
            st.info("Tulis jenis pekerjaan terlebih dahulu.")
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
