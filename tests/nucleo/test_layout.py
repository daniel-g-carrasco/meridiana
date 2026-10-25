"""Module layout: every module inside the margins, rows far enough apart, the fire-brigade rules kept."""

import itertools
import math
import unittest

import _setup  # noqa: F401
from shapely.geometry import Polygon

from meridiana import layout, sun

ROOF = [(0.0, 0.0), (40.0, 0.0), (40.0, 20.0), (0.0, 20.0)]   # 40 x 20 m, sides along East and North
MILANO = dict(lat=45.4642, lon=9.19)


def polys(result):
    return [Polygon(m.corners) for m in result.modules]


class TiltedRows(unittest.TestCase):
    def setUp(self):
        self.r = layout.compute(ROOF, params=layout.Params(edge=0.5), **MILANO)

    def test_rows_face_south_on_a_roof_squared_to_the_compass(self):
        self.assertAlmostEqual(self.r.azimuth, 0.0, places=6)
        self.assertTrue(all(m.azimuth == 0.0 for m in self.r.modules))

    def test_every_module_keeps_the_edge_band(self):
        roof = Polygon(ROOF)
        self.assertGreater(self.r.count, 100)
        self.assertGreaterEqual(min(roof.exterior.distance(m) for m in polys(self.r)), 0.5 - 1e-6)
        self.assertTrue(all(roof.covers(m) for m in polys(self.r)))

    def test_modules_never_overlap(self):
        ps = polys(self.r)
        overlaps = sum(1 for a, b in itertools.combinations(ps, 2) if a.intersection(b).area > 1e-9)
        self.assertEqual(overlaps, 0)

    def test_the_pitch_leaves_the_clearance_the_sun_asks(self):
        rise = 2.278 * math.sin(math.radians(10))
        expected = sun.row_clearance(rise, 180.0, sun.DesignWindow().positions(**MILANO))
        self.assertAlmostEqual(self.r.clearance, expected, places=3)
        self.assertAlmostEqual(self.r.pitch, 2.278 * math.cos(math.radians(10)) + expected, places=3)
        self.assertGreater(self.r.limit_angle, 0)

    def test_each_row_is_centred_on_the_roof(self):
        row0 = [p for m, p in zip(self.r.modules, polys(self.r), strict=True) if m.row == 0]
        left = min(p.bounds[0] for p in row0)
        right = max(p.bounds[2] for p in row0)
        self.assertAlmostEqual(left - 0.0, 40.0 - right, places=6)

    def test_a_pitch_given_as_a_value_or_a_ratio_is_kept(self):
        r = layout.compute(ROOF, params=layout.Params(pitch_mode="value", pitch=4.0), **MILANO)
        self.assertAlmostEqual(r.pitch, 4.0, places=6)
        r = layout.compute(ROOF, params=layout.Params(pitch_mode="gcr", gcr=0.5), **MILANO)
        self.assertAlmostEqual(r.pitch, 2.278 / 0.5, places=6)

    def test_ballast_alone_is_flagged(self):
        r = layout.compute(ROOF, params=layout.Params(mounting="tilted_ballasted"), **MILANO)
        self.assertIn(layout.BALLAST_WARNING, r.notes)

    def test_modules_taken_out_by_hand_stay_out(self):
        key = self.r.modules[5].key
        r = layout.compute(ROOF, params=layout.Params(edge=0.5), removed={key}, **MILANO)
        self.assertEqual(r.count, self.r.count - 1)
        self.assertNotIn(key, {m.key for m in r.modules})

    def test_tables_leave_their_gap(self):
        r = layout.compute(ROOF, params=layout.Params(table_modules=10, table_gap=0.5), **MILANO)
        row0 = sorted((p.bounds[0], p.bounds[2]) for m, p in zip(r.modules, polys(r), strict=True) if m.row == 0)
        gaps = [round(b[0] - a[1], 3) for a, b in zip(row0, row0[1:], strict=False)]
        self.assertIn(0.5, gaps)
        self.assertEqual(len(row0) % 10, 0)

    def test_a_turned_roof_turns_the_rows(self):
        turned = [tuple(p) for p in Polygon(ROOF).exterior.coords[:-1]]
        import shapely.affinity as aff
        turned = list(aff.rotate(Polygon(turned), 20, origin=(0, 0)).exterior.coords)[:-1]
        r = layout.compute(turned, **MILANO)
        self.assertAlmostEqual(abs(r.azimuth), 20.0, places=3)


