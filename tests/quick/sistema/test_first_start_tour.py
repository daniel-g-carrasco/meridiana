"""The guided tour offered at the first start (Daniel 10/11/2026: «--tour» does not come back, the tour stays in Meridio;
r29 offered it from MainWindow._offer_tour): on an empty profile Meridio opens with a welcome, «Start tour» or «Later»;
a project asked for by name, a copy to recover, a run for a photograph and a profile that has seen it are not
interrupted.

    python -m unittest quick.sistema.test_first_start_tour
"""
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QGuiApplication

from _fixtures import capannone
from meridiana.app.platform import config
from quick.gestures import pump


class _Start:
    """quick.main in this process, offscreen, on a temporary profile; `look(window, help)` is asked every 100 ms until
    it answers True (or 60 times), then the window is quit."""

    def __init__(self, test):
        from meridiana.app.platform import log
        from meridiana.gui import application, qt_translations
        self.application = application
        qt = application.create_app()
        hooks = sys.excepthook, threading.excepthook, log.file(), log._tell

        def put_back():                 # what main changes of the process: the hooks of the errors, the log, Qt's words
            sys.excepthook, threading.excepthook = hooks[0], hooks[1]
            log.setup(hooks[2])
            log.tell_with(hooks[3])
            qt_translations.install(qt, "en")
        test.addCleanup(put_back)

    def run(self, argv, look, environ=None):
        seen = {"tries": 0}

        def poll():
            window = next((w for w in QGuiApplication.allWindows() if w.objectName() == "quickWindow"), None)
            seen["tries"] += 1
            if window is not None and look(window, seen):
                QTimer.singleShot(0, QGuiApplication.quit)
                return
            if seen["tries"] < 60:
                QTimer.singleShot(100, poll)
            else:
                QGuiApplication.quit()
        QTimer.singleShot(200, poll)
        env = {"MERIDIANA_INSTANCE": "off", **(environ or {})}
        with mock.patch.dict(os.environ, env), mock.patch("meridiana.gui.startup.windows_identity"):
            code = self.application.main(argv)
        pump(50)
        return code, seen


class FirstStart(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.scratch.cleanup)
        self.profile = Path(self.scratch.name) / "profile"
        self.start = _Start(self)
        self.offers = []
        from meridiana.gui.backend import assistant_help
        real = assistant_help.AssistantHelp.offerTour

        def recorded(service):
            shown = real(service)
            self.offers.append((service, shown))
            return shown
        patcher = mock.patch.object(assistant_help.AssistantHelp, "offerTour", recorded)
        patcher.start()
        self.addCleanup(patcher.stop)

    def config_file(self):
        return self.profile / "quick-profile" / "config" / "config.json"

    def page_of_meridio(self, window):
        layer = window.findChild(QObject, "assistantLayer")
        return layer.property("page") if layer is not None else None

    def test_an_empty_profile_is_offered_the_tour_by_meridio(self):
        def look(window, seen):
            if not self.offers:
                return False
            service, shown = self.offers[-1]
            seen.update(shown=shown, invitation=service.tourInvitation, active=service.tourActive,
                        title=service.tourStep["title"], page=self.page_of_meridio(window))
            return True
        code, seen = self.start.run(["--profile", str(self.profile)], look)
        self.assertEqual(code, 0)
        self.assertEqual(len(self.offers), 1, seen)
        self.assertTrue(seen["shown"] and seen["invitation"] and seen["active"], seen)
        self.assertEqual(seen["title"], "Let Meridio show you around")
        self.assertEqual(seen["page"], "tour", "Meridio opens on the welcome")
        # nothing answered: the next start offers it again
        self.assertEqual(config.load(self.config_file()).tour_status, "new")

    def test_a_project_asked_for_by_name_is_not_interrupted(self):
        file = Path(self.scratch.name) / "tetto.mer"
        capannone("Tetto").save(file)

        def look(window, seen):
            return seen["tries"] >= 25          # 2.5 s: well past the delay of the offer
        code, _seen = self.start.run([str(file), "--profile", str(self.profile)], look)
        self.assertEqual(code, 0)
        self.assertEqual(self.offers, [])

    def test_a_profile_that_answered_is_not_asked_again(self):
        cfg = config.Config()
        cfg.tour_status = "skipped"
        self.config_file().parent.mkdir(parents=True)
        config.save(cfg, self.config_file())

        def look(window, seen):
            return seen["tries"] >= 25
        code, _seen = self.start.run(["--profile", str(self.profile)], look)
        self.assertEqual(code, 0)
        self.assertEqual(self.offers, [])

    def test_a_run_for_a_photograph_is_not_asked(self):
        shot = Path(self.scratch.name) / "shot.png"

        def look(window, seen):
            return False                        # the photograph ends the run by itself
        code, _seen = self.start.run(["--profile", str(self.profile)], look,
                                     {"MERIDIANA_SCREENSHOT": str(shot), "MERIDIANA_SCREENSHOT_DELAY": "2.5"})
        self.assertEqual(code, 0)
        self.assertTrue(shot.is_file())
        self.assertEqual(self.offers, [])


class TheWelcome(unittest.TestCase):
    """Its two answers, on the service alone."""

    def make(self):
        from meridiana.gui.backend.assistant_help import AssistantHelp
        cfg = config.Config()
        saved = []
        service = AssistantHelp(cfg=cfg, save=lambda: saved.append((cfg.tour_status, cfg.tour_step)))
        return service, cfg, saved

    def test_start_tour_goes_to_the_first_step(self):
        service, cfg, saved = self.make()
        targets = []
        service.navigateRequested.connect(targets.append)
        self.assertTrue(service.offerTour())
        self.assertEqual(saved, [], "offering writes nothing")
        self.assertEqual(service.tourStep["progress"], "Welcome")
        service.previous()                       # nothing before the welcome
        self.assertTrue(service.tourInvitation)
        service.next()                           # «Start tour»
        self.assertFalse(service.tourInvitation)
        self.assertTrue(service.tourActive)
        self.assertEqual((service.tourIndex, service.tourStep["number"]), (0, 1))
        self.assertEqual(cfg.tour_status, "active")
        self.assertEqual(len(targets), 1)
        self.assertFalse(service.offerTour(), "offered once")

    def test_later_skips_it_for_good(self):
        service, cfg, saved = self.make()
        dismissed = []
        service.dismissed.connect(lambda: dismissed.append(True))
        service.offerTour()
        service.pauseTour()                      # «Later», or Meridio closed while the welcome is shown
        self.assertEqual(cfg.tour_status, "skipped")
        self.assertFalse(service.tourActive or service.tourInvitation)
        self.assertEqual(dismissed, [True])
        self.assertFalse(service.offerTour())
        service.startTour(False)                 # still there from Help and Meridio's menu
        self.assertTrue(service.tourActive)
        self.assertFalse(service.tourInvitation)


if __name__ == "__main__":
    unittest.main()
