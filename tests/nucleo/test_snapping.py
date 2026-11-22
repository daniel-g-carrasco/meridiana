"""Drawing aids: the point goes where a CAD user expects, and Ctrl lets it go free."""

import unittest

import _setup  # noqa: F401

from meridiana.core.geometry.snapping import Snapper, ortho

SCALE = 0.05          # metres per pixel: a roof seen at a working zoom


class Directions(unittest.TestCase):
    def setUp(self):
        self.s = Snapper(tolerance_px=10)

    def test_a_right_angle_from_the_last_side(self):
        r = self.s.snap((10.2, 5.0), [(0.0, 0.0), (10.0, 0.0)], SCALE)
        self.assertEqual(r.kind, "direction")
        self.assertAlmostEqual(r.point[0], 10.0, places=9)
        self.assertAlmostEqual(r.point[1], 5.0, places=9)
        self.assertEqual(r.guides[0].label, "90°")
        self.assertAlmostEqual(r.turn, 90.0, places=6)

    def test_the_extension_of_the_last_side(self):
        r = self.s.snap((15.0, 0.3), [(0.0, 0.0), (10.0, 0.0)], SCALE)
        self.assertEqual(r.guides[0].kind, "extension")
        self.assertAlmostEqual(r.point[1], 0.0, places=9)

    def test_polar_steps_from_the_first_point(self):
        r = Snapper(polar_step=15).snap((7.0, 7.3), [(0.0, 0.0)], SCALE)
        self.assertEqual(r.guides[0].kind, "polar")
        self.assertAlmostEqual(r.bearing, 45.0, places=6)

    def test_parallel_to_an_edge_passed_over(self):
        s = Snapper(polar_step=0)
        s.set_references([((0.0, 20.0), (30.0, 30.0))])
        # the cursor passes over the reference edge, then the drawing goes on far from it
        s.snap((15.0, 25.0), [(0.0, 10.0)], SCALE)
        r = s.snap((15.0, 15.1), [(0.0, 10.0)], SCALE)
        self.assertEqual(r.guides[0].kind, "parallel")
        self.assertAlmostEqual(r.bearing, 71.565, places=2)

    def test_an_edge_not_passed_over_offers_nothing_far_away(self):
        s = Snapper(polar_step=0)
        s.set_references([((0.0, 20.0), (30.0, 30.0))])
        r = s.snap((15.0, 15.1), [(0.0, 10.0)], SCALE)
        self.assertEqual(r.kind, "free")


class Objects(unittest.TestCase):
    def test_a_vertex_wins_over_a_direction(self):
        s = Snapper()
        s.set_references([((10.1, 5.1), (30.0, 5.1))])
        r = s.snap((10.15, 5.05), [(0.0, 0.0), (10.0, 0.0)], SCALE)
        self.assertEqual(r.kind, "vertex")
        self.assertEqual(r.point, (10.1, 5.1))

    def test_the_midpoint_of_an_edge(self):
        s = Snapper()
        s.set_references([((0.0, 10.0), (20.0, 10.0))])
        r = s.snap((10.1, 10.2), [], SCALE)
        self.assertEqual(r.kind, "midpoint")
        self.assertEqual(r.point, (10.0, 10.0))

    def test_back_on_the_first_point_closes_the_outline(self):
        r = Snapper().snap((0.1, 0.2), [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0)], SCALE)
        self.assertEqual(r.kind, "close")
        self.assertEqual(r.point, (0.0, 0.0))

    def test_a_point_on_an_edge(self):
        s = Snapper()
        s.set_references([((0.0, 10.0), (20.0, 10.0))])
        r = s.snap((5.0, 10.2), [], SCALE)
        self.assertEqual(r.kind, "edge")
        self.assertAlmostEqual(r.point[1], 10.0, places=9)


class Rectangles(unittest.TestCase):
    def test_the_fourth_corner_finds_itself(self):
        # three corners of a 10 x 5 rectangle drawn: the fourth sits where the right angle from the last
        # side meets the perpendicular through the first point
        r = Snapper().snap((0.3, 5.2), [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0)], SCALE)
        self.assertEqual(r.kind, "intersection")
        self.assertAlmostEqual(r.point[0], 0.0, places=9)
        self.assertAlmostEqual(r.point[1], 5.0, places=9)
        self.assertAlmostEqual(r.area, 50.0, places=6)

    def test_a_guide_stops_on_an_edge(self):
        s = Snapper()
        s.set_references([((0.0, 8.0), (30.0, 8.0))])
        r = s.snap((10.25, 8.2), [(0.0, 0.0), (10.0, 0.0)], SCALE)
        self.assertEqual(r.kind, "intersection")
        self.assertAlmostEqual(r.point[0], 10.0, places=9)
        self.assertAlmostEqual(r.point[1], 8.0, places=9)


class Control(unittest.TestCase):
    def test_free_drawing_takes_the_cursor_as_it_is(self):
        r = Snapper().snap((10.2, 5.0), [(0.0, 0.0), (10.0, 0.0)], SCALE, free=True)
        self.assertEqual(r.kind, "free")
        self.assertEqual(r.point, (10.2, 5.0))
        self.assertAlmostEqual(r.length, (0.2 ** 2 + 25) ** 0.5, places=9)

    def test_the_tolerance_follows_the_zoom(self):
        # the same 0.2 m off the guide: 4 px at a working zoom, 200 px zoomed in
        far = Snapper().snap((10.2, 5.0), [(0.0, 0.0), (10.0, 0.0)], 0.001)
        self.assertEqual(far.kind, "free")


