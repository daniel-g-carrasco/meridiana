"""The index of the registered projects in the Qt Quick window (R151; gui/backend/index_refresh.py): scanned when the
window starts, again after a save, one scan at a time, a failure said in the status bar. It was MainWindow._refresh_index
of the Widgets window, lost with it on 10/11/2026 (the Quick read registry.list_index and nobody filled it).

    python -m unittest quick.sistema.test_project_index
"""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtCore import Qt

from _fixtures import capannone
from _setup import wait_until
from meridiana.app.project import project_index
from meridiana.data.registry import Registry
from quick.gestures import pump


def registry_with_a_folder(database, folder):
    reg = Registry(database)
    client = reg.create_client("Example client")
    job = reg.create_job("00001", "Example shed", client["id"], reserved=False)
    reg.link_folder(job["id"], folder)
    return reg, job


class Sources(unittest.TestCase):
    def test_a_linked_folder_and_a_project_carry_their_job_and_client(self):
        temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temp.cleanup)
        folder = Path(temp.name) / "projects"
        folder.mkdir()
        capannone("Shed").save(folder / "shed.mer")
        reg, job = registry_with_a_folder(Path(temp.name) / "registry.sqlite3", folder)
        self.addCleanup(reg.close)
        (path, metadata), = project_index.sources(reg)
        self.assertEqual(path.resolve(), folder.resolve())
        self.assertEqual(metadata, {"job_id": job["id"], "job_code": "00001", "job_name": "Example shed",
                                    "client_name": "Example client", "reserved": False})
        rows = project_index.refresh(reg.path, project_index.sources(reg))
        self.assertEqual([Path(r["path"]).name for r in rows], ["shed.mer"])
        self.assertEqual(reg.list_index(), rows)


class InTheWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from meridiana.gui.application import create_app
        cls.app = create_app()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.cache = root / "cache"
        self.folder = root / "projects"
        self.folder.mkdir()
        capannone("Shed").save(self.folder / "shed.mer")
        # the registry where the window's profile keeps it (gui/backend/files_part.py), before the window exists
        reg, self.job = registry_with_a_folder(self.cache / "quick-profile" / "data" / "registry.sqlite3", self.folder)
        reg.close()
        self.host = None
        self.addCleanup(self.dispose)

    def open(self):
        from meridiana.gui.application import QuickWindow
        self.host = QuickWindow(capannone("In hand"), self.cache, real_views=True)
        self.host.window.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.host.window.show()
        self.part = self.host.parts.controllers["filePart"]
        return self.part

    def dispose(self):
        if self.host is not None:
            self.host.close()
            self.host = None
            pump(50)

    def names(self):
        return sorted(Path(row["path"]).name for row in self.part.registry.list_index())

    def test_the_window_fills_the_index_at_the_start_and_again_after_a_save(self):
        part = self.open()
        self.assertTrue(wait_until(self.app, lambda: self.names() == ["shed.mer"], seconds=10), self.names())
        row, = part.registry.list_index()
        self.assertEqual((row["job_code"], row["client_name"]), ("00001", "Example client"))
        wait_until(self.app, lambda: not part.index.running, seconds=10)
        self.assertTrue(part.files.saveAs(str(self.folder / "second.mer")))
        self.assertTrue(wait_until(self.app, lambda: self.names() == ["second.mer", "shed.mer"], seconds=10),
                        self.names())

    def test_a_change_in_clients_and_jobs_scans_again(self):
        part = self.open()
        wait_until(self.app, lambda: self.names() == ["shed.mer"] and not part.index.running, seconds=10)
        other = self.folder.parent / "other"
        other.mkdir()
        capannone("Other").save(other / "other.mer")
        part.registry.link_folder(self.job["id"], other)
        part.dialogs.registryChanged.emit()
        self.assertTrue(wait_until(self.app, lambda: self.names() == ["other.mer", "shed.mer"], seconds=10),
                        self.names())

    def test_a_failure_is_said_in_the_status_bar_and_logged(self):
        with mock.patch.object(project_index, "refresh", side_effect=OSError("disk full")), \
                mock.patch("meridiana.gui.backend.index_refresh.log.complain") as complain:
            self.open()
            shell = self.host.shell
            self.assertTrue(wait_until(self.app, lambda: "disk full" in shell._notice, seconds=10), shell._notice)
            self.assertEqual(complain.call_args.args[0], "project index")


class OneAtATime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from meridiana.gui.application import create_app
        cls.app = create_app()

    def test_asked_again_while_scanning_it_scans_once_more_with_what_is_registered_then(self):
        from meridiana.gui.backend.index_refresh import IndexRefresh
        temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temp.cleanup)
        folder = Path(temp.name) / "projects"
        folder.mkdir()
        capannone("Shed").save(folder / "shed.mer")
        reg, _job = registry_with_a_folder(Path(temp.name) / "registry.sqlite3", folder)
        self.addCleanup(reg.close)
        told, calls = [], []
        real = project_index.refresh

        def counted(database, folders):
            calls.append(len(folders))
            return real(database, folders)

        index = IndexRefresh(reg, told.append)
        self.addCleanup(index.close)
        with mock.patch.object(project_index, "refresh", side_effect=counted):
            index.refresh()
            capannone("Late").save(folder / "late.mer")
            index.refresh()                         # while the first may still run: coalesced, not a second job
            index.refresh()
            self.assertTrue(wait_until(self.app, lambda: not index.running and
                                       sorted(Path(r["path"]).name for r in reg.list_index()) == ["late.mer", "shed.mer"],
                                       seconds=10), reg.list_index())
        self.assertLessEqual(len(calls), 2)
        self.assertEqual(told, [])

    def test_nothing_registered_and_nothing_indexed_starts_no_scan(self):
        from meridiana.gui.backend.index_refresh import IndexRefresh
        temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temp.cleanup)
        reg = Registry(Path(temp.name) / "registry.sqlite3")
        self.addCleanup(reg.close)
        index = IndexRefresh(reg, print)
        self.addCleanup(index.close)
        index.refresh()
        self.assertFalse(index.running)


if __name__ == "__main__":
    unittest.main()
