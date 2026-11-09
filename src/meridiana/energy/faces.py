"""Strings over more than one roof face (R433, Daniel on 05/11/2026): «il programma è in grado di capirlo e farla
continuare in un'altra falda? [...] nello stesso edificio lo faccia, al di fuori sia scelta del progettista».

His choice of the same day:
- a string stays on its own face first;
- in the same building, **with optimizers** that keep every module at its maximum power point (SolarEdge, Huawei,
  Sungrow, Tigo TS4-A-O), the proposal lets it go on over another face only when needed, said by a warning;
- **without optimizers** only by the designer's choice (drawn by hand, or `energy["strings"]["across_faces"]` asked
  for the proposal), with the estimate of what the different exposures cost;
- between different buildings only by hand.

The face of a module is its sub-field's (building, pitch); on the ground, its sub-field. The exposure is the module's
plane (tilt, azimuth) at the layout's precision.

The estimate [I: a first order model, the year's energy itself is the electrical network's, cell by cell]: hour by
hour each module's effective irradiance on its plane (the typical year's when it is computed, else a clear sky of the
site); a string without optimizers carries one current: the inverter's MPPT takes the best of the levels of its
modules, those below that level are bypassed and give nothing (bypass diodes at module level), those above give only
at that level; a module on an optimizer gives its own. The loss is what that leaves of the sum of the modules' own.
The kWh are that share of the year's DC energy of the string's modules (only once the year is computed).

No Qt here."""

from __future__ import annotations

import functools
from dataclasses import dataclass, field

import numpy as np

from ..i18n import _, number

KEY = "string_faces"            # the check of a string over more than one face or exposure


@dataclass(frozen=True)
class Face:
    """A roof face: its building ("" on the ground), its pitch (-1 for a ground sub-field: the sub-field itself is
    the face), the words that name it."""
    building: str
    pitch: int
    name: str
    place: str = ""                 # the sub-field, for a ground face


def faces_of(project) -> dict:
    """sub-field id -> its Face."""
    buildings = {b.id: b for b in project.buildings}
    out = {}
    for sf in project.subfields:
        b = buildings.get(sf.building) if sf.building else None
        if b is None:
            out[sf.id] = Face("", -1, sf.name, sf.id)
        else:
            index = b.pitch_index(sf.pitch)
            index = index if index is not None else 0          # as Project.surface_of finds the pitch
            out[sf.id] = Face(b.id, index, _("{building}, pitch {n}").format(building=b.name, n=index + 1))
    return out


def same_face(a: Face, b: Face) -> bool:
    return (a.building, a.pitch, a.place) == (b.building, b.pitch, b.place)


def orientation_of(tilt: float, azimuth: float) -> tuple:
    """As plant._orientation: the plane at the layout's 0.1 degree."""
    tilt = round(float(tilt), 1)
    return tilt, round((float(azimuth) + 180.0) % 360.0 - 180.0, 1) if tilt else 0.0


@functools.lru_cache(maxsize=64)
def clear_sky(lat: float, lon: float, tilt: float, azimuth: float) -> np.ndarray:
    """W/m2 on a plane (CEI 82-25 azimuth) hour by hour over a year of clear sky at the site: Haurwitz's global, Erbs's
    split, the isotropic sky (pvlib). Only for the estimate before the year is computed."""
    import pandas as pd
    import pvlib
    times = pd.date_range("2025-01-01 00:30", periods=8760, freq="h", tz="UTC")
    sp = pvlib.solarposition.get_solarposition(times, lat, lon)
    ghi = pvlib.clearsky.haurwitz(sp.apparent_zenith)["ghi"]
    split = pvlib.irradiance.erbs(ghi, sp.zenith, times)
    poa = pvlib.irradiance.get_total_irradiance(tilt, (180.0 + azimuth) % 360.0, sp.apparent_zenith, sp.azimuth,
                                                split["dni"], ghi, split["dhi"])
    return np.nan_to_num(np.asarray(poa["poa_global"], dtype=float))


def year_of(sim) -> dict | None:
    """What the estimate takes from a computed year (simulate.Simulation): each plane's effective irradiance hour by
    hour, and each array's DC energy for one module. None without a year."""
    parts = getattr(sim, "parts", None) if sim is not None else None
    per = getattr(parts, "per_array", None)
    if not per:
        return None
    planes, kwh = {}, {}
    for ap in per:
        a = ap.a
        planes.setdefault(orientation_of(a.tilt, a.azimuth), np.asarray(ap.g_eff, dtype=float))
    for a in getattr(sim, "arrays", []) or []:
        n = a.get("connected_modules") or a.get("modules") or 0
        if n:
            kwh[str(a["key"]).split(".")[0], orientation_of(a["tilt"], a["azimuth"])] = float(a["dc_kwh"]) / n
    return {"planes": planes, "kwh": kwh}


