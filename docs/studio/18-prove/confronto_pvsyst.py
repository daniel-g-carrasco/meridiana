"""Meridiana against PVsyst on public cases (study 18, section B, part 3).

For each case the PVsyst project is rebuilt with the core API of Meridiana (ArraySpec, ModuleSpec,
InverterSpec, Losses, Horizon, simulate) and run on three kinds of weather:

- "pvgis": the PVGIS typical year of the site, as the application fetches it (PVGIS 5.3, SARAH-3);
  for the one report that used the PVGIS TMY itself, also PVGIS 5.2 (SARAH-2), the database the
  report most likely had;
- "met": the hourly weather file (.MET) of the PVsyst project itself, when the public repository holds
  it: then the two programs see the same irradiance and temperature hour by hour, and what remains is
  the difference of the models;
- "scaled": the PVGIS typical year scaled month by month (global, diffuse, temperature) to the monthly
  table printed in the report, for the reports made with Meteonorm, whose hourly file is not public.

The PVsyst figures come from the loss diagram and the monthly table of each report (casi.json of the
local folder of public reports, or the .VC0 of the sample project plus the numbers of its PDF typed
below with their page). Inputs that PVsyst prints at operating conditions (Pmpp at 50 degrees) give the
temperature coefficient the one-diode model of PVsyst used; the module's electrical data come from the
CEC list of Meridiana's catalogue when the model is there, else from a record typed from the datasheet
class of the module, and the script says which.

The inverter is compared twice: with the weighted efficiency of the catalogue (or of the closest model,
said so), and with the efficiency tuned so that Meridiana's yearly inverter loss equals PVsyst's, which
isolates the other steps of the chain.

Usage (from the repository root, with the project's virtual environment):

    PYTHONPATH=src QT_QPA_PLATFORM=offscreen python docs/studio/18-prove/confronto_pvsyst.py
        [--cache DIR] [--samples DIR] [--cases a,b,c] [--out FILE]

The weather cache (DIR/pvgis) is written by the script; the samples folder is the local one with the
public PVsyst reports (pvsyst-report-pubblici/casi.json) and the sample projects (pvsyst-campioni/).
The results go to confronto_pvsyst-risultati.txt next to the script.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import date, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from meridiana import catalog  # noqa: E402
from meridiana.energy import meteo as meteo_mod  # noqa: E402
from meridiana.energy.components import InverterSpec, ModuleSpec  # noqa: E402
from meridiana.energy.meteo import COLUMNS, Horizon, Meteo  # noqa: E402
from meridiana.energy.pedigree import Source  # noqa: E402
from meridiana.energy.simulate import ArraySpec, Losses, simulate  # noqa: E402
from meridiana.pvsyst import project as pvproject  # noqa: E402

PVGIS_52_URL = "https://re.jrc.ec.europa.eu/api/v5_2/"
MONTHS = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]

# Meridiana's chain step -> PVsyst's loss-diagram key (casi.json); the order is Meridiana's
STEP_MAP = [("poa", "transposition", "trasposizione sul piano"), ("far", "far_shading", "orizzonte (ombre lontane)"),
            ("near", "near_shading", "ombre vicine, irraggiamento"), ("iam", "iam", "riflessione sul vetro (IAM)"),
            ("soiling", "soiling", "sporcamento"), ("irradiance_level", "irradiance_level", "livello di irraggiamento"),
            ("temperature", "temperature", "temperatura"), ("quality", "module_quality", "qualita' del modulo"),
            ("lid", "lid", "LID"), ("mismatch", "mismatch", "mismatch"),
            ("electrical", "electrical_shading", "effetto elettrico delle ombre"), ("dc_wiring", "ohmic", "cavi DC"),
            ("inverter", "inverter_efficiency", "inverter, efficienza"),
            ("clipping", "inverter_over_power", "inverter, oltre la potenza nominale"),
            ("ac_wiring", "ac_ohmic", "cavi AC"), ("unavailability", "unavailability", "indisponibilita'")]
NODE_KEYS = ["globhor", "globinc", "globeff", "e_nom", "e_mpp", "e_inv", "e_grid"]
NODE_LABELS = {"globhor": "GlobHor kWh/m2", "globinc": "GlobInc kWh/m2", "globeff": "GlobEff kWh/m2",
               "e_nom": "EArrNom MWh", "e_mpp": "EArrMPP MWh", "e_inv": "EOutInv MWh", "e_grid": "E_Grid MWh"}
# PVsyst steps that have no counterpart in Meridiana's chain
EXTRA_LABELS = {"inverter_max_current": "inverter, corrente massima", "inverter_over_voltage": "inverter, sovratensione",
                "inverter_power_threshold": "inverter, soglia di potenza",
                "inverter_voltage_threshold": "inverter, soglia di tensione", "night_consumption": "consumo notturno",
                "auxiliaries": "ausiliari", "mv_transformer": "trasformatore MT", "mv_line": "linea MT",
                "hv_line": "linea AT", "grid_limitation": "limite di immissione", "degradation": "degrado (anno n)",
                "spectral": "correzione spettrale", "mismatch_orientation": "mismatch di orientamento",
                "mismatch_rear": "mismatch lato posteriore", "optimizer": "ottimizzatori"}


# ----------------------------------------------------------------------------------------------------
# the cases
# ----------------------------------------------------------------------------------------------------

@dataclass
class Case:
    key: str
    title: str
    pvsyst_version: str
    source: str                      # where the PVsyst numbers come from
    lat: float
    lon: float
    alt: float
    tz: float                        # hours from UTC, standard time
    weather: dict                    # {"kind": "pvgis"|"met"|"scaled", ...}
    arrays: list                     # dicts: tilt, azimuth, modules, rows, pitch, slant, stack, upright, thermal
    module: dict                     # {"catalogue": model} or {"record": {...}}; "gamma": the report's; "cells", "area"
    inverter: dict                   # pac_total (W), eta (catalogue or proxy), label, note
    losses: dict                     # Losses kwargs
    iam_profile: list | None = None  # [(angle, iam)] printed by PVsyst
    horizon: list | None = None      # [(azimuth from South + West, height)] printed by PVsyst
    ref: dict = field(default_factory=dict)      # PVsyst nodes, steps, extra steps, monthly table
    notes: list = field(default_factory=list)


def _diagram(case_json: dict) -> tuple[dict, dict]:
    """The loss diagram of a casi.json case: {pvsyst key: %} for the steps, and the extra ones."""
    known = {p for _m, p, _l in STEP_MAP}
    steps, extra = {}, {}
    for item in case_json["loss_diagram"]:
        if item.get("pct") is None:
            continue
        if item["key"] in known:
            steps[item["key"]] = float(item["pct"])
        elif item["key"] in EXTRA_LABELS:
            extra[item["key"]] = float(item["pct"])
    return steps, extra


def _ref_from_json(c: dict) -> dict:
    o = c["outputs"]
    steps, extra = _diagram(c)
    monthly = {k: [] for k in ("ghi", "dhi", "t", "globinc", "globeff", "e_grid")}
    unit = {"kWh": 1.0, "MWh": 1000.0, "GWh": 1e6}[c["monthly"]["units"]["E_Grid"]]
    for row in c["monthly"]["rows"]:
        if row["month"] == "Year":
            continue
        monthly["ghi"].append(row["GlobHor"])
        monthly["dhi"].append(row["DiffHor"])
        monthly["t"].append(row["T_Amb"])
        monthly["globinc"].append(row["GlobInc"])
        monthly["globeff"].append(row["GlobEff"])
        monthly["e_grid"].append(row["E_Grid"] * unit)
    return {"globhor": o["globhor_kwh_m2"], "globinc": o["globinc_kwh_m2"], "globeff": o["globeff_kwh_m2"],
            "e_nom": o["array_nominal_mwh"] * 1000.0, "e_mpp": o["array_mpp_mwh"] * 1000.0,
            "e_inv": o["inverter_output_mwh"] * 1000.0, "e_grid": o["e_grid_mwh"] * 1000.0,
            "pr": o["pr_pct"], "yield": o["specific_yield_kwh_kwp"], "steps": steps, "extra": extra,
            "monthly": monthly, "p_stc_kw": c["system"]["p_nom_kwp"]}


def _ref_from_variant(vc: Path, e_nom: float, e_mpp: float, e_inv: float, e_grid: float, pr: float,
                      yield_: float, steps: dict, extra: dict, p_stc_kw: float) -> dict:
    """The monthly results of a .VC0 (summed from its hourly records) plus the loss diagram of the PDF."""
    v = pvproject.read_variant(vc)
    r = v.results
    monthly = {"ghi": r["GlobHor"], "dhi": r["DiffHor"], "t": r["T_Amb"], "globinc": r["GlobInc"],
               "globeff": r["GlobEff"], "e_grid": r["E_Grid"]}
    return {"globhor": sum(r["GlobHor"]), "globinc": sum(r["GlobInc"]), "globeff": sum(r["GlobEff"]),
            "e_nom": e_nom, "e_mpp": e_mpp, "e_inv": e_inv, "e_grid": e_grid, "pr": pr, "yield": yield_,
            "steps": steps, "extra": extra, "monthly": monthly, "p_stc_kw": p_stc_kw}


def build_cases(samples: Path) -> dict:
    cases: dict = {}
    reports = samples / "pvsyst-report-pubblici"
    campioni = samples / "pvsyst-campioni"
    by_id = {}
    if (reports / "casi.json").exists():
        with open(reports / "casi.json", encoding="utf-8") as fh:
            by_id = {c["id"]: c for c in json.load(fh)}

    # A. PEAKI, Greece: PVsyst 7.4.8 on the PVGIS TMY, fixed 25 deg south, no shading
    if "gr-peaki-fixed-commercial" in by_id:
        c = by_id["gr-peaki-fixed-commercial"]
        cases["peaki"] = Case(
            key="peaki", title="PEAKI (Neochoropoulo, Grecia), 396,9 kWp fisso 25/0, senza ombre",
            pvsyst_version=c["pvsyst_version"], source=c["source"]["url"] + " (casi.json)",
            lat=39.62, lon=20.85, alt=475.0, tz=2.0,
            weather={"kind": "pvgis", "report_db": "PVGIS api TMY (versione non stampata; 5.2 o 5.3)"},
            arrays=[{"tilt": 25.0, "azimuth": 0.0, "modules": 735, "thermal": "semi"}],
            # Luxor LX-540M/182-144+ is not in the catalogue: the CEC record of a module of the same
            # class (144 half cells of 182 mm, 540 W) stands in; the temperature coefficient is the one
            # PVsyst's model shows (Pmpp 361 kWp at 50 degrees for 396.9 kWp: -0.362 %/K, report p. 3)
            module={"catalogue": "LR5-72HPH-540M", "proxy_for": "Luxor LX-540M/182-144+", "gamma": -0.362,
                    "cells": 144, "area": 1900.0 / 735},
            inverter={"pac_total": 400000.0, "eta": 0.984, "label": "4 x Huawei SUN2000-100KTL-M1 (catalogo: M2, eta Euro 98,4 %)"},
            losses={"soiling": 0.0, "quality": -0.75, "lid": 0.0, "mismatch": 2.0, "dc_wiring": 1.5, "ac_wiring": 0.0,
                    "unavailability": 0.0},
            iam_profile=c["losses"]["iam"]["profile"], ref=_ref_from_json(c),
            notes=["Il rapporto stampa la qualita' del modulo -0,8 % sulla pagina dei parametri e +0,75 % nel diagramma: "
                   "il valore in uso e' -0,75 % (lo dicono i file .VC0 dei campioni, chiave PQualityModP).",
                   "49 stringhe su 40 ingressi MPPT al 10 %: la perdita di clipping di PVsyst (-1,94 %) nasce dagli "
                   "ingressi con due stringhe; Meridiana somma la potenza DC e non la vede."])

    # B. IIT Kanpur, India: PVsyst 7.4.0, 5.04 kWp, ASHRAE IAM, the .MET is public (sample sabya169)
    folder = campioni / "github-sabya169-PVsyst"
    if folder.exists():
        pdf = "New.VC0-Report.pdf"
        cases["kanpur"] = Case(
            key="kanpur", title="IIT Kanpur (India), 5,04 kWp fisso 24/0, senza ombre, meteo .MET del progetto",
            pvsyst_version="7.4.0", source=f"campione github-sabya169-PVsyst: .VC0 (risultati mensili) e {pdf} p. 3-5",
            lat=26.5066, lon=80.2276, alt=128.0, tz=5.5,
            weather={"kind": "met", "path": folder / "IIT KANPUR - HALL 7_MN81_SYN.MET",
                     "report_db": "Meteonorm 8.1 (1996-2015), Sat=100 % - Synthetic"},
            arrays=[{"tilt": 24.0, "azimuth": 0.0, "modules": 16, "thermal": "semi"}],
            # "Generic PM318B01_315 (custom parameters)": a 96-cell back-contact module of 315 W (the
            # printed area 26.1 m2 / 16 = 1.63 m2 and 388 V / 8 = 48.5 V at 50 degrees say so); typed
            # values of that class, not in the catalogue; gamma from Pmpp 4567 W at 50 degrees: -0.375 %/K
            module={"record": {"manufacturer": "Generic", "model": "PM318B01_315 (valori tipici di un modulo "
                                                                      "back-contact da 96 celle)",
                               "pmax": 315.0, "vmp": 53.3, "imp": 5.91, "voc": 64.3, "isc": 6.27,
                               "gamma_pmax": -0.375, "beta_voc": -0.27, "alpha_isc": 0.05, "cells": 96,
                               "cells_in_series": 96, "length": 1.559, "width": 1.046},
                    "gamma": -0.375, "cells": 96, "area": 26.1 / 16},
            inverter={"pac_total": 4950.0, "eta": 0.978,
                      "label": "1 x Huawei SUN2000-4.95KTL-JPL1 (catalogo: SUN2000-5KTL-L1, eta Euro 97,8 %)"},
            losses={"soiling": 0.0, "quality": -0.75, "lid": 0.0, "mismatch": 2.0, "dc_wiring": 1.5, "ac_wiring": 0.0,
                    "unavailability": 0.0, "iam_b0": 0.05},
            iam_profile=None,
            ref=_ref_from_variant(folder / "5KW SOLAR MODEL_Project.VC0", e_nom=8327.0, e_mpp=7243.0, e_inv=6986.0,
                                  e_grid=6985.8, pr=81.87, yield_=1386.0,
                                  steps={"transposition": 6.4, "iam": -2.59, "irradiance_level": -0.85,
                                         "temperature": -10.26, "module_quality": 0.75, "mismatch": -2.00,
                                         "ohmic": -0.99, "inverter_efficiency": -3.11, "inverter_over_power": 0.0},
                                  extra={"night_consumption": -0.45}, p_stc_kw=5.04),
            notes=["Il modulo e' 'custom': i suoi parametri non sono pubblici; Vmp, Imp, Voc, Isc sono valori tipici "
                   "della classe, il coefficiente di temperatura viene dal rapporto."])

    # C. Al Marj, Egypt: PVsyst 7.4.6, 61.6 kWp, Fresnel AR IAM, the .MET is public (sample youefkh05)
    folder = campioni / "github-youefkh05-PV_plant_model"
    if folder.exists():
        cases["almarj"] = Case(
            key="almarj", title="Al Marj (Egitto), 61,6 kWp fisso 28/-3, senza ombre, meteo .MET del progetto",
            pvsyst_version="7.4.6", source="campione github-youefkh05-PV_plant_model: .VC0 e Results_Report.pdf p. 3-5",
            lat=30.1579, lon=31.3319, alt=33.0, tz=2.0,
            weather={"kind": "met", "path": folder / "Al Marj_MN81_SYN.MET",
                     "report_db": "Meteonorm 8.1 (1991-2010) - Synthetic"},
            arrays=[{"tilt": 28.0, "azimuth": -3.0, "modules": 114, "thermal": "semi"}],
            # Jinko JKM540M-72HL4-TV is in the CEC list; gamma from Pmpp 56.2 kWp at 50 degrees: -0.348 %/K
            module={"catalogue": "JKM540M-72HL4-TV", "gamma": -0.348, "cells": 144, "area": 294.0 / 114},
            inverter={"pac_total": 60000.0, "eta": 0.980,
                      "label": "1,5 x Huawei SUN2000-40KTL-M3 (6 MPPT al 25 %); catalogo: SUN2000-50KTL-M3, eta Euro 98,0 %"},
            losses={"soiling": 0.0, "quality": -0.75, "lid": 0.0, "mismatch": 2.0, "dc_wiring": 1.5, "ac_wiring": 0.0,
                    "unavailability": 0.0},
            iam_profile=[(0, 1.0), (30, 0.999), (50, 0.987), (60, 0.962), (70, 0.892), (75, 0.816), (80, 0.681),
                         (85, 0.440), (90, 0.0)],
            ref=_ref_from_variant(folder / "Grid_Connected_Yousef_Khaled_Project.VC0", e_nom=124087.0,
                                  e_mpp=109544.0, e_inv=107727.0, e_grid=107727.0, pr=85.13, yield_=1750.0,
                                  steps={"transposition": 8.8, "iam": -1.96, "irradiance_level": -0.44,
                                         "temperature": -9.20, "module_quality": 0.75, "mismatch": -2.00,
                                         "ohmic": -1.09, "inverter_efficiency": -1.63, "inverter_over_power": 0.0},
                                  extra={"night_consumption": -0.03}, p_stc_kw=61.56))

    # D. Kuwait: PVsyst 8.0.21, 92.4 kWp, user IAM profile, the .MET is public (sample IKH116)
    folder = campioni / "github-IKH116-export-zip" / "extracted"
    if folder.exists():
        cases["kuwait"] = Case(
            key="kuwait", title="Jalib ash Shuyukh (Kuwait), 92,4 kWp fisso 29/0, senza ombre, meteo .MET del progetto",
            pvsyst_version="8.0.21", source="campione github-IKH116-export-zip: .VC0 e PVsyst_Variant1_Simulation_Report.pdf p. 3-5",
            lat=29.2583, lon=47.8936, alt=37.0, tz=3.0,
            weather={"kind": "met", "path": folder / "Jal_b ash Shuy_kh_MN82_SYN.MET",
                     "report_db": "Meteonorm 8.2 (1998-2000), Sat=100 % - Synthetic"},
            arrays=[{"tilt": 29.0, "azimuth": 0.0, "modules": 168, "thermal": "semi"}],
            # LONGi LR5-72HPH-550M is in the CEC list; gamma from Pmpp 84.7 kWp at 50 degrees: -0.333 %/K
            module={"catalogue": "LR5-72HPH-550M", "gamma": -0.333, "cells": 144, "area": 429.0 / 168},
            inverter={"pac_total": 100000.0, "eta": 0.978,
                      "label": "2 x SMA Sunny Tripower STP50-40 Core1; non in catalogo, eta Euro 97,8 % dal datasheet (a memoria)"},
            losses={"soiling": 0.0, "quality": -0.25, "lid": 0.0, "mismatch": 2.0, "dc_wiring": 1.5, "ac_wiring": 0.0,
                    "unavailability": 0.0},
            iam_profile=[(0, 1.0), (25, 1.0), (45, 0.995), (60, 0.962), (65, 0.936), (70, 0.903), (75, 0.851),
                         (80, 0.754), (90, 0.0)],
            ref=_ref_from_variant(folder / "Project2.VC0", e_nom=193860.0, e_mpp=168340.0, e_inv=163670.0,
                                  e_grid=163670.0, pr=83.35, yield_=1771.0,
                                  steps={"transposition": 9.5, "iam": -1.5, "irradiance_level": 0.4,
                                         "temperature": -10.9, "module_quality": 0.2, "mismatch": -2.0,
                                         "ohmic": -1.1, "inverter_efficiency": -2.8, "inverter_over_power": 0.0},
                                  extra={}, p_stc_kw=92.4),
            notes=["PVsyst 8 stampa le percentuali con un decimale: il confronto per passo vale a 0,05 punti."])

    # E. Montescaglioso, Italy: PVsyst 7.2.11, 5.64 MWp in 20 rows 20 deg at 7.5 m, horizon, Meteonorm
    if "it-montescaglioso-fixed" in by_id:
        c = by_id["it-montescaglioso-fixed"]
        cases["montescaglioso"] = Case(
            key="montescaglioso", title="Montescaglioso (MT), 5643 kWp, 20 file 20/0 passo 7,5 m, orizzonte, Meteonorm 8.0",
            pvsyst_version=c["pvsyst_version"], source=c["source"]["url"] + " (casi.json, pagine 2-10)",
            lat=40.52, lon=16.66, alt=57.0, tz=1.0,
            weather={"kind": "scaled", "report_db": c["weather"]["source"]},
            arrays=[{"tilt": 20.0, "azimuth": 0.0, "modules": 8550, "thermal": "open", "rows": 20, "pitch": 7.5,
                     "slant": 4.79, "stack": 2, "upright": True, "stand_off": 0.8}],
            # Risen RSM132-8-660BMDG is in the CEC list; gamma from Pmpp 5166 kWp at 50 degrees: -0.338 %/K
            module={"catalogue": "RSM132-8-660BMDG", "gamma": -0.338, "cells": 132, "area": 26559.0 / 8550},
            inverter={"pac_total": 5600000.0, "eta": 0.984,
                      "label": "28 x Huawei SUN2000-215KTL-H3 (200 kW); non in catalogo, eta della famiglia 98,4 %"},
            losses={"soiling": 2.0, "quality": -0.5, "lid": 1.6, "mismatch": 1.1, "dc_wiring": 1.0, "ac_wiring": 1.0,
                    "unavailability": 0.0},
            iam_profile=c["losses"]["iam"]["profile"], horizon=c["shading"]["horizon_profile"], ref=_ref_from_json(c),
            notes=["Il rapporto stampa l'energia annua arrotondata a 8 GWh: si usano la tabella mensile e il diagramma "
                   "(8065 MWh).", "Ombre vicine 'lineari' in PVsyst: nessun effetto elettrico; Meridiana lo calcola "
                   "sempre per le file e lo mostra come passo a parte."])

    # F. NEOM, Saudi Arabia: PVsyst 7.4.0, 5 MWp fixed 30 deg, hot climate, Meteonorm 8.1
    if "sa-neom-fixed" in by_id:
        c = by_id["sa-neom-fixed"]
        cases["neom"] = Case(
            key="neom", title="NEOM (Arabia Saudita), 4999 kWp fisso 30/0, senza ombre, clima caldo, Meteonorm 8.1",
            pvsyst_version=c["pvsyst_version"], source=c["source"]["url"] + " (casi.json)",
            lat=28.33, lon=34.95, alt=147.0, tz=3.0,
            weather={"kind": "scaled", "report_db": c["weather"]["source"]},
            arrays=[{"tilt": 30.0, "azimuth": 0.0, "modules": 10203, "thermal": "semi"}],
            # "Generic LR5-66HPH-490M G2": the CEC record of LONGi LR5-66HBD-490M (same cells, bifacial
            # glass) stands in; gamma from Pmpp 4581 kWp at 50 degrees: -0.335 %/K
            module={"catalogue": "LR5-66HBD-490M", "proxy_for": "Generic LR5-66HPH-490M G2", "gamma": -0.335,
                    "cells": 132, "area": 24228.0 / 10203},
            inverter={"pac_total": 4375000.0, "eta": 0.980,
                      "label": "5 x Generic PVS800-57-0875kW-B (ABB centrale); non in catalogo, eta Euro 98,0 % ipotizzato"},
            losses={"soiling": 0.0, "quality": -0.75, "lid": 0.0, "mismatch": 2.2, "dc_wiring": 1.5, "ac_wiring": 0.0,
                    "unavailability": 0.0},
            iam_profile=c["losses"]["iam"]["profile"], ref=_ref_from_json(c))

    # G. LaFact, Spain: PVsyst 7.3.4 DEMO, 590 kWp on two roof planes, 10/+86 and 20/180 (north)
    if "es-lafact-two-orientations-roof" in by_id:
        c = by_id["es-lafact-two-orientations-roof"]
        cases["lafact"] = Case(
            key="lafact", title="LaFact (Terrassa, Spagna), 590 kWp su due falde 10/+86 e 20/180, senza ombre, Meteonorm 8.1",
            pvsyst_version=c["pvsyst_version"], source=c["source"]["url"] + " (casi.json)",
            lat=41.58, lon=2.01, alt=328.0, tz=1.0,
            weather={"kind": "scaled", "report_db": c["weather"]["source"]},
            arrays=[{"tilt": 10.0, "azimuth": 86.0, "modules": 612, "thermal": "semi"},
                    {"tilt": 20.0, "azimuth": 180.0, "modules": 568, "thermal": "semi"}],
            # JA Solar Deep Blue 3.0 500 W (JAM66S30-500/MR) is not in the catalogue: typed values of the
            # class (132 half cells of 182 mm); gamma from Pmpp at 40 degrees (291 of 306 kWp): -0.327 %/K
            module={"record": {"manufacturer": "JA Solar", "model": "Deep Blue 3.0 500 W (valori tipici della classe)",
                               "pmax": 500.0, "vmp": 38.0, "imp": 13.16, "voc": 45.6, "isc": 13.9,
                               "gamma_pmax": -0.327, "beta_voc": -0.27, "alpha_isc": 0.045, "cells": 132,
                               "cells_in_series": 66, "length": 2.278, "width": 1.134},
                    "gamma": -0.327, "cells": 132, "area": 3048.0 / 1180},
            inverter={"pac_total": 600000.0, "eta": 0.982, "label": "6 x Fronius Tauro Eco 100-3-D (catalogo, eta Euro 98,2 %)"},
            losses={"soiling": 0.0, "quality": -0.25, "lid": 0.0, "mismatch": 2.2, "dc_wiring": 1.5, "ac_wiring": 0.0,
                    "unavailability": 0.0},
            iam_profile=c["losses"]["iam"]["profile"], ref=_ref_from_json(c),
            notes=["Il rapporto stampa la qualita' -0,3 % nei parametri e +0,25 % nel diagramma: in uso -0,25 %."])

    # H. Pelham, UK: PVsyst 7.4.5, 52.6 MWp in rows 20 deg at 8.69 m, electrical shading by strings (50 %)
    if "uk-pelham-fixed" in by_id:
        c = by_id["uk-pelham-fixed"]
        cases["pelham"] = Case(
            key="pelham", title="Pelham (Hertfordshire, UK), 52615 kWp, file 20/-2 passo 8,69 m, orizzonte, ombre per stringhe, Meteonorm 8.0",
            pvsyst_version=c["pvsyst_version"], source=c["source"]["url"] + " (casi.json)",
            lat=51.94, lon=0.12, alt=114.0, tz=0.0,
            weather={"kind": "scaled", "report_db": c["weather"]["source"]},
            arrays=[{"tilt": 20.0, "azimuth": -2.0, "modules": 95664, "thermal": "open", "rows": 1840, "pitch": 8.69,
                     "slant": 4.60, "stack": 2, "upright": True, "stand_off": 0.8}],
            # CSI CS6W-550MS is in the CEC list; gamma from Pmpp 48.20 MWp at 50 degrees: -0.336 %/K
            module={"catalogue": "CS6W-550MS", "gamma": -0.336, "cells": 144, "area": 245280.0 / 95664},
            inverter={"pac_total": 37450000.0, "eta": 0.984,
                      "label": "214 x Huawei SUN2000-175KTL-H0; non in catalogo, eta della famiglia 98,4 %"},
            losses={"soiling": 0.8, "quality": -0.5, "lid": 1.0, "mismatch": 0.6, "dc_wiring": 1.5, "ac_wiring": 1.5,
                    "unavailability": 0.0, "iam_b0": 0.05},
            iam_profile=None, horizon=c["shading"]["horizon_profile"], ref=_ref_from_json(c),
            notes=["La scena 3D ha anche terreno e siepi: il modello a file di Meridiana e' un'approssimazione.",
                   "DC/AC 1,40: PVsyst taglia -0,61 % sull'inverter."])
    return cases


# ----------------------------------------------------------------------------------------------------
# weather
# ----------------------------------------------------------------------------------------------------

def _tz(hours: float) -> timezone:
    return timezone(timedelta(hours=hours))


def pvgis_meteo(lat: float, lon: float, cache: Path, version: str = "5.3") -> Meteo:
    """The PVGIS typical year: through Meridiana's own fetch for 5.3; through pvlib for 5.2 (same form)."""
    if version == "5.3":
        return meteo_mod.typical_year(lat, lon, cache)
    path = cache / "pvgis" / f"tmy52_{lat:.4f}_{lon:.4f}.json"
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
    else:
        from pvlib.iotools import get_pvgis_tmy
        data, meta = get_pvgis_tmy(lat, lon, usehorizon=False, url=PVGIS_52_URL, timeout=90, coerce_year=1990)
        raw = {"meta": meta, "fetched": date.today().isoformat(),
               "columns": {c: [round(float(v), 3) for v in data[c].to_numpy()] for c in COLUMNS}}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(raw), encoding="utf-8")
    index = pd.date_range("1990-01-01 00:00", periods=8760, freq="h", tz="UTC")
    frame = pd.DataFrame({c: np.asarray(raw["columns"][c], dtype=float) for c in COLUMNS}, index=index)
    loc = raw["meta"]["inputs"]["location"]
    md = raw["meta"]["inputs"]["meteo_data"]
    label = f"PVGIS 5.2, typical year from {md.get('radiation_db')} + {md.get('meteo_db')}, {md.get('year_min')}-{md.get('year_max')}"
    return Meteo(frame, float(loc["latitude"]), float(loc["longitude"]), float(loc["elevation"]),
                 float(loc.get("irradiance_time_offset", 0.0)), Source("data", label, PVGIS_52_URL + "tmy"), raw["fetched"])


