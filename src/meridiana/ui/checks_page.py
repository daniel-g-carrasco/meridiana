"""The checks of the project in one list (study 17, F; design document, 3.8): by level as the default (TO FIX,
TO CHECK, TO KNOW, PASSED closed), by object or by area from the menu in the head, and «ready for delivery»
for the Report phase (what is to fix and to check, the values still at their default, the estimates in use);
the sections are the headers of the project's tree (SectionDelegate). Each row is one short sentence with its
mark and its source; a click on a row opens its detail (why, and what to do) as a wrapped row under it, no row is
ever selected (R125). «Fix…» and the eye sit on the row where they serve: the eye takes the views to where the
problem is, framed, the rest dimmed (R127); «Fix…» shows the fix before it is kept (R126). The items of the object
selected in the views stand out (study 12, C4). The filters are the counts in the head, each a level that stays
pressed (R130), «This phase» and «This object» (the marks of the tree set the latter, R30); the counts in the
status bar lead to the section. Ctrl+. asks the fix of the row the keyboard is on; the notes of the rules that
apply can be copied for the technical report."""

from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QActionGroup, QBrush, QColor, QFont, QFontMetrics, QGuiApplication, QPainter,
                           QPainterPath, QPalette, QPen)
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QLabel, QMenu, QPushButton,
                               QSizePolicy, QStyle, QStyleOptionToolButton, QStyleOptionViewItem,
                               QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import checks, theme_colors
from ..i18n import _
from . import icons, symbols
from .cards import default_tokens
from .design import Radius, Space
from .sections import SectionDelegate, is_section, section

# the status colours of the charts' palette (critical, warning, good), on the mark only: the mark and the words
# carry the meaning, the colour helps; what is only worth knowing keeps the colour of the text
COLOURS = {"fail": theme_colors.STATUS["critical"], "warn": theme_colors.STATUS["warning"],
           "ok": theme_colors.STATUS["good"]}
DETAIL_ROLE = Qt.ItemDataRole.UserRole + 9      # on the row under an item: its detail, drawn wrapped
GROUP_ROLE = Qt.ItemDataRole.UserRole + 10      # on a header: the key of its group (checks.Group.key)
CLOSED_ROLE = Qt.ItemDataRole.UserRole + 11     # on a header: shown closed by default
SYMBOL_ROLE = Qt.ItemDataRole.UserRole + 12     # on a header or an item: the name of its symbol (ui/symbols.py)
COUNTS_ROLE = Qt.ItemDataRole.UserRole + 13     # on a header by object or by area: [(symbol, count), ...]
COUNT_SYMBOL = 14                               # a count's symbol, the size of a symbol in a line of text
COUNT_GAP = (3, 10)                             # from a count's symbol to its number, from a number to the next
RESIZE_SETTLE_MS = 90
PAD = Space.S                                   # around the detail's text
DETAIL_BOTTOM = 10                              # under the detail, before the line to the next item
ROW_HEIGHT = 34         # an item's row: «Fix…» and the eye (Size.CHIP) inside it with air (R124: «Correggi» was cut)
SECTION_AIR = Space.XL  # above a section's header: the sections a little further apart than the tree's (R136)
DETAIL_CHARS = 100      # the detail wraps at about this many characters, not at the panel's edge (R129)

level_names = checks.level_names


def view_names() -> dict:
    return {"level": _("By level"), "object": _("By object"), "area": _("By area"),
            "delivery": _("Ready for delivery")}


def object_names(project) -> dict:
    """(kind, id) -> the name the tree shows, for the view by object; the site with the project's name."""
    from .properties import exclusion_names
    names = {("site", ""): _("Site: {name}").format(name=project.name)}
    for b in project.buildings:
        names[("building", b.id)] = b.name
    for s in project.subfields:
        names[("subfield", s.id)] = s.name
    kinds, numbers = exclusion_names(), project.exclusion_numbers()
    for e in project.exclusions:
        names[("exclusion", e.id)] = f"{kinds.get(e.kind, e.kind)} {numbers[e.id]}"
    return names


