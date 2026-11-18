"""Parking canopies (R281, study 22, 3.7): the structure first, the modules after.

A canopy is a building with `model.Canopy`: its outline a rectangle whose first side runs along the rows of spaces,
its height the one under the low edge, its roof one slope (a row) or two opposed slopes meeting at a ridge (two
rows). It is placed in Modelling with its columns and beams and no module (`add`); in Plant «On a canopy» lays a
sub-field on each slope (`lay`). The columns and beams are boxes of indicative sizes for the drawing, the shadows
and the IFC model: they do not certify a structural design."""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import model
from .i18n import _

COLUMN = 0.25               # m, the side of a column's square section
BEAM = (0.20, 0.30)         # m, a beam's width and depth
MERGE = 0.5                 # m: two lines of beams closer than this are one


@dataclass(frozen=True)
class Spec:
    stalls: int = 4
    rows: int = 1
    bay_width: float = 2.5
    depth: float = 5.0
    clearance: float = 2.7
    tilt: float = 8.0
    turn: float = 0.0
    pillars: str = "cantilever"         # model.PILLARS
    columns: int = 0                    # on each line; 0: proposed from the spaces (proposed_columns)

    def validate(self) -> None:
        if type(self.stalls) is not int or not 1 <= self.stalls <= 100 or self.rows not in (1, 2):
            raise ValueError('Invalid parking row count')
        for value, low, high in ((self.bay_width, 0.5, 20), (self.depth, 1, 50),
                                 (self.clearance, 0.1, 100), (self.tilt, 0, 60), (self.turn, -180, 180)):
            if not math.isfinite(value) or not low <= value <= high:
                raise ValueError('Invalid canopy dimensions')
        if self.pillars not in model.PILLARS or type(self.columns) is not int or not 0 <= self.columns <= 200:
            raise ValueError('Invalid canopy columns')


