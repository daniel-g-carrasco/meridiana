"""The files of every version (tests/formati/file) open in a real Quick window unchanged, and a bad or future file
is refused before a window is made (once R389's parity test, kept for the Quick when the Widgets went)."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import _setup
from _fixtures import capannone_rho
from meridiana.app.platform import config
from meridiana.core.model import model
from quick.aiuti.differential import canonical_project
from quick.aiuti.formats import QuickFiles, current_config_roundtrip, frozen_cases

setUpModule = _setup.keep_global_state


class FormatInventoryTest(unittest.TestCase):
    def test_every_frozen_file_is_classified_and_latest_versions_present(self):
        cases = frozen_cases()
        self.assertEqual({c.path for c in cases}, set(_setup.FORMATS.iterdir()))
        self.assertIn(f"progetto-v{model.FORMAT_VERSION}.meridiana", {c.path.name for c in cases})
        self.assertIn(f"config-v{config.CONFIG_VERSION}.json", {c.path.name for c in cases})
        self.assertEqual(sum(c.kind == "invalid_project" for c in cases), 3)


class FrozenQuickTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        from meridiana.gui.application import create_app
        create_app()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
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
        from meridiana.core.model.underlay import Underlay
        project = capannone_rho()
        project.underlays = [Underlay("u1", image=base64.b64encode(b"recorded asset").decode())]
        project.report = {"attachments": [{"title": "Recorded attachment", "path": "sheet.pdf",
                                            "data": base64.b64encode(b"attachment bytes").decode()}]}
        source = self.folder / "source.mer"
        project.save(source)
        self.quick.open(source)
        expected, _ = model.Project.load(source)
        self.assertEqual(canonical_project(self.quick.project), canonical_project(expected))
        self.assertEqual(self.quick.project.underlays[0].image, project.underlays[0].image)

    def test_current_config_roundtrip_keeps_current_version_and_choices(self):
        original = _setup.FORMATS / f"config-v{config.CONFIG_VERSION}.json"
        result = current_config_roundtrip(original, self.folder)
        self.assertEqual(result["status"], "equal", result)
        saved = json.loads((self.folder / "current-config-saved.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["version"], config.CONFIG_VERSION)


if __name__ == "__main__":
    unittest.main()
