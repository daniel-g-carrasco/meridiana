"""R389: frozen formats enter Quick unchanged; unavailable saving is explicit."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import _setup
from _fixtures import capannone_rho
from meridiana import config, model
from quick.parity.differential import MissingCommand, canonical_project
from quick.parity.formats import QuickFiles, frozen_cases, roundtrip, current_config_roundtrip

setUpModule = _setup.keep_global_state


class FormatInventoryTest(unittest.TestCase):
    def test_every_frozen_file_is_classified_and_latest_versions_present(self):
        cases = frozen_cases()
        self.assertEqual({c.path for c in cases}, set(_setup.FORMATS.iterdir()))
        self.assertIn(f"progetto-v{model.FORMAT_VERSION}.meridiana", {c.path.name for c in cases})
        self.assertIn(f"config-v{config.CONFIG_VERSION}.json", {c.path.name for c in cases})
        self.assertEqual(sum(c.kind == "invalid_project" for c in cases), 3)

    def test_absent_save_prevents_claiming_a_roundtrip(self):
        quick = QuickFiles(Path("unused"))
        self.assertFalse(quick.can_save)
        with self.assertRaisesRegex(MissingCommand, "Quick:save"):
            quick.save(Path("must-not-exist.mer"))


class FrozenQuickTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        from meridiana.quick.app import create_app
        create_app()

    def setUp(self):
        root = _setup.ROOT / "build/quick-parity/temp"
        root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=root)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.quick = QuickFiles(self.folder / "cache")
        self.addCleanup(self.quick.close)

    def test_every_valid_project_opens_in_actual_quick_window_without_changes(self):
        for case in frozen_cases():
            if case.kind != "project":
                continue
            with self.subTest(file=case.path.name):
                digest = hashlib.sha256(case.path.read_bytes()).hexdigest()
                expected, notice = model.Project.load(case.path)
                got_notice = self.quick.open(case.path)
                self.assertIsNotNone(self.quick.host.window)
                self.assertEqual(self.quick.host.warnings, [])
                self.assertEqual(canonical_project(self.quick.project), canonical_project(expected))
                self.assertEqual(got_notice, notice)
                self.assertEqual(hashlib.sha256(case.path.read_bytes()).hexdigest(), digest)
                result = roundtrip(case.path, self.folder / (case.path.stem + ".mer"), self.quick)
                self.assertEqual(result["status"], "missing", result)
                self.assertEqual(result["missing"], ["Quick:save"])
                self.assertFalse((self.folder / (case.path.stem + ".mer")).exists())

    def test_invalid_and_future_project_inputs_are_rejected_without_a_window(self):
        for case in frozen_cases():
            if case.kind != "invalid_project":
                continue
            with self.subTest(file=case.path.name):
                with self.assertRaises((ValueError, UnicodeError)):
                    self.quick.open(case.path)
                self.assertIsNone(self.quick.host)

    def test_mer_archive_opens_with_assets_and_identical_semantics(self):
        import base64
        from meridiana.underlay import Underlay
        project = capannone_rho()
        project.underlays = [Underlay("u1", image=base64.b64encode(b"parity asset").decode())]
        project.report = {"attachments": [{"title": "Recorded attachment", "path": "sheet.pdf",
                                            "data": base64.b64encode(b"attachment bytes").decode()}]}
        source = self.folder / "source.mer"
        project.save(source)
        self.quick.open(source)
        expected, _ = model.Project.load(source)
        self.assertEqual(canonical_project(self.quick.project), canonical_project(expected))
        self.assertEqual(self.quick.project.underlays[0].image, project.underlays[0].image)
        self.assertEqual(roundtrip(source, self.folder / "saved.mer", self.quick)["status"], "missing")

    def test_all_config_fixtures_are_missing_quick_configuration_not_reverse_migrated(self):
        for case in frozen_cases():
            if "config" not in case.kind:
                continue
            with self.subTest(file=case.path.name):
                before = case.path.read_bytes()
                self.assertEqual(self.quick.config_status(case.path)["missing"],
                                 ["Quick:load_config", "Quick:save_config"])
                self.assertEqual(case.path.read_bytes(), before)

    def test_current_config_roundtrip_keeps_current_version_and_choices(self):
        # Shared file contract only: Quick configuration is absent and reported above.
        original = _setup.FORMATS / f"config-v{config.CONFIG_VERSION}.json"
        result = current_config_roundtrip(original, self.folder)
        self.assertEqual(result["status"], "equal", result)
        saved = json.loads((self.folder / "current-config-saved.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["version"], config.CONFIG_VERSION)


if __name__ == "__main__":
    unittest.main()
