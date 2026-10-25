"""Study 18, part B.2: Meridiana against PVGIS 5.3 (PVcalc) at Rho, 45.5226 N 9.0300 E, 150 m: one plane at
15 degrees facing South, 74.1 kWp as 188 modules of 394.15 W (the generic module of the project, typical
TOPCon values scaled), free-standing (Meridiana's thermal case "open").

Meridiana runs on the PVGIS typical year already in Daniel's cache (tmy_45.5226_9.0300.json, SARAH3 + ERA5,
2005-2023, fetched 21/10/2026) and on the cached horizon profile; the cache folder is copied to a scratch
folder first and never written. PVGIS is asked through its API (re.jrc.ec.europa.eu, no key, GET only):
PVcalc with the suggested 14 % of system losses, with the loss figure Meridiana derives from its own chain
(system.pvgis_loss), with 0 % (the bare model), each with and without the DEM horizon; and MRcalc for the
long-term monthly means of the horizontal irradiation and the temperature, to see how far the typical
year sits from the 19-year average PVcalc works on. The raw answers are kept in the scratch folder.

What is compared: the yearly and monthly energy at parity of losses; the irradiation on the plane (PVGIS's
H(i) against Meridiana's POA, before and after the horizon); PVGIS's own loss figures (l_aoi, l_spec, l_tg)
against Meridiana's chain steps; and a PVGIS-like module model (Martin and Ruiz IAM, Faiman temperature,
Huld power, pvlib's functions) fed with Meridiana's plane irradiance, to tell the module model's share of
the gap from the transposition's. The results go to confronto_pvgis-risultati.txt beside this script.

Run from the repository root (STUDIO18_SCRATCH names the scratch folder, else the system temp):
    PYTHONPATH=src QT_QPA_PLATFORM=offscreen python docs/studio/18-prove/confronto_pvgis.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))

import pvlib  # noqa: E402
import requests  # noqa: E402

from meridiana.energy import meteo, system  # noqa: E402
from meridiana.energy.components import InverterSpec, ModuleSpec  # noqa: E402
from meridiana.energy.simulate import ArraySpec, Losses, simulate  # noqa: E402

OUT = HERE / "confronto_pvgis-risultati.txt"
LAT, LON, ELEV = 45.5226, 9.03, 150.0
TILT, AZIMUTH_CEI = 15.0, 0.0
N_MODULES, P_KWP = 188, 74.1
PVGIS = "https://re.jrc.ec.europa.eu/api/v5_3/"
USER_AGENT = "Meridiana study 18 (PV design; https://github.com/daniel-g-carrasco/meridiana)"
CACHE_SRC = Path(os.environ.get("LOCALAPPDATA", "")) / "Meridiana" / "cache"
SCRATCH = Path(os.environ.get("STUDIO18_SCRATCH") or Path(tempfile.gettempdir()) / "meridiana-studio18")
MONTHS = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
LINES: list[str] = []


def say(text: str = "") -> None:
    print(text)
    LINES.append(text)


def pvgis_get(tool: str, params: dict) -> dict:
    """One GET to PVGIS 5.3, the JSON kept in the scratch folder (re-read from there when already asked)."""
    name = tool + "_" + "_".join(f"{k}-{v}" for k, v in params.items()) + ".json"
    path = SCRATCH / "pvgis-answers" / name
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    t0 = time.perf_counter()
    for attempt in range(4):                   # the service drops a connection now and then: ask again
        try:
            r = requests.get(PVGIS + tool, params={**params, "outputformat": "json"}, timeout=90,
                             headers={"User-Agent": USER_AGENT})
            r.raise_for_status()
            break
        except requests.RequestException as error:
            if attempt == 3:
                raise
            say(f"   PVGIS {tool}: {type(error).__name__}, nuovo tentativo fra {3 * (attempt + 1)} s")
            time.sleep(3 * (attempt + 1))
    say(f"   PVGIS {tool} {params}: {r.status_code} in {time.perf_counter() - t0:.1f} s")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(r.text, encoding="utf-8")
    time.sleep(0.5)
    return r.json()


def pvcalc(loss: float, usehorizon: int, tech: str = "crystSi") -> dict:
    """PVcalc totals and monthly values for the plane of this study."""
    raw = pvgis_get("PVcalc", {"lat": LAT, "lon": LON, "peakpower": P_KWP, "loss": loss, "angle": TILT,
                               "aspect": AZIMUTH_CEI, "mountingplace": "free", "pvtechchoice": tech,
                               "usehorizon": usehorizon})
    out = raw["outputs"]
    tot = out["totals"]["fixed"]
    return {"E_y": float(tot["E_y"]), "H_y": float(tot["H(i)_y"]), "SD_y": float(tot["SD_y"]),
            "l_aoi": float(tot["l_aoi"]), "l_spec": float(tot["l_spec"]), "l_tg": float(tot["l_tg"]),
            "l_total": float(tot["l_total"]),
            "E_m": [float(x["E_m"]) for x in out["monthly"]["fixed"]],
            "H_m": [float(x["H(i)_m"]) for x in out["monthly"]["fixed"]],
            "db": raw["inputs"]["meteo_data"]["radiation_db"], "years": (raw["inputs"]["meteo_data"]["year_min"],
                                                                         raw["inputs"]["meteo_data"]["year_max"]),
            "horizon_db": raw["inputs"]["meteo_data"].get("horizon_db")}


def chain_of(sim) -> dict:
    return {c.key: c for c in sim.chain}


def main() -> None:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    cache = SCRATCH / "cache"
    shutil.copytree(CACHE_SRC / "pvgis", cache / "pvgis", dirs_exist_ok=True)
    m = meteo.typical_year(LAT, LON, cache)
    hor = meteo.horizon(LAT, LON, cache)
    d = m.data
    say("Confronto Meridiana / PVGIS 5.3 PVcalc a Rho (45.5226, 9.0300), falda 15 gradi verso Sud, 74,1 kWp")
    say(f"anno tipo in cache: {m.source.label}, scaricato il {m.fetched}, quota {m.elevation} m, offset del sole "
        f"{m.time_offset_h} h; GHI {d.ghi.sum() / 1000:.1f} kWh/m2, DHI {d.dhi.sum() / 1000:.1f}, DNI {d.dni.sum() / 1000:.1f}, "
        f"T media {d.temp_air.mean():.2f} °C, vento medio {d.wind_speed.mean():.2f} m/s")
    say(f"orizzonte in cache: {hor.source.label}; altezza da {hor.elevation.min():.1f} a {hor.elevation.max():.1f} gradi "
        f"({len(hor.azimuth)} punti); cielo visto dal piano (fattore diffuso) {hor.diffuse_factor(TILT, 180.0):.4f}")
    module = ModuleSpec.from_record({"power_kw": P_KWP / N_MODULES, "length": 1.762, "width": 1.134})
    array = ArraySpec("s1", "Falda", TILT, AZIMUTH_CEI, N_MODULES, module, thermal="open")
    p_stc = array.p_stc
    inverter = InverterSpec.sized_for(p_stc)
    losses = Losses()
    say(f"modulo: {module.source.label}; {module.pmax:.2f} W, gamma {module.gamma_pmax} %/K, efficienza {100 * module.efficiency:.2f} %")
    say(f"inverter: {inverter.source.label}: {inverter.pac_total / 1000:.1f} kW, eta {100 * inverter.eta:.1f} %")
    loss_mer = system.pvgis_loss(losses, inverter.eta)
    say(f"perdite di Meridiana nel formato di PVGIS (system.pvgis_loss): {loss_mer} %  "
        f"(soiling {losses.soiling}, LID 1.0, mismatch {losses.mismatch}, cavi DC {losses.dc_wiring}/2, inverter "
        f"{100 * (1 - inverter.eta):.0f}, cavi AC {losses.ac_wiring}/2, combinati in prodotto)")
    say()

    # ---- Meridiana
    say("1. Meridiana sull'anno tipo PVGIS")
    runs = {
        "predefinita, con orizzonte": simulate(m, [array], inverter, losses, hor),
        "predefinita, senza orizzonte": simulate(m, [array], inverter, losses, None),
        "perdite a zero, con orizzonte": simulate(m, [array], inverter, Losses(soiling=0, lid=0.0, mismatch=0, dc_wiring=0,
                                                                                ac_wiring=0), hor),
    }
    for name, s in runs.items():
        c = chain_of(s)
        say(f"   {name:32} E_AC {s.energy_kwh:9.0f} kWh, {s.specific_yield:7.1f} kWh/kWp, PR {100 * s.pr:5.2f} %, "
            f"POA {c['poa'].value:7.1f} kWh/m2, orizzonte {c['far'].change:+.2f} %, IAM {c['iam'].change:+.2f} %, "
            f"livello {c['irradiance_level'].change:+.2f} %, temperatura {c['temperature'].change:+.2f} %, "
            f"inverter {c['inverter'].change:+.2f} %, taglio {c['clipping'].change:+.2f} %")
    mer = runs["predefinita, con orizzonte"]
    mer_no = runs["predefinita, senza orizzonte"]
    mer_clean = runs["perdite a zero, con orizzonte"]
    say()

    # ---- PVGIS
    say("2. PVGIS 5.3 PVcalc (risposte grezze nella cartella di lavoro)")
    pv14 = pvcalc(14.0, 1)
    pvL = pvcalc(loss_mer, 1)
    pvL_no = pvcalc(loss_mer, 0)
    pv0 = pvcalc(0.0, 1)
    pv0_no = pvcalc(0.0, 0)
    pv25 = pvcalc(loss_mer, 1, "crystSi2025")             # PVGIS's coefficients for recent modules (2025)
    say(f"   base dati {pv14['db']} {pv14['years'][0]}-{pv14['years'][1]}, orizzonte {pv14['horizon_db']}")
    for name, p in (("perdite 14 %, con orizzonte", pv14), (f"perdite {loss_mer} %, con orizzonte", pvL),
                    (f"perdite {loss_mer} %, senza orizzonte", pvL_no), ("perdite 0 %, con orizzonte", pv0),
                    ("perdite 0 %, senza orizzonte", pv0_no), (f"perdite {loss_mer} %, crystSi2025", pv25)):
        say(f"   {name:34} E_y {p['E_y']:9.0f} kWh ({p['E_y'] / P_KWP:7.1f} kWh/kWp, SD {p['SD_y']:.0f}), H(i)_y {p['H_y']:7.1f} kWh/m2, "
            f"l_aoi {p['l_aoi']:+.2f} %, l_spec {p['l_spec']:+.2f} %, l_tg {p['l_tg']:+.2f} %, l_total {p['l_total']:+.2f} %")
    say()

    # ---- the long-term means against the typical year
    say("3. L'anno tipo contro la media pluriennale di PVGIS (MRcalc, irradiazione orizzontale e temperatura)")
    mr = pvgis_get("MRcalc", {"lat": LAT, "lon": LON, "horirrad": 1, "avtemp": 1})
    rows = mr["outputs"]["monthly"]
    years = sorted({int(r["year"]) for r in rows})
    hh = np.zeros(12)
    tt = np.zeros(12)
    for r in rows:
        hh[int(r["month"]) - 1] += float(r["H(h)_m"]) / len(years)
        tt[int(r["month"]) - 1] += float(r["T2m"]) / len(years)
    tmy_ghi = d.ghi.groupby(d.index.month).sum().to_numpy() / 1000.0
    tmy_t = d.temp_air.groupby(d.index.month).mean().to_numpy()
    say(f"   anni {years[0]}-{years[-1]} ({len(years)}); GHI media {hh.sum():.1f} kWh/m2 contro anno tipo {tmy_ghi.sum():.1f} "
        f"({100 * (tmy_ghi.sum() / hh.sum() - 1):+.2f} %); T media {tt.mean():.2f} contro {tmy_t.mean():.2f} °C")
    say("   mese   GHI media  GHI tipo   scarto    T media  T tipo")
    for k in range(12):
        say(f"   {MONTHS[k]:5} {hh[k]:9.1f} {tmy_ghi[k]:9.1f} {100 * (tmy_ghi[k] / hh[k] - 1):+8.2f} %  {tt[k]:7.2f} {tmy_t[k]:7.2f}")
    say()

    # ---- the comparison
    say("4. Produzione annua e mensile")
    say(f"   Meridiana predefinita {mer.energy_kwh:.0f} kWh ({mer.specific_yield:.1f} kWh/kWp)")
    say(f"   PVGIS perdite 14 %:   {pv14['E_y']:.0f} kWh ({pv14['E_y'] / P_KWP:.1f} kWh/kWp): Meridiana {100 * (mer.energy_kwh / pv14['E_y'] - 1):+.2f} %")
    say(f"   PVGIS perdite {loss_mer} %:  {pvL['E_y']:.0f} kWh ({pvL['E_y'] / P_KWP:.1f} kWh/kWp): Meridiana {100 * (mer.energy_kwh / pvL['E_y'] - 1):+.2f} %  (parita di perdite di sistema)")
    say(f"   PVGIS crystSi2025, {loss_mer} %: {pv25['E_y']:.0f} kWh ({pv25['E_y'] / P_KWP:.1f} kWh/kWp, l_tg {pv25['l_tg']:+.2f} %): "
        f"Meridiana {100 * (mer.energy_kwh / pv25['E_y'] - 1):+.2f} %  (moduli recenti)")
    say(f"   senza orizzonte: Meridiana {mer_no.energy_kwh:.0f} kWh contro PVGIS {pvL_no['E_y']:.0f} kWh: {100 * (mer_no.energy_kwh / pvL_no['E_y'] - 1):+.2f} %")
    say("   mese   PVGIS E_m(L)  Meridiana E_AC   scarto     PVGIS H(i)_m  Meridiana POA   scarto")
    e_m = mer.monthly.e_ac.to_numpy()
    poa_m = mer_no.monthly.poa.to_numpy()
    for k in range(12):
        say(f"   {MONTHS[k]:5} {pvL['E_m'][k]:11.0f} {e_m[k]:13.0f} {100 * (e_m[k] / pvL['E_m'][k] - 1):+9.2f} %  "
            f"{pvL_no['H_m'][k]:11.1f} {poa_m[k]:13.1f} {100 * (poa_m[k] / pvL_no['H_m'][k] - 1):+9.2f} %")
    say()
    say("5. Irradiazione sul piano e orizzonte")
    c = chain_of(mer)
    far_mer = c["far"].change
    far_pv = 100 * (pvL["H_y"] / pvL_no["H_y"] - 1)
    say(f"   POA prima dell'orizzonte: Meridiana {c['poa'].value:.1f} kWh/m2 (Perez), PVGIS H(i)_y senza orizzonte {pvL_no['H_y']:.1f} (Muneer): "
        f"{100 * (c['poa'].value / pvL_no['H_y'] - 1):+.2f} %")
    say(f"   orizzonte: Meridiana {far_mer:+.2f} % sull'irradiazione (diretto + circumsolare tolti sotto la linea, "
        f"cielo {100 * (1 - hor.diffuse_factor(TILT, 180.0)):.2f} % nascosto), PVGIS {far_pv:+.2f} % su H(i)")
    say(f"   POA dopo l'orizzonte: Meridiana {c['far'].value:.1f} contro PVGIS {pvL['H_y']:.1f}: {100 * (c['far'].value / pvL['H_y'] - 1):+.2f} %")
    say()
    say("6. Il modello del modulo: i passi di Meridiana contro le voci di PVGIS")
    tg_mer = 100 * ((1 + c["irradiance_level"].change / 100) * (1 + c["temperature"].change / 100) - 1)
    say(f"   riflessione: Meridiana IAM {c['iam'].change:+.2f} % (ASHRAE b0 0,05 + Marion sul diffuso), PVGIS l_aoi {pvL['l_aoi']:+.2f} % (Martin e Ruiz)")
    say(f"   spettro: Meridiana nessuna correzione, PVGIS l_spec {pvL['l_spec']:+.2f} %")
    say(f"   livello e temperatura: Meridiana {c['irradiance_level'].change:+.2f} % e {c['temperature'].change:+.2f} % "
        f"(insieme {tg_mer:+.2f} %; De Soto a 25 °C + gamma {module.gamma_pmax} %/K, PVsyst Uc 29), PVGIS l_tg {pvL['l_tg']:+.2f} % "
        f"(Huld, Faiman U0 26,9 U1 6,2)")
    say(f"   a monte delle perdite di sistema: Meridiana E_DC (perdite a zero, dopo IAM, soiling 0) {chain_of(mer_clean)['dc_wiring'].value:.0f} kWh "
        f"contro PVGIS a perdite 0 {pv0['E_y']:.0f} kWh: {100 * (chain_of(mer_clean)['dc_wiring'].value / pv0['E_y'] - 1):+.2f} %")
    say()

    # ---- a PVGIS-like module model on Meridiana's plane irradiance, with pvlib's functions
    say("7. Modello alla PVGIS (Martin-Ruiz, Faiman, Huld; pvlib) sulla POA di Meridiana, per separare le cause")
    t_sun = d.index + pd.Timedelta(hours=m.time_offset_h)
    sp = pvlib.solarposition.get_solarposition(t_sun, LAT, LON, altitude=m.elevation, pressure=d.pressure.to_numpy(),
                                               temperature=d.temp_air.to_numpy())
    zen, az = sp.apparent_zenith.to_numpy(), sp.azimuth.to_numpy()
    el = 90.0 - zen
    dni_extra = pvlib.irradiance.get_extra_radiation(t_sun).to_numpy()
    am = pvlib.atmosphere.get_relative_airmass(zen)
    ghi, dni, dhi = d.ghi.to_numpy(), d.dni.to_numpy(), d.dhi.to_numpy()
    aoi = pvlib.irradiance.aoi(TILT, 180.0, zen, az)
    poa = pvlib.irradiance.get_total_irradiance(TILT, 180.0, zen, az, dni, ghi, dhi, dni_extra=dni_extra, airmass=am,
                                                albedo=losses.albedo, model="perez", diffuse_components=True)
    beam, sky, ground, circ = (np.nan_to_num(np.asarray(poa[k], dtype=float))
                               for k in ("poa_direct", "poa_sky_diffuse", "poa_ground_diffuse", "poa_circumsolar"))
    blocked = (hor.at(az) > el) & (el > 0)
    beam_h = np.where(blocked, 0.0, beam + circ)           # PVGIS: only the beam is removed below the horizon
    g_h = beam_h + (sky - circ) + ground
    say(f"   POA Perez di questo calcolo {(beam + sky + ground).sum() / 1000:.1f} kWh/m2 (= Meridiana {c['poa'].value:.1f}); "
        f"con il solo diretto tolto sotto l'orizzonte {g_h.sum() / 1000:.1f}")
    iam_b = np.nan_to_num(np.asarray(pvlib.iam.martin_ruiz(aoi, a_r=0.16), dtype=float))
    iam_dif = pvlib.iam.martin_ruiz_diffuse(TILT, a_r=0.16)
    iam_sky_mr, iam_ground_mr = ((iam_dif["sky"], iam_dif["ground"]) if isinstance(iam_dif, dict) else iam_dif)
    g_eff = beam_h * iam_b + (sky - circ) * float(np.atleast_1d(iam_sky_mr)[0]) + ground * float(np.atleast_1d(iam_ground_mr)[0])
    t_mod = np.asarray(pvlib.temperature.faiman(g_h, d.temp_air.to_numpy(), d.wind_speed.to_numpy(), u0=26.9, u1=6.2), float)
    p_huld = np.clip(np.nan_to_num(np.asarray(pvlib.pvarray.huld(g_eff, t_mod, p_stc, cell_type="cSi", k_version="pvgis5"), float)), 0, None)
    e_huld = p_huld.sum() / 1000.0
    spec = 1 + pvL["l_spec"] / 100.0
    say(f"   IAM Martin-Ruiz a_r 0,16: {100 * (g_eff.sum() / g_h.sum() - 1):+.2f} % (PVGIS l_aoi {pvL['l_aoi']:+.2f} %)")
    say(f"   Huld + Faiman: E_DC {e_huld:.0f} kWh, {100 * (e_huld / (p_stc / 1000 * g_eff.sum() / 1000) - 1):+.2f} % rispetto a P_STC x G_eff "
        f"(PVGIS l_tg {pvL['l_tg']:+.2f} %); T modulo media nelle ore di sole {t_mod[g_h > 50].mean():.1f} °C")
    say(f"   con lo spettro di PVGIS ({pvL['l_spec']:+.2f} %) e perdite 0: {e_huld * spec:.0f} kWh contro PVGIS a perdite 0 "
        f"{pv0['E_y']:.0f} kWh: {100 * (e_huld * spec / pv0['E_y'] - 1):+.2f} % (resta: Muneer contro Perez, anno tipo contro media)")
    say(f"   con le perdite di Meridiana ({loss_mer} %): {e_huld * spec * (1 - loss_mer / 100):.0f} kWh contro Meridiana "
        f"{mer.energy_kwh:.0f}: il modello del modulo di Meridiana da' {100 * (mer.energy_kwh / (e_huld * spec * (1 - loss_mer / 100)) - 1):+.2f} % "
        f"rispetto a quello di PVGIS sulla stessa POA")
    say()

    # ---- the catalogue module of Daniel's project, for the sensitivity to the module
    say("8. Lo stesso confronto con il modulo del progetto di Rho (LONGi LR7-54HVH-495M, 188 moduli, 93,06 kWp)")
    from meridiana import catalog
    rec = next(r for r in catalog.load("modules") if r["model"] == "LR7-54HVH-495M")
    longi = ModuleSpec.from_record(catalog.for_project(rec))
    a2 = ArraySpec("s1", "Falda", TILT, AZIMUTH_CEI, N_MODULES, longi, thermal="open")
    inv2 = InverterSpec.sized_for(a2.p_stc)
    s2 = simulate(m, [a2], inv2, losses, hor)
    c2 = chain_of(s2)
    loss2 = system.pvgis_loss(losses, inv2.eta)
    say(f"   Meridiana {s2.energy_kwh:.0f} kWh, {s2.specific_yield:.1f} kWh/kWp, PR {100 * s2.pr:.2f} %; livello {c2['irradiance_level'].change:+.2f} %, "
        f"temperatura {c2['temperature'].change:+.2f} % (gamma {longi.gamma_pmax} %/K), LID {c2['lid'].change:+.2f} %")
    say(f"   PVGIS a perdite {loss2} % (per kWp come sopra): {pvL['E_y'] / P_KWP:.1f} kWh/kWp: Meridiana {100 * (s2.specific_yield / (pvL['E_y'] / P_KWP) - 1):+.2f} %")
    say(f"   resa a 25 °C del modello De Soto del LONGi: 200 W/m2 {100 * float(longi.power_at_25([200.0])[0]) / (0.2 * longi.pmax):.1f} %, "
        f"400 {100 * float(longi.power_at_25([400.0])[0]) / (0.4 * longi.pmax):.1f} %, 600 {100 * float(longi.power_at_25([600.0])[0]) / (0.6 * longi.pmax):.1f} %, "
        f"800 {100 * float(longi.power_at_25([800.0])[0]) / (0.8 * longi.pmax):.1f} % di quella STC; "
        f"generico: 200 {100 * float(module.power_at_25([200.0])[0]) / (0.2 * module.pmax):.1f} %, 400 {100 * float(module.power_at_25([400.0])[0]) / (0.4 * module.pmax):.1f} %, "
        f"600 {100 * float(module.power_at_25([600.0])[0]) / (0.6 * module.pmax):.1f} %, 800 {100 * float(module.power_at_25([800.0])[0]) / (0.8 * module.pmax):.1f} %")
    OUT.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    print(f"\nscritto {OUT}")


if __name__ == "__main__":
    main()
