"""Halaman Laporan dan Video Edukasi."""
import os
from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QComboBox, QDateEdit, QFileDialog, QHBoxLayout, QProgressDialog,
                               QTabWidget, QVBoxLayout, QWidget)

from .config import data_dir
from .reports import export_pdf, export_xlsx, format_cell, kop, laporan
from .widgets import SummaryBar, ask, button, fill_table, info, label, make_table, selected_id, warn


def _folder_dokumen() -> Path:
    d = Path.home() / "Documents"
    return d if d.exists() else Path.home()


# =============================================================================
# Laporan
# =============================================================================
class ReportPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx, self.db, self.rep = ctx, ctx.db, None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 8)
        top = QHBoxLayout()
        self.cb_jenis, self.cb_per = QComboBox(), QComboBox()
        self.cb_jenis.addItems(["Keuangan", "Obat"])
        self.cb_per.addItems(["Mingguan", "Bulanan"])
        self.de = QDateEdit(QDate.currentDate())
        self.de.setCalendarPopup(True)
        self.de.setDisplayFormat("dd-MM-yyyy")
        for w in (self.cb_jenis, self.cb_per):
            w.currentIndexChanged.connect(self.refresh)
        self.de.dateChanged.connect(self.refresh)
        top.addWidget(label("Laporan"))
        top.addWidget(self.cb_jenis)
        top.addWidget(self.cb_per)
        top.addWidget(button("◀", "soft", lambda: self.geser(-1)))
        top.addWidget(self.de)
        top.addWidget(button("▶", "soft", lambda: self.geser(1)))
        top.addStretch()
        top.addWidget(button("Ekspor Excel", slot=self.to_xlsx))
        top.addWidget(button("Ekspor PDF", "soft", self.to_pdf))
        lay.addLayout(top)
        self.lbl = label("", "h2")
        lay.addWidget(self.lbl)
        self.summary = SummaryBar()
        lay.addWidget(self.summary)
        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)

    def geser(self, step):
        d = self.de.date()
        self.de.setDate(d.addDays(7 * step) if self.cb_per.currentText() == "Mingguan" else d.addMonths(step))

    def refresh(self):
        a = self.de.date()
        self.rep = rep = laporan(self.db, self.cb_jenis.currentText(), self.cb_per.currentText(),
                                 date(a.year(), a.month(), a.day()))
        self.lbl.setText(f"{rep['judul']} — {rep['periode']}")
        self.summary.set_items(rep["ringkasan"])
        while self.tabs.count():
            w = self.tabs.widget(0)
            self.tabs.removeTab(0)
            w.deleteLater()
        for t in rep["tabel"]:
            kolom = t["kolom"]
            lebar = {i: max([len(str(r[i])) for r in t["baris"]] or [0])
                     for i, (_n, j) in enumerate(kolom) if j == "teks"}
            tbl = make_table([n for n, _ in kolom], stretch=max(lebar, key=lebar.get) if lebar else None)
            fill_table(tbl, [[format_cell(v, j) for v, (_n, j) in zip(r, kolom)] for r in t["baris"]],
                       right=tuple(i for i, (_n, j) in enumerate(kolom) if j != "teks"),
                       bold_last=bool(t.get("total")))
            self.tabs.addTab(tbl, t["judul"])

    def _simpan(self, ext, filt, fn):
        if not self.rep:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Simpan laporan",
                                              str(_folder_dokumen() / f"{self.rep['nama_file']}.{ext}"), filt)
        if not path:
            return
        try:
            fn(self.rep, path, kop(self.db))
        except Exception as e:  # file sedang dibuka di Excel, folder tidak bisa ditulis, dll.
            warn(self, f"Laporan gagal disimpan:\n{e}")
            return
        if ask(self, "Laporan berhasil disimpan.\nBuka file sekarang?"):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def to_xlsx(self):
        self._simpan("xlsx", "Excel (*.xlsx)", export_xlsx)

    def to_pdf(self):
        self._simpan("pdf", "PDF (*.pdf)", export_pdf)


# =============================================================================
# Video edukasi
# =============================================================================
def _path_unik(path: Path) -> Path:
    n, p = 1, path
    while p.exists():
        p = path.with_name(f"{path.stem}-{n}{path.suffix}")
        n += 1
    return p


