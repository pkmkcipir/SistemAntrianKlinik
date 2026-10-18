"""Tema tampilan, dialog form generik, dan helper tabel yang dipakai di seluruh aplikasi."""
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
    QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

MAIN_QSS = """
QMainWindow, QDialog { background: #eef3f1; }
QFrame#side { background: #0e6b67; }
QLabel#brand { color: white; font-size: 15pt; font-weight: 700; padding: 20px 18px 0 18px; background: transparent; }
QLabel#brandSub { color: #a7e3da; padding: 2px 18px 16px 18px; background: transparent; }
QListWidget#nav { background: transparent; border: none; outline: 0; color: #d3f1ec; font-size: 11pt; padding: 0 10px; }
QListWidget#nav::item { padding: 11px 14px; border-radius: 8px; margin: 2px 0; }
QListWidget#nav::item:hover { background: #0b5753; }
QListWidget#nav::item:selected { background: #f4fbf9; color: #0e6b67; font-weight: 600; }
QFrame#card { background: white; border: 1px solid #dbe6e2; border-radius: 10px; }
QLabel { background: transparent; color: #10252b; }
QLabel#h1 { font-size: 17pt; font-weight: 700; }
QLabel#h2 { font-size: 12pt; font-weight: 600; }
QLabel#muted { color: #5f7a76; }
QLabel#stat { font-size: 15pt; font-weight: 700; color: #0e6b67; }
QLabel#big { font-size: 20pt; font-weight: 700; color: #0e6b67; }
QLabel#footer { color: #5f7a76; padding: 7px 0; }
QPushButton { background: #0e6b67; color: white; border: none; border-radius: 7px; padding: 8px 16px; font-weight: 600; }
QPushButton:hover { background: #12827c; }
QPushButton:pressed { background: #0b5753; }
QPushButton:disabled { background: #cfdad7; color: #8fa5a1; }
QPushButton[kind="soft"] { background: #dde8e5; color: #10252b; }
QPushButton[kind="soft"]:hover { background: #cbdad6; }
QPushButton[kind="danger"] { background: #c2410c; }
QPushButton[kind="danger"]:hover { background: #9a3412; }
QPushButton#poliBtn { background: white; border: 2px solid #b9d8d2; border-radius: 12px; padding: 0; }
QLabel#poliKode { font-size: 17pt; font-weight: 700; color: #0e6b67; }
QLabel#poliNama { font-size: 10.5pt; font-weight: 600; }
QLabel#poliJml { color: #5f7a76; }
QPushButton#poliBtn:hover { background: #effaf7; border-color: #0e6b67; }
QLineEdit, QComboBox, QPlainTextEdit { background: white; border: 1px solid #c5d4d0; border-radius: 6px; padding: 5px 8px; selection-background-color: #b9e6df; selection-color: #10252b; }
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus { border: 1px solid #0e6b67; }
QTableWidget { background: white; alternate-background-color: #f6faf9; border: 1px solid #dbe6e2; gridline-color: #edf2f0; selection-background-color: #cfeee8; selection-color: #10252b; }
QTableWidget::item { padding: 3px 6px; }
QHeaderView::section { background: #e4eeeb; color: #34504b; border: none; border-bottom: 1px solid #cfdcd8; padding: 7px 8px; font-weight: 600; }
QTabWidget::pane { border: 1px solid #dbe6e2; background: white; top: -1px; }
QTabBar::tab { background: #dde8e5; padding: 8px 18px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px; }
QTabBar::tab:selected { background: white; color: #0e6b67; font-weight: 600; }
QProgressBar { border: 1px solid #c5d4d0; border-radius: 6px; text-align: center; }
QProgressBar::chunk { background: #0e6b67; border-radius: 5px; }
"""


