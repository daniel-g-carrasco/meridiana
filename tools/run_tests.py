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
the suite keeps a time limit of its own and kills the process tree (taskkill /T) once «Timeout (» is printed.

Several suites at once (r32-prove). Every suite is a process of its own, with its own test home (tests/_setup.py makes a
temporary HOME and USERPROFILE for each process, and each one checks the user's real folders at its end), its output in
build/test-runs/<suite>.log and its result in <suite>.json; the end is a table: suite, tests, red, seconds.
    python tools/run_tests.py --all                      every suite, one after the other
    python tools/run_tests.py --all --parallel 4         the same, four processes at a time (--parallel alone: 4)
    python tools/run_tests.py tests/nucleo tests/calcoli --parallel 2
    python tools/run_tests.py --changed [base] [--parallel N] [--list]
                                                         the suites that the changed files can touch (SELECTION below)
    python tools/run_tests.py tests/nucleo --durations 15   one suite as always, and its slowest tests at the end
The exit code is not zero if a suite is red or did not end."""

from __future__ import annotations

import argparse
import faulthandler
import json
import os
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

LIMIT = float(os.environ.get("MERIDIANA_TEST_LIMIT", "600"))
ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "build" / "test-runs"            # the log and the result of every suite of the last run
R628 = "quick.shell.test_finestre_libere_r628"
DELEGATE_SKIP = f"setUpClass ({R628}.Free)"
TIMED_SKIPS = {
    "setUpClass (quick.meridio.test_edges_r698.EdgesTest)": "no offscreen RHI on this machine",
    "quick.pagine.test_pagine_r630.MadeAheadTest.test_4_on_a_graphics_api_the_pages_made_ahead_appear":
        "Qt Quick has no RHI here: the pages are made as they are asked (software renderer)",
    DELEGATE_SKIP: "run by Windows, on a screen large enough",
}


class WatchedResult(unittest.TextTestResult):
    """The text result, with faulthandler's alarm armed again at the start of every test, and the time of each test."""

    times: dict = {}                            # test id -> seconds (the set-ups of a class and a module are not in it)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ids = set()

    def startTest(self, test):
        self.ids.add(test.id())
        if LIMIT > 0:
            faulthandler.cancel_dump_traceback_later()
            faulthandler.dump_traceback_later(LIMIT, exit=True)
        self._started = time.perf_counter()
        super().startTest(test)

    def stopTest(self, test):
        super().stopTest(test)
        WatchedResult.times[test.id()] = time.perf_counter() - self._started


def slowest(count: int) -> list[tuple[str, float]]:
    return sorted(WatchedResult.times.items(), key=lambda item: -item[1])[:count]


def timed_coverage(expected, result) -> bool:
    missing, unexpected = expected - result.ids, []
    for test, reason in result.skipped:
        name = test.id()
        delegated = f"{R628}.Windows.test_r628_free_windows_on_the_program_s_window" in result.ids
        if TIMED_SKIPS.get(name) != reason or (name == DELEGATE_SKIP and not delegated):
            unexpected.append((name, reason))
        elif name.startswith("setUpClass ("):
            prefix = name.removeprefix("setUpClass (").removesuffix(")") + "."
            missing = {case for case in missing if not case.startswith(prefix)}
    print(f"Timed coverage: {len(expected & result.ids)} of {len(expected)} marked tests started, "
          f"{len(result.skipped)} skips in module, {len(unexpected)} unexpected", flush=True)
    for test, reason in result.skipped:
        print(f"Skipped: {test.id()}: {reason}")
    if missing or unexpected:
        print(f"Incomplete timed coverage: missing {sorted(missing)}, unexpected skips {unexpected}", file=sys.stderr)
    return bool(expected) and not (missing or unexpected)


def main(start: str, names: list[str] | None = None, durations: int = 0, report: str | None = None, *,
         timed_ci: bool = False) -> int:
    # the repository on the path as with «python -m unittest» from it: tests that import tools.* (parity) found it
    sys.path.insert(1, str(ROOT))
    if timed_ci:
        from tools.quick_rif_tests import timed_test_ids
        expected = timed_test_ids(names[0])
        if not expected:
            print(f"No marked tests selected: {names[0]}", file=sys.stderr)
            return 1
        os.environ["MERIDIANA_TIMED"] = "warn"
    faulthandler.enable()
    runner = unittest.TextTestRunner(resultclass=WatchedResult)
    began = time.perf_counter()
    if names:                                   # whole modules by name, as «python -m unittest quick.test_bridge»
        sys.path.insert(0, str(ROOT / "tests"))
        argv = ["unittest", *names]
    else:
        argv = ["unittest", "discover", "-s", start, "-t", "tests"]
    program = unittest.main(module=None, argv=argv, exit=False, testRunner=runner)
    faulthandler.cancel_dump_traceback_later()
    seconds = time.perf_counter() - began
    code = 0 if program.result.wasSuccessful() else 1
    if timed_ci and not timed_coverage(expected, program.result):
        code = 1
    # R594: a run that wrote in the user's own folders of Meridiana fails, with what it wrote (tests/_setup.py)
    setup = sys.modules.get("_setup")
    written = setup.profile_written() if setup is not None else []
    if written:
        print("FAILED: the tests wrote in the user's folders of Meridiana (R594):\n  " + "\n  ".join(written),
              file=sys.stderr)
        code = 1
    # R598: a photo of the session that was not the project in hand fails the run (tests/_setup.py)
    mismatched = setup.photo_mismatches() if setup is not None and hasattr(setup, "photo_mismatches") else []
    if mismatched:
        print(f"FAILED: {len(mismatched)} session.photo() not the project in hand:\n" + "\n".join(mismatched),
              file=sys.stderr)
        code = 1
    if durations:
        print(f"\nThe {durations} slowest tests:", file=sys.stderr)
        for name, taken in slowest(durations):
            print(f"  {taken:7.2f}s  {name}", file=sys.stderr)
    if report:
        result = program.result
        Path(report).write_text(json.dumps({
            "run": result.testsRun, "seconds": round(seconds, 2), "skipped": len(result.skipped), "code": code,
            "failures": [t.id() for t, _ in result.failures], "errors": [t.id() for t, _ in result.errors],
            "wrote_in_profile": written,
            "slowest": [[n, round(t, 2)] for n, t in slowest(max(durations, 30))]}), encoding="utf-8")
    return code


def end_qt() -> None:
    sys.path.insert(0, str(ROOT / "tests"))
    import _setup
    _setup.end_qt()


# ---------------------------------------------------------------------------------------------------------------------
# Several suites: the list, the choice from the changed files, the processes and the table (r32-prove).

def suites() -> dict[str, list[str]]:
    """Every suite of tests/ that the PC runs, by name, with the arguments of its one run. «esterni» (a PC with PVsyst) is
    not here. The modules of tests/quick itself run one by one, as tools/quick_rif_tests.py does: a Quick group does not mix
    its QApplication and QGuiApplication with another."""
    out = {}
    tests = ROOT / "tests"
    for name in ("nucleo", "calcoli", "formati", "profili"):
        if (tests / name).is_dir():
            out[name] = [f"tests/{name}"]
    quick = tests / "quick"
    for path in sorted(quick.iterdir()):
        if path.is_dir() and path.name != "__pycache__" and any(path.rglob("test_*.py")):
            out[f"quick/{path.name}"] = [f"tests/quick/{path.name}"]
    for path in sorted(quick.glob("test_*.py")):
        out[f"quick.{path.stem}"] = ["--names", f"quick.{path.stem}"]
    return out


# The choice of suites from the changed files (--changed): the one table. The first row whose prefix starts the path decides;
# a path that no row names runs everything. Row: prefix, suites, why. Suites: names of suites(), or ALL / QUICK (every
# quick/ subgroup and module); None: the test's own suite. The layers are core < data < app < gui, a change reaches the ones
# above: so core, data and app touch everything, and only a change in the gui's own windows is narrower. `nucleo` goes with
# every change in src/ (it holds the test of the layers and the files shipped).
ALL, QUICK = "ALL", "QUICK"
GUI_QML = "src/meridiana/gui/qml/Meridiana/"
GUI_BACKEND = "src/meridiana/gui/backend/"
SELECTION: list[tuple[str, object, str]] = [
    ("tools/run_tests.py", (ALL,), "the runner itself"),
    ("tests/_", (ALL,), "helpers shared by the tests"),
    ("tests/quick/__init__.py", (QUICK,), "the Quick's common base"),
    ("tests/", None, "its own suite"),
    ("src/meridiana/core/", (ALL,), "core: every layer above uses it"),
    ("src/meridiana/data/", (ALL,), "data: app and gui use it"),
    ("src/meridiana/app/", (ALL,), "app: the gui and the formats use it"),
    ("src/meridiana/i18n.py", (ALL,), "the words of every window"),
    (GUI_QML + "Plan/", ("quick/pianta", "nucleo"), "the plan's QML"),
    ("src/meridiana/gui/Plan.qml", ("quick/pianta", "nucleo"), "the plan's QML"),
    (GUI_QML + "View3D/", ("quick/vista3d", "nucleo"), "the 3D view's QML"),
    (GUI_QML + "Charts/", ("quick/grafici", "nucleo"), "the charts' QML"),
    (GUI_QML + "Plant/", ("quick/impianto", "nucleo"), "the plant's QML"),
    (GUI_QML + "Catalog/", ("quick/impianto", "nucleo"), "the catalogue's QML"),
    (GUI_QML + "Assistant/", ("quick/meridio", "nucleo"), "the assistant's QML"),
    (GUI_QML + "Properties/", ("quick/proprieta", "nucleo"), "the properties' QML"),
    (GUI_QML + "Shell/", ("quick/shell", "nucleo"), "the shell's QML"),
    (GUI_BACKEND + "plan", ("quick/pianta", "nucleo"), "the plan's backend"),
    (GUI_BACKEND + "plant", ("quick/impianto", "nucleo"), "the plant's backend"),
    (GUI_BACKEND + "charts", ("quick/grafici", "nucleo"), "the charts' backend"),
    (GUI_BACKEND + "assistant", ("quick/meridio", "nucleo"), "the assistant's backend"),
    (GUI_BACKEND + "properties", ("quick/proprieta", "nucleo"), "the properties' backend"),
    (GUI_BACKEND + "shell", ("quick/shell", "nucleo"), "the shell's backend"),
    ("src/meridiana/gui/", (QUICK, "nucleo"), "a window or part we do not know: every Quick suite"),
    ("src/", (ALL,), "src outside the layers"),
    ("docs/manuale/", ("nucleo",), "the manual ships with the program"),
    ("docs/quick/compat/", (QUICK, "nucleo"), "the compatibility files of the Quick"),
    ("docs/", (), "documents"),
    ("site/", (), "the site"),
    (".claude/", (), "assistants' files"),
    ("po/", (QUICK, "nucleo"), "the catalogues of words"),
    ("data/", ("nucleo",), "desktop and metainfo files"),
]


def suite_of_test(path: str, known: dict[str, list[str]]) -> tuple[tuple, str]:
    parts = path.split("/")
    if parts[1:2] == ["esterni"]:
        return (), "only on the PC with PVsyst"
    if len(parts) > 3 and parts[1] == "quick" and f"quick/{parts[2]}" in known:
        return (f"quick/{parts[2]}",), "its own suite"
    if len(parts) == 3 and parts[1] == "quick":
        if parts[2].startswith("test_") and f"quick.{parts[2][:-3]}" in known:
            return (f"quick.{parts[2][:-3]}",), "its own module"
        return (QUICK,), "a helper at the root of tests/quick"
    if len(parts) > 2 and parts[1] in known:
        return (parts[1],), "its own suite"
    return (ALL,), "tests/ outside the suites"


def choose(changed: list[str], known: dict[str, list[str]]) -> tuple[dict[str, list[str]], list[str]]:
    """The suites to run for the changed files, each with its reasons (the file and the row), and the files that need no
    test. A group is expanded; a path that no row names runs everything."""
    chosen: dict[str, list[str]] = {}
    nothing: list[str] = []
    for path in changed:
        group, why = (ALL,), "no row names it: everything"
        for prefix, rows, reason in SELECTION:
            if path.startswith(prefix):
                group, why = (rows, reason) if rows is not None else suite_of_test(path, known)
                break
        if not group:
            nothing.append(path)
        for item in group:
            names = (list(known) if item == ALL else [n for n in known if n.startswith("quick")] if item == QUICK
                     else [item])
            for name in names:
                if name in known:
                    chosen.setdefault(name, []).append(f"{path}: {why}")
    return chosen, nothing


def changed_files(base: str) -> list[str]:
    """What differs from `base` (from its merge base with HEAD) plus what is not committed (changed, staged, new)."""
    def git(*args):
        done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
        if done.returncode:
            raise SystemExit(f"git {' '.join(args)}: {done.stderr.strip()}")
        return [line for line in done.stdout.splitlines() if line.strip()]
    files = set(git("diff", "--name-only", f"{base}...HEAD")) | set(git("diff", "--name-only", "HEAD"))
    files |= set(git("ls-files", "--others", "--exclude-standard"))
    return sorted(files)


def _kill_tree(process: subprocess.Popen) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
    else:
        process.kill()


def run_one(name: str, args: list[str], durations: int, suite_limit: float) -> dict:
    """One suite as a process of its own, its output in a file; its result read from the file it writes."""
    RUNS.mkdir(parents=True, exist_ok=True)
    safe = name.replace("/", "-")
    log, result = RUNS / f"{safe}.log", RUNS / f"{safe}.json"
    result.unlink(missing_ok=True)
    command = [sys.executable, str(Path(__file__).resolve()), *args, "--report", str(result),
               "--durations", str(durations)]
    began, reported, status = time.perf_counter(), None, ""
    with open(log, "w", encoding="utf-8", errors="replace") as out:
        process = subprocess.Popen(command, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT)
        while process.poll() is None:
            time.sleep(0.2)
            now = time.perf_counter()
            if reported is None and result.exists():
                reported = now
            if reported is not None and now - reported > 60:      # the result is out and the process does not end
                status = "killed after its result"
                _kill_tree(process)
            elif now - began > suite_limit:
                status = f"killed after {suite_limit:.0f}s"
                _kill_tree(process)
        process.wait()
    row = {"suite": name, "wall": time.perf_counter() - began, "code": process.returncode, "status": status,
           "log": str(log)}
    try:
        row.update(json.loads(result.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        row["status"] = status or "no result (crashed?)"
    return row


def run_suites(names: list[str], known: dict[str, list[str]], parallel: int, durations: int, suite_limit: float) -> int:
    def last(name):                              # the slowest of the last run first, so that a long suite does not start last
        try:
            return json.loads((RUNS / f"{name.replace('/', '-')}.json").read_text(encoding="utf-8"))["seconds"]
        except (OSError, ValueError, KeyError):
            return 0
    pending, rows, lock = sorted(names, key=lambda n: -last(n)), {}, threading.Lock()

    def worker():
        while True:
            with lock:
                if not pending:
                    return
                name = pending.pop(0)
            row = run_one(name, known[name], durations, suite_limit)
            with lock:
                rows[name] = row
                red = len(row.get("failures", [])) + len(row.get("errors", []))
                print(f"  {name}: {row.get('run', '?')} tests, {red} red, {row['wall']:.0f}s", flush=True)

    began = time.perf_counter()
    threads = [threading.Thread(target=worker) for _ in range(max(1, min(parallel, len(names))))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print_table([rows[n] for n in names], time.perf_counter() - began, parallel, durations)
    return 1 if any(r["code"] or "run" not in r for r in rows.values()) else 0


def print_table(rows: list[dict], total: float, parallel: int, durations: int) -> None:
    width = max(len(r["suite"]) for r in rows) + 2
    print(f"\n{'suite':<{width}}{'tests':>7}{'red':>5}{'skipped':>9}{'seconds':>9}")
    red_all, slow = [], []
    for r in rows:
        red = len(r.get("failures", [])) + len(r.get("errors", []))
        note = "  " + r["status"] if r.get("status") else (f"  exit code {r['code']}" if r["code"] and not red else "")
        print(f"{r['suite']:<{width}}{r.get('run', '-'):>7}{red:>5}{r.get('skipped', '-'):>9}{r['wall']:>9.0f}{note}")
        red_all += [(r["suite"], t) for t in r.get("failures", []) + r.get("errors", [])]
        red_all += [(r["suite"], "wrote in the user's folders of Meridiana (R594): " + w)
                    for w in r.get("wrote_in_profile", [])]
        slow += [(t, n, r["suite"]) for n, t in r.get("slowest", [])]
    print(f"{'total':<{width}}{sum(r.get('run', 0) for r in rows):>7}{len(red_all):>5}{'':>9}{total:>9.0f}"
          f"   ({parallel} at a time; the suites added up: {sum(r['wall'] for r in rows):.0f}s)")
    if red_all:
        print("\nRed:")
        for suite, test in red_all:
            print(f"  {suite}  {test}")
    for r in rows:
        if "run" not in r:
            print(f"\n{r['suite']}: {r['status']}; its output: {r['log']}")
    if durations:
        print(f"\nThe {durations} slowest tests of all:")
        for taken, name, _suite in sorted(slow, reverse=True)[:durations]:
            print(f"  {taken:7.2f}s  {name}")


def cli() -> tuple[int, bool]:
    """The exit code, and whether the tests ran in this process (then Qt is taken apart before the end)."""
    parser = argparse.ArgumentParser(description="Run one suite of tests/ in this process, or several as processes.")
    parser.add_argument("paths", nargs="*", help="tests/<folder>: one runs in this process, several as processes")
    parser.add_argument("--names", nargs="+", help="whole test modules by name (quick.test_bridge)")
    parser.add_argument("--all", action="store_true", help="every suite")
    parser.add_argument("--changed", nargs="?", const="main", metavar="BASE",
                        help="the suites that the files changed from BASE (main) and not committed can touch")
    parser.add_argument("--parallel", nargs="?", const=4, type=int, metavar="N",
                        help="N suites at a time (4 without N); several suites without it go one at a time")
    parser.add_argument("--list", action="store_true", help="with --changed or --all: say the suites, do not run")
    parser.add_argument("--durations", type=int, default=0, metavar="N", help="the N slowest tests at the end")
    parser.add_argument("--report", help="(one suite) the file where its result is written, as JSON")
    parser.add_argument("--timed-ci", action="store_true", help="verify timed test selection and warn on measured thresholds")
    parser.add_argument("--suite-limit", type=float, default=2400, help="seconds after which a suite is killed")
    args = parser.parse_args()
    if args.timed_ci and (not args.names or len(args.names) != 1):
        parser.error("--timed-ci requires one module or class with --names")
    if args.names:
        return main("", args.names, args.durations, args.report, timed_ci=args.timed_ci), True
    if not (args.all or args.changed or len(args.paths) > 1 or args.parallel):
        if len(args.paths) != 1:
            parser.error("a folder of tests, --all or --changed")
        return main(args.paths[0], None, args.durations, args.report), True
    known = suites()
    if args.all:
        names = list(known)
    elif args.changed:
        changed = changed_files(args.changed)
        chosen, nothing = choose(changed, known)
        print(f"{len(changed)} files changed from {args.changed} and not committed; {len(nothing)} need no test")
        names = [n for n in known if n in chosen]
        for name in names:
            why = sorted(set(chosen[name]))
            print(f"  {name}: {why[0]}" + (f" (+{len(why) - 1} more)" if len(why) > 1 else ""))
        if not names:
            print("nothing to run")
            return 0, False
    else:
        names = []
        for path in args.paths:
            key = path.replace("\\", "/").rstrip("/").removeprefix("tests/")
            if key not in known:
                parser.error(f"{path}: not a suite (they are: {', '.join(known)})")
            names.append(key)
    print(f"{len(names)} suites: {', '.join(names)}", flush=True)
    if args.list:
        return 0, False
    return run_suites(names, known, args.parallel or 1, args.durations, args.suite_limit), False


if __name__ == "__main__":
    code, in_process = cli()
    sys.stdout.flush()
    sys.stderr.flush()
    if in_process:
        end_qt()
    os._exit(code)
