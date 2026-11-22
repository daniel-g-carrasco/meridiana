"""The processes of the jobs (study 48, chapter 3): started with subprocess, each with a thread that writes its
commands, one that reads its messages and one that keeps its standard error for the log. The threads only move bytes
and unpickle small messages: nothing is computed in the window's process. A stop is asked with grace and the process
killed after GRACE_S; an idle process waits for the next job of its kind for the kind's keep_warm, then is told to go.
The jobs `where="thread"` run here in a threading.Thread, with the same Context.

Every message goes to `deliver(message)`, on the thread that read it; the Center queues it for the window's thread."""

from __future__ import annotations

import heapq
import itertools
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

from meridiana.app.platform import log
from meridiana.app.work import wire

WORKER = "meridiana.app.work.worker"    # the module started as the job's process (`-m`): a name, never put together
GRACE_S = 2.0           # a stop not answered within this is a kill
QUIT_S = 0.5            # a process told to go and still there after this is killed
TAIL = 8192             # bytes of a process's standard error kept for the log


class Alarm:
    """Calls at a time to come, on one thread of their own (the kill after the grace, the end of a warm wait, the
    window woken after a settle)."""

    def __init__(self):
        self._heap: list = []
        self._count = itertools.count()
        self._cond = threading.Condition()
        self._closed = False
        self._thread = threading.Thread(target=self._loop, name="meridiana-work-alarm", daemon=True)
        self._thread.start()

    def at(self, delay: float, call) -> None:
        with self._cond:
            heapq.heappush(self._heap, (time.monotonic() + max(0.0, delay), next(self._count), call))
            self._cond.notify()

    def _loop(self):
        while True:
            with self._cond:
                while not self._closed and (not self._heap or self._heap[0][0] > time.monotonic()):
                    self._cond.wait(None if not self._heap else self._heap[0][0] - time.monotonic())
                if self._closed:
                    return
                _when, _n, call = heapq.heappop(self._heap)
            try:
                call()
            except Exception as error:      # an alarm that fails is said; the others still ring
                log.complain("A job's timer failed", error)

    def close(self):
        with self._cond:
            self._closed = True
            self._heap.clear()
            self._cond.notify()
        self._thread.join(2.0)


class Proc:
    """One process of the jobs. Made at once on the owner's thread, started later by the runner's launcher
    (`spawn`): CreateProcess costs 10-30 ms on Windows, too much for the window's thread. What is sent before the
    process exists waits in `outgoing` and is written when it does."""

    def __init__(self, runner, name: str, low: bool):
        self.runner, self.name, self.low = runner, name, low
        self.popen = None               # None until the launcher has started it
        self.birth = "waiting"          # "waiting" for the launcher, "spawning", "born", or "dropped" before birth
        self.pid = None                 # the interpreter's own (on Windows the launcher of a venv starts it)
        self.run = None                 # the run in hand, or None: idle
        self.share = None               # the share of its last job (index, count)
        self.stopping = None            # the run asked to stop
        self.keep = 0.0                 # how long to wait for a job after that stop (a restart)
        self.keep_warm = 0.0            # how long to wait for a job after an end (Kind.keep_warm)
        self.idle_since = time.monotonic()
        self.alive = True
        self.tail = bytearray()
        self.write_error = ""
        self.threads: list[threading.Thread] = []
        self.outgoing: queue.SimpleQueue = queue.SimpleQueue()

    def spawn(self) -> None:
        """The process started, with the threads of its pipes (on the launcher's thread)."""
        import meridiana
        src = str(Path(meridiana.__file__).resolve().parents[1])       # wherever the package is, the worker finds it
        env = dict(os.environ, PYTHONIOENCODING="utf-8",
                   PYTHONPATH=os.pathsep.join(x for x in (src, os.environ.get("PYTHONPATH", "")) if x))
        args = [sys.executable, "-m", WORKER, "--parent", str(os.getpid())] + (["--low"] if self.low else [])
        flags = 0x08000000 if sys.platform == "win32" else 0                # CREATE_NO_WINDOW
        self.popen = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      env=env, creationflags=flags)
        self.threads = [threading.Thread(target=target, name=f"meridiana-work-{what}-{self.popen.pid}", daemon=True)
                        for what, target in (("write", self._write), ("read", self._read), ("err", self._err))]
        for thread in self.threads:
            thread.start()

    def send(self, message) -> None:
        self.outgoing.put(wire.frame(message))

    def _write(self):
        stream = self.popen.stdin
        while True:
            data = self.outgoing.get()
            if data is None:
                break
            try:
                stream.write(data)
                stream.flush()
            except (OSError, ValueError) as error:      # the process has gone: its reader says how
                self.write_error = str(error)
                return
        try:
            stream.close()
        except OSError as error:
            self.write_error = str(error)

    def _read(self):
        try:
            for message in wire.frames(self.popen.stdout.read):
                if message[0] == "ready":
                    self.pid = message[1]
                    continue
                self.runner._incoming(self, message)
        except (OSError, ValueError, EOFError) as error:
            self.write_error = self.write_error or str(error)
        finally:
            self.runner._ended(self)

    def _err(self):
        for line in iter(self.popen.stderr.readline, b""):
            self.tail += line
            del self.tail[:-TAIL]

    def kill(self) -> None:
        if self.popen is None:
            return
        try:
            self.popen.kill()
        except OSError as error:
            log.complain("A job's process could not be stopped", error)

    def stderr_tail(self) -> str:
        return bytes(self.tail).decode("utf-8", "replace").strip()


