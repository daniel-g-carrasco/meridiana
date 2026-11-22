"""The one owner of the heavy jobs (study 48, chapter 3): it takes them (`submit`, `adopt`), keeps only the last one of
each slot, cancels, decides what a change of the project does to them (`changed`, the session's listener), hands their
messages to the owner's thread a few milliseconds at a time (`pump`) and gives the bar its rows (`rows`).

Every message of a process or a thread job comes in on the thread that read it and waits in a queue; only `pump`,
on the owner's thread (the window's), calls back the job's owner. `post()` asks the owner for a `pump` soon (Qt: a
queued signal; the tests: nothing, they pump). Each call back is timed: `stats()` has the longest, with its name, for
the guard of the window (tests/quick/aiuti/finestra_libera.py)."""

from __future__ import annotations

import contextlib
import itertools
import pickle
import threading
import time
from dataclasses import dataclass, field

from meridiana.app.platform import log
from meridiana.app.work.eta import Eta
from meridiana.app.work.job import Handle, Kind
from meridiana.app.work.runner import Alarm, Runner
from meridiana.core.compute import resources
from meridiana.i18n import _, number

KEEP_AFTER_SETTLE = 5.0         # seconds a process stopped for a restart waits beyond the settle for its next job
WARM_WAIT = 0.02                # seconds between two looks of a warm job waiting for its busy process (_settled)


@dataclass(eq=False)
class _Job:
    """What the center keeps of a job besides its Handle."""
    request: object = None
    build: object = None
    slot: str = ""
    on_partial: object = None
    on_done: object = None
    on_failed: object = None
    cancel: object = None               # an adopted job's own Cancel
    count: int = 1                      # its processes
    runs: list = field(default_factory=list)
    shares: dict = field(default_factory=dict)      # index -> (done, total)
    phases: dict = field(default_factory=dict)      # index -> the phase it told last (a msgid)
    results: dict = field(default_factory=dict)
    rss: dict = field(default_factory=dict)
    eta: Eta = field(default_factory=Eta)
    settle_until: float = 0.0


def size_text(n: int) -> str:
    """Bytes as the designer reads them: «1,5 GB», «512 MB»."""
    if n >= resources.GIB:
        return f"{number(n / resources.GIB, 1)} GB"
    return f"{number(n / resources.MIB, 0)} MB"


