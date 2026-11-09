"""R417, seguito (r22-modellazione): la potenza obiettivo dal lato scelto, nei sottocampi disegnati come moduli (a filo,
R445) e nelle predefinite di posa (R523).

Daniel, 05/11/2026: «nella disposizione dei moduli ci deve anche essere l'opzione di dire tipo: voglio 45kw di picco.
e vengono disposti in quantità in modo da raggiungere quella potenza»."""
import unittest

import _setup  # noqa: F401

from meridiana import layout, manual, model

MODULE = layout.Module(power_kw=0.475)
MILANO = dict(lat=45.46, lon=9.19)
RECT = [(0, 0), (30, 0), (30, 18), (0, 18)]


def fronts(result, frame_azimuth=None):
    """The front edges (work v) of the rows that have modules, sorted."""
    size = layout.Sizes.of(MODULE, layout.Params(), 30.0)
    frame = layout.row_frame(result.azimuth if frame_azimuth is None else frame_azimuth, size)
    return sorted({round(frame.to_work(r.x, r.y)[1], 3) for r in result.rows if r.places})


class FromTheSideChosen(unittest.TestCase):
    def laid(self, **params):
        return layout.compute(RECT, module=MODULE, params=layout.Params(alignment="aligned", target_kwp=20.0,
                                                                        **params), **MILANO)

    def test_front_is_the_default_without_shadows(self):
        whole = layout.compute(RECT, module=MODULE, params=layout.Params(alignment="aligned"), **MILANO)
        best = self.laid()
        self.assertEqual(best.count, 42)
        self.assertEqual(fronts(best)[0], fronts(whole)[0])

    def test_back_takes_the_rows_from_the_back(self):
        whole = layout.compute(RECT, module=MODULE, params=layout.Params(alignment="aligned"), **MILANO)
        back = self.laid(target_from="back")
        self.assertEqual(back.count, 42)
        self.assertEqual(fronts(back)[-1], fronts(whole)[-1])
        self.assertNotIn(fronts(whole)[0], fronts(back))

    def test_front_ignores_the_shadows(self):
        # a shadow over the front rows: "best" goes away from it, "front" stays on the front row
        shadow = [(1.0, [layout.Exclusion([(-1, -1), (31, -1), (31, 6), (-1, 6)], "other")])]
        whole = layout.compute(RECT, module=MODULE, params=layout.Params(alignment="aligned"), **MILANO)
        best = layout.compute(RECT, module=MODULE, params=layout.Params(alignment="aligned", target_kwp=20.0),
                              shaded=shadow, **MILANO)
        front = layout.compute(RECT, module=MODULE, params=layout.Params(alignment="aligned", target_kwp=20.0,
                                                                         target_from="front"), shaded=shadow, **MILANO)
        self.assertNotEqual(fronts(best)[0], fronts(whole)[0])
        self.assertEqual(fronts(front)[0], fronts(whole)[0])

    def test_an_unknown_start_is_refused(self):
        with self.assertRaises(ValueError):
            self.laid(target_from="middle")
        with self.assertRaises(ValueError):
            model._check_placement({"target_from": "middle"}, "s.params")
        model._check_placement({"target_from": "back"}, "s.params")


class DrawnAsModules(unittest.TestCase):
    """A sub-field drawn with the tool is its modules (R445): the power asked is laid out of its rows, which stay
    whole in the file (the outline does not shrink, a bigger power comes back)."""

    def project(self):
        p = model.Project(name="prova")
        p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[[0, 0], [40, 0], [40, 30], [0, 30]],
                                          height=6.0))
        sf = p.new_subfield("s1", "S", [[2, 2], [32, 2], [32, 20], [2, 20]], "b1")
        sf.filled = True
        p.subfields.append(sf)
        manual.make_flush(p, sf)
        return p, sf

    def test_flush_sub_field_lays_the_power_asked(self):
        p, sf = self.project()
        whole = p.fill(sf).count
        rows_before = [r.as_dict() for r in sf.hand_rows()]
        sf.params["target_kwp"] = 10.0
        r = p.fill(sf)
        want = layout.target_modules(10.0, p.module_of(sf).power_kw)
        self.assertEqual(r.count, want)
        self.assertEqual(r.capacity, whole)
        self.assertEqual([x.as_dict() for x in sf.hand_rows()], rows_before)
        sf.params["target_kwp"] = 0.0
        self.assertEqual(p.fill(sf).count, whole)

    def test_the_key_changes_with_the_power_asked(self):
        p, sf = self.project()
        before = p.layout_key(sf)
        sf.params["target_kwp"] = 10.0
        self.assertNotEqual(p.layout_key(sf), before)

    def test_rows_laid_by_hand_on_an_area_stay_the_designer_s(self):
        p, sf = self.project()
        sf.flush = False
        whole = p.fill(sf).count
        sf.params["target_kwp"] = 10.0
        self.assertEqual(p.fill(sf).count, whole)


class Defaults(unittest.TestCase):
    def test_the_power_asked_is_a_default(self):
        self.assertIn("target_kwp", model.DEFAULT_KEYS)
        self.assertIn("target_from", model.DEFAULT_KEYS)
        p = model.Project(name="prova")
        p.layout_defaults = {"params": {"target_kwp": 15.0, "target_from": "back"}}
        sf = p.new_subfield("s1", "S", [[0, 0], [20, 0], [20, 10], [0, 10]], None)
        self.assertEqual(sf.params["target_kwp"], 15.0)
        self.assertEqual(sf.layout_params().target_from, "back")


if __name__ == "__main__":
    unittest.main()
