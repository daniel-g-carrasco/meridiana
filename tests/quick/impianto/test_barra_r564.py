"""R564 (Daniel 14/11/2026): the bar of the modules in the Plant, in the real window off screen.

- one button, «Layout» (S), whose menu is the common one: Layout, Row of modules (L), Area with automatic layout,
  Fill, Empty; East-west, «On a canopy», «Fill» and «Empty» are no longer buttons, and the summary of the modules
  laid comes up into the bar;
- «Fill» on a sub-field drawn with «Layout» (by hand and laid, R445) was on and did nothing, saying nothing (the
  defect): now it is off with its reason beside it, and asked anyway it says why;
- «Modules on a canopy…» in the canopy's own menu in the Plant, on the plan and in the 3D view, the window of
  before with that canopy chosen;
- the entries of a sub-field are the same words in the bar, on the plan, in the 3D view and in the tree;
- the «?» of the card at the right end of its head, as a section's (R597)."""
import os
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QObject, QPointF

import _setup
from _fixtures import capannone
from meridiana import i18n
from meridiana.app import jobs
from meridiana.core.layout import manual
from meridiana.core.model import canopies, model
from meridiana.gui.application import QuickWindow, create_app
from quick.gestures import pump, wait_for

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')


def project():
    """The shed with three sub-fields: «Sud» laid automatically, «Disegnato» drawn with Layout (its modules, R445),
    «Area» an empty area of the automatic layout; and two parking canopies east of it."""
    p = capannone()
    b = p.buildings[0]
    p.subfields[0].ring = [[1, 1], [19, 1], [19, 19], [1, 19]]
    drawn = model.SubField(id=p.new_id('s'), name='Disegnato', ring=[[21, 1], [39, 1], [39, 9], [21, 9]],
                           building=b.id, params={'tilt': 15.0})
    p.subfields.append(drawn)
    manual.make_flush(p, drawn)
    p.subfields.append(model.SubField(id=p.new_id('s'), name='Area', ring=[[21, 11], [39, 11], [39, 19], [21, 19]],
                                      building=b.id, params={'tilt': 15.0}))
    canopies.add(p, canopies.Spec(stalls=4, rows=2), (52.0, 4.0))
    canopies.add(p, canopies.Spec(stalls=3, rows=1), (52.0, 30.0))
    return p


def items(root):
    out, pending = [], [root]
    while pending:
        node = pending.pop()
        out.append(node)
        pending.extend(node.childItems())
    return out


