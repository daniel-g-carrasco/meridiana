"""What Meridio can do with the project (study 14, 6.4 and 6.5; task 14, steps 1 and 2): the tools the model may
call, each with its name, its description and the JSON schema of its arguments, and the function that answers it
from the project as it is now.

Reading, without asking: `read_checks`, `project_summary`, `read_selection`, `read_results`, `read_pedigree`,
`read_rules`, `vvf_activities`, `design_rules`, `search_manual`, `search_projects`, `project_revisions`, `similar_projects` and
`list_tasks`; `go_to`
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

from meridiana.core.rules import checks as checks_module
from meridiana.core.layout import layout
from meridiana.core.model import model, settings
from meridiana.app.project import project_index
from meridiana.app.profiles import registry as profiles
from meridiana.app.interface.fields import field_label, field_value, mounting_names, pitch_mode_names
from meridiana.i18n import _, number

RESULT_LIMIT = 6000             # characters of one tool's answer: the local model has 16k tokens for everything
PAGE_ROOM = 300                 # of them, kept on a page of a long answer for its «answer_page»
MANUAL_HITS = 4
LEVELS = checks_module.LEVELS   # "fail", "warn", "info", "ok"
KINDS = ("building", "subfield", "exclusion", "site", "phase", "settings", "setting", "property")
SECTIONS = ("energy", "consumption", "economics")


def _schema(properties: dict | None = None, required: tuple = ()) -> dict:
    return {"type": "object", "properties": properties or {}, "required": list(required),
            "additionalProperties": False}


# the tools as the model sees them: English for the model, the answers in the program's language
COMMON_SPECS = {
    'read_checks': {
        "description": "Read the checks of the project, the most serious first: each with an id, its level (fail, "
                       "warn, info, ok), area, text, source (the standard with edition, clause and page, or "
                       "Meridiana's own reading), the object it is about and whether Meridiana has a fix for it "
                       "(offer it with propose_fix). filtered_counts describes only the checks returned after every "
                       "filter; project_counts describes the whole project. An empty list means that nothing matches "
                       "the filters, not that the project has no checks.",
        "parameters": _schema({
            "min_level": {"type": "string", "enum": list(LEVELS),
                          "description": "the lowest level wanted: fail alone, warn and worse (default), ..."},
            "area": {"type": "string", "enum": [],
                     "description": "only the checks of this area"},
            "object_id": {"type": "string", "description": "only checks about this building, sub-field or exclusion "
                                                           "id from project_summary; a building includes its objects"}}),
    },
    'project_summary': {
        "description": "A summary of the project: the site (coordinates rounded to 0.01 degree), the buildings, "
                       "the sub-fields with their module, modules laid, power, tilt and azimuth, the inverters, "
                       "the variants, the phase open, whether the year of production is computed.",
        "parameters": _schema(),
    },
    'go_to': {
        "description": "Bring the window to an object (building, subfield, exclusion, site) or to a phase (model, "
                       "plant, production, consumption, economics, report), a settings section, a specific setting "
                       "or a property. Call list_navigation_targets for registered setting/property IDs first. "
                       "The window scrolls to and briefly highlights the target without changing any value.",
        "parameters": _schema({
            "kind": {"type": "string", "enum": list(KINDS)},
            "id": {"type": "string", "description": "the object's id from project_summary or read_checks, or "
                                                    "the phase's id, or a registered ID from list_navigation_targets"}}, ("kind",)),
    },
    'list_navigation_targets': {
        "description": "List the real settings sections, options and project property controls this version can "
                       "show with go_to. Use the returned kind and id verbatim; never invent a control ID. "
                       "This only lists destinations and changes nothing.",
        "parameters": _schema(),
    },
    'read_navigation': {
        "description": "Read the actual mouse/touchpad navigation profile, 3D orbit and pivot, and current keyboard bindings. Always use this before explaining gestures or shortcuts: they may differ from defaults. Orbit applies only to 3D; pan and pointer-centred zoom apply to both views.",
        "parameters": _schema(),
    },
    'read_more': {
        "description": "Read another page of a long answer. An answer too long for one reply comes in pages, each "
                       "whole, with answer_page: page, pages, answer_id. When answer_page says there are more pages "
                       "and the rest matters for the question, read them before you answer; never answer as if the "
                       "first page were the whole list.",
        "parameters": _schema({"answer_id": {"type": "string", "description": "answer_page.answer_id"},
                               "page": {"type": "integer", "description": "the page wanted, from 2"}},
                              ("answer_id", "page")),
    },
    'search_manual': {
        "description": "Search Meridiana's user manual (in Italian) and its commands (menu, keys) for how to do "
                       "something in the program. Use it before explaining how to use Meridiana.",
        "parameters": _schema({"query": {"type": "string", "description": "a few words, in Italian"}}, ("query",)),
    },
    'read_selection': {
        "description": "Read the object selected in the window, with the fields of its Properties panel and the "
                       "fields propose_edit accepts for it.",
        "parameters": _schema(),
    },
    'read_results': {
        "description": "Read the results computed: production (energy, specific yield, PR, the chain of the "
                       "losses, the months), strings (inputs, modules in series, voltages), consumption, economics "
                       "(self-consumption, bills, NPV, payback, LCOE).",
        "parameters": _schema({"section": {"type": "string",
                                           "enum": ["production", "strings", "consumption", "economics"]}},
                              ("section",)),
    },
    'read_pedigree': {
        "description": "Read how a result is computed, step by step: formula, the values that went in with their "
                       "source (input typed by the designer, default of Meridiana, data, norm, model, computed) "
                       "and the reference. Without `step`, every step in short; with it, the steps whose key or "
                       "title contains it, in full.",
        "parameters": _schema({
            "calculation": {"type": "string", "enum": ["production", "strings", "consumption", "economics"]},
            "step": {"type": "string"}}, ("calculation",)),
    },
    'design_rules': {
        "description": "Search Meridiana's design rules, each with its source: optimizers by maker (architecture, "
                       "modules per unit, string length, singles and doubles in one string, partial installation, "
                       "strings in parallel, module power), SolarEdge's tables of continuous and connected power per "
                       "string, how the automatic proposals use them, the DC/AC band of the inverter sizing, the "
                       "preferred makers, the fire brigade's rules for sub-fields, how an imported IFC model is placed on the "
                       "plan (mouse, coordinates, overlaps). With an inverter or optimizer model "
                       "(SE20K, S1400, SUN2000-450W-P2...) and the module's power, also what the program's rules give "
                       "for that pair. Use it before advising a choice of optimizer, inverter, ratio or maker.",
        "parameters": _schema({
            "query": {"type": "string", "description": "the designer's question or a few words, Italian or English"},
            "inverter": {"type": "string", "description": "an inverter model, e.g. SE20K"},
            "optimizer": {"type": "string", "description": "an optimizer model, e.g. S1400"},
            "module_w": {"type": "number", "description": "the module's STC power, W"}}, ("query",)),
    },
    'propose_fix': {
        "description": "Propose to the designer the fix a check already has (its id from read_checks). The "
                       "designer sees a card and applies it or not: you never apply anything. Prefer this to "
                       "propose_edit.",
        "parameters": _schema({"check_id": {"type": "string"}}, ("check_id",)),
    },
    'propose_edit': {
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
    'propose_undo': {
        "description": "Propose Undo or Redo as a card with the text of the history step. The designer applies it "
                       "with a click; you never undo or redo anything yourself. If that direction has no step, the "
                       "answer says so.",
        "parameters": _schema({"action": {"type": "string", "enum": ["undo", "redo"]}}, ("action",)),
    },
    'search_projects': {
        "description": "Search the local index of projects in linked folders by text, kind, client, power, date "
                       "or distance from a project id. The returned ids are local aliases for the other tools.",
        "parameters": _schema({"query": {"type": "string"},
                               "kind": {"type": "string", "enum": ["", "roof", "ground", "mixed"]},
                               "client": {"type": "string"}, "power_from": {"type": "number"},
                               "power_to": {"type": "number"}, "since": {"type": "string"},
                               "project_id": {"type": "string"}, "max_distance_km": {"type": "number"}}),
    },
    'project_revisions': {
        "description": "Show the latest readable revision of each project series, or of one series_id or project "
                       "alias. A newer damaged file never hides the latest valid revision.",
        "parameters": _schema({"series_id": {"type": "string"}, "project_id": {"type": "string"}}),
    },
    'similar_projects': {
        "description": "Find the latest similar projects: same kind, power within the requested range, mounting, "
                       "tilt and distance explained. Each series appears once, at its latest valid revision.",
        "parameters": _schema({"project_id": {"type": "string", "description": "an id from search_projects; empty "
                                                                                "for the project in hand"},
                               "power_from": {"type": "number"}, "power_to": {"type": "number"},
                               "client": {"type": "string"}}),
    },
    'prepare_open_project': {
        "description": "Prepare a confirmation card for opening a project id returned by another project tool. "
                       "Never opens it: only the designer's click can open, through the normal unsaved-changes flow.",
        "parameters": _schema({"project_id": {"type": "string"}}, ("project_id",)),
    },
    'list_tasks': {
        "description": "Read local tasks and due dates, optionally including completed tasks or filtering by job "
                       "or due date. The returned ids are local aliases for prepare_task.",
        "parameters": _schema({"include_done": {"type": "boolean"}, "job_id": {"type": "string"},
                               "due_before": {"type": "string"}}),
    },
    'prepare_task': {
        "description": "Prepare a card to create a local task or complete one returned by list_tasks. Never writes "
                       "the registry: only the designer's click applies the proposal.",
        "parameters": _schema({"action": {"type": "string", "enum": ["create", "complete"]},
                               "task_id": {"type": "string"}, "text": {"type": "string"},
                               "due": {"type": "string"}, "job_id": {"type": "string"},
                               "project_id": {"type": "string"}}, ("action",)),
    },
}

SPEC_ORDER = ('read_checks', 'project_summary', 'go_to', 'list_navigation_targets', 'read_navigation', 'read_more', 'search_manual', 'read_selection', 'read_results', 'read_pedigree', 'read_rules', 'vvf_activities', 'design_rules', 'search_catalog', 'propose_fix', 'propose_edit', 'propose_undo', 'search_projects', 'project_revisions', 'similar_projects', 'prepare_open_project', 'list_tasks', 'prepare_task')
STEP_1 = ("read_checks", "project_summary", "go_to", "search_manual", "list_navigation_targets", "read_navigation",
          "read_more")
STEP_2 = ("read_selection", "read_results", "read_pedigree", "read_rules", "vvf_activities", "design_rules",
          "search_catalog", "propose_fix",
          "propose_edit", "propose_undo")
STEP_3 = ("search_projects", "project_revisions", "similar_projects", "prepare_open_project", "list_tasks",
          "prepare_task", "prepare_bug_report", "start_guided_tour", "propose_catalog_record")


# What stays on while a document is in the conversation: it can only fill the review window, and the designer confirms.
# The project's tools stay off, as a document's words must not reach them.
DOCUMENT_TOOLS = ("propose_catalog_record",)


def _specs(profile_id):
    values = copy.deepcopy(COMMON_SPECS)
    values["read_checks"]["parameters"]["properties"]["area"]["enum"] = sorted(checks_module.area_names(profile_id=profile_id))
    values.update({row["name"]: {key: value for key, value in row.items() if key != "name"}
                   for row in profiles.get(profile_id).assistant_tool_specs()})
    return {name: values[name] for name in (*SPEC_ORDER, *(key for key in values if key not in SPEC_ORDER)) if name in values}


def specs(names=None, *, profile_id: str = "it") -> list[dict]:
    available = _specs(profile_id)
    return [{"name": name, **available[name]} for name in (names or (*STEP_1, *STEP_2, *STEP_3)) if name in available]


def __getattr__(name):
    if name == "SPECS":
        return _specs("it")
    raise AttributeError(name)


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
    # what the proposal was computed on (study 50, 4.1): field path -> its value then; for Undo and Redo, "step" ->
    # the history's text then. changed_since() compares them with the project before «Apply»
    before: dict = field(default_factory=dict, repr=False)


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
    pages: dict = field(default_factory=dict)      # answer id -> the pages of a long answer, for read_more
    page_count: int = 0


def _json(value) -> str:
    """A tool's answer as JSON text, whole: one longer than RESULT_LIMIT is divided in pages by run()."""
    return json.dumps(value, ensure_ascii=False, default=str)


