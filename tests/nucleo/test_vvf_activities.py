"""The activities subject to fire prevention controls (R327): Annex I of DPR 151/2011 as data, all 80, the
thresholds and the categories as the GU no. 221 of 22/09/2011 prints them (checked by hand on the PDF of Daniel's
archive, pages 9-24), the search by number and by words."""

import unittest

import _setup  # noqa: F401

from meridiana import vvf_activities as vvf


class Annex(unittest.TestCase):
    def test_eighty_activities_numbered_one_to_eighty_each_with_its_text_and_a_category(self):
        self.assertEqual([a.number for a in vvf.ACTIVITIES], list(range(1, 81)))
        for a in vvf.ACTIVITIES:
            with self.subTest(activity=a.number):
                self.assertTrue(a.text and a.short)
                self.assertIn(a.threshold, a.text)          # the threshold is the law's words, never a summary
                self.assertTrue(a.categories())             # every row of the table has at least one category
                self.assertTrue(5 <= a.page <= 20)          # GU pages of Annex I
                self.assertNotIn("—", a.text + a.short)
        self.assertIn("GU Serie generale n. 221 del 22/09/2011", vvf.SOURCE)

    def test_samples_against_the_text_of_the_gu(self):
        # 49, GU p. 14: generators and cogeneration above 25 kW; A up to 350 kW, B up to 700 kW, C above
        a = vvf.activity(49)
        self.assertIn("motori endotermici", a.text)
        self.assertEqual(a.threshold, "di potenza complessiva superiore a 25 kW")
        self.assertEqual({c: a.category_text(c) for c in a.categories()},
                         {"A": "fino a 350 kW", "B": "oltre 350 kW e fino a 700 kW", "C": "oltre 700 kW"})
        # 75, GU p. 19: car parks above 300 m²; A up to 1.000 m²
        a = vvf.activity(75)
        self.assertIn("superficie complessiva coperta superiore a 300 m²", a.threshold)
        self.assertEqual(a.category_text("A"), "Autorimesse fino a 1.000 m²")
        self.assertTrue(a.category_text("C").startswith("Autorimesse oltre 3000 m²"))
        # 71, GU p. 18: offices above 300 people
        a = vvf.activity(71)
        self.assertEqual(a.text, "Aziende ed uffici con oltre 300 persone presenti")
        self.assertEqual(a.category_text("C"), "oltre 800 persone")
        # 70, GU p. 18: depots above 1000 m² with more than 5.000 kg of goods; categories B and C only
        a = vvf.activity(70)
        self.assertIn("superiore a 1000 m²", a.threshold)
        self.assertIn("superiori complessivamente a 5.000 kg", a.threshold)
        self.assertEqual(a.categories(), ("B", "C"))
        self.assertEqual(a.category_text("B"), "fino a 3.000 m²")
        # 74, GU p. 19: heat generators above 116 kW
        self.assertEqual(vvf.activity(74).threshold, "con potenzialità superiore a 116 kW")
        # 3, GU p. 5-6: sub-items with their own rows
        three = vvf.activity(3)
        self.assertEqual(len(three.bands), 2)
        self.assertEqual(three.category_text("A"), "b) disciolti o liquefatti: Depositi di GPL fino a 300 kg")
        # 80, GU p. 20: «tutte» stands in column A
        self.assertEqual(vvf.activity(80).categories(), ("A",))

    def test_an_activity_by_number_or_none(self):
        self.assertIsNone(vvf.activity(0))
        self.assertIsNone(vvf.activity(81))
        self.assertIsNone(vvf.activity("x"))
        self.assertEqual(vvf.activity("64").number, 64)

    def test_search_by_number_and_by_words_ignoring_accents_and_case(self):
        self.assertEqual([a.number for a in vvf.search("49")], [49])
        self.assertIn(75, [a.number for a in vvf.search("autorimesse")])
        self.assertIn(71, [a.number for a in vvf.search("UFFICI")])
        self.assertEqual(vvf.search("gruppi elettrogeni endotermici")[0].number, 49)
        self.assertIn(64, [a.number for a in vvf.search("elaborazione dati")])
        self.assertIn(77, [a.number for a in vvf.search("altezza antincendio")])
        self.assertIn(16, [a.number for a in vvf.search("infiammabilita solventi")])   # «infiammabilità»
        self.assertEqual(vvf.search(""), [])
        self.assertEqual(vvf.search("di e con"), [])
        self.assertEqual(vvf.search("attività 71")[0].number, 71)
        self.assertEqual(vvf.search("gruppo elettrogeno")[0].number, 49)      # the singular finds the plural
        self.assertEqual(vvf.search("ufficio")[0].number, 71)
        self.assertEqual({a.number for a in vvf.search("autorimessa")[:2]}, {59, 75})
        self.assertIn(70, [a.number for a in vvf.search("deposito 10.000 m²")])
        self.assertNotIn(10, [a.number for a in vvf.search("deposito 10.000 m²")[:1]])    # a measure is no number
        self.assertEqual(vvf.search("10.000 m²"), [])
        self.assertEqual(vvf.search("data center")[0].number, 64)

    def test_the_index_has_every_activity_and_fits_one_answer_of_a_tool(self):
        lines = vvf.index()
        self.assertEqual(len(lines), 80)
        self.assertTrue(lines[48].startswith("49. "))
        self.assertLess(len("".join(lines)), 5000)

    def test_a_choice_in_the_list_keeps_the_switch_and_the_category_coherent(self):
        self.assertEqual(vvf.shown(False, 0), 0)
        self.assertEqual(vvf.shown(True, 0), vvf.NOT_SPECIFIED)                 # a project before format 24
        self.assertEqual(vvf.shown(True, 49), 49)
        self.assertEqual(vvf.chosen(49, "B"), {"subject": True, "activity": 49, "category": "B"})
        self.assertEqual(vvf.chosen(70, "A"), {"subject": True, "activity": 70, "category": ""})   # 70 has no A
        self.assertEqual(vvf.chosen(57), {"subject": True, "activity": 57, "category": "C"})       # 57 has C alone
        self.assertEqual(vvf.chosen(0, "B"), {"subject": False, "activity": 0, "category": ""})
        self.assertEqual(vvf.chosen(vvf.NOT_SPECIFIED, "B"), {"subject": True, "activity": 0, "category": "B"})

    def test_as_dict_gives_the_categories_and_the_page(self):
        d = vvf.as_dict(vvf.activity(49))
        self.assertEqual(d["number"], 49)
        self.assertEqual(d["categories"]["B"], "oltre 350 kW e fino a 700 kW")
        self.assertTrue(d["source"].endswith("p. 14"))
        self.assertEqual(vvf.as_dict(vvf.activity(29))["threshold"], "tutte (nessuna soglia)")


if __name__ == "__main__":
    unittest.main()
