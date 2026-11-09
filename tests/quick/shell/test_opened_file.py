"""A project opened from the launcher, with its file (06/11/2026, «scelte sì/no», defects 1-3).

The launcher reads the project before the window is made: the window did not know the file. The title said «Meridiana»
instead of «prova.mer - Meridiana», Ctrl+S opened the File page to ask where, and the project did not enter the recent
ones. Now the window takes the file: the title says it (with « *» while there is something to save), Ctrl+S writes it
where it is, without a page, and the recent projects begin with it.

    python -m unittest quick.shell.test_opened_file
"""
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import Qt

from _fixtures import capannone
from meridiana import model
from meridiana.quick.app import QuickWindow, create_app
from quick.gestures import key, pump


class OpenedFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        folder = Path(self.temp.name)
        self.file = folder/'prova.mer'
        capannone().save(self.file)
        project, _notice = model.Project.load(self.file)
        self.host = QuickWindow(project, folder/'cache', real_views=True, path=self.file)
        self.win = self.host.window
        self.win.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.win.show()
        pump(200)

    def tearDown(self):
        self.host.close()
        pump(50)
        self.temp.cleanup()

    def test_the_title_says_the_file(self):
        self.assertEqual(self.win.title(), 'prova.mer - Meridiana')
        session = self.host.bridge.session
        session.edit('Rename', lambda p: setattr(p, 'name', 'Altro nome'))
        pump(20)
        self.assertEqual(self.win.title(), 'prova.mer * - Meridiana')

    def test_ctrl_s_writes_the_file_where_it_is(self):
        session = self.host.bridge.session
        self.assertEqual(session.path, self.file)
        session.edit('Rename', lambda p: setattr(p, 'name', 'Scritto con Ctrl+S'))
        files = self.host.engine.rootContext().contextProperty('filesBackend')
        asked = []
        files.fileDialogRequested.connect(lambda *a: asked.append(a))
        key(self.app, self.win, Qt.Key.Key_S, modifiers=Qt.KeyboardModifier.ControlModifier)
        pump(200)
        self.assertEqual(asked, [])
        self.assertEqual(model.Project.load(self.file)[0].name, 'Scritto con Ctrl+S')
        self.assertFalse(session.dirty())
        self.assertFalse(self.win.property('fileOpen'), 'Ctrl+S with a file opens no page')
        self.assertEqual(self.win.title(), 'prova.mer - Meridiana')

    def test_the_file_enters_the_recent_projects(self):
        files = self.host.engine.rootContext().contextProperty('filesBackend')
        self.assertEqual(files.property('recent')[0]['path'], str(self.file))
        self.assertEqual(files.property('projectPath'), str(self.file))


class NoFile(unittest.TestCase):
    def test_a_project_without_a_file_keeps_the_plain_title(self):
        app = create_app()
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
            host = QuickWindow(capannone(), Path(temporary), real_views=True)
            try:
                self.assertIsNone(host.bridge.session.path)
                self.assertEqual(host.window.title(), 'Meridiana')
            finally:
                host.close()
                pump(50)
        del app


if __name__ == '__main__':
    unittest.main()
