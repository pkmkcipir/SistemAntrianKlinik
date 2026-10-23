"""Halaman data: Pasien, Keuangan, dan Obat (stok & mutasi)."""
import sqlite3

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (QDateEdit, QHBoxLayout, QInputDialog, QLineEdit, QTabWidget, QVBoxLayout,
                               QWidget)

from .config import angka, fmt_date, rupiah, umur
from .widgets import (SummaryBar, ask, ask_form, button, fill_table, info, label, make_table, pasien_items,
                      selected_id, warn)

PASIEN_FIELDS = [
    ("nama", "Nama lengkap *", "text"),
    ("nik", "NIK", "text"),
    ("jk", "Jenis kelamin", "combo", ["Perempuan", "Laki-laki"]),
    ("tgl_lahir", "Tanggal lahir (hh-bb-tttt)", "date_text"),
    ("telepon", "Telepon / WhatsApp", "text"),
    ("penjamin", "Penjamin", "combo", ["Umum", "BPJS", "Asuransi", "Lainnya"]),
    ("alamat", "Alamat", "multi"),
    ("catatan", "Catatan", "multi"),
]
KAT_MASUK = ["Pemeriksaan", "Tindakan", "Persalinan", "Imunisasi", "KB", "Obat", "Pendaftaran", "Lainnya"]
KAT_KELUAR = ["Pembelian Obat", "Alat & Bahan Medis", "Gaji & Jasa", "Listrik & Air", "Operasional", "Lainnya"]
METODE = ["Tunai", "Transfer", "QRIS", "BPJS / Klaim", "Asuransi"]


def _tanggal_edit(awal: QDate):
    de = QDateEdit(awal)
    de.setCalendarPopup(True)
    de.setDisplayFormat("dd-MM-yyyy")
    return de


def _iso(de):
    return de.date().toString("yyyy-MM-dd")


class PatientPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx, self.db = ctx, ctx.db
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 8)
        top = QHBoxLayout()
        self.ed_cari = QLineEdit()
        self.ed_cari.setPlaceholderText("Cari nama, No. RM, NIK, atau telepon")
        self.ed_cari.setClearButtonEnabled(True)
        self.ed_cari.textChanged.connect(self.refresh)
        top.addWidget(self.ed_cari, 1)
        top.addWidget(button("+ Pasien baru", slot=self.add))
        top.addWidget(button("Ubah", "soft", self.edit))
        top.addWidget(button("Daftarkan ke antrian", "soft", self.to_queue))
        top.addWidget(button("Hapus", "danger", self.delete))
        lay.addLayout(top)
        self.table = make_table(["No. RM", "Nama", "NIK", "JK", "Umur", "Telepon", "Penjamin", "Alamat"], stretch=7)
        self.table.doubleClicked.connect(lambda _i: self.edit())
        lay.addWidget(self.table, 1)
        self.lbl = label("", "muted")
        lay.addWidget(self.lbl)

    def refresh(self):
        rows = self.db.pasien_cari(self.ed_cari.text(), 1000)
        jk = {"Laki-laki": "L", "Perempuan": "P"}
        fill_table(self.table, [[p["no_rm"], p["nama"], p["nik"], jk.get(p["jk"], ""), umur(p["tgl_lahir"]),
                                 p["telepon"], p["penjamin"], p["alamat"].replace("\n", " ")] for p in rows],
                   ids=[p["id"] for p in rows])
        total = self.db.one("SELECT COUNT(*) AS n FROM pasien")["n"]
        self.lbl.setText(f"Menampilkan {len(rows)} dari {angka(total)} pasien terdaftar")

    def _simpan(self, d, id=None):
        try:
            self.db.pasien_save(d, id)
        except sqlite3.IntegrityError as e:
            warn(self, f"Data tidak dapat disimpan: {e}")
            return
        self.refresh()
        self.ctx.notify_data_changed()

    def add(self):
        d = ask_form(self, "Pasien baru", PASIEN_FIELDS, required=("nama",))
        if d:
            self._simpan(d)

    def edit(self):
        pid = selected_id(self.table)
        if pid is None:
            info(self, "Pilih pasien di tabel terlebih dahulu.")
            return
        d = ask_form(self, "Ubah data pasien", PASIEN_FIELDS, dict(self.db.pasien_get(pid)), required=("nama",))
        if d:
            self._simpan(d, pid)

    def delete(self):
        pid = selected_id(self.table)
        if pid is None:
            info(self, "Pilih pasien di tabel terlebih dahulu.")
            return
        p = self.db.pasien_get(pid)
        if ask(self, f"Hapus data pasien {p['nama']} ({p['no_rm']})?\nRiwayat antrian dan keuangan tetap tersimpan "
                     "tanpa nama pasien."):
            self.db.pasien_del(pid)
            self.refresh()
            self.ctx.notify_data_changed()

    def to_queue(self):
        pid = selected_id(self.table)
        if pid is None:
            info(self, "Pilih pasien di tabel terlebih dahulu.")
            return
        polis = self.db.poli_list()
        if not polis:
            warn(self, "Belum ada layanan aktif. Tambahkan di menu Pengaturan.")
            return
        nama, ok = QInputDialog.getItem(self, "Daftarkan ke antrian", "Pilih layanan:",
                                        [f"{p['kode']} — {p['nama']}" for p in polis], 0, False)
        if ok:
            t = self.db.tiket_ambil(polis[[f"{p['kode']} — {p['nama']}" for p in polis].index(nama)]["id"], pid)
            self.ctx.notify_data_changed()
            self.ctx.print_ticket(t)
            info(self, f"Nomor antrian: {t['kode']}\nLayanan: {t['poli_nama']}")