def met_meteo(path: Path, lat: float, lon: float, alt: float, tz: float) -> Meteo:
    """The hourly weather of a PVsyst .MET as a Meteo: the file is in the site's standard time, each value
    labelled at the start of its hour, so the sun is placed half an hour later (PVsyst's own convention
    for hourly data); the direct normal irradiance, which the file does not hold, comes from the global
    and the diffuse at that instant, as PVsyst derives it, capped at the extraterrestrial value."""
    import pvlib
    m = pvproject.read_met(path)
    ghi = np.clip(np.asarray(m["ghi"], dtype=float), 0.0, None)
    dhi = np.clip(np.asarray(m["dhi"], dtype=float), 0.0, ghi)
    local = pd.date_range("1990-01-01 00:00", periods=8760, freq="h", tz=_tz(tz))
    index = local.tz_convert("UTC")
    mid = index + pd.Timedelta(minutes=30)
    sp = pvlib.solarposition.get_solarposition(mid, lat, lon, altitude=alt)
    zen = sp.apparent_zenith.to_numpy()
    extra = pvlib.irradiance.get_extra_radiation(mid).to_numpy()
    dni = pvlib.irradiance.dni(pd.Series(ghi), pd.Series(dhi), pd.Series(zen)).to_numpy()
    dni = np.clip(np.nan_to_num(dni, nan=0.0, posinf=0.0), 0.0, extra)
    frame = pd.DataFrame({"ghi": ghi, "dni": dni, "dhi": dhi, "temp_air": np.asarray(m["t_amb"], dtype=float),
                          "wind_speed": np.clip(np.asarray(m["wind"], dtype=float), 0.0, None),
                          "pressure": np.full(8760, float(pvlib.atmosphere.alt2pres(alt))),
                          "relative_humidity": np.full(8760, 50.0)}, index=index)
    return Meteo(frame, lat, lon, alt, 0.5, Source("data", f"PVsyst .MET {path.name}: {m['source']}"),
                 date.today().isoformat())


