"""What the machine can give Meridiana right now, without psutil: the memory of the system and how much of it is
free, whether the system says it is short of memory, and from those a budget in bytes for what the program keeps in
memory to save time, and the number of processes a divisible computation may use (R435, Daniel 06/11/2026: «if I
have 32 GB and no other process, I want to use the rest; with other processes it shrinks; with 8 GB, what there is»).

Windows through kernel32 (GlobalMemoryStatusEx, the low-memory notification), Linux through /proc (meminfo and the
pressure stall information of the kernel); elsewhere a cautious guess. The budget is read again each time it is
asked: a `Budget` keeps the preference (automatic, or a fixed share set by the designer) and answers with today's
numbers."""

from __future__ import annotations

import os
import sys

GIB = 1 << 30
MIB = 1 << 20
RESERVE = 2 * GIB            # left to the system and the other programs whatever the machine
WORKER_BYTES = 350 * MIB     # what a process of the electrical network takes (interpreter, NumPy, the year): guess
MIN_WEIGHT = 2000            # modules x chunks of hours under which the processes cost more than they give


def system_memory() -> tuple[int, int] | None:
    """(total, available) in bytes, or None where it cannot be read."""
    if sys.platform == "win32":
        return _windows_memory()
    try:
        values = {}
        with open("/proc/meminfo", encoding="ascii") as f:
            for line in f:
                name, _sep, rest = line.partition(":")
                values[name] = int(rest.split()[0]) * 1024
        return values["MemTotal"], values.get("MemAvailable", values.get("MemFree", 0))
    except (OSError, KeyError, ValueError, IndexError):
        return None


def _windows_memory():
    import ctypes
    from ctypes import wintypes

    class Status(ctypes.Structure):
        _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_uint64), ("ullAvailPhys", ctypes.c_uint64),
                    ("ullTotalPageFile", ctypes.c_uint64), ("ullAvailPageFile", ctypes.c_uint64),
                    ("ullTotalVirtual", ctypes.c_uint64), ("ullAvailVirtual", ctypes.c_uint64),
                    ("ullAvailExtendedVirtual", ctypes.c_uint64)]
    status = Status()
    status.dwLength = ctypes.sizeof(Status)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    if not kernel.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None
    return int(status.ullTotalPhys), int(status.ullAvailPhys)


_low_memory_handle = None


def memory_is_short() -> bool:
    """Whether the system says it is short of memory: Windows' low-memory resource notification, Linux' memory
    pressure (`some avg10` above 10 % in /proc/pressure/memory: a tenth of the last ten seconds spent waiting for
    memory). False where neither can be read."""
    global _low_memory_handle
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            if _low_memory_handle is None:
                kernel.CreateMemoryResourceNotification.restype = wintypes.HANDLE
                _low_memory_handle = kernel.CreateMemoryResourceNotification(0)     # LowMemoryResourceNotification
            if not _low_memory_handle:
                return False
            state = wintypes.BOOL()
            kernel.QueryMemoryResourceNotification.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL))
            if not kernel.QueryMemoryResourceNotification(_low_memory_handle, ctypes.byref(state)):
                return False
            return bool(state.value)
        except (OSError, AttributeError):
            return False
    try:
        with open("/proc/pressure/memory", encoding="ascii") as f:
            for line in f:
                if line.startswith("some"):
                    fields = dict(part.split("=") for part in line.split()[1:])
                    return float(fields.get("avg10", 0)) > 10
    except (OSError, ValueError):
        pass
    return False


def cpu_count() -> int:
    try:
        return len(os.sched_getaffinity(0))
    except AttributeError:
        return os.cpu_count() or 1


MODES = ("save", "auto", "all")      # R548: Impostazioni > Prestazioni, «Risparmia», «Automatico», «Usa tutto»
SAVE_SHARE = 0.15                   # «save»: at most this share of the machine, whatever is free
ALL_RESERVE = 1 * GIB               # «all»: what is left to the system
PRELOAD_MIN = 3 * GIB // 2          # under this budget nothing is prepared ahead (R548): a PC short of memory
# what each kind of cache may take of the budget; «all» gives the computation's caches more (R548: the shading of
# the year and the parts of the network kept for the variants and the undo)
CACHE_SHARES = {"shading": 0.25, "tiles": 0.1, "years": 0.2, "network": 0.1, "weather": 0.02}
CACHE_SHARES_ALL = {**CACHE_SHARES, "shading": 0.35, "network": 0.2}


