"""R389: layouts follow edits asynchronously and old workers cannot overwrite a new edit."""
import time
import unittest

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from meridiana import jobs, model
from meridiana.quick.backend.plan import PlanController


class LayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_move_updates_module_geometry_and_rename_keeps_layout(self):
        project = model.Project(name='Async plan')
        project.subfields.append(model.SubField(id='s1', name='Field', filled=True,
                                 ring=[[0, 0], [40, 0], [40, 20], [0, 20]]))
        controller = PlanController(project)
        results, keys, _ = jobs.layout_of(project)
        controller.session.layout_done(0, results, keys)
        before = results['s1'].modules[0].centre
        controller.setPhase('plant')
        controller.editor.select('subfield', 's1')
        controller.editor.apply_command(dict(type='transform', kind='subfield', oid='s1', mode='move', dx=0., dy=20.))
        self.assertTrue(controller.busy)
        deadline = time.monotonic()+10
        while controller.busy and time.monotonic()<deadline:
            self.app.processEvents()
            time.sleep(.002)
        self.assertFalse(controller.busy)
        after = controller.session.results['s1'].modules[0].centre
        self.assertAlmostEqual(after[1]-before[1],20.)
        result = controller.session.results['s1']
        controller.session.edit('Rename',lambda p:setattr(p.subfields[0],'name','Renamed'))
        self.assertFalse(controller.busy)
        self.assertIs(controller.session.results['s1'],result)
        controller.close()

    def test_obsolete_worker_is_ignored(self):
        controller=PlanController(model.Project())
        controller.session.generation=2
        controller.scheduler.accept(1, {'old': ValueError('obsolete')}, {'old':'key'}, '')
        self.assertEqual(controller.session.results,{})
        controller.close()


if __name__=='__main__':
    unittest.main()
