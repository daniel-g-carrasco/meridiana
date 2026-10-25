"""The straight skeleton of a footprint: the roof whose pitches all have the same slope (study 16, A).

Every side of the outline moves inwards at the same speed; the corners trace the hips, the valleys and the
ridges, and each side sweeps the face of its pitch. The height of a point of a face is the time its side took to
reach it, the distance from the eave: on a roof of slope s it stands at eave + height * tan(s). A gable end does
not move (its wall is vertical): the pitches beside it run on to it, as when the gable side is pushed far along
its neighbours and the faces are cut on the footprint (the proof's extended_for_gables), without the far
polygon and the cut.

The events are those of Felkel and Obdrzalek (1998): a side shrinking to nothing (edge event) and a reflex
corner running into another side (split event). Every event of the same instant is handled together, on the
wavefront as it stands at that instant: the corners that meet become one, a corner on a side splits the
wavefront there, and what is left is cut where it touches itself (two reflex corners meeting, three sides
vanishing at one point). The arithmetic that decides is exact (fractions.Fraction): no tolerance says whether
two events happen together. Floats only screen the candidates. Coordinates are taken to the micrometre; the unit
normal of a side whose length is not rational is rounded to 1e-18, which makes the result the exact skeleton of
sides moving at speeds within 1e-18 of one.

Checked against CGAL 5.6 (Straight_skeleton_2) on the 306 footprints of
docs/studio/16-prove/scheletro-riferimento.json (tests/test_skeleton.py). No holes yet (a courtyard is task 16a,
step 4).
"""

from __future__ import annotations

import math
from fractions import Fraction

Point = tuple[float, float]
Face = list[tuple[float, float, float]]     # (x, y, height above the eave in units of run)

_UNIT = 1_000_000            # coordinates to the micrometre
_ROUND = 10 ** 18            # unit normals of irrational length, to 1e-18
SHORT = 1e-4                 # m: a side shorter than this is no side
IN_LINE = 1e-3               # m: a corner this close to the line through its neighbours is no corner
_SCREEN = 1e-6               # m of height: events this close to the first one are checked exactly


class SkeletonError(ValueError):
    """A footprint the skeleton cannot be built on: fewer than three sides, crossing itself, no eave."""


def _rational(value) -> Fraction:
    return Fraction(round(float(value) * _UNIT), _UNIT)


def _sqrt(q: Fraction) -> Fraction:
    """The square root of a positive rational: exact when it is a rational, else to about 1e-18."""
    n, d = q.numerator, q.denominator
    rn, rd = math.isqrt(n), math.isqrt(d)
    if rn * rn == n and rd * rd == d:
        return Fraction(rn, rd)
    return Fraction(math.isqrt(n * d * _ROUND * _ROUND), d * _ROUND)


def clean(ring) -> tuple[list[tuple[Fraction, Fraction]], list[int]]:
    """The footprint as the skeleton takes it: counter-clockwise, to the micrometre, without sides shorter than
    SHORT and without corners in line with their neighbours (within IN_LINE), as shapely.simplify(0) does.
    Returns the points and, for each side left, the side of `ring` it comes from (side i runs from point i to
    point i + 1; of two sides in line the first stands for both). SkeletonError for fewer than three sides."""
    pts = [(_rational(x), _rational(y)) for x, y in ring]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    n = len(pts)
    if n < 3:
        raise SkeletonError("a footprint needs at least three sides")
    origin = list(range(n))                       # side k runs from pts[k] to pts[k + 1]
    twice = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1], strict=True))
    if twice < 0:
        pts.reverse()                             # side k of the reversed ring is side n - 2 - k reversed
        origin = [(n - 2 - k) % n for k in range(n)]
    changed = True
    while changed and len(pts) >= 3:
        changed = False
        m = len(pts)
        for k in range(m):
            a, b = pts[k], pts[(k + 1) % m]
            if math.dist(a, b) < SHORT:
                del pts[k]                        # the side goes; the one before runs on to its end
                del origin[k]
                changed = True
                break
        if changed:
            continue
        for k in range(m):
            p, a, q = pts[k - 1], pts[k], pts[(k + 1) % m]
            ux, uy = float(q[0] - p[0]), float(q[1] - p[1])
            length = math.hypot(ux, uy)
            along = (float(a[0] - p[0]) * ux + float(a[1] - p[1]) * uy)
            off = abs(float(a[0] - p[0]) * uy - float(a[1] - p[1]) * ux)
            if length > 0 and off < IN_LINE * length and 0 < along < length * length:
                del pts[k]                        # side k joins side k - 1, which stands for both
                del origin[k]
                changed = True
                break
    if len(pts) < 3:
        raise SkeletonError("a footprint needs at least three sides")
    from shapely.geometry import Polygon
    if not Polygon([(float(x), float(y)) for x, y in pts]).is_valid:
        raise SkeletonError("the footprint crosses itself")
    return pts, origin


