"""R419: the summary in the Plant's bar follows the gestures, says what the plant says, and shows the selection without
moving. Only the words and counts of the backend: the QML computes nothing."""
import statistics
import os
import tempfile
import time
import unittest
from pathlib import Path

import _setup
from meridiana import i18n, jobs
from meridiana.quick.app import QuickWindow, create_app
from meridiana.quick.backend import plant_summary as summary
from quick import confini
from quick.gestures import item, pump, wait_for
from quick.parity.differential import connected_fixture

setUpModule = _setup.keep_global_state

# Offscreen, Qt Quick's threaded render loop dies with an access violation while a job imports pvlib or fits a module
# (8 runs out of 8; 0 out of 8 with the basic loop; real windows not seen to: docs/quick/r14-impianto-esito.md).
if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')


def values(columns):
    return {r['label']: r['value'] for c in columns for r in c['rows']}


class Bar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(i18n.setup, i18n.language())      # the next module's language is its own
        cls.app = _setup.qt_or_skip()
        create_app()
        i18n.setup('it')
        project = connected_fixture()
        results, keys, _laid = jobs.layout_of(project)
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(project, Path(cls.folder.name), real_views=True, theme={'theme': 'light'})
        cls.session = cls.host.bridge.session
        cls.host.bridge.accept_layout(cls.session.generation, results, keys)
        cls.win = cls.host.window
        cls.win.resize(1600, 960)
        cls.win.show()
        controllers = cls.host.parts.controllers
        cls.plant, cls.actions, cls.summary = controllers['plant'], controllers['plantActions'], controllers['plantSummary']
        cls.host.shell.trigger('phase_plant')
        wait_for(lambda: not cls.plant.busy and cls.plant.units, 60)
        pump(100)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def setUp(self):
        self.host.plan.editor.swept = []
        self.plant.selectString(-1)
        self.plant.clear_choice()
        self.session.select('', '')
        self.win.resize(1600, 960)
        pump(700)       # the bar's mode follows the window's size after a short wait

    def test_the_totals_are_the_plants_figures(self):
        said = values(self.summary.totals)
        state = self.plant.state
        laid = sum(len(g.modules) for g in self.session.good_results().values())
        connected = sum(len(s.modules) for s in state.strings)
        self.assertTrue(said['Moduli posati'].startswith(i18n.number(laid, 0)))
        self.assertIn(i18n.number(state.p_stc_w / 1000, 1), said['Moduli posati'])
        self.assertTrue(said['Collegati'].startswith(i18n.number(connected, 0)))
        self.assertTrue(said['Scollegati'].startswith(i18n.number(len(state.left), 0)))
        self.assertEqual(said['Stringhe'], i18n.number(len(state.strings), 0))
        used = sum(1 for slot in state.inputs.values() if slot.strings)
        self.assertIn(f'{used} usati', said['Ingressi'])
        self.assertIn('AC', said['Potenza'])

    def test_it_follows_a_string_deleted_and_taken_back(self):
        before = values(self.summary.totals)
        self.plant.deleteString(0)
        wait_for(lambda: values(self.summary.totals)['Stringhe'] != before['Stringhe'], 20)
        after = values(self.summary.totals)
        self.assertNotEqual(after['Collegati'], before['Collegati'])
        self.assertEqual(after['Moduli posati'], before['Moduli posati'])
        self.plant.undo()
        wait_for(lambda: values(self.summary.totals) == before, 20)

    def test_it_follows_a_module_taken_off_the_layout(self):
        before = values(self.summary.totals)['Moduli posati']
        sfid, result = next(iter(self.session.good_results().items()))
        key = result.modules[-1].key
        self.session.edit('togli', lambda p: next(s for s in p.subfields if s.id == sfid).removed.append(key))
        results, keys, _laid = jobs.layout_of(self.session.project)     # what the layout's job brings back
        self.host.bridge.accept_layout(self.session.generation, results, keys)
        wait_for(lambda: values(self.summary.totals)['Moduli posati'] != before, 10)
        self.plant.undo()
        results, keys, _laid = jobs.layout_of(self.session.project)
        self.host.bridge.accept_layout(self.session.generation, results, keys)
        wait_for(lambda: values(self.summary.totals)['Moduli posati'] == before, 10)

    def test_r419_the_selection_shows_apart_and_nothing_moves(self):
        box = item(self.win, 'plant-summary')
        where = (box.x(), box.y(), box.width(), box.height())
        self.assertEqual(self.summary.selection, {})
        self.plant.selectString(0)
        pump(80)
        self.assertEqual(self.summary.selection['title'], f"Stringa {self.plant.strings[0]['label']}")
        self.plant.selectString(-1)
        self.plant.selectUnit(self.plant.units[0]['number'])
        pump(80)
        self.assertEqual(self.summary.selection['title'], self.plant.units[0]['label'])
        self.plant.selectInput(self.plant.units[0]['number'], 1)
        pump(80)
        self.assertEqual(self.summary.selection['title'], self.plant.inputs[0]['place'])
        self.plant.clear_choice()
        pump(80)
        self.assertEqual(self.summary.selection, {})
        keys = [(sfid, m.key) for sfid, r in self.session.good_results().items() for m in r.modules][:3]
        self.host.plan.editor.swept = keys
        self.host.plan.overlayChanged.emit()
        pump(80)
        self.assertEqual(values([self.summary.selection])['Moduli'].split(' ')[0], '3')
        self.assertEqual((box.x(), box.y(), box.width(), box.height()), where)

    def test_r181_the_string_being_drawn_shows_in_the_selections_place(self):
        unit = self.plant.units[0]['number']
        self.plant.draw(unit, 1, -1)
        pump(200)
        self.assertIn(f'{unit}.1', self.summary.selection['title'])
        self.host.plan.editor.draft = self.host.plan.editor.draft_target = None
        self.host.plan._overlays()
        pump(120)

    def test_r419_thousands_of_modules_selected_cost_no_turn(self):
        keys = [(sfid, f'{i}') for sfid in self.session.good_results() for i in range(8000)]
        connected = summary.Connected(self.plant.state, self.session.project)
        times = []
        for _i in range(5):
            start = time.perf_counter()
            column = summary.of_modules('x', keys, connected)
            times.append(time.perf_counter() - start)
        self.assertEqual(column['rows'][0]['value'].split(' ')[0], i18n.number(len(keys), 0))
        self.assertLess(statistics.median(times), .030, times)

    def test_r419_it_stays_in_bounds_and_moves_above_the_plan_when_the_bar_has_no_room(self):
        trailing = item(self.win, 'phaseTrailing')
        self.assertTrue(trailing.isVisible())
        self.assertEqual([str(f) for f in confini.audit(self.win) if 'plant-s' in f.where or 'info-' in f.where], [])
        seen = set()
        for size, text in (((1000, 640), 'medium'), ((800, 560), 'medium'), ((800, 560), 'large')):
            self.host.theme.configure({'textSize': text})
            self.addCleanup(self.host.theme.configure, {'textSize': 'medium'})
            self.win.resize(*size)
            pump(800)
            above = item(self.win, 'viewsTrailing')
            self.assertNotEqual(trailing.isVisible(), above.property('active'), (size, text))
            seen.add(above.property('active'))
            self.plant.selectString(0)
            pump(150)
            self.assertEqual([str(f) for f in confini.audit(self.win) if 'plant-s' in f.where or 'info-' in f.where], [], size)
            self.plant.selectString(-1)
        self.assertIn(True, seen, 'at 800 wide there is no room in the bar')


