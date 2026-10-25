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
from PySide6.QtWidgets import QAbstractScrollArea, QWidget

from .cards import default_tokens
from .design import Radius, Space

HEIGHT = Space.XL                # logical pixels of a band (24 until R161: «troppo accentuate» on a small screen)
SOLID = 0.85                     # the band's opacity at the edge: what is under it still shows (R161)
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
        edge = QColor(_COLOUR[0])
        edge.setAlphaF(SOLID)
        half = QColor(edge)
        half.setAlphaF(SOLID * 0.35)
        clear = QColor(edge)
        clear.setAlpha(0)
        g = QLinearGradient(0, 0, 0, self.height())
        for at, colour in ((0.0, edge), (0.45, half), (1.0, clear)):
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


def attach(area: QAbstractScrollArea) -> Fades | None:
    """The soft edges of `area`, made once."""
    if area is None:
        return None
    found = area.findChild(Fades)
    return found if found is not None else Fades(area)


def set_colour(colour: str) -> None:
    """The panels' colour of the theme: the bands fade into it."""
    _COLOUR[0] = colour
    for f in list(_LIVE):
        for e in f.edges:
            e.update()
