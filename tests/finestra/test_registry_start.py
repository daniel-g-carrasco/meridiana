"""A damaged registry does not stop project work or get overwritten at startup (R150)."""

import tempfile
import unittest
from pathlib import Path

import _setup
from _fixtures import capannone

from meridiana import config, registry
from meridiana.paths import Paths

setUpModule = _setup.keep_global_state


class RegistryStart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_a_damaged_registry_leaves_the_original_untouched_and_the_window_usable(self):
        root = Path(tempfile.mkdtemp())
        paths = Paths(root / "config", root / "state", root / "data", root / "cache")
        paths.data.mkdir(parents=True)
        damaged = paths.data / "registry.sqlite3"
        damaged.write_bytes(b"invented damaged registry")
        before = damaged.read_bytes()
        original = registry.Registry

        def fail_damaged(path):
            if Path(path) == damaged:
                raise registry.RegistryError("the registry schema is newer")
            return original(path)

        from unittest import mock
        with mock.patch("meridiana.ui.window.registry.Registry", side_effect=fail_damaged):
            _setup.window(self, capannone(), cfg=config.Config(background="none"), paths=paths)
        self.assertNotEqual(self.win.registry.path, damaged)
        self.assertEqual(damaged.read_bytes(), before)
        self.assertIn("temporary", self.win.registry_error)
        self.assertTrue(any("temporary" in parts[1] for _kind, parts in self.dialogs))
        self.assertEqual(self.win.project.name, capannone().name)


if __name__ == "__main__":
    unittest.main()
