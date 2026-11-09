"""Optimizers on some modules only (R456, Daniel's answer 6 of 06/11/2026: «sì, parziale più avanti, Meridio deve
saperlo»): the modules named in energy["strings"]["optimized"] carry the optimizer of their inverter, the others none.
The makers' rules of partial use (optimizer_rules.json, «partial»; energy/optimizer_strings.partial_checks), each with
its document and page; the year of a string with the two kinds of module (electrical_network.mixed_curve); the choice
of the modules in the obstacles' shadow (plant.shaded_keys); SolarEdge never."""
import copy
import tempfile
import unittest
from pathlib import Path

import _setup  # noqa: F401
from meridiana import catalog, jobs, model
from meridiana.energy import optimizer_strings, pipeline, plant


def record(kind: str, maker: str, name: str) -> dict:
    return next(r for r in catalog.search(kind, manufacturer=maker, limit=None) if r["model"] == name)


def setup(maker: str, name: str, inverter=("Huawei", "SUN2000-10KTL-M1")):
    return optimizer_strings.setup({"optimizer": record("optimizers", maker, name)}, record("inverters", *inverter))


class TheRules(unittest.TestCase):
    """partial_checks for each family, with the level and the document of the data file."""

    def levels(self, s, **kw):
        args = dict(n=12, k=3, planes=1, parallel=1) | kw
        return {c.key: c.level for c in optimizer_strings.partial_checks(s, **args)}, \
            optimizer_strings.partial_checks(s, **args)[0].source

    def test_huawei_sun2000_p_anywhere_in_one_orientation_sized_as_without(self):
        s = setup("Huawei", "SUN2000-450W-P2")
        levels, source = self.levels(s)
        self.assertEqual(levels, {"mlpe_partial": "info"})
        self.assertIn("10/11/2025, p. 11", source)
        self.assertIn("15/07/2026, p. 10", source)
        self.assertEqual(self.levels(s, planes=2)[0]["mlpe_partial_planes"], "fail")
        self.assertEqual(self.levels(s, parallel=2)[0]["mlpe_partial_parallel"], "warn")

    def test_tigo_ts4_o_on_its_own_mppt_and_one_plane(self):
        s = setup("Tigo", "TS4-A-O", ("SMA", "STP10.0-3SE-40"))
        levels, source = self.levels(s, parallel=2, planes=2)
        self.assertEqual(levels, {"mlpe_partial": "info", "mlpe_partial_planes": "fail", "mlpe_partial_parallel": "fail"})
        self.assertIn("tigoenergy.com", source)

    def test_merc_is_to_be_confirmed_sungrow_not_said_tigo_rapid_shutdown_never(self):
        merc = self.levels(setup("Huawei", "MERC-1300W-P"))
        self.assertEqual(merc[0], {"mlpe_partial": "warn"})
        self.assertIn("nota 8", merc[1])
        detail = optimizer_strings.partial_checks(setup("Huawei", "MERC-1300W-P"), 12, 3, 1, 1)[0].detail
        self.assertIn("06/11/2026", detail)
        self.assertEqual(self.levels(setup("Sungrow", "SP600S", ("Sungrow", "SG6.0RS")))[0], {"mlpe_partial": "warn"})
        self.assertEqual(self.levels(setup("Tigo", "TS4-A-F (versione 20 A Isc)", ("SMA", "STP10.0-3SE-40")))[0], {"mlpe_partial": "fail"})


def roof(optimizer=None, keys=None, obstacle=False):
    """9 x 10 m of flat roof at Rho, rows at 30° 3 m apart (the rows ahead shade the lower cells in winter), on a
    SUN2000-10KTL-M1; with `obstacle` a 2 m chimney in the middle."""
    p = model.Project(name="Prova")
    p.site = model.Site(lat=45.5226, lon=9.0300, address="Rho (MI)")
    p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[[0, 0], [11, 0], [11, 12], [0, 12]],
                                      height=6.0))
    p.subfields.append(model.SubField(id="s1", name="Sud", ring=[[1, 1], [10, 1], [10, 11], [1, 11]], building="b1",
                                      params={"tilt": 30.0, "pitch_mode": "value", "pitch": 3.0}, filled=True))
    if obstacle:
        p.exclusions.append(model.ExclusionItem(id="e1", ring=[[5, 5.6], [6, 5.6], [6, 6.4], [5, 6.4]], kind="chimney",
                                                building="b1", height=2.0))
    entry = {"record": record("inverters", "Huawei", "SUN2000-10KTL-M1"), "count": 1, "name": ""}
    if optimizer:
        entry["optimizer"] = record("optimizers", *optimizer)
    p.energy["inverters"] = [entry]
    return p


