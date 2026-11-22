"""The reading of an IFC model as a job of the jobs' center (R598, study 48 chapter 6, step 2): the reader
(`ifc_worker`, a process of its own as before: IfcOpenShell's C++ can loop or crash on a broken model) started and
watched from a process of the jobs, never from the window. Here: its lines read and decoded, its time and its memory
watched, its processes looked for every KIDS_EVERY_S, the second try in the «simple» way after a crash, Cancel. The
answer goes to the window in pieces already pickled (`pack`), each small enough to be unpickled in a few
milliseconds on the window's thread (`unpack`, a piece per turn): the megabytes of the solids never stop it.

The reader itself (ifc_read*, ifc_import, ifc_worker, ifc_scan, ifc_mesh) is not touched here: its lines are read as
they are, and keys or stages this module does not know are passed on as they are."""

from __future__ import annotations

import json
import math
import os
import pickle
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

from meridiana.app.work.job import GIB, Kind, Refused
from meridiana.core.compute import procmem
from meridiana.core.compute import resources as _resources
from meridiana.i18n import N_, _, number

WORKER = "meridiana.app.exchange.ifc_worker"     # the module the reading runs as (`python -m`): a name, never put together
BUDGET_S = 180                  # a reading that takes longer is stopped: the file is said too heavy (study 20, 4.2)
SECOND_TRY_S = 60               # the reading again without IfcOpenShell's iterator, after it crashed
BUDGET_SHARE = 0.7              # past this share of its time the worker gives up the shapes left and answers with the rest
MEMORY = procmem.limit()        # half the PC's memory, 8 GiB at most: the reader with its processes
WATCH_S = 0.5                   # how often the reader's time and memory are looked at
KIDS_EVERY_S = 3.0              # how often the reader's processes are looked for again (the memory of each, every look)
KEPT_READINGS = 2               # R548: the readings kept in the window (pickled), the same file asked again in the session
PIECE_BYTES = 64 << 10          # a piece of the answer: unpickled on the window's thread in under a millisecond (model A:
#                                 256 kB pieces took up to 8,7 ms on a loaded PC)

KIND = Kind(name="ifc_read", title=N_("Reading the IFC model"), run="meridiana.app.exchange.ifc_job:read",
            where="process", memory=MEMORY + GIB, low_priority=False, on_change="finish", topics=("project",))
# memory: the reader's own ceiling (MEMORY) is watched here and said with its own words; the job's, a GiB above it,
# only catches what this process would hold beyond the reader. low_priority: the designer waits for the reading (the
# reader raises its own priority). on_change "finish": the reading is of the file, not of the project; what is
# planned of it is made on the project of the moment (dialogs.py, _plan_ifc), as before

STAGES = {"open": N_("Opening the file…"), "structure": N_("Reading the storeys and the buildings…"),
          "roofs": N_("Reading the roofs…"), "tessellate": N_("Making the shapes of the complex elements…"),
          "planes": N_("Finding the roof planes…"), "terraces": N_("Looking for slabs under the open sky…"),
          "obstacles": N_("Looking for what stands on the roofs…"), "done": N_("Done."),
          "again": N_("IfcOpenShell stopped on this file: reading again, the simple shapes only…"),
          "scan": N_("Reading the file, in several processes at once…"),
          "solids": N_("Making the solids of the elements…"),
          "context": N_("Preparing the model's true geometry for the 3D…"),
          "scan_failed": N_("The fast reading stopped: reading with IfcOpenShell…")}


def stage(what: str) -> str:
    """The phase the bar says for a stage of the reader (a msgid); a stage this module does not know, as it is."""
    return STAGES.get(what, what)


def worker_command(path: str, mode: str = "direct", cache: str | None = None) -> tuple[str, list[str], dict]:
    """The program, the arguments and the environment of the worker: this Python (its pythonw on Windows, no console
    window) with the folder of the package on its path, as the window was started from a checkout. `cache`: the folder
    the true geometry of the model is kept in, the session's (R594: never the user's folders behind its back); None,
    no geometry for the 3D."""
    exe = Path(sys.executable)
    if os.name == "nt" and exe.name.lower() == "python.exe" and exe.with_name("pythonw.exe").is_file():
        exe = exe.with_name("pythonw.exe")
    import meridiana
    src = str(Path(meridiana.__file__).resolve().parents[1])       # the folder the package is in, wherever this file is
    env = {"PYTHONPATH": os.pathsep.join(x for x in (src, os.environ.get("PYTHONPATH", "")) if x),
           "PYTHONIOENCODING": "utf-8"}
    budget = SECOND_TRY_S if mode == "simple" else BUDGET_S
    # r21-ifc-vista: the true geometry of the model for the 3D, kept in the cache (ifc_mesh, scene_context)
    context = ["--context", str(cache)] if cache else []
    return str(exe), ["-m", WORKER, path, "--mode", mode, "--budget", str(round(budget * BUDGET_SHARE)),
                      *context], env


