"""The camera of the 3D view in numbers: the turntable keeps the vertical, the orbit turns around the point under
the cursor and leaves it there, the zoom goes towards the cursor, the pan follows the pointer, a middle click
recentres, the standard views look where they say, the animation eases out."""

import math
import random
import unittest

import numpy as np

import _setup  # noqa: F401

from meridiana import camera as cam

W, H = 800.0, 600.0


def framed() -> cam.Camera:
    c = cam.Camera()
    c.fit((0.0, 5.0, 0.0), 25.0, W / H)
    return c


class Orbit(unittest.TestCase):
    def test_the_turntable_keeps_the_vertical_vertical(self):
        c = framed()
        rnd = random.Random(7)
        for _ in range(200):
            c.orbit(rnd.uniform(-80, 80), rnd.uniform(-80, 80), c.target)
            self.assertAlmostEqual(c.right()[1], 0.0, places=9)        # no roll
            self.assertGreater(c.up()[1], 0.0)                          # never upside down
            self.assertLessEqual(abs(c.elevation()), cam.ELEVATION_LIMIT + 1e-6)

    def test_dragging_right_turns_the_model_right_and_down_shows_it_from_above(self):
        c = framed()
        b, e = c.bearing(), c.elevation()
        c.orbit(20, 0, c.target)
        self.assertAlmostEqual(c.bearing(), b + 20 * cam.DEGREES_PER_PIXEL, places=6)
        c.orbit(0, 20, c.target)
        self.assertAlmostEqual(c.elevation(), e - 20 * cam.DEGREES_PER_PIXEL, places=6)

    def test_the_point_under_the_cursor_stays_there_while_orbiting(self):
        c = framed()
        px, py = 610.0, 420.0
        pivot = c.pivot(px, py, W, H)                     # nothing hit: the ground under the cursor
        self.assertAlmostEqual(pivot[1], 0.0, places=9)
        for mode in ("turntable", "arcball"):
            c.orbit(35, -12, pivot, mode)
            x, y = c.project(pivot, W, H)
            self.assertAlmostEqual(x, px, places=6)
            self.assertAlmostEqual(y, py, places=6)

    def test_a_point_of_the_model_is_the_pivot_and_the_sky_falls_back_on_the_target(self):
        c = framed()
        self.assertEqual(list(c.pivot(400, 300, W, H, hit=(1.0, 2.0, 3.0))), [1.0, 2.0, 3.0])
        c.rotation = cam.look(0.0, 20.0)                  # looking up: the ray never meets the ground
        self.assertEqual(list(c.pivot(400, 10, W, H)), list(c.target))

    def test_the_arcball_turns_freely(self):
        c = framed()
        c.orbit(60, 60, c.target, "arcball")
        self.assertGreater(abs(c.right()[1]), 1e-3)       # it rolls: the vertical is not kept


class ZoomPanRecentre(unittest.TestCase):
    def test_the_wheel_zooms_towards_the_cursor(self):
        c = framed()
        px, py = 200.0, 450.0
        point = c.zoom_point(px, py, W, H)
        before = np.linalg.norm(c.position - point)
        c.zoom(2.0, point)
        self.assertAlmostEqual(np.linalg.norm(c.position - point), before * cam.ZOOM_STEP ** 2, places=6)
        x, y = c.project(point, W, H)
        self.assertAlmostEqual(x, px, places=6)           # the point stays under the cursor
        self.assertAlmostEqual(y, py, places=6)
        c.zoom(500.0, point)
        self.assertGreaterEqual(np.linalg.norm(c.position - point), cam.MIN_DISTANCE - 1e-9)

    def test_the_pan_follows_the_pointer(self):
        c = framed()
        x0, y0 = c.project(c.target, W, H)
        c.pan(30, -20, W, H)
        self.assertTrue(np.allclose(c.project(c.target, W, H), (x0, y0)))      # the target moved with the camera
        d = framed()
        p = d.target.copy()
        d.pan(30, -20, W, H, p)
        x, y = d.project(p, W, H)
        self.assertAlmostEqual(x, x0 + 30, places=6)
        self.assertAlmostEqual(y, y0 - 20, places=6)

    def test_a_middle_click_brings_the_point_to_the_middle(self):
        c = framed()
        point = c.ground(650, 500, W, H)
        d = np.linalg.norm(point - c.position)
        c.recentre(point)
        x, y = c.project(point, W, H)
        self.assertAlmostEqual(x, W / 2, places=6)
        self.assertAlmostEqual(y, H / 2, places=6)
        self.assertAlmostEqual(np.linalg.norm(point - c.position), d, places=6)
        self.assertTrue(np.allclose(c.target, point))

    def test_fit_shows_the_whole_sphere(self):
        c = framed()
        for v in [(25, 0, 0), (-25, 0, 0), (0, 25, 0), (0, -25, 0), (0, 0, 25), (0, 0, -25)]:
            x, y = c.project(np.array(v) + (0.0, 5.0, 0.0), W, H)
            self.assertTrue(0 <= x <= W and 0 <= y <= H, v)


