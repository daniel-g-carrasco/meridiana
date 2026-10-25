"""The sides of an outline after it is drawn: their lengths, the side nearest a point, and a side stretched
to a new length as CAD programs stretch it."""

import unittest

import _setup  # noqa: F401

from meridiana import sides

RECT = [[0, 0], [40, 0], [40, 20], [0, 20]]
ELL = [[0, 0], [30, 0], [30, 10], [10, 10], [10, 25], [0, 25]]


class Sides(unittest.TestCase):
    def test_lengths_and_the_nearest_side(self):
        self.assertEqual(sides.lengths(RECT), [40.0, 20.0, 40.0, 20.0])
        self.assertEqual(sides.nearest(RECT, (39.5, 9.0), 1.0), 1)
        self.assertIsNone(sides.nearest(RECT, (20.0, 10.0), 1.0))          # in the middle: no side near

    def test_a_rectangle_stays_a_rectangle(self):
        wider = sides.stretch(RECT, 0, 50.0)
        self.assertEqual(wider, [[0, 0], [50.0, 0], [50.0, 20], [0, 20]])
        deeper = sides.stretch(RECT, 1, 12.5)                              # the East side: the North side moves
        self.assertEqual(sides.lengths(deeper), [40.0, 12.5, 40.0, 12.5])
        self.assertEqual(sides.stretch(RECT, 2, 30.0)[3], [10.0, 20.0])  # the North side, drawn westwards

    def test_an_ell_keeps_its_arms(self):
        longer = sides.stretch(ELL, 0, 36.0)                               # the bottom: the short arm grows
        self.assertEqual(sides.lengths(longer)[:3], [36.0, 10.0, 26.0])
        self.assertEqual(sides.lengths(longer)[3:], [15.0, 10.0, 25.0])

    def test_what_lies_beyond_moves_with_the_side(self):
        moved = sides.stretch(ELL, 2, 25.0)                                # the inner side, drawn westwards
        self.assertEqual(moved[0], [-5.0, 0.0])                            # the west wall went with it
        self.assertEqual(sides.lengths(moved)[2], 25.0)

    def test_what_would_vanish_is_refused(self):
        with self.assertRaises(ValueError):
            sides.stretch(RECT, 0, 0.01)                                   # 0.2 m2 left
        with self.assertRaises(ValueError):
            sides.stretch(RECT, 0, 0.0)


if __name__ == "__main__":
    unittest.main()
