"""pyqtgraph behind the charts (ui/charts.py), loaded the first time a chart is drawn: importing it costs some
0,35 s, paid in a thread of its own when an energy page is about to be seen (charts.preload). Here are the
pieces that subclass pyqtgraph: the plot widget that takes the wheel only where it zooms, the view that zooms
on x alone, the axes in the theme's ink with the numbers written by number(), the legend whose entries turn
their series on and off, the colour scale of a heat map, the exports to SVG and PNG.

Study 17, D.4: pyqtgraph draws an hourly year (8.760 points) in 24-32 ms and answers the pointer in 2-4 ms,
where matplotlib needed 150-190 ms for every change of the drawing."""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QLinearGradient, QPainter, QPicture, QTransform
from PySide6.QtWidgets import QGraphicsGridLayout, QGraphicsLinearLayout, QGraphicsRectItem, QLabel

from .design import Size, Type

__all__ = ["Axis", "ColourScale", "Entry", "Legend", "Plot", "View", "colour", "colour_bar", "colour_map", "export",
           "hover_box", "pg"]

# antialiasing on: measured at 24-31 ms against 32-38 for the first drawing, 3-4 ms against 2-3 for the
# pointer (study 17, D.4), nothing that counts; images row by row, as numpy writes a matrix
pg.setConfigOptions(antialias=True, imageAxisOrder="row-major")

TOP = 22                        # px above the plotted area: the readout of the value under the pointer sits there


def colour(c: str, alpha: int | None = None) -> QColor:
    q = QColor(c)
    if alpha is not None:
        q.setAlpha(alpha)
    return q


class Axis(pg.AxisItem):
    """An axis whose numbers are written by the program (number(), with the decimal comma), never scaled
    to an SI prefix; the wheel and the drag over it are left to the plot widget."""

    def __init__(self, orientation: str):
        super().__init__(orientation)
        self.fmt: Callable[[float], str] | None = None
        self.enableAutoSIPrefix(False)

    def boundingRect(self):
        """With the grid on, pyqtgraph's rectangle stops at the ends of the axis and the number at an end (the 0
        of a bar chart) was dropped: the ends get the room they have without the grid."""
        r = super().boundingRect()
        if self.grid is False:
            return r
        own = self.mapRectFromParent(self.geometry())
        m = 15
        return r | (own.adjusted(0, -m, 0, m) if self.orientation in ("left", "right") else own.adjusted(-m, 0, m, 0))

    def tickValues(self, minVal, maxVal, size):
        return super().tickValues(minVal, maxVal, size)[:1]     # the major ticks only: a hairline grid, not a mesh

    def tickStrings(self, values, scale, spacing):
        if self.fmt is None:
            return super().tickStrings(values, scale, spacing)
        return [self.fmt(v) for v in values]

    def wheelEvent(self, event):
        event.ignore()

    def mouseDragEvent(self, event):
        event.ignore()


class View(pg.ViewBox):
    """The plotted area. It zooms only when the chart says so (the hourly and weekly series, design 5.2):
    on x alone, with the wheel or by dragging a band across it; a double click shows everything again. The
    y-axis keeps the range of the data."""

    def __init__(self):
        super().__init__(enableMenu=False)
        self.zoomable = False
        self.full: tuple[float, float] | None = None       # the whole x range, for the double click
        self.setMouseMode(self.RectMode)
        self.setMouseEnabled(x=False, y=False)

    def set_zoomable(self, on: bool, full: tuple[float, float]) -> None:
        self.zoomable = on
        self.full = full
        self.setMouseEnabled(x=on, y=False)
        if on:
            span = full[1] - full[0]
            self.setLimits(xMin=full[0], xMax=full[1], minXRange=max(span / 500.0, 1e-9))
        else:
            self.setLimits(xMin=None, xMax=None, minXRange=None)

    def zoom_x(self, factor: float, centre: float) -> None:
        """x scaled by factor round the value centre (factor < 1 brings the view closer)."""
        self.scaleBy(x=factor, center=QPointF(centre, 0.0))

    def show_all(self) -> None:
        if self.full is not None:
            self.setXRange(self.full[0], self.full[1], padding=0)

    def wheelEvent(self, ev, axis=None):
        if not self.zoomable:
            ev.ignore()
            return
        super().wheelEvent(ev, axis=0)                      # x only, wherever the wheel turns

    def mouseDragEvent(self, ev, axis=None):
        if not self.zoomable or ev.button() != Qt.MouseButton.LeftButton or axis is not None:
            ev.ignore()
            return
        super().mouseDragEvent(ev)                          # the band, then showAxRect

    def updateScaleBox(self, p1, p2):
        """The band being dragged, the whole height of the area."""
        r = self.childGroup.mapRectFromParent(QRectF(p1, p2))
        y0, y1 = self.viewRange()[1]
        self.rbScaleBox.setPos(QPointF(r.left(), y0))
        self.rbScaleBox.setTransform(QTransform.fromScale(r.width(), y1 - y0))
        self.rbScaleBox.show()

    def showAxRect(self, ax, **kwargs):
        r = ax.normalized()
        if r.width() > 0:
            self.setXRange(r.left(), r.right(), padding=0)
        self.sigRangeChangedManually.emit(self.state["mouseEnabled"])


