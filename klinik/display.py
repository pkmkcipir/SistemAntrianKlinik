"""Layar antrian untuk monitor ruang tunggu: nomor dipanggil, video edukasi, teks berjalan."""
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QLayout, QStackedLayout, QVBoxLayout,
                               QWidget)

from .audio import audio_tersedia
from .config import COPYRIGHT, tanggal_panjang
from .themes import get_tema, qss_layar

# Bahnschrift (bawaan Windows 10/11) mirip huruf papan petunjuk: angka antrian terbaca dari jauh.
NUM_FONT = ["Bahnschrift", "Segoe UI", "Arial"]
PLACEHOLDER = "Video edukasi belum ditambahkan.\nTambahkan lewat menu Video Edukasi di aplikasi."



def _font(w, px, bold=False, families=None):
    f = w.font()
    if families:
        f.setFamilies(families)
    f.setPixelSize(max(8, int(px)))
    f.setBold(bold)
    w.setFont(f)


class Marquee(QWidget):
    """Teks berjalan di footer."""

    def __init__(self):
        super().__init__()
        self._text, self._x, self.speed = "", 0.0, 2.5
        self.color = QColor("#ffffff")
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(30)

    def set_text(self, text):
        self._text, self._x = text, float(self.width())

    def _tick(self):
        if not self._text or not self.isVisible():
            return
        self._x -= self.speed
        if self._x < -QFontMetrics(self.font()).horizontalAdvance(self._text):
            self._x = float(self.width())
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setPen(self.color)
        p.setFont(self.font())
        fm = p.fontMetrics()
        p.drawText(int(self._x), (self.height() + fm.ascent() - fm.descent()) // 2, self._text)


class PoliRow(QFrame):
    """Satu baris layanan: nama, jumlah menunggu, dan nomor yang terakhir dipanggil."""

    def __init__(self):
        super().__init__()
        self.setObjectName("poliRow")
        g = QGridLayout(self)
        g.setContentsMargins(24, 4, 24, 4)
        g.setVerticalSpacing(0)
        self.nama, self.info, self.now = QLabel(), QLabel(), QLabel("-")
        self.nama.setObjectName("pNama")
        self.info.setObjectName("pInfo")
        self.now.setObjectName("pNow")
        self.now.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        g.addWidget(self.nama, 0, 0, Qt.AlignmentFlag.AlignBottom)
        g.addWidget(self.info, 1, 0, Qt.AlignmentFlag.AlignTop)
        g.addWidget(self.now, 0, 1, 2, 1)
        g.setColumnStretch(0, 1)

    def update_state(self, s):
        self.nama.setText(s["nama"])
        self.now.setText(s["sekarang"])
        txt = f"{s['menunggu']} menunggu"
        if s["berikut"]:
            txt += ", berikut " + ", ".join(s["berikut"])
        self.info.setText(txt)

    def rescale(self, u):
        _font(self.nama, 30 * u, True)
        _font(self.info, 20 * u)
        _font(self.now, 54 * u, True, NUM_FONT)


class DisplayWindow(QWidget):
    closed = Signal()

    def __init__(self, db, announcer):
        super().__init__()
        self.db = db
        self.setObjectName("display")
        self.setWindowTitle("Layar Antrian")
        self._tema_id = None
        self.files, self.idx, self._fail = None, -1, 0
        self._token, self._advanced, self._t_load = 0, -1, 0.0
        self._vol, self._sig, self.rows, self._flash_n = 0.4, None, [], 0
        self._build()
        self._setup_player()
        self._apply_tema()
        announcer.started.connect(lambda: self._duck(True))
        announcer.done.connect(lambda: self._duck(False))
        self.t_clock = QTimer(self)
        self.t_clock.timeout.connect(self._tick)
        self.t_refresh = QTimer(self)
        self.t_refresh.timeout.connect(self.refresh)
        self.t_flash = QTimer(self)
        self.t_flash.timeout.connect(self._flash_tick)

    # ---- susunan tampilan ------------------------------------------------------
    @staticmethod
    def _lbl(name, right=False, center=False):
        lb = QLabel()
        lb.setObjectName(name)
        h = (Qt.AlignmentFlag.AlignRight if right else
             Qt.AlignmentFlag.AlignHCenter if center else Qt.AlignmentFlag.AlignLeft)
        lb.setAlignment(h | Qt.AlignmentFlag.AlignVCenter)
        return lb

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)  # ukuran font ikut jendela, bukan sebaliknya
        self.setMinimumSize(640, 360)

        header = QFrame()
        header.setObjectName("header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(32, 14, 32, 14)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        self.hTitle, self.hSub, self.hTel = self._lbl("hTitle"), self._lbl("hSub"), self._lbl("hTel")
        for w in (self.hTitle, self.hSub, self.hTel):
            titles.addWidget(w)
        times = QVBoxLayout()
        times.setSpacing(0)
        self.hDate, self.hClock = self._lbl("hDate", right=True), self._lbl("hClock", right=True)
        times.addWidget(self.hDate)
        times.addWidget(self.hClock)
        hl.addLayout(titles, 1)
        hl.addLayout(times)
        root.addWidget(header)

        body = QHBoxLayout()
        body.setContentsMargins(24, 20, 24, 20)
        body.setSpacing(24)
        box = QFrame()
        box.setObjectName("videoBox")
        self.stack = QStackedLayout(box)
        self.stack.setContentsMargins(0, 0, 0, 0)
        self.placeholder = self._lbl("placeholder", center=True)
        self.placeholder.setText(PLACEHOLDER)
        self.video = QVideoWidget()
        self.stack.addWidget(self.placeholder)
        self.stack.addWidget(self.video)

        right = QVBoxLayout()
        right.setSpacing(16)
        self.called = QFrame()
        self.called.setObjectName("called")
        cl = QVBoxLayout(self.called)
        cl.setContentsMargins(32, 18, 32, 22)
        cl.setSpacing(0)
        self.cCap, self.cNum = self._lbl("cCap"), self._lbl("cNum")
        self.cPoli, self.cLoket = self._lbl("cPoli"), self._lbl("cLoket")
        self.cCap.setText("Sedang dipanggil")
        cl.addWidget(self.cCap)
        cl.addWidget(self.cNum, 1)
        cl.addWidget(self.cPoli)
        cl.addWidget(self.cLoket)
        self.board = QFrame()
        self.board.setObjectName("board")
        self.rows_lay = QVBoxLayout(self.board)
        self.rows_lay.setContentsMargins(0, 8, 0, 8)
        self.rows_lay.setSpacing(0)
        right.addWidget(self.called, 3)
        right.addWidget(self.board, 2)

        body.addWidget(box, 62)
        body.addLayout(right, 38)
        root.addLayout(body, 1)

        footer = QFrame()
        footer.setObjectName("footer")
        fl = QVBoxLayout(footer)
        fl.setContentsMargins(0, 8, 0, 8)
        fl.setSpacing(0)
        self.marquee = Marquee()
        self.fMark = self._lbl("fMark", center=True)
        self.fMark.setText(COPYRIGHT)
        fl.addWidget(self.marquee)
        fl.addWidget(self.fMark)
        root.addWidget(footer)
        self._set_called("", "Belum ada panggilan", "")

    def _rescale(self):
        u = max(self.height(), 480) / 1080
        _font(self.hTitle, 46 * u, True)
        _font(self.hSub, 22 * u)
        _font(self.hTel, 22 * u)
        _font(self.hDate, 26 * u)
        _font(self.hClock, 44 * u, True, NUM_FONT)
        _font(self.cCap, 28 * u, True)
        _font(self.cPoli, 42 * u, True)
        _font(self.cLoket, 30 * u)
        _font(self.placeholder, 32 * u)
        _font(self.marquee, 36 * u, True)
        self.marquee.setFixedHeight(int(60 * u))
        self.marquee.speed = max(1.5, 3.2 * u)
        _font(self.fMark, 20 * u)
        k = u * min(1.0, 4 / max(len(self.rows), 1))
        for r in self.rows:
            r.rescale(k)
        self._fit_number(u)

    def _fit_number(self, u=None):
        u = u or max(self.height(), 480) / 1080
        m = self.called.layout().contentsMargins()
        extra = sum(w.sizeHint().height() for w in (self.cCap, self.cPoli, self.cLoket)) + m.top() + m.bottom()
        avail_w = max(self.called.width() - m.left() - m.right(), 120)
        avail_h = max(self.called.height() - extra, 40)
        size, text = 230 * u, self.cNum.text()
        while size > 24:
            _font(self.cNum, size, True, NUM_FONT)
            fm = QFontMetrics(self.cNum.font())
            if fm.horizontalAdvance(text) <= avail_w and fm.height() <= avail_h:
                break
            size -= 8

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._rescale()

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(60, self._rescale)

    # ---- tampil di monitor -----------------------------------------------------
    def show_on(self, screen, fullscreen):
        geo = screen.geometry()
        self.setScreen(screen)
        if fullscreen:
            self.move(geo.topLeft())
            self.showFullScreen()
            if self.windowHandle():
                self.windowHandle().setScreen(screen)
        else:
            self.resize(min(1280, geo.width() - 120), min(720, geo.height() - 120))
            self.move(geo.x() + 60, geo.y() + 60)
            self.showNormal()
        self._apply_cursor()
        self.reload_settings()
        self.reload_videos(force=True)
        self.refresh()
        self._tick()
        self.t_clock.start(1000)
        self.t_refresh.start(2500)

    def _apply_cursor(self):
        self.setCursor(Qt.CursorShape.BlankCursor if self.isFullScreen() else Qt.CursorShape.ArrowCursor)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_F11:
            self.showNormal() if self.isFullScreen() else self.showFullScreen()
            self._apply_cursor()
        elif e.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.showNormal()
            self._apply_cursor()
        else:
            super().keyPressEvent(e)

    def closeEvent(self, e):
        self.t_clock.stop()
        self.t_refresh.stop()
        self.t_flash.stop()
        self.player.stop()
        self.closed.emit()
        e.accept()

    # ---- data ------------------------------------------------------------------
    def _apply_tema(self):
        """Terapkan tema warna dari Pengaturan (hanya bila berubah)."""
        t = get_tema(self.db.get("tema"))
        if t["id"] == self._tema_id:
            return
        self._tema_id = t["id"]
        self.setStyleSheet(qss_layar(t))
        self.marquee.color = QColor(t["footer_fg"])
        self.marquee.update()

    def reload_settings(self):
        self._apply_tema()
        g = self.db.get
        self.hTitle.setText(g("nama_klinik") or "")
        self.hSub.setText(g("alamat") or "")
        tel = g("telepon") or ""
        self.hTel.setText(f"Telp/WA {tel}" if tel else "")
        self.hTel.setVisible(bool(tel))
        self.marquee.set_text(g("running_text") or "")
        try:
            self._vol = max(0, min(100, int(g("volume_video")))) / 100
        except (TypeError, ValueError):
            self._vol = 0.4
        if self.audio:
            self.audio.setVolume(self._vol)
        self._rescale()

    def refresh(self):
        st = self.db.display_state()
        sig = [(p["id"], p["kode"], p["nama"]) for p in st["poli"]]
        if sig != self._sig:
            self._sig = sig
            self._build_rows(len(sig))
        for row, p in zip(self.rows, st["poli"]):
            row.update_state(p)
        t = st["terakhir"]
        if t:
            self._set_called(t["kode"], t["poli_nama"], t["loket"])
        else:  # belum ada panggilan hari ini, atau nomor yang dipanggil sudah dihapus
            self._set_called("", "Belum ada panggilan", "")

    def _build_rows(self, n):
        while self.rows_lay.count():
            w = self.rows_lay.takeAt(0).widget()
            if w:
                w.deleteLater()
        self.rows = []
        for _ in range(n):
            r = PoliRow()
            self.rows.append(r)
            self.rows_lay.addWidget(r, 1)
        self._rescale()

    def _set_called(self, kode, poli, loket):
        self.cNum.setText(kode or "—")
        self.cPoli.setText(poli or "")
        self.cLoket.setText(loket or "")
        self._fit_number()

    def show_called(self, t):
        """Dipanggil saat operator memanggil nomor: tampilkan dan kedipkan panel."""
        self._set_called(t["kode"], t["poli_nama"], t.get("loket", ""))
        self._flash_n = 14
        self.t_flash.start(420)

    def _flash_tick(self):
        self._flash_n -= 1
        self.called.setProperty("flash", self._flash_n > 0 and self._flash_n % 2 == 0)
        st = self.called.style()
        # Qt tidak menerapkan ulang gaya ke label anak saat properti induk berubah: lakukan manual,
        # supaya warna teks ikut berganti (mis. putih -> gelap di atas panel kuning).
        for w in (self.called, *self.called.findChildren(QLabel)):
            st.unpolish(w)
            st.polish(w)
        if self._flash_n <= 0:
            self.t_flash.stop()

    def _tick(self):
        n = datetime.now()
        self.hDate.setText(tanggal_panjang(n.date()))
        self.hClock.setText(n.strftime("%H:%M:%S"))

    # ---- video edukasi ---------------------------------------------------------
    def _setup_player(self):
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self) if audio_tersedia() else None
        if self.audio:
            self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.player.mediaStatusChanged.connect(self._media_status)
        self.player.errorOccurred.connect(lambda *_: self._gagal())

    def _duck(self, on):
        """Kecilkan suara video saat ada panggilan."""
        if self.audio:
            self.audio.setVolume(self._vol * (0.12 if on else 1.0))

    def reload_videos(self, force=False):
        files = [r["path"] for r in self.db.video_list(aktif_only=True) if Path(r["path"]).exists()]
        if files == self.files and not force:
            return
        self.files, self.idx, self._fail, self._advanced = files, -1, 0, -1
        self.player.stop()
        self.placeholder.setText(PLACEHOLDER)
        if not files:
            self.stack.setCurrentWidget(self.placeholder)
            return
        self.stack.setCurrentWidget(self.video)
        self.player.setLoops(-1 if len(files) == 1 else 1)
        self._next_video()

    def _next_video(self):
        if not self.files:
            return
        self._token += 1
        self.idx = (self.idx + 1) % len(self.files)
        self._t_load = time.monotonic()
        url = QUrl.fromLocalFile(self.files[self.idx])
        if self.player.source() == url:
            self.player.setSource(QUrl())  # file yang sama: paksa muat ulang
        self.player.setSource(url)
        self.player.play()

    def _advance(self, delay=0):
        """Pindah ke video berikutnya, tepat sekali per video walau Qt mengirim beberapa sinyal."""
        if self._advanced == self._token:
            return
        self._advanced = self._token
        QTimer.singleShot(delay, self._next_video)

    def _media_status(self, st):
        S = QMediaPlayer.MediaStatus
        if st == S.EndOfMedia:
            if time.monotonic() - self._t_load < 0.7:  # selesai terlalu cepat = file rusak
                self._gagal()
            else:
                self._fail = 0
                self._advance()
        elif st == S.InvalidMedia:
            self._gagal()

    def _gagal(self):
        """Video rusak/tidak didukung: lewati ke berikutnya; berhenti hanya jika semua video gagal."""
        if self._advanced == self._token or not self.files:
            return
        self._fail += 1
        if self._fail > len(self.files):
            self._advanced = self._token
            self.player.stop()
            self.placeholder.setText("Video tidak dapat diputar.\nGunakan format MP4 (H.264 + AAC).")
            self.stack.setCurrentWidget(self.placeholder)
            return
        self._advance(800)
