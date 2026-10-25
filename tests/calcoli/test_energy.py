"""The production model: the module follows its datasheet, the physics points the right way (South beats
North, a wall of horizon takes the direct light, a small inverter clips), the loss chain adds up to the
energy given, and every formula of the pedigree can be drawn."""

import unittest

import numpy as np

import _setup  # noqa: F401
from _fixtures import clear_sky_meteo

from meridiana import layout
from meridiana.energy import nearshade
from meridiana.energy.components import InverterSpec, ModuleSpec
from meridiana.energy.meteo import Horizon
from meridiana.energy.pedigree import Source
from meridiana.energy.simulate import ArraySpec, Losses, profile_iam, simulate

METEO = clear_sky_meteo()


def module() -> ModuleSpec:
    return ModuleSpec.from_record({"power_kw": 0.45, "length": 2.278, "width": 1.134})


def south(n=20, tilt=30.0, azimuth=0.0, thermal="open") -> ArraySpec:
    return ArraySpec("s1", "Sud", tilt, azimuth, n, module(), thermal)


class Module(unittest.TestCase):
    def test_the_fitted_model_gives_the_datasheet_power_at_stc(self):
        m = module()
        self.assertAlmostEqual(float(m.power_at_25([1000.0])[0]), m.pmax, delta=0.01 * m.pmax)

    def test_the_year_at_once_gives_the_power_of_each_hour_on_its_own(self):
        """The maximum power point found over the whole array at once (chandrupatla) is the one found one
        point at a time (brentq), which took 70 times longer on a year."""
        import numpy as np
        from pvlib.pvsystem import max_power_point
        m = module()
        p = m.sdm()
        self.assertNotIn("linear", p)
        g = np.linspace(5.0, 1100.0, 200)
        il, io, rs, rsh, nnsvth = m.diode_params(g, 25.0)
        one_by_one = np.asarray(max_power_point(il, io, rs, rsh, nnsvth, method="brentq")["p_mp"], dtype=float)
        np.testing.assert_allclose(m.power_at_25(g), one_by_one, rtol=0, atol=1e-6)
        np.testing.assert_allclose(m.current_at_25(g), max_power_point(il, io, rs, rsh, nnsvth, method="brentq")["i_mp"],
                                   rtol=0, atol=1e-6)

    def test_without_a_low_light_datum_the_fit_takes_the_conventional_value_and_says_so(self):
        """Before 23/10/2026 the five De Soto parameters were fitted to the STC point alone and the typical
        module came out at 100.7% at 200 W/m² (an artefact: study 18, B-calcoli 6.1); now the fit is held
        to LOW_LIGHT_DEFAULT (97.5%) and the pedigree says the value is conventional."""
        from meridiana.energy.components import LOW_LIGHT_DEFAULT
        m = module()
        p = m.sdm()
        self.assertEqual((p["form"], p["origin"], p["low_light_from"]), ("pvsyst", "fit", "default"))
        self.assertAlmostEqual(100 * m.low_light_ratio(200.0), LOW_LIGHT_DEFAULT, places=2)
        self.assertTrue(0.88 < m.low_light_ratio(100.0) < 0.97)
        self.assertAlmostEqual(float(m.power_at_25(1000.0)), m.vmp * m.imp, delta=0.01 * m.pmax)
        s = simulate(METEO, [south()])
        step = s.record.find("s1.module")
        low = next(q for q in step.inputs if q.symbol == r"\eta_{200}/\eta_{STC}")
        self.assertEqual((low.value, low.source.kind), (LOW_LIGHT_DEFAULT, "default"))
        self.assertIn("estimate", step.explanation)
        level = next(c for c in s.chain if c.key == "irradiance_level")
        self.assertTrue(-2.5 < level.change < 0.0, level.change)     # a loss, no longer a gain

    def test_the_datasheets_low_light_value_is_met_and_credited(self):
        rec = {"manufacturer": "X", "model": "Y", "pmax": 450, "vmp": 33.6, "imp": 13.4, "voc": 40.1, "isc": 14.1,
               "cells": 108, "length": 2.278, "width": 1.134, "low_light_200": 96.0}
        m = ModuleSpec.from_record(rec)
        self.assertEqual(m.sdm()["low_light_from"], "datasheet")
        self.assertAlmostEqual(100 * m.low_light_ratio(200.0), 96.0, places=2)
        self.assertLess(m.power_at_25(200.0), module().power_at_25(200.0))
        s = simulate(METEO, [ArraySpec("s1", "Sud", 30.0, 0.0, 20, m)])
        low = next(q for q in s.record.find("s1.module").inputs if q.symbol == r"\eta_{200}/\eta_{STC}")
        self.assertEqual((low.value, low.source.kind), (96.0, "data"))

    def test_a_pvsyst_files_one_diode_parameters_drive_the_low_light(self):
        from meridiana.catalog import panond
        rec, said = panond.module(_setup.DATA / "pvsyst" / "ET-M772BH550GL.PAN")
        self.assertEqual(rec["pvsyst_sdm"], {"R_sh_ref": 300.0, "R_sh_0": 2000.0, "R_sh_exp": 5.5, "R_s": 0.203,
                                             "gamma_ref": 0.98, "mu_gamma": -0.0001})
        self.assertTrue(any("300" in s and "0.203" in s for s in said))
        m = ModuleSpec.from_record(rec)
        p = m.sdm()
        self.assertEqual((p["form"], p["origin"], p["R_sh_ref"], p["R_sh_0"], p["gamma_ref"]), ("pvsyst", "pan", 300.0, 2000.0, 0.98))
        self.assertAlmostEqual(float(m.power_at_25(1000.0)), 550.0, delta=550.0 * 0.02)
        self.assertTrue(0.93 < m.low_light_ratio(200.0) < 1.0, m.low_light_ratio(200.0))
        s = simulate(METEO, [ArraySpec("s1", "Sud", 30.0, 0.0, 20, m)])
        step = s.record.find("s1.module")
        self.assertEqual(next(q for q in step.inputs if q.symbol == "R_{sh}").source.kind, "data")
        self.assertNotIn("estimate", step.explanation)
        # the same file without its one-diode parameters falls back on the datasheet fit
        plain = ModuleSpec.from_record({k: v for k, v in rec.items() if k != "pvsyst_sdm"})
        self.assertEqual(plain.sdm()["origin"], "fit")

    def test_an_impossible_datasheet_falls_back_on_the_linear_model_and_says_so(self):
        m = ModuleSpec.from_record({"manufacturer": "X", "model": "Y", "pmax": 450, "vmp": 43.6, "imp": 13.4,
                                    "voc": 40.1, "isc": 14.1, "cells": 108, "length": 2.278, "width": 1.134})
        self.assertTrue(m.sdm().get("linear"))
        self.assertEqual(float(m.power_at_25(500.0)), 225.0)
        self.assertEqual(float(m.current_at_25(500.0)), 6.7)
        s = simulate(METEO, [ArraySpec("s1", "Sud", 30.0, 0.0, 20, m)])
        self.assertIn("proportional", s.record.find("s1.module").explanation)
        self.assertAlmostEqual(next(c for c in s.chain if c.key == "irradiance_level").change, 0.0, places=9)

    def test_a_cells_count_that_contradicts_the_voc_is_not_trusted(self):
        """The CEC list gives 24 cells in series for the Jinko JKM540M-72HL4-TV (Voc 49.49 V) and 22 for the
        Risen RSM132-8-660BMDG (Voc 45.89 V): the cells of a sub-string. Trusted, they made the fit fail and
        the module linear (study 18, B-pvsyst 6.7)."""
        jinko = ModuleSpec.from_record({"manufacturer": "Jinko", "model": "JKM540M-72HL4-TV", "pmax": 540, "vmp": 40.91,
                                        "imp": 13.2, "voc": 49.49, "isc": 13.87, "cells_in_series": 24})
        risen = ModuleSpec.from_record({"manufacturer": "Risen", "model": "RSM132-8-660BMDG", "pmax": 660, "vmp": 37.9,
                                        "imp": 17.42, "voc": 45.89, "isc": 18.47, "cells_in_series": 22})
        self.assertEqual((jinko.cells_in_series, risen.cells_in_series), (72, 66))
        self.assertFalse(jinko.sdm().get("linear"))
        coherent = ModuleSpec.from_record({"manufacturer": "X", "model": "Y", "pmax": 415, "vmp": 31.56, "imp": 13.15,
                                           "voc": 37.07, "isc": 13.9, "cells": 108, "cells_in_series": 54})
        self.assertEqual(coherent.cells_in_series, 54)

    def test_quarter_cells_are_counted_by_four(self):
        # Jinko JKM475N-48QL6-DB: 192 quarter-cut cells, Voc 36.44 V
        q = ModuleSpec.from_record({"manufacturer": "Jinko", "model": "JKM475N-48QL6-DB", "pmax": 475, "vmp": 31.13,
                                    "imp": 15.26, "voc": 36.44, "isc": 15.85, "cells": 192, "length": 1.762,
                                    "width": 1.134})
        self.assertEqual(q.cells_in_series, 48)

    def test_half_cells_are_counted_in_pairs(self):
        self.assertEqual(module().cells_in_series, 54)
        full = ModuleSpec.from_record({"manufacturer": "X", "model": "Y", "pmax": 270, "vmp": 31.0, "imp": 8.71,
                                       "voc": 38.4, "isc": 9.26, "cells": 60, "length": 1.65, "width": 0.99})
        self.assertEqual(full.cells_in_series, 60)

    def test_a_datasheet_module_says_where_its_values_come_from(self):
        m = ModuleSpec.from_record({"manufacturer": "Acme", "model": "AC-450", "pmax_w": 450, "vmp": 33.6,
                                    "imp": 13.4, "voc": 40.1, "isc": 14.1, "temp_coeff_pmax_pct_c": -0.29,
                                    "cells": 108, "length_mm": 1762, "width_mm": 1134,
                                    "datasheet_url": "https://example.org/ac450.pdf"})
        self.assertEqual(m.source.kind, "data")
        self.assertAlmostEqual(m.length, 1.762)
        self.assertAlmostEqual(m.gamma_pmax, -0.29)
        self.assertEqual(module().source.kind, "default")


