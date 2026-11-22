"""R389: the result inspectors edit the same project, with undo and guarded drafts."""
import copy
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QUrl

import _setup
from meridiana.core.model import model
from meridiana import i18n
from meridiana.app.session import ProjectSession


setUpModule = _setup.keep_global_state


class ResultEditorsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        i18n.setup('it')

    def editor(self, phase):
        from meridiana.gui.backend.charts_editor import ResultEditor
        session = ProjectSession(model.Project())
        editor = ResultEditor(session, phase)
        self.addCleanup(editor.close)
        return session, editor

    def test_loss_price_and_consumption_fields_edit_with_undo(self):
        for phase, field, section, key, value in (
            ('production', 'losses.soiling', 'energy', 'losses', '3,5'),
            ('consumption', 'annual_kwh', 'consumption', 'annual_kwh', '12500'),
            ('economics', 'buy_f1', 'economics', 'buy_f1', '0,42'),
        ):
            with self.subTest(phase=phase):
                session, editor = self.editor(phase)
                before = copy.deepcopy(getattr(session.project, section))
                self.assertTrue(editor.commit(field, value, editor.epoch))
                expected = {'production': {'soiling': 3.5}, 'consumption': 12500, 'economics': .42}[phase]
                self.assertEqual(getattr(session.project, section)[key], expected)
                session.undo.undo()
                self.assertEqual(getattr(session.project, section), before)

    def test_an_editor_behind_another_phase_makes_its_fields_when_shown_or_asked(self):
        # R598: 40 sub-fields filled at once held the window for seconds while the Production inspector made its
        # form again behind another phase. The page says whether it is on show (`shown`): behind, a change makes
        # nothing and tells only what is read live; the fields are made when it is shown, or asked from Python
        session, editor = self.editor('production')
        made, told = [], []
        refresh = editor.refresh
        editor.refresh = lambda: (made.append(True), refresh())[1]
        editor.changed.connect(lambda: told.append(True))
        session.edit('soiling', lambda p: p.energy.setdefault('losses', {}).__setitem__('soiling', 3.0))
        self.assertEqual(len(made), 1, 'nobody watches (no page): made at every change, as before')
        editor.setProperty('shown', False)
        del made[:], told[:]
        session.edit('soiling', lambda p: p.energy['losses'].__setitem__('soiling', 4.0))
        session.edit('soiling', lambda p: p.energy['losses'].__setitem__('soiling', 5.0))
        self.assertEqual(made, [], 'behind another phase: nothing made')
        self.assertEqual(len(told), 2, 'what is read live is told')
        self.assertEqual(editor.field('losses.soiling').data['value'], 5.0, 'asked from Python: made now')
        self.assertEqual(len(made), 1)
        session.edit('soiling', lambda p: p.energy['losses'].__setitem__('soiling', 6.0))
        self.assertEqual(len(made), 1)
        editor.setProperty('shown', True)
        self.assertEqual(len(made), 2, 'shown: made once, with every change that came meanwhile')
        self.assertEqual(editor.field('losses.soiling').data['value'], 6.0)
        editor.setProperty('shown', True)
        session.edit('soiling', lambda p: p.energy['losses'].__setitem__('soiling', 7.0))
        self.assertEqual(len(made), 3, 'on show: made at the change')

    def test_same_field_survives_refresh_but_old_file_draft_is_rejected(self):
        session, editor = self.editor('economics')
        field = editor.field('buy_f1')
        self.assertTrue(editor.commit('buy_f1', .4, editor.epoch))
        self.assertIs(field, editor.field('buy_f1'))
        epoch = editor.epoch
        session.changed('file')
        self.assertFalse(editor.commit('buy_f1', .6, epoch))
        self.assertEqual(session.project.economics['buy_f1'], .4)

    def test_invalid_and_disabled_fields_do_not_modify_project(self):
        session, editor = self.editor('economics')
        self.assertFalse(editor.commit('buy_f1', 'nan', editor.epoch))
        self.assertFalse(editor.commit('buy_f1', 5, editor.epoch))
        self.assertFalse(editor.commit('shared_pct', 20, editor.epoch))
        self.assertFalse(session.undo.can_undo())
        self.assertTrue(editor.commit('community', True, editor.epoch))
        self.assertTrue(editor.commit('shared_pct', 20, editor.epoch))

    def test_consumption_mode_clears_higher_priority_data_in_one_undo(self):
        session, editor = self.editor('consumption')
        session.project.consumption.update(measured=[['2025-01-01', 1]], monthly_bands_kwh=[{'F1': 20}], bands_kwh={'F1': 30})
        session.changed('project:energy')
        before = copy.deepcopy(session.project.consumption)
        self.assertTrue(editor.commit('mode', 'annual', editor.epoch))
        self.assertEqual(session.project.consumption['measured'], [])
        self.assertEqual(session.project.consumption['monthly_bands_kwh'], [])
        self.assertEqual(session.project.consumption['bands_kwh'], {})
        session.undo.undo()
        self.assertEqual(session.project.consumption, before)

    def test_bills_are_prepared_once_and_invalidated_by_edits_and_undo(self):
        from meridiana.gui.backend import charts_editor
        session, editor = self.editor('consumption')
        with patch.object(charts_editor.profiles, 'get', wraps=charts_editor.profiles.get) as policy:
            first = editor.bills
            columns = editor.billColumns
            totals = editor.billTotals
            self.assertEqual(editor.bills, first)
            self.assertEqual(editor.billTotals, totals)
            self.assertEqual(policy.call_count, 1)
        session.edit('bill', lambda p: p.consumption.update(monthly_bands_kwh=[{columns[0]: 123}]))
        self.assertEqual(editor.bills[0][columns[0]], 123)
        self.assertEqual(editor.billTotals[columns[0]], 123)
        session.undo.undo()
        self.assertEqual(editor.bills, first)

    def test_monthly_bill_and_total_use_real_values(self):
        session, editor = self.editor('consumption')
        self.assertTrue(editor.commit('mode', 'bills', editor.epoch))
        self.assertTrue(editor.setBill(0, 'F1', 234.5))
        self.assertEqual(session.project.consumption['monthly_bands_kwh'][0]['F1'], 234.5)
        self.assertEqual(editor.billTotals['F1'], 234.5)
        self.assertFalse(editor.setBill(12, 'F1', 8))
        self.assertFalse(editor.setBill(0, 'F1', -2))

    def test_automatic_lid_keeps_the_override_disabled(self):
        session, editor = self.editor('production')
        self.assertFalse(editor.field('losses.lid').data['enabled'])
        self.assertTrue(editor.commit('lid_auto', False, editor.epoch))
        self.assertTrue(editor.commit('losses.lid', 2.5, editor.epoch))
        self.assertEqual(session.project.energy['losses']['lid'], 2.5)
        self.assertTrue(editor.commit('lid_auto', True, editor.epoch))
        self.assertIsNone(session.project.energy['losses'].get('lid'))

    def test_curve_import_is_asynchronous_and_undoable(self):
        session, editor = self.editor('consumption')
        before = copy.deepcopy(session.project.consumption)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'curve.csv'
            path.write_text('timestamp;kWh\n2025-01-01 00:00;1.5\n2025-01-01 01:00;2.5\n', encoding='utf8')
            self.assertTrue(editor.importCurve(QUrl.fromLocalFile(str(path))))
            self.assertTrue(editor.busy)
            _setup.wait_until(self.app, lambda: not editor.busy)
            self.assertFalse(editor.error, editor.error)
            self.assertEqual([row[1] for row in session.project.consumption['measured']], [1.5, 2.5])
            self.assertEqual(editor.mode, 'measured')
            session.undo.undo()
            self.assertEqual(session.project.consumption, before)

    def test_curve_finishing_after_file_change_cannot_edit_new_project(self):
        session, editor = self.editor('consumption')
        entered, release = threading.Event(), threading.Event()
        def read(_path, _unit):
            entered.set()
            release.wait(5)
            return [['2025-01-01 00:00', 9]]
        with patch('meridiana.gui.backend.charts_editor.cons.read_curve', read):
            try:
                editor.importCurve(QUrl.fromLocalFile(str(Path.cwd() / 'unused.csv')))
                self.assertTrue(entered.wait(2))
                session.changed('file')
            finally:
                release.set()
            _setup.wait_until(self.app, lambda: not editor.busy)
        self.assertFalse(session.project.consumption.get('measured'))
        self.assertFalse(session.undo.can_undo())
