"""The year's energy with power optimizers on inverters with MPPT of their own (R456, r18: Huawei SUN2000-P and MERC,
Sungrow SP600S, Tigo TS4-A-O), energy/electrical_network.py: each optimizer at its module's maximum power point and with
its efficiency, the inverter's MPPT choosing the string's voltage within its window. First the string alone on made-up
curves, then three small roofs of the program's own (no designer's data), each with and without optimizers on the same
strings: with the shade of the rows ahead the optimizers gain, without shade they give what the plain string gives,
less their efficiency and plus the mismatch between modules they take away (the 1 % of the losses, as SolarEdge's)."""
import copy
import tempfile
import unittest
from pathlib import Path

import numpy as np

import _setup  # noqa: F401
from meridiana import catalog
from meridiana.energy import electrical as iv, electrical_network as en, optimizers
from meridiana.energy.components import ModuleSpec


def module() -> ModuleSpec:
    return ModuleSpec.from_record({"manufacturer": "Acme", "model": "450", "pmax": 450, "vmp": 33.6, "imp": 13.4,
                                   "voc": 40.1, "isc": 14.1, "beta_voc": -0.25, "alpha_isc": 0.046,
                                   "gamma_pmax": -0.30, "cells": 108, "length": 1.762, "width": 1.134})


def record(kind: str, maker: str, model: str) -> dict:
    return next(r for r in catalog.search(kind, manufacturer=maker, limit=None) if r["model"] == model)


def huawei() -> optimizers.Optimizer:
    # SUN2000-450W-P2 (scheda IT 06/02/2023 p. 1): 10-80 V MPPT, 80 V and 15 A out, 99.0 % weighted
    return optimizers.Optimizer.from_record(record("optimizers", "Huawei", "SUN2000-450W-P2"))


G = np.array([1000.0, 600.0, 200.0, 50.0])         # W/m², four hours at 25 °C


def curve(share: float = 1.0, blocks=(1.0, 1.0, 1.0)) -> iv.Curve:
    g = np.stack([G * share * b for b in blocks], axis=1)
    return iv.module_curve(module(), g, np.full(len(G), 25.0), (3, 1))


def string(curves: list, opt) -> en.OptimizedString:
    inputs: dict = {}
    for c in curves:
        if id(c) not in inputs:
            inputs[id(c)] = [en.optimizer_input(c, opt), 0]
        inputs[id(c)][1] += 1
    return en.OptimizedString([tuple(v) for v in inputs.values()], opt.eta, opt.v_out_max, opt.i_out_max or None)


