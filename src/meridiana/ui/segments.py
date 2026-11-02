"""The choice between views (R322, B1; Daniel, 02/11/2026): segments on a track, a rectangle of the control's radius, and
the rectangle of the one chosen sliding to the next, as the tab of the phases slides (ui/phasebar.py, R83, R97): the
same curve, the same duration, started after the work the change asked for, nought with less motion.

Two hosts, one drawing (`paint_track`, `paint_raised`) and one movement (`Slide`):
- `Segments`, a row of `Segment` buttons in a frame: the charts' «Chart | Table», the variants, the views of the Checks.
  Exclusive, one rectangle slides and the arrows move it; not exclusive (`exclusive=False`, a filter that stays pressed
  with the others: the Checks' levels, this phase, this object), each segment on has its rectangle, which comes and goes
  in a fade: there is nowhere for it to slide from.
- `on_bar(tab_bar)`, for a QTabBar that must stay one: a QTabWidget's (the charts' tabs), the bars Qt makes for panels
  put together (R109). The bar keeps its tabs, its keys and its tooltips; the track goes under them from an event
  filter, the tabs transparent in the global sheet (ui/theme.py, `QTabBar::tab`).

The segments are CHIP high, the track 2 px around them, so 28 as a control."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QRectF, QSize, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QSizePolicy, QTabBar, QToolButton

from .. import theme_colors
from . import motion
from .design import Line, Motion, Radius, Size, Space

TRACK_AIR = Space.XXS       # the track around the segments


def tokens() -> dict:
    """The colours of the theme in use (ui/theme.Theme gives them to the shared style)."""
    from .cards import default_tokens
    from .style import shared
    return shared().tokens or default_tokens()


def paint_track(p: QPainter, rect: QRectF, t: dict) -> None:
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(t["field"]))
    p.drawRoundedRect(rect, Radius.CONTROL, Radius.CONTROL)


def paint_raised(p: QPainter, rect: QRectF, t: dict, focused: bool = False) -> None:
    """The rectangle of a segment chosen: on the panels' colour with the line (the accent's with the keyboard on it)."""
    width = Line.FOCUS if focused else Line.HAIR
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(t["accent"] if focused else t["line"]), width))
    p.setBrush(QColor(t["panel"]))
    inset = width / 2
    p.drawRoundedRect(rect.adjusted(inset, inset, -inset, -inset), Radius.INNER, Radius.INNER)


class Slide(QObject):
    """The rectangle of the choice going from where it was painted to where `target()` says, as ui/phasebar.PhaseHeader
    does with the tab of the phases. `move` when the choice has changed, `now` when painting."""

    def __init__(self, host, target):
        super().__init__(host)
        self.host, self.target = host, target
        self.animation = QVariantAnimation(self)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(motion.SLIDE_EASING)
        self.animation.valueChanged.connect(lambda _v: self.host.update())
        self.animation.finished.connect(self._landed)
        self.source: QRectF | None = None           # where it comes from, while held or sliding
        self.shown: QRectF | None = None            # where it was last painted

    def move(self) -> None:
        """The choice has changed: held where it was shown while the window does what the change asks (R97: started
        with the click, its first 50 ms go into the new page's paint and it jumps), then sliding."""
        self.animation.stop()
        held = self.shown is not None and self.host.isVisible() and not motion.reduced()
        self.source = QRectF(self.shown) if held else None
        self.host.update()
        if held:
            motion.after_work(self, self._play)

    def _play(self) -> None:
        if self.source is None or motion.reduced() or self.source == self.target():
            self._landed()
            return
        self.animation.setDuration(Motion.FAST)
        self.animation.start()

    def _landed(self) -> None:
        self.source = None
        self.host.update()

    def now(self) -> QRectF | None:
        """The rectangle as it is to be painted now: held, sliding or at the choice."""
        r = self.target()
        if r is None or self.source is None:
            return r
        if self.animation.state() != QVariantAnimation.State.Running:
            return QRectF(self.source)
        t, a = float(self.animation.currentValue()), self.source
        return QRectF(a.left() + (r.left() - a.left()) * t, r.top(), a.width() + (r.width() - a.width()) * t, r.height())

    def paint(self, p: QPainter, colours: dict, focused: bool = False) -> None:
        r = self.now()
        self.shown = r
        if r is not None:
            paint_raised(p, r, colours, focused)


class Segment(QToolButton):
    """One segment: its word, cut with the dots when the track has no room (its tooltip says it whole); the rectangle
    of the choice is the track's, under it. Under the pointer, the hover layer of every control (R160)."""

    PAD = Space.L - 1       # the word from its edge, as a tab's

    def __init__(self, text: str = "", tip: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("segment")
        self.setText(text)
        self.setToolTip(tip)
        self.setCheckable(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def sizeHint(self) -> QSize:
        return QSize(QFontMetrics(self.font()).horizontalAdvance(self.text()) + 2 * self.PAD + 2, Size.CHIP)

    def minimumSizeHint(self) -> QSize:
        least = QFontMetrics(self.font()).horizontalAdvance("M…") + 2 * Space.XS
        return QSize(min(least, self.sizeHint().width()), Size.CHIP)

    def ink(self, t: dict) -> QColor:
        if not self.isEnabled():
            return QColor(theme_colors.faded_text(t))
        return QColor(t["text"] if self.isChecked() or self.underMouse() else t["text2"])

    def paintEvent(self, event) -> None:
        t = tokens()
        p = QPainter(self)
        box = QRectF(self.rect())
        if self.isEnabled() and not self.isChecked() and (self.underMouse() or self.isDown()):
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(theme_colors.qt_hex(t["press" if self.isDown() else "hover"])))
            p.drawRoundedRect(box, Radius.INNER, Radius.INNER)
        if self.hasFocus():
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(QPen(QColor(t["accent"]), Line.FOCUS))
            p.setBrush(Qt.BrushStyle.NoBrush)
            inset = Line.FOCUS / 2
            p.drawRoundedRect(box.adjusted(inset, inset, -inset, -inset), Radius.INNER, Radius.INNER)
        self.paint_face(p, box, t)

    def paint_face(self, p: QPainter, box: QRectF, t: dict) -> None:
        room = box.toRect().adjusted(Space.XS, 0, -Space.XS, 0)
        p.setPen(self.ink(t))
        p.setFont(self.font())
        p.drawText(room, Qt.AlignmentFlag.AlignCenter,
                   QFontMetrics(self.font()).elidedText(self.text(), Qt.TextElideMode.ElideRight, room.width()))


class Segments(QFrame):
    """A track of segments. `add` puts one in, with what stands for it; `chosen` says what a click or an arrow chose;
    `set_current` chooses without saying it. Something else can stand on the track at its end (`row`: the «+» of the
    variants). Exclusive: the rectangle slides. Not exclusive: `Segment.toggled` of each, its rectangle fades."""

    chosen = Signal(object)

    def __init__(self, exclusive: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("segments")
        self.exclusive = exclusive
        self.row = QHBoxLayout(self)
        self.row.setContentsMargins(TRACK_AIR, TRACK_AIR, TRACK_AIR, TRACK_AIR)
        self.row.setSpacing(0 if exclusive else Space.XXS)
        self.group = QButtonGroup(self)
        self.group.setExclusive(exclusive)
        self.items: list[Segment] = []
        self.slide = Slide(self, self.selection)
        self.moved = False                          # exclusive: the choice changed since the last click said
        self.fading: Segment | None = None          # not exclusive: the segment whose rectangle comes or goes
        self.fade = QVariantAnimation(self)
        self.fade.setStartValue(0.0)
        self.fade.setEndValue(1.0)
        self.fade.setDuration(Motion.FAST)
        self.fade.valueChanged.connect(lambda _v: self.update())
        self.fade.finished.connect(self._faded)
        self.group.buttonToggled.connect(self._toggled)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        if exclusive:
            self.setFocusPolicy(Qt.FocusPolicy.TabFocus)    # the arrows choose, the rectangle shows the focus

    def add(self, text: str, data=None, tip: str = "", segment: Segment | None = None) -> Segment:
        b = segment if segment is not None else Segment(text, tip)
        b.setProperty("data", data if data is not None else text)
        if not self.exclusive:
            b.setFocusPolicy(Qt.FocusPolicy.TabFocus)       # each its own state: Tab, the arrows and the space bar
        self.group.addButton(b)
        self.row.insertWidget(len(self.items), b)
        self.items.append(b)
        b.clicked.connect(lambda _c=False, s=b: self._clicked(s))
        return b

    def _clicked(self, button) -> None:
        """A click: said, but for one on the segment already chosen, which changes nothing (the group keeps it)."""
        if not self.exclusive or self.moved:
            self.chosen.emit(button.property("data"))
        self.moved = False

    def clear(self) -> None:
        for b in self.items:
            self.group.removeButton(b)
            self.row.removeWidget(b)
            b.deleteLater()
        self.items = []

    def current(self):
        """What stands for the segment chosen (exclusive), or none."""
        b = self.group.checkedButton()
        return b.property("data") if b is not None else None

    def set_current(self, data) -> None:
        for b in self.items:
            if b.property("data") == data:
                b.setChecked(True)
                self.moved = False
                return

    def selection(self) -> QRectF | None:
        """Where the rectangle of the choice stands, in the track's pixels."""
        b = self.group.checkedButton() if self.exclusive else None
        return QRectF(b.geometry()) if b is not None and not b.isHidden() else None

    def _toggled(self, button, on: bool) -> None:
        if self.exclusive:
            if on:
                self.moved = True
                self.slide.move()
            return
        self.fade.stop()
        self.fading = button if self.isVisible() and not motion.reduced() else None
        if self.fading is not None:
            self.fade.start()
        self.update()

    def _faded(self) -> None:
        self.fading = None
        self.update()

    def keyPressEvent(self, event) -> None:
        step = {Qt.Key.Key_Left: -1, Qt.Key.Key_Right: 1}.get(event.key())
        ready = [b for b in self.items if b.isEnabled() and not b.isHidden()]
        at = self.group.checkedButton()
        if step is None or not self.exclusive or at not in ready:
            super().keyPressEvent(event)
            return
        i = ready.index(at) + step
        if 0 <= i < len(ready):
            ready[i].click()
        event.accept()

    def paintEvent(self, event) -> None:
        t = tokens()
        p = QPainter(self)
        paint_track(p, QRectF(self.rect()), t)
        if self.exclusive:
            self.slide.paint(p, t, self.hasFocus())
            return
        for b in self.items:
            on = b.isChecked()
            if b is self.fading:
                value = float(self.fade.currentValue())
                p.setOpacity(value if on else 1 - value)
            elif not on:
                continue
            paint_raised(p, QRectF(b.geometry()), t)
            p.setOpacity(1)


class BarTrack(QObject):
    """A track under the tabs of a QTabBar (see the module's words): its rectangle sliding as `Segments`' does."""

    def __init__(self, bar: QTabBar):
        super().__init__(bar)
        self.bar = bar
        self.slide = Slide(bar, self.selection)
        bar.setDrawBase(False)
        bar.currentChanged.connect(lambda _i: self.slide.move())
        bar.installEventFilter(self)

    def _shown(self) -> list[int]:
        return [i for i in range(self.bar.count()) if self.bar.isTabVisible(i)]

    def track(self) -> QRectF | None:
        """The track: around the tabs shown, the air the sheet leaves above and below the bar left out."""
        shown = self._shown()
        if not shown:
            return None
        whole = QRectF(self.bar.tabRect(shown[0])).united(QRectF(self.bar.tabRect(shown[-1])))
        air = Space.XS - TRACK_AIR
        return whole.adjusted(0, air, 0, -air)

    def selection(self) -> QRectF | None:
        """The tab chosen, within the margins the sheet gives it (`QTabBar::tab`, and its first and last)."""
        i, shown = self.bar.currentIndex(), self._shown()
        if i not in shown:
            return None
        return QRectF(self.bar.tabRect(i)).adjusted(TRACK_AIR if i == shown[0] else 0, Space.XS,
                                                    -TRACK_AIR if i == shown[-1] else 0, -Space.XS)

    def eventFilter(self, obj, event) -> bool:
        if obj is self.bar and event.type() == QEvent.Type.Paint:
            track = self.track()
            if track is not None:
                t = tokens()
                p = QPainter(self.bar)
                paint_track(p, track, t)
                self.slide.paint(p, t, self.bar.hasFocus())
                p.end()
        return False                    # the bar then paints its tabs, transparent, over them


def on_bar(bar: QTabBar) -> BarTrack:
    """`bar` as a track of segments; once for a bar."""
    held = bar.findChild(BarTrack)
    return held if held is not None else BarTrack(bar)
