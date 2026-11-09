"""The report's preview made ahead (R548, Daniel 08/11/2026: «terrei molta più roba precaricata in memoria»): once
the year is ready and nothing changed for AHEAD_WAIT_MS, while the Report page is not shown and the memory allows it
(resources.preload: not with «Risparmia», not on a PC short of memory, not on battery unless «Usa tutto»), the
preview is made by a worker of its own at low priority; entered, the page shows its pages at once and asks no other
while nothing changed. Measured on Rho (offscreen): the first preview from 3.5 s after the entry to the pages there
at the entry (docs/quick/stato/r25-memoria.md).

r27 (docs/prestazioni/2026-11-08/confronto-r27-dell.md): made ahead only while the designer is still (activity.py: no
key, button, wheel, drag or change of phase for activity.IDLE_S), never while the phases are walked or the plan is
edited (the first entry of the phases walked in a row cost 40-150 ms more in r25, with the preview made 2.5 s after
the year whatever the designer did). The designer back: a request still being written is dropped, a worker already
running is suspended (with the process it started: the venv's launcher on Windows) and goes on at the next quiet or
when the page is entered; a change of the project ends it.

A mixin of ReportBackend (report.py): `_stale` says that the pages no longer answer for the project (a change came
after their request), `_made` what they were made with besides the project and the year (the profile, the language,
the day: what does not reach the session), `_ahead_failed` that the last one failed (made again after a change),
`_paused` the worker suspended."""
from __future__ import annotations

import datetime
import json
import os
import sys

from PySide6.QtCore import QTimer

from meridiana import i18n, resources
from . import activity

# the year ready and nothing changed for this long: the preview is made ahead. r27: as long as the designer's quiet
# (activity.IDLE_S), 2.5 s in r25: on the screen the walk of the phases begun 2.5 s after the year met the start of
# the preview (its request written on the pool, the window's snapshot) at its first click
AHEAD_WAIT_MS = 4000


def _tree(pid: int) -> list[int]:
    """`pid` and the processes under it (Windows: the venv's launcher starts the true interpreter as its child)."""
    if sys.platform != "win32":
        return [pid]
    import ctypes
    from ctypes import wintypes

    class Entry(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260)]
    k32 = ctypes.windll.kernel32
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    snap = k32.CreateToolhelp32Snapshot(2, 0)
    parents = {}
    entry = Entry()
    entry.dwSize = ctypes.sizeof(Entry)
    ok = k32.Process32FirstW(snap, ctypes.byref(entry))
    while ok:
        parents[entry.th32ProcessID] = entry.th32ParentProcessID
        ok = k32.Process32NextW(snap, ctypes.byref(entry))
    k32.CloseHandle(snap)
    found, todo = [pid], [pid]
    while todo:
        parent = todo.pop()
        for child, of in parents.items():
            if of == parent and child not in found:
                found.append(child)
                todo.append(child)
    return found


def suspend(pid: int, pause: bool) -> bool:
    """The process `pid` and those under it paused (`pause`) or let go on; whether it took."""
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
            for one in _tree(pid):
                handle = k32.OpenProcess(0x0800, False, one)        # PROCESS_SUSPEND_RESUME
                if handle:
                    done = call(handle) == 0 or done
                    k32.CloseHandle(handle)
            return done
        import signal
        os.kill(pid, signal.SIGSTOP if pause else signal.SIGCONT)
        return True
    except (OSError, AttributeError):
        return False


class AheadPreview:
    def _init_ahead(self):
        self._stale, self._made, self._ahead_run, self._ahead_failed = True, None, False, False
        self._paused = None             # the worker of a preview made ahead, suspended while the designer works
        self._ahead = QTimer(self)
        self._ahead.setSingleShot(True)
        self._ahead.setInterval(AHEAD_WAIT_MS)
        self._ahead.timeout.connect(self._preview_ahead)
        activity.subscribe(self._designer_back)

    def _key(self):
        """What a preview is made with besides the project and its year: the profile, the language, the day."""
        try:
            return json.dumps([self.profile(), i18n.language(), datetime.date.today().isoformat()], sort_keys=True,
                              default=str)
        except Exception:           # a profile that cannot be read: never taken as the same
            return None

    def _fresh(self):
        """Whether the pages in hand answer for the project as it is (R548): nothing changed after their request."""
        return bool(self._pages) and not self._stale and self._made is not None and self._made == self._key()

    def _can_go_ahead(self):
        return not (self._closed or self._active or self._busy or not self._stale or self._ahead_failed
                    or not self.ready or self.session.year_outdated() or not resources.preload())

    def _ahead_going(self):
        """Whether a preview made ahead is on its way (its request being written, or its worker running)."""
        return self._busy and self._mode == "preview" and self._ahead_run

    def _plan_ahead(self):
        """R548: a preview made ahead a moment after the year is ready, while the page is not shown, when the
        memory allows it (resources.preload: not with «Risparmia», not on a PC short of memory); r27: once the
        designer is still. One on its way that a change made stale ends (its pages would not be shown)."""
        if self._ahead_going() and self._stale and not self._active:
            self.cancel()               # its end (report._finished) plans the next one
            if self._busy:
                return
        if self._can_go_ahead():
            self._ahead.start(max(self._ahead.interval(), activity.wait_left_ms()))
        else:
            self._ahead.stop()

    def preload_changed(self):
        """The memory's choice changed (Impostazioni > Prestazioni): a preview ahead planned or dropped."""
        self._plan_ahead()

    def _preview_ahead(self):
        if not activity.idle():         # r27: the designer came back meanwhile: at the next quiet
            if self._can_go_ahead() or self._paused_now():
                self._ahead.start(activity.wait_left_ms())
            return
        if self._paused_now():
            self._go_on()
        elif self._can_go_ahead():
            self._start("preview", ahead=True)

    def _paused_now(self):
        return self._paused is not None and self._paused is self._process and self._ahead_going()

    def _designer_back(self):
        """r27: the designer did something after a quiet: a preview made ahead waits (activity.py)."""
        if self._closed or self._active or not self._ahead_going():
            return
        if self._pending is not None:   # its request still being written: dropped, nothing done yet
            self.cancel()
            self._ahead.start(activity.wait_left_ms())
            return
        if self._process is not None and not self._paused_now() and suspend(int(self._process.processId()), True):
            self._paused = self._process
            self._ahead.start(activity.wait_left_ms())

    def _go_on(self):
        """The suspended worker let go on (the quiet came back, or the page was entered)."""
        process, self._paused = self._paused, None
        if process is not None and process is self._process:
            suspend(int(process.processId()), False)

    def _ahead_entered(self):
        """The page entered: nothing more to plan; a preview made ahead and suspended goes on, for the page."""
        self._ahead.stop()
        if self._paused_now():
            self._go_on()
