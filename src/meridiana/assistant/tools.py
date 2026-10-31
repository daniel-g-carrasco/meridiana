"""What Meridio can do with the project (study 14, 6.4 and 6.5; task 14, steps 1 and 2): the tools the model may
call, each with its name, its description and the JSON schema of its arguments, and the function that answers it
from the project as it is now.

Reading, without asking: `read_checks`, `project_summary`, `read_selection`, `read_results`, `read_pedigree`,
`read_rules`, `search_manual`, `search_projects`, `project_revisions`, `similar_projects` and `list_tasks`; `go_to`
only moves the window. Proposing, never applying: `propose_fix` offers the fix a check already has (the way to prefer: in the
trial of study 14, 4.4, a model free to write the fields invented one), `propose_edit` a change of the fields the
Properties panel and the energy pages have, checked with the rules of the project file; a wrong field goes back to
the model with the list of the right ones. `propose_undo` offers the current Undo or Redo step.
`prepare_open_project` shows path and revision but never opens by itself. A proposal is a `Proposal` the window
shows as a card: only the designer applies it with a click.

The tools read the project through a `host`, the window or a test's stand-in, with:
    host.project                the model.Project in hand
    host.checks()               the checks as the Checks panel shows them (checks.Item, the worst first)
    host.layouts()              sub-field id -> layout.Result (or the exception that stopped it)
    host.energy()               what the energy pipeline gave (EnergyResult.as_dict), {} before the first year
    host.plant()                the live plant (energy/plant.Plant) or None
    host.selection()            (kind, id) of what is selected
    host.phase()                the id of the phase open
    host.rules_facts()          rules.Facts of the project, or None
    host.index_rows()           the derived rows of the local project index
    host.go_to(target)          the window brought to ("subfield", id), ("phase", id)...
    host.bindings()             command id -> its keys (shortcuts.bindings), or None for the defaults
They run on the window's thread, between two rounds of the model: they read the project as it is, without races.
No Qt here."""

from __future__ import annotations

import copy
import dataclasses
import json
import math
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field

from .. import checks as checks_module
from .. import layout, model, project_index, settings
from ..fields import field_label, field_value, mounting_names, pitch_mode_names
from ..i18n import _, number

RESULT_LIMIT = 6000             # characters of one tool's answer: the local model has 16k tokens for everything
MANUAL_HITS = 4
LEVELS = checks_module.LEVELS   # "fail", "warn", "info", "ok"
KINDS = ("building", "subfield", "exclusion", "site", "phase", "settings", "setting", "property")
SECTIONS = ("energy", "consumption", "economics")


def _schema(properties: dict | None = None, required: tuple = ()) -> dict:
    return {"type": "object", "properties": properties or {}, "required": list(required),
            "additionalProperties": False}


# the tools as the model sees them: English for the model, the answers in the program's language
SPECS = {
    "read_checks": {
        "description": "Read the checks of the project, the most serious first: each with an id, its level (fail, "
                       "warn, info, ok), area, text, source (the standard with edition, clause and page, or "
                       "Meridiana's own reading), the object it is about and whether Meridiana has a fix for it "
                       "(offer it with propose_fix). filtered_counts describes only the checks returned after every "
                       "filter; project_counts describes the whole project. An empty list means that nothing matches "
                       "the filters, not that the project has no checks.",
        "parameters": _schema({
            "min_level": {"type": "string", "enum": list(LEVELS),
                          "description": "the lowest level wanted: fail alone, warn and worse (default), ..."},
            "area": {"type": "string", "enum": sorted(checks_module.area_names()),
                     "description": "only the checks of this area"},
            "object_id": {"type": "string", "description": "only checks about this building, sub-field or exclusion "
                                                           "id from project_summary; a building includes its objects"}}),
    },
    "project_summary": {
        "description": "A summary of the project: the site (coordinates rounded to 0.01 degree), the buildings, "
                       "the sub-fields with their module, modules laid, power, tilt and azimuth, the inverters, "
                       "the variants, the phase open, whether the year of production is computed.",
        "parameters": _schema(),
    },
    "go_to": {
        "description": "Bring the window to an object (building, subfield, exclusion, site) or to a phase (model, "
                       "plant, production, consumption, economics, report), a settings section, a specific setting "
                       "or a property. Call list_navigation_targets for registered setting/property IDs first. "
                       "The window scrolls to and briefly highlights the target without changing any value.",
        "parameters": _schema({
            "kind": {"type": "string", "enum": list(KINDS)},
            "id": {"type": "string", "description": "the object's id from project_summary or read_checks, or "
                                                    "the phase's id, or a registered ID from list_navigation_targets"}}, ("kind",)),
    },
    "list_navigation_targets": {
        "description": "List the real settings sections, options and project property controls this version can "
                       "show with go_to. Use the returned kind and id verbatim; never invent a control ID. "
                       "This only lists destinations and changes nothing.",
        "parameters": _schema(),
    },
    "read_navigation": {
        "description": "Read the actual mouse/touchpad navigation profile, 3D orbit and pivot, and current keyboard bindings. Always use this before explaining gestures or shortcuts: they may differ from defaults. Orbit applies only to 3D; pan and pointer-centred zoom apply to both views.",
        "parameters": _schema(),
    },
    "search_manual": {
        "description": "Search Meridiana's user manual (in Italian) and its commands (menu, keys) for how to do "
                       "something in the program. Use it before explaining how to use Meridiana.",
        "parameters": _schema({"query": {"type": "string", "description": "a few words, in Italian"}}, ("query",)),
    },
    "read_selection": {
        "description": "Read the object selected in the window, with the fields of its Properties panel and the "
                       "fields propose_edit accepts for it.",
        "parameters": _schema(),
    },
    "read_results": {
        "description": "Read the results computed: production (energy, specific yield, PR, the chain of the "
                       "losses, the months), strings (inputs, modules in series, voltages), consumption, economics "
                       "(self-consumption, bills, NPV, payback, LCOE).",
        "parameters": _schema({"section": {"type": "string",
                                           "enum": ["production", "strings", "consumption", "economics"]}},
                              ("section",)),
    },
    "read_pedigree": {
        "description": "Read how a result is computed, step by step: formula, the values that went in with their "
                       "source (input typed by the designer, default of Meridiana, data, norm, model, computed) "
                       "and the reference. Without `step`, every step in short; with it, the steps whose key or "
                       "title contains it, in full.",
        "parameters": _schema({
            "calculation": {"type": "string", "enum": ["production", "strings", "consumption", "economics"]},
            "step": {"type": "string"}}, ("calculation",)),
    },
    "read_rules": {
        "description": "Read the rules that apply to the project (connection, interface protection, minimum "
                       "renewable power, fire brigade, who may design...) with their sources, and the facts they "
                       "were judged on.",
        "parameters": _schema(),
    },
    "propose_fix": {
        "description": "Propose to the designer the fix a check already has (its id from read_checks). The "
                       "designer sees a card and applies it or not: you never apply anything. Prefer this to "
                       "propose_edit.",
        "parameters": _schema({"check_id": {"type": "string"}}, ("check_id",)),
    },
    "propose_edit": {
        "description": "Propose to the designer a change of fields of an object (building, subfield, exclusion, "
                       "by id) or of the project's energy, consumption or economics settings (id empty), with the "
                       "reason. Only the fields read_selection lists are accepted; a wrong one comes back with the "
                       "list. The designer sees a card and applies it or not.",
        "parameters": _schema({
            "kind": {"type": "string", "enum": ["building", "subfield", "exclusion", *SECTIONS]},
            "id": {"type": "string"},
            "changes": {"type": "object", "description": "field path -> new value, e.g. {\"params.tilt\": 20}"},
            "reason": {"type": "string"}}, ("kind", "changes", "reason")),
    },
    "propose_undo": {
        "description": "Propose Undo or Redo as a card with the text of the history step. The designer applies it "
                       "with a click; you never undo or redo anything yourself. If that direction has no step, the "
                       "answer says so.",
        "parameters": _schema({"action": {"type": "string", "enum": ["undo", "redo"]}}, ("action",)),
    },
    "search_projects": {
        "description": "Search the local index of projects in linked folders by text, kind, client, power, date "
                       "or distance from a project id. The returned ids are local aliases for the other tools.",
        "parameters": _schema({"query": {"type": "string"},
                               "kind": {"type": "string", "enum": ["", "roof", "ground", "mixed"]},
                               "client": {"type": "string"}, "power_from": {"type": "number"},
                               "power_to": {"type": "number"}, "since": {"type": "string"},
                               "project_id": {"type": "string"}, "max_distance_km": {"type": "number"}}),
    },
    "project_revisions": {
        "description": "Show the latest readable revision of each project series, or of one series_id or project "
                       "alias. A newer damaged file never hides the latest valid revision.",
        "parameters": _schema({"series_id": {"type": "string"}, "project_id": {"type": "string"}}),
    },
    "similar_projects": {
        "description": "Find the latest similar projects: same kind, power within the requested range, mounting, "
                       "tilt and distance explained. Each series appears once, at its latest valid revision.",
        "parameters": _schema({"project_id": {"type": "string", "description": "an id from search_projects; empty "
                                                                                "for the project in hand"},
                               "power_from": {"type": "number"}, "power_to": {"type": "number"},
                               "client": {"type": "string"}}),
    },
    "prepare_open_project": {
        "description": "Prepare a confirmation card for opening a project id returned by another project tool. "
                       "Never opens it: only the designer's click can open, through the normal unsaved-changes flow.",
        "parameters": _schema({"project_id": {"type": "string"}}, ("project_id",)),
    },
    "list_tasks": {
        "description": "Read local tasks and due dates, optionally including completed tasks or filtering by job "
                       "or due date. The returned ids are local aliases for prepare_task.",
        "parameters": _schema({"include_done": {"type": "boolean"}, "job_id": {"type": "string"},
                               "due_before": {"type": "string"}}),
    },
    "prepare_task": {
        "description": "Prepare a card to create a local task or complete one returned by list_tasks. Never writes "
                       "the registry: only the designer's click applies the proposal.",
        "parameters": _schema({"action": {"type": "string", "enum": ["create", "complete"]},
                               "task_id": {"type": "string"}, "text": {"type": "string"},
                               "due": {"type": "string"}, "job_id": {"type": "string"},
                               "project_id": {"type": "string"}}, ("action",)),
    },
}
STEP_1 = ("read_checks", "project_summary", "go_to", "search_manual", "list_navigation_targets", "read_navigation")
STEP_2 = ("read_selection", "read_results", "read_pedigree", "read_rules", "propose_fix", "propose_edit",
          "propose_undo")
