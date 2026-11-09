"""Meridio knows the design rules (R462, Daniel 06/11/2026: «Meridio deve sapere tutte queste cose per consigliare le
scelte migliori»): 15 real questions put to the tool `design_rules` as the model would, verbatim, with the rule that
must come back among the first three and its source. No model is called: the tool alone answers, from the data the
program designs with (catalog/data/optimizer_rules.json, preferred_makers.json, energy/sizing.py, rules.py)."""

import json
import unittest

from meridiana.assistant import design_rules, tools


class _Host:
    project = None


# question, passage id expected among the first three, words of its text, words of its source
QUESTIONS = [
    ("Che ottimizzatore metto con un SE20K e moduli da 465 W?", "solaredge.S1400.SE20K",
     ("14-30 optimizers", "continuous power 18.000 W", "20.250 W", "28.000 W"), ("DS-000205-EU", "p. 3")),
    ("Posso mettere un singolo in una stringa di S1400?", "solaredge_s1400.mixing",
     ("at most one optimizer with a single module per string",), ("DS-000205-EU", "nota 9", "nota 8")),
    ("Che rapporto DC/AC uso?", "dcac.band", ("1,10 by default", "0,95-1,30"), ("energy/sizing.py", "studio/34")),
    ("Quanta potenza posso collegare per stringa con S1000 su un SE33.3K?", "solaredge.S1000.SE33.3K",
     ("continuous power 13.500 W", "15.750 W per string with 1-2 strings", "18.500 W with 3 strings"), ("DS-000105-IT", "p. 3")),
    ("Posso usare gli S1200 su un SE33.3K?", "solaredge.S1200.SE33.3K", ("continuous power 17.000 W",),
     ("DS-000105-IT",)),
    ("Gli ottimizzatori Huawei vanno su un inverter di un'altra marca?", "huawei.makers",
     ("With inverters of other makers: no",), ("optimizer_rules.json (Huawei)",)),
    ("Posso installare i Tigo TS4-A-O solo su alcuni moduli?", "tigo_ts4_o.partial",
     ("yes, with conditions", "senza stringhe in parallelo"), ("support.tigoenergy.com", "14/09/2026")),
    ("Con i MERC-1300W-P posso mettere due stringhe sullo stesso MPPT?", "huawei_merc.parallel",
     ("at most 1 string per MPPT",), ("Optimierer-Anleitung", "p. 7")),
    ("Quali marche di inverter preferiamo?", "preferred.inverters",
     ("Huawei, SMA, Fronius, SolarEdge", "for Daniel to confirm"), ("preferred_makers.json",)),
    ("Quanto possono essere grandi i sottocampi per i vigili del fuoco?", "fire.N15",
     ("no larger than 20 m in any direction", "corridors of at least 2 m"), ("DCPREV 14030/2025 sect. 3.3.5.1",)),
    ("A che distanza dagli evacuatori di fumo devo stare con i moduli?", "fire.N15",
     ("at least 1 m from smoke vents",), ("DCPREV 14030/2025", "3.3.5.1")),
    ("Quanti moduli al massimo per stringa con SUN2000-450W-P2 su un SUN2000-10KTL-M1?", "huawei_sun2000_p.strings",
     ("KTL-M1", "6-35 optimizers", "10.000 W per string"), ("scheda IT del 06/02/2023", "p. 1")),
    ("Posso mescolare S440 e P401 nella stessa stringa?", "solaredge_s_res.mixing", ("no",),
     ("DS-000091-IT", "nota 7", "serie S e serie P mai nella stessa stringa")),
    ("Le proposte automatiche possono andare sopra la potenza continua?", "solaredge.policy",
     ("never goes above the continuous power on SolarEdge's residential tables", "within the power the table allows "
      "connected"), ("R456", "proposal_tiers")),
    ("Con il TS4-A-2F posso lasciare un modulo da solo?", "tigo_ts4_2f.mixing", ("with TS4-A-F in the same string",),
     ("002-00157-00", "p. 2")),
]


