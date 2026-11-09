"""The journeys of the Quick: the offscreen ones run with the suite; the native ones (real mouse and keyboard on a hidden
desktop, tools/quick_native_input.py) only when asked (r23-f8).

The native journeys are apart from the normal suite: they run only on Windows with MERIDIANA_NATIVE=1 and a real
platform (_setup.native_reason). Otherwise MERIDIANA_NO_NATIVE is set before their modules are imported, so that their
classes skip themselves as they always did, and discovery leaves them out altogether: a module that is not run does not
run its tearDownModule either, and test_native.py's, which writes docs/quick/collaudo/run-native.json (the registry's
evidence, checked by parity/test_registry), no longer rewrites it after a run where nothing native ran (r22-unita).
The native modules are not edited for this: the registry keeps the sha256 of test_native.py, and its evidence would
become stale.

    MERIDIANA_NATIVE=1 python tools/run_tests.py tests/quick/percorsi     (the desktop free, no Meridiana open)
"""
import os

import _setup

NATIVE_REASON = _setup.native_reason()
if NATIVE_REASON:
    os.environ["MERIDIANA_NO_NATIVE"] = "1"


def _native(test) -> bool:
    """A test of a class that the natives' marks skip (Windows messages, MERIDIANA_NO_NATIVE)."""
    cls = type(test)
    return bool(getattr(cls, "__unittest_skip__", False)) and \
        getattr(cls, "__unittest_skip_why__", "") in ("switched off", "Windows messages")


def _without_natives(suite, loader):
    kept = loader.suiteClass()
    for test in suite:
        if hasattr(test, "__iter__"):
            inner = _without_natives(test, loader)
            if inner.countTestCases():
                kept.addTest(inner)
        elif not _native(test):
            kept.addTest(test)
    return kept


def load_tests(loader, standard_tests, pattern):
    found = loader.discover(start_dir=os.path.dirname(__file__), pattern=pattern or "test*.py")
    standard_tests.addTests(_without_natives(found, loader) if NATIVE_REASON else found)
    return standard_tests
