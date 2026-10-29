"""Only modules wired to an existing inverter input can deliver energy to the meter."""

import dataclasses
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest import mock

import numpy as np
import _setup  # noqa: F401
from _fixtures import capannone, clear_sky_meteo, inverter_record, write_cache

from meridiana import jobs, session
from meridiana.energy import pipeline, pvgis, system
from meridiana.energy.pedigree import Source
from meridiana.energy.simulate import ArrayOptimizers, Optimizers, simulate


class ConnectedProduction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.cache = Path(cls.temp.name)
        cls.weather = clear_sky_meteo(45.5226, 9.03)
        write_cache(cls.weather, cls.cache)

    def setUp(self):
        self.project = capannone()
        self.project.energy = {"inverters": [{"record": inverter_record(), "count": 1}],
                               "losses": {"use_horizon": False, "use_near": False}, "strings": {"runs": []}}
        self.layouts = jobs.layout_of(self.project)[0]
        self.keys = [f"s1/{pm.key}" for pm in self.layouts["s1"].modules[:8]]

    def compute(self):
        def estimate(_lat, _lon, peak_kw, *_args, **_kwargs):
            return pvgis.PVGISEstimate(peak_kw * 1000, [peak_kw * 1000 / 12] * 12, 0,
                                       Source("computed", "synthetic reference"))
        with mock.patch.object(pvgis, "pvcalc", side_effect=estimate) as remote:
            result = pipeline.compute(self.project, self.layouts, self.cache, fetch=False)
        return result, remote

    def test_unconnected_modules_never_reach_dc_ac_monthly_or_economics(self):
        for unit, mppt, keys in ((1, 1, []), (99, 1, self.keys), (1, 99, self.keys)):
            with self.subTest(unit=unit, mppt=mppt, keys=bool(keys)):
                self.project.energy["strings"]["runs"] = [{"inverter": unit, "mppt": mppt, "modules": keys}]
                with warnings.catch_warnings():
                    warnings.simplefilter("error", RuntimeWarning)
                    out, remote = self.compute()
                self.assertIsNone(out.error_sim)
                self.assertEqual(out.sim.energy_kwh, 0)
                self.assertTrue((out.sim.hourly[["p_dc", "p_ac", "e_kwh"]] == 0).all().all())
                self.assertTrue((out.sim.monthly[["e_dc", "e_ac"]] == 0).all().all())
                self.assertEqual(out.pvgis.yearly_kwh, 0)
                self.assertEqual(out.econ.kpi["production"], 0)
                remote.assert_not_called()

    def test_partial_connection_matches_the_connected_modules_before_inverter_clipping(self):
        self.project.energy["strings"]["runs"] = [{"inverter": 1, "mppt": 1, "modules": self.keys}]
        out, remote = self.compute()
        array = system.arrays_of(self.project, self.layouts)[0]
        connected = dataclasses.replace(array, modules=8, placed=array.placed[:8])
        expected = simulate(self.weather, [connected], system.inverters_of(self.project, connected.p_stc)[0],
                            system.losses_of(self.project))
        np.testing.assert_allclose(out.sim.hourly.p_dc, expected.hourly.p_dc, rtol=1e-8, atol=1e-8)
        np.testing.assert_allclose(out.sim.hourly.p_ac, expected.hourly.p_ac, rtol=1e-8, atol=1e-8)
        self.assertGreater(out.sim.energy_kwh, 0)
        self.assertEqual(remote.call_args.args[2], connected.p_stc / 1000)
        self.assertEqual(out.sim.p_stc_kw, array.p_stc / 1000)  # installed capacity still costs money

    def test_duplicate_module_references_do_not_generate_twice(self):
        run = {"inverter": 1, "mppt": 1, "modules": self.keys}
        self.project.energy["strings"]["runs"] = [run]
        original, _ = self.compute()
        self.project.energy["strings"]["runs"] = [dict(run, modules=self.keys * 2), run]
        duplicated, _ = self.compute()
        np.testing.assert_array_equal(original.sim.hourly.e_kwh, duplicated.sim.hourly.e_kwh)

    def test_an_inverter_sized_as_a_placeholder_is_not_an_actual_connection(self):
        self.project.energy.pop("inverters")
        self.project.energy["strings"]["runs"] = [{"inverter": 1, "mppt": 1, "modules": self.keys}]
        out, _ = self.compute()
        self.assertEqual(out.sim.energy_kwh, 0)

    def test_deleting_a_string_invalidates_the_previous_year(self):
        self.project.energy["strings"]["runs"] = [{"inverter": 1, "mppt": 1, "modules": self.keys}]
        work = session.ProjectSession(self.project)
        generation = work.energy_asked()
        work.energy_done(generation, {"sim": object()})
        self.assertFalse(work.energy_stale())
        self.project.energy["strings"]["runs"] = []
        self.assertTrue(work.energy_stale())

    def test_fully_connected_plant_keeps_the_previous_hourly_production(self):
        array = system.arrays_of(self.project, self.layouts)[0]
        self.project.energy["strings"]["runs"] = [{"inverter": 1, "mppt": 1,
                                                   "modules": [f"s1/{pm.key}" for pm in array.placed]}]
        out, _ = self.compute()
        expected = simulate(self.weather, [array], system.inverters_of(self.project, array.p_stc)[0],
                            system.losses_of(self.project))
        np.testing.assert_array_equal(out.sim.hourly.e_kwh, expected.hourly.e_kwh)

    def test_an_unused_inverter_cannot_absorb_the_active_inverters_clipping(self):
        self.project.energy["inverters"][0]["record"]["ac_power_nominal_w"] = 2000
        self.project.energy["strings"]["runs"] = [{"inverter": 1, "mppt": 1, "modules": self.keys}]
        before, _ = self.compute()
        self.project.energy["inverters"].append({"record": inverter_record(), "count": 1})
        after, _ = self.compute()
        np.testing.assert_array_equal(before.sim.hourly.e_kwh, after.sim.hourly.e_kwh)
        self.assertEqual(after.sim.p_ac_kw, 2)

    def test_optimizer_string_power_uses_only_the_generating_modules(self):
        array = system.arrays_of(self.project, self.layouts)[0]
        wired = frozenset(pm.key for pm in array.placed[:8])
        limited = dataclasses.replace(array, connected=wired)
        reference = dataclasses.replace(array, modules=8, placed=array.placed[:8])
        inv = system.inverters_of(self.project, array.p_stc)[0]
        losses = system.losses_of(self.project)
        opts = Optimizers(arrays={array.key: ArrayOptimizers(share=1, single=1, eta=0.99,
                                                           v_string=750, name="Test", source=Source("data", "Test"))},
                          strings=[({array.key: 8}, 1000)])
        actual = simulate(self.weather, [limited], inv, losses, optimizers=opts)
        expected = simulate(self.weather, [reference], inv, losses, optimizers=opts)
        np.testing.assert_allclose(actual.hourly.p_dc, expected.hourly.p_dc, rtol=1e-8, atol=1e-8)

        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            disconnected = simulate(self.weather, [dataclasses.replace(array, connected=frozenset())],
                                    inv, losses, optimizers=opts)
        self.assertEqual(disconnected.energy_kwh, 0)
        self.assertTrue(np.isfinite(disconnected.hourly.p_dc).all())
