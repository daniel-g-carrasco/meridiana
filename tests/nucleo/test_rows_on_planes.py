"""Rows on the plane of a pitch (R278, R279, R280; 30/10/2026): the east-west pair stands on the pitch, whatever its
tilt and azimuth; a row drawn with the Row tool follows the line drawn, from its first click, also on a pitch; the
east-west tool lays pairs along the line drawn, in one step undone."""

import math
import unittest

import _setup
import numpy as np
from _fixtures import laid
from _fixtures import tetto_con_lucernario as project

from meridiana import geo, layout, manual, mesh, model
from meridiana.energy.nearshade import modules_corners

setUpModule = _setup.keep_global_state

SQUARE = [(0, 0), (40, 0), (40, 30), (0, 30)]
PLANES = {"flat": layout.Surface(), "inclined": layout.Surface(tilt=20.0, azimuth=0.0, z0=6.0, x0=0.0, y0=15.0),
          "turned": layout.Surface(tilt=25.0, azimuth=-40.0, z0=8.0, x0=3.0, y0=4.0)}


def normal(surface: layout.Surface) -> np.ndarray:
    fx, fy = geo.facing_vector(surface.azimuth)
    b = math.radians(surface.tilt)
    return np.array([math.sin(b) * fx, math.sin(b) * fy, math.cos(b)])


def heights(surface: layout.Surface, points: np.ndarray) -> np.ndarray:
    """The distance of 3D points from the plane of the surface, along its normal."""
    origin = np.array([surface.x0, surface.y0, surface.z0])
    return (points - origin) @ normal(surface)


class EastWestOnAPitch(unittest.TestCase):
    """R278: the pair's feet on the pitch, its modules at the tilt chosen from the pitch, the ridge of both halves at
    one height above it."""

    def check(self, surface, rows=None, stack=1):
        p = layout.Params(mounting="east_west", tilt=10.0, stack=stack, edge=0.5)
        r = layout.compute(SQUARE, surface=surface, params=p, rows=rows)
        self.assertGreater(r.count, 10)
        across = layout.Module().length if p.portrait else layout.Module().width
        top = p.stand_off + (stack * across + (stack - 1) * p.stack_gap) * math.sin(math.radians(p.tilt))
        corners = modules_corners(r.modules)                 # the plan corners lifted to each module's own plane
        n = normal(surface)
        for pm, c in zip(r.modules, corners, strict=True):
            h = heights(surface, c)
            if pm.level == 0:
                self.assertAlmostEqual(h.min(), p.stand_off, places=6)         # the foot on the pitch
            if pm.level == stack - 1:
                self.assertAlmostEqual(h.max(), top, places=6)                 # the ridge, both halves alike
            m = np.cross(c[0] - c[3], c[1] - c[0])
            m /= np.linalg.norm(m)
            angle = math.degrees(math.acos(min(1.0, abs(float(m @ n)))))
            self.assertAlmostEqual(angle, p.tilt, places=4)                    # tilted from the pitch, not the floor
            along = np.linalg.norm(c[0] - c[3])
            self.assertAlmostEqual(along, layout.Module().width, places=6)    # a module, not its shadow on the plan
        return r

    def test_on_a_flat_roof_as_before(self):
        self.check(PLANES["flat"])

    def test_on_an_inclined_pitch(self):
        self.check(PLANES["inclined"])

    def test_on_a_turned_pitch_with_two_stacked(self):
        self.check(PLANES["turned"], stack=2)

    def test_rows_by_hand_running_down_the_slope(self):
        surface = PLANES["turned"]
        alpha = round(geo.bearing_to_azimuth(geo.azimuth_to_bearing(surface.azimuth) + 90.0), 2)
        self.check(surface, rows=[layout.Row("f1", 5.0, 5.0, alpha, [round(1.2 * k, 6) for k in range(8)])])

    def test_the_3d_instances_are_the_modules(self):
        r = self.check(PLANES["turned"])
        module = layout.Module()
        table = mesh.module_table(r.modules, module.width, module.length)
        corners = modules_corners(r.modules)
        local = np.array([[50, 0, -50], [50, 0, 50], [-50, 0, 50], [-50, 0, -50]], dtype=float)
        for row, c in zip(table, corners, strict=True):
            m = np.array([row[0:3], row[4:7], row[8:11]], dtype=float)
            where = np.array([row[3], row[7], row[11]], dtype=float)
            qt = local @ m.T + where
            got = sorted(map(tuple, np.round(np.stack([qt[:, 0], -qt[:, 2], qt[:, 1]], axis=1), 3)))
            want = sorted(map(tuple, np.round(c, 3)))
            self.assertEqual(got, want)


