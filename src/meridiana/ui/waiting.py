"""Waits made visible (study 16, theme F; Daniel's choices of 23/10/2026; design document 3.12): nothing under
THRESHOLD_MS; past it an arc that turns in the area that waits (the plan while the modules are laid, the energy pages
while the year is computed, the catalogue while it is first read), with the words in the status bar; a bar with its
percentage and Cancel only for PVGIS and the PDF report (ui/window.py); the values of the last computation kept in
sight, greyed, with a mark on the title of their phase; the 3D view's skeleton only at the start; never a modal
window; everything still when the system asks for less motion.

- `Spinner`: the arc, 24 or 48 px, in the text's colour over a faint ring; still (one frame) with less motion.
- `Delayed`: shows a widget once a wait has lasted the threshold, hides it as soon as the wait ends.
- `pin`: keeps a widget in a corner of another (the arc over a page that scrolls).
- `set_stale`: a value greyed in the theme's muted text, as one to update.
- `Skeleton3D`: the sky, the ground and the buildings over the 3D view until its first frame."""

from __future__ import annotations

from PySide6.QtCore import QElapsedTimer, QEvent, QObject, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPalette, QPen, QPolygonF
from PySide6.QtWidgets import QApplication, QWidget

from .. import log, mesh, theme_colors, view_colours
from .design import Radius

THRESHOLD_MS = 300          # nothing under it (study 16, F.6: Material 200 ms, RAIL 100 ms, Nielsen 1 s)
FRAME_MS = 16               # 60 frames a second: 0,12 ms each over a plan of 5.000 modules (16-prove/attese.py)
TURN_MS = 1200              # one turn of the arc
SKELETON_LIMIT_MS = 3000    # the 3D's skeleton goes after this whatever happens, and the log says why
STALE_MARK = " ·"           # after the title of a phase whose values are to update («Production ·»)


def _colour(value) -> QColor:
    return QColor(theme_colors.qt_hex(value)) if isinstance(value, str) else QColor(value)


def less_motion() -> bool:
    """Whether the system asks for less motion (Windows' animation effects off, the portal's reduced-motion)."""
    app = QApplication.instance()
    if app is None:
        return False
    from .theme import SystemAccent
    return SystemAccent.of(app).reduced_motion


