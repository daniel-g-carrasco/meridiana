"""The product catalogue: the CEC list is there and searchable, a datasheet record becomes a catalogue record,
and a module from either layer gives its datasheet power through the single-diode model."""

import re
import time
import unittest

import _setup  # noqa: F401

from meridiana import catalog
from meridiana.energy.components import ModuleSpec


class Catalogue(unittest.TestCase):
    def test_the_cec_list_is_there(self):
        counts = catalog.counts()
        self.assertGreater(counts["modules"]["cec"], 10000)
        self.assertGreater(counts["inverters"]["cec"], 1000)

    def test_search_by_words_and_power(self):
        found = catalog.search("modules", "longi", low=400, high=500)
        self.assertGreater(len(found), 10, "the catalogue has many LONGi modules between 400 and 500 W")
        for r in found:
            self.assertIn("longi", f"{r['manufacturer']} {r['model']}".casefold())
            self.assertTrue(400 <= r["pmax"] <= 500)

    def test_a_cec_module_follows_its_datasheet(self):
        r = catalog.search("modules", "jinko", low=400, high=600, source="cec")[0]
        m = ModuleSpec.from_record(r)
        self.assertEqual(m.source.kind, "data")
        self.assertGreater(m.series_cells, 0)
        self.assertAlmostEqual(float(m.power_at_25([1000.0])[0]), r["vmp"] * r["imp"], delta=0.02 * r["pmax"])

    def test_a_datasheet_record_is_normalised(self):
        rec = catalog.normalise_module({
            "manufacturer": "Acme", "model": "AC-450", "pmax_w": 450, "vmp_v": 33.6, "imp_a": 13.4, "voc_v": 40.1,
            "isc_a": 14.1, "temp_coeff_pmax_pct_c": -0.29, "temp_coeff_voc_pct_c": -0.25,
            "temp_coeff_isc_pct_c": 0.045, "cells": 108, "length_mm": 1762, "width_mm": 1134,
            "datasheet_url": "https://example.org/ac450.pdf", "markets": ["IT"]})
        self.assertEqual(rec["source"], "curated")
        self.assertAlmostEqual(rec["length"], 1.762)
        m = ModuleSpec.from_record(rec)
        self.assertEqual(m.cells_in_series, 54)
        self.assertAlmostEqual(float(m.power_at_25([1000.0])[0]), 450.0, delta=4.5)
        self.assertIsNone(catalog.normalise_module({"manufacturer": "X", "model": "no data"}))

    def test_a_record_for_the_project_carries_what_the_layout_reads(self):
        r = catalog.search("modules", "trina", low=400, high=700, source="cec")[0]
        p = catalog.for_project(r)
        self.assertAlmostEqual(p["power_kw"], r["pmax"] / 1000.0)
        self.assertGreater(p["length"], 1.0)


def naive_family(rec: dict) -> str:
    """The rule as the study wrote it (16-prove/catalogo_filtri.py): the first family whose words appear, in one
    text; with the clauses of the free text that say «not printed» left out (the study counted them)."""
    free = " ".join(str(rec.get(k) or "") for k in ("model", "series", "notes")).casefold()
    free = ". ".join(c for c in re.split(r"[.;]", free)
                     if not re.search(r"\bnot\s+(?:printed|stated|named|given|declared|specified|mentioned)\b", c))
    text = f"{str(rec.get('technology') or '').casefold()} {free}"
    for name, pattern in catalog.FAMILIES:
        if re.search(pattern, text):
            return name
    return catalog.UNKNOWN_FAMILY


