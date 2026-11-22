"""R619: Meridio's figure (app/assistant/figure.py), the geometry the window draws: the order of drawing (every side
before every face, the faces red, yellow, blue), the slabs on one plane, the rounds of the points, the eyes that stay
in the yellow and change shape with a cut, the matrices the QML repeats. The ideas of the prototype's checks
(meridiana-prove/r35-meridio-volto/kimi-4/test_meridio_kimi4.py and verifica_consegna.py)."""
import itertools
import math
import unittest

import _setup  # noqa: F401
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from meridiana.app.assistant import figure as f
from meridiana.app.platform import config

GAZES = [(gx * (0.82 if gx and gy else 1), gy * (0.82 if gx and gy else 1))
         for gx, gy in itertools.product((-1, 0, 1), repeat=2)]


def with_gaze(name: str, gaze=(0.0, 0.0)) -> dict:
    p = dict(f.POSES[name])
    if name in ("rest", "speak"):            # the expressions whose eyes follow the pointer (Character.qml, target)
        p["gx"] = max(-1.0, min(1.0, p["gx"] + gaze[0]))
        p["gy"] = max(-1.0, min(1.0, p["gy"] + gaze[1]))
    return p


class Shape(unittest.TestCase):
    def test_the_hair_and_proportions_are_the_tenth_sketchs(self):
        expected = [(-37.72, -6.92), (-23.0, -17.96), (-32.2, -38.2), (-10.12, -29.92), (0.92, -51.08),
                    (8.28, -31.76), (26.68, -42.8), (21.16, -17.96), (37.72, -6.92)]
        for actual, wanted in zip(f.HAIR, expected, strict=True):
            self.assertAlmostEqual(actual[0], wanted[0])
            self.assertAlmostEqual(actual[1], wanted[1])
        self.assertEqual((f.RADIUS, f.TOP, f.FILLET, f.PLATE), (22.0, -6.0, 1.8, 7.0))
        self.assertEqual(f.FLAPS[1][1][2], (1.0, 49.0))     # the middle flap, the longest

    def test_every_point_is_rounded_with_the_same_radius(self):
        for key, corners in (("hat", f.HAIR), ("flap0", f.FLAPS[0][1]), ("flap1", f.FLAPS[1][1]),
                             ("flap2", f.FLAPS[2][1])):
            outline = Polygon(f.outline(key))
            self.assertTrue(outline.is_valid, key)
            for i, corner in enumerate(corners):
                prev, nxt = corners[i - 1], corners[(i + 1) % len(corners)]
                u = (prev[0] - corner[0], prev[1] - corner[1])
                v = (nxt[0] - corner[0], nxt[1] - corner[1])
                theta = math.acos((u[0] * v[0] + u[1] * v[1]) / (math.hypot(*u) * math.hypot(*v)))
                inside = Polygon(corners).contains(Point(corner[0] + (u[0] / math.hypot(*u) + v[0] / math.hypot(*v)) * 0.01,
                                                         corner[1] + (u[1] / math.hypot(*u) + v[1] / math.hypot(*v)) * 0.01))
                distance = outline.exterior.distance(Point(corner))
                if inside:          # a point: the rounded arc stands r (1 / sin(θ/2) - 1) inside the sharp corner
                    want = f.FILLET * (1 / math.sin(theta / 2) - 1)
                    self.assertAlmostEqual(distance, want, delta=0.02, msg=(key, i))
                else:               # a valley: rounded too, the outline passes off the sharp corner
                    self.assertGreater(distance, 0.01, (key, i))

    def test_the_sticker_grows_every_part_by_its_border(self):
        for key in f.ORDER:
            for small, width in ((True, f.STICKER), (False, f.STICKER / 2)):
                grown = Polygon(f.sticker_outline(key, small))
                part = Polygon(f.outline(key))
                self.assertTrue(grown.contains(part.buffer(width - 0.1)), key)      # round, by chords
                self.assertFalse(grown.contains(part.buffer(width + 0.1)), key)


