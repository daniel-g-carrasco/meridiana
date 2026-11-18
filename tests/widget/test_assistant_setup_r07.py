"""The setup works before an LLM exists, and never puts the key in settings."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import _setup
setUpModule = _setup.keep_global_state


class SetupCard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_cloud_save_stays_local_and_password_is_cleared(self):
        from meridiana.ui.assistant_setup import AssistantSetup
        from PySide6.QtWidgets import QLineEdit
        cfg = SimpleNamespace(assistant_cloud_profiles={}, assistant_cloud_model='', assistant_provider='local')
        card = AssistantSetup(cfg, lambda: None)
        self.addCleanup(card.deleteLater)
        card.provider.setCurrentIndex(card.provider.findData('mistral'))
        card.model.setText('mistral-small-latest')
        card.key.setText('private-test-key')
        saved = []
        card.configured.connect(saved.append)
        with patch('meridiana.assistant.keys.put') as put:
            card.save_cloud()
            put.assert_called_once_with('mistral', 'private-test-key')
        self.assertEqual(card.key.echoMode(), QLineEdit.EchoMode.Password)
        self.assertEqual(card.key.text(), '')
        self.assertEqual(saved, ['mistral'])
        self.assertNotIn('private-test-key', repr(vars(cfg)))
        self.assertEqual(cfg.assistant_cloud_profiles['mistral']['model'], 'mistral-small-latest')

    def test_no_model_does_not_save_credentials(self):
        from meridiana.ui.assistant_setup import AssistantSetup
        cfg = SimpleNamespace(assistant_cloud_profiles={}, assistant_cloud_model='', assistant_provider='local')
        card = AssistantSetup(cfg, lambda: None)
        self.addCleanup(card.deleteLater)
        card.key.setText('private-test-key')
        with patch('meridiana.assistant.keys.put') as put:
            card.save_cloud()
        put.assert_not_called()
        self.assertEqual(cfg.assistant_cloud_profiles, {})

    def test_voice_edit_in_preferences_preserves_the_selected_provider_and_profiles(self):
        from meridiana import config
        from meridiana.ui.preferences import MeridioPage
        cfg = config.Config(assistant_provider='gemini', assistant_cloud_profiles={
            'gemini': {'model': 'my-model', 'endpoint': 'https://generativelanguage.googleapis.com/v1beta/openai'}})
        with patch('meridiana.assistant.keys.get', return_value=''):
            page = MeridioPage(cfg)
        self.addCleanup(page.deleteLater)
        page.voice.setChecked(True)
        choice = page.choice()
        self.assertEqual(choice['assistant_provider'], 'gemini')
        self.assertEqual(choice['assistant_cloud_profiles'], cfg.assistant_cloud_profiles)
