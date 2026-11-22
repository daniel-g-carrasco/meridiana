"""The session: the live truth of the work in hand, without Qt. The project and its file, the layouts of
the sub-fields with the keys they were made from, the energy year, the selection, the undo by snapshots,
what counts as "modified", the recovery copies. The window shows the session and reports the gestures to
it; a change of the project goes through `edit`, which takes the snapshot before and after and tells the
listeners what changed (study 18, A 9.1 and 9.3, step 2).

The undo keeps the project as JSON before and after each step: cheap and exact for projects of this size
(1,5 ms a snapshot on 20 buildings, A 4.2), and every edit is undoable without writing an undo for each.
A change that raises leaves the project as it was (A 4.3, defect 1)."""

from __future__ import annotations

import contextlib
import copy
import json
import os
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from meridiana.core.model import model
from meridiana.app.project import recovery
from meridiana.app import year_key
from meridiana.i18n import _

UNDO_LIMIT = 200                # steps kept: at 0,2 MB a step on a large project, 40 MB at most
MERGE_SECONDS = 2.0             # the arrows of a field clicked again and again are one step

# The topics a change is told by (the window draws by topic, never "everything"; study 18, A 9.1):
#   project:text        the names (of the project, a building, a sub-field, an imported model), the project reserved or not
#   project:privacy     the project reserved or not, or its per-project network consents
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
#   project:defaults    the layout the next sub-fields start from (R523): no sub-field already drawn moves
#   restored            with the topics above: an undo or a redo put the project back
#   file                another project took the place of this one
#   layout:<id>         the layout of that sub-field came back (new, or gone)
#   energy              the energy year came back
#   selection           what is selected
#   checks              the inputs of the checks changed (with the topics that changed them)
GEOMETRY = ("footprint", "height", "roof", "parapet",
            "base", "on", "part_of")       # format 28: where a body stands, whose it is (study 37)
NO_LAYOUT = {"project:text", "project:privacy", "project:underlays", "project:rules", "project:report",
             "project:defaults"}
CHECK_INPUTS = {"project:text", "project:fire", "project:rules", "project:energy", "project:subfields",
                "project:geometry", "project:site", "project:variants"}


def design_of(data: dict) -> dict:
    """The design of the variant in hand, in a snapshot of the project (to_json, format 7 and 8)."""
    return next((v.get("design") or {} for v in data.get("variants") or [] if v.get("id") == data.get("variant")), {})


def topics_of(before: dict, after: dict) -> set[str]:
    """The topics of what differs between two snapshots of the project (to_json)."""
    topics: set[str] = set()
    if before.get("regulatory_profile") != after.get("regulatory_profile"):
        topics.update({"project:rules", "project:site", "project:fire", "project:energy", "checks"})
    if (before.get("name") != after.get("name") or before.get("reserved") != after.get("reserved")
            or (before.get("model_names") or {}) != (after.get("model_names") or {})):      # format 33, R604
        topics.add("project:text")
    if before.get("reserved") != after.get("reserved") or before.get("network_consent") != after.get("network_consent"):
        topics.add("project:privacy")
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
    if (before.get("layout_defaults") or {}) != (after.get("layout_defaults") or {}):
        topics.add("project:defaults")
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
    if (before.get("props") or []) != (after.get("props") or []):      # R269: the 3D objects
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


def photo_of(project: model.Project) -> dict:
    """The project as data that nobody else holds (a deep copy of to_json): the undo's snapshot, a job's photo."""
    return copy.deepcopy(project.to_json())


def project_from(photo: dict) -> model.Project:
    """The project of a photo (session.photo()), made by the job where it runs, never on the window's thread (R598,
    study 48 chapter 6, step 0). The photo is left as it was: Project.from_json works on a deep copy of what it is
    given, so the undo, which keeps the same dict, never sees what the job does with its project."""
    return model.Project.from_json(photo, check=False)


# What Project.save writes into the project itself (its time, the resources embedded, the report's paths), outside
# any edit: the photo takes them anew after a save, or it would no longer be the project in hand.
SAVED_FIELDS = ("modified", "resources", "report")


def saved_parts(project: model.Project) -> dict:
    """SAVED_FIELDS of a project just saved, as the photo holds them: copies nobody else holds (made where the save
    ran, a thread for a save in the background)."""
    return {name: copy.deepcopy(getattr(project, name)) for name in SAVED_FIELDS}


