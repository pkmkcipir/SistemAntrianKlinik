"""Jendela utama: menu samping, halaman, layar antrian (PC dan TV), dan suara panggilan."""
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFrame, QHBoxLayout, QListWidget, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from . import ticket
from .audio import Announcer, make_chime
from .config import APP_TITLE, APP_VERSION, COPYRIGHT, data_dir
from .db import Database
from .display import DisplayWindow
from .mediainfo import probe_cached
from .pages_antrian import QueuePage
from .pages_data import FinancePage, MedicinePage, PatientPage
from .pages_lain import ReportPage, VideoPage
from .pages_pengaturan import SettingsPage
from .themes import get_tema
from .voice import VoiceService, kalimat_panggilan
from .webserver import Hub, WebServer
from .widgets import MAIN_QSS, button, info, label, warn


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.voices = VoiceService(self)
        self.announcer = Announcer(self.voices, self)
        self.hub = Hub()
        self.hub.audio_dir = self.voices.dir
        self.hub.chime = Path(make_chime(data_dir() / "chime.wav"))
        self.web = WebServer(self.hub)
        self.display = None
        self._test_text = None
        self._printer_dicatat = False
        self.voices.ready.connect(self._voice_ready)
        self.voices.failed.connect(self._voice_failed)

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
        self.lbl_note = label("", "muted")
        self.lbl_tv = label("", "muted")
        self.lbl_tv.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.btn_display = button("Buka layar antrian", slot=self.toggle_display)
        top.addWidget(self.title)
        top.addStretch()
        top.addWidget(self.lbl_note)
        top.addSpacing(14)
        top.addWidget(self.lbl_tv)
        top.addSpacing(14)
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

        self.publish_web()
        self.start_web()
        self._web_timer = QTimer(self)
        self._web_timer.timeout.connect(self.publish_web)
        self._web_timer.start(3000)

    def _on_nav(self, i):
        if i < 0:
            return
        name, page = self.pages[i]
        self.stack.setCurrentIndex(i)
        self.title.setText(name)
        page.refresh()

    # ---- cetak tiket ----------------------------------------------------------------------
    def print_ticket(self, t, manual=False):
        """Cetak tiket nomor antrian untuk diberikan ke pasien (otomatis saat nomor diambil, atau cetak ulang)."""
        g = self.db.get
        if not manual and g("cetak_otomatis") != "1":
            return
        if not g("printer"):
            if manual:
                info(self, "Printer belum dipilih. Buka Pengaturan > Cetak Tiket lalu pilih printer.")
            elif not self._printer_dicatat:
                self._printer_dicatat = True
                self.note("Tiket belum bisa dicetak: pilih printer di Pengaturan > Cetak Tiket.")
            return
        ok, pesan = ticket.cetak(self.db, t)
        if not ok:
            warn(self, f"Tiket nomor {t['kode']} gagal dicetak:\n{pesan}\n\nBerikan nomor ini kepada pasien secara manual.")

    # ---- layar antrian di PC ---------------------------------------------------------------
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

    # ---- layar antrian di TV (web) -----------------------------------------------------------
    def start_web(self):
        self.web.stop()
        if self.db.get("web_aktif") == "1":
            try:
                port = int(self.db.get("web_port"))
            except (TypeError, ValueError):
                port = 8080
            self.web.start(port)
        if self.web.running:
            self.lbl_tv.setText("TV: " + self.web.urls()[0])
        else:
            self.lbl_tv.setText("TV: nonaktif" if self.db.get("web_aktif") != "1" else "TV: gagal dijalankan")

    def apply_web_settings(self):
        self.start_web()
        self.publish_web()

    def publish_web(self):
        """Salin keadaan terkini (nomor, layanan, video, pengaturan) untuk dikirim ke layar TV."""
        g = self.db.get
        st = self.db.display_state()
        vids = [r for r in self.db.video_list(aktif_only=True) if Path(r["path"]).exists()]
        t = st["terakhir"]
        try:
            vol = int(g("volume_video"))
        except (TypeError, ValueError):
            vol = 40
        video = []
        for r in vids:
            info = probe_cached(r["path"])  # kodek video: halaman TV memakainya untuk melewati format yang tak didukung
            video.append({"id": r["id"], "judul": r["judul"], "url": f"/video/{r['id']}{Path(r['path']).suffix.lower()}",
                          "mime": info["mime"], "ok": info["ok"], "catatan": info["catatan"]})
        self.hub.set_state({
            "ready": True,
            "klinik": {"nama": g("nama_klinik"), "alamat": g("alamat"), "telepon": g("telepon")},
            "teks": g("running_text"),
            "volume": vol,
            "suara": g("suara_tv") == "1",
            "poli": st["poli"],
            "terakhir": {"kode": t["kode"], "poli": t["poli_nama"], "loket": t["loket"]} if t else None,
            "video": video,
            "tema": get_tema(g("tema")),
            "mark": COPYRIGHT,
        }, {r["id"]: Path(r["path"]) for r in vids})

    # ---- panggilan -----------------------------------------------------------------------------
    def announce(self, t):
        """Nomor dipanggil: tampil di layar PC dan TV, lalu ting-tung + suara perempuan Indonesia."""
        t = dict(t)
        if self._display_visible():
            self.display.show_called(t)
        teks = kalimat_panggilan(t["kode"], t["nomor"], t["poli_nama"], t.get("loket") or "")
        pc = self.db.get("suara") == "1"
        tv = self.db.get("suara_tv") == "1" and self.web.running
        self.hub.new_call(t, teks)
        if pc or tv:
            self.voices.request(teks)  # dipakai bersama oleh PC dan TV; cache bila sudah pernah
        self.announcer.play(teks, enabled=pc, voice=True)
        self.notify_data_changed()

    def test_voice(self):
        if not self.announcer.audio_ok:
            info(self, "Perangkat audio (speaker) tidak terdeteksi di PC ini, jadi suara tidak dapat diputar.")
            return
        teks = kalimat_panggilan("A001", 1, "Pemeriksaan Umum", "Ruang Periksa 1")
        self._test_text = teks
        self.voices.request(teks)
        self.announcer.play(teks, enabled=True, voice=True)

    def _voice_ready(self, teks, path):
        self.hub.set_audio(teks, path)
        if teks == self._test_text:
            self._test_text = None

    def _voice_failed(self, teks, pesan):
        self.hub.set_failed(teks)
        if teks == self._test_text:
            self._test_text = None
            warn(self, "Suara perempuan Indonesia belum bisa diambil dari layanan online.\n"
                       "Periksa koneksi internet PC ini lalu coba lagi.\n\n"
                       + ("Suara cadangan Windows dipakai.\n\n" if self.announcer.voice_ok else "")
                       + f"Detail: {pesan[:200]}")
        else:
            self.note("Suara online belum tersedia (cek internet); hanya ting-tung atau suara cadangan yang diputar.")

    def note(self, teks):
        self.lbl_note.setText(teks)
        QTimer.singleShot(9000, lambda: self.lbl_note.setText("") if self.lbl_note.text() == teks else None)

    # ---- pemberitahuan dari halaman ----------------------------------------------------------------
    def notify_data_changed(self):
        self.publish_web()
        if self._display_visible():
            self.display.refresh()

    def notify_settings_changed(self):
        self.sub.setText(self.db.get("nama_klinik") or "")
        self.publish_web()
        if self._display_visible():
            self.display.reload_settings()

    def notify_videos_changed(self):
        self.publish_web()
        if self._display_visible():
            self.display.reload_videos()

    def notify_all(self):
        self.notify_settings_changed()
        self.notify_videos_changed()
        self.notify_data_changed()

    def closeEvent(self, e):
        if self.display is not None:
            self.display.close()
        self.web.stop()
        e.accept()