class TheYear(unittest.TestCase):
    """The same strings with no optimizer, with one on the modules in the shade of the rows ahead only, and on every
    module (SUN2000-450W-P2): partial use gains most of what the full one gains."""

    @classmethod
    def setUpClass(cls):
        from _fixtures import clear_sky_meteo, write_cache
        cls.cache = Path(tempfile.mkdtemp())
        write_cache(clear_sky_meteo(45.5226, 9.03), cls.cache)
        p = roof()
        results, _keys, _laid = jobs.layout_of(p)
        cls.strings = plant.touched({}, plant.propose(p, results))
        front = min(m.row for m in results["s1"].modules)
        cls.shaded = [f"s1/{m.key}" for m in results["s1"].modules if m.row != front]
        cls.all = [f"s1/{m.key}" for m in results["s1"].modules]

    def year(self, optimizer, keys=None):
        p = roof(optimizer)
        p.energy["strings"] = copy.deepcopy(self.strings)
        if keys is not None:
            plant.set_optimized(p.energy, keys)
        results, _keys, _laid = jobs.layout_of(p)
        return pipeline.compute(p, results, self.cache, fetch=False)

    def test_partial_between_none_and_full(self):
        p2 = ("Huawei", "SUN2000-450W-P2")
        none, part, full = self.year(None), self.year(p2, self.shaded), self.year(p2)
        self.assertTrue(self.shaded and len(self.shaded) < len(self.all))
        self.assertLess(none.sim.energy_kwh, part.sim.energy_kwh)
        self.assertLessEqual(part.sim.energy_kwh, full.sim.energy_kwh * 1.002)
        on = [s for s in part.plant.strings if s.optimized]
        self.assertTrue(on)
        self.assertEqual(sum(len(s.optimized) for s in part.plant.strings), len(self.shaded))
        self.assertIn("mlpe_partial", {c.key for s in on for c in s.plan.checks})
        print(f"\nR456 parziale: senza {none.sim.energy_kwh:.1f} kWh, sui {len(self.shaded)} moduli in ombra "
              f"{part.sim.energy_kwh:.1f} kWh, su tutti i {len(self.all)} {full.sim.energy_kwh:.1f} kWh")

    def test_every_module_named_is_the_full_case_to_the_last_digit(self):
        p2 = ("Huawei", "SUN2000-450W-P2")
        full = self.year(p2)
        named = self.year(p2, self.all)
        self.assertAlmostEqual(named.sim.energy_kwh, full.sim.energy_kwh, delta=0.002 * full.sim.energy_kwh)


class TheChoice(unittest.TestCase):

    def test_the_modules_in_the_obstacles_shadow(self):
        p = roof(("Huawei", "SUN2000-450W-P2"), obstacle=True)
        results, _keys, _laid = jobs.layout_of(p)
        shaded = plant.shaded_keys(p, results)
        self.assertTrue(0 < len(shaded) < len(results["s1"].modules), len(shaded))
        p.energy["strings"] = plant.touched({}, plant.propose(p, results))
        keys, text = plant.optimized_after(p, results, shaded, True, only=True)
        self.assertEqual(set(keys), set(shaded))
        self.assertTrue(text)
        plant.set_optimized(p.energy, keys)
        # taking one off, then putting it back where every module has one: the plain case again, nothing written
        keys, _text = plant.optimized_after(p, results, shaded[:1], False)
        self.assertEqual(len(keys), len(shaded) - 1)

    def test_solaredge_never(self):
        p = roof()
        p.energy["inverters"] = [{"record": record("inverters", "SolarEdge", "SE10K"), "count": 1, "name": "",
                                  "optimizer": record("optimizers", "SolarEdge", "S440")}]
        results, _keys, _laid = jobs.layout_of(p)
        p.energy["strings"] = plant.touched({}, plant.propose(p, results))
        some = [f"s1/{m.key}" for m in results["s1"].modules][:3]
        keys, text = plant.optimized_after(p, results, some, False)
        self.assertIsNone(keys)
        self.assertIn("does not admit", text)
        plant.set_optimized(p.energy, some)
        built = plant.build(p, results)
        failed = [c for s in built.strings for c in s.plan.checks if c.key == "mlpe_partial"]
        self.assertTrue(failed and all(c.level == "fail" and "DS-000105-IT p. 3" in c.source for c in failed))


if __name__ == "__main__":
    unittest.main()
