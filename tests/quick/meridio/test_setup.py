"""R105/R389: configuration and asynchronous local survey, no real credentials."""
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PySide6.QtWidgets import QApplication

from _setup import wait_until
from meridiana import config
from meridiana.assistant import local, setup
from meridiana.quick.backend.assistant_local import LocalModels
from meridiana.quick.backend.assistant_setup import AssistantSetup


class SetupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.cfg = config.Config()
        self.stored = {}
        self.keys = SimpleNamespace(get=lambda key: self.stored.get(key, ""),
                                    put=lambda key, value: self.stored.__setitem__(key, value))
        self.save = Mock()
        self.backend = AssistantSetup(self.cfg, self.save, key_store=self.keys)

    def test_every_provider_saves_profile_and_key_separately_without_request(self):
        with patch.object(setup, "make", side_effect=AssertionError("No model request during setup")):
            for key, spec in setup.CLOUD.items():
                with self.subTest(provider=key):
                    self.assertTrue(self.backend.saveCloud(key, "test-model", spec.endpoint, "synthetic-key"))
                    self.assertEqual(self.cfg.assistant_provider, key)
                    self.assertEqual(setup.profile(self.cfg, key)["model"], "test-model")
                    self.assertNotIn("synthetic-key", str(vars(self.cfg)))
                    self.assertEqual(self.stored[key], "synthetic-key")
        self.assertEqual(self.save.call_count, len(setup.CLOUD))

    def test_invalid_endpoint_or_missing_key_changes_no_profile(self):
        self.assertFalse(self.backend.saveCloud("openai", "test", "http://unsafe.example", "key"))
        self.assertFalse(self.backend.saveCloud("openai", "test", setup.CLOUD["openai"].endpoint, ""))
        self.assertFalse(self.stored)
        self.save.assert_not_called()

    def test_existing_key_can_be_kept_and_provider_fields_follow_selection(self):
        self.stored["openai"] = "synthetic-key"
        self.assertTrue(self.backend.saveCloud("openai", "test", setup.CLOUD["openai"].endpoint, ""))
        self.backend.chooseProvider("openai")
        self.assertEqual(self.backend.model, "test")
        self.backend.chooseProvider("claude")
        self.assertEqual(self.backend.provider, "anthropic")
        self.assertEqual(self.backend.accountUrl, setup.CLOUD["anthropic"].docs)

    def test_local_selection_persists_runtime(self):
        self.backend.saveLocal("http://127.0.0.1:11434", "gemma4", "ollama")
        self.assertEqual(self.cfg.assistant_provider, "local")
        self.assertEqual(self.cfg.assistant_local_model, "gemma4")
        self.assertEqual(self.cfg.assistant_local_runtime, "ollama")
        self.save.assert_called_once()

    def test_survey_runs_off_thread_and_model_choice_keeps_disabled_models_disabled(self):
        threads = []
        model = local.Model("qwen3.6:4b", size=3_000_000_000, tools=True)
        runtime = local.Runtime("ollama", "http://127.0.0.1:11434", running=True,
                                models=[model, local.Model("blind-to-tools", tools=False)])
        found = local.Survey([runtime], local.Machine(32), local.Choice(runtime, model, local.match(model.name), True))

        def survey(**kwargs):
            threads.append(threading.get_ident())
            return found

        backend = LocalModels(survey=survey)
        selected = []
        backend.chosen.connect(lambda *args: selected.append(args))
        backend.start()
        self.assertTrue(wait_until(self.app, lambda: not backend.busy, 5))
        self.assertNotEqual(threads[0], threading.get_ident())
        self.assertTrue(backend.models[0]["recommended"])
        backend.useSelected()
        self.assertEqual(selected, [(runtime.url, model.name, "ollama")])
        backend.select(1)
        backend.useSelected()
        self.assertEqual(len(selected), 1)

    def test_probe_runs_off_thread_and_guide_covers_missing_ram(self):
        threads = []

        def check(provider):
            threads.append(threading.get_ident())
            return local.Check(True, tools=True)

        backend = LocalModels(current=lambda: ("http://127.0.0.1:11434", "fake", "ollama"), check=check)
        backend.probe()
        self.assertTrue(wait_until(self.app, lambda: not backend.testing, 5))
        self.assertNotEqual(threads[0], threading.get_ident())
        self.assertTrue(backend.testStatus)
        backend.show_survey(local.Survey())
        self.assertTrue(backend.needsRam)
        backend.setRam(16)
        self.assertFalse(backend.needsRam)
        self.assertTrue(any(row["command"] for row in backend.guide))