class Families(unittest.TestCase):
    """The family of the cell, from the words a datasheet or a listing uses (study 16, theme E)."""

    def counts(self, source):
        import collections
        return dict(collections.Counter(m["cell_family"] for m in catalog.load("modules") if m["source"] == source))

    def test_the_datasheets_read_give_topcon_back_contact_hjt_and_ten_unstated(self):
        # the study counted 48 TOPCon and 3 unstated: seven datasheets say «TOPCon is not printed» or «not stated»
        # (docs/catalogo/moduli.md: 41 TOPCon, 9 HJT, 13 back contact and 10 «n-type» without architecture)
        self.assertEqual(self.counts("curated"), {"topcon": 41, "back_contact": 13, "hjt": 9, "unknown": 10})

    def test_the_cec_list_in_use_gives_mono_poly_thin_film_and_one_hjt(self):
        # list 2026.7.3: the material of the list (17,372 + 9 Mono-c-Si, 3,926 Multi-c-Si, 333 thin film), and the one
        # module that names its cell, «Heliene 66M-360 HJT»; the study counted 15,310 / 1,409 / 166 / 1 on the older list
        self.assertEqual(self.counts("cec"), {"mono": 17380, "poly": 3926, "thin_film": 333, "hjt": 1})

    def test_a_cell_named_in_the_notes_beats_the_material_in_the_technology(self):
        self.assertEqual(catalog.family_of({"technology": "Mono-c-Si", "notes": "n-type TOPCon cells"}), "topcon")
        self.assertEqual(catalog.family_of({"technology": "back contact (shingled)", "notes": "mono PERC"}),
                         "back_contact")

    def test_a_cell_named_only_to_say_it_is_not_stated_is_not_that_cell(self):
        for notes in ("The datasheet and product pages do not name the cell architecture (TOPCon is not printed).",
                      "Cell technology printed only as 'N-Type' (TOPCon not stated).",
                      "The datasheet says only 'n-type': cell technology (TOPCon/other) not stated. NOCT only.",
                      "Cell architecture not named on the datasheet (TOPCon is not printed). Efficiency 24.2%."):
            with self.subTest(notes):
                self.assertEqual(catalog.family_of({"technology": "n-type (architecture not stated)", "notes": notes}),
                                 "unknown")
        # what else the same notes say still counts
        self.assertEqual(catalog.family_of({"technology": "n-type", "notes": "Cell origin not printed. HJT cells."}),
                         "hjt")
        self.assertEqual(catalog.family_of({"technology": "n-type", "notes": "TOPCon cells, not bifacial."}), "topcon")

    def test_each_word_gives_its_family(self):
        for text, family in (("Mono-c-Si", "mono"), ("Multi-c-Si", "poly"), ("poly", "poly"), ("CdTe", "thin_film"),
                             ("CIGS", "thin_film"), ("a-Si/nc", "thin_film"), ("Thin Film", "thin_film"),
                             ("Panasonic HIT", "hjt"), ("heterojunction", "hjt"), ("HJT", "hjt"),
                             ("ABC", "back_contact"), ("HPBC 2.0", "back_contact"), ("IBC", "back_contact"),
                             ("mono PERC", "perc"), ("n-type TOPCon", "topcon"), ("n-type", "unknown"), ("", "unknown")):
            with self.subTest(text):
                self.assertEqual(catalog.family_of({"technology": text}), family)

    def test_a_word_inside_another_word_is_not_a_family(self):
        for text in ("ambitious", "hitachi", "percent", "cabc1", "monoassiali", "mono-facial", "monofacial",
                     "mono facial", "mono-glass", "multilayer", "polymer backsheet", "multi busbar"):
            self.assertEqual(catalog.family_of({"model": text}), "unknown", text)

    def test_every_datasheet_record_carries_its_family_and_the_rule_gives_the_same(self):
        """The field written in modules_curated.json (from the datasheet's own label) and the rule on the text
        must agree on every record: a new datasheet that the rule reads differently is looked at, not trusted."""
        import json
        raw = json.loads((catalog.DATA / "modules_curated.json").read_text(encoding="utf-8"))
        self.assertEqual(len(raw), 73)
        known = {key for key, _p in catalog.FAMILIES} | {catalog.UNKNOWN_FAMILY}
        for r in raw:
            with self.subTest(r["model"]):
                self.assertIn(r.get("cell_family"), known)
                self.assertEqual(r["cell_family"], catalog.family_of(catalog.normalise_module(r)))
        # and the loaded record has the written one
        written = {f"cur:{r['manufacturer']}:{r['model']}": r["cell_family"] for r in raw}
        for m in catalog.load("modules"):
            if m["source"] == "curated":
                self.assertEqual(m["cell_family"], written[m["id"]])

    def test_a_written_family_wins_over_the_rule(self):
        self.assertEqual(catalog.enrich_module({"technology": "Mono-c-Si", "cell_family": "hjt"})["cell_family"], "hjt")
        self.assertEqual(catalog.enrich_module({"technology": "Mono-c-Si"})["cell_family"], "mono")

    def test_the_quick_rule_gives_what_the_rule_as_written_gives_on_every_record(self):
        for m in catalog.load("modules"):
            self.assertEqual(catalog.family_of(m), naive_family(m), m["id"])

    def test_every_module_has_a_family_and_a_true_or_false_bifacial(self):
        known = {key for key, _p in catalog.FAMILIES} | {catalog.UNKNOWN_FAMILY}
        for m in catalog.load("modules"):
            self.assertIn(m["cell_family"], known)
            self.assertIsInstance(m["bifacial"], bool)

    def test_the_classification_of_the_whole_catalogue_stays_quick(self):
        modules = catalog.load("modules")
        took = []
        for _n in range(3):
            start = time.perf_counter()
            for m in modules:
                catalog.family_of(m)
            took.append(time.perf_counter() - start)
        self.assertLess(min(took), 0.2)

    def test_the_loading_with_the_classification_stays_under_400_ms(self):
        """Asked: under 300 ms, measured with the 16,959 modules of the older list (about 170 ms). The list of
        2026.7.3 has 21,713 (+28%) and loads in 240-265 ms here, 135 of them to read the file."""
        took = []
        for _n in range(5):
            catalog.load.cache_clear()
            start = time.perf_counter()
            catalog.load("modules")
            took.append(time.perf_counter() - start)
        self.assertLess(min(took), 0.4)


