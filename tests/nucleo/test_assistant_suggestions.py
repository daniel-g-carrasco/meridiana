"""The questions ready under Meridio's conversation (R108): made on the PC by rules after each turn, they follow
what was just said (the tools the model called, the words of the question and of the answer, an offer at the end, a
proposal shown) and the state of the project (the worst check open, the year computed or not, the phase), never a
question already asked, never one that needs a result not there yet; at once, without a model."""

import time
import unittest

import _setup  # noqa: F401
from _fakes import Host, with_problems
from _fixtures import capannone_rho

from meridiana.assistant import context, suggestions
from meridiana.assistant.suggestions import Facts, suggest


def turn(question: str, answer: str, calls=(), results=(), phase: str = "Modello") -> list[dict]:
    """One turn as the conversation keeps it: the question with where the designer was, the model's round with its
    calls, their results, the words of the answer."""
    messages = [{"role": "user", "content": context.question(question, phase)}]
    if calls:
        messages.append({"role": "assistant", "content": "", "calls": [
            {"id": f"call_{n}", "name": name, "arguments": args} for n, (name, args) in enumerate(calls)]})
        for n, (name, _args) in enumerate(calls):
            error = (results[n] if n < len(results) else False)
            messages.append({"role": "tool", "id": f"call_{n}", "name": name, "content": "{}", "error": error})
    messages.append({"role": "assistant", "content": answer, "calls": []})
    return messages


UOC = "Inverter tetto, ingresso 2, 18 in serie: Uoc max 1043 V oltre i 1000 V dell'inverter"
SHADE = "Sud: il 4,2 % dell'irraggiamento è perso per le ombre degli ostacoli"


