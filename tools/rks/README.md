# Pembuatan RKS dan preview

Modul ini memilih PDF referensi dari `data/`, mengambil lapisan teks dan tabel bergarisnya, lalu membuat DOCX dengan sampul dinamis, heading Word, tabel editable, serta daftar isi otomatis. Model bahasa hanya mengarahkan permintaan ke tool. Isi file dibentuk tanpa panggilan generasi teks ke model.

Jalankan antarmuka dari root proyek:

```powershell
uv run streamlit run streamlit_app.py
```

Pilih **Pembuatan RKS dan preview**, tulis pekerjaan, lalu klik **Buat DOCX dan preview**. Halaman ini tetap bisa digunakan ketika chatbot belum memiliki API key. Pada chat, permintaan membuat RKS diarahkan ke tool `create_rks_document`. Sumber dipilih otomatis berdasarkan peringkat; alternatif dan skor pilihan dicatat. `source_id` hanya diperlukan bila pengguna secara eksplisit menentukan sumber. Jika tak ada sumber yang memenuhi ambang, sistem membuat template umum dengan placeholder tanpa fakta proyek atau sitasi palsu.

## Pencarian sumber

Nama PDF dan tiga halaman awal digunakan untuk shortlist kata kunci, kategori pekerjaan, serta kode aset persis. Ketika shortlist kosong, pencarian isi per halaman dapat menemukan dokumen dengan nama yang kurang informatif. Potongan bukti per bagian dicari dengan kata kunci lokal dan pencarian semantik melalui PGVector yang sudah digunakan proyek. Skor gabungan memakai bobot yang dapat dikonfigurasi; hasil disaring dengan ambang dan diurut ulang. Jika PGVector/model lokal tidak tersedia, kata kunci tetap bekerja dan `semantic_status` menyatakan keterbatasan. Setiap bukti menyimpan nama dokumen, halaman bila ada, skor, dan identitas sumber dalam `manifest.json`. Generator RKS saat ini tetap memindahkan isi satu PDF sumber secara setia; bukti per bagian adalah jejak audit, bukan izin untuk menambah fakta dari PDF lain.

| Variabel `.env` | Bawaan | Fungsi |
|---|---:|---|
| `RKS_SEARCH_TOP_K` | 5 | Maksimum hasil per pencarian |
| `RKS_SEARCH_SCORE_THRESHOLD` | 0.55 | Ambang skor 0–1 |
| `RKS_SEARCH_KEYWORD_WEIGHT` | 0.65 | Bobot kata kunci dalam hasil gabungan |
| `RKS_SEARCH_SEMANTIC_WEIGHT` | 0.35 | Bobot semantik dalam hasil gabungan |
| `RKS_SEARCH_SEMANTIC_ENABLED` | true | Coba PGVector lokal bila tersedia |
| `RKS_SEARCH_CHUNK_SIZE` | 1000 | Panjang potongan teks saat indeks dan pencarian lokal |
| `RKS_SEARCH_CHUNK_OVERLAP` | 150 | Tumpang tindih potongan |
| `RKS_SEARCH_MAX_SECTIONS` | 100 | Batas bagian yang dicari buktinya; jejak halaman asal tetap disimpan untuk semua heading |

Skor adalah sinyal peringkat internal, bukan probabilitas bahwa isi dokumen benar. Tahun/versi diambil dari nama file jika ada; metadata yang tidak tersedia tidak ditebak. Indeks PGVector lama belum memiliki nomor halaman; jalankan ulang proses indeks untuk dokumen baru atau migrasikan indeks lama agar sitasi semantik memiliki halaman. Proses indeks baru memecah teks per halaman. Pencarian tidak menambahkan isi yang gagal diekstraksi, dan halaman ambigu tetap diberi tanda pemeriksaan.

CLI untuk memeriksa alur yang sama:

```powershell
uv run python -m tools.rks "buatkan rks overhaul tangki 041T314"
```

Hasil tiap permintaan berada di `output/rks/<artifact_id>/`: `RKS.docx`, `RKS.pdf` jika render berhasil, inventaris `extraction.json`, dan `manifest.json`. UUID baru digunakan untuk setiap pembuatan. Manifest menyimpan hash sumber serta hash DOCX dan PDF setelah finalisasi. Endpoint unduhan menolak file yang berubah setelah hash dibuat.

## Render dan daftar isi