class FinancePage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx, self.db = ctx, ctx.db
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 8)
        top = QHBoxLayout()
        hari = QDate.currentDate()
        self.de_a, self.de_b = _tanggal_edit(QDate(hari.year(), hari.month(), 1)), _tanggal_edit(hari)
        for de in (self.de_a, self.de_b):
            de.dateChanged.connect(self.refresh)
        top.addWidget(label("Dari"))
        top.addWidget(self.de_a)
        top.addWidget(label("sampai"))
        top.addWidget(self.de_b)
        top.addStretch()
        top.addWidget(button("+ Pemasukan", slot=lambda: self.add("Pemasukan")))
        top.addWidget(button("+ Pengeluaran", "soft", lambda: self.add("Pengeluaran")))
        top.addWidget(button("Ubah", "soft", self.edit))
        top.addWidget(button("Hapus", "danger", self.delete))
        lay.addLayout(top)
        self.summary = SummaryBar()
        lay.addWidget(self.summary)
        self.table = make_table(["Tanggal", "Tipe", "Kategori", "Keterangan", "Pasien", "Metode", "Jumlah"], stretch=3)
        self.table.doubleClicked.connect(lambda _i: self.edit())
        lay.addWidget(self.table, 1)

    def refresh(self):
        rows = self.db.keu_list(_iso(self.de_a), _iso(self.de_b))
        masuk = sum(r["jumlah"] for r in rows if r["tipe"] == "Pemasukan")
        keluar = sum(r["jumlah"] for r in rows if r["tipe"] == "Pengeluaran")
        self.summary.set_items([("Pemasukan", rupiah(masuk)), ("Pengeluaran", rupiah(keluar)),
                                ("Saldo", rupiah(masuk - keluar)), ("Transaksi", angka(len(rows)))])
        fill_table(self.table, [[fmt_date(r["tanggal"]), r["tipe"], r["kategori"], r["keterangan"],
                                 r["pasien_nama"] or "", r["metode"], rupiah(r["jumlah"])] for r in rows],
                   ids=[r["id"] for r in rows], right=(6,))

    def _fields(self, tipe):
        return [("tanggal", "Tanggal", "date"),
                ("kategori", "Kategori", "combo_edit", KAT_MASUK if tipe == "Pemasukan" else KAT_KELUAR),
                ("keterangan", "Keterangan", "text"),
                ("jumlah", "Jumlah", "money"),
                ("metode", "Metode bayar", "combo", METODE),
                ("pasien_id", "Pasien (opsional)", "combo_search", pasien_items(self.db))]

    def _simpan(self, tipe, d, id=None):
        if d["jumlah"] <= 0:
            warn(self, "Jumlah harus lebih dari 0.")
            return
        self.db.keu_save({**d, "tipe": tipe}, id)
        self.refresh()
        self.ctx.notify_data_changed()

    def add(self, tipe):
        d = ask_form(self, f"Tambah {tipe.lower()}", self._fields(tipe))
        if d:
            self._simpan(tipe, d)

    def edit(self):
        kid = selected_id(self.table)
        if kid is None:
            info(self, "Pilih transaksi di tabel terlebih dahulu.")
            return
        r = self.db.keu_get(kid)
        d = ask_form(self, f"Ubah {r['tipe'].lower()}", self._fields(r["tipe"]), dict(r))
        if d:
            self._simpan(r["tipe"], d, kid)

    def delete(self):
        kid = selected_id(self.table)
        if kid is None:
            info(self, "Pilih transaksi di tabel terlebih dahulu.")
            return
        if ask(self, "Hapus transaksi yang dipilih?"):
            self.db.keu_del(kid)
            self.refresh()
            self.ctx.notify_data_changed()


