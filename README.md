# Sistem Antrian Klinik

Aplikasi desktop Windows 11 untuk antrian klinik: layar antrian untuk monitor ruang tunggu **dan TV lewat URL
jaringan**, video edukasi, **suara panggilan perempuan Bahasa Indonesia**, data pasien, serta laporan keuangan
dan obat mingguan/bulanan.

Data klinik bawaan: **Klinik Bidan Dewi Anjani**, Kavling Tanah Harapan No.D63, RT.011/RW.006, Pejuang,
Medan Satria, Bekasi, West Java 17131, telp/WA 085178266540. Semuanya bisa diubah di menu **Pengaturan**.

`@copyright iman.mn_` tampil di footer aplikasi, footer layar antrian (PC dan TV), serta laporan Excel dan PDF.

## Fitur

- **Antrian**: ambil nomor per layanan (A001, B001, ...), lalu panggil berikutnya, panggil ulang, lewati, selesai,
  batalkan, atau hapus (satu nomor, beberapa nomor dengan Ctrl/Shift + klik atau tombol Delete, maupun semua
  nomor hari ini untuk satu layanan). Pasien boleh dikaitkan ke data pasien atau dibiarkan kosong.
- **Layar antrian di PC** (otomatis penuh di monitor kedua): nomor yang sedang dipanggil, antrian per layanan,
  video edukasi, teks berjalan, jam dan tanggal.
- **Layar antrian di TV lewat URL**: buka alamat seperti `http://192.168.1.20:8080` di browser TV yang satu
  jaringan dengan PC. Tampilannya sama, lengkap dengan video dan suara panggilan. Lihat bagian di bawah.
- **Cetak tiket nomor antrian**: saat pasien mengambil nomor, tiket otomatis dicetak untuk diberikan ke pasien
  sebelum dipanggil. Ukuran kertas thermal 58 mm atau 80 mm (tinggi menyesuaikan isi), A6, atau ukuran kustom.
- **Tema layar antrian**: 6 pilihan warna (Hijau Klinik, Biru Medis, Pink Ibu dan Anak, Ungu Lavender, Gelap,
  Oranye Hangat) di **Pengaturan > Tema Layar**, termasuk warna panel saat nomor dipanggil (berkedip). Berlaku
  di layar PC dan layar TV.
- **Suara panggilan perempuan Indonesia** (Microsoft Gadis): ting-tung lalu ucapan, misalnya
  "Nomor antrian, A, tiga belas. Silakan menuju, Pemeriksaan Umum, Ruang Periksa 1."
- **Video Edukasi**: tambah video dari menu, atur urutan, centang untuk menayangkan. Video diputar berurutan
  dan berulang selama pasien menunggu, dan volumenya mengecil sendiri saat ada panggilan.
- **Pasien**, **Keuangan**, dan **Obat** (obat masuk, keluar, koreksi stok, status stok menipis/habis).
- **Laporan** mingguan (Senin sampai Minggu) dan bulanan untuk **keuangan** dan **obat**, bisa diekspor ke
  **Excel** dan **PDF**.
- **Backup dan pulihkan** data dari menu Pengaturan.

## Layar antrian di TV lewat URL

1. Pastikan PC yang menjalankan aplikasi dan TV tersambung ke **WiFi/LAN yang sama**.
2. Buka **Pengaturan > Suara dan TV**. URL tampil di sana (dan di kanan atas aplikasi), misalnya
   `http://192.168.1.20:8080`. Klik **Salin URL** bila perlu.
3. Ketik URL itu di browser TV, lalu jadikan favorit atau halaman awal.
4. Tekan **OK** (atau klik) sekali di TV untuk mengaktifkan suara dan **layar penuh** sekaligus. Browser
   mewajibkan satu sentuhan sebelum boleh membunyikan suara dan masuk layar penuh. Setelah itu, tombol **F**,
   klik dua kali, atau tombol di sudut kanan bawah (muncul saat remote/mouse digerakkan) untuk keluar dan masuk
   layar penuh lagi. Tombol **Esc** juga keluar dari layar penuh.
5. Jika Windows meminta izin firewall saat aplikasi pertama dibuka, pilih **Allow access** untuk
   **Private networks**. Jika terlewat: Windows Security > Firewall & network protection > Allow an app through
   firewall, lalu centang SistemAntrianKlinik pada Private. Jaringan Windows juga harus bertipe Private.

