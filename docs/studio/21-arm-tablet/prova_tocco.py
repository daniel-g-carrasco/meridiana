"""Study 21 (R87): what Meridiana's views do today with a finger, offscreen, without changing the code.

Sends QTouchEvents (a touch screen, not a touchpad) to the plan (ui/plan.py) and to the 3D view (ui/view3d.py)
with Qt's test API and reports what changed: a one-finger tap (does it select, as a click?), a two-finger pinch
(does the zoom change?), a two-finger drag (does the view pan?). Then opens the main window and counts the
visible buttons smaller than the touch targets Windows asks for (40 x 40 px recommended, 23 x 23 minimum:
learn.microsoft.com, "Guidelines for touch targets" and "Touch" in the Win32 UX guide).

Run from the repository root, with the tests' helpers on the path:

    set PYTHONUTF8=1 && set QT_QPA_PLATFORM=offscreen && set PYTHONPATH=tests;src
    python docs/studio/21-arm-tablet/prova_tocco.py
"""

from __future__ import annotations

import math
import sys
import unittest

import _setup  # noqa: F401  (tests/_setup.py: src on the path, offscreen, temporary home)
import _fixtures

from PySide6.QtCore import QEvent, QObject, QPoint, Qt
from PySide6.QtGui import QInputDevice, QPointingDevice
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractButton, QApplication


def finger_device() -> QPointingDevice:
    """A touch screen Qt knows about. A QPointingDevice built by hand is not registered with the window system
    interface and its events go nowhere (tried: nothing reached even a plain QWidget with WA_AcceptTouchEvents);
    QTest.createTouchDevice registers it."""
    return QTest.createTouchDevice(QInputDevice.DeviceType.TouchScreen)


def scale_of(plan) -> float:
    return math.hypot(plan.transform().m11(), plan.transform().m21())


def centre_of_module(plan) -> QPoint:
    """A point of the viewport over a module of the shed: the middle of the first module's quad."""
    for r in plan.drawn[1].values():
        if r is not None and not isinstance(r, Exception) and len(r.table):
            q = r.table[0]
            x, y = float(q[0:8:2].mean()), float(q[1:8:2].mean())
            from meridiana.ui.plan import to_scene
            return plan.mapFromScene(to_scene(x, y))
    return plan.viewport().rect().center()


class Recorder(QObject):
    """Which events reach a widget: touch ones, mouse ones (synthesized or not), gestures."""

    WATCHED = {QEvent.Type.TouchBegin: "TouchBegin", QEvent.Type.TouchUpdate: "TouchUpdate",
               QEvent.Type.TouchEnd: "TouchEnd", QEvent.Type.MouseButtonPress: "MousePress",
               QEvent.Type.MouseButtonRelease: "MouseRelease", QEvent.Type.MouseMove: "MouseMove",
               QEvent.Type.Gesture: "Gesture", QEvent.Type.NativeGesture: "NativeGesture"}

    def __init__(self):
        super().__init__()
        self.seen = []

    def eventFilter(self, obj, event):
        name = self.WATCHED.get(event.type())
        if name:
            source = ""
            if name.startswith("Mouse"):
                source = {Qt.MouseEventSource.MouseEventSynthesizedByQt: " (synthesized by Qt)",
                          Qt.MouseEventSource.MouseEventSynthesizedBySystem: " (synthesized by the system)",
                          Qt.MouseEventSource.MouseEventSynthesizedByApplication: " (by the application)"
                          }.get(event.source(), "")
            self.seen.append(name + source)
        return False

    def summary(self) -> str:
        out, last, n = [], None, 0
        for s in self.seen + [None]:
            if s == last:
                n += 1
                continue
            if last is not None:
                out.append(last if n == 1 else f"{last} x{n}")
            last, n = s, 1
        return ", ".join(out) or "nothing"


