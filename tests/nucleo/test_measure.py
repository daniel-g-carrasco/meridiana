"""The numbers of a measurement in space and its constraints (study 46): spans of known geometry, every constraint on
a point of the plan and on a ray of the 3D view, and the degenerate cases, which answer without NaN or errors."""

import math
import unittest

import _setup  # noqa: F401

from meridiana.core.geometry import measure as m

S30 = math.sin(math.radians(30))
C30 = math.cos(math.radians(30))


def close(test, p, q, places=9):
    test.assertIsNotNone(p)
    for a, b in zip(p, q, strict=True):
        test.assertAlmostEqual(a, b, places=places)


def no_nan(value):
    return all(math.isfinite(v) for v in value if v is not None)


class Spans(unittest.TestCase):
    def test_a_pitch_of_30_degrees_up_its_slope(self):
        # 6 m in plan up a 30° pitch facing South: the true length is 6 / cos 30°
        s = m.span((0.0, 0.0, 3.0), (0.0, 6.0, 3.0 + 6.0 * math.tan(math.radians(30))))
        self.assertAlmostEqual(s.plan, 6.0, places=9)
        self.assertAlmostEqual(s.length, 6.0 / C30, places=9)
        self.assertAlmostEqual(s.rise, 6.0 * math.tan(math.radians(30)), places=9)
        self.assertAlmostEqual(s.slope, 30.0, places=9)
        self.assertAlmostEqual(s.percent, 100 * math.tan(math.radians(30)), places=9)
        self.assertAlmostEqual(s.bearing, 0.0, places=9)
        self.assertFalse(s.level)

    def test_the_study_example(self):
        # «6,78 m; in pianta 6,40 m; dislivello 2,24 m; 19,3°»
        s = m.span((0.0, 0.0, 0.0), (6.4, 0.0, 2.24))
        self.assertAlmostEqual(s.length, 6.78, places=2)
        self.assertAlmostEqual(s.slope, 19.3, places=1)
        self.assertAlmostEqual(s.percent, 35.0, places=1)
        self.assertAlmostEqual(s.bearing, 90.0, places=9)

    def test_down_hill_and_bearing_clockwise_from_north(self):
        s = m.span((0.0, 0.0, 5.0), (-3.0, -3.0, 2.0))
        self.assertAlmostEqual(s.rise, -3.0)
        self.assertAlmostEqual(s.bearing, 225.0)
        self.assertAlmostEqual(s.slope, math.degrees(math.atan(3 / math.hypot(3, 3))))

    def test_level_and_vertical_and_none(self):
        self.assertTrue(m.span((0, 0, 1), (4, 0, 1.004)).level)
        v = m.span((1, 1, 0), (1, 1, 4))
        self.assertEqual((v.plan, v.length, v.slope, v.percent, v.bearing), (0.0, 4.0, 90.0, None, None))
        z = m.span((1, 1, 1), (1, 1, 1))
        self.assertEqual((z.length, z.plan, z.slope, z.percent, z.bearing), (0.0, 0.0, 0.0, None, None))

    def test_a_bearing_never_reads_360(self):
        s = m.span((0.0, 0.0, 0.0), (-1e-17, 5.0, 0.0))
        self.assertGreaterEqual(s.bearing, 0.0)
        self.assertLess(s.bearing, 360.0)


class Paths(unittest.TestCase):
    def test_totals_open_and_closed(self):
        square = [(0, 0, 0), (4, 0, 0), (4, 3, 0), (0, 3, 0)]
        self.assertEqual(m.totals(square), (11.0, 11.0))
        self.assertEqual(m.totals(square, closed=True), (14.0, 14.0))
        self.assertAlmostEqual(m.plan_area(square), 12.0)

    def test_a_path_up_a_pitch(self):
        true, plan = m.totals([(0, 0, 0), (0, 4, 4 * S30 / C30), (3, 4, 4 * S30 / C30)])
        self.assertAlmostEqual(plan, 7.0)
        self.assertAlmostEqual(true, 4 / C30 + 3)

    def test_area_in_plan_of_a_tilted_ring_and_of_too_few_points(self):
        self.assertAlmostEqual(m.plan_area([(0, 0, 0), (2, 0, 0), (2, 2, 1.0), (0, 2, 1.0)]), 4.0)
        self.assertEqual(m.plan_area([(0, 0, 0), (1, 1, 1)]), 0.0)
        self.assertEqual(m.totals([]), (0, 0))