Catatan:
- PC aplikasi harus menyala selama TV dipakai. Layar TV hanya menampilkan nomor antrian, nama layanan, dan
  video, **tanpa data pasien**.
- Video untuk TV paling aman berformat MP4 (H.264 + AAC). Format lain mungkin tidak bisa diputar browser TV.
- Jika PC dan TV sama-sama bersuara, matikan salah satunya di Pengaturan (Putar suara di PC / di TV).
- Port bawaan 8080 bisa diubah di Pengaturan. Bila port dipakai program lain, aplikasi otomatis memakai port
  berikutnya dan menampilkan URL yang benar.
- Halaman TV memakai HTML sederhana, jadi kebanyakan TV pintar dan Chromecast/Android TV bisa membukanya.
  Jika browser TV terlalu lama, pakai stick (Chromecast/Fire TV), mini PC, atau kabel HDMI dari PC.

## Cetak tiket nomor antrian

Tiket berisi nama klinik, nomor antrian yang besar, layanan dan ruang, tanggal dan jam, jumlah antrian di depan,
nama pasien (jika ada), serta teks bawah.

1. Pasang printer dan drivernya di Windows (printer thermal seperti POS-58, XP-58, atau Epson TM biasanya
   memakai driver bawaan pabrik).
2. Buka **Pengaturan > Cetak Tiket**, pilih printer dan ukuran kertas (**Thermal 58 mm**, **Thermal 80 mm**,
   A6, atau Kustom). Tinggi tiket otomatis menyesuaikan isi, jadi kertas tidak terbuang.
3. Klik **Pratinjau tiket** untuk melihat hasilnya, lalu **Cetak percobaan**, lalu **Simpan pengaturan**.
4. Selesai. Setiap pasien mengambil nomor (di halaman **Antrian** atau lewat **Daftarkan ke antrian** di halaman
   Pasien), tiket langsung tercetak. **Cetak ulang tiket terakhir** dan **Cetak tiket nomor terpilih** tersedia
   untuk mencetak ulang.

Catatan:
- Opsi yang bisa dipilih: cetak otomatis (ya/tidak), nama pasien, alamat klinik, teks bawah, dan jumlah salinan.
- Jika tiket gagal dicetak, muncul peringatan berisi nomornya supaya bisa diberikan ke pasien secara manual.
- Jika kertas thermal keluar terlalu panjang atau terpotong, buka Printing Preferences printer di Windows dan
  pilih ukuran roll sesuai lebar kertas (58 atau 80 mm).
- **Simpan contoh ke PDF** memudahkan memeriksa tata letak tanpa printer.

### Jika video tidak tampil di TV

Peramban/TV hanya bisa memutar format tertentu, sedangkan layar antrian di PC bisa memutar lebih banyak.

- Buka **Video Edukasi**: kolom **Layar TV (web)** menjelaskan apakah tiap video siap diputar di TV
  (misalnya "Siap TV: H.264 High + AAC-LC") atau tidak (misalnya H.265, AVI, MKV, H.264 10-bit).
- Format paling aman: **MP4 (H.264 + AAC)**. Untuk mengubahnya pakai HandBrake (preset Fast 1080p30, centang
  "Web optimized" supaya video cepat mulai).
- Video yang tidak didukung otomatis dilewati di TV, dan catatannya tampil sebentar di atas video.
- Untuk melihat info teknis di TV, tambahkan `?debug=1` di ujung URL, misalnya `http://192.168.1.20:8080/?debug=1`.

## Suara panggilan

Suara memakai **Microsoft Gadis** (perempuan, Bahasa Indonesia) lewat paket `edge-tts`.

- Perlu internet **sekali** untuk setiap kalimat baru. Hasilnya disimpan di
  `%APPDATA%\SistemAntrianKlinik\suara`, jadi panggilan berikutnya langsung diputar tanpa internet.
- Agar siap offline, klik **Pengaturan > Suara dan TV > Unduh suara nomor 1-100** (butuh beberapa menit).
  Ulangi bila nama layanan atau ruang diubah.
