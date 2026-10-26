"""The checks of a project: what CEI 0-21:2026 asks of the connection at each size, the layout's notes,
and the list ordered from what fails to what passed."""

import unittest

import _setup  # noqa: F401

from meridiana import checks, model


def levels(items, needle):
    return [i.level for i in items if needle in i.source]


class Connection(unittest.TestCase):
    """The clauses of CEI 0-21:2026-07 the checks name, verified on the archive (B-norme-citazioni.md, sections 2.1
    and 3): 6 kW single phase, 8.3 p. 65 (the DSO may raise it to 10 kW); 11,08 kW, the inverter's own interface
    protection, 8.2.2.2 p. 62, 8.2.2.3 p. 63 and 8.6.2 p. 96; 20 kW, the backup of the interface device, 8.2.2.4
    p. 63-64; 100 kW, low or medium voltage, 6.3 Tab. 5 p. 33."""

    def test_a_small_single_phase_system(self):
        items = checks.connection(4.6, 1, True)
        self.assertEqual(levels(items, "8.3"), ["ok"])
        self.assertEqual(levels(items, "8.6.2"), ["ok"])           # the inverter's own protection will do
        self.assertEqual(levels(items, "8.2.2.4"), [])

    def test_single_phase_above_six_kilowatts_fails(self):
        self.assertEqual(levels(checks.connection(8.0, 1, True), "8.3"), ["fail"])

    def test_a_business_system_needs_a_relay_and_a_backup(self):
        items = checks.connection(50.0, 3, True)
        self.assertEqual(levels(items, "8.6.2"), ["info"])
        self.assertEqual(levels(items, "8.2.2.4"), ["info"])
        self.assertEqual(levels(items, "8.3"), [])
        self.assertEqual(levels(items, "6.3"), [])

    def test_above_a_hundred_kilowatts_medium_voltage_may_come(self):
        self.assertEqual(levels(checks.connection(150.0, 3, True), "6.3"), ["warn"])

    def test_an_inverter_sized_by_itself_is_said_to_be(self):
        items = checks.connection(10.0, None, False)
        self.assertTrue(any(i.target == ("phase", "production") for i in items))
        self.assertTrue(any(i.level == "info" and "8.3" in i.source for i in items))


