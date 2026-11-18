"""R374, R375, R376: the new kinds of 3D object (the vehicles and the fixed objects of the site, family «site»), their
shadows as Daniel chose them on 07/11/2026, the fence along its path, the model drawn per object (`asset`, format 30)
written only when set, and the catalogue of models: every active model reachable from a kind."""
import json
import unittest

import _setup
import numpy as np

from meridiana import model, props


class Kinds(unittest.TestCase):
    def test_every_kind_has_a_name_a_family_and_default_measures(self):
        names = model.prop_names()
        for kind in props.KINDS:
            with self.subTest(kind=kind):
                self.assertIn(kind, names)
                self.assertIn(props.family(kind), ("tree", "obstacle", "person", "car", "site"))
                self.assertGreater(props.measures(kind)["height"], 0)
                self.assertEqual(len(props.footprint(kind, (1.0, 2.0))), 8 if kind in props.ROUND else 4)
                pos, nor, col = props.placed_mesh(kind, (0.0, 0.0))
                self.assertGreater(len(pos), 0)

    def test_the_vehicles_and_the_site_objects_of_the_catalogue(self):
        self.assertEqual(props.CAR_KINDS, ("compact", "suv", "truck", "pickup", "sports_car", "bicycle"))
        self.assertEqual(props.SITE_KINDS, ("silo", "container", "gas_tank", "utility_box", "lamp", "tower", "fence"))
        self.assertEqual(props.measures("container"), {"width": 6.06, "depth": 2.44, "height": 2.59})
        self.assertEqual(props.measures("truck")["length"], 7.5)
        self.assertEqual(props.plan_size("silo"), (3.0, 3.0))


class Shadows(unittest.TestCase):
    """Daniel 07/11/2026: the silo, the container, the tower and the fence shade; the vehicles and the people do not
    (the car and the SUV of R269 keep their shadow: the kWh of the projects of before stay)."""

    def test_who_casts_a_shadow(self):
        for kind in ("silo", "container", "tower", "fence", "compact", "suv", "broadleaf", "chimney"):
            self.assertTrue(props.casts_shadow(kind), kind)
            self.assertTrue(model.Prop(id="o", kind=kind).casts_shadow(), kind)
        for kind in ("truck", "pickup", "sports_car", "bicycle", "lamp", "gas_tank", "utility_box", "adult", "walking"):
            self.assertFalse(props.casts_shadow(kind), kind)
            self.assertFalse(model.Prop(id="o", kind=kind).casts_shadow(), kind)
        self.assertFalse(props.casts_shadow("walkway"))
        self.assertTrue(props.casts_shadow("walkway", railing=True))

    def test_the_solids_follow_the_shape(self):
        silo = props.shadow_solid("silo", width=3.0, depth=3.0, height=8.0)
        self.assertEqual(len(silo), 1)
        self.assertEqual(silo[0].shape, (16, 3))                      # an octagonal prism
        self.assertAlmostEqual(float(np.hypot(silo[0][0, 0], silo[0][0, 1])), 1.5, places=6)
        tower = props.shadow_solid("tower", width=8.0, depth=8.0, height=30.0)[0]
        self.assertEqual(tower.shape, (8, 3))                         # a frustum: the top four corners drawn in
        self.assertAlmostEqual(float(abs(tower[4:, 0]).max()), 1.2)
        self.assertEqual(float(tower[4:, 2].min()), 30.0)
        box = props.shadow_solid("container", width=6.0, depth=2.4, height=2.6)[0]
        self.assertEqual(box.shape, (8, 3))
        self.assertAlmostEqual(float(box[:, 0].max() - box[:, 0].min()), 6.0)

    def test_a_fence_shades_segment_by_segment_not_its_hull(self):
        solids = props.placed_solids("fence", (0.0, 0.0), path=[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0]], height=1.5)
        self.assertEqual(len(solids), 2)
        first = solids[0]
        self.assertAlmostEqual(float(first[:, 1].max() - first[:, 1].min()), 0.1, places=6)     # its thickness
        self.assertAlmostEqual(float(first[:, 0].max()), 10.0, places=6)
        self.assertEqual(float(first[:, 2].max()), 1.5)
        # the hull of the same path would have covered the triangle between the two segments
        self.assertTrue(all(abs(float(s[:, 0].max() - s[:, 0].min())) < 10.2 for s in solids))

    def test_the_procedural_fence_follows_its_path_like_a_hedge(self):
        pos, nor, col = props.placed_mesh("fence", (0.0, 0.0), path=[[0.0, 0.0], [8.0, 0.0]], height=1.5)
        self.assertGreater(len(pos), 0)
        self.assertAlmostEqual(float(pos[:, 1].max()), 1.5, places=5)