class TheOptimizedString(unittest.TestCase):
    """One string of optimizers on an MPPT, on curves of the single-diode module."""

    def setUp(self):
        self.opt = huawei()
        self.full = curve()

    def test_every_optimizer_at_its_maximum_power_gives_it_times_its_efficiency(self):
        s = string([self.full] * 10, self.opt)
        voltage, (current,), (power,) = en.optimized_operating_point([s], 140.0, 980.0, 27.0, None)
        ideal = 10 * iv.mpp(self.full).power
        np.testing.assert_allclose(power, 0.99 * ideal, rtol=1e-9)
        self.assertTrue(np.all((voltage >= 140.0) & (voltage <= 980.0)))
        # the highest voltage that keeps the whole power: the modules' own current (the least current)
        np.testing.assert_allclose(current, iv.mpp(self.full).current, rtol=1e-6)

    def test_a_shaded_module_costs_only_itself(self):
        shaded = curve(0.3)
        curves = [self.full] * 9 + [shaded]
        plain = iv.mpp(iv.series(curves), voltage_min=140.0, voltage_max=980.0).power
        _v, _c, (power,) = en.optimized_operating_point([string(curves, self.opt)], 140.0, 980.0, 27.0, None)
        ideal = 9 * iv.mpp(self.full).power + iv.mpp(shaded).power
        np.testing.assert_allclose(power, 0.99 * ideal, rtol=1e-9)
        self.assertTrue(np.all(power > plain))            # +2.3 % at 1000 W/m² on these curves

    def test_a_bypassed_block_is_no_gain_and_the_efficiency_is_lost(self):
        # a module with one block shaded: the plain string bypasses the block and loses nothing more; the optimizers
        # only add their 1 %
        curves = [self.full] * 9 + [curve(1.0, (1.0, 1.0, 0.2))]
        plain = iv.mpp(iv.series(curves), voltage_min=140.0, voltage_max=980.0).power
        _v, _c, (power,) = en.optimized_operating_point([string(curves, self.opt)], 140.0, 980.0, 27.0, None)
        np.testing.assert_allclose(power, 0.99 * plain, rtol=2e-3)

    def test_a_long_string_is_held_at_the_inverters_voltage_with_all_its_power(self):
        # 30 x 450 W: 30 x 33.6 V of MPP voltage would be above the 980 V of a SUN2000-10KTL-M1's MPPT; the optimizers
        # lower the voltage (guide DE 10/11/2025 p. 9, FR 15/07/2026 p. 8) and the string keeps its power
        curves = [self.full] * 30
        plain = iv.mpp(iv.series(curves), voltage_min=140.0, voltage_max=980.0).power
        voltage, (current,), (power,) = en.optimized_operating_point([string(curves, self.opt)], 140.0, 980.0, 27.0,
                                                                      None)
        np.testing.assert_allclose(power, 0.99 * 30 * iv.mpp(self.full).power, rtol=1e-9)
        self.assertEqual(float(voltage[0]), 980.0)
        self.assertLess(plain[0], 30 * iv.mpp(self.full).power[0])      # the plain string is held below its MPP
        np.testing.assert_allclose(current[0], power[0] / 980.0)

    def test_the_optimizers_output_current_bounds_a_string_at_the_inverters_voltage(self):
        # 40 x 450 W at 980 V would ask 18.4 A of optimizers that give 15 A: 980 V x 15 A = 14.7 kW at most
        curves = [self.full] * 40
        voltage, (current,), (power,) = en.optimized_operating_point([string(curves, self.opt)], 140.0, 980.0, 30.0,
                                                                      None)
        self.assertAlmostEqual(float(current[0]), 15.0, places=9)
        self.assertAlmostEqual(float(power[0]), 980.0 * 15.0, places=6)

    def test_a_window_above_the_full_power_span_is_solved_exactly(self):
        # 4 modules in the sun and 2 at 30 %: with every optimizer at its MPP the string would sit at about 150 V,
        # below a 200 V window; at 200 V the sunny modules move above their MPP voltage, solved on their curves
        shaded = curve(0.3)
        s = string([self.full] * 4 + [shaded] * 2, self.opt)
        voltage, (current,), (power,) = en.optimized_operating_point([s], 200.0, 980.0, 27.0, None)
        np.testing.assert_allclose(voltage, 200.0)
        np.testing.assert_allclose(s.voltage(current), 200.0, rtol=1e-6)
        self.assertTrue(np.all(power <= s.full + 1e-9))
        plain = iv.mpp(iv.series([self.full] * 4 + [shaded] * 2), voltage_min=200.0, voltage_max=980.0).power
        self.assertTrue(np.all(power[:3] > plain[:3]))

    def test_parallel_strings_share_one_voltage(self):
        a = string([self.full] * 10, self.opt)
        b = string([self.full] * 9 + [curve(0.3)], self.opt)
        voltage, (ia, ib), (pa, pb) = en.optimized_operating_point([a, b], 140.0, 980.0, 40.0, None)
        np.testing.assert_allclose(pa, a.full, rtol=1e-9)
        np.testing.assert_allclose(pb, b.full, rtol=1e-9)
        np.testing.assert_allclose(pa / ia, voltage)
        np.testing.assert_allclose(pb / ib, voltage)

    def test_an_mppt_current_limit_moves_the_voltage_up_as_little_as_it_can(self):
        # the same two strings on an MPPT of 27 A: at full power they would ask 27.9 A at 1000 W/m²; the lowest voltage
        # at which their actual currents fit, the shaded string's sunny modules a little above their MPP voltage
        a = string([self.full] * 10, self.opt)
        b = string([self.full] * 9 + [curve(0.3)], self.opt)
        voltage, (ia, ib), (pa, pb) = en.optimized_operating_point([a, b], 140.0, 980.0, 27.0, None)
        self.assertAlmostEqual(float(ia[0] + ib[0]), 27.0, delta=0.01)
        np.testing.assert_allclose(pa[0], a.full[0], rtol=1e-9)
        flat = b.full[0] / b.saturation[0]
        self.assertGreater(float(pa[0] + pb[0]), flat * 27.0)       # better than cutting the current at full power
        self.assertLess(float(pb[0]), float(b.full[0]))
        np.testing.assert_allclose(pa[1:] + pb[1:], a.full[1:] + b.full[1:], rtol=1e-9)


