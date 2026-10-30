# Template React — Pertamina Document Assistant

Template antarmuka untuk branch `integrasi-fe`. Kontennya adalah data demo lokal. Fitur chat AI, pencarian RKS, PDF asli, dan konversi DOCX belum terhubung ke backend.

## Menjalankan

```bash
cd frontend
npm install
npm run dev
```

Buka alamat lokal yang dicetak Vite. Untuk membuat versi produksi, jalankan `npm run build`.

## Cakupan template

- Chat dan riwayat sesi tersimpan di `localStorage` browser.
- Contoh pertanyaan menampilkan jawaban dan dokumen demo.
- Panel dokumen memiliki tab isi, daftar bab, dan konversi.
- Tombol konversi menunjukkan status menunggu API dan tidak membuat file palsu.

Saat backend tersedia, ganti fungsi `createDemoResponse` di `src/App.jsx` dengan panggilan API untuk chat dan pemuatan dokumen. Dialog konversi perlu dihubungkan ke endpoint konversi dan unduhan DOCX. Berkas Python/Streamlit di root proyek tidak diubah oleh template ini.
