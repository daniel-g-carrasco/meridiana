"""Dock layout motion and geometry previews without changing the live layout.

A hidden, disposable QMainWindow solves the same docking operation as the real one.
The preview paints snapshots in those rectangles, leaving focus, visibility signals,
application state and jobs of the live window untouched until the drop is accepted.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

import shiboken6
from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QRect, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QApplication, QDockWidget, QMainWindow, QStatusBar, QTabBar, QToolBar, QWidget)

from ..i18n import _
from . import motion
from .cards import EDGE, GAP, CardDock, arena, default_tokens
from .design import Motion, Radius, Size, Space

DIRECT = Qt.FindChildOption.FindDirectChildrenOnly
INERTIA = Space.M       # a drop zone is left only once the pointer is this far inside the next one (R317)


def cards(window: QMainWindow) -> list[QWidget]:
    return [*window.findChildren(QDockWidget, options=DIRECT), window.centralWidget()]


def _docked(widget: QWidget | None) -> bool:
    """A card the window lays out: a floating panel is a window of its own, its geometry on the screen."""
    return widget is not None and not widget.isHidden() and not (
        isinstance(widget, QDockWidget) and widget.isFloating())


def _settle_layout(window: QMainWindow) -> None:
    """Resolve card margins synchronously, without dispatching unrelated application jobs."""
    for _turn in range(6):
        before = [widget.geometry() for widget in cards(window) if widget is not None]
        for dock in window.findChildren(CardDock, options=DIRECT):
            dock._fit_now()
            dock.layout().activate()
        window.layout().activate()
        after = [widget.geometry() for widget in cards(window) if widget is not None]
        if before == after:
            break


@dataclass(frozen=True)
class DockTarget:
    area: Qt.DockWidgetArea
    anchor: QDockWidget | None = None
    orientation: Qt.Orientation = Qt.Orientation.Horizontal
    before: bool = False
    tab: bool = False
    extent: int = 0         # the card's height or width once there; 0: its own (R317: Size.PLACEHOLDER across)


def apply_target(window: QMainWindow, source: QDockWidget, target: DockTarget) -> None:
    """One docking operation, shared by the solver and the accepted drop."""
    size = source.size()
    source.setFloating(False)
    source.show()
    if target.anchor is None:
        window.addDockWidget(target.area, source)
    elif target.tab:
        window.tabifyDockWidget(target.anchor, source)
        source.raise_()
    elif target.before:
        window.addDockWidget(target.area, source)
        window.splitDockWidget(source, target.anchor, target.orientation)
    else:
        window.splitDockWidget(target.anchor, source, target.orientation)
    if not target.tab:
        orientation = (target.orientation if target.anchor is not None else
                       Qt.Orientation.Horizontal if target.area in (Qt.DockWidgetArea.LeftDockWidgetArea,
                                                                   Qt.DockWidgetArea.RightDockWidgetArea)
                       else Qt.Orientation.Vertical)
        extent = target.extent or (size.width() if orientation == Qt.Orientation.Horizontal else size.height())
        window.resizeDocks([source], [extent], orientation)
    _settle_layout(window)
    _show_tab_bars(window)


def _show_tab_bars(window: QMainWindow) -> None:
    """A layout pass forced in the same turn as a tabify leaves Qt's new tab bar hidden for good (Qt shows it
    only from its own deferred pass): the panel behind it then had no way back, and the layout saved with it put
    every panel of that group off the window at the next start (R294). A bar holding two or more panels is shown."""
    for bar in window.findChildren(QTabBar, options=DIRECT):
        if bar.count() > 1 and bar.isHidden():
            bar.show()


def lost_panels(window: QMainWindow) -> list[QDockWidget]:
    """The open panels with no place to be seen: docked outside the window and not a tab behind another one whose
    tab bar shows (Qt parks a panel at negative coordinates when its tab group lost the bar, R294), or floating
    off every screen. Asked of a window shown and laid out."""
    room = window.rect()
    bars = any(bar.isVisible() and bar.count() > 1 for bar in window.findChildren(QTabBar, options=DIRECT))
    screens = [screen.availableGeometry() for screen in QApplication.screens()]
    lost = []
    for dock in window.findChildren(QDockWidget, options=DIRECT):
        if dock.isHidden():
            continue
        if dock.isFloating():
            if not any(area.intersects(dock.frameGeometry()) for area in screens):
                lost.append(dock)
            continue
        if room.intersects(dock.geometry()):
            continue
        shown = [tab for tab in window.tabifiedDockWidgets(dock) if not tab.isHidden()
                 and not tab.isFloating() and room.intersects(tab.geometry())]
        if not (shown and bars):
            lost.append(dock)
    return lost


def commit_target(window: QMainWindow, source: QDockWidget, target: DockTarget) -> None:
    """The drop accepted on the live window. A drop that would leave an open panel out of sight (R294) is not
    kept: the layout as it was before it comes back, and every panel stays one click away."""
    before = window.saveState()
    apply_target(window, source, target)
    if lost_panels(window):
        window.restoreState(before)
        _settle_layout(window)
        _show_tab_bars(window)


def _placed(window: QMainWindow) -> dict[QWidget, QRect]:
    """The cards where `window` has them now. A tab behind another one is parked by Qt off the window (at -1500,
    -625 here): it is given the rectangle of the tab in front, under which it lies, rather than flying there and
    back on every preview (R312); one whose front is not in sight is left out."""
    room = window.rect()
    result = {}
    for widget in cards(window):
        if not _docked(widget):
            continue
        rect = QRect(widget.geometry())
        if isinstance(widget, QDockWidget) and not room.intersects(rect):
            front = next((tab for tab in window.tabifiedDockWidgets(widget)
                          if _docked(tab) and room.intersects(tab.geometry())), None)
            if front is None:
                continue
            rect = QRect(front.geometry())
        result[widget] = rect
    return result


def cancel_drags(window: QMainWindow) -> None:
    """No drag of a panel, no preview, no motion layer and no carried picture left over the cards: before a layout
    is put back."""
    for dock in window.findChildren(CardDock, options=DIRECT):
        drag = getattr(dock, 'drag_motion', None)
        if drag is not None and drag.solver is not None:
            drag.finish(cancel=True)
    for layer in window.findChildren(Reflow, options=DIRECT):
        layer.drag = None
        layer.hold_open = False
        layer.lead.stop()
        layer.animation.stop()
        layer.hide()
        layer.deleteLater()
    for lift in window.findChildren(Lift, options=DIRECT):
        lift.animation.stop()
        lift.hide()
        lift.deleteLater()


class _Measure(QWidget):
    def __init__(self, original: QWidget):
        super().__init__()
        self.hint = original.sizeHint()
        self.minimum = original.minimumSizeHint()
        self.setMinimumSize(original.minimumSize())
        self.setMaximumSize(original.maximumSize())
        self.setSizePolicy(original.sizePolicy())

    def sizeHint(self):
        return self.hint

    def minimumSizeHint(self):
        return self.minimum


class LayoutPreview:
    """A throwaway Qt layout with matching constraints and state, never the real widgets."""

    def __init__(self, window: QMainWindow, source: QDockWidget):
        self.window, self.source = window, source
        self.solved = False
        self._build()

    def _build(self) -> None:
        window, source = self.window, self.source
        self.shadow = QMainWindow(window, Qt.WindowType.Window)
        self.shadow.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        self.shadow.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.shadow.setDockOptions(window.dockOptions() & ~QMainWindow.DockOption.AnimatedDocks)
        self.shadow.setContentsMargins(window.contentsMargins())
        self.shadow.setLayoutDirection(window.layoutDirection())
        self.shadow.resize(window.size())
        self.copies = {}
        if window.centralWidget() is not None:
            centre = _Measure(window.centralWidget())
            self.shadow.setCentralWidget(centre)
            self.copies[window.centralWidget()] = centre
        menu = window.menuWidget()
        if menu is not None and menu.isVisible():
            dummy = QWidget()
            dummy.setFixedHeight(menu.height())
            self.shadow.setMenuWidget(dummy)
        status = window.findChild(QStatusBar, options=DIRECT)
        if status is not None and status.isVisible():
            dummy = QStatusBar()
            dummy.setFixedHeight(status.height())
            self.shadow.setStatusBar(dummy)
        for toolbar in window.findChildren(QToolBar, options=DIRECT):
            dummy = QToolBar()
            dummy.setObjectName(toolbar.objectName())
            dummy.setFixedSize(toolbar.size())
            self.shadow.addToolBar(window.toolBarArea(toolbar), dummy)
            dummy.setVisible(toolbar.isVisible())
        for corner in (Qt.Corner.TopLeftCorner, Qt.Corner.TopRightCorner,
                       Qt.Corner.BottomLeftCorner, Qt.Corner.BottomRightCorner):
            self.shadow.setCorner(corner, window.corner(corner))
        for real in window.findChildren(QDockWidget, options=DIRECT):
            dummy = (CardDock(real.windowTitle(), self.shadow) if isinstance(real, CardDock)
                     else QDockWidget(real.windowTitle(), self.shadow))
            dummy.setObjectName(real.objectName())
            dummy.setFeatures(real.features())
            dummy.setAllowedAreas(real.allowedAreas())
            if not isinstance(real, CardDock):
                dummy.setMinimumSize(real.minimumSize())
            dummy.setMaximumSize(real.maximumSize())
            if real.titleBarWidget() is not None and not isinstance(real, CardDock):
                dummy.setTitleBarWidget(_Measure(real.titleBarWidget()))
            dummy.setWidget(_Measure(real.widget()) if real.widget() is not None else QWidget())
            self.shadow.addDockWidget(window.dockWidgetArea(real), dummy)
            self.copies[real] = dummy
        self.shadow.restoreState(window.saveState())
        self.shadow.show()
        _settle_layout(self.shadow)
        self.base = self.shadow.saveState()
        self.source_size = source.size()

    def solve(self, target: DockTarget) -> dict[QWidget, QRect]:
        # Qt retains tab groups during repeated restoreState calls on the same layout.
        # Rebuild the small measuring window on target changes so every preview starts
        # from the real baseline, including after hovering over a tab target.
        if self.solved:
            self.close()
            self._build()
        self.solved = True
        source = self.copies[self.source]
        source.resize(self.source_size)
        copied = replace(target, anchor=self.copies.get(target.anchor))
        apply_target(self.shadow, source, copied)
        _settle_layout(self.shadow)
        placed = _placed(self.shadow)
        return {real: placed[dummy] for real, dummy in self.copies.items() if dummy in placed}

    def close(self) -> None:
        # Out of the window's children at once: QMainWindow.restoreState looks its panels up by object name among
        # all its descendants, and adopted a measuring copy still waiting for deletion as a second "help" (R294).
        self.shadow.hide()
        self.shadow.setParent(None)
        self.shadow.deleteLater()


def _collapsed(rect: QRect, edge: str) -> QRect:
    r = QRect(rect)
    if edge == 'bottom':
        r.setTop(r.bottom() + 1)
    elif edge == 'left':
        r.setRight(r.left() - 1)
    elif edge == 'top':
        r.setBottom(r.top() - 1)
    else:
        r.setLeft(r.right() + 1)
    return r


class Reflow(QWidget):
    """One lightweight snapshot layer, retargeted from its current frame on reversal."""

    def __init__(self, window: QMainWindow):
        super().__init__(window)
        self.host = window
        self.setObjectName('dock-reflow')
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setGeometry(arena(window))
        self.pictures = {}
        self.inners = {}
        self.starts = {}
        for widget in cards(window):
            if _docked(widget) and widget.isVisible() and not widget.visibleRegion().isEmpty():
                self.pictures[widget] = motion.picture(widget)
                self.inners[widget] = widget.card_rect() if isinstance(widget, CardDock) else widget.contentsRect()
                self.starts[widget] = QRect(widget.geometry())
        self.ends = dict(self.starts)
        self.progress = 0.0
        self.preview_source = None
        self.preview_rect = QRect()
        self.animation = QVariantAnimation(self)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._step)
        self.animation.finished.connect(self._settled)
        self.hold_open = False
        self.slot_first = False             # the slot drawn where it goes while the cards are still (R317)
        self.lead = QTimer(self)            # the moment between the slot shown and the cards sliding
        self.lead.setSingleShot(True)
        self.lead.timeout.connect(self.animation.start)
        self.drag = None                    # the DockDrag holding this layer open, if any
        self.lift = None                    # the carried picture of the panel dragged, kept above this layer
        self.generation = 0
        motion._RESPONSIVE.add(self)
        self.show()
        self.raise_()

    def card_rect(self, rect: QRect) -> QRect:
        """The card drawn in a panel's rectangle: EDGE from the arena's sides, GAP from its top and bottom."""
        room = self.geometry()
        return rect.adjusted(EDGE if abs(rect.left() - room.left()) <= 2 else 0,
                             GAP if abs(rect.top() - room.top()) <= 2 else 0,
                             -EDGE if abs(rect.right() - room.right()) <= 2 else 0,
                             -GAP if rect.bottom() >= room.bottom() - 2 else 0)

    def rectangles(self) -> dict[QWidget, QRect]:
        t = self.progress
        result = {}
        for widget, end in self.ends.items():
            start = self.starts.get(widget, end)
            result[widget] = QRect(*(round(a + (b - a) * t) for a, b in
                                    zip(start.getRect(), end.getRect(), strict=True)))
        return result

    def slot(self) -> QRect:
        """Where the slot of the card carried is drawn now."""
        if self.slot_first:
            return self.card_rect(self.preview_rect)
        return self.card_rect(self.rectangles().get(self.preview_source, self.preview_rect))

    def retarget(self, ends: dict[QWidget, QRect], *, edge: str = 'right', preview=None,
                 hold: bool = False, ms: int = Motion.FAST, lead: int = 0) -> None:
        """The cards from where they are drawn now to `ends` in `ms`. With `lead` (R317), the slot of `preview`
        shows at once where it goes and the cards start sliding `lead` ms later: first what will happen, then it."""
        self.starts = self.rectangles()
        self.animation.stop()
        self.lead.stop()
        self.hold_open = hold
        self.preview_source = preview
        self.preview_rect = QRect(ends.get(preview, QRect()))
        # The live window is already in its final state for a collapse or a committed drop.
        # Hide only our layer while grabbing newly opened cards, never any actual panel.
        self.hide()
        for widget, end in ends.items():
            if widget not in self.pictures:
                if widget.visibleRegion().isEmpty():
                    continue                # a tab behind another: nothing of it to show
                self.pictures[widget] = motion.picture(widget)
                self.inners[widget] = widget.card_rect() if isinstance(widget, CardDock) else widget.contentsRect()
                self.starts[widget] = _collapsed(end, edge)
        self.show()
        self.raise_()
        if self.lift is not None:
            if not shiboken6.isValid(self.lift) or self.lift.isHidden():
                self.lift = None
            elif not self.lift.isWindow():
                self.lift.raise_()          # the carried picture stays over the cards (a window is above them)
        self.ends = {widget: QRect(ends.get(widget, _collapsed(start, edge)))
                     for widget, start in self.starts.items()}
        self.animation.setDuration(0 if motion.reduced() else ms)
        self.progress = 0.0                 # after: a new duration plays the old time's value out (0.66 if left)
        self.slot_first = bool(lead) and preview is not None
        if lead and not motion.reduced():
            self.update()
            self.lead.start(lead)
        else:
            self.animation.start()

    def _step(self, value) -> None:
        self.progress = float(value)
        self.update()

    def _settled(self) -> None:
        if not self.hold_open:
            self.hide()
            self.deleteLater()

    def refresh_motion(self) -> None:
        if motion.reduced():
            self.animation.stop()
            self.lead.stop()
            self._step(1.0)
            self._settled()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.translate(-self.x(), -self.y())
        theme = getattr(self.host, 'theme', None)
        tokens = theme.tokens if theme is not None else default_tokens()
        p.fillRect(self.geometry(), QColor(tokens['window']))
        positions = self.rectangles()
        card_rect = self.card_rect
        for widget, rect in positions.items():
            if widget is self.preview_source or rect.width() <= 0 or rect.height() <= 0:
                continue
            picture = self.pictures[widget]
            # Keep text at its real size while the available rectangle moves. Scaling
            # a whole panel stretches glyphs and controls during long drag previews.
            p.save()
            target = card_rect(rect)
            path = QPainterPath()
            path.addRoundedRect(QRectF(target).adjusted(0.5, 0.5, -0.5, -0.5), Radius.CARD, Radius.CARD)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.fillPath(path, QColor(tokens['panel']))
            p.setPen(QPen(QColor(tokens['card_line']), 1.0))
            p.drawPath(path)
            p.setClipPath(path)
            inner = self.inners[widget]
            content = QRect(target.topLeft(), inner.size()).adjusted(1, 1, -1, -1).intersected(target)
            p.setClipRect(content, Qt.ClipOperation.IntersectClip)
            p.drawPixmap(target.topLeft() - inner.topLeft(), picture)
            p.restore()
        if self.preview_source is not None and self.preview_rect.isValid():
            r = QRectF(self.slot()).adjusted(1, 1, -1, -1)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            accent = QColor(tokens['text2'])
            fill = QColor(accent)
            fill.setAlphaF(0.12)
            p.setBrush(fill)
            p.setPen(QPen(accent, 1.5, Qt.PenStyle.DashLine))
            p.drawRoundedRect(r, Radius.CARD, Radius.CARD)
            p.setPen(accent)
            p.drawText(r.adjusted(Space.L, Space.L, -Space.L, -Space.L),
                       Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                       self.preview_source.windowTitle())


def floating_lifts() -> bool:
    """Whether the carried card can be a little window of its own, placed by the program (R317): not on Wayland."""
    return not QGuiApplication.platformName().startswith('wayland')


class Lift(QWidget):
    """The card taken by the pointer (R312): its picture, carried from the point it was taken at, a little larger
    than it lay and a touch translucent (lifted; no shadow, the system draws none). Between two pointer moves only
    this widget moves: no style, no layout of the window is touched. At the end it flies into the slot it was
    given, back to its size, and dissolves into the real card there; cancelled, it flies home the same way.

    A little window of its own, owned by the window (R317): a child of it was cut at its edge when the pointer
    carried the card out. The kind of window Qt carries its own drag pictures in (a tooltip's: never active, no
    frame, above the window, placed by the program): translucent, without a shadow, never under the mouse, so the
    pointer stays the title's, held by its grab, and the window keeps the keyboard (Esc). On Wayland a program
    cannot place a window of its own: there the picture stays a child of the window, kept inside it, the point it
    was taken at sliding under the pointer at the edge."""

    SCALE = 1.03                            # carried: a little larger than it lay
    OPACITY = 0.94                          # carried: the floor shows a little through it

    FLAGS = (Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.BypassWindowManagerHint |
             Qt.WindowType.NoDropShadowWindowHint | Qt.WindowType.WindowDoesNotAcceptFocus |
             Qt.WindowType.WindowTransparentForInput)

    def __init__(self, window: QMainWindow, dock: QDockWidget, grip: QPoint):
        own = floating_lifts()
        super().__init__(window, self.FLAGS if own else Qt.WindowType.Widget)
        self.host = window
        self.setObjectName('dock-lift')
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        if own:
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        else:
            self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.picture = motion.picture(dock)
        self.inner = dock.card_rect() if isinstance(dock, CardDock) else dock.contentsRect()  # the card, in the picture
        self.home = QRect(self.inner.translated(dock.pos()))       # the card in the window, where it was taken
        self.frame = QRect(self.home)                               # the card now, at scale 1
        self.grip = window.mapFromGlobal(grip) - self.home.topLeft()     # the point taken, in the card's pixels
        self.scale = 1.0
        self.opacity = 1.0
        self.cached = None                  # the picture at the carried scale, made once the lift has settled
        self.run = None                     # (frame from, frame to, scale from, to, opacity from, to, then)
        self.animation = QVariantAnimation(self)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(lambda value: self._apply(float(value)))
        self.animation.finished.connect(self._finished)
        motion._RESPONSIVE.add(self)
        self._place()
        self.show()
        if not own:
            self.raise_()
        self._tween(self.frame, self.SCALE, self.OPACITY, Motion.FAST)

    def follow(self, point: QPoint) -> None:
        """The pointer at `point` (the window's pixels): the card keeps the point it was taken at under it."""
        delta = point - self.grip - self.frame.topLeft()
        if delta.isNull():
            return
        self.frame.translate(delta)
        if self.run is not None:            # the rise goes on where the pointer is
            self.run[0].translate(delta)
            self.run[1].translate(delta)
        self._place()

    def fly(self, slot: QRect, then: Callable[[], None] | None = None) -> None:
        """Into `slot` (the window's pixels), back to its size and whole; `then()` once there."""
        self._tween(slot, 1.0, 1.0, Motion.CAREFUL, then)

    def dissolve(self) -> None:
        self._tween(self.frame, self.scale, 0.0, Motion.NORMAL, self._gone)

    def _gone(self) -> None:
        self.hide()
        self.deleteLater()

    def _tween(self, frame: QRect, scale: float, opacity: float, ms: int, then=None) -> None:
        self.animation.stop()
        self.run = [QRect(self.frame), QRect(frame), self.scale, scale, self.opacity, opacity, then]
        if ms <= 0 or motion.reduced():
            self._apply(1.0)
            self._finished()
            return
        self.animation.setDuration(ms)
        self.animation.start()

    def _apply(self, t: float) -> None:
        run = self.run
        if run is None:
            return
        self.frame = QRect(*(round(a + (b - a) * t) for a, b in zip(run[0].getRect(), run[1].getRect(), strict=True)))
        self.scale = run[2] + (run[3] - run[2]) * t
        self.opacity = run[4] + (run[5] - run[4]) * t
        self._place()
        self.update()

    def _finished(self) -> None:
        run, self.run = self.run, None
        if run is None:
            return
        if self.scale == self.SCALE and self.cached is None:
            # the carried picture scaled once: every move then blits it (fluid on the 4K, no transform a frame)
            self.cached = self.picture.scaled(self.picture.size() * self.SCALE, Qt.AspectRatioMode.IgnoreAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)
            self.cached.setDevicePixelRatio(self.picture.devicePixelRatio())
            self.update()
        if run[6] is not None:
            run[6]()

    def _place(self) -> None:
        s = self.scale
        corner = self.frame.topLeft() + self.grip - QPoint(round(self.grip.x() * s), round(self.grip.y() * s))
        width, height = round(self.frame.width() * s), round(self.frame.height() * s)
        if self.isWindow():
            corner = self.host.mapToGlobal(corner)      # on the screen, wherever the pointer takes it
        else:                                           # inside the window, whole: the grip slides at its edge
            room = self.host.rect()
            corner = QPoint(max(room.left(), min(corner.x(), room.right() + 1 - width)),
                            max(room.top(), min(corner.y(), room.bottom() + 1 - height)))
        self.setGeometry(corner.x(), corner.y(), width, height)

    def refresh_motion(self) -> None:
        if motion.reduced() and self.run is not None:
            self.animation.stop()
            self._apply(1.0)
            self._finished()

    def paintEvent(self, event) -> None:
        theme = getattr(self.host, 'theme', None)
        tokens = theme.tokens if theme is not None else default_tokens()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self.opacity)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), Radius.CARD, Radius.CARD)
        p.fillPath(path, QColor(tokens['panel']))
        p.setPen(QPen(QColor(tokens['card_line']), 1.0))
        p.drawPath(path)
        p.setClipPath(path)
        s = self.scale
        # the content at its real size from the card's top left corner, clipped to what the card held: never
        # stretched into a slot of another size, and never the floor grabbed around the card
        content = QRect(1, 1, round(self.inner.width() * s) - 2, round(self.inner.height() * s) - 2)
        p.setClipRect(content, Qt.ClipOperation.IntersectClip)
        if self.cached is not None and s == self.SCALE:
            p.drawPixmap(QPoint(-round(self.inner.x() * s), -round(self.inner.y() * s)), self.cached)
        else:
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            p.scale(s, s)
            p.drawPixmap(-self.inner.topLeft(), self.picture)


