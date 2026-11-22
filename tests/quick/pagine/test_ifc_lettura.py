"""The reading of an IFC in the dialog, as a job of the jobs' center (R598, study 48 chapter 6 step 2; the job itself
without Qt in tests/nucleo/test_ifc_job.py).

R594: the model's geometry went to %LOCALAPPDATA%\\Meridiana\\cache\\ifc whatever the session: it goes to the session's
cache, and a dialog without one (the tests') keeps none. R598: the answer the dialog gets is the reader's, the same
dict as before; a change of the project meanwhile lets the reading end (on_change "finish") and the plan is made on
the project of the moment; the dialog closed meanwhile cancels the reading, at once, and the reader ends behind it."""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import _setup
from PySide6.QtTest import QTest

from meridiana.app.exchange import ifc_job
from meridiana.app.platform import config
from meridiana.app.session import ProjectSession
from meridiana.core.model import model
from meridiana.gui.backend.dialogs import DialogsBackend

setUpModule = _setup.keep_global_state
SAMPLE = Path(__file__).resolve().parents[2] / "data" / "ifc" / "vetrata-inclinata.ifc"
HERE = {"lat": 46.0, "lon": 13.0, "address": "46.00000000, 13.00000000"}
TIMED = ("read_seconds", "read_peak_mb", "times", "seconds")      # how long it took: not the same twice


def untimed(value):
    """`value` without what says how long it took, at any depth."""
    if isinstance(value, dict):
        return {k: untimed(v) for k, v in value.items() if k not in TIMED}
    if isinstance(value, list):
        return [untimed(v) for v in value]
    return value


def wait(predicate, seconds=60.0):
    limit = time.monotonic() + seconds
    while not predicate() and time.monotonic() < limit:
        QTest.qWait(20)
    return predicate()


def dialog(session=None) -> DialogsBackend:
    backend = DialogsBackend(session or ProjectSession(model.Project(site=model.Site(**HERE))),
                             config.Config(network_tiles=False, network_geocoding=False))
    backend.open("ifc")
    return backend


def found_line() -> str:
    """The reader's answer for a square building 20 x 10 (as test_ifc_finestra's)."""
    ring = [[100.0, 100.0], [120.0, 100.0], [120.0, 110.0], [100.0, 110.0]]
    found = {"schema": "IFC2X3", "application": "Prova", "unit_m": 1.0, "true_north": 0.0, "map": None,
             "site": None, "sites": 0, "address": "", "obstacles": [], "counts": {}, "supports": [],
             "buildings": [{"name": "Palazzetto", "ifc": "x", "ground": 0.0, "source": "roof", "footprint": ring,
                            "pitches": [{"ring": ring, "normal": [0.0, 0.0, 1.0], "point": [110.0, 105.0, 8.0],
                                         "area": 200.0, "holes": 0, "owners": [1]}]}]}
    return json.dumps({"result": found})


def slow_reader(marks: Path, seconds: float) -> dict:
    """A reader that says its pid, waits `seconds`, then answers found_line()."""
    text = (f"import os, time; open({str(marks)!r}, 'w').write(str(os.getpid())); "
            f"print('{{\"progress\": 0.1, \"what\": \"roofs\"}}', flush=True); time.sleep({seconds}); "  # wait: the reader's answer held back `seconds`
            f"print({found_line()!r}, flush=True)")
    return {"direct": [sys.executable, "-c", text]}


class Cache(unittest.TestCase):
    def test_the_dialog_reads_into_the_sessions_cache(self):
        _setup.qt_or_skip()
        backend = dialog()
        self.addCleanup(backend.deleteLater)
        self.addCleanup(backend.close)
        with tempfile.TemporaryDirectory() as tmp:
            backend.paths = SimpleNamespace(cache=Path(tmp))
            backend.readFile(str(SAMPLE))
            self.assertEqual(backend._ifc_cache, str(Path(tmp) / "ifc"))
            backend.cancel()                  # the reader stopped before it writes anything
        bare = dialog()
        self.addCleanup(bare.deleteLater)
        self.addCleanup(bare.close)
        bare.readFile(str(SAMPLE))
        self.assertIsNone(bare._ifc_cache)
        bare.cancel()