def apply_theme(app):
    """Paksa tema terang + gaya Fusion supaya tampilan sama di semua PC (termasuk Windows mode gelap)."""
    app.setStyle("Fusion")
    try:
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    except Exception:
        pass
    p, c = QPalette(), QColor
    for role, color in (
        (QPalette.ColorRole.Window, "#eef3f1"), (QPalette.ColorRole.WindowText, "#10252b"),
        (QPalette.ColorRole.Base, "#ffffff"), (QPalette.ColorRole.AlternateBase, "#f6faf9"),
        (QPalette.ColorRole.Text, "#10252b"), (QPalette.ColorRole.Button, "#dde8e5"),
        (QPalette.ColorRole.ButtonText, "#10252b"), (QPalette.ColorRole.Highlight, "#0e6b67"),
        (QPalette.ColorRole.HighlightedText, "#ffffff"), (QPalette.ColorRole.ToolTipBase, "#ffffff"),
        (QPalette.ColorRole.ToolTipText, "#10252b"), (QPalette.ColorRole.PlaceholderText, "#8fa5a1"),
    ):
        p.setColor(role, c(color))
    app.setPalette(p)
    app.setFont(QFont("Segoe UI", 10))


# ---- widget kecil ------------------------------------------------------------
def card():
    f = QFrame()
    f.setObjectName("card")
    return f


def label(text="", name="", wrap=False):
    lb = QLabel(text)
    if name:
        lb.setObjectName(name)
    lb.setWordWrap(wrap)
    return lb


def button(text, kind="", slot=None):
    b = QPushButton(text)
    if kind:
        b.setProperty("kind", kind)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if slot:
        b.clicked.connect(lambda _=False: slot())
    return b


def info(parent, text, title="Informasi"):
    QMessageBox.information(parent, title, text)


def warn(parent, text, title="Perhatian"):
    QMessageBox.warning(parent, title, text)


def ask(parent, text, title="Konfirmasi"):
    m = QMessageBox(QMessageBox.Icon.Question, title, text, parent=parent)
    ya = m.addButton("Ya", QMessageBox.ButtonRole.YesRole)
    m.addButton("Tidak", QMessageBox.ButtonRole.NoRole)
    m.exec()
    return m.clickedButton() is ya


class SummaryBar(QWidget):
    """Deretan ringkasan angka (label kecil + nilai besar)."""

    def __init__(self):
        super().__init__()
        self.lay = QHBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(10)

    def set_items(self, items):
        while self.lay.count():
            w = self.lay.takeAt(0).widget()
            if w:
                w.deleteLater()
        for lab, val in items:
            f = card()
            fl = QVBoxLayout(f)
            fl.setContentsMargins(14, 8, 14, 8)
            fl.setSpacing(0)
            fl.addWidget(label(lab, "muted"))
            fl.addWidget(label(str(val), "stat"))
            self.lay.addWidget(f)
        self.lay.addStretch()


# ---- tabel -------------------------------------------------------------------
def make_table(headers, stretch=None):
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    t.setAlternatingRowColors(True)
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(32)
    h = t.horizontalHeader()
    h.setHighlightSections(False)
    h.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    if stretch is not None:
        h.setSectionResizeMode(stretch, QHeaderView.ResizeMode.Stretch)
    return t


def fill_table(t, rows, ids=None, right=(), bold_last=False):
    """Isi tabel. ids[i] disimpan di kolom pertama baris i (dibaca lewat selected_id)."""
    t.setRowCount(0)
    t.setRowCount(len(rows))
    align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    for r, row in enumerate(rows):
        for c, v in enumerate(row):
            it = QTableWidgetItem("" if v is None else str(v))
            if c in right:
                it.setTextAlignment(align)
            if c == 0 and ids is not None:
                it.setData(Qt.ItemDataRole.UserRole, ids[r])
            if bold_last and r == len(rows) - 1:
                f = it.font()
                f.setBold(True)
                it.setFont(f)
            t.setItem(r, c, it)


def selected_id(t):
    r = t.currentRow()
    if r < 0 or t.item(r, 0) is None:
        return None
    return t.item(r, 0).data(Qt.ItemDataRole.UserRole)


def pasien_items(db, limit=3000):
    """Daftar (label, id) pasien untuk combo pencarian."""
    return [("— tanpa pasien —", None)] + [(f"{p['no_rm']} · {p['nama']}", p["id"])
                                          for p in db.pasien_cari("", limit)]