def _covered(window: QMainWindow) -> bool:
    """A page over the cards (File, an entrance playing over it): the change happens under it and there is
    nothing to show; a layer raised over it would cut the page into the cards' pictures. A small overlay, such as
    a floating assistant, does not count."""
    room = arena(window)
    shown = set(cards(window))
    siblings = [child for child in window.children() if isinstance(child, QWidget)]
    top = max((i for i, widget in enumerate(siblings) if widget in shown), default=-1)
    for widget in siblings[top + 1:]:
        if isinstance(widget, (Reflow, Lift)) or widget.isWindow() or not widget.isVisible():
            continue
        over = widget.geometry().intersected(room)
        if over.width() * over.height() * 2 >= room.width() * room.height():
            return True
    return False


def reflow(window: QMainWindow, change: Callable, *, edge: str = 'right') -> Reflow | None:
    layer = window.findChild(Reflow, options=DIRECT)
    if layer is not None and layer.drag is not None:
        layer.drag.finish(cancel=True)      # a panel toggled by the keyboard mid-drag: the preview's baseline is gone
    if motion.reduced() or not window.isVisible() or _covered(window):
        change()
        if layer is not None:
            layer.hide()
            layer.deleteLater()
        return None
    if layer is None or not layer.isVisible():
        layer = Reflow(window)
    layer.generation += 1
    generation = layer.generation
    change()
    window.layout().activate()

    def settle():
        if layer.generation != generation:
            return
        layer.retarget(_placed(window), edge=edge)

    motion.after_work(layer, settle)
    return layer


