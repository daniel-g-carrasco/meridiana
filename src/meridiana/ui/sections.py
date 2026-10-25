"""Sections in a tree (study 17, T2, Daniel's choice of 23/10/2026): the rows that group the others become
headers in small capitals with the count beside the name, air above, never selected. The name in the secondary
text's tone and the count muted (R136, 25/10/2026: «far percepire un po' meglio il fatto che sia un titolo (non
esagerare)»): the catalogue's label, one step darker. The same delegate serves the project's tree and the Checks
panel (design document, 3.5 and 3.8). An object's row may carry a tail («Copertura · 188», the modules laid) drawn
muted.

In the project's tree (`pills`, the target of 24/10/2026, docs/studio/19-grafica): «EDIFICI  2», the count apart
and not in capitals; no arrows, no indent (the sections are always open); the selection and the hover a rounded
pill across the whole row, each column drawing its part (`row_pill`)."""

from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QIcon, QPainter, QPalette
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem, QTreeWidgetItem

SECTION_ROLE = Qt.ItemDataRole.UserRole + 7     # on a header row: the count shown beside the name
TAIL_ROLE = Qt.ItemDataRole.UserRole + 8        # on an object's row: the tail of its text, drawn muted
AIR = 8                                         # logical pixels above a header
_TITLE = ["#5f5a52"]                            # the theme's text2: a section's name (set_colours)


def set_colours(t: dict) -> None:
    _TITLE[0] = t["text2"]


def section(parent, text: str, count: int, columns: int = 2, column: int = 0) -> QTreeWidgetItem:
    """A header row under `parent`: not selectable, its count on every column (the delegates of each column
    read it), the text in `column` as given (the delegate writes it in capitals)."""
    texts = [""] * columns
    texts[column] = text
    it = QTreeWidgetItem(parent, texts)
    set_count(it, count)
    it.setFlags(Qt.ItemFlag.ItemIsEnabled)
    return it


def set_count(item: QTreeWidgetItem, count: int) -> None:
    for c in range(item.columnCount()):
        item.setData(c, SECTION_ROLE, count)


def is_section(index) -> bool:
    return index.siblingAtColumn(0).data(SECTION_ROLE) is not None


def header_font(font: QFont) -> QFont:
    """A section's header and its count: the catalogue's label (design.Text.LABEL)."""
    from .design import Text, text_font
    return text_font(Text.LABEL, font)


def muted_colour(option: QStyleOptionViewItem) -> QColor:
    """The muted text of the theme: the placeholder text of the palette, which the theme sets to `muted`."""
    return option.palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.PlaceholderText)


PILL_RADIUS = 4                 # the selection inside the list: Radius.INNER (ui/design.py)


def row_pill(painter: QPainter, option: QStyleOptionViewItem) -> None:
    """The selection (or the hover) of a row as one rounded pill from the view's left edge to its right one, 4 px
    in: this cell draws the part of it that falls in the cell, so that the columns make one pill."""
    view = option.widget
    selected = bool(option.state & QStyle.StateFlag.State_Selected)
    hover = bool(option.state & QStyle.StateFlag.State_MouseOver)
    if view is None or not (selected or hover):
        return
    port = view.viewport().rect()
    r = QRectF(port.left() + 4, option.rect.top() + 1, port.width() - 8, option.rect.height() - 2)
    colour = QColor(option.palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Highlight))
    if not selected:
        colour = QColor(option.palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Text))
        colour.setAlpha(18)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setClipRect(option.rect)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(colour)
    painter.drawRoundedRect(r, PILL_RADIUS, PILL_RADIUS)
    painter.restore()


class SectionDelegate(QStyledItemDelegate):
    """Draws the header rows; `column` is the one that carries the header's text (0 in the project's tree, 1 in
    the Checks panel). The other columns of a header row are drawn as usual, lowered by the air above."""

    def __init__(self, parent=None, column: int = 0, pills: bool = False, air: int = AIR):
        super().__init__(parent)
        self.column = column
        self.pills = pills              # the project's tree: the rows' pills, the count apart (T2)
        self.air = air                  # above a header

    def paint(self, painter, option, index) -> None:
        count = index.siblingAtColumn(0).data(SECTION_ROLE)
        if count is None:
            if self.pills:
                row_pill(painter, option)
            tail = index.data(TAIL_ROLE)
            if tail and index.column() == self.column:
                self._paint_with_tail(painter, option, index, tail)
            else:
                super().paint(painter, option, index)
            return
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        # the ground only: the icon is drawn below, under the air (it came twice, the by-object headers of the
        # Checks panel: found by the template's alignment, 25/10/2026)
        opt.icon = QIcon()
        opt.features &= ~QStyleOptionViewItem.ViewItemFeature.HasDecoration
        opt.state &= ~QStyle.StateFlag.State_MouseOver
        opt.state &= ~QStyle.StateFlag.State_Selected
        style = opt.widget.style() if opt.widget is not None else None
        if style is not None:
            style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)
        rect = QRect(option.rect).adjusted(0, self.air, 0, 0)
        if index.column() != self.column:
            low = QStyleOptionViewItem(option)
            low.rect = rect
            if index.column() == 0 and not self.pills and opt.widget is not None:
                # the header's mark in the column of its items' marks, as far from the name as theirs from their
                # text (R136: it stood an indentation to the left, 30 px from the name)
                low.rect = rect.adjusted(opt.widget.indentation(), 0, 0, 0)
            super().paint(painter, low, index)
            return
        painter.save()
        painter.setFont(header_font(option.font))
        name = index.data(Qt.ItemDataRole.DisplayRole) or ""
        box = rect.adjusted(4 if not self.pills else 8, 0, -2, 0)
        painter.setPen(QColor(_TITLE[0]))
        painter.drawText(box, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)
        x = box.left() + QFontMetrics(painter.font()).horizontalAdvance(name.upper())
        painter.setPen(muted_colour(option))
        tail = f"  ·  {count}" if not self.pills else f"  {count}"
        painter.drawText(QRect(x, box.top(), max(0, box.right() - x), box.height()),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, tail)
        painter.restore()

    def _paint_with_tail(self, painter, option, index, tail: str) -> None:
        """«Name · 188»: the name as usual, the tail in the muted colour after it."""
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        full = opt.text
        name = full[:-len(tail)] if tail and full.endswith(tail) else full
        opt.text = name
        style = opt.widget.style() if opt.widget is not None else None
        if style is None:
            super().paint(painter, option, index)
            return
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)
        text_rect = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, opt, opt.widget)
        x = text_rect.x() + QFontMetrics(opt.font).horizontalAdvance(name)
        painter.save()
        painter.setFont(opt.font)
        selected = bool(opt.state & QStyle.StateFlag.State_Selected)
        painter.setPen(option.palette.color(QPalette.ColorRole.HighlightedText) if selected else muted_colour(option))
        painter.drawText(QRect(x, text_rect.y(), max(0, text_rect.right() - x), text_rect.height()),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, tail)
        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        size = super().sizeHint(option, index)
        if index.siblingAtColumn(0).data(SECTION_ROLE) is not None:
            height = QFontMetrics(header_font(option.font)).height() + 6
            size.setHeight(max(size.height(), height) + self.air)
        return size
