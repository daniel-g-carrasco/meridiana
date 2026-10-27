"""Meridio answers (task 14; study 14, 4.4 and 6): the providers (llama-server's server-sent events, Claude through a
stand-in of the SDK), the loop of model and tools, the tools on a project without a window, the proposals that change
nothing until applied, what leaves the PC for the cloud, the costs, the words on the way out. The questions A, D, B and
27 are the real model's answers, recorded on the laptop (tests/data/assistant) and played again by a fake server on
127.0.0.1; nothing uses the network. The window's side is in finestra/test_assistant_chat.py."""

import copy
import json
import threading
import time
import unittest
from unittest import mock

import _setup  # noqa: F401
from _fakes import FakeAnthropic, FakeServer, Host, recorded, text_answer, tool_answer, with_problems
from _fixtures import capannone_rho

from meridiana.assistant import context, conversation, costs, privacy, providers, text, tools
from meridiana.i18n import number


def problems_host(**more) -> Host:
    p = capannone_rho()
    p.subfields[0].filled = True
    return with_problems(Host(p, **more))


def calls_of(conv) -> list:
    return [(c["name"], c["arguments"]) for m in conv.messages if m["role"] == "assistant" for c in m["calls"]]


class Recorded(unittest.TestCase):
    """The questions of study 14, 4.4 as the real model answered them, played again."""

    def ask(self, label: str, rounds: int, question: str):
        server = FakeServer([recorded(f"{label}-{n}.sse") for n in range(1, rounds + 1)])
        self.addCleanup(server.close)
        host = problems_host()
        conv = conversation.Conversation()
        pieces = []
        last = conversation.answer(conv, providers.OpenAICompatible(base_url=server.url), context.system(lang="it"),
                                   context.question(question, "Modello"), host, on_text=pieces.append)
        return server, host, conv, last, pieces

    def test_question_a_reads_the_checks_and_puts_the_voltage_before_the_shade(self):
        server, host, conv, last, pieces = self.ask("A", 2, "Ci sono problemi da sistemare prima della relazione?")
        self.assertEqual(calls_of(conv), [("read_checks", {"min_level": "warn"})])
        self.assertEqual(last.done.reason, "end")
        self.assertGreater(len(pieces), 20)                         # the words came as they were written
        self.assertEqual("".join(pieces), last.text)
        self.assertLess(last.text.index("1043"), last.text.index("Sud"))
        # the second request carried the call and its result, the checks with their ids and sources
        second = server.requests[1]["messages"]
        self.assertEqual(second[-2]["tool_calls"][0]["function"]["name"], "read_checks")
        result = json.loads(second[-1]["content"])
        self.assertEqual([(c["id"], c["level"]) for c in result["checks"]], [("c1", "fail"), ("c2", "warn")])
        self.assertEqual(result["checks"][0]["source"], "CEI 64-8/7:2024, 712.512.1.1")
        self.assertEqual(server.requests[0]["chat_template_kwargs"], {"enable_thinking": False})
        self.assertEqual(conv.bill.dollars, 0.0)                    # local: tokens counted, no cost
        self.assertGreater(conv.bill.usage.cache_read, 0)           # llama-server read the instructions from its cache

    def test_question_d_searches_the_manual_and_answers_with_the_menu_and_the_keys(self):
        server, host, conv, last, pieces = self.ask("D", 2, "Come provo un'altra disposizione senza perdere quella "
                                                            "attuale e poi le confronto?")
        [(name, args)] = calls_of(conv)
        self.assertEqual(name, "search_manual")
        self.assertIn("variant", args["query"])
        found = json.loads(conv.messages[2]["content"])
        self.assertIn("Ctrl+Shift+N", [k for c in found["commands"] for k in c["keys"]])     # from shortcuts.py
        self.assertIn("Ctrl+Maiusc+N", last.text)
        self.assertIn("Confronta le varianti", last.text)

    def test_question_b_goes_to_the_shaded_sub_field_and_proposes_its_fix_without_applying_it(self):
        server, host, conv, last, pieces = self.ask("B", 5, "Portami sul sottocampo con le ombre e prepara la "
                                                            "correzione, ma non applicarla")
        self.assertEqual(host.went, [("subfield", "s1")])
        self.assertEqual(calls_of(conv)[-2:], [("go_to", {"kind": "subfield", "id": "s1"}),
                                               ("propose_fix", {"check_id": "c2"})])
        [proposal] = conv.state.proposals.values()
        self.assertEqual((proposal.title, proposal.kind, proposal.oid), ("Posa fuori dalle ombre", "subfield", "s1"))
        self.assertEqual([line[0] for line in proposal.lines], ["params.shade_free"])
        self.assertNotIn("shade_free", host.project.subfields[0].params)       # proposed, not applied
        trial = copy.deepcopy(host.project)
        proposal.change(trial)
        self.assertTrue(trial.subfields[0].params["shade_free"])

    def test_question_27_reads_the_worst_check_and_goes_to_its_phase(self):
        server, host, conv, last, pieces = self.ask("Q27", 3, "Portami sulla verifica più grave")
        self.assertEqual(calls_of(conv), [("read_checks", {"min_level": "fail"}),
                                          ("go_to", {"kind": "phase", "id": "plant"})])
        self.assertEqual(host.went, [("phase", "plant")])


