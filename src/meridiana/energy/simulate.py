"""The hourly production of the system over a typical year, with every loss on the way, as PVsyst lays
it out: from the sun on the horizontal plane to the energy delivered at the meter.

The chain, hour by hour, for each array (a sub-field: one orientation, one module, one mounting):
1. the sun's position at the representative instant of the weather data (NREL SPA);
2. the irradiance on the plane of the modules (transposition, Perez 1990 by default);
3. the far shading of the horizon on the direct and circumsolar parts; then, for tilted rows, the shade of
   each row on the next (pvlib.shading.shaded_fraction1d, Anderson and Jensen 2024) and the sky the row in
   front hides (Passias and Källbäck 1984), the first row excepted; then the shadows of the obstacles of
   the scene, cast on the planes of the modules (nearshade.py);
4. the reflection on the module's glass (incidence angle modifier, ASHRAE, b0 = 0.05);
5. the soiling;
6. the cell temperature (the PVsyst thermal model, Uc and Uv by mounting, with the module's efficiency at
   its working point: two passes with the module's power, as PVsyst iterates);
7. the module's power: one-diode model at 25 °C for the irradiance, the datasheet's gamma for the
   temperature (components.py);
8. the losses of the array: module quality, light-induced degradation, mismatch, the electrical effect of
   the shade on the strings (switched and scaled as PVsyst's "fraction for electrical effect"), with power
   optimizers (task 22) their conversion and the power a string of them carries, DC wiring (ohmic: given at STC
   and scaled with the square of the array's current);
then, for all the arrays together, the inverter (PVWatts efficiency curve, Dobos 2014) and its clipping
at the nominal AC power, the AC wiring (ohmic too, scaled with the square of the AC power) and the
unavailability.

The typical year is placed on a real calendar (REFERENCE_YEAR) in Italian local time, so that the
production meets the consumption hour by hour, bands F1/F2/F3 and daylight saving time included.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from ..i18n import _, number

if TYPE_CHECKING:
    import pandas as pd             # imported where it is used: 0,4 s at the window's start otherwise (task 18c)
from . import nearshade
from .components import InverterSpec, ModuleSpec
from .meteo import Horizon, Meteo
from .pedigree import Quantity, Record, Source, Step, computed

REFERENCE_YEAR = 2026
TIMEZONE = "Europe/Rome"

# the PVsyst thermal model, Uc (W/m²K) and Uv (W/m²K per m/s), by how the back of the module is cooled
THERMAL = {"open": (29.0, 0.0), "semi": (20.0, 0.0), "integrated": (15.0, 0.0)}
TYPICAL_EFFICIENCY = 0.20          # for the heat balance of a module whose size is unknown
# from the mounting of a sub-field (layout.MOUNTINGS) to its thermal case
MOUNTING_THERMAL = {"coplanar": "semi", "integrated": "integrated", "tilted_anchored": "open",
                    "tilted_ballasted": "open", "east_west": "open", "ground": "open", "canopy": "open"}


def thermal_names() -> dict:
    return {"open": _("free-standing, air all round (Uc 29)"), "semi": _("parallel to the roof, air duct behind (Uc 20)"),
            "integrated": _("integrated, insulated back (Uc 15)")}


@dataclass
class Losses:
    """The designer's settings of the loss chain; every one has a default that is said to be one."""
    transposition: str = "perez"
    albedo: float = 0.20
    use_horizon: bool = True
    use_near: bool = True           # the shadows of the obstacles of the scene
    iam_b0: float = 0.05
    soiling: float = 2.0            # % of the irradiance
    quality: float = 0.0            # %, negative for a gain
    lid: float | None = None        # %; None: the module's first-year loss, else 1.0
    mismatch: float = 1.0           # %
    dc_wiring: float = 1.5          # % at STC
    ac_wiring: float = 1.0          # % at the nominal AC power
    unavailability: float = 0.0     # %
    # the electrical effect of the shade of the rows and of the obstacles on the strings (PVsyst: "linear
    # shadings" against "according to module strings", with its "fraction for electrical effect"); the
    # defaults are what the chain did before 23/10/2026: the full effect, always
    electrical_shading: bool = True
    electrical_fraction: float = 100.0     # % of the electrical effect applied

    @classmethod
    def from_dict(cls, data: dict | None) -> Losses:
        out = cls()
        for k, v in (data or {}).items():
            if hasattr(out, k):
                setattr(out, k, v)
        return out


def lid_pct(losses: Losses, module=None) -> float:
    """The light-induced degradation the chain applies, in %: the designer's figure, else the module's
    first-year loss from its datasheet, else 1%. PVGIS's loss figure is built with the same value."""
    if losses.lid is not None:
        return float(losses.lid)
    first = getattr(module, "first_year_loss", None)
    return float(first) if first is not None else 1.0


@dataclass
class ArraySpec:
    key: str
    name: str
    tilt: float                     # degrees
    azimuth: float                  # CEI 82-25/1: from South, + towards West
    modules: int
    module: ModuleSpec
    thermal: str = "open"
    rows: int = 0                   # tilted rows: how many, their pitch and the slant height of a row (m)
    pitch: float = 0.0
    slant: float = 0.0
    upright: bool = True            # modules with their long side up the slope (portrait)
    stack: int = 1                  # modules across a table
    stand_off: float = 0.15         # m, the lowest edge of a row above the roof or the ground
    placed: list = field(default_factory=list, repr=False)       # its layout.PlacedModule, for the shadows
    obstacles: list = field(default_factory=list, repr=False)    # nearshade.Solid that can shade it
    connected: frozenset | None = field(default=None, repr=False)  # placed keys wired to a real input; None: potential

    @property
    def p_stc(self) -> float:
        return self.modules * self.module.pmax

    @property
    def generating_modules(self) -> int:
        return self.modules if self.connected is None else sum(pm.key in self.connected for pm in self.placed)

    @property
    def p_connected(self) -> float:
        return self.generating_modules * self.module.pmax


@dataclass
class ArrayOptimizers:
    """The power optimizers on an array's modules (task 22, energy/optimizers.py): the share of its modules in a
    string of optimizers, the share of them alone on their optimizer (each its own MPPT: no mismatch with the
    others), the optimizers' weighted efficiency, the inverter's fixed string voltage."""
    share: float                    # 0-1 of the array's modules
    single: float                   # 0-1 of the array's modules alone on an optimizer
    eta: float                      # 0-1
    v_string: float                 # V
    name: str                       # the optimizer, "SolarEdge S440"
    source: Source


@dataclass
class Optimizers:
    """The optimizers of the year: by array, and the strings of optimizers with the most power each carries,
    as ({array key: modules of the string in it}, W)."""
    arrays: dict = field(default_factory=dict)
    strings: list = field(default_factory=list)


@dataclass
class ChainStep:
    key: str
    label: str
    kind: str                       # "irradiance" (kWh/m²) or "energy" (kWh)
    value: float
    change: float | None = None     # % against the previous value of the same kind; None for a start


@dataclass
class Simulation:
    hourly: pd.DataFrame            # local time of REFERENCE_YEAR; powers in W, energies in kWh
    monthly: pd.DataFrame
    chain: list[ChainStep]
    record: Record
    arrays: list[dict]
    p_stc_kw: float
    p_ac_kw: float
    energy_kwh: float
    specific_yield: float           # kWh/kWp
    pr: float                       # 0-1
    notes: list[str] = field(default_factory=list)
    # the first pass (steps 1-7 of every array), kept so that the year with the strings (with_strings) applies
    # only the array step and the system's again
    parts: object = field(default=None, repr=False, compare=False)


@dataclass
class _ArrayPass:
    """What steps 1-7 gave for one array: the irradiances along the chain, the shadings, the cell temperature,
    the module's power and current. The array step (8) and the system's are applied on these, once without
    the strings and again with them (with_strings), without the sun, the transposition and the temperature
    computed twice (task 18c, step 3)."""
    a: ArraySpec
    g_inc: np.ndarray
    g_far: np.ndarray
    g_rows: np.ndarray
    g_near: np.ndarray
    g_iam: np.ndarray
    g_eff: np.ndarray
    beam_left: np.ndarray           # the direct part after the shadings, before the glass
    iam_b: np.ndarray
    p_nom: np.ndarray
    p_25: np.ndarray
    p_t: np.ndarray
    t_cell: np.ndarray
    i_ratio: np.ndarray             # the array's current over its STC current, before the losses of the array
    shaded: np.ndarray              # the rows' linear shade
    extra_rows: np.ndarray          # and their electrical effect
    f_obst: np.ndarray              # the obstacles' linear shade
    near: object                    # nearshade.Shading, or None
    layout: tuple
    lid: float
    u_c: float
    u_v: float
    eta_mean: float
    dome: float
    alb: float
    sky_mask: float
    ground_lost: float


