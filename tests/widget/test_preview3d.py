"""The 3D preview of the dialogs (ui/preview3d.py, R282, study 22, 3.8) and its use in «Building from a template»
and «Parking canopy»: the projection of known cases, a click on a pill that opens its field, the measure written
that reaches the dialog's field and changes the shape, Esc that gives up without closing the dialog, a measure
refused, the drawing in the light and the dark theme. PySide6 and a display (offscreen will do)."""

import math
import unittest

import _setup

setUpModule = _setup.keep_global_state


class Projection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def preview(self):
        from meridiana.ui.preview3d import Preview3D, prism
        p = Preview3D()
        self.addCleanup(p.deleteLater)
        p.resize(400, 300)
        p.show_scene(prism([(0, 0), (10, 0), (10, 10), (0, 10)], 0, 4))
        return p

    def test_from_the_south_west_east_goes_right_north_left_and_up_goes_up(self):
        p = self.preview()
        o, east, north, up = (p.project(q) for q in ((0, 0, 0), (10, 0, 0), (0, 10, 0), (0, 0, 4)))
        self.assertGreater(east.x(), o.x())
        self.assertLess(east.y(), o.y())            # the South-West corner is the nearest: lowest on the screen
        self.assertLess(north.x(), o.x())
        self.assertAlmostEqual(north.y(), east.y(), places=6)
        self.assertAlmostEqual(up.x(), o.x(), places=6)   # verticals stay vertical
        self.assertLess(up.y(), o.y())
        # 45° from the South-West: the two sides of the square drawn equally long, mirrored
        self.assertAlmostEqual(east.x() - o.x(), o.x() - north.x(), places=6)

    def test_from_the_south_a_side_along_x_is_horizontal_and_its_length_is_kept(self):
        p = self.preview()
        p.turn(180.0, 30.0)
        a, b, top = p.project((0, 0, 0)), p.project((10, 0, 0)), p.project((0, 0, 4))
        self.assertAlmostEqual(a.y(), b.y(), places=6)
        scale = (b.x() - a.x()) / 10
        self.assertAlmostEqual((a.y() - top.y()) / scale, 4 * math.cos(math.radians(30)), places=6)
        # a turn of the view keeps the scale: the fit is on the scene's sphere
        p.turn(250.0, 50.0)
        c, d = p.project((0, 0, 0)), p.project((0, 0, 4))
        self.assertAlmostEqual((c.y() - d.y()) / scale, 4 * math.cos(math.radians(50)), places=6)

    def test_the_walls_seen_from_behind_are_not_drawn_and_a_box_is_a_structure(self):
        from meridiana.ui.preview3d import box, normal
        faces = box((0, 0), (0.3, 0.3, 2.5))
        self.assertEqual({f.kind for f in faces}, {"structure"})
        self.assertEqual(len(faces), 5)
        self.assertTrue(all(normal(f.points)[2] > 0 for f in faces if f.points[0][2] == f.points[1][2] == 2.5))
        p = self.preview()
        d, _r, _u = p._axes()
        seen = [f for f in p.faces if f.kind == "wall" and sum(a * b for a, b in zip(normal(f.points), d, strict=True)) > 0]
        self.assertEqual(len(seen), 2)              # from the South-West: the South and the West walls

    def test_the_elevation_stays_between_10_and_80_degrees(self):
        p = self.preview()
        p.turn(10, 120)
        self.assertEqual(p.elevation, 80.0)
        p.turn(-30, -5)
        self.assertEqual((p.azimuth, p.elevation), (330.0, 10.0))


