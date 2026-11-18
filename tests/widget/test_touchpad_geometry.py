"""Pointer anchors use logical coordinates through the real widget/viewport event paths."""
import unittest

import numpy as np
import _setup
from _fixtures import plan_view, view3d
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QInputDevice, QNativeGestureEvent, QPointingDevice, QWheelEvent

setUpModule = _setup.keep_global_state


class TouchpadGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        cls.device = QPointingDevice("Test touchpad", 91, QInputDevice.DeviceType.TouchPad,
                                    QPointingDevice.PointerType.Finger,
                                    QInputDevice.Capability.Position, 5, 0)

    def native(self, receiver, at, kind, *, value=0.0, delta=None):
        event = QNativeGestureEvent(kind, self.device, 2, at, at,
                                    receiver.mapToGlobal(at), value, delta if delta is not None else QPointF())
        self.app.sendEvent(receiver, event)
        self.assertTrue(event.isAccepted())

    def wheel(self, receiver, at, *, pixel=None, angle=None, ctrl=False):
        event = QWheelEvent(at, receiver.mapToGlobal(at), pixel if pixel is not None else QPoint(),
                            angle if angle is not None else QPoint(), Qt.MouseButton.NoButton,
                            Qt.KeyboardModifier.ControlModifier if ctrl else Qt.KeyboardModifier.NoModifier,
                            Qt.ScrollPhase.NoScrollPhase, False,
                            Qt.MouseEventSource.MouseEventNotSynthesized, self.device)
        self.app.sendEvent(receiver, event)
        self.assertTrue(event.isAccepted())

    def test_plan_fractional_cursor_and_inverse_pinch_keep_the_same_scene_point(self):
        plan, _ = plan_view(self)
        plan.rotate_view(37)
        at = QPointF(211.25, 172.75)
        before = plan.viewportTransform().inverted()[0].map(at)
        scale = plan.metres_per_pixel()
        for value in (0.25, -0.2):
            self.native(plan.viewport(), at, Qt.NativeGestureType.ZoomNativeGesture, value=value)
            actual = plan.viewportTransform().inverted()[0].map(at)
            self.assertLess((actual - before).manhattanLength(), 1e-7)
        self.assertAlmostEqual(plan.metres_per_pixel(), scale)
        for angle in (QPoint(0, 60), QPoint(0, -60)):
            self.wheel(plan.viewport(), at, angle=angle, ctrl=True)
            actual = plan.viewportTransform().inverted()[0].map(at)
            self.assertLess((actual - before).manhattanLength(), 1e-7)

    def test_unphased_real_touchpad_pan_is_one_pixel_per_pixel_on_rotated_plan(self):
        plan, _ = plan_view(self)
        plan.rotate_view(53)
        at = QPointF(211.25, 172.75)
        point = plan.viewportTransform().inverted()[0].map(at)
        scale = plan.metres_per_pixel()
        self.wheel(plan.viewport(), at, pixel=QPoint(31, -17), angle=QPoint(120, -60))
        after = plan.viewportTransform().map(point)
        self.assertAlmostEqual(after.x() - at.x(), 31, delta=1e-6)
        self.assertAlmostEqual(after.y() - at.y(), -17, delta=1e-6)
        self.assertEqual(plan.metres_per_pixel(), scale)

    def test_native_pan_keeps_fractional_deltas_in_both_views(self):
        plan, _ = plan_view(self)
        view, _ = view3d(self)
        at = QPointF(211.25, 172.75)
        point2d = plan.viewportTransform().inverted()[0].map(at)
        point3d = view.backend.camera.zoom_point(at.x(), at.y(), *view.backend.size)
        for _ in range(8):
            for receiver in (plan.viewport(), view):
                self.native(receiver, at, Qt.NativeGestureType.PanNativeGesture, delta=QPointF(0.5, -0.25))
        after2d = plan.viewportTransform().map(point2d)
        after3d = view.backend.camera.project(point3d, *view.backend.size)
        self.assertAlmostEqual(after2d.x() - at.x(), 4, delta=1e-6)
        self.assertAlmostEqual(after2d.y() - at.y(), -2, delta=1e-6)
        self.assertTrue(np.allclose(after3d, (at.x() + 4, at.y() - 2), atol=1e-6))

    def test_3d_unphased_device_pan_and_inverse_pinch_keep_cursor_anchor(self):
        view, _ = view3d(self)
        b = view.backend
        at = QPointF(211.25, 172.75)
        point = b.camera.zoom_point(at.x(), at.y(), *b.size)
        self.wheel(view, at, pixel=QPoint(31, -17), angle=QPoint(120, -60))
        self.assertTrue(np.allclose(b.camera.project(point, *b.size), (at.x() + 31, at.y() - 17), atol=1e-6))
        for ortho in (False, True):
            b.camera.ortho = ortho
            point = b.camera.zoom_point(at.x(), at.y(), *b.size)
            for value in (0.25, -0.2):
                self.native(view, at, Qt.NativeGestureType.ZoomNativeGesture, value=value)
                self.assertTrue(np.allclose(b.camera.project(point, *b.size), (at.x(), at.y()), atol=1e-6))

    def test_a_view_change_inside_an_unphased_scroll_takes_a_new_pan_depth(self):
        """Review B: a standard view chosen while two fingers scroll (before the 180 ms pause) kept the depth
        of the old camera, and the pan no longer followed the fingers."""
        from meridiana import camera
        view, _ = view3d(self)
        b = view.backend
        w, h = b.size
        b.touch_pan(5, 0, 400, 300)
        turned = b.camera.copy()
        turned.rotation = camera.look((b.camera.bearing() + 180) % 360, b.camera.elevation())
        turned.position = turned.target - turned.forward() * float(np.linalg.norm(b.camera.target - b.camera.position))
        b.go(turned, animate=False)
        point = b.camera.zoom_point(400, 300, w, h)
        b.touch_pan(20, 0, 400, 300)
        self.assertTrue(np.allclose(b.camera.project(point, w, h), (420, 300), atol=1e-6))

    def test_wheel_without_a_pick_or_with_a_stale_pick_behind_the_camera_keeps_the_cursor_anchor(self):
        """The sky (no pick) and a pick of an older frame now behind the camera fall back to the ground or
        the target's plane under the current ray."""
        view, _ = view3d(self)
        b = view.backend
        w, h = b.size
        at = (211.25, 172.75)
        for hit in (None, b.camera.position - b.camera.forward() * 50.0):
            anchor = b.camera.zoom_point(*at, w, h)
            point = (0.0, 0.0, 0.0) if hit is None else tuple(hit)
            b.wheel(1, 0, *at, hit is not None, *point)
            self.assertTrue(np.allclose(b.camera.project(anchor, w, h), at, atol=1e-6))

    def test_wheel_uses_current_cursor_ray_when_pick_came_from_previous_frame(self):
        view, _ = view3d(self)
        b = view.backend
        at = QPointF(211.25, 172.75)
        for ortho in (False, True):
            b.camera.ortho = ortho
            old_pick = b.camera.zoom_point(at.x(), at.y(), *b.size)
            # The render-control frame has not caught up with this preceding gesture yet.
            b.touch_zoom(1, 500, 380)
            anchor = b.camera.zoom_point(at.x(), at.y(), *b.size)
            for step in (1, -1):
                b.wheel(step, 0, at.x(), at.y(), True, *old_pick)
                self.assertTrue(np.allclose(b.camera.project(anchor, *b.size),
                                            (at.x(), at.y()), atol=1e-6), ortho)