class DanielConversation(unittest.TestCase):
    def test_the_r170_conversation_gives_the_model_unambiguous_answers(self):
        from types import SimpleNamespace
        from meridiana import checks, model
        from meridiana.energy.simulate import ChainStep

        p = capannone_rho()
        p.subfields[0].name = "Copertura"
        p.subfields.append(model.SubField(id="s2", name="Sottocampo 2", ring=[[1, 1], [5, 1], [5, 5], [1, 5]],
                                          building="b1", params={"mounting": "coplanar"}, filled=True))
        results = {"s1": SimpleNamespace(count=188), "s2": SimpleNamespace(count=15)}
        sim = SimpleNamespace(
            arrays=[{"key": "s1.0", "name": "Copertura", "obstacle_shading": 0.033, "p_stc_kw": 84.6},
                    {"key": "s2.0", "name": "Sottocampo 2", "obstacle_shading": 0.0, "p_stc_kw": 6.75}],
            notes=[], p_stc_kw=91.35, p_ac_kw=75.0, energy_kwh=100000.0, specific_yield=1095.0, pr=0.82,
            monthly={}, chain=[ChainStep("far", "Orizzonte", "irradiance", 1000.0, 0.0),
                               ChainStep("near", "File e ostacoli", "irradiance", 989.6, -1.04)])
        energy = {"sim": sim, "shade_free_counts": {"s1": 130}}
        shade = next(i for i in checks.gather(p, results, energy) if i.area == "shade")
        host = Host(p, energy=energy, selection=("subfield", "s2"), lay=False)
        host._layouts = results
        host._checks = [shade, checks.Item("info", "layout", "Sottocampo 2: posa", target=("subfield", "s2"))]
        host.history_text = lambda action: "Posa fuori dalle ombre" if action == "undo" else ""
        host.history = mock.Mock()
        client = FakeAnthropic([
            [("tool", "read_checks", {"object_id": "s1", "min_level": "info"})],
            [("tool", "propose_fix", {"check_id": "c1"})],
            [("tool", "read_results", {"section": "production"}), ("tool", "propose_undo", {"action": "undo"})],
            [("tool", "read_checks", {"object_id": "s2"})],
            [("tool", "read_checks", {"object_id": "s2", "min_level": "info"}),
             ("tool", "read_selection", {}), ("tool", "project_summary", {})],
            [("text", "Ho letto tutto.")],
        ])
        conv = conversation.Conversation()
        last = conversation.answer(conv, providers.Anthropic(model="claude-haiku-5-5", client=client),
                                   context.system(lang="it"), "Riprendiamo il progetto", host)
        self.assertEqual(last.text, "Ho letto tutto.")
        answers = {}
        for message in conv.messages:
            if message["role"] == "tool":
                answers.setdefault(message["name"], []).append(json.loads(message["content"]))
        first = answers["read_checks"][0]
        self.assertEqual(first["filtered_counts"]["warn"], 1)
        self.assertEqual(first["project_counts"]["info"], 1)
        self.assertIn("sub-field's annual irradiance after far shading", first["checks"][0]["text"])
        self.assertIn("10:00", first["checks"][0]["fix"])
        self.assertIn("14:00", first["checks"][0]["fix"])
        self.assertIn("130 modules instead of 188, 31% fewer, for 3.3% obstacle shade", first["checks"][0]["fix"])
        self.assertIn("does not keep more modules", first["checks"][0]["detail"])
        self.assertFalse(answers["propose_fix"][0]["applied"])
        production = answers["read_results"][0]
        self.assertIn("whole plant", production["losses"][1]["basis"])
        self.assertIn("after far shading", production["obstacle_shading"][0]["basis"])
        self.assertEqual(answers["propose_undo"][0]["step"], "Posa fuori dalle ombre")
        self.assertFalse(answers["propose_undo"][0]["applied"])
        host.history.assert_not_called()
        empty, small = answers["read_checks"][1:3]
        self.assertEqual(empty["checks"], [])
        self.assertEqual(empty["filtered_counts"], {"fail": 0, "warn": 0, "info": 0, "ok": 0})
        self.assertEqual(empty["project_counts"]["info"], 1)
        self.assertIn("filter", empty["message"])
        self.assertEqual(small["filtered_counts"]["info"], 1)
        selection = answers["read_selection"][0]["params_display"]
        self.assertEqual(selection["pitch_mode"], {"label": "row pitch", "value": "From the sun"})
        self.assertEqual(selection["shade_free"], {"label": "out of the shadows", "value": "no"})
        summary = answers["project_summary"][0]["subfields"][1]
        self.assertEqual(summary["mounting_name"], "Coplanar on the pitch")
        self.assertEqual(summary["orientation_name"], "Portrait")