class Budget:
    """The memory Meridiana may spend on what it keeps to save time, after the designer's choice (`mode`, R548):
    «save», at most SAVE_SHARE of the machine and nothing prepared ahead; «auto», what is available now less a
    reserve for the system (RESERVE); «all», the same with ALL_RESERVE only. `share` (MERIDIANA_MEMORY_SHARE, the
    trials) fixes a share of the machine instead. `bytes()` is asked again whenever a cache decides: it follows the
    machine, and drops to a quarter while the system says it is short of memory."""

    def __init__(self, share: float | None = None, mode: str = "auto"):
        self.share = share
        self.mode = mode if mode in MODES else "auto"

    def bytes(self) -> int:
        memory = system_memory()
        if memory is None:
            return 1 * GIB
        total, available = memory
        if self.share is not None:
            allowed = int(total * max(0.05, min(0.9, self.share)))
        elif self.mode == "all":
            allowed = max(512 * MIB, available - ALL_RESERVE)
        else:
            allowed = max(512 * MIB, available - RESERVE)
            if self.mode == "save":
                allowed = min(allowed, max(256 * MIB, int(total * SAVE_SHARE)))
        if memory_is_short():
            allowed //= 4
        return allowed


_SHARE: float | None = None
_MODE = "auto"


def configure(mode: str | float | None = "auto") -> None:
    """The designer's choice (config.memory_mode, R548): «save», «auto» or «all». MERIDIANA_MEMORY_MODE in the
    environment wins, and is set for the processes this one starts (the year, the report); MERIDIANA_MEMORY_SHARE
    fixes a share of the machine (the trials). A number (the share of config.memory_share before R548) is taken as
    the trials' share."""
    global _SHARE, _MODE
    share = None
    if isinstance(mode, (int, float)) and not isinstance(mode, bool):
        share, mode = (float(mode) or None), "auto"
    forced = os.environ.get("MERIDIANA_MEMORY_SHARE")
    if forced:
        try:
            share = float(forced) or None
        except ValueError:
            pass
    _SHARE = share
    mode = os.environ.get("MERIDIANA_MEMORY_MODE_FORCED") or mode
    _MODE = mode if mode in MODES else "auto"
    os.environ["MERIDIANA_MEMORY_MODE"] = _MODE


def mode() -> str:
    return _MODE


def budget() -> Budget:
    return Budget(_SHARE, _MODE)


def cache_limit(kind: str) -> int:
    """The bytes one kind of cache may hold now: a share of the budget (`CACHE_SHARES`), never under 32 MB."""
    shares = CACHE_SHARES_ALL if _MODE == "all" else CACHE_SHARES
    return max(32 * MIB, int(budget().bytes() * shares.get(kind, 0.1)))


def preload() -> bool:
    """Whether what the designer will likely ask next may be prepared ahead, in background (R548: the report's
    preview after the year, the true geometry of the project's IFC model): not with «save», not under PRELOAD_MIN of
    budget, not while the system is short of memory, not on battery unless «all» was chosen. MERIDIANA_PRELOAD=0 or
    1 in the environment decides (the trials)."""
    forced = os.environ.get("MERIDIANA_PRELOAD")
    if forced in ("0", "1"):
        return forced == "1"
    if _MODE == "save":
        return False
    if _MODE != "all" and on_battery():
        return False
    return budget().bytes() >= PRELOAD_MIN


def in_use() -> dict:
    """What Meridiana holds in memory now, for Impostazioni > Prestazioni (R548): this process (`window`) and the
    processes it started (`helpers`: the year's, the report's, the IFC's), the machine's total and available memory
    and today's budget, in bytes; 0 where they cannot be read."""
    from . import procmem
    own = procmem.rss() or 0
    pid = os.getpid()
    helpers = sum(procmem.rss(c) or 0 for c in procmem.children(pid))
    total, available = system_memory() or (0, 0)
    return {"window": own, "helpers": helpers, "total": total, "available": available, "budget": budget().bytes(),
            "mode": _MODE}


