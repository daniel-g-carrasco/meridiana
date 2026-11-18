"""The synchronous conversation restores aliases only when executing local tool arguments."""

import copy
import json
import unittest
from types import SimpleNamespace

import _setup  # noqa: F401
from _fixtures import capannone
from meridiana.assistant import conversation, privacy, providers


class ArchiveAliasRoundtripTest(unittest.TestCase):
    def test_synchronous_cloud_search_restores_names_without_sending_them(self):
        row = {"path": "/jobs/example.meridiana", "job_code": "26042", "kind": "roof", "reserved": False}
        redactor = privacy.Redactor.of(capannone("Current design")).with_archive([row])
        alias = redactor.redact("26042")
        sent = []

        def stream(system, messages, specs):
            sent.append(copy.deepcopy(messages))
            if len(sent) == 1:
                return iter([providers.ToolCall("c1", "search_projects", {"query": alias}), providers.Done("tools")])
            return iter([providers.Text("Fine."), providers.Done("end")])

        provider = SimpleNamespace(cloud=True, family="test", model="test", stream=stream)
        host = SimpleNamespace(index_rows=lambda: [row])
        current = conversation.Conversation()
        conversation.answer(current, provider, "Test", "Apri 26042", host,
                            prepare=redactor.messages, restore=redactor.restore)
        result = next(m for m in current.messages if m["role"] == "tool")
        self.assertEqual(len(json.loads(result["content"])["projects"]), 1)
        self.assertNotIn("26042", json.dumps(sent))
        call = next(m for m in current.messages if m["role"] == "assistant")["calls"][0]
        self.assertEqual(call["arguments"]["query"], alias)
