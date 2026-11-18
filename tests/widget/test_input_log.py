"""The optional raw input log: the same facts Qt gives Meridiana on Windows and on Wayland."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup

setUpModule = _setup.keep_global_state


class InputLog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from PySide6.QtWidgets import QWidget
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "input.jsonl"
        self.widget = QWidget()
        self.addCleanup(self.widget.deleteLater)

    def attach(self):
        from meridiana.ui import input_log
        with mock.patch.dict(os.environ, {"MERIDIANA_INPUT_LOG": str(self.path)}):
            logger = input_log.attach(self.widget, "plan")
        self.assertIsNotNone(logger)
        return logger

    def records(self):
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]

    def test_wheel_gesture_key_and_mouse_keep_the_raw_event_fields(self):
        from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
        from PySide6.QtGui import QKeyEvent, QMouseEvent, QNativeGestureEvent, QPointingDevice, QWheelEvent
        from PySide6.QtWidgets import QApplication
        self.attach()
        at = QPointF(31.5, 42.25)
        global_at = QPointF(self.widget.mapToGlobal(at.toPoint()))
        events = [
            QWheelEvent(at, global_at, QPoint(3, -7), QPoint(120, -240), Qt.MouseButton.NoButton,
                        Qt.KeyboardModifier.ControlModifier, Qt.ScrollPhase.ScrollUpdate, False,
                        Qt.MouseEventSource.MouseEventSynthesizedBySystem),
            QNativeGestureEvent(Qt.NativeGestureType.ZoomNativeGesture, QPointingDevice.primaryPointingDevice(), 2,
                                at, at, global_at, 0.125, QPointF()),
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier, " ", True, 3),
            QMouseEvent(QEvent.Type.MouseMove, at, global_at, Qt.MouseButton.LeftButton,
                        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier),
        ]
        for event in events:
            QApplication.sendEvent(self.widget, event)
        wheel, gesture, override, key, mouse = self.records()
        self.assertEqual([r["type"] for r in self.records()],
                         ["Wheel", "NativeGesture", "ShortcutOverride", "KeyPress", "MouseMove"])
        self.assertEqual(override["key"], "Key_Space")
        self.assertTrue(all(r["surface"] == "plan" and r["time"].endswith("Z") for r in self.records()))
        self.assertEqual(wheel["angleDelta"], {"x": 120, "y": -240})
        self.assertEqual(wheel["pixelDelta"], {"x": 3, "y": -7})
        self.assertEqual(wheel["phase"], "ScrollUpdate")
        self.assertEqual(wheel["source"], "MouseEventSynthesizedBySystem")
        self.assertEqual(wheel["position"], {"x": 31.5, "y": 42.25})
        self.assertEqual(wheel["globalPosition"], {"x": global_at.x(), "y": global_at.y()})
        self.assertIn("ControlModifier", wheel["modifiers"])
        self.assertEqual(gesture["gesture"], "ZoomNativeGesture")
        self.assertEqual(gesture["value"], 0.125)
        self.assertEqual(key["key"], "Key_Space")
        self.assertEqual(key["text"], " ")
        self.assertTrue(key["autoRepeat"])
        self.assertEqual(key["count"], 3)
        self.assertEqual(mouse["button"], "LeftButton")
        self.assertIn("LeftButton", mouse["buttons"])
        self.assertIn("ShiftModifier", mouse["modifiers"])

    def test_the_plan_and_3d_views_log_the_events_sent_to_their_actual_recipients(self):
        from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
        from PySide6.QtGui import QKeyEvent, QWheelEvent
        from PySide6.QtWidgets import QApplication

        from _fixtures import view3d
        from meridiana.ui.plan import PlanView
        with mock.patch.dict(os.environ, {"MERIDIANA_INPUT_LOG": str(self.path)}):
            plan = PlanView(Path(self.folder.name))
            self.addCleanup(plan.deleteLater)
            self.addCleanup(plan.close)
            scene, _results = view3d(self)
        for view in (plan, scene):
            QApplication.sendEvent(view, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Space,
                                                   Qt.KeyboardModifier.NoModifier))
            at = QPointF(20, 30)
            target = plan.viewport() if view is plan else view
            QApplication.sendEvent(target, QWheelEvent(at, QPointF(target.mapToGlobal(at.toPoint())), QPoint(),
                                                       QPoint(0, 120), Qt.MouseButton.NoButton,
                                                       Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase,
                                                       False))
        self.assertEqual([(r["surface"], r["type"]) for r in self.records()],
                         [("plan", "ShortcutOverride"), ("plan", "KeyPress"), ("plan", "Wheel"),
                          ("3d", "ShortcutOverride"), ("3d", "KeyPress"), ("3d", "Wheel")])

    def test_without_the_variable_no_file_or_logger_is_made(self):
        from meridiana.ui import input_log
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(input_log.attach(self.widget, "3d"))
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
