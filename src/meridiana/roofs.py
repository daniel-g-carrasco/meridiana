"""Roof pitches: the planes a building's roof is made of, from its outline and a roof type.

A pitch (Pitch) is a plan polygon and a plane: tilt and azimuth by CEI 82-25 (the side the pitch faces,
which is the way water runs), its height at one plan point, the side of the outline it goes down to and its
name. Generated roofs:
- flat: one horizontal plane at the roof height;
- mono-pitch: one plane rising from a chosen eave side;
- gable and hip on any outline (task 16a): the straight skeleton (skeleton.py), one pitch for each eave side in
  the order of the sides, none for a gable end; a gable roof has its gable ends where the designer says, by
  default at the ends of its arms (default_gables), a hip roof has none unless the designer says;
- a free pitch: an outline the designer draws, with its eave side and its slope.
The slope can be given in degrees, in percent, or by the eave and ridge heights: given, the ridge wins and the
slope is worked out from it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from shapely.geometry import Polygon

from . import geo, skeleton
from .i18n import _

# The slope proposed for a new pitched roof, by what covers it, in percent (Daniel, 23/10/2026: 35 %, and the
# covering changes it; study 16, A.8). Clay: ANDIL, Manuale coperture in laterizio 2025, p. 7 («35 % pendenza
# minima marsigliesi», «30 % pendenza minima», «< 30 % pendenza sconsigliata»). Metal and sandwich panels: 7 %,
# the producers' sheets (Isopan Isocop, study 16, A.8). Proposals, to be changed by the designer.
COVERINGS = {"tiles": 35.0, "pantiles": 30.0, "metal": 7.0}
DEFAULT_COVERING = "tiles"


def covering_names() -> dict:
    return {"tiles": _("Marseille tiles"), "pantiles": _("Clay pantiles (coppi)"), "metal": _("Metal or sandwich panels")}


def covering_source(covering: str) -> str:
    """Where the slope proposed for a covering comes from."""
    if covering == "metal":
        return _("the producers' sheets of sandwich panels (Isopan), study 16 A.8")
    return _("ANDIL, Manuale coperture in laterizio 2025, p. 7")


def proposed_tilt(covering: str = DEFAULT_COVERING) -> float:
    """The slope proposed for a covering, in degrees."""
    return slope_from_percent(COVERINGS.get(covering, COVERINGS[DEFAULT_COVERING]))


@dataclass
class Pitch:
    ring: list[tuple[float, float]]
    tilt: float
    azimuth: float
    z0: float
    x0: float
    y0: float
    side: int | None = None       # the side of the outline the pitch goes down to (its eave), if it has one
    name: str = ""
    whole: int | None = None      # a part of a free pitch folded out of plane (roof_join): the place of that pitch

    def z(self, x: float, y: float) -> float:
        if self.tilt == 0:
            return self.z0
        fx, fy = geo.facing_vector(self.azimuth)
        return self.z0 - ((x - self.x0) * fx + (y - self.y0) * fy) * math.tan(math.radians(self.tilt))

    def corners_3d(self) -> list[tuple[float, float, float]]:
        return [(x, y, self.z(x, y)) for x, y in self.ring]


def slope_from_percent(percent: float) -> float:
    return math.degrees(math.atan(percent / 100.0))


def slope_from_heights(eave: float, ridge: float, run: float) -> float:
    """Tilt of a plane rising from `eave` to `ridge` height over a horizontal `run`."""
    if run <= 0:
        raise ValueError("the run must be positive")
    return math.degrees(math.atan((ridge - eave) / run))


def side_name(side: int) -> str:
    return _("pitch of side {n}").format(n=side + 1)


def _outward_azimuth(a, b, inside) -> float:
    """CEI azimuth of the outward normal of side a-b of a polygon containing `inside`."""
    ex, ey = b[0] - a[0], b[1] - a[1]
    nx, ny = ey, -ex
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    if (inside[0] - mx) * nx + (inside[1] - my) * ny > 0:
        nx, ny = -nx, -ny
    return geo.bearing_to_azimuth(geo.bearing(nx, ny))


def flat(footprint, height: float) -> list[Pitch]:
    ring = [tuple(map(float, p)) for p in footprint]
    return [Pitch(ring, 0.0, 0.0, height, ring[0][0], ring[0][1], None, _("flat roof"))]


def flat_plane(footprint, heights) -> list[Pitch]:
    """A flat roof on one inclined plane (R455, format 28): the plane through the corners at `heights` (one for each
    corner, least squares when they are more than three), as one pitch; level when it is."""
    import numpy as np
    ring = [tuple(map(float, p)) for p in footprint]
    pts = np.asarray(ring, float)
    zs = np.asarray([float(z) for z in heights], float)
    origin = pts.mean(0)
    rows = np.column_stack([pts[:, 0] - origin[0], pts[:, 1] - origin[1], np.ones(len(pts))])
    a, b, c = np.linalg.lstsq(rows, zs, rcond=None)[0]
    tilt = math.degrees(math.atan(math.hypot(a, b)))
    if tilt < 1e-4:
        return flat(footprint, float(zs.min()))
    azimuth = geo.bearing_to_azimuth(geo.bearing(-a, -b))        # it faces downhill
    x0, y0 = ring[0]
    z0 = float(a * (x0 - origin[0]) + b * (y0 - origin[1]) + c)
    return [Pitch(ring, round(tilt, 4), round(azimuth, 4), z0, x0, y0, None, _("flat roof"))]


SADDLE_DEFAULTS = {"direction": 0.0, "band": 2.5, "tilt": 10.0, "channel": 0.6, "depth": 0.15, "offset": 0.0}


def saddle_spec(spec: dict | None) -> dict:
    """The parameters of a saddle roof with their defaults where not given, kept within sense."""
    out = {**SADDLE_DEFAULTS, **{k: float(v) for k, v in (spec or {}).items() if k in SADDLE_DEFAULTS}}
    out["band"] = max(out["band"], 0.2)
    out["channel"] = max(out["channel"], 0.0)
    out["tilt"] = min(max(out["tilt"], 0.0), 80.0)
    out["depth"] = max(out["depth"], 0.0)
    return out


def saddles(footprint, height: float, spec: dict | None = None) -> list[Pitch]:
    """A roof of saddle-backed bands (R455, format 28): parallel bands `band` m wide, each with two pitches falling
    from its ridge (at `height`) to its edges at `tilt`, parted by level drainage channels `channel` m wide and
    `depth` m under the bands' edges. `direction` is the bearing of the bands' axis (degrees from North), `offset`
    slides the pattern along the normal. The pattern starts at the outline's upstream side and repeats across it."""
    import shapely
    s = saddle_spec(spec)
    ring = [tuple(map(float, p)) for p in footprint]
    poly = Polygon(ring)
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty or poly.area < 1e-6:
        return flat(footprint, height)
    d = math.radians(s["direction"])
    ux, uy = math.sin(d), math.cos(d)             # along the bands
    nx, ny = math.cos(d), -math.sin(d)            # across them, to their right
    along = [x * ux + y * uy for x, y in ring]
    across = [x * nx + y * ny for x, y in ring]
    lo, hi = min(across), max(across)
    t0, t1 = min(along) - 1.0, max(along) + 1.0
    period = s["band"] + s["channel"]
    start = lo + (s["offset"] % period if period > 0 else 0.0) - period
    drop = s["band"] / 2.0 * math.tan(math.radians(s["tilt"]))

    def strip(a, b):
        return Polygon([(a * nx + t0 * ux, a * ny + t0 * uy), (b * nx + t0 * ux, b * ny + t0 * uy),
                        (b * nx + t1 * ux, b * ny + t1 * uy), (a * nx + t1 * ux, a * ny + t1 * uy)])

    def pieces(shape):
        for g in getattr(shape, "geoms", [shape]):
            if g.geom_type == "Polygon" and g.area > 0.05:
                r = [(float(x), float(y)) for x, y in list(g.exterior.coords)[:-1]]
                if len(r) >= 3:
                    yield r if _area2(r) > 0 else r[::-1]

    out = []
    k = 0
    at = start
    while at < hi + 1e-9:
        b0, b1 = at, at + s["band"]
        mid = (b0 + b1) / 2.0
        band = poly.intersection(strip(b0, b1))
        if not band.is_empty:
            k += 1
            for half, (facing, where) in enumerate(((( -nx, -ny), strip(b0, mid)), ((nx, ny), strip(mid, b1)))):
                for r in pieces(band.intersection(where)):
                    c = Polygon(r).representative_point()
                    sc = c.x * nx + c.y * ny
                    x0, y0 = c.x + (mid - sc) * nx, c.y + (mid - sc) * ny        # a point on the ridge line
                    azimuth = geo.bearing_to_azimuth(geo.bearing(*facing))
                    name = _("band {n}, {side}").format(n=k, side=_("left") if half == 0 else _("right"))
                    out.append(Pitch(r, s["tilt"], round(azimuth, 4), height, x0, y0, None, name))
        if s["channel"] > 0:
            for r in pieces(poly.intersection(strip(b1, b1 + s["channel"]))):
                out.append(Pitch(r, 0.0, 0.0, height - drop - s["depth"], r[0][0], r[0][1], None,
                                 _("channel {n}").format(n=k)))
        at += period if period > 0 else s["band"]
    return out or flat(footprint, height)


