"""R537 (Daniel 07/11/2026: «da rendere più chiara l'esecuzione del salvataggio quando premo Ctrl+S»), study 38.

Ctrl+S writes on a thread of its own and says it in the status bar as Office and Blender do: «Saving…» only past
300 ms (a quick save does not flash), «Saved at 02:41: name.mer» with the tick for a few seconds, then it fades; the
dot on File is lit by a change and off once saved; an error stays, in red, with «Save as…» and its cross, until
closed. The same for opening a project («Opened: name»).

    python -m unittest quick.shell.test_salvataggio_r537
"""
import os
import stat
import tempfile
import time
import unittest
from pathlib import Path

from PySide6.QtCore import QObject, Qt

from _fixtures import capannone
from meridiana import model
from meridiana.quick.app import QuickWindow, create_app
from quick.gestures import key, pump


class SaveSignal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.folder = Path(self.temp.name)
        self.file = self.folder/'prova.mer'
        capannone().save(self.file)
        project, _notice = model.Project.load(self.file)
        self.host = QuickWindow(project, self.folder/'cache', real_views=True, path=self.file)
        self.win = self.host.window
        self.win.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.win.show()
        pump(200)
        self.shell = self.host.shell
        self.files = self.host.engine.rootContext().contextProperty('filesBackend')
        self.session = self.host.bridge.session
        self.kinds = []
        self.shell.changed.connect(lambda: self.kinds.append(self.shell.property('noticeKind')))

    def tearDown(self):
        os.chmod(self.file, stat.S_IWRITE | stat.S_IREAD)
        self.host.close()
        pump(50)
        self.temp.cleanup()

    def item(self, name):
        return self.win.findChild(QObject, name)

    def wait_saved(self, seconds=10):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            pump(20)
            if not self.files.property('busy'):
                break
        pump(50)

    def rename(self, name):
        self.session.edit('Rename', lambda p: setattr(p, 'name', name))
        pump(30)

    def test_the_dot_of_modified_lights_and_goes_out(self):
        dot = self.item('fileDirtyDot')
        self.assertFalse(dot.property('visible'))
        self.rename('Con una modifica')
        self.assertTrue(dot.property('visible'))
        self.assertEqual(self.win.title(), 'prova.mer * - Meridiana')
        key(self.app, self.win, Qt.Key.Key_S, modifiers=Qt.KeyboardModifier.ControlModifier)
        self.wait_saved()
        self.assertFalse(dot.property('visible'))
        self.assertEqual(self.win.title(), 'prova.mer - Meridiana')
        self.assertEqual(model.Project.load(self.file)[0].name, 'Con una modifica')

    def test_ctrl_s_says_saved_with_the_time_then_fades(self):
        self.rename('Salvato')
        key(self.app, self.win, Qt.Key.Key_S, modifiers=Qt.KeyboardModifier.ControlModifier)
        self.wait_saved()
        self.assertEqual(self.shell.property('noticeKind'), 'done')
        hint = self.item('statusHint')
        self.assertIn('prova.mer', hint.property('text'))
        self.assertRegex(hint.property('text'), r'\d\d:\d\d')
        self.assertTrue(self.item('statusNoticeIcon').property('visible'))
        self.assertFalse(self.win.property('fileOpen'), 'Ctrl+S opens no page')
        pump(4300)
        self.assertEqual(self.shell.property('noticeKind'), '', 'the confirmation goes by itself')
        self.assertTrue(any(k == 'done' for k in self.kinds))

    def test_a_quick_save_does_not_flash(self):
        self.rename('Veloce')
        key(self.app, self.win, Qt.Key.Key_S, modifiers=Qt.KeyboardModifier.ControlModifier)
        self.wait_saved()
        self.assertNotIn('busy', self.kinds, 'a save under 300 ms shows no «Saving…»')

    def test_a_slow_save_says_saving_past_300_ms(self):
        files = self.files
        job = files._begin

        def slow(kind, path, work, finish):
            def late():
                time.sleep(0.6)
                return work()
            job(kind, path, late, finish)
        files._begin = slow
        self.rename('Lento')
        key(self.app, self.win, Qt.Key.Key_S, modifiers=Qt.KeyboardModifier.ControlModifier)
        pump(150)
        self.assertNotEqual(self.shell.property('noticeKind'), 'busy', 'not before 300 ms')
        pump(300)
        self.assertEqual(self.shell.property('noticeKind'), 'busy')
        self.assertTrue(self.item('statusSaving').property('visible'))
        self.wait_saved()
        self.assertEqual(self.shell.property('noticeKind'), 'done')

    def test_a_change_while_writing_keeps_the_dot(self):
        self.rename('Scritto')
        self.files.write()
        self.rename('Cambiato mentre scriveva')
        self.wait_saved()
        self.assertTrue(self.session.dirty())
        self.assertTrue(self.item('fileDirtyDot').property('visible'))
        self.assertEqual(model.Project.load(self.file)[0].name, 'Scritto')

    def test_an_error_stays_until_closed(self):
        os.chmod(self.file, stat.S_IREAD)       # Windows: a read-only folder still takes files, a read-only file not
        self.rename('Non si salva')
        key(self.app, self.win, Qt.Key.Key_S, modifiers=Qt.KeyboardModifier.ControlModifier)
        self.wait_saved()
        self.assertEqual(self.shell.property('noticeKind'), 'error')
        self.assertIn('prova.mer', self.item('statusHint').property('text'))
        self.assertTrue(self.item('statusSaveAs').property('visible'))
        self.assertTrue(self.item('statusNoticeClose').property('visible'))
        self.assertTrue(self.session.dirty())
        pump(5000)
        self.shell.show_notice('a sentence of another part')
        self.shell.trigger('fit')
        pump(50)
        self.assertEqual(self.shell.property('noticeKind'), 'error', 'it stays until its cross')
        self.shell.dismissNotice()
        pump(20)
        self.assertEqual(self.shell.property('noticeKind'), '')
        self.assertFalse(self.item('statusSaveAs').property('visible'))

    def test_opening_says_the_project(self):
        other = self.folder/'altro.mer'
        project = capannone()
        project.name = 'Progetto aperto'
        project.save(other)
        self.files._continue('open', str(other))
        self.wait_saved()
        self.assertEqual(self.session.path, other)
        self.assertEqual(self.shell.property('noticeKind'), 'done')
        self.assertIn('Progetto aperto', self.item('statusHint').property('text'))


if __name__ == '__main__':
    unittest.main()