# the small roofs: a flat roof at Rho, modules at 30° in rows; the program's clear-sky year (tests/_fixtures)
ROOFS = {"Huawei": (("Huawei", "SUN2000-10KTL-M1"), ("Huawei", "SUN2000-450W-P2"), 9.0, 18.0, 0.990),
         "Tigo": (("SMA", "STP10.0-3SE-40"), ("Tigo", "TS4-A-O"), 9.0, 18.0, 0.996),
         "Sungrow": (("Sungrow", "SG6.0RS"), ("Sungrow", "SP600S"), 6.0, 10.0, 0.990)}


def roof(inverter, optimizer, width: float, depth: float, pitch: float):
    from meridiana import model
    p = model.Project(name="Prova")
    p.site = model.Site(lat=45.5226, lon=9.0300, address="Rho (MI)")
    p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[[0, 0], [width + 2, 0],
                                                                            [width + 2, depth + 2], [0, depth + 2]],
                                      height=6.0))
    p.subfields.append(model.SubField(id="s1", name="Sud", ring=[[1, 1], [width + 1, 1], [width + 1, depth + 1],
                                                                 [1, depth + 1]], building="b1",
                                      params={"tilt": 30.0, "pitch_mode": "value", "pitch": pitch}, filled=True))
    entry = {"record": record("inverters", *inverter), "count": 1, "name": ""}
    if optimizer:
        entry["optimizer"] = record("optimizers", *optimizer)
    p.energy["inverters"] = [entry]
    return p


class SmallRoofs(unittest.TestCase):
    """For each maker the same strings with and without its optimizers: rows 3 m apart (the rows ahead shade the
    lower cells in winter) and one row alone (no shade)."""

    @classmethod
    def setUpClass(cls):
        from _fixtures import clear_sky_meteo, write_cache
        cls.cache = Path(tempfile.mkdtemp())
        write_cache(clear_sky_meteo(45.5226, 9.03), cls.cache)

    def year(self, maker: str, shaded: bool):
        from meridiana import jobs
        from meridiana.energy import pipeline, plant
        inverter, optimizer, width, wide, _eta = ROOFS[maker]
        size = (width, 10.0, 3.0) if shaded else (wide, 3.5, 6.0)
        plain = roof(inverter, None, *size)
        results, _keys, _laid = jobs.layout_of(plain)
        strings = plant.touched({}, plant.propose(plain, results))    # within the inverter's own window
        out = {}
        for with_optimizers in (True, False):
            p = roof(inverter, optimizer if with_optimizers else None, *size)
            p.energy["strings"] = copy.deepcopy(strings)
            results, _keys, _laid = jobs.layout_of(p)
            out[with_optimizers] = pipeline.compute(p, results, self.cache, fetch=False)
        return out

    def check(self, maker: str):
        eta = ROOFS[maker][4]
        shade = self.year(maker, True)
        clear = self.year(maker, False)
        for out in (shade[True], clear[True]):
            self.assertTrue(out.plant.strings)
            self.assertIn("optimizers", [c.key for c in out.sim.chain])
            step = out.sim.record.find("s1.0.optimizers")
            self.assertNotIn(r"U_{string}", [q.symbol for q in step.inputs])
            self.assertFalse([c for s in out.plant.strings for c in s.plan.checks if c.key == "mlpe_energy"])
        gain = shade[True].sim.energy_kwh / shade[False].sim.energy_kwh
        same = clear[True].sim.energy_kwh / clear[False].sim.energy_kwh
        self.assertGreater(gain, 1.04, maker)
        # without shade: the efficiency lost, the 1 % mismatch between modules taken away (losses.mismatch)
        self.assertAlmostEqual(same, eta / 0.99, delta=0.001, msg=maker)
        return gain, same

    def test_huawei(self):
        gain, same = self.check("Huawei")           # 06/11/2026: +6.27 % in the shade, -0.02 % in the sun

    def test_tigo(self):
        gain, same = self.check("Tigo")             # +7.24 % and +0.60 % (99.6 %, the only efficiency printed)

    def test_sungrow(self):
        gain, same = self.check("Sungrow")          # +6.26 % and -0.02 %


if __name__ == "__main__":
    unittest.main()
