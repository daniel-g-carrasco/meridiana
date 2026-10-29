"""The real chat applies the archive privacy filter before its fake Claude provider (R151)."""

import json
import unittest
from types import SimpleNamespace
from unittest import mock

import _setup
from _fakes import FakeAnthropic, FakeServer, text_answer
from _fixtures import capannone

from meridiana import assistant, config
from meridiana.assistant import providers

setUpModule = _setup.keep_global_state


def project_row(title, reserved=False):
    return {"path": f"/jobs/{title}_R01.meridiana", "name": f"{title}_R01", "title": title,
            "series_id": title, "revision": "R01", "revision_number": 1, "modified": "2026-10-01T10:00:00+00:00",
            "file_modified": "2026-10-01T10:00:00+00:00", "kind": "roof", "power_kwp": 100.0,
            "mountings": ["tilted_anchored"], "tilts": [15.0], "lat": 45.5, "lon": 9.0,
            "address": "Example town", "job_id": "job1", "job_code": "26042", "job_name": title,
            "client_name": "Example client", "reserved": reserved, "error": ""}


class MeridioPrivacyWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, capannone("Current project"),
                      cfg=config.Config(background="none", assistant_provider="claude"))
        self.chat = self.win.assistant_chat
        self.chat.keys = SimpleNamespace(get=lambda family: "sk-ant-api-test-0123456789")
        self.client = FakeAnthropic([[("tool", "search_projects", {"query": "shed"})], [("text", "Fatto.")]])
        self.chat.make_cloud = lambda key: providers.Anthropic(model=self.cfg.assistant_cloud_model, key=key,
                                                               client=self.client)
        self.local = FakeServer([text_answer("Risponde il modello locale.")] * 2)
        self.addCleanup(self.local.close)
        self.chat.make_local = lambda: providers.OpenAICompatible(base_url=self.local.url)
        self.rows = [project_row("Public shed"), project_row("Secret client", reserved=True)]
        patch = mock.patch.object(self.win.registry, "list_index", return_value=self.rows)
        patch.start()
        self.addCleanup(patch.stop)
        self.cfg.assistant_consent = {"anthropic": ["2026-10-24"]}
        self.win.assistant.reduced_motion = True
        self.win.assistant.open_panel()

    def idle(self):
        return _setup.wait_until(self.app, lambda: self.win.assistant.mood.state == assistant.IDLE
                                 and self.chat.job is None, 10)

    def test_cloud_messages_have_no_archive_names_paths_or_reserved_rows(self):
        self.win.assistant.ask("Cerca Public shed e Secret client")
        self.assertTrue(self.idle())
        self.assertEqual(len(self.client.calls), 2)
        sent = json.dumps(self.client.calls, default=str)
        for secret in ("Public shed", "Secret client", "/jobs", "26042", "Example client"):
            self.assertNotIn(secret, sent)
        messages = self.client.calls[1]["messages"]
        blocks = [block for message in messages for block in
                  (message.get("content") if isinstance(message.get("content"), list) else [])
                  if isinstance(block, dict) and block.get("type") == "tool_result"]
        result = json.loads(blocks[-1]["content"])
        self.assertEqual(len(result["projects"]), 1)
        self.assertEqual(result["projects"][0]["id"], "pr1")
        self.assertNotIn("path", result["projects"][0])
        self.assertNotIn("title", result["projects"][0])

    def test_a_reserved_archive_question_goes_to_the_local_provider(self):
        self.win.assistant.ask("Cerca anche nei progetti riservati")
        self.assertTrue(self.idle())
        self.assertEqual(self.client.calls, [])
        self.assertEqual(len(self.local.requests), 1)


if __name__ == "__main__":
    unittest.main()
