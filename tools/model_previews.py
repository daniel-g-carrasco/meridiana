"""R374, R375: the previews of the kinds of 3D object for the picker (Shell/ObjectPicker.qml), one PNG per kind in
data/models/previews: the catalogue's model where the kind has one (models3d.ASSET_FOR_KIND), the mesh props.py draws
otherwise (the trees, the roof obstacles). Drawn without Qt Quick 3D: an isometric view, the triangles painted far to
near, flat shaded by their normal, on a transparent ground; 112 px for a 56 px tile on a doubled screen.

    python tools/model_previews.py            (from the repository; PYTHONPATH=src)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "data" / "models" / "previews"
SIZE = 112
MARGIN = 6


def triangles(kind):
    from meridiana import props
    from meridiana.quick.backend import models3d, scene_assets
    key = models3d.ASSET_FOR_KIND.get(kind)
    if key is not None:
        p, n, c = scene_assets.load_model(key)
        return np.asarray(p, float), np.asarray(n, float), np.asarray(c[:, :3], float)
    p, n, c = props.placed_mesh(kind, (0.0, 0.0))
    return np.asarray(p, float), np.asarray(n, float), np.asarray(c, float)


def render(kind, out: Path):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QColor, QImage, QPainter, QPolygonF
    p, n, c = triangles(kind)
    low, high = p.min(0), p.max(0)
    p = (p - (low + high) / 2) / max(float((high - low).max()), 1e-6)       # centred, the longest side 1
    d = np.array([1.0, 0.9, 1.0]); d /= np.linalg.norm(d)                   # the eye, from East, above, South
    f = -d
    r = np.cross(f, [0.0, 1.0, 0.0]); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    sx, sy, depth = p @ r, p @ u, p @ f
    light = np.array([0.4, 1.0, 0.6]); light /= np.linalg.norm(light)
    tri = len(p) // 3
    sx, sy, depth = sx.reshape(tri, 3), sy.reshape(tri, 3), depth.reshape(tri, 3)
    normals = n.reshape(tri, 3, 3).mean(1)
    shade = 0.55 + 0.45 * np.clip(normals @ light, 0, 1)
    colour = np.clip(c.reshape(tri, 3, 3).mean(1) * shade[:, None], 0, 1)
    span = max(sx.max() - sx.min(), sy.max() - sy.min(), 1e-6)
    scale = (SIZE - 2 * MARGIN) / span
    ox = SIZE / 2 - (sx.max() + sx.min()) / 2 * scale
    oy = SIZE / 2 + (sy.max() + sy.min()) / 2 * scale
    order = np.argsort(-depth.mean(1))                                      # the far ones first
    image = QImage(SIZE, SIZE, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(Qt.NoPen)
    for i in order:
        colour_i = QColor.fromRgbF(*colour[i])
        painter.setBrush(colour_i)
        painter.setPen(colour_i)                                            # the seams between the triangles closed
        painter.drawPolygon(QPolygonF([QPointF(ox + sx[i, k] * scale, oy - sy[i, k] * scale) for k in range(3)]))
    painter.end()
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(out), "PNG")


def main():
    from PySide6.QtGui import QGuiApplication
    from meridiana import props
    app = QGuiApplication.instance() or QGuiApplication(["previews", "-platform", "offscreen"])
    for kind in props.KINDS:
        render(kind, OUT / f"{kind}.png")
        print(kind)
    return 0


if __name__ == "__main__":
    sys.exit(main())
