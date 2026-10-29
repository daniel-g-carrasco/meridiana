"""Power optimizers (task 22, energy/optimizers.py and energy/plant.py): SolarEdge's rules of the module on its
optimizer, of the strings and of the inverter, each from its document, the examples of SolarEdge's own notes, and the
strings Meridiana proposes on an inverter at a fixed string voltage."""

import math
import unittest

import _setup  # noqa: F401

from meridiana import catalog
from meridiana.energy import optimizers, plant
from meridiana.energy.components import ModuleSpec


def module(**k) -> ModuleSpec:
    rec = {"manufacturer": "Acme", "model": "450", "pmax": 450, "vmp": 33.6, "imp": 13.4, "voc": 40.1, "isc": 14.1,
           "beta_voc": -0.25, "alpha_isc": 0.046, "gamma_pmax": -0.30, "cells": 108, "length": 1.762, "width": 1.134}
    rec.update(k)
    return ModuleSpec.from_record(rec)


def inverter(model: str) -> dict:
    return next(r for r in catalog.search("inverters", manufacturer="SolarEdge", limit=None) if r["model"] == model)


def optimizer_rec(model: str) -> dict:
    return next(r for r in catalog.search("optimizers", manufacturer="SolarEdge", limit=None) if r["model"] == model)


def rules(opt: str, inv: str):
    return optimizers.rules_for(optimizers.Optimizer.from_record(optimizer_rec(opt)),
                                optimizers.fixed_voltage(inverter(inv)))


def grid(rows: int, per_row: int, azimuth: float = 0.0, x0: float = 0.0) -> list:
    from meridiana import layout
    out = []
    for r in range(rows):
        for s in range(per_row):
            x, y = x0 + 1.2 * s, 3.0 * r
            out.append(layout.PlacedModule(r, s, 0, [(x - 0.5, y - 1), (x + 0.5, y - 1), (x + 0.5, y + 1),
                                                     (x - 0.5, y + 1)], (x, y), 1.0, 15.0, azimuth))
    return out


def project(model: str, count: int = 1, optimizer: str | None = None, per: int | None = None,
            strings: dict | None = None):
    from meridiana import model as m
    p = m.Project(name="Prova")
    entry = {"record": inverter(model), "count": count, "name": ""}
    if optimizer:
        entry["optimizer"] = optimizer_rec(optimizer)
    if per:
        entry["per_optimizer"] = per
    p.energy = {"inverters": [entry]}
    # without strings of the designer, Meridiana's proposal (as a project of before format 14 had it, or as
    # «Propose the strings» writes it down)
    p.energy["strings"] = strings if strings is not None else {"auto": True}
    return p


def group(placed, sfid="s1", mod=None):
    return plant.Group(f"{sfid}.0", sfid, sfid, mod or module(), placed)


class TheInverter(unittest.TestCase):
    """An inverter at a fixed string voltage as the rules read it, from the catalogue's records."""

    def test_the_solaredge_inverters_of_the_catalogue_are_at_a_fixed_string_voltage(self):
        found = {r["model"]: optimizers.fixed_voltage(r) for r in catalog.search("inverters", manufacturer="SolarEdge",
                                                                                limit=None)}
        self.assertTrue(all(v is not None for v in found.values()))
        self.assertEqual((found["SE5000H"].grid, found["SE5000H"].v_string), ("single_phase", 380.0))
        self.assertEqual((found["SE10K"].grid, found["SE10K"].v_string, found["SE10K"].p_dc_max),
                         ("three_phase_400", 750.0, 15000.0))
        self.assertEqual((found["SE100K"].units, found["SE100K"].unit_model), (3, "SE33.3K"))
        self.assertTrue(found["SE8000H (Home Hub)"].home_hub)
        self.assertIsNone(optimizers.fixed_voltage(next(r for r in catalog.search("inverters", limit=None)
                                                        if r["manufacturer"] == "Huawei")))

    def test_a_record_of_before_task_22_is_read_by_inference_and_says_so(self):
        old = {k: v for k, v in inverter("SE50K").items()
               if k not in ("dc_architecture", "string_voltage_v", "optimizer_grid", "synergy_units",
                            "optimizer_unit_model", "dc_input_pairs")}
        fv = optimizers.fixed_voltage(old)
        self.assertEqual((fv.grid, fv.units, fv.unit_model, fv.v_string), ("three_phase_400", 2, "SE25K", 750.0))
        self.assertEqual(set(fv.inferred), {"grid", "units", "unit model", "voltage"})


