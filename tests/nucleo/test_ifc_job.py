"""The IFC reading as a job of the jobs' center (app/exchange/ifc_job.py, R598 study 48 chapter 6 step 2), without Qt:
the reader stood in for by small programs (the tests' `commands`), in a real process of the jobs.

r32-montanti: past the time there is no second try, what happened and what to do are said at once; the second try
in the simple way stays after a crash of the reader. R594: the geometry goes to the folder given, without one nowhere.
The answer travels in pieces already pickled and comes back the same dict."""

import pickle
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

import _setup  # noqa: F401  (src on the path)

from meridiana.app.exchange import ifc_job
from meridiana.app.work.center import Center

POLL = 0.02


def program(text: str, marks: Path, mode: str) -> list:
    """A stand-in for the reader: it writes its way in `marks`, then runs `text`."""
    return [sys.executable, "-c", f"open({str(marks)!r}, 'a').write({mode + chr(10)!r}); " + text]


class Job(unittest.TestCase):
    def setUp(self):
        self.posted = threading.Event()
        self.center = Center(self.posted.set)
        self.addCleanup(self.center.close)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.marks = Path(temp.name) / "ways.txt"
        self.failures, self.done, self.parts, self.phases = [], [], {}, []
        self.center.subscribe(lambda: self.phases.extend(r["phase"] for r in self.center.rows() if r["phase"]))

    def until(self, condition, seconds=30.0) -> bool:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.posted.clear()
            self.center.pump()
            if condition():
                return True
            self.posted.wait(POLL)
        return condition()

    def run_job(self, ways: dict, budget_s: float):
        commands = {mode: program(text, self.marks, mode) for mode, text in ways.items()}
        req = ifc_job.request("model.ifc", budget_s=budget_s, commands=commands)
        handle = self.center.submit(ifc_job.KIND, req, on_partial=self.parts.__setitem__,
                                    on_done=lambda layout, stale: self.done.append(layout),
                                    on_failed=lambda kind, text: self.failures.append(text))
        self.assertTrue(self.until(lambda: self.failures or self.done, 60))
        return handle

    def ways(self) -> list:
        return self.marks.read_text(encoding="utf-8").split() if self.marks.exists() else []

    def test_past_the_time_it_stops_at_once_without_a_second_try(self):
        self.run_job({"direct": "import time; time.sleep(30)", "simple": "print('{\"result\": {}}')"}, 1.0)  # wait: a reader that never answers, past the time limit
        self.assertEqual(self.ways(), ["direct"])
        self.assertNotIn(ifc_job.STAGES["again"], self.phases)
        self.assertEqual(len(self.failures), 1)
        self.assertFalse(self.done)
        self.assertIn("1", self.failures[0])                        # the seconds allowed are said

    def test_after_a_crash_the_simple_shapes_are_read_again(self):
        self.run_job({"direct": "import sys; sys.exit(3)",
                      "simple": "import time; time.sleep(0.3); "  # wait: the phase «again» seen by a pump before the reader's own
                                "print('{\"progress\": 0.5, \"what\": \"roofs\"}'); "
                                "print('{\"result\": {\"buildings\": [], \"new_counter\": 7}}')"}, 30.0)
        self.assertEqual(self.ways(), ["direct", "simple"])
        self.assertIn(ifc_job.STAGES["again"], self.phases)
        self.assertEqual(len(self.done), 1, self.failures)
        unpack = ifc_job.Unpack(self.done[0], self.parts)
        while not unpack.step():
            pass
        self.assertTrue(unpack.result.get("second_try"))
        self.assertEqual(unpack.result["new_counter"], 7)          # a key the window does not know, passed on

    def test_an_error_of_the_reader_is_said_without_a_second_try(self):
        self.run_job({"direct": "print('{\"error\": \"not an IFC\", \"kind\": \"file\"}'); import sys; sys.exit(2)",
                      "simple": "print('{\"result\": {}}')"}, 30.0)
        self.assertEqual(self.ways(), ["direct"])
        self.assertIn("not an IFC", self.failures[0])

    def test_cancel_ends_the_reader_behind_the_row(self):
        commands = {"direct": program("import time; time.sleep(60)", self.marks, "direct")}  # wait: a reader that never answers, ended by the cancel
        handle = self.center.submit(ifc_job.KIND, ifc_job.request("model.ifc", commands=commands))
        self.assertTrue(self.until(lambda: self.ways() == ["direct"], 30))
        start = time.perf_counter()
        handle.cancel()
        self.assertLess(time.perf_counter() - start, 0.05)          # the row goes at once, nothing waited for
        self.assertEqual(handle.state, "cancelled")
        self.assertEqual(self.center.rows(), [])


class Pieces(unittest.TestCase):
    def test_the_answer_comes_back_the_same_in_small_pieces(self):
        solids = [{"id": i, "hull": [[float(i), float(j)] for j in range(12)], "z0": 0.0, "z1": 3.5} for i in range(6000)]
        result = {"schema": "IFC4", "solids": solids, "buildings": [{"name": "B"}], "listing": {"elements": 6000},
                  "context": {"mesh": "x.npz"}, "empty": []}
        sent = {}
        layout = ifc_job.pack(result, sent.__setitem__)
        self.assertGreater(len(sent), 4)                            # the solids cut
        self.assertLess(max(len(b) for b in sent.values()), 2 * ifc_job.PIECE_BYTES)
        unpack = ifc_job.Unpack(layout, sent)
        steps = 1
        while not unpack.step():
            steps += 1
        self.assertEqual(steps, len(sent))
        self.assertEqual(unpack.result, result)
        self.assertEqual(list(unpack.result), list(result))         # the keys in their order
        again = ifc_job.Unpack(layout, sent)
        while not again.step():
            pass
        again.result["buildings"].append(1)                         # each asker has a copy of its own
        self.assertEqual(pickle.loads(sent["buildings#0"]), [{"name": "B"}])

    def test_a_piece_missing_is_seen(self):
        sent = {}
        layout = ifc_job.pack({"a": 1, "b": 2}, sent.__setitem__)
        del sent["b#0"]
        self.assertEqual(ifc_job.Unpack(layout, sent).missing(), ["b#0"])


class Command(unittest.TestCase):
    def test_the_geometry_goes_to_the_folder_given_and_without_one_nowhere(self):
        _program, args, _env = ifc_job.worker_command("m.ifc", "direct", r"C:\session\cache\ifc")
        self.assertEqual(args[args.index("--context") + 1], r"C:\session\cache\ifc")
        self.assertEqual(args[args.index("-m") + 1], ifc_job.WORKER)
        _program, args, _env = ifc_job.worker_command("m.ifc", "direct")
        self.assertNotIn("--context", args)


if __name__ == "__main__":
    unittest.main()
