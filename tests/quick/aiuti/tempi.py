"""The tests that measure time (a phase within 500 ms, a call of the window within 5 ms, a 60 Hz frame, a save
under 300 ms, an event of the plan's camera within 2 ms): one mark, `timed`, and one switch, MERIDIANA_TIMED.

Their thresholds are the program's own and they stay as they are: on Daniel's computers (and on the home server)
these tests run with the others and a slow step is red. On the CI's runners (two cores, no graphics card, a
software renderer, other jobs on the same host) the same step takes from one and a half to four times as long, and
what a red there says is the runner, not the program (22/11/2026). So the CI runs them apart (tools/quick_rif_tests.py
--timed): they are measured and a slow one gives a warning, the run is not red for it; the shards skip them with
MERIDIANA_TIMED=skip.

    MERIDIANA_TIMED unset    they run and their thresholds are asserted (the default, on every computer)
    MERIDIANA_TIMED=skip     they are skipped, with the reason (the CI's shards)

A test is marked for its time only. What a marked test checks besides the time is still checked on the CI, in the
timing job, but as a warning: keep such checks in a test of their own where they can be. TIMED below is the list of
the modules the timing job runs: a new mark goes in it too (tests/quick/sistema/test_tempi.py checks that the two
agree)."""
from __future__ import annotations

import functools
import os
import unittest

ENV = 'MERIDIANA_TIMED'

# the modules with a test marked `timed`, as python -m unittest names them
TIMED = (
    'quick.shell.test_phase_latency',
    'quick.shell.test_year_free',
    'quick.shell.test_checks_free',
    'quick.shell.test_weather_free',
    'quick.shell.test_salvataggio_r537',
    'quick.pagine.test_report_free',
    'quick.pianta.test_sun_map',
    'quick.pianta.test_measure_plan',
    'quick.pianta.test_motion_budget',
    'quick.meridio.test_edges_r698',
)


def skipped() -> bool:
    return os.environ.get(ENV, '').strip().lower() == 'skip'


def timed(what: str):
    """Mark a test whose assertion is a time: `what` says which (it is the reason of the skip)."""
    def mark(test):
        @functools.wraps(test)
        def run(self, *args, **kwargs):
            if skipped():
                raise unittest.SkipTest(f'timed ({what}): measured in the CI\'s timing job, {ENV}=skip')
            return test(self, *args, **kwargs)
        run.timed = what
        return run
    return mark
