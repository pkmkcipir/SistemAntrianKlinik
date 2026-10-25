"""Tiket nomor antrian: tata letak dan pencetakan.

Ukuran kertas mengikuti jenis tiket: thermal 58 mm atau 80 mm (tinggi otomatis sesuai isi), A6, atau ukuran
kustom. Semua ukuran dihitung dalam milimeter lalu diubah ke piksel sesuai resolusi printer, jadi hasilnya sama
di printer thermal (203 dpi) maupun printer laser (600 dpi).
"""
from collections import namedtuple

from PySide6.QtCore import QMarginsF, QPointF, QRectF, QSizeF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPageLayout, QPageSize, QPainter, QPen
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo

from .config import COPYRIGHT, fmt_date, fmt_time, now_iso

# kunci: (nama, lebar kertas mm, tinggi kertas mm (0 = otomatis sesuai isi), lebar area cetak mm)
KERTAS = {
    "58": ("Thermal 58 mm", 58, 0, 48),
    "80": ("Thermal 80 mm", 80, 0, 72),
    "a6": ("A6 (105 x 148 mm)", 105, 148, 89),
    "kustom": ("Ukuran kustom", 0, 0, 0),
}
Konfig = namedtuple("Konfig", "lebar tinggi isi nama alamat teks salinan")

FONT_TEKS = ["Segoe UI", "Arial", "Helvetica"]
FONT_ANGKA = ["Bahnschrift", "Segoe UI", "Arial"]


def _angka(v, default, lo, hi):
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


def konfigurasi(db) -> Konfig:
    """Ukuran kertas dan opsi cetak dari menu Pengaturan > Cetak Tiket."""
    k = db.get("kertas")
    if k in ("58", "80", "a6"):
        _nama, lebar, tinggi, isi = KERTAS[k]
    else:
        lebar = _angka(db.get("kertas_w"), 58, 40, 220)
        tinggi = _angka(db.get("kertas_h"), 0, 0, 1000)
        isi = max(lebar - 8, 30)
    return Konfig(lebar, tinggi, isi, db.get("cetak_nama") == "1", db.get("cetak_alamat") == "1",
                  (db.get("teks_karcis") or "").strip(), _angka(db.get("salinan"), 1, 1, 5))


def contoh_tiket(db) -> dict:
    """Tiket contoh untuk pratinjau dan cetak percobaan."""
    p = next(iter(db.poli_list()), None)
    return {"kode": "A013", "poli_nama": p["nama"] if p else "Pemeriksaan Umum",
            "poli_loket": p["loket"] if p else "Ruang Periksa 1", "nama_tampil": "Siti Aminah",
            "no_rm": "RM-000001", "dibuat": now_iso(), "di_depan": 3}


def data_tiket(db, t) -> dict:
    t = dict(t)
    nama = (t.get("nama_tampil") or t.get("nama") or "").strip()
    return {
        "klinik": db.get("nama_klinik") or "", "alamat": db.get("alamat") or "", "telepon": db.get("telepon") or "",
        "kode": t["kode"], "poli": t.get("poli_nama") or "", "ruang": t.get("poli_loket") or "",
        "nama": nama, "rm": t.get("no_rm") or "", "waktu": t.get("dibuat") or "",
        "di_depan": t["di_depan"] if "di_depan" in t else db.jumlah_di_depan(t),
    }