- Pada Windows, mode `auto` mencoba Microsoft Word melalui `pywin32` dalam proses terpisah dengan jendela tersembunyi. Word memperbarui field dan daftar isi, menyimpan DOCX, memeriksa nomor halaman entri daftar isi terhadap bookmark tujuan, lalu membuat PDF dari file yang sama. Word perlu terpasang dan sesi pengguna Windows harus dapat mengakses COM.
- Untuk LibreOffice, sediakan `soffice` pada PATH atau isi `SOFFICE_PATH`. Adapter menyimpan ulang DOCX ke direktori tersendiri sebelum mengubahnya menjadi PDF. Nomor halaman daftar isi pada adapter ini diberi status perlu pemeriksaan karena belum diverifikasi melalui bookmark seperti adapter Word.
- `RKS_RENDERER=word` atau `RKS_RENDERER=libreoffice` dapat membatasi pilihan. Jika tidak ada renderer yang dapat digunakan, DOCX tetap tersedia sebagai draf perlu pemeriksaan dan antarmuka menyatakan preview belum tersedia.
- Container backend yang ada memerlukan volume `data/` untuk sumber PDF. Untuk preview dalam Linux/container, LibreOffice dan font template harus disediakan pada image saat tahap penyiapan deployment.

Preview antarmuka menampilkan halaman dari PDF hasil render, dengan pilihan halaman dan perbesaran. Penggantian sumber menghapus hasil yang sedang ditampilkan. DOCX yang dibuka pada aplikasi/perangkat lain masih dapat bergeser karena perbedaan font dan mesin tata letak.

Pada chat, panel dokumen membuka tab **Pratinjau halaman** sebagai tab utama. RKS yang diambil lewat pencarian lama otomatis disiapkan menjadi DOCX dan preview dari sumber yang sama. Hasil yang hash sumber dan versi pipelinenya cocok dapat dipakai kembali; pergantian halaman tidak memicu pembuatan ulang. Tab **Teks sumber** menyimpan tampilan teks ekstraksi untuk pemeriksaan. Catatan pemeriksaan diringkas dalam panel tertutup agar halaman preview langsung terlihat.

## Kesetiaan isi dan batasan

Keluaran RKS memakai struktur Word editable: sampul disusun dari teks yang terbaca pada PDF terpilih, judul bab/subbab menjadi heading Word agar masuk daftar isi, dan tabel bergaris dipetakan menjadi tabel Word. Sampul formal dengan field risiko memakai bingkai halaman, kotak judul, kotak nama pekerjaan, logo, dan nama perusahaan; sampul lain memakai judul serta ringkasan yang diambil dari PDF sumber. Hubungan sel gabungan, logo, centang, diagram, dan gambar lain tetap perlu diperiksa pada PDF asli. Simbol kontrol yang tidak dapat dibaca ditulis `[simbol tidak terbaca]`; halaman tanpa lapisan teks memerlukan transkripsi manual. Hasil seperti ini berstatus **perlu pemeriksaan** dan harus dibandingkan dengan PDF sumber sebelum digunakan.

Status **lengkap** berarti pemeriksaan otomatis teks dan render lulus, bukan penilaian substansi atau persetujuan manusia. Deteksi heading dan hubungan kolom tabel bersifat heuristik; dokumen dengan tata letak kompleks tetap perlu ditinjau melalui preview. BOQ hanya mengikuti teks yang tersedia di sumber; sistem tidak membuat item atau nilai baru. BOQ terpisah tidak digabungkan otomatis tanpa hubungan sumber yang dapat dipastikan.

## API

| Endpoint | Kegunaan |
|---|---|
| `GET /api/rks/sources?query=...` | Cari sumber dan identitasnya |
| `POST /api/rks/search` | Cari bukti per halaman; mendukung `query`, `source_id`, `document_type`, `year`, `version`, `section`, `top_k`, dan `score_threshold` |
| `POST /api/rks/generate` | Buat dokumen dengan `{ "query": "...", "source_id": "..." }`; `source_id` boleh kosong jika satu pilihan jelas |
| `GET /api/rks/<id>` | Status, sumber, dan catatan hasil |
| `GET /api/rks/<id>/document.docx` | DOCX final yang sesuai manifest |
| `GET /api/rks/<id>/preview.pdf` | PDF hasil render dari DOCX tersebut |

Pembuatan menggunakan endpoint sinkron; klien perlu menampilkan indikator proses dan memberikan waktu untuk render dokumen panjang. API mengikuti mekanisme akses layanan yang ada; autentikasi lintas pengguna belum ditambahkan oleh modul ini.

Pengujian regresi tanpa layanan model eksternal:

```powershell
uv run python -m unittest discover -s tests -v
```
