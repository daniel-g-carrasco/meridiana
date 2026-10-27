"""Where a string's line runs (string_paths.py, R117, R184): straight between modules next to each other, direct or
orthogonal dashed jumps, separate lanes and dashes, and a colour that no string touching it has."""

import unittest

import _setup  # noqa: F401
import numpy as np

from meridiana import string_paths

W, H = 1.13, 2.28


def block(rows: int, per_row: int, gap: float = 0.0) -> np.ndarray:
    """Modules side by side in rows, `gap` metres between the rows (0: a table, the rows touching)."""
    quads = []
    for r in range(rows):
        for c in range(per_row):
            x, y = c * W, r * (H + gap)
            quads.append([[x, y], [x + W, y], [x + W, y + H], [x, y + H]])
    return np.array(quads)


def enters(router, path, ends) -> list[int]:
    """The modules other than `ends` whose inside the path enters (a micrometre in from their edges: running along
    an edge is not entering)."""
    import shapely
    line = shapely.LineString(path)
    return [k for k in range(len(router.quads)) if k not in ends and
            shapely.relate_pattern(line, shapely.Polygon(router.quads[k]).buffer(-1e-6, join_style="mitre"),
                                   "T********")]


class Lines(unittest.TestCase):
    def test_modules_side_by_side_and_corner_to_corner_are_joined_straight(self):
        r = string_paths.Router(block(3, 6))
        (path, jump), = r.legs([0, 1])
        self.assertFalse(jump)
        self.assertEqual(len(path), 2)
        self.assertFalse(r.legs([0, 7])[0][1])                  # corner to corner, the line through the corner
        self.assertFalse(r.legs([5, 11])[0][1])                 # the end of a row and the next row's end

    def test_a_module_skipped_makes_a_jump_between_the_two_centres(self):
        for gap in (0.0, 0.8):
            r = string_paths.Router(block(3, 6, gap))
            for a, b in ((0, 2), (0, 13), (2, 15), (0, 17), (6, 9)):
                with self.subTest(gap=gap, a=a, b=b):
                    (path, jump), = r.legs([a, b])
                    self.assertTrue(jump)
                    self.assertEqual(path[0], tuple(r.centres[a]))
                    self.assertEqual(path[-1], tuple(r.centres[b]))

    def test_same_row_jump_is_direct_and_cross_row_jump_is_an_orthogonal_bridge_in_the_gap(self):
        r = string_paths.Router(block(2, 6, 0.8))
        direct = r.route(0, 2)
        self.assertEqual(direct, [tuple(r.centres[0]), tuple(r.centres[2])])
        path = r.route(0, 11)
        self.assertEqual(len(path), 4)
        self.assertEqual(enters(r, path, (0, 11)), [])
        for a, b in zip(path, path[1:], strict=False):
            self.assertTrue(abs(a[0] - b[0]) < 1e-9 or abs(a[1] - b[1]) < 1e-9, (a, b))
        self.assertEqual(path[0][0], path[1][0])
        self.assertEqual(path[1][1], path[2][1])
        self.assertEqual(path[2][0], path[3][0])
        self.assertGreater(path[1][1], 2.28)
        self.assertLess(path[1][1], 3.08)

    def test_a_jump_across_many_modules_stays_straight_and_is_still_a_jump(self):
        r = string_paths.Router(block(2, 200, 0.6))
        (path, jump), = r.legs([199, 200])                     # the end of a row to the start of the next
        self.assertTrue(jump)
        self.assertEqual(len(path), 2)

    def test_three_direct_jumps_sharing_a_corner_have_distinct_dash_lanes_at_two_zooms(self):
        import shapely
        strings = [[6, 8], [1, 13], [0, 14]]               # three disjoint strings around module 7 (R134)
        for scale in (10.0, 25.0):
            with self.subTest(scale=scale):
                r = string_paths.Router(block(3, 6, 0.8))
                before = [[leg[0] for leg in r.legs(order)] for order in strings]
                self.assertEqual(shapely.distance(shapely.LineString(before[0][0]),
                                                  shapely.LineString(before[1][0])), 0.0)
                routed, lanes = r.legs_together(strings, 6.0 / scale)
                self.assertEqual(len(set(lanes)), 3)
                for i in range(len(strings)):
                    self.assertTrue(routed[i][0][1])
                    self.assertEqual(routed[i][0][0][0], before[i][0][0])
                    self.assertEqual(routed[i][0][0][-1], before[i][0][-1])

    def test_two_overlapping_bridges_take_separate_screen_lanes(self):
        import shapely
        strings = [[0, 9], [1, 10]]
        r = string_paths.Router(block(2, 6, 0.8))
        before = [[leg[0] for leg in r.legs(order)] for order in strings]
        self.assertEqual(shapely.distance(shapely.LineString(before[0][0]), shapely.LineString(before[1][0])), 0.0)
        routed, lanes = r.legs_together(strings, 6.0 / 25.0)
        self.assertEqual(len(set(lanes)), 2)
        self.assertNotEqual(routed[1][0][0], before[1][0][0])
        for i, order in enumerate(strings):
            self.assertEqual(enters(r, routed[i][0][0], (order[0], order[-1])), [])
            self.assertEqual(routed[i][0][0][0], before[i][0][0])
            self.assertEqual(routed[i][0][0][-1], before[i][0][-1])
        distance = shapely.distance(shapely.LineString(routed[0][0][0]), shapely.LineString(routed[1][0][0]))
        self.assertGreaterEqual(distance * 25.0, 3.0)

    def test_touching_rows_get_distinct_dash_lanes(self):
        strings = [[6, 8], [1, 13], [0, 14]]
        r = string_paths.Router(block(3, 6))
        routed, lanes = r.legs_together(strings, 0.6)
        self.assertEqual(len(set(lanes)), 3)                       # no free geometry: the plan varies the dash
        for order, legs in zip(strings, routed, strict=True):
            self.assertTrue(legs[0][1])
            self.assertEqual(legs[0][0][0], tuple(r.centres[order[0]]))
            self.assertEqual(legs[0][0][-1], tuple(r.centres[order[-1]]))

    def test_one_string_and_strings_that_do_not_meet_keep_their_original_paths(self):
        r = string_paths.Router(block(3, 6, 0.8))
        for strings in ([[0, 2]], [[0, 2], [3, 5]]):
            with self.subTest(strings=strings):
                routed, lanes = r.legs_together(strings, 0.6)
                self.assertEqual(routed, [r.legs(order) for order in strings])
                self.assertEqual(lanes, [0] * len(strings))

    def test_eight_thousand_modules_are_routed_in_well_under_a_second(self):
        import time
        quads = block(40, 200, 0.6)
        start = time.perf_counter()
        r = string_paths.Router(quads)
        legs = r.legs(list(range(len(quads))))
        self.assertLess(time.perf_counter() - start, 3.0)       # about 0,15 s on Daniel's PC, room for a busy one
        self.assertEqual(sum(j for _p, j in legs), 39)          # only the turns from a row to the next
        start = time.perf_counter()
        routed, lanes = r.legs_together([list(range(len(quads)))], 0.06)
        self.assertLess(time.perf_counter() - start, 3.0)
        self.assertEqual((routed, lanes), ([legs], [0]))


