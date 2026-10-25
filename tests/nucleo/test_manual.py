"""The layout by hand (manual.py; study 16, C; task 16c): a row drawn with the sub-field's module and gaps, rows
taken away, added at the back, lengthened, moved within their sub-field, exploded into their modules that keep their
keys, a module turned by 90°, Delete, «Lay again automatically», a new module on rows by hand; and the checks the
fire-brigade rules, the exclusions and the shadows become (checks.manual_items)."""

import math
import unittest

import _setup
from _fixtures import laid
from _fixtures import tetto_con_lucernario as project

from meridiana import checks, manual, model, session

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class Drawing(unittest.TestCase):
    def test_a_row_drawn_on_an_empty_sub_field_takes_its_module_gap_and_orientation(self):
        p = project()
        rid = manual.draw(p, "s1", (5.0, 3.0), (15.0, 3.2))(p)
        sf = p.subfields[0]
        self.assertTrue(sf.manual and sf.filled)
        r = laid(p)
        # 10 m along a row of modules 1,134 m wide with 2 cm between them: 8 modules
        self.assertEqual(r.count, 8)
        self.assertEqual({m.rid for m in r.modules}, {rid})
        self.assertEqual({m.azimuth for m in r.modules}, {0.0})
        xs = sorted(c[0] for m in r.modules for c in m.corners)
        self.assertAlmostEqual(xs[0], 5.0, places=4)                           # from the first click
        self.assertAlmostEqual(xs[-1], 5.0 + 8 * 1.134 + 7 * 0.02, places=4)
        self.assertAlmostEqual(min(c[1] for m in r.modules for c in m.corners), 3.0, places=4)   # its front edge

    def test_a_row_drawn_backwards_ends_at_the_first_click_and_one_too_short_has_a_module(self):
        p = project()
        manual.draw(p, "s1", (15.0, 3.0), (10.0, 3.0))(p)
        r = laid(p)
        self.assertAlmostEqual(max(c[0] for m in r.modules for c in m.corners), 15.0, places=4)
        q = project()
        manual.draw(q, "s1", (5.0, 3.0), (5.2, 3.0))(q)
        self.assertEqual(laid(q).count, 1)

    def test_a_row_drawn_on_a_laid_sub_field_joins_its_rows_and_makes_it_by_hand(self):
        p = project()
        p.subfields[0].filled = True
        auto = laid(p)
        rid = manual.draw(p, "s1", (2.0, 27.0), (8.0, 27.0), auto)(p)
        r = laid(p)
        self.assertTrue(r.manual)
        self.assertEqual(r.count, auto.count + 5)
        self.assertNotIn(rid, {row.id for row in auto.rows})

    def test_a_row_over_the_skylight_is_drawn_red_and_kept(self):
        p = project()
        sf = p.subfields[0]
        rows = [manual.line_row(p, sf, (28.0, 13.0), (36.0, 13.0), [])]
        self.assertTrue(manual.trouble(p, sf, rows))
        self.assertFalse(manual.trouble(p, sf, [manual.line_row(p, sf, (5.0, 3.0), (12.0, 3.0), [])]))
        manual.draw(p, "s1", (28.0, 13.0), (36.0, 13.0))(p)
        self.assertEqual(laid(p).count, 6)                                      # 8 m: 6 modules

    def test_tables_of_the_sub_field_are_drawn_whole(self):
        p = project()
        p.subfields[0].params.update({"table_modules": 4, "table_gap": 0.5})
        manual.draw(p, "s1", (5.0, 3.0), (20.0, 3.0))(p)
        xs = sorted(round(min(c[0] for c in m.corners), 3) for m in laid(p).modules)
        gaps = sorted({round(b - a - 1.134, 3) for a, b in zip(xs, xs[1:], strict=False)})
        self.assertEqual(gaps, [0.02, 0.5])
        self.assertEqual(len(xs) % 4, 0)


