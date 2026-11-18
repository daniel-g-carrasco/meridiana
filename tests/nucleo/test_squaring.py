"""Squaring a traced outline: right angles where the hand was near one, chamfers kept, vertices on a side
kept and put on it, shapes with nothing square left alone."""

import math
import unittest

import _setup  # noqa: F401

from meridiana import squaring


class Squaring(unittest.TestCase):
    def test_a_rectangle_traced_askew(self):
        traced = [(0.0, 0.0), (6.1, 0.15), (12.05, 0.3), (12.4, 8.1), (0.3, 7.6)]
        out, why = squaring.square(traced)
        self.assertEqual(why, "")
        angles = squaring.corner_angles(out)
        corners = [a for i, a in enumerate(angles) if i != 1]
        for a in corners:
            self.assertAlmostEqual(a, 90.0, delta=0.5)
        self.assertAlmostEqual(angles[1], 180.0, delta=0.5)     # the vertex on the side stays on it
        self.assertEqual(len(out), len(traced))
        self.assertLess(max(math.dist(a, b) for a, b in zip(traced, out, strict=True)), 0.6)

    def test_an_l_with_a_chamfer(self):
        shape = [(0, 0), (10.2, 0.3), (10.0, 4.1), (6.0, 4.0), (4.1, 6.05), (0.1, 6.0)]
        out, why = squaring.square(shape)
        self.assertEqual(why, "")
        angles = squaring.corner_angles(out)
        for i in (0, 1, 2, 5):
            self.assertAlmostEqual(angles[i], 90.0, delta=1.0)
        self.assertTrue(120 < angles[3] < 150 and 120 < angles[4] < 150)      # the chamfer stays a chamfer

    def test_a_square_needs_nothing(self):
        out, why = squaring.square([(0, 0), (10, 0), (10, 5), (0, 5)])
        self.assertEqual(why, "square_enough")

    def test_a_triangle_is_not_squarish(self):
        _out, why = squaring.square([(0, 0), (10, 0), (5, 8)])
        self.assertEqual(why, "not_squarish")


if __name__ == "__main__":
    unittest.main()
