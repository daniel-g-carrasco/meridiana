"""The rules that apply to a system, as the notes of its technical report: which ones apply at each size,
voltage level, fire control, mounting and storage; the minimum renewable capacity of the building with the
national and the Lombardy coefficients; the notes as text."""

import unittest
from types import SimpleNamespace

import _setup  # noqa: F401

from meridiana import checks, model, rules


def ids(f):
    return [r.id for r in rules.applying(f)]


def facts(**kw):
    f = rules.Facts(p_dc_kw=10.0, p_ac_kw=10.0, installs={"BAPV"}, fire=False)
    for k, v in kw.items():
        setattr(f, k, v)
    if "level" not in kw:
        f.level = rules.auto_level(f.p_nominal_kw)
    return f


class Which(unittest.TestCase):
    def test_a_small_house_in_low_voltage(self):
        got = ids(facts(p_dc_kw=4.5, p_ac_kw=4.0, premises="domestic", contracted_kw=3.0, floor_m2=120.0))
        self.assertEqual(got[:2], ["N01", "N03"])             # the installer may design
        self.assertIn("N04", got)                            # the inverter's own interface protection
        self.assertNotIn("N05", got)
        self.assertIn("N14", got)                            # not subject to the fire brigade
        self.assertEqual(got[-1], "N23")                     # permitting, always

    def test_the_nominal_power_is_the_smaller_of_modules_and_inverters(self):
        f = facts(p_dc_kw=12.5, p_ac_kw=10.0)                 # CEI 0-21:2026-07 3.61
        self.assertEqual(f.p_nominal_kw, 10.0)
        self.assertIn("N04", ids(f))
        self.assertNotIn("N05", ids(f))
        self.assertIn("N05", ids(facts(p_dc_kw=12.5, p_ac_kw=12.0)))

    def test_a_business_roof_subject_to_the_fire_brigade(self):
        got = ids(facts(p_dc_kw=60.0, p_ac_kw=50.0, fire=True, inverters=2, storage=True))
        for rule in ("N02", "N05", "N06", "N08", "N13", "N15", "N22"):
            self.assertIn(rule, got)
        self.assertNotIn("N14", got)
        self.assertNotIn("N09", got)

    def test_medium_and_high_voltage_from_the_power(self):
        # 100 kW, low or medium voltage: CEI 0-21:2026-07 6.3 Tab. 5 p. 33 and 7.4.10 p. 46, CEI 0-16:2026-07 6.3
        # Tab. 4 p. 43 (0,1 MW); 6-10 MW "MT o AT", above 10 MW the high voltage: CEI 0-16:2026-07 Tab. 4 p. 43
        # (verified on the archive: docs/studio/18-prove/B-norme-citazioni.md, section 3)
        self.assertEqual(rules.auto_level(100.0), "BT")
        self.assertEqual(rules.auto_level(100.5), "MT")
        self.assertEqual(rules.auto_level(12000.0), "AT")
        mv = ids(facts(p_dc_kw=900.0, p_ac_kw=800.0))
        self.assertIn("N09", mv)
        self.assertIn("N10", mv)                              # RIGEDI and the plant controller (ARERA 385/2025 art. 2.1 p. 22)
        self.assertFalse({"N04", "N05", "N06", "N07"} & set(mv))
        self.assertIn("N07", ids(facts(p_dc_kw=150.0, p_ac_kw=150.0, level="BT")))    # the designer said BT

    def test_too_high_a_voltage_is_to_fix(self):
        # above 1500 V d.c. the system is no longer low voltage: CEI 64-8/1 11.2 p. 10; DCPREV 14030/2025 1.2 p. 5
        f = facts(uoc_max=1580.0)
        rule = next(r for r in rules.applying(f) if r.id == "N12")
        self.assertEqual(rule.level, "fail")

    def test_ground_mounted_and_canopies(self):
        got = ids(facts(installs={"ground"}, fire=None))
        self.assertIn("N21", got)
        self.assertIn("N27", got)
        self.assertFalse({"N13", "N14", "N15"} & set(got))
        self.assertIn("N18", ids(facts(installs={"canopy"}, fire=True)))


