"""A string over more than one roof face (R433, Daniel's choice of 05/11/2026): first its own face; in the same building
with optimizers the proposal goes on over another face only when needed, with a warning; without optimizers only when
the designer asks, with the estimate of what the exposures cost; between buildings only by hand. The estimate of
energy/faces.py against the year of the electrical network: a capannone with two faces, East and West at 15°, the same
modules in one string over both faces or in two strings, one a face."""
import copy
import tempfile
import unittest
from pathlib import Path

import numpy as np

import _setup  # noqa: F401
from meridiana import catalog, jobs, model
from meridiana.energy import faces, pipeline, plant

M1 = ("Huawei", "SUN2000-10KTL-M1")         # 2 MPPT, one input each
P2 = ("Huawei", "SUN2000-450W-P2")


def record(kind: str, maker: str, name: str) -> dict:
    return next(r for r in catalog.search(kind, manufacturer=maker, limit=None) if r["model"] == name)


def capannone(span: float, optimizer=None, across: bool = False, two_buildings: bool = False) -> model.Project:
    """A 10 x 14 m capannone with a gable roof at 15°, its ridge North-South: a sub-field on each face, `span` metres
    along the ridge (the West pitch is side 3, the East one side 1)."""
    p = model.Project(name="Capannone a due falde")
    p.site = model.Site(lat=45.5226, lon=9.0300, address="Rho (MI)")
    for b in ("b1", "b2") if two_buildings else ("b1",):
        dx = 20.0 if b == "b2" else 0.0
        p.buildings.append(model.Building(id=b, name="Capannone" if b == "b1" else "Magazzino",
                                          footprint=[[dx, 0], [dx + 10, 0], [dx + 10, 14], [dx, 14]], height=6.0,
                                          roof=model.Roof(type="gable", tilt=15.0)))
    rings = [("s0", "b1", 3, 0.0), ("s1", "b2" if two_buildings else "b1", 1, 20.0 if two_buildings else 0.0)]
    for sfid, b, side, dx in rings:
        x0, x1 = (dx + 0.4, dx + 4.6) if side == 3 else (dx + 5.4, dx + 9.6)
        p.subfields.append(model.SubField(id=sfid, name="Ovest" if side == 3 else "Est",
                                          ring=[[x0, 0.4], [x1, 0.4], [x1, 0.4 + span], [x0, 0.4 + span]],
                                          building=b, pitch=side, params={"mounting": "coplanar"}, filled=True))
    entry = {"record": record("inverters", *M1), "count": 1, "name": ""}
    if optimizer:
        entry["optimizer"] = record("optimizers", *optimizer)
    p.energy["inverters"] = [entry]
    if across:
        p.energy["strings"] = {plant.ACROSS: True}
    return p


class TheEstimate(unittest.TestCase):
    """faces.exposure_loss on made-up hours."""

    def test_one_plane_or_every_module_on_an_optimizer_loses_nothing(self):
        g = np.array([800.0, 400.0, 0.0])
        self.assertEqual(faces.exposure_loss([(g, 10, False)]), 0.0)
        self.assertEqual(faces.exposure_loss([(g, 5, True), (g[::-1].copy(), 5, True)]), 0.0)

    def test_the_least_lit_module_holds_the_string_or_is_bypassed(self):
        east, west = np.array([800.0]), np.array([200.0])
        # 3 + 3 modules: all at 200 (1200) or the 3 East at 800 with the West bypassed (2400): 2400 of 3000
        self.assertAlmostEqual(faces.exposure_loss([(east, 3, False), (west, 3, False)]), 0.2)
        # the West on optimizers: 3 x 200 of their own, the East alone at 800: nothing lost
        self.assertAlmostEqual(faces.exposure_loss([(east, 3, False), (west, 3, True)]), 0.0)


