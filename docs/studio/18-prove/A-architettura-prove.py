"""Proofs for theme A of the complete review (architecture and data model): the cost of the undo by
snapshots, of the dirty key and of the layout keys on a generated project; the behaviour of edit() when a
change raises; the energy job scheduled after an edit that changes nothing of the layout; the file format
and the settings with damaged input; the keys of the modules taken out by hand; the roof model on an L.

Runs offscreen (QT_QPA_PLATFORM=offscreen), without the network (background "none"), on a copy of the
project kept in a temporary folder. Nothing of the repository is written.

    python prove_A.py <repo root> > A-architettura-risultati.txt
"""
# ruff: noqa: B023  (the lambdas run inside the same loop step that binds their names)

from __future__ import annotations

import base64
import copy
import json
import os
import platform
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
from statistics import median

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("LANGUAGE", "en")
ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("C:/Users/utente/dev/meridiana-lavoro")
sys.path.insert(0, str(ROOT / "src"))

from meridiana import config, layout, model, roofs  # noqa: E402


def timed(fn, repeat: int = 5):
    """Median wall time of fn() in milliseconds, over `repeat` runs."""
    out = []
    for _ in range(repeat):
        t = time.perf_counter()
        fn()
        out.append((time.perf_counter() - t) * 1000)
    return median(out)


