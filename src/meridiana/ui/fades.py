"""A soft edge where a list or a page goes on beyond its card (Daniel, 24/10/2026: «la fine dei contenuti
all'interno di una scheda quando questi non ci stanno non deve essere una troncatura netta, ci deve essere una sorta
di bordo con ombreggiamento che faccia intuire che non sono terminati»): a band of the card's colour fading out
over the first and the last pixels of the viewport, shown only on the side where there is more to scroll to.

The bands are children of the scroll area over its viewport, transparent to the pointer; they follow the scroll bar
and the area's size. `attach` once per area; `set_colour` with the theme."""

from __future__ import annotations

import weakref

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import QAbstractItemView, QAbstractScrollArea, QWidget

from .cards import default_tokens
from .design import Radius, Space

HEIGHT = Space.XL                # logical pixels of a band (24 until R161: «troppo accentuate» on a small screen)
# the band's opacity from the card's edge in: whole on the edge, so that nothing scrolled reaches the card's line
# (R177, Daniel 26/10/2026: «i contenuti ... non vengono sfumati correttamente e arrivano fino al limite della scheda
# sfondandolo», with 0.85 on the edge what was under it showed up to the line), then light at once (R161)
STOPS = ((0.0, 1.0), (0.18, 0.75), (0.5, 0.28), (1.0, 0.0))
SOLID = STOPS[0][1]
_COLOUR = [default_tokens()["panel"]]  # the panels' colour of the theme in use
_LIVE: "weakref.WeakSet[Fades]" = weakref.WeakSet()


class Edge(QWidget):
    def __init__(self, area: QAbstractScrollArea, top: bool):
        super().__init__(area)
        self.top = top
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.hide()

    def paintEvent(self, event) -> None:
        """The band inside the card's line and its rounded corners: it went over the border of the pages' cards
        (R161: «come se la sfumatura del contenuto finisse sopra i bordi»)."""
        p = QPainter(self)
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
    def __init__(self, area: QAbstractScrollArea):
        super().__init__(area)
        self.area = area
        self.edges = (Edge(area, True), Edge(area, False))
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


AIR = Space.S                    # between what scrolls in a page and the card's top and bottom lines (R177)


def attach(area: QAbstractScrollArea, air: bool = False) -> Fades | None:
    """The soft edges of `area`, made once. With `air`, what scrolls stops AIR pixels from the card's top and bottom
    lines and fades out before them (R177, Daniel 26/10/2026: «arrivano fino al limite della scheda sfondandolo»): for
    the pages and panels, not the lists, whose top margin is their header's."""
    if area is None:
        return None
    if air and not isinstance(area, QAbstractItemView):
        m = area.viewportMargins()
        if (m.top(), m.bottom()) != (AIR, AIR):
            area.setViewportMargins(m.left(), AIR, m.right(), AIR)
    found = area.findChild(Fades)
    return found if found is not None else Fades(area)


def set_colour(colour: str) -> None:
    """The panels' colour of the theme: the bands fade into it."""
    _COLOUR[0] = colour
    for f in list(_LIVE):
        for e in f.edges:
            e.update()