class Physics(unittest.TestCase):
    def test_south_beats_north(self):
        s = simulate(METEO, [south()])
        n = simulate(METEO, [south(azimuth=180.0)])
        self.assertGreater(s.energy_kwh, 1.3 * n.energy_kwh)

    def test_the_performance_ratio_is_plausible(self):
        # bounds of plausibility chosen by hand, not a standard: the synthetic year of _energy is not a climate
        # (the numbers of a real site are compared with PVsyst in docs/studio/18-prove/B-pvsyst.md)
        s = simulate(METEO, [south()])
        self.assertTrue(0.70 < s.pr < 0.92, s.pr)
        self.assertTrue(900 < s.specific_yield < 2000, s.specific_yield)

    def test_a_wall_of_horizon_takes_the_direct_light(self):
        wall = Horizon(np.array([0.0, 90.0, 180.0, 270.0]), np.full(4, 89.0), Source("input", "wall"))
        s = simulate(METEO, [south()], horizon=wall)
        far = next(c for c in s.chain if c.key == "far")
        self.assertLess(far.change, -40.0)
        free = simulate(METEO, [south()], horizon=Horizon.flat())
        self.assertAlmostEqual(next(c for c in free.chain if c.key == "far").change, 0.0, places=6)

    def test_the_horizon_also_dims_the_light_reflected_by_the_ground(self):
        """PVsyst's albedo factor: the ground's light fades linearly with the horizon's height and is gone at
        20° (Montescaglioso prints 0.86 with a diffuse factor of 0.99; study 18, B-pvsyst 6.8); before
        23/10/2026 the ground part was left whole."""
        def wall(h):
            return Horizon(np.array([0.0, 90.0, 180.0, 270.0]), np.full(4, h), Source("input", "wall"))

        def kept(hor):
            s = simulate(METEO, [south()], horizon=hor)
            return next(q for q in s.record.find("s1.far").inputs if q.symbol == r"f_{alb}").value
        self.assertAlmostEqual(kept(Horizon.flat()), 100.0, places=6)
        self.assertAlmostEqual(kept(wall(10.0)), 50.0, places=3)
        self.assertAlmostEqual(kept(wall(30.0)), 0.0, places=6)
        free, dimmed = simulate(METEO, [south()], horizon=Horizon.flat()), simulate(METEO, [south()], horizon=wall(10.0))
        poa_far = {k: next(c for c in s.chain if c.key == "far").value for k, s in (("free", free), ("dim", dimmed))}
        ground = float(METEO.data.ghi.sum() / 1000.0) * 0.20 * (1 - np.cos(np.radians(30.0))) / 2   # kWh/m² reflected
        lost = poa_far["free"] - poa_far["dim"]
        self.assertGreater(lost, 0.5 * ground)                 # half the ground's light, plus the sun below 10°
        self.assertLess(lost, 0.5 * ground + 0.05 * poa_far["free"])
        self.assertAlmostEqual(dimmed.arrays[0]["albedo_seen"], 0.5, places=5)

    def test_the_mountains_hide_their_share_of_the_sky(self):
        # a horizontal plane under a uniform sky: what lies below a wall of height h weighs sin²(h)
        wall = Horizon(np.array([0.0, 90.0, 180.0, 270.0]), np.full(4, 30.0), Source("input", "wall"))
        self.assertAlmostEqual(wall.diffuse_factor(0.0, 180.0), 1 - np.sin(np.radians(30.0)) ** 2, delta=0.005)
        self.assertAlmostEqual(Horizon.flat().diffuse_factor(30.0, 180.0), 1.0, places=6)
        # a plane facing South does not see the mountains behind it
        north = Horizon(np.array([0.0, 60.0, 90.0, 270.0, 300.0]), np.array([30.0, 30.0, 0.0, 0.0, 30.0]),
                        Source("input", "north"))
        self.assertGreater(north.diffuse_factor(60.0, 180.0), north.diffuse_factor(60.0, 0.0))

    def test_rows_close_together_shade_each_other_more(self):
        def rows(pitch):
            a = south(n=40, tilt=25.0)
            a.rows, a.pitch, a.slant = 10, pitch, 2.278
            return simulate(METEO, [a])
        tight, loose = rows(2.6), rows(6.0)
        near_t = next(c for c in tight.chain if c.key == "near").change
        near_l = next(c for c in loose.chain if c.key == "near").change
        self.assertLess(near_t, near_l)
        self.assertLess(near_t, -1.0)
        self.assertGreater(near_l, -2.0)
        self.assertIsNotNone(tight.record.find("s1.rows"))
        flat = simulate(METEO, [south()])
        self.assertAlmostEqual(next(c for c in flat.chain if c.key == "near").change, 0.0, places=9)

    def test_the_row_in_front_hides_sky_and_ground_as_the_view_factors_say(self):
        # Montescaglioso (PVsyst 7.2.11, public report https://va.mite.gov.it/File/Documento/744498, pages 2-10;
        # case 5 of docs/studio/11-pvsyst-casi-di-confronto.md): 20 rows of 2 x 660 W upright, 20°, 4.79 m on
        # 7.50 m; PVsyst's scene hides 4.4% of the diffuse and 76.9% of the light reflected by the ground
        a = south(n=40, tilt=20.0)
        a.rows, a.pitch, a.slant, a.stack = 20, 7.5, 4.79, 2
        s = simulate(METEO, [a])
        step = s.record.find("s1.rows")
        values = {q.symbol: q.value for q in step.inputs}
        self.assertAlmostEqual(values[r"\Delta_d"], 4.50 * 19 / 20, delta=0.05)      # pvlib's 2D view factor
        self.assertGreater(values[r"\Delta_r"], 30.0)
        self.assertLess(values[r"\Delta_r"], 19 / 20 * 100.0)

    def test_an_obstacle_south_of_the_modules_takes_its_share(self):
        roof = [(0.0, 0.0), (14.0, 0.0), (14.0, 8.0), (0.0, 8.0)]
        placed = layout.compute(roof, params=layout.Params(tilt=30.0, pitch_mode="value", pitch=4.0), lat=45.5,
                                lon=9.0).modules

        def run(obstacles, use_near=True):
            a = south(n=len(placed), tilt=30.0)
            a.placed, a.obstacles = placed, obstacles
            return simulate(METEO, [a], losses=Losses(use_near=use_near))
        wall = nearshade.prism([(0.0, -2.0), (14.0, -2.0), (14.0, -1.7), (0.0, -1.7)], 0.0, 3.0, "wall")
        free, shaded, off = run([]), run(wall), run(wall, use_near=False)
        self.assertLess(shaded.energy_kwh, free.energy_kwh * 0.97)
        self.assertAlmostEqual(off.energy_kwh, free.energy_kwh, places=6)
        self.assertLess(next(c for c in shaded.chain if c.key == "near").change, -3.0)
        step = shaded.record.find("s1.obstacles")
        self.assertIsNotNone(step)
        self.assertIn("wall", step.inputs[0].value)
        self.assertGreater(shaded.arrays[0]["obstacle_shading"], 0.03)
        self.assertEqual(free.arrays[0]["obstacle_shading"], 0.0)
        # laid in strings, the shade costs more: the electrical effect
        a = south(n=len(placed), tilt=30.0)
        a.placed, a.obstacles = placed, wall
        rows = {}
        for pm in placed:
            rows.setdefault(pm.row, []).append(pm.key)
        wired = simulate(METEO, [a], strings={"s1": list(rows.values())})
        self.assertLess(wired.energy_kwh, shaded.energy_kwh)
        self.assertIn("electrical", [c.key for c in wired.chain])
        self.assertNotIn("electrical", [c.key for c in shaded.chain])
        self.assertIsNotNone(wired.record.find("s1.electrical"))
        self.assertGreater(wired.arrays[0]["electrical_shading"], 0.0)

    def test_the_strings_applied_downstream_give_the_year_simulate_gives_with_them(self):
        """with_strings keeps the first pass (sun, transposition, shadings, temperature, module) and applies the
        array step again: every number equals a whole simulate with the strings (task 18c, step 3)."""
        import dataclasses

        from meridiana.energy.simulate import with_strings
        roof = [(0.0, 0.0), (14.0, 0.0), (14.0, 8.0), (0.0, 8.0)]
        placed = layout.compute(roof, params=layout.Params(tilt=30.0, pitch_mode="value", pitch=4.0), lat=45.5,
                                lon=9.0).modules
        wall = nearshade.prism([(0.0, -2.0), (14.0, -2.0), (14.0, -1.7), (0.0, -1.7)], 0.0, 3.0, "wall")
        rows = {}
        for pm in placed:
            rows.setdefault(pm.row, []).append(pm.key)
        strings = {"s1": list(rows.values())}

        def array():
            a = south(n=len(placed), tilt=30.0)
            a.rows, a.pitch, a.slant = 2, 4.0, 2.278
            a.placed, a.obstacles = placed, wall
            return a
        whole = simulate(METEO, [array()], strings=strings)
        first = simulate(METEO, [array()])
        again = with_strings(first, strings)
        self.assertLess(again.energy_kwh, first.energy_kwh)

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
        self.assertEqual(plain(again), plain(whole))              # exactly, record and all
        self.assertEqual(plain(with_strings(first, None)), plain(first))

    def test_rows_shaded_from_below_lose_more_upright_than_lying_down(self):
        def rows(upright):
            a = south(n=40, tilt=25.0)
            a.rows, a.pitch, a.slant, a.upright = 10, 2.6, 2.278 if upright else 1.134, upright
            return simulate(METEO, [a])
        up, down = rows(True), rows(False)
        self.assertIn("electrical", [c.key for c in up.chain])
        self.assertIsNotNone(up.record.find("s1.rows_electrical"))
        self.assertGreater(up.arrays[0]["rows_electrical"], down.arrays[0]["rows_electrical"])

    def test_a_modules_own_iam_profile_is_used(self):
        own = module()
        own.iam_profile = {"theta": [0.0, 40.0, 60.0, 80.0, 90.0], "iam": [1.0, 1.0, 0.9, 0.5, 0.0]}
        with_profile = simulate(METEO, [ArraySpec("s1", "Sud", 30.0, 0.0, 20, own)])
        plain = simulate(METEO, [south()])
        iam = next(c for c in with_profile.chain if c.key == "iam").change
        self.assertNotAlmostEqual(iam, next(c for c in plain.chain if c.key == "iam").change, places=3)
        self.assertIn("80°: 0.50", with_profile.record.find("s1.iam").inputs[0].value)

    def test_the_profile_is_joined_as_pvsyst_joins_it(self):
        theta = [0.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0]           # ET-M772BH550GL.PAN
        iam = [1.0, 1.0, 1.0, 0.99, 0.98, 0.96, 0.89, 0.66, 0.0]
        at = profile_iam(np.array([25.0, 35.0, 75.0, 90.0, 95.0, -75.0]), theta, iam)
        self.assertEqual(at[0], 1.0)                                    # flat: no cubic swelling above 1
        self.assertAlmostEqual(at[1], 0.995)                            # up to the first point below 1: a line
        self.assertAlmostEqual(at[2], -0.0625 * 0.96 + 0.5625 * 0.89 + 0.5625 * 0.66)   # cubic on 60..90
        self.assertEqual((at[3], at[4]), (0.0, 0.0))
        self.assertAlmostEqual(at[5], at[2])
        grid = profile_iam(np.linspace(0, 90, 901), theta, iam)
        self.assertLessEqual(grid.max(), 1.0)
        self.assertTrue(np.all(np.diff(grid) <= 1e-12))

    def test_a_small_inverter_clips(self):
        small = InverterSpec("X", "Y", pac=0.5 * 20 * 450, eta=0.97)
        s = simulate(METEO, [south()], inverter=small)
        clip = next(c for c in s.chain if c.key == "clipping")
        self.assertLess(clip.change, -1.0)
        self.assertTrue(any("clips" in n for n in s.notes))

    def test_hot_backs_lose_more(self):
        open_ = simulate(METEO, [south(thermal="open")])
        integ = simulate(METEO, [south(thermal="integrated")])
        self.assertLess(integ.energy_kwh, open_.energy_kwh)

    def test_the_heat_balance_uses_the_efficiency_at_the_working_point(self):
        """PVsyst iterates the module's efficiency in its thermal balance; with the STC efficiency the
        temperature step came out 0.16-0.57 points too kind (study 18, B-pvsyst 6.2). A second pass with the
        efficiency the model gives warms the cells a little more."""
        import pvlib
        s = simulate(METEO, [south()])
        step = s.record.find("s1.temperature")
        values = {q.symbol: q.value for q in step.inputs}
        eta_stc, eta_mean = values[r"\eta_m"], values[r"\bar{\eta}"]
        self.assertLess(eta_mean, eta_stc)
        self.assertGreater(eta_mean, 0.75 * eta_stc)
        self.assertAlmostEqual(s.arrays[0]["eta_operating"], eta_mean / 100.0, places=9)
        # the temperature step against the one-pass balance at the STC efficiency, computed here by hand
        a = south()
        m = a.module
        u_c, u_v = 29.0, 0.0
        poa = s.hourly.poa.to_numpy()
        t_one = np.asarray(pvlib.temperature.pvsyst_cell(poa, METEO.data.temp_air.to_numpy(), METEO.data.wind_speed.to_numpy(),
                                                        u_c=u_c, u_v=u_v, module_efficiency=m.efficiency, alpha_absorption=0.9))
        p_25 = a.modules * m.power_at_25(s.hourly.poa_eff.to_numpy())
        one_pass = float((p_25 * (1 + m.gamma_pmax / 100 * (t_one - 25))).sum() / p_25.sum() - 1) * 100
        two_pass = next(c for c in s.chain if c.key == "temperature").change
        self.assertLess(two_pass, one_pass)                       # a larger loss: hotter cells
        self.assertGreater(two_pass, one_pass - 0.6)              # by a few tenths of a point

    def test_the_dc_wiring_loss_follows_the_square_of_the_current(self):
        """R I²: at STC the loss is the given share of the STC power; on the year it is larger than the
        (P/P_STC)² scaling of before (PVsyst prints -1.10% for 1.5% at STC in Kuwait, Meridiana gave -0.85%;
        study 18, B-pvsyst 6.3)."""
        r = 1.5
        s = simulate(METEO, [south()], losses=Losses(dc_wiring=r))
        none = simulate(METEO, [south()], losses=Losses(dc_wiring=0.0))
        lost = 1 - s.hourly.p_dc.sum() / none.hourly.p_dc.sum()
        el = none.hourly.p_dc.to_numpy()
        with_power = float((r / 100 * el ** 2 / (20 * 450.0)).sum() / el.sum())      # the scaling of before
        self.assertGreater(lost, with_power)
        self.assertLess(lost, r / 100)
        self.assertIn("I_{mp}", s.record.find("s1.array").formula)
        # a module at STC the whole hour would lose exactly r% of its STC power: the current ratio is 1 there
        m = south().module
        self.assertAlmostEqual(float(m.current_at_25(1000.0) / m.current_at_25(1000.0)), 1.0)

    def test_the_electrical_effect_can_be_linear_or_a_fraction_as_in_pvsyst(self):
        def rows(**kw):
            a = south(n=40, tilt=25.0)
            a.rows, a.pitch, a.slant = 10, 2.6, 2.278
            return simulate(METEO, [a], losses=Losses(**kw))
        full, half, linear = rows(), rows(electrical_fraction=50.0), rows(electrical_shading=False)
        self.assertIn("electrical", [c.key for c in full.chain])
        self.assertNotIn("electrical", [c.key for c in linear.chain])
        self.assertIsNone(linear.record.find("s1.rows_electrical"))
        self.assertIn("switched off", linear.record.find("s1.rows").explanation)
        self.assertGreater(linear.energy_kwh, half.energy_kwh)
        self.assertGreater(half.energy_kwh, full.energy_kwh)
        self.assertAlmostEqual(half.arrays[0]["rows_electrical"], full.arrays[0]["rows_electrical"] / 2, places=4)
        f_el = next(q for q in full.record.find("s1.rows_electrical").inputs if q.symbol == "f_{el}")
        self.assertEqual((f_el.value, f_el.source.kind), (100.0, "default"))
        self.assertIn("estimate", full.record.find("s1.rows_electrical").explanation)
        # a project saved before the switch existed keeps the full effect
        self.assertEqual((Losses.from_dict({"soiling": 1.0}).electrical_shading,
                          Losses.from_dict({"soiling": 1.0}).electrical_fraction), (True, 100.0))

    def test_two_arrays_add_up(self):
        a = simulate(METEO, [south()])
        b = simulate(METEO, [ArraySpec("s2", "Est", 15.0, -90.0, 10, module())])
        both = simulate(METEO, [south(), ArraySpec("s2", "Est", 15.0, -90.0, 10, module())],
                        inverter=InverterSpec("X", "Y", pac=30 * 450, eta=0.97))
        self.assertAlmostEqual(both.p_stc_kw, a.p_stc_kw + b.p_stc_kw)
        self.assertEqual(len(both.arrays), 2)