class TheTables(unittest.TestCase):
    """The rules of the strings by optimizer and inverter, as SolarEdge's tables print them (DS-000091-IT p. 3,
    DS-000105-IT p. 3, DS-000205-EU p. 3, DS-000047-ITA p. 2, DS-000012-ENG p. 3)."""

    def test_the_residential_s_series_single_phase(self):
        r, _why = rules("S440", "SE5000H")
        self.assertEqual((r.opt_min, r.opt_max, r.p_cont), (8, 25, 5700.0))
        self.assertEqual((r.p_one, r.p_many), (10000.0, 10000.0))   # AC within 5700 W: the inverter's maximum DC power
        self.assertIn("DS-000091-IT", r.source)
        r, _why = rules("S500B", "SE6000H")
        self.assertEqual((r.opt_min, r.p_one, r.p_many), (6, 6000.0, 6000.0))        # AC above 5700 W: 6000 W
        r, _why = rules("S500", "SE8000H (Home Hub)")
        self.assertEqual((r.p_one, r.p_many, r.many), (6000.0, 6800.0, 2))   # 6800 W with 8000 W and two strings

    def test_the_residential_s_series_three_phase(self):
        r, _why = rules("S500", "SE10K")
        self.assertEqual((r.opt_min, r.opt_max, r.p_cont, r.p_one), (16, 50, 11250.0, 15000.0))
        r, _why = rules("S650B", "SE16K")
        self.assertEqual((r.opt_min, r.p_one, r.diff_w), (14, 13500.0, 2000.0))
        self.assertEqual(optimizers.connected_limit(r, 2, 1500.0)[0], 13500.0)
        limit, why = optimizers.connected_limit(r, 2, 2500.0)
        self.assertEqual(limit, 11250.0)                   # more than 2000 W apart: the continuous power each
        self.assertTrue(why)
        self.assertEqual(optimizers.connected_limit(r, 1, 9999.0)[0], 13500.0)

    def test_the_commercial_s_series_by_inverter_and_number_of_strings(self):
        r, _why = rules("S1000", "SE50K")                   # a Synergy unit of 25 kW: the SE25K column
        self.assertEqual((r.opt_min, r.mod_min, r.opt_max, r.mod_max, r.p_cont), (14, 27, 30, 60, 13500.0))
        self.assertEqual((optimizers.connected_limit(r, 1, 0)[0], optimizers.connected_limit(r, 2, 0)[0]),
                         (15750.0, 18500.0))
        self.assertEqual((r.diff_opt, r.min_dc, r.diff_w), (5, 11000.0, 0.0))
        r, _why = rules("S1000", "SE100K")                  # SE33.3K: 15750 W up to two strings, 18500 W from three
        self.assertEqual([optimizers.connected_limit(r, n, 0)[0] for n in (1, 2, 3)], [15750.0, 15750.0, 18500.0])
        r, _why = rules("S1400", "SE90K")
        self.assertEqual((r.opt_min, r.mod_min, r.p_cont, r.p_one, r.p_many), (15, 29, 20400.0, 22650.0, 30400.0))

    def test_the_s1200_on_a_33_kw_unit_needs_850_v_and_it_is_said(self):
        r, _why = rules("S1200", "SE100K")
        self.assertEqual([w[0] for w in r.warnings], ["toggle"])
        self.assertIn("note 11", r.warnings[0][3])
        r, _why = rules("S1200", "SE50K")
        self.assertEqual(r.warnings, ())

    def test_an_optimizer_the_tables_do_not_put_with_the_inverter_has_no_rules_and_a_reason(self):
        r, why = rules("S1200", "SE10K")
        self.assertIsNone(r)
        self.assertIn("S1200", why)
        r, why = rules("P1100", "SE16K")                    # «SE25K & larger»
        self.assertIsNone(r)
        r, why = optimizers.rules_for(optimizers.Optimizer.from_record(
            next(x for x in catalog.search("optimizers", limit=None) if x["manufacturer"] == "Tigo")),
            optimizers.fixed_voltage(inverter("SE5000H")))
        self.assertIsNone(r)

    def test_the_p_series_of_before(self):
        r, _why = rules("P401", "SE5000H")
        self.assertEqual((r.opt_min, r.opt_max, r.p_cont), (8, 25, 5700.0))
        self.assertIn("DS-000047-ITA", r.source)
        r, _why = rules("P505", "SE16K")
        self.assertEqual((r.opt_min, r.p_one, r.diff_w), (14, 13500.0, 2000.0))
        r, _why = rules("P950", "SE16K")
        self.assertEqual((r.opt_min, r.mod_min, r.p_one, r.p_many, r.diff_w), (14, 27, 15750.0, 18500.0, 2000.0))


