"""Halaman Antrian: ambil nomor + panel operator (panggil, ulang, lewati, selesai)."""
from PySide6.QtCore import QStringListModel, Qt
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QCompleter, QGridLayout, QHBoxLayout, QLineEdit, QPushButton,
                               QVBoxLayout, QWidget)

from .config import fmt_time
from .widgets import ask, button, card, fill_table, info, label, make_table, selected_id

STATUS = {"menunggu": "Menunggu", "dipanggil": "Dipanggil", "selesai": "Selesai",
          "lewat": "Dilewati", "batal": "Batal"}
WARNA = {"menunggu": "#b45309", "dipanggil": "#0e6b67", "selesai": "#64748b",
         "lewat": "#c2410c", "batal": "#94a3b8"}


class PoliButton(QPushButton):
    """Tombol ambil nomor: kode besar, nama layanan (boleh 2 baris), dan jumlah yang menunggu."""

    def __init__(self, kode, nama):
        super().__init__()
        self.setObjectName("poliBtn")
        self.setMinimumHeight(112)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(0)
        self.jml = label("", "poliJml")
        for w in (label(kode, "poliKode"), label(nama, "poliNama", wrap=True), self.jml):
            w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            lay.addWidget(w)

    def set_jumlah(self, n):
        self.jml.setText(f"{n} menunggu")


