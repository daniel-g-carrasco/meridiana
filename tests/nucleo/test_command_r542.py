"""The command `meridiana` (bin/meridiana, `python -m meridiana`, the entry point of the Windows package and of the
Flatpak) opens the Qt Quick window (R542, Daniel 07/11/2026). The Widgets window and its options went with
r30-struttura: `--widgets`, `--tour` and `--self-test` are said gone and open nothing (a script that waited for
`--self-test` to end would have waited for a window). --version and --help answer as before."""
import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest import mock

import _setup  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]


class TheCommand(unittest.TestCase):
    def run_main(self, *args):
        from meridiana import __main__ as entry
        calls = {}

        def quick(argv=None):
            calls["quick"] = list(sys.argv)
            return 0
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv", ["meridiana", *args]), mock.patch("meridiana.gui.application.main", quick), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = entry.main()
        return code, calls, out.getvalue(), err.getvalue()

    def test_no_argument_opens_the_quick(self):
        code, calls, _out, _err = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("quick", calls)

    def test_a_project_opens_in_the_quick(self):
        _code, calls, _out, _err = self.run_main("Rho.meridiana")
        self.assertEqual(calls["quick"][-1], "Rho.meridiana")

    def test_the_options_of_the_widgets_window_are_said_gone(self):
        for args in (("--widgets", "Rho.meridiana"), ("Rho.meridiana", "--widgets"), ("--tour", "new"),
                     ("--tour=3",), ("--self-test", "report.txt")):
            with self.subTest(args=args):
                code, calls, _out, err = self.run_main(*args)
                self.assertEqual((code, calls), (2, {}))            # nothing opened
                self.assertIn(args[0].partition("=")[0] if args[0].startswith("--") else "--widgets", err)
                self.assertIn("meridiana.gui.package_check", err)

    def test_the_help_says_what_is_left(self):
        code, calls, out, _err = self.run_main("--help")
        self.assertEqual((code, calls), (0, {}))
        self.assertIn("--version", out)
        for gone in ("--widgets", "--tour", "--self-test"):
            self.assertNotIn(gone, out)

    def test_the_flatpak_launcher_leaves_them_to_bin_meridiana(self):
        # answered without a window by bin/meridiana, never passed on to the Quick as a project to open
        text = (ROOT / "build-aux/flatpak-quick/meridiana-quick.sh").read_text(encoding="utf-8")
        case = next(line for line in text.splitlines() if "--version|" in line)
        for option in ("--widgets", "--tour", "--self-test", "--help"):
            self.assertIn(option, case)
        self.assertIn('bin/meridiana "$@"', text.split(case, 1)[1].split(";;", 1)[0])

    def test_the_windows_package_and_bin_use_the_same_entry_point(self):
        for path in ("build-aux/windows/meridiana_main.py", "bin/meridiana"):
            self.assertIn("from meridiana.__main__ import main", (ROOT / path).read_text(encoding="utf-8"))

    def test_the_packages_are_checked_with_package_check(self):
        # the check of a package is the Quick's (meridiana.gui.package_check), in the place of --self-test
        for path in ("build-aux/windows/build.ps1", ".github/workflows/release.yml", ".github/workflows/flatpak-build.yml"):
            text = (ROOT / path).read_text(encoding="utf-8")
            self.assertIn("meridiana.gui.package_check", text, path)
            self.assertNotIn("--self-test", text, path)
        self.assertNotIn("--self-test", (ROOT / ".github/workflows/test.yml").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
