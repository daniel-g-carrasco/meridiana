"""The checks as a job of the mechanism (R598, docs/studio/48-lavori-pesanti.md, chapter 6, step 6): one job for the two
that show them (the bridge's rows, `checkRows`, and the Checks panel), in a process, made once for both and handed to
the window as plain data.

What travels is small. The job runs in the layout's process (`Kind.home`): the layouts it checks are those that
process keeps (`ctx.kept`, by sub-field and key, app/layout_job.py), so they never travel. The window sends the photo
(session.photo(), a reference), the keys of the layouts it holds, the layouts that failed (their exception), its language, and
the energy year only when it is not the one sent last (`energy_id`), as the checks read it (`light`): the process
keeps it. A layout the process does not
keep (one the year's process made, one read from the store) it lays out itself when its key is that of the photo's
project, and keeps it for the layout's job too; what it cannot have so (a layout of before, the energy of a process
started since) it asks for (`missing`), and the window asks again with it (Feed).

The Feed is the job's one owner on the window's thread (no Qt): it asks after a short quiet, only the last request
counting; a job on its way goes to its end and the next one comes after it (a job stopped late would leave the
layout's process busy, and the layout would start a cold one); while a layout is on its way it waits for it, since its
layouts are what the checks read. An answer is shown only when it is of the inputs in hand (photo, layouts, energy and
plant, by reference); otherwise it is asked again. Cancel from the bar leaves the checks of before; so does a process
that fails, with its sentence."""

from __future__ import annotations

import dataclasses
import weakref
from dataclasses import dataclass

from meridiana.app import layout_job
from meridiana.app.platform import log
from meridiana.app.work.job import Kind
from meridiana.core.rules import checks, rules
from meridiana import i18n
from meridiana.i18n import N_

SLOT = "checks"
SETTLE = 0.05                   # seconds of quiet before a job: the inputs of one gesture come in a burst
TRIES = 3                       # answers «missing» in a row before the job is said to have failed
TOLD = ("file", "checks", "energy")             # the session's topics the checks are made of, with every "layout:<id>"

# The center never restarts it (no topics): a job stopped late would keep the layout's process busy; the Feed asks
# for the next one after it instead. Its processes are the layout's.
KIND = Kind(name="checks", title=N_("Checks"), run="meridiana.app.checks_job:run", where="process", processes=1,
            keep_warm=layout_job.SESSION, low_priority=layout_job.KIND.low_priority, topics=(), settle=SETTLE,
            home=layout_job.KIND.name)

_FEEDS: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()     # session -> its Feed


def gather_session(project, results, energy, plant_state=None):
    """The checks of the panel: the core's, those of the live strings and of the plant, condensed (R605); the values
    chosen by default; the notes of the rules for the report."""
    from meridiana.core.energy import faces, plant, system
    good = {k: v for k, v in results.items() if not isinstance(v, Exception)}
    arrays = system.arrays_of(project, good)
    inverter = system.combined(system.inverters_of(project, sum(a.p_stc for a in arrays))) if arrays else None
    items = checks.gather(project, results, energy, inverter, bool(system.inverter_entries(project.energy)))
    if plant_state is None:
        sim = (energy or {}).get("sim")
        t_cell = max(a["t_cell_max"] for a in sim.arrays) if sim is not None else None
        p_dc = sim.hourly.p_dc.to_numpy() if sim is not None else None
        plant_state = plant.build(project, good, t_cell_max_year=t_cell, p_dc_hourly=p_dc, exposure=faces.year_of(sim))
    items += checks.plant_items(plant_state, profile_id=project.regulatory_profile)
    items.sort(key=lambda item: checks.LEVELS.index(item.level))
    items = checks.condensed(items, project)        # R605: the plant's items too, one row for what repeats
    return items, checks.defaults_in_use(energy), rules.notes_text(rules.facts(project, results, energy, inverter))


@dataclass
class _Pass:
    """What the checks read of an array's first pass (faces.year_of): the array and its effective irradiance."""
    a: object
    g_eff: object


@dataclass
class _Parts:
    per_array: list


@dataclass
class _Record:
    """A calculation of the year as the checks read it (defaults_in_use): its record alone."""
    record: object


