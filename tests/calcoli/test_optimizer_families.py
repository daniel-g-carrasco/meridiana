"""The optimizers of every maker on file (R456, energy/optimizer_strings.py, catalog/rules.py): for each family a case
that passes and one that does not, with the number of its sheet; units of one and of two modules in one string where the
sheet allows it; a small project with Huawei and one with Tigo."""

import unittest

import _setup  # noqa: F401

from meridiana import catalog
from meridiana.catalog import rules
from meridiana.energy import optimizer_strings as mlpe
from meridiana.energy import optimizers, plant
from meridiana.energy.components import ModuleSpec

T_MIN = -10.0


def module(**k) -> ModuleSpec:
    rec = {"manufacturer": "Acme", "model": "450", "pmax": 450, "vmp": 33.6, "imp": 13.4, "voc": 40.1, "isc": 14.1,
           "beta_voc": -0.25, "alpha_isc": 0.046, "gamma_pmax": -0.30, "cells": 108, "length": 1.762, "width": 1.134}
    rec.update(k)
    return ModuleSpec.from_record(rec)


def record(kind: str, maker: str, model: str) -> dict:
    found = [r for r in catalog.search(kind, manufacturer=maker, limit=None) if r["model"] == model]
    return found[0] if found else {"manufacturer": maker, "model": model}


def setup(optimizer: str, maker: str, inverter: str, per: int | None = None, inverter_maker: str | None = None):
    entry = {"optimizer": record("optimizers", maker, optimizer)}
    if per:
        entry["per_optimizer"] = per
    inv = record("inverters", inverter_maker or maker, inverter)
    inv.setdefault("mppt_voltage_min_v", 200)
    return mlpe.setup(entry, inv)


def checks(s, mod, n, sizes=None, window=(1, 10 ** 6)):
    return {c.key: c for c in mlpe.string_checks(s, mod, n, sizes, T_MIN, window)}


class TheFamilies(unittest.TestCase):
    def test_every_optimizer_of_the_catalogue_has_its_family_with_its_documents(self):
        for maker in ("SolarEdge", "Huawei", "Sungrow", "Tigo"):
            for rec in catalog.search("optimizers", manufacturer=maker, limit=None):
                fam = rules.family(rec)
                self.assertIsNotNone(fam, rec["model"])
                self.assertTrue(fam.datasheet, fam.id)
                for row in fam.raw.get("string_rules", []):
                    self.assertTrue(row.get("source"), (fam.id, row["inverters"]))

    def test_the_sungrow_sp600s_goes_with_the_inverters_its_v8_sheet_names(self):
        # SP600S V8 p. 1: SG5.0-20RT-P2 without the «consult Sungrow», the RS and CX-P2 with it; SG10RT (no P2) not named
        fam = rules.family({"manufacturer": "Sungrow", "model": "SP600S"})
        self.assertEqual(rules.string_rule(fam, {"manufacturer": "Sungrow", "model": "SG10RT-P2"}).consult, False)
        self.assertTrue(rules.string_rule(fam, {"manufacturer": "Sungrow", "model": "SG50CX-P2"}).consult)
        self.assertEqual(rules.string_rule(fam, {"manufacturer": "Sungrow", "model": "SG10RT"}).state, rules.NO)

    def test_the_small_huawei_optimizers_are_not_for_the_100ktl_m2(self):
        # SUN2000-450W-P2/600W-P IT 06/02/2023 p. 1: «SUN2000-12/15/17/20KTL-M2», not the commercial 100KTL-M2
        fam = rules.family({"manufacturer": "Huawei", "model": "SUN2000-450W-P2"})
        self.assertEqual(rules.string_rule(fam, {"manufacturer": "Huawei", "model": "SUN2000-100KTL-M2"}).state, rules.NO)
        self.assertEqual(rules.string_rule(fam, {"manufacturer": "Huawei", "model": "SUN2000-20KTL-M2"}).maximum, 35)


