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

    def test_fewer_inverters_comes_before_the_closest_ratio(self):
        result = sizing.choose(project(), groups([100]), [inverter("20K", 20), inverter("25K", 25),
                                                            inverter("50K", 50)], 1.1)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual([(e["record"]["model"], e["count"]) for e in result.entries], [("50K", 1)])

    def test_fewer_models_comes_before_the_closest_ratio(self):
        limited = {"mppt_count": 1, "dc_current_max_per_mppt_a": [45], "dc_isc_max_per_mppt_a": [60]}
        result = sizing.choose(project(), groups([96]), [inverter("10K", 10, **limited),
                                                           inverter("20K", 20, **limited),
                                                           inverter("30K", 30, **limited)], 1.1)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual([(e["record"]["model"], e["count"]) for e in result.entries], [("20K", 2)])
        self.assertIn("fewer inverters, then fewer models, then the closest DC/AC ratio", result.criterion)

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


if __name__ == "__main__":
    unittest.main()
