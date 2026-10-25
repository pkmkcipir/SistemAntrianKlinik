"""Tema tampilan layar antrian. Dipakai oleh layar PC (Qt) dan halaman TV (browser).

Setiap tema berisi warna untuk: latar halaman, header, kotak video, panel nomor yang dipanggil
(normal dan saat berkedip ketika nomor dipanggil), daftar layanan, dan footer.
"""

DEFAULT = "hijau"

TEMA = {
    "hijau": {
        "nama": "Hijau Klinik",
        "bg": "#eaf1ee", "header": "#0e6b67", "header_fg": "#ffffff", "header_sub": "#bfeae3",
        "video_bg": "#0a1517", "video_fg": "#8fb3ad",
        "called": "#0e6b67", "called_fg": "#ffffff", "flash": "#f2b705", "flash_fg": "#10252b",
        "board": "#ffffff", "row_line": "#d9e6e2", "row_name": "#10252b", "row_info": "#5f7a76",
        "row_num": "#0e6b67", "footer": "#093f3c", "footer_fg": "#ffffff", "mark": "#a7e3da",
    },
    "biru": {
        "nama": "Biru Medis",
        "bg": "#e8eff8", "header": "#0b4f8a", "header_fg": "#ffffff", "header_sub": "#bcd8f2",
        "video_bg": "#08121c", "video_fg": "#8fa9c0",
        "called": "#1565b8", "called_fg": "#ffffff", "flash": "#ffb703", "flash_fg": "#10253b",
        "board": "#ffffff", "row_line": "#d3e0ee", "row_name": "#10253b", "row_info": "#5a6f87",
        "row_num": "#1565b8", "footer": "#083a66", "footer_fg": "#ffffff", "mark": "#9ec5ea",
    },
    "pink": {
        "nama": "Pink Ibu dan Anak",
        "bg": "#fbeef3", "header": "#b8336a", "header_fg": "#ffffff", "header_sub": "#ffd3e4",
        "video_bg": "#1b0d14", "video_fg": "#c9a3b4",
        "called": "#c2386d", "called_fg": "#ffffff", "flash": "#ffd166", "flash_fg": "#4a1230",
        "board": "#ffffff", "row_line": "#f1d3df", "row_name": "#3b1226", "row_info": "#86596c",
        "row_num": "#b8336a", "footer": "#7a1d45", "footer_fg": "#ffffff", "mark": "#ffc1da",
    },
    "ungu": {
        "nama": "Ungu Lavender",
        "bg": "#f1edf9", "header": "#5b3b9b", "header_fg": "#ffffff", "header_sub": "#d9ccf5",
        "video_bg": "#130d20", "video_fg": "#b0a3d0",
        "called": "#6d47b8", "called_fg": "#ffffff", "flash": "#ffd166", "flash_fg": "#2a1856",
        "board": "#ffffff", "row_line": "#e0d6f2", "row_name": "#261848", "row_info": "#73659a",
        "row_num": "#5b3b9b", "footer": "#3e2670", "footer_fg": "#ffffff", "mark": "#cdbdf3",
    },
    "gelap": {
        "nama": "Gelap (cocok untuk ruangan redup)",
        "bg": "#0d171a", "header": "#13262b", "header_fg": "#e8f4f2", "header_sub": "#8fb3ad",
        "video_bg": "#000000", "video_fg": "#6f8c88",
        "called": "#0f766e", "called_fg": "#ffffff", "flash": "#ffd23f", "flash_fg": "#0d171a",
        "board": "#16282d", "row_line": "#24414a", "row_name": "#e8f4f2", "row_info": "#8fb3ad",
        "row_num": "#5eead4", "footer": "#091113", "footer_fg": "#e8f4f2", "mark": "#7fb5ad",
    },
    "oranye": {
        "nama": "Oranye Hangat",
        "bg": "#fbf1e6", "header": "#b45309", "header_fg": "#ffffff", "header_sub": "#fde0bf",
        "video_bg": "#1a1009", "video_fg": "#c8a98a",
        "called": "#c2640a", "called_fg": "#ffffff", "flash": "#0f766e", "flash_fg": "#ffffff",
        "board": "#ffffff", "row_line": "#f0dcc3", "row_name": "#3a2108", "row_info": "#86673f",
        "row_num": "#b45309", "footer": "#7a3705", "footer_fg": "#ffffff", "mark": "#f7c995",
    },
}


def get_tema(id_):
    """Tema lengkap (dengan kunci 'id'); id tidak dikenal memakai tema bawaan."""
    id_ = id_ if id_ in TEMA else DEFAULT
    return {"id": id_, **TEMA[id_]}


def qss_layar(t):
    """Stylesheet Qt untuk layar antrian di PC."""
    return f"""
QWidget#display {{ background: {t['bg']}; }}
QLabel {{ background: transparent; }}
QFrame#header {{ background: {t['header']}; }}
QLabel#hTitle, QLabel#hDate, QLabel#hClock {{ color: {t['header_fg']}; }}
QLabel#hSub, QLabel#hTel {{ color: {t['header_sub']}; }}
QFrame#videoBox {{ background: {t['video_bg']}; }}
QLabel#placeholder {{ color: {t['video_fg']}; }}
QFrame#called {{ background: {t['called']}; }}
QFrame#called[flash="true"] {{ background: {t['flash']}; }}
QFrame#called QLabel {{ color: {t['called_fg']}; }}
QFrame#called[flash="true"] QLabel {{ color: {t['flash_fg']}; }}
QFrame#board {{ background: {t['board']}; }}
QFrame#poliRow {{ background: transparent; border-bottom: 1px solid {t['row_line']}; }}
QLabel#pNama {{ color: {t['row_name']}; }}
QLabel#pInfo {{ color: {t['row_info']}; }}
QLabel#pNow {{ color: {t['row_num']}; }}
QFrame#footer {{ background: {t['footer']}; }}
QLabel#fMark {{ color: {t['mark']}; }}
"""