class TheProposal(unittest.TestCase):
    """3 modules a face: fewer than the shortest string of the SUN2000-10KTL-M1 (5 without optimizers, 6 with the
    SUN2000-450W-P2 by Huawei's table), so a face alone makes no string."""

    def propose(self, p):
        results, _keys, _laid = jobs.layout_of(p)
        self.assertEqual([len(results[s].modules) for s in ("s0", "s1")], [3, 3])
        return plant.proposal(p, results)

    def test_without_optimizers_the_faces_stay_apart_unless_the_designer_asks(self):
        out = self.propose(capannone(5.4))
        self.assertFalse(out.strings)
        self.assertEqual(len(out.left), 6)
        out = self.propose(capannone(5.4, across=True))
        (s,) = out.strings
        self.assertEqual({sf for sf, _k, _c in s.modules}, {"s0", "s1"})
        (c,) = out.crossings
        self.assertEqual(len(c.faces), 2)
        self.assertGreater(c.loss, 0.05)                    # East and West at 15° on clear sky: about 16 %
        check = next(k for k in s.plan.checks if k.key == faces.KEY)
        self.assertEqual(check.level, "warn")
        self.assertIn("%", check.detail)
        self.assertEqual(s.state, "check")

    def test_with_optimizers_the_string_goes_on_over_the_other_face_by_itself_with_a_warning(self):
        out = self.propose(capannone(5.4, P2))
        (s,) = out.strings
        self.assertEqual(len(s.modules), 6)
        (c,) = out.crossings
        self.assertEqual(c.optimized, 6)
        self.assertEqual(c.loss, 0.0)
        self.assertEqual(next(k for k in s.plan.checks if k.key == faces.KEY).level, "warn")
        self.assertTrue(plant.acceptable(s))

    def test_never_between_two_buildings(self):
        p = capannone(5.4, P2, two_buildings=True)
        results, _keys, _laid = jobs.layout_of(p)
        out = plant.proposal(p, results)
        self.assertFalse(out.strings)
        # by hand it is the designer's choice: said, with the two buildings
        p.energy["strings"] = {"runs": [{"inverter": 1, "mppt": 1, "modules": [
            f"{sf}/{m.key}" for sf in ("s0", "s1") for m in results[sf].modules]}]}
        built = plant.build(p, results)
        (c,) = built.crossings
        self.assertEqual(c.buildings, 2)
        self.assertIn(model.Project.__name__ and "two buildings", faces.detail(c))


class TheYear(unittest.TestCase):
    """The same 12 modules (6 a face) in one string over both faces, or in two strings one a face on the two MPPT of the
    same inverter: the year of the electrical network on the clear sky of the fixtures (the ratios count)."""

    @classmethod
    def setUpClass(cls):
        from _fixtures import clear_sky_meteo, write_cache
        cls.cache = Path(tempfile.mkdtemp())
        write_cache(clear_sky_meteo(45.5226, 9.03), cls.cache)

    def year(self, optimizer, together: bool):
        p = capannone(9.0, optimizer)
        results, _keys, _laid = jobs.layout_of(p)
        west = [f"s0/{m.key}" for m in results["s0"].modules]
        east = [f"s1/{m.key}" for m in results["s1"].modules]
        self.assertEqual((len(west), len(east)), (6, 6))
        runs = ([{"inverter": 1, "mppt": 1, "modules": west + east}] if together else
                [{"inverter": 1, "mppt": 1, "modules": west}, {"inverter": 1, "mppt": 2, "modules": east}])
        p.energy["strings"] = copy.deepcopy({"runs": runs})
        return pipeline.compute(p, results, self.cache, fetch=False)

    def test_without_optimizers_the_string_over_two_faces_loses_about_what_the_estimate_says(self):
        one, two = self.year(None, True), self.year(None, False)
        lost = 1 - one.sim.energy_kwh / two.sim.energy_kwh
        (c,) = one.plant.crossings
        self.assertGreater(lost, 0.03)
        self.assertLess(abs(c.loss - lost), 0.5 * lost, (c.loss, lost))
        self.assertIsNotNone(c.kwh)
        print(f"\nR433 senza ottimizzatori: una stringa {one.sim.energy_kwh:.1f} kWh, due {two.sim.energy_kwh:.1f} kWh, "
              f"perdita {100 * lost:.2f} %, stima {100 * c.loss:.2f} % ({c.kwh:.1f} kWh)")

    def test_with_optimizers_the_string_over_two_faces_holds(self):
        one, two = self.year(P2, True), self.year(P2, False)
        ratio = one.sim.energy_kwh / two.sim.energy_kwh
        self.assertAlmostEqual(ratio, 1.0, delta=0.005)
        (c,) = one.plant.crossings
        self.assertEqual(c.loss, 0.0)
        print(f"\nR433 con ottimizzatori: una stringa {one.sim.energy_kwh:.1f} kWh, due {two.sim.energy_kwh:.1f} kWh, "
              f"rapporto {ratio:.4f}")


if __name__ == "__main__":
    unittest.main()
