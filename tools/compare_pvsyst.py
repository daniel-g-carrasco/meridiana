#!/usr/bin/env python3
"""Meridiana against PVsyst on public simulation reports.

For each case of a casi.json (inputs and outputs read from public PVsyst reports, kept outside the
repository: see docs/studio/11-pvsyst-casi-di-confronto.md), the same system is computed by Meridiana:
- the weather is the PVGIS typical year of the site, scaled month by month to the report's horizontal
  global and diffuse irradiation and to its mean temperature, so that both start from the same months
  (the hours inside a month keep PVGIS's shape: the transposition cannot match exactly);
- the module is the catalogue's when its model is there, the typical one scaled to its power otherwise;
- thermal case, IAM, losses, horizon, rows and inverters as the report gives them.
The nodes of PVsyst's loss diagram are printed beside Meridiana's, with the steps both programs have.
Meridiana has no auxiliaries, MV transformer or lines: the comparison is full up to the inverter output.

  python tools/compare_pvsyst.py <casi.json> [--case ID ...] [--cache DIR] [--markdown FILE]

Only fixed, monofacial cases run today (no trackers or bifacial yet): the others are listed as skipped.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from meridiana import catalog  # noqa: E402
from meridiana.energy import meteo  # noqa: E402
from meridiana.energy.components import InverterSpec, ModuleSpec  # noqa: E402
from meridiana.energy.pedigree import Source  # noqa: E402
from meridiana.energy.simulate import ArraySpec, Losses, simulate  # noqa: E402

THERMAL = {29.0: "open", 20.0: "semi", 15.0: "integrated"}      # Meridiana's cases by their Uc
NODES = [("globhor", "GlobHor (kWh/m²)", "ghi"), ("globinc", "GlobInc (kWh/m²)", "poa"),
         ("globeff", "GlobEff (kWh/m²)", "soiling"), ("array_nominal", "EArrNom (MWh)", "nominal"),
         ("array_mpp", "EArrMPP (MWh)", "dc_wiring"), ("inverter_output", "E inverter out (MWh)", "clipping")]
STEPS = ["transposition", "far_shading", "near_shading", "iam", "soiling", "irradiance_level", "temperature",
         "module_quality", "lid", "mismatch", "electrical_shading", "ohmic", "inverter_efficiency",
         "inverter_over_power"]


class Skipped(Exception):
    pass


def scaled(m: meteo.Meteo, rows: list[dict]) -> meteo.Meteo:
    """The typical year with each month's global and diffuse horizontal irradiation and mean temperature
    made the report's; the direct normal follows from the two (sun at the data's own instant)."""
    import pandas as pd
    import pvlib
    d = m.data.copy()
    month = d.index.month
    for k, row in enumerate(rows, start=1):
        sel = month == k
        g = d.loc[sel, "ghi"].sum() / 1000.0
        dh = d.loc[sel, "dhi"].sum() / 1000.0
        if row.get("GlobHor") and g > 0:
            d.loc[sel, "ghi"] *= float(row["GlobHor"]) / g
        if row.get("DiffHor") and dh > 0:
            d.loc[sel, "dhi"] *= float(row["DiffHor"]) / dh
        elif row.get("GlobHor") and g > 0:
            d.loc[sel, "dhi"] *= float(row["GlobHor"]) / g
        if row.get("T_Amb") is not None:
            d.loc[sel, "temp_air"] += float(row["T_Amb"]) - d.loc[sel, "temp_air"].mean()
    d["dhi"] = np.minimum(d.dhi, d.ghi)
    sun = pvlib.solarposition.get_solarposition(d.index + pd.Timedelta(hours=m.time_offset_h), m.latitude,
                                                m.longitude, altitude=m.elevation)
    cos_z = np.cos(np.radians(sun.zenith.to_numpy()))
    lit = cos_z > 0.05
    dni = np.zeros(len(d))
    dni[lit] = (d.ghi.to_numpy()[lit] - d.dhi.to_numpy()[lit]) / cos_z[lit]
    d["dni"] = np.clip(dni, 0.0, 1100.0)
    return dataclasses.replace(m, data=d, source=Source("data", m.source.label + ", scaled to the report's months"))


def module_of(entry: dict, iam: dict) -> ModuleSpec:
    found = None
    model = (entry.get("model") or "").lower().replace(" ", "")
    for rec in catalog.search("modules", entry.get("model") or "") if model else []:
        if (rec.get("model") or "").lower().replace(" ", "") == model and abs(float(rec.get("pmax") or 0)
                                                                           - float(entry["pnom_w"])) < 1:
            found = rec
            break
    m = ModuleSpec.from_record(found or {"pmax": float(entry["pnom_w"]), "manufacturer": entry.get("manufacturer"),
                                         "model": entry.get("model")})
    if iam.get("profile"):
        m.iam_profile = {"theta": [float(a) for a, _v in iam["profile"]], "iam": [float(v) for _a, v in iam["profile"]]}
    return m


def inverter_of(rows: list[dict], eff_step: float) -> InverterSpec:
    """The inverters: the catalogue's when the model of the first is there (its weighted efficiency), else one
    whose nominal efficiency is the report's "loss during operation" (which makes the losses a little higher:
    PVWatts' curve adds the part-load losses on top)."""
    first = rows[0]
    count = sum(int(r.get("count") or 0) for r in rows)
    if count == 0 or not all(r.get("pnom_kw") for r in rows):
        raise Skipped("inverters without their count or power")
    pac_each = 1000.0 * sum(float(r["pnom_kw"]) * int(r["count"]) for r in rows) / count
    model = (first.get("model") or "").lower().replace(" ", "")
    for rec in catalog.search("inverters", first.get("model") or "") if model else []:
        if (rec.get("model") or "").lower().replace(" ", "") == model:
            inv = InverterSpec.from_record(rec, count)
            inv.pac = pac_each                   # as the report sizes them (PVsyst may limit them)
            return inv
    return InverterSpec(first.get("manufacturer", ""), first.get("model", ""), pac_each, 1.0 + eff_step / 100.0, count)


