"""Where the energy job's time goes, measured without a profiler: `EnergyJob._compute` on a project, repeated,
with the main steps timed by wrapping their functions (a wrapper costs a microsecond, a profiler inflates every
Python call). Cold means the near-shading cache is emptied first (as after a change of the scene); warm means
it is kept (as after a change of the money or the losses).

Needs the project file and a PVGIS cache for its site, as profilo_energia.py: MERIDIANA_SAMPLE (default: Daniel's
"Prova capannone Rho") and MERIDIANA_CACHE (default: %LOCALAPPDATA%/Meridiana/cache); the cache is copied to a
temporary folder. Run with QT_QPA_PLATFORM=offscreen and PYTHONPATH=src:
    python docs/studio/18-prove/energia_tempo.py [--repeats 5] [--save-npz file]
`--save-npz` writes the hourly production and load of the project (kWh) for dispatch_varianti.py --data."""

from __future__ import annotations

import argparse
import functools
import os
import shutil
import statistics
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("PROBE_REPO", HERE.parents[2]))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(HERE))
from carico import CpuMeter  # noqa: E402

from meridiana import checks, model  # noqa: E402
from meridiana.energy import consumption as consumption_model  # noqa: E402
from meridiana.energy import economics, meteo, nearshade, pipeline, pvgis, stringing  # noqa: E402

SAMPLE = Path(os.environ.get("MERIDIANA_SAMPLE", r"C:\Users\utente\dev\meridiana-prove\Prova capannone Rho.meridiana"))
CACHE = Path(os.environ.get("MERIDIANA_CACHE") or Path(os.environ.get("LOCALAPPDATA", "")) / "Meridiana" / "cache")

STATS: dict = defaultdict(list)         # (kind, label) -> the seconds of every call
KIND = {"now": "warm"}                  # "cold" or "warm": which run is on


def timed(owner, name: str, label: str) -> None:
    orig = getattr(owner, name)

    @functools.wraps(orig)
    def wrapper(*a, **k):
        t = time.perf_counter()
        try:
            return orig(*a, **k)
        finally:
            STATS[(KIND["now"], label)].append(time.perf_counter() - t)
    setattr(owner, name, wrapper)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--repeats", type=int, default=5)
    p.add_argument("--save-npz", default=None)
    args = p.parse_args()
    root = Path(tempfile.mkdtemp(prefix="meridiana-energy-"))
    shutil.copytree(CACHE / "pvgis", root / "cache" / "pvgis")
    project, _n = model.Project.load(SAMPLE)
    results = {sf.id: project.fill(sf) for sf in project.subfields if sf.filled}
    print(f"project {SAMPLE.name}: {sum(len(r.modules) for r in results.values())} modules, "
          f"{len(project.exclusions)} exclusions, {len(project.buildings)} buildings")
    import pvlib
    timed(pipeline, "simulate", "simulate (the hourly year)")
    if hasattr(pipeline, "with_strings"):
        timed(pipeline, "with_strings", "simulate.with_strings (the electrical effect, downstream)")
    timed(pvlib.solarposition, "get_solarposition", "pvlib solar position (SPA), in simulate")
    timed(pvlib.irradiance, "get_total_irradiance", "pvlib transposition (Perez), in simulate")
    timed(pvlib.shading, "shaded_fraction1d", "pvlib row shading, in simulate")
    timed(pvlib.bifacial.infinite_sheds, "get_irradiance_poa", "pvlib infinite sheds (ground), in simulate")
    timed(nearshade, "cached_shading", "nearshade.cached_shading (hash and table)")
    timed(nearshade, "shading", "nearshade.shading (the table itself)")
    timed(nearshade, "electrical", "nearshade.electrical")
    timed(economics, "dispatch", "economics.dispatch (all calls)")
    timed(economics, "evaluate", "economics.evaluate (all 17 calls)")
    timed(economics, "sizing", "economics.sizing (9 sizes)")
    timed(economics, "storage_sizing", "economics.storage_sizing (7 batteries)")
    timed(checks, "count_out_of_shadows", "checks.count_out_of_shadows (a layout)")
    timed(pvgis, "pvcalc", "pvgis.pvcalc (cache)")
    timed(stringing, "assign", "stringing.assign")
    timed(stringing, "suggest", "stringing.suggest")
    timed(consumption_model, "build", "consumption.build")
    timed(meteo, "typical_year", "meteo.typical_year (cache read)")
    timed(meteo, "horizon", "meteo.horizon (cache read)")
    # the energy job's work, as the window's EnergyJob runs it (energy/pipeline.py since task 18b)
    def compute() -> dict:
        return pipeline.compute_or_say(project, results, root / "cache", False).as_dict()
    out = compute()                                        # imports and caches warmed up
    if args.save_npz:
        np.savez(args.save_npz, prod=out["sim"].hourly.e_kwh.to_numpy(), cons=out["load"].hourly.to_numpy())
        print("saved", args.save_npz)
    econ_dispatch_calls = len(STATS[("warm", "economics.dispatch (all calls)")])
    STATS.clear()
    meter = CpuMeter().start()
    totals = {"cold": [], "warm": []}
    for _ in range(args.repeats):
        for kind in ("cold", "warm"):
            if kind == "cold":
                with nearshade._CACHE_LOCK:
                    nearshade._CACHE.clear()
            KIND["now"] = kind
            t = time.perf_counter()
            compute()
            totals[kind].append(time.perf_counter() - t)
    busy = meter.stop()
    print(f"CPU busy during the measurement: {busy:.0f}% over {meter.seconds:.0f} s; repeats {args.repeats}")
    for kind in ("cold", "warm"):
        s = sorted(totals[kind])
        print(f"EnergyJob._compute {kind}: median {statistics.median(s):.2f} s (min {s[0]:.2f}, max {s[-1]:.2f})")
    for kind in ("cold", "warm"):
        print(f"\nsteps of a {kind} run, summed over the run (mean over {args.repeats} runs; nested steps are "
              f"counted in their parents too):")
        rows = sorted(((sum(v) / args.repeats, len(v) / args.repeats, k[1]) for k, v in STATS.items() if k[0] == kind),
                      reverse=True)
        for total, n, k in rows:
            print(f"  {k:48s} {total * 1e3:8.1f} ms  {n:6.1f} calls a run")
    print(f"\ndispatch is called {econ_dispatch_calls} times a run: "
          f"{'with' if economics.Battery.from_settings(economics.Settings.from_dict(project.economics)) else 'without'} "
          f"a battery in the project")


if __name__ == "__main__":
    main()
