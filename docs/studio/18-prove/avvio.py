"""How long Meridiana takes to start, offscreen: the imports, the main window built, shown and painted, a project
opened and the window idle again (layout done, 3D and checks drawn). Each measurement is a fresh process (the
imports are paid once a process), run `--runs` times; the medians are printed by the parent.

    QT_QPA_PLATFORM=offscreen python docs/studio/18-prove/avvio.py [--runs 5] [--project file] [--no3d]

Settings, state and cache are copies in a temporary folder, the background is "none" (no tiles, no network) so
that the number is the program's own. `--no3d` replaces the 3D view with a stub, as probe.py does, to tell what Qt
Quick 3D costs at the start."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("PROBE_REPO", HERE.parents[2]))
SAMPLE = Path(os.environ.get("MERIDIANA_SAMPLE", r"C:\Users\utente\dev\meridiana-prove\Prova capannone Rho.meridiana"))
CACHE = Path(os.environ.get("MERIDIANA_CACHE") or Path(os.environ.get("LOCALAPPDATA", "")) / "Meridiana" / "cache")


def child(project: Path, no3d: bool) -> None:
    """One start, timed step by step; the result as one JSON line on stdout."""
    t0 = time.perf_counter()
    sys.path.insert(0, str(REPO / "src"))
    from PySide6.QtWidgets import QApplication
    t_qt = time.perf_counter()
    import meridiana.ui.window as window  # noqa: F401  (pulls numpy, pandas, shapely, matplotlib, the pages)
    from meridiana import config
    from meridiana.paths import Paths
    t_imports = time.perf_counter()
    app = QApplication(["avvio"])
    root = Path(tempfile.mkdtemp(prefix="meridiana-avvio-"))
    if (CACHE / "pvgis").exists():
        shutil.copytree(CACHE / "pvgis", root / "cache" / "pvgis")
    paths = Paths(config=root / "config", state=root / "state", data=root / "data", cache=root / "cache")
    cfg = config.Config(background="none", check_updates=False)
    if no3d:
        from PySide6.QtCore import QObject, Signal
        from PySide6.QtWidgets import QWidget

        class StubBackend(QObject):
            menuRequested = Signal(float, float)

            def __init__(self, parent=None):
                super().__init__(parent)
                self.reduced_motion = False
                self.selection_centre = None
                self.user_moved = False
                self._press = None
                self.scene = None

            def frame(self, *a, **k):
                pass

        class Quiet:
            def __getattr__(self, name):
                return lambda *a, **k: None

        class Stub(QWidget):
            """The 3D view's surface without Qt Quick 3D: what the window asks of it, answered with nothing."""
            modulePicked = Signal(int)
            buildingPicked = Signal()
            pointPicked = Signal(float, float)
            hoverPicked = Signal(tuple)
            failed = Signal(str)

            def __init__(self, parent=None):
                super().__init__(parent)
                self.backend = StubBackend(self)
                self.cube = Quiet()
                self.marks = Quiet()
                self.viewbar = None

            def show_scene(self, *a, **k):
                pass

            def fit(self):
                pass

            def set_sun(self, *a):
                pass

            def set_navigation(self, *a):
                pass

            def set_outline(self, *a):
                pass
        window.View3D = Stub
    t1 = time.perf_counter()
    win = window.MainWindow(paths, cfg)
    t_window = time.perf_counter()
    win.resize(1600, 900)
    win.show()
    app.processEvents()
    app.processEvents()
    t_shown = time.perf_counter()
    win.open_path(project)
    app.processEvents()
    t_open_sync = time.perf_counter()

    def idle():
        return (win.pool.activeThreadCount() == 0 and not win.relayout_timer.isActive()
                and not win.energy_timer.isActive())
    deadline = time.perf_counter() + 60
    while time.perf_counter() < deadline:
        app.processEvents()
        if idle():
            break
    t_idle = time.perf_counter()
    app.processEvents()
    out = {"qt_import_ms": 1e3 * (t_qt - t0), "meridiana_imports_ms": 1e3 * (t_imports - t_qt),
           "window_build_ms": 1e3 * (t_window - t1), "show_and_paint_ms": 1e3 * (t_shown - t_window),
           "open_sync_ms": 1e3 * (t_open_sync - t_shown), "open_to_idle_ms": 1e3 * (t_idle - t_shown),
           "total_to_idle_ms": 1e3 * (t_idle - t0),
           "modules": sum(getattr(r, "count", 0) for r in win.results.values())}
    win.undo.setClean()
    win.saved_state = win._state_key()
    win.close()
    print("RESULT " + json.dumps(out))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--runs", type=int, default=5)
    p.add_argument("--project", default=str(SAMPLE))
    p.add_argument("--no3d", action="store_true")
    p.add_argument("--child", action="store_true")
    args = p.parse_args()
    if args.child:
        child(Path(args.project), args.no3d)
        return
    sys.path.insert(0, str(HERE))
    from carico import CpuMeter
    meter = CpuMeter().start()
    rows = []
    for i in range(args.runs):
        cmd = [sys.executable, str(Path(__file__).resolve()), "--child", "--project", args.project]
        if args.no3d:
            cmd.append("--no3d")
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, encoding="utf-8", errors="replace")
        line = next((ln for ln in r.stdout.splitlines() if ln.startswith("RESULT ")), None)
        if line is None:
            print(f"run {i + 1}: no result\n{r.stdout[-2000:]}\n{r.stderr[-3000:]}")
            continue
        rows.append(json.loads(line[7:]))
        print(f"run {i + 1}: " + ", ".join(f"{k} {v:.0f}" for k, v in rows[-1].items() if k != "modules"))
    busy = meter.stop()
    print(f"\nCPU busy during the runs: {busy:.0f}%; {len(rows)} runs; project {Path(args.project).name} "
          f"({rows[0]['modules'] if rows else '?'} modules); 3D {'stub' if args.no3d else 'real'}; offscreen")
    for k in rows[0]:
        if k == "modules":
            continue
        s = sorted(r[k] for r in rows)
        print(f"  {k:22s} median {statistics.median(s):7.0f} ms  (min {s[0]:.0f}, max {s[-1]:.0f})")


if __name__ == "__main__":
    main()
