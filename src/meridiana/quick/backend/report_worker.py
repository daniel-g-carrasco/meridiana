"""Private report child process, launched only with the parent's private staging folder.

Started cold (`report_worker <folder>`: the request is already there) or warm (`report_worker --warm <folder>`): the
imports and the application made first, then it waits on stdin for «go», written when the request is in the folder,
so that the preview does not wait for the imports (study 41). An empty stdin (the window gone) ends it.

The pickle is an internal IPC snapshot created by ReportBackend, never a user file.
All temporary output lives below that staging folder and is disposable on cancel.
"""
from __future__ import annotations

import json
from pathlib import Path
import pickle
import os
import sys


def mark_pdf(path, fingerprint, date):
    """R437: the fingerprint of the year and the date in the file itself, in its properties: not in what is read."""
    from pypdf import PdfReader, PdfWriter
    writer = PdfWriter(clone_from=PdfReader(str(path)))
    writer.add_metadata({"/MeridianaFingerprint": fingerprint, "/MeridianaExported": date})
    with path.open("wb") as stream:
        writer.write(stream)


def supplied(project, energy):
    """What the Widgets window adds to the year for its report (ui/window.py _report_data, _show_checks): the checks
    with those of the plant, most serious first, and the facts of the rules. The Quick window sends the year and the
    layouts: without these the chapters that need them were left out (30 pages where the Widgets wrote 31 on the
    Rho trial, 05/11/2026). Made here, in the worker's process, never on the window's thread."""
    if energy.get("sim") is None or "checks" in energy:
        return {}
    from meridiana import checks, rules
    from meridiana.energy import system
    good = {k: v for k, v in (energy.get("results") or {}).items() if not isinstance(v, Exception)}
    try:
        arrays = system.arrays_of(project, good)
        inverter = system.combined(system.inverters_of(project, sum(a.p_stc for a in arrays))) if arrays else None
    except (ValueError, KeyError) as error:
        print(json.dumps({"event": "note", "what": f"plant not read for the checks: {error}"}), flush=True)
        inverter = None
    items = checks.gather(project, good, energy, inverter, bool(system.inverter_entries(project.energy)))
    items += checks.plant_items(energy.get("plant"))
    items.sort(key=lambda item: checks.LEVELS.index(item.level))
    return {"checks": items, "rules_facts": rules.facts(project, good, energy, inverter)}


def main(folder, app=None, name="request.pickle"):
    from PySide6.QtGui import QGuiApplication
    from meridiana import i18n, model, portability
    from meridiana.report_typst.compose import NoPlant
    from meridiana.ui import report, report_3d
    folder = Path(folder)
    with (folder / name).open("rb") as stream:
        request = pickle.load(stream)
    i18n.setup(request["language"])
    app = app or QGuiApplication([])
    project = model.Project.from_json(request["project"], check=False)
    profile = portability.profile(project, folder) if request["embedded"] else request["profile"]
    energy = request["energy"]
    if "year_file" in energy:       # a preview: the year written once for every preview of it (study 41)
        with Path(energy["year_file"]).open("rb") as stream:
            energy = {**pickle.load(stream), **energy["extra"]}
    energy = {**energy, **supplied(project, energy)}
    images = []
    if request["mode"] == "preview":
        steps = report.preview_pages(project, energy, folder, images, profile)      # drawn by the window (R509)
    else:
        kind = request.get("kind", "pdf")
        made = folder / f"report.{kind}"
        steps = report.export_steps(project, energy, made, profile, kind=kind)
        if request["register"]:
            steps = report.with_register(steps, project, energy, made, profile)
    result = {}
    try:
        while True:
            try:
                fraction, what = next(steps)
            except StopIteration as done:
                result["total"] = done.value
                break
            except NoPlant as error:
                # R459: said as it is, not as a traceback
                print(str(error), file=sys.stderr, flush=True)
                raise SystemExit(2) from None
            print(json.dumps({"event": "progress", "fraction": fraction, "what": what}), flush=True)
        if request["mode"] == "preview":
            result["pages"] = images
        else:
            result["register"] = request["register"] and energy.get("sim") is not None
            if kind == "pdf":
                mark_pdf(made, request.get("fingerprint", ""), request.get("date", ""))
        (folder / "result.json").write_text(json.dumps(result), encoding="utf-8")
    finally:
        steps.close()
        report_3d.release()
        app.quit()


def warm(folder):
    """Everything the report needs imported, the application made; then the request awaited on stdin."""
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtPdf import QPdfDocument  # noqa: F401  (the pages of the preview are drawn from the PDF)
    from meridiana import model, portability  # noqa: F401
    from meridiana.ui import report, report_3d  # noqa: F401
    try:
        import matplotlib.backends.backend_agg  # noqa: F401  (the charts of the chapters)
    except ImportError:
        pass
    app = QGuiApplication([])
    word, _space, name = sys.stdin.readline().strip().partition(" ")
    if word != "go" or not name:
        return
    main(folder, app, name)


if __name__ == "__main__":
    if os.environ.get("MERIDIANA_REPORT_LOW") == "1":
        # R548: a preview made ahead, while the designer is elsewhere: below the window and the year
        from meridiana import resources
        resources.lower_priority()
    if sys.argv[1] == "--warm":
        warm(sys.argv[2])
    else:
        main(sys.argv[1], name=sys.argv[2] if len(sys.argv) > 2 else "request.pickle")
