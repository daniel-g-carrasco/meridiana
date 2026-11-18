"""Import graph of src/meridiana: for each module, the package modules it imports (top level and inside
functions) and the modules that import it; lines of code (total, non-blank, code without comments);
which modules outside ui/ import PySide6 or shiboken. Output as text, for the review."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("C:/Users/utente/dev/meridiana-lavoro/src/meridiana")
PKG = "meridiana"


def module_name(path: Path) -> str:
    rel = path.relative_to(ROOT).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join([PKG, *parts]) if parts else PKG


def resolve(current: str, node: ast.ImportFrom, is_pkg: bool) -> list[str]:
    """The absolute module names an ImportFrom brings in (package-relative ones resolved)."""
    if node.level == 0:
        base = node.module or ""
    else:
        # the package the module lives in (a package's __init__ is the package itself), then up level - 1
        pkg = current if is_pkg else current.rsplit(".", 1)[0]
        parts = pkg.split(".")
        up = node.level - 1
        parts = parts[: len(parts) - up] if up else parts
        base = ".".join(parts + ([node.module] if node.module else []))
    out = []
    for alias in node.names:
        cand = f"{base}.{alias.name}" if base else alias.name
        out.append((base, cand))
    return out


def main() -> None:
    files = sorted(ROOT.rglob("*.py"))
    names = {module_name(f): f for f in files}
    known = set(names)
    imports: dict[str, set[str]] = {}
    qt: dict[str, list[tuple[int, str]]] = {}
    lines: dict[str, tuple[int, int, int]] = {}
    lazy: dict[str, set[str]] = {}
    for name, path in names.items():
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        is_pkg = path.name == "__init__.py"
        total = src.count("\n") + (0 if src.endswith("\n") else 1)
        non_blank = sum(1 for ln in src.splitlines() if ln.strip())
        code = sum(1 for ln in src.splitlines() if ln.strip() and not ln.strip().startswith("#"))
        lines[name] = (total, non_blank, code)
        deps: set[str] = set()
        deps_lazy: set[str] = set()
        qt_hits: list[tuple[int, str]] = []
        top_level_ids = {id(n) for n in tree.body}
        for node in ast.walk(tree):
            at_top = id(node) in top_level_ids
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in ("PySide6", "shiboken6", "shiboken"):
                        qt_hits.append((node.lineno, alias.name))
                    if alias.name == PKG or alias.name.startswith(PKG + "."):
                        (deps if at_top else deps_lazy).add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if node.level == 0 and mod.split(".")[0] in ("PySide6", "shiboken6", "shiboken"):
                    qt_hits.append((node.lineno, mod))
                if node.level > 0 or mod == PKG or mod.startswith(PKG + "."):
                    for base, cand in resolve(name, node, is_pkg):
                        target = cand if cand in known else base
                        if target in known and target != name:
                            (deps if at_top else deps_lazy).add(target)
                        elif target not in known and base in known and base != name:
                            (deps if at_top else deps_lazy).add(base)
        imports[name] = deps
        lazy[name] = deps_lazy
        qt[name] = qt_hits
    imported_by: dict[str, set[str]] = {n: set() for n in names}
    for n, deps in imports.items():
        for d in deps | lazy[n]:
            imported_by.setdefault(d, set()).add(n)
    grand = (sum(v[0] for v in lines.values()), sum(v[1] for v in lines.values()), sum(v[2] for v in lines.values()))
    print(f"files {len(names)}; lines total {grand[0]}, non-blank {grand[1]}, code (no comment lines) {grand[2]}")
    print()
    for n in sorted(names):
        t, nb, c = lines[n]
        short = n.removeprefix(PKG + ".") or "(package)"
        imps = sorted(x.removeprefix(PKG + ".") for x in imports[n])
        lz = sorted(x.removeprefix(PKG + ".") for x in lazy[n] - imports[n])
        by = sorted(x.removeprefix(PKG + ".") for x in imported_by[n])
        qline = ", ".join(f"{ln}:{m}" for ln, m in qt[n])
        print(f"{short}: {t} lines ({c} code)")
        print(f"  imports: {', '.join(imps) or '-'}")
        if lz:
            print(f"  imports lazily: {', '.join(lz)}")
        print(f"  imported by: {', '.join(by) or '-'}")
        if qline:
            print(f"  Qt: {qline}")
    print()
    print("Qt outside ui/:")
    for n in sorted(names):
        if ".ui" not in n and qt[n]:
            print(f"  {n}: {qt[n]}")
    print()
    print("core modules importing ui:")
    for n in sorted(names):
        if ".ui" not in n:
            bad = [d for d in imports[n] | lazy[n] if ".ui" in d]
            if bad:
                print(f"  {n}: {bad}")
    # cycles among top-level imports
    print()
    print("import cycles (top level):")
    seen = set()

    def dfs(start, node, path):
        for d in imports.get(node, ()):
            if d == start:
                cyc = tuple(path + [d])
                if cyc not in seen:
                    seen.add(cyc)
                    print("  " + " -> ".join(x.removeprefix(PKG + ".") for x in cyc))
            elif d not in path and len(path) < 6:
                dfs(start, d, path + [d])
    for n in sorted(names):
        dfs(n, n, [n])


if __name__ == "__main__":
    main()
