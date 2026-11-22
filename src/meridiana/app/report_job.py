"""The technical report as jobs of the jobs' center (R598, study 48 chapter 6, step 3): its preview and its export, in
a process of the jobs that starts and watches the report's own process (`report_worker`, in gui: the report draws
with Qt, and a job's function lives in app or core, job.resolve). Here, never on the window's thread: the year read
from the store of the years and written once for the report's process, the request written, the report's process
started (or the one kept warm for it) and its lines read, its pages sent one by one as results on the way
(ctx.partial), its pause while the designer works (a preview made ahead, R548 r27), Cancel, and for an export the
files put in their place (as `.part`, renamed at the end) and the export remembered (R437).

The window's request is small: the session's photo, the options, where the year is (`year_spec`), the folder of its
own (`root`) where every folder of its reports lives, and the folders it no longer shows (`drop`)."""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from meridiana.app.work.job import Kind, Refused
from meridiana.core.compute import procmem
from meridiana.i18n import N_, _

SESSION = 24 * 3600.0           # seconds: «for the session», as the layout's process
SETTLE = 0.18                   # the quiet after a change before the preview is made again (the page's timer before)
WATCH_S = 0.1                   # how often the report's process, Cancel and the pause are looked at
YEAR_WAIT_S = 300.0             # a year file the window is still writing (year_spec "file"), waited for at most this
TAIL = 12000                    # bytes of the report process's standard error kept
NAME = "report"                 # one name: the preview and the export share the process kept warm
# what the report is made of: every change but the selection (the page's rule before)
TOPICS = ("project", "restored", "file", "layout", "energy", "checks")
PAUSED = N_("waiting while you work")

PREVIEW = Kind(name=NAME, title=N_("Report preview"), run="meridiana.app.report_job:make", memory=procmem.limit(),
               keep_warm=SESSION, low_priority=False, on_change="restart", topics=TOPICS, settle=SETTLE)
# made ahead while the page is not shown (R548): below the window, ended by a change (its pages would not be shown;
# the page plans the next one at the next quiet), no process kept for it
AHEAD = Kind(name=NAME, title=N_("Report preview"), run="meridiana.app.report_job:make", memory=procmem.limit(),
             keep_warm=0.0, low_priority=True, on_change="discard", topics=TOPICS)
# an export goes to its end on its photo: on_done says `stale` when the project changed meanwhile
EXPORT = Kind(name=NAME, title=N_("Technical report"), run="meridiana.app.report_job:make", memory=procmem.limit(),
              keep_warm=SESSION, low_priority=False, on_change="finish", topics=TOPICS)


def year_spec(session, cache) -> dict | None:
    """Where the report's process finds the year in hand without the window serializing it: the store of the years
    (data/year_store, written by the year's own process) by its key, with the keys of the layouts in hand (the
    report is made on them); None when the session has no year computed to look for there."""
    key = session.energy_key_computed
    if cache is None or not key or not session.energy or session.energy.get("sim") is None:
        return None
    from meridiana.app import year_key
    from meridiana.app.layout_job import held
    return {"store": {"cache": str(cache), "fingerprint": year_key.fingerprint(key), "key": key,
                      "layouts": held(session)}}


# the job, in a process of the jobs