class TheModule(unittest.TestCase):
    """The module on its optimizer (DS p. 2; Power Optimizer Compatibility with PV Modules v1.0, p. 2-3)."""

    def checks(self, mod, opt, per=1, t_min=-10.0, inv="SE5000H"):
        o = optimizers.Optimizer.from_record(optimizer_rec(opt))
        return {c.key: c for c in optimizers.module_checks(mod, o, per, t_min,
                                                           optimizers.fixed_voltage(inverter(inv)))}

    def test_a_module_within_every_limit(self):
        c = self.checks(module(), "S500")
        self.assertEqual({k: v.level for k, v in c.items()},
                         {"opt_power": "ok", "opt_voc": "ok", "opt_isc": "ok", "opt_imp": "ok"})
        self.assertTrue(all(v.source for v in c.values()))

    def test_a_module_too_strong_for_the_optimizer_fails(self):
        self.assertEqual(self.checks(module(pmax=600), "S500")["opt_power"].level, "fail")     # 600 W on 550 W
        self.assertEqual(self.checks(module(pmax=550), "S500")["opt_power"].level, "ok")       # exactly the rating

    def test_the_voc_on_the_coldest_morning(self):
        # 52 V at STC, -0.30 %/K, -10 °C: 52 x 1.105 = 57.5 V within 60 V; at -25 °C 59.8 V; a 56 V module fails
        self.assertEqual(self.checks(module(voc=52.0, beta_voc=-0.30), "S440")["opt_voc"].level, "ok")
        self.assertEqual(self.checks(module(voc=56.0, beta_voc=-0.30), "S440")["opt_voc"].level, "fail")

    def test_the_isc_with_the_home_hub_takes_16_5_a(self):
        self.assertEqual(self.checks(module(isc=16.0), "S500")["opt_isc"].level, "fail")
        self.assertEqual(self.checks(module(isc=16.0), "S500", inv="SE6000H (Home Hub)")["opt_isc"].level, "ok")

    def test_an_imp_above_the_continuous_input_current_is_a_loss_not_a_danger(self):
        c = self.checks(module(imp=15.6, isc=16.0, pmax=500), "S1200", per=2, inv="SE50K")
        self.assertEqual((c["opt_imp"].level, c["opt_isc"].level), ("warn", "ok"))

    def test_the_example_of_the_bifacial_note_two_modules_in_series(self):
        # Bi-facial Modules v1.5, p. 2: 2 x 400 W = 800 W within 850 W, 2 x 49.7 V within 125 V, 10.22 A within the
        # input's current; at the lowest temperature the Voc is checked too (2 x 49.7 x 1.0945 = 108.8 V)
        c = self.checks(module(pmax=400, voc=49.7, isc=10.22, imp=9.7, vmp=41.3, beta_voc=-0.27), "P850", per=2,
                        inv="SE16K")
        self.assertEqual({k: v.level for k, v in c.items()}, {"opt_power": "ok", "opt_voc": "ok", "opt_isc": "ok"})
        self.assertIn("800", c["opt_power"].detail)


