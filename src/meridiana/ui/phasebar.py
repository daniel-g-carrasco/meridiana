"""The row of the phases and the bar of each phase (task 17b; study 17, B4, Daniel's choice of 23/10/2026; design
document 3.3 and 5.3), built from phases.py. The row: «1 Modello», «2 Impianto»..., each number in a small disc
inside its tab (the accent's for the phase open), «Variant» in its right corner. Under the row, across the window,
a card with the bar of the phase: the tab of the phase open and the card are one shape (the target of 24/10/2026,
docs/studio/19-grafica), meeting the card with inverse rounded corners (R84, as GNOME's tabs); at a change of phase
the tab slides to the new one (R83, as Office's ribbon), the page and the tools change at once. The bar: one QToolBar per phase in a QStackedWidget, the groups side by side with their
title under them (small capitals, muted) and a thin line between; the words under the icons (68 px: icons of 24,
the word, the group's title) or the icons alone (44 px: icons of 22, the group's title stays, it is what
explains). The bar is there in every phase, even with two groups: a row that comes and goes would move the views
by 70 px at each change.

The buttons carry the window's QActions (one command, one action: the menus, the keys and the tooltips are the
same) with a short word of their own under the icon; the one button full of accent of the phase (Lay the modules,
Compute) has its icon in the colour of the text on the accent.

`Phases` is the central widget of the window (the pages) and speaks as the QTabWidget it replaces (currentIndex,
setCurrentIndex, currentChanged, tabBar, tabText, count, widget, currentWidget, setCornerWidget), so that the
window and its tests go on as before; its `header` (the row and the card of the bar) stands above the panels, in
the window's menu widget."""

from __future__ import annotations

import math

from PySide6.QtCore import QEasingCurve, QEvent, QPointF, QRectF, QSize, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QFontMetricsF, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QSizePolicy, QStackedWidget, QTabBar, QToolBar,
                               QToolButton, QVBoxLayout, QWidget)

from .. import phases, theme_colors
from ..i18n import _
from . import icons
from .cards import EDGE, RADIUS, default_tokens
from .design import Button, Icon, Motion, Radius, Size, Space, Text, set_text, text_font
from .waiting import STALE_MARK

TALL = 72                   # the bar with the words under the icons (design 5.3): what the bar must not exceed;
                            # 68 until R179 (Daniel 26/10/2026: «le descrizioni dei singoli strumenti vengono
                            # tagliati in basso»): the buttons were 4 px short of the line the word needs
LOW = 44                    # the icons alone
LOW_WINDOW = 900            # logical pixels: a lower window gets the icons alone by itself (the laptop, a column)
ICON_TALL, ICON_LOW = Icon.TILE, Icon.BAR
# the word under the icon is Text.SECONDARY, the title of the group Text.GROUP (R159): read when used, the size of
# the text can change with the window open (R133)
GROUP_GAP = Space.XS                                    # between the commands and their group's name (R159)
TAB_HEIGHT = Size.CONTROL + Space.XS   # a compact control with equal breathing room above and below
HOVER_INSET = Space.XXS     # the ground of a phase under the pointer, in from its tab's sides (R160)
BADGE = Button.SMALL[0]      # the disc of a phase's number
TAB_PAD = (Space.L, Space.L)  # equal space before the disc and after the name
CARD_PAD = (Space.L - 2, Space.S, Space.L - 2, Space.S - 1)   # inside the card of the bar


def _colours(t: dict | None = None) -> dict:
    t = t or default_tokens()
    return {"text": t["text"], "text2": t["text2"], "muted": t["muted"], "disc": t["line_soft"], "accent": t["accent"],
            "accent_fg": t["accent_fg"], "card": t["panel"], "edge": t["card_line"],
            "hover": theme_colors.qt_hex(t["hover"])}


