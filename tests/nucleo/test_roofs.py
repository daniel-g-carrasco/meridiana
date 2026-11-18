"""Roof pitches: the planes meet where a roof's ridge and hips are, and water runs outwards; gable and hip
roofs follow any outline (task 16a)."""

import math
import unittest

import _setup  # noqa: F401
from shapely.geometry import Polygon
from shapely.ops import unary_union

from meridiana import roofs

HOUSE = [(0.0, 0.0), (12.0, 0.0), (12.0, 8.0), (0.0, 8.0)]     # 12 x 8 m, long side East-West
L_PLAN = [(0, 0), (20, 0), (20, 8), (8, 8), (8, 18), (0, 18)]  # 20 x 18 m, arms 8 m wide (study 16, A.2)


def points(pitch):
    return {(round(x, 6), round(y, 6)) for x, y in pitch.ring}


class Slopes(unittest.TestCase):
    def test_percent_and_heights_give_degrees(self):
        self.assertAlmostEqual(roofs.slope_from_percent(100), 45.0)
        self.assertAlmostEqual(roofs.slope_from_heights(6.0, 8.0, 4.0), math.degrees(math.atan(0.5)))

    def test_a_negative_run_is_refused(self):
        with self.assertRaises(ValueError):
            roofs.slope_from_heights(6.0, 8.0, 0.0)

    def test_the_slope_proposed_by_the_covering(self):
        # Daniel, 23/10/2026: 35 % for a new roof; ANDIL 2025 p. 7 for clay, the producers' sheets for metal
        self.assertAlmostEqual(roofs.proposed_tilt(), 19.29, places=2)
        self.assertAlmostEqual(roofs.proposed_tilt("pantiles"), roofs.slope_from_percent(30.0))
        self.assertAlmostEqual(roofs.proposed_tilt("metal"), roofs.slope_from_percent(7.0))
        self.assertIn("ANDIL", roofs.covering_source("tiles"))