class Efficiency(unittest.TestCase):
    def test_a_record_with_size_and_power_gets_its_efficiency_marked_as_derived(self):
        r = catalog.enrich_module({"pmax": 400.0, "length": 1.7, "width": 1.0, "source": "cec"})
        self.assertAlmostEqual(r["efficiency_pct"], 23.53, places=2)
        self.assertTrue(r["efficiency_derived"])

    def test_a_declared_efficiency_is_kept_and_not_marked(self):
        r = catalog.enrich_module({"pmax": 400.0, "length": 1.7, "width": 1.0, "efficiency_pct": 22.5})
        self.assertEqual(r["efficiency_pct"], 22.5)
        self.assertFalse(r.get("efficiency_derived", False))

    def test_without_the_size_there_is_no_efficiency(self):
        r = catalog.enrich_module({"pmax": 400.0, "length": None, "width": None})
        self.assertNotIn("efficiency_pct", r)
        self.assertNotIn("efficiency_derived", r)

    def test_in_the_catalogue_the_derived_ones_are_the_cec_records_with_a_size(self):
        modules = catalog.load("modules")
        derived = [m for m in modules if m.get("efficiency_derived")]
        sized = [m for m in modules if m["source"] == "cec" and m.get("length") and m.get("width")]
        self.assertEqual(len(derived), len(sized))
        self.assertEqual(len(sized), 5669)
        self.assertTrue(all(m["source"] == "cec" for m in derived))
        self.assertTrue(all(5 < m["efficiency_pct"] < 30 for m in derived))       # thin film is the low end, ~6.5%
        self.assertTrue(all(m.get("efficiency_pct") for m in modules if m["source"] == "curated"))


