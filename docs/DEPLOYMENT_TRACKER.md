# Deployment Tracker — Pertamina Chatbot (Tanpa VPS)

Dokumen ini mencatat tahap-tahap deployment beserta statusnya. Centang `[x]` setelah selesai
dan isi kolom **Catatan** (tanggal, URL, masalah yang ditemui) agar jadi rekam jejak.

**Arsitektur target**

```
Browser ──► Frontend React (Vercel) ──► Backend FastAPI (Hugging Face Spaces / Cloud Run)
                                              │
                                              ├──► Supabase (Postgres + pgvector)
                                              └──► OpenRouter (LLM)
```

| Komponen | Layanan | Status | URL | Catatan |
|---|---|---|---|---|
| Database | Supabase | ☑ sudah ada & terisi | | Tinggal verifikasi (Tahap 1) |
| Backend | **Azure Container Apps** (Azure for Students, `indonesiacentral`) | ☑ live 2026-11-24 | https://pertamina-backend.grayriver-e4c2bf23.indonesiacentral.azurecontainerapps.io | Image `ghcr.io/flax3-ops/pertamina-backend:latest` |
| Frontend | Vercel (project `pertamina-chatbot`, akun `furqonfikri97-1863`) | ☑ live 2026-11-24 | https://pertamina-chatbot.vercel.app | Deploy via CLI dari `Frontend/frontend` |
| Streamlit | Streamlit Community Cloud | ☑ sudah jalan | https://pertaminachatbot-enawev7dvaq8t6sj79yrba.streamlit.app | Lihat Tahap 6 |

> Syarat dan batas free tier tiap layanan bisa berubah. Cek ulang di situs resmi sebelum mulai.

### Keputusan (2026-11-23)

| Topik | Keputusan |
|---|---|
| Database | Supabase yang sudah ada dan sudah terisi knowledge base |
| Backend | ~~Hugging Face Spaces~~ → **Azure Container Apps** via Azure for Students (2026-11-24). Script: `scripts/deploy_azure.py` |
| Fitur aktif | Preview PDF (LibreOffice), web search (Tavily), Streamlit app |
| Google Drive KB | **Tidak di-setup untuk deploy awal** (2026-11-23). Opsional, bisa ditambahkan nanti tanpa ubah kode. |
| Folder `data/` | **Dibutuhkan backend saat jalan** (lihat temuan di bawah), jadi ikut dimasukkan ke image |
| Repo GitHub | Tetap **publik**, PDF di `data/` dibiarkan (keputusan pemilik repo, 2026-11-23) |
| Streamlit | Deploy dari branch `main` |
| Google Drive | Dilewati. Deploy memakai Supabase yang sudah terisi + PDF di `data/` |

> **Implikasi tanpa Google Drive:**
> - Tombol sync di halaman Knowledge Base tidak berfungsi (status "belum terhubung"). Chat, RAG, RKS, amandemen, dan tender tidak terpengaruh.
> - Dokumen baru ditambahkan manual: index ke Supabase dari lokal (`python -m rag.doc_loader`), dan bila perlu jadi sumber RKS, commit PDF ke `data/` lalu push ulang ke Space.
> - Untuk mengaktifkan nanti: ikuti Tahap 2.3a, isi secret `GDRIVE_*`, restart Space.

> **Kenapa Space public, bukan private:** URL Space private hanya bisa diakses dengan token Hugging Face.
> Frontend di Vercel dipanggil dari browser pengguna, jadi tidak bisa menyertakan token itu tanpa membocorkannya.
> Secrets di Space public tetap tersembunyi. Yang terlihat hanya file kode, dan isinya sama dengan repo GitHub yang sudah publik.

### Temuan dari kode

