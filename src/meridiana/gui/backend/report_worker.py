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


def outline(path):
    """The report's chapters as its PDF has them (Typst's bookmarks): each one's title, depth (1 a chapter) and the
    page of the PDF it starts on, counted from 1 (the preview's page numbers too, before an attachment's pages)."""
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    rows = []

    def walk(items, depth):
        for item in items:
            if isinstance(item, list):
                walk(item, depth + 1)
                continue
            try:
                page = reader.get_destination_page_number(item) + 1
            except (KeyError, ValueError, AttributeError):
                page = 0
            rows.append({"title": str(item.title), "level": depth, "page": page})
    walk(reader.outline, 1)
    return rows


def supplied(project, energy):
    """What the Widgets window adds to the year for its report (ui/window.py _report_data, _show_checks): the checks
    with those of the plant, most serious first, and the facts of the rules. The Quick window sends the year and the
    layouts: without these the chapters that need them were left out (30 pages where the Widgets wrote 31 on the
    Rho trial, 05/11/2026). Made here, in the worker's process, never on the window's thread."""
    if energy.get("sim") is None or "checks" in energy:
        return {}
    from meridiana.core.rules import checks, rules
    from meridiana.core.energy import system
    good = {k: v for k, v in (energy.get("results") or {}).items() if not isinstance(v, Exception)}
    try:
        arrays = system.arrays_of(project, good)
        inverter = system.combined(system.inverters_of(project, sum(a.p_stc for a in arrays))) if arrays else None
    except (ValueError, KeyError) as error:
        print(json.dumps({"event": "note", "what": f"plant not read for the checks: {error}"}), flush=True)
        inverter = None
    items = checks.gather(project, good, energy, inverter, bool(system.inverter_entries(project.energy)))
    items += checks.plant_items(energy.get("plant"), profile_id=project.regulatory_profile)
    items.sort(key=lambda item: checks.LEVELS.index(item.level))
    items = checks.condensed(items, project)        # R605: the same list as the Checks panel
    return {"checks": items, "rules_facts": rules.facts(project, good, energy, inverter)}


def main(folder, app=None, name="request.pickle"):
    from PySide6.QtGui import QGuiApplication
    from meridiana import i18n
    from meridiana.app.project import portability
    from meridiana.app.session import project_from
    from meridiana.app.report.compose import NoPlant
    from meridiana.gui.paper import report, report_3d
    folder = Path(folder)
    with (folder / name).open("rb") as stream:
        request = pickle.load(stream)  # noqa: S301 - ReportBackend's request in the private job directory
    i18n.setup(request["language"])
    app = app or QGuiApplication([])
    project = project_from(request["project"])          # the session's photo (R598)
    profile = portability.profile(project, folder) if request["embedded"] else request["profile"]
    energy = request["energy"]
    if "year_file" in energy:       # a preview: the year written once for every preview of it (study 41)
        with Path(energy["year_file"]).open("rb") as stream:
            energy = {**pickle.load(stream), **energy["extra"]}  # noqa: S301 - staged year from the trusted report job
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
    told = 0
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
            # R598: each page of the preview told as soon as it is known (report_job: a result on the way), the
            # chapters and the pages they start on before the first
            if images and not told:
                print(json.dumps({"event": "outline", "rows": outline(images[0]["path"])}), flush=True)
            for n in range(told, len(images)):
                print(json.dumps({"event": "page", "n": n, "row": images[n]}), flush=True)
            told = len(images)
        if request["mode"] == "preview":
            result["pages"] = images
        else:
            result["register"] = request["register"] and energy.get("sim") is not None
            if kind == "pdf":
                mark_pdf(made, request.get("fingerprint", ""), request.get("date", ""))
            # what was made, in the order of the files the window asked for (report_job puts them in their places)
            result["made"] = [str(made)] + ([str(p) for p in report.register_paths(made)] if result["register"] else [])
        (folder / "result.json").write_text(json.dumps(result), encoding="utf-8")
    finally:
        steps.close()
        report_3d.release()
        app.quit()


def warm(folder):
    """Everything the report needs imported, the application made; then the request awaited on stdin."""
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtPdf import QPdfDocument  # noqa: F401  (the pages of the preview are drawn from the PDF)
    from meridiana.core.model import model  # noqa: F401
    from meridiana.app.project import portability  # noqa: F401
    from meridiana.gui.paper import report, report_3d  # noqa: F401
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
        from meridiana.core.compute import resources
        resources.lower_priority()
    if sys.argv[1] == "--warm":
        warm(sys.argv[2])
    else:
        main(sys.argv[1], name=sys.argv[2] if len(sys.argv) > 2 else "request.pickle")
