"""Autosave and recovery in the Quick window (recovery.py, gui/backend/recovery_part.py; r30-struttura A2): a copy of
the unsaved changes goes to the state folder and a save takes it away; a copy left by a Meridiana that stopped without
saving is offered back at the start (with a project asked for by name only its own) and when its project is opened;
«No» deletes it; the copy of a Meridiana still running is neither offered nor deleted; the window closed without a
question about its changes (the end of a session) keeps a copy for the next start. The Widgets window's tests of the same rules were in
tests/finestra (test_second_start.py, test_file.py).

    python -m unittest quick.sistema.test_recovery
"""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtCore import QObject, Qt, QTimer

from _fixtures import capannone
from meridiana import PACKAGE_DIR
from meridiana.core.model import model
from meridiana.app.project import recovery
from meridiana.i18n import _
from quick.gestures import pump

SRC = str(PACKAGE_DIR.parent)          # the folder the package is in (src/)

OWNER = """
import sys
from pathlib import Path
from meridiana.core.model import model
from meridiana.app.project import recovery
from meridiana.i18n import _
state = Path(sys.argv[1])
recovery.claim(state)
recovery.write(state, Path(sys.argv[2]), model.Project(name="Still open").to_json())
print("ready", flush=True)
sys.stdin.readline()
recovery.release(state)
"""


def left_behind(state: Path, path: Path | None, name: str) -> Path:
    """A copy as a Meridiana that stopped without saving leaves it: nobody's."""
    project = capannone(name)
    return recovery.write(state, path, project.to_json())


