"""The energy pipeline as one function without Qt (energy/pipeline.py): the whole chain on the synthetic
year of _fixtures.py, what it gives when the weather or the modules are missing, and what it costs (one
simulation, the strings applied downstream of it, the count out of the shadows without a whole layout:
task 18c)."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup  # noqa: F401
from _fixtures import clear_sky_meteo, write_cache

from meridiana import checks, compare, jobs, model
from meridiana.energy import meteo, pipeline


def project(with_chimney: bool = False) -> model.Project:
    p = model.Project(name="Prova")
    p.site = model.Site(lat=45.5226, lon=9.0300, address="Rho (MI)")
    b = model.Building(id="b1", name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]], height=9.5)
    p.buildings.append(b)
    p.subfields.append(model.SubField(id="s1", name="Sud", ring=[[1, 1], [39, 1], [39, 19], [1, 19]], building="b1",
                                      params={"tilt": 15.0}, filled=True))
    if with_chimney:
        p.exclusions.append(model.ExclusionItem(id="e1", ring=[[18, 9], [20, 9], [20, 11], [18, 11]], kind="chimney",
                                                building="b1", height=2.5))
    return p


class Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cache = Path(tempfile.mkdtemp())
        write_cache(clear_sky_meteo(45.5226, 9.03), cls.cache)

    def test_the_whole_chain_without_the_window(self):
        p = project()
        results, keys, laid = jobs.layout_of(p)
        self.assertEqual(laid, ["s1"])
        self.assertEqual(set(keys), {"s1"})
        with mock.patch.object(pipeline, "simulate", wraps=pipeline.simulate) as sim, \
                mock.patch.object(checks, "count_out_of_shadows", wraps=checks.count_out_of_shadows) as counted:
            out = pipeline.compute(p, results, self.cache, fetch=False)
        self.assertIsNone(out.error_sim)
        self.assertEqual(out.sim.energy_kwh, 0)
        self.assertGreater(out.load.annual_kwh, 0)
        self.assertIn("npv", out.econ.kpi)
        self.assertIn("error", out.strings)                     # an inverter sized by itself: no window to check
        self.assertFalse(out.plant.strings)
        self.assertEqual(len(out.plant.left), sum(a["modules"] for a in out.sim.arrays))
        self.assertEqual(out.context.production_kwh, out.sim.energy_kwh)
        self.assertEqual(out.battery_kwh, 0.0)
        self.assertTrue(out.notes)                              # unconnected modules are explicitly reported
        # potential temperature pass, then connected generation, and a layout out of the shadows for
        # each sub-field shaded beyond the threshold (none on a roof without obstacles)
        self.assertEqual(sim.call_count, 2)
        shaded = [a for a in out.sim.arrays if float(a.get("obstacle_shading") or 0.0) > checks.OBSTACLE_SHADE]
        self.assertEqual(counted.call_count, len(shaded))
        self.assertEqual(out.shade_free_counts, {})
        d = out.as_dict()
        self.assertIs(d["sim"], out.sim)
        self.assertNotIn("error_sim", d)
        self.assertNotIn("wiring", d)
        self.assertEqual(d["notes"], out.notes)
        self.assertAlmostEqual(compare.summary(d)["kwh"], out.sim.energy_kwh)

    def test_the_strings_of_a_catalogue_inverter_make_the_year_run_again_with_the_shade(self):
        from meridiana import catalog
        p = project(with_chimney=True)
        p.energy["inverters"] = [{"record": next(r for r in catalog.search("inverters", "SCA100K-T-US-480")),
                                  "count": 1, "name": ""}]
        p.energy["strings"] = {"auto": True}        # Meridiana's proposal, as a project of before format 14 had it
        results, _keys, _laid = jobs.layout_of(p)
        with mock.patch.object(pipeline, "simulate", wraps=pipeline.simulate) as sim, \
                mock.patch.object(pipeline, "with_strings", wraps=pipeline.with_strings) as again:
            out = pipeline.compute(p, results, self.cache, fetch=False)
        strings = out.plant.strings
        self.assertTrue(out.plant.auto)                          # proposed by Meridiana
        self.assertTrue(strings)
        self.assertEqual(len({len(s.modules) for s in strings}), 1)
        self.assertTrue(out.plant.year)                          # checked at the hottest cell of the year
        self.assertEqual(out.strings["t_cell_max"], out.plant.t_cell_max)
        self.assertTrue(all(slot.plan is not None for slot in out.plant.inputs.values() if slot.used))
        # the chimney shades the array: the strings laid give the shade its electrical effect, applied on the
        # connected-generation pass; unassigned modules contribute zero
        self.assertEqual(sim.call_count, 2)
        self.assertEqual(again.call_count, 1)
        self.assertEqual(set(again.call_args[0][1]), {"s1.0"})
        self.assertIs(again.call_args[0][0].parts, out.sim.parts)       # the year with the strings, from the first pass
        self.assertIsNotNone(out.sim.record.find("s1.0.electrical"))

    def test_without_the_weather_the_consumption_is_there_and_the_rest_says_why(self):
        p = project()
        results, _keys, _laid = jobs.layout_of(p)
        out = pipeline.compute(p, results, Path(tempfile.mkdtemp()), fetch=False)
        self.assertIsNotNone(out.load)
        self.assertIsNone(out.sim)
        self.assertIn("Fetch the weather", out.error_sim)
        self.assertEqual(compare.summary(out.as_dict()), {"error": out.error_sim})

    def test_without_a_module_laid_the_year_is_not_computed(self):
        p = project()
        out = pipeline.compute(p, {}, self.cache, fetch=False)
        self.assertIsNone(out.sim)
        self.assertIn("Lay the modules", out.error_sim)

    def test_what_goes_wrong_is_said_in_the_result_not_raised(self):
        p = project()
        with mock.patch.object(pipeline, "simulate", side_effect=meteo.MeteoError("no sky")):
            out = pipeline.compute_or_say(p, jobs.layout_of(p)[0], self.cache, fetch=False)
        self.assertIn("no sky", out.error_sim)
        with mock.patch.object(pipeline, "simulate", side_effect=KeyError("ghi")), \
                mock.patch.object(pipeline.log, "complain") as complained:
            out = pipeline.compute_or_say(p, jobs.layout_of(p)[0], self.cache, fetch=False)
        self.assertEqual(out.error_sim, "KeyError: 'ghi'")
        self.assertEqual(complained.call_args[0][0], "energy")

    def test_the_layout_job_prepares_the_3d_table_of_each_layout(self):
        from meridiana import mesh
        p = project()
        results, _keys, _laid = jobs.layout_of(p)
        r = results["s1"]
        self.assertEqual(r.table.shape, (r.count, 20))
        along, across = jobs.module_sides(p, p.subfields[0])
        self.assertTrue((r.table == mesh.module_table(r.modules, along, across)).all())
        self.assertEqual((along, across), (1.134, 2.278) if p.subfields[0].layout_params().portrait else (2.278, 1.134))

    def test_a_layout_in_hand_is_kept_when_its_inputs_did_not_change(self):
        p = project()
        results, keys, _laid = jobs.layout_of(p)
        known = {sid: (keys[sid], r) for sid, r in results.items()}
        again, _keys, laid = jobs.layout_of(p, known)
        self.assertEqual(laid, [])
        self.assertIs(again["s1"], results["s1"])
        p.subfields[0].params["gap"] = 0.05
        _again, _keys, laid = jobs.layout_of(p, known)
        self.assertEqual(laid, ["s1"])


class PipelineSteps(unittest.TestCase):
    """energy/pipeline.py, without Qt: its steps told, and Interrupted from the caller goes through."""

    def test_the_pipeline_tells_its_steps_and_stops_where_it_is_asked_to(self):
        import tempfile
        from pathlib import Path

        from _fixtures import clear_sky_meteo, write_cache

        from meridiana import jobs, model
        from meridiana.energy import pipeline
        cache = Path(tempfile.mkdtemp())
        write_cache(clear_sky_meteo(), cache)
        p = model.Project(name="Prova")
        p.site = model.Site(lat=45.5226, lon=9.0300, address="Rho (MI)")
        b = model.Building(id=p.new_id("b"), name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                           height=9.5)
        p.buildings.append(b)
        p.subfields.append(model.SubField(id=p.new_id("s"), name="Sud", ring=[[1, 1], [39, 1], [39, 19], [1, 19]],
                                          building=b.id, params={"tilt": 15.0}, filled=True))
        results, _keys, _laid = jobs.layout_of(p)
        told = []
        out = pipeline.compute(p, results, cache, False, lambda done, total, what: told.append((done, total, what)))
        self.assertIsNotNone(out.sim)
        self.assertEqual([d for d, _t, _w in told], [0, 1, 2])         # no connected modules: no request to PVcalc
        self.assertTrue(all(t == pipeline.STEPS for _d, t, _w in told))
        self.assertEqual(told[1][2], "the horizon")

        def stop(done, total, what):
            if done == 2:
                raise pipeline.Interrupted()

        with self.assertRaises(pipeline.Interrupted):               # not turned into an error to show
            pipeline.compute_or_say(p, results, cache, False, stop)


if __name__ == "__main__":
    unittest.main()
