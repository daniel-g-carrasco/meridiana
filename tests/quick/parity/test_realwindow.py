"""R389/R392: native frame evidence and detectors with injected faults."""
import os
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, QUrl, Slot
from PySide6.QtGui import QColor, QImage
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from quick.gestures import drag
from quick.parity.realwindow import (Frame, FrameRecorder, PythonCalls, assert_frames,
                                     native_app, require_native, wait_frames)


def painted_frame(number=0, *, blank=False, rect=(10, 10, 40, 30), tops=()):
    image = QImage(80, 60, QImage.Format.Format_RGB32)
    image.fill(QColor('white'))
    if not blank:
        for y in range(10, 40):
            for x in range(10, 50):
                image.setPixelColor(x, y, QColor('navy'))
    return Frame(number, float(number), image, {'marker': list(rect)}, tuple(tops))


class FrameDetectorTest(unittest.TestCase):
    def test_detects_blank_disappearing_region_jump_and_popup(self):
        good = painted_frame()
        assert_frames([good, painted_frame(1)], stable={'marker': 1}, regions={'content': (5, 5, 50, 40)})
        for bad, message in [(painted_frame(1, blank=True), 'blank'),
                             (painted_frame(1, rect=(20, 10, 40, 30)), 'jump'),
                             (painted_frame(1, tops=('unwanted',)), 'top-level')]:
            with self.subTest(message=message), self.assertRaisesRegex(AssertionError, message):
                assert_frames([good, bad], stable={'marker': 1}, regions={'content': (5, 5, 50, 40)})
        with self.assertRaisesRegex(AssertionError, 'disappeared'):
            assert_frames([Frame(1, 0, good.image, {}, ())], stable={'marker': 1})

    def test_detects_region_loss_even_if_rest_of_window_is_not_blank(self):
        first = painted_frame()
        second = painted_frame(1)
        for y in range(10, 40):
            for x in range(10, 30):
                second.image.setPixelColor(x, y, QColor('white'))
        with self.assertRaisesRegex(AssertionError, 'region'):
            assert_frames([first, second], regions={'left': (5, 5, 25, 40)})

    def test_empty_capture_and_invalid_region_are_failures(self):
        with self.assertRaisesRegex(AssertionError, 'No frames'):
            assert_frames([])
        with self.assertRaisesRegex(ValueError, 'outside'):
            assert_frames([painted_frame()], regions={'bad': (100, 0, 10, 10)})

    def test_python_probe_detects_calls_without_bridge_instrumentation(self):
        def callback():
            return 1
        with PythonCalls(files=[__file__]) as counter:
            for _ in range(8):
                callback()
        self.assertEqual(counter.calls['callback'], 8)
        with self.assertRaisesRegex(AssertionError, 'Python'):
            counter.assert_no_calls()


QML = b'''
import QtQuick
Window {
    id: root
    width: 320; height: 240; visible: false; color: "#eeeeee"
    objectName: "fixtureWindow"
    property real offset: 0
    Rectangle { objectName: "marker"; x: 20; y: 20; width: 120; height: 80; color: "navy"
        Text { objectName: "markerLabel"; anchors.centerIn: parent; text: "Native frame"; color: "white"; font.pixelSize: 14 }
    }
    Rectangle { x: 20 + root.offset; y: 150; width: 40; height: 40; color: "orange" }
    MouseArea { anchors.fill: parent; property real start: 0
        onPressed: function(mouse) { start = mouse.x }
        onPositionChanged: function(mouse) { if (pressed) root.offset = mouse.x-start }
    }
}
'''


@unittest.skipUnless(os.environ.get('MERIDIANA_QUICK_NATIVE') == '1',
                     'Native GPU evidence requires MERIDIANA_QUICK_NATIVE=1; offscreen is not native evidence')
class NativeFrameTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = native_app()
        require_native(cls.app)
        Path('build').mkdir(exist_ok=True)

    def setUp(self):
        self.engine = QQmlApplicationEngine()
        self.engine.loadData(QML, QUrl('file:///native-parity-fixture.qml'))
        self.window = self.engine.rootObjects()[0]
        self.window.show()
        self.assertTrue(QTest.qWaitForWindowExposed(self.window, 5000))

    def tearDown(self):
        self.window.close()
        self.engine.deleteLater()
        self.app.processEvents()

    def test_real_frames_and_synthetic_continuous_drag(self):
        with FrameRecorder(self.window, names=['marker']) as recorder:
            wait_frames(recorder, 2)
            with PythonCalls() as calls:
                drag(self.app, self.window, QPointF(180, 180), QPointF(220, 180), steps=8)
            wait_frames(recorder, len(recorder.frames)+1)
        self.assertAlmostEqual(self.window.property('offset'), 40, delta=1)
        calls.assert_no_calls()
        recorder.assert_valid(stable={'marker': 1}, regions={'marker': (15, 15, 130, 90)})
        self.assertEqual(recorder.unexpected_windows, [])
        with tempfile.TemporaryDirectory(dir=Path('build')) as temporary:
            manifest = recorder.save(Path(temporary))
            self.assertEqual(manifest['capture'], 'QQuickWindow.frameSwapped -> grabWindow')
            self.assertGreaterEqual(manifest['frames'], 3)

    def test_named_tree_reports_actual_logical_rect_font_and_color(self):
        from quick.parity.geometry import capture_quick
        snap = capture_quick(self.window, scenario='fixture')
        items = {row['id']: row for row in snap['widgets']}
        self.assertEqual(items['marker']['rect'], [20, 20, 120, 80])
        self.assertEqual(items['markerLabel']['font']['pixel_size'], 14)
        self.assertEqual(items['markerLabel']['colors']['text'], '#ffffffff')
        self.assertEqual(items['markerLabel']['text'], 'Native frame')

    def test_pixel_font_uses_the_same_resolved_metrics_as_widgets(self):
        from PySide6.QtGui import QFontInfo
        from quick.parity.geometry import capture_quick
        label = self.window.findChild(QObject, 'markerLabel')
        font = label.property('font')
        font.setPixelSize(13)
        label.setProperty('font', font)
        resolved = QFontInfo(font)
        row = next(row for row in capture_quick(self.window)['widgets'] if row['id'] == 'markerLabel')
        self.assertEqual(row['font'], {'family': resolved.family(), 'pixel_size': resolved.pixelSize(),
                                      'point_size': resolved.pointSizeF(), 'weight': int(font.weight()),
                                      'italic': font.italic()})
        self.assertGreater(row['font']['point_size'], 0)

    def test_short_lived_popup_after_last_frame_is_still_rejected(self):
        from PySide6.QtQuick import QQuickWindow
        with FrameRecorder(self.window) as recorder:
            wait_frames(recorder, 2)
            popup = QQuickWindow()
            popup.setObjectName('transientFileWindow')
            popup.show()
            popup.hide()
        with self.assertRaisesRegex(AssertionError, 'transientFileWindow'):
            recorder.assert_valid()
        popup.close()

    def test_python_probe_catches_a_qml_callback_on_every_drag_step(self):
        class FaultProbe(QObject):
            @Slot()
            def tick(self):
                return None
        probe = FaultProbe()
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty('faultProbe', probe)
        faulty_qml = QML.replace(b'if (pressed) root.offset',
                                b'if (pressed) faultProbe.tick(); if (pressed) root.offset')
        engine.loadData(faulty_qml, QUrl('file:///native-fault-callback.qml'))
        window = engine.rootObjects()[0]
        window.show()
        try:
            self.assertTrue(QTest.qWaitForWindowExposed(window, 5000))
            with PythonCalls(files=[__file__]) as calls:
                drag(self.app, window, QPointF(180, 180), QPointF(220, 180), steps=8)
            self.assertGreaterEqual(calls.calls['tick'], 8)
            with self.assertRaisesRegex(AssertionError, 'Python'):
                calls.assert_no_calls()
        finally:
            window.close()
            engine.deleteLater()
            self.app.processEvents()

    def test_real_blank_and_unexpected_top_level_are_caught(self):
        from PySide6.QtQuick import QQuickWindow
        with FrameRecorder(self.window, names=['marker']) as recorder:
            wait_frames(recorder, 2)
            marker = self.window.findChild(type(self.window.contentItem()), 'marker')
            marker.setVisible(False)
            self.window.setProperty('offset', -1000)
            popup = QQuickWindow()
            popup.setObjectName('unexpectedFileWindow')
            popup.resize(80, 60)
            popup.show()
            wait_frames(recorder, len(recorder.frames)+2)
            popup.close()
        self.assertTrue(recorder.unexpected_windows)
        with self.assertRaises(AssertionError):
            assert_frames(recorder.frames, stable={'marker': 1}, regions={'marker': (15, 15, 130, 90)})


