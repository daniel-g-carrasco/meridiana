"""R359: 26 directions and real pointer gestures of the Quick view cube."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PySide6.QtCore import QObject, QPoint, QUrl, Qt
from PySide6.QtGui import QImage
from PySide6.QtQml import QJSEngine
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication

import _setup
from meridiana.app.view import camera, navicube

ROOT = Path(__file__).resolve().parents[3]
QML = ROOT / "src/meridiana/gui/qml/Meridiana/View3D"
APP = QApplication.instance() or QApplication([])
setUpModule = _setup.keep_global_state


class CubeMathTest(unittest.TestCase):
    def setUp(self):
        self.engine = QJSEngine()
        source = (QML / "CubeMath.js").read_text(encoding="utf-8")
        result = self.engine.evaluate(source.replace(".pragma library", ""))
        self.assertFalse(result.isError(), result.toString())

    def call(self, name, *args):
        result = self.engine.evaluate(f"JSON.stringify({name}({','.join(json.dumps(a) for a in args)}))")
        self.assertFalse(result.isError(), result.toString())
        return json.loads(result.toString())

    def test_every_direction_matches_widgets(self):
        for bearing in (0, 30, 45, 135, 225, 315):
            cam = camera.Camera(rotation=camera.look(bearing, -35))
            for part in navicube.parts():
                with self.subTest(bearing=bearing, part=part):
                    got = self.call("lookingFrom", part, bearing)
                    expected = navicube.looking_from(part, cam)
                    for actual, wanted in zip(got, expected, strict=True):
                        self.assertAlmostEqual(actual, wanted, places=7)

    def test_projected_cells_and_picking_match_widgets(self):
        seen = set()
        for bearing in range(0, 360, 45):
            for elevation in (-90, -35, 0, 35, 90):
                cam = camera.Camera(rotation=camera.look(bearing, elevation))
                cells = self.call("cells", bearing, elevation, 64)
                expected = navicube.faces(cam, 64)
                self.assertEqual(len(cells), len(expected))
                for cell in cells:
                    part = tuple(cell["part"])
                    seen.add(part)
                    x = sum(p[0] for p in cell["polygon"]) / 4
                    y = sum(p[1] for p in cell["polygon"]) / 4
                    self.assertEqual(self.call("pick", cells, x, y), list(navicube.pick(cam, 64, x, y)))
        self.assertEqual(seen, set(navicube.parts()))

    def test_r643_sign_of_north_points_where_the_camera_shows_north(self):
        """R643: the 3D view's sign of North turns to where the scene's North (-z) falls on the screen, as the
        Widgets' camera projects it; looking North (bearing 0) it points up, whatever the height."""
        import math
        north = [0.0, 0.0, -1.0]
        for bearing in (0, 30, 90, 135, 200, 315):
            for elevation in (-89, -60, -35, -10):
                cam = camera.Camera(rotation=camera.look(bearing, elevation))
                right, up = cam.right(), cam.up()
                x = sum(a * b for a, b in zip(north, right, strict=True))
                y = sum(a * b for a, b in zip(north, up, strict=True))
                expected = math.degrees(math.atan2(x, y))
                got = self.call("screenNorth", bearing, elevation)
                with self.subTest(bearing=bearing, elevation=elevation):
                    self.assertAlmostEqual((got - expected + 180) % 360 - 180, 0, places=6)
        for elevation in (-80, -35, -5):
            self.assertAlmostEqual(self.call("screenNorth", 0, elevation), 0, places=9)

    def test_arrow_limits_and_plan_bearing(self):
        self.assertEqual(self.call("turned", 330, -80, "right"), [15, -80])
        self.assertEqual(self.call("turned", 30, -80, "up"), [30, -90])
        self.assertEqual(self.call("turned", 30, 80, "down"), [30, 90])
        self.assertEqual(self.call("lookingFrom", [0, 1, 0], 140), [180, -90])