def table_of(width: float, m: ModuleSpec) -> tuple[int, bool]:
    """How many modules across a table of this slant width, and whether they stand upright: the reading
    of the two that fits a whole number best (the module's own sizes when known, else typical ones)."""
    best = None
    for upright, side in ((True, m.length), (False, m.width)):
        n = max(1, round(width / side))
        miss = abs(width - n * side) / width
        if best is None or miss < best[0]:
            best = (miss, n, upright)
    return best[1], best[2]


def inputs(case: dict):
    if case.get("bifacial"):
        raise Skipped("bifacial")
    if case["site"].get("lat") is None or case["site"].get("lon") is None:
        raise Skipped("no site coordinates in the report")
    orients = case["orientations"]
    if any(o.get("type") != "fixed" for o in orients):
        raise Skipped("trackers")
    losses_in = case["losses"]
    iam = losses_in.get("iam") or {}
    modules = case["modules"]
    if len(modules) != 1 and len(modules) != len(orients):
        raise Skipped("several module types on several orientations")
    total = int(sum(int(m["count"]) for m in modules))
    uc = float(losses_in.get("thermal_uc") or 29.0)
    thermal = THERMAL[min(THERMAL, key=lambda u: abs(u - uc))]
    arrays = []
    for i, o in enumerate(orients):
        entry = modules[i] if len(modules) == len(orients) else modules[0]
        if len(modules) == len(orients):
            count = int(entry["count"])
        else:
            share = o.get("share") if len(orients) > 1 else 1.0
            if share is None:
                raise Skipped("several orientations without their share")
            count = round(total * float(share))
        a = ArraySpec(f"a{i + 1}", f"{o['tilt_deg']:g}/{o['azimuth_deg']:+g}", float(o["tilt_deg"]),
                      float(o["azimuth_deg"]), count, module_of(entry, iam), thermal)
        if o.get("rows") and o.get("pitch_m") and o.get("collector_width_m"):
            a.rows, a.pitch, a.slant = int(o["rows"]), float(o["pitch_m"]), float(o["collector_width_m"])
            a.stack, a.upright = table_of(a.slant, a.module)
        arrays.append(a)
    p_stc = sum(a.p_stc for a in arrays)
    inv_rows = case["inverters"]
    pac_total = 1000.0 * sum(float(r["pnom_kw"]) * int(r["count"]) for r in inv_rows)
    eff_step = next((s["pct"] for s in case["loss_diagram"] if s["key"] == "inverter_efficiency" and s["pct"]), -2.0)
    inverter = inverter_of(inv_rows, float(eff_step))
    ac_stc = losses_in.get("ac_ohmic_pct_stc")
    losses = Losses(albedo=float(case["weather"].get("albedo") or 0.2),
                    use_horizon=bool(case["shading"].get("horizon_profile")), use_near=False,
                    iam_b0=float(iam.get("b0") or 0.05), soiling=float(losses_in.get("soiling_pct") or 0.0),
                    quality=float(losses_in.get("module_quality_pct") or 0.0),
                    lid=float(losses_in.get("lid_pct") or 0.0),
                    mismatch=float(losses_in.get("mismatch_pct") or 0.0) + float(losses_in.get("string_mismatch_pct") or 0.0),
                    dc_wiring=float(losses_in.get("ohmic_dc_pct_stc") or 0.0),
                    ac_wiring=float(ac_stc) * pac_total / p_stc if ac_stc else 0.0,
                    unavailability=float(losses_in.get("unavailability_pct") or 0.0))
    horizon = None
    if losses.use_horizon:
        pts = sorted((float(a) + 180.0) % 360.0 for a, _e in case["shading"]["horizon_profile"])
        prof = {(float(a) + 180.0) % 360.0: float(e) for a, e in case["shading"]["horizon_profile"]}
        horizon = meteo.Horizon(np.array(pts), np.array([prof[a] for a in pts]),
                                Source("data", "horizon printed in the PVsyst report"))
    return arrays, inverter, losses, horizon