# the computation's processes started before configure() take the designer's choice from the environment
if os.environ.get("MERIDIANA_MEMORY_MODE") in MODES:
    _MODE = os.environ["MERIDIANA_MEMORY_MODE"]


def fingerprint(*things) -> bytes:
    """A digest of everything in `things`, followed into dataclasses, objects, containers and NumPy arrays by
    content (R478: the caches of the computation kept from one year to the next answer for what their result was
    made of, not for an object or a moment). Two equal contents give the same digest; a content written in another
    order (a dict filled otherwise) may give another, which only costs a computation again."""
    import hashlib
    h = hashlib.blake2b(digest_size=20)
    _feed(h, things, set())
    return h.digest()


def _feed(h, x, path: set) -> None:
    import dataclasses
    kind = type(x)
    h.update(kind.__qualname__.encode())
    if x is None or kind in (bool, int, float, complex, str):
        h.update(repr(x).encode())
        h.update(b"\x00")
        return
    if isinstance(x, (bytes, bytearray, memoryview)):
        h.update(len(x).to_bytes(8, "little"))
        h.update(x)
        return
    try:
        import numpy as np
    except ImportError:                     # pragma: no cover (NumPy is always there with the energy)
        np = None
    if np is not None and isinstance(x, np.ndarray):
        h.update(str(x.dtype).encode())
        h.update(repr(x.shape).encode())
        if x.dtype == object:
            for item in x.ravel():
                _feed(h, item, path)
        else:
            h.update(np.ascontiguousarray(x).data)
        return
    if np is not None and isinstance(x, np.generic):
        h.update(repr(x.item()).encode())
        return
    if id(x) in path:                       # a cycle: said, not followed
        h.update(b"<cycle>")
        return
    path.add(id(x))
    try:
        if isinstance(x, (list, tuple)):
            h.update(len(x).to_bytes(8, "little"))
            for item in x:
                _feed(h, item, path)
        elif isinstance(x, dict):
            h.update(len(x).to_bytes(8, "little"))
            for k, v in x.items():
                _feed(h, k, path)
                _feed(h, v, path)
        elif isinstance(x, (set, frozenset)):
            h.update(len(x).to_bytes(8, "little"))
            for digest in sorted(fingerprint(item) for item in x):
                h.update(digest)
        elif dataclasses.is_dataclass(x) and not isinstance(x, type):
            for f in dataclasses.fields(x):
                h.update(f.name.encode())
                _feed(h, getattr(x, f.name, None), path)
        elif hasattr(x, "__dict__") and not callable(x):
            _feed(h, vars(x), path)
            for name in getattr(kind, "__slots__", ()):
                _feed(h, getattr(x, name, None), path)
        elif hasattr(kind, "__slots__"):
            for name in kind.__slots__:
                _feed(h, getattr(x, name, None), path)
        elif callable(x):
            h.update(getattr(x, "__module__", "").encode() + getattr(x, "__qualname__", repr(kind)).encode())
        else:
            import pickle
            h.update(pickle.dumps(x, protocol=5))
    finally:
        path.discard(id(x))


# R478: a computation asked to stop by the process that waits for it (shell_compute --serve): its long loops look at
# this between their pieces, and stop there; what they finished stays in the caches.
import threading as _threading

STOP = _threading.Event()


class Stopped(Exception):
    """The computation in hand was asked to stop (STOP): nothing to say, the caller asked for it."""


def checkpoint() -> None:
    if STOP.is_set():
        raise Stopped()