class Touch(unittest.TestCase):
    """Not assertions on what should happen: a record of what happens (the study's point)."""

    def setUp(self):
        self.app = _setup.qt_or_skip()
        self.device = finger_device()
        self.notes = []

    def record(self, widget) -> Recorder:
        rec = Recorder()
        widget.installEventFilter(rec)
        self.addCleanup(widget.removeEventFilter, rec)
        return rec

    def say(self, text: str) -> None:
        self.notes.append(text)
        print(text, flush=True)

    def test_plan(self):
        plan, _results = _fixtures.plan_view(self, _fixtures.capannone())
        viewport = plan.viewport()
        rec = self.record(viewport)
        before_sel = plan.selection
        at = centre_of_module(plan)
        seq = QTest.touchEvent(viewport, self.device)
        seq.press(0, at, viewport)
        seq.commit()
        seq = QTest.touchEvent(viewport, self.device)
        seq.release(0, at, viewport)
        seq.commit()
        self.app.processEvents()
        self.say(f"plan, one-finger tap on a module: selection {before_sel} -> {plan.selection} "
                 f"(accept touch events: {viewport.testAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)}); "
                 f"events at the viewport: {rec.summary()}")
        rec.seen.clear()

        before = scale_of(plan)
        c = viewport.rect().center()
        a, b = c + QPoint(-20, 0), c + QPoint(20, 0)
        seq = QTest.touchEvent(viewport, self.device)
        seq.press(0, a, viewport).press(1, b, viewport)
        seq.commit()
        for step in range(1, 11):
            seq = QTest.touchEvent(viewport, self.device)
            seq.move(0, a + QPoint(-8 * step, 0), viewport).move(1, b + QPoint(8 * step, 0), viewport)
            seq.commit()
        seq = QTest.touchEvent(viewport, self.device)
        seq.release(0, a + QPoint(-80, 0), viewport).release(1, b + QPoint(80, 0), viewport)
        seq.commit()
        self.app.processEvents()
        self.say(f"plan, two-finger pinch (20 px -> 100 px apart): scale {before:.4f} -> {scale_of(plan):.4f}, "
                 f"selection now {plan.selection}; events: {rec.summary()}")
        rec.seen.clear()

        t0 = plan.transform()
        before_dx, before_dy = t0.dx(), t0.dy()
        seq = QTest.touchEvent(viewport, self.device)
        seq.press(0, a, viewport).press(1, b, viewport)
        seq.commit()
        for step in range(1, 11):
            seq = QTest.touchEvent(viewport, self.device)
            seq.move(0, a + QPoint(0, 10 * step), viewport).move(1, b + QPoint(0, 10 * step), viewport)
            seq.commit()
        seq = QTest.touchEvent(viewport, self.device)
        seq.release(0, a + QPoint(0, 100), viewport).release(1, b + QPoint(0, 100), viewport)
        seq.commit()
        self.app.processEvents()
        t1 = plan.transform()
        self.say(f"plan, two-finger drag down 100 px: translation ({before_dx:.1f}, {before_dy:.1f}) -> "
                 f"({t1.dx():.1f}, {t1.dy():.1f}), selection now {plan.selection}; events: {rec.summary()}")

        # for comparison: the same tap as a mouse click (what a pen or a mouse does)
        plan.selection = ("", "")
        QTest.mouseClick(viewport, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, at)
        self.app.processEvents()
        self.say(f"plan, a mouse click at the same point: selection {plan.selection}")

    def test_view3d(self):
        view, _results = _fixtures.view3d(self, _fixtures.capannone())
        backend = view.backend
        picked = []
        view.modulePicked.connect(lambda i: picked.append(("module", i)))
        view.buildingPicked.connect(lambda: picked.append(("building",)))
        view.pointPicked.connect(lambda x, y: picked.append(("point", round(x, 1), round(y, 1))))
        c = view.rect().center()
        cam0 = backend.camera.copy()
        rec = self.record(view)
        seq = QTest.touchEvent(view, self.device)
        seq.press(0, c, view)
        seq.commit()
        self.app.processEvents()
        held = set(backend.navigator.held)
        seq = QTest.touchEvent(view, self.device)
        seq.release(0, c, view)
        seq.commit()
        _setup.wait_until(self.app, lambda: bool(picked), 3)
        self.say(f"3D, one-finger tap at the centre: buttons the navigator saw held {held or '{}'}, picked {picked}, "
                 f"accept touch events: {view.testAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)}; "
                 f"events at the view: {rec.summary()}")
        rec.seen.clear()
        picked.clear()
        QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, c)
        _setup.wait_until(self.app, lambda: bool(picked), 3)
        self.say(f"3D, a mouse click at the same point, for comparison: picked {picked}")
        rec.seen.clear()

        a, b = c + QPoint(-20, 0), c + QPoint(20, 0)
        seq = QTest.touchEvent(view, self.device)
        seq.press(0, a, view).press(1, b, view)
        seq.commit()
        for step in range(1, 11):
            seq = QTest.touchEvent(view, self.device)
            seq.move(0, a + QPoint(-8 * step, 0), view).move(1, b + QPoint(8 * step, 0), view)
            seq.commit()
        seq = QTest.touchEvent(view, self.device)
        seq.release(0, a + QPoint(-80, 0), view).release(1, b + QPoint(80, 0), view)
        seq.commit()
        self.app.processEvents()
        cam1 = backend.camera
        import numpy as np
        moved = not (np.allclose(cam0.position, cam1.position, atol=1e-6) and np.allclose(cam0.target, cam1.target, atol=1e-6))
        self.say(f"3D, two-finger pinch: camera position {np.round(cam0.position, 2)} -> {np.round(cam1.position, 2)}, "
                 f"camera moved: {moved}; events: {rec.summary()}")

    def test_buttons_of_the_window(self):
        from unittest import mock
        with mock.patch.object(_setup, "wait_until", wraps=_setup.wait_until):
            win = _setup.window(self, _fixtures.capannone())
        self.app.processEvents()
        small, tiny, total = [], [], 0
        for b in win.findChildren(QAbstractButton):
            if not b.isVisible():
                continue
            total += 1
            w, h = b.width(), b.height()
            if w < 23 or h < 23:
                tiny.append((b.objectName() or type(b).__name__, w, h, b.text()[:20]))
            elif w < 40 or h < 40:
                small.append((b.objectName() or type(b).__name__, w, h, b.text()[:20]))
        self.say(f"main window at 1200 x 800: {total} visible buttons; {len(small)} between 23 and 40 px on a side, "
                 f"{len(tiny)} under 23 px on a side (Windows' minimum)")
        for name, w, h, text in sorted(tiny, key=lambda t: (t[1], t[2]))[:12]:
            self.say(f"  under 23 px: {name} {w} x {h} {text!r}")
        sizes = sorted({(w, h) for _n, w, h, _t in small})
        self.say(f"  sizes between 23 and 40 px: {sizes[:12]}")


if __name__ == "__main__":
    print("Qt", QApplication.instance().applicationVersion() if QApplication.instance() else "", file=sys.stderr)
    unittest.main(verbosity=1)