class Window(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from meridiana.gui.application import create_app
        cls.app = create_app()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.folder = Path(self.temp.name)
        self.file = self.folder / "tetto.mer"
        capannone("Tetto").save(self.file)
        self.other = self.folder / "altro.mer"
        capannone("Altro").save(self.other)
        self.host = None
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.close)

    def open(self, path=None, claim=True):
        from meridiana.gui.application import QuickWindow
        project = model.Project.load(path)[0] if path else capannone("Senza file")
        self.host = QuickWindow(project, self.folder / "cache", real_views=True, path=path)
        self.win = self.host.window
        self.win.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.win.show()
        pump(200)
        self.session = self.host.bridge.session
        self.files = self.host.parts.controllers["files"]
        self.part = self.host.parts.controllers["recovery"]
        self.state = self.host.paths.state
        if claim:
            self.part.claim()
        return self.host

    def close(self):
        if self.host is not None:
            host, self.host = self.host, None
            host.close()
            host.parts.controllers["recovery"].release()
            pump(50)

    def wait(self, condition, seconds=20):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            pump(20)
            if condition():
                return True
        return False

    def dialog(self):
        return self.win.findChild(QObject, "recoveryDialog")

    def edit(self, name="Tetto, cambiato"):
        self.session.edit("Rename", lambda p: setattr(p, "name", name))

    # the copy of the work in hand

    def test_unsaved_changes_get_a_copy_and_a_save_takes_it_away(self):
        self.open(self.file)
        slot = recovery.slot(self.state, self.file)
        self.assertFalse(self.part.autosave(), "nothing to save, no copy")
        self.edit()
        self.assertTrue(self.part.autosave())
        self.assertTrue(self.wait(lambda: self.session.autosaved == slot))
        self.assertTrue(slot.exists())
        self.files.write()
        self.assertTrue(self.wait(lambda: not self.session.dirty() and not self.files.property("busy")))
        self.assertTrue(self.wait(lambda: not slot.exists()), "the save takes the copy away")
        self.assertIsNone(self.session.autosaved)

    def test_a_copy_written_while_the_project_was_saved_does_not_stay(self):
        self.open(self.file)
        self.edit()
        self.assertTrue(self.part.autosave())
        self.session.save(self.file)                            # saved before the copy's thread came back
        self.assertTrue(self.wait(lambda: self.part._thread is None))
        self.assertFalse(recovery.slot(self.state, self.file).exists())

    def test_the_timer_of_the_copies_runs_while_the_window_is_open(self):
        from meridiana.gui.backend import recovery_part
        self.open(self.file)
        self.assertTrue(self.part.timer.isActive())
        self.assertEqual(self.part.timer.interval(), recovery_part.AUTOSAVE_MS)

    # a copy left behind

    def test_the_copy_of_the_project_asked_for_is_offered_and_yes_recovers_it(self):
        self.open(self.file)
        copy = left_behind(self.state, self.file, "Tetto, non salvato")
        self.assertFalse(self.dialog().property("visible"))
        self.assertTrue(self.part.offer(self.file))
        pump(100)
        self.assertTrue(self.dialog().property("visible"))
        self.assertIn("tetto.mer", self.part.property("question"))
        self.assertEqual(self.session.project.name, "Tetto")    # nothing changes before the answer
        self.part.answer(True)
        pump(100)
        self.assertFalse(self.dialog().property("visible"))
        self.assertEqual(self.session.project.name, "Tetto, non salvato")
        self.assertEqual(self.session.path, self.file)
        self.assertTrue(self.session.dirty(), "recovered: not saved yet")
        self.assertEqual(self.win.title(), "tetto.mer * - Meridiana")
        self.assertEqual(self.host.shell.property("notice"), _("Recovered: save it to keep it"))
        self.assertTrue(copy.exists(), "the copy stays until the project is saved")
        self.files.write()
        self.assertTrue(self.wait(lambda: not copy.exists()))
        self.assertEqual(model.Project.load(self.file)[0].name, "Tetto, non salvato")

    def test_the_buttons_of_the_question_answer_it(self):
        self.open(self.file)
        copy = left_behind(self.state, self.file, "Tetto, non salvato")
        self.part.offer(self.file)
        pump(100)
        self.dialog().reject()                                  # «No»
        pump(100)
        self.assertFalse(copy.exists(), "«No» deletes the copy")
        self.assertEqual(self.session.project.name, "Tetto")
        self.assertFalse(self.part.property("offered"))
        self.assertFalse(self.part.offer(self.file), "nothing left to offer")
        copy = left_behind(self.state, self.file, "Tetto, di nuovo")
        self.part.offer(self.file)
        pump(100)
        self.dialog().accept()                                  # «Yes»
        pump(100)
        self.assertEqual(self.session.project.name, "Tetto, di nuovo")

    def test_with_a_project_asked_for_by_name_another_projects_copy_waits(self):
        self.open(self.file)
        copy = left_behind(self.state, self.other, "Altro, non salvato")
        self.assertFalse(self.part.offer(self.file))            # «Yes» on it would have left the project asked for unopened
        self.assertFalse(self.part.property("offered"))
        self.assertTrue(copy.exists())
        self.assertTrue(self.part.offer())                      # a start without a project: the newest copy
        self.assertIn("altro.mer", self.part.property("question"))
        self.part.answer(True)
        pump(50)
        self.assertEqual(self.session.path, self.other)
        self.assertEqual(self.session.project.name, "Altro, non salvato")

    def test_the_copy_of_a_project_never_saved_comes_back_without_a_file(self):
        self.open()
        left_behind(self.state, None, "Mai salvato")
        self.assertTrue(self.part.offer())
        self.part.answer(True)
        pump(50)
        self.assertIsNone(self.session.path)
        self.assertEqual(self.session.project.name, "Mai salvato")
        self.assertTrue(self.session.dirty())

    def test_a_copy_that_cannot_be_read_is_said_and_set_aside(self):
        self.open(self.file)
        copy = left_behind(self.state, self.file, "Tetto, non salvato")
        self.part.offer(self.file)
        self.part._copy["project"] = {"format": "not a project"}
        with mock.patch("meridiana.app.platform.log.complain"):
            self.part.answer(True)
        pump(50)
        self.assertEqual(self.session.project.name, "Tetto")
        self.assertEqual(self.host.shell.property("noticeKind"), "error")
        self.assertFalse(copy.exists())
        self.assertTrue(copy.with_suffix(".unreadable").exists(), "not lost, not offered again")

    def test_the_copy_of_a_meridiana_still_running_is_neither_offered_nor_deleted(self):
        # the window open with unsaved changes, a double click on a project starts another one: it asked «Meridiana
        # stopped without saving...», false, and its «No» deleted the copy of the window still open (R07)
        self.open(self.file)
        process = subprocess.Popen([sys.executable, "-c", OWNER, str(self.state), str(self.other)],
                                   env=dict(os.environ, PYTHONPATH=SRC), stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: (process.kill(), process.wait(30), process.stdin.close(), process.stdout.close(),
                                 process.stderr.close()))
        self.assertEqual(process.stdout.readline().strip(), "ready")
        copy = recovery.slot(self.state, self.other)
        self.assertTrue(copy.exists())
        self.assertFalse(self.part.offer())
        self.assertFalse(self.part.offer(self.other))
        self.assertFalse(self.part.property("offered"))
        self.assertTrue(copy.exists())

    def test_a_project_opened_from_the_file_page_is_offered_its_copy(self):
        self.open(self.file)
        copy = left_behind(self.state, self.other, "Altro, non salvato")
        self.files.openChosen(str(self.other))
        self.assertTrue(self.wait(lambda: self.session.path == self.other), self.files.property("error"))
        self.assertEqual(self.session.project.name, "Altro")
        self.assertTrue(self.wait(lambda: self.part.property("offered")))
        self.assertTrue(copy.exists(), "opening the file does not delete its copy")
        self.part.answer(True)
        pump(50)
        self.assertEqual(self.session.project.name, "Altro, non salvato")
        self.assertEqual(self.session.path, self.other)

    def test_changes_discarded_for_another_project_take_their_copy_away(self):
        self.open(self.file)
        self.edit()
        self.part.autosave()
        slot = recovery.slot(self.state, self.file)
        self.assertTrue(self.wait(lambda: self.session.autosaved == slot))
        self.files.openChosen(str(self.other))
        self.files.resolveChanges("discard")
        self.assertTrue(self.wait(lambda: self.session.path == self.other), self.files.property("error"))
        self.assertTrue(self.wait(lambda: not slot.exists()))
        self.assertFalse(self.part.property("offered"))

    # the end of the window

    def test_a_window_closed_without_a_question_keeps_a_fresh_copy_for_the_next_start(self):
        # taken apart by the program (QuickWindow.close), as at the end of a session: closed with its cross the window
        # asks first (quick.sistema.test_close_question)
        self.open(self.file)
        self.edit("Tetto, chiuso senza domanda")
        state = self.state
        self.close()
        copies = recovery.pending(state, self.file)
        self.assertEqual(len(copies), 1)
        self.assertEqual(copies[0]["project"]["name"], "Tetto, chiuso senza domanda")
        # the next start offers it
        self.open(self.file)
        self.assertTrue(self.part.offer(self.file))
        self.part.answer(False)

    def test_quit_after_the_question_and_an_untouched_window_leave_no_copy(self):
        self.open(self.file)
        self.edit()
        self.part.autosave()
        self.assertTrue(self.wait(lambda: self.session.autosaved is not None))
        self.files.request("quit")                              # File > Quit: asks, here «Discard»
        self.assertTrue(self.files.property("confirmation"))
        state = self.state
        self.files.resolveChanges("discard")                    # the window closes
        pump(100)
        self.close()
        self.assertEqual(recovery.pending(state), [])
        self.open(self.other)
        state = self.state
        self.close()
        self.assertEqual(recovery.pending(state), [])

    def test_the_window_of_a_test_writes_no_copy_at_its_end(self):
        self.open(self.file, claim=False)
        self.edit()
        state = self.state
        self.close()
        self.assertEqual(recovery.pending(state), [])


