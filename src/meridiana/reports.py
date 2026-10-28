"""The report's templates and settings (R61, docs/compiti/19r-relazione.md), without Qt: which chapters a template
writes and in which order, which data each chapter needs to be there, the choices the project keeps
(`Project.report`) and the author's profiles the preferences keep (`Config.report_profiles`).

Two templates: «Complete», the default, ten chapters from the summary to the annexes, with a cover and the
contents; «Compact», the essentials in a few pages, in the order of the reports of the inverters' design
programs (overview and results, energy month by month, modules by sub-field, electrical design, simulation
parameters). No name, firm or place is in the program: the author's are written once in the preferences, as
profiles, and chosen for each project; without a profile the report says only the project and the date.

A chapter is written when the template has it, the designer left it on and its data are there: a chapter without
data is left out, never written empty.

The attachments are PDF files the designer adds (the datasheets of the modules, of the inverters, of the
optimizers, the certificates): put after the last chapter, each behind a page that names it and listed in the
contents with its page (ui/report.py merges them with pypdf). The project embeds their bytes on save and also keeps
paths: absolute in memory, relative to the project's file in the file (`portable`, `resolved`), so an older project
still works and a moved one no longer depends on the original files."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .i18n import _

DEFAULT = "complete"


@dataclass(frozen=True)
class Chapter:
    id: str
    title: str
    needs: tuple[str, ...] = ()      # the report's data that must be there ("sim", "results", "plant", "load"...)
    note: str = ""                   # what it holds, beside its box in the Report phase


@dataclass(frozen=True)
class Template:
    id: str
    name: str
    note: str
    chapters: tuple[str, ...]
    contents: bool                   # the list of the chapters with their pages, after the cover


def chapters() -> dict[str, Chapter]:
    """Every chapter of every template, by id."""
    items = [
        Chapter("summary", _("Summary"), ("sim",),
                _("The headline numbers, the layout in 3D and the plan of the modules")),
        Chapter("site", _("Site and climate data"), (),
                _("Where, the weather used and its source, irradiation and temperature month by month")),
        Chapter("layout", _("Roofs and layout"), ("results",),
                _("Each sub-field: area, modules, mounting, orientation, distances, the rows' pitch")),
        Chapter("plant", _("Electrical system"), ("plant",),
                _("Inverters, strings by input, the voltages checked (CEI 64-8/7), DC/AC ratio")),
        Chapter("production", _("Energy yield"), ("sim",),
                _("Month by month with PVGIS beside, the losses from the sun to the grid")),
        Chapter("consumption", _("Consumption and balance"), ("load",),
                _("The consumption by band, self-consumption and the energy fed in")),
        Chapter("economics", _("Economics"), ("econ",),
                _("Saving, investment, cash flow, the size of the system and of the storage")),
        Chapter("checks", _("Checks and standards"), ("checks",),
                _("Every check with its result and its source, the notes of the rules that apply")),
        Chapter("methods", _("Parameters and methods"), ("sim",),
                _("How each number is computed: models, losses, thresholds, with source and formula")),
        Chapter("annexes", _("Annexes"), ("sim",),
                _("The data of the modules and of the inverters used")),
        Chapter("overview", _("System overview and results"), ("sim",),
                _("The headline numbers, the layout in 3D and the plan of the modules")),
        Chapter("monthly", _("Estimated monthly energy"), ("sim",),
                _("The energy month by month, as a table and a chart")),
        Chapter("fields", _("Modules by sub-field"), ("results",),
                _("For each sub-field: module, number, power, mounting, orientation, tilt")),
        Chapter("electrical", _("Electrical design"), ("plant",),
                _("Inverters and their strings, the modules of each string")),
        Chapter("parameters", _("Simulation parameters"), ("sim",),
                _("Place, weather and its source, the losses applied")),
    ]
    return {c.id: c for c in items}


def templates() -> dict[str, Template]:
    items = [
        Template("complete", _("Complete"),
                 _("Cover, contents and ten chapters, from the summary to the annexes: the technical report."),
                 ("summary", "site", "layout", "plant", "production", "consumption", "economics", "checks",
                  "methods", "annexes"), True),
        Template("compact", _("Compact"),
                 _("The essentials in a few pages, as the inverters' design programs write them: results, "
                   "energy month by month, modules, strings, parameters."),
                 ("overview", "monthly", "fields", "electrical", "parameters"), False),
    ]
    return {t.id: t for t in items}


def settings(project) -> dict:
    """The project's choices for its report, the defaults filled in: the template, the chapters turned off, the
    author's profile (None: the preferences' default), the client, whether the address is written, the
    revision, the attachments ({"path", "title"}, in their order) and whether the register of the calculations is
    exported with the report."""
    raw = dict(getattr(project, "report", None) or {})
    template = raw.get("template") if raw.get("template") in templates() else DEFAULT
    off = [c for c in raw.get("off", []) if isinstance(c, str)]
    profile = raw.get("profile")
    return {"template": template, "off": off, "profile": profile if isinstance(profile, str) else None,
            "client": str(raw.get("client") or ""), "address": raw.get("address", True) is not False,
            "revision": str(raw.get("revision") or ""), "attachments": clean_attachments(raw.get("attachments")),
            "register": raw.get("register") is True}


# the attachments

def clean_attachments(raw) -> list[dict]:
    """The attachments as the settings give them: {"path", "title"} for each entry with a path, the rest left out
    (a file edited by hand)."""
    out = []
    for a in raw if isinstance(raw, list) else []:
        if isinstance(a, dict) and isinstance(a.get("path"), str) and a["path"].strip():
            out.append({"path": a["path"].strip(), "title": str(a.get("title") or "").strip()})
    return out


def attachment_title(a: dict) -> str:
    """The name an attachment goes by in the report: its own, else its file's without the extension."""
    return a.get("title") or Path(a["path"]).stem


