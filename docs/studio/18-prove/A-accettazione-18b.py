"""The acceptance of task 18b, step 3 (keys per object, events per topic), measured on the window: on the
generated project of the architecture proofs (20 buildings, 40 sub-fields, 60 exclusions) a building renamed
must cost under 100 ms on the window's thread, lay out nothing and compute no year; a height changed must lay
out again only the sub-fields of that building. tests/test_speed.py checks the same offscreen with a wide
threshold; this script prints the numbers, for the proof on Daniel's PC with the real screen.

    python docs/studio/18-prove/A-accettazione-18b.py [<repo root>] > A-accettazione-18b-risultati.txt

Offscreen unless QT_QPA_PLATFORM says otherwise; no network (background "none"); nothing of the repository is
written (the project goes to a temporary folder).
"""

from __future__ import annotations

import os
import platform
import sys
import tempfile
import time
from pathlib import Path
from statistics import median

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("LANGUAGE", "en")
ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from _projects import generated  # noqa: E402

from meridiana import config  # noqa: E402
from meridiana.paths import Paths  # noqa: E402


def main() -> None:
    from unittest import mock

    from PySide6.QtWidgets import QApplication, QMessageBox

    from meridiana.ui.window import MainWindow

    app = QApplication.instance() or QApplication([])
    for name, answer in (("question", QMessageBox.StandardButton.Discard), ("information", QMessageBox.StandardButton.Ok),
                         ("warning", QMessageBox.StandardButton.Ok)):
        mock.patch.object(QMessageBox, name, side_effect=lambda *a, r=answer, **k: r).start()

    def wait_until(condition, seconds: float = 60.0) -> bool:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            app.processEvents()
            if condition():
                return True
            time.sleep(0.005)
        return condition()

    def settle(win) -> None:
        wait_until(lambda: not win.relayout_timer.isActive() and all(
            win.session.layout_state(sf) in ("ok", "error", "empty") for sf in win.project.subfields))
        for _ in range(5):
            app.processEvents()

    import PySide6
    print(f"python {platform.python_version()}, PySide6 {PySide6.__version__}, {platform.system()} {platform.release()}, "
          f"QT_QPA_PLATFORM={os.environ.get('QT_QPA_PLATFORM')}")
    root = Path(tempfile.mkdtemp())
    paths = Paths(config=root / "c", state=root / "s", data=root / "d", cache=root / "k")
    file = root / "generated.meridiana"
    p = generated(20, 2, 3)
    p.save(file)
    win = MainWindow(paths, config.Config(background="none"))
    win.resize(1400, 900)
    t = time.perf_counter()
    win.open_path(file)
    win.show()
    settle(win)
    modules = sum(r.count for r in win.results.values() if not isinstance(r, Exception))
    print(f"project of {len(p.buildings)} buildings, {len(p.subfields)} sub-fields, {len(p.exclusions)} exclusions: "
          f"opened, laid out ({modules} modules) and drawn in {(time.perf_counter() - t) * 1000:.0f} ms")

    print()
    print("== a building renamed (the measure: under 100 ms, no layout, no year)")
    bid = win.project.buildings[0].id
    win.energy = {"marker": True}
    computed = []
    win._compute_energy = lambda fetch=False: computed.append(fetch)
    job, generation = win.layout_job, win.generation
    times = []
    for k in range(5):
        t = time.perf_counter()
        win._edited("building", bid, {"name": f"Renamed {k}"})
        times.append((time.perf_counter() - t) * 1000)
        app.processEvents()
    print(f"   edit() of a name on the window's thread: median {median(times):.1f} ms "
          f"({', '.join(f'{x:.0f}' for x in times)})")
    print(f"   layout asked for: {win.relayout_timer.isActive() or win.layout_job is not job or win.generation != generation}")
    print(f"   year asked for: {bool(computed) or win.energy_timer.isActive()}")
    times = []
    for _ in range(5):
        t = time.perf_counter()
        win.undo.undo()
        app.processEvents()
        times.append((time.perf_counter() - t) * 1000)
        win.undo.redo()
        app.processEvents()
    print(f"   undo of a rename: median {median(times):.1f} ms; layout asked for: "
          f"{win.relayout_timer.isActive() or win.layout_job is not job}; year asked for: {bool(computed)}")
    del win._compute_energy
    win.energy = {}

    print()
    print("== a height changed (the measure: only the sub-fields of that building laid out again)")
    b = win.project.buildings[3]
    mine = sorted(sf.id for sf in win.project.subfields if sf.building == b.id)
    t = time.perf_counter()
    win._edited("building", b.id, {"height": 12.0})
    edited = (time.perf_counter() - t) * 1000
    settle(win)
    print(f"   edit() on the window's thread {edited:.0f} ms (plan, tree, properties, 3D at once); settled after "
          f"{(time.perf_counter() - t) * 1000:.0f} ms")
    print(f"   sub-fields laid out again: {sorted(win.layout_job.laid)} (the building's: {mine})")

    print()
    print("== the pieces, measured one by one")
    good = win.session.good_results()
    pieces = {
        "layout_key for every sub-field": lambda: [win.project.layout_key(sf) for sf in win.project.subfields],
        "session.energy_key()": lambda: win.session.energy_key(),
        "_show_tree": lambda: win._show_tree(),
        "_show_properties": lambda: win._show_properties(),
        "_show_energy_forms (arrays_of, obstacles once)": lambda: win._show_energy_forms(),
        "_show_3d": lambda: win._show_3d(),
        "_show_checks": lambda: win._show_checks(),
        "plan.show_project": lambda: win.plan.show_project(win.project, good),
    }
    for name, fn in pieces.items():
        out = []
        for _ in range(5):
            t = time.perf_counter()
            fn()
            out.append((time.perf_counter() - t) * 1000)
        print(f"   {name:48s} {median(out):8.1f} ms")
    win.close()
    win.deleteLater()
    app.processEvents()


if __name__ == "__main__":
    main()
