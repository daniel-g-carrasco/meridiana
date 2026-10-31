"""The project: a site, its buildings with their roof pitches, the sub-fields the designer drew, the
exclusions, the modules used. Plain data, a JSON schema in the .mer archive, coordinates in local metres from the
site origin (geo.py).

The designer's workflow is in steps, and the model keeps them apart: a building is modelled first
(outline, heights, roof); sub-fields are then drawn where the designer wants them, each with its own
mounting, tilt, orientation and margins; modules are laid in a sub-field only when asked (`filled`).
A sub-field is the CEI 82-25/1 3.2.3.2 "sottocampo": the part of the array with one mounting and one
orientation.

Format changes: FORMAT_VERSION + 1 and a step in MIGRATIONS; a file from a newer version is refused
rather than half read and saved back without what this version does not know.
"""

from __future__ import annotations

import copy
import dataclasses
import math
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import atomic, layout, roofs, settings, skeleton, sun
from .underlay import Underlay

FORMAT = "meridiana-project"
FORMAT_VERSION = 21
# what a variant holds: the rest of the project (site, buildings, exclusions, consumption, rules) is shared
DESIGN = ("subfields", "modules", "energy", "economics")


def _to_7(data: dict) -> dict:
    """6 -> 7: one representation of the variants in the file: every variant, the one in hand too, keeps its
    design under "design" (the one in hand had it in the keys of the project, the others in theirs); each
    pitch drawn by hand has an id; app_version is no longer written."""
    out = {k: v for k, v in data.items() if k not in DESIGN}
    variants = [dict(v) for v in (data.get("variants") or [{"id": "v1", "name": "Base", "note": ""}])
                if v.__class__ is dict]
    current = data.get("variant") or (variants[0].get("id") if variants else "v1")
    design = {k: data[k] for k in DESIGN if k in data}
    for v in variants:
        if v.get("id") == current and design:
            v["design"] = design
    out["variants"] = variants
    for b in out.get("buildings") or []:
        roof = b.get("roof") if b.__class__ is dict else None
        for i, pitch in enumerate((roof or {}).get("free_pitches") or []):
            if pitch.__class__ is dict:
                pitch.setdefault("id", f"p{i + 1}")
    return out


def _energy_to_8(energy):
    """The energy of one variant, 7 -> 8: the one inverter and its count become the first of a list of
    inverters ({"record", "count", "name"}); a count without an inverter meant nothing and goes. The strings
    asked (modules in series, strings on each input) stay what they were: the proposal's parameters."""
    if energy.__class__ is not dict:
        return energy
    out = {k: v for k, v in energy.items() if k not in ("inverter", "inverter_count")}
    rec = energy.get("inverter")
    if rec.__class__ is dict and rec:
        count = energy.get("inverter_count", 1)
        out["inverters"] = [{"record": rec, "count": count if count.__class__ is int and count >= 1 else 1,
                             "name": ""}]
    return out


def _to_8(data: dict) -> dict:
    """7 -> 8: inverters and strings as objects (task 16d): in the energy of every variant, the inverter of
    before is the first of the list (_energy_to_8); the strings keep their keys, proposed by Meridiana until
    the designer touches one."""
    out = dict(data)
    variants = []
    for v in data.get("variants") or []:
        if v.__class__ is dict and (v.get("design") or {}).__class__ is dict and "energy" in v.get("design", {}):
            v = {**v, "design": {**v["design"], "energy": _energy_to_8(v["design"]["energy"])}}
        variants.append(v)
    if "variants" in data:
        out["variants"] = variants
    return out


def _is_rectangle(footprint) -> bool:
    """An outline that is its own minimum rotated rectangle: the roofs up to format 8 were built right on it."""
    from shapely.geometry import Polygon
    poly = Polygon([(float(x), float(y)) for x, y in footprint])
    rect = poly.minimum_rotated_rectangle
    return (len(poly.simplify(0).exterior.coords) == 5
            and abs(rect.area - poly.area) < 1e-6 * max(poly.area, 1.0))


def _old_azimuths(footprint, roof: dict) -> list[float]:
    """The azimuths of the pitches of a gable or hip roof up to format 8, in their order: two or four planes on
    the minimum rotated rectangle of the outline, the ridge along its long side or parallel to `ridge_along`
    (roofs.gable and roofs.hip before task 16a, kept here for the migration only)."""
    from shapely.geometry import Polygon
    ring = [(float(x), float(y)) for x, y in footprint]
    r = [(float(x), float(y)) for x, y in list(Polygon(ring).minimum_rotated_rectangle.exterior.coords)[:-1]]
    along = None
    if roof.get("type") == "gable" and roof.get("ridge_along").__class__ is int:
        i = roof["ridge_along"] % len(ring)
        along = (ring[(i + 1) % len(ring)][0] - ring[i][0], ring[(i + 1) % len(ring)][1] - ring[i][1])
    if along is None:
        first_long = math.dist(r[0], r[1]) >= math.dist(r[1], r[2])
    else:
        n = math.hypot(*along) or 1.0
        ux, uy = along[0] / n, along[1] / n

        def parallel(a, b):
            return abs((b[0] - a[0]) * ux + (b[1] - a[1]) * uy) / (math.dist(a, b) or 1.0)
        first_long = parallel(r[0], r[1]) >= parallel(r[1], r[2])
    r = r if first_long else r[1:] + r[:1]
    centre = ((r[0][0] + r[2][0]) / 2, (r[0][1] + r[2][1]) / 2)
    sides = ([(r[0], r[1]), (r[2], r[3])] if roof.get("type") == "gable"
             else [(r[0], r[1]), (r[1], r[2]), (r[2], r[3]), (r[3], r[0])])
    return [round(roofs._outward_azimuth(a, b, centre), 4) for a, b in sides]


def _same_azimuth(a: float, b: float) -> bool:
    return abs((a - b + 180.0) % 360.0 - 180.0) < 0.01


def _roof_to_9(raw: dict) -> tuple[dict, tuple]:
    """A gable or hip roof of format 8 with its sides: a hip has only eaves; on a rectangle a gable keeps its
    ridge (the sides facing as its two pitches did are the eaves, the others the gable ends); on any other
    outline the roof now follows the outline, with the gable ends of a new roof (roofs.default_gables). With the
    azimuths of the old pitches and the new pitches, for the sub-fields."""
    from shapely.geometry import Polygon
    footprint = [(float(x), float(y)) for x, y in raw["footprint"]]
    roof = raw["roof"]
    old = _old_azimuths(footprint, roof)
    rectangle = _is_rectangle(footprint)
    n = len(footprint)
    if roof["type"] == "hip":
        edges = ["eave"] * n
    elif rectangle:
        inside = Polygon(footprint).representative_point()
        edges = ["eave" if any(_same_azimuth(roofs._outward_azimuth(footprint[i], footprint[(i + 1) % n],
                                                                     (inside.x, inside.y)), a) for a in old)
                 else "gable" for i in range(n)]
    else:
        ends = roofs.default_gables(footprint)
        edges = ["gable" if i in ends else "eave" for i in range(n)]
    pitches, _dropped = roofs.pitched(footprint, float(raw.get("height", 10.0)), float(roof.get("tilt", 0.0)),
                                      {i for i, kind in enumerate(edges) if kind == "gable"})
    return {**raw, "roof": {**roof, "edges": edges}}, (old, pitches, rectangle)


def _subfield_to_9(raw, roofs_of: dict):
    """A sub-field of format 8 on a gable or hip roof: from the place of its pitch among the old ones to the
    side of the eave of the new one. On a rectangle the pitch facing as the old one did (the same plane, the
    same layout); elsewhere the pitch under the middle of the sub-field, or the nearest."""
    from shapely.geometry import Point, Polygon
    if raw.__class__ is not dict or raw.get("building") not in roofs_of:
        return raw
    old, pitches, rectangle = roofs_of[raw["building"]]
    if not pitches:
        return raw
    index = raw.get("pitch")
    facing = old[index] if index.__class__ is int and 0 <= index < len(old) else old[0]
    try:
        middle = Polygon([(float(x), float(y)) for x, y in raw["ring"]]).centroid
    except (TypeError, ValueError, KeyError):
        return raw
    pool = [p for p in pitches if _same_azimuth(p.azimuth, facing)] if rectangle else []
    pool = pool or pitches

    def place(p):
        shape = Polygon(p.ring)
        return (0 if shape.buffer(1e-6).contains(middle) else 1, shape.distance(Point(middle.x, middle.y)))
    return {**raw, "pitch": min(pool, key=place).side}


def _to_9(data: dict) -> dict:
    """8 -> 9: the roofs on any outline (task 16a). A gable or hip roof says for each side whether it is an
    eave or a gable end (_roof_to_9); a sub-field on such a roof refers to its pitch by the side of its eave, no
    longer by its place among the pitches (_subfield_to_9), in every variant. A file damaged where this reads
    is left to the checks that follow."""
    out = dict(data)
    roofs_of: dict = {}
    buildings = []
    for b in data.get("buildings") or []:
        roof = b.get("roof") if b.__class__ is dict else None
        if roof.__class__ is dict and roof.get("type") in ("gable", "hip"):
            try:
                b, roofs_of[b.get("id")] = _roof_to_9(b)
            except (TypeError, ValueError, KeyError, IndexError, ZeroDivisionError):
                pass
        buildings.append(b)
    if "buildings" in data:
        out["buildings"] = buildings
    variants = []
    for v in data.get("variants") or []:
        design = v.get("design") if v.__class__ is dict else None
        if design.__class__ is dict and design.get("subfields").__class__ is list:
            v = {**v, "design": {**design, "subfields": [_subfield_to_9(sf, roofs_of) for sf in design["subfields"]]}}
        variants.append(v)
    if "variants" in data:
        out["variants"] = variants
    return out