def request(path: str, cache: str | None = None, budget_s: float = BUDGET_S, memory: int = MEMORY,
            commands: dict | None = None) -> dict:
    """What the job is asked: the file, the session's cache for the geometry, the time and the memory allowed.
    `commands` stands in for the worker in the tests: the way ("direct", "simple") -> the program with its arguments;
    a way it has not got is never tried."""
    return {"path": str(path), "cache": cache, "budget_s": float(budget_s), "memory": int(memory),
            "commands": commands}


# the job, in a process of the jobs

def read(req: dict, ctx) -> list:
    """The reading of req["path"], with a second try in the simple way after a crash: the answer of the reader as
    `pack` splits it (ctx.partial), with "read_seconds", "read_peak_mb" and, after a second try, "second_try" as the
    window had them. Refused with the designer's sentence past the time or the memory, when the reader cannot read
    the file or does not start."""
    from meridiana import i18n
    if os.environ.get(i18n.WINDOW_LANGUAGE):
        i18n.setup_as_window()          # the window's language for the sentences said to the designer
    started = time.monotonic()
    ctx.progress(0.0, 0.0, stage("open"))
    mode, budget, first_failure, peak = "direct", float(req["budget_s"]), "", 0
    while True:
        outcome, value, used = _once(req, mode, budget, ctx)
        peak = max(peak, used)
        if outcome == "result":
            break
        if outcome == "crash" and mode == "direct" and _has_way(req, "simple"):
            first_failure = value
            ctx.progress(0.0, 1.0, stage("again"))
            mode, budget = "simple", SECOND_TRY_S
            continue
        raise Refused(value)
    result = value
    result["read_seconds"] = round(time.monotonic() - started, 2)
    result["read_peak_mb"] = round(peak / 2 ** 20)
    if first_failure:
        result["second_try"] = first_failure
    return pack(result, ctx.partial)


def _has_way(req: dict, mode: str) -> bool:
    commands = req.get("commands")
    return commands is None or mode in commands


def _command(req: dict, mode: str, budget: float):
    program, args, env = worker_command(req["path"], mode, req.get("cache"))
    commands = req.get("commands")
    if commands is not None:
        given = commands[mode]
        program, args = given[0], list(given[1:])
    return [program, *args], dict(os.environ, **env)


def _once(req: dict, mode: str, budget: float, ctx):
    """One run of the reader: ("result", the answer, peak bytes), ("crash", why, peak) when it ended without an
    answer, ("error", why, peak) for the others. Cancel (ctx.checkpoint) and the limits end the reader and its
    processes before this returns or raises."""
    name = Path(req["path"]).name
    args, env = _command(req, mode, budget)
    flags = 0x08000000 if sys.platform == "win32" else 0                # CREATE_NO_WINDOW
    try:
        proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=env, creationflags=flags)
    except OSError as error:
        raise Refused(_("The reader did not start: {why}").format(why=error)) from None
    lines: queue.SimpleQueue = queue.SimpleQueue()
    tail: list = []

    def out():
        for line in proc.stdout:
            lines.put(line)
        lines.put(None)

    def err():
        for line in proc.stderr:
            tail.append(line)
            del tail[:-3]
    readers = [threading.Thread(target=t, daemon=True, name=f"meridiana-ifc-{w}") for w, t in (("out", out),
                                                                                              ("err", err))]
    for thread in readers:
        thread.start()
    launched = time.monotonic()
    result, error, ended = None, "", False
    kids, kids_at, looks, peak = [], -KIDS_EVERY_S, 0, 0
    watched = launched
    try:
        while not ended:
            ctx.checkpoint()
            try:
                line = lines.get(timeout=WATCH_S)
            except queue.Empty:
                line = b""
            if line is None:
                ended = True
            elif line:
                result, error = _line(line, result, error, ctx)
            now = time.monotonic()
            if now - watched < WATCH_S and not ended:
                continue
            watched = now
            if now - launched > budget:
                # no second try: the simple way of a model too heavy for the first cannot end in its 60 s either
                raise Refused(_("The reading took more than {s} s and was stopped: the model is too large for "
                                "Meridiana, or IfcOpenShell is stuck on one of its elements. Nothing was added. "
                                "Export from the architect's program only the building's shell with its roofs (no "
                                "furniture, no installations, no site) and import that file.").format(s=number(budget, 0)))
            used = procmem.rss(proc.pid)
            if used:
                # the venv's launcher and its interpreter, and the scan's processes: the list of the PC's processes
                # taken again every KIDS_EVERY_S, not at every look (r32-lentezze)
                looks += 1
                if looks <= 3 or now - kids_at >= KIDS_EVERY_S:
                    kids, kids_at = procmem.children(proc.pid), now
                used += sum(procmem.rss(child) or 0 for child in kids)
                peak = max(peak, used)
                if used > req["memory"]:
                    raise Refused(_("The reading took more than {gb} GB of memory and was stopped. Export from the "
                                    "architect's program only the building and try again.").format(
                                        gb=number(req["memory"] / procmem.GIB, 1)))
        code = proc.wait()
    finally:
        _end(proc)
    for thread in readers:
        thread.join(2.0)
    if result is not None:
        return "result", result, peak
    if error:
        return "error", _("{file} could not be read: {why}").format(file=name, why=error), peak
    if tail:
        from meridiana.app.platform import log
        log.complain("ifc reading", RuntimeError(" | ".join(b.decode("utf-8", "replace").strip() for b in tail)))
    return "crash", _("IfcOpenShell stopped while reading {file} (exit code {code}): the file has something it "
                      "cannot read. The window is fine; nothing was added.").format(file=name, code=code), peak


