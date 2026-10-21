"""Suara panggilan perempuan Bahasa Indonesia.

Memakai suara neural Microsoft "id-ID-GadisNeural" (perempuan, logat Indonesia asli) lewat paket edge-tts.
Setiap kalimat hanya perlu diunduh sekali (butuh internet); hasilnya disimpan sebagai file MP3 di
%APPDATA%\\SistemAntrianKlinik\\suara sehingga panggilan berikutnya bisa tanpa internet.
"""
import asyncio
import hashlib
import os
import queue
import re
import tempfile
import threading
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from .config import data_dir, terbilang

VOICE = "id-ID-GadisNeural"
RATE = "-8%"  # sedikit lebih pelan supaya jelas terdengar di ruang tunggu


def _eja(m):
    return " ".join(m.group())


def _singkatan(teks: str) -> str:
    """KIA -> 'K I A', KB -> 'K B' (singkatan huruf besar dieja satu per satu)."""
    return re.sub(r"\b[A-Z]{2,4}\b", _eja, teks)


def kalimat_panggilan(kode: str, nomor: int, poli: str, loket: str = "") -> str:
    """Kalimat yang diucapkan, mis. 'Nomor antrian, A, tiga belas. Silakan menuju, Pemeriksaan Umum, Ruang Periksa 1.'"""
    huruf = " ".join(kode.rstrip("0123456789"))
    tujuan = _singkatan(poli) + (", " + _singkatan(loket) if loket else "")
    return f"Nomor antrian, {huruf}, {terbilang(int(nomor))}. Silakan menuju, {tujuan}."


def kunci(teks: str) -> str:
    return hashlib.sha1(f"{VOICE}|{RATE}|{teks}".encode("utf-8")).hexdigest()[:20]


async def _sintesis(teks: str, path: Path, timeout: float = 25):
    import edge_tts  # diimpor di sini agar aplikasi tetap jalan walau paket ini bermasalah

    sementara = Path(str(path) + ".part")
    try:
        await asyncio.wait_for(edge_tts.Communicate(teks, VOICE, rate=RATE).save(str(sementara)), timeout)
        if not sementara.exists() or sementara.stat().st_size < 2000:
            raise RuntimeError("layanan suara mengembalikan audio kosong")
        os.replace(sementara, path)
    finally:
        sementara.unlink(missing_ok=True)


def cek_layanan(timeout: float = 25):
    """Uji sintesis singkat (butuh internet). Mengembalikan (berhasil, pesan)."""
    p = Path(tempfile.gettempdir()) / "sak-cek-suara.mp3"
    try:
        asyncio.run(_sintesis("Tes suara antrian.", p, timeout))
        p.unlink(missing_ok=True)
        return True, ""
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


class VoiceService(QObject):
    """Meminta, menyimpan (cache), dan mengunduh massal suara panggilan.

    Pekerjaan jaringan berjalan di thread terpisah; hasilnya diteruskan ke thread utama lewat antrean
    yang dibaca timer, jadi aman dipakai dari antarmuka."""

    ready = Signal(str, str)        # (kalimat, path mp3)
    failed = Signal(str, str)       # (kalimat, pesan)
    progress = Signal(int, int)     # (selesai, total) unduh massal
    prefetch_done = Signal(int, int)  # (berhasil, gagal)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dir = data_dir() / "suara"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._q = queue.Queue()
        self._pending = set()
        self._busy = False
        self._cancel = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._drain)
        self._timer.start(100)

    @property
    def busy(self):
        return self._busy

    def path_for(self, teks):
        return self.dir / f"{kunci(teks)}.mp3"

    def cached(self, teks):
        p = self.path_for(teks)
        return p if p.exists() and p.stat().st_size > 2000 else None

    def request(self, teks):
        """Sediakan audio untuk kalimat ini: dari cache, atau unduh dulu bila belum ada."""
        p = self.cached(teks)
        if p:
            self._q.put(("ready", teks, str(p)))
            return
        if teks in self._pending:
            return
        self._pending.add(teks)
        threading.Thread(target=self._kerja, args=(teks,), daemon=True).start()

    def _kerja(self, teks):
        try:
            asyncio.run(_sintesis(teks, self.path_for(teks)))
            self._q.put(("ready", teks, str(self.path_for(teks))))
        except Exception as e:
            self._q.put(("failed", teks, f"{type(e).__name__}: {e}"))
        finally:
            self._pending.discard(teks)

    # ---- unduh massal (agar bisa dipakai offline) ----------------------------------
    def prefetch(self, daftar, konkuren=4):
        if self._busy:
            return
        todo = [t for t in dict.fromkeys(daftar) if not self.cached(t)]
        if not todo:
            self._q.put(("done", 0, 0))
            return
        self._busy, self._cancel = True, False
        threading.Thread(target=self._kerja_massal, args=(todo, konkuren), daemon=True).start()

    def cancel_prefetch(self):
        self._cancel = True

    def _kerja_massal(self, todo, konkuren):
        hasil = {"ok": 0, "gagal": 0}

        async def utama():
            sem = asyncio.Semaphore(konkuren)

            async def satu(t):
                async with sem:
                    if self._cancel:
                        return
                    try:
                        await _sintesis(t, self.path_for(t))
                        hasil["ok"] += 1
                    except Exception:
                        hasil["gagal"] += 1
                        if hasil["ok"] == 0 and hasil["gagal"] >= 5:  # kemungkinan besar offline: hentikan
                            self._cancel = True
                    self._q.put(("progress", hasil["ok"] + hasil["gagal"], len(todo)))

            await asyncio.gather(*(satu(t) for t in todo))

        try:
            asyncio.run(utama())
        finally:
            self._q.put(("done", hasil["ok"], hasil["gagal"]))

    # ---- teruskan hasil ke thread utama -------------------------------------------------
    def _drain(self):
        while True:
            try:
                jenis, a, b = self._q.get_nowait()
            except queue.Empty:
                return
            if jenis == "ready":
                self.ready.emit(a, b)
            elif jenis == "failed":
                self.failed.emit(a, b)
            elif jenis == "progress":
                self.progress.emit(a, b)
            else:
                self._busy = False
                self.prefetch_done.emit(a, b)
