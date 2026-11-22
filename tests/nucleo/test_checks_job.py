"""R598, study 48 chapter 6 step 6: the checks as one job of the mechanism (app/checks_job.py), for the bridge's rows and
the Checks panel. Its rows are those of checks.gather and gather_session called directly on the same inputs, with and
without the year; the layouts do not travel (the layout's process keeps them, or lays out by itself what it does
not keep); the energy travels once; and, with real processes, what happens when the project changes while the checks
are on their way, when a layout is on its way, when the bar cancels them and when their process falls."""

import pickle
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path

import _setup  # noqa: F401

from _fixtures import capannone, clear_sky_meteo, mixed, write_cache
from meridiana.app import checks_job, jobs, layout_job, pipeline
from meridiana.app.session import ProjectSession, photo_of, project_from
from meridiana.app.work.center import Center
from meridiana.app.work.job import Context
from meridiana.core.rules import checks

POLL = 0.05


def ctx(kept=None):
    return Context(1, (0, 1), {} if kept is None else kept, lambda message: None, stop=threading.Event())


def direct(project, results, energy):
    """What the two old jobs gave: the bridge's rows and the panel's items, extras and notes."""
    return [vars(i) for i in checks.gather(project, results, energy)], checks_job.gather_session(project, results, energy)


def laid_session(p):
    s = ProjectSession(p)
    results, keys, _laid = jobs.layout_of(s.project)
    s.layout_done(s.generation, results, keys)
    return s


class SameRows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cache = Path(tempfile.mkdtemp())
        write_cache(clear_sky_meteo(), cls.cache)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.cache, ignore_errors=True)

    def check(self, s, kept):
        feed = checks_job.Feed(s, center=None)
        self.addCleanup(feed.close)
        request = feed._request()
        answer = checks_job.run(pickle.loads(pickle.dumps(request)), ctx(kept))
        self.assertNotIn("missing", answer)
        project = project_from(photo_of(s.project))
        bridge, (items, extras, notes) = direct(project, s.results, s.energy)
        self.assertEqual(answer["bridge"], bridge)
        self.assertEqual(answer["items"], items)
        self.assertEqual(answer["extras"], extras)
        self.assertEqual(answer["notes"], notes)
        self.assertEqual(answer["names"], checks.object_names(project))
        return answer

    def test_the_jobs_rows_are_those_of_gather_and_gather_session_with_and_without_the_year(self):
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
                self.assertTrue(answer["bridge"] and answer["items"])

    def test_a_failed_layout_stays_a_failure_of_the_checks(self):
        s = laid_session(capannone())
        sid = s.project.subfields[0].id
        s.results = dict(s.results, **{sid: ValueError("Broken layout")})
        answer = self.check(s, {})
        self.assertTrue(any(r["level"] == "fail" and "Broken layout" in r["text"] for r in answer["bridge"]))


class WhatTravels(unittest.TestCase):
    def test_the_layouts_never_and_the_energy_once(self):
        s = laid_session(mixed())
        s.energy_done(s.energy_asked(), {"notes": ["a note of the year"]})
        feed = checks_job.Feed(s, center=None)
        self.addCleanup(feed.close)
        first = feed._request()
        self.assertNotIn("layouts", first)
        self.assertEqual(set(first["keys"]), set(s.results))
        self.assertIs(first["photo"], s.photo(), "the photo, a reference")
        self.assertIn("energy", first)
        second = feed._request()
        self.assertNotIn("energy", second, "the process keeps it")
        self.assertEqual(second["energy_id"], first["energy_id"])
        weight = len(pickle.dumps(second)) - len(pickle.dumps(s.photo()))
        self.assertLess(weight, 5000, "beyond the photo, only the keys")
        kept = {}
        answer = checks_job.run(second, ctx(kept))
        self.assertEqual(answer, {"missing": {"layouts": [], "energy": True}}, "a process without the year asks")
        checks_job.run(first, ctx(kept))
        self.assertNotIn("missing", checks_job.run(second, ctx(kept)))
        self.assertTrue(kept["layouts"], "what it laid out kept for the layout's job too")

    def test_a_layout_of_before_is_asked_for_and_then_kept(self):
        s = laid_session(capannone())
        sid = s.project.subfields[0].id
        s.layout_keys = dict(s.layout_keys, **{sid: "a layout of before"})
        feed = checks_job.Feed(s, center=None)
        self.addCleanup(feed.close)
        kept = {}
        answer = checks_job.run(feed._request(), ctx(kept))
        self.assertEqual(answer["missing"]["layouts"], [sid])
        feed._send = {sid}
        again = feed._request()
        self.assertIs(again["layouts"][sid], s.results[sid])
        self.assertNotIn("missing", checks_job.run(again, ctx(kept)))
        self.assertIn((sid, "a layout of before"), kept["layouts"])


