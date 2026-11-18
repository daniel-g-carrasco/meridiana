"""R389: the complete object menu and its undoable commands, from window.context_actions."""
import unittest

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from meridiana import model
from meridiana.quick.backend.plan import PlanController

APP = None


def setUpModule():
    global APP
    APP = QApplication.instance() or QApplication([])


class Context(unittest.TestCase):
    def setUp(self):
        p = model.Project(name='Menu parity')
        p.buildings.append(model.Building(id='b1', name='Roof', footprint=[[0, 0], [40, 0], [40, 20], [0, 20]]))
        p.subfields.append(model.SubField(id='s1', name='Array', building='b1', filled=True,
                                         ring=[[2, 2], [38, 2], [38, 18], [2, 18]]))
        self.c = PlanController(p, manage_layout=False)
        self.c.session.results = {'s1': p.fill(p.subfields[0])}
        self.c.refresh()

    def tearDown(self):
        self.c.close()

    def commands(self):
        return [r['command'] for r in self.c.contextItems if not r['separator']]

    def test_object_menus_match_widgets(self):
        for kind, oid, commands in [
            ('site', '', ['properties', 'frame']),
            ('building', 'b1', ['properties', 'frame', 'pitches', 'fire_bands', 'fire_bands_all', 'cut', 'copy', 'rename',
                                'duplicate', 'square', 'remove']),       # the bands: R445, decision 2
            ('subfield', 's1', ['properties', 'frame', 'lay', 'explode_all', 'empty', 'rename', 'duplicate', 'square', 'remove']),
        ]:
            self.c.editor.select(kind, oid)
            self.assertEqual(self.commands(), commands)
        self.c.contextAt(-100, -100)
        self.assertEqual(self.c.editor.selection, ('site', ''))

    def test_module_row_commands_and_explode_undo(self):
        module = self.c.editor.results['s1'].modules[0]
        self.c.editor.select('subfield', 's1', module.key)
        # R533: the module, its row, then its sub-field in a submenu, whose «Delete» says it deletes the sub-field
        self.assertEqual(self.commands(), ['properties', 'frame', 'remove', 'select_row', 'remove_row', 'append_row',
            'resize_row', 'explode_row', 'lay', 'explode_all', 'empty', 'rename', 'duplicate', 'square', 'delete_subfield'])
        menus = {r['command']: r['menu'] for r in self.c.contextItems if not r['separator']}
        self.assertEqual(menus['remove'], '')
        self.assertEqual(menus['select_row'], '')
        self.assertTrue(menus['lay'] and menus['lay'] == menus['delete_subfield'])
        titles = [r['text'] for r in self.c.contextItems if r.get('header')]
        self.assertEqual(len(titles), 2)                                       # Module, Row
        self.c.contextCommand('select_row')
        self.assertEqual(self.c.editor.selection, ('row', 's1/'+module.rid))
        before = self.c.session.project.to_json()
        self.c.contextCommand('explode_row')
        self.assertFalse(self.c.error)
        self.assertTrue(self.c.session.project.subfields[0].manual)
        self.c.session.undo.undo()
        self.assertEqual(self.c.session.project.to_json(), before)

    def test_empty_preserves_hand_rows_and_pitches_are_outlines(self):
        self.c.editor.select('subfield', 's1')
        self.c.contextCommand('explode_all')
        self.assertFalse(self.c.error)
        before = self.c.session.project.subfields[0].rows.copy()
        self.c.contextCommand('empty')
        sf = self.c.session.project.subfields[0]
        self.assertFalse(sf.filled)
        self.assertEqual(sf.rows, before)
        self.c.editor.select('building', 'b1')
        self.c.contextCommand('pitches')
        self.assertFalse(self.c.error)
        self.assertEqual(len(self.c.session.project.subfields), 2)
        self.assertFalse(self.c.session.project.subfields[-1].filled)

    def test_drawing_menu_only_drawing_actions(self):
        self.c.setTool('building')
        self.c.click(0, 0)
        self.assertEqual(self.commands(), ['close_outline', 'back', 'cancel_outline'])
        self.assertFalse(self.c.contextItems[0]['enabled'])
        self.c.contextCommand('cancel_outline')
        self.assertEqual(self.c.tool, 'building')
        self.assertFalse(self.c.drawing.points)

    def test_r508_while_a_string_is_drawn_its_commands_come_first(self):
        self.c.setPhase('plant')
        modules = self.c.editor.results['s1'].modules
        self.c.setTool('string')                         # as plantActions.draw does
        self.c.editor.start_draft(1, 1)
        x, y = modules[0].centre
        self.c.click(x, y)
        self.c.click(*modules[1].centre)
        self.assertEqual(len(self.c.editor.draft), 2)
        self.c.contextAt(*modules[2].centre)
        self.assertEqual(self.commands()[:3], ['finish_string', 'back_module', 'cancel_string'])
        self.assertNotIn('properties', self.commands())
        self.assertTrue(self.c.contextItems[0]['enabled'])
        self.assertIn('copy_degrees', self.commands())    # the point under the click, as everywhere (R487)
        self.c.contextCommand('back_module')
        self.assertEqual(len(self.c.editor.draft), 1)
        self.c.contextCommand('finish_string')
        self.assertIsNone(self.c.editor.draft)
        self.assertEqual(len(self.c.editor.runs()), 1)
        self.assertEqual(self.c.tool, 'select')
        count = self.c.session.undo.count()
        self.c.setTool('string')
        self.c.editor.start_draft(1, 1)
        self.c.contextAt(*modules[2].centre)
        self.assertFalse(self.c.contextItems[0]['enabled'], 'nothing to finish yet')
        self.assertFalse(self.c.contextItems[1]['enabled'], 'no module to take back')
        self.c.click(*modules[2].centre)
        self.c.contextCommand('cancel_string')
        self.assertIsNone(self.c.editor.draft)
        self.assertEqual(self.c.session.undo.count(), count)
        self.assertEqual(self.c.tool, 'select')

    def test_manual_relayout_asks_and_cancel_keeps_rows_then_undo_restores_them(self):
        self.c.editor.select('subfield', 's1')
        self.c.contextCommand('explode_all')
        before = self.c.session.project.to_json()
        prompts = []
        self.c.relayoutRequested.connect(lambda title, text: prompts.append((title, text)))
        self.c.contextCommand('relayout')
        self.assertEqual(len(prompts), 1)
        self.assertEqual(self.c.session.project.to_json(), before)
        self.c.confirmRelayout(False)
        self.assertEqual(self.c.session.project.to_json(), before)
        self.c.contextCommand('relayout')
        self.c.confirmRelayout(True)
        self.assertFalse(self.c.session.project.subfields[0].manual)
        self.assertFalse(self.c.error)
        self.c.session.undo.undo()
        self.assertEqual(self.c.session.project.to_json(), before)

    def test_phase_string_visibility_and_aids_persist_across_tools(self):
        self.assertFalse(self.c.stringsVisible)
        self.c.setPhase('plant')
        self.assertTrue(self.c.stringsVisible)
        self.c.setPhase('model')
        self.assertFalse(self.c.stringsVisible)
        self.c.key('W')
        self.assertTrue(self.c.stringsVisible)
        self.c.key('F3')
        self.assertFalse(self.c.snapsEnabled)
        self.c.setTool('building')
        self.assertFalse(self.c.drawing.snaps_on)
        self.c.key('F8')
        self.assertTrue(self.c.orthoEnabled)

    def test_unassigned_modules_are_red_even_before_the_first_string(self):
        self.c.setPhase('plant')
        self.assertFalse(self.c.editor.runs())
        self.assertEqual(len(self.c.unwiredPaths), len(self.c.editor.results['s1'].modules))     # their own layer (R496)
        from meridiana import theme_colors
        self.assertTrue(all(row['stroke'] == theme_colors.STATUS['critical'] for row in self.c.unwiredPaths))
        self.assertFalse(self.c.wireFills)
        self.c.setPhase('model')
        self.assertFalse(self.c.stringsVisible, "the plan hides the layers; they stay built for the way back (R483)")
        self.assertEqual(len(self.c.unwiredPaths), len(self.c.editor.results['s1'].modules))


if __name__ == '__main__':
    unittest.main()
