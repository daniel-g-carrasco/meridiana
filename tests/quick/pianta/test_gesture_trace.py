"""Opt-in traces observe real input and render callbacks without changing delivery."""
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import _setup
from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPoint, QPointF, Qt
from PySide6.QtGui import QInputDevice, QNativeGestureEvent, QPointingDevice, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtQuick import QQuickWindow

from meridiana.gui.application import create_app

setUpModule = _setup.keep_global_state


class GestureTracing(unittest.TestCase):
    def test_a_swap_already_queued_when_the_trace_closes_is_ignored(self):
        from PySide6.QtCore import QMetaObject
        from meridiana.gui.backend.gesture_trace import GestureTrace
        app = create_app()
        window = QQuickWindow()
        with tempfile.TemporaryDirectory() as folder:
            trace = GestureTrace(window, Path(folder)/'closed.jsonl')
            QMetaObject.invokeMethod(trace, 'swapped', Qt.QueuedConnection)
            trace.close()
            sequence = trace.seq
            app.processEvents()
            self.assertEqual(trace.seq, sequence, 'a queued swap must not read the disposed plan or append rows')
        window.deleteLater()
        app.processEvents()

    def test_render_sync_never_reads_gui_owned_qml_properties(self):
        from meridiana.gui.backend.gesture_trace import GestureTrace
        app = create_app()
        window = QQuickWindow()
        with tempfile.TemporaryDirectory() as folder:
            trace = GestureTrace(window, Path(folder)/'trace.jsonl')
            gui_thread = threading.get_ident()
            original = trace.camera_state
            errors = []
            def guarded():
                if threading.get_ident() != gui_thread:
                    raise AssertionError('QML properties read from the render thread')
                return original()
            trace.camera_state = guarded
            def synchronize():
                try:
                    trace.before_sync()
                except Exception as error:
                    errors.append(str(error))
            thread = threading.Thread(target=synchronize)
            thread.start()
            thread.join()
            trace.close()
            self.assertEqual(errors, [])
        window.deleteLater()
        app.processEvents()

    def test_disabled_trace_has_no_observer_or_clock_work(self):
        from meridiana.gui.backend import gesture_trace
        app = create_app()
        window = QQuickWindow()
        with patch.dict(os.environ, {}, clear=True):
            count = len(window.children())
            with patch.object(gesture_trace.time, 'perf_counter_ns', side_effect=AssertionError('clock read')):
                self.assertIsNone(gesture_trace.install(window))
                QCoreApplication.sendEvent(window, QWheelEvent(
                    QPointF(20, 20), QPointF(20, 20), QPoint(), QPoint(0, 120),
                    Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False))
            self.assertEqual(len(window.children()), count)
        window.deleteLater()
        app.processEvents()

    def test_jsonl_contains_input_values_handling_and_render_durations(self):
        from meridiana.gui.backend import gesture_trace
        app = create_app()
        window = QQuickWindow()
        window.resize(300, 200)
        class ClosingFilter(QObject):
            armed = False

            def eventFilter(self, watched, event):
                if self.armed and event.type() == QEvent.Wheel:
                    trace.close()  # App shutdown can happen synchronously inside input delivery.
                return False
        closing = ClosingFilter(window)
        window.installEventFilter(closing)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'trace.jsonl'
            with patch.dict(os.environ, {'MERIDIANA_TRACE_GESTURES': str(path)}):
                trace = gesture_trace.install(window)
            try:
                window.show()
                self.assertTrue(_setup.wait_until(app, lambda: trace.frame_count > 0, 10))
                QCoreApplication.sendEvent(window, QWheelEvent(
                    QPointF(20, 30), QPointF(20, 30), QPoint(4, 7), QPoint(8, 14),
                    Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False))
                pad = QPointingDevice('trace pad', 9703, QInputDevice.TouchPad,
                                      QPointingDevice.Finger, QInputDevice.Position, 5, 0)
                point = QPointF(30, 40)
                for kind, value in ((Qt.BeginNativeGesture, 0), (Qt.ZoomNativeGesture, .025),
                                    (Qt.EndNativeGesture, 0)):
                    QCoreApplication.sendEvent(window, QNativeGestureEvent(
                        kind, pad, 2, point, point, point, value, QPointF()))
                QTest.mousePress(window, Qt.MiddleButton, Qt.NoModifier, QPoint(30, 40), 0)
                QTest.mouseMove(window, QPoint(40, 50), 0)
                QTest.mouseRelease(window, Qt.MiddleButton, Qt.NoModifier, QPoint(40, 50), 0)
                closing.armed = True
                QCoreApplication.sendEvent(window, QWheelEvent(
                    QPointF(20, 30), QPointF(20, 30), QPoint(), QPoint(0, -120),
                    Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False))
                window.update()
                _setup.turn_events(app, 80)
            finally:
                trace.close()
                window.close()
                window.deleteLater()
                app.processEvents()
            rows = [json.loads(line) for line in path.read_text(encoding='utf8').splitlines()]
            events = [r for r in rows if r['record'] == 'event']
            self.assertGreaterEqual(len(events), 6)
            self.assertEqual(events[0]['gesture'], 'scroll')
            self.assertEqual(events[0]['pixel_delta'], [4, 7])
            self.assertEqual(events[0]['position'], [20, 30])
            self.assertGreaterEqual(events[0]['gui_ms'], 0)
            native = [r for r in events if r.get('native_type') == 'ZoomNativeGesture']
            self.assertEqual(len(native), 1)
            self.assertAlmostEqual(native[0]['value'], .025)
            self.assertTrue(any(r['gesture'] == 'drag' for r in events))
            self.assertEqual(events[-1].get('angle_delta'), [0, -120], 'shutdown must flush the event that closed it')
            frames = [r for r in rows if r['record'] == 'frame']
            self.assertTrue(frames)
            for row in frames:
                for key in ('sync_ms', 'render_ms', 'render_frame_ms'):
                    if row['timing_available']:
                        self.assertGreaterEqual(row[key], 0)
                    else:
                        self.assertIsNone(row[key])
            self.assertEqual([r['seq'] for r in rows], list(range(len(rows))))
            self.assertEqual({r['version'] for r in rows}, {1})
            session = next(r for r in rows if r['record'] == 'session')
            self.assertGreater(session['refresh_hz'], 0)
            self.assertIn('screen_on', session)
            self.assertTrue(all(r['t_ns'] >= 0 for r in rows))
