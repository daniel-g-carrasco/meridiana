"""Procedural low-poly props: true dimensions, closed outward solids and cheap shadow hulls."""

import unittest

import _setup  # noqa: F401
import numpy as np

from meridiana import props


TREE_CASES = (
    ("broadleaf", {"height": 6.0, "crown_diameter": 4.0, "trunk_height": 1.8}),
    ("broadleaf", {"height": 9.0, "crown_diameter": 5.5, "trunk_height": 2.7}),
    ("conifer", {"height": 8.0, "crown_diameter": 3.5, "trunk_height": 1.0}),
    ("conifer", {"height": 12.0, "crown_diameter": 4.5, "trunk_height": 1.4}),
    ("shrub", {"height": 1.4, "crown_diameter": 1.6, "trunk_height": 0.15}),
    ("shrub", {"height": 0.8, "crown_diameter": 1.1, "trunk_height": 0.1}),
    ("hedge", {"height": 1.8, "crown_diameter": 0.9, "trunk_height": 0.1, "length": 6.0}),
    ("hedge", {"height": 1.1, "crown_diameter": 0.7, "trunk_height": 0.1, "length": 2.5}),
    ("palm", {"height": 9.0, "crown_diameter": 5.0, "trunk_height": 6.5}),
    ("palm", {"height": 6.0, "crown_diameter": 3.8, "trunk_height": 4.2}),
)


class MeshChecks(unittest.TestCase):
    def assert_mesh(self, shape, budget, tolerance=2e-5):
        pos, nor, col = shape
        for array in (pos, nor, col):
            self.assertEqual(array.dtype, np.float32)
            self.assertEqual(array.ndim, 2)
            self.assertEqual(array.shape[1], 3)
            self.assertTrue(np.isfinite(array).all())
        self.assertEqual(len(pos), len(nor))
        self.assertEqual(len(pos), len(col))
        self.assertEqual(len(pos) % 3, 0)
        self.assertGreater(len(pos), 0)
        self.assertLessEqual(len(pos) // 3, budget)
        self.assertTrue(np.all((col >= 0.0) & (col <= 1.0)))
        np.testing.assert_allclose(np.linalg.norm(nor, axis=1), 1.0, rtol=0, atol=2e-6)

        tri = pos.astype(np.float64).reshape(-1, 3, 3)
        cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        self.assertGreater(float(np.linalg.norm(cross, axis=1).min()), 1e-10)
        agreement = np.einsum("ij,ij->i", cross, nor[::3].astype(np.float64))
        self.assertTrue(np.all(agreement > 0.0))
        self.assert_outward_components(tri)
        return pos, nor, col

    def assert_outward_components(self, tri):
        vertices, inverse = np.unique(tri.reshape(-1, 3), axis=0, return_inverse=True)
        faces = inverse.reshape(-1, 3)
        neighbours = [[] for _ in range(len(faces))]
        owners = {}
        for face_index, face in enumerate(faces):
            for a, b in zip(face, np.roll(face, -1), strict=True):
                edge = tuple(sorted((int(a), int(b))))
                if edge in owners:
                    other = owners[edge]
                    neighbours[face_index].append(other)
                    neighbours[other].append(face_index)
                else:
                    owners[edge] = face_index
        unseen = set(range(len(faces)))
        while unseen:
            stack = [unseen.pop()]
            component = []
            while stack:
                current = stack.pop()
                component.append(current)
                for other in neighbours[current]:
                    if other in unseen:
                        unseen.remove(other)
                        stack.append(other)
            part = vertices[faces[component]]
            volume = np.einsum("ij,ij->i", part[:, 0], np.cross(part[:, 1], part[:, 2])).sum() / 6.0
            self.assertGreater(float(volume), 0.0)

    def assert_bounds(self, pos, width, height, depth, tolerance=2e-5):
        np.testing.assert_allclose(pos.min(axis=0), (-width / 2, 0.0, -depth / 2), rtol=0, atol=tolerance)
        np.testing.assert_allclose(pos.max(axis=0), (width / 2, height, depth / 2), rtol=0, atol=tolerance)

    def assert_shadow_inside(self, shadow, pos, tolerance=3e-5):
        self.assertGreater(len(shadow), 0)
        for corners in shadow:
            self.assertEqual(corners.ndim, 2)
            self.assertEqual(corners.shape[1], 3)
            self.assertGreaterEqual(len(corners), 4)
            qt = corners[:, [0, 2, 1]] * (1.0, 1.0, -1.0)
            self.assertTrue(np.all(qt >= pos.min(axis=0) - tolerance))
            self.assertTrue(np.all(qt <= pos.max(axis=0) + tolerance))


class Trees(MeshChecks):
    def test_every_tree_has_the_requested_dimensions_and_a_valid_mesh(self):
        for kind, dimensions in TREE_CASES:
            with self.subTest(kind=kind, dimensions=dimensions):
                shape = props.tree(kind, **dimensions)
                pos, _nor, _col = self.assert_mesh(shape, props.TREE_TRIANGLE_BUDGET)
                self.assert_bounds(pos, dimensions.get("length", dimensions["crown_diameter"]),
                                   dimensions["height"], dimensions["crown_diameter"])

    def test_trees_are_deterministic_and_accept_theme_colours(self):
        first = props.tree("broadleaf", colours={"tree": "#408060", "trunk": (0.3, 0.2, 0.1)})
        second = props.tree("broadleaf", colours={"tree": "#408060", "trunk": (0.3, 0.2, 0.1)})
        for a, b in zip(first, second, strict=True):
            np.testing.assert_array_equal(a, b)
        self.assertTrue(np.any(np.all(np.isclose(first[2], (64 / 255, 128 / 255, 96 / 255)), axis=1)))

    def test_tree_rotation_is_around_the_vertical_qt_axis(self):
        upright = props.tree("hedge", length=6.0, crown_diameter=1.0)[0]
        turned = props.tree("hedge", length=6.0, crown_diameter=1.0, rotation=90.0)[0]
        self.assertAlmostEqual(float(turned[:, 0].max() - turned[:, 0].min()),
                               float(upright[:, 2].max() - upright[:, 2].min()), places=5)
        self.assertAlmostEqual(float(turned[:, 2].max() - turned[:, 2].min()),
                               float(upright[:, 0].max() - upright[:, 0].min()), places=5)
        self.assertAlmostEqual(float(turned[:, 1].max()), float(upright[:, 1].max()), places=6)

    def test_every_tree_shadow_stays_inside_its_decorative_envelope(self):
        for kind, dimensions in TREE_CASES:
            with self.subTest(kind=kind):
                pos = props.tree(kind, **dimensions)[0]
                shadow = props.shadow_solid(kind, **dimensions)
                self.assert_shadow_inside(shadow, pos)

    def test_invalid_tree_dimensions_are_rejected(self):
        for dimensions in ({"height": 0.0}, {"crown_diameter": -1.0}, {"height": 3.0, "trunk_height": 3.0}):
            with self.subTest(dimensions=dimensions), self.assertRaises(ValueError):
                props.tree("broadleaf", **dimensions)


if __name__ == "__main__":
    unittest.main()