def target_at(window: QMainWindow, source: QDockWidget, point: QPoint, *, tabs: bool = False) -> DockTarget | None:
    """Where a drop at `point` (the window's pixels) would put `source`: a band Space.XXL wide along the arena's
    sides docks it at that side; a panel under the point takes it beside itself, in the half of the point (the side
    nearest it, the distances measured in the panel's width and height), or with `tabs` (Alt held, R317) as a tab
    behind it wherever the point is on it: never a tab without Alt. Alt does not change the bands. The central
    widget is never a destination (R312): over it, outside the window's bands, there is nothing to answer."""
    room = arena(window)
    if not room.contains(point):
        return None
    distances = ((point.x() - room.left(), Qt.DockWidgetArea.LeftDockWidgetArea),
                 (room.right() - point.x(), Qt.DockWidgetArea.RightDockWidgetArea),
                 (point.y() - room.top(), Qt.DockWidgetArea.TopDockWidgetArea),
                 (room.bottom() - point.y(), Qt.DockWidgetArea.BottomDockWidgetArea))
    distance, area = min(distances, key=lambda pair: pair[0])
    if distance < Space.XXL and source.allowedAreas() & area:
        return _band(window, source, area, point)
    for anchor in window.findChildren(QDockWidget, options=DIRECT):
        if anchor is source or anchor.isHidden() or anchor.isFloating() or not anchor.geometry().contains(point):
            continue
        area = window.dockWidgetArea(anchor)
        if not source.allowedAreas() & area:
            continue
        if tabs:
            return DockTarget(area, anchor, tab=True)
        r = anchor.geometry()
        x, y = (point.x() - r.left()) / r.width(), (point.y() - r.top()) / r.height()
        side = min((x, 'left'), (1 - x, 'right'), (y, 'top'), (1 - y, 'bottom'))[1]
        return _beside(window, area, anchor, side)
    return None


