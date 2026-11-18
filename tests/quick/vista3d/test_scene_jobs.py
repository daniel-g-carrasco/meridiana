"""Standalone scene layouts: real workers, stale results and nonblocking close."""
from __future__ import annotations

import threading
import unittest
from unittest.mock import patch

import _setup
import numpy as np
from PySide6.QtCore import QCoreApplication, QEvent, QThreadPool
from PySide6.QtTest import QSignalSpy

from meridiana import jobs, model, move
from meridiana.quick.backend.scene_jobs import SceneLayouts
from meridiana.session import ProjectSession

setUpModule = _setup.keep_global_state


def project():
    p = model.Project(name="Standalone layout scheduler")
    p.buildings.append(model.Building("b1", "Shed", [[0, 0], [24, 0], [24, 16], [0, 16]], height=8))
    p.subfields.append(model.SubField("s1", "South", [[1, 1], [23, 1], [23, 15], [1, 15]],
                                       building="b1", filled=True, params={"tilt": 15.0}))
    return p


class SceneLayoutsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.session = ProjectSession(project())
        self.scheduler = SceneLayouts(self.session)
        self.releases = []

    def tearDown(self):
        for release in self.releases:
            release.set()
        self.scheduler.close()
        self.assertTrue(QThreadPool.globalInstance().waitForDone(5000))
        self.app.processEvents()

    def wait(self, condition):
        self.assertTrue(_setup.wait_until(self.app, condition, seconds=5), "Worker did not reach expected state")

    def settle(self):
        self.wait(lambda: not self.scheduler.busy)

    def begin(self):
        self.scheduler.begin()
        self.assertTrue(self.scheduler.busy)
        self.settle()
        self.assertIn("s1", self.session.good_results())

    def test_height_move_and_undo_match_core_without_energy(self):
        self.begin()
        initial = self.session.results["s1"].table.copy()
        self.session.edit("Raise roof", lambda p: setattr(p.buildings[0], "height", 10))
        self.settle()
        raised = self.session.results["s1"].table.copy()
        self.assertFalse(np.array_equal(initial, raised))
        self.session.edit("Move building", move.translate(self.session.project, "building", "b1", 4, 3))
        self.settle()
        expected, keys, _ = jobs.layout_of(self.session.project)
        np.testing.assert_array_equal(self.session.results["s1"].table, expected["s1"].table)
        self.assertEqual(self.session.layout_keys, keys)
        self.session.undo.undo()
        self.settle()
        np.testing.assert_array_equal(self.session.results["s1"].table, raised)
        self.session.undo.undo()
        self.settle()
        np.testing.assert_array_equal(self.session.results["s1"].table, initial)
        self.assertEqual(self.session.energy, {})
        self.assertEqual(self.session.energy_generation, 0)

    def test_rename_and_undo_retain_layout_without_job(self):
        self.begin()
        generation = self.session.generation
        before = self.session.results["s1"]
        with patch.object(jobs, "layout_of", wraps=jobs.layout_of) as compute:
            self.session.edit("Rename", lambda p: setattr(p.buildings[0], "name", "New name"))
            self.session.undo.undo()
            self.app.processEvents()
            self.assertFalse(self.scheduler.busy)
            self.assertEqual(compute.call_count, 0)
        self.assertIs(self.session.results["s1"], before)
        self.assertEqual(self.session.generation, generation)

    def test_burst_debounces_and_delivers_on_main_thread(self):
        self.begin()
        core = jobs.layout_of
        workers, deliveries = [], []

        def compute(p, known):
            workers.append(threading.get_ident())
            return core(p, known)

        self.session.subscribe(lambda topics: deliveries.append(threading.get_ident())
                               if any(t.startswith("layout:") for t in topics) else None)
        with patch.object(jobs, "layout_of", side_effect=compute):
            for height in (9, 10, 11):
                self.session.edit("Raise", lambda p, value=height: setattr(p.buildings[0], "height", value))
            self.settle()
        self.assertEqual(len(workers), 1)
        self.assertNotEqual(workers[0], threading.get_ident())
        self.assertEqual(deliveries, [threading.get_ident()])
        expected, _, _ = core(self.session.project)
        np.testing.assert_array_equal(self.session.results["s1"].table, expected["s1"].table)

    def test_running_snapshot_stays_old_and_stale_result_is_not_applied(self):
        entered, release = threading.Event(), threading.Event()
        self.releases.append(release)
        core = jobs.layout_of
        seen_heights, delivered_heights = [], []

        def compute(p, known):
            if not seen_heights:
                entered.set()
                self.assertTrue(release.wait(5))
            seen_heights.append(p.buildings[0].height)
            return core(p, known)

        self.session.subscribe(lambda topics: delivered_heights.append(self.session.project.buildings[0].height)
                               if "layout:s1" in topics else None)
        with patch.object(jobs, "layout_of", side_effect=compute):
            self.scheduler.begin()
            self.wait(entered.is_set)
            self.session.edit("Raise while pending", lambda p: setattr(p.buildings[0], "height", 12))
            release.set()
            self.settle()
        self.assertEqual(seen_heights, [8, 12])
        self.assertEqual(delivered_heights, [12])
        expected, _, _ = core(self.session.project)
        np.testing.assert_array_equal(self.session.results["s1"].table, expected["s1"].table)

    def test_file_replacement_cannot_receive_previous_project_layout(self):
        self.begin()
        self.session.take(model.Project(), None, saved=True)
        self.settle()
        self.assertEqual(self.session.results, {})
        self.assertEqual(self.session.layout_keys, {})

    def test_known_layout_identity_is_preserved_on_explicit_refresh(self):
        self.begin()
        old = self.session.results["s1"]
        self.scheduler.request()
        self.settle()
        self.assertIs(self.session.results["s1"], old)

    def test_subfield_layout_error_is_retained_and_reported(self):
        self.begin()
        error = QSignalSpy(self.scheduler.error)
        self.session.edit("Invalid boundary", lambda p: setattr(p.subfields[0], "ring", [[0, 0], [1, 0]]))
        self.settle()
        self.assertIsInstance(self.session.results["s1"], Exception)
        self.assertEqual(error.count(), 1)
        self.assertIn("s1", error.at(0)[0])
        self.session.undo.undo()
        self.settle()
        self.assertIn("s1", self.session.good_results())

    def test_close_with_running_worker_does_not_wait_or_publish(self):
        entered, release, finished = threading.Event(), threading.Event(), threading.Event()
        self.releases.append(release)
        core = jobs.layout_of

        def compute(p, known):
            entered.set()
            try:
                if not release.wait(5):
                    raise RuntimeError("Test gate was not released")
                return core(p, known)
            finally:
                finished.set()

        with patch.object(jobs, "layout_of", side_effect=compute):
            self.scheduler.begin()
            self.wait(entered.is_set)
            self.scheduler.close()
            self.assertFalse(finished.is_set(), "close waited for the blocked worker")
            self.assertFalse(self.scheduler.busy)
            self.scheduler.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            release.set()
            self.wait(finished.is_set)
            self.app.processEvents()
        self.assertEqual(self.session.results, {})
        self.assertEqual(self.session.listeners, [])

    def test_worker_failure_is_reported_and_next_request_recovers(self):
        error = QSignalSpy(self.scheduler.error)
        with patch.object(jobs, "layout_of", side_effect=RuntimeError("Layout worker failed")):
            self.scheduler.begin()
            self.settle()
        self.assertEqual(error.count(), 1)
        self.assertIn("Layout worker failed", error.at(0)[0])
        self.scheduler.request()
        self.settle()
        self.assertIn("s1", self.session.good_results())


if __name__ == "__main__":
    unittest.main()
