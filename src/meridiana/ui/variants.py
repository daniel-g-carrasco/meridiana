"""The variants of the project side by side: each one laid out and computed away from the window's thread,
one after the other, its column filled as soon as it is ready; the better value of each row in bold. The
table can be copied, to paste into a spreadsheet or the report."""

from __future__ import annotations

import html

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QGuiApplication, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import (QApplication, QDialog, QDialogButtonBox, QHeaderView, QLabel, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from .. import compare, log
from . import tell
from ..i18n import _
from .theme import marked


def dot() -> QIcon:
    """The dot of the variant in hand, in the colour of the selection."""
    pix = QPixmap(12, 12)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QApplication.palette().color(QPalette.ColorRole.Highlight))
    p.drawEllipse(2, 2, 8, 8)
    p.end()
    return QIcon(pix)


class CompareSignals(QObject):
    one = Signal(int, str, dict)        # generation, variant id, its figures
    done = Signal(int)


class CompareJob(QRunnable):
    def __init__(self, generation: int, ids: list[str], compute):
        super().__init__()
        self.generation, self.ids, self.compute = generation, ids, compute
        self.signals = CompareSignals()

    def run(self):
        for vid in self.ids:
            try:
                figures = self.compute(vid)
            except Exception as error:      # noqa: BLE001 (a thread's boundary: said out loud, not lost)
                log.complain(f"variant {vid}", error)
                figures = {"error": f"{type(error).__name__}: {error}"}
            tell(self.signals.one, self.generation, vid, figures)
        tell(self.signals.done, self.generation)


class VariantsDialog(QDialog):
    """`variants` are (id, name) in their order, `compute(id)` gives the figures of one (in a worker)."""

    generation = 0

    def __init__(self, variants: list[tuple[str, str]], compute, current: str = "", parent=None,
                 pool: QThreadPool | None = None):
        super().__init__(parent)
        self.setWindowTitle(_("Compare the variants"))
        self.ids = [vid for vid, _name in variants]
        self.names = [name for _vid, name in variants]
        self.figures: dict[str, dict] = {}
        box = QVBoxLayout(self)
        self.status = QLabel()
        self.status.setWordWrap(True)
        box.addWidget(self.status)
        self.table = QTableWidget(len(compare.rows()), len(self.ids))
        self.table.setHorizontalHeaderLabels(self.names)
        if current in self.ids:                     # the variant in hand: a dot drawn, not «●» in another font
            self.table.horizontalHeaderItem(self.ids.index(current)).setIcon(dot())
        self.table.setVerticalHeaderLabels([label for _k, label, _d, _b in compare.rows()])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        box.addWidget(self.table, 1)
        note = QLabel(marked(html.escape(_(
            "Each variant is computed as the window computes the one in hand: the same weather, consumption and "
            "prices; bold marks the better value of a row. ● is the variant in hand."))))
        note.setTextFormat(Qt.TextFormat.RichText)
        note.setWordWrap(True)
        box.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.copy_button = QPushButton(_("Copy the table"))
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self._copy)
        buttons.addButton(self.copy_button, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.rejected.connect(self.reject)
        box.addWidget(buttons)
        self.resize(760, 560)
        VariantsDialog.generation += 1
        self.mine = VariantsDialog.generation
        self.job = CompareJob(self.mine, self.ids, compute)
        self.job.signals.one.connect(self._one)
        self.job.signals.done.connect(self._done)
        self.status.setText(_("Computing {n} variants…").format(n=len(self.ids)))
        (pool or QThreadPool.globalInstance()).start(self.job)

    def _one(self, generation: int, vid: str, figures: dict) -> None:
        if generation != self.mine:
            return
        self.figures[vid] = figures
        col = self.ids.index(vid)
        for row, (key, _label, decimals, _better) in enumerate(compare.rows()):
            text = figures["error"] if "error" in figures and row == 0 else (
                "" if "error" in figures else compare.cell(figures, key, decimals))
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if "error" in figures:
                item.setToolTip(figures["error"])
            self.table.setItem(row, col, item)
        self.status.setText(_("Computed {done} of {n} variants…").format(done=len(self.figures), n=len(self.ids)))
        self._mark()

    def _mark(self) -> None:
        known = [self.figures.get(vid, {"error": ""}) for vid in self.ids]
        for row, (key, _label, _decimals, better) in enumerate(compare.rows()):
            win = compare.best(known, key, better)
            for col in range(len(self.ids)):
                item = self.table.item(row, col)
                if item is not None:
                    font = item.font()
                    font.setWeight(font.Weight.DemiBold if col == win else font.Weight.Normal)
                    item.setFont(font)

    def _done(self, generation: int) -> None:
        if generation != self.mine:
            return
        self.copy_button.setEnabled(True)
        errors = sum(1 for f in self.figures.values() if "error" in f)
        self.status.setText(_("All the variants are computed.") if not errors else
                            _("Computed; {n} could not be: hover on the cell to read why.").format(n=errors))

    def summaries(self) -> list[dict]:
        return [self.figures.get(vid, {"error": _("not computed")}) for vid in self.ids]

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(compare.table_text(self.names, self.summaries()))
        self.status.setText(_("The table is in the clipboard."))