def make(req: dict, ctx) -> dict:
    """A preview or an export. The preview's result: its pages (also sent one by one, "page:<n>"), their total and
    the folder they are drawn from; the export's: the files written and the year's fingerprint; {"missing": "year"}
    when the year is not in the store as asked (the window writes it itself and asks again); {"failed": sentence}
    for a preview made ahead (said by the page when entered, never in the status bar)."""
    from meridiana import i18n
    if os.environ.get(i18n.WINDOW_LANGUAGE):
        i18n.setup_as_window()
    root = Path(req["root"])
    root.mkdir(parents=True, exist_ok=True)
    for folder in req.get("drop") or ():
        shutil.rmtree(folder, ignore_errors=True)       # folders of previews the window no longer shows
    from meridiana.app import year_key
    from meridiana.app.session import project_from
    project = project_from(req["photo"])
    fingerprint = year_key.fingerprint(year_key.expected(project))
    targets = [Path(t) for t in req.get("targets") or ()]
    for target in targets[:1]:
        _writable(target)
    year = _year(req, project, ctx)
    if year is None:
        return {"missing": "year"}
    proc, folder = _process(req, ctx)
    try:
        request = {"project": req["photo"], "energy": {"year_file": str(year), "extra": req.get("extra") or {}},
                   "profile": req["profile"], "embedded": req["embedded"], "mode": req["mode"],
                   "language": req["language"], "width": req.get("width", 1240), "kind": req.get("kind", "pdf"),
                   "register": req.get("register", False), "fingerprint": fingerprint, "date": req["date"]}
        name = "request.pickle"
        with (folder / name).open("wb") as stream:
            pickle.dump(request, stream, protocol=pickle.HIGHEST_PROTOCOL)
        result = _relay(proc, folder, name, req, ctx)
        if req["mode"] == "preview":
            out = {"pages": result["pages"], "total": result["total"], "folder": str(folder)}
        else:
            made = [Path(p) for p in result.get("made") or ()]
            _put(made, targets[:len(made)])
            if req.get("remember"):
                remember(req["remember"]["path"], req["remember"]["name"], targets[0], fingerprint, req["date"])
            out = {"written": [str(t) for t in targets[:len(made)]], "fingerprint": fingerprint, "date": req["date"]}
            shutil.rmtree(folder, ignore_errors=True)
    except Refused as error:
        if proc is not None:
            _end(proc)
        shutil.rmtree(folder, ignore_errors=True)
        if req.get("low"):
            out = {"failed": str(error)}
        else:
            if req.get("spare"):
                _spare(req, ctx)        # the next report finds its process warm, whatever this one said
            raise
    except BaseException:
        if proc is not None:
            _end(proc)
        shutil.rmtree(folder, ignore_errors=True)       # Cancel, the window gone, an error: no folder left
        raise
    if req.get("spare"):
        _spare(req, ctx)
    return out


def _writable(target: Path) -> None:
    """The place of the file there and writable before anything is made (as export_steps did beside it)."""
    part = target.with_name(target.name + ".part")
    try:
        part.write_bytes(b"")
        part.unlink()
    except OSError as error:
        raise Refused(_("{file} cannot be written").format(file=target)) from error


def _put(made: list, targets: list) -> None:
    """The files made in their places, each written as `<name>.part` beside it and renamed at the end: whole or not
    at all, and an older file under the same name stays as it was until then."""
    for source, target in zip(made, targets, strict=True):
        part = target.with_name(target.name + ".part")
        try:
            try:
                os.replace(source, part)
            except OSError:                 # another volume than the cache's
                shutil.copyfile(source, part)
            os.replace(part, target)
        except OSError as error:
            if part.exists():
                part.unlink()
            raise Refused(_("{file} cannot be written").format(file=target)) from error


def remember(path, name: str, target, fingerprint: str, date: str) -> None:
    """R437: what the report exported last of the project `name` was made from, in the window's state."""
    if not path or not name:
        return
    from meridiana.data import atomic
    path = Path(path)
    try:
        records = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, ValueError):
        records = {}
    records[name] = dict(file=str(target), fingerprint=fingerprint, date=date)
    atomic.write_json(path, records)


# the year