class Rows(unittest.TestCase):
    def setUp(self):
        self.p = project()
        self.p.subfields[0].filled = True
        self.auto = laid(self.p)
        self.rows = [r for r in self.auto.rows if r.places]

    def test_the_first_gesture_keeps_the_rows_of_the_automatic_layout(self):
        manual.take(self.p, "s1", self.auto)(self.p)
        r = laid(self.p)
        self.assertTrue(r.manual)
        self.assertEqual([m.key for m in r.modules], [m.key for m in self.auto.modules])

    def test_a_row_taken_away_goes_with_its_modules_taken_out(self):
        first = self.rows[0]
        self.p.subfields[0].removed = [first.slot_key(0), self.rows[1].slot_key(0)]
        auto = laid(self.p)
        manual.remove(self.p, "s1", first.id, auto)(self.p)
        r = laid(self.p)
        self.assertEqual(r.count, auto.count - first.count + 1)
        self.assertEqual(self.p.subfields[0].removed, [self.rows[1].slot_key(0)])

    def test_a_row_added_at_the_back_is_one_pitch_behind_the_last(self):
        last = self.rows[-1]
        rid = manual.append(self.p, "s1", self.rows[0].id, self.auto)(self.p)
        r = laid(self.p)
        new = [m for m in r.modules if m.rid == rid]
        self.assertEqual(len(new), self.rows[0].count)
        back = min(c[1] for m in r.modules if m.rid == last.id for c in m.corners)
        self.assertAlmostEqual(min(c[1] for m in new for c in m.corners) - back, self.auto.pitch, delta=2e-3)

    def test_the_end_of_a_row_dragged_lengthens_and_shortens_it(self):
        row = self.rows[0]
        end = manual.end_point(row, manual.frame(self.p, self.p.subfields[0], self.rows)[1])
        manual.resize(self.p, "s1", row.id, (end[0] - 3.0, end[1]), self.auto)(self.p)
        r = laid(self.p)
        self.assertEqual(sum(1 for m in r.modules if m.rid == row.id), row.count - 3)
        manual.resize(self.p, "s1", row.id, (end[0] + 2.5, end[1]), r)(self.p)
        self.assertEqual(sum(1 for m in laid(self.p).modules if m.rid == row.id), row.count + 2)
        manual.resize(self.p, "s1", row.id, (row.x - 9.0, row.y), laid(self.p))(self.p)
        self.assertEqual(sum(1 for m in laid(self.p).modules if m.rid == row.id), 1)

    def test_a_row_moved_keeps_its_keys_and_stays_in_its_sub_field(self):
        row = self.rows[1]
        manual.translate(self.p, "s1", row.id, 0.0, 0.5, self.auto)(self.p)
        r = laid(self.p)
        before = {m.key: m.centre for m in self.auto.modules}
        for m in r.modules:
            self.assertAlmostEqual(m.centre[1] - before[m.key][1], 0.5 if m.rid == row.id else 0.0, delta=1e-3)
        with self.assertRaises(ValueError) as caught:
            manual.translate(self.p, "s1", row.id, 0.0, -40.0, r)
        self.assertIn("stays in its sub-field", str(caught.exception))