class Design(unittest.TestCase):
    """Who may design under DM 37/2008 art. 5 par. 2 (p. 4): the supply and the premises decide, not the PV
    power."""

    def paragraphs(self, f, rule_id):
        rule = next(r for r in rules.applying(f) if r.id == rule_id)
        return rule.paragraphs(f)

    def test_a_small_system_on_a_large_shed_needs_a_professional(self):
        f = facts(p_dc_kw=5.0, p_ac_kw=5.0, premises="productive", contracted_kw=4.0, floor_m2=2000.0)
        self.assertEqual(rules.design(f), "professional")
        self.assertIn("N02", ids(f))
        self.assertNotIn("N03", ids(f))
        self.assertIn("above 200 m²", self.paragraphs(f, "N02")[0])
        self.assertIn("2,000 m²", self.paragraphs(f, "N02")[0])

    def test_a_house_with_3_kw_and_150_m2_may_be_designed_by_the_installer(self):
        f = facts(p_dc_kw=6.5, p_ac_kw=6.0, premises="domestic", contracted_kw=3.0, floor_m2=150.0)
        self.assertEqual(rules.design(f), "installer")
        self.assertIn("N03", ids(f))
        self.assertNotIn("N02", ids(f))
        self.assertIn("not above 400 m²", self.paragraphs(f, "N03")[0])
        self.assertIn("art. 5 par. 1", rules.title(next(r for r in rules.RULES if r.id == "N03"), f))

    def test_premises_subject_to_fire_control_or_at_risk_need_a_professional(self):
        f = facts(premises="productive", contracted_kw=3.0, floor_m2=150.0, fire=True)
        self.assertEqual(rules.design(f), "professional")
        self.assertIn("751.03", self.paragraphs(f, "N02")[0])
        f = facts(premises="domestic", contracted_kw=3.0, floor_m2=150.0, risk=True)
        self.assertEqual(rules.design(f), "professional")
        self.assertIn("art. 5 par. 2 d", self.paragraphs(f, "N02")[0])
        self.assertEqual(rules.design(facts(premises="condominium", contracted_kw=3.0, floor_m2=100.0)), "professional")
        self.assertEqual(rules.design(facts(premises="domestic", contracted_kw=3.0, floor_m2=150.0, level="MT")),
                         "professional")
        self.assertEqual(rules.design(facts(premises="domestic", contracted_kw=7.5, floor_m2=150.0)), "professional")

    def test_without_the_data_the_professional_is_taken_as_due(self):
        f = facts(p_dc_kw=4.5, p_ac_kw=4.0)                     # a small system, but nothing said of the supply
        self.assertEqual(rules.design(f), "unknown")
        self.assertIn("N02", ids(f))
        self.assertNotIn("N03", ids(f))
        text = self.paragraphs(f, "N02")
        self.assertIn("not stated", text[0])
        self.assertIn("installer's technical manager", text[2])
        self.assertIn("until the supply", rules.title(next(r for r in rules.RULES if r.id == "N02"), f))
        self.assertEqual(rules.design(facts(premises="productive", contracted_kw=3.0)), "unknown")   # no area yet
        ask = checks.rule_items(f)
        self.assertTrue(any(i.target == ("site",) and "contracted power" in i.text for i in ask))

    def test_the_facts_read_the_supply_from_the_project(self):
        p = model.Project()
        p.rules = {"contracted_kw": 4.5, "floor_m2": 180, "premises": "productive", "risk": True}
        f = rules.facts(p)
        self.assertEqual((f.contracted_kw, f.floor_m2, f.premises, f.risk), (4.5, 180.0, "productive", True))
        p.rules = {"premises": "castle"}
        self.assertEqual(rules.facts(p).premises, "")           # an unknown value counts as not stated


