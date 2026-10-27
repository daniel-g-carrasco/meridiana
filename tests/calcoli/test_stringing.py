"""Strings and CEI 64-8/7:2024: the standard's own example of Annex B, the range of modules in series of
an inverter, protections when strings are many, and a layout suggested for a roof."""

import unittest

import _setup  # noqa: F401

from meridiana.energy import stringing
from meridiana.energy.components import InverterSpec, ModuleSpec


def module(**k) -> ModuleSpec:
    rec = {"manufacturer": "Acme", "model": "450", "pmax": 450, "vmp": 33.6, "imp": 13.4, "voc": 40.1, "isc": 14.1,
           "beta_voc": -0.25, "alpha_isc": 0.046, "gamma_pmax": -0.30, "cells": 108, "length": 1.762, "width": 1.134,
           "max_system_voltage_v": 1500, "max_series_fuse_a": 25}
    rec.update(k)
    return ModuleSpec.from_record(rec)


def inverter(**k) -> InverterSpec:
    rec = {"manufacturer": "Acme", "model": "10K", "ac_power_nominal_w": 10000, "efficiency_euro_pct": 97.5,
           "dc_voltage_max_v": 1100, "mppt_voltage_min_v": 180, "mppt_voltage_max_v": 1000, "mppt_count": 2,
           "dc_current_max_per_mppt_a": [16, 16], "dc_isc_max_per_mppt_a": [20, 20]}
    rec.update(k)
    return InverterSpec.from_record(rec)


class Standard(unittest.TestCase):
    def test_the_example_of_annex_b(self):
        # CEI 64-8/7:2024-07, Allegato B, p. 109 (B-norme-citazioni.md, section 3): multicrystalline module,
        # Uoc 38.3 V, -0.35 %/°C, Tmin -15 °C: KU 1.14, Uoc max 43.7 V
        m = module(voc=38.3, beta_voc=-0.35)
        self.assertAlmostEqual(stringing.ku(m, -15.0), 1.14, places=6)
        self.assertAlmostEqual(stringing.ku(m, -15.0) * 38.3, 43.7, delta=0.05)

    def test_without_the_temperature_the_standards_twenty_percent(self):
        self.assertAlmostEqual(stringing.ku(module(), None), 1.2)      # KU = 1,2: CEI 64-8/7:2024-07 Allegato B p. 109

    def test_the_voltage_limit_is_the_lower_of_inverter_and_module(self):
        self.assertEqual(stringing.voltage_limit(module(max_system_voltage_v=1000), inverter()), 1000.0)
        self.assertEqual(stringing.voltage_limit(module(), inverter()), 1100.0)


class Layout(unittest.TestCase):
    def test_the_range_of_modules_in_series(self):
        lo, hi = stringing.series_range(module(), inverter(), -10.0, 70.0)
        # 1100 V over 40.1 x 1.0875 V: 25 modules at most; the MPPT window ends first
        self.assertGreater(lo, 0)
        self.assertLessEqual(hi * 40.1 * stringing.ku(module(), -10.0), 1100.0)
        self.assertGreaterEqual(lo * stringing.vmp_at(module(), 70.0), 180.0)

    def test_a_plan_within_the_rules_passes(self):
        p = stringing.plan(module(), inverter(), 12, [1, 1], -10.0, 70.0)
        self.assertTrue(p.ok, [(c.key, c.detail) for c in p.checks if not c.ok])
        self.assertTrue(p.record.find("uocmax").formula)

    def test_too_many_modules_in_series_fail(self):
        p = stringing.plan(module(), inverter(), 30, [1, 0], -10.0, 70.0)
        self.assertFalse(p.ok)
        self.assertFalse(next(c for c in p.checks if c.key == "uoc").ok)

    def test_too_many_strings_on_one_input_fail_on_short_circuit_current(self):
        p = stringing.plan(module(), inverter(), 12, [2, 0], -10.0, 70.0)
        self.assertFalse(next(c for c in p.checks if c.key == "isc0").ok)        # 2 x 17.6 A on 20 A
        imp = next(c for c in p.checks if c.key == "imp0")                       # 26.8 A on 16 A: a loss
        self.assertTrue(imp.ok)
        self.assertEqual(imp.level, "warn")

    def test_a_layout_with_no_string_is_not_fine(self):
        self.assertFalse(stringing.plan(module(), inverter(), 12, [0, 0], -10.0, 70.0).ok)

    def test_a_real_inverter_and_module_of_the_catalogue(self):
        from meridiana import catalog
        inv = catalog.search("inverters", "SUN2000-20KTL-M5", source="curated")
        mod = catalog.search("modules", "LR7-54HVH", source="curated")
        if not inv or not mod:
            self.skipTest("the datasheets are not in the catalogue")
        p = stringing.suggest(ModuleSpec.from_record(mod[0]), InverterSpec.from_record(inv[0]), 40, -10.0, 70.0)
        self.assertTrue(p.ok, [(c.key, c.detail) for c in p.checks if not c.ok])
        self.assertEqual(p.modules, 40)

    def test_three_strings_ask_about_protection(self):
        inv = inverter(mppt_count=1, dc_current_max_per_mppt_a=[60], dc_isc_max_per_mppt_a=[80])
        p = stringing.plan(module(), inv, 12, [3], -10.0, 70.0)
        fuse = next(c for c in p.checks if c.key == "fuse0")
        # 1.35 x 25 = 33.75 A, (3 - 1) x 17.6 A = 35.25 A: protection needed (CEI 64-8/7:2024-07 712.431.101-102,
        # p. 95)
        self.assertIn("1.35", fuse.detail)

    def test_a_suggestion_uses_the_modules(self):
        s = stringing.suggest(module(), inverter(), 24, -10.0, 70.0)
        self.assertIsNotNone(s)
        self.assertTrue(s.ok, [(c.key, c.detail) for c in s.checks if not c.ok])
        self.assertEqual(s.modules, 24)



