"""How the automatic layout places the modules in a row (R418) and how many it lays for a power asked (R417)."""

import hashlib
import json
import math
import unittest

import _setup  # noqa: F401
import shapely
from shapely.geometry import Polygon

from meridiana import layout, model

SHAPES = {
    "rectangle": [(0, 0), (30, 0), (30, 18), (0, 18)],
    "trapezoid": [(0, 2.6), (16.2, 0), (20.0, 21.2), (0.6, 22.0)],
    "L": [(0, 0), (40, 0), (40, 12), (18, 12), (18, 30), (0, 30)],
    "roof": [(0, 0), (120, 6), (116, 90), (-4, 84)],
}
BLOCK = [layout.Exclusion([(6, 6), (9, 6), (9, 9), (6, 9)], "skylight", 0.5)]
VARIANTS = {
    "tilted": (dict(), None, ()),
    "ground_2v": (dict(mounting="ground", stack=2, tilt=25.0), None, ()),
    "flush_pitch": (dict(mounting="coplanar"), layout.Surface(tilt=20.0, azimuth=10.0, z0=8.0), ()),
    "flush_landscape": (dict(mounting="coplanar", portrait=False), layout.Surface(tilt=20.0), ()),
    "east_west": (dict(mounting="east_west", tilt=10.0), None, ()),
    "tables": (dict(table_modules=6, table_gap=0.4), None, ()),
    "fire": (dict(fire_rules=True), None, ()),
    "exclusion": (dict(), None, BLOCK),
}
# what the layout gave before R418 for a sub-field that does not say how to align: modules and a digest of their
# keys and corners. A project saved before must open with these very modules.
BEFORE = {
    ("rectangle", "tilted"): (125, '4dda1b90bf7c'),
    ("rectangle", "ground_2v"): (100, '426c7737ed34'),
    ("rectangle", "flush_pitch"): (165, 'c61afcc81994'),
    ("rectangle", "flush_landscape"): (180, 'e12d19f56629'),
    ("rectangle", "east_west"): (168, '3534e5abeffc'),
    ("rectangle", "tables"): (120, '8edea81ea6f6'),
    ("rectangle", "fire"): (88, '5904245841dd'),
    ("rectangle", "exclusion"): (117, 'b562ed161bbc'),
    ("trapezoid", "tilted"): (71, 'a15be69c1cea'),
    ("trapezoid", "ground_2v"): (28, 'ea01d7520205'),
    ("trapezoid", "flush_pitch"): (106, '35e7426bfe0c'),
    ("trapezoid", "flush_landscape"): (115, '26aad3bd1ec5'),
    ("trapezoid", "east_west"): (64, 'b2df260bb14d'),
    ("trapezoid", "tables"): (60, '888c5ed682a7'),
    ("trapezoid", "fire"): (52, '6ba5a056d3c4'),
    ("trapezoid", "exclusion"): (64, '35dae6618fc3'),
    ("L", "tilted"): (169, '0180e708e960'),
    ("L", "ground_2v"): (122, 'a760569e3632'),
    ("L", "flush_pitch"): (248, 'b66ad0877d59'),
    ("L", "flush_landscape"): (272, '0ae274da0596'),
    ("L", "east_west"): (240, '3917268d54b1'),
    ("L", "tables"): (150, '4db7a6d58e94'),
    ("L", "fire"): (155, 'a2ac1604f05a'),
    ("L", "exclusion"): (163, 'd943fd71252a'),
    ("roof", "tilted"): (2369, '864da40dd854'),
    ("roof", "ground_2v"): (1442, 'af898ec61670'),
    ("roof", "flush_pitch"): (3834, '640bbae4622b'),
    ("roof", "flush_landscape"): (3850, 'd0e27918c13c'),
    ("roof", "east_west"): (3312, 'd8cb5cd712e3'),
    ("roof", "tables"): (2208, '2169a102f829'),
    ("roof", "fire"): (2024, '897668dd907e'),
    ("roof", "exclusion"): (2361, 'feb2ae2d603a'),
}
MILANO = dict(lat=45.5, lon=9.1)
MODULE_475 = layout.Module(power_kw=0.475)