class Gather(unittest.TestCase):
    def project(self, mounting="tilted_ballasted"):
        p = model.Project()
        b = model.Building(id="b1", name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]], height=9.5)
        p.buildings.append(b)
        p.subfields.append(model.SubField(id="s1", name="Copertura", ring=[[1, 1], [39, 1], [39, 19], [1, 19]],
                                          building="b1", params={"mounting": mounting}, filled=True))
        p.subfields.append(model.SubField(id="s2", name="Vuoto", ring=[[1, 1], [5, 1], [5, 5], [1, 5]], building="b1"))
        return p

    def test_the_layouts_notes_and_what_is_not_laid(self):
        p = self.project()
        results = {sf.id: p.fill(sf) for sf in p.subfields}
        items = checks.gather(p, results, None)
        self.assertTrue(any(i.level == "warn" and "NTC" in i.source and i.target == ("subfield", "s1") for i in items))
        self.assertTrue(any(i.level == "info" and i.target == ("subfield", "s2") for i in items))
        self.assertEqual([i.level for i in items], sorted((i.level for i in items), key=checks.LEVELS.index))

    def test_the_layout_notes_speak_italian_when_the_checks_show_them(self):
        from meridiana import i18n
        p = self.project()
        result = p.fill(p.subfields[0])
        result.notes.append("no room left inside the margins")
        before = i18n._translation
        self.addCleanup(lambda: setattr(i18n, "_translation", before))
        i18n.setup("it")
        items = checks.gather(p, {"s1": result}, None)
        ballast = next(i for i in items if "NTC" in i.source)
        self.assertIn("La zavorra da sola non è un vincolo su una soletta", ballast.detail)
        self.assertIn("servono ancoraggi o tiranti.", ballast.detail)
        self.assertTrue(any(i.text == "Copertura: non resta spazio dentro i margini" for i in items))

    def test_fixes_lay_the_modules_and_go_back_to_the_suggested_strings(self):
        from meridiana.energy.stringing import Check, StringPlan
        p = self.project()
        results = {sf.id: p.fill(sf) for sf in p.subfields}
        mine = StringPlan(24, [2, 2], [Check("voc", "Open-circuit voltage within the inverter's", False, "1.580 V")])
        better = StringPlan(20, [3, 2], [Check("voc", "Open-circuit voltage within the inverter's", True, "1.320 V")],
                            suggested=True)
        items = checks.gather(p, results, {"strings": {"plan": mine, "suggestion": better}})
        lay = next(i for i in items if i.target == ("subfield", "s2"))
        self.assertEqual(lay.fix, ("action", "fill", "subfield", "s2"))
        bad = next(i for i in items if i.area == "strings")
        self.assertEqual((bad.level, bad.fix), ("fail", ("energy", "strings", None)))
        self.assertIn("20 in series, 3 + 2", bad.fix_label)
        better.checks[0].ok = False                             # nothing better to offer: no fix
        items = checks.gather(p, results, {"strings": {"plan": mine, "suggestion": better}})
        self.assertEqual(next(i for i in items if i.area == "strings").fix, ())

    def test_too_much_shade_proposes_keeping_out_of_the_shadows(self):
        from types import SimpleNamespace
        p = self.project()
        results = {sf.id: p.fill(sf) for sf in p.subfields}
        sim = SimpleNamespace(arrays=[{"key": "s1.0", "name": "Copertura", "obstacle_shading": 0.06}], notes=[],
                              p_stc_kw=50.0)
        shade = next(i for i in checks.gather(p, results, {"sim": sim}) if i.area == "shade")
        self.assertEqual(shade.fix, ("edit", "subfield", "s1", {"params.shade_free": True}))
        self.assertIn("21/12", shade.fix_label)
        self.assertIn(f"instead of {results['s1'].count}", shade.fix_label)
        p.subfields[0].params["shade_free"] = True                     # already out of them: nothing more to offer
        shade = next(i for i in checks.gather(p, results, {"sim": sim}) if i.area == "shade")
        self.assertEqual(shade.fix, ())

    def test_the_shade_fix_states_clock_times_its_module_cost_and_the_three_alternatives(self):
        from types import SimpleNamespace
        p = self.project()
        p.sun_window.update(start=10.5, end=14.0)
        sim = SimpleNamespace(arrays=[{"key": "s1.0", "name": "Copertura", "obstacle_shading": 0.033}], notes=[],
                              p_stc_kw=50.0)
        results = {"s1": SimpleNamespace(count=188)}
        shade = next(i for i in checks.gather(p, results, {"sim": sim, "shade_free_counts": {"s1": 130}})
                     if i.area == "shade")
        self.assertIn("10:30", shade.fix_label)
        self.assertIn("14:00", shade.fix_label)
        self.assertIn("130 modules instead of 188, 31% fewer, for 3.3% obstacle shade", shade.fix_label)
        self.assertIn("Moving the sub-field", shade.detail)
        self.assertIn("wider clearance", shade.detail)
        self.assertIn("only the modules next to the obstacles", shade.detail)
        self.assertIn("does not keep more modules", shade.detail)
        expensive = next(i for i in checks.gather(p, results, {"sim": sim, "shade_free_counts": {"s1": 10}})
                         if i.area == "shade")
        self.assertIn("more modules than the shade costs", expensive.fix_label)
        self.assertTrue(expensive.fix_label.startswith("Compare"))

    def test_obstacle_shade_is_weighted_over_all_the_arrays_of_the_sub_field(self):
        from types import SimpleNamespace
        p = self.project()
        sim = SimpleNamespace(arrays=[
            {"key": "s1.0", "name": "Copertura est", "obstacle_shading": 0.08, "p_stc_kw": 30.0},
            {"key": "s1.1", "name": "Copertura ovest", "obstacle_shading": 0.0, "p_stc_kw": 20.0}],
            notes=[], p_stc_kw=50.0)
        results = {"s1": SimpleNamespace(count=188)}
        shaded = [i for i in checks.gather(p, results, {"sim": sim, "shade_free_counts": {"s1": 130}})
                  if i.area == "shade"]
        self.assertEqual(len(shaded), 1)
        self.assertEqual(shaded[0].target, ("subfield", "s1"))
        self.assertIn("Copertura: the obstacles take 4.8% of the sub-field's annual irradiance after far shading",
                      shaded[0].text)
        self.assertIn("for 4.8% obstacle shade", shaded[0].fix_label)

    def test_the_count_out_of_the_shadows_comes_from_the_energy_job(self):
        from types import SimpleNamespace
        from unittest import mock
        p = self.project()
        results = {sf.id: p.fill(sf) for sf in p.subfields}
        sim = SimpleNamespace(arrays=[{"key": "s1.0", "name": "Copertura", "obstacle_shading": 0.06}], notes=[],
                              p_stc_kw=50.0)
        with mock.patch.object(checks, "count_out_of_shadows", side_effect=AssertionError("a layout in the window")):
            items = checks.gather(p, results, {"sim": sim, "shade_free_counts": {"s1": 7}})
        shade = next(i for i in items if i.area == "shade")
        self.assertIn(f"7 modules instead of {results['s1'].count}", shade.fix_label)

    def test_the_count_out_of_the_shadows_is_laid_out_once_per_scene(self):
        """The same sub-field, the same obstacles: the count is kept by its layout key, so a year computed again
        for the losses or the money lays nothing out; an obstacle that grows lays it out again (task 18c, step 5)."""
        from unittest import mock
        p = self.project()
        p.exclusions.append(model.ExclusionItem(id="e1", ring=[[18, 9], [20, 9], [20, 11], [18, 11]], kind="chimney",
                                                building="b1", height=2.5))
        sf = p.subfields[0]
        with _counts_cleared(), mock.patch.object(model.Project, "fill", wraps=p.fill) as fill:
            first = checks.count_out_of_shadows(p, sf)
            self.assertEqual(fill.call_count, 1)
            self.assertEqual(checks.count_out_of_shadows(p, sf), first)
            self.assertEqual(fill.call_count, 1)
            self.assertEqual(first, p.fill(_shade_free(sf), shade=_shadows()).count)
            self.assertFalse(sf.layout_params().shade_free)             # the sub-field itself is left as it is
            fill.reset_mock()
            p.exclusions[0].height = 6.0
            self.assertEqual(checks.count_out_of_shadows(p, sf), p.fill(_shade_free(sf), shade=_shadows()).count)
            self.assertEqual(fill.call_count, 2)                        # the count, and the check's own layout
            p.name = "Another name"
            checks.count_out_of_shadows(p, sf)
            self.assertEqual(fill.call_count, 2)                        # a name moves no shadow


