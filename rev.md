# Status revisi — 10 November 2026

| No. | Revisi | Status saat ini | Pekerjaan lanjutan |
|---:|---|---|---|
| 1 | RKS → rancangan kontrak → bank data | Selesai untuk alur tender: Bagian B dibuat sebagai DOCX tersendiri dan disimpan di PostgreSQL (`contract_drafts`). Gudang Rancangan Kontrak menyediakan pencarian, preview, unduh, dan tautan ke RKS asal. Satu kontrak hasil generate lama sudah dipulihkan ke arsip. | Belum ada instruksi atau alur untuk meneruskan kontrak ke knowledge base; hal ini memang di luar cakupan saat ini. |
| 2 | Tombol lanjutan dari RKS ke dokumen lain | Sebagian: RKS dapat diteruskan ke generator tender. | Tentukan jenis dokumen lanjutan lain sebelum menambahkan tombolnya. |
| 3 | Gudang RKS dengan tombol interaksi | Selesai: daftar, pencarian, filter, preview, unduh, sembunyikan/tampilkan peninjauan, dan lanjutkan ke tender. | Tinjau pengalaman penggunaan jika ada masukan baru. |
| 4 | DOCX sebagai sumber database/knowledge base | Implementasi tersedia: DOCX dapat diindeks ke PostgreSQL/PGVector, dicari, dan dipakai sebagai sumber generator RKS. Pengujian dengan DOCX contoh tercatat 30 lulus. | Validasi dengan DOCX proyek nyata; teks dalam gambar masih memerlukan OCR bila ingin diindeks. |
| 5 | Nama pejabat per proyek/peran | Implementasi tersedia: kandidat dari RKS dibaca bersama lokasi sumber, dapat diperiksa/dikoreksi pada web, dan disimpan per proyek/peran di PostgreSQL. | Uji alur lengkap memakai RKS proyek nyata, termasuk nama atau jabatan yang ambigu. |
| 6 | Relasi RKS dengan tender yang dibuat | Selesai untuk tender baru: Gudang RKS mencatat dan menampilkan dokumen tender terkait. | Tender lama yang belum tercatat memerlukan pemulihan terpisah bila diperlukan. |
| 7 | Penyimpanan riwayat chat | Sudah tersedia pada PostgreSQL. | Verifikasi kembali bila skenario multi-pengguna diterapkan. |
| 8 | Tender membaca konteks RKS hasil generator | Sudah tersedia, termasuk penerusan RKS dari Gudang RKS. | Periksa kecocokan hasil ekstraksi pada setiap proyek. |
| 9 | Preview sebelum unduh untuk RKS dan tender | Sudah tersedia dari DOCX hasil generate. | Penampilan halaman bergantung pada renderer Word/LibreOffice yang tersedia. |
| 10 | Data tender dari RKS dan BOQ | Sebagian: ekstraksi dan pengisian otomatis tersedia; pengguna dapat mengoreksi hasilnya. | Validasi nilai dan asal data untuk setiap proyek, terutama BOQ/HPS. |
| 11 | Nilai contoh tender seperti pejabat, jadwal, HPS, dan nomor | Sebagian: pejabat memakai nilai per proyek atau placeholder; jadwal kosong tetap kosong; HPS, nomor tender, tanggal, metode, jenis kontrak, dan risiko CSMS dapat dibiarkan kosong untuk draft dengan placeholder pada DOCX. | Audit sisa nilai contoh/default lain pada seluruh bagian tender dan rancangan kontrak. |

Catatan: status di atas menggambarkan kode dan database lokal pada tanggal pemeriksaan. Data arsip PostgreSQL dan berkas hasil generate tidak ikut tersimpan dalam commit Git.