def _key_to_10(key):
    """A module's key of format 9, «row:slot[:level]» with the row's place in the layout, as the id of format 10:
    the same module, in the row of the automatic layout with that place («f1» the first). None when it is not one."""
    if key.__class__ is not str:
        return None
    parts = key.split(":")
    if len(parts) not in (2, 3) or not all(x.isdigit() for x in parts):
        return None
    return ":".join([f"f{int(parts[0]) + 1}"] + parts[1:])


def _run_key_to_10(key):
    """A module of a string by hand, «sub-field/row:slot», as format 10 has it."""
    if key.__class__ is not str or "/" not in key:
        return None
    sf, _sep, rest = key.rpartition("/")
    new = _key_to_10(rest)
    return f"{sf}/{new}" if new is not None else None


def _design_to_10(design: dict) -> dict:
    out = dict(design)
    if design.get("subfields").__class__ is list:
        subfields = []
        for sf in design["subfields"]:
            if sf.__class__ is dict and sf.get("removed").__class__ is list:
                sf = {**sf, "removed": [k for k in (_key_to_10(x) for x in sf["removed"]) if k is not None]}
            subfields.append(sf)
        out["subfields"] = subfields
    energy = design.get("energy")
    strings = energy.get("strings") if energy.__class__ is dict else None
    if strings.__class__ is dict and strings.get("runs").__class__ is list:
        runs = []
        for run in strings["runs"]:
            if run.__class__ is dict and run.get("modules").__class__ is list:
                run = {**run, "modules": [k for k in (_run_key_to_10(x) for x in run["modules"]) if k is not None]}
            runs.append(run)
        out["energy"] = {**energy, "strings": {**strings, "runs": runs}}
    return out


def _to_10(data: dict) -> dict:
    """9 -> 10: the rows as objects (task 16c). The sub-fields lay as before (no rows of their own, automatic); the
    keys of the modules taken out by hand and of the strings by hand, «row:slot» with the row's place, become the ids
    of the same modules in the rows of the automatic layout, «f1:slot» for the first row (`_key_to_10`), in every
    variant. A key that is not one is left out, and said (`_unreadable`)."""
    out = dict(data)
    variants = []
    for v in data.get("variants") or []:
        design = v.get("design") if v.__class__ is dict else None
        if design.__class__ is dict:
            v = {**v, "design": _design_to_10(design)}
        variants.append(v)
    if "variants" in data:
        out["variants"] = variants
    return out


def _unreadable(data: dict) -> int:
    """How many keys of modules of a file before format 10 are not «row:slot»: the migration leaves them out. The
    designs of a file before format 7 are in the project's keys, those of later ones in the variants."""
    designs = [data] + [v.get("design") for v in data.get("variants") or [] if v.__class__ is dict]
    n = 0
    for design in designs:
        if design.__class__ is not dict:
            continue
        for sf in design.get("subfields") or []:
            if sf.__class__ is dict and sf.get("removed").__class__ is list:
                n += sum(1 for k in sf["removed"] if _key_to_10(k) is None)
        energy = design.get("energy")
        strings = energy.get("strings") if energy.__class__ is dict else None
        for run in (strings.get("runs") if strings.__class__ is dict else None) or []:
            if run.__class__ is dict and run.get("modules").__class__ is list:
                n += sum(1 for k in run["modules"] if _run_key_to_10(k) is None)
    return n


def _to_14(data: dict) -> dict:
    """13 -> 14: the strings are the designer's, never Meridiana's live proposal (R114, R118, Daniel 25/10/2026). Up to
    13 a variant without strings of its own («auto», the default) had them proposed again at every change; from 14 it
    has none until the designer asks. So that nothing changes under him, every variant that had the proposal keeps it
    as an explicit «auto», and the window writes it down as his strings at the first layout (energy/plant.py)."""
    out = dict(data)
    variants = []
    for v in data.get("variants") or []:
        design = v.get("design") if v.__class__ is dict else None
        if design.__class__ is dict:
            energy = design.get("energy") if design.get("energy").__class__ is dict else {}
            strings = energy.get("strings") if energy.get("strings").__class__ is dict else {}
            if strings.get("auto", True) is not False:
                v = {**v, "design": {**design, "energy": {**energy, "strings": {**strings, "auto": True}}}}
        variants.append(v)
    if "variants" in data:
        out["variants"] = variants
    return out


def _to_15(data: dict) -> dict:
    """14 -> 15: optional grid data, initialized from the rule inputs already present."""
    rules = data.get("rules") if isinstance(data.get("rules"), dict) else {}
    level = rules.get("connection") if rules.get("connection") in ("BT", "MT", "AT") else ""
    contracted = rules.get("contracted_kw") if isinstance(rules.get("contracted_kw"), (int, float)) else 0.0
    network = {"level": level, "available_kw": contracted}
    return {**data, "network": data.get("network", network)}


def _reshaped(data: dict) -> list[str]:
    """The buildings of a file before format 9 whose gable or hip roof stood on a rectangle that was not their
    outline: from 9 the roof follows the outline, and the designer is told."""
    out = []
    for b in data.get("buildings") or []:
        try:
            if b["roof"]["type"] in ("gable", "hip") and not _is_rectangle(b["footprint"]):
                out.append(str(b.get("name") or b.get("id")))
        except (TypeError, ValueError, KeyError, IndexError, AttributeError):
            continue
    return out


CANOPY_BAY = 2.5            # m, the width of a parking space the migration to 21 counts the spaces with
_SAME = 1e-3                # m, how far two corners may be and still be one


def _canopy_slope(raw) -> dict | None:
    """A slope of a canopy as the dialog of a file before format 21 made it (canopies.fields up to 30/10/2026): a
    sub-field on the ground on its own plane, over a rectangle, the plane going down square to one of its sides.
    Its corners from the low side, counter-clockwise, with the tilt and the heights; None for anything else (a
    slope changed by hand, which stays a sub-field)."""
    try:
        params, support = raw.get("params") or {}, raw.get("support")
        if raw.get("building") is not None or params.get("mounting") != "canopy" or support.__class__ is not dict \
                or support.get("enabled", True) is not True:
            return None
        pts = [(float(x), float(y)) for x, y in raw["ring"]]
        tilt, azimuth = float(support.get("tilt", 0.0)), float(support.get("azimuth", 0.0))
        z0, x0, y0 = (float(support.get(k, 0.0)) for k in ("z0", "x0", "y0"))
    except (AttributeError, KeyError, TypeError, ValueError):
        return None
    if len(pts) != 4 or not all(math.isfinite(v) for v in (*sum(pts, ()), tilt, azimuth, z0, x0, y0)) \
            or not 0.0 <= tilt < 89.0:
        return None
    sides = [(pts[(i + 1) % 4][0] - pts[i][0], pts[(i + 1) % 4][1] - pts[i][1]) for i in range(4)]
    lengths = [math.hypot(*s) for s in sides]
    if min(lengths) < 0.1 or any(abs(lengths[i] - lengths[i + 2]) > _SAME for i in (0, 1)) or any(
            abs(sides[i][0] * sides[(i + 1) % 4][0] + sides[i][1] * sides[(i + 1) % 4][1]) > _SAME * lengths[i]
            for i in range(4)):
        return None
    from . import geo
    fx, fy = geo.facing_vector(azimuth)
    slope = math.tan(math.radians(tilt))
    zs = [z0 - ((x - x0) * fx + (y - y0) * fy) * slope for x, y in pts]
    low = min(zs)
    first = next((i for i in range(4) if abs(zs[i] - low) < _SAME and abs(zs[(i + 1) % 4] - low) < _SAME), None)
    if first is None:
        return None
    pts = pts[first:] + pts[:first]
    if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1], strict=True)) < 0:
        pts = [pts[1], pts[0], pts[3], pts[2]]          # the same low side first, counter-clockwise
    return {"ring": pts, "tilt": tilt, "low": low, "high": max(zs)}


def _paired(a: dict, b: dict) -> bool:
    """Two slopes of one canopy of two rows: the same tilt and heights, the high side of one the other's."""
    return (abs(a["tilt"] - b["tilt"]) < 1e-6 and abs(a["low"] - b["low"]) < _SAME
            and abs(a["high"] - b["high"]) < _SAME
            and math.dist(a["ring"][2], b["ring"][3]) < _SAME and math.dist(a["ring"][3], b["ring"][2]) < _SAME)


