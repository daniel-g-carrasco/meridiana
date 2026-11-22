"""The start of the Qt Quick window (gui/application.py main; r30-struttura A4): what the Widgets start did and the Quick
did not. Qt's own options on the command line are not a project to open (R07); a file that is not a project opens
the window and says so, never a start that ends without one; what goes wrong is kept in the profile's log and an
error nobody caught is said in the status bar; Qt's own words are in the language of the window (R26) and a tooltip
still knows a key; a run for a photograph (MERIDIANA_SCREENSHOT) writes it and ends; the processes a start from a
checkout launches find the package (bin/meridiana).

    python -m unittest quick.sistema.test_start
"""
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtCore import QCoreApplication, QObject, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlEngine

from _fixtures import capannone
from meridiana.app.platform import config, log
from meridiana.app.platform.paths import Paths
from quick.gestures import pump

ROOT = Path(__file__).resolve().parents[3]
SRC = str(ROOT / "src")


def profile_paths(profile: Path) -> Paths:
    return Paths(*(profile / "quick-profile" / name for name in ("config", "state", "data", "cache")))


def environment(**extra: str) -> dict:
    env = dict(os.environ, PYTHONPATH=SRC, QT_QPA_PLATFORM="offscreen", QSG_RENDER_LOOP="basic",
               MERIDIANA_PRELOAD="0", **extra)
    for name in ("MERIDIANA_TEST_SCREEN", "MERIDIANA_INSTANCE"):
        if name not in extra:
            env.pop(name, None)
    return env


