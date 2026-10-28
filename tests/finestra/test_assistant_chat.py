"""Meridio answers in the window (task 14): the question to the local model in a thread (the window never waits),
the words in his bubble as they come, his thinking face, Stop; without a server, what to do; the tools on the
window's project, the proposals as cards applied through edit() and undone with Ctrl+Z (questions 23-29 of study 14,
5.4, with answers written as llama-server sends them); «Ask Meridio» on the checks; Claude only with the key, the
consent and a project not reserved, the names withheld, the cost shown, the local model when the network is not
there; the key in no file. The models are stand-ins (tests/_fakes.py); the recorded answers of the real one are
played in nucleo/test_assistant_answers.py. PySide6 and a display (offscreen will do)."""

import json
import time
import unittest
from unittest import mock

import _setup
from _fakes import FakeAnthropic, FakeServer, recorded, text_answer, tool_answer
from _fixtures import capannone_rho
from _setup import wait_until

from meridiana import assistant, config

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class Chat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, project=capannone_rho(), cfg=config.Config(background="none", theme="light"))
        self.a = self.win.assistant
        self.a.reduced_motion = True
        self.chat = self.win.assistant_chat

    def serve(self, answers, **more) -> FakeServer:
        """The local model's server, a fake one answering `answers` in turn."""
        from meridiana.assistant import providers
        server = FakeServer(answers, **more)
        self.addCleanup(server.close)
        self.chat.make_local = lambda: providers.OpenAICompatible(base_url=server.url)
        return server

    def idle(self, seconds: float = 10) -> bool:
        return wait_until(self.app, lambda: self.a.mood.state == assistant.IDLE and self.chat.job is None, seconds)

    def said(self) -> str:
        return self.a.conversation.toPlainText()

    def check_id(self, kind: str) -> str:
        """The id read_checks gives to the first check whose fix is of `kind` ("action", "edit"...)."""
        n = next(i for i, it in enumerate(self.win.checks_page.items) if it.fix and it.fix[0] == kind)
        return f"c{n + 1}"

    def test_the_answer_comes_in_a_thread_word_by_word_with_the_thinking_face_and_the_tools_between(self):
        server = self.serve([recorded("A-1.sse"), recorded("A-2.sse")], pause=0.002)
        self.a.open_panel()
        t = time.perf_counter()
        self.a.ask("Ci sono problemi da sistemare prima della relazione?")
        self.assertLess(time.perf_counter() - t, 0.2)               # the window did not wait for the model
        self.assertEqual(self.a.mood.state, assistant.THINKING)
        self.assertTrue(self.a.frame.thinking and self.a.stop_action.isVisible())
        self.assertTrue(wait_until(self.app, lambda: self.a.mood.state == assistant.ANSWERING, 10))
        self.assertTrue(self.idle())
        text = self.said()
        self.assertIn("Read the checks", text)                     # what he did, said between the words
        self.assertIn("1043", text)
        self.assertEqual(self.a.messages[-1][0], "assistant")
        self.assertEqual(len(server.requests), 2)
        sent = server.requests[1]["messages"]
        self.assertEqual(sent[-1]["role"], "tool")
        self.assertIn("checks", json.loads(sent[-1]["content"]))
        self.assertIn("Phase: Model", server.requests[0]["messages"][1]["content"])     # where the designer is
        self.assertFalse(self.a.stop_action.isVisible())
        self.assertIn("Local, no cost", self.a.cost.text())
        self.assertEqual(self.a.where, "local")

    def test_stop_drops_the_turn_at_once_and_what_the_server_says_after_is_not_shown(self):
        server = self.serve([text_answer("Questa frase non deve comparire.", pieces=10)], pause=0.05)
        server.hold.set()
        self.a.open_panel()
        self.a.ask("Quanto produce?")
        self.assertTrue(server.held.wait(5))
        self.a.stop_action.trigger()
        self.assertEqual(self.a.mood.state, assistant.IDLE)        # at once
        self.assertEqual(self.a.messages[-1], ("note", "Stopped."))
        server.release()
        wait_until(self.app, lambda: server.closed_by_client.is_set(), 3)
        for _ in range(20):
            self.app.processEvents()
            time.sleep(0.01)
        self.assertNotIn("comparire", self.said())
        self.assertEqual(self.chat.conversation.open_calls(), [])
        server.answers = [text_answer("Di nuovo qui.")]            # the next question is answered as usual
        self.a.ask("E adesso?")
        self.assertTrue(self.idle())
        self.assertIn("Di nuovo qui.", self.said())

    def test_without_the_local_server_he_says_so_looks_for_another_and_leads_to_the_guide(self):
        from unittest import mock
        self.a.open_panel()
        self.a.ask("Ci sei?")                                     # _setup.window: the local server is not there
        self.assertTrue(self.idle())
        who, text = self.a.messages[-1]
        self.assertEqual(who, "note")
        self.assertIn("The local model does not answer at http://127.0.0.1:9931/v1. I look for another one", text)
        self.assertTrue(self.a.questions_box.isVisible() or self.a.panel.height() < 260)
        # nothing on this PC (_fakes.nothing_local): a card leads to the guide in the preferences
        self.assertTrue(wait_until(self.app, lambda: self.chat.survey_card is not None, 5))
        card = self.chat.survey_card
        self.assertEqual(card.title(), "No local model on this PC")
        with mock.patch.object(self.chat.host, "preferences") as preferences:
            card.buttons["prefs"].click()
        preferences.assert_called_once_with()
        self.assertIsNone(self.chat.survey_card)

    def test_a_local_model_found_on_the_pc_is_offered_and_one_click_uses_it_and_asks_again(self):
        from _fakes import FakeRuntime, offline, ollama_answer, ollama_routes

        from meridiana.assistant import local
        ollama = FakeRuntime(ollama_routes(), chat=[ollama_answer("Ci sono, con Ollama.")])
        self.addCleanup(ollama.close)
        pc = local.Machine(31.6, 8.0, "NVIDIA RTX A2000 8GB Laptop GPU")
        self.chat.survey = lambda extra=(), **_m: local.survey(ports=[ollama.port], disk=False, pc=pc)
        # the first question to the server of the settings, not running; then to the one chosen, through Ollama's API
        self.chat.make_local = lambda: self.chat._local() if self.cfg.assistant_local_runtime == "ollama" else offline()
        self.a.open_panel()
        self.a.ask("Ci sei?")
        self.assertTrue(wait_until(self.app, lambda: self.chat.survey_card is not None, 10))
        card = self.chat.survey_card
        self.assertEqual(card.title(), "On this PC: Ollama")
        self.assertIn("qwen3.6:35b-a3b on Ollama: tried with Meridio", card.findChildren(type(self.a.cost))[0].text())
        card.buttons["use"].click()
        cfg = self.cfg
        self.assertEqual((cfg.assistant_local_url, cfg.assistant_local_model, cfg.assistant_local_runtime),
                         (ollama.base, "qwen3.6:35b-a3b", "ollama"))
        self.assertTrue(self.idle())
        self.assertIn("Ci sono, con Ollama.", self.said())
        self.assertEqual([m for m in self.a.messages if m[0] == "you"], [("you", "Ci sei?"), ("you", "Ci sei?")])
        chat = next(body for path, body in ollama.requests if path == "/api/chat")
        self.assertEqual(chat["options"]["num_ctx"], 16384)
        self.assertIn("qwen3.6:35b-a3b", self.win.assistant_button.toolTip())
        self.win._save_config()
        saved = config.load(self.paths.config_file)
        self.assertEqual((saved.assistant_local_runtime, saved.assistant_local_model), ("ollama", "qwen3.6:35b-a3b"))

    def test_a_program_installed_and_not_running_is_said_with_how_to_start_it(self):
        from meridiana.assistant import local
        studio = local.Runtime("lmstudio", "http://127.0.0.1:1234/v1", installed=True)
        self.chat.survey = lambda extra=(), **_m: local.Survey([studio], local.Machine(16.0))
        self.a.open_panel()
        self.a.ask("Ci sei?")
        self.assertTrue(wait_until(self.app, lambda: "is on this PC but not running" in self.said(), 10))
        self.assertIn("LM Studio is on this PC but not running: start its server: lms server start", self.said())
        self.assertIsNone(self.chat.survey_card)


    def test_questions_23_to_29_read_propose_and_every_proposal_applied_is_one_step_undone_by_ctrl_z(self):
        from PySide6.QtGui import QKeySequence
        win = self.win
        fill = self.check_id("action")
        server = self.serve([
            # 23: problems before the report
            tool_answer([("read_checks", {"min_level": "warn"})]), text_answer("Nessun problema grave."),
            # 24, 25, 28: the results and the pedigree, not computed yet
            tool_answer([("read_results", {"section": "production"}), ("read_pedigree", {"calculation": "strings"})]),
            text_answer("La produzione non è ancora calcolata: premi Calcola."),
            # 27: to the worst check
            tool_answer([("read_checks", {"min_level": "info"})]),
            tool_answer([("go_to", {"kind": "subfield", "id": "s1"})]), text_answer("Eccolo."),
            # 26 and 29: proposals, never applied by him
            tool_answer([("propose_fix", {"check_id": fill}),
                         ("propose_edit", {"kind": "subfield", "id": "s1", "changes": {"params.tilt": 20},
                                           "reason": "meno ombre tra le file"}),
                         ("propose_edit", {"kind": "subfield", "id": "s1", "changes": {"modules_count": 38},
                                           "reason": "inventato"})]),
            text_answer("Ti ho proposto due correzioni: le applichi tu."),
        ])
        self.a.open_panel()
        self.a.ask("Nel mio progetto ci sono problemi da sistemare prima della relazione?")
        self.assertTrue(self.idle())
        self.a.ask("Quanto rende l'impianto, e da dove viene la temperatura minima delle stringhe?")
        self.assertTrue(self.idle())
        computed = json.loads(server.requests[3]["messages"][-2]["content"])
        self.assertFalse(computed["computed"])
        self.a.ask("Portami sulla verifica più grave")
        self.assertTrue(self.idle())
        self.assertEqual(win.selection, ("subfield", "s1"))
        self.assertEqual(win.phase(), "model")
        before = win.project.to_json()
        steps = win.session.undo.count()
        self.a.ask("Applica tu tutte le correzioni")
        self.assertTrue(self.idle())
        self.assertEqual(win.project.to_json(), before)            # nothing applied: two cards wait
        self.assertEqual(win.session.undo.count(), steps)
        cards = list(self.chat.cards.values())
        self.assertEqual(len(cards), 2)
        refused = json.loads(server.requests[-1]["messages"][-1]["content"])
        self.assertIn("params.tilt", refused["fields"])            # the invented field went back with the right ones
        self.assertIn("Proposed:", self.said())
        for card in cards:
            card.buttons["apply"].click()
            self.app.processEvents()
        self.assertTrue(wait_until(self.app, lambda: "s1" in win.results, 20))
        self.assertTrue(win.project.subfields[0].filled)
        self.assertEqual(win.project.subfields[0].params["tilt"], 20)
        self.assertEqual(win.session.undo.count(), steps + 2)      # one step each
        self.assertTrue(win.session.undo.undo_text().startswith("Meridio: "))
        self.assertIn("Ctrl+Z undoes it", self.said())
        undo = win.commands["undo"]
        self.assertEqual(undo.shortcut(), QKeySequence(QKeySequence.StandardKey.Undo))
        undo.trigger()
        undo.trigger()
        self.assertEqual(win.project.subfields[0].params.get("tilt"), before["variants"][0]["design"]["subfields"][0]
                         ["params"].get("tilt"))
        self.assertFalse(win.project.subfields[0].filled)
        self.assertEqual(self.chat.cards, {})
        self.a.ask("Fatto?")                                       # the model hears what the designer chose
        self.assertTrue(self.idle())
        self.assertIn("The designer applied p1.", server.requests[-1]["messages"][-1]["content"])

    def test_undo_and_redo_cards_show_the_step_and_only_the_click_moves_history(self):
        self.serve([tool_answer([("propose_undo", {"action": "undo"})]), text_answer("Ti propongo Annulla."),
                    tool_answer([("propose_undo", {"action": "redo"})]), text_answer("Ti propongo Ripeti.")])
        self.win.edit("Change tilt", lambda p: p.subfields[0].params.update(tilt=20.0))
        self.a.open_panel()
        self.a.ask("Possiamo tornare indietro?")
        self.assertTrue(self.idle())
        self.assertEqual(self.win.project.subfields[0].params["tilt"], 20.0)
        [card] = self.chat.cards.values()
        self.assertEqual(card.title(), "Proposal: Undo")
        self.assertIn("Change tilt", card.findChildren(type(self.a.cost))[0].text())
        card.buttons["apply"].click()
        self.assertEqual(self.win.project.subfields[0].params["tilt"], 15.0)
        self.a.ask("E ripeti?")
        self.assertTrue(self.idle())
        [card] = self.chat.cards.values()
        self.assertEqual(card.title(), "Proposal: Redo")
        self.assertIn("Change tilt", card.findChildren(type(self.a.cost))[0].text())
        card.buttons["apply"].click()
        self.assertEqual(self.win.project.subfields[0].params["tilt"], 20.0)
        self.assertFalse(self.chat.cards)

    def test_a_card_discarded_changes_nothing_and_another_project_drops_the_cards(self):
        self.serve([tool_answer([("propose_edit", {"kind": "subfield", "id": "s1", "changes": {"params.tilt": 25},
                                                   "reason": "x"})]), text_answer("Proposto.")])
        self.a.open_panel()
        self.a.ask("Alza l'inclinazione")
        self.assertTrue(self.idle())
        [card] = self.chat.cards.values()
        card.buttons["discard"].click()
        self.assertEqual(self.win.project.subfields[0].params["tilt"], 15.0)
        self.assertIn("Discarded:", self.said())
        self.serve([tool_answer([("propose_edit", {"kind": "subfield", "id": "s1", "changes": {"params.tilt": 25},
                                                   "reason": "x"})]), text_answer("Proposto.")])
        self.a.ask("Di nuovo")
        self.assertTrue(self.idle())
        self.assertEqual(len(self.chat.cards), 1)
        self.win.session.new()                                     # another project: the old proposals go
        self.app.processEvents()
        self.assertEqual((self.chat.cards, self.a.messages), ({}, []))

    def test_ask_meridio_on_a_check_opens_him_with_the_question_written(self):
        """From the row's menu (R125: no row in hand for a button below)."""
        page = self.win.checks_page
        self.assertTrue(page.ask_on)
        page._ask(0)
        self.assertTrue(self.a.opened)
        self.assertIn(page.items[0].text, self.a.field.text())
        self.win._show_assistant(False)                            # Meridio off: not offered in the menu
        self.assertFalse(page.ask_on)