def depth_of(c: cam.Camera, point) -> float:
    """How far a point lies along the sight."""
    return float(np.dot(np.asarray(point, dtype=float) - c.position, c.forward()))


class PivotInView(unittest.TestCase):
    """A pivot that left the screen (the middle of a selection scrolled away) comes back to the middle of the view
    at the same depth, so that the orbit does not swing the view like a zoom (Autodesk's Safe 3D Navigation;
    study 16, G5)."""

    def test_a_pivot_in_the_view_stays_where_it_is(self):
        c = framed()
        for px, py in ((400.0, 300.0), (30.0, 40.0), (780.0, 580.0)):
            with self.subTest(px=px, py=py):
                p = c.ground(px, py, W, H)
                self.assertTrue(np.array_equal(c.keep_in_view(p, W, H), p))

    def test_a_pivot_out_of_the_view_comes_back_to_the_middle_at_the_same_distance_along_the_sight(self):
        c = framed()
        for out in (c.target + c.right() * 400.0, c.target - c.right() * 400.0, c.target + c.up() * 300.0,
                    c.target - c.up() * 300.0 + c.right() * 500.0):
            x, y = c.project(out, W, H)
            self.assertFalse(0 <= x <= W and 0 <= y <= H)              # to begin with it is off the screen
            with self.subTest(out=tuple(out)):
                back = c.keep_in_view(out, W, H)
                self.assertTrue(np.allclose(c.project(back, W, H), (W / 2, H / 2), atol=1e-6))
                self.assertAlmostEqual(depth_of(c, back), depth_of(c, out), places=9)

    def test_a_pivot_behind_the_camera_takes_the_depth_of_the_target(self):
        c = framed()
        behind = c.position - c.forward() * 30.0 + c.right() * 5.0
        back = c.keep_in_view(behind, W, H)
        self.assertTrue(np.allclose(c.project(back, W, H), (W / 2, H / 2), atol=1e-6))
        self.assertAlmostEqual(depth_of(c, back), depth_of(c, c.target), places=9)

    def test_in_the_parallel_view_too(self):
        c = framed()
        c.ortho = True
        out = c.target + c.right() * 400.0 + c.forward() * 12.0
        self.assertFalse(0 <= c.project(out, W, H)[0] <= W)
        back = c.keep_in_view(out, W, H)
        self.assertTrue(np.allclose(c.project(back, W, H), (W / 2, H / 2), atol=1e-6))
        self.assertAlmostEqual(depth_of(c, back), depth_of(c, out), places=9)
        inside = c.target + c.up() * 2.0
        self.assertTrue(np.array_equal(c.keep_in_view(inside, W, H), inside))

    def test_a_mark_of_so_many_pixels_is_as_wide_wherever_it_stands(self):
        c = framed()
        for ground in ((400.0, 300.0), (80.0, 560.0), (700.0, 120.0)):
            p = c.ground(*ground, W, H)
            for ortho in (False, True):
                c.ortho = ortho
                with self.subTest(ground=ground, ortho=ortho):
                    x0, y0 = c.project(p, W, H)
                    x1, y1 = c.project(p + c.right() * (8 * c.pixel_size(p, H)), W, H)
                    self.assertAlmostEqual(x1 - x0, 8.0, places=6)
                    self.assertAlmostEqual(y1, y0, places=6)


