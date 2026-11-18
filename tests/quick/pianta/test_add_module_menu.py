"""«Add a module here» in the plan's menu: one module where the menu was opened, never a whole row (06/11/2026)."""
import unittest

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from meridiana import model
from meridiana.quick.backend.plan import PlanController

APP = None


def setUpModule():
    global APP
    APP = QApplication.instance() or QApplication([])


class AddModuleMenu(unittest.TestCase):
    def setUp(self):
        p = model.Project(name='Add a module')
        p.buildings.append(model.Building(id='b1', name='Roof', footprint=[[0, 0], [40, 0], [40, 20], [0, 20]]))
        p.subfields.append(model.SubField(id='s1', name='Array', building='b1', filled=True,
                                         ring=[[2, 2], [38, 2], [38, 18], [2, 18]]))
        self.p = p
        self.c = PlanController(p, manage_layout=False)
        self.lay()

    def lay(self):
        self.c.session.results = {'s1': self.p.fill(self.p.subfields[0])}
        self.c.editor.set_results(self.c.session.results)
        self.c.refresh()

    def tearDown(self):
        self.c.close()

    def count(self):
        return len(self.p.fill(self.p.subfields[0]).modules)

    def test_the_menu_on_a_module_taken_out_puts_back_that_one(self):
        before = self.count()
        module = self.c.editor.results['s1'].modules[5]
        self.c.session.edit('out', lambda q: q.subfields[0].removed.append(module.key))
        self.lay()
        self.c.contextAt(*module.centre)
        commands = [r['command'] for r in self.c.contextItems if not r['separator']]
        self.assertIn('add_module', commands)
        texts = {r['command']: r['text'] for r in self.c.contextItems}
        self.assertNotIn('fila', texts['add_module'].lower())
        self.c.contextCommand('add_module')
        self.assertEqual(self.count(), before)
        self.assertEqual(self.p.subfields[0].removed, [])

    def test_the_menu_past_a_shorter_row_adds_one_module_not_a_row(self):
        result = self.c.editor.results['s1']
        row = next(r for r in result.rows if r.places)
        last = max((m for m in result.modules if m.rid == row.id), key=lambda m: m.slot)
        from meridiana import manual
        self.c.session.edit('take', manual.take(self.p, 's1', result))

        def shorten(q):
            q.subfields[0].rows[0]['places'] = q.subfields[0].rows[0]['places'][:-2]
        self.c.session.edit('shorter', shorten)
        self.lay()
        before = self.count()
        self.c.contextAt(*last.centre)
        self.c.contextCommand('add_module')
        self.assertEqual(self.c.error, '') if hasattr(self.c, 'error') else None
        self.assertEqual(self.count(), before + 1)


if __name__ == "__main__":
    unittest.main()
