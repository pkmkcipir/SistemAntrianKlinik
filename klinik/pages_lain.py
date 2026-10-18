"""Halaman Laporan, Video Edukasi, dan Pengaturan."""
import os
import sqlite3
from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateEdit, QFileDialog, QFormLayout,
                               QHBoxLayout, QLineEdit, QPlainTextEdit, QProgressDialog, QSlider, QTabWidget,
                               QVBoxLayout, QWidget)

from .config import APP_VERSION, COPYRIGHT, data_dir
from .reports import export_pdf, export_xlsx, format_cell, kop, laporan
from .widgets import (SummaryBar, ask, ask_form, button, card, fill_table, info, label, make_table,
                      selected_id, warn)


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


# =============================================================================
# Pengaturan
# =============================================================================
class SettingsPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx, self.db = ctx, ctx.db
        root = QHBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 8)
        root.setSpacing(16)

        left = card()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(18, 16, 18, 16)
        ll.addWidget(label("Identitas klinik dan layar antrian", "h2"))
        self.ed_nama, self.ed_tel = QLineEdit(), QLineEdit()
        self.ed_alamat, self.ed_run = QPlainTextEdit(), QPlainTextEdit()
        self.ed_alamat.setFixedHeight(64)
        self.ed_run.setFixedHeight(84)
        self.sl_vol = QSlider(Qt.Orientation.Horizontal)
        self.sl_vol.setRange(0, 100)
        self.lbl_vol = label("")
        self.sl_vol.valueChanged.connect(lambda v: self.lbl_vol.setText(f"{v}%"))
        vol = QHBoxLayout()
        vol.addWidget(self.sl_vol, 1)
        vol.addWidget(self.lbl_vol)
        self.cb_mon = QComboBox()
        self.chk_suara = QCheckBox("Suara panggilan (bunyi ting-tung dan ucapan nomor)")
        self.chk_auto = QCheckBox("Buka layar antrian otomatis saat aplikasi dimulai (jika ada monitor kedua)")
        form = QFormLayout()
        form.setVerticalSpacing(10)
        for teks, w in (("Nama klinik", self.ed_nama), ("Alamat", self.ed_alamat), ("Telepon / WhatsApp", self.ed_tel),
                        ("Teks berjalan", self.ed_run), ("Volume video", vol), ("Monitor layar antrian", self.cb_mon)):
            form.addRow(teks, w)
        form.addRow(self.chk_suara)
        form.addRow(self.chk_auto)
        ll.addLayout(form)
        row = QHBoxLayout()
        row.addWidget(button("Simpan pengaturan", slot=self.simpan))
        row.addWidget(button("Tes suara", "soft", ctx.test_voice))
        row.addStretch()
        ll.addLayout(row)
        ll.addStretch()
        root.addWidget(left, 5)

        right = QVBoxLayout()
        right.setSpacing(12)
        c2 = card()
        l2 = QVBoxLayout(c2)
        l2.setContentsMargins(18, 16, 18, 16)
        l2.addWidget(label("Layanan / poli", "h2"))
        self.t_poli = make_table(["Kode", "Layanan", "Ruang", "Status"], stretch=1)
        self.t_poli.doubleClicked.connect(lambda _i: self.edit_poli())
        l2.addWidget(self.t_poli, 1)
        row2 = QHBoxLayout()
        row2.addWidget(button("+ Layanan", slot=self.add_poli))
        row2.addWidget(button("Ubah", "soft", self.edit_poli))
        row2.addStretch()
        l2.addLayout(row2)
        right.addWidget(c2, 1)

        c3 = card()
        l3 = QVBoxLayout(c3)
        l3.setContentsMargins(18, 16, 18, 16)
        l3.addWidget(label("Data dan cadangan", "h2"))
        l3.addWidget(label(f"Data tersimpan di: {data_dir()}", "muted", wrap=True))
        row3 = QHBoxLayout()
        row3.addWidget(button("Backup data", slot=self.backup))
        row3.addWidget(button("Pulihkan dari backup", "soft", self.restore))
        row3.addWidget(button("Buka folder data", "soft",
                              lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir())))))
        l3.addLayout(row3)
        l3.addWidget(label(f"Sistem Antrian Klinik v{APP_VERSION}   {COPYRIGHT}", "muted"))
        right.addWidget(c3)
        root.addLayout(right, 4)

    def refresh(self):
        g = self.db.get
        self.ed_nama.setText(g("nama_klinik") or "")
        self.ed_alamat.setPlainText(g("alamat") or "")
        self.ed_tel.setText(g("telepon") or "")
        self.ed_run.setPlainText(g("running_text") or "")
        try:
            self.sl_vol.setValue(int(g("volume_video")))
        except (TypeError, ValueError):
            self.sl_vol.setValue(40)
        self.chk_suara.setChecked(g("suara") == "1")
        self.chk_auto.setChecked(g("buka_otomatis") == "1")
        self.cb_mon.clear()
        self.cb_mon.addItem("Otomatis (monitor kedua jika ada)", "auto")
        for i, s in enumerate(QGuiApplication.screens()):
            self.cb_mon.addItem(f"Monitor {i + 1} ({s.size().width()}×{s.size().height()})", str(i))
        self.cb_mon.setCurrentIndex(max(self.cb_mon.findData(g("monitor")), 0))
        rows = self.db.poli_list(aktif_only=False)
        fill_table(self.t_poli, [[p["kode"], p["nama"], p["loket"], "Aktif" if p["aktif"] else "Nonaktif"]
                                 for p in rows], ids=[p["id"] for p in rows])

    def simpan(self):
        nama = self.ed_nama.text().strip()
        if not nama:
            warn(self, "Nama klinik wajib diisi.")
            return
        for k, v in (("nama_klinik", nama), ("alamat", self.ed_alamat.toPlainText().strip()),
                     ("telepon", self.ed_tel.text().strip()), ("running_text", self.ed_run.toPlainText().strip()),
                     ("volume_video", self.sl_vol.value()), ("monitor", self.cb_mon.currentData()),
                     ("suara", "1" if self.chk_suara.isChecked() else "0"),
                     ("buka_otomatis", "1" if self.chk_auto.isChecked() else "0")):
            self.db.set(k, v)
        self.ctx.notify_settings_changed()
        info(self, "Pengaturan disimpan.")

    # ---- layanan ---------------------------------------------------------------
    @staticmethod
    def _poli_fields():
        return [("kode", "Kode huruf (1-3) *", "text"), ("nama", "Nama layanan *", "text"),
                ("loket", "Ruang / loket", "text"), ("aktif", "Aktif", "check")]

    def _simpan_poli(self, d, id=None):
        if not d["kode"].isalpha() or len(d["kode"]) > 3:
            warn(self, "Kode harus berupa 1 sampai 3 huruf, misalnya A.")
            return
        try:
            self.db.poli_save(d, id)
        except sqlite3.IntegrityError:
            warn(self, "Kode huruf sudah dipakai layanan lain.")
            return
        self.refresh()
        self.ctx.notify_data_changed()

    def add_poli(self):
        d = ask_form(self, "Layanan baru", self._poli_fields(), {"aktif": True}, required=("kode", "nama"))
        if d:
            self._simpan_poli(d)

    def edit_poli(self):
        pid = selected_id(self.t_poli)
        if pid is None:
            info(self, "Pilih layanan di tabel terlebih dahulu.")
            return
        p = next(r for r in self.db.poli_list(aktif_only=False) if r["id"] == pid)
        d = ask_form(self, "Ubah layanan", self._poli_fields(), dict(p), required=("kode", "nama"))
        if d:
            self._simpan_poli(d, pid)

    # ---- backup ----------------------------------------------------------------
    def backup(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan backup data", str(_folder_dokumen() / f"backup-klinik-{date.today():%Y%m%d}.db"),
            "Database (*.db)")
        if not path:
            return
        try:
            self.db.backup(path)
        except Exception as e:
            warn(self, f"Backup gagal:\n{e}")
            return
        info(self, f"Backup tersimpan:\n{path}")

    def restore(self):
        path, _ = QFileDialog.getOpenFileName(self, "Pilih file backup", str(_folder_dokumen()), "Database (*.db)")
        if not path or not ask(self, "Semua data saat ini akan diganti dengan isi file backup.\nLanjutkan?"):
            return
        try:
            self.db.restore(path)
        except Exception as e:
            warn(self, f"Pemulihan gagal:\n{e}")
            return
        self.refresh()
        self.ctx.notify_all()
        info(self, "Data berhasil dipulihkan.")
