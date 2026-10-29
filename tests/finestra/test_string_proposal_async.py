"""A global assignment must not block the window or apply after cancellation/project edits."""
import threading
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import _setup
from _fixtures import capannone
from meridiana import config

setUpModule = _setup.keep_global_state


class AsyncProposal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def exercise(self, stale):
        from PySide6.QtCore import QTimer
        cfg = config.Config(network_tiles=False, network_geocoding=False, network_pvgis=False, check_updates=False)
        win = _setup.window(self, capannone(), cfg=cfg)
        self.assertTrue(_setup.wait_until(self.app, lambda: bool(win.session.good_results()) and win._layouts_settled()))
        entered, release = threading.Event(), threading.Event()
        threads = []

        def propose(*_args, **_kwargs):
            threads.append(threading.get_ident())
            entered.set()
            release.wait(5)
            raise RuntimeError('Late result must be discarded')

        before = copy.deepcopy(win.project.energy)
        with patch('meridiana.energy.plant.proposal', side_effect=propose, create=True):
            win._start_string_proposal('serpentine')
            try:
                self.assertTrue(_setup.wait_until(self.app, entered.is_set))
                self.assertNotEqual(threads, [threading.get_ident()])
                ticks = []
                QTimer.singleShot(0, lambda: ticks.append(1))
                self.assertTrue(_setup.wait_until(self.app, lambda: bool(ticks)))
                if stale:
                    win.edit('Rename during assignment', lambda p: setattr(p, 'name', 'Changed'))
                else:
                    win._cancel_string_proposal()
            finally:
                release.set()
            self.assertTrue(_setup.wait_until(self.app, lambda: win.string_proposal_job is None))
        self.assertEqual(win.project.energy, before)

    def test_cancellation_keeps_strings(self):
        self.exercise(False)

    def test_project_edit_discards_stale_proposal(self):
        self.exercise(True)

    def test_proposal_keeps_hardware_and_explicit_replacement_is_undoable(self):
        from meridiana.energy.plant import Plant
        from meridiana.session import ProjectSession
        from meridiana.ui.window import MainWindow
        session = ProjectSession(capannone())
        session.project.energy['inverters'] = [{'record': {'model': 'Selected'}, 'count': 1}]
        before = copy.deepcopy(session.project.energy)
        host = SimpleNamespace(edit=session.edit)
        runs = [{'inverter': 1, 'mppt': 1, 'modules': [['field', '0:0']]}]
        MainWindow._strings_put(host, 'Apply strings', runs, entries=Plant().entries)
        self.assertEqual(session.project.energy['inverters'], before['inverters'])
        session.undo.undo()
        self.assertEqual(session.project.energy, before)
        replacement = [{'record': {'model': 'New optimizer inverter'}, 'count': 1}]
        MainWindow._strings_put(host, 'Apply hardware and strings', runs, entries=replacement)
        self.assertEqual(session.project.energy['inverters'], replacement)
        session.undo.undo()
        self.assertEqual(session.project.energy, before)

    def test_adopting_proposal_without_hardware_change_keeps_selected_inverters(self):
        from meridiana.energy.plant import Plant
        from meridiana.session import ProjectSession
        from meridiana.ui.window import MainWindow
        session = ProjectSession(capannone())
        entries = [{'record': {'model': 'Selected'}, 'count': 1}]
        session.project.energy['inverters'] = copy.deepcopy(entries)
        host = SimpleNamespace(session=session, tell=lambda _text: None)
        MainWindow._adopt_proposal(host, Plant())
        self.assertEqual(session.project.energy['inverters'], entries)

    def test_valid_partial_wiring_is_applied_and_unconnected_modules_are_reported(self):
        from _fixtures import inverter_record
        from meridiana import jobs
        from meridiana.energy import plant
        from meridiana.ui.window import MainWindow
        project = capannone()
        project.energy['inverters'] = [{'record': inverter_record(), 'count': 2, 'name': ''}]
        results, _, _ = jobs.layout_of(project)
        proposal = plant.proposal(project, results)
        self.assertTrue(proposal.search_complete)
        self.assertTrue(proposal.left)
        self.assertTrue(proposal.strings)
        applied, messages = [], []
        job = SimpleNamespace(interrupted=False, state='current', layout_keys={}, keep=None, strategy='serpentine')
        host = SimpleNamespace(string_proposal_job=job, string_proposal_progress=SimpleNamespace(end=lambda: None),
                               _state_key=lambda: 'current', session=SimpleNamespace(layout_keys={}),
                               _layouts_settled=lambda: True, tell=messages.append,
                               _strings_put=lambda *args, **kwargs: applied.append((args, kwargs)))
        MainWindow._string_proposal_done(host, (job, proposal))
        self.assertEqual(len(applied), 1)
        self.assertIn(str(len(proposal.left)), messages[-1])
        self.assertIn('unconnected', messages[-1])
        # A budget cutoff must still leave the previous wiring untouched.
        applied.clear()
        host.string_proposal_job = job
        proposal.search_complete = False
        proposal.search_reason = 'Search budget reached'
        MainWindow._string_proposal_done(host, (job, proposal))
        self.assertEqual(applied, [])
        # Unit-wide operating current can be a warning for manual wiring, but never an automatic proposal.
        proposal.search_complete = True
        proposal.search_reason = ''
        proposal.checks = {1: [SimpleNamespace(level='warn', key='imp_total', detail='10 A exceeds 8 A')]}
        host.string_proposal_job = job
        MainWindow._string_proposal_done(host, (job, proposal))
        self.assertEqual(applied, [])
        self.assertIn('10 A exceeds 8 A', messages[-1])
        proposal.checks = {}
        proposal.strings[0].state, proposal.strings[0].why = 'warn', 'Missing electrical limit'
        host.string_proposal_job = job
        MainWindow._string_proposal_done(host, (job, proposal))
        self.assertEqual(applied, [])
        self.assertIn('Missing electrical limit', messages[-1])

    def test_queued_plant_refresh_discards_previous_empty_layout_result(self):
        from meridiana.energy.plant import Plant
        from meridiana.ui.window import MainWindow
        current = Plant()
        host = SimpleNamespace(plant_generation=4, plant_returned=3, plant_state=current,
                               plant_timer=SimpleNamespace(isActive=lambda: True))
        MainWindow._plant_done(host, 4, Plant(auto=True))
        self.assertIs(host.plant_state, current)
        self.assertEqual(host.plant_returned, 3)
