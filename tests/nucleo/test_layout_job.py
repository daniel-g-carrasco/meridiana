"""R598, study 48 chapter 6 step 1: the layout of a change as a job of the mechanism (app/layout_job.py). Its layouts are
those of jobs.layout_of called directly (the same keys, the same modules); what travels is only what the window does
not hold; the strings it realigns are those session.realign_strings makes, applied without a snapshot on the window's
thread; and the session tells the views of a layout a piece each when the window gives it its pieces."""

import threading
import time
import unittest

import _setup  # noqa: F401

from _fixtures import mixed
from meridiana.app import jobs, layout_job
from meridiana.app.session import ProjectSession, needs_layout, photo_of
from meridiana.app.work.center import Center
from meridiana.app.work.job import Context
from meridiana.core.model import model


def project():
    p = model.Project(name="Layout job")
    p.buildings.append(model.Building(id="b1", name="Shed", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]]))
    p.subfields.append(model.SubField(id="s1", name="South", building="b1", filled=True,
                                      ring=[[1, 1], [39, 1], [39, 19], [1, 19]], params={"tilt": 15.0}))
    p.buildings.append(model.Building(id="b2", name="Store", footprint=[[50, 0], [70, 0], [70, 20], [50, 20]]))
    p.subfields.append(model.SubField(id="s2", name="North", building="b2", filled=True,
                                      ring=[[51, 1], [69, 1], [69, 19], [51, 19]], params={"tilt": 10.0}))
    return p


def ctx(kept=None):
    return Context(1, (0, 1), {} if kept is None else kept, lambda message: None, stop=threading.Event())


def modules(results):
    return {sid: [m.key for m in r.modules] for sid, r in results.items() if not isinstance(r, Exception)}


class LayoutJob(unittest.TestCase):
    def test_the_jobs_layout_is_that_of_layout_of(self):
        for p in (project(), mixed()):
            s = ProjectSession(p)
            answer = layout_job.run(layout_job.request_of(s), ctx())
            direct, keys, _laid = jobs.layout_of(model.Project.from_json(photo_of(p), check=False))
            self.assertEqual(answer["keys"], keys)
            self.assertEqual(set(answer["results"]), set(direct), "nothing held: every layout sent")
            self.assertEqual(modules(answer["results"]), modules(direct))
            self.assertEqual({sid: [m.corners for m in r.modules] for sid, r in answer["results"].items()},
                             {sid: [m.corners for m in r.modules] for sid, r in direct.items()})

    def test_what_the_window_holds_stays_its_own_and_only_the_changed_travel(self):
        s = ProjectSession(project())
        kept = {}
        first = layout_job.run(layout_job.request_of(s), ctx(kept))
        s.layout_done(s.generation, layout_job.results_of(first, s) or first["results"], first["keys"])
        mine = dict(s.results)
        s.edit("smaller", lambda p: setattr(p.subfields[1], "ring", [[51, 1], [60, 1], [60, 19], [51, 19]]))
        s.generation += 1
        answer = layout_job.run(layout_job.request_of(s), ctx(kept))
        self.assertEqual(set(answer["results"]), {"s2"}, "the sub-field unchanged is not sent again")
        self.assertEqual(answer["laid"], ["s2"], "and not laid again in the process: it kept it")
        results = layout_job.results_of(answer, s)
        self.assertIs(results["s1"], mine["s1"], "the window keeps its own result")
        direct, keys, _laid = jobs.layout_of(s.project)
        self.assertEqual(modules(results), modules(direct))
        self.assertEqual(answer["keys"], keys)
        s.layout_keys = {}                  # the session no longer holds what the job did not send
        self.assertIsNone(layout_job.results_of(answer, s))

    def test_a_cold_process_lays_out_what_it_does_not_keep_and_sends_only_what_the_window_lacks(self):
        s = ProjectSession(project())
        results, keys, _laid = jobs.layout_of(s.project)
        s.layout_done(s.generation, results, keys)
        answer = layout_job.run(layout_job.request_of(s), ctx())
        self.assertEqual(answer["results"], {})
        self.assertEqual(sorted(answer["laid"]), ["s1", "s2"])

    def test_the_kind_follows_the_topics_that_can_move_a_module(self):
        topics = ["project:text", "project:privacy", "project:geometry", "project:subfields", "project:fire",
                  "project:site", "project:energy", "project:rules", "project:variants", "project:underlays",
                  "project:report", "project:defaults"]
        for topic in topics:
            self.assertEqual(layout_job.KIND.follows({topic}), needs_layout({topic}), topic)
        self.assertEqual(layout_job.KIND.where, "process")
        self.assertEqual(layout_job.KIND.on_change, "restart")
        self.assertGreater(layout_job.KIND.keep_warm, 3600)


