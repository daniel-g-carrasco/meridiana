"""The defaults of the next sub-fields (R523, Daniel 07/11/2026): chosen before drawing, they give the drawn sub-field
its module, mounting, orientation, gaps and pitch; the sub-fields already drawn never change with them; a project
without defaults draws as before, and its file is as before."""
import json
import unittest

from meridiana import config, layout, manual, model, session as session_mod


def project(flat=False, subject=False):
    p = model.Project(name="Prova")
    p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                                      height=8.0, roof=model.Roof(type="flat" if flat else "gable",
                                                                  tilt=0.0 if flat else 15.0)))
    p.buildings[0].fire.subject = subject
    return p


RING = [[4, 2], [30, 2], [30, 9], [4, 9]]


def draw(p, sid="s1", ring=RING, flush=True):
    b = p.buildings[0]
    sf = p.new_subfield(sid, "Tetto", [list(q) for q in ring], b.id, b.pitch_ref(0))
    p.add_subfield(sf)
    if flush:
        manual.make_flush(p, sf)
    return sf


class WithoutDefaults(unittest.TestCase):
    def test_a_sub_field_is_drawn_as_before(self):
        for flat, mounting in ((False, "coplanar"), (True, "tilted_anchored")):
            p = project(flat)
            b = p.buildings[0]
            sf = p.new_subfield("s1", "Tetto", RING, b.id, b.pitch_ref(0))
            self.assertEqual(sf.params, model.new_params(mounting))
            self.assertEqual(sf.module, "generic-450")
        p = project()
        self.assertEqual(p.new_subfield("s1", "Prato", RING, None).params, model.new_params("ground"))

    def test_the_file_is_as_before(self):
        data = project().to_json()
        self.assertNotIn("layout_defaults", data)
        self.assertEqual(data["version"], model.FORMAT_VERSION)


