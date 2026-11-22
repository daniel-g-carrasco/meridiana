"""A slender element leaning over a roof is no obstacle. Every obstacle read from a model becomes an upright prism of
its plan outline from the roof to its top: a tie rod of 20 mm, 6.5 m long and leaning 37 degrees, made a blade 3.9 m
tall along 2.9 m (on one model, 16 of them made 239 m2 of walls against rods whose shadow is a line). A leaning plate
(a solar collector, a stair's railing flight, a steel sheet) is not slender and stays an obstacle, as an upright one.

The sample `tests/data/ifc/tirante-inclinato.ifc` (made by hand, no data of any real model): a flat roof of 12 x 8 m at
6 m, a rod of 20 mm and 5 m leaning 37 degrees from the vertical with its foot on the roof, a chimney 1.5 m tall, a
plate of 2 x 1 x 0.05 m whose 2 m side rises 35 degrees from the roof."""

import unittest
from pathlib import Path

import _setup  # noqa: F401

from meridiana.app.exchange import ifc_import, ifc_read
from meridiana.core.model import model

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "ifc" / "tirante-inclinato.ifc"
ROOF = 6.0


class LeaningRod(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.found = ifc_read.read(str(SAMPLE), mode="direct")

    def test_the_rod_is_no_obstacle_and_is_counted(self):
        names = sorted(o["name"] for o in self.found["obstacles"])
        self.assertEqual(names, ["CAMINO", "LAMIERA"])           # before: also TIRANTE, 4 m tall
        self.assertEqual(self.found["counts"].get("leaning"), 1)

    def test_the_chimney_and_the_leaning_plate_stay_with_their_heights(self):
        by_name = {o["name"]: o for o in self.found["obstacles"]}
        self.assertAlmostEqual(by_name["CAMINO"]["z1"] - ROOF, 1.5, places=3)
        self.assertAlmostEqual(by_name["LAMIERA"]["z1"] - ROOF, 1.188, places=2)

    def test_the_import_says_why_the_rod_is_left_out(self):
        plan = ifc_import.plan(self.found, model.Project(), "origin", None, name="t", source_name="t.ifc")
        heights = sorted(round(e.height, 2) for e, _host in plan.exclusions)
        self.assertEqual(heights, [1.19, 1.5])
        self.assertTrue(any(s.startswith("1 slender element leaning over a roof") for s in plan.left_out),
                        plan.left_out)


if __name__ == "__main__":
    unittest.main()
