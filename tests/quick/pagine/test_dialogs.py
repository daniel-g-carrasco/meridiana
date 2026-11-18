"""Dialog journeys: cancellation, privacy and the original core decisions."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import _setup
from meridiana import canopies, config, shortcuts, templates
from meridiana.registry import Registry
from meridiana.session import ProjectSession
from meridiana.quick.backend.dialogs import DialogsBackend

setUpModule = _setup.keep_global_state


class DialogsTest(unittest.TestCase):
    def setUp(self):
        self.app = _setup.qt_or_skip()
        self.session = ProjectSession()
        self.cfg = config.Config(network_geocoding=False, network_tiles=False)
        self.backend = DialogsBackend(self.session, self.cfg)

    def tearDown(self):
        self.backend.cancel()
        self.backend.deleteLater()

    def test_new_coordinates_and_cancel_leave_project_unchanged(self):
        before = self.session.snapshot()
        self.backend.open("new")
        self.backend.setValue("query", "45.5226, 9.0300")
        self.assertTrue(self.backend.state["valid"])
        self.assertTrue(self.backend.mapBackend.marker)
        self.backend.cancel()
        self.assertEqual(before, self.session.snapshot())
        self.backend.open("new")
        self.assertFalse(self.backend.mapBackend.marker)
        self.assertFalse(self.backend.state["valid"])
        self.assertEqual("", self.backend.state["latitude"])

    def test_new_emits_complete_network_without_replacing_session(self):
        out = []
        self.backend.created.connect(out.append)
        self.backend.open("new")
        for key, value in {
            "query": "45.5226, 9.0300",
            "name": "Rho",
            "voltage_v": 400,
            "phases": "3",
            "pod": "IT001",
            "reserved": True,
            "maps_consent": True,
        }.items():
            self.backend.setValue(key, value)
        self.assertTrue(self.backend.accept())
        self.assertEqual(out[0]["site"].lat, 45.5226)
        self.assertEqual(out[0]["network"].voltage_v, 400)
        self.assertEqual(out[0]["network"].pod, "IT001")
        self.assertIn("tiles", out[0]["network_consent"])
        self.assertNotEqual(self.session.project.name, "Rho")

    def test_invalid_coordinates_never_create(self):
        self.backend.open("new")
        self.backend.setValue("query", "95, 190")
        self.assertFalse(self.backend.accept())
        self.assertFalse(self.backend.state["valid"])

    def test_site_is_one_undoable_edit(self):
        before = self.session.project.site.lat
        self.backend.open("site")
        self.backend.setValue("query", "42.1, 12.5")
        self.assertTrue(self.backend.accept())
        self.assertEqual(self.session.project.site.lat, 42.1)
        self.session.undo.undo()
        self.assertEqual(self.session.project.site.lat, before)

    def test_reserved_blocks_geocoding_even_with_global_permission(self):
        self.cfg.network_geocoding = True
        self.backend.open("new")
        self.backend.setValue("reserved", True)
        self.backend.setValue("query", "Roma")
        with patch.object(self.backend.net, "get") as get:
            self.backend.search()
            get.assert_not_called()
        self.assertTrue(self.backend.status)

    def test_online_result_select_and_error(self):
        self.backend.open("new")
        self.backend.show_answer(b'[{"display_name":"Roma","lat":"41.9","lon":"12.5"}]')
        self.backend.choosePlace(0, True)
        self.assertEqual(self.backend.state["latitude"], 41.9)
        self.backend.show_answer(b"broken")
        self.assertTrue(self.backend.status)

    def test_canopy_parity_and_cancel(self):
        self.backend.open("canopy")
        self.backend.setValue("rows", 2)
        spec = self.backend.canopy_spec()
        self.assertEqual(spec, canopies.Spec(rows=2))
        self.assertEqual(self.backend.state["ring"], canopies.footprint(spec, (0, 0)))
        self.backend.cancel()
        self.assertFalse(self.session.project.buildings)

    def test_template_each_shape_matches_core_and_invalid_rejected(self):
        self.backend.open("template")
        for shape in templates.KINDS:
            self.backend.setValue("shape", shape)
            self.assertEqual(self.backend.state["ring"], templates.footprint(shape))
        self.backend.setValue("shape", "L")
        self.backend.setValue("arm_south", 100)
        self.assertFalse(self.backend.accept())

    def test_shortcut_conflict_moves_key_and_cancel_preserves_config(self):
        before = dict(self.cfg.shortcuts)
        self.backend.open("shortcuts")
        ids = list(shortcuts.bindings({}))
        self.backend.assignShortcut(ids[0], "Ctrl+Shift+9")
        self.backend.assignShortcut(ids[1], "Ctrl+Shift+9")
        self.assertEqual(self.backend.bindings[ids[0]], [])
        self.backend.cancel()
        self.assertEqual(self.cfg.shortcuts, before)

    def test_registry_validation_reserved_job_and_import_preview(self):
        with tempfile.TemporaryDirectory() as folder:
            registry = Registry(Path(folder) / "registry.sqlite")
            self.backend.set_registry(registry)
            self.backend.open("registry")
            self.assertFalse(self.backend.saveClient(""))
            self.assertTrue(self.backend.saveClient("Client"))
            cid = registry.list_clients()[0]["id"]
            self.assertFalse(self.backend.saveJob("abc", "Job", cid, False))
            self.assertTrue(self.backend.saveJob("00001", "Job", cid, True))
            self.backend.open("new")
            self.backend.setValue("job_id", registry.list_jobs()[0]["id"])
            self.backend.setValue("reserved", False)
            self.assertTrue(self.backend.state["reserved"])
            registry.close()
            self.backend.set_registry(None)

    def test_side_measures_formulas_and_invalid_keep_previous_geometry(self):
        self.backend.open("template")
        self.assertTrue(self.backend.editMeasure("1", "12 m + 30 cm"))
        self.assertAlmostEqual(self.backend.state["width"], 12.3)
        before = self.backend.state["ring"]
        self.assertFalse(self.backend.editMeasure("1", "-5 m"))
        self.assertEqual(self.backend.state["ring"], before)
        self.backend.open("canopy")
        self.assertTrue(self.backend.editMeasure("1", "12 m"))
        self.assertEqual(self.backend.state["bay_width"], 3)
        self.assertFalse(self.backend.editMeasure("tilt", "80"))
        self.assertEqual(self.backend.state["tilt"], 8)

    def test_map_privacy_requires_project_and_global_permission(self):
        self.backend.open("new")
        preview = self.backend.mapBackend
        self.backend.setValue("query", "45.52, 9.03")
        self.assertFalse(preview.allowed)
        self.cfg.network_tiles = True
        self.backend.setValue("reserved", True)
        self.assertFalse(preview.allowed)
        self.backend.setValue("maps_consent", True)
        self.assertTrue(preview.allowed)
        self.backend.setValue("query", "invalid")
        self.assertFalse(preview.allowed)
        self.assertEqual(preview.marker, [])

    def test_invalid_coordinate_search_never_goes_online(self):
        self.cfg.network_geocoding = True
        self.backend.open("new")
        self.backend.setValue("query", "95, 190")
        with patch.object(self.backend.net, "get") as get:
            self.backend.search()
            get.assert_not_called()
        self.assertTrue(self.backend.status)

    def test_pasted_coordinate_pair_and_invalid_network_numbers(self):
        self.backend.open("new")
        self.backend.setValue("latitude", "45.52")
        self.assertFalse(self.backend.state["valid"])
        self.backend.setValue("longitude", "9.03")
        self.assertTrue(self.backend.state["valid"])
        self.assertTrue(self.backend.mapBackend.marker)
        self.backend.setValue("longitude", "")
        self.assertFalse(self.backend.state["valid"])
        self.assertFalse(self.backend.mapBackend.marker)
        self.backend.setValue("latitude", "45,52;9,03")
        self.assertTrue(self.backend.state["valid"])
        self.assertAlmostEqual(self.backend.state["longitude"], 9.03)
        self.backend.setValue("voltage_v", float("nan"))
        self.assertEqual(self.backend.state["voltage_v"], 0)

    def test_site_cannot_move_after_drawing(self):
        self.session.edit("canopy", lambda p: canopies.add(p, canopies.Spec(), (0, 0)))
        before = self.session.snapshot()
        self.backend.open("site")
        self.backend.setValue("query", "42.1, 12.5")
        self.assertFalse(self.backend.accept())
        self.assertEqual(before, self.session.snapshot())

    def test_shortcuts_atomic_save_failure_keeps_config(self):
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as folder:
            self.backend.paths = SimpleNamespace(
                config_file=Path(folder) / "config.json"
            )
            self.backend.open("shortcuts")
            cid = next(iter(self.backend.bindings))
            self.backend.assignShortcut(cid, "Ctrl+Shift+9")
            old = dict(self.cfg.shortcuts)
            with patch("meridiana.config.save", side_effect=OSError("disk full")):
                self.assertFalse(self.backend.accept())
            self.assertEqual(self.cfg.shortcuts, old)
            self.assertTrue(self.backend.accept())
            self.assertEqual(
                config.load(self.backend.paths.config_file).shortcuts,
                self.cfg.shortcuts,
            )


if __name__ == "__main__":
    unittest.main()