class _Side:
    """A side of the footprint and its front: the line n . p = c + s t at time t (n the inward unit normal,
    s the speed: 1 for an eave, 0 for a gable end)."""
    __slots__ = ("ax", "ay", "dx", "dy", "nx", "ny", "c", "s", "f")

    def __init__(self, a, b, speed: int):
        self.ax, self.ay = a
        self.dx, self.dy = b[0] - a[0], b[1] - a[1]
        length2 = self.dx * self.dx + self.dy * self.dy
        root = _sqrt(length2)
        nx, ny = -self.dy / root, self.dx / root
        if root * root != length2:
            nx, ny = Fraction(round(nx * _ROUND), _ROUND), Fraction(round(ny * _ROUND), _ROUND)
        self.nx, self.ny = nx, ny
        self.c = nx * self.ax + ny * self.ay
        self.s = Fraction(speed)
        self.f = (float(nx), float(ny), float(self.c), float(speed), float(self.dx), float(self.dy))


class _Vertex:
    """A corner of the wavefront: at (x, y) at time t, moving at (vx, vy), between the fronts of sides e_in and
    e_out; `node` is where it started (the start of the arc it traces)."""
    __slots__ = ("x", "y", "t", "vx", "vy", "e_in", "e_out", "node", "reflex", "f")

    def __init__(self, x, y, t, e_in, e_out, sides):
        self.x, self.y, self.t = x, y, t
        self.e_in, self.e_out = e_in, e_out
        self.node = (x, y)
        si, sj = sides[e_in], sides[e_out]
        self.vx, self.vy = _velocity(si, sj)
        self.reflex = si.dx * sj.dy - si.dy * sj.dx < 0
        self.f = (float(x), float(y), float(t), float(self.vx), float(self.vy))

    def at(self, t):
        dt = t - self.t
        return self.x + self.vx * dt, self.y + self.vy * dt


def _velocity(si: _Side, sj: _Side):
    det = si.nx * sj.ny - si.ny * sj.nx
    if det:
        return (si.s * sj.ny - si.ny * sj.s) / det, (si.nx * sj.s - si.s * sj.nx) / det
    if si.nx * sj.nx + si.ny * sj.ny > 0 and si.s == sj.s:
        k = si.s / (si.nx * si.nx + si.ny * si.ny)      # two sides in line: the corner goes straight in
        return k * si.nx, k * si.ny
    raise SkeletonError("two sides meet head on")


class _Slot:
    """A place of the wavefront at the instant of an event: its point, the fronts before and after it, the
    corners that end there and whether something happened there."""
    __slots__ = ("p", "e_in", "e_out", "olds", "event")

    def __init__(self, p, e_in, e_out, olds, event):
        self.p, self.e_in, self.e_out, self.olds, self.event = p, e_in, e_out, olds, event


def _collapse_float(u, w, side):
    ux, uy, ut, uvx, uvy = u.f
    wx, wy, wt, wvx, wvy = w.f
    dx, dy = side.f[4], side.f[5]
    rate = (wvx - uvx) * dx + (wvy - uvy) * dy
    if rate >= 0:
        return None
    gap = (wx - wvx * wt - ux + uvx * ut) * dx + (wy - wvy * wt - uy + uvy * ut) * dy
    return -gap / rate


def _collapse_exact(u, w, side):
    rate = (w.vx - u.vx) * side.dx + (w.vy - u.vy) * side.dy
    if rate >= 0:
        return None
    gap = ((w.x - w.vx * w.t - u.x + u.vx * u.t) * side.dx + (w.y - w.vy * w.t - u.y + u.vy * u.t) * side.dy)
    return -gap / rate


