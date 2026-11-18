"""R389: real command boundaries and an honest, extensible parity ledger."""
import copy
import unittest
from pathlib import Path

import _setup
from _fixtures import capannone

from quick.parity.differential import (
    COMMAND_SCENARIOS, Adapter, MissingCommand, QuickAdapter, WidgetsAdapter,
    canonical_project, compare, run_scenario,
)

setUpModule = _setup.keep_global_state


class ComparisonTest(unittest.TestCase):
    def test_canonicalization_preserves_ids_names_versions_and_geometry(self):
        project = capannone()
        before = canonical_project(project)
        for field, value in (("name", "Changed"), ("bim_id", "other-id")):
            changed = copy.deepcopy(project)
            setattr(changed, field, value)
            self.assertTrue(compare(before, canonical_project(changed)))
        changed = copy.deepcopy(project)
        changed.buildings[0].footprint[0][0] = .0001
        self.assertTrue(compare(before, canonical_project(changed)))

    def test_numeric_tolerance_does_not_hide_missing_or_extra_fields(self):
        self.assertEqual(compare({"kwh": 10.}, {"kwh": 10. + 1e-11}), [])
        self.assertTrue(compare({"kwh": 10.}, {"kwh": 10.01}))
        self.assertTrue(compare({"kwh": None}, {}))
        self.assertTrue(compare([1, 2], [2, 1]))

    def test_missing_command_cannot_mutate_either_side_or_count_as_equal(self):
        calls = []
        left = Adapter("Widgets", {"roof": lambda **kw: calls.append("left")}, lambda: {})
        right = Adapter("Quick", {}, lambda: {})
        result = run_scenario({"id": "roof", "steps": [{"command": "roof"}]}, left, right)
        self.assertEqual(result["status"], "missing")
        self.assertEqual(result["missing"], ["Quick:roof"])
        self.assertEqual(calls, [])
        with self.assertRaises(MissingCommand):
            right.execute("roof")

    def test_adapter_failure_is_error_not_missing_or_pass(self):
        def broken():
            raise ValueError("real failure")
        a = Adapter("Widgets", {"roof": broken}, lambda: {})
        b = Adapter("Quick", {"roof": lambda: None}, lambda: {})
        result = run_scenario({"id": "roof", "steps": [{"command": "roof"}]}, a, b)
        self.assertEqual(result["status"], "error")
        self.assertIn("real failure", result["error"])

    def test_all_requested_journeys_are_explicit(self):
        ids = {s["id"] for s in COMMAND_SCENARIOS}
        self.assertLessEqual({"building", "roof", "subfield", "layout", "exclusion", "row",
                             "move", "rotate", "undo_redo", "variants", "automatic_strings",
                             "manual_strings", "inverters", "battery", "consumption", "economics",
                             "recorded_year", "report", "save"}, ids)
        self.assertTrue(all(s["requests"] and s["steps"] for s in COMMAND_SCENARIOS))

    def test_manifest_describes_the_executed_scenarios(self):
        import json
        manifest = json.loads((_setup.ROOT / "docs/quick/compat/scenarios.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["scenarios"], COMMAND_SCENARIOS)


class ActualBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from meridiana import i18n
        from meridiana.paths import Paths
        import tempfile
        from unittest import mock
        i18n.setup("it")
        parent = _setup.ROOT / "build" / "quick-parity" / "temp"
        parent.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        paths = Paths(**{k: self.folder / k for k in ("config", "state", "data", "cache")})
        from quick.parity.differential import connected_fixture
        project = connected_fixture() if "recorded_weather" in self._testMethodName else capannone()
        with mock.patch.object(tempfile, "tempdir", str(self.folder)):
            self.widgets = WidgetsAdapter(_setup.window(self, copy.deepcopy(project), paths=paths), self.app)
        self.quick = QuickAdapter(copy.deepcopy(self.widgets.session.project), paths.cache, self.app)
        self.addCleanup(self.quick.close)

    def test_real_rename_height_undo_redo_preserve_project_at_every_step(self):
        scenario = {"id": "editing", "observations": ["project"], "steps": [
            {"command": "select", "args": {"kind": "building", "oid": "b1"}},
            {"command": "rename", "args": {"value": "Tetto Sud"}},
            {"command": "height", "args": {"value": 11.5}},
            {"command": "undo"}, {"command": "undo"},
            {"command": "redo"}, {"command": "redo"},
        ]}
        result = run_scenario(scenario, self.widgets, self.quick)
        self.assertEqual(result["status"], "equal", result)
        self.assertEqual(len(result["steps"]), 7)
        self.assertEqual(self.quick.session.project.buildings[0].height, 11.5)

    @unittest.expectedFailure
    def test_r389_rename_undo_text_matches_widgets(self):
        # Quick uses Rename; Widgets uses Change Name. Keep visible until aligned.
        result = run_scenario({"id": "rename_text", "observations": ["project", "undo"], "steps": [
            {"command": "select", "args": {"kind": "building", "oid": "b1"}},
            {"command": "rename", "args": {"value": "Tetto Sud"}},
        ]}, self.widgets, self.quick)
        self.assertEqual(result["status"], "equal", result)

    @unittest.expectedFailure
    def test_r389_new_building_name_matches_widgets(self):
        result = run_scenario(next(s for s in COMMAND_SCENARIOS if s["id"] == "building"),
                              self.widgets, self.quick)
        self.assertEqual(result["status"], "equal", result)

    def test_current_missing_commands_are_listed_individually(self):
        results = [run_scenario(s, self.widgets, self.quick) for s in COMMAND_SCENARIOS
                   if any(step["command"] not in self.quick.commands for step in s["steps"])]
        self.assertGreaterEqual(len(results), 15)
        self.assertTrue(all(r["status"] == "missing" for r in results), results)
        self.assertTrue(all(any(m.startswith("Quick:") for m in r["missing"]) for r in results))
        self.assertFalse(any(m.startswith("Widgets:") for r in results for m in r["missing"]), results)

    def test_widgets_reference_uses_real_inverter_string_variant_and_energy_handlers(self):
        w = self.widgets
        w.execute("inverters", count=2)
        self.assertEqual(w.session.project.energy["inverters"][0]["count"], 2)
        w.execute("manual_strings", unit=1, mppt=1, count=20)
        self.assertEqual(len(w.session.project.energy["strings"]["runs"][0]["modules"]), 20)
        w.execute("variants", name="Alternativa")
        self.assertEqual(w.session.project.current_variant()["name"], "Alternativa")
        w.execute("consumption", value=40000.)
        w.execute("economics", value=45000.)
        w.execute("battery", value={"usable_energy_kwh": 20.})
        self.assertEqual(w.session.project.consumption["annual_kwh"], 40000.)
        self.assertEqual(w.session.project.economics["capex_total"], 45000.)
        self.assertEqual(w.session.project.economics["battery"]["usable_energy_kwh"], 20.)

    def test_widgets_geometry_journey_and_saved_project_reopen(self):
        from unittest.mock import patch
        from shapely.geometry import Polygon
        from meridiana import model
        w = self.widgets
        # These are layout/plant journeys. The annual worker is deliberately not started.
        with patch.object(w.window, "_compute_energy"):
            w.execute("building", x1=60., y1=0., x2=100., y2=20.)
            bid = w.session.project.buildings[-1].id
            w.execute("roof", oid=bid, kind="gable")
            roof = w.session.project.building(bid)
            self.assertEqual(len(roof.pitches()), 2)
            self.assertTrue(all(pitch.tilt > 0 for pitch in roof.pitches()),
                            "Changing roof type must use the same proposed slope as Properties")
            w.execute("subfield", ring=[[62, 2], [98, 2], [98, 8], [62, 8]])
            sf = w.session.project.subfields[-1]
            sid = sf.id
            self.assertEqual(sf.building, bid)
            self.assertEqual(sf.params["mounting"], "coplanar")
            self.assertFalse(sf.filled)
            w.execute("select", kind="subfield", oid=sid)
            w.execute("layout")
            self.assertTrue(w.window.project_subfield(sid).filled)
            before_count = w.session.results[sid].count
            self.assertGreater(before_count, 0)
            w.execute("exclusion", ring=[[76, 3], [80, 3], [80, 7], [76, 7]])
            exclusion = w.session.project.exclusions[-1]
            self.assertEqual(exclusion.building, bid)
            self.assertLess(w.session.results[sid].count, before_count)
            obstacle = Polygon(exclusion.ring)
            self.assertTrue(all(Polygon(m.corners).intersection(obstacle).area < 1e-8
                                for m in w.session.results[sid].modules))
            before = copy.deepcopy(w.session.project.building(bid).footprint)
            subfield_before = copy.deepcopy(w.window.project_subfield(sid).ring)
            w.execute("move", kind="building", oid=bid, dx=3., dy=2.)
            self.assertEqual(w.session.project.building(bid).footprint, [[x + 3, y + 2] for x, y in before])
            self.assertEqual(w.window.project_subfield(sid).ring, [[x + 3, y + 2] for x, y in subfield_before])
            moved = canonical_project(w.session.project)
            w.execute("rotate", kind="building", oid=bid, cx=80., cy=10., degrees=90.)
            rotated = canonical_project(w.session.project)
            point = w.session.project.building(bid).footprint[0]
            self.assertAlmostEqual(point[0], 88.)
            self.assertAlmostEqual(point[1], -7.)
            self.assertAlmostEqual(Polygon(w.session.project.building(bid).footprint).area, 800.)
            w.execute("undo")
            self.assertFalse(compare(moved, canonical_project(w.session.project)))
            w.execute("redo")
            self.assertFalse(compare(rotated, canonical_project(w.session.project)))
            w.execute("select", kind="subfield", oid="s1")
            rows_before = len(w.session.results["s1"].rows)
            w.execute("row", start=[4., 4.], end=[15., 4.])
            sf = w.window.project_subfield("s1")
            self.assertTrue(sf.manual)
            self.assertGreater(len(sf.hand_rows()), rows_before)
            self.assertGreater(w.session.results["s1"].count, 0)
            expected = canonical_project(w.session.project)
            for extension in (".mer", ".meridiana"):
                destination = self.folder / ("geometry" + extension)
                w.execute("save", path=destination)
                saved = canonical_project(w.session.project)
                changes = compare(expected, saved)
                # Saving with a cache embeds its weather envelope, even when empty.
                # Do not remove resources from the canonical comparator to hide it.
                if changes:
                    self.assertEqual(changes, [{"path": "$.resources.weather", "widgets": None,
                                                "quick": {}, "missing": "Widgets"}])
                expected = saved
                loaded, notice = model.Project.load(destination)
                self.assertIsNone(notice)
                self.assertFalse(compare(expected, canonical_project(loaded)))
                self.assertTrue(w.window.open_path(destination))
                w.wait()
                self.assertFalse(compare(expected, canonical_project(w.session.project)))
                self.assertEqual(w.session.undo.count(), 0)
                self.assertGreater(w.session.results[sid].count, 0)
                with self.assertRaises(FileExistsError):
                    w.execute("save", path=destination)

    def test_widgets_automatic_strings_connect_real_modules_and_undo_as_one_step(self):
        from unittest.mock import patch
        w = self.widgets
        with patch.object(w.window, "_compute_energy"):
            w.execute("inverters", count=2)
            before = canonical_project(w.session.project)
            count_before = w.session.undo.count()
            w.execute("automatic_strings", strategy="serpentine")
            runs = w.session.project.energy["strings"]["runs"]
            self.assertTrue(runs)
            available = {f"{sid}/{m.key}" for sid, layout in w.session.good_results().items()
                         for m in layout.modules}
            assigned = [key for run in runs for key in run["modules"]]
            self.assertGreater(len(assigned), 20)
            self.assertEqual(len(assigned), len(set(assigned)))
            self.assertLessEqual(set(assigned), available)
            self.assertTrue(all(run["inverter"] in (1, 2) and run["mppt"] in (1, 2) for run in runs))
            self.assertEqual(w.session.undo.count(), count_before + 1)
            after = canonical_project(w.session.project)
            w.execute("undo")
            self.assertFalse(compare(before, canonical_project(w.session.project)))
            w.execute("redo")
            self.assertFalse(compare(after, canonical_project(w.session.project)))

    def test_known_differences_are_observed_not_unrelated_exceptions(self):
        from quick.parity.differential import write_evidence
        from uuid import uuid4
        results = []
        for scenario in (
            next(s for s in COMMAND_SCENARIOS if s["id"] == "building"),
            {"id": "rename_undo_text", "steps": [
                {"command": "select", "args": {"kind": "building", "oid": "b1"}},
                {"command": "rename", "args": {"value": "Nuovo nome"}},
            ]},
        ):
            result = run_scenario(scenario, self.widgets, self.quick)
            self.assertEqual(result["status"], "different", result)
            results.append(result)
            self.widgets.execute("undo")
            self.quick.execute("undo")
            self.assertFalse(compare(canonical_project(self.widgets.session.project),
                                     canonical_project(self.quick.session.project)))
        self.assertTrue(any(d["path"].endswith(".name") for d in results[0]["steps"][0]["differences"]))
        self.assertTrue(any(d["path"] == "$.undo.undo" for d in results[1]["steps"][-1]["differences"]))
        results.append(run_scenario(next(s for s in COMMAND_SCENARIOS if s["id"] == "undo_redo"),
                                    self.widgets, self.quick))
        results.extend(run_scenario(s, self.widgets, self.quick) for s in COMMAND_SCENARIOS
                       if any(step["command"] not in self.quick.commands for step in s["steps"]))
        write_evidence(_setup.ROOT / "build/quick-parity" / f"commands-{uuid4().hex}.json", results)

    def test_recorded_weather_runs_both_real_workers_and_reports_differences(self):
        from meridiana.quick.sample import recorded_weather
        from quick.parity.differential import write_evidence
        from uuid import uuid4
        self.assertTrue(recorded_weather(self.widgets.session.project, self.quick.bridge.cache))
        scenario = next(s for s in COMMAND_SCENARIOS if s["id"] == "recorded_year")
        result = run_scenario(scenario, self.widgets, self.quick)
        self.assertNotEqual(result["status"], "error", result)
        self.assertFalse(result["missing"], result)
        for side in (self.widgets, self.quick):
            sim = side.session.energy.get("sim")
            self.assertIsNotNone(sim, side.session.energy)
            self.assertEqual(len(sim.hourly), 8760)
            self.assertGreater(sim.energy_kwh, 1000.)
            self.assertEqual(side.session.energy["battery_kwh"], 20.)
            self.assertIn("npv", side.session.energy["econ"].kpi)
        self.assertFalse(compare(self.widgets.session.energy["sim"].hourly.e_kwh.tolist(),
                                 self.quick.session.energy["sim"].hourly.e_kwh.tolist()))
        result["verified"] = {"hours": 8760, "annual_kwh": self.quick.session.energy["sim"].energy_kwh,
                              "battery_kwh": 20., "hourly_production_equal": True}
        write_evidence(_setup.ROOT / "build/quick-parity" / f"year-{uuid4().hex}.json", [result])


if __name__ == "__main__":
    unittest.main()
