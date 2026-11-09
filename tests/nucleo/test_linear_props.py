"""Linear hedges and walkways: one path drives their outline, mesh, shadows and module exclusions."""

import unittest

import numpy as np

from meridiana import mesh, model, move, props


class LinearProps(unittest.TestCase):
    def test_old_hedges_and_walkways_migrate_to_two_point_paths(self):
        data = model.Project().to_json()
        data["version"] = 24
        data["props"] = [
            {"id": "h", "kind": "hedge", "at": [10, 5], "rotation": 90, "length": 4, "width": 0.8},
            {"id": "w", "kind": "walkway", "at": [2, 3], "length": 3, "width": 0.8},
        ]
        p = model.Project.from_json(data)
        self.assertGreaterEqual(model.FORMAT_VERSION, 25)
        np.testing.assert_allclose(p.props[0].path, [[10, 3], [10, 7]])
        np.testing.assert_allclose(p.props[1].path, [[0.5, 3], [3.5, 3]])
        self.assertTrue(p.props[1].railing)

    def test_a_buffered_polyline_is_one_continuous_footprint(self):
        ring = props.footprint("hedge", [0, 0], width=0.8, path=[[0, 0], [4, 0], [4, 3]])
        from shapely.geometry import Polygon
        shape = Polygon(ring)
        self.assertTrue(shape.is_valid)
        self.assertAlmostEqual(shape.area, 0.8 * 7, delta=0.05)
        self.assertGreater(len(ring), 4)

    def test_path_moves_turns_and_drives_shadows_and_layout(self):
        p = model.Project()
        p.buildings.append(model.Building(id="b", name="Shed", footprint=[[0, 0], [12, 0], [12, 8], [0, 8]], height=5))
        x = model.Prop(id="w", kind="walkway", at=[3, 4], building="b", path=[[1, 4], [5, 4], [5, 6]], railing=True)
        p.props.append(x)
        self.assertEqual(len(p._prop_exclusions("b")), 1)
        self.assertGreater(len(props.placed_solids(x.kind, x.at, path=x.path)[0]), 8)
        move.rotate(p, "prop", "w", 0, 0, 90)(p)
        np.testing.assert_allclose(x.path, [[-4, 1], [-4, 5], [-6, 5]])
        self.assertEqual(len(mesh.prop_triangles(p)), 1)

    def test_path_is_validated(self):
        data = model.Project().to_json()
        data["props"] = [{"id": "h", "kind": "hedge", "path": [[0, 0]]}]
        with self.assertRaisesRegex(ValueError, "props\\[0\\].path"):
            model.Project.from_json(data)

    def test_railing_posts_have_a_shadow_map_visible_section(self):
        ring = props.footprint("walkway", [0, 0], width=0.7, path=[[-2, 2], [3, 2]])
        surface = lambda x, y: 3.0 + (y + 4.0) * np.tan(np.radians(18.0))
        base = mesh.path_triangles(ring, surface, 0.02, (0.5, 0.3, 0.2), False)
        shape = mesh.path_triangles(ring, surface, 0.02, (0.5, 0.3, 0.2), True)
        rails = shape[0][len(base[0]):]
        x, y = ring[0]
        top = surface(x, y) + 0.92
        near = rails[(np.abs(rails[:, 0] - x) < 0.1) & (np.abs(rails[:, 2] + y) < 0.1) &
                     (rails[:, 1] < top - 0.2)]
        self.assertGreaterEqual(float(np.ptp(near[:, 0])), 0.049)
        self.assertGreaterEqual(float(np.ptp(near[:, 2])), 0.049)


if __name__ == "__main__":
    unittest.main()