def _shade_free(sf):
    import copy
    alt = copy.deepcopy(sf)
    alt.params["shade_free"] = True
    return alt


def _shadows():
    from meridiana.energy import system
    return system.shadow_exclusions


def _counts_cleared():
    from unittest import mock
    return mock.patch.dict(checks._COUNTS, {}, clear=True)

    def test_the_connection_follows_the_voltage_level(self):
        items = checks.connection(400.0, 3, True, "MT", True)
        self.assertEqual([i.level for i in items], ["info"])
        self.assertIn("CEI 0-16", items[0].text)
        self.assertIn("Tab. 4", items[0].source)
        self.assertEqual(items[0].target, ("site",))

    def test_a_layout_that_failed_is_to_fix(self):
        p = self.project("tilted_anchored")
        items = checks.gather(p, {"s1": ValueError("the area encloses less than 1 m2")}, None)
        self.assertEqual(items[0].level, "fail")
        self.assertIn("1 m2", items[0].text)

    def with_energy(self):
        """The sample project with a year computed: a plan that fails, too much shade, modules in no string, an
        inverter sized by itself, a clipping note (task 17e: every kind of item the window shows)."""
        from types import SimpleNamespace

        from meridiana.energy.stringing import Check, StringPlan
        p = self.project()
        results = {sf.id: p.fill(sf) for sf in p.subfields}
        plan = StringPlan(24, [2, 2], [Check("uoc", "Uoc max within the maximum DC voltage", False, "1.580 V of 1.500 V"),
                                       Check("imp0", "input 1: operating current within the input's maximum", True,
                                             "26.0 A of 25.0 A", "warn")])
        sim = SimpleNamespace(arrays=[{"key": "s1.0", "name": "Copertura", "obstacle_shading": 0.06}],
                              notes=["The inverter clips 3.2% of the energy: check the DC/AC ratio."], p_stc_kw=50.0)
        wiring = SimpleNamespace(left=[1, 2, 3])
        inverter = SimpleNamespace(phases=1, p_ac_kw=50.0)
        energy = {"sim": sim, "strings": {"plan": plan, "suggestion": None}, "wiring": wiring,
                  "shade_free_counts": {"s1": 7}}
        return p, results, energy, inverter

    def test_every_item_to_fix_or_to_check_says_why_and_what_to_do(self):
        """The detail (study 17, F.6): why, and what to do, also where there is no fix; the text stays one short
        sentence, the problem first."""
        p, results, energy, inverter = self.with_energy()
        items = checks.gather(p, results, energy, inverter, chosen=False)
        levels = {i.level for i in items}
        self.assertEqual(levels & {"fail", "warn"}, {"fail", "warn"})
        for it in items:
            with self.subTest(text=it.text):
                self.assertLessEqual(len(it.text), checks.TEXT_LENGTH)
                if it.level in ("fail", "warn"):
                    self.assertTrue(it.detail.strip(), f"no detail: {it.text}")
                    self.assertNotIn("please", it.detail.lower())
        for it in checks.gather(p, results, None):                   # before the year: the same rule
            self.assertLessEqual(len(it.text), checks.TEXT_LENGTH)
            if it.level in ("fail", "warn"):
                self.assertTrue(it.detail.strip(), f"no detail: {it.text}")
        for kw, phases in ((4.6, 1), (8.0, 1), (12.0, None), (50.0, 3), (150.0, 3)):
            for it in checks.connection(kw, phases, False):
                self.assertLessEqual(len(it.text), checks.TEXT_LENGTH)
                if it.level in ("fail", "warn"):
                    self.assertTrue(it.detail.strip(), f"no detail: {it.text}")

    def test_the_details_of_the_strings_come_from_the_check_key(self):
        self.assertIn("coldest morning", checks.string_detail("uoc"))
        self.assertEqual(checks.string_detail("isc1"), checks.string_detail("isc0"))
        self.assertIn("Fewer strings", checks.string_detail("fuserange2"))
        self.assertEqual(checks.string_detail("selv"), "")
        p, results, energy, inverter = self.with_energy()
        items = checks.gather(p, results, energy, inverter)
        uoc = next(i for i in items if i.area == "strings" and i.level == "fail")
        self.assertIn("Fewer modules in series", uoc.detail)
        ntc = next(i for i in items if i.area == "layout" and i.level == "warn")
        self.assertIn("Ballast alone", ntc.detail)                   # the note of the layout, whole, in the detail
        self.assertIn("anchored mounting", ntc.detail)
        rule = next(i for i in items if i.area == "rules" and i.text.startswith("N02"))
        self.assertTrue(rule.detail)                                 # a rule's first paragraph

    def test_the_values_still_at_their_default_come_from_the_records(self):
        from meridiana.energy.pedigree import Quantity, Record, Source, Step
        rec = Record("Economics")
        rec.add(Step("price", "Price of the energy bought", "", "", [
            Quantity("p", "price in F1", 0.25, "€/kWh", Source("default", "indicative default"), 3),
            Quantity("q", "yearly kWh", 30000, "kWh", Source("input", "given"), 0)]))
        rec.add(Step("again", "Price of the energy bought", "", "", [
            Quantity("p", "price in F1", 0.25, "€/kWh", Source("default", "indicative default"), 3)]))
        econ = type("Econ", (), {"record": rec})()
        items = checks.defaults_in_use({"econ": econ})
        self.assertEqual(len(items), 1)                              # the same value twice, said once
        self.assertEqual((items[0].level, items[0].area, items[0].target), ("info", "defaults", ("phase", "economics")))
        self.assertIn("price in F1 = 0.250 €/kWh", items[0].text)
        self.assertEqual(items[0].source, "indicative default")
        self.assertTrue(items[0].detail)
        self.assertEqual(checks.defaults_in_use(None), [])
        self.assertEqual(checks.defaults_in_use({"sim": object()}), [])


