"""R549: the side panels at the start and their buttons (Daniel, 08/11/2026, Flatpak r24 on lucciola under Niri).

«su linux appena aperto non ci sono barre laterali sinistra e barra verifiche in basso e i pulsanti in basso a destra e
scorciatoia ctrl + b non funzionano come dovrebbero»; «se premo sul pulsante per aprire il pannello di sinistra, mi apre
il pannello Progetto ma a destra».

The cause, reproduced here: Niri opens a new window at half the laptop's screen, held at the window's least width (800
x 828 logical, the title bar Qt draws taken off 854). That is the «medium» shape and too narrow for two columns, so the
arrangement put Project as a tab behind Properties on the right. Widened to 1422 x 828 the shape stays «medium», and
the side of Project was set only when the shape changed: it stayed on the right, behind Properties, with no card on
the left. The right button, which took every card of the right side, then hid both; the state saved at the close had
them hidden, and the next start opened without panels."""
import json
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import Q_ARG, QMetaObject, Qt

from _fixtures import capannone
from meridiana.i18n import _
from meridiana.quick.app import QuickWindow, create_app
from quick.gestures import click, item, key, point, pump, wait_for

# Daniel's quick-shell.json at 17:25 of 08/11/2026 (the close after the start without panels), the floating sizes cut
CLOSED = {'version': 1, 'layout': {
    'bottom': 230.0, 'left': 310.0, 'right': 370.0, 'view': 'plan', 'weights': {},
    'selected': {'bottom': 'checks', 'left': 'project', 'right': 'properties'},
    'stacks': {'bottom': [], 'left': [], 'right': []},
    'panels': [dict(id=i, zone=z, opened=False, x=32.0, y=32.0, width=440.0, height=440.0)
               for i, z in (('project', 'right'), ('properties', 'right'), ('checks', 'bottom'), ('assistant', 'right'))]}}
CLOSED['shapes'] = {'vertical': json.loads(json.dumps(CLOSED['layout'])), 'wide': json.loads(json.dumps(CLOSED['layout']))}
for shape_panel in CLOSED['shapes']['vertical']['panels'][:2]:
    shape_panel['opened'] = True
for shape_panel in CLOSED['shapes']['wide']['panels'][:2]:
    shape_panel['opened'] = True
CLOSED['shapes']['wide']['panels'][0]['zone'] = 'left'