class CubeEventsTest(unittest.TestCase):
    def setUp(self):
        self.view = QQuickView()
        from meridiana.gui.backend.controls import install_controls
        self.view.engine().addImportPath(str(QML.parents[1]))
        self.theme = install_controls(self.view.engine())
        self.view.setSource(QUrl.fromLocalFile(str(QML / "ViewCube.qml")))
        self.assertEqual(self.view.status(), QQuickView.Status.Ready, str(self.view.errors()))
        self.view.show()
        QTest.qWait(50)
        self.cube = self.view.rootObject()

    def tearDown(self):
        self.view.close()
        self.view.deleteLater()
        APP.processEvents()

    def test_compact_cube_orients_and_has_no_menu_target(self):
        self.assertEqual(self.cube.width(), 76)
        self.assertEqual(self.cube.height(), 76)
        self.assertIsNone(self.cube.findChild(QObject, "viewCubeMenu"))
        orient = QSignalSpy(self.cube.orientRequested)
        QTest.mouseClick(self.view, Qt.MouseButton.LeftButton, pos=QPoint(38, 38))
        self.assertEqual(orient.count(), 1)
        from ._fidelity_support import js
        self.assertEqual(js(self.cube, "hit(67,68)"), "")
        QTest.mouseClick(self.view, Qt.MouseButton.LeftButton, pos=QPoint(67, 68))
        self.assertEqual(orient.count(), 1)
        image = self.view.grabWindow()
        dpr = image.devicePixelRatio()
        background = image.pixelColor(round(74*dpr), round(74*dpr))
        for x in range(63, 73):
            for y in range(66, 73):
                self.assertEqual(image.pixelColor(round(x*dpr), round(y*dpr)), background,
                                 "The removed menu arrow must leave the corner empty")

    def test_hover_on_faces_edges_and_corners_uses_common_neutral_colour(self):
        from ._fidelity_support import data, js
        self.assertTrue(js(self.cube, "Qt.colorEqual(hoverColor, Theme.colors.hover)"))
        self.assertEqual(self.cube.property("drawingOpacity"), 1)
        cells = data(self.cube, "projectedCells")
        for count in (1, 2, 3):
            cell = next(c for c in cells if sum(v != 0 for v in c["part"]) == count)
            x = 38 + sum(p[0] for p in cell["polygon"]) / 4
            y = 38 + sum(p[1] for p in cell["polygon"]) / 4
            QTest.mouseMove(self.view, QPoint(1, 1))
            QTest.qWait(30)
            before = self.view.grabWindow()
            QTest.mouseMove(self.view, QPoint(round(x), round(y)))
            QTest.qWait(30)
            self.assertEqual(self.cube.property("hoverTarget"), "part:" + ",".join(map(str, cell["part"])))
            after = self.view.grabWindow()
            self.assertNotEqual(before, after, cell["part"])

    def test_all_26_parts_receive_real_clicks(self):
        seen = set()
        orient = QSignalSpy(self.cube.orientRequested)
        for bearing in range(0, 360, 45):
            for elevation in (-90, -35, 0, 35, 90):
                self.cube.setProperty("bearing", bearing)
                self.cube.setProperty("elevation", elevation)
                cam = camera.Camera(rotation=camera.look(bearing, elevation))
                for part, polygon, _depth in navicube.faces(cam, 64):
                    if part in seen:
                        continue
                    x = 38 + sum(p[0] for p in polygon) / 4
                    y = 38 + sum(p[1] for p in polygon) / 4
                    before = orient.count()
                    QTest.mouseClick(self.view, Qt.MouseButton.LeftButton, pos=QPoint(round(x), round(y)))
                    self.assertEqual(orient.count(), before + 1, part)
                    wanted = navicube.looking_from(part, cam)
                    for actual, expected in zip(orient.at(before), wanted, strict=True):
                        self.assertAlmostEqual(actual, expected, places=7)
                    seen.add(part)
        self.assertEqual(seen, set(navicube.parts()))

    def test_double_click_still_fits_the_drawing(self):
        self.cube.setProperty("bearing", 0)
        self.cube.setProperty("elevation", 0)
        fit = QSignalSpy(self.cube.fitRequested)
        QTest.mouseDClick(self.view, Qt.MouseButton.LeftButton, pos=QPoint(38, 38))
        self.assertEqual(fit.count(), 1)


@unittest.skipUnless(sys.platform == "win32" and os.environ.get("QT_QPA_PLATFORM") != "offscreen",
                     "First native D3D11 grab is a Windows integration check")
class CubeNativePixelsTest(unittest.TestCase):
    def test_first_scene_grab_has_faces_not_only_letters(self):
        # The original Canvas passed all gestures but lost its first texture in
        # the real View3D host. Native Shape paths must fill these same targets.
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, QT_QPA_PLATFORM="windows", QSG_RENDER_LOOP="threaded", QT_SCALE_FACTOR="1")
            result = subprocess.run([sys.executable, str(ROOT / "tools/models_scene_probe.py"), "--out", tmp],
                                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=40)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            image = QImage(str(Path(tmp) / "1366x900-s1-light.png"))
            self.assertFalse(image.isNull())
            background = image.pixelColor(1242, 40)
            filled = sum(image.pixelColor(x, y).red() > background.red() + 20
                         for x in range(1274, 1322) for y in range(44, 98))
            self.assertGreater(filled, 600, "Cube faces disappeared while labels remained")


if __name__ == "__main__":
    unittest.main()
