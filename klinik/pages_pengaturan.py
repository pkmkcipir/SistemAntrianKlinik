"""Halaman Pengaturan: identitas klinik, suara dan TV, layanan (poli), data dan backup."""
import sqlite3
from datetime import date

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit,
                               QPlainTextEdit, QProgressDialog, QSlider, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from .config import APP_VERSION, COPYRIGHT, data_dir
from .pages_lain import _folder_dokumen
from .voice import kalimat_panggilan
from .widgets import ask, ask_form, button, fill_table, info, label, make_table, selected_id, warn


class SettingsPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx, self.db = ctx, ctx.db
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 8)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_klinik(), "Klinik")
        self.tabs.addTab(self._tab_suara_tv(), "Suara dan TV")
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
                     ("buka_otomatis", "1" if self.chk_auto.isChecked() else "0"),
                     ("suara", "1" if self.chk_suara.isChecked() else "0"),
                     ("suara_tv", "1" if self.chk_tv.isChecked() else "0"),
                     ("web_aktif", "1" if self.chk_web.isChecked() else "0"),
                     ("web_port", self.sp_port.value())):
            self.db.set(k, v)
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
