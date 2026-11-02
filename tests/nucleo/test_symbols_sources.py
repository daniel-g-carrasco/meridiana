"""The window's symbols are the only signs of «confirmed, error, warning, information, block» (R330, «armonizziamo»):
the sources hold no character of a font for them in a text of the program (a missing glyph left a box in the place of
the cross, and a character cannot be drawn flat), no Lucide icon for those meanings, and the report draws its marks
from the same tracks as the window, in a module without Qt. A character that is right where it stands (a fallback, a
text that ends in a file) is in ALLOWED, with the reason. No Qt, no display."""

import ast
import re
import unittest
from pathlib import Path

import _setup

SRC = _setup.ROOT / "src" / "meridiana"

# the characters that say a status: ticks, crosses, the warning sign, the no-entry, the info sign, the emoji of them
FORBIDDEN = {chr(c) for c in (*range(0x2713, 0x2719), 0x26A0, 0x26D4, 0x2139, 0x2705, 0x274C, 0x2757, 0x2755, 0x1F6AB,
                              0x24D8, 0x1F6C8, 0x2611, 0x2612, 0x21B6, 0xFE0F)}
# file (relative to src/meridiana) -> why its characters stay
ALLOWED = {
    "ui/symbols.py": "html(): the character when the temporary folder cannot be written, the last resort",
}
# Lucide's icons that say a status: the window's symbols are used for those (icons.py NAMES, icons.icon("..."))
STATUS_ICONS = {"check", "check-check", "circle-check", "circle-check-big", "square-check", "badge-check",
                "triangle-alert", "circle-alert", "octagon-alert", "badge-alert", "circle-x", "octagon-x", "ban",
                "circle-slash", "info", "badge-info", "circle-help", "shield-alert", "shield-check", "shield-x"}


def strings_of(path: Path):
    """The string constants of a Python file, docstrings left out: (line, text)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                docs.add(id(first.value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
            yield node.lineno, node.value


class SymbolsAreTheOnlySigns(unittest.TestCase):
    def test_no_character_of_a_font_says_a_status_in_a_text_of_the_program(self):
        found = []
        for path in sorted(SRC.rglob("*.py")):
            rel = path.relative_to(SRC).as_posix()
            if rel in ALLOWED:
                continue
            for line, text in strings_of(path):
                bad = sorted(set(text) & FORBIDDEN)
                if bad:
                    found.append(f"{rel}:{line}: {' '.join(f'U+{ord(c):04X}' for c in bad)} in {text[:50]!r}")
        # the templates (the report's Typst, Qt Quick) outside the comments
        for pattern in ("*.typ", "*.qml"):
            for path in sorted(SRC.rglob(pattern)):
                for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    code = line.split("//", 1)[0] if "//" in line and "://" not in line else line
                    bad = sorted(set(code) & FORBIDDEN)
                    if bad:
                        found.append(f"{path.relative_to(SRC).as_posix()}:{number}: {bad}")
        self.assertEqual(found, [], "use ui/symbols.py (icon, paint, sign, html), or justify it in ALLOWED")

    def test_the_allowed_files_still_need_their_characters(self):
        for rel in ALLOWED:
            texts = "".join(t for _line, t in strings_of(SRC / rel))
            self.assertTrue(set(texts) & FORBIDDEN, f"{rel} has no such character any more: leave it out of ALLOWED")

    def test_no_lucide_icon_says_a_status(self):
        found = []
        icons_py = ast.parse((SRC / "ui" / "icons.py").read_text(encoding="utf-8"))
        for node in ast.walk(icons_py):
            if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "NAMES" for t in node.targets):
                found += [f"icons.NAMES: {v.value}" for v in node.value.values
                          if isinstance(v, ast.Constant) and v.value in STATUS_ICONS]
        for path in sorted(SRC.rglob("*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "icon"
                        and getattr(node.func.value, "id", "") == "icons" and node.args
                        and isinstance(node.args[0], ast.Constant) and node.args[0].value in STATUS_ICONS):
                    found.append(f"{path.relative_to(SRC).as_posix()}:{node.lineno}: icons.icon({node.args[0].value!r})")
        self.assertEqual(found, [], "a status is a symbol of ui/symbols.py")


class TheReportDrawsTheWindowsSymbols(unittest.TestCase):
    def test_the_shapes_module_has_no_qt(self):
        tree = ast.parse((SRC / "symbol_shapes.py").read_text(encoding="utf-8"))
        modules = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        modules += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        self.assertFalse([m for m in modules if "PySide6" in m or "Qt" in m], modules)

    def test_the_marks_of_the_report_are_the_same_tracks(self):
        from meridiana import symbol_shapes
        marks = symbol_shapes.report_marks()
        self.assertEqual(set(marks), {"ok", "warn", "fail", "info"})
        for level, name in symbol_shapes.LEVEL.items():
            _tone, ground, sign = symbol_shapes.SHAPES[name]
            self.assertIn(ground, marks[level])
            self.assertIn(sign, marks[level])
            self.assertIn(symbol_shapes.FILL_TOKEN, marks[level])          # the report's colour goes there
        self.assertIn(symbol_shapes.TRIANGLE, marks["warn"])               # the warning's triangle, as wide as the disc

    def test_the_template_draws_them_and_no_longer_its_own(self):
        template = (SRC / "report_typst" / "template.typ").read_text(encoding="utf-8")
        mark = template[template.index("#let mark("):template.index("// an image no wider")]
        self.assertIn("D.marks", mark)
        self.assertFalse(re.search(r"\b(polygon|curve|circle|line)\(", mark), "the template draws its own marks again")


if __name__ == "__main__":
    unittest.main()