class Entry(pg.GraphicsWidget):
    """One entry of the legend: the series' colour and its name; a click turns the series on and off, and an
    entry turned off is dimmed and struck through."""

    def __init__(self, name: str, colour_: str, font: QFont, ink: str, toggled: Callable[[Entry], None]):
        super().__init__()
        self.name, self.colour, self.font, self.ink, self.toggled = name, colour_, QFont(font), ink, toggled
        self.on = True
        fm = QFontMetricsF(self.font)
        self.w = 12 + 5 + fm.horizontalAdvance(name) + 2
        self.h = max(16.0, fm.height() + 2)
        self.setMinimumSize(self.w, self.h)
        self.setMaximumSize(self.w, self.h)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(name)

    def boundingRect(self):
        return QRectF(0, 0, self.w, self.h)

    def set_on(self, on: bool) -> None:
        self.on = on
        self.update()

    def paint(self, p, *_args):
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(1.0 if self.on else 0.4)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self.colour))
        p.drawRoundedRect(QRectF(0, (self.h - 12) / 2, 12, 12), 2, 2)
        font = QFont(self.font)
        font.setStrikeOut(not self.on)
        p.setFont(font)
        p.setPen(QColor(self.ink))
        p.drawText(QRectF(17, 0, self.w - 17, self.h), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                   self.name)

    def mouseClickEvent(self, ev):
        if ev.button() != Qt.MouseButton.LeftButton:
            ev.ignore()
            return
        ev.accept()
        self.toggled(self)


