"""The checks of the project in one list (study 17, F; design document, 3.8): by level as the default (TO FIX,
TO CHECK, TO KNOW, PASSED closed), by object or by area from the menu in the head, and «ready for delivery»
for the Report phase (what is to fix and to check, the values still at their default, the estimates in use);
the sections are the headers of the project's tree (SectionDelegate). Each row is one short sentence with its
mark and its source; the arrow opens the detail (why, and what to do) as a wrapped row under it; «Fix» and the
eye sit on the row where they serve. A click shows the object an item is about in the views, the rest dimmed,
and the arrows go through the list with the views following; a double click leads to the object or the page;
the items of the object selected in the views stand out (study 12, C4). The filters are «This phase» and «This
object» (the marks of the tree set the latter, R30); the counts in the head and in the status bar lead to the
section (C9). «Fix» below applies the fix of the item in hand (Ctrl+.); the notes of the rules that apply can be
copied for the technical report."""

from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QActionGroup, QBrush, QColor, QFont, QFontMetrics, QGuiApplication, QPainter,
                           QPainterPath, QPalette, QPen)
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QMenu, QPushButton, QSizePolicy,
                               QStyle, QStyleOptionViewItem, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                               QWidget)

from .. import checks, theme_colors
from ..i18n import _
from . import icons
from .sections import SectionDelegate, section
from .theme import symbol_font

MARKS = {"fail": "✘", "warn": "⚠", "info": "ℹ", "ok": "✔"}
# the status colours of the charts' palette (critical, warning, good), on the mark only: the mark and the words
# carry the meaning, the colour helps; what is only worth knowing keeps the colour of the text
COLOURS = {"fail": "#d03b3b", "warn": "#fab219", "ok": "#0ca30c"}
DETAIL_ROLE = Qt.ItemDataRole.UserRole + 9      # on the row under an item: its detail, drawn wrapped
GROUP_ROLE = Qt.ItemDataRole.UserRole + 10      # on a header: the key of its group (checks.Group.key)
CLOSED_ROLE = Qt.ItemDataRole.UserRole + 11     # on a header: shown closed by default
PAD = 6                                         # around the detail's text (Space.S)
DETAIL_BOTTOM = 10                              # under the detail, before the line to the next item

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
        return QRect(left, option.rect.top(), max(80, right - left), option.rect.height())

    @staticmethod
    def detail_font(font):
        from .design import Type
        from .design import font as scaled
        return scaled(Type.SMALL, Type.REGULAR, font)

    def paint(self, painter, option, index) -> None:
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

    def sizeHint(self, option, index) -> QSize:
        if index.data(DETAIL_ROLE) is None:
            return super().sizeHint(option, index)
        r = self._detail_rect(index, option)
        rect = QFontMetrics(self.detail_font(option.font)).boundingRect(
            QRect(0, 0, r.width(), 0), Qt.TextFlag.TextWordWrap, index.data(Qt.ItemDataRole.DisplayRole) or "")
        return QSize(rect.width(), rect.height() + DETAIL_BOTTOM)


CARD_INSET = 8          # the cards of the items from the panel's sides (F2)
CARD_RADIUS = 6


