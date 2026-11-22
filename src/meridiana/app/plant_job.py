"""The plant after a change as a job of the mechanism (R598, docs/studio/48-lavori-pesanti.md, chapter 6, steps 1 and
7): plant.build in a process, made from the session's photo, only the last request counting; before, a QRunnable
of the window that held the interpreter while the views took a layout (146-175 ms of a view's 20 ms waiting for it).

What travels is small, as for the checks (app/checks_job.py). The job runs in the layout's process (`Kind.home`): the
layouts it reads are those that process keeps (`ctx.kept`, by sub-field and key, app/layout_job.py), so they never
travel; one it does not keep it lays out itself when its key is that of the photo's project, and what it cannot have
so (a layout of before) it asks for (`missing`), and the window sends it with the next request. Of the year it reads
the hottest cell, the DC power of each hour and the exposure of the faces (`year_of`): sent only when the energy in
hand is another one (`year_id`), and kept by the process. The window's language goes with it, since the plant's
notes and checks are words.

The plant is made once in the process for both its readers: the plant's page (this job) and the checks (`shared`),
whichever comes first; the other takes it when its inputs are the same (photo, layouts, year, language).

`Builds` is the job's one owner on the window's thread (no Qt): `ask()` is the page's rebuild; a job on its way goes
to its end and the next one comes after it (one stopped late would keep the layout's process busy); an answer is
taken (its `pieces`, Center.piece) only when it is of the project in hand, as before: the same state key (the process makes
it), the same layouts and the same energy; otherwise it is dropped, and the change that made it old has asked for
the next one. Cancel from the bar leaves the plant of before; so does a process that fails, with its sentence in the
status bar (Center.tell)."""

from __future__ import annotations

import numpy as np

from meridiana import i18n
from meridiana.app import layout_job
from meridiana.app.platform import log
from meridiana.app.work.job import Kind
from meridiana.core.compute import resources
from meridiana.i18n import N_

SLOT = "plant"
SETTLE = 0.0                    # the page's own timer is the quiet (PlantBackend._schedule)
TRIES = 3                       # answers «missing» in a row before the job is said to have failed

KIND = Kind(name="plant", title=N_("Plant"), run="meridiana.app.plant_job:run", where="process", processes=1,
            keep_warm=layout_job.SESSION, low_priority=layout_job.KIND.low_priority, topics=(), settle=SETTLE,
            home=layout_job.KIND.name)


def year_of(energy) -> tuple:
    """What plant.build reads of the year in hand: its hottest cell, the DC power of each hour, the exposure of the
    faces (faces.year_of); three None without a year."""
    from meridiana.core.energy import faces
    sim = (energy or {}).get("sim")
    if sim is None:
        return None, None, None
    return max(a["t_cell_max"] for a in sim.arrays), sim.hourly.p_dc.to_numpy(), faces.year_of(sim)


def same(a, b) -> bool:
    """Whether two values made of numbers, arrays, dicts and tuples are equal (an array compared whole)."""
    if a is b:
        return True
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        return (isinstance(a, np.ndarray) and isinstance(b, np.ndarray) and a.shape == b.shape
                and bool(np.array_equal(a, b)))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b, strict=True))
    return type(a) is type(b) and a == b


def _stopped(ctx):
    """A callable that says whether the job was asked to stop (the search of Meridiana's strings looks at it)."""
    def asked() -> bool:
        try:
            ctx.checkpoint()
        except resources.Stopped:
            return True
        return False
    return asked


def shared(ctx, photo: dict, keys: dict, year: tuple, project, results: dict):
    """plant.build of these inputs (`keys`: the layouts that succeeded, sub-field id -> key), or the one this process
    made last when its inputs are the same: the plant's job and the checks read the same plant, made once."""
    from meridiana.core.energy import plant, stringing
    have = ctx.kept.get("plant")
    if (have is not None and have["language"] == i18n.language() and have["keys"] == keys
            and same(have["year"], year) and have["photo"] == photo):
        return have["state"]
    hot, power, exposure = year
    state = plant.build(project, results, t_cell_max_year=hot, p_dc_hourly=power, exposure=exposure,
                        search=stringing.SearchBudget(cancelled=_stopped(ctx)))
    ctx.checkpoint()                    # a search cut short by a stop is never kept
    ctx.kept["plant"] = {"photo": photo, "keys": dict(keys), "year": year, "language": i18n.language(),
                         "state": state}
    return state


def run(request: dict, ctx) -> dict:
    """In the layout's process: the plant of the photo's project on the layouts the window holds (by their keys),
    or what is missing to make it."""
    from meridiana.app.session import ProjectSession, project_from
    if request.get("language") and i18n.language() != request["language"]:
        i18n.setup(request["language"])                 # the window's: the notes are in the words it speaks now
    kept = ctx.kept.setdefault("layouts", {})          # layout_job's: (sub-field, key) -> result
    if "year" in request:
        ctx.kept["plant_year"] = (request["year_id"], request["year"])
    have = ctx.kept.get("plant_year")
    no_year = have is None or have[0] != request["year_id"]
    keys = request["keys"]
    results, missing = layout_job.from_kept(kept, keys, sent=request.get("layouts"))
    if no_year and not missing:
        return {"missing": {"layouts": [], "year": True}}
    ctx.checkpoint()
    project = project_from(request["photo"])
    if missing:
        layout_job.lay_missing(project, kept, keys, results, missing)
    if missing or no_year:
        return {"missing": {"layouts": missing, "year": no_year}}
    results = {sid: results[sid] for sid in keys}      # in the window's order
    state = shared(ctx, request["photo"], keys, have[1], project, results)
    return {"state": state, "key": ProjectSession.key_of(project)}


