"""
Static legal boilerplate and standard templates for Dokumen Tender Pertamina Patra Niaga:
- BAB II (Ketentuan Umum IKPP - 30 Articles)
- Appendices (Lampiran 1A - 8 Standard Forms & CSMS Evaluation Matrix)
- Bagian B: Standard Contract Articles (Pasal 1 - 18, PI-07, SP3MK)
"""

# ──────────────────────────────────────────────────────────────
# BAB II KETENTUAN UMUM IKPP (Standard Articles)
# ──────────────────────────────────────────────────────────────

BAB_II_ARTICLES = [
    {
        "nomor": 1,
        "judul": "DEFINISI",
        "paragraf_intro": "Dalam Dokumen IKPP ini dipergunakan pengertian, istilah dan singkatan pada Pedoman Pengadaan Barang/Jasa No. A03-001/PNG200000/2024-S9 Revisi ke-1 dan STK terkait Pengadaan Barang/Jasa lainnya beserta perubahannya.",
        "poin": [
            ("1", "Barang/Jasa Spesifik", "Barang/Jasa yang berdasarkan tuntutan teknis dan/atau persyaratan teknologi dan/atau keahlian tertentu dan/atau kepentingan operasi dan/atau keselamatan dan/atau lisensi jaminan (warranty) tidak dapat digantikan dengan Barang atau peralatan lain yang sejenis atau hanya dapat dilaksanakan oleh Penyedia Barang/Jasa tertentu."),
            ("2", "Daftar Penyedia Teregistrasi (DPT)", "Daftar Penyedia Barang/Jasa yang lulus Registrasi dan dibuktikan dengan kepemilikan Surat Keterangan Teregistrasi (SKT)."),
            ("3", "Dokumen Pemenuhan Persyaratan Kualifikasi (DP2K)", "Dokumen yang disampaikan Peserta, yang terdiri dari Dokumen Pemenuhan Persyaratan Kualifikasi Umum (DP2KU) dan/atau Dokumen Pemenuhan Persyaratan Kualifikasi Khusus (DP2KK)."),
            ("4", "Dokumen Pemilihan", "Dokumen yang terdiri dari Dokumen Penilaian Kualifikasi (DPK) dan Dokumen Tender (DT)."),
            ("5", "Dokumen Penawaran", "Dokumen yang disampaikan Peserta yang berisi penawaran administrasi, teknis, HSSE Plan (apabila dipersyaratkan), TKDN (apabila dipersyaratkan), dan komersial."),
            ("6", "Dokumen Tender", "Dokumen yang terdiri dari Dokumen Instruksi dan Ketentuan Pelaksanaan Pemilihan (IKPP) serta Rancangan Kontrak (RK)."),
            ("7", "Fungsi Peminta Pengadaan (FPP)", "Fungsi di lingkungan Organisasi Pertamina yang memiliki kewenangan dalam perencanaan kebutuhan Barang/Jasa, dan/atau pengajuan permintaan Barang/Jasa, dan/atau pengawasan Kontrak, dan/atau penerimaan hasil Pekerjaan dan/atau pemanfaatan Barang/Jasa hasil pengadaan."),
            ("8", "Harga Evaluasi Akhir (HEA)", "Penyesuaian atau normalisasi harga terhadap penawaran komersial yang disampaikan oleh Peserta, dengan memperhitungkan komponen preferensi harga berdasarkan capaian/komitmen TKDN dalam rangka untuk menentukan peringkat Peserta."),
            ("9", "Harga Perkiraan Sendiri/Owner Estimate (HPS/OE)", "Perhitungan/kalkulasi perkiraan biaya pekerjaan yang disusun oleh FPP dan disetujui oleh Pejabat Berwenang dari lini FPP dalam rangka pengadaan Barang/Jasa."),
            ("10", "Hubungan Istimewa", "Hubungan antara dua atau lebih Penyedia Barang/Jasa yang dikendalikan langsung oleh pihak yang sama, yaitu lebih dari 50% pemegang saham dan/atau salah satu pengurusnya sama."),
            ("11", "Instruksi dan Ketentuan Pelaksanaan Pemilihan (IKPP)", "Bagian dari Dokumen Tender yang antara lain berisi ketentuan penyampaian dokumen penawaran, kriteria evaluasi, ketentuan sanggahan, dll."),
            ("12", "Jasa Konstruksi", "Layanan Jasa Konsultansi Konstruksi dan/atau Pekerjaan Konstruksi."),
            ("13", "Jasa Konsultansi Konstruksi", "Layanan keseluruhan atau sebagian kegiatan yang meliputi pengkajian, perencanaan, perancangan, pengawasan, dan manajemen penyelenggaraan konstruksi suatu bangunan."),
            ("14", "Jasa Konsultansi Non-Konstruksi", "Jasa layanan profesional yang membutuhkan keahlian tertentu di berbagai bidang keilmuan yang mengutamakan adanya olah pikir."),
            ("15", "Jasa Lainnya", "Segala pekerjaan atau penyediaan Jasa selain Jasa Konsultansi, Pekerjaan Konstruksi serta Pengadaan Barang."),
            ("16", "Klarifikasi", "Permintaan penjelasan atas materi penawaran selama proses Pemilihan Penyedia oleh Pelaksana Pemilihan Penyedia bersama FPP dan Fungsi Terkait kepada Calon Peserta maupun Peserta dan hasilnya dicatat dalam risalah rapat."),
            ("17", "Komponen Dalam Negeri pada Barang", "Penggunaan bahan baku, rancang bangun dan perekayasaan yang mengandung unsur manufaktur, fabrikasi, perakitan dan penyelesaian akhir pekerjaan yang berasal dari dan dilaksanakan di dalam negeri."),
            ("18", "Komponen Dalam Negeri pada Jasa", "Penggunaan jasa sampai dengan penyerahan akhir dengan memanfaatkan tenaga kerja, termasuk tenaga ahli, alat kerja termasuk perangkat lunak dan sarana pendukung yang berasal dari dan dilaksanakan di dalam negeri."),
            ("19", "Komponen Dalam Negeri pada Gabungan Barang dan Jasa", "Penggunaan bahan baku, rancang bangun dan perekayasaan serta penggunaan jasa dengan memanfaatkan tenaga kerja dan peralatan sampai dengan penyerahan akhir yang berasal dari dan dilaksanakan di dalam negeri."),
            ("20", "Konsorsium", "Gabungan dari dua atau lebih Penyedia Barang/Jasa, dalam rangka mencapai tujuan tertentu dengan menyatukan sumber daya yang dimiliki Para Pihak, di mana masing-masing Pemimpin dan Anggota Konsorsium tetap berdiri sendiri-sendiri."),
            ("21", "Kontrak", "Perjanjian pelaksanaan penyediaan Barang/Jasa antara Pertamina dengan Pelaksana Kontrak yang dituangkan dalam kesepakatan tertulis dan bersifat mengikat."),
            ("22", "Masa Kontrak", "Jangka waktu yang antara lain terdiri dari jangka waktu pelaksanaan pekerjaan, jangka waktu pemeliharaan dan/atau masa garansi yang disepakati Para Pihak."),
            ("23", "Multi Winner", "Lebih dari satu Pelaksana Kontrak pada waktu bersamaan untuk penyediaan Barang/Jasa yang sama atau sejenis dalam jangka waktu tertentu."),
            ("24", "Pelaksana Kontrak", "Penyedia Barang/Jasa yang telah ditunjuk oleh PT PPN sebagai Pelaksana Pekerjaan dan telah menandatangani SP3MK/Kontrak untuk melaksanakan kewajibannya."),
            ("25", "Penyelenggara Pemilihan Penyedia (P3)", "Fungsi Procurement (Pengadaan) yang bertugas untuk menyelenggarakan Pemilihan Penyedia sesuai ketentuan dan batasan yang berlaku."),
            ("26", "Pemimpin Konsorsium (Lead Firm)", "Perusahaan yang ditunjuk oleh Anggota Konsorsium untuk mewakili Konsorsium dengan tugas dan tanggung jawab sebagaimana tertuang dalam Perjanjian Kerja Sama Konsorsium."),
            ("27", "Penawaran Tidak Lulus", "Penawaran yang dinilai tidak lengkap dan/atau tidak sesuai dan/atau tidak memenuhi persyaratan kualifikasi, administrasi, teknis, TKDN, HSSE, dan/atau komersial."),
            ("28", "Pertamina", "PT Pertamina Patra Niaga (PT PPN)."),
            ("29", "Peserta Pemilihan (Peserta)", "Penyedia Barang/Jasa yang berpartisipasi pada kegiatan Pemilihan Penyedia baik yang berstatus belum lulus maupun telah lulus Penilaian Kualifikasi."),
            ("30", "Produk Dalam Negeri", "Barang dan jasa yang diproduksi atau dikerjakan oleh perusahaan yang berinvestasi dan berproduksi di Indonesia, menggunakan tenaga kerja WNI, dan bahan baku dalam negeri."),
            ("31", "Produsen Dalam Negeri", "Badan usaha atau perseorangan yang didirikan berdasarkan hukum Indonesia dan menghasilkan Produk Dalam Negeri."),
            ("32", "Pimpinan Penyedia", "Direksi yang namanya tercantum pada Akta Pendirian/Anggaran Dasar, atau Kepala Cabang, atau pejabat yang berhak mewakili asosiasi/konsorsium."),
            ("33", "Preferensi Harga", "Nilai penyesuaian/normalisasi terhadap penawaran komersial yang disampaikan oleh Peserta untuk perhitungan HEA."),
            ("34", "Registrasi Penyedia (Registrasi)", "Kegiatan Penilaian Kualifikasi Umum dan persyaratan lainnya dalam rangka penerbitan Surat Keterangan Teregistrasi (SKT)."),
            ("35", "Sanksi", "Tindakan berupa pemberian poin sanksi finansial dan/atau sanksi administrasi berdasarkan jenis pelanggaran yang dilakukan oleh Penyedia/Peserta/Pelaksana Kontrak."),
            ("36", "Sertifikat TKDN", "Sertifikat yang diterbitkan oleh Kementerian Perindustrian kepada Produsen Dalam Negeri dengan masa berlaku 3 (tiga) tahun."),
            ("37", "Sistem Aplikasi Procurement Pertamina (SAPP)", "Sistem ERP dan/atau non-ERP di lingkungan PT PPN (SMART by GEP, Promise, Profed, i-Vendor, Docgen, dll)."),
            ("38", "SP3MK", "Surat Perintah Pelaksanaan Pekerjaan Mendahului Kontrak."),
            ("39", "SKUP Migas", "Surat Kemampuan Usaha Penunjang Minyak dan Gas Bumi yang diterbitkan oleh Ditjen Migas Kementerian ESDM."),
            ("40", "Tanda Tangan Elektronik (TTE)", "Informasi Elektronik yang dilekatkan atau terkait dengan Informasi Elektronik lainnya sebagai alat verifikasi dan autentikasi."),
            ("41", "Tingkat Komponen Dalam Negeri (TKDN)", "Besaran kandungan dalam negeri pada Barang, Jasa, serta gabungan Barang dan Jasa."),
            ("42", "TTE Tersertifikasi (TTE PSrE)", "TTE dengan Sertifikat Elektronik yang dikeluarkan oleh Penyelenggara Sertifikat Elektronik terakreditasi Kominfo."),
            ("43", "TTE Non-PSrE", "TTE yang tidak dikeluarkan oleh Penyelenggara Sertifikat Elektronik resmi diakui Kominfo."),
            ("44", "Update Data Penyedia", "Penyampaian pembaharuan dokumen yang telah kedaluwarsa oleh Penyedia Barang/Jasa DPT."),
            ("45", "Wakil Peserta", "Pimpinan tertinggi atau pejabat/pekerja yang memiliki kewenangan untuk mewakili dalam proses Pemilihan Penyedia.")
        ]
    },
    {
        "nomor": 2,
        "judul": "SYARAT PESERTA",
        "isi": [
            "1. Status Peserta yang dapat mengikuti Pemilihan Penyedia (Tunggal dan/atau Konsorsium) mengacu pada BAB I - IKPP (ketentuan khusus).",
            "2. Apabila Peserta berbentuk Konsorsium maka Penyedia Barang/Jasa dengan lingkup pekerjaan pendanaan (penyediaan modal) tidak diperkenankan menjadi Pemimpin Konsorsium (Lead Firm).",
            "3. Peserta telah dinyatakan lulus persyaratan penilaian kualifikasi umum dan khusus (apabila dipersyaratkan).",
            "4. Peserta telah memiliki kesesuaian kualifikasi umum dengan paket pengadaan yang akan dilaksanakan mengacu pada BAB I - IKPP.",
            "5. Peserta merupakan Daftar Penyedia Teregistrasi (DPT) dan memiliki Surat Keterangan Teregistrasi (SKT) yang masih berlaku.",
            "6. Peserta merupakan Penyedia Barang/Jasa dengan Kinerja golongan Hijau/Kuning."
        ]
    },
    {
        "nomor": 3,
        "judul": "PENJELASAN TENDER (PRE-BID MEETING)",
        "isi": [
            "1. Penjelasan dilaksanakan sebelum Peserta menyampaikan Dokumen Penawaran.",
            "2. Hanya Peserta yang mendaftar yang dapat mengikuti penjelasan.",
            "3. Penjelasan Tender dilaksanakan melalui Rapat Penjelasan (pre-bid meeting) dan/atau Penjelasan Lokasi Pekerjaan (site visit apabila diperlukan).",
            "4. Penjelasan tender dapat dilakukan dengan memanfaatkan platform digital melalui Video Conference (Microsoft Teams) dan/atau fitur discussion forum pada SAPP-SmartGEP.",
            "5. Berita Acara Penjelasan Tender termasuk dokumen adendum/amandemen (apabila ada) merupakan bagian yang tidak terpisahkan dari Dokumen Tender."
        ]
    },
    {
        "nomor": 4,
        "judul": "KETENTUAN DAN TATA CARA PENYAMPAIAN DOKUMEN PENAWARAN",
        "isi": [
            "1. Dokumen Penawaran dibuat di atas kertas beridentitas perusahaan (kop surat), bertanggal, ditandatangani menggunakan TTE PSrE dan dibubuhi e-meterai.",
            "2. Peserta dilarang mencantumkan persyaratan tambahan di luar ketentuan pada Dokumen Tender.",
            "3. Penawaran disampaikan secara elektronik melalui SAPP-SmartGEP sesuai batas waktu yang telah ditentukan.",
            "4. Rincian penawaran harga (BOQ) wajib disampaikan dalam format PDF bertandatangan digital dan file Microsoft Excel sebagai dokumen pendukung klarifikasi perhitungan."
        ]
    },
    {
        "nomor": 5,
        "judul": "PEMBUKAAN DOKUMEN PENAWARAN",
        "isi": [
            "1. Pembukaan Dokumen Penawaran dilaksanakan oleh P3, FPP, dan Fungsi Terkait pada waktu yang ditetapkan.",
            "2. Pembukaan dokumen penawaran pada prinsipnya tidak perlu dihadiri oleh Peserta, kecuali diatur secara khusus pada Bab I IKPP.",
            "3. Pembukaan dan evaluasi dilaksanakan apabila jumlah Peserta yang menyampaikan penawaran memenuhi kuorum minimum (sekurang-kurangnya 2 peserta untuk proses tender kompetisi)."
        ]
    },
    {
        "nomor": 6,
        "judul": "KETENTUAN EVALUASI DOKUMEN PENAWARAN",
        "isi": [
            "1. Pelaksanaan evaluasi Dokumen Penawaran terdiri dari: Evaluasi Administrasi, Evaluasi Teknis, Evaluasi HSSE Plan, Evaluasi TKDN, dan Evaluasi Komersial.",
            "2. Kriteria, metode, dan tata cara evaluasi harus ditetapkan di awal pada Dokumen Tender dan tidak dapat diubah setelah pembukaan dokumen penawaran.",
            "3. Klarifikasi penawaran dapat dilaksanakan melalui media discussion forum SAPP-SmartGEP tanpa memperbolehkan adanya post bidding (penambahan/pengubahan substansi penawaran)."
        ]
    },
    {
        "nomor": 7,
        "judul": "EVALUASI ADMINISTRASI",
        "isi": [
            "1. Evaluasi administrasi dilakukan dengan meneliti kelengkapan dan keabsahan dokumen penawaran administrasi menggunakan sistem gugur (non-scoring).",
            "2. Penawaran dinyatakan tidak lulus apabila terdapat sebagian atau seluruh persyaratan administrasi yang tidak dipenuhi."
        ]
    },
    {
        "nomor": 8,
        "judul": "EVALUASI TEKNIS",
        "isi": [
            "1. Evaluasi teknis dilaksanakan dengan metode Scoring atau Non-Scoring sebagaimana ditetapkan pada Bab I IKPP.",
            "2. Pada metode scoring, penawaran dinyatakan lulus apabila nilai evaluasi teknis memenuhi ambang batas (passing grade) yang ditentukan (minimal nilai 80 dari skala 100)."
        ]
    },
    {
        "nomor": 9,
        "judul": "EVALUASI HSSE PLAN",
        "isi": [
            "1. Evaluasi HSSE Plan mengacu pada STK Contractor Safety Management System (CSMS) Pertamina yang berlaku.",
            "2. Evaluasi dilakukan dengan metode scoring 8 (delapan) elemen CSMS dengan passing grade minimal skor 80 dari 100."
        ]
    },
    {
        "nomor": 10,
        "judul": "EVALUASI TKDN DAN PERHITUNGAN HEA",
        "isi": [
            "1. Evaluasi TKDN dilakukan terhadap komitmen persentase TKDN pada Formulir A3/A4/A5 dan sertifikat TKDN Kementerian Perindustrian.",
            "2. Perhitungan Harga Evaluasi Akhir (HEA) dilakukan untuk pengadaan yang memberikan preferensi harga:",
            "   a. HE TKDN Barang = (1 / (1 + KP Barang)) x KBB",
            "   b. HE TKDN Jasa = (1 / (1 + KP Jasa)) x KBJ",
            "   c. HEA = HE TKDN Barang + HE TKDN Jasa + KNB",
            "3. Penawaran dengan capaian komitmen TKDN di bawah batasan minimal yang dipersyaratkan dinyatakan gugur."
        ]
    },
    {
        "nomor": 11,
        "judul": "EVALUASI KOMERSIAL",
        "isi": [
            "1. Evaluasi komersial dilakukan terhadap Peserta yang telah lulus evaluasi administrasi, teknis, HSSE Plan, dan TKDN.",
            "2. Peserta dinyatakan gugur apabila penawaran komersial melebihi Nilai Total HPS/OE yang diumumkan (penawaran > HPS/OE)."
        ]
    },
    {
        "nomor": 12,
        "judul": "PENENTUAN PERINGKAT PESERTA",
        "isi": [
            "1. Peringkat disusun dari urutan terbaik berdasarkan metode evaluasi yang ditetapkan (Komersial Terendah, HEA Terbaik, atau Nilai Kombinasi Teknis & Komersial).",
            "2. Apabila terdapat kesamaan nilai, penawaran komersial terendah dan/atau komitmen TKDN tertinggi akan menduduki peringkat lebih tinggi."
        ]
    },
    {
        "nomor": 13,
        "judul": "METODE EVALUASI",
        "isi": [
            "1. Metode Komersial Terbaik/HEA Terbaik: Digunakan untuk pekerjaan berkategori standar atau teknis sederhana.",
            "2. Metode Nilai Kombinasi Teknis dan Komersial: Bobot teknis antara 60-80% dan komersial antara 20-40% dengan total bobot 100%."
        ]
    },
    {
        "nomor": 14,
        "judul": "PEMBERITAHUAN / PENGUMUMAN HASIL EVALUASI",
        "isi": [
            "Hasil evaluasi diumumkan kepada Peserta melalui SAPP-SmartGEP lengkap dengan penjelasan kelulusan maupun ketidaklulusan penawaran."
        ]
    },
    {
        "nomor": 15,
        "judul": "KETENTUAN KOREKSI ARITMATIKA DAN HARGA TIMPANG",
        "isi": [
            "1. Koreksi aritmatika dilakukan terhadap perkalian volume dan harga satuan tanpa mengubah harga satuan yang ditawarkan.",
            "2. Item harga satuan dinyatakan timpang apabila melebihi 110% dari harga satuan HPS/OE dan diklarifikasi oleh FPP."
        ]
    },
    {
        "nomor": 16,
        "judul": "KETENTUAN KOREKSI ARITMATIKA MEKANISME 1 SAMPAI 4",
        "isi": [
            "• Mekanisme 1: Untuk Kontrak Harga Satuan yang dievaluasi secara Total.",
            "• Mekanisme 2: Untuk Kontrak Harga Lumpsum.",
            "• Mekanisme 3: Untuk Kontrak Harga Satuan dievaluasi Itemize.",
            "• Mekanisme 4: Untuk Kontrak Harga Satuan Itemize dalam rangka Security of Supply."
        ]
    },
    {
        "nomor": 17,
        "judul": "NEGOSIASI",
        "isi": [
            "1. Negosiasi dilaksanakan melalui e-Reverse Auction (e-RA) pada platform SAPP-SmartGEP dan/atau Negosiasi Langsung.",
            "2. Hasil negosiasi komersial tidak boleh mengurangi persentase komitmen TKDN, ruang lingkup kerja, atau spesifikasi teknis."
        ]
    },
    {
        "nomor": 18,
        "judul": "PENGUMUMAN CALON PEMENANG",
        "isi": [
            "Pengumuman calon pemenang disampaikan melalui SAPP-SmartGEP setelah mendapat penetapan dari Pejabat Berwenang dan bersifat belum final sebelum masa sanggah berakhir."
        ]
    },
    {
        "nomor": 19,
        "judul": "KETENTUAN SANGGAHAN",
        "isi": [
            "1. Peserta yang tidak puas atas penetapan calon pemenang dapat mengajukan sanggahan tertulis disertai Jaminan Sanggahan sebesar 2 permil (maksimal Rp 100.000.000,00).",
            "2. Masa sanggah berlangsung selama 1 (satu) sampai 3 (tiga) hari kerja sejak pengumuman pemenang."
        ]
    },
    {
        "nomor": 20,
        "judul": "KETENTUAN JAMINAN PENGADAAN",
        "isi": [
            "1. Jaminan Pelaksanaan: Diberlakukan untuk kontrak > Rp 5 Miliar sebesar 5% dari nilai kontrak (atau 10% jika penawaran <= 80% HPS/OE).",
            "2. Jaminan Pemeliharaan: Sebesar minimal 5% dari nilai kontrak untuk pekerjaan yang mensyaratkan masa retensi/garansi.",
            "3. Jaminan Komitmen TKDN: Wajib diserahkan apabila disyaratkan dalam rangka menjamin kepatuhan pemenuhan TKDN."
        ]
    },
    {
        "nomor": 21,
        "judul": "PENUNJUKAN PEMENANG",
        "isi": [
            "Penunjukan Pemenang diterbitkan secara resmi melalui Surat Penunjukan Penyedia Barang/Jasa (SPPBJ) setelah masa sanggah terlewati atau sanggahan dinyatakan tidak benar."
        ]
    },
    {
        "nomor": 22,
        "judul": "PENERBITAN SP3MK",
        "isi": [
            "Surat Perintah Pelaksanaan Pekerjaan Mendahului Kontrak (SP3MK) dapat diterbitkan dalam kondisi darurat atau urgensi operasional mendesak sebelum kontrak formal ditandatangani."
        ]
    },
    {
        "nomor": 23,
        "judul": "KETENTUAN PENERBITAN KONTRAK",
        "isi": [
            "Kontrak ditandatangani selambat-lambatnya sesuai batas waktu yang ditentukan setelah penyerahan Jaminan Pelaksanaan yang sah."
        ]
    },
    {
        "nomor": 24,
        "judul": "PEMILIHAN PENYEDIA GAGAL",
        "isi": [
            "Tender dinyatakan gagal apabila: peserta kurang dari kuorum, tidak ada penawaran yang sah, seluruh penawaran di atas HPS/OE, atau terbukti terjadi tindak KKN."
        ]
    },
    {
        "nomor": 25,
        "judul": "PEMBATALAN PEMILIHAN PENYEDIA",
        "isi": [
            "Pembatalan proses tender dapat dilakukan karena perubahan rencana kerja, anggaran tidak tersedia, atau penetapan putusan pengadilan."
        ]
    },
    {
        "nomor": 26,
        "judul": "PEMILIHAN PENYEDIA MENGGUNAKAN SISTEM DIGITAL",
        "isi": [
            "Seluruh pertukaran dokumen, klarifikasi, submit penawaran, dan persetujuan Berita Acara dilakukan secara digital melalui sistem SAPP-SmartGEP."
        ]
    },
    {
        "nomor": 27,
        "judul": "PENILAIAN KINERJA PADA TAHAP PEMILIHAN PENYEDIA",
        "isi": [
            "1. Sistem poin reward & sanksi diberlakukan (+3 lulus tahap, -10 mundur tanpa alasan, -30 sanggahan palsu, -60 mundur setelah menang).",
            "2. Pelanggaran berat seperti manipulasi data, tindak pidana, wanprestasi, dan kecelakaan fatal langsung dikenakan Sanksi Merah atau Daftar Hitam (Blacklist)."
        ]
    },
    {
        "nomor": 28,
        "judul": "BUSINESS CONTINUITY MANAGEMENT SYSTEM (BCMS)",
        "isi": [
            "Penerapan prosedur mitigasi apabila terjadi gangguan sistem digital (ransomware / cyber incident) melalui kanal komunikasi darurat yang terverifikasi."
        ]
    },
    {
        "nomor": 29,
        "judul": "KEBIJAKAN ESG (ENVIRONMENTAL, SOCIAL & GOVERNANCE)",
        "isi": [
            "Penyedia diwajibkan mematuhi kaidah Green Procurement, perlindungan hak pekerja, keselamatan lingkungan, dan tata kelola bisnis yang transparan."
        ]
    },
    {
        "nomor": 30,
        "judul": "KETENTUAN LAIN-LAIN",
        "isi": [
            "1. Dokumen penawaran yang telah disampaikan menjadi milik Pertamina.",
            "2. Biaya penyiapan dokumen penawaran sepenuhnya menjadi tanggung jawab Peserta.",
            "3. Dokumen resmi wajib menggunakan Bahasa Indonesia."
        ]
    }
]


