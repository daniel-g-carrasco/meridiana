"""The gizmo of Move and Rotate in the core (gizmo.py; study 16, B2 and B4; task 16b, steps 5-7): its size on the
screen, which handle is under the pointer, the drag along an arrow, across the plane and round the ring, the steps.
The camera of the study's proof (16-prove/gizmo.py): errors of 6e-6 m and 1e-4 degrees there."""

import math
import unittest

import numpy as np

import _setup  # noqa: F401

from meridiana import camera, gizmo, mesh

W, H = 800.0, 600.0


def cam() -> camera.Camera:
    c = camera.Camera()
    c.position = np.array([12.0, 9.0, 16.0])
    c.rotation = camera.look(math.degrees(math.atan2(-12.0, 16.0)) % 360.0,
                             -math.degrees(math.atan2(9.0, math.hypot(12.0, 16.0))))
    c.target = np.zeros(3)
    return c


def pixel(c, point):
    return c.project(np.asarray(point, dtype=float), W, H)


class Handles(unittest.TestCase):
    def test_an_arrow_is_as_long_on_the_screen_wherever_the_gizmo_stands(self):
        c = cam()
        for where in ((0.0, 0.0, 0.0), (-6.0, 3.0, -9.0)):
            size = gizmo.length(c, where, H)
            a, b = pixel(c, where), pixel(c, np.asarray(where) + c.right() * size)
            with self.subTest(where=where):
                self.assertAlmostEqual(math.hypot(b[0] - a[0], b[1] - a[1]), gizmo.PIXELS, delta=1e-6)

    def test_each_handle_is_taken_a_few_pixels_off_it_and_nothing_in_a_corner(self):
        c = cam()
        size = gizmo.length(c, (0, 0, 0), H)
        for name, point in (("x", gizmo.EAST * 0.5 * size), ("y", gizmo.NORTH * 0.5 * size)):
            px, py = pixel(c, point)
            with self.subTest(name=name):
                self.assertEqual(gizmo.pick(c, px + 4, py - 3, W, H, (0, 0, 0), size), name)
        r = math.radians(225.0)                              # the ring, away from the arrows
        px, py = pixel(c, (gizmo.EAST * math.cos(r) + gizmo.NORTH * math.sin(r)) * mesh.GIZMO_RING[0] * size)
        self.assertEqual(gizmo.pick(c, px + 3, py, W, H, (0, 0, 0), size), "rz")
        middle = sum(mesh.GIZMO_PLANE) / 2
        px, py = pixel(c, (gizmo.EAST + gizmo.NORTH) * middle * size)
        self.assertEqual(gizmo.pick(c, px, py, W, H, (0, 0, 0), size), "xy")
        self.assertEqual(gizmo.pick(c, 5.0, 5.0, W, H, (0, 0, 0), size), "")

    def test_the_arrow_up_is_drawn_but_nothing_takes_it(self):
        c = cam()
        size = gizmo.length(c, (0, 0, 0), H)
        px, py = pixel(c, gizmo.UP * 0.6 * size)
        self.assertEqual(gizmo.pick(c, px, py, W, H, (0, 0, 0), size), "")
        self.assertNotIn("z", gizmo.ACTIVE)
        self.assertIsNone(gizmo.Drag.begin("z", c, px, py, W, H, (0, 0, 0)))


class Drags(unittest.TestCase):
    def test_along_an_arrow_the_object_moves_along_that_direction_only(self):
        c = cam()
        centre = np.array([2.0, 1.0, -3.0])
        for name, axis in (("x", gizmo.EAST), ("y", gizmo.NORTH)):
            start = pixel(c, centre + axis * 0.5)
            drag = gizmo.Drag.begin(name, c, *start, W, H, centre)
            for want in (2.5, -3.0, 0.7):
                end = pixel(c, centre + axis * (0.5 + want) + gizmo.UP * 0.0)
                east, north, degrees = drag.update(c, *end, W, H, snaps=False)
                with self.subTest(name=name, want=want):
                    self.assertAlmostEqual(east if name == "x" else north, want, delta=0.001)
                    self.assertEqual(north if name == "x" else east, 0.0)
                    self.assertEqual(degrees, 0.0)

    def test_the_steps_are_ten_centimetres_or_one_with_shift_and_a_millimetre_without_snaps(self):
        c = cam()
        drag = gizmo.Drag.begin("x", c, *pixel(c, gizmo.EAST * 0.5), W, H, (0, 0, 0))
        end = pixel(c, gizmo.EAST * (0.5 + 1.234))
        self.assertAlmostEqual(drag.update(c, *end, W, H)[0], 1.2, places=9)
        self.assertAlmostEqual(drag.update(c, *end, W, H, {"shift"})[0], 1.23, places=9)
        self.assertAlmostEqual(drag.update(c, *end, W, H, snaps=False)[0], 1.234, places=9)

    def test_across_the_square_east_and_north_together(self):
        c = cam()
        start = pixel(c, (gizmo.EAST + gizmo.NORTH) * 0.3)
        drag = gizmo.Drag.begin("xy", c, *start, W, H, (0, 0, 0))
        end = pixel(c, (gizmo.EAST + gizmo.NORTH) * 0.3 + gizmo.EAST * 3.0 - gizmo.NORTH * 1.2)
        east, north, _deg = drag.update(c, *end, W, H)
        self.assertAlmostEqual(east, 3.0, places=9)
        self.assertAlmostEqual(north, -1.2, places=9)
        self.assertTrue(np.allclose(drag.offset(), (3.0, 0.0, 1.2)))           # Qt axes: z is South

    def test_round_the_ring_the_angle_from_the_press_anticlockwise(self):
        c = cam()

        def ring_point(degrees):
            r = math.radians(degrees)
            return (gizmo.EAST * math.cos(r) + gizmo.NORTH * math.sin(r)) * 3.0
        drag = gizmo.Drag.begin("rz", c, *pixel(c, ring_point(45.0)), W, H, (0, 0, 0))
        self.assertAlmostEqual(drag.update(c, *pixel(c, ring_point(75.0)), W, H, snaps=False)[2], 30.0, delta=1e-4)
        self.assertEqual(drag.update(c, *pixel(c, ring_point(80.0)), W, H)[2], 30.0)          # 15° steps
        self.assertEqual(drag.update(c, *pixel(c, ring_point(80.0)), W, H, {"shift"})[2], 35.0)
        self.assertAlmostEqual(drag.update(c, *pixel(c, ring_point(10.0)), W, H, snaps=False)[2], -35.0, delta=1e-4)

    def test_an_arrow_seen_end_on_keeps_the_last_value(self):
        c = camera.Camera()
        c.position = np.array([40.0, 0.0, 0.0])
        c.rotation = camera.look(270.0, 0.0)                 # looking West along the East arrow: it is a point
        drag = gizmo.Drag(handle="x", centre=np.zeros(3), start=0.0, value=(1.0, 0.0, 0.0))
        self.assertIsNone(gizmo.along(c, 400.0, 300.0, W, H, (0, 0, 0), gizmo.EAST))
        self.assertEqual(drag.update(c, 400.0, 300.0, W, H), (1.0, 0.0, 0.0))

    def test_the_turn_of_the_preview_is_anticlockwise_seen_from_above(self):
        q = gizmo.rotation(90.0)
        self.assertTrue(np.allclose(camera.rotate(q, gizmo.EAST), gizmo.NORTH))


if __name__ == "__main__":
    unittest.main()
