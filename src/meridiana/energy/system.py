"""From the project to the energy model: the arrays are the modules laid, grouped by orientation (an
east-west sub-field makes two arrays, one per side); the module is the one the sub-field uses, with its
datasheet; the thermal case follows the mounting unless the designer chose another; the inverters are the
ones chosen (a list since task 16d), or one sized at the default DC/AC ratio, said to be such."""

from __future__ import annotations

import math
from collections import defaultdict

from ..i18n import _
from . import nearshade
from .components import InverterSpec, ModuleSpec
from .simulate import MOUNTING_THERMAL, ArraySpec, Losses, lid_pct


def obstacle_kind_names() -> dict:
    return {"vent": _("smoke vent"), "opening": _("opening"), "plant": _("roof plant"), "skylight": _("skylight"),
            "chimney": _("chimney"), "tree": _("tree"), "walkway": _("walkway"), "other": _("obstacle"),
            "column": _("column"), "beam": _("beam")}


def obstacles_of(project, sf, prisms: list | None = None) -> list:
    """What can cast a shadow on a sub-field's modules, as convex solids: the exclusions that rise above
    their roof or the ground, the parapets, the other buildings with their roofs; and the other pitches of its
    own building, whatever its roof (task 16a: on an L an arm shades the other; on a rectangle the other
    pitches stand behind the plane of the sub-field's and cast nothing). `prisms`: project.obstacle_prisms()
    computed once by the caller when it asks for many sub-fields (it costs a roof height per corner)."""
    names = obstacle_kind_names()
    out = []
    for o in (project.obstacle_prisms() if prisms is None else prisms):
        if o["kind"] == "parapet":
            b = project.building(o["building"])
            name = _("parapet of {name}").format(name=b.name if b else o["id"])
        else:
            name = f"{names.get(o['kind'], o['kind'])} {o['id']}"
        out += nearshade.prism(o["ring"], o["z0"], o["z1"], name)
    for b in project.buildings:
        if b.id == sf.building:
            own = b.pitch_index(sf.pitch)
            for i, pt in enumerate(b.pitches()):
                if i != (own if own is not None else 0) and pt.tilt > 0:
                    out += nearshade.under(pt.corners_3d(), b.height,
                                           _("{name}, {pitch}").format(name=b.name, pitch=pt.name))
            continue
        if b.canopy is not None:        # R281: a canopy is its roof on columns (the columns: obstacle_prisms)
            for pt in b.pitches():
                out += nearshade.under(pt.corners_3d(), b.height - 0.05, b.name)
            continue
        out += nearshade.prism(b.footprint, 0.0, b.height, b.name)
        for pt in b.pitches():
            if pt.tilt > 0:
                out += nearshade.under(pt.corners_3d(), b.height, b.name)
    return out


def shadow_exclusions(project, sf, window) -> list:
    """Where the obstacles cast their shadow on the sub-field's surface in the design window, as areas the
    modules keep out of (layout.Exclusion): the same rule as the row pitch (no shade on that day between
    those hours), drawn on the roof plane or the ground, a little below the modules, so on the safe side.
    `Project.fill` takes it as its `shade` (the model does not read the energy side)."""
    import numpy as np
    import shapely
    from shapely.geometry import Polygon

    from .. import layout
    solids = obstacles_of(project, sf)
    if not solids:
        return []
    surf = project.surface_of(sf)
    n, _e1, _e2 = nearshade.plane_axes(surf.tilt, surf.azimuth)
    d = float(n @ np.array([surf.x0, surf.y0, surf.z0]))
    where = window.positions(project.site.lat, project.site.lon)
    suns = nearshade.sun_vectors([q.bearing for q in where], [q.elevation for q in where])
    suns = suns[(suns[:, 2] > 0.0) & (suns @ n > 1e-6)]
    if not len(suns):
        return []
    plan = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])     # the plan's axes: the shadow seen from above
    pieces = []
    for s in solids:
        hulls = nearshade._hulls(s, n, d, plan, suns)
        if hulls is not None:
            pieces += [h for h in np.atleast_1d(hulls) if not h.is_empty and h.area > 1e-4]
    if not pieces:
        return []
    ring = Polygon([(float(x), float(y)) for x, y in sf.ring])
    shade = shapely.union_all(np.array(pieces, dtype=object)).intersection(ring.buffer(1.0))
    polygons = [g for g in getattr(shade, "geoms", [shade]) if g.geom_type == "Polygon" and g.area > 1e-3]
    return [layout.Exclusion(ring=[(float(x), float(y)) for x, y in g.exterior.coords[:-1]], kind="shadow",
                             holes=[[(float(x), float(y)) for x, y in r.coords[:-1]] for r in g.interiors])
            for g in polygons]


