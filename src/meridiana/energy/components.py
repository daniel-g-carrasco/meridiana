"""The PV module and the inverter as the energy model sees them, from a datasheet (the catalogue, a .PAN or
.OND file, the designer's typing) or, for a first look, from typical values that are said to be such.

The module's power is computed with a one-diode model, whose parameters come, in this order, from:
1. the module's PVsyst file (.PAN): PVsyst's own one-diode model (Mermoud and Lejeune 2010; pvlib's
   calcparams_pvsyst), with its shunt resistance growing at low light (RShunt, Rp_0, Rp_Exp), its series
   resistance and its diode factor (RSerie, Gamma, muGamma); the light and saturation currents follow from
   Isc and Voc;
2. the CEC list (NREL SAM): De Soto's five parameters fitted by SAM (pvlib's calcparams_desoto);
3. the datasheet alone: PVsyst's model form fitted to the STC point, with the shunt resistance set so that
   the relative efficiency at 200 W/m² is the datasheet's (IEC 61853-1) or, when the datasheet gives none,
   a conventional value said to be such (LOW_LIGHT_DEFAULT). A fit to the STC point alone leaves the
   behaviour at low light an artefact of the fit (study 18, B-calcoli section 6.1).
When no fit reproduces the datasheet the power is taken proportional to the irradiance, and the pedigree
says so. The effect of temperature is taken from the datasheet's coefficient of the maximum power (gamma,
measured to IEC 61215), not from the model, whose temperature behaviour follows the band gap and can differ
from the measured one by a few hundredths of %/K: the designer trusts the datasheet, and so does the
calculation.
"""

from __future__ import annotations

import functools
import math
from dataclasses import dataclass, field

import numpy as np

from ..i18n import _
from .dependencies import load_pvlib
from .pedigree import Source

# typical values of an n-type TOPCon module of 108 half cells, 450 W, for a project with no module chosen yet
TYPICAL_450 = {"pmax": 450.0, "vmp": 33.6, "imp": 13.40, "voc": 40.1, "isc": 14.10, "gamma_pmax": -0.30,
               "beta_voc": -0.25, "alpha_isc": 0.046, "cells": 108, "technology": "n-type TOPCon"}
# the relative efficiency at 200 W/m² and 25 °C (IEC 61853-1) taken when the datasheet gives none: the
# middle of the 96-99 % that recent crystalline modules measure (study 18, B-calcoli section 6.1); a
# conventional value, said to be such in the pedigree
LOW_LIGHT_DEFAULT = 97.5
# PVsyst's default for the shunt resistance at zero irradiance when the file does not give it: 4 x RShunt
PVSYST_RSH0_FACTOR = 4.0
PVSYST_RSH_EXP = 5.5
VTH_25 = 0.025693                  # kT/q at 25 °C, V