def _area2(ring) -> float:
    return sum(ring[i][0] * ring[(i + 1) % len(ring)][1] - ring[(i + 1) % len(ring)][0] * ring[i][1]
               for i in range(len(ring)))


def mono(footprint, eave_side: int, eave: float, tilt: float) -> list[Pitch]:
    """One plane: down towards side `eave_side` (index of the side from vertex i to i+1)."""
    ring = [tuple(map(float, p)) for p in footprint]
    side = eave_side % len(ring)
    a, b = ring[side], ring[(side + 1) % len(ring)]
    c = Polygon(ring).representative_point()
    alpha = _outward_azimuth(a, b, (c.x, c.y))
    return [Pitch(ring, tilt, round(alpha, 4), eave, a[0], a[1], side, side_name(side))]


def _turn(ring, i: int) -> float:
    """The turn at corner i of a ring, positive where it turns the way the ring goes round (an outer corner)."""
    n = len(ring)
    p, a, q = ring[i - 1], ring[i], ring[(i + 1) % n]
    cross = (a[0] - p[0]) * (q[1] - a[1]) - (a[1] - p[1]) * (q[0] - a[0])
    area = sum(u[0] * v[1] - v[0] * u[1] for u, v in zip(ring, ring[1:] + ring[:1], strict=True))
    return cross if area > 0 else -cross


