"""The sides of an outline after it is drawn: their lengths, the side nearest a point, and a side
stretched to a new length the way CAD programs stretch it: what lies at the far end of the side moves
with it, along it, and the rest stays (a rectangle stays a rectangle, an L keeps its arms).

No Qt here: the plan and the properties call it, the window applies the change as one undoable edit."""

from __future__ import annotations

import math

from shapely.geometry import Polygon

from .i18n import _

EPS = 1e-6


def lengths(ring) -> list[float]:
    pts = [tuple(map(float, p)) for p in ring]
    return [math.dist(a, b) for a, b in zip(pts, pts[1:] + pts[:1], strict=True)]


def nearest(ring, point, within: float) -> int | None:
    """The side nearest `point`, if it is closer than `within` (metres)."""
    best, where = within, None
    pts = [tuple(map(float, p)) for p in ring]
    for i, (a, b) in enumerate(zip(pts, pts[1:] + pts[:1], strict=True)):
        dx, dy = b[0] - a[0], b[1] - a[1]
        n2 = dx * dx + dy * dy
        t = 0.0 if n2 < EPS else max(0.0, min(1.0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / n2))
        d = math.dist(point, (a[0] + t * dx, a[1] + t * dy))
        if d < best:
            best, where = d, i
    return where


def stretch(ring, side: int, length: float) -> list[list[float]]:
    """The outline with side `side` (from vertex `side` to the next) made `length` metres long: every vertex
    at or beyond the side's far end, along the side, moves with it. Refused when the outline would cross
    itself or vanish."""
    pts = [tuple(map(float, p)) for p in ring]
    n = len(pts)
    if length <= 0:
        raise ValueError(_("a side must be longer than zero"))
    a, b = pts[side % n], pts[(side + 1) % n]
    now = math.dist(a, b)
    if now < EPS:
        raise ValueError(_("the side has no length"))
    ux, uy = (b[0] - a[0]) / now, (b[1] - a[1]) / now
    delta = length - now
    tol = 1e-6 * max(1.0, now)
    out = []
    for x, y in pts:
        t = (x - a[0]) * ux + (y - a[1]) * uy
        out.append([round(x + ux * delta, 6), round(y + uy * delta, 6)] if t >= now - tol else [x, y])
    poly = Polygon(out)
    if not poly.is_valid or poly.area < 0.5:
        raise ValueError(_("the outline would cross itself or vanish"))
    return out
