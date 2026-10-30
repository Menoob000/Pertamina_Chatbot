# Pertamina Chatbot

Chatbot AI untuk mempermudah dan mengotomatisasi proses pengadaan di lingkungan **PT Pertamina Patra Niaga**.

---

## 🚀 Cara Menjalankan Proyek

### 1. Prasyarat
Pastikan Anda telah menginstal software berikut:
* **Docker**
* **Python** & **`uv`** (Package manager)

---

### 2. Jalankan Database (pgvector)
Jalankan container PostgreSQL dengan ekstensi `pgvector` menggunakan Docker:

```bash
docker run --name pgvector-container \
  -e POSTGRES_USER=langchain \
  -e POSTGRES_PASSWORD=langchain \
  -e POSTGRES_DB=langchain \
  -p 5432:5432 \
  -d pgvector/pgvector:pg16
