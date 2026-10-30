"""Dock layout motion and geometry previews without changing the live layout.

A hidden, disposable QMainWindow solves the same docking operation as the real one.
The preview paints snapshots in those rectangles, leaving focus, visibility signals,
application state and jobs of the live window untouched until the drop is accepted.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QRect, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QApplication, QDockWidget, QMainWindow, QStatusBar, QTabBar, QToolBar, QWidget)

from . import motion
from .cards import EDGE, GAP, CardDock, arena, default_tokens
from .design import Motion, Radius, Space

DIRECT = Qt.FindChildOption.FindDirectChildrenOnly


def cards(window: QMainWindow) -> list[QWidget]:
    return [*window.findChildren(QDockWidget, options=DIRECT), window.centralWidget()]


def _docked(widget: QWidget | None) -> bool:
    """A card the window lays out: a floating panel is a window of its own, its geometry on the screen."""
    return widget is not None and not widget.isHidden() and not (
        isinstance(widget, QDockWidget) and widget.isFloating())


def _settle_layout(window: QMainWindow) -> None:
    """Resolve card margins synchronously, without dispatching unrelated application jobs."""
    for _ in range(6):
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
        extent = size.width() if orientation == Qt.Orientation.Horizontal else size.height()
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


def cancel_drags(window: QMainWindow) -> None:
    """No drag of a panel, no preview and no motion layer left over the cards: before a layout is put back."""
    for dock in window.findChildren(CardDock, options=DIRECT):
        drag = getattr(dock, 'drag_motion', None)
        if drag is not None and drag.solver is not None:
            drag.finish(cancel=True)
    for layer in window.findChildren(Reflow, options=DIRECT):
        layer.drag = None
        layer.hold_open = False
        layer.animation.stop()
        layer.hide()
        layer.deleteLater()


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
        return {real: QRect(dummy.geometry()) for real, dummy in self.copies.items()
                if not dummy.isHidden() and (not isinstance(dummy, QDockWidget) or not dummy.isFloating())}

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
        self.drag = None                    # the DockDrag holding this layer open, if any
        self.generation = 0
        motion._RESPONSIVE.add(self)
        self.show()
        self.raise_()

    def rectangles(self) -> dict[QWidget, QRect]:
        t = self.progress
        result = {}
        for widget, end in self.ends.items():
            start = self.starts.get(widget, end)
            result[widget] = QRect(*(round(a + (b - a) * t) for a, b in
                                    zip(start.getRect(), end.getRect(), strict=True)))
        return result

    def retarget(self, ends: dict[QWidget, QRect], *, edge: str = 'right', preview=None,
                 hold: bool = False) -> None:
        self.starts = self.rectangles()
        self.animation.stop()
        self.hold_open = hold
        self.preview_source = preview
        self.preview_rect = QRect(ends.get(preview, QRect()))
        # The live window is already in its final state for a collapse or a committed drop.
        # Hide only our layer while grabbing newly opened cards, never any actual panel.
        self.hide()
        for widget, end in ends.items():
            if widget not in self.pictures:
                self.pictures[widget] = motion.picture(widget)
                self.inners[widget] = widget.card_rect() if isinstance(widget, CardDock) else widget.contentsRect()
                self.starts[widget] = _collapsed(end, edge)
        self.show()
        self.raise_()
        self.ends = {widget: QRect(ends.get(widget, _collapsed(start, edge)))
                     for widget, start in self.starts.items()}
        self.progress = 0.0
        self.animation.setDuration(0 if motion.reduced() else Motion.FAST)
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
            self._step(1.0)
            self._settled()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.translate(-self.x(), -self.y())
        theme = getattr(self.host, 'theme', None)
        tokens = theme.tokens if theme is not None else default_tokens()
        p.fillRect(self.geometry(), QColor(tokens['window']))
        positions = self.rectangles()

        def card_rect(rect):
            room = self.geometry()
            return rect.adjusted(EDGE if abs(rect.left() - room.left()) <= 2 else 0,
                                 GAP if abs(rect.top() - room.top()) <= 2 else 0,
                                 -EDGE if abs(rect.right() - room.right()) <= 2 else 0,
                                 -GAP if rect.bottom() >= room.bottom() - 2 else 0)

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
            r = QRectF(card_rect(positions.get(self.preview_source, self.preview_rect))).adjusted(1, 1, -1, -1)
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


def _covered(window: QMainWindow) -> bool:
    """A page over the cards (File, an entrance playing over it): the change happens under it and there is
    nothing to show; a layer raised over it would cut the page into the cards' pictures. A small overlay, such as
    a floating assistant, does not count."""
    room = arena(window)
    shown = set(cards(window))
    siblings = [child for child in window.children() if isinstance(child, QWidget)]
    top = max((i for i, widget in enumerate(siblings) if widget in shown), default=-1)
    for widget in siblings[top + 1:]:
        if isinstance(widget, Reflow) or widget.isWindow() or not widget.isVisible():
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
        ends = {widget: QRect(widget.geometry()) for widget in cards(window) if _docked(widget)}
        layer.retarget(ends, edge=edge)

    motion.after_work(layer, settle)
    return layer


def target_at(window: QMainWindow, source: QDockWidget, point: QPoint) -> DockTarget | None:
    room = arena(window)
    if not room.contains(point):
        return None
    distances = ((point.x() - room.left(), Qt.DockWidgetArea.LeftDockWidgetArea),
                 (room.right() - point.x(), Qt.DockWidgetArea.RightDockWidgetArea),
                 (point.y() - room.top(), Qt.DockWidgetArea.TopDockWidgetArea),
                 (room.bottom() - point.y(), Qt.DockWidgetArea.BottomDockWidgetArea))
    distance, area = min(distances, key=lambda pair: pair[0])
    if distance < Space.XXL and source.allowedAreas() & area:
        return DockTarget(area)
    for anchor in window.findChildren(QDockWidget, options=DIRECT):
        if anchor is source or anchor.isHidden() or anchor.isFloating() or not anchor.geometry().contains(point):
            continue
        area = window.dockWidgetArea(anchor)
        if not source.allowedAreas() & area:
            continue
        r = anchor.geometry()
        x, y = (point.x() - r.left()) / r.width(), (point.y() - r.top()) / r.height()
        distance, side = min((x, 'left'), (1 - x, 'right'), (y, 'top'), (1 - y, 'bottom'))
        if distance > 0.25:
            return DockTarget(area, anchor, tab=True)
        return DockTarget(area, anchor, Qt.Orientation.Horizontal if side in ('left', 'right')
                          else Qt.Orientation.Vertical, before=side in ('left', 'top'))
    centre = window.centralWidget()
    if centre is not None and centre.geometry().contains(point):
        r = centre.geometry()
        sides = ((point.x() - r.left(), Qt.DockWidgetArea.LeftDockWidgetArea),
                 (r.right() - point.x(), Qt.DockWidgetArea.RightDockWidgetArea),
                 (point.y() - r.top(), Qt.DockWidgetArea.TopDockWidgetArea),
                 (r.bottom() - point.y(), Qt.DockWidgetArea.BottomDockWidgetArea))
        distance, area = min(sides, key=lambda pair: pair[0])
        if distance < Space.XXXL * 2 and source.allowedAreas() & area:
            return DockTarget(area)
    return None


_CANCEL = (QEvent.Type.WindowDeactivate, QEvent.Type.Hide, QEvent.Type.DevicePixelRatioChange)


class DockDrag(QObject):
    """Title dragging with an exact target and animated neighbouring card geometry."""

    def __init__(self, dock: QDockWidget, title: QWidget):
        super().__init__(title)
        self.dock, self.title = dock, title
        self.origin = None
        self.solver = None
        self.layer = None
        self.target = None
        self.last_point = None
        title.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        kind = event.type()
        if self.solver is not None and kind == QEvent.Type.ShortcutOverride and event.key() == Qt.Key.Key_Escape:
            event.accept()                  # Esc is the drag's own: no window shortcut takes it first
            return True
        if self.solver is not None and kind == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self.finish(cancel=True)
            return True
        if self.solver is not None and kind in _CANCEL and obj is self.dock.parentWidget():
            # Deactivated, hidden or moved to another pixel ratio: the pictures and the measuring
            # window no longer describe the window, and a hidden window drops the mouse grab.
            self.finish(cancel=True)
            return False
        if obj is not self.title:
            return False
        if kind == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            if self.dock.isFloating() or not self.dock.features() & QDockWidget.DockWidgetFeature.DockWidgetMovable:
                return False
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
                self.solver = LayoutPreview(window, self.dock)
                self.layer = Reflow(window)
                self.layer.hold_open = True
                self.layer.drag = self
                QApplication.instance().installEventFilter(self)
                self.title.grabMouse()
            window = self.dock.parentWidget()
            target = target_at(window, self.dock, window.mapFromGlobal(point))
            if target != self.target:
                self.target = target
                ends = self.solver.solve(target) if target is not None else self.layer.starts
                self.layer.retarget(ends, preview=self.dock if target is not None else None, hold=True)
            return True
        if (kind == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton and
                self.origin is not None):           # a QPoint at the screen's origin is false
            self.finish()
            return True
        return False

    def finish(self, cancel: bool = False) -> None:
        origin, self.origin = self.origin, None
        if self.solver is None:
            return
        QApplication.instance().removeEventFilter(self)
        self.title.releaseMouse()
        window = self.dock.parentWidget()
        self.layer.hold_open = False
        self.layer.drag = None
        self.layer.preview_source = None
        if not cancel and self.target is not None:
            # Finish from the visible preview rectangles to the committed layout.
            reflow(window, lambda: apply_target(window, self.dock, self.target))
        elif (not cancel and self.last_point is not None and
              not window.rect().contains(window.mapFromGlobal(self.last_point)) and
              self.dock.features() & QDockWidget.DockWidgetFeature.DockWidgetFloatable):
            offset = origin - self.dock.mapToGlobal(QPoint())

            def float_dock():
                self.dock.setFloating(True)
                self.dock.move(self.last_point - offset)
                self.dock.show()

            reflow(window, float_dock)
        else:
            ends = {widget: QRect(widget.geometry()) for widget in cards(window) if _docked(widget)}
            self.layer.retarget(ends)
        self.solver.close()
        self.solver = self.layer = self.target = None
