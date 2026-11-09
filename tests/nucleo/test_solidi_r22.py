"""Seguiti di r20-solidi (r22-modellazione):
- la quota di base di un corpo si prende nel 3D con le maniglie alla base (come i vertici del tetto, R303);
- la direzione delle schiene d'asino si traccia in pianta con due punti;
- le regole VVF valgono per l'edificio intero quando i corpi sono parti di uno (Building.part_of, R440): il corpo
  prende la soggezione dell'intero, la fascia di 1 m corre sul bordo dell'insieme dei corpi (non sul lato che due
  corpi hanno in comune), i dati per le regole hanno un'attività per edificio."""
import types
import unittest

import _setup  # noqa: F401
from shapely.geometry import Point, Polygon

from meridiana import model, roof_vertices, roofs, rules


def project():
    p = model.Project(name="prova")
    p.buildings.append(model.Building(id="b1", name="Magazzino", footprint=[[0, 0], [20, 0], [20, 10], [0, 10]],
                                      height=8.0, fire=model.Fire(subject=True, activity=70, category="B")))
    p.buildings.append(model.Building(id="b2", name="Corpo", footprint=[[20, 0], [40, 0], [40, 10], [20, 10]],
                                      height=8.0, part_of="b1"))
    return p


class BaseHandle(unittest.TestCase):
    def test_a_body_has_base_handles_and_a_lone_building_on_the_ground_not(self):
        p = project()
        p.buildings.append(model.Building(id="b3", name="Solo", footprint=[[50, 0], [60, 0], [60, 10], [50, 10]],
                                          height=6.0))
        base = [h for h in roof_vertices.handles_of(p, "building", "b2") if h.base]
        self.assertEqual(len(base), 4)
        self.assertTrue(all(h.z == 0.0 for h in base))
        self.assertFalse([h for h in roof_vertices.handles_of(p, "building", "b3") if h.base])

    def test_a_base_handle_dragged_sets_the_base_of_the_body(self):
        p = project()
        p.buildings[1].base = 3.0
        handle = next(h for h in roof_vertices.handles_of(p, "building", "b2") if h.base)
        self.assertEqual(handle.z, 3.0)
        roof_vertices.set_heights(p, "b2", [(handle.corners[0], 5.5)])
        b = p.building("b2")
        self.assertEqual(b.base, 5.5)
        self.assertEqual(b.height, 8.0)             # the heights stay measured from the ground
        with self.assertRaises(ValueError):
            roof_vertices.set_heights(p, "b2", [(handle.corners[0], 9.0)])
        with self.assertRaises(ValueError):
            roof_vertices.weld(p, "b2", handle.corners[0], (0, 0))
        self.assertFalse(roof_vertices.folded(b, handle.corners[0]))

    def test_the_roof_handles_stay_as_they_were(self):
        p = project()
        p.buildings[1].base = 2.0
        roof = [h for h in roof_vertices.handles_of(p, "building", "b2") if not h.base]
        self.assertEqual(roof, roof_vertices.handles(p.building("b2")))


class SaddleDirection(unittest.TestCase):
    def test_two_points_give_the_bearing_of_the_bands(self):
        self.assertEqual(roofs.axis_bearing((0, 0), (0, 10)), 0.0)
        self.assertEqual(roofs.axis_bearing((0, 0), (10, 0)), 90.0)
        self.assertEqual(roofs.axis_bearing((10, 10), (0, 0)), 45.0)        # an axis: the way back is the same
        with self.assertRaises(ValueError):
            roofs.axis_bearing((1, 1), (1.001, 1))

    def test_the_trace_on_the_plan_writes_the_direction(self):
        from meridiana.quick.backend.properties import PropertiesBackend
        from meridiana.quick.backend.properties_part import Inspectors
        from meridiana.session import ProjectSession
        p = project()
        p.buildings[0].roof = model.Roof(type="saddles", saddles=roofs.saddle_spec({"direction": 90.0}))
        session = ProjectSession(p)
        backend = PropertiesBackend(session)
        self.addCleanup(backend.close)
        session.select("building", "b1")
        backend.refresh()
        host = types.SimpleNamespace(session=session, properties=backend)
        Inspectors.points_picked(host, "saddles:b1", [[0.0, 0.0], [10.0, 10.0]])
        self.assertEqual(session.project.building("b1").roof.saddles["direction"], 45.0)
        self.assertEqual(session.undo.count(), 1)


class FireByBuilding(unittest.TestCase):
    def test_a_body_takes_the_fire_rules_of_its_building(self):
        p = project()
        sf = model.SubField(id="s1", name="S", ring=[[22, 2], [38, 2], [38, 8], [22, 8]], building="b2", filled=True)
        p.subfields.append(sf)
        self.assertTrue(p.fill_params(sf).fire_rules)
        self.assertIs(p.fire_of(p.building("b2")), p.building("b1").fire)

    def test_the_band_runs_on_the_edge_of_the_whole_building(self):
        p = project()
        guides = [Polygon(ring) for _bid, ring in p.fire_guides() if len(ring) >= 3]
        inside = [g for g in guides if g.contains(Point(20, 5))]
        self.assertTrue(inside, "no band along the side the two bodies share")
        self.assertTrue(any(g.contains(Point(30, 5)) for g in guides), "the band of the body too")
        self.assertFalse(any(g.contains(Point(39.5, 5)) for g in guides))
        inner = p.fire_inner(p.building("b2"), 1.0)
        self.assertTrue(inner.contains(Point(20.2, 5)))
        self.assertFalse(inner.contains(Point(39.5, 5)))

    def test_the_rules_have_one_activity_per_building(self):
        p = project()
        for i, bid in enumerate(("b1", "b2")):
            p.subfields.append(model.SubField(id=f"s{i}", name="S", building=bid, filled=True,
                                              ring=[[22 - 20 * (1 - i), 2], [38 - 20 * (1 - i), 2],
                                                    [38 - 20 * (1 - i), 8], [22 - 20 * (1 - i), 8]]))
        facts = rules.facts(p, {})
        self.assertTrue(facts.fire)
        self.assertEqual(facts.fire_activities, [("Magazzino", 70, "B")])


if __name__ == "__main__":
    unittest.main()