_OUTER = {Qt.DockWidgetArea.LeftDockWidgetArea: 'left', Qt.DockWidgetArea.RightDockWidgetArea: 'right',
          Qt.DockWidgetArea.TopDockWidgetArea: 'top', Qt.DockWidgetArea.BottomDockWidgetArea: 'bottom'}
_ACROSS = (Qt.DockWidgetArea.TopDockWidgetArea, Qt.DockWidgetArea.BottomDockWidgetArea)


def _beside(window: QMainWindow, area: Qt.DockWidgetArea, anchor: QDockWidget, side: str) -> DockTarget:
    """Beside `anchor` on `side`. Above or below a panel as wide as the window, the card lies across it: its slot
    Size.PLACEHOLDER tall, not its own height (R317: a tall card dropped there pushed the central card far up)."""
    horizontal = side in ('left', 'right')
    r, room = anchor.geometry(), arena(window)
    across = not horizontal and r.left() <= room.left() + EDGE and r.right() >= room.right() - EDGE
    return DockTarget(area, anchor, Qt.Orientation.Horizontal if horizontal else Qt.Orientation.Vertical,
                      before=side in ('left', 'top'), extent=Size.PLACEHOLDER if across else 0)


def _band(window: QMainWindow, source: QDockWidget, area: Qt.DockWidgetArea, point: QPoint) -> DockTarget:
    """The band along the window's side `area`. Where a panel docked at that side lies across the band at the
    point, the band and that panel's outer side are one place: one target, beside that panel on its outer side, the
    same the panel's own half gives a step inside (R317: the slot no longer hops between two answers for one
    place). Where the band is empty, the side itself."""
    along_x = area in (Qt.DockWidgetArea.TopDockWidgetArea, Qt.DockWidgetArea.BottomDockWidgetArea)
    room = window.rect()
    there = []
    for dock in window.findChildren(QDockWidget, options=DIRECT):
        r = dock.geometry()
        if (dock is source or not _docked(dock) or window.dockWidgetArea(dock) != area or not room.intersects(r)
                or not (r.left() <= point.x() <= r.right() if along_x else r.top() <= point.y() <= r.bottom())):
            continue
        reach = (abs(point.y() - r.center().y()) - r.height() / 2 if along_x
                 else abs(point.x() - r.center().x()) - r.width() / 2)
        there.append((reach, dock))
    if not there:                       # across the window above or below: the named height (R317)
        return DockTarget(area, extent=Size.PLACEHOLDER if area in _ACROSS else 0)
    anchor = min(there, key=lambda pair: pair[0])[1]           # the one at the side, under or nearest the point
    return _beside(window, area, anchor, _OUTER[area])


