"""Render baked geometry for offline visual review; not a performance measurement."""

import argparse
import json
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw


def photograph(shape, path, caption, angle=28):
    """Software orthographic raster, interpolated vertex colours and diffuse light only."""
    p, normals, colours = shape
    p = p.astype(float).copy()
    centre = (p.max(axis=0) + p.min(axis=0)) / 2
    p -= centre
    a, b = math.radians(angle), math.radians(-12)
    yaw = np.array(
        [[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]]
    )
    pitch = np.array(
        [[1, 0, 0], [0, math.cos(b), -math.sin(b)], [0, math.sin(b), math.cos(b)]]
    )
    p = p @ (pitch @ yaw).T
    w, h = 560, 600
    scale = min(
        (w - 80) / max(np.ptp(p[:, 0]), 1e-9), (h - 100) / max(np.ptp(p[:, 1]), 1e-9)
    )
    screen = np.c_[p[:, 0] * scale + w / 2, -p[:, 1] * scale + (h - 40) / 2]
    pixels = np.full((h, w, 3), (239, 241, 245), dtype=np.uint8)
    depth = np.full((h, w), -np.inf)
    light = np.array([-0.4, 0.8, 0.5])
    light /= np.linalg.norm(light)
    shade = 0.48 + 0.52 * np.maximum(0, normals @ light)
    lit = np.clip(colours * shade[:, None], 0, 1)
    for k in range(0, len(p), 3):
        tri = screen[k : k + 3]
        x0, y0 = np.maximum(np.floor(tri.min(axis=0)).astype(int), 0)
        x1, y1 = np.minimum(np.ceil(tri.max(axis=0)).astype(int), [w - 1, h - 45])
        if x1 < x0 or y1 < y0:
            continue
        aa, bb, cc = tri
        denominator = (bb[1] - cc[1]) * (aa[0] - cc[0]) + (cc[0] - bb[0]) * (
            aa[1] - cc[1]
        )
        if abs(denominator) < 1e-10:
            continue
        yy, xx = np.mgrid[y0 : y1 + 1, x0 : x1 + 1]
        u = (
            (bb[1] - cc[1]) * (xx + 0.5 - cc[0]) + (cc[0] - bb[0]) * (yy + 0.5 - cc[1])
        ) / denominator
        v = (
            (cc[1] - aa[1]) * (xx + 0.5 - cc[0]) + (aa[0] - cc[0]) * (yy + 0.5 - cc[1])
        ) / denominator
        bary = np.stack([u, v, 1 - u - v], axis=-1)
        z = bary @ p[k : k + 3, 2]
        region = depth[y0 : y1 + 1, x0 : x1 + 1]
        mask = (bary.min(axis=-1) >= -1e-6) & (z > region)
        region[mask] = z[mask]
        pixels[y0 : y1 + 1, x0 : x1 + 1][mask] = ((bary @ lit[k : k + 3]) * 255).astype(
            np.uint8
        )[mask]
    image = Image.fromarray(pixels)
    draw = ImageDraw.Draw(image)
    draw.text((16, h - 36), caption, fill=(20, 24, 32))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, default=Path("data/models"))
    parser.add_argument("--output", type=Path, default=Path("build/models-preview"))
    args = parser.parse_args()
    records = json.loads((args.models / "catalog.json").read_text(encoding="utf8"))[
        "models"
    ]
    tiles = []
    for row in records:
        with np.load(args.models / row["file"], allow_pickle=False) as archive:
            shape = (
                archive["positions"],
                archive["normals"],
                archive["colours"][:, :3],
            )
        path = args.output / (row["key"] + ".png")
        photograph(shape, path, row["key"] + ": " + str(row["triangles"]))
        with Image.open(path) as im:
            tiles.append(im.resize((280, 300)).copy())
    sheet = Image.new("RGB", (280 * 6, 300 * math.ceil(len(tiles) / 6)), "white")
    for index, tile in enumerate(tiles):
        sheet.paste(tile, ((index % 6) * 280, (index // 6) * 300))
    sheet.save(args.output / "catalog.png")