def _to_21(data: dict, notes: list | None = None) -> dict:
    """20 -> 21: a parking canopy is a structure (R281, study 22, decision 8). Up to 20 the dialog made one or two
    sub-fields, each on its own plane, and nothing held them; from 21 the canopy is a building with `canopy` (its
    spaces and columns), its roof the plane of the slopes (mono, or gable with the ridge between two rows), the
    height the one under the low edge. The slopes it recognises lie on its pitches from here (`building`, `pitch`,
    no plane of their own: the same plane). The same canopy in two variants is one building. A slope changed by
    hand (not a rectangle, its plane askew) stays a sub-field on its own plane; `notes` says both."""
    from .i18n import _, ngettext
    out = copy.deepcopy(data)
    used = {str(x.get("id")) for key in ("buildings", "exclusions", "underlays") for x in out.get(key) or []
            if x.__class__ is dict}
    designs = [v["design"] for v in out.get("variants") or [] if v.__class__ is dict
               and v.get("design").__class__ is dict]
    for design in designs:
        used |= {str(s.get("id")) for s in design.get("subfields") or [] if s.__class__ is dict}
    buildings = out.setdefault("buildings", [])
    made: dict = {}                             # the outline, rounded, -> the building's id
    left = 0

    def canopy_of(ring, low, tilt, rows) -> str:
        key = (rows, round(low, 3), round(tilt, 4), tuple((round(x, 3), round(y, 3)) for x, y in ring))
        if key in made:
            return made[key]
        n = 1
        while f"b{n}" in used:
            n += 1
        bid = f"b{n}"
        used.add(bid)
        width = math.dist(ring[0], ring[1])
        if tilt <= 0:
            roof = {"type": "flat"}
        elif rows == 1:
            roof = {"type": "mono", "eave_side": 0, "tilt": tilt}
        else:
            roof = {"type": "gable", "tilt": tilt, "edges": ["eave", "gable", "eave", "gable"]}
        buildings.append({"id": bid, "name": _("Canopy {n}").format(n=len(made) + 1),
                          "footprint": [[round(x, 6), round(y, 6)] for x, y in ring], "height": low, "roof": roof,
                          "canopy": {"bays": max(1, min(100, round(width / CANOPY_BAY))), "rows": rows,
                                     "pillars": "cantilever", "columns": 0}})
        made[key] = bid
        return bid

    for design in designs:
        rows = [s for s in design.get("subfields") or [] if s.__class__ is dict]
        slopes = {i: _canopy_slope(s) for i, s in enumerate(rows)}
        left += sum(1 for i, s in enumerate(rows) if slopes[i] is None and s.get("building") is None
                    and (s.get("params") or {}).get("mounting") == "canopy")
        taken: set = set()
        for i, a in slopes.items():
            if a is None or i in taken:
                continue
            j = next((j for j, b in slopes.items() if j > i and b is not None and j not in taken and _paired(a, b)),
                     None)
            taken.add(i)
            if j is None:
                bid = canopy_of(a["ring"], a["low"], a["tilt"], 1)
                rows[i].update(building=bid, pitch=0)
            else:
                taken.add(j)
                b = slopes[j]
                bid = canopy_of([a["ring"][0], a["ring"][1], b["ring"][0], b["ring"][1]], a["low"], a["tilt"], 2)
                rows[i].update(building=bid, pitch=0)
                rows[j].update(building=bid, pitch=2 if a["tilt"] > 0 else 0)
            for k in (i, j):
                if k is not None:
                    rows[k].pop("support", None)
    if notes is not None and made:
        names = ", ".join(b["name"] for b in buildings if b["id"] in made.values())
        notes.append(ngettext(
            "{n} parking canopy of an earlier format is now a structure with its columns ({names}): check its "
            "spaces and columns.", "{n} parking canopies of an earlier format are now structures with their columns "
            "({names}): check their spaces and columns.", len(made)).format(n=len(made), names=names))
    if notes is not None and left:
        notes.append(ngettext(
            "{n} canopy slope changed by hand could not be read as a structure: it stays a sub-field on its own "
            "plane.", "{n} canopy slopes changed by hand could not be read as a structure: they stay sub-fields on "
            "their own planes.", left).format(n=left))
    return out


# 1 -> 2:exclusions have a height (None: the default of their kind), buildings a parapet; both cast shadows
# 2 -> 3: the project has its rules (connection level, minimum renewable capacity of the building), empty
# 3 -> 4: variants; what there was becomes the first, "Base"
# 4 -> 5: a gable roof may have its ridge parallel to a side the designer picked (None: the long side)
# 5 -> 6: images under the drawing (underlay.py), none
# 6 -> 7: every variant with its design in the file, ids of the free pitches (_to_7)
# 7 -> 8: the inverters as a list, the strings as objects (_to_8)
# 8 -> 9: the roofs on any outline: sides as eaves or gable ends, a ridge height, a covering; sub-fields on the
#         side of their eave (_to_9)
# 9 -> 10: the rows as objects: a sub-field may keep its rows by hand; the modules' keys are ids (_to_10)
# 10 -> 11: the report's choices (R61, reports.py): the template, the chapters off, the profile, the client; none
# 11 -> 12: a project may be reserved, never sent to a cloud model (task 14); a file before is not. A format of its
#          own: an older Meridiana would drop the mark in silence and save the project without it
# 12 -> 13: an inverter at a fixed string voltage (SolarEdge) may keep its power optimizers in its entry of
#          energy["inverters"]: "optimizer", a record of the catalogue, and "per_optimizer" (task 22); a file before
#          has none, and nothing changes in it. A format of its own for the same reason as 12: an older Meridiana
#          rewrites the list of the inverters at the first change of a count and would drop them in silence
# 13 -> 14: no string is made by itself any longer: a variant whose strings were Meridiana's live proposal keeps it as
#          "auto", written down as the designer's at the first layout (_to_14); an older Meridiana would read a file of
#          14 without strings as «automatic» and lay them by itself
# 14 -> 15: optional grid data, initialized from the existing rule inputs (_to_15)
# 15 -> 16: per-project consents for coordinates sent to map and weather services, none before
# 16 -> 17: embedded report attachments, author profile and weather, empty for a project of before
# 17 -> 18: job and project-series identity, empty until the project is linked to a local registry
# 20 -> 21: a parking canopy is a structure, a building with `canopy` (R281): the canopies made as sub-fields on
#           planes of their own are recognised and become one, their slopes on its pitches; the slopes changed by
#           hand stay sub-fields; the designer is told both (_to_21)
MIGRATIONS: dict = {1: lambda data: data, 2: lambda data: data,
                    3: lambda data: {**data, "variants": [{"id": "v1", "name": "Base", "note": ""}], "variant": "v1"},
                    4: lambda data: data, 5: lambda data: {**data, "underlays": data.get("underlays", [])},
                    6: _to_7, 7: _to_8, 8: _to_9, 9: _to_10, 10: lambda data: {**data, "report": data.get("report", {})},
                    11: lambda data: {**data, "reserved": data.get("reserved", False)}, 12: lambda data: data,
                    13: _to_14, 14: _to_15, 15: lambda data: {**data, "network_consent": data.get("network_consent", {})},
                    16: lambda data: {**data, "resources": data.get("resources", {}), "climate": data.get("climate", {})},
                    17: lambda data: {**data, "job_id": data.get("job_id", ""),
                                     "series_id": data.get("series_id", "")},
                    18: lambda data: {**data, "bim_id": data.get("bim_id") or str(uuid.uuid5(
                        uuid.NAMESPACE_URL, "meridiana:legacy:" + (data.get("series_id") or
                        repr((data.get("created", ""), data.get("job_id", ""), data.get("name", ""))))))},
                    19: lambda data: data,  # optional explicit optimizer groups; absent keeps legacy order
                    20: _to_21}
# the keys of a sub-field's params that say where its strings go (task 16d): never a reason to lay it out again
ELECTRICAL = ("inverter", "mppt")
ROOF_TYPES = ("flat", "mono", "gable", "hip", "free")
EDGE_KINDS = ("eave", "gable")           # what a side of a gable or hip roof is (task 16a)
PITCHED = ("gable", "hip")               # the roofs that follow the outline with the skeleton
EXCLUSION_KINDS = ("vent", "opening", "plant", "skylight", "chimney", "tree", "walkway", "other")
# how high above the roof (or the ground) an exclusion of each kind usually rises, in metres: indicative
# defaults, to be measured on the site; zero casts no shadow
OBSTACLE_HEIGHTS = {"vent": 0.5, "opening": 0.0, "plant": 1.5, "skylight": 0.4, "chimney": 1.0, "tree": 8.0,
                    "walkway": 0.0, "other": 0.0}


PARAPET_THICKNESS = 0.25         # m, for the 3D view and the shadows


def exclusion_names() -> dict:
    """What each kind of exclusion is called (the window's lists, the checks: «Skylight 2»)."""
    from .i18n import _
    return {"vent": _("Smoke vent (EFC)"), "opening": _("Opening"), "plant": _("Roof plant"),
            "skylight": _("Skylight"), "chimney": _("Chimney"), "tree": _("Tree"), "walkway": _("Walkway"),
            "other": _("Other")}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parapet_quads(footprint, thickness: float = PARAPET_THICKNESS) -> list[list[tuple[float, float]]]:
    """A parapet along each side of an outline, as plan quadrilaterals inside it."""
    ring = [(float(x), float(y)) for x, y in footprint]
    area = 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1], strict=True))
    out = []
    for a, b in zip(ring, ring[1:] + ring[:1], strict=True):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length < 1e-6:
            continue
        ix, iy = (-dy / length, dx / length) if area > 0 else (dy / length, -dx / length)    # inwards
        out.append([a, b, (b[0] + ix * thickness, b[1] + iy * thickness), (a[0] + ix * thickness, a[1] + iy * thickness)])
    return out


def roof_z(building, ring) -> list[float]:
    """The height of a building's roof at the plan points given: on the pitch they lie on, or the nearest."""
    from shapely.geometry import Point, Polygon
    pitches = building.pitches()
    if not pitches:
        return [building.height for _p in ring]
    shapes = [Polygon(pt.ring) for pt in pitches]
    out = []
    for x, y in ring:
        here = Point(x, y)
        k = min(range(len(pitches)), key=lambda i: shapes[i].distance(here))
        out.append(pitches[k].z(x, y))
    return out


@dataclass
class Site:
    lat: float = 45.4642
    lon: float = 9.1900
    address: str = ""


@dataclass
class Network:
    distributor: str = ""
    pod: str = ""
    voltage_v: float = 0.0
    phases: str = ""
    level: str = ""                 # "", BT, MT, AT: chosen, never guessed from power
    connection: str = ""            # "", existing, new, modification
    available_kw: float = 0.0       # the existing supply, 0 when not stated
    requested_kw: float = 0.0       # the new PV connection, a different datum
    practice_code: str = ""

    def technical_rule(self) -> str:
        if self.voltage_v <= 0:
            return ""
        return "CEI 0-21" if self.voltage_v <= 1000 else "CEI 0-16"