def scaled_meteo(base: Meteo, monthly: dict, tz: float, label: str) -> Meteo:
    """The typical year scaled month by month to the report's global and diffuse irradiation and mean
    temperature: global and diffuse by their ratios, the direct normal by the ratio of the beam
    (global minus diffuse), the temperature by its difference. The hourly shapes stay PVGIS's."""
    d = base.data.copy()
    months = d.index.tz_convert(_tz(tz)).month.to_numpy()
    for k in range(12):
        rows = months == k + 1
        for _pass in range(4):              # the diffuse is capped at the global: a few passes reach the targets
            g, dh = d.ghi.to_numpy()[rows].sum() / 1000.0, d.dhi.to_numpy()[rows].sum() / 1000.0
            kg = monthly["ghi"][k] / g if g > 0 else 1.0
            kd = monthly["dhi"][k] / dh if dh > 0 else 1.0
            kb = (monthly["ghi"][k] - monthly["dhi"][k]) / (g - dh) if g - dh > 0 else 1.0
            d.loc[rows, "ghi"] = d.ghi.to_numpy()[rows] * kg
            d.loc[rows, "dhi"] = np.minimum(d.dhi.to_numpy()[rows] * kd, d.ghi.to_numpy()[rows])
            d.loc[rows, "dni"] = d.dni.to_numpy()[rows] * max(kb, 0.0)
        d.loc[rows, "temp_air"] = d.temp_air.to_numpy()[rows] + (monthly["t"][k] - d.temp_air.to_numpy()[rows].mean())
    return Meteo(d, base.latitude, base.longitude, base.elevation, base.time_offset_h,
                 Source("data", f"{base.source.label}, scalato mese per mese su {label}"), base.fetched)


