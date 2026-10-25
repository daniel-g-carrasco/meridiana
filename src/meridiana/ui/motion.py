"""Light movements, as GNOME and KDE make them (R75; Daniel, 24/10/2026: «ci devono essere leggere e semplici
animazioni nel cambio scheda, nel ricaricamento di proprietà, apertura e chiusura sezioni»), made again for R83
(«le animazioni sono lente e scattanti»): what changes is covered by a veil with its picture as it was, the change
is made, and once the window has done what the change asked of it (the next turn of its event loop) the veil
plays from the picture before to the picture after. Measured on 24/10/2026: the old fade grabbed the whole page
(16-112 ms before anything moved) and faded it through a QGraphicsOpacityEffect, which renders the page again at
every frame; the veil grabs only the area that moves, is opaque (nothing under it is painted again while it
plays) and paints two pictures with the painter's opacity. Nothing moves when the system or the preferences ask
for less motion (`set_reduced`).

`crossfade(area, change)`: the area fades from before to after in place (another subject in the properties).
`slide(area, change, direction)`: what comes slides in from `direction` while what goes fades (the bar of a phase,
as Office's ribbon). `hold` and `Veil.play` are the two halves, for a caller that moves other things with it (the
tab of the phase, ui/phasebar.py). `push(area, change, drop)`: what was there moves down (or up) by `drop` pixels
to where it goes, a strip at the bottom staying (the menu bar that Alt adds above the phases, R164)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QObject, QPoint, QPointF, QRect, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from .design import Motion, Space

_STATE = {"reduced": False}
SHIFT = Space.XXL           # how far what comes slides in (logical pixels)


def set_reduced(on: bool) -> None:
    _STATE["reduced"] = bool(on)


def reduced() -> bool:
    return _STATE["reduced"]


def picture(area: QWidget) -> QPixmap:
    """What `area` shows on screen, the backgrounds its ancestors paint under it included (a transparent panel
    grabbed alone would come out on the palette's window colour)."""
    top = area.window()
    return top.grab(QRect(area.mapTo(top, QPoint(0, 0)), area.size()))


class Veil(QWidget):
    """The picture of an area over it while it changes: still (`hold`), then playing towards the picture after
    (`play`), then gone. Opaque: the widgets under it are not painted again at each frame."""

    def __init__(self, area: QWidget, before: QPixmap, ground: QColor | None = None):
        super().__init__(area)
        self.setObjectName("veil")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.area, self.before, self.ground = area, before, ground
        self.after: QPixmap | None = None
        self.gone = False                   # replaced by a newer veil before it played
        self.shift = 0.0
        self.drop, self.keep = 0.0, 0           # a push: pixels down (up when negative), the strip at the bottom kept
        self.t = 0.0
        self.animation = QVariantAnimation(self)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._moved)
        self.animation.finished.connect(self.deleteLater)
        self.setGeometry(area.rect())
        self.show()
        self.raise_()

    def play(self, ms: int = Motion.NORMAL, shift: float = 0.0, drop: float = 0.0, keep: int = 0) -> None:
        """From the picture before to the area as it is now, in `ms`; with `shift`, what comes slides in from
        that many pixels (negative: from the left); with `drop`, what was there moves down that many pixels (up:
        negative) above a strip `keep` pixels high at the bottom that stays."""
        if self.gone:
            return
        if not self.area.isVisible() or self.area.width() < 2 or self.area.height() < 2:
            self.deleteLater()
            return
        self.setGeometry(self.area.rect())
        self.hide()                                 # the picture after is the area's, not the veil's
        try:
            self.after = picture(self.area)
        except RuntimeError:
            self.deleteLater()
            return
        self.show()
        self.raise_()
        self.shift = shift
        self.drop, self.keep = drop, keep
        self.animation.setDuration(ms)
        self.animation.start()

    def _moved(self, value) -> None:
        self.t = float(value)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        if self.after is None:
            p.drawPixmap(0, 0, self.before)
            return
        t = self.t
        if self.drop:
            # the picture after under it all; over it what was there, moved, but for the strip at the bottom;
            # at the end, a few pixels from its place, it melts into the picture after (no jump at the end)
            p.drawPixmap(0, 0, self.after)
            ratio = self.before.devicePixelRatio()
            h = self.height() - self.keep
            p.setOpacity(1.0 if t < 0.9 else max(0.0, (1.0 - t) * 10.0))
            p.setClipRect(QRect(0, 0, self.width(), h))
            p.drawPixmap(QPointF(0, self.drop * t), self.before)
            p.setClipping(False)
            if self.keep:
                p.drawPixmap(QPointF(0, h), self.before, QRectF(0, h * ratio, self.width() * ratio, self.keep * ratio))
            return
        if self.shift:
            p.fillRect(self.rect(), self.ground if self.ground is not None else self.palette().window())
            p.setOpacity(max(0.0, 1.0 - 2.0 * t))   # what goes is gone half way
            p.drawPixmap(QPointF(-self.shift * t, 0), self.before)
            p.setOpacity(t)
            p.drawPixmap(QPointF(self.shift * (1.0 - t), 0), self.after)
        else:
            p.drawPixmap(0, 0, self.after)
            p.setOpacity(1.0 - t)
            p.drawPixmap(0, 0, self.before)


def hold(area: QWidget, ground: QColor | None = None) -> Veil | None:
    """`area` covered by its picture as it is now, until the veil's `play`; None (nothing to play) with less
    motion or when `area` is not on screen. A veil still over `area` goes: the new picture already has it."""
    if reduced() or area is None or not area.isVisible() or area.width() < 2 or area.height() < 2:
        return None
    try:
        before = picture(area)
    except RuntimeError:
        return None
    for old in area.findChildren(Veil, options=Qt.FindChildOption.FindDirectChildrenOnly):
        old.gone = True
        old.animation.stop()
        old.hide()
        old.deleteLater()
    return Veil(area, before, ground)


def after_work(context: QObject, run: Callable[[], None]) -> None:
    """`run()` once the window has done what a change asked of it: two turns of the event loop later, so after the
    work the change's slots left for the next turn too (the properties pad their fields there)."""
    QTimer.singleShot(0, context, lambda: QTimer.singleShot(0, context, run))


def _later(veil: Veil | None, ms: int, shift: float) -> None:
    if veil is not None:
        after_work(veil, lambda: veil.play(ms, shift))


def crossfade(area: QWidget, change: Callable[[], None], ms: int = Motion.NORMAL) -> None:
    """`change()`, and `area` fades from what it showed to what it shows once the window has done with the change;
    at once with less motion or when `area` is not on screen."""
    veil = hold(area)
    change()
    _later(veil, ms, 0.0)


def push(area: QWidget, change: Callable[[], None], drop: Callable[[], float], keep: Callable[[], int] = lambda: 0,
         ms: int = Motion.NORMAL) -> None:
    """`change()`, and what `area` showed moves by `drop()` pixels (asked once the window has done with the
    change: down when positive) to the area as it is now, the strip `keep()` pixels high at its bottom staying; at
    once with less motion or when `area` is not on screen."""
    veil = hold(area)
    change()
    if veil is not None:
        after_work(veil, lambda: veil.play(ms, drop=drop(), keep=keep()))


def slide(area: QWidget, change: Callable[[], None], direction: int, ms: int = Motion.NORMAL,
          ground: QColor | None = None) -> None:
    """`change()`, and what `area` shows now slides in from the right (`direction` > 0) or from the left while what
    it showed fades; `ground` is the colour under the two pictures."""
    veil = hold(area, ground)
    change()
    _later(veil, ms, SHIFT if direction >= 0 else -SHIFT)
