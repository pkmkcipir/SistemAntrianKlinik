"""Halaman Pengaturan: identitas klinik, suara dan TV, layanan (poli), data dan backup."""
import sqlite3
from datetime import date

from PySide6.QtCore import QRectF, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QGuiApplication, QPainter, QPixmap, QTextOption
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPlainTextEdit, QProgressDialog, QScrollArea, QSlider, QSpinBox, QTabWidget,
                               QVBoxLayout, QWidget)

from . import ticket
from .config import APP_VERSION, COPYRIGHT, data_dir
from .pages_lain import _folder_dokumen
from .themes import TEMA, get_tema
from .voice import kalimat_panggilan
from .widgets import ask, ask_form, button, fill_table, info, label, make_table, selected_id, warn


class TemaPreview(QWidget):
    """Miniatur layar antrian dengan warna tema; panel nomor berkedip bergantian seperti saat nomor dipanggil."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(600, 338)
        self.t, self.flash = get_tema(None), False
        timer = QTimer(self)
        timer.timeout.connect(self._ganti)
        timer.start(900)

    def set_tema(self, t):
        self.t = t
        self.update()

    def _ganti(self):
        self.flash = not self.flash
        if self.isVisible():
            self.update()

    def paintEvent(self, _e):
        t, w, h = self.t, self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        def teks(x, y, lebar, tinggi, text, warna, px, tebal=False, rata=Qt.AlignmentFlag.AlignLeft):
            f = QFont(self.font())
            f.setPixelSize(px)
            f.setBold(tebal)
            p.setFont(f)
            p.setPen(QColor(warna))
            opsi = QTextOption(rata | Qt.AlignmentFlag.AlignVCenter)
            opsi.setWrapMode(QTextOption.WrapMode.NoWrap)
            p.drawText(QRectF(x, y, lebar, tinggi), text, opsi)

        p.fillRect(0, 0, w, h, QColor(t["bg"]))
        hh = int(h * 0.17)
        p.fillRect(0, 0, w, hh, QColor(t["header"]))
        teks(16, 0, w * 0.6, hh, "Klinik Bidan Dewi Anjani", t["header_fg"], int(hh * 0.42), True)
        teks(0, 0, w - 16, hh, "14:32:05", t["header_fg"], int(hh * 0.4), True, Qt.AlignmentFlag.AlignRight)
        m = 14
        vy, vh, vw = hh + m, h - hh - 2 * m - int(h * 0.13), int(w * 0.56)
        p.fillRect(m, vy, vw, vh, QColor(t["video_bg"]))
        teks(m, vy, vw, vh, "Video edukasi", t["video_fg"], 16, False, Qt.AlignmentFlag.AlignHCenter)
        cx = m + vw + m
        cw, ch = w - cx - m, int(vh * 0.56)
        bg, fg = (t["flash"], t["flash_fg"]) if self.flash else (t["called"], t["called_fg"])
        p.fillRect(cx, vy, cw, ch, QColor(bg))
        teks(cx + 10, vy + 4, cw - 20, 22, "Sedang dipanggil", fg, 13, True)
        teks(cx + 10, vy + 24, cw - 20, ch - 60, "A013", fg, int(ch * 0.42), True)
        teks(cx + 10, vy + ch - 34, cw - 20, 30, "Pemeriksaan Umum", fg, 15, True)
        by = vy + ch + 8
        bh = vy + vh - by
        p.fillRect(cx, by, cw, bh, QColor(t["board"]))
        rh = bh // 3
        for i, (nama, kode) in enumerate((("Pemeriksaan Umum", "A013"), ("KIA Ibu dan Anak", "B004"), ("Apotek", "D002"))):
            y = by + i * rh
            p.fillRect(cx, y + rh - 1, cw, 1, QColor(t["row_line"]))
            teks(cx + 10, y, cw - 70, rh, nama, t["row_name"], 12, True)
            teks(cx, y, cw - 10, rh, kode, t["row_num"], 20, True, Qt.AlignmentFlag.AlignRight)
        fy = h - int(h * 0.13)
        p.fillRect(0, fy, w, h - fy, QColor(t["footer"]))
        teks(16, fy, w - 32, (h - fy) * 0.6, "Selamat datang. Mohon menunggu panggilan sesuai nomor antrian Anda.",
             t["footer_fg"], 12, True)
        teks(0, fy + (h - fy) * 0.55, w, (h - fy) * 0.45, "@copyright iman.mn_", t["mark"], 11, False,
             Qt.AlignmentFlag.AlignHCenter)
        p.end()


class SettingsPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx, self.db = ctx, ctx.db
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 8)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_klinik(), "Klinik")
        self.tabs.addTab(self._tab_tema(), "Tema Layar")
        self.tabs.addTab(self._tab_suara_tv(), "Suara dan TV")
        self.tabs.addTab(self._tab_cetak(), "Cetak Tiket")
        self.tabs.addTab(self._tab_layanan(), "Layanan")
        self.tabs.addTab(self._tab_data(), "Data")
        lay.addWidget(self.tabs, 1)
        row = QHBoxLayout()
        row.addWidget(button("Simpan pengaturan", slot=self.simpan))
        row.addStretch()
        lay.addLayout(row)

    # ---- susunan tab -------------------------------------------------------------------
    @staticmethod
    def _tab():
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(22, 18, 22, 16)
        lay.setSpacing(8)
        return w, lay

    def _tab_klinik(self):
        w, lay = self._tab()
        self.ed_nama, self.ed_tel = QLineEdit(), QLineEdit()
        self.ed_alamat, self.ed_run = QPlainTextEdit(), QPlainTextEdit()
        self.ed_alamat.setFixedHeight(64)
        self.ed_run.setFixedHeight(84)
        self.sl_vol = QSlider(Qt.Orientation.Horizontal)
        self.sl_vol.setRange(0, 100)
        self.lbl_vol = label("")
        self.sl_vol.valueChanged.connect(lambda v: self.lbl_vol.setText(f"{v}%"))
        vol = QHBoxLayout()
        vol.addWidget(self.sl_vol, 1)
        vol.addWidget(self.lbl_vol)
        self.cb_mon = QComboBox()
        self.chk_auto = QCheckBox("Buka layar antrian otomatis saat aplikasi dimulai (jika ada monitor kedua)")
        holder = QWidget()
        holder.setMaximumWidth(780)
        form = QFormLayout(holder)
        form.setContentsMargins(0, 0, 0, 0)
        form.setVerticalSpacing(10)
        for teks, x in (("Nama klinik", self.ed_nama), ("Alamat", self.ed_alamat), ("Telepon / WhatsApp", self.ed_tel),
                        ("Teks berjalan", self.ed_run), ("Volume video", vol),
                        ("Monitor layar antrian PC", self.cb_mon)):
            form.addRow(teks, x)
        form.addRow(self.chk_auto)
        lay.addWidget(holder)
        lay.addStretch()
        return w

    def _tab_tema(self):
        w, lay = self._tab()
        lay.addWidget(label("Tema layar antrian (PC dan TV)", "h2"))
        lay.addWidget(label("Mengubah warna layar antrian, termasuk warna panel saat nomor dipanggil (berkedip). "
                            "Berlaku di layar PC dan layar TV setelah Simpan pengaturan.", "muted", wrap=True))
        self.preview = TemaPreview()
        self.cb_tema = QComboBox()
        for kunci, t in TEMA.items():
            self.cb_tema.addItem(t["nama"], kunci)
        self.cb_tema.currentIndexChanged.connect(lambda _i: self.preview.set_tema(get_tema(self.cb_tema.currentData())))
        row = QHBoxLayout()
        row.addWidget(label("Tema"))
        self.cb_tema.setMinimumWidth(320)
        row.addWidget(self.cb_tema)
        row.addStretch()
        lay.addLayout(row)
        lay.addWidget(self.preview, 0, Qt.AlignmentFlag.AlignLeft)
        lay.addWidget(label("Pratinjau: panel nomor berganti warna seperti saat ada panggilan.", "muted"))
        lay.addStretch()
        return w

    def _tab_suara_tv(self):
        w, lay = self._tab()
        lay.addWidget(label("Suara panggilan", "h2"))
        self.chk_suara = QCheckBox("Putar ting-tung dan suara panggilan di PC ini")
        lay.addWidget(self.chk_suara)
        lay.addWidget(label(
            "Suara: perempuan Bahasa Indonesia (Microsoft Gadis). Perlu internet saat sebuah kalimat pertama kali "
            "disuarakan; hasilnya disimpan di PC ini sehingga panggilan berikutnya bisa tanpa internet. "
            "Klik Unduh suara agar nomor 1 sampai 100 langsung siap dipakai offline.", "muted", wrap=True))
        row = QHBoxLayout()
        row.addWidget(button("Tes suara", "soft", self.ctx.test_voice))
        row.addWidget(button("Unduh suara nomor 1-100", "soft", self.unduh_suara))
        row.addStretch()
        lay.addLayout(row)
        lay.addSpacing(16)

        lay.addWidget(label("Layar antrian di TV (lewat jaringan yang sama)", "h2"))
        self.chk_web = QCheckBox("Aktifkan layar antrian untuk TV")
        lay.addWidget(self.chk_web)
        prow = QHBoxLayout()
        prow.addWidget(label("Port"))
        self.sp_port = QSpinBox()
        self.sp_port.setRange(1024, 65000)
        prow.addWidget(self.sp_port)
        prow.addSpacing(24)
        self.chk_tv = QCheckBox("Putar ting-tung dan suara panggilan di TV")
        prow.addWidget(self.chk_tv)
        prow.addStretch()
        lay.addLayout(prow)
        self.lbl_url = label("", "big", wrap=True)
        self.lbl_url.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.lbl_url)
        urow = QHBoxLayout()
        urow.addWidget(button("Salin URL", "soft", self.salin_url))
        urow.addWidget(button("Buka di browser PC", "soft", self.buka_url))
        urow.addStretch()
        lay.addLayout(urow)
        lay.addWidget(label(
            "Cara pakai: pastikan TV dan PC ini tersambung ke WiFi/LAN yang sama, lalu ketik URL di atas pada browser "
            "TV dan jadikan favorit. Tekan OK atau klik sekali di TV untuk mengaktifkan suara. Jika PC dan TV "
            "sama-sama bersuara, matikan salah satunya. Layar TV hanya menampilkan nomor antrian dan video, "
            "tanpa data pasien. Jika Windows meminta izin firewall, pilih Allow access untuk Private networks.",
            "muted", wrap=True))
        lay.addStretch()
        return w

    def _tab_cetak(self):
        w, lay = self._tab()
        lay.addWidget(label("Cetak tiket nomor antrian", "h2"))
        lay.addWidget(label("Tiket dicetak saat pasien mengambil nomor, lalu diberikan ke pasien sebelum dipanggil. "
                            "Pilih printer dan ukuran kertas sesuai tiket.", "muted", wrap=True))
        holder = QWidget()
        holder.setMaximumWidth(780)
        form = QFormLayout(holder)
        form.setContentsMargins(0, 0, 0, 0)
        form.setVerticalSpacing(10)
        self.cb_printer = QComboBox()
        prow = QHBoxLayout()
        prow.addWidget(self.cb_printer, 1)
        prow.addWidget(button("Segarkan", "soft", self._muat_printer))
        self.cb_kertas = QComboBox()
        for kunci, (nama, *_sisa) in ticket.KERTAS.items():
            self.cb_kertas.addItem(nama, kunci)
        self.sp_kw, self.sp_kh = QSpinBox(), QSpinBox()
        self.sp_kw.setRange(40, 220)
        self.sp_kw.setSuffix(" mm")
        self.sp_kh.setRange(0, 1000)
        self.sp_kh.setSuffix(" mm")
        self.sp_kh.setSpecialValueText("otomatis")
        self.cb_kertas.currentIndexChanged.connect(self._kertas_berubah)
        ukuran = QHBoxLayout()
        for x in (label("Lebar"), self.sp_kw, label("   Tinggi"), self.sp_kh):
            ukuran.addWidget(x)
        ukuran.addStretch()
        self.ed_teks = QLineEdit()
        self.ed_teks.setPlaceholderText("Teks di bagian bawah tiket")
        self.sp_salinan = QSpinBox()
        self.sp_salinan.setRange(1, 5)
        self.chk_cetak_auto = QCheckBox("Cetak tiket otomatis saat pasien mengambil nomor")
        self.chk_cetak_nama = QCheckBox("Cetak nama pasien di tiket (jika ada)")
        self.chk_cetak_alamat = QCheckBox("Cetak alamat klinik di tiket")
        form.addRow("Printer", prow)
        form.addRow("Ukuran kertas", self.cb_kertas)
        form.addRow("Ukuran kustom", ukuran)
        form.addRow("Teks bawah", self.ed_teks)
        form.addRow("Jumlah salinan", self.sp_salinan)
        form.addRow(self.chk_cetak_auto)
        form.addRow(self.chk_cetak_nama)
        form.addRow(self.chk_cetak_alamat)
        lay.addWidget(holder)
        row = QHBoxLayout()
        row.addWidget(button("Pratinjau tiket", "soft", self.pratinjau))
        row.addWidget(button("Cetak percobaan", "soft", self.cetak_percobaan))
        row.addWidget(button("Simpan contoh ke PDF", "soft", self.contoh_pdf))
        row.addStretch()
        lay.addLayout(row)
        lay.addWidget(label(
            "Printer thermal (POS-58, XP-58, Epson TM, dan sejenisnya): pasang drivernya di Windows lebih dulu, lalu "
            "pilih di sini. Tinggi tiket otomatis menyesuaikan isinya. Jika kertas keluar terlalu panjang atau "
            "terpotong, buka Printing Preferences printer dan pilih ukuran roll sesuai lebar kertas (58 atau 80 mm). "
            "Pratinjau dan Simpan contoh ke PDF bisa dipakai tanpa printer.", "muted", wrap=True))
        lay.addStretch()
        return w

    def _muat_printer(self, pilih=None):
        if pilih is None:
            pilih = self.cb_printer.currentData() if self.cb_printer.count() else self.db.get("printer")
        nama, bawaan = ticket.daftar_printer()
        self.cb_printer.clear()
        self.cb_printer.addItem("(Belum dipilih)", "")
        for n in nama:
            self.cb_printer.addItem(n + (" (bawaan Windows)" if n == bawaan else ""), n)
        if pilih and pilih not in nama:
            self.cb_printer.addItem(f"{pilih} (tidak ditemukan)", pilih)
        self.cb_printer.setCurrentIndex(max(self.cb_printer.findData(pilih or ""), 0))

    def _kertas_berubah(self):
        kustom = self.cb_kertas.currentData() == "kustom"
        self.sp_kw.setEnabled(kustom)
        self.sp_kh.setEnabled(kustom)

    def _muat_cetak(self):
        g = self.db.get
        self._muat_printer(g("printer"))
        self.cb_kertas.setCurrentIndex(max(self.cb_kertas.findData(g("kertas")), 0))
        for sp, kunci, awal in ((self.sp_kw, "kertas_w", 58), (self.sp_kh, "kertas_h", 0), (self.sp_salinan, "salinan", 1)):
            try:
                sp.setValue(int(g(kunci)))
            except (TypeError, ValueError):
                sp.setValue(awal)
        self.ed_teks.setText(g("teks_karcis") or "")
        self.chk_cetak_auto.setChecked(g("cetak_otomatis") == "1")
        self.chk_cetak_nama.setChecked(g("cetak_nama") == "1")
        self.chk_cetak_alamat.setChecked(g("cetak_alamat") == "1")
        self._kertas_berubah()

    def _simpan_cetak(self):
        for k, v in (("printer", self.cb_printer.currentData() or ""), ("kertas", self.cb_kertas.currentData()),
                     ("kertas_w", self.sp_kw.value()), ("kertas_h", self.sp_kh.value()),
                     ("teks_karcis", self.ed_teks.text().strip()), ("salinan", self.sp_salinan.value()),
                     ("cetak_otomatis", "1" if self.chk_cetak_auto.isChecked() else "0"),
                     ("cetak_nama", "1" if self.chk_cetak_nama.isChecked() else "0"),
                     ("cetak_alamat", "1" if self.chk_cetak_alamat.isChecked() else "0")):
            self.db.set(k, v)

    def pratinjau(self):
        self._simpan_cetak()
        contoh = ticket.contoh_tiket(self.db)
        img = ticket.render_gambar(self.db, contoh, 203)
        cfg = ticket.konfigurasi(self.db)
        dlg = QDialog(self)
        dlg.setWindowTitle("Pratinjau tiket")
        lay = QVBoxLayout(dlg)
        lay.addWidget(label(f"Ukuran kertas: {cfg.lebar} mm x {ticket.tinggi_tiket(self.db, contoh):.0f} mm "
                            "(tinggi menyesuaikan isi)" if not cfg.tinggi else
                            f"Ukuran kertas: {cfg.lebar} mm x {cfg.tinggi} mm", "muted"))
        isi = QLabel()
        isi.setPixmap(QPixmap.fromImage(img))
        isi.setStyleSheet("background: white; border: 1px solid #c5d4d0;")
        gulung = QScrollArea()
        gulung.setWidget(isi)
        gulung.setMinimumSize(min(img.width() + 40, 760), min(img.height() + 20, 620))
        lay.addWidget(gulung)
        lay.addWidget(button("Tutup", "soft", dlg.accept))
        dlg.exec()

    def cetak_percobaan(self):
        self._simpan_cetak()
        ok, pesan = ticket.cetak(self.db, ticket.contoh_tiket(self.db))
        if ok:
            info(self, "Tiket percobaan dikirim ke printer.")
        else:
            warn(self, f"Tiket percobaan gagal dicetak:\n{pesan}")

    def contoh_pdf(self):
        self._simpan_cetak()
        path, _ = QFileDialog.getSaveFileName(self, "Simpan contoh tiket", str(_folder_dokumen() / "tiket-contoh.pdf"),
                                              "PDF (*.pdf)")
        if not path:
            return
        ok, pesan = ticket.cetak(self.db, ticket.contoh_tiket(self.db), pdf_path=path)
        if not ok:
            warn(self, f"Gagal menyimpan PDF:\n{pesan}")
        elif ask(self, "Contoh tiket tersimpan.\nBuka file sekarang?"):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _tab_layanan(self):
        w, lay = self._tab()
        lay.addWidget(label("Layanan / poli yang tampil di antrian", "h2"))
        self.t_poli = make_table(["Kode", "Layanan", "Ruang", "Status"], stretch=1)
        self.t_poli.doubleClicked.connect(lambda _i: self.edit_poli())
        lay.addWidget(self.t_poli, 1)
        row = QHBoxLayout()
        row.addWidget(button("+ Layanan", slot=self.add_poli))
        row.addWidget(button("Ubah", "soft", self.edit_poli))
        row.addStretch()
        lay.addLayout(row)
        return w

    def _tab_data(self):
        w, lay = self._tab()
        lay.addWidget(label("Data dan cadangan", "h2"))
        lay.addWidget(label(f"Data tersimpan di: {data_dir()}", "muted", wrap=True))
        row = QHBoxLayout()
        row.addWidget(button("Backup data", slot=self.backup))
        row.addWidget(button("Pulihkan dari backup", "soft", self.restore))
        row.addWidget(button("Buka folder data", "soft",
                             lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir())))))
        row.addStretch()
        lay.addLayout(row)
        lay.addSpacing(10)
        lay.addWidget(label(f"Sistem Antrian Klinik v{APP_VERSION}   {COPYRIGHT}", "muted"))
        lay.addStretch()
        return w

    # ---- muat & simpan -----------------------------------------------------------------
    def refresh(self):
        g = self.db.get
        self.ed_nama.setText(g("nama_klinik") or "")
        self.ed_alamat.setPlainText(g("alamat") or "")
        self.ed_tel.setText(g("telepon") or "")
        self.ed_run.setPlainText(g("running_text") or "")
        try:
            self.sl_vol.setValue(int(g("volume_video")))
        except (TypeError, ValueError):
            self.sl_vol.setValue(40)
        self.chk_auto.setChecked(g("buka_otomatis") == "1")
        self.cb_tema.setCurrentIndex(max(self.cb_tema.findData(g("tema")), 0))
        self.preview.set_tema(get_tema(self.cb_tema.currentData()))
        self.cb_mon.clear()
        self.cb_mon.addItem("Otomatis (monitor kedua jika ada)", "auto")
        for i, s in enumerate(QGuiApplication.screens()):
            self.cb_mon.addItem(f"Monitor {i + 1} ({s.size().width()}×{s.size().height()})", str(i))
        self.cb_mon.setCurrentIndex(max(self.cb_mon.findData(g("monitor")), 0))
        self.chk_suara.setChecked(g("suara") == "1")
        self.chk_web.setChecked(g("web_aktif") == "1")
        self.chk_tv.setChecked(g("suara_tv") == "1")
        try:
            self.sp_port.setValue(int(g("web_port")))
        except (TypeError, ValueError):
            self.sp_port.setValue(8080)
        self._refresh_url()
        self._muat_cetak()
        rows = self.db.poli_list(aktif_only=False)
        fill_table(self.t_poli, [[p["kode"], p["nama"], p["loket"], "Aktif" if p["aktif"] else "Nonaktif"]
                                 for p in rows], ids=[p["id"] for p in rows])

    def _refresh_url(self):
        web = self.ctx.web
        if web.running:
            self.lbl_url.setText("\n".join(web.urls()))
        elif self.db.get("web_aktif") == "1":
            self.lbl_url.setText("Server TV gagal dijalankan: " + (web.error or "port dipakai program lain"))
        else:
            self.lbl_url.setText("Layar TV nonaktif")

    def simpan(self):
        nama = self.ed_nama.text().strip()
        if not nama:
            warn(self, "Nama klinik wajib diisi.")
            return
        for k, v in (("nama_klinik", nama), ("alamat", self.ed_alamat.toPlainText().strip()),
                     ("telepon", self.ed_tel.text().strip()), ("running_text", self.ed_run.toPlainText().strip()),
                     ("volume_video", self.sl_vol.value()), ("monitor", self.cb_mon.currentData()),
                     ("tema", self.cb_tema.currentData()),
                     ("buka_otomatis", "1" if self.chk_auto.isChecked() else "0"),
                     ("suara", "1" if self.chk_suara.isChecked() else "0"),
                     ("suara_tv", "1" if self.chk_tv.isChecked() else "0"),
                     ("web_aktif", "1" if self.chk_web.isChecked() else "0"),
                     ("web_port", self.sp_port.value())):
            self.db.set(k, v)
        self._simpan_cetak()
        self.ctx.apply_web_settings()
        self.ctx.notify_settings_changed()
        self._refresh_url()
        info(self, "Pengaturan disimpan.")

    # ---- TV ----------------------------------------------------------------------------
    def salin_url(self):
        urls = self.ctx.web.urls()
        if not urls:
            info(self, "Layar TV belum aktif. Centang Aktifkan layar antrian untuk TV lalu Simpan pengaturan.")
            return
        QGuiApplication.clipboard().setText(urls[0])
        info(self, f"URL disalin:\n{urls[0]}")

    def buka_url(self):
        web = self.ctx.web
        if not web.running:
            info(self, "Layar TV belum aktif. Centang Aktifkan layar antrian untuk TV lalu Simpan pengaturan.")
            return
        QDesktopServices.openUrl(QUrl(f"http://localhost:{web.port}"))

    # ---- unduh suara -------------------------------------------------------------------
    def unduh_suara(self):
        v = self.ctx.voices
        if v.busy:
            info(self, "Unduhan suara sedang berjalan.")
            return
        teks = [kalimat_panggilan(f"{p['kode']}{n:03d}", n, p["nama"], p["loket"])
                for p in self.db.poli_list() for n in range(1, 101)]
        if not teks:
            warn(self, "Belum ada layanan aktif.")
            return
        if not ask(self, f"Unduh {len(teks)} kalimat suara untuk semua layanan aktif?\n"
                         "Butuh internet dan memakan waktu beberapa menit. Setelah selesai, panggilan nomor 1 "
                         "sampai 100 bisa diputar tanpa internet."):
            return
        dlg = QProgressDialog("Mengunduh suara...", "Batal", 0, len(teks), self)
        dlg.setWindowTitle("Unduh suara")
        dlg.setWindowModality(Qt.WindowModality.WindowModal)
        dlg.setMinimumDuration(0)

        def progres(selesai, total):
            dlg.setMaximum(total)
            dlg.setValue(selesai)

        def selesai(ok, gagal):
            v.progress.disconnect(progres)
            v.prefetch_done.disconnect(selesai)
            dlg.close()
            if gagal and not ok:
                warn(self, "Suara tidak dapat diunduh. Periksa koneksi internet PC ini lalu coba lagi.")
            else:
                info(self, f"Selesai. {ok} kalimat diunduh" + (f", {gagal} gagal." if gagal else "."))

        v.progress.connect(progres)
        v.prefetch_done.connect(selesai)
        dlg.canceled.connect(v.cancel_prefetch)
        v.prefetch(teks)

    # ---- layanan -----------------------------------------------------------------------
    @staticmethod
    def _poli_fields():
        return [("kode", "Kode huruf (1-3) *", "text"), ("nama", "Nama layanan *", "text"),
                ("loket", "Ruang / loket", "text"), ("aktif", "Aktif", "check")]

    def _simpan_poli(self, d, id=None):
        if not d["kode"].isalpha() or len(d["kode"]) > 3:
            warn(self, "Kode harus berupa 1 sampai 3 huruf, misalnya A.")
            return
        try:
            self.db.poli_save(d, id)
        except sqlite3.IntegrityError:
            warn(self, "Kode huruf sudah dipakai layanan lain.")
            return
        self.refresh()
        self.ctx.notify_data_changed()

    def add_poli(self):
        d = ask_form(self, "Layanan baru", self._poli_fields(), {"aktif": True}, required=("kode", "nama"))
        if d:
            self._simpan_poli(d)

    def edit_poli(self):
        pid = selected_id(self.t_poli)
        if pid is None:
            info(self, "Pilih layanan di tabel terlebih dahulu.")
            return
        p = next(r for r in self.db.poli_list(aktif_only=False) if r["id"] == pid)
        d = ask_form(self, "Ubah layanan", self._poli_fields(), dict(p), required=("kode", "nama"))
        if d:
            self._simpan_poli(d, pid)

    # ---- backup ------------------------------------------------------------------------
    def backup(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan backup data", str(_folder_dokumen() / f"backup-klinik-{date.today():%Y%m%d}.db"),
            "Database (*.db)")
        if not path:
            return
        try:
            self.db.backup(path)
        except Exception as e:
            warn(self, f"Backup gagal:\n{e}")
            return
        info(self, f"Backup tersimpan:\n{path}")

    def restore(self):
        path, _ = QFileDialog.getOpenFileName(self, "Pilih file backup", str(_folder_dokumen()), "Database (*.db)")
        if not path or not ask(self, "Semua data saat ini akan diganti dengan isi file backup.\nLanjutkan?"):
            return
        try:
            self.db.restore(path)
        except Exception as e:
            warn(self, f"Pemulihan gagal:\n{e}")
            return
        self.refresh()
        self.ctx.notify_all()
        info(self, "Data berhasil dipulihkan.")