# For the tests only (tests/_setup.py sets MERIDIANA_CHECK_PHOTO=1): every photo() compared with the project in hand,
# which is what it must be. A job given a photo that is not the project would compute something else; the mismatch
# raises at once, and it is kept here so that the run fails at its end even when Qt swallowed the exception of a slot.
CHECK_PHOTO = os.environ.get("MERIDIANA_CHECK_PHOTO") == "1"
PHOTO_MISMATCHES: list[str] = []


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

    def join_last(self) -> bool:
        """The last step joins the one before it, as one thing for Undo (a cut and its paste, R432). Not across a save:
        what was saved stays a place to come back to. Whether it joined."""
        if self.index < 2 or self.index != len(self.steps) or self.clean_index == self.index - 1:
            return False
        last = self.steps.pop()
        top = self.steps[-1]
        top.text, top.after, top.when = last.text, last.after, last.when
        self.index -= 1
        if self.clean_index > self.index:
            self.clean_index = -1
        self._tell()
        return True

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
        self.realigned: list = []       # what the last layout took out of the strings (R442)
        self.energy_generation = 0      # of the energy years asked for
        self.energy_key_asked = ""      # the inputs of the energy year asked for last, and of the one in hand
        self.energy_key_computed = ""
        self._year_parts_computed: dict = {}
        self._weather_computed = ""
        self.selection = ("site", "")
        self.selected_module = ("", "")
        self.many = []                  # R439: ids of one kind selected together; the selection is one of them
        self.undo = Undo(self._restore, undo_limit)
        self._photo: dict | None = None             # photo(): the last snapshot, and the project it is of
        self._photo_of = None
        self._key_of_photo: tuple | None = None     # state_key(): (the photo it was made on, the key)
        self._changing = 0                          # inside the change of an edit or an amend: the photo is behind
        self.saved_state: str | None = self.state_key()
        self.autosaved: Path | None = None
        self.listeners: list[Callable[[set], None]] = []
        self._held: set | None = None
        # R547 «Risposta subito» (Daniel, 08/11/2026): a change that moves modules is shown at once by the listeners
        # subscribed `at_once` (the plan, the 3D), the others told after the window has drawn it. `later(call)` is
        # given by the window (call after its next frame); without it every listener is told at once, as before.
        self.later: Callable[[Callable[[], None]], None] | None = None
        self._at_once: list = []
        self._waiting: set | None = None
        # R598 (study 48, chapter 6, step 1): the round of the views after a layout a view at a time on the window's
        # turns: `pieces(name, call)` is given by the window (the jobs' Center.piece); without it every listener is
        # told at once, as before. A change made meanwhile tells the views still waiting first (_tell_now), so that
        # every view hears every change, in order. The views told after the frame of a gesture (R547) are told at
        # once, as before: they answer the designer's hand.
        self.pieces: Callable[..., None] | None = None
        self._telling: list = []                    # (listener, topics) still to tell, a piece each
        self._posted_for = None                     # the listener whose piece waits in the window's turns
        self.spreading = False                      # a listener told in its piece: it may leave pieces of its own
        # R598: the plan's scene of the strings made by the layout's job with the layout (app/view/plan_wiring.py):
        # `wiring_options()` is given by the plan (what the scene is made with besides the project), `wiring_offer`
        # is what the job made with them, for the plan to take when its inputs are still those
        self.wiring_options: Callable[[], dict | None] | None = None
        self.wiring_offer: dict | None = None

    # events

    def subscribe(self, listener: Callable[[set], None], at_once: bool = False) -> None:
        self.listeners.append(listener)
        if at_once:
            self._at_once.append(listener)

    def changed(self, *topics: str) -> None:
        if self._held is not None:
            self._held.update(topics)
            return
        self._tell_now()
        told = set(topics)
        for listener in self._hearing(told):
            listener(told)

    def _hearing(self, told: set) -> list:
        """The listeners to tell of `told` now; R547: while a change is shown first, the others hear it after the
        frame, all topics together."""
        if self._waiting is not None:
            self._waiting.update(told)
            return [x for x in self.listeners if x in self._at_once]
        return list(self.listeners)

    def _changed_in_pieces(self, topics: set) -> None:
        """`changed`, the listeners told a piece each on the window's turns (self.pieces): those that draw the
        modules first (subscribed `at_once`), then the others in their order."""
        if self.pieces is None:
            self.changed(*topics)
            return
        told = set(topics)
        listeners = self._hearing(told)
        first = [x for x in listeners if x in self._at_once]
        self._tell_in_pieces(first + [x for x in listeners if x not in self._at_once], told)

    def _tell_in_pieces(self, listeners: list, told: set) -> None:
        """After the pieces still waiting, if any (each listener hears its changes in their order)."""
        if not listeners:
            return
        self._telling.extend((listener, set(told)) for listener in listeners)
        self._post_next()

    def _join_pieces(self, told: set) -> None:
        """`told` to every listener after what it still waits for: joined to its last piece waiting (it hears both
        at once, on the project as it is now), or in a piece of its own after the others."""
        last = {}
        for listener, topics in self._telling:
            if topics is not None:              # not a call left for after the views (after_told)
                last[id(listener)] = topics
        for listener in list(self.listeners):
            if id(listener) in last:
                last[id(listener)].update(told)
            else:
                self._telling.append((listener, set(told)))
        self._post_next()

    def _post_next(self) -> None:
        if not self._telling or self.pieces is None:
            return
        head = self._telling[0][0]
        if self._posted_for is head:            # its piece is already waiting
            return
        self._posted_for = head
        what = "told" if self._telling[0][1] is None else "tell"
        self.pieces(f"{what}:{getattr(head, '__qualname__', type(head).__name__)}", self._tell_one, head)

    def _tell_one(self, listener) -> None:
        """A piece: `listener`, the first waiting, told (the Center times it with the listener's name). A piece left
        behind by a change that told the waiting ones at once tells nobody, and asks for the next one's."""
        if self._posted_for is listener:
            self._posted_for = None
        if not self._telling or self._telling[0][0] is not listener:
            self._post_next()
            return
        _listener, told = self._telling.pop(0)
        if told is None:                        # a call left for after the views (after_told)
            try:
                listener()
            finally:
                self._post_next()
            return
        if listener not in self.listeners:      # unsubscribed meanwhile (a view closed): nobody to tell
            self._post_next()
            return
        self.spreading = True
        try:
            listener(told)
        finally:
            self.spreading = False
            self._post_next()

    def _tell_now(self) -> None:
        """The listeners still waiting for their piece told now, in order: a change that comes finds every view told
        of the ones before."""
        while self._telling:
            listener, told = self._telling.pop(0)
            if told is None:
                listener()
            elif listener in self.listeners:
                listener(told)

    def telling(self) -> bool:
        """Whether some views are still to be told of a change (a piece each, on the window's turns)."""
        return bool(self._telling)

    def after_told(self, call: Callable[[], None]) -> None:
        """`call` once every view has heard what it still waits for, in a piece of its own after theirs: what the
        window does with a change once the views show it (a model added: its phase, its tool and the plan framed on it,
        R598 passo 2); at once when no view waits. A change that comes meanwhile tells the views first, then calls it."""
        if not self._telling or self.pieces is None:
            call()
            return
        self._telling.append((call, None))
        self._post_next()

    def _answer_first(self, keys_before: dict | None) -> None:
        """R547: the change just made moves modules (a layout to wait for): the listeners subscribed `at_once` show it
        now, the others (properties, checks, plant, the year's bridge that asks for the layout...) once the window
        has drawn it, in one round with whatever else came meanwhile."""
        if self.later is None or self._waiting is not None or keys_before is None:
            return
        if keys_before == self.expected_layout_keys():        # no module moves (a name, a default, a rule): all at once
            return
        self._waiting = set()
        self.later(self._tell_waiting)

    def _keys_for_answer(self) -> dict | None:
        """R547: the layout keys before a change, to tell whether it moves modules (only with a window that answers first)."""
        return self.expected_layout_keys() if self.later is not None else None

    def _tell_waiting(self) -> None:
        """R547's round after the frame: the listeners not subscribed `at_once`, with every topic that came meanwhile.
        R598: with the window's pieces, a listener per piece on its turns, after the pieces still waiting (a layout's
        views); without them all now, as before."""
        topics, self._waiting = self._waiting, None
        if not topics:
            return
        others = [x for x in self.listeners if x not in self._at_once]
        if self.pieces is not None:
            self._tell_in_pieces(others, topics)
            return
        self._tell_now()                    # a layout's views still waiting for their piece hear it first
        for listener in others:
            listener(set(topics))

    def _told_before(self) -> None:
        """Before the project or the selection changes again: every view told now of the changes before, on the
        project they were made on (the round after the frame and the pieces still waiting), so that each hears every
        change in its order."""
        if self._waiting is not None:
            self._tell_waiting()
        self._tell_now()

    @contextlib.contextmanager
    def held(self, pieces: bool = False):
        """The changes made inside told once at the end, with all their topics together: one round of the listeners
        where there would be one for each (study 41: the layout that comes back and the strings it realigns, two
        rounds of every view for one gesture). `pieces`: that round a view at a time on the window's turns (R598)."""
        if self._held is not None:
            yield
            return
        self._held = set()
        try:
            yield
        finally:
            topics, self._held = self._held, None
            if topics:
                if pieces:
                    self._changed_in_pieces(topics)
                else:
                    self.changed(*topics)

    # the project as data

    def snapshot(self) -> dict:
        return photo_of(self.project)

    def photo(self) -> dict:
        """The project as data now, for a heavy job (R598, study 48 rule 1): the very snapshot `edit`, `amend` and
        the undo made last, kept as a reference, so that a job costs the window no copy; made once when there is none
        (a project just opened). Whoever receives it never changes it (the undo keeps the same dict)."""
        if self._photo is None or self._photo_of is not self.project:
            self._photo, self._photo_of = self.snapshot(), self.project
        elif CHECK_PHOTO:
            self._check_photo()
        return self._photo

    def _photo_in_hand(self) -> dict | None:
        """The photo when it is the project in hand, made by nobody here: the snapshot "before" of a change and the
        project an undo starts from are that very data (R598, passo 2: a to_json and a deepcopy less at each change,
        about 15 ms on model A). None when there is none yet or the project is being changed."""
        if self._photo is None or self._photo_of is not self.project or self._changing:
            return None
        if CHECK_PHOTO:
            self._check_photo()
        return self._photo

    def _check_photo(self) -> None:
        """CHECK_PHOTO: the photo is the project in hand, or the change that left it behind is named by its keys."""
        now = photo_of(self.project)
        if now == self._photo:
            return
        keys = sorted(k for k in set(now) | set(self._photo) if now.get(k) != self._photo.get(k))
        where = "".join(traceback.format_stack(limit=8)[:-2])
        message = (f"session.photo() is not the project in hand (keys {', '.join(keys)}): the project was changed "
                   f"without session.edit() or amend(), and a job would compute on the old one.\n{where}")
        PHOTO_MISMATCHES.append(message)
        raise AssertionError(message)

    def keep_photo(self, data: dict) -> None:
        """photo_of(self.project), made where the project was read (the program started with a file, as `open` and
        `take` are given it), so that the first heavy job does not make it on the window's thread: 16-39 ms on model
        A when the sun map was turned on (measured on screen, 14/11/2026)."""
        self._keep_photo(data)

    def _keep_photo(self, data: dict) -> None:
        self._photo, self._photo_of = data, self.project

    def _restore(self, data: dict) -> None:
        self._tell_now()                    # the views still waiting for their piece hear the change before first
        now = self._photo_in_hand()
        if now is None:
            now = self.project.to_json()
        self._invalidate_regulatory_jobs(now, data)
        topics = topics_of(now, data)
        keys_before = self._keys_for_answer()
        self.project = model.Project.from_json(copy.deepcopy(data), check=False)
        self._keep_photo(data)
        self._answer_first(keys_before)
        self.changed("restored", *topics)

    def _invalidate_regulatory_jobs(self, before: dict, after: dict) -> None:
        """Reject earlier results even before deferred window listeners ask for new jobs."""
        if (before.get("regulatory_profile") != after.get("regulatory_profile")
                or (before.get("site") or {}).get("timezone") != (after.get("site") or {}).get("timezone")):
            self.generation += 1
            self.energy_generation += 1

    def edit(self, text: str, change: Callable[[model.Project], object], merge=None, spread: bool = False) -> set[str]:
        """Apply `change(project)` as one undoable step; with `merge`, a step that follows the same kind of
        change within a moment joins the last one. If `change` raises, the project is put back as it was
        before and the error goes on to the caller. The topics of what changed (empty: nothing did, and
        nobody is told). `spread`: the views told a piece each on the window's turns (self.pieces), those that draw
        first (subscribed `at_once`) first, also when no module moves: a heavy change such as a model imported, whose
        views cost hundreds of milliseconds each (R598, passo 2); without pieces, as any change."""
        self._told_before()                 # R547: a new edit finds every view told of the one before
        before = self._photo_in_hand()
        if before is None:
            before = self.snapshot()
        spreading = spread and self.pieces is not None and self._held is None
        keys_before = None if spreading else self._keys_for_answer()
        self._changing += 1
        try:
            change(self.project)
        except Exception:
            self.project = model.Project.from_json(before, check=False)
            self._keep_photo(before)
            raise
        finally:
            self._changing -= 1
        after = self.snapshot()
        self._keep_photo(after)
        self._invalidate_regulatory_jobs(before, after)
        topics = topics_of(before, after) if before != after else set()
        if topics:
            self.undo.push(Step(text, before, after, merge))
            if spreading:
                self._changed_in_pieces(topics)
            else:
                self._answer_first(keys_before)
                self.changed(*topics)
        return topics

    def amend(self, change: Callable[[model.Project], object]) -> set[str]:
        """Apply `change(project)` without an undo step: what the program writes down by itself and Ctrl+Z must not
        take back (the proposal of a project of before format 14 made the designer's strings at the first layout:
        undone, it would be written down again at once). If the project was saved as it was, it still counts as
        saved: nothing the designer did is waiting. The topics of what changed, told as by `edit`."""
        clean = not self.dirty()
        before = self._photo_in_hand()
        if before is None:
            before = self.snapshot()
        self._changing += 1
        try:
            change(self.project)
        except Exception:
            self.project = model.Project.from_json(before, check=False)
            self._keep_photo(before)
            raise
        finally:
            self._changing -= 1
        after = self.snapshot()
        self._keep_photo(after)
        self._invalidate_regulatory_jobs(before, after)
        topics = topics_of(before, after) if before != after else set()
        # still saved whatever changed, even a part no view follows by topic (the site's weather, R196: opening a
        # saved project and closing it asked to save, 30/10/2026)
        if clean and before != after:
            self.saved_state = self.state_key()
        if topics:
            self.changed(*topics)
        return topics

    def select(self, kind: str, oid: str, module: tuple = ("", ""), spread: bool = False) -> None:
        """What is selected: an object by kind and id, and within a sub-field one of its modules. `spread`: a selection
        that goes with a change told in pieces (edit(spread=True): the body a model imported brings, R598, passo 2):
        each view hears it with its piece of that change, or in a piece after it, never all at once; with nothing
        waiting, as any selection."""
        if spread and self._telling and self.pieces is not None and self._held is None and self._waiting is None:
            self.selection, self.selected_module = (kind, oid), tuple(module)
            self.many = []
            self._join_pieces({"selection"})
            return
        self._tell_now()                    # the views still waiting for their piece hear the change before first
        self.selection, self.selected_module = (kind, oid), tuple(module)
        self.many = []
        self.changed("selection")

    def select_many(self, kind: str, oids: list) -> None:
        """More objects of one kind together (R439): the last is the selection, the one the others follow."""
        oids = list(dict.fromkeys(oids))
        if len(oids) < 2:
            self.select(kind, oids[0] if oids else "")
            return
        self._tell_now()
        self.selection, self.selected_module = (kind, oids[-1]), ("", "")
        self.many = oids
        self.changed("selection")

    def selected_many(self) -> list:
        """The ids selected together that still exist, in order; none when fewer than two are left."""
        field = {"building": "buildings", "subfield": "subfields", "exclusion": "exclusions", "prop": "props"}.get(
            self.selection[0])
        if not self.many or field is None:
            return []
        there = {x.id for x in getattr(self.project, field)}
        left = [oid for oid in self.many if oid in there]
        return left if len(left) > 1 else []

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

    def layout_done(self, generation: int, results: dict, keys: dict, realigned=False, photo: dict | None = None,
                    pieces: bool = False) -> bool:
        """A layout came back: taken if it is the one awaited (a newer change is not on its way), and the
        sub-fields whose layout is another (new, or gone) are told as "layout:<id>"; the ones kept are not.
        `realigned` and `photo`: the strings the layout's job realigned on `photo`, the photo it was given
        (layout_job.realigned: None when no string lost a module), taken when that photo is still the project in
        hand; False: realigned here. `pieces`: the views told a piece each on the window's turns (R598)."""
        if generation != self.generation:
            return False
        changed = ({sid for sid, r in results.items() if self.results.get(sid) is not r}
                   | {sid for sid in self.results if sid not in results})
        self.results, self.layout_keys = results, keys
        with self.held(pieces):     # the layout and the strings realigned on it: the views told once
            if changed:
                self.changed(*(f"layout:{sid}" for sid in sorted(changed)), "checks")
            # after a change, the strings follow the modules laid (R442); a project just opened is left as saved (its
            # year answers for it), the checks say what is lost
            if not (self.undo.can_undo() or self.undo.can_redo()):
                self.realigned = []
            elif realigned is not False and photo is not None and self._photo is photo and self._photo_of is self.project:
                self.realigned = self._realigned_by_the_job(realigned)
            else:
                self.realigned = self.realign_strings()
        return True

    def _realigned_by_the_job(self, made: dict | None) -> list[tuple[str, int, list]]:
        """realign_strings with what the layout's job made on the photo in hand (layout_job.realigned): the strings
        set, the job's photo after kept as the photo, the topics told and what is saved followed, as `amend` does,
        without a snapshot here."""
        if made is None:
            return []
        before, after = self._photo, made["photo"]
        clean = self.saved_state == made["saved"][0]        # not dirty(): the job made the key of the photo in hand
        self.project.energy.__setitem__("strings", made["strings"])
        self._keep_photo(after)
        self._invalidate_regulatory_jobs(before, after)
        if clean:
            self.saved_state = made["saved"][1]
        if made["topics"]:
            self.changed(*made["topics"])
        names = {sf.id: sf.name or sf.id for sf in self.project.subfields}
        return [(label, n, [names.get(sid, sid) for sid in sids]) for label, n, sids in made["gone"]]

    def realign_strings(self) -> list[tuple[str, int, list]]:
        """The modules no longer laid taken out of the strings (R442), as the program's own note (`amend`): for each
        string that lost some, its label, how many and the names of their sub-fields. Sub-fields whose layout is
        not in hand keep their keys."""
        from meridiana.core.energy import plant
        runs = ((self.project.energy or {}).get("strings") or {}).get("runs") or []
        if not runs:
            return []
        after, gone = plant.realign(runs, *plant.laid_of(self.project.subfields, self.results))
        if not gone:
            return []
        self.amend(lambda p: p.energy.__setitem__("strings", plant.touched(p.energy.get("strings"), after)))
        from meridiana.core.model import imported
        shown = imported.namer(self.project)
        names = {sf.id: shown.subfield(sf) or sf.id for sf in self.project.subfields}
        return [(label, n, [names.get(sid, sid) for sid in sids]) for label, n, sids in gone]

    @staticmethod
    def realigned_text(gone: list[tuple[str, int, list]]) -> str:
        """What `realign_strings` did, in one line for the status bar (R442)."""
        from meridiana.i18n import ngettext
        total = sum(n for _label, n, _where in gone)
        where = ", ".join(f"{label} ({n}, {' + '.join(sfs)})" for label, n, sfs in gone)
        return ngettext("{n} module no longer laid taken out of the strings: {where}",
                        "{n} modules no longer laid taken out of the strings: {where}", total).format(n=total, where=where)

    def energy_key(self, layout_keys: dict | None = None) -> str:
        """Everything the energy year is computed from, as one string (app/year_key.py): on the layouts in hand (by
        their keys), or on the keys given."""
        return year_key.key(self.project, self.layout_keys if layout_keys is None else layout_keys)

    def expected_key(self) -> str:
        """The year's key for the project as it is now, the layouts on their way included (expected_layout_keys)."""
        return year_key.expected(self.project)

    def layouts_answer(self) -> bool:
        """Whether the layouts in hand are those of the project as it is (no layout to wait for): a change that moves
        no module, such as the strings realigned on the layout just come (R442)."""
        return bool(self.layout_keys) and self.layout_keys == self.expected_layout_keys()

    def expected_layout_keys(self) -> dict:
        """The key each filled sub-field will have: from the change itself, not from when its layout comes back."""
        return year_key.layout_keys(self.project)

    def weather_mark(self) -> str:
        """When the typical year inside the project was fetched: the same weather whether it is only in the cache or, after
        a save, in the file too; empty when the project holds none."""
        climate = self.project.climate or (getattr(self.project, "resources", {}) or {}).get("weather") or {}
        tmy = climate.get("tmy") if isinstance(climate, dict) else None
        return str(tmy.get("fetched", "")) if isinstance(tmy, dict) else ""

    def year_fingerprint(self) -> str:
        """The inputs of the year as they are now, in one short mark (R437): modules, strings, inverters, site, losses,
        what shades. The same as a year's: that year answers for this project. The weather is a site's, and it counts
        apart (year_outdated), since it enters the file only when it is saved."""
        return year_key.fingerprint(self.expected_key())

    def year_outdated(self) -> bool:
        """Whether the year in hand no longer answers for the project: its inputs, or a weather fetched since."""
        if self.energy_outdated():
            return True
        now, was = self.weather_mark(), self._weather_computed
        return bool(self.energy and now and was and now != was)

    def _year_parts(self, layout_keys: dict | None = None) -> dict:
        """The inputs of the year, each with a mark, to say what changed (the layouts: as the project will lay them
        out, or `layout_keys`)."""
        return year_key.parts(self.project, self.expected_layout_keys() if layout_keys is None else layout_keys)

    def year_changes(self) -> list[str]:
        """What changed since the year in hand was computed, in words; empty when it answers for the project."""
        if not self.energy or not self.year_outdated():
            return []
        words = {"layouts": _("the layout of the modules"), "modules": _("the modules"), "site": _("the site"),
                 "wired": _("the inverters"), "shade": _("the buildings and the obstacles"), "props": _("the buildings and the obstacles"),
                 "consumption": _("the consumption"), "economics": _("the economics"), "energy.strings": _("the strings"),
                 "energy.losses": _("the losses"), "energy.inverters": _("the inverters")}
        now, was = self._year_parts(), self._year_parts_computed
        changed = [name for name in sorted(set(now) | set(was)) if now.get(name) != was.get(name)]
        said: list[str] = [_("the weather")] if self.weather_mark() and self._weather_computed and self.weather_mark() != self._weather_computed else []
        for name in changed:
            word = words.get(name) or (_("the inverters") if "inverter" in name else _("the settings of the plant"))
            if word not in said:
                said.append(word)
        return said

    def take_year(self, results: dict, layout_keys: dict, energy: dict, pieces: bool = False) -> None:
        """A year kept from an earlier computation of these very inputs (year_store): in hand as if just computed.
        `pieces`: the views told a piece each on the window's turns, of the layouts and then of the year (R598)."""
        self.layout_done(self.generation, results, layout_keys, pieces=pieces)
        self.energy_asked()
        self.energy_done(self.energy_generation, energy, pieces=pieces)

    def energy_asked(self, layout_keys: dict | None = None) -> int:
        """A new energy year is asked for: its generation; the inputs it is computed from are remembered, with the
        keys of the layouts it is computed on: those in hand, or `layout_keys` for a job that lays out by itself
        (the Quick's, with `expected_layout_keys()`: at opening there is no layout in hand yet, and the year came back
        «not up to date» with nothing changed, r17-unita). What each input was is kept too, to say later what
        changed (R437)."""
        self.energy_generation += 1
        keys = self.layout_keys if layout_keys is None else layout_keys
        self.energy_key_asked = self.energy_key(keys)
        self._energy_layout_keys_asked = dict(keys)
        self._year_parts_asked = self._year_parts(keys)
        return self.energy_generation

    def energy_done(self, generation: int, out: dict, pieces: bool = False) -> bool:
        """The year asked for came: taken if it is the one awaited and of the inputs it was asked on, and told as
        "energy". `pieces`: the views told a piece each on the window's turns (R598), after those still waiting."""
        if generation != self.energy_generation or (self.energy_key_asked and self.energy_key_asked != self.energy_key(
                getattr(self, "_energy_layout_keys_asked", self.layout_keys))):
            return False
        self.energy = out
        self.energy_key_computed = self.energy_key_asked
        self._year_parts_computed = getattr(self, "_year_parts_asked", None) or self._year_parts()
        self._weather_computed = self.weather_mark()
        with self.held(pieces):
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
        return self.expected_key() != self.energy_key_computed

    def layout_state(self, sf: model.SubField) -> str:
        return self.project.layout_state(sf, self.layout_keys, self.results)

    def variant_figures(self, snapshot: dict, vid: str, cache: Path) -> dict:
        """Lay out and compute one variant of the project as the window does the one in hand (nothing of the
        session is touched: callable from a worker): its figures for the comparison."""
        from . import compare, jobs
        from . import pipeline
        p = model.Project.from_json(copy.deepcopy(snapshot), check=False)
        p.switch_variant(vid)
        results, _keys, _laid = jobs.layout_of(p)
        good = {k: v for k, v in results.items() if not isinstance(v, Exception)}
        return compare.summary(pipeline.compute_or_say(p, good, cache, False).as_dict())

    # files

    def state_key(self) -> str:
        """The project as it would be saved, less the time of the save: equal keys, nothing to save. An image
        under the drawing counts by its size and its ends: written whole it cost 38 ms at each step with an
        image of 8 MB, and an image only changes by being imported again. Kept for the photo it was made with (R598,
        passo 2): the photo is the project in hand, the same dict gives the same key, and every change of the project
        makes a new photo; the title, the plant and the exports asked it 7 to 10 times for one Canc."""
        photo = self._photo if self._photo is not None and self._photo_of is self.project and not self._changing else None
        kept = self._key_of_photo
        if photo is not None and kept is not None and kept[0] is photo:
            if CHECK_PHOTO:
                self._check_key(kept[1])
            return kept[1]
        key = self.key_of(self.project)
        self._key_of_photo = (photo, key) if photo is not None else None
        return key

    def _check_key(self, key: str) -> None:
        """CHECK_PHOTO: the key kept for the photo is the key of the project in hand, as _check_photo."""
        if self.key_of(self.project) == key:
            return
        where = "".join(traceback.format_stack(limit=8)[:-2])
        message = ("session.state_key() kept for the photo is not the key of the project in hand: the project was "
                   f"changed without session.edit() or amend().\n{where}")
        PHOTO_MISMATCHES.append(message)
        raise AssertionError(message)

    @staticmethod
    def key_of(project: model.Project) -> str:
        """state_key of any project: of the copy a save in the background wrote (adopt_save)."""
        from meridiana.core.rules import registry
        data = project.to_json() | {"modified": None, "regulatory": registry.identity(project)}
        data["underlays"] = [{**u, "image": [len(u["image"]), u["image"][:64], u["image"][-64:]]}
                             for u in data.get("underlays", [])]
        data.pop("resources", None)             # rebuilt on save, never a designer's change to undo
        return json.dumps(data, sort_keys=True)

    def dirty(self) -> bool:
        return self.state_key() != self.saved_state

    def mark_saved(self) -> None:
        self.saved_state = self.state_key()
        self.undo.set_clean()

    def take(self, project: model.Project, path: Path | None, saved: bool, photo: dict | None = None) -> None:
        """Another project in the place of this one (a file opened, a new one, an import, a recovery): the
        layouts, the year, the selection and the undo of the old one go; `saved`: nothing to save yet. `photo`:
        photo_of(project), made where the project was read (a thread), so that the first heavy job does not make
        it on the window's thread (20 ms on model A)."""
        self.project, self.path = project, path
        self._photo, self._photo_of = (photo, project) if photo is not None else (None, None)
        self.results, self.layout_keys, self.energy = {}, {}, {}
        self.energy_key_asked = self.energy_key_computed = ""
        self.selection, self.selected_module = ("site", ""), ("", "")
        self.many = []
        self.undo.clear()
        self.saved_state = self.state_key() if saved else None
        self.changed("file", "project")

    def new(self) -> None:
        self.take(model.Project(), None, saved=True)

    def open(self, path: Path, cache_dir: Path | None = None) -> str | None:
        """The project of `path` in hand; the notice of the load, if any. A damaged file raises ValueError with
        the path of the key, an unreadable one OSError, and the project in hand stays."""
        project, notice = model.Project.load(path, cache_dir)
        self.take(project, Path(path), saved=True, photo=photo_of(project))
        return notice

    def save(self, path: Path | None = None, cache_dir: Path | None = None, report_profile: dict | None = None) -> Path:
        """The project written to `path` (or its own); OSError when it could not be."""
        target = Path(path) if path is not None else self.path
        if target is None:
            raise ValueError("the project has no file yet")
        self.project.save(target, cache_dir, report_profile)
        self._photo_saved(saved_parts(self.project))
        self.path = target
        self.mark_saved()
        return target

    def _photo_saved(self, parts: dict) -> None:
        """Project.save wrote `parts` (SAVED_FIELDS, as saved_parts gives them) into the project in hand: the photo
        takes them in a new dict (the old one is the undo's, never changed); without a photo, the next job makes it."""
        if self._photo is not None and self._photo_of is self.project:
            self._photo = {**self._photo, **{k: v for k, v in parts.items() if k in self._photo}}

    def adopt_save(self, project: model.Project, written: model.Project, path: Path, key: str,
                   parts: dict | None = None) -> bool:
        """A save made in the background on a copy of the project (R537) taken back: `written` is that copy after
        its save, `key` the state_key when it was taken. The file is the project's, its time and resources come in;
        untouched meanwhile, the project is as saved (its report as written, the undo clean); changed meanwhile,
        what is to save is the difference from the file (the dot of «modified» stays). Another project in hand
        meanwhile (an open, a new one): nothing changes. True when the project in hand is as saved. `parts`:
        saved_parts(written), made where the save ran, so that the photo follows what comes in without a copy here;
        without them the photo is made again at the next job."""
        if self.project is not project:
            return False
        untouched = self.state_key() == key
        project.modified, project.resources = written.modified, written.resources
        if untouched:
            project.report = written.report
        if parts is None:
            self._photo = None
        else:
            self._photo_saved({k: v for k, v in parts.items() if untouched or k != "report"})
        self.path = Path(path)
        if untouched:
            self.mark_saved()
        else:
            self.saved_state = self.key_of(written)
        return untouched

    def save_revision(self, cache_dir: Path | None = None, report_profile: dict | None = None) -> Path:
        """A new file next to this one, with the suffix _R01, _R02...: the previous one stays as it was."""
        if self.path is None:
            raise ValueError("the project has no file yet")
        return self.save(recovery.next_revision(self.path), cache_dir, report_profile)

    # autosave and recovery

    def autosave(self, state_dir: Path) -> Path | None:
        """A copy of the unsaved changes in the state folder (recovery.py), if there are any: where it went;
        OSError when it could not be written."""
        if not self.dirty():
            return None
        written = recovery.write(state_dir, self.path, self.photo())     # from_json copies it: the photo stays
        if self.autosaved is not None and self.autosaved != written:
            self.autosaved.unlink(missing_ok=True)      # the project got a file: the copy of the new one goes
        self.autosaved = written
        return written

    def drop_autosave(self, state_dir: Path) -> None:
        for f in {self.autosaved, recovery.slot(state_dir, self.path)}:
            if f is not None:
                f.unlink(missing_ok=True)
        self.autosaved = None
