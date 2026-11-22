"""R610 (Daniel 14/11/2026, Windows: «la relazione è molto lenta da scorrere, lo scrolling è più lento del normale»).

Measured on the real screen (Direct3D 11, ratio 2.5, Windows set to 4 lines a notch): a notch moves the report, a
page, the properties and a list by the same 96 px (Qt's Flickable: the system's lines times 24 px), with the same
300 ms of glide; two fingers on the touchpad (30 steps of 8 to 16, 295 px as backend/touchpad.py turns them into
pixels) moved them 21 to 52 px, a sixth: Qt 6.12's Flickable takes the pixels of an event «not synthesized», the
source Windows gives every WM_MOUSEWHEEL, for a mouse wheel's. Here the real report page and a common page
(M.ScrollPage) get the same Qt wheel events, as Windows gives them, through WindowsTouchpad: the same notch moves
them alike, and the same two fingers move both by the pixels they carry.

    python -m unittest quick.controlli.test_scorrimento_r610
"""
import os
import tempfile
import unittest

import _setup
from PySide6.QtCore import QObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QPointingDevice, QWheelEvent
from PySide6.QtQuick import QQuickView

from meridiana.gui.backend.controls import install_controls
from meridiana.gui.backend.touchpad import WINDOWS_PIXELS_PER_UNIT, WindowsTouchpad
from quick.gestures import pump, wait_for

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')

PAGE = b'''
import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M
Rectangle {
    width: 900; height: 600; color: Theme.colors.window
    M.ScrollPage { objectName: "page"; anchors.fill: parent
        Repeater { model: 300; Rectangle { width: 200; height: 24; color: index % 2 ? "#ccc" : "#eee" } } }
}
'''
STEPS = [-(8 + (k * 5) % 9) for k in range(30)]        # two fingers on a precision touchpad: 30 steps of 8 to 16


def setUpModule():
    _setup.keep_global_state()


class SameScroll(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        from _fixtures import capannone
        from meridiana.app.platform.config import Config
        from meridiana.app.session import ProjectSession
        from meridiana.gui.backend import report_pages
        from meridiana.gui.backend.report import ReportBackend
        cls.temp = tempfile.TemporaryDirectory()
        cls.backend = ReportBackend(ProjectSession(capannone()), Config(), paths={'cache': cls.temp.name})
        # a preview of 16 pages, as a finished preview publishes them (report.py, _finished)
        rows = [{'note': f'Page {n}', 'ratio': 297 / 210, 'page': str(n)} for n in range(1, 17)]
        cls.backend._pages, cls.backend._count = report_pages.publish(rows), len(rows)
        cls.report = QQuickView()
        install_controls(cls.report.engine())
        cls.report.setInitialProperties({'backend': cls.backend, 'showInspector': False})
        cls.report.setSource(QUrl.fromLocalFile(str(_setup.ROOT / 'src/meridiana/gui/qml/Meridiana/Report/ReportPage.qml')))
        assert cls.report.status() == QQuickView.Status.Ready, [e.toString() for e in cls.report.errors()]
        cls.report.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        cls.report.resize(900, 700)
        cls.file = tempfile.NamedTemporaryFile('wb', suffix='.qml', delete=False)
        cls.file.write(PAGE)
        cls.file.close()
        cls.page = QQuickView()
        install_controls(cls.page.engine())
        cls.page.setSource(QUrl.fromLocalFile(cls.file.name))
        assert cls.page.rootObject() is not None, cls.page.errors()
        for view in (cls.report, cls.page):
            view.show()
        wait_for(lambda: cls.report.isExposed() and cls.page.isExposed())
        cls.time = 10000

    @classmethod
    def tearDownClass(cls):
        for view in (cls.report, cls.page):
            view.close()
            view.deleteLater()
        cls.backend.close()
        pump(20)
        os.unlink(cls.file.name)
        cls.temp.cleanup()

    def areas(self):
        preview = self.report.rootObject().findChild(QObject, 'reportPreview')
        page = self.page.rootObject().findChild(QObject, 'page')
        return [(self.report, preview.property('contentItem')), (self.page, page.property('contentItem'))]

    def moved(self, view, flick, steps):
        """The content's way for Qt wheel events with the angles Windows gives (no pixels, no phase, the mouse as
        device), through the filter the window has (WindowsTouchpad)."""
        pad = WindowsTouchpad(active=True, source=lambda: None)
        view.installEventFilter(pad)
        self.addCleanup(view.removeEventFilter, pad)
        wait_for(lambda: flick.property('contentHeight') > flick.property('height') + 2000)
        flick.setProperty('contentY', 400)
        pump(20)
        start = flick.property('contentY')
        at = flick.mapToScene(QPointF(flick.property('width') / 2, flick.property('height') / 2))
        for step in steps:
            SameScroll.time += 10
            event = QWheelEvent(at, QPointF(view.mapToGlobal(at.toPoint())), QPoint(), QPoint(0, step),
                                Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase,
                                False, Qt.MouseEventSource.MouseEventNotSynthesized,
                                QPointingDevice.primaryPointingDevice())
            event.setTimestamp(SameScroll.time)
            self.app.sendEvent(view, event)
            pump(2)
        pad.end()                        # what its quiet timer does WINDOWS_STREAM_MS later
        wait_for(lambda: not flick.property('moving'), 5)
        return flick.property('contentY') - start

    def test_r610_a_notch_moves_the_report_as_a_common_page(self):
        moved = [self.moved(view, flick, [-120]) for view, flick in self.areas()]
        print('R610 notch: report, page', moved)
        self.assertGreater(moved[0], 0)
        self.assertAlmostEqual(moved[0], moved[1], delta=1)

    def test_r610_two_fingers_move_the_report_and_a_page_by_their_pixels(self):
        carried = -sum(STEPS) * WINDOWS_PIXELS_PER_UNIT
        moved = [self.moved(view, flick, STEPS) for view, flick in self.areas()]
        print('R610 touchpad: carried', round(carried), 'report, page', moved)
        self.assertAlmostEqual(moved[0], moved[1], delta=3)
        for way in moved:
            self.assertGreater(way, 0.85 * carried)
            self.assertLess(way, 1.05 * carried)


if __name__ == '__main__':
    unittest.main()
