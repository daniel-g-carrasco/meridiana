"""Import and update jobs: source parity, errors, cancellation and queued results."""

import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PySide6.QtCore import QThread, QThreadPool
import _setup
from PySide6.QtTest import QTest
from meridiana import config, ifc_read, updates
from meridiana.pvsyst import project as pvproject, mapping
from meridiana.session import ProjectSession
from meridiana.quick.backend.dialogs import DialogsBackend

setUpModule = _setup.keep_global_state
DATA = Path(__file__).resolve().parents[2] / "data"


def wait(predicate, seconds=30):
    limit = time.monotonic() + seconds
    while not predicate() and time.monotonic() < limit:
        QTest.qWait(10)
    if not predicate():
        raise AssertionError("job did not finish")


class DialogJobsTest(unittest.TestCase):
    def setUp(self):
        self.app = _setup.qt_or_skip()
        self.backend = DialogsBackend(
            ProjectSession(),
            config.Config(network_tiles=False, network_geocoding=False),
        )

    def tearDown(self):
        self.backend.cancel()
        QThreadPool.globalInstance().waitForDone(30000)
        QTest.qWait(20)
        self.backend.deleteLater()

    def test_pvsyst_real_file_uses_exact_core_mapping_and_keeps_source(self):
        path = DATA / "pvsyst" / "Prova Rho_Project.PRJ"
        original = path.read_bytes()
        prj = pvproject.read_project(path)
        expected, report = mapping.to_project(
            prj, [pvproject.read_variant(prj.variants[0].path)]
        )
        self.backend.open("pvsyst")
        self.backend.readFile(str(path))
        wait(lambda: not self.backend.busy)
        self.assertFalse(self.backend.status)
        self.assertEqual(len(self.backend.state["variants"]), len(prj.variants))
        for index in range(1, len(prj.variants)):
            self.backend.selectVariant(index, False)
        self.backend.readVariants()
        wait(lambda: not self.backend.busy)
        self.assertTrue(self.backend.state["valid"], self.backend.status)
        actual = self.backend._pv_result[0]
        self.assertEqual(actual.site, expected.site)
        self.assertEqual(actual.modules, expected.modules)
        self.assertEqual(len(actual.subfields), len(expected.subfields))
        self.assertEqual(self.backend._pv_result[1], report)
        self.assertEqual(path.read_bytes(), original)
        ready = []
        self.backend.projectReady.connect(ready.append)
        self.assertTrue(self.backend.accept())
        self.assertIs(ready[0], actual)

    def test_bad_file_returns_error_without_touching_project(self):
        before = self.backend.session.snapshot()
        self.backend.open("pvsyst")
        self.backend.readFile(str(DATA / "missing.PRJ"))
        wait(lambda: not self.backend.busy)
        self.assertTrue(self.backend.status)
        self.assertFalse(self.backend.accept())
        self.assertEqual(before, self.backend.session.snapshot())

    def test_cancelled_worker_cannot_deliver_and_callback_runs_on_gui_thread(self):
        gate = threading.Event()
        delivered = []
        self.backend._start(lambda: gate.wait(3), delivered.append)
        self.backend.cancel()
        gate.set()
        QThreadPool.globalInstance().waitForDone(5000)
        QTest.qWait(50)
        self.assertFalse(delivered)
        self.backend._start(
            lambda: 42, lambda value: delivered.append((value, QThread.currentThread()))
        )
        wait(lambda: not self.backend.busy)
        self.assertEqual(delivered, [(42, self.app.thread())])

    def test_ifc_process_import_and_undo(self):
        if not ifc_read.available():
            self.skipTest("optional IfcOpenShell not installed")
        self.backend.open("ifc")
        self.backend.readFile(str(DATA / "ifc" / "Building-Architecture.ifc"))
        wait(lambda: not self.backend.busy, 90)
        self.backend.setValue("how", "origin")        # R454: by hand is the default, the plan places it
        wait(lambda: not self.backend.busy and self.backend.state["valid"], 90)
        self.assertTrue(self.backend.state["valid"], self.backend.status)
        self.assertTrue(self.backend.accept())
        self.assertTrue(self.backend.session.project.buildings)
        self.backend.session.undo.undo()
        self.assertFalse(self.backend.session.project.buildings)

    def test_ifc_storeys_ticked_and_the_shadow_choice(self):
        """r22-ifc: a model of several storeys offers them ticked; one left out leaves its roofs out of the plan."""
        if not ifc_read.available():
            self.skipTest("optional IfcOpenShell not installed")
        self.backend.open("ifc")
        self.backend.readFile(str(DATA / "ifc" / "Building-Architecture.ifc"))
        wait(lambda: not self.backend.busy, 90)
        self.backend.setValue("how", "origin")
        wait(lambda: not self.backend.busy and self.backend.state["valid"], 90)
        fields = {f["key"]: f for f in self.backend.fields}
        self.assertEqual(fields["storeys"]["kind"], "checks")
        names = [o["value"] for o in fields["storeys"]["options"]]
        self.assertEqual(self.backend.state["storeys"], names)                   # all of them at first
        before = len(self.backend._ifc_plan.buildings)
        self.assertGreater(before, 0)
        with_roofs = {b.get("storey") or "" for b in self.backend._ifc_found["buildings"]}
        dropped = next(n for n in names if n in with_roofs)          # this sample's roof is on no storey
        self.backend.setValue("storeys", [n for n in names if n != dropped])
        wait(lambda: not self.backend.busy, 90)
        self.assertFalse(self.backend.state["valid"])                           # its roof left out: nothing to add
        self.assertEqual(len(self.backend._ifc_plan.buildings), 0)
        self.backend.setValue("storeys", names)
        wait(lambda: not self.backend.busy and self.backend.state["valid"], 90)
        self.assertEqual(len(self.backend._ifc_plan.buildings), before)
        self.assertEqual(self.backend.state["shade"], "off")                     # the shadows: the bodies, as before

    def test_download_only_offers_verified_result_and_cancel_blocks_installer(self):
        with tempfile.TemporaryDirectory() as folder:
            self.backend.paths = SimpleNamespace(cache=Path(folder))
            self.backend.open("update")
            self.backend._installer = updates.Asset(
                "setup.exe", "https://example.invalid", 1, "sha", "sig"
            )
            out = []
            self.backend.installerReady.connect(out.append)
            with patch(
                "meridiana.updates.download",
                side_effect=ValueError("signature does not match"),
            ):
                self.backend.downloadUpdate()
                wait(lambda: not self.backend.busy)
            self.assertFalse(out)
            self.assertIn("signature", self.backend.status)
            with patch(
                "meridiana.updates.download", return_value=Path(folder) / "setup.exe"
            ) as download:
                self.backend.downloadUpdate()
                wait(lambda: not self.backend.busy)
                self.assertIn("cancelled", download.call_args.kwargs)
            self.assertEqual(len(out), 1)

    def test_close_during_worker_never_delivers_or_emits_user_cancel(self):
        gate = threading.Event()
        delivered = []
        closed = []
        self.backend.closed.connect(lambda: closed.append(True))
        self.backend._start(lambda: gate.wait(2), delivered.append)
        self.backend.close()
        gate.set()
        QThreadPool.globalInstance().waitForDone(5000)
        QTest.qWait(50)
        self.assertFalse(delivered)
        self.assertFalse(closed)


if __name__ == "__main__":
    unittest.main()
