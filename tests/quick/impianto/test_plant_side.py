"""R407, R406: the right panel of the Plant says, shows and does what ui/plant_page does, inside its card.

Words against the functions of the Widgets; the shape on the real workbench, walked by quick/confini.py."""
import os
import tempfile
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QPointF, Qt
from meridiana import i18n, jobs
from meridiana.energy import plant as core
from meridiana.quick.app import QuickWindow, create_app
from meridiana.quick.backend import plant_presenter as presenter
from meridiana.ui import plant_page as widgets
from quick import confini
from quick.gestures import click, item, key, point, pump, wait_for
from quick.parity.differential import connected_fixture

setUpModule = _setup.keep_global_state

# Offscreen, Qt Quick's threaded render loop dies with an access violation while a job imports pvlib or fits a module
# (8 runs out of 8; 0 out of 8 with the basic loop; real windows not seen to: docs/quick/r14-impianto-esito.md).
if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')


def built(project):
    results, _keys, _laid = jobs.layout_of(project)
    return core.build(project, results)


class Words(unittest.TestCase):
    """Copied from ui/plant_page: these stay equal, or the two programs say different things."""

    @classmethod
    def setUpClass(cls):
        i18n.setup('it')
        cls.addClassCleanup(i18n.setup, i18n.language())
        cls.project = connected_fixture()
        cls.state = built(cls.project)

    def test_the_lines_of_the_panel(self):
        self.assertEqual(presenter.summary(self.state), widgets.summary(self.state))
        self.assertEqual(presenter.totals(self.state), widgets.plant_totals(self.state))
        for unit in self.state.units:
            self.assertEqual(presenter.unit_lines(self.state, unit), list(widgets.unit_lines(self.state, unit)))

    def test_a_string_says_its_rows_as_the_group_of_the_string_chosen(self):
        for s in self.state.strings:
            rows = [(r['level'], r['text']) for r in presenter.rows_of(s)]
            self.assertEqual(rows, widgets.string_figures(s)[1] or [('', i18n._('No check yet: the strings are being laid.'))])

    def test_an_input_says_its_state_and_what_it_takes(self):
        words = {'ok': i18n._('correct'), 'warn': i18n._('to be checked'), 'fail': i18n._('out of limit')}
        for unit in self.state.units:
            for k in range(1, unit.inputs + 1):
                slot = self.state.inputs.get((unit.number, k))
                said = presenter.input_words(self.state, unit, k, slot)
                strings = list(slot.strings) if slot is not None else []
                self.assertEqual(said['level'], slot.level if strings else 'info')
                self.assertEqual(said['room'], slot is None or not slot.allowed or len(strings) < slot.allowed)
                self.assertTrue(said['tip'].startswith(words.get(said['level'], i18n._('empty'))), said['tip'])
                self.assertIn(str(unit.number), said['addTip'])


