"""Where an imported IFC model goes on the plan (R454, Daniel 06/11/2026: «li inserisca direttamente al centro della
mappa non mi piace molto, perché io avevo già fatto una prima modellazione e il programma me l'ha sovrapposto»).
No Qt: the plan collects the gestures (quick/backend/plan_place.py), this module does the arithmetic.

The import (ifc_import.plan) lays the model's world on the plan by a frame: turned by `theta` about the model's
`origin`, then moved by `shift` (ifc_import.Frame, kept in Plan.reference). A `Placement` moves that whole lay rigidly:
the model's origin goes to `at` on the plan and everything turns by `turn` degrees anticlockwise more. A point the
import put at p goes to R(turn) (p - base) + at, `base` being where the import put the model's origin.

What follows from it:
- the bodies keep their quota of base and their heights (absolute on the ground, `Building.base`, `on`), and stay one
  group (`Building.group`, ifc_import.apply): moved or turned later they move together;
- `placed` gives the plan with every outline moved and its reference composed (theta - turn, shift = at), so the
  exports in the frame of the imported file (ifc_export.frame_of, dxf_export) still lie on the architect's model;
- `follow`, `snap` and `turned` are the mouse: the middle of the model under the pointer, a corner of the model on a
  corner or a side of a building already drawn (or a corner of a building on a side of the model), the wheel and R
  turning it about its middle;
- `values` and `from_values` are the coordinates: the model's origin in UTM, latitude and longitude, or metres East
  and North of the site, with the turn; `proposal` is the file's own georeferencing (IfcMapConversion, a named
  IfcSite), the first choice when there is one; `distance_km` and `far` the warning beyond ifc_import.FAR_KM;
- `overlaps`, `beside` and `apply(..., replace=...)`: a model that falls on buildings already drawn replaces them
  (the sub-fields drawn on them go to the new body under them), stands beside them, or is kept with them."""

from __future__ import annotations

import copy
import math
from collections.abc import Callable
from dataclasses import dataclass

from . import geo, model, move
from .i18n import _, number
from .ifc_import import FAR_KM, Place, Plan, apply as _apply_plan, problem

OVERLAP_M2 = 1.0            # m2 shared with a building already drawn: less is a touch, not an overlap
GAP = 1.0                   # m between the model and the buildings it is laid beside
SNAP_PX = 12                # screen pixels within which a corner or a side takes the model
SYSTEMS = ("utm", "latlon", "local")
TURN_STEPS = move.ANGLE_STEPS   # the wheel and R: 15 degrees, 5 with Ctrl, 90 with Shift


@dataclass(frozen=True)
class Placement:
    """Where the model is: its origin at `at` on the plan, turned `turn` degrees anticlockwise from where the import
    laid it; `base` is where the import put the origin (Plan.reference["shift"])."""
    at: tuple = (0.0, 0.0)
    turn: float = 0.0
    base: tuple = (0.0, 0.0)


def start(plan: Plan) -> Placement:
    """The model where the import laid it."""
    shift = (plan.reference or {}).get("shift") or (0.0, 0.0)
    base = (float(shift[0]), float(shift[1]))
    return Placement(at=base, turn=0.0, base=base)


def mapping(pl: Placement) -> Callable[[float, float], tuple[float, float]]:
    a = math.radians(pl.turn)
    c, s = math.cos(a), math.sin(a)
    (bx, by), (ax, ay) = pl.base, pl.at
    return lambda x, y: (ax + c * (x - bx) - s * (y - by), ay + s * (x - bx) + c * (y - by))


def _turn_vector(x: float, y: float, degrees: float) -> tuple[float, float]:
    a = math.radians(degrees)
    return math.cos(a) * x - math.sin(a) * y, math.sin(a) * x + math.cos(a) * y