class FireRules(unittest.TestCase):
    """The fire brigade's guidelines for PV, DCPREV 14030 of 01/09/2025, 3.3.5.1 points 2-3, p. 15-16: 1 m from the
    edge of the roof, groups of at most 20 m by 20 m two metres apart, 1 m from smoke vents, openings and roof
    plant (verified on the archive: B-norme-citazioni.md, section 3)."""

    def setUp(self):
        self.r = layout.compute([(0, 0), (60, 0), (60, 45), (0, 45)],
                                params=layout.Params(fire_rules=True, edge=0.3), **MILANO)

    def test_one_metre_from_the_roof_edge(self):
        roof = Polygon([(0, 0), (60, 0), (60, 45), (0, 45)])
        self.assertGreaterEqual(min(roof.exterior.distance(m) for m in polys(self.r)), 1.0 - 1e-6)

    def test_groups_are_at_most_twenty_metres_and_two_apart(self):
        by_group = {}
        for m, p in zip(self.r.modules, polys(self.r), strict=True):
            by_group.setdefault(m.group, []).append(p)
        self.assertGreater(len(by_group), 3)
        from shapely.ops import unary_union
        shapes = {g: unary_union(ps) for g, ps in by_group.items()}
        for s in shapes.values():
            minx, miny, maxx, maxy = s.bounds
            self.assertLessEqual(maxx - minx, 20.0 + 1e-6)
            self.assertLessEqual(maxy - miny, 20.0 + 1e-6)
        for a, b in itertools.combinations(shapes.values(), 2):
            self.assertGreaterEqual(a.distance(b), 2.0 - 1e-6)

    def test_a_smoke_vent_keeps_its_metre(self):
        vent = layout.Exclusion(ring=[(20, 20), (22, 20), (22, 22), (20, 22)], kind="vent")
        r = layout.compute([(0, 0), (60, 0), (60, 45), (0, 45)],
                           params=layout.Params(fire_rules=True), exclusions=[vent], **MILANO)
        v = Polygon(vent.ring)
        self.assertGreaterEqual(min(v.distance(m) for m in polys(r)), 1.0 - 1e-6)


class Flush(unittest.TestCase):
    def test_coplanar_modules_follow_the_pitch(self):
        pitch = layout.Surface(tilt=30.0, azimuth=0.0, z0=8.0, x0=0.0, y0=0.0)
        r = layout.compute(ROOF, surface=pitch, params=layout.Params(mounting="coplanar", edge=0.3), **MILANO)
        self.assertTrue(all(m.tilt == 30.0 and m.azimuth == 0.0 for m in r.modules))
        depth = max(p.bounds[3] - p.bounds[1] for p in polys(r))
        self.assertAlmostEqual(depth, 2.278 * math.cos(math.radians(30)), places=6)
        # up the slope (North) the roof is higher
        north = max(r.modules, key=lambda m: m.centre[1])
        south = min(r.modules, key=lambda m: m.centre[1])
        self.assertGreater(north.z, south.z)

    def test_coplanar_on_a_flat_roof_lies_flat(self):
        r = layout.compute(ROOF, params=layout.Params(mounting="coplanar"), **MILANO)
        self.assertTrue(all(m.tilt == 0.0 for m in r.modules))


class EastWest(unittest.TestCase):
    def test_pairs_face_east_and_west(self):
        r = layout.compute(ROOF, params=layout.Params(mounting="east_west", tilt=10.0), **MILANO)
        faces = {m.azimuth for m in r.modules}
        self.assertEqual(faces, {-90.0, 90.0})
        east = sum(1 for m in r.modules if m.azimuth == -90.0)
        self.assertEqual(east * 2, r.count)


class Tables(unittest.TestCase):
    def test_a_table_of_two_counts_every_module(self):
        one = layout.compute(ROOF, params=layout.Params(stack=1, pitch_mode="value", pitch=5.0), **MILANO)
        two = layout.compute(ROOF, params=layout.Params(stack=2, pitch_mode="value", pitch=5.0), **MILANO)
        per_row = sum(1 for m in one.modules if m.row == 0)
        self.assertEqual(sum(1 for m in two.modules if m.row == 0), 2 * per_row)   # deeper tables, fewer rows
        lows = [m for m in two.modules if m.level == 0]
        highs = {(m.row, m.slot): m for m in two.modules if m.level == 1}
        for m in lows:
            upper = highs[(m.row, m.slot)]
            self.assertGreater(upper.z, m.z)              # the second module sits higher up the table
            self.assertGreater(upper.centre[1], m.centre[1])   # and behind it, the rows facing South
            self.assertNotEqual(upper.key, m.key)
        ps = polys(two)
        overlaps = sum(1 for a, b in itertools.combinations(ps, 2) if a.intersection(b).area > 1e-9)
        self.assertEqual(overlaps, 0)
        less = layout.compute(ROOF, params=layout.Params(stack=2, pitch_mode="value", pitch=5.0), **MILANO,
                              removed={highs[(lows[0].row, lows[0].slot)].key})
        self.assertEqual(less.count, two.count - 1)

    def test_both_halves_of_a_pair_rise_to_the_ridge(self):
        r = layout.compute(ROOF, params=layout.Params(mounting="east_west", tilt=10.0, stack=2), **MILANO)
        for face in (-90.0, 90.0):
            side = [m for m in r.modules if m.azimuth == face]
            low = {(m.row, m.slot): m.z for m in side if m.level == 0}
            self.assertTrue(all(m.z > low[(m.row, m.slot)] for m in side if m.level == 1))