def _salin(parent, src, dst) -> bool:
    """Salin file besar dengan progress. False bila dibatalkan."""
    total, selesai, batal = max(os.path.getsize(src), 1), 0, False
    dlg = QProgressDialog(f"Menyalin {Path(src).name} ...", "Batal", 0, 100, parent)
    dlg.setWindowTitle("Menambahkan video")
    dlg.setWindowModality(Qt.WindowModality.WindowModal)
    dlg.setMinimumDuration(200)
    with open(src, "rb") as fi, open(dst, "wb") as fo:
        while True:
            buf = fi.read(4 * 1024 * 1024)
            if not buf:
                break
            fo.write(buf)
            selesai += len(buf)
            dlg.setValue(int(selesai * 100 / total))
            QApplication.processEvents()
            if dlg.wasCanceled():
                batal = True
                break
    dlg.close()
    if batal:
        Path(dst).unlink(missing_ok=True)
    return not batal


class VideoPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx, self.db, self._filling = ctx, ctx.db, False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 8)
        top = QHBoxLayout()
        top.addWidget(button("+ Tambah video", slot=self.add))
        top.addWidget(button("▲ Naik", "soft", lambda: self.pindah(-1)))
        top.addWidget(button("▼ Turun", "soft", lambda: self.pindah(1)))
        top.addStretch()
        top.addWidget(button("Hapus", "danger", self.delete))
        lay.addLayout(top)
        lay.addWidget(label("Video diputar berurutan dan berulang di layar antrian selama pasien menunggu. "
                            "Centang kolom Aktif untuk menayangkan. Format paling aman: MP4 (H.264 + AAC). "
                            "File disalin ke folder data aplikasi, jadi aman jika flashdisk dicabut.",
                            "muted", wrap=True))
        self.table = make_table(["Aktif", "Judul", "File", "Ukuran", "Status"], stretch=1)
        self.table.itemChanged.connect(self._toggled)
        lay.addWidget(self.table, 1)

    def refresh(self):
        self._filling = True
        rows = self.db.video_list()
        data = []
        for v in rows:
            p = Path(v["path"])
            ada = p.exists()
            data.append(["", v["judul"], p.name, f"{p.stat().st_size / 1_048_576:.1f} MB" if ada else "-",
                         "Siap diputar" if ada else "File tidak ditemukan"])
        fill_table(self.table, data, ids=[v["id"] for v in rows], right=(3,))
        for r, v in enumerate(rows):
            it = self.table.item(r, 0)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if v["aktif"] else Qt.CheckState.Unchecked)
        self._filling = False

    def _toggled(self, it):
        if self._filling or it.column() != 0:
            return
        self.db.video_aktif(it.data(Qt.ItemDataRole.UserRole), it.checkState() == Qt.CheckState.Checked)
        self.ctx.notify_videos_changed()

    def add(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Pilih video edukasi", "", "Video (*.mp4 *.mkv *.avi *.mov *.wmv *.webm *.m4v);;Semua file (*.*)")
        for src in files:
            dst = _path_unik(data_dir() / "videos" / Path(src).name)
            try:
                if not _salin(self, src, dst):
                    break
            except OSError as e:
                warn(self, f"Video tidak dapat disalin:\n{e}")
                break
            self.db.video_add(Path(src).stem, str(dst))
        if files:
            self.refresh()
            self.ctx.notify_videos_changed()

    def delete(self):
        vid = selected_id(self.table)
        if vid is None:
            info(self, "Pilih video di tabel terlebih dahulu.")
            return
        if not ask(self, "Hapus video ini dari daftar tayang?"):
            return
        v = next(r for r in self.db.video_list() if r["id"] == vid)
        self.db.video_del(vid)
        try:
            p = Path(v["path"])
            if p.parent.resolve() == (data_dir() / "videos").resolve():
                p.unlink(missing_ok=True)
        except OSError:
            pass
        self.refresh()
        self.ctx.notify_videos_changed()

    def pindah(self, step):
        vid = selected_id(self.table)
        if vid is None:
            return
        self.db.video_move(vid, step)
        self.refresh()
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0).data(Qt.ItemDataRole.UserRole) == vid:
                self.table.selectRow(r)
        self.ctx.notify_videos_changed()