- `tools/rks/catalog.py` membaca `data/*.pdf` sebagai sumber RKS (`list_sources`, `search_sources`). Tanpa file di `data/`, generator RKS tidak punya sumber.
- `tools/pdf_converter.py` dan `streamlit_app.py` juga mencari PDF di `data/`.
- Sinkronisasi Google Drive (`api/gdrive.py` → `tools/gdrive/sync.py`) **menulis** file ke `./data`, jadi folder itu harus bisa ditulis. `compose.backend.yaml` me-mount `data` sebagai read-only (`:ro`), yang akan membuat sync gagal di setup VPS tersebut.
- Storage HF Spaces tidak permanen: file hasil sync Google Drive hilang saat restart. Ada dua pilihan: sertakan PDF di image, atau jalankan sync ulang setelah Space menyala.
- Tavily dipakai di `agent.py` (`TavilySearch`) dan membaca `TAVILY_API_KEY` secara otomatis.
- 11 PDF di `data/` sudah ter-commit di repo GitHub `Menoob000/Pertamina_Chatbot`, dan repo tersebut **publik** (dicek 2026-11-23). Dokumen tersebut saat ini bisa diakses siapa saja. Diputuskan: repo tetap publik.
- Google Drive: `tools/gdrive/auth.py` menulis `GDRIVE_CREDENTIALS_JSON` / `GDRIVE_TOKEN_JSON` dari env ke `credentials.json` / `token.json`, lalu me-refresh token otomatis bila ada `refresh_token`. Kedua file sudah ada di `.gitignore`. Saat dicek (2026-11-23), keduanya belum ada di `.env` maupun di root project.

---

## Tahap 0 — Persiapan repo

- [ ] Branch kerja sudah up to date dengan `main` (`git pull`).
- [ ] `node_modules` tidak ikut ter-commit (tambahkan ke `.gitignore`, lalu `git rm -r --cached`).
- [ ] Folder `Frontend/frontend/node_modules.bak_local` (backup lokal) dihapus jika tidak diperlukan.
- [ ] `.env` tidak ter-commit. Periksa dengan `git ls-files | grep -i "\.env"`.
- [ ] Periksa isi `data/`: dokumen internal Pertamina **jangan** ikut ke repo/Space publik.
- [ ] Kumpulkan semua kunci/secret di satu tempat aman (password manager), bukan di file repo.

| Tanggal | Catatan |
|---|---|
| | |

---

## Tahap 1 — Database (Supabase)

Project sudah memakai `DATABASE_URL` (lihat `rag/vector_store.py`, `agent.py`, `rag/conversation_store.py`).

Project Supabase **sudah ada dan terisi**, jadi tahap ini hanya verifikasi.

- [ ] Pastikan `DATABASE_URL` di `.env` lokal adalah connection string **Session pooler** (bukan direct connection yang hanya IPv6).
- [ ] Pastikan ekstensi `vector` aktif (Database → Extensions).
- [ ] Cek koleksi `knowledge_base` berisi data (tabel `langchain_pg_collection` dan `langchain_pg_embedding`).
- [ ] Uji koneksi dari lokal: jalankan backend lalu kirim satu pertanyaan RAG.
- [ ] Cek project Supabase tidak dalam status *paused* (project free di-pause setelah lama tidak aktif).

| Tanggal | Catatan |
|---|---|
| | |

---

## Tahap 2 — Backend (Hugging Face Spaces, SDK Docker)

Backend memakai `Dockerfile.backend` (torch CPU, docling, LibreOffice, model embedding).
RAM besar dibutuhkan, karena itu dipilih HF Spaces (sekitar 16 GB RAM pada free tier).

### 2.1 Siapkan Space
- [ ] Buat akun https://huggingface.co → New Space → SDK **Docker** → visibility **Public** (Space private tidak bisa dipanggil dari frontend Vercel).
- [ ] Space memakai repo git terpisah. Clone repo Space ke folder terpisah atau tambahkan sebagai remote.