def arrays_of(project, results: dict) -> list[ArraySpec]:
    """`results` maps a sub-field's id to its layout.Result (the filled ones)."""
    out: list[ArraySpec] = []
    prisms = None                   # the obstacles of the project, once for every sub-field (study 18, A 7.2)
    for sf in project.subfields:
        r = results.get(sf.id)
        if not sf.filled or r is None or isinstance(r, Exception) or not r.modules:
            continue
        if prisms is None:
            prisms = project.obstacle_prisms()
        groups: dict = defaultdict(int)
        for pm in r.modules:
            groups[(round(pm.tilt, 1), round(pm.azimuth, 1))] += 1
        module = ModuleSpec.from_record(project.modules.get(sf.module) or {"power_kw": project.module_of(sf).power_kw})
        mounting = sf.layout_params().mounting
        thermal = (project.energy.get("thermal") or {}).get(sf.id) or MOUNTING_THERMAL.get(mounting, "open")
        many = len(groups) > 1
        params = sf.layout_params()
        mod = project.module_of(sf)
        along_slope = mod.length if params.portrait else mod.width
        slant = params.stack * along_slope + (params.stack - 1) * params.stack_gap
        row_based = mounting in ("tilted_anchored", "tilted_ballasted", "ground") and getattr(r, "pitch", 0) > 0
        obstacles = obstacles_of(project, sf, prisms)
        for i, ((tilt, az), n) in enumerate(sorted(groups.items(), key=lambda kv: kv[0][1])):
            side = ""
            if many:
                side = " " + (_("east") if az < -45 else _("west") if az > 45 else _("south") if abs(az) <= 45 else "")
            rows = len({pm.row for pm in r.modules if round(pm.azimuth, 1) == az}) if row_based else 0
            placed = [pm for pm in r.modules if (round(pm.tilt, 1), round(pm.azimuth, 1)) == (tilt, az)]
            out.append(ArraySpec(key=f"{sf.id}.{i}", name=sf.name + side, tilt=float(tilt), azimuth=float(az),
                                 modules=int(n), module=module, thermal=thermal, rows=rows,
                                 pitch=float(r.pitch) if row_based else 0.0, slant=slant if row_based else 0.0,
                                 upright=bool(params.portrait), stack=max(1, int(params.stack)),
                                 stand_off=float(params.stand_off), placed=placed, obstacles=obstacles))
    return out


def inverter_entries(energy: dict | None) -> list[dict]:
    """The inverters of a project's energy settings as {"record", "count", "name"}, the ones with a record: the
    list of format 8, or the one inverter of a dictionary written before it (read as a list of one). An inverter
    at a fixed string voltage keeps its power optimizers (format 13): "optimizer", a record of the catalogue, and
    "per_optimizer", the modules on each (1 or 2)."""
    e = energy or {}
    out = []
    for item in e.get("inverters") or []:
        rec = item.get("record") if item.__class__ is dict else None
        if rec.__class__ is dict and rec:
            count = item.get("count")
            entry = {"record": rec, "count": count if count.__class__ is int and count >= 1 else 1,
                     "name": str(item.get("name") or "")}
            if item.get("optimizer").__class__ is dict and item["optimizer"]:
                entry["optimizer"] = item["optimizer"]
            if item.get("per_optimizer") in (1, 2) and item["per_optimizer"].__class__ is int:
                entry["per_optimizer"] = item["per_optimizer"]
            out.append(entry)
    old = e.get("inverter")
    if not out and old.__class__ is dict and old:
        out.append({"record": old, "count": max(1, int(e.get("inverter_count") or 1)), "name": ""})
    return out


