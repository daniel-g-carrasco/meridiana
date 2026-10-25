"""What the views show beside the drawing (study 12, V1-V3; study 15, 3.3 and 3.11): the round length of the
plan's scale bar, what lies under the cursor with its height, and the quick measure of the selection for the
status bar. No Qt here: the plan draws them."""

from __future__ import annotations

import math

from shapely.geometry import Point, Polygon

from .i18n import _, ngettext, number

STEPS = (1.0, 2.0, 5.0)


def scale_bar(metres_per_pixel: float, longest_px: float = 120.0) -> tuple[float, float]:
    """The longest round length (1, 2 or 5 times a power of ten, in metres) whose bar fits in `longest_px`, and
    its length on screen in pixels."""
    if metres_per_pixel <= 0 or not math.isfinite(metres_per_pixel):
        raise ValueError("the scale must be a positive number")
    most = metres_per_pixel * longest_px
    power = 10.0 ** math.floor(math.log10(most))
    length = max(s * power for s in STEPS if s * power <= most * (1 + 1e-9))
    return length, length / metres_per_pixel


def length_text(metres: float) -> str:
    """A length as the scale bar writes it: «50 cm», «5 m», «200 m», «2 km»."""
    if metres < 1:
        return _("{n} cm").format(n=number(metres * 100, 0))
    if metres >= 1000:
        return _("{n} km").format(n=number(metres / 1000, 0 if metres % 1000 == 0 else 1))
    return _("{n} m").format(n=number(metres, 0))


def _thing(project, kind: str, oid: str):
    if kind == "building":
        return project.building(oid)
    if kind == "subfield":
        return next((s for s in project.subfields if s.id == oid), None)
    if kind == "exclusion":
        return next((e for e in project.exclusions if e.id == oid), None)
    return None


def height_at(project, kind: str, oid: str, x: float, y: float) -> float:
    """The height of what is under the cursor at (x, y): the roof of a building at that point (its pitch), the
    top of an obstacle, the ground (0) for what lies on it. A module (`oid` its sub-field) is at the height of
    its sub-field: it said 0 before (review, 23/10/2026)."""
    if kind == "module":
        kind = "subfield"
    if kind == "pitch":
        bid, _sep, i = oid.partition(":")
        b = project.building(bid)
        pitches = b.pitches() if b is not None else []
        return pitches[int(i)].z(x, y) if i.isdigit() and int(i) < len(pitches) else 0.0
    thing = _thing(project, kind, oid)
    if thing is None:
        return 0.0
    bid = thing.id if kind == "building" else getattr(thing, "building", None)
    b = project.building(bid)
    z = 0.0
    if b is not None:
        here = Point(x, y)
        pitches = b.pitches()
        if pitches:
            k = min(range(len(pitches)), key=lambda i: Polygon(pitches[i].ring).distance(here))
            z = pitches[k].z(x, y)
        else:
            z = b.height
    if kind == "exclusion":
        z += thing.obstacle_height()
    return z


def under_text(project, kind: str, oid: str, key: str, x: float, y: float, kind_names: dict | None = None) -> str:
    """What is under the cursor, as the status bar says it: «Sub-field Sud, module r3c12 (12,40; 7,85; z 9,92 m)»,
    as FreeCAD's preselection does (study 15, 3.3). The coordinates alone when nothing is there."""
    where = _("E {x}  N {y}  z {z} m").format(x=number(x), y=number(y), z=number(height_at(project, kind, oid, x, y)))
    if kind in ("", "site"):
        return _("E {x}  N {y} m").format(x=number(x), y=number(y))
    if kind == "pitch":
        bid, _sep, i = oid.partition(":")
        b = project.building(bid)
        name = _("{building}, pitch {n}").format(building=b.name if b else bid, n=int(i) + 1 if i.isdigit() else i)
    elif kind == "module":
        sf = _thing(project, "subfield", oid)
        name = _("{subfield}, module {key}").format(subfield=sf.name if sf else oid, key=key)
    else:
        thing = _thing(project, kind, oid)
        if kind == "exclusion":
            name = (kind_names or {}).get(getattr(thing, "kind", ""), _("Exclusion")) + f" {oid}"
        else:
            name = getattr(thing, "name", oid)
    return f"{name}  ·  {where}"


def anchor(project, kind: str, oid: str) -> tuple[float, float, float] | None:
    """Where the mark of an object goes: the middle of its outline (a point inside it), at its height."""
    thing = _thing(project, kind, oid)
    if thing is None:
        return None
    ring = thing.footprint if kind == "building" else thing.ring
    if len(ring) < 3:
        return None
    p = Polygon([tuple(map(float, q)) for q in ring]).representative_point()
    return float(p.x), float(p.y), height_at(project, kind, oid, float(p.x), float(p.y))


