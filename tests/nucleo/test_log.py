"""What fails is written down and told: the log file in the state folder and the hook for the exceptions nobody
caught (study 18, G 3.3)."""

import sys
import tempfile
import threading
import unittest
from pathlib import Path

import _setup  # noqa: F401

from meridiana import log


class File(unittest.TestCase):
    def setUp(self):
        self.hook = sys.excepthook
        self.thread_hook = threading.excepthook
        self.folder = Path(tempfile.mkdtemp())
        self.file = self.folder / "state" / "meridiana.log"

    def tearDown(self):
        sys.excepthook, threading.excepthook = self.hook, self.thread_hook
        log.setup(None)
        log.tell_with(None)

    def test_a_complaint_goes_to_the_file_with_its_traceback(self):
        log.setup(self.file)
        try:
            raise ValueError("the thing")
        except ValueError as error:
            log.complain("somewhere", error)
        text = self.file.read_text(encoding="utf-8")
        self.assertIn("somewhere: ValueError: the thing", text)
        self.assertIn("Traceback", text)
        self.assertRegex(text, r"^\d{4}-\d{2}-\d{2}T")

    def test_a_big_log_is_rotated_once(self):
        self.file.parent.mkdir(parents=True)
        self.file.write_text("x" * (log.LOG_KEEP + 1), encoding="utf-8")
        log.setup(self.file)
        self.assertTrue(self.file.with_name("meridiana.log.1").exists())
        self.assertFalse(self.file.exists())

    def test_an_uncaught_exception_is_logged_and_told_in_one_line(self):
        told = []
        log.setup(self.file)
        log.install_excepthook(told.append)
        try:
            raise RuntimeError("boom")
        except RuntimeError as error:
            sys.excepthook(type(error), error, error.__traceback__)
        self.assertEqual(told, ["RuntimeError: boom"])
        self.assertIn("unhandled: RuntimeError: boom", self.file.read_text(encoding="utf-8"))

    def test_a_teller_that_fails_does_not_hide_the_error(self):
        def bad(_text):
            raise OSError("no window")
        log.setup(self.file)
        log.install_excepthook(bad)
        sys.excepthook(ValueError, ValueError("first"), None)
        text = self.file.read_text(encoding="utf-8")
        self.assertIn("unhandled: ValueError: first", text)
        self.assertIn("telling: OSError: no window", text)

    def test_without_a_file_a_complaint_still_reaches_stderr(self):
        log.setup(None)
        log.complain("quiet", ValueError("x"))           # no exception, no file
        self.assertIsNone(log.file())
