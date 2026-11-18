"""Real session edits, immutable workers and electrical observations."""
import copy
import time
import threading
import unittest
from unittest.mock import patch

import _setup  # noqa: F401  isolate the user's profile before loading Qt
from _fixtures import capannone, inverter_record
from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication

from meridiana import jobs
from meridiana.session import ProjectSession
from meridiana.energy import plant
from meridiana.quick.backend.plant import PlantBackend


class PlantBackendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.project = capannone()
        cls.results, cls.keys, _ = jobs.layout_of(cls.project)

    def setUp(self):
        self.session = ProjectSession(copy.deepcopy(self.project))
        self.session.results, self.session.layout_keys = self.results, self.keys
        self.backend = PlantBackend(self.session)
        self.addCleanup(self.backend.close)
        self.wait()

    def wait(self):
        until = time.monotonic() + 30
        while self.backend.busy and time.monotonic() < until:
            self.app.processEvents()
            time.sleep(.005)
        self.app.processEvents()
        self.assertFalse(self.backend.busy, self.backend.message)

    def wired(self):
        self.backend.addInverter(inverter_record())
        self.wait()
        keys = [f's1/{m.key}' for m in self.results['s1'].modules][:20]
        self.backend.commitString(1, 1, keys, -1)
        self.wait()
        return keys

    def test_r118_add_never_proposes_and_same_model_increments(self):
        self.backend.addInverter(inverter_record())
        self.backend.addInverter(inverter_record())
        self.wait()
        self.assertEqual(self.session.project.energy['inverters'][0]['count'], 2)
        self.assertEqual(self.backend.runs(), [])
        self.assertEqual(len(self.backend.units), 2)

    def test_r298_card_lines_and_electrical_bars_match_widgets(self):
        from meridiana.ui.plant_page import string_figures, unit_lines
        self.wired()
        state = self.backend.state
        old_bars, _rows = string_figures(state.strings[0])
        bars = self.backend.strings[0]['bars']
        self.assertEqual([(b['label'], b['text'], b['low'], b['high'], b['state']) for b in bars],
                         [b[1:] for b in old_bars])
        self.assertEqual(self.backend.units[0]['lines'], list(unit_lines(state, state.units[0])))

    def test_r297_move_rename_remove_keep_physical_strings_and_undo(self):
        keys = self.wired()
        self.backend.addInverter(inverter_record(model='Second'))
        self.wait()
        self.backend.renameUnit(1, 'Roof')
        self.backend.moveUnit(1, 1)
        self.wait()
        self.assertEqual(self.backend.runs()[0]['inverter'], 2)
        self.assertEqual(self.backend.runs()[0]['modules'], keys)
        self.backend.removeUnit(2, False)
        self.wait()
        self.assertEqual(self.backend.runs()[0]['inverter'], 0)
        self.backend.undo()
        self.wait()
        self.assertEqual(self.backend.units[1]['name'], 'Roof')

    def test_r115_moves_reverses_deletes_and_restores_string(self):
        keys = self.wired()
        self.backend.reverseString(0)
        self.backend.moveString(0, 1, 2)
        self.wait()
        self.assertEqual(self.backend.runs()[0]['modules'], keys[::-1])
        self.assertEqual(self.backend.runs()[0]['mppt'], 2)
        self.backend.deleteString(0)
        self.wait()
        self.assertEqual(self.backend.runs(), [])
        self.backend.undo()
        self.wait()
        self.assertEqual(self.backend.runs()[0]['modules'], keys[::-1])

    def test_checks_match_core_including_voltage_current_sources(self):
        self.wired()
        expected = plant.build(self.session.project, self.results)
        got = self.backend.strings[0]
        self.assertEqual(got['state'], expected.strings[0].state)
        self.assertEqual(got['voltages'], plant.voltages(expected.strings[0]))
        self.assertEqual(got['checks'], [dict(key=c.key, label=c.label, detail=c.detail,
                                           level=c.level, source=c.source)
                                        for c in expected.strings[0].plan.checks])

    def test_invalid_connection_cannot_change_project(self):
        self.wired()
        before = self.session.snapshot()
        self.assertFalse(self.backend.moveString(0, 99, 99))
        self.assertEqual(before, self.session.snapshot())
        self.assertTrue(self.backend.message)

    def test_r396_no_dot_without_previous_result_and_certain_stale_only(self):
        self.assertFalse(self.backend.calculateDirty)
        self.assertFalse(self.backend.layoutDirty)
        generation = self.session.energy_asked()
        self.session.energy_done(generation, {'fixture': True})
        self.assertFalse(self.backend.calculateDirty)
        self.backend.setEnergy('dc_ac_ratio', 1.2)
        self.assertTrue(self.backend.calculateDirty)
        self.backend.undo()
        self.assertFalse(self.backend.calculateDirty)
        self.session.edit('Tilt', lambda p: p.subfields[0].params.update(tilt=17))
        self.assertTrue(self.backend.layoutDirty)
        self.assertTrue(self.backend.calculateDirty)
        self.backend.undo()
        self.assertFalse(self.backend.layoutDirty)
        self.assertFalse(self.backend.calculateDirty)

    def test_storage_apply_is_atomic_and_invalid_keeps_old(self):
        patch = {'battery': {'manufacturer': 'Fixture', 'model': 'AC', 'coupling': 'ac',
                            'usable_energy_kwh': 10, 'max_charge_power_w': 5000,
                            'max_discharge_power_w': 5000, 'round_trip_efficiency_pct': 90,
                            'efficiency_basis': 'ac_round_trip'},
                 'battery_units': 1, 'storage_coupling': 'ac', 'storage_inverter': {},
                 'storage_efficiency_pct': None}
        self.assertTrue(self.backend.applyStorage(patch))
        before = self.session.snapshot()
        self.assertFalse(self.backend.applyStorage(dict(patch, battery_units=0)))
        self.assertEqual(before, self.session.snapshot())
        self.backend.removeStorage()
        self.assertFalse(self.session.project.economics['battery'])
        self.backend.undo()
        self.assertEqual(self.session.project.economics['battery'], patch['battery'])

    def test_async_proposal_matches_core_and_preserves_snapshot(self):
        self.backend.addInverter(inverter_record(ac_power_nominal_w=100000,
                                                 dc_current_max_per_mppt_a=[300, 300],
                                                 dc_isc_max_per_mppt_a=[400, 400]))
        self.wait()
        before = self.session.snapshot()
        expected = plant.proposal(self.session.project, self.results, strategy='serpentine')
        self.backend.propose({'strategy': 'serpentine', 'replace': True})
        self.assertEqual(before, self.session.snapshot())
        self.wait()
        self.assertTrue(expected.search_complete)
        self.assertEqual(self.backend.runs(), plant.runs_of(expected))
        self.backend.undo()
        self.wait()
        self.assertEqual(self.session.snapshot(), before)

    def test_cancelled_search_cannot_apply_late_result(self):
        self.wired()
        before = self.session.snapshot()
        self.backend.propose({'strategy': 'rows', 'replace': True})
        self.backend.cancelSearch()
        QThreadPool.globalInstance().waitForDone(30000)
        self.app.processEvents()
        self.assertEqual(self.session.snapshot(), before)

    def test_stale_sizing_and_proposal_return_after_project_edit_without_applying(self):
        from meridiana.energy.sizing import Result
        for kind in ('sizing', 'proposal'):
            with self.subTest(kind=kind):
                entered, release = threading.Event(), threading.Event()
                worker = []
                def slow(*args, worker=worker, entered=entered, release=release, kind=kind, **kwargs):
                    worker.append(threading.get_ident())
                    entered.set()
                    release.wait(10)
                    return Result(ok=True, entries=[], runs=[], ratio=1.1) if kind == 'sizing' else plant.Plant()
                target = 'meridiana.energy.sizing.choose' if kind == 'sizing' else 'meridiana.energy.plant.proposal'
                with patch(target, side_effect=slow):
                    if kind == 'sizing':
                        self.backend.startSizing('Acme', [inverter_record()])
                    else:
                        self.backend.propose({'replace': True})
                    self.assertTrue(entered.wait(5))
                    self.assertNotEqual(worker, [threading.get_ident()])
                    self.session.edit('Rename', lambda p: setattr(p, 'name', p.name + ' changed'))
                    expected = self.session.snapshot()
                    release.set()
                    self.wait()
                    self.assertEqual(expected, self.session.snapshot())
                    self.assertIn('changed', self.backend.message)

    def test_optimizer_edit_and_explicit_groups_have_checks_and_one_undo(self):
        from meridiana import catalog
        inv = next(r for r in catalog.search('inverters', manufacturer='SolarEdge', limit=None) if r['model'] == 'SE50K')
        self.backend.addInverter(inv)
        self.wait()
        self.assertTrue(self.backend.units[0]['optimized'])
        keys = [f's1/{m.key}' for m in self.results['s1'].modules][:40]
        self.backend.commitString(1, 1, keys, -1)
        self.wait()
        before = self.session.snapshot()
        self.assertTrue(self.backend.setOptimizerGroups(0, [1] * 40))
        self.wait()
        self.assertEqual(self.backend.runs()[0]['optimizer_group_sizes'], [1] * 40)
        self.assertFalse(self.backend.setOptimizerGroups(0, [3] * 13 + [1]))
        self.backend.undo()
        self.wait()
        self.assertEqual(before, self.session.snapshot())

    def test_sweep_complete_and_each_strategy_preserve_existing_strings(self):
        keys = self.wired()
        before = copy.deepcopy(self.backend.runs()[0])
        for strategy in plant.strategy_names():
            with self.subTest(strategy=strategy):
                self.backend.propose({'strategy': strategy, 'replace': False, 'only': keys})
                self.wait()
                self.assertEqual(self.backend.runs()[0], before)

    def test_empty_redraw_deletes_and_overlapping_draw_remaps_selection(self):
        keys = self.wired()
        self.backend.commitString(1, 2, keys, -1)
        self.wait()
        self.assertEqual(len(self.backend.runs()), 1)
        self.assertEqual(self.backend.selected, 0)
        self.backend.commitString(1, 2, [], 0)
        self.wait()
        self.assertEqual(self.backend.runs(), [])