class ChecksTree(QTreeWidget):
    """A tree whose rows are laid out again when its width changes: the details wrap to the width. The items of
    a section stand in one card (F2, the target of 24/10/2026): each row draws its slice of it before its
    cells, the first with the top corners, the last with the bottom ones, a soft line between two items, the
    detail on the tonal veil; the selection a rounded ground inside the card. `colours` are the theme's."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("checks-tree")
        self.colours = {"card": "#ffffff", "line": "#d9d5cc", "sink": "#ebeae7", "select": "#f5e3c8",
                        "hover": "#1e1c190f"}
        # the rows laid out again once the width rests: at every step of a panel's edge dragged it measured every
        # row's wrapped detail (4 500 times in 40 steps, R120)
        self.relayout = QTimer(self)
        self.relayout.setSingleShot(True)
        self.relayout.setInterval(90)
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
        whole text in the tooltip). The column of what is checked takes the rest."""
        want = self.sizeHintForColumn(2)
        width = min(want, int(self.viewport().width() * self.SOURCE_SHARE))
        if self.header().sectionSize(2) != width:
            self.header().resizeSection(2, max(0, width))

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

    def mousePressEvent(self, event) -> None:
        """The arrow opens and closes the detail and does nothing else: the item in hand, the list and the views stay
        where they are (Daniel, 24/10/2026: opening a row moved the list)."""
        item = self._arrow_of(event.position().toPoint()) if event.button() == Qt.MouseButton.LeftButton else None
        if item is not None:
            item.setExpanded(not item.isExpanded())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        item = self._arrow_of(event.position().toPoint()) if event.button() == Qt.MouseButton.LeftButton else None
        if item is not None:
            item.setExpanded(not item.isExpanded())
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

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
        # the item in hand and the one under the pointer: a pill inside the card, never the card's whole width
        hovered = option.state & QStyle.StateFlag.State_MouseOver
        if not detail and (self.currentItem() is item or hovered):
            pill = QPainterPath()
            pill.addRoundedRect(QRectF(r.left() + 4, r.top() + 2, r.width() - 8, r.height() - 4), 4, 4)
            painter.fillPath(pill, QColor(c["select"] if self.currentItem() is item else c["hover"]))
        painter.setPen(QPen(QColor(c["line"]), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(shape)
        if not last and not (opened and not detail):         # the line between two items
            y = r.top() + r.height() - 1
            painter.drawLine(QRectF(r.left(), y, r.width(), 0).topLeft(), QRectF(r.left(), y, r.width(), 0).topRight())
        painter.restore()


class ChecksPage(QWidget):
    navigate = Signal(tuple)          # an item's target: ("subfield", id), ("building", id), ("phase", id), ("site",)
    fix = Signal(object)              # the item whose fix the designer asked for
    ask = Signal(object)              # the item the designer asks Meridio about (task 14)
    focusRequested = Signal(tuple)    # the item in hand changed: its target, to show in the views
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
        # the counts as pills, each with its mark drawn and leading to its section (the target of 24/10/2026, F2)
        self.counts: dict = {}
        from .marks import icon as mark_icon
        for lv in checks.LEVELS:
            b = QToolButton()
            b.setObjectName("count")
            b.setAutoRaise(True)
            b.setIcon(mark_icon(lv))
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            b.setToolTip(level_names()[lv])
            b.clicked.connect(lambda _c=False, lv=lv: self.go_to(lv))
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
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setItemDelegate(ChecksDelegate(self.tree, column=1))      # the sections (T2), the details
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)          # ChecksTree.fit_source
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(False)
        self.tree.itemDoubleClicked.connect(self._open)
        self.tree.currentItemChanged.connect(lambda *_a: self._current(focus=True))
        self.tree.itemExpanded.connect(lambda it: self._remember(it, True))
        self.tree.itemCollapsed.connect(lambda it: self._remember(it, False))
        box.addWidget(self.tree, 1)
        row = QHBoxLayout()
        self.fix_button = QPushButton(_("Fix"))         # the fix of the item in hand, for the keyboard (Ctrl+.)
        self.fix_button.setEnabled(False)
        self.fix_button.clicked.connect(self._fix)
        row.addWidget(self.fix_button)
        from ..assistant import NAME
        self.ask_button = QPushButton(_("Ask {name}").format(name=NAME))      # beside «Fix» (study 14, 7.1)
        self.ask_button.setToolTip(_("Ask {name} about the item in hand: why it matters and what to do").format(
            name=NAME))
        self.ask_button.setEnabled(False)
        self.ask_button.clicked.connect(self._ask)
        row.addWidget(self.ask_button)
        self.fix_label = QLabel()
        self.fix_label.setWordWrap(True)
        row.addWidget(self.fix_label, 1)
        self.copy_button = QPushButton(_("Copy the notes for the report"))
        self.copy_button.setToolTip(_("The paragraphs of the rules that apply, with their sources, to paste into the "
                                      "technical report"))
        self.copy_button.clicked.connect(self._copy)
        row.addWidget(self.copy_button)
        box.addLayout(row)
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
        """The theme's colours for the cards of the items (F2)."""
        # the cards of the items stand apart from the panel in both themes: in the dark one the card is the panel,
        # so a veil of white lifts them, and their line is the full one (Daniel, 24/10/2026: «non si intuiscono i
        # confini delle sottoschede»)
        dark = theme_colors.luminance(t["panel"]) < 0.2
        card = theme_colors.mix(t["panel"], "#ffffff", 0.045) if dark else t["card"]
        hover = QColor(t["text"])
        hover.setAlpha(18)
        self.tree.colours = {"card": card, "line": t["line"], "sink": t["field"], "select": t["select_bg"],
                             "hover": hover.name(QColor.NameFormat.HexArgb)}
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
        font = symbol_font(self.tree.font())
        muted = QBrush(self.palette().color(QPalette.ColorGroup.Active, QPalette.ColorRole.PlaceholderText))
        for g in checks.grouped(source, self.view, self.names):
            # a section's header (study 17, T2 and F2), drawn by SectionDelegate with its count
            head = section(self.tree, g.name, len(g.items), columns=4, column=1)
            head.setData(0, GROUP_ROLE, g.key)
            head.setData(0, CLOSED_ROLE, g.closed)
            if g.kind:                                  # by object: the icon of the kind, as in the tree
                head.setIcon(0, icons.icon(g.kind))
            else:                                       # the worst mark inside
                head.setText(0, MARKS[g.level])
                head.setFont(0, font)
                head.setToolTip(0, level_names()[g.level])
                if g.level in COLOURS:
                    head.setForeground(0, QBrush(QColor(COLOURS[g.level])))
            if self.view in ("object", "area"):         # the counts by level, beside the name
                n = checks.counts([source[i] for i in g.items])
                head.setText(2, "  ".join(f"{MARKS[lv]} {n[lv]}" for lv in checks.LEVELS if n[lv]))
                head.setFont(2, font)
                head.setForeground(2, muted)
            self.groups[g.key] = head
            for n in g.items:
                it = source[n]
                row = QTreeWidgetItem(head, [MARKS[it.level], it.text, it.source, ""])
                row.setFont(0, font)
                row.setForeground(2, muted)                 # the source, quiet (F2)
                if it.level in COLOURS:
                    row.setForeground(0, QBrush(QColor(COLOURS[it.level])))
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

    def _buttons(self, row: QTreeWidgetItem, it: checks.Item, n: int) -> None:
        """«Fix» and the eye on the row, only where they serve (study 17, F.5)."""
        on_object = len(it.target) >= 2 and it.target[0] in checks.OBJECTS
        if not it.fix and not on_object:
            return
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, CARD_INSET + 6, 0)    # inside the item's card, off its edge
        lay.setSpacing(2)
        if it.fix:
            b = QToolButton()
            b.setObjectName("rowfix")
            b.setText(_("Fix"))
            b.setAutoRaise(True)
            b.setToolTip(it.fix_label)
            b.clicked.connect(lambda _c=False, n=n: self._fix_row(n))
            lay.addWidget(b)
        if on_object:
            e = QToolButton()
            e.setObjectName("roweye")
            e.setIcon(icons.icon("eye"))
            e.setAutoRaise(True)
            e.setToolTip(_("Show the object in the views, the rest dimmed"))
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
        if self.phase_only and not checks.shown_in_phase(it, self.phase):
            return True
        return self.subset is not None and n not in self.subset

    def set_phase(self, pid: str) -> None:
        """The phase the window shows (its id in phases.py): what «This phase» keeps."""
        self.phase = pid
        if self.phase_only:
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
            b.setEnabled(bool(n[lv]))
            b.setToolTip(f"{n[lv]} {words[lv]}")
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
            self._current()

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
            if first is None:
                self.tree.clearSelection()
            self.tree.blockSignals(False)
        self._current()

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
            self._current()

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

    def _current(self, focus: bool = False) -> None:
        it = self.selected()
        if focus and it is not None:
            self.focusRequested.emit(tuple(it.target))
        can = it is not None and bool(it.fix)
        self.fix_button.setEnabled(can)
        self.fix_label.setText(it.fix_label if can else "")
        self.ask_button.setEnabled(it is not None)

    def _fix(self) -> None:
        self.apply_fix()

    def _ask(self) -> None:
        it = self.selected()
        if it is not None:
            self.ask.emit(it)

    def apply_fix(self) -> bool:
        """The fix of the item in hand asked for (the button below, Ctrl+.); False when it has none, and the
        head says so."""
        it = self.selected()
        if it is not None and it.fix:
            self.fix.emit(it)
            return True
        self.summary.setText(_("The item in hand has no fix: its detail says what to do.") if it is not None else
                             _("No item in hand: choose one in the list first."))
        return False

    def _fix_row(self, n: int) -> None:
        """«Fix» on a row: the item in hand (the views follow), and its fix asked for."""
        row = self.rows.get(n)
        if row is not None and self.tree.currentItem() is not row:
            self.tree.setCurrentItem(row)
        it = self.all[n]
        if it.fix:
            self.fix.emit(it)

    def _eye(self, n: int) -> None:
        """The eye on a row: its object shown in the views, the rest dimmed (what a click on the row does, said)."""
        row = self.rows.get(n)
        if row is not None:
            self.tree.blockSignals(True)
            self.tree.setCurrentItem(row)
            self.tree.blockSignals(False)
            self._current()
        self.focusRequested.emit(tuple(self.all[n].target))

    def _copy(self) -> None:
        text = self.notes_text()
        if text.strip():
            QGuiApplication.clipboard().setText(text)
            self.summary.setText(_("The notes for the report are in the clipboard: paste them into the document."))

    def _open(self, item: QTreeWidgetItem, _column: int) -> None:
        target = item.data(0, Qt.ItemDataRole.UserRole)
        if target:
            self.navigate.emit(tuple(target))
