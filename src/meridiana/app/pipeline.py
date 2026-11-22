"""The energy pipeline of a project, as one function without Qt: the weather of the site, the arrays of
the modules laid, the consumption, the hourly year with its losses, the strings on the modules and the year
again with their electrical effect, the counts out of the shadows for the checks, PVGIS's second opinion, the
economics and the sizings. The window's job (`ui/window.py`), the comparison of the variants and the tests
call it alike (study 18, A 9.3, step 1).

The network is used when the designer asked or the window found the site's data missing (`fetch`): otherwise only
what is inside the project or in the cache."""

from __future__ import annotations

from dataclasses import dataclass, field, fields, replace
from pathlib import Path

from meridiana.core.rules import checks
from meridiana.app.platform import log
from meridiana.i18n import _, number
from meridiana.core.energy import consumption as consumption_model
from meridiana.core.energy import economics, faces, meteo, plant, pvgis, system
from meridiana.core.energy.simulate import simulate, with_network
from meridiana.core.rules import registry
from meridiana.core.energy.calculation_basis import CalculationBasis, basis_of


@dataclass
class EnergyResult:
    """What the pipeline gives; a field is None when the pipeline stopped before it (no weather, no module
    laid) or the step had nothing to say. `as_dict` is what the window, the checks, the rules, the report and
    the comparison read today."""

    notes: list = field(default_factory=list)
    error_sim: str | None = None
    meteo_text: str | None = None
    meteo_brief: tuple | None = None    # the same in two short lines, for the bar of the Production (R313)
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
    basis: CalculationBasis | None = None    # immutable context of this result, never today's edited plant

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


def _embedded(project, refresh: bool = False) -> tuple[dict, dict | None]:
    """The project's climate block and the typical year kept in it, when it is of this site (not on a refresh)."""
    lat, lon = project.site.lat, project.site.lon
    climate = getattr(project, "climate", {}) or (getattr(project, "resources", {}) or {}).get("weather") or {}
    embedded = climate.get("tmy") if not refresh and meteo.usable(climate.get("tmy"), lat, lon) else None
    return climate, embedded


def weather_at_hand(project, cache: Path, refresh: bool = False) -> bool:
    """Whether the typical year of the site is in the project or in the cache: had without the network."""
    _climate, embedded = _embedded(project, refresh)
    return embedded is not None or meteo.cached(project.site.lat, project.site.lon, cache)


def weather_of(project, cache: Path, refresh: bool = False):
    """The typical year of the site (meteo.Meteo): the one in the project, else the cache's, else PVGIS's (the
    network: ask weather_at_hand first when it is not allowed). MeteoError when it could not be had."""
    _climate, embedded = _embedded(project, refresh)
    return meteo.typical_year(project.site.lat, project.site.lon, cache, refresh=refresh, embedded=embedded)


def horizon_of(project, cache: Path, fetch: bool, refresh: bool = False):
    """The horizon of the site (meteo.Horizon): the one in the project with its typical year, else the cache's, else
    (`fetch`) PVGIS's; None when it is not at hand and the network is not allowed. MeteoError when it could not be
    had."""
    lat, lon = project.site.lat, project.site.lon
    climate, embedded = _embedded(project, refresh)
    embedded_horizon = climate.get("horizon") if not refresh and embedded is not None else None
    has_horizon = embedded_horizon is not None or meteo.cached(lat, lon, cache, "horizon")
    return meteo.horizon(lat, lon, cache, refresh=refresh, embedded=embedded_horizon) if (fetch or has_horizon) else None


