"""The question when the Quick window is closed with unsaved changes (Daniel, 10/11/2026; gui/backend/closing_part.py):
«Save» writes the project and closes, «Save» on a project without a file asks where and closes only once it is
written, «Don't save» closes, «Cancel» leaves the window and the project as they were; without changes the window
closes at once; when the system ends the session nobody is asked and the recovery copy is kept.

    python -m unittest quick.sistema.test_close_question
"""
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, Qt

from _fixtures import capannone
from meridiana.core.model import model
from meridiana.app.project import recovery
from quick.gestures import pump


class CloseQuestion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from meridiana.gui.application import create_app
        cls.app = create_app()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.folder = Path(self.temp.name)
        self.file = self.folder / "tetto.mer"
        capannone("Tetto").save(self.file)
        self.host = None
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.dispose)

    def open(self, path=None):
        from meridiana.gui.application import QuickWindow
        project = model.Project.load(path)[0] if path else capannone("Senza file")
        self.host = QuickWindow(project, self.folder / "cache", real_views=True, path=path)
        self.win = self.host.window
        self.win.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.win.show()
        pump(200)
        self.session = self.host.bridge.session
        self.files = self.host.parts.controllers["files"]
        self.closing = self.host.parts.controllers["closing"]
        self.recovery = self.host.parts.controllers["recovery"]
        self.asked = []
        self.files.fileDialogRequested.connect(lambda *args: self.asked.append(args))
        return self.host

    def dispose(self):
        if self.host is not None:
            self.host.close()
            self.host = None
            pump(50)

    def change(self, name="Cambiato"):
        self.session.edit("Rename", lambda p: setattr(p, "name", name))
        self.assertTrue(self.session.dirty())

    def dialog(self):
        return self.win.findChild(QObject, "closeDialog")

    def press(self, method, *args):
        """A button of the dialog, as its click calls it: accept (Save), reject (Cancel, also Esc), the action (Don't
        save)."""
        self.assertTrue(QMetaObject.invokeMethod(self.dialog(), method, *args))
        pump(150)

    def close_window(self):
        self.win.close()
        pump(150)

    def test_the_question_and_its_buttons_speak_the_window_language(self):
        from meridiana import i18n
        i18n.setup("it")
        self.addCleanup(i18n.setup, "en")
        self.open(self.file)
        self.change()
        self.assertEqual(self.closing.question, "Salvare le modifiche a tetto.mer?")
        self.assertEqual(self.closing.words, dict(title="Modifiche non salvate", save="Salva", discard="Non salvare",
                                                   cancel="Annulla"))

    def test_without_changes_the_window_closes_at_once(self):
        self.open(self.file)
        self.close_window()
        self.assertFalse(self.closing.asking)
        self.assertTrue(self.host._closed)
        self.assertFalse(self.win.isVisible())

    def test_with_changes_it_asks_and_cancel_leaves_everything_as_it_was(self):
        self.open(self.file)
        self.change()
        before = self.file.read_bytes()
        self.close_window()
        self.assertTrue(self.closing.asking)
        self.assertTrue(self.dialog().property("opened"))
        self.assertIn("tetto.mer", self.closing.question)
        self.assertFalse(self.host._closed)
        self.assertTrue(self.win.isVisible())
        self.press("reject")
        self.assertFalse(self.closing.asking)
        self.assertFalse(self.dialog().property("opened"))
        self.assertFalse(self.host._closed)
        self.assertTrue(self.win.isVisible())
        self.assertTrue(self.session.dirty())
        self.assertEqual(self.file.read_bytes(), before)
        self.assertEqual(self.session.project.name, "Cambiato")
        # asked again the next time
        self.close_window()
        self.assertTrue(self.closing.asking)
        self.assertTrue(self.dialog().property("opened"))
        self.assertEqual(self.host.warnings, [])

    def test_save_writes_the_file_and_closes(self):
        self.open(self.file)
        self.change("Salvato")
        self.close_window()
        self.assertTrue(self.closing.asking)
        self.press("accept")
        pump(300)
        self.assertTrue(self.host._closed)
        self.assertFalse(self.win.isVisible())
        self.assertEqual(model.Project.load(self.file)[0].name, "Salvato")
        self.assertEqual(recovery.pending(self.host.paths.state), [])

    def test_save_without_a_file_asks_where_and_closes_only_once_written(self):
        self.open()
        self.change("Nuovo")
        self.close_window()
        self.closing.answer("save")
        pump(150)
        self.assertEqual([a[0] for a in self.asked], ["save"])          # «Save as»
        self.assertFalse(self.host._closed)
        self.files.cancelFileDialog()                                   # the chooser closed without a name
        pump(150)
        self.assertFalse(self.host._closed)
        self.assertTrue(self.win.isVisible())
        self.close_window()
        self.closing.answer("save")
        pump(150)
        target = self.folder / "nuovo.mer"
        self.files.fileChosen("save", str(target))
        pump(300)
        self.assertTrue(target.exists())
        self.assertEqual(model.Project.load(target)[0].name, "Nuovo")
        self.assertTrue(self.host._closed)

    def test_dont_save_closes_and_leaves_the_file(self):
        self.open(self.file)
        before = self.file.read_bytes()
        self.change()
        self.close_window()
        self.press("actionTriggered", Q_ARG(int, 0))
        pump(300)
        self.assertTrue(self.host._closed)
        self.assertFalse(self.win.isVisible())
        self.assertEqual(self.file.read_bytes(), before)

    def test_the_end_of_the_session_asks_nothing_and_keeps_the_recovery_copy(self):
        self.open(self.file)
        self.recovery.claim()
        self.change("Da recuperare")
        self.closing.session_ends()          # what QGuiApplication.commitDataRequest calls
        self.close_window()
        self.assertFalse(self.closing.asking)
        self.assertTrue(self.host._closed)
        self.recovery.release()              # as main does after the window closed: the copy is anybody's again
        copies = recovery.pending(self.host.paths.state, self.file)
        self.assertEqual(len(copies), 1)
        self.assertEqual(copies[0]["project"]["name"], "Da recuperare")


if __name__ == "__main__":
    unittest.main()
