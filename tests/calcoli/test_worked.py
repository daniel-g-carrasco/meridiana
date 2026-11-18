"""The formulas written again with the numbers (R479, energy/worked.py): for every step of the shed of the tests, the
result written at the end of each line is the value the calculation used in the hour of the example (or in the
year), the numbers of the line give that result, and a result of one step is carried to the next with the same
number. Two sheds: the plant with its electrical network (an inverter, a string), and the year of simulate with a
horizon, the tilted rows and the obstacles of the roof."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import _setup  # noqa: F401
from _fixtures import capannone, capannone_rho, clear_sky_meteo, inverter_record, write_cache

from meridiana import jobs
from meridiana.energy import pipeline, pvgis, system, worked
from meridiana.energy.components import InverterSpec
from meridiana.energy.meteo import Horizon
from meridiana.energy.pedigree import Source
from meridiana.energy.simulate import Losses, simulate
from meridiana.report_typst.steps import for_window, numbered


def calc_value(sim, of: list, hour):
    """Where the calculation keeps the value a line shows, in the line's unit."""
    first = sim.parts
    arrays = {ap.a.key: ap for ap in first.per_array}
    years = {d["key"]: d for d in sim.arrays}
    inv = sim.example["inverter"]
    kind = of[0]
    if kind == "sun":
        return 90.0 - first.sun_el[hour] if of[1] == "zenith" else first.sun_az[hour]
    if kind == "array":
        return getattr(arrays[of[1]], of[2])[hour]
    if kind == "shaded":
        return 100.0 * arrays[of[1]].shaded[hour]
    if kind == "year":
        return 100.0 * years[of[1]][of[2]]
    if kind == "module25":
        ap = arrays[of[1]]
        return ap.p_25[hour] / ap.a.generating_modules
    if kind == "stage":
        return sim.stages[of[1]][of[2]][hour] / 1000.0
    if kind == "optimizer":
        o = years[of[1]]["optimizers"]
        return o["mismatch"] if of[2] == "mismatch" else 100.0 * (1 - (1 - o["loss"]) * (1 - o["cut"]))
    if kind == "inverter":
        return inv[of[1]][hour] / 1000.0
    if kind == "inverter_zeta":
        return inv["p_dc"][hour] / (inv["pac"] / inv["eta"])
    if kind == "inverter_eta":
        return 100.0 * inv["p_raw"][hour] / inv["p_dc"][hour]
    if kind == "energy":
        return sim.energy_kwh
    if kind == "pr":
        return 100.0 * sim.pr
    if kind == "network_mpp":
        return sum(s["p_el"][hour] for s in sim.stages.values()) / 1000.0
    raise AssertionError(f"unknown {of}")


class Coherence:
    """The checks, for a Simulation in `self.sim`."""

    def check_steps(self):
        sim = self.sim
        formulas = [s for s in sim.record.steps if s.formula]
        self.assertGreater(len(formulas), 8)
        for step in formulas:
            with self.subTest(step=step.key):
                self.assertTrue(step.worked, "a formula without its numbers")
                self.assertTrue(step.proof, "a line without its proof")
                self.assertTrue(step.example)
                for p in step.proof:
                    line = step.worked[p["line"]]
                    shown = worked.V(p["shown"], p["decimals"]).digits()
                    self.assertIn(shown, line.rsplit("=", 1)[-1], line)
                    value = float(calc_value(sim, p["of"], p["hour"]))
                    self.assertLessEqual(abs(p["shown"] - value), 0.5 * 10 ** -p["decimals"] + 1e-9 * abs(value),
                                         f"{step.key}: {line} against {value}")
                    if p["expr"]:
                        got = worked.evaluate(p["expr"], p["env"]) * (100.0 if p["percent"] else 1.0)
                        tolerance = 3 * 10 ** -p["decimals"] + 0.003 * abs(p["shown"])
                        self.assertLessEqual(abs(got - p["shown"]), tolerance, f"{step.key}: {line} gives {got}")
                    if p["hour"] is not None and p["hour"] != sim.example["hour"]:
                        mine = next(ap for ap in sim.parts.per_array if step.key.startswith(ap.a.key + "."))
                        self.assertEqual(p["hour"], mine.example["hour"])

    def check_chain(self):
        """A step's result goes into the next with the number it was written with."""
        rec = self.sim.record

        def last(key):
            return rec.find(key).proof[-1]["shown"]

        for ap in self.sim.parts.per_array:
            k = ap.a.key
            with self.subTest(array=k):
                light = last(f"{k}.far") if rec.find(f"{k}.far") else last(f"{k}.poa")
                temperature = rec.find(f"{k}.temperature").proof[-1]["env"]
                self.assertEqual(temperature["g"], light)
                self.assertEqual(rec.find(f"{k}.soiling").proof[-1]["env"]["g"], last(f"{k}.iam"))
                module = rec.find(f"{k}.module").proof[-1]["env"]
                self.assertEqual(module["tc"], last(f"{k}.temperature"))
                self.assertEqual(rec.find(f"{k}.array").proof[0]["env"]["p"], last(f"{k}.module"))
                hour = ap.example["hour"]
                self.assertEqual(hour, int(np.argmax(ap.g_inc)))

    def check_views(self):
        """The report's block and the window's carry the lines; the list «symbol = value» is gone."""
        blocks = numbered([self.sim.record])[0]
        from meridiana.energy.pedigree import Record   # noqa: F401
        plain = [{"title": self.sim.record.title,
                  "steps": [dict(key=s.key, title=s.title, formula=s.formula, explanation=s.explanation,
                                 inputs=[], result=None, reference=s.reference, worked=s.worked, example=s.example,
                                 proof=s.proof) for s in self.sim.record.steps]}]
        window = for_window(plain)[0]
        for b, v, s in zip(blocks, window, self.sim.record.steps, strict=True):
            self.assertNotIn("values", b)
            self.assertEqual(b["worked"], s.worked if s.formula else [])
            self.assertEqual(v["worked"], b["worked"])
            self.assertEqual(v["example"], b["example"])