@dataclass
class _Pass:
    """The first pass of simulate: the weather, the sun and steps 1-7 of every array."""
    meteo: Meteo
    arrays: list
    inverter: InverterSpec
    losses: Losses
    hor: Horizon | None
    index: object                   # the local calendar of the reference year
    hours: int
    p_stc: float
    weights: np.ndarray
    ghi: np.ndarray
    dhi: np.ndarray
    temp_air: np.ndarray
    sun_az: np.ndarray
    sun_el: np.ndarray
    per_array: list


def _local_index() -> pd.DatetimeIndex:
    import pandas as pd
    utc = pd.date_range(f"{REFERENCE_YEAR}-01-01 00:00", periods=8760, freq="h", tz="UTC")
    return utc.tz_convert(TIMEZONE)


def profile_iam(aoi, theta: list[float], iam: list[float]) -> np.ndarray:
    """A module's own IAM profile between its points, joined as PVsyst joins them (its staff on PVsyst's forum):
    a straight line up to the first point below 1, then a cubic through the four points around the angle.
    Never above 1, and 0 from 90 degrees on."""
    x = np.abs(np.asarray(aoi, dtype=float))
    t, v = np.asarray(theta, dtype=float), np.asarray(iam, dtype=float)
    if t[-1] < 90.0:
        t, v = np.append(t, 90.0), np.append(v, 0.0)
    if v[0] > 0:
        v = v / v[0]
    out = np.interp(x, t, v)
    n, below = len(t), np.flatnonzero(v < 1.0)
    if n >= 4 and below.size:
        k = np.clip(np.searchsorted(t, x, side="right") - 1, 0, n - 2)      # the segment [t_k, t_k+1]
        j = np.clip(k - 1, 0, n - 4)                                         # its four points j .. j+3
        cubic = np.zeros_like(x)
        for i in range(4):
            w = np.ones_like(x)
            for m in range(4):
                if m != i:
                    w = w * (x - t[j + m]) / (t[j + i] - t[j + m])
            cubic = cubic + w * v[j + i]
        out = np.where(k >= below[0], cubic, out)
    return np.where(x >= 90.0, 0.0, np.clip(out, 0.0, 1.0))


def _pvwatts_inverter(pdc: np.ndarray, pac_nom: float, eta_nom: float) -> tuple[np.ndarray, np.ndarray]:
    """AC power before and after clipping. The PVWatts v5 curve (Dobos 2014, as pvlib.inverter.pvwatts):
    eta = eta_nom / 0.9637 (-0.0162 z - 0.0059 / z + 0.9858), z = Pdc / Pdc0, Pdc0 = Pac,nom / eta_nom."""
    pdc0 = pac_nom / eta_nom
    z = np.divide(pdc, pdc0, out=np.zeros_like(pdc), where=pdc > 0)
    curve = -0.0162 * z - np.divide(0.0059, z, out=np.zeros_like(z), where=z > 0) + 0.9858
    eta = np.where(z > 0, eta_nom / 0.9637 * curve, 0.0)
    unclipped = np.clip(eta * pdc, 0.0, None)
    return unclipped, np.minimum(unclipped, pac_nom)


def simulate(meteo: Meteo, arrays: list[ArraySpec], inverter: InverterSpec | None = None,
             losses: Losses | None = None, horizon: Horizon | None = None, strings: dict | None = None,
             optimizers: Optimizers | None = None) -> Simulation:
    """`strings` maps an array's key to its strings (lists of module keys): with them the shade of the
    obstacles also has its electrical effect. `optimizers`: the power optimizers on the modules (task 22)."""
    return _finish(_first_pass(meteo, arrays, inverter, losses, horizon), strings, optimizers)


def with_strings(sim: Simulation, strings: dict | None, optimizers: Optimizers | None = None) -> Simulation:
    """The year of `sim` again with the strings laid on the modules (the electrical effect of the obstacles'
    shade) and the power optimizers on them: the sun, the transposition, the shadings, the temperature and the
    module's power of the first pass are kept, only the array step and the system's are applied again. The same
    numbers as simulate(..., strings=strings, optimizers=optimizers), at a fraction of its time."""
    return _finish(sim.parts, strings, optimizers)