class Start(unittest.TestCase):
    """The program's own start (quick.app.main), in this process, offscreen, on a temporary profile."""

    def test_a_start_with_a_project_offers_its_copy_and_lets_its_mark_go_at_the_end(self):
        from PySide6.QtGui import QGuiApplication

        import threading

        from meridiana.app.platform import log
        from meridiana.app.platform.paths import Paths
        from meridiana.gui import application as quick
        from meridiana.gui import qt_translations
        qt = quick.create_app()
        hooks = sys.excepthook, threading.excepthook, log.file(), log._tell

        def put_back():                 # what main changes of the process: the hooks of the errors, the log, Qt's words
            sys.excepthook, threading.excepthook = hooks[0], hooks[1]
            log.setup(hooks[2])
            log.tell_with(hooks[3])
            qt_translations.install(qt, "en")
        self.addCleanup(put_back)
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as scratch:
            folder = Path(scratch)
            profile = folder / "profile"
            file = folder / "tetto.mer"
            capannone("Tetto").save(file)
            paths = Paths(*(profile / "quick-profile" / name for name in ("config", "state", "data", "cache")))
            left_behind(paths.state, file, "Tetto, non salvato")
            left_behind(paths.state, folder / "altro.mer", "Altro, non salvato")
            seen = {}

            def look():
                window = next((w for w in QGuiApplication.allWindows() if w.objectName() == "quickWindow"), None)
                dialog = window.findChild(QObject, "recoveryDialog") if window is not None else None
                if dialog is None or not dialog.property("visible"):
                    seen["tries"] = seen.get("tries", 0) + 1
                    if seen["tries"] < 100:
                        QTimer.singleShot(100, look)
                    else:
                        QGuiApplication.quit()
                    return
                seen["question"] = window.findChild(QObject, "recoveryQuestion").property("text")
                seen["owners"] = len(list((paths.state / "recovery" / recovery.OWNERS).glob("*.lock")))
                dialog.accept()
                QTimer.singleShot(300, lambda: (seen.update(title=window.title()), QGuiApplication.quit()))
            QTimer.singleShot(300, look)
            with mock.patch.dict(os.environ, {"MERIDIANA_INSTANCE": "off"}), \
                    mock.patch("meridiana.gui.startup.windows_identity"):
                code = quick.main([str(file), "--profile", str(profile)])
            pump(50)
            self.assertEqual(code, 0)
            self.assertIn("tetto.mer", seen.get("question", ""), seen)
            self.assertEqual(seen["owners"], 1, "the start holds its mark while it runs")
            self.assertEqual(seen["title"], "tetto.mer * - Meridiana")
            # the end: its mark let go; the project recovered and closed without saving is still offered, the other
            # project's copy still waits
            self.assertEqual(list((paths.state / "recovery" / recovery.OWNERS).glob("*.lock")), [])
            names = sorted(c["project"]["name"] for c in recovery.pending(paths.state))
            self.assertEqual(names, ["Altro, non salvato", "Tetto, non salvato"])


if __name__ == "__main__":
    unittest.main()
