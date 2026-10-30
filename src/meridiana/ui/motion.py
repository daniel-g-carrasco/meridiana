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
to where it goes, a strip at the bottom staying (the menu bar that Alt adds above the phases, R164).
`enter(area, change, kind)`: an opaque page appears over the held picture with a fade, a little slide or a sheet
opening from the left (R178); the veil hides itself at the last frame and with less motion nothing plays."""

from __future__ import annotations

from collections.abc import Callable
import weakref

from PySide6.QtCore import QEasingCurve, QObject, QPoint, QPointF, QRect, QRectF, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QTreeView, QWidget

from .design import Motion, Space

_STATE = {"reduced": False}
_RESPONSIVE: weakref.WeakSet = weakref.WeakSet()
SHIFT = Space.XXL           # how far what comes slides in (logical pixels)


def set_reduced(on: bool) -> None:
    _STATE["reduced"] = bool(on)
    for controller in list(_RESPONSIVE):
        try:
            controller.refresh_motion()
        except RuntimeError:  # A Qt child deleted before its Python wrapper is collected.
            _RESPONSIVE.discard(controller)


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
        _RESPONSIVE.add(self)
        self.setGeometry(area.rect())
        self.show()
        self.raise_()

    def play(self, ms: int = Motion.NORMAL, shift: float = 0.0, drop: float = 0.0, keep: int = 0) -> None:
        """From the picture before to the area as it is now, in `ms`; with `shift`, what comes slides in from
        that many pixels (negative: from the left); with `drop`, what was there moves down that many pixels (up:
        negative) above a strip `keep` pixels high at the bottom that stays."""
        if self.gone:
            return
        if reduced():
            self.refresh_motion()
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

    def refresh_motion(self) -> None:
        if reduced():
            self.gone = True
            self.animation.stop()
            self.hide()
            self.deleteLater()

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


class Entrance(QWidget):
    """An opaque area entering over what was there before. Two pictures are enough: no opacity effect, no mask and
    no layout work at the frames. `slide` fades and comes a little from the left, `sheet` opens from that side and
    `fade` only dissolves. The choices share their duration and their reduced-motion path."""

    finished = Signal()

    def __init__(self, area: QWidget, before: QPixmap, kind: str):
        super().__init__(area.parentWidget())
        self.setObjectName("entrance")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.area, self.before, self.kind = area, before, kind
        self.after: QPixmap | None = None
        self.t = 0.0
        self.done = False
        self.animation = QVariantAnimation(self)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._moved)
        self.animation.finished.connect(self._finish)
        _RESPONSIVE.add(self)
        self.setGeometry(area.geometry())
        self.show()
        self.raise_()

    def play(self, ms: int = Motion.NORMAL) -> None:
        if self.done:                               # cancelled while the window settled: it never plays
            return
        if reduced() or not self.area.isVisible() or self.area.width() < 2 or self.area.height() < 2:
            self._finish()
            return
        try:
            self.after = self.area.grab()
        except RuntimeError:
            self._finish()
            return
        self.raise_()
        self.animation.setDuration(ms)
        self.animation.start()

    def cancel(self) -> None:
        """The veil dropped before or while it plays (the page opened again during its exit, closed during its
        entrance): hidden at once, `finished` emitted, and its play left for after the window's work does nothing.
        Stopping the animation and hiding it from outside was not enough: that play showed it again."""
        self._finish()

    def _finish(self) -> None:
        if self.done:
            return
        self.done = True
        self.animation.stop()
        self.hide()
        self.finished.emit()
        self.deleteLater()

    def refresh_motion(self) -> None:
        if reduced():
            self._finish()

    def _moved(self, value) -> None:
        self.t = float(value)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        if self.kind == "leave" and self.after is not None:
            p.drawPixmap(0, 0, self.after)
            p.setOpacity(1.0 - self.t)
            p.drawPixmap(QPointF(-Space.L * self.t, 0), self.before)
            return
        p.drawPixmap(0, 0, self.before)
        if self.after is None:
            return
        t = self.t
        if self.kind == "sheet":
            p.setClipRect(QRect(0, 0, round(self.width() * t), self.height()))
            p.drawPixmap(0, 0, self.after)
            return
        p.setOpacity(t)
        dx = Space.XL * (1.0 - t) if self.kind == "slide" else 0.0
        p.drawPixmap(QPointF(dx, 0), self.after)


def enter(area: QWidget, change: Callable[[], None], kind: str = "slide", ms: int = Motion.NORMAL) -> Entrance | None:
    """Show an opaque `area` with `change`, then play its entrance after the window has settled. The picture before
    is held from the first frame. With less motion, or no visible window, only `change` happens."""
    top = area.window()
    if reduced() or not top.isVisible() or area.width() < 2 or area.height() < 2:
        change()
        return None
    try:
        before = top.grab(QRect(area.mapTo(top, QPoint(0, 0)), area.size()))
    except RuntimeError:
        change()
        return None
    _replace(area)
    entrance = Entrance(area, before, kind)
    change()
    entrance.raise_()
    after_work(entrance, lambda: entrance.play(ms))
    return entrance


def _replace(area: QWidget) -> None:
    """The entrance or exit still over `area` goes: the new picture already shows it (opened again during its exit,
    closed again during its entrance), and its pending frame must not play over the new one."""
    parent = area.parentWidget()
    if parent is None:
        return
    for old in parent.findChildren(Entrance, options=Qt.FindChildOption.FindDirectChildrenOnly):
        if old.area is area:
            old.cancel()


def leave(area: QWidget, change: Callable[[], None], ms: int = Motion.FAST) -> Entrance | None:
    """Close an overlay with the same short picture transition used when entering it. The caller keeps the veil
    returned and cancels it if the area comes back before it has played (file_page.FilePage.exit); a later
    `enter` or `leave` of the same area drops it too (`_replace`), for callers that do not keep it."""
    if reduced() or not area.isVisible():
        _replace(area)
        change()
        return None
    before = picture(area)
    _replace(area)
    for veil in area.findChildren(Veil, options=Qt.FindChildOption.FindDirectChildrenOnly):
        veil.gone = True                    # a section's crossfade would play again when the page comes back
        veil.animation.stop()
        veil.hide()
        veil.deleteLater()
    entrance = Entrance(area, before, "leave")
    change()

    def play():
        if entrance.done:                           # cancelled: the area came back before its exit played
            return
        if reduced():
            entrance._finish()
            return
        entrance.hide()
        entrance.after = picture(area)
        entrance.show()
        entrance.raise_()
        entrance.animation.setDuration(ms)
        entrance.animation.start()

    after_work(entrance, play)
    return entrance


class Collapse(QObject):
    """A section's real layout height, reversible without a jump or an opacity effect.

    Owns only its height constraints while moving. Expanded sections recover the caller's
    original bounds, so wrapped text and later content changes continue to lay out normally.
    """

    def __init__(self, widget: QWidget):
        super().__init__(widget)
        self.widget = widget
        self.bounds = (widget.minimumHeight(), widget.maximumHeight())
        self.expanded = not widget.isHidden()
        self.animation = QVariantAnimation(self)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._height)
        self.animation.finished.connect(self._finish)
        _RESPONSIVE.add(self)

    @property
    def running(self) -> bool:
        return self.animation.state() == QVariantAnimation.State.Running

    def set_expanded(self, expanded: bool, ms: int = Motion.FAST) -> None:
        expanded = bool(expanded)
        if self.expanded == expanded and (self.running or self.widget.isHidden() != expanded):
            return
        w = self.widget
        if not self.running and self.expanded:
            self.bounds = (w.minimumHeight(), w.maximumHeight())
        start = 0 if w.isHidden() else min(w.height(), w.maximumHeight())
        self.animation.stop()
        self.expanded = expanded
        if reduced() or not w.window().isVisible():
            self._finish()
            return
        w.setMinimumHeight(0)
        w.setMaximumHeight(self.bounds[1])
        if expanded:
            w.show()
        natural = w.sizeHint().height()
        if w.hasHeightForWidth():
            natural = w.heightForWidth(w.width())
        end = min(self.bounds[1], max(self.bounds[0], natural, 0)) if expanded else 0
        w.setMaximumHeight(start)
        self.animation.setStartValue(start)
        self.animation.setEndValue(end)
        self.animation.setDuration(ms)
        self.animation.start()

    def _height(self, value) -> None:
        self.widget.setMaximumHeight(round(value))

    def _finish(self) -> None:
        self.animation.stop()
        self.widget.setVisible(self.expanded)
        if self.expanded:
            self.widget.setMaximumHeight(self.bounds[1])
            self.widget.setMinimumHeight(self.bounds[0])
        else:
            self.widget.setMinimumHeight(0)
            self.widget.setMaximumHeight(0)

    def refresh_motion(self) -> None:
        if reduced() and self.running:
            self._finish()


def collapse(widget: QWidget, expanded: bool, ms: int = Motion.FAST) -> Collapse:
    """Animate a section open or closed; repeat calls reverse the active movement."""
    controller = widget.findChild(Collapse, options=Qt.FindChildOption.FindDirectChildrenOnly)
    if controller is None:
        controller = Collapse(widget)
    controller.set_expanded(expanded, ms)
    return controller


class TreeMotion(QObject):
    """Qt's native tree expansion, following the same live reduced-motion preference."""

    def __init__(self, tree: QTreeView, sections_only: bool = False):
        super().__init__(tree)
        self.tree = tree
        self.sections_only = sections_only
        _RESPONSIVE.add(self)
        self.refresh_motion()

    def refresh_motion(self) -> None:
        self.tree.setAnimated(not reduced() and not self.sections_only)

    def set_expanded(self, item, expanded: bool) -> None:
        """Animate a section, while item details keep their immediate interaction contract."""
        tree = self.tree
        if not self.sections_only:
            item.setExpanded(expanded)
            return
        if reduced() or item.parent() is not None or not tree.isVisible() or item.isExpanded() == expanded:
            item.setExpanded(expanded)
            return
        area = tree.viewport()
        before = picture(area)
        boundary = tree.visualItemRect(item).bottom() + 1

        def span(parent):
            total = 0
            for index in range(parent.childCount()):
                child = parent.child(index)
                if not child.isHidden():
                    total += tree.visualItemRect(child).height()
                    if child.isExpanded():
                        total += span(child)
            return total

        delta = span(item) if not expanded else 0
        item.setExpanded(expanded)
        tree.doItemsLayout()
        if expanded:
            delta = span(item)
        delta = min(delta, max(0, area.height() - boundary)) * (1 if expanded else -1)
        for old in area.findChildren(SectionVeil, options=Qt.FindChildOption.FindDirectChildrenOnly):
            old.gone = True
            old.animation.stop()
            old.hide()
            old.deleteLater()
        veil = SectionVeil(area, before, boundary, delta)
        after_work(veil, lambda: veil.play(Motion.FAST))


