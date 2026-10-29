"""Meridio opens a project only after the card and the normal unsaved-changes choice (R151)."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup
from _fixtures import capannone

from meridiana.assistant import tools

setUpModule = _setup.keep_global_state


class MeridioProjectsWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def prepared(self, win, path):
        row = {"path": str(path), "name": path.stem, "title": "Target project", "series_id": "target",
               "revision": "R07", "modified": "2026-10-29T10:00:00+00:00", "kind": "roof",
               "power_kwp": 57.6, "job_code": "26042", "job_name": "Target project",
               "client_name": "Example client", "address": "Example town", "reserved": False, "error": ""}
        chat = win.assistant_chat
        with mock.patch.object(win.registry, "list_index", return_value=[row]):
            found = tools.run("search_projects", {"query": "Target"}, chat.host, chat.conversation.state)
            self.assertFalse(found.error)
            outcome = tools.run("prepare_open_project", {"project_id": "pr1"}, chat.host, chat.conversation.state)
        chat._tool_done(None, outcome)
        return outcome.proposal

    def test_the_card_shows_path_and_revision_and_discard_allows_opening(self):
        from PySide6.QtWidgets import QLabel
        target = Path(tempfile.mkdtemp()) / "target_R07.meridiana"
        capannone("Target project").save(target)
        win = _setup.window(self, capannone("Current project"))
        proposal = self.prepared(win, target)
        card = self.chat_card(win, proposal)
        text = "\n".join(label.text() for label in card.findChildren(QLabel))
        self.assertIn(str(target), text)
        self.assertIn("R07", text)
        self.assertEqual(win.project.name, "Current project")
        win.edit("Change", lambda project: setattr(project, "name", "Unsaved project"))
        card.buttons["apply"].click()
        self.assertEqual(win.project.name, "Target project")
        self.assertEqual(win.path, target)
        self.assertEqual(proposal.state, "applied")

    def test_cancelling_the_unsaved_choice_keeps_the_project_and_the_card(self):
        from PySide6.QtWidgets import QMessageBox
        target = Path(tempfile.mkdtemp()) / "target_R07.meridiana"
        capannone("Target project").save(target)
        win = _setup.window(self, capannone("Current project"),
                            answers={"question": QMessageBox.StandardButton.Cancel})
        proposal = self.prepared(win, target)
        card = self.chat_card(win, proposal)
        win.edit("Change", lambda project: setattr(project, "name", "Unsaved project"))
        card.buttons["apply"].click()
        self.assertEqual(win.project.name, "Unsaved project")
        self.assertNotEqual(win.path, target)
        self.assertEqual(proposal.state, "pending")
        self.assertIn(proposal.id, win.assistant_chat.cards)

    @staticmethod
    def chat_card(win, proposal):
        return win.assistant_chat.cards[proposal.id]


if __name__ == "__main__":
    unittest.main()