class TheBarOfTheModules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(i18n.setup, i18n.language())
        cls.app = _setup.qt_or_skip()
        create_app()
        i18n.setup('en')
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(project(), Path(cls.folder.name), real_views=True, theme={'theme': 'light'})
        cls.session = cls.host.bridge.session
        results, keys, _laid = jobs.layout_of(cls.session.project)
        cls.host.bridge.accept_layout(cls.session.generation, results, keys)
        cls.win = cls.host.window
        cls.win.show()
        pump(80)
        cls.win.resize(1400, 860)               # after show: the window takes its size then
        cls.host.window.showPhase('plant')
        pump(400)
        cls.sub = {sf.name: sf.id for sf in cls.session.project.subfields}
        cls.canopies = [b for b in cls.session.project.buildings if b.canopy is not None]

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def setUp(self):
        self.host.window.showPhase('plant')
        self.session.select('site', '')
        pump(100)

    def find(self, name):
        found = [i for i in items(self.win.contentItem()) if i.objectName() == name]
        return found[0] if found else None

    def visible(self, name):
        return [i for i in items(self.win.contentItem()) if i.objectName() == name and i.isVisible()]

    def menu_of_layout(self):
        button = self.visible('tool_tool_subfield')[0]
        menu = button.findChild(QObject, 'tool_tool_subfieldMenu')
        menu.open()
        self.addCleanup(menu.close)
        pump(300)
        names = ['phaseMenu_' + c for c in ('tool_subfield', 'tool_row', 'fill_area', 'fill', 'empty')]
        found = [i for i in items(self.win.contentItem()) if i.objectName().startswith('phaseMenu_') and i.isVisible()]
        entries = sorted(found, key=lambda e: e.mapToScene(QPointF(0, 0)).y())
        self.assertEqual([e.objectName() for e in entries], names, 'the menu of Layout, in order')
        return button, entries

    # the bar

    def test_one_button_layout_with_its_menu(self):
        button, entries = self.menu_of_layout()
        self.assertEqual(button.property('text'), 'Layout')
        self.assertEqual([e.property('text') for e in entries],
                         ['Layout', 'Row of modules', 'Area with automatic layout', 'Fill', 'Empty'])
        self.assertEqual([e.property('shortcutText') for e in entries][:2], ['S', 'L'])
        for gone in ('tool_fill', 'tool_empty', 'tool_canopy_layout', 'tool_layout_east_west'):
            self.assertEqual(self.visible(gone), [], gone)
        self.assertIsNone(self.find('phaseMenu_layout_east_west'))
        self.assertIsNone(self.find('phaseMenu_canopy_layout'))

    def test_the_summary_of_the_modules_comes_up_into_the_bar(self):
        trailing = self.find('phaseTrailing')
        wait_for(lambda: trailing.isVisible(), 5)       # at 1400 px the summary stands in the bar
        bar = self.find('phaseToolbar')
        self.assertAlmostEqual(trailing.mapToScene(QPointF(0, 0)).y(), bar.mapToScene(QPointF(0, 0)).y(), delta=1)

    def test_the_defect_fill_on_a_drawn_sub_field_is_off_and_says_why(self):
        """Before: on a sub-field drawn with Layout «Fill» was on and did nothing, saying nothing."""
        drawn = self.session.subfield(self.sub['Disegnato'])
        self.assertTrue(drawn.manual and drawn.filled)
        self.session.select('subfield', drawn.id)
        pump(100)
        shell = self.host.shell
        self.assertFalse(shell.commandEnabled['fill'])
        self.assertEqual(shell.commandNote['fill'], 'already full')
        _button, entries = self.menu_of_layout()
        fill = entries[3]
        self.assertFalse(fill.property('enabled'))
        self.assertEqual(fill.property('shortcutText'), 'already full', 'the reason beside it')
        steps = len(self.session.undo.steps)
        shell.trigger('fill')                       # the Draw menu (Alt) and a key reach it anyway
        pump(50)
        self.assertEqual(len(self.session.undo.steps), steps, 'nothing changed')
        self.assertIn('«Disegnato» is already full', shell.notice)

    def test_the_defect_fill_acts_or_is_off_with_its_reason(self):
        """The contract alone, with what r32-unita had too (it was red there: on, nothing done, nothing said)."""
        drawn = self.sub['Disegnato']
        self.session.select('subfield', drawn)
        pump(100)
        shell = self.host.shell
        steps = len(self.session.undo.steps)
        off = shell.commandEnabled['fill'] is False
        shell.trigger('fill')
        pump(50)
        acted = len(self.session.undo.steps) != steps
        said = bool(shell.notice)
        self.assertTrue(acted or (off and said), f'on={not off}, acted={acted}, said={shell.notice!r}')

    def test_fill_and_empty_do_what_they_say(self):
        shell = self.host.shell
        area = self.sub['Area']
        self.session.select('subfield', area)
        pump(100)
        self.assertTrue(shell.commandEnabled['fill'])
        self.assertNotIn('fill', shell.commandNote)
        shell.trigger('fill')
        self.assertTrue(self.session.subfield(area).filled)
        self.assertEqual(self.session.undo.steps[self.session.undo.index - 1].text, 'Fill')
        shell.trigger('empty')
        self.assertFalse(self.session.subfield(area).filled)
        self.assertEqual(self.session.undo.steps[self.session.undo.index - 1].text, 'Empty')

    def test_area_with_automatic_layout_from_the_bar_and_from_the_roof(self):
        shell, plan = self.host.shell, self.host.plan
        shell.trigger('fill_area')
        self.assertEqual(plan.tool, 'subfield')
        self.assertEqual(plan.drawing.options.get('fill'), 'area')
        shell.escape()
        shell.trigger('tool_subfield')               # S draws a sub-field that is its modules again
        self.assertEqual(plan.tool, 'subfield')
        self.assertNotEqual(plan.drawing.options.get('fill', 'modules'), 'area')
        shell.escape()
        plan.contextAt(10.0, 10.0)
        entry = next(e for e in plan.contextItems if e['command'] == 'fill_area')
        self.assertEqual(entry['text'], 'Area with automatic layout', 'the same words as the bar')

    # the canopy's menu

    def centre(self, b):
        xs, ys = zip(*b.footprint, strict=True)
        return sum(xs) / len(xs), sum(ys) / len(ys)

    def test_the_canopy_menu_on_the_plan_opens_the_window_with_that_canopy(self):
        plan, dialogs = self.host.plan, self.host.parts.controllers['dialogs']
        second = self.canopies[1]
        plan.contextAt(*self.centre(second))
        found = plan.contextItems
        self.assertTrue(found[0]['header'])
        self.assertEqual(found[0]['text'], f'Canopy «{second.name}»')
        self.assertEqual((found[1]['command'], found[1]['text']), ('canopy_layout', 'Modules on a canopy…'))
        plan.contextCommand('canopy_layout')
        wait_for(lambda: dialogs.kind == 'canopy-layout', 5)
        self.assertEqual(dialogs.state['bid'], second.id, 'the canopy of the menu, not the first')
        self.host.parts.controllers['filePart'].dismissDialog()
        dialogs.cancel()
        self.host.window.showPhase('model')
        pump(100)
        plan.contextAt(*self.centre(second))
        self.assertNotIn('canopy_layout', [e['command'] for e in plan.contextItems], 'only in the Plant')

    def test_the_canopy_menu_in_the_3d_view_opens_the_window_with_that_canopy(self):
        scene, dialogs = self.host.scene, self.host.parts.controllers['dialogs']
        second = self.canopies[1]
        self.session.select('building', second.id)
        pump(100)
        found = scene.contextActions
        self.assertTrue(found[0]['header'])
        self.assertEqual(found[0]['text'], f'Canopy «{second.name}»')
        self.assertEqual((found[1]['key'], found[1]['text']), ('canopy_layout', 'Modules on a canopy…'))
        scene.contextCommand('canopy_layout', '')
        wait_for(lambda: dialogs.kind == 'canopy-layout', 5)
        self.assertEqual(dialogs.state['bid'], second.id)
        self.host.parts.controllers['filePart'].dismissDialog()
        dialogs.cancel()
        house = self.session.project.buildings[0]
        self.session.select('building', house.id)
        self.assertNotIn('canopy_layout', [a['key'] for a in scene.contextActions], 'a building is not a canopy')

    # the same entries everywhere

    def test_a_sub_field_s_entries_are_the_same_words_everywhere(self):
        tree = self.host.parts.controllers['inspectors'].tree
        for name, first, enabled, note in (('Sud', 'Fill', False, 'already full'),
                                           ('Disegnato', 'Lay again automatically', True, ''),
                                           ('Area', 'Fill', True, '')):
            sid = self.sub[name]
            self.session.select('subfield', sid)
            self.host.plan.contextAt(*self.centre_of(sid))
            plan = [e for e in self.host.plan.contextItems if e['command'] in ('lay', 'relayout')]
            scene = [a for a in self.host.scene.contextActions if a['key'] in ('fill', 'relayout')]
            self.assertEqual((plan[0]['text'], plan[0]['enabled'], plan[0]['note']), (first, enabled, note), name)
            self.assertEqual((scene[0]['text'], scene[0]['enabled'], scene[0]['note']), (first, enabled, note), name)
            said = [a for a in tree.actions('subfield', sid) if a['id'] in ('fill', 'relayout')]
            self.assertEqual((said[0]['text'], said[0]['enabled'], said[0]['note']), (first, enabled, note), name)
            for words in (e['text'] for e in self.host.plan.contextItems):
                self.assertNotIn(words, ('Lay the modules', 'Lay again', 'Take the modules out'))

    def centre_of(self, sid):
        ring = self.session.subfield(sid).ring
        xs, ys = zip(*ring, strict=True)
        return sum(xs) / len(xs), sum(ys) / len(ys)

    # the «?» of the card

    def test_the_card_help_mark_stands_at_the_right_of_its_head(self):
        mark = self.visible('propertiesHelp')[0]
        card = self.find('rightPanel')
        left = mark.mapToScene(QPointF(0, 0)).x() - card.mapToScene(QPointF(0, 0)).x()
        right = card.width() - left - mark.width()
        self.assertGreater(left, card.width() / 2, 'on the right of the head, after the title')
        self.assertLess(right, 48, 'beside the cross, at the end of the head')


