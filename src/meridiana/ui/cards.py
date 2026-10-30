"""The panels as cards (study 17, A3, Daniel's choice of 23/10/2026: «mi piacciono molto»; the target of
24/10/2026, docs/studio/19-grafica): each dock a rounded card floating on the window's floor, EDGE px from the
window's sides and GAP px from the bar above, from the status bar and from its neighbours (the separators of the
main window are the gap, and stay draggable), its title inside the card, 12 px from its edge, in the text's
colour; a thin line around it in both themes and no shadow (Daniel's choice of 24/10/2026 between two trials:
«vai con niente ombre»); a dock dragged out loses the card and is a plain dock again. The views (plan, 3D) stand 6 px inside their card with their four corners rounded (R77; design 3.2).

Depth rules (design, 3.2 and C2; 24/10/2026): radius 8 for a card and a tile, 6 for a view inside its card,
6 for a group, a field and a button; one line
of 1 px per level; never a card inside a card."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QMargins, QObject, QPointF, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QDockWidget, QMainWindow, QStatusBar, QToolBar, QToolButton, QWidget

from .. import theme_colors
from ..i18n import _
from .design import Layout, Radius, Space


def default_tokens() -> dict:
    return theme_colors.derive(theme_colors.DEFAULT_SEED, False).tokens


# the measures of the design system (ui/design.py), by the names this module has always used
GAP = Layout.GAP        # between two cards, and from the bars above and below; the separators too
EDGE = Layout.EDGE      # from the window's sides (Daniel, 24/10/2026: «margini con l'esterno un po' più accentuati»)
RADIUS = Radius.CARD
PAD = Layout.PAD        # inside the card, around the content
TITLE_X = Layout.TITLE_X
TITLE_PAD = (Space.M + 1, Space.XS + 1)    # above and below the title: its 14 px line centred on 34
VIEW_RADIUS = Radius.VIEW


def arena(window: QMainWindow) -> QRect:
    """The part of the main window between its bars: the menu bar and the toolbars above, the status bar below,
    toolbars on the sides. The cards keep GAP from its edges. The bars are the window's own children: looked for among
    them only (among all the window's widgets it cost 0.7 ms, at every step of a panel's edge dragged, R120)."""
    r = window.rect()
    direct = Qt.FindChildOption.FindDirectChildrenOnly
    left, top, right, bottom = r.left(), r.top(), r.right() + 1, r.bottom() + 1
    menu = window.menuWidget()
    if menu is not None and menu.isVisible():
        top = max(top, menu.geometry().bottom() + 1)
    # the visible one: a window given its status bar by setStatusBar keeps the replaced one, hidden, until it is
    # deleted, and the panel previews measured their cards against the window's bottom edge (R294)
    status = next((s for s in window.findChildren(QStatusBar, options=direct) if s.isVisible()), None)
    if status is not None and status.parentWidget() is window:
        bottom = min(bottom, status.geometry().top())
    for bar in window.findChildren(QToolBar, options=direct):
        if bar.parentWidget() is not window or not bar.isVisible() or bar.isFloating():
            continue
        g, area = bar.geometry(), window.toolBarArea(bar)
        if area == Qt.ToolBarArea.TopToolBarArea:
            top = max(top, g.bottom() + 1)
        elif area == Qt.ToolBarArea.BottomToolBarArea:
            bottom = min(bottom, g.top())
        elif area == Qt.ToolBarArea.LeftToolBarArea:
            left = max(left, g.right() + 1)
        elif area == Qt.ToolBarArea.RightToolBarArea:
            right = min(right, g.left())
    return QRect(left, top, max(0, right - left), max(0, bottom - top))


def gaps(widget: QWidget, window: QMainWindow, gap: int = GAP, edge: int = EDGE) -> QMargins:
    """The margins that keep `widget` (a child of the main window) `edge` pixels from the window's sides and `gap`
    pixels from the bars above and below, where it touches them; nothing on the sides that face another card,
    where the separator is the gap."""
    a, g = arena(window), widget.geometry()

    def near(x, y) -> bool:
        return abs(x - y) <= 2
    # with the bottom right corner given to the right column (window.py), Qt lays that column one separator
    # (8 px) under the status bar (measured on 24/10/2026): the card keeps its gap above the bar. At most GAP:
    # an overrun made by the docks' minimum sizes would grow with the margin, and the window with it
    over = min(gap, max(0, g.bottom() - a.bottom()))
    return QMargins(edge if near(g.left(), a.left()) else 0, gap if near(g.top(), a.top()) else 0,
                    edge if near(g.right(), a.right()) else 0,
                    gap + over if g.bottom() >= a.bottom() - 2 else 0)


class Corner(QWidget):
    """One corner of a view, `VIEW_RADIUS` square: what lies outside the view's rounded rectangle, painted in the
    colour of the card behind it, smooth at any density (a mask is a staircase). Transparent to the pointer."""

    def __init__(self, view: QWidget, which: int):
        super().__init__(view)
        self.which = which                          # 0 top left, 1 top right, 2 bottom left, 3 bottom right
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

    def paintEvent(self, event) -> None:
        r = float(self.width())
        right, bottom = self.which in (1, 3), self.which in (2, 3)
        box = QRectF(-r if right else 0.0, -r if bottom else 0.0, 2 * r, 2 * r)   # the corner's circle, doubled
        rest = QPainterPath()
        rest.addRect(QRectF(0, 0, r, r))
        arc = QPainterPath()
        arc.addRoundedRect(box, r, r)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillPath(rest.subtracted(arc), QColor(_CORNER_COLOUR[0]))


_CORNER_COLOUR = [default_tokens()["panel"]]    # the cards' colour of the theme in use
_ROUNDED: list = []                             # the views rounded, to repaint their corners with the theme


class Rounder(QObject):
    """Keeps the four corners of a view rounded: four small widgets over its corners, moved when it grows."""

    def __init__(self, widget: QWidget, radius: int):
        super().__init__(widget)
        self.radius = radius
        self.widget = widget
        self.corners = [Corner(widget, i) for i in range(4)]
        widget.installEventFilter(self)
        _ROUNDED.append(self)
        self.apply()

    def apply(self) -> None:
        w, r = self.widget, self.radius
        spots = ((0, 0), (w.width() - r, 0), (0, w.height() - r), (w.width() - r, w.height() - r))
        for corner, (x, y) in zip(self.corners, spots, strict=True):
            corner.setGeometry(x, y, r, r)
            corner.raise_()

    def eventFilter(self, obj, event) -> bool:
        if obj is self.widget and event.type() in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.ChildAdded):
            self.apply()
        return False


def round_corners(widget: QWidget, radius: int = VIEW_RADIUS) -> Rounder:
    """`widget` with its four corners rounded inside its card (the plan and the 3D view, design 3.2)."""
    return Rounder(widget, radius)


def set_corner_colour(colour: str) -> None:
    """The cards' colour of the theme: the views' corners are painted in it."""
    _CORNER_COLOUR[0] = colour
    for rounder in list(_ROUNDED):
        try:
            for c in rounder.corners:
                c.update()
        except RuntimeError:                        # a view gone with its window
            _ROUNDED.remove(rounder)


class GapKeeper(QObject):
    """Keeps the central widget of the main window GAP pixels from the arena's edges it touches (the sides
    where no card stands between it and the window's edge). The check runs when the widget moves and once more
    after the layout pass that moved it: in the middle of a pass the menu bar may not be in its place yet, and
    a window restored from its saved state kept a wrong gap until the next resize (task 17b)."""

    def __init__(self, widget: QWidget):
        super().__init__(widget)
        self.widget = widget
        self.pending = False
        widget.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Move, QEvent.Type.Show):
            self.apply()
            if not self.pending:
                self.pending = True
                QTimer.singleShot(0, self, self.apply)
        return False

    def apply(self) -> None:
        self.pending = False
        window = self.widget.parentWidget()
        if isinstance(window, QMainWindow):
            margins = gaps(self.widget, window)
            if margins != self.widget.contentsMargins():
                self.widget.setContentsMargins(margins)


def keep_gaps(widget: QWidget) -> GapKeeper:
    return GapKeeper(widget)


class CloseButton(QToolButton):
    """The cross that closes the panel, drawn by the painter (no icon file, no symbol font)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoRaise(True)
        from .design import Button
        self.setFixedSize(Button.SMALL[0], Button.SMALL[0])      # a small button on a title (R121)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setToolTip(_("Close the panel; View > Panels brings it back"))
        self.colour = QColor(default_tokens()["muted"])
        self.veil = QColor(theme_colors.qt_hex(default_tokens()["hover"]))

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.underMouse():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self.veil)
            p.drawRoundedRect(QRectF(self.rect()), Radius.INNER, Radius.INNER)
        p.setPen(QPen(self.colour, 1.5))
        c = QPointF(self.width() / 2, self.height() / 2)
        d = 3.5
        p.drawLine(QPointF(c.x() - d, c.y() - d), QPointF(c.x() + d, c.y() + d))
        p.drawLine(QPointF(c.x() - d, c.y() + d), QPointF(c.x() + d, c.y() - d))