def monthly_weather(meteo: Meteo, tz: float) -> dict:
    d = meteo.data
    months = d.index.tz_convert(_tz(tz)).month.to_numpy()
    out = {"ghi": [], "dhi": [], "t": []}
    for k in range(12):
        rows = months == k + 1
        out["ghi"].append(d.ghi.to_numpy()[rows].sum() / 1000.0)
        out["dhi"].append(d.dhi.to_numpy()[rows].sum() / 1000.0)
        out["t"].append(float(d.temp_air.to_numpy()[rows].mean()))
    return out


# ----------------------------------------------------------------------------------------------------
# the system
# ----------------------------------------------------------------------------------------------------

def build_module(spec: dict, iam_profile, gamma_override: float | None = "report", given_sdm: bool = True) -> ModuleSpec:
    """The module of a case: the catalogue record (or the typed one), the report's temperature coefficient
    unless told otherwise, the report's IAM profile, the printed area (the efficiency enters the thermal
    model)."""
    if "catalogue" in spec:
        found = [r for r in catalog.search("modules", spec["catalogue"], limit=20) if r.get("model") == spec["catalogue"]]
        if not found:
            raise RuntimeError(f"module {spec['catalogue']} not in the catalogue")
        rec = dict(found[0])
    else:
        rec = dict(spec["record"])
    if not given_sdm:
        rec.pop("sdm", None)
    if gamma_override == "report":
        rec["gamma_pmax"] = spec["gamma"]
    elif gamma_override is not None:
        rec["gamma_pmax"] = gamma_override
    rec["cells"] = spec.get("cells", rec.get("cells") or 0)
    area = spec.get("area")
    if area:
        rec["length"], rec["width"] = area / 1.134, 1.134
    if iam_profile:
        rec["iam_profile"] = {"theta": [float(a) for a, _v in iam_profile], "iam": [float(v) for _a, v in iam_profile]}
    else:
        rec.pop("iam_profile", None)
    return ModuleSpec.from_record(rec)