@dataclass
class Roof:
    type: str = "flat"
    eave_side: int = 0            # mono: the side the plane goes down to
    # formats 5-8: the ridge of a gable parallel to this side; read by the migration to 9 (edges), then unused;
    # it goes with the next format
    ridge_along: int | None = None
    tilt: float = 0.0             # degrees
    free_pitches: list = field(default_factory=list)   # [{"id", "ring", "eave_side", "eave", "tilt"}]
    # gable and hip (format 9): "eave" or "gable" for each side of the outline; empty, or not one for each side
    # (the outline changed), the type's own: a gable's ends on its arms (roofs.default_gables), a hip all eaves
    edges: list = field(default_factory=list)
    ridge_height: float | None = None   # gable and hip: m above the ground; given, the slope is worked out from it
    covering: str = ""            # what covers it (roofs.COVERINGS): what proposes the slope; "" not said


@dataclass
class Fire:
    subject: bool = False         # activity subject to fire-brigade control (DPR 151/2011)
    category: str = ""            # A, B, C
    roof_fire_resistant: bool = False


PILLARS = ("cantilever", "two_rows")     # a canopy's columns: one line under its high edge, or one at each long edge


@dataclass
class Canopy:
    """A parking canopy's structure (R281, study 22, 3.7; format 21). The building that holds it gives what it shares
    with a building: its outline (a rectangle, the first side along the rows of spaces), the height under its low
    edge (Building.height), its roof plane (one slope, "mono", or two opposed slopes meeting at a ridge, "gable");
    this says how many spaces and rows it covers and how its columns stand. Its walls are none: columns and beams
    of indicative sizes (canopies.structure), never a structural design."""
    bays: int = 4                 # parking spaces along each row
    rows: int = 1                 # 1: one row under one slope; 2: two rows under opposed slopes
    pillars: str = "cantilever"   # PILLARS
    columns: int = 0              # columns on each line; 0: one every two spaces, the two ends included


class OpenRoof(list):
    """The pitches of a roof that stands on columns, with no walls under it (a canopy): mesh draws no walls."""
    open = True


@dataclass
class Building:
    id: str
    name: str
    footprint: list
    height: float = 10.0          # eave height, or the roof level of a flat roof
    roof: Roof = field(default_factory=Roof)
    fire: Fire = field(default_factory=Fire)
    parapet: float = 0.0          # height of the parapet above a flat roof, all round the outline
    canopy: Canopy | None = None  # a parking canopy: its structure (format 21), the height the one under its low edge

    def __post_init__(self):
        if isinstance(self.canopy, dict):       # read from a file or a snapshot (R281)
            names = {f.name for f in dataclasses.fields(Canopy)}
            self.canopy = Canopy(**{k: v for k, v in self.canopy.items() if k in names})

    def geometry_key(self) -> str:
        """Everything of the building that stands in space (outline, height, roof, parapet, a canopy's structure)
        as one string: the name and the fire data are not in it. Equal keys, the same shape, the same shadows, the
        same pitches."""
        import json
        shape = {"footprint": self.footprint, "height": self.height, "roof": asdict(self.roof),
                 "parapet": self.parapet}
        if self.canopy is not None:             # R281: only when there is one, so the other keys stay as they were
            shape["canopy"] = asdict(self.canopy)
        return json.dumps(shape, sort_keys=True, default=str)

    def pitches(self) -> list[roofs.Pitch]:
        """The pitches of the roof, kept until the geometry changes (the key says): the views, the shadows and
        the layouts ask for them many times for the same roof. Not a field: never in the file nor compared."""
        return self._roof()[1]

    def _roof(self) -> tuple:
        """(key, pitches, problem, the kind of each side), kept until the geometry changes: the properties ask
        for the sides at every refresh, and the default gables cost a skeleton."""
        key = self.geometry_key()
        cached = self.__dict__.get("_pitches_cache")
        if cached is not None and cached[0] == key:
            return cached
        kinds = self._sides_kind()
        found, problem = self._pitches(kinds)
        if self.canopy is not None:
            found = OpenRoof(found)             # R281: a canopy's roof stands on its columns
        cached = (key, found, problem, kinds)
        self.__dict__["_pitches_cache"] = cached
        return cached

    def roof_problem(self) -> tuple[str, list[int]]:
        """What the roof could not be as asked: ("", []) when it is; ("gables", sides) when those gable ends had
        to be eaves (a side beside an inner corner, in some outlines); ("outline", []) when the outline cannot
        carry a pitched roof (it crosses itself), which is then flat until the outline is put right."""
        return self._roof()[2]

    def sides_kind(self) -> list[str]:
        """"eave" or "gable" for each side of the outline, as the roof of type gable or hip uses them: the
        designer's (Roof.edges) when there is one for each side, else the type's own (a gable's ends on its
        arms, roofs.default_gables; a hip all eaves)."""
        return list(self._roof()[3])

    def _sides_kind(self) -> list[str]:
        n = len(self.footprint)
        edges = self.roof.edges
        if len(edges) == n and all(e in EDGE_KINDS for e in edges):
            return list(edges)
        ends = roofs.default_gables(self.footprint) if self.roof.type == "gable" else set()
        return ["gable" if i in ends else "eave" for i in range(n)]

    def slope(self) -> float:
        """The slope of the roof in degrees: on a gable or hip roof with its ridge height given, the one worked out
        from it."""
        found = self.pitches()
        if self.roof.type in PITCHED and found and self.roof_problem()[0] != "outline":
            return found[0].tilt
        return self.roof.tilt

    def ridge(self) -> float:
        """The height of the highest point of the roof above the ground (the ridge of a pitched roof)."""
        return max(self.height, roofs.ridge_height(self.pitches()))

    def retyped(self, kind: str) -> dict:
        """The changes of a new roof type, as the window sends them (`roof.` paths): the type; the sides back to
        the type's own; and, for a pitched roof that had no slope, the covering and the slope it proposes
        (roofs.COVERINGS: 35 % for tiles, Daniel 23/10/2026)."""
        changes: dict = {"roof.type": kind, "roof.edges": []}
        if kind in ("mono", *PITCHED) and self.roof.tilt <= 0:
            covering = self.roof.covering or roofs.DEFAULT_COVERING
            changes["roof.covering"] = covering
            changes["roof.tilt"] = roofs.proposed_tilt(covering)
        return changes

    def with_side(self, side: int, kind: str | None = None) -> list[str]:
        """The sides of the roof with `side` made `kind`: an eave or a gable end; the other one when not given
        (a side clicked on the plan)."""
        edges = self.sides_kind()
        edges[side] = kind or ("eave" if edges[side] == "gable" else "gable")
        return edges

    def pitch_index(self, ref) -> int | None:
        """Where in pitches() is the pitch a sub-field refers to (SubField.pitch): on a gable or hip roof the one
        whose eave is that side (format 9), on the others the one in that place; None when there is none."""
        found = self.pitches()
        if ref is None or ref.__class__ is not int:
            return None
        if self.roof.type in PITCHED:
            return next((i for i, p in enumerate(found) if p.side == ref), None)
        return ref if 0 <= ref < len(found) else None

    def pitch_ref(self, index: int) -> int:
        """What a sub-field on pitches()[index] keeps of its pitch (SubField.pitch): the side of its eave on a gable
        or hip roof, its place on the others."""
        found = self.pitches()
        if self.roof.type in PITCHED and 0 <= index < len(found) and found[index].side is not None:
            return found[index].side
        return index

    def _pitches(self, kinds: list[str]) -> tuple[list[roofs.Pitch], tuple[str, list[int]]]:
        r = self.roof
        fine = ("", [])
        if r.type == "flat":
            return roofs.flat(self.footprint, self.height), fine
        if r.type == "mono":
            return roofs.mono(self.footprint, r.eave_side, self.height, r.tilt), fine
        if r.type in PITCHED:
            gables = {i for i, kind in enumerate(kinds) if kind == "gable"}
            try:
                found, dropped = roofs.pitched(self.footprint, self.height, r.tilt, gables, r.ridge_height)
            except skeleton.SkeletonError:
                return roofs.flat(self.footprint, self.height), ("outline", [])
            return found, (("gables", sorted(dropped)) if dropped else fine)
        from .i18n import _
        out = []
        for i, p in enumerate(r.free_pitches):
            pitch = roofs.free(p["ring"], p["eave_side"], p["eave"], p["tilt"])
            pitch.side, pitch.name = None, _("pitch {n}").format(n=i + 1)
            out.append(pitch)
        return out, fine


@dataclass
class ExclusionItem:
    id: str
    ring: list
    kind: str = "other"
    clearance: float = 0.0
    building: str | None = None
    height: float | None = None   # above the roof or the ground; None: the default of its kind

    def obstacle_height(self) -> float:
        return float(self.height) if self.height is not None else OBSTACLE_HEIGHTS.get(self.kind, 0.0)


@dataclass
class SupportPlane:
    """An explicitly enabled placement plane in the site's local metres, independent of a polygon's edges."""
    enabled: bool = True
    tilt: float = 0.0
    azimuth: float = 0.0
    z0: float = 0.0
    x0: float = 0.0
    y0: float = 0.0

    def surface(self) -> layout.Surface:
        return layout.Surface(tilt=self.tilt, azimuth=self.azimuth, z0=self.z0, x0=self.x0, y0=self.y0)


