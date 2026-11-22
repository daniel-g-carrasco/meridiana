"""The layers of the package, as in Neistar (docs/studio/43-strati-come-neistar.md, section 1): core and data know
nobody, app joins them, gui shows. Read from the sources with the AST (nothing is imported, it takes a second), every
import statement and the known literal dynamic loaders, the ones inside functions too.

- R1, who may import whom: core imports core; data imports data; app imports app, core and data; gui imports
  everything. The root of the package: __init__ and i18n import no layer, __main__ only gui and app and only inside
  its functions.
- R2, Qt (PySide6, shiboken6) only in gui; no network library in core and in data.
- R4, the __init__.py of a layer imports nothing of the package (no re-exports: they hide where a name comes from).
- R3, the modules of gui without Qt are those of FREE_OF_QT and never more: a new one is logic in the window, and goes
  to app or core unless there is a reason (presentation: schemes, texts, states), written beside its name.
- R5, relative imports stay within one folder; imports between folders are absolute, even for approved debts.
- At the root of the package only __init__, __main__ and i18n.

The presence of Qt is not proof of a module's responsibility (R3): that still needs human review.

DEBITI lists the imports against the rules that are there today, one line each, «file -> module»: why, and the step
that pays it (section 2.5 of the study). A new one is red, with its file, line and rule; one that is no longer there
is red too («take the line out»): the list can only get shorter."""

import ast
import json
import unittest
from importlib.util import resolve_name
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "meridiana"
LAYERS = ("core", "data", "app", "gui")
MAY = {"core": {"core"}, "data": {"data"}, "app": {"app", "core", "data"}, "gui": set(LAYERS)}
QT = ("PySide6", "shiboken6")
NETWORK = ("requests", "socket", "urllib.request", "http.client", "urllib3", "httpx")
ROOT_MODULES = {"__init__.py", "__main__.py", "i18n.py"}

DEBITI: dict[str, str] = {
    # the project saved and opened by the model itself (2.5, n. 4-5): Project.save/load to app/project/file.py, C7a
    "core/model/model.py -> data/atomic": "Project.save writes the file: C7a",
    "core/model/model.py -> data/project_archive": "Project.load opens the .mer: C7a",
    "core/model/model.py -> app/project/portability": "Project.save takes the resources inside: C7a",
    "core/model/model.py -> app/report/reports": "Project.save keeps the report's settings portable: C7a",
    # the weather: the download from PVGIS and its cache inside the core (2.5, n. 10-11): to app/weather.py, C7b
    "core/energy/meteo.py -> data/atomic": "the weather's cache written by the core: C7b",
    "core/energy/meteo.py -> requests": "PVGIS asked from the core: C7b",
    "core/energy/pvgis.py -> data/atomic": "the PVGIS cache written by the core: C7b",
    "core/energy/pvgis.py -> requests": "PVGIS asked from the core: C7b",
    # the catalogue looked up by the computations (2.5, n. 12-17): the records passed by app, as in Neistar, C7d
    "core/energy/optimizers.py -> data/catalog/rules": "the makers' rules read by the core: C7d",
    "core/energy/optimizers.py -> data/catalog": "the catalogue searched by the core: C7d",
    "core/energy/optimizer_strings.py -> data/catalog/rules": "the makers' rules read by the core: C7d",
    "core/energy/plant.py -> data/catalog": "the catalogue searched by the core: C7d",
    "core/energy/sizing.py -> data/catalog": "the catalogue searched by the core: C7d",
    "core/rules/checks.py -> data/catalog": "the catalogue searched by the checks: C7d",
    # the shadows of an IFC model asked by the core (2.5, n. 8-9): the function passed by whoever calls, C7c
    "core/model/model.py -> app/exchange/ifc_shade": "the key of the IFC shadows: C7c",
    "core/energy/system.py -> app/exchange/ifc_shade": "the IFC shadows of the year: C7c",
    # small ones (2.5, n. 18-20), C7e
    "core/rules/checks.py -> app/interface/phases": "the name of a phase in a check: C7e",
    "core/geometry/mesh.py -> app/jobs": "the fallback of module_sides: C7e",
    "data/catalog/personal.py -> app/platform/paths": "the folder of the personal catalogue found by data: C7e",
}

