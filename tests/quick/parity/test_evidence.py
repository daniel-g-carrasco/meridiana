"""Evidence must follow actual unittest outcomes and preserve prior artifacts."""

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import quick_rif_evidence as evidence


FIXTURE = '''import os
import unittest

class Outcomes(unittest.TestCase):
    def test_pass(self):
        print("real worker", os.getpid())
        self.assertEqual(2 + 2, 4)

    def test_fail(self):
        self.assertEqual("actual", "expected")

    @unittest.skip("fixture skip")
    def test_skip(self):
        self.fail("must not run")

    @unittest.expectedFailure
    def test_expected_failure(self):
        self.assertEqual(1, 2)

    @unittest.expectedFailure
    def test_unexpected_success(self):
        self.assertEqual(1, 1)

    def test_subtest_failure(self):
        with self.subTest(part=1):
            self.assertEqual(1, 2)

class TeardownError(unittest.TestCase):
    def test_pass_before_teardown(self):
        self.assertEqual(1, 1)

    @classmethod
    def tearDownClass(cls):
        raise RuntimeError("real teardown error")
'''


class EvidenceTest(unittest.TestCase):
    def setUp(self):
        parent = evidence.ROOT / "build/quick-evidence-tests"
        parent.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.fixture = self.folder / "evidence_fixture.py"
        self.fixture.write_text(FIXTURE, encoding="utf-8")
        self.output = self.folder / "evidence.json"
        extra = os.pathsep.join([str(self.folder), os.environ.get("PYTHONPATH", "")])
        self.env = patch.dict(os.environ, {"PYTHONPATH": extra})
        self.env.start()
        self.addCleanup(self.env.stop)

    def run_methods(self, methods):
        mapping = {f"evidence_fixture.{method}": ["command:save"] for method in methods}
        return evidence.run_mapping(mapping, self.output, timeout=30)

    def test_real_success_failure_skip_and_expected_failure_are_distinct(self):
        report = self.run_methods(["Outcomes.test_pass", "Outcomes.test_fail", "Outcomes.test_skip",
                                   "Outcomes.test_expected_failure", "Outcomes.test_unexpected_success",
                                   "Outcomes.test_subtest_failure", "TeardownError.test_pass_before_teardown"])
        cases = {c["symbol"]: c for c in report["cases"]}
        self.assertEqual({k: v["result"] for k, v in cases.items()}, {
            "Outcomes.test_pass": "passed", "Outcomes.test_fail": "failed", "Outcomes.test_skip": "skipped",
            "Outcomes.test_expected_failure": "expected_failure",
            "Outcomes.test_unexpected_success": "unexpected_success",
            "Outcomes.test_subtest_failure": "failed", "TeardownError.test_pass_before_teardown": "error"})
        self.assertEqual(len({c["pid"] for c in cases.values()}), len(cases))
        self.assertNotIn(os.getpid(), {c["pid"] for c in cases.values()})
        self.assertIn("real worker", (evidence.ROOT / report["log"]).read_text(encoding="utf-8"))
        self.assertIn("real teardown error", (evidence.ROOT / report["log"]).read_text(encoding="utf-8"))

    def test_report_has_exact_source_hash_and_registry_fields(self):
        from quick.parity.registry import validate_evidence
        report = self.run_methods(["Outcomes.test_pass"])
        case = report["cases"][0]
        self.assertEqual(case["sha256"], hashlib.sha256(self.fixture.read_bytes()).hexdigest())
        self.assertEqual(case["path"], self.fixture.relative_to(evidence.ROOT).as_posix())
        self.assertEqual(case["symbol"], "Outcomes.test_pass")
        self.assertEqual(case["parity_ids"], ["command:save"])
        self.assertEqual(json.loads(self.output.read_text(encoding="utf-8")), report)
        proof = {"kind": "test", "path": case["path"], "symbol": case["symbol"],
                 "sha256": case["sha256"], "run": self.output.relative_to(evidence.ROOT).as_posix()}
        self.assertEqual(validate_evidence({"id": "command:save", "status": "in corso", "evidence": [proof]}), [])

    def test_existing_report_or_log_is_never_overwritten(self):
        self.output.write_text("previous report", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.run_methods(["Outcomes.test_pass"])
        self.assertEqual(self.output.read_text(encoding="utf-8"), "previous report")
        other = self.folder / "other.json"
        log = evidence.log_path(other)
        log.write_text("previous log", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            evidence.run_mapping({"evidence_fixture.Outcomes.test_pass": ["command:save"]}, other)
        self.assertEqual(log.read_text(encoding="utf-8"), "previous log")
        self.assertFalse(other.exists())

    def test_missing_method_and_worker_crash_do_not_produce_success(self):
        with self.fixture.open("a", encoding="utf-8") as handle:
            handle.write('\nclass Crash(unittest.TestCase):\n    def test_crash(self):\n        os._exit(7)\n')
        report = self.run_methods(["Outcomes.test_missing", "Crash.test_crash"])
        self.assertEqual([c["result"] for c in report["cases"]], ["load_error", "process_error"])
        self.assertEqual(report["cases"][1]["symbol"], "Crash.test_crash")
        self.assertEqual(report["cases"][1]["sha256"], hashlib.sha256(self.fixture.read_bytes()).hexdigest())

    def test_source_changed_during_real_execution_cannot_be_certified(self):
        with self.fixture.open("a", encoding="utf-8") as handle:
            handle.write('\nclass MutatesSource(unittest.TestCase):\n    def test_edit(self):\n'
                         '        from pathlib import Path\n        p = Path(__file__)\n'
                         '        p.write_text(p.read_text(encoding="utf-8") + "\\n# changed\\n", encoding="utf-8")\n'
                         '        self.assertEqual(1, 1)\n')
        before = hashlib.sha256(self.fixture.read_bytes()).hexdigest()
        report = self.run_methods(["MutatesSource.test_edit"])
        self.assertEqual(report["cases"][0]["result"], "source_changed")
        self.assertEqual(report["cases"][0]["sha256"], before)
        self.assertNotEqual(before, hashlib.sha256(self.fixture.read_bytes()).hexdigest())

    def test_timeout_is_recorded_and_does_not_abort_the_whole_report(self):
        with self.fixture.open("a", encoding="utf-8") as handle:
            handle.write('\nclass Slow(unittest.TestCase):\n    def test_wait(self):\n'
                         '        import time\n        time.sleep(10)\n')
        report = evidence.run_mapping({"evidence_fixture.Slow.test_wait": ["command:save"],
                                       "evidence_fixture.Outcomes.test_pass": ["command:save"]},
                                      self.output, timeout=1)
        self.assertEqual([c["result"] for c in report["cases"]], ["timeout", "passed"])
        self.assertFalse(report["all_passed"])

    def test_unknown_parity_id_is_rejected_before_execution(self):
        with self.assertRaisesRegex(ValueError, "Unknown parity"):
            evidence.run_mapping({"evidence_fixture.Outcomes.test_pass": ["command:invented"]}, self.output)
        self.assertFalse(self.output.exists())