def shapes(plan: Plan) -> list[tuple[str, list]]:
    """What the plan shows of the model while it is placed, where the import laid it: each body's outline, its roof
    planes, the obstacles and the supports (kind, ring). Made once: the placement moves them."""
    out = []
    for b in plan.buildings:
        out.append(("building", [tuple(map(float, q)) for q in b.footprint]))
        try:
            pitches = b.pitches()
        except (ValueError, ArithmeticError):
            pitches = []
        out += [("roof", [tuple(map(float, q)) for q in p.ring]) for p in pitches if len(p.ring) >= 3]
    out += [("exclusion", [tuple(map(float, q)) for q in e.ring]) for e, _host in plan.exclusions]
    out += [("support", [tuple(map(float, q)) for q in sf.ring]) for sf, _host in plan.supports]
    return out


def middle(plan: Plan) -> tuple[float, float]:
    """The middle of the bodies' outlines together (of their bounding box), where the import laid them: the point
    the pointer holds and the model turns about."""
    pts = [q for b in plan.buildings for q in b.footprint] or [q for sf, _h in plan.supports for q in sf.ring]
    if not pts:
        return (0.0, 0.0)
    xs, ys = [float(q[0]) for q in pts], [float(q[1]) for q in pts]
    return ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)


def moved(rings: list, pl: Placement) -> list:
    f = mapping(pl)
    return [(kind, [f(x, y) for x, y in ring]) for kind, ring in rings]


def follow(plan: Plan, pl: Placement, pointer, grab=None) -> Placement:
    """The placement that puts the model's middle (or `grab`, a point of the model where the import laid it) under
    the pointer."""
    gx, gy = grab if grab is not None else middle(plan)
    rx, ry = _turn_vector(gx - pl.base[0], gy - pl.base[1], pl.turn)
    return Placement(at=(float(pointer[0]) - rx, float(pointer[1]) - ry), turn=pl.turn, base=pl.base)


def turned(plan: Plan, pl: Placement, degrees: float) -> Placement:
    """The model turned by `degrees` anticlockwise about its middle."""
    cx, cy = mapping(pl)(*middle(plan))
    dx, dy = _turn_vector(pl.at[0] - cx, pl.at[1] - cy, degrees)
    return Placement(at=(cx + dx, cy + dy), turn=round((pl.turn + degrees + 180.0) % 360.0 - 180.0, 9), base=pl.base)


def shifted(pl: Placement, dx: float, dy: float) -> Placement:
    return Placement(at=(pl.at[0] + dx, pl.at[1] + dy), turn=pl.turn, base=pl.base)


def _sides(rings):
    for ring in rings:
        pts = [tuple(map(float, q)) for q in ring]
        yield from zip(pts, pts[1:] + pts[:1], strict=True)


def _foot(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    n2 = dx * dx + dy * dy
    t = 0.0 if n2 < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n2))
    return a[0] + t * dx, a[1] + t * dy


@dataclass(frozen=True)
class Snap:
    dx: float = 0.0
    dy: float = 0.0
    kind: str = ""              # "corner", "side" or "" (nothing near)
    point: tuple | None = None  # where the model touches the building


def snap(project: model.Project, outlines: list, reach: float, skip=()) -> Snap:
    """The shift that lays the model's outlines (`outlines`, on the plan now) on the buildings already drawn: a corner
    of the model on a corner of a building within `reach` metres, else a corner on a side (or a building's corner on a
    side of the model). The nearest wins; nothing within reach is Snap()."""
    targets = [b.footprint for b in project.buildings if b.id not in skip and len(b.footprint) >= 3]
    if not targets or not outlines or reach <= 0:
        return Snap()
    mine = [q for ring in outlines for q in ring]
    theirs = [tuple(map(float, q)) for ring in targets for q in ring]
    best = None
    for p in mine:
        for q in theirs:
            d = math.hypot(q[0] - p[0], q[1] - p[1])
            if d <= reach and (best is None or d < best[0]):
                best = (d, q[0] - p[0], q[1] - p[1], q)
    if best is not None:
        return Snap(best[1], best[2], "corner", best[3])
    for p in mine:
        for a, b in _sides(targets):
            q = _foot(p, a, b)
            d = math.hypot(q[0] - p[0], q[1] - p[1])
            if d <= reach and (best is None or d < best[0]):
                best = (d, q[0] - p[0], q[1] - p[1], q)
    for q in theirs:
        for a, b in _sides(outlines):
            p = _foot(q, a, b)
            d = math.hypot(q[0] - p[0], q[1] - p[1])
            if d <= reach and (best is None or d < best[0]):
                best = (d, q[0] - p[0], q[1] - p[1], q)
    if best is None:
        return Snap()
    return Snap(best[1], best[2], "side", best[3])