STEP_3 = ("search_projects", "project_revisions", "similar_projects", "prepare_open_project", "list_tasks",
          "prepare_task", "prepare_bug_report", "start_guided_tour", "propose_catalog_record")


def specs(names=None) -> list[dict]:
    """The tools as the providers take them: [{"name", "description", "parameters"}], always in the same order
    (a provider caches what comes before the conversation)."""
    return [{"name": n, **SPECS[n]} for n in (names or (*STEP_1, *STEP_2, *STEP_3))]


# what one call gives back

@dataclass
class Proposal:
    """A change offered to the designer: `lines` are (field path, before, after) as the card writes them;
    `change(project)` makes it inside the window's edit(), or `item` is the check whose fix the window applies
    (an action, a computation: what a button would do)."""
    id: str
    title: str
    kind: str                   # the object's kind, or a section; "" for a check's fix of its own
    oid: str
    lines: list
    reason: str = ""
    source: str = ""
    change: Callable | None = field(default=None, repr=False)
    item: object = None
    network: bool = False       # applying it uses the network (a year computed with PVGIS)
    state: str = "pending"      # "applied", "discarded", "failed"


@dataclass
class Outcome:
    content: str                # JSON text for the model
    note: str = ""              # what Meridio did, in a few words, for the designer
    error: bool = False
    proposal: Proposal | None = None


@dataclass
class State:
    """What the tools remember within one conversation: the checks by the ids last given, the proposals made."""
    checks: dict = field(default_factory=dict)
    proposals: dict = field(default_factory=dict)
    projects: dict = field(default_factory=dict)
    tasks: dict = field(default_factory=dict)
    count: int = 0
    project_count: int = 0
    task_count: int = 0
    cloud: bool = False


def _json(value) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str)
    if len(text) > RESULT_LIMIT:
        text = json.dumps({"truncated": True, "part": text[:RESULT_LIMIT]}, ensure_ascii=False)
    return text


def _error(text: str, **more) -> Outcome:
    return Outcome(_json({"error": text, **more}), error=True)


def run(name: str, arguments, host, state: State) -> Outcome:
    """One call of the model: its answer, or an error it can read and correct."""
    if name not in SPECS:
        return _error(f"no tool named {name!r}", tools=sorted(SPECS))
    if not isinstance(arguments, dict):
        return _error("the arguments are not a JSON object")
    try:
        return TOOLS[name](host, state, **arguments)
    except TypeError as error:          # an argument the tool does not take
        return _error(f"bad arguments: {error}", schema=SPECS[name]["parameters"])
    except (ValueError, KeyError) as error:
        return _error(str(error))


# names

def object_name(project, kind: str, oid: str) -> str:
    """What the tree calls an object: «Sud», «Lucernario 2»; the site by the project's name."""
    if kind == "building":
        b = project.building(oid)
        return b.name if b else oid
    if kind == "subfield":
        sf = next((s for s in project.subfields if s.id == oid), None)
        return sf.name if sf else oid
    if kind == "exclusion":
        e = next((x for x in project.exclusions if x.id == oid), None)
        if e is None:
            return oid
        return f"{model.exclusion_names().get(e.kind, e.kind)} {project.exclusion_numbers()[e.id]}"
    if kind == "site":
        return _("the site")
    if kind == "phase":
        from .. import phases
        try:
            return phases.by_id(oid).title
        except (KeyError, AttributeError):
            return oid
    return oid