# ---- dialog form generik --------------------------------------------------------
class FormDialog(QDialog):
    """Dialog form dari daftar field: (key, label, jenis[, opsi]).

    Jenis: text, multi, int, money, date, date_text, combo, combo_edit, combo_search, check.
    """

    def __init__(self, parent, title, fields, values=None, required=()):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(480)
        self.required = set(required)
        self.w, self.labels = {}, {}
        values = values or {}
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setVerticalSpacing(10)
        for key, text, kind, *rest in fields:
            w = self._make(kind, rest[0] if rest else None)
            self.w[key] = (kind, w)
            self.labels[key] = text.rstrip(" *")
            if values.get(key) is not None:
                self._set(kind, w, values[key])
            form.addRow(text, w)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Save).setText("Simpan")
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText("Batal")
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 14)
        lay.addLayout(form)
        lay.addWidget(bb)

    @staticmethod
    def _make(kind, extra):
        if kind == "text":
            return QLineEdit()
        if kind == "multi":
            w = QPlainTextEdit()
            w.setFixedHeight(66)
            return w
        if kind in ("int", "money"):
            w = QSpinBox()
            lo, hi = extra if extra else ((0, 2_000_000_000) if kind == "money" else (0, 1_000_000))
            w.setRange(lo, hi)
            w.setGroupSeparatorShown(True)
            if kind == "money":
                w.setPrefix("Rp ")
                w.setSingleStep(1000)
            return w
        if kind == "date":
            w = QDateEdit(QDate.currentDate())
            w.setCalendarPopup(True)
            w.setDisplayFormat("dd-MM-yyyy")
            return w
        if kind == "date_text":
            w = QLineEdit()
            w.setInputMask("00-00-0000;_")
            return w
        if kind.startswith("combo"):
            w = QComboBox()
            for it in extra or []:
                text, data = it if isinstance(it, tuple) else (it, it)
                w.addItem(text, data)
            if kind != "combo":
                w.setEditable(True)
            if kind == "combo_search":
                w.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
                w.completer().setFilterMode(Qt.MatchFlag.MatchContains)
                w.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            return w
        return QCheckBox()

    @staticmethod
    def _set(kind, w, v):
        if kind == "text":
            w.setText(str(v))
        elif kind == "multi":
            w.setPlainText(str(v))
        elif kind in ("int", "money"):
            w.setValue(int(v))
        elif kind == "date":
            w.setDate(QDate.fromString(str(v)[:10], "yyyy-MM-dd"))
        elif kind == "date_text":
            d = QDate.fromString(str(v)[:10], "yyyy-MM-dd")
            if d.isValid():
                w.setText(d.toString("dd-MM-yyyy"))
        elif kind == "check":
            w.setChecked(bool(v))
        elif kind == "combo_edit":
            w.setCurrentText(str(v))
        else:
            i = w.findData(v)
            if i < 0:
                i = w.findText(str(v))
            if i >= 0:
                w.setCurrentIndex(i)

    def data(self):
        out = {}
        for key, (kind, w) in self.w.items():
            if kind == "text":
                out[key] = w.text().strip()
            elif kind == "multi":
                out[key] = w.toPlainText().strip()
            elif kind in ("int", "money"):
                out[key] = w.value()
            elif kind == "date":
                out[key] = w.date().toString("yyyy-MM-dd")
            elif kind == "date_text":
                digits = "".join(ch for ch in w.text() if ch.isdigit())
                d = QDate.fromString(digits, "ddMMyyyy")
                out[key] = "" if not digits else (d.toString("yyyy-MM-dd") if d.isValid() else None)
            elif kind == "check":
                out[key] = w.isChecked()
            elif kind == "combo_edit":
                out[key] = w.currentText().strip()
            else:  # combo / combo_search
                i = w.currentIndex()
                ok = i >= 0 and (kind == "combo" or w.currentText() == w.itemText(i))
                out[key] = w.itemData(i) if ok else None
        return out

    def _ok(self):
        d = self.data()
        for key, (kind, _w) in self.w.items():
            if kind == "date_text" and d[key] is None:
                warn(self, f"Format “{self.labels[key]}” tidak valid. Gunakan hh-bb-tttt, contoh 17-08-1990.")
                return
        for key in self.required:
            if d.get(key) in ("", None):
                warn(self, f"Kolom “{self.labels[key]}” wajib diisi.", "Data belum lengkap")
                return
        self.accept()


def ask_form(parent, title, fields, values=None, required=()):
    dlg = FormDialog(parent, title, fields, values, required)
    return dlg.data() if dlg.exec() else None
