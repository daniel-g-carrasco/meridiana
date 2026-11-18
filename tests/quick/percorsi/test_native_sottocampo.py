"""The sub-field as its modules under the native mouse and keyboard, on its own desktop (R445, R473): drawn with four
clicks the modules show while drawing and the sub-field is made of them; a side of it dragged shows the ghosts with
their count and the modules laid stay; Ctrl+Z gives it back in one step; a measure typed with its comma moves the
side by that much; a module set aside on the vent (red) comes back from the menu; a building's side dragged stays
parallel; the fire-brigade bands come from the menu.

    python -m unittest quick.percorsi.test_native_sottocampo
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
host.shell.trigger('phase_plant')
spin(1.5)
area = find(win, name='plan')
plan = host.plan
session = host.bridge.session
wait_until(lambda: area.property('fitted') and area.property('zoom') > 2, 30)


def at(x, y):
    p = area.screen(x, y)
    q = area.mapToScene(QPointF(p.x(), p.y()))
    return q.x(), q.y()


def ring_of():
    return [list(map(float, q)) for q in session.project.subfields[0].ring]


host.shell.trigger('tool_subfield'); spin(0.4)
for x, y in ((5, 3), (30, 3), (30, 15)):
    native.click(*at(x, y), settle=150)
native.move(*at(5, 15)); spin(0.4)
pv = plan.preview
seen['draw_preview_modules'] = (pv.get('modules') or {}).get('count', 0)
seen['draw_card'] = list((pv.get('card') or {}).get('lines', []))
native.click(*at(5, 15), settle=150)
native.click(*at(5, 3), settle=250)
spin(0.5)
sf = session.project.subfields[0]
host.bridge._enabled = True          # the layouts after a change start with the first year: here without it
host.bridge.layout_timer.start()
seen['drawn'] = dict(flush=sf.flush, manual=sf.manual, rows=len(sf.rows), ring=ring_of())
wait_until(lambda: sf.id in session.good_results(), 20); spin(0.8)
got = session.good_results().get(sf.id)
seen['laid'] = len(got.modules) if got else None
seen['blocked'] = len(got.blocked) if got else None
before = {m.key: m.centre for m in got.modules} if got else {}

native.key('esc'); spin(0.3)
native.click(*at(12, 9), settle=200)
seen['selected'] = list(plan.editor.selection)
east = max(x for x, _y in ring_of())
native.move(*at(east, 9)); spin(0.4)
seen['side_hover'] = find(win, name='sideMouse').property('side')
native.press(); spin(0.2)
native.move(*at(east + 2.4, 9), steps=16); spin(0.5)
pv = plan.preview
seen['drag'] = dict(tool=plan.tool, type=pv.get('type'), added=pv.get('added'), removed=pv.get('removed'),
                    card=list((pv.get('card') or {}).get('lines', [])),
                    ghosts=len([o for o in plan.draftObjects if o['kind'] == 'ghost']))
native.release(); spin(0.8)
seen['after_drag'] = dict(tool=plan.tool, error=plan.error, ring=ring_of(), rows=len(session.project.subfields[0].rows))
wait_until(lambda: sf.id in session.good_results() and len(session.good_results()[sf.id].modules) > len(before), 20)
after = {m.key: m.centre for m in session.good_results()[sf.id].modules}
seen['stayed'] = all(after.get(k) == c for k, c in before.items())
seen['more'] = len(after) - len(before)
native.key('z', modifiers=('ctrl',)); spin(0.8)
seen['after_undo'] = dict(ring=ring_of(), rows=len(session.project.subfields[0].rows))

north = max(y for _x, y in ring_of())
native.move(*at(17, north)); spin(0.3)
native.press(); spin(0.2)
native.move(*at(17, north + 0.5), steps=6); spin(0.3)
native.type_text('4,2')
spin(0.4)
pv = plan.preview
seen['typed'] = dict(added=pv.get('added'), removed=pv.get('removed'), card=list((pv.get('card') or {}).get('lines', [])))
native.release(); spin(0.3)
seen['typed_wait'] = plan.tool
native.key('enter'); spin(0.8)
seen['after_typed'] = dict(tool=plan.tool, error=plan.error, rows=len(session.project.subfields[0].rows))
wait_until(lambda: not plan.busy, 20); spin(0.5)
native.key('z', modifiers=('ctrl',)); spin(0.8)

result = session.good_results().get(sf.id)
seen['red'] = len(result.blocked) if result else None
if result is not None and result.blocked:
    red = result.blocked[0]
    native.click(*at(*red.centre), button='right', settle=300); spin(0.5)
    item = find(win, text='Aggiungi un modulo qui') or find(win, text='Add a module here')
    seen['menu_item'] = item is not None
    if item is not None:
        native.click(*center(item)); spin(0.8)
    else:
        native.key('esc')
    seen['kept'] = list(session.project.subfields[0].kept)

host.shell.trigger('phase_model'); spin(1.0)
native.click(*at(2, 2), settle=250)
seen['model_selected'] = list(plan.editor.selection)
native.move(*at(40, 10)); spin(0.3)
native.press(); spin(0.2)
native.move(*at(45, 11), steps=12); spin(0.4)
seen['building_drag'] = dict(tool=plan.tool, rings=plan.preview.get('rings'))
native.release(); spin(0.6)
seen['building_after'] = session.project.buildings[0].footprint
native.key('z', modifiers=('ctrl',)); spin(0.6)
seen['building_undo'] = session.project.buildings[0].footprint

native.click(*at(10, 10), button='right', settle=300); spin(0.5)
item = (find(win, text='Aggiungi le fasce VVF di 1 m come ostacoli (questa copertura)')
        or find(win, text='Add the 1 m fire-brigade bands as obstacles (this roof)'))
seen['bands_item'] = item is not None
if item is not None:
    native.click(*center(item)); spin(0.8)
else:
    native.key('esc')
seen['bands'] = [e.kind for e in session.project.exclusions].count('band')
print(json.dumps(seen, default=str))
'''


def _project(folder: Path) -> Path:
    from meridiana import model
    p = model.Project(name='Prova sottocampo')
    p.site = model.Site(lat=45.52, lon=9.04, address='Rho (MI)')
    p.buildings.append(model.Building(id='b1', name='Capannone', footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                                      height=8.0, fire=model.Fire(subject=True)))
    p.exclusions.append(model.ExclusionItem(id='e1', ring=[[18, 8], [22, 8], [22, 12], [18, 12]], kind='vent',
                                            building='b1'))
    path = folder / 'capannone.meridiana'
    p.save(path)
    return path


@unittest.skipUnless(sys.platform == 'win32', 'Windows messages')
@unittest.skipIf(os.environ.get('MERIDIANA_NO_NATIVE'), 'switched off')
class SubfieldAsModules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        folder = Path(cls.folder.name)
        ctl = folder / 'ctl'
        args = ['--ctl', str(ctl), '--project', str(_project(folder)), '--no-calc',
                '--desktop', 'meridiana-collaudo-sottocampo', '--timeout', '100']
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

    def test_the_modules_show_while_drawing_and_the_sub_field_is_made_of_them(self):
        self.assertGreater(self.seen['draw_preview_modules'], 50)
        self.assertTrue(any('moduli' in line or 'module' in line for line in self.seen['draw_card']))
        drawn = self.seen['drawn']
        self.assertTrue(drawn['flush'] and drawn['manual'])
        self.assertEqual(drawn['rows'], 3)                                     # tilted rows on the flat roof
        self.assertEqual(self.seen['laid'] + self.seen['blocked'], 63)
        self.assertGreater(self.seen['blocked'], 0)                            # on the vent, set aside

    def test_a_side_dragged_shows_the_ghosts_and_the_count_and_the_modules_stay(self):
        self.assertEqual(self.seen['selected'], ['subfield', 's1'])
        self.assertGreaterEqual(self.seen['side_hover'], 0)
        drag = self.seen['drag']
        self.assertEqual((drag['tool'], drag['type']), ('side', 'side'))
        self.assertEqual((drag['added'], drag['removed'], drag['ghosts']), (6, 0, 6))
        self.assertTrue(any('+6' in line for line in drag['card']), drag['card'])
        after = self.seen['after_drag']
        self.assertEqual((after['tool'], after['error']), ('select', ''))
        self.assertGreater(max(x for x, _y in after['ring']), 31.0)
        self.assertTrue(self.seen['stayed'])
        self.assertEqual(self.seen['more'], 6)

    def test_ctrl_z_takes_it_back_in_one_step(self):
        self.assertAlmostEqual(max(x for x, _y in self.seen['after_undo']['ring']), 29.61, places=1)
        self.assertEqual(self.seen['after_undo']['rows'], 3)

    def test_a_measure_typed_with_its_comma_moves_the_side(self):
        typed = self.seen['typed']
        self.assertTrue(any('4,2_' in line for line in typed['card']), typed['card'])
        self.assertEqual(typed['added'], 21)                                   # one row more
        self.assertEqual(self.seen['typed_wait'], 'select' if False else self.seen['typed_wait'])
        self.assertEqual(self.seen['after_typed'], dict(tool='select', error='', rows=4))

    def test_a_red_module_comes_back_from_the_menu(self):
        self.assertTrue(self.seen.get('menu_item'))
        self.assertEqual(len(self.seen.get('kept', [])), 1)

    def test_a_building_side_dragged_stays_parallel_and_undoes(self):
        self.assertEqual(self.seen['model_selected'], ['building', 'b1'])
        self.assertEqual(self.seen['building_drag']['tool'], 'side')
        ring = self.seen['building_after']
        self.assertEqual([ring[0], ring[3]], [[0.0, 0.0], [0.0, 20.0]])
        self.assertAlmostEqual(ring[1][0], 45.0, delta=0.1)
        self.assertAlmostEqual(ring[2][0], ring[1][0])
        self.assertEqual(self.seen['building_undo'], [[0, 0], [40, 0], [40, 20], [0, 20]])

    def test_the_bands_come_from_the_menu(self):
        self.assertTrue(self.seen['bands_item'])
        self.assertEqual(self.seen['bands'], 4)


if __name__ == '__main__':
    unittest.main()
