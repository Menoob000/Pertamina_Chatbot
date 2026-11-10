"""Project officials and deterministic placeholders used by every tender entry point."""
from copy import deepcopy


ROLES = {
    "procurement": "Pejabat Procurement",
    "authorized_officer": "Pejabat Berwenang",
    "work_supervisor": "Pengawas Pekerjaan",
}
OFFICIAL_FIELDS = ("name", "position", "organization_unit")
LEGACY_FIELDS = {
    "pejabat_procurement_nama": "[Nama Pejabat Procurement]",
    "pejabat_procurement_jabatan": "[Jabatan Pejabat Procurement]",
    "pejabat_berwenang": "[Nama/Jabatan Pejabat Berwenang]",
    "pengawas_pekerjaan": "[Nama/Jabatan Pengawas Pekerjaan]",
}


def empty_officials() -> dict:
    return {role: {"name": "", "position": "", "organization_unit": "",
                   "field_sources": {}, "evidence": [], "candidates": []}
            for role in ROLES}


def official_label(role: str, official: dict) -> str:
    values = [str(official.get(field) or "").strip() for field in ("name", "position")]
    if not any(values):
        return f"[Nama/Jabatan {ROLES[role]}]"
    return f"{values[0] or '[Nama belum diisi]'} / {values[1] or '[Jabatan belum diisi]'}"


def normalize_officer_parameters(parameters: dict) -> dict:
    """Preserve the existing API fields while accepting structured per-role values."""
    result = dict(parameters)
    officials = parameters.get("officials")
    if isinstance(officials, dict):
        procurement = officials.get("procurement") or {}
        result["pejabat_procurement_nama"] = str(procurement.get("name") or "").strip()
        result["pejabat_procurement_jabatan"] = str(procurement.get("position") or "").strip()
        for role, field in (("authorized_officer", "pejabat_berwenang"),
                            ("work_supervisor", "pengawas_pekerjaan")):
            result[field] = official_label(role, officials.get(role) or {})
    for field, placeholder in LEGACY_FIELDS.items():
        result[field] = str(result.get(field) or "").strip() or placeholder
    return result


def apply_officials_to_draft(draft: dict, parameters: dict) -> None:
    """Override model-produced signers with the selected values, including blanks."""
    normalized = normalize_officer_parameters(parameters)
    procurement = draft.setdefault("cover_page", {}).setdefault("pejabat_procurement", {})
    procurement["nama"] = normalized["pejabat_procurement_nama"]
    procurement["jabatan_1"] = "Fungsi Procurement (Pengadaan)"
    if isinstance(parameters.get("officials"), dict):
        procurement["jabatan_1"] = str((parameters["officials"].get("procurement") or {}).get("organization_unit") or "Fungsi Procurement (Pengadaan)")
    procurement["jabatan_2"] = normalized["pejabat_procurement_jabatan"]
    kk = draft.setdefault("ketentuan_khusus_ikpp", {})
    kk["pejabat_berwenang"] = normalized["pejabat_berwenang"]
    kk["pengawas_pekerjaan"] = normalized["pengawas_pekerjaan"]
    # Only final values enter the document; provenance stays on the web/database.
    draft["officials"] = {
        role: {field: str((parameters.get("officials", {}).get(role) or {}).get(field) or "").strip()
               for field in OFFICIAL_FIELDS}
        for role in ROLES
    } if isinstance(parameters.get("officials"), dict) else {}


def edit_officials(extracted: dict, values: dict) -> dict:
    """Keep original evidence when a user changes or explicitly clears a field."""
    result = deepcopy(extracted or empty_officials())
    for role in ROLES:
        official = result.setdefault(role, empty_officials()[role])
        for field in OFFICIAL_FIELDS:
            old = str(official.get(field) or "").strip()
            value = str((values.get(role) or {}).get(field) or "").strip()
            if value != old:
                official.setdefault("field_sources", {})[field] = "user"
            official[field] = value
    return result