class Reading(unittest.TestCase):
    def setUp(self):
        self.app = _setup.qt_or_skip()
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.marks = Path(temp.name) / "pid.txt"
        self.addCleanup(ifc_job._KEPT.clear)

    def test_the_answer_is_the_readers_own(self):
        out = subprocess.run([sys.executable, "-m", ifc_job.WORKER, str(SAMPLE)], capture_output=True, text=True,
                             encoding="utf-8", timeout=300, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        lines = [json.loads(x) for x in out.stdout.splitlines() if x.startswith("{")]
        reader = next(x["result"] for x in lines if "result" in x)
        backend = dialog()
        self.addCleanup(backend.deleteLater)
        self.addCleanup(backend.close)
        preload = mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": "1"})       # the memory allows keeping it
        preload.start()
        self.addCleanup(preload.stop)
        backend.readFile(str(SAMPLE))
        self.assertTrue(wait(lambda: backend.state.get("ifcRead") or backend.status, 300), backend.status)
        got = backend._ifc_found
        self.assertEqual(untimed(got), untimed(reader))
        self.assertGreater(got["read_seconds"], 0)
        # R548: the same file again in the session, at once and without a reader; a copy of its own
        got["buildings"].append("changed")
        backend.readFile(str(SAMPLE))
        self.assertIsNone(backend._ifc_reader)
        self.assertTrue(wait(lambda: backend._ifc_found is not got and backend.state.get("ifcRead"), 30))
        self.assertTrue(backend._ifc_found["from_memory"])
        self.assertEqual(backend._ifc_found["buildings"], reader["buildings"])

    def test_a_change_of_the_project_meanwhile_lets_the_reading_end(self):
        backend = dialog()
        self.addCleanup(backend.deleteLater)
        self.addCleanup(backend.close)
        backend._state["fileName"] = "palazzetto.ifc"
        backend._read_ifc("palazzetto.ifc", ifc_job.request("palazzetto.ifc", commands=slow_reader(self.marks, 1.5)))
        self.assertTrue(wait(self.marks.exists, 30))
        session = backend.session
        session.edit("Rename", lambda p: setattr(p, "name", "Changed meanwhile"))
        self.assertTrue(backend._ifc_reader.active)                 # on_change "finish": it goes on
        self.assertTrue(backend._ifc_reader.stale)
        self.assertTrue(wait(lambda: backend.state.get("ifcRead") or backend.status, 60), backend.status)
        backend.setValue("how", "origin")
        self.assertTrue(wait(lambda: not backend.busy and backend.state.get("valid"), 60), backend.status)
        self.assertTrue(backend.accept())
        # the import made on the project of the moment: the change kept, the building added
        self.assertEqual(session.project.name, "Changed meanwhile")
        self.assertEqual(len(session.project.buildings), 1)

    def test_the_dialog_closed_meanwhile_cancels_the_reading_at_once(self):
        from meridiana.core.compute import procmem
        backend = dialog()
        self.addCleanup(backend.deleteLater)
        self.addCleanup(backend.close)
        backend._read_ifc("palazzetto.ifc", ifc_job.request("palazzetto.ifc", commands=slow_reader(self.marks, 60)))
        self.assertTrue(wait(self.marks.exists, 30))
        pid = int(self.marks.read_text())
        center = backend.center
        start = time.perf_counter()
        backend.cancel()
        self.assertLess(time.perf_counter() - start, 0.05)          # nothing waited for on the window's thread
        self.assertFalse(backend.busy)
        self.assertEqual(center.rows(), [])
        self.assertTrue(wait(lambda: procmem.rss(pid) is None, 10), "the reader ended behind the row")


if __name__ == "__main__":
    unittest.main()
