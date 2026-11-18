"""The view cube of the 3D view (study 12, T1; study 15, 2.5), as FreeCAD's NaviCube is made: 26 parts to click
(6 faces, 12 edges, 8 corners), arrows that turn the view by 45 degrees, a compass ring with N, E, S, W, and Home.
Faces Top, N, E, S, W rather than front and back: «from the South» is the elevation a PV designer needs (study 12a,
2.10). No Qt here: the view draws what `faces` gives and asks `pick` what was clicked.

A part is a direction from the centre of the cube, each component -1, 0 or 1, in Qt's axes (x East, y up,
z South): (0, 1, 0) is the top face, (0, 0, -1) the North face, (1, 1, 0) the edge between the top and the East
face, (1, 1, 1) the corner of the top, East and South faces. Each face is drawn as 3 x 3 cells: the middle one is
the face, those along its sides the edges, those at its corners the corners; clicking a cell looks from its part.
"""

from __future__ import annotations

import itertools
import math

import numpy as np

from . import camera

FACES = {(0, 1, 0): "top", (0, -1, 0): "bottom", (0, 0, -1): "north", (0, 0, 1): "south", (1, 0, 0): "east",
         (-1, 0, 0): "west"}
BORDER = 0.28               # the share of a face's side taken by its edge cells, each side
STEP = 45.0                 # the arrows turn the view by this much (FreeCAD: 360 / 8)


def face_names() -> dict:
    from .i18n import pgettext
    return {"top": pgettext("view cube", "Top"), "bottom": pgettext("view cube", "Bottom"),
            "north": pgettext("cardinal", "N"), "south": pgettext("cardinal", "S"),
            "east": pgettext("cardinal", "E"), "west": pgettext("cardinal", "W")}


def parts() -> list[tuple[int, int, int]]:
    """The 26 parts: every direction of components -1, 0, 1 but the centre."""
    return [p for p in itertools.product((-1, 0, 1), repeat=3) if p != (0, 0, 0)]


def kind(part) -> str:
    n = sum(1 for c in part if c)
    return {1: "face", 2: "edge", 3: "corner"}[n]


def looking_from(part, current: camera.Camera | None = None) -> tuple[float, float]:
    """The bearing and the elevation of a camera that looks at the cube from `part`. For the top and the bottom the
    bearing is the nearest quarter of the one in hand: a click on Top does not turn the plan upside down («rotate to
    nearest», as FreeCAD's)."""
    d = np.asarray(part, dtype=float)
    f = -d / np.linalg.norm(d)                      # the camera looks towards the centre
    elevation = math.degrees(math.asin(max(-1.0, min(1.0, f[1]))))
    if abs(f[0]) < 1e-9 and abs(f[2]) < 1e-9:
        bearing = current.bearing() if current is not None else 0.0
        return round(bearing / 90.0) * 90.0 % 360.0, elevation
    return math.degrees(math.atan2(f[0], -f[2])) % 360.0, elevation


def turned(current: camera.Camera, arrow: str) -> tuple[float, float]:
    """The view after an arrow: left and right turn the model by STEP about the vertical, up and down tilt it by
    STEP (never over the top)."""
    b, e = current.bearing(), current.elevation()
    if arrow == "left":
        return (b - STEP) % 360.0, e
    if arrow == "right":
        return (b + STEP) % 360.0, e
    if arrow == "up":
        return b, max(-90.0, e - STEP)
    if arrow == "down":
        return b, min(90.0, e + STEP)
    raise ValueError(f"unknown arrow {arrow!r}")


def compass_view(letter: str, current: camera.Camera) -> tuple[float, float]:
    """A letter of the compass ring: the view from that side, as high as the one in hand."""
    looks = {"N": 180.0, "E": 270.0, "S": 0.0, "W": 90.0}[letter]
    return looks, current.elevation()


def _axes(cam: camera.Camera) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return cam.right(), cam.up(), cam.forward()


def _cell_corners(normal, i: int, j: int) -> list[np.ndarray]:
    """The four corners of cell (i, j) of a face, i and j from -1 to 1 along its two other axes."""
    n = np.asarray(normal, dtype=float)
    axes = [k for k in range(3) if n[k] == 0]
    u, v = np.eye(3)[axes[0]], np.eye(3)[axes[1]]
    edges = {-1: (-1.0, -1.0 + 2 * BORDER), 0: (-1.0 + 2 * BORDER, 1.0 - 2 * BORDER), 1: (1.0 - 2 * BORDER, 1.0)}
    (a0, a1), (b0, b1) = edges[i], edges[j]
    return [n + a * u + b * v for a, b in ((a0, b0), (a1, b0), (a1, b1), (a0, b1))]


def faces(cam: camera.Camera, size: float) -> list[tuple[tuple, list[tuple[float, float]], float]]:
    """The cells of the faces turned towards the camera, as (part, polygon in pixels, depth), farthest first, for a
    cube drawn `size` pixels across centred at (0, 0). Parallel projection: the cube has no perspective."""
    right, up, fwd = _axes(cam)
    scale = size / (2 * math.sqrt(3))
    out = []
    for normal in FACES:
        n = np.asarray(normal, dtype=float)
        if float(np.dot(n, -fwd)) <= 1e-6:
            continue                                # turned away
        axes = [k for k in range(3) if n[k] == 0]
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                corners = _cell_corners(normal, i, j)
                poly = [(float(np.dot(c, right)) * scale, -float(np.dot(c, up)) * scale) for c in corners]
                part = list(normal)
                part[axes[0]] += i
                part[axes[1]] += j
                depth = float(np.mean([np.dot(c, fwd) for c in corners]))
                out.append((tuple(part), poly, depth))
    out.sort(key=lambda f: -f[2])
    return out


def _inside(poly, x: float, y: float) -> bool:
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1], strict=True):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def pick(cam: camera.Camera, size: float, x: float, y: float) -> tuple | None:
    """The part under (x, y), pixels from the centre of the cube; None outside it."""
    for part, poly, _depth in reversed(faces(cam, size)):     # nearest first
        if _inside(poly, x, y):
            return part
    return None
