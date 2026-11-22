"""The marks of the timed tests (tests/quick/aiuti/tempi.py) and the list the CI's timing job runs agree: a test
marked and not listed would be skipped by the shards and run by no job."""
import re
import unittest
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
