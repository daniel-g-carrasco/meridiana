"""Choosing one name out of many (R268: the makers of the inverters, 165 of them, stood in a drop-down list as tall
as the screen): a search box that filters as one types, a list as tall as about eight rows that scrolls beyond them,
and the favourites on top, each row with a star that adds it to the favourites or takes it out. The favourites are
the user's (the caller keeps them, in the settings), the name chosen is the project's: the caller tells which one to
preselect.

Nothing here knows what the names are: the texts and the names come from the caller, with, for the names that are
best not chosen, the reason (`dimmed`: name -> why): those rows are shown attenuated, after the others, with the
reason as their tooltip, and they stay reachable. The whole list is always there: a search finds every name.

Keyboard: typing filters; Up and Down (also Page Up and Page Down) move the choice from the search box; Enter chooses;
Escape clears the search, and with it empty closes the window; Ctrl+F goes back to the search box; Ctrl+D (or Space
in the list) stars the row in hand. Colours from the palette, so the two themes and a change of theme are followed
without being told; measures from design.py.
"""

from __future__ import annotations

import math
import unicodedata

from PySide6.QtCore import QEvent, QPointF, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPainterPath, QPalette, QPen, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QDialogButtonBox, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QStyle, QStyledItemDelegate, QStyleOptionViewItem, QToolTip,
                               QVBoxLayout, QWidget)

from .. import theme_colors
from ..i18n import _
from . import design
from .design import Icon, Line, Radius, Size, Space, Text

VISIBLE_ROWS = 8                        # the list shows this many rows at most, then it scrolls
ROW = Size.CONTROL                      # a row as tall as a control
NAME_ROLE = Qt.ItemDataRole.UserRole            # the name (a header row has none)
FAVOURITE_ROLE = Qt.ItemDataRole.UserRole + 1   # True on a starred row
DIM_ROLE = Qt.ItemDataRole.UserRole + 2         # the reason a row is attenuated ("" when it is not)
STAR = Icon.CONTROL                     # the star's box
STAR_INNER = 0.42                       # the inner radius of the star, as a part of the outer one


def fold(text: str) -> str:
    """`text` for a search that minds neither case nor accents: «Hüttinger», «huttinger» and «HUTTINGER» are
    one; what is between letters (spaces, dots) stays."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def star_rect(row: QRect) -> QRect:
    """The box of the star at the right end of a row."""
    return QRect(row.right() - Space.M - STAR + 1, row.top() + (row.height() - STAR) // 2, STAR, STAR)


def star_path(box: QRectF) -> QPainterPath:
    """A five-pointed star inside `box`."""
    centre = box.center()
    outer = box.width() / 2 - 1
    inner = outer * STAR_INNER
    path = QPainterPath()
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        radius = outer if i % 2 == 0 else inner
        point = QPointF(centre.x() + radius * math.cos(angle), centre.y() + radius * math.sin(angle))
        if i == 0:
            path.moveTo(point)
        else:
            path.lineTo(point)
    path.closeSubpath()
    return path


class RowDelegate(QStyledItemDelegate):
    """A row: its pill when selected or under the pointer, the name (attenuated when the row is dimmed), the star
    (filled on a favourite, an outline on the row in hand or under the pointer); a header: its words in capitals."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        name = index.data(NAME_ROLE)
        pal = option.palette
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = option.rect
        if name is None:
            painter.setFont(design.text_font(Text.LABEL, option.font))
            painter.setPen(pal.color(QPalette.ColorGroup.Active, QPalette.ColorRole.PlaceholderText))
            text_rect = rect.adjusted(Line.TEXT_INSET, 0, -Line.TEXT_INSET, 0)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
                             index.data(Qt.ItemDataRole.DisplayRole) or "")
            painter.restore()
            return
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        # the view marks the row at its top as hovered after a scroll made by code (the list opened on the name in
        # hand), with the pointer nowhere near it: the hover pill only while the pointer is really over the list
        view = option.widget
        under = view is None or not hasattr(view, "viewport") or view.viewport().underMouse()
        hover = bool(option.state & QStyle.StateFlag.State_MouseOver) and under
        if selected or hover:
            colour = QColor(pal.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Highlight))
            if not selected:
                colour = QColor(pal.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Text))
                colour.setAlphaF(theme_colors.HOVER)            # the hover of every control (R160)
            pill = QRectF(rect.left() + Space.XS, rect.top() + 1, rect.width() - 2 * Space.XS, rect.height() - 2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(colour)
            painter.drawRoundedRect(pill, Radius.INNER, Radius.INNER)
        dimmed = bool(index.data(DIM_ROLE))
        group = QPalette.ColorGroup.Disabled if dimmed else QPalette.ColorGroup.Active
        role = QPalette.ColorRole.HighlightedText if selected and not dimmed else QPalette.ColorRole.Text
        ink = pal.color(group, role)
        star = star_rect(rect)
        painter.setFont(design.text_font(Text.BODY, option.font))
        text_rect = QRect(rect.left() + Line.TEXT_INSET, rect.top(), star.left() - Space.M - rect.left() - Line.TEXT_INSET,
                          rect.height())
        text = painter.fontMetrics().elidedText(index.data(Qt.ItemDataRole.DisplayRole) or "",
                                                Qt.TextElideMode.ElideRight, text_rect.width())
        painter.setPen(ink)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
        favourite = bool(index.data(FAVOURITE_ROLE))
        if favourite or selected or hover:
            path = star_path(QRectF(star))
            if favourite:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(pal.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Text))
            else:
                pen = QPen(pal.color(QPalette.ColorGroup.Active, QPalette.ColorRole.PlaceholderText))
                pen.setWidthF(Icon.STROKE)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        return QSize(super().sizeHint(option, index).width(), ROW)


