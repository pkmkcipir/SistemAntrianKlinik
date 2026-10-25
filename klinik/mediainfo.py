"""Membaca info dasar video (kontainer, kodek) tanpa FFmpeg, untuk memeriksa apakah video bisa diputar
di peramban/TV. Untuk MP4/MOV, kotak (box) ISO-BMFF dibaca langsung dari berkas; hanya bagian kecil yang dibaca.

Hasil `probe()` bersifat penasihat: keputusan akhir ada di peramban (`canPlayType`) pada halaman TV.
  ok = True   hampir pasti bisa diputar peramban/TV (H.264 Baseline/Main/High + AAC di MP4, atau WebM)
  ok = None   tergantung peramban/TV (H.265, AV1, MKV, MOV) atau info tidak terbaca
  ok = False  hampir pasti tidak bisa (AVI, WMV, H.264 10-bit, MPEG-4 Part 2, ...)
"""
import struct
from pathlib import Path

PROFIL_H264 = {66: "Baseline", 77: "Main", 88: "Extended", 100: "High", 110: "High 10",
               122: "High 4:2:2", 244: "High 4:4:4"}
KONTAINER_TIDAK_DIDUKUNG = {".avi", ".wmv", ".flv", ".mpg", ".mpeg", ".ts", ".3gp", ".asf"}
_cache = {}


def _boxes(f, start, end):
    """Iterasi kotak pada rentang [start, end): yield (tipe, awal_isi, akhir_isi)."""
    pos = start
    while pos + 8 <= end:
        f.seek(pos)
        hdr = f.read(8)
        if len(hdr) < 8:
            return
        size, tipe = struct.unpack(">I4s", hdr)
        hlen = 8
        if size == 1:
            ext = f.read(8)
            if len(ext) < 8:
                return
            size, hlen = struct.unpack(">Q", ext)[0], 16
        elif size == 0:
            size = end - pos
        if size < hlen:
            return
        yield tipe.decode("latin-1"), pos + hlen, min(pos + size, end)
        pos += size


def _trak(f, a, b):
    """(jenis, fourcc sample entry, data entry) untuk satu trak."""
    kind = None
    for t1, a1, b1 in _boxes(f, a, b):
        if t1 != "mdia":
            continue
        for t2, a2, b2 in _boxes(f, a1, b1):
            if t2 == "hdlr":
                f.seek(a2 + 8)
                kind = f.read(4).decode("latin-1")
            elif t2 == "minf":
                for t3, a3, b3 in _boxes(f, a2, b2):
                    if t3 != "stbl":
                        continue
                    for t4, a4, b4 in _boxes(f, a3, b3):
                        if t4 == "stsd":
                            f.seek(a4 + 8)  # lewati version/flags + entry_count
                            hdr = f.read(8)
                            if len(hdr) == 8:
                                size, fourcc = struct.unpack(">I4s", hdr)
                                return kind, fourcc.decode("latin-1"), f.read(min(max(size - 8, 0), 8192))
    return kind, None, b""


def _esds(data):
    """(objectTypeIndication, audioObjectType) dari kotak esds, atau (None, None)."""
    i = data.find(b"esds")
    if i < 0:
        return None, None

    def tag_len(pos):
        tag, n = data[pos], 0
        pos += 1
        for _ in range(4):
            c = data[pos]
            pos += 1
            n = (n << 7) | (c & 0x7F)
            if not c & 0x80:
                break
        return tag, n, pos

    try:
        tag, _n, pos = tag_len(i + 8)            # ES_Descriptor
        if tag != 0x03:
            return None, None
        pos += 2
        flags = data[pos]
        pos += 1
        if flags & 0x80:
            pos += 2
        if flags & 0x40:
            pos += 1 + data[pos]
        if flags & 0x20:
            pos += 2
        tag, _n, pos = tag_len(pos)              # DecoderConfigDescriptor
        if tag != 0x04:
            return None, None
        oti, pos = data[pos], pos + 13
        aot = None
        if pos < len(data):
            tag, _n, pos = tag_len(pos)          # DecoderSpecificInfo
            if tag == 0x05 and pos < len(data):
                aot = data[pos] >> 3
        return oti, aot
    except IndexError:
        return None, None