### 2.2 Sesuaikan file untuk Space
- [ ] HF mengharuskan file bernama `Dockerfile` di root Space. Salin `Dockerfile.backend` menjadi `Dockerfile` (di repo Space, bukan di repo utama).
- [ ] Buat `README.md` di root repo Space dengan front matter:
  ```yaml
  ---
  title: Pertamina Chatbot Backend
  sdk: docker
  app_port: 8000
  ---
  ```
  (`app_port: 8000` dipakai agar `CMD` uvicorn di Dockerfile tidak perlu diubah.)
- [ ] Pastikan `HEALTHCHECK` dan `CMD` tetap memakai port 8000.
- [ ] Container HF berjalan sebagai user non-root (UID 1000). Pastikan `/app/output` **dan** `/app/data` dapat ditulis (mis. `chmod -R 777 /app/output /app/data` di Dockerfile), karena sync Google Drive menulis ke `data/`.
- [ ] Sertakan `data/*.pdf` di image (dibutuhkan `tools/rks/catalog.py`). File ini akan terlihat di Space public, sama seperti di repo GitHub.
- [ ] Jangan sertakan `.env`, `node_modules`, `frontend/`, `tmp/`, `output/`, `.worktrees/`, `.uv-cache/` ke repo Space. Gunakan `.dockerignore` atau pilih file yang di-push.

### 2.3 Secrets dan variables (Settings → Variables and secrets)
Isi sebagai **Secret** (kecuali yang tertulis Variable):

- [ ] `DATABASE_URL`
- [ ] `OPENROUTER_API_KEY`
- [ ] `LLM_MODEL_NAME` (Variable)
- [ ] `EMBEDDING_MODEL` (Variable, harus sama dengan build arg di Dockerfile)
- [ ] `CORS_ORIGINS` (isi setelah URL frontend diketahui, lihat Tahap 4)
- [ ] `TAVILY_API_KEY` (web search di `agent.py`)
- [ ] *(Opsional, dilewati untuk deploy awal)* `GDRIVE_CREDENTIALS_JSON` dan `GDRIVE_TOKEN_JSON` (lewat Tahap 2.3a)
- [ ] Kunci lain yang dipakai di `.env` lokal (mis. Qdrant) bila fiturnya aktif

### 2.3a Setup Google Drive OAuth (OPSIONAL, dilewati untuk deploy awal)
Di Space tidak bisa login OAuth lewat browser, jadi token dibuat di laptop lalu disalin sebagai secret.
Scope yang dipakai (`tools/gdrive/auth.py`): `drive.readonly`, `userinfo.email`, `openid`.

- [ ] Buka https://console.cloud.google.com → buat/pilih project → aktifkan **Google Drive API**.
- [ ] Konfigurasi **OAuth consent screen** (tipe External), tambahkan email sendiri sebagai test user.
- [ ] Ubah status publishing ke **In production**. Jika tetap di *Testing*, refresh token kedaluwarsa setelah 7 hari dan sync Drive di Space akan berhenti. Aplikasi yang belum diverifikasi Google tetap bisa dipakai sendiri, hanya muncul layar peringatan saat login.
- [ ] Buat **OAuth client ID** tipe **Desktop app**, unduh JSON-nya, simpan sebagai `credentials.json` di root project (sudah di-`.gitignore`).
- [ ] Jalankan backend lokal, lalu login Google Drive dari UI. Ini membuat `token.json` lewat `authenticate_google_drive()`.
- [ ] Pastikan `token.json` berisi field `refresh_token`.
- [ ] Salin seluruh isi `credentials.json` ke secret `GDRIVE_CREDENTIALS_JSON`, dan isi `token.json` ke `GDRIVE_TOKEN_JSON` (di HF Space dan Streamlit secrets).
- [ ] Setelah Space menyala, isi Folder ID Google Drive di UI lalu jalankan sync. Ulangi sync setiap kali Space restart, karena storage tidak permanen.

