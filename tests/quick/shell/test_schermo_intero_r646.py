"""R646 (approved by Daniel 15/11/2026): F11 puts the window over the whole screen and takes it back as it was; the
command is in the View menu and in the shortcuts' list, its key changeable as the others'; nothing of it goes into the
profile. On the real window off screen: Windows and Niri on a real screen are not tried here."""
import os
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QKeyEvent, QWindow
from PySide6.QtCore import QEvent

import _setup
from _fixtures import capannone
from meridiana.app.interface import shortcuts
from meridiana.gui.application import QuickWindow, create_app
from quick.gestures import pump, wait_for

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')


class FullScreen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        create_app()
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(capannone(), Path(cls.folder.name), theme={'theme': 'light'})
        cls.win = cls.host.window
        cls.win.show()
        pump(80)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def setUp(self):
        # whatever a test leaves, the next one starts from a window not full screen
        self.addCleanup(lambda: self.host.shell.trigger('fullscreen')
                        if self.win.visibility() == QWindow.Visibility.FullScreen else None)

    def key(self, key):
        for kind in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            self.app.sendEvent(self.win, QKeyEvent(kind, key, Qt.KeyboardModifier.NoModifier))
        pump(120)

    def test_the_command_is_in_the_view_menu_with_f11(self):
        command = next(c for c in shortcuts.commands() if c.id == 'fullscreen')
        self.assertEqual((command.group, command.keys), ('view', ('F11',)))
        view = next(m for m in self.host.shell.menus if m['id'] == 'view')
        entry = next(c for c in view['commands'] if c['id'] == 'fullscreen')
        self.assertEqual(entry['keys'], ['F11'])
        self.assertTrue(entry['enabled'], 'the window answers it')

    def test_f11_goes_full_screen_and_back_to_the_same_place(self):
        self.win.showNormal()
        pump(60)
        self.win.setGeometry(QRect(120, 90, 1180, 760))
        pump(120)
        before = self.win.geometry()
        self.key(Qt.Key.Key_F11)
        wait_for(lambda: self.win.visibility() == QWindow.Visibility.FullScreen, 5)
        self.key(Qt.Key.Key_Escape)                 # Esc is the tools': it does not leave full screen
        self.assertEqual(self.win.visibility(), QWindow.Visibility.FullScreen)
        self.assertEqual([i.property('checked') for i in self.entries()], [True], 'the View menu says it is on')
        self.key(Qt.Key.Key_F11)
        wait_for(lambda: self.win.visibility() == QWindow.Visibility.Windowed, 5)
        pump(120)
        self.assertEqual(self.win.geometry(), before, 'the window comes back where it was, as large')
        self.assertEqual([i.property('checked') for i in self.entries()], [False])

    def entries(self):
        """The View menu's entry «Full screen» in the window's menus."""
        from PySide6.QtCore import QObject
        view = next(m for m in self.host.shell.menus if m['id'] == 'view')
        text = next(c['text'] for c in view['commands'] if c['id'] == 'fullscreen')
        found, pending = [], [self.win.contentItem()]
        while pending:
            node = pending.pop()
            try:
                pending.extend(node.childItems())
                name = node.objectName()
            except RuntimeError:            # an item of a page made or let go meanwhile
                continue
            if name.startswith('mainMenu_'):         # the menu bar's titles hold their menus, the menus their list
                for menu in node.findChildren(QObject):
                    if not menu.objectName().startswith('mainMenuPopup_'):
                        continue
                    listed = menu.property('contentItem').property('contentItem').childItems()
                    found += [o for o in listed if o.property('text') == text]
        return found

    def test_a_maximized_window_comes_back_maximized(self):
        self.win.showMaximized()
        wait_for(lambda: self.win.visibility() == QWindow.Visibility.Maximized, 5)
        self.host.shell.trigger('fullscreen')
        wait_for(lambda: self.win.visibility() == QWindow.Visibility.FullScreen, 5)
        self.host.shell.trigger('fullscreen')
        wait_for(lambda: self.win.visibility() == QWindow.Visibility.Maximized, 5)
        self.win.showNormal()
        pump(60)

    def test_nothing_of_it_goes_into_the_profile(self):
        import dataclasses

        from meridiana.app.platform import config
        self.assertFalse([f.name for f in dataclasses.fields(config.Config)
                          if 'full' in f.name or 'visibility' in f.name or 'maximi' in f.name])
        cfg = getattr(self.host, 'cfg', None)
        kept = dataclasses.asdict(cfg) if cfg is not None else None
        self.host.shell.trigger('fullscreen')
        wait_for(lambda: self.win.visibility() == QWindow.Visibility.FullScreen, 5)
        self.assertEqual(dataclasses.asdict(cfg) if cfg is not None else None, kept, 'the settings are as they were')
        self.host.shell.trigger('fullscreen')
        pump(100)


if __name__ == '__main__':
    unittest.main()