def _size(value) -> int:
    return len(json.dumps(value, ensure_ascii=False, default=str))


def pages_of(text: str, room: int) -> list[dict]:
    """A tool's answer in pages of at most `room` characters, each whole JSON (study 50, 3.3 point 3): the longest list
    of the answer divided between them, what is not the list on the first page; an answer without such a list (or with
    an element alone beyond the room) as pieces of its text, «part», to be joined in their order."""
    value = json.loads(text)
    if not isinstance(value, dict):
        value = {"items": value}
    lists = [(_size(v), k) for k, v in value.items() if isinstance(v, list) and len(v) > 1]
    if lists:
        key = max(lists)[1]
        head = {k: v for k, v in value.items() if k != key}
        pages: list[dict] = []
        chunk: list = []

        def page(items) -> dict:
            return {**(head if not pages else {"continued": key}), key: items}
        for item in value[key]:
            if chunk and _size(page([*chunk, item])) > room:
                pages.append(page(chunk))
                chunk = []
            chunk.append(item)
        pages.append(page(chunk))
        if all(_size(p) <= room for p in pages):
            return pages
    out, start = [], 0
    while start < len(text):
        end = min(len(text), start + room)
        while _size({"part": text[start:end]}) > room:
            end = start + max(1, (end - start) * 9 // 10)
        out.append({"part": text[start:end]})
        start = end
    return out


def _paged(outcome: Outcome, state: State) -> Outcome:
    """The outcome as it goes to the model: whole when it fits, else its first page, the others kept for read_more."""
    if len(outcome.content) <= RESULT_LIMIT:
        return outcome
    pages = pages_of(outcome.content, RESULT_LIMIT - PAGE_ROOM)
    state.page_count += 1
    answer = f"a{state.page_count}"
    total = len(pages)
    state.pages[answer] = [_json({**p, "answer_page": {
        "page": n, "pages": total, "answer_id": answer,
        "next": f"read_more with answer_id {answer} and page {n + 1}" if n < total else "this is the last page"}})
        for n, p in enumerate(pages, 1)]
    outcome.content = state.pages[answer][0]
    return outcome


def _error(text: str, **more) -> Outcome:
    return Outcome(_json({"error": text, **more}), error=True)


def run(name: str, arguments, host, state: State) -> Outcome:
    """One call of the model: its answer (its first page, when it is long), or an error it can read and correct."""
    project = getattr(host, "project", None)
    available = _specs(project.regulatory_profile if project is not None else "it")
    if name not in available:
        return _error(f"no tool named {name!r}", tools=sorted(available))
    if not isinstance(arguments, dict):
        return _error("the arguments are not a JSON object")
    try:
        return _paged(_quoted(TOOLS[name](host, state, **arguments)), state)
    except TypeError as error:          # an argument the tool does not take
        return _error(f"bad arguments: {error}", schema=available[name]["parameters"])
    except (ValueError, KeyError) as error:
        return _error(str(error))


def _quoted(outcome: Outcome) -> Outcome:
    """R649: an answer in another language than the program's (the Italian manual, a law, a standard) said to be a
    quotation, with the language to answer in: a small model wrote its answer in the language it had read."""
    from meridiana import i18n
    from . import languages, persona
    program = i18n.language().lower()
    if outcome.error or program not in persona.LANGUAGES:
        return outcome
    found = languages.detect(outcome.content, least=6)
    if not found or found == program:
        return outcome
    try:
        data = json.loads(outcome.content)
    except ValueError:
        return outcome
    if not isinstance(data, dict):
        return outcome
    head = {"quoted_language": persona.LANGUAGES[found],
            "answer_in": persona.LANGUAGES[program] + ": quote the text above in its language, in quotation marks, "
                         "and write your answer in " + persona.LANGUAGES[program]}
    return dataclasses.replace(outcome, content=_json({**head, **data}))     # first: on the first page of a long one


def read_more(host, state: State, answer_id: str, page) -> Outcome:
    """Another page of a long answer of this conversation."""
    pages = state.pages.get(str(answer_id))
    if pages is None:
        return _error(f"no answer {answer_id!r} in this conversation: call the tool again",
                      answers=sorted(state.pages))
    if isinstance(page, float) and page.is_integer():
        page = int(page)
    if page.__class__ is not int or not 1 <= page <= len(pages):
        return _error(f"page must be a whole number from 1 to {len(pages)}")
    return Outcome(pages[page - 1])


# names

def object_name(project, kind: str, oid: str) -> str:
    """What the tree calls an object: «Sud», «Lucernario 2»; the site by the project's name."""
    if kind == "building":
        b = project.building(oid)
        return b.name if b else oid
    if kind == "subfield":
        sf = next((s for s in project.subfields if s.id == oid), None)
        from meridiana.core.model import imported
        return imported.subfield_name(project, sf) if sf else oid
    if kind == "exclusion":
        e = next((x for x in project.exclusions if x.id == oid), None)
        if e is None:
            return oid
        return f"{model.exclusion_names(profile_id=project.regulatory_profile).get(e.kind, e.kind)} {project.exclusion_numbers()[e.id]}"
    if kind == "site":
        return _("the site")
    if kind == "phase":
        from meridiana.app.interface import phases
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
    names = checks_module.area_names(profile_id=getattr(getattr(host, "project", None), "regulatory_profile", "it"))
    levels = checks_module.level_names()
    out = []
    selected = []
    state.checks = {}
    for n, it in enumerate(items, 1):
        cid = f"c{n}"
        state.checks[cid] = it
        # R605: a row that stands for several objects (members) is about each of them
        targets = (it.target, *getattr(it, "members", ()))
        if (LEVELS.index(it.level) > top or (area and it.area != area)
                or not any(_about_object(host.project, t, object_id) for t in targets)):
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


def _activity_name(fire, *, profile_id="it"):
    from meridiana.app.profiles import registry
    return registry.get(profile_id).activity_name(fire)


def project_summary(host, state: State) -> Outcome:
    p = host.project
    subfields = []
    total = 0.0
    for sf in p.subfields:
        laid = _laid(host, sf)
        module = _module(p, sf)
        kw = laid * float(module.get("power_kw") or 0.0)
        total += kw
        params = sf.layout_params(profile_id=p.regulatory_profile)
        subfields.append({"id": sf.id, "name": object_name(p, "subfield", sf.id), "on": object_name(p, "building", sf.building)
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
                  **profiles.for_project(p).building_summary(b)} for b in p.buildings]
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
           # the title the designer reads (study 50, 3.6): with the id «plant» beside «Impianto» a small model wrote «[plant]»
           "phase": object_name(p, "phase", host.phase()), "selection": _target(p, host.selection()),
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
        from meridiana.app.interface import phases
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


def manual_passages(*, profile_id: str = "it") -> list[tuple[str, str, str]]:
    """Manual paragraphs in the interface language, with Italian section fallback and regulatory scope."""
    from meridiana.app.interface import help as helps
    out: list = []
    for name in helps.CHAPTERS:
        sections = helps.manual_sections(name)
        if not sections:
            continue
        title = sections[0][1]
        for _level, heading, anchor, text in sections:
            if not profiles.get(profile_id).manual_section_allowed(name, anchor):
                continue
            for block in re.split(r"\n\s*\n", text):
                if block.strip():
                    out.append((title, heading, block.strip()))
    return out


def search_manual(host, state: State, query: str) -> Outcome:
    words = _words(query)
    if not words:
        raise ValueError("query: write a few words")
    scored = []
    for title, heading, text in manual_passages(profile_id=getattr(getattr(host, "project", None), "regulatory_profile", "it")):
        hay = _fold(f"{heading} {text}")
        score = sum(hay.count(w) for w in words) + 2 * sum(w in _fold(heading) for w in words)
        hits = sum(w in hay for w in words)
        if hits:
            scored.append((hits, score, title, heading, text))
    scored.sort(key=lambda s: (-s[0], -s[1]))
    passages = [{"chapter": t, "heading": h, "text": x[:900]} for _h, _s, t, h, x in scored[:MANUAL_HITS]]
    from meridiana.app.interface import shortcuts
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
            "free_pitches": len(b.roof.free_pitches)},
            **profiles.for_project(p).building_details(b),
            "area_m2": round(shape.area, 1), "perimeter_m": round(shape.length, 1),
            "subfields": [object_name(p, "subfield", s.id) for s in p.subfields if s.building == b.id],
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
                    "base_m": e.base, "clearance_m": e.clearance, "on": object_name(p, "building", e.building) if e.building else
                    "ground"})
    else:
        out.update({"kind": "site", "site": {"lat": round(p.site.lat, 2), "lon": round(p.site.lon, 2)},
                    "address": p.site.address, "sun_window": p.sun_window})
    if kind in EDITABLE:
        out["fields_for_propose_edit"] = fields_of(kind, profile_id=p.regulatory_profile)
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
        from meridiana.core.energy.optimizers import OptimizedPlan
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


