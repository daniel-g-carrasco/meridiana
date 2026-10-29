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
                patch('meridiana.ui.window.QInputDialog.getItem', return_value=('Acme', True)):
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
        with patch('meridiana.ui.window.QInputDialog.getItem', return_value=('', False)) as ask:
            win._size_inverters()
        self.assertFalse(ask.called)
        self.assertIsNone(win.sizing_job)