class DesignRulesTest(unittest.TestCase):
    def ask(self, question: str, **more) -> dict:
        out = tools.run("design_rules", {"query": question, **more}, _Host(), tools.State())
        self.assertFalse(out.error, out.content)
        self.assertLessEqual(len(out.content), tools.RESULT_LIMIT)
        return json.loads(out.content)

    def test_fifteen_questions_find_the_rule_with_its_source(self):
        self.assertEqual(len(QUESTIONS), 15)
        for question, pid, words, source in QUESTIONS:
            with self.subTest(question=question):
                found = self.ask(question)["rules"]
                first = {r["id"]: r for r in found[:3]}
                self.assertIn(pid, first, [r["id"] for r in found])
                for w in words:
                    self.assertIn(w, first[pid]["text"])
                for s in source:
                    self.assertIn(s, first[pid]["source"])

    def test_the_advice_is_the_programs_own_choice(self):
        """SE20K and modules of 465 W: the stringing's choice (energy/optimizers.suggest), S1400 with two modules,
        with the numbers of its table; S1000 and S1200 refused for an SE20K, as rules_for does."""
        advice = self.ask("Che ottimizzatore metto con un SE20K e moduli da 465 W?")["advice"]
        self.assertTrue(advice["program_would_choose"].startswith("SolarEdge S1400, 2 module(s)"))
        s1400 = advice["optimizers"][0]
        self.assertEqual(s1400["optimizer"], "SolarEdge S1400")
        self.assertEqual(s1400["rules"]["continuous_w"], 18000.0)
        self.assertEqual((s1400["rules"]["connected_w_fewer"], s1400["rules"]["connected_w_many"]), (20250.0, 28000.0))
        self.assertIn("DS-000205-EU", s1400["source"])
        refused = {o["optimizer"]: o.get("why", "") for o in advice["optimizers"] if "rules" not in o}
        self.assertIn("not for SE20K", refused["SolarEdge S1000"])

    def test_s1200_on_se33_3k_carries_the_850_v_warning(self):
        advice = self.ask("Posso usare gli S1200 su un SE33.3K?")["advice"]
        s1200 = next(o for o in advice["optimizers"] if o["optimizer"] == "SolarEdge S1200")
        self.assertTrue(any("850 V" in w and "note 11" in w for w in s1200["warnings"]), s1200)
        self.assertFalse(advice["program_would_choose"].startswith("SolarEdge S1200"))

    def test_an_inverter_with_mppt_gets_its_familys_string_rule(self):
        advice = self.ask("Quanti moduli al massimo per stringa con SUN2000-450W-P2 su un SUN2000-10KTL-M1?",
                          module_w=450)["advice"]
        rule = advice["string_rule"]
        self.assertEqual((rule["state"], rule["optimizers_min"], rule["optimizers_max"], rule["p_string_w"]),
                         ("ok", 6, 35, 10000.0))
        self.assertIn("06/02/2023", rule["source"])
        self.assertIn("fits", advice["module_power"])

    def test_the_passages_come_from_the_data_with_a_source_each(self):
        data = json.loads((design_rules.DATA / "optimizer_rules.json").read_text(encoding="utf-8"))
        families = [f["id"] for entry in data.values() if isinstance(entry, dict) for f in entry.get("families", [])]
        ids = {p["id"] for p in design_rules.passages()}
        for fid in families:
            self.assertIn(fid, ids)
        self.assertTrue(all(p["source"].strip() for p in design_rules.passages()))
        self.assertIn("design_rules", tools.STEP_2)
        self.assertIn("design_rules", {s["name"] for s in tools.specs()})

    def test_words_of_no_topic_say_so_and_list_the_topics(self):
        out = self.ask("zzzz qqqq")
        self.assertEqual(out["rules"], [])
        self.assertIn("topics", out)
        self.assertTrue(tools.run("design_rules", {"query": ""}, _Host(), tools.State()).error)


class PartialAndFacesTest(unittest.TestCase):
    """R456 answer 6 and R433: Meridio knows the partial installation and the strings over two faces as the program
    applies them, each with its pages."""

    def ids(self, query):
        return [p["id"] for p in design_rules.search(query)["rules"]]

    def test_partial_installation_by_family_with_the_pages(self):
        found = self.ids("ottimizzatori solo su alcuni moduli in ombra con SUN2000-450W-P2")
        self.assertIn("huawei_sun2000_p.partial.program", found)
        rule = next(p for p in design_rules.passages() if p["id"] == "huawei_sun2000_p.partial.program")
        self.assertIn("10/11/2025, p. 11", rule["source"])
        merc = next(p for p in design_rules.passages() if p["id"] == "huawei_merc.partial.program")
        self.assertIn("to be confirmed", merc["text"])
        se = next(p for p in design_rules.passages() if p["id"] == "solaredge.partial.program")
        self.assertIn("DS-000105-IT p. 3", se["source"])

    def test_a_string_over_two_faces(self):
        self.assertIn("faces", self.ids("la stringa puo proseguire su un'altra falda dello stesso edificio?"))
        rule = next(p for p in design_rules.passages() if p["id"] == "faces")
        self.assertIn("R433", rule["source"])


if __name__ == "__main__":
    unittest.main()
