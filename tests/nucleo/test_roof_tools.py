"""The roof tools of study 22 (R274, R275), without Qt: a free pitch by its numbers (depth, slope, ridge height, eave and
ridge swapped) and the roof a drawn ridge stands for, on a rectangle, an L, a T, a trapezoid, and on the 306 footprints
of the skeleton's reference."""

import json
import math
import unittest

import _setup

from meridiana import roofs, skeleton

RECT = [(0.0, 0.0), (16.0, 0.0), (16.0, 10.0), (0.0, 10.0)]
L_SHAPE = [(0.0, 0.0), (20.0, 0.0), (20.0, 8.0), (8.0, 8.0), (8.0, 20.0), (0.0, 20.0)]
T_SHAPE = [(0.0, 0.0), (10.0, 0.0), (10.0, 4.0), (6.0, 4.0), (6.0, 10.0), (4.0, 10.0), (4.0, 4.0), (0.0, 4.0)]
TRAPEZOID = [(0.0, 0.0), (16.0, 0.0), (13.0, 10.0), (3.0, 10.0)]


class FreePitch(unittest.TestCase):
    def test_the_depth_the_ridge_and_the_slope_say_the_same_thing(self):
        self.assertAlmostEqual(roofs.free_depth(RECT, 0), 10.0)
        self.assertAlmostEqual(roofs.free_depth(RECT, 1), 16.0)
        ridge = roofs.free_ridge(RECT, 0, 6.0, 20.0)
        self.assertAlmostEqual(ridge, 6.0 + 10.0 * math.tan(math.radians(20.0)))
        self.assertAlmostEqual(roofs.free_tilt(RECT, 0, 6.0, ridge), 20.0)
        self.assertAlmostEqual(roofs.free_tilt(RECT, 0, 6.0, 8.5), math.degrees(math.atan(2.5 / 10.0)))

    def test_a_ridge_at_or_under_the_eave_is_refused_with_the_reason(self):
        for ridge in (6.0, 5.0):
            with self.assertRaises(ValueError) as said:
                roofs.free_tilt(RECT, 0, 6.0, ridge)
            self.assertIn("eave", str(said.exception))

    def test_the_side_across_is_the_parallel_one_on_a_rectangle_and_the_far_one_on_a_triangle(self):
        self.assertEqual(roofs.opposite_side(RECT, 0), 2)
        self.assertEqual(roofs.opposite_side(RECT, 3), 1)
        self.assertIn(roofs.opposite_side([(0, 0), (10, 0), (5, 4)], 0), (1, 2))

    def test_swapping_eave_and_ridge_turns_the_pitch_over_at_the_same_eave(self):
        ring = [(0.0, 0.0), (16.0, 0.0), (16.0, 5.0), (0.0, 5.0)]
        down = roofs.free_spec(ring, False, 6.0, 20.0)
        up = roofs.free_spec(ring, True, 6.0, 20.0)
        self.assertEqual((down["eave_side"], up["eave_side"]), (0, 2))
        a, b = roofs.free(down["ring"], 0, 6.0, 20.0), roofs.free(up["ring"], 2, 6.0, 20.0)
        self.assertAlmostEqual(a.z(8.0, 0.0), 6.0)                 # first drawn side low...
        self.assertAlmostEqual(b.z(8.0, 0.0), roofs.free_ridge(ring, 0, 6.0, 20.0))   # ...or high
        self.assertAlmostEqual(b.z(8.0, 5.0), 6.0)
        self.assertAlmostEqual((a.azimuth - b.azimuth) % 360.0, 180.0)

    def test_a_ridge_written_gives_the_slope_from_the_eave_it_goes_down_to(self):
        spec = roofs.free_spec(RECT, True, 6.0, 35.0, ridge=9.0)
        self.assertEqual(spec["eave_side"], 2)
        self.assertAlmostEqual(spec["tilt"], math.degrees(math.atan(3.0 / 10.0)))
        with self.assertRaises(ValueError):
            roofs.free_spec(RECT, False, 6.0, 35.0, ridge=6.0)


