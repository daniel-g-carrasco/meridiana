"""The straight skeleton: the faces of a roof of equal slopes on any footprint, checked against CGAL (study 16,
A.5: the 306 footprints of docs/studio/16-prove/scheletro-riferimento.json) and against the proof's gables."""

import json
import math
import time
import unittest

import _setup
from shapely.geometry import Polygon
from shapely.ops import unary_union

from meridiana import skeleton

REFERENCE = _setup.ROOT / "docs" / "studio" / "16-prove" / "scheletro-riferimento.json"
MM = 1e-3

# the six footprints of the proof (scheletro.py) and their gable ends for the roof with two pitches
PLANS = {
    "rettangolo": [(0, 0), (20, 0), (20, 10), (0, 10)],
    "L": [(0, 0), (20, 0), (20, 8), (8, 8), (8, 18), (0, 18)],
    "T": [(0, 0), (24, 0), (24, 8), (16, 8), (16, 20), (8, 20), (8, 8), (0, 8)],
    "U": [(0, 0), (24, 0), (24, 16), (16, 16), (16, 7), (8, 7), (8, 16), (0, 16)],
    "trapezio": [(0, 0), (22, 0), (18, 10), (3, 10)],
    "lato storto": [(0, 0), (20, 0), (21.5, 10), (0, 10)],
}
GABLE_ENDS = {"rettangolo": [1, 3], "L": [1, 4], "T": [1, 4, 7], "U": [2, 6], "trapezio": [1, 3],
              "lato storto": [1, 3]}


def simplified(face):
    """A face without the points within a millimetre of the one before and without the points in line with
    their neighbours: CGAL keeps a node where an arc of another face ends, the skeleton may not."""
    pts = []
    for p in face:
        if not pts or math.dist(pts[-1][:2], p[:2]) >= MM:
            pts.append(tuple(p))
    if len(pts) > 1 and math.dist(pts[0][:2], pts[-1][:2]) < MM:
        pts.pop()
    changed = True
    while changed and len(pts) > 3:
        changed = False
        for k in range(len(pts)):
            a, b, c = pts[k - 1], pts[k], pts[(k + 1) % len(pts)]
            cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            if abs(cross) < MM * max(math.dist(a[:2], c[:2]), 1e-9):
                del pts[k]
                changed = True
                break
    return pts


def same_ring(f, g) -> bool:
    """The same ring within a millimetre (heights too), whatever point it starts from."""
    if len(f) != len(g):
        return False
    return any(all(math.dist(f[i], g[(i + shift) % len(g)]) < MM for i in range(len(f))) for shift in range(len(g)))


def side_of(face, ring):
    """The side of `ring` a CGAL face stands on (CGAL turns the ring counter-clockwise first)."""
    n = len(ring)
    ccw = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1], strict=True)) > 0
    for i in range(n):
        a, b = (ring[i], ring[(i + 1) % n]) if ccw else (ring[(i + 1) % n], ring[i])
        for k in range(len(face)):
            if math.dist(face[k][:2], a) < MM and math.dist(face[(k + 1) % len(face)][:2], b) < MM:
                return i
    return None


def extended_for_gables(ring, ends, far=1000.0):
    """The proof's way to a gable end (scheletro.py): the gable side pushed far along the eaves beside it."""
    pts = list(ring)
    n = len(pts)
    out = list(pts)
    for i in ends:
        a, b = pts[i], pts[(i + 1) % n]
        prev_a, next_b = pts[(i - 1) % n], pts[(i + 2) % n]
        da, db = (a[0] - prev_a[0], a[1] - prev_a[1]), (b[0] - next_b[0], b[1] - next_b[1])
        la, lb = math.hypot(*da), math.hypot(*db)
        out[i] = (out[i][0] + da[0] / la * far, out[i][1] + da[1] / la * far)
        out[(i + 1) % n] = (out[(i + 1) % n][0] + db[0] / lb * far, out[(i + 1) % n][1] + db[1] / lb * far)
    return out


