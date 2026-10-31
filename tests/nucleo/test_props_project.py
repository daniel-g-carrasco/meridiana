"""R269: the 3D objects of the surroundings as objects of the project: the data and its format, moving them, their
shadows in the calculation, the layout kept off a roof obstacle, the scene and the IFC."""

import json
import unittest

import _setup
import numpy as np

from meridiana import mesh, model, move, props, sun, viewaids
from meridiana.energy import system


def site() -> model.Project:
    p = model.Project()
    p.buildings.append(model.Building(id="b1", name="Shed", footprint=[[0, 0], [20, 0], [20, 10], [0, 10]],
                                      height=6.0))
    return p


class Data(unittest.TestCase):
    def test_a_project_of_format_21_opens_with_no_object_and_saves_as_22(self):
        data = json.loads((_setup.FORMATS / "progetto-v21.meridiana").read_text(encoding="utf-8"))
        self.assertNotIn("props", data)
        p = model.Project.from_json(data)
        self.assertEqual(p.props, [])
        self.assertEqual(model.FORMAT_VERSION, 22)
        self.assertEqual(p.to_json()["props"], [])
        self.assertEqual(model.MIGRATIONS[21]({"a": 1}), {"a": 1, "props": []})

    def test_the_frozen_file_of_22_keeps_its_objects_through_a_save(self):
        p, notice = model.Project.load(_setup.FORMATS / "progetto-v22.meridiana")
        self.assertIsNone(notice)
        self.assertEqual([(x.kind, x.building) for x in p.props], [("broadleaf", None), ("chimney", "b1")])
        self.assertEqual(p.props[0].measures()["height"], 9.0)
        self.assertEqual(p.props[0].measures()["crown_diameter"], 5.0)
        again = model.Project.from_json(json.loads(json.dumps(p.to_json())))
        self.assertEqual(again.props, p.props)

    def test_a_damaged_object_is_refused_with_the_path_of_its_key(self):
        base = site().to_json()
        for prop, said in (({"id": "o1", "kind": "dragon"}, "props[0].kind"),
                           ({"id": "o1", "at": [1.0]}, "props[0].at"),
                           ({"id": "o1", "height": 0}, "props[0].height"),
                           ({"id": "o1", "width": -2.0}, "props[0].width"),
                           ({"id": "o1", "rotation": "north"}, "props[0].rotation")):
            with self.subTest(prop=prop):
                with self.assertRaises(ValueError) as caught:
                    model.Project.from_json({**base, "props": [prop]})
                self.assertIn(said, str(caught.exception))

    def test_measures_default_by_kind_and_a_tree_keeps_its_trunk_below_its_height(self):
        palm = model.Prop(id="o1", kind="palm", height=4.0)          # the default trunk is 6.5 m
        m = palm.measures()
        self.assertEqual(m["height"], 4.0)
        self.assertLess(m["trunk_height"], 4.0)
        self.assertEqual(model.Prop(id="o2", kind="suv").measures()["length"], props.CAR_DEFAULTS["suv"][0])
        hedge = model.Prop(id="o3", kind="hedge", length=7.0, width=1.0, at=[0.0, 0.0])
        xs = [q[0] for q in hedge.footprint()]
        self.assertAlmostEqual(max(xs) - min(xs), 7.0)
        self.assertEqual(len(model.Prop(id="o4", kind="conifer").footprint()), 8)      # a round crown

    def test_labels_count_by_kind_in_the_order_placed(self):
        p = site()
        p.props = [model.Prop(id="o1", kind="conifer"), model.Prop(id="o2", kind="compact"),
                   model.Prop(id="o3", kind="conifer")]
        self.assertEqual([p.prop_label(x) for x in p.props], ["Conifer 1", "Car 1", "Conifer 2"])


class Moving(unittest.TestCase):
    def test_an_object_moves_turns_and_is_copied_and_changes_host(self):
        p = site()
        p.props.append(model.Prop(id="o1", kind="compact", at=[25.0, 5.0]))
        move.translate(p, "prop", "o1", -15.0, 0.0)(p)
        x = p.prop("o1")
        self.assertEqual(x.at, [10.0, 5.0])
        self.assertEqual(x.building, "b1")                  # now on the roof
        self.assertAlmostEqual(p.prop_base(x), 6.0)
        move.rotate(p, "prop", "o1", 10.0, 5.0, 90.0)(p)
        self.assertEqual(x.rotation, 90.0)
        made = move.copy(p, "prop", "o1", 20.0, 0.0)(p)
        self.assertEqual(p.prop(made).at, [30.0, 5.0])
        self.assertIsNone(p.prop(made).building)
        self.assertEqual(p.prop(made).rotation, 90.0)

    def test_a_car_under_a_canopy_stands_on_the_ground(self):
        from meridiana import canopies
        p = model.Project()
        bid = canopies.add(p, canopies.Spec(), (0.0, 0.0))
        b = p.building(bid)
        middle = [sum(q[0] for q in b.footprint) / len(b.footprint), sum(q[1] for q in b.footprint) / len(b.footprint)]
        self.assertIsNone(p.prop_host(middle))
        p.props.append(model.Prop(id="o1", kind="compact", at=[30.0, 30.0]))
        move.translate(p, "prop", "o1", middle[0] - 30.0, middle[1] - 30.0)(p)
        self.assertIsNone(p.prop("o1").building)
        self.assertEqual(p.prop_base(p.prop("o1")), 0.0)

    def test_an_object_on_a_roof_goes_with_its_building(self):
        p = site()
        p.props.append(model.Prop(id="o1", kind="chimney", at=[5.0, 5.0], building="b1"))
        move.rotate(p, "building", "b1", 0.0, 0.0, 90.0)(p)
        x = p.prop("o1")
        self.assertAlmostEqual(x.at[0], -5.0)
        self.assertAlmostEqual(x.at[1], 5.0)
        self.assertEqual(x.rotation, 90.0)
        self.assertEqual(len(move.moving(p, "building", "b1")), 2)