def _settled(window: QMainWindow, source: QDockWidget, point: QPoint, tabs: bool,
             here: DockTarget | None) -> DockTarget | None:
    """The zone at `point` with inertia (R317): `here`, the zone the pointer was in, holds while it is less than
    INERTIA away (the window's edge bounds the probes): the next one is taken only once the pointer is that far
    inside it. Off the window, at once."""
    wanted = target_at(window, source, point, tabs=tabs)
    if wanted == here:
        return here
    room = arena(window)
    if not room.contains(point):
        return wanted
    for dx, dy in ((INERTIA, 0), (-INERTIA, 0), (0, INERTIA), (0, -INERTIA)):
        probe = QPoint(min(max(point.x() + dx, room.left()), room.right()),
                       min(max(point.y() + dy, room.top()), room.bottom()))
        if target_at(window, source, probe, tabs=tabs) == here:
            return here
    return wanted


def _same_card(a: DockTarget | None, b: DockTarget | None) -> bool:
    """Two zones beside the same panel: only the half differs (above or below it, left or right)."""
    return (a is not None and b is not None and a.anchor is not None and a.anchor is b.anchor and a.area == b.area
            and not a.tab and not b.tab)


_CANCEL = (QEvent.Type.WindowDeactivate, QEvent.Type.Hide, QEvent.Type.DevicePixelRatioChange)




