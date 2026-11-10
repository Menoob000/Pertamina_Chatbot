# Sumber knowledge base PDF dan DOCX

Letakkan sumber yang telah diperiksa pada `data/`, kemudian jalankan dari root:

```powershell
uv run python -m rag.doc_loader
```

Untuk direktori atau collection terpisah:

```powershell
uv run python -m rag.doc_loader ./data --collection knowledge_base
```

Loader melaporkan `indexed`, `skipped`, dan `failed` per berkas. Dokumen rusak
atau tanpa teks tidak membatalkan dokumen lain. Berkas sementara Word `~$...`
diabaikan. Tidak ada pemindahan otomatis dokumen dari Gudang RKS ke KB.

## Pembaca bersama

`rag/source_reader.py` menyediakan blok dan potongan sumber untuk pengindeksan,
katalog, serta pencarian generator. PDF memakai lokasi halaman. DOCX memakai
lokasi paragraf atau tabel/baris; `page` bernilai null, bukan nomor perkiraan.

`rag/docx_source.py` membaca urutan paragraf/tabel, heading beserta bagian induk,
penomoran Word yang umum (decimal, alfabet, Roman, bullet), dan sel gabungan.
Penomoran yang diwariskan dari style serta start override dibaca dari OOXML.
Header/footer disimpan terpisah dari isi utama. Potongan tabel mengulang header
pada setiap baris dan setiap pecahan baris panjang. Ukuran chunk adalah target
karakter; tabel dengan header panjang dapat melampauinya agar header tetap utuh.

Format penomoran Word lanjutan, text box, tracked changes, dan tabel bersarang
perlu pemeriksaan tambahan. Teks dalam gambar tidak di-OCR. Elemen tersebut
tetap berada pada berkas DOCX hasil, tetapi tidak dijamin seluruhnya terindeks.

## Penyimpanan dan versi

Struktur tabel `documents` lama dipertahankan. Loader menambah kolom secara
aditif: `source_path`, `source_sha256`, `file_format`, `structure`,
`collection_name`, `is_active`, dan `indexed_at`.

Identitas versi dibuat dari collection, path sumber, dan SHA256. Pengindeksan
ulang melewati sumber dengan hash aktif sama. Setelah versi baru berhasil
diindeks, teks versi lama ditandai tidak aktif dan embeddings lamanya dihapus
dalam transaksi SQL yang sama. Riwayat teks/struktur lama tetap tersimpan.
Kegagalan pengindeksan membersihkan vector baru sejauh layanan tersedia;
versi lama tidak ditandai nonaktif sebelum penyimpanan versi baru berhasil.

Metadata chunk mencakup document ID, source ID/hash, nama dan format berkas,
jenis dokumen, bagian, lokasi, halaman jika PDF, serta tahun/versi jika terbaca
dari nama berkas. Konfigurasi chunk, overlap, threshold, bobot hybrid, dan jumlah
hasil tetap menggunakan `config.py`/environment yang sudah ada.

## Pencarian dan generator

API `/api/rks/search` menerima filter tambahan `file_format: "pdf" | "docx"`.
Hasil pencarian menyertakan lokasi sumber. Hasil semantic DOCX hanya diterima
jika hash indeks cocok dengan sumber aktif; indeks lama perlu dimuat ulang.
Pencarian kata kunci dapat berjalan saat PGVector tidak tersedia.

Untuk sumber DOCX, generator menyimpan ulang struktur Word sumber secara
langsung agar numbering, tabel/merge, logo, cover, section dan content control
tetap terjaga. Generator tidak menyeragamkan desain sumber DOCX yang berbeda.
Jika heading tersedia tetapi daftar isi belum ada, field TOC ditambahkan sebelum
heading pertama. Renderer Office memperbarui daftar isi dan membuat PDF dari
DOCX final yang sama. Sumber aslinya tidak ditimpa.

Fitur ini tidak menambahkan parafrase atau fakta teknis. Cover dan field CSMS
pada sumber DOCX dipertahankan; rekomendasi CSMS yang tampil di web tidak
mengganti checkbox sumber DOCX secara otomatis.

## Pengujian dan contoh

```powershell
uv run python -m unittest discover -s tests -v
uv run python scripts/verify_docx_kb.py --database
```

Skrip verifikasi membuat contoh sumber yang jelas bertanda data uji, menggunakan
collection PostgreSQL tersendiri, memeriksa pengindeksan ulang dan hybrid search,
lalu membuat DOCX/PDF di `output/docx_kb_review/`. Contoh ini tidak dimasukkan ke
collection KB produksi. Word pada Windows perlu berjalan dalam sesi pengguna
yang dapat mengakses COM; sandbox dapat menolak renderer dengan pesan logon.

Hasil uji dan lokasi sumber tersimpan di `verification.json`. `qa_pages/` berisi
halaman PNG untuk pemeriksaan visual. Membuka DOCX atau menjalankan ulang skrip
dapat mengubah metadata/hash berkas; gunakan artifact final dari proses terbaru.
