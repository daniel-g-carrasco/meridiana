"""R598, study 48 chapter 6 steps 1 and 7: the plant after a change as a job of the mechanism (app/plant_job.py), at home
in the layout's process. Its plant is that of plant.build called directly on the same inputs, with and without the
year; the layouts do not travel and the year travels once; the checks read the same plant, made once in the process;
and, with real processes, what happens when the project changes while the plant is on its way, when the bar cancels
it and when its process falls."""

import dataclasses
import math
import pickle
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import _setup  # noqa: F401
import numpy as np

from _fixtures import capannone, clear_sky_meteo, mixed, write_cache
from meridiana.app import checks_job, jobs, layout_job, pipeline, plant_job
from meridiana.app.session import ProjectSession, photo_of, project_from
from meridiana.app.work.center import Center
from meridiana.app.work.job import Context
from meridiana.core.energy import faces, plant

POLL = 0.05


def ctx(kept=None):
    return Context(1, (0, 1), {} if kept is None else kept, lambda message: None, stop=threading.Event())


def plain(value):
    """A plant as plain data, arrays as lists, so that two plants made apart compare whole."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return (type(value).__name__, {f.name: plain(getattr(value, f.name)) for f in dataclasses.fields(value)})
    if isinstance(value, np.ndarray):
        return ("array", value.shape, [None if isinstance(x, float) and math.isnan(x) else x for x in value.ravel().tolist()])
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted(repr(plain(v)) for v in value)
    if isinstance(value, float) and math.isnan(value):
        return "nan"
    if hasattr(value, "__dict__") and not callable(value):
        return (type(value).__name__, plain(vars(value)))
    return value


def direct(session):
    """The plant as the page's QRunnable made it: plant.build on the session's layouts and year."""
    sim = (session.energy or {}).get("sim")
    hot = max(a["t_cell_max"] for a in sim.arrays) if sim is not None else None
    power = sim.hourly.p_dc.to_numpy() if sim is not None else None
    return plant.build(project_from(photo_of(session.project)), session.good_results(), t_cell_max_year=hot,
                       p_dc_hourly=power, exposure=faces.year_of(sim))


def laid_session(p):
    s = ProjectSession(p)
    results, keys, _laid = jobs.layout_of(s.project)
    s.layout_done(s.generation, results, keys)
    return s


def builds(s, center=None, pieces=()):
    return plant_job.Builds(s, center, pieces)


class SamePlant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cache = Path(tempfile.mkdtemp())
        write_cache(clear_sky_meteo(), cls.cache)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.cache, ignore_errors=True)

    def check(self, s, kept):
        request = builds(s)._request()
        answer = plant_job.run(pickle.loads(pickle.dumps(request)), ctx(kept))
        self.assertNotIn("missing", answer)
        self.assertEqual(plain(answer["state"]), plain(direct(s)))
        self.assertEqual(answer["key"], s.state_key(), "the process makes the window's state key")
        return answer

    def test_the_jobs_plant_is_that_of_plant_build_with_and_without_the_year(self):
        for p in (capannone(), mixed()):
            s = laid_session(p)
            with self.subTest(project=p.name, year=False):
                self.check(s, {})                       # a cold process: it lays out by itself
            good = s.good_results()
            energy = pipeline.compute(s.project, good, self.cache, fetch=False).as_dict()
            s.energy_done(s.energy_asked(), energy)
            self.assertTrue(s.energy.get("sim") is not None, "a year computed")
            with self.subTest(project=p.name, year=True):
                kept = {"layouts": {(sid, s.layout_keys[sid]): r for sid, r in good.items()}}
                answer = self.check(s, kept)            # the layout's process: the layouts it keeps
                self.assertTrue(answer["state"].year, "made at the conditions of the year")
                self.assertEqual(bool(answer["state"].strings), bool(p.energy.get("inverters")), "with inverters")

    def test_the_checks_and_the_plant_read_one_plant_made_once(self):
        s = laid_session(mixed())
        energy = pipeline.compute(s.project, s.good_results(), self.cache, fetch=False).as_dict()
        s.energy_done(s.energy_asked(), energy)
        for first in ("plant", "checks"):
            with self.subTest(first=first):
                feed = checks_job.Feed(s, center=None)          # a new process: the energy sent again
                self.addCleanup(feed.close)
                kept, made = {}, []
                real = plant.build

                def counted(*args, made=made, real=real, **kwargs):
                    made.append(True)
                    return real(*args, **kwargs)
                with mock.patch.object(plant, "build", counted):
                    asks = [("plant", builds(s)._request()), ("checks", feed._request())]
                    for name, request in (asks if first == "plant" else asks[::-1]):
                        answer = (plant_job if name == "plant" else checks_job).run(pickle.loads(pickle.dumps(request)),
                                                                                    ctx(kept))
                        self.assertNotIn("missing", answer)
                        if name == "plant":
                            state = answer["state"]
                        else:
                            items = answer["items"]
                self.assertEqual(made, [True], "one plant for the two jobs")
                self.assertEqual(plain(state), plain(direct(s)))
                expected = checks_job.gather_session(project_from(photo_of(s.project)), s.results, s.energy)[0]
                self.assertEqual(items, expected, "the checks of the plant made once are those of before")

    def test_another_project_or_language_is_another_plant(self):
        from meridiana import i18n
        self.addCleanup(i18n.setup, i18n.language())
        s = laid_session(capannone())
        kept = {}
        plant_job.run(builds(s)._request(), ctx(kept))
        state = kept["plant"]["state"]
        plant_job.run(builds(s)._request(), ctx(kept))
        self.assertIs(kept["plant"]["state"], state, "the same inputs: the plant kept")
        s.edit("rename", lambda p: setattr(p.subfields[0], "name", "Another"))
        plant_job.run(builds(s)._request(), ctx(kept))
        self.assertIsNot(kept["plant"]["state"], state, "another photo: another plant")
        state = kept["plant"]["state"]
        i18n.setup("it" if i18n.language() != "it" else "en")
        plant_job.run(builds(s)._request(), ctx(kept))
        self.assertIsNot(kept["plant"]["state"], state, "another language: another plant (its notes are words)")


class WhatTravels(unittest.TestCase):
    def test_the_layouts_never_and_the_year_once(self):
        s = laid_session(mixed())
        owner = builds(s)
        first = owner._request()
        self.assertNotIn("layouts", first)
        self.assertEqual(set(first["keys"]), set(s.good_results()))
        self.assertIs(first["photo"], s.photo(), "the photo, a reference")
        self.assertIn("year", first)
        second = owner._request()
        self.assertNotIn("year", second, "the process keeps it")
        self.assertEqual(second["year_id"], first["year_id"])
        weight = len(pickle.dumps(second)) - len(pickle.dumps(s.photo()))
        self.assertLess(weight, 5000, "beyond the photo, only the keys")
        kept = {}
        answer = plant_job.run(second, ctx(kept))
        self.assertEqual(answer, {"missing": {"layouts": [], "year": True}}, "a process without the year asks")
        plant_job.run(first, ctx(kept))
        self.assertNotIn("missing", plant_job.run(second, ctx(kept)))
        self.assertTrue(kept["layouts"], "what it laid out kept for the layout's job too")
        s.energy_done(s.energy_asked(), {"notes": ["another year"]})
        self.assertIn("year", owner._request(), "another energy: its year sent")

    def test_a_layout_of_before_is_asked_for_and_then_kept(self):
        s = laid_session(capannone())
        sid = s.project.subfields[0].id
        s.layout_keys = dict(s.layout_keys, **{sid: "a layout of before"})
        owner = builds(s)
        kept = {}
        answer = plant_job.run(owner._request(), ctx(kept))
        self.assertEqual(answer["missing"]["layouts"], [sid])
        owner._send = {sid}
        again = owner._request()
        self.assertIs(again["layouts"][sid], s.results[sid])
        self.assertNotIn("missing", plant_job.run(again, ctx(kept)))
        self.assertIn((sid, "a layout of before"), kept["layouts"])


class QueuedPieces(unittest.TestCase):
    def test_each_queued_piece_rechecks_the_project_and_ends_busy(self):
        s = laid_session(capannone())
        center = mock.NonCallableMock()
        pieces, shown, signals = [], [], []
        center.piece.side_effect = lambda name, call, *args: pieces.append((call, args))
        owner = plant_job.Builds(s, center,
                                (("plant.show", lambda state, mark: shown.append(state)),
                                 ("plant.signal", lambda state, mark: signals.append(True))))
        owner._request()
        owner._done({"state": "old plant", "key": s.state_key()}, False)
        self.assertTrue(owner.busy())
        self.assertEqual(len(pieces), 2)
        s.edit("rename", lambda p: setattr(p, "name", "Changed"))
        for call, args in pieces:
            call(*args)
        self.assertEqual(shown, [])
        self.assertEqual(signals, [])
        self.assertFalse(owner.busy())

    def test_a_change_between_two_pieces_prevents_the_second_delivery(self):
        s = laid_session(capannone())
        center = mock.NonCallableMock()
        pieces, shown = [], []
        center.piece.side_effect = lambda name, call, *args: pieces.append((call, args))
        owner = plant_job.Builds(s, center,
                                (("first", lambda state, mark: s.edit("rename", lambda p: setattr(p, "name", "B"))),
                                 ("second", lambda state, mark: shown.append(state))))
        owner._request()
        owner._done({"state": "old", "key": s.state_key()}, False)
        for call, args in pieces:
            call(*args)
        self.assertEqual(shown, [])
        self.assertFalse(owner.busy())


class InProcesses(unittest.TestCase):
    """Builds with the window's center and real processes (the layout's, the plant at home in it)."""

    def setUp(self):
        self.posted = threading.Event()
        self.center = Center(self.posted.set)
        self.addCleanup(self.center.close)
        self.session = laid_session(mixed())
        self.shown, self.told = [], []
        self.builds = plant_job.Builds(self.session, self.center,
                                       (("plant.test", lambda state, mark: self.shown.append(state)),),
                                       changed=lambda: self.told.append(True))
        self.addCleanup(self.builds.close)

    def until(self, condition, seconds=60.0) -> bool:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.posted.clear()
            self.center.pump()
            if condition():
                return True
            self.posted.wait(POLL)
        return condition()

    def names(self, state):
        return {u.name for u in state.units}

    def test_in_the_layouts_process_the_plant_follows_the_project_and_only_the_last_is_taken(self):
        self.center.warm(layout_job.KIND)
        self.builds.ask()
        self.assertTrue(self.until(lambda: self.shown and not self.builds.busy()), "the first plant")
        self.assertEqual(plain(self.shown[-1]), plain(direct(self.session)))
        self.assertEqual([p.name for p in self.center.runner.processes()], ["layout"], "in the layout's process")
        self.assertTrue(self.center.stats()["by_name"].get("plant.test") is not None, "taken as a piece")
        launch, made = self.center._launch, []

        def launched(handle):           # a change while the plant is on its way: right after it starts
            launch(handle)
            if handle.kind is plant_job.KIND and not made:
                made.append(handle)
                self.session.edit("name", lambda p: p.energy["inverters"][0].__setitem__("name", "Last name"))
                self.builds.ask()        # the page asks again (PlantBackend._on_change)
        self.center._launch = launched
        try:
            count = len(self.shown)
            self.session.edit("name", lambda p: p.energy["inverters"][0].__setitem__("name", "First name"))
            self.builds.ask()
            self.assertTrue(self.until(lambda: made and len(self.shown) > count and not self.builds.busy()),
                            "the last plant came")
        finally:
            self.center._launch = launch
        taken = " ".join(n for state in self.shown[count:] for n in self.names(state))
        self.assertNotIn("First name", taken, "the answer of before was never taken")
        self.assertIn("Last name", " ".join(self.names(self.shown[-1])))
        self.assertEqual(plain(self.shown[-1]), plain(direct(self.session)))
        self.assertEqual(len(self.center.runner.all_processes()), 1, "no other process")

    def test_cancel_from_the_bar_leaves_the_plant_of_before(self):
        self.builds.ask()
        self.assertTrue(self.until(lambda: self.shown and not self.builds.busy()))
        count = len(self.shown)
        self.builds.ask()
        self.assertTrue(self.until(lambda: any(r["slot"] == plant_job.SLOT for r in self.center.rows())))
        row = next(r for r in self.center.rows() if r["slot"] == plant_job.SLOT)
        self.assertTrue(row["cancellable"])
        self.assertEqual(row["title"], "Plant")
        self.center.cancel(self.center.find(row["id"]))
        self.assertTrue(self.until(lambda: not self.builds.busy(), 10))
        self.until(lambda: False, 1.0)
        self.assertEqual(len(self.shown), count, "nothing taken after Cancel")
        self.builds.ask()
        self.assertTrue(self.until(lambda: len(self.shown) > count and not self.builds.busy()), "asked again")

    def test_a_process_that_falls_says_so_and_the_next_request_works(self):
        sentences = []
        self.center.tell = sentences.append
        self.builds.ask()
        self.assertTrue(self.until(lambda: self.shown and not self.builds.busy()))
        count = len(self.shown)
        launch = self.center._launch

        def launched(handle):           # the warm process killed as soon as the job is sent to it
            launch(handle)
            for proc in self.center.runner.processes():
                proc.kill()
        self.center._launch = launched
        try:
            self.builds.ask()
            self.assertTrue(self.until(lambda: sentences and not self.builds.busy()))
        finally:
            self.center._launch = launch
        self.assertEqual(len(self.shown), count, "the plant of before stays")
        self.builds.ask()
        self.assertTrue(self.until(lambda: len(self.shown) > count and not self.builds.busy()))
        self.assertEqual(plain(self.shown[-1]), plain(direct(self.session)))


if __name__ == "__main__":
    unittest.main()