def _target(project, target) -> dict:
    target = tuple(target or ())
    if not target:
        return {}
    kind = target[0]
    oid = target[1] if len(target) > 1 else ""
    return {"kind": kind, "id": oid, "name": object_name(project, kind, oid)}


# reading

def _about_object(project, target, object_id: str) -> bool:
    if not object_id:
        return True
    if len(target) < 2:
        return False
    kind, oid = target[:2]
    if oid == object_id:
        return True
    if any(b.id == object_id for b in project.buildings):
        if kind == "subfield":
            sf = next((s for s in project.subfields if s.id == oid), None)
            return sf is not None and sf.building == object_id
        if kind == "exclusion":
            exclusion = next((e for e in project.exclusions if e.id == oid), None)
            return exclusion is not None and exclusion.building == object_id
    return False


def read_checks(host, state: State, min_level: str = "warn", area: str = "", object_id: str = "") -> Outcome:
    if min_level not in LEVELS:
        raise ValueError(f"min_level must be one of {', '.join(LEVELS)}")
    items = list(host.checks())
    top = LEVELS.index(min_level)
    names = checks_module.area_names()
    levels = checks_module.level_names()
    out = []
    selected = []
    state.checks = {}
    for n, it in enumerate(items, 1):
        cid = f"c{n}"
        state.checks[cid] = it
        if (LEVELS.index(it.level) > top or (area and it.area != area)
                or not _about_object(host.project, it.target, object_id)):
            continue
        row = {"id": cid, "level": it.level, "level_name": levels.get(it.level, it.level),
               "area": names.get(it.area, it.area), "text": it.text,
               "source": it.source or "Meridiana", "about": _target(host.project, it.target)}
        if it.fix:
            row["fix"] = it.fix_label or True
        if it.detail:
            row["detail"] = it.detail
        out.append(row)
        selected.append(it)
    result = {"checks": out, "filtered_counts": checks_module.counts(selected),
              "project_counts": checks_module.counts(items)}
    if not out:
        result["message"] = _("No checks match this filter.")
    return Outcome(_json(result), _("Read the checks"))


def _module(project, sf) -> dict:
    rec = project.modules.get(sf.module) or {}
    return {"name": f"{rec.get('manufacturer', '')} {rec.get('model', sf.module)}".strip(),
            "power_kw": rec.get("power_kw")}


def _laid(host, sf) -> int:
    result = (host.layouts() or {}).get(sf.id)
    if not sf.filled or result is None or isinstance(result, Exception):
        return 0
    return int(getattr(result, "count", 0))


def project_summary(host, state: State) -> Outcome:
    p = host.project
    subfields = []
    total = 0.0
    for sf in p.subfields:
        laid = _laid(host, sf)
        module = _module(p, sf)
        kw = laid * float(module.get("power_kw") or 0.0)
        total += kw
        params = sf.layout_params()
        subfields.append({"id": sf.id, "name": sf.name, "on": object_name(p, "building", sf.building)
                          if sf.building else "ground", "module": module["name"], "modules_laid": laid,
                          "power_kwp": round(kw, 2), "mounting": params.mounting,
                          "mounting_name": mounting_names().get(params.mounting, params.mounting),
                          "pitch_mode": params.pitch_mode,
                          "pitch_mode_name": pitch_mode_names().get(params.pitch_mode, params.pitch_mode),
                          "shade_free": params.shade_free, "shade_free_name": field_value("params.shade_free",
                                                                                         params.shade_free),
                          "portrait": params.portrait, "orientation_name": field_value("params.portrait",
                                                                                       params.portrait),
                          "tilt": params.tilt, "azimuth": "auto" if params.azimuth is None else params.azimuth,
                          "laid": sf.filled, "by_hand": sf.manual})
    buildings = [{"id": b.id, "name": b.name, "height_m": b.height, "roof": b.roof.type,
                  "slope": round(b.slope(), 1) if hasattr(b, "slope") else b.roof.tilt,
                  "fire_brigade": b.fire.subject} for b in p.buildings]
    inverters = [{"name": e.get("name") or e.get("record", {}).get("model", ""), "count": e.get("count", 1),
                  "ac_kw": round(float(e.get("record", {}).get("ac_power_nominal_w") or 0) / 1000.0, 2),
                  **({"optimizer": e["optimizer"].get("model", ""), "modules_on_each": e.get("per_optimizer", 1)}
                     if (e.get("optimizer") or {}).__class__ is dict and e.get("optimizer") else {})}
                 for e in (p.energy.get("inverters") or [])]
    energy = host.energy() or {}
    sim = energy.get("sim")
    out = {"project": p.name, "address": p.site.address,
           "site": {"lat": round(p.site.lat, 2), "lon": round(p.site.lon, 2)},
           "buildings": buildings, "subfields": subfields, "power_kwp": round(total, 2),
           "exclusions": len(p.exclusions), "inverters": inverters or "sized by Meridiana from the DC/AC ratio",
           "variants": [v.get("name") for v in p.variants], "variant": p.current_variant().get("name"),
           "phase": host.phase(), "selection": _target(p, host.selection()),
           "year_computed": sim is not None}
    if sim is not None:
        out["year"] = {"energy_kwh": round(sim.energy_kwh), "specific_yield": round(sim.specific_yield),
                       "pr": round(sim.pr, 3)}
    return Outcome(_json(out), _("Read the project"))


def go_to(host, state: State, kind: str, id: str = "") -> Outcome:   # noqa: A002  the model's word
    p = host.project
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}")
    shown_name = ""
    if kind in ("settings", "setting", "property"):
        rows = _navigation_targets(host)
        choice = next((row for row in rows if row["kind"] == kind and row["id"] == id), None)
        if choice is None:
            return _error("the requested control is not registered", targets=rows)
        target = (kind, id)
        shown_name = choice["label"]
    elif kind == "phase":
        from .. import phases
        if id not in phases.ids():
            return _error(f"no phase {id!r}", phases=phases.ids())
        target = ("phase", id)
    elif kind == "site":
        target = ("site",)
    else:
        found = {"building": [b.id for b in p.buildings], "subfield": [s.id for s in p.subfields],
                 "exclusion": [e.id for e in p.exclusions]}[kind]
        if id not in found:
            return _error(f"no {kind} {id!r}", ids=found)
        target = (kind, id)
    host.go_to(target)
    shown = _target(p, target)
    shown["name"] = shown_name or shown["name"]
    return Outcome(_json({"done": True, "shown": shown}),
                   _("Went to {what}").format(what=shown["name"]))


