"""R374/R376: decorative meshes never change physical shadows or annual yield."""

from pathlib import Path
import struct
import tempfile
import unittest

import numpy as np
from pandas.testing import assert_frame_equal

import _setup
from _fixtures import capannone, clear_sky_meteo, inverter_record, write_cache

from meridiana import jobs, model, props
from meridiana.energy import pipeline, system
from meridiana.quick.backend.scene import SceneBackend
from meridiana.quick.backend.scene_assets import catalog, load_model
from meridiana.session import ProjectSession

setUpModule = _setup.keep_global_state


class DecorativeEnergyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.cache = Path(self.directory.name)

    def scene(self, session):
        scene = SceneBackend(session, self.cache / "geometry")
        self.addCleanup(scene.close)
        return scene

    def assert_solids_equal(self, before, after):
        self.assertEqual(len(before), len(after))
        for first, second in zip(before, after, strict=True):
            self.assertEqual(first.name, second.name)
            np.testing.assert_array_equal(first.corners, second.corners)

    def test_assets_do_not_change_shadow_hulls_or_a_nonzero_8760_hour_year(self):
        project = capannone()
        project.subfields[0].ring = [[1, 1], [11, 1], [11, 5], [1, 5]]
        project.subfields[0].params = {"mounting": "coplanar"}
        building = project.buildings[0].id
        project.props = [
            model.Prop(
                "tank", "tank", [5, 0], height=3, width=2, length=2, building=building
            ),
            model.Prop("antenna", "antenna", [10, 0], height=4, building=building),
            model.Prop("car", "compact", [-6, -5], rotation=37),
            model.Prop("person", "adult", [-2, -5]),
        ]
        project.energy["inverters"] = [
            {"record": inverter_record(), "count": 1, "name": ""}
        ]
        project.energy["strings"] = {"auto": True}
        session = ProjectSession(project)
        results, keys, _ = jobs.layout_of(project)
        self.assertGreater(sum(result.count for result in results.values()), 0)
        self.assertLessEqual(sum(result.count for result in results.values()), 12)
        session.layout_done(session.generation, results, keys)
        snapshot = session.snapshot()
        energy_key = session.energy_key()
        solids = system.prop_solids(project)
        self.assertGreater(len(solids), 0)
        hulls = {
            prop.id: props.shadow_solid(prop.kind, prop.rotation, **prop.measures())
            for prop in project.props
        }
        write_cache(clear_sky_meteo(project.site.lat, project.site.lon), self.cache)
        before = pipeline.compute(project, results, self.cache, fetch=False)
        self.assertIsNone(before.error_sim)
        self.assertTrue(before.plant.strings)
        self.assertGreater(before.basis.connected_modules, 0)
        self.assertEqual(len(before.sim.hourly), 8760)
        self.assertGreater(before.sim.energy_kwh, 0)
        self.assertGreater(float(before.sim.hourly["p_ac"].max()), 0)
        self.assertTrue(
            any(
                float(array.get("obstacle_shading") or 0) > 0
                for array in before.sim.arrays
            )
        )
        self.assertEqual(session.snapshot(), snapshot)

        # Read every asset, render the built-in shapes, then entirely different
        # decorative sources. Overrides belong to the view, never to Project.
        for record in catalog():
            load_model(record["key"])
        scene = self.scene(session)
        self.assertEqual(len(scene.decorations), 4)
        scene.decorative_models = False
        scene.rebuild()
        undecorated_vertices = len(scene.triangles[0])
        self.assertEqual(scene.decorations, [])
        scene.decorative_models = True
        scene.asset_overrides = {
            "tank": "utility_box",
            "antenna": "transmission_tower",
            "car": "truck",
            "person": "woman_modular_walking",
        }
        scene.rebuild()
        self.assertEqual(
            {row["key"] for row in scene.decorations},
            set(scene.asset_overrides.values()),
        )
        self.assertLess(len(scene.triangles[0]), undecorated_vertices)
        self.assertEqual(session.snapshot(), snapshot)
        self.assertEqual(session.energy_key(), energy_key)
        self.assertEqual(session.undo.count(), 0)
        self.assert_solids_equal(solids, system.prop_solids(session.project))
        for prop in session.project.props:
            current = props.shadow_solid(prop.kind, prop.rotation, **prop.measures())
            self.assertEqual(len(current), len(hulls[prop.id]))
            for first, second in zip(hulls[prop.id], current, strict=True):
                np.testing.assert_array_equal(first, second)

        after = pipeline.compute(
            session.project, session.good_results(), self.cache, fetch=False
        )
        self.assertIsNone(after.error_sim)
        self.assertEqual(after.sim.energy_kwh, before.sim.energy_kwh)
        self.assertEqual(after.sim.p_stc_kw, before.sim.p_stc_kw)
        self.assertEqual(after.sim.p_ac_kw, before.sim.p_ac_kw)
        self.assertEqual(after.sim.pr, before.sim.pr)
        assert_frame_equal(after.sim.hourly, before.sim.hourly, check_exact=True)
        assert_frame_equal(after.sim.monthly, before.sim.monthly, check_exact=True)
        self.assertEqual(after.sim.arrays, before.sim.arrays)
        self.assertEqual(session.snapshot(), snapshot)
        self.assert_solids_equal(solids, system.prop_solids(session.project))

    def test_200_cars_and_200_people_share_two_geometry_buffers_and_cached_loads(self):
        project = model.Project(name="400 decorative instances")
        for index in range(200):
            project.props.append(
                model.Prop(
                    f"car{index}", "compact", [6 * (index % 20), 8 * (index // 20)]
                )
            )
            project.props.append(
                model.Prop(
                    f"person{index}", "adult", [6 * (index % 20) + 3, 8 * (index // 20)]
                )
            )
        session = ProjectSession(project)
        snapshot = session.snapshot()
        load_model.cache_clear()
        self.addCleanup(load_model.cache_clear)
        scene = self.scene(session)
        first_cache = load_model.cache_info()
        self.assertEqual(first_cache.misses, 2)
        self.assertEqual(first_cache.currsize, 2)
        self.assertEqual(len(scene._asset_geometry), 2)
        geometry = {row["key"]: row["geometry"] for row in scene.decorations}
        self.assertEqual(set(geometry), {"car", "casual_standing"})
        self.assertEqual(len({id(value) for value in geometry.values()}), 2)
        # Index sharing must preserve every original triangle, normal and vertex colour.
        self.assertLess(sum(len(value.vertexData()) for value in geometry.values()),
                        (3124 + 5776) * 3 * 40)
        for key, value in geometry.items():
            vertices = np.frombuffer(bytes(value.vertexData()), '<f4').reshape(-1, 10)
            indices = np.frombuffer(bytes(value.indexData()), '<u4')
            p, n, c = load_model(key)
            np.testing.assert_array_equal(vertices[indices], np.column_stack((p, n, c)))
        for row in scene.decorations:
            self.assertEqual(row["count"], 200)
            data = Path(row["source"].toLocalFile()).read_bytes()
            self.assertEqual(
                struct.unpack("<4sHHIII", data[:20]), (b"QtIR", 1, 0, 80, 20, 200)
            )
            self.assertEqual(len(data), 20 + 200 * 80)
            self.assertEqual(len(set(row["ids"])), 200)
        scene.rebuild()
        self.assertEqual(load_model.cache_info().misses, 2)
        self.assertEqual(len(scene._asset_geometry), 2)
        for row in scene.decorations:
            self.assertIs(row["geometry"], geometry[row["key"]])
        self.assertEqual(session.snapshot(), snapshot)


if __name__ == "__main__":
    unittest.main()