class Shadows(unittest.TestCase):
    def test_a_tree_shades_a_sub_field_beside_it_and_its_name_is_readable(self):
        p = model.Project()
        sf = model.SubField(id="s1", name="Ground", ring=[[0, 6], [20, 6], [20, 16], [0, 16]],
                            params={"mounting": "ground"})
        p.subfields.append(sf)
        window = sun.DesignWindow(**p.sun_window)
        self.assertEqual(system.shadow_exclusions(p, sf, window), [])
        p.props.append(model.Prop(id="o1", kind="broadleaf", at=[10.0, 3.0], height=10.0, width=6.0))
        shade = system.shadow_exclusions(p, sf, window)
        self.assertTrue(shade)
        names = {s.name for s in system.obstacles_of(p, sf)}
        self.assertEqual(names, {"Broadleaf tree 1"})

    def test_people_cast_no_shadow_cars_and_obstacles_do(self):
        p = site()
        p.props = [model.Prop(id="o1", kind="adult", at=[30.0, 0.0]),
                   model.Prop(id="o2", kind="suv", at=[30.0, 5.0]),
                   model.Prop(id="o3", kind="tank", at=[5.0, 5.0], building="b1")]
        names = {s.name for s in system.prop_solids(p)}
        self.assertEqual(names, {"SUV 1", "Tank 1"})
        tank = [s for s in system.prop_solids(p) if s.name == "Tank 1"][0]
        self.assertAlmostEqual(float(tank.corners[:, 2].min()), 6.0)          # on the roof

    def test_a_roof_obstacle_keeps_the_modules_off_and_changes_the_layout_key(self):
        p = site()
        sf = model.SubField(id="s1", name="Roof", ring=[[1, 1], [19, 1], [19, 9], [1, 9]], building="b1",
                            params={"mounting": "coplanar"})
        p.subfields.append(sf)
        before = p.layout_key(sf)
        laid = len(p.fill(sf).modules)
        p.props.append(model.Prop(id="o1", kind="plant", at=[10.0, 5.0], width=3.0, length=2.0, building="b1"))
        self.assertNotEqual(p.layout_key(sf), before)
        self.assertLess(len(p.fill(sf).modules), laid)
        p.props[0].kind = "broadleaf"                       # a tree on a roof does not cut the layout
        self.assertEqual(len(p.fill(sf).modules), laid)


class Scene(unittest.TestCase):
    def test_the_report_scene_holds_the_objects_where_they_stand(self):
        p = site()
        empty = mesh.project_scene(p, {})[0][0].shape[0]
        p.props.append(model.Prop(id="o1", kind="conifer", at=[30.0, 20.0]))
        tri = mesh.project_scene(p, {})[0][0]
        self.assertGreater(tri.shape[0], empty)
        added = tri[empty:]
        self.assertAlmostEqual(float(added[:, 0].mean()), 30.0, delta=0.5)        # Qt x East
        self.assertAlmostEqual(float(np.median(added[:, 2])), -20.0, delta=0.5)   # Qt z South
        self.assertAlmostEqual(float(added[:, 1].max()), props.TREE_DEFAULTS["conifer"][0], places=3)

    def test_the_3d_outline_and_the_status_text_know_the_object(self):
        p = site()
        p.props.append(model.Prop(id="o1", kind="chimney", at=[5.0, 5.0], building="b1"))
        edges = viewaids.outline(p, {}, "prop", "o1")
        self.assertEqual(edges.shape[1:], (2, 3))
        self.assertAlmostEqual(float(edges[:, :, 1].max()), 6.0 + props.OBSTACLE_DEFAULTS["chimney"][2])
        self.assertIn("Chimney 1", viewaids.under_text(p, "prop", "o1", "", 5.0, 5.0))


class Ifc(unittest.TestCase):
    def test_the_objects_go_into_the_ifc_as_proxies_people_left_out(self):
        try:
            import ifcopenshell  # noqa: F401
        except ImportError:
            self.skipTest("ifcopenshell is not installed")
        import tempfile
        from pathlib import Path

        from meridiana import ifc_export
        p = site()
        p.props = [model.Prop(id="o1", kind="broadleaf", at=[30.0, 5.0]),
                   model.Prop(id="o2", kind="adult", at=[32.0, 5.0])]
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "p.ifc"
            ifc_export.export(p, {}, out)
            f = ifcopenshell.open(str(out))
        names = [e.Name for e in f.by_type("IfcBuildingElementProxy")]
        self.assertIn("Broadleaf tree 1", names)
        self.assertNotIn("Person 1", names)


if __name__ == "__main__":
    unittest.main()