def compute(project, results: dict, cache: Path, fetch: bool, progress=None, refresh: bool = False) -> EnergyResult:
    """The pipeline on `project` (a copy of the window's, or any project) with the layouts of its sub-fields
    (`results`: id -> layout.Result, the good ones). MeteoError when the weather asked for could not be had;
    any other error is the caller's to say. `progress(done, STEPS, what)` is called before each step (the
    window's bar for PVGIS), and may raise Interrupted to stop there; inside the electrical network `done` is a
    fraction between 2 and 3, told before each chunk of hours, so that a Cancel stops it there too. `fetch` allows the network; `refresh`
    downloads again even when the project or cache already has the data."""
    step = progress or (lambda *_a: None)
    out = EnergyResult()
    lat, lon = project.site.lat, project.site.lon
    cached = weather_at_hand(project, cache, refresh)
    arrays = system.arrays_of(project, results)
    ctx = consumption_model.Context(p_stc_kw=sum(a.p_stc for a in arrays) / 1000.0)
    wanted = consumption_model.Consumption.from_dict(project.consumption, profile_id=project.regulatory_profile)
    out.load = consumption_model.build(wanted, ctx, profile_id=project.regulatory_profile, timezone=registry.effective_timezone(project))
    if not (fetch or cached):
        out.meteo_text = _("Not fetched yet: PVGIS gives the typical year of the site for free, with the network.")
        out.meteo_brief = (_("Not fetched yet."), "")
        out.error_sim = _("Fetch the weather of the site first (button above).")
        return out
    step(0, STEPS, _("the typical year"))
    m = weather_of(project, cache, refresh)
    s = m.summary
    out.meteo_text = _("{source}, fetched {date}. Global horizontal irradiation {ghi} kWh/m², mean "
                       "temperature {t} °C (from {tmin} to {tmax} °C).").format(
        source=m.source.label, date=m.fetched, ghi=number(s["ghi_kwh_m2"], 0, grouping=True),
        t=number(s["t_mean"], 1), tmin=number(s["t_min"], 1), tmax=number(s["t_max"], 1))
    out.meteo_brief = (_("{source}, fetched {date}").format(source=m.source.label.split(",")[0], date=m.fetched),
                       _("{ghi} kWh/m² a year, mean {t} °C").format(ghi=number(s["ghi_kwh_m2"], 0, grouping=True),
                                                                    t=number(s["t_mean"], 1)))
    losses = system.losses_of(project)
    hor = None
    step(1, STEPS, _("the horizon"))
    if losses.use_horizon:
        try:
            hor = horizon_of(project, cache, fetch, refresh)
        except meteo.MeteoError as error:
            out.notes.append(str(error))
    if not arrays:
        out.error_sim = _("Lay the modules of a sub-field first: the production is computed on the modules laid.")
        return out
    p_stc = sum(a.p_stc for a in arrays)
    inverters = system.inverters_of(project, p_stc)
    inverter = system.combined(inverters)          # the AC side of the year: every inverter together
    step(2, STEPS, _("the year hour by hour"))
    sim = simulate(m, arrays, inverter, losses, hor, timezone=registry.effective_timezone(project), profile_id=project.regulatory_profile)
    # the strings, from the temperatures of the year; laid on the modules, they give the shade of the
    # obstacles its electrical effect. A partial connection needs a second pass for its contributing panels;
    # a fully connected plant reuses this pass (task 18c, step 3).
    t_cell_max = max(a["t_cell_max"] for a in sim.arrays)
    t_air_min = float(m.data.temp_air.min())
    out.plant = plant.build(project, groups=plant.groups_from_arrays(project, arrays), t_cell_max_year=t_cell_max,
                            t_min_year=t_air_min, p_dc_hourly=sim.hourly.p_dc.to_numpy())
    out.strings = ({"error": out.plant.notes[0]} if out.plant.notes else
                   {"strings": len(out.plant.strings), "t_min": out.plant.t_min, "t_cell_max": t_cell_max})
    # The first pass is potential generation, used only to determine the year's checking temperatures.
    # A string without an existing, explicitly chosen inverter/input transfers no power; a sized placeholder
    # is not an installed inverter. Plant.build already removes duplicate module keys from the runs.
    real_units = {u.number: u for u in out.plant.units if u.entry >= 0 and u.spec.pac > 0}
    wired = [s for s in out.plant.strings if s.inverter in real_units
             and 1 <= s.mppt <= real_units[s.inverter].inputs]
    connected = {(sf, key) for s in wired for sf, key, _centre in s.modules}
    arrays = [replace(a, connected=frozenset(pm.key for pm in a.placed
                                           if (a.key.split(".")[0], pm.key) in connected)) for a in arrays]
    active_units = {s.inverter for s in wired if s.modules}
    active_inverter = system.combined([u.spec for n, u in real_units.items() if n in active_units]) if active_units else inverter
    limited = any(a.generating_modules != a.modules for a in arrays)
    if limited or (active_inverter.pac_total, active_inverter.eta) != (inverter.pac_total, inverter.eta):
        inverter = active_inverter
        sim = simulate(m, arrays, inverter, losses, hor, timezone=registry.effective_timezone(project), profile_id=project.regulatory_profile)
    if limited:
        out.notes.append(_("Only modules connected to an existing inverter input contribute to production; "
                           "unconnected modules produce zero."))
    # the power optimizers on the modules (task 22): their efficiency, the module-level MPPT, the strings' limit
    generating_arrays = [replace(a, modules=a.generating_modules,
                                 placed=[pm for pm in a.placed if pm.key in a.connected])
                         for a in arrays if a.generating_modules]
    optimized = plant.optimizers_of(out.plant, generating_arrays)
    # the longest step on a large plant (R266): told at each chunk of hours with how far it is, 2 to 3 of STEPS
    sim = with_network(sim, out.plant, optimized,
                       progress=lambda share: step(2 + share, STEPS, _("the electrical network")))
    out.sim = sim
    # Overload checks receive the connected DC year, not the preliminary potential year.
    out.plant = plant.build(project, groups=plant.groups_from_arrays(project, arrays), t_cell_max_year=t_cell_max,
                            t_min_year=t_air_min, p_dc_hourly=sim.hourly.p_dc.to_numpy(), p_dc_connected=True,
                            p_dc_by_inverter={item['number']: item['p_dc'] for item in sim.inverters},
                            exposure=faces.year_of(sim))
    # what keeping the modules out of the obstacles' shadows would leave, for the fix the checks offer: a
    # layout for each shaded sub-field, here and not in the window's thread (it cost 30-40 ms there at each
    # result, 0.3-0.4 s on a large field)
    counts = {}
    for sfid, lost in checks.obstacle_shading_by_subfield(sim).items():
        if lost <= checks.OBSTACLE_SHADE:
            continue
        sf = next((s for s in project.subfields if s.id == sfid), None)
        if sf is not None and not sf.layout_params(profile_id=project.regulatory_profile).shade_free and not sf.manual:      # by hand: no such fix
            counts[sfid] = checks.count_out_of_shadows(project, sf)
    out.shade_free_counts = counts
    if wanted.follows_production(ctx, profile_id=project.regulatory_profile):
        ctx.production_kwh = sim.energy_kwh
        out.load = consumption_model.build(wanted, ctx, profile_id=project.regulatory_profile, timezone=registry.effective_timezone(project))
    out.context = ctx
    try:
        # the same LID as the chain (the module's first-year loss when the designer gave none) and the
        # horizon only when the chain applies it, so that PVGIS and Meridiana see the same losses
        loss = system.pvgis_loss(losses, inverter.eta, arrays[0].module)
        months = [0.0] * 12
        yearly = 0.0
        estimate = None
        for a in generating_arrays:
            step(3, STEPS, _("PVGIS's estimate"))           # before each request: a Cancel stops between them
            estimate = pvgis.pvcalc(lat, lon, a.p_stc / 1000.0, a.tilt, a.azimuth,
                                    system.pvgis_loss(losses, inverter.eta, a.module), cache,
                                    building=a.thermal != "open", network=fetch, horizon=losses.use_horizon)
            yearly += estimate.yearly_kwh
            months = [x + y for x, y in zip(months, estimate.monthly_kwh, strict=True)]
        if estimate is not None:
            out.pvgis = pvgis.PVGISEstimate(yearly, months, loss, estimate.source)
        elif not generating_arrays:
            from meridiana.core.energy.pedigree import Source
            out.pvgis = pvgis.PVGISEstimate(0.0, months, loss, Source("computed", _("No connected modules")))
    except meteo.MeteoError as error:
        out.notes.append(str(error))
    degradation = next((a.module.yearly_loss for a in arrays if a.module.yearly_loss is not None), None)
    degradation = float(degradation) if degradation is not None else None
    from meridiana.core.energy.storage import validate_connection
    validate_connection(project.economics, project.energy.get("inverters", []))
    settings = economics.Settings.from_dict(project.economics, profile_id=project.regulatory_profile)
    load = out.load
    out.econ = economics.evaluate(sim.hourly.e_kwh, load.hourly, sim.p_stc_kw, sim.p_ac_kw, settings,
                                  project.site.address, degradation, profile_id=project.regulatory_profile, timezone=registry.effective_timezone(project))
    out.sizing = economics.sizing(sim.hourly.e_kwh, load.hourly, sim.p_stc_kw, sim.p_ac_kw, settings,
                                  project.site.address, degradation, profile_id=project.regulatory_profile, timezone=registry.effective_timezone(project))
    out.storage = economics.storage_sizing(sim.hourly.e_kwh, load.hourly, sim.p_stc_kw, sim.p_ac_kw, settings,
                                           project.site.address, degradation, profile_id=project.regulatory_profile, timezone=registry.effective_timezone(project))
    battery = economics.Battery.from_settings(settings)
    out.battery_kwh = battery.usable_kwh if battery is not None else 0.0
    out.basis = basis_of(sim, battery=battery, battery_units=settings.battery_units, econ=out.econ)
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