def build_arrays(case: Case, module: ModuleSpec) -> list[ArraySpec]:
    out = []
    for i, a in enumerate(case.arrays):
        out.append(ArraySpec(key=f"a{i}", name=f"campo {i + 1}", tilt=a["tilt"], azimuth=a["azimuth"],
                             modules=a["modules"], module=module, thermal=a.get("thermal", "open"),
                             rows=a.get("rows", 0), pitch=a.get("pitch", 0.0), slant=a.get("slant", 0.0),
                             upright=a.get("upright", True), stack=a.get("stack", 1),
                             stand_off=a.get("stand_off", 0.15)))
    return out


def build_horizon(profile) -> Horizon | None:
    if not profile:
        return None
    az = np.array([(float(a) + 180.0) % 360.0 for a, _h in profile])
    el = np.array([float(h) for _a, h in profile])
    return Horizon(az, el, Source("data", "profilo dell'orizzonte stampato nel rapporto PVsyst (PVGIS)"))


def run(case: Case, meteo: Meteo, eta: float, module: ModuleSpec | None = None, losses: Losses | None = None,
        use_horizon: bool = True) -> dict:
    """One simulation of a case: the nodes of the chain (kWh/m2 and kWh), the steps (%), PR, yield, the
    monthly table and a few details of the arrays."""
    module = module or build_module(case.module, case.iam_profile)
    arrays = build_arrays(case, module)
    inv = InverterSpec("PVsyst", case.inverter["label"], pac=case.inverter["pac_total"], eta=eta, count=1)
    if losses is None:
        kwargs = dict(case.losses)
        kwargs.setdefault("iam_b0", 0.05)
        losses = Losses(transposition="perez", albedo=0.20, use_horizon=use_horizon, use_near=False, **kwargs)
    hor = build_horizon(case.horizon) if use_horizon else None
    sim = simulate(meteo, arrays, inv, losses, hor)
    chain = {s.key: s for s in sim.chain}
    steps = {k: (chain[k].change if k in chain and chain[k].change is not None else None) for k, _p, _l in STEP_MAP}
    nodes = {"globhor": chain["ghi"].value, "globinc": chain["poa"].value, "globeff": chain["soiling"].value,
             "e_nom": chain["nominal"].value, "e_mpp": chain["dc_wiring"].value, "e_inv": chain["clipping"].value,
             "e_grid": chain["unavailability"].value}
    months = meteo.data.index.tz_convert(_tz(case.tz)).month.to_numpy()
    h = sim.hourly
    monthly = {"ghi": [], "dhi": [], "t": [], "globinc": [], "globeff": [], "e_grid": []}
    for k in range(12):
        rows = months == k + 1
        monthly["ghi"].append(h.ghi.to_numpy()[rows].sum() / 1000.0)
        monthly["dhi"].append(h.dhi.to_numpy()[rows].sum() / 1000.0)
        monthly["t"].append(float(h.temp_air.to_numpy()[rows].mean()))
        monthly["globinc"].append(h.poa.to_numpy()[rows].sum() / 1000.0)
        monthly["globeff"].append(h.poa_eff.to_numpy()[rows].sum() / 1000.0)
        monthly["e_grid"].append(h.e_kwh.to_numpy()[rows].sum())
    details = {}
    for a in sim.arrays:
        details[a["key"]] = {k: a.get(k) for k in ("row_shading", "rows_electrical", "sky_seen", "t_cell_max", "poa_kwh_m2")}
        st = sim.record.find(f"{a['key']}.rows")
        if st is not None:
            details[a["key"]]["rows_step"] = {q.label: q.value for q in st.inputs} | {"loss": st.result.value}
    return {"nodes": nodes, "steps": steps, "pr": 100.0 * sim.pr, "yield": sim.specific_yield, "energy": sim.energy_kwh,
            "p_stc_kw": sim.p_stc_kw, "monthly": monthly, "details": details, "eta": eta, "notes": sim.notes,
            "sdm": module.sdm(), "module": f"{module.manufacturer} {module.model}", "gamma": module.gamma_pmax,
            "weather": meteo.source.label}


