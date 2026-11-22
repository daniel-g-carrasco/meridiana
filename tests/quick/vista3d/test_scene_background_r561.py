"""R561, R598 (study 48 chapter 6 step 5): the 3D scene of every change is a job of the mechanism, in the layout's
process (app/scene_job.py), for every size of project, so the window does not wait for it (an IFC model placed: 2.2 s
of the window's thread, model A; then a thread of the pool, which held the interpreter). The scene before stays shown
until the new one comes; a scene asked again meanwhile drops the older answer, and so does a scene made here; a pick
waits for the scene on its way; the jobs' bar has its row (no sentence of its own in the status bar any more)."""

from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

import numpy as np

import _setup

from meridiana.app import scene_job
from meridiana.core.geometry import mesh
from meridiana.core.model import model
from meridiana.gui.backend.scene import SceneBackend
from meridiana.gui.backend.work import WorkBackend
from meridiana.app.session import ProjectSession

setUpModule = _setup.keep_global_state


def project():
    p = model.Project(name="r561")
    p.buildings.append(model.Building(id="b1", name="A", footprint=[[0, 0], [20, 0], [20, 10], [0, 10]], height=6.0))
    return p


def wide(p, k):
    p.buildings.append(model.Building(id=f"n{k}", name=f"N{k}", footprint=[[40 + 30 * k, 0], [60 + 30 * k, 0],
                                                                            [60 + 30 * k, 15], [40 + 30 * k, 15]],
                                      height=9.0))


class SceneInTheBackground(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(folder.cleanup)
        self.session = ProjectSession(project())
        self.work = WorkBackend(self.session)
        self.addCleanup(self.work.close)
        self.scene = SceneBackend(self.session, Path(folder.name) / "geometry", center=self.work.center)
        self.addCleanup(self.scene.close)
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.scene.drawing, 60), "the first scene")

    def bodies(self):
        return {oid for part, oid, _n in self.scene._owners if part == "building"}

    def test_a_scene_comes_from_its_job_and_the_one_before_stays_meanwhile(self):
        before = self.scene.rebuilds
        triangles = len(self.scene.triangles[0])
        window, made = threading.get_ident(), []
        real = mesh.project_scene

        def project_scene(*args, **kwargs):
            made.append(threading.get_ident() == window)
            return real(*args, **kwargs)
        with mock.patch.object(mesh, "project_scene", project_scene):
            self.session.edit("add", lambda p: wide(p, 0))
            self.assertTrue(self.scene.drawing)
            self.assertEqual(triangles, len(self.scene.triangles[0]))      # the window did not make it
            self.assertTrue(_setup.wait_until(self.app, lambda: not self.scene.drawing, 60))
        self.assertEqual([], made, "never made in the window's process")
        self.assertEqual(before + 1, self.scene.rebuilds)
        self.assertEqual(["layout"], [p.name for p in self.work.center.runner.processes()], "in the layout's process")
        taken = self.scene.triangles[0].copy()
        self.assertGreater(len(taken), triangles)
        self.scene.rebuild()                                               # the same scene made here
        np.testing.assert_array_equal(taken, self.scene.triangles[0])
        self.assertEqual({"b1", "n0"}, self.bodies())
        self.assertTrue(Path(self.scene.modulesSource.toLocalFile()).exists(), "the modules' file the job wrote")

    def test_an_answer_for_a_project_changed_again_is_dropped(self):
        self.session.edit("one", lambda p: wide(p, 0))
        self.session.edit("two", lambda p: wide(p, 1))
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.scene.drawing, 60))
        self.assertEqual({"b1", "n0", "n1"}, self.bodies())
        self.session.edit("three", lambda p: wide(p, 2))
        scenes = self.scene.scenes
        self.assertTrue(_setup.wait_until(self.app, lambda: scenes._asked is not None, 60), "the job asked")
        self.scene.rebuild()                    # a scene made here meanwhile is newer than the one on its way
        rebuilds = self.scene.rebuilds
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.scene.drawing, 60))
        self.assertEqual(rebuilds, self.scene.rebuilds, "the answer on its way was not taken")
        self.assertEqual({"b1", "n0", "n1", "n2"}, self.bodies())

    def test_a_pick_waits_for_the_scene_on_its_way(self):
        self.session.edit("add", lambda p: wide(p, 0))
        self.scene.pick("buildings", 0, 10.0, 6.0, -5.0)
        self.assertEqual("site", self.session.selection[0])
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.scene.drawing, 60))

    def test_the_bar_has_its_row_without_cancel(self):
        rows = []
        self.work.rowsChanged.connect(lambda: rows.extend(r for r in self.work.rows if r["slot"] == scene_job.SLOT))
        self.session.edit("add", lambda p: wide(p, 0))
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.scene.drawing, 60))
        self.assertTrue(rows, "the scene's job had its row")
        self.assertFalse(rows[0]["cancellable"])
        self.assertEqual("3D view", rows[0]["title"])


if __name__ == "__main__":
    unittest.main()