class Providers(unittest.TestCase):
    def test_server_sent_events_are_read_with_comments_and_lines_and_end_at_done(self):
        lines = [": keep-alive", "data: {\"a\":", "data: 1}", "", "event: x", "data: two", "", "data: [DONE]", "",
                 "data: never"]
        self.assertEqual(list(providers.sse_data(lines)), ["{\"a\":\n1}", "two"])

    def test_the_arguments_of_a_call_come_in_pieces_and_a_bad_json_is_said_not_run(self):
        events = tool_answer([("go_to", {"kind": "site"})])
        events.insert(-3, providers_chunk_bad())
        server = FakeServer([events])
        self.addCleanup(server.close)
        r = conversation.collect(providers.OpenAICompatible(base_url=server.url), "s", [{"role": "user",
                                                                                         "content": "q"}], [])
        self.assertEqual([(c.name, c.arguments) for c in r.calls], [("go_to", {"kind": "site"}), ("go_to", None)])
        conv = conversation.Conversation()
        conv.ask("q")
        conv.add_round(r, providers.OpenAICompatible())
        outcomes = conv.run_tools(r.calls, Host(capannone_rho(), lay=False))
        self.assertEqual([o.error for o in outcomes], [False, True])
        self.assertIn("not valid JSON", outcomes[1].content)

    def test_no_server_says_offline_and_the_http_errors_have_their_kind(self):
        import requests
        with mock.patch("requests.post", side_effect=requests.ConnectionError("refused")):
            with self.assertRaises(providers.ProviderError) as caught:
                list(providers.OpenAICompatible().stream("s", [], []))
        self.assertEqual(caught.exception.kind, "offline")
        for status, kind in ((401, "auth"), (404, "model"), (429, "limit"), (500, "server")):
            server = FakeServer([status])
            self.addCleanup(server.close)
            with self.subTest(status=status), self.assertRaises(providers.ProviderError) as caught:
                list(providers.OpenAICompatible(base_url=server.url).stream("s", [], []))
            self.assertEqual(caught.exception.kind, kind)

    def test_stop_ends_the_read_at_once_even_before_the_first_word_and_takes_nothing_after(self):
        """A model reading a long prompt sends nothing for tens of seconds: Stop wakes the reader all the same (the
        connection shut down, its socket's file closed), and the server, writing again, finds the connection gone."""
        server = FakeServer([text_answer("Una risposta lunga che non arriverà mai alla fine.", pieces=30)], pause=0.05)
        server.hold.set()
        self.addCleanup(server.close)
        provider = providers.OpenAICompatible(base_url=server.url)
        out = {}

        def run():
            out["round"] = conversation.collect(provider, "s", [{"role": "user", "content": "q"}], [],
                                                on_text=lambda t: out.setdefault("words", []).append(t))
        worker = threading.Thread(target=run)
        worker.start()
        self.assertTrue(server.held.wait(5))
        t = time.perf_counter()
        provider.cancel()
        worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertLess(time.perf_counter() - t, 1.0)              # the server still holds: nobody else woke it
        self.assertEqual(out["round"].done.reason, "stopped")
        self.assertEqual((out["round"].text, out.get("words")), ("", None))
        server.release()
        self.assertTrue(server.closed_by_client.wait(5))

    def test_a_turn_stopped_between_the_calls_and_their_results_closes_them_for_the_next_question(self):
        conv = conversation.Conversation()
        conv.ask("q")
        r = conversation.Round(calls=[providers.ToolCall("x1", "read_checks", {})])
        conv.add_round(r, providers.OpenAICompatible())
        self.assertEqual(len(conv.open_calls()), 1)
        conv.ask("again")
        self.assertEqual([m["role"] for m in conv.messages], ["user", "assistant", "tool", "user"])
        self.assertTrue(conv.messages[2]["error"])
        self.assertEqual(conv.open_calls(), [])

    def test_claude_gets_the_instructions_and_tools_cached_the_results_together_and_its_own_turn_back(self):
        client = FakeAnthropic([[("text", "Leggo."), ("tool", "read_checks", {"min_level": "warn"}),
                                 ("tool", "project_summary", {})], [("text", "Due problemi.")]])
        provider = providers.Anthropic(model="claude-haiku-5-5", key="k", client=client)
        conv = conversation.Conversation()
        last = conversation.answer(conv, provider, context.system(lang="it"), "Problemi?", problems_host())
        self.assertEqual(last.text, "Due problemi.")
        first, second = client.calls
        self.assertEqual(first["model"], "claude-haiku-5-5")
        self.assertEqual(first["output_config"], {"effort": "low"})
        self.assertEqual(first["system"][0]["cache_control"], {"type": "ephemeral"})
        self.assertTrue(all(t["eager_input_streaming"] for t in first["tools"]))
        self.assertEqual([m["role"] for m in second["messages"]], ["user", "assistant", "user"])
        self.assertIs(second["messages"][1]["content"], conv.messages[1]["raw"]["anthropic"])   # as it came
        results = second["messages"][2]["content"]
        self.assertEqual([b["type"] for b in results], ["tool_result", "tool_result"])       # one message
        self.assertNotIn("betas", first)
        self.assertGreater(conv.bill.dollars, 0)
        # Sonnet: the refusal fallback of the claude-api skill, through the beta endpoint
        sonnet = providers.Anthropic(model="claude-sonnet-5-5", key="k", client=FakeAnthropic([]), effort="medium",
                                     fallbacks=True)
        args = sonnet.request("s", [{"role": "user", "content": "q"}], [])
        self.assertEqual((args["betas"], args["fallbacks"]), ([providers.FALLBACK_BETA], "default"))

    def test_claude_unreachable_is_offline_and_a_refused_key_is_auth(self):
        import anthropic
        request = mock.Mock()
        for error, kind in ((anthropic.APIConnectionError(request=request), "offline"),
                            (anthropic.AuthenticationError("no", response=mock.Mock(status_code=401, headers={}),
                                                           body=None), "auth")):
            provider = providers.Anthropic(model="claude-haiku-5-5", key="k", client=FakeAnthropic([], error))
            with self.subTest(kind=kind), self.assertRaises(providers.ProviderError) as caught:
                list(provider.stream("s", [{"role": "user", "content": "q"}], []))
            self.assertEqual(caught.exception.kind, kind)