def digest(result) -> tuple[int, str]:
    text = json.dumps([[pm.key, [[round(x, 6), round(y, 6)] for x, y in pm.corners]] for pm in result.modules])
    return result.count, hashlib.sha1(text.encode()).hexdigest()[:12]


def laid(shape, variant, removed=frozenset(), module=None, **extra):
    kw, surface, blocked = VARIANTS[variant]
    return layout.compute(SHAPES[shape], surface, module or layout.Module(), layout.Params(**{**kw, **extra}),
                          list(blocked), removed=set(removed), **MILANO)


def places(result):
    """Each row that holds modules, front to back: where its places start along the row, in the work frame."""
    out = []
    for row in result.rows:
        if not row.places:
            continue
        kw_frame = layout.Frame.of(row.azimuth, 0.0, False)
        u0, v0 = kw_frame.to_work(row.x, row.y)
        out.append((v0, [u0 + u for u in row.places]))
    return [r for _v, r in sorted(out, key=lambda item: item[0])]


def residues(values, step):
    return {round(((u % step) + step) % step, 3) % round(step, 3) for u in values}


class SavedProjectsStayTheSame(unittest.TestCase):
    def test_a_sub_field_that_says_nothing_lays_the_very_modules_of_before(self):
        for (shape, variant), expected in BEFORE.items():
            with self.subTest(shape=shape, variant=variant):
                self.assertEqual(digest(laid(shape, variant)), expected)

    def test_modules_taken_out_by_hand_stay_out_of_the_same_places(self):
        r = laid("trapezoid", "tilted", {"f2:1", "f3:4"})
        self.assertEqual(digest(r), (69, '7e5bec56abee'))

    def test_the_frozen_files_open_with_the_modules_they_had(self):
        p, notice = model.Project.load(_setup.FORMATS / "progetto-v25.meridiana")
        self.assertIsNone(notice)
        for sf in p.subfields:
            self.assertNotIn("alignment", sf.params)
            self.assertEqual(sf.layout_params().alignment, layout.LEGACY_ALIGNMENT)
            self.assertEqual(sf.layout_params().target_kwp, 0.0)

    def test_the_key_of_a_saved_sub_field_does_not_change(self):
        p, _notice = model.Project.load(_setup.FORMATS / "progetto-v25.meridiana")
        sf = p.subfields[0]
        before = p.layout_key(sf)
        self.assertNotIn("alignment", before)
        self.assertNotIn("target_kwp", before)
        sf.params["alignment"] = "aligned"
        self.assertNotEqual(p.layout_key(sf), before)

    def test_an_explicit_change_is_what_lays_differently(self):
        before = laid("trapezoid", "tilted")
        for mode in layout.ALIGNMENTS:
            self.assertNotEqual(digest(laid("trapezoid", "tilted", alignment=mode)), digest(before), mode)

    def test_an_unknown_way_is_refused(self):
        with self.assertRaises(ValueError):
            laid("rectangle", "tilted", alignment="diagonal")