class PanelsAtStart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.host = None

    def tearDown(self):
        warnings = self.host.warnings[:] if self.host else []
        if self.host:
            self.host.close()
        self.app.processEvents()
        self.temp.cleanup()
        self.assertEqual(warnings, [])

    def start(self, state=None):
        if state is not None:
            folder = Path(self.temp.name) / 'quick-profile/state'
            folder.mkdir(parents=True, exist_ok=True)
            (folder / 'quick-shell.json').write_text(json.dumps(state), encoding='utf-8')
        self.host = QuickWindow(capannone(), Path(self.temp.name))
        self.win = self.host.window
        self.win.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.win.show()
        pump(60)

    def settle(self, width, height):
        """The compositor's size, kept long enough for the arrangement (its timer) to answer."""
        self.win.resize(width, height)
        wait_for(lambda: self.arrangement().get('shape') and self.win.width() == width)
        pump(400)

    def arrangement(self):
        value = self.win.property('arrangementInfo')
        return value.toVariant() if hasattr(value, 'toVariant') else value

    def card(self, name):
        return item(self.win, name)

    def shown_on(self, name, side):
        card, workspace = self.card(name), self.card('workspace')
        if not card.isVisible() or card.width() < 50:
            return False
        middle = card.x() + card.width() / 2
        return middle < workspace.width() / 2 if side == 'left' else middle > workspace.width() / 2

    def press(self, name):
        button = self.card(name)
        click(self.app, self.win, point(button, button.width() / 2, button.height() / 2))
        pump(400)

    def test_a_narrow_start_widened_brings_project_back_to_the_left(self):
        self.start()
        self.settle(1600, 960)          # the QML's own size, where the saved state is put back
        self.settle(800, 828)
        self.assertEqual((self.arrangement()['shape'], self.arrangement()['panels']), ('medium', 'together'))
        self.assertEqual(self.card('leftPanel').property('zone'), 'right')
        self.settle(1422, 828)
        self.assertEqual((self.arrangement()['shape'], self.arrangement()['panels']), ('medium', 'apart'))
        self.assertTrue(self.shown_on('leftPanel', 'left'))
        self.assertTrue(self.shown_on('rightPanel', 'right'))
        self.assertFalse(self.card('checksPanel').isVisible())          # 828 px: below LOW_WINDOW, Checks closed

    def test_the_start_shows_project_left_and_properties_right_whatever_was_saved(self):
        self.start(CLOSED)
        self.settle(1422, 828)
        self.assertTrue(self.shown_on('leftPanel', 'left'))
        self.assertTrue(self.shown_on('rightPanel', 'right'))
        self.assertFalse(self.card('checksPanel').isVisible())
        self.settle(800, 828)          # a narrow window: Project shares the right side, as a tab
        self.assertEqual(self.card('leftPanel').property('zone'), 'right')
        self.assertTrue(self.card('rightPanel').property('opened'))
        self.settle(1422, 828)
        self.assertTrue(self.shown_on('leftPanel', 'left'))

    def test_a_tall_start_opens_checks_and_the_saved_closed_cards_come_back(self):
        self.start(CLOSED)
        self.settle(1600, 960)
        self.assertTrue(self.shown_on('leftPanel', 'left'))
        self.assertTrue(self.shown_on('rightPanel', 'right'))
        self.assertTrue(self.card('checksPanel').isVisible())

    def test_the_start_from_the_launcher_resized_at_once_with_the_saved_state_left_dirty(self):
        # as the launcher starts it: no project on the command line (path None), the sample project, Daniel's state
        # with Project on the right in «vertical»; Niri's sizes come before the arrangement's timer has answered
        self.start(CLOSED)
        self.win.resize(800, 828)
        pump(30)
        self.win.resize(1422, 828)
        wait_for(lambda: self.arrangement().get('shape') == 'medium', seconds=5)
        pump(400)
        self.assertTrue(self.shown_on('leftPanel', 'left'))
        self.assertTrue(self.shown_on('rightPanel', 'right'))
        self.assertFalse(self.card('checksPanel').isVisible())

    def test_each_button_is_its_side_whatever_cards_stand_there(self):
        self.start()
        self.settle(1600, 960)
        project, properties, checks = self.card('leftPanel'), self.card('rightPanel'), self.card('checksPanel')
        workspace = self.card('workspace')
        said = lambda side, cards, shown=True: (_('{side}: {cards}') if shown else _('{side}, hidden: {cards}')).format(
            side=_(side), cards=cards)
        self.assertEqual(self.card('statusPanelLeft').property('tip'), said('Left side', project.property('title')) + ' (Ctrl+B)')
        self.assertEqual(self.card('statusPanelRight').property('tip'), said('Right side', properties.property('title')))
        # Project moved to the right by hand: it answers to the right button, and the left side is empty
        project.setProperty('zone', 'right')
        workspace.arrangementChanged.emit()
        pump(300)
        self.assertEqual(self.card('statusPanelLeft').property('tip'),
                         said('Left side', project.property('title'), False) + ' (Ctrl+B)')
        self.press('statusPanelRight')
        self.assertFalse(project.property('opened') or properties.property('opened'))
        self.assertTrue(checks.isVisible())                                 # the bottom is another side
        self.press('statusPanelRight')                                      # the group back, Properties in front
        self.assertTrue(properties.isVisible() and project.property('opened') and not project.isVisible())
        # the bottom button: the bottom only, never the cards of the right side
        self.press('statusPanelBottom')
        self.assertFalse(checks.isVisible())
        self.assertTrue(properties.isVisible() and project.property('opened'))
        self.press('statusPanelBottom')
        self.assertTrue(checks.isVisible())
        # the left side empty since the start: its button brings its own card, Project, there
        self.press('statusPanelLeft')
        self.assertTrue(self.shown_on('leftPanel', 'left'))
        self.assertTrue(self.shown_on('rightPanel', 'right'))
        # Ctrl+B is the left side
        key(self.app, self.win, Qt.Key.Key_B, modifiers=Qt.KeyboardModifier.ControlModifier)
        pump(400)
        self.assertFalse(project.isVisible())
        self.assertTrue(properties.isVisible() and checks.isVisible())
        key(self.app, self.win, Qt.Key.Key_B, modifiers=Qt.KeyboardModifier.ControlModifier)
        pump(400)
        self.assertTrue(self.shown_on('leftPanel', 'left'))

    def test_a_group_of_tabs_hides_and_comes_back_whole_with_its_tab_in_front(self):
        self.start()
        self.settle(1600, 960)
        project, properties = self.card('leftPanel'), self.card('rightPanel')
        workspace = self.card('workspace')
        project.setProperty('zone', 'right')
        QMetaObject.invokeMethod(workspace, 'selectPanel', Q_ARG('QVariant', 'project'))
        pump(300)
        self.assertTrue(project.isVisible() and not properties.isVisible())
        self.press('statusPanelRight')
        self.assertFalse(project.property('opened') or properties.property('opened'))
        self.press('statusPanelRight')
        self.assertTrue(project.isVisible() and properties.property('opened') and not properties.isVisible())

    def test_a_size_changed_behind_the_file_page_is_arranged_when_it_closes(self):
        self.start()
        self.settle(1600, 960)
        self.win.setProperty('fileOpen', True)
        pump(200)
        self.win.resize(1422, 828)
        pump(600)
        self.assertEqual(self.arrangement()['shape'], 'wide')          # the File page holds the arrangement
        self.win.setProperty('fileOpen', False)
        wait_for(lambda: self.arrangement()['shape'] == 'medium', seconds=5)
        self.assertEqual(self.arrangement()['bar'] in ('beside', 'icons'), True)
        self.assertTrue(self.shown_on('leftPanel', 'left'))


if __name__ == '__main__':
    unittest.main()