def _line(line: bytes, result, error, ctx):
    """One line of the reader: its progress told, its answer or its error kept (a line that is not one, skipped)."""
    try:
        msg = json.loads(line.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return result, error
    if not isinstance(msg, dict):
        return result, error
    if "progress" in msg:
        ctx.progress(float(msg["progress"]), 1.0, stage(str(msg.get("what", ""))))
    elif "result" in msg:
        result = msg["result"]
    elif "result_file" in msg:
        # R400: a large result comes through a file of the worker, read here and removed
        try:
            path = Path(msg["result_file"])
            result = json.loads(path.read_text(encoding="utf-8"))
            path.unlink(missing_ok=True)
        except (OSError, ValueError) as failure:
            error = str(failure)
    elif "error" in msg:
        error = str(msg["error"])
    return result, error


def _end(proc) -> None:
    """The reader and the processes it started ended, when they are still there (R400: the scan's processes too)."""
    if proc.poll() is not None:
        return
    below = procmem.children(proc.pid)
    try:
        proc.kill()
    except OSError as error:
        from meridiana.app.platform import log
        log.complain("The IFC reader could not be stopped", error)
    for child in below:
        try:
            os.kill(child, 9)
        except OSError:
            continue                    # already gone with its parent
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired as error:
        from meridiana.app.platform import log
        log.complain("The IFC reader did not end", error)


# the answer in pieces

def pack(result: dict, send) -> list:
    """`result` as pieces already pickled, sent with send(key, bytes) (ctx.partial): each key of its own, a list
    larger than PIECE_BYTES cut in parts. The layout returned, [(key, pieces, is a cut list)], is what `unpack` puts
    back together, in the order of the keys."""
    layout = []
    for key, value in result.items():
        blob = pickle.dumps(value, protocol=5)
        if isinstance(value, list) and len(value) > 1 and len(blob) > PIECE_BYTES:
            step = max(1, math.ceil(len(value) / math.ceil(len(blob) / PIECE_BYTES)))
            pieces = [pickle.dumps(value[i:i + step], protocol=5) for i in range(0, len(value), step)]
            cut = True
        else:
            pieces, cut = [blob], False
        for i, piece in enumerate(pieces):
            send(piece_key(key, i), piece)
        layout.append((key, len(pieces), cut))
    return layout


def piece_key(key: str, i: int) -> str:
    return f"{key}#{i}"


class Unpack:
    """The answer put back together from its pieces, one `step()` at a time (each about a millisecond): a fresh
    dict, whoever asks. `blobs`: key#i -> bytes, as `pack` sent them."""

    def __init__(self, layout: list, blobs: dict):
        self.layout, self.blobs = list(layout), blobs
        self.order = [(key, i, cut) for key, n, cut in self.layout for i in range(n)]
        self.at = 0
        self.result: dict = {}

    def missing(self) -> list:
        return [piece_key(k, i) for k, i, _cut in self.order if piece_key(k, i) not in self.blobs]

    def step(self) -> bool:
        """One piece unpickled; True when the whole answer is made (`result`)."""
        if self.at < len(self.order):
            key, i, cut = self.order[self.at]
            value = pickle.loads(self.blobs[piece_key(key, i)])
            if cut:
                self.result.setdefault(key, []).extend(value)
            else:
                self.result[key] = value
            self.at += 1
        return self.at >= len(self.order)


# R548: the readings kept in the window, the same file asked again in the session

def _reading_bytes(reading) -> int:
    layout, blobs = reading
    return sum(len(b) for b in blobs.values()) + 64 * len(layout) + 1024


# (path, size, mtime) -> (layout, blobs): the pieces, pickled (a fresh copy for each); at most KEPT_READINGS, within
# the budget's models (study 56: two readings of a large IFC were kept whatever their size)
_KEPT = _resources.Kept(lambda: _resources.cache_limit("models"), _reading_bytes, most=KEPT_READINGS)


def identity(path: str):
    try:
        st = os.stat(path)
    except (OSError, TypeError, ValueError):
        return None
    return (os.path.normcase(os.path.abspath(path)), st.st_size, st.st_mtime_ns)


def kept(path: str):
    """(layout, blobs) of the reading of `path` kept in this session, unchanged since; None otherwise or when the
    memory is to be spared (resources.preload)."""
    from meridiana.core.compute import resources
    if not resources.preload():
        return None
    return _KEPT.get(identity(path))


def keep(path: str, layout: list, blobs: dict) -> None:
    from meridiana.core.compute import resources
    key = identity(path)
    if key is None or not resources.preload():
        return
    _KEPT[key] = (list(layout), dict(blobs))     # not kept when the models' share cannot take it
