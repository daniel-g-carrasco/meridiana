"""The near shading of a raised obstacle (format 32): a prism from its base to its top, the sun passes under it. A
project without bases casts the same shadows to the bit as before the base existed: its shading is compared with the
one cast by the prisms as the code of before made them (`prisms_of_before`, commit 262cfc3a's obstacle_prisms). On
14/11/2026 the digest of every number of that shading was the same on the code of before and after (398ff1c1...)."""

import unittest

import numpy as np

import _setup  # noqa: F401
from _fixtures import capannone_rho

from meridiana.core.energy import nearshade, system
from meridiana.core.model import model


def prisms_of_before(p: model.Project) -> list[dict]:
    """Project.obstacle_prisms as it was before the base (commit 262cfc3a), word for word for the exclusions."""
    out = []
    for e in p.exclusions:
        h = e.obstacle_height()
        if h <= 0 or len(e.ring) < 3:
            continue
        ring = [(float(x), float(y)) for x, y in e.ring]
        b = p.building(e.building)
        zs = model.roof_z(b, ring) if b is not None else [0.0]
        out.append({"ring": ring, "z0": min(zs), "z1": max(zs) + h, "kind": e.kind, "id": e.id,
                    "building": e.building})
    return out + [o for o in p.obstacle_prisms() if o["id"] not in {e.id for e in p.exclusions}]


def shading_parts(p: model.Project, prisms: list | None) -> list:
    """Every number the year takes from the near shading of the project's laid sub-fields."""
    out = []
    for sf in p.subfields:
        r = p.fill(sf)
        [a] = system.arrays_of(p, {sf.id: r})
        sh = nearshade.shading(a.placed, system.obstacles_of(p, sf, prisms), a.tilt, a.azimuth)
        out.append((sh.table, sh.sky, sh.modules, sh.blocks, sh.block_fractions, sh.obstacles, sh.keys))
    return out


def flat_roof(base: float) -> model.Project:
    """A flat roof at 9,5 m, modules flat on it all round a box 2 x 2 m whose top is 4 m above the roof."""
    p = model.Project(name="Prova")
    p.site = capannone_rho().site
    p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                                      height=9.5))
    p.subfields.append(model.SubField(id="s1", name="Sud", ring=[[1, 1], [39, 1], [39, 19], [1, 19]], building="b1",
                                      params={"mounting": "coplanar"}, filled=True))
    p.exclusions.append(model.ExclusionItem(id="e1", ring=[[18, 8], [20, 8], [20, 10], [18, 10]], kind="plant",
                                            building="b1", height=4.0, base=base))
    return p


def shading_of(p: model.Project):
    sf = p.subfields[0]
    [a] = system.arrays_of(p, {sf.id: p.fill(sf)})
    return a, nearshade.shading(a.placed, a.obstacles, a.tilt, a.azimuth)


class WithoutBases(unittest.TestCase):
    def test_the_shadows_of_a_project_without_bases_are_those_of_before_to_the_bit(self):
        p = capannone_rho()
        p.subfields[0].filled = True
        self.assertEqual(p.obstacle_prisms(), prisms_of_before(p))
        now, before = shading_parts(p, None), shading_parts(p, prisms_of_before(p))
        for got, want in zip(now, before, strict=True):
            for x, y in zip(got, want, strict=True):
                if isinstance(x, np.ndarray):
                    self.assertEqual((x.dtype, x.shape, x.tobytes()), (y.dtype, y.shape, y.tobytes()))
                else:
                    self.assertEqual(x, y)
        self.assertGreater(float(now[0][0].sum()), 0.0)          # the fixture's obstacles do cast shadows


class Raised(unittest.TestCase):
    def test_a_raised_obstacle_shades_a_module_by_its_foot_less_than_the_same_one_from_the_roof(self):
        a_ground, ground = shading_of(flat_roof(0.0))
        a_raised, raised = shading_of(flat_roof(3.0))
        self.assertEqual([pm.key for pm in a_ground.placed], [pm.key for pm in a_raised.placed])   # the same modules
        # the module just north of the box, by its foot: the sun from the south passes under the raised one
        near = min(range(len(a_ground.placed)), key=lambda i: np.hypot(a_ground.placed[i].centre[0] - 19.0,
                                                                          a_ground.placed[i].centre[1] - 11.0))
        self.assertLess(float(raised.modules[near].sum()), float(ground.modules[near].sum()))
        self.assertLess(float(raised.table.sum()), float(ground.table.sum()))
        self.assertGreater(float(raised.table.sum()), 0.0)                      # it still casts a shadow
        self.assertGreaterEqual(raised.sky, ground.sky)


if __name__ == "__main__":
    unittest.main()