class Minimum(unittest.TestCase):
    """P = k x S of the D.Lgs. 199/2021 (testo vigente, with the D.Lgs. 5/2026), All. III Sez. B points 3 and 5 and
    Sez. C points 2-3, p. 53: k = 0,05 for a new building, 0,025 for a major renovation, public buildings +10 %.
    Lombardy from 01/01/2027: k = 0,08 and 0,06, allegato al decreto 6437/2026 6.27 p. 20 and 6.14 c) iv p. 17,
    DGR 6153 p. 6 (B-norme-citazioni.md, section 3)."""

    def test_new_and_renovated_buildings(self):
        self.assertIsNone(rules.minimum(facts(footprint_m2=1000.0)))          # not stated: nothing to compute
        k, p = rules.minimum(facts(obligation="new", footprint_m2=1000.0))
        self.assertEqual((k, round(p, 6)), (0.05, 50.0))
        k, p = rules.minimum(facts(obligation="renovation", footprint_m2=1000.0, public=True))
        self.assertEqual((k, round(p, 6)), (0.025, 27.5))                   # public buildings +10%

    def test_lombardy_raises_k_from_2027(self):
        f = facts(obligation="new", footprint_m2=1000.0, region="Lombardia", permit_2027=True, use="data_centre")
        self.assertEqual(rules.minimum(f)[0], 0.08)
        self.assertEqual(rules.minimum(facts(obligation="new", footprint_m2=1000.0, region="Lombardia",
                                             permit_2027=True, use="large_retail"))[0], 0.06)
        self.assertEqual(rules.minimum(facts(obligation="new", footprint_m2=1000.0, region="Lombardia",
                                             use="data_centre"))[0], 0.05)       # an earlier permit: national k
        got = ids(f)
        self.assertIn("N24", got)
        self.assertIn("N25", got)
        self.assertIn("N26", got)
        self.assertIn("N20", got)

    def test_the_region_from_the_address(self):
        self.assertEqual(rules.region_of("Via Roma 1, Rho, Milano, Lombardia, 20017, Italia"), "Lombardia")
        self.assertEqual(rules.region_of("Via Roma 1, Torino, Piemonte, Italia"), "")

    def test_the_check_against_the_system(self):
        low = checks.rule_items(facts(obligation="new", footprint_m2=1000.0, p_dc_kw=40.0))
        self.assertEqual([i.level for i in low if "kWp" in i.text], ["warn"])
        ok = checks.rule_items(facts(obligation="new", footprint_m2=1000.0, p_dc_kw=60.0))
        self.assertEqual([i.level for i in ok if "kWp" in i.text], ["ok"])
        ask = checks.rule_items(facts(footprint_m2=1000.0))
        self.assertTrue(any(i.target == ("site",) and "minimum renewable" in i.text for i in ask))


class Project(unittest.TestCase):
    def project(self):
        p = model.Project()
        p.site.address = "Via Roma 1, Rho, Milano, Lombardia, 20017, Italia"
        p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[[0, 0], [40, 0], [40, 25], [0, 25]],
                                          height=9.5, fire=model.Fire(subject=True)))
        p.buildings.append(model.Building(id="b2", name="Vicino", footprint=[[60, 0], [80, 0], [80, 10], [60, 10]]))
        p.subfields.append(model.SubField(id="s1", name="Copertura", ring=[[2, 2], [38, 2], [38, 23], [2, 23]],
                                          building="b1", params={"mounting": "tilted_anchored"}, filled=True))
        p.rules = {"obligation": "new"}
        return p

    def test_the_facts_of_a_drawn_project(self):
        p = self.project()
        results = {sf.id: p.fill(sf) for sf in p.subfields}
        inverter = SimpleNamespace(pac_total=40000.0, count=1, phases=3)
        f = rules.facts(p, results, None, inverter)
        self.assertGreater(f.p_dc_kw, 0)
        self.assertEqual(f.p_ac_kw, 40.0)
        self.assertEqual(f.footprint_m2, 1000.0)              # only the building with the modules
        self.assertEqual(f.footprint_of, ["Capannone"])
        self.assertIs(f.fire, True)
        self.assertEqual(f.installs, {"BAPV"})
        self.assertEqual(f.region, "Lombardia")
        self.assertEqual(f.level, "BT")
        p.rules = {**p.rules, "connection": "MT"}
        self.assertEqual(rules.facts(p, results, None, inverter).level, "MT")

    def test_the_rules_are_saved_with_the_project(self):
        p = self.project()
        p.rules = {"obligation": "renovation", "public": True, "connection": "MT"}
        q = model.Project.from_json(p.to_json())
        self.assertEqual(q.rules, p.rules)
        old = p.to_json()
        old["version"] = 2
        del old["rules"]
        self.assertEqual(model.Project.from_json(old).rules, {})

    def test_the_notes_as_text(self):
        p = self.project()
        results = {sf.id: p.fill(sf) for sf in p.subfields}
        f = rules.facts(p, results, None, SimpleNamespace(pac_total=40000.0, count=1, phases=3))
        text = rules.notes_text(f)
        self.assertTrue(text.startswith("1. REFERENCE STANDARDS AND DESIGN"))
        self.assertIn("4. MINIMUM RENEWABLE CAPACITY OBLIGATION", text)
        self.assertIn("P = k × S = 50.0 kW", text)
        self.assertIn("Source: CEI 64-8/7:2024-07", text)


if __name__ == "__main__":
    unittest.main()
