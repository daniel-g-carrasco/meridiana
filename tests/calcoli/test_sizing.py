"""Automatic inverter sizing together with a complete, valid string proposal (R187)."""

import unittest

import _setup  # noqa: F401

from meridiana import layout, model
from meridiana.energy import plant, sizing
from meridiana.energy.components import ModuleSpec


def module(**changes) -> ModuleSpec:
    rec = {"manufacturer": "Acme", "model": "450", "pmax": 450, "vmp": 33.6, "imp": 13.4, "voc": 40.1,
           "isc": 14.1, "beta_voc": -0.25, "alpha_isc": 0.046, "gamma_pmax": -0.30, "cells": 108,
           "length": 1.762, "width": 1.134, "max_system_voltage_v": 1500, "max_series_fuse_a": 25}
    rec.update(changes)
    return ModuleSpec.from_record(rec)


def inverter(name: str, kw: float, **changes) -> dict:
    rec = {"manufacturer": "Acme", "model": name, "ac_power_nominal_w": kw * 1000,
           "efficiency_euro_pct": 97.5, "dc_voltage_max_v": 1100, "mppt_voltage_min_v": 180,
           "mppt_voltage_max_v": 1000, "mppt_count": 4, "dc_current_max_per_mppt_a": [60] * 4,
           "dc_isc_max_per_mppt_a": [100] * 4, "source": "curated"}
    rec.update(changes)
    return rec


def grid(count: int, azimuth: float = 0.0) -> list:
    out = []
    for i in range(count):
        r, s = divmod(i, 12)
        x, y = 1.2 * s, 3.0 * r
        out.append(layout.PlacedModule(r, s, 0, [(x - 0.5, y - 1), (x + 0.5, y - 1),
                                                   (x + 0.5, y + 1), (x - 0.5, y + 1)],
                                       (x, y), 1.0, 15.0, azimuth))
    return out


def project(entries=None) -> model.Project:
    p = model.Project(name="Prova")
    p.energy = {"inverters": entries or [], "dc_ac_ratio": 1.1,
                "strings": {"strategy": "serpentine"}}
    return p


def groups(counts: list[int]) -> list:
    out = []
    for i, count in enumerate(counts):
        placed = grid(count, 90.0 * i)
        out.append(plant.Group(f"s{i + 1}.0", f"s{i + 1}", f"Field {i + 1}", module(), placed))
    return out