# ──────────────────────────────────────────────────────────────
# CSMS EVALUATION MATRIX DATA (Lampiran 3A - 8 Elemen)
# ──────────────────────────────────────────────────────────────

CSMS_MATRIX_DATA = [
    {
        "section": "I. PROSES 1: KEPEMIMPINAN DAN AKUNTABILITAS",
        "sub_total_bobot": 28,
        "items": [
            ("1", "Keterlibatan Manajemen Dalam Mempromosikan Budaya HSSE (Program Kampanye, HSSE Meeting, MWT/Inspeksi Manajemen, Intervensi Sub-Standard, Corporate Life Saving Rules Pertamina)"),
            ("2", "Penghargaan dan Sanksi Terkait Aspek HSSE (Sistem Reward bagi pekerja taat HSSE dan Sanksi tegas bagi pelanggaran HSSE)")
        ]
    },
    {
        "section": "II. PROSES 2: KEBIJAKAN DAN SASARAN",
        "sub_total_bobot": 33,
        "items": [
            ("1", "HSSE Policy dan Objective (Komitmen Pencegahan Kecelakaan, Kepatuhan Peraturan, Larangan Obat Terlarang & Senjata Tajam)"),
            ("2", "Target Kebijakan HSSE (Zero LTI, Zero Fatality, Target Jam Kerja Selamat)"),
            ("3", "HSSE Key Performance Indicators (KPI) (Lagging Indicator & Leading Indicator sesuai format Pertamina)")
        ]
    },
    {
        "section": "III. PROSES 3: ORGANISASI, TANGGUNG JAWAB, SUMBER DAYA, DAN DOKUMEN",
        "sub_total_bobot": 38,
        "items": [
            ("1", "Struktur Organisasi Pelaksanaan Pekerjaan (Job Description jelas & Posisi Personel Ahli K3 Migas/BNSP)"),
            ("2", "Pemeriksaan Kesehatan (Program Fit To Work, Medical Check Up / MCU berkala pekerja)"),
            ("3", "Asuransi Ketenagakerjaan (BPJS Ketenagakerjaan seluruh personel yang terlibat)"),
            ("4", "Pelatihan dan Kompetensi Pekerja (Induksi HSSE, Defensive Driving, Sertifikasi Teknis Khusus)"),
            ("5", "HSSE Communication (Toolbox Meeting, Safety Stand Down, HSSE Sign & Leaflet)")
        ]
    },
    {
        "section": "IV. PROSES 4: MANAJEMEN RISIKO",
        "sub_total_bobot": 57,
        "items": [
            ("1", "Work Site Hazard Analysis (HIRADC / Risk Register terperinci untuk seluruh tahapan pekerjaan)"),
            ("2", "Job Safety Analysis (JSA) / JHSEA lengkap dari pra-mobilisasi hingga demobilisasi"),
            ("3", "Rencana Mitigasi Bahaya, Penyediaan APD standar, Proteksi Kebakaran, Housekeeping, dan Hygiene Industri")
        ]
    },
    {
        "section": "V. PROSES 5: PERENCANAAN DAN PROSEDUR",
        "sub_total_bobot": 45,
        "items": [
            ("1", "Prosedur Kerja dan Standar Keselamatan (Standard Operating Procedure untuk pekerjaan berisiko tinggi)"),
            ("2", "Emergency Response Plan (Alur Tanggap Darurat, Tim First Aider / P3K, Ambulans, Kontak Darurat)"),
            ("3", "Prosedur Pengelolaan Pencegahan Penyakit Menular / Pandemi")
        ]
    },
    {
        "section": "VI. PROSES 6: IMPLEMENTASI DAN PENGENDALIAN OPERASIONAL",
        "sub_total_bobot": 46,
        "items": [
            ("1", "Management of Change (MOC) / Prosedur Pengelolaan Perubahan Lapangan"),
            ("2", "Kelaikan Peralatan Kerja (Sertifikat Inspeksi, SILO/SIA, Safety Data Sheet / SDS material kimia)"),
            ("3", "Sistem Izin Kerja Aman (SIKA / Permit to Work system)"),
            ("4", "Pengelolaan Subkontraktor (Seleksi & Evaluasi HSSE Subkontraktor)"),
            ("5", "Keselamatan Berkendara (Kelaikan Kendaraan, SIM & Pelatihan Defensive Driving)")
        ]
    },
    {
        "section": "VII. PROSES 7: JAMINAN: PEMANTAUAN, PENGUKURAN DAN AUDIT",
        "sub_total_bobot": 37,
        "items": [
            ("1", "Program Audit Internal HSSE berkala dan Jadwal MWT Lapangan"),
            ("2", "Prosedur Investigasi dan Pelaporan Insiden / Kecelakaan Kerja ke Pertamina")
        ]
    },
    {
        "section": "VIII. PROSES 8: TINJAUAN",
        "sub_total_bobot": 8,
        "items": [
            ("1", "Program Tinjauan / Review Manajemen terhadap implementasi HSSE Plan berkala")
        ]
    }
]


