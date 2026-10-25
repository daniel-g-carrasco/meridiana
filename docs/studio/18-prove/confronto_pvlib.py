"""Study 18, part B.1: Meridiana's hourly production chain (src/meridiana/energy/simulate.py) against pvlib
on the synthetic clear-sky year of tests/_energy.py (clear_sky_meteo: simplified Solis dimmed to 72 %,
a seasonal temperature, 1.5 m/s of wind; Rho's coordinates).

The same system (one array at 15 degrees facing South, 188 LONGi LR7-54HVH-495M of the catalogue on two
Huawei SUN2000-50KTL-M3, DC/AC 0.93) on the same weather, computed three ways:
1. Meridiana, simulate.simulate(), twice: with every percentage loss at zero ("clean"), to compare the
   physics step by step, and with the default Losses(), to check the bookkeeping of the chain against the
   formulas the pedigree prints;
2. a replica with pvlib's base functions, written here in the order simulate.py declares (NREL SPA at the
   offset instant, Perez 1990, ASHRAE IAM with Marion's integration for the diffuse parts, PVsyst cell
   temperature on the incident irradiance, De Soto at 25 degrees plus the datasheet's gamma, PVWatts
   inverter): where Meridiana and the replica differ, the code does not do what its docstring says;
3. pvlib.modelchain.ModelChain with the same models (perez, ashrae, pvsyst, desoto, pvwatts, no_loss):
   where the replica and the ModelChain differ, Meridiana departs from pvlib's standard chain, on purpose
   (the IAM on the diffuse, the temperature through gamma instead of the single-diode model) or not.

Meridiana's intermediate values (plane irradiance, cell temperature, module power at 25 degrees) are read
by wrapping the pvlib functions and the ModuleSpec method it calls; nothing in src/ is changed.

Hour by hour: RMSE, largest difference and when; over the year: the sums and their difference in %.
The results go to confronto_pvlib-risultati.txt beside this script.

Run from the repository root:
    PYTHONPATH=src QT_QPA_PLATFORM=offscreen python docs/studio/18-prove/confronto_pvlib.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import pvlib  # noqa: E402
from pvlib.pvsystem import max_power_point  # noqa: E402

from _energy import clear_sky_meteo  # noqa: E402
from meridiana import catalog  # noqa: E402
from meridiana.energy import simulate as sim_mod  # noqa: E402
from meridiana.energy.components import InverterSpec, ModuleSpec  # noqa: E402
from meridiana.energy.simulate import ArraySpec, Losses, simulate  # noqa: E402

OUT = HERE / "confronto_pvlib-risultati.txt"
TILT, AZIMUTH_CEI = 15.0, 0.0            # CEI 82-25: from South, + West
SURFACE_AZ = 180.0                       # pvlib: from North, clockwise
N_MODULES = 188
INVERTERS = 2
LINES: list[str] = []


def say(text: str = "") -> None:
    print(text)
    LINES.append(text)


class Spy:
    """Wraps a function and keeps every result it returned, in order."""

    def __init__(self, func):
        self.func, self.calls = func, []

    def __call__(self, *args, **kwargs):
        out = self.func(*args, **kwargs)
        self.calls.append(out)
        return out


def compare(name: str, unit: str, a: np.ndarray, b: np.ndarray, index: pd.DatetimeIndex, what: str,
            energy: bool = True) -> None:
    """a: Meridiana's hourly values; b: the other chain's. Sums as kWh or kWh/m² (energy) or means."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    diff = b - a
    k = int(np.nanargmax(np.abs(diff)))
    rmse = float(np.sqrt(np.nanmean(diff ** 2)))
    if energy:
        sa, sb = float(np.nansum(a) / 1000.0), float(np.nansum(b) / 1000.0)
        rel = 100.0 * (sb / sa - 1.0) if sa else float("nan")
        say(f"  {name:34} Meridiana {sa:12.2f}  {what} {sb:12.2f}  scarto {rel:+8.4f} %   RMSE {rmse:9.4f} {unit}"
            f"   max |scarto| {diff[k]:+10.4f} {unit} il {index[k].strftime('%d/%m %H:%M')}")
    else:
        sa, sb = float(np.nanmean(a)), float(np.nanmean(b))
        say(f"  {name:34} Meridiana {sa:12.3f}  {what} {sb:12.3f}  scarto {sb - sa:+8.4f}      RMSE {rmse:9.4f} {unit}"
            f"   max |scarto| {diff[k]:+10.4f} {unit} il {index[k].strftime('%d/%m %H:%M')}")


