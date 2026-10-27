"""The session: the live truth of the work in hand, without Qt. The project and its file, the layouts of
the sub-fields with the keys they were made from, the energy year, the selection, the undo by snapshots,
what counts as "modified", the recovery copies. The window shows the session and reports the gestures to
it; a change of the project goes through `edit`, which takes the snapshot before and after and tells the
listeners what changed (study 18, A 9.1 and 9.3, step 2).

The undo keeps the project as JSON before and after each step: cheap and exact for projects of this size
(1,5 ms a snapshot on 20 buildings, A 4.2), and every edit is undoable without writing an undo for each.
A change that raises leaves the project as it was (A 4.3, defect 1)."""

from __future__ import annotations

import copy
import dataclasses
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from . import model, recovery

UNDO_LIMIT = 200                # steps kept: at 0,2 MB a step on a large project, 40 MB at most
MERGE_SECONDS = 2.0             # the arrows of a field clicked again and again are one step

# The topics a change is told by (the window draws by topic, never "everything"; study 18, A 9.1):
#   project:text        the names (of the project, a building, a sub-field), the project reserved or not
#   project:geometry    a building's outline, height, roof or parapet, a building or an exclusion added, removed
#                       or changed: the shapes and the shadows
#   project:subfields   a sub-field, anything but its name
#   project:fire        the fire data of a building (the layout's fire rules, the checks)
#   project:site        the site or the design window
#   project:energy      energy, consumption, economics, the modules of the project
#   project:rules       the rules of the project (connection, obligation...)
#   project:variants    the variants, or the one in hand
#   project:underlays   the images under the drawing
#   project:report      the report's choices (template, chapters, profile, client)
#   restored            with the topics above: an undo or a redo put the project back
#   file                another project took the place of this one
#   layout:<id>         the layout of that sub-field came back (new, or gone)
#   energy              the energy year came back
#   selection           what is selected
#   checks              the inputs of the checks changed (with the topics that changed them)
GEOMETRY = ("footprint", "height", "roof", "parapet")
NO_LAYOUT = {"project:text", "project:underlays", "project:rules", "project:report"}   # what never moves a module
CHECK_INPUTS = {"project:text", "project:fire", "project:rules", "project:energy", "project:subfields",
                "project:geometry", "project:site", "project:variants"}


def design_of(data: dict) -> dict:
    """The design of the variant in hand, in a snapshot of the project (to_json, format 7 and 8)."""
    return next((v.get("design") or {} for v in data.get("variants") or [] if v.get("id") == data.get("variant")), {})


def topics_of(before: dict, after: dict) -> set[str]:
    """The topics of what differs between two snapshots of the project (to_json)."""
    topics: set[str] = set()
    if before.get("name") != after.get("name") or before.get("reserved") != after.get("reserved"):
        topics.add("project:text")
    if before.get("site") != after.get("site") or before.get("sun_window") != after.get("sun_window"):
        topics.add("project:site")
    old, new = design_of(before), design_of(after)
    if (before.get("consumption") != after.get("consumption")
            or any(old.get(k) != new.get(k) for k in ("energy", "economics", "modules"))):
        topics.add("project:energy")
    if before.get("rules") != after.get("rules") or before.get("network") != after.get("network"):
        topics.add("project:rules")
    heads = ([{k: v for k, v in var.items() if k != "design"} for var in data.get("variants") or []]
             for data in (before, after))
    if next(heads) != next(heads) or before.get("variant") != after.get("variant"):
        topics.add("project:variants")
    if before.get("underlays") != after.get("underlays"):
        topics.add("project:underlays")
    if (before.get("report") or {}) != (after.get("report") or {}):
        topics.add("project:report")
    a, b = before.get("buildings") or [], after.get("buildings") or []
    if a != b:
        pairs = list(zip(a, b, strict=False))
        if len(a) != len(b) or any(x.get("id") != y.get("id") or any(x.get(k) != y.get(k) for k in GEOMETRY)
                                   for x, y in pairs):
            topics.add("project:geometry")
        if any(x.get("fire") != y.get("fire") for x, y in pairs):
            topics.add("project:fire")
        if any(x.get("name") != y.get("name") for x, y in pairs):
            topics.add("project:text")
    if (before.get("exclusions") or []) != (after.get("exclusions") or []):
        topics.add("project:geometry")
    a, b = old.get("subfields") or [], new.get("subfields") or []
    if a != b:
        pairs = list(zip(a, b, strict=False))
        if len(a) != len(b) or any({**x, "name": ""} != {**y, "name": ""} for x, y in pairs):
            topics.add("project:subfields")
        if any(x.get("name") != y.get("name") for x, y in pairs):
            topics.add("project:text")
    if topics & CHECK_INPUTS:
        topics.add("checks")
    return topics