# ──────────────────────────────────────────────────────────────
# STANDARD BAGIAN B: RANCANGAN KONTRAK ARTICLES (Pasal 1 - 18)
# ──────────────────────────────────────────────────────────────

CONTRACT_ARTICLES = [
    {
        "pasal": 1,
        "judul": "DEFINISI DAN HIERARKI DOKUMEN",
        "isi": [
            "1. Dalam Perjanjian ini, kata-kata dan ungkapan-ungkapan memiliki arti yang sama sebagaimana ditentukan dalam Pedoman Pengadaan Barang/Jasa PT PERTAMINA PATRA NIAGA No. A03-001/PNG200000/2024-S9 Revisi ke-1.",
            "2. Dokumen-dokumen berikut merupakan satu kesatuan yang tidak terpisahkan dari Perjanjian ini, dan apabila terjadi pertentangan antara ketentuan dalam dokumen-dokumen tersebut, maka urutan kekuatan berlakunya (hierarki dokumen) adalah sebagai berikut:",
            "   a. Amandemen / Addendum Kontrak (jika ada);",
            "   b. Perjanjian Kontrak ini beserta seluruh Lampirannya;",
            "   c. Surat Perintah Pelaksanaan Pekerjaan Mendahului Kontrak (SP3MK) (jika ada);",
            "   d. Surat Penunjukan Pemenang Pengadaan (SPPBJ);",
            "   e. Berita Acara Klarifikasi dan Negosiasi Penawaran;",
            "   f. Berita Acara Rapat Penjelasan (Pre-Bid Meeting) beserta Addendum Dokumen Tender;",
            "   g. Syarat dan Ketentuan Khusus dan Umum IKPP;",
            "   h. Rencana Kerja dan Syarat-Syarat (RKS) / Kerangka Acuan Kerja (KAK);",
            "   i. Dokumen Penawaran Teknis dan Penawaran Harga dari PELAKSANA KONTRAK."
        ]
    },
    {
        "pasal": 2,
        "judul": "RUANG LINGKUP PEKERJAAN",
        "isi": [
            "1. PERTAMINA dengan ini menunjuk PELAKSANA KONTRAK dan PELAKSANA KONTRAK menerima penunjukan tersebut untuk melaksanakan seluruh pekerjaan sesuai spesifikasi teknis, standar mutu, dan ketentuan yang diatur dalam RKS serta Kontrak ini.",
            "2. Ruang lingkup pekerjaan utama mencakup penyediaan tenaga kerja profesional, peralatan, material, transportasi, pengujian, keselamatan kerja (HSSE), serta penyelesaian serah terima hasil pekerjaan sesuai jadwal.",
            "3. Rincian volume, jenis pekerjaan, dan spesifikasi material diatur secara detail dalam Lampiran Bill of Quantity (BoQ) dan Spesifikasi Teknis."
        ]
    },
    {
        "pasal": 3,
        "judul": "JANGKA WAKTU PELAKSANAAN DAN MASA KONTRAK",
        "isi": [
            "1. Jangka waktu pelaksanaan pekerjaan ditetapkan selama jangka waktu kalender yang disepakati terhitung sejak tanggal diterbitkannya Surat Perintah Mulai Kerja (SPMK) atau SP3MK.",
            "2. Masa Pemeliharaan (warranty/retensi) berlaku selama masa yang disyaratkan terhitung sejak tanggal penandatanganan Berita Acara Serah Terima Pertama (BAST-I).",
            "3. PELAKSANA KONTRAK wajib menyelesaikan seluruh cacat mutu dan kekurangan pekerjaan selama masa pemeliharaan atas beban biaya sendiri."
        ]
    },
    {
        "pasal": 4,
        "judul": "NILAI KONTRAK DAN TATA CARA PEMBAYARAN",
        "isi": [
            "1. Nilai total Kontrak ini adalah sebagaimana disepakati dalam Berita Acara Negosiasi Harga, belum termasuk Pajak Pertambahan Nilai (PPN).",
            "2. Pembayaran dilaksanakan secara bertahap berdasarkan pencapaian progres fisik (Milestone / Monthly Progress) yang telah diperiksa dan disetujui oleh Pengawas Pekerjaan PERTAMINA.",
            "3. Setiap penagihan wajib dilengkapi dengan: Surat Tagihan/Invoice bermeterai, Kuitansi, Faktur Pajak, Berita Acara Progres Fisik, Berita Acara Pemeriksaan Pekerjaan, dan dokumen pendukung lainnya sesuai SOP Keuangan PERTAMINA."
        ]
    },
    {
        "pasal": 5,
        "judul": "JAMINAN-JAMINAN (PELAKSANAAN & PEMELIHARAAN)",
        "isi": [
            "1. PELAKSANA KONTRAK wajib menyerahkan Jaminan Pelaksanaan sebesar 5% (atau 10% jika penawaran <= 80% HPS/OE) dari total Nilai Kontrak dalam bentuk Bank Garansi dari Bank BUMN/Bank Swasta Nasional terkemuka sebelum penandatanganan Kontrak.",
            "2. Jaminan Pelaksanaan berlaku sejak tanggal penandatanganan Kontrak sampai dengan sekurang-kurangnya 30 hari kalender setelah penandatanganan BAST-I.",
            "3. Untuk masa pemeliharaan, PELAKSANA KONTRAK wajib menyerahkan Jaminan Pemeliharaan sebesar minimal 5% dari Nilai Kontrak atau diberlakukan pemotongan retensi pembayaran sebesar 5% hingga BAST-II ditandatangani."
        ]
    },
    {
        "pasal": 6,
        "judul": "HAK DAN KEWAJIBAN PERTAMINA",
        "isi": [
            "1. PERTAMINA berhak melakukan pengawasan, inspeksi, evaluasi, dan pengujian terhadap seluruh tahapan pelaksanaan pekerjaan serta menolak hasil pekerjaan yang tidak memenuhi spesifikasi teknis.",
            "2. PERTAMINA berkewajiban melakukan pembayaran atas prestasi pekerjaan yang telah diselesaikan dan diterima dengan baik sesuai syarat dan tata cara pembayaran dalam Kontrak ini."
        ]
    },
    {
        "pasal": 7,
        "judul": "HAK DAN KEWAJIBAN PELAKSANA KONTRAK",
        "isi": [
            "1. PELAKSANA KONTRAK berhak menerima pembayaran sesuai termin dan progres fisik yang telah disetujui PERTAMINA.",
            "2. PELAKSANA KONTRAK berkewajiban melaksanakan dan menyelesaikan seluruh pekerjaan secara cermat, tepat waktu, sesuai standar keteknikan yang baik, mematuhi seluruh peraturan K3L, serta menyediakan tenaga ahli yang kompeten."
        ]
    },
    {
        "pasal": 8,
        "judul": "PENGAWASAN DAN PENGENDALIAN PEKERJAAN",
        "isi": [
            "1. Pengawasan pelaksanaan pekerjaan di lapangan dilaksanakan oleh Pengawas Pekerjaan / Direksi Pekerjaan yang ditunjuk secara resmi oleh PERTAMINA.",
            "2. Pengawas Pekerjaan berhak memberikan instruksi tertulis, menghentikan pekerjaan sementara apabila terjadi pelanggaran HSSE kritis, serta melakukan verifikasi mutu dan volume pekerjaan."
        ]
    },
    {
        "pasal": 9,
        "judul": "ASPEK KESELAMATAN, KESEHATAN KERJA DAN LINDUNGAN LINGKUNGAN (HSSE)",
        "isi": [
            "1. PELAKSANA KONTRAK wajib mematuhi seluruh ketentuan Contractor Safety Management System (CSMS), Sistem Izin Kerja Aman (SIKA), dan Corporate Life Saving Rules (CLSR) Pertamina.",
            "2. Segala dampak kecelakaan kerja, penyakit akibat kerja, atau pencemaran lingkungan yang timbul akibat kelalaian pelaksanaan pekerjaan menjadi tanggung jawab penuh PELAKSANA KONTRAK.",
            "3. Pelanggaran berat terhadap kaidah HSSE dapat berakibat penghentian pekerjaan, sanksi finansial, hingga pemutusan kontrak secara sepihak."
        ]
    },
    {
        "pasal": 10,
        "judul": "KOMITMEN DAN SANKSI TINGKAT KOMPONEN DALAM NEGERI (TKDN)",
        "isi": [
            "1. PELAKSANA KONTRAK wajib merealisasikan komitmen persentase TKDN yang telah dinyatakan dalam dokumen penawaran dan Form A3/A4/A5.",
            "2. Realisasi capaian TKDN akan diverifikasi oleh Surveyor Independen atau Tim Verifikasi TKDN yang ditunjuk PERTAMINA pada akhir masa kontrak.",
            "3. Apabila realisasi capaian TKDN < nilai komitmen yang disepakati, PELAKSANA KONTRAK dikenakan sanksi finansial (denda) pemotongan pembayaran dan/atau pencairan Jaminan Komitmen TKDN sesuai ketentuan STK P3DN yang berlaku."
        ]
    },
    {
        "pasal": 11,
        "judul": "DENDA KETERLAMBATAN DAN SANKSI",
        "isi": [
            "1. Apabila PELAKSANA KONTRAK terlambat menyelesaikan pekerjaan sesuai jangka waktu yang ditentukan, dikenakan denda keterlambatan sebesar 1‰ (satu permil) untuk setiap hari keterlambatan, maksimal sebesar 5% (lima persen) dari Nilai Kontrak.",
            "2. Apabila akumulasi denda telah mencapai batas maksimal 5%, PERTAMINA berhak memutuskan Kontrak secara sepihak dan mencairkan Jaminan Pelaksanaan."
        ]
    },
    {
        "pasal": 12,
        "judul": "KEADAAN KAHAR (FORCE MAJEURE)",
        "isi": [
            "1. Yang dimaksud Keadaan Kahar adalah peristiwa di luar kemampuan Para Pihak yang wajar, meliputi: bencana alam, gempa bumi, banjir bandang, perang, kerusuhan massal, kebakaran hebat, dan kebijakan pemerintah yang secara langsung menghambat pelaksanaan kontrak.",
            "2. Pihak yang terdampak wajib memberitahukan secara tertulis kepada pihak lainnya selambat-lambatnya dalam waktu 7 (tujuh) hari kalender sejak terjadinya peristiwa kahar disertai bukti dari instansi yang berwenang."
        ]
    },
    {
        "pasal": 13,
        "judul": "PEMUTUSAN PERJANJIAN (TERMINATION)",
        "isi": [
            "1. PERTAMINA berhak memutuskan Perjanjian ini secara sepihak dengan pemberitahuan tertulis tanpa perlu menunggu putusan pengadilan (mengesampingkan Pasal 1266 dan 1267 KUHPerdata) dalam hal: PELAKSANA KONTRAK bangkrut/pailit, wanprestasi, denda mencapai nilai maksimum, atau melakukan pelanggaran integritas/KKN.",
            "2. Dalam hal terjadi pemutusan kontrak sepihak akibat kesalahan PELAKSANA KONTRAK, Jaminan Pelaksanaan dicairkan untuk PERTAMINA dan Penyedia dikenakan Sanksi Kategori Merah atau Hitam."
        ]
    },
    {
        "pasal": 14,
        "judul": "KERAHASIAAN INFORMASI DAN HAK KEKAYAAN INTELEKTUAL",
        "isi": [
            "1. Seluruh informasi teknis, gambar desain, data operasi, dan dokumen kontrak bersifat rahasia dan tidak boleh disebarluaskan kepada pihak ketiga tanpa izin tertulis dari PERTAMINA.",
            "2. Seluruh hasil karya, gambar rekayasa, dan data hasil pekerjaan menjadi hak milik eksklusif PERTAMINA."
        ]
    },
    {
        "pasal": 15,
        "judul": "KEPATUHAN HUKUM DAN ANTI PENYUAPAN (ABC / FCPA)",
        "isi": [
            "1. PELAKSANA KONTRAK wajib mematuhi seluruh perundang-undangan pencegahan tindak pidana korupsi, anti-suap (Anti-Bribery and Corruption), dan etika bisnis yang sehat.",
            "2. PELAKSANA KONTRAK dilarang memberikan hadiah, fasilitas, komisi, atau gratifikasi dalam bentuk apapun kepada pejabat atau pekerja PERTAMINA."
        ]
    },
    {
        "pasal": 16,
        "judul": "PENYELESAIAN PERSELISIHAN",
        "isi": [
            "1. Setiap perselisihan yang timbul dari penafsiran atau pelaksanaan Perjanjian ini diutamakan diselesaikan secara musyawarah untuk mufakat dalam waktu 30 (tiga puluh) hari kalender.",
            "2. Apabila musyawarah tidak mencapai mufakat, Para Pihak sepakat untuk menyelesaikan perselisihan melalui Badan Arbitrase Nasional Indonesia (BANI) atau Pengadilan Negeri yang disepakati bersama."
        ]
    },
    {
        "pasal": 17,
        "judul": "AMANDEMEN DAN ADDENDUM KONTRAK",
        "isi": [
            "Setiap perubahan terhadap ruang lingkup, nilai kontrak, atau jangka waktu pelaksanaan pekerjaan hanya sah apabila dituangkan dalam Amandemen atau Addendum Kontrak tertulis yang ditandatangani oleh Para Pihak."
        ]
    },
    {
        "pasal": 18,
        "judul": "BAHASA, HUKUM YANG BERLAKU DAN PENUTUP",
        "isi": [
            "1. Perjanjian ini dibuat, ditafsirkan, dan tunduk pada hukum Negara Republik Indonesia.",
            "2. Bahasa resmi yang digunakan dalam Perjanjian ini adalah Bahasa Indonesia.",
            "3. Demikian Perjanjian ini ditandatangani oleh Para Pihak dalam rangkap 2 (dua) asli bermeterai cukup dan memiliki kekuatan hukum yang sama."
        ]
    }
]