def _split_float(r, u, w, side, now):
    nx, ny, c, s, dx, dy = side.f
    rx, ry, rt, rvx, rvy = r.f
    den = nx * rvx + ny * rvy - s
    if den >= 0:
        return None
    t = (c - (nx * (rx - rvx * rt) + ny * (ry - rvy * rt))) / den
    if t < now - _SCREEN:
        return None
    px, py = rx + rvx * (t - rt), ry + rvy * (t - rt)
    ux, uy, ut, uvx, uvy = u.f
    wx, wy, wt, wvx, wvy = w.f
    qx, qy = ux + uvx * (t - ut), uy + uvy * (t - ut)
    zx, zy = wx + wvx * (t - wt), wy + wvy * (t - wt)
    slack = _SCREEN * math.hypot(dx, dy) * (1.0 + abs(t))
    if (px - qx) * dx + (py - qy) * dy < -slack or (zx - px) * dx + (zy - py) * dy < -slack:
        return None
    return t


def _split_exact(r, u, w, side):
    den = side.nx * r.vx + side.ny * r.vy - side.s
    if den >= 0:
        return None
    t = (side.c - (side.nx * (r.x - r.vx * r.t) + side.ny * (r.y - r.vy * r.t))) / den
    px, py = r.at(t)
    qx, qy = u.at(t)
    zx, zy = w.at(t)
    if (px - qx) * side.dx + (py - qy) * side.dy < 0 or (zx - px) * side.dx + (zy - py) * side.dy < 0:
        return None
    return t


def _area2(points) -> Fraction:
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1], strict=True))


def _skeleton(pts, speeds):
    """The arcs of the skeleton, as the segments each face is bounded by: {side: [(p, q), ...]} with p, q the
    exact nodes. The sides of the footprint themselves are not in it."""
    n = len(pts)
    sides = [_Side(pts[i], pts[(i + 1) % n], speeds[i]) for i in range(n)]
    if not any(speeds):
        raise SkeletonError("a roof needs at least one eave")
    corners = [_meet(sides[(i - 1) % n], sides[i], pts[i]) for i in range(n)]
    cycles = [[_Vertex(corners[i][0], corners[i][1], Fraction(0), (i - 1) % n, i, sides) for i in range(n)]]
    segments: dict[int, list] = {i: [] for i in range(n)}
    now = Fraction(0)
    # with a gable end a front can run into a convex corner too (the corner moves slower than the front): every
    # corner is tried against the other fronts; with equal speeds only a reflex corner can split a front
    every = len(set(speeds)) > 1

    def ended(v, p):
        if v.node != p:
            segments[v.e_in].append((v.node, p))
            segments[v.e_out].append((v.node, p))

    guard = 0
    while cycles:
        guard += 1
        if guard > 50 * n + 50:
            raise SkeletonError("the skeleton did not close")
        # 1. the candidate events, screened with floats
        found = []
        fnow = float(now)
        for ci, cyc in enumerate(cycles):
            m = len(cyc)
            for k in range(m):
                t = _collapse_float(cyc[k], cyc[(k + 1) % m], sides[cyc[k].e_out])
                if t is not None:
                    found.append((t, ci, "c", k, None))
            for ri, r in enumerate(cyc):
                if not (r.reflex or every):
                    continue
                for k in range(m):
                    if k == ri or (k + 1) % m == ri:
                        continue                # the fronts beside the corner
                    t = _split_float(r, cyc[k], cyc[(k + 1) % m], sides[cyc[k].e_out], fnow)
                    if t is not None:
                        found.append((t, ci, "s", k, ri))
        if not found:
            raise SkeletonError("the skeleton did not close: the eaves cannot reach every part")
        first = min(f[0] for f in found)
        near = [f for f in found if f[0] <= first + _SCREEN * (1.0 + abs(first))]
        # 2. the exact instant and the events at it
        exact = []
        for _t, ci, kind, k, ri in near:
            cyc = cycles[ci]
            m = len(cyc)
            if kind == "c":
                t = _collapse_exact(cyc[k], cyc[(k + 1) % m], sides[cyc[k].e_out])
            else:
                t = _split_exact(cyc[ri], cyc[k], cyc[(k + 1) % m], sides[cyc[k].e_out])
            if t is not None:
                exact.append((t, ci, kind, k, ri))
        if not exact:
            raise SkeletonError("the skeleton did not close: no event confirmed")
        t_ev = min(e[0] for e in exact)
        if t_ev < now:
            t_ev = now
        events = [e for e in exact if e[0] == t_ev]
        now = t_ev
        # 3. the wavefront at that instant, cycle by cycle
        touched: dict[int, list] = {}
        for _t, ci, kind, k, ri in events:
            touched.setdefault(ci, []).append((kind, k, ri))
        rebuilt = []
        for ci, cyc in enumerate(cycles):
            if ci not in touched:
                rebuilt.append(cyc)
                continue
            rebuilt += _rebuild(cyc, touched[ci], now, sides, segments, ended)
        cycles = rebuilt
    return sides, corners, segments


