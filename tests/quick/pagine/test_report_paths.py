"""Report requests leave directory creation to the report worker."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import _setup
from meridiana.app.session import ProjectSession
from meridiana.core.model.model import Project
from meridiana.gui.backend.report import ReportBackend

setUpModule = _setup.keep_global_state


class ReportPaths(unittest.TestCase):
    def test_request_does_not_create_a_directory_on_the_window_thread(self):
        _setup.qt_or_skip()
        with tempfile.TemporaryDirectory() as folder:
            backend = ReportBackend(ProjectSession(Project()), paths={"cache": Path(folder) / "cache"})
            try:
                with patch.object(backend, "_year_spec", return_value={"file": "year.pickle"}):
                    with patch.object(Path, "mkdir", side_effect=AssertionError("directory on UI thread")):
                        request = backend._request()
                root = Path(request["root"])
                self.assertEqual(root.parent, Path(folder) / "cache")
                self.assertFalse(root.exists())
            finally:
                backend.close()
