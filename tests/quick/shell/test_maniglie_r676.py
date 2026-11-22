"""Panel edges resize in every phase and never take input inside another card (R676, R678)."""
import sys
import tempfile
import unittest
from pathlib import Path

import _setup

sys.path.insert(0, str(_setup.ROOT / 'tools'))
from probe_resize_handles import PHASES, borders, foreign_panels, window
from meridiana.app.interface.phases import phases
from quick.gestures import pump

setUpModule = _setup.keep_global_state


class Handles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.app, cls.host = window(Path(cls.folder.name), proof=False)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        pump(100)
        cls.folder.cleanup()

    def test_every_visible_panel_resizes_from_its_edge_in_every_phase(self):
        self.assertEqual(PHASES, tuple(phase.id for phase in phases()))
        rows = borders(self.app, self.host)
        self.assertEqual(len(rows), 18)
        for row in rows:
            with self.subTest(phase=row['phase'], side=row['side']):
                # the left card: Project in Model and Plant, the report's contents in Report (r39)
                shown = row['side'] != 'left' or row['phase'] in ('model', 'plant', 'report')
                self.assertEqual(row['visible'], shown)
                if shown:
                    self.assertEqual(row['cursor'], 'SplitVCursor' if row['side'] == 'bottom' else 'SplitHCursor')
                    self.assertAlmostEqual(row['delta'], 60, delta=1)

    def test_no_handle_takes_a_hover_or_press_inside_another_panel(self):
        rows = foreign_panels(self.app, self.host)
        self.assertEqual(len(rows), 48)       # 40, and the report's contents card in Report, its edge and the others' (r39)
        for row in rows:
            with self.subTest(**row):
                self.assertFalse(row['contains'])
                self.assertFalse(row['grabbed'])
                self.assertFalse(row['changed'])
                self.assertNotIn(row['cursor'], ('SplitHCursor', 'SplitVCursor'))


if __name__ == '__main__':
    unittest.main()
