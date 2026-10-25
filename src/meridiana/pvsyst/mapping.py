"""A PVsyst project, with the variants chosen, as a Meridiana project: the site, one Meridiana variant for
each PVsyst variant (sub-fields, modules, inverter, strings, losses, export limit), and the PVsyst results kept
beside them for the comparison. Everything that is approximated, left out or missing is said, in four lists
the window shows before anything is created (docs/studio/10-pvsyst-formati-file.md, 5 and 6).

Geometry: the PV fields of the 3D scene become sub-fields on the ground, at their plan position (PVsyst's
scene frame in the northern hemisphere: X West, Y South; Meridiana's: x East, y North), modules re-laid by
Meridiana with PVsyst's tilt, azimuth, rows, pitch and table. Without a scene (PVsyst's "unlimited" planes)
the modules of an orientation go in one free row, or in rows as wide as the sheds PVsyst describes."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .. import catalog, model
from ..i18n import _, number
from .project import Field, ProjectFile, SubArray, Variant

THERMAL = {29.0: "open", 20.0: "semi", 15.0: "integrated"}
_NORM = re.compile(r"[^0-9a-z]")


@dataclass
class Report:
    read: list = field(default_factory=list)
    approximated: list = field(default_factory=list)
    not_imported: list = field(default_factory=list)
    missing: list = field(default_factory=list)


def _norm(s: str) -> str:
    return _NORM.sub("", (s or "").lower())


_INDEX: dict = {}


def _catalogue(kind: str) -> list:
    if kind not in _INDEX:
        _INDEX[kind] = [(_norm(r.get("model", "")), r) for r in catalog.load(kind) if len(_norm(r.get("model", ""))) >= 5]
    return _INDEX[kind]


def from_catalogue(kind: str, *names: str) -> dict | None:
    """The catalogue's record whose model is written in one of the names (a PVsyst file name, the scene's
    module name): the longest model found, so that "LR5-54HTH-450M" wins over "LR5-54HTH"."""
    hay = [_norm(n) for n in names if n]
    best = None
    for m, rec in _catalogue(kind):
        if any(m in h for h in hay) and (best is None or len(m) > len(best[0])):
            best = (m, rec)
    return best[1] if best else None


def find_file(name: str, base: Path, kind: str) -> Path | None:
    """A component file named by the variant: next to the project, or in a ComposPV folder beside it."""
    if not name:
        return None
    sub = "PVModules" if kind == "module" else "Inverters"
    for d in (base, base / "ComposPV" / sub, base.parent / "ComposPV" / sub, base / sub):
        if d.is_dir():
            for p in d.iterdir():
                if p.name.casefold() == name.casefold():
                    return p
    return None


def _module(name: str, scene_name: str, base: Path, rep: Report, size: tuple = ()) -> tuple[str, dict]:
    from ..catalog import panond
    path = find_file(name, base, "module")
    if path is not None:
        try:
            rec, _said = panond.module(path)
            rep.read.append(_("module {name} from {file}").format(name=f"{rec['manufacturer']} {rec['model']}",
                                                                  file=path.name))
            return f"pan:{rec['manufacturer']} {rec['model']}", catalog.for_project(rec)
        except (OSError, ValueError) as error:
            rep.missing.append(_("{file} could not be read: {error}").format(file=path.name, error=error))
    rec = from_catalogue("modules", name, scene_name)
    if rec is not None:
        rep.approximated.append(_("module {name} from Meridiana's catalogue: {file} was not with the project").format(
            name=f"{rec.get('manufacturer', '')} {rec.get('model', '')}".strip(), file=name))
        return f"cat:{rec.get('manufacturer', '')} {rec.get('model', '')}", catalog.for_project(rec)
    rec = dict(model.GENERIC_MODULES["generic-450"])
    if len(size) == 2 and min(size) > 0.3:          # the scene gives the module's sizes: the fields fit them
        rec["width"], rec["length"] = min(size), max(size)
        rec["model"] = f"450 W, {round(1000 * rec['length'])} x {round(1000 * rec['width'])} mm"
    rep.missing.append(_("{file}: not with the project and not in the catalogue; a generic 450 W module stands in: "
                         "choose the real one").format(file=name or "?"))
    return f"generic:{rec['model']}" if len(size) == 2 else "generic-450", rec


def _inverter(name: str, base: Path, rep: Report) -> dict | None:
    from ..catalog import panond
    path = find_file(name, base, "inverter")
    if path is not None:
        try:
            rec, _said = panond.inverter(path)
            rep.read.append(_("inverter {name} from {file}").format(name=f"{rec['manufacturer']} {rec['model']}",
                                                                    file=path.name))
            return rec
        except (OSError, ValueError) as error:
            rep.missing.append(_("{file} could not be read: {error}").format(file=path.name, error=error))
    rec = from_catalogue("inverters", name)
    if rec is not None:
        rep.approximated.append(_("inverter {name} from Meridiana's catalogue: {file} was not with the project").format(
            name=f"{rec.get('manufacturer', '')} {rec.get('model', '')}".strip(), file=name))
        return rec
    rep.missing.append(_("{file}: not with the project and not in the catalogue; the inverter is sized by Meridiana")
                       .format(file=name or "?"))
    return None


def _azimuth(az: float, lat: float) -> float:
    """PVsyst's azimuth in Meridiana's (CEI 82-25: from South, + West); the southern hemisphere's scene counts
    from North [to be checked with the trial]."""
    if lat >= 0:
        return az
    return (180.0 - az + 180.0) % 360.0 - 180.0


def _ring(cx: float, cy: float, az: float, length: float, depth: float, margin: float = 0.05) -> list:
    a = math.radians(az)
    f = (-math.sin(a), -math.cos(a))                 # the way the modules face
    r = (math.cos(a), -math.sin(a))                  # along the row
    hl, hd = length / 2 + margin, depth / 2 + margin
    # not rounded: the layout puts the front row on the front edge, which must stay exactly straight
    return [[cx + sr * hl * r[0] + sd * hd * f[0], cy + sr * hl * r[1] + sd * hd * f[1]]
            for sr, sd in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def _field_subfield(sid: str, fl: Field, lat: float, module_id: str) -> model.SubField:
    x, y = (-fl.origin[0], -fl.origin[1]) if lat >= 0 else (fl.origin[0], fl.origin[1])
    az = _azimuth(fl.azimuth, lat)
    if fl.kind == "pvShdArrayTracking":
        # trackers stand in as flat rows along their axis: the rows face sideways, East of the axis
        az = (az - 90.0 + 180.0) % 360.0 - 180.0
    depth = (fl.rows - 1) * fl.pitch + fl.width * math.cos(math.radians(fl.tilt))
    params = {"mounting": "ground", "tilt": fl.tilt, "azimuth": az, "edge": 0.0, "portrait": fl.portrait,
              "stack": max(1, fl.n_height), "gap": fl.gap_x or 0.02, "stack_gap": fl.gap_y or 0.02,
              "pitch_mode": "value", "pitch": fl.pitch if fl.rows > 1 and fl.pitch > 0 else depth + 1.0}
    return model.SubField(id=sid, name=fl.name or sid, ring=_ring(x, y, az, fl.length, depth), building=None,
                          module=module_id, params=params, filled=True)


def _free_subfield(sid: str, name: str, n: int, tilt: float, az: float, rows: int, pitch: float, width: float,
                   rec: dict, at_x: float, module_id: str) -> tuple[model.SubField, float]:
    """A field for n modules where PVsyst had no scene: in one row (PVsyst's unlimited plane casts no
    shade), or in the rows of its sheds."""
    long_side, short_side = float(rec.get("length") or 2.278), float(rec.get("width") or 1.134)
    stack = max(1, round(width / long_side)) if width else 1
    rows = max(1, rows)
    per_row = math.ceil(n / (rows * stack))
    length = per_row * short_side + (per_row - 1) * 0.02
    slant = stack * long_side + (stack - 1) * 0.02
    depth = (rows - 1) * pitch + slant * math.cos(math.radians(tilt)) if rows > 1 and pitch > 0 else \
        slant * math.cos(math.radians(tilt))
    params = {"mounting": "ground", "tilt": tilt, "azimuth": az, "edge": 0.0, "portrait": True, "stack": stack,
              "pitch_mode": "value", "pitch": pitch if rows > 1 and pitch > 0 else depth + 1.0}
    cx = at_x + length / 2
    return (model.SubField(id=sid, name=name, ring=_ring(cx, 0.0, az, length, depth), building=None,
                           module=module_id, params=params, filled=True), length)


def design_of(v: Variant, prj: ProjectFile, base: Path, rep: Report) -> dict:
    """The Meridiana design (model.DESIGN fields, as JSON) of one PVsyst variant."""
    lat = v.site.lat or prj.site.lat
    modules: dict = {}
    by_file: dict = {}

    def module_for(sa: SubArray, scene_name: str = "", size: tuple = ()) -> str:
        key = sa.module_file or scene_name
        if key not in by_file:
            mid, rec = _module(sa.module_file, scene_name, base, rep, size)
            if len(size) == 2 and min(size) > 0.3:
                long_side, short_side = max(size), min(size)
                if abs(float(rec.get("length") or 0) - long_side) > 0.02 or abs(float(rec.get("width") or 0) - short_side) > 0.02:
                    rec["length"], rec["width"] = long_side, short_side
                    rep.approximated.append(_("module sizes from PVsyst's scene: {l} x {w} m").format(
                        l=number(long_side, 3), w=number(short_side, 3)))
            if sa.iam_points and not rec.get("iam_profile"):
                rec["iam_profile"] = {"theta": [p[0] for p in sa.iam_points], "iam": [p[1] for p in sa.iam_points]}
                rep.read.append(_("IAM profile of {n} points ({mode}) from the variant").format(
                    n=len(sa.iam_points), mode=sa.iam_mode))
            modules[mid] = rec
            by_file[key] = mid
        return by_file[key]

    subfields = []
    main = max(v.sub_arrays, key=lambda s: s.modules) if v.sub_arrays else None
    if v.fields:
        for k, fl in enumerate(v.fields, start=1):
            sa = next((s for s in v.sub_arrays if s.orientation == fl.orientation), main)
            mid = module_for(sa, fl.module, fl.module_size) if sa is not None else "generic-450"
            subfields.append(_field_subfield(f"s{k}", fl, lat, mid))
        rep.approximated.append(_("{n} PV fields of the 3D scene placed on the ground at their plan position; Meridiana "
                                  "lays their modules again with PVsyst's tilt, azimuth, rows and tables").format(n=len(v.fields)))
        if "building" in v.system_kind.lower() or any(f.origin[2] > 0.5 for f in v.fields):
            rep.approximated.append(_("the tables stood on a building in PVsyst: draw the building and move the "
                                      "sub-fields onto it"))
    else:
        at = 0.0
        for o in v.orientations:
            arrays = [s for s in v.sub_arrays if s.orientation == o.number] or ([main] if len(v.orientations) == 1 and main else [])
            n = sum(s.modules for s in arrays)
            if not n:
                continue
            mid = module_for(arrays[0])
            sf, length = _free_subfield(f"s{o.number}", o.name or _("Orientation {n}").format(n=o.number), n, o.tilt,
                                        _azimuth(o.azimuth, lat), o.sheds, o.pitch, o.width, modules[mid], at, mid)
            subfields.append(sf)
            at += length + 5.0
        rep.approximated.append(_("no 3D scene in PVsyst: the modules of each orientation stand in one free row, or in "
                                  "the rows of its sheds, on the ground"))
    energy: dict = {}
    if main is not None:
        rec = _inverter(main.inverter_file, base, rep)
        if rec is not None:
            same = [s for s in v.sub_arrays if s.inverter_file == main.inverter_file]
            energy["inverters"] = [{"record": rec, "count": max(1, round(sum(s.n_inverters for s in same))),
                                    "name": ""}]
        if len({s.inverter_file for s in v.sub_arrays}) > 1:
            rep.approximated.append(_("several inverter models: Meridiana keeps the one of the largest sub-array"))
        inputs = next((i for i in v.inverters if sum(i) > 0), None)
        if inputs and rec is not None:
            # PVsyst's strings are counts, not modules: laid on the modules by Meridiana's proposal with those counts,
            # written down as the designer's at the first layout (format 14: "auto" only for this)
            energy["strings"] = {"n_series": main.n_series, "per_mppt": inputs, "auto": True}
            rep.read.append(_("{n} modules in series, strings on the inputs {per}").format(
                n=main.n_series, per=" + ".join(str(x) for x in inputs)))
        losses = {"soiling": round(v.soiling, 3), "quality": main.quality, "lid": main.lid,
                  "mismatch": round(main.mismatch + main.string_mismatch, 3), "dc_wiring": main.dc_wiring}
        if prj.albedo:
            albedo = sum(prj.albedo) / len(prj.albedo)
            losses["albedo"] = round(albedo, 3)
            if max(prj.albedo) - min(prj.albedo) > 1e-3:
                rep.approximated.append(_("monthly albedo from {lo} to {hi}: their mean {mean} used").format(
                    lo=number(min(prj.albedo)), hi=number(max(prj.albedo)), mean=number(albedo)))
        if "hay" in (v.transposition or prj.transposition).lower():
            losses["transposition"] = "haydavies"
        if main.iam_mode == "Default" and main.iam_b0:
            losses["iam_b0"] = main.iam_b0
        if v.unavailability_days:
            losses["unavailability"] = round(100.0 * v.unavailability_days / 365.0, 3)
            rep.approximated.append(_("unavailability: {d} days a year as {p}% of the energy (PVsyst draws random "
                                      "periods, its loss comes out a little lower)").format(
                d=number(v.unavailability_days, 1), p=number(losses["unavailability"], 2)))
        energy["losses"] = losses
        if main.absent:
            rep.approximated.append(_("{keys} not in the variant, taken as 0: PVsyst does not write a value equal to its "
                                      "default (to be confirmed with PVsyst itself)").format(keys=", ".join(main.absent)))
        rep.read.append(_("losses: soiling {s}%, quality {q}%, LID {l}%, mismatch {m}%, DC wiring {w}% at STC").format(
            s=number(losses["soiling"], 1), q=number(losses["quality"], 2), l=number(losses["lid"], 1),
            m=number(losses["mismatch"], 2), w=number(losses["dc_wiring"], 2)))
    if v.uc is not None:
        case = THERMAL[min(THERMAL, key=lambda u: abs(u - v.uc))]
        energy["thermal"] = {sf.id: case for sf in subfields}
        if abs(v.uc - min(THERMAL, key=lambda u: abs(u - v.uc))) > 0.5 or v.uv:
            rep.approximated.append(_("thermal Uc {uc}, Uv {uv}: Meridiana's nearest case, Uc {near}").format(
                uc=number(v.uc, 1), uv=number(v.uv, 1), near=number(min(THERMAL, key=lambda u: abs(u - v.uc)), 0)))
    if prj.design_t_min is not None:
        energy["t_min"] = prj.design_t_min
    if v.results:
        energy["pvsyst_results"] = {"file": v.path.name, "version": v.version, "monthly": v.results}
        if "E_Grid" in v.results:
            rep.read.append(_("PVsyst's results kept for the comparison: {e} MWh a year to the grid").format(
                e=number(sum(v.results["E_Grid"]) / 1000.0, 1)))
    economics: dict = {}
    if v.grid_limit_kw:
        economics["export_limit_kw"] = v.grid_limit_kw
        rep.read.append(_("export limit {kw} kW").format(kw=number(v.grid_limit_kw, 0)))
    for kind in {o.kind for o in v.orientations if o.kind.startswith("Track")}:
        rep.not_imported.append(_("trackers ({kind}): Meridiana does not compute them yet; fixed rows stand in").format(kind=kind))
    if v.bifacial:
        rep.not_imported.append(_("the bifacial gain"))
    if any(s.optimizer for s in v.sub_arrays):
        rep.not_imported.append(_("optimizers ({name})").format(name=next(s.optimizer for s in v.sub_arrays if s.optimizer)))
    if v.scene_others:
        rep.not_imported.append(_("{n} objects of the 3D scene (buildings, trees, obstacles): to draw again in "
                                  "Meridiana").format(n=len(v.scene_others)))
    for what in v.not_understood:
        rep.not_imported.append({"storage": _("the storage"), "economics": _("the economics")}.get(what, what))
    # what this variant lost or approximated stays with it: the checks list it until the designer acts
    energy["pvsyst_import"] = {"file": v.path.name, "approximated": list(dict.fromkeys(rep.approximated)),
                               "not_imported": list(dict.fromkeys(rep.not_imported)),
                               "missing": list(dict.fromkeys(rep.missing))}
    return {"subfields": [asdict(s) for s in subfields], "modules": modules or
            {k: dict(m) for k, m in model.GENERIC_MODULES.items()}, "energy": energy, "economics": economics}


def to_project(prj: ProjectFile, variants: list[Variant]) -> tuple[model.Project, Report]:
    """A new Meridiana project with one variant for each PVsyst variant given, in their order."""
    rep = Report()
    site = prj.site if prj.site.lat or prj.site.lon else (variants[0].site if variants else prj.site)
    p = model.Project(name=prj.name or prj.path.stem)
    p.site = model.Site(lat=site.lat, lon=site.lon, address=", ".join(x for x in (site.name, site.country) if x))
    rep.read.append(_("site {name}: {lat}, {lon}, {alt} m").format(name=p.site.address or "?", lat=number(site.lat, 4),
                                                               lon=number(site.lon, 4), alt=number(site.altitude, 0)))
    if prj.met_file:
        rep.approximated.append(_("weather: PVGIS's typical year of the site, not PVsyst's {file} (its monthly values "
                                  "stay with the results for the comparison)").format(file=prj.met_file))
    base = prj.path.parent
    for k, v in enumerate(variants):
        sub = Report()
        design = design_of(v, prj, base, sub)
        title = v.comment or v.path.suffix
        for name, items in (("read", sub.read), ("approximated", sub.approximated),
                            ("not_imported", sub.not_imported), ("missing", sub.missing)):
            getattr(rep, name).extend(f"{title}: {x}" for x in dict.fromkeys(items))
        if k == 0:
            p.variants = [{"id": "v1", "name": title, "note": _("from PVsyst {file}").format(file=v.path.name)}]
            p.variant = "v1"
        else:
            vid = p.add_variant(title)
            p.current_variant()["note"] = _("from PVsyst {file}").format(file=v.path.name)
            p.variant = vid
        p.set_design(design)
    if len(variants) > 1:
        p.switch_variant("v1")
    return p, rep