def inverters_of(project, p_stc_w: float) -> list[InverterSpec]:
    """One InverterSpec for each inverter chosen, with its count, in the order of the list; without one that has
    a nominal power, one sized at the DC/AC ratio of the project (said to be such)."""
    e = project.energy or {}
    out = [inv for item in inverter_entries(e)
           if (inv := InverterSpec.from_record(item["record"], count=item["count"])).pac > 0]
    return out or [InverterSpec.sized_for(p_stc_w, float(e.get("dc_ac_ratio") or 1.1))]


def combined(inverters: list[InverterSpec]) -> InverterSpec:
    """The inverters as one for the AC side of the year (simulate): the nominal powers added, the efficiency
    weighted by them, the count of every unit; one model alone is itself. The year with an inverter for each
    input is task 18d (step 3): until then the clipping is on the sum."""
    if len(inverters) == 1:
        return inverters[0]
    from .pedigree import Source
    total = sum(i.pac_total for i in inverters)
    units = sum(i.count for i in inverters)
    eta = sum(i.eta * i.pac_total for i in inverters) / total if total > 0 else 0.97
    phases = {i.phases for i in inverters}
    return InverterSpec(manufacturer=" + ".join(dict.fromkeys(i.manufacturer for i in inverters)),
                        model=" + ".join(f"{i.count} x {i.model}" for i in inverters), pac=total / units, eta=eta,
                        count=units, phases=phases.pop() if len(phases) == 1 else 3,
                        source=Source("computed", _("the inverters of the plant together: {what}").format(
                            what="; ".join(f"{i.count} x {i.manufacturer} {i.model}".strip() for i in inverters))))


def describe(energy: dict | None) -> str:
    """The inverters in a line, as the Production phase and the Plant say them: «2 x Huawei SUN2000-10KTL-M1,
    20 kW AC»; none chosen, how Meridiana sizes one."""
    from ..i18n import number
    entries = inverter_entries(energy)
    if not entries:
        return _("Not chosen: sized by itself at the DC/AC ratio {r}.").format(
            r=number(float((energy or {}).get("dc_ac_ratio") or 1.1), 2))
    parts, total = [], 0.0
    for e in entries:
        rec = e["record"]
        kw = float(rec.get("ac_power_nominal_w") or rec.get("pac") or 0.0) / 1000.0
        total += kw * e["count"]
        name = e["name"] or f"{rec.get('manufacturer', '')} {rec.get('model', '')}".strip()
        parts.append(f"{e['count']} x {name}")
    return _("{what}, {kw} kW AC").format(what=" + ".join(parts), kw=number(total, 1))


def sized_count(p_stc_w: float, ratio: float, record: dict) -> int:
    """How many inverters of `record`, all alike, give the DC/AC ratio asked or a little less (at least one)."""
    pac = float(record.get("ac_power_nominal_w") or record.get("pac") or 0.0)
    if pac <= 0 or p_stc_w <= 0:
        return 1
    return max(1, math.ceil(p_stc_w / max(0.1, ratio) / pac - 1e-9))


def losses_of(project) -> Losses:
    return Losses.from_dict((project.energy or {}).get("losses"))


def pvgis_loss(losses: Losses, inverter_eta: float, module: ModuleSpec | None = None) -> float:
    """The one loss figure PVGIS asks for, from Meridiana's chain: what PVGIS does not model itself
    (soiling, LID, mismatch, wiring at about half their STC value over a year, inverter, unavailability).
    The LID is the one the chain applies to `module` (simulate.lid_pct)."""
    lid = lid_pct(losses, module)
    keep = ((1 - losses.soiling / 100) * (1 - lid / 100) * (1 - losses.mismatch / 100) * (1 - losses.quality / 100)
            * (1 - losses.dc_wiring / 200) * inverter_eta * (1 - losses.ac_wiring / 200) * (1 - losses.unavailability / 100))
    return round(100 * (1 - keep), 1)
