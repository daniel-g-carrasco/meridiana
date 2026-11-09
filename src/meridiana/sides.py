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


def outward(ring, side: int) -> tuple[float, float]:
    """The unit normal of side `side`, pointing out of the outline (whichever way the ring is drawn)."""
    pts = [tuple(map(float, p)) for p in ring]
    n = len(pts)
    a, b = pts[side % n], pts[(side + 1) % n]
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length < EPS:
        raise ValueError(_("the side has no length"))
    area = 0.5 * sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(pts, pts[1:] + pts[:1], strict=True))
    nx, ny = (dy / length, -dx / length) if area > 0 else (-dy / length, dx / length)
    return nx, ny


def offset(ring, side: int, point) -> float:
    """How far `point` lies from side `side` along its outward normal (negative inwards): the distance a side
    dragged to the pointer moves by (R473)."""
    pts = [tuple(map(float, p)) for p in ring]
    a = pts[side % len(pts)]
    nx, ny = outward(ring, side)
    return (float(point[0]) - a[0]) * nx + (float(point[1]) - a[1]) * ny


def shift(ring, side: int, distance: float) -> list[list[float]]:
    """The outline with side `side` moved `distance` metres along its outward normal, staying parallel to itself
    (R473): its two neighbours lengthen or shorten along their own lines, as CAD programs stretch a side, and the
    other sides stay. A neighbour parallel to the side (a notch's bottom) moves with it instead. Refused when the
    outline would cross itself or vanish."""
    pts = [tuple(map(float, p)) for p in ring]
    n = len(pts)
    if n < 3:
        raise ValueError(_("the outline would cross itself or vanish"))
    i, j = side % n, (side + 1) % n
    nx, ny = outward(ring, i)
    a, b = pts[i], pts[j]
    moved_a = (a[0] + nx * distance, a[1] + ny * distance)
    moved_b = (b[0] + nx * distance, b[1] + ny * distance)
    out = [list(p) for p in pts]

    def along(p, q, start, end):
        """Where the line through p-q (the moved side) meets the line through start-end (a neighbour)."""
        dx, dy = q[0] - p[0], q[1] - p[1]
        ex, ey = end[0] - start[0], end[1] - start[1]
        den = dx * ey - dy * ex
        if abs(den) < EPS * max(1.0, math.hypot(dx, dy) * math.hypot(ex, ey)):
            return None                     # parallel: the neighbour moves with the side
        t = ((start[0] - p[0]) * ey - (start[1] - p[1]) * ex) / den
        return (p[0] + t * dx, p[1] + t * dy)
    prev, nxt = pts[(i - 1) % n], pts[(j + 1) % n]
    new_a = along(moved_a, moved_b, prev, a) if n > 3 else None
    new_b = along(moved_a, moved_b, b, nxt) if n > 3 else None
    if n == 3:
        # a triangle: its two other sides meet at the far corner, which stays; they lengthen towards the moved side
        new_a = along(moved_a, moved_b, prev, a)
        new_b = along(moved_a, moved_b, b, nxt)
    out[i] = list(new_a if new_a is not None else moved_a)
    out[j] = list(new_b if new_b is not None else moved_b)
    out = [[round(x, 6), round(y, 6)] for x, y in out]
    poly = Polygon(out)
    signed = sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(out, out[1:] + out[:1], strict=True))
    was = sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(pts, pts[1:] + pts[:1], strict=True))
    if not poly.is_valid or poly.area < 0.5 or signed * was <= 0:
        # the side dragged past the far side turns the outline inside out: refused as a fold
        raise ValueError(_("the outline would cross itself or vanish"))
    # a neighbour that crossed over (the side dragged past the far side) folds the outline: refused above by
    # validity; a neighbour shrunk to nothing would leave two corners on one point
    for p, q in zip(out, out[1:] + out[:1], strict=True):
        if math.dist(p, q) < 1e-3:
            raise ValueError(_("the outline would cross itself or vanish"))
    return out


def insert(ring, side: int, parts: int | None = None, at=None) -> tuple[list[list[float]], int]:
    """The outline with vertices added on side `side` (from vertex `side` to the next, R356): one where `at` falls on
    the side (projected on it), or `parts - 1` that divide it in `parts` equal parts. Gives the outline and how many
    vertices came. Refused when the point falls on a corner or the parts are fewer than two."""
    pts = [[float(x), float(y)] for x, y in ring]
    n = len(pts)
    a, b = pts[side % n], pts[(side + 1) % n]
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if at is not None:
        t = max(0.0, min(1.0, ((at[0] - a[0]) * dx + (at[1] - a[1]) * dy) / (length * length))) if length > EPS else 0.0
        if t * length < 0.01 or (1.0 - t) * length < 0.01:
            raise ValueError(_("the point is on a corner: a vertex goes inside the side"))
        ts = [t]
    else:
        if parts is None or parts < 2:
            raise ValueError(_("a side is divided in two parts at least"))
        ts = [k / parts for k in range(1, parts)]
    added = [[round(a[0] + t * dx, 4), round(a[1] + t * dy, 4)] for t in ts]
    out = [list(q) for q in ring]
    out[side % n + 1:side % n + 1] = added
    return out, len(added)