class Strings(unittest.TestCase):
    """R442 with the strings realigned by the job: the same as session.realign_strings, applied as amend does."""

    def strung(self, reference: bool):
        s = ProjectSession(project())
        results, keys, _laid = jobs.layout_of(s.project)
        s.layout_done(s.generation, results, keys)
        mods = results["s1"].modules
        s.edit("strings", lambda p: p.energy.update(strings={"runs": [
            {"inverter": 1, "mppt": 1, "modules": [f"s1/{m.key}" for m in mods[:10]]},
            {"inverter": 1, "mppt": 2, "modules": [f"s2/{m.key}" for m in results["s2"].modules[:4]]}]}))
        gone = [m.key for m in mods[:3]]
        s.edit("out", lambda p: p.subfields[0].removed.extend(gone))
        s.mark_saved()                      # saved as it is: what the program writes by itself keeps it saved
        told = []
        s.subscribe(told.append)
        s.generation += 1
        if reference:
            results, keys, _laid = jobs.layout_of(s.project, s.known_layouts())
            s.layout_done(s.generation, results, keys)
        else:
            request = layout_job.request_of(s)
            answer = layout_job.run(request, ctx())
            s.layout_done(answer["generation"], layout_job.results_of(answer, s), answer["keys"],
                          answer["strings"], request["photo"])
        return s, told

    def test_the_strings_realigned_by_the_job_are_those_of_the_session(self):
        reference, told_reference = self.strung(True)
        by_job, told_by_job = self.strung(False)
        self.assertEqual(by_job.realigned, [("1.1.1", 3, ["South"])])
        self.assertEqual(by_job.realigned, reference.realigned)
        self.assertEqual(by_job.project.energy["strings"], reference.project.energy["strings"])
        same = lambda s: {k: v for k, v in photo_of(s.project).items() if k != "bim_id"}    # noqa: E731
        self.assertEqual(same(by_job), same(reference), "the project as the session's realign leaves it")
        self.assertEqual(by_job.photo(), photo_of(by_job.project), "the photo is the project in hand")
        self.assertEqual(len(told_by_job), 1, "the layout and the strings told once")
        self.assertEqual(told_by_job, told_reference)
        self.assertFalse(reference.dirty())
        self.assertFalse(by_job.dirty(), "still saved, as amend leaves it")
        self.assertFalse(by_job.undo.can_redo())
        self.assertEqual(by_job.undo.count(), reference.undo.count(), "no undo step for what the program wrote")

    def test_a_photo_no_longer_in_hand_is_realigned_by_the_session(self):
        s, _told = self.strung(True)
        request = layout_job.request_of(s)
        answer = layout_job.run(request, ctx())
        s.edit("rename", lambda p: setattr(p, "name", "Another"))          # the photo in hand is another
        s.layout_done(s.generation, layout_job.results_of(answer, s), answer["keys"], answer["strings"],
                      request["photo"])
        self.assertEqual(s.photo(), photo_of(s.project))

    def test_a_project_just_opened_is_not_realigned(self):
        s = ProjectSession(project())
        results, keys, _laid = jobs.layout_of(s.project)
        runs = [{"inverter": 1, "mppt": 1, "modules": ["s1/" + m.key for m in results["s1"].modules[:5]] + ["s1/gone"]}]
        s.project.energy["strings"] = {"runs": runs}
        s.take(s.project, None, saved=True)
        request = layout_job.request_of(s)
        answer = layout_job.run(request, ctx())
        self.assertIsNotNone(answer["strings"], "the job realigns whatever it is given")
        s.layout_done(s.generation, layout_job.results_of(answer, s) or answer["results"], answer["keys"],
                      answer["strings"], request["photo"])
        self.assertEqual(s.realigned, [])
        self.assertEqual(s.project.energy["strings"]["runs"], runs)
        self.assertFalse(s.dirty())