class Generated(unittest.TestCase):
    def test_a_flat_roof_is_one_level_plane(self):
        (p,) = roofs.flat(HOUSE, 7.0)
        self.assertEqual(p.tilt, 0.0)
        self.assertEqual(p.z(5, 5), 7.0)

    def test_a_mono_pitch_goes_down_to_its_eave(self):
        (p,) = roofs.mono(HOUSE, 0, eave=6.0, tilt=10.0)       # eave on the South side (y = 0)
        self.assertAlmostEqual(p.azimuth, 0.0, places=6)
        self.assertAlmostEqual(p.z(6, 0), 6.0, places=9)
        self.assertAlmostEqual(p.z(6, 8), 6.0 + 8 * math.tan(math.radians(10)), places=9)
        self.assertEqual((p.side, p.name), (0, "pitch of side 1"))

    def test_a_gable_meets_on_a_ridge_along_the_long_side(self):
        pitches = roofs.gable(HOUSE, eave=6.0, tilt=30.0)
        self.assertEqual([p.side for p in pitches], [0, 2])                # one per eave, in the order of the sides
        self.assertEqual([p.name for p in pitches], ["pitch of side 1", "pitch of side 3"])
        self.assertEqual([round(p.azimuth) for p in pitches], [0, 180])
        ridge = 6.0 + 4.0 * math.tan(math.radians(30))
        for p in pitches:
            self.assertAlmostEqual(p.z(6.0, 4.0), ridge, places=9)
        self.assertAlmostEqual(sum(Polygon(p.ring).area for p in pitches), 96.0, places=9)

    def test_a_gable_with_its_gable_ends_on_the_long_sides(self):
        pitches = roofs.gable(HOUSE, eave=6.0, tilt=30.0, gables={0, 2})   # the ridge North-South
        self.assertEqual(sorted(round(p.azimuth) for p in pitches), [-90, 90])      # water to East and West
        ridge = 6.0 + 6.0 * math.tan(math.radians(30))                              # half of 12 m up
        for p in pitches:
            self.assertAlmostEqual(p.z(6.0, 4.0), ridge, places=9)

    def test_a_hip_roof_has_four_pitches_meeting_on_the_ridge(self):
        pitches = roofs.hip(HOUSE, eave=6.0, tilt=25.0)
        self.assertEqual(len(pitches), 4)
        self.assertEqual([round(p.azimuth) for p in pitches], [0, -90, 180, 90])
        self.assertAlmostEqual(sum(Polygon(p.ring).area for p in pitches), 96.0, places=9)
        ridge = 6.0 + 4.0 * math.tan(math.radians(25))
        for p in pitches:
            # every pitch reaches the ridge height at the ridge ends, 4 m in from the short sides
            self.assertAlmostEqual(max(z for _x, _y, z in p.corners_3d()), ridge, places=9)

    def test_a_rectangle_gives_the_roofs_of_before(self):
        """The outlines and the planes of the gable and hip roofs of format 8 on the same rectangle: the corners
        of the minimum rectangle, the middles of its short sides, the ridge ends half a width in."""
        gable = roofs.gable(HOUSE, eave=6.0, tilt=30.0)
        self.assertEqual([points(p) for p in gable], [{(0, 0), (12, 0), (12, 4), (0, 4)},
                                                      {(12, 8), (0, 8), (0, 4), (12, 4)}])
        hip = roofs.hip(HOUSE, eave=6.0, tilt=25.0)
        self.assertEqual([points(p) for p in hip], [{(0, 0), (12, 0), (8, 4), (4, 4)}, {(12, 0), (12, 8), (8, 4)},
                                                    {(12, 8), (0, 8), (4, 4), (8, 4)}, {(0, 8), (0, 0), (4, 4)}])
        for p in gable + hip:
            self.assertEqual(p.z0, 6.0)
            self.assertAlmostEqual(p.z(*p.ring[0]), 6.0, places=9)        # the eave's start, on the eave

    def test_an_l_with_its_gables_on_the_arms_has_four_pitches_and_a_valley(self):
        pitches = roofs.gable(L_PLAN, eave=6.0, tilt=20.0)             # the gable ends by default: on the arms
        self.assertEqual([p.side for p in pitches], [0, 2, 3, 5])
        self.assertAlmostEqual(unary_union([Polygon(p.ring) for p in pitches]).area, 240.0, places=6)
        self.assertAlmostEqual(sum(Polygon(p.ring).area for p in pitches), 240.0, places=6)
        # the valley: the inner corner at the eave, down from where the ridges of the two arms meet
        rise = 4.0 * math.tan(math.radians(20))
        north, east = pitches[1], pitches[2]                          # sides 3 and 4 of the outline, 2 and 3 here
        for p in (north, east):
            self.assertIn((8, 8), points(p))
            self.assertIn((4, 4), points(p))
            self.assertAlmostEqual(p.z(8, 8), 6.0, places=9)
            self.assertAlmostEqual(p.z(4, 4), 6.0 + rise, places=9)
        # nowhere above the footprint is the roof higher than the ridge of an arm 8 m wide (8.91 m before)
        self.assertAlmostEqual(roofs.ridge_height(pitches), 6.0 + rise, places=9)

    def test_a_hip_roof_on_an_l_has_six_pitches(self):
        pitches = roofs.hip(L_PLAN, eave=6.0, tilt=20.0)
        self.assertEqual([p.side for p in pitches], [0, 1, 2, 3, 4, 5])
        self.assertAlmostEqual(unary_union([Polygon(p.ring) for p in pitches]).area, 240.0, places=6)

    def test_the_gable_ends_of_a_new_roof(self):
        cases = {"rectangle": ([(0, 0), (20, 0), (20, 10), (0, 10)], {1, 3}),
                 "square": ([(0, 0), (10, 0), (10, 10), (0, 10)], {1, 3}),
                 "L": (L_PLAN, {1, 4}),
                 "T": ([(0, 0), (24, 0), (24, 8), (16, 8), (16, 20), (8, 20), (8, 8), (0, 8)], {1, 4, 7}),
                 "U": ([(0, 0), (24, 0), (24, 16), (16, 16), (16, 7), (8, 7), (8, 16), (0, 16)], {2, 6}),
                 "trapezoid": ([(0, 0), (22, 0), (18, 10), (3, 10)], {1, 3}),
                 "crooked side": ([(0, 0), (20, 0), (21.5, 10), (0, 10)], {1, 3})}
        for name, (ring, ends) in cases.items():
            with self.subTest(plan=name):
                self.assertEqual(roofs.default_gables(ring), ends)        # those of the proof (study 16, A.5)

    def test_the_ridge_height_gives_the_slope(self):
        pitches, dropped = roofs.pitched(HOUSE, 6.0, 45.0, {1, 3}, ridge=8.0)
        self.assertEqual(dropped, set())
        for p in pitches:
            self.assertAlmostEqual(p.tilt, math.degrees(math.atan(2.0 / 4.0)), places=9)   # 2 m up over 4 m
        self.assertAlmostEqual(roofs.ridge_height(pitches), 8.0, places=9)
        # a ridge at or below the eave is no ridge: the slope given stays
        self.assertEqual(roofs.pitched(HOUSE, 6.0, 30.0, {1, 3}, ridge=5.0)[0][0].tilt, 30.0)

    def test_a_gable_end_the_skeleton_cannot_take_becomes_an_eave(self):
        # a rectangle with a bump below: with gables on all three sides of the bump no eave would reach it
        ring = [(8.866, -3.97), (8.866, 0.0), (0.0, 0.0), (0.0, 12.305), (29.879, 12.305), (29.879, 0.0),
                (12.095, 0.0), (12.095, -3.97)]
        pitches, dropped = roofs.pitched(ring, 6.0, 30.0, {0, 2, 3, 6, 7})
        self.assertEqual(dropped, {0, 6})                       # the sides beside an inner corner
        self.assertEqual([p.side for p in pitches], [0, 1, 4, 5, 6])

    def test_the_ridges_are_the_level_edges_at_the_top(self):
        self.assertEqual(roofs.ridges(roofs.gable(HOUSE, 6.0, 30.0), 6.0), [((12.0, 4.0), (0.0, 4.0))])
        self.assertEqual(roofs.ridges(roofs.hip(HOUSE, 6.0, 30.0), 6.0), [((8.0, 4.0), (4.0, 4.0))])
        self.assertEqual(len(roofs.ridges(roofs.gable(L_PLAN, 6.0, 30.0), 6.0)), 2)     # one on each arm
        self.assertEqual(roofs.ridges(roofs.flat(HOUSE, 6.0), 6.0), [])

    def test_a_free_pitch_is_a_plane_on_its_eave(self):
        p = roofs.free([(0, 0), (10, 0), (10, 5), (0, 5)], eave_side=2, eave=4.0, tilt=20.0)
        self.assertAlmostEqual(p.azimuth, 180.0, places=6)       # eave on the North side
        self.assertAlmostEqual(p.z(5, 5), 4.0, places=9)
        self.assertGreater(p.z(5, 0), 4.0)


if __name__ == "__main__":
    unittest.main()