class Spinner(QWidget):
    """The arc that turns where something is awaited: a quarter and a bit of a ring, in the text's colour (or
    the colours given: the plan has its own), on a faint ring; with `backdrop`, on a rounded chip as the plan's
    north arrow. With less motion it does not turn: one frame, still. `frames` counts what was painted (the
    tests)."""

    def __init__(self, parent=None, size: int = 24, backdrop: bool = False, tip: str = ""):
        super().__init__(parent)
        self.side = size
        self.backdrop = backdrop
        pad = 6 if backdrop else 0
        self.setFixedSize(size + 2 * pad, size + 2 * pad)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, not tip)
        if tip:
            self.setToolTip(tip)
        self.colours: dict = {}                     # "arc", "ring", "chip": QColor; empty, the palette's
        self.reduced_motion = less_motion()
        self.frames = 0
        self.clock = QElapsedTimer()
        self.timer = QTimer(self, interval=FRAME_MS)
        self.timer.timeout.connect(self.update)
        self.hide()
        app = QApplication.instance()
        if app is not None:
            from .theme import SystemAccent
            SystemAccent.of(app).motion.connect(self._motion)

    def set_colours(self, arc=None, ring=None, chip=None) -> None:
        """Colours of its own ("#rrggbb" or "#rrggbbaa" as the tokens write them, or QColor; None: the palette's
        accent, a faint ring, the plan's chip)."""
        self.colours = {k: _colour(v) for k, v in (("arc", arc), ("ring", ring), ("chip", chip)) if v is not None}
        self.update()

    def start(self) -> None:
        self.frames = 0
        self.clock.start()
        self.show()
        self.raise_()
        if not self.reduced_motion:
            self.timer.start()

    def stop(self) -> None:
        self.timer.stop()
        self.hide()

    def turning(self) -> bool:
        return self.timer.isActive()

    def _motion(self, reduced: bool) -> None:
        self.reduced_motion = reduced
        if reduced:
            self.timer.stop()
        elif self.isVisible():
            self.timer.start()
        self.update()

    def angle(self) -> float:
        """Degrees, clockwise from twelve o'clock: from the time elapsed, so that a late frame does not slow it."""
        if self.reduced_motion or not self.clock.isValid():
            return 0.0
        return (self.clock.elapsed() % TURN_MS) * 360.0 / TURN_MS

    def paintEvent(self, _event) -> None:
        self.frames += 1
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        if self.backdrop:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self.colours.get("chip", _colour(view_colours.PHOTO["label_bg"])))
            p.drawRoundedRect(QRectF(self.rect()), Radius.CONTROL, Radius.CONTROL)
        width = max(2.0, self.side / 10)
        inset = (self.width() - self.side) / 2 + width / 2 + 1
        box = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
        arc = self.colours.get("arc", pal.color(QPalette.ColorRole.Text))       # not the accent (R104)
        ring = self.colours.get("ring")
        if ring is None:
            ring = QColor(pal.color(QPalette.ColorRole.PlaceholderText))
            ring.setAlphaF(0.25)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(ring, width))
        p.drawEllipse(box)
        pen = QPen(arc, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        # Qt counts sixteenths of a degree, anticlockwise from three o'clock
        p.drawArc(box, int((90 - self.angle()) * 16), int(-110 * 16))
        p.end()


class Delayed(QObject):
    """A wait shown only once it has lasted the threshold: `begin` when it starts (again while waiting changes
    nothing), `end` when it is over, and the widget (a Spinner, started; any other, shown) appears only if the
    end has not come within THRESHOLD_MS. Gone at once at the end."""

    shown = Signal(bool)

    def __init__(self, widget: QWidget, parent: QObject | None = None, threshold: int = THRESHOLD_MS):
        super().__init__(parent if parent is not None else widget)
        self.widget = widget
        self.waiting = False
        self.timer = QTimer(self, singleShot=True, interval=threshold)
        self.timer.timeout.connect(self._show)
        widget.hide()

    def begin(self) -> None:
        if self.waiting:
            return
        self.waiting = True
        self.timer.start()

    def end(self) -> None:
        was = self.waiting and not self.timer.isActive()
        self.waiting = False
        self.timer.stop()
        if isinstance(self.widget, Spinner):
            self.widget.stop()
        else:
            self.widget.hide()
        if was:
            self.shown.emit(False)

    def _show(self) -> None:
        if not self.waiting:
            return
        if isinstance(self.widget, Spinner):
            self.widget.start()
        else:
            self.widget.show()
        self.shown.emit(True)


class _Pin(QObject):
    def __init__(self, widget: QWidget, host: QWidget, margin: int, where: str):
        super().__init__(widget)
        self.widget, self.host, self.margin, self.where = widget, host, margin, where
        host.installEventFilter(self)
        self.place()

    def place(self) -> None:
        inner = getattr(self.host, "viewport", None)
        area = inner().geometry() if callable(inner) else self.host.rect()
        if self.where == "centre":
            self.widget.move(area.center().x() - self.widget.width() // 2,
                             area.center().y() - self.widget.height() // 2)
        else:
            self.widget.move(area.right() + 1 - self.widget.width() - self.margin, area.top() + self.margin)

    def eventFilter(self, obj, event) -> bool:
        if obj is self.host and event.type() in (QEvent.Type.Resize, QEvent.Type.LayoutRequest, QEvent.Type.Show):
            self.place()
        return False


def pin(widget: QWidget, host: QWidget, margin: int = 8, where: str = "top-right") -> None:
    """`widget` (a child of `host`) kept in the top right corner of `host` (or in its middle, "centre"), or of its
    viewport if it has one (a scroll area: the widget stays put while the page under it scrolls)."""
    _Pin(widget, host, margin, where)


class Progress(QWidget):
    """For the long works that know how far they are, and only those (PVGIS and the PDF report; study 16, F4):
    what is being done, the bar with its percentage and Cancel, in the status bar; never a window of its own.
    Shown past the threshold (`begin`), gone at once at the end or at Cancel (`end`)."""

    cancelled = Signal()

    def __init__(self, parent: QWidget | None = None):
        from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QToolButton

        from ..i18n import _
        super().__init__(parent)
        box = QHBoxLayout(self)
        box.setContentsMargins(6, 0, 0, 0)
        box.setSpacing(6)
        self.label = QLabel()
        self.label.setMinimumWidth(1)               # cut, never wider than the window allows (a column of niri)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setFixedWidth(120)
        self.bar.setFormat("%p%")
        self.cancel = QToolButton()
        self.cancel.setAutoRaise(True)
        self.cancel.setText(_("Cancel"))
        self.cancel.clicked.connect(self.cancelled.emit)
        box.addWidget(self.label, 1)
        box.addWidget(self.bar)
        box.addWidget(self.cancel)
        self.wait = Delayed(self, self)

    def begin(self, text: str) -> None:
        self.set(0.0, text)
        self.wait.begin()

    def set(self, fraction: float, text: str = "") -> None:
        if self.bar.maximum() == 0:
            self.bar.setRange(0, 100)
        self.bar.setValue(round(100 * min(1.0, max(0.0, fraction))))
        if text:
            self.label.setText(text)
            self.label.setToolTip(text)

    def unknown(self, text: str = "") -> None:
        """A step that cannot say how far it is (an IFC file being opened, study 20): the bar moves without a
        percentage until the next `set`."""
        self.bar.setRange(0, 0)
        if text:
            self.label.setText(text)
            self.label.setToolTip(text)

    def end(self) -> None:
        self.wait.end()

    def running(self) -> bool:
        return self.wait.waiting


def set_stale(label: QWidget, on: bool) -> None:
    """A value to update: drawn in the theme's muted text (the palette's placeholder text, so both themes have it)
    while the project has changed after it was computed; back to the text's colour when the new one comes. Grey,
    not struck through (Daniel, 23/10/2026)."""
    label.setForegroundRole(QPalette.ColorRole.PlaceholderText if on else QPalette.ColorRole.WindowText)
    label.setProperty("stale", on)
    label.update()


def is_stale(label: QWidget) -> bool:
    return bool(label.property("stale"))


class Skeleton3D(QWidget):
    """What the 3D view shows until its first frame, at the start (study 16, F2; Daniel 23/10/2026: the skeleton
    only there): the view's own sky and ground (view_colours.D3, the same in both themes) and the buildings from the
    plan as simple boxes in an oblique view from the south, outlined in the theme's muted ink. A child of the
    QQuickWidget, as large as it, letting the mouse through; gone at the first frame the scene renders (the first
    afterRendering, or frameSwapped, of its quickWindow), when the graphics fail, or SKELETON_LIMIT_MS after it was
    first shown, said in the log. `gone` tells why: "frame", "time" or "failed"."""

    gone = Signal(str)

    def __init__(self, view: QWidget, limit_ms: int = SKELETON_LIMIT_MS):
        super().__init__(view)
        self.view = view
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.boxes: list = []                       # (outline in metres, height in metres)
        self.ink = QColor("#696257")
        self.why = ""
        self.timer = QTimer(self, singleShot=True, interval=limit_ms)
        self.timer.timeout.connect(lambda: self.done("time"))
        self.quick = view.quickWindow() if hasattr(view, "quickWindow") else None
        if self.quick is not None:
            self.quick.afterRendering.connect(self._frame, Qt.ConnectionType.QueuedConnection)
            self.quick.frameSwapped.connect(self._frame, Qt.ConnectionType.QueuedConnection)
        if hasattr(view, "failed"):
            view.failed.connect(self._failed)
        view.installEventFilter(self)
        self.setGeometry(view.rect())
        self.raise_()

    def set_buildings(self, boxes: list) -> None:
        """(outline, height) of each building, the outline in metres (x East, y North) as the plan draws it."""
        self.boxes = [([(float(x), float(y)) for x, y in ring], float(h)) for ring, h in boxes if len(ring) >= 3]
        self.update()

    def set_colours(self, t: dict) -> None:
        """The theme's tokens: the outlines in its muted ink (the sky and the ground are the view's own)."""
        self.ink = QColor(t.get("muted", "#696257"))
        self.update()

    def eventFilter(self, obj, event) -> bool:
        if obj is self.view and event.type() == QEvent.Type.Resize:
            self.setGeometry(self.view.rect())
        return False

    def showEvent(self, event) -> None:
        super().showEvent(event)
        drawn = getattr(self.view, "drawn", None)
        if not self.why and callable(drawn) and not drawn():
            # no graphics device here (the tests' offscreen platform): no frame will come, nothing to wait for
            self.done("not drawn")
            return
        if not self.why and not self.timer.isActive():
            self.timer.start()

    def _frame(self, *_args) -> None:
        if self.isVisible():
            self.done("frame")

    def _failed(self, *_args) -> None:
        self.done("failed")

    def done(self, why: str) -> None:
        """Gone, for `why`; once."""
        if self.why:
            return
        self.why = why
        self.timer.stop()
        if self.quick is not None:
            self.quick.afterRendering.disconnect(self._frame)
            self.quick.frameSwapped.disconnect(self._frame)
        if hasattr(self.view, "failed"):
            self.view.failed.disconnect(self._failed)
        if why == "time":
            log.complain("3D view", TimeoutError(f"no frame within {self.timer.interval()} ms: its skeleton is taken "
                                                 "away, the view may stay empty until it draws"))
        self.view.removeEventFilter(self)
        self.hide()
        self.gone.emit(why)
        self.deleteLater()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        horizon = h * 0.45
        sky = QLinearGradient(0, 0, 0, horizon)
        sky.setColorAt(0, QColor(view_colours.D3["sky_top"]))
        sky.setColorAt(1, QColor(view_colours.D3["sky_bottom"]))
        p.fillRect(QRectF(0, 0, w, horizon), sky)
        p.fillRect(QRectF(0, horizon, w, h - horizon), QColor(view_colours.D3["ground"]))
        if not self.boxes:
            return
        # an oblique view from the south: East across, North into the picture (squashed), the heights up
        xs = [x for ring, _h in self.boxes for x, _y in ring]
        ys = [y for ring, _h in self.boxes for _x, y in ring]
        top = max(height for _r, height in self.boxes)
        squash = 0.45
        scale = min(w * 0.6 / max(max(xs) - min(xs), 1.0),
                    h * 0.5 / max((max(ys) - min(ys)) * squash + top, 1.0), 40.0)
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        base = horizon + (h - horizon) * 0.55

        def at(x: float, y: float, z: float) -> QPointF:
            return QPointF(w / 2 + (x - cx) * scale, base - (y - cy) * squash * scale - z * scale)

        p.setPen(QPen(self.ink, 1.5))
        wall, roof = QColor.fromRgbF(*mesh.WALL), QColor.fromRgbF(*mesh.ROOF_FLAT)
        for ring, height in sorted(self.boxes, key=lambda b: -min(y for _x, y in b[0])):     # the far ones first
            p.setBrush(wall)
            for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1], strict=True):
                p.drawPolygon(QPolygonF([at(x0, y0, 0), at(x1, y1, 0), at(x1, y1, height), at(x0, y0, height)]))
            p.setBrush(roof)
            p.drawPolygon(QPolygonF([at(x, y, height) for x, y in ring]))
        p.end()
