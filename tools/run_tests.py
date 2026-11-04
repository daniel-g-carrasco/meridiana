"""One group of tests, for the CI: python tools/run_tests.py tests/widget

After the summary the process ends at once with the tests' result. A group that opens hundreds of windows can crash while the
interpreter takes its objects apart in no order of its own («QObject: shared QObject was deleted directly», a segmentation
fault on Linux, an abort on Windows, 03-04/11/2026, not always): all the tests had passed by then, and the job went red. The
cause is not found; what this hides is that end of the process and nothing else, the summary still says what the tests did."""

from __future__ import annotations

import os
import sys
import unittest


def main(start: str) -> int:
    program = unittest.main(module=None, argv=["unittest", "discover", "-s", start, "-t", "tests"], exit=False)
    return 0 if program.result.wasSuccessful() else 1


if __name__ == "__main__":
    code = main(sys.argv[1])
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
