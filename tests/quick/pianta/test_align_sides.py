"""R505: «Align the view to a side» takes the side nearest the pointer within 14 screen pixels at any zoom, without
aiming at the line: only buildings, pitches and sub-fields, the selected object's sides first, the longer of two as
near; the side is lit and the R497 icon shows as soon as it is taken; Esc leaves the command."""
import math
import unittest

from PySide6.QtCore import QPointF, Qt
from PySide6.QtQml import QQmlEngine, QQmlExpression
from PySide6.QtTest import QTest

from meridiana import model
from meridiana.quick.backend.plan_collect import REACH_PX, nearest_side
from quick.pianta import test_edit_window as edit

setUpModule = edit.setUpModule

SQUARE = [[0, 0], [40, 0], [40, 20], [0, 20]]


class NearestSideRules(unittest.TestCase):
    def test_reach_is_in_screen_pixels_at_any_zoom(self):
        rings = [('building', 'b', SQUARE)]
        for mpp in (0.02, 0.1, 0.5):
            for px, taken in ((0, True), (6, True), (13, True), (15, False), (30, False)):
                with self.subTest(mpp=mpp, px=px):
                    hit = nearest_side(rings, (20, -px * mpp), mpp)
                    self.assertEqual(hit is not None, taken)
                    if taken:
                        self.assertEqual(hit[3], 0)

    def test_nearest_wins_and_the_longer_of_two_as_near(self):
        mpp = 0.1
        short = ('subfield', 's', [[10, -0.5], [12, -0.5], [12, -2], [10, -2]])     # a side 2 m long, 0,5 m away
        rings = [short, ('building', 'b', SQUARE)]
        # 0,2 m from the building's side, 0,3 m from the short one: the nearer, the building
        self.assertEqual(nearest_side(rings, (11, -0.2), mpp)[:2], ('building', 'b'))
        # 0,24 m and 0,26 m (within 3 px): the longer on screen, the building's side of 40 m
        self.assertEqual(nearest_side(rings, (11, -0.24), mpp)[:2], ('building', 'b'))
        # 1 px from the short side and 4,5 px from the building: the short one
        self.assertEqual(nearest_side(rings, (11, -0.55), mpp)[:2], ('subfield', 's'))

    def test_the_selected_objects_side_first(self):
        mpp = 0.1
        inner = ('subfield', 's1', [[0.5, 0.5], [39.5, 0.5], [39.5, 19.5], [0.5, 19.5]])
        rings = [inner, ('building', 'b1', SQUARE)]
        self.assertEqual(nearest_side(rings, (20, 0.1), mpp)[:2], ('building', 'b1'))
        self.assertEqual(nearest_side(rings, (20, 0.1), mpp, ('subfield', 's1'))[:2], ('subfield', 's1'))
        self.assertEqual(nearest_side(rings, (20, 0.4), mpp, ('building', 'b1'))[:2], ('building', 'b1'))
        self.assertEqual(nearest_side(rings, (20, 0.4), mpp, ('row', 's1/r3'))[:2], ('subfield', 's1'))
        # the selected object out of reach: the nearest of the others
        self.assertEqual(nearest_side(rings, (20, 0.45), mpp, ('building', 'far'))[:2], ('subfield', 's1'))


class AlignSidesWindow(unittest.TestCase):
    setUp = edit.EditWindowTest.setUp
    tearDown = edit.EditWindowTest.tearDown
    visual = edit.EditWindowTest.visual

    def at(self, east, north):
        e = QQmlExpression(QQmlEngine.contextForObject(self.plan), self.plan, f'screen({east}, {north})')
        p = e.evaluate()[0]
        self.assertFalse(e.hasError(), e.error().toString())
        return self.plan.mapToScene(p)

    def zoom(self, z):
        self.plan.setProperty('zoom', z)
        self.plan.setProperty('panX', 300)
        self.plan.setProperty('panY', 700)
        QTest.qWait(40)

    def test_distance_from_the_side_zoom_click_and_escape(self):
        p = self.session.project
        p.exclusions.append(model.ExclusionItem('e1', [[18, 0.3], [22, 0.3], [22, 2], [18, 2]], building='b1'))
        self.controller.refresh()
        angles = []
        self.controller.alignRequested.connect(angles.append)
        for z in (8, 20):
            self.zoom(z)
            self.controller.pickAnyEdge('align')
            self.assertNotIn('exclusion', {kind for kind, _oid, _ring in self.controller.collector.rings})
            badge = self.visual('collectBadge')
            side = self.at(20, 0)                    # the middle of the south side of the building, on screen
            below = self.at(20, -1)
            ux, uy = below.x() - side.x(), below.y() - side.y()
            unit = math.hypot(ux, uy)
            for px, taken in ((2, True), (9, True), (13, True), (18, False), (40, False)):
                with self.subTest(zoom=z, px=px):
                    point = QPointF(side.x() + ux / unit * px, side.y() + uy / unit * px).toPoint()
                    QTest.mouseMove(self.window, point)
                    QTest.qWait(30)
                    hover = self.controller.collector.hover
                    self.assertEqual(hover is not None, taken, hover)
                    self.assertEqual(badge.isVisible(), taken)
                    lit = [d for d in self.controller._draft if d.get('stroke') == '#ffb000']
                    self.assertEqual(len(lit), 1 if taken else 0)
                    if taken:
                        self.assertEqual((hover[0], hover[1], hover[3]), ('building', 'b1', 0))
            # a click 10 px off the line takes that side
            point = QPointF(side.x() + ux / unit * 10, side.y() + uy / unit * 10).toPoint()
            QTest.mouseMove(self.window, point)
            QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, point)
            QTest.qWait(30)
            self.assertEqual(len(angles), 1 if z == 8 else 2)
            self.assertFalse(self.controller.collecting)
        # Esc leaves the command, nothing aligned
        self.controller.pickAnyEdge('align')
        self.assertTrue(self.controller.collecting)
        self.plan.forceActiveFocus()
        QTest.keyClick(self.window, Qt.Key_Escape)
        QTest.qWait(30)
        self.assertFalse(self.controller.collecting)
        self.assertEqual(len(angles), 2)

    def test_the_selected_sub_field_wins_and_pills_do_not_take_the_click(self):
        self.zoom(8)                                     # 2 m between the outlines: 16 px
        self.controller.editor.select('subfield', 's1')
        self.controller.refresh()
        self.controller.pickAnyEdge('align')
        middle = self.at(20, 1.1).toPoint()              # 9 px from the sub-field's side, 7 px from the building's
        QTest.mouseMove(self.window, self.at(20, 10).toPoint())      # the first move only enters the plan
        QTest.qWait(30)
        QTest.mouseMove(self.window, middle)
        QTest.qWait(60)
        hover = self.controller.collector.hover
        self.assertEqual(hover[:2], ('subfield', 's1'))
        self.assertFalse(self.visual('vertexMouse').property('enabled'))
        QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, middle)
        QTest.qWait(30)
        self.assertFalse(self.controller.collecting)
        self.assertEqual(self.controller.editor.selection, ('subfield', 's1'))


if __name__ == '__main__':
    unittest.main()