def roof_checks(test, ring, faces, gables=()):
    """What the proof checked: one face per eave and none for a gable, standing on its side, the footprint
    covered once, each point at the height of its distance from the eave and the same on every face it is on."""
    poly = Polygon(ring)
    shapes = []
    heights = {}
    for i, f in enumerate(faces):
        if i in gables:
            test.assertIsNone(f, f"side {i}")
            continue
        test.assertIsNotNone(f, f"side {i}")
        a, b = ring[i], ring[(i + 1) % len(ring)]
        starts = {(round(f[0][0], 6), round(f[0][1], 6)), (round(f[1][0], 6), round(f[1][1], 6))}
        test.assertEqual(starts, {(round(a[0], 6), round(a[1], 6)), (round(b[0], 6), round(b[1], 6))}, f"side {i}")
        shape = Polygon([p[:2] for p in f])
        test.assertTrue(shape.is_valid, f"side {i}")
        shapes.append(shape)
        dx, dy = b[0] - a[0], b[1] - a[1]
        for x, y, h in f:
            test.assertAlmostEqual(h, abs(dy * (x - a[0]) - dx * (y - a[1])) / math.hypot(dx, dy), places=6)
            key = (round(x, 4), round(y, 4))
            if key in heights:
                test.assertAlmostEqual(heights[key], h, places=6, msg=f"at {key}")
            heights[key] = h
    test.assertAlmostEqual(sum(s.area for s in shapes), poly.area, places=6)
    test.assertAlmostEqual(unary_union(shapes).area, poly.area, places=6)


class AgainstCgal(unittest.TestCase):
    def test_the_faces_are_those_of_cgal_on_the_306_reference_footprints(self):
        data = json.loads(REFERENCE.read_text(encoding="utf-8"))
        self.assertEqual(len(data["cases"]), 306)
        for case in data["cases"]:
            ring = [tuple(p) for p in case["ring"]]
            with self.subTest(case=case["name"]):
                mine = skeleton.faces(ring)
                theirs = {side_of(f, ring): simplified(f) for f in case["faces"]}
                self.assertEqual(sorted(theirs), list(range(len(ring))))         # one face per side, in order
                for i, f in enumerate(mine):
                    self.assertTrue(same_ring(simplified(f), theirs[i]), f"side {i}: {f} against {theirs[i]}")

    def test_a_footprint_of_twenty_sides_takes_less_than_50_ms(self):
        comb = [(0, 0), (40, 0), (40, 10), (36, 10), (36, 16), (30, 16), (30, 10), (26, 10), (26, 18), (20, 18),
                (20, 10), (16, 10), (16, 14), (10, 14), (10, 10), (6, 10), (6, 20), (2, 20), (2, 10), (0, 10)]
        star = [(round(r * math.cos(2 * math.pi * k / 20), 3), round(r * math.sin(2 * math.pi * k / 20), 3))
                for k, r in enumerate([12, 9, 14, 8, 13, 10, 15, 9, 12, 11, 14, 8, 13, 9, 15, 10, 12, 9, 14, 11])]
        skeleton.faces(PLANS["T"])                  # the first call imports shapely
        for ring in (comb, star):
            self.assertEqual(len(ring), 20)
            best = min(self._time(ring) for _ in range(3))
            self.assertLess(best, 0.050, f"{best * 1000:.1f} ms")

    @staticmethod
    def _time(ring) -> float:
        t = time.perf_counter()
        skeleton.faces(ring)
        return time.perf_counter() - t


class Rectangle(unittest.TestCase):
    """On a rectangle the skeleton gives the roofs of before (roofs.hip and roofs.gable on test_roofs.HOUSE)."""

    HOUSE = [(0.0, 0.0), (12.0, 0.0), (12.0, 8.0), (0.0, 8.0)]

    def test_the_hip_roof_of_a_rectangle(self):
        faces = skeleton.faces(self.HOUSE)
        expected = [[(0, 0, 0), (12, 0, 0), (8, 4, 4), (4, 4, 4)], [(12, 0, 0), (12, 8, 0), (8, 4, 4)],
                    [(12, 8, 0), (0, 8, 0), (4, 4, 4), (8, 4, 4)], [(0, 8, 0), (0, 0, 0), (4, 4, 4)]]
        for f, e in zip(faces, expected, strict=True):
            self.assertTrue(same_ring(f, e), f)

    def test_the_gable_roof_of_a_rectangle(self):
        faces = skeleton.roof(self.HOUSE, {1, 3})
        self.assertIsNone(faces[1])
        self.assertIsNone(faces[3])
        self.assertTrue(same_ring(simplified(faces[0]), [(0, 0, 0), (12, 0, 0), (12, 4, 4), (0, 4, 4)]), faces[0])
        self.assertTrue(same_ring(simplified(faces[2]), [(12, 8, 0), (0, 8, 0), (0, 4, 4), (12, 4, 4)]), faces[2])

    def test_one_eave_and_three_gables_make_a_mono_pitch(self):
        faces = skeleton.roof(self.HOUSE, {1, 2, 3})
        self.assertTrue(same_ring(simplified(faces[0]), [(0, 0, 0), (12, 0, 0), (12, 8, 8), (0, 8, 8)]), faces[0])

    def test_a_clockwise_ring_gives_the_same_faces_by_side(self):
        cw = self.HOUSE[::-1]                       # side i of cw is side 2 - i of HOUSE, reversed
        faces, back = skeleton.faces(cw), skeleton.faces(self.HOUSE)
        for i in range(4):
            self.assertTrue(same_ring(faces[i], back[(2 - i) % 4]), i)