class Wiring(unittest.TestCase):
    def laid(self, **params):
        from meridiana import layout
        roof = [(0.0, 0.0), (30.0, 0.0), (30.0, 14.0), (0.0, 14.0)]
        return layout.compute(roof, params=layout.Params(pitch_mode="value", pitch=4.0, **params), lat=45.5,
                              lon=9.0).modules

    def test_a_string_runs_along_a_row_and_back_along_the_next(self):
        import math
        placed = self.laid()
        order = stringing.serpentine(placed)
        self.assertEqual(len(order), len(placed))
        steps = [math.dist(a.centre, b.centre) for a, b in zip(order, order[1:], strict=False)]
        self.assertLess(max(steps), 4.5)                 # never a jump across the roof: the next row starts near

    def test_the_inputs_take_their_strings_and_the_rest_is_said(self):
        placed = self.laid()
        w = stringing.assign([("s1", placed)], 10, [2, 1], inverters=2)
        self.assertEqual(len(w.runs), 6)                 # two inverters, three strings each
        self.assertEqual([r.label for r in w.runs][:3], ["1.1.1", "1.1.2", "1.2.1"])
        self.assertTrue(all(len(r.modules) == 10 for r in w.runs))
        self.assertEqual(len(w.left), len(placed) - 60)
        keys = [k for r in w.runs for _s, k, _c in r.modules] + [k for _s, k, _c in w.left]
        self.assertEqual(len(keys), len(set(keys)))      # every module once

    def test_a_string_never_mixes_two_arrays(self):
        placed = self.laid()
        half = len(placed) // 2
        w = stringing.assign([("a", placed[:half]), ("b", placed[half:])], 7, [50])
        self.assertTrue(all(len({sf for sf, _k, _c in r.modules}) == 1 for r in w.runs))


def grid(rows: int, per_row: int, x0: float = 0.0) -> list:
    """Modules facing South in `rows` rows of `per_row`, 1.2 m apart along the row and 3 m between the rows."""
    from meridiana import layout
    out = []
    for r in range(rows):
        for s in range(per_row):
            x, y = x0 + 1.2 * s, 3.0 * r
            out.append(layout.PlacedModule(r, s, 0, [(x - 0.5, y - 1), (x + 0.5, y - 1), (x + 0.5, y + 1),
                                                     (x - 0.5, y + 1)], (x, y), 1.0, 15.0, 0.0))
    return out


def plant_project(entries: list, strings: dict | None = None, targets: dict | None = None):
    """A project with the inverters `entries` and the strings `strings` («auto»: Meridiana's proposal, as a project of
    before format 14 had it, written down at the first layout by the window)."""
    from meridiana import model
    p = model.Project(name="Prova")
    p.energy = {"inverters": [{"record": rec, "count": n, "name": ""} for rec, n in entries]}
    if strings is not None:
        p.energy["strings"] = strings
    for sfid, (inv, mppt) in (targets or {}).items():
        p.subfields.append(model.SubField(id=sfid, name=sfid, ring=[[0, 0], [1, 0], [1, 1]],
                                          params={"inverter": inv, "mppt": mppt}))
    return p