FREE_OF_QT: dict[str, str] = {
    "gui/backend/profiles/generic/profile.py": "generic profile inspector fields and scope presentation",
    "gui/backend/profiles/contracts.py": "profile inspector fields and their static presentation composition",
    "gui/backend/profiles/it/charts.py": "profile inspector fields and their static presentation composition",
    "gui/backend/profiles/it/profile.py": "profile inspector fields and their static presentation composition",
    "gui/backend/profiles/it/properties.py": "profile inspector fields and their static presentation composition",
    "gui/backend/profiles/registry.py": "profile inspector fields and their static presentation composition",
    # the window's own pieces that need no Qt: its entry, its start, what it shows (schemes, texts, states)
    "gui/__main__.py": "python -m meridiana.gui: the entry of the window",
    "gui/startup.py": "the start of the window: identity on Windows, the project given, the channel of the instance",
    "gui/capture.py": "the window's screenshots: logical to physical pixels",
    "gui/sample.py": "the recorded sample of Rho for the window's own checks",
    "gui/backend/activity.py": "whether the designer is working or still",
    "gui/backend/catalog_i18n.py": "the titles of the catalogue's kinds and the labels of its fields",
    "gui/backend/charts_data.py": "the result pages as plain data",
    "gui/backend/charts_schema.py": "the scheme of the charts",
    "gui/backend/conversation_view.py": "Meridio's message blocks as HTML",
    "gui/backend/models3d.py": "which 3D model shows which object",
    "gui/backend/navigation_targets.py": "the places Meridio can take the window to",
    "gui/backend/plan_collect.py": "the point and edge collectors of the plan",
    "gui/backend/plan_edit.py": "the gestures of the plan as edits (Daniel 10/11: stays in gui for now, study 43 choice 4)",
    "gui/backend/plan_locale.py": "the words of the plan",
    "gui/backend/plan_maps.py": "the map sources and their records for the plan",
    "gui/backend/plan_marks.py": "the symbols and the checks' marks of the plan",
    "gui/backend/plan_place.py": "placing an IFC model on the plan",
    "gui/backend/plan_scene.py": "the scene of the plan, as the QML draws it",
    "gui/backend/plan_shadows.py": "the shadows on the plan, from the solids of the energy model",
    "gui/backend/plan_tools.py": "the tools of the plan (Daniel 10/11: stays in gui for now, study 43 choice 4)",
    "gui/backend/plant_presenter.py": "the plant as its page shows it",
    "gui/backend/properties_schema.py": "the scheme of the properties' fields",
    "gui/backend/scene_assets.py": "the static context meshes of the 3D view",
    "gui/backend/settings_schema.py": "the scheme of the settings' page",
    "gui/backend/shell_state.py": "the panel arrangements kept for the window",
    "gui/backend/shell_tips.py": "the tips of the window's frame",
}


def modules() -> set[str]:
    out = set()
    for path in SRC.rglob("*.py"):
        parts = ("meridiana",) + path.relative_to(SRC).with_suffix("").parts
        out.add(".".join(parts[:-1] if parts[-1] == "__init__" else parts))
    return out


MODULES = modules()


def layer(parts) -> str | None:
    return parts[0] if parts and parts[0] in LAYERS else None


def owner(name: str) -> str:
    """The module a dotted name lives in (the longest that exists), as a path below the package: data/atomic."""
    parts = name.split(".")
    while len(parts) > 1 and ".".join(parts) not in MODULES:
        parts = parts[:-1]
    return "/".join(parts[1:]) or "meridiana"


