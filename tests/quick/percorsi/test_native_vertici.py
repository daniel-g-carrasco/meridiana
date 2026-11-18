"""R356 (Daniel 08/11/2026: «intendevo selezionare e muovere più vertici alla volta») under the native mouse and
keyboard, on a desktop of its own. In Modellazione, on the corners of a building: a click chooses one, Shift+click adds,
Ctrl+click adds or takes away; a drag of a corner chosen moves them all in one Undo; the right arrow moves them by
10 cm; a figure opens the measure and Enter moves them by it along the last move; a window over some corners takes
them; Esc lets them go.

    python -m unittest quick.percorsi.test_native_vertici
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from quick.percorsi.test_native import _run
from quick.percorsi.test_native_sottocampo import _project

JOURNEY = r'''
import json
from PySide6.QtCore import QPointF

seen = {}
wait_until(lambda: host.plan is not None, 60)
host.shell.trigger('phase_model')
spin(1.5)
area = find(win, name='plan')
plan = host.plan
session = host.bridge.session
ed = plan.editor
wait_until(lambda: area.property('fitted') and area.property('zoom') > 2, 30)


def at(x, y):
    p = area.screen(x, y)
    q = area.mapToScene(QPointF(p.x(), p.y()))
    return q.x(), q.y()


def ring():
    return [[round(float(v), 3) for v in q[:2]] for q in session.project.buildings[0].footprint]


seen['before'] = ring()
native.click(*at(8, 15), settle=300); spin(0.5)
seen['selected'] = list(ed.selection)
native.click(*at(40, 0), settle=300); spin(0.3)
seen['one'] = list(plan.chosenCorners)
native.click(*at(40, 20), settle=300, modifiers=('shift',)); spin(0.3)
seen['shift'] = list(plan.chosenCorners)
native.click(*at(0, 20), settle=300, modifiers=('ctrl',)); spin(0.3)
seen['ctrl_on'] = list(plan.chosenCorners)
native.click(*at(0, 20), settle=300, modifiers=('ctrl',)); spin(0.3)
seen['ctrl_off'] = list(plan.chosenCorners)
seen['bar'] = area.property('localHint')
undo = session.undo.count()
native.drag(*at(40, 0), *at(44, 0), steps=16); spin(0.6)
seen['drag'] = ring()
seen['drag_steps'] = session.undo.count() - undo
seen['after_drag'] = list(plan.chosenCorners)
native.key('right'); spin(0.5)
seen['arrow'] = ring()
native.key('1'); spin(0.4)
field = find(win, name='cornersField')
seen['field'] = bool(field is not None and field.property('visible'))
native.key('enter'); spin(0.6)
seen['typed'] = ring()
seen['steps'] = session.undo.count() - undo
for _i in range(seen['steps']):
    native.key('z', modifiers=('ctrl',)); spin(0.4)
seen['undone'] = ring()
native.key('esc'); spin(0.3)
seen['esc'] = list(plan.chosenCorners)
native.drag(*at(36, -3), *at(46, 23), steps=16); spin(0.5)
seen['window'] = list(plan.chosenCorners)
seen['window_selection'] = list(ed.selection)
print(json.dumps(seen, default=str))
'''


@unittest.skipUnless(sys.platform == 'win32', 'Windows messages')
@unittest.skipIf(os.environ.get('MERIDIANA_NO_NATIVE'), 'switched off')
class MoreCorners(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        folder = Path(cls.folder.name)
        ctl = folder / 'ctl'
        args = ['--ctl', str(ctl), '--project', str(_project(folder)), '--no-calc',
                '--desktop', 'meridiana-collaudo-vertici', '--timeout', '100']
        code, output = _run('start', *args, timeout=140)
        if code:
            raise unittest.SkipTest(f'no program: {output[-300:]}')
        script = folder / 'journey.py'
        script.write_text(JOURNEY, encoding='utf-8')
        try:
            code, output = _run('run', '--ctl', str(ctl), str(script), timeout=400)
            lines = [line for line in output.splitlines() if line.startswith('{')]
            if not lines:
                raise AssertionError(f'the journey said nothing: {output[-800:]}')
            cls.seen = json.loads(lines[-1])
        finally:
            _run('run', '--ctl', str(ctl), '--stop', timeout=30)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_the_rule_of_the_selection_on_the_corners(self):
        s = self.seen
        self.assertEqual(s['selected'], ['building', 'b1'], s)
        self.assertEqual(s['one'], [1], s)
        self.assertEqual(s['shift'], [1, 2], s)
        self.assertEqual(s['ctrl_on'], [1, 2, 3], s)
        self.assertEqual(s['ctrl_off'], [1, 2], s)
        self.assertIn('Maiusc+clic: aggiunge', s['bar'])

    def test_a_drag_the_arrows_and_a_measure_move_them_together(self):
        s = self.seen
        before, drag, arrow, typed = s['before'], s['drag'], s['arrow'], s['typed']
        dx = drag[1][0] - before[1][0]
        self.assertGreater(dx, 2.0, s)
        self.assertAlmostEqual(drag[2][0] - before[2][0], dx, places=3)      # both, by the same step
        self.assertEqual([drag[0], drag[3]], [before[0], before[3]])           # the others stay
        self.assertEqual(s['drag_steps'], 1)
        self.assertEqual(s['after_drag'], [1, 2])
        self.assertAlmostEqual(arrow[1][0] - drag[1][0], 0.1, places=3)      # the right arrow: 10 cm East
        self.assertAlmostEqual(arrow[2][0] - drag[2][0], 0.1, places=3)
        self.assertTrue(s['field'])
        self.assertAlmostEqual(typed[1][0] - arrow[1][0], 1.0, places=3)     # «1» along the last move
        self.assertEqual(s['steps'], 3)
        self.assertEqual(s['undone'], before)

    def test_a_window_takes_some_corners_and_esc_lets_them_go(self):
        s = self.seen
        self.assertEqual(s['esc'], [])
        self.assertEqual(s['window'], [1, 2], s)
        self.assertEqual(s['window_selection'], ['building', 'b1'])


if __name__ == '__main__':
    unittest.main()