class Order(unittest.TestCase):
    def test_every_side_is_drawn_before_every_face_and_the_faces_go_red_yellow_blue(self):
        plan = f.draw_plan()
        layers = [layer for layer, _key, _t in plan]
        first_side = layers.index("side")
        self.assertEqual(set(layers[:first_side]), {"sticker"})
        sides = [i for i, layer in enumerate(layers) if layer == "side"]
        faces = [i for i, layer in enumerate(layers) if layer == "face"]
        self.assertLess(max(sides), min(faces))
        self.assertEqual([key for layer, key, _t in plan if layer == "face"],
                         ["flap0", "flap2", "flap1", "face", "hat"])
        self.assertEqual({key for layer, key, _t in plan if layer == "side"}, set(f.ORDER))

    def test_the_slabs_are_on_one_plane_with_one_thickness(self):
        # the same depths for every part's side, the back plane included; a face never shifted in depth
        plan = f.draw_plan()
        depths = {key: sorted(t for layer, k, t in plan if layer == "side" and k == key) for key in f.ORDER}
        self.assertEqual(len({tuple(d) for d in depths.values()}), 1)
        self.assertEqual(max(depths["face"]), 1.0)
        self.assertEqual({t for layer, _k, t in plan if layer == "face"}, {0.0})
        # turned, every part's face moves to its back by the same shift on the screen: one plane, one thickness
        for name in f.POSES:
            p = dict(f.POSES[name], yaw=27.0, pitch=-14.0)
            shifts = set()
            for key in f.ORDER:
                front = f.part_matrix(key, p, 0.3, 23, 23, front=True)
                back = f.part_matrix(key, p, 0.3, 23, 23, front=False)
                self.assertEqual([round(v, 9) for v in front[:2] + front[3:5]],
                                 [round(v, 9) for v in back[:2] + back[3:5]])
                shifts.add((round(back[2] - front[2], 9), round(back[5] - front[5], 9)))
            self.assertEqual(len(shifts), 1, name)
            dx, dy = f.depth_shift(p["yaw"], p["pitch"], 0.3, -f.PLATE)
            self.assertEqual(shifts, {(round(dx, 9), round(dy, 9))})

    def test_the_stickers_white_is_under_the_whole_figure_as_it_turns(self):
        # the border drawn on the front and the back plane only: what lies between is covered while he turns
        for yaw, pitch in itertools.product((-40, -20, 0, 20, 40), (-25, 0, 25)):
            p = dict(f.POSES["rest"], yaw=yaw, pitch=pitch)
            layers = f.projected(p, 46)
            white = unary_union([Polygon(q).buffer(0) for layer, _k, q in layers if layer == "sticker"])
            colour = unary_union([Polygon(q).buffer(0) for layer, _k, q in layers if layer != "sticker"])
            self.assertTrue(white.contains(colour), (yaw, pitch))
            # a border all round: at least half the border's width beyond the colours, everywhere
            self.assertTrue(white.contains(colour.buffer(f.STICKER * 46 / f.UNITS * 0.5)), (yaw, pitch))

    def test_the_matrices_are_the_prototypes_projection(self):
        # the prototype (kimi-4): swing about the pivot, shift, then the view of a point at depth z
        def view(x, y, z, yaw, pitch, scale, ox, oy):
            cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
            cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
            x1, z1 = x * cy + z * sy, -x * sy + z * cy
            return ox + x1 * scale, oy + (y * cp - z1 * sp) * scale
        p = dict(f.POSES["wave"], yaw=19.0, pitch=8.0, flap1X=1.5, faceY=-2.0)
        for key in f.ORDER:
            angle, shift = f.turn_and_shift(key, p)
            px, py = f.pivot(key)
            co, si = math.cos(math.radians(angle)), math.sin(math.radians(angle))
            for x, y in f.outline(key)[::7]:
                sx = px + (x - px) * co - (y - py) * si + shift[0]
                sy = py + (x - px) * si + (y - py) * co + shift[1]
                for front in (True, False):
                    z = f.PLATE / 2 if front else -f.PLATE / 2
                    want = view(sx, sy, z, p["yaw"], p["pitch"], 0.5, 40, 41)
                    got = f.apply(f.part_matrix(key, p, 0.5, 40, 41, front), [(x, y)])[0]
                    self.assertAlmostEqual(got[0], want[0], places=9)
                    self.assertAlmostEqual(got[1], want[1], places=9)


