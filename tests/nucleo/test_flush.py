"""The sub-field as its modules (R445, format 27): drawn as a grid whose outline is flush with the outer modules,
reshaped by moving a side without moving the modules laid (rows and columns added or taken away, counted first as
ghosts), stepped by taking modules out, the modules on an obstacle set aside in red and put back with a click, the
fire-brigade bands as guides and as exclusions; and a side of any outline moved parallel to itself (R473)."""

import json
import unittest

import _setup  # noqa: F401
from _fixtures import tetto_con_lucernario

from meridiana import checks, manual, model, sides

setUpModule = _setup.keep_global_state


def flat_roof(fire: bool = False) -> model.Project:
    """A flat roof of 40 x 20 m with a smoke vent and a sub-field drawn as modules over 25 x 12 m of it: 5 rows of
    21 modules flat on the roof (portrait, 1,134 x 2,278 m, 2 cm apart)."""
    p = model.Project(name="Prova")
    p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                                      height=8.0, fire=model.Fire(subject=fire)))
    p.exclusions.append(model.ExclusionItem(id="e1", ring=[[18, 8], [22, 8], [22, 12], [18, 12]], kind="vent",
                                            building="b1"))
    sf = model.SubField(id="s1", name="Tetto", ring=[[5, 3], [30, 3], [30, 15], [5, 15]], building="b1",
                        pitch=p.buildings[0].pitch_ref(0), params=model.new_params("coplanar"))
    p.subfields.append(sf)
    manual.make_flush(p, sf)
    return p


class Drawn(unittest.TestCase):
    def test_a_grid_of_rows_by_hand_with_the_outline_flush_with_the_modules(self):
        p = flat_roof()
        sf = p.subfields[0]
        self.assertTrue(sf.flush and sf.manual and sf.filled)
        self.assertEqual(len(sf.rows), 5)
        r = p.fill(sf)
        self.assertEqual(r.count + len(r.blocked), 105)
        xs = [x for x, _y in sf.ring]
        ys = [y for _x, y in sf.ring]
        self.assertAlmostEqual(min(ys), 3.0, places=3)                     # the front edge of the first row
        self.assertAlmostEqual(max(ys), 3.0 + 5 * 2.278 + 4 * 0.02, places=3)
        self.assertAlmostEqual(max(xs) - min(xs), 21 * 1.134 + 20 * 0.02, places=3)
        self.assertEqual(p.fill_params(sf).edge, 0.0)                     # no band hidden inside it

    def test_the_modules_on_the_vent_are_set_aside_and_come_back_with_a_click(self):
        p = flat_roof(fire=True)
        sf = p.subfields[0]
        r = p.fill(sf)
        self.assertTrue(r.blocked)
        self.assertFalse({m.key for m in r.blocked} & {m.key for m in r.modules})
        aside = r.blocked[0]
        manual.add_module(p, "s1", aside.centre, r)(p)
        self.assertEqual(sf.kept, [aside.key])
        again = p.fill(sf)
        self.assertIn(aside.key, [m.key for m in again.modules])
        self.assertEqual(len(again.blocked), len(r.blocked) - 1)
        warned = [it for it in checks.manual_items(p, sf, again) if "on the exclusion" in it.text]
        self.assertEqual(len(warned), 1, [it.text for it in checks.manual_items(p, sf, again)])

    def test_a_module_off_the_roof_is_set_aside_too(self):
        p = flat_roof()
        sf = p.subfields[0]
        r = p.fill(sf)
        manual.shift_side(p, "s1", 1, 15.0, r)(p)                          # the East side past the roof's edge at 40
        again = p.fill(sf)
        self.assertTrue(all(max(x for x, _y in m.corners) <= 40.0 + 1e-3 for m in again.modules))
        self.assertTrue(again.blocked)

    def test_taking_a_corner_module_out_steps_the_outline(self):
        p = flat_roof()
        sf = p.subfields[0]
        r = p.fill(sf)
        corner = min(r.modules, key=lambda m: (m.centre[1], m.centre[0]))
        manual.delete_module(p, "s1", corner.key, r)(p)
        self.assertEqual(len(sf.ring), 6)
        self.assertNotIn(corner.key, [m.key for m in p.fill(sf).modules])

    def test_the_file_keeps_it_and_a_file_of_before_reads_the_same(self):
        p = flat_roof()
        sf = p.subfields[0]
        sf.kept.append("f1:0")
        data = json.loads(json.dumps(p.to_json()))
        self.assertEqual(data["version"], model.FORMAT_VERSION)     # 27 brought it (R445); 28 the solids, 29 R523
        q = model.Project.from_json(data)
        self.assertTrue(q.subfields[0].flush)
        self.assertEqual(q.subfields[0].kept, ["f1:0"])
        old = tetto_con_lucernario()
        raw = next(v["design"] for v in old.to_json()["variants"])["subfields"][0]
        self.assertNotIn("flush", raw)
        self.assertNotIn("kept", raw)
        self.assertFalse(model.Project.from_json(json.loads(json.dumps(old.to_json()))).subfields[0].flush)

    def test_laying_again_grids_it_whole_and_keeps_it_as_modules(self):
        p = flat_roof()
        sf = p.subfields[0]
        r = p.fill(sf)
        manual.delete_module(p, "s1", r.modules[30].key, r)(p)       # one in the middle: the outline stays
        manual.relayout(p, "s1")(p)
        self.assertTrue(sf.flush and sf.manual)
        self.assertEqual(sf.removed, [])
        self.assertEqual(p.fill(sf).count + len(p.fill(sf).blocked), 105)