def exposure_loss(levels: list) -> float:
    """The share of the modules' own energy a string loses for its exposures: `levels` are (hourly W/m2, modules,
    optimized) for each plane of the string, optimized when those modules sit on optimizers that keep them at their
    maximum power point. 0 when every module is on an optimizer or the string has one plane."""
    if not levels:
        return 0.0
    own = sum(n * g for g, n, _o in levels)
    total = float(np.sum(own))
    if total <= 0:
        return 0.0
    plain = [(g, n) for g, n, o in levels if not o and n]
    given = sum((n * g for g, n, o in levels if o), np.zeros_like(levels[0][0]))
    if plain:
        best = np.zeros_like(levels[0][0])
        for g, _n in plain:
            carried = sum((m * (h >= g - 1e-9) for h, m in plain), np.zeros_like(g))
            best = np.maximum(best, g * carried)
        given = given + best
    return max(0.0, 1.0 - float(np.sum(given)) / total)


@dataclass
class Crossing:
    """A string over more than one face or exposure: which, how many of its modules sit on optimizers, the estimate."""
    index: int
    label: str
    faces: list
    buildings: int
    exposures: list                 # [((tilt, azimuth), modules)]
    modules: int
    optimized: int
    loss: float = 0.0               # share of the string's energy
    kwh: float | None = None
    basis: str = ""
    by_hand: bool = True
    texts: list = field(default_factory=list)


def _planes(project, exposures, year):
    out = {}
    for o in exposures:
        g = (year or {}).get("planes", {}).get(o) if year else None
        if g is None:
            g = clear_sky(round(project.site.lat, 3), round(project.site.lon, 3), o[0], o[1])
        out[o] = g
    return out


def crossing(project, index: int, label: str, refs: list, orientations: dict, face_of: dict, optimized,
             year: dict | None = None, by_hand: bool = True) -> Crossing | None:
    """The crossing of one string, None when it stays on one face and one exposure. `refs` its modules as (sub-field,
    key, centre); `orientations` (sub-field, key) -> plane; `optimized(sfid, key)` whether a module is on an optimizer
    that keeps it at its maximum power point."""
    faces, exposures, opt = [], {}, {}
    for sf, key, _c in refs:
        f = face_of.get(sf)
        if f is not None and not any(same_face(f, g) for g in faces):
            faces.append(f)
        o = orientations.get((sf, key))
        if o is None:
            continue
        exposures[o] = exposures.get(o, 0) + 1
        if optimized(sf, key):
            opt[o] = opt.get(o, 0) + 1
    if len(faces) < 2 and len(exposures) < 2:
        return None
    out = Crossing(index, label, faces, len({f.building or f.place for f in faces}), sorted(exposures.items()),
                   len(refs), sum(opt.values()), by_hand=by_hand)
    if len(exposures) > 1:
        planes = _planes(project, exposures, year)
        levels = []
        for o, n in exposures.items():
            k = opt.get(o, 0)
            if k:
                levels.append((planes[o], k, True))
            if n - k:
                levels.append((planes[o], n - k, False))
        out.loss = exposure_loss(levels)
        if year and year.get("kwh"):
            per = year["kwh"]
            base = sum(per.get((sf, orientations.get((sf, key))), 0.0) for sf, key, _c in refs)
            out.kwh = out.loss * base if base > 0 else None
        out.basis = (_("on the typical year computed") if year and year.get("planes") else
                     _("on a year of clear sky at the site, the production not computed yet"))
    return out


def detail(c: Crossing) -> str:
    """The words of the check: where it runs, what the exposures cost, what Daniel's rule says of it."""
    where = ", ".join(f.name for f in c.faces)
    planes = "; ".join(_("{n} modules at {tilt}° facing {az}°").format(n=n, tilt=number(o[0], 0), az=number(o[1], 0))
                       for o, n in c.exposures)
    parts = [_("it runs over {where}").format(where=where) if len(c.faces) > 1 else _("one face, more exposures"),
             planes]
    if len(c.exposures) > 1:
        loss = _("estimated loss for the different exposures {pct} %").format(pct=number(100 * c.loss, 1))
        if c.kwh is not None:
            loss += _(", {kwh} kWh a year").format(kwh=number(c.kwh, 0))
        parts.append(f"{loss}, {c.basis}")
    if c.optimized and c.optimized == c.modules:
        parts.append(_("every module on an optimizer at its maximum power point: the string holds"))
    elif c.optimized:
        parts.append(_("{k} of its {n} modules on optimizers; the others carry the string's one current").format(
            k=c.optimized, n=c.modules))
    else:
        parts.append(_("without optimizers the string's current is held by its least lit module"))
    if c.buildings > 1:
        parts.append(_("between two buildings: only by the designer's choice, check the cables' route"))
    return "; ".join(parts)


def level(c: Crossing) -> str:
    """A warning for a string over two faces (Daniel's rule: allowed, never silent) or one that loses for its exposures;
    an information for one face with more exposures and every module on an optimizer (the makers allow it: Tigo's
    orientations article, point 3; Huawei FR 15/07/2026 p. 10), which loses nothing."""
    return "warn" if len(c.faces) > 1 or c.loss > 1e-4 else "info"

