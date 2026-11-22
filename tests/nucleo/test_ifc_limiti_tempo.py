"""R34: the limits of the reading are of quantity, in the file's order, never of time. Before, two of them were of
time (15 s for the walls, 15 s for what is placed below the roofs), and how much they left out depended on how busy
the PC was: two readings of one model gave 129 and 137 obstacles. Now the points of those elements come from the scan
when it has them, the slow way is read for at most MAX_SLOW_POINTS elements and the shapes are made for at most
MAX_CANDIDATES candidates; what is past a limit is counted and said. The budget of time stays only when the caller gives
one, counted and said as depending on this PC. `checkpoint` stops a reading on request.

The samples are made by hand (`tests/data/ifc/README.md`)."""

import itertools
import time
import unittest
from pathlib import Path
from unittest import mock

import _setup  # noqa: F401

from meridiana.app.exchange import ifc_import, ifc_read, ifc_scan, ifc_worker
from meridiana.core.compute import resources
from meridiana.core.model import model

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "ifc"
PARAPETS = str(SAMPLES / "parapetto-parziale.ifc")       # 5 obstacles, all placed below the roofs
CUTS = str(SAMPLES / "r575-d9-tagli.ifc")                # 2 walls, one of them outside the roofs


def summary(found: dict) -> list[str]:
    return ifc_import.plan(found, model.Project(), "origin", None, name="t", source_name="t.ifc").left_out


def rings(found: dict) -> list:
    return sorted((o["kind"], o["ring"], o["z0"], o["z1"]) for o in found["obstacles"])


class NotTheClock(unittest.TestCase):
    def test_a_slow_clock_gives_the_same_obstacles(self):
        whole = ifc_read.read(PARAPETS)
        self.assertEqual(len(whole["obstacles"]), 5)
        ticks = itertools.count(0.0, 20.0)          # every look at the clock 20 s later: a very slow or busy PC
        with mock.patch.object(time, "perf_counter", side_effect=lambda: next(ticks)):
            slow = ifc_read.read(PARAPETS)
        self.assertEqual(rings(slow), rings(whole))
        self.assertFalse(slow["counts"].get("late_skipped"))
        self.assertFalse(slow["counts"].get("walls_skipped"))
        self.assertFalse(slow["counts"].get("over_budget"))

    def test_the_walls_do_not_depend_on_the_clock(self):
        whole = ifc_read.read(CUTS)
        ticks = itertools.count(0.0, 20.0)
        with mock.patch.object(time, "perf_counter", side_effect=lambda: next(ticks)):
            slow = ifc_read.read(CUTS)
        self.assertEqual(slow["counts"]["walls_outside"], whole["counts"]["walls_outside"])
        self.assertEqual(whole["counts"]["walls_outside"], 1)


