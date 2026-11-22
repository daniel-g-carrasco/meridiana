"""Local prefill: synthetic servers and available memory, never the user's runtime."""
import unittest
from unittest.mock import patch

import _setup  # noqa: F401
from _fakes import FakeRuntime, ollama_answer
from meridiana.app.assistant import preparation, providers


class PreparationTest(unittest.TestCase):
    def server(self, loaded=False):
        s = FakeRuntime({"/api/ps": {"models": [{"name": "qwen3.5:9b"}] if loaded else []},
                         "/api/tags": {"models": [{"name": "qwen3.5:9b", "size": 6600000000}]},
                         "_shows": {"qwen3.5:9b": {"capabilities": ["tools", "thinking"]}}},
                        chat=[ollama_answer("hidden"), ollama_answer("visible")])
        self.addCleanup(s.close)
        return s, providers.Ollama(model="qwen3.5:9b", base_url=s.base)

    def test_prefill_and_question_share_prefix_tools_and_resident_options(self):
        s, p = self.server()
        specs = [{"name": "ping", "description": "test", "parameters": {"type": "object"}}]
        with patch.object(preparation, "system_memory", return_value=(32e9, 12e9)):
            self.assertEqual(preparation.prepare(p, "fixed", specs), "prepared")
        list(p.stream("fixed", [{"role": "user", "content": "hello"}], specs))
        first, second = [body for path, body in s.requests if path == "/api/chat"]
        self.assertEqual(first["messages"], second["messages"][:1])
        self.assertEqual(first["tools"], second["tools"])
        self.assertEqual(first["options"]["num_ctx"], second["options"]["num_ctx"])
        self.assertEqual(first["think"], second["think"])
        self.assertEqual(first["keep_alive"], "30m")
        self.assertEqual(first["options"]["num_predict"], 1)

    def test_loaded_model_is_not_prepared_again_even_when_ram_is_low(self):
        s, p = self.server(loaded=True)
        with patch.object(preparation, "system_memory", return_value=(32e9, 1e9)):
            self.assertEqual(preparation.prepare(p, "S", []), "loaded")
        self.assertFalse(s.requests)

    def test_available_ram_not_total_controls_prefill_and_unknown_is_skipped(self):
        for memory in ((32e9, 1e9), None):
            s, p = self.server()
            with patch.object(preparation, "system_memory", return_value=memory):
                self.assertEqual(preparation.prepare(p, "S", []), "memory")
            self.assertFalse([b for path, b in s.requests if path == "/api/chat"])

    def test_setting_migrates_to_off_and_explicit_true_survives_roundtrip(self):
        from meridiana.app.platform.config import Config, migrate
        self.assertFalse(Config().assistant_prepare_on_start)
        old = migrate({"version": 35})
        self.assertFalse(old["assistant_prepare_on_start"])
        explicit = Config.from_json({"version": 35, "assistant_prepare_on_start": True})
        self.assertTrue(Config.from_json(explicit.to_json()).assistant_prepare_on_start)

    def test_two_clients_recheck_residency_and_prefill_only_once(self):
        from concurrent.futures import ThreadPoolExecutor
        s, p = self.server()
        s.routes["/api/ps"] = lambda _handler: {"models": [{"name": p.model}]
            if any(path == "/api/chat" for path, _ in s.requests) else []}
        q = providers.Ollama(model=p.model, base_url=s.base)
        with patch.object(preparation, "system_memory", return_value=(32e9, 12e9)):
            with ThreadPoolExecutor(max_workers=2) as pool:
                a = pool.submit(preparation.prepare, p, "S", [])
                b = pool.submit(preparation.prepare, q, "S", [])
                self.assertEqual(sorted([a.result(), b.result()]), ["loaded", "prepared"])
        self.assertEqual(len([body for path, body in s.requests if path == "/api/chat"]), 1)
