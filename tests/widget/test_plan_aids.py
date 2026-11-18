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

    def test_the_plan_rotates_without_changing_the_project_and_the_compass_follows(self):
        plan = self.plan
        before = self.project.to_json()
        centre = plan.mapToScene(plan.viewport().rect().center())
        scale = plan.transform().m11()
        plan.rotate_view(30.0)
        self.assertAlmostEqual(plan.view_rotation(), 30.0)
        self.assertAlmostEqual(plan.north.angle, -30.0)
        self.assertEqual(plan.north.heading_text(), "30° NE")
        self.assertEqual(self.project.to_json(), before)
        from meridiana.ui.plan import to_scene
        plan.align_to_side(self.project.buildings[0].footprint, 1)
        a, b = (plan.mapFromScene(to_scene(*self.project.buildings[0].footprint[i])) for i in (1, 2))
        self.assertAlmostEqual(a.y(), b.y(), delta=1e-6)
        self.assertEqual(plan.north.heading_text(), "90° E")
        # panning a turned plan: the drawing follows the hand on the screen (it went the wrong way, and at 90°
        # translate_view divided by nought; review of 26/10/2026)
        point = to_scene(*self.project.buildings[0].footprint[0])
        on_screen = plan.mapFromScene(point)
        plan.translate_view(40, -25)
        moved = plan.mapFromScene(point) - on_screen
        self.assertLessEqual(abs(moved.x() - 40) + abs(moved.y() + 25), 2)   # the scroll bars round to pixels
        plan.translate_view(-40, 25)
        plan.reset_rotation()
        self.assertAlmostEqual(plan.view_rotation(), 0.0)
        self.assertAlmostEqual(plan.transform().m11(), scale)
        self.assertLess((plan.mapToScene(plan.viewport().rect().center()) - centre).manhattanLength(),
                        8 * plan.metres_per_pixel())       # the scene's scroll bars round to whole pixels
        self.assertEqual(plan.north.heading_text(), "0° N")

    def test_string_numbers_stay_on_their_modules_at_every_rotation_zoom_and_pan(self):
        from PySide6.QtCore import QPoint, QPointF

        plan = self.plan
        router = plan._router()
        order = list(range(min(12, len(router.centres))))
        numbers = plan._number_items(order, 100.0)
        self.assertTrue(numbers)
        for angle in (30.0, 115.0):
            plan.reset_rotation()
            plan.rotate_view(angle)
            for factor in (1.0, 1.6, 0.7):
                plan.zoom_at(factor, QPoint(120, 90))
                plan.translate_view(37, -23)
                for item in numbers:
                    module = order[int(item.text) - 1]
                    expected = QPointF(plan.mapFromScene(QPointF(*router.centres[module])))
                    actual = QPointF(plan.mapFromScene(item.pos())) + item.boundingRect().center()
                    self.assertLess((actual - expected).manhattanLength(), 3.0,
                                    (angle, factor, item.text, actual, expected))

    def test_every_stringed_module_has_a_screen_sized_dot_until_modules_get_small(self):
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QColor, QTransform
        from PySide6.QtWidgets import QGraphicsItem

        from meridiana.ui.plan import ChipItem

        plan = self.plan
        router = plan._router()
        order = list(range(min(12, len(router.centres))))
        for angle in (0.0, 30.0, 115.0):
            plan.setTransform(QTransform().scale(40.0, 40.0).rotate(angle))
            items = plan._string_items(order, QColor("#ffd166"), 2.5, 35.0, 140)
            dots = [item for item in items if item.data(0) == "string_dot"]
            self.assertEqual(len(dots), len(order), angle)
            for dot in dots:
                module = dot.data(1)
                expected = QPointF(plan.mapFromScene(QPointF(*router.centres[module])))
                actual = QPointF(plan.mapFromScene(dot.pos())) + dot.rect().center()
                self.assertLess((actual - expected).manhattanLength(), 0.01, (angle, module))
                self.assertEqual((dot.rect().width(), dot.rect().height()), (ChipItem.DOT, ChipItem.DOT))
                self.assertTrue(dot.flags() & QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
            for item in items:
                plan.scene().removeItem(item)
        plan.setTransform(QTransform().scale(2.0, 2.0))
        items = plan._string_items(order, QColor("#ffd166"), 2.5, 35.0, 140)
        self.assertFalse(any(item.data(0) == "string_dot" for item in items))
        numbers = plan._number_items(order, 100.0, QColor("#ffd166"))
        self.assertTrue(all(item.swatch and item.colour.name() == "#ffd166" for item in numbers))

    def test_the_n_of_the_compass_goes_with_the_arrow_and_a_click_brings_north_up(self):
        """R174 (Daniel, 26/10/2026: «la N di nord non segue la freccia ... la N dovrebbe poter ruotare. e anche un
        modo per riportarlo a nord ci vuole»): the N stands past the arrow's tip, wherever it points; a click on the
        compass says so (its signal, which the window ties to «North up»)."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QSignalSpy, QTest
        north = self.plan.north
        centre = north.CENTRE
        north.set_rotation(0.0)
        up = north.letter_centre()
        self.assertAlmostEqual(up.x(), centre.x())
        self.assertLess(up.y(), centre.y())                         # North up: the N above the middle
        self.assertEqual(north.cursor().shape(), Qt.CursorShape.ArrowCursor)
        north.set_rotation(90.0)                                    # the view turned: North to the left
        left = north.letter_centre()
        self.assertAlmostEqual(left.y(), centre.y(), places=6)
        self.assertLess(left.x(), centre.x())
        self.assertIn("(N)", north.toolTip())                       # the click is said where it is
        self.assertEqual(north.cursor().shape(), Qt.CursorShape.PointingHandCursor)
        north.set_rotation(120.0)                                   # Daniel's screenshot: 120° SE
        tilted = north.letter_centre()
        self.assertLess(tilted.x(), centre.x())
        self.assertGreater(tilted.y(), centre.y())                  # down and to the left, at the arrow's tip
        spy = QSignalSpy(north.clicked)
        QTest.mouseClick(north, Qt.MouseButton.LeftButton)
        self.assertEqual(spy.count(), 1)

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

    def test_zoom_reaches_the_whole_equal_earth_world_and_returns_to_the_same_roof(self):
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QTransform

        plan = self.plan
        plan.loader.offline = True
        for _ in range(30):
            plan.zoom_at(0.1, QPoint(plan.viewport().width() // 2, plan.viewport().height() // 2))
        self.assertGreaterEqual(plan.metres_per_pixel(), 50000)
        self.assertTrue(plan.world.equal_earth)
        self.assertTrue(plan.site_mark.isVisible())
        self.assertIn("km", plan.scale_bar.text())
        self.assertFalse(plan.scale_bar.isVisible())
        self.assertEqual(plan.north.angle, -plan.view_rotation())
        plan.setTransform(QTransform().scale(10, 10))
        plan.centerOn(0, 0)
        plan._moved()
        self.assertFalse(plan.world.equal_earth)
        self.assertFalse(plan.site_mark.isVisible())
        self.assertTrue(plan.scale_bar.isVisible())
        self.assertAlmostEqual(plan.metres_per_pixel(), 0.1)
        plan.resize(500, 400)
        plan.zoom_at(0.0, QPoint(250, 200))
        self.assertAlmostEqual(plan.metres_per_pixel(), 84000, places=6)

    def test_natural_earth_draws_offline_alone_and_under_the_tiles(self):
        from PySide6.QtGui import QTransform

        plan = self.plan
        plan.loader.offline = True
        plan.set_source("none")
        plan.setTransform(QTransform().scale(0.0001, 0.0001))
        plan.centerOn(0, 0)
        plan._moved()
        for name in ("Italy", "United States of America", "Brazil", "Australia"):
            self.assertIn(name, plan.world.country_items)
            self.assertTrue(plan.world.country_items[name].isVisible())
        self.assertTrue(any(label.isVisible() for label in plan.world.labels))
        occupied = []
        for label in plan.world.labels:
            if not label.isVisible():
                continue
            rect = label.boundingRect()
            rect.moveCenter(plan.mapFromScene(plan.world.label_anchors[label]))
            self.assertFalse(any(rect.intersects(other) for other in occupied), label.text())
            occupied.append(rect)
        self.assertTrue(all(item.zValue() < 0 for item in plan.world.items))
        plan.set_source("osm")
        self.assertEqual(plan.attribution.full, "Natural Earth")
        plan.setTransform(QTransform().scale(10, 10))
        plan._moved()
        self.assertFalse(plan.world.country_items["Italy"].isVisible())

    def test_equal_earth_hides_tiles_without_loading_them_and_has_a_quiet_threshold(self):
        from PySide6.QtGui import QTransform
        from PySide6.QtWidgets import QGraphicsRectItem
        plan = self.plan
        plan.loader.offline = True
        tile = QGraphicsRectItem(0, 0, 10, 10)
        plan.scene().addItem(tile)
        plan.tile_items[("test", 0, 0, 0)] = tile
        plan.setTransform(QTransform().scale(1 / 2100, 1 / 2100))
        plan._moved()
        self.assertTrue(plan.world.equal_earth)
        self.assertFalse(tile.isVisible())
        plan._update_tiles()
        self.assertEqual(plan.wanted_tiles, set())
        plan.setTransform(QTransform().scale(1 / 1800, 1 / 1800))
        plan._moved()
        self.assertTrue(plan.world.equal_earth)
        plan.setTransform(QTransform().scale(1 / 1400, 1 / 1400))
        plan._moved()
        self.assertFalse(plan.world.equal_earth)
        self.assertTrue(tile.isVisible())


if __name__ == "__main__":
    unittest.main()