def contain_children() -> bool:
    """The processes this process starts end with it, whatever way it ends (R478: no orphans of the computation's
    pool). Windows: a job object that kills its processes when its last handle closes, with this process in it
    (its children enter it by themselves); Linux: this process dies with its parent (PR_SET_PDEATHSIG), and the pool's
    workers do the same with theirs (`_import_energy`). Whether it took."""
    global _JOB
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.CreateJobObjectW.restype = wintypes.HANDLE
            kernel.GetCurrentProcess.restype = wintypes.HANDLE
            kernel.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
            kernel.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
            job = kernel.CreateJobObjectW(None, None)
            if not job:
                return False

            class Basic(ctypes.Structure):
                _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                            ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                            ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                            ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                            ("SchedulingClass", wintypes.DWORD)]

            class Counters(ctypes.Structure):
                _fields_ = [(name, ctypes.c_uint64) for name in ("r", "w", "o", "rb", "wb", "ob")]

            class Extended(ctypes.Structure):
                _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", Counters),
                            ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                            ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]
            info = Extended()
            info.BasicLimitInformation.LimitFlags = 0x2000              # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not kernel.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
                return False                                            # 9: JobObjectExtendedLimitInformation
            if not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
                return False
            _JOB = job                                                  # kept open until this process ends
            return True
        return _die_with_parent()
    except (OSError, AttributeError, ValueError):
        return False


_JOB = None


def _die_with_parent() -> bool:
    """Linux: SIGKILL to this process when its parent ends (prctl PR_SET_PDEATHSIG); False elsewhere."""
    if not sys.platform.startswith("linux"):
        return False
    import ctypes
    import signal
    libc = ctypes.CDLL(None, use_errno=True)
    parent = os.getppid()
    if libc.prctl(1, int(signal.SIGKILL), 0, 0, 0) != 0:
        return False
    if os.getppid() != parent:             # the parent had already gone before the call
        os._exit(1)
    return True


class Cache:
    """A cache with a limit in bytes read again at each entry (`limit`, a function: the budget follows the machine)
    and an eviction that weighs how recently an entry was used against what it cost to make: when room is needed,
    the entry with the lowest `cost x 0.5 ^ (uses since its last use / HALF_LIFE)` goes first, so a result that
    took a minute survives many cheap ones used after it. `size_of(value)` gives an entry's bytes, `cost` the
    seconds it took. Thread-safe."""

    HALF_LIFE = 8

    def __init__(self, limit, size_of):
        import threading
        self.limit, self.size_of = limit, size_of
        self._entries: dict = {}            # key -> [value, bytes, cost, last use]
        self._clock = 0
        self._lock = threading.Lock()
        self.hits = self.misses = 0         # what was found and what was not, since the process started (R478)
        self.pinned = set()                 # keys that leave last (the tiles on show, R516)

    def get(self, key, default=None):
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self.misses += 1
                return default
            self.hits += 1
            self._clock += 1
            entry[3] = self._clock
            return entry[0]

    def put(self, key, value, cost: float = 1.0) -> bool:
        """Keeps `value` if it fits the limit alone; False when it does not."""
        size = self.size_of(value)
        limit = self.limit()
        if size > limit:
            return False
        with self._lock:
            self._clock += 1
            self._entries[key] = [value, size, max(cost, 1e-3), self._clock]
            self._trim(limit)
        return True

    def _trim(self, limit: int) -> None:
        while sum(e[1] for e in self._entries.values()) > limit and len(self._entries) > 1:
            pinned = self.pinned
            free = [k for k in self._entries if k not in pinned] or list(self._entries)
            worst = min(free, key=lambda k: self._entries[k][2]
                        * 0.5 ** ((self._clock - self._entries[k][3]) / self.HALF_LIFE))
            del self._entries[worst]

    def clear(self) -> None:
        """Everything forgotten (the trials that count what is computed)."""
        with self._lock:
            self._entries.clear()

    def trim(self) -> None:
        """Today's limit applied: called when the machine got short of memory, or the preference changed."""
        with self._lock:
            self._trim(self.limit())

    def __len__(self):
        return len(self._entries)

    def __contains__(self, key):
        """Whether `key` is kept, without counting it as a use."""
        return key in self._entries

    def bytes(self) -> int:
        return sum(e[1] for e in self._entries.values())