class EveryWay(unittest.TestCase):
    def test_the_modules_stay_inside_and_never_overlap(self):
        for (shape, variant) in BEFORE:
            for mode in layout.ALIGNMENTS:
                with self.subTest(shape=shape, variant=variant, mode=mode):
                    r = laid(shape, variant, alignment=mode)
                    self.assertGreater(r.count, 0)
                    usable = Polygon(r.usable[0]) if len(r.usable) == 1 else None
                    polys = [Polygon(pm.corners) for pm in r.modules]
                    if usable is not None:
                        grown = usable.buffer(0.001)
                        self.assertTrue(all(grown.contains(q) for q in polys))
                    self.assertAlmostEqual(sum(q.area for q in polys),
                                           shapely.union_all(polys).area, places=4)

    def test_more_freedom_never_lays_fewer_modules(self):
        for (shape, variant) in BEFORE:
            with self.subTest(shape=shape, variant=variant):
                aligned = laid(shape, variant, alignment="aligned").count
                staggered = laid(shape, variant, alignment="staggered").count
                free = laid(shape, variant, alignment="free").count
                self.assertLessEqual(aligned, staggered)
                self.assertLessEqual(staggered, free)
                self.assertLessEqual(BEFORE[shape, variant][0], free)

    def test_on_a_rectangle_the_three_ways_are_the_rows_of_before(self):
        before = laid("rectangle", "tilted")
        for mode in layout.ALIGNMENTS:
            r = laid("rectangle", "tilted", alignment=mode)
            self.assertEqual(r.count, before.count, mode)
            for a, b in zip(r.modules, before.modules, strict=True):
                self.assertEqual(a.key, b.key)
                for (x0, y0), (x1, y1) in zip(a.corners, b.corners, strict=True):
                    self.assertAlmostEqual(x0, x1, places=6)
                    self.assertAlmostEqual(y0, y1, places=6)

    def test_modules_taken_out_by_hand_stay_out(self):
        for mode in layout.ALIGNMENTS:
            whole = laid("trapezoid", "tilted", alignment=mode)
            gone = {whole.keys[3], whole.keys[10]}
            r = laid("trapezoid", "tilted", gone, alignment=mode)
            self.assertEqual(r.count, whole.count - 2, mode)
            self.assertFalse(gone & set(r.keys), mode)
            self.assertEqual(r.unmatched, [], mode)

    def test_fire_groups_stay_at_most_twenty_metres(self):
        for mode in layout.ALIGNMENTS:
            r = laid("roof", "fire", alignment=mode)
            frame = layout.Frame.of(r.azimuth, 0.0, False)
            members: dict = {}
            for i, pm in enumerate(r.modules):
                members.setdefault(pm.group, []).append(i)
            self.assertGreater(len(members), 1, mode)
            for idx in members.values():
                self.assertLessEqual(layout.extent(r.modules, idx, frame), 20.0 + 1e-6, mode)


class Aligned(unittest.TestCase):
    def test_the_columns_stay_straight(self):
        step = layout.Module().width + layout.Params().gap
        for shape in SHAPES:
            r = laid(shape, "tilted", alignment="aligned")
            self.assertEqual(len(residues([u for row in places(r) for u in row], step)), 1, shape)

    def test_it_picks_the_origin_that_lays_most(self):
        # the rows of this shape have free lengths that only one origin of the columns serves all at once: an origin
        # taken from the outline's corner, or the middle, loses a module per row
        r = laid("trapezoid", "tilted", alignment="aligned")
        self.assertEqual(r.count, 72)

    def test_the_columns_stay_straight_in_tables(self):
        p = layout.Params()
        period = 6 * layout.Module().width + 5 * p.gap + 0.4
        r = laid("trapezoid", "tables", alignment="aligned")
        starts = [row[0::6] for row in places(r)]
        self.assertEqual(len(residues([u for row in starts for u in row], period)), 1)

    def test_rows_on_a_pitch_are_straight_along_the_slope(self):
        r = laid("trapezoid", "flush_pitch", alignment="aligned")
        step = layout.Module().width + layout.Params().gap
        frame = layout.Frame.of(r.azimuth, r.tilt, True)
        us = [min(frame.to_work(*q)[0] for q in pm.corners) for pm in r.modules]
        self.assertEqual(len(residues(us, step)), 1)


