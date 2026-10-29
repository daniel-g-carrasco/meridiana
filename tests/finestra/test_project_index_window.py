"""The window refreshes the derived project index away from its own thread (R151)."""

import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import _setup
from _fixtures import capannone

from meridiana import config, project_index, registry
from meridiana.paths import Paths

setUpModule = _setup.keep_global_state


class ProjectIndexWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_linked_projects_are_indexed_in_a_worker_and_after_a_save(self):
        root = Path(tempfile.mkdtemp())
        paths = Paths(root / "config", root / "state", root / "data", root / "cache")
        folder = root / "linked"
        folder.mkdir()
        reg = registry.Registry(paths.data / "registry.sqlite3")
        client = reg.create_client("Example client")
        job = reg.create_job("26042", "Example job", client["id"])
        reg.link_folder(job["id"], folder)
        reg.close()
        project = capannone("Before save")
        project.job_id = job["id"]
        path = folder / "example_R01.meridiana"
        project.save(path)
        threads = []
        original = project_index.scan

        def watched(*args):
            threads.append(threading.get_ident())
            return original(*args)

        with mock.patch("meridiana.ui.window.project_index.scan", side_effect=watched):
            win = _setup.window(self, cfg=config.Config(background="none"), paths=paths)
            self.assertTrue(_setup.wait_until(self.app, lambda: bool(win.registry.list_index())))
            win.open_path(path)
            win.edit("Rename", lambda current: setattr(current, "name", "After save"))
            self.assertTrue(win._save())
            self.assertTrue(_setup.wait_until(
                self.app, lambda: any(row.get("title") == "After save" for row in win.registry.list_index())))
        self.assertTrue(threads)
        self.assertNotIn(threading.get_ident(), threads)
        row = next(row for row in win.registry.list_index() if row["path"] == str(path))
        self.assertEqual(row["revision"], "R01")
        self.assertEqual(row["client_name"], "Example client")

    def test_a_scheduled_refresh_does_not_touch_a_closed_registry(self):
        win = _setup.window(self)
        win.registry.close()
        win._refresh_index()


if __name__ == "__main__":
    unittest.main()