def _navigation_targets(host) -> list[dict]:
    listing = getattr(host, "navigation_targets", None)
    return listing() if callable(listing) else []


def read_navigation(host, state: State) -> Outcome:
    from .navigation_help import snapshot
    data = snapshot(host)
    # the commands as rows and their keys once (the bindings repeated them): written as dicts they passed the limit
    # of an answer with the commands of 31/10/2026, and the model read a truncated part
    data.pop("bindings", None)
    if "commands" in data:
        data["commands_columns"] = ["id", "label", "keys"]
        data["commands"] = [[c["id"], c["label"], c["keys"]] for c in data["commands"]]
    return Outcome(_json(data), _("Read your current navigation settings"))


def list_navigation_targets(host, state: State) -> Outcome:
    return Outcome(_json({"targets": _navigation_targets(host)}))


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _words(text: str) -> list[str]:
    """The words of a query, folded and cut to their first five letters (a poor man's stem: «varianti» finds
    «variante»); the short ones (articles, prepositions) left out."""
    return [w[:5] for w in re.findall(r"\w+", _fold(text)) if len(w) > 3]


def manual_passages() -> list[tuple[str, str, str]]:
    """(chapter title, heading, text) of each paragraph of the manual, read from docs/manuale or the shipped
    copy (help.manual_dir); [] when there is none."""
    from .. import help as helps
    folder = helps.manual_dir()
    out: list = []
    if folder is None:
        return out
    for name in helps.CHAPTERS:
        f = folder / name
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        title = helps.chapter_title(text)
        heading = title
        for block in re.split(r"\n\s*\n", text):
            block = block.strip()
            if not block:
                continue
            if block.startswith("#"):
                heading = block.lstrip("#").strip().splitlines()[0]
                rest = block.split("\n", 1)[1].strip() if "\n" in block else ""
                if not rest:
                    continue
                block = rest
            out.append((title, heading, block))
    return out


def search_manual(host, state: State, query: str) -> Outcome:
    words = _words(query)
    if not words:
        raise ValueError("query: write a few words")
    scored = []
    for title, heading, text in manual_passages():
        hay = _fold(f"{heading} {text}")
        score = sum(hay.count(w) for w in words) + 2 * sum(w in _fold(heading) for w in words)
        hits = sum(w in hay for w in words)
        if hits:
            scored.append((hits, score, title, heading, text))
    scored.sort(key=lambda s: (-s[0], -s[1]))
    passages = [{"chapter": t, "heading": h, "text": x[:900]} for _h, _s, t, h, x in scored[:MANUAL_HITS]]
    from .. import shortcuts
    bound = host.bindings() if hasattr(host, "bindings") else None
    keys = bound or shortcuts.bindings({})
    native = getattr(host, "key_text", None) or (lambda k: k)       # «Ctrl+Maiusc+N» on an Italian desktop
    groups = shortcuts.groups()
    commands = []
    for c in shortcuts.commands():
        text = shortcuts.plain(c.text)
        hits = sum(w in _fold(text) for w in words)
        if hits:
            commands.append((hits, {"command": text, "menu": groups.get(c.group, c.group),
                                    "keys": [native(k) for k in keys.get(c.id, c.keys)]}))
    commands.sort(key=lambda c: -c[0])
    return Outcome(_json({"passages": passages, "commands": [c for _h, c in commands[:6]]}),
                   _("Searched the manual: «{query}»").format(query=query))


def _value(v):
    if isinstance(v, float):
        return round(v, 3) if math.isfinite(v) else None
    return v


def read_selection(host, state: State) -> Outcome:
    p = host.project
    kind, oid = tuple(host.selection())[:2] if host.selection() else ("site", "")
    out: dict = {"kind": kind, "id": oid, "name": object_name(p, kind, oid)}
    if kind == "building" and p.building(oid) is not None:
        b = p.building(oid)
        from shapely.geometry import Polygon
        shape = Polygon(b.footprint)
        out.update({"height_m": b.height, "parapet_m": b.parapet, "roof": dataclasses.asdict(b.roof) | {
            "free_pitches": len(b.roof.free_pitches)}, "fire": dataclasses.asdict(b.fire),
            "area_m2": round(shape.area, 1), "perimeter_m": round(shape.length, 1),
            "subfields": [s.name for s in p.subfields if s.building == b.id],
            "exclusions": [object_name(p, "exclusion", e.id) for e in p.exclusions if e.building == b.id]})
    elif kind == "subfield" and any(s.id == oid for s in p.subfields):
        sf = next(s for s in p.subfields if s.id == oid)
        params = dataclasses.asdict(p.fill_params(sf))
        out.update({"on": object_name(p, "building", sf.building) if sf.building else "ground",
                    "module": _module(p, sf), "modules_laid": _laid(host, sf), "laid": sf.filled,
                    "by_hand": sf.manual, "params": {k: _value(v) for k, v in params.items()},
                    "params_display": {k: {"label": field_label(f"params.{k}"),
                                           "value": field_value(f"params.{k}", v)} for k, v in params.items()},
                    "window_from_project": "window" not in sf.params,
                    "params_set_by_designer": sorted(sf.params)})
        from shapely.geometry import Polygon
        out["area_m2"] = round(Polygon(sf.ring).area, 1)
    elif kind == "exclusion" and any(e.id == oid for e in p.exclusions):
        e = next(x for x in p.exclusions if x.id == oid)
        out.update({"kind_of": e.kind, "height_m": e.obstacle_height(), "height_set": e.height is not None,
                    "clearance_m": e.clearance, "on": object_name(p, "building", e.building) if e.building else
                    "ground"})
    else:
        out.update({"kind": "site", "site": {"lat": round(p.site.lat, 2), "lon": round(p.site.lon, 2)},
                    "address": p.site.address, "sun_window": p.sun_window})
    if kind in EDITABLE:
        out["fields_for_propose_edit"] = fields_of(kind)
    return Outcome(_json(out), _("Read the selection"))


def section_names() -> dict:
    return {"production": _("production"), "strings": _("strings"), "consumption": _("consumption"),
            "economics": _("economics")}