class RowFollowsTheLine(unittest.TestCase):
    """R280: the row starts at the first click and runs along the line drawn, its modules square to it."""

    def check_line(self, p, start, end, plane=None):
        manual.draw(p, "s1", start, end)(p)
        r = laid(p)
        d = np.subtract(end, start)
        d /= np.linalg.norm(d)
        first = min((c for m in r.modules for c in m.corners), key=lambda c: math.dist(c, start))
        self.assertLess(math.dist(first, start), 1e-4)                    # from the first click
        for m in r.modules:
            c = np.array(m.corners)
            e = c[0] - c[3]
            self.assertLess(abs(e[0] * d[1] - e[1] * d[0]) / np.linalg.norm(e), 1e-6)   # square to the line
        offs = (np.array([c for m in r.modules for c in m.corners]) - np.array(start)) @ np.array([-d[1], d[0]])
        self.assertTrue(offs.min() > -1e-4 or offs.max() < 1e-4)            # all on one side (0,1 mm, as kept)
        self.assertLess(np.abs(offs).min(), 1e-4)                            # the front edge on it
        # the front edges (on a pitch the modules are square to the line on it, not on the plan)
        along = (np.array([m.corners[i] for m in r.modules for i in (0, 3)]) - np.array(start)) @ d
        self.assertGreater(along.min(), -1e-4)                               # from the first click towards the end
        return r

    def test_an_oblique_line_on_a_flat_roof(self):
        r = self.check_line(project(), (5.0, 3.0), (5.0 + 30.0 * math.cos(0.5), 3.0 + 30.0 * math.sin(0.5)))
        self.assertEqual(r.count, int((30.0 + 0.02) // (1.134 + 0.02)))

    def test_an_oblique_line_on_a_pitch_keeps_the_modules_on_it(self):
        from _fixtures import casa_a_falde
        p = casa_a_falde()
        p.subfields[0].filled = False
        start, end = (1.0, 1.0), (9.0, 3.0)
        r = self.check_line(p, start, end)
        surface = p.surface_of(p.subfields[0])
        c = modules_corners(r.modules)
        h = heights(surface, c.reshape(-1, 3))
        self.assertTrue(np.allclose(h, h[0], atol=1e-6))                   # flat on the pitch
        sides = np.linalg.norm(c[:, 0] - c[:, 3], axis=1)
        self.assertTrue(np.allclose(sides, 1.134, atol=1e-6))               # whole modules on the slope
        gaps = sorted(np.linalg.norm(c[i + 1, 3] - c[i, 0]) for i in range(len(c) - 1))
        self.assertAlmostEqual(gaps[0], 0.02, places=6)


class RowOnTheTurnedPlan(unittest.TestCase):
    """R280 as Daniel drew it: two clicks on the plan turned, a line oblique on the screen and on the plan."""

    def test_two_clicks_on_a_turned_plan(self):
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtWidgets import QApplication

        from meridiana.ui.plan import from_scene, to_scene
        _setup.qt_or_skip()
        win = _setup.window(self, project())
        plan = win.plan
        plan.rotate_view(30.0)
        plan.fit()
        win._set_tool("row")
        plan.snaps_on = False
        clicks = [plan.mapFromScene(to_scene(*q)) for q in ((10.0, 8.0), (30.0, 20.0))]
        for point in clicks:
            for kind in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
                held = Qt.MouseButton.LeftButton if kind == QEvent.Type.MouseButtonPress else Qt.MouseButton.NoButton
                QApplication.sendEvent(plan.viewport(), QMouseEvent(
                    kind, QPointF(point), QPointF(plan.viewport().mapToGlobal(point)), Qt.MouseButton.LeftButton,
                    held, Qt.KeyboardModifier.NoModifier))
        start, end = (from_scene(plan.mapToScene(q)) for q in clicks)
        sf = win.project.subfields[0]
        self.assertTrue(sf.manual)
        r = win.project.fill(sf)
        d = np.subtract(end, start) / math.dist(start, end)
        first = min((c for m in r.modules for c in m.corners), key=lambda c: math.dist(c, start))
        self.assertLess(math.dist(first, start), 1e-3)
        for m in r.modules:
            e = np.subtract(m.corners[0], m.corners[3])
            self.assertLess(abs(e[0] * d[1] - e[1] * d[0]) / np.linalg.norm(e), 1e-5)
        self.assertEqual(r.count, int((math.dist(start, end) + 0.02) // (1.134 + 0.02)))


class EastWestTool(unittest.TestCase):
    """R279: a line drawn with the east-west tool lays pairs along it, in one step undone."""

    def test_pairs_along_the_line_in_one_step(self):
        p = project()
        manual.draw(p, "s1", (5.0, 3.0), (5.0, 15.0), east_west=True)(p)
        sf = p.subfields[0]
        self.assertEqual(sf.params["mounting"], "east_west")
        r = laid(p)
        self.assertEqual({round(m.azimuth) for m in r.modules}, {-90, 90})
        self.assertEqual(r.count, 2 * int((12.0 + 0.02) // (1.134 + 0.02)))
        # a pair faces both ways: from the line, it goes into the sub-field (to the east here), not out of it
        self.assertGreater(min(c[0] for m in r.modules for c in m.corners), 5.0 - 1e-4)

    def test_on_a_pitch_the_pairs_stand_on_it(self):
        from _fixtures import casa_a_falde
        p = casa_a_falde()
        manual.draw(p, "s1", (1.0, 1.0), (10.0, 1.0), east_west=True)(p)
        surface = p.surface_of(p.subfields[0])
        r = laid(p)
        self.assertGreater(r.count, 0)
        c = modules_corners(r.modules)
        h = heights(surface, c.reshape(-1, 3)).reshape(len(c), 4)
        self.assertTrue(np.allclose(h.min(axis=1), layout.Params().stand_off, atol=1e-6))    # every foot on it
        self.assertEqual(len({round(m.tilt, 3) for m in r.modules}), 2)                    # two real orientations

    def test_the_window_tool_is_one_undo_step(self):
        _setup.qt_or_skip()
        p = model.Project()
        p.subfields = [model.SubField(id="s1", name="Ground", ring=[[0, 0], [20, 0], [20, 20], [0, 20]])]
        win = _setup.window(self, p)
        win.commands["layout_east_west"].trigger()
        self.assertEqual(win.plan.tool, "east_west")
        win._row_drawn([2.0, 2.0], [2.0, 12.0])
        sf = win.project.subfields[0]
        self.assertEqual(sf.params.get("mounting"), "east_west")
        self.assertTrue(sf.manual and win.project.fill(sf).count > 0)
        win.undo.undo()
        sf = win.project.subfields[0]
        self.assertNotIn("mounting", sf.params)
        self.assertFalse(sf.manual)


if __name__ == "__main__":
    unittest.main()
