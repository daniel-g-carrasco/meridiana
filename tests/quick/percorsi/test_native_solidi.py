"""The solids under the native mouse and keyboard, on their own desktop (study 37): the Building tool drawn inside a
roof with four clicks makes a plant room standing on it (R352), a click on it picks the room before the building under
it, its properties show where it stands and its base (R453), Ctrl+Z takes it back in one step; drawn outside, a
building from the ground as before; the roof type «Saddle-backed bands» gives the shed its bands (R455).

    python -m unittest quick.percorsi.test_native_solidi
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from quick.percorsi.test_native import _run

JOURNEY = r'''
import json
from PySide6.QtCore import QPointF

seen = {}
wait_until(lambda: host.plan is not None, 60)
host.shell.trigger('phase_model')
spin(1.0)
area = find(win, name='plan')
plan = host.plan
session = host.bridge.session
wait_until(lambda: area.property('fitted') and area.property('zoom') > 2, 30)


def at(x, y):
    p = area.screen(x, y)
    q = area.mapToScene(QPointF(p.x(), p.y()))
    return q.x(), q.y()


def buildings():
    return [dict(id=b.id, name=b.name, on=b.on, base=b.base, height=b.height, type=b.roof.type)
            for b in session.project.buildings]


host.shell.trigger('tool_building'); spin(0.4)
seen['tool'] = plan.tool
for x, y in ((10, 5), (16, 5), (16, 10)):
    native.click(*at(x, y), settle=150)
native.move(*at(10, 10)); spin(0.3)
native.click(*at(10, 10), settle=150)
native.click(*at(10, 5), settle=300)
spin(0.6)
seen['room'] = buildings()
seen['room_error'] = plan.error
native.key('esc'); spin(0.3)
native.click(*at(13, 7), settle=250)
seen['picked_room'] = list(plan.editor.selection)
spin(0.6)
seen['stands_on'] = (find(win, text='Poggia su') or find(win, text='Stands on')) is not None
seen['base_field'] = (find(win, text='Quota di base') or find(win, text='Base height')) is not None
native.click(*at(30, 15), settle=250)
seen['picked_shed'] = list(plan.editor.selection)
native.key('z', modifiers=('ctrl',)); spin(0.8)
seen['after_undo'] = buildings()

host.shell.trigger('tool_building'); spin(0.4)
for x, y in ((42, 2), (46, 2), (46, 8), (42, 8)):
    native.click(*at(x, y), settle=150)
native.click(*at(42, 2), settle=300)
spin(0.6)
seen['outside'] = buildings()
native.key('esc'); spin(0.3)

session.edit('saddles', lambda p: p.buildings[0].roof.__setattr__('type', 'saddles') or
             p.buildings[0].roof.saddles.update(dict(direction=90.0, band=4.0, tilt=10.0, channel=0.6, depth=0.15)))
spin(0.8)
seen['saddles'] = dict(type=session.project.buildings[0].roof.type, pitches=len(session.project.buildings[0].pitches()),
                       rings=len(plan.editor.rings()))
print(json.dumps(seen, default=str))
'''


def _project(folder: Path) -> Path:
    from meridiana import model
    p = model.Project(name='Prova solidi')
    p.site = model.Site(lat=45.52, lon=9.04, address='Rho (MI)')
    p.buildings.append(model.Building(id='b1', name='Capannone', footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                                      height=8.0))
    path = folder / 'solidi.meridiana'
    p.save(path)
    return path


@unittest.skipUnless(sys.platform == 'win32', 'Windows messages')
@unittest.skipIf(os.environ.get('MERIDIANA_NO_NATIVE'), 'switched off')
class Solids(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        folder = Path(cls.folder.name)
        ctl = folder / 'ctl'
        args = ['--ctl', str(ctl), '--project', str(_project(folder)), '--no-calc',
                '--desktop', 'meridiana-collaudo-solidi', '--timeout', '100']
        code, output = _run('start', *args, timeout=140)
        if code:
            raise unittest.SkipTest(f'no program: {output[-300:]}')
        script = folder / 'journey.py'
        script.write_text(JOURNEY, encoding='utf-8')
        try:
            code, output = _run('run', '--ctl', str(ctl), str(script), timeout=300)
            lines = [line for line in output.splitlines() if line.startswith('{')]
            if not lines:
                raise AssertionError(f'the journey said nothing: {output[-800:]}')
            cls.seen = json.loads(lines[-1])
        finally:
            _run('run', '--ctl', str(ctl), '--stop', timeout=30)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_drawn_on_the_roof_it_is_a_plant_room_standing_on_it(self):
        self.assertEqual(self.seen['tool'], 'building')
        self.assertEqual(self.seen['room_error'], '')
        room = self.seen['room']
        self.assertEqual(len(room), 2)
        self.assertEqual((room[1]['on'], room[1]['base'], room[1]['height']), ('b1', 8.0, 11.0))
        self.assertIn(room[1]['name'], ('Locale tecnico 1', 'Plant room 1'))

    def test_a_click_picks_the_room_first_and_its_properties_say_where_it_stands(self):
        self.assertEqual(self.seen['picked_room'][0], 'building')
        self.assertEqual(self.seen['picked_room'][1], self.seen['room'][1]['id'])
        self.assertTrue(self.seen['stands_on'])
        self.assertTrue(self.seen['base_field'])
        self.assertEqual(self.seen['picked_shed'], ['building', 'b1'])

    def test_ctrl_z_takes_it_back_and_outside_it_is_a_building(self):
        self.assertEqual(len(self.seen['after_undo']), 1)
        outside = self.seen['outside']
        self.assertEqual(len(outside), 2)
        self.assertEqual((outside[1]['on'], outside[1]['base'], outside[1]['height']), ('', 0.0, 6.0))

    def test_the_saddle_roof_has_its_bands_in_the_plan(self):
        self.assertEqual(self.seen['saddles']['type'], 'saddles')
        self.assertGreater(self.seen['saddles']['pitches'], 10)
        self.assertGreater(self.seen['saddles']['rings'], 10)


if __name__ == '__main__':
    unittest.main()
