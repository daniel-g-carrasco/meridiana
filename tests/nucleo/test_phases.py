"""The six phases described once in the core (task 17b, step 1; design document 2.1 and 3.3): numbered 1-6 in
order, each with its groups of commands, its inspector, its areas of the checks and its three questions; the
commands exist in shortcuts.py unless a later task brings them; the deliverables of the Report phase with their
state. No Qt."""

import unittest

import _setup  # noqa: F401

from meridiana import assistant, checks, phases, shortcuts


class ThePhases(unittest.TestCase):
    def test_six_phases_numbered_in_order_with_their_titles(self):
        ps = phases.phases()
        self.assertEqual([p.number for p in ps], [1, 2, 3, 4, 5, 6])
        self.assertEqual([p.id for p in ps], ["model", "plant", "production", "consumption", "economics", "report"])
        self.assertEqual([p.label for p in ps][:2], ["1 Modelling", "2 Plant"])
        self.assertEqual(phases.by_number(6).id, "report")
        self.assertEqual(phases.by_id("consumption").number, 4)
        self.assertEqual(phases.index_of("production"), 2)
        with self.assertRaises(KeyError):
            phases.by_id("checks")

    def test_the_groups_are_those_of_the_design_without_the_sun_and_the_background(self):
        groups = {p.id: [g.title for g in p.groups] for p in phases.phases()}
        self.assertEqual(groups["model"], ["Edit", "Draw", "Obstacles", "Precision"])         # R277
        self.assertEqual(groups["plant"], ["Panels", "Inverter", "Storage", "Strings"])
        self.assertEqual(groups["production"], ["Computation", "Comparison"])
        self.assertEqual(groups["consumption"], ["Data"])
        self.assertEqual(groups["economics"], ["Computation", "Comparison"])
        self.assertEqual(groups["report"], ["Comparison", "Export"])
        for p in phases.phases():
            commands = [t.command for t in p.tools()]
            self.assertEqual(len(commands), len(set(commands)), p.id)
            for g in p.groups:
                self.assertNotIn(g.title, ("Sun", "Background"))            # they stay in the views (C5)
                minimum = {("plant", "storage"): 1, ("economics", "compute"): 1, ("model", "obstacles"): 1}.get(
                    (p.id, g.id), 2)                # the obstacles come with the 3D objects (study 22, question 10)
                # the Panels of the Plant hold six: the layout of before and «On a canopy» (R277, R281)
                most = 6 if (p.id, g.id) == ("plant", "modules") else 5
                self.assertTrue(minimum <= len([t for t in g.tools if not t.planned]) <= most, (p.id, g.id))
        for pid in ("production", "economics", "report"):
            self.assertIn("new_variant", [t.command for t in phases.by_id(pid).tools()])
        self.assertNotIn("refill", [t.command for t in phases.by_id("model").tools()])
        self.assertIn("strings_clear", [t.command for t in phases.by_id("plant").tools()])

    def test_every_command_cited_exists_unless_a_later_task_brings_it(self):
        known = {c.id for c in shortcuts.commands()}
        for p in phases.phases():
            for t in p.tools(planned=True):
                with self.subTest(p.id, command=t.command):
                    if t.planned:
                        # a task or a request brings it; once its command exists the bar shows it by itself
                        # (R277: «Su pensilina» with the canopy's task), and `planned` may go
                        self.assertRegex(t.planned, r"^(1[67][a-g]|relazione|R\d+|oggetti-3d)$")
                    else:
                        self.assertIn(t.command, known)
        model, plant = phases.by_id("model"), phases.by_id("plant")
        modules = [t.command for g in plant.groups if g.id == "modules" for t in g.tools]
        self.assertEqual(modules, ["tool_subfield", "tool_row", "layout_east_west", "canopy_layout", "fill", "empty"])
        self.assertEqual([t.command for t in plant.tools(planned=True) if t.planned], [])   # «On a canopy» is there (R281)
        self.assertEqual([t.command for t in model.tools(planned=True) if t.planned], [])    # R269: «3D object»
        edit = [t.command for g in model.groups if g.id == "edit" for t in g.tools]
        self.assertEqual(edit, ["tool_select", "tool_move", "tool_rotate"])
        precision = [t.command for g in model.groups if g.id == "precision" for t in g.tools]
        self.assertEqual(precision, ["tool_measure", "square", "rectangle"])

    def test_one_button_full_of_accent_at_most_per_phase_and_one_line_labels(self):
        for p in phases.phases():
            with self.subTest(p.id):
                self.assertLessEqual(sum(t.primary for t in p.tools(planned=True)), 1)
                for t in p.tools(planned=True):
                    self.assertNotIn("\n", t.label)
                    self.assertLess(len(t.label), 16, t.label)
        self.assertEqual([t.command for t in phases.by_id("model").tools() if t.primary], [])     # R277: drawing
        self.assertEqual([t.command for t in phases.by_id("plant").tools() if t.primary], ["fill"])
        self.assertEqual([t.command for t in phases.by_id("production").tools() if t.primary], ["compute"])

    def test_every_phase_has_an_inspector_an_area_of_checks_and_three_questions(self):
        areas = checks.area_names()
        for p in phases.phases():
            with self.subTest(p.id):
                self.assertIn(p.inspector, phases.INSPECTORS)
                self.assertTrue(p.areas)
                for a in p.areas:
                    self.assertIn(a, areas)
                self.assertEqual(len(p.questions), 3)
        self.assertEqual([p.inspector for p in phases.phases()],
                         ["properties", "plant", "results", "results", "results", "deliverables"])   # C10
        self.assertEqual(assistant.questions("model"), list(phases.by_id("model").questions))
        self.assertEqual(assistant.questions("nowhere"), list(phases.by_id("economics").questions))
        self.assertEqual(assistant.TABS, tuple(phases.ids()))

    def test_the_module_layout_is_called_posa_in_italian(self):
        from meridiana import i18n
        before = i18n._translation
        self.addCleanup(lambda: setattr(i18n, "_translation", before))
        i18n.setup("it")
        model, plant = phases.by_id("model"), phases.by_id("plant")
        self.assertEqual(model.title, "Modellazione")                                   # R277, decision 1
        self.assertEqual([g.title for g in plant.groups][:3], ["Pannelli", "Inverter", "Accumulo"])
        self.assertEqual(checks.area_names()["layout"], "Posa")
        self.assertEqual(plant.questions[0], "Che ne pensi di questa posa?")
        self.assertEqual(i18n._("Orientation"), "Disposizione")
        self.assertEqual(i18n._("Restore the default layout"), "Ripristina la disposizione predefinita")

    def test_r277_no_command_of_the_bars_is_lost_moving_the_layout_to_the_plant(self):
        """Every command of the bars of before (HEAD 5b80772, written here as it was) is still on a bar, the
        layout's in the Plant before the inverters; the Modelling has the model alone."""
        before = {
            "model": ["tool_select", "tool_move", "tool_rotate", "tool_building", "building_template", "carport",
                      "tool_pitch", "tool_exclusion", "tool_subfield", "tool_row", "layout_east_west", "fill",
                      "empty", "tool_measure", "square", "rectangle"],
            "plant": ["inverter_catalog", "inverter_auto", "battery_catalog", "strings_auto", "strings_complete",
                      "strings_manual", "strings_clear"],
            "production": ["compute", "fetch_pvgis", "new_variant", "compare_variants"],
            "consumption": ["consumption_base", "import_curve"],
            "economics": ["compute", "new_variant", "compare_variants"],
            "report": ["new_variant", "compare_variants", "export_report", "export_ifc", "export_csv",
                       "save_revision", "copy_notes"]}
        now = {p.id: [t.command for t in p.tools()] for p in phases.phases()}
        lost = {c for cs in before.values() for c in cs} - {c for cs in now.values() for c in cs}
        self.assertEqual(lost, set())
        added = ["tool_ridge", "canopy_layout", "object_3d"]     # R275, R281 and R269, new on the bars
        self.assertEqual(sorted([c for cs in before.values() for c in cs] + added),
                         sorted(c for cs in now.values() for c in cs))
        layout = ["tool_subfield", "tool_row", "layout_east_west", "fill", "empty"]
        model = [c for c in before["model"] if c not in layout and c != "tool_exclusion"]
        model.insert(model.index("tool_pitch") + 1, "tool_ridge")
        model.insert(model.index("tool_ridge") + 1, "tool_exclusion")     # in the Obstacles group
        model.insert(model.index("tool_exclusion") + 1, "object_3d")      # R269, beside it
        self.assertEqual(now["model"], model)
        self.assertEqual(now["plant"], layout[:3] + ["canopy_layout"] + layout[3:] + before["plant"])
        for pid in ("production", "consumption", "economics", "report"):
            self.assertEqual(now[pid], before[pid])

    def test_r277_a_tool_of_the_plan_works_in_the_phase_whose_bar_has_it(self):
        self.assertEqual(phases.home("tool_subfield", "model"), "plant")
        self.assertEqual(phases.home("tool_row", "production"), "plant")
        self.assertEqual(phases.home("layout_east_west", "model"), "plant")
        self.assertEqual(phases.home("tool_building", "plant"), "model")
        self.assertEqual(phases.home("tool_pitch", "report"), "model")
        self.assertEqual(phases.home("tool_move", "plant"), "model")
        for tool in ("tool_select", "tool_measure"):                # shared by the two phases of the plan
            self.assertEqual(phases.home(tool, "plant"), "plant")
            self.assertEqual(phases.home(tool, "model"), "model")
            self.assertEqual(phases.home(tool, "economics"), "model")
        self.assertEqual(phases.home("unknown", "plant"), "model")

    def test_next_and_previous_go_round(self):
        self.assertEqual(phases.next("model"), "plant")
        self.assertEqual(phases.next("report"), "model")
        self.assertEqual(phases.previous("model"), "report")
        self.assertEqual(phases.previous("production"), "plant")

    def test_the_keys_of_the_phases(self):
        b = shortcuts.bindings({})
        self.assertEqual(b["next_phase"], ["Ctrl+Tab", "Ctrl+PgDown"])
        self.assertEqual(b["previous_phase"], ["Ctrl+Shift+Backtab", "Ctrl+PgUp"])
        self.assertEqual(b["compute"], ["F5"])
        # the phases by their numbers, Ctrl+1 to Ctrl+6 (Daniel, 24/10/2026, past C8)
        for n, pid in enumerate(("model", "plant", "production", "consumption", "economics", "report"), 1):
            self.assertEqual(b[f"phase_{pid}"], [f"Ctrl+{n}"])
        self.assertEqual(b["panel_properties"], ["Ctrl+P"])

    def test_the_checks_lead_to_a_phase_by_its_id(self):
        import inspect
        source = inspect.getsource(checks)
        self.assertNotIn('("tab", 1)', source)
        for pid in ("production", "consumption", "economics"):
            self.assertIn(f'("phase", "{pid}")', source)


