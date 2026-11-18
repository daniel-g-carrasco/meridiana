"""Placing an imported IFC model under the native mouse and keyboard, on its own desktop (R454): «Add» hands the model to
the plan, its outline follows the real pointer and takes the shed's corner, R and the wheel held with Shift turn it, a
click lays it, Ctrl+Z takes the whole import back; on the shed the question, «Beside» lays it next to it; C opens the
coordinates with the file's place first and the warning beyond FAR_KM; Esc gives the import up; saved and opened again
it is where it was laid. A model built by the test, no client's data.

    python -m unittest quick.percorsi.test_native_posiziona
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from quick.percorsi.test_native import _run

JOURNEY = r'''
import json, tempfile
from pathlib import Path
from PySide6.QtCore import QPointF
from meridiana import model

seen = {}
wait_until(lambda: host.plan is not None, 60)
host.shell.trigger('phase_model')
spin(1.0)
area = find(win, name='plan')
plan = host.plan
session = host.bridge.session
dialogs = host.parts.controllers['dialogs']
wait_until(lambda: area.property('fitted') and area.property('zoom') > 2, 30)
RING = [[100.0, 100.0], [120.0, 100.0], [120.0, 110.0], [100.0, 110.0]]
FOUND = {"schema": "IFC4", "application": "Prova", "unit_m": 1.0, "true_north": 0.0, "map": None,
         "site": {"lat": 45.5201, "lon": 9.0402, "elevation": 0.0, "name": "Cantiere", "placement": [0.0, 0.0, 0.0]},
         "sites": 1, "address": "", "obstacles": [], "counts": {}, "supports": [], "times": {"total": 1.0},
         "buildings": [{"name": "Palazzetto", "ifc": "x", "ground": 0.0, "source": "roof", "footprint": RING,
                        "pitches": [{"ring": RING, "normal": [0.0, 0.0, 1.0], "point": [110.0, 105.0, 8.0],
                                     "area": 200.0, "holes": 0, "owners": [1]}]}]}


def at(x, y):
    p = area.screen(x, y)
    q = area.mapToScene(QPointF(p.x(), p.y()))
    return q.x(), q.y()


def buildings():
    return [dict(id=b.id, name=b.name, group=b.group, ring=b.footprint) for b in session.project.buildings]


def start_import():
    dialogs.open('ifc')
    dialogs._state['fileName'] = 'palazzetto.ifc'
    dialogs._ifc_done(dialogs._generation, json.loads(json.dumps(FOUND)))
    wait_until(lambda: not dialogs.busy and dialogs.state['valid'], 30)
    seen.setdefault('how', dialogs.state['how'])
    dialogs.accept()
    spin(0.5)
    area.forceActiveFocus()
    spin(0.2)


def shift_wheel(x, y, notches):
    VK_SHIFT, VK_LSHIFT = 0x10, 0xA0
    state = (__import__('ctypes').c_ubyte * 256)()
    user32.GetKeyboardState(state)
    state[VK_SHIFT] = state[VK_LSHIFT] = 0x80
    user32.SetKeyboardState(state)
    native.wheel(x, y, notches)
    state[VK_SHIFT] = state[VK_LSHIFT] = 0
    user32.SetKeyboardState(state)
    spin(0.2)


start_import()
seen['placing'] = dict(plan.placing)
seen['placing'].pop('values', None); seen['placing'].pop('systems', None); seen['placing'].pop('labels', None)
seen['placing'].pop('texts', None); seen['placing'].pop('proposal', None)
seen['hint'] = area.property('statusText')
native.move(*at(55.0, 30.0)); spin(0.2)
native.move(*at(50.15, 5.1)); spin(0.4)
seen['snap'] = plan.placer.snap.kind
seen['ghost'] = len([o for o in plan.draftObjects if o.get('kind') == 'ghost'])
native.key('r'); spin(0.3)
seen['turn_r'] = plan.placer.pl.turn
shift_wheel(*at(50.15, 5.1), -1)
seen['turn_wheel'] = plan.placer.pl.turn
native.move(*at(50.1, 5.05)); spin(0.3)
native.click(*at(50.15, 5.1), settle=400)
spin(0.6)
seen['laid'] = buildings()
seen['selection'] = list(plan.editor.selection)
native.key('z', modifiers=('ctrl',)); spin(0.8)
seen['after_undo'] = len(session.project.buildings)

start_import()
native.move(*at(20.0, 10.0)); spin(0.4)
native.click(*at(20.0, 10.0), settle=500)
spin(0.6)
button = find(win, name='placeBeside')
seen['question'] = button is not None
if button is not None:
    native.click(*center(button), settle=500)
    spin(0.8)
seen['beside'] = buildings()
native.key('z', modifiers=('ctrl',)); spin(0.8)

start_import()
native.move(*at(70.0, 40.0)); spin(0.3)
native.key('c'); spin(0.8)
system = find(win, name='placeSystem')
seen['coordinates_open'] = system is not None
seen['proposed'] = [find(win, name='placeA').property('text'), find(win, name='placeB').property('text')] if system else []
field = find(win, name='placeA')
if field is not None:
    native.click(*center(field), settle=200)
    native.key('a', modifiers=('ctrl',))
    native.type_text('45,62'); spin(0.4)
    seen['far'] = find(win, name='placeCheck').property('text')
    native.key('a', modifiers=('ctrl',))
    native.type_text('45,5205'); spin(0.4)
    seen['near'] = find(win, name='placeCheck').property('text')
    native.click(*center(find(win, name='placeThere')), settle=500)
    spin(0.5)
    area.forceActiveFocus(); spin(0.2)
    seen['follow_after'] = plan.placing.get('follow')
    native.key('enter'); spin(0.8)
seen['by_coordinates'] = buildings()
folder = Path(tempfile.mkdtemp())
session.project.save(folder / 'posato.meridiana')
again, _note = model.Project.load(folder / 'posato.meridiana')
seen['reopened'] = [b.footprint for b in again.buildings] == [b.footprint for b in session.project.buildings]

start_import()
native.move(*at(70.0, 40.0)); spin(0.3)
native.key('esc'); spin(0.5)
seen['after_esc'] = dict(active=plan.placing['active'], count=len(session.project.buildings))
print(json.dumps(seen, default=str))
'''


def _project(folder: Path) -> Path:
    from meridiana import model
    p = model.Project(name='Prova posa IFC')
    p.site = model.Site(lat=45.52, lon=9.04, address='Rho (MI)')
    p.buildings.append(model.Building(id='b1', name='Capannone', footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                                      height=8.0))
    path = folder / 'posa.meridiana'
    p.save(path)
    return path


@unittest.skipUnless(sys.platform == 'win32', 'Windows messages')
@unittest.skipIf(os.environ.get('MERIDIANA_NO_NATIVE'), 'switched off')
class PlaceIfc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        folder = Path(cls.folder.name)
        ctl = folder / 'ctl'
        args = ['--ctl', str(ctl), '--project', str(_project(folder)), '--no-calc',
                '--desktop', 'meridiana-collaudo-posiziona', '--timeout', '100']
        code, output = _run('start', *args, timeout=140)
        if code:
            raise unittest.SkipTest(f'no program: {output[-300:]}')
        script = folder / 'journey.py'
        script.write_text(JOURNEY, encoding='utf-8')
        try:
            code, output = _run('run', '--ctl', str(ctl), str(script), timeout=300)
            lines = [line for line in output.splitlines() if line.startswith('{')]
            if not lines:
                raise AssertionError(f'the journey said nothing: {output[-1500:]}')
            cls.seen = json.loads(lines[-1])
        finally:
            _run('run', '--ctl', str(ctl), '--stop', timeout=30)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_add_hands_the_model_to_the_plan_with_its_help(self):
        self.assertEqual(self.seen['how'], 'hand')
        self.assertTrue(self.seen['placing']['active'])
        self.assertTrue(self.seen['placing']['follow'])
        self.assertIn('Esc', self.seen['hint'])

    def test_the_outline_follows_the_mouse_takes_the_corner_and_turns(self):
        self.assertGreater(self.seen['ghost'], 0)
        self.assertEqual(self.seen['snap'], 'corner')
        self.assertAlmostEqual(self.seen['turn_r'], 15.0)
        self.assertAlmostEqual(self.seen['turn_wheel'], 0.0)

    def test_a_click_lays_it_on_the_corner_and_ctrl_z_takes_it_back(self):
        laid = self.seen['laid']
        self.assertEqual(len(laid), 2)
        xs = [q[0] for q in laid[1]['ring']]
        ys = [q[1] for q in laid[1]['ring']]
        self.assertEqual((min(xs), min(ys)), (40.0, 0.0))
        self.assertEqual(self.seen['selection'][:2], ['building', laid[1]['id']])
        self.assertEqual(self.seen['after_undo'], 1)

    def test_on_the_shed_the_question_and_beside(self):
        self.assertTrue(self.seen['question'])
        beside = self.seen['beside']
        self.assertEqual(len(beside), 2)
        from shapely.geometry import Polygon
        self.assertLess(Polygon(beside[0]['ring']).intersection(Polygon(beside[1]['ring'])).area, 1e-6)

    def test_coordinates_with_the_files_place_first_and_the_warning(self):
        self.assertTrue(self.seen['coordinates_open'])
        self.assertTrue(self.seen['proposed'][0].startswith('45'))
        self.assertIn('km', self.seen['far'])
        self.assertNotEqual(self.seen['far'], self.seen['near'])
        self.assertFalse(self.seen['follow_after'])
        self.assertEqual(len(self.seen['by_coordinates']), 2)
        self.assertTrue(self.seen['reopened'])

    def test_esc_gives_the_import_up(self):
        self.assertEqual(self.seen['after_esc'], {'active': False, 'count': 2})


if __name__ == '__main__':
    unittest.main()