class SlowPoints(unittest.TestCase):
    def test_past_the_limit_what_is_below_the_roofs_is_counted_and_said(self):
        whole = ifc_read.read(PARAPETS)
        self.assertFalse([line for line in summary(whole) if "not examined" in line])
        with mock.patch.object(ifc_read, "MAX_SLOW_POINTS", 0):
            cut = ifc_read.read(PARAPETS)
        self.assertEqual(len(cut["obstacles"]), 0)
        self.assertEqual(cut["counts"]["late_skipped"], 5)
        said = [line for line in summary(cut) if "start below the roofs" in line]
        self.assertEqual(len(said), 1, summary(cut))
        self.assertTrue(said[0].startswith("5 "), said)
        self.assertNotIn("lack of time", said[0])

    def test_past_the_limit_the_walls_are_counted_and_said(self):
        with mock.patch.object(ifc_read, "MAX_SLOW_POINTS", 0):
            cut = ifc_read.read(CUTS)
        self.assertEqual(cut["counts"]["walls_outside"], 0)
        self.assertEqual(cut["counts"]["walls_skipped"], 2)
        said = [line for line in summary(cut) if "walls were not examined" in line]
        self.assertEqual(len(said), 1, summary(cut))

    def test_the_points_of_the_scan_are_not_read_again(self):
        whole = ifc_read.read(PARAPETS)
        scanned = ifc_scan.scan(PARAPETS)
        slow = mock.Mock(wraps=ifc_read.box_points)
        with mock.patch.object(ifc_read, "MAX_SLOW_POINTS", 0), mock.patch.object(ifc_read, "box_points", slow):
            given = ifc_read.read(PARAPETS, points=scanned.points)
        asked = {call.args[0].id() for call in slow.call_args_list}
        self.assertFalse({i for i in asked if scanned.points(i) is not None})
        self.assertEqual(slow.call_count, 0)
        self.assertEqual(rings(given), rings(whole))
        self.assertFalse(given["counts"].get("late_skipped"))
        self.assertEqual(given["counts"]["slow_points"], 0)

    def test_the_points_of_the_scan_are_those_of_the_slow_way(self):
        # (a wall cut by a clipping is not here: the slow way takes the solid before the cut, the scan the one after)
        scanned = ifc_scan.scan(PARAPETS)
        f = ifc_read.open_model(PARAPETS)
        walls = ifc_read._by_type(f, "IfcWall")
        self.assertTrue(walls)
        for e in walls:
            fast, slow = scanned.points(e.id()), ifc_read.box_points(e, {}, ifc_read.unit_scale(f))
            self.assertIsNotNone(fast)
            for k in range(3):
                self.assertAlmostEqual(float(fast[:, k].min()), float(slow[:, k].min()), places=3)
                self.assertAlmostEqual(float(fast[:, k].max()), float(slow[:, k].max()), places=3)
        self.assertIsNone(scanned.points(10 ** 9))


class Candidates(unittest.TestCase):
    def test_past_the_limit_the_candidates_are_counted_and_said(self):
        whole = ifc_read.read(PARAPETS)
        picked = whole["counts"]["obstacle_candidates"]
        self.assertGreater(picked, 1)
        with mock.patch.object(ifc_read, "MAX_CANDIDATES", 1):
            cut = ifc_read.read(PARAPETS)
        self.assertEqual(cut["counts"]["obstacle_candidates"], 1)
        self.assertEqual(cut["counts"]["candidates_skipped"], picked - 1)
        self.assertLess(len(cut["obstacles"]), len(whole["obstacles"]))
        said = [line for line in summary(cut) if "may stand on the roofs" in line]
        self.assertEqual(len(said), 1, summary(cut))
        self.assertTrue(said[0].startswith(f"{picked - 1} "), said)


class Budget(unittest.TestCase):
    def test_what_the_time_given_left_out_says_it_depends_on_this_pc(self):
        found = ifc_read.read(PARAPETS)
        found["counts"].update(over_budget=3, uncut=2)
        lines = summary(found)
        said = [line for line in lines if "time it is given on this PC" in line]
        self.assertEqual(len(said), 2, lines)
        self.assertTrue(any(line.startswith("2 roof planes not cut") for line in said), said)


class Checkpoint(unittest.TestCase):
    def test_it_is_called_and_what_it_raises_goes_out(self):
        calls = []
        ifc_read.read(PARAPETS, checkpoint=lambda: calls.append(1))
        total = len(calls)
        self.assertGreater(total, 10)
        for at in sorted({1, 2, total // 3, total // 2, total - 1, total}):
            seen = itertools.count(1)

            def stop(at=at, seen=seen):
                if next(seen) >= at:
                    raise resources.Stopped()
            with self.subTest(at=at), self.assertRaises(resources.Stopped):
                ifc_read.read(PARAPETS, checkpoint=stop)

    def test_the_worker_passes_it_on(self):
        calls = []
        ifc_worker.read(PARAPETS, "direct", lambda f, w: None, None, None, checkpoint=lambda: calls.append(1))
        self.assertGreater(len(calls), 10)

        def stop():
            raise resources.Stopped()
        with self.assertRaises(resources.Stopped):
            ifc_worker.read(PARAPETS, "direct", lambda f, w: None, None, None, checkpoint=stop)


if __name__ == "__main__":
    unittest.main()