def _susun(p, dpi, x0_mm, lebar_mm, d, cfg, gambar) -> float:
    """Susun isi tiket (dan gambar bila gambar=True). Mengembalikan tinggi isi dalam mm."""
    px = dpi / 25.4
    x0, W = x0_mm * px, lebar_mm * px
    y = 2.5 * px
    hitam = QColor("black")
    tengah = Qt.AlignmentFlag.AlignHCenter.value
    bungkus = Qt.TextFlag.TextWordWrap.value

    def font(mm, tebal=False, angka=False):
        f = QFont()
        f.setFamilies(FONT_ANGKA if angka else FONT_TEKS)
        f.setPixelSize(max(6, round(mm * px)))
        f.setBold(tebal)
        return f

    def teks(text, mm, tebal=False, jeda=0.5):
        nonlocal y
        if not text:
            return
        f = font(mm, tebal)
        flags = tengah | bungkus
        tinggi = QFontMetricsF(f).boundingRect(QRectF(0, 0, W, 100_000), flags, text).height()
        if gambar:
            p.setFont(f)
            p.setPen(hitam)
            p.drawText(QRectF(x0, y, W, tinggi), flags, text)
        y += tinggi + jeda * px

    def garis():
        nonlocal y
        y += 1.0 * px
        if gambar:
            p.setPen(QPen(hitam, max(1.0, 0.3 * px), Qt.PenStyle.DashLine))
            p.drawLine(QPointF(x0, y), QPointF(x0 + W, y))
        y += 2.0 * px

    def angka_besar(text):
        nonlocal y
        mm = 20.0
        while mm > 8 and QFontMetricsF(font(mm, True, True)).horizontalAdvance(text) > W * 0.98:
            mm -= 1
        f = font(mm, True, True)
        tinggi = QFontMetricsF(f).height()
        if gambar:
            p.setFont(f)
            p.setPen(hitam)
            p.drawText(QRectF(x0, y, W, tinggi), tengah | Qt.AlignmentFlag.AlignVCenter.value, text)
        y += tinggi + 1.0 * px

    teks(d["klinik"], 4.2, True)
    if cfg.alamat:
        teks(d["alamat"], 2.5)
    if d["telepon"]:
        teks("Telp/WA " + d["telepon"], 2.7)
    garis()
    teks("Nomor antrian", 3.4)
    angka_besar(d["kode"])
    teks(d["poli"], 4.0, True)
    teks(d["ruang"], 3.0)
    garis()
    waktu = f"{fmt_date(d['waktu'])}  {fmt_time(d['waktu'])}".strip()
    teks(waktu, 2.9)
    n = d["di_depan"]
    teks("Anda antrian berikutnya" if n == 0 else f"Antrian di depan Anda: {n}", 3.1, True)
    if cfg.nama and d["nama"]:
        teks("Nama: " + d["nama"], 2.9)
    garis()
    teks(cfg.teks, 2.6)
    teks(COPYRIGHT, 2.2, jeda=0)
    y += 7.0 * px  # ruang untuk pemotongan/sobekan
    return y / px


def _ukur(d, cfg, dpi) -> float:
    img = QImage(4, 4, QImage.Format.Format_RGB32)
    p = QPainter(img)
    try:
        return _susun(p, dpi, 0, cfg.isi, d, cfg, False)
    finally:
        p.end()


def tinggi_tiket(db, t, dpi=203) -> float:
    """Tinggi kertas (mm) yang dipakai untuk tiket ini."""
    cfg = konfigurasi(db)
    return cfg.tinggi or _ukur(data_tiket(db, t), cfg, dpi)


def render_gambar(db, t, dpi=203) -> QImage:
    """Gambar tiket apa adanya (untuk pratinjau). Lebar dan tinggi mengikuti ukuran kertas."""
    cfg, d = konfigurasi(db), data_tiket(db, t)
    tinggi = cfg.tinggi or _ukur(d, cfg, dpi)
    px = dpi / 25.4
    img = QImage(round(cfg.lebar * px), round(tinggi * px), QImage.Format.Format_RGB32)
    img.fill(QColor("white"))
    img.setDotsPerMeterX(round(dpi / 0.0254))
    img.setDotsPerMeterY(round(dpi / 0.0254))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    _susun(p, dpi, (cfg.lebar - cfg.isi) / 2, cfg.isi, d, cfg, True)
    p.end()
    return img


def daftar_printer():
    """(daftar nama printer, nama printer bawaan Windows)."""
    return QPrinterInfo.availablePrinterNames(), QPrinterInfo.defaultPrinterName()


def cetak(db, t, printer_name=None, pdf_path=None):
    """Cetak tiket ke printer (atau ke file PDF untuk uji tata letak). Mengembalikan (berhasil, pesan)."""
    try:
        cfg, d = konfigurasi(db), data_tiket(db, t)
        if pdf_path:
            pr = QPrinter(QPrinter.PrinterMode.HighResolution)
            pr.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            pr.setOutputFileName(str(pdf_path))
        else:
            nama = printer_name if printer_name is not None else db.get("printer")
            if not nama:
                return False, "Printer belum dipilih (Pengaturan > Cetak Tiket)."
            info = QPrinterInfo.printerInfo(nama)
            if info.isNull():
                return False, f"Printer \"{nama}\" tidak ditemukan. Pilih ulang di Pengaturan > Cetak Tiket."
            pr = QPrinter(info, QPrinter.PrinterMode.HighResolution)
        dpi = pr.resolution()
        tinggi = cfg.tinggi or _ukur(d, cfg, dpi)
        pr.setPageSize(QPageSize(QSizeF(cfg.lebar, tinggi), QPageSize.Unit.Millimeter, "Tiket",
                                 QPageSize.SizeMatchPolicy.ExactMatch))
        pr.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
        pr.setFullPage(True)
        p = QPainter()
        if not p.begin(pr):
            return False, "Printer tidak dapat dimulai. Periksa apakah printer menyala dan terhubung."
        try:
            for i in range(cfg.salinan):
                if i:
                    pr.newPage()
                _susun(p, dpi, (cfg.lebar - cfg.isi) / 2, cfg.isi, d, cfg, True)
        finally:
            p.end()
        return True, ""
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