def read_rules(host, state: State, rule_id: str = "") -> Outcome:
    from meridiana.app.profiles import registry
    return registry.for_project(host.project).read_rules(host, state, rule_id)


def _rule_in_short(rules, r, f) -> dict:
    return {"id": r.id, "rule": rules.title(r, f), "source": r.source(), "level": r.level,
            "text": "read it with rule_id"}


def vvf_activities(host, state: State, query: str = "") -> Outcome:
    from meridiana.app.profiles import registry
    return registry.for_project(host.project).vvf_activities(host, state, query)


def design_rules(host, state: State, query: str, inverter: str = "", optimizer: str = "",
                 module_w: float | None = None, *, profile_id: str = "it") -> Outcome:
    """The design rules (R462): assistant/design_rules.py builds them from the data the program designs with."""
    from . import design_rules as knowledge
    project = getattr(host, "project", None)
    if project is not None:
        profile_id = project.regulatory_profile
    if not str(query or "").strip() and not inverter and not optimizer:
        raise ValueError("query: write the question or a few words")
    try:
        watts = float(module_w) if module_w not in (None, "") else None
    except (TypeError, ValueError):
        raise ValueError("module_w: a number of watts") from None
    out = knowledge.fitted(knowledge.search(str(query or ""), str(inverter or ""), str(optimizer or ""), watts, profile_id=profile_id),
                           RESULT_LIMIT - 200)
    return Outcome(_json(out), _("Read the design rules: «{query}»").format(query=query))


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
                        reason=_("Step: {step}").format(step=step), before={"step": step})
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
    lines, change, network, was = [], None, False, {}
    if fix[0] == "energy":
        path, value = fix[1], fix[2]
        before = _get_path(p.energy, path)
        lines = [(path, _show(before), _show(value))]
        change = lambda project, path=path, value=value: _set_path(project.energy, path, value)    # noqa: E731
        kind, oid = "energy", ""
        was = {path: copy.deepcopy(_current(p, kind, oid, path))}
    elif fix[0] == "edit":
        kind, oid, changes = fix[1], fix[2], dict(fix[3])
        lines = [(path, _show(_current(p, kind, oid, path)), _show(v)) for path, v in changes.items()]
        change = lambda project, k=kind, o=oid, c=changes: apply_edit(project, k, o, c)            # noqa: E731
        was = {path: copy.deepcopy(_current(p, kind, oid, path)) for path in changes}
    else:
        kind, oid = (fix[2], fix[3]) if fix[0] == "action" and len(fix) > 3 else ("", "")
        network = fix[0] == "compute"
    proposal = Proposal(id=f"p{state.count}", title=it.fix_label or it.text, kind=kind, oid=oid, lines=lines,
                        reason=it.text, source=it.source, change=change, item=None if change else it,
                        network=network, before=was)
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
                 "fire.activity": WHOLE, "fire.category": ("", *tuple("ABC")),
                 "fire.roof_fire_resistant": SWITCH},
    "subfield": {"name": TEXT, "params.mounting": tuple(sorted(layout.MOUNTINGS)), "params.portrait": SWITCH,
                 "params.stack": WHOLE, "params.tilt": NUMBER, "params.azimuth": NUMBER, "params.gap": NUMBER,
                 "params.edge": NUMBER, "params.shade_free": SWITCH, "params.flush_row_gap": NUMBER,
                 "params.table_modules": WHOLE, "params.table_gap": NUMBER, "params.pitch_mode": ("sun", "value", "gcr"),
                 "params.pitch": NUMBER, "params.gcr": NUMBER},
    "exclusion": {"kind": model.EXCLUSION_KINDS, "height": NUMBER, "base": NUMBER, "clearance": NUMBER},
}
NULLABLE = {"params.azimuth", "height", "roof.ridge_height"}       # None: automatic, the kind's default