class Staggered(unittest.TestCase):
    def test_a_row_moves_from_the_next_by_half_a_module_or_not_at_all(self):
        step = layout.Module().width + layout.Params().gap
        for shape in SHAPES:
            r = laid(shape, "tilted", alignment="staggered")
            found = residues([u for row in places(r) for u in row[:1]], step / 2)
            self.assertEqual(len(found), 1, shape)
            rows = [residues(row, step) for row in places(r)]
            self.assertTrue(all(len(x) == 1 for x in rows), shape)

    def test_it_really_staggers_when_that_lays_more(self):
        aligned = laid("trapezoid", "flush_landscape", alignment="aligned")
        r = laid("trapezoid", "flush_landscape", alignment="staggered")
        along = layout.Module().length + layout.Params().gap
        self.assertGreater(r.count, aligned.count)
        frame = layout.Frame.of(r.azimuth, r.tilt, True)
        starts = {}
        for pm in r.modules:
            v = round(min(frame.to_work(*q)[1] for q in pm.corners), 2)
            u = min(frame.to_work(*q)[0] for q in pm.corners)
            starts[v] = min(starts.get(v, u), u)
        grids = {round(u % along, 2) for u in starts.values()}
        self.assertEqual(len(grids), 2)
        low, high = sorted(grids)
        self.assertAlmostEqual(high - low, along / 2, delta=0.011)


class Free(unittest.TestCase):
    def test_it_fits_a_row_in_a_shape_where_the_front_edge_wastes_room(self):
        before = laid("L", "flush_pitch").count
        self.assertGreater(laid("L", "flush_pitch", alignment="free").count, before)

    def test_a_row_may_stand_further_than_the_pitch_never_closer(self):
        for shape in SHAPES:
            r = laid(shape, "tilted", alignment="free")
            frame = layout.Frame.of(r.azimuth, 0.0, False)
            vs = sorted(frame.to_work(row.x, row.y)[1] for row in r.rows if row.places)
            self.assertTrue(all(b - a >= r.pitch - 0.002 for a, b in zip(vs, vs[1:], strict=False)), shape)

    def test_rows_line_up_where_the_room_lets_them(self):
        # the photo of Daniel (20261105): the free rows are not all shifted from one another for nothing
        step = layout.Module().width + layout.Params().gap
        r = laid("trapezoid", "tilted", alignment="free")
        old = laid("trapezoid", "tilted")
        self.assertLess(len(residues([row[0] for row in places(r)], step)),
                        len(residues([row[0] for row in places(old)], step)))


class Reshaped(unittest.TestCase):
    def test_a_vertex_moved_leaves_the_columns_straight(self):
        step = layout.Module().width + layout.Params().gap
        ring = [list(q) for q in SHAPES["trapezoid"]]
        for dx, dy in ((3.0, -2.0), (-1.0, 4.0), (2.5, 2.5)):
            moved = [[ring[0][0] + dx, ring[0][1] + dy], *ring[1:]]
            r = layout.compute(moved, params=layout.Params(alignment="aligned"), **MILANO)
            self.assertEqual(len(residues([u for row in places(r) for u in row], step)), 1, (dx, dy))