def _year(req: dict, project, ctx) -> Path | None:
    """The file of the year for the report's process: the one the window writes (`file`), waited for; or the year
    of the store, with the layouts in hand, written once for every report of it (the preview made ahead too, in its
    own process: the same name). None when the store has not that year, or its layouts are not those in hand."""
    spec = req["year"]
    if "file" in spec:
        path, end = Path(spec["file"]), time.monotonic() + YEAR_WAIT_S
        while not path.is_file():
            ctx.checkpoint()
            if time.monotonic() > end:
                raise Refused(_("The report could not be made"))
            time.sleep(0.05)
        return path
    store = spec["store"]
    layouts = store["layouts"]
    mark = hashlib.sha256(json.dumps([store["key"], sorted(layouts.items())]).encode("utf-8")).hexdigest()[:24]
    folder = Path(req["root"]) / "years"
    path = folder / f"year-{mark}.pickle"
    if path.is_file():
        return path
    from meridiana.data import year_store
    data = year_store.read(Path(store["cache"]), store["fingerprint"], store["key"])
    ctx.checkpoint()
    if data is None:
        return None
    keys = data["layout_keys"]
    results = {sid: r for sid, r in data["results"].items() if not isinstance(r, Exception)}
    if {sid: keys.get(sid) for sid in results} != layouts:
        # the layouts in hand are newer than the year's: those of the photo, the year's kept where the keys agree
        from meridiana.app import jobs
        laid, laid_keys, _laid = jobs.layout_of(project, {sid: (keys[sid], r) for sid, r in results.items()
                                                          if sid in keys})
        results = {sid: r for sid, r in laid.items() if not isinstance(r, Exception)}
        if {sid: laid_keys.get(sid) for sid in results} != layouts:
            return None
        ctx.checkpoint()
    folder.mkdir(parents=True, exist_ok=True)
    part = path.with_name(f"{path.name}.{os.getpid()}.part")
    with part.open("wb") as stream:
        pickle.dump({**data["energy"], "results": results}, stream, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(part, path)
    for old in folder.glob("year-*.pickle"):
        if old != path:
            try:
                old.unlink()
            except OSError:
                continue                # read by the other process this moment (Windows): it goes the next time
    return path


# the report's process

def _environment(folder: Path, low: bool) -> dict:
    import meridiana
    source = str(Path(meridiana.__file__).resolve().parents[1])     # the folder the package is in
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(x for x in (source, os.environ.get("PYTHONPATH", "")) if x),
               PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    env.pop("MERIDIANA_REPORT_LOW", None)
    if low:
        env["MERIDIANA_REPORT_LOW"] = "1"           # R548: the preview made ahead, below the window and the year
    for name in ("TMP", "TEMP", "TMPDIR", "MPLCONFIGDIR"):
        env[name] = str(folder)
    return env


def _start(req: dict, folder: Path, warm: bool):
    flags = 0x08000000 if sys.platform == "win32" else 0                # CREATE_NO_WINDOW
    args = [sys.executable, "-m", req["worker"]] + (["--warm", str(folder)] if warm else [str(folder), "request.pickle"])
    return subprocess.Popen(args, stdin=subprocess.PIPE if warm else subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=_environment(folder, bool(req.get("low"))),
                            creationflags=flags)


def _process(req: dict, ctx):
    """The report's process for this job: the one kept warm (its imports done, waiting for «go») with its folder,
    or None and a new folder (the process is started by _relay, once the request is there). As before, an export
    starts its own and leaves the warm one to the next preview (the page is where the designer waits for it)."""
    spare = ctx.kept.pop("spare", None) if req["mode"] == "preview" else None
    if spare is not None:
        proc, folder = spare
        if proc.poll() is None and folder.is_dir():
            return proc, folder
        _end(proc)
        shutil.rmtree(folder, ignore_errors=True)
    return None, Path(tempfile.mkdtemp(prefix="run-", dir=req["root"]))


def _spare(req: dict, ctx) -> None:
    """A report's process started now for the next preview, its imports done while nothing is asked (study 41);
    one at most."""
    if "spare" in ctx.kept:
        return
    folder = Path(tempfile.mkdtemp(prefix="run-", dir=req["root"]))
    try:
        ctx.kept["spare"] = (_start(req, folder, warm=True), folder)
    except OSError as error:            # the next report starts its process cold, as before
        from meridiana.app.platform import log
        log.complain("The report's process kept warm could not be started", error)
        shutil.rmtree(folder, ignore_errors=True)


def _relay(proc, folder: Path, name: str, req: dict, ctx) -> dict:
    """The report made by its process: its progress and its pages told, Cancel and the pause followed; its
    result.json, or Refused with what its standard error says."""
    if proc is None:
        proc = _start(req, folder, warm=False)
    else:
        proc.stdin.write(f"go {name}\n".encode("utf-8"))
        proc.stdin.close()
    lines: queue.SimpleQueue = queue.SimpleQueue()
    tail = bytearray()

    def out():
        for line in proc.stdout:
            lines.put(line)
        lines.put(None)

    def err():
        for line in proc.stderr:
            tail.extend(line)
            del tail[:-TAIL]
    readers = [threading.Thread(target=t, daemon=True, name=f"meridiana-report-{w}") for w, t in (("out", out),
                                                                                                 ("err", err))]
    for thread in readers:
        thread.start()
    pause = req.get("pause")
    paused, done, what, pages = False, 0.0, "", 0
    try:
        while True:
            ctx.checkpoint()
            wanted = bool(pause) and os.path.exists(pause)
            if wanted != paused:
                paused = suspend(proc.pid, wanted) and wanted
                ctx.progress(done, 1.0, PAUSED if paused else what)
            try:
                line = lines.get(timeout=WATCH_S)
            except queue.Empty:
                continue
            if line is None:
                break
            try:
                event = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                continue
            if event.get("event") == "progress":
                done, what = float(event["fraction"]), str(event["what"])
                ctx.progress(done, 1.0, what)
            elif event.get("event") == "outline":
                ctx.partial("outline", event["rows"])
            elif event.get("event") == "page":
                ctx.partial(f"page:{event['n']}", event["row"])
                pages += 1
        code = proc.wait()
    except BaseException:
        _end(proc)
        raise
    for thread in readers:
        thread.join(2.0)
    manifest = folder / "result.json"
    if code or not manifest.is_file():
        text = bytes(tail).decode("utf-8", "replace").strip()
        if text:
            from meridiana.app.platform import log
            log.complain(f"The report's process ended (exit code {code})", RuntimeError(text[-2000:]))
        raise Refused(text.splitlines()[-1] if text else _("The report could not be made"))
    ctx.flush()
    return json.loads(manifest.read_text(encoding="utf-8"))


def _end(proc) -> None:
    """The report's process and those under it ended (Windows: the venv's launcher starts the interpreter as its
    child), waited for: its files are let go before its folder goes."""
    if proc.poll() is not None:
        return
    below = procmem.children(proc.pid)
    for pid in below:
        try:
            os.kill(pid, 9)
        except OSError:
            continue                    # already gone with its parent
    try:
        proc.kill()
        proc.wait(timeout=5)
    except (OSError, subprocess.TimeoutExpired) as error:
        from meridiana.app.platform import log
        log.complain("The report's process could not be stopped", error)


def suspend(pid: int, pause: bool) -> bool:
    """The process `pid` and those under it paused (`pause`) or let go on (r27: a preview made ahead waits while the
    designer works); whether it took."""
    if not pid:
        return False
    try:
        if sys.platform == "win32":
            import ctypes
            k32, ntdll = ctypes.windll.kernel32, ctypes.windll.ntdll
            k32.OpenProcess.restype = ctypes.c_void_p
            k32.CloseHandle.argtypes = (ctypes.c_void_p,)
            call = ntdll.NtSuspendProcess if pause else ntdll.NtResumeProcess
            call.argtypes = (ctypes.c_void_p,)
            done = False
            for one in [pid, *procmem.children(pid)]:
                handle = k32.OpenProcess(0x0800, False, one)        # PROCESS_SUSPEND_RESUME
                if handle:
                    done = call(handle) == 0 or done
                    k32.CloseHandle(handle)
            return done
        import signal
        for one in [pid, *procmem.children(pid)]:
            os.kill(one, signal.SIGSTOP if pause else signal.SIGCONT)
        return True
    except (OSError, AttributeError):
        return False
