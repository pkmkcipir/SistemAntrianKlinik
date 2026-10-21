"""Lapisan database SQLite (satu file: klinik.db)."""
import shutil
import sqlite3
from pathlib import Path

from .config import data_dir, now_iso, today_iso

SCHEMA = """
CREATE TABLE IF NOT EXISTS setting(key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE IF NOT EXISTS poli(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kode TEXT NOT NULL UNIQUE,
  nama TEXT NOT NULL,
  loket TEXT NOT NULL DEFAULT '',
  aktif INTEGER NOT NULL DEFAULT 1);

CREATE TABLE IF NOT EXISTS pasien(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  no_rm TEXT NOT NULL UNIQUE,
  nama TEXT NOT NULL,
  nik TEXT NOT NULL DEFAULT '',
  jk TEXT NOT NULL DEFAULT '',
  tgl_lahir TEXT NOT NULL DEFAULT '',
  telepon TEXT NOT NULL DEFAULT '',
  penjamin TEXT NOT NULL DEFAULT 'Umum',
  alamat TEXT NOT NULL DEFAULT '',
  catatan TEXT NOT NULL DEFAULT '',
  dibuat TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS antrian(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tanggal TEXT NOT NULL,
  poli_id INTEGER NOT NULL REFERENCES poli(id),
  nomor INTEGER NOT NULL,
  kode TEXT NOT NULL,
  pasien_id INTEGER REFERENCES pasien(id) ON DELETE SET NULL,
  nama TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'menunggu',
  loket TEXT NOT NULL DEFAULT '',
  dibuat TEXT NOT NULL,
  dipanggil TEXT,
  selesai TEXT,
  jml_panggil INTEGER NOT NULL DEFAULT 0,
  UNIQUE(tanggal, poli_id, nomor));
CREATE INDEX IF NOT EXISTS ix_antrian ON antrian(tanggal, poli_id, status);

CREATE TABLE IF NOT EXISTS keuangan(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tanggal TEXT NOT NULL,
  tipe TEXT NOT NULL CHECK(tipe IN ('Pemasukan','Pengeluaran')),
  kategori TEXT NOT NULL DEFAULT '',
  keterangan TEXT NOT NULL DEFAULT '',
  jumlah INTEGER NOT NULL DEFAULT 0,
  metode TEXT NOT NULL DEFAULT 'Tunai',
  pasien_id INTEGER REFERENCES pasien(id) ON DELETE SET NULL);
CREATE INDEX IF NOT EXISTS ix_keuangan ON keuangan(tanggal);

CREATE TABLE IF NOT EXISTS obat(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kode TEXT NOT NULL UNIQUE,
  nama TEXT NOT NULL,
  satuan TEXT NOT NULL DEFAULT 'Tablet',
  harga_jual INTEGER NOT NULL DEFAULT 0,
  stok_min INTEGER NOT NULL DEFAULT 0,
  aktif INTEGER NOT NULL DEFAULT 1);

CREATE TABLE IF NOT EXISTS obat_mutasi(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tanggal TEXT NOT NULL,
  obat_id INTEGER NOT NULL REFERENCES obat(id),
  tipe TEXT NOT NULL CHECK(tipe IN ('Masuk','Keluar','Koreksi')),
  delta INTEGER NOT NULL,
  keterangan TEXT NOT NULL DEFAULT '',
  pasien_id INTEGER REFERENCES pasien(id) ON DELETE SET NULL,
  dibuat TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_mutasi ON obat_mutasi(obat_id, tanggal);

CREATE TABLE IF NOT EXISTS video(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  judul TEXT NOT NULL,
  path TEXT NOT NULL,
  urutan INTEGER NOT NULL DEFAULT 0,
  aktif INTEGER NOT NULL DEFAULT 1);
"""

DEFAULTS = {
    "nama_klinik": "Klinik Bidan Dewi Anjani",
    "alamat": "Kavling Tanah Harapan No.D63, RT.011/RW.006, Pejuang, Medan Satria, Bekasi, West Java 17131",
    "telepon": "085178266540",
    "running_text": "Selamat datang di Klinik Bidan Dewi Anjani. Mohon menunggu panggilan sesuai nomor antrian Anda. "
                    "Jaga kebersihan tangan dan gunakan masker bila sedang batuk atau pilek.",
    "suara": "1",
    "suara_tv": "1",
    "web_aktif": "1",
    "web_port": "8080",
    "volume_video": "40",
    "monitor": "auto",
    "buka_otomatis": "1",
}

