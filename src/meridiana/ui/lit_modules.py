"""The modules a sweep would take, lit as the pointer moves (R344; Daniel, 03/11/2026: «la selezione di più moduli con
il riquadro è molto scattosa, specie se ci sono tanti moduli»).

What it replaced was one painter path of all the lit modules, each with its halo and its outline, made again at every
move. Measured on 3,888 modules (offscreen, raster): 20 ms to make the item again, and 850 ms to paint it once all were
lit, because the rasteriser fills and strokes one path of thousands of sub-paths as one huge polygon (0.22 ms a module,
the same drawn module by module with its own polygon: 0.008 ms). So here:

- the lit modules are drawn one polygon each, into a layer of the viewport's own pixels (a QImage), not into the scene;
- a move draws only the modules that came or went, and those lit that touch their pixels (a grid of cells says which,
  in numpy): the cells are cleared and drawn again, clipped to them, so the layer is the same as if all were drawn;
- the layer is made again, whole, when the view moves or zooms, the colours change, or more modules changed than
  REDRAW_ALL.

No Qt object is made or deleted while the pointer moves; the item keeps its place in the scene (its z, under the
labels) and shows the layer."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPolygonF, QRegion
from PySide6.QtWidgets import QGraphicsItem

CELL = 16                       # the grid, in the viewport's pixels, that tells which modules a change touches
REDRAW_ALL = 1500               # more modules than this changed at once: the layer is made again whole


class LitModules(QGraphicsItem):
    """`quads` (N, 4, 2) are the modules in the scene's plane; `order` the indices of those lit."""

    def __init__(self, view, quads, reach: float) -> None:
        super().__init__()
        self.view = view
        self.quads = np.asarray(quads, dtype=float).reshape(-1, 4, 2)
        self.order = np.zeros(0, dtype=np.intp)
        self.halo = QPen()
        self.ink = QPen()
        self.fill = QColor()
        self.layer: QImage | None = None
        self.key = None
        self.style = None
        self.low = self.high = self.px = np.zeros((0, 2))
        self.size = (0, 0)
        self.drawn = 0                                  # modules drawn into the layer by the last change, for the tests
        if len(self.quads):
            lo, hi = self.quads.min(axis=(0, 1)), self.quads.max(axis=(0, 1))
            self.rect = QRectF(lo[0] - reach, lo[1] - reach, hi[0] - lo[0] + 2 * reach, hi[1] - lo[1] + 2 * reach)
        else:
            self.rect = QRectF()
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def boundingRect(self) -> QRectF:
        return self.rect

    def shape(self) -> QPainterPath:
        return QPainterPath()                           # nothing to pick: it is a light, not an object

    def set_style(self, halo: QPen, ink: QPen, fill: QColor) -> None:
        """The pens and the fill the modules are drawn with; the layer is made again when they change."""
        style = (halo.color().rgba(), halo.widthF(), ink.color().rgba(), ink.widthF(), fill.rgba())
        self.halo, self.ink, self.fill = QPen(halo), QPen(ink), QColor(fill)
        if style != self.style:
            self.style = style
            self.layer = None
            self.update()

    def set_modules(self, order) -> None:
        """The modules lit from now, as sorted indices: only what changed is drawn again."""
        order = np.asarray(order, dtype=np.intp)
        old, self.order = self.order, order
        if self.layer is None or self._key() != self.key:
            self.layer = None
            self.update()
            return
        changed = np.concatenate((np.setdiff1d(order, old, assume_unique=True),
                                  np.setdiff1d(old, order, assume_unique=True)))
        if not len(changed):
            return
        if len(changed) > REDRAW_ALL:
            self.layer = None
            self.update()
            return
        self._patch(changed)

    def paint(self, painter: QPainter, option=None, widget=None) -> None:
        if not len(self.order):
            return
        if self.layer is None or self._key() != self.key:
            self._rebuild()
        painter.save()
        painter.resetTransform()                        # the layer is in the viewport's pixels
        painter.drawImage(QPointF(0, 0), self.layer)
        painter.restore()

    # the layer

    def _key(self) -> tuple:
        t = self.view.viewportTransform()
        size = self.view.viewport().size()
        return (t.m11(), t.m12(), t.m21(), t.m22(), t.dx(), t.dy(), size.width(), size.height(),
                self.view.viewport().devicePixelRatioF(), self.style)

    def _rebuild(self) -> None:
        t = self.view.viewportTransform()
        size = self.view.viewport().size()
        dpr = self.view.viewport().devicePixelRatioF()
        self.key = self._key()
        self.size = (size.width(), size.height())
        x, y = self.quads[..., 0], self.quads[..., 1]
        self.px = np.stack((t.m11() * x + t.m21() * y + t.dx(), t.m12() * x + t.m22() * y + t.dy()), axis=-1)
        reach = max(self.halo.widthF(), self.ink.widthF()) / 2 + 1       # the stroke and its soft edge
        self.low = self.px.min(axis=1) - reach
        self.high = self.px.max(axis=1) + reach
        self.layer = QImage(max(1, round(size.width() * dpr)), max(1, round(size.height() * dpr)),
                            QImage.Format.Format_ARGB32_Premultiplied)
        self.layer.setDevicePixelRatio(dpr)
        self.layer.fill(Qt.GlobalColor.transparent)
        painter = QPainter(self.layer)
        self._draw(painter, self.order)
        painter.end()
        self.drawn = len(self.order)

    def _draw(self, painter: QPainter, which) -> None:
        """The modules `which`, each one polygon: first the halos, then the outlines over their fill."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        polygons = [QPolygonF([QPointF(x, y) for x, y in quad]) for quad in self.px[which].tolist()]
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(self.halo)
        for polygon in polygons:
            painter.drawPolygon(polygon)
        painter.setPen(self.ink)
        painter.setBrush(self.fill)
        for polygon in polygons:
            painter.drawPolygon(polygon)

    def _cells(self, which) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """The cells of the grid that the modules `which` reach: first and last (x, y) of each, and whether any is on
        the layer."""
        w, h = self.size
        grid = np.array([-(-w // CELL), -(-h // CELL)])
        first = np.floor(self.low[which] / CELL).astype(int)
        last = np.floor(self.high[which] / CELL).astype(int)
        on = np.all(last >= 0, axis=1) & np.all(first < grid, axis=1)
        return np.clip(first, 0, grid - 1), np.clip(last, 0, grid - 1), on

    def _patch(self, changed) -> None:
        """Draw again what the modules `changed` (came or went) touch: its cells cleared, then the lit ones over
        them drawn, clipped to the cells."""
        w, h = self.size
        gx, gy = -(-w // CELL), -(-h // CELL)
        first, last, on = self._cells(changed)
        first, last = first[on], last[on]
        if not len(first):
            self.drawn = 0
            return
        diff = np.zeros((gy + 1, gx + 1), dtype=np.int32)       # the cells marked, counted by their corners
        np.add.at(diff, (first[:, 1], first[:, 0]), 1)
        np.add.at(diff, (first[:, 1], last[:, 0] + 1), -1)
        np.add.at(diff, (last[:, 1] + 1, first[:, 0]), -1)
        np.add.at(diff, (last[:, 1] + 1, last[:, 0] + 1), 1)
        marked = diff.cumsum(axis=0).cumsum(axis=1)[:gy, :gx] > 0
        total = np.zeros((gy + 1, gx + 1), dtype=np.int32)      # how many marked cells in any block of cells
        total[1:, 1:] = marked.cumsum(axis=0).cumsum(axis=1)
        a, b, lit_on = self._cells(self.order)
        touched = (total[b[:, 1] + 1, b[:, 0] + 1] - total[a[:, 1], b[:, 0] + 1]
                   - total[b[:, 1] + 1, a[:, 0]] + total[a[:, 1], a[:, 0]]) > 0
        touching = self.order[lit_on & touched]
        region = QRegion()
        for y in np.flatnonzero(marked.any(axis=1)):
            edges = np.flatnonzero(np.diff(np.concatenate(([0], marked[y].astype(np.int8), [0]))))
            for start, stop in zip(edges[::2], edges[1::2], strict=True):
                region = region.united(QRegion(int(start) * CELL, int(y) * CELL, int(stop - start) * CELL, CELL))
        painter = QPainter(self.layer)
        painter.setClipRegion(region)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(region.boundingRect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        self._draw(painter, touching)
        painter.end()
        self.drawn = len(touching)
        inverse, ok = self.view.viewportTransform().inverted()
        if ok:
            self.update(inverse.mapRect(QRectF(region.boundingRect())))
        else:
            self.update()
