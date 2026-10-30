import unittest
from types import SimpleNamespace
from unittest.mock import Mock
import _setup  # noqa: F401
from meridiana import app, config

class Startup(unittest.TestCase):
    def host(self, status="done", recovered=False):
        return SimpleNamespace(cfg=config.Config(tour_status=status,last_project="old.mer"),
            offer_recovery=Mock(return_value=recovered),open_path=Mock(return_value=True),open_file_page=Mock())

    def test_first_start_is_new_with_tour_and_later_start_is_open(self):
        first=self.host("new")
        self.assertTrue(app.prepare_workspace(first,None))
        first.open_file_page.assert_called_once_with("new")
        later=self.host()
        self.assertFalse(app.prepare_workspace(later,None))
        later.open_file_page.assert_called_once_with("open")
        later.open_path.assert_not_called()

    def test_explicit_project_and_recovery_take_precedence(self):
        for status in ("new","done"):
            host=self.host(status)
            self.assertFalse(app.prepare_workspace(host,"chosen.mer"))
            host.open_path.assert_called_once_with("chosen.mer")
            host.open_file_page.assert_not_called()
        host=self.host("new",True)
        self.assertFalse(app.prepare_workspace(host,"chosen.mer"))
        host.open_path.assert_not_called()
        host.open_file_page.assert_not_called()

    def test_failed_explicit_open_shows_project_chooser_without_starting_tour(self):
        host=self.host("new");host.open_path.return_value=False
        self.assertFalse(app.prepare_workspace(host,"missing.mer"))
        host.open_file_page.assert_called_once_with("open")


    def test_only_a_document_argument_is_an_explicit_project(self):
        from pathlib import Path
        self.assertIsNone(app.explicit_project(["meridiana"]))
        self.assertIsNone(app.explicit_project(["meridiana", "--verbose"]))
        self.assertEqual(app.explicit_project(["Meridiana.exe", "C:/Lavori/tetto è.mer"]), Path("C:/Lavori/tetto è.mer"))

    def test_qt_options_on_the_command_line_are_not_a_project(self):
        # «meridiana -platform offscreen»: the value of a Qt option was taken for a project, a warning box stopped
        # the start (it had been hidden by the exists() check the R07 start removed)
        import os
        import subprocess
        import sys
        import tempfile
        from pathlib import Path
        from meridiana.paths import Paths
        root = Path(tempfile.mkdtemp())
        env = dict(os.environ, XDG_CONFIG_HOME=str(root / "c"), XDG_STATE_HOME=str(root / "s"),
                   XDG_DATA_HOME=str(root / "d"), XDG_CACHE_HOME=str(root / "k"),
                   MERIDIANA_SCREENSHOT=str(root / "shot.png"), MERIDIANA_SCREENSHOT_DELAY="2")
        env.pop("QT_QPA_PLATFORM", None)
        paths = Paths.from_env(env)
        config.save(config.Config(background="none", network_pvgis=False, tour_status="done"), paths.config_file)
        src = Path(app.__file__).resolve().parents[1]
        env["PYTHONPATH"] = str(src)
        try:
            run = subprocess.run([sys.executable, "-m", "meridiana", "-platform", "offscreen"], env=env,
                                 cwd=str(root), timeout=90, capture_output=True, text=True, errors="replace")
        except subprocess.TimeoutExpired:
            self.fail("the start stopped: an argument of Qt was opened as a project")
        self.assertEqual(run.returncode, 0, run.stderr[-2000:])
        self.assertTrue((root / "shot.png").exists())
        self.assertNotIn("could not be opened", (paths.state / "meridiana.log").read_text(encoding="utf-8")
                         if (paths.state / "meridiana.log").exists() else "")
