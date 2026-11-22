"""Daniel 21/11/2026: a field drawn too long by mistake (5635 modules on 1,5 km) froze the window: the preview laid and
drew every module at every move of the pointer, and the lay made 5635 shapes and their union on the window's thread.

Now the preview past plan_tools.PREVIEW_MODULES is the outline and the number, its cost the same at 10 000 modules as
at 1500; past CONFIRM_MODULES the lay asks first, and a sub-field is laid by a job (app/lay_job.py) whose rows are
those the window would have made.

    python -m unittest quick.pianta.test_posa_enorme
"""
import time
import unittest

import _setup
from PySide6.QtWidgets import QApplication

from meridiana.app import lay_job
from meridiana.app.session import project_from
from meridiana.core.layout import manual
from meridiana.core.model import model
from meridiana.gui.backend import plan_tools
from meridiana.gui.backend.plan import PlanController
from meridiana.gui.backend.plan_tools import DrawingMachine

setUpModule = _setup.keep_global_state
BUDGET_S = 0.03                 # a pointer's move past the limit: the preview of a few rings, never of the modules


def project():
    p = model.Project(name='Posa enorme')
    p.site = model.Site(lat=45.52, lon=9.04, address='')
    return p


def gesture(drawing, far):
    """The rectangle tool's gesture: a side of 60 m from (0, 0) North, then its depth East out to `far` metres, a
    move every 10 m: the times of each preview and the last one."""
    drawing.set_tool('subfield', fill='modules')
    drawing.set_rectangle(True)
    drawing.click((0.0, 0.0))
    drawing.click((0.0, 60.0))
    times, last = [], None
    x = 10.0
    while x <= far:
        start = time.perf_counter()
        drawing.move((x, 60.0))
        last = drawing.preview
        times.append(time.perf_counter() - start)
        x += 10.0
    return times, last


class FieldPreview(unittest.TestCase):
    def test_a_gesture_out_to_ten_thousand_modules_never_draws_them_all(self):
        drawing = DrawingMachine(project())
        times, last = gesture(drawing, 1700.0)
        modules = last['modules']
        self.assertTrue(modules['estimated'])
        self.assertEqual(modules['quads'], [])
        self.assertGreater(modules['count'], 9000)
        # every preview past the limit costs the same: none near the cost of laying the modules
        past = times[len(times) // 2:]
        self.assertLess(max(past), BUDGET_S, [round(t * 1000, 1) for t in past[-5:]])
        self.assertIn('about', ' '.join(last['card']['lines']))

    def test_the_estimate_is_close_to_the_modules_laid(self):
        drawing = DrawingMachine(project())
        _times, last = gesture(drawing, 1000.0)
        p = project()
        sf = p.new_subfield('_x', '', [[0, 0], [1000, 0], [1000, 60], [0, 60]], None, None)
        laid = len(manual.corners(p, sf, manual.grid(p, sf)))
        self.assertAlmostEqual(last['modules']['count'] / laid, 1.0, delta=0.1)

    def test_under_the_limit_the_modules_are_drawn(self):
        drawing = DrawingMachine(project())
        # R712 (4515404a): the preview draws up to PREVIEW_MODULES = 800 modules; 60 x 40 m holds about 600
        _times, last = gesture(drawing, 40.0)
        self.assertFalse(last['modules'].get('estimated', False))
        self.assertEqual(len(last['modules']['quads']), last['modules']['count'])
        self.assertLessEqual(last['modules']['count'], plan_tools.PREVIEW_MODULES)


class LongRow(unittest.TestCase):
    def test_a_row_past_the_limit_is_its_outline(self):
        p = project()
        p.subfields.append(model.SubField(id='s1', name='Area', filled=False,
                                          ring=[[0, 0], [5000, 0], [5000, 40], [0, 40]]))
        drawing = DrawingMachine(p)
        drawing.set_tool('row')
        start = time.perf_counter()
        result = drawing.row_values([(1.0, 1.0), (4900.0, 1.0)])
        spent = time.perf_counter() - start
        self.assertGreater(result['count'], plan_tools.PREVIEW_MODULES)
        self.assertEqual(result['quads'], [])
        self.assertEqual(len(result['outline']), 4)
        self.assertFalse(result['bad'])
        self.assertLess(spent, 0.2)


class AskFirst(unittest.TestCase):
    RING = [[0, 0], [1486.47, 0], [1486.47, 8], [0, 8]]

    def setUp(self):
        QApplication.instance() or QApplication([])
        self.c = PlanController(project(), manage_layout=False)
        self.asked = []
        self.c.relayoutRequested.connect(lambda title, text: self.asked.append(text))
        self.c.setTool('subfield')

    def tearDown(self):
        self.c.close()

    def draw(self):
        command = {'type': 'polygon', 'tool': 'subfield', 'ring': self.RING, 'spec': {'fill': 'modules'}}
        self.c._run(lambda: [command])

    def test_a_large_field_asks_first_and_no_answers_nothing(self):
        self.draw()
        self.assertEqual(len(self.asked), 1, 'asked once')
        self.assertIn('km', self.asked[0])
        self.assertEqual(self.c.session.project.subfields, [])
        self.c.confirmRelayout(False)
        self.assertEqual(self.c.session.project.subfields, [])

    def test_yes_lays_it_as_the_job_would(self):
        self.draw()
        photo = self.c.session.photo()
        self.c.confirmRelayout(True)        # no center in the tests' plan: laid at once
        sf = self.c.session.project.subfields[-1]
        self.assertTrue(sf.flush)
        made = lay_job.lay(project_from(photo), self.RING)
        self.assertEqual(sf.rows, made['rows'])
        self.assertEqual(sf.ring, made['ring'])
        # and the rows the job gives are written as they came, with one undo
        self.c.session.undo.undo()
        self.assertEqual(self.c.session.project.subfields, [])
        self.c._lay_came({'type': 'polygon', 'tool': 'subfield', 'ring': self.RING, 'spec': {'fill': 'modules'}}, made)
        self.assertEqual(self.c.session.project.subfields[-1].rows, made['rows'])
        self.assertEqual(self.c.session.project.subfields[-1].ring, made['ring'])


if __name__ == '__main__':
    unittest.main()
