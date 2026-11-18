"""Long sizing leaves the GUI responsive; cancelled or stale proposals never overwrite edits."""
import threading
import unittest
from unittest.mock import patch

import _setup
from _fixtures import capannone, inverter_record
from meridiana import config

setUpModule = _setup.keep_global_state


class AsyncSizing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def exercise(self, stale=False):
        from PySide6.QtCore import QTimer
        from meridiana.energy.sizing import Result
        cfg = config.Config(network_tiles=False, network_geocoding=False, network_pvgis=False, check_updates=False)
        win = _setup.window(self, capannone(), cfg=cfg)
        self.assertTrue(_setup.wait_until(self.app, lambda: bool(win.session.good_results())))
        entered, release = threading.Event(), threading.Event()
        thread = []

        def choose(*_args, **_kwargs):
            thread.append(threading.get_ident())
            entered.set()
            release.wait(5)
            return Result(ok=True, entries=[], runs=[], ratio=1.1)

        record = inverter_record()
        before = win.project.to_json()
        with patch('meridiana.energy.sizing.choose', side_effect=choose), \
                patch('meridiana.ui.window.catalog.brands', return_value=['Acme']), \
                patch('meridiana.ui.window.catalog.load', return_value=[record]), \
                patch('meridiana.ui.brand_picker.NameDialog.ask', return_value=('Acme', True, [])):
            win._size_inverters()
            try:
                self.assertTrue(_setup.wait_until(self.app, entered.is_set))
                self.assertNotEqual(thread, [threading.get_ident()])
                ticks = []
                QTimer.singleShot(0, lambda: ticks.append(True))
                self.assertTrue(_setup.wait_until(self.app, lambda: bool(ticks)))
                if stale:
                    win.edit('Rename', lambda p: setattr(p, 'name', 'Edited during search'))
                else:
                    win._cancel_sizing()
            finally:
                release.set()
            self.assertTrue(_setup.wait_until(self.app, lambda: win.pool.activeThreadCount() == 0))
            _setup.turn_events(self.app, 30)
        self.assertEqual(win.project.energy, before['variants'][0]['design']['energy'])
        self.assertIsNone(win.sizing_job)
        if stale:
            self.assertEqual(win.project.name, 'Edited during search')
            self.assertIn('project changed', win.statusBar().currentMessage())
        else:
            self.assertEqual(win.project.to_json(), before)

    def test_cancelled_search_never_applies_its_late_result(self):
        self.exercise()

    def test_project_edits_make_the_pending_proposal_stale(self):
        self.exercise(stale=True)

    def test_sizing_waits_for_the_current_layout_before_asking_for_a_brand(self):
        cfg = config.Config(network_tiles=False, network_geocoding=False, network_pvgis=False, check_updates=False)
        win = _setup.window(self, capannone(), cfg=cfg)
        self.assertTrue(_setup.wait_until(self.app, lambda: win._layouts_settled()))
        sf = win.project.subfields[0]
        win._edited('subfield', sf.id, {'params.edge': 5.0})
        with patch('meridiana.ui.brand_picker.NameDialog.ask', return_value=('', False, [])) as ask:
            win._size_inverters()
        self.assertFalse(ask.called)
        self.assertIsNone(win.sizing_job)


class WhatTheChoiceSays(unittest.TestCase):
    """What the window says when a sizing or a string proposal comes back (R267, review F): the notes of a choice
    made, the whole reason of a choice impossible, the strings whose only warning is a condition of their order."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        cfg = config.Config(network_tiles=False, network_geocoding=False, network_pvgis=False, check_updates=False)
        _setup.window(self, capannone(), cfg=cfg)
        self.assertTrue(_setup.wait_until(self.app, self.win._layouts_settled))

    def sized(self, result) -> str:
        with patch('meridiana.energy.sizing.choose', return_value=result), \
                patch('meridiana.ui.window.catalog.brands', return_value=['Acme']), \
                patch('meridiana.ui.window.catalog.load', return_value=[inverter_record()]), \
                patch('meridiana.ui.brand_picker.NameDialog.ask', return_value=('Acme', True, [])):
            self.win._size_inverters()
            self.assertTrue(_setup.wait_until(self.app, lambda: self.win.sizing_job is None, 30))
        return self.win.statusBar().currentMessage()

    def test_a_choice_made_says_its_notes(self):
        from meridiana.energy.sizing import Result
        note = "S1400: only on an inverter without integrated DC fuses (DS-000205-EU p. 2)"
        said = self.sized(Result(ok=True, entries=[], runs=[], ratio=1.1, notes=[note]))
        self.assertEqual(self.win.undo.undoText(), "Size the inverters by themselves")
        self.assertIn("Inverters sized in Plant", said)
        self.assertIn("Note: " + note, said)

    def test_a_choice_impossible_says_its_first_line_and_shows_the_whole_reason(self):
        from meridiana.energy.sizing import Result
        reason = ("No complete string proposal is possible with these inverters.\nWhy:\n"
                  "• PVS-10-TL: Field 1: 14 modules, a string needs 16 to 25 in series\n"
                  "• PVS-50-TL: Field 1: 14 modules, a string needs 17 to 23 in series")
        before = self.win.project.to_json()
        self.assertEqual(self.sized(Result(ok=False, reason=reason)), reason.partition("\n")[0])
        self.assertIn(("information", ("Size the inverter by itself", reason)), self.dialogs)
        self.assertEqual(self.win.project.to_json(), before)
        self.dialogs.clear()
        self.assertEqual(self.sized(Result(ok=False, reason="No inverter of Acme fits.")), "No inverter of Acme fits.")
        self.assertEqual(self.dialogs, [])                      # one line: the status bar is enough

    def test_strings_whose_only_warning_is_a_condition_are_proposed_and_the_condition_said(self):
        from types import SimpleNamespace as Fake

        from meridiana.ui import window as window_module
        win = self.win
        fuses = Fake(key="opt_fuses", level="warn", ok=True, label="S1400", detail="only on an inverter without DC fuses",
                     source="DS-000205-EU p. 2")
        clipped = Fake(key="opt_imp", level="warn", ok=True, label="S1200", detail="Imp above 15 A: clipped", source="")

        def string(*checks):
            return Fake(state="check", lost=False, plan=Fake(checks=list(checks)), why="a warning")

        def back(strings):
            job = Fake(interrupted=False, state=win._state_key(), layout_keys=dict(win.session.layout_keys), keep=None,
                       strategy="")
            result = Fake(strings=strings, checks={}, search_complete=True, search_reason="", left=[], notes=[])
            win.string_proposal_job = job
            with patch.object(window_module.plant_model, "runs_of", return_value=[{"modules": ["m1"]}]), \
                    patch.object(win, "_strings_put") as put:
                win._string_proposal_done((job, result))
            return put.called, win.statusBar().currentMessage()

        put, said = back([string(fuses)])
        self.assertTrue(put)                                    # as the automatic sizing accepts it (plant.acceptable)
        self.assertIn("Note: S1400: only on an inverter without DC fuses (DS-000205-EU p. 2)", said)
        put, said = back([string(fuses, clipped)])
        self.assertFalse(put)                                   # a loss is a fault of the string: never proposed
        self.assertIn("No complete string proposal was applied", said)