def read_results(host, state: State, section: str) -> Outcome:
    energy = host.energy() or {}
    said = _("Read the results: {what}").format(what=section_names().get(section, section))
    if section == "production":
        sim = energy.get("sim")
        if sim is None:
            return Outcome(_json({"computed": False, "why": energy.get("error_sim") or
                                  "the year is not computed: Compute (F5) in the Production phase"}),
                           said)
        monthly = []
        try:
            monthly = [round(float(v)) for v in sim.monthly["energy_kwh"]] if "energy_kwh" in sim.monthly else []
        except (KeyError, TypeError, ValueError):
            monthly = []
        out = {"p_stc_kwp": round(sim.p_stc_kw, 2), "p_ac_kw": round(sim.p_ac_kw, 2),
               "energy_kwh": round(sim.energy_kwh), "specific_yield_kwh_kwp": round(sim.specific_yield),
               "pr": round(sim.pr, 3), "losses": [{"step": c.label, "kind": c.kind, "value": round(c.value, 1),
                                                    "change_pct": None if c.change is None else round(c.change, 2),
                                                    "basis": _("the whole plant, against the previous step of the same "
                                                               "quantity, weighted by array power")}
                                                   for c in sim.chain],
               "obstacle_shading": [{"array": a["name"], "subfield_id": str(a["key"]).split(".")[0],
                                     "loss_pct": round(100 * float(a.get("obstacle_shading") or 0.0), 2),
                                     "basis": _("the array's annual irradiance after far shading")}
                                    for a in sim.arrays],
               "notes": list(sim.notes)}
        if monthly:
            out["monthly_kwh"] = monthly
        pvgis = energy.get("pvgis")
        if pvgis is not None and getattr(pvgis, "energy_kwh", None) is not None:
            out["pvgis_kwh"] = round(float(pvgis.energy_kwh))
    elif section == "strings":
        plant = host.plant() or energy.get("plant")
        if plant is None:
            return Outcome(_json({"computed": False}), said)
        from ..energy.optimizers import OptimizedPlan
        inputs = []
        for (unit, mppt), inp in sorted(plant.inputs.items()):
            plan = inp.plan
            row = {"inverter": unit, "input": mppt, "strings": len(inp.strings), "level": inp.level,
                   "power_kw": round(inp.power_w / 1000.0, 2)}
            if isinstance(plan, OptimizedPlan):
                # a string of power optimizers (task 22): its optimizers and power against SolarEdge's table
                row.update({"optimizer": plan.optimizer, "modules_on_each": plan.per,
                            "optimizers_in_a_string": plan.optimizers, "range_of_optimizers": list(plan.opt_range),
                            "string_power_w": round(plan.power_w), "string_power_allowed_w": plan.limit_w
                            if plan.limit_w != float("inf") else None, "string_power_carried_w": plan.continuous_w,
                            "string_voltage_v": plan.v_string,
                            "checks": [{"check": c.label, "level": c.level, "detail": c.detail, "source": c.source}
                                       for c in plan.checks]})
            elif plan is not None:
                row.update({"in_series": plan.n_series, "range_in_series": [plan.n_series_min, plan.n_series_max],
                            "uoc_max_v": round(plan.uoc_max, 1), "v_limit_v": round(plan.v_limit, 1),
                            "vmp_hot_v": round(plan.vmp_hot, 1), "vmp_cold_v": round(plan.vmp_cold, 1),
                            "mppt_window_v": list(plan.window),
                            "checks": [{"check": c.label, "level": c.level, "detail": c.detail} for c in plan.checks]})
            inputs.append(row)
        out = {"strings": len(plant.strings), "inputs": inputs, "t_min_c": round(plant.t_min, 1),
               "t_cell_max_c": round(plant.t_cell_max, 1), "conditions": "the typical year" if plant.year else
               "PVsyst's design conditions", "modules_in_no_string": len(plant.left), "notes": list(plant.notes)}
    elif section == "consumption":
        load = energy.get("load")
        if load is None:
            return Outcome(_json({"computed": False, "why": energy.get("error_load") or "no consumption"}),
                           said)
        out = {"annual_kwh": round(load.annual_kwh), "basis": load.basis,
               "by_band_kwh": {k: round(v) for k, v in load.by_band().items()}}
    elif section == "economics":
        econ = energy.get("econ")
        if econ is None:
            return Outcome(_json({"computed": False}), said)
        out = {k: _value(v) if not isinstance(v, (int, float)) or isinstance(v, bool) else
               (round(v, 4) if abs(v) < 10 else round(v, 1)) for k, v in econ.kpi.items()}
    else:
        raise ValueError("section must be production, strings, consumption or economics")
    return Outcome(_json(out), said)


def _records(host, calculation: str) -> list:
    energy = host.energy() or {}
    if calculation == "production":
        sim = energy.get("sim")
        return [sim.record] if sim is not None else []
    if calculation == "economics":
        econ = energy.get("econ")
        return [econ.record] if econ is not None else []
    if calculation == "consumption":
        load = energy.get("load")
        return [load.record] if load is not None else []
    if calculation == "strings":
        plant = host.plant() or energy.get("plant")
        if plant is None:
            return []
        return [inp.plan.record for _k, inp in sorted(plant.inputs.items())
                if inp.plan is not None and inp.plan.record is not None][:1]
    raise ValueError("calculation must be production, strings, consumption or economics")


def _quantity(q) -> dict:
    out = {"what": q.label, "value": q.text()}
    if q.source is not None:
        out["source"] = q.source.kind
        out["from"] = q.source.label + (f" ({q.source.ref})" if q.source.ref else "")
    return out


def read_pedigree(host, state: State, calculation: str, step: str = "") -> Outcome:
    records = _records(host, calculation)
    said = _("Read how it is computed: {what}").format(what=section_names().get(calculation, calculation))
    if not records:
        return Outcome(_json({"computed": False}), said)
    wanted = _fold(step)
    steps = []
    for rec in records:
        for s in rec.steps:
            if wanted and wanted not in _fold(f"{s.key} {s.title}"):
                continue
            row = {"key": s.key, "title": s.title}
            if s.result is not None:
                row["result"] = _quantity(s.result)
            if wanted:
                row.update({"formula": s.formula, "explanation": s.explanation,
                            "inputs": [_quantity(q) for q in s.inputs], "reference": s.reference})
            else:
                row["defaults"] = [q.label for q in s.inputs if q.source is not None and q.source.kind == "default"]
            steps.append(row)
    if wanted and not steps:
        return _error(f"no step with {step!r}", steps=[s.key for r in records for s in r.steps])
    return Outcome(_json({"calculation": calculation, "steps": steps}), said)


def read_rules(host, state: State) -> Outcome:
    from .. import rules
    f = host.rules_facts()
    if f is None:
        return _error("the rules could not be read: the plant could not be read")
    applying = [{"rule": rules.title(r, f), "source": r.source(), "level": r.level, "paragraphs": r.paragraphs(f)}
                for r in rules.applying(f)]
    facts = {"p_dc_kw": round(f.p_dc_kw, 2), "p_ac_kw": round(f.p_ac_kw, 2), "p_nominal_kw": round(f.p_nominal_kw, 2),
             "connection": f.level, "fire_brigade": f.fire, "obligation": f.obligation or "not stated",
             "storage": f.storage, "uoc_max_v": f.uoc_max, "region": f.region}
    return Outcome(_json({"facts": facts, "rules": applying}), _("Read the rules that apply"))


# proposing

def _show(v) -> str:
    if isinstance(v, bool):
        return _("yes") if v else _("no")
    if isinstance(v, float):
        return number(v, 2)
    if v is None:
        return _("automatic")
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)[:60]
    return str(v)