class Optimizers(unittest.TestCase):
    """R424: on a plant with optimizers the string runs from unit to unit, a square for each, thin cables to the modules."""

    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(i18n.setup, i18n.language())      # the next module's language is its own
        cls.app = _setup.qt_or_skip()
        create_app()
        i18n.setup('it')
        from meridiana import catalog
        from meridiana.energy import plant as core
        record = next(r for r in catalog.search('inverters', manufacturer='SolarEdge', limit=None) if r['model'] == 'SE50K')
        project = connected_fixture()
        results, keys, _laid = jobs.layout_of(project)
        refs = [f'{sfid}/{m.key}' for sfid, r in results.items() for m in r.modules]
        cls.pairs = refs[:40]
        project.energy['inverters'] = [dict(record=record, count=1, name='')]
        project.energy['strings'] = core.touched(project.energy.get('strings'), [dict(inverter=1, mppt=1, modules=cls.pairs)])
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(project, Path(cls.folder.name), real_views=True, theme={'theme': 'light'})
        cls.host.bridge.accept_layout(cls.host.bridge.session.generation, results, keys)
        cls.win = cls.host.window
        cls.win.resize(1600, 960)
        cls.win.show()
        cls.plant = cls.host.parts.controllers['plant']
        cls.host.shell.trigger('phase_plant')
        wait_for(lambda: not cls.plant.busy and cls.plant.strings, 60)
        pump(200)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def batches(self):
        return self.host.plan.optimizerPaths

    def test_a_square_for_each_unit_and_a_cable_for_each_module_in_few_native_paths(self):
        unit = self.plant.units[0]
        per = self.host.plan.editor.string_optimizers[unit['number']]
        self.assertEqual(per, unit['per'])
        squares = [b for b in self.batches() if b['fill'] != 'transparent']
        cables = [b for b in self.batches() if b['fill'] == 'transparent']
        self.assertEqual(sum(b['path'].count('Z') for b in squares), 40 // per)
        self.assertEqual(sum(b['path'].count('M') for b in cables), 40)
        self.assertLessEqual(len(self.batches()), 4)
        self.assertTrue(item(self.win, 'optimizerLegend').isVisible())

    def test_the_string_runs_through_the_units_not_the_modules(self):
        lines = [w for w in self.host.plan.wires if w['kind'] == 'string_line']
        self.assertEqual(len(lines), 1)
        self.assertEqual(len(lines[0]['points']), 40 // self.plant.units[0]['per'])

    def test_a_pair_of_one_module_stands_off_the_module_with_its_cable(self):
        from meridiana import string_paths
        import numpy as np
        quad = np.array([[[0, 0], [2, 0], [2, 1], [0, 1]], [[2, 0], [4, 0], [4, 1], [2, 1]]], dtype=float)
        (alone, ) = string_paths.optimizer_units(quad, [[0]])
        self.assertNotEqual((alone[0], alone[1]), (1.0, .5))
        (pair, ) = string_paths.optimizer_units(quad, [[0, 1]])
        self.assertEqual((pair[0], pair[1]), (2.0, .5))
        self.assertAlmostEqual(pair[4], 1 / 3)

    def test_zoomed_out_the_line_alone(self):
        plan = self.host.plan
        before = plan._mpp
        self.addCleanup(setattr, plan, '_mpp', before)
        self.addCleanup(plan._overlays)
        plan._mpp = 50.0
        plan._overlays()
        self.assertEqual(self.batches(), [])
        self.assertTrue([w for w in plan.wires if w['kind'] == 'string_line'])

    def test_r425_the_words_of_a_module_say_its_optimizer(self):
        sfid, key = self.pairs[2].split('/', 1)
        words = self.host.plan.moduleTip(sfid, key)
        self.assertIn('Modulo 3 di 40', words)
        self.assertIn('ottimizzatore', words)


if __name__ == '__main__':
    unittest.main()