def _first_pass(meteo: Meteo, arrays: list[ArraySpec], inverter: InverterSpec | None, losses: Losses | None,
                horizon: Horizon | None) -> _Pass:
    import pandas as pd
    import pvlib

    losses = losses or Losses()
    arrays = [a for a in arrays if a.modules > 0]
    if not arrays:
        raise ValueError(_("no modules laid: lay the modules of a sub-field first"))
    p_stc = sum(a.p_stc for a in arrays)
    if inverter is None:
        inverter = InverterSpec.sized_for(p_stc)
    d = meteo.data
    index = _local_index()
    hours = len(d)

    # 1. the sun
    t_sun = d.index + pd.Timedelta(hours=meteo.time_offset_h)
    sp = pvlib.solarposition.get_solarposition(t_sun, meteo.latitude, meteo.longitude, altitude=meteo.elevation,
                                               pressure=d.pressure.to_numpy(), temperature=d.temp_air.to_numpy())
    zenith = sp.apparent_zenith.to_numpy()
    sun_az = sp.azimuth.to_numpy()
    sun_el = 90.0 - zenith
    dni_extra = pvlib.irradiance.get_extra_radiation(t_sun).to_numpy()
    airmass = pvlib.atmosphere.get_relative_airmass(zenith)

    ghi, dni, dhi = d.ghi.to_numpy(), d.dni.to_numpy(), d.dhi.to_numpy()
    temp_air, wind = d.temp_air.to_numpy(), d.wind_speed.to_numpy()
    hor = horizon if (horizon is not None and losses.use_horizon) else None
    blocked = (hor.at(sun_az) > sun_el) & (sun_el > 0) if hor is not None else np.zeros(hours, dtype=bool)
    iam_d = pvlib.iam.marion_diffuse("ashrae", np.array([a.tilt for a in arrays]), b=losses.iam_b0)

    needed = None                   # the cells of the shading table the sun's path reads, once for all arrays
    per_array: list[_ArrayPass] = []
    weights = np.array([a.p_stc for a in arrays]) / p_stc
    for i, a in enumerate(arrays):
        surface_az = (180.0 + a.azimuth) % 360.0
        aoi = pvlib.irradiance.aoi(a.tilt, surface_az, zenith, sun_az)
        poa = pvlib.irradiance.get_total_irradiance(a.tilt, surface_az, zenith, sun_az, dni, ghi, dhi,
                                                    dni_extra=dni_extra, airmass=airmass, albedo=losses.albedo,
                                                    model=losses.transposition, diffuse_components=True)

        sky, ground, beam, circum = (np.nan_to_num(np.asarray(poa[name], dtype=float)) if name in poa
                                     else np.zeros(hours)
                                     for name in ("poa_sky_diffuse", "poa_ground_diffuse", "poa_direct",
                                                  "poa_circumsolar"))
        g_inc = beam + sky + ground
        # 3. far shading: the direct part and the circumsolar part come from the sun's direction, the
        # mountains hide part of the rest of the sky, and the ground in front loses its light behind them
        sun_part = beam + circum
        dome = hor.diffuse_factor(a.tilt, surface_az) if hor is not None else 1.0
        alb = _albedo_factor(hor, a.tilt, surface_az) if hor is not None else 1.0
        ground = ground * alb
        sky_left = (sky - circum) * dome
        beam_left = np.where(blocked, 0.0, sun_part)
        g_far = beam_left + sky_left + ground
        # 3b. near shading of tilted rows: every row but the first is shaded by the one in front
        shaded = np.zeros(hours)
        extra_rows = np.zeros(hours)
        sky_mask = 0.0
        ground_lost = 0.0
        layout = nearshade.blocks_of(a.module.cells, a.module.diodes, a.module.twin)
        if a.rows > 1 and a.pitch > 0 and a.slant > 0:
            behind = (a.rows - 1) / a.rows
            sf = pvlib.shading.shaded_fraction1d(zenith, sun_az, (surface_az - 90.0) % 360.0, a.tilt,
                                                 collector_width=a.slant, pitch=a.pitch)
            row_share = np.where(sun_el > 0, np.clip(np.nan_to_num(np.asarray(sf, dtype=float)), 0.0, 1.0), 0.0)
            shaded = row_share * behind
            extra_rows = behind * nearshade.rows_electrical(row_share, a.stack, a.upright, layout)
            gcr = min(0.99, a.slant / a.pitch)
            # the sky the row in front hides: the row's view factor of the sky, integrated over its height,
            # against a free plane's (infinite rows, isotropic sky; Marion et al. 2017)
            free = (1.0 + math.cos(math.radians(a.tilt))) / 2.0
            seen = float(np.atleast_1d(pvlib.bifacial.utils.vf_row_sky_2d_integ(a.tilt, gcr, 0.0, 1.0))[0])
            sky_mask = max(0.0, 1.0 - seen / free) * behind
            # the ground in front of a row: partly hidden by the row in front, partly in the rows' shade and
            # under less sky (Mikofski et al. 2019, pvlib's infinite sheds), against the free plane's
            height = a.stand_off + a.slant / 2.0 * math.sin(math.radians(a.tilt))
            sheds = pvlib.bifacial.infinite_sheds.get_irradiance_poa(
                a.tilt, surface_az, zenith, sun_az, gcr, height, a.pitch, ghi, dhi, dni, losses.albedo)
            between = np.nan_to_num(np.asarray(sheds["poa_ground_diffuse"], dtype=float))
            kept = np.clip(np.divide(between, ground, out=np.ones(hours), where=ground > 1e-6), 0.0, 1.0)
            before = ground.sum()
            ground = ground * ((1.0 - behind) + behind * kept)
            ground_lost = float(1.0 - ground.sum() / before) if before > 0 else 0.0
        beam_left = beam_left * (1.0 - shaded)
        sky_left = sky_left * (1.0 - sky_mask)
        g_rows = beam_left + sky_left + ground
        # 3c. the shadows of the obstacles of the scene, on the planes of the modules
        near = None
        f_obst = np.zeros(hours)
        if losses.use_near and a.obstacles and a.placed:
            if needed is None:
                needed = nearshade.needed_cells(sun_az, sun_el)
            illuminated = [pm for pm in a.placed if pm.key in a.connected] if a.connected else a.placed
            near = nearshade.cached_shading(illuminated, a.obstacles, a.tilt, a.azimuth, needed, layout)
            f_obst = nearshade.at(near.table, sun_az, sun_el)
            beam_left = beam_left * (1.0 - f_obst)
            sky_left = sky_left * near.sky
        g_near = beam_left + sky_left + ground
        # 4. glass reflection
        profile = a.module.iam_profile
        if profile:
            # the module's own profile, read from its PVsyst file, for the beam and integrated for the diffuse
            iam_b = np.nan_to_num(profile_iam(aoi, profile["theta"], profile["iam"]))

            def own(x, p=profile):
                return profile_iam(x, p["theta"], p["iam"])

            iam_sky, iam_ground = (float(np.atleast_1d(pvlib.iam.marion_integrate(own, a.tilt, region))[0])
                                   for region in ("sky", "ground"))
        else:
            iam_b = np.nan_to_num(np.asarray(pvlib.iam.ashrae(aoi, b=losses.iam_b0), dtype=float))
            iam_sky, iam_ground = float(np.atleast_1d(iam_d["sky"])[i]), float(np.atleast_1d(iam_d["ground"])[i])
        g_iam = beam_left * iam_b + sky_left * iam_sky + ground * iam_ground
        # 5. soiling
        g_eff = g_iam * (1.0 - losses.soiling / 100.0)
        # 6. cell temperature, 7. the module: the heat balance needs the module's efficiency at its working
        # point, which needs the cell temperature; two passes, as PVsyst iterates (study 18, B-pvsyst 6.2:
        # with the STC efficiency the temperature step came out 0.16-0.57 points too kind)
        u_c, u_v = THERMAL.get(a.thermal, THERMAL["open"])
        n = a.modules
        eta_stc = a.module.efficiency if math.isfinite(a.module.efficiency) and a.module.efficiency > 0 else TYPICAL_EFFICIENCY
        area = a.module.area if a.module.area > 0 else a.module.pmax / (1000.0 * eta_stc)
        p_nom = a.p_stc * g_eff / 1000.0
        p_25 = n * a.module.power_at_25(g_eff)
        gamma = a.module.gamma_pmax / 100.0
        eta_op = np.full(hours, eta_stc)
        for _pass in range(2):
            t_cell = np.asarray(pvlib.temperature.pvsyst_cell(g_far, temp_air, wind, u_c=u_c, u_v=u_v,
                                                              module_efficiency=eta_op, alpha_absorption=0.9), dtype=float)
            p_t = p_25 * (1.0 + gamma * (t_cell - 25.0))
            lit = g_far > 1.0
            eta_op = np.where(lit, np.clip(np.divide(p_t, n * area * g_far, out=np.zeros(hours), where=lit),
                                           0.0, 1.5 * eta_stc), eta_stc)
        sunny = g_far > 50.0
        eta_mean = float(eta_op[sunny].mean()) if sunny.any() else eta_stc
        # the array's current over its STC current (the module model's current at the maximum power point,
        # with the temperature coefficient of Isc), for the DC wiring of the array step
        i_ratio = np.divide(a.module.current_at_25(g_eff), float(a.module.current_at_25(1000.0)) or 1.0)
        i_ratio = i_ratio * (1.0 + a.module.alpha_isc / 100.0 * (t_cell - 25.0))
        # Installed panels still define the physical rows and their temperature, but only a real electrical
        # connection transfers their power. Apply this before array losses and inverter clipping, never after AC.
        share = a.generating_modules / a.modules
        p_nom, p_25, p_t = p_nom * share, p_25 * share, p_t * share
        per_array.append(_ArrayPass(a, g_inc, g_far, g_rows, g_near, g_iam, g_eff, beam_left, iam_b, p_nom, p_25, p_t,
                                    t_cell, i_ratio, shaded, extra_rows, f_obst, near, layout, lid_pct(losses, a.module),
                                    u_c, u_v, eta_mean, dome, alb, sky_mask, ground_lost))
    return _Pass(meteo, arrays, inverter, losses, hor, index, hours, p_stc, weights, ghi, dhi, temp_air, sun_az, sun_el,
                 per_array)


