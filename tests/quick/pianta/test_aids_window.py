"""R174/R389: aids and string markers attached to the installed native plan."""
import math
import unittest

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QFontMetricsF
from PySide6.QtTest import QTest

from meridiana.quick.backend.controls import install_controls
from meridiana.ui import design
from quick.pianta import test_edit_window as edit
from quick.pianta.test_window import settle_zoom

setUpModule = edit.setUpModule


def descendants(item):
    for child in item.childItems():
        yield child
        yield from descendants(child)


class AidsWindow(unittest.TestCase):
    setUp = edit.EditWindowTest.setUp
    tearDown = edit.EditWindowTest.tearDown
    visual = edit.EditWindowTest.visual

    def test_side_field_pill_disc_font_and_baseline_at_two_zoom_levels(self):
        self.controller.editor.select('building', 'b1')
        for zoom in (10, 25):
            self.plan.setProperty('zoom', zoom)
            self.plan.setProperty('panX', 150)
            self.plan.setProperty('panY', 700)
            QTest.qWait(50)
            pill = self.visual('sidePill0')
            self.controller.editSide(0)
            QTest.qWait(20)
            editor, field = self.visual('sideEditor'), self.visual('sideLengthField')
            self.assertTrue(editor.isVisible())
            self.assertEqual(editor.height(), pill.height())
            self.assertLessEqual(abs(editor.x()-pill.x()), 1)
            self.assertLessEqual(abs(editor.y()-pill.y()), 1)
            self.assertTrue(editor.boundingRect().contains(field.mapRectToItem(editor, field.boundingRect())))
            self.assertEqual(field.property('font').pixelSize(), design.Type.SMALL)
            metrics = QFontMetricsF(field.property('font'))
            self.assertLessEqual(abs(field.property('baselineOffset')-design.Space.XXS-metrics.ascent()), 1)
            self.assertEqual(field.x(), design.Space.XXS+editor.property('disc')+design.Space.XS)
            unit = next(c for c in editor.childItems() if c.property('text') == 'm')
            self.assertAlmostEqual(unit.y()+unit.property('baselineOffset'), field.property('baselineOffset'))
            QTest.keyClick(self.window, Qt.Key_Escape)
            self.assertFalse(self.controller.sideEditing)

    def test_compass_scale_corners_pan_resize_and_toolbar_avoidance(self):
        install_controls(self.engine).configure({'reducedMotion': True})
        compass, scale, bar = (self.visual(n) for n in ('compass', 'scaleBar', 'planViewBar'))
        self.assertEqual((compass.x(), compass.y()), (self.plan.width()-compass.width()-8, 8))
        self.assertEqual((scale.x(), scale.y()), (8, self.plan.height()-scale.height()-8))
        self.assertIn('sud', compass.property('tooltipText').lower())
        before = [(item.x(), item.y()) for item in (compass, scale)]
        QTest.mousePress(self.window, Qt.MiddleButton, Qt.NoModifier, QPoint(600, 400))
        QTest.mouseMove(self.window, QPoint(640, 375))
        QTest.mouseRelease(self.window, Qt.MiddleButton, Qt.NoModifier, QPoint(640, 375))
        self.assertEqual([(item.x(), item.y()) for item in (compass, scale)], before)
        self.window.resize(round(bar.width()+compass.width()), 480)
        QTest.qWait(60)
        self.assertGreater(compass.y(), bar.y()+bar.height())
        self.assertLess(compass.y()+compass.height(), scale.y())
        self.window.resize(1000, 600)
        QTest.qWait(60)
        self.assertEqual(compass.y(), 8)
        self.assertEqual(compass.x(), self.plan.width()-compass.width()-8)
        self.assertEqual(scale.y(), self.plan.height()-scale.height()-8)
        self.assertFalse(self.warnings, self.warnings)

    def test_real_zoom_scale_rotate_pan_and_compass_reset_preserve_project(self):
        compass, scale = (self.visual(n) for n in ('compass', 'scaleBar'))
        before = self.session.snapshot()
        length = scale.property('length')
        self.plan.zoomAt(1/8, 120, 90)
        self.assertGreater(scale.property('length'), length)
        length, pixels = scale.property('length'), scale.property('pixels')
        self.assertIn(round(length/10**math.floor(math.log10(length)), 9), (1, 2, 5))
        self.assertAlmostEqual(pixels, length*self.plan.property('zoom'))
        self.assertLessEqual(pixels, scale.property('longest'))
        centre = self.plan.world(self.plan.width()/2, self.plan.height()/2)
        zoom = self.plan.property('zoom')
        self.plan.rotateView(30)
        self.assertEqual(compass.property('headingText'), '30° NE')
        self.assertAlmostEqual((self.plan.world(self.plan.width()/2, self.plan.height()/2)-centre).manhattanLength(), 0)
        self.assertEqual(self.session.snapshot(), before)
        self.assertIn('(N)', compass.property('tooltipText'))
        for angle in (90, 120):
            self.plan.rotateView(angle-self.plan.property('bearing'))
            letter = compass.property('letterCentre')
            self.assertLess(letter.x(), 28)
            self.assertGreaterEqual(letter.y(), 28-1e-8)
        a = self.plan.screen(10, 5)
        self.plan.setProperty('panX', self.plan.property('panX')+40)
        self.plan.setProperty('panY', self.plan.property('panY')-25)
        self.assertEqual(self.plan.screen(10, 5)-a, QPointF(40, -25))
        self.plan.setProperty('panX', self.plan.property('panX')-40)
        self.plan.setProperty('panY', self.plan.property('panY')+25)
        QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier,
                         compass.mapToScene(QPointF(28, 28)).toPoint())
        self.assertEqual(compass.property('headingText'), '0° N')
        self.assertEqual(self.plan.property('bearing'), 0)
        self.assertEqual(self.plan.property('zoom'), zoom)
        self.assertLess((self.plan.world(self.plan.width()/2, self.plan.height()/2)-centre).manhattanLength(), 1e-8)
        self.assertEqual(self.session.snapshot(), before)
        self.assertFalse(self.warnings, self.warnings)

    @staticmethod
    def app_events():
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.processEvents()

    def test_r560_pills_keep_their_size_on_screen_at_two_zoom_levels_while_zooming_and_settled(self):
        # R560 (Daniel 08/11/2026): «le pillole in pianta degli inverter e delle stringhe vengono zoommate insieme
        # allo zoom della pianta. Non deve succedere, un po' come accade con le pillole delle misure dei lati». The
        # strings' names, their numbers and the inverters' notices keep their size on screen at every zoom, while the
        # wheel turns (before the zoom settles) and after; only their place follows the plan.
        chosen = self.result.modules[:12]
        self.session.edit('String fixture', lambda p: p.energy.update(strings={'runs': [
            {'inverter': 1, 'mppt': 1, 'modules': ['s1/'+m.key for m in chosen]}]}))
        self.controller.setPhase('plant')
        self.controller.chooseString(0)
        self.plan.setProperty('startingUp', False)     # past the window's start: a zoom settles 300 ms after (R541)

        def pills(prefix):
            out = {}
            for o in descendants(self.plan):
                name = o.objectName()
                if name.startswith(prefix) and o.isVisible():
                    r = o.mapRectToScene(o.boundingRect())
                    out.setdefault(name, []).append((round(r.width(), 2), round(r.height(), 2), r.center()))
            return out

        def sizes(found):
            return {k: sorted((w, h) for w, h, _c in v) for k, v in found.items()}
        for low, high in ((40, 64), (2.5, 4)):            # near (names and numbers), far (discs and notices)
            self.plan.setProperty('panX', 137)
            self.plan.setProperty('panY', 377)
            self.plan.setProperty('zoom', low)
            settle_zoom(self.plan, self.controller)
            self.app_events()
            before = pills('stringLabel-')
            self.assertTrue(before, f'zoom {low}: no pills')
            self.plan.setProperty('zoom', high)        # one notch of a long gesture: not settled yet
            self.app_events()      # bindings follow at once: no wait, the zoom has not settled
            self.assertNotEqual(self.plan.property('settledZoom'), high)
            during = pills('stringLabel-')
            self.assertEqual(sizes(during), sizes(before), f'zoom {low} -> {high}, while zooming')
            # their centres follow the plan: the same points of the plan, scaled about the plan's origin
            k = high / low
            for name, rows in before.items():
                for (_w, _h, c0), (_w2, _h2, c1) in zip(sorted(rows, key=lambda r: (r[2].x(), r[2].y())),
                                                        sorted(during[name], key=lambda r: (r[2].x(), r[2].y())),
                                                        strict=True):
                    origin = self.plan.mapToScene(QPointF(137, 377))
                    self.assertAlmostEqual(c1.x()-origin.x(), (c0.x()-origin.x())*k, delta=0.6)
                    self.assertAlmostEqual(c1.y()-origin.y(), (c0.y()-origin.y())*k, delta=0.6)
            settle_zoom(self.plan, self.controller)
            self.app_events()
            after = pills('stringLabel-')
            for name in set(before) & set(after):
                self.assertEqual(set(sizes(after)[name]) - set(sizes(before)[name]), set(), name)
        # the measures of the sides, the reference: the same size at both zooms
        self.controller.editor.select('building', 'b1')
        seen = []
        for zoom in (10, 25):
            self.plan.setProperty('zoom', zoom)
            self.app_events()
            pill = self.visual('sidePill0')
            seen.append(round(pill.mapRectToScene(pill.boundingRect()).height(), 2))
        self.assertEqual(seen[0], seen[1])
        self.assertFalse(self.warnings, self.warnings)

    def test_string_numbers_and_eight_pixel_dots_follow_modules_at_all_camera_transforms(self):
        chosen = self.result.modules[:12]
        self.session.edit('String fixture', lambda p: p.energy.update(strings={'runs': [
            {'inverter': 1, 'mppt': 1, 'modules': ['s1/'+m.key for m in chosen]}]}))
        self.controller.setPhase('plant')
        self.controller.chooseString(0)
        for angle in (0, 30, 115):
            for zoom in (40, 64, 28):
                self.plan.setProperty('bearing', angle)
                self.plan.setProperty('zoom', zoom)
                self.plan.setProperty('panX', 137)
                self.plan.setProperty('panY', 377)
                settle_zoom(self.plan, self.controller)  # R541: the strings' names laid out again once the zoom settles
                QTest.qWait(180)  # the map/label LOD changes when the camera settles
                numbers = [o for o in descendants(self.plan) if o.objectName() == 'stringLabel-number-0']
                self.assertTrue(numbers)
                for label in numbers:
                    record = label.property('modelData')
                    if hasattr(record, 'toVariant'):
                        record = record.toVariant()
                    module = chosen[record['item']['number']-1]
                    expected = self.plan.screen(*module.centre)
                    actual = label.mapToScene(QPointF(label.width()/2, label.height()/2))
                    # R467: beside its module and off the module's dot, the same distance at every camera
                    gap = math.hypot(expected.x()-actual.x(), expected.y()-actual.y())
                    self.assertGreater(gap, 4 + label.height()/2 - 1e-6)
                    self.assertLess(gap, 4 + 7 + label.width()/2 + 1e-6)
                dots = [o for o in self.plan.childItems() if o.property('location') is not None
                        and o.width() == o.height() == 8]
                self.assertEqual(len(dots), len(chosen))
                for dot, record in zip(dots, self.controller.dots, strict=True):
                    self.assertEqual(dot.property('radius'), 4)
                    expected = self.plan.screen(record['x'], record['y'])
                    self.assertLess((dot.mapToScene(QPointF(4, 4))-expected).manhattanLength(), 1e-6)
        self.plan.setProperty('zoom', 2)
        settle_zoom(self.plan, self.controller)
        QTest.qWait(180)
        self.assertFalse(self.controller.dots)
        self.assertFalse(self.warnings, self.warnings)