class Placing(unittest.TestCase):
    def test_the_corners_placed_in_one_go_are_the_rotated_boxes_of_shapely(self):
        # every module's plan footprint equals box(u0, lo_v, u0 + along, hi_v) scaled back along the slope and
        # rotated out of the work frame by shapely.affinity, corner by corner in the same order; the centre
        # is the centroid, the height the surface's plus the stand-off and the lift
        from shapely import affinity
        from shapely.geometry import box
        surface = layout.Surface(tilt=20.0, azimuth=-30.0, z0=6.0, x0=1.0, y0=2.0)
        rot, slope, along = 37.5, math.cos(math.radians(20.0)), 1.134
        pending = [(r, s, 0, k, -30.0, 3.0 * s + 0.1 * r, 2.0 * r + 0.3 * k, 2.0 * r + 0.3 * k + 1.7, 0.2 * k,
                    f"f{r + 1}:{s}" if k == 0 else f"f{r + 1}:{s}:{k}", f"f{r + 1}")
                   for r in range(3) for s in range(4) for k in range(2)]
        placed = layout._place(pending, along, rot, slope, surface, 0.15, 20.0)
        self.assertEqual([pm.key for pm in placed], [f"f{r + 1}:{s}" if k == 0 else f"f{r + 1}:{s}:{k}"
                                                     for r in range(3) for s in range(4) for k in range(2)])
        self.assertEqual({pm.rid for pm in placed}, {"f1", "f2", "f3"})
        for pm, (r, s, _g, k, a, u0, lo_v, hi_v, lift, _key, _rid) in zip(placed, pending, strict=True):
            foot = affinity.rotate(affinity.scale(box(u0, lo_v, u0 + along, hi_v), 1.0, slope, origin=(0, 0)),
                                   -rot, origin=(0, 0))
            want = list(foot.exterior.coords)[:-1]
            self.assertEqual(len(pm.corners), 4)
            for got, exp in zip(pm.corners, want, strict=True):
                self.assertAlmostEqual(got[0], exp[0], places=12)
                self.assertAlmostEqual(got[1], exp[1], places=12)
            self.assertAlmostEqual(pm.centre[0], foot.centroid.x, places=12)
            self.assertAlmostEqual(pm.centre[1], foot.centroid.y, places=12)
            self.assertAlmostEqual(pm.z, surface.z(*pm.centre) + 0.15 + lift, places=12)
            self.assertEqual((pm.row, pm.slot, pm.level, pm.azimuth, pm.tilt), (r, s, k, a, 20.0))
        self.assertEqual(layout._place([], along, rot, slope, surface, 0.15, 20.0), [])

    def test_the_result_carries_the_corners_and_the_keys_as_arrays(self):
        import numpy as np
        r = layout.compute(ROOF, params=layout.Params(edge=0.5), removed={"f1:1"}, **MILANO)
        self.assertEqual(r.corners.shape, (r.count, 4, 2))
        self.assertEqual(r.keys, [m.key for m in r.modules])
        self.assertNotIn("f1:1", r.keys)
        self.assertTrue(np.array_equal(r.corners, np.array([m.corners for m in r.modules])))
        self.assertIsNone(r.table)
        empty = layout.compute(ROOF, params=layout.Params(edge=25.0), **MILANO)
        self.assertEqual((empty.count, empty.keys, empty.corners.shape), (0, [], (0, 4, 2)))


L_ROOF = [(0, 0), (50, 0), (50, 18), (22, 18), (22, 40), (0, 40)]