def calibrated(case: Case, meteo: Meteo, target: float, eta0: float, **kw) -> dict:
    """Meridiana with the inverter's weighted efficiency tuned until its yearly efficiency loss equals
    PVsyst's (three rounds of the simple scaling are enough to 0.01 points)."""
    eta = eta0
    res = None
    for _ in range(3):
        res = run(case, meteo, eta, **kw)
        got = res["steps"]["inverter"]
        eta = min(0.999, eta * (1.0 + target / 100.0) / (1.0 + got / 100.0))
    return res


# ----------------------------------------------------------------------------------------------------
# tables
# ----------------------------------------------------------------------------------------------------

def _f(x, d=1, sign=False):
    if x is None:
        return "-"
    return f"{x:+.{d}f}" if sign else f"{x:.{d}f}"


def _pct(a, b):
    return 100.0 * (b / a - 1.0) if a else float("nan")


def table_nodes(out: io.StringIO, case: Case, runs: dict) -> None:
    ref = case.ref
    names = list(runs)
    out.write("\nNodi della catena (PVsyst dal rapporto; Meridiana per variante; scarto % rispetto a PVsyst)\n")
    head = f"{'nodo':<18}{'PVsyst':>11}" + "".join(f"{n:>24}" for n in names)
    out.write(head + "\n")
    for key in NODE_KEYS:
        scale = 1000.0 if key.startswith("e_") else 1.0
        rv = ref[key] / scale
        line = f"{NODE_LABELS[key]:<18}{rv:>11.1f}"
        for n in names:
            mv = runs[n]["nodes"][key] / scale
            line += f"{mv:>14.1f} ({_pct(rv, mv):+6.2f} %)"
        out.write(line + "\n")
    line = f"{'resa kWh/kWp':<18}{ref['yield']:>11.0f}"
    for n in names:
        line += f"{runs[n]['yield']:>14.0f} ({_pct(ref['yield'], runs[n]['yield']):+6.2f} %)"
    out.write(line + "\n")
    line = f"{'PR %':<18}{ref['pr']:>11.2f}"
    for n in names:
        line += f"{runs[n]['pr']:>14.2f} ({runs[n]['pr'] - ref['pr']:+6.2f} pt)"
    out.write(line + "\n")
    # the ratios between nodes, less sensitive to the weather
    out.write("\nRapporti fra nodi (meno sensibili al meteo)\n")
    pairs = [("globinc", "globhor", "GlobInc/GlobHor"), ("globeff", "globinc", "GlobEff/GlobInc"),
             ("e_mpp", "e_nom", "EArrMPP/EArrNom"), ("e_inv", "e_mpp", "EOutInv/EArrMPP"), ("e_grid", "e_inv", "E_Grid/EOutInv"),
             ("e_grid", "e_nom", "E_Grid/EArrNom")]
    out.write(f"{'rapporto':<18}{'PVsyst':>11}" + "".join(f"{n:>24}" for n in names) + "\n")
    for a, b, label in pairs:
        rv = ref[a] / ref[b]
        line = f"{label:<18}{rv:>11.4f}"
        for n in names:
            mv = runs[n]["nodes"][a] / runs[n]["nodes"][b]
            line += f"{mv:>14.4f} ({100 * (mv - rv):+6.2f} pt)"
        out.write(line + "\n")


def table_steps(out: io.StringIO, case: Case, runs: dict) -> None:
    ref = case.ref
    names = list(runs)
    out.write("\nPassi del diagramma delle perdite (% sul valore precedente; scarto in punti)\n")
    out.write(f"{'passo':<36}{'PVsyst':>9}" + "".join(f"{n:>22}" for n in names) + "\n")
    for mk, pk, label in STEP_MAP:
        rv = ref["steps"].get(pk)
        line = f"{label:<36}{_f(rv, 2, True):>9}"
        for n in names:
            mv = runs[n]["steps"].get(mk)
            if mv is None and rv is None:
                line += f"{'-':>22}"
            elif rv is None:
                line += f"{_f(mv, 2, True):>12}{'(n.c.)':>10}"
            elif mv is None:
                line += f"{'-':>12}{'(n.c.)':>10}"
            else:
                line += f"{_f(mv, 2, True):>12}{'(' + _f(mv - rv, 2, True) + ')':>10}"
        out.write(line + "\n")
    if ref["extra"]:
        factor = 1.0
        for _k, v in ref["extra"].items():
            factor *= 1.0 + v / 100.0
        out.write("Passi di PVsyst senza equivalente in Meridiana: "
                  + "; ".join(f"{EXTRA_LABELS.get(k, k)} {v:+.2f} %" for k, v in ref["extra"].items())
                  + f" (fattore complessivo {factor:.4f})\n")
        for n in names:
            adj = runs[n]["nodes"]["e_grid"] * factor
            out.write(f"   {n}: E_Grid di Meridiana x fattore = {adj / 1000:.1f} MWh, scarto {_pct(ref['e_grid'], adj):+.2f} % "
                      f"(senza fattore {_pct(ref['e_grid'], runs[n]['nodes']['e_grid']):+.2f} %)\n")
    if "electrical_shading" not in ref["steps"]:
        for n in names:
            el = runs[n]["steps"].get("electrical")
            if el:
                undone = runs[n]["nodes"]["e_grid"] / (1.0 + el / 100.0)
                out.write(f"   {n}: senza l'effetto elettrico delle file, che PVsyst (ombre lineari) non ha: E_Grid "
                          f"{undone / 1000:.1f} MWh, scarto {_pct(ref['e_grid'], undone):+.2f} %\n")


