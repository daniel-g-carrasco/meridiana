"""One wall at the edge of a flat roof made the parapet of the whole body. A parapet is a wall all round the outline
and casts its shadow there (model.obstacle_prisms): a partition wall of 4.56 m covering 3 % of a flat roof's outline
gave that roof a parapet of 4.56 m all round, a stair railing over 9 % one of 8.2 m. Now the parapet of a flat body
is the greatest height its parapet walls reach over at least half of the outline; a wall taller than that, or one
standing alone, stays an obstacle of its own.

The sample `tests/data/ifc/parapetto-parziale.ifc` (made by hand, no data of any real model): a flat roof of 12 x 8 m
at 6 m with a parapet 1.1 m tall on three sides and a wall 2 m long and 4 m tall at the edge of the fourth; a second
flat roof of 10 x 6 m, far from it, with only a low wall 2 m long and 0.6 m tall at its edge."""

import unittest
from pathlib import Path

from shapely.geometry import Polygon

import _setup  # noqa: F401

from meridiana.app.exchange import ifc_import, ifc_read
from meridiana.core.model import model

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "ifc" / "parapetto-parziale.ifc"


class PartialParapet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.found = ifc_read.read(str(SAMPLE))
        cls.plan = ifc_import.plan(cls.found, model.Project(), "origin", None, name="t", source_name="t.ifc")

    def body(self, area):
        """The index of the body whose outline has `area` m2, and its exclusions."""
        i = next(i for i, b in enumerate(self.plan.buildings) if abs(Polygon(b.footprint).area - area) < 0.5)
        return i, self.plan.buildings[i], [e for e, host in self.plan.exclusions if host == i]

    def test_the_reader_takes_every_wall_for_a_parapet(self):
        kinds = sorted((o["name"], o["kind"]) for o in self.found["obstacles"])
        self.assertEqual(kinds, [("MURETTO", "parapet"), ("MURO_ALTO", "parapet"), ("PARAPETTO_NORD", "parapet"),
                                 ("PARAPETTO_OVEST", "parapet"), ("PARAPETTO_SUD", "parapet")])

    def test_the_tall_wall_is_an_obstacle_and_the_low_walls_the_parapet(self):
        _i, b, mine = self.body(96.0)
        self.assertAlmostEqual(b.parapet, 1.1, places=2)                   # before: 4.0 all round
        self.assertEqual([(e.kind, round(e.height, 2)) for e in mine], [("other", 4.0)])
        wall = Polygon(mine[0].ring)
        x0, y0, x1, y1 = wall.bounds
        self.assertAlmostEqual(x1 - x0, 0.2, places=3)
        self.assertAlmostEqual(y1 - y0, 2.0, places=3)
        self.assertLess(wall.distance(Polygon(b.footprint).exterior), 0.01)

    def test_a_short_wall_alone_is_no_parapet(self):
        _i, b, mine = self.body(60.0)
        self.assertEqual(b.parapet, 0.0)                                    # before: 0.6 all round
        self.assertEqual([(e.kind, round(e.height, 2)) for e in mine], [("other", 0.6)])
        self.assertEqual(len(self.plan.exclusions), 2)


if __name__ == "__main__":
    unittest.main()
