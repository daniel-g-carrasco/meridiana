"""What a job is (study 48, chapter 3): its kind (`Kind`), the job in hand (`Handle`), what its function receives
(`Context`) and how the processes of one job share its parts (`mine`)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from meridiana.core.compute import resources

GIB = resources.GIB
WHERE = ("process", "thread")
ON_CHANGE = ("restart", "discard", "finish")
PROGRESS_EVERY = 0.05           # seconds: a job that tells its progress more often is told on at this pace


class Refused(Exception):
    """A job that cannot be done for a reason the user can act on, raised by the job's function with the sentence
    already in the user's words (`_()`): the bar and the owner get that sentence alone, without the type of the error
    (rule 9: one sentence, never in silence; the log still has it)."""


@dataclass(frozen=True)
class Kind:
    """A kind of job. `run` is "package.module:function", imported where the job runs: run(request, ctx) -> result,
    a module of meridiana.app or meridiana.core (the worker has no Qt). The defaults are those of a computation."""
    name: str                       # the default slot, the name in the log and in the guard's report
    title: str                      # msgid of what the bar says; the bar translates it
    run: str
    where: str = "process"          # "process" (what computes) or "thread" (what waits: the network, the disk)
    processes: int = 1              # at most; fewer when the machine has not the processors or the memory
    memory: int = 2 * GIB           # ceiling of the whole job: each process has memory // processes, and stops over it
    keep_warm: float = 0.0          # seconds an idle process waits for the next job of this kind (ctx.kept lives on)
    low_priority: bool = True       # the processes below the window's
    on_change: str = "restart"      # a change of `topics`: "restart", "discard" or "finish"
    topics: tuple[str, ...] = ()    # the session's topics its result is made of ("layout" takes every "layout:<id>")
    settle: float = 1.0             # seconds of quiet after the last change before the restart
    cancellable: bool = True
    # False: a moment of a job that has its row already (the year's files read, app/year_read.py), not a row of its
    # own in the bar (Center.rows): the bar's QML is not rebuilt for a read of milliseconds
    in_bar: bool = True
    # the name of another kind whose processes run this one too, with their ctx.kept: what that kind keeps serves
    # this one without travelling (the checks in the layout's process, which holds the layouts); "" for its own
    home: str = ""

    @property
    def family(self) -> str:
        """The name of the processes this kind runs in, and of their ctx.kept."""
        return self.home or self.name

    def __post_init__(self):
        if self.where not in WHERE:
            raise ValueError(f"where: {self.where!r}, not one of {WHERE}")
        if self.on_change not in ON_CHANGE:
            raise ValueError(f"on_change: {self.on_change!r}, not one of {ON_CHANGE}")
        if ":" not in self.run:
            raise ValueError(f"run: {self.run!r} is not «package.module:function»")

    def follows(self, topics) -> bool:
        """Whether a change of these session topics touches this kind's result; "file" (another project) touches
        every kind that follows anything."""
        if not self.topics:
            return False
        for topic in topics:
            if topic == "file":
                return True
            for mine_ in self.topics:
                if topic == mine_ or topic.startswith(mine_ + ":"):
                    return True
        return False


def resolve(run: str):
    """The function named by Kind.run, imported: only from meridiana.app or meridiana.core (a job never brings the
    window's modules, nor Qt, into a worker)."""
    import pkgutil
    module = run.partition(":")[0]
    if not module.startswith(("meridiana.app.", "meridiana.core.")):
        raise ValueError(f"a job's function lives in meridiana.app or meridiana.core, not in {module}")
    return pkgutil.resolve_name(run)


class Context:
    """What the job's function receives, in its process or in its thread. `share` is (index, count): this process
    among those of the job; `kept` lives as long as the process (Kind.keep_warm)."""

    def __init__(self, run: int, share: tuple[int, int], kept: dict, send, stop=None, clock=time.monotonic):
        self.run, self.share, self.kept = run, tuple(share), kept
        self._send, self._stop, self._clock = send, stop, clock
        self._told = 0.0
        self._waiting = None            # the last progress not yet sent (PROGRESS_EVERY)
        self._phase = None              # the phase of the last progress sent

    def progress(self, done: float, total: float, phase: str = "") -> None:
        """Units the job chooses; the total may grow. `phase` is a msgid, translated by the bar."""
        message = ("progress", self.run, float(done), float(total), phase)
        now = self._clock()
        # a new phase goes at once: held back, it was replaced by the next progress and never seen (the IFC's
        # «reading again» after a crash of the reader)
        if now - self._told >= PROGRESS_EVERY or phase != self._phase:
            self._told, self._waiting, self._phase = now, None, phase
            self._send(message)
        else:
            self._waiting = message

    def partial(self, key: str, data) -> None:
        """A result on the way (picklable, small: the window takes it in pieces of 3 ms)."""
        self._send(("partial", self.run, key, data))

    def checkpoint(self) -> None:
        """resources.Stopped once Cancel was asked: the job ends there, what it finished stays where it put it."""
        if self._stop is not None:
            if self._stop.is_set():
                raise resources.Stopped()
        else:
            resources.checkpoint()

    def flush(self) -> None:
        """The last progress held back, sent (before the result)."""
        if self._waiting is not None:
            message, self._waiting = self._waiting, None
            self._send(message)


def mine(parts: list, share: tuple[int, int], weight=lambda part: 1.0) -> list:
    """The parts of this process: sorted by weight, the lightest first, dealt one each in turn. The same order in
    every process, so that together they do every part once and none twice."""
    index, count = share
    order = sorted(range(len(parts)), key=lambda i: (weight(parts[i]), i))
    return [parts[i] for k, i in enumerate(order) if k % max(1, count) == index]


@dataclass(eq=False)
class Handle:
    """A job in hand. `state`: "waiting", "running", "settling", "done", "failed", "cancelled". The progress of an
    adopted job (one that runs elsewhere and only shows in the bar, the year today) is told with `progress` and
    `end`; Cancel calls the function given to Center.adopt."""
    id: int
    kind: Kind | None
    title: str
    center: object = field(repr=False, default=None)
    state: str = "waiting"
    peak_memory: int = 0                # the most the processes held together, bytes
    since: float = 0.0
    adopted: bool = False
    stale: bool = False                 # the project changed after the job's photo (on_change "finish")
    error: str = ""

    def progress(self, done, total, phase="") -> None:
        """Adopted jobs only."""
        self.center._adopted_progress(self, done, total, phase)

    def end(self) -> None:
        """Adopted jobs only: the job is over, its row goes."""
        self.center._adopted_end(self)

    def cancel(self) -> None:
        self.center.cancel(self)

    @property
    def active(self) -> bool:
        return self.state in ("waiting", "running", "settling")
