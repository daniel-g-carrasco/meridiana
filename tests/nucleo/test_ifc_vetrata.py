"""The mullions of a sloping curtain wall were walls (r32-montanti). A shed's glazing made as an IfcCurtainWall, not as an
IfcRoof: its plates were no roof, and each mullion lying on the slope became an obstacle from the roof to its top (a
5 cm mullion of 2.8 m, a wall of 4 m in plan and in the shadows). Now the sloping plates of a curtain wall are roof
glazing, as the plates of an IfcRoof: a pitch of the building, whose solid casts the shed's shadow, and the mullions
lie in its plane. An upright curtain wall on a roof, a chimney, stay obstacles.

The sample `tests/data/ifc/vetrata-inclinata.ifc` (made by hand, no data of any real model): a flat roof of 20 x 10 m
at 6 m, a curtain wall of one plate sloping 35 degrees (4 x 3 m in plan) with two mullions on it, an upright curtain
wall 2 m tall with one mullion, a chimney 1.5 m tall."""

import math
import unittest
from pathlib import Path

import numpy as np

import _setup  # noqa: F401

from meridiana.app.exchange import ifc_import, ifc_read
from meridiana.core.model import model

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "ifc" / "vetrata-inclinata.ifc"


def tilt(normal) -> float:
    return math.degrees(math.acos(min(1.0, abs(float(normal[2])))))


class Sample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.found = ifc_read.read(str(SAMPLE))

    def test_the_sloping_glazing_is_a_pitch_of_the_roof(self):
        pitches = [p for b in self.found["buildings"] for p in b["pitches"]]
        glass = [p for p in pitches if abs(tilt(p["normal"]) - 35.0) < 0.5]
        self.assertEqual(len(glass), 1, [round(tilt(p["normal"]), 1) for p in pitches])
        self.assertAlmostEqual(glass[0]["area"], 12.0, delta=0.1)
        self.assertEqual(self.found["counts"].get("glazing"), 1)

    def test_its_mullions_are_not_obstacles_and_the_upright_ones_and_the_chimney_are(self):
        names = sorted(o["name"] for o in self.found["obstacles"])
        self.assertEqual(names, ["CAMINO", "MONTANTE_VERTICALE"])      # before: two MONTANTE_INCLINATO, 2.14 m
        upright = next(o for o in self.found["obstacles"] if o["name"] == "MONTANTE_VERTICALE")
        self.assertAlmostEqual(upright["z1"] - upright["z0"], 2.0, places=2)

    def test_the_import_makes_no_wall_on_the_slope(self):
        project = model.Project()
        plan = ifc_import.plan(self.found, project, "origin", None, name="t", source_name="t.ifc")
        heights = sorted(round(e.height, 2) for e, _host in plan.exclusions)
        self.assertEqual(heights, [1.5, 2.0])
        tilts = sorted(round(p.tilt) for b in plan.buildings for p in b.pitches())
        self.assertIn(35, tilts)


class FacadeWindow(unittest.TestCase):
    """A window in the facade of a higher body whose roof stops 0.6 m behind that facade, above a lower roof in front
    (`tests/data/ifc/finestra-facciata.ifc`, made by hand): it was an obstacle of the lower roof, a wall from that roof
    to the window's top (on one model, three such windows stood as walls of 5.6 m). The band of the facade is measured
    from the outline of the higher body, its roof and the walls under its edge, not from its roof alone. A chimney and
    a machine 1 m in front of the wall stay obstacles (r32-montanti)."""

    def test_the_window_is_the_facade_and_what_stands_on_the_low_roof_stays(self):
        found = ifc_read.read(str(SAMPLE.with_name("finestra-facciata.ifc")))
        names = sorted(o["name"] for o in found["obstacles"])
        self.assertEqual(names, ["CAMINO", "UNITA_ESTERNA"])         # before: also MONTANTE_FINESTRA, 6 to 7.5 m
        self.assertGreaterEqual(found["counts"].get("facade", 0), 1)


class Leaning(unittest.TestCase):
    """Which plates of a curtain wall are roof glazing: sloping, not flat, not upright, above the ground."""

    class Structure:
        def building_of(self, _eid):
            return None

        def ground(self, _bid):
            return 0.0, ""

    class Plate:
        def __init__(self, eid):
            self.eid = eid

        def id(self):
            return self.eid

    def leaning(self, quad, z=6.0) -> bool:
        face = np.array(quad, float) + [0.0, 0.0, z]
        return bool(ifc_read._leaning([self.Plate(1)], {1: [face]}, self.Structure()))

    def test_sloping_upright_flat_and_low(self):
        slope = [(0, 0, 0), (4, 0, 0), (4, 3, 2.1), (0, 3, 2.1)]
        self.assertTrue(self.leaning(slope))
        self.assertFalse(self.leaning([(0, 0, 0), (4, 0, 0), (4, 0, 2), (0, 0, 2)]))    # a facade
        self.assertFalse(self.leaning([(0, 0, 0), (4, 0, 0), (4, 3, 0), (0, 3, 0)]))    # flat: not a slope
        self.assertFalse(self.leaning(slope, z=0.5))             # a canopy at the ground is no roof


if __name__ == "__main__":
    unittest.main()