### 2.4 Build dan uji
- [ ] Push ke Space, tunggu build selesai (build pertama lama karena torch dan model).
- [ ] Uji health: `https://<user>-<space>.hf.space/api/health` mengembalikan OK.
- [ ] Uji satu request chat dari `curl`/Postman.
- [ ] Catat URL backend di tabel atas.

| Tanggal | Catatan |
|---|---|
| | |

---

## Tahap 3 — Frontend (Vercel)

Frontend ada di `Frontend/frontend` (F besar, Vercel membedakan huruf besar/kecil) (Vite). `vercel.json` sudah tersedia.

- [ ] Buat akun https://vercel.com dan hubungkan GitHub.
- [ ] Import repo, set **Root Directory** = `Frontend/frontend`.
- [ ] Framework preset: Vite. Build command `npm run build`, output `dist`.
- [ ] Environment variable: `VITE_API_URL` = URL backend dari Tahap 2 (tanpa `/api`, tanpa `/` di akhir).
- [ ] Deploy dan catat URL (mis. `https://xxx.vercel.app`).
- [ ] Buka halaman, pastikan request ke backend tidak error di tab Network.

| Tanggal | Catatan |
|---|---|
| | |

---

## Tahap 4 — Hubungkan frontend dan backend

- [ ] Isi `CORS_ORIGINS` di backend dengan URL Vercel (tanpa `/` di akhir). Jika memakai preview deploy, pertimbangkan `CORS_ORIGIN_REGEX`.
- [ ] Restart Space agar variabel terbaca.
- [ ] Uji end-to-end: kirim pesan di UI dan terima jawaban.
- [ ] Uji fitur utama satu per satu:
  - [ ] Chat RAG
  - [ ] Generate RKS dan download dokumen
  - [ ] Preview PDF (LibreOffice)
  - [ ] Generator amandemen
  - [ ] Dokumen tender (upload DP3)
  - [ ] Google Drive Knowledge Base (dilewati, cukup pastikan halaman tidak crash)

| Tanggal | Catatan |
|---|---|
| | |

---

## Tahap 5 — Pasca-deploy

- [ ] Catat batas free tier yang dipakai (RAM, jam aktif, storage) dan tanggal cek ulang.
- [ ] Pasang monitor sederhana (mis. UptimeRobot) pada `/api/health` agar Space tidak tidur.
- [ ] Verifikasi kekurangan yang diketahui:
  - Riwayat chat (`MemorySaver`) hilang saat restart.
  - File di `output/` tidak permanen, jadi download segera.
- [ ] Siapkan rencana cadangan: pindah ke Google Cloud Run bila HF Spaces tidak memadai.
- [ ] Rotasi API key jika sempat ter-commit atau terekspos.

---

## Tahap 6 — Streamlit (Streamlit Community Cloud)

Streamlit app sudah berjalan di Streamlit Community Cloud. Tahap ini memastikan app tetap sinkron dengan `main`.

- [ ] Set app Streamlit agar deploy dari branch `main` (keputusan 2026-11-23). Cek di Manage app → Settings, ganti bila masih memakai branch lain.
- [ ] Cek secrets Streamlit (`DATABASE_URL`, `OPENROUTER_API_KEY`, `TAVILY_API_KEY`, `GDRIVE_*`) sama dengan backend.
- [ ] `streamlit_app.py` meng-import `agent` secara langsung, jadi Streamlit menjalankan agent sendiri dan tidak bergantung pada backend HF.
- [ ] Fitur tender di Streamlit (`tools/tender/streamlit_tender_view.py`) memanggil FastAPI lewat `FASTAPI_BASE_URL`. Set ke URL backend HF agar fitur ini jalan.
- [ ] Pantau batas RAM Streamlit Community Cloud. Jika app sering crash karena memori, pindahkan ke HF Space kedua.
- [ ] Reboot app setelah update `main` dan uji fitur utamanya.

| Tanggal | Catatan |
|---|---|
| | |

---

## Alternatif backend: Google Cloud Run