def parallel() -> cam.Camera:
    c = framed()
    c.ortho = True
    return c


def drawn(c: cam.Camera, point) -> tuple[float, float]:
    """Where the parallel camera of Scene.qml draws a point: its offset from the camera's axis times the
    magnification the view gives it, H / (2 * half_height)."""
    v = np.asarray(point, dtype=float) - c.position
    m = H / (2 * c.half_height())
    return W / 2 + float(np.dot(v, c.right())) * m, H / 2 - float(np.dot(v, c.up())) * m


class Parallel(unittest.TestCase):
    """The parallel view of the cube's menu: rays parallel to the camera's direction, one scale at every depth."""

    def test_a_point_is_projected_where_the_parallel_camera_draws_it(self):
        c = parallel()
        for point in ((20.0, 0.0, 0.0), (0.0, 0.0, -20.0), (-15.0, 12.0, 8.0), (3.0, 0.0, 30.0)):
            with self.subTest(point=point):
                self.assertTrue(np.allclose(c.project(point, W, H), drawn(c, point), atol=1e-6))
        above = c.position + c.up() * 2.0 - c.forward() * 10.0                   # behind the camera's plane
        self.assertIsNotNone(c.project(above, W, H))       # drawn all the same: the camera clips at -20 km

    def test_the_ray_of_a_pixel_is_parallel_to_the_view_and_goes_through_what_is_drawn_there(self):
        c = parallel()
        point = np.array([20.0, 0.0, 0.0])
        px, py = drawn(c, point)
        origin, direction = c.ray(px, py, W, H)
        self.assertTrue(np.allclose(direction, c.forward()))
        off = (point - origin) - np.dot(point - origin, direction) * direction
        self.assertLess(np.linalg.norm(off), 1e-6)          # the point lies on the ray

    def test_the_ground_under_a_pixel_is_drawn_at_that_pixel(self):
        c = parallel()
        for px, py in ((400.0, 300.0), (60.0, 520.0), (700.0, 90.0)):
            with self.subTest(px=px, py=py):
                g = c.ground(px, py, W, H)
                self.assertAlmostEqual(g[1], 0.0)
                self.assertTrue(np.allclose(drawn(c, g), (px, py), atol=1e-6))

    def test_the_pan_moves_everything_by_the_pixels_of_the_pointer(self):
        c = parallel()
        near, far = np.array([0.0, 5.0, 0.0]), np.array([0.0, 0.0, -60.0])
        before = [drawn(c, q) for q in (near, far)]
        c.pan(30, -20, W, H, far)                           # the depth of a point farther than the target
        for (x0, y0), q in zip(before, (near, far), strict=True):
            x, y = drawn(c, q)
            self.assertAlmostEqual(x, x0 + 30, places=6)    # at every depth: a parallel view has one scale
            self.assertAlmostEqual(y, y0 - 20, places=6)

    def test_the_wheel_zooms_towards_the_point_under_the_cursor(self):
        c = parallel()
        c.rotation = cam.look(30.0, 10.0)                   # looking a little up: the sky under the cursor
        c.position = c.target - c.forward() * 60.0
        px, py = 200.0, 100.0
        point = c.zoom_point(px, py, W, H)
        self.assertTrue(np.allclose(drawn(c, point), (px, py), atol=1e-6))
        self.assertAlmostEqual(float(np.dot(point - c.position, c.forward())), 60.0, places=6)    # the target's depth
        before = c.half_height()
        c.zoom(2.0, point)
        self.assertAlmostEqual(c.half_height(), before * cam.ZOOM_STEP ** 2, places=6)
        self.assertTrue(np.allclose(drawn(c, point), (px, py), atol=1e-6))      # still under the cursor


