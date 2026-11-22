"""The cheap remedies for small local models (study 50, 3.7, remedies 1 and 3; 7.2 point 6). Two answers of
qwen3.5:4b on 15/11/2026: «nella finestra di una fase (come [PHASE])» and «[plant] ... ([model.dc_power_nominal_w])».
- the sentence that allows placeholders in square brackets goes only to a cloud model, the only one that sees them;
- the question's head says where the designer is in plain words, with no label without its value;
- project_summary gives the phase by its title, not by its id;
- an answer with a placeholder or an internal key in square brackets is not shown as it is: a known word is put in
  its place, the rest is found for the window to ask once more or say it does not know.
No Qt, no model."""

import json
import unittest

import _setup  # noqa: F401
from _fakes import Host
from _fixtures import capannone_rho

from meridiana.app.assistant import context, privacy, text, tools
from meridiana.app.interface import phases


class Instructions(unittest.TestCase):
    def test_the_placeholders_are_explained_only_to_a_cloud_model_in_every_profile(self):
        for profile in ("it", "generic"):
            with self.subTest(profile=profile):
                local = context.system("Meridio", "it", profile_id=profile)
                cloud = context.system("Meridio", "it", profile_id=profile, cloud=True)
                self.assertNotIn("square brackets", local)
                self.assertNotIn("[PROJECT]", local)
                self.assertIn(privacy.INSTRUCTION, cloud)
                self.assertTrue(cloud.startswith(local))

    def test_the_head_of_the_question_says_where_in_plain_words(self):
        asked = context.question("Che cosa posso fare?", "Impianto", "sottocampo Sud")
        head = asked.splitlines()[0]
        self.assertNotIn("Phase:", head)
        self.assertNotIn("[", head)
        self.assertIn("Impianto", head)
        self.assertIn("sottocampo Sud", head)
        self.assertTrue(asked.endswith("Che cosa posso fare?"))
        self.assertEqual(context.question("Ciao"), "Ciao")
        self.assertNotIn("Selected", context.question("Ciao", "Impianto"))

    def test_the_selection_is_named_with_the_designers_word_for_its_kind(self):
        p = capannone_rho()
        said = context.selection_words(p, "subfield", "s1")
        self.assertNotIn("subfield", said)
        self.assertIn(tools.object_name(p, "subfield", "s1"), said)
        self.assertEqual(context.selection_words(p, "site", ""), "")


class Summary(unittest.TestCase):
    def test_the_phase_is_given_by_its_title(self):
        p = capannone_rho()
        out = json.loads(tools.run("project_summary", {}, Host(p, phase="plant"), tools.State()).content)
        self.assertEqual(out["phase"], phases.by_id("plant").title)
        self.assertNotIn("plant", json.dumps(out["phase"]))


class Output(unittest.TestCase):
    def test_placeholders_and_internal_keys_in_brackets_are_found(self):
        found = text.stray_brackets("Nella finestra di una fase (come [PHASE]) e in [plant] vedi "
                                    "([model.dc_power_nominal_w]) e [dc_ac_ratio].")
        self.assertEqual(found, ["[PHASE]", "[model.dc_power_nominal_w]", "[dc_ac_ratio]"])

    def test_ordinary_brackets_are_left_alone(self):
        self.assertEqual(text.stray_brackets("Vedi [il manuale](https://x.it), la nota [1], [V] e [I], "
                                             "un elenco [a, b] e [qui]."), [])

    def test_known_words_take_the_place_of_their_placeholder_and_the_rest_stays_to_be_asked(self):
        known = context.known_words("Impianto")
        mended, stray = text.mend("Nella fase (come [PHASE]) e in [plant] la potenza ([model.dc_power_nominal_w]).",
                                  known)
        self.assertIn("(come Impianto)", mended)
        self.assertIn("in " + phases.by_id("plant").title, mended)
        self.assertEqual(stray, ["[model.dc_power_nominal_w]"])
        clean, none = text.mend("Tutto a posto.", known)
        self.assertEqual((clean, none), ("Tutto a posto.", []))


if __name__ == "__main__":
    unittest.main()
