# Template React — Pertamina Document Assistant

Antarmuka React untuk `integrasi-fe`. Tanpa backend, aplikasi tetap terbuka dalam mode demo. Jika API `integrasi-be` berjalan, frontend memakai jawaban agent, dokumen RKS, dan konversi DOCX dari backend.

## Menjalankan

```bash
cd frontend
npm install
npm run dev
```

Buka alamat lokal yang dicetak Vite. Vite meneruskan permintaan `/api` ke `http://127.0.0.1:8000`, sehingga browser cukup memakai satu origin frontend. Untuk membuat versi produksi, jalankan `npm run build`; saat deployment, `/api` harus diarahkan ke backend.

## Cakupan template

- Tanpa backend: contoh pertanyaan menampilkan jawaban dan dokumen demo. Konversi tidak menghasilkan file palsu.
- Dengan backend: tombol status di kanan atas menampilkan koneksi; chat memakai API dan viewer menampilkan isi dokumen asli.
- Konversi DOCX aktif bila PDF sumber ditemukan backend. File yang selesai dapat diunduh melalui URL unduhan dari API.
- Tampilan riwayat tetap disimpan di `localStorage`. Sesi agent di backend masih berada dalam memori dan akan dibuat ulang jika server dimulai ulang.

Backend berada di branch `integrasi-be`, yang bisa dijalankan dari checkout/worktree terpisah. Backend belum digabung ke branch ini. Berkas Python/Streamlit di root `integrasi-fe` tidak diubah.
