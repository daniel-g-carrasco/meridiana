"""PVsyst's component files: a module (.PAN) or an inverter (.OND) read into a record of the catalogue.

The format is PVsyst's own, "intended for internal use only" and not documented (PVsyst help, "Format of
PVsyst files"; pvlib.iotools.read_panond says the same): text, UTF-8 since PVsyst 6.80, nested objects
("PVObject_=pvModule" ... "End of PVObject pvModule"), one "key=value" a line. The keys read here are the
ones PVsyst writes for the datasheet values; the units are PVsyst's (muISC in mA/K, muVocSpec in mV/K,
powers of an inverter in kW). A file without the essential values is refused and the missing ones named:
a wrong reading must not become a module that looks right. What was read, and how, comes back with the
record so that the designer sees it before using it."""

from __future__ import annotations

import re
from pathlib import Path

from ..i18n import _

NUMBER = re.compile(r"^[-+]?\d+(\.\d*)?([eE][-+]?\d+)?$")
MODULE_NEEDS = ("PNom", "Voc", "Isc", "Vmp", "Imp")
INVERTER_NEEDS = ("PNomConv", "VMppMin")


def read(path: Path) -> dict:
    """Every "key=value" of the file, whatever object it is in; the first one wins (the commercial data come
    first). Numbers are numbers, the rest text."""
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    out: dict = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, _sep, value = line.strip().partition("=")
        key, value = key.strip(), value.strip()
        if not key or key.startswith("PVObject") or key in out:
            continue
        out[key] = float(value) if NUMBER.match(value) else value
    return out


def iam_profile(path: Path) -> dict | None:
    """The module's own incidence angle modifier, when its file has one (IAMMode=UserProfile): the points
    "angle,IAM" of the PVObject_IAM block, in order. None otherwise, or when the points do not make a
    profile (angles from 0 rising, values between 0 and 1)."""
    lines = Path(path).read_bytes().decode("utf-8-sig", errors="replace").splitlines()
    inside, mode, points = False, "", []
    for line in lines:
        t = line.strip()
        if t.startswith("PVObject_IAM"):
            inside = True
        elif inside and t.startswith("End of PVObject pvIAM"):
            break
        elif inside and t.startswith("IAMMode="):
            mode = t.partition("=")[2].strip()
        elif inside and t.startswith("Point_"):
            a, _sep, b = t.partition("=")[2].partition(",")
            try:
                points.append((float(a), float(b)))
            except ValueError:
                return None
    if mode != "UserProfile" or len(points) < 3:
        return None
    theta = [a for a, _b in points]
    iam = [b for _a, b in points]
    if theta[0] != 0.0 or any(y <= x for x, y in zip(theta, theta[1:], strict=False)) or not all(0 <= v <= 1.0001 for v in iam):
        return None
    return {"theta": theta, "iam": iam}


def _num(d: dict, *keys):
    for k in keys:
        v = d.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def one_diode(d: dict) -> dict | None:
    """The parameters of PVsyst's one-diode model in the file, with pvlib's names (calcparams_pvsyst): None
    when the file lacks the shunt resistance, the series resistance or the diode factor. Rp_0 and Rp_Exp
    are left out when absent, and components.py takes PVsyst's defaults (4 x RShunt, 5.5)."""
    rsh, rs, gamma = _num(d, "RShunt"), _num(d, "RSerie"), _num(d, "Gamma")
    if rsh is None or rs is None or gamma is None:
        return None
    out = {"R_sh_ref": rsh, "R_s": rs, "gamma_ref": gamma, "R_sh_0": _num(d, "Rp_0"), "R_sh_exp": _num(d, "Rp_Exp"),
           "mu_gamma": _num(d, "muGamma")}
    return {k: v for k, v in out.items() if v is not None}