class Center:
    def __init__(self, post, clock=time.monotonic, tell=None):
        """`post()`: asks the owner to call pump() soon, on its thread; it may be called from any thread. `clock`:
        the time of the settles and of the estimates (the tests give one of their own). `tell(text)`: a sentence for
        the status bar when a job fails (rule 9), beside its own on_failed."""
        self._post, self.clock, self.tell = post, clock, tell
        self._lock = threading.Lock()
        self._events: dict = {}             # key -> message, in the order they came; one key per coalesced kind
        self._serial = itertools.count()
        self._posted = False
        self._ids = itertools.count(1)
        self._run_ids = itertools.count(1)
        self._handles: dict[int, Handle] = {}       # the jobs in hand, in the order they came
        self._jobs: dict[int, _Job] = {}
        self._slots: dict[str, Handle] = {}
        self._runs: dict[int, tuple[Handle, int]] = {}
        self._listeners: list = []
        self._pieces: dict = {}             # name -> (call, args): the owner's own work, a piece per turn (piece)
        self._dirty = False
        self._closed = False
        self.reset_stats()
        self.alarm = Alarm()
        self.runner = Runner(self._incoming, self.alarm)

    # taking jobs

    def submit(self, kind: Kind, request=None, *, build=None, slot=None, on_partial=None, on_done=None,
               on_failed=None, settle: bool = False) -> Handle:
        """A job of `kind` on `request` (picklable and small: the project's photo, session.photo(), and the
        options). build(): called on the owner's thread at each restart, gives the new request, and must be cheap.
        slot (kind.name by default): a new job in a slot takes the place of the one there. on_partial(key, data),
        on_done(result, stale) and on_failed(kind, message) are called on the owner's thread; the result of a job of
        more processes is the list of their results, in the order of their shares. `settle`: the job starts after
        the kind's quiet, as a restart does (the owner of a result already done that the project's change made old:
        a drag asks again at every step, and only the last one starts); its request is then made by build()."""
        if self._closed:
            raise RuntimeError("the jobs are closed")
        with self._timed(f"submit:{kind.name}"):
            slot = slot or kind.name
            old = self._slots.get(slot)
            if old is not None and old.active:
                self._drop(old, "cancelled")
            if request is None and build is not None and not settle:
                request = build()
            handle = Handle(next(self._ids), kind, kind.title, center=self, since=self.clock())
            self._handles[handle.id] = handle
            job = self._jobs[handle.id] = _Job(request, build, slot, on_partial, on_done, on_failed)
            self._slots[slot] = handle
            if settle:
                handle.state = "settling"
                job.settle_until = self.clock() + kind.settle
                self.alarm.at(kind.settle, self._wake)
                self._touch()
                return handle
            try:
                self._launch(handle)
            except (pickle.PicklingError, TypeError, AttributeError):
                self._drop(handle, "failed")            # a request that cannot travel: the caller's mistake, raised
                raise
            self._touch()
        return handle

    def adopt(self, title: str, cancel=None, slot: str = "") -> Handle:
        """A job that runs elsewhere and only shows here (the year, today): its progress told with Handle.progress,
        its end with Handle.end; `cancel()` is what the bar's Cancel calls; `slot` names its row (rows())."""
        handle = Handle(next(self._ids), None, title, center=self, state="running", adopted=True, since=self.clock())
        self._handles[handle.id] = handle
        self._jobs[handle.id] = _Job(cancel=cancel, slot=slot)
        self._touch()
        return handle

    def warm(self, kind: Kind) -> None:
        """A process of `kind` started ahead, its function imported, and kept for the kind's keep_warm: the first job
        does not wait for the imports (the layout after the first change). Nothing shows in the bar; a kind that
        already has a process alive is left as it is."""
        if self._closed or kind.where != "process" or kind.keep_warm <= 0:
            return
        with self._timed(f"warm:{kind.name}"):
            self.runner.warm(kind)

    def piece(self, name: str, call, *args) -> None:
        """A piece of the owner's own work on its thread, run by pump() on a turn of the window after the jobs'
        deliveries, as many as fit in the turn's budget (one at least), each timed under `name` as a delivery is
        (stats): what the window does with a result, spread over its turns instead of all at once (the views told
        of a layout one by one). A piece of the same name still waiting is replaced by this one, in its place (only
        the last counts). What it raises is said in the log, as a delivery's."""
        if self._closed:
            return
        self._pieces[name] = (call, args)
        self._wake()

    def flush_pieces(self) -> None:
        """Every piece still waiting run now, in order (its owner needs them done: a new change of the project)."""
        while self._pieces and not self._closed:
            name = next(iter(self._pieces))
            call, args = self._pieces.pop(name)
            self._call(name, call, *args)

    def _launch(self, handle: Handle) -> None:
        job, kind = self._jobs[handle.id], handle.kind
        count = 1
        if kind.where == "process":
            count = max(1, min(kind.processes, resources.workers_for(kind.processes, resources.MIN_WEIGHT)))
        blob = pickle.dumps(job.request, protocol=5) if kind.where == "process" else None
        job.count, job.runs, job.shares, job.phases, job.results, job.rss = count, [], {}, {}, {}, {}
        job.eta.reset()
        handle.state = "waiting"
        for index in range(count):
            run = next(self._run_ids)
            self._runs[run] = (handle, index)
            job.runs.append(run)
            try:
                self.runner.start(kind, run, job.request, (index, count), kind.memory // count, blob)
            except (OSError, RuntimeError, ValueError) as error:
                self._fail(handle, _("{title} could not start: {error}"), f"{type(error).__name__}: {error}")
                return

    # the owner's gestures

    def cancel(self, handle: Handle) -> None:
        """Cancel: the row goes at once (the listeners are told now), the processes stop with grace and, past
        runner.GRACE_S, are killed; an adopted job's own Cancel is called."""
        if not handle.active:
            return
        with self._timed(f"cancel:{handle.kind.name if handle.kind else handle.title}"):
            job = self._jobs.get(handle.id)
            self._drop(handle, "cancelled")
            if handle.adopted and job is not None and job.cancel is not None:
                self._call(f"{handle.title}.cancel", job.cancel)
            self._dirty = False
            self._tell_rows()

    def changed(self, topics) -> None:
        """The session's listener: a job whose kind follows a topic changed does what its kind says (rule 7)."""
        with self._timed("changed"):
            self._changed(topics)

    def _changed(self, topics) -> None:
        touched = False
        for handle in list(self._handles.values()):
            if handle.adopted or not handle.active or not handle.kind.follows(topics):
                continue
            touched = True
            kind, job = handle.kind, self._jobs[handle.id]
            if kind.on_change == "finish":
                handle.stale = True
            elif kind.on_change == "discard":
                self._drop(handle, "cancelled")
            else:
                if handle.state != "settling":
                    self._stop_runs(handle, keep=kind.settle + KEEP_AFTER_SETTLE)
                    handle.state = "settling"
                    job.shares, job.phases = {}, {}
                    job.eta.reset()
                job.settle_until = self.clock() + kind.settle
                self.alarm.at(kind.settle, self._wake)
        if touched:
            self._touch()

    def subscribe(self, listener) -> None:
        """`listener()` is told on the owner's thread that rows() changed."""
        self._listeners.append(listener)

    # the owner's thread

    def pump(self, budget: float = 0.003) -> bool:
        """Delivers what is queued, for at most `budget` seconds (one message at least); True if more is waiting
        (the owner pumps again on its next turn)."""
        start = time.perf_counter()
        with self._lock:
            self._posted = False
        if self._closed:
            return False
        self._settled()
        first = True
        while first or time.perf_counter() - start < budget:
            with self._lock:
                if not self._events:
                    break
                key = next(iter(self._events))
                message = self._events.pop(key)
            self._deliver(message)
            first = False
        while self._pieces and not self._closed and (first or time.perf_counter() - start < budget):
            name = next(iter(self._pieces))
            call, args = self._pieces.pop(name)
            self._call(name, call, *args)
            first = False
        if self._dirty:
            self._dirty = False
            self._tell_rows()
        with self._lock:
            return bool(self._events) or bool(self._pieces)

    def rows(self) -> list[dict]:
        """The bar: the jobs in hand in the order they came; fraction and left (seconds) are None when unknown."""
        now, out = self.clock(), []
        for handle in self._handles.values():
            if handle.kind is not None and not handle.kind.in_bar:
                continue
            job = self._jobs[handle.id]
            fraction = self._fraction(handle) if handle.state in ("running", "waiting") else None
            out.append(dict(id=handle.id, slot=job.slot, title=handle.title, phase=self._phase(job),
                            fraction=fraction, left=job.eta.left(now) if fraction is not None else None,
                            cancellable=(job.cancel is not None) if handle.adopted else handle.kind.cancellable,
                            state=handle.state, since=handle.since))
        return out

    def find(self, job_id: int) -> Handle | None:
        return self._handles.get(job_id)

    def stats(self) -> dict:
        """The longest call on the owner's thread since reset_stats(): (seconds, name), how many there were, and the
        longest of each name (`by_name`: name -> seconds)."""
        return {"longest_call": self._longest, "calls": self._calls, "by_name": dict(self._by_name)}

    def timed(self, name: str, function, *args):
        """A piece of the owner's own work on its thread, made of what a job gave or of a gesture on it (what the
        window draws of a result, one surface at a time), timed under `name` with the calls back: the guard of the
        window (stats) sees it as it sees a delivery. Its answer; what it raises goes on to the caller."""
        start = time.perf_counter()
        try:
            return function(*args)
        finally:
            self._note(name, time.perf_counter() - start)

    def reset_stats(self) -> None:
        self._longest, self._calls, self._by_name = (0.0, ""), 0, {}

    def close(self) -> None:
        """Every job dropped without a word, every process ended: nothing left behind."""
        with self._lock:
            self._closed = True
            self._events.clear()
        self._pieces.clear()
        for handle in list(self._handles.values()):
            handle.state = "cancelled"
        self._handles.clear()
        self._jobs.clear()
        self._slots.clear()
        self._runs.clear()
        self.runner.close()

    # inside

    def _incoming(self, message) -> None:
        """A message of a process or a thread, on the thread that read it: queued; the progress, the memory and the
        results on the way of one key keep only the last that is still waiting."""
        word, run = message[0], message[1]
        if word == "progress" or word == "rss":
            key = (word, run)
        elif word == "partial":
            key = (word, run, message[2])
        else:
            key = (word, run, next(self._serial))
        with self._lock:
            if self._closed:
                return
            self._events[key] = message
            post = not self._posted
            self._posted = True
        if post:
            self._post()

    def _wake(self) -> None:
        with self._lock:
            if self._closed or self._posted:
                return
            self._posted = True
        self._post()

    def _touch(self) -> None:
        self._dirty = True
        self._wake()

    def _deliver(self, message) -> None:
        word, run = message[0], message[1]
        found = self._runs.get(run)
        if found is None:               # a run cancelled, restarted or ended: nobody waits for it
            return
        handle, index = found
        job, name = self._jobs[handle.id], handle.kind.name
        if word in ("progress", "partial") and handle.state == "waiting":
            handle.state = "running"
            self._dirty = True
        if word == "progress":
            _word, _run, done, total, phase = message
            job.shares[index] = (done, total)
            job.phases[index] = phase
            self._feed(job)
            self._dirty = True
        elif word == "partial":
            if job.on_partial is not None:
                self._call(f"{name}.on_partial", job.on_partial, message[2], message[3])
        elif word == "rss":
            job.rss[index] = message[2]
            handle.peak_memory = max(handle.peak_memory, sum(job.rss.values()))
        elif word == "done":
            job.results[index] = message[2]
            del self._runs[run]
            if len(job.results) == job.count:
                self._finish(handle)
        elif word == "stopped":
            del self._runs[run]
        elif word == "failed":                  # the exception's type and message: a technical detail, said as such
            self._fail(handle, _("{title} stopped with an error: {error}"), message[2])
        elif word == "refused":                 # job.Refused: a sentence already in the user's words
            self._fail(handle, "{error}", message[2])
        elif word == "memory":
            used, quota = message[2], message[3]
            handle.peak_memory = max(handle.peak_memory, used)
            self._fail(handle, _("{title} needed more memory than allowed ({limit}) and was stopped."),
                       f"{used} bytes over the quota of {quota}", limit=size_text(quota))
        elif word == "ended":
            self._fail(handle, _("{title} ended unexpectedly."), f"exit code {message[2]}: {message[3]}")

    def _fraction(self, handle: Handle) -> float | None:
        """Done over total, summed over the processes; a process that has not told yet counts as the mean of the
        others. None while nothing is known or the total is not."""
        job = self._jobs[handle.id]
        if not job.shares:
            return None
        done = sum(d for d, _t in job.shares.values())
        total = sum(t for _d, t in job.shares.values())
        if total <= 0:
            return None
        total *= max(1, job.count) / len(job.shares)
        return max(0.0, min(1.0, done / total))

    def _feed(self, job: _Job) -> None:
        """The estimate of the time left fed with the units of every process, once every one has told its share:
        before, the mean that stands for the silent ones would make the pace jump when they speak."""
        if job.shares and len(job.shares) >= job.count:
            done = sum(d for d, _t in job.shares.values())
            total = sum(t for _d, t in job.shares.values())
            if total > 0:
                job.eta.feed(self.clock(), done, total)

    @staticmethod
    def _phase(job: _Job) -> str:
        """The phase the bar says (a msgid): that of the process furthest from its end, which says what is left
        (each process tells its own, and the last one to speak would make the bar flicker between them)."""
        if not job.phases:
            return ""

        def behind(index):
            done, total = job.shares.get(index, (0.0, 0.0))
            return (done / total if total > 0 else 0.0, index)
        return job.phases[min(job.phases, key=behind)]

    def _finish(self, handle: Handle) -> None:
        job = self._jobs[handle.id]
        result = job.results[0] if job.count == 1 else [job.results[i] for i in range(job.count)]
        self._drop(handle, "done", stop=False)
        if handle.kind.where == "process" and job.count > 1:
            self.runner.warm_again(handle.kind.family, handle.kind.keep_warm)
        if job.on_done is not None:
            self._call(f"{handle.kind.name}.on_done", job.on_done, result, handle.stale)

    def _fail(self, handle: Handle, sentence: str, detail: str, error: str | None = None, **values) -> None:
        """A job that failed: the other processes stopped, the detail in the log, the sentence to its owner and to
        the status bar (rule 9). What enters the sentence as {error}: `error`, already translated, or else the
        detail when it is an exception's type and message (a technical detail, said as one); never an English
        sentence written here."""
        if not handle.active:
            return
        job = self._jobs[handle.id]
        self._drop(handle, "failed")
        handle.error = detail
        log.complain(f"The job {handle.kind.name} failed", RuntimeError(detail))
        text = sentence.format(title=_(handle.title), error=detail if error is None else error, **values)
        if job.on_failed is not None:
            self._call(f"{handle.kind.name}.on_failed", job.on_failed, handle.kind, text)
        if self.tell is not None:
            self._call("tell", self.tell, text)

    def _stop_runs(self, handle: Handle, keep: float = 0.0) -> None:
        job = self._jobs[handle.id]
        for run in job.runs:
            if self._runs.pop(run, None) is not None:
                self.runner.stop(run, keep)
        job.runs = []

    def _drop(self, handle: Handle, state: str, stop: bool = True) -> None:
        """The job out of the center: its processes stopped (the ones still on it), its row gone."""
        if not handle.adopted and stop:
            self._stop_runs(handle)
        else:
            for run in self._jobs[handle.id].runs:
                self._runs.pop(run, None)
        handle.state = state
        self._handles.pop(handle.id, None)
        job = self._jobs.pop(handle.id, None)
        if job is not None and self._slots.get(job.slot) is handle:
            del self._slots[job.slot]
        self._dirty = True

    def _settled(self) -> None:
        """The restarts whose quiet has come: a new request from build(), the processes again. A warm job (one
        process kept warm) whose process is still at work (its run of before stopping, or another kind at home in
        it: the layout and the checks) waits for it, instead of starting a cold one without what it kept."""
        now = self.clock()
        for handle in [h for h in self._handles.values() if h.state == "settling"]:
            job = self._jobs[handle.id]
            if now < job.settle_until:
                continue
            kind = handle.kind
            if kind.where == "process" and kind.processes == 1 and kind.keep_warm > 0 and self.runner.busy(kind):
                job.settle_until = now + WARM_WAIT
                self.alarm.at(WARM_WAIT, self._wake)
                continue
            with self._timed(f"restart:{handle.kind.name}"):
                if job.build is not None:
                    ok, request = self._call(f"{handle.kind.name}.build", job.build)
                    if not ok:                  # `request` is the exception, said in the log by _call
                        self._fail(handle, _("{title} could not start: {error}"),
                                   f"build() raised {type(request).__name__}: {request}",
                                   error=_("the request could not be made"))
                        continue
                    job.request = request
                try:
                    self._launch(handle)
                except (pickle.PicklingError, TypeError, AttributeError) as error:
                    self._fail(handle, _("{title} could not start: {error}"), f"{type(error).__name__}: {error}")
                self._dirty = True

    def _adopted_progress(self, handle: Handle, done, total, phase) -> None:
        if not handle.active:
            return
        job = self._jobs[handle.id]
        job.shares, job.phases = {0: (float(done), float(total))}, {0: phase}
        self._feed(job)
        self._touch()

    def _adopted_end(self, handle: Handle) -> None:
        if handle.active:
            self._drop(handle, "done")
            self._touch()

    def _tell_rows(self) -> None:
        for listener in list(self._listeners):
            self._call("rows", listener)

    @contextlib.contextmanager
    def _timed(self, name: str):
        """What the center itself does on the owner's thread (submit, cancel, changed, a restart), timed as the
        calls back are: the guard sees a slow submit as it sees a slow delivery."""
        start = time.perf_counter()
        try:
            yield
        finally:
            self._note(name, time.perf_counter() - start)

    def _note(self, name: str, spent: float) -> None:
        self._calls += 1
        if spent > self._by_name.get(name, -1.0):
            self._by_name[name] = spent
        if spent > self._longest[0]:
            self._longest = (spent, name)

    def _call(self, name: str, function, *args):
        """A call back on the owner's thread, timed (stats); one that raises is said in the log and the others go
        on. (True, its answer) or (False, the exception)."""
        start = time.perf_counter()
        try:
            return True, function(*args)
        except Exception as error:      # the owner's code: said, and the jobs go on
            log.complain(f"A job's answer failed ({name})", error)
            return False, error
        finally:
            self._note(name, time.perf_counter() - start)