@dataclass
class SubField:
    id: str
    name: str
    ring: list
    building: str | None = None   # None: on the ground
    pitch: int | None = None      # index of the building's pitch it lies on
    module: str = "generic-450"
    params: dict = field(default_factory=dict)       # layout.Params fields that differ from the defaults
    filled: bool = False          # modules laid only when the designer asks
    removed: list = field(default_factory=list)      # module keys taken out by hand
    # the rows by hand (task 16c), layout.Row.as_dict each: kept as they are while `manual`; the automatic layout
    # makes its own otherwise, and `rows` stays empty
    rows: list = field(default_factory=list)
    manual: bool = False
    support: SupportPlane | None = None

    def __post_init__(self):
        if isinstance(self.support, dict):
            names = {f.name for f in dataclasses.fields(SupportPlane)}
            self.support = SupportPlane(**{k: v for k, v in self.support.items() if k in names})

    def hand_rows(self) -> list[layout.Row]:
        return [layout.Row.of(r) for r in self.rows]

    def layout_params(self) -> layout.Params:
        p = layout.Params()
        for k, v in self.params.items():
            if k == "window":
                p.window = sun.DesignWindow(**v)
            elif hasattr(p, k):
                setattr(p, k, v)
        return p


GENERIC_MODULES = {
    "generic-450": {"manufacturer": "Generico", "model": "450 W, 2278 x 1134 mm", "length": 2.278, "width": 1.134,
                    "power_kw": 0.450},
    "generic-550": {"manufacturer": "Generico", "model": "550 W, 2278 x 1134 mm", "length": 2.278, "width": 1.134,
                    "power_kw": 0.550},
}


def _build(kls, raw):
    names = {f.name for f in dataclasses.fields(kls)}
    return kls(**{k: v for k, v in raw.items() if k in names})


# Reading a file: what a damaged or hand-edited project may hold, said with the path of the key ("buildings[2].height:
# 1e+300 is beyond 1000") instead of a crash later in the layout, the 3D view or the tiles (study 18, A 5.1 and G 6.1).
# The limits are generous: they are there to stop nonsense (NaN, 1e308, a ring of text), not to judge a design.
COORD_LIMIT = 1.0e6             # m from the site's origin: a plan is never that wide
HEIGHT_LIMIT = 1000.0           # m: eave heights, parapets, obstacles
IMAGE_SIDE_LIMIT = 20000        # pixels of an image under the drawing
IMAGE_BYTES_LIMIT = 64 << 20    # of its base64 text: the file would be unusable anyway


def _is_number(value) -> bool:
    return value.__class__ in (int, float) and math.isfinite(value)


def _check_number(value, path: str, lo: float | None = None, hi: float | None = None) -> float:
    if not _is_number(value):
        raise ValueError(f"{path}: {value!r} is not a number")
    if lo is not None and value < lo or hi is not None and value > hi:
        raise ValueError(f"{path}: {value!r} is outside {lo} to {hi}")
    return float(value)


def _check_ring(value, path: str, least: int) -> None:
    if value.__class__ is not list:
        raise ValueError(f"{path}: {value!r} is not a list of points")
    if len(value) < least:
        raise ValueError(f"{path}: {len(value)} points, at least {least} needed")
    for i, point in enumerate(value):
        if point.__class__ not in (list, tuple) or len(point) != 2:
            raise ValueError(f"{path}[{i}]: {point!r} is not a point [x, y]")
        for coord in point:
            _check_number(coord, f"{path}[{i}]", -COORD_LIMIT, COORD_LIMIT)


def _check_dict(value, path: str) -> dict:
    if value.__class__ is not dict:
        raise ValueError(f"{path}: {value!r} is not a table")
    return value


def _check_fields(kls, raw: dict, path: str, unknown: list[str]) -> None:
    """Every key of `raw` against the dataclass: the required ones present, each of the type of its default
    (a switch, a whole number, a number, text, a list, a table; None where the default is None), the rest
    reported in `unknown` and ignored."""
    seen = set()
    for f in dataclasses.fields(kls):
        seen.add(f.name)
        required = f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING
        if f.name not in raw:
            if required:
                raise ValueError(f"{path}: the key '{f.name}' is missing")
            continue
        value = raw[f.name]
        if value is None and (f.default is None or not required):
            if f.default is None:
                continue
        kind = f.default.__class__ if f.default is not dataclasses.MISSING else None
        if required:
            kind = {"id": str, "name": str, "footprint": list, "ring": list}.get(f.name)
        if f.default_factory is not dataclasses.MISSING:
            kind = f.default_factory().__class__
        if kind is bool and value.__class__ is not bool:
            raise ValueError(f"{path}.{f.name}: {value!r} is not a switch")
        elif kind is int and (value.__class__ is not int):
            raise ValueError(f"{path}.{f.name}: {value!r} is not a whole number")
        elif kind is float and not _is_number(value):
            raise ValueError(f"{path}.{f.name}: {value!r} is not a number")
        elif kind is str and value.__class__ is not str:
            raise ValueError(f"{path}.{f.name}: {value!r} is not text")
        elif kind is list and value.__class__ is not list:
            raise ValueError(f"{path}.{f.name}: {value!r} is not a list")
        elif kind is dict and value.__class__ is not dict:
            raise ValueError(f"{path}.{f.name}: {value!r} is not a table")
        elif kind is None and f.default is None and value is not None:
            # a field whose default is None: an int, a number or text by its name (ridge_along, pitch, height,
            # building)
            if f.name in ("ridge_along", "pitch") and value.__class__ is not int:
                raise ValueError(f"{path}.{f.name}: {value!r} is not a whole number")
            if f.name in ("height", "ridge_height") and not _is_number(value):
                raise ValueError(f"{path}.{f.name}: {value!r} is not a number")
            if f.name == "building" and value.__class__ is not str:
                raise ValueError(f"{path}.{f.name}: {value!r} is not text")
    unknown.extend(f"{path}.{k}" for k in raw if k not in seen)


def _check_design(design: dict, path: str, ids: set[str], unknown: list[str]) -> None:
    """A variant's design: its sub-fields (ids unique in the variant and apart from the buildings' and the
    exclusions'), its modules, its energy and economics settings (settings.py)."""
    for key in ("energy", "economics"):
        if design.get(key) is not None:
            settings.check(key, _check_dict(design[key], f"{path}.{key}"), unknown, f"{path}.{key}")
    modules = design.get("modules")
    if modules is not None:
        for mid, m in _check_dict(modules, f"{path}.modules").items():
            m = _check_dict(m, f"{path}.modules[{mid}]")
            for key in ("length", "width", "power_kw"):
                if key not in m:
                    raise ValueError(f"{path}.modules[{mid}]: the key '{key}' is missing")
                _check_number(m[key], f"{path}.modules[{mid}].{key}", 1e-6, 1e6)
    mine: set[str] = set()
    for i, raw in enumerate(design.get("subfields") or []):
        where = f"{path}.subfields[{i}]"
        raw = _check_dict(raw, where)
        _check_fields(SubField, raw, where, unknown)
        _check_ring(raw["ring"], f"{where}.ring", 3)
        if raw["id"] in ids or raw["id"] in mine:
            raise ValueError(f"{where}.id: '{raw['id']}' is used twice")
        mine.add(raw["id"])
        _check_rows(raw.get("rows") or [], f"{where}.rows")
        if raw.get("support") is not None:
            support = _check_dict(raw["support"], f"{where}.support")
            _check_fields(SupportPlane, support, f"{where}.support", unknown)
            if type(support.get("enabled", True)) is not bool:
                raise ValueError(f"{where}.support.enabled: expected a switch")
            for key, low, high in (("tilt", 0.0, 89.0), ("azimuth", -180.0, 180.0),
                                   ("z0", -HEIGHT_LIMIT, HEIGHT_LIMIT),
                                   ("x0", -COORD_LIMIT, COORD_LIMIT), ("y0", -COORD_LIMIT, COORD_LIMIT)):
                _check_number(support.get(key, 0.0), f"{where}.support.{key}", low, high)
    unknown.extend(f"{path}.{k}" for k in design if k not in DESIGN)


def _check_rows(rows: list, path: str) -> None:
    """The rows by hand of a sub-field (layout.Row.as_dict): an id each, once; the origin and the azimuth numbers;
    the places numbers; the keys text; turned a switch."""
    seen: set = set()
    for i, raw in enumerate(rows):
        where = f"{path}[{i}]"
        raw = _check_dict(raw, where)
        if raw.get("id").__class__ is not str or not raw["id"]:
            raise ValueError(f"{where}.id: {raw.get('id')!r} is not text")
        if raw["id"] in seen:
            raise ValueError(f"{where}.id: '{raw['id']}' is used twice")
        seen.add(raw["id"])
        for key in ("x", "y"):
            _check_number(raw.get(key), f"{where}.{key}", -COORD_LIMIT, COORD_LIMIT)
        _check_number(raw.get("azimuth"), f"{where}.azimuth", -360.0, 360.0)
        places = raw.get("places", [])
        if places.__class__ is not list:
            raise ValueError(f"{where}.places: {places!r} is not a list")
        for j, u in enumerate(places):
            _check_number(u, f"{where}.places[{j}]", -COORD_LIMIT, COORD_LIMIT)
        keys = raw.get("keys", [])
        if keys.__class__ is not list or any(k.__class__ is not str for k in keys):
            raise ValueError(f"{where}.keys: {keys!r} is not a list of text")
        if raw.get("turned", False).__class__ is not bool:
            raise ValueError(f"{where}.turned: {raw.get('turned')!r} is not a switch")


