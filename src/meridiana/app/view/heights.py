"""The surface under a point of the plan: its height and the normal of its plane (study 46, the measuring tool).

A point inside a building's outline is on its roof, at the pitch it falls on (a flat roof is one level pitch); where
roofs lie one over another (a plant room on a shed) the highest one is the one seen from above; anywhere else the
ground, at 0. A point on the boundary of a pitch (its eave, its ridge, a corner) is on it: a corner snapped to in the
plan has the height of the roof there, not of the ground. No Qt.
"""

from __future__ import annotations

import math

GROUND = (0.0, (0.0, 0.0, 1.0))
EDGE = 1e-6          # metres: a point this close to a pitch's outline is on the pitch (snapped corners and edges)


def _inside(x: float, y: float, ring) -> bool:
    yes = False
    j = len(ring) - 1
    for i in range(len(ring)):
        (xi, yi), (xj, yj) = ring[i], ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            yes = not yes
        j = i
    return yes


def _near_outline(x: float, y: float, ring, tolerance: float) -> bool:
    for (ax, ay), (bx, by) in zip(ring, ring[1:] + ring[:1], strict=True):
        dx, dy = bx - ax, by - ay
        n2 = dx * dx + dy * dy
        t = 0.0 if n2 < 1e-24 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / n2))
        if math.hypot(ax + dx * t - x, ay + dy * t - y) <= tolerance:
            return True
    return False


def _normal(pitch) -> tuple:
    """The unit normal of the pitch's plane, pointing up, from the plane itself (any pitch that answers z(x, y))."""
    x, y = pitch.ring[0]
    z = pitch.z(x, y)
    gx, gy = pitch.z(x + 1.0, y) - z, pitch.z(x, y + 1.0) - z
    n = math.sqrt(gx * gx + gy * gy + 1.0)
    return (-gx / n, -gy / n, 1.0 / n)


class Surfaces:
    """The roofs of a project as seen from above; `at(x, y)` the (height, normal) of the surface under the point."""

    def __init__(self, project=None):
        self._items = []
        for b in getattr(project, "buildings", None) or []:
            if len(b.footprint) < 3:
                continue
            for pitch in b.pitches():
                ring = [(float(p[0]), float(p[1])) for p in pitch.ring]
                if len(ring) < 3:
                    continue
                xs, ys = [p[0] for p in ring], [p[1] for p in ring]
                box = (min(xs) - EDGE, min(ys) - EDGE, max(xs) + EDGE, max(ys) + EDGE)
                self._items.append((box, ring, pitch, _normal(pitch)))

    def __len__(self):
        return len(self._items)

    def at(self, x: float, y: float) -> tuple[float, tuple]:
        """(height, unit normal) of the highest surface under (East, North): a pitch, or the ground (0, up)."""
        best = None
        for (x0, y0, x1, y1), ring, pitch, normal in self._items:
            if not (x0 <= x <= x1 and y0 <= y <= y1):
                continue
            if not (_inside(x, y, ring) or _near_outline(x, y, ring, EDGE)):
                continue
            z = float(pitch.z(x, y))
            if best is None or z > best[0]:
                best = (z, normal)
        return best or GROUND

    def height(self, x: float, y: float) -> float:
        return self.at(x, y)[0]
