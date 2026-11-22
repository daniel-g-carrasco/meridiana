"""An element hanging above a roof comes in raised, from its own underside to its top (ExclusionItem.base, format 32).
As an upright prism from the roof to its top, a stair's railing 2.4 to 3.6 m above the roof (the stair or the balcony
it belongs to is no roof in the model) made a wall 8 to 11.7 m tall and 9 to 13 m long; until R34 it was left out.
What stands on something has the base of its own underside (a railing on top of a wall, the wall its own obstacle);
several elements of one obstacle stand where the lowest does (the segments of a mullion stacked from the roof up).

The sample `tests/data/ifc/ringhiera-sospesa.ifc` (made by hand, no data of any real model): a flat roof of 12 x 8 m at
4 m; a railing 1 m tall and 6 m long whose bottom is 4 m above the roof; a wall 1.2 m tall and one 2.2 m tall, each
with a railing 1 m tall on its top; three segments of a mullion of 0.15 x 0.15 x 2.3 m stacked from the roof to 6.9 m;
a chimney 1.5 m tall."""

import unittest
from pathlib import Path

import _setup  # noqa: F401

from meridiana.app.exchange import ifc_import, ifc_read
from meridiana.core.model import model

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "ifc" / "ringhiera-sospesa.ifc"
ROOF = 4.0


class Hanging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.found = ifc_read.read(str(SAMPLE), mode="direct")
        cls.by_name = {o["name"]: o for o in cls.found["obstacles"]}
        cls.plan = ifc_import.plan(cls.found, model.Project(), "origin", None, name="t", source_name="t.ifc")
        cls.project = model.Project()
        ifc_import.apply(cls.project, cls.plan)

    def test_the_hanging_railing_comes_in_raised_and_is_counted(self):
        railing = self.by_name["RINGHIERA_SOSPESA"]        # before R34: left out, counted as hanging
        self.assertAlmostEqual(railing["base"], 4.0, places=3)
        self.assertAlmostEqual(railing["z0"] - ROOF, 4.0, places=3)
        self.assertAlmostEqual(railing["z1"] - ROOF, 5.0, places=3)
        self.assertEqual(self.found["counts"].get("raised"), 3)     # the three railings
        self.assertNotIn("hanging", self.found["counts"])

    def test_a_railing_on_a_wall_has_its_own_base_and_the_wall_stands(self):
        self.assertEqual(self.by_name["MURETTO"]["base"], 0.0)
        self.assertAlmostEqual(self.by_name["MURETTO"]["z1"] - ROOF, 1.2, places=3)
        self.assertAlmostEqual(self.by_name["RINGHIERA_MURETTO"]["base"], 1.2, places=3)
        self.assertAlmostEqual(self.by_name["RINGHIERA_MURETTO"]["z1"] - ROOF, 2.2, places=3)
        self.assertEqual(self.by_name["MURO"]["base"], 0.0)
        self.assertAlmostEqual(self.by_name["MURO"]["z1"] - ROOF, 2.2, places=3)
        self.assertAlmostEqual(self.by_name["RINGHIERA_MURO"]["base"], 2.2, places=3)
        self.assertAlmostEqual(self.by_name["RINGHIERA_MURO"]["z1"] - ROOF, 3.2, places=3)

    def test_the_stacked_mullion_is_one_pole_from_the_roof(self):
        # one obstacle of three elements: its base the least of theirs, the lowest stands on the roof
        pole = self.by_name["MONTANTE"]
        self.assertEqual(pole["elements"], 3)
        self.assertEqual(pole["base"], 0.0)
        self.assertAlmostEqual(pole["z0"], ROOF, places=3)
        self.assertAlmostEqual(pole["z1"] - ROOF, 6.9, places=3)

    def test_the_chimney_stands(self):
        self.assertEqual(self.by_name["CAMINO"]["base"], 0.0)
        self.assertAlmostEqual(self.by_name["CAMINO"]["z1"] - ROOF, 1.5, places=3)
        self.assertEqual(len(self.found["obstacles"]), 7)

    def test_the_project_has_the_raised_railing_from_4_to_5_m_above_the_roof(self):
        got = sorted((round(e.base, 3), round(e.height, 3)) for e in self.project.exclusions)
        self.assertEqual(got, [(0.0, 1.2), (0.0, 1.5), (0.0, 2.2), (0.0, 6.9), (1.2, 2.2), (2.2, 3.2), (4.0, 5.0)])
        (body,) = self.project.buildings
        roof = body.height
        raised = [e for e in self.project.exclusions if e.base == 4.0]
        self.assertEqual(len(raised), 1)
        prisms = {p["id"]: p for p in self.project.obstacle_prisms()}
        prism = prisms[raised[0].id]
        self.assertAlmostEqual(prism["z0"] - roof, 4.0, places=3)
        self.assertAlmostEqual(prism["z1"] - roof, 5.0, places=3)
        # the railing on the wall from its own underside, the wall under it from the roof
        on_wall = [prisms[e.id] for e in self.project.exclusions if e.base == 2.2]
        self.assertEqual([(round(p["z0"] - roof, 3), round(p["z1"] - roof, 3)) for p in on_wall], [(2.2, 3.2)])

    def test_the_import_says_the_railings_come_in_raised(self):
        self.assertTrue(any(s.startswith("3 obstacles hanging above a roof come in raised")
                            for s in self.plan.approximated), self.plan.approximated)
        self.assertFalse(any("hanging" in s for s in self.plan.left_out), self.plan.left_out)


class Climbing(unittest.TestCase):
    """`tests/data/ifc/ringhiera-scala.ifc`: on the same roof, a railing 1 m tall climbing a stair from 2.4 to 5.4 m
    above it along 6 m, and one lying level 1.5 m above it. Raised from its underside to its top the first was a wall
    6 m long and 4 m tall (m20: two stairs' railings, 6.8 x 5.7 and 9.95 x 4.7 m): it is left out and said; the level
    one comes in raised."""

    @classmethod
    def setUpClass(cls):
        cls.found = ifc_read.read(str(SAMPLE.with_name("ringhiera-scala.ifc")), mode="direct")
        cls.plan = ifc_import.plan(cls.found, model.Project(), "origin", None, name="t", source_name="t.ifc")

    def test_the_railing_climbing_the_stair_is_left_out_and_said(self):
        self.assertEqual([o["name"] for o in self.found["obstacles"]], ["RINGHIERA_PIANA"])
        self.assertEqual(self.found["counts"].get("sloping"), 1)
        self.assertTrue(any(s.startswith("1 element climbing above a roof") for s in self.plan.left_out),
                        self.plan.left_out)

    def test_the_level_railing_comes_in_raised(self):
        (railing,) = self.found["obstacles"]
        self.assertAlmostEqual(railing["base"], 1.5, places=3)
        self.assertAlmostEqual(railing["z1"] - ROOF, 2.5, places=3)

    def test_the_fill_seen_from_the_side(self):
        import numpy as np
        band = np.array([(0, 0, 0), (6, 0, 3), (6, 0, 4), (0, 0, 1), (0, 0.05, 0), (6, 0.05, 3), (6, 0.05, 4),
                         (0, 0.05, 1)], float)
        self.assertAlmostEqual(ifc_read._side_fill(band), 0.25, places=3)
        box = np.array([(x, y, z) for x in (0, 6) for y in (0, 0.05) for z in (0, 1)], float)
        self.assertAlmostEqual(ifc_read._side_fill(box), 1.0, places=6)
        self.assertLess(ifc_read._side_fill(band), ifc_read.SIDE_FILL)


if __name__ == "__main__":
    unittest.main()
