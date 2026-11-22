"""A long answer of a tool comes in pages (study 50, 3.3 point 3 and 7.2 point 7): until now beyond RESULT_LIMIT the
model got the text cut in the middle, inside {"truncated": true, "part": ...} (6.511 characters of read_checks on the
test project). Now every page is whole JSON within the limit, says which page it is and how many there are, and
read_more gives the others. No Qt, no model."""

import json
import unittest

import _setup  # noqa: F401
from _fakes import Host, with_problems
from _fixtures import capannone_rho

from meridiana.app.assistant import conversation, tools
from meridiana.app.assistant.providers import ToolCall
from meridiana.core.rules import checks


def many_checks_host() -> Host:
    p = capannone_rho()
    p.subfields[0].filled = True
    host = with_problems(Host(p))
    host._checks = [checks.Item("warn", "layout", f"Sottocampo {n}: la fila {n} è più corta del previsto, "
                                "controlla i margini dal bordo e il passo delle file", "Meridiana",
                                ("subfield", "s1")) for n in range(1, 61)]
    return host


class Pages(unittest.TestCase):
    def test_a_long_answer_comes_in_whole_pages_and_read_more_gives_the_rest(self):
        host = many_checks_host()
        state = tools.State()
        first = tools.run("read_checks", {"min_level": "info"}, host, state)
        self.assertLessEqual(len(first.content), tools.RESULT_LIMIT)
        page = json.loads(first.content)                 # whole JSON, not a piece of text
        self.assertNotIn("truncated", page)
        info = page["answer_page"]
        self.assertEqual(info["page"], 1)
        self.assertGreater(info["pages"], 1)
        self.assertIn("read_more", info["next"])
        self.assertEqual(page["project_counts"]["warn"], 60)      # what is not the list stays on the first page
        texts = [c["text"] for c in page["checks"]]
        for n in range(2, info["pages"] + 1):
            more = tools.run("read_more", {"answer_id": info["answer_id"], "page": n}, host, state)
            self.assertFalse(more.error, more.content)
            self.assertLessEqual(len(more.content), tools.RESULT_LIMIT)
            rest = json.loads(more.content)
            self.assertEqual(rest["answer_page"]["page"], n)
            texts += [c["text"] for c in rest["checks"]]
        self.assertEqual(len(texts), 60)
        self.assertEqual(len(set(texts)), 60)
        last = json.loads(tools.run("read_more", {"answer_id": info["answer_id"], "page": info["pages"]},
                                    host, state).content)
        self.assertNotIn("read_more", last["answer_page"]["next"])

    def test_a_page_out_of_range_or_an_unknown_answer_is_said(self):
        host = many_checks_host()
        state = tools.State()
        info = json.loads(tools.run("read_checks", {"min_level": "info"}, host, state).content)["answer_page"]
        self.assertTrue(tools.run("read_more", {"answer_id": info["answer_id"], "page": 99}, host, state).error)
        self.assertTrue(tools.run("read_more", {"answer_id": "a77", "page": 2}, host, state).error)
        self.assertFalse(tools.run("read_more", {"answer_id": info["answer_id"], "page": 2.0}, host, state).error)

    def test_an_answer_without_a_list_to_divide_is_paged_as_text_and_comes_back_whole(self):
        long = {"text": "Una frase lunga, con \"virgolette\" e accenti: è così. " * 300}
        pages = tools.pages_of(json.dumps(long, ensure_ascii=False), tools.RESULT_LIMIT - tools.PAGE_ROOM)
        self.assertGreater(len(pages), 1)
        for p in pages:
            self.assertLessEqual(len(json.dumps(p, ensure_ascii=False)), tools.RESULT_LIMIT - tools.PAGE_ROOM)
        self.assertEqual(json.loads("".join(p["part"] for p in pages)), long)

    def test_a_short_answer_is_left_as_it_is(self):
        host = many_checks_host()
        out = json.loads(tools.run("read_checks", {"min_level": "fail"}, host, tools.State()).content)
        self.assertNotIn("answer_page", out)

    def test_in_the_conversation_the_model_gets_the_first_page_and_can_ask_for_the_next(self):
        host = many_checks_host()
        conv = conversation.Conversation()
        conv.ask("Tutte le verifiche?")
        conv.run_tools([ToolCall("c1", "read_checks", {"min_level": "info"})], host)
        info = json.loads(conv.messages[-1]["content"])["answer_page"]
        conv.run_tools([ToolCall("c2", "read_more", {"answer_id": info["answer_id"], "page": 2})], host)
        self.assertEqual(json.loads(conv.messages[-1]["content"])["answer_page"]["page"], 2)
        self.assertIn("read_more", [t["name"] for t in tools.specs()])


if __name__ == "__main__":
    unittest.main()