def _section_fields(section: str, *, profile_id="it") -> dict:
    """The scalar fields of a section of the energy settings (settings.py), by path, with their type."""
    out = {}

    def walk(kls, prefix: str) -> None:
        for f in dataclasses.fields(kls):
            values = settings.initial_values(kls, profile_id)
            default = (values[f.name] if f.name in values else
                       f.default if f.default is not dataclasses.MISSING else f.default_factory())
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


def fields_of(kind: str, *, profile_id: str = "it") -> dict:
    """The fields propose_edit takes for a kind, path -> its type or the words allowed."""
    table = EDITABLE.get(kind) or (_section_fields(kind, profile_id=profile_id) if kind in SECTIONS else {})
    table = profiles.get(profile_id).editable(kind, table)
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
    from meridiana.app.session import set_path
    set_path(data, path, value)


def _thing(project, kind: str, oid: str):
    found = {"building": project.buildings, "subfield": project.subfields, "exclusion": project.exclusions}.get(kind, [])
    return next((x for x in found if x.id == oid), None)


def _current(project, kind: str, oid: str, path: str):
    if kind in SECTIONS:
        value = _get_path(getattr(project, kind), path)
        if value is None:
            schema = settings.from_dict(settings.SECTIONS[kind], {}, profile_id=project.regulatory_profile)
            for k in path.split("."):
                schema = getattr(schema, k, None)
            return schema
        return value
    thing = _thing(project, kind, oid)
    head, _dot, tail = path.partition(".")
    if thing is None:
        return None
    if head == "params" and kind == "subfield":
        return getattr(thing.layout_params(profile_id=project.regulatory_profile), tail, None)
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
    allowed = EDITABLE.get(kind) or (_section_fields(kind, profile_id=project.regulatory_profile) if kind in SECTIONS else None)
    if allowed is not None:
        allowed = profiles.for_project(project).editable(kind, allowed)
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
    if kind == "building" and typed.get("fire.activity"):
        typed["fire.subject"] = True            # R327: an activity chosen turns the switch on, as in the Properties
    trial = copy.deepcopy(project)
    apply_edit(trial, kind, oid, typed)
    model.Project.from_json(trial.to_json(), check=True)
    if kind in SECTIONS:
        settings.check(kind, getattr(trial, kind), [], profile_id=project.regulatory_profile)
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
                        change=lambda project, k=kind, o=id, c=typed: apply_edit(project, k, o, c),
                        before={path: copy.deepcopy(_current(p, kind, id, path)) for path in typed})
    state.proposals[proposal.id] = proposal
    return Outcome(_json({"proposed": proposal.id, "shown_to_designer": True, "applied": False,
                          "waiting": "the designer applies it or not with a click"}),
                   _("Proposed: {what}").format(what=title), proposal=proposal)