def _meet(si: _Side, sj: _Side, p):
    """Where the lines of two sides cross at time 0: the corner itself, unless a rounded normal moved a line by
    some 1e-18 m; on the lines, the corners and the events stay exact."""
    det = si.nx * sj.ny - si.ny * sj.nx
    if not det:
        return p
    return (si.c * sj.ny - si.ny * sj.c) / det, (si.nx * sj.c - si.c * sj.nx) / det


def _rebuild(cyc, events, t, sides, segments, ended) -> list:
    """The wavefront `cyc` at the instant `t` of its `events`: the corners at the same point joined, split at
    the points where it touches itself; the cycles that have no area left end there, their fronts becoming
    ridges."""
    m = len(cyc)
    where = [v.at(t) for v in cyc]
    cuts: dict[int, list] = {}
    for kind, k, ri in events:
        if kind != "s":
            continue
        p = where[ri]
        if p != where[k] and p != where[(k + 1) % m]:
            side = sides[cyc[k].e_out]
            key = (p[0] - where[k][0]) * side.dx + (p[1] - where[k][1]) * side.dy
            if all(q != p for _key, q in cuts.get(k, [])):
                cuts.setdefault(k, []).append((key, p))
    slots = []
    for k, v in enumerate(cyc):
        slots.append(_Slot(where[k], v.e_in, v.e_out, [v], False))
        for _key, p in sorted(cuts.get(k, []), key=lambda c: c[0]):
            slots.append(_Slot(p, v.e_out, v.e_out, [], True))
    pending, done = [slots], []
    while pending:
        c = _joined(pending.pop(), ended)
        if c is None:
            continue
        cut = _touching(c)
        if cut is not None:
            # B. the cycle cut where it touches itself
            i, j = cut
            si, sj = c[i], c[j]
            for v in si.olds + sj.olds:
                ended(v, si.p)
            first = [_Slot(si.p, sj.e_in, si.e_out, [], True)] + c[i + 1:j]
            second = [_Slot(si.p, si.e_in, sj.e_out, [], True)] + c[j + 1:] + c[:i]
            pending += [first, second]
        elif len(c) >= 3 and _in_line(c, sides, segments, ended):
            pending.append(c)                     # C. a front in line with the next one: again from A
        else:
            done.append(c)
    # D. what is left: cycles with an area go on, the others end here
    out = []
    for c in done:
        if len(c) < 3 or _area2([s.p for s in c]) <= 0:
            for idx, s in enumerate(c):
                for v in s.olds:
                    ended(v, s.p)
                if len(c) >= 2:
                    q = c[(idx + 1) % len(c)].p
                    if q != s.p:
                        segments[s.e_out].append((s.p, q))
            continue
        cycle = []
        for s in c:
            if not s.event and len(s.olds) == 1 and s.olds[0].e_in == s.e_in and s.olds[0].e_out == s.e_out:
                cycle.append(s.olds[0])           # untouched: it goes on along its arc
                continue
            for v in s.olds:
                ended(v, s.p)
            cycle.append(_Vertex(s.p[0], s.p[1], t, s.e_in, s.e_out, sides))
        out.append(cycle)
    return out


def _joined(slots, ended):
    """A. The places at the same point, one after the other, become one; None when the whole cycle is one
    point (its corners end there)."""
    start = next((i for i in range(len(slots)) if slots[i].p != slots[i - 1].p), None)
    if start is None:
        for s in slots:
            for v in s.olds:
                ended(v, s.p)
        return None
    merged: list[_Slot] = []
    for s in slots[start:] + slots[:start]:
        last = merged[-1] if merged else None
        if last is not None and last.p == s.p:
            last.e_out = s.e_out
            last.olds = last.olds + s.olds
            last.event = True
        else:
            merged.append(_Slot(s.p, s.e_in, s.e_out, list(s.olds), s.event))
    return merged


def _touching(c):
    """The first two places of the cycle at the same point, or None."""
    seen: dict = {}
    for idx, s in enumerate(c):
        if s.p in seen:
            return seen[s.p], idx
        seen[s.p] = idx
    return None


