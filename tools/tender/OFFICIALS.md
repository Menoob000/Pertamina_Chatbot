# Pejabat per RKS dan peran

Alur tender membaca kandidat pejabat dari RKS DOCX/PDF, menampilkan sumber di web,
menyimpan koreksi per proyek, lalu meneruskan nilai akhir ke generator yang sama.

## Peran dan sumber

Peran awal adalah `procurement`, `authorized_officer`, dan `work_supervisor`.
Masing-masing mempunyai `name`, `position`, `organization_unit`, sumber per field,
daftar kandidat, dan kutipan asal. Ekstraktor memakai label eksplisit seperti
`Nama Pejabat Procurement: ...`, `Jabatan Pejabat Berwenang: ...`, atau
`Pengawas Pekerjaan: ...`. Pasangan label/nilai pada tabel Word juga dibaca.
Lokasi PDF adalah halaman; lokasi DOCX adalah paragraf atau tabel/baris, karena
penomoran halaman Word bergantung pada proses layout.

Tidak ada nama yang dibuat oleh model. Kandidat berbeda untuk field yang sama
membuat field tersebut kosong dan meminta pemeriksaan. Pengguna dapat mengetik
kandidat yang dipilih atau nilai koreksi. Sumber asli dipertahankan ketika nilai
diubah atau sengaja dikosongkan.

## Penyimpanan

`ConversationStore.initialize()` membuat tabel tambahan saat Streamlit dimulai:

- `project_officials`: nilai aktif per owner, identitas proyek, dan peran.
- `project_official_history`: snapshot setiap perubahan, termasuk sumber.

Identitas proyek adalah `rks:<artifact_id>` jika API memverifikasi byte berkas
unggahan cocok dengan artifact. RKS unggahan/manual menggunakan `sha256:<hash>`.
Nama berkas yang sama dengan isi berbeda menjadi proyek terpisah. Artifact yang
dibuat ulang juga merupakan identitas baru; tidak otomatis mewarisi pejabat dari
artifact sebelumnya. Nilai peran dan widget ikut tersimpan dalam draf percakapan.

Saat ekstraksi diulang, koreksi pengguna dari proyek yang sama dipulihkan,
termasuk kolom yang sengaja dikosongkan. Pemisahan owner mengikuti identitas
aplikasi yang sudah ada. Tabel ini tidak menambahkan autentikasi pengguna.

## Hasil tender

Nama/jabatan pejabat dan jadwal bersifat opsional. Kolom pejabat kosong menjadi
placeholder netral, misalnya `[Nama Pejabat Procurement]`. Data lama dalam field
API `pejabat_procurement_nama`, `pejabat_procurement_jabatan`, `pejabat_berwenang`,
dan `pengawas_pekerjaan` tetap didukung. Payload `officials` terstruktur, jika
disediakan, menjadi nilai utama, termasuk kolom yang sengaja dikosongkan.

Sampul, baris pejabat di IKPP, tanda tangan rancangan kontrak, dan SP3MK memakai
nilai yang sama. Status `Dari RKS`, `Diisi pengguna`, `Belum diisi`, dan lokasi
sumber hanya ditampilkan di web; tidak ditambahkan ke DOCX/PDF.

Tabel pre-bid mempertahankan kontrol tanggal Word. Jadwal pemasukan penawaran
berbentuk tabel; kolom yang belum diberikan dibiarkan kosong. Nilai waktu/tempat
yang tidak mempunyai input pengguna tidak diambil dari keluaran model.
Validasi nama pekerjaan, nomor/tanggal dokumen, CSMS, HPS, metode, dan jenis
kontrak tetap berlaku.

## Batasan dan pemeriksaan pengguna

Ekstraksi tidak mencakup OCR dokumen hasil pindai atau tebakan nama dari tanda
tangan tanpa label peran yang jelas. Peran di luar tiga peran awal perlu
ditambahkan ke pemetaan peran. Teks yang tidak terdeteksi tetap dapat diisi manual.

Pengujian aplikasi dan render tidak dijalankan pada implementasi ini sesuai
permintaan pengguna. Saat meninjau, periksa ekstraksi berlabel pada DOCX/PDF,
perbedaan kandidat, kolom kosong, koreksi manual, refresh, perpindahan RKS,
dan kesesuaian nilai pada sampul/IKPP/tanda tangan. Draf tender lama perlu
dianalisis ulang untuk mendapatkan informasi pejabat dan lokasi sumber baru.