def shown_label(kind: str, path: str) -> str:
    """A field of a proposal as the card names it (the Properties' words; a section's field by its last part)."""
    return field_label(path.split(".")[-1] if kind in SECTIONS else path, kind)


def changed_since(proposal: Proposal, host) -> str:
    """Whether a proposal can still be applied as the card shows it (study 50, 4.1): "" when the project still holds
    the values it was made on, otherwise what changed, in words for the designer. Between the card and «Apply» the
    designer may have typed another value, deleted the object, fixed the check or moved in the history: a change
    computed on what is no longer there is not applied."""
    if proposal.kind == "history":
        if "step" not in proposal.before or not hasattr(host, "history_text"):
            return ""
        now = host.history_text(proposal.oid)
        if now != proposal.before.get("step"):
            return _("the history has changed: the step is now «{step}»").format(step=now or "-")
        return ""
    if proposal.kind in ("open_project", "task"):
        return ""
    project = host.project
    if proposal.change is None:                     # a check's own fix (an action, a computation)
        if proposal.item is not None and proposal.item not in list(host.checks()):
            return _("the check is no longer there: the project has changed")
        return ""
    if proposal.kind in EDITABLE and _thing(project, proposal.kind, proposal.oid) is None:
        return _("what it was about is no longer in the project")
    for path, was in proposal.before.items():
        now = _current(project, proposal.kind, proposal.oid, path)
        if now != was:
            return _("{field} is now {now}, not {before} as when it was proposed").format(
                field=shown_label(proposal.kind, path), now=_show(now), before=_show(was))
    return ""


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
    from meridiana.data.catalog import KINDS
    if kind not in KINDS or not isinstance(record, dict):
        return _error("choose a catalogue kind and a record object")
    if not hasattr(host, "prepare_catalog_record"):
        return _error("this window cannot show a catalogue review")
    shown = host.prepare_catalog_record(kind, record)
    return Outcome(_json({"shown_for_review": bool(shown), "saved": False}),
                   _("Prepared a catalogue record for your review"))