class Pieces(unittest.TestCase):
    """The views told of a layout a piece each, on the window's turns (session.pieces = Center.piece)."""

    def setUp(self):
        self.center = Center(lambda: None)
        self.addCleanup(self.center.close)

    def test_the_views_of_a_layout_are_told_one_per_piece_the_first_at_once_listeners_first(self):
        s = ProjectSession(project())
        s.pieces = self.center.piece
        heard = []
        s.subscribe(lambda t: heard.append(("tree", t)))
        s.subscribe(lambda t: heard.append(("plan", t)), at_once=True)
        results, keys, _laid = jobs.layout_of(s.project)
        s.layout_done(s.generation, results, keys, pieces=True)
        self.assertEqual(heard, [], "nobody told before the window's turn")
        self.assertTrue(s.telling())
        while self.center.pump(budget=0.0):
            pass
        self.assertEqual([h[0] for h in heard], ["plan", "tree"])
        self.assertIn("layout:s1", heard[0][1])
        self.assertFalse(s.telling())
        self.assertTrue(all(name.startswith("tell:") for name in self.center.stats()["by_name"]))

    def test_a_change_meanwhile_tells_the_views_still_waiting_first(self):
        s = ProjectSession(project())
        s.pieces = self.center.piece
        heard = []
        s.subscribe(lambda t: heard.append(("a", sorted(t))))
        s.subscribe(lambda t: heard.append(("b", sorted(t))))
        results, keys, _laid = jobs.layout_of(s.project)
        s.layout_done(s.generation, results, keys, pieces=True)
        self.center.pump(budget=0.0)                    # "a" told, "b" waits for its piece
        self.assertEqual([h[0] for h in heard], ["a"])
        s.select("subfield", "s1")
        self.assertEqual([(h[0], "selection" in h[1]) for h in heard], [("a", False), ("b", False), ("a", True),
                                                                        ("b", True)],
                         "b heard of the layout before the selection")
        start = time.monotonic()
        while self.center.pump(budget=0.0) and time.monotonic() - start < 5:
            pass
        self.assertEqual(len(heard), 4, "the piece left behind tells nobody twice")

    def test_without_pieces_every_view_is_told_at_once(self):
        s = ProjectSession(project())
        heard = []
        s.subscribe(heard.append)
        results, keys, _laid = jobs.layout_of(s.project)
        s.layout_done(s.generation, results, keys, pieces=True)
        self.assertEqual(len(heard), 1)


class InAProcess(unittest.TestCase):
    def test_the_job_in_its_process_gives_the_layout_of_layout_of(self):
        posted = threading.Event()
        center = Center(posted.set)
        self.addCleanup(center.close)
        s = ProjectSession(mixed())
        got = []
        center.submit(layout_job.KIND, layout_job.request_of(s), on_done=lambda r, stale: got.append(r),
                      on_failed=lambda k, text: got.append(text))
        end = time.monotonic() + 60
        while not got and time.monotonic() < end:
            posted.wait(0.05)
            posted.clear()
            center.pump()
        self.assertTrue(got and isinstance(got[0], dict), got)
        direct, keys, _laid = jobs.layout_of(s.project)
        self.assertEqual(got[0]["keys"], keys)
        self.assertEqual(modules(got[0]["results"]), modules(direct))


if __name__ == "__main__":
    unittest.main()