class Colours(unittest.TestCase):
    def test_strings_that_touch_never_share_a_colour(self):
        r = string_paths.Router(block(3, 6))
        strings = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11], [12, 13, 14]]
        out = string_paths.colours(strings, r, 2)
        self.assertEqual(out[:2], [0, 1])
        self.assertNotEqual(out[0], out[1])                     # 0-2 and 3-5 side by side
        self.assertNotEqual(out[1], out[2])                     # 3-5 over 6-8
        self.assertEqual(string_paths.colours(strings, None, 3), [0, 1, 2, 0, 1])      # without the plan: in turn

    def test_with_their_own_numbers_the_others_keep_their_colour_when_one_goes(self):
        r = string_paths.Router(block(1, 48))
        strings = [list(range(k, k + 4)) for k in range(0, 48, 6)]
        seeds = [11, 3, 25, 7, 40, 18, 2, 33]
        before = string_paths.colours(strings, r, 8, seeds)
        after = string_paths.colours(strings[:2] + strings[3:], r, 8, seeds[:2] + seeds[3:])
        self.assertEqual(after, before[:2] + before[3:])

    def test_far_strings_keep_their_place_in_the_list(self):
        r = string_paths.Router(block(1, 48))
        strings = [list(range(k, k + 4)) for k in range(0, 48, 6)]          # two modules free between each two
        self.assertEqual(string_paths.colours(strings, r, 8), list(range(8)))

    def test_strings_in_rows_one_behind_the_other_are_neighbours_across_the_gap(self):
        r = string_paths.Router(block(2, 6, 1.5))                           # rows 1,5 m apart, as sheds are
        self.assertEqual(string_paths.colours([[0, 1, 2], [6, 7, 8]], r, 8, [3, 3]), [3, 4])


if __name__ == "__main__":
    unittest.main()
