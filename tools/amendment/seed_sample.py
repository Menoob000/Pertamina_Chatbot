"""Seed official IKN amendment sample into amendment_drafts table."""
from tools.amendment.archive import AmendmentArchive
from tools.amendment.builder import build_amendment_docx

archive = AmendmentArchive()
archive.initialize()

existing = archive.list()
ikn_exists = any("DPPU Nusantara" in item["project_name"] for item in existing)

if not ikn_exists:
    ikn_params = {
        "project_name": "Pembangunan DPPU Nusantara Ibu Kota Negara (IKN) – Penajam Paser Utara",
        "contract_ref": "SP-068/PND900000/2024-S0",
        "contract_date": "25 April 2024",
        "amendment_level": "Amendemen II",
        "tanggal_amendemen": "02 Desember 2025",
        "prev_amendment_date": "15 Agustus 2025",
        "company_name": "PT Pertamina Patra Niaga",
        "company_office": "Jakarta Selatan dan berkantor pusat di Gedung Wisma Tugu II Lantai 2, Jalan HR. Rasuna Said Kav. C7-9, Kota Administrasi Jakarta Selatan, Provinsi DKI Jakarta",
        "company_rep_name": "Riki Madyanto",
        "company_rep_title": "Sr. Manager Opt. & Maint. Kalimantan",
        "contractor_name": "PT PGAS Solution",
        "contractor_office": "Jakarta Pusat dan berkantor pusat di Jakarta",
        "contractor_rep_name": "Heru Indriatno",
        "contractor_rep_title": "Direktur Teknik dan Pengembangan",
        "nilai_pekerjaan_baru": 28642900000,
        "tanggal_sp3mk": "14 Maret 2024",
        "nomor_sp3mk": "SP3MK-007/PND900000/2024-S0",
        "durasi_bulan_pemeliharaan": 6,
        "tanggal_berlaku_amendemen": "04 September 2025",
        "klausul_lampiran": (
            "Mengubah beberapa ketetuan dalam Lampiran B KONTRAK, Lampiran C KONTRAK, "
            "Lampiran D KONTRAK, Lampiran G KONTRAK, Lampiran D-I AMENDEMEN dan Lampiran G-I AMENDEMEN "
            "dengan perubahan yang masing-masing terdapat dalam Lampiran B-I AMENDEMEN II, "
            "Lampiran C-I AMENDEMEN II, Lampiran D-II AMENDEMEN II, dan Lampiran G-II AMENDEMEN II."
        ),
        "lingkup_pekerjaan": (
            "2. Pekerjaan yang harus dilaksanakan oleh KONTRAKTOR adalah Pembangunan DPPU Nusantara "
            "Ibu Kota Negara (IKN) – Penajam Paser Utara dengan ruang lingkup sebagaimana diuraikan dalam "
            "Lampiran B-I AMENDEMEN II."
        ),
        "tambahan_pekerjaan": (
            "3. Pekerjaan yang harus dilaksanakan oleh KONTRAKTOR Pengadaan 1 (Satu) Unit Pompa PMK Kap. 3000 GPM "
            "di IT Balikpapan dengan ruang lingkup sebagaimana diuraikan dalam Lampiran B KONTRAK dengan penambahan "
            "terdapat dalam Lampiran B-I AMENDEMEN II dan harus diselesaikan sesuai dengan jadwal yang diuraikan dalam "
            "Lampiran D-I AMENDEMEN II (“PEKERJAAN”)."
        ),
        "dasar_dokumen": [
            "Surat KONTRAKTOR kepada PERUSAHAAN No.10150.S/DPPU-IKN/PGAS/XI/2025 tanggal 21 November 2025 perihal Revisi Penawaran Harga dan Waktu pada Pembangunan DPPU Nusantara Ibu Kota Negara (IKN) – Penajam Paser Utara;",
            "Notulen Rapat No.NR-794/PND95C000/2025-S5 tanggal 13 Oktober 2025 perihal War Room dan Pembahasan Pengajuan Amendemen Pekerjaan Pembangunan DPPU Ibu Kota Nusantara (IKN) Penajam Paser Utara;",
            "Notulen Rapat No.NR-950/PND95C000/2025-S5 tanggal 18 November 2025 perihal Pembahasan Pengajuan Amendemen Pekerjaan Pembangunan DPPU Ibu Kota Nusantara (IKN) Penajam Paser Utara;",
            "Berita Acara Klarifikasi dan Negosiasi Amendemen Waktu dan Biaya No.951/PND95C000/2025-S5 tanggal 02 Desember 2025."
        ],
        "portal_autentifikasi": "https://tte.komdigi.go.id/verifyPDF"
    }
    docx_bytes = build_amendment_docx(ikn_params)
    aid = archive.save(
        project_name=ikn_params["project_name"],
        amendment_level=ikn_params["amendment_level"],
        amendment_docx=docx_bytes,
        custom_filename="Contoh_Resmi_Amendemen_II_DPPU_IKN.docx",
        metadata=ikn_params
    )
    print("Contoh dokumen resmi IKN berhasil disimpan ke PostgreSQL! ID:", aid)
else:
    print("Contoh dokumen resmi IKN sudah ada di database.")
