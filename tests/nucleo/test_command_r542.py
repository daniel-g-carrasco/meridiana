"""R542 (Daniel 07/11/2026 sera, «congeliamo ma ricordiamo di eliminare dopo»): the command `meridiana` (bin/meridiana,
`python -m meridiana`, the entry point of the Windows package and of the Flatpak) opens the Qt Quick window; the old
Widgets window only with `--widgets`. --version, --help and --self-test answer as before."""
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

        def widgets(argv):
            calls["widgets"] = list(argv)
            return 0
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["meridiana", *args]), \
                mock.patch("meridiana.quick.app.main", quick), mock.patch("meridiana.app.main", widgets), \
                contextlib.redirect_stdout(out):
            code = entry.main()
        return code, calls, out.getvalue()

    def test_no_argument_opens_the_quick(self):
        code, calls, _out = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("quick", calls)
        self.assertNotIn("widgets", calls)

    def test_a_project_opens_in_the_quick(self):
        _code, calls, _out = self.run_main("Rho.meridiana")
        self.assertNotIn("widgets", calls)
        self.assertEqual(calls["quick"][-1], "Rho.meridiana")

    def test_widgets_only_with_the_option(self):
        _code, calls, _out = self.run_main("--widgets", "Rho.meridiana")
        self.assertNotIn("quick", calls)
        self.assertEqual(calls["widgets"][1:], ["Rho.meridiana"])          # the option is not a file to open
        _code, calls, _out = self.run_main("--widgets", "--tour", "new")
        self.assertEqual(calls["widgets"][1:], ["--tour", "new"])

    def test_the_help_says_the_option(self):
        code, calls, out = self.run_main("--help")
        self.assertEqual((code, calls), (0, {}))
        self.assertIn("--widgets", out)

    def test_the_flatpak_launcher_keeps_the_option_for_bin_meridiana(self):
        # bin/meridiana opens the Quick now: the launcher passes --widgets on, it does not drop it
        text = (ROOT / "build-aux/flatpak-quick/meridiana-quick.sh").read_text(encoding="utf-8")
        branch = text.split("--widgets)", 1)[1].split(";;", 1)[0]
        self.assertNotIn("shift", branch)
        self.assertIn('bin/meridiana "$@"', branch)

    def test_the_windows_package_and_bin_use_the_same_entry_point(self):
        for path in ("build-aux/windows/meridiana_main.py", "bin/meridiana"):
            self.assertIn("from meridiana.__main__ import main", (ROOT / path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