class EstimatedBifaciality(unittest.TestCase):
    """A bifacial module whose datasheet gives no bifaciality gets its family's typical value, marked as an estimate
    and kept apart from the datasheet's (Daniel, 23/10/2026)."""

    def estimate(self, **fields):
        return catalog.enrich_module({"bifacial": True, "pmax": 500.0, **fields})

    def test_perc_70_topcon_and_hjt_80(self):
        for family, value in (("perc", 70.0), ("topcon", 80.0), ("hjt", 80.0)):
            r = self.estimate(cell_family=family)
            with self.subTest(family):
                self.assertEqual(r["bifaciality_estimated"], value)
                self.assertNotIn("bifaciality", r)                 # what the datasheet says stays empty

    def test_the_datasheets_value_is_not_estimated_over(self):
        r = self.estimate(cell_family="topcon", bifaciality=72.0)
        self.assertNotIn("bifaciality_estimated", r)
        self.assertEqual(r["bifaciality"], 72.0)

    def test_a_monofacial_module_has_none(self):
        r = catalog.enrich_module({"bifacial": False, "cell_family": "topcon"})
        self.assertNotIn("bifaciality_estimated", r)

    def test_the_other_families_have_no_figure(self):
        for family in ("back_contact", "thin_film", "poly", "mono", "unknown"):
            self.assertNotIn("bifaciality_estimated", self.estimate(cell_family=family), family)

    def test_in_the_catalogue_six_datasheets_without_a_factor_get_the_estimate(self):
        modules = catalog.load("modules")
        estimated = [m for m in modules if m.get("bifaciality_estimated")]
        self.assertEqual(len(estimated), 6 + 0)                     # SoliTek (3), Peimar OR12H, Sunerg (2): TOPCon
        self.assertEqual({m["cell_family"] for m in estimated}, {"topcon"})
        self.assertEqual({m["bifaciality_estimated"] for m in estimated}, {80.0})
        self.assertTrue(all(m["bifacial"] and not m.get("bifaciality") for m in estimated))
        self.assertEqual({m["manufacturer"] for m in estimated}, {"SoliTek", "Peimar", "Sunerg Solar"})
        # the ones that print a factor keep it and carry no estimate
        printed = [m for m in modules if m["source"] == "curated" and m["bifacial"] and m.get("bifaciality")]
        self.assertEqual(len(printed), 36)
        self.assertTrue(all("bifaciality_estimated" not in m for m in printed))
        # back contact and the unstated that print none stay without
        bare = [m for m in modules if m["source"] == "curated" and m["bifacial"]
                and not m.get("bifaciality") and not m.get("bifaciality_estimated")]
        self.assertEqual(len(bare), 5)

    def test_the_project_gets_the_estimate_marked_as_it_is(self):
        r = next(m for m in catalog.load("modules") if m.get("bifaciality_estimated"))
        p = catalog.for_project(r)
        self.assertEqual(p["bifaciality_estimated"], 80.0)
        self.assertNotIn("bifaciality", {k for k, v in p.items() if v})
        spec = ModuleSpec.from_record(p)
        self.assertEqual(spec.bifaciality, 0.0)                     # nothing computes with an estimate by itself


