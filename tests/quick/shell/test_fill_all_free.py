"""«Fill all» (R605) on many sub-fields, in the real window off screen: the row of the Checks panel that stands for
40 sub-fields without modules fills them in one change, one step of the undo, and their layout is the job of the
layout after a change (the jobs' center, with its row in the bar): no road of its own.

The guard of the window (study 48, chapter 5) is measured and printed, not asserted: with 40 sub-fields the layout's
own calls (restart:layout, layout.on_done: 12-56 ms, the keys of 40 sub-fields) and the views told of 40 sub-fields
laid at once (the plan, the bridge) are over the threshold whatever change brings them. The Production inspector,
behind the model's phase, makes nothing (R598: its form of 80 fields made again at once held the window 7-15 s off
screen; now it is made when its page is shown, gui/backend/charts_editor.py): asserted here."""
import sys
import tempfile
import unittest
from pathlib import Path

import _setup
from _fixtures import clear_sky_meteo, generated, write_cache
from meridiana.gui.application import QuickWindow, create_app
from quick.aiuti.finestra_libera import settled, software_frames, window_stays_free

ONLY = ("submit:layout", "restart:layout", "layout.", "cancel:layout", "warm:layout", "changed")


def empty_many():
    """Ten sheds with four sub-fields each, none laid: 40 sub-fields without modules."""
    p = generated(10, 4, 0)
    for sf in p.subfields:
        sf.filled = False
    return p


class FillAllFree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        create_app()
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.cache = Path(cls.folder.name)
        write_cache(clear_sky_meteo(), cls.cache)
        cls.host = QuickWindow(empty_many(), cls.cache, theme={'theme': 'light'}, real_views=True)
        cls.bridge, cls.work = cls.host.bridge, cls.host.work
        cls.center, cls.session = cls.work.center, cls.host.bridge.session
        cls.bridge.configure_background(enabled=False)
        cls.win = cls.host.window
        cls.win.resize(1400, 900)
        cls.win.show()
        cls.bridge.recompute()

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def quiet(self) -> bool:
        return not self.bridge.busy and self.bridge._layout is None and not self.session.telling()

    def test_fill_all_lays_them_through_the_layout_job_with_its_row_and_one_undo(self):
        # nothing filled at the start: no layout keys to answer for, only the window's own work to end
        self.assertTrue(_setup.wait_for(self.quiet, 180000), 'the opening has ended')
        checks = self.host.parts.controllers['checks']
        self.assertTrue(_setup.wait_for(lambda: not checks.busy and any(
            not r['header'] and r.get('fixText') for r in checks.rows), 60000), 'the row for the 40')
        row = next(r for r in checks.rows if not r['header'] and r.get('fixText'))
        self.assertEqual(len(row['members']), 40)
        self.assertTrue(settled(self.win), 'the window has settled')
        steps = self.session.undo.count()
        bar = []
        launch = self.center._launch

        def launched(handle):
            launch(handle)
            bar.append([r['slot'] for r in self.center.rows()])
        self.center._launch = launched
        self.addCleanup(setattr, self.center, '_launch', launch)
        production, made = self.host.parts.controllers['productionEditor'], []
        refresh = production.refresh
        production.refresh = lambda: (made.append(True), refresh())[1]
        self.addCleanup(setattr, production, 'refresh', refresh)
        self.assertFalse(production.shown, 'the Production inspector is behind the model phase, and says so')
        with window_stays_free(self.center, call_ms=float('inf'), beat_ms=None, only=ONLY) as seen:
            checks.requestFix(row['itemIndex'])
            came = _setup.wait_for(lambda: self.quiet() and self.session.layouts_answer(), 180000)
        print(f'\nfill all on 40 sub-fields: {seen}; software frames: {software_frames(self.win)}; '
              f'over 5 ms: {seen.over(5)}', file=sys.stderr)
        self.assertTrue(came, 'the layouts of the 40 came back')
        self.assertEqual(made, [], 'the Production inspector, behind another phase, made none of its fields')
        self.assertEqual(len([f for f in (production.field(f'array_{i}') for i in range(40)) if f is not None]), 40,
                         'asked, its fields are those of the 40 arrays')
        self.assertTrue(any('layout' in slots for slots in bar), f'the layout job had its row in the bar: {bar}')
        self.assertEqual(self.session.undo.count(), steps + 1)
        results = self.session.good_results()
        self.assertTrue(all(sf.filled for sf in self.session.project.subfields))
        self.assertTrue(all(results[sf.id].count > 0 for sf in self.session.project.subfields))


if __name__ == '__main__':
    unittest.main()
