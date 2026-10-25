"""Where a string's line runs (string_paths.py, R117): straight between modules next to each other, around the modules
it skips without passing over them, and a colour that no string touching it has."""

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

    def test_a_module_skipped_is_gone_around_and_never_passed_over(self):
        for gap in (0.0, 0.8):
            r = string_paths.Router(block(3, 6, gap))
            for a, b in ((0, 2), (0, 13), (2, 15), (0, 17), (6, 9)):
                with self.subTest(gap=gap, a=a, b=b):
                    (path, jump), = r.legs([a, b])
                    self.assertTrue(jump)
                    self.assertGreater(len(path), 2)
                    self.assertEqual(enters(r, path, (a, b)), [])
                    self.assertEqual(path[0], tuple(r.centres[a]))
                    self.assertEqual(path[-1], tuple(r.centres[b]))

    def test_a_jump_across_many_modules_stays_straight_and_is_still_a_jump(self):
        r = string_paths.Router(block(2, 200, 0.6))
        (path, jump), = r.legs([199, 200])                     # the end of a row to the start of the next
        self.assertTrue(jump)
        self.assertEqual(len(path), 2)

    def test_eight_thousand_modules_are_routed_in_well_under_a_second(self):
        import time
        quads = block(40, 200, 0.6)
        start = time.perf_counter()
        r = string_paths.Router(quads)
        legs = r.legs(list(range(len(quads))))
        self.assertLess(time.perf_counter() - start, 3.0)       # about 0,15 s on Daniel's PC, room for a busy one
        self.assertEqual(sum(j for _p, j in legs), 39)          # only the turns from a row to the next


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