class Panel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(i18n.setup, i18n.language())      # the next module's language is its own
        cls.app = _setup.qt_or_skip()
        create_app()
        i18n.setup('it')
        project = connected_fixture()
        results, keys, _laid = jobs.layout_of(project)
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(project, Path(cls.folder.name), real_views=True,
                               theme={'theme': 'light', 'accent': 'indigo', 'backgrounds': 'grey'})
        cls.host.bridge.accept_layout(cls.host.bridge.session.generation, results, keys)
        cls.win = cls.host.window
        cls.win.resize(1600, 960)
        cls.win.show()
        cls.plant = cls.host.parts.controllers['plant']
        cls.actions = cls.host.parts.controllers['plantActions']
        cls.host.shell.trigger('phase_plant')
        wait_for(lambda: not cls.plant.busy and cls.plant.units, 60)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def setUp(self):
        self.win.resize(1600, 960)
        self.actions.openSection('inverter')
        self.plant.selectString(-1)
        pump(350)

    def assertInBounds(self):
        found = confini.audit(self.win)
        self.assertEqual([str(f) for f in found if 'plant' in f.where], [])

    def test_r343_the_groups_inside_a_section_have_no_frame(self):
        strings = item(self.win, 'plant-strings')
        self.assertTrue(strings.property('nested'))
        panel = item(self.win, 'plant-inverters')
        group = item(self.win, 'plant-inverters-group')
        scene = group.mapToScene(QPointF(0, 0))
        self.assertEqual(scene.x() - panel.mapToScene(QPointF(0, 0)).x(), 8)     # SECTION_MARGINS
        self.assertEqual(strings.mapToScene(QPointF(0, 0)).x(), scene.x())       # nothing round them
        self.assertEqual(strings.width(), group.width())
        self.assertEqual(panel.width() - group.width() - 8, 10)                  # the bar's room, kept (R100)

    def test_r406_the_panels_sentences_go_to_the_status_bar_and_never_under_the_sections(self):
        long = ' '.join(['Impianto > Stringhe: 57 stringhe assegnate; 76 moduli restano senza collegamento.'] * 8)
        self.plant.tell(long + '\nsecond line')
        pump(350)
        self.assertInBounds()
        self.assertIn('second line', item(self.win, 'statusHint').property('text'))
        self.assertNotIn('\n', item(self.win, 'statusHint').property('text'))
        side = item(self.win, 'plant-inspector')
        self.assertFalse(any(long in str(c.property('text') or '') for c in side.childItems()))
        self.plant.tell('')

    def test_r337_one_section_as_tall_as_what_it_holds_and_it_scrolls_only_past_the_room(self):
        side = item(self.win, 'plant-inspector')
        self.actions.openSection('storage')
        pump(350)
        self.assertLess(item(self.win, 'plant-section-storage').height(), side.height())
        self.actions.openSection('inverter')
        pump(350)
        panel = item(self.win, 'plant-inverters')
        self.assertLessEqual(panel.mapToScene(QPointF(0, panel.height())).y(), side.mapToScene(QPointF(0, side.height())).y())
        self.assertInBounds()

    def test_r341_narrow_the_rows_go_under_their_labels_and_nothing_is_cut(self):
        space = item(self.win, 'workspace')
        before = space.property('rightExtent')
        self.addCleanup(space.setProperty, 'rightExtent', before)
        wide = item(self.win, 'plant-ratio-row')
        self.assertFalse(wide.property('stacked'))
        space.setProperty('rightExtent', 213)
        pump(350)
        self.assertInBounds()
        self.assertTrue(wide.property('stacked'))

    def test_r298_a_string_chosen_opens_its_group_with_its_commands_and_menu(self):
        strings = self.plant.strings
        self.assertGreater(len(strings), 0)
        self.actions.openSection('panels')
        pump(300)
        self.plant.selectString(0)
        pump(350)
        self.assertEqual(self.actions.section, 'inverter')
        group = item(self.win, 'plant-string-chosen')
        self.assertTrue(group.isVisible())
        panel = item(self.win, 'plant-inverters')
        panel.setProperty('contentY', 0)
        pump(150)
        self.assertInBounds()
        for name in ('plant-string-redraw', 'plant-string-move', 'plant-string-delete'):
            self.assertTrue(item(self.win, name).isVisible(), name)
        click(self.app, self.win, point(item(self.win, 'plant-string-move')))
        pump(250)
        shown = [t for p in _popups(self.win) for t in _texts(p)]
        name = strings[0]['label']
        for word in (f'Inverti la stringa {name}', f'Sposta la stringa {name} su', f'Elimina la stringa {name} (Canc)'):
            self.assertTrue(any(word in t for t in shown), (word, shown))
        key(self.app, self.win, Qt.Key.Key_Escape)
        pump(150)

    def test_r507_a_click_on_the_open_section_closes_it_and_another_opens(self):
        side = item(self.win, 'plant-inspector')
        self.assertEqual(self.actions.section, 'inverter')
        editor = self.actions._plan.editor
        self.assertTrue(editor.strings_mode)
        strings_mode = False        # R529: with no section open a click on a module selects it, as with Panels
        click(self.app, self.win, point(item(self.win, 'plant-section-inverter')))
        pump(350)
        self.assertEqual(self.actions.section, '')
        heads = [item(self.win, f'plant-section-{k}') for k in ('panels', 'inverter', 'storage')]
        for head in heads:            # all three closed: each section is its head and its line
            self.assertLess(head.parentItem().height(), head.height() + 4, head.objectName())
        self.assertEqual(editor.strings_mode, strings_mode)      # closing gives the modules' clicks back
        click(self.app, self.win, point(item(self.win, 'plant-section-storage')))
        pump(350)
        self.assertEqual(self.actions.section, 'storage')
        click(self.app, self.win, point(item(self.win, 'plant-section-storage')))
        pump(350)
        self.assertEqual(self.actions.section, '')
        click(self.app, self.win, point(item(self.win, 'plant-section-inverter')))
        pump(350)
        self.assertEqual(self.actions.section, 'inverter')
        self.assertGreater(item(self.win, 'plant-section-inverter').parentItem().height(), side.height() / 3)

    def test_r297_the_cards_only_of_the_inverters_chosen_and_the_working_one_filled(self):
        cards = [u for u in self.plant.units if u['card']]
        for unit in cards:
            self.assertIsNotNone(item(self.win, f"inverter-card-{unit['number']}"))
        self.plant.selectUnit(cards[0]['number'])
        pump(100)
        card = item(self.win, f"inverter-card-{cards[0]['number']}")
        self.assertEqual(card.property('current'), True)
        self.assertEqual(item(self.win, 'plant-working-summary').property('text'), cards[0]['summary'])

    def test_r517_the_datasheet_of_an_inverter_opens_from_its_menu(self):
        # Daniel 07/11/2026: «non si riesce ad aprire la scheda inverter»: «Scheda tecnica…» of the card's menu closed
        # the menu and opened nothing (seen with the native mouse too, tools/quick_native_input.py).
        number = next(u for u in self.plant.units if u['card'])['number']
        panel = item(self.win, 'plant-inverters')
        panel.setProperty('contentY', 0)
        pump(150)
        card = item(self.win, f'inverter-card-{number}')
        more = next(c for c in _all(card) if c.property('iconName') == 'ellipsis')
        click(self.app, self.win, point(more))
        pump(300)
        entry = next(i for p in _popups(self.win) for i in _all(p) if i.property('text') == 'Scheda tecnica…')
        click(self.app, self.win, point(entry))
        pump(400)
        sheets = [p for p in _popups(self.win) if 'Scheda tecnica' in _texts(p)]
        self.assertEqual(len(sheets), 1, [_texts(p)[:4] for p in _popups(self.win)])
        self.assertGreater(len([t for t in _texts(sheets[0]) if ': ' in t]), 5, _texts(sheets[0])[:8])
        key(self.app, self.win, Qt.Key.Key_Escape)
        pump(300)
        self.assertEqual(_popups(self.win), [])


def _all(root):
    pending, found = [root], []
    while pending:
        current = pending.pop()
        pending.extend(current.childItems())
        found.append(current)
    return found


def _popups(window):
    pending, found = [window.contentItem()], []
    while pending:
        current = pending.pop()
        pending.extend(current.childItems())
        if current.metaObject().className().startswith('QQuickPopupItem') and current.isVisible():
            found.append(current)
    return found


def _texts(root):
    pending, found = [root], []
    while pending:
        current = pending.pop()
        pending.extend(current.childItems())
        text = current.property('text')
        if isinstance(text, str) and text:
            found.append(text)
    return found


if __name__ == '__main__':
    unittest.main()