def outer_side(ring, side: int) -> bool:
    """A side between two outer corners: the end of an arm, where a gable end stands."""
    ring = [tuple(map(float, p)) for p in ring]
    return _turn(ring, side) > 0 and _turn(ring, (side + 1) % len(ring)) > 0


def _corner_count(face) -> int:
    """The corners of a face, without the points in line with their neighbours."""
    pts = [p[:2] for p in face]
    count = 0
    for k in range(len(pts)):
        a, b, c = pts[k - 1], pts[k], pts[(k + 1) % len(pts)]
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cross) > 1e-6 * max(math.dist(a, c), 1e-9):
            count += 1
    return count


def default_gables(footprint) -> set[int]:
    """Where a gable roof has its gable ends unless the designer says otherwise (Daniel, 23/10/2026: on an L,
    on the two arms): the sides between two outer corners whose face of the hip roof is a triangle, the ends of
    the arms. When every face is one (a square, a regular outline) every other one, so that two eaves at least
    are left. Empty when the skeleton cannot be built."""
    ring = [tuple(map(float, p)) for p in footprint]
    try:
        faces = skeleton.faces(ring)
    except skeleton.SkeletonError:
        return set()
    ends = [i for i, f in enumerate(faces) if f is not None and _corner_count(f) == 3 and outer_side(ring, i)]
    if len([f for f in faces if f is not None]) - len(ends) < 2:
        ends = ends[1::2]
    return set(ends)


def _covers(ring, faces) -> bool:
    shapes = [Polygon([p[:2] for p in f]) for f in faces if f is not None]
    area = Polygon(ring).area
    return all(s.is_valid for s in shapes) and abs(sum(s.area for s in shapes) - area) <= 1e-3 * area