def cases():
    """The layouts of before task 16c, with what they gave then (computed on 24/10/2026 by the generator that made
    the modules directly, before the rows): the count, the sums of the corners' East and North and of the heights,
    the number of fire-brigade groups."""
    sky = layout.Exclusion(ring=[(10, 10), (13, 10), (13, 12), (10, 12)], kind="skylight", clearance=0.5)
    plant = layout.Exclusion(ring=[(30, 25), (32, 25), (32, 27), (30, 27)], kind="plant")
    P = layout.Params
    return {
        "tilted": (dict(area_ring=ROOF, params=P(edge=0.5)), (165, 13200.0000, 5643.9636, 57.3846, 1)),
        "tables": (dict(area_ring=ROOF, params=P(table_modules=10, table_gap=0.5)),
                   (150, 12000.0000, 5130.8760, 52.1678, 1)),
        "fire": (dict(area_ring=[(0, 0), (60, 0), (60, 45), (0, 45)], params=P(fire_rules=True, edge=0.3)),
                 (552, 65856.0000, 47621.7071, 191.9775, 6)),
        "coplanar_skew": (dict(area_ring=L_ROOF, surface=layout.Surface(tilt=20.0, azimuth=-30.0, z0=6.0, x0=1, y0=2),
                               params=P(mounting="coplanar", edge=0.4, portrait=False)),
                          (480, 38160.0628, 30525.0444, 3406.0433, 1)),
        "ew2": (dict(area_ring=ROOF, params=P(mounting="east_west", tilt=10.0, stack=2)),
                (256, 21426.2568, 10240.0000, 140.1106, 1)),
        "stack2": (dict(area_ring=ROOF, params=P(stack=2, pitch_mode="value", pitch=5.0)),
                   (198, 15840.0000, 6140.5662, 108.3668, 1)),
        "ground_gcr": (dict(area_ring=L_ROOF, params=P(mounting="ground", pitch_mode="gcr", gcr=0.4, stack=2,
                                                       table_modules=12, table_gap=0.4)),
                       (192, 16512.0000, 10900.4084, 105.0830, 1)),
        "l_fire_tables": (dict(area_ring=L_ROOF, params=P(fire_rules=True, table_modules=8, edge=0.5, azimuth=12.0),
                               exclusions=[sky, plant]), (152, 12203.8514, 9682.9301, 52.8634, 6)),
        "ew_fire": (dict(area_ring=L_ROOF, params=P(mounting="east_west", fire_rules=True, tilt=12.0, stack=2,
                                                     table_modules=6), exclusions=[sky]),
                    (240, 25665.9689, 13248.0000, 150.1685, 3)),
        "removed": (dict(area_ring=ROOF, params=P(edge=0.5), removed={"f1:1", "f3:3"}),
                    (163, 13169.2480, 5603.2710, 56.6890, 1)),
    }