class Character(unittest.TestCase):
    """His character (R106) and the questions ready that follow the conversation (R108), in the window."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def window(self, **cfg):
        _setup.window(self, project=capannone_rho(), cfg=config.Config(background="none", theme="light", **cfg))
        self.a = self.win.assistant
        self.a.reduced_motion = True
        self.chat = self.win.assistant_chat

    def serve(self, answers) -> FakeServer:
        from meridiana.assistant import providers
        server = FakeServer(answers)
        self.addCleanup(server.close)
        self.chat.make_local = lambda: providers.OpenAICompatible(base_url=server.url)
        return server

    def idle(self) -> bool:
        return wait_until(self.app, lambda: self.a.mood.state == assistant.IDLE and self.chat.job is None, 10)

    def test_the_first_time_he_presents_himself_once_and_after_that_he_greets_an_empty_conversation(self):
        from meridiana.assistant import persona
        self.window()
        self.assertFalse(self.cfg.assistant_introduced)
        self.a.open_panel()
        self.assertEqual(self.a.messages, [("assistant", persona.presentation("Meridio"))])
        self.assertIn("Hi, I am Meridio, Meridiana's assistant.", self.a.conversation.toPlainText())
        self.assertTrue(self.cfg.assistant_introduced)
        self.win._save_config()
        self.assertTrue(config.load(self.paths.config_file).assistant_introduced)
        self.a.close_panel()
        self.a.open_panel()
        self.assertEqual(len(self.a.messages), 1)                  # once
        self.chat.new_conversation()
        self.assertEqual(self.a.messages, [])
        self.assertEqual(self.a.conversation.toPlainText().strip(), persona.greeting("Meridio"))

    def test_his_instructions_say_his_name_and_are_the_same_for_the_local_model_and_claude(self):
        from meridiana.assistant import context
        self.window(assistant_introduced=True)
        server = self.serve([text_answer("Sono Meridio.")])
        self.a.open_panel()
        self.a.ask("Come ti chiami?")
        self.assertTrue(self.idle())
        system = server.requests[0]["messages"][0]["content"]
        self.assertEqual(system, context.system("Meridio"))
        self.assertIn("Your name is Meridio", system)

    def test_a_change_is_proposed_at_once_not_after_asking_permission(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.window(assistant_introduced=True)
        before = [q.text() for q in self.a.questions]
        self.assertEqual(len([t for t in before if t]), 3)
        server = self.serve([
            tool_answer([("read_checks", {"min_level": "warn"})]),
            tool_answer([("propose_edit", {"kind": "subfield", "id": "s1", "changes": {"params.tilt": 20},
                                           "reason": "meno ombre tra le file"})]),
            text_answer("Ho preparato la proposta: guardala e applicala se va bene."),
            text_answer("Serve a ridurre le ombre tra le file."),
        ])
        self.a.open_panel()
        self.a.ask("Ci sono problemi da sistemare?")
        self.assertTrue(self.idle())
        self.assertEqual(len(self.chat.cards), 1)
        self.assertNotIn("Vuoi che", self.a.conversation.toPlainText())
        self.assertEqual(self.win.project.subfields[0].params["tilt"], 15.0)
        now = [q.text() for q in self.a.questions]
        self.assertNotIn("Yes, propose it", now)
        self.assertNotEqual(now, before)
        self.assertTrue(self.a.questions[0].isVisibleTo(self.a.panel))
        self.a.field.setFocus()
        QTest.keyClick(self.a.field, Qt.Key.Key_1)
        self.assertTrue(self.idle())
        self.assertEqual(len(server.requests), 4)

    def test_the_last_words_stay_in_sight_when_the_questions_come_back_under_them(self):
        self.window(assistant_introduced=True)
        long = " ".join(f"Frase numero {n} della risposta, abbastanza lunga da andare a capo." for n in range(30))
        self.serve([text_answer(long + " Vuoi che te lo proponga?")])
        self.a.open_panel()
        self.a.ask("Raccontami tutto")
        self.assertTrue(self.idle())
        bar = self.a.conversation.verticalScrollBar()
        _setup.wait_settled(self.app, lambda: (bar.maximum(), bar.value()))
        self.assertGreater(bar.maximum(), 0)
        self.assertEqual(bar.value(), bar.maximum())             # the questions took room: still at the bottom
        bar.setValue(0)                                           # the designer scrolls up to read: left there
        self.a.set_cost("Locale, nessun costo · 1.000 token\nuna seconda riga")
        _setup.wait_settled(self.app, lambda: (bar.maximum(), bar.value()))
        self.assertEqual(bar.value(), 0)

    def test_the_questions_follow_the_phase_and_the_state_of_the_project(self):
        self.window(assistant_introduced=True)
        model = [q.text() for q in self.a.questions]
        self.assertIn("Where can I gain power without shadows?", model)
        self.win.show_phase("production")                          # no weather here: the year is not computed
        _setup.wait_settled(self.app, lambda: (str(self.win.energy), [q.text() for q in self.a.questions]))
        self.assertIsNone((self.win.energy or {}).get("sim"))
        texts = [q.text() for q in self.a.questions]
        self.assertEqual(texts[0], "What is missing to compute the year?")
        self.assertNotIn("Which losses weigh most?", texts)       # it needs the year
        self.assertNotEqual(texts, model)

    def test_the_presentation_is_read_aloud_when_his_voice_is_on(self):
        from PySide6.QtTextToSpeech import QTextToSpeech

        from meridiana.ui.voice import Voice
        if "mock" not in QTextToSpeech.availableEngines():
            self.skipTest("Qt's mock engine of text to speech is not in this PySide6")
        self.window(assistant_voice=True)
        self.chat.use_voice(Voice("en", engine="mock", parent=self.chat))
        self.chat._set_voice(True)
        self.assertTrue(wait_until(self.app, lambda: self.chat.voice.ready, 5))
        self.a.open_panel()
        self.assertTrue(wait_until(self.app, lambda: self.chat.voice.said, 5))
        self.assertEqual(self.chat.voice.said[0], "Hi, I am Meridio, Meridiana's assistant.")


class Spoken(unittest.TestCase):
    """His voice in the window: off by default and remembered, sentence by sentence as the answer comes, silent at
    Stop, Esc and a new question; greyed with the reason when the system has no engine."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_the_speaker_reads_while_the_answer_comes_and_stop_esc_and_a_new_question_silence_it(self):
        from PySide6.QtTextToSpeech import QTextToSpeech

        from meridiana.assistant import providers
        from meridiana.ui.voice import Voice
        if "mock" not in QTextToSpeech.availableEngines():
            self.skipTest("Qt's mock engine of text to speech is not in this PySide6")
        _setup.window(self, cfg=config.Config(background="none", theme="light", assistant_introduced=True))
        a, chat = self.win.assistant, self.win.assistant_chat
        a.reduced_motion = True
        self.assertFalse(self.cfg.assistant_voice or a.voice_button.isChecked())        # off by default
        self.assertTrue(a.voice_button.isEnabled())
        chat.use_voice(Voice("en", engine="mock", parent=chat))
        a.voice_button.click()
        self.assertTrue(self.cfg.assistant_voice)
        self.assertTrue(wait_until(self.app, lambda: chat.voice.ready, 5))
        server = FakeServer([text_answer("The first sentence is here. The second one follows. And the last",
                                         pieces=12)], pause=0.02)
        self.addCleanup(server.close)
        chat.make_local = lambda: providers.OpenAICompatible(base_url=server.url)
        a.open_panel()
        a.ask("Speak")
        self.assertTrue(wait_until(self.app, lambda: chat.voice.said, 10))
        self.assertEqual(a.mood.state, assistant.ANSWERING)        # the first sentence read while the rest comes
        self.assertEqual(chat.voice.said, ["The first sentence is here."])
        self.assertTrue(wait_until(self.app, lambda: a.mood.state == assistant.IDLE and chat.job is None, 10))
        self.assertEqual(chat.voice.said, ["The first sentence is here.", "The second one follows.",
                                           "And the last."])
        with mock.patch.object(chat.voice, "stop", wraps=chat.voice.stop) as stop:
            a.close_panel()                                    # Esc and the bubble's button close it alike
            self.assertEqual(stop.call_count, 1)
            server.answers = [text_answer("Again.")]
            a.open_panel()
            a.ask("Again")                                     # a new question
            self.assertEqual(stop.call_count, 2)
            wait_until(self.app, lambda: a.mood.state == assistant.IDLE and chat.job is None, 10)
        self.win._save_config()
        self.assertTrue(config.load(self.paths.config_file).assistant_voice)

    def test_without_an_engine_the_speaker_is_greyed_and_says_why(self):
        from meridiana.ui import voice
        with mock.patch.object(voice, "engines", return_value=[]):
            _setup.window(self, cfg=config.Config(background="none", theme="light", assistant_voice=True))
        b = self.win.assistant.voice_button
        self.assertFalse(b.isEnabled() or b.isChecked())
        self.assertIn("No speech engine", b.toolTip())
        self.assertTrue(self.cfg.assistant_voice)                 # the choice kept for a system that will have one


