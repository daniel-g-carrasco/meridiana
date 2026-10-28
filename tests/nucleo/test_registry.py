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
        folder = self.reg.link_folder(job["id"], self.folder / "reserved-folder")
        self.reg.set_manifest_consent(folder["id"], True)
        self.assertTrue((self.folder / "reserved-folder" / registry.MANIFEST_NAME).is_file())
        self.reg.update_job(job["id"], reserved=True)
        self.assertFalse((self.folder / "reserved-folder" / registry.MANIFEST_NAME).exists())
        with self.assertRaises(registry.RegistryError):
            self.reg.set_manifest_consent(folder["id"], True)
        self.assertFalse(self.reg.list_folders(job["id"])[0]["manifest_consent"])

    def test_the_folder_manifest_waits_for_consent_and_follows_the_job(self):
        job = self.job()
        self.reg.link_project(job["id"], self.folder / "series_R01.meridiana", "Example design",
                              project_id="series-stable-id", revision="R01")
        folder_path = self.folder / "job-folder"
        folder = self.reg.link_folder(job["id"], folder_path)
        manifest = folder_path / registry.MANIFEST_NAME
        self.assertFalse(manifest.exists())
        with self.assertRaises(registry.RegistryError):
            self.reg.write_manifest(folder["id"])
        self.assertFalse(manifest.exists())
        self.reg.set_manifest_consent(folder["id"], True)
        data = registry.read_exchange(manifest, manifest=True)
        self.assertEqual(data["job"]["code"], "00125")
        self.assertEqual(data["projects"][0]["id"], "series-stable-id")
        self.reg.update_job(job["id"], phase="definitive")
        self.assertEqual(registry.read_exchange(manifest, manifest=True)["job"]["phase"], "definitive")
        self.reg.set_manifest_consent(folder["id"], False)
        self.assertFalse(manifest.exists())
        self.assertFalse(manifest.with_name(manifest.name + ".bak").exists())

    def test_registry_export_preview_and_import_merge_by_id_without_duplicates(self):
        job = self.job()
        self.reg.link_project(job["id"], self.folder / "series.meridiana", "Example design",
                              project_id="series-stable-id")
        self.reg.link_folder(job["id"], self.folder / "job-folder")
        exported = self.folder / "registry.json"
        self.reg.export(exported)
        data = registry.read_exchange(exported)
        other = registry.Registry(self.folder / "other.sqlite3")
        self.addCleanup(other.close)
        self.assertEqual(other.preview_import(data)["new"], 4)
        other.import_data(data)
        self.assertEqual(other.preview_import(data)["unchanged"], 4)
        other.import_data(data)
        self.assertEqual(len(other.list_clients()), 1)
        self.assertEqual(len(other.list_jobs()), 1)
        self.assertEqual(len(other.list_projects()), 1)
        self.assertEqual(len(other.list_folders()), 1)
        client = self.reg.list_clients()[0]
        self.reg.update_client(client["id"], name="Changed example client")
        self.reg.export(exported)
        changed = registry.read_exchange(exported)
        self.assertEqual(other.preview_import(changed)["updated"], 1)
        other.import_data(changed)
        self.assertEqual(other.client(client["id"])["name"], "Changed example client")
        self.assertEqual(len(other.list_clients()), 1)

    def test_folder_consent_is_local_and_does_not_travel_with_registry_import(self):
        job = self.job()
        folder_path = self.folder / "job-folder"
        folder = self.reg.link_folder(job["id"], folder_path)
        self.reg.set_manifest_consent(folder["id"], True)
        self.reg.export(self.folder / "registry.json")
        data = registry.read_exchange(self.folder / "registry.json")
        self.assertFalse(data["folders"][0]["manifest_consent"])
        self.reg.set_manifest_consent(folder["id"], False)
        other = registry.Registry(self.folder / "other.sqlite3")
        self.addCleanup(other.close)
        other.import_data(data)
        imported = other.list_folders()[0]
        self.assertFalse(imported["manifest_consent"])
        self.assertFalse((folder_path / registry.MANIFEST_NAME).exists())
        other.set_manifest_consent(imported["id"], True)
        other.import_data(data)
        self.assertTrue(other.list_folders()[0]["manifest_consent"])
        self.assertTrue((folder_path / registry.MANIFEST_NAME).is_file())
        moved = self.folder / "unapproved-folder"
        changed_path = {**data, "folders": [{**data["folders"][0], "path": str(moved)}]}
        other.import_data(changed_path)
        self.assertFalse(other.list_folders()[0]["manifest_consent"])
        self.assertFalse((moved / registry.MANIFEST_NAME).exists())
        other.import_data(data)
        other.set_manifest_consent(imported["id"], True)
        second = other.create_job("00999", "Another example", other.list_clients()[0]["id"])
        changed_job = {**data, "folders": [{**data["folders"][0], "job_id": second["id"]}]}
        other.import_data(changed_job)
        self.assertFalse(other.list_folders()[0]["manifest_consent"])

    def test_manifest_failures_are_per_folder_and_retried_after_the_database_commit(self):
        job = self.job()
        first = self.reg.link_folder(job["id"], self.folder / "first")
        second = self.reg.link_folder(job["id"], self.folder / "second")
        original = registry.atomic.write_json

        def fail_first(path, data, keep_backup=True):
            if Path(path).parent == self.folder / "first":
                raise OSError("invented unavailable folder")
            return original(path, data, keep_backup=keep_backup)

        with mock.patch.object(registry.atomic, "write_json", side_effect=fail_first):
            self.reg.set_manifest_consent(first["id"], True)
            self.reg.set_manifest_consent(second["id"], True)
        self.assertTrue(self.reg.list_folders()[0]["manifest_consent"])
        self.assertIn(first["id"], self.reg.manifest_errors)
        self.assertTrue((self.folder / "second" / registry.MANIFEST_NAME).is_file())
        with mock.patch.object(Path, "unlink", side_effect=OSError("invented busy folder")):
            self.reg.set_manifest_consent(second["id"], False)
        self.assertFalse(self.reg.list_folders(job["id"])[1]["manifest_consent"])
        self.assertIn(second["id"], self.reg.manifest_errors)
        self.reg.update_job(job["id"], phase="definitive")
        self.assertEqual(self.reg.manifest_errors, {})
        self.assertTrue((self.folder / "first" / registry.MANIFEST_NAME).is_file())
        self.assertFalse((self.folder / "second" / registry.MANIFEST_NAME).exists())

    def test_malformed_import_fields_are_refused_before_preview_or_write(self):
        job = self.job()
        self.reg.link_project(job["id"], self.folder / "series.meridiana", "Example")
        self.reg.link_folder(job["id"], self.folder / "folder")
        original = self.reg.export_data()
        cases = (("clients", "name", []), ("clients", "archived", "false"),
                 ("jobs", "code", ["00125"]), ("jobs", "reserved", "false"),
                 ("projects", "path", ["series.meridiana"]), ("folders", "path", ["folder"]))
        for kind, field, value in cases:
            with self.subTest(kind=kind, field=field):
                data = copy.deepcopy(original)
                data[kind][0][field] = value
                with self.assertRaises(registry.RegistryError):
                    self.reg.preview_import(data)
                with self.assertRaises(registry.RegistryError):
                    self.reg.import_data(data)
        self.assertEqual(self.reg.list_jobs()[0]["code"], "00125")
        self.assertFalse(self.reg.list_jobs()[0]["reserved"])

    def test_an_import_conflict_is_previewed_and_changes_nothing(self):
        existing = self.job()
        source = registry.Registry(self.folder / "source.sqlite3")
        self.addCleanup(source.close)
        source.create_job("00125", "Another example job", source.create_client("Another client")["id"])
        source.export(self.folder / "source.json")
        data = registry.read_exchange(self.folder / "source.json")
        self.assertTrue(self.reg.preview_import(data)["conflicts"])
        with self.assertRaises(registry.RegistryError):
            self.reg.import_data(data)
        self.assertEqual([job["id"] for job in self.reg.list_jobs()], [existing["id"]])
        data["version"] += 1
        with self.assertRaises(registry.RegistryError):
            self.reg.import_data(data)


if __name__ == "__main__":
    unittest.main()
