"""R374/R376: shipped CC0 meshes, full static poses and offline conversion."""

import base64
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[3]


def tool(name):
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        return importlib.import_module(name)
    finally:
        sys.path.pop(0)


class AssetsTest(unittest.TestCase):
    def test_catalog_exists_with_selected_full_meshes(self):
        self.assertTrue((ROOT / "data/models/catalog.json").is_file())
        from meridiana.quick.backend.scene_assets import catalog, load_model

        records = {a["key"]: a for a in catalog()}
        for key, triangles in {
            "roof_antenna": 492,
            "utility_box": 4404,
            "casual_standing": 5776,
            "casual_walking": 5776,
            "transmission_tower": 5743,
        }.items():
            self.assertEqual(records[key]["triangles"], triangles)
            self.assertEqual(len(load_model(key)[0]), triangles * 3)

    def test_all_arrays_are_grounded_unit_normals_immutable_and_cached(self):
        from meridiana.quick.backend.scene_assets import catalog, load_model

        for record in catalog():
            with self.subTest(key=record["key"]):
                shape = load_model(record["key"])
                self.assertIs(shape, load_model(record["key"]))
                p, n, c = shape
                for array in shape:
                    self.assertEqual(array.dtype, np.float32)
                    self.assertFalse(array.flags.writeable)
                    self.assertTrue(np.isfinite(array).all())
                self.assertEqual(p.shape, n.shape)
                self.assertEqual(c.shape, (len(p), 4))
                np.testing.assert_allclose(np.linalg.norm(n, axis=1), 1, atol=2e-5)
                self.assertAlmostEqual(float(p[:, 1].min()), 0, places=5)
                self.assertTrue(((c >= 0) & (c <= 1)).all())
                np.testing.assert_allclose(
                    record["bounds"], [p.min(0), p.max(0)], atol=1e-6
                )

    def test_full_poses_are_different(self):
        from meridiana.quick.backend.scene_assets import catalog, load_model

        stand, walk = load_model("casual_standing")[0], load_model("casual_walking")[0]
        self.assertGreater(float(np.max(np.linalg.norm(stand - walk, axis=1))), 0.15)
        self.assertAlmostEqual(float(stand[:, 1].max()), 1, places=5)
        self.assertLess(float(walk[:, 1].max()), 0.99)
        records = {r["key"]: r for r in catalog()}
        for character, triangles in {
            "casual": 5776,
            "worker": 5240,
            "woman_dress": 6108,
            "woman_modular": 6424,
            "business_man": 6634,
            "hoodie": 6206,
            "man": 1852,
            "woman": 2776,
        }.items():
            with self.subTest(character=character):
                standing = records[character + "_standing"]
                walking = records[character + "_walking"]
                self.assertEqual(standing["triangles"], triangles)
                self.assertEqual(walking["triangles"], triangles)
                self.assertEqual(
                    standing["normalization_height"], walking["normalization_height"]
                )
                self.assertGreater(standing["maximum_displacement_from_unskinned"], 0.5)
                self.assertGreater(walking["maximum_displacement_from_unskinned"], 0.5)
                height = load_model(character + "_walking")[0][:, 1].max()
                # A Standing clip may start seated: sharing that scale enlarges
                # the walking partner. Full standing height must be the reference.
                self.assertGreater(height, 0.85)
                self.assertLess(height, 1.05)

    def test_only_approved_cc0_in_active_catalog_and_provenance_present(self):
        from meridiana.quick.backend.scene_assets import catalog

        records = catalog()
        self.assertEqual(len(records), 34)
        for record in records:
            self.assertEqual(record["license"], "CC0-1.0")
            self.assertEqual(len(record["source_sha256"]), 64)
            self.assertEqual(len(record["sha256"]), 64)
            self.assertTrue(
                (ROOT / "data/models" / record["license_evidence"]).is_file()
            )
            self.assertNotIn(record["author"], ("Chase W.", "Poly by Google"))
        inactive = {r["key"] for r in records if not r["active"]}
        self.assertEqual(
            inactive, {"street_lamp_01", "bicycle_drummyfish"}      # R374: the Innerscene bicycle is active
        )

    def test_unknown_model_rejected(self):
        from meridiana.quick.backend.scene_assets import load_model

        with self.assertRaises(KeyError):
            load_model("../../private")

    def test_obj_bake_roundtrip_preserves_triangles_and_colours(self):
        converter = tool("models_bake")
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            obj = folder / "plane.obj"
            obj.write_text("v 0 0 0\nv 2 0 0\nv 2 2 0\nv 0 2 0\nf 1 2 3 4\n")
            shape = converter.load(obj)[:3]
            normalized, height = converter.normalize(shape)
            self.assertEqual(height, 2)
            self.assertEqual(len(normalized[0]), 6)
            np.testing.assert_allclose(normalized[0].min(0), [-0.5, 0, 0])
            np.testing.assert_allclose(normalized[0].max(0), [0.5, 1, 0])
            target = folder / "mesh.npz"
            converter.save_mesh(target, normalized)
            with np.load(target, allow_pickle=False) as saved:
                for name, expected in zip(
                    ("positions", "normals", "colours"), normalized, strict=True
                ):
                    np.testing.assert_array_equal(saved[name], expected)
            with self.assertRaises(FileExistsError):
                converter.save_mesh(target, normalized)

    def test_skinned_pose_uses_inverse_transpose_normals(self):
        gltf, pose = tool("models_gltf"), tool("models_pose")
        arrays = [
            np.array([[0, 0, 0], [0, 0, 1], [1, -1, 0]], "<f4"),
            np.tile(np.array([1, 1, 0], "<f4") / np.sqrt(2), (3, 1)).astype("<f4"),
            np.zeros((3, 4), "<u2"),
            np.tile(np.array([1, 0, 0, 0], "<f4"), (3, 1)),
            np.eye(4, dtype="<f4").reshape(1, 16),
            np.array([[0], [1]], "<f4"),
            np.array([[1, 1, 1], [3, 1, 1]], "<f4"),
        ]
        views, accessors, blob = [], [], b""
        for index, array in enumerate(arrays):
            views.append(dict(buffer=0, byteOffset=len(blob), byteLength=array.nbytes))
            blob += array.tobytes()
            accessors.append(
                dict(
                    bufferView=index,
                    componentType=5123 if index == 2 else 5126,
                    count=len(array),
                    type={1: "SCALAR", 3: "VEC3", 4: "VEC4", 16: "MAT4"}[
                        array.shape[1]
                    ],
                )
            )
        document = dict(
            asset=dict(version="2.0"),
            scene=0,
            scenes=[dict(nodes=[0, 1])],
            nodes=[dict(mesh=0, skin=0), {}],
            meshes=[
                dict(
                    primitives=[
                        dict(
                            attributes=dict(
                                POSITION=0, NORMAL=1, JOINTS_0=2, WEIGHTS_0=3
                            )
                        )
                    ]
                )
            ],
            skins=[dict(joints=[1], inverseBindMatrices=4)],
            animations=[
                dict(
                    name="Scale",
                    samplers=[dict(input=5, output=6)],
                    channels=[dict(sampler=0, target=dict(node=1, path="scale"))],
                )
            ],
            buffers=[
                dict(
                    byteLength=len(blob),
                    uri="data:application/octet-stream;base64,"
                    + base64.b64encode(blob).decode(),
                )
            ],
            bufferViews=views,
            accessors=accessors,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "skin.gltf"
            path.write_text(json.dumps(document))
            shape, weight_error = pose.bake(gltf.Gltf(path), "Scale", 0.5)
            self.assertEqual(weight_error, 0)
            np.testing.assert_allclose(shape[0], [[0, 0, 0], [0, 0, 1], [2, -1, 0]])
            np.testing.assert_allclose(
                shape[1],
                np.tile([1 / np.sqrt(5), 2 / np.sqrt(5), 0], (3, 1)),
                atol=1e-6,
            )

    def test_obj_cannot_read_materials_outside_asset_folder(self):
        gltf = tool("models_gltf")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "untrusted.obj"
            path.write_text(
                "mtllib ../private.mtl\nv 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"
            )
            with self.assertRaises(gltf.Unsupported):
                gltf.read_obj(path)

    def test_bake_refuses_manifest_without_explicit_cc0_license(self):
        converter = tool("models_bake")
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            manifest = folder / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "sources": [
                            {"license": "CC-BY-3.0", "files": [], "entry": "model.obj"}
                        ]
                    }
                )
            )
            with self.assertRaisesRegex(ValueError, "CC0"):
                converter.bake_catalog(manifest, folder, folder / "out")


if __name__ == "__main__":
    unittest.main()
