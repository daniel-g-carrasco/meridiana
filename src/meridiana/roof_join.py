"""The roof drawn by hand as one surface (R303, R304), without Qt: from the free pitches as the file keeps them to the
pitches the views, the shadows, the layouts, the IFC and the report use (model.Building.pitches).

Each free pitch says either a plane (its eave side, eave height and slope, what the designer writes) or the height of
each of its corners (`"z"`, what a corner moved in 3D leaves: the pitch is then "frozen", those heights are the truth).

**Joined (R304, the default of a new roof).** Pitches side by side share a line, and a roof has one height on it: the
planes are worked out together so that they meet exactly on the line the designer drew, which becomes the ridge or
the valley. The plan never changes: the pitches, and the sub-fields on them, stay where they were drawn; what gives
way is a height. By weight, so that the designer's words go first:
1. continuity on the shared lines: always, exactly (a constraint, not a weight);
2. an eave on the outside of the building stays at its height, a flat pitch stays flat (EAVE_WEIGHT, FLAT_WEIGHT);
3. a sloped pitch keeps its slope as far as it can (SLOPE_WEIGHT);
4. the level of a flat pitch and of an eave lying on a shared line gives way last (LEVEL_WEIGHT): this is what
   lifts a flat part up to the top of the slope beside it, instead of flattening the slope.
Two pitches of a gable with the same eave and slope are left exactly as they are. Pitches that touch at a point, or
not at all, are not neighbours. Three pitches at a point are one more shared line each.

**A pitch out of plane (R303).** Corners that do not lie on one plane cannot be one pitch: a module lies on a plane,
tilt and azimuth are of a plane, and a best-fit plane would leave every corner off its height, with gaps to the
neighbours and shadows of a roof that is not there. So the pitch is folded along a diagonal into planar parts (fold),
each a pitch of its own, with every corner exact: the energy reads the real tilt and azimuth of each part and the
shadows the real solid. Among the diagonals, the one that leaves planar parts, then the one that folds as a ridge
(water runs off; the other one would be a valley across the pitch), then the shortest. The largest part keeps the
place of the pitch among pitches() (a sub-field's reference stays), the others go after all the pitches. A
sub-field is laid only on its part (model.Project.fill).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from shapely.geometry import LineString, Polygon

from . import geo, roofs
from .i18n import _

TOUCH = 0.02            # m: sides this close, and corners this close, are the same line and the same point
SHARED_LEAST = 0.05     # m: two sides sharing less than this only touch
PLANAR = 0.005          # m: corners within this of a plane lie on it (the 5 mm of a roof's own tolerance)
MOVED = 0.01            # m: a pitch whose corners moved this much is said to have moved
LEVEL = 1e-5            # below this rise per metre a pitch is flat

EAVE_WEIGHT = 100.0     # an eave on the outside of the building stays at its height
FLAT_WEIGHT = 100.0     # a flat pitch stays flat
SLOPE_WEIGHT = 1.0      # a sloped pitch keeps its slope
LEVEL_WEIGHT = 1e-4     # the level of a flat pitch gives way first
INNER_EAVE_WEIGHT = 1e-1   # the eave of a sloped pitch on a shared line: a little firmer than a flat's level


@dataclass
class Fold:
    """A pitch out of plane and the lines it was folded along (plan points), what the window tells the designer."""
    pitch: int
    lines: list = field(default_factory=list)


@dataclass
class Resolved:
    pitches: list                 # roofs.Pitch: one for each free pitch in its place, then the other parts of the folded
    heights: list                 # for each free pitch, the height of each corner of its ring
    folds: list                   # Fold
    moved: list                   # the free pitches that joining moved from what their own numbers say


def _ccw(ring) -> list:
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1], strict=True))
    return list(ring) if area >= 0 else list(reversed(ring))


def shared_lines(rings) -> list[tuple]:
    """The lines two pitches share: (p, q, a, b) with p < q and the plan ends a, b. Two sides on one line within
    TOUCH, overlapping by SHARED_LEAST, with the pitches on either side of it: one pitch drawn over another is not its
    neighbour, and a contact at a point is not a shared line."""
    out = []
    ccw = [_ccw(r) for r in rings]
    for p, rp in enumerate(ccw):
        for q in range(p + 1, len(ccw)):
            rq = ccw[q]
            for a0, a1 in zip(rp, rp[1:] + rp[:1], strict=True):
                ex, ey = a1[0] - a0[0], a1[1] - a0[1]
                length = math.hypot(ex, ey)
                if length < 1e-9:
                    continue
                ux, uy = ex / length, ey / length
                for b0, b1 in zip(rq, rq[1:] + rq[:1], strict=True):
                    if (b1[0] - b0[0]) * ux + (b1[1] - b0[1]) * uy >= 0:      # the same way round: the same side
                        continue
                    if max(abs((c[0] - a0[0]) * uy - (c[1] - a0[1]) * ux) for c in (b0, b1)) > TOUCH:
                        continue
                    t0, t1 = sorted((c[0] - a0[0]) * ux + (c[1] - a0[1]) * uy for c in (b0, b1))
                    lo, hi = max(0.0, t0), min(length, t1)
                    if hi - lo >= SHARED_LEAST:
                        out.append((p, q, (a0[0] + ux * lo, a0[1] + uy * lo), (a0[0] + ux * hi, a0[1] + uy * hi)))
    return out


def _fit(points) -> tuple[tuple[float, float, float], float]:
    """The plane z = a x + b y + c nearest (x, y, z) points, and how far the farthest stays from it."""
    m = np.array([[x, y, 1.0] for x, y, _z in points])
    z = np.array([q[2] for q in points])
    coef = np.linalg.lstsq(m, z, rcond=None)[0]
    return (float(coef[0]), float(coef[1]), float(coef[2])), float(np.abs(m @ coef - z).max())


def _area(points) -> float:
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1], strict=True))) / 2


def fold(ring, heights) -> list[list[int]]:
    """A ring with a height at each corner cut into parts that lie on planes: lists of places in the ring. One part, the
    whole ring, when it lies on one plane already or no diagonal can cut it (it crosses itself)."""
    pts = [(float(p[0]), float(p[1]), float(z)) for p, z in zip(ring, heights, strict=True)]
    done: list[list[int]] = []

    def split(ids: list[int]) -> None:
        here = [pts[i] for i in ids]
        if len(ids) <= 3 or _fit(here)[1] <= PLANAR:
            done.append(ids)
            return
        shape = Polygon([q[:2] for q in here])
        if not shape.is_valid:
            done.append(ids)
            return
        inside = shape.buffer(1e-6)
        best, cut = None, None
        n = len(ids)
        for i in range(n):
            for j in range(i + 2, n):
                if i == 0 and j == n - 1:
                    continue
                if not inside.covers(LineString([here[i][:2], here[j][:2]])):
                    continue
                one, two = ids[i:j + 1], ids[j:] + ids[:i + 1]
                pa, pb = [pts[k] for k in one], [pts[k] for k in two]
                if _area(pa) < 1e-6 or _area(pb) < 1e-6:
                    continue
                (a, b, c), ra = _fit(pa)
                rb = _fit(pb)[1]
                off = max(0.0, ra - PLANAR) + max(0.0, rb - PLANAR)
                ridge = all(q[2] <= a * q[0] + b * q[1] + c + 1e-9 for q in pb)
                score = (round(off, 4), 0 if ridge else 1, math.dist(here[i][:2], here[j][:2]))
                if best is None or score < best:
                    best, cut = score, (one, two)
        if cut is None:
            done.append(ids)
            return
        split(cut[0])
        split(cut[1])
    split(list(range(len(pts))))
    return done


def pitch_of_plane(ring, plane, side=None, name: str = "") -> roofs.Pitch:
    """A roofs.Pitch for z = a x + b y + c on the ring."""
    a, b, c = plane
    x0, y0 = ring[0]
    z0 = a * x0 + b * y0 + c
    rise = math.hypot(a, b)
    if rise < LEVEL:
        return roofs.Pitch(list(ring), 0.0, 0.0, z0, x0, y0, side, name)
    azimuth = geo.bearing_to_azimuth(geo.bearing(-a / rise, -b / rise))     # the way water runs
    return roofs.Pitch(list(ring), math.degrees(math.atan(rise)), azimuth, z0, x0, y0, side, name)


def _plane_of(pitch: roofs.Pitch) -> tuple[float, float, float]:
    if pitch.tilt == 0:
        return 0.0, 0.0, pitch.z0
    fx, fy = geo.facing_vector(pitch.azimuth)
    t = math.tan(math.radians(pitch.tilt))
    return -fx * t, -fy * t, pitch.z0 + (pitch.x0 * fx + pitch.y0 * fy) * t


def _on_ring(ring, heights, point) -> float | None:
    """The height of a frozen pitch at a point of its outline: along the side it lies on, straight between the corners."""
    for (a, za), (b, zb) in zip(zip(ring, heights, strict=True), zip(ring[1:] + ring[:1], heights[1:] + heights[:1],
                                                                     strict=True), strict=True):
        length2 = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2
        if length2 < 1e-18:
            continue
        t = max(0.0, min(1.0, ((point[0] - a[0]) * (b[0] - a[0]) + (point[1] - a[1]) * (b[1] - a[1])) / length2))
        if math.dist(point, (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))) <= TOUCH:
            return za + t * (zb - za)
    return None


def _solve(rings, base, frozen, lines, detached) -> dict[int, tuple[float, float, float]]:
    """The planes of the pitches not frozen that have a neighbour: the least change from their own numbers, by the
    weights, under the condition that they meet on every shared line (the null space of the conditions, so that they
    hold exactly). Coordinates about the middle of the roof, for the numbers' sake."""
    active = sorted({k for p, q, _a, _b in lines for k in (p, q) if frozen[k] is None})
    if not active:
        return {}
    place = {k: i for i, k in enumerate(active)}
    all_points = [q for k in active for q in rings[k]]
    ox, oy = sum(q[0] for q in all_points) / len(all_points), sum(q[1] for q in all_points) / len(all_points)
    n = 3 * len(active)

    def row(k: int, x: float, y: float, sign: float = 1.0) -> dict:
        i = 3 * place[k]
        return {i: sign * (x - ox), i + 1: sign * (y - oy), i + 2: sign}

    conditions: list[tuple[dict, float]] = []
    wanted: list[tuple[dict, float]] = []
    for p, q, a, b in lines:
        for point in (a, b):
            if _is_detached(rings, detached, p, point) or _is_detached(rings, detached, q, point):
                continue
            if frozen[p] is None and frozen[q] is None:
                conditions.append(({**row(p, *point), **row(q, *point, -1.0)}, 0.0))
            elif frozen[p] is None or frozen[q] is None:
                free_k, held = (p, q) if frozen[p] is None else (q, p)
                z = _on_ring(rings[held], frozen[held], point)
                if z is not None:
                    conditions.append((row(free_k, *point), z))
    for k in active:
        pitch = base[k]
        i = 3 * place[k]
        size = math.sqrt(max(_area(rings[k]), 1e-6))
        a0, b0, _c0 = _plane_of(pitch)
        ring = rings[k]
        mid = (sum(q[0] for q in ring) / len(ring), sum(q[1] for q in ring) / len(ring))
        if pitch.tilt <= 0:
            wanted += [({i: FLAT_WEIGHT * size}, 0.0), ({i + 1: FLAT_WEIGHT * size}, 0.0)]
            wanted.append(({j: v * LEVEL_WEIGHT for j, v in row(k, *mid).items()}, LEVEL_WEIGHT * pitch.z(*mid)))
            continue
        wanted += [({i: SLOPE_WEIGHT * size}, SLOPE_WEIGHT * size * a0), ({i + 1: SLOPE_WEIGHT * size},
                                                                         SLOPE_WEIGHT * size * b0)]
        side = pitch.side or 0
        e0, e1 = ring[side], ring[(side + 1) % len(ring)]
        if _shared_share(e0, e1, k, lines) >= 0.5:
            weight = INNER_EAVE_WEIGHT
            middle = ((e0[0] + e1[0]) / 2, (e0[1] + e1[1]) / 2)
            wanted.append(({j: v * weight for j, v in row(k, *middle).items()}, weight * pitch.z(*middle)))
        else:
            for end in (e0, e1):
                wanted.append(({j: v * EAVE_WEIGHT for j, v in row(k, *end).items()}, EAVE_WEIGHT * pitch.z(*end)))

    def matrix(rows) -> tuple[np.ndarray, np.ndarray]:
        m = np.zeros((len(rows), n))
        r = np.zeros(len(rows))
        for line, (coef, value) in enumerate(rows):
            r[line] = value
            for j, v in coef.items():
                m[line, j] = v
        return m, r

    A, b = matrix(wanted)
    C, d = matrix(conditions)
    if len(conditions):
        x0 = np.linalg.lstsq(C, d, rcond=None)[0]
        _u, s, vt = np.linalg.svd(C)
        rank = int((s > 1e-9 * max(s.max(), 1.0)).sum())
        null = vt[rank:].T
        x = x0 if null.size == 0 else x0 + null @ np.linalg.lstsq(A @ null, b - A @ x0, rcond=None)[0]
    else:
        x = np.linalg.lstsq(A, b, rcond=None)[0]
    out = {}
    for k in active:
        i = 3 * place[k]
        aa, bb, cc = float(x[i]), float(x[i + 1]), float(x[i + 2])
        out[k] = (aa, bb, cc - aa * ox - bb * oy)
    return out