class Combinations(unittest.TestCase):
    def test_tracker_count_can_require_more_inverters_than_the_power_ratio(self):
        rec = inverter("30K", 30, mppt_count=1, strings_per_mppt=[1])
        result = sizing.choose(project(), groups([20, 20]), [rec], 1.0)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(result.entries[0]["count"], 2)
        self.assertFalse(result.plant.left)

    def test_connector_capacity_can_require_more_inverters_than_the_power_ratio(self):
        rec = inverter("100K", 100, mppt_count=1, strings_per_mppt=[1])
        result = sizing.choose(project(), groups([96]), [rec], 1.0)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(result.entries[0]["count"], 4)
        self.assertEqual([len(s.modules) for s in result.plant.strings], [24] * 4)

    def test_powers_of_one_brand_are_combined_when_no_model_alone_strings_every_group(self):
        gs = groups([55, 55])
        gs[1].module = module(pmax=180, vmp=6.0, imp=30.0, voc=10.0, isc=32.0)
        ordinary = inverter("20K", 20, mppt_count=6, mppt_voltage_max_v=400,
                            dc_current_max_per_mppt_a=[20] * 6, dc_isc_max_per_mppt_a=[30] * 6)
        low_voltage = inverter("25K", 25, mppt_count=3, dc_voltage_max_v=120, mppt_voltage_min_v=60,
                               mppt_voltage_max_v=120, dc_current_max_per_mppt_a=[70] * 3,
                               dc_isc_max_per_mppt_a=[100] * 3)
        result = sizing.choose(project(), gs, [ordinary, low_voltage], 1.1)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual([(e["record"]["model"], e["count"]) for e in result.entries], [("20K", 1), ("25K", 1)])
        self.assertEqual(sum(len(r["modules"]) for r in result.runs), 110)

    def test_the_ratio_comes_before_the_number_of_inverters(self):
        """R420: 45 kWp at 1.10 asked is not one 50 kW inverter (0.90) when two 20 kW ones give 1.13."""
        result = sizing.choose(project(), groups([100]), [inverter("20K", 20), inverter("25K", 25),
                                                            inverter("50K", 50)], 1.1)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual([(e["record"]["model"], e["count"]) for e in result.entries], [("20K", 2)])
        self.assertEqual(result.standing, sizing.IN_BAND)
        self.assertRegex(result.why, r"1[.,]1[23]")

    def test_within_the_band_fewer_inverters_win(self):
        result = sizing.choose(project(), groups([100]), [inverter("20K", 20), inverter("40K", 40)], 1.1)
        self.assertEqual([(e["record"]["model"], e["count"]) for e in result.entries], [("40K", 1)])

    def test_alternatives_are_valid_and_say_their_ratio(self):
        result = sizing.choose(project(), groups([100]), [inverter("20K", 20), inverter("25K", 25),
                                                            inverter("33K", 33), inverter("50K", 50)], 1.1)
        names = [r.entries[0]["record"]["model"] for r in result.alternatives]
        self.assertTrue(result.alternatives)
        self.assertLessEqual(len(result.alternatives), sizing.MAX_ALTERNATIVES)
        self.assertIn("33K", names)
        for alternative in result.alternatives:
            self.assertTrue(alternative.ok)
            self.assertTrue(alternative.runs)
            self.assertTrue(alternative.why)
            self.assertGreater(alternative.ratio, 0)

    def test_an_oversized_inverter_only_when_nothing_else_remains_and_is_said(self):
        result = sizing.choose(project(), groups([100]), [inverter("50K", 50)], 1.1)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(result.standing, sizing.UNDER_ONE)
        self.assertLess(result.ratio, 1)
        self.assertTrue(any("oversized" in note for note in result.notes), result.notes)

    def test_above_the_band_comes_before_under_one(self):
        result = sizing.choose(project(), groups([100]), [inverter("33K", 33), inverter("50K", 50)], 1.1)
        self.assertEqual([(e["record"]["model"], e["count"]) for e in result.entries], [("33K", 1)])
        self.assertEqual(result.standing, sizing.ABOVE_BAND)
        self.assertEqual([r.entries[0]["record"]["model"] for r in result.alternatives][:1], ["50K"])

    def test_the_band_follows_what_was_asked(self):
        self.assertAlmostEqual(sizing.band(1.1)[0], 0.95)
        self.assertAlmostEqual(sizing.band(1.1)[1], 1.3)
        self.assertAlmostEqual(sizing.band(1.3)[0], 1.15)
        self.assertAlmostEqual(sizing.band(0.9)[0], 0.75)
        self.assertEqual(sizing.standing(0.8, 0.9), sizing.IN_BAND)
        self.assertEqual(sizing.standing(0.9, 1.1), sizing.UNDER_ONE)
        self.assertEqual(sizing.standing(1.05, 1.3), sizing.BELOW_BAND)

    def test_single_phase_inverters_are_not_mixed_or_multiplied(self):
        three = inverter("20K", 20, phases=3)
        one = inverter("6K", 6, phases=1)
        result = sizing.choose(project(), groups([60]), [three, one], 1.1)
        for candidate in [result, *result.alternatives]:
            phases = [e["record"].get("phases") for e in candidate.entries]
            self.assertFalse(1 in phases and (3 in phases or candidate.units > 1), candidate.why)

    def test_fewer_models_comes_before_the_closest_ratio(self):
        limited = {"mppt_count": 1, "dc_current_max_per_mppt_a": [45], "dc_isc_max_per_mppt_a": [60]}
        result = sizing.choose(project(), groups([96]), [inverter("10K", 10, **limited),
                                                           inverter("20K", 20, **limited),
                                                           inverter("30K", 30, **limited)], 1.1)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual([(e["record"]["model"], e["count"]) for e in result.entries], [("20K", 2)])
        self.assertIn("then fewer inverters, then fewer models, then the closest ratio", result.criterion)

    def test_a_combination_is_accepted_only_if_every_module_has_a_valid_string(self):
        limited = inverter("30K", 30, mppt_count=2, dc_current_max_per_mppt_a=[16, 16],
                           dc_isc_max_per_mppt_a=[20, 20])
        result = sizing.choose(project(), groups([100]), [limited], 1.0)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(result.entries[0]["count"], 2)
        self.assertFalse(result.plant.left)
        self.assertTrue(all(s.state == "ok" for s in result.plant.strings))

    def test_different_orientations_are_never_mixed_on_one_input(self):
        result = sizing.choose(project(), groups([24, 24]), [inverter("30K", 30, mppt_count=2)], 1.0)
        self.assertTrue(result.ok, result.reason)
        for slot in result.plant.inputs.values():
            strings = [result.plant.strings[i] for i in slot.strings]
            self.assertLessEqual(len({s.modules[0][0] for s in strings}), 1)
        self.assertFalse(result.plant.left)


