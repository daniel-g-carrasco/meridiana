"""Charts for the energy pages: pyqtgraph in a Qt widget (study 17, D2, decided by Daniel on 23/10/2026), drawn
to one set of rules so that every chart reads the same way (the data-visualisation method Meridiana follows):
- colour by the job: one hue for one series, the categorical slots in their fixed order for series that
  are told apart, blue against red for gains and losses, a light-to-dark blue for magnitude;
- the palette validated for colour-blind readers in its light and its dark steps, the dark ones chosen
  when the window is dark; surface, grid and axes from the theme's `chart` tokens, text in the window's font (Inter);
- thin marks, hairline solid grid, no second y-axis, a legend from two series up, text in ink colours,
  never in the series' colour;
- every chart has its table: the same numbers, one click away.

What the pointer can do, in the order of the interface design (docs/design/interfaccia.md, 5.2):
1. the value under the pointer, with every series, in the margin over the plotted area (a vertical line on
   the lines, the bar or the cell outlined);
2. a click on an entry of the legend turns its series off and on;
3. the hourly and weekly series (a line of more than LONG points) zoom on x: the wheel, a band dragged
   across, a double click to see everything; the y-axis keeps the range of the data;
4. the context menu saves the chart as SVG or PNG, in the light theme and with its title.

The PDF report draws its own figures with matplotlib (ui/report.py) from the same colours."""

from __future__ import annotations

import functools
import threading
import time
import weakref
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import shiboken6
from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel, QMenu, QMessageBox, QStackedWidget,
                               QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)

from ..i18n import _, number
from .design import Type

SERIES = {"light": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
          "dark": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"]}
SEQUENTIAL = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf",
              "#1c5cab", "#184f95", "#104281", "#0d366b"]
CHROME = {"light": {"surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
                    "grid": "#e1e0d9", "axis": "#c3c2b7", "neutral": "#f0efec"},
          "dark": {"surface": "#1a1a19", "ink": "#f0efec", "ink2": "#c3c2b7", "muted": "#898781",
                   "grid": "#2c2c2a", "axis": "#383835", "neutral": "#383835"}}
LONG = 100                      # a line of more points is an hourly or weekly series: clipped to the view, it zooms
DENSE = 400                     # a line of more points is drawn 1 px wide: 2 px with antialiasing cost 331 ms on
                                # 8.760 points, 1 px 3 ms (offscreen, 24/10/2026)
_FAMILY = [""]                  # the window's font for the charts (Inter), given by set_theme
_BACKEND: list = []             # ui.charts_pg once loaded (pyqtgraph, 0,35 s: at the first chart drawn)
_LOADING: list = []             # the thread loading it (preload), while it runs
_LOCK = threading.Lock()


def backend():
    """pyqtgraph behind the charts (charts_pg), loaded at the first drawing."""
    with _LOCK:
        if not _BACKEND:
            from . import charts_pg
            _BACKEND.append(charts_pg)
        return _BACKEND[0]


def preload() -> None:
    """pyqtgraph loaded in a thread of its own, when the pages of the energy are about to be seen: their first
    charts wait for it (_draw_next) instead of the window stopping for 0,35 s at the first switch. A second
    later, the figure and the image backend of matplotlib: the formulas of «How it is computed» draw with them
    and the charts no longer load them (0,16 s more at the first opening of that tab, 997 against 835 ms);
    loaded at once, they held up the page opened right after (Consumption 91 -> 145 ms, offscreen)."""
    if _BACKEND or _LOADING:
        return

    def load():
        try:
            backend()
        finally:
            _LOADING.clear()
        time.sleep(1.0)
        import matplotlib.backends.backend_agg  # noqa: F401
        import matplotlib.figure  # noqa: F401
        import matplotlib.mathtext  # noqa: F401
    thread = threading.Thread(target=load, name="charts-preload", daemon=True)
    _LOADING.append(thread)
    thread.start()


LIVE: "weakref.WeakSet[Chart]" = weakref.WeakSet()       # every chart made, to draw again in a new theme