class Rows(unittest.TestCase):
    """The rows as objects (task 16c, step 1): the automatic layout makes rows and the modules come from them."""

    def test_every_case_of_before_lays_the_same_modules_through_its_rows(self):
        # the same corners, centres and heights as the generator of before; the 54 layouts of these cases and of the
        # PVsyst projects of the study were compared module by module on Daniel's PC (24/10/2026): all equal
        for name, (kw, (count, sx, sy, sz, groups)) in cases().items():
            with self.subTest(case=name):
                r = layout.compute(**kw, **MILANO)
                self.assertEqual(r.count, count)
                self.assertAlmostEqual(sum(c[0] for m in r.modules for c in m.corners), sx, places=3)
                self.assertAlmostEqual(sum(c[1] for m in r.modules for c in m.corners), sy, places=3)
                self.assertAlmostEqual(sum(m.z for m in r.modules), sz, places=3)
                self.assertEqual(len({m.group for m in r.modules}), groups)
                self.assertTrue(all(m.key.startswith(m.rid + ":") for m in r.modules))
                self.assertFalse(r.manual)

    def test_the_rows_given_back_lay_the_same_modules(self):
        for name, (kw, _digest) in cases().items():
            with self.subTest(case=name):
                auto = layout.compute(**kw, **MILANO)
                rows = [layout.Row.of(row.as_dict()) for row in auto.rows]      # as the file keeps them
                hand = layout.compute(**kw, rows=rows, **MILANO)
                self.assertTrue(hand.manual)
                self.assertEqual([m.key for m in hand.modules], [m.key for m in auto.modules])
                self.assertEqual([(m.row, m.slot, m.level, m.azimuth) for m in hand.modules],
                                 [(m.row, m.slot, m.level, m.azimuth) for m in auto.modules])
                for a, b in zip(auto.modules, hand.modules, strict=True):
                    for p, q in zip(a.corners, b.corners, strict=True):
                        self.assertAlmostEqual(p[0], q[0], delta=1e-4)        # the file keeps 0,1 mm
                        self.assertAlmostEqual(p[1], q[1], delta=1e-4)
                    self.assertAlmostEqual(a.z, b.z, delta=1e-4)
                self.assertEqual(len(hand.groups), len(layout.clusters(auto.modules, 2.0)) if auto.groups else 0)

    def test_a_row_moved_keeps_the_keys_of_its_modules(self):
        auto = layout.compute(ROOF, params=layout.Params(edge=0.5), **MILANO)
        rows = [layout.Row.of(r.as_dict()) for r in auto.rows]
        rows[2].x += 0.3
        moved = layout.compute(ROOF, params=layout.Params(edge=0.5), rows=rows, **MILANO)
        before = {m.key: m for m in auto.modules}
        for m in moved.modules:
            dx = m.centre[0] - before[m.key].centre[0]
            self.assertAlmostEqual(dx, 0.3 if m.rid == "f3" else 0.0, delta=1e-4)

    def test_a_row_exploded_keeps_the_keys_its_modules_had_and_its_line(self):
        auto = layout.compute(ROOF, params=layout.Params(edge=0.5), **MILANO)
        row = auto.rows[0]
        # the rows face South: x grows along them
        alone = [layout.Row(f"f{90 + i}", row.x + u, row.y, row.azimuth, [0.0], keys=[row.slot_key(i)])
                 for i, u in enumerate(row.places)]
        hand = layout.compute(ROOF, params=layout.Params(edge=0.5), rows=alone + auto.rows[1:], **MILANO)
        self.assertEqual(sorted(m.key for m in hand.modules), sorted(m.key for m in auto.modules))
        self.assertEqual({m.row for m in hand.modules if m.rid.startswith("f9")}, {0})   # still one line

    def test_a_turned_row_lays_the_other_side_along_it(self):
        p = layout.Params(edge=0.5, mounting="coplanar")
        auto = layout.compute(ROOF, params=p, **MILANO)
        row = auto.rows[0]
        r = layout.compute(ROOF, params=p, rows=[layout.Row("f50", row.x, row.y, row.azimuth, [0.0], turned=True)],
                           **MILANO)
        (m,) = r.modules
        xs, ys = [c[0] for c in m.corners], [c[1] for c in m.corners]
        self.assertAlmostEqual(max(xs) - min(xs), 2.278, places=6)      # landscape along an East-West row
        self.assertAlmostEqual(max(ys) - min(ys), 1.134, places=6)
        self.assertTrue(m.turned)

    def test_keys_taken_out_that_match_no_module_are_said(self):
        r = layout.compute(ROOF, params=layout.Params(edge=0.5), removed={"f1:0", "f99:3", "x"}, **MILANO)
        self.assertEqual(r.unmatched, ["f99:3", "x"])

    def test_by_hand_the_fire_groups_come_from_the_modules_two_metres_apart(self):
        area, p = [(0, 0), (60, 0), (60, 45), (0, 45)], layout.Params(fire_rules=True, edge=0.3)
        auto = layout.compute(area, params=p, **MILANO)
        rows = [layout.Row.of(r.as_dict()) for r in auto.rows if r.places]
        self.assertEqual(len(layout.compute(area, params=p, rows=rows, **MILANO).groups), 6)
        # the corridor between two groups of rows, 2 m: the rows behind it brought 1 m closer join them
        fronts = [layout.Frame.of(r.azimuth, 10.0, False).to_work(r.x, r.y)[1] for r in rows]
        depth = 2.278 * math.cos(math.radians(10.0))
        gaps = [b - a - depth for a, b in zip(fronts, fronts[1:], strict=False)]
        k = next(i for i, g in enumerate(gaps) if abs(g - 2.0) < 1e-3) + 1
        for row in rows[k:]:
            row.y -= 1.0
        joined = layout.compute(area, params=p, rows=rows, **MILANO)
        self.assertEqual(len(joined.groups), 3)


class Refusals(unittest.TestCase):
    def test_an_unknown_mounting_is_refused(self):
        with self.assertRaises(ValueError):
            layout.compute(ROOF, params=layout.Params(mounting="hovering"))

    def test_a_degenerate_area_is_refused(self):
        with self.assertRaises(ValueError):
            layout.compute([(0, 0), (1, 0), (0.5, 0.0001)])


if __name__ == "__main__":
    unittest.main()
