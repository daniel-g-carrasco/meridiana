"""What casts a shadow on a sub-field, on a roof of very many pitches: the top of the walls is asked once for each
building, not once for each pitch (it reads every corner of the roof: on an imported roof of 158 pitches and 60
sub-fields it held the window for a minute at every result)."""
import unittest
from unittest import mock

import _setup  # noqa: F401
from _fixtures import capannone
from meridiana.core.model import model
from meridiana.core.energy import system


def rect(x0, y0, x1, y1):
    return [[float(x0), float(y0)], [float(x1), float(y0)], [float(x1), float(y1)], [float(x0), float(y1)]]


def free_roof(pitches):
    return model.Roof(type='free', joined=False, free_pitches=[
        {"id": f"p{i + 1}", "ring": rect(i, 0.5, i + 1, 10), "eave_side": 0, "eave": 6.0, "tilt": 10.0}
        for i in range(pitches)])


class ManyPitches(unittest.TestCase):
    def project(self, pitches):
        p = capannone()
        first = p.buildings[0]
        first.footprint, first.height, first.roof = rect(0, 0, 40, 20), 6.0, free_roof(pitches)
        p.buildings.append(model.Building(id=p.new_id("b"), name="Corpo 2", footprint=rect(60, 0, 100, 20),
                                          height=6.0, roof=free_roof(pitches)))
        sf = next(sf for sf in p.subfields if sf.building == first.id)
        sf.pitch = 0
        return p, sf

    def test_the_wall_top_is_asked_once_for_each_building(self):
        p, sf = self.project(30)
        with mock.patch.object(model.Building, "wall_top", autospec=True, side_effect=model.Building.wall_top) as top:
            solids = system.obstacles_of(p, sf)
        self.assertEqual(top.call_count, len(p.buildings))
        self.assertTrue(solids)

    def test_the_solids_are_those_of_a_wall_top_asked_every_time(self):
        p, sf = self.project(8)
        b, other = p.buildings[0], p.buildings[1]
        found = system.obstacles_of(p, sf, prisms=[])
        expected = []
        for i, pt in enumerate(b.pitches()):
            if i != 0 and system._stands_up(pt, b):
                expected += system.nearshade.under(pt.corners_3d(), b.wall_top(), "")
        expected += system.nearshade.prism(other.footprint, other.base, other.wall_top(), "")
        for pt in other.pitches():
            if system._stands_up(pt, other):
                expected += system.nearshade.under(pt.corners_3d(), other.wall_top(), "")
        mine = [s for s in found if getattr(s, "name", "").startswith((b.name, other.name))]
        self.assertEqual(len(mine), len(expected))


class KeptKey(unittest.TestCase):
    """Building.geometry_key is kept until what it reads changes: the same string as made anew, at every change."""

    def building(self):
        return model.Building(id="b1", name="Corpo", footprint=rect(0, 0, 40, 20), height=6.0, roof=free_roof(20))

    def test_it_is_made_once_while_nothing_changes(self):
        b = self.building()
        with mock.patch.object(model.Building, "_geometry_key_made", autospec=True,
                               side_effect=model.Building._geometry_key_made) as made:
            keys = {b.geometry_key() for _ in range(5)}
        self.assertEqual(made.call_count, 1)
        self.assertEqual(keys, {b._geometry_key_made()})

    def test_every_change_in_place_is_seen(self):
        b = self.building()
        seen = [b.geometry_key()]

        def changed():
            key = b.geometry_key()
            self.assertEqual(key, b._geometry_key_made())
            self.assertNotIn(key, seen)
            seen.append(key)

        b.roof.free_pitches[3]["tilt"] += 1.0
        changed()
        b.roof.free_pitches[3]["ring"][0][0] += 0.01
        changed()
        b.footprint[1][0] += 0.5
        changed()
        b.height += 1.0
        changed()
        b.parapet += 0.3
        changed()
        b.base += 2.0
        changed()
        b.roof.joined = True
        changed()
        b.roof = model.Roof(type="mono", tilt=5.0)
        changed()

    def test_the_name_is_not_in_it(self):
        b = self.building()
        key = b.geometry_key()
        b.name = "Altro nome"
        self.assertEqual(b.geometry_key(), key)


if __name__ == "__main__":
    unittest.main()