def pitched(footprint, eave: float, tilt: float, gables=frozenset(), ridge: float | None = None
            ) -> tuple[list[Pitch], set[int]]:
    """The pitches of a gable or hip roof on any outline, all of the same slope: one for each eave side, in the
    order of the sides, named after it; none for a gable end. `ridge`, when given above the eave, is the height
    of the ridge: the slope is the one that brings the highest point of the roof there and `tilt` is not used.
    A gable end the skeleton cannot take (a side beside an inner corner, in some outlines) becomes an eave: the
    second value says which. SkeletonError for an outline the skeleton cannot be built on (crossing itself)."""
    ring = [tuple(map(float, p)) for p in footprint]
    asked = {int(i) for i in gables}
    error: skeleton.SkeletonError | None = None
    faces = None
    for used in (asked, {i for i in asked if outer_side(ring, i)}, set()):
        try:
            found = skeleton.roof(ring, used)
        except skeleton.SkeletonError as e:
            error = e
            continue
        if _covers(ring, found):
            faces = found
            break
        error = skeleton.SkeletonError("the faces do not cover the footprint")
    if faces is None:
        raise error or skeleton.SkeletonError("no roof")
    if ridge is not None:
        run = max((h for f in faces if f is not None for _x, _y, h in f), default=0.0)
        if run > 0 and ridge > eave:
            tilt = slope_from_heights(eave, ridge, run)
    out = []
    for side, face in enumerate(faces):
        if face is None:
            continue
        pts = [(x, y) for x, y, _h in face]
        (ax, ay), (bx, by) = pts[0], pts[1]
        alpha = geo.bearing_to_azimuth(geo.bearing(by - ay, -(bx - ax)))    # faces run counter-clockwise
        out.append(Pitch(pts, tilt, round(alpha, 4), eave, ax, ay, side, side_name(side)))
    return out, asked - used


def gable(footprint, eave: float, tilt: float, gables=None) -> list[Pitch]:
    """Two pitches meeting on a ridge, or more on an outline that is not a rectangle: the gable ends on `gables`
    (sides), or where default_gables puts them."""
    return pitched(footprint, eave, tilt, default_gables(footprint) if gables is None else gables)[0]


def hip(footprint, eave: float, tilt: float) -> list[Pitch]:
    """A pitch for every side, all of the same slope."""
    return pitched(footprint, eave, tilt)[0]


def ridge_height(pitches) -> float:
    """The height of the highest point of a roof."""
    return max((z for p in pitches for _x, _y, z in p.corners_3d()), default=0.0)


def ridges(pitches, eave: float) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """The ridges of a roof: the level edges of its pitches above the eave, each once, at the highest level
    first. The plan shows them when the pointer passes over the roof."""
    seen: dict = {}
    for p in pitches:
        if p.tilt <= 0:
            continue
        ring = p.ring
        for a, b in zip(ring, ring[1:] + ring[:1], strict=True):
            za, zb = p.z(*a), p.z(*b)
            if abs(za - zb) < 1e-6 and za > eave + 1e-6 and math.dist(a, b) > 1e-6:
                key = tuple(sorted(((round(a[0], 6), round(a[1], 6)), (round(b[0], 6), round(b[1], 6)))))
                seen.setdefault(key, (za, (tuple(a), tuple(b))))
    return [seg for _z, seg in sorted(seen.values(), key=lambda v: -v[0])]


def free(ring, eave_side: int, eave: float, tilt: float) -> Pitch:
    """A pitch the designer drew: the plane goes down towards side `eave_side`, at height `eave` there."""
    return mono(ring, eave_side, eave, tilt)[0]


# A free pitch by its numbers (R274, study 22, 3.4): its depth from the eave, the ridge it reaches, the slope a
# ridge written gives, the side across from the eave (the eave and the ridge swapped). The ridge is derived:
# the file keeps ring, eave side, eave and slope only.

def _side_ends(ring, side: int):
    ring = [tuple(map(float, p)) for p in ring]
    return ring, ring[side % len(ring)], ring[(side + 1) % len(ring)]