def _rebased(report: dict, change) -> dict:
    if not isinstance(report, dict) or not isinstance(report.get("attachments"), list):
        return report
    items = [{**a, "path": change(a["path"])} if isinstance(a, dict) and isinstance(a.get("path"), str) and
             a["path"].strip() else a for a in report["attachments"]]
    return {**report, "attachments": items}


def portable(report: dict, folder: Path) -> dict:
    """The report's settings as the project's file keeps them: each attachment's path relative to the file's
    `folder`, with «/» between its parts; absolute when it lies on another drive (Windows has no relative path
    from one drive to another)."""
    def relative(path: str) -> str:
        p = Path(path)
        if not p.is_absolute():
            return path
        try:
            return Path(os.path.relpath(p, folder)).as_posix()
        except ValueError:
            return str(p)
    return _rebased(report, relative)


def resolved(report: dict, folder: Path) -> dict:
    """The report's settings as the program holds them: each attachment's path absolute, a relative one taken from
    the project file's `folder`."""
    def absolute(path: str) -> str:
        p = Path(path)
        return str(p if p.is_absolute() else Path(os.path.normpath(Path(folder) / p)))
    return _rebased(report, absolute)


def has(data: dict, key: str) -> bool:
    """Whether the report's data have `key` with something to write."""
    value = data.get(key)
    if key == "results":
        return any(getattr(r, "modules", None) for r in (value or {}).values())
    if key == "plant":
        return value is not None and bool(getattr(value, "units", None))
    if key == "checks":
        return bool(value) or bool(data.get("rules_notes"))
    return value is not None


def missing(chapter: Chapter, data: dict) -> list[str]:
    """The data `chapter` needs and does not have."""
    return [k for k in chapter.needs if not has(data, k)]


def plan(project, data: dict) -> list[Chapter]:
    """The chapters to write, in order: the template's, left on, with their data."""
    s = settings(project)
    every = chapters()
    return [every[c] for c in templates()[s["template"]].chapters
            if c not in s["off"] and not missing(every[c], data)]


# the author's profile (Preferences > Report): what the cover, the header and the footer say
PROFILE_KEYS = ("name", "signer", "register", "firm", "address", "phone", "email", "web", "logo")


def profile_labels() -> dict[str, str]:
    return {"name": _("Profile"), "signer": _("Name and title"), "register": _("Professional register"),
            "firm": _("Firm"), "address": _("Address"), "phone": _("Phone"), "email": _("E-mail"),
            "web": _("Website"), "logo": _("Logo")}


def clean_profile(raw) -> dict | None:
    """A profile as the configuration keeps it: the known keys, as text; None for what is not a profile."""
    if not isinstance(raw, dict) or not str(raw.get("name") or "").strip():
        return None
    return {k: str(raw.get(k) or "").strip() for k in PROFILE_KEYS}


def profile_for(project, profiles: list, default: str = "") -> dict | None:
    """The profile the project's report is signed with: its own choice, or the preferences' default; "" chosen
    means none."""
    chosen = settings(project)["profile"]
    name = default if chosen is None else chosen
    if not name:
        return None
    return next((p for p in (clean_profile(x) for x in profiles) if p and p["name"] == name), None)
