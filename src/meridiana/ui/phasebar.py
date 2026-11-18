"""The row of the phases and the bar of each phase (task 17b; study 17, B4, Daniel's choice of 23/10/2026; design
document 3.3 and 5.3), built from phases.py. The row: «1 Modello», «2 Impianto»..., each number in a small disc
inside its tab (the accent's for the phase open), «Variant» in its right corner. Under the row, across the window,
a card with the bar of the phase: the tab of the phase open and the card are one shape (the target of 24/10/2026,
docs/studio/19-grafica), meeting the card with inverse rounded corners (R84, as GNOME's tabs); at a change of phase
the tab slides to the new one (R83, as Office's ribbon), the page and the tools change at once. The bar: one QToolBar per phase in a QStackedWidget, the groups side by side with their
title under them (small capitals, muted) and a thin line between; three modes (design.Bar, R333, R334): the words
under the icons (icons of 24, the word, the group's title), the words beside the icons (icons of 16, no titles, the
low bar of a laptop) or the icons alone (icons of 22, the group's title stays, it is what explains). The bar is there
in every phase, even with two groups: a row that comes and goes would move the views by 70 px at each change.

The buttons carry the window's QActions (one command, one action: the menus, the keys and the tooltips are the
same) with a short word of their own under the icon; the one button full of accent of the phase (Lay the modules,
Compute) has its icon in the colour of the text on the accent.

`Phases` is the central widget of the window (the pages) and speaks as the QTabWidget it replaces (currentIndex,
setCurrentIndex, currentChanged, tabBar, tabText, count, widget, currentWidget, setCornerWidget), so that the
window and its tests go on as before; its `header` (the row and the card of the bar) stands above the panels, in
the window's menu widget."""

from __future__ import annotations

import math

from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, QSize, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QFontMetricsF, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QMenu, QSizePolicy, QStackedWidget, QTabBar, QToolBar,
                               QToolButton, QToolTip, QVBoxLayout, QWidget)

from .. import arrangement, phases, theme_colors
from ..i18n import _, ngettext
from . import icons
from .cards import EDGE, RADIUS, default_tokens
from .design import Bar, Button, Icon, Motion, Radius, Size, Space, Text, set_text, text_font
from .motion import SLIDE_EASING
from .theme import tighten
from .waiting import STALE_MARK

TALL = 72                   # the bar with the words under the icons (design 5.3): what the bar must not exceed;
                            # 68 until R179 (Daniel 26/10/2026: «le descrizioni dei singoli strumenti vengono
                            # tagliati in basso»): the buttons were 4 px short of the line the word needs