class NameList(QListWidget):
    """The list of the picker: a click on a star toggles the favourite without choosing the row; Enter chooses,
    Space stars; a letter typed goes to the search box."""

    def __init__(self, picker: "NamePicker"):
        super().__init__(picker)
        self.picker = picker
        self.setItemDelegate(RowDelegate(self))
        self.setUniformItemSizes(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMouseTracking(True)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)

    def on_star(self, pos) -> QListWidgetItem | None:
        """The row whose star is under `pos` (viewport coordinates), if any."""
        item = self.itemAt(pos)
        if item is None or item.data(NAME_ROLE) is None:
            return None
        return item if star_rect(self.visualItemRect(item)).contains(pos) else None

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and (item := self.on_star(event.position().toPoint())):
            self.picker.toggle_favourite(item.data(NAME_ROLE))
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if self.on_star(event.position().toPoint()) is not None:
            return                                  # the second click of a quick pair is not a choice
        item = self.itemAt(event.position().toPoint())
        if item is not None and item.data(NAME_ROLE) is not None:
            self.picker.chosen.emit(item.data(NAME_ROLE))
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if (name := self.picker.current()) is not None:
                self.picker.chosen.emit(name)
            return
        if key == Qt.Key.Key_Space:
            if (name := self.picker.current()) is not None:
                self.picker.toggle_favourite(name)
            return
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_PageUp, Qt.Key.Key_PageDown, Qt.Key.Key_Home,
                   Qt.Key.Key_End):
            self.picker.step(key)
            return
        text = event.text()
        if text and text.isprintable() and not (event.modifiers() & ~Qt.KeyboardModifier.ShiftModifier):
            self.picker.search.setFocus()
            self.picker.search.insert(text)
            return
        super().keyPressEvent(event)

    def event(self, event) -> bool:
        if event.type() == QEvent.Type.ToolTip:
            pos = self.viewport().mapFromGlobal(event.globalPos())
            item = self.itemAt(pos)
            if item is not None and item.data(NAME_ROLE) is not None:
                if star_rect(self.visualItemRect(item)).contains(pos):
                    text = (_("Remove from favourites (Ctrl+D)") if item.data(FAVOURITE_ROLE)
                            else _("Add to favourites (Ctrl+D)"))
                else:
                    text = item.data(DIM_ROLE) or ""
                if text:
                    QToolTip.showText(event.globalPos(), text, self)
                else:
                    QToolTip.hideText()
                return True
        return super().event(event)