- Jika internet putus dan kalimat belum tersimpan, yang diputar hanya ting-tung (atau suara Indonesia bawaan
  Windows bila terpasang).
- `edge-tts` memakai layanan Microsoft Edge yang tidak resmi. Jika suatu saat berhenti berfungsi, build ulang
  di GitHub akan otomatis memakai `edge-tts` versi terbaru.
- Tombol **Tes suara** di Pengaturan menampilkan pesan jelas bila suara tidak bisa diambil.

## Build EXE dan installer di GitHub

1. Buat repository baru di GitHub, lalu unggah **seluruh isi folder ini** (termasuk folder `.github`).
   Paling aman lewat `git push` atau GitHub Desktop agar folder `.github` ikut terunggah.
2. Buka tab **Actions** > **Build Windows (EXE + Installer)** > **Run workflow**.
   Build juga jalan otomatis setiap push ke branch `main`.
3. Setelah selesai (beberapa menit), unduh dari bagian **Artifacts**:
   - `SistemAntrianKlinik-Setup`: installer `SistemAntrianKlinik-Setup-x.y.z.exe` untuk Windows 11.
   - `SistemAntrianKlinik-Portable`: versi zip tanpa instalasi.
4. Untuk rilis resmi, beri tag versi, misalnya `git tag v1.4.0 && git push origin v1.4.0`.
   Installer otomatis terlampir di halaman **Releases**, dan nomor versi aplikasi ikut menyesuaikan.

Memasang versi baru di atas versi lama **tidak menghapus data** (database, video, dan suara tersimpan di
`%APPDATA%`). Pada log langkah *Smoke test* di GitHub Actions tertulis apakah layar TV dan suara online
berfungsi pada hasil build.

Saat pertama dijalankan, Windows SmartScreen mungkin menampilkan peringatan karena aplikasi belum
ditandatangani. Klik **More info** > **Run anyway**. Jika installer dijalankan sebagai administrator (pilih
"semua pengguna"), aturan Windows Firewall untuk layar TV ditambahkan otomatis.

## Cara pakai singkat

1. Pasang installer, jalankan aplikasi, buka **Pengaturan** untuk memeriksa identitas klinik, nama layanan
   (poli), dan ruang.
2. Monitor ruang tunggu sebagai monitor kedua: layar antrian terbuka otomatis, atau klik **Buka layar antrian**.
   Tekan **F11** untuk penuh/jendela dan **Esc** untuk keluar dari penuh. Atau pakai TV lewat URL (di atas).
3. Buka **Video Edukasi** > **Tambah video** (format paling aman MP4 H.264 + AAC).
4. Di **Antrian**, klik layanan untuk mengambil nomor, lalu **Panggil berikutnya** saat pasien dilayani.

## Data

Semua data tersimpan di `%APPDATA%\SistemAntrianKlinik` (database `klinik.db`, folder `videos`, folder `suara`).
Tombol **Backup data** di Pengaturan menyalin database ke lokasi pilihan Anda. Lakukan secara berkala.

## Menjalankan dari source (opsional)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Struktur proyek

```
main.py                    titik masuk aplikasi
klinik/
  config.py                konstanta, folder data, format tanggal/rupiah
  db.py                    database SQLite
  widgets.py               tema, dialog form, helper tabel
  display.py               layar antrian di PC, video
  audio.py                 ting-tung dan pemutaran suara panggilan di PC
  voice.py                 suara perempuan Indonesia (edge-tts) + cache
  webserver.py             server layar TV lewat jaringan lokal
  pages_antrian.py         halaman Antrian
  pages_data.py            halaman Pasien, Keuangan, Obat
  pages_lain.py            halaman Laporan dan Video Edukasi
  pages_pengaturan.py      halaman Pengaturan (termasuk Tema Layar)
  themes.py                tema warna layar antrian (PC dan TV)
  ticket.py                tiket nomor antrian (tata letak dan cetak)
  mediainfo.py             pembaca info video (kodek) untuk cek kecocokan TV
  reports.py               laporan mingguan/bulanan + ekspor Excel/PDF
  main_window.py           jendela utama
assets/                    ikon aplikasi dan halaman TV (tv.html)
installer.iss              skrip installer (Inno Setup)
.github/workflows/         build otomatis di GitHub Actions
```