def proposed_columns(stalls: int) -> int:
    """One column every two spaces, the two ends included (Daniel, study 22, decision 7): 4 spaces, 3 columns."""
    return max(2, stalls // 2 + 1)


def footprint(spec: Spec, at: tuple[float, float]) -> list[list[float]]:
    """The outline from `at`, its first corner: the first side along the rows, turned `turn` degrees
    counter-clockwise."""
    angle = math.radians(spec.turn)
    co, si = math.cos(angle), math.sin(angle)
    width, depth = spec.stalls * spec.bay_width, spec.rows * spec.depth
    return [[at[0] + x * co - y * si, at[1] + x * si + y * co] for x, y in ((0, 0), (width, 0), (width, depth),
                                                                            (0, depth))]


def roof(spec: Spec) -> model.Roof:
    """One row: one slope down to the first side; two rows: two slopes down to the long sides, the ridge between."""
    if spec.tilt <= 0:
        return model.Roof(type="flat")
    if spec.rows == 1:
        return model.Roof(type="mono", eave_side=0, tilt=spec.tilt)
    return model.Roof(type="gable", tilt=spec.tilt, edges=["eave", "gable", "eave", "gable"])


def building(spec: Spec, at: tuple[float, float], bid: str = "c1", name: str = "") -> model.Building:
    spec.validate()
    return model.Building(id=bid, name=name or _("Canopy"), footprint=footprint(spec, at), height=spec.clearance,
                          roof=roof(spec), canopy=model.Canopy(bays=spec.stalls, rows=spec.rows, pillars=spec.pillars,
                                                               columns=spec.columns))


def add(project: model.Project, spec: Spec, at: tuple[float, float]) -> str:
    """The canopy's structure, no module. Call inside one session edit; the new building's id."""
    n = sum(1 for b in project.buildings if b.canopy is not None) + 1
    b = building(spec, at, project.new_id("b"), _("Canopy {n}").format(n=n))
    project.buildings.append(b)
    return b.id


def frame(b: model.Building):
    """The canopy's frame: its first corner, the unit vectors along the rows (u) and across them (v, to the
    left of u), the length along u and the depth along v. None for an outline that is not a quadrilateral."""
    if len(b.footprint) != 4:
        return None
    (x0, y0), (x1, y1), _p2, (x3, y3) = (tuple(map(float, q)) for q in b.footprint)
    width = math.hypot(x1 - x0, y1 - y0)
    if width < 1e-6:
        return None
    u = ((x1 - x0) / width, (y1 - y0) / width)
    v = (-u[1], u[0])
    depth = (x3 - x0) * v[0] + (y3 - y0) * v[1]
    if depth < 1e-6:
        return None
    return (x0, y0), u, v, width, depth


def roof_at(pitches, x: float, y: float) -> float:
    """The roof over a point inside the outline: the lowest pitch plane there (the slopes meet at the ridge)."""
    from shapely.geometry import Point, Polygon
    here = Point(x, y)
    inside = [p for p in pitches if Polygon(p.ring).buffer(1e-6).contains(here)]
    return min(p.z(x, y) for p in (inside or pitches))


def lines(b: model.Building) -> tuple[list[float], list[float]]:
    """Where across the canopy (metres along v) its columns stand and its beams run. «cantilever»: one line under
    the highest edge (the back of one slope, the ridge of two); «two_rows»: one at each long edge. A beam on every
    line of columns and along both long edges; on two rows, under the ridge too."""
    f = frame(b)
    if f is None or b.canopy is None:
        return [], []
    (x0, y0), u, v, width, depth = f
    pitches = b.pitches()
    inset = COLUMN / 2

    def z(across):
        return roof_at(pitches, x0 + u[0] * width / 2 + v[0] * across, y0 + u[1] * width / 2 + v[1] * across)
    if b.canopy.pillars == "two_rows":
        columns = [inset, depth - inset]
    else:
        candidates = [depth / 2, depth - inset, inset]  # the middle first: on a flat roof it wins
        best = candidates[0]
        for c in candidates[1:]:
            if z(c) > z(best) + 1e-6:
                best = c
        columns = [best]
    beams = sorted(set(columns) | {inset, depth - inset} | ({depth / 2} if b.canopy.rows == 2 else set()))
    merged: list[float] = []
    for c in beams:
        if merged and c - merged[-1] < MERGE:
            if c in columns:
                merged[-1] = c                  # the line of columns keeps its place
            continue
        merged.append(c)
    return columns, merged


def structure(b: model.Building) -> list[dict]:
    """The columns and beams of a canopy as upright boxes, as model.obstacle_prisms gives the obstacles:
    {"ring", "z0", "z1", "kind" ("column" or "beam"), "id" (the canopy's), "building"}. A beam runs along u under
    the roof, its top at the lowest point of the roof over it; a column rises from the ground to the beam on its
    line. Kept with the building's geometry key: the views and the shadows ask many times."""
    key = b.geometry_key()
    cached = b.__dict__.get("_structure_cache")
    if cached is not None and cached[0] == key:
        return [dict(s) for s in cached[1]]
    out: list[dict] = []
    f = frame(b)
    if f is not None and b.canopy is not None:
        (x0, y0), u, v, width, depth = f
        pitches = b.pitches()

        def at(along, across):
            return (x0 + u[0] * along + v[0] * across, y0 + u[1] * along + v[1] * across)

        def rect(a0, a1, c0, c1):
            return [at(a0, c0), at(a1, c0), at(a1, c1), at(a0, c1)]
        columns, beams = lines(b)
        bottoms = {}
        for c in beams:
            half = BEAM[0] / 2
            ring = rect(0.0, width, c - half, c + half)
            top = min(roof_at(pitches, *q) for q in ring + [at(width / 2, c - half), at(width / 2, c + half)])
            bottoms[c] = max(0.0, top - BEAM[1])
            out.append({"ring": ring, "z0": bottoms[c], "z1": max(top, bottoms[c] + 1e-3), "kind": "beam",
                        "id": b.id, "building": b.id})
        n = b.canopy.columns or proposed_columns(b.canopy.bays)
        half = COLUMN / 2
        along = [width / 2] if n == 1 else [half + i * (width - COLUMN) / (n - 1) for i in range(n)]
        for c in columns:
            z1 = bottoms.get(c, min(bottoms.values(), default=b.height))
            for a in along:
                out.append({"ring": rect(a - half, a + half, c - half, c + half), "z0": 0.0, "z1": max(z1, 1e-3),
                            "kind": "column", "id": b.id, "building": b.id})
    b.__dict__["_structure_cache"] = (key, out)
    return [dict(s) for s in out]


def canopies(project: model.Project) -> list[model.Building]:
    return [b for b in project.buildings if b.canopy is not None]


def slopes(b: model.Building, overhang: float = 0.0) -> list[tuple[list, int]]:
    """The areas «On a canopy» covers: one for each slope, as its pitch with `overhang` metres more beyond the
    structure on the outer sides (never across the ridge); with the reference of the pitch each lies on."""
    f = frame(b)
    pitches = b.pitches()
    if f is None or not pitches:
        return []
    (x0, y0), u, v, width, depth = f

    def at(along, across):
        return [x0 + u[0] * along + v[0] * across, y0 + u[1] * along + v[1] * across]
    o = overhang
    if len(pitches) == 1 or b.canopy is None or b.canopy.rows == 1:
        bands = [(-o, depth + o)]
    else:
        bands = [(-o, depth / 2), (depth / 2, depth + o)]
    out = []
    for c0, c1 in bands:
        ring = [at(-o, c0), at(width + o, c0), at(width + o, c1), at(-o, c1)]
        mid = at(width / 2, (c0 + c1) / 2)
        from shapely.geometry import Point, Polygon
        index = min(range(len(pitches)), key=lambda i: Polygon(pitches[i].ring).distance(Point(*mid)))
        out.append((ring, b.pitch_ref(index)))
    return out


def lay(project: model.Project, bid: str, portrait: bool = True, gap: float = 0.02, overhang: float = 0.0,
        edge: float = 0.1) -> list[str]:
    """«On a canopy» (R281, study 22, decision 9): a sub-field on each slope of the canopy `bid`, filled, flush with
    its plane, the general layout inside; those the canopy had in this variant are replaced. Call inside one
    session edit; the new sub-fields' ids. ValueError for no such canopy or values out of range."""
    b = project.building(bid)
    if b is None or b.canopy is None:
        raise ValueError(_("there is no such canopy"))
    for value, low, high in ((gap, 0.0, 0.5), (overhang, 0.0, 2.0), (edge, 0.0, 2.0)):
        if not math.isfinite(value) or not low <= value <= high:
            raise ValueError(_("{value} is out of range").format(value=value))
    project.subfields = [s for s in project.subfields if s.building != bid]
    ids = []
    found = slopes(b, overhang)
    for k, (ring, ref) in enumerate(found):
        pitch = b.pitches()[b.pitch_index(ref)] if b.pitch_index(ref) is not None else b.pitches()[0]
        sid = project.new_id("s")
        name = b.name if len(found) == 1 else _("{name}, slope {n}").format(name=b.name, n=k + 1)
        project.subfields.append(model.SubField(
            id=sid, name=name, ring=ring, building=bid, pitch=ref, filled=True,
            params={"mounting": "canopy", "portrait": bool(portrait), "tilt": pitch.tilt, "gap": gap,
                    "flush_row_gap": gap, "edge": edge, "stand_off": 0.1}))
        ids.append(sid)
    return ids