class DockDrag(QObject):
    """Title dragging (R312). The card taken is carried by the pointer as a picture (Lift) while the live panels
    stay as they are under the motion layer. A drop zone answers only after the pointer dwelt on it (Motion.DWELL):
    then the panels in its way slide aside and the slot shows; left, they slide back. The drop goes where the slot
    is shown, never where the pointer passed too briefly to be answered: released, the picture flies into the
    slot and dissolves into the real card; Esc, or a release where there is no zone, flies it home."""

    def __init__(self, dock: QDockWidget, title: QWidget):
        super().__init__(title)
        self.dock, self.title = dock, title
        self.origin = None
        self.solver = None
        self.layer = None
        self.lift = None
        self.target = None                  # the zone shown, where a release would go
        self.pending = None                 # the zone under the pointer, waiting its dwell
        self.waiting = False
        self.last_point = None
        self.local = None                   # the pointer in the window's pixels, at its last move
        self.tabs = False                   # Alt held: a panel takes the card as a tab (R317)
        self.status = None                  # the status bar saying what Alt does, while the drag lasts
        self.said = ''
        self.dwell = QTimer(self)
        self.dwell.setSingleShot(True)
        self.dwell.timeout.connect(self._dwelt)
        title.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        kind = event.type()
        if self.solver is not None and kind == QEvent.Type.ShortcutOverride and event.key() == Qt.Key.Key_Escape:
            event.accept()                  # Esc is the drag's own: no window shortcut takes it first
            return True
        if self.solver is not None and kind == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self.finish(cancel=True)
            return True
        if (self.solver is not None and kind in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease) and
                event.key() == Qt.Key.Key_Alt):
            # Alt is the drag's own while it lasts (R317): tabs, at once, the pointer still. Not the window's: the
            # menus Alt shows and the page it pushes (AltMenus) see neither its press nor its release
            if not event.isAutoRepeat():
                self.tabs = kind == QEvent.Type.KeyPress
                self._track()
            return True
        if self.solver is not None and kind in _CANCEL and obj is self.dock.parentWidget():
            # Deactivated, hidden or moved to another pixel ratio: the pictures and the measuring
            # window no longer describe the window, and a hidden window drops the mouse grab.
            self.finish(cancel=True)
            return False
        if obj is not self.title:
            return False
        if kind == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            window = self.dock.parentWidget()
            if (self.dock.isFloating() or not self.dock.features() & QDockWidget.DockWidgetFeature.DockWidgetMovable
                    or (isinstance(window, QMainWindow) and window.centralWidget() is self.dock)):
                return False                # the central card is never dragged (R312)
            self.origin = event.globalPosition().toPoint()
            event.accept()
            return True
        if kind == QEvent.Type.MouseMove and self.origin is not None:
            point = event.globalPosition().toPoint()
            self.last_point = point
            if self.solver is None:
                if (point - self.origin).manhattanLength() < QApplication.startDragDistance():
                    return True
                window = self.dock.parentWidget()
                if not isinstance(window, QMainWindow) or self.dock.isFloating():
                    self.origin = None
                    return False
                self._take(window)
            window = self.dock.parentWidget()
            self.local = window.mapFromGlobal(point)
            self.lift.follow(self.local)    # the only thing that moves with the pointer
            # Alt read at every move, from the event and the application (held before the drag began); its press and
            # release, seen below, set it either way. A key eaten here leaves the application's modifiers behind
            if (event.modifiers() | QApplication.keyboardModifiers()) & Qt.KeyboardModifier.AltModifier:
                self.tabs = True
            self._track()
            return True
        if (kind == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton and
                self.origin is not None):           # a QPoint at the screen's origin is false
            self.finish()
            return True
        return False

    def _track(self) -> None:
        """The zone under the pointer, with Alt as it is now and with inertia (R317). Another panel, a band, Alt
        pressed or let go: answered after its dwell. The other half of the panel answered already: at once."""
        if self.solver is None or self.local is None:
            return
        here = self.pending if self.waiting else self.target
        wanted = _settled(self.dock.parentWidget(), self.dock, self.local, self.tabs, here)
        if wanted == self.target:
            self.waiting, self.pending = False, None
            self.dwell.stop()
        elif _same_card(wanted, self.target):
            self.waiting, self.pending = False, None
            self.dwell.stop()
            self._answer(wanted)
        elif self.waiting and _same_card(wanted, self.pending):
            self.pending = wanted           # the same panel waited for: its dwell goes on
        elif not self.waiting or wanted != self.pending:
            self.waiting, self.pending = True, wanted
            self.dwell.start(Motion.DWELL)

    def _take(self, window: QMainWindow) -> None:
        """The card lifted: the measuring window, the motion layer with the card's home slot, the picture."""
        self.solver = LayoutPreview(window, self.dock)
        self.layer = Reflow(window)
        self.layer.hold_open = True
        self.layer.drag = self
        self.lift = Lift(window, self.dock, self.origin)
        self.tabs = bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.AltModifier)
        self.layer.lift = self.lift
        self.layer.retarget(_placed(window), preview=self.dock, hold=True)
        QApplication.instance().installEventFilter(self)
        self.title.grabMouse()
        self.status = next((bar for bar in window.findChildren(QStatusBar, options=DIRECT) if bar.isVisible()), None)
        if self.status is not None:
            self.said = _("Alt: as tabs")
            self.status.showMessage(self.said)

    def _dwelt(self) -> None:
        if self.solver is None or not self.waiting:
            return
        zone, self.pending, self.waiting = self.pending, None, False
        self._answer(zone)

    def _answer(self, zone: DockTarget | None) -> None:
        """The zone shown: the cards make room for its slot, or go back home without one."""
        self.target = zone
        window = self.dock.parentWidget()
        ends = self.solver.solve(zone) if zone is not None else _placed(window)
        self.layer.retarget(ends, preview=self.dock, hold=True, ms=Motion.CAREFUL, lead=Motion.FAST)

    def finish(self, cancel: bool = False) -> None:
        origin, self.origin = self.origin, None
        if self.solver is None:
            return
        self.dwell.stop()
        self.waiting, self.pending = False, None
        QApplication.instance().removeEventFilter(self)
        self.title.releaseMouse()
        if self.status is not None and shiboken6.isValid(self.status) and self.status.currentMessage() == self.said:
            self.status.clearMessage()
        self.status = None
        window, dock = self.dock.parentWidget(), self.dock
        layer, lift, target, solver = self.layer, self.lift, self.target, self.solver
        self.solver = self.layer = self.lift = self.target = None
        layer.drag = None
        if not cancel and target is not None:
            slot = layer.card_rect(layer.ends.get(dock, layer.preview_rect))

            def land():
                # the layout changes only now, under the picture come to rest: the layer then goes from the slot
                # to the committed layout (the same rectangles, solved on a copy) and the picture dissolves
                if shiboken6.isValid(window) and shiboken6.isValid(layer):
                    layer.hold_open = False
                    reflow(window, lambda: commit_target(window, dock, target))
                if shiboken6.isValid(lift):
                    lift.dissolve()

            lift.fly(slot, land)
        elif (not cancel and self.last_point is not None and
              not window.rect().contains(window.mapFromGlobal(self.last_point)) and
              dock.features() & QDockWidget.DockWidgetFeature.DockWidgetFloatable):
            offset = origin - dock.mapToGlobal(QPoint())
            layer.hold_open = False
            layer.preview_source = None

            def float_dock():
                dock.setFloating(True)
                dock.move(self.last_point - offset)
                dock.show()

            lift.dissolve()
            reflow(window, float_dock)
        else:
            resting = _placed(window)
            layer.retarget(resting, preview=dock, hold=True, ms=Motion.CAREFUL)      # the cards back home

            def home():
                if shiboken6.isValid(layer):
                    layer.hold_open = False
                    layer.retarget(resting)         # the card's picture back in its slot, then the layer goes
                if shiboken6.isValid(lift):
                    lift.dissolve()

            lift.fly(layer.card_rect(resting[dock]), home)
        solver.close()
