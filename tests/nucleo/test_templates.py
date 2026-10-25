"""Building templates (task 16a, step 8): each one a valid outline with the measures written, placed and turned
where the designer clicks, and measures that make no outline said in words."""

import math
import unittest

import _setup  # noqa: F401
from shapely.geometry import Polygon

from meridiana import roofs, sides, templates


class Templates(unittest.TestCase):
    def test_every_template_is_a_valid_outline_with_the_measures_written(self):
        expected = {"rectangle": [20, 10, 20, 10], "L": [20, 8, 12, 10, 8, 18], "T": [24, 8, 8, 12, 8, 12, 8, 8],
                    "U": [24, 16, 8, 9, 8, 9, 8, 16]}
        for kind in templates.KINDS:
            with self.subTest(kind=kind):
                ring = templates.footprint(kind)
                poly = Polygon(ring)
                self.assertTrue(poly.is_valid)
                self.assertTrue(poly.exterior.is_ccw)
                self.assertEqual(ring[0], [0.0, 0.0])
                if kind in expected:
                    self.assertEqual([round(x, 9) for x in sides.lengths(ring)], expected[kind])
        trapezoid = templates.footprint("trapezoid", {"base": 22, "top": 15, "depth": 10, "offset": 3})
        self.assertEqual(trapezoid, [[0, 0], [22, 0], [18, 10], [3, 10]])     # the proof's trapezoid

    def test_measures_written_are_the_measures_of_the_outline(self):
        ring = templates.footprint("L", {"width": 30, "depth": 25, "arm_south": 10, "arm_west": 12})
        self.assertEqual(sides.lengths(ring), [30, 10, 18, 15, 12, 25])
        self.assertAlmostEqual(Polygon(ring).area, 30 * 10 + 12 * 15)

    def test_the_templates_have_the_roofs_of_the_proof(self):
        for kind, ends in (("L", {1, 4}), ("T", {1, 4, 7}), ("U", {2, 6}), ("trapezoid", {1, 3})):
            with self.subTest(kind=kind):
                self.assertEqual(roofs.default_gables(templates.footprint(kind)), ends)

    def test_measures_that_make_no_outline_are_said(self):
        for kind, measures, words in (("L", {"arm_south": 20}, "arms"), ("U", {"arm": 12}, "courtyard"),
                                      ("rectangle", {"width": 0}, "more than zero"),
                                      ("T", {"stem": 30}, "stem")):
            with self.subTest(kind=kind), self.assertRaises(ValueError) as caught:
                templates.footprint(kind, measures)
            self.assertIn(words, str(caught.exception))

    def test_a_template_placed_stands_on_the_point_clicked_turned(self):
        ring = templates.placed(templates.footprint("rectangle"), (100.0, 50.0), 90.0)
        self.assertEqual(ring[0], [100.0, 50.0])
        self.assertEqual(ring[1], [100.0, 70.0])                  # the 20 m side turned to the North
        self.assertAlmostEqual(Polygon(ring).area, 200.0, places=6)
        self.assertEqual([round(x, 3) for x in sides.lengths(ring)], [20, 10, 20, 10])
        self.assertTrue(math.isclose(Polygon(templates.placed(templates.footprint("U"), (0, 0), 33.0)).area,
                                     Polygon(templates.footprint("U")).area, rel_tol=1e-6))


if __name__ == "__main__":
    unittest.main()