def _import_records(path: Path):
    """Static imports and the literal dynamic forms used by the package, including deferred calls."""
    rel = path.relative_to(SRC)
    package = ("meridiana",) + rel.parts[:-1]
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    loaders = {a.asname or a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
               and n.module == "importlib" for a in n.names if a.name == "import_module"}
    libraries = {a.asname or a.name for n in ast.walk(tree) if isinstance(n, ast.Import)
                 for a in n.names if a.name == "importlib"}
    constants = {target.id: n.value.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                 and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)
                 for target in n.targets if isinstance(target, ast.Name)}
    inside = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            inside.update(id(n) for n in ast.walk(node) if n is not node)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield node.lineno, a.name, id(node) in inside, False
        elif isinstance(node, ast.ImportFrom):
            base = ".".join(package[:len(package) - node.level + 1]) if node.level else ""
            module = ".".join(x for x in (base, node.module) if x)
            for a in node.names:
                yield node.lineno, f"{module}.{a.name}" if a.name != "*" else module, id(node) in inside, bool(node.level)
        elif isinstance(node, ast.Call) and node.args:
            function = node.func
            dynamic = (isinstance(function, ast.Name) and function.id in loaders | {"__import__"}
                       or isinstance(function, ast.Attribute) and function.attr == "import_module"
                       and isinstance(function.value, ast.Name) and function.value.id in libraries)
            if not dynamic:
                continue
            argument = node.args[0]
            name = argument.value if isinstance(argument, ast.Constant) else constants.get(getattr(argument, "id", ""))
            if isinstance(argument, ast.Name) and argument.id == "__package__":
                name = ".".join(package)
            if not isinstance(name, str):
                # Parts.discover in gui imports the names returned by pkgutil.
                # No flow analysis: a new unresolved loader below gui needs review.
                if layer(rel.parts) != "gui":
                    yield node.lineno, "unresolved_dynamic_import", id(node) in inside, False
                continue
            relative = name.startswith(".")
            if relative:
                context = node.args[1] if len(node.args) > 1 else next(
                    (k.value for k in node.keywords if k.arg == "package"), None)
                context = context.value if isinstance(context, ast.Constant) else ".".join(package)
                name = resolve_name(name, context)
            yield node.lineno, name, id(node) in inside, relative


def imports(path: Path):
    """(line, absolute dotted name, inside a function), preserving the guard's public helper."""
    for line, name, lazy, _relative in _import_records(path):
        yield line, name, lazy


def import_folder(name: str) -> Path:
    module = owner(name)
    if module == "meridiana":
        return Path(".")
    return Path(module) if (SRC / module).is_dir() else Path(module).parent


def has_qt(path: Path) -> bool:
    return any(name.split(".")[0] in QT for _, name, _ in imports(path))


def against_the_rules() -> dict[str, list[str]]:
    """{«file -> module»: [«file:line: name: rule»]} of every import against the rules, debts or not.
    python -c "from nucleo import test_strati as t; print(*t.against_the_rules(), sep=chr(10))" lists the keys."""
    found: dict[str, list[str]] = {}
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(SRC)
        mine = layer(rel.parts)
        for line, name, lazy, relative in _import_records(path):
            parts = name.split(".")
            target = layer(parts[1:]) if parts[0] == "meridiana" else None
            rule = None
            if name == "unresolved_dynamic_import":
                rule = "dynamic imports outside gui need a literal module or an explicit classification"
            elif mine is None:
                if rel.as_posix() in ("__init__.py", "i18n.py") and target:
                    rule = f"{rel.as_posix()} imports no layer"
                elif rel.as_posix() == "__main__.py" and target and (target not in ("gui", "app") or not lazy):
                    rule = "__main__ imports gui and app only, inside its functions"
            elif parts[0] in QT and mine != "gui":
                rule = "Qt only in gui"
            elif mine in ("core", "data") and name.startswith(NETWORK):
                rule = f"no network in {mine}"
            elif target and target not in MAY[mine]:
                rule = f"{mine} may not import {target}"
            if rule:
                key = f"{rel.as_posix()} -> {owner(name) if parts[0] == 'meridiana' else parts[0]}"
                found.setdefault(key, []).append(f"{rel.as_posix()}:{line}: {name}: {rule}")
            if relative and parts[0] == "meridiana" and import_folder(name) != rel.parent:
                key = f"{rel.as_posix()} -> {owner(name)}"
                found.setdefault(key, []).append(
                    f"{rel.as_posix()}:{line}: {name}: R5: imports between folders must be absolute")
    return found


