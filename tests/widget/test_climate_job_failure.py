"""Dependency failures leave the climate job through its failure signal, not a stuck spinner."""
import unittest
from pathlib import Path
from unittest.mock import patch

import _setup


class ClimateFailure(unittest.TestCase):
    def test_import_failure_emits_failure_once_and_never_success(self):
        _setup.qt_or_skip()
        from meridiana.ui.window import ClimateJob
        job = ClimateJob(45, 9, Path('unused-test-cache'), False)
        failed, done = [], []
        job.signals.failed.connect(lambda *args: failed.append(args))
        job.signals.done.connect(lambda *args: done.append(args))
        with patch('meridiana.ui.window.meteo.typical_year', side_effect=ImportError('dependency bootstrap')):
            job.run()
        self.assertEqual(failed, [(45.0, 9.0, 'dependency bootstrap')])
        self.assertFalse(done)