class Helpers(unittest.TestCase):
    def test_the_foot_of_the_perpendicular(self):
        close(self, m.foot((3.0, 5.0, 2.0), (0.0, 0.0, 0.0), (10.0, 0.0, 0.0)), (3.0, 0.0, 0.0))
        # beyond the end of the edge, on its line
        close(self, m.foot((15.0, 2.0, 0.0), (0.0, 0.0, 0.0), (10.0, 0.0, 0.0)), (15.0, 0.0, 0.0))
        # an edge of no length: its point
        close(self, m.foot((3.0, 5.0, 2.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0)), (1.0, 1.0, 1.0))

    def test_a_length_along_a_direction(self):
        close(self, m.along((1, 1, 0), (0, 3, 4), 10.0), (1, 7, 8))
        # the length in plan: up a 30° slope, 6 m in plan
        p = m.along((0, 0, 0), (0, C30, S30), 6.0, plan=True)
        self.assertAlmostEqual(math.hypot(p[0], p[1]), 6.0)
        # a vertical direction has no length in plan: the true length
        close(self, m.along((0, 0, 0), (0, 0, 1), 2.0, plan=True), (0, 0, 2))
        self.assertIsNone(m.along((0, 0, 0), (0, 0, 0), 2.0))
        self.assertIsNone(m.along((0, 0, 0), (1, 0, 0), float("nan")))

    def test_the_length_typed(self):
        self.assertEqual(m.parse_length("2,5"), 2.5)
        self.assertEqual(m.parse_length(" 3.25 m"), 3.25)
        self.assertEqual(m.parse_length("-1,5"), -1.5)
        for bad in ("", "abc", "nan", "inf", None, "1,2,3"):
            self.assertIsNone(m.parse_length(bad), bad)


class OnAPoint(unittest.TestCase):
    """A point of the plan: the constraint seen from above."""

    def test_the_axes(self):
        o = (2.0, 3.0, 1.0)
        close(self, m.constrain_point(m.axis(o, "east"), (7.0, 4.5, 6.0)), (7.0, 3.0, 1.0))
        close(self, m.constrain_point(m.axis(o, "north"), (7.0, 4.5, 6.0)), (2.0, 4.5, 1.0))
        # the vertical seen from above is a point: the height of the point under the pointer
        close(self, m.constrain_point(m.axis(o, "up"), (7.0, 4.5, 6.0)), (2.0, 3.0, 6.0))

    def test_a_sloping_line_keeps_the_point_in_plan(self):
        # a direction up a 30° slope towards North: the point stays at the pointer's North, its height on the line
        p = m.constrain_point(m.line((0, 0, 0), (0, C30, S30)), (0.3, 5.0, 0.0))
        close(self, p, (0.0, 5.0, 5.0 * S30 / C30))

    def test_parallel_and_perpendicular_to_an_edge(self):
        edge = ((0.0, 0.0, 3.0), (10.0, 10.0, 3.0))           # an eave at 45°
        o = (5.0, 0.0, 3.0)
        p = m.constrain_point(m.parallel(o, edge), (9.0, 3.0, 3.0))
        close(self, p, (8.5, 3.5, 3.0))
        q = m.constrain_point(m.perpendicular(o, edge), (4.0, 2.0, 7.0))
        # on the line square to the eave in plan, the height of the surface kept
        self.assertAlmostEqual((q[0] - o[0]) + (q[1] - o[1]), 0.0)
        self.assertAlmostEqual(q[2], 7.0)

    def test_a_pitch_plane_gives_the_height_under_the_point(self):
        # 30° pitch rising to the North from an eave at 3 m
        normal = (0.0, -S30, C30)
        p = m.constrain_point(m.plane((0, 0, 3.0), normal), (4.0, 2.0, 0.0))
        close(self, p, (4.0, 2.0, 3.0 + 2.0 * S30 / C30))

    def test_a_vertical_plane_seen_edge_on(self):
        p = m.constrain_point(m.plane((0, 0, 0), (1, 0, 0)), (3.0, 4.0, 5.0))
        close(self, p, (0.0, 4.0, 5.0))

    def test_square_projection_for_a_snapped_point(self):
        close(self, m.project(m.axis((0, 0, 0), "up"), (3.0, 4.0, 7.5)), (0, 0, 7.5))
        close(self, m.project(m.plane((0, 0, 0), (0, 0, 1)), (3.0, 4.0, 7.5)), (3, 4, 0))