class Layers(unittest.TestCase):
    def test_every_import_goes_down(self):
        found = against_the_rules()
        wrong = [m for key, messages in found.items() for m in messages if key not in DEBITI or "R5:" in m]
        self.assertEqual(wrong, [], "imports against the layers (docs/studio/43, section 1)")
        self.assertEqual(sorted(set(DEBITI) - set(found)), [], "debts paid: take these lines out of DEBITI")

    def test_the_init_of_a_layer_imports_nothing_of_the_package(self):
        wrong = []
        for name in LAYERS:
            init = SRC / name / "__init__.py"
            if init.is_file():
                wrong += [f"{name}/__init__.py:{line}: {n}" for line, n, _ in imports(init)
                          if n.split(".")[0] == "meridiana"]
        self.assertEqual(wrong, [])

    def test_the_modules_of_gui_without_qt_are_never_more(self):
        free = set()
        for path in sorted((SRC / "gui").rglob("*.py")) if (SRC / "gui").is_dir() else []:
            rel = path.relative_to(SRC).as_posix()
            if path.name != "__init__.py" and not has_qt(path):
                free.add(rel)
        self.assertEqual(sorted(free - set(FREE_OF_QT)), [],
                         "new modules of gui without Qt: logic goes to app or core (R3), or say why here")
        self.assertEqual(sorted(set(FREE_OF_QT) - free), [], "no longer there or with Qt now: take them out")

    def test_at_the_root_of_the_package_only_init_main_and_i18n(self):
        loose = sorted(p.name for p in SRC.glob("*.py") if p.name not in ROOT_MODULES)
        folders = sorted(p.name for p in SRC.iterdir() if p.is_dir() and p.name != "__pycache__" and p.name not in LAYERS)
        self.assertEqual(loose, [], "a module at the root: it goes in a layer")
        self.assertEqual(folders, [], "a folder at the root that is not a layer")

    def test_the_debts_are_those_of_the_study(self):
        """17 imports of section 2.5 of the study (C3 paid three of the twenty), with the network of the weather written
        apart (two lines more): the list only gets shorter, a debt paid is a line taken out."""
        approved = json.loads(Path(__file__).with_name("approved_layer_debts.json").read_text(encoding="utf-8"))
        self.assertLessEqual(set(DEBITI), set(approved), "a debt not in the approved list")

    def test_the_rules_see_a_wrong_import(self):
        """The check itself: a made-up file of core that imports Qt, gui and the network is caught three times."""
        import tempfile
        global SRC
        kept = SRC
        with tempfile.TemporaryDirectory() as folder:
            SRC = Path(folder)
            (SRC / "core").mkdir()
            (SRC / "core" / "bad.py").write_text(
                "from PySide6 import QtCore\nfrom ..gui import shell\n\ndef f():\n    import requests\n",
                encoding="utf-8")
            try:
                with self.assertRaises(AssertionError) as caught:
                    self.test_every_import_goes_down()
            finally:
                SRC = kept
        text = str(caught.exception)
        for rule in ("Qt only in gui", "core may not import gui", "no network in core"):
            self.assertIn(rule, text)


if __name__ == "__main__":
    unittest.main()