def needs_layout(topics: set) -> bool:
    """Whether what changed can move a module: a name, a rule or an image never does (undone or redone, the
    same: the topics are those of the difference)."""
    return any(t.startswith("project:") and t not in NO_LAYOUT for t in topics)


def set_path(data: dict, path: str, value) -> None:
    """data["a"]["b"] = value for "a.b"; None takes the key away (back to the default)."""
    keys = path.split(".")
    for k in keys[:-1]:
        data = data.setdefault(k, {})
    if value is None:
        data.pop(keys[-1], None)
    else:
        data[keys[-1]] = value


@dataclass
class Step:
    """One undoable step: the project before and after, as `to_json` gave it."""
    text: str
    before: dict
    after: dict
    merge: object = None            # steps with the same key within MERGE_SECONDS join (None: never)
    when: float = field(default_factory=time.monotonic)


class Undo:
    """The stack of the steps, with the index of the step the project stands at, the clean index (where it
    was saved) and a limit on the steps kept. `restore(data)` puts the project back to a snapshot; the
    listeners are told after every change of the stack."""

    def __init__(self, restore: Callable[[dict], None], limit: int = UNDO_LIMIT, merge_seconds: float = MERGE_SECONDS):
        self.restore = restore
        self.limit = max(1, int(limit))
        self.merge_seconds = merge_seconds
        self.steps: list[Step] = []
        self.index = 0                  # steps[:index] are done
        self.clean_index = 0            # -1: the saved state is no longer on the stack
        self.listeners: list[Callable[[], None]] = []

    def _tell(self) -> None:
        for listener in self.listeners:
            listener()

    def push(self, step: Step) -> None:
        del self.steps[self.index:]
        if self.clean_index > self.index:
            self.clean_index = -1
        top = self.steps[-1] if self.steps else None
        if (top is not None and step.merge is not None and top.merge == step.merge
                and step.when - top.when <= self.merge_seconds and self.index != self.clean_index):
            top.after, top.when = step.after, step.when
        else:
            self.steps.append(step)
            self.index += 1
            if len(self.steps) > self.limit:
                drop = len(self.steps) - self.limit
                del self.steps[:drop]
                self.index -= drop
                self.clean_index = self.clean_index - drop if self.clean_index >= drop else -1
        self._tell()

    def undo(self) -> None:
        if not self.can_undo():
            return
        self.index -= 1
        self.restore(self.steps[self.index].before)
        self._tell()

    def redo(self) -> None:
        if not self.can_redo():
            return
        self.restore(self.steps[self.index].after)
        self.index += 1
        self._tell()

    def take_back(self) -> None:
        """The last step undone and forgotten, with no redo left: a fix shown as a preview and refused (R126)."""
        if not self.can_undo() or self.can_redo():
            return
        self.index -= 1
        step = self.steps.pop()
        if self.clean_index > self.index:
            self.clean_index = -1
        self.restore(step.before)
        self._tell()

    def can_undo(self) -> bool:
        return self.index > 0

    def can_redo(self) -> bool:
        return self.index < len(self.steps)

    def undo_text(self) -> str:
        return self.steps[self.index - 1].text if self.can_undo() else ""

    def redo_text(self) -> str:
        return self.steps[self.index].text if self.can_redo() else ""

    def count(self) -> int:
        return len(self.steps)

    def is_clean(self) -> bool:
        return self.clean_index == self.index

    def set_clean(self) -> None:
        self.clean_index = self.index
        self._tell()

    def clear(self) -> None:
        self.steps, self.index, self.clean_index = [], 0, 0
        self._tell()


