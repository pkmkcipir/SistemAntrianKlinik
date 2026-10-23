"""Titik masuk aplikasi Sistem Antrian Klinik.  @copyright iman.mn_"""
import os
import sys
import tempfile
import traceback
from pathlib import Path


def run_selftest() -> int:
    """Uji cepat (dipakai GitHub Actions): pastikan exe bisa start dan semua modul termuat."""
    log = Path(tempfile.gettempdir()) / "SistemAntrianKlinik-selftest.log"
    try:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["SAK_NO_AUDIO"] = "1"
        os.environ["SAK_DATA_DIR"] = tempfile.mkdtemp(prefix="sak-")
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        from klinik.main_window import MainWindow
        from klinik.widgets import apply_theme

        app = QApplication(sys.argv)
        apply_theme(app)
        win = MainWindow()
        win.show()
        win.open_display()

        # server layar TV harus menjawab dan halaman TV harus ikut terkemas
        import json
        import urllib.request
        web = "server TV tidak berjalan"
        if win.web.running:
            base = f"http://127.0.0.1:{win.web.port}"
            with urllib.request.urlopen(base + "/api/state", timeout=5) as r:
                ok_state = json.loads(r.read()).get("ready") is True
            with urllib.request.urlopen(base + "/", timeout=5) as r:
                ok_html = b"Layar Antrian" in r.read()
            web = "ok" if ok_state and ok_html else f"gagal (state={ok_state}, halaman={ok_html})"

        # karcis nomor antrian: cetak ke PDF memastikan dukungan cetak ikut terkemas
        from klinik import ticket
        pdf = Path(tempfile.gettempdir()) / "sak-selftest-karcis.pdf"
        ok_cetak, pesan_cetak = ticket.cetak(win.db, ticket.contoh_karcis(win.db), pdf_path=pdf)
        ok_cetak = ok_cetak and pdf.exists() and pdf.stat().st_size > 1000

        # suara perempuan Indonesia (butuh internet): hanya dicatat, tidak menggagalkan uji
        from klinik.voice import cek_layanan
        suara_ok, pesan = cek_layanan()

        QTimer.singleShot(800, app.quit)
        app.exec()
        log.write_text(f"OK | TV: {web} | KARCIS: {'ok' if ok_cetak else 'gagal - ' + pesan_cetak} | "
                       f"SUARA: {'ok' if suara_ok else 'gagal - ' + pesan}", encoding="utf-8")
        return 0 if web == "ok" and ok_cetak else 1
    except Exception:
        log.write_text(traceback.format_exc(), encoding="utf-8")
        return 1


def run() -> int:
    if sys.platform == "win32":
        try:  # supaya ikon di taskbar Windows memakai ikon aplikasi
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("iman.mn_.SistemAntrianKlinik")
        except Exception:
            pass
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from klinik.config import APP_NAME, resource_path
    from klinik.main_window import MainWindow
    from klinik.widgets import apply_theme

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    apply_theme(app)
    app.setWindowIcon(QIcon(resource_path("assets/icon.png")))
    win = MainWindow()
    win.show()
    win.auto_open_display()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run_selftest() if "--selftest" in sys.argv else run())
