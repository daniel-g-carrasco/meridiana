"""Counterproofs independent of the future generic implementation."""

import tempfile
from pathlib import Path
import unittest

from profili import leaks


class ProfileBoundaries(unittest.TestCase):
    def test_directory_names_do_not_silently_authorize_italian_rules(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = ("profiles/generic/policy.py", "profiles/it_like/policy.py", "app/it/policy.py",
                     "data/profiles/it/policy.py")
            for name in paths:
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('SOURCE = "CEI 0-21"\n', encoding="utf-8")
            self.assertEqual({r["path"] for r in leaks.scan(root)}, set(paths))

    def test_core_profile_cannot_import_data_or_gui(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            policy = root / "core/rules/profiles/it/profile.py"
            policy.parent.mkdir(parents=True)
            policy.write_text("from meridiana.data import catalog\nfrom meridiana.gui import application\n", encoding="utf-8")
            self.assertEqual(leaks.core_profile_imports(root),
                             ["meridiana.data.catalog", "meridiana.gui.application"])
