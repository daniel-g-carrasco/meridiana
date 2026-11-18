"""Offline glTF animation and skin bake, adapted from the R11 proof."""

import copy
import math
import numpy as np


def sample(g, sampler, seconds, rotation=False):
    times = g.accessor(sampler["input"]).ravel()
    values = g.accessor(sampler["output"])
    interpolation = sampler.get("interpolation", "LINEAR")
    if interpolation not in ("LINEAR", "STEP"):
        raise ValueError("Unsupported interpolation: " + interpolation)
    k = int(
        np.clip(np.searchsorted(times, seconds, side="right") - 1, 0, len(times) - 1)
    )
    if k == len(times) - 1 or interpolation == "STEP":
        return values[k].astype(float)
    f = float(np.clip((seconds - times[k]) / (times[k + 1] - times[k]), 0, 1))
    a, b = values[k].astype(float), values[k + 1].astype(float)
    if rotation:
        dot = float(np.dot(a, b))
        if dot < 0:
            b, dot = -b, -dot
        if dot < 0.9995:
            angle = math.acos(np.clip(dot, -1, 1))
            return (math.sin((1 - f) * angle) * a + math.sin(f * angle) * b) / math.sin(
                angle
            )
        q = a * (1 - f) + b * f
        return q / np.linalg.norm(q)
    return a * (1 - f) + b * f


def bake(g, animation_name, seconds):
    nodes = copy.deepcopy(g.j["nodes"])
    animation = next(
        a for a in g.j["animations"] if a["name"].split("|")[-1] == animation_name
    )
    for channel in animation["channels"]:
        target = channel["target"]
        path = target["path"]
        if path not in ("translation", "rotation", "scale"):
            raise ValueError("Unsupported channel: " + path)
        nodes[target["node"]][path] = sample(
            g, animation["samplers"][channel["sampler"]], seconds, path == "rotation"
        )
    worlds = {}

    def walk(index, parent):
        worlds[index] = parent @ g._local(nodes[index])
        for child in nodes[index].get("children", []):
            walk(child, worlds[index])

    for index in g.j["scenes"][g.j.get("scene", 0)]["nodes"]:
        walk(index, np.eye(4))
    positions, normals, colours = [], [], []
    max_weight_error = 0.0
    for index, node in enumerate(nodes):
        if index not in worlds or "mesh" not in node:
            continue
        world = worlds[index]
        for primitive in g.j["meshes"][node["mesh"]]["primitives"]:
            attributes = primitive["attributes"]
            if "skin" in node:
                skin = g.j["skins"][node["skin"]]
                inverse = (
                    g.accessor(skin["inverseBindMatrices"])
                    .reshape(-1, 4, 4)
                    .transpose(0, 2, 1)
                )
                # glTF world position = sum(weight * joint_world * inverse_bind * position).
                palette = np.asarray(
                    [
                        worlds[j] @ inv
                        for j, inv in zip(skin["joints"], inverse, strict=True)
                    ]
                )
                joints = g.accessor(attributes["JOINTS_0"]).astype(int)
                weights = g.accessor(attributes["WEIGHTS_0"]).astype(float)
                max_weight_error = max(
                    max_weight_error, float(np.max(abs(weights.sum(axis=1) - 1)))
                )
                weights /= weights.sum(axis=1, keepdims=True)
                transform = np.sum(palette[joints] * weights[:, :, None, None], axis=1)
                pos = g.accessor(attributes["POSITION"])
                pos = np.einsum("nij,nj->ni", transform, np.c_[pos, np.ones(len(pos))])[
                    :, :3
                ]
                replacements = {attributes["POSITION"]: pos}
                if "NORMAL" in attributes:
                    n = g.accessor(attributes["NORMAL"])
                    n = np.einsum(
                        "nij,nj->ni",
                        np.linalg.inv(transform[:, :3, :3]).transpose(0, 2, 1),
                        n,
                    )
                    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
                    replacements[attributes["NORMAL"]] = n
                original = g.accessor
                g.accessor = lambda key, replacement=replacements, old=original: (
                    replacement[key] if key in replacement else old(key)
                )
                try:
                    g._primitive(primitive, np.eye(4), positions, normals, colours)
                finally:
                    g.accessor = original
            else:
                g._primitive(primitive, world, positions, normals, colours)
    return tuple(
        np.concatenate(a).astype(np.float32) for a in (positions, normals, colours)
    ), max_weight_error