def free_depth(ring, eave_side: int) -> float:
    """How far a free pitch runs from its eave, in plan: the distance of its farthest corner from the eave's line."""
    ring, a, b = _side_ends(ring, eave_side)
    length = math.dist(a, b)
    if length < 1e-9:
        return 0.0
    return max(abs((p[0] - a[0]) * (b[1] - a[1]) - (p[1] - a[1]) * (b[0] - a[0])) / length for p in ring)


def free_ridge(ring, eave_side: int, eave: float, tilt: float) -> float:
    """The height of the top of a free pitch: the eave plus its depth at its slope."""
    return eave + free_depth(ring, eave_side) * math.tan(math.radians(tilt))


def free_tilt(ring, eave_side: int, eave: float, ridge: float) -> float:
    """The slope that brings a free pitch from `eave` to `ridge` over its depth; ValueError, said for the designer,
    for a ridge not above the eave or a pitch without depth."""
    if ridge <= eave + 1e-3:
        from .i18n import number
        raise ValueError(_("the ridge must stand above the eave ({h} m)").format(h=number(eave)))
    depth = free_depth(ring, eave_side)
    if depth <= 1e-6:
        raise ValueError(_("the pitch has no depth"))
    return slope_from_heights(eave, ridge, depth)


def free_keeping_ridge(ring, eave_side: int, eave: float, tilt: float, *, new_eave: float | None = None,
                       new_tilt: float | None = None) -> tuple[float, float]:
    """A free pitch with its ridge kept (R413): (eave, slope) after the eave or the slope is written. A pitch lying flat
    has no ridge of its own, and its eave moves alone. ValueError, said for the designer, when they cannot meet."""
    ridge = free_ridge(ring, eave_side, eave, tilt)
    if new_eave is not None:
        return (new_eave, tilt) if tilt <= 0 else (new_eave, free_tilt(ring, eave_side, new_eave, ridge))
    if tilt <= 0 and new_tilt > 0:
        return eave, new_tilt
    return eave_keeping_ridge(ridge, free_depth(ring, eave_side), new_tilt), new_tilt


def eave_keeping_ridge(ridge: float, run: float, tilt: float) -> float:
    """The eave of a roof of `run` metres from eave to top, its top kept at `ridge`, at the slope `tilt`. ValueError, said
    for the designer, when the eave would go under the ground."""
    eave = ridge - run * math.tan(math.radians(tilt))
    if eave < 0:
        raise ValueError(_("with the ridge kept at {h} m this slope takes the eave under the ground").format(h=round(ridge, 2)))
    return round(eave, 3)


def opposite_side(ring, side: int) -> int:
    """The side across from `side`: the one whose middle lies farthest from its line (on a rectangle, the side
    parallel to it). Where the eave goes when eave and ridge are swapped."""
    ring, a, b = _side_ends(ring, side)
    n = len(ring)
    length = math.dist(a, b) or 1.0

    def far(i):
        p, q = ring[i], ring[(i + 1) % n]
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        return abs((mx - a[0]) * (b[1] - a[1]) - (my - a[1]) * (b[0] - a[0])) / length
    return max((i for i in range(n) if i != side % n), key=far)


def free_spec(ring, swapped: bool, eave: float, tilt: float, ridge: float | None = None) -> dict:
    """A free pitch drawn from its first side, as the file keeps it: the eave on that side, or across from it
    when eave and ridge are swapped (Tab); the slope `tilt`, or the one a `ridge` height gives (ValueError at or
    under the eave)."""
    ring = [[float(x), float(y)] for x, y in ring]
    side = opposite_side(ring, 0) if swapped else 0
    if ridge is not None:
        tilt = free_tilt(ring, side, eave, ridge)
    return {"ring": ring, "eave_side": side, "eave": float(eave), "tilt": float(tilt)}


# The roof from its ridge (R275, study 22, 3.5): the designer draws the ridge, the sides its points touch become
# gable ends, the others eaves, and the straight skeleton makes the roof. The ridge stands on the building's axis
# (Daniel, 31/10/2026, decision 4): a ridge drawn off it is said, not followed (pitches of different slope would
# need a weighted skeleton, study 22 L6b).

