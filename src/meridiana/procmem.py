"""The memory of a process, without psutil: what the window watches while a worker reads an IFC model (the worker is
stopped before it takes the PC's memory, study 20, 4.2), and what the study measured. Windows through the process
API of kernel32 (K32GetProcessMemoryInfo), Linux through /proc; None where neither works.

On Windows the python.exe of a virtual environment is a launcher: the interpreter is its child, and the launcher
holds 4 MB whatever the child does (study 20, 3.5). `tree` adds the memory of the descendants: the window watches the
worker that way. Killing the launcher ends the child too (it puts it in a job that dies with it)."""

from __future__ import annotations

import os
import sys

GIB = 1 << 30


def _windows_counters(pid: int | None):
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.K32GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    own = pid is None or pid == os.getpid()
    handle = kernel.GetCurrentProcess() if own else kernel.OpenProcess(0x1000 | 0x0010, False, pid)
    if not handle:
        return None
    try:
        c = Counters()
        c.cb = ctypes.sizeof(Counters)
        if not kernel.K32GetProcessMemoryInfo(handle, ctypes.byref(c), c.cb):
            return None
        return c
    finally:
        if not own:
            kernel.CloseHandle(handle)


def _linux_status(pid: int | None, key: str) -> int | None:
    try:
        with open(f"/proc/{pid or 'self'}/status", encoding="ascii") as fh:
            for line in fh:
                if line.startswith(key + ":"):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def children(pid: int) -> list[int]:
    """The processes started by `pid` and by those, at any depth (Windows: a snapshot of the processes; Linux: /proc)."""
    parents: dict = {}
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Entry(ctypes.Structure):
            _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                        ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD),
                        ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                        ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                        ("szExeFile", ctypes.c_wchar * 260)]
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        kernel.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
        kernel.Process32FirstW.argtypes = (wintypes.HANDLE, ctypes.POINTER(Entry))
        kernel.Process32NextW.argtypes = (wintypes.HANDLE, ctypes.POINTER(Entry))
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        snap = kernel.CreateToolhelp32Snapshot(0x2, 0)          # TH32CS_SNAPPROCESS
        if not snap or snap == wintypes.HANDLE(-1).value:
            return []
        try:
            e = Entry()
            e.dwSize = ctypes.sizeof(Entry)
            ok = kernel.Process32FirstW(snap, ctypes.byref(e))
            while ok:
                parents.setdefault(int(e.th32ParentProcessID), []).append(int(e.th32ProcessID))
                ok = kernel.Process32NextW(snap, ctypes.byref(e))
        finally:
            kernel.CloseHandle(snap)
    else:
        try:
            names = [n for n in os.listdir("/proc") if n.isdigit()]
        except OSError:
            return []
        for n in names:
            try:
                with open(f"/proc/{n}/stat", encoding="ascii", errors="replace") as fh:
                    ppid = int(fh.read().rsplit(")", 1)[1].split()[1])
            except (OSError, ValueError, IndexError):
                continue
            parents.setdefault(ppid, []).append(int(n))
    out, todo = [], [pid]
    while todo:
        for c in parents.get(todo.pop(), []):
            if c not in out and c != pid:
                out.append(c)
                todo.append(c)
    return out


def rss(pid: int | None = None, tree: bool = False) -> int | None:
    """The bytes a process holds in memory now (its working set), with its descendants' when `tree`; None when it
    cannot be read."""
    if sys.platform == "win32":
        c = _windows_counters(pid)
        own = int(c.WorkingSetSize) if c is not None else None
    else:
        own = _linux_status(pid, "VmRSS")
    if not tree or pid is None or own is None:
        return own
    return own + sum(rss(c) or 0 for c in children(pid))


def peak(pid: int | None = None) -> int | None:
    """The most bytes a process has held in memory (its peak working set), None when it cannot be read."""
    if sys.platform == "win32":
        c = _windows_counters(pid)
        return int(c.PeakWorkingSetSize) if c is not None else None
    return _linux_status(pid, "VmHWM")


def physical() -> int | None:
    """The PC's memory in bytes."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Status(ctypes.Structure):
            _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        s = Status()
        s.dwLength = ctypes.sizeof(Status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s)):
            return None
        return int(s.ullTotalPhys)
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        return None


def limit(share: float = 0.5, most: int = 8 * GIB) -> int:
    """What a worker may take before it is stopped: half the PC's memory, 8 GiB at most (4 GiB when it cannot be
    read)."""
    total = physical()
    return min(most, int(total * share)) if total else 4 * GIB