class Reshaped(unittest.TestCase):
    def test_moving_a_side_out_adds_whole_columns_and_the_modules_laid_stay(self):
        p = flat_roof()
        sf = p.subfields[0]
        r = p.fill(sf)
        before = {m.key: m.centre for m in r.modules}
        seen = manual.preview_shift(p, sf, 1, 3.0, r)                      # the East side, 3 m out
        self.assertEqual((seen["added"], seen["removed"]), (10, 0))        # two columns of five rows
        manual.shift_side(p, "s1", 1, 3.0, r)(p)
        after = {m.key: m.centre for m in p.fill(sf).modules}
        for key, centre in before.items():
            self.assertEqual(after[key], centre)
        self.assertEqual(len(after), len(before) + 10)
        self.assertAlmostEqual(max(x for x, _y in sf.ring), 5.393 + 23 * 1.134 + 22 * 0.02, places=2)

    def test_moving_a_side_in_takes_whole_rows_away(self):
        p = flat_roof()
        sf = p.subfields[0]
        r = p.fill(sf)
        seen = manual.preview_shift(p, sf, 2, -2.5, r)                     # the South side, 2,5 m in
        self.assertEqual((seen["added"], seen["removed"]), (0, 42))        # two rows: the second one is cut
        self.assertEqual(len(seen["remove"]), 42)
        manual.shift_side(p, "s1", 2, -2.5, r)(p)
        self.assertEqual(len(sf.rows), 3)
        self.assertAlmostEqual(min(y for _x, y in sf.ring), 7.596, places=3)

    def test_a_new_row_past_the_last_keeps_its_columns(self):
        p = flat_roof()
        sf = p.subfields[0]
        r = p.fill(sf)
        seen = manual.preview_shift(p, sf, 0, 2.5, r)                      # the North side, 2,5 m out: one row
        self.assertEqual((seen["added"], seen["removed"]), (21, 0))
        manual.shift_side(p, "s1", 0, 2.5, r)(p)
        rows = sf.hand_rows()
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[-1].places, rows[0].places)
        self.assertAlmostEqual(rows[-1].y - rows[-2].y, 2.298, places=3)

    def test_the_ghosts_are_the_modules_that_would_come_and_go(self):
        p = flat_roof()
        sf = p.subfields[0]
        r = p.fill(sf)
        seen = manual.preview_shift(p, sf, 3, 1.2, r)                      # the West side: one column
        self.assertEqual(len(seen["add"]), 5)
        self.assertTrue(all(len(c) == 4 for c in seen["add"]))
        self.assertTrue(all(min(x for x, _y in c) < 5.393 for c in seen["add"]))

    def test_a_move_that_folds_the_outline_is_refused(self):
        p = flat_roof()
        sf = p.subfields[0]
        with self.assertRaises(ValueError):
            manual.preview_shift(p, sf, 2, -20.0, p.fill(sf))


