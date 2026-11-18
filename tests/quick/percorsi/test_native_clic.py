"""R529, R531, R532, R533 under the native mouse and keyboard, on a desktop of their own. In Plant a hundred clicks on
modules picked at random (inside ones and those along the outline of the sub-field, whose sides and corners can be
dragged), each with the hand moving 0 to 4 physical pixels between press and release, each select their module; so
do the clicks after the Inverter section was opened and closed. Modules swept with a window go with Del in one step
of Undo, and with the menu, whose entries speak of the modules selected and keep the sub-field in a submenu.

Before: 59 of 100 (18 gave the row, 16 went to the side being dragged, 5 to its corners), and 0 of 100 after Inverter.

    python -m unittest quick.percorsi.test_native_clic
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
import json, math, random
from PySide6.QtCore import QPointF
from shapely.geometry import Polygon, Point

seen = {}
wait_until(lambda: host.plan is not None, 60)
host.shell.trigger('phase_plant')
spin(1.5)
area = find(win, name='plan')
plan = host.plan
session = host.bridge.session
actions = host.parts.controllers['plantActions']
ed = plan.editor
wait_until(lambda: area.property('fitted') and area.property('zoom') > 2, 30)


def at(x, y):
    p = area.screen(x, y)
    q = area.mapToScene(QPointF(p.x(), p.y()))
    return q.x(), q.y()


host.shell.trigger('tool_subfield'); spin(0.4)
for x, y in ((5, 3), (30, 3), (30, 15), (5, 15), (5, 3)):
    native.click(*at(x, y), settle=150)
spin(0.5)
sf = session.project.subfields[0]
host.bridge._enabled = True
host.bridge.layout_timer.start()
wait_until(lambda: sf.id in session.good_results(), 20); spin(0.8)
native.key('esc'); spin(0.2)
mods = list(session.good_results()[sf.id].modules)
ring = Polygon([tuple(map(float, q)) for q in sf.ring]).exterior
zoom, dpr = area.property('zoom'), native.dpr()
rng = random.Random(7)


def inside(m):
    c = m.corners
    a, b = rng.uniform(.1, .9), rng.uniform(.1, .9)
    return ((1-a)*(1-b)*c[0][0] + a*(1-b)*c[1][0] + a*b*c[2][0] + (1-a)*b*c[3][0],
            (1-a)*(1-b)*c[0][1] + a*(1-b)*c[1][1] + a*b*c[2][1] + (1-a)*b*c[3][1])


def clicks(n):
    rows, last = [], None
    for i in range(n):
        m = rng.choice([m for m in mods if m.key != last])     # the same module twice is the row, by design
        last = m.key
        calls = dict(plan.calls)
        x, y = inside(m)
        sx, sy = at(x, y)
        native.move(sx, sy, steps=6)
        native.press(); native.spin(30)
        j, turn = rng.uniform(0, 4)/dpr, rng.uniform(0, 6.283)
        native.jump(sx + j*math.cos(turn), sy + j*math.sin(turn)); native.spin(20)
        native.release(); native.spin(160)
        rows.append(dict(ok=tuple(ed.selected_module) == (sf.id, m.key), edge=Point(x, y).distance(ring)*zoom < 13,
                         sel=list(ed.selection), tool=plan.tool, i=i, want=m.key, got=list(ed.selected_module),
                         used={k: v - calls.get(k, 0) for k, v in plan.calls.items() if v != calls.get(k, 0)}))
        native.spin(rng.uniform(450, 650))
        if plan.tool != 'select':
            native.key('esc'); native.spin(100)
    return dict(ok=sum(r['ok'] for r in rows), of=n, edge=sum(r['edge'] for r in rows),
                edge_ok=sum(r['ok'] and r['edge'] for r in rows), fails=[r for r in rows if not r['ok']][:5])


seen['dpr'] = dpr
seen['plain'] = clicks(100)
actions.openSection('inverter'); spin(0.2); actions.toggleSection('inverter'); spin(0.3)
seen['after_inverter'] = clicks(20)

def removed():
    return len(session.project.subfields[0].removed)


def sweep_box():
    native.key('esc'); spin(0.1); native.key('esc'); spin(0.1)
    native.drag(*at(8, 13.5), *at(21, 7.5), steps=16); spin(0.3)
    return len(ed.swept)


actions.openSection('inverter'); spin(0.3)
seen['swept'] = sweep_box()
undo = session.undo.count()
native.key('delete'); spin(0.6)
seen['del'] = dict(removed=removed(), steps=session.undo.count() - undo, bar=plan.hint)
native.key('z', modifiers=('ctrl',)); spin(0.6)
seen['undo'] = removed()
actions.openSection('panels'); spin(0.3)
sweep_box()
picked = set(map(tuple, ed.swept))
m = next(m for m in mods if (sf.id, m.key) in picked)
native.click(*at(*m.centre), button='right', settle=400); spin(0.4)
seen['menu_many'] = [dict(c=i['command'], t=i['text'], m=i.get('menu', ''), h=bool(i.get('header')))
                     for i in plan.contextItems if i.get('header') or not i['separator']]
grab('menu-many.png')
item = find(win, name='planContext-remove_selected')
seen['menu_item'] = item is not None
if item is not None:
    native.click(*center(item)); spin(0.8)
else:
    native.key('esc')
seen['menu_removed'] = removed()
seen['subfields'] = len(session.project.subfields)
native.key('z', modifiers=('ctrl',)); spin(0.6)
native.key('esc'); spin(0.1); native.key('esc'); spin(0.1)
one = mods[7]
native.click(*at(*one.centre), settle=200); spin(0.3)
native.click(*at(*one.centre), button='right', settle=400); spin(0.4)
seen['menu_one'] = [dict(c=i['command'], m=i.get('menu', ''), h=bool(i.get('header')))
                    for i in plan.contextItems if i.get('header') or not i['separator']]
native.key('esc'); spin(0.2)
native.key('delete'); spin(0.6)
seen['one_removed'] = removed()
seen['one_bar'] = plan.hint
# R529, the rule of the selection with the real mouse and keys: after a window a plain click starts again, Shift+click
# adds, Ctrl+click adds or takes away, a plain window starts again, Ctrl+window takes away
native.key('z', modifiers=('ctrl',)); spin(0.6)
seen['rule_window'] = sweep_box()
inside = [m for m in mods if (sf.id, m.key) in set(map(tuple, ed.swept))]
outside = [m for m in mods if (sf.id, m.key) not in set(map(tuple, ed.swept))]
a, b, c = inside[0], outside[0], outside[1]
native.click(*at(*a.centre), settle=300); spin(0.3)
seen['rule_plain'] = dict(swept=len(ed.swept), module=list(ed.selected_module), want=a.key)
native.click(*at(*b.centre), settle=300, modifiers=('shift',)); spin(0.3)
native.click(*at(*c.centre), settle=300, modifiers=('shift',)); spin(0.3)
seen['rule_shift'] = sorted(k for _s, k in map(tuple, ed.swept))
native.click(*at(*b.centre), settle=300, modifiers=('ctrl',)); spin(0.3)
seen['rule_ctrl_off'] = sorted(k for _s, k in map(tuple, ed.swept))
native.click(*at(*b.centre), settle=300, modifiers=('ctrl',)); spin(0.3)
seen['rule_ctrl_on'] = sorted(k for _s, k in map(tuple, ed.swept))
seen['rule_bar'] = plan.hint
seen['rule_abc'] = [a.key, b.key, c.key]
print(json.dumps(seen, default=str))
'''


@unittest.skipUnless(sys.platform == 'win32', 'Windows messages')
@unittest.skipIf(os.environ.get('MERIDIANA_NO_NATIVE'), 'switched off')
class ModuleClicks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        folder = Path(cls.folder.name)
        ctl = folder / 'ctl'
        args = ['--ctl', str(ctl), '--project', str(_project(folder)), '--no-calc',
                '--desktop', 'meridiana-collaudo-clic', '--timeout', '100']
        code, output = _run('start', *args, timeout=140)
        if code:
            raise unittest.SkipTest(f'no program: {output[-300:]}')
        script = folder / 'journey.py'
        script.write_text(JOURNEY, encoding='utf-8')
        try:
            code, output = _run('run', '--ctl', str(ctl), str(script), timeout=600)
            lines = [line for line in output.splitlines() if line.startswith('{')]
            if not lines:
                raise AssertionError(f'the journey said nothing: {output[-800:]}')
            cls.seen = json.loads(lines[-1])
        finally:
            _run('run', '--ctl', str(ctl), '--stop', timeout=30)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_the_rule_of_the_selection_with_the_real_mouse_and_keys(self):
        # R529 (Daniel 07/11/2026 sera): Shift adds, Ctrl adds or takes away, a plain click starts again
        s = self.seen
        self.assertGreater(s['rule_window'], 3)
        self.assertEqual(s['rule_plain']['swept'], 0, s['rule_plain'])          # after a window: starts again
        self.assertEqual(s['rule_plain']['module'][1], s['rule_plain']['want'])
        a, b, c = s['rule_abc']
        self.assertEqual(s['rule_shift'], sorted([a, b, c]))                 # Shift adds, from the one chosen
        self.assertEqual(s['rule_ctrl_off'], sorted([a, c]))                 # Ctrl takes away what is in
        self.assertEqual(s['rule_ctrl_on'], sorted([a, b, c]))               # and adds what is not
        self.assertIn('Maiusc: aggiunge', s['rule_bar'])
        self.assertIn('Ctrl: aggiunge o toglie', s['rule_bar'])

    def test_a_hundred_clicks_select_a_hundred_modules_also_along_the_outline(self):
        plain = self.seen['plain']
        self.assertEqual(plain['ok'], 100, plain)
        self.assertGreater(plain['edge'], 20)              # the modules on the sides and corners were tried
        self.assertEqual(plain['edge_ok'], plain['edge'])

    def test_after_inverter_opened_and_closed_the_clicks_still_select_modules(self):
        self.assertEqual(self.seen['after_inverter']['ok'], 20, self.seen['after_inverter'])

    def test_del_takes_out_the_modules_swept_in_one_step_and_says_how_many(self):
        n = self.seen['swept']
        self.assertGreater(n, 3)
        self.assertEqual(self.seen['del']['removed'], n)       # with Inverter open (R531)
        self.assertEqual(self.seen['del']['steps'], 1)
        self.assertIn(str(n), self.seen['del']['bar'])
        self.assertEqual(self.seen['undo'], 0)

    def test_the_menu_on_many_modules_speaks_of_them_and_takes_them_out(self):
        menu = self.seen['menu_many']
        top = [e['c'] for e in menu if not e['m'] and not e['h']]
        self.assertIn('remove_selected', top)
        for single in ('remove', 'select_row', 'remove_row', 'append_row', 'explode_row', 'add_module'):
            self.assertNotIn(single, top)
        self.assertTrue(menu[0]['h'] and str(self.seen['swept']) in menu[0]['t'])
        deleting = [e for e in menu if e['c'] in ('remove', 'delete_subfield')]
        self.assertEqual([(e['c'], bool(e['m'])) for e in deleting], [('delete_subfield', True)])
        self.assertTrue(self.seen['menu_item'])
        self.assertEqual(self.seen['menu_removed'], self.seen['swept'])         # R532
        self.assertEqual(self.seen['subfields'], 1)

    def test_one_module_has_its_menu_and_goes_with_del(self):
        menu = self.seen['menu_one']
        self.assertEqual([e['c'] for e in menu if not e['m'] and not e['h']][:3], ['properties', 'frame', 'remove'])
        self.assertEqual(sum(e['h'] for e in menu), 2)
        self.assertEqual(self.seen['one_removed'], 1)
        self.assertIn('modul', self.seen['one_bar'].lower())