TIKET_SQL = (
    "SELECT a.*, p.nama AS poli_nama, p.kode AS poli_kode, pa.no_rm AS no_rm, "
    "COALESCE(NULLIF(pa.nama,''), a.nama) AS nama_tampil "
    "FROM antrian a JOIN poli p ON p.id=a.poli_id LEFT JOIN pasien pa ON pa.id=a.pasien_id "
)


class Database:
    def __init__(self, path=None):
        self.path = Path(path) if path else data_dir() / "klinik.db"
        self._open()

    def _open(self):
        self.con = sqlite3.connect(self.path)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA foreign_keys=ON")
        self.con.executescript(SCHEMA)
        if not self.one("SELECT 1 FROM poli LIMIT 1"):
            self.con.executemany(
                "INSERT INTO poli(kode,nama,loket) VALUES(?,?,?)",
                [("A", "Pemeriksaan Umum", "Ruang Periksa 1"), ("B", "KIA Ibu dan Anak", "Ruang Periksa 2"),
                 ("C", "KB dan Imunisasi", "Ruang Tindakan"), ("D", "Apotek", "Loket Obat")])
            self.con.commit()

    # ---- dasar -----------------------------------------------------------
    def q(self, sql, params=()):
        return self.con.execute(sql, params).fetchall()

    def one(self, sql, params=()):
        return self.con.execute(sql, params).fetchone()

    def ex(self, sql, params=()):
        try:
            cur = self.con.execute(sql, params)
            self.con.commit()
        except Exception:
            self.con.rollback()  # perintah gagal (mis. kode ganda): jangan biarkan transaksi menggantung
            raise
        return cur.lastrowid

    def backup(self, dest):
        self.con.commit()
        out = sqlite3.connect(dest)
        try:
            self.con.backup(out)
        finally:
            out.close()

    def restore(self, src):
        chk = sqlite3.connect(src)
        try:
            tabel = {r[0] for r in chk.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            chk.close()
        if not {"pasien", "antrian", "keuangan", "obat"} <= tabel:
            raise ValueError("File ini bukan backup Sistem Antrian Klinik.")
        self.backup(str(self.path) + ".sebelum-restore")
        self.con.close()
        shutil.copy2(src, self.path)
        self._open()

    # ---- pengaturan ------------------------------------------------------
    def get(self, key, default=None):
        r = self.one("SELECT value FROM setting WHERE key=?", (key,))
        return r["value"] if r else DEFAULTS.get(key, default)

    def set(self, key, value):
        self.ex("INSERT INTO setting(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))

    # ---- poli / layanan --------------------------------------------------
    def poli_list(self, aktif_only=True):
        return self.q("SELECT * FROM poli" + (" WHERE aktif=1" if aktif_only else "") + " ORDER BY kode")

    def poli_save(self, d, id=None):
        v = (d["kode"].strip().upper(), d["nama"].strip(), d.get("loket", "").strip(),
             1 if d.get("aktif", True) else 0)
        if id is None:
            return self.ex("INSERT INTO poli(kode,nama,loket,aktif) VALUES(?,?,?,?)", v)
        self.ex("UPDATE poli SET kode=?, nama=?, loket=?, aktif=? WHERE id=?", (*v, id))
        return id

    # ---- pasien ----------------------------------------------------------
    def _no_rm_baru(self):
        r = self.one("SELECT seq FROM sqlite_sequence WHERE name='pasien'")
        return f"RM-{(r['seq'] if r else 0) + 1:06d}"

    def pasien_cari(self, q="", limit=500):
        like = f"%{q.strip()}%"
        return self.q("SELECT * FROM pasien WHERE nama LIKE ? OR no_rm LIKE ? OR nik LIKE ? "
                      "OR telepon LIKE ? ORDER BY nama COLLATE NOCASE LIMIT ?", (like,) * 4 + (limit,))

    def pasien_get(self, id):
        return self.one("SELECT * FROM pasien WHERE id=?", (id,))

    def pasien_save(self, d, id=None):
        cols = ("nama", "nik", "jk", "tgl_lahir", "telepon", "penjamin", "alamat", "catatan")
        vals = [d.get(c) or "" for c in cols]
        if id is None:
            return self.ex(
                f"INSERT INTO pasien(no_rm,{','.join(cols)},dibuat) VALUES(?,{','.join('?' * len(cols))},?)",
                [self._no_rm_baru(), *vals, now_iso()])
        self.ex(f"UPDATE pasien SET {','.join(c + '=?' for c in cols)} WHERE id=?", [*vals, id])
        return id

    def pasien_del(self, id):
        self.ex("DELETE FROM pasien WHERE id=?", (id,))

    # ---- antrian ---------------------------------------------------------
    def tiket(self, id):
        return self.one(TIKET_SQL + "WHERE a.id=?", (id,))

    def tiket_ambil(self, poli_id, pasien_id=None, nama=""):
        tgl = today_iso()
        with self.con:
            poli = self.con.execute("SELECT * FROM poli WHERE id=?", (poli_id,)).fetchone()
            n = self.con.execute("SELECT COALESCE(MAX(nomor),0)+1 FROM antrian WHERE tanggal=? AND poli_id=?",
                                 (tgl, poli_id)).fetchone()[0]
            cur = self.con.execute(
                "INSERT INTO antrian(tanggal,poli_id,nomor,kode,pasien_id,nama,status,dibuat) "
                "VALUES(?,?,?,?,?,?,'menunggu',?)",
                (tgl, poli_id, n, f"{poli['kode']}{n:03d}", pasien_id, nama, now_iso()))
        return self.tiket(cur.lastrowid)

    def tiket_hari(self, poli_id=None, tgl=None):
        sql, p = TIKET_SQL + "WHERE a.tanggal=?", [tgl or today_iso()]
        if poli_id:
            sql += " AND a.poli_id=?"
            p.append(poli_id)
        return self.q(sql + " ORDER BY a.id", p)

    def hitung_menunggu(self):
        return {r["poli_id"]: r["n"] for r in self.q(
            "SELECT poli_id, COUNT(*) AS n FROM antrian WHERE tanggal=? AND status='menunggu' "
            "GROUP BY poli_id", (today_iso(),))}

    def panggil_tiket(self, tid, loket=""):
        t = self.tiket(tid)
        with self.con:
            # nomor yang masih 'dipanggil' di ruang yang sama dianggap selesai
            self.con.execute(
                "UPDATE antrian SET status='selesai', selesai=? WHERE tanggal=? AND poli_id=? "
                "AND loket=? AND status='dipanggil' AND id<>?",
                (now_iso(), t["tanggal"], t["poli_id"], loket, tid))
            self.con.execute(
                "UPDATE antrian SET status='dipanggil', loket=?, dipanggil=?, jml_panggil=jml_panggil+1 "
                "WHERE id=?", (loket, now_iso(), tid))
        return self.tiket(tid)

    def panggil_berikut(self, poli_id, loket=""):
        r = self.one("SELECT id FROM antrian WHERE tanggal=? AND poli_id=? AND status='menunggu' "
                     "ORDER BY nomor LIMIT 1", (today_iso(), poli_id))
        return self.panggil_tiket(r["id"], loket) if r else None

    def tiket_aktif(self, poli_id, loket=None):
        sql, p = TIKET_SQL + "WHERE a.tanggal=? AND a.poli_id=? AND a.status='dipanggil'", [today_iso(), poli_id]
        if loket is not None:
            sql += " AND a.loket=?"
            p.append(loket)
        return self.one(sql + " ORDER BY a.dipanggil DESC LIMIT 1", p)

    def panggil_ulang(self, poli_id, loket=None):
        t = self.tiket_aktif(poli_id, loket)
        if not t:
            return None
        self.ex("UPDATE antrian SET dipanggil=?, jml_panggil=jml_panggil+1 WHERE id=?", (now_iso(), t["id"]))
        return self.tiket(t["id"])

    def tiket_status(self, tid, status):
        self.ex("UPDATE antrian SET status=?, selesai=? WHERE id=?", (status, now_iso(), tid))

    def display_state(self):
        """Data untuk layar antrian: nomor terakhir per poli + antrian berikutnya."""
        tgl, out = today_iso(), []
        for p in self.poli_list():
            cur = self.one("SELECT kode, loket FROM antrian WHERE tanggal=? AND poli_id=? "
                           "AND dipanggil IS NOT NULL ORDER BY dipanggil DESC LIMIT 1", (tgl, p["id"]))
            tunggu = [r["kode"] for r in self.q(
                "SELECT kode FROM antrian WHERE tanggal=? AND poli_id=? AND status='menunggu' ORDER BY nomor",
                (tgl, p["id"]))]
            out.append({"id": p["id"], "kode": p["kode"], "nama": p["nama"],
                        "sekarang": cur["kode"] if cur else "-", "loket": cur["loket"] if cur else "",
                        "menunggu": len(tunggu), "berikut": tunggu[:3]})
        last = self.one(TIKET_SQL + "WHERE a.tanggal=? AND a.dipanggil IS NOT NULL "
                        "ORDER BY a.dipanggil DESC LIMIT 1", (tgl,))
        return {"poli": out, "terakhir": dict(last) if last else None}

    # ---- keuangan --------------------------------------------------------
    def keu_list(self, start, end):
        return self.q("SELECT k.*, pa.nama AS pasien_nama FROM keuangan k "
                      "LEFT JOIN pasien pa ON pa.id=k.pasien_id "
                      "WHERE k.tanggal BETWEEN ? AND ? ORDER BY k.tanggal, k.id", (start, end))

    def keu_get(self, id):
        return self.one("SELECT * FROM keuangan WHERE id=?", (id,))

    def keu_save(self, d, id=None):
        v = (d["tanggal"], d["tipe"], d.get("kategori", ""), d.get("keterangan", ""),
             int(d["jumlah"]), d.get("metode", "Tunai"), d.get("pasien_id"))
        if id is None:
            return self.ex("INSERT INTO keuangan(tanggal,tipe,kategori,keterangan,jumlah,metode,pasien_id) "
                           "VALUES(?,?,?,?,?,?,?)", v)
        self.ex("UPDATE keuangan SET tanggal=?,tipe=?,kategori=?,keterangan=?,jumlah=?,metode=?,pasien_id=? "
                "WHERE id=?", (*v, id))
        return id

    def keu_del(self, id):
        self.ex("DELETE FROM keuangan WHERE id=?", (id,))

    # ---- obat ------------------------------------------------------------
    def obat_list(self, q="", aktif_only=False):
        like = f"%{q.strip()}%"
        sql = ("SELECT o.*, COALESCE((SELECT SUM(delta) FROM obat_mutasi m WHERE m.obat_id=o.id),0) AS stok "
               "FROM obat o WHERE (o.nama LIKE ? OR o.kode LIKE ?)")
        if aktif_only:
            sql += " AND o.aktif=1"
        return self.q(sql + " ORDER BY o.nama COLLATE NOCASE", (like, like))

    def obat_get(self, id):
        return self.one("SELECT * FROM obat WHERE id=?", (id,))

    def obat_save(self, d, id=None, stok_awal=0):
        kode = (d.get("kode") or "").strip().upper()
        if not kode:
            kode = f"OB-{self.one('SELECT COALESCE(MAX(id),0)+1 AS n FROM obat')['n']:04d}"
        v = (kode, d["nama"].strip(), d.get("satuan") or "Tablet", int(d.get("harga_jual", 0)),
             int(d.get("stok_min", 0)), 1 if d.get("aktif", True) else 0)
        if id is None:
            id = self.ex("INSERT INTO obat(kode,nama,satuan,harga_jual,stok_min,aktif) VALUES(?,?,?,?,?,?)", v)
            if stok_awal > 0:
                self.mutasi_add(id, today_iso(), "Masuk", stok_awal, "Stok awal")
        else:
            self.ex("UPDATE obat SET kode=?,nama=?,satuan=?,harga_jual=?,stok_min=?,aktif=? WHERE id=?", (*v, id))
        return id

    def stok(self, obat_id):
        return self.one("SELECT COALESCE(SUM(delta),0) AS s FROM obat_mutasi WHERE obat_id=?", (obat_id,))["s"]

    def mutasi_add(self, obat_id, tanggal, tipe, jumlah, ket="", pasien_id=None, total=0, metode="Tunai"):
        """Catat obat masuk/keluar/koreksi. Bila total > 0, otomatis dicatat ke keuangan
        (Keluar = pemasukan 'Obat', Masuk = pengeluaran 'Pembelian Obat')."""
        jumlah = int(jumlah)
        if tipe == "Koreksi" and jumlah == 0:
            raise ValueError("Selisih koreksi tidak boleh 0.")
        if tipe != "Koreksi" and jumlah <= 0:
            raise ValueError("Jumlah harus lebih dari 0.")
        delta = -jumlah if tipe == "Keluar" else jumlah
        stok = self.stok(obat_id)
        if stok + delta < 0:
            raise ValueError(f"Stok tidak mencukupi (tersedia {stok}).")
        o = self.obat_get(obat_id)
        with self.con:
            self.con.execute(
                "INSERT INTO obat_mutasi(tanggal,obat_id,tipe,delta,keterangan,pasien_id,dibuat) "
                "VALUES(?,?,?,?,?,?,?)", (tanggal, obat_id, tipe, delta, ket, pasien_id, now_iso()))
            if total and total > 0 and tipe in ("Masuk", "Keluar"):
                keluar = tipe == "Keluar"
                self.con.execute(
                    "INSERT INTO keuangan(tanggal,tipe,kategori,keterangan,jumlah,metode,pasien_id) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (tanggal, "Pemasukan" if keluar else "Pengeluaran", "Obat" if keluar else "Pembelian Obat",
                     f"{o['nama']} x{jumlah} {o['satuan']}", int(total), metode, pasien_id if keluar else None))

    def mutasi_list(self, start, end):
        return self.q("SELECT m.*, o.nama AS obat_nama, o.satuan, pa.nama AS pasien_nama "
                      "FROM obat_mutasi m JOIN obat o ON o.id=m.obat_id "
                      "LEFT JOIN pasien pa ON pa.id=m.pasien_id "
                      "WHERE m.tanggal BETWEEN ? AND ? ORDER BY m.tanggal, m.id", (start, end))

    def obat_rekap(self, start, end):
        """Stok awal, masuk, keluar, koreksi per obat pada rentang [start, end]."""
        return self.q(
            "SELECT o.*, "
            "COALESCE((SELECT SUM(delta) FROM obat_mutasi WHERE obat_id=o.id AND tanggal<?),0) AS awal, "
            "COALESCE((SELECT SUM(delta) FROM obat_mutasi WHERE obat_id=o.id AND tanggal BETWEEN ? AND ? "
            "AND tipe='Masuk'),0) AS masuk, "
            "COALESCE((SELECT -SUM(delta) FROM obat_mutasi WHERE obat_id=o.id AND tanggal BETWEEN ? AND ? "
            "AND tipe='Keluar'),0) AS keluar, "
            "COALESCE((SELECT SUM(delta) FROM obat_mutasi WHERE obat_id=o.id AND tanggal BETWEEN ? AND ? "
            "AND tipe='Koreksi'),0) AS koreksi "
            "FROM obat o ORDER BY o.nama COLLATE NOCASE", (start, start, end, start, end, start, end))

    # ---- video edukasi ---------------------------------------------------
    def video_list(self, aktif_only=False):
        return self.q("SELECT * FROM video" + (" WHERE aktif=1" if aktif_only else "") + " ORDER BY urutan, id")

    def video_add(self, judul, path):
        n = self.one("SELECT COALESCE(MAX(urutan),0)+1 AS n FROM video")["n"]
        return self.ex("INSERT INTO video(judul,path,urutan) VALUES(?,?,?)", (judul, path, n))

    def video_del(self, id):
        self.ex("DELETE FROM video WHERE id=?", (id,))

    def video_aktif(self, id, aktif):
        self.ex("UPDATE video SET aktif=? WHERE id=?", (1 if aktif else 0, id))

    def video_move(self, id, step):
        ids = [r["id"] for r in self.video_list()]
        i = ids.index(id)
        j = i + step
        if not 0 <= j < len(ids):
            return
        ids[i], ids[j] = ids[j], ids[i]
        with self.con:
            for n, vid in enumerate(ids):
                self.con.execute("UPDATE video SET urutan=? WHERE id=?", (n, vid))