def _finish(first: _Pass, strings: dict | None, optimizers: Optimizers | None = None) -> Simulation:
    """Step 8 of every array (its losses, the electrical effect of the shade with the `strings` given, the power
    optimizers), then the inverter and the AC side, the chain, the months and the record: the whole year from the
    first pass."""
    import pandas as pd
    meteo, inverter, losses, hor = first.meteo, first.inverter, first.losses, first.hor
    index, hours, p_stc, weights = first.index, first.hours, first.p_stc, first.weights
    ghi, dhi, temp_air, sun_az, sun_el = first.ghi, first.dhi, first.temp_air, first.sun_az, first.sun_el
    src_meteo = meteo.source
    rec = Record(_("Production of the system"))
    notes: list[str] = []
    rec.add(Step("sun", _("Position of the sun"), r"\theta_z,\ \gamma_s = \mathrm{SPA}(t + \Delta t,\ \varphi,\ \lambda,\ h)",
                 _("Every hour of the typical year, at the instant its irradiance represents (the hour plus the offset "
                   "PVGIS declares), with refraction."),
                 [Quantity(r"\varphi", _("latitude"), meteo.latitude, "°", src_meteo, 4),
                  Quantity(r"\lambda", _("longitude"), meteo.longitude, "°", src_meteo, 4),
                  Quantity("h", _("elevation"), meteo.elevation, "m", src_meteo, 0),
                  Quantity(r"\Delta t", _("time offset of the data"), meteo.time_offset_h, "h", src_meteo, 3)],
                 None, _("NREL Solar Position Algorithm, Reda and Andreas 2004 (pvlib.solarposition)")))

    per_array = []
    tot = {k: np.zeros(hours) for k in ("poa", "poa_far", "poa_near", "poa_iam", "poa_eff", "p_nom", "p_25", "p_t",
                                        "p_q", "p_lid", "p_mm", "p_el", "p_opt", "p_cut", "p_dc")}
    any_electrical = False
    opts = optimizers.arrays if optimizers is not None else {}
    stage = []                      # what the first half of step 8 gave each array: for the strings' limit, the rest
    for ap in first.per_array:
        a = ap.a
        opt = opts.get(a.key)
        p_t = ap.p_t
        shaded, extra_rows, f_obst, near = ap.shaded, ap.extra_rows, ap.f_obst, ap.near
        # 8. the array
        p_q = p_t * (1.0 - losses.quality / 100.0)
        p_lid = p_q * (1.0 - ap.lid / 100.0)
        # with an optimizer each, the modules no longer drag one another: no mismatch among them (task 22)
        mismatch = losses.mismatch * (1.0 - (opt.single if opt is not None else 0.0))
        p_mm = p_lid * (1.0 - mismatch / 100.0)
        # the electrical effect of the shade: the direct light the shaded strings lose beyond the linear shade,
        # of the rows on the next and of the obstacles; PVsyst's switch (linear shadings or by strings) and its
        # fraction for the electrical effect
        f_el = losses.electrical_fraction / 100.0 if losses.electrical_shading else 0.0
        beam_part = np.divide(ap.beam_left * ap.iam_b, ap.g_iam, out=np.zeros(hours), where=ap.g_iam > 0)
        cut_rows = f_el * beam_part * np.divide(extra_rows, 1.0 - shaded, out=np.zeros(hours), where=shaded < 0.999)
        extra = None
        cut_obst = np.zeros(hours)
        if f_el > 0 and near is not None and strings and strings.get(a.key):
            extra = nearshade.electrical(near, strings[a.key], sun_az, sun_el)
            cut_obst = f_el * beam_part * np.divide(extra, 1.0 - f_obst, out=np.zeros(hours), where=f_obst < 0.999)
        p_el = p_mm * (1.0 - np.clip(cut_rows + cut_obst, 0.0, 1.0))
        rows_electrical = f_el > 0 and bool(extra_rows.any())
        if rows_electrical or extra is not None:
            any_electrical = True
        # the optimizers convert the share of the modules behind them with their weighted efficiency
        p_opt = p_el * (1.0 - opt.share * (1.0 - opt.eta)) if opt is not None else p_el
        stage.append({"p_q": p_q, "p_lid": p_lid, "p_mm": p_mm, "p_el": p_el, "p_opt": p_opt, "cut_rows": cut_rows,
                      "cut_obst": cut_obst, "extra": extra, "rows_electrical": rows_electrical, "mismatch": mismatch})
    cuts = _string_cuts(first.per_array, stage, optimizers, hours)
    for i, ap in enumerate(first.per_array):
        a = ap.a
        opt = opts.get(a.key)
        st = stage[i]
        g_inc, g_far, g_rows, g_near, g_iam, g_eff = ap.g_inc, ap.g_far, ap.g_rows, ap.g_near, ap.g_iam, ap.g_eff
        p_nom, p_25, p_t, t_cell, near, layout = ap.p_nom, ap.p_25, ap.p_t, ap.t_cell, ap.near, ap.layout
        lid, u_c, u_v, eta_mean, dome, alb = ap.lid, ap.u_c, ap.u_v, ap.eta_mean, ap.dome, ap.alb
        n = a.modules
        p_mm, p_el, p_opt, extra = st["p_mm"], st["p_el"], st["p_opt"], st["extra"]
        p_cut = np.clip(p_opt - cuts.get(a.key, 0.0), 0.0, None)
        # the DC wiring: an ohmic loss, R I², given as a share of the STC power at STC and scaled with the square
        # of the array's current (the module model's current at the maximum power point, with the temperature
        # coefficient of Isc, reduced as the power is by the losses before the wiring), as PVsyst computes it; on
        # a string of optimizers the inverter holds the voltage, so the current goes with the power
        i_ratio = ap.i_ratio * np.divide(p_el, p_t, out=np.ones(hours), where=p_t > 0)
        squares = np.clip(i_ratio, 0.0, None) ** 2
        if opt is not None:
            relative_power = np.divide(p_cut, a.p_connected, out=np.zeros(hours), where=a.p_connected > 0)
            squares = (1.0 - opt.share) * squares + opt.share * np.clip(relative_power, 0.0, None) ** 2
        p_dc = np.clip(p_cut - losses.dc_wiring / 100.0 * a.p_connected * squares, 0.0, None)
        for key, val in (("poa", g_inc), ("poa_far", g_far), ("poa_near", g_near), ("poa_iam", g_iam),
                         ("poa_eff", g_eff)):
            tot[key] += weights[i] * val
        for key, val in (("p_nom", p_nom), ("p_25", p_25), ("p_t", p_t), ("p_q", st["p_q"]), ("p_lid", st["p_lid"]),
                         ("p_mm", p_mm), ("p_el", p_el), ("p_opt", p_opt), ("p_cut", p_cut), ("p_dc", p_dc)):
            tot[key] += val
        per_array.append({"key": a.key, "name": a.name, "tilt": a.tilt, "azimuth": a.azimuth, "modules": n,
                          "connected_modules": a.generating_modules, "connected_p_stc_kw": a.p_connected / 1000.0,
                          "p_stc_kw": a.p_stc / 1000.0, "poa_kwh_m2": float(g_inc.sum() / 1000.0),
                          "dc_kwh": float(p_dc.sum() / 1000.0), "t_cell_max": float(np.nanmax(t_cell)),
                          "lid": float(lid), "thermal": a.thermal, "eta_operating": eta_mean})
        per_array[-1]["sky_seen"] = dome
        far_sum = g_far.sum()
        per_array[-1]["row_shading"] = float((g_far - g_rows).sum() / far_sum) if far_sum > 0 else 0.0
        per_array[-1]["obstacle_shading"] = float((g_rows - g_near).sum() / far_sum) if far_sum > 0 else 0.0
        per_array[-1]["albedo_seen"] = alb
        _array_steps(rec, a, losses, lid, u_c, u_v, src_meteo, hor, dome, alb, eta_mean)
        if a.rows > 1 and a.pitch > 0 and a.slant > 0:
            _rows_step(rec, a, per_array[-1]["row_shading"], ap.sky_mask, ap.ground_lost, losses)
        mm = p_mm.sum()
        if st["rows_electrical"]:
            lost = float((p_mm * np.clip(st["cut_rows"], 0.0, 1.0)).sum() / mm) if mm > 0 else 0.0
            per_array[-1]["rows_electrical"] = lost
            _rows_electrical_step(rec, a, layout, lost, losses)
        if near is not None:
            _obstacles_step(rec, a, near, per_array[-1]["obstacle_shading"])
        if extra is not None:
            per_array[-1]["electrical_shading"] = (float((p_mm * np.clip(st["cut_obst"], 0.0, 1.0)).sum() / mm)
                                                   if mm > 0 else 0.0)
            _electrical_step(rec, a, near, len(strings[a.key]), per_array[-1]["electrical_shading"], losses,
                             opt is not None)
        if opt is not None:
            el = p_el.sum()
            per_array[-1]["optimizers"] = {"share": opt.share, "single": opt.single, "eta": opt.eta,
                                           "mismatch": st["mismatch"], "name": opt.name,
                                           "loss": float(1.0 - p_opt.sum() / el) if el > 0 else 0.0,
                                           "cut": float(1.0 - p_cut.sum() / p_opt.sum()) if p_opt.sum() > 0 else 0.0}
            _optimizers_step(rec, a, opt, losses, per_array[-1]["optimizers"])
    if optimizers is not None and tot["p_opt"].sum() > 0:
        share_cut = 1.0 - tot["p_cut"].sum() / tot["p_opt"].sum()
        if share_cut > 0.005:
            notes.append(_("The strings of optimizers cut {pct} of the energy at the power they carry: more strings, "
                           "shorter, keep it (SolarEdge's single string guidelines).").format(
                pct=f"{number(100 * share_cut, 1)}%"))

    # inverter and AC side
    pac_nom = inverter.pac_total
    ac_unclipped, ac = _pvwatts_inverter(tot["p_dc"], pac_nom, inverter.eta)
    frac_ac = losses.ac_wiring / 100.0 * np.clip(ac / pac_nom, 0.0, None)
    p_ac = ac * (1.0 - frac_ac)
    p_grid = p_ac * (1.0 - losses.unavailability / 100.0)
    if (ac_unclipped - ac).sum() > 0.005 * ac_unclipped.sum():
        notes.append(_("The inverter clips {pct} of the energy: check the DC/AC ratio.").format(
            pct=f"{number(100 * (ac_unclipped - ac).sum() / ac_unclipped.sum(), 1)}%"))   # the decimal comma (24/10/2026)

    hourly = pd.DataFrame({
        "ghi": ghi, "dhi": dhi, "temp_air": temp_air, "poa": tot["poa"], "poa_eff": tot["poa_eff"],
        "p_dc": tot["p_dc"], "p_ac": p_grid, "e_kwh": p_grid / 1000.0}, index=index)
    energy = float(p_grid.sum() / 1000.0)
    h_poa = float(tot["poa"].sum() / 1000.0)
    p0 = p_stc / 1000.0
    pr = energy / (p0 * h_poa) if h_poa > 0 else float("nan")

    def kwh(x):
        return float(np.sum(x) / 1000.0)

    chain = [ChainStep("ghi", _("Global horizontal irradiation"), "irradiance", kwh(ghi))]
    for key, label, val in (("poa", _("Global incident on the plane"), tot["poa"]),
                            ("far", _("Far shading, horizon"), tot["poa_far"]),
                            ("near", _("Near shading: rows and obstacles"), tot["poa_near"]),
                            ("iam", _("Reflection on the glass (IAM)"), tot["poa_iam"]),
                            ("soiling", _("Soiling"), tot["poa_eff"])):
        chain.append(ChainStep(key, label, "irradiance", kwh(val)))
    connection_limited = any(a.generating_modules != a.modules for a in first.arrays)
    chain.append(ChainStep("nominal", (_("Connected modules' nominal energy at STC efficiency") if connection_limited
                                      else _("Array nominal energy at STC efficiency")), "energy", kwh(tot["p_nom"])))
    for key, label, val in (("irradiance_level", _("Loss for the irradiance level"), tot["p_25"]),
                            ("temperature", _("Loss for the temperature"), tot["p_t"]),
                            ("quality", _("Module quality"), tot["p_q"]),
                            ("lid", _("Light-induced degradation (LID)"), tot["p_lid"]),
                            ("mismatch", _("Mismatch"), tot["p_mm"]),
                            *((("electrical", _("Electrical effect of the shading, by string"), tot["p_el"]),)
                              if any_electrical else ()),
                            *((("optimizers", _("Power optimizers"), tot["p_opt"]),) if opts else ()),
                            *((("string_limit", _("Strings of optimizers beyond their continuous power"),
                                tot["p_cut"]),) if opts and (tot["p_opt"] - tot["p_cut"]).sum() > 0 else ()),
                            ("dc_wiring", _("DC wiring"), tot["p_dc"]),
                            ("inverter", _("Inverter efficiency"), ac_unclipped),
                            ("clipping", _("Inverter clipping over its nominal power"), ac),
                            ("ac_wiring", _("AC wiring"), p_ac),
                            ("unavailability", _("Unavailability"), p_grid)):
        chain.append(ChainStep(key, label, "energy", kwh(val)))
    last = {}
    for s in chain:
        prev = last.get(s.kind)
        s.change = None if prev in (None, 0) else 100.0 * (s.value / prev - 1.0)
        if s.key == "nominal":
            s.change = None
        last[s.kind] = s.value

    months = index.month
    monthly = pd.DataFrame({
        "ghi": pd.Series(ghi, index=index).groupby(months).sum() / 1000.0,
        "dhi": pd.Series(dhi, index=index).groupby(months).sum() / 1000.0,
        "temp_air": pd.Series(temp_air, index=index).groupby(months).mean(),
        "poa": pd.Series(tot["poa"], index=index).groupby(months).sum() / 1000.0,
        "poa_eff": pd.Series(tot["poa_eff"], index=index).groupby(months).sum() / 1000.0,
        "e_dc": pd.Series(tot["p_dc"], index=index).groupby(months).sum() / 1000.0,
        "e_ac": pd.Series(p_grid, index=index).groupby(months).sum() / 1000.0})
    monthly["pr"] = monthly.e_ac / (p0 * monthly.poa)

    _system_steps(rec, inverter, losses, p_stc, energy, h_poa, pr)
    return Simulation(hourly=hourly, monthly=monthly, chain=chain, record=rec, arrays=per_array,
                      p_stc_kw=p0, p_ac_kw=pac_nom / 1000.0, energy_kwh=energy, specific_yield=energy / p0,
                      pr=pr, notes=notes, parts=first)