class Bookkeeping(unittest.TestCase):
    def test_the_chain_adds_up_to_the_energy(self):
        s = simulate(METEO, [south()], losses=Losses(soiling=3.0, mismatch=2.0))
        energies = [c for c in s.chain if c.kind == "energy"]
        for prev, cur in zip(energies, energies[1:], strict=False):
            if cur.change is not None:
                self.assertAlmostEqual(cur.value, prev.value * (1 + cur.change / 100), delta=1e-6 * max(1, prev.value))
        self.assertAlmostEqual(energies[-1].value, s.energy_kwh, places=6)
        self.assertAlmostEqual(float(s.monthly.e_ac.sum()), s.energy_kwh, places=3)
        self.assertAlmostEqual(float(s.hourly.e_kwh.sum()), s.energy_kwh, places=3)

    def test_the_year_is_in_italian_local_time(self):
        s = simulate(METEO, [south()])
        self.assertEqual(len(s.hourly), 8760)
        self.assertEqual(str(s.hourly.index.tz), "Europe/Rome")
        self.assertEqual(s.hourly.index[0].isoformat(), "2026-01-01T01:00:00+01:00")
        noon = s.hourly.e_kwh.groupby(s.hourly.index.hour).sum()
        self.assertIn(int(noon.idxmax()), (12, 13))      # the sun's noon is near 12:25 in winter, 13:25 in summer

    def test_no_modules_no_simulation(self):
        with self.assertRaises(ValueError):
            simulate(METEO, [south(n=0)])

    def test_every_formula_can_be_drawn(self):
        from matplotlib.mathtext import MathTextParser
        parser = MathTextParser("path")
        rowed = south(n=40, tilt=25.0)
        rowed.rows, rowed.pitch, rowed.slant = 10, 3.0, 2.278
        rowed.placed = layout.compute([(0.0, 0.0), (10.0, 0.0), (10.0, 6.0), (0.0, 6.0)],
                                      params=layout.Params(tilt=25.0)).modules
        rowed.obstacles = nearshade.prism([(4.0, 7.0), (5.0, 7.0), (5.0, 8.0), (4.0, 8.0)], 0.0, 2.0, "chimney")
        s = simulate(METEO, [rowed], horizon=Horizon.flat(), strings={"s1": [[pm.key for pm in rowed.placed]]})
        self.assertIsNotNone(s.record.find("s1.obstacles"))
        self.assertIsNotNone(s.record.find("s1.electrical"))
        self.assertGreater(len(s.record.steps), 6)
        for step in s.record.steps:
            if step.formula:
                parser.parse(f"${step.formula}$")
            for q in step.inputs + ([step.result] if step.result else []):
                if q.symbol:
                    parser.parse(f"${q.symbol}$")