class Views(unittest.TestCase):
    def test_the_standard_views_look_where_they_say(self):
        c = framed()
        for name, bearing, elevation in (("south", 0, 0), ("east", 270, 0), ("north", 180, 0), ("west", 90, 0)):
            c.view(name, (0, 0, 0), 10, 1.0)
            self.assertAlmostEqual(c.bearing(), bearing, places=6)
            self.assertAlmostEqual(c.elevation(), elevation, places=6)
        c.view("south", (0, 0, 0), 10, 1.0)
        self.assertGreater(c.position[2], 0.0)            # from the south: z points South in Qt's axes
        c.view("top", (0, 0, 0), 10, 1.0)
        self.assertAlmostEqual(c.elevation(), -90.0, places=6)
        self.assertAlmostEqual(c.up()[2], -1.0, places=6)  # North up on the screen

    def test_straight_down_or_up_the_bearing_is_where_the_top_of_the_view_points(self):
        c = cam.Camera()
        for bearing in (0.0, 37.0, 90.0, 180.0, 250.0):
            for elevation in (-90.0, 90.0, -89.9999):
                with self.subTest(bearing=bearing, elevation=elevation):
                    c.rotation = cam.look(bearing, elevation)
                    self.assertAlmostEqual((c.bearing() - bearing + 180) % 360 - 180, 0.0, places=6)

    def test_the_animation_eases_out_and_ends_on_the_new_camera(self):
        a, b = framed(), framed()
        b.view("east", (0, 0, 0), 10, 1.0)
        self.assertTrue(np.allclose(cam.between(a, b, 0.0).position, a.position))
        end = cam.between(a, b, 1.0)
        self.assertTrue(np.allclose(end.position, b.position))
        self.assertTrue(np.allclose(np.abs(end.rotation), np.abs(b.rotation)))
        self.assertAlmostEqual(cam.ease(0.5), 0.875)
        mid = cam.between(a, b, 0.5)
        self.assertAlmostEqual(np.linalg.norm(mid.rotation), 1.0)
        # (the quarter of a second is the view's: test_views_navigation, the camera's way at 125, 200 and 250 ms)

    def test_quaternions(self):
        q = cam.axis_angle((0, 1, 0), 90)
        self.assertTrue(np.allclose(cam.rotate(q, (0, 0, -1)), (-1, 0, 0)))    # North turned to the West
        self.assertTrue(np.allclose(cam.slerp(q, q, 0.3), q))
        self.assertAlmostEqual(math.degrees(2 * math.acos(cam.slerp((1, 0, 0, 0), q, 0.5)[0])), 45.0)


class Axonometric(unittest.TestCase):
    """The parallel camera of the report's 3D pictures (ui/report_3d.py): it looks where it is told and holds the
    whole scene with its margin."""

    def test_the_axonometric_camera_looks_from_its_corner_and_holds_every_point_within_its_margin(self):
        rnd = random.Random(3)
        points = np.array([(rnd.uniform(0, 40), rnd.uniform(0, 12), rnd.uniform(-20, 0)) for _ in range(300)])
        for bearing in (315.0, 45.0):
            c = cam.axonometric(points, bearing, -30.0, 1100 / 720, margin=0.05)
            self.assertTrue(c.ortho)
            self.assertAlmostEqual(c.bearing(), bearing, places=6)
            self.assertAlmostEqual(c.elevation(), -30.0, places=6)
            seen = np.array([c.project(q, 1100, 720) for q in points])
            self.assertGreaterEqual(seen[:, 0].min(), 0.05 * 1100 - 1e-6)
            self.assertLessEqual(seen[:, 0].max(), 0.95 * 1100 + 1e-6)
            self.assertGreaterEqual(seen[:, 1].min(), 0.05 * 720 - 1e-6)
            self.assertLessEqual(seen[:, 1].max(), 0.95 * 720 + 1e-6)
            # tight on one side at least: the scene as large as the picture allows
            self.assertTrue(math.isclose(seen[:, 0].max() - seen[:, 0].min(), 0.9 * 1100, rel_tol=1e-6) or
                            math.isclose(seen[:, 1].max() - seen[:, 1].min(), 0.9 * 720, rel_tol=1e-6))
        # looking towards the north-west the camera stands to the south-east of what it looks at
        c = cam.axonometric(points, 315.0, -30.0, 1.5)
        self.assertGreater(c.position[0], c.target[0])              # east
        self.assertGreater(c.position[2], c.target[2])              # south (Qt's +z)


if __name__ == "__main__":
    unittest.main()