def inverter_rec(**k) -> dict:
    rec = {"manufacturer": "Acme", "model": "10K", "ac_power_nominal_w": 10000, "efficiency_euro_pct": 97.5,
           "dc_voltage_max_v": 1100, "mppt_voltage_min_v": 180, "mppt_voltage_max_v": 1000, "mppt_count": 2,
           "dc_current_max_per_mppt_a": [16, 16], "dc_isc_max_per_mppt_a": [20, 20]}
    rec.update(k)
    return rec


class Plant(unittest.TestCase):
    """The plant of task 16d (energy/plant.py): the strings of an array spread over the inputs as PVsyst spreads
    them, the checks for each input and inverter, the modules in no string by inverter."""

    def group(self, placed, sfid="s1"):
        from meridiana.energy import plant
        return plant.Group(f"{sfid}.0", sfid, sfid, module(), placed)

    def test_ten_strings_on_three_mppt_are_three_three_four(self):
        from meridiana.energy import plant
        self.assertEqual(stringing.spread(10, 3), [3, 3, 4])
        self.assertEqual(stringing.spread(7, 2), [3, 4])
        self.assertEqual(stringing.spread(2, 3), [0, 1, 1])
        three = inverter_rec(mppt_count=3, dc_current_max_per_mppt_a=[60] * 3, dc_isc_max_per_mppt_a=[80] * 3,
                             ac_power_nominal_w=40000)
        p = plant_project([(three, 1)], {"auto": True, "strategy": "rows", "n_series": 12})
        out = plant.build(p, groups=[self.group(grid(10, 12))])
        per = [len(out.inputs[(1, k)].strings) for k in (1, 2, 3)]
        self.assertEqual(per, [3, 3, 4])
        self.assertEqual([s.label for s in out.strings][:4], ["1.1.1", "1.1.2", "1.1.3", "1.2.1"])
        self.assertFalse(out.left)
        self.assertTrue(all(len(s.modules) == 12 for s in out.strings))      # identical strings on every input

    def test_the_strings_of_a_sub_field_go_to_the_input_it_names(self):
        from meridiana.energy import plant
        two = inverter_rec(mppt_count=2, dc_isc_max_per_mppt_a=[80, 80], dc_current_max_per_mppt_a=[60, 60])
        p = plant_project([(two, 2)], {"auto": True, "strategy": "rows", "n_series": 12}, {"s1": (2, 2)})
        out = plant.build(p, groups=[plant.Group("s1.0", "s1", "s1", module(), grid(2, 12), (2, 2))])
        self.assertEqual({(s.inverter, s.mppt) for s in out.strings}, {(2, 2)})
        self.assertEqual(len(out.units), 2)

    def test_an_inverter_overloaded_beyond_three_percent_fails_on_a_program_threshold(self):
        import numpy as np

        from meridiana.energy import plant
        year = np.r_[np.full(1000, 12000.0), np.zeros(7760)]
        self.assertAlmostEqual(stringing.overload_loss(year, 10000.0, 1.0), 100 * 2000 / 12000)
        self.assertEqual(stringing.overload_check("Inverter 1", 3.1).level, "fail")
        self.assertEqual(stringing.overload_check("Inverter 1", 1.0).level, "warn")
        self.assertEqual(stringing.overload_check("Inverter 1", 0.1).level, "ok")
        self.assertIn("program", stringing.overload_check("Inverter 1", 3.1).detail)
        self.assertEqual(stringing.threshold_source().kind, "default")        # said as Meridiana's, not a norm's
        small = inverter_rec(ac_power_nominal_w=8000, dc_isc_max_per_mppt_a=[80, 80],
                             dc_current_max_per_mppt_a=[60, 60])
        p = plant_project([(small, 1)], {"auto": True, "strategy": "rows", "n_series": 12})
        placed = grid(2, 12)                                    # 24 x 450 W = 10.8 kWp on 8 kW
        hours = np.r_[np.full(1500, 10800.0), np.full(1500, 4000.0), np.zeros(5760)]
        out = plant.build(p, groups=[self.group(placed)], t_cell_max_year=62.0, p_dc_hourly=hours)
        overload = next(c for c in out.checks[1] if c.key == "overload")
        self.assertEqual(overload.level, "fail")
        from meridiana import checks
        item = next(i for i in checks.plant_items(out) if "beyond the nominal power" in i.text)
        self.assertEqual((item.level, item.area, item.target), ("fail", "strings", ("phase", "plant")))
        self.assertIn("not a standard", item.source)

    def test_inputs_loaded_unevenly_are_a_warning(self):
        self.assertIsNone(stringing.imbalance_check("I", [5000.0, 0.0]))
        self.assertEqual(stringing.imbalance_check("I", [3.0, 3.0, 4.0]).level, "ok")        # PVsyst's own 3 + 3 + 4
        self.assertEqual(stringing.imbalance_check("I", [1.0, 4.0]).level, "warn")

    def test_the_modules_in_no_string_are_counted_by_inverter(self):
        from meridiana.energy import plant
        two = inverter_rec(dc_isc_max_per_mppt_a=[20, 20])          # one string per input
        p = plant_project([(two, 1)], {"auto": True, "strategy": "rows", "n_series": 12})
        out = plant.build(p, groups=[self.group(grid(3, 13))])
        self.assertEqual(len(out.strings), 2)
        self.assertEqual(len(out.left), 3 * 13 - 24)
        self.assertEqual(out.left_by_unit, {1: 15})
        from meridiana import checks
        self.assertTrue(any("15 modules in no string" in i.text for i in checks.plant_items(out)))

    def test_the_checks_of_the_plant_say_why_and_what_to_do_and_their_defaults(self):
        """The detail of the Checks panel (task 17e) on the plant's items too (task 16d): an input's check by its
        key, the modules in no string; the defaults of the strings' plan in «ready for delivery», in the Plant."""
        from meridiana import checks
        from meridiana.energy import plant
        p = plant_project([(inverter_rec(), 1)], {"auto": True, "strategy": "rows", "n_series": 26})
        out = plant.build(p, groups=[self.group(grid(2, 26) + grid(1, 3, 40.0))])
        items = checks.plant_items(out)
        uoc = next(i for i in items if "Uoc max" in i.text)
        self.assertEqual(uoc.level, "fail")
        self.assertEqual(uoc.detail, checks.string_detail("uoc"))
        left = next(i for i in items if "in no string" in i.text)
        self.assertEqual(left.detail, checks.left_detail())
        defaults = checks.defaults_in_use({"plant": out})
        cold = next(i for i in defaults if "lowest temperature of the site" in i.text)
        self.assertEqual(cold.target, ("phase", "plant"))
        from meridiana import model
        none = checks.plant_items(plant.build(model.Project(name="Prova"), groups=[self.group(grid(1, 12))]))
        self.assertLessEqual(len(none[0].text), checks.TEXT_LENGTH)              # the note itself in the detail
        self.assertIn("catalogue", none[0].detail)

    def test_before_the_year_the_strings_are_checked_at_pvsyst_design_conditions(self):
        from meridiana.energy import plant
        p = plant_project([(inverter_rec(), 1)], {"auto": True, "strategy": "rows", "n_series": 12})
        out = plant.build(p, groups=[self.group(grid(1, 12))])
        self.assertEqual((out.t_cell_max, out.t_cell_cold, out.t_min, out.year), (60.0, 20.0, -10.0, False))
        plan = out.inputs[(1, 1)].plan
        step = plan.record.find("vmp")
        cell = next(q for q in step.inputs if q.symbol == r"T_{c,max}")
        self.assertEqual((cell.value, cell.source.kind), (60.0, "default"))
        self.assertIn("PVsyst", cell.source.label)
        self.assertEqual(out.strings[0].state, "ok")
        year = plant.build(p, groups=[self.group(grid(1, 12))], t_cell_max_year=65.0)
        self.assertEqual((year.t_cell_max, year.t_cell_cold, year.year), (65.0, -10.0, True))

    def test_without_a_catalogue_inverter_nothing_is_proposed_and_it_is_said(self):
        from meridiana import model
        from meridiana.energy import plant
        p = model.Project(name="Prova")
        out = plant.build(p, groups=[self.group(grid(2, 12))])
        self.assertFalse(out.strings)
        self.assertEqual(len(out.left), 24)
        self.assertIn("catalogue", out.notes[0])