def propose_undo(host, state: State, action: str) -> Outcome:
    if action not in ("undo", "redo"):
        raise ValueError("action must be undo or redo")
    step = host.history_text(action)
    if not step:
        return _error(f"nothing to {action}")
    state.count += 1
    title = _("Undo") if action == "undo" else _("Redo")
    proposal = Proposal(id=f"p{state.count}", title=title, kind="history", oid=action, lines=[],
                        reason=_("Step: {step}").format(step=step))
    state.proposals[proposal.id] = proposal
    return Outcome(_json({"proposed": proposal.id, "step": step, "shown_to_designer": True, "applied": False,
                          "waiting": "the designer applies it or not with a click"}),
                   _("Proposed: {what}").format(what=title), proposal=proposal)


def propose_fix(host, state: State, check_id: str) -> Outcome:
    it = state.checks.get(check_id)
    if it is None:
        read_checks(host, state, "ok")             # the ids of the checks as they are now
        it = state.checks.get(check_id)
        if it is None:
            return _error(f"no check {check_id!r}: read_checks gives the ids")
    if it not in list(host.checks()):
        return _error("that check is no longer there (the project changed): read_checks again")
    if not it.fix:
        return _error("that check has no fix: explain what to do, or propose_edit")
    state.count += 1
    p = host.project
    fix = tuple(it.fix)
    lines, change, network = [], None, False
    if fix[0] == "energy":
        path, value = fix[1], fix[2]
        before = _get_path(p.energy, path)
        lines = [(path, _show(before), _show(value))]
        change = lambda project, path=path, value=value: _set_path(project.energy, path, value)    # noqa: E731
        kind, oid = "energy", ""
    elif fix[0] == "edit":
        kind, oid, changes = fix[1], fix[2], dict(fix[3])
        lines = [(path, _show(_current(p, kind, oid, path)), _show(v)) for path, v in changes.items()]
        change = lambda project, k=kind, o=oid, c=changes: apply_edit(project, k, o, c)            # noqa: E731
    else:
        kind, oid = (fix[2], fix[3]) if fix[0] == "action" and len(fix) > 3 else ("", "")
        network = fix[0] == "compute"
    proposal = Proposal(id=f"p{state.count}", title=it.fix_label or it.text, kind=kind, oid=oid, lines=lines,
                        reason=it.text, source=it.source, change=change, item=None if change else it,
                        network=network)
    state.proposals[proposal.id] = proposal
    return Outcome(_json({"proposed": proposal.id, "shown_to_designer": True, "applied": False,
                          "waiting": "the designer applies it or not with a click"}),
                   _("Proposed: {what}").format(what=proposal.title), proposal=proposal)


# the fields a proposal may change: the Properties panel's (ui/properties.py) with the type of each, or a set of
# the words allowed
NUMBER, WHOLE, SWITCH, TEXT = "number", "whole", "switch", "text"
EDITABLE = {
    "building": {"name": TEXT, "height": NUMBER, "parapet": NUMBER, "roof.type": model.ROOF_TYPES,
                 "roof.tilt": NUMBER, "roof.ridge_height": NUMBER, "fire.subject": SWITCH,
                 "fire.roof_fire_resistant": SWITCH},
    "subfield": {"name": TEXT, "params.mounting": tuple(sorted(layout.MOUNTINGS)), "params.portrait": SWITCH,
                 "params.stack": WHOLE, "params.tilt": NUMBER, "params.azimuth": NUMBER, "params.gap": NUMBER,
                 "params.edge": NUMBER, "params.shade_free": SWITCH, "params.flush_row_gap": NUMBER,
                 "params.table_modules": WHOLE, "params.table_gap": NUMBER, "params.pitch_mode": ("sun", "value", "gcr"),
                 "params.pitch": NUMBER, "params.gcr": NUMBER},
    "exclusion": {"kind": model.EXCLUSION_KINDS, "height": NUMBER, "clearance": NUMBER},
}
NULLABLE = {"params.azimuth", "height", "roof.ridge_height"}       # None: automatic, the kind's default


def _section_fields(section: str) -> dict:
    """The scalar fields of a section of the energy settings (settings.py), by path, with their type."""
    out = {}

    def walk(kls, prefix: str) -> None:
        for f in dataclasses.fields(kls):
            default = f.default if f.default is not dataclasses.MISSING else f.default_factory()
            path = prefix + f.name
            if dataclasses.is_dataclass(default):
                walk(default.__class__, path + ".")
            elif default is None or isinstance(default, float):
                out[path] = NUMBER
            elif isinstance(default, bool):
                out[path] = SWITCH
            elif isinstance(default, int):
                out[path] = WHOLE
            elif isinstance(default, str):
                out[path] = TEXT
    walk(settings.SECTIONS[section], "")
    for kept in ("pod", "strings.strategy"):        # what is not a design choice, or has its own list
        out.pop(kept, None)
    if section == "energy":
        out["strings.strategy"] = settings.STRATEGIES
    return out


def fields_of(kind: str) -> dict:
    """The fields propose_edit takes for a kind, path -> its type or the words allowed."""
    table = EDITABLE.get(kind) or (_section_fields(kind) if kind in SECTIONS else {})
    return {k: (list(v) if isinstance(v, tuple) else v) for k, v in table.items()}


def _typed(path: str, kind_of, value):
    if value is None and path in NULLABLE:
        return None
    if isinstance(kind_of, tuple):
        if value not in kind_of:
            raise ValueError(f"{path}: {value!r} is not one of {', '.join(kind_of)}")
        return value
    if kind_of == SWITCH:
        if value.__class__ is not bool:
            raise ValueError(f"{path}: {value!r} is not true or false")
        return value
    if kind_of == WHOLE:
        if value.__class__ is not int and not (isinstance(value, float) and value.is_integer()):
            raise ValueError(f"{path}: {value!r} is not a whole number")
        return int(value)
    if kind_of == NUMBER:
        if value.__class__ not in (int, float) or not math.isfinite(value):
            raise ValueError(f"{path}: {value!r} is not a number")
        return float(value)
    if value.__class__ is not str or not value.strip():
        raise ValueError(f"{path}: {value!r} is not a text")
    return value.strip()


def _get_path(data: dict, path: str):
    for k in path.split("."):
        if not isinstance(data, dict) or k not in data:
            return None
        data = data[k]
    return data


def _set_path(data: dict, path: str, value) -> None:
    from ..session import set_path
    set_path(data, path, value)


def _thing(project, kind: str, oid: str):
    found = {"building": project.buildings, "subfield": project.subfields, "exclusion": project.exclusions}.get(kind, [])
    return next((x for x in found if x.id == oid), None)