class Dialogs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        _setup.meridiana_look()

    def shown(self, dialog):
        self.addCleanup(dialog.deleteLater)
        dialog.show()
        self.app.processEvents()
        return dialog

    def click_pill(self, preview, key):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        preview.grab()                              # laid out as drawn
        centre = preview._rects[key].center().toPoint()
        QTest.mouseClick(preview, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, centre)
        self.app.processEvents()

    def test_a_click_on_a_pill_opens_its_field_and_the_length_written_reaches_the_dialog(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        from meridiana import templates
        from meridiana.ui.template_dialog import TemplateDialog
        d = self.shown(TemplateDialog())
        preview = d.preview
        self.assertEqual([p.number for p in preview.pills()], [1, 2, 3, 4, 5, 6])
        self.assertEqual(preview.pill(3).text.replace(",", "."), "12.00 m")     # 20 - 8: the South arm's top
        self.click_pill(preview, 3)
        self.assertEqual(preview.editing, 3)
        self.assertTrue(preview.editor.isVisible())
        preview.editor.selectAll()
        QTest.keyClicks(preview.editor, "14")
        QTest.keyClick(preview.editor, Qt.Key.Key_Return)
        self.assertTrue(d.isVisible())              # Enter is the pill's, not the dialog's
        self.assertIsNone(preview.editing)
        self.assertEqual(d.measures()["width"], 22.0)       # the South arm longer, its thickness kept
        self.assertEqual(d.ring, templates.footprint("L", d.measures()))
        self.assertAlmostEqual(preview.pill(3).value, 14.0)
        self.assertAlmostEqual(preview.pill(1).value, 22.0)

    def test_esc_gives_up_and_leaves_the_dialog_open(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        from meridiana.ui.template_dialog import TemplateDialog
        d = self.shown(TemplateDialog())
        before = d.measures()
        self.click_pill(d.preview, 1)
        QTest.keyClicks(d.preview.editor, "35")
        QTest.keyClick(d.preview.editor, Qt.Key.Key_Escape)
        self.assertTrue(d.isVisible())
        self.assertIsNone(d.preview.editing)
        self.assertFalse(d.preview.editor.isVisible())
        self.assertEqual(d.measures(), before)

    def test_a_length_no_measure_can_make_is_refused_and_the_field_stays_open(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        from meridiana.ui.template_dialog import TemplateDialog, side_measure
        d = self.shown(TemplateDialog())
        d.kind.setCurrentIndex(d.kind.findData("trapezoid"))
        self.app.processEvents()
        before = d.measures()
        self.click_pill(d.preview, 4)                # the West side runs 3 m along the base
        d.preview.editor.setText("2")
        QTest.keyClick(d.preview.editor, Qt.Key.Key_Return)
        self.assertEqual(d.preview.editing, 4)
        self.assertTrue(d.preview.editor.property("problem"))
        self.assertIn("3", d.preview.editor.toolTip())
        self.assertEqual(d.measures(), before)
        d.preview.editor.setText("5")               # 3-4-5: a depth of 4 m
        QTest.keyClick(d.preview.editor, Qt.Key.Key_Return)
        self.assertAlmostEqual(d.measures()["depth"], 4.0)
        self.assertAlmostEqual(d.preview.pill(4).value, 5.0)
        # what cannot be read is said, as in the number fields
        self.click_pill(d.preview, 1)
        d.preview.editor.setText("dodici")
        QTest.keyClick(d.preview.editor, Qt.Key.Key_Return)
        self.assertTrue(d.preview.editor.property("problem"))
        # every side of every template gives back its own length
        from meridiana import templates
        for kind in templates.KINDS:
            m = templates.defaults(kind)
            ring = templates.footprint(kind, m)
            for side in range(1, len(ring) + 1):
                (ax, ay), (bx, by) = ring[side - 1], ring[side % len(ring)]
                target = math.hypot(bx - ax, by - ay) + 1.0
                key, value = side_measure(kind, side, target, m)
                new = templates.footprint(kind, {**m, key: value})
                (ax, ay), (bx, by) = new[side - 1], new[side % len(new)]
                self.assertAlmostEqual(math.hypot(bx - ax, by - ay), target, places=6, msg=f"{kind} {side}")

    def test_the_canopy_pills_reach_their_fields_and_out_of_range_is_refused(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        from meridiana.ui.canopy_dialog import CanopyDialog
        d = self.shown(CanopyDialog())
        d.rows.setCurrentIndex(1)
        self.app.processEvents()
        planes = [f for f in d.preview.faces if f.kind == "plane"]
        self.assertEqual(len(planes), 2)                             # two planes, one per row (R281: and columns)
        self.assertAlmostEqual(d.preview.pill(2).value, 10.0)      # two rows of 5 m
        self.click_pill(d.preview, 2)
        d.preview.editor.setText("12")
        QTest.keyClick(d.preview.editor, Qt.Key.Key_Return)
        self.assertAlmostEqual(d.fields['depth'].value(), 6.0)
        self.click_pill(d.preview, 1)
        d.preview.editor.setText("12")
        QTest.keyClick(d.preview.editor, Qt.Key.Key_Return)
        self.assertAlmostEqual(d.fields['bay_width'].value(), 3.0)  # 4 spaces
        self.click_pill(d.preview, 'tilt')
        d.preview.editor.setText("70")
        QTest.keyClick(d.preview.editor, Qt.Key.Key_Return)
        self.assertEqual(d.preview.editing, 'tilt')                 # beyond 60°: refused, the field open
        self.assertAlmostEqual(d.fields['tilt'].value(), 8.0)
        QTest.keyClick(d.preview.editor, Qt.Key.Key_Escape)
        self.assertTrue(d.isVisible())
        d.fields['clearance'].setValue(3.5)                        # a field changed: the drawing follows
        self.assertAlmostEqual(min(p[2] for f in d.preview.faces if f.kind == "plane" for p in f.points), 3.5)

    def test_a_plane_seen_from_under_is_drawn_before_the_columns_and_from_above_after(self):
        # R281: the painter's order of Y's report, 3: the columns stand under the canopy's plane
        from meridiana.ui.preview3d import Face, Preview3D, box
        view = Preview3D()
        self.addCleanup(view.deleteLater)
        view.resize(300, 220)
        steep = Face([(0, 0, 3), (4, 0, 3), (4, 4, 6), (0, 4, 6)], "plane")      # rising to the North, 37°
        view.show_scene([steep, *box((2, 2), (0.3, 0.3, 3))])
        for azimuth, elevation, plane_first in ((225, 30, False), (0, 15, True)):
            view.turn(azimuth, elevation)
            kinds = [face.kind for _l, _d, face, _n, _f in view.drawn()]
            self.assertEqual(kinds.index("plane") < kinds.index("structure"), plane_first, azimuth)

    def test_pointing_a_field_lights_its_sides(self):
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QEnterEvent
        from PySide6.QtCore import QPointF

        from meridiana.ui.template_dialog import TemplateDialog
        d = self.shown(TemplateDialog())
        field = d.fields["depth"]
        self.app.sendEvent(field, QEnterEvent(QPointF(1, 1), QPointF(1, 1), QPointF(1, 1)))
        self.assertEqual(d.preview.highlight, {4, 6})
        self.app.sendEvent(field, QEvent(QEvent.Type.Leave))
        self.assertEqual(d.preview.highlight, set())


class Themes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_both_dialogs_draw_in_the_light_and_the_dark_theme(self):
        from PySide6.QtGui import QPalette

        from meridiana.ui.canopy_dialog import CanopyDialog
        from meridiana.ui.template_dialog import TemplateDialog
        for theme in ("light", "dark"):
            _setup.meridiana_look(theme)
            for dialog in (TemplateDialog(), CanopyDialog()):
                self.addCleanup(dialog.deleteLater)
                dialog.show()
                self.app.processEvents()
                image = dialog.preview.grab().toImage()
                base = dialog.preview.palette().color(QPalette.ColorRole.Base)
                corner = image.pixelColor(image.width() // 2, int(8 * image.devicePixelRatio()))
                self.assertLess(abs(corner.lightness() - base.lightness()), 6, theme)    # the view's ground
                dark = base.lightness() < 128
                self.assertEqual(dark, theme == "dark")
                # something is drawn: the faces differ from the ground
                centre = image.pixelColor(image.width() // 2, image.height() // 2)
                self.assertNotEqual(centre.rgb(), base.rgb(), f"{theme} {type(dialog).__name__}")
                dialog.close()


if __name__ == "__main__":
    unittest.main()