class CardTitle(QWidget):
    """The title bar of a card: the dock's title in the text's colour, a little larger than the text and
    semibold, TITLE_X pixels from the card's left edge, and the cross that closes it, as far from the right edge.
    Mouse events it does not take go to the dock, which moves it as usual (QDockWidget::setTitleBarWidget)."""

    def __init__(self, dock: QDockWidget):
        super().__init__(dock)
        self.dock = dock
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        t = default_tokens()
        self.colours = {"text": t["text"], "header": t["header"]}
        self.measured = ("", 0)            # the font's key and its line's height: asked thousands of times (R120)
        # the dock's child, not the bar's: QDockWidget lays the title bar at x 0 as wide as the content, and the
        # cross of a card against the window's left side fell out of it (2 px of 18 showed; qt-app-template)
        self.close_button = CloseButton(dock)
        self.close_button.clicked.connect(dock.close_animated)
        dock.windowTitleChanged.connect(lambda _t: self.update())
        dock.featuresChanged.connect(self._features)
        self._features(dock.features())

    def _features(self, features) -> None:
        self.close_button.setVisible(bool(features & QDockWidget.DockWidgetFeature.DockWidgetClosable))

    def title_font(self) -> QFont:
        from .design import Text, text_font
        return text_font(Text.TITLE, self.font())

    def card_box(self) -> QRect:
        """The card's rectangle in the title bar's own pixels (the bar may start above the card, in the gap)."""
        card = self.dock.card_rect() if not self.dock.isFloating() else self.dock.rect()
        return card.translated(-self.pos())

    def line_height(self) -> int:
        """The title's line, measured again only when the font changed: the layout asks it at every step of a panel's
        edge dragged, and a font and its metrics made each time cost 5 ms a step (R120, 25/10/2026)."""
        key = self.font().key()
        if key != self.measured[0]:
            from PySide6.QtGui import QFontMetrics
            self.measured = (key, QFontMetrics(self.title_font()).height())
        return self.measured[1]

    def sizeHint(self) -> QSize:
        above = max(0, self.dock.card_rect().top() - self.y()) if not self.dock.isFloating() else 0
        return QSize(60, above + TITLE_PAD[0] + self.line_height() + TITLE_PAD[1])

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.place()

    def place(self) -> None:
        """The cross TITLE_X from the card's right edge, on the title's line, in the dock's pixels."""
        card = self.dock.card_rect() if not self.dock.isFloating() else self.geometry()
        b = self.close_button
        mid = card.top() + TITLE_PAD[0] + self.line_height() // 2
        b.move(card.right() - TITLE_X + 4 - b.width() + 1, mid - b.height() // 2)
        b.raise_()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        if self.dock.isFloating():                          # a plain dock again: a header band
            p.fillRect(self.rect(), QColor(self.colours["header"]))
        card = self.card_box()
        p.setFont(self.title_font())
        p.setPen(QColor(self.colours["text"]))
        r = QRect(card.left() + TITLE_X, card.top() + TITLE_PAD[0],
                  max(0, card.width() - 2 * TITLE_X - self.close_button.width()), self.line_height())
        p.drawText(r, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.dock.windowTitle())


class CardDock(QDockWidget):
    """A dock drawn as a card when docked. The colours come from the window's theme (`parent.theme`), or from
    `set_colours`."""

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.dark = False
        self.colours: dict = {}
        self._outer = QMargins()
        self._fit_pending = False
        self.title_bar = CardTitle(self)
        self.setTitleBarWidget(self.title_bar)
        from .dock_motion import DockDrag
        self.drag_motion = DockDrag(self, self.title_bar)
        self.topLevelChanged.connect(lambda _f: self._fit())
        theme = getattr(parent, "theme", None)
        if theme is not None and getattr(theme, "tokens", None):
            self.set_colours(theme.tokens, theme.dark)
            theme.changed.connect(lambda: self.set_colours(theme.tokens, theme.dark))
        else:
            self.set_colours(default_tokens(), False)

    def set_colours(self, t: dict, dark: bool) -> None:
        """The theme's tokens: the card on `panel` with a soft line around it, in both themes (the mockups)."""
        self.dark = dark
        # the line between line_soft and line: seen in both themes without drawing a frame (24/10/2026)
        self.colours = {"bg": t["panel"], "line": t["card_line"],
                        "muted": t["muted"], "header": t["header"], "field": t["field"]}
        self.title_bar.colours = {"text": t["text"], "header": t["header"]}
        self.title_bar.close_button.colour = QColor(t["muted"])
        self.title_bar.close_button.veil = QColor(theme_colors.qt_hex(t["hover"]))      # R160
        self.update()
        self.title_bar.update()

    def close_animated(self) -> None:
        from .dock_motion import reflow
        window = self.parentWidget()
        if isinstance(window, QMainWindow) and not self.isFloating():
            area = window.dockWidgetArea(self)
            edge = {Qt.DockWidgetArea.BottomDockWidgetArea: "bottom",
                    Qt.DockWidgetArea.TopDockWidgetArea: "top",
                    Qt.DockWidgetArea.LeftDockWidgetArea: "left"}.get(area, "right")
            reflow(window, self.close, edge=edge)
        else:
            self.close()

    def card_rect(self) -> QRect:
        """Where the card is drawn, in the dock's own pixels."""
        return self.rect().marginsRemoved(self._outer)

    def _fit(self) -> None:
        self._fit_now()
        # once more after the layout pass: in the middle of it the menu widget (the phases' header) may not be in
        # its place yet, and a card under it kept no gap (the same as GapKeeper)
        if not self._fit_pending:
            self._fit_pending = True
            QTimer.singleShot(0, self, self._fit_later)

    def _fit_later(self) -> None:
        self._fit_pending = False
        self._fit_now()

    def _fit_now(self) -> None:
        window = self.parentWidget()
        if self.isFloating() or not isinstance(window, QMainWindow):
            self._outer = QMargins()
            self.setContentsMargins(0, 0, 0, 0)
        else:
            outer = gaps(self, window)
            if outer != self._outer:
                self._outer = outer
                self.title_bar.updateGeometry()
            self.setContentsMargins(self._outer + QMargins(PAD, 0, PAD, PAD))
        self.title_bar.place()
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit()

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        self._fit()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._fit()

    def paintEvent(self, event) -> None:
        if self.isFloating() or not self.colours:
            super().paintEvent(event)
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.card_rect()).adjusted(0.5, 0.5, -0.5, -0.5), RADIUS, RADIUS)
        p.fillPath(path, QColor(self.colours["bg"]))
        p.setPen(QPen(QColor(self.colours["line"]), 1.0))
        p.drawPath(path)
