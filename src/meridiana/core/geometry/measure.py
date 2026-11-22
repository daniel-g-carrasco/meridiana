"""The numbers of a measurement in space and the constraints that guide its points (study 46, the ruler).

Every point is (East, North, height) in metres. A span between two points gives its true length, its length in plan,
the height difference, the slope and the direction from North; a path gives its totals and, closed, its area in plan.

A constraint is a line or a plane through the last point. It applies to a point of the plan as seen from above (the
point keeps its place on the plan where it can), to a point the 3D view snapped (projected square on it) and to the
pointer's ray of the 3D view (where the ray meets the plane, or the point of the line nearest the ray). The
degenerate cases answer None or a defined point, never NaN, and nothing raises: a ray parallel to its plane or line,
a point behind the ray's origin, an edge or a direction of no length. No Qt: every rule is in tests/nucleo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

Point3 = tuple[float, float, float]
Edge3 = tuple[Point3, Point3]

EPS = 1e-9
LEVEL = 0.005           # a span whose ends differ by less than this in height is level (it shows as 0,00)
AXES: dict[str, Point3] = {"east": (1.0, 0.0, 0.0), "north": (0.0, 1.0, 0.0), "up": (0.0, 0.0, 1.0)}


def _sub(a, b) -> Point3:
    return a[0] - b[0], a[1] - b[1], a[2] - b[2]


def _add(a, b) -> Point3:
    return a[0] + b[0], a[1] + b[1], a[2] + b[2]


def _scale(a, k: float) -> Point3:
    return a[0] * k, a[1] * k, a[2] * k


def _dot(a, b) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b) -> Point3:
    return a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]


def unit(v) -> Point3 | None:
    """`v` of length one, or None when it has no length (or is not finite)."""
    n = math.sqrt(_dot(v, v))
    return None if not math.isfinite(n) or n < EPS else (v[0] / n, v[1] / n, v[2] / n)


def finite(p) -> bool:
    return p is not None and len(p) == 3 and all(math.isfinite(float(c)) for c in p)


def point3(p, z: float = 0.0) -> Point3:
    """A point of two or three coordinates as (East, North, height), floats."""
    return (float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else float(z))


# -- the numbers of a span and of a path -------------------------------------------------------------------------

@dataclass(frozen=True)
class Span:
    length: float              # the true length, metres
    plan: float                # its length in plan
    rise: float                # height of the end over the start (negative when it goes down)
    slope: float               # degrees from the horizontal, 0 to 90
    percent: float | None      # the slope in percent; None for a vertical span
    bearing: float | None      # degrees from North, clockwise; None when it has no length in plan

    @property
    def level(self) -> bool:
        return abs(self.rise) < LEVEL


def span(a, b) -> Span:
    d = _sub(b, a)
    plan = math.hypot(d[0], d[1])
    length = math.hypot(plan, d[2])
    slope = math.degrees(math.atan2(abs(d[2]), plan))
    percent = abs(d[2]) / plan * 100.0 if plan > EPS else None
    bearing = None
    if plan > EPS:
        bearing = math.degrees(math.atan2(d[0], d[1])) % 360.0
        bearing = 0.0 if bearing >= 360.0 else bearing          # -1e-17 % 360 is 360.0
    return Span(length, plan, d[2], 0.0 if length < EPS else slope, percent, bearing)


def totals(points, closed: bool = False) -> tuple[float, float]:
    """(true length, length in plan) of the path through `points`, back to the first one when `closed`."""
    pts = list(points)
    pairs = list(zip(pts, pts[1:] + (pts[:1] if closed and len(pts) > 2 else []), strict=False))
    spans = [span(a, b) for a, b in pairs]
    return sum(s.length for s in spans), sum(s.plan for s in spans)


def plan_area(points) -> float:
    """The area in plan of the ring through `points` (square metres, 0 below three points)."""
    pts = list(points)
    if len(pts) < 3:
        return 0.0
    return 0.5 * abs(sum(a[0] * b[1] - a[1] * b[0] for a, b in zip(pts, pts[1:] + pts[:1], strict=True)))


def foot(p, a, b) -> Point3:
    """The foot of the perpendicular from `p` to the line of the edge a-b (beyond its ends too); `a` when the edge
    has no length."""
    ab = _sub(b, a)
    n2 = _dot(ab, ab)
    if n2 < EPS * EPS:
        return point3(a)
    return _add(a, _scale(ab, _dot(_sub(p, a), ab) / n2))


def along(origin, direction, length: float, plan: bool = False) -> Point3 | None:
    """The point at `length` from `origin` along `direction`; with `plan` the length is the one in plan (the true one
    for a vertical direction). None when the direction has no length or the length is not finite."""
    u = unit(direction)
    if u is None or not math.isfinite(length):
        return None
    k = length
    if plan:
        h = math.hypot(u[0], u[1])
        if h > EPS:
            k = length / h
    return _add(origin, _scale(u, k))


def parse_length(text) -> float | None:
    """A length typed by hand: decimal comma or point, an optional metre suffix; None for anything else, never NaN
    or infinity."""
    try:
        value = float(str(text).strip().lower().removesuffix("m").strip().replace(",", "."))
    except (ValueError, TypeError):
        return None
    return value if math.isfinite(value) else None


# -- constraints ----------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Constraint:
    """A line (`direction`) or a plane (`normal`) through `origin`; the vectors have length one."""
    origin: Point3
    direction: Point3 | None = None
    normal: Point3 | None = None

    @property
    def is_line(self) -> bool:
        return self.direction is not None


def line(origin, direction) -> Constraint | None:
    u = unit(direction)
    return None if u is None else Constraint(point3(origin), direction=u)


def plane(origin, normal) -> Constraint | None:
    n = unit(normal)
    return None if n is None else Constraint(point3(origin), normal=n)


def axis(origin, name: str) -> Constraint:
    """The line through `origin` along East, North or the vertical ("east", "north", "up")."""
    return Constraint(point3(origin), direction=AXES[name])


def parallel(origin, edge) -> Constraint | None:
    """The line through `origin` parallel to the edge (two 3D ends); None for an edge of no length."""
    return line(origin, _sub(edge[1], edge[0]))


def perpendicular(origin, edge) -> Constraint | None:
    """The plane through `origin` square to the edge: every direction in it is perpendicular to the edge. Met with the
    plane of a pitch (`meet`) it is the line in the pitch square to its eave."""
    return plane(origin, _sub(edge[1], edge[0]))


def meet(a: Constraint, b: Constraint) -> Constraint | None:
    """The line where two planes meet; None when they are parallel or one of them is a line."""
    if a.normal is None or b.normal is None:
        return None
    u = _cross(a.normal, b.normal)
    uu = _dot(u, u)
    if uu < 1e-12:
        return None
    d1, d2 = _dot(a.normal, a.origin), _dot(b.normal, b.origin)
    p = _scale(_add(_scale(_cross(b.normal, u), d1), _scale(_cross(u, a.normal), d2)), 1.0 / uu)
    return line(p, u)


def project(c: Constraint, p) -> Point3:
    """`p` brought square on the line or the plane."""
    w = _sub(p, c.origin)
    if c.direction is not None:
        return _add(c.origin, _scale(c.direction, _dot(w, c.direction)))
    return _sub(point3(p), _scale(c.normal, _dot(w, c.normal)))


def constrain_point(c: Constraint, p) -> Point3:
    """A point of the plan on the constraint, as seen from above: the point of the line nearest to it in plan, the
    point of the plane right above or below it. A vertical line or plane is seen edge on: `p` goes square on it."""
    p = point3(p)
    if c.direction is not None:
        u = c.direction
        h2 = u[0] * u[0] + u[1] * u[1]
        if h2 < 1e-12:
            return project(c, p)
        s = ((p[0] - c.origin[0]) * u[0] + (p[1] - c.origin[1]) * u[1]) / h2
        return _add(c.origin, _scale(u, s))
    n = c.normal
    if abs(n[2]) < 1e-9:
        return project(c, p)
    z = c.origin[2] - (n[0] * (p[0] - c.origin[0]) + n[1] * (p[1] - c.origin[1])) / n[2]
    return p[0], p[1], z


def constrain_ray(c: Constraint, origin, direction) -> Point3 | None:
    """The pointer's ray of the 3D view on the constraint: where it meets the plane, or the point of the line nearest
    to it. None when the ray is parallel to them, has no direction, or the point lies behind its origin."""
    d = unit(direction)
    if d is None:
        return None
    o = point3(origin)
    if c.normal is not None:
        den = _dot(d, c.normal)
        if abs(den) < 1e-9:
            return None
        t = _dot(_sub(c.origin, o), c.normal) / den
        return None if t < 0 else _add(o, _scale(d, t))
    u = c.direction
    w = _sub(c.origin, o)
    b = _dot(u, d)
    den = 1.0 - b * b
    if den < 1e-9:
        return None
    e, f = _dot(d, w), _dot(u, w)
    s = (b * e - f) / den           # along the line
    t = (e - b * f) / den           # along the ray
    return None if t < 0 else _add(c.origin, _scale(u, s))


def on_plane(p, origin, normal, tolerance: float) -> bool:
    """Whether `p` lies within `tolerance` of the plane through `origin` square to `normal`."""
    n = unit(normal)
    return n is not None and abs(_dot(_sub(p, origin), n)) <= tolerance


def parallel_normals(a, b, cos: float = 0.999) -> bool:
    ua, ub = unit(a), unit(b)
    return ua is not None and ub is not None and abs(_dot(ua, ub)) >= cos