class NamePicker(QWidget):
    """The search box over the list. `names` in the order the caller wants them (the alphabet, as a rule), `current`
    the one to preselect, `favourites` the user's (a name not in `names` is kept but not shown), `dimmed` the names
    best not chosen with the reason, `placeholder` the search box's words. `favourites()` gives the list as it
    stands, `current()` the name in hand; `chosen` says Enter or a double click, `favouritesChanged` every star."""

    favouritesChanged = Signal(list)
    currentChanged = Signal(object)         # the name, or None
    chosen = Signal(str)

    def __init__(self, names: list[str], *, current: str = "", favourites=(), dimmed: dict | None = None,
                 placeholder: str = "", favourites_title: str = "", others_title: str = "", parent=None):
        super().__init__(parent)
        self.names = list(names)
        self.dimmed = dict(dimmed or {})
        self._favourites = [n for n in favourites if isinstance(n, str)]
        self.favourites_title = favourites_title or _("Favourites")
        self.others_title = others_title or _("All")
        self._current = current
        self.search = QLineEdit(self)
        self.search.setPlaceholderText(placeholder or _("Search…"))
        self.search.setClearButtonEnabled(True)
        design.set_text(self.search, Text.BODY)
        self.list = NameList(self)
        # as tall as VISIBLE_ROWS rows at most, and no taller than the whole list needs when it is short (the headers
        # count as rows); fixed, so that a search that shortens the list moves nothing around it
        favourites_shown, others = self._sections("")
        rows = len(favourites_shown) + len(others) + (2 if favourites_shown and others else 1 if favourites_shown else 0)
        self.list.setFixedHeight(max(3, min(VISIBLE_ROWS, rows)) * ROW + 2 * Line.HAIR)
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(Space.M)
        box.addWidget(self.search)
        box.addWidget(self.list)
        self.search.textChanged.connect(self._refill)
        self.search.installEventFilter(self)
        self.list.currentItemChanged.connect(self._current_item_changed)
        find = QShortcut(QKeySequence.StandardKey.Find, self)
        find.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        find.activated.connect(self.focus_search)
        star = QShortcut(QKeySequence("Ctrl+D"), self)
        star.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        star.activated.connect(self._star_current)
        self.setFocusProxy(self.search)
        self._refill()
        self.list.setMinimumWidth(self._width_for_names())

    # -- what the caller reads -----------------------------------------------------------------------------------

    def favourites(self) -> list[str]:
        return list(self._favourites)

    def current(self) -> str | None:
        item = self.list.currentItem()
        return item.data(NAME_ROLE) if item is not None else None

    def query(self) -> str:
        return self.search.text()

    def shown(self) -> list[str]:
        """The names in the list now, in their order (headers left out)."""
        return [item.data(NAME_ROLE) for item in self._items() if item.data(NAME_ROLE) is not None]

    def headers(self) -> list[str]:
        return [item.text() for item in self._items() if item.data(NAME_ROLE) is None]

    # -- what the user does ----------------------------------------------------------------------------------------

    def focus_search(self) -> None:
        self.search.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.search.selectAll()

    def toggle_favourite(self, name: str) -> None:
        if name in self._favourites:
            self._favourites.remove(name)
        else:
            self._favourites.append(name)
        self._refill()
        self.favouritesChanged.emit(self.favourites())

    def set_current(self, name: str) -> None:
        """The row of `name` in hand, when it is in the list."""
        for item in self._items():
            if item.data(NAME_ROLE) == name:
                self.list.setCurrentItem(item)
                return

    def step(self, key) -> None:
        """The choice moved by a key (Up, Down, Page Up, Page Down, Home, End) over the rows that are names."""
        rows = [i for i in range(self.list.count()) if self.list.item(i).data(NAME_ROLE) is not None]
        if not rows:
            return
        here = self.list.currentRow()
        at = rows.index(here) if here in rows else -1
        page = VISIBLE_ROWS - 1
        if key == Qt.Key.Key_Down:
            at = min(at + 1, len(rows) - 1)
        elif key == Qt.Key.Key_Up:
            at = max(at - 1, 0) if at >= 0 else 0
        elif key == Qt.Key.Key_PageDown:
            at = min(at + page, len(rows) - 1)
        elif key == Qt.Key.Key_PageUp:
            at = max(at - page, 0)
        elif key == Qt.Key.Key_Home:
            at = 0
        elif key == Qt.Key.Key_End:
            at = len(rows) - 1
        self.list.setCurrentRow(rows[at])
        self.list.scrollToItem(self.list.item(rows[at]))

    def eventFilter(self, obj, event) -> bool:
        if obj is self.search and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
                self.step(key)
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if (name := self.current()) is not None:
                    self.chosen.emit(name)
                return True
            if key == Qt.Key.Key_Escape and self.search.text():
                self.search.clear()                 # the first Escape clears the search, the second closes
                return True
        return super().eventFilter(obj, event)

    # -- inside ----------------------------------------------------------------------------------------------------

    def _items(self):
        return [self.list.item(i) for i in range(self.list.count())]

    def _star_current(self) -> None:
        if (name := self.current()) is not None:
            self.toggle_favourite(name)

    def _current_item_changed(self, item, _before) -> None:
        name = item.data(NAME_ROLE) if item is not None else None
        if name is not None:
            self._current = name
        self.currentChanged.emit(name)

    def _width_for_names(self) -> int:
        metrics = self.list.fontMetrics()
        widest = max((metrics.horizontalAdvance(n) for n in self.names), default=0)
        wanted = Line.TEXT_INSET + widest + Space.M + STAR + Space.M + Size.SCROLLBAR + 2 * Line.HAIR
        return max(240, min(wanted, 420))

    def _sections(self, query: str) -> tuple[list[str], list[str]]:
        """(the favourites shown, the other names shown), filtered by `query`; among the others the dimmed ones last,
        each part in the caller's order."""
        needle = fold(query.strip())
        known = {n for n in self.names}
        favourites = [n for n in self._favourites if n in known and needle in fold(n)]
        rest = [n for n in self.names if n not in self._favourites and needle in fold(n)]
        others = [n for n in rest if n not in self.dimmed] + [n for n in rest if n in self.dimmed]
        return favourites, others

    def _refill(self) -> None:
        wanted = self._current
        favourites, others = self._sections(self.search.text())
        self.list.blockSignals(True)
        self.list.clear()
        if favourites:
            self._add_header(self.favourites_title)
            for name in favourites:
                self._add_name(name)
            if others:
                self._add_header(self.others_title)
        for name in others:
            self._add_name(name)
        self.list.blockSignals(False)
        names = self.shown()
        if wanted and any(fold(n) == fold(wanted) for n in names):
            target = next(n for n in names if fold(n) == fold(wanted))
        else:
            target = names[0] if names else None
        if target is not None:
            self.set_current(target)
            self.list.scrollToItem(self.list.currentItem())
        else:
            self.currentChanged.emit(None)

    def _add_header(self, text: str) -> None:
        item = QListWidgetItem(text)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.list.addItem(item)

    def _add_name(self, name: str) -> None:
        item = QListWidgetItem(name)
        item.setData(NAME_ROLE, name)
        item.setData(FAVOURITE_ROLE, name in self._favourites)
        item.setData(DIM_ROLE, self.dimmed.get(name, ""))
        item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        self.list.addItem(item)