ALBEDO_VANISH_DEG = 20.0           # PVsyst: the far albedo vanishes behind a horizon this high (advanced parameter)


def _albedo_factor(hor: Horizon, tilt: float, surface_azimuth: float) -> float:
    """PVsyst's "albedo factor" of the horizon: the light reflected by the ground in front of the plane is
    reduced linearly with the height of the horizon in that direction and vanishes at ALBEDO_VANISH_DEG
    (PVsyst help, project settings, advanced parameters; study 06, section 3). The reduction is averaged
    over the directions below the horizontal the plane sees, weighted by its view of the ground (cos of the
    angle to the normal times cos of the elevation); a horizontal plane sees no ground and keeps 1."""
    b, g = math.radians(tilt), math.radians(surface_azimuth)
    n = np.array([math.sin(b) * math.sin(g), math.sin(b) * math.cos(g), math.cos(b)])
    az = np.arange(0.5, 360.0, 1.0)
    el = -np.radians(np.arange(0.25, 90.0, 0.5))
    aa, ee = np.meshgrid(np.radians(az), el)
    cos_t = np.cos(ee) * np.sin(aa) * n[0] + np.cos(ee) * np.cos(aa) * n[1] + np.sin(ee) * n[2]
    weight = (np.clip(cos_t, 0.0, None) * np.cos(ee)).sum(axis=0)
    if weight.sum() <= 0:
        return 1.0
    kept = np.clip(1.0 - np.asarray(hor.at(az), dtype=float) / ALBEDO_VANISH_DEG, 0.0, 1.0)
    return float((weight * kept).sum() / weight.sum())


def _estimate_shade() -> str:
    return _("This step is an estimate: Martinez-Moreno's model has no check against PVsyst or measurements here, "
             "and with two modules up a table it is an upper bound of the effect.")