def set_theme(t: dict, dark: bool, family: str = "") -> None:
    """Surface, grid, axes and ink of the charts from the theme's tokens (the series and the sequential blue do not
    change, study 13, 3.2); every chart is drawn again, now if it is on screen, at its next show if not."""
    m = "dark" if dark else "light"
    chart = t.get("chart", {})
    CHROME[m] = {"surface": chart.get("surface", t["view"]), "ink": t["text"], "ink2": t["text2"], "muted": t["muted"],
                 "grid": chart.get("grid", t["line_soft"]), "axis": chart.get("axis", t["line"]),
                 "neutral": t["line_soft"]}
    if family:
        _FAMILY[0] = family
    for c in list(LIVE):
        if shiboken6.isValid(c):
            c.redraw()
        else:                       # a chart of a window already deleted, whose Python side lives on
            LIVE.discard(c)


# The charts shown with a drawing waiting are drawn one at a time, each at a turn of the event loop: the page
# comes on screen at once and its charts follow (task 18c, step 10).
_QUEUE: list = []


def _enqueue(chart) -> None:
    if chart not in _QUEUE:
        _QUEUE.append(chart)
        if len(_QUEUE) == 1:
            QTimer.singleShot(0, _draw_next)


def _draw_next() -> None:
    if _LOADING:                    # pyqtgraph still loading in its thread: the charts a moment later
        QTimer.singleShot(30, _draw_next)
        return
    while _QUEUE:
        chart = _QUEUE.pop(0)
        if shiboken6.isValid(chart) and chart.pending is not None and chart.isVisible():
            method, args, kwargs = chart.pending
            chart.pending = None
            method(chart, *args, **kwargs)
            break
    if _QUEUE:
        QTimer.singleShot(0, _draw_next)


def mode() -> str:
    app = QApplication.instance()
    if app is None:
        return "light"
    return "dark" if app.palette().window().color().lightness() < 128 else "light"


@dataclass
class Table:
    columns: list[str]
    rows: list[list]


def _fmt(v, decimals=0) -> str:
    if isinstance(v, str):
        return v
    try:
        return number(float(v), decimals, grouping=True)
    except (TypeError, ValueError):
        return str(v)


def _xfmt(x) -> str:
    """A value of x as the readout writes it: whole numbers without decimals, the others with one."""
    try:
        f = float(x)
    except (TypeError, ValueError):
        return str(x)
    return _fmt(f, 0 if f.is_integer() else 1)


