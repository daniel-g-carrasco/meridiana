"""Meridio remembers local tasks and only prepares changes to them (R151)."""

import json
import tempfile
import unittest
from pathlib import Path

import _setup  # noqa: F401

from meridiana import registry
from meridiana.assistant import tools


class TaskHost:
    def __init__(self, reg):
        self.registry = reg

    def task_rows(self):
        return self.registry.list_tasks(include_done=True)


class MeridioTasksTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.reg = registry.Registry(self.folder / "registry.sqlite3")
        self.addCleanup(self.reg.close)
        client = self.reg.create_client("Example client")
        self.job = self.reg.create_job("26042", "Example job", client["id"])

    def test_tasks_persist_with_due_dates_and_completion_is_explicit(self):
        self.reg.link_project(self.job["id"], self.folder / "shed_R01.meridiana", "Example shed",
                              project_id="series1", revision="R01")
        task = self.reg.create_task("Check the grid connection", due="2026-11-02", job_id=self.job["id"],
                                    project_id="series1")
        self.assertEqual(self.reg.list_tasks(), [task])
        self.reg.update_task(task["id"], done=True)
        self.assertEqual(self.reg.list_tasks(), [])
        self.assertTrue(self.reg.list_tasks(include_done=True)[0]["done"])
        self.reg.close()
        self.reg = registry.Registry(self.folder / "registry.sqlite3")
        self.addCleanup(self.reg.close)
        self.assertEqual(self.reg.list_tasks(include_done=True)[0]["text"], "Check the grid connection")
        with self.assertRaises(registry.RegistryError):
            self.reg.create_task("Invalid date", due="next week")

    def test_prepare_task_never_writes_and_cloud_omits_reserved_tasks(self):
        host = TaskHost(self.reg)
        state = tools.State()
        outcome = tools.run("prepare_task", {"action": "create", "text": "Request the POD curve",
                                             "due": "2026-11-03", "job_id": self.job["id"]}, host, state)
        self.assertEqual(outcome.proposal.kind, "task")
        self.assertEqual(self.reg.list_tasks(), [])
        created = self.reg.create_task("Public task", job_id=self.job["id"])
        reserved_job = self.reg.create_job("26043", "Reserved job", self.job["client_id"], reserved=True)
        self.reg.create_task("Secret task", job_id=reserved_job["id"])
        cloud = tools.State(cloud=True)
        listed = tools.run("list_tasks", {}, host, cloud)
        result = json.loads(listed.content)
        self.assertEqual([item["text"] for item in result["tasks"]], ["Public task"])
        self.assertNotIn("Secret task", listed.content)
        self.assertNotIn("Reserved job", listed.content)
        local_state = tools.State()
        local = tools.run("list_tasks", {}, host, local_state)
        task_id = json.loads(local.content)["tasks"][0]["id"]
        completed = tools.run("prepare_task", {"action": "complete", "task_id": task_id}, host, local_state)
        self.assertEqual(completed.proposal.item["task_id"], created["id"])
        self.assertFalse(self.reg.task(created["id"])["done"])


if __name__ == "__main__":
    unittest.main()