class Huawei(unittest.TestCase):
    def test_sun2000_p_on_an_m1_from_6_to_35_and_10_kw_a_string(self):
        s = setup("SUN2000-450W-P2", "Huawei", "SUN2000-10KTL-M1")
        self.assertTrue(s.long_string)
        ok = checks(s, module(), 22)                                  # 22 x 450 = 9.9 kW
        self.assertEqual((ok["mlpe_count"].level, ok["mlpe_string_power"].level), ("ok", "ok"))
        self.assertIn("06/02/2023, p. 1", ok["mlpe_count"].source)
        short = checks(s, module(), 5)                                # «Nro minimo di ottimizzatori per stringa» 6
        self.assertEqual(short["mlpe_count"].level, "fail")
        over = checks(s, module(), 24)                                # 10.8 kW: allowed with losses, by hand
        self.assertEqual(over["mlpe_string_power"].level, "warn")
        self.assertIn("10/11/2025, p. 5", over["mlpe_string_power"].source)

    def test_a_long_string_replaces_the_inverters_voltage_and_its_energy_is_modelled(self):
        s = setup("SUN2000-450W-P2", "Huawei", "SUN2000-10KTL-M1")
        m = module(pmax=400, voc=49.0, vmp=41.0)
        self.assertEqual(mlpe.length_range(s, m, T_MIN, (5, 20)), (6, 25))  # 10,000 W / 400 W = 25 (guide DE p. 9)
        from meridiana.energy import stringing
        spec = plant.InverterSpec.from_record(record("inverters", "Huawei", "SUN2000-10KTL-M1"), count=1)
        plain = stringing.plan(m, spec, 25, [1, 0], T_MIN, 60.0)
        self.assertEqual({c.key: c.level for c in plain.checks}["uoc"], "fail")   # 25 x 53.3 V > 1,100 V
        found = {c.key: c for c in mlpe.adapt_plan(plain, s, m, 25, None, T_MIN, (5, 20)).checks}
        self.assertEqual(found["uoc"].level, "info")
        self.assertNotIn("mlpe_energy", found)          # the year is computed optimizer by optimizer (R456, r18)
        self.assertEqual(plain.checks[0].key, "uoc")
        self.assertEqual({c.key: c.level for c in plain.checks}["uoc"], "fail")   # the cached plan is not changed

    def test_sun2000_p_long_string_within_1900_v_of_voc_in_the_cold(self):
        s = setup("SUN2000-450W-P2", "Huawei", "SUN2000-10KTL-M1")
        m = module(pmax=280, voc=60.0)                                # 60 V x 1.0875 = 65.3 V: 1900 / 65.3 = 29
        self.assertEqual(mlpe.length_range(s, m, T_MIN, (1, 10 ** 6))[1], 29)
        self.assertEqual(checks(s, m, 29)["mlpe_long_voc"].level, "ok")
        # a warning, not a limit (Daniel, 06/11/2026, R456 answer 4); the proposals keep within it (29 above)
        self.assertEqual(checks(s, m, 30)["mlpe_long_voc"].level, "warn")
        self.assertTrue(checks(s, m, 30)["mlpe_long_voc"].ok)

    def test_pa0_on_an_l1_from_4_to_20_and_6_kw(self):
        s = setup("SUN2000-600W-PA0", "Huawei", "SUN2000-5KTL-L1")
        self.assertEqual(checks(s, module(), 13)["mlpe_count"].level, "ok")      # 13 x 450 = 5.85 kW
        self.assertEqual(checks(s, module(), 21)["mlpe_count"].level, "fail")    # «max 20» on L1

    def test_merc_on_the_50ktl_m3_from_8_to_20_optimizers_and_20_kw(self):
        s = setup("MERC-1100W-P", "Huawei", "SUN2000-50KTL-M3")
        self.assertEqual(s.per, 2)
        m = module(pmax=500)
        ok = checks(s, m, 40)                                          # 20 MERC, 20 kW (EN 20/08/2025 p. 2)
        self.assertEqual((ok["mlpe_count"].level, ok["mlpe_string_power"].level), ("ok", "ok"))
        bad = checks(s, m, 42)                                         # 21 MERC, 21 kW
        self.assertEqual((bad["mlpe_count"].level, bad["mlpe_string_power"].level), ("fail", "fail"))

    def test_merc_with_one_module_among_pairs_is_not_stated_so_never_proposed(self):
        s = setup("MERC-1100W-P", "Huawei", "SUN2000-50KTL-M3")
        self.assertEqual(checks(s, module(pmax=500), 39)["mlpe_mixed"].level, "warn")
        self.assertFalse(mlpe.length_allowed(s, 39))
        self.assertTrue(mlpe.length_allowed(s, 40))

    def test_merc_takes_modules_up_to_605_w(self):
        s = setup("MERC-1100W-P", "Huawei", "SUN2000-50KTL-M3", per=1)
        self.assertEqual(checks(s, module(pmax=600), 16)["mlpe_power"].level, "ok")
        self.assertEqual(checks(s, module(pmax=620), 16)["mlpe_power"].level, "fail")   # note 1: ≤605 W at STC

    def test_merc_one_string_an_mppt_and_strings_within_2_kw(self):
        s = setup("MERC-1300W-P", "Huawei", "SUN2000-50KTL-M3")
        found, _settled = mlpe.input_checks(s, [40, 40], [((15.0, 0.0),), ((15.0, 0.0),)])
        self.assertEqual({c.key: c.level for c in found}["mlpe_parallel"], "fail")    # guide DE p. 7
        (spread,) = mlpe.unit_checks("Inverter 1", s, [20000.0, 17000.0])
        self.assertEqual(spread.level, "warn")                                           # note 10: 2 kW
        self.assertEqual(mlpe.unit_checks("Inverter 1", s, [20000.0, 18500.0])[0].level, "ok")

    def test_huawei_parallel_strings_of_the_same_length_even_fully_optimized(self):
        s = setup("SUN2000-450W-P2", "Huawei", "SUN2000-20K-MB0")
        found, _settled = mlpe.input_checks(s, [16, 15], [((15.0, 0.0),), ((15.0, 0.0),)])
        self.assertEqual({c.key: c.level for c in found}["mlpe_lengths"], "fail")     # guide FR p. 11
        self.assertEqual(checks(s, module(), 16)["mlpe_rules"].level, "warn")        # MB0: limits not printed

    def test_huawei_optimizers_on_another_makers_inverter_are_refused(self):
        s = setup("MERC-1100W-P", "Huawei", "STP 20-50", inverter_maker="SMA")
        self.assertEqual(checks(s, module(), 20)["mlpe_inverter"].level, "fail")
        self.assertEqual(mlpe.length_range(s, module(), T_MIN, (5, 20)), (0, 0))