class TargetPower(unittest.TestCase):
    def test_nearest_module_count_even_above_the_power_asked(self):
        self.assertEqual(layout.target_modules(45.0, 0.475), 95)      # 94,7: 45,125 kWp
        self.assertEqual(layout.target_modules(44.9, 0.475), 95)      # 94,5..: above half
        self.assertEqual(layout.target_modules(44.6, 0.475), 94)

    def test_on_equal_distance_the_one_that_does_not_exceed(self):
        self.assertEqual(layout.target_modules(0.475 * 94.5, 0.475), 94)
        self.assertEqual(layout.target_modules(1.0, 0.4), 2)          # 2,5
        self.assertEqual(layout.target_modules(0.1, 0.475), 1)        # at least one

    def test_the_layout_holds_the_count_asked(self):
        r = layout.compute(SHAPES["rectangle"], module=MODULE_475,
                           params=layout.Params(alignment="aligned", target_kwp=45.0), **MILANO)
        self.assertEqual(r.count, 95)
        self.assertAlmostEqual(r.count * MODULE_475.power_kw, 45.125)
        self.assertEqual(r.target_missing, 0)
        self.assertEqual(r.capacity, 125)

    def test_it_says_how_many_are_missing_and_the_most_it_can_hold(self):
        r = layout.compute(SHAPES["rectangle"], module=MODULE_475,
                           params=layout.Params(alignment="aligned", target_kwp=100.0), **MILANO)
        self.assertEqual(r.count, 125)
        self.assertEqual(r.capacity, 125)
        self.assertEqual(r.target_missing, 211 - 125)

    def test_rows_compact_no_random_holes(self):
        for mode in (layout.LEGACY_ALIGNMENT, *layout.ALIGNMENTS):
            r = layout.compute(SHAPES["roof"], module=MODULE_475,
                               params=layout.Params(alignment=mode, target_kwp=45.0), **MILANO)
            self.assertEqual(r.count, 95, mode)
            lines = sorted({pm.row for pm in r.modules})
            self.assertEqual(lines, list(range(lines[0], lines[-1] + 1)), mode)
            for row in r.rows:
                offsets = sorted(row.places)
                step = layout.Module().width + layout.Params().gap
                for a, b in zip(offsets, offsets[1:], strict=False):
                    self.assertLess(b - a, step + 0.01, mode)

    def test_keys_stay_those_of_the_whole_layout(self):
        whole = laid("roof", "tilted", alignment="aligned")
        by_key = {pm.key: pm for pm in whole.modules}
        r = laid("roof", "tilted", alignment="aligned", target_kwp=45.0)
        self.assertEqual(r.count, 100)
        for pm in r.modules:
            self.assertIn(pm.key, by_key)
            for (x0, y0), (x1, y1) in zip(pm.corners, by_key[pm.key].corners, strict=True):
                self.assertAlmostEqual(x0, x1, places=6)
                self.assertAlmostEqual(y0, y1, places=6)

    def test_modules_taken_out_do_not_count(self):
        whole = laid("rectangle", "tilted", alignment="aligned", target_kwp=45.0)
        gone = {whole.keys[2], whole.keys[7]}
        r = laid("rectangle", "tilted", gone, alignment="aligned", target_kwp=45.0)
        self.assertEqual(r.count, whole.count)
        self.assertFalse(gone & set(r.keys))
        self.assertEqual(r.unmatched, [])

    def test_stacks_and_pairs_go_by_place(self):
        r = laid("roof", "ground_2v", alignment="aligned", target_kwp=45.0)
        self.assertEqual(r.count % 2, 0)
        self.assertEqual(r.count, 100)
        r = laid("roof", "east_west", alignment="aligned", target_kwp=45.5, module=MODULE_475)
        self.assertEqual(r.count % 2, 0)
        self.assertEqual(abs(r.count * 0.475 - 45.5) <= 0.475, True)

    def test_tables_stay_whole(self):
        r = laid("roof", "tables", alignment="aligned", target_kwp=45.0)
        self.assertEqual(r.count % 6, 0)
        self.assertEqual(r.count, 102)                                # 100 asked, 6 by 6: 102 is the nearest

    def test_fire_groups_stay_right_after_the_cut(self):
        whole = laid("roof", "fire", alignment="aligned")
        groups = {pm.key: pm.group for pm in whole.modules}
        r = laid("roof", "fire", alignment="aligned", target_kwp=200.0)
        self.assertLess(r.count, whole.count)
        self.assertTrue(all(pm.group == groups[pm.key] for pm in r.modules))

    def test_it_starts_from_the_rows_in_no_shadow(self):
        # a shadow over the front half of the roof: the rows asked stand behind it
        shadow = [layout.Exclusion([(-10, -10), (130, -10), (130, 40), (-10, 40)], "shadow")]
        r = layout.compute(SHAPES["roof"], module=layout.Module(),
                           params=layout.Params(alignment="aligned", target_kwp=45.0), shaded=[(1.0, shadow)], **MILANO)
        free = layout.compute(SHAPES["roof"], module=layout.Module(),
                              params=layout.Params(alignment="aligned", target_kwp=45.0), **MILANO)
        self.assertEqual(r.count, free.count)
        self.assertLess(min(pm.centre[1] for pm in free.modules), 20.0)
        self.assertGreater(min(pm.centre[1] for pm in r.modules), 40.0)

    def test_without_shadows_it_starts_from_the_front_row(self):
        r = laid("roof", "tilted", alignment="aligned", target_kwp=45.0)
        self.assertEqual(min(pm.row for pm in r.modules), 0)

    def test_a_sub_field_laid_by_hand_is_kept(self):
        whole = laid("rectangle", "tilted")
        r = layout.compute(SHAPES["rectangle"], params=layout.Params(target_kwp=9.0), rows=whole.rows, **MILANO)
        self.assertEqual(r.count, whole.count)


