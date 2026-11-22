"""Meridio searches the catalogue, read only (study 50, 5.1 and 5.2; 7.2 point 4): search_catalog finds products by
words, kind, power and state, gives a few rows in the designer's words (maker, model, data with units, origin, state)
and changes nothing. The first reading of the 21,000 modules takes more than a second: in the window it runs away from
its thread before the tools of the round (tools.slow_reads), as the catalogue page reads it. No Qt, no network."""

import json
import unittest
from unittest import mock

import _setup  # noqa: F401
from _fakes import Host
from _fixtures import capannone_rho

from meridiana.app.assistant import conversation, tools
from meridiana.app.assistant.providers import ToolCall
from meridiana.data import catalog


def ask(**arguments) -> tuple[dict, tools.Outcome]:
    outcome = tools.run("search_catalog", arguments, Host(capannone_rho()), tools.State())
    return json.loads(outcome.content), outcome


def record(identifier: str, kind: str) -> dict:
    return next(r for r in catalog.load(kind) if r.get("id") == identifier)


class SearchCatalog(unittest.TestCase):
    def test_it_finds_by_words_and_says_each_product_in_the_designers_words(self):
        out, outcome = ask(kind="inverters", query="huawei")
        self.assertFalse(outcome.error, outcome.content)
        self.assertLessEqual(len(outcome.content), tools.RESULT_LIMIT)
        self.assertGreater(out["found"], 0)
        self.assertLessEqual(len(out["products"]), tools.CATALOG_ROWS)
        first = out["products"][0]
        self.assertEqual(first["manufacturer"].casefold(), "huawei")
        self.assertIn("Nominal AC power", first["data"])
        self.assertTrue(first["data"]["Nominal AC power"].endswith(" W"))
        self.assertIn(first["origin"], ("Datasheets read for Meridiana", "Personal catalogue"))
        self.assertIn(first["state"], ("Current", "Phasing out", "Out of production", "State unknown"))
        for row in out["products"]:                              # never an internal key as a name
            self.assertNotIn("ac_power_nominal_w", json.dumps(row["data"]))

    def test_power_and_state_filter_and_the_us_list_only_when_asked(self):
        out, _o = ask(kind="inverters", power_from=50000, power_to=100000)
        self.assertTrue(out["products"])
        for row in out["products"]:
            self.assertTrue(50000 <= catalog.power_of(record(row["id"], "inverters"), "inverters") <= 100000)
            self.assertNotEqual(record(row["id"], "inverters").get("source"), "cec")
        current, _o = ask(kind="modules", query="jinko", state_of_production="current")
        for row in current["products"]:
            self.assertEqual(catalog.lifecycle_state(record(row["id"], "modules")), "current")
        us, _o = ask(kind="inverters", query="SMA", include_us_list=True)
        plain, _o = ask(kind="inverters", query="SMA")
        self.assertGreater(us["found"], plain["found"])

    def test_nothing_found_a_wrong_kind_and_a_wrong_state_are_said(self):
        none, outcome = ask(kind="batteries", query="zzzz-nessuno")
        self.assertFalse(outcome.error)
        self.assertEqual(none["products"], [])
        self.assertIn("message", none)
        self.assertTrue(ask(kind="cables")[1].error)
        self.assertTrue(ask(kind="modules", state_of_production="new")[1].error)

    def test_it_changes_neither_the_catalogue_nor_the_project(self):
        host = Host(capannone_rho())
        before = (len(catalog.load("batteries")), json.dumps(host.project.to_json(), sort_keys=True))
        tools.run("search_catalog", {"kind": "batteries", "query": ""}, host, tools.State())
        self.assertEqual(before, (len(catalog.load("batteries")), json.dumps(host.project.to_json(), sort_keys=True)))
        self.assertIn("search_catalog", [t["name"] for t in tools.specs()])

    def test_a_kind_not_yet_read_is_read_away_from_the_window_before_the_tools(self):
        calls = [ToolCall("c1", "search_catalog", {"kind": "modules", "query": "x"}),
                 ToolCall("c2", "read_checks", {})]
        with mock.patch.object(catalog, "ready", return_value=False), mock.patch.object(catalog, "prepare") as prepare:
            slow = tools.slow_reads(calls)
            self.assertEqual(len(slow), 1)
            slow[0]()
            prepare.assert_called_once_with("modules")
        with mock.patch.object(catalog, "ready", return_value=True):
            self.assertEqual(tools.slow_reads(calls), [])
        self.assertEqual(tools.slow_reads([ToolCall("c3", "search_catalog", {"kind": "cables"})]), [])

    def test_in_a_conversation_the_model_reads_the_rows(self):
        conv = conversation.Conversation()
        conv.ask("Un inverter Huawei da 50 kW?")
        conv.run_tools([ToolCall("c1", "search_catalog", {"kind": "inverters", "query": "huawei",
                                                          "power_from": 40000})], Host(capannone_rho()))
        self.assertIn("products", json.loads(conv.messages[-1]["content"]))


if __name__ == "__main__":
    unittest.main()