class Sungrow(unittest.TestCase):
    def test_sp600s_consult_sungrow_and_the_module_within_5_percent(self):
        s = setup("SP600S", "Sungrow", "SH5.0RS")
        self.assertEqual(checks(s, module(), 10)["mlpe_rules"].level, "warn")              # «consult Sungrow»
        self.assertEqual(checks(s, module(pmax=630), 10)["mlpe_power"].level, "ok")      # 600 W + 5 %
        self.assertEqual(checks(s, module(pmax=640), 10)["mlpe_power"].level, "warn")    # note **: DC/AC above 1.2
        self.assertEqual(mlpe.length_range(s, module(), T_MIN, (3, 11)), (3, 11))         # as without optimizers

    def test_sp600s_on_an_inverter_its_sheet_does_not_name(self):
        s = setup("SP600S", "Sungrow", "SG10RT")
        self.assertEqual(checks(s, module(), 10)["mlpe_inverter"].level, "fail")


class Tigo(unittest.TestCase):
    def test_ts4_o_parallel_strings_within_25_percent(self):
        s = setup("TS4-A-O", "Tigo", "STP 20-50", inverter_maker="SMA")
        facings = [((15.0, 0.0),), ((15.0, 0.0),)]
        ok, settled = mlpe.input_checks(s, [16, 13], facings)                 # 1 - 13/16 = 19 %
        self.assertTrue(settled)
        self.assertEqual({c.key: c.level for c in ok}["mlpe_lengths"], "ok")
        bad, _settled = mlpe.input_checks(s, [16, 11], facings)               # 31 %: the uneven strings article
        found = {c.key: c for c in bad}["mlpe_lengths"]
        self.assertEqual(found.level, "fail")
        self.assertIn("202304236", found.source)

    def test_ts4_o_takes_15_a_of_imp(self):
        s = setup("TS4-A-O", "Tigo", "STP 20-50", inverter_maker="SMA")
        self.assertNotIn("mlpe_imp", checks(s, module(imp=13.4), 10))
        self.assertEqual(checks(s, module(imp=16.0, isc=17.0), 10)["mlpe_imp"].level, "fail")   # 002-00143-00 p. 1

    def test_ts4_f_parallel_strings_alike(self):
        s = setup("TS4-A-F (versione 20 A Isc)", "Tigo", "STP 20-50", inverter_maker="SMA")
        found, settled = mlpe.input_checks(s, [16, 13], [((15.0, 0.0),), ((15.0, 0.0),)])
        self.assertFalse(settled)
        self.assertEqual({c.key: c.level for c in found}["mlpe_lengths"], "fail")
        self.assertEqual(checks(s, module(), 16)["mlpe_rules"].level, "info")     # as without optimizers (FAQ)
        self.assertNotIn("mlpe_energy", checks(s, module(), 16))                   # it does not optimize

    def test_ts4_2f_with_single_modules_on_ts4_f_in_the_same_string(self):
        s = setup("TS4-A-2F (versione 20 A Isc)", "Tigo", "STP 20-50", inverter_maker="SMA")
        self.assertEqual(s.per, 2)
        mixed = checks(s, module(), 19)                                        # 9 TS4-A-2F and one TS4-A-F
        self.assertEqual(mixed["mlpe_mixed"].level, "ok")
        self.assertIn("002-00157-00 Rev. 1.3 (08/10/2025), p. 2", mixed["mlpe_mixed"].source)
        self.assertTrue(mlpe.length_allowed(s, 19))
        self.assertEqual(checks(s, module(pmax=520), 18)["mlpe_power"].level, "fail")   # 500 W an input (20 A)