def _shared_share(a, b, k: int, lines) -> float:
    """How much of the side a-b of pitch k lies on shared lines, from 0 to 1."""
    length = math.dist(a, b)
    if length < 1e-9:
        return 0.0
    ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
    total = 0.0
    for p, q, s, e in lines:
        if k not in (p, q):
            continue
        if max(abs((c[0] - a[0]) * uy - (c[1] - a[1]) * ux) for c in (s, e)) > TOUCH:
            continue
        t0, t1 = sorted((c[0] - a[0]) * ux + (c[1] - a[1]) * uy for c in (s, e))
        total += max(0.0, min(length, t1) - max(0.0, t0))
    return min(1.0, total / length)


def _is_detached(rings, detached, k: int, point) -> bool:
    return any(p == k and j < len(rings[k]) and math.dist(rings[k][j], point) <= TOUCH for p, j in detached)


def _heights(ring, plane) -> list[float]:
    return [plane[0] * x + plane[1] * y + plane[2] for x, y in ring]


def _usable_heights(raw: dict, ring) -> list[float] | None:
    z = raw.get("z")
    return [float(v) for v in z] if isinstance(z, list) and len(z) == len(ring) else None


def resolve(free_pitches, joined: bool = True, detached=(), welds=()) -> Resolved:
    """The free pitches of a roof as pitches: joined when asked, each folded when its corners are off one plane. See
    the top of this module. `detached`: the corners ((pitch, place)) of pitches side by side that were parted; `welds`:
    the lists of corners made one point, one height whatever else changes (a slope written on one of the pitches):
    the height of a pitch by its corners if there is one among them, else their mean."""
    rings = [[(float(q[0]), float(q[1])) for q in f["ring"]] for f in free_pitches]
    base = [roofs.free(r, f["eave_side"], f["eave"], f["tilt"]) for r, f in zip(rings, free_pitches, strict=True)]
    frozen = [_usable_heights(f, r) for r, f in zip(rings, free_pitches, strict=True)]
    held = {(int(p), int(j)) for p, j in detached}
    lines = shared_lines(rings) if joined and len(rings) > 1 else []
    planes = _solve(rings, base, frozen, lines, held) if lines else {}
    heights: list[list[float]] = []
    for k, ring in enumerate(rings):
        if frozen[k] is not None:
            heights.append(list(frozen[k]))
        elif k in planes:
            heights.append(_heights(ring, planes[k]))
        else:
            heights.append([base[k].z(x, y) for x, y in ring])
    # a pitch not frozen between frozen ones may not find one plane through all they ask: their heights win, and it folds
    exact = [frozen[k] is not None for k in range(len(rings))]
    for p, q, a, b in lines:
        for k, other in ((p, q), (q, p)):
            if frozen[k] is not None or frozen[other] is None:
                continue
            for point in (a, b):
                if _is_detached(rings, held, k, point) or _is_detached(rings, held, other, point):
                    continue
                z = _on_ring(rings[other], frozen[other], point)
                if z is None:
                    continue
                for j, corner in enumerate(rings[k]):
                    if math.dist(corner, point) <= TOUCH and abs(heights[k][j] - z) > PLANAR:
                        heights[k][j] = z
                        exact[k] = True
    for weld in welds:
        members = [(int(i), int(j)) for i, j in weld if 0 <= i < len(rings) and 0 <= j < len(rings[i])]
        if len(members) < 2:
            continue
        held_z = [heights[i][j] for i, j in members if frozen[i] is not None]
        z = held_z[0] if held_z else sum(heights[i][j] for i, j in members) / len(members)
        for i, j in members:
            if abs(heights[i][j] - z) > PLANAR:
                heights[i][j] = z
                exact[i] = True
    out: list[roofs.Pitch] = []
    extra: list[roofs.Pitch] = []
    folds: list[Fold] = []
    moved: list[int] = []
    for k, ring in enumerate(rings):
        name = _("pitch {n}").format(n=k + 1)
        if not exact[k]:
            if k in planes and any(abs(z - base[k].z(x, y)) > 1e-6 for (x, y), z in zip(ring, heights[k], strict=True)):
                out.append(pitch_of_plane(ring, planes[k], None, name))
                if any(abs(z - base[k].z(x, y)) > MOVED for (x, y), z in zip(ring, heights[k], strict=True)):
                    moved.append(k)
            else:
                base[k].side, base[k].name = None, name
                out.append(base[k])
            continue
        points = [(x, y, z) for (x, y), z in zip(ring, heights[k], strict=True)]
        parts = fold(ring, heights[k])
        if len(parts) == 1:
            out.append(pitch_of_plane(ring, _fit(points)[0], None, name))
            continue
        parts.sort(key=lambda ids: -_area([ring[i] for i in ids]))
        made = [pitch_of_plane([ring[i] for i in ids], _fit([points[i] for i in ids])[0], None,
                               _("pitch {n}, part {m}").format(n=k + 1, m=m + 1)) for m, ids in enumerate(parts)]
        for pitch in made:
            pitch.whole = k
        out.append(made[0])
        extra += made[1:]
        folds.append(Fold(k, _fold_lines(ring, parts)))
    return Resolved(out + extra, heights, folds, moved)


def _fold_lines(ring, parts) -> list[tuple]:
    """The diagonals the parts share."""
    seen = []
    n = len(ring)
    for one in parts:
        for a, b in zip(one, one[1:] + one[:1], strict=True):
            if (a - b) % n not in (1, n - 1) and (b, a) not in seen and (a, b) not in seen:
                seen.append((a, b))
    return [(ring[a], ring[b]) for a, b in seen]