def placed(plan: Plan, pl: Placement) -> Plan:
    """A copy of the plan with every outline where the placement puts it and the reference composed with it: the model's
    world now lies on the plan turned by theta - turn about its origin, which stands at `at`."""
    out = copy.deepcopy(plan)
    f, degrees = mapping(pl), float(pl.turn)
    for b in out.buildings:
        b.footprint = move.moved(b.footprint, f)
        for fp in b.roof.free_pitches:
            fp["ring"] = move.moved(fp["ring"], f)
    for e, _host in out.exclusions:
        e.ring = move.moved(e.ring, f)
    for sf, _host in out.supports:
        sf.ring, sf.params = move._subfield(sf.ring, sf.params, f, degrees)
        sf.rows = move.moved_rows(sf.rows, f, degrees)
        move._move_support(sf.support, f, degrees)
    if out.reference:
        out.reference = {**out.reference, "theta": round(float(out.reference.get("theta") or 0.0) - degrees, 9),
                         "shift": [float(pl.at[0]), float(pl.at[1])], "placed": True}
    return out


def _union(rings):
    import shapely
    from shapely.geometry import Polygon
    polys = [Polygon(r).buffer(0) for r in rings if len(r) >= 3]
    return shapely.union_all(polys) if polys else Polygon()


def overlaps(project: model.Project, plan: Plan) -> list[str]:
    """The buildings already drawn that the placed model falls on (more than OVERLAP_M2 in common), in their order."""
    return overlaps_rings(project, [b.footprint for b in plan.buildings])


def overlaps_rings(project: model.Project, rings: list) -> list[str]:
    from shapely.geometry import Polygon
    shape = _union(rings)
    if shape.is_empty:
        return []
    out = []
    for b in project.buildings:
        if len(b.footprint) >= 3 and Polygon(b.footprint).buffer(0).intersection(shape).area > OVERLAP_M2:
            out.append(b.id)
    return out


def beside(project: model.Project, plan: Plan, pl: Placement, ids) -> Placement:
    """The placement nearest to `pl` that lays the model beside the buildings `ids` (GAP metres away), along the sides
    of the largest of them or across them, without falling on another building."""
    from shapely.geometry import Polygon
    from shapely import affinity
    olds = [b for b in project.buildings if b.id in ids]
    if not olds:
        return pl
    shape = _union([b.footprint for b in placed(plan, pl).buildings])
    largest = max(olds, key=lambda b: Polygon(b.footprint).area)
    ring = [tuple(map(float, q)) for q in largest.footprint]
    a, b = max(zip(ring, ring[1:] + ring[:1], strict=True), key=lambda s: math.dist(*s))
    length = math.dist(a, b) or 1.0
    u = ((b[0] - a[0]) / length, (b[1] - a[1]) / length)
    others = [Polygon(x.footprint).buffer(0) for x in project.buildings if len(x.footprint) >= 3]
    best = None
    for d in (u, (-u[0], -u[1]), (-u[1], u[0]), (u[1], -u[0])):
        def along(geom, d=d):
            return [q[0] * d[0] + q[1] * d[1] for q in _coords(geom)]
        blockers, t = [Polygon(x.footprint).buffer(0) for x in olds], 0.0
        for _round in range(12):
            there = affinity.translate(shape, d[0] * t, d[1] * t)
            t += max(0.0, max(max(along(p)) for p in blockers) - min(along(there)) + GAP)
            there = affinity.translate(shape, d[0] * t, d[1] * t)
            blockers = [p for p in others if p.intersection(there).area > 1e-6]
            if not blockers:
                break
        else:
            continue
        if best is None or t < best[0]:
            best = (t, d)
    if best is None:
        return pl
    t, d = best
    return shifted(pl, d[0] * t, d[1] * t)