class ProjectSession:
    """The work in hand. `project` and `path`; `results` (sub-field id -> layout.Result or the exception that
    stopped it) with `layout_keys` (id -> the inputs of that result, model.layout_key); `energy` (what
    energy/pipeline.py gave, as a dict); the generations that tell an old result from the one awaited; the
    selection; the undo; what was saved.

    Listeners are called with the set of the topics that changed (the list above): after every edit, undo
    or redo the topics of what differs; "file" when another project took the place of this one; "layout:<id>"
    and "energy" when a result comes back; "selection"."""

    def __init__(self, project: model.Project | None = None, path: Path | None = None, undo_limit: int = UNDO_LIMIT):
        self.project = project if project is not None else model.Project()
        self.path: Path | None = path
        self.results: dict = {}
        self.layout_keys: dict = {}
        self.energy: dict = {}
        self.generation = 0             # of the layouts asked for
        self.energy_generation = 0      # of the energy years asked for
        self.energy_key_asked = ""      # the inputs of the energy year asked for last, and of the one in hand
        self.energy_key_computed = ""
        self.selection = ("site", "")
        self.selected_module = ("", "")
        self.undo = Undo(self._restore, undo_limit)
        self.saved_state: str | None = self.state_key()
        self.autosaved: Path | None = None
        self.listeners: list[Callable[[set], None]] = []

    # events

    def subscribe(self, listener: Callable[[set], None]) -> None:
        self.listeners.append(listener)

    def changed(self, *topics: str) -> None:
        told = set(topics)
        for listener in list(self.listeners):
            listener(told)

    # the project as data

    def snapshot(self) -> dict:
        return copy.deepcopy(self.project.to_json())

    def _restore(self, data: dict) -> None:
        topics = topics_of(self.project.to_json(), data)
        self.project = model.Project.from_json(copy.deepcopy(data), check=False)
        self.changed("restored", *topics)

    def edit(self, text: str, change: Callable[[model.Project], object], merge=None) -> set[str]:
        """Apply `change(project)` as one undoable step; with `merge`, a step that follows the same kind of
        change within a moment joins the last one. If `change` raises, the project is put back as it was
        before and the error goes on to the caller. The topics of what changed (empty: nothing did, and
        nobody is told)."""
        before = self.snapshot()
        try:
            change(self.project)
        except Exception:
            self.project = model.Project.from_json(before, check=False)
            raise
        after = self.snapshot()
        topics = topics_of(before, after) if before != after else set()
        if topics:
            self.undo.push(Step(text, before, after, merge))
            self.changed(*topics)
        return topics

    def amend(self, change: Callable[[model.Project], object]) -> set[str]:
        """Apply `change(project)` without an undo step: what the program writes down by itself and Ctrl+Z must not
        take back (the proposal of a project of before format 14 made the designer's strings at the first layout:
        undone, it would be written down again at once). If the project was saved as it was, it still counts as
        saved: nothing the designer did is waiting. The topics of what changed, told as by `edit`."""
        clean = not self.dirty()
        before = self.snapshot()
        try:
            change(self.project)
        except Exception:
            self.project = model.Project.from_json(before, check=False)
            raise
        after = self.snapshot()
        topics = topics_of(before, after) if before != after else set()
        if topics:
            if clean:
                self.saved_state = self.state_key()
            self.changed(*topics)
        return topics

    def select(self, kind: str, oid: str, module: tuple = ("", "")) -> None:
        """What is selected: an object by kind and id, and within a sub-field one of its modules."""
        self.selection, self.selected_module = (kind, oid), tuple(module)
        self.changed("selection")

    # what the layouts and the energy need and give

    def subfield(self, sfid: str) -> model.SubField | None:
        return next((s for s in self.project.subfields if s.id == sfid), None)

    def good_results(self) -> dict:
        """The layouts that succeeded."""
        return {k: v for k, v in self.results.items() if not isinstance(v, Exception)}

    def known_layouts(self) -> dict:
        """The layouts in hand with their keys, for jobs.layout_of: a sub-field whose inputs did not change
        keeps its layout."""
        return {k: (self.layout_keys[k], r) for k, r in self.results.items() if k in self.layout_keys}

    def layout_done(self, generation: int, results: dict, keys: dict) -> bool:
        """A layout came back: taken if it is the one awaited (a newer change is not on its way), and the
        sub-fields whose layout is another (new, or gone) are told as "layout:<id>"; the ones kept are not."""
        if generation != self.generation:
            return False
        changed = ({sid for sid, r in results.items() if self.results.get(sid) is not r}
                   | {sid for sid in self.results if sid not in results})
        self.results, self.layout_keys = results, keys
        if changed:
            self.changed(*(f"layout:{sid}" for sid in sorted(changed)), "checks")
        return True

    def energy_key(self, layout_keys: dict | None = None) -> str:
        """Everything the energy year is computed from, as one string: the layouts in hand (by their keys; or the
        keys given), the energy, consumption and economics settings, the modules, the site. Equal keys, the same
        year: a change that leaves it alone (a name, a rule) does not compute the year again (study 18, A 9.2).
        The inverter and the input of each sub-field are in it (they are not in the layout's key:
        model.ELECTRICAL)."""
        p = self.project
        keys = self.layout_keys if layout_keys is None else layout_keys
        wired = {sf.id: [sf.params.get(k) for k in model.ELECTRICAL] for sf in p.subfields}
        return json.dumps({"layouts": sorted(keys.items()), "energy": p.energy,
                           "consumption": p.consumption, "economics": p.economics, "modules": p.modules,
                           "site": dataclasses.asdict(p.site), "wired": wired}, sort_keys=True, default=str)

    def energy_asked(self) -> int:
        """A new energy year is asked for: its generation; the inputs it is computed from are remembered."""
        self.energy_generation += 1
        self.energy_key_asked = self.energy_key()
        return self.energy_generation

    def energy_done(self, generation: int, out: dict) -> bool:
        if generation != self.energy_generation:
            return False
        self.energy = out
        self.energy_key_computed = self.energy_key_asked
        self.changed("energy", "checks")
        return True

    def energy_stale(self) -> bool:
        """Whether the year in hand was computed from other inputs than today's."""
        return bool(self.energy) and self.energy_key() != self.energy_key_computed

    def energy_outdated(self) -> bool:
        """Whether the year in hand no longer answers for the project as it is now, counting the layouts on their
        way: each filled sub-field with the key its next layout will have (model.layout_key, as jobs.layout_of
        gives it), not the key of the layout in hand. The window greys the year's values meanwhile (study 16,
        F1): from the change itself, not from when the layout comes back; an undo back to the state computed gives
        the same key, and the values are clean again at once."""
        if not self.energy:
            return False
        keys = {sf.id: self.project.layout_key(sf) for sf in self.project.subfields if sf.filled}
        return self.energy_key(keys) != self.energy_key_computed

    def layout_state(self, sf: model.SubField) -> str:
        return self.project.layout_state(sf, self.layout_keys, self.results)

    def variant_figures(self, snapshot: dict, vid: str, cache: Path) -> dict:
        """Lay out and compute one variant of the project as the window does the one in hand (nothing of the
        session is touched: callable from a worker): its figures for the comparison."""
        from . import compare, jobs
        from .energy import pipeline
        p = model.Project.from_json(copy.deepcopy(snapshot), check=False)
        p.switch_variant(vid)
        results, _keys, _laid = jobs.layout_of(p)
        good = {k: v for k, v in results.items() if not isinstance(v, Exception)}
        return compare.summary(pipeline.compute_or_say(p, good, cache, False).as_dict())

    # files

    def state_key(self) -> str:
        """The project as it would be saved, less the time of the save: equal keys, nothing to save. An image
        under the drawing counts by its size and its ends: written whole it cost 38 ms at each step with an
        image of 8 MB, and an image only changes by being imported again."""
        data = self.project.to_json() | {"modified": None}
        data["underlays"] = [{**u, "image": [len(u["image"]), u["image"][:64], u["image"][-64:]]}
                             for u in data.get("underlays", [])]
        return json.dumps(data, sort_keys=True)

    def dirty(self) -> bool:
        return self.state_key() != self.saved_state

    def mark_saved(self) -> None:
        self.saved_state = self.state_key()
        self.undo.set_clean()

    def take(self, project: model.Project, path: Path | None, saved: bool) -> None:
        """Another project in the place of this one (a file opened, a new one, an import, a recovery): the
        layouts, the year, the selection and the undo of the old one go; `saved`: nothing to save yet."""
        self.project, self.path = project, path
        self.results, self.layout_keys, self.energy = {}, {}, {}
        self.energy_key_asked = self.energy_key_computed = ""
        self.selection, self.selected_module = ("site", ""), ("", "")
        self.undo.clear()
        self.saved_state = self.state_key() if saved else None
        self.changed("file", "project")

    def new(self) -> None:
        self.take(model.Project(), None, saved=True)

    def open(self, path: Path) -> str | None:
        """The project of `path` in hand; the notice of the load, if any. A damaged file raises ValueError with
        the path of the key, an unreadable one OSError, and the project in hand stays."""
        project, notice = model.Project.load(path)
        self.take(project, Path(path), saved=True)
        return notice

    def save(self, path: Path | None = None) -> Path:
        """The project written to `path` (or its own); OSError when it could not be."""
        target = Path(path) if path is not None else self.path
        if target is None:
            raise ValueError("the project has no file yet")
        self.project.save(target)
        self.path = target
        self.mark_saved()
        return target

    def save_revision(self) -> Path:
        """A new file next to this one, with the suffix _R01, _R02...: the previous one stays as it was."""
        if self.path is None:
            raise ValueError("the project has no file yet")
        return self.save(recovery.next_revision(self.path))

    # autosave and recovery

    def autosave(self, state_dir: Path) -> Path | None:
        """A copy of the unsaved changes in the state folder (recovery.py), if there are any: where it went;
        OSError when it could not be written."""
        if not self.dirty():
            return None
        written = recovery.write(state_dir, self.path, self.project.to_json())
        if self.autosaved is not None and self.autosaved != written:
            self.autosaved.unlink(missing_ok=True)      # the project got a file: the copy of the new one goes
        self.autosaved = written
        return written

    def drop_autosave(self, state_dir: Path) -> None:
        for f in {self.autosaved, recovery.slot(state_dir, self.path)}:
            if f is not None:
                f.unlink(missing_ok=True)
        self.autosaved = None
