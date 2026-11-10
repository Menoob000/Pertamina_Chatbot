"""Editable officials with field provenance displayed only in Streamlit."""
from copy import deepcopy

import streamlit as st

from .officers import ROLES, OFFICIAL_FIELDS, empty_officials, edit_officials


def restore_project_officials(extracted: dict, project_key: str, store) -> dict:
    result = empty_officials()
    result.update(deepcopy(extracted or {}))
    if not store or not project_key:
        return result
    saved = store.load_project_officials(project_key)
    for role in ROLES:
        previous = saved.get(role) or {}
        for field in OFFICIAL_FIELDS:
            if (previous.get("field_sources") or {}).get(field) == "user":
                result[role][field] = previous.get(field) or ""
                result[role].setdefault("field_sources", {})[field] = "user"
        for evidence in previous.get("evidence") or []:
            if evidence not in result[role].setdefault("evidence", []):
                result[role]["evidence"].append(evidence)
    return result


def render_official_editor(store=None) -> dict:
    officials = st.session_state.get("tf_officials") or empty_officials()
    if "tf_officials" not in st.session_state:
        # Keep edits from drafts saved before structured per-role fields existed.
        for legacy, role, field in (
            ("pejabat_procurement_nama", "procurement", "name"),
            ("pejabat_procurement_jabatan", "procurement", "position"),
            ("pejabat_berwenang", "authorized_officer", "position"),
            ("pengawas_pekerjaan", "work_supervisor", "position"),
        ):
            value = st.session_state.get(f"tender_field_{legacy}") or ""
            if value.strip():
                officials[role][field] = value.strip()
                officials[role]["field_sources"][field] = "user"
    project_key = st.session_state.get("tf_officials_project_key")
    scope = (st.session_state.get("current_thread_id"), project_key)
    if store and project_key and st.session_state.get("_official_editor_scope") != scope:
        try:
            officials = restore_project_officials(officials, project_key, store)
            for role in ROLES:
                for field in OFFICIAL_FIELDS:
                    st.session_state[f"tender_field_official_{role}_{field}"] = (officials.get(role) or {}).get(field) or ""
            st.session_state["_official_editor_scope"] = scope
        except Exception as exc:
            st.warning(f"Data pejabat proyek belum dapat dipulihkan: {exc}")
    st.caption("Opsional untuk draf. Kolom kosong menjadi placeholder pada dokumen. Status dan lokasi sumber hanya ditampilkan di sini.")
    values = {}
    for role, label in ROLES.items():
        official = officials.get(role) or empty_officials()[role]
        with st.container(border=True):
            st.markdown(f"**{label}**")
            values[role] = {}
            for field, field_label in (("name", "Nama"), ("position", "Jabatan"),
                                        ("organization_unit", "Unit/fungsi")):
                key = f"tender_field_official_{role}_{field}"
                st.session_state.setdefault(key, official.get(field) or "")
                value = st.text_input(f"{field_label} {label.lower()}", key=key,
                                      placeholder="Belum diisi")
                values[role][field] = value
                origin = (official.get("field_sources") or {}).get(field)
                if value.strip() != str(official.get(field) or "").strip():
                    origin = "user"
                status = "Belum diisi" if not value.strip() else "Diisi pengguna" if origin == "user" else "Dari RKS"
                st.caption(f"{field_label}: {status}")
                candidates = [c for c in official.get("candidates", []) if c.get("field") == field]
                if origin == "ambiguous":
                    st.warning(f"{field_label} memiliki beberapa kandidat; periksa sumber lalu isi kolomnya.")
                for candidate in candidates:
                    source = candidate["source"]
                    st.caption(f"Sumber {field_label.lower()}: {candidate['value']} — {source['filename']}, {source['location']}")
            if official.get("evidence"):
                with st.expander(f"Kutipan sumber {label.lower()}", expanded=False):
                    for evidence in official["evidence"]:
                        st.caption(f"{evidence['filename']} — {evidence['location']}")
                        st.text(evidence["quote"])
    updated = edit_officials(officials, values)
    st.session_state["tf_officials"] = updated
    if store and project_key:
        try:
            store.save_project_officials(project_key, updated)
        except Exception as exc:
            st.warning(f"Data pejabat belum tersimpan ke database: {exc}")
    return updated
