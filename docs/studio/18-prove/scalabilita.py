"""How Meridiana scales with the number of modules: generated projects of about 1,000, 5,000 and 20,000 modules
(a flat roof with a parapet and roof plant, a ground field of tilted rows), and for each the time and the memory
of the layout (Project.fill), the near-shading table (nearshade.shading, uncached), the 3D mesh and instance
table (mesh.building_triangles, mesh.module_table), the plan's scene (PlanView.show_project offscreen: items
made, time; and what one pick under the pointer costs), the energy job (EnergyJob._compute, cold and warm), the
file (save, load) and the window opening the file until it is idle.

    QT_QPA_PLATFORM=offscreen PYTHONPATH=src python docs/studio/18-prove/scalabilita.py [--sizes 1000,5000,20000]
        [--repeats 5] [--skip-energy] [--skip-window]

Memory: tracemalloc's peak (Python and numpy allocations; shapely's GEOS objects and Qt's items are not seen by it)
and the process' working set before and after, from the OS. Needs the PVGIS cache of the site (the Rho
coordinates of probe.py's big_project): MERIDIANA_CACHE, default %LOCALAPPDATA%/Meridiana/cache."""
# ruff: noqa: B023  (the lambdas run inside the same loop step that binds their names)

from __future__ import annotations

import argparse
import ctypes
import gc
import json
import os
import shutil
import statistics
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("PROBE_REPO", HERE.parents[2]))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(HERE))
from carico import CpuMeter  # noqa: E402

CACHE = Path(os.environ.get("MERIDIANA_CACHE") or Path(os.environ.get("LOCALAPPDATA", "")) / "Meridiana" / "cache")


def working_set_mb() -> float:
    """The process' resident memory now, in MB (Windows: the working set; Linux: VmRSS)."""
    if sys.platform == "win32":
        class Counters(ctypes.Structure):
            _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        c = Counters()
        c.cb = ctypes.sizeof(c)
        kernel32 = ctypes.windll.kernel32
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        fn = kernel32.K32GetProcessMemoryInfo
        fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
        fn.restype = ctypes.c_int
        if not fn(kernel32.GetCurrentProcess(), ctypes.byref(c), c.cb):
            return float("nan")
        return c.WorkingSetSize / 2 ** 20
    with open("/proc/self/status", encoding="ascii") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return float(line.split()[1]) / 1024.0
    return float("nan")


def measure(fn, repeats: int):
    """fn() `repeats` times: (median seconds, samples, tracemalloc peak MB of the first run, RSS delta MB of the
    first run, the result of the last run)."""
    gc.collect()
    rss0 = working_set_mb()
    tracemalloc.start()
    t = time.perf_counter()
    out = fn()
    samples = [time.perf_counter() - t]
    _cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss1 = working_set_mb()
    for _ in range(repeats - 1):
        t = time.perf_counter()
        out = fn()
        samples.append(time.perf_counter() - t)
    return statistics.median(samples), samples, peak / 2 ** 20, rss1 - rss0, out


