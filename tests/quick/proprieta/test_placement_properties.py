"""R417, R418: the placement of the modules in the Properties of a sub-field."""
import unittest

from _fixtures import capannone
from meridiana import jobs, layout, model
from meridiana.session import ProjectSession


class PlacementProperties(unittest.TestCase):
    def setUp(self):
        from meridiana.quick.backend.properties import PropertiesBackend
        self.project = capannone()
        self.session = ProjectSession(self.project)
        self.backend = PropertiesBackend(self.session)
        self.addCleanup(self.backend.close)
        self.sf = self.project.subfields[0]
        self.sf.filled = True
        self.lay()
        self.session.select("subfield", self.sf.id)
        self.backend.refresh()

    def lay(self):
        results, keys, _props = jobs.layout_of(self.session.project)
        self.session.results, self.session.layout_keys = results, keys
        self.backend.refresh()

    def data(self, key):
        field = self.backend.field(key)
        return None if field is None else field.data

    def test_a_saved_sub_field_shows_how_it_was_saved_and_nothing_changes(self):
        self.assertNotIn("alignment", self.sf.params)
        shown = self.data("params.alignment")
        self.assertEqual(shown["value"], layout.LEGACY_ALIGNMENT)
        self.assertEqual([o["value"] for o in shown["options"]], [*layout.ALIGNMENTS, layout.LEGACY_ALIGNMENT])
        self.assertEqual(self.session.undo.count(), 0)

    def test_a_chosen_way_no_longer_offers_the_old_one(self):
        self.sf.params["alignment"] = "aligned"
        self.backend.refresh()
        self.assertEqual([o["value"] for o in self.data("params.alignment")["options"]], list(layout.ALIGNMENTS))

    def test_choosing_a_way_is_one_undoable_edit(self):
        self.assertTrue(self.backend.commit("params.alignment", "staggered"))
        self.assertEqual(self.session.project.subfields[0].params["alignment"], "staggered")
        self.assertEqual(self.session.undo.count(), 1)
        self.backend.undo()
        self.assertNotIn("alignment", self.session.project.subfields[0].params)

    def test_the_power_asked_shows_the_modules_it_comes_to(self):
        self.assertIsNone(self.data("target"))
        power = self.project.module_of(self.sf).power_kw
        self.assertTrue(self.backend.commit("params.target_kwp", str(10 * power)))
        self.lay()
        self.sf = self.session.project.subfields[0]
        self.assertEqual(self.session.results[self.sf.id].count, 10)
        self.assertIn("10", self.data("target")["value"])
        self.assertIn(str(self.session.results[self.sf.id].capacity), self.data("target")["value"])

    def test_too_much_power_says_how_many_are_short(self):
        self.assertTrue(self.backend.commit("params.target_kwp", "90000"))
        self.lay()
        result = self.session.results[self.session.project.subfields[0].id]
        self.assertGreater(result.target_missing, 0)
        self.assertEqual(result.count, result.capacity)
        self.assertIn(str(result.target_missing), self.data("target")["value"])

    def test_a_sub_field_laid_by_hand_keeps_its_rows(self):
        self.sf.manual = True
        self.sf.rows = [r.as_dict() for r in self.session.results[self.sf.id].rows]
        self.lay()
        self.assertFalse(self.data("params.alignment")["enabled"])
        self.assertFalse(self.data("params.target_kwp")["enabled"])

    def test_modules_taken_out_stay_out_of_the_same_places_on_a_new_way(self):
        result = self.session.results[self.sf.id]
        chosen = result.modules[len(result.modules) // 2]
        self.sf.removed = [chosen.key]
        self.lay()
        self.assertTrue(self.backend.commit("params.alignment", "aligned"))
        sf = self.session.project.subfields[0]
        self.assertEqual(len(sf.removed), 1)
        self.lay()
        now = self.session.results[sf.id]
        self.assertNotIn(sf.removed[0], now.keys)
        from shapely.geometry import Point, Polygon
        whole = layout.compute(self.project._ring_on_its_part(sf), self.project.surface_of(sf),
                               self.project.module_of(sf), self.project.fill_params(sf))
        where = next(pm for pm in whole.modules if pm.key == sf.removed[0])
        self.assertTrue(Polygon(where.corners).contains(Point(chosen.centre)))


class TakenOutAcrossRows(unittest.TestCase):
    def test_a_module_taken_out_between_new_rows_goes_to_the_nearest_one(self):
        from meridiana import manual
        p = model.Project(name="prova")
        sf = model.SubField(id="s1", name="S", ring=[[0, 2.6], [16.2, 0], [20.0, 21.2], [0.6, 22.0]],
                            params={"alignment": "aligned", "pitch_mode": "value", "pitch": 4.0}, filled=True)
        p.subfields.append(sf)
        r = p.fill(sf)
        sf.removed = [r.keys[5]]
        r = p.fill(sf)
        after = manual.removed_on_alignment(p, sf, "free", r)
        self.assertEqual(len(after), 1)
        whole = p.fill(model.SubField(id="s2", name="T", ring=sf.ring, params={**sf.params, "alignment": "free"}, filled=True))
        self.assertIn(after[0], whole.keys)


class NewSubFields(unittest.TestCase):
    def test_a_sub_field_drawn_now_stands_aligned(self):
        p = model.new_params("coplanar")
        self.assertEqual(p["alignment"], "aligned")


class PowerAskedR22(PlacementProperties):
    """R417 seguito (r22-modellazione): da dove si prendono le file, la regola detta, il sottocampo a filo."""

    def test_the_rule_is_said_and_the_side_can_be_chosen(self):
        self.assertIsNone(self.data("params.target_from"))
        self.assertTrue(self.backend.commit("params.target_kwp", "10"))
        self.lay()
        shown = self.data("params.target_from")
        self.assertEqual([o["value"] for o in shown["options"]], list(layout.TARGET_FROM))
        self.assertEqual(shown["value"], "best")
        self.assertIn("shadow", self.data("target_rule")["value"])
        self.assertTrue(self.backend.commit("params.target_from", "back"))
        self.lay()
        self.assertEqual(self.session.project.subfields[0].params["target_from"], "back")
        self.assertIn("back", self.data("target_rule")["value"])

    def test_a_sub_field_drawn_as_its_modules_takes_the_power_asked(self):
        from meridiana import manual
        manual.make_flush(self.session.project, self.sf)
        self.lay()
        whole = self.session.results[self.sf.id].count
        self.assertTrue(self.data("params.target_kwp").get("enabled", True))
        self.assertFalse(self.data("params.alignment")["enabled"])
        power = self.project.module_of(self.sf).power_kw
        self.assertTrue(self.backend.commit("params.target_kwp", str(10 * power)))
        self.lay()
        result = self.session.results[self.session.project.subfields[0].id]
        self.assertEqual((result.count, result.capacity), (10, whole))
        self.assertIn("10", self.data("target")["value"])


class DefaultsR22(unittest.TestCase):
    def test_the_defaults_have_the_power_asked(self):
        from meridiana.quick.backend.properties_schema import build_schema
        p = model.Project(name="prova")
        p.layout_defaults = {"params": {"target_kwp": 12.0}}
        keys = [f["id"] for section in build_schema(ProjectSession(p), "defaults", None) for f in section["fields"]]
        self.assertIn("params.target_kwp", keys)
        self.assertIn("params.target_from", keys)


if __name__ == "__main__":
    unittest.main()
