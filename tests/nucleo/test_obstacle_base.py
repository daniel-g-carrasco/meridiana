"""An obstacle's base (format 32): the bottom of an exclusion above the roof or the ground under it, a duct on its
supports or a pipe rack. It is a prism from its base to its top in the 3D view, the selection's outline, the
handles, the assistant's fields and the exports; the layout keeps the modules out of its outline as before. A
project without bases is what it was: the same prisms, the same file, the same keys."""

import json
import tempfile
import unittest
from pathlib import Path

import _setup  # noqa: F401
from _fixtures import capannone_rho

from meridiana.app.assistant import tools
from meridiana.app.exchange import dxf_export
from meridiana.app.view import viewaids
from meridiana.core.geometry import mesh, roof_vertices
from meridiana.core.model import model


def flat_roof(base: float = 0.0, height: float = 4.0, building: str | None = "b1") -> model.Project:
    """A flat roof 9,5 m high, a sub-field on it with tilted rows and a plant of 2 x 2 m in the middle."""
    p = model.Project(name="Prova")
    p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                                      height=9.5))
    p.subfields.append(model.SubField(id="s1", name="Sud", ring=[[1, 1], [39, 1], [39, 19], [1, 19]], building="b1",
                                      params={"tilt": 15.0}, filled=True))
    p.exclusions.append(model.ExclusionItem(id="e1", ring=[[18, 8], [20, 8], [20, 10], [18, 10]], kind="plant",
                                            building=building, height=height, base=base))
    return p


class WithoutBases(unittest.TestCase):
    """A project of before: nothing of it changes."""

    def test_the_prisms_the_file_and_the_shadow_keys_are_those_of_before(self):
        p = capannone_rho()
        prisms = [o for o in p.obstacle_prisms() if o["kind"] != "parapet"]
        self.assertEqual(prisms, [
            {"ring": [(18.0, 8.0), (20.0, 8.0), (20.0, 10.0), (18.0, 10.0)], "z0": 9.5, "z1": 10.0, "kind": "vent",
             "id": "e1", "building": "b1"},
            {"ring": [(30.0, 12.0), (31.0, 12.0), (31.0, 13.0), (30.0, 13.0)], "z0": 9.5, "z1": 11.7,
             "kind": "plant", "id": "e2", "building": "b1"}])
        raw = p.to_json()["exclusions"]
        self.assertEqual([sorted(x) for x in raw], [["building", "clearance", "height", "id", "kind", "ring"]] * 2)
        self.assertEqual(p.shadow_casters()["obstacles"],
                         [[[[18, 8], [20, 8], [20, 10], [18, 10]], "vent", None, "b1"],
                          [[[30, 12], [31, 12], [31, 13], [30, 13]], "plant", 2.2, "b1"]])