class PhaseTabBar(QTabBar):
    """The row of the phases: the names are labels (the numbers are not keys, C8), each number in a disc inside
    its tab, the accent's for the phase open. The tab of the phase open is drawn by the header, as one shape with
    the card of the bar under it; the bar draws only the discs and the names."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("phases")
        self.setExpanding(False)
        self.setDrawBase(False)
        self.setUsesScrollButtons(False)
        self.setElideMode(Qt.TextElideMode.ElideRight)     # a narrow window (a column of niri) shortens the names
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)         # the keyboard stays where it was; Ctrl+Tab changes phase
        self.setMouseTracking(True)
        self.colours = _colours()
        self.hovered = -1
        self.file_open = False              # the File page over the window: no phase is the one open (R99)
        self.picture: QPixmap | None = None  # the row as last drawn, and what it was drawn for (R97, R120)
        self.drawn_for = None

    @property
    def accent(self) -> QColor:
        return QColor(self.colours["accent"])

    def name_font(self, bold: bool) -> QFont:
        """A tab's name: a control's word (13 px, R121: «i testi nelle linguette sono troppo grandi»), the phase in
        hand semibold as a button's."""
        return text_font(Text.STRONG if bold else Text.CONTROL, self.font())

    def number_font(self) -> QFont:
        return text_font(Text.LABEL, self.font())

    @staticmethod
    def parts(text: str) -> tuple[str, str]:
        number, _sp, name = text.partition(" ")
        return (number, name) if number.isdigit() else ("", text)

    def tabSizeHint(self, index: int) -> QSize:
        _number, name = self.parts(self.tabText(index))
        text = math.ceil(QFontMetricsF(self.name_font(True)).horizontalAdvance(name)) + 2
        return QSize(TAB_PAD[0] + BADGE + 8 + text + TAB_PAD[1], TAB_HEIGHT)

    def minimumTabSizeHint(self, index: int) -> QSize:
        return QSize(TAB_PAD[0] + BADGE + 8 + 24 + TAB_PAD[1], TAB_HEIGHT)

    def setTabVisible(self, index: int, visible: bool) -> None:
        super().setTabVisible(index, visible)
        # QTabBar updates its tabs but leaves the parent layout's size hint cached.
        # Revealing a phase must reclaim available width before any names are elided.
        self.updateGeometry()

    def hover_rect(self, index: int) -> QRectF:
        """The hover surface has the same inset on all four sides of its hit rectangle."""
        return QRectF(self.tabRect(index)).adjusted(HOVER_INSET, HOVER_INSET, -HOVER_INSET, -HOVER_INSET)

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)
        i = self.tabAt(event.position().toPoint())
        if i != self.hovered:
            self.hovered = i
            self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self.hovered = -1
        self.update()

    def paintEvent(self, event) -> None:
        """The row drawn again only when something in it changed: the tab of the phase open slides over it, and the
        row was drawn from scratch at every frame of the slide, 17 a change of phase (R97, R120, 25/10/2026)."""
        ratio = self.devicePixelRatioF()
        key = (self.size().toTuple(), ratio, self.currentIndex(), self.hovered, self.file_open,
               tuple(self.colours.items()),
               tuple((self.tabText(i), self.isTabVisible(i)) for i in range(self.count())), self.font().key())
        if self.picture is None or key != self.drawn_for:
            picture = QPixmap(round(self.width() * ratio), round(self.height() * ratio))
            picture.setDevicePixelRatio(ratio)
            picture.fill(Qt.GlobalColor.transparent)
            painter = QPainter(picture)
            self._draw(painter)
            painter.end()
            self.picture, self.drawn_for = picture, key
        QPainter(self).drawPixmap(0, 0, self.picture)

    def _draw(self, p: QPainter) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self.colours
        for i in range(self.count()):
            if not self.isTabVisible(i):
                continue
            r = self.tabRect(i)
            on = i == self.currentIndex() and not self.file_open
            number, name = self.parts(self.tabText(i))
            if i == self.hovered and not on:
                # under the pointer: the controls' layer on a control's shape, as «File» beside it (R160: the
                # phases changed only their name's colour)
                ground = self.hover_rect(i)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(c["hover"]))
                p.drawRoundedRect(ground, Radius.CONTROL, Radius.CONTROL)
            x = r.left() + TAB_PAD[0]
            if number:
                disc = QRectF(x, QRectF(r).center().y() - BADGE / 2, BADGE, BADGE)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(c["accent"] if on else c["disc"]))
                p.drawEllipse(disc)
                # The outline retains fractional font metrics: tightBoundingRect and drawText
                # round differently with small/large text at a fractional screen density.
                glyph = QPainterPath()
                glyph.addText(QPointF(), self.number_font(), number)
                glyph.translate(disc.center() - glyph.boundingRect().center())
                p.fillPath(glyph, QColor(c["accent_fg"] if on else c["muted"]))
                x += BADGE + 8
            font = self.name_font(on)
            p.setFont(font)
            p.setPen(QColor(c["text"] if on or i == self.hovered else c["text2"]))
            room = r.right() - TAB_PAD[1] + 1 - x
            text = QFontMetricsF(font).elidedText(name, Qt.TextElideMode.ElideRight, max(0.0, room + 2))
            p.drawText(QRectF(x, r.top(), max(0, room), r.height()),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)