LOW = 44                    # the icons alone
LOW_WINDOW = arrangement.LOW_WINDOW     # a lower window has no words under the icons (the laptop, a column)
ICON_TALL, ICON_LOW = Icon.TILE, Icon.BAR
# the word under the icon is Text.SECONDARY, the title of the group Text.GROUP (R159): read when used, the size of
# the text can change with the window open (R133)
GROUP_GAP = Space.XS                                    # between the commands and their group's name (R159)
TAB_HEIGHT = Size.CONTROL + Space.XS   # a compact control with equal breathing room above and below
HOVER_INSET = Space.XXS     # the ground of a phase under the pointer, in from its tab's sides (R160)
BADGE = Button.SMALL[0]      # the disc of a phase's number
TAB_PAD = (Space.L, Space.L)  # equal space before the disc and after the name
CARD_PAD = (Space.L - 2, Space.S, Space.L - 2, Space.S - 1)   # inside the card of the bar
BAR_SIDES = 2 * (EDGE + CARD_PAD[0])    # what the window takes off its width before the bar
ITEM_SPACE = Space.XXS      # what QToolBar's layout leaves on each side of an item, whatever the sheet's spacing says
                            # (measured; tests/widget/test_tool_menu.py holds the air between the groups to Bar.GROUP_AIR)


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
        self.compact = False                # the numbers, the name of the phase open alone (R334, study 27, F)
        self.picture: QPixmap | None = None  # the row as last drawn, and what it was drawn for (R97, R120)
        self.drawn_for = None
        self.currentChanged.connect(self._width_changed)

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

    def set_compact(self, on: bool) -> None:
        """The numbers, with the name of the phase open alone; the other names in their tooltips and with Ctrl+number."""
        if on != self.compact:
            self.compact = on
            self._width_changed()

    def _width_changed(self, _index: int = -1) -> None:
        """With the numbers a tab's width depends on the phase open: QTabBar asks its tabs again only when told."""
        if self.compact or _index < 0:
            self.setElideMode(self.elideMode())
            self.updateGeometry()

    def number_only(self, index: int) -> bool:
        return self.compact and index != self.currentIndex()

    def full_width(self) -> int:
        """What the row asks for with every name written, whatever it shows now."""
        return sum(self._named_width(i) for i in range(self.count()) if self.isTabVisible(i))

    def _named_width(self, index: int) -> int:
        _number, name = self.parts(self.tabText(index))
        text = math.ceil(QFontMetricsF(self.name_font(True)).horizontalAdvance(name)) + 2
        return TAB_PAD[0] + BADGE + 8 + text + TAB_PAD[1]

    def _number_width(self, index: int) -> int:
        stale = self.tabText(index).endswith(STALE_MARK)
        return TAB_PAD[0] + BADGE + (8 if stale else 0) + TAB_PAD[1]

    def tabSizeHint(self, index: int) -> QSize:
        return QSize(self._number_width(index) if self.number_only(index) else self._named_width(index), TAB_HEIGHT)

    def minimumTabSizeHint(self, index: int) -> QSize:
        if self.compact:
            return self.tabSizeHint(index)
        return QSize(TAB_PAD[0] + BADGE + 8 + 24 + TAB_PAD[1], TAB_HEIGHT)

    def tip_of(self, index: int) -> str:
        """What the tab says under the pointer: with the numbers its name comes first, the name being what is not shown."""
        tip = self.tabToolTip(index)
        if not self.number_only(index):
            return tip
        name = self.parts(self.tabText(index))[1].removesuffix(STALE_MARK)
        return f"{name}\n{tip}" if tip else name

    def event(self, event) -> bool:
        if event.type() == QEvent.Type.ToolTip and self.compact:
            i = self.tabAt(event.pos())
            if i >= 0:
                QToolTip.showText(event.globalPos(), self.tip_of(i), self, self.tabRect(i))
                return True
        return super().event(event)

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
        key = (self.size().toTuple(), ratio, self.currentIndex(), self.hovered, self.file_open, self.compact,
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
                if self.number_only(i):                 # the number alone, and the mark of values to update
                    if not name.endswith(STALE_MARK):
                        continue
                    name = STALE_MARK.strip()
                    x -= 8
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
        tighten(self)                                           # the words of the bar, where room is short (study 29)
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

    def words(self) -> list[str]:
        return [self.label]

    def fit(self, mode: str, height: int, width: int) -> None:
        """The button in a mode of the bar (design.Bar)."""
        self.setToolButtonStyle({Bar.UNDER: Qt.ToolButtonStyle.ToolButtonTextUnderIcon,
                                 Bar.BESIDE: Qt.ToolButtonStyle.ToolButtonTextBesideIcon,
                                 Bar.ICONS: Qt.ToolButtonStyle.ToolButtonIconOnly}[mode])
        self.setIconSize(QSize(Bar.ICON[mode], Bar.ICON[mode]))
        self.setFixedSize(width, height)


class CommandMenu(QMenu):
    """The menu of a divided button: the window's actions, with those that delete everything in red."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setToolTipsVisible(True)
        self.danger: dict = {}                      # an action -> its icon in red
        self.danger_colour = QColor(default_tokens()["danger"])

    def initStyleOption(self, option, action) -> None:
        super().initStyleOption(option, action)
        icon = self.danger.get(action)
        if icon is not None:
            option.palette.setColor(QPalette.ColorRole.ButtonText, self.danger_colour)
            option.icon = icon


class SplitFace(ToolButton):
    """The command of a divided button: its tooltip says the command of now, its key, and that there are others (study
    26, section 4, rule 7)."""

    def __init__(self, action, label: str, others: int, parent=None):
        self.others = others
        super().__init__(action, label, parent=parent)
        self.setObjectName("split-face")

    def _own(self) -> None:
        super()._own()
        action = self.defaultAction()
        if action is None:
            return
        head, _sep, rest = action.toolTip().partition("\n")
        more = ngettext("{n} more in the arrow", "{n} more in the arrow", self.others).format(n=self.others)
        tip = f"{head}. {more}" + (f"\n{rest}" if rest else "")
        if self.toolTip() != tip:
            self.setToolTip(tip)


class SplitStrip(QToolButton):
    """The strip of a divided button: as tall as the button, a chevron on it, alive when the command is off. A press
    opens the menu; it shows pressed while a command of the menu that is not on the face is on (the ones that delete
    never go on the face: rule 2)."""

    pressed_now = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("split-strip")
        self.setAutoRaise(True)
        self.setCheckable(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_NoMouseReplay)     # a press on it with the menu open only closes it
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.colours = _colours()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.pressed_now.emit()
            return
        event.ignore()

    def mouseReleaseEvent(self, event) -> None:
        event.ignore()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        colour = self.colours["text" if self.underMouse() or self.isDown() else "text2"]
        p.setPen(QPen(QColor(colour), Icon.STROKE, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                      Qt.PenJoinStyle.RoundJoin))
        x, y = self.width() / 2, self.height() / 2
        side = Space.XS - 1
        p.drawPolyline([QPointF(x - side, y - 1.5), QPointF(x, y + 1.5), QPointF(x + side, y - 1.5)])


class ToolMenuButton(QWidget):
    """A button shared by a few commands (R306, as AutoCAD's flyouts), in two parts (R333, Daniel 03/11/2026, study 26,
    G2): the command, which runs the one on its face, and a strip with a chevron, as tall as the button, each with its
    own state under the pointer, pressed and off. The strip, or the right button anywhere on the button, opens the menu
    of all of them with their names, keys and tooltips, and it stays alive when the command is off.

    What is on the face (study 26, section 4): a mode of drawing when it goes on, by the menu, by its key or by anything
    else, because a mode that is on must show (a checkable action; rules 1 and 4); never a command run once (rule 1);
    never from a family that deletes (`fixed`, rule 2); never by itself (rule 3: a command going off goes off on its
    face). It changes with a short fade, in the same place and at the same width (rule 5). It is not kept: every start
    has the first one (rule 6)."""

    def __init__(self, family: list, fixed: bool = False, danger: dict | None = None, parent=None):
        """`family`: (command id, the word under the icon, its QAction), the one shown at first first; `danger`: the
        command that goes last in red -> its icon's name."""
        super().__init__(parent)
        first, label, action = family[0]
        self.family = {cid: (word, a) for cid, word, a in family}
        self.command = first
        self.fixed = fixed
        self.danger = danger or {}
        self.face = SplitFace(action, label, len(family) - 1, self)
        self.strip = SplitStrip(self)
        self.strip.pressed_now.connect(self.open_menu)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(self.face)
        row.addWidget(self.strip)
        self.commands = CommandMenu(self)
        for cid, _word, a in family:
            if cid in self.danger:
                self.commands.addSeparator()
            self.commands.addAction(a)
            a.toggled.connect(lambda on, k=cid: self._toggled(k, on))
            a.changed.connect(self._say)
        self.set_colours(default_tokens())
        self._say()
        self._mark()

    # what the rest of the window asks of a button of the bar

    @property
    def label(self) -> str:
        return self.face.label

    def defaultAction(self):
        return self.face.defaultAction()

    def text(self) -> str:
        return self.face.text()

    def icon(self):
        return self.face.icon()

    def iconSize(self) -> QSize:
        return self.face.iconSize()

    def toolTip(self) -> str:
        return self.face.toolTip()

    def toolButtonStyle(self):
        return self.face.toolButtonStyle()

    def isChecked(self) -> bool:
        return self.face.isChecked()

    def click(self) -> None:
        self.face.click()

    def set_own_icon(self, icon) -> None:
        self.face.set_own_icon(icon)

    def setFont(self, font) -> None:
        super().setFont(font)
        self.face.setFont(font)

    def words(self) -> list[str]:
        return [word for word, _a in self.family.values()]

    def fit(self, mode: str, height: int, width: int) -> None:
        """The two parts in a mode of the bar: `width` is the command's."""
        self.face.fit(mode, height, width)
        self.strip.setFixedSize(Bar.STRIP, height)
        self.setFixedSize(width + Bar.STRIP, height)

    def set_colours(self, t: dict) -> None:
        self.strip.colours = _colours(t)
        self.strip.update()
        self.commands.danger_colour = QColor(t["danger"])
        self.commands.danger = {self.family[cid][1]: icons.icon(name, colour=t["danger"]) for cid, name in self.danger.items()}

    # the face

    def _toggled(self, command: str, on: bool) -> None:
        if on and not self.fixed:
            self.use(command)
        self._mark()

    def use(self, command: str) -> None:
        """`command` on the face from now on: the next click runs it."""
        if command == self.command:
            return
        from . import motion
        motion.crossfade(self.face, lambda: self._put(command), Motion.FAST)

    def _put(self, command: str) -> None:
        self.command = command
        word, action = self.family[command]
        self.face.label = word
        self.setProperty("tool", command)
        self.face.setDefaultAction(action)
        self.face._own()
        self._mark()

    def _mark(self) -> None:
        """The strip pressed while a command of the menu is on and not on the face."""
        self.strip.setChecked(any(a.isChecked() for cid, (_w, a) in self.family.items() if cid != self.command))

    def _say(self) -> None:
        names = ", ".join(word for word, _a in self.family.values())
        tip = _("All of them: {names} (the right button too)").format(names=names)
        on = next((word for cid, (word, a) in self.family.items() if cid != self.command and a.isChecked()), "")
        if on:
            tip = _("On now: {command}").format(command=on) + "\n" + tip
        if self.strip.toolTip() != tip:
            self.strip.setToolTip(tip)
            self.strip.setAccessibleName(tip)

    # the menu

    def open_menu(self, at: QPoint | None = None) -> None:
        self._say()
        self.strip.setDown(True)
        self.update()
        self.commands.exec(at if at is not None else self.mapToGlobal(QPoint(0, self.height() + 1)))
        self.strip.setDown(False)
        self.update()

    def contextMenuEvent(self, event) -> None:
        self.open_menu(event.globalPos())

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self.update()

    def paintEvent(self, event) -> None:
        """Under the pointer the controls' layer on both parts, as one shape: the part under the pointer adds its own
        over it, and that difference alone divides them (Daniel 03/11/2026, no line). A command that is off stays out."""
        if not (self.underMouse() or self.strip.isDown()):
            return
        ground = QRectF(self.rect() if self.face.isEnabled() else self.strip.geometry())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self.strip.colours["hover"]))
        p.drawRoundedRect(ground, Button.TOOL[1], Button.TOOL[1])


