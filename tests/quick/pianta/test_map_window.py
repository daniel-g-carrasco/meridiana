"""R21/R149/R191/R389: maps installed in the actual PlanController and Plan QML."""

import base64
import os
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault('QSG_RENDER_LOOP', 'basic')

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, QPoint, Qt, QUrl
from PySide6.QtGui import QColor, QGuiApplication, QImage
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from meridiana import geo, model
from meridiana.quick.backend.plan import PlanController
from meridiana.underlay import Underlay


class MapWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def wait(self, condition):
        deadline = time.monotonic() + 8
        while not condition() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.002)
        self.assertTrue(condition())

    def setUp(self):
        self.cache = tempfile.TemporaryDirectory()
        image = QImage(20, 10, QImage.Format.Format_RGB32)
        image.fill(QColor('#dd4933'))
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, 'PNG')
        self.project = model.Project(name='Isolated map fixture', site=model.Site(45.5226, 9.03))
        self.project.underlays = [Underlay('u', image=base64.b64encode(data).decode(), width=20, height=10,
                                          scale=1, x=-10, y=5, opacity=1)]
        self.controller = PlanController(self.project, cache=Path(self.cache.name))
        self.controller.maps.configure(offline=True)
        self.controller.maps.setSource('none')
        self.engine = QQmlApplicationEngine()
        self.errors = []
        self.engine.warnings.connect(lambda errors: self.errors.extend(error.toString() for error in errors))
        self.controller.install(self.engine)
        self.engine.rootContext().setContextProperty('planBackend', self.controller)
        root = Path(__file__).resolve().parents[3] / 'src/meridiana/quick/qml/Meridiana/Plan/PlanWindow.qml'
        self.engine.load(QUrl.fromLocalFile(str(root)))
        self.assertTrue(self.engine.rootObjects(), self.errors)
        self.window = self.engine.rootObjects()[0]
        self.wait(lambda: self.window.isExposed())
        self.plan = self.window.findChild(QObject, 'plan')
        self.wait(lambda: self.controller.calls['viewSettled'] > 0)

    def tearDown(self):
        self.window.close()
        self.controller.close()
        self.engine.deleteLater()
        self.app.processEvents()
        self.cache.cleanup()

    def test_project_site_and_underlays_follow_session_edits_and_undo(self):
        maps = self.controller.maps
        self.assertEqual(maps.state.origin, geo.Origin(45.5226, 9.03))
        self.assertEqual(maps.underlays[0]['matrix'][7], -5)
        self.controller.session.edit('Move underlay', lambda p: setattr(p.underlays[0], 'y', 15))
        self.assertEqual(maps.underlays[0]['matrix'][7], -15)
        self.controller.key('Z', '', 1)
        self.assertEqual(maps.underlays[0]['matrix'][7], -5)
        self.controller.session.edit('Change site', lambda p: setattr(p.site, 'lon', 11.35))
        self.assertEqual(maps.state.origin, geo.Origin(45.5226, 11.35))
        self.assertFalse(self.errors, self.errors)

    def test_real_pan_keeps_the_background_and_settles_once_without_python_pointer_updates(self):
        self.plan.setProperty('zoom', 10)
        self.plan.setProperty('panX', 500)
        self.plan.setProperty('panY', 400)
        self.wait(lambda: self.controller.maps.state.mpp == .1)
        self.controller.calls.clear()
        QTest.mousePress(self.window, Qt.MiddleButton, Qt.NoModifier, QPoint(500, 400))
        for x in range(505, 566, 5):
            QTest.mouseMove(self.window, QPoint(x, 400), 1)
        QTest.mouseRelease(self.window, Qt.MiddleButton, Qt.NoModifier, QPoint(565, 400))
        self.wait(lambda: self.controller.calls['viewSettled'] >= 1)
        self.assertEqual(self.controller.calls['viewSettled'], 1)
        self.assertEqual(self.controller.calls['pointer'], 0)
        grab = self.window.grabWindow()
        dpr = grab.devicePixelRatio()
        px, py = float(self.plan.property('panX')), float(self.plan.property('panY'))
        self.assertEqual(grab.pixelColor(round(px * dpr), round(py * dpr)).name(), '#dd4933')
        folder = Path('build/quick-foto/pianta')
        folder.mkdir(parents=True, exist_ok=True)
        grab.save(str(folder / f'map-window-pan-{dpr:g}x.png'))
        self.assertFalse(self.errors, self.errors)

    def test_plan_zoom_enters_world_then_restores_local_underlay(self):
        self.plan.setProperty('zoom', 1 / 35000)
        self.plan.setProperty('panX', self.window.width() / 2)
        self.plan.setProperty('panY', self.window.height() / 3)
        self.wait(lambda: self.controller.maps.equalEarth)
        self.assertFalse(self.controller.maps.state.wanted)
        self.assertEqual(self.controller.maps.attribution, 'Natural Earth')
        grab = self.window.grabWindow()
        colors = {grab.pixelColor(x, y).name() for x in range(0, grab.width(), 8)
                  for y in range(0, grab.height(), 8)}
        self.assertIn('#52665b', colors)
        self.assertNotIn('#dd4933', colors)
        self.plan.setProperty('zoom', 10)
        self.wait(lambda: not self.controller.maps.equalEarth)
        grab = self.window.grabWindow()
        dpr = grab.devicePixelRatio()
        px, py = float(self.plan.property('panX')), float(self.plan.property('panY'))
        self.assertEqual(grab.pixelColor(round(px * dpr), round(py * dpr)).name(), '#dd4933')
        # Returning from the world must not leave hundreds of invisible labels
        # following every subsequent local pan and zoom.
        from quick.gestures import item
        labels = item(self.window, 'mapCountryLabels')
        self.assertEqual(labels.property('count'), 0)
        self.assertEqual(item(self.window, 'mapCountryPaths').property('count'), 0)
        self.assertFalse(self.errors, self.errors)


if __name__ == '__main__':
    unittest.main()
