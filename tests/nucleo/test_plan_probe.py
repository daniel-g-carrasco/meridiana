"""The plan's probe of the measuring tool (study 46, state r34-righello section 2.3): the surface under a point (a pitch,
a flat roof, the ground), the snaps the tool asks for, the polar guides on and off, the edge passed over with its
heights; and the measurements made apart from the one in hand (what a view asks at every step of the pointer)."""

import math
import unittest

import _setup  # noqa: F401

from meridiana import i18n
from meridiana.app.view.heights import Surfaces
from meridiana.app.view.measure_tool import MeasureTool
from meridiana.app.view.plan_probe import PlanProbe, reference_segments
from meridiana.core.model import model

MPP = 1 / 12                    # metres per pixel: the snaps reach 10 px, 0.83 m
T20 = math.tan(math.radians(20))
_before = None


def setUpModule():
    global _before
    _before = i18n._translation
    i18n.setup("en")


def tearDownModule():
    i18n._translation = _before


def shed():
    """A shed 24 x 12 m, eaves at 6 m, a gable roof at 20° with its ridge along East at N 6; a flat plant room
    on the ground beside it, 3 m high."""
    p = model.Project(name="Probe")
    p.buildings.append(model.Building(id="b1", name="Shed", height=6, footprint=[[0, 0], [24, 0], [24, 12], [0, 12]],
                                      roof=model.Roof(type="gable", tilt=20)))
    p.buildings.append(model.Building(id="b2", name="Room", height=3, footprint=[[30, 0], [34, 0], [34, 4], [30, 4]]))
    return p


class Heights(unittest.TestCase):
    def setUp(self):
        self.s = Surfaces(shed())

    def test_the_pitch_the_flat_roof_and_the_ground(self):
        z, n = self.s.at(10, 3)
        self.assertAlmostEqual(z, 6 + 3 * T20)
        self.assertAlmostEqual(n[2], math.cos(math.radians(20)))
        self.assertAlmostEqual(n[1], -math.sin(math.radians(20)))     # the south pitch faces South
        self.assertAlmostEqual(self.s.height(10, 9), 6 + 3 * T20)       # the north one, as high
        self.assertEqual(self.s.at(32, 2), (3.0, (0.0, 0.0, 1.0)))
        self.assertEqual(self.s.at(28, 2), (0.0, (0.0, 0.0, 1.0)))
        self.assertEqual(Surfaces(None).at(1, 1), (0.0, (0.0, 0.0, 1.0)))

    def test_on_the_outline_the_roof_wins(self):
        self.assertAlmostEqual(self.s.height(0, 0), 6)                  # a corner: the eave, not the ground
        self.assertAlmostEqual(self.s.height(12, 6), 6 + 6 * T20)       # on the ridge
        self.assertAlmostEqual(self.s.height(24, 3), 6 + 3 * T20)       # on the gable's edge

    def test_the_highest_roof_is_the_one_seen_from_above(self):
        p = shed()
        p.buildings.append(model.Building(id="b3", name="Plant", height=9, footprint=[[2, 2], [4, 2], [4, 4], [2, 4]]))
        self.assertAlmostEqual(Surfaces(p).height(3, 3), 9)


class Probe(unittest.TestCase):
    def setUp(self):
        self.p = PlanProbe(shed())
        self.tool = MeasureTool()

    def probe(self, point, mods=frozenset()):
        return self.p.probe(point, MPP, self.tool.wanted(mods))

    def test_the_references_are_the_drawings(self):
        segments = reference_segments(shed())
        self.assertEqual(len(segments), 4 + 4 + 8 + 4)        # two outlines, the gable's two pitches, the flat roof
        self.assertEqual(len(self.p.snapper.segments), len(segments))

    def test_a_vertex_with_its_height_and_the_edge_passed_over(self):
        pr = self.probe((24.2, 0.1))
        self.assertEqual((pr.kind, pr.point[:2]), ("vertex", (24.0, 0.0)))
        self.assertAlmostEqual(pr.point[2], 6.0)
        self.assertTrue(pr.exact)
        self.assertIsNotNone(pr.edge)
        for end in pr.edge:
            self.assertAlmostEqual(end[2], self.p.surfaces.height(end[0], end[1]))

    def test_a_midpoint_on_a_pitch(self):
        pr = self.probe((12.1, 0.1))
        self.assertEqual((pr.kind, pr.point[:2]), ("midpoint", (12.0, 0.0)))
        self.assertAlmostEqual(pr.point[2], 6.0)
        pr = self.probe((24.1, 3.05))                          # the middle of the south pitch's gable edge
        self.assertEqual(pr.kind, "midpoint")
        self.assertAlmostEqual(pr.point[2], 6 + 3 * T20)

    def test_a_point_on_a_pitch_carries_its_normal(self):
        pr = self.probe((10, 3))
        self.assertEqual(pr.kind, "free")
        self.assertAlmostEqual(pr.point[2], 6 + 3 * T20)
        self.assertAlmostEqual(pr.normal[2], math.cos(math.radians(20)))
        self.assertIsNone(pr.edge)

    def test_ctrl_and_none_take_every_snap_away(self):
        pr = self.probe((24.2, 0.1), frozenset({"ctrl"}))
        self.assertEqual((pr.kind, pr.point[:2], pr.edge), ("free", (24.2, 0.1), None))
        self.tool.set_snap("none")
        pr = self.probe((24.2, 0.1))
        self.assertEqual((pr.kind, pr.point[:2]), ("free", (24.2, 0.1)))

    def test_one_snap_from_the_menu(self):
        self.tool.set_snap("midpoint")
        self.assertEqual(self.probe((24.2, 0.1)).kind, "free")          # by a corner, no midpoint near
        self.assertEqual(self.probe((12.1, 0.1)).kind, "midpoint")
        self.tool.set_snap("perpendicular")                       # the tool finds the foot from the edge given
        pr = self.probe((12.4, 0.3))
        self.assertIsNotNone(pr.edge)

    def test_the_polar_guides_on_and_off(self):
        self.tool.click(self.probe((40, 20)))
        cursor = (47.0, 27.3)                                    # 0.3 m off the 45° step from the first point
        pr = self.probe(cursor)
        self.assertTrue(pr.guides)
        self.assertNotEqual(pr.point[:2], cursor)
        self.tool.set_polar(False)                               # the plan's Ortho off (gui/backend/plan.py)
        pr = self.probe(cursor)
        self.assertEqual((pr.guides, pr.point[:2], pr.kind), ((), cursor, "free"))

    def test_the_snaps_off_in_the_plan_leave_the_polar_guides(self):
        pr = self.p.probe((24.2, 0.1), MPP, self.tool.wanted(), snaps_on=False)
        self.assertEqual((pr.kind, pr.point[:2]), ("free", (24.2, 0.1)))


class Done(unittest.TestCase):
    def test_the_measurements_made_apart(self):
        t = MeasureTool()
        p = PlanProbe(shed())
        for point in ((0, -3), (10, -3)):
            t.click(p.probe(point, MPP, t.wanted()))
        t.key("Enter")
        t.click(p.probe((40, 20), MPP, t.wanted()))
        whole = t.display("plan")
        light = t.display("plan", with_done=False)
        self.assertEqual(light["done"], [])
        self.assertEqual({k: v for k, v in whole.items() if k != "done"}, {k: v for k, v in light.items() if k != "done"})
        self.assertEqual(t.done("plan"), whole["done"])
        self.assertEqual(t.done("plan")[0]["segments"][0]["pill"]["text"], "10.00 m")
        with self.assertRaises(ValueError):
            t.done("side")


if __name__ == "__main__":
    unittest.main()