class TheSingleStringNote(unittest.TestCase):
    """The examples of SolarEdge's Single String Design Guidelines v1.1 (08/2026), p. 2-3, through the plant."""

    def test_24_modules_of_415_w_on_an_se5000h_go_in_one_string(self):
        p = project("SE5000H", optimizer="S440")
        out = plant.build(p, groups=[group(grid(2, 12), mod=module(pmax=415))])
        self.assertEqual([len(s.modules) for s in out.strings], [24])
        (s,) = out.strings
        self.assertAlmostEqual(s.plan.power_w, 9960.0)
        self.assertEqual(s.state, "ok")                     # 9.96 kW within the 10 kW of 200 % oversizing
        levels = {c.key: c.level for c in s.plan.checks}
        self.assertEqual(levels["opt_continuous"], "info")  # above 5.7 kW the peaks are cut, within the 5 kW of AC

    def test_27_modules_of_370_w_take_two_strings(self):
        p = project("SE5000H", optimizer="S440")
        out = plant.build(p, groups=[group(grid(3, 9), mod=module(pmax=370))])
        self.assertEqual(sorted(len(s.modules) for s in out.strings), [13, 14])     # 27 is beyond the 25 allowed
        self.assertTrue(all(s.state == "ok" for s in out.strings))
        by_hand = {"auto": False, "runs": [{"inverter": 1, "mppt": 1, "modules": [s for s in out.strings[0].keys
                                                                                   + out.strings[1].keys]}]}
        out = plant.build(project("SE5000H", optimizer="S440", strings=by_hand),
                          groups=[group(grid(3, 9), mod=module(pmax=370))])
        self.assertEqual(out.strings[0].state, "fail")
        self.assertIn("opt_count", [c.key for c in out.strings[0].plan.checks if c.level == "fail"])


