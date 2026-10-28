"""Meridio's character (R106): one text of instructions for every model he talks through, who he is, how he speaks
(friendly and brief, honest about what he does not know and about the figures that are assumptions, never a number
guessed, the next step offered), his presentation and his greeting, in English and in Italian. The local model,
Ollama and Claude get the very same instructions (fake servers on 127.0.0.1 and the stand-in of the SDK)."""

import unittest

import _setup
from _fakes import FakeAnthropic, FakeRuntime, FakeServer, Host, ollama_answer, text_answer
from _fixtures import capannone_rho

from meridiana import i18n
from meridiana.assistant import context, conversation, persona, providers

CATALOGUE = _setup.ROOT / "locale" / "it" / "LC_MESSAGES" / "meridiana.mo"


class Instructions(unittest.TestCase):
    def test_he_knows_his_name_his_manner_and_speaks_of_himself_in_the_masculine(self):
        text = persona.system("Meridio", "it")
        self.assertTrue(text.startswith("You are Meridio, the assistant inside Meridiana"))
        self.assertIn("Your name is Meridio", text)
        self.assertIn("in the masculine", text)
        self.assertIn("sono contento, non contenta", text)
        self.assertIn("Friendly and warm", text)
        self.assertIn("Concise and technically precise", text)
        self.assertIn("In Italian", text)

    def test_he_says_what_he_does_not_know_and_proposes_changes_without_asking_permission(self):
        text = persona.system("Meridio", "it")
        self.assertIn("non lo so", text)
        self.assertIn("Every figure is read with the tools, never guessed", text)
        self.assertIn("default of Meridiana", text)
        self.assertIn("read_pedigree gives the source", text)
        self.assertNotIn("Vuoi che te lo proponga?", text)
        self.assertIn("call the proposal tool at once", text)
        self.assertIn("Never quote a standard, an article, a threshold or a law from memory", text)
        self.assertIn("do not introduce yourself again", text)
        self.assertIn("no emoji", text)                            # his voice would read them (R94)
        self.assertIn("names and values shown in the Properties panel", text)
        self.assertIn("never their internal keys or coded values", text)
        self.assertIn("I can propose undo or redo", text)
        self.assertIn("never undo or redo anything yourself", text)

    def test_in_english_the_examples_are_english(self):
        text = persona.system("Meridio", "en")
        self.assertIn("In English", text)
        self.assertNotIn("Shall I propose it?", text)
        self.assertNotIn("Vuoi che", text)
        self.assertEqual(persona.system("Meridio", "fr"), text)    # a language without phrases: English

    def test_the_text_is_the_same_at_every_call_so_that_the_providers_read_it_from_their_cache(self):
        self.assertEqual(persona.system("Meridio", "it"), persona.system("Meridio", "it"))
        self.assertEqual(context.system("Meridio", "it"), persona.system("Meridio", "it"))
        self.assertNotIn("{", persona.system("Meridio", "it"))     # every placeholder filled

    def test_no_em_dash_and_no_placeholder_left_in_his_words(self):
        for lang in ("it", "en"):
            for text in (persona.system("Meridio", lang), persona.presentation(), persona.greeting()):
                self.assertNotIn("—", text)
                self.assertNotIn("{", text)

    def test_the_presentation_says_his_name_what_he_does_and_does_not_and_where_he_thinks(self):
        text = persona.presentation("Meridio")
        self.assertTrue(text.startswith("Hi, I am Meridio, Meridiana's assistant."))
        for part in ("the checks, the results, the rules", "comes from an assumption", "I change nothing by myself",
                     "Ctrl+Z", "local model on this PC", "Claude only if you choose it"):
            self.assertIn(part, text)
        self.assertLess(len(text), 520)                           # short: a few lines in the bubble

    def test_the_presentation_and_the_greeting_are_in_italian_in_the_italian_program(self):
        if not CATALOGUE.exists():
            self.skipTest("tools/compile_po.py first")
        before = i18n._translation
        try:
            i18n.setup("it")
            hello, greeting = persona.presentation("Meridio"), persona.greeting("Meridio")
        finally:
            i18n._translation = before
        self.assertTrue(hello.startswith("Ciao, sono Meridio, l'assistente di Meridiana."), hello)
        self.assertIn("Ctrl+Z", hello)
        self.assertIn("Meridio", greeting)
        self.assertNotEqual(greeting, persona.greeting("Meridio"))


class SameForEveryProvider(unittest.TestCase):
    """The local server, Ollama and Claude are given the same instructions, word for word."""

    def test_llama_server_ollama_and_claude_get_the_same_system_text(self):
        system = context.system("Meridio", "it")
        server = FakeServer([text_answer("Ciao.")])
        self.addCleanup(server.close)
        ollama = FakeRuntime({"_shows": {"qwen3.6:35b-a3b": {"capabilities": ["completion", "tools"]}}},
                             chat=[ollama_answer("Ciao.")])
        self.addCleanup(ollama.close)
        claude = FakeAnthropic([[("text", "Ciao.")]])
        host = Host(capannone_rho(), lay=False)
        for provider in (providers.OpenAICompatible(base_url=server.url),
                         providers.Ollama(model="qwen3.6:35b-a3b", base_url=ollama.base),
                         providers.Anthropic(model="claude-haiku-5-5", client=claude)):
            conversation.answer(conversation.Conversation(), provider, system, "Chi sei?", host)
        self.assertEqual(server.requests[0]["messages"][0], {"role": "system", "content": system})
        chat = next(body for path, body in ollama.requests if path == "/api/chat")
        self.assertEqual(chat["messages"][0], {"role": "system", "content": system})
        self.assertEqual(claude.calls[0]["system"][0]["text"], system)


if __name__ == "__main__":
    unittest.main()
