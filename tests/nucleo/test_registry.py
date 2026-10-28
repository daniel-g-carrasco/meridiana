"""The local SQLite registry of clients, jobs, project series and folders (R150)."""

import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup  # noqa: F401

from meridiana import registry


class RegistryTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.db = self.folder / "registry.sqlite3"
        self.reg = registry.Registry(self.db)
        self.addCleanup(self.reg.close)

    def client(self, name="Example client"):
        return self.reg.create_client(name, kind="company", contacts={"email": "design@example.invalid"},
                                      notes="Invented test data")

    def job(self, client_id=None, code="00125", name="Example job"):
        client_id = client_id or self.client()["id"]
        return self.reg.create_job(code, name, client_id, status="in_progress", phase="preliminary")

    def test_schema_and_links_come_back_with_stable_ids_and_text_codes(self):
        self.assertEqual(self.reg.connection.execute("PRAGMA user_version").fetchone()[0], registry.SCHEMA_VERSION)
        self.assertEqual(self.reg.connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        self.assertEqual(self.reg.connection.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        client = self.client()
        job = self.job(client["id"])
        self.reg.link_project(job["id"], self.folder / "series_R01.meridiana", "Example design",
                                        project_id="series-stable-id", revision="R01")
        folder = self.reg.link_folder(job["id"], self.folder / "job-folder")
        self.reg.close()
        self.reg = registry.Registry(self.db)
        self.addCleanup(self.reg.close)
        self.assertEqual(self.reg.list_clients()[0]["id"], client["id"])
        self.assertEqual(self.reg.list_clients()[0]["contacts"], {"email": "design@example.invalid"})
        self.assertEqual(self.reg.list_jobs()[0]["code"], "00125")
        self.assertEqual(self.reg.list_jobs()[0]["status"], "in_progress")
        self.assertEqual(self.reg.list_projects(job["id"])[0]["id"], "series-stable-id")
        self.assertEqual(self.reg.list_projects(job["id"])[0]["revision"], "R01")
        self.assertEqual(self.reg.list_folders(job["id"])[0]["id"], folder["id"])
        self.assertFalse(self.reg.list_folders(job["id"])[0]["manifest_consent"])

    def test_a_client_with_jobs_is_archived_not_deleted(self):
        client = self.client()
        self.job(client["id"])
        with self.assertRaises(registry.RegistryError):
            self.reg.delete_client(client["id"])
        self.reg.archive_client(client["id"])
        self.assertEqual(self.reg.list_clients(), [])
        self.assertEqual(self.reg.list_clients(include_archived=True)[0]["id"], client["id"])

    def test_a_failed_transaction_leaves_no_partial_client(self):
        before = len(self.reg.list_clients())
        with self.assertRaises(sqlite3.IntegrityError):
            with self.reg._write() as connection:
                connection.execute("INSERT INTO clients(id, name) VALUES ('same-id', 'First')")
                connection.execute("INSERT INTO clients(id, name) VALUES ('same-id', 'Duplicate')")
        self.assertEqual(len(self.reg.list_clients()), before)
        self.assertIsNone(self.reg.client("same-id"))

    def test_the_backup_is_a_consistent_database_with_the_committed_data(self):
        client = self.client()
        self.assertTrue(self.reg.backup_path.is_file())
        backup = sqlite3.connect(self.reg.backup_path)
        row = backup.execute("SELECT id, name FROM clients").fetchone()
        backup.close()
        self.assertEqual(row, (client["id"], "Example client"))

    def test_duplicate_codes_and_a_newer_schema_are_refused(self):
        job = self.job()
        with self.assertRaises(registry.RegistryError):
            self.job(job["client_id"], code="00125", name="Another job")
        self.reg.close()
        connection = sqlite3.connect(self.db)
        connection.execute(f"PRAGMA user_version = {registry.SCHEMA_VERSION + 1}")
        connection.close()
        with self.assertRaises(registry.RegistryError):
            self.reg = registry.Registry(self.db)

    def test_a_reserved_job_never_gets_folder_manifest_consent(self):
        job = self.job()
        self.reg.update_job(job["id"], reserved=True)
        folder = self.reg.link_folder(job["id"], self.folder / "reserved-folder")
        with self.assertRaises(registry.RegistryError):
            self.reg.set_manifest_consent(folder["id"], True)
        self.assertFalse(self.reg.list_folders(job["id"])[0]["manifest_consent"])


if __name__ == "__main__":
    unittest.main()