class TheProposal(unittest.TestCase):
    """The strings Meridiana proposes with optimizers: as few as the limits allow, alike, every module in one."""

    def test_an_inverter_above_the_continuous_power_gets_strings_within_it(self):
        out = plant.build(project("SE6000H", optimizer="S500"), groups=[group(grid(2, 10))])
        self.assertEqual([len(s.modules) for s in out.strings], [10, 10])          # 9 kW in two of 4.5 kW
        self.assertFalse(out.left)
        self.assertTrue(all(s.state == "ok" for s in out.strings))

    def test_small_pitches_with_different_orientations_are_left_for_the_designer(self):
        east = group(grid(1, 6, azimuth=-90.0), "est")
        west = group(grid(1, 6, azimuth=90.0, x0=20.0), "ovest")
        out = plant.build(project("SE3000H", optimizer="S440"), groups=[east, west])
        self.assertEqual(out.strings, [])
        self.assertEqual(len(out.left), 12)  # neither orientation meets the 8-optimizer minimum

    def test_a_synergy_inverter_spreads_alike_strings_over_its_units(self):
        out = plant.build(project("SE50K", optimizer="S1000", per=2), groups=[group(grid(10, 20))])
        sizes = [len(s.modules) for s in out.strings]
        self.assertEqual(sum(sizes), 200)
        self.assertTrue(all(28 <= n <= 30 for n in sizes), sizes)                   # within 13.5 kW each
        per_unit = [len(out.inputs[(1, k)].strings) for k in (1, 2)]
        self.assertEqual(sorted(per_unit), [3, 4])
        self.assertTrue(all(s.state == "ok" for s in out.strings), [s.why for s in out.strings])
        self.assertEqual(out.strings[0].plan.optimizers, math.ceil(sizes[0] / 2))

    def test_the_optimizers_are_proposed_when_none_is_chosen_and_it_is_said(self):
        from meridiana import checks
        out = plant.build(project("SE5000H"), groups=[group(grid(2, 10))])
        self.assertTrue(out.units[0].choice.suggested)
        self.assertEqual(out.units[0].choice.optimizer.model, "S440")
        items = checks.plant_items(out)
        self.assertTrue(any(it.level == "info" and "S440" in it.text for it in items))
        self.assertTrue(any(it.level == "ok" and "DS-000091-IT" in it.source for it in items))

    def test_a_string_too_short_by_hand_fails_on_solaredges_table_with_its_source(self):
        from meridiana import checks
        keys = [f"s1/{pm.key}" for pm in grid(1, 6)]
        by_hand = {"auto": False, "runs": [{"inverter": 1, "mppt": 1, "modules": keys}]}
        out = plant.build(project("SE5000H", optimizer="S500", strings=by_hand), groups=[group(grid(1, 6))])
        self.assertEqual(out.strings[0].state, "fail")
        item = next(it for it in checks.plant_items(out) if it.level == "fail")
        self.assertIn("DS-000091-IT", item.source)
        self.assertTrue(item.detail)
        self.assertIn("6", plant.voltages(out.strings[0]))

    def test_strings_of_different_lengths_side_by_side_are_fine(self):
        placed = grid(2, 12)
        keys = [f"s1/{pm.key}" for pm in placed]
        by_hand = {"auto": False, "runs": [{"inverter": 1, "mppt": 1, "modules": keys[:10]},
                                           {"inverter": 1, "mppt": 1, "modules": keys[10:]}]}
        out = plant.build(project("SE5000H", optimizer="S440", strings=by_hand), groups=[group(placed)])
        self.assertEqual([s.state for s in out.strings], ["ok", "ok"])

    def test_the_inverter_s_maximum_dc_power_and_the_home_hub_s_one_to_one(self):
        out = plant.build(project("SE10K", optimizer="S500"), groups=[group(grid(3, 12))])   # 36 x 450 = 16.2 kW
        failed = [c.key for c in out.checks[1] if c.level == "fail"]
        self.assertEqual(failed, ["opt_dc_max"])
        out = plant.build(project("SE6000H (Home Hub)", optimizer="S500", per=1), groups=[group(grid(1, 10))])
        self.assertFalse([c for c in out.checks[1] if c.level == "fail"])

    def test_a_module_no_optimizer_takes_lays_no_string_and_says_why(self):
        big = module(pmax=720, voc=50.0, isc=18.5, imp=17.4, vmp=41.4)
        out = plant.build(project("SE5000H"), groups=[group(grid(1, 10), mod=big)])
        self.assertIsNone(out.units[0].choice)
        self.assertFalse(out.strings)
        self.assertEqual(len(out.left), 10)
        self.assertTrue(out.notes)



