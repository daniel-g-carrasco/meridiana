"""Static CC0 context meshes, loaded once and shared by Quick 3D instances.

Triangle soup: float32 position XYZ, unit normal XYZ, sRGB colour RGBA.
Y points up, the lowest vertex is at zero, X/Z bounds are centred. Standing
height is one; a walking pose uses its standing partner's scale. No runtime
animation, image decoding or network access. Physical dimensions belong to
the object's instance, never to these illustrative meshes or energy inputs.
"""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import hashlib
import json

import numpy as np

from meridiana.paths import shipped


@lru_cache(maxsize=1)
def _records():
    path = shipped("models", "catalog.json")
    if path is None:
        raise FileNotFoundError("Shipped model catalogue is missing")
    return json.loads(path.read_text(encoding="utf8"))["models"]


def catalog(*, active_only=False):
    """Return independent metadata records, including About attribution links."""
    return tuple(
        deepcopy(row) for row in _records() if not active_only or row["active"]
    )


@lru_cache(maxsize=None)
def load_model(key: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read and validate a packaged mesh; return immutable shared arrays."""
    record = next((row for row in _records() if row["key"] == key), None)
    if record is None:
        raise KeyError(key)
    path = shipped("models", record["file"])
    if path is None:
        raise FileNotFoundError(record["file"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
        raise ValueError(f"Model checksum mismatch: {key}")
    with np.load(path, allow_pickle=False) as archive:
        arrays = tuple(
            np.ascontiguousarray(archive[name], dtype=np.float32)
            for name in ("positions", "normals", "colours")
        )
    p, n, c = arrays
    size = record["triangles"] * 3
    if p.shape != (size, 3) or n.shape != p.shape or c.shape != (size, 4):
        raise ValueError(f"Invalid model shape: {key}")
    if not all(np.isfinite(a).all() for a in arrays):
        raise ValueError(f"Nonfinite model data: {key}")
    for array in arrays:
        array.flags.writeable = False
    return arrays
