"""R529, R531, R532, R533: a click takes the module under it, Del and «Delete» take out the modules selected, the menu
looks at the selection. The native mouse is in quick.percorsi.test_native_clic.

    python -m unittest quick.pianta.test_module_clicks
"""
import unittest

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from meridiana import model
from meridiana.quick.backend.plan import PlanController

APP = None


def setUpModule():
    global APP
    APP = QApplication.instance() or QApplication([])


class ModuleClicks(unittest.TestCase):
    def setUp(self):
        p = model.Project(name='Clicks')
        p.buildings.append(model.Building(id='b1', name='Roof', footprint=[[0, 0], [40, 0], [40, 20], [0, 20]]))
        p.subfields.append(model.SubField(id='s1', name='Array', building='b1', filled=True,
                                         ring=[[2, 2], [38, 2], [38, 18], [2, 18]]))
        self.c = PlanController(p, manage_layout=False)
        self.c.session.results = {'s1': p.fill(p.subfields[0])}
        self.c.refresh()
        self.c.setPhase('plant') if hasattr(self.c, 'setPhase') else self.c.editor.set_phase('plant')
        self.c.pointerScale(0.05, 0)
        self.e = self.c.editor
        self.modules = self.c.session.good_results()['s1'].modules

    def tearDown(self):
        self.c.close()

    def row_mates(self):
        first = self.modules[0]
        return first, next(m for m in self.modules if m.rid == first.rid and m.key != first.key)

    def test_another_module_of_the_row_is_that_module_and_the_same_module_twice_is_the_row(self):
        first, mate = self.row_mates()
        self.c.click(*first.centre, 0)
        self.assertEqual(self.e.selected_module, ('s1', first.key))
        self.c.click(*mate.centre, 0)                   # before R529: the row, while the hover showed the module
        self.assertEqual(self.e.selected_module, ('s1', mate.key))
        self.c.click(*mate.centre, 0)
        self.assertEqual(self.e.selection, ('row', 's1/' + first.rid))
        self.c.click(*first.centre, 0)
        self.assertEqual(self.e.selected_module, ('s1', first.key))

    def test_a_click_on_a_check_mark_over_the_modules_takes_the_module_under_it(self):
        first, mate = self.row_mates()
        shown = []
        self.c.markClicked.connect(lambda kind, oid: shown.append((kind, oid)))
        self.c.markClick('subfield', 's1', *first.centre)          # before: the sub-field, the module lost
        self.assertEqual(self.e.selected_module, ('s1', first.key))
        self.c.markClick('subfield', 's1', *mate.centre)
        self.assertEqual(self.e.selected_module, ('s1', mate.key))
        self.assertEqual(shown, [('subfield', 's1')])               # its checks shown once, as the mark did
        self.c.markClick('building', 'b1', *mate.centre)
        self.assertEqual(self.e.selection[0], 'building')

    def test_two_presses_on_one_side_at_two_places_are_not_a_double_click(self):
        self.e.select('subfield', 's1')
        self.c._overlays()
        self.c.beginSide(0, 3.0, 2.0)
        self.c.cancelSideDrag()
        self.c.beginSide(0, 20.0, 2.0)                  # same side, 17 m away, within 0.4 s
        self.assertIsNone(self.c._side)
        self.c.cancelSideDrag()

    def sweep_all(self):
        self.c.sweep([[0, 0], [40, 0], [40, 20], [0, 20]], 'window', 0)
        return len(self.e.swept)

    def test_delete_takes_out_the_modules_selected_in_one_step_and_says_how_many(self):
        n = self.sweep_all()
        self.assertGreater(n, 30)
        undo = self.c.session.undo.count()
        self.c.key('Delete', '', 0)
        self.assertEqual(len(self.c.session.project.subfields[0].removed), n)
        self.assertEqual(self.c.session.undo.count(), undo + 1)
        self.assertIn(str(n), self.c.hint)
        self.assertEqual(self.e.swept, [])

    def test_delete_takes_out_the_modules_also_with_the_strings_open(self):
        n = self.sweep_all()
        self.e.strings_mode = True                      # Inverter open (R531: Del did nothing)
        self.c.key('Delete', '', 0)
        self.assertEqual(len(self.c.session.project.subfields[0].removed), n)
        self.assertEqual(len(self.c.session.project.subfields), 1)

    def test_the_menu_on_many_modules_speaks_of_them_and_keeps_the_sub_field_apart(self):
        n = self.sweep_all()
        self.c.contextAt(*self.modules[3].centre)
        self.assertEqual(len(self.e.swept), n)
        items = self.c.contextItems
        top = [r for r in items if not r['menu'] and not r['separator']]
        commands = [r['command'] for r in top]
        for single in ('remove', 'select_row', 'remove_row', 'append_row', 'resize_row', 'explode_row', 'add_module'):
            self.assertNotIn(single, commands)
        self.assertIn('remove_selected', commands)
        self.assertIn(str(n), next(r['text'] for r in top if r['command'] == 'remove_selected'))
        self.assertIn(str(n), next(r['text'] for r in items if r.get('header')))
        sub = {r['command']: r['menu'] for r in items if r['menu']}
        self.assertTrue(sub['delete_subfield'] and sub['delete_subfield'] == sub['lay'])
        self.assertNotIn('Delete', [r['text'] for r in items])     # never a bare «Delete»
        undo = self.c.session.undo.count()
        self.c.contextCommand('remove_selected')
        self.assertEqual(len(self.c.session.project.subfields[0].removed), n)
        self.assertEqual(self.c.session.undo.count(), undo + 1)

    def test_select_their_rows_and_delete_the_sub_field(self):
        first, mate = self.row_mates()
        self.c.sweep([[first.corners[0][0] - .01, first.corners[0][1] - .01]] + [[x, y] for x, y in first.corners[1:]],
                     'crossing', 0)
        self.c.sweep([[x + .0, y] for x, y in mate.corners], 'crossing', 2)   # R529: Shift adds
        self.assertGreaterEqual(len(self.e.swept), 2)
        self.c.contextAt(*first.centre)
        self.c.contextCommand('select_rows')
        row = {m.key for m in self.modules if m.rid == first.rid}
        self.assertTrue(row <= {k for _s, k in self.e.swept})
        self.c.contextCommand('delete_subfield')
        self.assertEqual(self.c.session.project.subfields, [])


if __name__ == '__main__':
    unittest.main()