def providers_chunk_bad() -> str:
    """A second call whose arguments are not JSON."""
    from _fakes import chunk
    return chunk({"tool_calls": [{"index": 1, "id": "call_bad", "type": "function",
                                  "function": {"name": "go_to", "arguments": "{kind: site"}}]})


class Tools(unittest.TestCase):
    def test_every_tool_has_an_object_schema_and_a_description(self):
        names = [t["name"] for t in tools.specs()]
        self.assertEqual(names[:4], ["read_checks", "project_summary", "go_to", "search_manual"])
        self.assertEqual(set(names), set(tools.TOOLS))
        for t in tools.specs():
            self.assertEqual(t["parameters"]["type"], "object")
            self.assertGreater(len(t["description"]), 40)

    def test_the_summary_rounds_the_coordinates_and_tells_the_modules_laid(self):
        host = problems_host()
        out = json.loads(tools.run("project_summary", {}, host, tools.State()).content)
        self.assertEqual(out["site"], {"lat": 45.52, "lon": 9.03})
        self.assertGreater(out["subfields"][0]["modules_laid"], 50)
        self.assertFalse(out["year_computed"])

    def test_layout_parameters_have_the_names_and_values_shown_in_properties(self):
        host = problems_host(selection=("subfield", "s1"))
        host.project.subfields[0].params["mounting"] = "coplanar"
        selection = json.loads(tools.run("read_selection", {}, host, tools.State()).content)
        shown = selection["params_display"]
        self.assertEqual(shown["pitch_mode"], {"label": "row pitch", "value": "From the sun"})
        self.assertEqual(shown["shade_free"], {"label": "out of the shadows", "value": "no"})
        self.assertEqual(shown["mounting"]["value"], "Coplanar on the pitch")
        self.assertEqual(shown["portrait"], {"label": "orientation", "value": "Portrait"})
        summary = json.loads(tools.run("project_summary", {}, host, tools.State()).content)["subfields"][0]
        self.assertEqual(summary["mounting"], "coplanar")
        self.assertEqual(summary["mounting_name"], "Coplanar on the pitch")
        self.assertEqual(summary["pitch_mode_name"], "From the sun")
        self.assertEqual(summary["shade_free_name"], "no")
        self.assertEqual(summary["orientation_name"], "Portrait")

    def test_production_results_name_the_plant_and_array_bases_of_obstacle_shade(self):
        from types import SimpleNamespace
        from meridiana.energy.simulate import ChainStep
        sim = SimpleNamespace(
            p_stc_kw=65.0, p_ac_kw=50.0, energy_kwh=80000.0, specific_yield=1230.0, pr=0.8,
            monthly={}, notes=[], arrays=[{"key": "s1.0", "name": "Copertura est", "obstacle_shading": 0.033}],
            chain=[ChainStep("far", "Orizzonte", "irradiance", 1000.0, 0.0),
                   ChainStep("near", "File e ostacoli", "irradiance", 989.6, -1.04)])
        host = problems_host(energy={"sim": sim})
        out = json.loads(tools.run("read_results", {"section": "production"}, host, tools.State()).content)
        self.assertEqual(out["losses"][1]["change_pct"], -1.04)
        self.assertIn("whole plant", out["losses"][1]["basis"])
        self.assertEqual(out["obstacle_shading"][0]["array"], "Copertura est")
        self.assertEqual(out["obstacle_shading"][0]["subfield_id"], "s1")
        self.assertEqual(out["obstacle_shading"][0]["loss_pct"], 3.3)
        self.assertIn("after far shading", out["obstacle_shading"][0]["basis"])

    def test_check_counts_follow_the_filters_and_an_object_finds_checks_in_every_area(self):
        from meridiana import checks
        host = problems_host()
        host._checks = [
            checks.Item("fail", "layout", "Copertura: posa", target=("subfield", "s1")),
            checks.Item("warn", "shade", "Copertura: ombre", target=("subfield", "s1")),
            checks.Item("info", "layout", "Sottocampo 2: posa", target=("subfield", "s2")),
            checks.Item("ok", "strings", "Stringhe", target=("phase", "plant")),
        ]
        out = json.loads(tools.run("read_checks", {"object_id": "s1", "min_level": "info"}, host,
                                   tools.State()).content)
        self.assertEqual([c["text"] for c in out["checks"]], ["Copertura: posa", "Copertura: ombre"])
        self.assertEqual(out["filtered_counts"], {"fail": 1, "warn": 1, "info": 0, "ok": 0})
        self.assertEqual(out["project_counts"], {"fail": 1, "warn": 1, "info": 1, "ok": 1})
        self.assertNotIn("counts", out)
        empty = json.loads(tools.run("read_checks", {"object_id": "s1", "area": "strings"}, host,
                                     tools.State()).content)
        self.assertEqual(empty["checks"], [])
        self.assertEqual(empty["filtered_counts"], {"fail": 0, "warn": 0, "info": 0, "ok": 0})
        self.assertIn("filter", empty["message"])
        schema = tools.SPECS["read_checks"]
        self.assertIn("object_id", schema["parameters"]["properties"])
        self.assertIn("filtered", schema["description"])
    def test_the_selected_subfield_reads_its_effective_sun_window(self):
        host = problems_host(selection=("subfield", "s1"))
        sf = host.project.subfields[0]
        sf.params["window"] = {**host.project.sun_window, "day": 20, "month": 11, "start": 11.0, "end": 13.0}
        out = json.loads(tools.run("read_selection", {}, host, tools.State()).content)
        self.assertEqual(out["params"]["window"], sf.params["window"])
        self.assertFalse(out["window_from_project"])

    def test_a_proposal_of_a_field_not_allowed_or_out_of_range_comes_back_with_the_fields(self):
        host = problems_host(selection=("subfield", "s1"))
        state = tools.State()
        wrong = tools.run("propose_edit", {"kind": "subfield", "id": "s1", "changes": {"modules_count": 38},
                                           "reason": "più moduli"}, host, state)
        self.assertTrue(wrong.error)
        self.assertIn("params.tilt", json.loads(wrong.content)["fields"])
        steep = tools.run("propose_edit", {"kind": "building", "id": "b1", "changes": {"roof.tilt": 95},
                                           "reason": "x"}, host, state)
        self.assertTrue(steep.error)
        self.assertIn("roof.tilt", steep.content)
        good = tools.run("propose_edit", {"kind": "subfield", "id": "s1", "changes": {"params.tilt": 20},
                                          "reason": "meno ombra"}, host, state)
        self.assertFalse(good.error)
        self.assertEqual(good.proposal.lines, [("params.tilt", number(15.0, 2), number(20.0, 2))])
        self.assertEqual(host.project.subfields[0].params["tilt"], 15.0)
        energy = tools.run("propose_edit", {"kind": "economics", "changes": {"capex_per_kwp": 1100},
                                            "reason": "preventivo"}, host, state)
        self.assertFalse(energy.error)
        trial = copy.deepcopy(host.project)
        energy.proposal.change(trial)
        self.assertEqual(trial.economics["capex_per_kwp"], 1100.0)
        selection = json.loads(tools.run("read_selection", {}, host, state).content)
        self.assertIn("params.shade_free", selection["fields_for_propose_edit"])

    def test_undo_and_redo_are_proposals_with_the_step_text_never_applied_by_the_tool(self):
        host = problems_host()
        host.history_text = mock.Mock(side_effect=lambda action: "Meridio: tilt" if action == "undo" else "")
        host.history = mock.Mock()
        state = tools.State()
        outcome = tools.run("propose_undo", {"action": "undo"}, host, state)
        self.assertFalse(outcome.error)
        self.assertEqual(outcome.proposal.title, "Undo")
        self.assertIn("Meridio: tilt", outcome.proposal.reason)
        self.assertEqual((outcome.proposal.kind, outcome.proposal.oid), ("history", "undo"))
        self.assertFalse(json.loads(outcome.content)["applied"])
        host.history.assert_not_called()
        empty = tools.run("propose_undo", {"action": "redo"}, host, state)
        self.assertTrue(empty.error)
        self.assertIn("nothing to redo", empty.content)
        host.history.assert_not_called()

    def test_a_fix_of_a_check_gone_meanwhile_is_refused(self):
        host = problems_host()
        state = tools.State()
        tools.run("read_checks", {"min_level": "warn"}, host, state)
        host._checks = host._checks[1:]                     # the voltage fixed meanwhile
        self.assertTrue(tools.run("propose_fix", {"check_id": "c1"}, host, state).error)

    def test_go_to_refuses_what_is_not_there_and_tools_take_only_their_arguments(self):
        host = problems_host()
        self.assertTrue(tools.run("go_to", {"kind": "subfield", "id": "s9"}, host, tools.State()).error)
        self.assertTrue(tools.run("read_checks", {"colour": "red"}, host, tools.State()).error)
        self.assertTrue(tools.run("format_disk", {}, host, tools.State()).error)
        self.assertEqual(host.went, [])


