"""Support drafts remain local, redact diagnostics and never replace a file."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from PySide6.QtCore import QObject
from meridiana.session import ProjectSession
from meridiana.quick.backend.files_actions import FileActions


class FileActionsTest(unittest.TestCase):
    def setUp(self):
        self.owner = QObject()
        self.owner.session = ProjectSession()
        self.owner.root = SimpleNamespace(property=lambda _name: 'model')
        self.actions = FileActions(self.owner)

    def test_draft_redacts_only_opted_in_diagnostics_and_saves_exclusively(self):
        self.actions.setDraft('title', 'A title')
        self.actions.setDraft('description', 'Steps and expected result')
        self.actions.setDraft('diagnostics', 'api_key=private\nC:\\Users\\Name\\file.txt')
        self.assertNotIn('redacted', self.actions.preview)
        self.actions.setDraft('include_diagnostics', True)
        self.assertNotIn('private', self.actions.preview)
        self.assertNotIn('Name', self.actions.preview)
        self.assertIn('[redacted]', self.actions.preview)
        self.assertTrue(self.actions.canShare)
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / 'draft.txt'
            self.actions.saveDraft(str(path))
            saved = path.read_text(encoding='utf8')
            self.actions.setDraft('description', 'Changed draft')
            self.actions.saveDraft(str(path))
            self.assertEqual(saved, path.read_text(encoding='utf8'))
            self.assertTrue(self.actions.status)