def main() -> None:
    meteo = clear_sky_meteo()
    d = meteo.data
    hours = len(d)
    rec = next(r for r in catalog.load("modules") if r["model"] == "LR7-54HVH-495M")
    module = ModuleSpec.from_record(catalog.for_project(rec))
    inv_rec = next(r for r in catalog.load("inverters") if r["model"] == "SUN2000-50KTL-M3")
    inverter = InverterSpec.from_record(inv_rec, count=INVERTERS)
    array = ArraySpec("s1", "Falda", TILT, AZIMUTH_CEI, N_MODULES, module, thermal="open")
    p_stc = array.p_stc
    sdm = module.sdm()
    say("Confronto Meridiana / pvlib sull'anno sintetico di tests/_energy.py (cielo sereno Solis x 0,72)")
    say(f"sito {meteo.latitude}, {meteo.longitude}, {meteo.elevation} m; offset del sole {meteo.time_offset_h} h")
    say(f"modulo {module.manufacturer} {module.model}: {module.pmax} W, gamma {module.gamma_pmax} %/K, "
        f"celle in serie {module.cells_in_series}, efficienza {100 * module.efficiency:.2f} %, "
        f"perdita primo anno {module.first_year_loss} %")
    say("SDM del modulo: " + ", ".join(f"{k} {v:.5g}" if isinstance(v, float) else f"{k} {v}" for k, v in sdm.items()))
    say(f"inverter {inverter.manufacturer} {inverter.model} x {inverter.count}: {inverter.pac_total / 1000:.1f} kW, "
        f"eta {100 * inverter.eta:.1f} %; campo {N_MODULES} moduli, {p_stc / 1000:.2f} kWp, DC/AC "
        f"{p_stc / inverter.pac_total:.2f}")
    say(f"GHI dell'anno {d.ghi.sum() / 1000:.1f} kWh/m2, DHI {d.dhi.sum() / 1000:.1f}, DNI {d.dni.sum() / 1000:.1f}")
    say()

    # ---- 1. Meridiana, with the intermediate values read through wrappers
    spy_poa = Spy(pvlib.irradiance.get_total_irradiance)
    spy_t = Spy(pvlib.temperature.pvsyst_cell)
    spy_iam = Spy(pvlib.iam.ashrae)
    pvlib.irradiance.get_total_irradiance = spy_poa
    pvlib.temperature.pvsyst_cell = spy_t
    pvlib.iam.ashrae = spy_iam
    p25_calls: list[np.ndarray] = []
    original_power = ModuleSpec.power_at_25

    def power_at_25(self, irradiance):
        out = original_power(self, irradiance)
        p25_calls.append(np.asarray(out, dtype=float))
        return out

    ModuleSpec.power_at_25 = power_at_25
    clean = Losses(soiling=0.0, quality=0.0, lid=0.0, mismatch=0.0, dc_wiring=0.0, ac_wiring=0.0, unavailability=0.0)
    try:
        t0 = time.perf_counter()
        s_clean = simulate(meteo, [array], inverter, clean)
        t_clean = time.perf_counter() - t0
        m_poa = spy_poa.calls[-1]
        m_tcell = np.asarray(spy_t.calls[-1], dtype=float)
        m_iam_b = np.asarray(spy_iam.calls[-1], dtype=float)
        m_p25 = p25_calls[-1]
        t0 = time.perf_counter()
        s_def = simulate(meteo, [array], inverter)
        t_def = time.perf_counter() - t0
        d_tcell = np.asarray(spy_t.calls[-1], dtype=float)
        d_p25 = p25_calls[-1]
    finally:
        pvlib.irradiance.get_total_irradiance = spy_poa.func
        pvlib.temperature.pvsyst_cell = spy_t.func
        pvlib.iam.ashrae = spy_iam.func
        ModuleSpec.power_at_25 = original_power
    index = s_clean.hourly.index
    say(f"simulate(): {t_clean:.2f} s (perdite a zero), {t_def:.2f} s (perdite predefinite)")
    say(f"Meridiana, perdite a zero: {s_clean.energy_kwh:.1f} kWh, {s_clean.specific_yield:.1f} kWh/kWp, PR {100 * s_clean.pr:.2f} %")
    say(f"Meridiana, perdite predefinite: {s_def.energy_kwh:.1f} kWh, {s_def.specific_yield:.1f} kWh/kWp, PR {100 * s_def.pr:.2f} %")
    say()

    # ---- 2. the replica with pvlib's base functions, as simulate.py declares
    t_sun = d.index + pd.Timedelta(hours=meteo.time_offset_h)
    sp = pvlib.solarposition.get_solarposition(t_sun, meteo.latitude, meteo.longitude, altitude=meteo.elevation,
                                               pressure=d.pressure.to_numpy(), temperature=d.temp_air.to_numpy())
    zen, az = sp.apparent_zenith.to_numpy(), sp.azimuth.to_numpy()
    dni_extra = pvlib.irradiance.get_extra_radiation(t_sun).to_numpy()
    airmass = pvlib.atmosphere.get_relative_airmass(zen)
    ghi, dni, dhi = d.ghi.to_numpy(), d.dni.to_numpy(), d.dhi.to_numpy()
    temp_air, wind = d.temp_air.to_numpy(), d.wind_speed.to_numpy()
    aoi = pvlib.irradiance.aoi(TILT, SURFACE_AZ, zen, az)
    poa = pvlib.irradiance.get_total_irradiance(TILT, SURFACE_AZ, zen, az, dni, ghi, dhi, dni_extra=dni_extra,
                                                airmass=airmass, albedo=clean.albedo, model="perez",
                                                diffuse_components=True)
    beam, sky, ground, circum = (np.nan_to_num(np.asarray(poa[k], dtype=float))
                                 for k in ("poa_direct", "poa_sky_diffuse", "poa_ground_diffuse", "poa_circumsolar"))
    g_inc = beam + sky + ground
    iam_b = np.nan_to_num(np.asarray(pvlib.iam.ashrae(aoi, b=clean.iam_b0), dtype=float))
    iam_d = pvlib.iam.marion_diffuse("ashrae", TILT, b=clean.iam_b0)
    iam_sky, iam_ground = float(np.atleast_1d(iam_d["sky"])[0]), float(np.atleast_1d(iam_d["ground"])[0])
    # simulate.py:232-235 moves Perez's circumsolar part from the sky diffuse to the beam before the IAM
    # (simulate.py:294), so the circumsolar takes the beam's IAM, not Marion's; the replica does the same
    g_iam = (beam + circum) * iam_b + (sky - circum) * iam_sky + ground * iam_ground
    g_iam_marion_all = beam * iam_b + sky * iam_sky + ground * iam_ground      # circumsolar as diffuse
    t_cell = np.asarray(pvlib.temperature.pvsyst_cell(g_inc, temp_air, wind, u_c=29.0, u_v=0.0,
                                                      module_efficiency=module.efficiency, alpha_absorption=0.9), float)

    def p_mp(g: np.ndarray, t) -> np.ndarray:
        """Maximum power of one module by De Soto's model, brentq, at irradiance g and cell temperature t."""
        g = np.asarray(g, dtype=float)
        t = np.broadcast_to(np.asarray(t, dtype=float), g.shape)
        lit = g > 1.0
        out = np.zeros_like(g)
        # the module's own model form (De Soto for the CEC list, PVsyst's for a .PAN or a datasheet fit)
        il, io, rs, rsh, nnsvth = module.diode_params(g[lit], t[lit])
        out[lit] = np.clip(np.asarray(max_power_point(il, io, rs, rsh, nnsvth, method="brentq")["p_mp"], float), 0, None)
        return out

    r_p25 = N_MODULES * p_mp(g_iam, 25.0)
    r_pt = r_p25 * (1.0 + module.gamma_pmax / 100.0 * (t_cell - 25.0))
    r_p_sdm = N_MODULES * p_mp(g_iam, t_cell)                   # the single-diode model at the cell temperature
    pdc0 = inverter.pac_total / inverter.eta
    r_ac = np.asarray(pvlib.inverter.pvwatts(r_pt, pdc0, eta_inv_nom=inverter.eta), dtype=float)

    # ---- 3. ModelChain, the same models
    loc = pvlib.location.Location(meteo.latitude, meteo.longitude, tz="UTC", altitude=meteo.elevation)
    if sdm.get("form") == "pvsyst":
        dc_model = "pvsyst"
        params = {k: sdm[k] for k in ("alpha_sc", "gamma_ref", "mu_gamma", "I_L_ref", "I_o_ref", "R_sh_ref", "R_sh_0",
                                      "R_sh_exp", "R_s", "cells_in_series")}
        params.update(EgRef=1.121)
    else:
        dc_model = "desoto"
        params = {k: sdm[k] for k in ("alpha_sc", "a_ref", "I_L_ref", "I_o_ref", "R_sh_ref", "R_s")}
        params.update(EgRef=1.121, dEgdT=-0.0002677)
    # pvlib reads module_efficiency and alpha_absorption of the PVsyst thermal model from module_parameters
    # (pvsystem.py, Array.get_cell_temperature), not from temperature_model_parameters
    params.update(b=clean.iam_b0, module_efficiency=module.efficiency, alpha_absorption=0.9)
    system = pvlib.pvsystem.PVSystem(
        surface_tilt=TILT, surface_azimuth=SURFACE_AZ, albedo=clean.albedo, module_parameters=params,
        temperature_model_parameters={"u_c": 29.0, "u_v": 0.0, "module_efficiency": module.efficiency,
                                      "alpha_absorption": 0.9},
        modules_per_string=N_MODULES, strings_per_inverter=1,
        inverter_parameters={"pdc0": pdc0, "eta_inv_nom": inverter.eta})
    mc = pvlib.modelchain.ModelChain(system, loc, transposition_model="perez", aoi_model="ashrae",
                                     spectral_model="no_loss", temperature_model="pvsyst", dc_model=dc_model,
                                     ac_model="pvwatts", losses_model="no_loss")
    weather = pd.DataFrame({"ghi": ghi, "dni": dni, "dhi": dhi, "temp_air": temp_air, "wind_speed": wind,
                            "pressure": d.pressure.to_numpy()}, index=t_sun)
    t0 = time.perf_counter()
    mc.run_model(weather)
    t_mc = time.perf_counter() - t0
    mc_poa = np.nan_to_num(mc.results.total_irrad["poa_global"].to_numpy(dtype=float))
    mc_eff = np.nan_to_num(mc.results.effective_irradiance.to_numpy(dtype=float))
    mc_tcell = np.asarray(mc.results.cell_temperature, dtype=float)
    mc_dc = np.nan_to_num(mc.results.dc["p_mp"].to_numpy(dtype=float))
    # with a single-diode DC model ModelChain.pvwatts_inverter feeds the whole dc frame to the curve
    # (modelchain.py:728-730): the AC power is its p_mp column
    ac_frame = mc.results.ac
    mc_ac = np.nan_to_num((ac_frame["p_mp"] if isinstance(ac_frame, pd.DataFrame) else ac_frame).to_numpy(dtype=float))
    say(f"ModelChain: {t_mc:.2f} s; DC {mc_dc.sum() / 1000:.1f} kWh, AC {mc_ac.sum() / 1000:.1f} kWh")
    say()

    # ---- the comparisons, step by step
    m_sky = np.nan_to_num(np.asarray(m_poa["poa_sky_diffuse"], dtype=float))
    m_ground = np.nan_to_num(np.asarray(m_poa["poa_ground_diffuse"], dtype=float))
    m_beam = np.nan_to_num(np.asarray(m_poa["poa_direct"], dtype=float))
    m_ginc = s_clean.hourly.poa.to_numpy()
    m_geff = s_clean.hourly.poa_eff.to_numpy()
    m_pdc = s_clean.hourly.p_dc.to_numpy()
    m_pac = s_clean.hourly.p_ac.to_numpy()
    m_p25n = N_MODULES * m_p25
    _m_pt = m_p25n * (1.0 + module.gamma_pmax / 100.0 * (m_tcell - 25.0))
    say("A. Meridiana (perdite a zero) contro la replica con le funzioni base di pvlib (stessi modelli dichiarati)")
    say("   somme annue in kWh/m2 o kWh; RMSE e scarto massimo orari")
    compare("POA globale (G_inc)", "W/m2", m_ginc, g_inc, index, "replica")
    compare("POA diretta", "W/m2", m_beam, beam, index, "replica")
    compare("POA diffusa dal cielo", "W/m2", m_sky, sky, index, "replica")
    compare("POA riflessa dal suolo", "W/m2", m_ground, ground, index, "replica")
    compare("IAM diretto (media oraria)", "", m_iam_b, iam_b, index, "replica", energy=False)
    compare("POA efficace (dopo IAM)", "W/m2", m_geff, g_iam, index, "replica")
    compare("T cella (media)", "°C", m_tcell, t_cell, index, "replica", energy=False)
    compare("P modulo a 25 °C x N", "W", m_p25n, r_p25, index, "replica")
    compare("P DC (25 °C + gamma)", "W", m_pdc, r_pt, index, "replica")
    compare("P AC (PVWatts, tagli, cavi 0)", "W", m_pac, r_ac, index, "replica")
    say(f"   IAM diffuso di Marion: cielo {iam_sky:.5f}, suolo {iam_ground:.5f} (ASHRAE b0 {clean.iam_b0}, {TILT} gradi)")
    say()
    say("B. Meridiana (perdite a zero) contro pvlib.modelchain.ModelChain (perez, ashrae, pvsyst, desoto, pvwatts)")
    compare("POA globale (G_inc)", "W/m2", m_ginc, mc_poa, index, "ModelChain")
    compare("POA efficace", "W/m2", m_geff, mc_eff, index, "ModelChain")
    compare("T cella (media)", "°C", m_tcell, mc_tcell, index, "ModelChain", energy=False)
    compare("P DC", "W", m_pdc, mc_dc, index, "ModelChain")
    compare("P AC", "W", m_pac, mc_ac, index, "ModelChain")
    say()
    say("C. Le cause, una alla volta (replica con un solo cambiamento)")
    compare("POA eff.: circumsolare con IAM diffuso", "W/m2", m_geff, g_iam_marion_all, index, "Marion su circ.")
    mc_eff_mer = beam * iam_b + sky + ground          # ModelChain's effective irradiance: no IAM on the diffuse
    compare("POA eff.: IAM solo sul diretto", "W/m2", m_geff, mc_eff_mer, index, "senza Marion")
    compare("P DC: De Soto alla T cella", "W", m_pdc, r_p_sdm, index, "SDM(T)")
    r_pt_mc = N_MODULES * p_mp(mc_eff_mer, 25.0) * (1.0 + module.gamma_pmax / 100.0 * (t_cell - 25.0))
    compare("P DC: gamma su POA eff. ModelChain", "W", m_pdc, r_pt_mc, index, "gamma, no Marion")
    p1000_25 = float(p_mp(np.array([1000.0]), 25.0)[0])
    p1000_45 = float(p_mp(np.array([1000.0]), 45.0)[0])
    gamma_sdm = 100.0 * (p1000_45 / p1000_25 - 1.0) / 20.0
    say(f"   gamma del modello De Soto adattato: {gamma_sdm:+.3f} %/K fra 25 e 45 °C (scheda {module.gamma_pmax:+.2f} %/K); "
        f"P(1000, 25) = {p1000_25:.2f} W contro P_STC {module.pmax} W")
    lit = m_ginc > 50
    say(f"   T cella media nelle ore con POA > 50 W/m2: {m_tcell[lit].mean():.1f} °C, massima {m_tcell.max():.1f} °C; "
        f"differenza DC media SDM(T) contro gamma: {100 * (r_p_sdm.sum() / m_pdc.sum() - 1):+.2f} %")
    say()

    # ---- D. the bookkeeping of the default chain against the pedigree's formulas, hour by hour
    say("D. Catena con le perdite predefinite (Losses()): ogni passo contro la formula della pedigree")
    L = Losses()
    lid = module.first_year_loss if module.first_year_loss is not None else 1.0
    say(f"   soiling {L.soiling} %, qualita {L.quality} %, LID {lid} % (dalla scheda), mismatch {L.mismatch} %, "
        f"cavi DC {L.dc_wiring} % a STC, cavi AC {L.ac_wiring} % a P_AC,nom, indisponibilita {L.unavailability} %")
    for step in s_def.chain:
        say(f"   {step.key:18} {step.label:55} {step.value:12.2f} {'kWh/m2' if step.kind == 'irradiance' else 'kWh':7} "
            f"{'' if step.change is None else f'{step.change:+8.3f} %'}")
    d_geff = s_def.hourly.poa_eff.to_numpy()
    exp_geff = g_iam * (1.0 - L.soiling / 100.0)
    compare("POA eff. con soiling 2 %", "W/m2", d_geff, exp_geff, index, "formula")
    exp_p25 = N_MODULES * p_mp(exp_geff, 25.0)
    compare("P a 25 °C x N (su POA eff.)", "W", N_MODULES * d_p25, exp_p25, index, "formula")
    exp_pt = N_MODULES * d_p25 * (1.0 + module.gamma_pmax / 100.0 * (d_tcell - 25.0))
    exp_pmm = exp_pt * (1.0 - L.quality / 100.0) * (1.0 - lid / 100.0) * (1.0 - L.mismatch / 100.0)
    exp_pdc = exp_pmm * (1.0 - L.dc_wiring / 100.0 * np.clip(exp_pmm / p_stc, 0.0, None))
    compare("P DC = P_mm (1 - r P_mm/P_STC)", "W", s_def.hourly.p_dc.to_numpy(), exp_pdc, index, "formula")
    unclipped, ac = sim_mod._pvwatts_inverter(exp_pdc, inverter.pac_total, inverter.eta)
    exp_pac = ac * (1.0 - L.ac_wiring / 100.0 * np.clip(ac / inverter.pac_total, 0.0, None)) * (1 - L.unavailability / 100)
    compare("P AC = PVWatts, taglio, cavi AC", "W", s_def.hourly.p_ac.to_numpy(), exp_pac, index, "formula")
    pv_ac = np.asarray(pvlib.inverter.pvwatts(exp_pdc, pdc0, eta_inv_nom=inverter.eta), dtype=float)
    compare("_pvwatts_inverter vs pvlib.pvwatts", "W", ac, pv_ac, index, "pvlib")
    chain = {c.key: c for c in s_def.chain}
    say(f"   verifica dei passi: LID {chain['lid'].change:+.3f} % (atteso {-lid:+.3f}), mismatch "
        f"{chain['mismatch'].change:+.3f} % (atteso {-L.mismatch:+.3f}), soiling {chain['soiling'].change:+.3f} % "
        f"(atteso {-L.soiling:+.3f}), cavi DC {chain['dc_wiring'].change:+.3f} % (atteso "
        f"{-100 * L.dc_wiring / 100 * (exp_pmm ** 2).sum() / (p_stc * exp_pmm.sum()):+.3f} dalla media pesata di P/P_STC)")
    say(f"   PR = E_AC / (P0 H_poa): {s_def.energy_kwh / (p_stc / 1000 * s_def.hourly.poa.sum() / 1000):.4f} "
        f"contro s.pr {s_def.pr:.4f}; resa {s_def.specific_yield:.1f} kWh/kWp")
    say()

    # ---- E. side checks: the sun of 1990 against the sun of 2026, the clipping with one inverter
    say("E. Controlli a margine")
    sp26 = pvlib.solarposition.get_solarposition(
        pd.date_range("2026-01-01 00:00", periods=hours, freq="h", tz="UTC") + pd.Timedelta(hours=meteo.time_offset_h),
        meteo.latitude, meteo.longitude, altitude=meteo.elevation, pressure=d.pressure.to_numpy(),
        temperature=d.temp_air.to_numpy())
    de = (sp26.apparent_elevation.to_numpy() - sp.apparent_elevation.to_numpy())
    up = sp.apparent_elevation.to_numpy() > 0
    say(f"   il sole e' calcolato sul 1990 (indice della TMY) e l'anno locale e' il 2026: elevazione diversa al massimo di "
        f"{np.abs(de[up]).max():.3f} gradi, in media {np.abs(de[up]).mean():.3f}, nelle ore di sole")
    one = InverterSpec.from_record(inv_rec, count=1)
    s_one = simulate(meteo, [array], one)
    c1 = {c.key: c for c in s_one.chain}
    say(f"   con un solo inverter da {one.pac_total / 1000:.0f} kW (DC/AC {p_stc / one.pac_total:.2f}): taglio "
        f"{c1['clipping'].change:+.2f} %, inverter {c1['inverter'].change:+.2f} %, energia {s_one.energy_kwh:.0f} kWh, "
        f"note: {s_one.notes}")
    night = (m_ginc == 0)
    say(f"   ore senza sole: {int(night.sum())}; P DC e P AC in quelle ore: {m_pdc[night].max():.3f} W, {m_pac[night].max():.3f} W")
    say(f"   ore con POA > 0 e P DC = 0 (soglia 1 W/m2 di power_at_25): {int(((m_ginc > 0) & (m_pdc == 0)).sum())}, "
        f"irradiazione persa {m_ginc[(m_ginc > 0) & (m_pdc == 0)].sum() / 1000:.4f} kWh/m2")
    OUT.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    print(f"\nscritto {OUT}")


if __name__ == "__main__":
    main()
