"""The texts of the help next to things (task 17d; study 17, E.5 and E.6; design document 3.6 and 5.1): their
lengths in both languages, their sources among those of rules.py and checks.py, their places in the manual
(docs/manuale), their steps of «How it is computed»; and the anchors of the manual as GitHub makes them."""

import re
import textwrap
import unittest

import _setup

from meridiana import help as helps
from meridiana import i18n, phases, rules

SRC = _setup.ROOT / "src" / "meridiana"
CATALOGUE = _setup.ROOT / "locale" / "it" / "LC_MESSAGES" / "meridiana.mo"
# the texts the references may come from (the instruction of the task: no new citation of a standard)
REFERENCES = (SRC / "rules.py").read_text(encoding="utf-8") + (SRC / "checks.py").read_text(encoding="utf-8")
# a standard or a law named in a text, with the clause that may follow it
STANDARD = re.compile(r"\b(CEI|IEC|UNI|EN|DCPREV|DM|DPR|NTC|D\.Lgs\.|Legislative Decree)\s+([0-9][0-9A-Za-z./:-]*)"
                      r"(?:,?\s+(?:sect\.\s+|art\.\s+)?(\d+(?:\.\d+)+))?")


def in_language(language: str) -> dict:
    """The texts as the window shows them in `language`."""
    before = i18n._translation
    try:
        i18n.setup(language)
        return helps.texts()
    finally:
        i18n._translation = before


class Texts(unittest.TestCase):
    def languages(self):
        return ("en", "it") if CATALOGUE.exists() else ("en",)

    def test_the_short_sentence_and_the_text_keep_their_lengths_in_both_languages(self):
        for language in self.languages():
            for hid, h in in_language(language).items():
                with self.subTest(hid, language=language):
                    self.assertTrue(h.title and h.short and h.text)
                    self.assertLessEqual(len(h.short), helps.SHORT, h.short)
                    self.assertLessEqual(len(h.text), helps.TEXT, h.text)
                    self.assertLessEqual(len(textwrap.wrap(h.text, helps.LINE)), helps.LINES, h.text)

    def test_the_italian_is_a_translation_not_the_source_again(self):
        if not CATALOGUE.exists():
            self.skipTest("tools/compile_po.py first")
        english, italian = helps.texts(), in_language("it")
        for hid in english:
            with self.subTest(hid):
                self.assertNotEqual(english[hid].short, italian[hid].short)
                self.assertNotEqual(english[hid].text, italian[hid].text)

    def test_every_source_is_a_rule_or_a_reference_already_in_rules_or_checks(self):
        ids = {r.id for r in rules.RULES}
        for hid, h in helps.texts().items():
            for source in h.source:
                with self.subTest(hid, source=source):
                    if re.fullmatch(r"N\d\d", source):
                        self.assertIn(source, ids)
                    else:
                        self.assertIn(source, REFERENCES)

    def test_a_rule_is_read_by_its_own_source(self):
        h = helps.get("subfield.edge")
        self.assertEqual(helps.sources(h), [next(r for r in rules.RULES if r.id == "N15").source()])
        self.assertEqual(helps.sources(helps.get("subfield.pitch")), ["CEI 82-25/3 6.2"])

    def test_no_text_cites_a_standard_or_a_clause_that_rules_and_checks_do_not(self):
        for language in self.languages():
            for hid, h in in_language(language).items():
                for found in STANDARD.finditer(f"{h.short} {h.text}"):
                    name, number, clause = found.groups()
                    with self.subTest(hid, language=language, reference=found.group(0)):
                        self.assertIn(number, REFERENCES)
                        if clause:
                            self.assertIn(clause, REFERENCES)

    def test_the_pattern_finds_the_standards_and_their_clauses(self):
        found = [m.groups() for m in STANDARD.finditer(
            "CEI 82-25/3 6.2 gives; DCPREV 14030/2025, 3.3.5.1 and DM 37/2008 art. 5 par. 2; CEI 0-21:2026-07 3.61")]
        self.assertEqual(found, [("CEI", "82-25/3", "6.2"), ("DCPREV", "14030/2025", "3.3.5.1"),
                                 ("DM", "37/2008", None), ("CEI", "0-21:2026-07", "3.61")])
        self.assertNotIn("99-99", REFERENCES)                  # a made-up standard would be caught

    def test_every_phase_has_its_help(self):
        for phase in phases.phases():
            with self.subTest(phase.id):
                self.assertIsNotNone(helps.get(helps.for_phase(phase.id)))

    def test_every_step_of_how_it_is_computed_exists_in_the_computation(self):
        energy = "".join(p.read_text(encoding="utf-8") for p in (SRC / "energy").glob("*.py"))
        for hid, h in helps.texts().items():
            if not h.pedigree:
                continue
            page, _colon, step = h.pedigree.partition(":")
            with self.subTest(hid, pedigree=h.pedigree):
                self.assertIn(page, ("production", "consumption", "economics"))
                if step:
                    self.assertIn(f'Step("{step}"', energy)

    def test_the_question_for_meridio_names_what_it_is_about(self):
        h = helps.get("production.pr")
        self.assertIn(h.title, helps.question(h))
        self.assertIsNone(helps.get(""))
        self.assertIsNone(helps.get("nothing.here"))


class Manual(unittest.TestCase):
    def test_every_anchor_the_help_uses_is_a_heading_of_the_manual(self):
        folder = helps.manual_dir()
        self.assertEqual(folder, _setup.ROOT / "docs" / "manuale")
        known = {p.name: helps.anchors(p.read_text(encoding="utf-8")) for p in folder.glob("*.md")}
        for hid, h in helps.texts().items():
            chapter, anchor = helps.split(h.manual)
            with self.subTest(hid, manual=h.manual):
                self.assertIn(chapter, known)
                self.assertIn(anchor, known[chapter])

    def test_the_chapters_are_there_each_with_its_title_and_their_links_lead_somewhere(self):
        folder = helps.manual_dir()
        self.assertEqual(sorted(p.name for p in folder.glob("*.md")), sorted(helps.CHAPTERS))
        link = re.compile(r"\]\(([^)#\s]*)(?:#([^)\s]*))?\)")
        for name in helps.CHAPTERS:
            text = (folder / name).read_text(encoding="utf-8")
            with self.subTest(name):
                self.assertTrue(helps.chapter_title(text))
                anchors = helps.anchors(text)
                self.assertEqual(len(anchors), len(set(anchors)))
            for target, anchor in link.findall(text):
                with self.subTest(name, link=f"{target}#{anchor}"):
                    chapter = target or name
                    self.assertIn(chapter, helps.CHAPTERS)
                    if anchor:
                        self.assertIn(anchor, helps.anchors((folder / chapter).read_text(encoding="utf-8")))

    def test_anchors_as_github_makes_them(self):
        self.assertEqual(helps.slug("1. Modello"), "1-modello")
        self.assertEqual(helps.slug("Dal bordo dell'area"), "dal-bordo-dellarea")
        self.assertEqual(helps.slug("Moduli per tavola, in altezza"), "moduli-per-tavola-in-altezza")
        self.assertEqual(helps.slug("3. Producibilità"), "3-producibilità")
        self.assertEqual(helps.anchors("# A\n\n## B b\n\n```\n# not a heading\n```\n\n### B b\n#no\n"),
                         ["a", "b-b", "b-b-1"])
        self.assertEqual(helps.split("1-modello.md#tra-le-file"), ("1-modello.md", "tra-le-file"))
        self.assertEqual(helps.split("README.md"), ("README.md", ""))


if __name__ == "__main__":
    unittest.main()