class Exploded(unittest.TestCase):
    def setUp(self):
        self.p = project()
        self.p.subfields[0].filled = True
        self.auto = laid(self.p)
        self.row = next(r for r in self.auto.rows if r.places)

    def test_an_exploded_module_moved_30_cm_changes_only_itself(self):
        made = manual.explode(self.p, "s1", self.row.id, self.auto)(self.p)
        self.assertEqual(len(made), self.row.count)
        exploded = laid(self.p)
        self.assertEqual(sorted(m.key for m in exploded.modules), sorted(m.key for m in self.auto.modules))
        one = made[3]
        key = next(m.key for m in exploded.modules if m.rid == one)
        manual.translate(self.p, "s1", one, 0.3, 0.0, exploded)(self.p)
        moved = laid(self.p)
        before = {m.key: m.centre for m in exploded.modules}
        for m in moved.modules:
            self.assertAlmostEqual(m.centre[0] - before[m.key][0], 0.3 if m.key == key else 0.0, delta=1e-3)
            self.assertAlmostEqual(m.centre[1], before[m.key][1], delta=1e-3)

    def test_delete_takes_an_exploded_module_away_and_undo_brings_the_row_back(self):
        s = session.ProjectSession(self.p)
        s.edit("explode", manual.explode(self.p, "s1", self.row.id, self.auto))
        exploded = laid(s.project)
        key = next(m.key for m in exploded.modules if m.rid not in {r.id for r in self.auto.rows})
        s.edit("delete", manual.delete_module(s.project, "s1", key, exploded))
        r = laid(s.project)
        self.assertEqual(r.count, self.auto.count - 1)
        self.assertNotIn(key, r.keys)
        self.assertEqual(s.project.subfields[0].removed, [])          # the row went, not a mask
        s.undo.undo()
        s.undo.undo()
        back = laid(s.project)
        self.assertFalse(s.project.subfields[0].manual)
        self.assertEqual([m.key for m in back.modules], [m.key for m in self.auto.modules])

    def test_the_whole_sub_field_explodes_and_lays_the_same_modules(self):
        manual.explode(self.p, "s1", None, self.auto)(self.p)
        r = laid(self.p)
        self.assertEqual(len(self.p.subfields[0].rows), self.auto.count)
        self.assertEqual(sorted(m.key for m in r.modules), sorted(m.key for m in self.auto.modules))
        self.assertEqual(sorted(m.row for m in r.modules), sorted(m.row for m in self.auto.modules))

    def test_a_module_turned_by_90_degrees_keeps_its_middle_and_a_row_does_not_turn(self):
        made = manual.explode(self.p, "s1", self.row.id, self.auto)(self.p)
        r = laid(self.p)
        m = next(x for x in r.modules if x.rid == made[0])
        manual.turn(self.p, "s1", made[0], r)(self.p)
        t = next(x for x in laid(self.p).modules if x.rid == made[0])
        self.assertTrue(t.turned)
        self.assertAlmostEqual(t.centre[0], m.centre[0], delta=1e-3)
        self.assertAlmostEqual(t.centre[1], m.centre[1], delta=1e-3)
        xs = [c[0] for c in t.corners]
        self.assertAlmostEqual(max(xs) - min(xs), 2.278, places=3)
        other = next(r for r in self.auto.rows if r.places and r.id != self.row.id)
        with self.assertRaises(ValueError):
            manual.turn(self.p, "s1", other.id, laid(self.p))

    def test_a_module_on_a_row_of_many_is_taken_out_by_its_key(self):
        key = self.auto.modules[2].key
        manual.delete_module(self.p, "s1", key, self.auto)(self.p)
        self.assertEqual(self.p.subfields[0].removed, [key])
        self.assertFalse(self.p.subfields[0].manual)


class Again(unittest.TestCase):
    def test_lay_again_automatically_drops_the_rows_by_hand(self):
        p = project()
        p.subfields[0].filled = True
        auto = laid(p)
        manual.translate(p, "s1", auto.rows[0].id, 0.2, 0.0, auto)(p)
        p.subfields[0].removed = [auto.modules[0].key]
        manual.relayout(p, "s1")(p)
        sf = p.subfields[0]
        self.assertEqual((sf.manual, sf.rows, sf.removed, sf.filled), (False, [], [], True))
        self.assertEqual([m.key for m in laid(p).modules], [m.key for m in auto.modules])

    def test_a_module_within_two_centimetres_keeps_the_rows_and_one_larger_asks(self):
        p = project()
        p.subfields[0].filled = True
        manual.take(p, "s1", laid(p))(p)
        p.modules["near"] = {"manufacturer": "X", "model": "N", "length": 2.29, "width": 1.14, "power_kw": 0.46}
        p.modules["big"] = {"manufacturer": "X", "model": "B", "length": 2.38, "width": 1.30, "power_kw": 0.6}
        self.assertFalse(manual.needs_asking(p, "s1", "near"))
        self.assertTrue(manual.needs_asking(p, "s1", "big"))
        before = laid(p)
        manual.change_module(p, "s1", "near")(p)
        after = laid(p)
        self.assertEqual([m.key for m in after.modules], [m.key for m in before.modules])
        row = [m for m in after.modules if m.rid == after.rows[0].id]
        xs = sorted(min(c[0] for c in m.corners) for m in row)
        self.assertAlmostEqual(xs[1] - xs[0], 1.14 + 0.02, places=4)          # the gap between them stays
        manual.change_module(p, "s1", "big", adapt=False)(p)
        self.assertFalse(p.subfields[0].manual)