class Photograph(unittest.TestCase):
    """Starts of Meridiana itself (`python -m meridiana`), offscreen, each with a profile of its own, ended by the
    photograph they are asked for."""

    def start(self, folder: Path, *arguments: str, command=None, **extra: str):
        profile = folder / "profile"
        shot = folder / "window.png"
        env = environment(MERIDIANA_SCREENSHOT=str(shot), MERIDIANA_SCREENSHOT_DELAY="3", **extra)
        try:
            run = subprocess.run([*(command or [sys.executable, "-m", "meridiana"]), *arguments, "--profile",
                                  str(profile)], env=env, cwd=str(folder), timeout=240, capture_output=True, text=True,
                                 errors="replace", check=False)
        except subprocess.TimeoutExpired:
            self.fail("the start did not end with its photograph")
        log_file = profile_paths(profile).log_file
        return run, shot, log_file.read_text(encoding="utf-8") if log_file.exists() else ""

    def test_qt_options_on_the_command_line_are_not_a_project(self):
        # «meridiana -platform offscreen»: the value of a Qt option was taken for a project to open (R07, then on the
        # Widgets window; the Quick gave Qt no argument at all, and argparse took «offscreen» for the project)
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as scratch:
            run, shot, said = self.start(Path(scratch), "-platform", "offscreen")
            self.assertEqual(run.returncode, 0, run.stderr[-2000:])
            self.assertTrue(shot.exists())
            self.assertNotIn("could not be opened", run.stderr + said)
            self.assertNotIn("offscreen", said)

    def test_a_file_that_is_not_a_project_opens_the_window_and_is_said(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as scratch:
            folder = Path(scratch)
            broken = folder / "rotto.mer"
            broken.write_text("{ not a project", encoding="utf-8")
            run, shot, said = self.start(folder, str(broken))
            self.assertEqual(run.returncode, 0, run.stderr[-2000:])
            self.assertTrue(shot.exists(), "the window opened all the same")
            self.assertIn("rotto.mer", said)                    # kept in the profile's log: a package has no console

    def test_a_start_from_a_checkout_gives_the_package_to_the_processes_it_starts(self):
        # bin/meridiana puts src on its own path; the computation's process (`python -m meridiana.gui.backend.
        # shell_compute`) did not find the package unless PYTHONPATH was set by hand: no year, said only in the log
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as scratch:
            folder = Path(scratch)
            project = folder / "tetto.mer"
            capannone("Tetto").save(project)
            env = environment()
            del env["PYTHONPATH"]
            profile = folder / "profile"
            shot = folder / "window.png"
            env.update(MERIDIANA_SCREENSHOT=str(shot), MERIDIANA_SCREENSHOT_DELAY="8")
            run = subprocess.run([sys.executable, str(ROOT / "bin" / "meridiana"), str(project), "--profile",
                                  str(profile)], env=env, cwd=str(folder), timeout=240, capture_output=True, text=True,
                                 errors="replace", check=False)
            self.assertEqual(run.returncode, 0, run.stderr[-2000:])
            self.assertTrue(shot.exists())
            self.assertNotIn("No module named", run.stderr)

    def test_study_56_qt_keeps_its_disk_caches_in_the_profile_for_this_version_alone(self):
        # the program's start keeps the compiled QML in <profile>/qt-cache/<version>/qml (the window built in 6,6-7,0
        # s instead of 10,7-15,7 offscreen); the folder of another version goes, a folder not ours stays; the user's
        # own folders are never written (the R594 guard of this run sees them)
        from PySide6 import __version__ as qt_version
        from meridiana import __version__
        from meridiana.app.platform import qt_cache
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as scratch:
            folder = Path(scratch)
            caches = folder / "profile" / qt_cache.FOLDER
            old = caches / "0.0.1-qt6.0.0"
            old.mkdir(parents=True)
            (old / qt_cache.MARK).touch()
            (caches / "altro").mkdir()
            run, shot, _said = self.start(folder, MERIDIANA_QT_DISK_CACHE="1")
            self.assertEqual(run.returncode, 0, run.stderr[-2000:])
            self.assertTrue(shot.exists())
            mine = caches / qt_cache.key_of(__version__, qt_version)
            self.assertGreater(len(list((mine / "qml").glob("*.qmlc"))), 50)
            self.assertEqual(sorted(p.name for p in caches.iterdir()), sorted(["altro", mine.name]))
            self.assertNotIn("pipeline cache", run.stderr)          # no warning of Qt about the pipelines' file

    def test_the_options_of_the_widgets_window_are_said_gone_and_open_nothing(self):
        for option in ("--widgets", "--self-test", "--tour", "--tour=3"):
            with self.subTest(option=option):
                run = subprocess.run([sys.executable, "-m", "meridiana", option, "report.txt"], env=environment(),
                                     timeout=120, capture_output=True, text=True, errors="replace", check=False)
                self.assertEqual(run.returncode, 2, run.stderr[-2000:])
                self.assertIn(option.partition("=")[0], run.stderr)
                self.assertIn("package_check", run.stderr)


class InProcess(unittest.TestCase):
    """The program's own start in this process (quick.app.main), offscreen, on a temporary profile; what it changes
    of the process (the hooks of the errors, the log's file, Qt's words) is put back."""

    def setUp(self):
        from meridiana.gui import application as quick
        from meridiana.gui import qt_translations
        self.quick = quick
        self.app = quick.create_app()
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.profile = self.folder / "profile"
        self.paths = profile_paths(self.profile)
        hooks = sys.excepthook, threading.excepthook, log.file(), log._tell

        def put_back():
            sys.excepthook, threading.excepthook = hooks[0], hooks[1]
            log.setup(hooks[2])
            log.tell_with(hooks[3])
            qt_translations.install(self.app, "en")
            pump(50)
        self.addCleanup(put_back)

    def run_main(self, arguments, look, wait_ms=600):
        """main with `arguments`; `look(window, shell)` once the window is up (it may return a callable to run a
        little later), then the end."""
        def find():
            window = next((w for w in QGuiApplication.allWindows() if w.objectName() == "quickWindow"), None)
            if window is None or not window.isVisible():
                QTimer.singleShot(100, find)
                return
            shell = QQmlEngine.contextForObject(window).contextProperty("shell")
            later = look(window, shell)
            if callable(later):
                QTimer.singleShot(wait_ms, lambda: (later(), QGuiApplication.quit()))
            else:
                QTimer.singleShot(wait_ms, QGuiApplication.quit)
        QTimer.singleShot(300, find)
        with mock.patch.dict(os.environ, {"MERIDIANA_INSTANCE": "off"}), \
                mock.patch("meridiana.gui.startup.windows_identity"):
            return self.quick.main([*arguments, "--profile", str(self.profile)])

    def test_qt_speaks_the_language_of_the_window_and_a_tooltip_still_knows_a_key(self):
        from meridiana.gui.style.popups import tip_html
        self.paths.config.mkdir(parents=True)
        config.save(config.Config(language="it"), self.paths.config_file)
        project = self.folder / "tetto.mer"
        capannone("Tetto").save(project)
        seen = {}

        def look(_window, _shell):
            seen["cancel"] = QCoreApplication.translate("QPlatformTheme", "Cancel")
            # the Quick writes its keys in Qt's portable words («Del»), Qt's Italian says «Canc»: still a key
            seen["tip"] = tip_html("Elimina (Del)\nToglie ciò che è scelto", "#ffffff", "#000000")
            seen["words"] = tip_html("Elimina (vedi sotto)\nToglie ciò che è scelto", "#ffffff", "#000000")
        self.assertEqual(self.run_main([str(project)], look), 0)
        self.assertEqual(seen["cancel"], "Annulla")
        self.assertIn(">Del</span>", seen["tip"])
        self.assertNotIn("<span", seen["words"].split("</p>")[0])

    def test_an_error_nobody_caught_is_kept_in_the_log_and_said_in_the_status_bar(self):
        project = self.folder / "tetto.mer"
        capannone("Tetto").save(project)
        seen = {}

        def look(_window, shell):
            def fail():
                raise RuntimeError("una prova di errore")
            QTimer.singleShot(0, fail)
            return lambda: seen.update(notice=shell.property("notice"), file=log.file())
        with mock.patch("sys.stderr"):
            self.assertEqual(self.run_main([str(project)], look), 0)
        self.assertEqual(seen["file"], self.paths.log_file)
        self.assertIn("una prova di errore", seen["notice"])
        self.assertIn("meridiana.log", seen["notice"])
        self.assertIn("una prova di errore", self.paths.log_file.read_text(encoding="utf-8"))

    def test_an_error_in_a_thread_is_said_from_the_windows_thread(self):
        project = self.folder / "tetto.mer"
        capannone("Tetto").save(project)
        seen = {}

        def look(_window, shell):
            def fail():
                raise RuntimeError("un errore in un thread")
            worker = threading.Thread(target=fail)
            worker.start()
            worker.join(10)
            return lambda: seen.update(notice=shell.property("notice"))
        with mock.patch("sys.stderr"):
            self.assertEqual(self.run_main([str(project)], look), 0)
        self.assertIn("un errore in un thread", seen["notice"])

    def test_a_file_that_is_not_a_project_is_said_in_the_window(self):
        broken = self.folder / "rotto.mer"
        broken.write_text("{ not a project", encoding="utf-8")
        seen = {}

        def look(window, shell):
            seen.update(notice=shell.property("notice"), kind=shell.property("noticeKind"), title=window.title(),
                        dialog=window.findChild(QObject, "recoveryDialog").property("visible"))
        with mock.patch("sys.stderr"):
            self.assertEqual(self.run_main([str(broken)], look), 0)
        self.assertIn("rotto.mer", seen["notice"])
        self.assertEqual(seen["kind"], "error-open")
        self.assertEqual(seen["title"], "Meridiana")            # an empty project, without a file
        self.assertFalse(seen["dialog"])


class RecordedWeather(unittest.TestCase):
    def test_the_check_of_a_package_is_given_the_recorded_year_of_rho(self):
        # package_check computed no year on a profile of its own («Fetch the weather of the site first»): from the
        # sources it now takes the repository's recorded year as the program's start does, a package is given it
        from meridiana.core.model import model
        from meridiana.core.energy import meteo
        from meridiana.gui.sample import RECORDED, recorded_weather
        with tempfile.TemporaryDirectory() as scratch:
            cache = Path(scratch)
            rho = model.Project()
            rho.site.lat, rho.site.lon = 45.5226, 9.03
            self.assertFalse(recorded_weather(rho, cache, cache / "not there.json.gz"))
            self.assertTrue(recorded_weather(rho, cache, RECORDED))
            self.assertTrue(meteo._cache_file(cache, "tmy", 45.5226, 9.03).is_file())
            self.assertTrue(recorded_weather(rho, cache / "again"))            # from a checkout: the repository's
            elsewhere = model.Project()
            elsewhere.site.lat, elsewhere.site.lon = 41.9, 12.5
            self.assertFalse(recorded_weather(elsewhere, cache / "elsewhere", RECORDED))
            self.assertFalse((cache / "elsewhere").exists())


if __name__ == "__main__":
    unittest.main()