def _check_project(data: dict) -> list[str]:
    """ValueError with the path of the first thing that is not a project; the list of the keys the program
    does not know (kept out, said to the designer)."""
    unknown: list[str] = []
    if data.get("name", "").__class__ is not str:
        raise ValueError(f"name: {data.get('name')!r} is not text")
    site = _check_dict(data.get("site", {}), "site")
    _check_fields(Site, site, "site", unknown)
    _check_number(site.get("lat", 0.0), "site.lat", -90.0, 90.0)
    _check_number(site.get("lon", 0.0), "site.lon", -180.0, 180.0)
    _check_dict(data.get("climate", {}), "climate")
    window = _check_dict(data.get("sun_window", {}), "sun_window")
    _check_fields(sun.DesignWindow, window, "sun_window", unknown)
    if data.get("consumption") is not None:
        settings.check("consumption", _check_dict(data["consumption"], "consumption"), unknown)
    if data.get("rules") is not None:
        _check_dict(data["rules"], "rules")
    network = _check_dict(data.get("network", {}), "network")
    _check_fields(Network, network, "network", unknown)
    _check_number(network.get("voltage_v", 0.0), "network.voltage_v", 0.0, 1_000_000.0)
    _check_number(network.get("available_kw", 0.0), "network.available_kw", 0.0, 1_000_000_000.0)
    _check_number(network.get("requested_kw", 0.0), "network.requested_kw", 0.0, 1_000_000_000.0)
    if network.get("phases", "") not in ("", "1", "3"):
        raise ValueError(f"network.phases: {network.get('phases')!r} is not one of '', '1', '3'")
    if network.get("level", "") not in ("", "BT", "MT", "AT"):
        raise ValueError(f"network.level: {network.get('level')!r} is not one of '', BT, MT, AT")
    if network.get("connection", "") not in ("", "existing", "new", "modification"):
        raise ValueError(f"network.connection: {network.get('connection')!r} is not a connection kind")
    if data.get("reserved", False).__class__ is not bool:
        raise ValueError(f"reserved: {data.get('reserved')!r} is not a switch")
    consent = _check_dict(data.get("network_consent", {}), "network_consent")
    for service, day in consent.items():
        if service not in ("tiles", "pvgis") or not isinstance(day, str):
            raise ValueError(f"network_consent.{service}: {day!r} is not a consent date")
        try:
            datetime.strptime(day, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"network_consent.{service}: {day!r} is not an ISO date") from None
    ids: set[str] = set()
    for i, raw in enumerate(data.get("buildings") or []):
        path = f"buildings[{i}]"
        raw = _check_dict(raw, path)
        _check_fields(Building, raw, path, unknown)
        _check_ring(raw["footprint"], f"{path}.footprint", 3)
        _check_number(raw.get("height", 10.0), f"{path}.height", 0.0, HEIGHT_LIMIT)
        _check_number(raw.get("parapet", 0.0), f"{path}.parapet", 0.0, HEIGHT_LIMIT)
        roof = _check_dict(raw.get("roof", {}), f"{path}.roof")
        _check_fields(Roof, roof, f"{path}.roof", unknown)
        if roof.get("type", "flat") not in ROOF_TYPES:
            raise ValueError(f"{path}.roof.type: {roof.get('type')!r} is not one of {', '.join(ROOF_TYPES)}")
        _check_number(roof.get("tilt", 0.0), f"{path}.roof.tilt", 0.0, 89.0)
        for j, kind in enumerate(roof.get("edges", [])):
            if kind not in EDGE_KINDS:
                raise ValueError(f"{path}.roof.edges[{j}]: {kind!r} is not one of {', '.join(EDGE_KINDS)}")
        if roof.get("ridge_height") is not None:
            _check_number(roof["ridge_height"], f"{path}.roof.ridge_height", 0.0, HEIGHT_LIMIT)
        if roof.get("covering", "") not in ("", *roofs.COVERINGS):
            raise ValueError(f"{path}.roof.covering: {roof.get('covering')!r} is not one of "
                             f"{', '.join(roofs.COVERINGS)}")
        for j, pitch in enumerate(roof.get("free_pitches", [])):
            pitch = _check_dict(pitch, f"{path}.roof.free_pitches[{j}]")
            _check_ring(pitch.get("ring", []), f"{path}.roof.free_pitches[{j}].ring", 3)
            if pitch.get("id", "").__class__ is not str:
                raise ValueError(f"{path}.roof.free_pitches[{j}].id: {pitch.get('id')!r} is not text")
        _check_fields(Fire, _check_dict(raw.get("fire", {}), f"{path}.fire"), f"{path}.fire", unknown)
        if raw.get("canopy") is not None:      # R281, format 21
            canopy = _check_dict(raw["canopy"], f"{path}.canopy")
            _check_fields(Canopy, canopy, f"{path}.canopy", unknown)
            if not 1 <= canopy.get("bays", 1) <= 100:
                raise ValueError(f"{path}.canopy.bays: {canopy['bays']!r} is not between 1 and 100")
            if canopy.get("rows", 1) not in (1, 2):
                raise ValueError(f"{path}.canopy.rows: {canopy['rows']!r} is not 1 or 2")
            if canopy.get("pillars", "cantilever") not in PILLARS:
                raise ValueError(f"{path}.canopy.pillars: {canopy['pillars']!r} is not one of {', '.join(PILLARS)}")
            if not 0 <= canopy.get("columns", 0) <= 200:
                raise ValueError(f"{path}.canopy.columns: {canopy['columns']!r} is not between 0 and 200")
        if raw["id"] in ids:
            raise ValueError(f"{path}.id: '{raw['id']}' is used twice")
        ids.add(raw["id"])
    for i, raw in enumerate(data.get("exclusions") or []):
        path = f"exclusions[{i}]"
        raw = _check_dict(raw, path)
        _check_fields(ExclusionItem, raw, path, unknown)
        _check_ring(raw["ring"], f"{path}.ring", 3)
        if raw.get("kind", "other") not in EXCLUSION_KINDS:
            raise ValueError(f"{path}.kind: {raw.get('kind')!r} is not one of {', '.join(EXCLUSION_KINDS)}")
        if raw.get("height") is not None:
            _check_number(raw["height"], f"{path}.height", 0.0, HEIGHT_LIMIT)
        _check_number(raw.get("clearance", 0.0), f"{path}.clearance", 0.0, COORD_LIMIT)
    for i, raw in enumerate(data.get("underlays") or []):
        path = f"underlays[{i}]"
        raw = _check_dict(raw, path)
        _check_fields(Underlay, raw, path, unknown)
        for key in ("width", "height"):
            _check_number(raw.get(key, 0), f"{path}.{key}", 0, IMAGE_SIDE_LIMIT)
        if len(raw.get("image", "")) > IMAGE_BYTES_LIMIT:
            raise ValueError(f"{path}.image: {len(raw['image']) >> 20} MB, beyond {IMAGE_BYTES_LIMIT >> 20} MB")
        _check_number(raw.get("scale", 0.05), f"{path}.scale", 1e-9, COORD_LIMIT)
        for key in ("x", "y"):
            _check_number(raw.get(key, 0.0), f"{path}.{key}", -COORD_LIMIT, COORD_LIMIT)
    variants = data.get("variants")
    if variants.__class__ is not list or not variants:
        raise ValueError(f"variants: {variants!r} is not a list of variants")
    if data.get("variant") is not None and data["variant"].__class__ is not str:
        raise ValueError(f"variant: {data['variant']!r} is not text")
    seen: set[str] = set()
    for i, v in enumerate(variants):
        v = _check_dict(v, f"variants[{i}]")
        if v.get("id").__class__ is not str:
            raise ValueError(f"variants[{i}].id: {v.get('id')!r} is not text")
        if v["id"] in seen:
            raise ValueError(f"variants[{i}].id: '{v['id']}' is used twice")
        seen.add(v["id"])
        if v.get("name", "").__class__ is not str:
            raise ValueError(f"variants[{i}].name: {v.get('name')!r} is not text")
        if v.get("design") is not None:         # a variant without one (a file written by hand) is empty
            _check_design(_check_dict(v["design"], f"variants[{i}].design"), f"variants[{i}].design", ids, unknown)
        unknown.extend(f"variants[{i}].{k}" for k in v if k not in ("id", "name", "note", "design"))
    if data.get("report") is not None:
        _check_dict(data["report"], "report")
    if data.get("resources") is not None:
        _check_dict(data["resources"], "resources")
    for key in ("job_id", "series_id"):
        if key in data and type(data[key]) is not str:
            raise ValueError(f"{key}: {data[key]!r} is not text")
    try:
        uuid.UUID(data.get("bim_id", ""))
    except (ValueError, AttributeError, TypeError):
        raise ValueError("bim_id: expected a UUID") from None
    known = {"format", "version", "app_version", "name", "site", "climate", "sun_window", "buildings", "exclusions",
             "consumption", "rules", "network", "network_consent", "variants", "variant", "underlays", "report",
             "resources", "reserved", "created", "modified", "job_id", "series_id", "bim_id"}
    unknown.extend(k for k in data if k not in known)
    return unknown