def _array_steps(rec: Record, a: ArraySpec, losses: Losses, lid: float, u_c: float, u_v: float, src_meteo: Source,
                 hor: Horizon | None, dome: float, alb: float, eta_mean: float) -> None:
    designer = Source("input", _("drawn by the designer"))
    default = Source("default", _("Meridiana's default, can be changed in the losses"))
    m = a.module
    head = f"{a.name}: "
    names = {"perez": "Perez 1990", "haydavies": "Hay and Davies 1980", "isotropic": "Liu and Jordan 1963"}
    rec.add(Step(f"{a.key}.poa", head + _("Irradiance on the plane of the modules"),
                 r"G_{inc} = G_{b}\cos\theta + G_{d,cielo}(\beta) + G_{h}\,\rho\,\frac{1-\cos\beta}{2}",
                 _("Direct part on the plane, diffuse sky part by the transposition model, part reflected by the "
                   "ground. Hourly global, direct and diffuse irradiance from the typical year."),
                 [Quantity(r"\beta", _("tilt"), a.tilt, "°", designer, 1),
                  Quantity(r"\alpha", _("azimuth from South, + West (CEI 82-25/1)"), a.azimuth, "°", designer, 1),
                  Quantity(r"\rho", _("ground reflectance (albedo)"), losses.albedo, "", default, 2),
                  Quantity("", _("weather"), src_meteo.label, "", src_meteo)],
                 None, _("Transposition: {model} (pvlib.irradiance). Irradiation terms: CEI 82-25/1:2026, 3.2.1.15-18, "
                         "p. 13-14").format(model=names.get(losses.transposition, losses.transposition))))
    if hor is not None:
        rec.add(Step(f"{a.key}.far", head + _("Far shading of the horizon"),
                     r"G_{b}' = 0\ \mathrm{if}\ \alpha_s < h_{oriz}(\gamma_s),\quad "
                     r"f_{cielo} = 1 - \frac{\int_{\alpha < h_{oriz}} \cos\theta\,d\Omega}{\int_{cielo} \cos\theta\,d\Omega},"
                     r"\quad f_{alb} = \overline{\max\left(0,\ 1 - \frac{h_{oriz}(\gamma)}{20°}\right)}",
                     _("When the sun is below the horizon line in its direction, the direct and circumsolar parts are "
                       "lost. Of the rest of the sky, taken as uniform, the plane loses the part hidden by the horizon. "
                       "The light reflected by the ground in front is reduced as PVsyst reduces it: linearly with the "
                       "height of the horizon in each direction the plane sees the ground, to nothing at 20°."),
                     [Quantity("", _("horizon profile"), hor.source.label, "", hor.source),
                      Quantity(r"f_{cielo}", _("share of the diffuse sky still seen"), 100 * dome, "%", computed(""), 1),
                      Quantity(r"f_{alb}", _("share of the light reflected by the ground kept"), 100 * alb, "%",
                               Source("model", _("PVsyst's albedo factor of the horizon, vanishing at 20°")), 1)],
                     None, hor.source.ref))
    if m.iam_profile:
        prof = m.iam_profile
        points = "; ".join(f"{number(t, 0 if t == int(t) else 1)}°: {number(v, 2 if round(v, 2) == v else 3)}"
                           for t, v in zip(prof["theta"], prof["iam"], strict=True))
        rec.add(Step(f"{a.key}.iam", head + _("Reflection on the glass"),
                     r"IAM(\theta) = \sum_{i=0}^{3} IAM_{j+i} \prod_{m \neq i} "
                     r"\frac{\theta - \theta_{j+m}}{\theta_{j+i} - \theta_{j+m}}",
                     _("Part of the light is reflected by the glass, more at grazing angles, as the module's own profile "
                       "says. Between its points the profile is joined as PVsyst joins it: a straight line up to the "
                       "first point below 1, then a cubic through the four points around the angle (the formula). The "
                       "diffuse parts use the same profile integrated over the sky and the ground (Marion 2017)."),
                     [Quantity("", _("profile of the module"), points, "", m.source)], None,
                     _("PVsyst forum, staff replies in «IAM Profile - only 9 points?» and «IAM change in "
                       "PVsyst versions»; pvlib.iam.marion_integrate")))
    else:
        rec.add(Step(f"{a.key}.iam", head + _("Reflection on the glass"),
                     r"IAM(\theta) = 1 - b_0\left(\frac{1}{\cos\theta} - 1\right)",
                     _("Part of the light is reflected by the glass, more at grazing angles. The diffuse parts use the "
                       "same law integrated over the sky and the ground (Marion 2017)."),
                     [Quantity("b_0", _("ASHRAE coefficient"), losses.iam_b0, "", default, 3)], None,
                     _("ASHRAE incidence angle modifier (pvlib.iam.ashrae, pvlib.iam.marion_diffuse)")))
    rec.add(Step(f"{a.key}.soiling", head + _("Soiling"), r"G_{eff} = G_{IAM}\,(1 - s)",
                 _("Dust, pollen, bird droppings on the glass, as a share of the light."),
                 [Quantity("s", _("soiling loss"), losses.soiling, "%", default, 1)], None, ""))
    rec.add(Step(f"{a.key}.temperature", head + _("Temperature of the cells"),
                 r"T_c = T_a + \frac{\alpha\,G_{inc}\,(1 - \eta(T_c))}{U_c + U_v\,v}",
                 _("The heat balance of the module: what the module absorbs and does not turn into electricity "
                   "warms it; the air carries it away, more where the back is open. The efficiency is the module's "
                   "at its working point of the hour (its power over the incident irradiance), not the STC one: a "
                   "first pass at the STC efficiency, then the balance again with the efficiency the model gives, as "
                   "PVsyst iterates it."),
                 [Quantity(r"U_c", _("constant heat loss factor"), u_c, "W/m²K", Source("model", _("PVsyst thermal "
                                                                                                "model, by mounting"))),
                  Quantity(r"U_v", _("wind heat loss factor"), u_v, "W/m²K·s/m", Source("model", _("PVsyst thermal model"))),
                  Quantity(r"\alpha", _("absorption"), 0.9, "", Source("model", _("PVsyst thermal model"))),
                  Quantity(r"\eta_m", _("module efficiency at STC, first pass"), 100 * m.efficiency, "%", m.source, 2),
                  Quantity(r"\bar{\eta}", _("mean efficiency at the working point, hours above 50 W/m²"), 100 * eta_mean,
                           "%", computed(""), 2)],
                 None, _("PVsyst thermal model (pvlib.temperature.pvsyst_cell); PVsyst help, «Array thermal losses»: "
                         "the efficiency at the operating point")))
    sdm = m.sdm()
    estimate = _("The step «loss for the irradiance level» that follows from this model is an estimate: it rests on "
                 "parameters fitted to a few points of the datasheet, not on measurements at low light.")
    if sdm.get("linear"):
        formula, expl = r"P = P_{STC}\,\frac{G_{eff}}{1000}\,[1 + \gamma\,(T_c - 25)]", _(
            "The one-diode model could not be fitted to this datasheet: the power is taken proportional to the "
            "irradiance (the behaviour at low light is not modelled, the step «loss for the irradiance level» is "
            "zero by construction).")
        params = []
        reference = ""
    elif sdm.get("form") == "pvsyst":
        formula = (r"I = I_L - I_0\left[e^{\frac{V + I R_s}{\gamma_d N_s V_t}} - 1\right] - \frac{V + I R_s}{R_{sh}(G)},"
                   r"\quad R_{sh}(G) = R_{sh} + (R_{sh,0} - R_{sh})\,e^{-5.5\,G/G_{ref}}"
                   r",\quad P = P_{mp,25}(G_{eff})\,[1 + \gamma\,(T_c - 25)]")
        if sdm.get("origin") == "pan":
            src = Source("data", _("one-diode parameters of the module's PVsyst file"), m.source.label)
            expl = _("PVsyst's one-diode model with the parameters of the module's PVsyst file: the shunt resistance "
                     "grows at low light as the file says, which sets the behaviour at low irradiance as PVsyst "
                     "computes it; the light and saturation currents follow from Isc and Voc. It gives the power at "
                     "25 °C for the irradiance of the hour; the temperature acts through the datasheet's coefficient "
                     "of the maximum power.")
            low = []
        else:
            src = Source("computed", _("fitted to the datasheet: Isc, Voc and the maximum power at STC, the relative "
                                       "efficiency at 200 W/m²"))
            expl = _("PVsyst's one-diode model fitted to the datasheet: Isc, Voc and the maximum power at STC, and "
                     "the relative efficiency at 200 W/m², which sets the series resistance and the diode factor "
                     "(the shunt resistance is conventional, 1% of the current at the maximum power point). It gives "
                     "the power at 25 °C for the irradiance of the hour; the temperature acts through the "
                     "datasheet's coefficient of the maximum power.") + " " + estimate
            if sdm.get("low_light_from") == "datasheet":
                low_src = Source("data", _("datasheet, relative efficiency at 200 W/m² (IEC 61853-1)"), m.source.ref)
            else:
                low_src = Source("default", _("conventional value of Meridiana: the datasheet gives no low-light datum "
                                              "(recent crystalline modules measure 96-99% to IEC 61853-1)"))
            low = [Quantity(r"\eta_{200}/\eta_{STC}", _("relative efficiency at 200 W/m², 25 °C"),
                            sdm["low_light_200"], "%", low_src, 1)]
            if abs(sdm.get("low_light_got", sdm["low_light_200"]) - sdm["low_light_200"]) > 0.05:
                low.append(Quantity("", _("relative efficiency at 200 W/m² the model could reach"),
                                    sdm["low_light_got"], "%", computed(""), 1))
        params = low + [Quantity("I_L", _("light current"), sdm["I_L_ref"], "A", src, 3),
                        Quantity("I_0", _("saturation current"), f"{sdm['I_o_ref']:.3e} A", "", src),
                        Quantity("R_s", _("series resistance"), sdm["R_s"], "Ω", src, 3),
                        Quantity("R_{sh}", _("shunt resistance at STC"), sdm["R_sh_ref"], "Ω", src, 1),
                        Quantity("R_{sh,0}", _("shunt resistance at zero irradiance"), sdm["R_sh_0"], "Ω", src, 1),
                        Quantity(r"\gamma_d", _("diode factor"), sdm["gamma_ref"], "", src, 3)]
        reference = _("Mermoud and Lejeune, 25th EU PVSEC (2010), PVsyst's one-diode model "
                      "(pvlib.pvsystem.calcparams_pvsyst)")
    else:
        formula = (r"I = I_L - I_0\left[e^{\frac{V + I R_s}{a}} - 1\right] - \frac{V + I R_s}{R_{sh}}"
                   r",\quad P = P_{mp,25}(G_{eff})\,[1 + \gamma\,(T_c - 25)]")
        expl = _("Single-diode model of De Soto with the five parameters the CEC list gives for this module (fitted by "
                 "NREL's SAM to the datasheet): it gives the power at 25 °C for the irradiance of the hour. The "
                 "temperature acts through the datasheet's coefficient of the maximum power.") + " " + estimate
        fit = Source("data", _("CEC list of the module (NREL SAM library)"), m.source.ref)
        params = [Quantity("I_L", _("light current"), sdm["I_L_ref"], "A", fit, 3),
                  Quantity("I_0", _("saturation current"), f"{sdm['I_o_ref']:.3e} A", "", fit),
                  Quantity("R_s", _("series resistance"), sdm["R_s"], "Ω", fit, 3),
                  Quantity("R_{sh}", _("shunt resistance"), sdm["R_sh_ref"], "Ω", fit, 1),
                  Quantity("a", _("modified ideality factor"), sdm["a_ref"], "V", fit, 3)]
        reference = _("De Soto, Klein, Beckman, Solar Energy 80 (2006) 78-88 (pvlib.pvsystem.calcparams_desoto)")
    rec.add(Step(f"{a.key}.module", head + _("Power of the modules"), formula, expl,
                 [Quantity("N", _("connected modules") if a.connected is not None else _("modules"),
                           a.generating_modules, "", designer, 0),
                  Quantity(r"P_{STC}", _("maximum power at STC"), m.pmax, "W", m.source, 1),
                  Quantity(r"\gamma", _("temperature coefficient of the maximum power"), m.gamma_pmax, "%/K", m.source, 3),
                  Quantity("N_s", _("cells in series"), m.cells_in_series, "", computed(_("from the Voc and the count of "
                                                                                          "the datasheet")), 0),
                  *params], Quantity(r"P_{STC,campo}", _("array power at STC"), a.p_connected / 1000.0, "kWp", computed(""), 2),
                 reference))
    lid_src = (Source("input", _("set by the designer")) if losses.lid is not None else
               (Source("data", _("first-year degradation of the datasheet"), m.source.ref) if m.first_year_loss is not None
                else default))
    rec.add(Step(f"{a.key}.array", head + _("Losses of the array"),
                 r"P_{DC} = P\,(1-q)(1-LID)(1-m) - r\,P_{STC}\left(\frac{I_{mp}}{I_{mp,STC}}\right)^2",
                 _("Module quality, light-induced degradation, mismatch between modules; the DC wiring loss is ohmic, "
                   "R I²: given as a share of the STC power at STC, it is scaled hour by hour with the square of the "
                   "array's current (the current at the maximum power point of the module model, with the temperature "
                   "coefficient of Isc, reduced as the power is by the losses before the wiring), as PVsyst computes "
                   "it; scaled with the power instead, it came out 0.2-0.3 points too small (study 18)."),
                 [Quantity("q", _("module quality"), losses.quality, "%", default, 1),
                  Quantity("LID", _("light-induced degradation"), lid, "%", lid_src, 1),
                  Quantity("m", _("mismatch"), losses.mismatch, "%", default, 1),
                  Quantity("r", _("DC wiring loss at STC"), losses.dc_wiring, "%", default, 1)], None,
                 _("PVsyst help, «Array ohmic wiring loss»: loss fraction at STC, R I² in the simulation")))