def keys(strings) -> list[list[str]]:
    return [[pm.key for pm in s] for s in strings]


class Strategies(unittest.TestCase):
    """PVsyst's «Auto Attribution» strategies on a layout of 3 rows of 8 modules (task 16d, step 4)."""

    def test_back_and_forth_runs_along_a_row_and_back_along_the_next(self):
        from meridiana.energy import plant
        strings, left, starts = plant.order(grid(3, 8), 8, "serpentine")
        self.assertEqual(keys(strings), [[f"0:{s}" for s in range(8)], [f"1:{s}" for s in range(7, -1, -1)],
                                         [f"2:{s}" for s in range(8)]])
        self.assertEqual((left, starts), ([], [0, 1, 2]))
        strings, _left, starts = plant.order(grid(3, 8), 4, "serpentine")
        self.assertEqual(keys(strings)[2], ["1:7", "1:6", "1:5", "1:4"])
        self.assertEqual(starts, [0, 0, 1, 1, 2, 2])
        strings, left, _starts = plant.order(grid(3, 8), 5, "serpentine")      # cut along the path
        self.assertEqual(keys(strings)[1], ["0:5", "0:6", "0:7", "1:7", "1:6"])
        self.assertEqual(len(left), 24 - 20)

    def test_one_row_per_string_leaves_the_end_of_each_row_out(self):
        from meridiana.energy import plant
        strings, left, _starts = plant.order(grid(3, 8), 8, "rows")
        self.assertEqual(keys(strings), [[f"{r}:{s}" for s in range(8)] for r in range(3)])
        strings, left, _starts = plant.order(grid(3, 8), 6, "rows")
        self.assertEqual(len(strings), 3)
        self.assertEqual(sorted(pm.key for pm in left), ["0:6", "0:7", "1:6", "1:7", "2:6", "2:7"])

    def test_u_goes_out_along_one_row_and_back_along_the_next(self):
        from meridiana.energy import plant
        strings, left, starts = plant.order(grid(3, 8), 8, "u")
        self.assertEqual(keys(strings), [["0:0", "0:1", "0:2", "0:3", "1:3", "1:2", "1:1", "1:0"],
                                         ["0:4", "0:5", "0:6", "0:7", "1:7", "1:6", "1:5", "1:4"],
                                         [f"2:{s}" for s in range(8)]])       # the row left alone: along it
        self.assertEqual((left, starts), ([], [0, 0, 2]))
        first = strings[0]
        import math
        self.assertLess(math.dist(first[0].centre, first[-1].centre), 3.1)     # both ends at the same side

    def test_the_modules_left_out_are_counted_without_laying_the_strings(self):
        from meridiana.energy import plant
        for rows, per in ((3, 8), (5, 13), (2, 7)):
            placed = grid(rows, per)
            lengths = [per] * rows
            for strategy in ("serpentine", "rows", "u", "row_per_mppt"):
                for n in range(2, 15):
                    with self.subTest(rows=rows, strategy=strategy, n=n):
                        self.assertEqual(plant._left_out(lengths, n, strategy),
                                         len(plant.order(placed, n, strategy)[1]))

    def test_one_row_per_mppt_puts_the_strings_of_a_row_on_one_input(self):
        from meridiana.energy import plant
        three = inverter_rec(mppt_count=3, dc_current_max_per_mppt_a=[60] * 3, dc_isc_max_per_mppt_a=[80] * 3)
        p = plant_project([(three, 1)], {"auto": True, "strategy": "row_per_mppt", "n_series": 4})
        out = plant.build(p, groups=[plant.Group("s1.0", "s1", "s1", module(), grid(3, 8))])
        rows = {}
        for s in out.strings:
            rows.setdefault(s.mppt, set()).update(k.split(":")[0] for _sf, k, _c in s.modules)
        self.assertEqual(rows, {1: {"0"}, 2: {"1"}, 3: {"2"}})
        self.assertEqual([len(out.inputs[(1, k)].strings) for k in (1, 2, 3)], [2, 2, 2])