@dataclass
class Project:
    name: str = "Nuovo progetto"
    job_id: str = ""
    series_id: str = ""
    bim_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    site: Site = field(default_factory=Site)
    climate: dict = field(default_factory=dict)       # PVGIS's raw typical year and horizon, shared by the variants
    sun_window: dict = field(default_factory=lambda: asdict(sun.DesignWindow()))
    buildings: list[Building] = field(default_factory=list)
    subfields: list[SubField] = field(default_factory=list)
    exclusions: list[ExclusionItem] = field(default_factory=list)
    modules: dict = field(default_factory=lambda: {k: dict(v) for k, v in GENERIC_MODULES.items()})
    # the energy side, each a dict of what differs from the defaults (energy.system, energy.consumption,
    # energy.economics read them): losses, inverter, thermal cases; the consumption of the POD; the money
    energy: dict = field(default_factory=dict)
    consumption: dict = field(default_factory=dict)
    economics: dict = field(default_factory=dict)
    # what the rules of rules.py need beyond the drawing: "connection" (auto, BT, MT, AT), "obligation"
    # ("", none, new, renovation), "public", "use", "permit_2027"; for DM 37/2008 art. 5: "contracted_kw" and
    # "floor_m2" (0: not stated), "premises" ("", productive, domestic, condominium), "risk"
    rules: dict = field(default_factory=dict)
    network: Network = field(default_factory=Network)
    # the variants in their order, {"id", "name", "note"}: in the file every one of them has its "design" (the
    # DESIGN fields, as JSON); in memory the one being worked on ("variant") has it in the fields above, as the
    # working copy, and no "design" key (to_json puts it back, from_json takes it out)
    variants: list = field(default_factory=lambda: [{"id": "v1", "name": "Base", "note": ""}])
    variant: str = "v1"
    # images under the drawing (underlay.py), in the order they are laid: shared by the variants, as the site
    underlays: list[Underlay] = field(default_factory=list)
    # the report's choices, shared by the variants (reports.settings reads them with their defaults): "template",
    # "off" (the chapters turned off), "profile" (the author's, by name; "" none), "client", "address", "revision",
    # "attachments" ({"path", "title"}: the paths absolute here, relative to the file in it, reports.portable),
    # "register" (the register of the calculations exported with the report)
    report: dict = field(default_factory=dict)
    # attachments, the selected author profile and the weather, embedded so that the file opens on another PC
    resources: dict = field(default_factory=dict)
    # reserved: Meridio never sends anything of it to a cloud model, whatever the settings say (task 14; study 14,
    # 6.6); the local model is the only one that reads it
    reserved: bool = False
    # coordinates may leave a reserved project only to these services, after its own consent (ISO date each)
    network_consent: dict = field(default_factory=dict)
    created: str = field(default_factory=_now)
    modified: str = field(default_factory=_now)

    def sync_network(self) -> None:
        """Keep the rule inputs already used by rules.py, without inventing missing supply data."""
        rules = dict(self.rules)
        if self.network.available_kw > 0:
            rules["contracted_kw"] = self.network.available_kw
        if self.network.level:
            rules["connection"] = self.network.level
        elif self.network.voltage_v > 0:
            rules["connection"] = "BT" if self.network.voltage_v <= 1000 else "MT"
        self.rules = rules

    def online_allowed(self, service: str, configured: bool) -> bool:
        """Whether this service may receive project data now, under both the global and project choices."""
        if not configured:
            return False
        if not self.reserved:
            return True
        return service in ("tiles", "pvgis") and bool(self.network_consent.get(service))

    # ids

    def new_id(self, prefix: str) -> str:
        used = {x.id for x in (*self.buildings, *self.subfields, *self.exclusions, *self.underlays)}
        n = 1
        while f"{prefix}{n}" in used:
            n += 1
        return f"{prefix}{n}"

    def building(self, bid: str | None) -> Building | None:
        return next((b for b in self.buildings if b.id == bid), None)

    def exclusion_numbers(self) -> dict:
        """id -> its number among the exclusions of its kind, in the order drawn: «Skylight 2» rather than «e7»
        (study 12, N3)."""
        seen: dict = {}
        out = {}
        for e in self.exclusions:
            seen[e.kind] = seen.get(e.kind, 0) + 1
            out[e.id] = seen[e.kind]
        return out

    def duplicate(self, kind: str, oid: str, offset: tuple = (1.0, -1.0)) -> str:
        """A copy of a building, a sub-field or an exclusion, `offset` metres away (East, North), with an id of its
        own; a sub-field's copy has no modules laid until asked. The new id; ValueError for nothing to copy."""
        from .i18n import _
        found = {"building": self.buildings, "subfield": self.subfields, "exclusion": self.exclusions}.get(kind, [])
        thing = next((x for x in found if x.id == oid), None)
        if thing is None:
            raise ValueError(f"no {kind} {oid}")
        import copy as _copy

        def moved(ring):
            return [[round(float(x) + offset[0], 4), round(float(y) + offset[1], 4)] for x, y in ring]
        copy = dataclasses.replace(thing, id=self.new_id({"building": "b", "subfield": "s", "exclusion": "e"}[kind]))
        attr = "footprint" if kind == "building" else "ring"
        setattr(copy, attr, moved(getattr(thing, attr)))
        if kind == "building":
            copy.roof = _copy.deepcopy(thing.roof)
            copy.fire = _copy.deepcopy(thing.fire)
            copy.canopy = _copy.deepcopy(thing.canopy)      # R281: its own structure, not the original's
            # the pitches drawn by hand are in the site's coordinates too: left behind, the copy's roof stood
            # on the original, with its shadows and the pitches its sub-fields lie on (review, 23/10/2026)
            for pitch in copy.roof.free_pitches:
                pitch["ring"] = moved(pitch["ring"])
        if kind in ("building", "subfield"):
            copy.name = _("{name} (copy)").format(name=thing.name)
        if kind == "subfield":
            copy.params, copy.removed, copy.filled = _copy.deepcopy(thing.params), [], False
            copy.rows, copy.manual = [], False
            copy.support = _copy.deepcopy(thing.support)
            if copy.support is not None:
                copy.support.x0 += offset[0]
                copy.support.y0 += offset[1]
        found.append(copy)
        return copy.id

    # variants

    def design(self) -> dict:
        """The design of the variant being worked on, as JSON (a copy)."""
        import copy
        return copy.deepcopy({"subfields": [asdict(s) for s in self.subfields], "modules": self.modules,
                              "energy": self.energy, "economics": self.economics})

    def set_design(self, design: dict) -> None:
        import copy
        d = copy.deepcopy(design)
        self.subfields = [_build(SubField, raw) for raw in d.get("subfields", [])]
        self.modules = d.get("modules") or {k: dict(v) for k, v in GENERIC_MODULES.items()}
        self.energy = d.get("energy") or {}
        self.economics = d.get("economics") or {}

    def current_variant(self) -> dict:
        return next(v for v in self.variants if v["id"] == self.variant)

    def design_of(self, vid: str) -> dict:
        """The design of any variant, as JSON; KeyError for a variant that is not there."""
        if vid == self.variant:
            return self.design()
        found = next((v for v in self.variants if v["id"] == vid), None)
        if found is None:
            raise KeyError(vid)
        return found.get("design") or {}

    def switch_variant(self, vid: str) -> None:
        """Work on another variant: the design in hand goes back to its variant, the other's comes out (empty,
        for a variant without one). KeyError for a variant that is not there."""
        if vid == self.variant:
            return
        target = next((v for v in self.variants if v["id"] == vid), None)
        if target is None:
            raise KeyError(vid)
        self.current_variant()["design"] = self.design()
        self.set_design(target.pop("design", None) or {})
        self.variant = vid

    def add_variant(self, name: str) -> str:
        """A new variant, a copy of the one in hand, placed after it and worked on from now."""
        used = {v["id"] for v in self.variants}
        n = 1
        while f"v{n}" in used:
            n += 1
        vid = f"v{n}"
        at = self.variants.index(self.current_variant()) + 1
        self.current_variant()["design"] = self.design()
        self.variants.insert(at, {"id": vid, "name": name, "note": ""})
        self.variant = vid
        return vid

    def remove_variant(self, vid: str) -> None:
        """Delete a variant; the one in hand cannot go (switch first), nor the last one."""
        if vid == self.variant or len(self.variants) < 2:
            raise ValueError("the variant in hand cannot be deleted")
        self.variants = [v for v in self.variants if v["id"] != vid]

    # what the layout needs

    def surface_of(self, sf: SubField) -> layout.Surface:
        if sf.support is not None and sf.support.enabled:
            return sf.support.surface()
        b = self.building(sf.building)
        if b is None:
            return layout.Surface()
        pitches = b.pitches()
        index = b.pitch_index(sf.pitch)
        p = pitches[index] if index is not None else pitches[0]
        return layout.Surface(tilt=p.tilt, azimuth=p.azimuth, z0=p.z0, x0=p.x0, y0=p.y0)

    def module_of(self, sf: SubField) -> layout.Module:
        m = self.modules.get(sf.module) or GENERIC_MODULES["generic-450"]
        return layout.Module(length=m["length"], width=m["width"], power_kw=m["power_kw"])

    def exclusions_of(self, sf: SubField) -> list[layout.Exclusion]:
        return [layout.Exclusion(ring=[tuple(p) for p in e.ring], kind=e.kind, clearance=e.clearance)
                for e in self.exclusions if e.building == sf.building]

    def obstacle_prisms(self) -> list[dict]:
        """The exclusions that rise above their roof or the ground, and the parapets of the flat roofs, as
        vertical prisms {"ring", "z0", "z1", "kind", "id", "building"}: the 3D view draws them and the
        near shading casts their shadows."""
        out = []
        for e in self.exclusions:
            h = e.obstacle_height()
            if h <= 0 or len(e.ring) < 3:
                continue
            ring = [(float(x), float(y)) for x, y in e.ring]
            b = self.building(e.building)
            zs = roof_z(b, ring) if b is not None else [0.0]
            out.append({"ring": ring, "z0": min(zs), "z1": max(zs) + h, "kind": e.kind, "id": e.id,
                        "building": e.building})
        for b in self.buildings:
            if b.parapet > 0 and b.roof.type == "flat":
                for quad in parapet_quads(b.footprint):
                    out.append({"ring": quad, "z0": b.height, "z1": b.height + b.parapet, "kind": "parapet",
                                "id": b.id, "building": b.id})
            if b.canopy is not None:
                # R281: a canopy's columns and beams, upright boxes: drawn, shading and exported as the obstacles
                from . import canopies
                out.extend(canopies.structure(b))
        return out

    def fill_params(self, sf: SubField) -> layout.Params:
        """The parameters the layout of a sub-field uses: its own, the site's design window unless it has its own,
        the fire-brigade rules when its building is subject to them."""
        p = sf.layout_params()
        if "window" not in sf.params:
            p.window = sun.DesignWindow(**self.sun_window)        # the site's, unless the sub-field has its own
        b = self.building(sf.building)
        if b and b.fire.subject:
            p.fire_rules = True
        return p

    def fill(self, sf: SubField, shade=None) -> layout.Result:
        """The layout of a sub-field. `shade(project, sf, window)` gives the shadows of the obstacles as
        exclusions when the sub-field keeps out of them (energy.system.shadow_exclusions: the model does not
        read the energy side); without it such a sub-field cannot be laid out, and says so. A sub-field laid by
        hand (`manual`, task 16c) is its rows as they are: nothing is laid again, and the shadows and the fire
        rules become checks (checks.manual_items)."""
        p = self.fill_params(sf)
        blocked = self.exclusions_of(sf)
        if sf.manual:
            return layout.compute([tuple(q) for q in sf.ring], self.surface_of(sf), self.module_of(sf), p,
                                  blocked, self.site.lat, self.site.lon, set(sf.removed), rows=sf.hand_rows())
        if p.shade_free:
            if shade is None:
                raise ValueError("keeping out of the shadows needs the shadow function (energy.system.shadow_exclusions)")
            blocked = blocked + shade(self, sf, p.window)
        return layout.compute([tuple(q) for q in sf.ring], self.surface_of(sf), self.module_of(sf), p,
                              blocked, self.site.lat, self.site.lon, set(sf.removed))

    def layout_key(self, sf: SubField) -> str:
        """Everything `fill` reads for this sub-field, as one string: equal keys, the same layout. The sub-field,
        its module, the site and its design day, the geometry of the building it lies on with its fire subjection
        and the exclusions of that building; and, only when the sub-field keeps out of the shadows, the geometry
        of every building and every obstacle (any of them can cast a shadow on it). Not the names, not the other
        sub-fields, not the energy or the economics: a building renamed moves nothing, a height changed lays out
        again only the sub-fields that see it (study 18, A 9.2). As FreeCAD recomputes only the objects a change
        touched (study 15, 3.6), the window lays out again only what this key says changed. Not the inverter and
        the input the sub-field's strings go to (ELECTRICAL): they move no module."""
        import json
        host = self.building(sf.building)
        own = asdict(sf)
        own["params"] = {k: v for k, v in own["params"].items() if k not in ELECTRICAL}
        data = {"sf": own, "module": self.modules.get(sf.module), "site": asdict(self.site),
                "window": self.sun_window,
                "host": [host.geometry_key(), host.fire.subject] if host is not None else None,
                "exclusions": [[e.ring, e.kind, e.clearance] for e in self.exclusions if e.building == sf.building]}
        if sf.layout_params().shade_free and not sf.manual:
            data["shade"] = {"buildings": [b.geometry_key() for b in self.buildings],
                             "obstacles": [[e.ring, e.kind, e.height, e.building] for e in self.exclusions]}
        return json.dumps(data, sort_keys=True, default=str)

    def layout_state(self, sf: SubField, keys: dict, results: dict) -> str:
        """Where a sub-field's layout stands, given the keys and the results of the last layouts: "empty"
        (no modules asked), "stale" (it changed since: to lay out again), "error" (the layout failed, the
        reason in the result) or "ok"."""
        if not sf.filled:
            return "empty"
        if sf.id not in results or keys.get(sf.id) != self.layout_key(sf):
            return "stale"
        return "error" if isinstance(results[sf.id], Exception) else "ok"

    # files

    def to_json(self) -> dict:
        """The project as the file holds it (format 21): every variant with its design, the one in hand too;
        the working copy of the fields above goes into its variant."""
        data = asdict(self)
        for k in DESIGN:
            del data[k]
        for v in data["variants"]:
            if v.get("id") == self.variant:
                v["design"] = self.design()
        data["format"] = FORMAT
        data["version"] = FORMAT_VERSION
        return data

    @classmethod
    def from_json(cls, data, check: bool = True, unknown: list[str] | None = None,
                  notes: list[str] | None = None) -> "Project":
        """The project in `data`. With `check` (every file read from outside) what is not a project raises
        ValueError with the path of the key; `unknown`, if given, collects the keys the program does not
        know; `notes`, if given, what the migration changed that the designer should look at. The window's own
        snapshots pass `check=False`: they were written by `to_json` a moment ago."""
        from .i18n import _
        if not isinstance(data, dict) or data.get("format") != FORMAT:
            raise ValueError(_("not a Meridiana project"))
        data = copy.deepcopy(data)
        version = data.get("version", 0)
        if version.__class__ is not int or version < 1:
            raise ValueError(f"version: {version!r} is not a format number")
        if version > FORMAT_VERSION:
            from .project_archive import FutureVersionError
            raise FutureVersionError(_("made by a newer Meridiana (format {version}); update the program to open it").format(
                version=version))
        if version < 9 and notes is not None:
            reshaped = _reshaped(data)
            if reshaped:
                from .i18n import ngettext
                notes.append(ngettext(
                    "The roof of {names} now follows its outline: check its pitches and the sub-fields on them.",
                    "The roofs of {names} now follow their outlines: check their pitches and the sub-fields on "
                    "them.", len(reshaped)).format(names=", ".join(reshaped)))
        if version < 10 and notes is not None:
            lost = _unreadable(data)
            if lost:
                from .i18n import ngettext
                notes.append(ngettext(
                    "{n} key of a module taken out by hand or in a string by hand was not a row and a place: left out.",
                    "{n} keys of modules taken out by hand or in strings by hand were not a row and a place: left "
                    "out.", lost).format(n=lost))
        while version < FORMAT_VERSION:
            # R281: the migration to 21 tells the designer which canopies became structures
            data = _to_21(data, notes) if version == 20 else MIGRATIONS[version](data)
            version += 1
        if "bim_id" not in data:
            data = MIGRATIONS[18](data)       # hand-authored files without the optional identity
        if check:
            found = _check_project(data)
            if unknown is not None:
                unknown.extend(found)

        build = _build
        p = cls(name=data.get("name", "Progetto"), job_id=data.get("job_id", ""), bim_id=data["bim_id"],
                series_id=data.get("series_id", ""), site=build(Site, data.get("site", {})),
                climate=data.get("climate") or (data.get("resources") or {}).get("weather") or {},
                sun_window=data.get("sun_window", asdict(sun.DesignWindow())),
                consumption=data.get("consumption") or {}, rules=data.get("rules") or {},
                network=build(Network, data.get("network", {})), report=data.get("report") or {},
                resources=data.get("resources") or {},
                variants=data.get("variants") or [{"id": "v1", "name": "Base", "note": ""}],
                variant=data.get("variant") or "v1", reserved=data.get("reserved", False) is True,
                network_consent=dict(data.get("network_consent") or {}),
                created=data.get("created", _now()), modified=data.get("modified", _now()))
        for raw in data.get("buildings", []):
            b = build(Building, raw)
            b.roof = build(Roof, raw.get("roof", {}))
            b.fire = build(Fire, raw.get("fire", {}))
            p.buildings.append(b)
        p.exclusions = [build(ExclusionItem, raw) for raw in data.get("exclusions", [])]
        p.underlays = [build(Underlay, raw) for raw in data.get("underlays", []) if isinstance(raw, dict)
                       and raw.get("id")]
        if not any(v.get("id") == p.variant for v in p.variants):          # a file edited by hand
            p.variant = p.variants[0]["id"]
        p.set_design(p.current_variant().pop("design", None) or {})        # the one in hand: the working copy
        return p

    def save(self, path: Path, cache_dir: Path | None = None, report_profile: dict | None = None) -> None:
        """The project and its external resources written whole or not at all, attachments with relative paths."""
        from . import portability, project_archive, reports
        snapshot = copy.deepcopy(self)
        snapshot.modified = _now()
        portability.embed(snapshot, Path(path), cache_dir, report_profile)
        data = snapshot.to_json()
        data["report"] = reports.portable(data.get("report") or {}, Path(os.path.abspath(path)).parent)
        if Path(path).suffix.casefold() == ".mer":
            project_archive.write(Path(path), data, validate=self.from_json)
        else:
            atomic.write_json(Path(path), data)
        self.modified, self.report, self.resources = snapshot.modified, snapshot.report, snapshot.resources

    @classmethod
    def load(cls, path: Path, cache_dir: Path | None = None) -> tuple["Project", str | None]:
        """The project of the file and, when something is worth saying (the backup was used, keys the program
        does not know were left out, an external resource is missing), the notice; a damaged file raises ValueError
        with the path of the key, an unreadable one OSError."""
        from . import project_archive
        unknown: list[str] = []
        notes: list[str] = []
        notice = None
        try:
            data = project_archive.read_document(Path(path))
            project = cls.from_json(data, unknown=unknown, notes=notes)
        except project_archive.FutureVersionError:
            raise
        except (OSError, ValueError) as error:
            backup = Path(path).with_name(Path(path).name + ".bak")
            if not backup.exists():
                raise
            unknown.clear()
            notes.clear()
            project = cls.from_json(project_archive.read_document(backup), unknown=unknown, notes=notes)
            notice = f"{Path(path).name} could not be read ({type(error).__name__}: {error}); the previous save was opened"
        from . import portability, reports
        project.report = reports.resolved(project.report, Path(os.path.abspath(path)).parent)
        notes.extend(portability.materialize(project, cache_dir))
        for note in notes:
            notice = f"{notice}\n{note}" if notice else note
        if unknown:
            from .i18n import ngettext
            shown = ", ".join(unknown[:8]) + (", ..." if len(unknown) > 8 else "")
            left = ngettext("{n} key this Meridiana does not know was left out: {keys}",
                            "{n} keys this Meridiana does not know were left out: {keys}",
                            len(unknown)).format(n=len(unknown), keys=shown)
            notice = f"{notice}\n{left}" if notice else left
        return project, notice
