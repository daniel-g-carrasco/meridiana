"""R632 (2): Meridio docked as a tab and sent «back to the character» (Daniel 15/11/2026, on the Linux laptop: the tabs
«Plant | Meridio», the «–» of his head pressed, «la sua scheda rimane, anche se vuota»).

The «–» (and Esc, the same command) closed his conversation and left his tab among the panels' tabs, empty. Now the
tab goes, the panel shows the card that was there (or closes when it was the only one), and Meridio stands as the
floating character where he was. Asked again (the status bar's Meridio, Ctrl+L, a click on him) he comes back as the
tab, since he is still docked; and a window started again from what this one saved shows no empty tab.
"""
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, Qt

from _fixtures import capannone
from meridiana.app import jobs
from meridiana.gui.application import QuickWindow, create_app
from quick.gestures import click, key, point, pump, wait_for


def item(window, name):
    """An item of the window by name, from its own root item: Meridio's layer is over the header, beside the middle."""
    found = window.findChild(QObject, name)
    if found is not None:
        return found
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


class MeridioTabTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.host = self.start()

    def start(self):
        host = QuickWindow(capannone(), Path(self.temp.name), theme={'theme': 'light', 'reducedMotion': True},
                           real_views=True)
        win = host.window
        win.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        win.show()
        win.resize(1600, 960)
        results, keys, _ = jobs.layout_of(host.bridge.session.project)
        host.bridge.accept_layout(host.bridge.session.generation, results, keys)
        pump(300)
        wait_for(lambda: self.findable(host.window, 'assistantLayer'), 10)
        return host

    @staticmethod
    def findable(window, name):
        try:
            return item(window, name) is not None
        except AssertionError:
            return False

    def tearDown(self):
        if self.host is not None:
            self.stop()
        self.temp.cleanup()

    def stop(self):
        warnings = self.host.warnings[:]
        self.host.close()
        self.app.processEvents()
        self.host = None
        self.assertEqual(warnings, [])

    def parts(self):
        win = self.host.window
        return (item(win, 'assistantLayer'), item(win, 'assistantDockPanel'), item(win, 'assistantCharacter'),
                item(win, 'rightPanel'), item(win, 'propertiesGroupTabs'))

    def tab_shown(self):
        """Meridio's tab among the right side's tabs, or his card on screen."""
        layer, dock, _, _, tabs = self.parts()
        members = item(self.host.window, 'rightPanel').property('members')
        members = members.toVariant() if hasattr(members, 'toVariant') else members
        titles = [p.property('title') for p in members or []]
        return dock.isVisible() or (tabs.isVisible() and dock.property('title') in titles)

    def dock_him(self):
        layer, dock, character, properties, tabs = self.parts()
        self.host.shell.trigger('assistant')                     # his conversation, floating
        wait_for(lambda: layer.property('opened'), 5)
        self.where = (layer.property('avatarX'), layer.property('avatarY'))
        click(self.app, self.host.window, point(item(self.host.window, 'assistantDock')))     # «Dock to the panels»
        wait_for(lambda: dock.isVisible(), 5)
        self.assertTrue(item(self.host.window, 'assistantGroupTabs').isVisible(), 'docked beside Properties: two tabs')
        self.assertTrue(self.host.cfg.assistant_docked)

    def assert_back_to_the_character(self, what):
        layer, dock, character, properties, tabs = self.parts()
        wait_for(lambda: not layer.property('opened'), 5)
        pump(200)
        self.assertFalse(self.tab_shown(), f'{what}: his tab is left, empty')
        self.assertFalse(tabs.isVisible(), f'{what}: the tabs of one card left')
        self.assertTrue(properties.isVisible(), f'{what}: the card that was there is in front')
        self.assertTrue(character.isVisible(), f'{what}: the floating character')
        self.assertEqual((layer.property('avatarX'), layer.property('avatarY')), self.where, f'{what}: where he was')

    def test_the_dash_takes_his_tab_away_and_asked_again_he_comes_back_as_the_tab(self):
        self.dock_him()
        click(self.app, self.host.window, point(item(self.host.window, 'assistantClose')))       # «–»
        self.assert_back_to_the_character('«–»')
        layer, dock, character, properties, tabs = self.parts()
        self.host.shell.trigger('assistant')                     # asked again: still docked, his tab again
        wait_for(lambda: dock.isVisible(), 5)
        bubble = item(self.host.window, 'assistantBubble')
        wait_for(lambda: bubble.isVisible() and bubble.parentItem() is dock.property('assistantSpace'), 5)
        self.assertTrue(item(self.host.window, 'assistantGroupTabs').isVisible())
        self.assertFalse(character.isVisible())

    def test_esc_is_the_same_command(self):
        self.dock_him()
        key(self.app, self.host.window, Qt.Key.Key_Escape)
        self.assert_back_to_the_character('Esc')

    def test_alone_on_its_side_the_panel_closes(self):
        layer, dock, character, properties, tabs = self.parts()
        properties.setProperty('opened', False)                  # Meridio alone on the right
        self.dock_him_alone()
        click(self.app, self.host.window, point(item(self.host.window, 'assistantClose')))
        wait_for(lambda: not layer.property('opened'), 5)
        pump(200)
        self.assertFalse(self.tab_shown(), 'alone: his panel is left, empty')
        self.assertFalse(properties.isVisible())                 # nothing on the right: the side closes
        self.assertTrue(character.isVisible())

    def dock_him_alone(self):
        layer, dock, *_ = self.parts()
        self.host.shell.trigger('assistant')
        wait_for(lambda: layer.property('opened'), 5)
        click(self.app, self.host.window, point(item(self.host.window, 'assistantDock')))
        wait_for(lambda: dock.isVisible(), 5)

    def not_empty(self, what):
        """His tab, when it is there, holds his conversation."""
        layer, dock, character, properties, tabs = self.parts()
        bubble = item(self.host.window, 'assistantBubble')
        if self.tab_shown():
            self.assertTrue(layer.property('opened'), f'{what}: an empty tab')
            # behind another card (a start brings Properties in front): his tab chosen shows his conversation
            QMetaObject.invokeMethod(item(self.host.window, 'workspace'), 'selectPanel', Q_ARG('QVariant', 'assistant'))
            wait_for(lambda: dock.isVisible(), 5)
            wait_for(lambda: bubble.isVisible() and bubble.parentItem() is dock.property('assistantSpace'), 5)
            self.assertFalse(character.isVisible())
        else:
            self.assertTrue(character.isVisible(), f'{what}: Meridio nowhere')

    def test_the_arrangement_saved_with_him_open_brings_back_no_empty_tab(self):
        # the layout is saved while his tab is open (quick-shell.json holds it opened), then he is sent back to the
        # character, and the saved layout is put back as a start does (Workbench.put sets each card's `opened`)
        self.dock_him()
        self.host.layout_state.save()
        click(self.app, self.host.window, point(item(self.host.window, 'assistantClose')))
        self.assert_back_to_the_character('«–»')
        self.host.layout_state.restore()
        pump(300)
        self.assertFalse(self.tab_shown(), 'the saved layout put back: his empty tab again')
        self.not_empty('saved layout')

    def started_again(self, close):
        self.dock_him()
        if close:
            click(self.app, self.host.window, point(item(self.host.window, 'assistantClose')))
            self.assert_back_to_the_character('«–»')
        self.stop()
        self.host = self.start()
        self.assertTrue(self.parts()[0].property('docked'), 'still docked after the start')
        # docked, a start opens his conversation in his tab, as before R632: never the tab without it
        self.not_empty('started again')

    def test_a_window_started_again_with_him_open_shows_no_empty_tab(self):
        self.started_again(False)

    def test_a_window_started_again_after_the_dash_shows_no_empty_tab(self):
        self.started_again(True)


if __name__ == '__main__':
    unittest.main()