@dataclass
class ModuleSpec:
    manufacturer: str
    model: str
    pmax: float                 # W at STC
    vmp: float
    imp: float
    voc: float
    isc: float
    gamma_pmax: float           # %/K, negative
    beta_voc: float             # %/K, negative
    alpha_isc: float            # %/K, positive
    cells: int                  # as the datasheet counts them (half cells counted one by one)
    length: float               # m
    width: float                # m
    technology: str = ""
    bifaciality: float = 0.0    # 0 for a mono-facial module
    first_year_loss: float | None = None     # %, the datasheet's first-year degradation (LID included)
    yearly_loss: float | None = None         # %/year after the first
    source: Source = field(default_factory=lambda: Source("default", _("typical values")))
    series_cells: int = 0       # cells in series when the source gives them (the CEC list does)
    max_system_voltage: float | None = None  # V, IEC 61730 class of the module
    max_series_fuse: float | None = None     # A, I_MOD_MAX_OCPR of CEI 64-8/7 (712.3.22)
    sdm_given: dict | None = None            # single-diode parameters fitted by the source (CEC: by SAM)
    diodes: int | None = None                # bypass diodes, when the source says (a PVsyst file does)
    twin: bool | None = None                 # half cells in two halves, when the source says
    iam_profile: dict | None = None          # {"theta", "iam"}: the module's own IAM (a PVsyst file's)
    pvsyst_given: dict | None = None         # the one-diode parameters of the module's PVsyst file
    low_light_200: float | None = None       # %, relative efficiency at 200 W/m² and 25 °C (IEC 61853-1)
    _sdm: dict | None = field(default=None, repr=False, compare=False)

    @property
    def area(self) -> float:
        return self.length * self.width

    @property
    def efficiency(self) -> float:
        return self.pmax / (self.area * 1000.0) if self.area > 0 else float("nan")

    @property
    def cells_in_series(self) -> int:
        """Datasheets count the pieces of cell: halves (108, 144), quarters (192, 216, cut 4 times), whole
        cells (60, 72). A crystalline cell gives 0.68-0.75 V at open circuit, so the count of cells in series
        is the division of the printed count (by 1, 2, 3 or 4) that brings the Voc per cell nearest 0.71 V
        (tried on 21/10/2026 with Jinko's 192, 216 and 264 quarter-cut modules: 48, 54 and 66).

        The count the source gives (the CEC list, a PVsyst file) is trusted only when it agrees with the Voc
        (0.55-0.90 V a cell): the CEC list has 24 for the Jinko JKM540M-72HL4-TV (Voc 49.49 V: 2.06 V a cell)
        and 22 for the Risen RSM132-8-660BMDG, the cells of one sub-string, not those in series; then the Voc
        decides among the divisions of the printed count and the multiples of the given one (72 and 66; study
        18, B-pvsyst section 6.7)."""
        if self.voc <= 0:
            return self.series_cells or max(1, self.cells)
        if self.series_cells > 0 and 0.55 <= self.voc / self.series_cells <= 0.90:
            return self.series_cells
        options = [self.cells // k for k in (1, 2, 3, 4) if self.cells > 0 and self.cells % k == 0]
        options += [self.series_cells * k for k in (2, 3, 4, 6) if self.series_cells > 0]
        options += [self.series_cells // k for k in (2, 3, 4, 6) if self.series_cells > 0 and self.series_cells % k == 0]
        options = [n for n in options if 0.55 <= self.voc / n <= 0.90]
        if not options:
            return max(1, round(self.voc / 0.71))
        return min(options, key=lambda n: abs(self.voc / n - 0.71))

    def sdm(self) -> dict:
        """The parameters of the one-diode model, found once: "form" is "pvsyst" (PVsyst's model, from the
        module's PVsyst file or fitted to the datasheet) or "desoto" (the CEC list's), "origin" is "pan",
        "cec" or "fit"; {"linear": True} when no fit reproduces the datasheet (then the power is taken
        proportional to the irradiance, and the pedigree says so)."""
        if self._sdm is None:
            self._sdm = _pan_sdm(self) or _given_sdm(self) or _fit_sdm(self)
        return self._sdm

    def diode_params(self, irradiance, temp_cell=25.0) -> tuple:
        """(I_L, I_0, R_s, R_sh, nNsVth) of the one-diode model at the irradiance and cell temperature given,
        by the model's own form; the single-diode equation then is pvlib.pvsystem.singlediode's."""
        load_pvlib()
        from pvlib.pvsystem import calcparams_desoto, calcparams_pvsyst
        p = self.sdm()
        if p.get("form") == "pvsyst":
            return calcparams_pvsyst(irradiance, temp_cell, p["alpha_sc"], p["gamma_ref"], p["mu_gamma"],
                                     p["I_L_ref"], p["I_o_ref"], p["R_sh_ref"], p["R_sh_0"], p["R_s"],
                                     p["cells_in_series"], R_sh_exp=p["R_sh_exp"])
        return calcparams_desoto(irradiance, temp_cell, p["alpha_sc"], p["a_ref"], p["I_L_ref"], p["I_o_ref"],
                                 p["R_sh_ref"], p["R_s"])

    def _mpp_at_25(self, irradiance) -> tuple[np.ndarray, np.ndarray]:
        """Power and current at the maximum power point of one module at 25 °C, for the effective irradiance
        given (W/m²)."""
        load_pvlib()
        from pvlib.pvsystem import max_power_point
        g = np.clip(np.asarray(irradiance, dtype=float), 0.0, None)
        p = self.sdm()
        if p.get("linear"):
            return self.pmax * g / 1000.0, self.imp * g / 1000.0
        lit = g > 1.0
        power, current = np.zeros_like(g), np.zeros_like(g)
        if lit.any():
            il, io, rs, rsh, nnsvth = self.diode_params(g[lit], 25.0)
            # chandrupatla brackets the root as brentq does, over the whole array at once: on the 8760 hours of
            # a year 26 ms instead of 1.8 s, the same power within 1e-13 W (tried on 22/10/2026)
            mpp = max_power_point(il, io, rs, rsh, nnsvth, method="chandrupatla")
            power[lit] = np.clip(np.asarray(mpp["p_mp"], dtype=float), 0.0, None)
            current[lit] = np.clip(np.asarray(mpp["i_mp"], dtype=float), 0.0, None)
        return power, current

    def power_at_25(self, irradiance) -> np.ndarray:
        """Maximum power of one module at 25 °C for the effective irradiance given (W/m²)."""
        return self._mpp_at_25(irradiance)[0]

    def current_at_25(self, irradiance) -> np.ndarray:
        """Current at the maximum power point of one module at 25 °C for the effective irradiance given."""
        return self._mpp_at_25(irradiance)[1]

    def low_light_ratio(self, irradiance: float = 200.0) -> float:
        """The relative efficiency at the irradiance given and 25 °C: P(G) / (P(1000) G/1000)."""
        p = self.power_at_25(np.array([irradiance, 1000.0]))
        return float(p[0] / (p[1] * irradiance / 1000.0)) if p[1] > 0 else 1.0

    @classmethod
    def from_record(cls, rec: dict) -> ModuleSpec:
        """A module of the project or of the catalogue. A project's module without electrical data (the
        generic ones) gets the typical values, scaled to its power, and says so."""
        rec = {k: v for k, v in rec.items() if v is not None}
        electrical = all(rec.get(k) for k in ("vmp", "imp", "voc", "isc"))
        length = float(rec.get("length") or (rec.get("length_mm") or 0) / 1000.0 or 2.278)
        width = float(rec.get("width") or (rec.get("width_mm") or 0) / 1000.0 or 1.134)
        pmax = float(rec.get("pmax") or rec.get("pmax_w") or (rec.get("power_kw") or 0.45) * 1000.0)
        if electrical:
            name = f"{rec.get('manufacturer', '')} {rec.get('model', '')}".strip()
            if rec.get("source") == "cec":
                source = Source("data", _("CEC list of {name} (NREL SAM library)").format(name=name),
                                "https://github.com/NREL/SAM/tree/develop/deploy/libraries")
            elif rec.get("source") == "pan":
                source = Source("data", _("PVsyst file {file} of {name}").format(file=rec.get("file", ""), name=name))
            else:
                source = Source("data", _("datasheet of {name}").format(name=name), rec.get("datasheet_url", ""))
            return cls(manufacturer=rec.get("manufacturer", ""), model=rec.get("model", ""), pmax=pmax,
                       vmp=float(rec["vmp"]), imp=float(rec["imp"]), voc=float(rec["voc"]), isc=float(rec["isc"]),
                       gamma_pmax=float(rec.get("gamma_pmax", rec.get("temp_coeff_pmax_pct_c", -0.35)) or -0.35),
                       beta_voc=float(rec.get("beta_voc", rec.get("temp_coeff_voc_pct_c", -0.27)) or -0.27),
                       alpha_isc=float(rec.get("alpha_isc", rec.get("temp_coeff_isc_pct_c", 0.05)) or 0.05),
                       cells=int(rec.get("cells") or 0), length=length, width=width,
                       technology=rec.get("technology", ""), bifaciality=float(rec.get("bifaciality") or 0.0),
                       first_year_loss=rec.get("first_year_loss", rec.get("degradation_first_year_pct")),
                       yearly_loss=rec.get("yearly_loss", rec.get("degradation_annual_pct")), source=source,
                       series_cells=int(rec.get("cells_in_series") or 0), sdm_given=rec.get("sdm"),
                       max_system_voltage=rec.get("max_system_voltage_v"),
                       max_series_fuse=rec.get("max_series_fuse_a"), diodes=rec.get("bypass_diodes"),
                       twin=rec.get("twin_half_cells"), iam_profile=rec.get("iam_profile"),
                       pvsyst_given=rec.get("pvsyst_sdm"), low_light_200=rec.get("low_light_200"))
        k = pmax / TYPICAL_450["pmax"]
        t = TYPICAL_450
        return cls(manufacturer=rec.get("manufacturer", _("Generic")), model=rec.get("model", ""), pmax=pmax,
                   vmp=t["vmp"], imp=t["imp"] * k, voc=t["voc"], isc=t["isc"] * k, gamma_pmax=t["gamma_pmax"],
                   beta_voc=t["beta_voc"], alpha_isc=t["alpha_isc"], cells=t["cells"], length=length, width=width,
                   technology=t["technology"],
                   source=Source("default", _("typical values of an n-type TOPCon module, scaled to {w} W: choose "
                                              "the real module for the final design").format(w=round(pmax))))


def _per_input(rec: dict, key: str, single: str | None) -> list | None:
    v = rec.get(key)
    if isinstance(v, list) and v and all(isinstance(x, (int, float)) for x in v):
        return [float(x) for x in v]
    if isinstance(v, (int, float)):
        trackers = rec.get("mppt_count")
        return [float(v)] * (trackers if type(trackers) is int and trackers > 0 else 1)
    if single and rec.get("mppt_count") == 1 and isinstance(rec.get(single), (int, float)):
        return [float(rec[single])]
    return None


def _given_sdm(m: ModuleSpec) -> dict | None:
    """The source's own single-diode parameters (the CEC list's, fitted by SAM), kept if they give the
    datasheet's maximum power at STC within 2%."""
    g = m.sdm_given
    if not g:
        return None
    load_pvlib()
    from pvlib.pvsystem import calcparams_desoto, max_power_point
    try:
        p = {k: float(g[k]) for k in ("I_L_ref", "I_o_ref", "R_s", "R_sh_ref", "a_ref")}
    except (KeyError, TypeError, ValueError):
        return None
    alpha_sc = m.alpha_isc / 100.0 * m.isc
    il, io, rs, rsh, nnsvth = calcparams_desoto(1000.0, 25.0, alpha_sc, p["a_ref"], p["I_L_ref"], p["I_o_ref"],
                                               p["R_sh_ref"], p["R_s"])
    pmp = float(max_power_point(il, io, rs, rsh, nnsvth)["p_mp"])
    if abs(pmp - m.vmp * m.imp) > 0.02 * m.vmp * m.imp:
        return None
    p["alpha_sc"] = alpha_sc
    p["form"], p["origin"] = "desoto", "cec"
    return p


def _light_and_saturation(isc: float, voc: float, rs: float, rsh: float, a: float) -> tuple[float, float]:
    """I_L and I_0 of the one-diode model from the short-circuit and open-circuit points at STC, the
    series and shunt resistances and the diode voltage a = gamma N_s V_t given (two equations, two unknowns:
    the way PVsyst derives them from a .PAN)."""
    e_oc, e_sc = math.exp(min(voc / a, 700.0)), math.exp(min(isc * rs / a, 700.0))
    if e_oc <= e_sc:
        return -1.0, -1.0                   # no such curve: the caller rejects negative currents
    io = (isc * (1.0 + rs / rsh) - voc / rsh) / (e_oc - e_sc)
    il = io * (e_oc - 1.0) + voc / rsh
    return il, io


def _pvsyst_pmp(p: dict, irradiance: float = 1000.0) -> float:
    load_pvlib()
    from pvlib.pvsystem import calcparams_pvsyst, max_power_point
    il, io, rs, rsh, nnsvth = calcparams_pvsyst(irradiance, 25.0, p["alpha_sc"], p["gamma_ref"], p["mu_gamma"],
                                                p["I_L_ref"], p["I_o_ref"], p["R_sh_ref"], p["R_sh_0"], p["R_s"],
                                                p["cells_in_series"], R_sh_exp=p["R_sh_exp"])
    return float(max_power_point(il, io, rs, rsh, nnsvth)["p_mp"])


def _pan_sdm(m: ModuleSpec) -> dict | None:
    """PVsyst's one-diode model from the module's PVsyst file: the resistances and the diode factor as the
    file gives them (RShunt, Rp_0, Rp_Exp, RSerie, Gamma, muGamma), the light and saturation currents from
    Isc and Voc. Kept if it gives the datasheet's maximum power at STC within 2%, as PVsyst's own
    "Pmpp model" is allowed to differ from PNom."""
    g = m.pvsyst_given
    if not g:
        return None
    try:
        rsh, rs, gamma = float(g["R_sh_ref"]), float(g["R_s"]), float(g["gamma_ref"])
        rsh0 = float(g["R_sh_0"]) if g.get("R_sh_0") is not None else PVSYST_RSH0_FACTOR * rsh
        exp = float(g["R_sh_exp"]) if g.get("R_sh_exp") is not None else PVSYST_RSH_EXP
        mu_gamma = float(g.get("mu_gamma") or 0.0)
    except (KeyError, TypeError, ValueError):
        return None
    if not (rsh > 0 and rsh0 > 0 and rs >= 0 and gamma > 0 and exp >= 0):
        return None
    ns = m.cells_in_series
    rsh_stc = rsh + (rsh0 - rsh) * math.exp(-exp)
    il, io = _light_and_saturation(m.isc, m.voc, rs, rsh_stc, gamma * ns * VTH_25)
    if not (il > 0 and io > 0):
        return None
    p = {"form": "pvsyst", "origin": "pan", "I_L_ref": il, "I_o_ref": io, "R_s": rs, "R_sh_ref": rsh, "R_sh_0": rsh0,
         "R_sh_exp": exp, "gamma_ref": gamma, "mu_gamma": mu_gamma, "cells_in_series": ns,
         "alpha_sc": m.alpha_isc / 100.0 * m.isc}
    if abs(_pvsyst_pmp(p) - m.vmp * m.imp) > 0.02 * m.vmp * m.imp:
        return None
    return p


def _fit_sdm(m: ModuleSpec) -> dict:
    """PVsyst's model form fitted to the datasheet: at STC the short-circuit, open-circuit and maximum
    power points; the shunt resistance set so that the relative efficiency at 200 W/m² is the datasheet's
    or, failing that, the conventional LOW_LIGHT_DEFAULT (the pedigree says which). {"linear": True} when
    no fit reproduces the datasheet."""
    target = float(m.low_light_200) if m.low_light_200 else LOW_LIGHT_DEFAULT
    fitted = _fit_pvsyst(m.vmp, m.imp, m.voc, m.isc, m.alpha_isc / 100.0 * m.isc, m.cells_in_series, target)
    if fitted is None:
        return {"linear": True, "origin": "fit"}
    p = dict(fitted)
    p["low_light_from"] = "datasheet" if m.low_light_200 else "default"
    return p


@functools.lru_cache(maxsize=256)
def _fit_pvsyst(vmp: float, imp: float, voc: float, isc: float, alpha_sc: float, ns: int, target: float) -> dict | None:
    """The fit itself, kept by its datasheet values: the same module comes back at every simulation.

    As PVsyst does, the model is made to give Isc, Voc and the maximum power at STC (not Vmp and Imp one by
    one: the model's own Vmp may differ a little from the datasheet's), and the low-light target sets the
    rest. The shunt resistance is conventional, 1% of the current through it at the maximum power point
    (the median of the CEC list's 16 886 fits, read on 23/10/2026); the light and saturation currents follow
    from Isc and Voc; the series resistance and the diode factor are the two unknowns, with two conditions:
    the maximum power at STC and the relative efficiency at 200 W/m². They are found on a grid of (R_s,
    gamma) evaluated at once (pvlib's vectorised maximum power point), refined three times, which is robust
    where a root finder stalls. When the target lies outside what the model can give the nearest value is
    taken and the pedigree prints the value reached. A fit is kept only if it gives the maximum power at STC
    within 1%."""
    load_pvlib()
    from pvlib.pvsystem import calcparams_pvsyst, max_power_point
    rsh = 100.0 * vmp / imp
    rsh0 = PVSYST_RSH0_FACTOR * rsh
    rsh_stc = rsh + (rsh0 - rsh) * math.exp(-PVSYST_RSH_EXP)
    p_goal = vmp * imp
    goal = target / 100.0

    def evaluate(rs: np.ndarray, gamma: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """P(1000) and P(200) at 25 °C for each (R_s, gamma); nan where no curve passes through Isc and Voc."""
        rs, gamma = np.asarray(rs, dtype=float).ravel(), np.asarray(gamma, dtype=float).ravel()
        a = gamma * ns * VTH_25
        with np.errstate(all="ignore"):
            e_oc, e_sc = np.exp(np.minimum(voc / a, 700.0)), np.exp(np.minimum(isc * rs / a, 700.0))
            io = (isc * (1.0 + rs / rsh_stc) - voc / rsh_stc) / (e_oc - e_sc)
            il = io * (e_oc - 1.0) + voc / rsh_stc
        ok = np.isfinite(io) & np.isfinite(il) & (e_oc > e_sc) & (io > 0) & (il > 0)
        il, io = np.where(ok, il, isc), np.where(ok, io, 1e-10)
        n = rs.size
        g = np.concatenate([np.full(n, 1000.0), np.full(n, 200.0)])
        tiled = [np.tile(x, 2) for x in (gamma, il, io, rs)]
        params = calcparams_pvsyst(g, 25.0, alpha_sc, tiled[0], 0.0, tiled[1], tiled[2], rsh, rsh0, tiled[3], ns,
                                   R_sh_exp=PVSYST_RSH_EXP)
        pmp = np.asarray(max_power_point(*params, method="chandrupatla")["p_mp"], dtype=float)
        p1000, p200 = pmp[:n], pmp[n:]
        return np.where(ok, p1000, np.nan), np.where(ok, p200, np.nan)

    def on_curve(rs_axis: np.ndarray, g_lo: float, g_hi: float, m: int = 31):
        """For each R_s of the axis, the gamma in [g_lo, g_hi] giving the maximum power at STC (P falls as
        gamma grows), and the relative efficiency at 200 W/m² there; nan where there is none."""
        g_axis = np.linspace(g_lo, g_hi, m)
        rs_grid, g_grid = np.meshgrid(rs_axis, g_axis, indexing="ij")
        p1000, _p200 = evaluate(rs_grid, g_grid)
        p1000 = p1000.reshape(rs_grid.shape)
        gamma_star = np.full(rs_axis.size, np.nan)
        for i in range(rs_axis.size):
            col = p1000[i]
            good = np.isfinite(col)
            if good.sum() < 2:
                continue
            y, x = col[good], g_axis[good]
            if not (y.min() <= p_goal <= y.max()):
                continue
            order = np.argsort(y)                   # P falls with gamma: interpolate on P rising
            gamma_star[i] = float(np.interp(p_goal, y[order], x[order]))
        has = np.isfinite(gamma_star)
        rel = np.full(rs_axis.size, np.nan)
        if has.any():
            p1, p2 = evaluate(rs_axis[has], gamma_star[has])
            rel[has] = p2 / (0.2 * p1)
        return gamma_star, rel

    rs_lo, rs_hi = 0.0, max((voc - vmp) / imp, 1e-3)
    g_lo, g_hi = 0.4, 2.5
    rs_star = gamma_star = None
    for _round in range(3):
        rs_axis = np.linspace(rs_lo, rs_hi, 31)
        gammas, rel = on_curve(rs_axis, g_lo, g_hi)
        has = np.isfinite(rel)
        if has.sum() < 2:
            return None
        r_axis, g_axis, rel = rs_axis[has], gammas[has], rel[has]
        # the relative efficiency at low light grows with R_s along the curve: the first crossing of the goal
        crossing = np.flatnonzero(np.diff(np.sign(rel - goal)) != 0)
        if crossing.size:
            k = int(crossing[0])
            t = (goal - rel[k]) / (rel[k + 1] - rel[k]) if rel[k + 1] != rel[k] else 0.0
            rs_star = float(r_axis[k] + t * (r_axis[k + 1] - r_axis[k]))
            gamma_star = float(g_axis[k] + t * (g_axis[k + 1] - g_axis[k]))
        else:
            k = int(np.argmin(np.abs(rel - goal)))   # out of reach: the nearest end of the curve
            rs_star, gamma_star = float(r_axis[k]), float(g_axis[k])
            if _round > 0:
                break
        step_rs, step_g = (rs_hi - rs_lo) / 30.0, (g_hi - g_lo) / 30.0
        rs_lo, rs_hi = max(0.0, rs_star - step_rs), rs_star + step_rs
        g_lo, g_hi = max(0.2, gamma_star - 2 * step_g), gamma_star + 2 * step_g
    if rs_star is None or gamma_star is None:
        return None
    a = gamma_star * ns * VTH_25
    il, io = _light_and_saturation(isc, voc, rs_star, rsh_stc, a)
    if not (il > 0 and io > 0):
        return None
    p = {"form": "pvsyst", "origin": "fit", "I_L_ref": il, "I_o_ref": io, "R_s": rs_star, "R_sh_ref": rsh,
         "R_sh_0": rsh0, "R_sh_exp": PVSYST_RSH_EXP, "gamma_ref": gamma_star, "mu_gamma": 0.0,
         "cells_in_series": ns, "alpha_sc": alpha_sc}
    p1000 = _pvsyst_pmp(p)
    if abs(p1000 - p_goal) > 0.01 * p_goal:
        return None
    p["low_light_200"] = target
    p["low_light_got"] = 100.0 * _pvsyst_pmp(p, 200.0) / (0.2 * p1000)
    return p


@dataclass
class InverterSpec:
    manufacturer: str
    model: str
    pac: float                  # W, nominal AC power of one inverter
    eta: float                  # weighted efficiency (European or CEC), 0-1
    count: int = 1
    vdc_max: float | None = None
    vmppt_min: float | None = None
    vmppt_max: float | None = None
    mppt_count: int | None = None
    phases: int | None = None
    imax_per_mppt: list | None = None          # A, the maximum operating current of each input
    iscmax_per_mppt: list | None = None        # A, the maximum short-circuit current of each input
    source: Source = field(default_factory=lambda: Source("default", _("typical values")))
    imax_total: float | None = None            # shared DC operating-current limit of the whole inverter
    inputs_per_mppt: list | None = None        # physical connector pairs, not independent trackers
    imax_by_strings: list | None = None        # per tracker: {number of occupied inputs: operating current}
    imax_per_input: list | None = None          # rating of each physical input on each tracker, when documented
    iscmax_per_input: list | None = None

    @staticmethod
    def _limit(values, mppt: int) -> float | None:
        if values and 0 <= mppt < len(values):
            value = values[mppt]
            if type(value) in (int, float) and math.isfinite(value) and value > 0:
                return float(value)
        return None

    def current_limit(self, mppt: int, strings: int = 1) -> float | None:
        """Operating limit for the actual number of strings on this zero-based tracker."""
        base = self._limit(self.imax_per_mppt, mppt)
        if isinstance(self.imax_by_strings, list) and 0 <= mppt < len(self.imax_by_strings):
            rule = self.imax_by_strings[mppt]
            value = rule.get(str(strings)) if isinstance(rule, dict) else None
            if type(value) in (int, float) and math.isfinite(value) and value > 0:
                return min(base, float(value)) if base is not None else float(value)
            if isinstance(rule, dict) and rule and strings > 0:
                # A table without this operating configuration is not permission to use its largest value.
                return None
        return base

    def connector_current_limit(self, mppt: int) -> float | None:
        return self._limit(self.imax_per_input, mppt)

    def connector_isc_limit(self, mppt: int) -> float | None:
        return self._limit(self.iscmax_per_input, mppt)

    @property
    def pac_total(self) -> float:
        return self.pac * self.count

    @classmethod
    def sized_for(cls, dc_stc_w: float, ratio: float = 1.1) -> InverterSpec:
        """No inverter chosen yet: one sized at the DC/AC ratio given, with a typical efficiency."""
        pac = math.ceil(dc_stc_w / ratio / 100.0) * 100.0
        return cls(_("Not chosen"), _("sized at DC/AC {r}").format(r=ratio), pac=pac, eta=0.97,
                   source=Source("default", _("inverter not chosen: AC power from a DC/AC ratio of {r}, weighted "
                                              "efficiency 97%").format(r=ratio)))

    @classmethod
    def from_record(cls, rec: dict, count: int = 1) -> InverterSpec:
        eta = rec.get("efficiency_euro_pct") or rec.get("efficiency_cec_pct") or rec.get("efficiency_max_pct") or 97.0
        return cls(manufacturer=rec.get("manufacturer", ""), model=rec.get("model", ""),
                   pac=float(rec.get("ac_power_nominal_w") or rec.get("pac") or 0.0), eta=float(eta) / 100.0,
                   count=count, vdc_max=rec.get("dc_voltage_max_v"), vmppt_min=rec.get("mppt_voltage_min_v"),
                   vmppt_max=rec.get("mppt_voltage_max_v"), mppt_count=rec.get("mppt_count"),
                   phases=rec.get("phases"),
                   imax_per_mppt=_per_input(rec, "dc_current_max_per_mppt_a", "dc_current_max_a"),
                   iscmax_per_mppt=_per_input(rec, "dc_isc_max_per_mppt_a", None),
                   imax_total=float(rec["dc_current_max_a"]) if isinstance(rec.get("dc_current_max_a"), (int, float)) else None,
                   inputs_per_mppt=_per_input(rec, "strings_per_mppt", None),
                   imax_by_strings=(rec.get("dc_current_max_per_mppt_by_strings_a")
                                    if isinstance(rec.get("dc_current_max_per_mppt_by_strings_a"), list) else None),
                   imax_per_input=_per_input(rec, "dc_current_max_per_input_a", None),
                   iscmax_per_input=_per_input(rec, "dc_isc_max_per_input_a", None),
                   source=Source("data", (_("PVsyst file {file} of {name}") if rec.get("source") == "ond" else
                                          _("datasheet of {name}")).format(
                       file=rec.get("file", ""), name=f"{rec.get('manufacturer', '')} {rec.get('model', '')}".strip()),
                       rec.get("datasheet_url", "")))
