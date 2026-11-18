"""The defects of 05-06/11/2026 under the native mouse and keyboard, on a desktop of their own (branch r17-difetti).

- The zoom in Impianto: 18 notches over the plan and a click, and the program is still there (offscreen it crashed
  after about ten: Qt Quick's software renderer with the threaded loop, quick.test_render_loop).
- A click on a string's name label reaches the module under it (the label took it and chose its string).
- R410: C and two clicks inside a building drawn over another: the ridge goes to it, where it was drawn.

    python -m unittest quick.percorsi.test_native_r17
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from quick.percorsi.test_native import ROOT, _run

JOURNEY = r'''
import json
from PySide6.QtCore import QMetaObject, QPointF, Q_ARG, Q_RETURN_ARG, Qt
from meridiana import jobs

seen = {}
laid, laid_keys, _unused = jobs.layout_of(host.bridge.session.project, host.bridge.session.known_layouts())
host.bridge.accept_layout(host.bridge.session.generation, laid, laid_keys)
spin(1.0)
session = host.bridge.session
editor = host.plan.editor
area = find(win, name='plan')


def call(name, *args):
    value = QMetaObject.invokeMethod(area, name, Qt.DirectConnection, Q_RETURN_ARG('QVariant'),
                                     *[Q_ARG('QVariant', a) for a in args])
    return value if isinstance(value, QPointF) else QPointF(value.x(), value.y())


# R410 first, in Modellazione: a building drawn over the capannone, then C and two clicks inside it.
drawn_before = len(session.project.buildings)
native.click(*center(find(win, name='tool_tool_building'))); spin(0.2)
for at in [(600, 480), (790, 480), (790, 600), (600, 600)]:
    native.click(*at, steps=4, settle=60)
native.key('enter'); spin(0.5); native.key('esc'); spin(0.2); native.key('esc'); spin(0.2)
new = session.project.buildings[-1] if len(session.project.buildings) > drawn_before else None
seen['drawn'] = new is not None
if new is not None:
    others = {b.id: b.roof.type for b in session.project.buildings if b.id != new.id}
    native.key('c'); spin(0.2)
    seen['tool_after_c'] = host.plan.property('tool')
    native.click(610, 510, steps=4, settle=60); native.click(780, 510, steps=4, settle=60)
    spin(0.5)
    seen['ridge_selection'] = list(session.selection)
    native.key('esc'); spin(0.2); native.key('esc'); spin(0.2)
    b = session.project.building(new.id)
    tops = [q for f in b.roof.free_pitches for q, z in zip(f['ring'], f.get('z') or []) if z == max(f.get('z') or [0])]
    low, high = min(p[1] for p in b.footprint), max(p[1] for p in b.footprint)
    seen['ridge_type'] = b.roof.type
    seen['ridge_share'] = None if not tops else round((tops[0][1] - low)/(high - low), 2)
    seen['ridge_pitches'] = len(b.pitches())
    seen['others_kept'] = others == {x.id: x.roof.type for x in session.project.buildings if x.id != new.id}
    seen['new_id'] = new.id
    native.key('z', ('ctrl',)); spin(0.4)
    native.key('z', ('ctrl',)); spin(0.4)

# Impianto: the strings, a name label over a module, then the zoom.
plant = host.engine.rootContext().contextProperty('plantBackend')
host.shell.trigger('phase_plant')
wait_until(lambda: len(plant.strings) > 10 and not plant.busy, 90)
spin(1.0)
host.plan.chooseString(0); spin(0.5)
label = next((i for i in items(win) if i.objectName() == 'stringLabel-name-0' and i.isVisible()), None)
seen['label'] = label is not None
if label is not None:
    at = label.mapToScene(QPointF(label.width()/2, label.height()/2))
    local = area.mapFromScene(at)
    w = call('world', local.x(), local.y())
    seen['under_label'] = list(editor.pick((w.x(), w.y())))
    key = '/'.join(seen['under_label'][1:])
    seen['run_of_module'] = next((n for n, run in enumerate(editor.runs()) if key in (run.get('modules') or [])), -1)
    native.move(1100, 300); spin(0.1)
    native.click(at.x(), at.y(), steps=4, settle=120); spin(0.4)
    seen['label_click_selection'] = list(session.selection)
    seen['label_click_module'] = list(editor.selected_module)
    seen['label_after_click'] = [i.objectName() for i in items(win) if i.objectName().startswith('stringLabel-name') and i.isVisible()]
    seen['plan_tool'] = host.plan.property('tool')
    seen['chosen_string'] = editor.chosen_string
    seen['grabber'] = str(win.mouseGrabberItem().objectName()) if win.mouseGrabberItem() else ''
    seen['label_at'] = [round(at.x()), round(at.y())]
    native.key('esc'); spin(0.3)

middle = area.mapToScene(QPointF(area.width()*.5, area.height()*.5))
host.plan.command('fit') if hasattr(host.plan, 'command') else None
spin(0.4)
for _ in range(18):
    native.wheel(middle.x(), middle.y(), 1)
seen['zoom'] = round(area.property('zoom'), 2)
native.click(middle.x(), middle.y(), steps=3, settle=120); spin(2.0)
for _ in range(18):
    native.wheel(middle.x(), middle.y(), -1)
spin(1.0)
seen['alive'] = True
print(json.dumps(seen, default=str))
'''


@unittest.skipUnless(sys.platform == 'win32', 'Windows messages')
@unittest.skipIf(os.environ.get('MERIDIANA_NO_NATIVE'), 'switched off')
class Defects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        ctl = Path(cls.folder.name)/'ctl'
        code, output = _run('start', '--engine', 'quick', '--ctl', str(ctl), '--desktop', 'meridiana-collaudo-r17',
                            '--timeout', '120', '--no-calc', timeout=150)
        if code:
            raise unittest.SkipTest(f'no program: {output[-300:]}')
        script = Path(cls.folder.name)/'journey.py'
        script.write_text(JOURNEY, encoding='utf-8')
        try:
            code, output = _run('run', '--ctl', str(ctl), str(script), timeout=280)
            lines = [line for line in output.splitlines() if line.startswith('{')]
            if not lines:
                raise AssertionError(f'the journey said nothing (a crash?): {output[-800:]}')
            cls.seen = json.loads(lines[-1])
        finally:
            _run('run', '--ctl', str(ctl), '--stop', timeout=30)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_zoom_in_impianto_and_a_click_leave_the_program_alive(self):
        self.assertTrue(self.seen.get('alive'))
        self.assertGreater(self.seen['zoom'], 20)

    def test_a_click_on_a_string_label_selects_the_module_under_it(self):
        self.assertTrue(self.seen['label'])
        # In Impianto a click on a module chooses its string (a module in no string is selected): the string of the
        # module under the label, not the label's own (string 0), which the label chose when it took the click.
        under = self.seen['under_label']
        self.assertEqual(under[0], 'module', under)
        if self.seen['run_of_module'] >= 0:
            self.assertNotEqual(self.seen['run_of_module'], 0, 'the proof needs a module of another string')
            self.assertEqual(self.seen['chosen_string'], self.seen['run_of_module'], self.seen)
        else:
            self.assertEqual(self.seen['label_click_module'], under[1:], self.seen)

    def test_r410_the_ridge_goes_to_the_building_it_is_drawn_in(self):
        self.assertTrue(self.seen['drawn'])
        self.assertEqual(self.seen['tool_after_c'], 'ridge')
        self.assertEqual(self.seen['ridge_selection'], ['building', self.seen['new_id']])
        self.assertTrue(self.seen['others_kept'])
        self.assertEqual(self.seen['ridge_type'], 'free')
        self.assertEqual(self.seen['ridge_pitches'], 2)
        # Clicked a quarter from the far side; the share is read to two decimals (0.72 is within the 0.03).
        self.assertLessEqual(abs(round(self.seen['ridge_share'] - .75, 2)), .03, self.seen)


if __name__ == '__main__':
    assert ROOT.exists()
    unittest.main()