class ByHand(unittest.TestCase):
    """The rules of the layout become checks for the sub-fields laid by hand (task 16c, step 6): the cases of the
    task, through the whole list (more in test_manual.py)."""

    def test_a_row_dragged_onto_a_skylight_and_one_26_metres_long_under_the_fire_rules(self):
        from meridiana import manual
        from _fixtures import laid
        from _fixtures import tetto_con_lucernario as project
        p = project(fire=True)
        p.subfields[0].filled = True
        auto = laid(p)
        manual.translate(p, "s1", auto.rows[2].id, 0.0, 14.5 - auto.rows[2].y, auto)(p)
        items = checks.gather(p, {"s1": laid(p)}, None)
        self.assertTrue(any(i.level == "warn" and "on the exclusion Skylight 1" in i.text for i in items))
        self.assertTrue(any(i.level == "info" and "rows by hand" in i.text and
                            i.fix == ("action", "relayout", "subfield", "s1") for i in items))
        q = project(fire=True)
        manual.draw(q, "s1", (3.0, 3.0), (29.6, 3.0))(q)           # 23 modules of 1,134 m with 2 cm between
        long = [i for i in checks.gather(q, {"s1": laid(q)}, None) if "group of" in i.text]
        self.assertEqual([i.text for i in long], ["Sud: group of 26.5 m, beyond the 20 m"])
        self.assertEqual((long[0].level, long[0].source), ("warn", checks.FIRE_SOURCE))