@unittest.skipUnless(os.environ.get('MERIDIANA_QUICK_NATIVE') == '1',
                     'Prototype transitions require native GPU; offscreen is not native evidence')
class NativePrototypeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = native_app()
        from meridiana.quick.app import create_app
        create_app()

    def test_prototype_pan_and_phase_transitions_keep_content_and_panels(self):
        from _fixtures import capannone
        from meridiana import jobs
        from meridiana.quick.app import QuickWindow
        from quick.gestures import click, item, point, pump
        from PySide6.QtCore import Qt
        destination = Path('build/quick-foto/compat')
        destination.mkdir(parents=True, exist_ok=True)
        output = Path(tempfile.mkdtemp(prefix='native-prototype-', dir=destination))
        with tempfile.TemporaryDirectory(dir=Path('build')) as temporary:
            host = QuickWindow(capannone(), Path(temporary))
            try:
                window = host.window
                results, keys, _ = jobs.layout_of(host.bridge.session.project)
                host.bridge.accept_layout(0, results, keys)
                window.show()
                self.assertTrue(QTest.qWaitForWindowExposed(window, 5000))
                pump(80)
                plan = item(window, 'plan')
                before = plan.property('panX')
                with FrameRecorder(window, names=['leftPanel', 'rightPanel', 'checksPanel']) as recorder:
                    wait_frames(recorder, 2)
                    with PythonCalls() as calls:
                        drag(self.app, window, point(plan), point(plan)+QPointF(50, 20),
                             steps=8, button=Qt.MouseButton.MiddleButton)
                    calls.assert_no_calls()
                    self.assertAlmostEqual(plan.property('panX')-before, 50, delta=1)
                    for tab, phase in [('productionTab', 'production'), ('modelTab', 'model')]:
                        click(self.app, window, point(item(window, tab)))
                        wait_frames(recorder, len(recorder.frames)+3)
                        self.assertEqual(window.property('phase'), phase)
                        pump(200)
                recorder.assert_valid(stable={'leftPanel': 1, 'rightPanel': 1, 'checksPanel': 1},
                                      regions={'project': (20, 110, 280, 250), 'properties': (1250, 110, 300, 250)})
                self.assertEqual(recorder.unexpected_windows, [])
                self.assertGreater(host.bridge.moduleCount, 0)
                self.assertEqual(plan.property('paintedModules'), host.bridge.moduleCount)
                image = recorder.frames[-1].image
                origin = point(plan, 0, 0)
                dpr = image.devicePixelRatio()
                blue = 0
                for y in range(int(origin.y()+4), int(origin.y()+plan.height()-4), 4):
                    for x in range(int(origin.x()+4), int(origin.x()+plan.width()-4), 4):
                        color = image.pixelColor(int((x+.5)*dpr), int((y+.5)*dpr))
                        blue += color.blue() > color.red()+10 and color.red() < 100
                self.assertGreater(blue, 100, 'Modules must remain visibly painted after pan and both phase changes')
                recorder.save(output)
                self.assertEqual(host.warnings, [])
                print('Native prototype frame evidence:', output, flush=True)
            finally:
                host.close()
                self.app.processEvents()