class QueuePage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx, self.db = ctx, ctx.db
        self._sig, self._polis, self.btns, self.pasien_map = None, {}, {}, {}
        self._last_id = None

        root = QHBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 8)
        root.setSpacing(16)

        # ---- kiri: ambil nomor ----
        left = card()
        left.setFixedWidth(400)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(18, 16, 18, 16)
        ll.setSpacing(10)
        ll.addWidget(label("Ambil nomor antrian", "h2"))
        ll.addWidget(label("Pilih layanan di bawah. Kolom pasien boleh dikosongkan untuk pasien baru. "
                           "Tiket nomor dicetak otomatis bila printer sudah diatur di Pengaturan.",
                           "muted", wrap=True))
        self.ed_pasien = QLineEdit()
        self.ed_pasien.setPlaceholderText("Cari pasien (nama atau No. RM)")
        self.ed_pasien.setClearButtonEnabled(True)
        self.completer = QCompleter(self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.ed_pasien.setCompleter(self.completer)
        ll.addWidget(self.ed_pasien)
        self.grid = QGridLayout()
        self.grid.setSpacing(10)
        ll.addLayout(self.grid)
        ll.addSpacing(6)
        self.lbl_last = label("", "big", wrap=True)
        ll.addWidget(self.lbl_last)
        ll.addWidget(button("Cetak ulang tiket terakhir", "soft", self.cetak_terakhir))
        ll.addStretch()
        root.addWidget(left)

        # ---- kanan: operator ----
        right = QVBoxLayout()
        right.setSpacing(12)
        ctl = card()
        cl = QGridLayout(ctl)
        cl.setContentsMargins(18, 14, 18, 14)
        cl.setHorizontalSpacing(10)
        cl.setVerticalSpacing(10)
        self.cb_poli = QComboBox()
        self.ed_loket = QLineEdit()
        self.ed_loket.setPlaceholderText("Ruang / loket")
        cl.addWidget(label("Layanan"), 0, 0)
        cl.addWidget(self.cb_poli, 0, 1)
        cl.addWidget(label("Ruang"), 0, 2)
        cl.addWidget(self.ed_loket, 0, 3)
        cl.setColumnStretch(1, 1)
        cl.setColumnStretch(3, 1)
        self.lbl_now = label("", "h2")
        cl.addWidget(self.lbl_now, 1, 0, 1, 4)
        btns = QHBoxLayout()
        self.btn_next = button("Panggil berikutnya", slot=self.call_next)
        self.btn_next.setMinimumHeight(44)
        btns.addWidget(self.btn_next, 2)
        btns.addWidget(button("Panggil ulang", "soft", self.recall), 1)
        btns.addWidget(button("Selesai", "soft", lambda: self.finish("selesai")), 1)
        btns.addWidget(button("Lewati", "soft", lambda: self.finish("lewat")), 1)
        cl.addLayout(btns, 2, 0, 1, 4)
        right.addWidget(ctl)

        self.table = make_table(["No.", "Pasien", "Diambil", "Dipanggil", "Status", "Ruang"], stretch=1)
        self.table.doubleClicked.connect(lambda _i: self.call_selected())
        right.addWidget(self.table, 1)
        # Ctrl/Shift + klik memilih beberapa nomor sekaligus (untuk dihapus)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self.table, activated=self.hapus_terpilih,
                  context=Qt.ShortcutContext.WidgetShortcut)
        row = QHBoxLayout()
        row.addWidget(button("Panggil nomor terpilih", "soft", self.call_selected))
        row.addWidget(button("Cetak tiket nomor terpilih", "soft", self.cetak_terpilih))
        row.addStretch()
        right.addLayout(row)
        row2 = QHBoxLayout()
        row2.addWidget(button("Batalkan nomor", "danger", self.cancel_selected))
        row2.addWidget(button("Hapus terpilih", "danger", self.hapus_terpilih))
        row2.addWidget(button("Hapus semua", "danger", self.hapus_semua))
        row2.addStretch()
        right.addLayout(row2)
        root.addLayout(right, 1)

        self.cb_poli.currentIndexChanged.connect(self._poli_changed)

    # ---- data ------------------------------------------------------------------
    def refresh(self):
        polis = self.db.poli_list()
        sig = [(p["id"], p["kode"], p["nama"]) for p in polis]
        if sig != self._sig:
            self._sig = sig
            self._build(polis)
        rows = self.db.pasien_cari("", 2000)
        self.pasien_map = {f"{p['no_rm']} · {p['nama']}": p["id"] for p in rows}
        self.completer.setModel(QStringListModel(list(self.pasien_map), self.completer))
        self.refresh_data()

    def refresh_data(self):
        hitung = self.db.hitung_menunggu()
        for pid, btn in self.btns.items():
            btn.set_jumlah(hitung.get(pid, 0))
        self._load_table()

    def _build(self, polis):
        self._polis = {p["id"]: p for p in polis}
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.deleteLater()
        self.btns = {}
        for i, p in enumerate(polis):
            b = PoliButton(p["kode"], p["nama"])
            b.clicked.connect(lambda _=False, pid=p["id"]: self.take(pid))
            self.grid.addWidget(b, i // 2, i % 2)
            self.btns[p["id"]] = b
        cur = self.cb_poli.currentData()
        self.cb_poli.blockSignals(True)
        self.cb_poli.clear()
        for p in polis:
            self.cb_poli.addItem(f"{p['kode']} — {p['nama']}", p["id"])
        self.cb_poli.setCurrentIndex(max(self.cb_poli.findData(cur), 0))
        self.cb_poli.blockSignals(False)
        self._poli_changed()

    def _poli_changed(self):
        p = self._polis.get(self.cb_poli.currentData())
        self.ed_loket.setText(p["loket"] if p else "")
        self._load_table()

    def _load_table(self):
        pid = self.cb_poli.currentData()
        if pid is None:
            fill_table(self.table, [])
            return
        rows = self.db.tiket_hari(pid)
        data = [[t["kode"], (t["nama_tampil"] or "") + (f"  ({t['no_rm']})" if t["no_rm"] else ""),
                 fmt_time(t["dibuat"]), fmt_time(t["dipanggil"]), STATUS[t["status"]], t["loket"]] for t in rows]
        fill_table(self.table, data, ids=[t["id"] for t in rows])
        for r, t in enumerate(rows):
            self.table.item(r, 4).setForeground(QColor(WARNA[t["status"]]))
        a = self.db.tiket_aktif(pid, self._loket())
        self.lbl_now.setText(f"Sedang dipanggil: {a['kode']}" if a else "Belum ada nomor yang sedang dipanggil")

    def _loket(self):
        return self.ed_loket.text().strip()

    # ---- aksi ------------------------------------------------------------------
    def take(self, poli_id):
        txt = self.ed_pasien.text().strip()
        pid = self.pasien_map.get(txt)
        t = self.db.tiket_ambil(poli_id, pid, "" if pid else txt)
        self._last_id = t["id"]
        self.lbl_last.setText(f"Nomor antrian: {t['kode']}\n{t['poli_nama']}")
        self.ed_pasien.clear()
        self.refresh_data()
        self.ctx.notify_data_changed()
        self.ctx.print_ticket(t)  # tiket diberikan ke pasien sebelum dipanggil

    def cetak_terakhir(self):
        if self._last_id is None:
            info(self, "Belum ada nomor yang diambil.")
            return
        self.ctx.print_ticket(self.db.tiket(self._last_id), manual=True)

    def cetak_terpilih(self):
        tid = selected_id(self.table)
        if tid is None:
            info(self, "Pilih nomor di tabel terlebih dahulu.")
            return
        self.ctx.print_ticket(self.db.tiket(tid), manual=True)

    def _after_call(self, t):
        self.ctx.announce(t)
        self.refresh_data()

    def call_next(self):
        t = self.db.panggil_berikut(self.cb_poli.currentData(), self._loket())
        if t is None:
            info(self, "Tidak ada antrian yang menunggu di layanan ini.")
            return
        self._after_call(t)

    def recall(self):
        t = self.db.panggil_ulang(self.cb_poli.currentData(), self._loket())
        if t is None:
            info(self, "Belum ada nomor yang sedang dipanggil di layanan dan ruang ini.")
            return
        self._after_call(t)

    def finish(self, status):
        t = self.db.tiket_aktif(self.cb_poli.currentData(), self._loket())
        if t is None:
            info(self, "Belum ada nomor yang sedang dipanggil di layanan dan ruang ini.")
            return
        self.db.tiket_status(t["id"], status)
        self.refresh_data()
        self.ctx.notify_data_changed()

    def call_selected(self):
        tid = selected_id(self.table)
        if tid is None:
            info(self, "Pilih nomor di tabel terlebih dahulu.")
            return
        self._after_call(self.db.panggil_tiket(tid, self._loket()))

    def _terpilih(self):
        """[(id, kode)] untuk semua baris yang dipilih di tabel (urut dari atas)."""
        baris = sorted({i.row() for i in self.table.selectionModel().selectedRows()})
        if not baris and self.table.currentRow() >= 0:
            baris = [self.table.currentRow()]
        return [(self.table.item(r, 0).data(Qt.ItemDataRole.UserRole), self.table.item(r, 0).text()) for r in baris]

    def hapus_terpilih(self):
        pilih = self._terpilih()
        if not pilih:
            info(self, "Pilih nomor di tabel terlebih dahulu (Ctrl atau Shift + klik untuk memilih beberapa).")
            return
        daftar = ", ".join(k for _i, k in pilih[:8]) + (" ..." if len(pilih) > 8 else "")
        if not ask(self, f"Hapus {len(pilih)} nomor antrian ({daftar}) secara permanen?\n\n"
                         "Nomor yang dihapus tidak bisa dikembalikan. Jika nomor paling akhir yang dihapus, "
                         "nomor itu akan dipakai lagi oleh pasien berikutnya."):
            return
        self.db.tiket_hapus([i for i, _k in pilih])
        self.refresh_data()
        self.ctx.notify_data_changed()

    def hapus_semua(self):
        pid = self.cb_poli.currentData()
        if pid is None:
            return
        jumlah = len(self.db.tiket_hari(pid))
        nama = self._polis[pid]["nama"]
        if jumlah == 0:
            info(self, f"Tidak ada nomor antrian hari ini untuk {nama}.")
            return
        if not ask(self, f"Hapus SEMUA {jumlah} nomor antrian hari ini untuk {nama}?\n\n"
                         "Nomor akan mulai lagi dari 001, dan tiket yang sudah dicetak ke pasien tidak berlaku lagi."):
            return
        self.db.tiket_hapus_hari(pid)
        self._last_id = None
        self.lbl_last.setText("")
        self.refresh_data()
        self.ctx.notify_data_changed()

    def cancel_selected(self):
        tid = selected_id(self.table)
        if tid is None:
            info(self, "Pilih nomor di tabel terlebih dahulu.")
            return
        if ask(self, "Batalkan nomor antrian yang dipilih?"):
            self.db.tiket_status(tid, "batal")
            self.refresh_data()
            self.ctx.notify_data_changed()
