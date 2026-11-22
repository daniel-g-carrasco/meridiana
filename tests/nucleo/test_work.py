"""The mechanism of the heavy jobs without Qt (R598, docs/studio/48-lavori-pesanti.md): the center, its processes and
threads, the time left, the store, the photo of the session. The jobs are the sample of app/work/sample.py, in real
processes; every test closes its center and checks that no process is left."""

import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import _setup  # noqa: F401  (src on the path)

from meridiana.app.session import ProjectSession
from meridiana.app.work import job as work_job
from meridiana.app.work import runner as work_runner
from meridiana.app.work import sample, store
from meridiana.app.work.center import Center, size_text
from meridiana.app.work.eta import Eta
from meridiana.core.compute import resources
from meridiana.i18n import _

POLL = 0.02             # seconds: how often a condition that comes without a post is looked at again


def alive(pid) -> bool:
    """Whether a process is still there (Windows: its exit code is still STILL_ACTIVE)."""
    if pid is None:
        return False
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel.OpenProcess(0x1000, False, int(pid))         # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class Base(unittest.TestCase):
    def setUp(self):
        self.posts = 0
        self.posted = threading.Event()
        self.center = Center(self.post)
        self.pids = []                  # every process the test met: none may outlive the center
        self.addCleanup(self.no_process_left)
        self.addCleanup(self.center.close)

    def post(self):
        """The owner's wake-up, as the window's queued signal: here an event the test waits on."""
        self.posts += 1
        self.posted.set()

    def until(self, condition, seconds=30.0) -> bool:
        """Pumps as the window does when the center posts, until `condition()`; what comes without a post (a process
        ending) is looked at again every POLL seconds."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.posted.clear()
            self.center.pump()
            self.remember()
            if condition():
                return True
            self.posted.wait(POLL)
        return condition()

    def remember(self):
        for proc in self.center.runner.all_processes():
            for pid in (proc.popen.pid if proc.popen is not None else None, proc.pid):
                if pid is not None and pid not in self.pids:
                    self.pids.append(pid)

    def no_process_left(self):
        gone = threading.Event()
        end = time.monotonic() + 5
        while time.monotonic() < end and any(alive(p) for p in self.pids):
            gone.wait(POLL)             # a process killed with its launcher ends a moment after it
        self.assertEqual([p for p in self.pids if alive(p)], [], "processes left after close()")

    def submit(self, kind=None, request=None, **calls):
        got = {"partial": [], "done": [], "failed": []}
        if request is None and "build" not in calls:
            request = {"steps": 4, "pause": 0.02}
        handle = self.center.submit(
            kind or sample.kind(), request,
            on_partial=lambda k, d: got["partial"].append((k, d)),
            on_done=lambda r, stale: got["done"].append((r, stale)),
            on_failed=lambda k, text: got["failed"].append(text), **calls)
        return handle, got


class Jobs(Base):
    def test_a_job_runs_in_a_process_and_says_its_parts_and_its_end(self):
        handle, got = self.submit()
        self.assertTrue(self.until(lambda: got["done"]), got)
        result, stale = got["done"][0]
        self.assertEqual(result["parts"], [0, 1, 2, 3])
        self.assertNotEqual(result["pid"], os.getpid())
        self.assertFalse(stale)
        self.assertEqual(sorted(got["partial"]), [(f"part {i}", i * i) for i in range(4)])
        self.assertEqual(handle.state, "done")
        self.assertEqual(self.center.rows(), [])

    def test_only_the_last_job_of_a_slot_counts(self):
        first, got_first = self.submit(request={"steps": 50, "pause": 0.05})
        second, got_second = self.submit(request={"steps": 3, "pause": 0.01, "tag": "second"})
        self.assertEqual(first.state, "cancelled")
        self.assertEqual([r["id"] for r in self.center.rows()], [second.id])
        self.assertTrue(self.until(lambda: got_second["done"]))
        self.assertEqual(got_second["done"][0][0]["tag"], "second")
        self.until(lambda: False, 0.3)
        self.assertEqual(got_first["done"], [])
        self.assertEqual(got_first["partial"], [])

    def test_cancel_with_grace_the_row_goes_at_once_and_the_process_stays_warm(self):
        kind = sample.kind(keep_warm=30)
        handle, got = self.submit(kind, {"steps": 200, "pause": 0.05})
        self.assertTrue(self.until(lambda: self.center.rows() and self.center.rows()[0]["fraction"] is not None))
        told = []
        self.center.subscribe(lambda: told.append(self.center.rows()))
        self.center.cancel(handle)
        self.assertEqual(handle.state, "cancelled")
        self.assertEqual(told[-1], [], "the listeners are told at once, the row gone")
        proc = self.center.runner.processes()[0]
        self.assertTrue(self.until(lambda: proc.run is None, 3), "the process stopped at its next checkpoint")
        self.assertTrue(proc.alive)
        self.assertIsNone(proc.popen.poll(), "stopped with grace, not killed")
        self.assertEqual(got["done"], [])

    def test_a_job_deaf_to_cancel_is_killed_after_the_grace(self):
        handle, got = self.submit(request={"steps": 100, "pause": 0.2, "deaf": True})
        self.assertTrue(self.until(lambda: self.center.rows() and self.center.rows()[0]["state"] == "running"))
        proc = self.center.runner.processes()[0]
        start = time.monotonic()
        self.center.cancel(handle)
        self.assertEqual(self.center.rows(), [])
        self.assertTrue(self.until(lambda: proc.popen.poll() is not None, work_runner.GRACE_S + 3))
        self.assertGreaterEqual(time.monotonic() - start, work_runner.GRACE_S - 0.1)
        self.assertEqual(got["failed"], [], "a job cancelled is not a failure")

    def test_over_its_memory_a_job_stops_with_a_sentence(self):
        kind = sample.kind(memory=200 * resources.MIB)
        handle, got = self.submit(kind, {"steps": 100, "pause": 0.05, "hog": 400})
        self.assertTrue(self.until(lambda: got["failed"], 20), handle.state)
        self.assertEqual(handle.state, "failed")
        self.assertEqual(got["failed"][0], _("{title} needed more memory than allowed ({limit}) and was stopped.")
                         .format(title=_("Counting"), limit=size_text(200 * resources.MIB)))
        self.assertGreater(handle.peak_memory, 200 * resources.MIB)
        self.assertEqual(self.center.rows(), [])

    def test_a_warm_process_is_used_again_with_what_it_kept(self):
        kind = sample.kind(keep_warm=30)
        _first, got = self.submit(kind)
        self.assertTrue(self.until(lambda: got["done"]))
        _second, again = self.submit(kind)
        self.assertTrue(self.until(lambda: again["done"]))
        self.assertEqual(again["done"][0][0]["pid"], got["done"][0][0]["pid"])
        self.assertEqual(again["done"][0][0]["runs"], 2, "ctx.kept lives with the process")

    def test_a_kind_at_home_in_another_runs_in_its_process_with_what_it_kept(self):
        # the checks in the layout's process (Kind.home): its process and its ctx.kept, its own slot and name
        host = sample.kind(name="host", keep_warm=30)
        guest = sample.kind(name="guest", keep_warm=30, home="host")
        self.assertEqual((host.family, guest.family), ("host", "host"))
        _first, got = self.submit(host)
        self.assertTrue(self.until(lambda: got["done"]))
        _second, again = self.submit(guest)
        self.assertTrue(self.until(lambda: again["done"]))
        self.assertEqual(again["done"][0][0]["pid"], got["done"][0][0]["pid"], "the host's process")
        self.assertEqual(again["done"][0][0]["runs"], 2, "with what the host kept")
        self.assertIn("guest.on_done", self.center.stats()["by_name"], "timed under its own name")
        self.assertEqual([p.name for p in self.center.runner.processes()], ["host"])
        self.center.warm(guest)                             # the host's process is there: nothing more
        self.assertEqual(len(self.center.runner.processes()), 1)

    def test_a_warm_job_waits_for_its_busy_process_instead_of_starting_a_cold_one(self):
        host = sample.kind(name="host", keep_warm=30)
        guest = sample.kind(name="guest", keep_warm=30, home="host", settle=0.01)
        _first, got = self.submit(host, {"steps": 8, "pause": 0.1})
        self.assertTrue(self.until(lambda: self.center.runner.busy(host)))
        waiting, again = self.submit(guest, {"steps": 1, "pause": 0.01}, settle=True)
        self.assertTrue(self.until(lambda: got["done"] or again["done"]))
        self.assertTrue(got["done"] and not again["done"], "the guest waited for the host's run")
        self.assertTrue(self.until(lambda: again["done"]))
        self.assertEqual(again["done"][0][0]["pid"], got["done"][0][0]["pid"], "in the host's warm process")
        self.assertEqual(len(self.center.runner.all_processes()), 1, "no cold process started")
        self.assertEqual(waiting.state, "done")

    def test_a_job_that_fails_says_it_and_the_detail_goes_to_the_log(self):
        with mock.patch("meridiana.app.platform.log.complain") as complain:
            _handle, got = self.submit(request={"steps": 4, "pause": 0.01, "fail": 2})
            self.assertTrue(self.until(lambda: got["failed"]))
        self.assertIn("the sample failed at part 2", got["failed"][0])
        self.assertTrue(complain.called)

    def test_the_processes_of_a_job_stay_warm_from_its_end_each_with_its_share(self):
        # the share of process 0 ends at once, that of process 1 after 1,5 s: process 0 waits from the job's end,
        # not from its own (0,6 s), and the next job finds both warm, each on the share it had
        kind = sample.kind(processes=2, keep_warm=0.6)
        with mock.patch.dict(os.environ, {"MERIDIANA_WORKERS": "2"}):
            seen = []
            for _round in range(2):
                _handle, got = self.submit(kind, {"steps": 2, "pause": 0.01, "slow": {1: 1.5}})
                self.assertTrue(self.until(lambda got=got: got["done"]))
                seen.append([(r["pid"], tuple(r["parts"]), r["runs"]) for r in got["done"][0][0]])
        self.assertEqual(seen[1], [(pid, parts, 2) for pid, parts, _runs in seen[0]],
                         "the same processes, warm, each with its share")

    def test_a_job_refused_says_the_users_sentence_alone(self):
        for where in ("process", "thread"):
            with self.subTest(where=where):
                handle, got = self.submit(sample.kind(where=where), {"steps": 4, "pause": 0.01, "refuse": 1})
                self.assertTrue(self.until(lambda got=got: got["failed"]))
                self.assertEqual(got["failed"], ["the sample refused at part 1, as asked"])
                self.assertEqual(handle.state, "failed")

    def test_the_progress_of_more_processes_is_summed_and_every_part_done_once(self):
        with mock.patch.dict(os.environ, {"MERIDIANA_WORKERS": "2"}):
            handle, got = self.submit(sample.kind(processes=2), {"steps": 9, "pause": 0.01})
        self.assertTrue(self.until(lambda: got["done"]))
        results = got["done"][0][0]
        self.assertEqual(len(results), 2)
        self.assertNotEqual(results[0]["pid"], results[1]["pid"])
        self.assertEqual(sorted(results[0]["parts"] + results[1]["parts"]), list(range(9)))
        # the sum, told by hand on a job whose processes sleep
        with mock.patch.dict(os.environ, {"MERIDIANA_WORKERS": "2"}):
            handle, _got = self.submit(sample.kind(processes=2), {"steps": 4, "pause": 5})
        job = self.center._jobs[handle.id]
        self.assertTrue(self.until(lambda: len(job.shares) == 2))
        first, second = job.runs
        self.center._incoming(("progress", first, 1, 2, ""))
        self.center.pump()
        self.assertAlmostEqual(self.center.rows()[0]["fraction"], 1 / 4)
        self.center._incoming(("progress", second, 2, 2, ""))
        self.center.pump()
        self.assertAlmostEqual(self.center.rows()[0]["fraction"], 3 / 4)
        job.shares.pop(1)               # one process not heard yet: it counts as the others
        self.assertAlmostEqual(self.center.rows()[0]["fraction"], 1 / 4)

    def test_a_thread_job_runs_beside_the_owner(self):
        kind = sample.kind(where="thread")
        handle, got = self.submit(kind)
        self.assertTrue(self.until(lambda: got["done"]))
        self.assertEqual(got["done"][0][0]["pid"], os.getpid())
        self.assertEqual(len(got["partial"]), 4)
        handle, got = self.submit(kind, {"steps": 100, "pause": 0.02})
        self.assertTrue(self.until(lambda: got["partial"]))
        self.center.cancel(handle)
        self.until(lambda: False, 0.2)
        seen = len(got["partial"])
        self.until(lambda: False, 0.2)
        self.assertEqual(len(got["partial"]), seen, "nothing heard after Cancel")
        self.assertEqual(got["done"], [])


class Launcher(Base):
    """The processes are started by the runner's launcher, never on the owner's thread (CreateProcess costs 10-30 ms
    on Windows): a slow start is held here by an event."""

    def held(self):
        go, spawned = threading.Event(), []
        real = work_runner.Proc.spawn

        def slow(proc):
            spawned.append(proc.name)
            go.wait(10)
            real(proc)
        patch = mock.patch.object(work_runner.Proc, "spawn", slow)
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(go.set)
        return go, spawned

    def test_submit_returns_before_the_process_exists(self):
        go, spawned = self.held()
        self.center.reset_stats()
        start = time.perf_counter()
        handle, got = self.submit()
        spent = time.perf_counter() - start
        self.assertLess(spent, 0.05, "submit did not wait for the process")
        longest, name = self.center.stats()["longest_call"]
        self.assertEqual(name, "submit:count")
        self.assertLess(longest, 0.005)
        self.assertEqual(handle.state, "waiting")
        go.set()
        self.assertTrue(self.until(lambda: got["done"]))
        self.assertEqual(spawned, ["count"])

    def test_a_job_cancelled_before_its_process_starts_never_starts_it(self):
        go, spawned = self.held()
        first, _got = self.submit(sample.kind(name="first"), {"steps": 100, "pause": 0.05})
        self.assertTrue(self.until(lambda: spawned == ["first"], 5), "the first is being started")
        second, got = self.submit(sample.kind(name="second"))
        self.center.cancel(second)
        self.center.cancel(first)
        go.set()
        self.assertTrue(self.until(lambda: not self.center.runner.processes()
                                   or all(p.run is None for p in self.center.runner.processes()), 10))
        self.until(lambda: False, 0.3)
        self.assertEqual(spawned, ["first"], "the second was dropped before its turn")
        self.assertEqual(got["done"], [])

    def test_close_waits_for_a_process_being_born_and_ends_it(self):
        go, spawned = self.held()
        self.submit(sample.kind(name="first"), {"steps": 100, "pause": 0.05})
        self.assertTrue(self.until(lambda: spawned == ["first"], 5))
        self.submit(sample.kind(name="second"))
        procs = self.center.runner.all_processes()
        closing = threading.Thread(target=self.center.close)
        closing.start()
        go.set()
        closing.join(10)
        self.assertFalse(closing.is_alive())
        born = [p for p in procs if p.popen is not None]
        self.assertEqual([p.name for p in born], ["first"], "the second never started")
        self.assertIsNotNone(born[0].popen.poll(), "the one born during close() was ended")
        self.pids.append(born[0].popen.pid)


class Changes(Base):
    def test_restart_after_the_quiet_with_a_new_request_from_build(self):
        built = []

        def build():
            built.append(len(built) + 1)
            return {"steps": 6, "pause": 0.05, "tag": built[-1]}
        kind = sample.kind(topics=("project:geometry",), settle=0.3)
        handle, got = self.submit(kind, build=build, request=None)
        self.assertTrue(self.until(lambda: handle.state == "running"))
        self.center.changed({"project:text"})
        self.assertEqual(handle.state, "running", "a topic the job does not follow changes nothing")
        start = time.monotonic()
        self.center.changed({"project:geometry", "selection"})
        self.assertEqual(handle.state, "settling")
        self.assertIsNone(self.center.rows()[0]["fraction"])
        self.until(lambda: False, 0.15)
        self.center.changed({"project:geometry"})          # the quiet starts again
        self.assertTrue(self.until(lambda: got["done"], 30))
        self.assertGreaterEqual(time.monotonic() - start, 0.45)
        self.assertEqual(built, [1, 2])
        self.assertEqual(got["done"][-1][0]["tag"], 2)
        self.assertEqual(len(got["done"]), 1, "the first run never ended")

    def test_a_job_submitted_to_settle_starts_after_the_quiet_once(self):
        built = []

        def build():
            built.append(len(built) + 1)
            return {"steps": 2, "pause": 0.01, "tag": built[-1]}
        kind = sample.kind(topics=("project:geometry",), settle=0.3)
        start = time.monotonic()
        first, got_first = self.submit(kind, build=build, request=None, settle=True)
        self.assertEqual(first.state, "settling")
        self.assertEqual(built, [], "the request is made when the quiet has come")
        self.assertEqual(self.center.runner.all_processes(), [], "no process before the quiet")
        self.until(lambda: False, 0.15)
        second, got = self.submit(kind, build=build, request=None, settle=True)     # the drag goes on
        self.assertEqual(first.state, "cancelled")
        self.center.changed({"project:geometry"})          # and the quiet starts again
        self.assertTrue(self.until(lambda: got["done"], 30))
        self.assertGreaterEqual(time.monotonic() - start, 0.45)
        self.assertEqual(built, [1])
        self.assertEqual(got["done"][0][0]["tag"], 1)
        self.assertEqual(got_first["done"], [])

    def test_discard_drops_the_job(self):
        kind = sample.kind(topics=("layout",), on_change="discard")
        handle, got = self.submit(kind, {"steps": 100, "pause": 0.05})
        self.assertTrue(self.until(lambda: handle.state == "running"))
        self.center.changed({"layout:s1"})
        self.assertEqual(handle.state, "cancelled")
        self.until(lambda: False, 0.3)
        self.assertEqual(self.center.rows(), [])
        self.assertEqual(got["done"], [])

    def test_finish_goes_to_the_end_and_says_stale(self):
        kind = sample.kind(topics=("project",), on_change="finish")
        handle, got = self.submit(kind, {"steps": 6, "pause": 0.05})
        self.assertTrue(self.until(lambda: handle.state == "running"))
        self.center.changed({"project:geometry"})
        self.assertEqual(handle.state, "running")
        self.assertTrue(self.until(lambda: got["done"]))
        self.assertTrue(got["done"][0][1], "stale: the project changed under it")


class Owner(Base):
    def heard(self, center, handle, seconds=10.0) -> bool:
        """Pumps `center` until its job has told its first progress (the thread's own word comes before a test's)."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            center.pump()
            job = center._jobs.get(handle.id)
            if job is not None and job.shares:
                return True
            self.posted.wait(POLL)
            self.posted.clear()
        return False

    def test_the_time_left_comes_after_five_seconds_with_a_fake_clock(self):
        now = [100.0]
        center = Center(self.post, clock=lambda: now[0])
        self.addCleanup(center.close)
        handle = center.adopt("Computing…")
        handle.progress(0, 100)
        now[0] += 2
        handle.progress(20, 100)
        self.assertIsNone(center.rows()[0]["left"], "not before 5 s of data")
        now[0] += 4
        handle.progress(60, 100)
        self.assertAlmostEqual(center.rows()[0]["left"], 4.0)
        now[0] += 1
        self.assertAlmostEqual(center.rows()[0]["left"], 3.0)
        handle.end()
        self.assertEqual(center.rows(), [])

    def test_at_a_steady_pace_the_estimate_comes_after_the_warm_up_and_counts_down(self):
        eta = Eta()
        said = []
        for t in range(0, 30):
            eta.feed(t, 3.0 * t, 120.0)             # 3 units a second, 40 s in all
            said.append(eta.left(t))
        self.assertEqual(said[:5], [None] * 5, "nothing before 5 s of data")
        for t in range(5, 30):
            self.assertAlmostEqual(said[t], 40.0 - t, delta=0.01)
        self.assertAlmostEqual(eta.left(30.5), 9.5, delta=0.01, msg="between two pieces of data it counts down")

    def test_an_uneven_pace_does_not_make_the_estimate_jump(self):
        eta = Eta()
        done, said = 0.0, []
        for t in range(0, 60):
            done += 1.0 if t % 2 else 5.0           # 3 units a second on average, in jerks
            eta.feed(t, done, 300.0)
            said.append(eta.left(t))
        shown = [s for s in said if s is not None]
        self.assertTrue(shown)
        for before, after in zip(shown, shown[1:], strict=False):
            self.assertLess(after, before, "it counts down, never back up")
        for t in range(25, 60):                     # once the window is full, close to the truth
            self.assertAlmostEqual(said[t], (300 - (3.0 * (t + 1) + (0 if t % 2 else 2))) / 3.0, delta=1.5)

    def test_a_total_that_grows_changes_what_is_left_not_the_pace(self):
        eta = Eta()
        for t in range(0, 7):
            eta.feed(t, 10.0 * t, 100.0)
        self.assertAlmostEqual(eta.left(6), 4.0)
        eta.feed(7, 70.0, 200.0)                    # more tiles found: twice the work
        self.assertAlmostEqual(eta.left(7), 13.0, msg="taken at once, not started again")

    def test_a_new_phase_counted_from_zero_starts_the_measure_again(self):
        eta = Eta()
        for t in range(0, 8):
            eta.feed(t, 10.0 * t, 100.0)
        self.assertIsNotNone(eta.left(7))
        eta.feed(8, 0.0, 50.0)                      # the next pass counts its own units from zero
        for t in range(9, 13):
            eta.feed(t, 2.0 * (t - 8), 50.0)
            self.assertIsNone(eta.left(t), "warm again before a time is said")
        eta.feed(13, 10.0, 50.0)
        self.assertAlmostEqual(eta.left(13), 20.0, msg="the new pace alone: 2 units a second, 40 left")

    def test_after_a_restart_for_a_change_no_old_time_is_shown(self):
        now = [100.0]
        center = Center(self.post, clock=lambda: now[0])
        self.addCleanup(center.close)
        kind = sample.kind(where="thread", topics=("project:geometry",), settle=0.5)
        handle = center.submit(kind, build=lambda: {"steps": 1, "pause": 30})
        run = center._jobs[handle.id].runs[0]
        self.assertTrue(self.heard(center, handle), "the thread's own first word, before the test's")

        def told(run, done, total):
            center._incoming(("progress", run, done, total, "Counting"))
            center.pump()
        for t in range(0, 7):
            now[0] = 100.0 + t
            told(run, 10.0 * t, 100.0)
        self.assertAlmostEqual(center.rows()[0]["left"], 4.0)
        center.changed({"project:geometry"})
        self.assertIsNone(center.rows()[0]["left"])
        now[0] += 1.0
        center.pump()                               # the quiet has come: started again with a new run
        new_run = center._jobs[handle.id].runs[0]
        self.assertNotEqual(new_run, run)
        self.assertTrue(self.heard(center, handle))
        told(run, 70.0, 100.0)                      # the old run's last word: nobody waits for it
        self.assertIsNone(center.rows()[0]["left"])
        for t in range(0, 4):
            now[0] += 1.0
            told(new_run, 20.0 * t, 100.0)
            self.assertIsNone(center.rows()[0]["left"], "the new run is not warm yet")
        center.cancel(handle)

    def test_the_phase_is_that_of_the_process_furthest_from_its_end(self):
        center = Center(self.post)
        self.addCleanup(center.close)
        handle = center.submit(sample.kind(where="thread"), {"steps": 1, "pause": 30})
        self.assertTrue(self.heard(center, handle))
        job = center._jobs[handle.id]
        job.count = 2                               # two shares, as a job of two processes has
        center._runs[999] = (handle, 1)
        center._incoming(("progress", job.runs[0], 9, 10, "finest tiles"))
        center._incoming(("progress", 999, 2, 10, "preview"))
        center.pump()
        self.assertEqual(center.rows()[0]["phase"], "preview")
        center._incoming(("progress", job.runs[0], 10, 10, "finest tiles"))
        center.pump()
        self.assertEqual(center.rows()[0]["phase"], "preview", "the last to speak does not make it flicker")
        center._incoming(("progress", 999, 10, 10, "finest tiles"))
        center.pump()
        self.assertEqual(center.rows()[0]["phase"], "finest tiles")
        center.cancel(handle)

    def test_a_request_that_cannot_be_made_is_said_in_the_users_words(self):
        from meridiana import i18n
        told, failed, built = [], [], []
        center = Center(self.post, tell=told.append)
        self.addCleanup(center.close)

        def build():
            built.append(1)
            if len(built) > 1:
                raise ValueError("a photo that cannot be taken")
            return {"steps": 100, "pause": 0.05}
        kind = sample.kind(where="thread", topics=("project:geometry",), settle=0.05)
        with mock.patch.object(i18n, "_translation", i18n.translation_for("it")), \
                mock.patch("meridiana.app.platform.log.complain") as complain:
            handle = center.submit(kind, build=build, on_failed=lambda k, text: failed.append(text))
            center.changed({"project:geometry"})
            end = time.monotonic() + 10
            while not failed and time.monotonic() < end:
                self.posted.wait(POLL)
                self.posted.clear()
                center.pump()
            expected = i18n._("{title} could not start: {error}").format(
                title=i18n._("Counting"), error=i18n._("the request could not be made"))
        self.assertEqual(len(failed), 1, failed)
        self.assertEqual(failed[0], expected, "every word of it through the catalogue of the window's language")
        self.assertTrue(failed[0].startswith("Conteggio delle parti: il lavoro non è partito"), failed[0])
        self.assertNotIn("ValueError", failed[0])
        self.assertNotIn("photo", failed[0])
        self.assertEqual(told, failed)
        self.assertIn("ValueError: a photo that cannot be taken", handle.error, "the detail kept for the log")
        logged = " ".join(str(c.args) for c in complain.call_args_list)
        self.assertIn("a photo that cannot be taken", logged)

    def test_pump_keeps_to_its_budget_and_goes_on_the_next_time(self):
        seen = []

        def slow(key, data):            # a millisecond of work on the owner's thread
            seen.append(key)
            end = time.perf_counter() + 0.001
            while time.perf_counter() < end:
                pass
        handle = self.center.submit(sample.kind(where="thread"), {"steps": 1, "pause": 30}, on_partial=slow)
        run = self.center._jobs[handle.id].runs[0]
        for i in range(40):
            self.center._incoming(("partial", run, f"k{i}", i))
        self.center._incoming(("partial", run, "k5", "last"))     # the same key: only the last one counts
        self.center.reset_stats()
        start = time.perf_counter()
        more = self.center.pump(budget=0.003)
        spent = time.perf_counter() - start
        self.assertTrue(more)
        self.assertLess(len(seen), 40)
        self.assertLess(spent, 0.003 + 0.0025, "the budget plus at most one call")
        turns = 1
        while self.center.pump(budget=0.003):
            turns += 1
        self.assertEqual(seen, [f"k{i}" for i in range(40)])
        self.assertGreater(turns, 3)
        self.assertEqual(self.center.stats()["longest_call"][1], "count.on_partial")
        self.center.cancel(handle)

    def test_the_owners_own_work_is_timed_with_its_name(self):
        def draw(ms):                   # what the owner draws of a result: `ms` of work on its thread
            end = time.perf_counter() + ms / 1000
            while time.perf_counter() < end:
                pass
            return "drawn"
        self.center.reset_stats()
        self.assertEqual(self.center.timed("map.surface", draw, 6), "drawn")
        self.center.timed("map.legend", draw, 1)
        longest, name = self.center.stats()["longest_call"]
        self.assertEqual(name, "map.surface")
        self.assertGreaterEqual(longest, 0.006)
        self.assertEqual(self.center.stats()["calls"], 2)
        with self.assertRaises(ZeroDivisionError):
            self.center.timed("map.wrong", lambda: 1 / 0)
        self.assertEqual(self.center.stats()["calls"], 3, "timed even when it raises")

    def test_the_owners_pieces_go_a_turn_at_a_time_in_order_the_last_of_a_name_counting(self):
        done = []

        def piece(name, ms):            # `ms` of the owner's work on its thread
            end = time.perf_counter() + ms / 1000
            while time.perf_counter() < end:
                pass
            done.append(name)
        self.center.reset_stats()
        self.center.piece("tell:plan", piece, "plan", 4)
        self.center.piece("tell:checks", piece, "checks", 0)
        self.center.piece("tell:tree", piece, "tree", 0)
        self.center.piece("tell:checks", piece, "checks again", 0)       # waiting: replaced, in its place
        self.assertGreater(self.posts, 0, "a piece asks the owner for a turn")
        self.assertEqual(done, [], "nothing runs before the owner's turn")
        self.assertTrue(self.center.pump(budget=0.003), "the turn spent on the first piece: more to come")
        self.assertEqual(done, ["plan"], "one piece at least, then no more past the budget")
        self.assertFalse(self.center.pump(budget=0.003))
        self.assertEqual(done, ["plan", "checks again", "tree"])
        stats = self.center.stats()
        self.assertEqual(stats["longest_call"][1], "tell:plan", "each piece timed with its name")
        self.assertGreaterEqual(stats["by_name"]["tell:plan"], 0.004)
        self.assertLess(stats["by_name"]["tell:tree"], 0.004)

    def test_pieces_flushed_run_now_and_a_failing_one_is_said(self):
        done = []
        self.center.piece("a", done.append, "a")
        self.center.piece("b", lambda: 1 / 0)
        self.center.piece("c", done.append, "c")
        with mock.patch("meridiana.app.platform.log.complain") as complain:
            self.center.flush_pieces()
        self.assertEqual(done, ["a", "c"])
        self.assertTrue(complain.called)
        self.assertFalse(self.center.pump())
        self.center.close()
        self.center.piece("late", done.append, "late")
        self.center.pump()
        self.assertEqual(done, ["a", "c"], "a closed center runs nothing")

    def test_a_kind_warmed_ahead_waits_with_its_function_imported_and_takes_the_first_job(self):
        kind = sample.kind(name="ahead", keep_warm=30)
        self.center.warm(kind)
        self.center.warm(kind)              # already warm: no second process
        self.assertTrue(self.until(lambda: any(p.pid for p in self.center.runner.processes()), 20))
        self.remember()
        procs = self.center.runner.processes()
        self.assertEqual(len(procs), 1)
        self.assertEqual(self.center.rows(), [], "warming shows nothing in the bar")
        _handle, got = self.submit(kind)
        self.assertTrue(self.until(lambda: got["done"]))
        self.assertEqual(got["done"][0][0]["pid"], procs[0].pid, "the first job found the warm process")
        self.center.warm(sample.kind(name="cold"))          # keep_warm 0: nothing to keep warm
        self.assertEqual(len(self.center.runner.processes()), 1)

    def test_a_failed_owner_call_is_said_and_the_pump_goes_on(self):
        handle = self.center.submit(sample.kind(where="thread"), {"steps": 1, "pause": 30},
                                    on_partial=lambda k, d: 1 / 0)
        run = self.center._jobs[handle.id].runs[0]
        self.center._incoming(("partial", run, "a", 1))
        with mock.patch("meridiana.app.platform.log.complain") as complain:
            self.center.pump()
        self.assertTrue(complain.called)
        self.center.cancel(handle)

    def test_mine_deals_every_part_once_the_lightest_first(self):
        parts = list(range(11))
        weight = lambda p: (p * 7) % 5         # noqa: E731
        for count in (1, 2, 3, 4):
            dealt = [work_job.mine(parts, (i, count), weight) for i in range(count)]
            flat = [p for d in dealt for p in d]
            self.assertEqual(sorted(flat), parts, count)
            self.assertEqual(len(flat), len(set(flat)), count)
        first = work_job.mine(parts, (0, 1), weight)
        self.assertEqual([weight(p) for p in first], sorted(weight(p) for p in parts))

    def test_a_kind_says_what_is_wrong_and_runs_only_app_or_core(self):
        with self.assertRaises(ValueError):
            sample.kind(where="elsewhere")
        with self.assertRaises(ValueError):
            sample.kind(on_change="sometimes")
        with self.assertRaises(ValueError):
            work_job.resolve("meridiana.gui.application:main")
        self.assertIs(work_job.resolve(sample.RUN), sample.count)
        self.assertTrue(sample.kind(topics=("layout",)).follows({"layout:s3"}))
        self.assertFalse(sample.kind(topics=("layout",)).follows({"layouts"}))
        self.assertTrue(sample.kind(topics=("energy",)).follows({"file"}))
        self.assertFalse(sample.kind().follows({"file"}))

    def test_close_leaves_no_process(self):
        warm = sample.kind(name="warm", keep_warm=60)
        _a, got = self.submit(warm)
        self.assertTrue(self.until(lambda: got["done"]))
        _b, _got = self.submit(sample.kind(name="busy"), {"steps": 100, "pause": 0.1})
        _c, _got = self.submit(sample.kind(name="deaf"), {"steps": 100, "pause": 0.2, "deaf": True})
        self.assertTrue(self.until(lambda: len([p for p in self.center.runner.processes() if p.pid]) == 3))
        self.remember()
        self.assertGreaterEqual(len(self.pids), 3)
        start = time.perf_counter()
        self.center.close()
        self.assertLess(time.perf_counter() - start, 3.0)
        for pid in self.pids:
            self.assertFalse(alive(pid), pid)