if __name__ == '__main__':
    unittest.main()


class PlantSignalsTest(PlantBackendTest):
    """The signals of the backend by family (06/11/2026, the Quick's slowness): one edit gives one `dataChanged` for
    the lists of the strings and one `changed` after it, not four or five, and a selection gives none of them."""

    def setUp(self):
        super().setUp()
        self.counts = {}
        for name in ('changed', 'dataChanged', 'stateChanged', 'projectChanged', 'selectionChanged'):
            getattr(self.backend, name).connect(lambda name=name: self.counts.__setitem__(name, self.counts.get(name, 0) + 1))

    def test_one_data_signal_for_one_edit_and_one_changed_after_it(self):
        self.backend.addInverter(inverter_record())
        self.wait()
        self.assertEqual(self.counts.get('dataChanged'), 1, self.counts)
        self.assertEqual(self.counts.get('changed'), self.counts.get('stateChanged'), self.counts)
        self.assertLessEqual(self.counts.get('changed'), 3, self.counts)
        self.assertEqual(len(self.backend.units), 1)

    def test_a_selection_moves_no_list(self):
        self.session.select('subfield', 's1')
        self.app.processEvents()
        self.app.processEvents()
        self.assertNotIn('dataChanged', self.counts)
        self.assertNotIn('changed', self.counts)