def generated(n_buildings: int, subfields_per_building: int, exclusions_per_building: int,
              image_kb: int = 0) -> model.Project:
    """A project of n_buildings rectangles 40 x 20 m in a grid, each with its sub-fields (tilted rows, filled)
    and exclusions, and an image under the drawing of image_kb kilobytes (random bytes, never decoded)."""
    p = model.Project(name="Generated")
    p.site = model.Site(lat=45.5226, lon=9.0300, address="Rho (MI), Lombardia")
    for k in range(n_buildings):
        x0, y0 = (k % 5) * 50.0, (k // 5) * 30.0
        b = model.Building(id=p.new_id("b"), name=f"Building {k + 1}",
                           footprint=[[x0, y0], [x0 + 40, y0], [x0 + 40, y0 + 20], [x0, y0 + 20]], height=8.0)
        p.buildings.append(b)
        width = 38.0 / subfields_per_building
        for j in range(subfields_per_building):
            sx = x0 + 1 + j * width
            p.subfields.append(model.SubField(id=p.new_id("s"), name=f"Sub-field {k + 1}.{j + 1}",
                                              ring=[[sx, y0 + 1], [sx + width - 0.5, y0 + 1],
                                                    [sx + width - 0.5, y0 + 19], [sx, y0 + 19]],
                                              building=b.id, pitch=0, params={"tilt": 15.0}, filled=True))
        for j in range(exclusions_per_building):
            ex = x0 + 5 + j * 6
            p.exclusions.append(model.ExclusionItem(id=p.new_id("e"), ring=[[ex, y0 + 9], [ex + 1.5, y0 + 9],
                                                                          [ex + 1.5, y0 + 10.5], [ex, y0 + 10.5]],
                                                    kind="skylight", building=b.id))
    if image_kb:
        from meridiana.underlay import Underlay
        data = base64.b64encode(os.urandom(image_kb * 1024)).decode("ascii")
        p.underlays.append(Underlay(id=p.new_id("u"), name="plan.png", image=data, width=2000, height=1500))
    return p


def section(title: str) -> None:
    print()
    print(f"== {title}")


def part_core() -> None:
    section("environment")
    import numpy
    import pandas
    import PySide6
    print(f"python {platform.python_version()}, PySide6 {PySide6.__version__}, numpy {numpy.__version__}, "
          f"pandas {pandas.__version__}, {platform.system()} {platform.release()}, "
          f"QT_QPA_PLATFORM={os.environ.get('QT_QPA_PLATFORM')}")

    section("A3 undo: cost of the snapshots without the window")
    for label, p in (("small: 1 building, 1 sub-field, 2 exclusions", generated(1, 1, 2)),
                     ("large: 20 buildings, 40 sub-fields, 60 exclusions", generated(20, 2, 3)),
                     ("large + image 4 MB (base64 5.4 MB)", generated(20, 2, 3, image_kb=4096))):
        data = p.to_json()
        print(f"-- {label}: project JSON {len(json.dumps(data)) / 1024:.0f} kB")
        snap = timed(lambda: copy.deepcopy(p.to_json()))
        before, after = copy.deepcopy(p.to_json()), copy.deepcopy(p.to_json())
        cmp = timed(lambda: before != after)
        restore = timed(lambda: model.Project.from_json(copy.deepcopy(before)))
        state_key = timed(lambda: json.dumps(p.to_json() | {"modified": None}, sort_keys=True))
        keys = timed(lambda: [p.layout_key(sf) for sf in p.subfields])
        print(f"   snapshot() [deepcopy(to_json)]       {snap:8.2f} ms  (edit() does it twice)")
        print(f"   before != after                      {cmp:8.2f} ms")
        print(f"   restore [from_json(deepcopy)]        {restore:8.2f} ms")
        print(f"   state key [json.dumps sorted, whole] {state_key:8.2f} ms  (_state_key trims the image)")
        print(f"   layout_key for every sub-field       {keys:8.2f} ms  ({len(p.subfields)} sub-fields; "
              f"_show_tree and _show_properties pay it at each redraw)")
        tracemalloc.start()
        kept = [(copy.deepcopy(p.to_json()), copy.deepcopy(p.to_json())) for _ in range(20)]
        current, _peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(f"   memory of one undo step (before + after, Python objects): {current / 20 / 1024:.0f} kB; "
              f"an unlimited QUndoStack keeps every step")
        del kept

    section("A4 file format: what from_json does with damaged or old input")
    cases = {
        "no 'version' key": {"format": "meridiana-project"},
        "version 0 (older than any migration)": {"format": "meridiana-project", "version": 0},
        "a building without name and footprint": {"format": "meridiana-project", "version": 6,
                                                  "buildings": [{"id": "b1"}]},
        "a sub-field whose ring is a number": {"format": "meridiana-project", "version": 6,
                                               "subfields": [{"id": "s1", "name": "x", "ring": 5}]},
        "buildings is a dict, not a list": {"format": "meridiana-project", "version": 6, "buildings": {"id": "b1"}},
        "site latitude is text": {"format": "meridiana-project", "version": 6, "site": {"lat": "north"}},
        "variants without the one in hand": {"format": "meridiana-project", "version": 6,
                                             "variants": [{"id": "v9", "name": "x"}], "variant": "v1"},
        "a newer format (7)": {"format": "meridiana-project", "version": 7},
    }
    for label, data in cases.items():
        try:
            p = model.Project.from_json(data)
            # what the window does next with such a project: layout of the first sub-field, pitches
            extra = ""
            try:
                for sf in p.subfields:
                    p.fill(sf)
                for b in p.buildings:
                    b.pitches()
                if isinstance(p.site.lat, str):
                    p.layout_key(p.subfields[0]) if p.subfields else None
                    float(p.site.lat)
            except Exception as later:  # noqa: BLE001 (a proof: every error is reported)
                extra = f"; later {type(later).__name__}: {later}"
            print(f"   {label}: accepted{extra}")
        except Exception as error:  # noqa: BLE001 (a proof: every error is reported)
            caught = "caught by open_path" if isinstance(error, (OSError, ValueError)) else \
                "NOT caught by open_path (OSError, ValueError only)"
            print(f"   {label}: {type(error).__name__}: {error} -> {caught}")

    section("A4 settings: a float field is not type-checked")
    cfg = config.Config.from_json({"version": config.CONFIG_VERSION, "veil": "forty percent"})
    print(f"   veil='forty percent' accepted by Config.from_json: veil={cfg.veil!r}")
    try:
        from meridiana import view_colours
        view_colours.veil(cfg.veil)
        print("   view_colours.veil(cfg.veil): fine")
    except Exception as error:  # noqa: BLE001
        print(f"   view_colours.veil(cfg.veil) -> {type(error).__name__}: {error} (the window sets it at start)")
    try:
        config.Config.from_json({"version": config.CONFIG_VERSION, "accent": 12})
        print("   accent=12 (a str field): accepted")
    except ValueError as error:
        print(f"   accent=12 (a str field): refused, {error} (bool, int and str fields are checked; float is not)")

    section("A5 layout: the keys of the modules taken out by hand")
    area = [(0, 0), (30, 0), (30, 20), (0, 20)]
    base = layout.compute(area, layout.Surface(), layout.Module(), layout.Params(tilt=15.0))
    taken = base.modules[7].key
    centre_before = base.modules[7].centre
    removed = layout.compute(area, layout.Surface(), layout.Module(), layout.Params(tilt=15.0), removed={taken})
    print(f"   base layout {base.count} modules; key {taken!r} at {tuple(round(c, 2) for c in centre_before)} "
          f"taken out -> {removed.count} modules")
    wider = layout.compute(area, layout.Surface(), layout.Module(), layout.Params(tilt=15.0, gap=0.10), removed={taken})
    base_wider = layout.compute(area, layout.Surface(), layout.Module(), layout.Params(tilt=15.0, gap=0.10))
    gone = [m for m in base_wider.modules if m.key == taken][0]
    print(f"   after gap 0.02 -> 0.10 the same key {taken!r} is the module at "
          f"{tuple(round(c, 2) for c in gone.centre)}: moved by {abs(gone.centre[0] - centre_before[0]):.2f} m "
          f"along the row; {base_wider.count} -> {wider.count} modules (the hole moved with the key)")

    section("A5 roofs: a gable on an L-shaped footprint (roofs.py on the minimum rectangle)")
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    L = [(0, 0), (20, 0), (20, 8), (8, 8), (8, 18), (0, 18)]
    pitches, exact = roofs.gable(L, 6.0, 20.0)
    cover = unary_union([Polygon(pt.ring) for pt in pitches])
    foot = Polygon(L)
    print(f"   footprint {foot.area:.0f} m2; two pitches cover {cover.area:.0f} m2, of which "
          f"{cover.difference(foot).area:.0f} m2 outside the footprint; exact={exact}")
    corner = (8.0, 8.0)
    inner = [pt.z(*corner) for pt in pitches]
    print(f"   at the inner corner (8, 8) the pitches stand at {[round(z, 2) for z in inner]} m with the eave at 6 m: "
          f"no valley, the roof hangs over the void")
    hips, _exact = roofs.hip(L, 6.0, 20.0)
    cover = unary_union([Polygon(pt.ring) for pt in hips])
    print(f"   hip: {len(hips)} pitches cover {cover.area:.0f} m2, {cover.difference(foot).area:.0f} m2 outside")


def part_window() -> None:
    from unittest import mock

    from PySide6.QtWidgets import QApplication, QMessageBox

    from meridiana.paths import Paths
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
        """Every layout job back (every filled sub-field with a result whose key is the project's) and the window idle."""
        wait_until(lambda: not win.relayout_timer.isActive() and all(
            win.project.layout_state(sf, win.layout_keys, win.results) in ("ok", "error", "empty")
            for sf in win.project.subfields))
        for _ in range(5):
            app.processEvents()

    for label, p in (("small: 1 building, 1 sub-field, 2 exclusions", generated(1, 1, 2)),
                     ("large: 20 buildings, 40 sub-fields, 60 exclusions", generated(20, 2, 3))):
        section(f"A2/A3 the window offscreen, {label}")
        root = Path(tempfile.mkdtemp())
        paths = Paths(config=root / "c", state=root / "s", data=root / "d", cache=root / "k")
        file = root / "generated.meridiana"
        p.save(file)
        t = time.perf_counter()
        win = MainWindow(paths, config.Config(background="none"))
        built = (time.perf_counter() - t) * 1000
        win.resize(1400, 900)
        t = time.perf_counter()
        win.open_path(file)
        win.show()
        settle(win)
        opened = (time.perf_counter() - t) * 1000
        modules = sum(r.count for r in win.results.values() if not isinstance(r, Exception))
        print(f"   window built in {built:.0f} ms; project opened, laid out ({modules} modules) and drawn in {opened:.0f} ms")

        # the cost of one edit that touches nothing of the layout: a building renamed
        bid = win.project.buildings[0].id
        computed = []
        win._compute_energy = lambda fetch=False: computed.append(fetch)     # the energy timer's lambda finds it
        times, laid = [], []
        for k in range(5):
            win.energy = {"marker": True}            # as after one computation: the energy page has results
            t = time.perf_counter()
            win._edited("building", bid, {"name": f"Renamed {k}"})
            times.append((time.perf_counter() - t) * 1000)
            settle(win)
            laid.append(len(win.layout_job.laid))
            wait_until(lambda: not win.energy_timer.isActive(), 3.0)
        print(f"   edit() of a name (snapshot, compare, snapshot, _show_all with plan, tree, properties, forms): "
              f"median {median(times):.0f} ms in the window's thread")
        print(f"   the layout job after each rename laid out {laid} sub-fields again (of {len(win.project.subfields)}): "
              f"the building's name is in every sub-field's layout key")
        print(f"   energy computations started by the 5 renames: {len(computed)} (an edit of a name recomputes the year)")
        win.energy = {}
        del win._compute_energy

        # a rename seen by the keys, without the window
        p2 = win.project
        before_key = p2.layout_key(p2.subfields[-1])
        p2.buildings[0].name = "Other name"
        print(f"   a building renamed changes the layout key of a sub-field on another building: "
              f"{before_key != p2.layout_key(p2.subfields[-1])}")
        p2.buildings[0].fire.category = "C"
        print(f"   its fire category too: {before_key != p2.layout_key(p2.subfields[-1])} (the key is asdict() of "
              f"every building and exclusion)")
        p2.buildings[0].name, p2.buildings[0].fire.category = "Renamed 4", ""

        if len(p2.subfields) > 1:
            import cProfile
            import io
            import pstats
            for name, fn in (("_show_tree", win._show_tree), ("_show_energy_forms", win._show_energy_forms),
                             ("_show_checks", win._show_checks)):
                prof = cProfile.Profile()
                prof.enable()
                fn()
                prof.disable()
                out = io.StringIO()
                pstats.Stats(prof, stream=out).sort_stats("cumulative").print_stats(9)
                lines = [ln for ln in out.getvalue().splitlines() if ln.strip() and ("meridiana" in ln or "shapely" in ln
                                                                                     or "function calls" in ln)]
                print(f"   profile of {name}:")
                for ln in lines[:10]:
                    print("      " + ln.strip()[:150])

        # the pieces of _show_all, measured one by one
        good = {k: v for k, v in win.results.items() if not isinstance(v, Exception)}
        pieces = {
            "snapshot()": lambda: win.snapshot(),
            "_state_key() (dirty check, in _title)": lambda: win._state_key(),
            "plan.show_project (all items again)": lambda: win.plan.show_project(win.project, good),
            "_show_tree (with layout_key per sub-field)": lambda: win._show_tree(),
            "_show_properties": lambda: win._show_properties(),
            "_show_energy_forms (arrays_of, obstacles)": lambda: win._show_energy_forms(),
            "_show_3d (mesh + instance table)": lambda: win._show_3d(),
            "_show_checks (gather + marks + tree)": lambda: win._show_checks(),
            "undo.undo() [restore + _show_all]": lambda: (win.undo.undo(), app.processEvents()),
            "undo.redo()": lambda: (win.undo.redo(), app.processEvents()),
        }
        for name, fn in pieces.items():
            print(f"   {name:46s} {timed(fn, 5):8.1f} ms")
        settle(win)

        # an edit whose change raises: the project stays changed, nothing on the undo stack, no redraw
        n_before, undo_before = len(win.project.buildings), win.undo.count()
        try:
            win.edit("Half done", lambda pr: (pr.buildings.append(model.Building(id="bZ", name="ghost",
                                                                                    footprint=[[0, 0], [1, 0], [1, 1]])),
                                              1 / 0))
        except ZeroDivisionError:
            pass
        print(f"   edit() with a change that raises: buildings {n_before} -> {len(win.project.buildings)}, "
              f"undo steps {undo_before} -> {win.undo.count()}, dirty = {win._dirty()}: the ghost building is in the "
              f"project without an undo step (and the plan is not drawn again)")
        win.project.buildings = [b for b in win.project.buildings if b.id != "bZ"]
        win._show_all()
        settle(win)

        # the undo stack after 30 edits of the same number: merged into one step
        steps = win.undo.count()
        for k in range(30):
            win._edited("building", bid, {"height": 8.0 + 0.01 * (k + 1)})
        print(f"   30 edits of a height within 2 s: undo steps {steps} -> {win.undo.count()} (merged by key); "
              f"the stack has no limit (setUndoLimit never called)")
        settle(win)
        # the 3D view and the checks follow only the layout job: after an edit the plan is drawn at once, the 3D later
        t = time.perf_counter()
        win._edited("building", bid, {"height": 12.0})
        drawn_plan = win.plan.drawn[0].building(bid).height
        mesh_before = win.view3d.geometry_
        print(f"   after an edit of a height the plan shows {drawn_plan} m at once; the 3D scene and the checks are "
              f"made again only when the layout job returns (_layout_done), {win.relayout_timer.interval()} ms later "
              f"at the earliest; mesh object {type(mesh_before).__name__}")
        settle(win)
        print(f"   layout job + redraw after that edit: {(time.perf_counter() - t) * 1000:.0f} ms until settled")
        win.close()
        win.deleteLater()
        app.processEvents()


if __name__ == "__main__":
    part_core()
    part_window()