def run(case: dict, cache: Path) -> dict:
    arrays, inverter, losses, horizon = inputs(case)
    site = case["site"]
    m = scaled(meteo.typical_year(float(site["lat"]), float(site["lon"]), cache), case["monthly"]["rows"])
    sim = simulate(m, arrays, inverter, losses, horizon)
    chain = {c.key: c for c in sim.chain}
    area_node = {"ghi", "poa", "soiling"}
    mine = {}
    for key, _label, ckey in NODES:
        c = chain.get(ckey)
        if c is not None:
            mine[key] = c.value if ckey in area_node else c.value / 1000.0
    mine["e_grid"] = sim.energy_kwh / 1000.0
    mine["pr"] = 100.0 * sim.pr
    mine["yield"] = sim.specific_yield
    steps = {}
    by = {"transposition": "poa", "far_shading": "far", "near_shading": "near", "iam": "iam", "soiling": "soiling",
          "irradiance_level": "irradiance_level", "temperature": "temperature", "module_quality": "quality",
          "lid": "lid", "mismatch": "mismatch", "electrical_shading": "electrical", "ohmic": "dc_wiring",
          "inverter_efficiency": "inverter", "inverter_over_power": "clipping"}
    for k, ck in by.items():
        if ck in chain and chain[ck].change is not None:
            steps[k] = chain[ck].change
    return {"mine": mine, "steps": steps, "module": arrays[0].module.source.label, "weather": m.source.label,
            "p_stc_kwp": sim.p_stc_kw, "inverter": f"{inverter.model}, {100 * inverter.eta:.1f} %"}


def theirs(case: dict) -> tuple[dict, dict]:
    o = case["outputs"]
    nodes = {"globhor": o.get("globhor_kwh_m2"), "globinc": o.get("globinc_kwh_m2"), "globeff": o.get("globeff_kwh_m2"),
             "array_nominal": o.get("array_nominal_mwh"), "array_mpp": o.get("array_mpp_mwh"),
             "inverter_output": o.get("inverter_output_mwh"), "e_grid": o.get("e_grid_mwh"), "pr": o.get("pr_pct"),
             "yield": o.get("specific_yield_kwh_kwp")}
    steps = {s["key"]: s["pct"] for s in case["loss_diagram"] if s.get("pct") is not None and s["key"] in STEPS}
    return nodes, steps


def table(case: dict, got: dict) -> list[str]:
    nodes, steps = theirs(case)
    lines = [f"### {case['id']} (PVsyst {case['pvsyst_version']})", "",
             f"- Meridiana: {got['p_stc_kwp']:.1f} kWp; module: {got['module']}; inverter: {got['inverter']}.",
             f"- Weather: {got['weather']}.", "",
             "| Node | PVsyst | Meridiana | Difference |", "|---|---|---|---|"]
    labels = {k: lab for k, lab, _c in NODES} | {"e_grid": "E_Grid (MWh) [no aux., MV]", "pr": "PR (%)",
                                                 "yield": "Specific yield (kWh/kWp)"}
    for key, label in labels.items():
        a, b = nodes.get(key), got["mine"].get(key)
        if a is None or b is None:
            continue
        diff = f"{b - a:+.2f} points" if key == "pr" else f"{100 * (b / a - 1):+.1f} %"
        lines.append(f"| {label} | {a:,.1f} | {b:,.1f} | {diff} |")
    lines += ["", "| Step | PVsyst % | Meridiana % |", "|---|---|---|"]
    for key in STEPS:
        a, b = steps.get(key), got["steps"].get(key)
        if a is None and b is None:
            continue
        fa = f"{a:+.2f}" if a is not None else "-"
        fb = f"{b:+.2f}" if b is not None else "-"
        lines.append(f"| {key} | {fa} | {fb} |")
    return lines + [""]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cases", type=Path)
    ap.add_argument("--case", action="append", default=[])
    ap.add_argument("--cache", type=Path, default=Path.home() / ".cache" / "meridiana-compare")
    ap.add_argument("--markdown", type=Path)
    args = ap.parse_args()
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    out = []
    for case in cases:
        if args.case and case["id"] not in args.case:
            continue
        try:
            got = run(case, args.cache)
        except Skipped as why:
            print(f"{case['id']}: skipped ({why})")
            continue
        except meteo.MeteoError as error:
            print(f"{case['id']}: no weather ({error})")
            continue
        lines = table(case, got)
        print("\n".join(lines))
        out += lines
    if args.markdown and out:
        args.markdown.write_text("\n".join(out), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