class ToolGroup(QWidget):
    """A group of the bar: its buttons in a row and its title under them."""

    def __init__(self, group: phases.Group, tools: list, actions: dict, parent=None):
        super().__init__(parent)
        self.group = group
        self.buttons: dict = {}                                 # command id -> its button
        self.shared: dict = {}                                  # the command of a button's menu -> the button (R306)
        self.primary: ToolButton | None = None
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(0)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(Bar.GAP)
        for tool in tools:
            family = [t for t in tool.family() if t.command in actions]
            for t in family:
                if actions[t.command].icon().isNull() and t.icon:
                    # a command that came without an icon takes the one its tool was designed with (R277: «On canopy»)
                    actions[t.command].setIcon(icons.icon(t.icon))
            words = [(t.command, t.label or _plain(actions[t.command].text()), actions[t.command]) for t in family]
            b = (ToolMenuButton(words, tool.fixed, {t.command: t.icon or t.command for t in family if t.danger})
                 if len(words) > 1 else ToolButton(actions[tool.command], tool.label or _plain(actions[tool.command].text())))
            b.setProperty("tool", tool.command)
            b.setFont(text_font(Text.STRONG if tool.primary else Text.SECONDARY, b.font()))
            if tool.primary:
                b.setProperty("primary", True)
                self.primary = b
                self.primary_icon = tool.icon or tool.command
            row.addWidget(b)
            self.buttons[tool.command] = b
            self.shared.update({t.command: b for t in family})
        box.addLayout(row)
        self.title_gap = QWidget()
        self.title_gap.setFixedHeight(GROUP_GAP)
        box.addWidget(self.title_gap)
        self.title = QLabel(group.title)
        self.title.setObjectName("group-title")
        self.title.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.title.setFont(text_font(Text.GROUP, self.title.font()))
        box.addWidget(self.title)

    def button_height(self, mode: str) -> int:
        """One height for all the buttons of a mode, in every group and phase: with the word under the icon the icon and
        the line of the largest word's font (R179: the large text was cut)."""
        if mode != Bar.UNDER:
            return Bar.HEIGHT
        return Bar.ICON[mode] + QFontMetrics(text_font(Text.STRONG, self.font())).height() + 2 * Space.XS + Space.XXS

    @staticmethod
    def command_width(button, mode: str) -> int:
        """The command's part of a button, by the rule of design.Bar: its longest word decides."""
        metrics = QFontMetrics(button.font())
        return Bar.width(mode, max(metrics.horizontalAdvance(word) for word in button.words()))

    def width_in(self, mode: str) -> int:
        """How wide the group is in a mode, asked without changing to it (arrangement.py)."""
        row = sum(self.command_width(b, mode) + (Bar.STRIP if isinstance(b, ToolMenuButton) else 0)
                  for b in self.buttons.values()) + Bar.GAP * (len(self.buttons) - 1)
        return row if mode == Bar.BESIDE else max(row, self.title.sizeHint().width())

    def set_mode(self, mode: str) -> int:
        """The buttons in a mode of the bar; the height of the group."""
        height = self.button_height(mode)
        for b in self.buttons.values():
            b.fit(mode, height, self.command_width(b, mode))
        titled = mode != Bar.BESIDE
        self.title_gap.setVisible(titled)
        self.title.setVisible(titled)
        if not titled:
            return height
        title = QFontMetrics(self.title.font()).height()
        self.title.setFixedHeight(title)
        return height + GROUP_GAP + title

    def set_colours(self, t: dict) -> None:
        if self.primary is not None:
            self.primary.set_own_icon(icons.icon(self.primary_icon, colour=t["text"]))      # no accent (R158)
        for b in self.buttons.values():
            if isinstance(b, ToolMenuButton):
                b.set_colours(t)


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
        self.layout().setContentsMargins(Space.XS, 1, Space.XS, 1)
        self.groups: list[ToolGroup] = []
        self.lines: list[QFrame] = []
        self.text = True
        self.mode = Bar.UNDER
        self.trailing: list = []                # the actions of what stands at the bar's end
        for group in phase.groups:
            tools = [t for t in group.tools if t.command in actions]
            if not tools:
                continue
            if self.groups:
                self._add_line()
            w = ToolGroup(group, tools, actions)
            self.addWidget(w)
            self.groups.append(w)
        self.set_text(True)

    def add_trailing(self, widget: QWidget) -> None:
        """`widget` at the right end of the bar, after a line: what the phase shows of itself (the Plant's strip)."""
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.trailing = [self.addWidget(spacer), self._add_line(), self.addWidget(widget)]

    def show_trailing(self, on: bool) -> None:
        """What stands at the bar's end, with its line: out, it leaves all its room to the groups."""
        for action in self.trailing:
            action.setVisible(on)

    def _add_line(self):
        """The line between two groups: as tall as the buttons, level with them (study 26, L2), the same air on its
        two sides."""
        holder = QWidget()
        air = Bar.GROUP_AIR - ITEM_SPACE
        holder.setFixedWidth(Bar.LINE + 2 * air)
        box = QVBoxLayout(holder)
        box.setContentsMargins(air, 0, air, 0)
        box.setSpacing(0)
        line = QFrame()
        line.setObjectName("bar-line")
        line.setFixedWidth(Bar.LINE)
        box.addWidget(line)
        box.addStretch(1)
        self.lines.append(line)
        return self.addWidget(holder)

    def width_in(self, mode: str) -> int:
        """How wide the groups are in a mode, what comes at the bar's end left out."""
        lines = max(0, len(self.groups) - 1)
        return sum(g.width_in(mode) for g in self.groups) + lines * (Bar.LINE + 2 * Bar.GROUP_AIR) + 2 * Space.XS

    def set_mode(self, mode: str) -> None:
        """The mode of the bar (design.Bar). The height is the one the buttons and the titles need (the stack gives
        every phase the tallest, so the views never jump): the tests keep it within TALL and LOW."""
        self.mode = mode
        self.text = mode != Bar.ICONS
        inside = max((g.set_mode(mode) for g in self.groups), default=(TALL if mode == Bar.UNDER else LOW) - 3)
        for line in self.lines:
            line.setFixedHeight(max((g.button_height(mode) for g in self.groups), default=Bar.HEIGHT))
        for g in self.groups:
            g.layout().activate()                       # a bar not in view: its groups' sizes are read before it shows
        self.layout().invalidate()
        self.setFixedHeight(inside + 3)                 # the toolbar's margins and the line under it
        self.updateGeometry()

    def set_text(self, on: bool) -> None:
        self.set_mode(Bar.UNDER if on else Bar.ICONS)

    def set_colours(self, t: dict) -> None:
        for g in self.groups:
            g.set_colours(t)

    def buttons(self) -> dict:
        """command id -> its button, over the groups: the buttons there are, each under the command it first shows."""
        out: dict = {}
        for g in self.groups:
            out.update(g.buttons)
        return out

    def button_of(self, command: str) -> ToolButton | None:
        """The button that holds `command`, shown on it or in its menu (R306)."""
        return next((g.shared[command] for g in self.groups if command in g.shared), None)

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
        # no tooltip (R347): it woke under the pointer as File was being opened, a little window over the page
        self.file_button.setAccessibleDescription(_("New, open, save, export, catalogues, settings and help"))
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
        self.slide.setEasingCurve(SLIDE_EASING)
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

    def set_mode(self, mode: str) -> None:
        """Every bar in a mode, and the stack as tall as the tallest: the same height in every phase, so that the
        views never jump (a QToolBar's size hint ignores its fixed height)."""
        heights = []
        for i in range(self.bars.count()):
            bar = self.bar(i)
            if bar is not None:
                bar.set_mode(mode)
                heights.append(bar.minimumHeight())
        self.bars.setFixedHeight(max(heights, default=TALL if mode == Bar.UNDER else LOW))

    def set_text(self, on: bool) -> None:
        self.set_mode(Bar.UNDER if on else Bar.ICONS)

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