class TheSunMapTexts(unittest.TestCase):
    """R564 points 9 and 10: the two texts of the sun map."""

    def test_the_modules_line_says_it_is_without_shadows_as_the_line_above(self):
        from types import SimpleNamespace
        from meridiana.gui.backend.plan_map import PlanMapBackend
        sun = SimpleNamespace(on=True, levels={}, modules={'s1': [{'tilt': 15.0, 'free': 1388.4}]},
                              layers=lambda sid: (True, True), changing=False)
        fake = SimpleNamespace(sun=sun, texts={'stale': 'to be updated'})
        surface = SimpleNamespace(id='s1', free=1290.2, shown=None, stale=False)
        lines = PlanMapBackend._label(fake, surface).split('\n')
        self.assertEqual(lines, ['1290 kWh/m² a year without shadows', 'modules (15°): 1388 kWh/m² a year without shadows'])

    def test_the_date_at_the_pointer_never_breaks_in_the_middle(self):
        from PySide6.QtGui import QFont, QTextLayout, QTextOption
        from meridiana.app import sun_map as sm
        _setup.qt_or_skip()
        day = sm.day_text((12, 21))
        self.assertEqual(day, '21 December')
        text = f'loss 3.2 %  ·  1290 kWh/m² a year  ·  6.5 h on {day}'
        # the line wrapped as narrow as the tooltip's text can be, at the width that would leave «21» alone at the end
        layout = QTextLayout(text, QFont('Segoe UI', 13))
        option = QTextOption()
        option.setWrapMode(QTextOption.WrapMode.WordWrap)
        layout.setTextOption(option)
        whole = QTextLayout(text[:text.index('21') + 2], QFont('Segoe UI', 13))
        whole.beginLayout()
        width = whole.createLine().naturalTextWidth() + 1
        whole.endLayout()
        layout.beginLayout()
        lines = []
        while True:
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(width)
            lines.append(text[line.textStart():line.textStart() + line.textLength()])
        layout.endLayout()
        self.assertTrue(any('21 December' in line for line in lines), lines)


if __name__ == '__main__':
    unittest.main()