class InProcesses(unittest.TestCase):
    """The Feed with the window's center and real processes (the layout's, the checks at home in it)."""

    def setUp(self):
        self.posted = threading.Event()
        self.center = Center(self.posted.set)
        self.addCleanup(self.center.close)
        self.session = laid_session(mixed())
        self.feed = checks_job.Feed(self.session, self.center)
        self.addCleanup(self.feed.close)
        self.shown, self.failures = [], []
        self.feed.join("checks.test", self.shown.append, self.failures.append)

    def until(self, condition, seconds=60.0) -> bool:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.posted.clear()
            self.center.pump()
            if condition():
                return True
            self.posted.wait(POLL)
        return condition()

    def rows(self):
        return direct(project_from(photo_of(self.session.project)), self.session.results, self.session.energy)[0]

    def test_in_the_layouts_process_the_rows_follow_the_project_and_only_the_last_is_shown(self):
        self.center.warm(layout_job.KIND)
        self.assertTrue(self.until(lambda: self.shown), "the first checks")
        self.assertEqual(self.shown[-1]["bridge"], self.rows())
        self.assertEqual([p.name for p in self.center.runner.processes()], ["layout"], "in the layout's process")
        sf = self.session.project.subfields[0]
        launch, made = self.center._launch, []

        def launched(handle):           # a change while the checks are on their way: right after they start
            launch(handle)
            if handle.kind is checks_job.KIND and not made:
                made.append(handle)
                self.session.edit("rename", lambda p: setattr(p.subfields[0], "name", "Last name"))
        self.center._launch = launched
        try:
            self.session.edit("rename", lambda p: setattr(p.subfields[0], "name", "First name"))
            # the last answer itself, not only an idle feed: between the two checks the feed is idle for a moment
            # (seen under load on 22/11/2026: the last shown was still the project's first name)
            self.assertTrue(self.until(lambda: made and not self.feed.busy() and self.shown
                                       and self.shown[-1]["names"][("subfield", sf.id)] == "Last name"),
                            "the last checks came")
        finally:
            self.center._launch = launch
        names = [answer["names"][("subfield", sf.id)] for answer in self.shown]
        self.assertNotIn("First name", names, "the answer of before was never shown")
        self.assertEqual(names[-1], "Last name")
        self.assertEqual(self.shown[-1]["bridge"], self.rows())
        self.assertEqual(sf.name, "Last name")
        self.assertEqual(len(self.center.runner.all_processes()), 1, "no other process")

    def test_the_rows_are_in_the_windows_language(self):
        from meridiana import i18n
        self.addCleanup(i18n.setup, i18n.language())
        self.assertTrue(self.until(lambda: self.shown))
        for language in ("it", "en"):
            i18n.setup(language)
            count = len(self.shown)
            self.feed.ask(always=True)
            self.assertTrue(self.until(lambda n=count: len(self.shown) > n and not self.feed.busy()), language)
            self.assertEqual(self.shown[-1]["bridge"], self.rows(), language)

    def test_while_a_layout_is_on_its_way_the_checks_wait_for_it(self):
        self.assertTrue(self.until(lambda: self.shown))
        count = len(self.shown)
        layout = self.center.submit(layout_job.KIND, build=lambda: layout_job.request_of(self.session), settle=True)
        self.feed.ask()
        self.assertTrue(self.feed.busy() and self.feed._pending, "waiting for the layout")
        self.assertIsNone(self.feed._handle)
        layout.cancel()                 # gone without an answer: the checks waiting for it go
        self.assertTrue(self.until(lambda: len(self.shown) > count and not self.feed.busy()))

    def test_cancel_from_the_bar_leaves_the_checks_of_before(self):
        self.assertTrue(self.until(lambda: self.shown))
        before = self.feed.result
        self.session.edit("rename", lambda p: setattr(p.subfields[0], "name", "Cancelled"))
        self.assertTrue(self.until(lambda: any(r["slot"] == checks_job.SLOT for r in self.center.rows())))
        row = next(r for r in self.center.rows() if r["slot"] == checks_job.SLOT)
        self.assertTrue(row["cancellable"])
        self.center.cancel(self.center.find(row["id"]))
        self.assertTrue(self.until(lambda: not self.feed.busy(), 10))
        self.until(lambda: False, 1.0)
        self.assertIs(self.feed.result, before, "the checks of before stay")
        self.session.edit("rename", lambda p: setattr(p.subfields[0], "name", "Again"))
        self.assertTrue(self.until(lambda: self.feed.result is not before and not self.feed.busy()))
        self.assertEqual(self.feed.result["names"][("subfield", self.session.project.subfields[0].id)], "Again")

    def test_a_process_that_falls_says_so_and_the_next_change_asks_again(self):
        self.assertTrue(self.until(lambda: self.shown))
        before = self.feed.result
        launch = self.center._launch

        def launched(handle):           # the warm process killed as soon as the job is sent to it
            launch(handle)
            for proc in self.center.runner.processes():
                proc.kill()
        self.center._launch = launched
        try:
            self.session.edit("rename", lambda p: setattr(p.subfields[0], "name", "Fallen"))
            self.assertTrue(self.until(lambda: self.failures and not self.feed.busy()))
        finally:
            self.center._launch = launch
        self.assertIs(self.feed.result, before, "the checks of before stay")
        self.assertTrue(self.feed.error)
        self.session.edit("rename", lambda p: setattr(p.subfields[0], "name", "Risen"))
        self.assertTrue(self.until(lambda: self.feed.result is not before and not self.feed.busy()))
        self.assertEqual(self.feed.result["names"][("subfield", self.session.project.subfields[0].id)], "Risen")
        self.assertEqual(self.feed.result["bridge"], self.rows())


if __name__ == "__main__":
    unittest.main()