Gunakan bila HF Spaces tidak cocok. Butuh kartu untuk verifikasi, instance scale-to-zero.

- [ ] Buat project GCP, aktifkan Cloud Run dan Artifact Registry.
- [ ] Build image dari `Dockerfile.backend`, push ke Artifact Registry.
- [ ] Deploy dengan memori minimal 2 GiB, CPU 1–2, port 8000, `--min-instances 0` (atau 1 agar tanpa cold start, tapi berbiaya).
- [ ] Isi environment variable/secret yang sama seperti di Tahap 2.3.
- [ ] Ganti `VITE_API_URL` di Vercel ke URL Cloud Run, lalu redeploy.

---

## Log masalah

| Tanggal | Masalah | Penyebab | Solusi |
|---|---|---|---|
| 2026-11-24 | `az acr create` ditolak di `southeastasia` (RequestDisallowedByAzure) | Langganan student hanya boleh: centralindia, indonesiacentral, indiasouthcentral, eastasia, japanwest | Container App di `indonesiacentral` |
| 2026-11-24 | `az acr build` gagal di `indonesiacentral` (NoRegisteredProviderFound) | ACR Tasks tidak tersedia di region itu | ACR dipindah ke `eastasia` |
| 2026-11-24 | `az acr build` ditolak (TasksOperationsNotAllowed) | ACR Tasks diblokir untuk langganan student | Build image lewat GitHub Actions di fork `Flax3-ops/Pertamina_Chatbot`, push ke ghcr.io |
| 2026-11-24 | Gagal membuat HF Space: `402 Payment Required` | Docker/Gradio Space di cpu-basic sekarang wajib langganan PRO | Pindah ke Azure Container Apps (Azure for Students) |
| | | | |

---

## Tahap 2 (pengganti) — Backend di Azure Container Apps

- [x] Install Azure CLI (`winget install -e --id Microsoft.AzureCLI`), versi 2.93.0 — 2026-11-24
- [ ] Aktifkan Azure for Students: https://azure.microsoft.com/free/students (login email kampus)
- [ ] `az login` dan pastikan langganan aktif: `az account show`
- [ ] Jalankan `.venv/Scripts/python.exe scripts/deploy_azure.py`
  - Membuat resource group `pertamina-chatbot-rg` (region `indonesiacentral` (Southeast Asia diblokir policy langganan student)), ACR Basic, Container Apps environment
  - Build image lewat `az acr build`; bila ACR Tasks diblokir untuk langganan student, fallback ke Docker lokal (Docker Desktop harus jalan)
  - Container App: 1 vCPU, 2 GiB, min replica 0 (scale-to-zero, ada cold start), ingress publik port 8000
  - Secrets dari `.env`: DATABASE_URL, OPENROUTER_API_KEY, TAVILY_API_KEY, LANGSMITH_API_KEY
- [ ] Uji `https://<fqdn>/api/health`
- [ ] Setelah Vercel jadi: `scripts/deploy_azure.py --skip-build --cors https://<app>.vercel.app`
- [ ] Pantau sisa kredit di portal Azure (ACR Basic ± $5/bulan dipotong dari kredit)

| Tanggal | Catatan |
|---|---|
| | |

### Build image lewat GitHub Actions (karena ACR Tasks diblokir)

- Fork: https://github.com/Flax3-ops/Pertamina_Chatbot, branch `deploy-azure`
- Workflow: `.github/workflows/build-backend.yml` → push ke `ghcr.io/flax3-ops/pertamina-backend:latest`
- Konteks build memakai `deploy/hf-space/Dockerfile.dockerignore` (folder `data/` ikut masuk image)
- [x] Aktifkan Actions di fork (tab **Actions** → *I understand my workflows, go ahead and enable them*)
- [x] Workflow sukses (tab Actions)
- [x] Ubah visibility package `pertamina-backend` ke **Public** (profil GitHub → Packages → Package settings), agar Azure bisa pull tanpa kredensial
- [x] `scripts/deploy_azure.py --image ghcr.io/flax3-ops/pertamina-backend:latest`
- [x] Hapus ACR `eastasia` yang tidak terpakai agar kredit tidak terpotong