class ByHand(unittest.TestCase):
    """The designer's strings (task 16d, step 4): touching one makes them his; they follow the module keys of
    today's layout, survive a row moved and are said lost when the row is gone."""

    def plant_of(self, placed, runs, auto=False):
        from meridiana.energy import plant
        p = plant_project([(inverter_rec(dc_isc_max_per_mppt_a=[80, 80], dc_current_max_per_mppt_a=[60, 60]), 1)],
                          {"auto": auto, "strategy": "rows", "n_series": 8, "runs": runs})
        return plant.build(p, groups=[plant.Group("s1.0", "s1", "s1", module(), placed)])

    def test_touching_the_proposal_makes_it_the_designers(self):
        from meridiana.energy import plant
        proposal = self.plant_of(grid(3, 8), [], auto=True)
        runs = plant.runs_of(proposal)
        self.assertEqual(len(runs), 3)
        self.assertEqual(runs[0], {"inverter": 1, "mppt": 1, "modules": [f"s1/0:{s}" for s in range(8)]})
        runs, robbed = plant.add_modules(runs, 0, ["s1/1:0"])          # taken from the second string, said
        self.assertEqual((robbed, runs[0]["modules"][-1], len(runs[1]["modules"])), ([1], "s1/1:0", 7))
        strings = plant.touched({"auto": True, "strategy": "rows", "n_series": 8}, runs)
        self.assertEqual((strings.get("auto"), strings["strategy"], len(strings["runs"])), (None, "rows", 3))
        mine = self.plant_of(grid(3, 8), strings["runs"])
        self.assertFalse(mine.auto)
        self.assertEqual([len(s.modules) for s in mine.strings], [9, 7, 8])
        self.assertEqual([s.run for s in mine.strings], [0, 1, 2])
        runs, i = plant.remove_module(strings["runs"], "s1/0:3")
        self.assertEqual((i, len(runs[0]["modules"])), (0, 8))
        runs, j = plant.new_run(runs, 2, 1, ["s1/2:0", "s1/2:1"])
        self.assertEqual((j, runs[j]["inverter"], runs[j]["mppt"], len(runs[2]["modules"])), (3, 2, 1, 6))
        self.assertEqual(plant.reversed_run(runs, 3)[3]["modules"], ["s1/2:1", "s1/2:0"])
        # a string emptied goes when the strings are kept
        runs, _i = plant.remove_module([{"inverter": 1, "mppt": 1, "modules": ["s1/0:0"]}], "s1/0:0")
        self.assertEqual(plant.touched({}, runs)["runs"], [])

    def test_a_string_skips_a_module_starts_or_ends_where_asked_and_says_its_voltages(self):
        """R57 (Daniel, 24/10/2026): a module in the middle skipped and the rest kept, the string cut to start or
        end at a module (what is cut off is left in no string), its voltages against the limits in one line."""
        from meridiana.energy import plant
        run = {"inverter": 1, "mppt": 1, "modules": [f"s1/0:{s}" for s in range(8)]}
        runs, i = plant.remove_module([run], "s1/0:3")                  # skipped: the rest stays, in its order
        self.assertEqual((i, runs[0]["modules"]), (0, [f"s1/0:{s}" for s in (0, 1, 2, 4, 5, 6, 7)]))
        runs, i = plant.cut_run([run], "s1/0:2", "from")
        self.assertEqual((i, runs[0]["modules"]), (0, [f"s1/0:{s}" for s in range(2, 8)]))
        runs, i = plant.cut_run([run], "s1/0:2", "to")
        self.assertEqual(runs[0]["modules"], ["s1/0:0", "s1/0:1", "s1/0:2"])
        self.assertEqual(plant.cut_run([run], "s9/0:0", "to")[1], -1)
        mine = self.plant_of(grid(1, 8), [run])
        line = plant.voltages(mine.strings[0])
        self.assertIn("8 modules", line)
        self.assertIn("Uoc cold", line)
        self.assertIn("window", line)
        short = self.plant_of(grid(1, 8), [{"inverter": 1, "mppt": 1, "modules": ["s1/0:0", "s1/0:1"]}])
        lo = short.strings[0].plan.n_series_min
        if lo > 2:
            self.assertIn(f"{lo - 2} short", plant.voltages(short.strings[0]))

    def test_the_dcac_ratio_and_its_energy_cut_once_the_year_is_there(self):
        """R62: the ratio of the plant, and the energy cut only when a year was given (None before)."""
        from meridiana.energy import plant
        run = {"inverter": 1, "mppt": 1, "modules": [f"s1/0:{s}" for s in range(8)]}
        mine = self.plant_of(grid(1, 8), [run])
        ratio, loss = plant.dcac(mine)
        self.assertGreater(ratio, 0.0)
        self.assertIsNone(loss)
        mine.clipping = {1: 2.0}
        self.assertAlmostEqual(plant.dcac(mine)[1], 2.0)
        self.assertEqual(stringing.overload_check("Inverter 1", 0.6).level, "ok")      # green under 1 % now

    def test_a_change_checks_again_only_the_inputs_it_touched(self):
        from unittest import mock

        from meridiana.energy import plant
        plant._PLANS.clear()
        runs = [{"inverter": 1, "mppt": 1, "modules": [f"s1/0:{s}" for s in range(8)]},
                {"inverter": 1, "mppt": 2, "modules": [f"s1/1:{s}" for s in range(8)]}]
        with mock.patch.object(stringing, "plan", wraps=stringing.plan) as planned:
            self.plant_of(grid(3, 8), runs)
            self.assertEqual(planned.call_count, 2)                     # one for each input
            again = [dict(runs[0]), dict(runs[1], modules=runs[1]["modules"][:7])]
            out = self.plant_of(grid(3, 8), again)
            self.assertEqual(planned.call_count, 3)                     # only the input touched
        self.assertIs(out.strings[0].plan, out.inputs[(1, 1)].plan)
        self.assertEqual(out.strings[1].plan.n_series, 7)

    def test_a_string_by_hand_survives_a_row_moved_and_is_said_lost_when_the_row_goes(self):
        from meridiana import checks
        runs = [{"inverter": 1, "mppt": 1, "modules": ["s1/1:0", "s1/1:1", "s1/1:2"]}]
        here = self.plant_of(grid(3, 8), runs)
        moved = self.plant_of(grid(3, 8, x0=5.0), runs)                  # the same keys, other places
        self.assertEqual([k for _sf, k, _c in moved.strings[0].modules], ["1:0", "1:1", "1:2"])
        self.assertEqual(moved.strings[0].modules[0][2][0] - here.strings[0].modules[0][2][0], 5.0)
        self.assertFalse(moved.lost)
        self.assertEqual(len(moved.left), 24 - 3)
        gone = self.plant_of(grid(1, 8), runs)                            # rows 1 and 2 are no longer laid
        self.assertEqual(gone.strings[0].modules, [])
        self.assertEqual(gone.lost, [("1.1.1", ["s1/1:0", "s1/1:1", "s1/1:2"])])
        self.assertEqual(gone.strings[0].state, "fail")
        said = [i for i in checks.plant_items(gone) if "no longer laid" in i.text]
        self.assertEqual((len(said), said[0].fix), (1, ()))           # the designer's to change: no rewrite (R114)


