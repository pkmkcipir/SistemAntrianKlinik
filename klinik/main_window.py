"""Jendela utama: menu samping, halaman, dan kontrol layar antrian."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFrame, QHBoxLayout, QListWidget, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from .config import APP_TITLE, APP_VERSION, COPYRIGHT, terbilang
from .db import Database
from .display import Announcer, DisplayWindow
from .pages_antrian import QueuePage
from .pages_data import FinancePage, MedicinePage, PatientPage
from .pages_lain import ReportPage, SettingsPage, VideoPage
from .widgets import MAIN_QSS, button, info, label


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.announcer = Announcer(self)
        self.display = None
        self.setWindowTitle(f"{APP_TITLE} v{APP_VERSION}")
        self.resize(1320, 800)
        self.setMinimumSize(1100, 680)
        self.setStyleSheet(MAIN_QSS)

        root = QWidget()
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        side = QFrame()
        side.setObjectName("side")
        side.setFixedWidth(230)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 0, 0, 12)
        sl.setSpacing(0)
        sl.addWidget(label("Sistem Antrian\nKlinik", "brand"))
        self.sub = label(self.db.get("nama_klinik") or "", "brandSub", wrap=True)
        sl.addWidget(self.sub)
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        sl.addWidget(self.nav, 1)
        h.addWidget(side)

        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        top = QHBoxLayout()
        top.setContentsMargins(22, 16, 22, 2)
        self.title = label("", "h1")
        top.addWidget(self.title)
        top.addStretch()
        self.btn_display = button("Buka layar antrian", slot=self.toggle_display)
        top.addWidget(self.btn_display)
        content.addLayout(top)
        self.stack = QStackedWidget()
        content.addWidget(self.stack, 1)
        content.addWidget(label(COPYRIGHT, "footer"), 0, Qt.AlignmentFlag.AlignHCenter)
        h.addLayout(content, 1)

        self.pages = [("Antrian", QueuePage(self)), ("Pasien", PatientPage(self)),
                      ("Keuangan", FinancePage(self)), ("Obat", MedicinePage(self)),
                      ("Laporan", ReportPage(self)), ("Video Edukasi", VideoPage(self)),
                      ("Pengaturan", SettingsPage(self))]
        for name, page in self.pages:
            self.nav.addItem(name)
            self.stack.addWidget(page)
        self.nav.currentRowChanged.connect(self._on_nav)
        self.nav.setCurrentRow(0)

    def _on_nav(self, i):
        if i < 0:
            return
        name, page = self.pages[i]
        self.stack.setCurrentIndex(i)
        self.title.setText(name)
        page.refresh()

    # ---- layar antrian -----------------------------------------------------------
    def pick_screen(self):
        screens = QGuiApplication.screens()
        sel = self.db.get("monitor", "auto")
        if sel.isdigit() and int(sel) < len(screens):
            return screens[int(sel)]
        if len(screens) > 1:
            return next((s for s in screens if s != self.screen()), screens[0])
        return screens[0]

    def _display_visible(self):
        return self.display is not None and self.display.isVisible()

    def open_display(self):
        if self.display is None:
            self.display = DisplayWindow(self.db, self.announcer)
            self.display.closed.connect(lambda: self.btn_display.setText("Buka layar antrian"))
        scr = self.pick_screen()
        self.display.show_on(scr, fullscreen=len(QGuiApplication.screens()) > 1 and scr != self.screen())
        self.btn_display.setText("Tutup layar antrian")

    def toggle_display(self):
        if self._display_visible():
            self.display.close()
        else:
            self.open_display()

    def auto_open_display(self):
        if self.db.get("buka_otomatis") == "1" and len(QGuiApplication.screens()) > 1:
            self.open_display()

    # ---- pemberitahuan dari halaman ----------------------------------------------
    def announce(self, t):
        """Nomor dipanggil: tampilkan di layar antrian + bunyi + suara."""
        t = dict(t)
        if self._display_visible():
            self.display.show_called(t)
        prefix = t["kode"].rstrip("0123456789")
        ruang = f", {t['loket']}" if t.get("loket") else ""
        teks = f"Nomor antrian {' '.join(prefix)}, {terbilang(t['nomor'])}. Silakan menuju {t['poli_nama']}{ruang}."
        self.announcer.play(teks, voice=self.db.get("suara") == "1")
        self.notify_data_changed()

    def test_voice(self):
        if not self.announcer.audio_ok:
            info(self, "Perangkat audio (speaker) tidak terdeteksi di PC ini, jadi bunyi dan suara panggilan tidak aktif.")
            return
        self.announcer.play("Nomor antrian A, satu. Silakan menuju pemeriksaan umum.", voice=True)
        if not self.announcer.voice_ok:
            info(self, "Suara Bahasa Indonesia belum terpasang di Windows, jadi hanya bunyi ting-tung yang diputar.\n\n"
                       "Pasang lewat Pengaturan Windows > Waktu & bahasa > Ucapan > Tambah suara > Indonesia, "
                       "lalu jalankan ulang aplikasi.")

    def notify_data_changed(self):
        if self._display_visible():
            self.display.refresh()

    def notify_settings_changed(self):
        self.sub.setText(self.db.get("nama_klinik") or "")
        if self._display_visible():
            self.display.reload_settings()

    def notify_videos_changed(self):
        if self._display_visible():
            self.display.reload_videos()

    def notify_all(self):
        self.notify_settings_changed()
        self.notify_videos_changed()
        self.notify_data_changed()

    def closeEvent(self, e):
        if self.display is not None:
            self.display.close()
        e.accept()