class TheProject(unittest.TestCase):
    def project(self):
        p = model.Project(name="prova")
        b = model.Building(id="b1", name="Capannone", footprint=[[0, 0], [60, 0], [60, 40], [0, 40]], height=6.0)
        p.buildings.append(b)
        p.exclusions.append(model.ExclusionItem(id="e1", ring=[[10, 22], [20, 22], [20, 30], [10, 30]], kind="plant",
                                                building="b1", height=6.0))
        p.subfields.append(model.SubField(id="s1", name="S", ring=[[1, 1], [59, 1], [59, 39], [1, 39]], building="b1",
                                          params=model.new_params("tilted_anchored"), filled=True))
        return p

    def test_a_new_sub_field_stands_aligned(self):
        self.assertEqual(model.new_params("ground"), {"mounting": "ground", "alignment": "aligned"})

    def test_fill_gives_the_shadows_only_when_a_power_is_asked(self):
        from meridiana.energy import system
        p = self.project()
        sf = p.subfields[0]
        calls = []

        def shade(project, s, window):
            calls.append(window)
            return system.shadow_exclusions(project, s, window)
        p.fill(sf, shade=shade)
        self.assertEqual(calls, [])
        sf.params["target_kwp"] = 10.0
        r = p.fill(sf, shade=shade)
        self.assertEqual(len(calls), len(model.TARGET_WINDOWS))
        self.assertEqual(r.count, 22)

    def test_the_power_asked_avoids_the_shadow_of_the_plant(self):
        from meridiana.energy import system
        p = self.project()
        sf = p.subfields[0]
        sf.params["target_kwp"] = 40.0
        r = p.fill(sf, shade=system.shadow_exclusions)
        shadow = Polygon(system.shadow_exclusions(p, sf, p.fill_params(sf).window)[0].ring)
        self.assertEqual(r.count, 89)
        hit = sum(Polygon(pm.corners).intersects(shadow) for pm in r.modules)
        self.assertLessEqual(hit, 2)

    def test_the_shadows_are_in_the_key_only_when_a_power_is_asked(self):
        p = self.project()
        sf = p.subfields[0]
        self.assertNotIn('"shade"', p.layout_key(sf))
        sf.params["target_kwp"] = 10.0
        self.assertIn('"shade"', p.layout_key(sf))

    def test_a_file_with_the_new_settings_comes_back(self):
        p = self.project()
        sf = p.subfields[0]
        sf.params.update(alignment="free", target_kwp=45.0)
        again = model.Project.from_json(json.loads(json.dumps(p.to_json())))
        self.assertEqual(again.subfields[0].params["alignment"], "free")
        self.assertEqual(again.subfields[0].layout_params().target_kwp, 45.0)

    def test_nonsense_in_a_file_is_said(self):
        p = self.project()
        for key, value in (("alignment", "diagonal"), ("alignment", 3), ("target_kwp", "tanti"),
                           ("target_kwp", -1.0), ("target_kwp", math.inf)):
            data = p.to_json()
            data["variants"][0]["design"]["subfields"][0]["params"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                model.Project.from_json(data)


if __name__ == "__main__":
    unittest.main()