class TheYear(unittest.TestCase):
    """The power optimizers in the year (energy/simulate.py): no mismatch among the modules alone on one, the
    optimizer's weighted efficiency as a step of the chain, the string's continuous power, the DC wiring at the
    inverter's fixed voltage, the shade's electrical effect optimizer by optimizer."""

    @classmethod
    def setUpClass(cls):
        from _fixtures import clear_sky_meteo
        cls.meteo = clear_sky_meteo()

    def array(self, n=20, placed=None, obstacles=None):
        from meridiana.energy.simulate import ArraySpec
        a = ArraySpec("s1.0", "Sud", 30.0, 0.0, n, module(), "open")
        if placed is not None:
            a.placed, a.obstacles = placed, obstacles or []
        return a

    def optimizers(self, share=1.0, single=1.0, strings=None):
        from meridiana.energy.pedigree import Source
        from meridiana.energy.simulate import ArrayOptimizers, Optimizers
        return Optimizers({"s1.0": ArrayOptimizers(share, single, 0.986, 380.0, "SolarEdge S500",
                                                   Source("data", "datasheet of SolarEdge S500", optimizers.RES))},
                          strings or [])

    def test_the_optimizers_take_the_mismatch_away_and_convert_with_their_efficiency(self):
        from meridiana.energy.simulate import simulate
        plain = simulate(self.meteo, [self.array()])
        opt = simulate(self.meteo, [self.array()], optimizers=self.optimizers())
        steps = {c.key: c for c in opt.chain}
        self.assertAlmostEqual(steps["mismatch"].change, 0.0, places=9)
        self.assertAlmostEqual(steps["optimizers"].change, -1.4, places=6)          # 98.6 % weighted
        self.assertNotIn("optimizers", [c.key for c in plain.chain])
        self.assertNotIn("string_limit", [c.key for c in opt.chain])
        mm = next(c for c in plain.chain if c.key == "mismatch").change
        self.assertAlmostEqual(mm, -1.0, places=6)
        step = opt.record.find("s1.0.optimizers")
        self.assertIsNotNone(step)
        self.assertIn("DS-000091-IT", step.reference + "".join(q.source.ref for q in step.inputs if q.source))
        self.assertEqual(opt.arrays[0]["optimizers"]["mismatch"], 0.0)
        # two modules on an optimizer keep the mismatch between them
        two = simulate(self.meteo, [self.array()], optimizers=self.optimizers(single=0.0))
        self.assertAlmostEqual(next(c for c in two.chain if c.key == "mismatch").change, -1.0, places=6)

    def test_a_string_beyond_its_continuous_power_is_cut_at_the_peaks(self):
        from meridiana.energy.simulate import simulate
        free = simulate(self.meteo, [self.array()], optimizers=self.optimizers(strings=[({"s1.0": 20}, 99000.0)]))
        cut = simulate(self.meteo, [self.array()], optimizers=self.optimizers(strings=[({"s1.0": 20}, 5700.0)]))
        self.assertNotIn("string_limit", [c.key for c in free.chain])
        step = next(c for c in cut.chain if c.key == "string_limit")
        self.assertLess(step.change, 0.0)                    # 9 kW of modules on a string that carries 5.7 kW
        self.assertLess(cut.energy_kwh, free.energy_kwh)
        self.assertLessEqual(float(cut.hourly.p_dc.max()), 5700.0 + 1e-6)
        self.assertTrue(any("optimizers" in n for n in cut.notes))

    def test_the_dc_wiring_goes_with_the_power_at_the_fixed_voltage(self):
        import numpy as np

        from meridiana.energy.simulate import Losses, simulate
        opt = self.optimizers()
        a, b = (simulate(self.meteo, [self.array()], losses=Losses(dc_wiring=w), optimizers=opt) for w in (1.5, 0.0))
        wiring = 1.0 - a.hourly.p_dc.to_numpy().sum() / b.hourly.p_dc.to_numpy().sum()
        p = b.hourly.p_dc.to_numpy()                          # the power before the wiring, at the fixed voltage
        expected = (0.015 * 9000.0 * (p / 9000.0) ** 2).sum() / p.sum()
        self.assertAlmostEqual(wiring, expected, places=3)
        self.assertTrue(np.all(a.hourly.p_dc.to_numpy() <= b.hourly.p_dc.to_numpy() + 1e-9))

    def test_the_shade_costs_less_optimizer_by_optimizer_than_string_by_string(self):
        from meridiana import layout
        from meridiana.energy import nearshade
        from meridiana.energy.simulate import simulate
        roof = [(0.0, 0.0), (14.0, 0.0), (14.0, 8.0), (0.0, 8.0)]
        placed = layout.compute(roof, params=layout.Params(tilt=30.0, pitch_mode="value", pitch=4.0), lat=45.5,
                                lon=9.0).modules
        chimney = nearshade.prism([(6.0, -1.5), (7.0, -1.5), (7.0, -0.5), (6.0, -0.5)], 0.0, 3.0, "camino")
        rows: dict = {}
        for pm in placed:
            rows.setdefault(pm.row, []).append(pm.key)
        by_string = simulate(self.meteo, [self.array(len(placed), placed, chimney)],
                             strings={"s1.0": list(rows.values())})
        by_module = simulate(self.meteo, [self.array(len(placed), placed, chimney)],
                             strings={"s1.0": [[pm.key] for pm in placed]})
        self.assertGreater(by_string.arrays[0]["electrical_shading"], 0.0)
        self.assertLess(by_module.arrays[0]["electrical_shading"], by_string.arrays[0]["electrical_shading"])

    def test_every_formula_of_the_optimizers_can_be_drawn(self):
        from matplotlib.mathtext import MathTextParser

        from meridiana.energy.simulate import simulate
        parser = MathTextParser("path")
        year = simulate(self.meteo, [self.array()], optimizers=self.optimizers(strings=[({"s1.0": 20}, 5700.0)]))
        out = plant.build(project("SE5000H", optimizer="S440"), groups=[group(grid(2, 12))])
        steps = [year.record.find("s1.0.optimizers")] + out.strings[0].plan.record.steps
        self.assertEqual(len(steps), 3)
        for step in steps:
            parser.parse(f"${step.formula}$")
            for q in step.inputs + ([step.result] if step.result else []):
                if q.symbol:
                    parser.parse(f"${q.symbol}$")

    def test_the_optimizers_applied_downstream_give_what_simulate_gives_with_them(self):
        import dataclasses

        from meridiana.energy.simulate import simulate, with_strings
        opt = self.optimizers(strings=[({"s1.0": 20}, 5700.0)])
        whole = simulate(self.meteo, [self.array()], optimizers=opt)
        again = with_strings(simulate(self.meteo, [self.array()]), None, opt)

        def plain(x):
            if dataclasses.is_dataclass(x) and not isinstance(x, type):
                return {f.name: plain(getattr(x, f.name)) for f in dataclasses.fields(x) if f.name != "parts"}
            if hasattr(x, "to_numpy"):
                return x.to_numpy().tolist()
            if isinstance(x, dict):
                return {k: plain(v) for k, v in x.items()}
            if isinstance(x, (list, tuple)):
                return [plain(v) for v in x]
            return x
        self.assertEqual(plain(again), plain(whole))