class Runner:
    def __init__(self, deliver, alarm: Alarm | None = None):
        self.deliver = deliver
        self.alarm = alarm or Alarm()
        self._lock = threading.Lock()
        self._procs: list[Proc] = []
        self._threads: dict[int, threading.Event] = {}
        self._kept: dict[str, dict] = {}            # `kept` of the thread jobs, per kind
        self._closed = False
        self._births: queue.SimpleQueue = queue.SimpleQueue()
        self._launcher: threading.Thread | None = None

    # processes

    def start(self, kind, run: int, request, share, quota: int, blob: bytes | None = None):
        """Run `kind` as `run` on a process idle for its kind, or a new one; returns at once (a new process is
        started by the launcher's thread). `blob` is the request already pickled (once for all the processes of a
        job); a thread job takes the request itself."""
        if kind.where == "thread":
            self._start_thread(kind, run, request, share)
            return None
        if blob is None:
            import pickle
            blob = pickle.dumps(request, protocol=5)
        born = False
        with self._lock:
            if self._closed:
                raise RuntimeError("the jobs are closed")
            idle = [p for p in self._procs if p.alive and p.run is None and p.stopping is None
                    and p.name == kind.family and p.low == kind.low_priority]
            # a warm process takes the same share as before: what it kept (ctx.kept) is of those parts
            proc = next((p for p in idle if p.share == tuple(share)), None) or (idle[0] if idle else None)
            if proc is None:
                proc = Proc(self, kind.family, kind.low_priority)
                self._procs.append(proc)
                born = True
            proc.run, proc.keep_warm, proc.share = run, float(kind.keep_warm), tuple(share)
        proc.send(("job", run, kind.run, blob, tuple(share), int(quota), kind.family))
        if born:
            if self._launcher is None:
                self._launcher = threading.Thread(target=self._launch, name="meridiana-work-launch", daemon=True)
                self._launcher.start()
            self._births.put(proc)
        return proc

    def warm(self, kind) -> Proc | None:
        """A process for `kind` started ahead and idle, told to import the kind's function, waiting for a job for the
        kind's keep_warm (Center.warm). None when the kind already has a process alive."""
        with self._lock:
            if self._closed:
                raise RuntimeError("the jobs are closed")
            if any(p.alive and p.name == kind.family and p.low == kind.low_priority for p in self._procs):
                return None
            proc = Proc(self, kind.family, kind.low_priority)
            proc.keep_warm = float(kind.keep_warm)
            self._procs.append(proc)
            since = proc.idle_since
        proc.send(("warm", kind.run))
        if self._launcher is None:
            self._launcher = threading.Thread(target=self._launch, name="meridiana-work-launch", daemon=True)
            self._launcher.start()
        self._births.put(proc)
        self._idle(proc, proc.keep_warm, since)
        return proc

    def busy(self, kind) -> bool:
        """Whether the kind's family has processes and every one is at work or stopping: a warm job waits for them
        (Center._settled) rather than start another without what they kept."""
        with self._lock:
            mine = [p for p in self._procs if p.alive and p.name == kind.family and p.low == kind.low_priority]
            return bool(mine) and all(p.run is not None or p.stopping is not None for p in mine)

    def _launch(self) -> None:
        """The launcher's thread: the processes started one after the other, off the owner's thread (CreateProcess
        lets the interpreter go while it works). A process stopped or closed before its turn is never started."""
        while True:
            proc = self._births.get()
            if proc is None:
                return
            with self._lock:
                if self._closed or proc.birth != "waiting" or not proc.alive:
                    continue
                proc.birth = "spawning"
            try:
                proc.spawn()
            except (OSError, ValueError) as error:
                log.complain("A job's process could not be started", error)
                with self._lock:
                    run, proc.run, proc.alive, proc.birth = proc.run, None, False, "dropped"
                    if proc in self._procs:
                        self._procs.remove(proc)
                if run is not None:
                    self.deliver(("failed", run, f"{type(error).__name__}: {error}"))
                continue
            with self._lock:
                proc.birth = "born"

    def stop(self, run: int, keep: float = 0.0) -> None:
        """Ask `run` to stop; killed if not stopped within GRACE_S. `keep`: the process then waits that long for a
        job of its kind (a restart that comes after its settle). A process not yet started is never started."""
        event = self._threads.pop(run, None)
        if event is not None:
            event.set()                 # a thread cannot be killed: its later messages are not listened to
            return
        with self._lock:
            proc = next((p for p in self._procs if p.alive and p.run == run), None)
            if proc is None:
                return
            if proc.birth == "waiting":
                proc.birth, proc.alive, proc.run = "dropped", False, None
                self._procs.remove(proc)
                return
            proc.stopping, proc.keep = run, keep
        proc.send(("stop", run))

        def late():
            if proc.alive and proc.run == run:
                log.complain(f"The job's process {proc.pid} did not stop when asked; ended",
                             TimeoutError(f"no answer within {GRACE_S} s"))
                proc.kill()
        self.alarm.at(GRACE_S, late)

    def _incoming(self, proc: Proc, message) -> None:
        word = message[0]
        if word in ("done", "stopped", "failed", "refused", "memory"):
            if word == "memory":
                self.deliver(message)
                return                  # the process ends by itself
            # idle before the end is told: the owner may ask for the next job as soon as it hears it, and the next
            # job finds this process warm (with what it kept)
            with self._lock:
                keep = max(proc.keep, proc.keep_warm) if proc.stopping is not None else proc.keep_warm
                proc.run, proc.stopping, proc.keep = None, None, 0.0
                proc.idle_since = time.monotonic()
                since = proc.idle_since
            self.deliver(message)
            self._idle(proc, keep, since)
            return
        if proc.stopping is None:
            self.deliver(message)

    def warm_again(self, name: str, keep: float) -> None:
        """The idle processes of a kind wait `keep` seconds again from now. A job of more processes ends with its last
        one: those that ended before (a light share) wait for the next job from the job's end, not from their own,
        or they would be gone before it with what they kept."""
        if keep <= 0:
            return
        with self._lock:
            now = time.monotonic()
            procs = [p for p in self._procs if p.alive and p.run is None and p.stopping is None and p.name == name]
            for proc in procs:
                proc.idle_since = now
        for proc in procs:
            self._idle(proc, keep, now)

    def _idle(self, proc: Proc, keep: float, since: float) -> None:
        if keep <= 0:
            self._quit(proc)
            return

        def expire():
            if not (proc.alive and proc.run is None and proc.idle_since == since):
                return
            with self._lock:
                working = any(p.alive and p.run is not None and p.name == proc.name for p in self._procs)
            if working:                 # its job (or another of its kind) still runs on other processes: it waits
                self.alarm.at(keep, expire)
                return
            self._quit(proc)
        self.alarm.at(keep, expire)

    def _quit(self, proc: Proc) -> None:
        with self._lock:
            if proc.run is not None or not proc.alive:
                return
            proc.alive = False          # never chosen again
        proc.send(("quit",))
        proc.outgoing.put(None)

        def late():
            if proc.popen is not None and proc.popen.poll() is None:     # never started: nothing to kill
                proc.kill()
        self.alarm.at(QUIT_S, late)

    def _ended(self, proc: Proc) -> None:
        """The end of a process's messages: it has gone. A run in hand that was not stopping is a failure."""
        try:
            code = proc.popen.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            code = None
        for thread in proc.threads[2:]:
            thread.join(1.0)
        for stream in (proc.popen.stdout, proc.popen.stderr):
            try:
                stream.close()
            except OSError as error:
                proc.write_error = proc.write_error or str(error)
        with self._lock:
            run, stopping = proc.run, proc.stopping
            proc.alive, proc.run, proc.stopping = False, None, None
            if proc in self._procs:
                self._procs.remove(proc)
        proc.outgoing.put(None)
        if run is not None and stopping is None and not self._closed:
            tail = proc.stderr_tail()
            if tail or proc.write_error:
                log.complain(f"A job's process ended (exit code {code})",
                             RuntimeError(tail[-2000:] or proc.write_error))
            self.deliver(("ended", run, code, tail.splitlines()[-1] if tail else proc.write_error))

    def processes(self) -> list[Proc]:
        with self._lock:
            return [p for p in self._procs if p.alive]

    def all_processes(self) -> list[Proc]:
        with self._lock:
            return list(self._procs)

    # threads

    def _start_thread(self, kind, run, request, share):
        from meridiana.app.work.job import Context, Refused, resolve
        from meridiana.core.compute import resources
        stop = threading.Event()
        self._threads[run] = stop

        def send(message):
            if not stop.is_set():
                self.deliver(message)

        def body():
            ctx = Context(run, share, self._kept.setdefault(kind.family, {}), send, stop=stop)
            try:
                result = resolve(kind.run)(request, ctx)
                ctx.flush()
                send(("done", run, result))
            except resources.Stopped:
                pass
            except Refused as error:        # the user's own sentence
                send(("refused", run, str(error)))
            except Exception as error:      # said to the window; the detail in the log
                log.complain(f"The job {kind.name} failed", error)
                send(("failed", run, f"{type(error).__name__}: {error}"))
            finally:
                self._threads.pop(run, None)
        threading.Thread(target=body, name=f"meridiana-work-{kind.name}", daemon=True).start()

    # the end

    def close(self) -> None:
        """Every process told to go, then killed if still there after QUIT_S; the threads of their pipes ended. A
        process being started is waited for and ended with the others; one still waiting for its turn never starts."""
        with self._lock:
            self._closed = True
        if self._launcher is not None:
            self._births.put(None)
            self._launcher.join(10.0)       # at most the CreateProcess in hand
        with self._lock:
            procs = [p for p in self._procs if p.popen is not None]
            for proc in self._procs:
                if proc.popen is None:
                    proc.alive, proc.birth = False, "dropped"
        for event in list(self._threads.values()):
            event.set()
        self._threads.clear()
        for proc in procs:
            proc.alive = False
            if proc.run is not None:
                proc.send(("stop", proc.run))
            proc.send(("quit",))
            proc.outgoing.put(None)
        end = time.monotonic() + QUIT_S
        for proc in procs:
            try:
                proc.popen.wait(timeout=max(0.0, end - time.monotonic()))
            except subprocess.TimeoutExpired:
                proc.kill()
                try:
                    proc.popen.wait(timeout=2)
                except subprocess.TimeoutExpired as error:
                    log.complain(f"A job's process {proc.popen.pid} did not end", error)
        for proc in procs:
            for thread in proc.threads:
                thread.join(2.0)
            for stream in (proc.popen.stdout, proc.popen.stderr):
                try:
                    stream.close()
                except OSError as error:
                    log.complain("A job's pipe could not be closed", error)
        self.alarm.close()