class AutomaticErrors(unittest.TestCase):
    """Errors reproduced before R187: a proposal must respect every unit and every input, not only the first."""

    def group(self, placed):
        from meridiana.energy import plant
        return plant.Group("s1.0", "s1", "s1", module(), placed)

    def test_mixed_inverter_models_do_not_put_a_long_string_on_a_narrow_input(self):
        from meridiana.energy import plant
        wide = inverter_rec(model="WIDE", mppt_count=1, dc_current_max_per_mppt_a=[60],
                            dc_isc_max_per_mppt_a=[80])
        narrow = inverter_rec(model="NARROW", mppt_count=1, mppt_voltage_max_v=500,
                              dc_current_max_per_mppt_a=[60], dc_isc_max_per_mppt_a=[80])
        p = plant_project([(wide, 1), (narrow, 1)], {"auto": True, "strategy": "serpentine"})
        out = plant.build(p, groups=[self.group(grid(4, 24))])
        self.assertFalse(out.left)
        self.assertEqual(len(out.strings), 8)
        self.assertTrue(all(s.state == "ok" for s in out.strings),
                        [(s.label, len(s.modules), s.why) for s in out.strings])

    def test_an_explicit_input_never_receives_more_strings_than_its_current_allows(self):
        from meridiana.energy import plant
        one = inverter_rec(mppt_count=1, dc_current_max_per_mppt_a=[16], dc_isc_max_per_mppt_a=[20])
        p = plant_project([(one, 1)], {"auto": True, "strategy": "serpentine", "n_series": 12})
        out = plant.build(p, groups=[plant.Group("s1.0", "s1", "s1", module(), grid(3, 12), (1, 1))])
        self.assertEqual(len(out.strings), 1)
        self.assertEqual(len(out.left), 24)
        self.assertTrue(all(s.state == "ok" for s in out.strings))

    def test_parallel_capacity_uses_operating_and_short_circuit_current(self):
        inv = inverter(mppt_count=1, dc_current_max_per_mppt_a=[26], dc_isc_max_per_mppt_a=[40])
        self.assertEqual(stringing.strings_allowed(module(), inv, 0), 1)