class ToolButton(QToolButton):
    """A button of the bar: the window's action, with its own short word under the icon (the action's text stays
    whole in the menu and in the tooltip) and, for the primary one, its own icon colour."""

    def __init__(self, action, label: str, icon=None, parent=None):
        super().__init__(parent)
        self.label = label
        self.own_icon = icon
        self.own_tip = ""                                       # a tooltip of its own (the view bar's: word and key)
        self.setAutoRaise(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)            # the keyboard stays on the drawing
        self.setDefaultAction(action)
        if action.menu() is not None:
            self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._own()

    def _own(self) -> None:
        if self.label and self.text() != self.label:
            self.setText(self.label)
        if self.own_icon is not None:
            self.setIcon(self.own_icon)
        if self.own_tip and self.toolTip() != self.own_tip:
            self.setToolTip(self.own_tip)

    def actionEvent(self, event) -> None:
        super().actionEvent(event)                              # Qt put the action's text and icon back
        self._own()

    def set_own_icon(self, icon) -> None:
        self.own_icon = icon
        self._own()


class ToolGroup(QWidget):
    """A group of the bar: its buttons in a row and its title under them."""

    def __init__(self, group: phases.Group, tools: list, actions: dict, parent=None):
        super().__init__(parent)
        self.group = group
        self.buttons: dict = {}                                 # command id -> its button
        self.primary: ToolButton | None = None
        box = QVBoxLayout(self)
        box.setContentsMargins(4, 0, 4, 0)
        box.setSpacing(0)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(2)
        for tool in tools:
            if actions[tool.command].icon().isNull() and tool.icon:
                # a command that came without an icon takes the one its tool was designed with (R277: «On canopy»)
                actions[tool.command].setIcon(icons.icon(tool.icon))
            b = ToolButton(actions[tool.command], tool.label or _plain(actions[tool.command].text()))
            b.setProperty("tool", tool.command)
            b.setFont(text_font(Text.SECONDARY, b.font()))
            if tool.primary:
                b.setProperty("primary", True)
                self.primary = b
                self.primary_icon = tool.icon or tool.command
            row.addWidget(b)
            self.buttons[tool.command] = b
        box.addLayout(row)
        box.addSpacing(GROUP_GAP)
        self.title = QLabel(group.title)
        self.title.setObjectName("group-title")
        self.title.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.title.setFont(text_font(Text.GROUP, self.title.font()))
        box.addWidget(self.title)

    def set_mode(self, text: bool) -> int:
        """The buttons with the word under the icon or the icon alone, at the height that holds them (a font's
        line is taller than its size, so the button is measured, not guessed); the height of the group."""
        style = Qt.ToolButtonStyle.ToolButtonTextUnderIcon if text else Qt.ToolButtonStyle.ToolButtonIconOnly
        size = QSize(ICON_TALL, ICON_TALL) if text else QSize(ICON_LOW, ICON_LOW)
        height = 0
        for b in self.buttons.values():
            b.setToolButtonStyle(style)
            b.setIconSize(size)
            # what the button asks for, the word's whole line under the icon (R179: the 4 px added to the font's
            # line left out the gap the style puts between icon and word, and the large text was cut)
            b.setFixedHeight(max(ICON_TALL + QFontMetrics(b.font()).height() + 4, b.sizeHint().height()) if text
                             else ICON_LOW + 6)
            height = b.height() if b.height() > 1 else b.minimumHeight()
        title = QFontMetrics(self.title.font()).height()
        self.title.setFixedHeight(title)
        return height + GROUP_GAP + title

    def set_colours(self, t: dict) -> None:
        if self.primary is not None:
            self.primary.set_own_icon(icons.icon(self.primary_icon, colour=t["text"]))      # no accent (R158)