def project_for(target: int):
    """A project of about `target` modules: a flat roof (parapet, three roof plants) with tilted rows, and a ground
    field of tilted rows in pairs (as probe.py's big_project, sized to the target). The roof takes a third of the
    modules, the ground field the rest; the sides follow from the module density of each layout."""
    from meridiana import model
    p = model.Project(name=f"Scala {target}")
    p.site = model.Site(lat=45.5226, lon=9.0300, address="Rho, Città metropolitana di Milano, Lombardia, Italia")
    # roof: 1,394 modules on 120 x 60 m measured on 22/10 (0.194 modules per m2); ground: 3,288 on 160 x 120 m (0.171)
    roof_area = target / 3.0 / 0.194
    ground_area = target * 2.0 / 3.0 / 0.171
    w, h = (roof_area * 2.0) ** 0.5, (roof_area / 2.0) ** 0.5
    gw, gh = (ground_area * 4.0 / 3.0) ** 0.5, (ground_area * 3.0 / 4.0) ** 0.5
    b = model.Building(id="b1", name="Capannone", footprint=[[0, 0], [w, 0], [w, h], [0, h]], height=10.0, parapet=1.0)
    p.buildings.append(b)
    p.subfields.append(model.SubField(id="s1", name="Copertura", ring=[[1, 1], [w - 1, 1], [w - 1, h - 1], [1, h - 1]],
                                      building="b1", params={"mounting": "tilted_anchored", "tilt": 15.0}, filled=True))
    y0 = h + 20.0
    p.subfields.append(model.SubField(id="s2", name="Campo a terra", ring=[[0, y0], [gw, y0], [gw, y0 + gh], [0, y0 + gh]],
                                      building=None, params={"mounting": "ground", "tilt": 25.0, "stack": 2}, filled=True))
    for i, (fx, fy) in enumerate(((0.25, 0.33), (0.5, 0.58), (0.75, 0.25))):
        x, y = fx * w, fy * h
        p.exclusions.append(model.ExclusionItem(id=f"e{i + 1}", ring=[[x, y], [x + 4, y], [x + 4, y + 3], [x, y + 3]],
                                                kind="plant", building="b1"))
    return p