class Privacy(unittest.TestCase):
    def test_names_and_address_leave_as_placeholders_and_come_back_in_the_answer(self):
        p = capannone_rho()
        p.name = "Capannone Rossi Spa"
        p.site.address = "Via Garibaldi 5, Rho (MI)"
        r = privacy.Redactor.of(p, "C:/Progetti/Rossi_R01.meridiana")
        messages = [{"role": "user", "content": "Che ne pensi del Capannone Rossi Spa di via garibaldi 5?"},
                    {"role": "tool", "id": "1", "name": "project_summary",
                     "content": json.dumps({"project": p.name, "address": p.site.address, "file": "Rossi_R01"})}]
        out = r.messages(messages)
        sent = json.dumps(out)
        for secret in ("Rossi", "Garibaldi", "Rho (MI)"):
            self.assertNotIn(secret.lower(), sent.lower())
        self.assertIn("[PROJECT]", sent)
        self.assertIn("[ADDRESS]", sent)
        self.assertEqual(messages[0]["content"][:20], "Che ne pensi del Cap")      # the conversation stays as it is
        self.assertEqual(r.restore("Il [PROJECT] in [ADDRESS]"), "Il Capannone Rossi Spa in Via Garibaldi 5, Rho (MI)")

    def test_a_reserved_project_never_goes_and_the_cloud_asks_first(self):
        p = capannone_rho()
        self.assertEqual(privacy.allowed(p, "anthropic", {}), "consent")
        given = privacy.consent({}, "anthropic")
        self.assertEqual(privacy.allowed(p, "anthropic", given), "")
        p.reserved = True
        self.assertEqual(privacy.allowed(p, "anthropic", given), "reserved")
        self.assertEqual(len(privacy.what_leaves("anthropic", "claude-haiku-5-5")), 4)


