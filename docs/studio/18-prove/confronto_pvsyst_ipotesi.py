"""Two hypotheses on the steps where Meridiana's chain differs from PVsyst (study 18, section B, part 3),
tested on the cases of confronto_pvsyst.py that have the same weather as PVsyst (the .MET of the project,
or the PVGIS 5.2 typical year of the PEAKI report):

1. the temperature step: PVsyst's thermal balance uses the module efficiency at the operating point
   (iterated with its electrical model, about 0.85 to 0.9 of the STC efficiency), Meridiana the STC one
   (simulate.py, pvsyst_cell call). pvlib's pvsyst_cell is patched here to take a fraction of the STC
   efficiency, and the temperature step is compared with the one printed by PVsyst;
2. the DC wiring step: PVsyst computes R I^2 with the array current of the hour, Meridiana scales the STC
   fraction by the power ratio (simulate.py, dc_wiring). Both are recomputed on the hourly series of the
   same simulation, with I/Istc = (G_eff / 1000) (1 + alpha_isc (Tc - 25)).

Usage (from the repository root, with the project's virtual environment):

    PYTHONPATH=src QT_QPA_PLATFORM=offscreen python docs/studio/18-prove/confronto_pvsyst_ipotesi.py
        [--cache DIR] [--samples DIR] [--out FILE]
"""

from __future__ import annotations

import argparse
import io
import sys
import tempfile
from pathlib import Path

import numpy as np
import pvlib

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import confronto_pvsyst as cp  # noqa: E402
from meridiana.energy.components import InverterSpec  # noqa: E402
from meridiana.energy.simulate import THERMAL, Losses, simulate  # noqa: E402

ORIGINAL = pvlib.temperature.pvsyst_cell


def patched_cell(factor: float):
    def cell(poa_global, temp_air, wind_speed, u_c=29.0, u_v=0.0, module_efficiency=0.1, alpha_absorption=0.9):
        return ORIGINAL(poa_global, temp_air, wind_speed, u_c=u_c, u_v=u_v,
                        module_efficiency=module_efficiency * factor, alpha_absorption=alpha_absorption)
    return cell


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "meridiana-confronto-pvsyst")
    ap.add_argument("--samples", type=Path, default=Path(r"C:\Users\utente\dev\meridiana-prove"))
    ap.add_argument("--out", type=Path, default=HERE / "confronto_pvsyst_ipotesi-risultati.txt")
    args = ap.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    cases = cp.build_cases(args.samples)
    out = io.StringIO()
    out.write("Ipotesi sui passi di temperatura e cavi DC, stesso meteo di PVsyst (pvlib %s)\n" % pvlib.__version__)
    for key in ("kuwait", "almarj", "kanpur", "peaki"):
        if key not in cases:
            out.write(f"\ncaso {key}: non disponibile\n")
            continue
        case = cases[key]
        if case.weather["kind"] == "met":
            meteo = cp.met_meteo(case.weather["path"], case.lat, case.lon, case.alt, case.tz)
        else:
            meteo = cp.pvgis_meteo(case.lat, case.lon, args.cache, "5.2")
        target_t = case.ref["steps"]["temperature"]
        target_w = case.ref["steps"]["ohmic"]
        module = cp.build_module(case.module, case.iam_profile)
        out.write("\n" + "=" * 100 + f"\nCASO {key}: passo di temperatura di PVsyst {target_t:+.2f} %, cavi DC {target_w:+.2f} % "
                  f"({case.losses['dc_wiring']:.1f} % a STC); efficienza STC del modulo {100 * module.efficiency:.2f} %\n")
        out.write("1. bilancio termico con una frazione dell'efficienza STC (PVsyst itera l'efficienza al punto di lavoro)\n")
        out.write(f"{'frazione':>10}{'eta usata %':>13}{'temperatura %':>15}{'scarto pt':>11}{'E_Grid MWh':>12}\n")
        try:
            for factor in (1.0, 0.95, 0.92, 0.88, 0.85):
                pvlib.temperature.pvsyst_cell = patched_cell(factor)
                r = cp.run(case, meteo, case.inverter["eta"])
                out.write(f"{factor:>10.2f}{100 * factor * module.efficiency:>13.2f}{r['steps']['temperature']:>+15.2f}"
                          f"{r['steps']['temperature'] - target_t:>+11.2f}{r['nodes']['e_grid'] / 1000:>12.1f}\n")
        finally:
            pvlib.temperature.pvsyst_cell = ORIGINAL
        # 2. the DC wiring loss on the hourly series of one simulation
        arrays = cp.build_arrays(case, module)
        a = arrays[0]
        kwargs = dict(case.losses)
        kwargs.setdefault("iam_b0", 0.05)
        losses = Losses(use_near=False, **kwargs)
        sim = simulate(meteo, arrays, InverterSpec("x", "x", pac=case.inverter["pac_total"], eta=case.inverter["eta"]),
                       losses, None)
        h = sim.hourly
        g = h.poa_eff.to_numpy()
        u_c, u_v = THERMAL[a.thermal]
        t_cell = np.asarray(ORIGINAL(h.poa.to_numpy(), h.temp_air.to_numpy(), meteo.data.wind_speed.to_numpy(), u_c=u_c,
                                     u_v=u_v, module_efficiency=module.efficiency, alpha_absorption=0.9))
        p_stc = sum(x.p_stc for x in arrays)
        r_stc = case.losses["dc_wiring"] / 100.0
        # Meridiana: p_dc = p_el (1 - r p_el / p_stc); p_el recovered from p_dc
        p_dc = h.p_dc.to_numpy()
        p_el = np.where(p_dc > 0, (1 - np.sqrt(np.clip(1 - 4 * r_stc * p_dc / p_stc, 0, None))) / (2 * r_stc / p_stc), 0.0)
        loss_power = (r_stc * p_el ** 2 / p_stc).sum()
        i_ratio = g / 1000.0 * (1 + module.alpha_isc / 100.0 * (t_cell - 25.0))
        loss_current = (r_stc * p_stc * i_ratio ** 2).sum()
        out.write("2. perdita nei cavi DC sulle stesse ore: con il rapporto di potenza (Meridiana) e con R I^2 (PVsyst)\n")
        out.write(f"   Meridiana r P^2/Pstc: {-100 * loss_power / p_el.sum():+.2f} %; R I^2 con la corrente dell'ora: "
                  f"{-100 * loss_current / p_el.sum():+.2f} %; PVsyst stampa {target_w:+.2f} %\n")
    text = out.getvalue()
    args.out.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
