"""Drawing aids for the plan editor: where the point under the cursor really goes, and what to show.

The editor passes the cursor, the points drawn so far (the chain), the reference geometry nearby and the
current scale; this module answers with the snapped point, the guides to draw and the measurements of the
segment being drawn. It knows nothing about Qt, so every rule is tested in tests/test_snapping.py.

Priorities, as in the CAD tools Daniel uses: exact objects first (a vertex, a midpoint, the first point to
close the outline), then the intersection of a guide with a tracking line or an edge (how a rectangle
closes by itself), then a direction (perpendicular or parallel to the last side or to the edge nearby,
then the polar steps), then the nearest point of an edge. The tolerance is in screen pixels, so it follows
the zoom. Holding Ctrl (free=True) switches every aid off.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

Point = tuple[float, float]
Segment = tuple[Point, Point]


@dataclass(frozen=True)
class Guide:
    a: Point
    b: Point
    kind: str          # "perpendicular", "parallel", "extension", "polar", "tracking"
    label: str = ""


@dataclass
class Snap:
    point: Point
    kind: str                     # "free", "vertex", "midpoint", "close", "intersection", "direction", "edge"
    guides: list[Guide] = field(default_factory=list)
    length: float | None = None   # of the segment being drawn, metres
    bearing: float | None = None  # of that segment, degrees from North clockwise
    turn: float | None = None     # from the previous segment, degrees, positive to the left
    area: float | None = None     # of the outline closed through the point, m2


def _sub(a: Point, b: Point) -> Point:
    return a[0] - b[0], a[1] - b[1]


def _dot(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1]


def _cross(a: Point, b: Point) -> float:
    return a[0] * b[1] - a[1] * b[0]


def _unit(v: Point) -> Point | None:
    n = math.hypot(*v)
    return None if n < 1e-12 else (v[0] / n, v[1] / n)


def _closest_on_segment(p: Point, s: Segment) -> Point:
    a, b = s
    ab = _sub(b, a)
    n2 = _dot(ab, ab)
    if n2 < 1e-18:
        return a
    t = max(0.0, min(1.0, _dot(_sub(p, a), ab) / n2))
    return a[0] + ab[0] * t, a[1] + ab[1] * t


def _line_intersection(p: Point, d: Point, q: Point, e: Point) -> Point | None:
    """Of the lines p + t d and q + s e, or None when they are parallel."""
    den = _cross(d, e)
    if abs(den) < 1e-12:
        return None
    t = _cross(_sub(q, p), e) / den
    return p[0] + d[0] * t, p[1] + d[1] * t


def _bearing(v: Point) -> float:
    return math.degrees(math.atan2(v[0], v[1])) % 360.0


def _area(points: list[Point]) -> float:
    return 0.5 * abs(sum(_cross(a, b) for a, b in zip(points, points[1:] + points[:1], strict=True)))


EXACT = ("vertex", "midpoint", "close", "intersection")      # objects: they win over ortho, as osnaps in AutoCAD


def ortho(chain: list[Point], cursor: Point) -> Point:
    """F8, as AutoCAD's ortho: the point from the last one along the nearer of two square directions. Those of
    the first side drawn, so that an outline not aligned with North stays square; East and North before it."""
    last = chain[-1]
    u = _unit(_sub(chain[1], chain[0])) if len(chain) >= 2 else None
    u = u or (1.0, 0.0)
    v = (-u[1], u[0])
    d = _sub(cursor, last)
    a, b = _dot(d, u), _dot(d, v)
    return (last[0] + a * u[0], last[1] + a * u[1]) if abs(a) >= abs(b) else (last[0] + b * v[0], last[1] + b * v[1])


class Snapper:
    def __init__(self, tolerance_px: float = 10.0, polar_step: float = 15.0):
        self.tolerance_px = tolerance_px
        self.polar_step = polar_step
        self.segments: list[Segment] = []
        self.points: list[Point] = []
        self.acquired: list[Segment] = []     # edges the cursor passed over: their directions stay offered

    def set_references(self, segments: list[Segment], points: list[Point] | None = None) -> None:
        """The geometry already in the drawing: outlines of buildings, pitches, sub-fields."""
        self.segments = [s for s in segments if math.dist(*s) > 1e-9]
        self.points = list(points) if points is not None else [p for s in self.segments for p in s]
        self.acquired = []

    def reset(self) -> None:
        """A new outline starts: forget the edges acquired for the previous one."""
        self.acquired = []

    def snap(self, cursor: Point, chain: list[Point], scale: float, free: bool = False) -> Snap:
        """`scale` is metres per screen pixel; `chain` the points fixed so far (empty before the first)."""
        if not free:
            self._acquire(cursor, scale)
        result = Snap(cursor, "free") if free else self._snap(cursor, chain, scale)
        return self._measure(result, chain)

    def _acquire(self, c: Point, scale: float) -> None:
        """As in SketchUp and AutoCAD: passing over an edge makes its direction available afterwards."""
        s = self._nearest_segment(c, self.tolerance_px * scale)
        if s:
            self.acquired = [s] + [a for a in self.acquired if a != s][:1]

    def _snap(self, c: Point, chain: list[Point], scale: float) -> Snap:
        tol = self.tolerance_px * scale

        # 1. exact objects; the first point first: on the outline of a building it is also the building's corner,
        # and the corner won, so the click added a point instead of closing (R42, 24/10/2026)
        objects: list[tuple[Point, str]] = [(chain[0], "close")] if len(chain) >= 3 else []
        objects += [(p, "vertex") for p in self.points]
        objects += [(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), "midpoint") for a, b in self.segments]
        objects += [(p, "vertex") for p in chain[1:-1]]
        best = min(objects, key=lambda o: math.dist(o[0], c), default=None)
        if best and math.dist(best[0], c) <= tol:
            return Snap(best[0], best[1])

        if not chain:
            edge = self._nearest_edge_point(c, tol)
            return Snap(edge, "edge") if edge else Snap(c, "free")

        last = chain[-1]
        directions = self._directions(c, chain, tol)

        # 2. a guide meeting a tracking line through the first point, or an edge
        tracking = self._tracking(chain)
        for d, guide in directions:
            for q, e, tguide in tracking:
                x = _line_intersection(last, d, q, e)
                if x and math.dist(x, c) <= tol and _dot(_sub(x, last), d) > 0:
                    return Snap(x, "intersection", [Guide(last, x, guide.kind, guide.label), Guide(q, x, "tracking", tguide)])
            for s in self.segments:
                x = _line_intersection(last, d, s[0], _sub(s[1], s[0]))
                if x and math.dist(x, c) <= tol and _dot(_sub(x, last), d) > 0 and \
                        math.dist(_closest_on_segment(x, s), x) < 1e-6:
                    return Snap(x, "intersection", [Guide(last, x, guide.kind, guide.label)])

        # 3. a direction
        if directions:
            d, guide = directions[0]
            t = _dot(_sub(c, last), d)
            p = (last[0] + d[0] * t, last[1] + d[1] * t)
            return Snap(p, "direction", [Guide(last, p, guide.kind, guide.label)])

        # 4. an edge
        edge = self._nearest_edge_point(c, tol)
        return Snap(edge, "edge") if edge else Snap(c, "free")

    def _directions(self, c: Point, chain: list[Point], tol: float) -> list[tuple[Point, Guide]]:
        """Directions from the last point the cursor is close to, best first."""
        last = chain[-1]
        v = _sub(c, last)
        if math.hypot(*v) < tol:
            return []
        cands: list[tuple[float, Point, str, str]] = []     # (priority, unit direction, kind, label)

        def add(d: Point | None, kind: str, label: str, priority: float):
            if d is None:
                return
            for s in (1.0, -1.0):
                dd = (d[0] * s, d[1] * s)
                if _dot(v, dd) > 0:
                    cands.append((priority, dd, kind, label))

        if len(chain) >= 2:
            prev = _unit(_sub(chain[-1], chain[-2]))
            if prev:
                add(prev, "extension", "", 0.0)
                add((-prev[1], prev[0]), "perpendicular", "90°", 0.0)
        near = self._nearest_segment(c, 6 * tol)
        for s in ([near] if near else []) + [a for a in self.acquired if a != near]:
            e = _unit(_sub(s[1], s[0]))
            add(e, "parallel", "∥", 0.5)
            add((-e[1], e[0]), "perpendicular", "⊥", 0.5)
        if len(chain) >= 2:
            first = _unit(_sub(chain[1], chain[0]))
            if first:
                add(first, "parallel", "∥", 0.6)
                add((-first[1], first[0]), "perpendicular", "⊥", 0.6)
        if self.polar_step > 0:
            b = _bearing(v)
            nearest = round(b / self.polar_step) * self.polar_step
            r = math.radians(nearest)
            add((math.sin(r), math.cos(r)), "polar", f"{nearest % 360:g}°", 1.0)

        scored = []
        for priority, d, kind, label in cands:
            off = abs(_cross(v, d))              # distance of the cursor from the guide
            if off <= tol:
                scored.append((off / tol + priority, d, Guide(last, last, kind, label)))
        scored.sort(key=lambda t: t[0])
        return [(d, g) for _s, d, g in scored]

    def _tracking(self, chain: list[Point]) -> list[tuple[Point, Point, str]]:
        """Lines through the first point, parallel and perpendicular to the first side: where the
        outline closes square."""
        if len(chain) < 2:
            return []
        first = _unit(_sub(chain[1], chain[0]))
        if not first:
            return []
        return [(chain[0], first, "∥"), (chain[0], (-first[1], first[0]), "⊥")]

    def _nearest_segment(self, c: Point, within: float) -> Segment | None:
        best = min(self.segments, key=lambda s: math.dist(_closest_on_segment(c, s), c), default=None)
        if best and math.dist(_closest_on_segment(c, best), c) <= within:
            return best
        return None

    def _nearest_edge_point(self, c: Point, tol: float) -> Point | None:
        s = self._nearest_segment(c, tol)
        return _closest_on_segment(c, s) if s else None

    @staticmethod
    def _measure(snap: Snap, chain: list[Point]) -> Snap:
        if chain:
            v = _sub(snap.point, chain[-1])
            length = math.hypot(*v)
            if length > 1e-9:          # a segment with no length has no direction: neither is given
                snap.length = length
                snap.bearing = _bearing(v)
                if len(chain) >= 2:
                    u = _sub(chain[-1], chain[-2])
                    if math.hypot(*u) > 1e-9:
                        snap.turn = math.degrees(math.atan2(_cross(u, v), _dot(u, v)))
        if len(chain) >= 2:
            snap.area = _area(chain + [snap.point])
        return snap