class Defaults(unittest.TestCase):
    def test_the_sub_field_drawn_takes_module_and_layout(self):
        p = project(flat=True)
        p.modules["m1"] = {"manufacturer": "Acme", "model": "600", "length": 2.4, "width": 1.13, "power_kw": .6}
        p.layout_defaults = {"module": "m1", "params": {"mounting": "east_west", "portrait": False, "tilt": 12.0,
                                                        "gap": .05, "pitch_mode": "gcr", "gcr": .6}}
        sf = draw(p, flush=False)
        self.assertEqual(sf.module, "m1")
        self.assertEqual(sf.params["mounting"], "east_west")
        self.assertEqual(sf.params["alignment"], layout.NEW_ALIGNMENT)
        raw = sf.layout_params()
        self.assertEqual((raw.portrait, raw.tilt, raw.gap, raw.pitch_mode, raw.gcr), (False, 12.0, .05, "gcr", .6))

    def test_the_mounting_gives_way_where_it_cannot_stand(self):
        p = project()
        p.layout_defaults = {"params": {"mounting": "coplanar"}}
        self.assertEqual(p.new_subfield("s", "", RING, None).params["mounting"], "ground")
        p.layout_defaults = {"params": {"mounting": "ground"}}
        b = p.buildings[0]
        self.assertEqual(p.new_subfield("s", "", RING, b.id, b.pitch_ref(0)).params["mounting"], "coplanar")
        p.layout_defaults = {"module": "not-there", "params": {"mounting": "nonsense", "inverter": "i1"}}
        sf = p.new_subfield("s", "", RING, b.id, b.pitch_ref(0))
        self.assertEqual((sf.module, sf.params), ("generic-450", model.new_params("coplanar")))

    def test_the_grid_of_the_preview_follows_the_defaults(self):
        def count(p):
            b = p.buildings[0]
            draft = p.new_subfield("_draft", "", RING, b.id, b.pitch_ref(0))     # as plan_tools.grid_values
            return len(layout.modules_of(manual.grid(p, draft), p.module_of(draft), p.fill_params(draft),
                                         p.surface_of(draft)))
        p = project()
        plain = count(p)
        p.layout_defaults = {"params": {"gap": .5}}
        self.assertLess(count(p), plain)
        self.assertEqual(len(draw(p).hand_rows()[0].places), count(p) // len(draw(p, "s2").hand_rows()))

    def test_the_sub_fields_drawn_do_not_change_with_the_defaults(self):
        p = project()
        sf = draw(p)
        before = json.dumps(model._subfield_json(sf), sort_keys=True)
        key = p.layout_key(sf)
        p.layout_defaults = {"params": {"gap": .1, "portrait": False}}
        self.assertEqual(json.dumps(model._subfield_json(p.subfields[0]), sort_keys=True), before)
        self.assertEqual(p.layout_key(p.subfields[0]), key)

    def test_the_fire_bands_come_with_the_first_sub_field_on_a_subject_building(self):
        p = project(subject=True)
        p.layout_defaults = {"fire_bands": True}
        draw(p, flush=False)
        bands = [e for e in p.exclusions if e.kind == "band"]
        self.assertEqual(len(bands), 4)
        draw(p, "s2", flush=False)
        self.assertEqual(len([e for e in p.exclusions if e.kind == "band"]), 4)    # not twice
        q = project(subject=False)
        q.layout_defaults = {"fire_bands": True}
        draw(q, flush=False)
        self.assertEqual(q.exclusions, [])


class FromAndToASubField(unittest.TestCase):
    def test_use_as_defaults_leaves_the_mounting_to_the_surface(self):
        p = project()
        sf = draw(p, flush=False)
        sf.params.update(gap=.04, portrait=False, inverter="i1", target_kwp=20.0)
        sf.module = "generic-550"
        taken = p.defaults_of(sf)
        self.assertEqual(taken, {"module": "generic-550", "params": {"alignment": layout.NEW_ALIGNMENT, "gap": .04,
                                                                       "portrait": False}})
        sf.params["mounting"] = "integrated"
        self.assertEqual(p.defaults_of(sf)["params"]["mounting"], "integrated")

    def test_apply_the_defaults_to_a_sub_field_that_is_its_modules(self):
        p = project()
        sf = draw(p)
        sf.params["inverter"] = "i1"
        sf.removed = [model.SubField.hand_rows(sf)[0].slot_key(0)]
        p.layout_defaults = {"module": "generic-550", "params": {"portrait": False, "gap": .05}}
        manual.apply_defaults(p, "s1")(p)
        self.assertEqual(sf.module, "generic-550")
        self.assertEqual((sf.params["portrait"], sf.params["gap"], sf.params["inverter"]), (False, .05, "i1"))
        self.assertTrue(sf.flush and sf.manual)
        self.assertEqual(sf.removed, [])

    def test_apply_refuses_when_no_module_fits(self):
        p = project()
        sf = draw(p, ring=[[4, 2], [7, 2], [7, 4], [4, 4]])
        p.modules["big"] = {"manufacturer": "Acme", "model": "XL", "length": 9.0, "width": 9.0, "power_kw": 1.0}
        p.layout_defaults = {"module": "big"}
        rows = list(sf.rows)
        with self.assertRaises(ValueError):
            manual.apply_defaults(p, "s1")(p)
        self.assertEqual(sf.rows, rows)

    def test_apply_to_an_automatic_sub_field_keeps_its_own_power(self):
        p = project()
        sf = draw(p, flush=False)
        sf.params.update(target_kwp=30.0, gap=.08)
        p.layout_defaults = {"params": {"pitch_mode": "value", "pitch": 4.0}}
        manual.apply_defaults(p, "s1")(p)
        self.assertEqual(sf.params, {"mounting": "coplanar", "alignment": layout.NEW_ALIGNMENT, "pitch_mode": "value",
                                     "pitch": 4.0, "target_kwp": 30.0})


class InTheFile(unittest.TestCase):
    def test_saved_and_opened(self):
        p = project()
        p.layout_defaults = {"module": "generic-550", "params": {"gap": .03, "window": {"day": 21, "month": 12,
                                                                                         "start": 10.0, "end": 14.0}},
                             "fire_bands": True}
        data = json.loads(json.dumps(p.to_json()))
        unknown = []
        q = model.Project.from_json(data, unknown=unknown)
        self.assertEqual(unknown, [])
        self.assertEqual(q.layout_defaults, p.layout_defaults)
        self.assertEqual(q, p)

    def test_what_is_not_a_default_is_refused_with_its_path(self):
        for bad, where in (({"module": 3}, "module"), ({"fire_bands": "si"}, "fire_bands"),
                           ({"params": {"gap": "x"}}, "gap"), ({"params": []}, "params")):
            with self.subTest(bad=bad):
                data = json.loads(json.dumps(project().to_json()))
                data["layout_defaults"] = bad
                with self.assertRaisesRegex(ValueError, where):
                    model.Project.from_json(data)

    def test_a_change_of_the_defaults_lays_nothing_out(self):
        s = session_mod.ProjectSession(project())
        topics = s.edit("d", lambda p: setattr(p, "layout_defaults", {"params": {"gap": .1}}))
        self.assertEqual(topics, {"project:defaults"})
        self.assertFalse(session_mod.needs_layout(topics))
        s.undo.undo()
        self.assertEqual(s.project.layout_defaults, {})


class Profile(unittest.TestCase):
    def test_a_new_project_starts_from_the_profile(self):
        p = project()
        p.modules["m1"] = {"manufacturer": "Acme", "model": "600", "length": 2.4, "width": 1.13, "power_kw": .6}
        p.layout_defaults = {"module": "m1", "params": {"gap": .03}}
        saved = model.profile_defaults(p)
        self.assertEqual(saved["module_data"], p.modules["m1"])
        cfg = config.Config()
        cfg.layout_defaults = json.loads(json.dumps(saved))
        fresh = model.Project()
        model.start_from_profile(fresh, cfg.layout_defaults)
        self.assertEqual(fresh.layout_defaults, p.layout_defaults)
        self.assertEqual(fresh.modules["m1"], p.modules["m1"])
        model.start_from_profile(empty := model.Project(), {})
        self.assertEqual(empty.layout_defaults, {})
        model.start_from_profile(odd := model.Project(), {"module": "m2", "params": {"edge": 1.0, "nonsense": 2}})
        self.assertEqual(odd.layout_defaults, {"params": {"edge": 1.0}})


if __name__ == "__main__":
    unittest.main()
