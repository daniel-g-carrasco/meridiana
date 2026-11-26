"""The process of a job (study 48, chapter 3): started by the runner as `python -m meridiana.app.work.worker --parent
<pid> [--low]`, it says `ready`, then takes one job at a time from its pipe and answers with the job's progress, its
results on the way and its end (wire.py says the messages). It watches its own memory every WATCH_S seconds and ends
past its quota, saying so first; it ends with the window (resources.watch_parent), and the processes it starts end
with it (resources.contain_children). After a job it waits for the next: a kind that keeps it warm finds its `kept`."""

from __future__ import annotations

import os
import pickle
import sys
import threading
import time
import traceback

WATCH_S = 1.0                   # how often the process looks at its memory
MEMORY_EXIT = 3                 # the exit code past the quota


def _own_pipes() -> tuple[int, int]:
    """The window's commands and this process's messages on descriptors of its own; the null device in place of the
    standard input, the standard error in place of the standard output (what the code prints goes to the log, never
    into the messages). On Windows the process's standard handles too: the processes this one starts get a copy of
    them even when they inherit nothing else, and the year's process stood still for hours while its pool's workers
    shared the commands' pipe (shell_compute._own_stdin, R478 r20). The private descriptors are not inherited
    (PEP 446)."""
    commands = os.dup(0)
    messages = os.dup(1)
    null = os.open(os.devnull, os.O_RDONLY)
    os.dup2(null, 0)
    os.close(null)
    os.dup2(2, 1)
    if sys.platform == "win32":
        import ctypes
        import msvcrt
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.SetStdHandle.argtypes = (ctypes.c_uint32, ctypes.c_void_p)
        kernel.SetStdHandle(0xFFFFFFF6, msvcrt.get_osfhandle(0))       # STD_INPUT_HANDLE (-10)
        kernel.SetStdHandle(0xFFFFFFF5, msvcrt.get_osfhandle(1))       # STD_OUTPUT_HANDLE (-11): the standard error
    return commands, messages


def _reader(fd: int):
    """os.read for wire.frames. On Windows a read of nothing is not taken for the end (shell_compute.commands: in r19
    the pipe gave empty reads while the window was there); the end there is `quit`, or the window gone
    (watch_parent)."""
    def read(n: int) -> bytes:
        while True:
            chunk = os.read(fd, n)
            if chunk or sys.platform != "win32":
                return chunk
            time.sleep(0.05)
    return read


def main(argv: list[str]) -> None:
    commands, messages = _own_pipes()
    from meridiana.app.work import wire
    from meridiana.app.work.job import Context, Refused, resolve
    from meridiana.core.compute import procmem, resources
    out = wire.Writer(lambda data: os.write(messages, data))
    resources.contain_children()
    parent = int(argv[argv.index("--parent") + 1]) if "--parent" in argv else os.getppid()
    resources.watch_parent(parent)
    if "--low" in argv:
        resources.lower_priority()
    kept: dict = {}                     # per kind: what the jobs leave for the next one in this process
    lock = threading.Lock()
    now = {"run": None, "quota": 0}     # the job in hand
    waiting: list = []                  # a job that came before the one in hand had quite finished

    def run(run_id, function, blob, share, quota, name):
        ctx = Context(run_id, share, kept.setdefault(name, {}), out.send)
        try:
            result = resolve(function)(pickle.loads(blob), ctx)  # noqa: S301 - job request from the parent's private pipe
            ctx.flush()
            end = ("done", run_id, result)
        except resources.Stopped:
            end = ("stopped", run_id)
        except Refused as error:        # the user's own sentence
            end = ("refused", run_id, str(error))
        except MemoryError:
            out.send(("memory", run_id, procmem.rss() or 0, quota))
            sys.stderr.flush()
            os._exit(MEMORY_EXIT)
        except Exception as error:       # said to the window, with the traceback in the log (the standard error)
            traceback.print_exc()
            sys.stderr.flush()
            end = ("failed", run_id, f"{type(error).__name__}: {error}")
        # idle before the end is said: the window may send the next job as soon as it hears it
        with lock:
            now["run"] = None
            following = waiting.pop(0) if waiting else None
        try:
            try:
                out.send(end)
            except (pickle.PicklingError, TypeError, AttributeError) as error:     # a result that cannot travel
                print(f"The result of the job {name} could not be sent", file=sys.stderr, flush=True)    # the log
                out.send(("failed", run_id, f"{type(error).__name__}: {error}"))
        except OSError:
            os._exit(1)                 # the window has gone: nobody to tell
        if following is not None:
            begin(*following)

    def begin(run_id, function, blob, share, quota, name):
        with lock:
            if now["run"] is not None:
                waiting.append((run_id, function, blob, share, quota, name))
                return
            now["run"], now["quota"] = run_id, quota
            # cleared here, before the job's thread: a stop read just after is this job's
            resources.STOP.clear()
        threading.Thread(target=run, args=(run_id, function, blob, share, quota, name),
                         name="meridiana-work", daemon=True).start()

    def watch():
        while True:
            time.sleep(WATCH_S)
            with lock:
                run_id, quota = now["run"], now["quota"]
            if run_id is None:
                continue
            used = procmem.rss(os.getpid(), tree=True) or 0
            try:
                if quota and used > quota:
                    out.send(("memory", run_id, used, quota))
                    sys.stderr.flush()
                    os._exit(MEMORY_EXIT)
                out.send(("rss", run_id, used))
            except OSError:
                os._exit(1)

    threading.Thread(target=watch, name="meridiana-work-memory", daemon=True).start()
    out.send(("ready", os.getpid()))
    for message in wire.frames(_reader(commands)):
        word = message[0]
        if word == "quit":
            break
        if word == "job":
            begin(*message[1:])
        elif word == "warm":                # Center.warm: the job's function imported ahead, for the first job
            try:
                resolve(message[1])
            except Exception:               # said in the log; the job that comes will fail with it, said to the window
                traceback.print_exc()
                sys.stderr.flush()
        elif word == "stop":
            with lock:
                dropped = False
                if now["run"] == message[1]:
                    resources.STOP.set()
                elif any(w[0] == message[1] for w in waiting):     # a job not begun yet: it never begins
                    waiting[:] = [w for w in waiting if w[0] != message[1]]
                    dropped = True
            if dropped:
                out.send(("stopped", message[1]))
    # the window said so, or its pipe ended: nothing more to do; what this process started goes with it
    resources.STOP.set()
    resources.shutdown()
    sys.stderr.flush()
    os._exit(0)


if __name__ == "__main__":
    main(sys.argv)