def measure(project, results: dict, kind: str, oid: str) -> dict:
    """The quick measure of the selection (study 15, 3.11): perimeter and area of its outline, and for a sub-field
    the modules laid and their power; a row its own (row_measure). {} for nothing measurable."""
    if kind == "row":
        return row_measure(project, results, oid)
    thing = _thing(project, kind, oid)
    if thing is None:
        return {}
    ring = thing.footprint if kind == "building" else thing.ring
    pts = [tuple(map(float, p)) for p in ring]
    if len(pts) < 3:
        return {}
    out = {"length": sum(math.dist(a, b) for a, b in zip(pts, pts[1:] + pts[:1], strict=True)),
           "area": abs(Polygon(pts).area)}
    if kind == "subfield":
        r = results.get(oid)
        if thing.filled and r is not None and not isinstance(r, Exception):
            out["modules"] = r.count
            out["kwp"] = r.count * project.module_of(thing).power_kw
            out["tilt"], out["azimuth"] = r.tilt, r.azimuth
    return out


def row_measure(project, results: dict, oid: str) -> dict:
    """The quick measure of a row (task 16c, "<sub-field>/<row>"): its length, its modules and their power."""
    sfid, _sep, rid = oid.partition("/")
    sf, r = _thing(project, "subfield", sfid), results.get(sfid)
    if sf is None or r is None or isinstance(r, Exception):
        return {}
    mine = [m for m in r.modules if m.rid == rid]
    if not mine:
        return {}
    from shapely.geometry import MultiPoint
    box = MultiPoint([c for m in mine for c in m.corners]).minimum_rotated_rectangle
    pts = [tuple(map(float, p)) for p in list(box.exterior.coords)[:-1]] if box.geom_type == "Polygon" else []
    sides_ = [math.dist(a, b) for a, b in zip(pts, pts[1:] + pts[:1], strict=True)]
    return {"row": max(sides_) if sides_ else 0.0, "modules": len(mine),
            "kwp": len(mine) * project.module_of(sf).power_kw}


def measure_text(m: dict) -> str:
    if not m:
        return ""
    if "row" in m:
        return "  ·  ".join([_("row of {l} m").format(l=number(m["row"])),
                             ngettext("{n} module", "{n} modules", m["modules"]).format(n=m["modules"]),
                             _("{kw} kWp").format(kw=number(m["kwp"]))])
    parts = [_("perimeter {p} m").format(p=number(m["length"])), _("area {a} m²").format(a=number(m["area"], 1))]
    if "modules" in m:
        parts.append(ngettext("{n} module", "{n} modules", m["modules"]).format(n=m["modules"]))
        parts.append(_("{kw} kWp").format(kw=number(m["kwp"])))
    return "  ·  ".join(parts)


LIFT = 0.04             # an outline on a roof stands this much above it, not to be hidden in its surface


def outline(project, results: dict, kind: str, oid: str, key: str = ""):
    """The edges the 3D view outlines for an object (mesh.ribbons draws them): (M, 2, 3) in Qt axes. A building
    with its corners and pitches, a pitch, a sub-field on its roof, an exclusion as the prism it rises to, a
    module (`key`, `oid` its sub-field) on its face. Nothing (0 segments) for what is not there."""
    import numpy as np

    from . import mesh, model
    none = np.zeros((0, 2, 3))
    if kind == "building":
        b = project.building(oid)
        return mesh.building_edges(b.footprint, b.pitches()) if b is not None and len(b.footprint) >= 3 else none
    if kind == "pitch":
        bid, _sep, i = oid.partition(":")
        b = project.building(bid)
        pitches = b.pitches() if b is not None else []
        if not i.isdigit() or int(i) >= len(pitches):
            return none
        p = pitches[int(i)]
        return mesh.ring_edges([(float(x), float(y), p.z(float(x), float(y)) + LIFT) for x, y in p.ring])
    if kind == "module":
        sf = _thing(project, "subfield", oid)
        r = results.get(oid)
        if sf is None or r is None or isinstance(r, Exception):
            return none
        m = next((pm for pm in r.modules if pm.key == key), None)
        if m is None:
            return none
        size = project.module_of(sf)
        along, across = (size.width, size.length) if sf.layout_params().portrait else (size.length, size.width)
        return mesh.module_edges(m, along, across)
    if kind == "row":                              # task 16c: every module of the row, "<sub-field>/<row>"
        sfid, _sep, rid = oid.partition("/")
        sf, r = _thing(project, "subfield", sfid), results.get(sfid)
        if sf is None or r is None or isinstance(r, Exception):
            return none
        size = project.module_of(sf)
        along, across = (size.width, size.length) if sf.layout_params().portrait else (size.length, size.width)
        parts = [mesh.module_edges(m, along, across) for m in r.modules if m.rid == rid]
        return np.concatenate(parts) if parts else none
    thing = _thing(project, kind, oid)
    if thing is None or len(thing.ring) < 3:
        return none
    ring = [(float(x), float(y)) for x, y in thing.ring]
    if kind == "exclusion":
        prism = next((o for o in project.obstacle_prisms() if o["kind"] != "parapet" and o["id"] == oid), None)
        if prism is not None:
            return mesh.prism_edges(prism["ring"], prism["z0"], prism["z1"])
    b = project.building(getattr(thing, "building", None))
    zs = model.roof_z(b, ring) if b is not None else [0.0] * len(ring)
    return mesh.ring_edges([(x, y, z + LIFT) for (x, y), z in zip(ring, zs, strict=True)])
