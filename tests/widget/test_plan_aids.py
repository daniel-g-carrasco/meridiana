"""The plan's aids, on the plan alone (study 12, V1-V3): the north arrow and the scale bar as widgets over the
viewport in their corners, still while the plan moves, the scale bar with round lengths; the source of the
background said only over one; the outline of what a click would select without drawing the plan again, the
coordinates and the height of what is under the cursor, the repaints measured. The plan is made alone with the shed
(_fixtures.plan_view); the quick measure of the selection in the window's status bar is in finestra/test_panels.py.
PySide6 and a display (offscreen will do)."""

import unittest

import _setup
from _fixtures import capannone, plan_view

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class PlanAids(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.project = capannone()
        self.plan, self.results = plan_view(self, self.project)
        self.coords = []                                    # what the window shows in its status bar
        self.plan.cursorInfo.connect(self.coords.append)

    def corner(self, overlay):
        """Where an overlay stands over the viewport, in the viewport's pixels."""
        from PySide6.QtCore import QPoint
        vp = self.plan.viewport()
        return overlay.mapToGlobal(QPoint(0, 0)) - vp.mapToGlobal(QPoint(0, 0))

    def test_the_north_arrow_and_the_scale_bar_sit_in_their_corners_over_the_viewport(self):
        from PySide6.QtCore import QPoint

        from meridiana.ui.plan_overlays import MARGIN
        plan, vp = self.plan, self.plan.viewport()
        for overlay in (plan.north, plan.scale_bar, plan.attribution):
            self.assertIsNotNone(overlay.parentWidget())    # widgets, not drawn in drawForeground
        r = vp.rect()
        self.assertEqual(self.corner(plan.north), QPoint(r.width() - plan.north.width() - MARGIN, MARGIN))
        self.assertEqual(self.corner(plan.scale_bar), QPoint(MARGIN, r.height() - plan.scale_bar.height() - MARGIN))
        self.assertIn("South", plan.north.toolTip())

    def test_the_north_arrow_and_the_scale_bar_stay_put_while_the_plan_moves(self):
        plan = self.plan
        plan.set_tool("select")                             # the plan repaints only what changes: it scrolls
        self.app.processEvents()
        before = [self.corner(o) for o in (plan.north, plan.scale_bar)]
        plan.horizontalScrollBar().setValue(plan.horizontalScrollBar().value() + 300)    # a pan of 300 px
        plan.verticalScrollBar().setValue(plan.verticalScrollBar().value() - 120)
        self.app.processEvents()
        self.assertEqual([self.corner(o) for o in (plan.north, plan.scale_bar)], before)
        plan.resize(700, 500)                               # a resize frames the plan again
        self.app.processEvents()
        vp = plan.viewport().rect()
        from meridiana.ui.plan_overlays import MARGIN       # the design system's 8 (ui/design.py)
        self.assertEqual(self.corner(plan.north).x(), vp.width() - plan.north.width() - MARGIN)
        self.assertEqual(self.corner(plan.scale_bar).y(), vp.height() - plan.scale_bar.height() - MARGIN)

    def test_the_scale_bar_follows_the_zoom_with_round_lengths(self):
        import math

        from PySide6.QtCore import QPoint
        bar = self.plan.scale_bar

        def round_length(length: float) -> bool:
            """1, 2 or 5 times a power of ten."""
            return round(length / 10 ** math.floor(math.log10(length)), 9) in (1.0, 2.0, 5.0)
        before = bar.length
        self.assertTrue(round_length(before), before)
        self.plan.zoom_at(1 / 8, QPoint(100, 100))
        self.assertGreater(bar.length, before)
        self.assertTrue(round_length(bar.length), bar.length)
        self.assertAlmostEqual(bar.pixels, bar.length / self.plan.metres_per_pixel())
        self.assertLessEqual(bar.pixels, bar.LONGEST)

    def test_the_source_of_the_background_is_said_only_over_a_background(self):
        self.assertFalse(self.plan.attribution.isVisibleTo(self.plan))
        self.plan.set_source("osm")                         # what the window does with Background > OSM
        self.assertTrue(self.plan.attribution.isVisibleTo(self.plan))
        self.assertIn("OpenStreetMap", self.plan.attribution.text)
        self.plan.set_source("none")
        self.assertFalse(self.plan.attribution.isVisibleTo(self.plan))

    def test_a_source_this_version_does_not_know_falls_back_to_the_best_for_the_site(self):
        self.plan.set_source("a-source-of-tomorrow")
        self.assertEqual(self.plan.source, "pcn")            # the plan's site is in Milan: the national orthophoto
        self.assertEqual(self.plan.choice, "a-source-of-tomorrow")      # kept, for a version that knows it
        self.plan.set_source("none")

    def repainted(self, action) -> float:
        """The share of the plan's viewport painted again by `action` (the union of the paint events' regions): what
        the designer's machine redraws, measured, not the view's mode (study 18, D 5.2)."""
        from PySide6.QtCore import QEvent, QObject
        from PySide6.QtGui import QRegion
        from PySide6.QtTest import QTest
        vp = self.plan.viewport()
        if not QTest.qWaitForWindowExposed(self.plan, 2000):
            self.skipTest("the plan is not exposed: no paint to measure (said, not passed in silence)")

        class Paints(QObject):
            region = QRegion()

            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.Paint:
                    self.region = self.region.united(event.region())
                return False
        self.app.processEvents()
        paints = Paints()
        vp.installEventFilter(paints)
        try:
            action()
            self.app.processEvents()
        finally:
            vp.removeEventFilter(paints)
        whole = vp.width() * vp.height()
        return sum(r.width() * r.height() for r in paints.region) / whole if whole else 0.0

    def test_what_a_click_would_select_is_outlined_without_drawing_the_plan_again(self):
        from shapely.geometry import Point, Polygon

        from meridiana.ui.plan import to_scene
        plan = self.plan
        drawn = []
        original = plan.show_project
        plan.show_project = lambda *a: (drawn.append(1), original(*a))
        sf = self.project.subfields[0]
        r = self.results[sf.id]
        laid = [Polygon(m.corners).buffer(0.2) for m in r.modules]
        free = next((x, y) for x in range(3, 37) for y in range(3, 17)
                    if not any(q.contains(Point(x + 0.5, y + 0.5)) for q in laid))      # in the area, not on a module
        plan._update_cursor(plan.mapFromScene(to_scene(free[0] + 0.5, free[1] + 0.5)))
        kind, oid, _key = plan.hovered
        self.assertEqual((kind, oid), ("subfield", sf.id))
        self.assertIsNotNone(plan.hover_item)
        self.assertIn("Sud", self.coords[-1])
        self.assertIn("z ", self.coords[-1])                # the height of the roof there
        cx = sum(float(q[0]) for q in r.modules[0].corners) / 4
        cy = sum(float(q[1]) for q in r.modules[0].corners) / 4
        plan._update_cursor(plan.mapFromScene(to_scene(cx, cy)))
        self.assertEqual(plan.hovered, ("module", sf.id, r.modules[0].key))
        self.assertIn("module", self.coords[-1])
        plan._update_cursor(plan.mapFromScene(to_scene(1.15, 9.0)))     # by the edge of the area: still the area
        self.assertEqual(plan.hovered[:2], ("subfield", sf.id))
        plan._update_cursor(plan.mapFromScene(to_scene(-30.0, -30.0)))  # nothing there
        self.assertEqual((plan.hovered, plan.hover_item), (("", "", ""), None))
        self.assertEqual(drawn, [])
        # selecting, the outline of what is under the pointer repaints its own place; drawing, the guides cross the
        # whole plan and it is painted whole (the modules kept as an image between two zooms: esterni/test_tempi.py)
        share = self.repainted(lambda: plan._update_cursor(plan.mapFromScene(to_scene(cx, cy))))
        self.assertGreater(share, 0.0)
        self.assertLess(share, 0.5)
        plan.set_tool("building")
        self.app.processEvents()
        share = self.repainted(lambda: plan._update_cursor(plan.mapFromScene(to_scene(20.0, 10.0))))
        self.assertGreater(share, 0.95)
        plan.set_tool("select")


if __name__ == "__main__":
    unittest.main()
