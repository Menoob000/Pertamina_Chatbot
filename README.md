# Pertamina Procurement AI & Knowledge Assistant

Alur **Pembuatan RKS dan preview** tersedia melalui menu Streamlit dan endpoint `/api/rks`. Lihat [panduan modul RKS](tools/rks/README.md) untuk penggunaan, renderer, dan batasan hasil ekstraksi.

Platform AI terintegrasi untuk membantu dan mengotomatisasi proses pengadaan di lingkungan **PT Pertamina Patra Niaga**:
1. **💬 Chatbot AI & RKS Viewer:** Asisten interaktif berbasis RAG (*Retrieval-Augmented Generation*) untuk pencarian, telaah, dan konversi dokumen RKS (*Rencana Kerja dan Syarat-Syarat*) dari database PostgreSQL menjadi format Microsoft Word (.docx) resmi Pertamina.
2. **📑 Dokumen Tender Generator:** Layanan mandiri berbasis REST API FastAPI untuk menyusun Dokumen Tender lengkap (IKPP 40 butir, 30 artikel ketentuan umum, matriks evaluasi teknis Lampiran 2A, evaluasi CSMS, dan Rancangan Kontrak 18 pasal + Template SP3MK) sesuai Pedoman Pengadaan No. A03-001/PNG200000/2024-S9 Rev. 1.

---

## 🚀 Prasyarat Sistem