def _coords(geom):
    for g in getattr(geom, "geoms", [geom]):
        if not g.is_empty:
            yield from g.exterior.coords


def _rehost(p: model.Project, gone: list[str], ids: list[str]) -> None:
    """What stood on the buildings replaced goes to the new body under its middle: the sub-fields (the design), the 3D
    objects; what has no body under it goes with the building. The old obstacles go: the model brings its own."""
    from shapely.geometry import Polygon
    new = [b for b in p.buildings if b.id in ids]

    def under(ring):
        if len(ring) < 3:
            return None
        middle_point = Polygon([tuple(map(float, q)) for q in ring]).buffer(0).representative_point()
        return next((b for b in new if Polygon(b.footprint).buffer(1e-6).contains(middle_point)), None)

    keep = []
    for sf in p.subfields:
        if sf.building in gone:
            b = under(sf.ring)
            if b is None:
                continue
            sf.building = b.id
            index = move._largest_pitch(b, sf.ring)
            sf.pitch = b.pitch_ref(index if index is not None else 0)
        keep.append(sf)
    p.subfields = keep
    p.exclusions = [e for e in p.exclusions if e.building not in gone]
    for x in p.props:
        if x.building in gone:
            x.building = p.prop_host(x.at)
    for v in p.variants:
        design = v.get("design") if isinstance(v, dict) else None
        raws = (design.get("subfields") or []) if isinstance(design, dict) else []
        for raw in raws:
            if isinstance(raw, dict) and raw.get("building") in gone:
                b = under(raw.get("ring") or [])
                if b is not None:
                    raw["building"] = b.id
    for b in p.buildings:
        if b.on in gone:
            host = under(b.footprint)
            b.on = host.id if host is not None and host.id != b.id else ""
        if b.part_of in gone:
            b.part_of = ""
    p.buildings = [b for b in p.buildings if b.id not in gone]


def apply(project: model.Project, plan: Plan, pl: Placement, replace=()) -> list[str]:
    """The model added where the placement puts it, replacing the buildings `replace` (inside the window's edit: one undo
    step with the import); the ids of the new bodies. ValueError when it cannot be added there."""
    out = placed(plan, pl)
    why = problem(out)
    if why:
        raise ValueError(why)
    ids = _apply_plan(project, out)
    gone = [b.id for b in project.buildings if b.id in set(replace) and b.id not in ids]
    if gone:
        _rehost(project, gone, ids)
    return ids


# the coordinates

def _origin(project) -> geo.Origin:
    return geo.Origin(project.site.lat, project.site.lon)


def zone_of(project, place: Place | None = None) -> tuple[int, bool]:
    """The UTM zone the coordinates are in: the file's when its map conversion is in one, the site's otherwise."""
    utm = geo.utm_of_crs(place.crs) if place is not None and place.crs else None
    if utm is not None:
        return utm
    return geo.utm_zone(project.site.lon), project.site.lat < 0


def turn_of(plan: Plan, pl: Placement) -> float:
    """The model's turn from its file's axes to the true north, degrees anticlockwise (0: its +Y is the north)."""
    theta = float((plan.reference or {}).get("theta") or 0.0)
    return round(((pl.turn - theta) + 180.0) % 360.0 - 180.0, 6)