class SolarEdgeMixing(unittest.TestCase):
    def test_s1400_one_single_module_a_string_note_9(self):
        fv = optimizers.fixed_voltage(record("inverters", "SolarEdge", "SE25K"))
        opt = optimizers.Optimizer.from_record(record("optimizers", "SolarEdge", "S1400"))
        r, _why = optimizers.rules_for(opt, fv)
        m = module(pmax=450)

        def single(sizes):
            p = optimizers.string_plan(m, opt, 2, fv, r, sum(sizes), 1, 0.0, T_MIN, group_sizes=sizes)
            return [c for c in p.checks if c.key == "opt_singles"]
        self.assertEqual(single([2] * 13 + [1]), [])                              # 27 modules, one alone
        (bad,) = single([2] * 12 + [1, 1, 1])
        self.assertEqual(bad.level, "fail")
        self.assertIn("DS-000205-EU (08/01/2024), p. 3, note 9", bad.source)
        fam = rules.family({"manufacturer": "SolarEdge", "model": "S1400"})
        self.assertEqual(fam.mixing, "one_single")


def grid(rows: int, per_row: int, azimuth: float = 0.0) -> list:
    from meridiana import layout
    out = []
    for r in range(rows):
        for c in range(per_row):
            x, y = 1.2 * c, 3.0 * r
            out.append(layout.PlacedModule(r, c, 0, [(x - 0.5, y - 1), (x + 0.5, y - 1), (x + 0.5, y + 1),
                                                     (x - 0.5, y + 1)], (x, y), 1.0, 15.0, azimuth))
    return out


def project(maker: str, inverter: str, optimizer_maker: str, optimizer: str, per: int | None = None,
            strings: dict | None = None):
    from meridiana import model as m
    p = m.Project(name="Prova")
    entry = {"record": record("inverters", maker, inverter), "count": 1, "name": "",
             "optimizer": record("optimizers", optimizer_maker, optimizer)}
    if per:
        entry["per_optimizer"] = per
    p.energy = {"inverters": [entry], "strings": strings if strings is not None else {"auto": True}}
    return p


