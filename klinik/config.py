"""Konfigurasi, konstanta, dan fungsi bantu umum."""
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

APP_NAME = "SistemAntrianKlinik"
APP_TITLE = "Sistem Antrian Klinik"
APP_VERSION = "1.3.0"
COPYRIGHT = "@copyright iman.mn_"

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def resource_path(rel: str) -> str:
    """Lokasi file bawaan aplikasi (jalan di mode biasa maupun hasil PyInstaller)."""
    base = getattr(sys, "_MEIPASS", None) or Path(__file__).resolve().parent.parent
    return str(Path(base) / rel)


def data_dir() -> Path:
    """Folder data pengguna: %APPDATA%\\SistemAntrianKlinik (database, video, backup)."""
    override = os.environ.get("SAK_DATA_DIR")
    if override:
        base = Path(override)
    else:
        base = Path(os.environ.get("APPDATA") or Path.home() / ".local" / "share") / APP_NAME
    (base / "videos").mkdir(parents=True, exist_ok=True)
    return base


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


def today_iso() -> str:
    return date.today().isoformat()


def fmt_date(value) -> str:
    """'2026-10-17' -> '17-10-2026'."""
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").strftime("%d-%m-%Y")
    except ValueError:
        return str(value or "")


def fmt_time(value) -> str:
    return str(value)[11:16] if value else ""


def tanggal_panjang(d: date) -> str:
    return f"{HARI[d.weekday()]}, {d.day} {BULAN[d.month - 1]} {d.year}"


def angka(n) -> str:
    return f"{int(round(n or 0)):,}".replace(",", ".")


def rupiah(n) -> str:
    n = int(round(n or 0))
    return ("-Rp " if n < 0 else "Rp ") + angka(abs(n))


def umur(iso) -> str:
    try:
        lahir = datetime.strptime(str(iso)[:10], "%Y-%m-%d").date()
    except ValueError:
        return ""
    t = date.today()
    return f"{t.year - lahir.year - ((t.month, t.day) < (lahir.month, lahir.day))} th"


def week_range(d: date):
    """Minggu = Senin s/d Minggu."""
    start = d - timedelta(days=d.weekday())
    return start, start + timedelta(days=6)


def month_range(d: date):
    first = d.replace(day=1)
    nxt = (first + timedelta(days=32)).replace(day=1)
    return first, nxt - timedelta(days=1)


_SATUAN = ["nol", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh",
           "delapan", "sembilan", "sepuluh", "sebelas"]


def terbilang(n: int) -> str:
    """Angka -> kata bahasa Indonesia (untuk suara panggilan)."""
    if n < 12:
        return _SATUAN[n]
    if n < 20:
        return _SATUAN[n - 10] + " belas"
    if n < 100:
        return _SATUAN[n // 10] + " puluh" + (" " + _SATUAN[n % 10] if n % 10 else "")
    if n < 200:
        return "seratus" + (" " + terbilang(n - 100) if n > 100 else "")
    if n < 1000:
        return _SATUAN[n // 100] + " ratus" + (" " + terbilang(n % 100) if n % 100 else "")
    if n < 2000:
        return "seribu" + (" " + terbilang(n - 1000) if n > 1000 else "")
    if n < 1_000_000:
        return terbilang(n // 1000) + " ribu" + (" " + terbilang(n % 1000) if n % 1000 else "")
    return str(n)