class ChecksDelegate(SectionDelegate):
    """The sections' delegate, and the detail of an item as a row of wrapped text that spans the columns (the
    detail that matters does not go in a tooltip: NN/g, study 17, F.5)."""

    def _text_left(self, index) -> int:
        """Where the item's text starts in the viewport (its column, its padding, the style's margin): the detail
        stands under it, the mark's column before."""
        return self.parent().header().sectionViewportPosition(1) + 5

    def _detail_rect(self, index, option) -> QRect:
        tree = self.parent()
        from .checks_page import CARD_INSET
        left = max(option.rect.left(), self._text_left(index))
        right = tree.viewport().width() - CARD_INSET - 2 * PAD
        measure = QFontMetrics(self.detail_font(option.font)).averageCharWidth() * DETAIL_CHARS
        return QRect(left, option.rect.top(), max(80, min(right - left, measure)), option.rect.height())

    @staticmethod
    def detail_font(font):
        from .design import Type
        from .design import font as scaled
        return scaled(Type.SMALL, Type.REGULAR, font)

    def paint(self, painter, option, index) -> None:
        counts = index.data(COUNTS_ROLE)
        if counts:
            self._paint_counts(painter, option, counts)
            return
        if index.data(DETAIL_ROLE) is None:
            # the selection and the hover are the card's pill (ChecksTree._card_slice): the cells draw as at rest,
            # so the mark keeps its colour
            opt = QStyleOptionViewItem(option)
            opt.state &= ~QStyle.StateFlag.State_Selected
            opt.state &= ~QStyle.StateFlag.State_MouseOver
            super().paint(painter, opt, index)
            return
        painter.save()
        painter.setFont(self.detail_font(option.font))
        painter.setPen(option.palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.PlaceholderText).darker(
            115) if option.palette.color(QPalette.ColorRole.Base).lightness() > 128 else
            option.palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.PlaceholderText).lighter(125))
        painter.drawText(self._detail_rect(index, option).adjusted(0, 0, 0, -DETAIL_BOTTOM),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
                         index.data(Qt.ItemDataRole.DisplayRole) or "")
        painter.restore()

    def _paint_counts(self, painter, option, counts) -> None:
        """The counts by level of a header: each its symbol and its number, muted, on the header's line (below
        the air above it); the levels' names are in the tooltip (R138: they were the characters ✘ ⚠ ℹ ✔)."""
        r = option.rect
        middle = (r.top() + self.air + r.bottom() + 1) / 2
        x = float(r.left() + PAD)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(option.font)
        painter.setPen(option.palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.PlaceholderText))
        metrics = QFontMetrics(option.font)
        for name, n in counts:
            symbols.paint(painter, QRectF(x, middle - COUNT_SYMBOL / 2, COUNT_SYMBOL, COUNT_SYMBOL), name)
            x += COUNT_SYMBOL + COUNT_GAP[0]
            text = str(n)
            painter.drawText(QRectF(x, r.top() + self.air, metrics.horizontalAdvance(text) + 2, r.height() - self.air),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
            x += metrics.horizontalAdvance(text) + COUNT_GAP[1]
        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        if index.data(DETAIL_ROLE) is None:
            size = super().sizeHint(option, index)
            if index.parent().isValid():                # an item's row, not a section's header
                size.setHeight(max(size.height(), ROW_HEIGHT))
            return size
        r = self._detail_rect(index, option)
        rect = QFontMetrics(self.detail_font(option.font)).boundingRect(
            QRect(0, 0, r.width(), 0), Qt.TextFlag.TextWordWrap, index.data(Qt.ItemDataRole.DisplayRole) or "")
        return QSize(rect.width(), rect.height() + DETAIL_BOTTOM)


CARD_INSET = Space.M  # the cards of the items from the panel's sides (F2)
CARD_RADIUS = Radius.CONTROL


class ChecksTree(QTreeWidget):
    """A tree whose rows are laid out again when its width changes: the details wrap to the width. The items of
    a section stand in one card (F2, the target of 24/10/2026): each row draws its slice of it before its
    cells, the first with the top corners, the last with the bottom ones, a soft line between two items, the
    detail on the tonal veil. Nothing is selected (R125): the row under the pointer has a rounded ground, the one
    the keyboard is on a thin line too. A click on a row opens or closes its detail; Enter shows where the problem
    is (`shown`). `colours` are the theme's."""

    shown = Signal(object)          # the row whose place the keyboard asked for (Enter)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("checks-tree")
        self.hover_item: QTreeWidgetItem | None = None     # the item under the pointer, its detail counted in
        self.keyboard = False                               # the last move came from the keyboard
        self.viewport().setMouseTracking(True)
        t = default_tokens()
        self.colours = {"card": t["card"], "line": t["line"], "sink": t["field"], "select": t["select_bg"],
                        "hover": theme_colors.qt_hex(t["hover"]), "focus": t["accent"]}
        # the rows laid out again once the width rests: at every step of a panel's edge dragged it measured every
        # row's wrapped detail (4 500 times in 40 steps, R120)
        self.relayout = QTimer(self)
        self.relayout.setSingleShot(True)
        self.relayout.setInterval(RESIZE_SETTLE_MS)
        self.relayout.timeout.connect(self._width_settled)

    SOURCE_SHARE = 0.28          # the source's column at most this much of the width: the text first (24/10/2026)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if event.oldSize().width() != event.size().width():
            if event.oldSize().width() < 0:
                self._width_settled()
            else:
                self.relayout.start()

    def _width_settled(self) -> None:
        self.fit_source()
        self.scheduleDelayedItemsLayout()

    def fit_source(self) -> None:
        """The source as wide as its longest, up to SOURCE_SHARE of the width; longer ones are shortened (their
        whole text in the tooltip). The column of what is checked takes the rest. Measured on every row, the closed
        sections' too: Qt's measure saw only the rows shown, none while the sections were still closed, and the
        sources came out as «C…» (R128)."""
        want = 0
        stack = [self.topLevelItem(i) for i in range(self.topLevelItemCount())]
        while stack:
            it = stack.pop()
            if it.text(2):
                want = max(want, QFontMetrics(it.font(2)).horizontalAdvance(it.text(2)))
            counts = it.data(2, COUNTS_ROLE)
            if counts:
                metrics = QFontMetrics(self.font())
                want = max(want, sum(COUNT_SYMBOL + COUNT_GAP[0] + metrics.horizontalAdvance(str(n)) + COUNT_GAP[1]
                                     for _name, n in counts))
            stack.extend(it.child(i) for i in range(it.childCount()) if not it.child(i).data(0, DETAIL_ROLE))
        want += 2 * PAD + 8 if want else 0              # the item's padding and the style's margin
        width = min(want, int(self.viewport().width() * self.SOURCE_SHARE))
        if self.header().sectionSize(2) != width:
            self.header().resizeSection(2, max(0, width))

    def _row_of(self, pos) -> QTreeWidgetItem | None:
        """The item's row at `pos` (not a section's header, not a detail)."""
        index = self.indexAt(pos)
        item = self.itemFromIndex(index.siblingAtColumn(0)) if index.isValid() else None
        if item is None or item.parent() is None or item.data(0, DETAIL_ROLE):
            return None
        return item

    def _arrow_of(self, pos) -> QTreeWidgetItem | None:
        """The item whose arrow is at `pos`, if it has one there."""
        index = self.indexAt(pos)
        if not index.isValid():
            return None
        item = self.itemFromIndex(index.siblingAtColumn(0))
        left = self.visualRect(index.siblingAtColumn(0)).left()
        if item is None or not item.childCount() or not left - self.indentation() <= pos.x() < left:
            return None
        return item

    def _item_at(self, pos) -> QTreeWidgetItem | None:
        """The item at `pos`, the one its detail belongs to when the detail is there; none on a section's header."""
        index = self.indexAt(pos)
        item = self.itemFromIndex(index.siblingAtColumn(0)) if index.isValid() else None
        if item is not None and item.data(0, DETAIL_ROLE):
            item = item.parent()
        return item if item is not None and item.parent() is not None else None

    def mouseMoveEvent(self, event) -> None:
        item = self._item_at(event.position().toPoint())
        if item is not self.hover_item or self.keyboard:
            self.hover_item, self.keyboard = item, False
            self.viewport().update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        if self.hover_item is not None:
            self.hover_item = None
            self.viewport().update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        """A click on a row, or on its arrow, opens and closes its detail and does nothing else: no selection
        (R125), the list and the views stay where they are (Daniel, 24/10/2026: opening a row moved the list). A click
        on an open detail does nothing (R153: it moved the keyboard's row there and half erased the tint)."""
        pos = event.position().toPoint()
        self.keyboard = False
        index = self.indexAt(pos)
        if index.isValid() and index.siblingAtColumn(0).data(DETAIL_ROLE):
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            row = self._arrow_of(pos) or self._row_of(pos)
            if row is not None:
                self.blockSignals(True)
                self.setCurrentItem(row)                # where the keyboard goes on from, drawn only with the focus
                self.blockSignals(False)
                if row.childCount():
                    row.setExpanded(not row.isExpanded())
                self.setFocus(Qt.FocusReason.MouseFocusReason)
                self.viewport().update()
                event.accept()
                return
        elif event.button() == Qt.MouseButton.RightButton and self._row_of(pos) is not None:
            event.accept()                              # the menu, without taking the row (customContextMenuRequested)
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        """A double click is a click: the detail opened once, never opened and closed again."""
        pos = event.position().toPoint()
        if event.button() == Qt.MouseButton.LeftButton and (self._arrow_of(pos) or self._row_of(pos)) is not None:
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event) -> None:
        """Space opens and closes the detail of the row the keyboard is on, Enter shows where its problem is."""
        self.keyboard = True
        self.viewport().update()
        row = self.currentItem()
        if row is not None and row.parent() is not None and not row.data(0, DETAIL_ROLE):
            if event.key() == Qt.Key.Key_Space and row.childCount():
                row.setExpanded(not row.isExpanded())
                event.accept()
                return
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.shown.emit(row)
                event.accept()
                return
        super().keyPressEvent(event)

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self.viewport().update()

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self.viewport().update()

    def drawBranches(self, painter, rect, index) -> None:
        """A section's arrow at the height of its name, under the air above it, not in the middle of the whole row
        (R136: it stood higher than the text)."""
        if is_section(index):
            rect = rect.adjusted(0, SECTION_AIR, 0, 0)
        super().drawBranches(painter, rect, index)

    def drawRow(self, painter, option, index) -> None:
        item = self.itemFromIndex(index)
        parent = item.parent() if item is not None else None
        if item is not None and parent is not None:
            self._card_slice(painter, option, item, parent)
        super().drawRow(painter, option, index)

    def _card_slice(self, painter, option, item, parent) -> None:
        detail = bool(item.data(0, DETAIL_ROLE))
        row = item if not detail else parent                # the item the slice belongs to
        section = row.parent()
        if section is None:
            return
        n = section.indexOfChild(row)
        first = n == 0 and not detail
        opened = row.childCount() > 0 and row.isExpanded()
        last = n == section.childCount() - 1 and (detail or not opened)
        port = self.viewport().rect()
        r = QRectF(port.left() + CARD_INSET + 0.5, option.rect.top() + 0.5, port.width() - 2 * CARD_INSET - 1,
                   option.rect.height())
        c = self.colours
        shape = QPainterPath()
        top = r.top() - (0 if first else CARD_RADIUS)
        bottom = r.bottom() + (-1 if last else CARD_RADIUS)
        shape.addRoundedRect(QRectF(r.left(), top, r.width(), bottom - top), CARD_RADIUS, CARD_RADIUS)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipRect(QRectF(r.left() - 1, r.top() - 0.5, r.width() + 2, r.height()))
        painter.fillPath(shape, QColor(c["card"]))           # the detail on the card, as libadwaita's expander rows
        # the item under the pointer, its detail with it, a little darker as one container; the one the keyboard
        # moved to the same; nothing stays selected (R125, R153: «cambia solo leggermente colore di tutto il suo
        # contenitore»: the pill inside the card, half drawn when the detail was clicked, is gone)
        if row is self.hover_item or (self.keyboard and self.hasFocus() and self.currentItem() is row):
            painter.fillPath(shape, QColor(c["hover"]))
        painter.setPen(QPen(QColor(c["line"]), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(shape)
        if not last and not (opened and not detail):         # the line between two items
            y = r.top() + r.height() - 1
            painter.drawLine(QRectF(r.left(), y, r.width(), 0).topLeft(), QRectF(r.left(), y, r.width(), 0).topRight())
        painter.restore()


class CountChip(QToolButton):
    """The head's level filter: the same quiet status pill as the tree, at the 24 px interactive size.
    Its state stays visible while its level is selected; two digit slots keep the four filters equal."""

    def __init__(self, level: str):
        super().__init__()
        from .marks import icon as mark_icon
        self.level = level
        self.setObjectName("count")
        self.setCheckable(True)
        self.setAutoRaise(True)
        self.setIcon(mark_icon(level))

    def sizeHint(self) -> QSize:
        from . import status_pill
        from .design import Size, Text, text_font
        return status_pill.size_hint(self.text(), text_font(Text.LABEL, self.font()), Size.CHIP, reserve="88")

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event) -> None:
        from . import status_pill
        from .design import Text, text_font
        p = QPainter(self)
        opt = QStyleOptionToolButton()
        self.initStyleOption(opt)
        status_pill.paint(p, QRectF(self.rect()), self.level, self.text(), text_font(Text.LABEL, self.font()),
                          opt.palette, checked=self.isChecked(), hovered=bool(opt.state & QStyle.StateFlag.State_MouseOver),
                          focused=bool(opt.state & QStyle.StateFlag.State_HasFocus), pressed=self.isDown(),
                          enabled=self.isEnabled())


class ChecksPage(QWidget):
    navigate = Signal(tuple)          # an item's target: ("subfield", id), ("building", id), ("phase", id), ("site",)
    fix = Signal(object)              # the item whose fix the designer asked for: shown first (R126)
    previewAnswered = Signal(bool)    # the fix shown: kept (True) or taken back (False)
    ask = Signal(object)              # the item the designer asks Meridio about (task 14)
    focusRequested = Signal(tuple)    # the eye, Enter: the place of an item's problem, to show (R127)
    viewChanged = Signal(str)         # the view chosen in the head (checks.BY), for the settings

    def __init__(self, parent=None, view: str = "level"):
        super().__init__(parent)
        self.view = view if view in checks.BY else "level"
        self.items: list[checks.Item] = []          # the checks
        self.extras: list[checks.Item] = []         # the values still at their default (the delivery view)
        self.all: list[checks.Item] = []            # items + extras: what the rows' indices point into
        self.names: dict = {}                       # (kind, id) -> name, for the view by object
        self.rows: dict[int, QTreeWidgetItem] = {}
        self.groups: dict[tuple, QTreeWidgetItem] = {}
        self.opened: set = set()                    # (target, text) of the items whose detail is open
        self.phase = "model"                        # the phase the window shows (phases.py)
        self.phase_only = False
        # the checks of one object, from its mark in the project's tree (R30) or from «This object»
        self.subset_key: tuple | None = None
        self.subset_name = ""
        self.subset: set | None = None
        self.related: tuple = ()
        self.levels: set = set()                    # the levels the counts keep (R130); none pressed, all
        self.ask_on = True                          # Meridio is there to be asked (the window says)
        self.notes_text = lambda: ""                # the window gives the text of the notes
        self.expand_pending = False
        box = QVBoxLayout(self)
        head = QHBoxLayout()
        # the view, from a menu in the head (study 17, F.5): the choice is kept in the settings
        self.view_button = QToolButton()
        self.view_button.setObjectName("filter")
        self.view_button.setAutoRaise(True)
        self.view_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.view_button.setToolTip(_("How the checks are grouped: by level, by object, by area, or what to look at "
                                      "before delivering"))
        self.view_menu = QMenu(self.view_button)
        self.view_actions = QActionGroup(self.view_menu)
        self.view_actions.setExclusive(True)
        for key, name in view_names().items():
            a = self.view_menu.addAction(name)
            a.setCheckable(True)
            a.setData(key)
            a.setChecked(key == self.view)
            self.view_actions.addAction(a)
        self.view_actions.triggered.connect(lambda a: self.set_view(a.data()))
        self.view_button.setMenu(self.view_menu)
        head.addWidget(self.view_button)
        # the counts, each a link to its section (C9: the sections absorb the filters by level)
        self.summary = QLabel()
        # one line that never resizes the panel: wrapped, a new count made the card 18 px taller and the views
        # jumped (test_viewbar caught it); cut when narrow, the counts are in the status bar too
        self.summary.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.summary.setMinimumWidth(1)
        self.summary.setTextFormat(Qt.TextFormat.RichText)
        self.summary.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self.summary.linkActivated.connect(self.go_to)
        head.addWidget(self.summary, 1)
        # the counts as pills, each with its mark and its number, each a filter that stays pressed (R130)
        self.counts: dict = {}
        for lv in checks.LEVELS:
            b = CountChip(lv)
            b.toggled.connect(lambda on, lv=lv: self._level_toggled(lv, on))
            head.addWidget(b)
            self.counts[lv] = b
        head.addSpacing(8)
        # the two filters that are real questions (design 3.8): this phase, this object
        self.phase_button = QToolButton()
        self.phase_button.setObjectName("filter")
        self.phase_button.setCheckable(True)
        self.phase_button.setAutoRaise(True)
        self.phase_button.setText(_("This phase"))
        self.phase_button.setToolTip(_("Only the checks acted on in the phase shown, and those of every phase"))
        self.phase_button.toggled.connect(self._phase_toggled)
        head.addWidget(self.phase_button)
        self.object_button = QToolButton()
        self.object_button.setObjectName("filter")
        self.object_button.setCheckable(True)
        self.object_button.setAutoRaise(True)
        self.object_button.setText(_("This object"))
        self.object_button.setToolTip(_("Only the checks of the object selected in the views or in the tree"))
        self.object_button.toggled.connect(self._object_toggled)
        head.addWidget(self.object_button)
        # the chips and the counts: pills of the global sheet (ui/theme.py, Button.CHIP)
        box.addLayout(head)
        # a fix asked for, said before it is kept (R126: «"correggi" dovrebbe presentare le correzioni proposte
        # prima di applicarle all'istante»): an edit is made as a preview with the views on it, Keep or Take back;
        # what is not an edit waits for Apply
        from .design import Space
        self.preview = QFrame()
        self.preview.setObjectName("fix-preview")
        self.preview.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        bar = QHBoxLayout(self.preview)
        bar.setContentsMargins(Space.L, Space.XS, Space.XS, Space.XS)
        bar.setSpacing(Space.S)
        self.preview_text = QLabel()
        self.preview_text.setObjectName("fix-preview-text")
        self.preview_text.setWordWrap(True)
        bar.addWidget(self.preview_text, 1)
        self.preview_keep = QPushButton(symbols.icon("check"), _("Keep"))
        self.preview_keep.clicked.connect(lambda: self._answer(True))
        bar.addWidget(self.preview_keep)
        self.preview_drop = QPushButton(symbols.icon("cross"), _("Take back"))
        self.preview_drop.clicked.connect(lambda: self._answer(False))
        bar.addWidget(self.preview_drop)
        self.preview.hide()
        box.addWidget(self.preview)
        self.tree = ChecksTree()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["", _("What"), _("Source"), ""])
        self.tree.setHeaderHidden(True)                 # F2: the columns speak for themselves
        # the details open at once: Qt's animation was slow and moved the list (Daniel, 24/10/2026)
        self.tree.setAnimated(False)
        self.tree.setIndentation(16)
        self.tree.setRootIsDecorated(True)
        self.tree.setWordWrap(True)
        self.tree.setUniformRowHeights(False)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)      # R125
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.setItemDelegate(ChecksDelegate(self.tree, column=1, air=SECTION_AIR))   # the sections, the details
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)          # ChecksTree.fit_source
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(False)
        self.tree.customContextMenuRequested.connect(self._menu)
        self.tree.shown.connect(lambda row: self._eye(row.data(1, Qt.ItemDataRole.UserRole)))
        self.tree.itemExpanded.connect(lambda it: self._remember(it, True))
        self.tree.itemCollapsed.connect(lambda it: self._remember(it, False))
        box.addWidget(self.tree, 1)
        # below, what is about the whole list: «Fix» and «Ask Meridio» are on each row and in its menu (R125: no row
        # is in hand to act on from here)
        row = QHBoxLayout()
        row.addStretch(1)
        self.copy_button = QPushButton(_("Copy the notes for the report"))
        self.copy_button.setToolTip(_("The paragraphs of the rules that apply, with their sources, to paste into the "
                                      "technical report"))
        self.copy_button.clicked.connect(self._copy)
        row.addWidget(self.copy_button)
        box.addLayout(row)
        # the list's bar against the card's right line as in the other cards; the rows above and below keep the
        # margin, in line with the list's content (R182, Daniel 26/10/2026: «la barra di scorrimento ... è
        # posizionata diversamente in queste due schede ... mi piace di più la versione più attaccata al bordo
        # destro della scheda»)
        m = box.contentsMargins()
        box.setContentsMargins(m.left(), m.top(), 0, m.bottom())
        for line in (head, row):
            line.setContentsMargins(0, 0, m.right(), 0)
        self._view_texts()
        self._summary()

    # ----- filling

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self.expand_pending:
            self.expand_pending = False
            self._expand()

    def show_items(self, items: list[checks.Item], extras=(), names: dict | None = None) -> None:
        """The checks, the values still at their default (checks.defaults_in_use, for the delivery view) and the
        names of the objects (object_names). The item in hand, the open details and the filters stay."""
        current = self.selected_index()
        self.items, self.extras = list(items), list(extras)
        self.all = self.items + self.extras
        if names is not None:
            self.names = dict(names)
        self._fill()
        if self.subset_key is not None:                 # the object's items, as the new list numbers them
            self._subset_of(self.subset_key)
        self._apply()
        if self.related:
            self._mark_related()
        self._restore(current)

    def set_view(self, view: str) -> None:
        """One of checks.BY: the same rows grouped another way; the item in hand stays in hand."""
        if view not in checks.BY:
            raise ValueError(f"view {view!r}")
        if view == self.view:
            return
        current = self.selected_index()
        self.view = view
        self._view_texts()
        self._fill()
        self._apply()
        if self.related:
            self._mark_related()
        self._restore(current)
        self.viewChanged.emit(view)

    def set_colours(self, t: dict) -> None:
        """The theme's colours for the cards of the items (F2) and the counts' ink."""
        for b in self.counts.values():
            b.update()
        # the cards of the items stand apart from the panel in both themes: in the dark one the card is the panel,
        # so a veil of white lifts them, and their line is the full one (Daniel, 24/10/2026: «non si intuiscono i
        # confini delle sottoschede»)
        dark = theme_colors.luminance(t["panel"]) < 0.2
        card = theme_colors.mix(t["panel"], "#ffffff", 0.045) if dark else t["card"]
        self.tree.colours = {"card": card, "line": t["line"], "sink": t["field"], "select": t["select_bg"],
                             "hover": theme_colors.qt_hex(t["hover"]), "focus": t["accent"]}      # R160
        self.tree.viewport().update()

    def _view_texts(self) -> None:
        self.view_button.setText(view_names()[self.view])
        for a in self.view_actions.actions():
            a.setChecked(a.data() == self.view)

    def _fill(self) -> None:
        self.tree.blockSignals(True)
        self.tree.clear()
        self.rows, self.groups = {}, {}
        source = self.all if self.view == "delivery" else self.items
        muted = QBrush(self.palette().color(QPalette.ColorGroup.Active, QPalette.ColorRole.PlaceholderText))
        for g in checks.grouped(source, self.view, self.names):
            # a section's header (study 17, T2 and F2), drawn by SectionDelegate with its count
            head = section(self.tree, g.name, len(g.items), columns=4, column=1)
            head.setData(0, GROUP_ROLE, g.key)
            head.setData(0, CLOSED_ROLE, g.closed)
            if g.kind:                                  # by object: the icon of the kind, as in the tree
                head.setIcon(0, icons.icon(g.kind))
            else:                                       # the worst mark inside, the window's symbol (R138)
                head.setIcon(0, symbols.icon(symbols.LEVEL[g.level]))
                head.setData(0, SYMBOL_ROLE, symbols.LEVEL[g.level])
                head.setToolTip(0, level_names()[g.level])
            if self.view in ("object", "area"):         # the counts by level, beside the name, with the symbols
                n = checks.counts([source[i] for i in g.items])
                levels = [lv for lv in checks.LEVELS if n[lv]]
                head.setData(2, COUNTS_ROLE, [(symbols.LEVEL[lv], n[lv]) for lv in levels])
                head.setToolTip(2, "\n".join(f"{level_names()[lv]}: {n[lv]}" for lv in levels))
            self.groups[g.key] = head
            for n in g.items:
                it = source[n]
                row = QTreeWidgetItem(head, ["", it.text, it.source, ""])
                row.setIcon(0, symbols.icon(symbols.LEVEL[it.level]))       # the window's symbol (R138)
                row.setData(0, SYMBOL_ROLE, symbols.LEVEL[it.level])
                row.setForeground(2, muted)                 # the source, quiet (F2)
                row.setToolTip(0, level_names()[it.level])
                row.setToolTip(1, it.text)
                row.setToolTip(2, it.source)
                row.setData(0, Qt.ItemDataRole.UserRole, it.target)
                row.setData(1, Qt.ItemDataRole.UserRole, n)
                if it.detail:                           # the detail, a row under the item that the arrow opens
                    detail = QTreeWidgetItem(row, [it.detail])
                    detail.setData(0, DETAIL_ROLE, True)
                    detail.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    detail.setFirstColumnSpanned(True)
                self._buttons(row, it, n)
                self.rows[n] = row
        self.tree.blockSignals(False)
        # opened while the page is hidden, the tree wraps every row in a width of nothing: a second at each
        # start (measured on 22/10/2026); on screen it takes a few milliseconds
        if self.isVisible():
            self._expand()
        else:
            self.expand_pending = True

    @staticmethod
    def place_of(it: checks.Item) -> str:
        """What the eye of an item shows (R127): "object" (the views, framed), "phase" (its page), "site", or ""."""
        t = tuple(it.target)
        if len(t) >= 2 and t[0] in checks.OBJECTS:
            return "object"
        if len(t) >= 2 and t[0] == "phase":
            return "phase"
        return "site" if t[:1] == ("site",) else ""

    def _eye_tip(self, it: checks.Item) -> str:
        place = self.place_of(it)
        if place == "object":
            return _("Show where it is: the object framed in the plan and in the 3D view, the rest dimmed")
        if place == "phase":
            from .. import phases
            title = next((ph.title for ph in phases.phases() if ph.id == it.target[1]), it.target[1])
            return _("Go to the {phase} phase, where it is decided").format(phase=title)
        return _("Show the site in the views")

    def _buttons(self, row: QTreeWidgetItem, it: checks.Item, n: int) -> None:
        """«Fix…» and the eye on the row, only where they serve (study 17, F.5): the eye wherever the problem has a
        place, the views or a phase (R127)."""
        placed = bool(self.place_of(it))
        if not it.fix and not placed:
            return
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, CARD_INSET + 6, 0)    # inside the item's card, off its edge
        lay.setSpacing(2)
        lay.addStretch(1)               # against the right edge: every eye in one column, with or without «Fix…»
        if it.fix:
            b = QToolButton()
            b.setObjectName("rowfix")
            b.setText(_("Fix…"))
            b.setAutoRaise(True)
            b.setToolTip(_("{fix}: shown first, then you keep it or take it back").format(fix=it.fix_label))
            b.clicked.connect(lambda _c=False, n=n: self._fix_row(n))
            lay.addWidget(b)
        if placed:
            e = QToolButton()
            e.setObjectName("roweye")
            e.setIcon(icons.icon("eye"))
            e.setAutoRaise(True)
            e.setToolTip(self._eye_tip(it))
            e.clicked.connect(lambda _c=False, n=n: self._eye(n))
            lay.addWidget(e)
        self.tree.setItemWidget(row, 3, box)

    def row_buttons(self, n: int) -> dict:
        """The buttons on the row of item `n`, by name ("fix", "eye"); for the tests and the keyboard."""
        row = self.rows.get(n)
        box = self.tree.itemWidget(row, 3) if row is not None else None
        if box is None:
            return {}
        return {b.objectName()[3:]: b for b in box.findChildren(QToolButton)}

    def _expand(self) -> None:
        self.tree.fit_source()
        for head in self.groups.values():
            head.setExpanded(not head.data(0, CLOSED_ROLE))
        for n, row in self.rows.items():
            if row.childCount() and self._memory(n) in self.opened:
                row.setExpanded(True)

    def _memory(self, n: int) -> tuple:
        it = self.all[n]
        return (tuple(it.target), it.text)

    def _remember(self, item: QTreeWidgetItem, opened: bool) -> None:
        """An item's detail opened or closed by the designer stays so through the next refresh."""
        n = item.data(1, Qt.ItemDataRole.UserRole)
        if isinstance(n, int) and 0 <= n < len(self.all):
            (self.opened.add if opened else self.opened.discard)(self._memory(n))

    # ----- filters

    def _hidden(self, n: int) -> bool:
        it = self.all[n]
        if self.levels and it.level not in self.levels:
            return True
        if self.phase_only and not checks.shown_in_phase(it, self.phase):
            return True
        return self.subset is not None and n not in self.subset

    def set_phase(self, pid: str) -> None:
        """The phase the window shows (its id in phases.py): what «This phase» keeps."""
        self.phase = pid
        if self.phase_only:
            self._apply()

    def _level_toggled(self, level: str, on: bool) -> None:
        """A count pressed: its level kept with the others pressed; none pressed, every level (R130)."""
        (self.levels.add if on else self.levels.discard)(level)
        self._apply()
        head = self.groups.get(("level", level)) if on else None
        if head is not None and not head.isHidden():
            head.setExpanded(True)
            self.tree.scrollToItem(head, QAbstractItemView.ScrollHint.PositionAtTop)

    def set_levels(self, levels) -> None:
        """The levels the counts keep, pressed as they are."""
        self.levels = set(levels) & set(checks.LEVELS)
        for lv, b in self.counts.items():
            b.blockSignals(True)
            b.setChecked(lv in self.levels)
            b.blockSignals(False)
        self._apply()

    def _phase_toggled(self, on: bool) -> None:
        self.phase_only = on
        self._apply()

    def _object_toggled(self, on: bool) -> None:
        if not on:
            if self.subset_key is not None:
                self.show_subset(None)
            return
        if self.subset_key is not None:                 # set from the tree's mark: already on
            return
        if self.related and (self.related[0] in checks.OBJECTS or self.related[0] == "site"):
            self.show_subset(tuple(self.related), self.names.get(tuple(self.related), self.related[1]))
        else:
            self.object_button.blockSignals(True)
            self.object_button.setChecked(False)
            self.object_button.blockSignals(False)
            self.summary.setText(_("Select an object in the views or in the tree first."))

    def _subset_of(self, key: tuple) -> None:
        mark = checks.tree_marks(self.items, checks.LEVELS).get(tuple(key))
        self.subset = set(mark.items) if mark is not None else set()

    def take_first(self) -> None:
        """The first check shown, in hand and in view: where a mark of the tree leads (Daniel, 24/10/2026)."""
        stack = [self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount() - 1, -1, -1)]
        while stack:
            it = stack.pop()
            if it is None or it.isHidden():
                continue
            if it.data(1, Qt.ItemDataRole.UserRole) is not None and it.parent() is not None:
                it.parent().setExpanded(True)
                self.tree.setCurrentItem(it)
                self.tree.scrollToItem(it)
                return
            stack.extend(it.child(i) for i in range(it.childCount() - 1, -1, -1))

    def show_subset(self, key: tuple | None, name: str = "") -> None:
        """The items of one object alone (`key` as checks.tree_marks has it: ("subfield", id), ("group", "building"),
        ("site", "")), every level; None, all again."""
        self.subset_key = tuple(key) if key is not None else None
        # the name the view by object uses, when it has one (the tree's text carries the modules' count)
        self.subset_name = self.names.get(self.subset_key, name) if key is not None else ""
        name = self.subset_name
        if key is None:
            self.subset = None
        else:
            self._subset_of(key)
        self.object_button.blockSignals(True)
        self.object_button.setChecked(self.subset is not None)
        self.object_button.blockSignals(False)
        self.object_button.setToolTip(_("Only the checks of {name}; a click shows every object's again").format(name=name)
                                      if self.subset is not None else
                                      _("Only the checks of the object selected in the views or in the tree"))
        self._apply()

    def _apply(self) -> None:
        for n, row in self.rows.items():
            row.setHidden(self._hidden(n))
        for head in self.groups.values():
            head.setHidden(all(head.child(r).isHidden() for r in range(head.childCount())))
        self._summary()
        self._keep_current_shown()

    def _summary(self) -> None:
        """How many of each level, each count a link to its section; what the filters keep."""
        n = checks.counts(self.items)
        words = level_names()
        for lv, b in getattr(self, "counts", {}).items():
            b.setText(str(n[lv]))
            b.setEnabled(bool(n[lv]) or b.isChecked())      # a pressed one can always be let go
            b.setToolTip(_("{n} {level}: a click shows every level again").format(n=n[lv], level=words[lv])
                         if b.isChecked() else
                         _("{n} {level}: a click shows only these (the others pressed stay)").format(
                             n=n[lv], level=words[lv]))
            b.updateGeometry()
        text = ""
        if self.phase_only:
            text += " " + _("Only this phase.")
        if self.subset is not None:
            text += " " + _("Only the checks of {name}: {n}.").format(name=self.subset_name, n=len(self.subset))
        self.summary.setText(text.strip())

    def go_to(self, level: str) -> None:
        """A count clicked, in the head or in the status bar: the section of that level, open, with its first
        item in hand (the views are not moved)."""
        if level not in checks.LEVELS:
            return
        if self.levels and level not in self.levels:
            self.set_levels(())                     # a level the counts were hiding: every level again
        if self.view != "level":
            self.set_view("level")
        head = self.groups.get(("level", level))
        if head is None:
            return
        head.setExpanded(True)
        self.tree.scrollToItem(head, QAbstractItemView.ScrollHint.PositionAtTop)
        first = next((head.child(r) for r in range(head.childCount()) if not head.child(r).isHidden()), None)
        if first is not None:
            self.tree.blockSignals(True)
            self.tree.setCurrentItem(first)
            self.tree.blockSignals(False)

    def _keep_current_shown(self) -> None:
        """The item in hand stays one the list shows: a filter that hid it left «Fix» offering the fix of an item
        nobody could see (R13). The first item shown takes its place, or none; the views are not moved."""
        row = self.tree.currentItem()
        if row is not None and (row.isHidden() or (row.parent() is not None and row.parent().isHidden())):
            first = next((head.child(r) for head in (self.tree.topLevelItem(i)
                                                     for i in range(self.tree.topLevelItemCount()))
                          if not head.isHidden() for r in range(head.childCount()) if not head.child(r).isHidden()),
                         None)
            self.tree.blockSignals(True)
            self.tree.setCurrentItem(first)
            self.tree.blockSignals(False)

    def _restore(self, n: int | None) -> None:
        """The item that was in hand, in hand again in the new rows (the views are not moved)."""
        row = self.rows.get(n) if n is not None else None
        if row is not None and not row.isHidden():
            self.tree.blockSignals(True)
            self.tree.setCurrentItem(row)
            self.tree.blockSignals(False)
        self._keep_current_shown()

    # ----- the views and the list, both ways

    def show_related(self, kind: str, oid: str) -> None:
        """The items about the object selected in the views stand out, and the list goes to the first (Revit's
        «Show Related Warnings»); the views are not moved by it. With «This object» on, the list follows."""
        self.related = (kind, oid)
        if self.subset_key is not None and self.subset_key != (kind, oid) and self.subset_key[0] != "group":
            self.subset_key = (kind, oid)
            self.subset_name = self.names.get((kind, oid), oid)
            self._subset_of(self.subset_key)
            self.object_button.setToolTip(_("Only the checks of {name}; a click shows every object's again").format(
                name=self.subset_name))
            self._apply()
        self._mark_related()

    def _mark_related(self) -> None:
        kind, oid = self.related
        about = set(checks.about(self.items, kind, oid))
        first = None
        for n, row in self.rows.items():
            mine = n in about
            font = row.font(1)
            font.setWeight(QFont.Weight.DemiBold if mine else QFont.Weight.Normal)     # one weight that stands out
            row.setFont(1, font)
            if mine and first is None and not row.isHidden():
                first = row
        current = self.tree.currentItem()
        if current is not None and current.data(1, Qt.ItemDataRole.UserRole) in about:
            return                                  # the item in hand is about it already: the list stays
        if first is not None:
            self.tree.blockSignals(True)
            self.tree.setCurrentItem(first)
            self.tree.blockSignals(False)
            self.tree.scrollToItem(first)

    def title(self, base: str) -> str:
        n = checks.counts(self.items)
        bad = n["fail"] + n["warn"]
        return f"{base} ({bad})" if bad else base

    def selected_index(self) -> int | None:
        row = self.tree.currentItem()
        n = row.data(1, Qt.ItemDataRole.UserRole) if row is not None else None
        return n if isinstance(n, int) and 0 <= n < len(self.all) else None

    def selected(self) -> checks.Item | None:
        n = self.selected_index()
        return self.all[n] if n is not None else None

    def _ask(self, n: int) -> None:
        if isinstance(n, int) and 0 <= n < len(self.all):
            self.ask.emit(self.all[n])

    def apply_fix(self) -> bool:
        """The fix of the row the keyboard is on asked for (Ctrl+.); False when it has none, and the head says
        so."""
        it = self.selected()
        if it is not None and it.fix:
            self.fix.emit(it)
            return True
        self.summary.setText(_("This check has no fix: its detail says what to do.") if it is not None else
                             _("No check under the keyboard: go to one with the arrows first."))
        return False

    def _fix_row(self, n: int) -> None:
        """«Fix…» on a row: its fix asked for, shown before it is kept (R126)."""
        row = self.rows.get(n)
        if row is not None:
            self.tree.blockSignals(True)
            self.tree.setCurrentItem(row)
            self.tree.blockSignals(False)
        it = self.all[n]
        if it.fix:
            self.fix.emit(it)

    def _eye(self, n) -> None:
        """The eye on a row, Enter: where the problem is, shown (R127)."""
        if not isinstance(n, int) or not 0 <= n < len(self.all):
            return
        row = self.rows.get(n)
        if row is not None:
            self.tree.blockSignals(True)
            self.tree.setCurrentItem(row)
            self.tree.blockSignals(False)
        self.focusRequested.emit(tuple(self.all[n].target))

    def _menu(self, pos) -> None:
        """The row's menu: where it is, its fix, Meridio, its text."""
        row = self.tree._row_of(pos)
        n = row.data(1, Qt.ItemDataRole.UserRole) if row is not None else None
        if not isinstance(n, int) or not 0 <= n < len(self.all):
            return
        it = self.all[n]
        menu = QMenu(self.tree)
        if self.place_of(it):
            menu.addAction(icons.icon("eye"), _("Show where it is"), lambda: self._eye(n))
        if it.fix:
            menu.addAction(_("Fix…"), lambda: self._fix_row(n)).setToolTip(it.fix_label)
        if self.ask_on:
            from ..assistant import NAME
            menu.addAction(_("Ask {name}").format(name=NAME), lambda: self._ask(n))
        menu.addSeparator()
        menu.addAction(_("Copy the text"), lambda: QGuiApplication.clipboard().setText(
            it.text + (chr(10) + it.detail if it.detail else "")))
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    # ----- a fix shown before it is kept (R126)

    def show_preview(self, label: str, applied: bool) -> None:
        """The fix asked for, said: `applied`, made as a preview with the views on it (Keep or Take back); else
        waiting for Apply (Apply or Cancel)."""
        if applied:
            self.preview_text.setText(_("Preview of the fix «{fix}»: the views show the result. Keep it?").format(
                fix=label))
            self.preview_keep.setText(_("Keep"))
            self.preview_drop.setText(_("Take back"))
        else:
            self.preview_text.setText(_("The fix «{fix}»: apply it?").format(fix=label))
            self.preview_keep.setText(_("Apply"))
            self.preview_drop.setText(_("Cancel"))
        self.preview.show()
        self.preview_keep.setFocus(Qt.FocusReason.OtherFocusReason)

    def end_preview(self) -> None:
        self.preview.hide()

    def previewing(self) -> bool:
        return not self.preview.isHidden()

    def _answer(self, keep: bool) -> None:
        self.previewAnswered.emit(keep)

    def _copy(self) -> None:
        text = self.notes_text()
        if text.strip():
            QGuiApplication.clipboard().setText(text)
            self.summary.setText(_("The notes for the report are in the clipboard: paste them into the document."))