---

## Hasil verifikasi (2026-11-24)

| Uji | Hasil |
|---|---|
| `GET /api/health` | 200 `healthy` (±1 dtk saat hangat) |
| CORS preflight dari `https://pertamina-chatbot.vercel.app` | 200, `Access-Control-Allow-Origin` sesuai |
| CORS dari origin lain | 400 (ditolak, sesuai harapan) |
| Chat end-to-end (`POST /api/chat`) | 200, jawaban LLM ±16 dtk |
| Supabase (`GET /api/chat/threads`) | Terhubung, thread terbaca |
| Sumber RKS dari `data/` di image (`/api/rks/sources?query=tangki`) | 5 sumber ditemukan |
| Frontend memuat URL backend | `VITE_API_URL` tertanam di bundle JS |

## Cara update setelah ada perubahan kode

1. Backend: push ke branch `deploy-azure` di fork → GitHub Actions build image baru → lalu
   `.venv/Scripts/python.exe scripts/deploy_azure.py --image ghcr.io/flax3-ops/pertamina-backend:latest --cors https://pertamina-chatbot.vercel.app`
   (selalu sertakan `--image`; tanpa itu script akan membuat ulang ACR yang berbayar).
2. Frontend: dari `Frontend/frontend` jalankan `npx vercel deploy --prod --yes`.

## Resource Azure yang aktif (`pertamina-chatbot-rg`)

- Container App `pertamina-backend` (1 vCPU, 2 GiB, min replica 0 → cold start 1–3 menit setelah idle)
- Container Apps environment `pertamina-env`
- Log Analytics workspace (biaya kecil dari kredit)

---

## Google Drive Knowledge Base di production (2026-11-25)

- Akun login (token): `mahsanulfurqon8@gmail.com`, izin `drive.readonly`. Secret Azure: `GDRIVE_CREDENTIALS_JSON`, `GDRIVE_TOKEN_JSON`.
- Folder: **Master_data_RKS** milik `nathanael.erens@gmail.com`, dibagikan ke akun di atas
  (https://drive.google.com/drive/folders/1hUq-OOpHKnvhqowwQcLgB3A6QrNKwK9E). Default lewat env `GDRIVE_FOLDER_ID`;
  bisa diganti dari halaman Knowledge Base (berlaku sampai container restart). Ganti permanen:
  ubah `GDRIVE_FOLDER_ID` di `.env` lalu jalankan `scripts/deploy_azure.py --image ...`.
- Sync pertama: 32 file di Drive → **15 dokumen baru ter-index**, 10 dokumen lama di-skip (dedup sha256),
  Supabase sekarang **25 dokumen / 3.565 chunk, tanpa duplikat**.
- RAG di production sudah berfungsi setelah perbaikan torch/torchvision (commit `9676b90`).

| Masalah | Jumlah | Status |
|---|---|---|
| PDF hasil scan tanpa teks (butuh OCR) | 6 | Belum di-index. Project belum punya OCR |
| PDF dengan encoding font rusak (`RKS-Pengadaan Tug Boat 3,000 HP.pdf`) | 1 | Ter-index tapi teks acak, tidak bisa ditemukan pencarian |
| DOCX tanpa `numbering.xml` (`RENCANA_KERJA_DAN_SYARAT_RKS_PROYEK_KONS.docx`) | 1 | Diperbaiki (commit `8707f6a`), ter-index pada sync berikutnya setelah redeploy |

Catatan: token OAuth pertama yang dipakai tidak punya izin Drive (`invalid_scope`), sehingga dibuat ulang
dengan `prompt=consent`. Jika consent screen masih *Testing*, refresh token kedaluwarsa 7 hari.
