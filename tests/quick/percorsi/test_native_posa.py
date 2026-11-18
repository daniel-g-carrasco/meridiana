"""The defaults of the next sub-fields under the native mouse, on its own desktop (R523): with nothing selected the
Plant's Panels says «Predefinite per i prossimi sottocampi»; the fire bands switched on with a click there, landscape
modules and a gap chosen, a sub-field drawn with four clicks shows and is made of modules laid that way; the sub-field
drawn before does not change; Ctrl+Z takes back the sub-field and its bands in one step; saved and opened again, the
defaults are there.

    python -m unittest quick.percorsi.test_native_posa
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
from pathlib import Path
from PySide6.QtCore import QPointF
from meridiana import model

seen = {}
wait_until(lambda: host.plan is not None, 60)
host.shell.trigger('phase_plant')
spin(1.5)
area = find(win, name='plan')
plan = host.plan
session = host.bridge.session
panels = host.parts.controllers['plantPanels']
actions = host.parts.controllers['plantActions']
wait_until(lambda: area.property('fitted') and area.property('zoom') > 2, 30)


def at(x, y):
    p = area.screen(x, y)
    q = area.mapToScene(QPointF(p.x(), p.y()))
    return q.x(), q.y()


session.select('site', '')
actions.openSection('panels'); spin(1.0)
side = find(win, name='plant-inspector')
heading = find(win, name='plant-panels-heading', within=side)
seen['heading'] = heading.property('text') if heading is not None else None
seen['kind'] = panels.kind
before = json.dumps(model._subfield_json(session.project.subfields[0]), sort_keys=True)

check = find(win, name='editor:automatic', within=side)      # the azimuth's «Automatico», in view at the top
seen['check_found'] = check is not None
if check is not None:
    native.click(*center(check)); spin(0.6)
seen['after_click'] = dict(session.project.layout_defaults)
panels.commit('fire_bands', True)
panels.commit('params.portrait', False)
panels.commit('params.gap', '0,05')
seen['defaults'] = session.project.layout_defaults

host.shell.trigger('tool_subfield'); spin(0.4)
for x, y in ((16, 3), (36, 3), (36, 11)):
    native.click(*at(x, y), settle=150)
native.move(*at(16, 11)); spin(0.4)
seen['preview'] = (plan.preview.get('modules') or {}).get('count', 0)
seen['same_project'] = plan.drawing.project is session.project
seen['preview_ring'] = [list(map(float, q)) for q in (plan.drawing.points or [])] + [list(map(float, plan.drawing.pointer or []))]
native.click(*at(16, 11), settle=150)
native.click(*at(16, 3), settle=250)
spin(0.6)
drawn = session.project.subfields[-1]
seen['count'] = len(session.project.subfields)
seen['ring'] = drawn.ring
seen['drawn'] = dict(flush=drawn.flush, params=drawn.params, module=drawn.module, rows=len(drawn.rows),
                     places=[len(r['places']) for r in drawn.rows])
draft = session.project.new_subfield('_d', '', seen['preview_ring'], 'b1', None)     # the outline drawn, snapped
from meridiana import manual
seen['expected'] = len(manual.corners(session.project, draft, manual.grid(session.project, draft)))
seen['bands'] = [e.kind for e in session.project.exclusions].count('band')
seen['first_same'] = json.dumps(model._subfield_json(session.project.subfields[0]), sort_keys=True) == before

native.key('esc'); spin(0.3)
native.key('z', modifiers=('ctrl',)); spin(0.8)
seen['after_undo'] = dict(count=len(session.project.subfields),
                          bands=[e.kind for e in session.project.exclusions].count('band'),
                          defaults=session.project.layout_defaults)
native.key('y', modifiers=('ctrl',)); spin(0.8)
import shutil, tempfile
where = Path(tempfile.mkdtemp(prefix='meridiana-posa-'))
target = where / 'riaperto.meridiana'
session.save(target)
again = model.Project.load(target)[0]
shutil.rmtree(where, ignore_errors=True)
seen['reopened'] = dict(defaults=again.layout_defaults, count=len(again.subfields),
                        params=again.subfields[-1].params)
print(json.dumps(seen, default=str))
'''


def _project(folder: Path) -> Path:
    from meridiana import manual, model
    p = model.Project(name='Prova posa')
    p.site = model.Site(lat=45.52, lon=9.04, address='Rho (MI)')
    p.buildings.append(model.Building(id='b1', name='Capannone', footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                                      height=8.0, fire=model.Fire(subject=True)))
    sf = p.new_subfield('s1', 'Esistente', [[2, 13], [14, 13], [14, 18], [2, 18]], 'b1', None)
    p.add_subfield(sf)
    manual.make_flush(p, sf)
    path = folder / 'capannone.meridiana'
    p.save(path)
    return path


@unittest.skipUnless(sys.platform == 'win32', 'Windows messages')
@unittest.skipIf(os.environ.get('MERIDIANA_NO_NATIVE'), 'switched off')
class DefaultsBeforeDrawing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        folder = Path(cls.folder.name)
        ctl = folder / 'ctl'
        args = ['--ctl', str(ctl), '--project', str(_project(folder)), '--no-calc',
                '--desktop', 'meridiana-collaudo-posa', '--timeout', '100']
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

    def test_with_nothing_selected_the_panel_says_it_changes_the_defaults(self):
        self.assertEqual(self.seen['kind'], 'defaults')
        self.assertIn(self.seen['heading'], ('Predefinite per i prossimi sottocampi', 'Defaults for the next sub-fields'))
        self.assertTrue(self.seen['check_found'])
        self.assertEqual(self.seen['after_click'], {'params': {'azimuth': 0.0}})        # the click reached the form
        self.assertEqual(self.seen['defaults'], {'fire_bands': True, 'params': {'azimuth': 0.0, 'portrait': False,
                                                                                'gap': 0.05}})

    def test_the_sub_field_drawn_is_laid_with_the_defaults(self):
        drawn = self.seen['drawn']
        self.assertTrue(drawn['flush'])
        self.assertEqual(drawn['params'], {'mounting': 'tilted_anchored', 'alignment': 'aligned', 'azimuth': 0.0,
                                           'portrait': False, 'gap': 0.05})
        self.assertEqual(self.seen['preview'], self.seen['expected'])
        self.assertEqual(sum(drawn['places']), self.seen['expected'])
        self.assertGreater(self.seen['expected'], 0)
        self.assertEqual(self.seen['bands'], 4)

    def test_the_sub_field_drawn_before_does_not_change(self):
        self.assertTrue(self.seen['first_same'])

    def test_ctrl_z_takes_back_the_sub_field_and_its_bands_and_keeps_the_defaults(self):
        undone = self.seen['after_undo']
        self.assertEqual((undone['count'], undone['bands']), (1, 0))
        self.assertEqual(undone['defaults'], self.seen['defaults'])

    def test_saved_and_opened_the_defaults_are_there(self):
        again = self.seen['reopened']
        self.assertEqual(again['defaults'], self.seen['defaults'])
        self.assertEqual(again['count'], 2)
        self.assertEqual(again['params'], self.seen['drawn']['params'])


if __name__ == '__main__':
    unittest.main()