Pastikan software berikut telah terinstal pada sistem Anda:
* **Python 3.12+** (selaras dengan `pyproject.toml` dan Dockerfile)
* **[`uv`](https://github.com/astral-sh/uv)** (Python package & environment manager)
* **Docker** (untuk menjalankan container PostgreSQL pgvector)

---

## ⚙️ Konfigurasi Environment (`.env`)

Buat atau periksa file `.env` pada root project dengan konfigurasi berikut:

```env
OPENROUTER_API_KEY="sk-or-v1-..."
LANGSMITH_API_KEY="lsv2_pt_..."
TAVILY_API_KEY="tvly-..."
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_PROJECT="Pertamina_Chatbot"
```

---

## 🛠️ Cara Menjalankan Aplikasi

Riwayat percakapan Streamlit disimpan di PostgreSQL yang sama dengan knowledge base
(`PGVECTOR_HOST`, `PGVECTOR_PORT`, `PGVECTOR_DB`, `PGVECTOR_USER`, dan
`PGVECTOR_PASSWORD`). Tabel `chat_users`, `chat_threads`, `chat_messages`, dan
`tender_drafts` dibuat otomatis saat aplikasi dibuka. Hasil ekstraksi tender dan
isian formulir disimpan per percakapan agar dapat dibuka kembali setelah refresh.
Mode bawaan memakai satu identitas lokal:
riwayat lama dari token URL mana pun terlihat pada port 8501 maupun 8502 tanpa
memindahkan atau menghapus isi database.

Untuk memisahkan riwayat per pengguna, ubah `CHAT_IDENTITY_MODE` pada
`streamlit_app.py` dari `single` menjadi `multi`. Pada mode itu, token
`chat_owner` di URL menjadi identitas pengguna anonim dan tercatat di
`chat_users`. Token URL belum merupakan autentikasi; tambahkan login sebelum
memberi akses kepada beberapa pengguna melalui jaringan. Riwayat yang dibuat
dalam mode satu identitas tetap tersimpan di database dan memerlukan penentuan
pemilik sebelum dialihkan ke akun pengguna tertentu.

Aplikasi ini menggunakan arsitektur modular yang memisahkan **Database**, **FastAPI Backend**, dan **Streamlit Frontend**.

### 1. Jalankan Database PostgreSQL (`pgvector`)
Jalankan container PostgreSQL dengan ekstensi `pgvector` menggunakan Docker:

```bash
docker run --name pgvector-container \
  -e POSTGRES_USER=langchain \
  -e POSTGRES_PASSWORD=langchain \
  -e POSTGRES_DB=langchain \
  -p 5432:5432 \
  -d pgvector/pgvector:pg16
```

*(Opsional)* Jika database belum terisi dokumen, jalankan skrip pemuatan dokumen:
```bash
uv run python -m rag.doc_loader
```

Knowledge base mendukung PDF dan DOCX dalam `data/`. Loader menyimpan struktur
heading/tabel, lokasi sumber, dan hash isi; sumber yang tidak berubah dilewati,
sedangkan sumber yang berubah diindeks ulang. Dukungan DOCX mencakup pencarian
dan pembuatan RKS dengan penomoran serta tabel Word tetap dapat diedit.
Panduan dan batasannya tersedia di [Dukungan DOCX](docs/docx_knowledge_base.md).

---

### 2. Jalankan FastAPI Backend Server (Port 8000)
Buka terminal/PowerShell pertama di root direktori proyek, lalu jalankan:

```bash
uv run python -m api.main
```
*(Atau via uvicorn CLI: `uv run uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload`)*

> **Catatan Konfigurasi Port:** Port dan Host dapat dikonfigurasi langsung di dalam `api/main.py` atau melalui file `.env` (`FASTAPI_HOST=127.0.0.1` dan `FASTAPI_PORT=8000`).

* **URL Server:** `http://127.0.0.1:8000`
* **Dokumentasi Interaktif (Swagger UI):** `http://127.0.0.1:8000/docs`
* **Healthcheck Endpoint:** `http://127.0.0.1:8000/api/health`

---

### 3. Jalankan Streamlit Frontend (Port 8501)
Buka terminal/PowerShell kedua di root direktori proyek, lalu jalankan:

```bash
uv run streamlit run streamlit_app.py
```

* **URL Aplikasi Web:** `http://localhost:8501`

---

## 📖 Panduan Penggunaan Antarmuka Web

Di antarmuka Streamlit, Anda dapat berpindah mode kerja menggunakan **Menu Navigasi di Sidebar (sebelah kiri)**:

### A. Mode "💬 Chatbot & RKS Viewer"
1. **Percakapan Cerdas:** Tanyakan rincian pekerjaan, persyaratan teknis, atau ketentuan garansi.
2. **Pengambilan Dokumen:** Minta asisten untuk mengambil dokumen (*"Ambilkan dokumen RKS overhaul tangki 041T304"*). Dokumen akan tampil di panel *Split-Screen Document Viewer*.
3. **Konversi ke Word (.docx):**
   * Minta asisten di chat (*"Konversikan ke Word/DOCX"*), ATAU
   * Gunakan tab **"Convert PDF to DOCX"** pada Document Viewer / tombol popup.
   * File `.docx` resmi dengan sampul berbingkai, lembar pengesahan tanda tangan, daftar isi, dan header/footer Pertamina akan langsung siap diunduh.

### B. Mode "📑 Dokumen Tender Generator"
1. **Deteksi RKS Otomatis:** Jika sebelumnya Anda telah mengonversi dokumen RKS di sesi chat, file tersebut otomatis terdeteksi dengan badge hijau. Anda juga dapat mengunggah file RKS lain (DOCX/PDF).
2. **Dokumen BOQ (Opsional):** Unggah file Bill of Quantities dalam format Excel (`.xlsx`, `.xls`), `.csv`, atau `.pdf`.
3. **Ekstraksi Otomatis:** Klik **"🔍 Ekstrak Data dari Dokumen Pendukung"** untuk mengisi parameter pengadaan (Nama Pengadaan, Risiko CSMS, Nilai HPS Prime Cost & Total + K&R, dan ringkasan lingkup kerja) secara otomatis.
4. **Generate Dokumen Tender:** Tinjau form parameter, lalu klik **"🚀 Generate Dokumen Tender (.docx)"**.
   * FastAPI akan menyusun dokumen tender lengkap (~40-60 halaman standar Pertamina Patra Niaga).
   * Tombol unduh file `.docx` siap pakai akan langsung ditampilkan di layar.

### C. Gudang Rancangan Kontrak

Setiap tender yang berhasil dibuat juga menghasilkan DOCX tersendiri untuk Bagian B
(rancangan kontrak). Salinan DOCX dan identitas RKS asalnya, bila memakai RKS hasil
generator, disimpan di tabel PostgreSQL `contract_drafts`. Buka **Gudang Rancangan
Kontrak** pada sidebar untuk mencari, meninjau halaman, mengunduh DOCX, atau kembali
ke RKS asal. Dokumen arsip ini berstatus draft dan tidak dimasukkan otomatis ke
knowledge base. Jika penyimpanan database gagal, halaman tender menampilkan
peringatan; file tender tetap tersedia untuk diunduh.

---

## 📂 Struktur Direktori Proyek

```text
Pertamina_Chatbot/
├── api/
│   ├── __init__.py
│   └── main.py                     # FastAPI REST server & endpoints
├── assets/
│   ├── logo_pertamina.png          # Logo resmi Pertamina
│   └── doc_config.json             # Konfigurasi styling dokumen Word
├── data/                           # Dokumen mentah PDF RKS
├── output/                         # Output dokumen DOCX hasil render
├── rag/
│   ├── doc_loader.py               # Ingestion dokumen ke PostgreSQL
│   └── vector_store.py             # Koneksi pgvector & fungsi retrieval
├── tools/
│   ├── docx_exporter.py            # Mesin render DOCX resmi RKS Pertamina
│   ├── pdf_converter.py            # Utilitas pembaca metadata PDF
│   └── tender/
│       ├── __init__.py             # Package init & tool exports
│       ├── docx.py                 # Pure python-docx generator dokumen tender
│       ├── generator.py            # LangChain orchestrator & prompt LLM tender
│       ├── schema.py               # Pydantic models & JSON schema
│       ├── static_content.py       # Boilerplate pasal hukum & IKPP
│       ├── extractor.py            # Ekstraktor data RKS & BOQ
│       └── streamlit_tender_view.py# Halaman UI Streamlit Tender Generator
├── agent.py                        # LangGraph workflow agen chatbot
├── config.py                       # Konfigurasi model LLM & OpenRouter
├── streamlit_app.py                # Aplikasi antarmuka web Streamlit
├── pyproject.toml                  # Konfigurasi dependensi project (uv)
└── README.md                       # Dokumentasi petunjuk penggunaan
```
