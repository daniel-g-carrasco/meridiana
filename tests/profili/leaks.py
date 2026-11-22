"""Enumerate exact national references, including comments and raw catalogue data."""

from __future__ import annotations

import ast
from collections import Counter
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src" / "meridiana"
REGISTRIES = {"core/rules/registry.py", "app/profiles/registry.py", "gui/backend/profiles/registry.py"}
ITALIAN_FOLDERS = ("core/rules/profiles/it", "app/profiles/it", "gui/backend/profiles/it")
PATTERN = re.compile(
    r"\bCEI[ -]*(?:EN[ -]*)?\d[\w./: -]*|\b(?:VVF|DCPREV|NTC|ARERA|GSE|CER|TRASE|TIAD|CACER|TICA|GAUD[IÌ]|SUER)\b"
    r"|\bD\.?P\.?R\.?\s*151\b|\bD\.?M\.?\s*(?:MASE\s*)?(?:37|414)\b"
    r"|\bD\.?\s*Lgs\.?\s*\d+/\d+|\bDGR\s*[\w/]+|\b(?:6153|6437)/2026\b"
    r"|\b(?:Legislative Decree|Ministerial Decree|Presidential Decree|Regional Law|Decree Law)\b"
    r"|Europe/Rome|\b(?:F1|F2|F3)\b|\b(?:holidays|festivit[àa])\b",
    re.IGNORECASE,
)


def allowed(path: Path) -> bool:
    return any(path.parts[:len(Path(folder).parts)] == Path(folder).parts for folder in ITALIAN_FOLDERS)


def _symbol(tree, line: int) -> str:
    found = [(n.lineno, n.name) for n in ast.walk(tree)
             if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
             and n.lineno <= line <= n.end_lineno]
    return ".".join(name for _start, name in sorted(found)) or "<module>"


def scan(root: Path = SOURCE) -> list[dict]:
    """An exact string and its enclosing symbol/pointer, never a directory allowance."""
    counts = Counter()
    for path in sorted(root.rglob("*")):
        if path.suffix not in (".py", ".qml", ".json") or allowed(path.relative_to(root)):
            continue
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8-sig")
        if path.suffix == ".json":
            def visit(value, pointer="", rel=rel):
                if isinstance(value, dict):
                    for key, item in value.items():
                        child = pointer + "/" + key.replace("~", "~0").replace("/", "~1")
                        if PATTERN.search(key):
                            counts[(rel, child + "#key", key)] += 1
                        visit(item, child)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        visit(item, pointer + "/" + str(i))
                elif isinstance(value, str) and PATTERN.search(value):
                    counts[(rel, pointer, value)] += 1
            visit(json.loads(text))
        else:
            tree = ast.parse(text) if path.suffix == ".py" else None
            # The calendar contract names a service, without choosing a national calendar.
            neutral_declarations = set()
            calendar_calls = set()
            compatibility_fields = set()
            empty_calendars = set()
            if tree:
                for node in ast.walk(tree):
                    if (isinstance(node, ast.FunctionDef) and node.name == "holidays"
                            and len(node.body) == 1 and isinstance(node.body[0], ast.Return)
                            and isinstance(node.body[0].value, ast.Call)
                            and isinstance(node.body[0].value.func, ast.Name) and node.body[0].value.func.id == "set"
                            and not node.body[0].value.args and not node.body[0].value.keywords):
                        empty_calendars.add(node.lineno)
                    if (isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
                            and node.target.id == "trase" and node.value is not None
                            and ast.unparse(node.value) == "field(default_factory=lambda: registry.legacy_default('economics', 'trase'))"):
                        compatibility_fields.add(node.lineno)
                    if isinstance(node, ast.Attribute) and node.attr == "holidays":
                        calendar_calls.add(node.end_lineno)
                    if (isinstance(node, ast.FunctionDef) and node.name == "holidays"
                            and len(node.body) == 1 and isinstance(node.body[0], ast.Return)
                            and isinstance(node.body[0].value, ast.Call)
                            and isinstance(node.body[0].value.func, ast.Attribute)
                            and node.body[0].value.func.attr == "holidays"
                            and ast.unparse(node.body[0].value.func.value) == "registry.get(profile_id).calendar()"):
                        neutral_declarations.add(node.lineno)
                    if isinstance(node, ast.ClassDef) and any(
                            isinstance(base, ast.Name) and base.id == "Protocol" for base in node.bases):
                        for method in node.body:
                            if (isinstance(method, ast.FunctionDef) and method.name == "holidays"
                                    and len(method.body) == 1 and isinstance(method.body[0], ast.Expr)
                                    and isinstance(method.body[0].value, ast.Constant)
                                    and method.body[0].value.value is Ellipsis):
                                neutral_declarations.add(method.lineno)
            for line_no, line in enumerate(text.splitlines(), 1):
                matches = list(PATTERN.finditer(line))
                if line_no in calendar_calls:
                    matches = [m for m in matches if m.group().lower() != "holidays"]
                if line_no in empty_calendars:
                    matches = [m for m in matches if m.group().lower() != "holidays"]
                if line_no in compatibility_fields:
                    matches = [m for m in matches if m.group().lower() != "trase"]
                if matches and line_no not in neutral_declarations:
                    symbol = _symbol(tree, line_no) if tree else "<qml>"
                    counts[(rel, symbol, line.strip())] += 1
    return [{"path": path, "symbol": symbol, "text": text, "count": count}
            for (path, symbol, text), count in sorted(counts.items())]


def key(row: dict) -> tuple:
    return tuple(row[k] for k in ("path", "symbol", "text", "count"))


def compare(actual: list[dict], debts: list[dict]) -> tuple[set, set]:
    a, b = {key(r) for r in actual}, {key(r) for r in debts}
    return a - b, b - a


def within_initial(debts: list[dict], initial: list[dict]) -> bool:
    """Paying one of several identical occurrences is also a subtraction."""
    original = {key(r)[:3]: r["count"] for r in initial}
    return all(key(r)[:3] in original and 0 < r["count"] <= original[key(r)[:3]] for r in debts)


def imports(root: Path = SOURCE) -> list[str]:
    """Only a layer's registry imports its concrete Italian implementation."""
    bad = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        if allowed(rel):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
            names = []
            if isinstance(node, ast.Import):
                names = [n.name for n in node.names]
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level:
                    package = ("meridiana", *rel.parent.parts)
                    module = ".".join((*package[:len(package) - node.level + 1], module)).rstrip(".")
                names = [module + "." + n.name for n in node.names]
            elif isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant):
                if (isinstance(node.func, ast.Name) and node.func.id == "__import__"
                        or isinstance(node.func, ast.Attribute) and node.func.attr == "import_module"):
                    names = [str(node.args[0].value)]
            if any("profiles.it" in n for n in names) and rel.as_posix() not in REGISTRIES:
                bad.append(f"{rel.as_posix()}:{node.lineno}")
    return bad


def core_profile_imports(root: Path = SOURCE) -> list[str]:
    bad = []
    for path in sorted((root / "core/rules/profiles").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
            names = []
            if isinstance(node, ast.Import):
                names = [n.name for n in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [(node.module or "") + "." + n.name for n in node.names]
            for name in names:
                if name.startswith(("meridiana.data.", "meridiana.app.", "meridiana.gui.", "PySide6", "shiboken6")):
                    bad.append(name)
    return bad