def _electrical_quantities(losses: Losses) -> list[Quantity]:
    """The fraction of the electrical effect applied, with its default explained."""
    return [Quantity("f_{el}", _("share of the electrical effect applied"), losses.electrical_fraction, "%",
                     Source("default", _("Meridiana's default: the whole effect of Martinez-Moreno's model, an upper "
                                         "bound (two modules up a table, the strings along the rows); PVsyst's "
                                         "«fraction for electrical effect» is the designer's choice, 100% or less "
                                         "(50% in some public reports)")), 0)]


def _rows_step(rec: Record, a: ArraySpec, loss: float, sky_mask: float, ground_lost: float, losses: Losses) -> None:
    geometry = Source("computed", _("from the layout of the sub-field"))
    tail = (_("This is the linear loss; the electrical effect of the shade comes in the energy part.")
            if losses.electrical_shading else
            _("This is the linear loss, and the only one: the electrical effect of the shade is switched off in the "
              "losses (PVsyst's «linear shadings»)."))
    rec.add(Step(f"{a.key}.rows", a.name + ": " + _("Shading between the rows"),
                 r"f_s = f(\theta_z,\ \gamma_s,\ \beta,\ w,\ p)\cdot\frac{n-1}{n},\quad "
                 r"G_b' = G_b\,(1 - f_s),\quad G_d' = G_d\,(1 - \Delta_d),\quad G_r' = G_r\,(1 - \Delta_r)",
                 _("Each row but the first is shaded by the one in front when the sun is low: the shaded share of the "
                   "row's height, hour by hour, takes the direct light. The row in front also hides part of the sky, "
                   "as the row's view factor of the sky says, and most of the ground, whose light between the rows "
                   "is partly in their shade.") + " " + tail,
                 [Quantity("n", _("rows"), a.rows, "", geometry, 0),
                  Quantity("p", _("row pitch"), a.pitch, "m", geometry, 2),
                  Quantity("w", _("height of a row along its slope"), a.slant, "m", geometry, 2),
                  Quantity(r"GCR", _("ground cover ratio"), a.slant / a.pitch, "", computed(""), 2),
                  Quantity(r"\Delta_d", _("share of the sky hidden by the row in front"), 100 * sky_mask, "%",
                           Source("model", _("view factors of infinite rows, Marion et al. 2017")), 1),
                  Quantity(r"\Delta_r", _("share of the light reflected by the ground lost over the year"),
                           100 * ground_lost, "%", Source("model", "Mikofski et al. 2019"), 1)],
                 Quantity(r"\bar{f_s}", _("irradiance lost to the rows over the year"), 100 * loss, "%", computed(""), 2),
                 _("Anderson and Jensen 2024 (pvlib.shading.shaded_fraction1d); Marion et al. 2017 "
                   "(pvlib.bifacial.utils.vf_row_sky_2d_integ); Mikofski et al. 2019 "
                   "(pvlib.bifacial.infinite_sheds)")))


def _rows_electrical_step(rec: Record, a: ArraySpec, layout: tuple[int, int], loss: float, losses: Losses) -> None:
    geometry = Source("computed", _("from the layout of the sub-field"))
    rec.add(Step(f"{a.key}.rows_electrical", a.name + ": " + _("Electrical effect of the shading between the rows"),
                 r"(1 - F_{ES}) = (1 - f_s)\left(1 - f_{el}\,\frac{N_{SB}}{N_{TB}}\right)",
                 _("The row in front shades the next from below, the lowest module of a table first. With the strings "
                   "along the rows, all the modules of a string are shaded alike: an upright module touched has all "
                   "its strips of cells touched (with half cells, the lower half first), one lying down has its "
                   "strips touched from the lowest. The direct light of the shaded rows is cut again by the share of "
                   "blocks touched, as Martinez-Moreno's model puts it, for the share f_el of the effect chosen in "
                   "the losses.") + " " + _estimate_shade(),
                 [Quantity("", _("modules"), _("upright") if a.upright else _("lying down"), "", geometry),
                  Quantity("", _("modules across a table"), a.stack, "", geometry, 0),
                  Quantity(r"n_b", _("blocks of a module"), layout[0] * layout[1], "", computed(""), 0),
                  *_electrical_quantities(losses)],
                 Quantity(r"\Delta E", _("energy lost to the electrical effect of the rows over the year"), 100 * loss,
                          "%", computed(""), 2),
                 _("Martinez-Moreno, Munoz, Lorenzo, Solar Energy Materials and Solar Cells 94 (2010) 2298-2303, "
                   "eq. 6 (pvlib.shading.direct_martinez)")))


def _obstacles_step(rec: Record, a: ArraySpec, near: nearshade.Shading, loss: float) -> None:
    scene = Source("computed", _("from the scene as drawn: obstacles with their height, modules laid"))
    names = near.obstacles
    shown = ", ".join(names[:8]) + (_(" and {n} more").format(n=len(names) - 8) if len(names) > 8 else "")
    rec.add(Step(f"{a.key}.obstacles", a.name + ": " + _("Shading of the obstacles"),
                 r"f_o(\gamma_s,\ \alpha_s) = \frac{A_{ombra}}{A_{moduli}},\quad G_b' = G_b\,(1 - f_o),\quad "
                 r"G_d' = G_d\,f_{cielo,o}",
                 _("The obstacles of the scene (exclusions with a height, parapets, the other buildings) cast their "
                   "shadows along the sun's rays on the plane of the modules, row by row. The shaded share of the "
                   "modules' area is computed for the sun's positions every 5° of azimuth and 4° of elevation along "
                   "its path, then read hour by hour; the diffuse light loses the share of the sky the obstacles hide, "
                   "weighted as for the horizon (every 10° and 8°). The loss is taken proportional to the shaded "
                   "share: the bypass diodes make the real loss larger when a shadow crosses many cells (the "
                   "electrical effect is not modelled yet)."),
                 [Quantity("", _("obstacles"), shown, "", scene),
                  Quantity(r"f_{cielo,o}", _("share of the diffuse sky still seen"), 100 * near.sky, "%", computed(""), 1)],
                 Quantity(r"\bar{f_o}", _("irradiance lost to the obstacles over the year"), 100 * loss, "%",
                          computed(""), 2),
                 _("Table of shading factors on the sun's positions, as PVsyst's near shadings; geometry: shadows of "
                   "convex solids cast on the plane of the modules (Meridiana, nearshade.py)")))


