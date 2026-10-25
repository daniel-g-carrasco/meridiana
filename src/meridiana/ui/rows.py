"""What a table did inside a card, done with the design system's pieces (R79; Daniel, 24/10/2026: «non ci devono
essere tabelle vere e proprie all'interno delle schede. È complicato navigare all'interno di esse… i comandi vengono
recepiti dal resto della scheda… contenuti che fuoriescono»):

- `RowList`: things to read, one row each: the name on the left, what it is on the right in the secondary colour, a
  hair line between two rows; as tall as its rows, no scroll of its own (the card scrolls), the text shortened with
  its whole in the tooltip;
- `FieldGrid`: numbers to write in rows and columns (the bills, month by month in F1, F2, F3): a grid of the
  ordinary number fields, the rows' names on the left and the columns' on top, a total for each column; Tab goes
  from one to the next, the wheel scrolls the card unless a field has the keyboard (ui/wheel.py).

A table proper stays in the dialogs (the catalogues, the comparison of the variants), where it has the window."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDoubleSpinBox, QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from ..i18n import _, number
from .design import Size, Space, Text, text_font


class RowList(QWidget):
    def __init__(self, empty: str = "", parent=None):
        super().__init__(parent)
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(0, 0, 0, 0)
        self.box.setSpacing(0)
        self.empty = empty
        self.rows: list[tuple[str, str]] = []

    def set_rows(self, rows: list) -> None:
        """`rows`: (name, what it is) pairs, or (name, what it is, tooltip)."""
        while self.box.count():
            item = self.box.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.rows = [(r[0], r[1]) for r in rows]
        if not rows and self.empty:
            note = QLabel(self.empty)
            note.setObjectName("row-empty")
            note.setWordWrap(True)
            self.box.addWidget(note)
            return
        for i, r in enumerate(rows):
            name, what = r[0], r[1]
            tip = r[2] if len(r) > 2 else f"{name}: {what}"
            if i:
                line = QFrame()
                line.setObjectName("row-line")
                line.setFixedHeight(1)
                self.box.addWidget(line)
            row = QWidget()
            row.setObjectName("row")
            grid = QGridLayout(row)
            grid.setContentsMargins(0, Space.S, 0, Space.S)
            grid.setHorizontalSpacing(Space.L)
            left = QLabel(name)
            left.setFont(text_font(Text.STRONG))
            right = QLabel(what)
            right.setObjectName("row-detail")
            right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            right.setWordWrap(True)
            for w in (left, right):
                w.setToolTip(tip)
            grid.addWidget(left, 0, 0)
            grid.addWidget(right, 0, 1)
            grid.setColumnStretch(1, 1)
            self.box.addWidget(row)

    def texts(self) -> list[tuple[str, str]]:
        return list(self.rows)


class FieldGrid(QWidget):
    """Number fields in rows and columns; `changed` with every row as {column: value} after an edit."""

    changed = Signal(list)

    def __init__(self, rows: list[str], columns: list[str], unit: str = "", decimals: int = 0, parent=None):
        super().__init__(parent)
        self.columns = list(columns)
        self.loading = False
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(Space.S)
        grid.setVerticalSpacing(Space.XS)
        for j, c in enumerate(columns):
            head = QLabel(c)
            head.setObjectName("grid-head")
            head.setFont(text_font(Text.SECONDARY))
            head.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
            grid.addWidget(head, 0, j + 1)
        self.fields: list[list[QDoubleSpinBox]] = []
        for i, r in enumerate(rows):
            name = QLabel(r)
            name.setObjectName("grid-row")
            grid.addWidget(name, i + 1, 0)
            line = []
            for j in range(len(columns)):
                f = QDoubleSpinBox()
                f.setRange(0, 1e9)
                f.setDecimals(decimals)
                f.setGroupSeparatorShown(True)
                # twelve rows of arrows are noise: the arrows' room set to nought by the sheet (#grid-field); with
                # NoButtons Qt's style sheet gives the line edit inside a width of one pixel (24/10/2026)
                f.setObjectName("grid-field")
                f.setMinimumWidth(Size.CONTROL * 2)    # not the width of the largest number it takes
                f.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                if unit:
                    f.setSuffix(f" {unit}")
                f.setToolTip(f"{r}, {columns[j]}")
                f.valueChanged.connect(self._edited)
                grid.addWidget(f, i + 1, j + 1)
                line.append(f)
            self.fields.append(line)
        self.totals = []
        total_name = QLabel(_("Total"))
        total_name.setObjectName("grid-row")
        grid.addWidget(total_name, len(rows) + 1, 0)
        for j in range(len(columns)):
            t = QLabel("")
            t.setObjectName("grid-total")
            t.setFont(text_font(Text.STRONG))
            grid.addWidget(t, len(rows) + 1, j + 1)
            self.totals.append(t)
        for j in range(len(columns)):
            grid.setColumnStretch(j + 1, 1)
        self._sum()

    def set_values(self, rows: list) -> None:
        """Every row's {column: value}; missing values are nought. No `changed` for it."""
        self.loading = True
        try:
            for i, line in enumerate(self.fields):
                row = rows[i] if i < len(rows) and isinstance(rows[i], dict) else {}
                for j, f in enumerate(line):
                    f.setValue(float(row.get(self.columns[j], 0) or 0))
        finally:
            self.loading = False
        self._sum()

    def values(self) -> list[dict]:
        return [{c: f.value() for c, f in zip(self.columns, line, strict=True)} for line in self.fields]

    def _sum(self) -> None:
        for j, t in enumerate(self.totals):
            t.setText(number(sum(line[j].value() for line in self.fields), 0, grouping=True))

    def _edited(self, _v) -> None:
        self._sum()
        if not self.loading:
            self.changed.emit(self.values())