class Asset(unittest.TestCase):
    """Format 30: `asset`, the model of the catalogue drawn for the object, written only when set."""

    def test_the_format_number_and_the_empty_migration(self):
        self.assertEqual(model.FORMAT_VERSION, 30)
        self.assertEqual(model.MIGRATIONS[29]({"a": 1}), {"a": 1})

    def test_written_only_when_set_and_kept_through_a_save(self):
        p, _notice = model.Project.load(_setup.FORMATS / "progetto-v29.meridiana")
        p.props.append(model.Prop(id="o1", kind="lamp"))
        p.props.append(model.Prop(id="o2", kind="lamp", asset="street_light"))
        raw = p.to_json()["props"]
        self.assertNotIn("asset", raw[-2])
        self.assertEqual(raw[-1]["asset"], "street_light")
        again = model.Project.from_json(json.loads(json.dumps(p.to_json())))
        self.assertEqual([x.asset for x in again.props][-2:], [None, "street_light"])
        self.assertNotIn("asset", p.props[-2].as_dict())

    def test_a_wrong_asset_is_refused_with_its_path(self):
        p, _notice = model.Project.load(_setup.FORMATS / "progetto-v29.meridiana")
        data = p.to_json()
        data["props"] = [{"id": "o1", "kind": "lamp", "asset": "../x"}]
        with self.assertRaises(ValueError) as caught:
            model.Project.from_json(data)
        self.assertIn("props[0].asset", str(caught.exception))

    def test_the_shading_key_of_a_project_without_assets_is_as_before(self):
        p, _notice = model.Project.load(_setup.FORMATS / "progetto-v29.meridiana")
        p.props.append(model.Prop(id="o1", kind="silo"))
        keys = json.dumps([x.as_dict() for x in p.props if x.casts_shadow()])
        self.assertNotIn("asset", keys)


class Catalogue(unittest.TestCase):
    def test_every_active_model_is_reachable_from_a_kind_and_every_mapped_model_is_active(self):
        from meridiana.quick.backend import models3d, scene_assets
        active = {row["key"] for row in scene_assets.catalog(active_only=True)}
        self.assertEqual(len(active), 32)
        self.assertIn("bicycle_innerscene", active)
        reachable = set(models3d.ASSET_FOR_KIND.values())
        for keys in models3d.ASSETS_FOR_KIND.values():
            reachable |= set(keys)
        self.assertEqual(active - reachable, set())
        self.assertEqual(reachable - active, set())
        for kind in models3d.ASSET_FOR_KIND:
            self.assertIn(kind, props.KINDS)

    def test_the_picker_groups_hold_every_kind_once_but_the_opening(self):
        from meridiana.quick.backend import models3d
        shown = [k for _title, kinds in models3d.GROUPS for k in kinds]
        self.assertEqual(len(shown), len(set(shown)))
        self.assertEqual(set(props.KINDS) - set(shown), {"opening"})
        for group in models3d.groups():
            for entry in group["kinds"]:
                self.assertTrue(entry["preview"].endswith(entry["id"] + ".png"), entry)

    def test_the_choices_of_a_kind_and_the_model_drawn(self):
        from meridiana.quick.backend import models3d
        self.assertEqual([k for k, _n in models3d.choices("lamp")], ["streetlight", "street_light"])
        self.assertEqual(len(models3d.choices("adult")), 8)
        self.assertEqual(models3d.choices("truck"), [])
        self.assertEqual(models3d.asset_for(model.Prop(id="o", kind="adult", asset="hoodie_standing")), "hoodie_standing")
        self.assertEqual(models3d.asset_for(model.Prop(id="o", kind="adult", asset="nothing")), "casual_standing")
        self.assertIsNone(models3d.asset_for(model.Prop(id="o", kind="broadleaf")))


if __name__ == "__main__":
    unittest.main()
