"""The complete registry exchange keeps tasks and their stable relationships."""

import copy
import tempfile
import unittest
from pathlib import Path

import _setup  # noqa: F401
from meridiana import registry


class TaskExchangeTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.source = registry.Registry(self.root / "source.sqlite3")
        self.target = registry.Registry(self.root / "target.sqlite3")
        self.addCleanup(self.source.close)
        self.addCleanup(self.target.close)

    def test_tasks_roundtrip_with_links_due_dates_and_completed_state(self):
        reg = self.source
        client = reg.create_client("Example client")
        job = reg.create_job("26042", "Example job", client["id"], reserved=True)
        project = reg.link_project(job["id"], self.root / "example.meridiana", "Example design")
        linked = reg.create_task("Check network", "2026-11-01", job["id"], project["id"])
        personal = reg.create_task("Review catalogue")
        reg.update_task(personal["id"], done=True)
        path = self.root / "registry.json"
        reg.export(path)
        data = registry.read_exchange(path)
        self.assertEqual(self.target.preview_import(data)["new"], 5)
        self.target.import_data(data)
        self.assertEqual(self.target.task(linked["id"]), reg.task(linked["id"]))
        self.assertEqual(self.target.task(personal["id"]), reg.task(personal["id"]))
        self.assertEqual(self.target.preview_import(data)["unchanged"], 5)
        reg.update_task(linked["id"], done=True, text="Check supply")
        self.target.import_data(reg.export_data())
        self.assertEqual(len(self.target.list_tasks(include_done=True)), 2)
        self.assertEqual(self.target.task(linked["id"])["text"], "Check supply")
        self.assertTrue(self.target.task(linked["id"])["done"])

    def test_legacy_exchanges_without_tasks_keep_existing_local_tasks(self):
        task = self.target.create_task("Local task")
        data = self.source.export_data()
        data.pop("tasks", None)
        self.target.import_data(data)
        self.assertEqual(self.target.task(task["id"])["text"], "Local task")

    def test_invalid_tasks_and_duplicate_ids_are_rejected_before_writing(self):
        task = self.source.create_task("Example task")
        data = self.source.export_data()
        self.assertIn("tasks", data)
        for field, value in (("text", ""), ("due", "tomorrow"), ("done", "false"), ("job_id", 3)):
            changed = copy.deepcopy(data)
            changed["tasks"][0][field] = value
            with self.subTest(field=field), self.assertRaises(registry.RegistryError):
                self.target.preview_import(changed)
        duplicate = {**data, "tasks": [data["tasks"][0], data["tasks"][0]]}
        self.assertTrue(self.target.preview_import(duplicate)["conflicts"])
        with self.assertRaises(registry.RegistryError):
            self.target.import_data(duplicate)
        missing = copy.deepcopy(data)
        missing["tasks"][0]["project_id"] = "missing-project"
        with self.assertRaises(registry.RegistryError):
            self.target.import_data(missing)
        self.assertIsNone(self.target.task(task["id"]))