def _string_cuts(per_array: list, stage: list, optimizers: Optimizers | None, hours: int) -> dict:
    """What each array loses, hour by hour, to the strings of optimizers that would carry more than their continuous
    power (their optimizers' output current at the inverter's fixed voltage, SolarEdge's «potenza troncata»): a
    string's power is its modules' share of each array's power after the optimizers, the cut shared back in
    proportion. The module-by-module shade is not followed here: each module is its array's mean."""
    out: dict = {}
    if optimizers is None or not optimizers.strings:
        return out
    each = {ap.a.key: st["p_opt"] / max(1, ap.a.generating_modules) for ap, st in zip(per_array, stage, strict=True)}
    for counts, p_max in optimizers.strings:
        parts = {k: n * each[k] for k, n in counts.items() if k in each and n > 0}
        if not parts or not p_max:
            continue
        total = sum(parts.values())
        over = np.clip(total - float(p_max), 0.0, None)
        if not over.any():
            continue
        for k, part in parts.items():
            out[k] = out.get(k, np.zeros(hours)) + over * np.divide(part, total, out=np.zeros(hours), where=total > 0)
    return out


def _optimizers_step(rec: Record, a: ArraySpec, opt: ArrayOptimizers, losses: Losses, got: dict) -> None:
    rec.add(Step(f"{a.key}.optimizers", a.name + ": " + _("Power optimizers"),
                 r"m' = m\,(1 - s_1),\quad P_{opt} = P_{el}\,[1 - s\,(1 - \eta_{opt})],\quad "
                 r"P_{string} \leq I_{out,max}\,U_{string},\quad I_{DC} = P / U_{string}",
                 _("Each optimizer follows the maximum power point of its module, so the modules alone on one no "
                   "longer drag one another: the mismatch between modules is not applied to them (two modules on one "
                   "optimizer keep it). The electrical effect of a shadow is counted optimizer by optimizer, each "
                   "with its modules as a string of its own. The optimizer converts with its weighted efficiency; "
                   "the inverter holds the string at its fixed voltage, so the string's current goes with its power "
                   "(the DC wiring loss with the square of the power) and a string carries at most its optimizers' "
                   "output current at that voltage: what is above is cut. A string's power hour by hour is its "
                   "modules' share of the array's power."),
                 [Quantity("s", _("modules on optimizers"), 100 * opt.share, "%", computed(_("from the strings")), 0),
                  Quantity("s_1", _("modules alone on an optimizer"), 100 * opt.single, "%",
                           computed(_("from the strings")), 0),
                  Quantity(r"\eta_{opt}", _("weighted efficiency of the optimizer"), 100 * opt.eta, "%", opt.source, 1),
                  Quantity(r"U_{string}", _("inverter's fixed string voltage"), opt.v_string, "V",
                           Source("data", _("the inverter's datasheet and SolarEdge's tables"))),
                  Quantity("m'", _("mismatch applied"), got["mismatch"], "%", computed(""), 2)],
                 Quantity(r"\Delta E", _("energy lost to the optimizers and to the strings' limit over the year"),
                          100 * (1.0 - (1.0 - got["loss"]) * (1.0 - got["cut"])), "%", computed(""), 2),
                 _("{datasheet}, p. 1-2 (module-level MPPT, weighted efficiency); SolarEdge, Single String Design "
                   "Guidelines v1.1, p. 4 (the power cut)").format(datasheet=opt.source.ref or opt.source.label)))


def _electrical_step(rec: Record, a: ArraySpec, near: nearshade.Shading, n_strings: int, loss: float,
                     losses: Losses, optimized: bool = False) -> None:
    rec.add(Step(f"{a.key}.electrical", a.name + ": " + _("Electrical effect of the shading"),
                 r"(1 - F_{ES}) = (1 - F_{GS})\left(1 - f_{el}\,\frac{N_{SB}}{N_{TB} + 1}\right),\quad "
                 r"N_{TB} = n_b\,N_s",
                 _("The modules of a string carry one current: the shadow costs more than its area. For each string "
                   "the direct light is cut by its shaded share and again by the share of its blocks (the cells "
                   "behind one bypass diode) the shadow touches, N_SB, counted on each module for every position "
                   "of the sun. A module has three strips of cells along its long side, one per diode, split in two "
                   "halves when its cells are half cells: upright and shaded from below, all its blocks are "
                   "touched, or the lower three of six. What goes beyond the linear shade already counted is taken "
                   "from the direct part of the power, for the share f_el of the effect chosen in the losses; the "
                   "diffuse light is taken as even, without electrical effect.") + " " + (
                     _("With power optimizers each optimizer's modules are a string of their own: the shadow costs "
                       "only the modules it touches.") + " " if optimized else "") + _estimate_shade(),
                 [Quantity(r"n_b", _("blocks of a module"), near.per_module, "",
                           Source("data", _("bypass diodes and half cells of the module's PVsyst file")) if a.module.diodes
                           else Source("model", _("three bypass diodes, in two halves for half cells (from the module's "
                                                  "cells)")), 0),
                  Quantity("", _("optimizers") if optimized else _("strings"), n_strings, "", computed(""), 0),
                  *_electrical_quantities(losses)],
                 Quantity(r"\Delta E", _("energy lost to the electrical effect over the year"), 100 * loss, "%",
                          computed(""), 2),
                 _("Martinez-Moreno, Munoz, Lorenzo, Solar Energy Materials and Solar Cells 94 (2010) 2298-2303, "
                   "eq. 6 (pvlib.shading.direct_martinez)")))


def _system_steps(rec: Record, inv: InverterSpec, losses: Losses, p_stc: float, energy: float, h_poa: float,
                  pr: float) -> None:
    default = Source("default", _("Meridiana's default, can be changed in the losses"))
    rec.add(Step("inverter", _("Inverter"),
                 r"\eta = \frac{\eta_{nom}}{0.9637}\left(-0.0162\,\zeta - \frac{0.0059}{\zeta} + 0.9858\right),"
                 r"\quad P_{AC} = \min(\eta\,P_{DC},\ P_{AC,nom})",
                 _("The efficiency curve of PVWatts scaled to the weighted efficiency of the inverter; above its "
                   "nominal AC power the inverter clips."),
                 [Quantity(r"P_{AC,nom}", _("nominal AC power, all inverters"), inv.pac_total / 1000.0, "kW", inv.source, 2),
                  Quantity(r"\eta_{nom}", _("weighted efficiency"), 100 * inv.eta, "%", inv.source, 1),
                  Quantity(r"P_{STC}/P_{AC,nom}", _("DC/AC ratio"), p_stc / inv.pac_total, "", computed(""), 2)],
                 None, _("Dobos, PVWatts Version 5 Manual, NREL/TP-6A20-62641, 2014 (pvlib.inverter.pvwatts)")))
    rec.add(Step("ac", _("AC side"), r"E_{AC} = \sum_h P_{AC}\left(1 - r_{AC}\frac{P_{AC}}{P_{AC,nom}}\right)(1-u)\,\Delta t",
                 _("AC wiring loss: ohmic, so it grows with the square of the current, that is of the power at the "
                   "grid's voltage; given at the nominal AC power of the inverters, it is r_AC (P/P_nom)² of P_nom each "
                   "hour (PVsyst refers its AC loss fraction to the array's STC power instead: with DC/AC above 1 "
                   "the same percentage means a larger loss here). Then the hours the system is out of service."),
                 [Quantity(r"r_{AC}", _("AC wiring loss at nominal power"), losses.ac_wiring, "%", default, 1),
                  Quantity("u", _("unavailability"), losses.unavailability, "%", default, 1)],
                 Quantity(r"E_{AC}", _("energy produced in a typical year"), energy, "kWh", computed(""), 0), ""))
    rec.add(Step("pr", _("Performance ratio"), r"PR = \frac{E_{AC} / P_0}{H_i / G_{ref}}",
                 _("The final yield over the reference yield: the energy produced per kWp over the hours of sun at "
                   "1 kW/m² on the plane of the modules."),
                 [Quantity(r"E_{AC}", _("energy produced"), energy, "kWh", computed(""), 0),
                  Quantity(r"P_0", _("power at STC"), p_stc / 1000.0, "kWp", computed(""), 2),
                  Quantity(r"H_i", _("irradiation on the plane (weighted on the arrays' power)"), h_poa, "kWh/m²",
                           computed(""), 1),
                  Quantity(r"G_{ref}", _("reference irradiance"), 1, "kW/m²", Source("norm", "IEC 61724-1:2021"), 0)],
                 Quantity("PR", _("performance ratio"), 100 * pr, "%", computed(""), 1),
                 _("IEC 61724-1:2021, performance ratio (the standard is not in the local archive)")))