class Measurements(unittest.TestCase):
    def test_length_bearing_and_turn(self):
        r = Snapper().snap((3.0, 4.0), [(0.0, 0.0)], SCALE, free=True)
        self.assertAlmostEqual(r.length, 5.0)
        self.assertAlmostEqual(r.bearing, 36.8699, places=3)
        self.assertIsNone(r.turn)

    def test_on_the_last_corner_there_is_no_segment(self):
        # right after a click the pointer is still on the corner just placed: a guide may project it a
        # hair away, and that is no segment with a direction (it once crashed the measures)
        for free in (True, False):
            r = Snapper().snap((10.0, 0.0), [(0.0, 0.0), (10.0, 0.0)], SCALE, free=free)
            self.assertIsNone(r.length)
            self.assertIsNone(r.bearing)
            self.assertIsNone(r.turn)

    def test_a_left_turn_is_positive(self):
        r = Snapper().snap((10.0, 5.0), [(0.0, 0.0), (10.0, 0.0)], SCALE, free=True)
        self.assertAlmostEqual(r.turn, 90.0, places=6)
        r = Snapper().snap((10.0, -5.0), [(0.0, 0.0), (10.0, 0.0)], SCALE, free=True)
        self.assertAlmostEqual(r.turn, -90.0, places=6)


class Ortho(unittest.TestCase):
    def test_the_first_side_goes_east_or_north(self):
        self.assertEqual(ortho([(1.0, 1.0)], (5.0, 2.0)), (5.0, 1.0))
        self.assertEqual(ortho([(1.0, 1.0)], (2.0, -6.0)), (1.0, -6.0))

    def test_then_square_to_the_first_side(self):
        chain = [(0.0, 0.0), (3.0, 4.0)]                    # a side at 36.87° from East
        x, y = ortho(chain, (0.0, 8.0))                     # mostly across it
        self.assertAlmostEqual((x - 3.0) * 3 + (y - 4.0) * 4, 0.0)      # perpendicular to the first side
        x, y = ortho(chain, (7.0, 7.0))                     # mostly along it
        self.assertAlmostEqual((x - 3.0) * 4 - (y - 4.0) * 3, 0.0)      # parallel to it


class MeasuringSwitches(unittest.TestCase):
    """What the measuring tool asks for (study 46): only some objects, no guides; the drawing's answer is unchanged."""

    def setUp(self):
        self.s = Snapper()
        self.s.set_references([((0.0, 0.0), (20.0, 0.0)), ((20.0, 0.0), (20.0, 10.0))])

    def test_only_the_kinds_asked(self):
        near_mid = (10.1, 0.1)
        self.assertEqual(self.s.snap(near_mid, [], SCALE).kind, "midpoint")
        r = self.s.snap(near_mid, [], SCALE, kinds=frozenset({"vertex", "edge"}))
        self.assertEqual((r.kind, r.point), ("edge", (10.1, 0.0)))
        r = self.s.snap(near_mid, [], SCALE, kinds=frozenset({"vertex"}))
        self.assertEqual((r.kind, r.point), ("free", near_mid))
        self.assertEqual(self.s.snap((19.9, 0.1), [], SCALE, kinds=frozenset({"midpoint"})).kind, "free")
        self.assertEqual(self.s.snap((19.9, 0.1), [], SCALE, kinds=frozenset({"vertex"})).kind, "vertex")

    def test_no_directions_leaves_a_point_in_free_space_where_it_is(self):
        chain = [(30.0, 30.0)]
        cursor = (37.0, 37.3)                               # 0.3 m off the 45° step: the polar guide takes it
        self.assertEqual(self.s.snap(cursor, chain, SCALE).kind, "direction")
        r = self.s.snap(cursor, chain, SCALE, directions=False)
        self.assertEqual((r.kind, r.point, r.guides), ("free", cursor, []))
        self.assertAlmostEqual(r.length, ((7.0 ** 2) + (7.3 ** 2)) ** 0.5)

    def test_the_nearest_segment(self):
        self.assertEqual(self.s.nearest_segment((19.8, 5.0), SCALE), ((20.0, 0.0), (20.0, 10.0)))
        self.assertIsNone(self.s.nearest_segment((15.0, 5.0), SCALE))

    def test_the_references_far_from_the_cursor_change_no_answer(self):
        """The references are filtered by their boxes before snapping: the answers are those of the whole list."""
        import random
        rng = random.Random(46)
        segments = []
        for _ in range(300):
            a = (rng.uniform(0, 100), rng.uniform(0, 100))
            segments.append((a, (a[0] + rng.uniform(-8, 8), a[1] + rng.uniform(-8, 8))))
        filtered, whole = Snapper(), Snapper()
        filtered.set_references(segments)
        whole.set_references(segments)
        whole._near = lambda c, tol, reach=6: (whole.segments, whole.points)     # no filter: the answers of before
        chain = [(50.0, 50.0), (60.0, 52.0)]
        for _ in range(400):
            c = (rng.uniform(0, 100), rng.uniform(0, 100))
            for ch in ([], chain[:1], chain):
                a, b = filtered.snap(c, ch, 0.2), whole.snap(c, ch, 0.2)
                self.assertEqual((a.kind, a.point, a.guides), (b.kind, b.point, b.guides), (c, ch))
            self.assertEqual(filtered.nearest_segment(c, 0.2), whole.nearest_segment(c, 0.2))


if __name__ == "__main__":
    unittest.main()