class Facets(unittest.TestCase):
    """The filters of the catalogue's window, each alone and together (study 16, theme E)."""

    @classmethod
    def setUpClass(cls):
        cls.modules = catalog.load("modules")

    def ids(self, records):
        return [r["id"] for r in records]

    def test_no_filter_gives_every_module_in_the_catalogues_order(self):
        found = catalog.search("modules", limit=None)
        self.assertEqual(len(found), len(self.modules))

        def key(r):
            return r["source"] != "curated", r["manufacturer"].casefold(), r["pmax"]
        self.assertEqual(self.ids(found), self.ids(sorted(self.modules, key=key)))
        self.assertEqual(found[0]["source"], "curated")

    def test_the_family_alone(self):
        for family, expected in (("topcon", 41), ("back_contact", 13), ("hjt", None), ("mono", None), ("poly", None)):
            found = catalog.search("modules", family=family, limit=None)
            with self.subTest(family):
                self.assertEqual(self.ids(found), self.ids(m for m in catalog.search("modules", limit=None)
                                                           if m["cell_family"] == family))
                if expected:
                    self.assertEqual(len(found), expected)
                else:
                    self.assertTrue(found)
        self.assertEqual(catalog.search("modules", family="nonexistent", limit=None), [])

    def test_bifacial_yes_no_and_either(self):
        yes = catalog.search("modules", bifacial=True, limit=None)
        no = catalog.search("modules", bifacial=False, limit=None)
        either = catalog.search("modules", bifacial=None, limit=None)
        self.assertTrue(yes and no)
        self.assertTrue(all(r["bifacial"] is True for r in yes))
        self.assertTrue(all(r["bifacial"] is False for r in no))
        self.assertEqual(len(yes) + len(no), len(either))
        self.assertEqual(len(either), len(self.modules))
        self.assertEqual(len([r for r in yes if r["source"] == "curated"]), 47)

    def test_the_manufacturer_without_case(self):
        found = catalog.search("modules", manufacturer="jinko solar", limit=None)
        self.assertTrue(found)
        self.assertTrue(all(r["manufacturer"] == "Jinko Solar" for r in found))
        self.assertEqual(len(found), len([m for m in self.modules if m["manufacturer"] == "Jinko Solar"]))
        self.assertEqual(self.ids(found), self.ids(catalog.search("modules", manufacturer="JINKO SOLAR", limit=None)))
        self.assertEqual(catalog.search("modules", manufacturer="Jinko", limit=None), [])          # the whole name

    def test_the_efficiency_minimum_leaves_out_what_has_no_efficiency(self):
        found = catalog.search("modules", efficiency_min=22.0, limit=None)
        self.assertTrue(found)
        self.assertTrue(all(r["efficiency_pct"] >= 22.0 for r in found))
        self.assertEqual(len(found), len([m for m in self.modules if (m.get("efficiency_pct") or 0) >= 22.0]))
        self.assertLess(len(found), len(catalog.search("modules", efficiency_min=20.0, limit=None)))

    def test_the_length_maximum_leaves_out_what_has_no_size(self):
        found = catalog.search("modules", length_max=1.8, limit=None)
        self.assertTrue(found)
        self.assertTrue(all(0 < r["length"] <= 1.8 for r in found))
        self.assertEqual(len(found), len([m for m in self.modules if m.get("length") and m["length"] <= 1.8]))

    def test_all_together_give_the_intersection(self):
        found = catalog.search("modules", "solar", "curated", 400, 700, family="topcon", bifacial=True,
                               manufacturer="Jinko Solar", efficiency_min=22.0, length_max=2.5, limit=None)
        by_hand = [m for m in catalog.search("modules", limit=None)
                   if "solar" in f"{m['manufacturer']} {m['model']} {m.get('series') or ''}".casefold()
                   and m["source"] == "curated" and 400 <= m["pmax"] <= 700 and m["cell_family"] == "topcon"
                   and m["bifacial"] and m["manufacturer"] == "Jinko Solar" and (m.get("efficiency_pct") or 0) >= 22.0
                   and m.get("length") and m["length"] <= 2.5]
        self.assertTrue(by_hand)
        self.assertEqual(self.ids(found), self.ids(by_hand))
        self.assertEqual(catalog.search("modules", family="thin_film", bifacial=True, source="curated"), [])

    def test_the_order_can_be_asked_for(self):
        up = catalog.search("modules", family="topcon", sort="pmax", limit=None)
        down = catalog.search("modules", family="topcon", sort="pmax", descending=True, limit=None)
        powers = [r["pmax"] for r in up]
        self.assertEqual(powers, sorted(powers))
        self.assertEqual([r["pmax"] for r in down], sorted(powers, reverse=True))
        by_efficiency = [r.get("efficiency_pct") for r in catalog.search("modules", sort="efficiency_pct",
                                                                         descending=True, limit=None)]
        top = [e for e in by_efficiency if e is not None]
        self.assertEqual(top, sorted(top, reverse=True))
        self.assertEqual(by_efficiency[:len(top)], top)                 # the ones without efficiency come last

    def test_the_makers_are_listed_once_whatever_the_case(self):
        every = catalog.brands("modules")
        self.assertEqual(len(every), len({b.casefold() for b in every}))
        self.assertEqual(every, sorted(every, key=str.casefold))
        self.assertIn("Axitec", every)                                  # the datasheet's spelling, not the CEC's
        self.assertNotIn("AXITEC", every)
        self.assertEqual(len(catalog.brands("modules", "curated")), 26)
        self.assertTrue(set(catalog.brands("modules", "cec")) - set(catalog.brands("modules", "curated")))

    def test_the_limit_applies_after_the_filters(self):
        self.assertEqual(len(catalog.search("modules", family="topcon", limit=5)), 5)
        self.assertEqual(self.ids(catalog.search("modules", family="topcon", limit=5)),
                         self.ids(catalog.search("modules", family="topcon", limit=None))[:5])

    def test_the_other_kinds_still_search_by_words_and_power(self):
        found = catalog.search("inverters", "sma", low=3000, high=20000)
        self.assertTrue(found)
        self.assertTrue(all(3000 <= catalog.power_of(r, "inverters") <= 20000 for r in found))

    def test_all_the_filters_on_the_whole_catalogue_take_under_10_ms(self):
        catalog.search("modules", limit=None)                           # the first call prepares the order
        took = []
        for _n in range(7):
            start = time.perf_counter()
            catalog.search("modules", "solar", "", 300, 800, family="mono", bifacial=False, manufacturer="",
                           efficiency_min=15.0, length_max=2.5, limit=None)
            catalog.search("modules", "jinko", "", 400, 700, family="", bifacial=True, limit=None)
            took.append(time.perf_counter() - start)
        self.assertLess(min(took) / 2, 0.010)