class SmallProjects(unittest.TestCase):
    def test_a_huawei_roof_with_sun2000_p_in_strings_of_22(self):
        # 44 x 450 W on a SUN2000-10KTL-M1 with SUN2000-450W-P2: at most 10 kW a string (22 modules), one an MPPT
        g = plant.Group("s1.0", "s1", "s1", module(), grid(2, 22))
        out = plant.build(project("Huawei", "SUN2000-10KTL-M1", "Huawei", "SUN2000-450W-P2"), groups=[g])
        self.assertIsNotNone(out.units[0].mlpe)
        self.assertEqual(sorted(len(s.modules) for s in out.strings), [22, 22])
        self.assertFalse(out.left)
        for s in out.strings:
            self.assertNotEqual(s.state, "fail", s.why)
            levels = {c.key: c.level for c in s.plan.checks}
            self.assertEqual(levels["mlpe_count"], "ok")
            self.assertLessEqual(len(s.modules) * 450, 10000)

    def test_a_huawei_long_string_is_proposed_within_the_power_per_string(self):
        # 400 W modules of 49 V: 20 in series by the inverter's 1,100 V, 25 with the optimizers (10,000 W / 400 W)
        m = module(pmax=400, voc=49.0, vmp=41.0, imp=9.8, isc=10.4)
        g = plant.Group("s1.0", "s1", "s1", m, grid(2, 25))
        out = plant.build(project("Huawei", "SUN2000-10KTL-M1", "Huawei", "SUN2000-450W-P2"), groups=[g])
        self.assertEqual(sorted(len(s.modules) for s in out.strings), [25, 25])
        for s in out.strings:
            levels = {c.key: c.level for c in s.plan.checks}
            self.assertEqual(levels["uoc"], "info")
            self.assertNotIn("mlpe_energy", levels)
            self.assertTrue(plant.acceptable(s), s.why)

    def test_a_tigo_roof_on_an_sma_inverter_is_strung_as_without_optimizers(self):
        g = plant.Group("s1.0", "s1", "s1", module(), grid(2, 18))
        with_tigo = plant.build(project("SMA", "STP 20-50", "Tigo", "TS4-A-O"), groups=[g])
        plain = project("SMA", "STP 20-50", "Tigo", "TS4-A-O")
        del plain.energy["inverters"][0]["optimizer"]
        without = plant.build(plain, groups=[g])
        self.assertEqual(sorted(len(s.modules) for s in with_tigo.strings),
                         sorted(len(s.modules) for s in without.strings))      # Tigo's FAQ of 17/01/2025
        for s in with_tigo.strings:
            levels = {c.key: c.level for c in s.plan.checks}
            self.assertEqual(levels["mlpe_rules"], "info")
            self.assertNotIn("mlpe_energy", levels)
            self.assertEqual(s.state, "ok", s.why)

    def test_a_tigo_string_by_hand_across_two_orientations_with_ts4_o(self):
        east, west = grid(1, 8, azimuth=-90.0), grid(1, 8, azimuth=90.0)
        groups = [plant.Group("e.0", "e", "e", module(), east), plant.Group("w.0", "w", "w", module(), west)]
        keys = [f"e/{pm.key}" for pm in east] + [f"w/{pm.key}" for pm in west]
        by_hand = {"auto": False, "runs": [{"inverter": 1, "mppt": 1, "modules": keys}]}
        out = plant.build(project("SMA", "STP 20-50", "Tigo", "TS4-A-O", strings=by_hand), groups=groups)
        (s,) = out.strings
        self.assertEqual(s.state, "ok", s.why)                  # TS4-O on every module (orientations article, point 3)
        out = plant.build(project("SMA", "STP 20-50", "Tigo", "TS4-A-S", strings=by_hand), groups=groups)
        self.assertNotEqual(out.strings[0].state, "ok")          # TS4-S does not optimize: one orientation


if __name__ == "__main__":
    unittest.main()