def workers_for(tasks: int, weight: int = MIN_WEIGHT, per_worker: int = WORKER_BYTES) -> int:
    """How many processes a computation of `tasks` independent pieces may use now: one when the work is small
    (`weight`, modules times chunks of hours, under MIN_WEIGHT: starting a process costs a second or two), else the
    processors less one for the window, no more than the memory allows (`per_worker` each, within the budget), no
    more than the pieces. MERIDIANA_WORKERS in the environment fixes it (0 or 1: no processes)."""
    forced = os.environ.get("MERIDIANA_WORKERS")
    if forced:
        try:
            return max(1, min(int(forced), tasks))
        except ValueError:
            pass
    if tasks < 2 or weight < MIN_WEIGHT:
        return 1
    by_cpu = max(1, cpu_count() - 1)
    by_memory = max(1, budget().bytes() // per_worker)
    return int(max(1, min(by_cpu, by_memory, tasks)))


_POOL = None
_POOL_LOW = False
_LOW = False                    # the year in hand is one in the background (R478, `background`)


def pool(workers: int):
    """A pool of `workers` processes for the divisible computations, kept from one to the next (the processes
    import NumPy and the energy modules once); made again when a different size or priority is asked or a worker
    died. `warm` starts it ahead, while something else runs."""
    global _POOL, _POOL_LOW
    from concurrent.futures import ProcessPoolExecutor
    if _POOL is not None and (_POOL._max_workers != workers or getattr(_POOL, "_broken", False)
                              or _POOL_LOW != _LOW):
        _POOL.shutdown(wait=False, cancel_futures=True)
        _POOL = None
    if _POOL is None:
        # one thread of BLAS in each worker: with its own threads for every processor in every process, the
        # workers trod on one another (R435: the network of 778 modules on 11 processes took 45 s against 61
        # in one, before this; the chunks of the network are small arrays, BLAS threads give them nothing)
        for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
            os.environ.setdefault(name, "1")
        # spawned on every system, so that each worker is a child of this process (Linux' default, forkserver since
        # Python 3.14, made them children of a server that outlived its process: two trees of 12 orphans for an
        # hour and a half after a run of the tests, 06/11/2026); each worker watches this process and ends with it
        import atexit
        import multiprocessing
        _POOL = ProcessPoolExecutor(workers, mp_context=multiprocessing.get_context("spawn"),
                                    initializer=_import_energy, initargs=(_LOW, os.getpid()))
        _POOL_LOW = _LOW
        if not _ATEXIT:
            atexit.register(shutdown)
            _ATEXIT.append(True)
    return _POOL


_ATEXIT: list = []


def watch_parent(pid: int) -> bool:
    """This process ends (os._exit) as soon as process `pid` has ended, however it ended (R478: a pool's worker,
    the process of the computation, when the window or the test that made them is killed or crashes): a thread
    that waits on the process (Windows: its handle; Linux: a pidfd; elsewhere: asking every second). Whether the
    watch started; a process already gone ends this one at once."""
    import threading

    def gone():
        os._exit(1)
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.OpenProcess.restype = wintypes.HANDLE
            kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
            handle = kernel.OpenProcess(0x00100000, False, int(pid))         # SYNCHRONIZE
            if not handle:
                gone()

            def wait():
                kernel.WaitForSingleObject(handle, 0xFFFFFFFF)
                gone()
        elif hasattr(os, "pidfd_open"):
            try:
                fd = os.pidfd_open(int(pid))
            except ProcessLookupError:
                gone()

            def wait():
                import select
                select.select([fd], [], [])
                gone()
        else:
            def wait():
                import time
                while True:
                    try:
                        os.kill(int(pid), 0)
                    except ProcessLookupError:
                        gone()
                    except PermissionError:
                        pass
                    time.sleep(1.0)
        threading.Thread(target=wait, name="meridiana-watch-parent", daemon=True).start()
        return True
    except (OSError, AttributeError, ValueError):
        return False


def background(low: bool, workers: int | None) -> callable:
    """The priority and the processes of one year in the process kept for the session (R478): a year in the
    background lowers its own thread and makes its pool low and small (`workers`); the next year, in the
    foreground, gets a pool of its own size at normal priority. Returns what puts things back."""
    global _LOW
    saved = os.environ.get("MERIDIANA_WORKERS")
    _LOW = bool(low)
    if low:
        _lower_thread()
        if workers:
            os.environ["MERIDIANA_WORKERS"] = str(max(1, int(workers)))

    def restore():
        global _LOW
        _LOW = False
        if saved is None:
            os.environ.pop("MERIDIANA_WORKERS", None)
        else:
            os.environ["MERIDIANA_WORKERS"] = saved
    return restore


def _lower_thread() -> bool:
    """The calling thread below the others: Windows THREAD_PRIORITY_LOWEST (in a process of normal priority, as
    a process below normal), Linux nice 10 for this thread alone (a thread cannot be raised again without
    privileges: the year's thread is a new one each time)."""
    try:
        if sys.platform == "win32":
            import ctypes
            kernel = ctypes.windll.kernel32
            return bool(kernel.SetThreadPriority(kernel.GetCurrentThread(), -2))
        import threading
        tid = threading.get_native_id()
        os.setpriority(os.PRIO_PROCESS, tid, min(19, os.getpriority(os.PRIO_PROCESS, tid) + 10))
        return True
    except (OSError, AttributeError):
        return False


def _import_energy(low: bool = False, creator: int | None = None):
    # a worker of the pool does not outlive the process that made it (R478), whatever way that one ends
    _die_with_parent()
    if creator:
        watch_parent(creator)
    if low:
        lower_priority()
    from .energy import electrical_network  # noqa: F401 (the modules a chunk of the network needs, imported once)


def _ready():
    return True


def warm(tasks: int = 1 << 30, weight: int = 1 << 30) -> list:
    """Start the pool now (its workers import what they need) for a computation that comes later: the window's
    worker calls it before the layout and the first pass, so that the network finds the processes ready."""
    workers = workers_for(tasks, weight)
    if workers > 1:
        p = pool(workers)
        return [p.submit(_ready) for _ in range(workers)]
    return []


def shutdown() -> None:
    global _POOL
    if _POOL is not None:
        _POOL.shutdown(wait=False, cancel_futures=True)
        _POOL = None


def on_battery() -> bool:
    """Whether the machine runs on its battery now (R461: the year in the background more prudent): Windows
    GetSystemPowerStatus, Linux /sys/class/power_supply; False when it cannot be told (a desktop)."""
    if sys.platform == "win32":
        import ctypes

        class Status(ctypes.Structure):
            _fields_ = [("ac", ctypes.c_ubyte), ("flag", ctypes.c_ubyte), ("percent", ctypes.c_ubyte),
                        ("saver", ctypes.c_ubyte), ("life", ctypes.c_ulong), ("full", ctypes.c_ulong)]
        status = Status()
        try:
            if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
                return False
        except (OSError, AttributeError):
            return False
        return status.ac == 0                       # 0 offline, 1 online, 255 unknown
    from pathlib import Path
    supplies = Path("/sys/class/power_supply")
    try:
        mains = [p for p in supplies.iterdir() if (p / "type").read_text().strip() == "Mains"]
        return bool(mains) and not any((p / "online").read_text().strip() == "1" for p in mains)
    except OSError:
        return False


def _set_priority_class(flag: int) -> bool:
    """The priority class of this process on Windows, with the types of a 64-bit handle (without them
    SetPriorityClass fails and says False). Whether it took."""
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.SetPriorityClass.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    return bool(kernel.SetPriorityClass(kernel.GetCurrentProcess(), flag))


def raise_priority() -> bool:
    """This process a little above the others (r24: the reading of a large IFC model, which the designer waits for,
    shared the processors with the year the project was computing and took twice as long): Windows
    ABOVE_NORMAL_PRIORITY_CLASS, which the processes it starts do NOT inherit (each one asks for itself). Elsewhere
    nothing (a raise needs the system's leave). Whether it took."""
    try:
        if sys.platform == "win32":
            return _set_priority_class(0x00008000)
    except (OSError, AttributeError):
        pass
    return False


def lower_priority() -> bool:
    """This process, and the processes it starts after, below the others (R461: the year in the background leaves
    the window and the other programs fluid): Windows BELOW_NORMAL_PRIORITY_CLASS, inherited by the children; nice
    10 elsewhere. Whether it took (r24: on Windows it never did, the call had no types for the handle)."""
    try:
        if sys.platform == "win32":
            return _set_priority_class(0x00004000)
        os.nice(10)
        return True
    except (OSError, AttributeError):
        return False

