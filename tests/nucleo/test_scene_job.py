"""R598, study 48 chapter 6 step 5: the 3D scene as a job of the mechanism (app/scene_job.py), at home in the layout's
process. Its answer is that of mesh.project_scene called directly on the same project and layouts (the same arrays),
the props drawn as models left out by index, the modules' instance file written by the job; the layouts do not travel
(one of before is asked for and sent once); and, with real processes, the scene follows the project and only an
answer still current is taken, a process that falls leaves the scene of before."""

import pickle
import tempfile
import threading
import time
import unittest
from pathlib import Path

import _setup  # noqa: F401
import numpy as np

from _fixtures import capannone, mixed
from meridiana.app import jobs, layout_job, scene_job
from meridiana.app.session import ProjectSession, photo_of, project_from
from meridiana.app.view import viewaids
from meridiana.app.work.center import Center
from meridiana.app.work.job import Context
from meridiana.core.geometry import mesh
from meridiana.core.model import model

POLL = 0.05


def ctx(kept=None):
    return Context(1, (0, 1), {} if kept is None else kept, lambda message: None, stop=threading.Event())


def laid_session(p):
    s = ProjectSession(p)
    results, keys, _laid = jobs.layout_of(s.project)
    s.layout_done(s.generation, results, keys)
    return s


def direct(session, props=None):
    """mesh.project_scene called here, as the window made it before (SceneBackend.rebuild)."""
    p = project_from(photo_of(session.project))
    if props is not None:
        p.props = [p.props[i] for i in props]
    owners = []
    triangles, table, _edges = mesh.project_scene(p, session.good_results(), owners=owners)
    return triangles, table, owners


class SameScene(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())

    def assert_same(self, answer, made):
        triangles, table, owners = made
        self.assertEqual(len(triangles), len(answer["triangles"]))
        for a, b in zip(triangles, answer["triangles"], strict=True):
            self.assertEqual(a.dtype, b.dtype)
            np.testing.assert_array_equal(a, b)
        self.assertEqual(table.dtype, answer["table"].dtype)
        np.testing.assert_array_equal(table, answer["table"])
        self.assertEqual(owners, answer["owners"])

    def test_the_jobs_scene_is_that_of_mesh_project_scene(self):
        s = laid_session(mixed())
        self.assertTrue(any(r.modules for r in s.good_results().values()), "a scene with modules")
        owner = scene_job.Scenes(s, None, (), extra=lambda: {"props": None, "cache": str(self.folder)})
        answer = scene_job.run(owner._request(), ctx())
        self.assert_same(answer, direct(s))
        path = Path(answer["modules"])
        self.assertEqual(path.parent, self.folder)
        self.assertEqual(path, scene_job.instance_file(self.folder, answer["table"]), "the modules' file, written")

    def test_the_strings_job_is_viewaids_string_segments(self):
        s = laid_session(mixed())
        sid, laid = next((sid, r) for sid, r in s.good_results().items() if len(r.modules) >= 4)
        run = {"modules": [f"{sid}/{m.key}" for m in laid.modules[:4]]}
        s.edit("strings", lambda p: p.energy.__setitem__("strings", {"runs": [run]}))
        owner = scene_job.Scenes(s, None, (), kind=scene_job.STRINGS, slot=scene_job.STRINGS_SLOT)
        answer = scene_job.run_strings(owner._request(), ctx())
        lines, crosses = viewaids.string_segments(project_from(photo_of(s.project)), s.good_results())
        self.assertTrue(len(lines), "strings drawn")
        np.testing.assert_array_equal(np.asarray(lines), np.asarray(answer["lines"]))
        np.testing.assert_array_equal(np.asarray(crosses), np.asarray(answer["crosses"]))
        for mine, made in zip(answer["ribbons"], (scene_job.ribbons(lines), scene_job.ribbons(crosses)), strict=True):
            for x, y in zip(mine, made, strict=True):
                if y is None or isinstance(y, tuple):
                    self.assertEqual(x, y)
                else:
                    np.testing.assert_array_equal(x, y)

    def test_the_props_shown_as_models_are_left_out(self):
        p = mixed()
        p.props.append(model.Prop(id="o1", kind="broadleaf", at=[30.0, -10.0]))
        p.props.append(model.Prop(id="o2", kind="conifer", at=[34.0, -10.0]))
        s = laid_session(p)
        kept = len(s.project.props) - 1
        owner = scene_job.Scenes(s, None, (), extra=lambda: {"props": [kept], "cache": ""})
        answer = scene_job.run(owner._request(), ctx())
        self.assert_same(answer, direct(s, [kept]))
        self.assertEqual("", answer["modules"], "no folder: no file")
        self.assertEqual([oid for part, oid, _n in answer["owners"] if part == "prop"], ["o2"])


