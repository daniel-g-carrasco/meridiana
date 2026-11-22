"""R649 (Daniel 15/11/2026, the program in English: «why are you writing me in italian?»). With the program in English
and the Italian regulatory profile, what goes to Meridio's model is in English but for the quotations, marked as such;
the language of a text is told by its words (app/assistant/languages.py)."""
import json
import re
import unittest

import _setup  # noqa: F401
from _fixtures import capannone_rho
from meridiana import i18n
from meridiana.app.assistant import context, languages, tools


class Host:
    def __init__(self):
        self.project = capannone_rho()


ITALIAN_EXAMPLES = ("portami", "mostrami", '"tu"', "resa specifica", "Sono in", "Rispondi")


class LanguagesTest(unittest.TestCase):
    def test_the_language_of_a_text_by_its_words(self):
        self.assertEqual(languages.detect("Il rapporto di prestazione è basso perché le perdite per ombra sono alte."), "it")
        self.assertEqual(languages.detect("The performance ratio is low because the shading losses are high."), "en")
        self.assertEqual(languages.detect("PR 81 %"), "")
        self.assertEqual(languages.detect("Sud"), "")


class ScaffoldingTest(unittest.TestCase):
    def setUp(self):
        before = i18n._translation
        self.addCleanup(lambda: setattr(i18n, "_translation", before))

    def test_in_english_nothing_of_the_scaffolding_is_italian(self):
        i18n.setup("en")
        system = context.system("Meridio", profile_id="it")
        specs = json.dumps(tools.specs(profile_id="it"), ensure_ascii=False)
        asked = context.question("Why is the PR low?", "Production", "sub-field Sud")
        for name, text in (("instructions", system), ("tools", specs), ("question", asked)):
            for word in ITALIAN_EXAMPLES:
                self.assertNotIn(word, text, f"{name}: «{word}»")
            for sentence in re.split(r"(?<=[.!?])\s+", text):
                self.assertNotEqual(languages.detect(sentence), "it", f"{name}: {sentence}")
        # the rule on the language, at the end of the instructions and in the question's head
        self.assertTrue(system.rstrip().endswith(context.ANSWER_IN.format(language="English")))
        self.assertIn("Answer in English.", asked.splitlines()[0])

    def test_in_italian_the_examples_are_italian(self):
        i18n.setup("it")
        system = context.system("Meridio", profile_id="it")
        self.assertIn('"portami", "mostrami"', system)
        self.assertIn("Rispondi in italiano.", context.question("Che cosa posso fare?", "Impianto").splitlines()[0])

    def test_an_italian_quotation_is_marked_with_the_language_to_answer_in(self):
        i18n.setup("en")
        answer = json.loads(tools.run("vvf_activities", {"query": "uffici"}, Host(), tools.State()).content)
        self.assertEqual(answer["quoted_language"], "Italian")
        self.assertIn("English", answer["answer_in"])
        self.assertEqual(list(answer)[:2], ["quoted_language", "answer_in"], "first, on a long answer's first page")
        i18n.setup("it")
        answer = json.loads(tools.run("vvf_activities", {"query": "uffici"}, Host(), tools.State()).content)
        self.assertNotIn("quoted_language", answer)

    def test_the_english_manual_needs_no_foreign_language_quotation_marker(self):
        i18n.setup("en")
        answer = json.loads(tools.run("search_manual", {"query": "Power asked"}, Host(), tools.State()).content)
        self.assertNotIn("quoted_language", answer)
        self.assertTrue(answer["passages"])
        self.assertEqual(answer["passages"][0]["heading"], "Power asked")
        self.assertIn("45.13 kWp", answer["passages"][0]["text"])


if __name__ == "__main__":
    unittest.main()