class Raised(unittest.TestCase):
    def test_a_raised_obstacle_is_a_prism_from_its_base_to_its_top(self):
        prism = flat_roof(base=3.0, height=4.0).obstacle_prism(flat_roof(base=3.0).exclusions[0])
        self.assertEqual((prism["z0"], prism["z1"]), (12.5, 13.5))
        on_ground = flat_roof(base=1.0, height=3.0, building=None)
        self.assertEqual([(o["z0"], o["z1"]) for o in on_ground.obstacle_prisms() if o["id"] == "e1"], [(1.0, 3.0)])

    def test_a_base_at_or_above_its_top_leaves_no_prism(self):
        for base in (4.0, 5.0):
            with self.subTest(base=base):
                p = flat_roof(base=base, height=4.0)
                self.assertFalse(any(o["id"] == "e1" for o in p.obstacle_prisms()))
                self.assertIsNone(p.obstacle_prism(p.exclusions[0]))

    def test_the_base_is_written_only_when_raised_read_back_and_checked(self):
        p = flat_roof(base=3.0)
        data = json.loads(json.dumps(p.to_json()))
        self.assertEqual(data["exclusions"][0]["base"], 3.0)
        self.assertEqual(model.Project.from_json(data).exclusions[0].base, 3.0)
        self.assertNotIn("base", flat_roof(base=0.0).to_json()["exclusions"][0])
        for wrong in (-1.0, "3", 1e9):
            with self.subTest(base=wrong):
                bad = json.loads(json.dumps(data))
                bad["exclusions"][0]["base"] = wrong
                with self.assertRaisesRegex(ValueError, r"exclusions\[0\]\.base"):
                    model.Project.from_json(bad)

    def test_the_shadows_key_follows_the_base_and_the_layout_does_not(self):
        ground, raised = flat_roof(base=0.0), flat_roof(base=3.0)
        self.assertNotEqual(ground.shadow_casters(), raised.shadow_casters())
        sf_g, sf_r = ground.subfields[0], raised.subfields[0]
        self.assertEqual(ground.layout_key(sf_g), raised.layout_key(sf_r))      # the modules stay out all the same
        self.assertEqual([m.key for m in ground.fill(sf_g).modules], [m.key for m in raised.fill(sf_r).modules])
        sf_g.params["shade_free"] = sf_r.params["shade_free"] = True                # out of the shadows: it counts
        self.assertNotEqual(ground.layout_key(sf_g), raised.layout_key(sf_r))

    def test_the_3d_view_and_the_selection_draw_it_from_its_base(self):
        p = flat_roof(base=3.0, height=4.0)
        owners: list = []
        (pos, _nor, _col), _table, _segs = mesh.project_scene(p, {}, owners=owners)
        at = 0
        for part, oid, n in owners:
            if (part, oid) == ("exclusion", "e1"):
                ys = pos[at * 3:(at + n) * 3, 1]           # Qt's y is the height (mesh.to_qt)
                self.assertAlmostEqual(float(ys.min()), 12.5, places=5)
                self.assertAlmostEqual(float(ys.max()), 13.5, places=5)
                break
            at += n
        else:
            self.fail("the raised obstacle is not in the 3D scene")
        edges = viewaids.outline(p, {}, "exclusion", "e1")
        self.assertAlmostEqual(float(edges[..., 1].min()), 12.5, places=5)

    def test_the_handle_of_its_top_stops_above_its_base(self):
        p = flat_roof(base=3.0, height=4.0)
        roof_vertices.set_obstacle_height(p, "e1", 11.0)          # under the base, 12,5 m
        self.assertAlmostEqual(p.exclusions[0].height, 3.1)
        self.assertIsNotNone(p.obstacle_prism(p.exclusions[0]))
        roof_vertices.set_obstacle_height(p, "e1", 15.0)
        self.assertAlmostEqual(p.exclusions[0].height, 5.5)
        self.assertEqual(p.exclusions[0].base, 3.0)

    def test_the_assistant_reads_and_proposes_it(self):
        p = flat_roof(base=0.0)
        self.assertEqual(tools.fields_of("exclusion")["base"], tools.NUMBER)
        typed = tools.check_edit(p, "exclusion", "e1", {"base": 2.5})
        self.assertEqual(typed, {"base": 2.5})
        tools.apply_edit(p, "exclusion", "e1", typed)
        self.assertEqual(p.exclusions[0].base, 2.5)
        with self.assertRaises(ValueError):
            tools.check_edit(p, "exclusion", "e1", {"base": -1.0})

    def test_the_dxf_says_its_base_and_its_top(self):
        if not dxf_export.available():
            self.skipTest("ezdxf is not installed")
        import ezdxf
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pianta.dxf"
            dxf_export.export(flat_roof(base=3.0, height=4.0), {}, path, parts=("obstacles",))
            texts = [e.dxf.text for e in ezdxf.readfile(str(path)).modelspace().query("TEXT")]
        from meridiana.i18n import number
        base, top = number(3.0, 2), number(4.0, 2)
        self.assertTrue(any(base in t and top in t and t.index(base) < t.index(top) for t in texts), texts)
        self.assertFalse(any(t.endswith(f" h {top} m") for t in texts), texts)      # not as one from the roof

    def test_the_ifc_places_it_at_its_base(self):
        try:
            import ifcopenshell.util.element
            import ifcopenshell.util.placement
        except ImportError:
            self.skipTest("ifcopenshell is not installed")
        from _fixtures import exported
        found = {}
        with tempfile.TemporaryDirectory() as folder:
            for base in (0.0, 3.0):
                path, _summary, _results = exported(flat_roof(base=base, height=4.0), Path(folder), f"b{base}.ifc")
                f = ifcopenshell.open(str(path))
                for el in f.by_type("IfcElement"):
                    pset = ifcopenshell.util.element.get_pset(el, "Meridiana_Ostacolo") or {}
                    if pset.get("Id") == "e1":
                        z = float(ifcopenshell.util.placement.get_local_placement(el.ObjectPlacement)[2, 3])
                        depth = el.Representation.Representations[0].Items[0].Depth
                        found[base] = (z, float(depth))
        (z_ground, depth_ground), (z_raised, depth_raised) = found[0.0], found[3.0]
        unit = depth_ground / 4.0                   # the file's length unit, a metre in it
        self.assertAlmostEqual(depth_raised, 1.0 * unit, places=6)
        self.assertAlmostEqual(z_raised - z_ground, 3.0 * unit, places=6)


if __name__ == "__main__":
    unittest.main()
