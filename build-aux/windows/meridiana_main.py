"""Entry point of the Windows build (PyInstaller freezes this file).

The Qt Quick window starts its workers as `sys.executable -m <module> ...` (the computation, the tasks, the report:
quick/backend/shell_compute.py, shell_tasks.py, report.py). In the package sys.executable is Meridiana.exe, so a
first argument `-m` runs that module of the package, as Python would; the pools' processes (multiprocessing, spawn)
come back here too and are taken by freeze_support."""

import multiprocessing
import runpy
import sys


def run_module(argv):
    """`Meridiana.exe -m module args...`: the module run as __main__ with argv as Python gives it."""
    module = argv[2]
    sys.argv = [module, *argv[3:]]
    runpy.run_module(module, run_name="__main__", alter_sys=True)
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    if len(sys.argv) > 2 and sys.argv[1] == "-m":
        sys.exit(run_module(sys.argv))
    from meridiana.__main__ import main
    sys.exit(main())
