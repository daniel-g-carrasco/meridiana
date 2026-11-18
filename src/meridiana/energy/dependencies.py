"""Load the heavy solar library lazily, with one entry point for all worker threads."""
from __future__ import annotations

import importlib
import threading

_pvlib_lock = threading.RLock()


def load_pvlib():
    """Finish the root package before another thread imports one of its interdependent submodules.

    Importing iotools and pvsystem concurrently on a fresh process can expose pvlib's partially initialized
    pvsystem through its circular imports. Python's individual module locks do not prevent that cycle.
    Import failures propagate to the job's error handler; nothing is cached here after a failure.
    """
    with _pvlib_lock:
        return importlib.import_module("pvlib")