def _current(project, kind: str, oid: str, path: str):
    if kind in SECTIONS:
        value = _get_path(getattr(project, kind), path)
        if value is None:
            schema = settings.from_dict(settings.SECTIONS[kind], {})
            for k in path.split("."):
                schema = getattr(schema, k, None)
            return schema
        return value
    thing = _thing(project, kind, oid)
    head, _dot, tail = path.partition(".")
    if thing is None:
        return None
    if head == "params" and kind == "subfield":
        return getattr(thing.layout_params(), tail, None)
    value = getattr(thing, head, None)
    return getattr(value, tail, None) if tail else value


def apply_edit(project, kind: str, oid: str, changes: dict) -> None:
    """The change of a proposal (or of a check's fix of kind "edit") made on `project`, as the window's Properties
    make it (ui/window._edited): a field of an object by path, a path of a section of the energy settings."""
    if kind in SECTIONS:
        for path, value in changes.items():
            _set_path(getattr(project, kind), path, value)
        return
    if kind == "project":
        for k, v in changes.items():
            setattr(project, k, v)
        return
    thing = _thing(project, kind, oid)
    if thing is None:
        raise ValueError(f"no {kind} {oid}")
    for path, value in changes.items():
        head, _dot, tail = path.partition(".")
        if not tail:
            setattr(thing, head, value)
        elif head == "params":
            if value is None:
                thing.params.pop(tail, None)
            else:
                thing.params[tail] = value
        else:
            setattr(getattr(thing, head), tail, value)


def check_edit(project, kind: str, oid: str, changes) -> dict:
    """The changes of a proposal typed and checked: the fields are those of `fields_of(kind)` and the project with
    them must still be a project (model's checks of a file: ranges, outlines). ValueError with what is wrong."""
    allowed = EDITABLE.get(kind) or (_section_fields(kind) if kind in SECTIONS else None)
    if allowed is None:
        raise ValueError(f"kind must be one of building, subfield, exclusion, {', '.join(SECTIONS)}")
    if kind not in SECTIONS and _thing(project, kind, oid) is None:
        raise ValueError(f"no {kind} {oid!r}")
    if not isinstance(changes, dict) or not changes:
        raise ValueError("changes: give at least one field and its value")
    wrong = [k for k in changes if k not in allowed]
    if wrong:
        raise ValueError(f"fields not allowed: {', '.join(wrong)}")
    typed = {path: _typed(path, allowed[path], value) for path, value in changes.items()}
    trial = copy.deepcopy(project)
    apply_edit(trial, kind, oid, typed)
    model.Project.from_json(trial.to_json(), check=True)
    if kind in SECTIONS:
        settings.check(kind, getattr(trial, kind), [])
    return typed


def propose_edit(host, state: State, kind: str, changes, reason: str, id: str = "") -> Outcome:  # noqa: A002
    p = host.project
    try:
        typed = check_edit(p, kind, id, changes)
    except ValueError as error:
        return _error(str(error), fields=fields_of(kind) if kind in EDITABLE or kind in SECTIONS else
                      sorted(EDITABLE) + list(SECTIONS))
    state.count += 1
    lines = [(path, _show(_current(p, kind, id, path)), _show(v)) for path, v in typed.items()]
    name = object_name(p, kind, id) if kind not in SECTIONS else ""
    title = (_("{object}: {fields}").format(object=name, fields=", ".join(typed)) if name else ", ".join(typed))
    proposal = Proposal(id=f"p{state.count}", title=title, kind=kind, oid=id, lines=lines, reason=str(reason)[:400],
                        change=lambda project, k=kind, o=id, c=typed: apply_edit(project, k, o, c))
    state.proposals[proposal.id] = proposal
    return Outcome(_json({"proposed": proposal.id, "shown_to_designer": True, "applied": False,
                          "waiting": "the designer applies it or not with a click"}),
                   _("Proposed: {what}").format(what=title), proposal=proposal)


def _index_rows(host, state: State) -> list[dict]:
    rows = list(host.index_rows()) if hasattr(host, "index_rows") else []
    return [row for row in rows if not state.cloud or not row.get("reserved", False)]


def _project_payload(row: dict, state: State) -> dict:
    state.project_count += 1
    alias = f"pr{state.project_count}"
    state.projects[alias] = row
    if state.cloud:
        keys = ("revision", "modified", "file_modified", "kind", "power_kwp")
        return {"id": alias, **{key: row.get(key) for key in keys if key in row}, "readable": not row.get("error")}
    keys = ("path", "name", "title", "series_id", "revision", "modified", "file_modified", "kind", "power_kwp",
            "job_code", "job_name", "client_name", "address", "reserved", "error")
    return {"id": alias, **{key: row.get(key) for key in keys if key in row}}


def search_projects(host, state: State, query: str = "", kind: str = "", client: str = "",
                    power_from: float = 0.0, power_to: float = float("inf"), since: str = "",
                    project_id: str = "", max_distance_km: float | None = None) -> Outcome:
    reference = state.projects.get(project_id)
    if reference is None and not project_id and hasattr(host, "path"):
        reference = next((row for row in _index_rows(host, state) if row.get("path") == str(host.path())), None)
    if project_id and reference is None:
        return _error("unknown project id: search_projects first")
    found = project_index.search(_index_rows(host, state), query, kind, client, power_from, power_to, since,
                                 reference, max_distance_km)
    projects = [_project_payload(row, state) for row in found[:20]]
    return Outcome(_json({"projects": projects, "truncated": len(found) > len(projects)}),
                   _("Searched the local project index"))


def project_revisions(host, state: State, series_id: str = "", project_id: str = "") -> Outcome:
    if project_id:
        row = state.projects.get(project_id)
        if row is None:
            return _error("unknown project id: search_projects first")
        series_id = row.get("series_id", "")
    found = project_index.revisions(_index_rows(host, state), series_id)
    projects = [_project_payload(row, state) for row in found[:20]]
    return Outcome(_json({"projects": projects, "truncated": len(found) > len(projects)}),
                   _("Read the latest project revisions"))


def _reason(row: dict) -> str:
    kind = {"roof": _("roof"), "ground": _("ground"), "mixed": _("mixed")}.get(row.get("kind"), row.get("kind", ""))
    mounting = _("same mounting") if row["same_mounting"] else _("different mounting")
    tilt = _("similar tilt") if row["same_tilt"] else _("different tilt")
    return _("{kind}, {power} kWp against {reference}, {mounting}, {tilt}, {distance} km, revision {revision} of "
             "{date}").format(kind=kind, power=number(row.get("power_kwp") or 0, 1),
                              reference=number(row["reference_power_kwp"], 1), mounting=mounting, tilt=tilt,
                              distance=number(row["distance_km"], 1), revision=row.get("revision") or "-",
                              date=str(row.get("modified") or row.get("file_modified") or "")[:10])


