# Pertamina Integration API

Lapisan HTTP untuk fungsi yang sudah ada di root proyek. Kode `agent.py`, `rag/`, `tools/`, dan aplikasi Streamlit tidak dipindah atau diubah.

## Menjalankan dari root proyek

Siapkan dependensi Python melalui `uv sync`, database pgvector yang dipakai kode root, dan variabel lingkungan untuk layanan model/RAG. Kemudian:

```powershell
uv run uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

Dokumentasi interaktif tersedia di `http://127.0.0.1:8000/docs`. Jalankan dari root checkout `integrasi-be`, sebab kode lama membaca `./data` dan menulis `./output`. `GET /api/health` dapat digunakan tanpa memulai agent atau koneksi database.

Origin React bawaan adalah `http://localhost:5173` dan `http://127.0.0.1:5173`. Jika alamat frontend berbeda, set `FRONTEND_ORIGINS` dengan daftar origin dipisahkan koma.

## Alur API

1. `POST /api/threads` dengan `{"title":"Percakapan baru"}` menghasilkan ID thread.
2. `POST /api/threads/{id}/messages` dengan `{"message":"Cari RKS overhaul tangki"}` menjalankan satu giliran agent. Respons berisi `message`, `tool_events`, dan `document_id` jika dokumen penuh ditemukan.
3. `GET /api/documents/{id}` memberi isi dan susunan bab untuk viewer. `pdf_url` tersedia jika PDF yang cocok ada di `data/`.
4. `POST /api/documents/{id}/conversions` mengonversi PDF sumber dan memberi `download_url` DOCX. Pengguna tidak mengirim path file ke API.

Endpoint sesi lain: `GET /api/threads`, `GET /api/threads/{id}`, `PATCH /api/threads/{id}`, dan `DELETE /api/threads/{id}`. Kesalahan terduga memakai bentuk `{"error":{"code":"...","message":"..."}}`.

## Batasan tahap ini

- Thread, dokumen, dan daftar unduhan disimpan di memori **satu proses**. Riwayat hilang ketika API dimulai ulang. Gunakan satu worker hingga penyimpanan persisten tersedia.
- Endpoint chat bersifat sinkron; streaming token/aktivitas real-time belum ditambahkan.
- Endpoint belum memiliki autentikasi. Jalankan hanya di lingkungan pengembangan tepercaya sampai kontrol akses dirancang.
- PDF hanya dapat dikonversi bila metadata dokumen dari RAG menunjuk ke nama PDF yang ada di `data/`.
- Jika modul root gagal memuat database/model, endpoint chat memberi error `agent_unavailable`; `/api/health` tetap hidup.
- Server mengimpor `agent.py` saat chat pertama. Modul lama tersebut mempunyai efek samping berupa upaya membuat `graph.png`; perilaku itu sengaja tidak diubah pada tahap ini.

## Verifikasi ringan

Tes backend menggunakan mock untuk agent dan konversi sehingga tidak memerlukan database atau kunci API:

```powershell
uv run --no-project --python 3.13 --with fastapi --with httpx --with pytest --with python-docx python -m pytest backend/tests
```

Uji penuh dengan agent asli memerlukan database dan kredensial yang sama dengan aplikasi Streamlit.