class FireBands(unittest.TestCase):
    def test_the_guides_are_drawn_for_a_building_subject_to_the_rules(self):
        p = flat_roof(fire=True)
        guides = p.fire_guides()
        self.assertEqual([bid for bid, _ring in guides], ["b1", "b1"])
        inner = guides[0][1]
        self.assertEqual({round(x) for x, _y in inner}, {1, 39})            # 1 m in from the roof edge
        self.assertEqual(p.fire_guides.__func__(flat_roof()), [])          # not subject: no guide

    def test_the_bands_become_exclusions_once(self):
        p = flat_roof()
        made = p.fire_bands()
        self.assertEqual(len(made), 4)
        self.assertEqual({e.kind for e in made}, {"band"})
        self.assertEqual(len(p.fire_bands()), 0)
        self.assertEqual(len(p.fire_bands("b2")), 0)
        r = p.fill(p.subfields[0])
        self.assertTrue(r.blocked)                                          # the modules in the band are set aside
        data = json.loads(json.dumps(p.to_json()))
        self.assertEqual(len([e for e in model.Project.from_json(data).exclusions if e.kind == "band"]), 4)


class ParallelSides(unittest.TestCase):
    RECT = [[0, 0], [40, 0], [40, 20], [0, 20]]
    ELL = [[0, 0], [30, 0], [30, 10], [10, 10], [10, 25], [0, 25]]

    def test_a_side_moves_along_its_normal_and_its_neighbours_follow(self):
        self.assertEqual(sides.shift(self.RECT, 1, 5.0), [[0, 0], [45.0, 0], [45.0, 20.0], [0, 20]])
        self.assertEqual(sides.shift(self.RECT, 2, -3.0), [[0, 0], [40, 0], [40.0, 17.0], [0.0, 17.0]])
        self.assertEqual(sides.shift(self.ELL, 3, 2.0)[3:5], [[12.0, 10.0], [12.0, 25.0]])

    def test_the_outward_normal_and_the_offset_of_a_point(self):
        self.assertEqual(sides.outward(self.RECT, 1), (1.0, 0.0))
        self.assertEqual(sides.outward(list(reversed(self.RECT)), 1), (1.0, 0.0))    # drawn the other way round
        self.assertAlmostEqual(sides.offset(self.RECT, 1, (43.0, 5.0)), 3.0)
        self.assertAlmostEqual(sides.offset(self.RECT, 0, (10.0, 2.0)), -2.0)

    def test_an_oblique_side_keeps_the_angles_of_its_neighbours(self):
        ring = [[0, 0], [30, 0], [25, 10], [5, 10]]                         # a trapezium
        moved = sides.shift(ring, 2, 4.0)                                   # the top, 4 m up
        self.assertAlmostEqual(moved[2][1], 14.0)
        self.assertAlmostEqual(moved[2][0], 23.0)                           # the slanted side lengthened on its line
        self.assertAlmostEqual(moved[3][0], 7.0)

    def test_what_would_fold_or_vanish_is_refused(self):
        with self.assertRaises(ValueError):
            sides.shift(self.RECT, 1, -40.0)
        with self.assertRaises(ValueError):
            sides.shift(self.RECT, 0, -21.0)                                # past the far side: a fold

    def test_a_building_keeps_its_eave_when_a_side_moves(self):
        p = model.Project(name="Prova")
        b = model.Building(id="b1", name="Casa", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]], height=8.0,
                           roof=model.Roof(type="gable", tilt=15.0, edges=["eave", "gable", "eave", "gable"]))
        p.buildings.append(b)
        b.footprint = sides.shift(b.footprint, 1, 5.0)
        self.assertEqual([pp.z0 for pp in b.pitches()], [8.0, 8.0])
        self.assertEqual(max(x for x, _y in b.pitches()[0].ring), 45.0)


if __name__ == "__main__":
    unittest.main()