class Eyes(unittest.TestCase):
    def area(self, points):
        return Polygon(points).area if len(points) >= 3 else 0.0

    def test_at_rest_and_looking_the_eyes_are_full_circles(self):
        for gaze in GAZES:
            p = with_gaze("rest", gaze)
            for index, eye in enumerate(f.eyes(p)):
                cut = f.eye_cuts(p, index)
                self.assertAlmostEqual(self.area(eye["outline"]) / (math.pi * cut["radius"] ** 2), 1.0, delta=0.01)
                self.assertEqual(eye["arch"], [])

    def test_the_cuts_of_the_expressions(self):
        full = math.pi * f.EYE_RADIUS ** 2
        worried = f.eyes(f.POSES["worried"])
        for index, eye in enumerate(worried):
            self.assertLess(self.area(eye["outline"]), full * 0.8)
            top = min(eye["outline"], key=lambda q: q[1])
            # worried: the lid rises towards the middle (the left eye's highest point on its right)
            self.assertGreater(top[0], 0) if index == 0 else self.assertLess(top[0], 0)
        for index, eye in enumerate(f.eyes(f.POSES["think"])):
            top = min(eye["outline"], key=lambda q: q[1])
            self.assertLess(top[0], 0) if index == 0 else self.assertGreater(top[0], 0)
        for eye in f.eyes(f.POSES["happy"]):             # a crescent from below: what is left is above the centre
            self.assertLess(self.area(eye["outline"]), full * 0.65)
            self.assertLess(max(y for _x, y in eye["outline"]), 0.0)
        left, right = f.eyes(f.POSES["puzzled"])       # one eye cut, the other round
        self.assertGreater(self.area(right["outline"]) / self.area(left["outline"]), 1.25)
        for name in ("drowsy", "asleep"):
            for eye in f.eyes(f.POSES[name]):
                self.assertLess(self.area(eye["outline"]), full * 0.6, name)
        for eye in f.eyes(f.pose(blink=1)):          # closed: a line is left, not nothing
            self.assertGreater(self.area(eye["outline"]), 0.0)
            self.assertLess(self.area(eye["outline"]), full * 0.25)
        rest = f.eye_cuts(f.POSES["rest"], 0)
        for index, eye in enumerate(f.eyes(f.POSES["surprised"])):     # larger, round, a thin arch apart
            cut = f.eye_cuts(f.POSES["surprised"], index)
            self.assertGreater(cut["radius"], rest["radius"])
            self.assertAlmostEqual(self.area(eye["outline"]) / (math.pi * cut["radius"] ** 2), 1.0, delta=0.01)
            self.assertEqual(len(eye["arch"]), 33)
            self.assertLess(eye["arch_line"], cut["line"])
        for listening, talking in zip(f.eyes(f.POSES["listen"]), f.eyes(f.POSES["speak"]), strict=True):
            self.assertGreater(self.area(listening["outline"]) / self.area(talking["outline"]), 1.08)

    def test_the_small_figure_cuts_deeper_and_the_cut_comes_in_without_a_jump(self):
        for name in ("worried", "happy", "drowsy"):
            for big, small in zip(f.eyes(f.POSES[name], small=False), f.eyes(f.POSES[name], small=True), strict=True):
                self.assertLess(self.area(small["outline"]), self.area(big["outline"]))
        areas = [self.area(f.eyes(f.pose(blink=b / 100))[0]["outline"]) for b in range(0, 101)]
        jumps = [a - b for a, b in zip(areas, areas[1:], strict=False)]
        self.assertLess(max(jumps), 0.06 * math.pi * f.EYE_RADIUS ** 2)    # no step of more than 6 % of the eye

    def test_the_eyes_stay_in_the_yellow_in_every_expression_and_gaze(self):
        face = Polygon(f.face_outline(128)).buffer(0.06)
        for name in f.POSES:
            for gaze in GAZES:
                p = with_gaze(name, gaze)
                face_here = Polygon([(x + p["faceX"], y + p["faceY"]) for x, y in face.exterior.coords])
                for index, eye in enumerate(f.eyes(p)):
                    cx, cy = f.eye_centre(p, index)
                    for x, y in eye["outline"] + eye["arch"]:
                        self.assertTrue(face_here.contains(Point(cx + x, cy + y)), (name, gaze, index, x, y))

    def test_the_outline_is_asked_again_only_for_a_new_cut(self):
        a = f.eyes(f.pose(blink=0.301))
        self.assertIs(a, f.eyes(f.pose(blink=0.299, gx=1.0, faceY=2.0)))
        self.assertIsNot(a, f.eyes(f.pose(blink=0.4)))


class Settings(unittest.TestCase):
    def test_the_looks_and_the_default(self):
        self.assertEqual(config.Config().assistant_style, "sticker")
        for old, new in (("smooth", "sticker"), ("pixel", "sticker"), ("solid", "sticker"), ("sticker", "sticker")):
            self.assertEqual(config.migrate({"version": 34, "assistant_style": old})["assistant_style"], new)

    def test_the_window_gets_what_it_draws(self):
        data = f.window_data()
        self.assertEqual([part["key"] for part in data["parts"]], list(f.ORDER))
        self.assertEqual(set(data["poses"]), set(f.EXPRESSIONS))
        self.assertTrue(set(data["reactions"]) <= set(f.EXPRESSIONS))
        self.assertEqual(data["poseKeys"], list(f.POSE_KEYS))


if __name__ == "__main__":
    unittest.main()