# the catalogue, read only (study 50, 5.2): a few rows, each with the data that count for its kind
CATALOG_ROWS = 8
CATALOG_DATA = {
    "modules": ("pmax", "efficiency_pct", "voc", "isc", "length", "width", "bifacial"),
    "inverters": ("ac_power_nominal_w", "phases", "mppt_count", "dc_voltage_max_v", "mppt_voltage_min_v",
                  "mppt_voltage_max_v", "efficiency_euro_pct"),
    "microinverters": ("ac_power_nominal_w", "phases", "modules_per_unit", "dc_power_max_per_input_w"),
    "optimizers": ("rated_input_power_w", "max_input_voltage_v", "modules_per_unit", "efficiency_weighted_pct"),
    "batteries": ("usable_energy_kwh", "coupling", "max_charge_power_w", "max_discharge_power_w",
                  "round_trip_efficiency_pct"),
}


def _origin_names() -> dict:
    return {"curated": _("Datasheets read for Meridiana"), "cec": _("CEC list (USA)"),
            "personal": _("Personal catalogue")}


def _state_names() -> dict:
    from meridiana.data import catalog
    return {catalog.CURRENT: _("Current"), catalog.PHASING_OUT: _("Phasing out"),
            catalog.DISCONTINUED: _("Out of production"), catalog.UNKNOWN: _("State unknown")}


