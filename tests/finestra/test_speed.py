"""The acceptance of the keys per object and the events per topic (task 18b, step 3), measured offscreen on
the project of the architecture proofs (20 buildings, 40 sub-fields, 60 exclusions): a building renamed costs
little on the window's thread, lays out nothing and computes no year; a height changed lays out again only the
sub-fields of that building. The thresholds are wide (an offscreen CI runner is slow); the numbers for Daniel's
PC come from docs/studio/18-prove/A-accettazione-18b.py."""

import time
import unittest
from statistics import median

import _setup
from _fixtures import generated

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it

RENAME_MS = 400                 # the measure asks for 100 ms on the PC; offscreen on a runner, four times that


class Speed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, generated(20, 2, 3), size=(1400, 900), pause=True)
        self.settle()
        self.assertEqual(len(self.win.results), 40)

    def wait_until(self, condition, seconds: float = 60.0) -> bool:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.app.processEvents()
            if condition():
                return True
            time.sleep(0.005)
        return condition()

    def settle(self) -> None:
        """Every layout back (every filled sub-field with a result whose key is the project's) and the window idle."""
        self.assertTrue(self.wait_until(lambda: not self.win.relayout_timer.isActive() and all(
            self.win.session.layout_state(sf) in ("ok", "error", "empty") for sf in self.win.project.subfields)))
        for _ in range(5):
            self.app.processEvents()

    def test_a_rename_moves_nothing_and_costs_little_and_a_height_lays_again_only_the_sub_fields_it_touches(self):
        self.renamed()
        self.height_changed()

    def renamed(self):
        """A building renamed costs little on the window's thread, lays out nothing and computes no year."""
        win = self.win
        bid = win.project.buildings[0].id
        win.energy = {"marker": True}                   # as after one computation: the pages have results
        computed = []
        win._compute_energy = lambda fetch=False: computed.append(fetch)
        job, generation = win.layout_job, win.generation
        times = []
        for k in range(5):
            t = time.perf_counter()
            win._edited("building", bid, {"name": f"Renamed {k}"})
            times.append((time.perf_counter() - t) * 1000)
            self.app.processEvents()
        self.assertFalse(win.relayout_timer.isActive())        # no layout asked for
        self.assertIs(win.layout_job, job)
        self.assertEqual(win.generation, generation)
        self.assertFalse(win.energy_timer.isActive())          # no year asked for
        self.assertEqual(computed, [])
        self.assertEqual(win.tree.topLevelItem(0).child(0).child(0).text(0), "Renamed 4")
        self.assertLess(median(times), RENAME_MS, times)
        # the undo of a rename is as cheap
        t = time.perf_counter()
        win.undo.undo()
        self.app.processEvents()
        self.assertLess((time.perf_counter() - t) * 1000, RENAME_MS)
        self.assertEqual(win.project.buildings[0].name, "Renamed 3")
        self.assertFalse(win.relayout_timer.isActive())
        self.assertEqual(computed, [])

    def height_changed(self):
        """A height changed lays out again only the sub-fields of that building, and those that see every one."""
        win = self.win
        b = win.project.buildings[3]
        mine = [sf.id for sf in win.project.subfields if sf.building == b.id]
        self.assertEqual(len(mine), 2)
        before = dict(win.results)
        win._edited("building", b.id, {"height": 12.0})
        self.settle()
        self.assertEqual(sorted(win.layout_job.laid), sorted(mine))
        for sf in win.project.subfields:
            if sf.id not in mine:
                self.assertIs(win.results[sf.id], before[sf.id])
        # a sub-field that keeps out of the shadows sees every building: the height of another moves it
        other = win.project.subfields[0]
        self.assertNotEqual(other.building, b.id)
        win._edited("subfield", other.id, {"params.shade_free": True})
        self.settle()
        self.assertEqual(win.layout_job.laid, [other.id])
        win._edited("building", b.id, {"height": 14.0})
        self.settle()
        self.assertEqual(sorted(win.layout_job.laid), sorted([*mine, other.id]))


if __name__ == "__main__":
    unittest.main()