class OnlyWhenAsked(unittest.TestCase):
    """R114 and R118 (Daniel, 25/10/2026): the strings are the designer's; Meridiana proposes them only when asked
    (`propose`), completes them around his (`keep`), and nothing else makes or moves them: an inverter added leaves
    them where they are and its inputs free."""

    def project(self, entries, runs=None):
        return plant_project(entries, {"strategy": "rows", "n_series": 8, "runs": runs or []})

    def group(self, placed):
        from meridiana.energy import plant
        return plant.Group("s1.0", "s1", "s1", module(), placed)

    def test_without_strings_of_the_designer_nothing_is_laid_and_every_module_is_left(self):
        from meridiana import checks
        from meridiana.energy import plant
        p = self.project([(inverter_rec(), 1)])
        out = plant.build(p, groups=[self.group(grid(3, 8))])
        self.assertFalse(out.auto)
        self.assertEqual((out.strings, len(out.left)), ([], 24))
        left = next(i for i in checks.plant_items(out) if "in no string" in i.text)
        self.assertEqual(left.fix, ("command", "strings_complete"))               # «Complete the strings», asked
        self.assertIn("produces nothing", left.detail)

    def test_an_inverter_added_makes_no_string_and_the_strings_stay_on_their_inverters(self):
        from meridiana.energy import plant
        a, b = inverter_rec(model="A"), inverter_rec(model="B")
        runs = [{"inverter": 1, "mppt": 1, "modules": [f"s1/0:{s}" for s in range(8)]},
                {"inverter": 2, "mppt": 2, "modules": [f"s1/1:{s}" for s in range(8)]}]
        p = self.project([(a, 1), (b, 1)], runs)
        before = plant.unit_keys(p.energy)
        self.assertEqual(before, [(0, 0), (1, 0)])
        p.energy["inverters"][0]["count"] = 2                                    # one more A: B is unit 3 now
        after = plant.unit_keys(p.energy)
        moved = plant.renumber(runs, before, after, {0: 0, 1: 1})
        self.assertEqual([(r["inverter"], r["mppt"]) for r in moved], [(1, 1), (3, 2)])
        p.energy["strings"]["runs"] = moved
        out = plant.build(p, groups=[self.group(grid(3, 8))])
        self.assertEqual([(s.inverter, s.mppt, len(s.modules)) for s in out.strings], [(1, 1, 8), (3, 2, 8)])
        self.assertFalse(any(slot.strings for (n, _k), slot in out.inputs.items() if n == 2))   # the new one free
        self.assertEqual(len(out.left), 8)
        # an entry taken out: its strings are on no inverter (said by the checks), the others follow
        gone = plant.renumber(moved, after, [(0, 0)], {1: 0})
        self.assertEqual([(r["inverter"], r["mppt"]) for r in gone], [(0, 0), (1, 2)])
        self.assertEqual(plant.renumber(runs, [], after, {}), runs)              # sized by itself before: as it was

    def test_propose_lays_the_strategy_once_and_complete_keeps_the_designers_strings(self):
        from meridiana.energy import plant
        two = inverter_rec(dc_isc_max_per_mppt_a=[80, 80], dc_current_max_per_mppt_a=[60, 60])
        p = self.project([(two, 1)])
        groups = [self.group(grid(3, 8))]
        runs = plant.propose(p, groups=groups)
        self.assertEqual(len(runs), 3)                                           # rows of 8: three strings
        self.assertEqual(sorted(k for r in runs for k in r["modules"]), sorted(f"s1/{pm.key}" for pm in grid(3, 8)))
        self.assertEqual(p.energy["strings"]["runs"], [])                        # proposed, not written: the window
        mine = [{"inverter": 1, "mppt": 2, "modules": ["s1/1:3", "s1/1:2", "s1/0:2"]}]
        completed = plant.propose(p, groups=groups, keep=mine)
        self.assertEqual(completed[0], mine[0])                                  # his string first, as it was
        others = [k for r in completed[1:] for k in r["modules"]]
        self.assertFalse(set(others) & set(mine[0]["modules"]))                  # no module twice
        self.assertEqual(completed[1]["mppt"], 1)                                # the input without strings first
        self.assertEqual(plant.propose(p, groups=groups, strategy="serpentine")[0]["modules"][:2],
                         ["s1/0:0", "s1/0:1"])

    def test_complete_without_a_free_input_uses_the_room_left_and_proposes_nothing_beyond_it(self):
        from meridiana.energy import plant
        one = inverter_rec(mppt_count=1, dc_isc_max_per_mppt_a=[20], dc_current_max_per_mppt_a=[16])  # 1 string
        p = self.project([(one, 1)])
        groups = [self.group(grid(2, 8))]
        mine = [{"inverter": 1, "mppt": 1, "modules": [f"s1/0:{s}" for s in range(8)]}]
        self.assertEqual(plant.propose(p, groups=groups, keep=mine), mine)       # the input is full: nothing more
        wide = inverter_rec(mppt_count=1, dc_isc_max_per_mppt_a=[60], dc_current_max_per_mppt_a=[60])
        p = self.project([(wide, 1)])
        completed = plant.propose(p, groups=groups, keep=mine)
        self.assertEqual(len(completed), 2)
        self.assertEqual((completed[1]["inverter"], completed[1]["mppt"]), (1, 1))

    def test_a_string_deleted_or_drawn_again_takes_its_modules_from_the_others(self):
        from meridiana.energy import plant
        runs = [{"inverter": 1, "mppt": 1, "modules": ["s1/0:0", "s1/0:1"]},
                {"inverter": 1, "mppt": 2, "modules": ["s1/0:2", "s1/0:3"]}]
        self.assertEqual(plant.delete_run(runs, 0), [runs[1]])
        again, robbed = plant.set_run(runs, 0, ["s1/0:1", "s1/0:2", "s1/0:4"])
        self.assertEqual((again[0]["modules"], again[1]["modules"], robbed), (["s1/0:1", "s1/0:2", "s1/0:4"],
                                                                             ["s1/0:3"], [1]))
        self.assertEqual(runs[0]["modules"], ["s1/0:0", "s1/0:1"])               # the runs given are not touched


if __name__ == "__main__":
    unittest.main()