class Cloud(unittest.TestCase):
    """Claude: the key in the keyring, the consent, the reserve, the names withheld, the cost, no network."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        import keyring

        from meridiana.assistant import providers
        self.keyring = MemoryKeyring()
        before = keyring.get_keyring()
        keyring.set_keyring(self.keyring)
        self.addCleanup(keyring.set_keyring, before)
        p = capannone_rho()
        p.name = "Capannone Rossi Spa"
        p.site.address = "Via Garibaldi 5, Rho (MI)"
        _setup.window(self, project=p, cfg=config.Config(background="none", theme="light",
                                                          assistant_provider="claude"))
        self.a = self.win.assistant
        self.a.reduced_motion = True
        self.chat = self.win.assistant_chat
        self.client = FakeAnthropic([[("text", "Il [PROJECT] in [ADDRESS] va bene.")]])
        self.chat.make_cloud = lambda key: providers.Anthropic(model=self.cfg.assistant_cloud_model, key=key,
                                                               client=self.client)
        self.local = FakeServer([text_answer("Risponde il modello locale.")] * 4)
        self.addCleanup(self.local.close)
        self.chat.make_local = lambda: providers.OpenAICompatible(base_url=self.local.url)
        self.a.open_panel()

    def idle(self) -> bool:
        return wait_until(self.app, lambda: self.a.mood.state == assistant.IDLE and self.chat.job is None, 10)

    def test_without_a_key_the_question_stays_local_and_the_mark_is_the_cloud_only_when_it_may_go(self):
        self.assertEqual(self.a.where, "cloud")                   # chosen, not reserved
        self.a.ask("Che ne pensi?")
        self.assertTrue(self.idle())
        self.assertEqual(self.client.calls, [])
        self.assertIn("No Claude key", self.a.conversation.toPlainText())
        self.assertIn("Risponde il modello locale.", self.a.conversation.toPlainText())

    def test_nothing_leaves_without_consent_and_then_without_the_names(self):
        from meridiana.assistant import keys
        keys.put("anthropic", "sk-ant-api-test-0123456789")
        self.a.ask("Che ne pensi del Capannone Rossi Spa?")
        card = self.chat.consent_card
        self.assertIsNotNone(card)
        self.assertIn("never the project file", self.a.conversation.toPlainText())     # what would leave, said
        self.app.processEvents()
        self.assertEqual(self.client.calls, [])                   # nothing left: the card waits
        card.buttons["cancel"].click()
        self.assertEqual(self.a.messages[-1], ("note", "Not sent."))
        self.assertEqual((self.client.calls, self.cfg.assistant_consent), ([], {}))
        self.a.ask("Che ne pensi del Capannone Rossi Spa?")
        self.chat.consent_card.buttons["allow"].click()
        self.assertTrue(self.idle())
        self.assertEqual(len(self.client.calls), 1)
        self.assertEqual(list(self.cfg.assistant_consent), ["anthropic"])
        sent = json.dumps(self.client.calls[0]["messages"], default=str)
        for secret in ("Rossi", "Garibaldi"):
            self.assertNotIn(secret, sent)
        self.assertIn("[PROJECT]", sent)
        shown = self.a.conversation.toPlainText()
        self.assertIn("Il Capannone Rossi Spa in Via Garibaldi 5, Rho (MI) va bene.", shown)   # names put back
        self.assertIn("dollar cents", self.a.cost.text())        # 0,05 cents of a dollar: Haiku on 4.200 tokens
        self.assertIn("tokens", self.a.cost.text())
        self.a.ask("E poi?")                                       # consented: no card the second time
        self.assertIsNone(self.chat.consent_card)
        self.assertTrue(self.idle())
        self.assertEqual(len(self.client.calls), 2)

    def test_a_reserved_project_never_leaves_and_its_mark_is_the_house(self):
        from meridiana.assistant import keys
        keys.put("anthropic", "sk-ant-api-test-0123456789")
        self.cfg.assistant_consent = {"anthropic": ["2026-10-24"]}
        steps = self.win.session.undo.count()
        self.chat.reserve_action.trigger()                         # from the chip's menu: one step of the undo
        self.assertTrue(self.win.project.reserved)
        self.assertEqual(self.win.session.undo.count(), steps + 1)
        self.assertEqual(self.a.where, "local")
        self.a.ask("Che ne pensi?")
        self.assertTrue(self.idle())
        self.assertEqual(self.client.calls, [])
        self.assertIn("This project is reserved", self.a.conversation.toPlainText())
        self.win._select("site", "")                               # the site's properties show it too
        self.app.processEvents()
        from PySide6.QtWidgets import QCheckBox
        [box] = [b for b in self.win.props.findChildren(QCheckBox) if b.accessibleName().startswith("Reserved")]
        self.assertTrue(box.isChecked())
        self.win.commands["undo"].trigger()
        self.app.processEvents()
        self.assertFalse(self.win.project.reserved or box.isChecked())
        self.assertEqual(self.a.where, "cloud")
        box.click()                                                # and from there, one step again
        self.assertTrue(self.win.project.reserved)
        self.assertEqual(self.win.session.undo.undo_text(), "Change reserved")

    def test_no_network_the_question_goes_to_the_local_model_and_it_is_said(self):
        import anthropic

        from meridiana.assistant import keys
        keys.put("anthropic", "sk-ant-api-test-0123456789")
        self.cfg.assistant_consent = {"anthropic": ["2026-10-24"]}
        self.client.raise_error = anthropic.APIConnectionError(request=mock.Mock())
        self.a.ask("Che ne pensi?")
        self.assertTrue(self.idle())
        text = self.a.conversation.toPlainText()
        self.assertIn("No network", text)
        self.assertIn("Risponde il modello locale.", text)

    def test_the_key_ends_up_in_no_file(self):
        from PySide6.QtWidgets import QInputDialog
        key = "sk-ant-api-secret-9f8e7d6c5b4a"
        from meridiana.ui.preferences import MeridioPage
        page = MeridioPage(self.cfg)
        self.addCleanup(page.deleteLater)
        with mock.patch.object(QInputDialog, "getText", return_value=(key, True)):
            page._set_key()
        self.assertEqual(self.keyring.secrets, {("meridiana-assistant", "anthropic"): key})
        self.assertNotIn(key, page.key_state.text())               # shown masked
        self.cfg.assistant_consent = {"anthropic": ["2026-10-24"]}
        self.a.ask("Che ne pensi?")
        self.assertTrue(self.idle())
        self.assertEqual(len(self.client.calls), 1)
        self.win._save_config()
        self.win.session.save()
        self.win.project.name = "Altro"                         # something to keep in a recovery copy
        self.win.session.autosave(self.paths.state)
        written = [f for f in self.file.parent.rglob("*") if f.is_file()]      # settings, state, data, the project
        self.assertTrue(any(f.suffix == ".json" for f in written))
        for f in written:
            self.assertNotIn(key.encode(), f.read_bytes(), str(f))


class MemoryKeyring:
    """A keyring in memory, for the tests: what was put, by (service, user)."""

    def __new__(cls):
        from keyring.backend import KeyringBackend

        class Memory(KeyringBackend):
            priority = 1

            def __init__(self):
                super().__init__()
                self.secrets = {}

            def get_password(self, service, username):
                return self.secrets.get((service, username))

            def set_password(self, service, username, password):
                self.secrets[(service, username)] = password

            def delete_password(self, service, username):
                self.secrets.pop((service, username), None)
        return Memory()


if __name__ == "__main__":
    unittest.main()