def _probe_mp4(p, info):
    size = p.stat().st_size
    with open(p, "rb") as f:
        urutan, moov = [], None
        for tipe, a, b in _boxes(f, 0, size):
            urutan.append(tipe)
            if tipe == "moov":
                moov = (a, b)
        if not moov:
            raise ValueError("kotak moov tidak ditemukan")
        info["faststart"] = "mdat" not in urutan or urutan.index("moov") < urutan.index("mdat")
        video = audio = None
        for tipe, a, b in _boxes(f, *moov):
            if tipe != "trak":
                continue
            kind, fourcc, data = _trak(f, a, b)
            if kind == "vide" and video is None:
                video = (fourcc, data)
            elif kind == "soun" and audio is None:
                audio = (fourcc, data)

    catatan, ok = [], True
    if video is None:
        raise ValueError("tidak ada trek video")
    vc, vdata = video
    if vc in ("avc1", "avc3"):
        i = vdata.find(b"avcC")
        prof, compat, level = (vdata[i + 5], vdata[i + 6], vdata[i + 7]) if i >= 0 else (100, 0, 40)
        nama = PROFIL_H264.get(prof, str(prof))
        info["video"] = f"H.264 {nama}"
        info["mime"] = f'video/mp4; codecs="avc1.{prof:02X}{compat:02X}{level:02X}"'
        if prof not in (66, 77, 88, 100) or level > 52:
            ok = False
            catatan.append(f"H.264 {nama} (level {level / 10:.1f}) tidak didukung peramban/TV; "
                           "gunakan H.264 High 8-bit")
    elif vc in ("hvc1", "hev1", "dvh1", "dvhe"):
        info["video"], ok = "H.265 (HEVC)", None
        info["mime"] = 'video/mp4; codecs="hvc1.1.6.L93.B0"'
        catatan.append("H.265 hanya didukung sebagian peramban/TV")
    elif vc == "av01":
        info["video"], ok = "AV1", None
        info["mime"] = 'video/mp4; codecs="av01.0.08M.08"'
        catatan.append("AV1 hanya didukung peramban/TV baru")
    elif vc == "vp09":
        info["video"] = "VP9"
        info["mime"] = 'video/mp4; codecs="vp09.00.10.08"'
    else:
        info["video"], ok = vc or "?", False
        catatan.append(f"Kodek video {vc} tidak didukung peramban/TV")

    if audio is not None:
        ac, adata = audio
        if ac == "mp4a":
            oti, aot = _esds(adata)
            info["audio"] = {2: "AAC-LC", 5: "HE-AAC", 29: "HE-AACv2"}.get(aot, "AAC") if oti == 0x40 else "MP3/lainnya"
        elif ac in ("ac-3", "ec-3"):
            info["audio"] = "Dolby " + ("AC-3" if ac == "ac-3" else "E-AC-3")
            catatan.append("audio Dolby tidak didukung peramban: video tampil tanpa suara")
        elif ac in ("Opus", "fLaC"):
            info["audio"] = ac
        else:
            info["audio"] = ac or "?"
            catatan.append(f"audio {ac} mungkin tanpa suara di peramban")
    info.update(ok=ok, catatan="; ".join(catatan))


def probe(path) -> dict:
    """Info video untuk ditampilkan dan dikirim ke halaman TV."""
    p = Path(path)
    ext = p.suffix.lower()
    info = {"kontainer": ext.lstrip(".").upper(), "video": "", "audio": "", "mime": "", "ok": None,
            "catatan": "", "faststart": None}
    try:
        if ext in (".mp4", ".m4v", ".mov"):
            _probe_mp4(p, info)
            if ext == ".mov":
                info["ok"] = None if info["ok"] is not False else False
                info["catatan"] = "; ".join(x for x in ("MOV belum tentu didukung TV", info["catatan"]) if x)
        elif ext == ".webm":
            info.update(ok=True, video="VP8/VP9", audio="Opus/Vorbis", mime="video/webm")
        elif ext == ".mkv":
            info.update(ok=None, mime="video/x-matroska",
                        catatan="MKV belum tentu didukung peramban/TV (disarankan MP4 H.264 + AAC)")
        elif ext in KONTAINER_TIDAK_DIDUKUNG:
            info.update(ok=False, catatan=f"Format {ext} tidak didukung peramban/TV (ubah ke MP4 H.264 + AAC)")
        else:
            info.update(ok=None, catatan="Format tidak dikenal")
    except (OSError, struct.error, ValueError) as e:
        info.update(ok=None, catatan=f"Info video tidak terbaca ({e})")
    return info


def probe_cached(path) -> dict:
    """probe() dengan cache (berdasarkan ukuran dan waktu ubah) agar tidak membaca berkas berulang."""
    p = Path(path)
    try:
        st = p.stat()
    except OSError:
        return {"kontainer": p.suffix.lstrip(".").upper(), "video": "", "audio": "", "mime": "", "ok": None,
                "catatan": "File tidak ditemukan", "faststart": None}
    key = (str(p), st.st_size, st.st_mtime_ns)
    if key not in _cache:
        _cache[key] = probe(p)
    return _cache[key]


def ringkas(info: dict) -> str:
    """Teks pendek untuk kolom 'Web/TV' di halaman Video Edukasi."""
    isi = " + ".join(x for x in (info.get("video"), info.get("audio")) if x)
    if info.get("ok") is True:
        lambat = "" if info.get("faststart") is not False else " (mulai lambat: moov di akhir file)"
        catatan = f" [{info['catatan']}]" if info.get("catatan") else ""
        return f"Siap TV: {isi}{lambat}{catatan}"
    awal = "Tidak didukung TV" if info.get("ok") is False else "Belum tentu di TV"
    return f"{awal}: {info.get('catatan') or isi}"