class FromRidge(unittest.TestCase):
    def test_a_ridge_along_a_rectangle_end_to_end_is_a_gable_roof_on_its_axis(self):
        got = roofs.from_ridge(RECT, [(0.3, 5.0), (15.7, 5.0)], 6.0, 20.0)
        self.assertEqual(got.kind, "gable")
        self.assertEqual(got.edges, ["eave", "gable", "eave", "gable"])
        self.assertFalse(got.off_axis)
        self.assertEqual(len(got.pitches), 2)
        self.assertAlmostEqual(roofs.ridge_height(got.pitches), 6.0 + 5.0 * math.tan(math.radians(20.0)))

    def test_the_ridge_height_given_sets_the_slope(self):
        got = roofs.from_ridge(RECT, [(0.0, 5.0), (16.0, 5.0)], 6.0, 20.0, ridge=9.0)
        self.assertAlmostEqual(roofs.ridge_height(got.pitches), 9.0)
        self.assertAlmostEqual(got.pitches[0].tilt, math.degrees(math.atan(3.0 / 5.0)))

    def test_a_ridge_ending_inside_makes_a_hip_there(self):
        hip = roofs.from_ridge(RECT, [(5.0, 5.0), (11.0, 5.0)], 6.0, 20.0)
        self.assertEqual((hip.kind, hip.edges), ("hip", ["eave"] * 4))
        half = roofs.from_ridge(RECT, [(0.2, 5.0), (11.0, 5.0)], 6.0, 20.0)
        self.assertEqual(half.edges, ["eave", "eave", "eave", "gable"])
        self.assertEqual(len(half.pitches), 3)

    def test_a_ridge_across_makes_the_long_sides_the_gable_ends(self):
        got = roofs.from_ridge(RECT, [(8.0, 0.2), (8.0, 9.8)], 6.0, 20.0)
        self.assertEqual(got.edges, ["gable", "eave", "gable", "eave"])
        self.assertFalse(got.off_axis)

    def test_a_ridge_off_the_axis_is_put_on_it_and_said(self):
        got = roofs.from_ridge(RECT, [(0.3, 6.5), (15.7, 6.5)], 6.0, 20.0)
        self.assertTrue(got.off_axis)
        self.assertEqual(got.edges, ["eave", "gable", "eave", "gable"])
        (a, b), = roofs.ridges(got.pitches, 6.0)
        self.assertAlmostEqual(a[1], 5.0)                      # the roof's ridge stays on the axis
        self.assertAlmostEqual(b[1], 5.0)

    def test_an_l_with_its_ridge_bent_has_its_gable_ends_on_the_arms_and_the_valley(self):
        got = roofs.from_ridge(L_SHAPE, [(4.0, 19.8), (4.0, 4.0), (19.8, 4.0)], 6.0, 20.0)
        self.assertEqual({i for i, e in enumerate(got.edges) if e == "gable"}, roofs.default_gables(L_SHAPE))
        self.assertFalse(got.off_axis)
        self.assertEqual(got.dropped, [])

    def test_a_t_drawn_back_and_forth_has_three_gable_ends(self):
        got = roofs.from_ridge(T_SHAPE, [(0.1, 2.0), (5.0, 2.0), (9.9, 2.0), (5.0, 2.0), (5.0, 9.9)], 6.0, 20.0)
        self.assertEqual({i for i, e in enumerate(got.edges) if e == "gable"}, {1, 4, 7})
        self.assertFalse(got.off_axis)

    def test_a_trapezoid_takes_its_slanted_sides_as_gable_ends(self):
        got = roofs.from_ridge(TRAPEZOID, [(1.6, 5.0), (14.4, 5.0)], 6.0, 20.0)
        self.assertEqual(got.edges, ["eave", "gable", "eave", "gable"])
        self.assertFalse(got.off_axis)

    def test_an_outline_crossing_itself_cannot_carry_it(self):
        with self.assertRaises(skeleton.SkeletonError):
            roofs.from_ridge([(0, 0), (10, 10), (10, 0), (0, 10)], [(1, 5), (9, 5)], 6.0, 20.0)

    def test_the_run_is_half_the_width_of_a_rectangle(self):
        self.assertAlmostEqual(roofs.ridge_run(RECT), 5.0)
        self.assertEqual(roofs.ridge_run([(0, 0), (10, 10), (10, 0), (0, 10)]), 0.0)

    def test_on_the_306_reference_footprints_the_ridges_drawn_back_give_the_same_gable_roof(self):
        # study 22, 3.5, the proof that decides: the ridge of the gable roof with its gable ends, drawn again,
        # touches exactly those sides, so the pitches are the same
        cases = json.loads((_setup.ROOT / "docs" / "studio" / "16-prove" / "scheletro-riferimento.json")
                           .read_text(encoding="utf-8"))["cases"]
        self.assertEqual(len(cases), 306)
        for case in cases:
            ring = [tuple(p) for p in case["ring"]]
            found, dropped = roofs.pitched(ring, 0.0, 30.0, roofs.default_gables(ring))
            touched = set()
            for a, b in roofs.ridges(found, 0.0):
                touched |= roofs.ridge_gables(ring, [a, b])
            self.assertEqual(touched, roofs.default_gables(ring) - dropped, case["name"])


if __name__ == "__main__":
    unittest.main()