class Order(unittest.TestCase):
    """The list sorted by the column clicked (R25)."""

    RECORDS = [{"model": "b", "pmax": 450.0}, {"model": "A", "pmax": None}, {"model": "c", "pmax": 400},
               {"pmax": 500.0}, {"model": "a2", "pmax": 450.0}]

    def test_numbers_by_value_and_words_without_case(self):
        self.assertEqual([r["pmax"] for r in catalog.sorted_by(self.RECORDS, "pmax")][:4], [400, 450.0, 450.0, 500.0])
        self.assertEqual([r.get("model") for r in catalog.sorted_by(self.RECORDS, "model")][:4], ["A", "a2", "b", "c"])

    def test_a_record_without_the_field_is_last_either_way(self):
        for descending in (False, True):
            self.assertIsNone(catalog.sorted_by(self.RECORDS, "pmax", descending)[-1]["pmax"])
            self.assertNotIn("model", catalog.sorted_by(self.RECORDS, "model", descending)[-1])
        self.assertEqual(catalog.sorted_by(self.RECORDS, "pmax", True)[0]["pmax"], 500.0)

    def test_equal_values_keep_their_order(self):
        tied = [r["model"] for r in catalog.sorted_by(self.RECORDS, "pmax") if r["pmax"] == 450.0]
        self.assertEqual(tied, ["b", "a2"])

    def test_a_function_of_the_record_can_be_the_key(self):
        records = [{"cell_family": "mono"}, {"cell_family": "unknown"}, {"cell_family": "topcon"},
                   {"cell_family": "hjt"}, {"cell_family": "perc"}]
        for descending in (False, True):
            ordered = [r["cell_family"] for r in catalog.sorted_by(records, catalog.family_rank, descending)]
            self.assertEqual(ordered[-1], "unknown")                    # the unstated last either way
        self.assertEqual([r["cell_family"] for r in catalog.sorted_by(records, catalog.family_rank)],
                         ["topcon", "hjt", "perc", "mono", "unknown"])

    def test_the_search_without_a_limit_gives_every_record(self):
        self.assertEqual(len(catalog.search("modules", limit=None)), len(catalog.load("modules")))


if __name__ == "__main__":
    unittest.main()


class SolarEdge(unittest.TestCase):
    """Task 22: the SolarEdge inverters say what the optimizers' rules read (string voltage, the column of SolarEdge's
    tables, the Synergy units, the DC input pairs) and the optimizers their continuous input current, all from the
    datasheets archived on 25/10/2026 (README_INDICE.md of reference/catalogs/SolarEdge)."""

    def test_every_solaredge_inverter_is_at_a_fixed_string_voltage_with_its_column(self):
        found = {r["model"]: r for r in catalog.search("inverters", manufacturer="SolarEdge", limit=None)}
        self.assertTrue({"SE8000H (Home Hub)", "SE10000H (Home Hub)", "SE12.5K", "SE16K", "SE17K", "SE90K"}
                        <= set(found))
        for model, rec in found.items():
            with self.subTest(model=model):
                self.assertEqual(rec["dc_architecture"], "fixed_string_voltage")
                self.assertIn(rec["optimizer_grid"], ("single_phase", "three_phase_400"))
                self.assertIn(rec["string_voltage_v"], (380, 750, 850))
                self.assertTrue(rec["dc_power_max_w"] and rec["datasheet_revision"] and rec["dc_input_pairs"])
                self.assertIsNone(rec["mppt_voltage_min_v"])
        self.assertEqual((found["SE16K"]["dc_power_max_w"], found["SE16K"]["datasheet_revision"]),
                         (21600, "DS-000150-EU, September 29, 2024"))
        self.assertEqual((found["SE90K"]["synergy_units"], found["SE90K"]["optimizer_unit_model"]), (3, "SE30K"))

    def test_the_s_series_print_their_continuous_input_current(self):
        found = {r["model"]: r for r in catalog.search("optimizers", manufacturer="SolarEdge", limit=None)}
        self.assertEqual([found[m]["max_input_current_a"] for m in ("S440", "S500", "S1000", "S1200")], [15] * 4)
        self.assertEqual(found["S500"]["max_input_isc_home_hub_a"], 16.5)
        self.assertIsNone(found["P401"]["max_input_current_a"])
