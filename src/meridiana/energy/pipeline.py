"""The energy pipeline of a project, as one function without Qt: the weather of the site, the arrays of
the modules laid, the consumption, the hourly year with its losses, the strings on the modules and the year
again with their electrical effect, the counts out of the shadows for the checks, PVGIS's second opinion, the
economics and the sizings. The window's job (`ui/window.py`), the comparison of the variants and the tests
call it alike (study 18, A 9.3, step 1).

The network is used when the designer asked or the window found the site's data missing (`fetch`): otherwise only
what is inside the project or in the cache."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path

from .. import checks, log
from ..i18n import _, number
from . import consumption as consumption_model
from . import economics, meteo, plant, pvgis, system
from .simulate import simulate, with_strings


@dataclass
class EnergyResult:
    """What the pipeline gives; a field is None when the pipeline stopped before it (no weather, no module
    laid) or the step had nothing to say. `as_dict` is what the window, the checks, the rules, the report and
    the comparison read today."""

    notes: list = field(default_factory=list)
    error_sim: str | None = None
    meteo_text: str | None = None
    load: object = None             # consumption.Load
    context: object = None          # consumption.Context, once the production is known
    sim: object = None              # simulate.Result
    strings: dict | None = None     # {"strings", "t_min", "t_cell_max"} or {"error"}: what the Production says
    plant: object = None            # plant.Plant: the inverters, the strings on the modules and their checks
    shade_free_counts: dict | None = None
    pvgis: object = None            # pvgis.PVGISEstimate
    econ: object = None             # economics.Result
    sizing: object = None
    storage: object = None
    battery_kwh: float | None = None

    def as_dict(self) -> dict:
        """The keys with a value, `notes` always: `.get("sim") is None` means what it meant."""
        out = {"notes": list(self.notes)}
        for f in fields(self):
            value = getattr(self, f.name)
            if f.name != "notes" and value is not None:
                out[f.name] = value
        return out


STEPS = 4         # what `progress` counts: the typical year, the horizon, the year hour by hour, PVGIS's estimate


class Interrupted(Exception):
    """The designer stopped the computation (Cancel, study 16 F4): raised by the `progress` of the caller between
    two steps, so between two requests to PVGIS; nothing to show and nothing to say."""


def compute(project, results: dict, cache: Path, fetch: bool, progress=None, refresh: bool = False) -> EnergyResult:
    """The pipeline on `project` (a copy of the window's, or any project) with the layouts of its sub-fields
    (`results`: id -> layout.Result, the good ones). MeteoError when the weather asked for could not be had;
    any other error is the caller's to say. `progress(done, STEPS, what)` is called before each step (the
    window's bar for PVGIS), and may raise Interrupted to stop there. `fetch` allows the network; `refresh`
    downloads again even when the project or cache already has the data."""
    step = progress or (lambda *_a: None)
    out = EnergyResult()
    lat, lon = project.site.lat, project.site.lon
    climate = getattr(project, "climate", {}) or (getattr(project, "resources", {}) or {}).get("weather") or {}
    embedded = climate.get("tmy") if not refresh and meteo.usable(climate.get("tmy"), lat, lon) else None
    cached = embedded is not None or meteo.cached(lat, lon, cache)
    arrays = system.arrays_of(project, results)
    ctx = consumption_model.Context(p_stc_kw=sum(a.p_stc for a in arrays) / 1000.0)
    wanted = consumption_model.Consumption.from_dict(project.consumption)
    out.load = consumption_model.build(wanted, ctx)
    if not (fetch or cached):
        out.meteo_text = _("Not fetched yet: PVGIS gives the typical year of the site for free, with the network.")
        out.error_sim = _("Fetch the weather of the site first (button above).")
        return out
    step(0, STEPS, _("the typical year"))
    m = meteo.typical_year(lat, lon, cache, refresh=refresh, embedded=embedded)
    s = m.summary
    out.meteo_text = _("{source}, fetched {date}. Global horizontal irradiation {ghi} kWh/m², mean "
                       "temperature {t} °C (from {tmin} to {tmax} °C).").format(
        source=m.source.label, date=m.fetched, ghi=number(s["ghi_kwh_m2"], 0, grouping=True),
        t=number(s["t_mean"], 1), tmin=number(s["t_min"], 1), tmax=number(s["t_max"], 1))
    losses = system.losses_of(project)
    hor = None
    step(1, STEPS, _("the horizon"))
    if losses.use_horizon:
        try:
            embedded_horizon = climate.get("horizon") if not refresh and embedded is not None else None
            has_horizon = embedded_horizon is not None or meteo.cached(lat, lon, cache, "horizon")
            hor = meteo.horizon(lat, lon, cache, refresh=refresh, embedded=embedded_horizon) if (fetch or has_horizon) else None
        except meteo.MeteoError as error:
            out.notes.append(str(error))
    if not arrays:
        out.error_sim = _("Lay the modules of a sub-field first: the production is computed on the modules laid.")
        return out
    p_stc = sum(a.p_stc for a in arrays)
    inverters = system.inverters_of(project, p_stc)
    inverter = system.combined(inverters)          # the AC side of the year: every inverter together
    step(2, STEPS, _("the year hour by hour"))
    sim = simulate(m, arrays, inverter, losses, hor)
    # the strings, from the temperatures of the year; laid on the modules, they give the shade of the
    # obstacles its electrical effect, applied downstream of the first pass (the sun, the transposition, the
    # shadings and the temperature are not computed twice: task 18c, step 3)
    t_cell_max = max(a["t_cell_max"] for a in sim.arrays)
    t_air_min = float(m.data.temp_air.min())
    out.plant = plant.build(project, groups=plant.groups_from_arrays(project, arrays), t_cell_max_year=t_cell_max,
                            t_min_year=t_air_min, p_dc_hourly=sim.hourly.p_dc.to_numpy())
    out.strings = ({"error": out.plant.notes[0]} if out.plant.notes else
                   {"strings": len(out.plant.strings), "t_min": out.plant.t_min, "t_cell_max": t_cell_max})
    # the power optimizers on the modules (task 22): their efficiency, the module-level MPPT, the strings' limit
    optimized = plant.optimizers_of(out.plant, arrays)
    by_array = {}
    if out.plant.strings:
        for a in arrays:
            keys = {pm.key for pm in a.placed}
            sfid = a.key.split(".")[0]
            # a string by hand may cross two arrays: each array takes its own modules of it; with optimizers each
            # optimizer's modules are a string of their own for the electrical effect of the shade
            runs = []
            for s in out.plant.strings:
                mine = [k for sf, k, _c in s.modules if sf == sfid and k in keys]
                per = plant.optimizer_per(out.plant, s)
                if mine:
                    runs += [mine[j:j + per] for j in range(0, len(mine), per)] if per else [mine]
            if runs and a.obstacles:
                by_array[a.key] = runs
    if (by_array and losses.use_near) or optimized is not None:
        sim = with_strings(sim, by_array if losses.use_near else None, optimized)
    out.sim = sim
    # what keeping the modules out of the obstacles' shadows would leave, for the fix the checks offer: a
    # layout for each shaded sub-field, here and not in the window's thread (it cost 30-40 ms there at each
    # result, 0.3-0.4 s on a large field)
    counts = {}
    for sfid, lost in checks.obstacle_shading_by_subfield(sim).items():
        if lost <= checks.OBSTACLE_SHADE:
            continue
        sf = next((s for s in project.subfields if s.id == sfid), None)
        if sf is not None and not sf.layout_params().shade_free and not sf.manual:      # by hand: no such fix
            counts[sfid] = checks.count_out_of_shadows(project, sf)
    out.shade_free_counts = counts
    if wanted.follows_production(ctx):
        ctx.production_kwh = sim.energy_kwh
        out.load = consumption_model.build(wanted, ctx)
    out.context = ctx
    try:
        # the same LID as the chain (the module's first-year loss when the designer gave none) and the
        # horizon only when the chain applies it, so that PVGIS and Meridiana see the same losses
        loss = system.pvgis_loss(losses, inverter.eta, arrays[0].module)
        months = [0.0] * 12
        yearly = 0.0
        estimate = None
        for a in arrays:
            step(3, STEPS, _("PVGIS's estimate"))           # before each request: a Cancel stops between them
            estimate = pvgis.pvcalc(lat, lon, a.p_stc / 1000.0, a.tilt, a.azimuth,
                                    system.pvgis_loss(losses, inverter.eta, a.module), cache,
                                    building=a.thermal != "open", network=fetch, horizon=losses.use_horizon)
            yearly += estimate.yearly_kwh
            months = [x + y for x, y in zip(months, estimate.monthly_kwh, strict=True)]
        if estimate is not None:
            out.pvgis = pvgis.PVGISEstimate(yearly, months, loss, estimate.source)
    except meteo.MeteoError as error:
        out.notes.append(str(error))
    degradation = next((a.module.yearly_loss for a in arrays if a.module.yearly_loss is not None), None)
    degradation = float(degradation) if degradation is not None else None
    settings = economics.Settings.from_dict(project.economics)
    load = out.load
    out.econ = economics.evaluate(sim.hourly.e_kwh, load.hourly, sim.p_stc_kw, sim.p_ac_kw, settings,
                                  project.site.address, degradation)
    out.sizing = economics.sizing(sim.hourly.e_kwh, load.hourly, sim.p_stc_kw, sim.p_ac_kw, settings,
                                  project.site.address, degradation)
    out.storage = economics.storage_sizing(sim.hourly.e_kwh, load.hourly, sim.p_stc_kw, sim.p_ac_kw, settings,
                                           project.site.address, degradation)
    battery = economics.Battery.from_settings(settings)
    out.battery_kwh = battery.usable_kwh if battery is not None else 0.0
    return out


def compute_or_say(project, results: dict, cache: Path, fetch: bool, progress=None,
                   refresh: bool = False) -> EnergyResult:
    """`compute`, with what went wrong in `error_sim` instead of an exception: the weather that could not be
    had in the designer's words, anything else logged and named (a thread's boundary: said out loud, not lost).
    Interrupted goes on to the caller: it asked for it."""
    try:
        return compute(project, results, cache, fetch, progress, refresh=refresh)
    except Interrupted:
        raise
    except meteo.MeteoError as error:
        return EnergyResult(error_sim=_("The weather could not be had: {error}").format(error=error))
    except Exception as error:      # noqa: BLE001
        log.complain("energy", error)
        return EnergyResult(error_sim=f"{type(error).__name__}: {error}")