class Catalogue(unittest.TestCase):
    def test_three_real_brands_size_a_small_plant_with_a_complete_proposal(self):
        from meridiana import catalog
        from meridiana.energy.components import ModuleSpec
        rec = catalog.search("modules", "LR7-54HVH", source="curated")[0]
        gs = groups([24])
        gs[0].module = ModuleSpec.from_record(rec)
        for brand in ("Huawei", "SMA", "Sungrow"):
            with self.subTest(brand=brand):
                records = [r for r in catalog.load("inverters") if r.get("manufacturer") == brand]
                result = sizing.choose(project(), gs, records, 1.1)
                self.assertTrue(result.ok, result.reason)
                self.assertFalse(result.plant.left)
                self.assertTrue(all(s.state == "ok" for s in result.plant.strings))


class Impossible(unittest.TestCase):
    def test_shared_current_limit_cannot_be_certified_by_individual_tracker_checks(self):
        rec = inverter("30K", 30, mppt_count=2, dc_current_max_per_mppt_a=[20, 20],
                       dc_isc_max_per_mppt_a=[25, 25], dc_current_max_a=25)
        result = sizing.choose(project(), groups([20, 20]), [rec], 1.0)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(result.entries[0]['count'], 2)
        self.assertEqual({s.inverter for s in result.plant.strings}, {1, 2})

    def test_exhausting_the_search_budget_is_not_reported_as_electrical_impossibility(self):
        from unittest.mock import patch
        with patch.object(sizing, "MAX_CANDIDATES", 1):
            result = sizing.choose(project(), groups([20, 20]),
                                   [inverter("30K", 30, mppt_count=1), inverter("40K", 40, mppt_count=1)], 1)
        self.assertFalse(result.ok)
        self.assertIn("incomplete", result.reason)
        self.assertFalse(result.search_complete)

    def test_search_can_be_cancelled_without_applying_a_partial_choice(self):
        result = sizing.choose(project(), groups([20]), [inverter("30K", 30)], 1, cancelled=lambda: True)
        self.assertFalse(result.ok)
        self.assertFalse(result.search_complete)
        self.assertIn("cancelled", result.reason)
        self.assertEqual(result.entries, [])

    def test_a_prime_count_says_why_and_proposes_the_smallest_correction(self):
        rec = inverter("3K", 3, mppt_voltage_min_v=180, mppt_voltage_max_v=350, mppt_count=2)
        p = project([{"record": rec, "count": 1, "name": ""}])
        out = plant.build(p, groups=groups([23]))
        self.assertTrue(out.left)
        self.assertTrue(out.corrections)
        self.assertIn("Add 1 module", out.corrections[0])
        self.assertIn("24", out.corrections[0])
        self.assertIn("8", out.corrections[0])

    def test_no_valid_combination_leaves_the_choice_unchanged_and_says_why(self):
        bad = inverter("30K", 30, dc_current_max_per_mppt_a=[5] * 4, dc_isc_max_per_mppt_a=[8] * 4)
        result = sizing.choose(project(), groups([23]), [bad], 1.0)
        self.assertFalse(result.ok)
        self.assertEqual(result.entries, [])
        self.assertIn("current", result.reason)


def real_groups(counts: list[int], module_model: str) -> list:
    from meridiana import catalog
    spec = ModuleSpec.from_record(catalog.search("modules", module_model, source="curated")[0])
    out = groups(counts)
    for g in out:
        g.module = spec
    return out


def catalog_load(kind: str):
    from meridiana import catalog
    return catalog.load(kind)


def brand(name: str) -> list[dict]:
    from meridiana import catalog
    return [r for r in catalog.load("inverters") if r.get("manufacturer") == name]