class NetworkShed(Coherence, unittest.TestCase):
    """The shed with one inverter and a string of eight modules: the connected electrical network."""

    @classmethod
    def setUpClass(cls):
        temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temp.cleanup)
        cache = Path(temp.name)
        write_cache(clear_sky_meteo(45.5226, 9.03), cache)
        project = capannone()
        layouts = jobs.layout_of(project)[0]
        keys = [f"s1/{pm.key}" for pm in layouts["s1"].modules[:8]]
        project.energy = {"inverters": [{"record": inverter_record(), "count": 1}],
                          "losses": {"use_horizon": False, "use_near": False},
                          "strings": {"runs": [{"inverter": 1, "mppt": 1, "modules": keys}]}}

        def estimate(_lat, _lon, peak_kw, *_args, **_kwargs):
            return pvgis.PVGISEstimate(peak_kw * 1000, [peak_kw * 1000 / 12] * 12, 0, Source("computed", "synthetic"))
        with mock.patch.object(pvgis, "pvcalc", side_effect=estimate):
            cls.sim = pipeline.compute(project, layouts, cache, fetch=False).sim

    def test_every_step_shows_the_numbers_of_the_calculation(self):
        self.assertIsNotNone(self.sim.record.find("electrical_network"))
        self.check_steps()

    def test_results_carried_with_the_same_number(self):
        self.check_chain()
        np.testing.assert_allclose(self.sim.hourly.p_dc.to_numpy(), self.sim.inverters[0]["p_dc"])

    def test_views(self):
        self.check_views()


class ShadedShed(Coherence, unittest.TestCase):
    """The shed of the fire brigade's tests, laid, with a horizon, its rows two modules high and the obstacles of
    its roof; the year of simulate without the network."""

    @classmethod
    def setUpClass(cls):
        project = capannone_rho()
        project.subfields[0].filled = True
        layouts = jobs.layout_of(project)[0]
        arrays = system.arrays_of(project, layouts)
        horizon = Horizon(np.array([0.0, 90.0, 180.0, 270.0]), np.array([4.0, 8.0, 3.0, 12.0]), Source("input", "hills"))
        cls.sim = simulate(clear_sky_meteo(), arrays, InverterSpec.sized_for(sum(a.p_stc for a in arrays)),
                           Losses(), horizon)

    def test_every_step_shows_the_numbers_of_the_calculation(self):
        keys = {s.key.rsplit(".", 1)[-1] for s in self.sim.record.steps}
        self.assertLessEqual({"far", "rows", "obstacles", "iam", "temperature", "module", "array"}, keys)
        self.check_steps()

    def test_results_carried_with_the_same_number(self):
        self.check_chain()
        total = sum(s["p_dc"] for s in self.sim.stages.values())
        np.testing.assert_allclose(total, self.sim.hourly.p_dc.to_numpy())

    def test_the_shadings_come_in_the_lights_order(self):
        keys = [s.key.rsplit(".", 1)[-1] for s in self.sim.record.steps if "." in s.key]
        self.assertLess(keys.index("far"), keys.index("rows"))
        self.assertLess(keys.index("obstacles"), keys.index("iam"))

    def test_views(self):
        self.check_views()


if __name__ == "__main__":
    unittest.main()
