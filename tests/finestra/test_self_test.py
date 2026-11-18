"""`meridiana --self-test` (ui/selftest.py; task 18f), the packages' smoke test: the program checks itself offscreen,
and never in the folders of whoever runs it. On 25/10/2026 a run of the program from a build session, before the
self-test existed, opened its window on Daniel's screen and saved its settings and window in his real folders: the
self-test isolates itself, whatever the environment it is given. PySide6 (the run is a process of its own)."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _setup

from meridiana.paths import Paths
from meridiana.ui import selftest

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class Isolation(unittest.TestCase):
    def test_every_folder_of_the_program_and_its_caches_go_in_the_test_folder(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        # a user's environment: Windows' folders, a Linux desktop that asks Qt for Wayland
        environ = {"APPDATA": "C:/Users/u/AppData/Roaming", "LOCALAPPDATA": "C:/Users/u/AppData/Local",
                   "HOME": "/home/u", "QT_QPA_PLATFORM": "wayland", "XDG_CONFIG_HOME": "/home/u/.config"}
        selftest.isolate(folder, environ)
        paths = Paths.from_env(environ)
        for p in (paths.config, paths.state, paths.data, paths.cache, paths.config_file, paths.log_file):
            self.assertTrue(str(p).startswith(str(folder)), p)
        self.assertEqual(environ["QT_QPA_PLATFORM"], "offscreen")          # never a window on a screen
        self.assertEqual(environ["QML_DISABLE_DISK_CACHE"], "1")            # Qt's caches in the user's folder
        self.assertEqual(environ["QT_DISABLE_SHADER_DISK_CACHE"], "1")
        self.assertTrue(environ["MPLCONFIGDIR"].startswith(str(folder)))
        environ["MERIDIANA_SELF_TEST_PLATFORM"] = "minimal"                  # asked for by name only
        selftest.isolate(folder, environ)
        self.assertEqual(environ["QT_QPA_PLATFORM"], "minimal")


class Run(unittest.TestCase):
    def test_the_self_test_passes_and_leaves_nothing_in_the_users_folders(self):
        tmp = Path(tempfile.mkdtemp(prefix="meridiana-self-test-run-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        home = tmp / "home"
        home.mkdir()
        left_out = ("QT_QPA_PLATFORM", "MPLCONFIGDIR", "QML_DISABLE_DISK_CACHE", "QT_DISABLE_SHADER_DISK_CACHE")
        env = {k: v for k, v in os.environ.items() if not k.startswith("XDG_") and k not in left_out}
        # the user's folders, all of them in `home`: whatever the run writes there is a failure
        env.update(HOME=str(home), USERPROFILE=str(home), APPDATA=str(home / "AppData" / "Roaming"),
                   LOCALAPPDATA=str(home / "AppData" / "Local"), PYTHONPATH=str(_setup.ROOT / "src"))
        report = tmp / "report.txt"
        done = subprocess.run([sys.executable, "-m", "meridiana", "--self-test", str(report)], env=env,
                              cwd=str(tmp), capture_output=True, timeout=600)
        text = report.read_text(encoding="utf-8") if report.exists() else done.stderr.decode(errors="replace")
        self.assertEqual(done.returncode, 0, text)
        self.assertIn("PASS all: 0 failed", text)
        for name in ("layout", "3D scene", "energy", "PDF report", "manual", "catalogue it"):
            self.assertRegex(text, rf"(?m)^PASS {name}:")
        self.assertEqual([str(p.relative_to(home)) for p in home.rglob("*")], [])


if __name__ == "__main__":
    unittest.main()