class MedicinePage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx, self.db = ctx, ctx.db
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 8)
        tabs = QTabWidget()
        lay.addWidget(tabs)

        # ---- daftar obat ----
        t1 = QWidget()
        l1 = QVBoxLayout(t1)
        row = QHBoxLayout()
        self.ed_cari = QLineEdit()
        self.ed_cari.setPlaceholderText("Cari nama atau kode obat")
        self.ed_cari.setClearButtonEnabled(True)
        self.ed_cari.textChanged.connect(self.refresh)
        row.addWidget(self.ed_cari, 1)
        row.addWidget(button("+ Obat baru", slot=self.add_obat))
        row.addWidget(button("Ubah", "soft", self.edit_obat))
        l1.addLayout(row)
        self.t_obat = make_table(["Kode", "Nama obat", "Satuan", "Harga jual", "Stok", "Stok min", "Status"], stretch=1)
        self.t_obat.doubleClicked.connect(lambda _i: self.edit_obat())
        l1.addWidget(self.t_obat)
        tabs.addTab(t1, "Daftar obat")

        # ---- mutasi stok ----
        t2 = QWidget()
        l2 = QVBoxLayout(t2)
        row2 = QHBoxLayout()
        hari = QDate.currentDate()
        self.de_a, self.de_b = _tanggal_edit(QDate(hari.year(), hari.month(), 1)), _tanggal_edit(hari)
        for de in (self.de_a, self.de_b):
            de.dateChanged.connect(self.refresh)
        row2.addWidget(label("Dari"))
        row2.addWidget(self.de_a)
        row2.addWidget(label("sampai"))
        row2.addWidget(self.de_b)
        row2.addStretch()
        row2.addWidget(button("+ Obat masuk", slot=lambda: self.mutasi("Masuk")))
        row2.addWidget(button("− Obat keluar", "soft", lambda: self.mutasi("Keluar")))
        row2.addWidget(button("± Koreksi stok", "soft", lambda: self.mutasi("Koreksi")))
        l2.addLayout(row2)
        self.t_mut = make_table(["Tanggal", "Obat", "Tipe", "Jumlah", "Keterangan", "Pasien"], stretch=4)
        l2.addWidget(self.t_mut)
        tabs.addTab(t2, "Mutasi stok")

    def refresh(self):
        rows = self.db.obat_list(self.ed_cari.text())
        data = []
        for o in rows:
            status = ("Nonaktif" if not o["aktif"] else "Habis" if o["stok"] <= 0
                      else "Menipis" if o["stok"] <= o["stok_min"] else "Aman")
            data.append([o["kode"], o["nama"], o["satuan"], rupiah(o["harga_jual"]), angka(o["stok"]),
                         angka(o["stok_min"]), status])
        fill_table(self.t_obat, data, ids=[o["id"] for o in rows], right=(3, 4, 5))
        mut = self.db.mutasi_list(_iso(self.de_a), _iso(self.de_b))
        fill_table(self.t_mut, [[fmt_date(m["tanggal"]), m["obat_nama"], m["tipe"],
                                 f"{m['delta']:+d} {m['satuan']}", m["keterangan"], m["pasien_nama"] or ""]
                                for m in mut], right=(3,))

    def _obat_fields(self, baru):
        f = [("kode", "Kode (kosong = otomatis)", "text"), ("nama", "Nama obat *", "text"),
             ("satuan", "Satuan", "combo_edit",
              ["Tablet", "Kapsul", "Strip", "Botol", "Tube", "Sachet", "Ampul", "Vial", "Pcs"]),
             ("harga_jual", "Harga jual / satuan", "money"), ("stok_min", "Stok minimum", "int")]
        return f + [("stok_awal", "Stok awal", "int")] if baru else f + [("aktif", "Aktif", "check")]

    def _simpan_obat(self, d, id=None):
        try:
            self.db.obat_save(d, id, d.get("stok_awal", 0))
        except sqlite3.IntegrityError:
            warn(self, "Kode obat sudah dipakai. Gunakan kode lain.")
            return
        self.refresh()

    def add_obat(self):
        d = ask_form(self, "Obat baru", self._obat_fields(True), required=("nama",))
        if d:
            self._simpan_obat(d)

    def edit_obat(self):
        oid = selected_id(self.t_obat)
        if oid is None:
            info(self, "Pilih obat di tabel terlebih dahulu.")
            return
        d = ask_form(self, "Ubah data obat", self._obat_fields(False), dict(self.db.obat_get(oid)), required=("nama",))
        if d:
            self._simpan_obat(d, oid)

    def mutasi(self, tipe):
        obats = self.db.obat_list(aktif_only=True)
        if not obats:
            warn(self, "Tambahkan data obat terlebih dahulu di tab Daftar obat.")
            return
        items = [(f"{o['nama']} (stok {o['stok']} {o['satuan']})", o["id"]) for o in obats]
        f = [("tanggal", "Tanggal", "date"), ("obat_id", "Obat *", "combo_search", items)]
        if tipe == "Masuk":
            f += [("jumlah", "Jumlah masuk", "int", (1, 1_000_000)),
                  ("total", "Biaya pembelian (0 = tidak dicatat)", "money"),
                  ("keterangan", "Keterangan / supplier", "text")]
        elif tipe == "Keluar":
            f += [("jumlah", "Jumlah keluar", "int", (1, 1_000_000)),
                  ("pasien_id", "Pasien (opsional)", "combo_search", pasien_items(self.db)),
                  ("total", "Total harga (0 = tidak dicatat)", "money"),
                  ("keterangan", "Keterangan", "text")]
        else:
            f += [("jumlah", "Selisih (+ tambah, − kurang)", "int", (-1_000_000, 1_000_000)),
                  ("keterangan", "Alasan koreksi *", "text")]
        judul = {"Masuk": "Obat masuk", "Keluar": "Obat keluar", "Koreksi": "Koreksi stok"}[tipe]
        d = ask_form(self, judul, f, required=("obat_id",) + (("keterangan",) if tipe == "Koreksi" else ()))
        if not d:
            return
        try:
            self.db.mutasi_add(d["obat_id"], d["tanggal"], tipe, d["jumlah"], d.get("keterangan", ""),
                               d.get("pasien_id"), d.get("total", 0))
        except ValueError as e:
            warn(self, str(e))
            return
        self.refresh()
        self.ctx.notify_data_changed()