class NameDialog(QDialog):
    """A little window around the picker: the prompt, the picker, OK and Cancel. `ask` runs it and answers (the
    name, whether OK was pressed, the favourites as they stand): the favourites are the user's, so the caller keeps
    them also when the window was cancelled."""

    def __init__(self, parent, title: str, prompt: str, names: list[str], *, current: str = "", favourites=(),
                 dimmed: dict | None = None, placeholder: str = "", favourites_title: str = "",
                 others_title: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.picker = NamePicker(names, current=current, favourites=favourites, dimmed=dimmed,
                                 placeholder=placeholder, favourites_title=favourites_title,
                                 others_title=others_title, parent=self)
        box = QVBoxLayout(self)
        box.setContentsMargins(Space.L, Space.L, Space.L, Space.L)
        box.setSpacing(Space.M)
        if prompt:
            label = QLabel(prompt)
            label.setWordWrap(True)
            design.set_text(label, Text.BODY)
            box.addWidget(label)
        box.addWidget(self.picker)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        box.addWidget(self.buttons)
        self.picker.chosen.connect(self._chosen)
        self.picker.currentChanged.connect(self._current_changed)
        self._current_changed(self.picker.current())
        self.picker.focus_search()

    @classmethod
    def ask(cls, parent, title: str, prompt: str, names: list[str], *, current: str = "", favourites=(),
            dimmed: dict | None = None, placeholder: str = "", favourites_title: str = "",
            others_title: str = "") -> tuple[str, bool, list[str]]:
        dialog = cls(parent, title, prompt, names, current=current, favourites=favourites, dimmed=dimmed,
                     placeholder=placeholder, favourites_title=favourites_title, others_title=others_title)
        ok = dialog.exec() == QDialog.DialogCode.Accepted
        chosen = dialog.chosen() if ok else ""
        favourites_now = dialog.favourites()
        dialog.deleteLater()
        return chosen, ok, favourites_now

    def chosen(self) -> str:
        return self.picker.current() or ""

    def favourites(self) -> list[str]:
        return self.picker.favourites()

    def _chosen(self, _name: str) -> None:
        self.accept()

    def _current_changed(self, name) -> None:
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(name is not None)

    def accept(self) -> None:
        if self.picker.current() is None:
            return                                  # nothing in the list for the search typed: nothing to choose
        super().accept()
