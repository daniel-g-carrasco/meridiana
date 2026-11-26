"""The table of tools/run_tests.py that chooses the suites from the changed files (--changed): a few rows, and that every
suite it names exists."""
import importlib.util
import unittest
from types import SimpleNamespace

import _setup

SPEC = importlib.util.spec_from_file_location("run_tests_tool", _setup.ROOT / "tools" / "run_tests.py")
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


class Selection(unittest.TestCase):
    def setUp(self):
        self.known = tool.suites()

    def chosen(self, *files):
        return set(tool.choose(list(files), self.known)[0])

    def test_core_touches_every_suite(self):
        self.assertEqual(self.chosen("src/meridiana/core/energy/plant.py"), set(self.known))

    def test_the_plan_qml_touches_the_plan_suite_and_the_layer_test_only(self):
        self.assertEqual(self.chosen("src/meridiana/gui/qml/Meridiana/Plan/PlanView.qml"), {"quick/pianta", "nucleo"})

    def test_a_gui_part_we_do_not_know_runs_every_quick_suite(self):
        quick = {n for n in self.known if n.startswith("quick")}
        self.assertEqual(self.chosen("src/meridiana/gui/startup.py"), quick | {"nucleo"})

    def test_a_test_runs_its_own_suite_and_a_document_none(self):
        self.assertEqual(self.chosen("tests/quick/shell/test_parts.py"), {"quick/shell"})
        self.assertEqual(self.chosen("tests/calcoli/test_consumption.py"), {"calcoli"})
        self.assertEqual(self.chosen("docs/progetto.md"), set())

    def test_ci_propagates_the_timed_runner_status(self):
        ci = (_setup.ROOT / ".github/workflows/test.yml").read_text(encoding="utf-8")
        steps = ci.split("\n  timed:\n", 1)[1]
        self.assertRegex(steps, r"(?m)^\s+run: python -W default tools/quick_rif_tests\.py --timed-ci$")
        self.assertNotIn("continue-on-error", steps)

    def test_timed_coverage_allows_only_the_documented_skip_and_delegation(self):
        case = "quick.fixture.Case.test_timed"
        result = SimpleNamespace(ids={case}, skipped=[])
        self.assertTrue(tool.timed_coverage({case}, result))
        self.assertFalse(tool.timed_coverage({case, "quick.fixture.Case.test_lost"}, result))
        result.skipped = [(SimpleNamespace(id=lambda: case), "unexpected")]
        self.assertFalse(tool.timed_coverage({case}, result))

        edge = "quick.meridio.test_edges_r698.EdgesTest"
        skip = SimpleNamespace(id=lambda: f"setUpClass ({edge})")
        result.ids = set()
        result.skipped = [(skip, "no offscreen RHI on this machine")]
        self.assertTrue(tool.timed_coverage({edge + ".test_timed"}, result))
        self.assertFalse(tool.timed_coverage({case}, result))

        result.skipped = [(SimpleNamespace(id=lambda: tool.DELEGATE_SKIP), "run by Windows, on a screen large enough")]
        delegated = tool.R628 + ".Free.test_timed"
        self.assertFalse(tool.timed_coverage({delegated}, result))
        result.ids.add(tool.R628 + ".Windows.test_r628_free_windows_on_the_program_s_window")
        self.assertTrue(tool.timed_coverage({delegated}, result))

    def test_a_path_that_no_row_names_runs_everything(self):
        self.assertEqual(self.chosen("pyproject.toml"), set(self.known))

    def test_every_suite_the_table_names_exists(self):
        names = {s for _prefix, rows, _why in tool.SELECTION for s in (rows or ()) if s not in (tool.ALL, tool.QUICK)}
        self.assertEqual(names - set(self.known), set())


if __name__ == "__main__":
    unittest.main()