def values(project, pl: Placement, plan: Plan, system: str, place: Place | None = None) -> dict:
    """Where the model's origin is now, in `system`, and its turn from the file's axes to the true north (degrees
    anticlockwise): {"a", "b", "turn", "zone"}."""
    out = {"turn": turn_of(plan, pl), "zone": ""}
    x, y = pl.at
    if system == "local":
        out.update(a=round(x, 3), b=round(y, 3))
        return out
    lon, lat = _origin(project).to_lonlat(x, y)
    if system == "latlon":
        out.update(a=round(lat, 8), b=round(lon, 8))
        return out
    zone, south = zone_of(project, place)
    _z, east, north, _gamma, _k = geo.to_utm(lat, lon, zone)
    out.update(a=round(east, 3), b=round(north, 3), zone=f"{zone}{'S' if south else 'N'}")
    return out


def from_values(project, plan: Plan, pl: Placement, system: str, a: float, b: float, turn: float,
                place: Place | None = None) -> Placement:
    """The placement whose origin stands at (a, b) of `system` with the model turned `turn` degrees from its axes to the
    true north. ValueError, in words, for a place that is no place."""
    for v in (a, b, turn):
        if not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(_("Write a number in each field."))
    if system == "local":
        x, y = float(a), float(b)
    else:
        if system == "latlon":
            lat, lon = float(a), float(b)
        elif system == "utm":
            zone, south = zone_of(project, place)
            if not (100_000.0 <= a <= 900_000.0) or not (0.0 <= b <= 10_000_000.0):
                raise ValueError(_("These are no UTM coordinates of zone {zone}: East between 100.000 and 900.000 m, "
                                   "North up to 10.000.000 m.").format(zone=f"{zone}{'S' if south else 'N'}"))
            lat, lon = geo.from_utm(zone, float(a), float(b), south)
        else:
            raise ValueError(f"system: {system!r}")
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            raise ValueError(_("A latitude goes from -90 to 90 degrees, a longitude from -180 to 180."))
        x, y = _origin(project).to_local(lon, lat)
    if abs(x) > model.COORD_LIMIT or abs(y) > model.COORD_LIMIT:
        raise ValueError(_("The model would fall more than {km} km from the site: check the coordinates, or move the "
                           "site to the model.").format(km=number(model.COORD_LIMIT / 1000, 0)))
    theta = float((plan.reference or {}).get("theta") or 0.0)
    return Placement(at=(x, y), turn=round(((float(turn) + theta) + 180.0) % 360.0 - 180.0, 9), base=pl.base)


def proposal(project, place: Place | None) -> dict | None:
    """The file's own georeferencing as the first choice of the coordinates: its map conversion in UTM, or a site that
    somebody set in latitude and longitude, with the turn it gives; None when the file says nothing to trust."""
    if place is None or not place.reliable():
        return None
    out = {"turn": round(-float(place.angle), 6), "source": "map" if place.trust == "map" else "site"}
    utm = geo.utm_of_crs(place.crs) if place.crs else None
    if place.trust == "map" and utm is not None:
        _z, east, north, _g, _k = geo.to_utm(place.lat, place.lon, utm[0])
        out.update(system="utm", a=round(east, 3), b=round(north, 3), zone=f"{utm[0]}{'S' if utm[1] else 'N'}")
    else:
        out.update(system="latlon", a=round(place.lat, 8), b=round(place.lon, 8), zone="")
    out["text"] = (_("From the file's map conversion ({crs})").format(crs=place.crs or "?") if out["source"] == "map"
                   else _("From the file's site «{name}»").format(name=place.site_name or "?"))
    return out


def distance_km(plan: Plan, pl: Placement) -> float:
    """How far the model's middle stands from the site, km."""
    x, y = mapping(pl)(*middle(plan))
    return math.hypot(x, y) / 1000.0


def far(plan: Plan, pl: Placement) -> str:
    """The warning for a model beyond FAR_KM from the site, "" within."""
    km = distance_km(plan, pl)
    if km <= FAR_KM:
        return ""
    return _("The model would stand {km} km from the project's site, more than {far} km: check the coordinates. The sun "
             "and the climate stay the site's.").format(km=number(km, 1 if km < 100 else 0), far=number(FAR_KM, 0))