def similar_projects(host, state: State, project_id: str = "", power_from: float = 0.5, power_to: float = 2.0,
                     client: str = "") -> Outcome:
    reference = state.projects.get(project_id)
    if reference is None and not project_id and hasattr(host, "path"):
        reference = next((row for row in _index_rows(host, state) if row.get("path") == str(host.path())), None)
    if reference is None:
        return _error("search_projects first and give one of its project ids")
    found = project_index.similar(_index_rows(host, state), reference, power_from, power_to, client)
    projects = []
    for row in found[:20]:
        projects.append({**_project_payload(row, state), "reason": _reason(row),
                         "similarity": row["similarity"], "distance_km": row["distance_km"]})
    return Outcome(_json({"projects": projects, "truncated": len(found) > len(projects),
                          "meaning": "similarity helps a search; it is not a technical assessment"}),
                   _("Found similar projects"))


def prepare_open_project(host, state: State, project_id: str) -> Outcome:
    row = state.projects.get(project_id)
    if row is None:
        return _error("search_projects first and give one of its project ids")
    state.count += 1
    title = row.get("title") or row.get("name") or project_id
    proposal = Proposal(id=f"p{state.count}", title=title, kind="open_project", oid=project_id,
                        lines=[("Path", "", row["path"]), ("Revision", "", row.get("revision") or "-")], item=row)
    state.proposals[proposal.id] = proposal
    dirty = bool(host.dirty()) if hasattr(host, "dirty") else False
    return Outcome(_json({"proposed": proposal.id, "shown_to_designer": True, "applied": False,
                          "unsaved_changes": dirty, "waiting": "the designer confirms the path and revision"}),
                   _("Prepared opening {title}, revision {revision}").format(
                       title=title, revision=row.get("revision") or "-"), proposal=proposal)


def _task_rows(host, state: State) -> list[dict]:
    rows = list(host.task_rows()) if hasattr(host, "task_rows") else []
    return [row for row in rows if not state.cloud or not row.get("reserved", False)]


def _task_payload(row: dict, state: State) -> dict:
    state.task_count += 1
    alias = f"tk{state.task_count}"
    state.tasks[alias] = row
    if state.cloud:
        return {"id": alias, "text": row["text"], "due": row["due"], "done": row["done"]}
    keys = ("text", "due", "done", "job_id", "project_id", "job_code", "job_name", "client_name", "reserved")
    return {"id": alias, **{key: row.get(key) for key in keys if key in row}}


def list_tasks(host, state: State, include_done: bool = False, job_id: str = "", due_before: str = "") -> Outcome:
    rows = [row for row in _task_rows(host, state) if (include_done or not row["done"])
            and (not job_id or row.get("job_id") == job_id) and (not due_before or
            (row["due"] and row["due"] <= due_before))]
    tasks = [_task_payload(row, state) for row in rows[:20]]
    return Outcome(_json({"tasks": tasks, "truncated": len(rows) > len(tasks)}), _("Read the local tasks"))


def prepare_task(host, state: State, action: str, task_id: str = "", text: str = "", due: str = "",
                 job_id: str = "", project_id: str = "") -> Outcome:
    if action == "create":
        text = text.strip()
        if not text:
            return _error("a task needs text")
        if due:
            from datetime import date
            try:
                date.fromisoformat(due)
            except ValueError:
                return _error("a task due date must be ISO YYYY-MM-DD")
        item = {"action": "create", "text": text, "due": due, "job_id": job_id, "project_id": project_id}
        lines = [("Task", "", text), ("Due", "", due or "-")]
    elif action == "complete":
        row = state.tasks.get(task_id)
        if row is None:
            return _error("list_tasks first and give one of its task ids")
        text = row["text"]
        item = {"action": "complete", "task_id": row["id"]}
        lines = [("Task", "", text), ("State", "open", "done")]
    else:
        return _error("action must be create or complete")
    state.count += 1
    proposal = Proposal(id=f"p{state.count}", title=text, kind="task", oid=task_id, lines=lines, item=item)
    state.proposals[proposal.id] = proposal
    return Outcome(_json({"proposed": proposal.id, "shown_to_designer": True, "applied": False,
                          "waiting": "the designer confirms the task change"}),
                   _("Proposed: {what}").format(what=text), proposal=proposal)


def prepare_bug_report(host, state: State, summary: str, details: str = "") -> Outcome:
    if not isinstance(summary, str) or not summary.strip() or len(summary) > 180:
        return _error("give a short issue title, at most 180 characters")
    if not isinstance(details, str) or len(details) > 16000:
        return _error("details must be text of at most 16000 characters")
    host.prepare_bug_report(summary, details)
    return Outcome(_json({"draft_opened": True, "sent": False, "waiting": "the designer reviews and submits"}),
                   _("Opened a bug report draft for your review"))


def start_guided_tour(host, state: State) -> Outcome:
    host.start_guided_tour()
    return Outcome(_json({"started": True, "project_changed": False}), _("Started the guided tour"))


def propose_catalog_record(host, state: State, kind: str, record: dict) -> Outcome:
    from ..catalog import KINDS
    if kind not in KINDS or not isinstance(record, dict):
        return _error("choose a catalogue kind and a record object")
    shown = host.prepare_catalog_record(kind, record)
    return Outcome(_json({"shown_for_review": bool(shown), "saved": False}),
                   _("Prepared a catalogue record for your review"))


SPECS.update({
    "prepare_bug_report": {
        "description": "When the designer requests a bug report, or agrees to report a suspected defect, prepare an editable local draft. No report is sent. Include reproduction steps, observed and expected behaviour; never secrets or project content not requested by the designer.",
        "parameters": _schema({"summary": {"type": "string"}, "details": {"type": "string"}}, ("summary",)),
    },
    "start_guided_tour": {
        "description": "Start or resume Meridio's guided tour when the designer asks to be shown the application. Navigation only, no project changes.",
        "parameters": _schema(),
    },
    "propose_catalog_record": {
        "description": "Prepare a personal catalogue entry for the designer to review and correct. Never saves automatically. Retain the source and mark missing or uncertain technical values, never invent them.",
        "parameters": _schema({"kind": {"type": "string", "enum": ["modules", "inverters", "microinverters", "optimizers", "batteries"]}, "record": {"type": "object"}}, ("kind", "record")),
    },
})


TOOLS = {"read_checks": read_checks, "project_summary": project_summary, "go_to": go_to,
         "prepare_bug_report": prepare_bug_report, "start_guided_tour": start_guided_tour,
         "propose_catalog_record": propose_catalog_record,
         "list_navigation_targets": list_navigation_targets, "read_navigation": read_navigation,
         "search_manual": search_manual, "read_selection": read_selection, "read_results": read_results,
         "read_pedigree": read_pedigree, "read_rules": read_rules, "propose_fix": propose_fix,
         "propose_edit": propose_edit, "propose_undo": propose_undo, "search_projects": search_projects,
         "project_revisions": project_revisions, "similar_projects": similar_projects,
         "prepare_open_project": prepare_open_project, "list_tasks": list_tasks, "prepare_task": prepare_task}
