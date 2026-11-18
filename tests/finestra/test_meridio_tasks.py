"""Meridio creates and completes registry tasks only after the designer clicks (R151)."""

import json
import unittest

import _setup
from _fixtures import capannone

from meridiana.assistant import tools

setUpModule = _setup.keep_global_state


class MeridioTasksWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_task_cards_create_and_complete_only_on_confirmation(self):
        win = _setup.window(self, capannone())
        client = win.registry.create_client("Example client")
        job = win.registry.create_job("26042", "Example job", client["id"])
        chat = win.assistant_chat
        state = chat.conversation.state
        outcome = tools.run("prepare_task", {"action": "create", "text": "Check the grid connection",
                                             "due": "2026-11-02", "job_id": job["id"]}, chat.host, state)
        self.assertEqual(win.registry.list_tasks(), [])
        chat._tool_done(None, outcome)
        chat.cards[outcome.proposal.id].buttons["apply"].click()
        tasks = win.registry.list_tasks()
        self.assertEqual([task["text"] for task in tasks], ["Check the grid connection"])
        listed = tools.run("list_tasks", {}, chat.host, state)
        task_id = json.loads(listed.content)["tasks"][0]["id"]
        completed = tools.run("prepare_task", {"action": "complete", "task_id": task_id}, chat.host, state)
        self.assertFalse(tasks[0]["done"])
        chat._tool_done(None, completed)
        chat.cards[completed.proposal.id].buttons["apply"].click()
        self.assertTrue(win.registry.list_tasks(include_done=True)[0]["done"])


if __name__ == "__main__":
    unittest.main()