CROSSING = 30.0            # degrees: a side within this of the ridge's direction runs along it, beyond it crosses it


@dataclass
class RidgeRoof:
    kind: str                          # "gable" with a gable end at least, "hip" without
    edges: list[str]                   # "eave" or "gable" for each side of the outline, as Roof.edges
    pitches: list[Pitch]
    off_axis: bool                     # the ridge drawn is not where the roof's stands
    dropped: list[int]                 # gable ends asked that the outline cannot take (they are eaves)


def _segment_distance(p, a, b) -> float:
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    d2 = dx * dx + dy * dy
    t = 0.0 if d2 < 1e-18 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / d2))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def _angle(u, v) -> float:
    """The angle between two directions, 0-90 degrees, whichever way each one goes."""
    a = abs(math.degrees(math.atan2(u[1], u[0]) - math.atan2(v[1], v[0]))) % 180.0
    return min(a, 180.0 - a)


def ridge_gables(footprint, points) -> set[int]:
    """The sides a drawn ridge touches: for each point of it, the nearest side crossing the ridge there when it
    is nearer than half the distance to the sides running along it (on the axis of a rectangle, within a
    quarter of its width from the end). A point inside, an L's corner, touches nothing: a ridge ending inside
    the outline makes a hip there."""
    ring = [tuple(map(float, p)) for p in footprint]
    pts = [tuple(map(float, p)) for p in points]
    n = len(ring)
    out: set[int] = set()
    for k, p in enumerate(pts):
        dirs = [(q[0] - p[0], q[1] - p[1]) for q in (pts[k - 1] if k > 0 else None, pts[k + 1] if k + 1 < len(pts)
                                                     else None) if q is not None and math.dist(p, q) > 1e-6]
        if not dirs:
            continue
        side_dirs = [(ring[(i + 1) % n][0] - ring[i][0], ring[(i + 1) % n][1] - ring[i][1]) for i in range(n)]
        dist = [_segment_distance(p, ring[i], ring[(i + 1) % n]) for i in range(n)]
        for u in dirs:
            along = [dist[i] for i in range(n) if _angle(side_dirs[i], u) <= CROSSING]
            across = [i for i in range(n) if _angle(side_dirs[i], u) > CROSSING]
            if not across:
                continue
            near = min(across, key=lambda i: dist[i])
            if not along or dist[near] <= 0.5 * min(along):
                out.add(near)
    return out


def from_ridge(footprint, points, eave: float, tilt: float, ridge: float | None = None) -> RidgeRoof:
    """The roof a drawn ridge stands for: gable ends where its points touch the outline (ridge_gables), the
    others eaves, built by the straight skeleton at `tilt`, or at the slope that brings its top to `ridge`.
    SkeletonError when the outline cannot carry a pitched roof (it crosses itself)."""
    ring = [tuple(map(float, p)) for p in footprint]
    pts = [tuple(map(float, p)) for p in points]
    asked = ridge_gables(ring, pts)
    found, dropped = pitched(ring, eave, tilt, asked, ridge)
    used = asked - dropped
    edges = ["gable" if i in used else "eave" for i in range(len(ring))]
    tolerance = max(0.15, 0.03 * math.sqrt(Polygon(ring).area))
    roof_ridges = ridges(found, eave)
    off = False
    for a, b in zip(pts, pts[1:], strict=False):
        if math.dist(a, b) <= tolerance:
            continue
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        near = min(roof_ridges, key=lambda s: _segment_distance(mid, *s), default=None)
        if near is None or _segment_distance(mid, *near) > tolerance or \
                _angle((b[0] - a[0], b[1] - a[1]), (near[1][0] - near[0][0], near[1][1] - near[0][1])) > 10.0:
            off = True
    return RidgeRoof("gable" if used else "hip", edges, found, off, sorted(dropped))


