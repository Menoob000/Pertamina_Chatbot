"""LangChain Tool for Generating Contract Amendments from Chatbot."""
from __future__ import annotations

import os
from typing import Optional, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from tools.tender.contract_archive import ContractArchive
from .archive import AmendmentArchive
from .builder import build_amendment_docx
from .extractor import extract_context_from_contract


class GenerateAmendmentInput(BaseModel):
    contract_query: Optional[str] = Field(
        default=None,
        description="Nama proyek, nomor kontrak, atau ID kontrak acuan yang ada di database Gudang Kontrak."
    )
    amendment_level: Optional[str] = Field(
        default="Amendemen II",
        description="Tingkat amandemen yang ingin dibuat, misalnya 'Amendemen I', 'Amendemen II', atau 'Amendemen III'."
    )
    new_price: Optional[float] = Field(
        default=None,
        description="Nilai pekerjaan baru dalam angka Rupiah (jika ada perubahan nilai)."
    )
    change_notes: Optional[str] = Field(
        default=None,
        description="Ringkasan poin atau klausul yang diubah (misalnya perpanjangan waktu, penambahan lingkup kerja)."
    )


class GenerateAmendmentDocumentTool(BaseTool):
    name: str = "generate_amendment_document"
    description: str = (
        "Gunakan tool ini ketika pengguna meminta untuk membuat, men-generate, atau menyusun dokumen amandemen kontrak "
        "(pokok-pokok kontrak amandemen) dari kontrak yang tersimpan di sistem. "
        "Tool ini akan mengambil data kontrak induk, menyusun klausul amandemen resmi dalam format DOCX standar Pertamina, "
        "dan menyimpannya ke database serta direktori output."
    )
    args_schema: Type[BaseModel] = GenerateAmendmentInput

    def _run(
        self,
        contract_query: Optional[str] = None,
        amendment_level: Optional[str] = "Amendemen II",
        new_price: Optional[float] = None,
        change_notes: Optional[str] = None,
    ) -> str:
        contract_archive = ContractArchive()
        try:
            contracts = contract_archive.list()
        except Exception as e:
            return f"Gagal mengakses Gudang Kontrak di database: {e}"

        if not contracts:
            return (
                "Belum ada rancangan kontrak yang tersimpan di sistem (Gudang Kontrak). "
                "Harap buat atau arsipkan rancangan kontrak terlebih dahulu sebelum membuat dokumen amandemen."
            )

        matched_contract = None
        if contract_query and contract_query.strip():
            q = contract_query.strip().casefold()
            for c in contracts:
                if q in c["project_name"].casefold() or q in c["id"].casefold() or q in c.get("contract_filename", "").casefold():
                    matched_contract = c
                    break

        if not matched_contract:
            if len(contracts) == 1:
                matched_contract = contracts[0]
            else:
                contract_list_str = "\n".join([f"- **{c['project_name']}** (ID: `{c['id'][:8]}`)" for c in contracts[:5]])
                return (
                    f"Ditemukan beberapa kontrak di database. Mohon tentukan kontrak mana yang ingin diamandemen:\n\n"
                    f"{contract_list_str}\n\n"
                    "Sebutkan nama pekerjaan atau ID kontrak tersebut untuk melanjutkan pembuatan amandemen."
                )

        try:
            contract_data = contract_archive.get(matched_contract["id"])
            extracted = extract_context_from_contract(contract_data)

            lvl = amendment_level.strip() if amendment_level else "Amendemen II"
            extracted["amendment_level"] = lvl

            if new_price and new_price > 0:
                extracted["nilai_pekerjaan_baru"] = new_price

            if change_notes and change_notes.strip():
                extracted["tambahan_pekerjaan"] = f"3. Catatan Perubahan: {change_notes.strip()}"

            docx_bytes = build_amendment_docx(extracted)

            amend_archive = AmendmentArchive()
            amend_id = amend_archive.save(
                project_name=extracted["project_name"],
                amendment_level=lvl,
                amendment_docx=docx_bytes,
                contract_draft_id=matched_contract["id"],
                metadata=extracted,
            )

            filename = f"{lvl.replace(' ', '_')}_{extracted['project_name'][:25].strip().replace(' ', '_')}_{amend_id[:8]}.docx"
            out_path = os.path.abspath(os.path.join("output", filename))

            return (
                f"✅ **Dokumen Amandemen Berhasil Dibuat!**\n\n"
                f"- **Pekerjaan**: {extracted['project_name']}\n"
                f"- **Tingkat**: {lvl}\n"
                f"- **Referensi Kontrak Induk**: `{extracted['contract_ref']}` ({extracted['contract_date']})\n"
                f"- **Para Pihak**: {extracted['company_name']} & {extracted['contractor_name']}\n"
                f"- **File DOCX Tersimpan**: `{filename}` di folder `./output/`\n"
                f"- **ID Arsip Database**: `{amend_id[:8]}` (tersedia di menu Gudang Dokumen Amandemen)\n\n"
                f"Dokumen telah disusun mengikuti format baku Pokok-Pokok Kontrak Amandemen Pertamina Patra Niaga."
            )
        except Exception as exc:
            return f"Terjadi kesalahan saat men-generate dokumen amandemen: {exc}"