class Builds:
    """The plant of one session for its page. `center` is the window's jobs' Center, or a callable that gives it (made
    when first asked). An answer of the project in hand is taken by `pieces`, (name, call(state, mark)) one after the
    other on the window's turns (Center.piece: each timed under its name), as long as the owner is open; `mark` is what
    the answer was made of, for `current`. `changed()` is told whenever `busy()` may have changed."""

    def __init__(self, session, center, pieces, changed=None):
        self.session, self._center, self._centre = session, center, None
        self._pieces, self._told = tuple(pieces), changed
        self._taking = False                    # an answer's pieces still to come
        self._handle = None                     # the job in hand
        self._asked = None                      # what it was asked on: photo, layout keys, energy (by reference)
        self._again = False                     # asked while a job was on its way: one more after it
        self._energy, self._year_id, self._year_sent, self._year = None, 0, -1, (None, None, None)
        self._send: set = set()                 # the layouts the process asked for, sent with the next request
        self._tries = 0
        self._closed = False

    @property
    def center(self):
        if self._centre is None:
            self._centre = self._center() if callable(self._center) else self._center
            self._centre.subscribe(self._rows)
        return self._centre

    def busy(self) -> bool:
        """Whether a plant is on its way, about to be asked again after the one on its way, or being taken."""
        return self._again or self._taking or (self._handle is not None and self._handle.active)

    def ask(self) -> None:
        """The plant of the project in hand: now, or after the job on its way (only the last request counting)."""
        if self._closed:
            return
        if self._handle is not None and self._handle.active:
            self._again = self._handle.state != "settling"      # not started yet: its request is made when it starts
            return
        self._again = False
        self._handle = self.center.submit(KIND, build=self._request, on_done=self._done, on_failed=self._failed,
                                          slot=SLOT, settle=True)

    def current(self, mark) -> bool:
        """Whether `mark` (what an answer was made of) is still the project in hand: its photo, or else its state key
        as the process made it; the layouts in hand; the energy in hand."""
        s = self.session
        photo, layout_keys, energy, key = mark
        return (s.layout_keys == layout_keys and s.energy is energy
                and (s.photo() is photo or s.state_key() == key))

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        handle, self._handle, self._again = self._handle, None, False
        if handle is not None and handle.active:
            handle.cancel()

    # inside

    def _changed(self) -> None:
        if self._told is not None and not self._closed:
            self._told()

    def _rows(self) -> None:
        """The center's rows changed: a job cancelled from the bar asks for nothing more (the plant of before stays)."""
        if self._handle is not None and not self._handle.active and self._handle.state == "cancelled":
            self._handle, self._asked, self._again = None, None, False
            self._changed()

    def _request(self) -> dict:
        """Made when the job starts (Center.build): the inputs in hand, the year only when it is another."""
        s = self.session
        energy = s.energy
        if energy is not self._energy:
            self._energy, self._year_id, self._year = energy, self._year_id + 1, year_of(energy)
        good = s.good_results()
        request = {"photo": s.photo(), "keys": {sid: s.layout_keys.get(sid) for sid in good},
                   "year_id": self._year_id, "language": i18n.language()}
        if self._year_sent != self._year_id:
            request["year"], self._year_sent = self._year, self._year_id
        send, self._send = self._send, set()
        if send:
            request["layouts"] = {sid: good[sid] for sid in send if sid in good}
        self._asked = (request["photo"], dict(s.layout_keys), energy)
        return request

    def _done(self, answer, _stale) -> None:
        self._handle = None
        asked, self._asked = self._asked, None
        missing = answer.get("missing")
        if missing is not None:
            self._tries += 1
            if self._tries >= TRIES:
                self._tries = 0
                log.complain("The plant could not be made", RuntimeError(f"still missing: {missing}"))
                self._again = False
                self._changed()
                return
            self._send = set(missing.get("layouts") or ())
            if missing.get("year"):
                self._year_sent = -1
            self._again = False
            self.ask()
            return
        self._tries = 0
        mark = (*asked, answer["key"]) if asked is not None else None
        if mark is not None and self.current(mark) and self._pieces:
            self._taking = True
            for n, (name, call) in enumerate(self._pieces):
                self.center.piece(name, self._take, call, answer["state"], mark, n == len(self._pieces) - 1)
        if self._again:
            self._again = False
            self.ask()
        self._changed()

    def _take(self, call, state, mark, last: bool) -> None:
        if last:
            self._taking = False
        if not self._closed and self.current(mark):
            call(state, mark)
        if last:
            self._changed()

    def _failed(self, _kind, _sentence) -> None:
        """The sentence is in the status bar already (Center.tell); the plant of before stays."""
        self._handle, self._asked = None, None
        if self._again:
            self._again = False
            self.ask()
        self._changed()