class ThePipeline(unittest.TestCase):
    """A project with a SolarEdge inverter through the whole pipeline: the optimizers are proposed, the year has their
    step and the strings' limit, the checks come from SolarEdge's tables."""

    def test_a_solaredge_project_gets_its_optimizers_in_the_year(self):
        import tempfile
        from pathlib import Path
        from unittest import mock

        from _fixtures import clear_sky_meteo, write_cache

        from meridiana import checks, jobs, model
        from meridiana.energy import pipeline
        cache = Path(tempfile.mkdtemp())
        write_cache(clear_sky_meteo(45.5226, 9.03), cache)
        p = model.Project(name="Prova")
        p.site = model.Site(lat=45.5226, lon=9.0300, address="Rho (MI)")
        p.buildings.append(model.Building(id="b1", name="Casa", footprint=[[0, 0], [20, 0], [20, 8], [0, 8]],
                                          height=6.0))
        p.subfields.append(model.SubField(id="s1", name="Sud", ring=[[1, 1], [19, 1], [19, 7], [1, 7]],
                                          building="b1", params={"tilt": 15.0}, filled=True))
        p.energy["inverters"] = [{"record": inverter("SE6000H"), "count": 1, "name": ""}]
        results, _keys, _laid = jobs.layout_of(p)
        from meridiana.energy import plant as plant_model
        p.energy["strings"] = plant_model.touched({}, plant_model.propose(p, results))     # «Propose the strings»
        with mock.patch.object(pipeline, "with_network", wraps=pipeline.with_network) as again:
            out = pipeline.compute(p, results, cache, fetch=False)
        self.assertTrue(out.plant.optimized)
        self.assertTrue(out.plant.strings)
        self.assertEqual(again.call_count, 1)
        self.assertIsNotNone(again.call_args[0][2])
        self.assertIn("optimizers", [c.key for c in out.sim.chain])
        self.assertIsNotNone(out.sim.record.find("s1.0.optimizers"))
        items = checks.plant_items(out.plant)
        self.assertTrue(any("DS-000091-IT" in it.source for it in items))
        self.assertTrue(all(s.plan is not None and s.plan.continuous_w == 5700.0 for s in out.plant.strings))