class Cleaning(unittest.TestCase):
    def test_corners_in_line_and_sides_of_no_length_are_taken_away_first(self):
        ring = [(0, 0), (5, 0), (12, 0), (12, 8), (12, 8.00001), (0, 8)]
        pts, origin = skeleton.clean(ring)
        simple = Polygon(ring).simplify(0)
        self.assertEqual(len(pts), len(simple.exterior.coords) - 1)
        self.assertEqual(origin, [0, 2, 4, 5])      # side 0 stands for 0 and 1; side 3, of 10 um, is gone
        faces = skeleton.faces(ring)
        self.assertIsNone(faces[1])
        self.assertIsNone(faces[3])
        self.assertTrue(same_ring(simplified(faces[0]), [(0, 0, 0), (12, 0, 0), (8, 4, 4), (4, 4, 4)]))
        self.assertEqual(skeleton.faces(ring + ring[:1])[0], faces[0])     # a closed ring is the same ring

    def test_a_footprint_the_skeleton_cannot_take_is_said(self):
        for ring, words in (([(0, 0), (10, 0)], "three sides"),
                            ([(0, 0), (10, 10), (10, 0), (0, 10)], "crosses itself"),
                            ([(0, 0), (5, 0), (10, 0), (0, 0)], "three sides")):
            with self.subTest(ring=ring), self.assertRaises(skeleton.SkeletonError) as caught:
                skeleton.faces(ring)
            self.assertIn(words, str(caught.exception))
        with self.assertRaises(skeleton.SkeletonError):
            skeleton.roof(PLANS["rettangolo"], {0, 1, 2, 3})        # no eave


class Gables(unittest.TestCase):
    """The twelve roofs of the proof (study 16, A.5): the six footprints with a hip roof and with two pitches
    and their gable ends; a gable end that does not move gives the faces of the proof's way (the side pushed
    far along its eaves, the faces cut on the footprint)."""

    def test_the_twelve_roofs_of_the_proof(self):
        for name, ring in PLANS.items():
            ring = [tuple(map(float, p)) for p in ring]
            for gables in ((), GABLE_ENDS[name]):
                with self.subTest(plan=name, gables=gables):
                    roof_checks(self, ring, skeleton.roof(ring, set(gables)), gables)

    def test_the_gable_ends_are_those_of_the_proofs_far_sides(self):
        for name, ring in PLANS.items():
            ring = [tuple(map(float, p)) for p in ring]
            ends = GABLE_ENDS[name]
            mine = skeleton.roof(ring, set(ends))
            big = extended_for_gables(ring, ends)
            footprint = Polygon(ring)
            for i, f in enumerate(skeleton.faces(big)):
                if i in ends:
                    continue
                with self.subTest(plan=name, side=i):
                    cut = f and Polygon([p[:2] for p in f]).intersection(footprint)
                    self.assertEqual(cut.geom_type, "Polygon")
                    self.assertAlmostEqual(cut.symmetric_difference(Polygon([p[:2] for p in mine[i]])).area, 0.0,
                                           places=6)

    def test_a_crooked_gable_end_on_a_trapezoid(self):
        ring = PLANS["trapezio"]
        faces = skeleton.roof(ring, {1, 3})
        # the ridge halfway between the two eaves, from gable to gable along the crooked sides
        self.assertTrue(same_ring(simplified(faces[0]), [(0, 0, 0), (22, 0, 0), (20, 5, 5), (1.5, 5, 5)]), faces[0])
        self.assertTrue(same_ring(simplified(faces[2]), [(18, 10, 0), (3, 10, 0), (1.5, 5, 5), (20, 5, 5)]), faces[2])

    def test_an_l_with_its_gables_on_the_arms_has_a_valley_in_the_corner(self):
        faces = skeleton.roof(PLANS["L"], {1, 4})
        self.assertEqual([f is not None for f in faces], [True, False, True, True, False, True])
        # the valley from the inner corner (8, 8) down to (4, 4), where the two ridges meet
        self.assertTrue(same_ring(simplified(faces[2]), [(20, 8, 0), (8, 8, 0), (4, 4, 4), (20, 4, 4)]), faces[2])
        self.assertTrue(same_ring(simplified(faces[3]), [(8, 8, 0), (8, 18, 0), (4, 18, 4), (4, 4, 4)]), faces[3])


if __name__ == "__main__":
    unittest.main()
