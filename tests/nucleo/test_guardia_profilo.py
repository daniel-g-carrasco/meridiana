"""R594: the guard of the user's own folders of Meridiana. During tests/quick/pagine a reading of an IFC put its
geometry in %LOCALAPPDATA%\\Meridiana\\cache\\ifc. The run takes the files of those folders at its start and fails
when it has written there (tests/_setup.py, tools/run_tests.py); these tests say the guard sees a write."""

import os
import tempfile
import unittest
from pathlib import Path

import _setup


class Guard(unittest.TestCase):
    def test_a_new_a_changed_and_a_gone_file_are_seen(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "cache").mkdir()
            (root / "kept.txt").write_text("a", encoding="utf-8")
            (root / "changed.txt").write_text("a", encoding="utf-8")
            (root / "gone.txt").write_text("a", encoding="utf-8")
            before = _setup.profile_files([root])
            self.assertEqual(_setup.profile_changes(before, _setup.profile_files([root])), [])
            (root / "cache" / "ifc-model.npz").write_bytes(b"x")
            (root / "changed.txt").write_text("ab", encoding="utf-8")
            (root / "gone.txt").unlink()
            changes = _setup.profile_changes(before, _setup.profile_files([root]))
        self.assertEqual([c.split(" ", 1)[0] for c in changes], ["changed", "gone", "new"])
        self.assertTrue(changes[2].endswith("ifc-model.npz"))

    def test_the_folders_watched_are_the_users_and_not_the_tests_home(self):
        env = {"APPDATA": r"C:\U\me\AppData\Roaming", "LOCALAPPDATA": r"C:\U\me\AppData\Local",
               "HOME": "/home/me"}
        roots = [str(r) for r in _setup.profile_roots(env)]
        if os.name == "nt":
            self.assertEqual(sorted(roots), sorted([r"C:\U\me\AppData\Local\Meridiana",
                                                    r"C:\U\me\AppData\Roaming\Meridiana"]))
        else:
            self.assertTrue(all(r.startswith("/home/me/") for r in roots), roots)
        home = os.environ["HOME"]           # the tests' home (_setup): never what is watched
        self.assertFalse(any(str(r).startswith(home) for r in _setup.PROFILE_ROOTS), _setup.PROFILE_ROOTS)


if __name__ == "__main__":
    unittest.main()
