"""One group of tests, for the CI: python tools/run_tests.py tests/widget

After the summary the process ends at once with the tests' result. A group that opens hundreds of windows can crash while the
interpreter takes its objects apart in no order of its own («QObject: shared QObject was deleted directly», a segmentation
fault on Linux, an abort on Windows, 03-04/11/2026, not always): all the tests had passed by then, and the job went red. The
cause is not found; what this hides is that end of the process and nothing else, the summary still says what the tests did.

Before that end, what Qt still holds is taken apart (tests/_setup.end_qt, 07/11/2026): the last test's QML engine and its
window, left alive by a tearDown's deleteLater, met the DLLs' static destructors of os._exit and ended every run of
tests/quick/pianta, and of quick.pianta.test_aids_window alone, with an access violation after the summary.

faulthandler (r23-f8): a crash prints the stacks of every thread before the exit code (139 alone said nothing), and a test
that has not ended after MERIDIANA_TEST_LIMIT seconds (600 by default; 0 switches it off) prints them and ends the
process with the name of the test: a whole run of tests/quick stopped half way inside pianta without a trace (r22-unita).
The limit counts from the start of each test, so a class set-up is counted with the test before it. On Windows the
exit after the stacks can itself stay stuck (08/11/2026: a deadlocked process did not end in _exit): whoever runs
the suite keeps a time limit of its own and kills the process tree (taskkill /T) once «Timeout (» is printed."""

from __future__ import annotations

import faulthandler
import os
import sys
import unittest

LIMIT = float(os.environ.get("MERIDIANA_TEST_LIMIT", "600"))


class WatchedResult(unittest.TextTestResult):
    """The text result, with faulthandler's alarm armed again at the start of every test."""

    def startTest(self, test):
        if LIMIT > 0:
            faulthandler.cancel_dump_traceback_later()
            faulthandler.dump_traceback_later(LIMIT, exit=True)
        super().startTest(test)


def main(start: str) -> int:
    # the repository on the path as with «python -m unittest» from it: tests that import tools.* (parity) found it
    sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    faulthandler.enable()
    runner = unittest.TextTestRunner(resultclass=WatchedResult)
    program = unittest.main(module=None, argv=["unittest", "discover", "-s", start, "-t", "tests"], exit=False,
                            testRunner=runner)
    faulthandler.cancel_dump_traceback_later()
    return 0 if program.result.wasSuccessful() else 1


def end_qt() -> None:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests"))
    import _setup
    _setup.end_qt()


if __name__ == "__main__":
    code = main(sys.argv[1])
    sys.stdout.flush()
    sys.stderr.flush()
    end_qt()
    os._exit(code)
