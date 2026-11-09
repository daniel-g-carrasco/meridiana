"""R541, «lo zoom in e out nel modello 2D in Impianto continua ad essere lento e scattante (non troppissimo), forse per
il riposizionamento dei simboli» (Daniel, 07/11/2026). Measured on Rho with the real wheel: a hand turns a notch every
150-250 ms, the plan settled every lone notch at once (the strings' names and the dashes laid out again, 40-110 ms) and
the backend made the strings' lines and names again at every view that settled with another scale (90-130 ms). Now
the plan scales them while the wheel turns and lays them out once, 300 ms after the last notch."""
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from meridiana import model
from meridiana.quick.backend import plan as plan_backend
from meridiana.quick.backend.plan import PlanController

RHO = Path.home() / 'dev/meridiana-prove/Prova capannone Rho.meridiana'
APP = None


def setUpModule():
    global APP
    APP = QApplication.instance() or QApplication([])


def spin(seconds):
    from _setup import turn_events          # the time itself is tested: the 300 ms the plan waits after a gesture
    turn_events(APP, seconds * 1000)


@unittest.skipUnless(RHO.exists(), 'the Rho project of the trials')
class ZoomSettle(unittest.TestCase):
    def setUp(self):
        project, _notice = model.Project.load(RHO)
        self.c = PlanController(project, manage_layout=False)
        self.c.setPhase('plant')
        self.c.viewSettled(-20, -60, 160, 40, .2, 1.0)
        spin(plan_backend.SCALE_SETTLE_MS / 1000 + .2)        # the first scale's layers made, before counting
        self.made = 0
        original = self.c._overlays

        def counted():
            self.made += 1
            original()
        self.c._overlays = counted

    def tearDown(self):
        self.c.close()

    def test_the_strings_are_made_again_once_after_the_wheel_stops(self):
        self.assertTrue(self.c.stringsVisible and self.c.editor.runs())
        mpp = .2
        for _notch in range(6):     # a notch every 200 ms; the plan tells the view 140 ms after each
            mpp *= 1.5
            self.c.viewSettled(-20, -60, 160, 40, mpp, 1.0)
            spin(.06)
            self.assertEqual(self.made, 0, 'made again while the wheel still turns')
        spin(plan_backend.SCALE_SETTLE_MS / 1000 + .2)
        self.assertEqual(self.made, 1)

    def test_a_pan_makes_nothing_again(self):
        self.c.viewSettled(0, -40, 180, 60, .2, 1.0)
        spin(plan_backend.SCALE_SETTLE_MS / 1000 + .2)
        self.assertEqual(self.made, 0)


if __name__ == '__main__':
    unittest.main()