class TheAssistant(unittest.TestCase):
    def test_meridio_reads_the_strings_of_optimizers_with_their_limits_and_sources(self):
        import json

        from meridiana.assistant import tools
        out = plant.build(project("SE5000H", optimizer="S440"), groups=[group(grid(2, 12), mod=module(pmax=415))])

        class Host:
            def plant(self):
                return out

            def energy(self):
                return {}
        answer = json.loads(tools.read_results(Host(), tools.State(), "strings").content)
        self.assertEqual(answer["strings"], 1)
        row = answer["inputs"][0]
        self.assertEqual((row["optimizer"], row["optimizers_in_a_string"], row["string_power_carried_w"]),
                         ("SolarEdge S440", 24, 5700.0))
        self.assertTrue(all(c["source"] for c in row["checks"]))


if __name__ == "__main__":
    unittest.main()


class OrientationAndTopology(unittest.TestCase):
    def test_small_fields_with_the_same_facing_can_still_form_one_valid_string(self):
        out = plant.build(project("SE3000H", optimizer="S440"),
                          groups=[group(grid(1, 6), "a"), group(grid(1, 6, x0=20), "b")])
        self.assertEqual([len(s.modules) for s in out.strings], [12])
        self.assertEqual(out.strings[0].state, "ok")

    def test_manual_multifacing_string_warns_but_a_mixed_optimizer_pair_fails(self):
        from meridiana import checks
        east, west = group(grid(1, 14, azimuth=-90), "east"), group(grid(1, 14, azimuth=90), "west")
        a = [f"east/{pm.key}" for pm in east.placed]
        b = [f"west/{pm.key}" for pm in west.placed]
        for keys, expected in ((a+b, "check"), ([a[0],b[0]]+a[1:]+b[1:], "fail")):
            p = project("SE50K", optimizer="S1000", per=2,
                        strings={"runs": [{"inverter":1,"mppt":1,"modules":keys}]})
            out = plant.build(p, groups=[east, west])
            self.assertEqual(out.strings[0].state, expected)
            self.assertIn("orientation", out.strings[0].why)
            self.assertTrue(any("orientation" in item.text or "orientation" in item.detail
                                for item in checks.plant_items(out)))

    def test_p800p_parallel_inputs_do_not_sum_the_modules_voc(self):
        m = module(pmax=360, voc=60, vmp=50, isc=6.5, imp=6, beta_voc=-0.25)
        opt = optimizers.Optimizer.from_record({"manufacturer": "SolarEdge", "model": "P800p",
                                               "rated_input_power_w": 800, "max_input_voltage_v": 83,
                                               "max_input_isc_a": 7, "modules_per_unit": 2})
        got = {c.key:c for c in optimizers.module_checks(m, opt, 2, -10, None)}
        self.assertTrue(got["opt_voc"].ok, got["opt_voc"].detail)
        self.assertIn("65.2", got["opt_voc"].detail)
        self.assertTrue(got["opt_isc"].ok)  # datasheet's 7 A limit is per physical input
        self.assertTrue(got["opt_power"].ok)  # 720 W combined, below 800 W

    def test_every_module_type_in_a_manual_optimized_string_is_checked(self):
        a = group(grid(1, 8), "a")
        b = group(grid(1, 2), "b", module(model="overcurrent", isc=25, imp=20))
        runs = [{"inverter": 1, "mppt": 1, "modules": [f"{g.sfid}/{pm.key}" for g in (a,b) for pm in g.placed]}]
        out = plant.build(project("SE6000H", optimizer="S500", strings={"runs": runs}), groups=[a,b])
        self.assertEqual(out.strings[0].state, "fail")
        self.assertTrue(any(c.key == "opt_isc" and not c.ok for c in out.strings[0].plan.checks))

    def test_proposal_does_not_apply_one_inverters_rules_to_a_different_architecture(self):
        p = project("SE5000H", optimizer="S500")
        p.energy["inverters"].append({"record":inverter("SE50K"), "count":1,
                                       "optimizer":optimizer_rec("S1000"), "per_optimizer":2})
        out = plant.build(p, groups=[group(grid(4,10))])
        self.assertTrue(out.strings)
        self.assertTrue(all(s.state != "fail" for s in out.strings), [s.why for s in out.strings])