def table_monthly(out: io.StringIO, case: Case, run_: dict, name: str, weather_only: bool = False) -> None:
    ref = case.ref["monthly"]
    m = run_["monthly"]
    out.write(f"\nTabella mensile: PVsyst (rapporto) contro Meridiana [{name}]\n")
    if weather_only:
        out.write(f"{'mese':<5}{'GHI pv':>8}{'GHI me':>8}{'d%':>7}{'DHI pv':>8}{'DHI me':>8}{'d%':>7}{'T pv':>7}{'T me':>7}{'dT':>6}\n")
    else:
        out.write(f"{'mese':<5}{'GHI pv':>8}{'GHI me':>8}{'d%':>7}{'DHI pv':>8}{'DHI me':>8}{'T pv':>7}{'T me':>7}"
                  f"{'Inc pv':>8}{'Inc me':>8}{'d%':>7}{'Eff pv':>8}{'Eff me':>8}{'d%':>7}{'Egrid pv':>10}{'Egrid me':>10}{'d%':>7}\n")
    for k in range(12):
        if weather_only:
            out.write(f"{MONTHS[k]:<5}{ref['ghi'][k]:>8.1f}{m['ghi'][k]:>8.1f}{_pct(ref['ghi'][k], m['ghi'][k]):>+7.1f}"
                      f"{ref['dhi'][k]:>8.1f}{m['dhi'][k]:>8.1f}{_pct(ref['dhi'][k], m['dhi'][k]):>+7.1f}"
                      f"{ref['t'][k]:>7.1f}{m['t'][k]:>7.1f}{m['t'][k] - ref['t'][k]:>+6.1f}\n")
        else:
            out.write(f"{MONTHS[k]:<5}{ref['ghi'][k]:>8.1f}{m['ghi'][k]:>8.1f}{_pct(ref['ghi'][k], m['ghi'][k]):>+7.1f}"
                      f"{ref['dhi'][k]:>8.1f}{m['dhi'][k]:>8.1f}{ref['t'][k]:>7.1f}{m['t'][k]:>7.1f}"
                      f"{ref['globinc'][k]:>8.1f}{m['globinc'][k]:>8.1f}{_pct(ref['globinc'][k], m['globinc'][k]):>+7.1f}"
                      f"{ref['globeff'][k]:>8.1f}{m['globeff'][k]:>8.1f}{_pct(ref['globeff'][k], m['globeff'][k]):>+7.1f}"
                      f"{ref['e_grid'][k] / 1000:>10.2f}{m['e_grid'][k] / 1000:>10.2f}{_pct(ref['e_grid'][k], m['e_grid'][k]):>+7.1f}\n")
    tot = lambda key: sum(ref[key])  # noqa: E731
    me = lambda key: sum(m[key])  # noqa: E731
    if weather_only:
        out.write(f"{'anno':<5}{tot('ghi'):>8.1f}{me('ghi'):>8.1f}{_pct(tot('ghi'), me('ghi')):>+7.1f}"
                  f"{tot('dhi'):>8.1f}{me('dhi'):>8.1f}{_pct(tot('dhi'), me('dhi')):>+7.1f}"
                  f"{np.mean(ref['t']):>7.1f}{np.mean(m['t']):>7.1f}{np.mean(m['t']) - np.mean(ref['t']):>+6.1f}\n")
    else:
        out.write(f"{'anno':<5}{tot('ghi'):>8.1f}{me('ghi'):>8.1f}{_pct(tot('ghi'), me('ghi')):>+7.1f}"
                  f"{tot('dhi'):>8.1f}{me('dhi'):>8.1f}{np.mean(ref['t']):>7.1f}{np.mean(m['t']):>7.1f}"
                  f"{tot('globinc'):>8.1f}{me('globinc'):>8.1f}{_pct(tot('globinc'), me('globinc')):>+7.1f}"
                  f"{tot('globeff'):>8.1f}{me('globeff'):>8.1f}{_pct(tot('globeff'), me('globeff')):>+7.1f}"
                  f"{tot('e_grid') / 1000:>10.2f}{me('e_grid') / 1000:>10.2f}{_pct(tot('e_grid'), me('e_grid')):>+7.1f}\n")


