"""Bake a provenance manifest offline to static, full-resolution vertex meshes.

python tools/models_bake.py --sources build/models-originals --output build/models-baked
Requires numpy and Pillow only. No downloaded file is executed. All input hashes
are checked before decoding. The output directory must not contain a catalogue.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from models_gltf import Gltf, load
from models_pose import bake


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize(shape, reference_height=None, up_axis="Y"):
    """Ground and centre without changing aspect ratio; share scale across poses."""
    p, n, c = (np.asarray(a, dtype=np.float64).copy() for a in shape)
    if up_axis == "Z":
        # Rotation, not a reflection: preserve triangle winding.
        p = p[:, [0, 2, 1]] * [1, 1, -1]
        n = n[:, [0, 2, 1]] * [1, 1, -1]
    elif up_axis != "Y":
        raise ValueError("Unsupported up axis: " + up_axis)
    lo, hi = p.min(0), p.max(0)
    height = float(reference_height or (hi[1] - lo[1]))
    if height <= 0 or not np.isfinite(height):
        raise ValueError("Invalid mesh height")
    p = (p - [(lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2]) / height
    lengths = np.linalg.norm(n, axis=1)
    if np.any(lengths < 1e-10):
        tri = p.reshape(-1, 3, 3)
        face = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        face = np.repeat(face, 3, axis=0)
        n[lengths < 1e-10] = face[lengths < 1e-10]
        lengths = np.linalg.norm(n, axis=1)
        # Degenerate source triangles have no geometric normal.
        n[lengths < 1e-10] = [0, 1, 0]
        lengths = np.linalg.norm(n, axis=1)
    n /= lengths[:, None]
    if c.shape[1] == 3:
        c = np.c_[c, np.ones(len(c))]
    arrays = tuple(
        np.ascontiguousarray(a, dtype=np.float32) for a in (p, n, np.clip(c, 0, 1))
    )
    if not all(np.isfinite(a).all() for a in arrays):
        raise ValueError("Nonfinite mesh")
    return arrays, height


def save_mesh(path, shape):
    """Write numeric arrays only and verify the complete round trip."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, positions=shape[0], normals=shape[1], colours=shape[2])
    with np.load(path, allow_pickle=False) as archive:
        for name, expected in zip(
            ("positions", "normals", "colours"), shape, strict=True
        ):
            if not np.array_equal(archive[name], expected):
                raise ValueError("Bake round trip differs: " + name)


def bake_catalog(manifest, sources, output):
    manifest, sources, output = Path(manifest), Path(sources), Path(output)
    if (output / "catalog.json").exists():
        raise FileExistsError("Choose a new output directory")
    sources = sources.resolve()
    rows = []
    for source in json.loads(manifest.read_text(encoding="utf8"))["sources"]:
        if source.get("license") != "CC0-1.0":
            raise ValueError("Every source must have an explicit CC0-1.0 license")
        for item in source["files"]:
            path = (sources / item["path"]).resolve()
            if sources not in path.parents:
                raise ValueError("Source outside asset root")
            if digest(path) != item["sha256"]:
                raise ValueError("Source checksum mismatch: " + item["path"])
        path = sources / source["entry"]
        variants = source.get("poses", [dict(suffix="", clip=None, seconds=0)])
        height = None
        for pose in variants:
            weight_error = delta = 0.0
            if pose["clip"]:
                g = Gltf(path)
                shape, weight_error = bake(g, pose["clip"], pose["seconds"])
                unskinned = g.to_mesh()[0]
                delta = float(np.max(np.linalg.norm(shape[0] - unskinned, axis=1)))
            else:
                shape = load(path)[:3]
            native_bounds = [shape[0].min(0).tolist(), shape[0].max(0).tolist()]
            shape, height = normalize(shape, height, source.get("up_axis", "Y"))
            key = source["key"] + pose["suffix"]
            folder = "active" if source["active"] else "staged"
            filename = folder + "/" + key + ".npz"
            save_mesh(output / filename, shape)
            rows.append(
                dict(
                    key=key,
                    name=source["name"],
                    author=source["author"],
                    license="CC0-1.0",
                    source_url=source["source_url"],
                    license_url="https://creativecommons.org/publicdomain/zero/1.0/",
                    license_evidence=source["license_evidence"],
                    source_sha256=source["files"][0]["sha256"],
                    source_files=source["files"],
                    verified=source["verified"],
                    file=filename,
                    sha256=digest(output / filename),
                    active=source["active"],
                    triangles=len(shape[0]) // 3,
                    bounds=[shape[0].min(0).tolist(), shape[0].max(0).tolist()],
                    native_bounds=native_bounds,
                    normalization_height=height,
                    default_height_m=source["default_height_m"],
                    pose=pose["clip"],
                    seconds=pose["seconds"],
                    maximum_weight_sum_error=weight_error,
                    maximum_displacement_from_unskinned=delta,
                )
            )
    result = dict(
        format=1,
        axes="Y up; base zero; X/Z centred",
        colour_space="sRGB RGBA; opaque context geometry",
        models=rows,
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "catalog.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf8"
    )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=Path("data/models/sources.json")
    )
    parser.add_argument("--sources", type=Path, default=Path("build/models-originals"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = bake_catalog(args.manifest, args.sources, args.output)
    print(f"{len(rows)} static meshes; {sum(r['triangles'] for r in rows)} triangles")


if __name__ == "__main__":
    main()