def off_axis_pitches(footprint, points, eave: float, ridge: float | None, tilt: float) -> list[dict] | None:
    """A ridge drawn off the axis of a four-sided outline, where it is drawn (R410, Daniel 05/11/2026): the two pitches
    along it from their eaves to the ridge, each with its own slope, and a hip's triangle where it ends inside the
    outline. As free pitches written by the heights of their corners. None when the ridge is not one segment across
    such an outline: there the roof stays on the axis, and it is said."""
    ring = [tuple(map(float, p)) for p in footprint]
    pts = [tuple(map(float, p)) for p in points]
    if len(ring) != 4 or len(pts) != 2 or math.dist(*pts) < 1e-6:
        return None
    if not Polygon(ring).exterior.is_ccw:       # the pitches run counter-clockwise whichever way it was drawn
        ring.reverse()
    a, b = pts
    u = (b[0] - a[0], b[1] - a[1])
    across = [i for i in range(4) if _angle((ring[(i + 1) % 4][0] - ring[i][0], ring[(i + 1) % 4][1] - ring[i][1]), u) > CROSSING]
    if len(across) != 2 or (across[1] - across[0]) % 4 != 2:
        return None

    def nearest(p):
        return min(across, key=lambda i: _segment_distance(p, ring[i], ring[(i + 1) % 4]))
    start, end = nearest(a), nearest(b)
    if start == end:
        return None

    def hit(p, side):
        """Where the ridge's line meets a side it reaches."""
        q, r = ring[side], ring[(side + 1) % 4]
        v = (r[0] - q[0], r[1] - q[1])
        det = u[0]*v[1] - u[1]*v[0]
        t = ((q[0] - p[0])*v[1] - (q[1] - p[1])*v[0]) / det
        return (p[0] + t*u[0], p[1] + t*u[1])
    gables = ridge_gables(ring, pts)
    p = hit(a, start) if start in gables else a
    q = hit(b, end) if end in gables else b
    if ridge is None:
        ridge = eave + ridge_run(ring) * math.tan(math.radians(tilt))
    if ridge <= eave:
        return None
    faces = []

    def face(corners, heights):
        i = len(faces)
        faces.append({"id": f"p{i + 1}", "ring": [[float(x), float(y)] for x, y in corners], "eave_side": 0,
                      "eave": float(eave), "tilt": float(tilt), "z": [round(float(z), 3) for z in heights]})
    after_start, after_end = (start + 1) % 4, (end + 1) % 4
    # The two long sides run from the side the ridge starts at to the one where it ends, and back.
    face([ring[after_start], ring[(after_start + 1) % 4], q, p], [eave, eave, ridge, ridge])
    face([ring[after_end], ring[(after_end + 1) % 4], p, q], [eave, eave, ridge, ridge])
    if start not in gables:
        face([ring[start], ring[(start + 1) % 4], p], [eave, eave, ridge])
    if end not in gables:
        face([ring[end], ring[(end + 1) % 4], q], [eave, eave, ridge])
    return faces


def ridge_run(footprint) -> float:
    """The largest horizontal run of a pitched roof on the outline, from an eave to the top (half the width of a
    rectangle): what a proposed slope multiplies to give the ridge's height. 0 when no roof can be built."""
    try:
        return ridge_height(pitched(footprint, 0.0, 45.0)[0])
    except skeleton.SkeletonError:
        return 0.0


def axis_bearing(a, b) -> float:
    """The bearing (degrees from North, 0 to 180) of the line from `a` to `b` traced on the plan: the way the bands of
    a saddle roof run when the designer draws it. ValueError for two points closer than 10 cm."""
    dx, dy = float(b[0]) - float(a[0]), float(b[1]) - float(a[1])
    if math.hypot(dx, dy) < 0.1:
        raise ValueError(_("trace a line at least 10 cm long"))
    return round(geo.bearing(dx, dy) % 180.0, 2)


def long_side_bearing(footprint) -> float:
    """The bearing (degrees from North) of the longest side of an outline: the way the bands of a saddle roof run by
    default."""
    ring = [tuple(map(float, p)) for p in footprint]
    if len(ring) < 2:
        return 0.0
    a, b = max(zip(ring, ring[1:] + ring[:1], strict=True), key=lambda ab: math.dist(*ab))
    return round(geo.bearing(b[0] - a[0], b[1] - a[1]) % 180.0, 2)
