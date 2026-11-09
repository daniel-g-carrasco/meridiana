"""R478: the processes of the computation's pool do not outlive the process that made them, however it ends.

On 06/11/2026 a run of the Quick's tests on lucciola (Python 3.14, whose default on Linux was forkserver) left two
trees of 12 workers alive for an hour and a half with parent 1. Here a process makes the pool and is killed (the
hardest end: no atexit, no closing of the pool): every worker must be gone within seconds, on Windows and Linux."""
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"

MAKER = r'''
import os, sys, time, concurrent.futures
sys.path.insert(0, sys.argv[1])
os.environ["MERIDIANA_WORKERS"] = "2"
from meridiana import resources
concurrent.futures.wait(resources.warm(), timeout=120)
print(" ".join(str(p) for p in sorted(resources._POOL._processes)), flush=True)
time.sleep(600)
'''


def alive(pid: int) -> bool:
    """Whether process `pid` still runs (a zombie waiting for its parent does not)."""
    if sys.platform == "win32":
        import ctypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        handle = kernel.OpenProcess(0x1000, False, pid)            # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            kernel.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code))
            return code.value == 259                                # STILL_ACTIVE
        finally:
            kernel.CloseHandle(ctypes.c_void_p(handle))
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        with open(f"/proc/{pid}/stat", encoding="ascii") as f:
            return f.read().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return True


def wait_gone(pids, seconds=20.0):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        left = [p for p in pids if alive(p)]
        if not left:
            return []
        time.sleep(0.2)
    return [p for p in pids if alive(p)]


class PoolOrphans(unittest.TestCase):
    def test_the_workers_end_when_their_maker_is_killed(self):
        maker = subprocess.Popen([sys.executable, "-c", MAKER, str(SRC)], stdout=subprocess.PIPE, text=True)
        try:
            line = maker.stdout.readline().split()
            workers = [int(p) for p in line]
            self.assertGreaterEqual(len(workers), 1, "the pool did not start")
            self.assertTrue(all(alive(p) for p in workers))
        finally:
            maker.kill()
            maker.wait(30)
            maker.stdout.close()
        self.assertEqual(wait_gone(workers), [], "workers of the pool outlived the process that made them")


if __name__ == "__main__":
    unittest.main()