class SecondOpinion(unittest.TestCase):
    """PVGIS as a second opinion: asked with the 2025 crystalline-silicon model, the horizon only when the
    chain applies it, and the loss figure built with the LID the chain uses."""

    def test_pvgis_is_asked_for_the_2025_model_and_the_horizon_of_the_chain(self):
        from meridiana.energy import pvgis
        p = pvgis.params_of(45.5, 9.2, 9.0, 30.0, 0.0, 14.0, building=True, horizon=True)
        self.assertEqual(p["pvtechchoice"], "crystSi2025")
        self.assertEqual(p["usehorizon"], 1)
        self.assertEqual(p["mountingplace"], "building")
        self.assertEqual(pvgis.params_of(45.5, 9.2, 9.0, 30.0, 0.0, 14.0, horizon=False)["usehorizon"], 0)

    def test_the_lid_given_to_pvgis_is_the_one_of_the_chain(self):
        from meridiana.energy.simulate import lid_pct
        from meridiana.energy.system import pvgis_loss
        from dataclasses import replace
        m = replace(module(), first_year_loss=2.0)                   # a datasheet saying 2% in the first year
        self.assertEqual(lid_pct(Losses(), m), 2.0)                  # the datasheet's first-year loss
        self.assertEqual(lid_pct(Losses(lid=0.5), m), 0.5)           # the designer's figure wins
        self.assertEqual(lid_pct(Losses(), module()), 1.0)           # nothing known: 1%
        with_module = pvgis_loss(Losses(), 0.98, m)
        self.assertGreater(with_module, pvgis_loss(Losses(), 0.98))  # 2% of LID instead of 1%
        self.assertAlmostEqual(with_module, pvgis_loss(Losses(lid=2.0), 0.98), places=6)
        s = simulate(METEO, [ArraySpec("s1", "Sud", 30.0, 0.0, 20, m)])
        lid = next(q for q in s.record.find("s1.array").inputs if q.symbol == "LID")
        self.assertEqual(lid.value, 2.0)                             # the chain says the same