def light(energy: dict) -> dict:
    """The year as the checks read it, made to travel: on Rho the whole of it pickles to 81 MB in 124 ms (the
    simulation's first pass, `parts`, hour by hour for every array), this to about 2 MB. What gather, gather_session
    and the rules read is all there: the simulation's arrays, notes, record, hourly powers, powers at STC, and of its
    first pass each array's effective irradiance (faces.year_of); of the economics and the consumption their record;
    the rest as it is. A simulation that is not the core's (a test's) travels as it is."""
    if not energy:
        return energy
    out = dict(energy)
    sim = out.get("sim")
    if sim is not None and dataclasses.is_dataclass(sim):
        per = [_Pass(p.a, p.g_eff) for p in getattr(getattr(sim, "parts", None), "per_array", None) or []]
        out["sim"] = dataclasses.replace(sim, parts=_Parts(per), inverters=[], stages={}, example={})
    for name in ("econ", "load"):
        if out.get(name) is not None and hasattr(out[name], "record"):
            out[name] = _Record(out[name].record)
    return out


def run(request: dict, ctx) -> dict:
    """In the layout's process: the checks of the photo's project on the layouts the window holds (by their keys),
    or what is missing to make them."""
    from meridiana.app import plant_job
    from meridiana.app.session import project_from
    if request.get("language") and i18n.language() != request["language"]:
        i18n.setup(request["language"])                 # the window's: the rows are in the words it speaks now
    kept = ctx.kept.setdefault("layouts", {})          # layout_job's: (sub-field, key) -> result
    if "energy" in request:
        ctx.kept["energy"] = (request["energy_id"], request["energy"])
    have = ctx.kept.get("energy")
    no_energy = have is None or have[0] != request["energy_id"]
    keys, failed = request["keys"], request.get("failed") or {}
    results, missing = layout_job.from_kept(kept, keys, failed, request.get("layouts"))
    if no_energy and not missing:
        return {"missing": {"layouts": [], "energy": True}}
    ctx.checkpoint()
    project = project_from(request["photo"])
    if missing:
        # laid out here when the window's key is that of the photo's project: the same layout, kept for the layout too
        layout_job.lay_missing(project, kept, keys, results, missing)
    if missing or no_energy:
        return {"missing": {"layouts": missing, "energy": no_energy}}
    energy = have[1]
    ctx.checkpoint()
    bridge = [vars(item) for item in checks.gather(project, results, energy)]
    ctx.checkpoint()
    state = request.get("plant")
    if state is None:
        # the plant of these very inputs, made once in this process for the plant's job and for the checks
        good = {sid: r for sid, r in results.items() if not isinstance(r, Exception)}
        state = plant_job.shared(ctx, request["photo"], {sid: keys[sid] for sid in good}, plant_job.year_of(energy),
                                 project, good)
    items, extras, notes = gather_session(project, results, energy, state)
    return {"bridge": bridge, "items": items, "extras": extras, "notes": notes, "names": checks.object_names(project)}


def _travelling(error: Exception) -> Exception:
    """A layout's failure as it can travel: itself when it is one of Python's own, else its words (what the checks
    say of it, `{error}`, is the same)."""
    return error if type(error).__module__ == "builtins" else RuntimeError(str(error))


