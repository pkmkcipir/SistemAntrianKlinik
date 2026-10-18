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
        QTimer.singleShot(1500, app.quit)
        app.exec()
        log.write_text("OK", encoding="utf-8")
        return 0
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