def _plain(text: str) -> str:
    from .. import shortcuts
    return shortcuts.plain(text).rstrip("…")


class PhaseBar(QToolBar):
    """The bar of one phase, from its groups; a tool whose command the window has no action for is left out (the
    planned ones, phases.Tool.planned), and comes in at its designed place once the window has the action (R277:
    «Su pensilina» with the canopy's task); a group with none of its tools is left out whole."""

    def __init__(self, phase: phases.Phase, actions: dict, parent=None):
        super().__init__(phase.title, parent)
        self.setObjectName(f"bar-{phase.id}")
        self.phase = phase
        self.setMovable(False)
        self.setFloatable(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.layout().setContentsMargins(4, 1, 4, 1)
        self.groups: list[ToolGroup] = []
        self.lines: list[QFrame] = []
        self.text = True
        for group in phase.groups:
            tools = [t for t in group.tools if t.command in actions]
            if not tools:
                continue
            if self.groups:
                line = QFrame()
                line.setObjectName("bar-line")
                line.setFixedWidth(1)
                self.addWidget(line)
                self.lines.append(line)
            w = ToolGroup(group, tools, actions)
            self.addWidget(w)
            self.groups.append(w)
        self.set_text(True)

    def add_trailing(self, widget: QWidget) -> None:
        """`widget` at the right end of the bar, after a line: what the phase shows of itself (the Plant's strip)."""
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.addWidget(spacer)
        line = QFrame()
        line.setObjectName("bar-line")
        line.setFixedWidth(1)
        self.addWidget(line)
        self.addWidget(widget)

    def set_text(self, on: bool) -> None:
        """The words under the icons, or the icons alone with the groups' titles. The height is the one the
        buttons and the titles need (the stack gives every phase the tallest, so the views never jump): the
        tests keep it within TALL and LOW."""
        self.text = on
        inside = max((g.set_mode(on) for g in self.groups), default=(TALL if on else LOW) - 3)
        self.setFixedHeight(inside + 3)                 # the toolbar's margins and the line under it
        self.updateGeometry()

    def set_colours(self, t: dict) -> None:
        for g in self.groups:
            g.set_colours(t)

    def buttons(self) -> dict:
        """command id -> its button, over the groups."""
        out: dict = {}
        for g in self.groups:
            out.update(g.buttons)
        return out

    def primary(self) -> ToolButton | None:
        return next((g.primary for g in self.groups if g.primary is not None), None)


class PhaseHeader(QWidget):
    """The row of the phases and, under it, the card with the bar of the phase open, across the window above the
    panels (the window puts it in its menu widget): EDGE pixels from the window's sides as the cards, the tab of
    the phase open and the card one shape, filled with the panels' colour, with their line. With
    the bar on the left side (or gone, Ctrl+0) the card goes and the tab stands alone."""

    def __init__(self, tab_bar: PhaseTabBar, corner_box: QHBoxLayout, bars: QStackedWidget, parent=None):
        super().__init__(parent)
        self.setObjectName("phase-header")
        self.tab_bar, self.bars = tab_bar, bars
        self.colours = _colours()
        self.dark = False
        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(0)
        # «File» at the left of the phases (the target's File page, R40), drawn as they are: no ground at rest,
        # the controls' layer under the pointer, the pressed one while its page is open (R104, R158, R160: «file
        # non c'entra proprio nulla»)
        self.file_button = QToolButton()
        self.file_button.setObjectName("file-chip")
        self.file_button.setText(_("File"))
        set_text(self.file_button, Text.STRONG)
        self.file_button.setCheckable(True)
        self.file_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.file_button.setIconSize(QSize(Icon.CONTROL - 1, Icon.CONTROL - 1))
        self.file_button.setFixedHeight(Button.PUSH[0])         # a push button's height (R121)
        self.file_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.file_button.setToolTip(_("New, open, save, import, export, catalogues, settings and help"))
        self.file_button.toggled.connect(lambda _on: self._file_icon())
        head.addWidget(self.file_button, 0, Qt.AlignmentFlag.AlignVCenter)
        head.addSpacing(Space.L)
        head.addWidget(tab_bar, 0, Qt.AlignmentFlag.AlignBottom)
        head.addStretch(1)
        head.addLayout(corner_box)
        self.card = QWidget()
        self.card.setObjectName("phase-card")
        inside = QVBoxLayout(self.card)
        inside.setContentsMargins(*CARD_PAD)
        inside.setSpacing(0)
        inside.addWidget(bars)
        box = QVBoxLayout(self)
        box.setContentsMargins(EDGE, 0, EDGE, 0)
        box.setSpacing(0)
        box.addLayout(head)
        box.addWidget(self.card)
        bars.installEventFilter(self)
        tab_bar.currentChanged.connect(lambda _i: self.update())
        # the tab sliding from where it was shown to its phase (R83): `hold` keeps it there, `play` moves it
        self.slide = QVariantAnimation(self)
        self.slide.setStartValue(0.0)
        self.slide.setEndValue(1.0)
        self.slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.slide.valueChanged.connect(lambda _v: self._slide_step())
        self.slide.finished.connect(self._landed)
        self.slide_from: QRectF | None = None
        self.shown_tab: QRectF | None = None        # the tab as it was last painted
        self.file_open = False              # the File page over the window (set_file_open)

    def eventFilter(self, obj, event) -> bool:
        if obj is self.bars and event.type() in (QEvent.Type.ShowToParent, QEvent.Type.HideToParent):
            self.card.setVisible(not self.bars.isHidden())
            self.update()
        return False

    def set_colours(self, t: dict) -> None:
        self.colours = _colours(t)
        self.dark = theme_colors.luminance(t["window"]) < 0.2
        self.file_icons = (icons.icon("folder-open", t["text"]), icons.icon("folder-open", t["text"]))   # R158
        self._file_icon()
        self.tab_bar.colours = self.colours
        self.tab_bar.update()
        self.update()

    def _file_icon(self) -> None:
        icons_ = getattr(self, "file_icons", None)
        if icons_ is not None:
            self.file_button.setIcon(icons_[1] if self.file_button.isChecked() else icons_[0])

    def set_file_open(self, on: bool) -> None:
        """The File page open (R99): no tab drawn as the phase open, the tabs all at rest; closed, the phase's back."""
        self.slide.stop()
        self.slide_from = None
        self.tab_bar.file_open = on
        self.file_open = on
        self.tab_bar.update()
        self.update()

    def hold(self) -> None:
        """The tab stays where it is shown until `play`: the phase changes under it, the window does what the
        change asks, then it slides."""
        from .motion import reduced
        self.slide.stop()
        held = self.shown_tab is not None and self.isVisible() and not reduced()
        self.slide_from = QRectF(self.shown_tab) if held else None
        self.update()

    def play(self, ms: int = Motion.NORMAL) -> None:
        """The tab from where it was held to its phase."""
        from .motion import reduced
        if self.slide_from is None or reduced() or self.slide_from == self.tab_target():
            self._landed()
            return
        self.slide.setDuration(ms)
        self.slide.start()

    def _landed(self) -> None:
        self.slide_from = None
        self.update()

    def _slide_step(self) -> None:
        """Only the band the tab moves in painted again: the tab where it was and where it is now, its inverse corners
        and the card's top edge under it. The whole header, the bar's buttons with it, at every step made the slide
        stutter on a 4K screen (R97, Windows, 25/10/2026)."""
        now, before = self.tab_now(), self.shown_tab
        if now is None or before is None:
            self.update()
            return
        band = now.united(before)
        bottom = (self.card.geometry().top() + RADIUS + 2) if self.card.isVisible() else band.bottom() + 2
        self.update(QRectF(band.left() - RADIUS - 2, band.top() - 2, band.width() + 2 * RADIUS + 4,
                           bottom - band.top() + 2).toAlignedRect())

    def tab_target(self) -> QRectF | None:
        """Where the tab of the phase open stands, in the header's pixels; none while the File page is open."""
        i = self.tab_bar.currentIndex()
        if i < 0 or not self.tab_bar.isVisible() or self.file_open:
            return None
        return QRectF(self.tab_bar.tabRect(i).translated(self.tab_bar.pos()))

    def tab_now(self) -> QRectF | None:
        """The tab as it is to be painted now: held, sliding or at its phase."""
        r = self.tab_target()
        if r is None or self.slide_from is None:
            return r
        if self.slide.state() != QVariantAnimation.State.Running:
            return QRectF(self.slide_from)
        t = float(self.slide.currentValue())
        a = self.slide_from
        return QRectF(a.left() + (r.left() - a.left()) * t, r.top(), a.width() + (r.width() - a.width()) * t,
                      r.height())

    def shape(self) -> QPainterPath:
        """The card and the tab of the phase open, as one path, in the header's pixels: the tab meets the card with
        two inverse corners of the cards' radius (R84), left out where the card's own corner is."""
        path = QPainterPath()
        card = QRectF(self.card.geometry()).adjusted(0.5, 0.5, -0.5, -0.5)
        joined = self.card.isVisible()
        if joined:
            path.addRoundedRect(card, RADIUS, RADIUS)
        r = self.tab_now()
        self.shown_tab = r
        if r is not None:
            tab = QPainterPath()
            bottom = card.top() + RADIUS if joined else r.bottom() - 0.5
            box = QRectF(r.left() + 0.5, r.top() + 0.5, r.width() - 1, bottom - r.top() - 0.5)
            tab.addRoundedRect(box, RADIUS, RADIUS)
            square = QPainterPath()                         # square at the bottom: no notch where it meets the card
            square.addRect(box.adjusted(0, RADIUS, 0, 0))
            tab = tab.united(square)
            if joined:
                for side in (-1, 1):
                    x = box.left() if side < 0 else box.right()
                    flare = QRectF(x - RADIUS if side < 0 else x, card.top() - RADIUS, RADIUS, RADIUS)
                    if flare.left() < card.left() + RADIUS or flare.right() > card.right() - RADIUS:
                        corner = QPainterPath()             # the tab over the card's own corner: square it
                        corner.addRect(QRectF(card.left() if side < 0 else card.right() - RADIUS, card.top(),
                                              RADIUS, RADIUS))
                        tab = tab.united(corner)
                        continue
                    fill = QPainterPath()
                    fill.addRect(flare.adjusted(-1 if side > 0 else 0, 0, 1 if side < 0 else 0, 1))
                    hollow = QPainterPath()
                    hollow.addEllipse(QPointF(x - RADIUS if side < 0 else x + RADIUS, card.top() - RADIUS),
                                      RADIUS, RADIUS)
                    tab = tab.united(fill.subtracted(hollow))
            path = path.united(tab) if joined else tab
        return path

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = self.shape()
        p.fillPath(path, QColor(self.colours["card"]))
        p.setPen(QPen(QColor(self.colours["edge"]), 1.0))
        p.drawPath(path)


class Phases(QWidget):
    """The central widget: the page of the phase. The row of the phases with its corner and the card of the bar
    are its `header`, which the window sets above the panels."""

    currentChanged = Signal(int)
    phaseVisibilityChanged = Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.shown = -1                             # the phase whose page and bar are shown
        self.tab_bar = PhaseTabBar()
        self.corner_box = QHBoxLayout()
        self.corner_box.setContentsMargins(0, 0, 0, 4)
        self.corner_box.setSpacing(4)
        self.bars = QStackedWidget()
        self.bars.setObjectName("phase-bars")
        self.bars.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.pages = QStackedWidget()
        self.pages.setObjectName("phase-pages")
        self.header = PhaseHeader(self.tab_bar, self.corner_box, self.bars)
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(0)
        box.addWidget(self.pages, 1)
        self.tab_bar.currentChanged.connect(self._changed)

    def add_phase(self, phase: phases.Phase, page: QWidget) -> int:
        """A phase with its page, at the place its number gives (the phases may come in any order); its bar comes
        with `set_bar` once the window has its actions."""
        before = [self.tab_bar.tabData(i) for i in range(self.tab_bar.count())]
        index = sum(1 for pid in before if phases.index_of(pid) < phases.index_of(phase.id))
        # the page paints its card (the style sheet's panel, line and corners): a plain QWidget does not
        page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.pages.insertWidget(index, page)
        self.tab_bar.insertTab(index, phase.label)
        self.tab_bar.setTabData(index, phase.id)
        return index

    def set_stale(self, pid: str, on: bool, tip: str = "") -> None:
        """The mark of values to update after the phase's name («3 Production ·», study 16, F1; design 3.12),
        with `tip` as the tab's tooltip; taken away when they are fresh again."""
        i = self.index_of_phase(pid)
        if i < 0:
            return
        label = phases.by_id(pid).label
        text = label + STALE_MARK if on else label
        if self.tab_bar.tabText(i) != text:
            self.tab_bar.setTabText(i, text)
        self.tab_bar.setTabToolTip(i, tip if on else "")

    def is_stale(self, pid: str) -> bool:
        i = self.index_of_phase(pid)
        return i >= 0 and self.tab_bar.tabText(i).endswith(STALE_MARK)

    def phase_id(self, index: int | None = None) -> str:
        """The id of the phase at `index` (the current one when None); "" when there is none."""
        i = self.tab_bar.currentIndex() if index is None else index
        return self.tab_bar.tabData(i) or "" if 0 <= i < self.tab_bar.count() else ""

    def index_of_phase(self, pid: str) -> int:
        return next((i for i in range(self.tab_bar.count()) if self.tab_bar.tabData(i) == pid), -1)

    def set_bar(self, index: int, bar: PhaseBar) -> None:
        self.bars.insertWidget(index, bar)
        if index == self.tab_bar.currentIndex():
            self.bars.setCurrentIndex(index)

    def bar(self, index: int) -> PhaseBar | None:
        w = self.bars.widget(index)
        return w if isinstance(w, PhaseBar) else None

    def set_text(self, on: bool) -> None:
        """Every bar with the words or without, and the stack as tall as the tallest: the same height in every
        phase, so that the views never jump (a QToolBar's size hint ignores its fixed height)."""
        heights = []
        for i in range(self.bars.count()):
            bar = self.bar(i)
            if bar is not None:
                bar.set_text(on)
                heights.append(bar.minimumHeight())
        self.bars.setFixedHeight(max(heights, default=TALL if on else LOW))

    def _changed(self, index: int) -> None:
        """The page and the bar's tools at once; the tab held where it is while the window paints the new page, then
        sliding to the new phase, short, painting only the band it moves in (R83, R97). Measured on the Dell at 200 %
        (25/10/2026): started with the click, its first 50 ms went into the page's paint and it jumped; started after
        it, every step is a frame. The tools do not slide: Daniel, 24/10/2026, «fanno un flicker a scatti molto
        fastidioso»."""
        from . import motion
        self.shown = index
        self.header.hold()
        self.pages.setCurrentIndex(index)
        if 0 <= index < self.bars.count():
            self.bars.setCurrentIndex(index)
        self.currentChanged.emit(index)
        # short (R97: at 240 and 180 ms, repainting the whole header at every step, it was «lenta» and «scattante» on
        # Windows)
        motion.after_work(self, lambda: self.header.play(Motion.FAST))

    # the face of the QTabWidget it replaces

    def tabBar(self) -> QTabBar:
        return self.tab_bar

    def currentIndex(self) -> int:
        return self.tab_bar.currentIndex()

    def setCurrentIndex(self, index: int) -> None:
        if 0 <= index < self.count() and self.tab_bar.isTabVisible(index):
            self.tab_bar.setCurrentIndex(index)

    def set_phase_visible(self, pid: str, visible: bool) -> None:
        """Keep a phase in the model while removing its navigation entry."""
        index = self.index_of_phase(pid)
        if index < 0 or self.tab_bar.isTabVisible(index) == visible:
            return
        self.tab_bar.setTabVisible(index, visible)
        self.tab_bar.update()
        self.header.update()
        self.phaseVisibilityChanged.emit(pid, visible)

    def count(self) -> int:
        return self.tab_bar.count()

    def tabText(self, index: int) -> str:
        return self.tab_bar.tabText(index)

    def widget(self, index: int) -> QWidget:
        return self.pages.widget(index)

    def currentWidget(self) -> QWidget:
        return self.pages.currentWidget()

    def indexOf(self, page: QWidget) -> int:
        return self.pages.indexOf(page)

    def setCornerWidget(self, widget: QWidget) -> None:
        self.corner_box.addWidget(widget)

    def top(self) -> int:
        """Where the page begins: under the row and the bar (the assistant floats below it)."""
        return self.pages.y()

    def set_colours(self, t: dict) -> None:
        self.header.set_colours(t)
        for i in range(self.bars.count()):
            bar = self.bar(i)
            if bar is not None:
                bar.set_colours(t)