class ManualChecks(unittest.TestCase):
    def test_a_row_dragged_onto_a_skylight_is_said(self):
        p = project()
        p.subfields[0].filled = True
        auto = laid(p)
        row = auto.rows[2]                     # whole: the rows across the skylight leave it a hole
        self.assertEqual(row.count, max(r.count for r in auto.rows))
        manual.translate(p, "s1", row.id, 0.0, 14.5 - row.y, auto)(p)
        items = checks.manual_items(p, p.subfields[0], laid(p))
        texts = [i.text for i in items]
        self.assertTrue(any("by hand" in t for t in texts))
        found = [i for i in items if "on the exclusion Skylight 1" in i.text]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].fix, ("action", "relayout", "subfield", "s1"))
        everything = checks.gather(p, {"s1": laid(p)}, None)
        self.assertTrue(any("on the exclusion Skylight 1" in i.text for i in everything))
        self.assertTrue(all(len(i.text) <= checks.TEXT_LENGTH for i in everything))

    def test_a_row_26_metres_long_under_the_fire_rules_is_a_group_too_long(self):
        p = project(fire=True)
        manual.draw(p, "s1", (3.0, 3.0), (29.5, 3.0))(p)
        r = laid(p)
        self.assertGreater(r.count, 20)
        items = checks.manual_items(p, p.subfields[0], r)
        group = [i for i in items if "group of" in i.text]
        self.assertEqual(len(group), 1)
        reach = r.count * 1.134 + (r.count - 1) * 0.02
        self.assertIn(f"group of {reach:.1f} m, beyond the 20 m".replace(".", ","), group[0].text.replace(".", ","))
        self.assertEqual(group[0].source, checks.FIRE_SOURCE)
        self.assertTrue(any("edge band" in i.text for i in items) is False)

    def test_a_corridor_left_narrower_than_two_metres_is_said_with_its_width(self):
        p = project(fire=True)
        manual.draw(p, "s1", (3.0, 3.0), (17.0, 3.0))(p)
        manual.draw(p, "s1", (18.5, 3.0), (30.0, 3.0), laid(p))(p)
        r = laid(p)
        items = checks.manual_items(p, p.subfields[0], r)
        corridor = [i for i in items if "corridor of" in i.text]
        self.assertEqual(len(corridor), 1)
        first = [m for m in r.modules if m.rid == p.subfields[0].rows[0]["id"]]
        second = [m for m in r.modules if m.rid == p.subfields[0].rows[1]["id"]]
        gap = min(c[0] for m in second for c in m.corners) - max(c[0] for m in first for c in m.corners)
        self.assertIn(f"{gap:.2f}".replace(".", ","), corridor[0].text.replace(".", ","))

    def test_modules_in_the_shade_of_an_obstacle_on_the_design_day_are_counted(self):
        p = project()
        p.exclusions.append(model.ExclusionItem(id="e2", ring=[[10, 8], [11, 8], [11, 9], [10, 9]], kind="chimney",
                                                building="b1", height=3.0))
        p.subfields[0].filled = True
        auto = laid(p)
        manual.take(p, "s1", auto)(p)
        from meridiana.energy import system
        shaded = [i for i in checks.manual_items(p, p.subfields[0], laid(p), system.shadow_exclusions)
                  if i.area == "shade"]
        self.assertEqual(len(shaded), 1)
        self.assertRegex(shaded[0].text, r"\d+ modules? in the shade on the design day")

    def test_by_hand_the_shadows_of_the_year_offer_no_layout_out_of_them(self):
        from types import SimpleNamespace
        p = project()
        p.subfields[0].filled = True
        energy = {"sim": SimpleNamespace(arrays=[{"key": "s1.0", "name": "Sud", "obstacle_shading": 0.1}], notes=[],
                                         p_stc_kw=50.0, p_ac_kw=40.0), "shade_free_counts": {}}
        shaded = [i for i in checks.gather(p, {"s1": laid(p)}, energy) if "obstacles take" in i.text]
        self.assertEqual(shaded[0].fix[0], "edit")                      # automatic: «keep out of the shadows»
        manual.take(p, "s1", laid(p))(p)
        shaded = [i for i in checks.gather(p, {"s1": laid(p)}, energy) if "obstacles take" in i.text]
        self.assertEqual(shaded[0].fix, ())                             # by hand the option would move nothing

    def test_an_automatic_sub_field_has_none_of_them(self):
        p = project(fire=True)
        p.subfields[0].filled = True
        self.assertEqual(checks.manual_items(p, p.subfields[0], laid(p)), [])
        self.assertFalse(math.isnan(laid(p).pitch))


