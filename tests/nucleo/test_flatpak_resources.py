"""The active recipe must ship the resources and dependencies used by the installed app."""
import ast
import json
import re
import shlex
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name, parse_wheel_filename

from meridiana.app.platform import paths

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "build-aux/flatpak/io.github.daniel_g_carrasco.meridiana.yaml"


class FlatpakResources(unittest.TestCase):
    def test_shipped_data_is_available_without_the_checkout(self):
        commands = [shlex.split(line.strip()[2:]) for line in MANIFEST.read_text(encoding="utf-8").splitlines()
                    if line.strip().startswith("- cp -r ")]
        required = set()
        for source in (ROOT / "src").rglob("*.py"):
            tree = ast.parse(source.read_text(encoding="utf-8-sig"))
            constants = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    try:
                        value = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        continue
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            constants[target.id] = value
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not node.args:
                    continue
                name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
                if name != "shipped":
                    continue
                first = node.args[0]
                if isinstance(first, ast.Starred) and isinstance(first.value, ast.Name):
                    required.add(constants[first.value.id][0])
                elif isinstance(first, ast.Constant):
                    required.add(first.value.split("/")[0])
                else:
                    self.fail(f"Classify the dynamic shipped resource in {source}")
        required.discard("manuale")  # copied separately from docs/
        self.assertTrue({"typst", "models", "meridio", "natural_earth"} <= required)
        with tempfile.TemporaryDirectory() as folder:
            installed = Path(folder)
            for command in commands:
                destination = installed / command[-1].removeprefix("/app/share/meridiana/")
                for item in command[2:-1]:
                    source = ROOT / item
                    if source.is_dir() and (item == "data" or item.startswith("data/")):
                        shutil.copytree(source, destination / source.name, dirs_exist_ok=True)
            with patch.object(paths, "REPO_ROOT", installed):
                for name in sorted(required):
                    self.assertIsNotNone(paths.shipped(name), f"Flatpak omits data/{name}")
                    self.assertTrue(paths.shipped(name).is_relative_to(installed))
                self.assertTrue(paths.shipped("typst", "mitex", "lib.typ").is_file())
                catalogue = paths.shipped("models", "catalog.json")
                self.assertTrue(json.loads(catalogue.read_text(encoding="utf-8")))

    def test_pinned_modules_satisfy_runtime_requirements(self):
        manifest = MANIFEST.read_text(encoding="utf-8")
        pins = {}
        for item in re.findall(r"^  - (\S+\.json)$", manifest, re.M):
            document = json.loads((MANIFEST.parent / item).read_text(encoding="utf-8"))
            modules = document if isinstance(document, list) else [document]
            while modules:
                module = modules.pop()
                modules.extend(module.get("modules", []))
                for command in module.get("build-commands", []):
                    for name, version in re.findall(r"([\w.-]+)==([\w.]+)", command):
                        pins[canonicalize_name(name)] = version
                for source in module.get("sources", []):
                    filename = source.get("url", "").rsplit("/", 1)[-1]
                    if filename.endswith(".whl"):
                        name, version, _build, _tags = parse_wheel_filename(filename)
                        pins[name] = str(version)
        for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            requirement = Requirement(line)
            name = canonicalize_name(requirement.name)
            self.assertIn(name, pins, f"Flatpak omits {name}")
            self.assertIn(pins[name], requirement.specifier, name)


if __name__ == "__main__":
    unittest.main()
