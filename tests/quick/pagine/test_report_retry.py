"""Report retries keep their original inputs and respect stale requests."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

import _setup
from _fixtures import capannone
from meridiana.app.platform.config import Config
from meridiana.app.session import ProjectSession
from meridiana.gui.backend.report import ReportBackend

setUpModule = _setup.keep_global_state


class ReportRetry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.session = ProjectSession(capannone())
        self.session.path = self.folder / "A.meridiana"
        self.session.energy = {"notes": ["year A"]}
        self.backend = ReportBackend(self.session, Config(), paths={"cache": self.folder, "state": self.folder})
        self.addCleanup(self.backend.close)
        self.requests = []
        self.writer = patch("meridiana.gui.backend.report.QThreadPool")
        self.pool = self.writer.start()
        self.addCleanup(self.writer.stop)
        self.submit = patch.object(self.backend.center, "submit", side_effect=self.submitted)
        self.submit.start()
        self.addCleanup(self.submit.stop)

    def submitted(self, kind, request, **kwargs):
        self.requests.append(request)
        return SimpleNamespace(active=False)

    def test_missing_after_a_change_discards_the_stale_export(self):
        self.backend._start("export", self.folder / "A.pdf")
        self.session.edit("rename", lambda p: setattr(p, "name", "B"))
        self.backend._done({"missing": "year"}, True)
        self.assertEqual(len(self.requests), 1, "no export of B with the year of A")
        self.assertFalse(self.backend.busy)
        self.assertFalse((self.folder / "A.pdf").exists())

    def test_missing_retries_with_the_original_photo_year_layouts_and_options(self):
        self.backend._start("export", self.folder / "A.pdf")
        original = self.requests[0]
        year = self.session.energy
        layouts = self.session.good_results()
        self.session.energy = {"notes": ["year B"]}
        self.backend._data = {"client": "B"}
        self.backend._done({"missing": "year"}, False)
        self.assertEqual(len(self.requests), 2)
        retry = self.requests[1]
        for key in original.keys() - {"year"}:
            self.assertEqual(retry[key], original[key], key)
        self.assertIs(retry["photo"], original["photo"])
        self.assertIn("file", retry["year"])
        written = self.pool.globalInstance.return_value.start.call_args[0][0].year
        self.assertEqual(written, {**year, "results": layouts})

    def test_export_record_keeps_the_project_that_was_requested(self):
        self.backend._start("export", self.folder / "A.pdf")
        self.session.path = self.folder / "B.meridiana"
        self.backend._done({"written": [str(self.folder / "A.pdf")], "fingerprint": "year A", "date": "today"}, True)
        self.assertEqual(self.backend._records, {str(self.folder / "A.meridiana"):
                         {"file": str(self.folder / "A.pdf"), "fingerprint": "year A", "date": "today"}})