class Costs(unittest.TestCase):
    def test_haiku_and_sonnet_at_the_prices_of_the_day(self):
        u = providers.Usage(input=4000, output=400)
        self.assertAlmostEqual(costs.usd("claude-haiku-5-5", u), (4000 * 0.10 + 400 * 0.50) / 1e6)
        self.assertAlmostEqual(costs.usd("claude-sonnet-5-5", u), (4000 * 2 + 400 * 10) / 1e6)
        long = providers.Usage(input=150_000, output=100)
        self.assertAlmostEqual(costs.usd("claude-haiku-5-5", long), (150_000 * 0.50 + 100 * 2.50) / 1e6)
        self.assertIsNone(costs.usd("qwen", u))
        bill = costs.Bill()
        bill.add("claude-haiku-5-5", u, cloud=True)
        bill.add("qwen", u, cloud=False)
        self.assertEqual(bill.usage.total, 8800)
        self.assertIn("0,06", costs.money(bill.dollars).replace(".", ","))           # 0,06 dollar cents
        self.assertIn("dollar cents", costs.money(bill.dollars))
        self.assertEqual(costs.money(1.234), "1.23 $")                                    # in English: 1.23 $


class Words(unittest.TestCase):
    def test_the_little_markdown_of_a_model_becomes_html(self):
        out = text.html("Due problemi:\n\n1. **Uoc** oltre 1000 V\n2. ombra\n\nFatto `x<y`.")
        self.assertEqual(out, "<p>Due problemi:</p><ol><li><b>Uoc</b> oltre 1000 V</li><li>ombra</li></ol>"
                              "<p>Fatto <code>x&lt;y</code>.</p>")

    def test_sentences_are_cut_while_the_answer_comes_and_numbers_are_not_cut(self):
        done, rest = text.sentences("La Uoc è 1.043 V, oltre i 1000 V. Poi l'omb")
        self.assertEqual((done, rest), (["La Uoc è 1.043 V, oltre i 1000 V."], "Poi l'omb"))
        done, rest = text.sentences("- **prima** le stringhe\n- poi l'ombra", final=True)
        self.assertEqual((done, rest), (["prima le stringhe.", "poi l'ombra."], ""))



class ClientWithheld(unittest.TestCase):
    def test_the_reports_client_is_withheld_as_the_projects_name(self):
        """R61 brought a client's name into the project (Project.report): towards the cloud it is a placeholder."""
        from meridiana import model
        from meridiana.assistant import privacy
        p = model.Project(name="Capannone Rossi")
        p.site.address = "Via Garibaldi 12, Rho"
        p.report = {"client": "Rossi Costruzioni Srl"}
        r = privacy.Redactor.of(p, None, {"client": p.report["client"]})
        text = r.redact("Il committente Rossi Costruzioni Srl, Capannone Rossi in Via Garibaldi 12")
        self.assertNotIn("Rossi Costruzioni", text)
        self.assertIn("[CLIENT]", text)
        self.assertIn("[PROJECT]", text)

if __name__ == "__main__":
    unittest.main()
