"""The gizmo of Move and Rotate in the 3D view, without Qt (study 16, B2 and B4; task 16b, steps 5-7): where its
handles are, which one is under the pointer, what a drag along an arrow, across the square of the plane or round
the ring gives, in steps. The view (ui/view3d.py, qml/Scene.qml) draws it and passes the pixels; the sums are
here, tested offscreen (the 3D view does not draw offscreen, study 16, B4, so nothing here asks it).

Qt axes (camera.py): x East, y up, z South. The gizmo stands on the middle of the selection, at its roof; an
arrow is PIXELS long on the screen wherever it stands (its length from camera.pixel_size, as the pivot's
cross-hair). Its shapes are mesh.py's (GIZMO_*), in units of that length. The handles:
- "x" East (red) and "y" North (green): a drag along one moves the object along that direction only;
- "xy": the square between them, a drag moves the object across the horizontal plane;
- "rz": the ring about the vertical, a drag turns the object about its middle (anticlockwise on the plan is
  positive, as move.rotate takes it);
- "z" up (blue): drawn faint, and nothing takes it: the model is a plan with heights, and a move does not lift an
  object (its height is in its properties) nor tilt it (which the rings about East and North would do).
The steps, as on the plan (study 16, B6, with Daniel's choice of Ctrl for the copy): with the snaps on, 10 cm and
15 degrees, with Shift 1 cm and 1 degree; with the snaps off, 1 mm and 0.1 degree. Ctrl held at the release makes
a copy (the window does it)."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import mesh

PIXELS = 120.0                  # an arrow on the screen, whatever the distance (Qt Design Studio measures 100 px)
TOLERANCE = 8.0                 # pixels from a handle that still take it (task 16b)
EAST = np.array([1.0, 0.0, 0.0])
NORTH = np.array([0.0, 0.0, -1.0])
UP = np.array([0.0, 1.0, 0.0])
AXES = {"x": EAST, "y": NORTH, "z": UP}
HANDLES = ("x", "y", "z", "xy", "rz")
ACTIVE = ("x", "y", "xy", "rz")         # what a press can take: not "z" (see above)
STEPS = {"snap": 0.10, "fine": 0.01, "free": 0.001}      # metres
ANGLES = {"snap": 15.0, "fine": 1.0, "free": 0.1}        # degrees


def length(cam, centre, h: float) -> float:
    """The metres an arrow is long at `centre`, for a view `h` pixels high: PIXELS on the screen."""
    return PIXELS * cam.pixel_size(centre, h)


def step(kind: str, mods: set, snaps: bool) -> float:
    """The step of a drag: "move" in metres or "angle" in degrees. With the snaps (F3) the coarse one, the fine one
    with Shift; without them the free one."""
    table = ANGLES if kind == "angle" else STEPS
    if not snaps:
        return table["free"]
    return table["fine"] if "shift" in mods else table["snap"]


def stepped(value: float, size: float) -> float:
    return round(round(value / size) * size, 6) + 0.0 if size > 0 else value


def _to_segment(px: float, py: float, a, b) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    n2 = dx * dx + dy * dy
    t = 0.0 if n2 < 1e-12 else max(0.0, min(1.0, ((px - a[0]) * dx + (py - a[1]) * dy) / n2))
    return math.hypot(px - (a[0] + t * dx), py - (a[1] + t * dy))


def _inside(px: float, py: float, poly) -> bool:
    inside = False
    for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1], strict=True):
        if (ay > py) != (by > py) and px < ax + (py - ay) * (bx - ax) / (by - ay):
            inside = not inside
    return inside


def ring_points(centre, size: float, segments: int = mesh.RING_SEGMENTS) -> np.ndarray:
    """The circle of the ring in the scene, closed: (segments + 1, 3)."""
    a = np.linspace(0.0, 2 * math.pi, segments + 1)
    r = mesh.GIZMO_RING[0] * size
    return np.asarray(centre, dtype=float) + (np.cos(a)[:, None] * EAST + np.sin(a)[:, None] * NORTH) * r


def square_points(centre, size: float) -> list[np.ndarray]:
    a, b = mesh.GIZMO_PLANE
    c = np.asarray(centre, dtype=float)
    return [c + (EAST * u + NORTH * v) * size for u, v in ((a, a), (b, a), (b, b), (a, b))]


def pick(cam, px: float, py: float, w: float, h: float, centre, size: float, tolerance: float = TOLERANCE) -> str:
    """The handle under the pixel (one of ACTIVE), or "": the nearest arrow or the ring within `tolerance` pixels,
    else the square when the pixel is inside it (study 16, B4: on the screen, in Python, not with View3D.pick)."""
    c = np.asarray(centre, dtype=float)
    best, found = tolerance, ""
    for name in ("x", "y"):
        a, b = cam.project(c + AXES[name] * mesh.GIZMO_SHAFT[0] * size, w, h), cam.project(c + AXES[name] * size, w, h)
        if a is None or b is None:
            continue
        d = _to_segment(px, py, a, b)
        if d < best:
            best, found = d, name
    ring = [cam.project(p, w, h) for p in ring_points(c, size)]
    for a, b in zip(ring, ring[1:], strict=False):
        if a is not None and b is not None and _to_segment(px, py, a, b) < best:
            best, found = _to_segment(px, py, a, b), "rz"
    if found:
        return found
    square = [cam.project(p, w, h) for p in square_points(c, size)]
    if all(p is not None for p in square) and _inside(px, py, square):
        return "xy"
    return ""


def along(cam, px: float, py: float, w: float, h: float, origin, axis) -> float | None:
    """Where on the line origin + t * axis the ray through the pixel passes closest (two skew lines): t, or None when
    the line is seen end on."""
    o, d = cam.ray(px, py, w, h)
    a = np.asarray(axis, dtype=float)
    n = np.cross(a, d)
    if np.linalg.norm(n) < 1e-9:
        return None
    n2 = np.cross(d, n)
    return float(np.dot(o - np.asarray(origin, dtype=float), n2) / np.dot(a, n2))


def on_plane(cam, px: float, py: float, w: float, h: float, origin, normal) -> np.ndarray | None:
    """Where the ray through the pixel meets the plane through `origin` across `normal`; None when it runs along it
    or meets it behind the camera."""
    o, d = cam.ray(px, py, w, h)
    n = np.asarray(normal, dtype=float)
    den = float(np.dot(d, n))
    if abs(den) < 1e-9:
        return None
    s = float(np.dot(np.asarray(origin, dtype=float) - o, n)) / den
    if s < 0 and not cam.ortho:
        return None
    return o + s * d


def angle_on(cam, px: float, py: float, w: float, h: float, centre, zero) -> float | None:
    """The angle about the vertical through `centre` from the direction `zero` to the point of the horizontal plane
    under the pixel, anticlockwise seen from above, in (-180, 180]; None when there is no such point."""
    hit = on_plane(cam, px, py, w, h, centre, UP)
    if hit is None:
        return None
    v = hit - np.asarray(centre, dtype=float)
    if np.linalg.norm(v) < 1e-9:
        return None
    u = np.asarray(zero, dtype=float)
    return math.degrees(math.atan2(float(np.dot(np.cross(u, v), UP)), float(np.dot(u, v))))


@dataclass
class Drag:
    """One drag of a handle, from the press to the release: where it started (t along the arrow, the point on the
    plane, the direction on the ring) and the value it has reached (East, North in metres; degrees)."""
    handle: str
    centre: np.ndarray
    start: object
    value: tuple = (0.0, 0.0, 0.0)

    @classmethod
    def begin(cls, handle: str, cam, px: float, py: float, w: float, h: float, centre) -> "Drag | None":
        """A press on `handle` at the pixel; None for a handle nothing takes, or one seen so that it gives nothing."""
        c = np.asarray(centre, dtype=float)
        if handle in ("x", "y"):
            t = along(cam, px, py, w, h, c, AXES[handle])
            return None if t is None else cls(handle, c, t)
        if handle in ("xy", "rz"):
            p = on_plane(cam, px, py, w, h, c, UP)
            if p is None:
                return None
            if handle == "xy":
                return cls(handle, c, p)
            v = p - c
            n = float(np.linalg.norm(v))
            return cls(handle, c, v / n) if n > 1e-9 else None
        return None

    def update(self, cam, px: float, py: float, w: float, h: float, mods: set = frozenset(),
               snaps: bool = True) -> tuple:
        """The value with the pointer at the pixel, in steps: (East, North, degrees). A pixel that gives nothing (the
        arrow seen end on, the plane edge on) leaves the last value."""
        if self.handle in ("x", "y"):
            t = along(cam, px, py, w, h, self.centre, AXES[self.handle])
            if t is not None:
                d = stepped(t - self.start, step("move", mods, snaps))
                self.value = (d, 0.0, 0.0) if self.handle == "x" else (0.0, d, 0.0)
        elif self.handle == "xy":
            p = on_plane(cam, px, py, w, h, self.centre, UP)
            if p is not None:
                v, size = p - self.start, step("move", mods, snaps)
                self.value = (stepped(float(np.dot(v, EAST)), size), stepped(float(np.dot(v, NORTH)), size), 0.0)
        elif self.handle == "rz":
            a = angle_on(cam, px, py, w, h, self.centre, self.start)
            if a is not None:
                self.value = (0.0, 0.0, stepped(a, step("angle", mods, snaps)))
        return self.value

    def offset(self) -> np.ndarray:
        """The value as a move in Qt axes, for the gizmo and the preview."""
        return EAST * self.value[0] + NORTH * self.value[1]


def rotation(degrees: float) -> tuple[float, float, float, float]:
    """The quaternion (w, x, y, z) of a turn about the vertical by `degrees`, anticlockwise seen from above: what the
    preview of a turn is drawn with."""
    h = math.radians(degrees) / 2
    return (math.cos(h), 0.0, math.sin(h), 0.0)