class Store(unittest.TestCase):
    def test_written_whole_or_not_at_all(self):
        import numpy as np
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as caches:
            folder = Path(caches) / "store"         # a store of the caches (its root, for the ceiling: disk_cap)
            key = resources.fingerprint("a surface", 3)
            self.assertIsNone(store.read(folder, key))
            store.write(folder, key, {"light": np.arange(6.0)})
            np.testing.assert_array_equal(store.read(folder, key)["light"], np.arange(6.0))

            def broken(fh, **arrays):
                fh.write(b"PK\x03\x04 half a file")
                raise OSError("disk full")
            with mock.patch("numpy.savez", broken), self.assertRaises(OSError):
                store.write(folder, key, {"light": np.zeros(3)})
            np.testing.assert_array_equal(store.read(folder, key)["light"], np.arange(6.0))
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()), sorted([store.path(folder, key).name, ".store"]))

    def test_a_broken_file_counts_as_none_and_is_said(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            store.path(folder, "k").write_bytes(b"not a zip")
            self.assertIsNone(store.read(folder, "gone"), "a key not kept")
            with mock.patch("meridiana.app.platform.log.complain") as complain:
                self.assertIsNone(store.read(folder, "k"))
            self.assertTrue(complain.called)
            with self.assertRaises(ValueError):
                store.path(folder, "../outside")


class Photo(unittest.TestCase):
    def test_the_photo_is_the_snapshot_of_the_last_change_without_a_copy(self):
        session = ProjectSession()
        opened = session.photo()
        self.assertIs(session.photo(), opened, "made once for a project just opened")
        session.edit("Name", lambda p: setattr(p, "name", "Tetto"))
        step = session.undo.steps[-1]
        self.assertIs(session.photo(), step.after, "the very dict of the undo")
        self.assertEqual(session.photo()["name"], "Tetto")
        session.undo.undo()
        self.assertIs(session.photo(), step.before)
        session.amend(lambda p: setattr(p, "name", "Tetto 2"))
        self.assertEqual(session.photo()["name"], "Tetto 2")

        def broken(project):
            project.name = "half"
            raise ValueError("no")
        with self.assertRaises(ValueError):
            session.edit("Broken", broken)
        self.assertEqual(session.photo()["name"], "Tetto 2")

    def test_a_project_opened_comes_with_its_photo(self):
        from _fixtures import capannone
        from meridiana.app.session import photo_of
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "p.meridiana"
            capannone("Aperto").save(path)
            session = ProjectSession()
            with mock.patch.object(ProjectSession, "snapshot", side_effect=AssertionError("made on the thread")):
                session.open(path)
                self.assertEqual(session.photo()["name"], "Aperto")
            other = capannone("Altro")
            photo = photo_of(other)
            session.take(other, None, saved=False, photo=photo)
            self.assertIs(session.photo(), photo, "the photo made where it was read")
            session.take(capannone("Senza"), None, saved=False)
            self.assertEqual(session.photo()["name"], "Senza", "made at the first job when none came")


if __name__ == "__main__":
    unittest.main()