class Feed:
    """The checks of one session, for whoever shows them (`join`): one job, asked when what they are made of changes.
    `center` is the window's jobs' Center, or a callable that gives it (made when first asked)."""

    def __init__(self, session, center):
        self.session, self._center, self._centre = session, center, None
        self.result: dict | None = None         # the last answer shown: bridge, items, extras, notes, names
        self.error = ""
        self.plant_state = None                 # the shell's live plant, when it gives one (ChecksBackend)
        self._readers: list = []                # (name, deliver, failed, wants)
        self._handle = None                     # the job in hand
        self._asked = None                      # the inputs it was asked on, by reference
        self._again = False                     # asked while a job was on its way: one more after it
        self._pending = False                   # asked while a layout was on its way: when it comes
        self._energy, self._energy_id, self._energy_sent = None, 0, -1
        self._send: set = set()                 # the layouts the process asked for, sent with the next request
        self._tries = 0
        self._forced = False                    # asked with always=True: wanted until an answer is shown
        self._closed = False
        _FEEDS[session] = self
        session.subscribe(self._changed)

    @staticmethod
    def of(session) -> Feed | None:
        """The Feed of `session`'s window, if it has one."""
        return _FEEDS.get(session)

    @property
    def center(self):
        if self._centre is None:
            self._centre = self._center() if callable(self._center) else self._center
            self._centre.subscribe(self._rows)
        return self._centre

    def join(self, name: str, deliver, failed=None, wants=None) -> None:
        """`deliver(answer)` is called with every answer shown, as a piece of the window's turns named `name`;
        `failed(sentence)` when the job fails; `wants()`: whether this reader wants the checks made now (by default
        always). The answer in hand, if any, is given at once."""
        self._readers.append((name, deliver, failed, wants))
        if self.result is not None:
            deliver(self.result)
        self.ask()

    def leave(self, deliver) -> None:
        self._readers = [r for r in self._readers if r[1] != deliver]

    def wanted(self) -> bool:
        return self._forced or any(wants is None or wants() for _n, _d, _f, wants in self._readers)

    def busy(self) -> bool:
        """Whether checks are on their way, or waiting for a layout to come."""
        return self._pending or self._again or (self._handle is not None and self._handle.active)

    def cancel(self) -> None:
        """The job in hand, if any, not awaited any more (the checks of before stay)."""
        handle, self._handle = self._handle, None
        self._again = self._pending = self._forced = False
        if handle is not None and handle.active:
            handle.cancel()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.cancel()
        if self._changed in self.session.listeners:
            self.session.listeners.remove(self._changed)
        if _FEEDS.get(self.session) is self:
            del _FEEDS[self.session]
        self._readers = []

    # asking

    def _changed(self, topics) -> None:
        if self._closed or not (topics & set(TOLD) or any(t.startswith("layout:") for t in topics)):
            return
        self.plant_state = None         # the shell's live plant is of the project before (as the panel had it)
        if self.wanted():
            self.center.timed("checks.changed", self.ask)

    def ask(self, always: bool = False) -> None:
        """The checks of the project in hand: after the quiet, from the request made then; after the job on its way,
        if any; after the layout on its way, if any. `always`: even when no reader wants them now."""
        self._forced = self._forced or always
        if self._closed or not self.wanted():
            return
        if self._layout_coming():
            self._pending = True
            if self._handle is not None and self._handle.active:
                self._handle.cancel()           # of the layouts of before: the layout's process is freed sooner
            self._handle, self._again = None, False
            return
        self._pending = False
        if self._handle is not None and self._handle.active:
            self._again = self._handle.state != "settling"      # not started yet: its request is made when it starts
            return
        self._again = False
        self._handle = self.center.submit(KIND, build=self._request, on_done=self._done, on_failed=self._failed,
                                          settle=True)

    def _layout_coming(self) -> bool:
        return any(row["slot"] == layout_job.KIND.name for row in self.center.rows())

    def _rows(self) -> None:
        """The center's rows changed: a layout gone without an answer (cancelled, failed) lets the checks waiting
        for it go; a job cancelled from the bar asks for nothing more (the checks of before stay)."""
        if self._handle is not None and not self._handle.active:
            if self._handle.state == "cancelled":
                self._handle, self._again = None, False
        if self._pending and not self._layout_coming():
            self.ask()

    def _request(self) -> dict:
        """Made when the job starts (Center.build): the inputs in hand, the energy only when it is another."""
        s = self.session
        results, energy = s.results, s.energy
        if energy is not self._energy:
            self._energy, self._energy_id = energy, self._energy_id + 1
        request = {"photo": s.photo(), "keys": {sid: s.layout_keys.get(sid) for sid in results},
                   "failed": {sid: _travelling(r) for sid, r in results.items() if isinstance(r, Exception)},
                   "energy_id": self._energy_id, "plant": self.plant_state, "language": i18n.language()}
        if self._energy_sent != self._energy_id or not energy:
            request["energy"], self._energy_sent = light(energy), self._energy_id
        send, self._send = self._send, set()
        if send:
            request["layouts"] = {sid: results[sid] for sid in send
                                  if sid in results and not isinstance(results[sid], Exception)}
        self._asked = (request["photo"], results, energy, self.plant_state)
        return request

    # answers

    def _done(self, answer, _stale) -> None:
        self._handle = None
        asked, self._asked = self._asked, None
        missing = answer.get("missing")
        if missing is not None:
            self._tries += 1
            if self._tries >= TRIES:
                self._tries = 0
                log.complain("The checks could not be made", RuntimeError(f"still missing: {missing}"))
                return
            self._send = set(missing.get("layouts") or ())
            if missing.get("energy"):
                self._energy_sent = -1
            self._again = False
            self.ask()
            return
        self._tries = 0
        s = self.session
        current = asked is not None and all(a is b for a, b in zip(asked, (s.photo(), s.results, s.energy,
                                                                          self.plant_state), strict=True))
        if current:
            self.result, self.error, self._forced = answer, "", False
            for name, deliver, _failed, _wants in self._readers:
                self.center.piece(name, deliver, answer)
        if self._again or not current:
            self._again = False
            self.ask()

    def _failed(self, _kind, sentence) -> None:
        self._handle, self._asked = None, None
        self.error = sentence
        for _name, _deliver, failed, _wants in self._readers:
            if failed is not None:
                failed(sentence)
        if self._again:
            self._again = False
            self.ask()
