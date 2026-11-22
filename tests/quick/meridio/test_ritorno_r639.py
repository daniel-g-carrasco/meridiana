"""R639 (Daniel 15/11/2026, on the laptop: «mi è sparito meridio e non so come rifarlo comparire. Tasto in basso a
destra non serve»).

The ways that left him nowhere, each with the status bar's «Meridio» that must always bring him back in view, inside
the window: docked with his conversation open and the right side hidden by its button of the status bar (his tab
closed with the others: the bubble was in a tab not shown, the character hidden because the conversation was open,
and «Meridio» chose a tab that was not there); the same with the clean screen; the assistant turned off in the
Settings; a place left outside the window; a profile with a place outside the window, read at the start.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QObject, QPointF, QRectF, Qt

from _fixtures import capannone
from meridiana.app import jobs
from meridiana.data import atomic
from meridiana.gui.application import QuickWindow, create_app
from quick.gestures import click, point, pump, wait_for
from quick.meridio.support import KeyStore, Voice


def find(window, name):
    """An item by name from the window's own root: Meridio's stage is in Qt's overlay, beside the content."""
    top = window.contentItem()
    while top.parentItem() is not None:
        top = top.parentItem()
    pending = [top]
    while pending:
        node = pending.pop()
        if node.objectName() == name:
            return node
        pending.extend(node.childItems())
    raise AssertionError('Missing Quick item: ' + name)


def shown(item):
    while item is not None:
        if not item.isVisible() or item.opacity() <= 0.01:
            return False
        item = item.parentItem()
    return True


class BackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.temp.cleanup)
        self.hosts = []
        self.start()

    def start(self):
        with patch('meridiana.gui.backend.assistant_chat.keys', KeyStore()), \
                patch('meridiana.gui.backend.voice.Voice', return_value=Voice()):
            self.host = QuickWindow(capannone(), Path(self.temp.name), real_views=True,
                                    theme={'theme': 'light', 'reducedMotion': True})
        self.hosts.append(self.host)
        win = self.window = self.host.window
        win.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        win.show()
        win.resize(1400, 900)
        results, keys, _ = jobs.layout_of(self.host.bridge.session.project)
        self.host.bridge.accept_layout(self.host.bridge.session.generation, results, keys)
        pump(300)
        wait_for(lambda: self.window.findChild(QObject, 'assistantLayer') is not None, 10)
        self.layer = self.window.findChild(QObject, 'assistantLayer')
        self.chat = self.host.parts.controllers['assistant']
        self.chat.cfg.assistant_introduced = True
        wait_for(lambda: self.layer.property('placedOnce'), 5)
        pump(300)

    def tearDown(self):
        for host in self.hosts:
            if host.window is not None:
                warnings = host.warnings[:]
                host.close()
                self.app.processEvents()
                self.assertEqual(warnings, [])

    def inside(self, item):
        p = item.mapToScene(QPointF(0, 0))
        r = QRectF(p.x(), p.y(), item.width(), item.height())
        return QRectF(0, 0, self.window.width(), self.window.height()).contains(r)

    def seen(self):
        """He is on screen: the character, or his conversation where it is drawn, inside the window."""
        character, bubble = find(self.window, 'assistantCharacter'), find(self.window, 'assistantBubble')
        return (shown(character) and self.inside(character)) or (shown(bubble) and self.inside(bubble))

    def status_button(self):
        click(self.app, self.window, point(find(self.window, 'statusMeridio')))
        pump(400)

    def dock_open(self):
        self.host.shell.trigger('assistant')
        wait_for(lambda: self.layer.property('opened'), 5)
        click(self.app, self.window, point(find(self.window, 'assistantDock')))
        dock = find(self.window, 'assistantDockPanel')
        wait_for(lambda: dock.isVisible(), 5)
        pump(300)
        self.assertTrue(self.seen())

    def test_docked_and_the_right_side_hidden_he_stays_in_view(self):
        self.dock_open()
        click(self.app, self.window, point(find(self.window, 'statusPanelRight')))
        pump(400)
        self.assertTrue(self.seen(), 'docked, the right side hidden: Meridio nowhere')
        self.status_button()        # closes him: the character is there
        self.assertTrue(self.seen())
        self.status_button()
        self.assertTrue(self.layer.property('opened'))
        self.assertTrue(self.seen(), 'the status bar\'s «Meridio» did not bring him back')
        # docked, opened again he is his tab (R503), shown
        dock = find(self.window, 'assistantDockPanel')
        self.assertTrue(self.layer.property('dockedNow'))
        self.assertTrue(dock.isVisible())

    def test_docked_and_the_clean_screen_he_stays_in_view(self):
        self.dock_open()
        # what the clean screen does to the cards (Workbench.qml: every panel closed)
        workspace = self.window.property('workspaceItem')
        for panel in workspace.property('panels').toVariant():
            panel.setProperty('opened', False)
        pump(400)
        self.assertTrue(self.seen(), 'docked, every card closed: Meridio nowhere')
        self.status_button()
        self.status_button()
        self.assertTrue(self.layer.property('opened'))
        self.assertTrue(self.seen())

    def test_turned_off_in_the_settings_the_status_button_brings_him_back(self):
        settings = self.host.parts.controllers['settings']
        settings.setValue('assistant', False)
        pump(300)
        self.assertFalse(self.seen())
        self.status_button()
        self.assertTrue(self.seen(), 'turned off: the status bar\'s «Meridio» did nothing')
        self.assertTrue(self.chat.cfg.assistant, 'shown again, the setting says so')

    def test_a_place_outside_the_window_comes_back_inside(self):
        self.layer.setProperty('avatarX', 5000)
        self.layer.setProperty('avatarY', -400)
        pump(100)
        self.status_button()
        self.assertTrue(self.layer.property('opened'))
        self.assertTrue(self.inside(find(self.window, 'assistantCharacter')), 'opened outside the window')
        self.assertTrue(self.inside(find(self.window, 'assistantBubble')))

    def test_a_profile_with_a_place_outside_the_window_starts_inside(self):
        state = self.chat.host.state_file
        self.host.close()
        self.app.processEvents()
        self.hosts.remove(self.host)        # its own closing is not what is tested here
        atomic.write_json(state, {phase: ['left', 'top', 9000, 9000] for phase in ('model', 'plant')})
        self.start()
        self.assertTrue(self.seen(), 'started with a place outside the window: Meridio nowhere')

    def test_escape_then_the_status_button(self):
        self.host.shell.trigger('assistant')
        wait_for(lambda: self.layer.property('opened'), 5)
        self.chat.host.dismissRequested.emit()
        wait_for(lambda: not self.layer.property('opened'), 5)
        self.assertTrue(self.seen())
        self.status_button()
        self.assertTrue(self.layer.property('opened'))
        self.assertTrue(self.seen())


if __name__ == '__main__':
    unittest.main()
