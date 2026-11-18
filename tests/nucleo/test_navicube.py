"""The view cube in numbers (study 15, 2.5): 26 parts, the face clicked looks from its side, Top keeps the nearest
quarter of the bearing, the arrows turn by 45 degrees, the compass ring looks from its letters, what is under the
pointer is the part nearest to the camera."""

import unittest


import _setup  # noqa: F401

from meridiana import camera as cam
from meridiana import navicube as nc


def looking(bearing, elevation) -> cam.Camera:
    c = cam.Camera()
    c.rotation = cam.look(bearing, elevation)
    return c


class Parts(unittest.TestCase):
    def test_twenty_six_parts_six_faces_twelve_edges_eight_corners(self):
        kinds = [nc.kind(p) for p in nc.parts()]
        self.assertEqual((len(kinds), kinds.count("face"), kinds.count("edge"), kinds.count("corner")), (26, 6, 12, 8))
        self.assertEqual(set(nc.FACES.values()), {"top", "bottom", "north", "south", "east", "west"})
        self.assertEqual(set(nc.face_names()), set(nc.FACES.values()))

    def test_a_face_looks_from_its_side(self):
        for part, bearing, elevation in (((0, 0, 1), 0, 0), ((0, 0, -1), 180, 0), ((1, 0, 0), 270, 0),
                                         ((-1, 0, 0), 90, 0)):
            b, e = nc.looking_from(part)
            self.assertAlmostEqual(b, bearing)
            self.assertAlmostEqual(e, elevation)
        b, e = nc.looking_from((1, 1, 1))                   # the corner of top, East and South
        self.assertAlmostEqual(b, 315.0)
        self.assertAlmostEqual(e, -35.26439, places=4)
        self.assertAlmostEqual(nc.looking_from((0, 1, 1))[1], -45.0)

    def test_top_keeps_the_nearest_quarter_of_the_bearing(self):
        self.assertEqual(nc.looking_from((0, 1, 0), looking(100.0, -30.0)), (90.0, -90.0))
        self.assertEqual(nc.looking_from((0, 1, 0), looking(-10.0, -30.0)), (0.0, -90.0))
        self.assertEqual(nc.looking_from((0, -1, 0), looking(200.0, 10.0)), (180.0, 90.0))

    def test_the_arrows_turn_by_45_degrees_and_never_over_the_top(self):
        c = looking(30.0, -35.0)
        self.assertAlmostEqual(nc.turned(c, "right")[0], 75.0)
        self.assertAlmostEqual(nc.turned(c, "left")[0], 345.0)
        self.assertAlmostEqual(nc.turned(c, "up")[1], -80.0)
        self.assertEqual(nc.turned(looking(0, -80.0), "up")[1], -90.0)
        with self.assertRaises(ValueError):
            nc.turned(c, "sideways")

    def test_from_the_top_the_cube_keeps_the_orientation_in_hand(self):
        top = looking(90.0, -90.0)                          # East at the top of the view
        self.assertEqual(nc.looking_from((0, 1, 0), top), (90.0, -90.0))     # Top again: the plan does not turn
        self.assertAlmostEqual(nc.turned(top, "right")[0], 135.0)
        self.assertAlmostEqual(nc.turned(top, "left")[0], 45.0)
        bearing, elevation = nc.turned(top, "down")         # tilted from the side at the bottom of the view
        self.assertAlmostEqual(bearing, 90.0)
        self.assertAlmostEqual(elevation, -45.0)

    def test_the_compass_ring_looks_from_its_letter(self):
        c = looking(30.0, -35.0)
        self.assertEqual(nc.compass_view("S", c)[0], 0.0)
        self.assertEqual(nc.compass_view("N", c)[0], 180.0)
        self.assertAlmostEqual(nc.compass_view("E", c)[1], -35.0)


class Drawing(unittest.TestCase):
    def test_from_the_south_only_the_south_face_shows(self):
        c = looking(0.0, 0.0)
        shown = {part for part, _poly, _d in nc.faces(c, 100)}
        self.assertTrue(all(part[2] == 1 for part in shown))     # only cells of the South face
        self.assertEqual(nc.pick(c, 100, 0, 0), (0, 0, 1))
        self.assertEqual(nc.pick(c, 100, -27, 0), (-1, 0, 1))  # its west edge, on the left
        self.assertEqual(nc.pick(c, 100, 27, -27), (1, 1, 1))  # the top east corner
        self.assertIsNone(nc.pick(c, 100, 80, 80))

    def test_from_a_corner_three_faces_show_and_the_nearest_wins(self):
        c = looking(*nc.looking_from((1, 1, 1)))
        self.assertEqual(len(nc.faces(c, 120)), 27)           # three faces of nine cells
        self.assertEqual(nc.pick(c, 120, 0, 0), (1, 1, 1))     # the corner faces the camera
        faces = nc.faces(c, 120)
        self.assertTrue(all(a[2] >= b[2] for a, b in zip(faces, faces[1:], strict=False)))     # farthest first

    def test_every_part_can_be_clicked_from_its_own_view(self):
        for part in nc.parts():
            c = looking(*nc.looking_from(part, looking(0.0, -30.0)))
            self.assertEqual(nc.pick(c, 120, 0, 0), part, part)


if __name__ == "__main__":
    unittest.main()