def _catalog_value(f, value) -> str:
    """A value of a product as its card writes it: the number with its unit, a choice by its name."""
    if f.type == "yesno" or isinstance(value, bool):
        return _("yes") if value else _("no")
    if f.choices:
        return _(dict(f.choices).get(str(value), str(value)))
    if isinstance(value, (int, float)):
        text = number(value, 0 if abs(value) >= 100 or float(value).is_integer() else 2)
        return f"{text} {f.unit}".strip()
    return str(value)


def _product(rec: dict, kind: str) -> dict:
    from meridiana.data import catalog
    from meridiana.data.catalog import schema
    known = {f.key: f for f in schema.fields(kind)}
    data = {_(known[key].label): _catalog_value(known[key], rec[key])
            for key in CATALOG_DATA[kind] if key in known and rec.get(key) not in (None, "", [])}
    row = {"id": rec.get("id"), "manufacturer": rec.get("manufacturer", ""), "model": rec.get("model", ""),
           "data": data, "origin": _origin_names().get(rec.get("source"), str(rec.get("source") or "")),
           "state": _state_names()[catalog.lifecycle_state(rec)]}
    if rec.get("datasheet_url"):
        row["datasheet"] = rec["datasheet_url"]
    return row


def search_catalog(host, state: State, kind: str, query: str = "", power_from: float = 0.0, power_to: float = 0.0,
                   state_of_production: str = "", include_us_list: bool = False) -> Outcome:
    """The product catalogue searched (data/catalog.search), never changed. The CEC list (US models, 60 Hz) is left
    out unless asked, as the catalogue's page leaves it out with its market filter."""
    from meridiana.data import catalog
    if kind not in catalog.KINDS:
        raise ValueError(f"kind must be one of {', '.join(catalog.KINDS)}")
    if state_of_production and state_of_production not in catalog.LIFECYCLE_STATES:
        raise ValueError(f"state_of_production must be one of {', '.join(catalog.LIFECYCLE_STATES)}")
    try:
        low, high = float(power_from or 0.0), float(power_to or 0.0)
    except (TypeError, ValueError):
        raise ValueError("power_from and power_to: numbers, W (kWh for batteries)") from None
    found = catalog.search(kind, str(query or ""), low=low, high=high, limit=None,
                           states=(state_of_production,) if state_of_production else ())
    if not include_us_list:
        found = [r for r in found if r.get("source") != "cec"]
    out = {"kind": kind, "found": len(found), "products": [_product(r, kind) for r in found[:CATALOG_ROWS]]}
    if not found:
        out["message"] = "nothing in the catalogue matches: fewer words, another power range" + (
            "" if include_us_list else ", or include_us_list")
    elif len(found) > CATALOG_ROWS:
        out["more"] = f"{len(found) - CATALOG_ROWS} more match: narrow with words or power to see them"
    return Outcome(_json(out), _("Searched the catalogue"))