def inverter_record(model_name: str, pac_w: float, mppts: int = 2) -> dict:
    return {"manufacturer": "Acme", "model": model_name, "ac_power_nominal_w": pac_w, "efficiency_euro_pct": 97.5,
            "dc_voltage_max_v": 1100, "mppt_voltage_min_v": 180, "mppt_voltage_max_v": 1000, "mppt_count": mppts,
            "dc_current_max_per_mppt_a": [16] * mppts, "dc_isc_max_per_mppt_a": [20] * mppts}


class Inverters(unittest.TestCase):
    """The plant's inverters as a list (task 16d, step 1): each sub-field on an inverter and an input, the AC power
    the sum of them; a project of before, with its one inverter, opens and gives the same year."""

    @classmethod
    def setUpClass(cls):
        import tempfile
        from pathlib import Path

        from _fixtures import write_cache
        cls.cache = Path(tempfile.mkdtemp())
        write_cache(METEO, cls.cache)

    def project(self, energy: dict):
        from meridiana import model
        p = model.Project(name="Prova")
        p.site = model.Site(lat=45.5226, lon=9.0300, address="Rho (MI)")
        p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                                          height=9.5))
        for sid, ring, inverter in (("s1", [[1, 1], [19, 1], [19, 19], [1, 19]], 1),
                                    ("s2", [[21, 1], [39, 1], [39, 19], [21, 19]], 2)):
            p.subfields.append(model.SubField(id=sid, name=sid, ring=ring, building="b1", filled=True,
                                              params={"tilt": 15.0, "inverter": inverter, "mppt": 1}))
        p.energy = energy
        return p

    def year(self, p):
        from meridiana import jobs
        from meridiana.energy import pipeline
        results, _keys, _laid = jobs.layout_of(p)
        out = pipeline.compute(p, results, self.cache, fetch=False)
        self.assertIsNone(out.error_sim)
        return out

    def test_two_different_inverters_with_their_sub_fields_give_the_sum_of_their_ac_power(self):
        from meridiana.energy import system
        a, b = inverter_record("A10", 10000.0), inverter_record("B5", 5000.0, mppts=1)
        p = self.project({"inverters": [{"record": a, "count": 1, "name": ""}, {"record": b, "count": 1, "name": ""}]})
        specs = system.inverters_of(p, 30000.0)
        self.assertEqual([(s.model, s.pac, s.count) for s in specs], [("A10", 10000.0, 1), ("B5", 5000.0, 1)])
        both = system.combined(specs)
        self.assertEqual((both.pac_total, both.count), (15000.0, 2))
        self.assertAlmostEqual(both.eta, 0.975)
        out = self.year(p)
        self.assertAlmostEqual(out.sim.p_ac_kw, 15.0)
        self.assertIn("2 x", system.describe({"inverters": [{"record": a, "count": 2, "name": ""}]}))

    def test_a_project_of_yesterday_opens_and_gives_the_same_year(self):
        import json

        from meridiana import model
        rec = inverter_record("A10", 10000.0)
        today = self.project({"inverters": [{"record": rec, "count": 2, "name": ""}]})
        old = json.loads(json.dumps(self.project({}).to_json()))
        old["version"] = 7                                  # the file of yesterday: one inverter and its count
        old["variants"][0]["design"]["energy"] = {"inverter": rec, "inverter_count": 2}
        opened = model.Project.from_json(old)
        self.assertEqual(opened.energy["inverters"], [{"record": rec, "count": 2, "name": ""}])
        in_memory = self.project({"inverter": rec, "inverter_count": 2})     # a dictionary of before, never saved
        years = [self.year(p).sim for p in (today, opened, in_memory)]
        self.assertEqual({round(s.energy_kwh, 6) for s in years}, {round(years[0].energy_kwh, 6)})
        self.assertAlmostEqual(years[0].p_ac_kw, 20.0)

    def test_sized_by_itself_takes_as_many_alike_as_the_ratio_asks(self):
        from meridiana.energy import system
        rec = inverter_record("A10", 10000.0)
        self.assertEqual(system.sized_count(36000.0, 1.2, rec), 3)
        self.assertEqual(system.sized_count(36500.0, 1.2, rec), 4)
        self.assertEqual(system.sized_count(1000.0, 1.2, rec), 1)
        none = self.project({"dc_ac_ratio": 1.25})
        (sized,) = system.inverters_of(none, 25000.0)
        self.assertEqual((sized.pac, sized.source.kind), (20000.0, "default"))
        self.assertIn("1,25", system.describe(none.energy).replace(".", ","))


if __name__ == "__main__":
    unittest.main()