class Grouped(unittest.TestCase):
    """The three views of the Checks panel and the «ready for delivery» one, as sections of indices (task 17e)."""

    def items(self):
        from meridiana.checks import Item
        return [Item("fail", "layout", "a", target=("subfield", "s1")),
                Item("warn", "shade", "b", target=("subfield", "s1")),
                Item("warn", "connection", "c", target=("site",)),
                Item("info", "layout", "d", target=("building", "b1")),
                Item("info", "consumption", "e", target=("phase", "consumption")),
                Item("info", "defaults", "f", target=("phase", "economics")),
                Item("ok", "strings", "g", target=("phase", "production")),
                Item("ok", "rules", "h", target=("site",))]

    def test_by_level_in_the_order_of_the_levels_with_what_passed_closed(self):
        groups = checks.grouped(self.items(), "level")
        self.assertEqual([g.key for g in groups], [("level", "fail"), ("level", "warn"), ("level", "info"),
                                                   ("level", "ok")])
        self.assertEqual([g.name for g in groups], ["To fix", "To check", "To know", "Passed"])
        self.assertEqual([g.items for g in groups], [[0], [1, 2], [3, 4, 5], [6, 7]])
        self.assertEqual([g.closed for g in groups], [False, False, False, True])
        self.assertEqual([g.level for g in groups], ["fail", "warn", "info", "ok"])

    def test_by_object_with_the_names_the_worst_object_first(self):
        names = {("subfield", "s1"): "Copertura Sud", ("building", "b1"): "Capannone", ("site", ""): "Sito: Prova"}
        groups = checks.grouped(self.items(), "object", names)
        self.assertEqual([(g.name, g.kind, g.items, g.level) for g in groups],
                         [("Copertura Sud", "subfield", [0, 1], "fail"),
                          ("Sito: Prova", "site", [2, 4, 5, 6, 7], "warn"),      # the pages and the site together
                          ("Capannone", "building", [3], "info")])
        self.assertEqual(groups[0].key, ("object", "subfield", "s1"))
        unnamed = checks.grouped(self.items(), "object")
        self.assertEqual([g.name for g in unnamed], ["s1", "Site", "b1"])

    def test_by_area_as_the_list_comes(self):
        groups = checks.grouped(self.items(), "area")
        self.assertEqual([g.key[1] for g in groups], ["layout", "shade", "connection", "consumption", "defaults",
                                                      "strings", "rules"])
        self.assertEqual(groups[0].items, [0, 3])
        self.assertEqual(groups[0].name, "Layout")

    def test_ready_for_delivery_gathers_what_to_look_at_before_the_report(self):
        groups = checks.grouped(self.items(), "delivery")
        self.assertEqual([(g.key[1], g.items) for g in groups],
                         [("fail", [0]), ("warn", [1, 2]), ("defaults", [5]), ("estimates", [4])])
        self.assertEqual([g.name for g in groups], ["To fix", "To check", "Values still at their default",
                                                    "Estimates in use"])
        with self.assertRaises(ValueError):
            checks.grouped(self.items(), "colour")

    def test_the_phase_of_an_item(self):
        from meridiana.checks import Item
        items = self.items()
        self.assertEqual([checks.phase_of(i) for i in items],
                         ["model", "model", "model", "model", "consumption", "economics", "production", "model"])
        self.assertEqual(checks.phase_of(Item("info", "import", "x")), None)
        self.assertEqual(checks.phase_of(Item("info", "connection", "x")), "production")
        self.assertEqual(checks.in_phase(items + [Item("info", "import", "x")], "consumption"), [4, 8])
        self.assertEqual(checks.in_phase(items, "model"), [0, 1, 2, 3, 7])
        # the areas a phase declares (phases.py) are kept there too: the Plant's strings and connection, the
        # shading in the Production, the rules in the Report
        self.assertEqual(checks.in_phase(items, "plant"), [2, 6])
        self.assertEqual(checks.in_phase(items, "production"), [1, 6])
        self.assertEqual(checks.in_phase(items, "report"), [7])
        self.assertEqual(checks.in_phase(items + [Item("info", "import", "x")], "nowhere"), [8])