class OnARay(unittest.TestCase):
    """The pointer's ray of the 3D view."""

    def test_an_axis_takes_the_point_nearest_the_ray(self):
        # the eye at 10 m South, 5 m up, looking North and down towards the vertical through the origin
        p = m.constrain_ray(m.axis((0, 0, 0), "up"), (0.0, -10.0, 5.0), (0.0, 10.0, -1.0))
        close(self, p, (0.0, 0.0, 4.0))
        e = m.constrain_ray(m.axis((0, 0, 0), "east"), (3.0, -10.0, 5.0), (0.0, 2.0, -1.0))
        close(self, e, (3.0, 0.0, 0.0))

    def test_a_plane_where_the_ray_meets_it(self):
        normal = (0.0, -S30, C30)                     # the 30° pitch
        p = m.constrain_ray(m.plane((0, 0, 3.0), normal), (2.0, -20.0, 20.0), (0.0, 1.0, -1.0))
        self.assertAlmostEqual(p[2], 3.0 + p[1] * S30 / C30)
        self.assertAlmostEqual(p[0], 2.0)

    def test_perpendicular_in_the_pitch_plane(self):
        # eave along East at 3 m, pitch of 30° rising North: square to the eave in the pitch is straight up the slope
        o = (4.0, 0.0, 3.0)
        both = m.meet(m.perpendicular(o, ((0, 0, 3.0), (10, 0, 3.0))), m.plane(o, (0.0, -S30, C30)))
        self.assertTrue(both.is_line)
        self.assertAlmostEqual(abs(both.direction[1]), C30)
        self.assertAlmostEqual(abs(both.direction[2]), S30)
        p = m.constrain_ray(both, (4.0, 2.0, 20.0), (0.0, 0.0, -1.0))     # from above, 2 m North of the eave
        close(self, p, (4.0, 2.0, 3.0 + 2.0 * S30 / C30))

    def test_degenerate_rays(self):
        up = m.axis((0, 0, 0), "up")
        self.assertIsNone(m.constrain_ray(up, (1.0, 1.0, 9.0), (0.0, 0.0, -1.0)))        # parallel to the line
        floor = m.plane((0, 0, 0), (0, 0, 1))
        self.assertIsNone(m.constrain_ray(floor, (0.0, 0.0, 5.0), (1.0, 0.0, 0.0)))      # parallel to the plane
        self.assertIsNone(m.constrain_ray(floor, (0.0, 0.0, 5.0), (0.0, 0.0, 1.0)))      # behind the eye
        self.assertIsNone(m.constrain_ray(floor, (0.0, 0.0, 5.0), (0.0, 0.0, 0.0)))      # no direction


class Degenerate(unittest.TestCase):
    def test_constraints_of_no_length_are_none(self):
        p = (1.0, 1.0, 1.0)
        self.assertIsNone(m.line(p, (0, 0, 0)))
        self.assertIsNone(m.plane(p, (0, 0, 0)))
        self.assertIsNone(m.parallel(p, (p, p)))
        self.assertIsNone(m.perpendicular(p, (p, p)))

    def test_parallel_planes_do_not_meet(self):
        a, b = m.plane((0, 0, 0), (0, 0, 1)), m.plane((0, 0, 2), (0, 0, -1))
        self.assertIsNone(m.meet(a, b))
        self.assertIsNone(m.meet(a, m.axis((0, 0, 0), "east")))

    def test_nothing_is_nan(self):
        o = (0.0, 0.0, 0.0)
        for c in (m.axis(o, "up"), m.axis(o, "east"), m.plane(o, (1, 0, 0)), m.plane(o, (0, 0, 1))):
            self.assertTrue(no_nan(m.constrain_point(c, o)))
            self.assertTrue(no_nan(m.project(c, o)))
        s = m.span(o, o)
        self.assertTrue(no_nan((s.length, s.plan, s.rise, s.slope, s.percent, s.bearing)))

    def test_point_helpers(self):
        self.assertEqual(m.point3((1, 2)), (1.0, 2.0, 0.0))
        self.assertEqual(m.point3((1, 2), 5), (1.0, 2.0, 5.0))
        self.assertFalse(m.finite((1.0, float("nan"), 0.0)))
        self.assertFalse(m.finite(None))
        self.assertTrue(m.on_plane((3, 4, 0.01), (0, 0, 0), (0, 0, 2), 0.02))
        self.assertFalse(m.on_plane((3, 4, 0.01), (0, 0, 0), (0, 0, 0), 0.02))
        self.assertTrue(m.parallel_normals((0, 0, 1), (0, 0, -3)))


if __name__ == "__main__":
    unittest.main()
