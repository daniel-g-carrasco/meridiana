"""Behaviour at the QML boundary, without a Widgets window."""
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

from meridiana.quick.app import create_app

from _fixtures import capannone
from meridiana import jobs
from meridiana.quick.bridge import Bridge
from quick.gestures import wait_for


class BridgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bridge = Bridge(capannone(), Path(self.temp.name))
        self.addCleanup(self.bridge.close)
        results, keys, _ = jobs.layout_of(self.bridge.session.project)
        self.bridge.accept_layout(0, results, keys)

    def test_all_module_corners_are_exported_and_selection_is_specific(self):
        b = self.bridge
        expected = sum(len(r.modules) for r in b.session.results.values())
        self.assertEqual(b.moduleCount, expected)
        modules = [x for x in b.scene if x['kind'] == 'module']
        self.assertEqual(len(modules), expected)
        m = modules[0]
        self.assertEqual(len(m['points']), 5)
        b.select('module', m['oid'], m['key'])
        self.assertEqual(b.session.selected_module, (m['oid'], m['key']))

    def test_edit_is_undoable_without_rebuilding_geometry(self):
        b = self.bridge
        b.select('building', 'b1', '')
        scene = b.scene
        old = b.selection['name']
        b.rename('Changed')
        self.assertEqual(b.selection['name'], 'Changed')
        self.assertIs(scene, b.scene)
        b.undo()
        self.assertEqual(b.selection['name'], old)

    def test_rectangle_and_handle_are_one_undo_step_each(self):
        b = self.bridge
        before = len(b.session.project.buildings)
        b.rectangle(80, 20, 90, 35)
        self.assertEqual(len(b.session.project.buildings), before + 1)
        oid = b.selection['oid']
        b.resizeRectangle(oid, 80, 20, 95, 40)
        self.assertEqual(b.selected_object().footprint[2], [95, 40])
        b.undo()
        self.assertEqual(b.selected_object().footprint[2], [90, 35])
        b.undo()
        self.assertEqual(len(b.session.project.buildings), before)

    def test_invalid_dimensions_and_stale_layout_are_rejected(self):
        b = self.bridge
        n = len(b.session.project.buildings)
        b.rectangle(0, 0, 0, 5)
        self.assertEqual(len(b.session.project.buildings), n)
        self.assertTrue(b.error)
        b.session.generation = 2
        self.assertFalse(b.accept_layout(1, {}, {}))
        self.assertGreater(b.moduleCount, 0)

    def test_stale_energy_does_not_replace_the_current_year(self):
        b = self.bridge
        b.session.generation = 3
        b._year = {'hours': 8760, 'totalValue': 42.}
        b._finished(2, {'error_sim': 'old failure'}, [], {})
        b.timer.stop()
        self.assertEqual(b.year['totalValue'], 42.)
        self.assertEqual(b.error, '')

    def test_daily_chart_conserves_the_hourly_energy(self):
        import pandas as pd
        b = self.bridge
        hourly = pd.DataFrame({'e_kwh': [2.] * 8760},
                              index=pd.date_range('2025-01-01', periods=8760, freq='h', tz='Europe/Rome'))
        sim = SimpleNamespace(hourly=hourly, energy_kwh=17520.)
        with patch.object(b, '_request_checks'):
            b._finished(0, {'sim': sim}, [], {})
        self.assertEqual(b.year['hours'], 8760)
        self.assertEqual(len(b.year['points']), 365)
        self.assertAlmostEqual(sum(b.year['daily']), b.year['totalValue'])

    def test_height_is_undoable_and_invalid_values_leave_the_model_intact(self):
        b = self.bridge
        b.select('building', 'b1', '')
        before = b.selected_object().height
        for invalid in (float('nan'), float('inf'), -1., 0., 501.):
            b.setHeight(invalid)
            self.assertEqual(b.selected_object().height, before)
        b.setHeight(12.5)
        self.assertEqual(b.selected_object().height, 12.5)
        b.undo()
        self.assertEqual(b.selected_object().height, before)

    def test_rotated_building_does_not_offer_axis_aligned_resize_handles(self):
        b = self.bridge
        building = b.session.project.buildings[0]
        building.footprint = [[0, 5], [5, 0], [10, 5], [5, 10]]
        b.select('building', building.id, '')
        self.assertFalse(b.selection['rectangle'])
        before = [p[:] for p in building.footprint]
        b.resizeRectangle(building.id, 0, 5, 10, 5)
        self.assertEqual(building.footprint, before)

    def test_check_names_follow_rename_without_a_new_energy_year(self):
        b = self.bridge
        b._enabled = True
        b.session.results['s1'].notes.append('Fixture layout note')
        b.select('subfield', 's1', '')
        b.rename('PreviousName')
        wait_for(lambda: not b.busy)
        self.assertTrue(any('PreviousName' in row['text'] for row in b.checkRows))
        b.rename('QuickName')
        wait_for(lambda: not b.busy)
        self.assertTrue(any('QuickName' in row['text'] for row in b.checkRows))
        self.assertFalse(any('PreviousName' in row['text'] for row in b.checkRows))
        self.assertEqual(b.session.generation, 0)

    def test_layout_failures_are_kept_in_checks(self):
        b = self.bridge
        b._enabled = True
        b.session.results['s1'] = ValueError('Broken layout')
        b.select('subfield', 's1', '')
        b.rename('BrokenField')
        wait_for(lambda: not b.busy)
        self.assertTrue(any(row['level'] == 'fail' and 'BrokenField' in row['text'] for row in b.checkRows))


if __name__ == '__main__':
    unittest.main()