def module(path: Path) -> tuple[dict, list[str]]:
    """A .PAN file as a module record, and what was read (in words). ValueError when it is not a module or
    an essential value is missing."""
    d = read(path)
    missing = [k for k in MODULE_NEEDS if _num(d, k) is None]
    if missing:
        raise ValueError(_("{file} is not a module PVsyst wrote, or lacks {keys}").format(
            file=Path(path).name, keys=", ".join(missing)))
    isc, voc = _num(d, "Isc"), _num(d, "Voc")
    mu_isc, mu_voc = _num(d, "muISC"), _num(d, "muVocSpec")
    ns, npar = _num(d, "NCelS"), _num(d, "NCelP")
    rec = {
        "source": "pan", "file": Path(path).name,
        "manufacturer": str(d.get("Manufacturer", "")), "model": str(d.get("Model", Path(path).stem)),
        "technology": str(d.get("Technol", "")),
        "pmax": _num(d, "PNom"), "vmp": _num(d, "Vmp"), "imp": _num(d, "Imp"), "voc": voc, "isc": isc,
        # PVsyst gives the coefficients in mA/K and mV/K; the catalogue in %/K
        "alpha_isc": mu_isc / isc / 10.0 if mu_isc is not None else None,
        "beta_voc": mu_voc / voc / 10.0 if mu_voc is not None else None,
        "gamma_pmax": _num(d, "muPmpReq"),
        "cells": int(ns * (npar or 1)) if ns else 0, "cells_in_series": int(ns) if ns else 0,
        "length": _num(d, "Height"), "width": _num(d, "Width"),
        "thickness_mm": 1000.0 * _num(d, "Depth") if _num(d, "Depth") else None, "weight_kg": _num(d, "Weight"),
        "max_system_voltage_v": _num(d, "VMaxIEC", "VMaxUL"),
        "bifaciality": 100.0 * _num(d, "BifacialityFactor") if _num(d, "BifacialityFactor") else None,
        "first_year_loss": _num(d, "LIDLoss"),
        # how the cells stand behind the bypass diodes, for the electrical effect of the shade
        "bypass_diodes": int(_num(d, "NDiode")) if _num(d, "NDiode") else None,
        "twin_half_cells": (str(d["SubModuleLayout"]) == "slTwinHalfCells") if "SubModuleLayout" in d else None,
        "iam_profile": iam_profile(path),
        # PVsyst's one-diode model: the shunt resistance at STC and at zero light with its exponent, the
        # series resistance, the diode factor and its temperature coefficient (components.py uses them)
        "pvsyst_sdm": one_diode(d),
    }
    rec = {k: v for k, v in rec.items() if v not in (None, "")}
    said = [_("power {w} W, Voc {voc} V, Isc {isc} A, Vmp {vmp} V, Imp {imp} A").format(
        w=f"{rec['pmax']:g}", voc=f"{voc:g}", isc=f"{isc:g}", vmp=f"{rec['vmp']:g}", imp=f"{rec['imp']:g}")]
    if mu_isc is not None or mu_voc is not None:
        said.append(_("coefficients from mA/K and mV/K: Isc {a} %/K, Voc {b} %/K").format(
            a=f"{rec.get('alpha_isc', 0):.4f}", b=f"{rec.get('beta_voc', 0):.4f}"))
    if "gamma_pmax" in rec:
        said.append(_("Pmax {g} %/K").format(g=f"{rec['gamma_pmax']:g}"))
    if ns:
        said.append(_("{n} cells in series").format(n=int(ns)))
    if rec.get("iam_profile"):
        said.append(_("its own IAM profile, {n} points").format(n=len(rec["iam_profile"]["theta"])))
    if rec.get("pvsyst_sdm"):
        s = rec["pvsyst_sdm"]
        said.append(_("one-diode model: Rsh {rsh} Ω, Rsh(0) {rsh0} Ω, Rs {rs} Ω, gamma {g}").format(
            rsh=f"{s['R_sh_ref']:g}", rsh0=f"{s['R_sh_0']:g}" if s.get("R_sh_0") is not None else _("not given"),
            rs=f"{s['R_s']:g}", g=f"{s['gamma_ref']:g}"))
    if rec.get("bypass_diodes"):
        said.append((_("{n} bypass diodes, half cells in two halves") if rec.get("twin_half_cells") else
                     _("{n} bypass diodes")).format(n=rec["bypass_diodes"]))
    if "length" in rec and "width" in rec:
        said.append(_("{l} x {w} m").format(l=f"{rec['length']:g}", w=f"{rec['width']:g}"))
    absent = [k for k in ("muISC", "muVocSpec", "muPmpReq", "NCelS", "Height", "Width", "VMaxIEC") if k not in d]
    if absent:
        said.append(_("not in the file, the defaults instead: {keys}").format(keys=", ".join(absent)))
    return rec, said


def inverter(path: Path) -> tuple[dict, list[str]]:
    """A .OND file as an inverter record, and what was read. ValueError when it is not an inverter or an
    essential value is missing."""
    d = read(path)
    missing = [k for k in INVERTER_NEEDS if _num(d, k) is None]
    if missing:
        raise ValueError(_("{file} is not an inverter PVsyst wrote, or lacks {keys}").format(
            file=Path(path).name, keys=", ".join(missing)))
    pnom = _num(d, "PNomConv")
    mppts = _num(d, "NbMPPT")
    connectors = _num(d, "NbInputs")
    imax = _num(d, "IMaxDC")
    phases = {"mono": 1, "tri": 3}.get(str(d.get("MonoTri", "")).lower())
    rec = {
        "source": "ond", "file": Path(path).name, "type": "string",
        "manufacturer": str(d.get("Manufacturer", "")), "model": str(d.get("Model", Path(path).stem)),
        "ac_power_nominal_w": 1000.0 * pnom,
        "ac_power_max_va": 1000.0 * _num(d, "PMaxOUT") if _num(d, "PMaxOUT") else None,
        "mppt_voltage_min_v": _num(d, "VMppMin"), "mppt_voltage_max_v": _num(d, "VMPPMax", "VMppMax"),
        "dc_voltage_max_v": _num(d, "VAbsMax"), "efficiency_euro_pct": _num(d, "EfficEuro"),
        "efficiency_max_pct": _num(d, "EfficMax"), "mppt_count": int(mppts) if mppts else None, "phases": phases,
        # A common limit does not establish any individual tracker's limit or connector mapping.
        "dc_current_max_a": imax,
        "dc_input_pairs": int(connectors) if connectors else None,
    }
    rec = {k: v for k, v in rec.items() if v not in (None, "")}
    said = [_("{kw} kW AC, MPPT window {lo}-{hi} V").format(kw=f"{pnom:g}", lo=f"{rec['mppt_voltage_min_v']:g}",
                                                            hi=f"{rec.get('mppt_voltage_max_v', 0):g}")]
    if "efficiency_euro_pct" in rec:
        said.append(_("European efficiency {e}%").format(e=f"{rec['efficiency_euro_pct']:g}"))
    if mppts:
        said.append(_("{n} independent MPPTs").format(n=int(mppts)))
    if connectors:
        said.append(_("{n} physical DC input pairs; their MPPT mapping is not given.").format(n=int(connectors)))
    if imax:
        said.append(_("{a} A total DC current; the per-MPPT limits are not given.").format(a=f"{imax:g}"))
    absent = [k for k in ("VMPPMax", "VAbsMax", "EfficEuro", "NbMPPT", "IMaxDC", "MonoTri")
              if k not in d and not (k == "VMPPMax" and "VMppMax" in d)]
    if absent:
        said.append(_("not in the file: {keys}").format(keys=", ".join(absent)))
    return rec, said
