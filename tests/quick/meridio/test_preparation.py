"""Panel preparation stays away from the GUI and queues exactly one question."""
import threading
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from _setup import wait_until
from _fakes import FakeRuntime, ollama_answer
from meridiana.app.platform.config import Config
from meridiana.app.assistant import preparation
from meridiana.gui.backend.assistant_chat import AssistantChat
from quick.meridio.support import Host, Voice, KeyStore


class PanelPreparationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.server = FakeRuntime({"/api/ps": {"models": []},
                                   "/api/tags": {"models": [{"name": "qwen3.5:9b", "size": 6600000000}]},
                                   "_shows": {"qwen3.5:9b": {"capabilities": ["tools"]}}},
                                  chat=[ollama_answer("invisible"), ollama_answer("visible")])
        self.addCleanup(self.server.close)
        self.chat = AssistantChat(Host(), Config(assistant_introduced=True, assistant_local_runtime="ollama",
                                  assistant_local_url=self.server.base, assistant_local_model="qwen3.5:9b"),
                                  voice=Voice(), key_store=KeyStore())
        self.addCleanup(self.chat.close)

    def test_open_and_focus_prepare_once_and_question_waits_off_thread(self):
        entered, release = threading.Event(), threading.Event()
        original = preparation.prepare
        threads = []
        def slow(*args):
            threads.append(threading.get_ident())
            entered.set()
            release.wait(3)
            return original(*args)
        with patch.object(preparation, "prepare", side_effect=slow), patch.object(
                preparation, "system_memory", return_value=(32e9, 12e9)):
            self.chat.setOpened(True)
            self.assertTrue(wait_until(self.app, entered.is_set, 2))
            self.chat.prepareLocal()
            self.chat.setOpened(True)
            self.assertTrue(self.chat.preparing)
            self.assertEqual(self.chat.preparationText, "Preparing the model\u2026")
            self.chat.ask("hello")
            self.assertFalse(self.server.requests)
            release.set()
            self.assertTrue(wait_until(self.app, lambda: not self.chat.preparing and not self.chat.busy, 5))
        bodies = [b for path, b in self.server.requests if path == "/api/chat"]
        self.assertEqual(len(bodies), 2)
        self.assertEqual(bodies[0]["messages"], bodies[1]["messages"][:1])
        self.assertEqual(bodies[0]["tools"], bodies[1]["tools"])
        self.assertNotIn(threading.get_ident(), threads)
        self.assertEqual(len(threads), 1)
        self.assertFalse(any("invisible" in str(row) for row in self.chat.messages))
        self.assertEqual(sum(row["outgoing"] for row in self.chat.messages), 1)

    def test_low_ram_is_shown_without_prefill(self):
        with patch.object(preparation, "system_memory", return_value=(32e9, 1e9)):
            self.chat.setOpened(True)
            self.assertTrue(wait_until(self.app, lambda: not self.chat.preparing, 30))     # a condition: the limit only for a stuck one
        self.assertIn("free memory", self.chat.preparationText)
        self.assertFalse([b for path, b in self.server.requests if path == "/api/chat"])

    def test_startup_is_opt_in_delayed_until_window_ready_and_cancellable_on_close(self):
        self.assertFalse(self.chat.cfg.assistant_prepare_on_start)
        with patch.object(preparation, "prepare", return_value="prepared") as prepare:
            self.chat.windowReady()
            self.assertFalse(self.chat.startup_timer.isActive())
            self.chat.cfg.assistant_prepare_on_start = True
            self.chat.windowReady()
            self.assertTrue(self.chat.startup_timer.isActive())
            self.assertFalse(prepare.called)
            self.chat.startup_timer.setInterval(20)
            self.assertTrue(wait_until(self.app, lambda: prepare.called and not self.chat.preparing, 3))
            self.assertEqual(prepare.call_count, 1)
            self.chat.close()
            self.assertFalse(self.chat.startup_timer.isActive())

    def test_explicit_large_model_is_preserved(self):
        self.chat.cfg.assistant_local_model = "qwen3.6:35b-a3b"
        self.assertEqual(self.chat.make_local().model, "qwen3.6:35b-a3b")
        self.assertEqual(self.chat.cfg.assistant_local_model, "qwen3.6:35b-a3b")

    def test_close_discards_the_question_waiting_for_preparation(self):
        entered, release = threading.Event(), threading.Event()
        def slow(*_args):
            entered.set()
            release.wait(3)
            return "loaded"
        with patch.object(preparation, "prepare", side_effect=slow):
            self.chat.setOpened(True)
            self.assertTrue(wait_until(self.app, entered.is_set, 2))
            self.chat.ask("hello")
            self.chat.close()
            release.set()
            self.assertTrue(wait_until(self.app, lambda: not self.chat.preparing, 3))
        self.assertFalse(self.server.requests)
