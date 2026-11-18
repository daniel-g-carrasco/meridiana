"""Run selected unittest methods in separate processes and record real evidence.

Input is a JSON object mapping fully qualified test methods to parity ID lists.
Output and its .log companion must be new files within this checkout. This tool
never updates the parity ledger. Only unittest.addSuccess can produce passed.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import inspect
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import traceback
import unittest
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "src"), str(ROOT)]


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def log_path(output):
    return Path(str(output) + ".log")


def relative(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def source_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_mapping(mapping):
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("A nonempty mapping of test methods to parity IDs is required")
    registry = json.loads((ROOT / "docs/quick/compat/parita.json").read_text(encoding="utf-8"))
    known = {row["id"] for row in registry["items"]}
    for test, ids in mapping.items():
        if not isinstance(test, str) or not re.fullmatch(r"(?:[A-Za-z_]\w*\.){2,}test_\w+", test):
            raise ValueError(f"Expected module.Class.test_method: {test!r}")
        if not isinstance(ids, list) or not ids or any(not isinstance(pid, str) for pid in ids):
            raise ValueError(f"Nonempty parity ID list required for {test}")
        if len(set(ids)) != len(ids):
            raise ValueError(f"Duplicate parity IDs for {test}")
        for pid in ids:
            if pid not in known:
                raise ValueError(f"Unknown parity ID: {pid}")


class EvidenceResult(unittest.TextTestResult):
    """Retain success callbacks and every outcome that disqualifies full success."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.success_ids = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.success_ids.append(test.id())

    def outcome(self, selected):
        # Class/module cleanup errors can follow a method's addSuccess.
        if self.errors:
            return "error"
        if self.failures:
            return "failed"
        if self.unexpectedSuccesses:
            return "unexpected_success"
        if self.skipped:
            return "skipped"
        if self.expectedFailures:
            return "expected_failure"
        return "passed" if self.testsRun == 1 and self.success_ids == [selected] else "not_run"


def run_worker(test_id, parity_ids, output):
    """Run one actual TestCase with module/class fixtures via unittest.TestSuite."""
    case = {"test": test_id, "parity_ids": parity_ids, "path": "", "symbol": "", "sha256": "",
            "result": "load_error", "pid": os.getpid(), "started": timestamp()}
    try:
        module_name, class_name, method_name = test_id.rsplit(".", 2)
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
        if not isinstance(cls, type) or not issubclass(cls, unittest.TestCase):
            raise ValueError("Selected class is not a unittest.TestCase")
        if method_name not in cls.__dict__:
            raise ValueError("Select the class that directly defines the test method")
        path = Path(inspect.getsourcefile(cls)).resolve()
        case.update(path=relative(path), symbol=f"{class_name}.{method_name}", sha256=source_hash(path))
        with Path(str(output) + ".started.json").open("x", encoding="utf-8") as stream:
            json.dump(case, stream, ensure_ascii=False)
        suite = unittest.TestSuite([cls(method_name)])
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2, resultclass=EvidenceResult).run(suite)
        case.update(result=result.outcome(test_id), tests_run=result.testsRun,
                    success_callbacks=list(result.success_ids),
                    skipped=[reason for _test, reason in result.skipped])
        if source_hash(path) != case["sha256"]:
            case["result"] = "source_changed"
            case["error"] = "The selected test source changed during execution"
    except Exception as error:
        case.update(result="error" if "tests_run" in case else "load_error",
                    error=f"{type(error).__name__}: {error}")
        traceback.print_exc()
    case["finished"] = timestamp()
    with Path(output).open("x", encoding="utf-8") as stream:
        json.dump(case, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return 0 if case["result"] == "passed" else 1


def _started_case(output, fallback):
    path = Path(str(output) + ".started.json")
    if path.is_file():
        try:
            recorded = json.loads(path.read_text(encoding="utf-8"))
            return {**recorded, "result": fallback["result"], "log": fallback["log"]}
        except (OSError, ValueError):
            return fallback
    return fallback


def run_mapping(mapping, output, *, timeout=300):
    """Reserve new artifacts, then run each method in its own interpreter."""
    validate_mapping(mapping)
    if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Timeout must be a positive finite number of seconds")
    output = Path(output).resolve()
    relative(output)
    log = log_path(output)
    for path in (output, log):
        if path.exists():
            raise FileExistsError(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONPATH": os.pathsep.join(
        [str(ROOT / "tests"), str(ROOT / "src"), str(ROOT), os.environ.get("PYTHONPATH", "")])}
    report = {"schema": 1, "scope": "Actual unittest outcomes; no automatic parity approval",
              "started": timestamp(), "python": sys.version, "platform": sys.platform,
              "log": relative(log), "cases": []}
    with output.open("x", encoding="utf-8") as stream, log.open("x", encoding="utf-8") as transcript:
        with tempfile.TemporaryDirectory(prefix="quick-evidence-worker-", dir=output.parent) as folder:
            for index, (test_id, parity_ids) in enumerate(mapping.items()):
                worker_output = Path(folder) / f"{index}.json"
                command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--test", test_id,
                           "--parity-ids", json.dumps(parity_ids), "--output", str(worker_output)]
                transcript.write(f"\n=== {test_id} ===\n")
                transcript.flush()
                fallback = {"test": test_id, "parity_ids": parity_ids, "path": "", "symbol": "", "sha256": "",
                            "result": "process_error", "log": relative(log)}
                try:
                    completed = subprocess.run(command, cwd=ROOT, env=env, stdout=transcript,
                                               stderr=subprocess.STDOUT, timeout=timeout, check=False)
                    if worker_output.is_file():
                        case = json.loads(worker_output.read_text(encoding="utf-8"))
                    else:
                        case = {**_started_case(worker_output, fallback), "error": "Worker exited without an outcome report"}
                    case["returncode"] = completed.returncode
                    # A crash or abnormal shutdown after addSuccess cannot certify a pass.
                    expected_code = 0 if case["result"] == "passed" else 1
                    if completed.returncode != expected_code:
                        case.update(result="process_error", error="Worker process did not exit with its recorded outcome")
                except subprocess.TimeoutExpired:
                    case = {**_started_case(worker_output, fallback), "result": "timeout",
                            "error": f"Worker exceeded {timeout} seconds"}
                    transcript.write(case["error"] + "\n")
                except (OSError, ValueError, KeyError) as error:
                    case = {**fallback, "error": f"{type(error).__name__}: {error}"}
                    traceback.print_exc(file=transcript)
                case["log"] = relative(log)
                report["cases"].append(case)
        report["finished"] = timestamp()
        report["all_passed"] = all(case["result"] == "passed" for case in report["cases"])
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return report


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", type=Path, help="JSON object: fully qualified test method -> parity ID list")
    parser.add_argument("--output", type=Path, required=True, help="New JSON path inside this checkout; .log is created beside it")
    parser.add_argument("--timeout", type=float, default=300, help="Maximum seconds per isolated test, including startup and shutdown")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--test", help=argparse.SUPPRESS)
    parser.add_argument("--parity-ids", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.worker:
        return run_worker(args.test, json.loads(args.parity_ids), args.output)
    if args.mapping is None:
        parser.error("--mapping is required")
    try:
        mapping = json.loads(args.mapping.read_text(encoding="utf-8-sig"), object_pairs_hook=_unique_object)
        report = run_mapping(mapping, args.output, timeout=args.timeout)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    for case in report["cases"]:
        print(f"{case['result']}: {case['test']}")
    print(f"Evidence: {args.output}\nLog: {log_path(args.output)}")
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
