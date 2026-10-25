"""Bunyi dan suara panggilan di PC: ting-tung, lalu suara perempuan Indonesia (MP3 dari cache),
dengan cadangan suara Windows bila layanan suara online tidak tersedia."""
import math
import os
import struct
import wave
from pathlib import Path

from PySide6.QtCore import QLocale, QObject, QTimer, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QSoundEffect

from .config import data_dir

_AUDIO = None


def audio_tersedia() -> bool:
    """False bila dimatikan (SAK_NO_AUDIO=1) atau PC tidak punya perangkat keluaran audio.
    Dengan begitu aplikasi tetap jalan normal di PC tanpa speaker (video tetap tampil, tanpa suara)."""
    global _AUDIO
    if _AUDIO is None:
        if os.environ.get("SAK_NO_AUDIO") == "1":
            _AUDIO = False
        else:
            try:
                from PySide6.QtMultimedia import QMediaDevices
                _AUDIO = bool(QMediaDevices.audioOutputs())
            except Exception:
                _AUDIO = False
    return _AUDIO


def make_chime(path: Path) -> str:
    """Bunyi 'ting-tung' sederhana, dibuat sekali (tanpa file audio eksternal)."""
    if not path.exists():
        sr = 44100

        def bell(freq, dur):
            n = int(sr * dur)
            return [(math.sin(2 * math.pi * freq * i / sr) + 0.35 * math.sin(4 * math.pi * freq * i / sr)
                     + 0.15 * math.sin(6 * math.pi * freq * i / sr))
                    * math.exp(-4.0 * i / n) * min(1.0, i / 400) * 0.45 for i in range(n)]

        samples = bell(988, 0.6) + bell(740, 0.8)
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32767)) for s in samples))
    return str(path)


class Announcer(QObject):
    """Urutan panggilan di PC: ting-tung -> suara perempuan Indonesia -> (cadangan) suara Windows.

    Teks yang sama harus lebih dulu diminta ke VoiceService (oleh MainWindow); Announcer menunggu
    hasilnya lewat sinyal ready/failed dan memutar file MP3-nya."""
    started = Signal()
    done = Signal()

    def __init__(self, voices, parent=None):
        super().__init__(parent)
        self.voices = voices
        self.audio_ok = audio_tersedia()
        self.chime = self.vplayer = self.vout = self.tts = self._tts_cls = None
        if self.audio_ok:
            self.chime = QSoundEffect(self)
            self.chime.setSource(QUrl.fromLocalFile(make_chime(data_dir() / "chime.wav")))
            self.chime.setVolume(0.9)
            self.vout = QAudioOutput(self)
            self.vplayer = QMediaPlayer(self)
            self.vplayer.setAudioOutput(self.vout)
            self.vplayer.mediaStatusChanged.connect(self._vstatus)
            self.vplayer.errorOccurred.connect(self._verror)
            self._init_tts()
        voices.ready.connect(self._on_ready)
        voices.failed.connect(self._on_failed)
        self._gen = 0
        self._text, self._path, self._voice = "", None, True
        self._active = self._failed = self._chime_done = self._speaking = self._spoke = False
        self._safety = QTimer(self)
        self._safety.setSingleShot(True)
        self._safety.timeout.connect(self._finish)

    # ---- suara cadangan: Windows text-to-speech (bila ada suara Indonesia) -------------
    def _init_tts(self):
        try:
            from PySide6.QtTextToSpeech import QTextToSpeech
            if not QTextToSpeech.availableEngines():
                return
            tts = QTextToSpeech(self)
            for loc in tts.availableLocales():
                if loc.language() == QLocale.Language.Indonesian:
                    tts.setLocale(loc)
                    tts.stateChanged.connect(self._tts_state)
                    self.tts, self._tts_cls = tts, QTextToSpeech
                    break
        except Exception:
            self.tts = None

    @property
    def voice_ok(self):
        """True bila Windows punya suara Indonesia sebagai cadangan."""
        return self.tts is not None

    def _tts_state(self, st):
        S = self._tts_cls.State
        if st == S.Speaking:
            self._spoke = True
        elif st in (S.Ready, S.Error) and self._spoke and self._active:
            self._spoke = False
            self._finish()

    # ---- urutan panggilan ------------------------------------------------------------
    def play(self, text, enabled=True, voice=True):
        self._gen += 1
        gen = self._gen
        self._stop_voice()
        self._active = False
        if not enabled or not self.audio_ok:
            return  # PC senyap: suara dimatikan di Pengaturan atau tidak ada speaker
        self._text, self._voice = text, voice
        p = self.voices.cached(text) if voice else None
        self._path = str(p) if p else None
        self._failed = self._chime_done = self._speaking = self._spoke = False
        self._active = True
        self.started.emit()
        self._safety.start(35000)
        if self.chime:
            self.chime.play()
        QTimer.singleShot(1400, lambda: self._chime_end(gen))
        QTimer.singleShot(10400, lambda: self._timeout(gen))

    def _stop_voice(self):
        if self.vplayer:
            self.vplayer.stop()
        if self.tts:
            self._spoke = False
            self.tts.stop()

    def _chime_end(self, gen):
        if gen == self._gen and self._active:
            self._chime_done = True
            self._advance()

    def _timeout(self, gen):
        """Layanan suara terlalu lama menjawab: pakai suara cadangan."""
        if gen == self._gen and self._active and not self._path and not self._speaking:
            self._failed = True
            self._advance()

    def _on_ready(self, teks, path):
        if self._active and teks == self._text:
            self._path = path
            self._advance()

    def _on_failed(self, teks, _pesan):
        if self._active and teks == self._text:
            self._failed = True
            self._advance()

    def _advance(self):
        if not self._active or not self._chime_done or self._speaking:
            return
        if not self._voice:
            self._finish()
        elif self._path:
            self._play_file()
        elif self._failed:
            self._play_local()
        # selain itu: masih menunggu hasil sintesis (ready / failed / timeout)

    def _play_file(self):
        self._speaking = True
        url = QUrl.fromLocalFile(self._path)
        if self.vplayer.source() == url:
            self.vplayer.setSource(QUrl())  # file yang sama (panggil ulang): paksa muat ulang
        self.vplayer.setSource(url)
        self.vout.setVolume(1.0)
        self.vplayer.play()

    def _play_local(self):
        if self.vplayer:
            self.vplayer.stop()
        if self.tts:
            self._speaking, self._spoke = True, False
            self.tts.say(self._text)
        else:
            self._finish()

    def _vstatus(self, st):
        S = QMediaPlayer.MediaStatus
        if not (self._active and self._speaking):
            return
        if st == S.EndOfMedia:
            self._finish()
        elif st == S.InvalidMedia:
            self._play_local()

    def _verror(self, *_):
        if self._active and self._speaking:
            self._play_local()

    def _finish(self):
        self._safety.stop()
        was = self._active
        self._speaking = self._active = False
        if was:
            self.done.emit()
