"""The layout of the modules after a change, as a job of the mechanism (R598, docs/studio/48-lavori-pesanti.md, chapter 6,
step 1): in a process kept warm for the session, from the session's photo, only the last change counting.

What travels is small. The window sends the photo and the keys of the layouts it holds (`request_of`); the process keeps
the layouts it made (`ctx.kept`, by sub-field and key) and sends back only those the window does not hold, with every
key (`run`). The window puts them together with its own (`results_of`): a sub-field whose inputs did not change keeps
its very result, so that only the sub-fields really changed are told to the views.

The strings follow the modules laid (R442) here too: the process takes the modules no longer laid out of the strings
on its project, and sends the strings, the project's photo after the change, its topics and the keys of what is
saved before and after (`realigned`). The session applies them as its own `amend` would (session.layout_done) when
the photo they were made on is still the project in hand, without a snapshot on the window's thread; otherwise it
realigns by itself, as before."""

from __future__ import annotations

import copy

from meridiana.app import jobs
from meridiana.app.platform import log
from meridiana.app.work.job import Kind
from meridiana.i18n import N_

SESSION = 24 * 3600.0           # seconds: «for the session» (the Alarm wants a time; a day is longer than one)
SETTLE = 0.12                   # seconds of quiet after the last change: the layout's own pause before (layout_timer)
KEPT = 64                       # layouts a process keeps (sub-field, key), the oldest going first
# what can move a module (session.needs_layout): every topic of the project but those of NO_LAYOUT
TOPICS = ("project:geometry", "project:subfields", "project:fire", "project:site", "project:energy",
          "project:variants")

KIND = Kind(name="layout", title=N_("Layout"), run="meridiana.app.layout_job:run", where="process", processes=1,
            keep_warm=SESSION, low_priority=False, on_change="restart", topics=TOPICS, settle=SETTLE)


def held(session) -> dict:
    """The keys of the layouts the session holds that succeeded: sub-field id -> key."""
    return {sid: key for sid, key in session.layout_keys.items()
            if sid in session.results and not isinstance(session.results[sid], Exception)}


def request_of(session) -> dict:
    """The job's request: the generation it answers for, the photo (a reference, R598 rule 1), the keys held, and
    what the plan's scene of the strings is made with (session.wiring_options), when the plan asks for it."""
    options = session.wiring_options() if session.wiring_options is not None else None
    return {"generation": session.generation, "photo": session.photo(), "known": held(session), "wiring": options}


def run(request: dict, ctx) -> dict:
    """In the job's process: the layouts of the photo's project, those the window holds told by their keys alone."""
    from meridiana.app.session import project_from
    project = project_from(request["photo"])
    window = request.get("known") or {}
    kept = ctx.kept.setdefault("layouts", {})           # (sub-field, key) -> result, in the order they came
    known = {sid: (key, kept[(sid, key)]) for sid, key in window.items() if (sid, key) in kept}
    ctx.checkpoint()
    results, keys, laid = jobs.layout_of(project, known)
    for sid, result in results.items():
        if not isinstance(result, Exception):
            keep(kept, (sid, keys[sid]), result)
    ctx.checkpoint()
    fresh = {sid: r for sid, r in results.items() if isinstance(r, Exception) or window.get(sid) != keys.get(sid)}
    strings = realigned(project, request["photo"], results)
    ctx.checkpoint()
    return {"generation": request.get("generation"), "results": fresh, "keys": keys, "laid": laid,
            "strings": strings, "wiring": wiring_of(project, results, keys, request.get("wiring"))}


def wiring_of(project, results: dict, keys: dict, options: dict | None) -> dict | None:
    """The plan's scene of the strings on the layouts just made and the strings realigned on them (R598: made here
    instead of on the window's thread, 100-340 ms on Rho); None without the plan's options. One that cannot be made
    is said in the log, and the plan makes it as before."""
    if not options:
        return None
    from meridiana.app.view import plan_wiring
    try:
        return plan_wiring.made_with(project, results, keys, options)
    except Exception as error:      # the layout stands without it: the plan makes the scene itself, and says why
        log.complain("The strings' scene could not be made with the layout", error)
        return None


def realigned(project, photo: dict, results: dict) -> dict | None:
    """The strings on the modules laid (R442), as session.realign_strings makes them, on the job's own project: None
    when no string loses a module; else what session.layout_done needs to apply them without a snapshot of its own:
    the strings, the photo after, its topics, what each lost (`gone`) and the keys of what is saved before and
    after (`saved`, ProjectSession.key_of)."""
    from meridiana.app.session import ProjectSession, photo_of, topics_of
    from meridiana.core.energy import plant
    runs = ((project.energy or {}).get("strings") or {}).get("runs") or []
    if not runs:
        return None
    after, gone = plant.realign(runs, *plant.laid_of(project.subfields, results))
    if not gone:
        return None
    before_key = ProjectSession.key_of(project)
    project.energy.__setitem__("strings", plant.touched(project.energy.get("strings"), after))
    after_photo = photo_of(project)
    return {"strings": copy.deepcopy(project.energy["strings"]), "photo": after_photo,
            "topics": sorted(topics_of(photo, after_photo)), "gone": gone,
            "saved": (before_key, ProjectSession.key_of(project))}


def keep(kept: dict, key: tuple, result) -> None:
    """A layout kept in the process, the last used last (KEPT at most, the oldest going first)."""
    kept.pop(key, None)
    kept[key] = result
    while len(kept) > KEPT:
        del kept[next(iter(kept))]


def from_kept(kept: dict, keys: dict, failed: dict | None = None, sent: dict | None = None) -> tuple[dict, list]:
    """For a job at home in the layout's process (the checks, the plant): the layouts of `keys` (sub-field id ->
    key) as the window holds them, from those this process keeps, those the window sent (`sent`, kept too) and the
    failures it told (`failed`); and the sub-fields it has none of (`missing`)."""
    failed, sent = failed or {}, sent or {}
    results, missing = {}, []
    for sid, key in keys.items():
        if sid in failed:
            results[sid] = failed[sid]
        elif sid in sent:
            results[sid] = sent[sid]
            keep(kept, (sid, key), sent[sid])
        elif (sid, key) in kept:
            results[sid] = kept[(sid, key)]
            keep(kept, (sid, key), results[sid])
        else:
            missing.append(sid)
    return results, missing


def lay_missing(project, kept: dict, keys: dict, results: dict, missing: list) -> None:
    """The `missing` layouts laid out here, when the window's key is that of `project` (the photo's): the same layout,
    put in `results` and kept for the layout too; those it cannot have so stay in `missing`."""
    known = {sid: (keys[sid], r) for sid, r in results.items() if not isinstance(r, Exception)}
    laid, laid_keys, _laid = jobs.layout_of(project, known)
    for sid in list(missing):
        if sid in laid and laid_keys.get(sid) == keys[sid]:
            results[sid] = laid[sid]
            missing.remove(sid)
            if not isinstance(laid[sid], Exception):
                keep(kept, (sid, keys[sid]), laid[sid])


def results_of(answer: dict, session) -> dict | None:
    """The layouts of the job's answer put together with the session's own: a sub-field the job did not send keeps the
    result the session holds for that key (the same object). None when the session no longer holds one of them (a
    layout taken meanwhile from elsewhere): the job is to be asked again."""
    fresh, out = answer["results"], {}
    for sid, key in answer["keys"].items():
        if sid in fresh:
            out[sid] = fresh[sid]
            continue
        mine = session.results.get(sid)
        if mine is None or isinstance(mine, Exception) or session.layout_keys.get(sid) != key:
            return None
        out[sid] = mine
    return out