class WhatTravels(unittest.TestCase):
    def test_the_layouts_never_travel(self):
        s = laid_session(mixed())
        owner = scene_job.Scenes(s, None, ())
        request = owner._request()
        self.assertIs(request["photo"], s.photo(), "the photo, a reference")
        self.assertNotIn("layouts", request)
        weight = len(pickle.dumps(request)) - len(pickle.dumps(s.photo()))
        self.assertLess(weight, 5000, "beyond the photo, only the keys")
        kept = {}
        self.assertNotIn("missing", scene_job.run(request, ctx(kept)), "laid out in the process when not kept")
        self.assertTrue(kept["layouts"], "and kept for the layout's job too")

    def test_a_layout_of_before_is_asked_for_and_then_kept(self):
        s = laid_session(capannone())
        sid = s.project.subfields[0].id
        s.layout_keys = dict(s.layout_keys, **{sid: "a layout of before"})
        owner = scene_job.Scenes(s, None, ())
        kept = {}
        self.assertEqual({"missing": [sid]}, scene_job.run(owner._request(), ctx(kept)))
        owner._send = {sid}
        again = owner._request()
        self.assertIs(again["layouts"][sid], s.results[sid])
        self.assertNotIn("missing", scene_job.run(again, ctx(kept)))
        self.assertIn((sid, "a layout of before"), kept["layouts"])


class InProcesses(unittest.TestCase):
    """Scenes with a center and real processes (the layout's, the scene at home in it)."""

    def setUp(self):
        self.posted = threading.Event()
        self.center = Center(self.posted.set)
        self.addCleanup(self.center.close)
        self.session = laid_session(mixed())
        self.shown, self.told = [], []
        self.scenes = scene_job.Scenes(self.session, self.center, (("scene.test", self.shown.append),),
                                       changed=lambda: self.told.append(True))
        self.addCleanup(self.scenes.close)

    def until(self, condition, seconds=60.0) -> bool:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.posted.clear()
            self.center.pump()
            if condition():
                return True
            self.posted.wait(POLL)
        return condition()

    def bodies(self, answer):
        return {oid for part, oid, _n in answer["owners"] if part == "building"}

    def widen(self, name):
        def change(p):
            p.buildings.append(model.Building(id=name, name=name, footprint=[[200, 0], [210, 0], [210, 8], [200, 8]],
                                              height=5.0))
        return change

    def test_in_the_layouts_process_the_scene_follows_the_project_and_only_the_last_is_taken(self):
        self.center.warm(layout_job.KIND)
        self.scenes.ask()
        self.assertTrue(self.until(lambda: self.shown and not self.scenes.busy()), "the first scene")
        np.testing.assert_array_equal(self.shown[-1]["triangles"][0], direct(self.session)[0][0])
        self.assertEqual([p.name for p in self.center.runner.processes()], ["layout"], "in the layout's process")
        self.assertIn("scene.test", self.center.stats()["by_name"], "taken as a piece")
        launch, made = self.center._launch, []

        def launched(handle):           # a change while the scene is on its way: right after it starts
            launch(handle)
            if handle.kind is scene_job.KIND and not made:
                made.append(handle)
                self.session.edit("last", self.widen("last"))
                self.scenes.generation += 1
                self.scenes.ask()        # the 3D asks again (SceneBackend.rebuild_soon)
        self.center._launch = launched
        try:
            count = len(self.shown)
            self.session.edit("first", self.widen("first"))
            self.scenes.generation += 1
            self.scenes.ask()
            self.assertTrue(self.until(lambda: made and len(self.shown) > count and not self.scenes.busy()),
                            "the last scene came")
        finally:
            self.center._launch = launch
        self.assertEqual(len(self.shown), count + 1, "the answer of before was never taken")
        self.assertEqual({"first", "last"} & self.bodies(self.shown[-1]), {"first", "last"})
        np.testing.assert_array_equal(self.shown[-1]["triangles"][0], direct(self.session)[0][0])
        self.assertEqual(len(self.center.runner.all_processes()), 1, "no other process")

    def test_an_answer_of_a_project_changed_before_its_piece_is_dropped(self):
        held, piece = [], self.center.piece
        self.center.piece = lambda name, call, *args: held.append((call, args))
        try:
            self.scenes.ask()
            self.assertTrue(self.until(lambda: held), "the answer came, its piece held")
        finally:
            self.center.piece = piece
        self.scenes.generation += 1             # changed before the piece's turn: never taken
        for call, args in held:
            call(*args)
        self.assertEqual([], self.shown)
        self.assertFalse(self.scenes.busy())

    def test_the_bar_has_no_cancel_for_it_and_a_process_that_falls_says_so(self):
        sentences = []
        self.center.tell = sentences.append
        self.scenes.ask()
        self.assertTrue(self.until(lambda: self.shown and not self.scenes.busy()))
        count = len(self.shown)
        launch = self.center._launch

        def launched(handle):           # the warm process killed as soon as the job is sent to it
            launch(handle)
            row = next(r for r in self.center.rows() if r["slot"] == scene_job.SLOT)
            self.assertFalse(row["cancellable"], "a scene cancelled would leave a 3D of another project")
            for proc in self.center.runner.processes():
                proc.kill()
        self.center._launch = launched
        try:
            self.scenes.ask()
            self.assertTrue(self.until(lambda: sentences and not self.scenes.busy()))
        finally:
            self.center._launch = launch
        self.assertEqual(len(self.shown), count, "the scene of before stays")
        self.scenes.ask()
        self.assertTrue(self.until(lambda: len(self.shown) > count and not self.scenes.busy()))


if __name__ == "__main__":
    unittest.main()