# ----------------------------------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "meridiana-confronto-pvsyst")
    ap.add_argument("--samples", type=Path, default=Path(r"C:\Users\utente\dev\meridiana-prove"))
    ap.add_argument("--cases", default="")
    ap.add_argument("--out", type=Path, default=HERE / "confronto_pvsyst-risultati.txt")
    args = ap.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    out = io.StringIO()
    import pvlib
    out.write(f"Confronto Meridiana / PVsyst su casi pubblici, {date.today().isoformat()}, pvlib {pvlib.__version__}, "
              f"python {sys.version.split()[0]}\n")
    out.write(f"Campioni: {args.samples}; cache PVGIS: {args.cache}\n")
    cases = build_cases(args.samples)
    wanted = [k for k in args.cases.split(",") if k] or list(cases)
    summary = []
    for key in wanted:
        if key not in cases:
            out.write(f"\ncaso {key}: non disponibile (manca il materiale in {args.samples})\n")
            continue
        case = cases[key]
        out.write("\n" + "=" * 118 + f"\nCASO {key}: {case.title}\nPVsyst {case.pvsyst_version}; fonte: {case.source}\n")
        out.write(f"Meteo del rapporto: {case.weather['report_db']}; GlobHor {case.ref['globhor']:.1f} kWh/m2, "
                  f"T media {np.mean(case.ref['monthly']['t']):.2f} C\n")
        base_module = build_module(case.module, case.iam_profile)
        sdm = base_module.sdm()
        out.write(f"Modulo: {base_module.manufacturer} {base_module.model}"
                  + (f" (al posto di {case.module['proxy_for']})" if case.module.get("proxy_for") else "")
                  + f"; gamma {base_module.gamma_pmax:.3f} %/K dal rapporto; efficienza {100 * base_module.efficiency:.2f} %; "
                  + ("modello a un diodo: parametri della lista CEC" if case.module.get("catalogue") and "sdm" in
                     (catalog.search("modules", case.module["catalogue"], limit=1)[0] if case.module.get("catalogue") else {})
                     and not sdm.get("linear") else "modello a un diodo adattato al datasheet (De Soto)" if not sdm.get("linear")
                     else "LINEARE (adattamento fallito)") + "\n")
        out.write(f"Inverter: {case.inverter['label']}; P_AC {case.inverter['pac_total'] / 1000:.0f} kW; "
                  f"DC/AC {case.ref['p_stc_kw'] / (case.inverter['pac_total'] / 1000):.3f}\n")
        out.write(f"Perdite date a Meridiana: {case.losses}; IAM: "
                  + ("profilo a punti del rapporto" if case.iam_profile else "ASHRAE b0 0,05") + "; orizzonte: "
                  + ("profilo stampato" if case.horizon else "libero") + "\n")
        for n in case.notes:
            out.write(f"Nota: {n}\n")
        p_stc_me = sum(a["modules"] for a in case.arrays) * base_module.pmax / 1000.0
        out.write(f"Potenza STC: PVsyst {case.ref['p_stc_kw']:.2f} kWp, Meridiana {p_stc_me:.2f} kWp\n")
        # the weather
        runs: dict = {}
        tz = case.tz
        pvgis53 = pvgis_meteo(case.lat, case.lon, args.cache, "5.3")
        out.write(f"PVGIS 5.3 TMY: {pvgis53.source.label}; GlobHor {pvgis53.summary['ghi_kwh_m2']:.1f} kWh/m2 "
                  f"({_pct(case.ref['globhor'], pvgis53.summary['ghi_kwh_m2']):+.1f} % sul rapporto), T media "
                  f"{pvgis53.summary['t_mean']:.2f} C ({pvgis53.summary['t_mean'] - np.mean(case.ref['monthly']['t']):+.2f} C)\n")
        eta0 = case.inverter["eta"]
        target = case.ref["steps"].get("inverter_efficiency")
        pvgis52 = pvgis_meteo(case.lat, case.lon, args.cache, "5.2")
        out.write(f"PVGIS 5.2 TMY: {pvgis52.source.label}; GlobHor {pvgis52.summary['ghi_kwh_m2']:.1f} kWh/m2 "
                  f"({_pct(case.ref['globhor'], pvgis52.summary['ghi_kwh_m2']):+.1f} % sul rapporto), T media "
                  f"{pvgis52.summary['t_mean']:.2f} C\n")
        if case.weather["kind"] == "pvgis":
            runs["5.3 catalogo"] = run(case, pvgis53, eta0)
            runs["5.3 inv.tarato"] = calibrated(case, pvgis53, target, eta0)
            runs["5.2 catalogo"] = run(case, pvgis52, eta0)
            runs["5.2 inv.tarato"] = calibrated(case, pvgis52, target, eta0)
            main_run = "5.2 inv.tarato"
            weather_runs = [("5.3 catalogo", True), ("5.2 catalogo", True)]
        elif case.weather["kind"] == "met":
            met = met_meteo(case.weather["path"], case.lat, case.lon, case.alt, tz)
            out.write(f"MET del progetto: GlobHor {met.summary['ghi_kwh_m2']:.1f} kWh/m2, T media {met.summary['t_mean']:.2f} C\n")
            runs["MET catalogo"] = run(case, met, eta0)
            runs["MET inv.tarato"] = calibrated(case, met, target, eta0)
            runs["PVGIS 5.3 catalogo"] = run(case, pvgis53, eta0)
            main_run = "MET inv.tarato"
            weather_runs = [("PVGIS 5.3 catalogo", True)]
        else:
            scaled = scaled_meteo(pvgis53, case.ref["monthly"], tz, f"rapporto {case.key}")
            out.write(f"PVGIS scalato: GlobHor {scaled.summary['ghi_kwh_m2']:.1f} kWh/m2, T media {scaled.summary['t_mean']:.2f} C\n")
            runs["scalato catalogo"] = run(case, scaled, eta0)
            runs["scalato inv.tarato"] = calibrated(case, scaled, target, eta0)
            runs["PVGIS 5.3 catalogo"] = run(case, pvgis53, eta0)
            main_run = "scalato inv.tarato"
            weather_runs = [("PVGIS 5.3 catalogo", True)]
        out.write("Efficienza pesata dell'inverter: catalogo/proxy "
                  f"{100 * eta0:.2f} %, tarata sul passo di PVsyst {100 * runs[main_run]['eta']:.2f} %\n")
        table_nodes(out, case, runs)
        table_steps(out, case, runs)
        for a, det in runs[main_run]["details"].items():
            if det.get("rows_step"):
                out.write(f"Dettagli delle file ({a}): {det['rows_step']}; ombra lineare delle file "
                          f"{100 * det['row_shading']:.2f} %, effetto elettrico {100 * (det.get('rows_electrical') or 0):.2f} %\n")
            if det.get("sky_seen") is not None and case.horizon:
                out.write(f"Orizzonte ({a}): cielo diffuso ancora visto {100 * det['sky_seen']:.2f} % (PVsyst stampa il "
                          f"'Diffuse Factor' dell'orizzonte: vedi casi.json)\n")
            out.write(f"Temperatura massima di cella ({a}): {det['t_cell_max']:.1f} C\n")
        for n in runs[main_run]["notes"]:
            out.write(f"Meridiana avverte: {n}\n")
        table_monthly(out, case, runs[main_run], main_run)
        for name, wo in weather_runs:
            table_monthly(out, case, runs[name], name, weather_only=wo)
        # sensitivities on the main weather of the case
        wm = pvgis52 if case.weather["kind"] == "pvgis" else met if case.weather["kind"] == "met" else scaled
        sens: dict = {}
        if case.module.get("catalogue"):
            rec = catalog.search("modules", case.module["catalogue"], limit=1)[0]
            if rec.get("gamma_pmax") is not None:
                sens[f"gamma CEC {rec['gamma_pmax']:.3f}"] = run(case, wm, runs[main_run]["eta"],
                                                                  module=build_module(case.module, case.iam_profile, gamma_override=None))
            if rec.get("sdm"):
                m2 = build_module(case.module, case.iam_profile, given_sdm=False)
                sens["SDM De Soto dal datasheet" + (" (LINEARE)" if m2.sdm().get("linear") else "")] = run(case, wm, runs[main_run]["eta"], module=m2)
        if case.iam_profile:
            sens["IAM ASHRAE 0,05 (default)"] = run(case, wm, runs[main_run]["eta"], module=build_module(case.module, None))
        if case.horizon:
            sens["senza orizzonte"] = run(case, wm, runs[main_run]["eta"], use_horizon=False)
        sens["perdite predefinite di Meridiana"] = run(case, wm, runs[main_run]["eta"], losses=Losses(use_near=False))
        out.write("\nSensibilita' (stesso meteo della variante principale, inverter tarato):\n")
        out.write(f"{'variante':<40}{'E_Grid MWh':>12}{'scarto %':>10}{'PR %':>8}{'irr.liv.':>10}{'temper.':>9}{'IAM':>8}{'orizz.':>8}\n")
        base = runs[main_run]
        for name, r in [(main_run, base)] + list(sens.items()):
            out.write(f"{name:<40}{r['nodes']['e_grid'] / 1000:>12.1f}{_pct(case.ref['e_grid'], r['nodes']['e_grid']):>+10.2f}"
                      f"{r['pr']:>8.2f}{_f(r['steps']['irradiance_level'], 2, True):>10}{_f(r['steps']['temperature'], 2, True):>9}"
                      f"{_f(r['steps']['iam'], 2, True):>8}{_f(r['steps']['far'], 2, True):>8}\n")
        summary.append((case.key, case.title, case.ref, runs, main_run))
    # the summary
    out.write("\n" + "=" * 118 + "\nRIASSUNTO (variante principale: meteo del rapporto o scalato su di esso, inverter tarato)\n")
    out.write(f"{'caso':<16}{'E_Grid PVsyst':>14}{'Meridiana':>11}{'scarto %':>9}{'x fattore':>10}{'PR pv':>7}{'PR me':>7}{'dPR':>6}"
              f"{'GlobInc d%':>11}{'GlobEff/Inc d':>14}{'MPP/Nom d':>10}\n")
    for key, _title, ref, runs, main_run in summary:
        r = runs[main_run]
        factor = 1.0
        for v in ref["extra"].values():
            factor *= 1.0 + v / 100.0
        out.write(f"{key:<16}{ref['e_grid'] / 1000:>14.1f}{r['nodes']['e_grid'] / 1000:>11.1f}"
                  f"{_pct(ref['e_grid'], r['nodes']['e_grid']):>+9.2f}{_pct(ref['e_grid'], r['nodes']['e_grid'] * factor):>+10.2f}"
                  f"{ref['pr']:>7.2f}{r['pr']:>7.2f}{r['pr'] - ref['pr']:>+6.2f}"
                  f"{_pct(ref['globinc'], r['nodes']['globinc']):>+11.2f}"
                  f"{100 * (r['nodes']['globeff'] / r['nodes']['globinc'] - ref['globeff'] / ref['globinc']):>+14.2f}"
                  f"{100 * (r['nodes']['e_mpp'] / r['nodes']['e_nom'] - ref['e_mpp'] / ref['e_nom']):>+10.2f}\n")
    out.write("\nRIASSUNTO con il meteo PVGIS 5.3 grezzo e l'efficienza di catalogo (quello che l'applicazione farebbe oggi);\n"
              "'effetto meteo' = E_Grid di Meridiana con PVGIS 5.3 contro E_Grid di Meridiana con il meteo del rapporto\n")
    out.write(f"{'caso':<16}{'E_Grid PVsyst':>14}{'Meridiana':>11}{'scarto %':>9}{'eff.meteo %':>12}{'PR pv':>7}{'PR me':>7}"
              f"{'GlobHor d%':>11}{'T media d':>10}\n")
    for key, _title, ref, runs, main_run in summary:
        name = "5.3 catalogo" if "5.3 catalogo" in runs else "PVGIS 5.3 catalogo"
        r = runs[name]
        own = runs[main_run]["nodes"]["e_grid"]
        out.write(f"{key:<16}{ref['e_grid'] / 1000:>14.1f}{r['nodes']['e_grid'] / 1000:>11.1f}"
                  f"{_pct(ref['e_grid'], r['nodes']['e_grid']):>+9.2f}{_pct(own, r['nodes']['e_grid']):>+12.2f}{ref['pr']:>7.2f}{r['pr']:>7.2f}"
                  f"{_pct(ref['globhor'], r['nodes']['globhor']):>+11.2f}{np.mean(r['monthly']['t']) - np.mean(ref['monthly']['t']):>+10.2f}\n")
    text = out.getvalue()
    args.out.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
