# Pembuatan RKS dan preview

Modul ini memilih PDF referensi dari `data/`, memindahkan isi melalui ekstraksi geometri, dan membuat DOCX dengan margin, heading, tabel, serta daftar isi yang konsisten. Model bahasa hanya mengarahkan permintaan ke tool dan memilih sumber. Isi file dibentuk tanpa panggilan generasi teks ke model.

Jalankan antarmuka dari root proyek:

```powershell
uv run streamlit run streamlit_app.py
```

Pilih **Pembuatan RKS dan preview**, cari pekerjaan, pilih RKS acuan, lalu buat dokumen. Halaman ini tetap bisa digunakan ketika chatbot belum memiliki API key. Pada chat, permintaan membuat RKS diarahkan ke tool `create_rks_document`; bila sumber ambigu, agent meminta pilihan.

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

## Kesetiaan isi dan batasan

Inventaris mempertahankan teks, tabel, elemen visual, dan halaman asal. Struktur sel yang tidak pasti disimpan sebagai gambar tabel. Jika pemindahan berpotensi kehilangan kata, ditemukan karakter rusak, atau elemen saling bertumpang tindih, halaman sumber dipertahankan sebagai gambar dan hasil diberi status **perlu pemeriksaan**. Bagian tersebut mempertahankan tampilan sumber dan belum sepenuhnya dapat diedit atau dirapikan. OCR dicoba bila tersedia; hasil OCR tidak digunakan untuk menebak pengganti isi yang belum diverifikasi.

Status **lengkap** berarti pemeriksaan otomatis pemindahan dan render lulus, bukan penilaian substansi atau persetujuan manusia. Deteksi heading dan tabel bersifat heuristik; dokumen dengan tata letak kompleks tetap perlu ditinjau melalui preview. BOQ hanya mengikuti isi sumber; sistem tidak membuat item atau nilai baru. BOQ terpisah tidak digabungkan otomatis tanpa hubungan sumber yang dapat dipastikan.

## API

| Endpoint | Kegunaan |
|---|---|
| `GET /api/rks/sources?query=...` | Cari sumber dan identitasnya |
| `POST /api/rks/generate` | Buat dokumen dengan `{ "query": "...", "source_id": "..." }`; `source_id` boleh kosong jika satu pilihan jelas |
| `GET /api/rks/<id>` | Status, sumber, dan catatan hasil |
| `GET /api/rks/<id>/document.docx` | DOCX final yang sesuai manifest |
| `GET /api/rks/<id>/preview.pdf` | PDF hasil render dari DOCX tersebut |

Pembuatan menggunakan endpoint sinkron; klien perlu menampilkan indikator proses dan memberikan waktu untuk render dokumen panjang. API mengikuti mekanisme akses layanan yang ada; autentikasi lintas pengguna belum ditambahkan oleh modul ini.

Pengujian regresi tanpa layanan model eksternal:

```powershell
uv run python -m unittest discover -s tests -v
```