class SectionVeil(Veil):
    """Reveal a tree section and move the following rows, keeping every glyph unscaled.

    Qt's native tree animation is fixed at 256 ms. This snapshot path shares FAST
    with collapsible widget sections and never delays the real item/scroll state.
    """

    def __init__(self, area: QWidget, before: QPixmap, boundary: int, delta: int):
        super().__init__(area, before)
        self.boundary, self.delta = boundary, delta

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        if self.after is None:
            p.drawPixmap(0, 0, self.before)
            return
        p.drawPixmap(0, 0, self.after)
        boundary, delta, t = self.boundary, self.delta, self.t
        if delta > 0:
            edge = boundary + round(delta * t)
            p.setClipRect(QRect(0, edge, self.width(), self.height() - edge))
            p.drawPixmap(QPointF(0, delta * t), self.before)
        elif delta < 0:
            remaining = round(-delta * (1.0 - t))
            p.setClipRect(QRect(0, boundary, self.width(), remaining))
            p.drawPixmap(0, 0, self.before)
            p.setClipRect(QRect(0, boundary + remaining, self.width(), self.height() - boundary - remaining))
            p.drawPixmap(QPointF(0, remaining), self.after)


def animate_tree(tree: QTreeView, *, sections_only: bool = False) -> TreeMotion:
    controller = tree.findChild(TreeMotion, options=Qt.FindChildOption.FindDirectChildrenOnly)
    return controller if controller is not None else TreeMotion(tree, sections_only)
