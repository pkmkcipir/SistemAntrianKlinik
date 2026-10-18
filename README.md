# Sistem Antrian Klinik

Aplikasi desktop Windows 11 untuk antrian klinik, lengkap dengan layar antrian untuk monitor ruang tunggu,
video edukasi, data pasien, serta laporan keuangan dan obat mingguan/bulanan.

Data klinik bawaan: **Klinik Bidan Dewi Anjani**, Kavling Tanah Harapan No.D63, RT.011/RW.006, Pejuang,
Medan Satria, Bekasi, West Java 17131, telp/WA 085178266540. Semuanya bisa diubah di menu **Pengaturan**.

`@copyright iman.mn_` tampil di footer aplikasi, footer layar antrian, serta laporan Excel dan PDF.

## Fitur

- **Antrian**: ambil nomor per layanan (A001, B001, ...), lalu panggil berikutnya, panggil ulang, lewati, selesai,
  atau batalkan. Pasien boleh dikaitkan ke data pasien atau dibiarkan kosong untuk pasien baru.
- **Layar antrian** untuk monitor ruang tunggu (otomatis penuh di monitor kedua): nomor yang sedang dipanggil,
  daftar antrian per layanan, video edukasi, teks berjalan, jam dan tanggal. Ada bunyi ting-tung dan suara
  panggilan; volume video mengecil sendiri saat ada panggilan.
- **Video Edukasi**: tambah video dari menu, atur urutan, centang untuk menayangkan. Video diputar berurutan
  dan berulang selama pasien menunggu. File disalin ke folder data aplikasi.
- **Pasien**: simpan, cari, ubah, hapus; nomor RM otomatis (RM-000001, ...).
- **Keuangan**: catat pemasukan dan pengeluaran.
- **Obat**: daftar obat, obat masuk, obat keluar (bisa otomatis tercatat ke keuangan), koreksi stok, status stok
  menipis/habis.
- **Laporan** mingguan (Senin sampai Minggu) dan bulanan untuk **keuangan** dan **obat**, bisa diekspor ke
  **Excel** dan **PDF**.
- **Backup dan pulihkan** data dari menu Pengaturan.

## Build EXE dan installer di GitHub

1. Buat repository baru di GitHub, lalu unggah **seluruh isi folder ini** (termasuk folder `.github`).
   Paling aman lewat `git push` atau GitHub Desktop agar folder `.github` ikut terunggah.
2. Buka tab **Actions** > **Build Windows (EXE + Installer)** > **Run workflow**.
   Build juga jalan otomatis setiap push ke branch `main`.
3. Setelah selesai (beberapa menit), unduh dari bagian **Artifacts**:
   - `SistemAntrianKlinik-Setup`: installer `SistemAntrianKlinik-Setup-x.y.z.exe` untuk Windows 11.
   - `SistemAntrianKlinik-Portable`: versi zip tanpa instalasi.
4. Untuk rilis resmi, beri tag versi, misalnya `git tag v1.0.0 && git push origin v1.0.0`.
   Installer otomatis terlampir di halaman **Releases**, dan nomor versi aplikasi ikut menyesuaikan.

Saat pertama dijalankan, Windows SmartScreen mungkin menampilkan peringatan karena aplikasi belum
ditandatangani. Klik **More info** > **Run anyway**.

## Cara pakai singkat

1. Pasang installer, jalankan aplikasi, buka **Pengaturan** untuk memeriksa identitas klinik, nama layanan
   (poli), dan ruang.
2. Hubungkan monitor ruang tunggu sebagai monitor kedua. Layar antrian terbuka otomatis; atau klik
   **Buka layar antrian** di kanan atas. Tekan **F11** untuk penuh/jendela dan **Esc** untuk keluar dari penuh.
3. Buka **Video Edukasi** > **Tambah video** (format paling aman MP4 H.264 + AAC).
4. Di **Antrian**, klik layanan untuk mengambil nomor, lalu **Panggil berikutnya** saat pasien dilayani.

Suara panggilan memakai suara Bahasa Indonesia bawaan Windows. Jika belum ada, pasang lewat
Pengaturan Windows > Waktu & bahasa > Ucapan > Tambah suara > Indonesia, lalu coba **Tes suara** di Pengaturan.
Tanpa suara Indonesia, hanya bunyi ting-tung yang diputar.

## Data

Semua data tersimpan di `%APPDATA%\SistemAntrianKlinik` (database `klinik.db` dan folder `videos`).
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
  display.py               layar antrian, video, bunyi/suara panggilan
  pages_antrian.py         halaman Antrian
  pages_data.py            halaman Pasien, Keuangan, Obat
  pages_lain.py            halaman Laporan, Video Edukasi, Pengaturan
  reports.py               laporan mingguan/bulanan + ekspor Excel/PDF
  main_window.py           jendela utama
assets/                    ikon aplikasi
installer.iss              skrip installer (Inno Setup)
.github/workflows/         build otomatis di GitHub Actions
```