class SolarEdgeAndAbb(unittest.TestCase):
    """R267: the sizing with SolarEdge and ABB/FIMER on real catalogue records, three sizes of plant."""

    def test_r420_45_kwp_at_1_10_is_not_one_se50k(self):
        # 95 x 475 W = 45.1 kWp: Daniel's case. One SE50K gives 0.90: valid, it stays among the alternatives, said oversized
        result = sizing.choose(project(), real_groups([95], "JKM475N-48QL6-DV"), brand("SolarEdge"), 1.1)
        self.assert_valid(result)
        self.assertEqual(result.standing, sizing.IN_BAND, result.why)
        self.assertNotIn("SE50K", [e["record"]["model"] for e in result.entries])
        self.assertTrue(1.0 <= result.ratio <= 1.3)
        others = [r.entries[0]["record"]["model"] for r in result.alternatives]
        self.assertTrue(others)
        self.assertIn("DC/AC", result.why)

    def assert_valid(self, result):
        self.assertTrue(result.ok, result.reason)
        self.assertTrue(result.search_complete)
        self.assertFalse(result.plant.left)
        self.assertTrue(all(plant.acceptable(s) for s in result.plant.strings))
        self.assertFalse([c for checks in result.plant.checks.values() for c in checks if c.level == "fail"])

    def test_r428_daniels_95_modules_are_54_and_41_within_the_tables_connected_power(self):
        """95 x 475 W on 2 x SE20K with S1400: at least 27 modules a string (14 optimizers); the commercial table allows
        20,250 W connected with one string and 28,000 W each with two or more, above the 18,000 W carried continuously
        (DS-000205-EU p. 3), and the proposals use it (Daniel, 06/11/2026, R456 answer 1). So 54 + 41 again (41 x 475 =
        19,475 W in one string), ratios 1.29 and 0.98; within the continuous power alone (r17) it was 58 + 37, 1.38 and
        0.88; before R428 63 + 32, 1.50 and 0.76."""
        s1400 = next(r for r in catalog_load("optimizers") if r["model"] == "S1400")
        entries = [dict(record=next(r for r in brand("SolarEdge") if r["model"] == "SE20K"), count=2, name="", optimizer=s1400, per_optimizer=2)]
        p = project(entries)
        p.energy["strings"]["auto"] = True
        out = plant.build(p, groups=real_groups([95], "JKM475N-48QL6-DV"))
        self.assertFalse(out.left)
        self.assertTrue(all(plant.acceptable(s) for s in out.strings), [s.why for s in out.strings])
        by_unit = {}
        for s in out.strings:
            by_unit.setdefault(s.inverter, []).append(len(s.modules))
        self.assertEqual(sorted(by_unit.values()), [[27, 27], [41]])
        self.assertTrue(all(s.plan.power_w <= s.plan.limit_w + 1e-6 for s in out.strings))
        lone = next(s for s in out.strings if len(s.modules) == 41)
        self.assertEqual(lone.plan.limit_w, 20250.0)
        self.assertEqual({c.key: c.level for c in lone.plan.checks}["opt_continuous"], "info")
        ratios = sorted(plant.unit_ratios(out).values())
        self.assertAlmostEqual(ratios[0], 0.98, 2)
        self.assertAlmostEqual(ratios[1], 1.29, 2)

    def test_the_alternatives_say_the_ratio_of_each_inverter(self):
        result = sizing.choose(project(), real_groups([95], "JKM475N-48QL6-DV"), brand("SolarEdge"), 1.1)
        self.assertEqual(result.units, 2)
        self.assertEqual(len(result.unit_ratios), 2)
        # within the table's connected power the closest share is 1.29 and 0.98 (test_r428_...); before R428 0.74 apart
        self.assertLess(result.ratio_spread, 0.55)
        self.assertRegex(result.why, r"(?i)by inverter|per inverter")

    def test_a_share_uses_each_inverter_s_own_table(self):
        s1400 = next(r for r in catalog_load("optimizers") if r["model"] == "S1400")
        big = next(r for r in brand("SolarEdge") if r["model"] == "SE33.3K")
        small = next(r for r in brand("SolarEdge") if r["model"] == "SE25K")
        entries = [dict(record=big, count=1, name="", optimizer=s1400, per_optimizer=2), dict(record=small, count=1, name="", optimizer=s1400, per_optimizer=2)]
        p = project(entries)
        p.energy["strings"]["auto"] = True
        out = plant.build(p, groups=real_groups([130], "JKM475N-48QL6-DV"))
        self.assertFalse(out.left)
        self.assertEqual({s.inverter for s in out.strings}, {1, 2})
        self.assertFalse([c for checks in out.checks.values() for c in checks if c.level == "fail"])

    def test_solaredge_residential(self):
        result = sizing.choose(project(), real_groups([14], "JAM54S40-450/LR"), brand("SolarEdge"), 1.1)
        self.assert_valid(result)
        self.assertEqual([(e["record"]["model"], e["count"]) for e in result.entries], [("SE6000H", 1)])

    def test_solaredge_commercial_roof_is_found_without_exhausting_the_search(self):
        # before: 200,000 steps and 30 s on SE50K, then «search limit reached»
        result = sizing.choose(project(), real_groups([100], "LR7-54HVH-495M"), brand("SolarEdge"), 1.1)
        self.assert_valid(result)
        # 49.5 kWp at 1.10 asked: one SE50K (0.99) is within the band, and one inverter beats two
        self.assertEqual([(e["record"]["model"], e["count"]) for e in result.entries], [("SE50K", 1)])
        self.assertLess(result.search_nodes, 20000)
        powers = sorted(len(s.modules) * 495 for s in result.plant.strings)
        self.assertEqual(sum(powers), 49500)

    def test_solaredge_plant_of_hundreds_of_kw_skips_combinations_beyond_the_dc_maximum(self):
        # before: 1 x SE100K (175 kW DC at most) used the whole search for 372 kWp
        result = sizing.choose(project(), real_groups([600], "JAM66D45-620/LB"), brand("SolarEdge"), 1.1)
        self.assert_valid(result)
        self.assertEqual([(e["record"]["model"], e["count"]) for e in result.entries], [("SE100K", 3)])
        self.assertTrue(any("S1400" in note for note in result.notes))      # the order's condition is said

    def test_solaredge_east_west_roof_is_proposed_within_the_tables_connected_power(self):
        # 60 E + 44 W x 495 W: a commercial table allows more connected than carried (DS-000205-EU p. 3, S1400: 20,250 to
        # 22,650 W with one string), and the proposals use it (Daniel, 06/11/2026, R456 answer 1); a residential table
        # never above what a string carries continuously
        groups_ = real_groups([60, 44], "LR7-54HVH-495M")
        result = sizing.choose(project(), groups_, brand("SolarEdge"), 1.1)
        strings = result.plant.strings if result.plant is not None else []
        for s in strings:
            if getattr(s.plan, "continuous_w", 0):
                self.assertLessEqual(s.plan.power_w, s.plan.limit_w + 1e-6)
                levels = {c.key: c.level for c in s.plan.checks}
                self.assertNotEqual(levels.get("opt_continuous"), "warn", s.why)

    def test_a_plane_too_small_for_any_model_is_said_at_once(self):
        result = sizing.choose(project(), real_groups([5, 5], "JAM54S40-450/LR"), brand("SolarEdge"), 1.1)
        self.assertFalse(result.ok)
        self.assertTrue(result.search_complete)
        self.assertEqual(result.evaluated, 0)
        self.assertIn("5 modules on one plane, a string needs at least 6", result.reason)

    def test_abb_records_of_the_cec_say_what_is_missing_and_where_to_go(self):
        result = sizing.choose(project(), real_groups([100], "LR7-54HVH-495M"), brand("ABB"), 1.1)
        self.assertFalse(result.ok)
        self.assertEqual(result.entries, [])
        self.assertIn("number of MPPT", result.reason)
        self.assertIn("CEC", result.reason)
        self.assertIn("FIMER", result.reason)

    def test_solaredge_records_of_the_cec_point_to_the_curated_ones(self):
        result = sizing.choose(project(), real_groups([14], "JAM54S40-450/LR"), brand("SolarEdge Technologies Ltd"),
                               1.1)
        self.assertFalse(result.ok)
        self.assertRegex(result.reason, r"SolarEdge: \d+ models")

    def test_fimer_sizes_the_commercial_and_the_large_plant(self):
        self.assert_valid(sizing.choose(project(), real_groups([100], "LR7-54HVH-495M"), brand("FIMER"), 1.1))
        self.assert_valid(sizing.choose(project(), real_groups([600], "JAM66D45-620/LB"), brand("FIMER"), 1.1))

    def test_fimer_residential_says_the_series_length_it_needs(self):
        # PVS-10-TL: n_min = ceil(460 V / Vmp at 60 °C) = 16 > 14 modules
        result = sizing.choose(project(), real_groups([14], "JAM54S40-450/LR"), brand("FIMER"), 1.1)
        self.assertFalse(result.ok)
        self.assertTrue(result.search_complete)
        self.assertIn("PVS-10-TL, PVS-20-TL: Field 1: 14 modules, a string needs 16 to 25 in series", result.reason)


class SharedSearch(unittest.TestCase):
    def test_an_undecided_combination_does_not_use_up_the_others_search(self):
        from unittest.mock import patch
        real = plant.build
        calls = []

        def build(p, *args, **kwargs):
            calls.append(p.energy["inverters"][0]["record"]["model"])
            if len(calls) == 1:                 # the first combination cannot be decided
                out = plant.Plant(search_complete=False, search_reason="limit")
                kwargs["search"].nodes = kwargs["search"].limit
                return out
            return real(p, *args, **kwargs)
        with patch.object(plant, "build", side_effect=build):
            result = sizing.choose(project(), groups([100]), [inverter("20K", 20), inverter("25K", 25),
                                                                inverter("50K", 50)], 1.1)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(len(result.undecided), 1)
        self.assertTrue(any("could not be decided" in note for note in result.notes))


if __name__ == "__main__":
    unittest.main()
