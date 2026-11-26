"""The marks of the timed tests (tests/quick/aiuti/tempi.py) and the list the CI's timing job runs agree: a test
marked and not listed would be skipped by the shards and run by no job."""
import contextlib
import io
import re
import unittest
from unittest.mock import patch
from pathlib import Path

from quick.aiuti import tempi

QUICK = Path(__file__).resolve().parents[1]


class TimedMarks(unittest.TestCase):
    def test_every_module_with_a_timed_test_is_in_the_timing_jobs_list_and_only_those(self):
        marked = set()
        for path in QUICK.rglob('test_*.py'):
            if re.search(r'^\s*@timed\(', path.read_text(encoding='utf-8'), re.M):
                marked.add('quick.' + '.'.join(path.relative_to(QUICK).with_suffix('').parts))
        self.assertEqual(sorted(marked), sorted(tempi.TIMED))

    def test_shared_threshold_warning_does_not_hide_a_later_functional_failure(self):
        @tempi.timed('fixture threshold')
        def probe(case):
            tempi.check_timing(False, 'fixture was slow')
            case.fail('functional problem')

        log = io.StringIO()
        with patch.dict('os.environ', {tempi.ENV: 'warn'}), contextlib.redirect_stdout(log):
            with self.assertRaisesRegex(AssertionError, 'functional problem'):
                probe(self)
        self.assertIn('::warning', log.getvalue())
        self.assertIn('fixture was slow', log.getvalue())

    def test_unmarked_checks_and_guard_self_tests_are_strict(self):
        @tempi.timed('fixture threshold')
        def probe(case):
            tempi.check_timing(False, 'guard self-check', strict=True)

        with patch.dict('os.environ', {tempi.ENV: 'warn'}):
            with self.assertRaisesRegex(AssertionError, 'unmarked'):
                tempi.check_timing(False, 'unmarked')
            with self.assertRaisesRegex(AssertionError, 'guard self-check'):
                probe(self)
        with patch.dict('os.environ', {tempi.ENV: ''}):
            with self.assertRaisesRegex(AssertionError, 'local threshold'):
                tempi.check_timing(False, 'local threshold')
