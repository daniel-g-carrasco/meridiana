"""What a move of the modules breaks without any import saying so (study 43, risks R3 and R4).

- Every module started by name (`python -m ...`, the processes of the computation, the tasks, the report, the IFC
  reading, the gallery, the launcher of the Flatpak, the check of the packages) exists: a name in a string is not an
  import, Ruff and the imports of the tests do not see it. The constants are read from the sources with the AST (the
  modules need Qt) and the command lines from build-aux/, bin/ and .github/.
- Every file the package finds by its own path exists: the catalogue's data, the report's template, the rules of
  Meridio's reading aloud, the voice's worker, LibreOffice's measure, the manual, the QML of the window."""

import ast
import importlib.util
import re
import unittest

import _setup

ROOT = _setup.ROOT
SRC = ROOT / "src" / "meridiana"
STARTED = re.compile(r"""-m['",\s]+(meridiana(?:\.[A-Za-z_]\w*)+)""")


def worker_constants() -> dict[str, str]:
    """{file: module} of every module-level `WORKER = "meridiana..."` of the package."""
    out = {}
    for path in SRC.rglob("*.py"):
        for node in ast.parse(path.read_text(encoding="utf-8-sig")).body:
            if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "WORKER" for t in node.targets) \
                    and isinstance(node.value, ast.Constant) and str(node.value.value).startswith("meridiana."):
                out[path.relative_to(ROOT).as_posix()] = node.value.value
    return out


def command_lines() -> dict[str, set[str]]:
    """{module: files} of every `-m meridiana...` written in the build, the launcher and the workflows."""
    out: dict[str, set[str]] = {}
    for folder in ("build-aux", "bin", ".github"):
        for path in (ROOT / folder).rglob("*"):
            if path.is_file() and path.suffix not in (".png", ".ico", ".svg"):
                try:
                    text = path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                for name in STARTED.findall(text):
                    out.setdefault(name, set()).add(path.relative_to(ROOT).as_posix())
    return out


class StartedByName(unittest.TestCase):
    def test_the_constants_name_modules_that_exist(self):
        found = worker_constants()
        self.assertGreaterEqual(len(found), 5, found)       # report, IFC, computation, tasks, gallery
        missing = {f: m for f, m in found.items() if importlib.util.find_spec(m) is None}
        self.assertEqual(missing, {})

    def test_each_constant_is_the_module_it_is_written_in_or_a_neighbour(self):
        """shell_compute, shell_tasks and gallery start themselves: their constant is their own name."""
        for file, module in worker_constants().items():
            own = file[len("src/"):-len(".py")].replace("/", ".")
            if file.endswith(("shell_compute.py", "shell_tasks.py", "gallery.py")):
                self.assertEqual(module, own, file)

    def test_the_command_lines_name_modules_that_exist(self):
        lines = command_lines()
        self.assertTrue(lines, "no `-m meridiana...` found: the pattern is wrong")
        missing = {m: sorted(f) for m, f in lines.items() if importlib.util.find_spec(m) is None}
        self.assertEqual(missing, {})


class FoundByPath(unittest.TestCase):
    def test_the_files_beside_the_modules_exist(self):
        from meridiana import PACKAGE_DIR, REPO_ROOT
        from meridiana.data import catalog
        self.assertEqual(PACKAGE_DIR, SRC.resolve())
        self.assertEqual(REPO_ROOT, ROOT.resolve())
        self.assertTrue((catalog.DATA / "modules_cec.json.gz").is_file(), catalog.DATA)
        self.assertTrue((catalog.DATA / "preferred_makers.json").is_file())
        self.assertTrue((catalog.DATA / "optimizer_rules.json").is_file())
        for module, name in (("meridiana.app.report.engine", "TEMPLATE"),
                             ("meridiana.app.report.office", "SCRIPT"), ("meridiana.app.assistant.reading", "RULES")):
            mod = importlib.import_module(module)
            self.assertTrue(getattr(mod, name).is_file(), f"{module}.{name}")
        from meridiana.app.assistant import design_rules, speech
        self.assertTrue((design_rules.DATA / "optimizer_rules.json").is_file())
        self.assertTrue(speech.worker_script().is_file())

    def test_the_files_of_the_repository_are_found(self):
        from meridiana.app.interface import help
        from meridiana.app.platform import paths
        self.assertEqual(help.manual_dir(), (ROOT / "docs" / "manuale").resolve())
        self.assertIsNotNone(paths.shipped("icons"))
        self.assertIsNotNone(paths.shipped("fonts"))

    def test_the_qml_of_the_window_is_beside_its_package(self):
        spec = importlib.util.find_spec("meridiana.gui")
        folder = next(iter(spec.submodule_search_locations))
        from pathlib import Path
        self.assertTrue((Path(folder) / "qml" / "Meridiana" / "Shell" / "Workbench.qml").is_file(), folder)
        self.assertTrue((Path(folder) / "Plan.qml").is_file())
        self.assertTrue((Path(folder) / "paper" / "ReportScene.qml").is_file())


if __name__ == "__main__":
    unittest.main()