def when_shown(method):
    """A chart is built when it is on screen. Hidden (another tab, another page), the last request waits and
    runs at the next show: a computation that comes back redrew some twenty charts nobody was looking at,
    1.5-2 s with the window frozen (measured on 22/10/2026)."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        self.last = (method, args, kwargs)
        if self.isVisible():
            self.pending = None
            return method(self, *args, **kwargs)
        self.pending = (method, args, kwargs)
        return None
    return wrapper


class Chart(QWidget):
    """A titled chart with its table one click away."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        # pyqtgraph's widget is made at the first drawing (backend()): until then a plain widget holds the
        # place, so that a window with its energy pages hidden loads no pyqtgraph
        self.plot = None
        self.canvas: QWidget = QWidget()
        self.canvas.setMinimumHeight(160)
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.note = QLabel()            # the message, when there is nothing to draw
        self.note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.note.setWordWrap(True)
        self.note.setMinimumHeight(160)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.canvas)
        self.stack.addWidget(self.table)
        self.stack.addWidget(self.note)
        self.name = title
        from .design import Text, set_text
        self.title = set_text(QLabel(title), Text.STRONG)
        self.toggle = QToolButton()
        self.toggle.setObjectName("filter")          # a chip of the global sheet (Button.CHIP)
        self.toggle.setText(_("Table"))
        self.toggle.setCheckable(True)
        self.toggle.setToolTip(_("The same numbers as a table"))
        self.toggle.toggled.connect(self._toggled)
        head = QHBoxLayout()
        head.addWidget(self.title, 1)
        head.addWidget(self.toggle)
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.addLayout(head)
        box.addWidget(self.stack, 1)
        self.showing = "plot"           # "plot" or "message", under the table when «Table» is on
        self.hidden: set[str] = set()   # the series turned off from the legend, by name, kept across drawings
        self.series: dict[str, list] = {}           # name -> the items that draw it
        self.entries: dict = {}         # name -> its entry in the legend
        self._hover = None              # (x, y) in the data -> the readout, for the drawing on screen
        self._marks: list = []          # what the pointer lights up, hidden when it leaves
        self._mode: str | None = None   # "light" while exporting
        self.numbers: Table | None = None           # what «Table» shows, filled in when it is on
        self._table_filled = False
        self.pending = None             # the chart asked for while hidden (when_shown)
        self.last = None                # the last chart asked for, to draw again in a new theme
        LIVE.add(self)

    def _ensure_plot(self):
        """pyqtgraph's widget, the first time something is drawn."""
        if self.plot is None:
            self.plot = backend().Plot(self._moved, self._left, self.menu)
            placeholder, self.canvas = self.canvas, self.plot
            self.stack.removeWidget(placeholder)
            placeholder.deleteLater()
            self.stack.insertWidget(0, self.canvas)
        return self.plot

    def _toggled(self, on: bool) -> None:
        if on and not self._table_filled:
            self._fill_table()
        self._show(self.showing)

    def _show(self, which: str) -> None:
        self.showing = which
        self.stack.setCurrentIndex(1 if self.toggle.isChecked() else 0 if which == "plot" else 2)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self.pending is not None:
            _enqueue(self)              # drawn at the return to the event loop, one chart a turn

    def redraw(self) -> None:
        """The last chart again (a new theme): now if shown, at the next show if not."""
        if self.last is None:
            return
        method, args, kwargs = self.last
        if self.isVisible():
            self.pending = None
            keep = self._xrange()
            method(self, *args, **kwargs)
            self._set_xrange(keep)
        else:
            self.pending = self.last

    def _xrange(self):
        p = self.plot
        return tuple(p.view.viewRange()[0]) if p is not None and p.view.zoomable else None

    def _set_xrange(self, r) -> None:
        if r is not None and self.plot is not None and self.plot.view.zoomable:
            self.plot.view.setXRange(r[0], r[1], padding=0)

    # theme

    def _font(self) -> QFont:
        app = QApplication.instance()
        font = QFont(_FAMILY[0] or (app.font().family() if app is not None else ""))
        font.setPixelSize(Type.CAPTION)
        return font

    def _begin(self):
        """The plot cleared for a new drawing, in the theme's colours: (plot, chrome, series colours, font)."""
        p = self._ensure_plot()
        m = self._mode or mode()
        c, colours, font = CHROME[m], SERIES[m], self._font()
        p.reset(c, font)
        self.series, self.entries, self._marks, self._hover = {}, {}, [], None
        self._show("plot")
        return p, c, colours, font

    def _unit_label(self, p, unit: str, c: dict, font: QFont) -> None:
        if unit:
            p.getAxis("left").setLabel(unit, color=c["ink2"], **{"font-size": f"{Type.SMALL}px", "font-family": font.family()})

    def _legend(self, p, c, font, named: list[tuple[str, str]]) -> None:
        """The legend, from two series up: (name, colour) in slot order."""
        if len(named) < 2:
            return
        B = backend()
        entries = []
        for name, colour in named:
            e = B.Entry(name, colour, font, c["ink2"], lambda entry: self.set_series(entry.name, not entry.on))
            e.set_on(name not in self.hidden)
            self.entries[name] = e
            entries.append(e)
        p.show_legend(entries)

    def _add_series(self, p, name: str, items: list) -> None:
        for item in items:
            p.addItem(item)
            item.setVisible(name not in self.hidden)
        self.series.setdefault(name, []).extend(items)

    def set_series(self, name: str, on: bool) -> None:
        """A series turned on or off (the click on its entry in the legend), dimmed in the legend when off."""
        if on:
            self.hidden.discard(name)
        else:
            self.hidden.add(name)
        for item in self.series.get(name, []):
            item.setVisible(on)
        if name in self.entries:
            self.entries[name].set_on(on)
        self._left()

    def _mark(self, item):
        """Something the pointer lights up, hidden until then and when it leaves."""
        item.hide()
        self.plot.addItem(item, ignoreBounds=True)
        self._marks.append(item)
        return item

    def _set_table(self, table: Table) -> None:
        """The numbers of the drawing, put in the table when «Table» is on: an hourly year is 8.760 rows, 0,15 s
        of cells nobody may look at."""
        self.numbers = table
        self._table_filled = False
        if self.toggle.isChecked():
            self._fill_table()

    def _fill_table(self) -> None:
        table = self.numbers
        self._table_filled = True
        if table is None:
            return
        self.table.clear()
        self.table.setColumnCount(len(table.columns))
        self.table.setRowCount(len(table.rows))
        self.table.setHorizontalHeaderLabels(table.columns)
        for i, row in enumerate(table.rows):
            for j, v in enumerate(row):
                item = QTableWidgetItem(v if isinstance(v, str) else _fmt(v, 1 if abs(float(v)) < 100 else 0))
                if not isinstance(v, str):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i, j, item)
        self.table.resizeColumnsToContents()

    # forms

    @when_shown
    def bars(self, categories: list[str], series: list[tuple[str, list[float]]], unit: str, stacked: bool = False,
             decimals: int = 0) -> None:
        """Columns by category: one series in slot 1, several side by side or stacked, in slot order."""
        p, c, colours, font = self._begin()
        pg = backend().pg
        n, k = len(categories), len(series)
        xs = np.arange(n, dtype=float)
        width = 0.7 if stacked or k == 1 else 0.8 / max(k, 1)
        bottom = np.zeros(n)
        lo = hi = 0.0
        shapes = []                     # per series: x, bottom, height, width of its bars
        for s, (label, values) in enumerate(series):
            v = np.asarray(values, dtype=float)
            if stacked:
                x, w, y0 = xs, width, bottom.copy()
                bottom = bottom + v
                pen = pg.mkPen(c["surface"], width=1.5)
            else:
                x, w, y0 = xs - 0.4 + width * (s + 0.5), width * 0.92, np.zeros(n)
                pen = pg.mkPen(None)
            self._add_series(p, label, [pg.BarGraphItem(x=x, y0=y0, height=v, width=w, brush=colours[s % 8], pen=pen)])
            shapes.append((label, x, y0, v, w))
            if n:
                lo, hi = min(lo, float(np.min(y0 + np.minimum(v, 0)))), max(hi, float(np.max(y0 + np.maximum(v, 0))))
        top = (hi * 1.05) if hi > lo else lo + 1
        p.view.setRange(xRange=(-0.6, max(n, 1) - 0.4), yRange=(lo, top), padding=0)
        p.getAxis("bottom").setTicks([[(i, cat) for i, cat in enumerate(categories)]])
        p.getAxis("left").fmt = lambda v: _fmt(v, decimals)
        self._unit_label(p, unit, c, font)
        p.grid(y=True)
        self._legend(p, c, font, [(label, colours[s % 8]) for s, (label, _v) in enumerate(series)])
        p.fit([_fmt(lo, decimals), _fmt(top, decimals)], font)
        outline = self._mark(pg.BarGraphItem(x=[0.0], height=[0.0], width=0.1, brush=None,
                                             pen=pg.mkPen(c["ink"], width=1.5)))

        def hover(x, _y):
            j = int(round(x))
            if not 0 <= j < n:
                return ""
            shown = [sh for sh in shapes if sh[0] not in self.hidden]
            if not shown:
                return ""
            outline.setOpts(x=[float(sh[1][j]) for sh in shown],
                            y0=[float(sh[2][j]) for sh in shown], height=[float(sh[3][j]) for sh in shown],
                            width=[float(sh[4]) for sh in shown])
            outline.show()
            if k == 1:
                return f"{categories[j]}: {_fmt(shown[0][3][j], decimals)} {unit}"
            parts = [f"{sh[0]} {_fmt(sh[3][j], decimals)} {unit}" for sh in shown]
            if stacked and len(shown) > 1:
                parts.append(_("total {value}").format(value=f"{_fmt(sum(sh[3][j] for sh in shown), decimals)} {unit}"))
            return f"{categories[j]}: " + " · ".join(parts)
        self._hover = hover
        self._set_table(Table([""] + [s[0] for s in series],
                              [[cat] + [s[1][i] for s in series] for i, cat in enumerate(categories)]))

    @when_shown
    def changes(self, labels: list[str], values: list[float], unit: str = "%") -> None:
        """Horizontal bars round zero: gains in blue, losses in red (the diverging pair), the value at the tip."""
        p, c, colours, font = self._begin()
        pg = backend().pg
        n = len(labels)
        v = np.asarray(values, dtype=float)
        ys = np.arange(n, dtype=float)[::-1]           # the first step on top
        blue, red = colours[0], colours[7]
        if n:
            p.addItem(pg.BarGraphItem(x0=np.minimum(v, 0.0), x1=np.maximum(v, 0.0), y=ys, height=0.6,
                                      brushes=[blue if x >= 0 else red for x in v], pen=pg.mkPen(None)))
        p.addItem(pg.InfiniteLine(pos=0.0, angle=90, pen=pg.mkPen(c["axis"], width=1)), ignoreBounds=True)
        span = float(np.max(np.abs(v))) if n else 1.0
        span = span or 1.0
        small = QFont(font)
        small.setPixelSize(Type.CAPTION)
        for x, y in zip(v, ys, strict=True):
            t = pg.TextItem(f"{_fmt(x, 1)}{unit}", color=c["ink2"], anchor=(0, 0.5) if x >= 0 else (1, 0.5))
            t.setFont(small)
            t.setPos(x + (0.02 * span if x >= 0 else -0.02 * span), y)
            p.addItem(t, ignoreBounds=True)
        lo, hi = min(0.0, float(v.min()) if n else 0.0), max(0.0, float(v.max()) if n else 0.0)
        room = 0.2 * max(hi - lo, 0.1)            # for the values at the tips, on both sides
        p.view.setRange(xRange=(lo - room if lo < 0 else -0.05 * room, hi + room if hi > 0 else 0.05 * room),
                        yRange=(-0.6, max(n, 1) - 0.4), padding=0)
        left = p.getAxis("left")
        left.setTicks([[(float(y), lab) for y, lab in zip(ys, labels, strict=True)]])
        left.setTextPen(c["ink2"])
        p.getAxis("bottom").fmt = lambda x: f"{_fmt(x, 0)}{unit}"
        p.grid(x=True)
        p.fit(labels, font)
        box = self._mark(backend().hover_box(c["ink"]))

        def hover(_x, y):
            i = n - 1 - int(round(y))
            if not 0 <= i < n:
                return ""
            box.setRect(QRectF(min(0.0, v[i]), ys[i] - 0.3, abs(v[i]), 0.6))
            box.show()
            return f"{labels[i]}: {_fmt(v[i], 2)}{unit}"
        self._hover = hover
        self._set_table(Table([_("Step"), unit], [[lab, x] for lab, x in zip(labels, values, strict=True)]))

    @when_shown
    def heatmap(self, matrix, rows: list[str], cols: list[str], unit: str, decimals: int = 1,
                ticks: list | None = None, row_ticks: list | None = None) -> None:
        """A grid of magnitudes, light to dark blue, with its scale; `ticks` and `row_ticks` the (index, label) of
        the axes when not every column or row is to be named (the days of a year: the months)."""
        p, c, _colours, font = self._begin()
        B = backend()
        pg = B.pg
        m = np.asarray(matrix, dtype=float)
        nr, nc = m.shape
        image = pg.ImageItem(m)
        image.setRect(QRectF(-0.5, -0.5, nc, nr))
        lo, hi = float(np.nanmin(m)), float(np.nanmax(m))
        hi = hi if hi > lo else lo + 1.0
        cmap = B.colour_map(SEQUENTIAL)
        image.setColorMap(cmap)
        image.setLevels((lo, hi))
        p.addItem(image)
        p.view.invertY(True)                           # January on top
        p.view.setRange(xRange=(-0.5, nc - 0.5), yRange=(-0.5, nr - 0.5), padding=0)
        p.getAxis("left").setTicks([row_ticks if row_ticks is not None else [(i, r) for i, r in enumerate(rows)]])
        step = max(1, len(cols) // 12)
        p.getAxis("bottom").setTicks([ticks if ticks is not None else
                                      [(j, cols[j]) for j in range(0, len(cols), step)]])
        p.getAxis("bottom").setPen(pg.mkPen(None))
        B.colour_bar(p, image, cmap, lo, hi, unit, lambda x: _fmt(x, decimals), c, font)
        p.fit(rows, font)
        box = self._mark(B.hover_box(c["ink"]))

        def hover(x, y):
            i, j = int(round(y)), int(round(x))
            if not (0 <= i < nr and 0 <= j < nc):
                return ""
            box.setRect(QRectF(j - 0.5, i - 0.5, 1.0, 1.0))
            box.show()
            return f"{rows[i]}, {cols[j]}: {_fmt(m[i, j], decimals)} {unit}"
        self._hover = hover
        self._set_table(Table([""] + list(cols), [[r] + [float(x) for x in m[i]] for i, r in enumerate(rows)]))

    @when_shown
    def line(self, xs: list, series: list[tuple[str, list[float]]], unit: str, xlabel: str = "", decimals: int = 0,
             area: bool = True, mark_zero: bool = True, mark: tuple[float, str] | None = None,
             markers: bool = False, ticks: list | None = None, names: list[str] | None = None) -> None:
        """Lines over x; `mark` draws a thin vertical line at a value of x with its label (the design as it
        is, among the alternatives); `markers` puts a dot on every point when the points are few; `names`
        are what each x is called in the readout and in the table («Mon 12:00»)."""
        p, c, colours, font = self._begin()
        pg = backend().pg
        x = np.asarray(xs, dtype=float)
        long = len(x) > LONG
        values = [np.asarray(v, dtype=float) for _label, v in series]
        for k, (label, _v) in enumerate(series):
            col = colours[k % 8]
            opts = {"pen": pg.mkPen(col, width=1 if len(x) > DENSE else 2)}
            if markers:
                opts.update(symbol="o", symbolSize=7, symbolBrush=col, symbolPen=pg.mkPen(c["surface"], width=1.5))
            if area and len(series) == 1 and len(x) <= DENSE:     # filled under 8.760 points: 30-90 ms
                opts.update(fillLevel=0.0, fillBrush=pg.mkBrush(backend().colour(col, 26)))
            item = pg.PlotDataItem(x, values[k], **opts)
            self._add_series(p, label, [item])
            if long:                # once in the view: set before, pyqtgraph 0.14 asks the widget for the view's range
                item.setClipToView(True)
                item.setDownsampling(auto=True, method="peak")
        x0, x1 = (float(x.min()), float(x.max())) if len(x) else (0.0, 1.0)
        if x1 <= x0:
            x1 = x0 + 1.0
        pad = 0.0 if long else 0.03 * (x1 - x0)
        ys = np.concatenate(values) if values and len(x) else np.zeros(1)
        lo, hi = float(np.nanmin(ys)), float(np.nanmax(ys))
        if mark_zero or area:
            lo, hi = min(lo, 0.0), max(hi, 0.0)
        room = 0.06 * ((hi - lo) or 1.0)
        top = hi + room
        p.view.setRange(xRange=(x0 - pad, x1 + pad), yRange=(lo - (room if lo < 0 else 0.0), top), padding=0)
        if long:
            p.view.set_zoomable(True, (x0, x1))
        if mark_zero:
            p.addItem(pg.InfiniteLine(pos=0.0, angle=0, pen=pg.mkPen(c["axis"], width=1)), ignoreBounds=True)
        if mark is not None:
            p.addItem(pg.InfiniteLine(pos=float(mark[0]), angle=90,
                                      pen=pg.mkPen(c["ink2"], width=1, style=Qt.PenStyle.DashLine)), ignoreBounds=True)
            t = pg.TextItem(mark[1], color=c["ink2"], anchor=(-0.05, 0.0))
            small = QFont(font)
            small.setPixelSize(Type.CAPTION)
            t.setFont(small)
            t.setPos(float(mark[0]), top)
            p.addItem(t, ignoreBounds=True)
        bottom = p.getAxis("bottom")
        if xlabel:
            bottom.setLabel(xlabel, color=c["ink2"], **{"font-size": f"{Type.SMALL}px", "font-family": font.family()})
        if ticks:
            bottom.setTicks([[(float(t[0]), t[1]) for t in ticks]])
        else:
            bottom.fmt = _xfmt
        p.getAxis("left").fmt = lambda v: _fmt(v, decimals)
        self._unit_label(p, unit, c, font)
        p.grid(y=True)
        self._legend(p, c, font, [(label, colours[k % 8]) for k, (label, _v) in enumerate(series)])
        p.fit([_fmt(lo, decimals), _fmt(top, decimals)], font)
        cross = self._mark(pg.InfiniteLine(angle=90, pen=pg.mkPen(c["ink2"], width=1, style=Qt.PenStyle.DashLine)))
        dots = self._mark(pg.ScatterPlotItem(size=8, pen=pg.mkPen(c["surface"], width=1.5)))
        cross.setZValue(30)
        dots.setZValue(31)

        def called(j: int) -> str:
            if names is not None:
                return names[j]
            return f"{xlabel} {_xfmt(xs[j])}" if xlabel else _xfmt(xs[j])

        def hover(at, _y):
            if not len(x):
                return ""
            j = int(np.clip(np.searchsorted(x, at), 1, len(x) - 1))
            j = j - 1 if abs(at - x[j - 1]) <= abs(x[j] - at) else j
            shown = [k for k, (label, _v) in enumerate(series) if label not in self.hidden]
            cross.setPos(float(x[j]))
            cross.show()
            dots.setData([{"pos": (float(x[j]), float(values[k][j])), "brush": colours[k % 8]} for k in shown])
            dots.show()
            if not shown:
                return called(j)
            if len(series) == 1:
                return f"{called(j)}: {_fmt(values[0][j], decimals)} {unit}"
            return f"{called(j)}: " + " · ".join(f"{series[k][0]} {_fmt(values[k][j], decimals)} {unit}" for k in shown)
        self._hover = hover
        self._set_table(Table([xlabel or ""] + [s[0] for s in series],
                              [[names[i] if names is not None else str(xv)] + [s[1][i] for s in series]
                               for i, xv in enumerate(xs)]))

    @when_shown
    def message(self, text: str) -> None:
        """Words instead of a chart, when there is nothing to draw (no pyqtgraph needed for them)."""
        c = CHROME[mode()]
        self.note.setText(text)
        self.note.setStyleSheet(f"color: {c['ink2']}; background: {c['surface']}; padding: 12px;")
        self._hover = None
        self._show("message")
        self._set_table(Table([""], [[text]]))

    # the pointer

    def _moved(self, args) -> None:
        """The pointer over the plot (60 times a second at most, through the SignalProxy)."""
        p = self.plot
        if p is None or self._hover is None or not shiboken6.isValid(p):    # a move late on a chart deleted
            return
        pos = args[0]
        if not p.view.sceneBoundingRect().contains(pos):
            self._left()
            return
        at = p.view.mapSceneToView(pos)
        for m in self._marks:
            m.hide()
        p.show_readout(self._hover(at.x(), at.y()))

    def _left(self) -> None:
        if self.plot is not None and not shiboken6.isValid(self.plot):
            return
        for m in self._marks:
            m.hide()
        if self.plot is not None:
            self.plot.show_readout("")

    # the context menu and the exports

    def menu(self) -> QMenu:
        m = QMenu(self)
        m.addAction(_("Save as SVG…")).triggered.connect(lambda: self._save("svg"))
        m.addAction(_("Save as PNG…")).triggered.connect(lambda: self._save("png"))
        if self.plot is not None and self.plot.view.zoomable:
            m.addSeparator()
            m.addAction(_("Frame it")).triggered.connect(self.plot.view.show_all)
        return m

    def _save(self, kind: str) -> None:
        stem = "".join(ch if ch.isalnum() or ch in " -_" else " " for ch in self.name).strip() or "chart"
        pattern = _("SVG images (*.svg)") if kind == "svg" else _("PNG images (*.png)")
        path, _f = QFileDialog.getSaveFileName(self, _("Save the chart"), f"{stem}.{kind}", pattern)
        if path and not self.export(path, kind):
            QMessageBox.warning(self, _("Save the chart"), _("The chart could not be written to {path}.").format(path=path))

    def export(self, path: str, kind: str = "svg") -> bool:
        """The chart as it is drawn (its series on and off, its zoom) in the light theme and with its title, to
        an SVG or a PNG file, whatever the theme of the window; True when the file is there."""
        if self.last is None or self.plot is None or self.showing != "plot":
            return False
        method, args, kwargs = self.last
        keep = self._xrange()
        self._mode = "light"
        try:
            method(self, *args, **kwargs)
            self._set_xrange(keep)
            self.plot.getPlotItem().setTitle(self.name, color=CHROME["light"]["ink"], size="11pt", bold=True)
            written = backend().export(self.plot, path, kind, self.name)
        finally:
            self._mode = None
            method(self, *args, **kwargs)
            self._set_xrange(keep)
        return written and Path(path).is_file()

