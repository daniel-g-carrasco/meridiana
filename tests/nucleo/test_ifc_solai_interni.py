"""A building without IfcRoof took the tops of all its slabs above the ground floor for roofs: an interior model's
first floor, a slab under a ceiling, and everything on them (partitions, sanitary fittings) became obstacles. Now «a
roof is only what has no other building over it» (ifc_read.Above): a slab is a floor, left out, when at least half of
its plan lies under a slab, a roof or a covering 1.8 m or more above it; a slab with walls a storey tall standing
inside it (long together twice the side of the square of its area) and nothing over it is the floor of a storey the
model gives no roof to: it stays a body with its outline, its top flat at the top of those walls, the walls under it.
The share covered is of the true plan of what covers it, never of its convex hull: a slab in the recess of a higher U
slab is under the open sky.

The sample `tests/data/ifc/solai-interni.ifc` (made by hand, no data of any real model): one building without IfcRoof,
a slab of 10 x 8 m at 4 m under a ceiling (IfcCovering) at 6.7 m with a partition under it; a slab of 10 x 10 m at 8 m
with three partitions 8 m long and 3 m tall (to 11 m) inside it and nothing over it; a slab of 3.6 x 5.8 m at 4 m in
the recess of a U slab at 7 m; the highest slab, 10 x 10 m at 12 m, free, with a chimney."""

import unittest
from pathlib import Path

from shapely.geometry import Polygon

import _setup  # noqa: F401

from meridiana.app.exchange import ifc_import, ifc_read
from meridiana.core.model import model

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "ifc" / "solai-interni.ifc"


class InteriorFloors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.found = ifc_read.read(str(SAMPLE))
        cls.plan = ifc_import.plan(cls.found, model.Project(), "origin", None, name="t", source_name="t.ifc")

    def pitches(self):
        return sorted((round(Polygon(p["ring"]).area), round(p["point"][2], 2))
                      for b in self.found["buildings"] for p in b["pitches"])

    def test_the_covered_slab_goes_and_the_storey_is_raised_to_its_top(self):
        # before: (80, 4.0) under the ceiling was a roof, and (100, 8.0) the floor of the storey of partitions
        self.assertEqual(self.pitches(), [(21, 4.0), (96, 7.0), (100, 11.0), (100, 12.0)])
        self.assertTrue(all(b["source"] == "slabs" for b in self.found["buildings"]))
        storey = next(p for b in self.found["buildings"] for p in b["pitches"] if round(p["point"][2], 2) == 11.0)
        self.assertEqual(storey["normal"], [0.0, 0.0, 1.0])
        c = self.found["counts"]
        self.assertEqual((c["floors"], c["storeys_topped"]), (1, 1))
        self.assertAlmostEqual(c["floors_area"], 80.0, places=1)
        self.assertAlmostEqual(c["storeys_topped_area"], 100.0, places=1)

    def test_the_recess_is_measured_on_the_true_plan(self):
        # the U's hull covers the slab in its recess whole: by the hull it would have been a floor
        u = next(p for b in self.found["buildings"] for p in b["pitches"] if round(p["point"][2], 2) == 7.0)
        low = next(p for b in self.found["buildings"] for p in b["pitches"] if round(p["point"][2], 2) == 4.0)
        recess = Polygon(low["ring"])
        self.assertAlmostEqual(Polygon(u["ring"]).convex_hull.intersection(recess).area / recess.area, 1.0, places=2)

    def test_no_partition_is_an_obstacle(self):
        # before: the four partitions too, as walls on the floors
        self.assertEqual([(o["name"], o["kind"]) for o in self.found["obstacles"]], [("CAMINO", "chimney")])
        self.assertEqual(len(self.plan.exclusions), 1)

    def test_the_summary_says_it(self):
        self.assertIn("1 floor slab with the building over it (a ceiling, another floor) is not taken for a roof "
                      "(80.0 m2)", self.plan.left_out)
        self.assertIn("1 floor slab with a storey of walls on it and no roof over them in the model: taken as a body "
                      "with a flat top at the top of those walls (100.0 m2)", self.plan.approximated)


if __name__ == "__main__":
    unittest.main()
