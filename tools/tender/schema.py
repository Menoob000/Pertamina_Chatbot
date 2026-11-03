"""
Schema definition and Pydantic models for Dokumen Tender Pertamina Patra Niaga.
This schema models the dynamic elements that the LLM and user form generate,
which are then passed into the pure python-docx renderer.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# ──────────────────────────────────────────────────────────────
# Pydantic Models for Dokumen Tender
# ──────────────────────────────────────────────────────────────

class PejabatProcurement(BaseModel):
    jabatan_1: str = "Wkl. Fungsi Procurement (Pengadaan)"
    jabatan_2: str = "Area Manager Procurement Kalimantan"
    nama: str = "Rigga Widar Atmagi"

class UnitRegional(BaseModel):
    nama_entitas: str = "PT PERTAMINA PATRA NIAGA REGIONAL KALIMANTAN"
    fungsi: str = "PELAKSANA PEMILIHAN PENYEDIA FUNGSI PROCUREMENT KALIMANTAN"
    alamat: str = "Jln. Yos Sudarso No. 148 Balikpapan 76123"
    telepon: str = "(0542) 752 4444"
    website: str = "www.pertaminapatraniaga.com"

class CoverPageData(BaseModel):
    nama_pengadaan: str
    nomor_tender: str = "No.Project/DT/PND970000/2026-S7"
    tanggal: str = "04 Desember 2025"
    pejabat_procurement: PejabatProcurement = Field(default_factory=PejabatProcurement)
    unit_regional: UnitRegional = Field(default_factory=UnitRegional)

class KBUPEntry(BaseModel):
    kode: str
    kode_sub_bidang: str
    deskripsi: str

class JadwalPreBid(BaseModel):
    mekanisme: str = "Online"
    hari_tanggal: str = "Senin, 08 Desember 2025"
    waktu: str = "10.00 WITA"
    tempat: str = "Microsoft Teams Meeting dengan link yang disampaikan melalui email Undangan Prebid Meeting"
    catatan: List[str] = [
        "Undangan disampaikan pada SAPP-SmartGEP",
        "Jumlah maksimal perwakilan dari Peserta yang dapat mengikuti Pre-Bid Meeting adalah 5 (lima) orang dan yang dapat mengikuti Penjelasan Lokasi Pekerjaan adalah 3 (tiga) orang.",
        "Penjelasan Lokasi Pekerjaan merupakan satu kesatuan dengan pelaksanaan Pre-Bid Meeting."
    ]

class JadwalPemasukan(BaseModel):
    mulai_hari_tanggal: str = "Senin, 08 Desember 2025"
    mulai_waktu: str = "09.00 WITA"
    selesai_hari_tanggal: str = "Senin, 15 Desember 2025"
    selesai_waktu: str = "16.00 WITA"
    tempat_portal: str = "https://smart.gep.com"
    catatan: List[str] = [
        "Tata waktu untuk setiap Pemilihan Penyedia yang belum tercantum pada tabel di atas dapat dilihat pada SAPP-Smart GEP.",
        "Tata waktu dan tahapan Pemilihan Penyedia dapat disesuaikan dengan kebutuhan Pertamina dan dituangkan dalam Berita Acara Pre-Bid Meeting dan/atau kesepakatan dalam discussion forum SAPP-SmartGEP dan/atau perubahan Milestone SAPP-Smart GEP."
    ]

class KomponenBarangTKDN(BaseModel):
    jenis_barang: str
    tipe_barang: str
    spesifikasi_barang: str
    persen_tkdn: str

class HPSOEInfo(BaseModel):
    prime_cost: float = 0.0
    prime_cost_str: str = "Rp0,00"
    total_dengan_kr: float = 0.0
    total_dengan_kr_str: str = "Rp0,00"

class LampiranChecklist(BaseModel):
    no: str
    jenis_lampiran: str
    keterangan: str

class KetentuanKhususIKPP(BaseModel):
    penyelenggara: str = "Fungsi Procurement (Pengadaan)"
    kategori_pengadaan: str = "Pengadaan dalam Kondisi Normal"
    pemilihan_penyedia: str = "Pertama"
    syarat_status_peserta: str = "Tunggal"
    syarat_golongan_usaha: str = "Menengah"
    syarat_kualifikasi_csms: Dict[str, str] = {
        "tingkat_risiko": "Tinggi",
        "kualifikasi_minimal": "Tinggi"
    }
    syarat_kbup_kbli: List[KBUPEntry] = []
    metode_pemenuhan: str = "Tender Terbatas"
    pejabat_berwenang: str = "Sr. Manager Opt. & Maint. Regional Kalimantan"
    pengawas_pekerjaan: str = "Region Manager RPD Regional Kalimantan"
    jadwal_prebid: JadwalPreBid = Field(default_factory=JadwalPreBid)
    jadwal_pemasukan: JadwalPemasukan = Field(default_factory=JadwalPemasukan)
    masa_berlaku_penawaran: str = "Penawaran berlaku selama 90 (sembilan puluh) Hari Kalender sejak Pembukaan Dokumen Penawaran"
    mekanisme_permintaan_penjelasan: str = "1. Peserta hanya dapat menyampaikan permintaan penjelasan/klarifikasi hanya pada saat pelaksanaan Penjelasan Pekerjaan\n2. Pertamina berhak untuk tidak menanggapi dan/atau memberikan penjelasan/klarifikasi apabila permintaan disampaikan di luar tata waktu sebagaimana diatur pada butir di atas."
    ketentuan_kehadiran_penjelasan: str = "Wajib Hadir\n1. Ketidakhadiran Peserta tidak menggugurkan ke tahapan selanjutnya.\n2. Seluruh Peserta baik yang hadir maupun tidak hadir akan mendapatkan salinan risalah Penjelasan Pekerjaan serta Amendemen Dokumen Tender (apabila ada).\n3. Segala kesalahan menyampaikan Dokumen Penawaran sebagai akibat ketidakhadiran Peserta saat Penjelasan Pekerjaan menjadi risiko dan tanggung jawab dari Peserta yang bersangkutan."
    metode_penyampaian_penawaran: str = "1 (satu) tahap 1 (satu) Sampul"
    syarat_dibukanya_penawaran: str = "Terdapat sekurang-kurangnya 2 (dua) Peserta yang menyampaikan Dokumen Penawaran (tidak termasuk Peserta yang mengundurkan diri)."
    ketentuan_kehadiran_pembukaan: str = "Pembukaan dokumen penawaran tidak perlu dihadiri Peserta\n1. Pembukaan Penawaran akan dilakukan oleh Pertamina tanpa perlu dihadiri oleh Peserta.\n2. Pertamina dapat mengundang Peserta dalam rangka klarifikasi terhadap Dokumen Penawaran yang disampaikan."
    ketentuan_klarifikasi: Dict[str, str] = {
        "media": "Discussion Forum SAPP-SmartGEP",
        "maks_penambahan": "1 (satu) kali",
        "waktu_penyampaian": "1 (satu) Hari Kerja"
    }
    parameter_penetapan_pemenang: str = "HEA Terbaik"
    metode_peringkat_peserta: str = "Peringkat Peserta ditentukan dengan memperhatikan metode HEA Terbaik"
    evaluasi_administrasi: str = "1. Ketentuan Umum Evaluasi Administrasi dijelaskan dalam BAB II.\n2. Evaluasi administrasi akan dilakukan terhadap seluruh persyaratan Dokumen Administrasi yang disampaikan oleh Peserta.\n3. Syarat dokumen administrasi dijelaskan pada BAB II."
    evaluasi_teknis: Dict[str, Any] = {
        "metode": "Scoring",
        "passing_grade": "80 dari skala 100 (seratus)",
        "keterangan": "Syarat, kriteria dan parameter evaluasi teknis dijelaskan pada BAB II Lampiran 2A."
    }
    sanggahan_fase_1: str = "Tidak Dibuka Sanggahan Pengumuman Hasil Evaluasi Fase I"
    evaluasi_hsse_plan: Dict[str, Any] = {
        "dipersyaratkan": True,
        "tingkat_risiko": "High Risk",
        "metode": "Scoring",
        "passing_grade": "Minimal 80% dalam skala 100%"
    }
    evaluasi_tkdn: Dict[str, Any] = {
        "minimal_persen": 20.12,
        "komponen_barang": [],
        "preferensi_harga": "Diberikan preferensi harga sesuai ketentuan yang berlaku."
    }
    jenis_kontrak: str = "Gabungan Harga Satuan & Lumpsum"
    jumlah_pemenang: str = "Single Winner"
    hps_oe: HPSOEInfo = Field(default_factory=HPSOEInfo)
    tata_cara_evaluasi_komersial: str = "Metode evaluasi penawaran komersial Item harga satuan & item harga lumpsum dievaluasi secara Total"
    mekanisme_koreksi_aritmatika: str = "Mekanisme 1"
    ketentuan_negosiasi: Dict[str, Any] = {
        "tata_cara": "Tata Cara Negosiasi e-Reverse Auction (e-RA)",
        "mekanisme": "Mekanisme A opsi 1",
        "media": "SAPP - SmartGEP"
    }
    sanggahan_hasil_pemilihan: str = "Dibuka sanggahan Pengumuman Hasil Pemilihan Penyedia\n1. Masa Sanggah dibuka selambat-lambatnya selama 1 (satu) Hari Kerja sejak pengumuman pemenang.\n2. Sanggahan atas hasil pengumuman calon pemenang harus disertai dengan jaminan sanggahan."
    ketentuan_tambahan_gagal: str = "Proses Pemilihan Penyedia dapat dilanjutkan ke tahap berikutnya, apabila:\n1. Jumlah Peserta mendaftar/menyampaikan konfirmasi partisipasi ≥ 2\n2. Jumlah Peserta yang menyampaikan DP2K ≥ 2\n3. Jumlah Peserta yang lulus Penilaian Kualifikasi ≥ 2\n4. Jumlah Peserta yang menyampaikan Dokumen Penawaran ≥ 2\n5. Jumlah Peserta yang lulus evaluasi penawaran = 1 atau ≥ 2"
    eksepsi_rancangan_kontrak: str = "Tidak diperbolehkan menyampaikan eksepsi atas Rancangan Kontrak.\nPeserta wajib menyetujui Rancangan Kontrak yang disampaikan Pertamina."
    ketentuan_jaminan: List[str] = [
        "1. Dipersyaratkan Jaminan Sanggahan atas Hasil Pengumuman Calon Pemenang",
        "2. Dipersyaratkan Jaminan Pelaksanaan",
        "3. Tidak Dipersyaratkan Jaminan Uang Muka",
        "4. Dipersyaratkan Jaminan Pemeliharaan",
        "5. Dipersyaratkan Jaminan Komitmen TKDN"
    ]
    ketentuan_denda: str = "Diatur sebagaimana Rancangan Kontrak."
    lampiran_ikpp: List[LampiranChecklist] = []
    koordinasi_pemilihan: str = "Pertanyaan terkait pelaksanaan Pemilihan disampaikan melalui Discussion Forum pada SAPP-SmartGEP. Apabila terdapat kendala dapat menghubungi Chatbot Spartan Procurement https://ptm.id/spartan"
    lain_lain: str = "1. Seluruh Dokumen Penawaran dan Kontrak yang mensyaratkan tanda tangan dan meterai harus dibubuhkan dengan e-meterai dan Tanda Tangan Elektronik (TTE) PSrE sesuai ketentuan.\n2. Tanda tangan digital PSrE dapat diakses melalui https://tte.komdigi.go.id/listpsrenew"

class Lampiran2AItem(BaseModel):
    no: int
    kriteria: str
    dokumen_diperlukan: str
    parameter_evaluasi: str
    bobot: Optional[int] = None

class RancanganKontrakData(BaseModel):
    judul_pekerjaan: str
    nomor_kontrak: str = "KTR-[KODE]-[TAHUN]"
    durasi_pekerjaan_hari: int = 180
    masa_pemeliharaan_hari: int = 90
    sistem_pembayaran: str = "Milestone / Monthly Progress"
    denda_per_mil: float = 1.0  # 1 permil per hari keterlambatan
    lingkup_pekerjaan: List[str] = []

class DokumenTenderData(BaseModel):
    cover_page: CoverPageData
    ketentuan_khusus_ikpp: KetentuanKhususIKPP = Field(default_factory=KetentuanKhususIKPP)
    lampiran_2a_evaluasi_teknis: List[Lampiran2AItem] = []
    lampiran_5b_boq_items: List[Dict[str, Any]] = []
    rancangan_kontrak: RancanganKontrakData


# ──────────────────────────────────────────────────────────────
# Strict JSON Schema string for the LLM Prompt
# ──────────────────────────────────────────────────────────────

DOKUMEN_TENDER_JSON_SCHEMA = """
{
  "cover_page": {
    "nama_pengadaan": "<string: Judul Pengadaan Lengkap>",
    "nomor_tender": "<string: e.g. No.Project/DT/PND970000/2026-S7>",
    "tanggal": "<string: e.g. 04 Desember 2025>",
    "pejabat_procurement": {
      "jabatan_1": "Wkl. Fungsi Procurement (Pengadaan)",
      "jabatan_2": "<string: e.g. Area Manager Procurement Kalimantan>",
      "nama": "<string: Nama Pejabat Procurement>"
    },
    "unit_regional": {
      "nama_entitas": "<string: e.g. PT PERTAMINA PATRA NIAGA REGIONAL KALIMANTAN>",
      "fungsi": "<string: e.g. PELAKSANA PEMILIHAN PENYEDIA FUNGSI PROCUREMENT KALIMANTAN>",
      "alamat": "<string: e.g. Jln. Yos Sudarso No. 148 Balikpapan 76123>",
      "telepon": "<string: e.g. (0542) 752 4444>",
      "website": "www.pertaminapatraniaga.com"
    }
  },
  "ketentuan_khusus_ikpp": {
    "penyelenggara": "Fungsi Procurement (Pengadaan)",
    "kategori_pengadaan": "Pengadaan dalam Kondisi Normal",
    "pemilihan_penyedia": "Pertama",
    "syarat_status_peserta": "Tunggal",
    "syarat_golongan_usaha": "<Menengah|Besar|Kecil>",
    "syarat_kualifikasi_csms": {
      "tingkat_risiko": "<Tinggi|Sedang|Rendah>",
      "kualifikasi_minimal": "<Tinggi|Sedang|Rendah>"
    },
    "syarat_kbup_kbli": [
      {
        "kode": "<string: e.g. Q - Jasa Pelaksana Konstruksi>",
        "kode_sub_bidang": "<string: e.g. Q.13.09>",
        "deskripsi": "<string: e.g. Konstruksi Perpipaan Minyak, Gas, dan Energi termasuk perawatannya>"
      }
    ],
    "metode_pemenuhan": "<Tender Terbatas|Tender Terbuka|Pemilihan Langsung>",
    "pejabat_berwenang": "<string: e.g. Sr. Manager Opt. & Maint. Regional Kalimantan>",
    "pengawas_pekerjaan": "<string: e.g. Region Manager RPD Regional Kalimantan>",
    "jadwal_prebid": {
      "mekanisme": "Online",
      "hari_tanggal": "<string: Hari, DD Bulan YYYY>",
      "waktu": "<string: e.g. 10.00 WITA>",
      "tempat": "Microsoft Teams Meeting dengan link yang disampaikan melalui email Undangan Prebid Meeting",
      "catatan": [
        "Undangan disampaikan pada SAPP-SmartGEP",
        "Jumlah maksimal perwakilan peserta 5 orang."
      ]
    },
    "jadwal_pemasukan": {
      "mulai_hari_tanggal": "<string>",
      "mulai_waktu": "<string>",
      "selesai_hari_tanggal": "<string>",
      "selesai_waktu": "<string>",
      "tempat_portal": "https://smart.gep.com",
      "catatan": ["Tata waktu detail dapat dilihat pada SAPP-SmartGEP"]
    },
    "masa_berlaku_penawaran": "Penawaran berlaku selama 90 (sembilan puluh) Hari Kalender sejak Pembukaan Dokumen Penawaran",
    "metode_penyampaian_penawaran": "1 (satu) tahap 1 (satu) Sampul",
    "parameter_penetapan_pemenang": "HEA Terbaik",
    "metode_peringkat_peserta": "Peringkat Peserta ditentukan dengan memperhatikan metode HEA Terbaik",
    "evaluasi_teknis": {
      "metode": "Scoring",
      "passing_grade": "80 dari skala 100 (seratus)",
      "keterangan": "Syarat, kriteria dan parameter evaluasi teknis dijelaskan pada BAB II Lampiran 2A."
    },
    "evaluasi_hsse_plan": {
      "dipersyaratkan": true,
      "tingkat_risiko": "High Risk",
      "metode": "Scoring",
      "passing_grade": "Minimal 80% dalam skala 100%"
    },
    "evaluasi_tkdn": {
      "minimal_persen": 20.12,
      "komponen_barang": [
        {
          "jenis_barang": "<string>",
          "tipe_barang": "<string>",
          "spesifikasi_barang": "<string>",
          "persen_tkdn": "<string>"
        }
      ],
      "preferensi_harga": "Diberikan preferensi harga sesuai ketentuan yang berlaku."
    },
    "jenis_kontrak": "Gabungan Harga Satuan & Lumpsum",
    "jumlah_pemenang": "Single Winner",
    "hps_oe": {
      "prime_cost": 13283434534,
      "prime_cost_str": "Rp13.283.434.534,00",
      "total_dengan_kr": 14346100000,
      "total_dengan_kr_str": "Rp14.346.100.000,00"
    },
    "tata_cara_evaluasi_komersial": "Metode evaluasi penawaran komersial Item harga satuan & item harga lumpsum dievaluasi secara Total",
    "mekanisme_koreksi_aritmatika": "Mekanisme 1",
    "ketentuan_negosiasi": {
      "tata_cara": "Tata Cara Negosiasi e-Reverse Auction (e-RA)",
      "mekanisme": "Mekanisme A opsi 1",
      "media": "SAPP - SmartGEP"
    }
  },
  "lampiran_2a_evaluasi_teknis": [
    {
      "no": 1,
      "kriteria": "<string: e.g. Metode Kerja & Tahapan Pelaksanaan>",
      "dokumen_diperlukan": "<string: e.g. Dokumen Metode Kerja dan Schedule>",
      "parameter_evaluasi": "<string: e.g. Kesesuaian urutan kerja dengan scope pekerjaan dan timeline>",
      "bobot": 25
    },
    {
      "no": 2,
      "kriteria": "<string: e.g. Tenaga Ahli & Personel Inti>",
      "dokumen_diperlukan": "<string: e.g. CV, Ijazah, dan Sertifikat Keahlian (SKA/SKK)>",
      "parameter_evaluasi": "<string: e.g. Memenuhi kualifikasi minimum Project Manager dan Site Engineer>",
      "bobot": 25
    },
    {
      "no": 3,
      "kriteria": "<string: e.g. Peralatan Utama Kerja>",
      "dokumen_diperlukan": "<string: e.g. Daftar Kepemilikan/Sewa Alat dan Sertifikat Kelaikan (SILO)>",
      "parameter_evaluasi": "<string: e.g. Ketersediaan alat berat dan peralatan pendukung sesuai kebutuhan lapangan>",
      "bobot": 25
    },
    {
      "no": 4,
      "kriteria": "<string: e.g. Jadwal Kerja (Time Schedule & Kurva S)>",
      "dokumen_diperlukan": "<string: e.g. Barchart, CPM, dan Kurva S detail per minggu>",
      "parameter_evaluasi": "<string: e.g. Alokasi waktu realistis dan milestone target tercapai>",
      "bobot": 25
    }
  ],
  "rancangan_kontrak": {
    "judul_pekerjaan": "<string: Judul Pekerjaan untuk Kontrak>",
    "nomor_kontrak": "<string: e.g. KTR-042/PND970000/2026-S7>",
    "durasi_pekerjaan_hari": 180,
    "masa_pemeliharaan_hari": 90,
    "sistem_pembayaran": "Pembayaran berdasarkan pencapaian progres fisik (Milestone / Monthly Progress) sesuai Berita Acara Progres Fisik yang disetujui Pengawas Pekerjaan.",
    "denda_per_mil": 1.0,
    "lingkup_pekerjaan": [
      "<string: Lingkup pekerjaan butir 1>",
      "<string: Lingkup pekerjaan butir 2>",
      "<string: Lingkup pekerjaan butir 3>"
    ]
  }
}
"""