INVERTER = {"manufacturer": "Generico", "model": "10K", "ac_power_nominal_w": 10000, "efficiency_euro_pct": 97.5,
            "dc_voltage_max_v": 1100, "mppt_voltage_min_v": 180, "mppt_voltage_max_v": 1000, "mppt_count": 2,
            "dc_current_max_per_mppt_a": [16, 16], "dc_isc_max_per_mppt_a": [20, 20]}


class SameOutputs(unittest.TestCase):
    """The strings, the 3D, the report and the comparison of the variants read the modules laid, as before task 16c:
    a sub-field by hand and exploded gives what the automatic one with the same modules gives (task 16c, step 8)."""

    @classmethod
    def setUpClass(cls):
        import tempfile
        from pathlib import Path

        from _fixtures import clear_sky_meteo, write_cache
        cls.cache = Path(tempfile.mkdtemp())
        write_cache(clear_sky_meteo(45.5226, 9.03), cls.cache)

    def pair(self):
        """The same project twice: automatic, and by hand with every row exploded into its modules."""
        from meridiana import jobs
        p = project()
        p.site = model.Site(lat=45.5226, lon=9.03, address="Rho (MI)")
        p.subfields[0].ring = [[1, 1], [30, 1], [30, 14], [1, 14]]
        p.exclusions.append(model.ExclusionItem(id="e2", ring=[[10, 8], [11, 8], [11, 9], [10, 9]], kind="chimney",
                                                building="b1", height=2.0))
        p.subfields[0].filled = True
        p.energy = {"inverters": [{"record": dict(INVERTER), "count": 2, "name": ""}], "strings": {"auto": True}}
        q = model.Project.from_json(p.to_json())
        manual.explode(q, "s1", None, laid(q))(q)
        self.assertTrue(q.subfields[0].manual)
        a, b = jobs.layout_of(p)[0], jobs.layout_of(q)[0]
        self.assertEqual([m.key for m in a["s1"].modules], [m.key for m in b["s1"].modules])
        self.assertGreater(len(q.subfields[0].rows), 10 * len([r for r in a["s1"].rows if r.places]))
        return p, q, a, b

    def test_the_strings_are_the_same(self):
        from meridiana.energy import plant
        p, q, a, b = self.pair()
        one, two = plant.build(p, a), plant.build(q, b)
        self.assertTrue(one.strings)
        self.assertEqual([s.keys for s in one.strings], [s.keys for s in two.strings])
        self.assertEqual([(s.label, s.state) for s in one.strings], [(s.label, s.state) for s in two.strings])
        self.assertEqual(len(one.left), len(two.left))

    def test_the_3d_table_is_the_same(self):
        import numpy as np
        _p, _q, a, b = self.pair()
        self.assertTrue(np.allclose(a["s1"].table, b["s1"].table, atol=1e-4))

    def test_the_report_of_the_strings_is_the_same(self):
        _setup.qt_or_skip()
        from meridiana.energy import plant
        from meridiana.ui.report import plant_html
        p, q, a, b = self.pair()
        self.assertEqual(plant_html(p, plant.build(p, a)), plant_html(q, plant.build(q, b)))

    def test_the_figures_of_the_comparison_are_the_same(self):
        from meridiana import compare
        from meridiana.energy import pipeline
        p, q, a, b = self.pair()
        one = compare.summary(pipeline.compute_or_say(p, a, self.cache, False).as_dict())
        two = compare.summary(pipeline.compute_or_say(q, b, self.cache, False).as_dict())
        self.assertNotIn("error", one)
        self.assertEqual(set(one), set(two))
        for key, value in one.items():
            if isinstance(value, float):
                self.assertAlmostEqual(two[key], value, delta=max(1e-6, abs(value) * 1e-5), msg=key)
            else:
                self.assertEqual(two[key], value, key)


if __name__ == "__main__":
    unittest.main()
