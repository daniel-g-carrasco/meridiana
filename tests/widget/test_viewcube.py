"""The view cube of the 3D view alone (study 12, T1-T3): at the top right of the view at any size, its faces computed
once a frame, a face that looks from its side, a double click that frames the scene, the arrows and the compass's
letters that turn the view, Home and «Set this view as Home», the parallel projection from its menu; and the outline
of the selection that stays a few pixels wide when the camera comes closer. The 3D view is made alone with the shed
(_fixtures.view3d); the selection shared by the two views is in finestra/test_selection_3d.py. PySide6 and a display
(offscreen will do)."""

import unittest

import numpy as np

import _setup
from _fixtures import capannone, view3d

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class Cube(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.project = capannone()
        self.view, self.results = view3d(self, self.project)
        self.b = self.view.backend
        self.cube = self.view.cube

    def test_the_cube_sits_at_the_top_right_of_the_3d_view(self):
        v = self.view
        self.assertIs(self.cube.parentWidget(), v)

        def corner():
            """The cube's gaps to the right and the top of the view: a few pixels each, never off or in the middle."""
            g = self.cube.geometry()
            return v.width() - 1 - g.right(), g.top()
        for size in ((800, 600), (420, 640)):               # it follows the view when the view is resized
            v.resize(*size)
            self.app.processEvents()
            right, top = corner()
            self.assertTrue(0 < right <= 12 and 0 < top <= 12, (size, right, top))
            self.assertTrue(v.rect().contains(self.cube.geometry()))      # whole inside the view

    def test_the_cube_stays_its_size_and_what_is_round_it_takes_less(self):
        """R359, measured: 150 x 150 px of widget before, 137 x 137 drawn; the cube itself 64 across."""
        import numpy as np

        from meridiana import navicube
        from meridiana.ui import viewcube
        self.assertEqual(viewcube.CUBE, 64)
        self.cube.fit_view(1600, 900)
        self.assertLessEqual(self.cube.width() * self.cube.height(), 0.6 * 150 * 150)
        cells = navicube.faces(self.b.camera, viewcube.CUBE)
        reach = max(float(np.hypot(x, y)) for _p, poly, _d in cells for x, y in poly)
        self.assertLess(reach, self.cube.width() / 2)        # the cube whole inside it
        for name, poly in self.cube.arrows().items():        # each arrow inside and small, with a wider place to click
            box = poly.boundingRect()
            self.assertTrue(self.cube.rect().toRectF().contains(box), name)
            self.assertEqual(self.cube.at(box.center()), ("arrow", name))

    def test_a_small_view_takes_the_compact_cube_with_home_in_its_menu(self):
        from PySide6.QtGui import QResizeEvent

        from meridiana.ui import viewcube
        self.assertTrue(viewcube.compact_for(500, 400))
        self.assertFalse(viewcube.compact_for(1000, 600))
        self.view.resize(500, 400)
        self.view.resizeEvent(QResizeEvent(self.view.size(), self.view.size()))
        cube = self.cube
        self.assertTrue(cube.compact)
        self.assertEqual((cube.width(), cube.height()), (viewcube.COMPACT_SIZE, viewcube.COMPACT_SIZE))
        self.assertEqual(cube.at(cube.centre())[0], "part")
        self.assertEqual(cube.at(cube.menu_rect().center()), ("menu",))
        self.assertNotEqual(cube.at(cube.home_rect().center()), ("home",))
        cube.grab()
        words = [a.text() for a in cube.menu().actions()]
        self.assertIn("Go to Home", words)
        self.assertTrue(self.view.rect().contains(cube.geometry()))
        self.view.resize(1000, 700)
        self.view.resizeEvent(QResizeEvent(self.view.size(), self.view.size()))
        self.assertFalse(cube.compact)
        self.assertNotIn("Go to Home", [a.text() for a in cube.menu().actions()])
        cube.grab()

    def test_a_press_on_its_empty_corners_is_the_views(self):
        from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
        from PySide6.QtGui import QMouseEvent
        cube = self.cube
        cube.fit_view(1600, 900)
        empty = QPointF(cube.width() - 1.0, 1.0)
        self.assertIsNone(cube.at(empty))
        event = QMouseEvent(QEvent.Type.MouseButtonPress, empty, QPointF(cube.mapToGlobal(QPoint(0, 0))),
                            Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        cube.mousePressEvent(event)
        self.assertFalse(event.isAccepted())

    def test_a_frame_of_the_cube_computes_its_faces_once_and_none_when_nothing_changed(self):
        """R120: the 3D view under it paints every frame; the cube is drawn again only when the view turned."""
        from unittest import mock

        from meridiana import navicube
        self.cube.picture = None
        with mock.patch.object(navicube, "faces", wraps=navicube.faces) as faces:
            self.cube.grab()                                # one paint
            self.assertEqual(faces.call_count, 1)
            self.cube.grab()                                # the same view: the picture kept
            self.assertEqual(faces.call_count, 1)
            cam = self.cube.backend.camera
            cam.rotation = cam.rotation[[1, 0, 2, 3]].copy()     # the view turned
            self.cube.grab()
            self.assertEqual(faces.call_count, 2)

    def test_a_face_looks_from_its_side_and_a_double_click_frames_the_scene(self):
        self.cube.click(("part", (0, 0, 1)))               # the South face
        self.assertAlmostEqual(self.b.camera.bearing() % 360, 0.0, places=4)
        self.assertAlmostEqual(self.b.camera.elevation(), 0.0, places=4)
        self.b.wheel(6.0, 0, 50, 50, False, 0, 0, 0)        # somewhere else
        self.cube.click(("part", (1, 1, 0)), double=True)  # the edge of top and East, framed
        self.assertAlmostEqual(self.b.camera.bearing(), 270.0, places=4)
        self.assertAlmostEqual(self.b.camera.elevation(), -45.0, places=4)
        self.assertTrue(np.allclose(self.b.camera.target, self.b.scene[0]))

    def test_what_the_pointer_is_on(self):
        c = self.cube.centre()
        self.cube.click(("part", (0, 1, 0)))               # from above, North up
        what = self.cube.at(c)
        self.assertEqual(what, ("part", (0, 1, 0)))
        self.assertEqual(self.cube.at(self.cube.home_rect().center()), ("home",))
        self.assertEqual(self.cube.at(self.cube.arrows()["left"].boundingRect().center()), ("arrow", "left"))

    def test_the_arrows_and_the_letters_turn_the_view(self):
        self.cube.click(("part", (0, 0, 1)))
        self.cube.click(("arrow", "right"))
        self.assertAlmostEqual(self.b.camera.bearing(), 45.0, places=4)
        self.cube.click(("letter", "E"))                    # from the East
        self.assertAlmostEqual(self.b.camera.bearing(), 270.0, places=4)

    def test_home_and_set_this_view_as_home(self):
        self.cube.click(("part", (-1, 0, 0)))
        self.b.set_home()
        self.cube.click(("part", (0, 0, 1)))
        self.cube.click(("home",))
        self.assertAlmostEqual(self.b.camera.bearing(), 90.0, places=4)    # the view from the West, set as Home

    def test_the_menu_switches_to_a_parallel_view(self):
        from PySide6.QtCore import QObject
        menu = self.cube.menu()
        texts = [a.text() for a in menu.actions()]
        self.assertEqual(len(texts), 3)
        menu.actions()[0].trigger()
        self.assertTrue(self.b.ortho)
        view = self.view.rootObject().findChild(QObject, "parallel")
        self.assertGreater(view.property("horizontalMagnification"), 0)
        self.b.set_ortho(False)

    def test_the_outline_stays_a_few_pixels_wide_when_the_camera_comes_closer(self):
        from meridiana import viewaids
        v = self.view
        # the building selected, outlined as the window outlines it (MainWindow._outline_3d)
        v.set_outline(viewaids.outline(self.project, self.results, "building", "b1"), np.zeros((0, 2, 3)))
        before = v.outline_pixel
        self.assertGreater(before, 0)
        cam = self.b.camera.copy()
        cam.position = cam.target + (cam.position - cam.target) * 0.25
        self.b.camera = cam
        self.b.cameraChanged.emit()
        self.assertLess(v.outline_pixel, before * 0.5)


if __name__ == "__main__":
    unittest.main()