def stub_3d(window_module) -> None:
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import QWidget

    class Stub(QWidget):
        modulePicked = Signal(int)
        buildingPicked = Signal()
        failed = Signal(str)

        def show_scene(self, *a, **k):
            pass

        def fit(self):
            pass

        def set_sun(self, *a):
            pass
    window_module.View3D = Stub


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="1000,5000,20000")
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--skip-energy", action="store_true")
    ap.add_argument("--skip-window", action="store_true")
    ap.add_argument("--no3d", action="store_true", help="the window opened with a stub 3D view")
    ap.add_argument("--json", default=None, help="write every number here too")
    args = ap.parse_args()
    from PySide6.QtCore import QPointF
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(["scalabilita"])
    from meridiana import config, mesh, model
    from meridiana.energy import nearshade, system
    from meridiana.paths import Paths
    from meridiana.ui import plan as plan_module
    from meridiana.ui import window
    root = Path(tempfile.mkdtemp(prefix="meridiana-scala-"))
    if (CACHE / "pvgis").exists():
        shutil.copytree(CACHE / "pvgis", root / "cache" / "pvgis")
    results_all = {}
    meter = CpuMeter().start()
    for target in (int(s) for s in args.sizes.split(",")):
        rep = args.repeats if target <= 5000 else max(2, min(args.repeats, 3))
        p = project_for(target)
        row: dict = {"target": target, "repeats": rep}
        print(f"\n=== project of about {target} modules (repeats {rep})")
        # 1. the layout
        t_fill, s_fill, peak, rss, results = measure(lambda: {sf.id: p.fill(sf) for sf in p.subfields}, rep)
        n = sum(r.count for r in results.values())
        counts = {k: v.count for k, v in results.items()}
        row.update(modules=n, per_subfield=counts, fill_s=t_fill, fill_samples=s_fill, fill_peak_mb=peak, fill_rss_mb=rss)
        print(f"  modules laid: {n} {counts}")
        print(f"  Project.fill (both sub-fields): median {t_fill:.3f} s (min {min(s_fill):.3f}, max {max(s_fill):.3f}); "
              f"tracemalloc peak {peak:.1f} MB, working set +{rss:.1f} MB")
        # 2. the near-shading table, uncached, for every array (as simulate does, once per energy run of a new scene)
        arrays = system.arrays_of(p, results)
        import numpy as np
        # the sun's path of the site over the year, as simulate reads it (every hour; here from pvlib directly)
        import pandas as pd
        import pvlib
        idx = pd.date_range("1990-01-01", periods=8760, freq="h", tz="UTC")
        pos = pvlib.solarposition.get_solarposition(idx, p.site.lat, p.site.lon)
        needed = nearshade.needed_cells(pos.azimuth.to_numpy(), 90.0 - pos.apparent_zenith.to_numpy())

        def shade_all():
            out = []
            for a in arrays:
                layout = nearshade.blocks_of(a.module.cells, a.module.diodes, a.module.twin)
                out.append(nearshade.shading(a.placed, a.obstacles, a.tilt, a.azimuth, needed, layout))
            return out
        t_sh, s_sh, peak, rss, shadings = measure(shade_all, rep)
        row.update(arrays=len(arrays), obstacles=len(arrays[0].obstacles) if arrays else 0, shading_s=t_sh,
                   shading_samples=s_sh, shading_peak_mb=peak, shading_rss_mb=rss,
                   shading_table_mb=sum(s.modules.nbytes + s.blocks.nbytes for s in shadings if s.modules is not None) / 2 ** 20)
        print(f"  nearshade.shading, {len(arrays)} arrays x {row['obstacles']} solids, {int(needed.sum())} cells: "
              f"median {t_sh:.3f} s (min {min(s_sh):.3f}, max {max(s_sh):.3f}); tracemalloc peak {peak:.1f} MB, "
              f"per-module tables {row['shading_table_mb']:.1f} MB")
        # 3. the 3D mesh and the instance table
        def mesh_all():
            parts = [mesh.building_triangles(b.footprint, b.pitches()) for b in p.buildings]
            parts += [mesh.prism_triangles(o["ring"], o["z0"], o["z1"]) for o in p.obstacle_prisms()]
            tables = []
            for sf in p.subfields:
                r = results[sf.id]
                m = p.module_of(sf)
                pr = sf.layout_params()
                along, across = (m.width, m.length) if pr.portrait else (m.length, m.width)
                tables.append(mesh.module_table(r.modules, along, across))
            return parts, np.concatenate(tables)
        t_mesh, s_mesh, peak, rss, (parts, table) = measure(mesh_all, rep)
        row.update(mesh_s=t_mesh, mesh_samples=s_mesh, mesh_peak_mb=peak, table_rows=int(len(table)))
        print(f"  mesh.building_triangles + prisms + module_table ({len(table)} rows): median {t_mesh:.3f} s "
              f"(min {min(s_mesh):.3f}, max {max(s_mesh):.3f})")
        # 4. the plan's scene, offscreen
        view = plan_module.PlanView(root / "cache")
        view.set_source("none")
        view.resize(1400, 900)
        view.show()
        app.processEvents()
        # every item drawn again (the first time, or new colours), then the draw a change of the project asks for
        # while the layouts in hand are the same (their modules kept, task 18c, step 8)
        t_plan, s_plan, peak, rss, _ = measure(lambda: view.show_project(p, results, force=True), rep)
        t_same, s_same, _pk, _r, _ = measure(lambda: view.show_project(p, results), rep)
        items = len(view.scene().items())
        view.fit()
        app.processEvents()
        # a pick in the middle of the ground field: what every mouse move costs in the Select tool
        sf2 = p.subfields[1]
        xs = [q[0] for q in sf2.ring]
        ys = [q[1] for q in sf2.ring]
        centre = plan_module.to_scene((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
        t_pick, s_pick, _pk, _r, hit = measure(lambda: view._pick(QPointF(centre)), rep * 4)
        # a mouse move over the view (the Select tool: _update_cursor picks and outlines what is under the pointer)
        t_move, s_move, _pk, _r, _ = measure(lambda: view._update_cursor(view.mapFromScene(centre)), rep * 4)
        row.update(plan_s=t_plan, plan_samples=s_plan, plan_same_s=t_same, plan_items=items, plan_peak_mb=peak,
                   plan_rss_mb=rss, pick_ms=1e3 * t_pick, pick_hit=hit[0], move_ms=1e3 * t_move)
        print(f"  PlanView.show_project: median {t_plan:.3f} s (min {min(s_plan):.3f}, max {max(s_plan):.3f}); "
              f"{items} graphics items; working set +{rss:.1f} MB; again with the same layouts median {t_same:.3f} s")
        print(f"  PlanView._pick over the ground field: median {1e3 * t_pick:.1f} ms (hit {hit[0]!r}); "
              f"_update_cursor (one mouse move, Select): median {1e3 * t_move:.1f} ms")
        view.close()
        view.deleteLater()
        app.processEvents()
        # 5. the energy job, cold (shading computed) and warm (shading cached)
        if not args.skip_energy:
            from meridiana.energy import pipeline

            def compute():           # the energy job's work (energy/pipeline.py since task 18b)
                return pipeline.compute_or_say(p, results, root / "cache", False).as_dict()

            def energy_cold():
                with nearshade._CACHE_LOCK:
                    nearshade._CACHE.clear()
                return compute()
            e_rep = max(2, min(rep, 3)) if target >= 20000 else rep
            t_cold, s_cold, peak, rss, out = measure(energy_cold, e_rep)
            t_warm, s_warm, _pk, _r, out = measure(compute, e_rep)
            row.update(energy_cold_s=t_cold, energy_cold_samples=s_cold, energy_warm_s=t_warm,
                       energy_warm_samples=s_warm, energy_peak_mb=peak, energy_rss_mb=rss,
                       energy_error=out.get("error_sim", ""), energy_kwh=getattr(out.get("sim"), "energy_kwh", None))
            said = ("error: " + out["error_sim"]) if out.get("error_sim") else f"{out['sim'].energy_kwh:,.0f} kWh"
            print(f"  EnergyJob._compute cold: median {t_cold:.2f} s (min {min(s_cold):.2f}, max {max(s_cold):.2f}); "
                  f"warm: median {t_warm:.2f} s (min {min(s_warm):.2f}, max {max(s_warm):.2f}); tracemalloc peak "
                  f"{peak:.0f} MB; working set +{rss:.0f} MB; {said}")
        # 6. the file
        file = root / f"scala-{target}.meridiana"
        t_save, s_save, _pk, _r, _ = measure(lambda: p.save(file), rep)
        t_load, s_load, _pk, _r, _ = measure(lambda: model.Project.load(file), rep)
        row.update(file_kb=file.stat().st_size / 1024.0, save_s=t_save, load_s=t_load)
        print(f"  file: {file.stat().st_size / 1024:.1f} kB; save median {1e3 * t_save:.1f} ms, load median "
              f"{1e3 * t_load:.1f} ms (the modules are not in the file: opening lays them out again)")
        # 7. the window opening the file until idle (layout job, plan, 3D, checks), as the designer sees it
        if not args.skip_window:
            if args.no3d:
                stub_3d(window)
            paths = Paths(config=root / "config", state=root / "state", data=root / "data", cache=root / "cache")
            cfg = config.Config(background="none", check_updates=False)
            opens = []
            for _ in range(max(2, min(rep, 3))):
                win = window.MainWindow(paths, cfg)
                win.resize(1600, 900)
                win.show()
                app.processEvents()
                t = time.perf_counter()
                win.open_path(file)
                app.processEvents()
                sync = time.perf_counter() - t

                def idle():
                    return (win.pool.activeThreadCount() == 0 and not win.relayout_timer.isActive()
                            and not win.energy_timer.isActive())
                deadline = time.perf_counter() + 300
                while time.perf_counter() < deadline:
                    app.processEvents()
                    if idle():
                        break
                app.processEvents()
                opens.append((sync, time.perf_counter() - t))
                win.undo.setClean()
                win.saved_state = win._state_key()
                win.close()
                win.deleteLater()
                app.processEvents()
            row.update(open_sync_s=statistics.median(o[0] for o in opens), open_idle_s=statistics.median(o[1] for o in opens),
                       open_samples=opens)
            print(f"  window: open_path returns after median {1e3 * row['open_sync_s']:.0f} ms, idle after median "
                  f"{row['open_idle_s']:.2f} s ({len(opens)} runs, 3D {'stub' if args.no3d else 'real'})")
        results_all[target] = row
        gc.collect()
    busy = meter.stop()
    print(f"\nCPU busy during the whole run: {busy:.0f}% over {meter.seconds:.0f} s")
    if args.json:
        Path(args.json).write_text(json.dumps(results_all, indent=1, default=str), encoding="utf-8")
        print("written", args.json)


if __name__ == "__main__":
    main()
