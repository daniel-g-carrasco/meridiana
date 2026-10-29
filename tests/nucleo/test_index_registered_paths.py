"""Saved registered files are index sources without granting access to their whole folder."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import _setup  # noqa: F401
from _fixtures import capannone
from meridiana import project_index, registry
from meridiana.ui.window import MainWindow


class RegisteredIndexPathsTest(unittest.TestCase):
    def test_a_registered_project_is_scanned_without_a_linked_folder(self):
        root = Path(tempfile.mkdtemp())
        reg = registry.Registry(root / "registry.sqlite3")
        self.addCleanup(reg.close)
        job = reg.create_job("26042", "Example job", reg.create_client("Example client")["id"])
        path = root / "registered.meridiana"
        project = capannone("Registered design")
        project.save(path)
        capannone("Unlinked neighbour").save(root / "unlinked.meridiana")
        reg.link_project(job["id"], path, project.name)
        queued = []
        host = SimpleNamespace(registry=reg, index_generation=0, index_job=None,
                               pool=SimpleNamespace(start=queued.append), _index_done=lambda *_a: None)
        MainWindow._refresh_index(host)
        self.assertEqual(len(queued), 1)
        rows = project_index.scan(queued[0].folders)
        self.assertEqual([row["path"] for row in rows], [str(path)])
        self.assertEqual(rows[0]["job_code"], "26042")
        self.assertEqual(reg.list_folders(), [])