class Suggestions(unittest.TestCase):
    def test_before_any_question_the_phase_s_own_and_only_those_that_make_sense_now(self):
        got = suggest([], Facts(phase="model", subfields=1))
        self.assertEqual(got, ["Where can I gain power without shadows?",
                               "Which fire brigade rule sets these distances?",
                               "What if I kept the modules out of the obstacles' shade?"])
        self.assertNotIn("How much energy does the shade cost?", got)     # no year yet

    def test_with_a_check_in_error_its_fix_is_offered_first(self):
        got = suggest([], Facts(phase="model", worst=(UOC, SHADE), subfields=1))
        self.assertEqual(got[0], "How do I fix «Inverter tetto, ingresso 2, 18 in serie: Uoc max…»?")
        self.assertEqual(len(got), 3)

    def test_an_answer_that_ends_offering_a_proposal_gives_yes_first(self):
        messages = turn("Ci sono problemi da sistemare?", "Due problemi: prima la tensione della stringa, poi "
                        "l'ombra (CEI 64-8/7). Vuoi che te lo proponga?", [("read_checks", {"min_level": "warn"})])
        got = suggest(messages, Facts(phase="model", worst=(UOC, SHADE), subfields=1))
        self.assertEqual(got[:2], ["Yes, propose it", "First tell me why"])
        self.assertEqual(got[2], "Which one do I fix first?")         # the answer was about the checks

    def test_an_offer_to_take_the_designer_somewhere_gives_take_me_there(self):
        messages = turn("Dov'è l'ombra?", "È sul sottocampo Sud. Vuoi che ti ci porti, così lo vedi?")
        self.assertEqual(suggestions.offer(messages), "propose")       # «ti ci porti» is not «portarti»
        messages = turn("Dov'è l'ombra?", "È sul sottocampo Sud. Posso portarti lì?")
        self.assertEqual(suggestions.offer(messages), "take")
        self.assertEqual(suggest(messages, Facts(phase="model"))[0], "Yes, take me there")

    def test_a_question_at_the_end_that_is_not_an_offer_gives_no_yes(self):
        messages = turn("Quanto produce?", "Circa 51.000 kWh l'anno. Ti torna con quello che ti aspettavi?")
        self.assertEqual(suggestions.offer(messages), "")

    def test_the_results_read_give_the_questions_of_the_results_once_the_year_is_there(self):
        messages = turn("Quanto produce l'impianto?", "Circa 51.000 kWh, resa specifica 1.240 kWh/kWp, PR 0,84.",
                        [("read_results", {"section": "production"})], phase="Producibilità")
        got = suggest(messages, Facts(phase="production", year=True, subfields=1))
        self.assertEqual(got[:2], ["Which losses weigh most?", "Is this specific yield plausible for the site?"])
        self.assertEqual(len(got), 3)

    def test_without_the_year_the_results_phase_asks_what_is_missing_and_nothing_that_needs_it(self):
        got = suggest([], Facts(phase="production"))
        self.assertEqual(got[0], "What is missing to compute the year?")
        for needs_the_year in ("Which losses weigh most?", "Why is the performance ratio this one?",
                               "How far is it from PVGIS?"):
            self.assertNotIn(needs_the_year, got)

    def test_the_words_of_the_question_bring_their_topic_without_any_tool(self):
        messages = turn("Quanti moduli posso mettere in serie su questo inverter?", "Al massimo 17, per la Uoc a "
                        "-10 °C.")
        self.assertEqual(suggestions.topics(messages)[0], "strings")
        got = suggest(messages, Facts(phase="plant", strings=True))
        self.assertIn("How many modules in series at most, and why?", got)

    def test_a_short_word_counts_only_whole_spi_is_not_spiegami(self):
        self.assertNotIn("rules", suggestions.text_topics("Spiegami meglio la prima parte"))
        self.assertIn("rules", suggestions.text_topics("Serve lo SPI dedicato?"))
        self.assertNotIn("pr", suggestions.text_topics("Prima di tutto, il problema"))
        self.assertIn("pr", suggestions.text_topics("Perché il PR è basso?"))

    def test_a_question_already_asked_is_never_offered_again(self):
        messages = turn("Which losses weigh most?", "Le ombre e la temperatura.",
                        [("read_results", {"section": "production"})])
        got = suggest(messages, Facts(phase="production", year=True))
        self.assertNotIn("Which losses weigh most?", got)
        self.assertEqual(len(got), len(set(got)))

    def test_a_proposal_shown_brings_why_and_another_way(self):
        messages = turn("Sistema l'ombra", "Ti ho proposto la posa fuori dalle ombre.",
                        [("propose_fix", {"check_id": "c2"})])
        got = suggest(messages, Facts(phase="model", year=True))
        self.assertEqual(got[:2], ["Why exactly this change?", "Is there another way?"])
        refused = turn("Sistema l'ombra", "Non ci riesco.", [("propose_fix", {"check_id": "c9"})], results=[True])
        self.assertFalse(suggestions.proposed(refused))

    def test_the_manual_searched_gives_the_key_and_the_menus(self):
        messages = turn("Come faccio a confrontare due varianti?", "Menu Varianti, Ctrl+Maiusc+C.",
                        [("search_manual", {"query": "confrontare varianti"})])
        got = suggest(messages, Facts(phase="model"))
        self.assertIn("Is there a key for it?", got)

    def test_the_selected_sub_field_is_named_in_its_question(self):
        messages = turn("Come va la posa?", "Bene: 120 moduli sul tetto.", [("read_selection", {})])
        got = suggest(messages, Facts(phase="model", selected="Sud"))
        self.assertEqual(got[0], "Is the layout of «Sud» right?")

    def test_never_more_than_three_and_each_one_once(self):
        messages = []
        for q in ("Ci sono problemi?", "Quanto produce?", "Conviene?", "Serve la batteria?"):
            messages += turn(q, "Vuoi che te lo proponga?", [("read_checks", {}), ("read_results",
                                                                                  {"section": "economics"})])
        got = suggest(messages, Facts(phase="economics", year=True, economics=True, consumption=True,
                                      worst=(UOC,)))
        self.assertLessEqual(len(got), 3)
        self.assertEqual(len(got), len(set(got)))

    def test_the_lines_before_the_question_are_not_the_question(self):
        content = "(The designer applied p1.)\n(Phase: Modello. Selected: sottocampo Sud.)\nE adesso?"
        self.assertEqual(suggestions.plain_question(content), "E adesso?")
        self.assertEqual(suggestions.plain_question("(una parentesi) e una domanda"), "(una parentesi) e una domanda")

    def test_a_long_check_is_cut_at_a_word(self):
        self.assertEqual(suggestions.quote(UOC), "Inverter tetto, ingresso 2, 18 in serie: Uoc max…")
        self.assertEqual(suggestions.quote("Corto."), "Corto")

    def test_the_facts_are_read_from_the_window_or_a_host(self):
        p = capannone_rho()
        p.subfields[0].filled = True
        host = with_problems(Host(p, selection=("subfield", p.subfields[0].id), phase="plant"))
        facts = suggestions.facts_of(host)
        self.assertEqual(facts.phase, "plant")
        self.assertEqual(facts.worst[0], UOC)                      # the most serious first
        self.assertFalse(facts.year or facts.economics or facts.consumption)
        self.assertEqual(facts.selected, p.subfields[0].name)
        self.assertEqual(facts.subfields, 1)

    def test_they_come_at_once_even_after_a_long_conversation(self):
        messages = []
        for n in range(40):
            messages += turn(f"Domanda {n} sulle stringhe e le perdite?", "Risposta con kWh e PR. " * 20,
                             [("read_results", {"section": "production"}), ("read_checks", {})])
        facts = Facts(phase="production", year=True, worst=(UOC, SHADE))
        t = time.perf_counter()
        for _ in range(20):
            suggest(messages, facts)
        self.assertLess((time.perf_counter() - t) / 20, 0.02)


if __name__ == "__main__":
    unittest.main()