class Marks(unittest.TestCase):
    """The checks on the views (study 12, C1, C3): a mark per object with its worst level and its count, the tree's
    marks rising to the groups and the site, the items about an object, the filter by level."""

    def items(self):
        from meridiana.checks import Item
        return [Item("warn", "layout", "a", target=("subfield", "s1")),
                Item("fail", "layout", "b", target=("subfield", "s1")),
                Item("info", "layout", "c", target=("subfield", "s2")),
                Item("ok", "strings", "d", target=("subfield", "s2")),
                Item("warn", "connection", "e", target=("site",)),
                Item("info", "production", "f", target=("phase", "production")),
                Item("warn", "layout", "g", target=("exclusion", "e1"))]

    def test_a_mark_per_object_with_its_worst_level_and_count(self):
        from meridiana import checks
        m = checks.marks(self.items())
        self.assertEqual(set(m), {("subfield", "s1"), ("subfield", "s2"), ("exclusion", "e1")})
        self.assertEqual((m[("subfield", "s1")].level, m[("subfield", "s1")].count, m[("subfield", "s1")].items),
                         ("fail", 2, [0, 1]))
        self.assertEqual((m[("subfield", "s2")].level, m[("subfield", "s2")].count), ("info", 1))    # «ok» no mark
        only_bad = checks.marks(self.items(), ("fail", "warn"))
        self.assertNotIn(("subfield", "s2"), only_bad)

    def test_the_tree_marks_rise_to_the_groups_and_the_site(self):
        from meridiana import checks
        t = checks.tree_marks(self.items())
        self.assertEqual((t[("group", "subfield")].level, t[("group", "subfield")].count), ("fail", 3))
        self.assertEqual((t[("group", "exclusion")].level, t[("group", "exclusion")].count), ("warn", 1))
        self.assertEqual((t[("site", "")].level, t[("site", "")].count), ("fail", 6))   # every item shown but «ok»
        self.assertNotIn(("group", "building"), t)
        self.assertEqual(checks.tree_marks([]), {})

    def test_the_items_about_an_object_and_the_filter(self):
        from meridiana import checks
        self.assertEqual(checks.about(self.items(), "subfield", "s1"), [0, 1])
        self.assertEqual(checks.about(self.items(), "building", "b1"), [])
        self.assertEqual(checks.filtered(self.items(), ("fail", "warn")), [0, 1, 4, 6])
        self.assertEqual(checks.worst(["info", "warn", "ok"]), "warn")

    def test_a_mark_of_the_tree_in_words_the_worst_first(self):
        from meridiana import checks
        items = self.items()
        t = checks.tree_marks(items)
        self.assertEqual(checks.mark_text(items, t[("subfield", "s1")]), "1 to fix, 1 to check about this object")
        self.assertEqual(checks.mark_text(items, t[("site", "")], inside=True),
                         "1 to fix, 3 to check, 2 to know in this object and inside")


if __name__ == "__main__":
    unittest.main()