class TheDeliverables(unittest.TestCase):
    def test_the_report_is_unavailable_then_to_make_then_done_then_stale(self):
        d = {x.id: x for x in phases.deliverables(False, {}, "k1")}
        self.assertEqual((d["report"].state, d["report"].command), ("unavailable", "export_report"))
        self.assertEqual(phases.deliverables(True, {}, "k1")[0].state, "todo")
        made = {"report": ("Prova.pdf", "23/10/2026 18:00", "k1")}
        self.assertEqual(phases.deliverables(True, made, "k1")[0].state, "done")
        self.assertIn("Prova.pdf", phases.deliverables(True, made, "k1")[0].note)
        stale = phases.deliverables(True, made, "k2")[0]
        self.assertEqual(stale.state, "stale")
        self.assertIn("18:00", stale.note)

    def test_the_hourly_series_goes_as_the_report_does(self):
        d = {x.id: x for x in phases.deliverables(False, {}, "k1")}
        self.assertEqual((d["csv"].state, d["csv"].command), ("unavailable", "export_csv"))
        self.assertEqual(phases.deliverables(True, {}, "k1")[1].state, "todo")
        made = {"csv": ("Prova - registro dei calcoli.csv", "25/10/2026 10:00", "k1")}
        self.assertEqual([x.state for x in phases.deliverables(True, made, "k1")[:2]], ["todo", "done"])
        self.assertEqual(phases.deliverables(True, made, "k2")[1].state, "stale")

    def test_the_ifc_model_needs_no_year_and_is_to_make_then_done_then_stale(self):
        d = {x.id: x for x in phases.deliverables(False, {}, "k1")}
        self.assertEqual((d["ifc"].state, d["ifc"].command), ("todo", "export_ifc"))
        made = {"ifc": ("Prova.ifc", "25/10/2026 10:00", "k1")}
        d = {x.id: x for x in phases.deliverables(False, made, "k1")}
        self.assertEqual(d["ifc"].state, "done")
        self.assertIn("Prova.ifc", d["ifc"].note)
        d = {x.id: x for x in phases.deliverables(False, made, "k2")}
        self.assertEqual(d["ifc"].state, "stale")

    def test_the_other_deliverables_name_the_task_that_brings_them(self):
        others = [x for x in phases.deliverables(True, {}, "k") if x.id not in ("report", "csv", "ifc")]
        self.assertEqual([x.id for x in others], ["dxf", "strings"])
        for x in others:
            self.assertEqual((x.state, x.command), ("planned", ""))
            self.assertIn("task", x.note)
        self.assertEqual(set(phases.state_names()), {"done", "stale", "todo", "unavailable", "planned"})


if __name__ == "__main__":
    unittest.main()