def _in_line(c, sides, segments, ended) -> bool:
    """C. Two fronts in line at a place, which only a gable end brings about. A gable end in line with an eave
    and facing the same way is taken over by the eave: from here the eave runs on over it (the wall of the gable
    ends where the pitch passes over it). Two fronts in line facing each other overlap: the shorter is used up,
    the stretch they share closes both faces there. Changes the cycle in place and says whether it did."""
    m = len(c)
    for k in range(m):
        s = c[k]
        si, sj = sides[s.e_in], sides[s.e_out]
        if si.nx * sj.ny - si.ny * sj.nx:
            continue
        prev, nxt = c[k - 1], c[(k + 1) % m]
        if si.nx * sj.nx + si.ny * sj.ny > 0:
            if si.s == sj.s:
                continue                          # in line at the same speed: the corner goes straight in
            if si.s > sj.s:                       # the front after is the gable's: the eave takes it over
                segments[s.e_in].append((s.p, nxt.p))
                nxt.e_in, nxt.event = s.e_in, True
            else:
                segments[s.e_out].append((prev.p, s.p))
                prev.e_out, prev.event = s.e_out, True
        else:
            back = (nxt.p[0] - s.p[0]) ** 2 + (nxt.p[1] - s.p[1]) ** 2
            ahead = (prev.p[0] - s.p[0]) ** 2 + (prev.p[1] - s.p[1]) ** 2
            shared = (s.p, nxt.p) if back <= ahead else (prev.p, s.p)
            segments[s.e_in].append(shared)
            segments[s.e_out].append(shared)
            if back <= ahead:
                nxt.e_in, nxt.event = s.e_in, True
            else:
                prev.e_out, prev.event = s.e_out, True
        for v in s.olds:
            ended(v, s.p)
        del c[k]
        return True
    return False


def _face(k: int, corners, segments) -> list:
    """The face of side k as its ring of exact points: the side, then the arcs back to its start."""
    n = len(corners)
    a, b = corners[k], corners[(k + 1) % n]
    links: dict = {}
    for idx, (p, q) in enumerate(segments[k]):
        links.setdefault(p, []).append((q, idx))
        links.setdefault(q, []).append((p, idx))
    used: set = set()
    ring = [a, b]
    here = b
    while here != a:
        step = next(((q, idx) for q, idx in links.get(here, ()) if idx not in used), None)
        if step is None or len(ring) > len(segments[k]) + 2:
            raise SkeletonError(f"the face of side {k + 1} does not close")
        used.add(step[1])
        here = step[0]
        if here != a:
            ring.append(here)
    return ring


def _float_face(ring, side: _Side) -> Face:
    """A face as floats with the height of each point (the time its side reached it), without the points
    closer than a micrometre to the one before."""
    out: Face = []
    for x, y in ring:
        h = side.nx * x + side.ny * y - side.c
        point = (float(x), float(y), float(h))
        if out and math.dist(out[-1][:2], point[:2]) < 1e-9:
            continue
        out.append(point)
    if len(out) > 1 and math.dist(out[0][:2], out[-1][:2]) < 1e-9:
        out.pop()
    return out


def faces(ring, gables=()) -> list[Face | None]:
    """The faces of the roof on `ring`, one for each side of it in its order: each the ring of its points,
    counter-clockwise, from the start of its side (its eave), with the height of each point above the eave in
    units of horizontal run (0 on the eave). A side in `gables` is a gable end: it does not move, and its face
    is None; so is the face of a side the cleaning took away (no length, in line with the one before).
    SkeletonError for a footprint the skeleton cannot be built on."""
    ring = [tuple(map(float, p)) for p in ring]
    if len(ring) > 1 and ring[0] == ring[-1]:
        ring.pop()
    pts, origin = clean(ring)
    gables = set(gables)
    speeds = [0 if origin[k] in gables else 1 for k in range(len(pts))]
    sides, corners, segments = _skeleton(pts, speeds)
    out: list[Face | None] = [None] * len(ring)
    for k in range(len(pts)):
        if speeds[k] == 0:
            continue
        out[origin[k]] = _float_face(_face(k, corners, segments), sides[k])
    return out


def roof(ring, gables=frozenset()) -> list[Face | None]:
    """The pitched roof on `ring` with the sides in `gables` as gable ends (task 16a): a face for every eave,
    None for the gables. The same as faces(); the name the task gives it."""
    return faces(ring, gables)