class Legend(pg.GraphicsWidget):
    """The legend under the plotted area, in the scene (so that the exports carry it), four entries a row."""

    COLUMNS = 4

    def __init__(self):
        super().__init__()
        self.grid = QGraphicsGridLayout()
        self.grid.setContentsMargins(0, 4, 0, 0)
        self.grid.setHorizontalSpacing(14)
        self.grid.setVerticalSpacing(2)
        self.setLayout(self.grid)
        self.entries: list[Entry] = []

    def clear(self) -> None:
        for e in self.entries:
            self.grid.removeItem(e)
            if e.scene() is not None:
                e.scene().removeItem(e)
        self.entries = []

    def add(self, entry: Entry) -> None:
        k = len(self.entries)
        self.grid.addItem(entry, k // self.COLUMNS, k % self.COLUMNS)
        self.entries.append(entry)


class Plot(pg.PlotWidget):
    """The widget of a chart: pyqtgraph's plot with the view above, the axes above, the legend under the
    plotted area, a label for the value under the pointer in the margin over it. The pointer is read from
    the scene's sigMouseMoved through a SignalProxy at 60 a second; the wheel goes to the view when it
    zooms and to the page under it when it does not (so that the page scrolls over a chart)."""

    def __init__(self, moved: Callable, left: Callable, menu: Callable):
        self.view = View()
        super().__init__(viewBox=self.view, axisItems={"left": Axis("left"), "bottom": Axis("bottom")})
        self._left, self._menu = left, menu
        self.setMinimumHeight(Size.CHART_MIN_HEIGHT)  # the page under it keeps its strip in a 960 px window
        pi = self.getPlotItem()
        pi.hideButtons()
        pi.setMenuEnabled(False)
        pi.layout.setContentsMargins(4, TOP, 10, 4)
        for side in ("left", "bottom"):
            self.getAxis(side).setZValue(-1)                # the grid under the bars and the lines
        self.legend_box = Legend()
        self.colour_bar = None
        self.readout = QLabel(self.viewport())
        self.readout.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.readout.hide()
        self.proxy = pg.SignalProxy(self.scene().sigMouseMoved, rateLimit=60, slot=moved)

    # what is drawn

    def reset(self, c: dict, font: QFont) -> None:
        """Nothing drawn, in the theme's colours: the items, the legend, the colour scale, the ticks, the
        ranges and the zoom of the drawing before go."""
        pi = self.getPlotItem()
        pi.clear()
        self.legend_box.clear()
        pi.layout.removeItem(self.legend_box)
        self.legend_box.hide()
        if self.colour_bar is not None:
            pi.layout.removeItem(self.colour_bar)
            if self.colour_bar.scene() is not None:
                self.colour_bar.scene().removeItem(self.colour_bar)
            self.colour_bar = None
            pi.layout.setColumnFixedWidth(4, 0)             # the gap ColorBarItem keeps before it
        pi.setTitle(None)
        v = self.view
        v.disableAutoRange()
        v.invertY(False)
        v.set_zoomable(False, (0.0, 1.0))
        v.rbScaleBox.setPen(pg.mkPen(c["ink2"], width=1))
        v.rbScaleBox.setBrush(pg.mkBrush(colour(c["ink2"], 0x26)))
        self.setBackground(c["surface"])
        small = QFont(font)
        small.setPixelSize(Type.CAPTION)
        for side in ("left", "bottom"):
            a = self.getAxis(side)
            a.fmt = None
            a.setTicks(None)
            a.setLabel(None)
            a.showLabel(False)
            a.setGrid(False)
            a.setStyle(tickLength=0, tickTextOffset=6, tickAlpha=255, tickFont=small, showValues=True)
            a.setTextPen(c["muted"])
            a.setTickPen(c["grid"])
            pi.showAxis(side)
        self.getAxis("bottom").setPen(c["axis"])
        self.getAxis("left").setPen(pg.mkPen(None))
        self.readout.setFont(small)
        self.readout.setStyleSheet(f"color: {c['ink2']}; background: transparent;")
        self.readout.hide()

    def grid(self, x: bool = False, y: bool = False) -> None:
        self.getAxis("bottom").setGrid(255 if x else False)
        self.getAxis("left").setGrid(255 if y else False)

    def fit(self, left: list[str], font: QFont) -> None:
        """The axes as wide and as high as their texts, worked out here: pyqtgraph measures them while it
        paints and lays the plot out again after, so a chart came on screen with its numbers cut off and then
        moved. `left` are the texts the left axis may show."""
        tick = QFont(font)
        tick.setPixelSize(Type.CAPTION)
        label = QFont(font)
        label.setPixelSize(Type.SMALL)
        fm, lm = QFontMetricsF(tick), QFontMetricsF(label)
        a = self.getAxis("left")
        w = max((fm.horizontalAdvance(t) for t in left), default=0.0) + 6 + 4
        if a.label.isVisible():
            w += lm.height() + 2
        a.setWidth(int(math.ceil(w)))
        b = self.getAxis("bottom")
        h = fm.height() + 6 + 2
        if b.label.isVisible():
            h += lm.height() + 2
        b.setHeight(int(math.ceil(h)))
        if self.colour_bar is not None:
            bar = self.colour_bar.axis
            ticks = [bar.tickStrings([v], 1, 1)[0] for v in self.colour_bar.values]
            bar.setWidth(int(math.ceil(max(fm.horizontalAdvance(t) for t in ticks) + 4 + 4 + lm.height() + 2)))
        self.getPlotItem().layout.activate()
        self.legend_box.grid.activate()                     # the entries side by side now, not at the next turn

    def show_legend(self, entries: list[Entry]) -> None:
        if not entries:
            return
        for e in entries:
            self.legend_box.add(e)
        pi = self.getPlotItem()
        pi.layout.addItem(self.legend_box, 4, 1)
        pi.layout.setAlignment(self.legend_box, Qt.AlignmentFlag.AlignLeft)
        self.legend_box.show()

    def show_readout(self, text: str) -> None:
        """The value under the pointer, over the left edge of the plotted area."""
        if not text:
            self.readout.hide()
            return
        self.readout.setText(text)
        self.readout.adjustSize()
        top_left = self.mapFromScene(self.view.sceneBoundingRect().topLeft())
        self.readout.move(max(0, top_left.x()), max(0, top_left.y() - self.readout.height() - 2))
        self.readout.show()

    # the pointer and the wheel

    def wheelEvent(self, ev):
        if not self.view.zoomable:
            ev.ignore()                                     # the page under the chart scrolls
            return
        delta = ev.angleDelta().y() or ev.angleDelta().x()
        if not delta:
            ev.ignore()
            return
        centre = self.view.mapSceneToView(self.mapToScene(ev.position().toPoint()))
        self.view.zoom_x(1.02 ** (delta * self.view.state["wheelScaleFactor"]), centre.x())
        ev.accept()

    def mouseDoubleClickEvent(self, ev):
        """Everything again, on the plotted area of a chart that zooms. Here and not in the view: Qt 6 sends a
        press before the double click, and pyqtgraph's scene hands its items the press only."""
        inside = self.view.sceneBoundingRect().contains(self.mapToScene(ev.position().toPoint()))
        if self.view.zoomable and inside and ev.button() == Qt.MouseButton.LeftButton:
            self.view.show_all()
            ev.accept()
            return
        super().mouseDoubleClickEvent(ev)

    def leaveEvent(self, ev):
        super().leaveEvent(ev)
        self._left()

    def contextMenuEvent(self, ev):
        self._menu().exec(ev.globalPos())
        ev.accept()


def colour_map(colours: list[str]):
    return pg.ColorMap(pos=np.linspace(0.0, 1.0, len(colours)), color=[QColor(h) for h in colours])


class _Strip(pg.GraphicsWidget):
    """The colours of a scale, the lowest value at the bottom."""

    def __init__(self, cmap, width: int):
        super().__init__()
        self.cmap = cmap
        self.setMinimumWidth(width)
        self.setMaximumWidth(width)

    def paint(self, painter, _option, _widget=None) -> None:
        r = self.boundingRect()
        gradient = QLinearGradient(r.bottomLeft(), r.topLeft())
        positions, colours = self.cmap.getStops(mode=pg.ColorMap.QCOLOR)
        for at, colour in zip(positions, colours, strict=True):
            gradient.setColorAt(float(at), colour)
        painter.fillRect(r, gradient)


class ColourScale(pg.GraphicsWidget):
    """The scale of a heat map: its colours and the values beside them, in the plot's layout where pyqtgraph's
    ColorBarItem stood. Drawn here: ColorBarItem is a whole plot, with a view, menus and four axes of its own, and
    it cost 37 ms of the first heat map of a page (R120, 25/10/2026)."""

    def __init__(self, cmap, lo: float, hi: float, width: int = 12):
        super().__init__()
        self.values = (lo, hi)
        self.axis = pg.AxisItem("right")
        self.axis.setRange(lo, hi)
        row = QGraphicsLinearLayout(Qt.Orientation.Horizontal)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addItem(_Strip(cmap, width))
        row.addItem(self.axis)
        self.setLayout(row)


def colour_bar(plot: Plot, image, cmap, lo: float, hi: float, unit: str, fmt: Callable[[float], str], c: dict,
               font: QFont):
    """The scale of a heat map, at the right of the plotted area, in the theme's ink, without a frame (the image's
    colours and levels are set by the chart)."""
    bar = ColourScale(cmap, lo, hi)
    layout = plot.getPlotItem().layout
    layout.addItem(bar, 2, 5)                               # as ColorBarItem placed itself: beside the view
    layout.setColumnFixedWidth(4, 5)
    small = QFont(font)
    small.setPixelSize(Type.CAPTION)
    a = bar.axis
    a.setPen(pg.mkPen(None))
    a.setTextPen(c["muted"])
    a.setStyle(tickLength=0, tickTextOffset=4, tickFont=small)
    a.enableAutoSIPrefix(False)
    a.tickStrings = lambda values, _scale, _spacing: [fmt(v) for v in values]
    a.setLabel(unit, color=c["ink2"], **{"font-size": f"{Type.SMALL}px", "font-family": font.family()})
    plot.colour_bar = bar
    return bar


def hover_box(pen_colour: str) -> QGraphicsRectItem:
    item = QGraphicsRectItem()
    item.setPen(pg.mkPen(pen_colour, width=1.5))
    item.setBrush(pg.mkBrush(None))
    item.setZValue(20)
    item.hide()
    return item


def export(plot: Plot, path: str, kind: str, title: str = "", width: int = 1600) -> bool:
    """The plot item as an SVG (vector) or a PNG `width` px wide, on the plot's background: the scene drawn by
    Qt into the file, as on screen. pyqtgraph's own SVGExporter fails on the paths Qt 6.12 closes with a «Z»
    (ValueError in correctCoordinates, on a bare PlotWidget too, 24/10/2026); its ImageExporter scaled the
    text glyph by glyph. True when the file was written."""
    item = plot.getPlotItem()
    item.layout.activate()                              # the title just set takes its row
    source = item.sceneBoundingRect()
    target = QRectF(0, 0, source.width(), source.height())
    if kind == "svg":
        from PySide6.QtSvg import QSvgGenerator
        device = QSvgGenerator()
        device.setFileName(path)
        device.setSize(target.size().toSize())
        device.setViewBox(target)
        device.setTitle(title)
        # at the resolution pyqtgraph's pictures are recorded at (the axes, the bars): at the generator's own 72
        # dpi Qt replays them shrunk to 0,75 of their size, away from what they measure
        device.setResolution(QPicture().logicalDpiX())
    else:
        # drawn at the chart's size on an image of more pixels (its pixel ratio): the text is laid out as on
        # screen and drawn sharp, where scaling the drawing spaced the letters unevenly
        ratio = width / max(source.width(), 1.0)
        device = QImage(width, round(source.height() * ratio), QImage.Format.Format_ARGB32)
        device.setDevicePixelRatio(ratio)
    p = QPainter(device)
    if not p.isActive():                                # a folder that cannot be written
        return False
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    p.fillRect(target, plot.backgroundBrush())
    item.scene().render(p, target, source)
    p.end()
    return True if kind == "svg" else device.save(path, "PNG")
