"""A soft edge where a list or a page goes on beyond its card (Daniel, 24/10/2026: «la fine dei contenuti
all'interno di una scheda quando questi non ci stanno non deve essere una troncatura netta, ci deve essere una sorta
di bordo con ombreggiamento che faccia intuire che non sono terminati»): a band of the card's colour fading out
over the first and the last pixels of the viewport, shown only on the side where there is more to scroll to.

The bands are children of the scroll area over its viewport, transparent to the pointer; they follow the scroll bar
and the area's size. `attach` once per area; `set_colour` with the theme."""

from __future__ import annotations

import weakref

from PySide6.QtCore import QEvent, QObject, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPalette
from PySide6.QtWidgets import QAbstractItemView, QAbstractScrollArea, QWidget

from .cards import default_tokens
from .design import Radius, Space

HEIGHT = Space.L                 # a short veil: the first row becomes readable at once (R192)
# Whole only at the outermost pixel, so nothing scrolled reaches the card's line (R177). The quick falloff keeps the
# first visible row clear instead of covering it with the broad veil introduced by R177.
STOPS = ((0.0, 1.0), (0.16, 0.42), (0.5, 0.10), (1.0, 0.0))
PAGE_STOPS = ((0.0, 1.0), (0.18, 0.75), (0.5, 0.28), (1.0, 0.0))
SOLID = STOPS[0][1]
_COLOUR = [default_tokens()["panel"]]  # the panels' colour of the theme in use
_LIVE: "weakref.WeakSet[Fades]" = weakref.WeakSet()


class Edge(QWidget):
    def __init__(self, area: QAbstractScrollArea, top: bool, table: bool = False):
        super().__init__(area)
        self.area = area
        self.top = top
        self.table = table
        self.page = False
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.hide()

    def paintEvent(self, event) -> None:
        """Cover item view boundaries completely; page cards retain their rounded inner outline."""
        p = QPainter(self)
        if self.table or self.page:
            # A viewport is rectangular, even when the surrounding card has round corners.
            # Paint through the boundary pixel centres: inset clipping left a full-colour seam.
            base = (self.area.viewport().palette().color(QPalette.ColorRole.Base) if self.table else
                    QColor(_COLOUR[0]))
            if self.height() <= 1:
                p.fillRect(self.rect(), base)
                return
            g = QLinearGradient(0, 0.5, 0, self.height() - 0.5)
            for at, alpha in PAGE_STOPS if self.page else STOPS:
                colour = QColor(base)
                colour.setAlphaF(alpha)
                g.setColorAt(at if self.top else 1.0 - at, colour)
            p.fillRect(self.rect(), g)
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        g = QLinearGradient(0, 0, 0, self.height())
        for at, alpha in STOPS:
            colour = QColor(_COLOUR[0])
            colour.setAlphaF(alpha)
            g.setColorAt(at if self.top else 1.0 - at, colour)
        r = QRectF(self.rect()).adjusted(1, 1 if self.top else 0, -1, 0 if self.top else -1)
        radius = Radius.CARD - 1
        # rounded on the side of the card's edge only: the rectangle runs on past the other side
        outline = QRectF(r.x(), r.y() if self.top else r.y() - radius, r.width(), r.height() + radius)
        path = QPainterPath()
        path.addRoundedRect(outline, radius, radius)
        p.setClipRect(r)
        p.fillPath(path, g)


class Fades(QObject):
    def __init__(self, area: QAbstractScrollArea, table: bool = False):
        super().__init__(area)
        self.area = area
        self.edges = (Edge(area, True, table), Edge(area, False, table))
        self.frame = None
        bar = area.verticalScrollBar()
        bar.valueChanged.connect(self.follow)
        bar.rangeChanged.connect(self.follow)
        area.installEventFilter(self)
        area.viewport().installEventFilter(self)
        _LIVE.add(self)
        self.follow()

    def eventFilter(self, obj, event) -> bool:
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.Move):
            self.follow()
        return False

    def follow(self, *_args) -> None:
        port = self.area.viewport().geometry()
        bar = self.area.verticalScrollBar()
        top, bottom = self.edges
        h = min(HEIGHT, max(0, port.height() // 5))
        top.setGeometry(port.x(), port.y(), port.width(), h)
        bottom.setGeometry(port.x(), port.y() + port.height() - h, port.width(), h)
        top.setVisible(bar.value() > bar.minimum())
        bottom.setVisible(bar.value() < bar.maximum())
        top.raise_()
        bottom.raise_()
        if self.frame is not None:
            self.frame.raise_()


AIR = Space.S                    # between what scrolls in a page and the card's top and bottom lines (R177)


def attach(area: QAbstractScrollArea, air: bool = False, *, table: bool = False) -> Fades | None:
    """The soft edges of `area`, made once. With `air`, what scrolls stops AIR pixels from the card's top and bottom
    lines and fades out before them (Meridiana's R177, Daniel 26/10/2026: «arrivano fino al limite della scheda
    sfondandolo»): for the pages and panels, not the lists, whose top margin is their header's.
    `table` opts data tables into their viewport's Base; navigation keeps the panel colour."""
    if area is None:
        return None
    if air and not isinstance(area, QAbstractItemView):
        m = area.viewportMargins()
        if (m.top(), m.bottom()) != (AIR, AIR):
            area.setViewportMargins(m.left(), AIR, m.right(), AIR)
    found = area.findChild(Fades)
    if found is not None:
        controller = found
    else:
        controller = Fades(area, table)
    for edge in controller.edges:
        edge.table = edge.table or table
        # A page's viewport is already inset from its card by AIR. Rounding and insetting this
        # overlay again left an uncovered row and cut text sharply at the viewport boundary.
        edge.page = edge.page or (air and not isinstance(area, QAbstractItemView))
        edge.update()
    return controller


def set_colour(colour: str) -> None:
    """The panels' colour of the theme: the bands fade into it."""
    _COLOUR[0] = colour
    for f in list(_LIVE):
        for e in f.edges:
            e.update()