def slow_reads(calls) -> list[Callable]:
    """What a round's calls need read before they run, and that would hold the window if read on its thread: the
    catalogue of a kind not yet read (catalog.ready; 21,000 modules, more than a second). The window runs these away
    from its thread, as the catalogue page reads it, then runs the tools."""
    from functools import partial
    from meridiana.data import catalog
    kinds = []
    for c in calls:
        kind = (getattr(c, "arguments", None) or {}).get("kind") if getattr(c, "name", "") == "search_catalog" else None
        if kind in catalog.KINDS and kind not in kinds and not catalog.ready(kind):
            kinds.append(kind)
    return [partial(catalog.prepare, kind) for kind in kinds]


COMMON_SPECS.update({
    "search_catalog": {
        "description": "Search the product catalogue of this PC (PV modules, inverters, microinverters, optimizers, "
                       "batteries) by words of maker, model or series, by power and by production state. Read only: "
                       "it changes nothing and chooses nothing. It gives at most 8 products, the ones read from the "
                       "datasheets first, each with its maker, model, main data with units, where the data come "
                       "from and whether it is still made, and how many match in all. The CEC list (US models) is "
                       "left out unless include_us_list is true. Use it before naming a product of the catalogue.",
        "parameters": _schema({
            "kind": {"type": "string", "enum": ["modules", "inverters", "microinverters", "optimizers", "batteries"]},
            "query": {"type": "string", "description": "words of maker, model or series, e.g. huawei 50ktl"},
            "power_from": {"type": "number", "description": "W (kWh for batteries); AC power for inverters"},
            "power_to": {"type": "number", "description": "W (kWh for batteries)"},
            "state_of_production": {"type": "string", "enum": ["current", "phasing_out", "discontinued", "unknown"]},
            "include_us_list": {"type": "boolean"}}, ("kind",)),
    },
    "prepare_bug_report": {
        "description": "When the designer requests a bug report, or agrees to report a suspected defect, prepare an editable local draft. No report is sent. Include reproduction steps, observed and expected behaviour; never secrets or project content not requested by the designer.",
        "parameters": _schema({"summary": {"type": "string"}, "details": {"type": "string"}}, ("summary",)),
    },
    "start_guided_tour": {
        "description": "Start or resume Meridio's guided tour when the designer asks to be shown the application. Navigation only, no project changes.",
        "parameters": _schema(),
    },
    "propose_catalog_record": {
        "description": "Fill the catalogue's review window with a product, for the designer to check and confirm; it never saves. Call it when the designer asks to add a product or a datasheet. Fields of `record`: manufacturer, model, datasheet_url and those of the kind, with the units of the catalogue (metres for a module's size): modules pmax vmp imp voc isc gamma_pmax beta_voc alpha_isc length width cells max_system_voltage_v max_series_fuse_a and classes (one {pmax, vmp, imp, voc, isc} per power class, each from its own column); inverters ac_power_nominal_w phases dc_voltage_max_v mppt_voltage_min_v mppt_voltage_max_v mppt_count dc_current_max_per_mppt_a dc_isc_max_per_mppt_a efficiency_euro_pct; microinverters ac_power_nominal_w modules_per_unit dc_power_max_per_input_w dc_voltage_max_v mppt_voltage_min_v mppt_voltage_max_v dc_current_max_per_input_a dc_isc_max_per_input_a efficiency_weighted_pct; optimizers rated_input_power_w max_input_voltage_v mppt_voltage_min_v mppt_voltage_max_v max_input_isc_a max_output_current_a modules_per_unit efficiency_weighted_pct compatible_inverters; batteries usable_energy_kwh coupling max_charge_power_w max_discharge_power_w round_trip_efficiency_pct. Only what the source states: leave out the rest, never a typical value.",
        "parameters": _schema({"kind": {"type": "string", "enum": ["modules", "inverters", "microinverters", "optimizers", "batteries"]}, "record": {"type": "object"}}, ("kind", "record")),
    },
})


TOOLS = {"read_checks": read_checks, "project_summary": project_summary, "go_to": go_to,
         "prepare_bug_report": prepare_bug_report, "start_guided_tour": start_guided_tour,
         "propose_catalog_record": propose_catalog_record,
         "list_navigation_targets": list_navigation_targets, "read_navigation": read_navigation,
         "read_more": read_more,
         "search_manual": search_manual, "read_selection": read_selection, "read_results": read_results,
         "read_pedigree": read_pedigree, "read_rules": read_rules, "vvf_activities": vvf_activities,
         "design_rules": design_rules, "search_catalog": search_catalog,
         "propose_fix": propose_fix,
         "propose_edit": propose_edit, "propose_undo": propose_undo, "search_projects": search_projects,
         "project_revisions": project_revisions, "similar_projects": similar_projects,
         "prepare_open_project": prepare_open_project, "list_tasks": list_tasks, "prepare_task": prepare_task}
