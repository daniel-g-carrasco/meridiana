"""Static measures of src/meridiana for theme G of the review (study 18).

Pure standard library, read-only on the repository: lines per file (code, blank, comments, docstrings),
functions and methods longer than 60 lines, classes longer than 500 lines, every `except` with what it
catches and what it does, print/log usage, the import graph (module level and inside functions) with its
cycles, duplicated blocks, user-facing strings without `_()` and gettext literals missing from po/it.po,
public functions of the core without type hints.

Usage: python misure.py <repo root> <output file>
"""

from __future__ import annotations

import ast
import re
import sys
import tokenize
from collections import defaultdict
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Users\utente\dev\meridiana-lavoro")
SRC = ROOT / "src" / "meridiana"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "docs" / "studio" / "18-prove" / "G-misure.txt"
PO = ROOT / "po" / "it.po"
LONG_FUNCTION = 60
LONG_CLASS = 500
DUP_WINDOW = 6          # consecutive normalised code lines that make a duplicated block

lines_out: list[str] = []


def say(text: str = "") -> None:
    lines_out.append(text)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def module_name(path: Path) -> str:
    parts = path.relative_to(SRC.parent).with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


files = sorted(p for p in SRC.rglob("*.py"))
sources = {p: p.read_text(encoding="utf-8") for p in files}
trees = {p: ast.parse(src, filename=str(p)) for p, src in sources.items()}
modules = {module_name(p): p for p in files}


# 1. lines per file

def docstring_lines(tree: ast.AST) -> set[int]:
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                out.update(range(body[0].lineno, body[0].end_lineno + 1))
    return out


def comment_lines(src: str) -> set[int]:
    out: set[int] = set()
    try:
        for tok in tokenize.generate_tokens(iter(src.splitlines(keepends=True)).__next__):
            if tok.type == tokenize.COMMENT:
                line = src.splitlines()[tok.start[0] - 1]
                if line.strip().startswith("#"):
                    out.add(tok.start[0])
    except (tokenize.TokenError, IndentationError):
        pass
    return out


stats = {}
for p, src in sources.items():
    raw = src.splitlines()
    total = len(raw)
    blank = sum(1 for line in raw if not line.strip())
    docs = docstring_lines(trees[p])
    comments = comment_lines(src) - docs
    code = total - blank - len(docs) - len(comments)
    stats[p] = {"total": total, "blank": blank, "doc": len(docs), "comment": len(comments), "code": code}

say("MISURE DI src/meridiana (script misure.py, solo libreria standard, lettura AST)")
say(f"Radice: {ROOT}")
say()
say("1. RIGHE PER FILE (totali / codice / docstring / commenti / vuote)")
say(f"{'file':52} {'tot':>6} {'cod':>6} {'doc':>6} {'com':>6} {'vuo':>6}")
tot = defaultdict(int)
for p in sorted(files, key=lambda q: -stats[q]["total"]):
    s = stats[p]
    say(f"{rel(p):52} {s['total']:6} {s['code']:6} {s['doc']:6} {s['comment']:6} {s['blank']:6}")
    for k, v in s.items():
        tot[k] += v
say(f"{'TOTALE (' + str(len(files)) + ' file)':52} {tot['total']:6} {tot['code']:6} {tot['doc']:6} {tot['comment']:6} {tot['blank']:6}")
core = [p for p in files if "ui" not in p.relative_to(SRC).parts]
ui = [p for p in files if "ui" in p.relative_to(SRC).parts]
say(f"nucleo (senza ui/): {len(core)} file, {sum(stats[p]['total'] for p in core)} righe, "
    f"{sum(stats[p]['code'] for p in core)} di codice")
say(f"ui/: {len(ui)} file, {sum(stats[p]['total'] for p in ui)} righe, {sum(stats[p]['code'] for p in ui)} di codice")
say()


# 2. long functions and classes

functions = []
classes = []
for p, tree in trees.items():
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            n = node.end_lineno - node.lineno + 1
            classes.append((n, rel(p), node.lineno, node.name))
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    sub._qualname = f"{node.name}.{sub.name}"
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            n = node.end_lineno - node.lineno + 1
            functions.append((n, rel(p), node.lineno, getattr(node, "_qualname", node.name)))
functions.sort(reverse=True)
say(f"2. FUNZIONI E METODI OLTRE {LONG_FUNCTION} RIGHE (righe, file:riga, nome); funzioni in tutto: {len(functions)}")
long_functions = [f for f in functions if f[0] > LONG_FUNCTION]
for n, f, line, name in long_functions:
    say(f"  {n:5}  {f}:{line}  {name}")
say(f"  totale: {len(long_functions)} funzioni oltre {LONG_FUNCTION} righe, "
    f"{sum(f[0] for f in long_functions)} righe in tutto")
by_len = defaultdict(int)
for n, *_r in functions:
    by_len["<=20" if n <= 20 else "21-40" if n <= 40 else "41-60" if n <= 60 else "61-100" if n <= 100 else ">100"] += 1
say("  distribuzione: " + ", ".join(f"{k}: {by_len[k]}" for k in ("<=20", "21-40", "41-60", "61-100", ">100")))
say()
classes.sort(reverse=True)
say(f"2b. CLASSI OLTRE {LONG_CLASS} RIGHE (e le 10 piu' lunghe); classi in tutto: {len(classes)}")
for n, f, line, name in classes[:10]:
    flag = "  <-- oltre 500" if n > LONG_CLASS else ""
    say(f"  {n:5}  {f}:{line}  {name}{flag}")
say()


# 3. except clauses

def describe_body(body: list[ast.stmt]) -> tuple[str, bool]:
    """What the handler does, and whether it is silent (nothing said, nothing raised, no log)."""
    text = "\n".join(ast.unparse(s) for s in body)
    silent = True
    kinds = []
    if len(body) == 1 and isinstance(body[0], ast.Pass):
        return "pass", True
    for s in body:
        for node in ast.walk(s):
            if isinstance(node, ast.Raise):
                kinds.append("raise")
                silent = False
            if isinstance(node, ast.Call):
                name = ast.unparse(node.func)
                if name.endswith("log.complain") or name == "complain":
                    kinds.append("log.complain")
                    silent = False
                elif any(name.endswith(x) for x in ("setText", ".warning", ".information", ".question", ".critical",
                                                     "showMessage", ".emit", "hint.emit", ".append", "QMessageBox")):
                    kinds.append("message/signal")
                    silent = False
                elif name == "_" or name.endswith("._"):
                    kinds.append("_()")
                    silent = False
    if not kinds:
        if any(isinstance(s, ast.Return) for s in body):
            kinds.append("return")
        if any(isinstance(s, ast.Continue) for s in body):
            kinds.append("continue")
        if any(isinstance(s, ast.Assign) for s in body):
            kinds.append("assign")
    first = text.splitlines()[0]
    return (", ".join(dict.fromkeys(kinds)) or "other") + " | " + (first[:90] + ("..." if len(first) > 90 else "")), silent


say("3. OGNI `except` (file:riga, cosa cattura, cosa fa; * = tace: niente messaggio, niente log, niente raise)")
handlers = []
for p, tree in trees.items():
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            caught = ast.unparse(node.type) if node.type is not None else "<bare>"
            what, silent = describe_body(node.body)
            handlers.append((rel(p), node.lineno, caught, what, silent))
handlers.sort()
for f, line, caught, what, silent in handlers:
    say(f"  {'*' if silent else ' '} {f}:{line}  except {caught}  ->  {what}")
say(f"  totale: {len(handlers)} except, di cui {sum(1 for h in handlers if h[4])} che tacciono, "
    f"{sum(1 for h in handlers if 'Exception' in h[2] or h[2] == '<bare>')} su Exception/BaseException/nudi")
say()

say("3b. print E LOG")
for p, tree in trees.items():
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = ast.unparse(node.func)
            if name == "print" or name.endswith("log.complain") or name.startswith("logging."):
                say(f"  {rel(p)}:{node.lineno}  {ast.unparse(node)[:110]}")
say()


# 4. imports

def resolve(node: ast.ImportFrom | ast.Import, here: str, is_init: bool) -> list[str]:
    """The meridiana modules an import statement brings in."""
    out = []
    if isinstance(node, ast.Import):
        for a in node.names:
            if a.name.startswith("meridiana"):
                out.append(a.name)
        return out
    if node.level == 0:
        if node.module and node.module.startswith("meridiana"):
            base = node.module
        else:
            return []
    else:
        parts = here.split(".")
        pkg = parts if is_init else parts[:-1]          # the package the module lives in
        pkg = pkg[:len(pkg) - (node.level - 1)] if node.level > 1 else pkg
        base = ".".join(pkg)
        if node.module:
            base = f"{base}.{node.module}"
    for a in node.names:
        cand = f"{base}.{a.name}"
        out.append(cand if cand in modules else base)
    return [m for m in out if m in modules]


top_edges: dict[str, set[str]] = defaultdict(set)
lazy: list[tuple[str, int, str, str]] = []
for p, tree in trees.items():
    here = module_name(p)
    is_init = p.name == "__init__.py"
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for m in resolve(node, here, is_init):
                if m != here:
                    top_edges[here].add(m)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for sub in ast.walk(node):
                if isinstance(sub, (ast.Import, ast.ImportFrom)):
                    for m in resolve(sub, here, is_init):
                        if m != here:
                            lazy.append((here, sub.lineno, m, getattr(node, "_qualname", node.name)))


def reaches(graph, start, goal, seen=None) -> bool:
    seen = seen or set()
    if start == goal:
        return True
    for nxt in graph.get(start, ()):
        if nxt not in seen:
            seen.add(nxt)
            if reaches(graph, nxt, goal, seen):
                return True
    return False


def tarjan(graph):
    _index, stack, on, idx, low, out = {}, [], set(), {}, {}, []
    counter = [0]

    def strong(v):
        idx[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on.add(v)
        for w in graph.get(v, ()):
            if w not in idx:
                strong(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], idx[w])
        if low[v] == idx[v]:
            comp = []
            while True:
                w = stack.pop()
                on.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1 or v in graph.get(v, ()):
                out.append(sorted(comp))
    for v in list(graph):
        if v not in idx:
            strong(v)
    return out


say("4. IMPORT FRA I MODULI DI meridiana")
cycles = tarjan({k: set(v) for k, v in top_edges.items()})
say(f"  archi a livello di modulo: {sum(len(v) for v in top_edges.values())}; cicli a livello di modulo: "
    f"{len(cycles)}" + ("" if not cycles else " -> " + "; ".join(" <-> ".join(c) for c in cycles)))
qt_in_core = []
for p, tree in trees.items():
    if "ui" in p.relative_to(SRC).parts:
        continue
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            if any(n.startswith("PySide6") or n.startswith("shiboken") for n in names):
                qt_in_core.append(f"{rel(p)}:{node.lineno}")
say(f"  Qt importato nel nucleo (fuori da ui/): {', '.join(qt_in_core) if qt_in_core else 'nessuno'}")
ui_to_core = sorted({(a, b) for a, bs in top_edges.items() for b in bs if a.startswith("meridiana.ui") and not b.startswith("meridiana.ui")})
core_to_ui = sorted({(a, b) for a, bs in top_edges.items() for b in bs if not a.startswith("meridiana.ui") and b.startswith("meridiana.ui")})
say(f"  archi nucleo -> ui (non dovrebbero esserci): {core_to_ui if core_to_ui else 'nessuno'}")
say(f"  import dentro funzioni (pigri) verso moduli di meridiana: {len(lazy)}")
fragile = []
for here, line, target, func in lazy:
    # fragile: hoisting it to the module level would make a cycle
    if reaches(top_edges, target, here):
        fragile.append((here, line, target, func))
say(f"  di questi, {len(fragile)} evitano un ciclo (portati in testa al modulo chiuderebbero un ciclo):")
for here, line, target, func in sorted(fragile):
    say(f"    {modules[here].relative_to(ROOT).as_posix()}:{line}  in {func}: importa {target}")
say("  gli altri import pigri (per avvio piu' rapido o per comodita'):")
for here, line, target, func in sorted(set(lazy) - set(fragile)):
    say(f"    {modules[here].relative_to(ROOT).as_posix()}:{line}  in {func}: importa {target}")
say("  moduli con piu' dipendenze interne a livello di modulo:")
for here, deps in sorted(top_edges.items(), key=lambda kv: -len(kv[1]))[:8]:
    say(f"    {here}: {len(deps)} -> {', '.join(sorted(d.replace('meridiana.', '') for d in deps))}")
say()


# 5. duplicated blocks

def normalised(src: str, tree: ast.AST) -> list[tuple[int, str]]:
    docs = docstring_lines(tree)
    out = []
    for i, line in enumerate(src.splitlines(), start=1):
        s = line.strip()
        if not s or s.startswith("#") or i in docs:
            continue
        s = re.sub(r"\s+", " ", s)
        if s in ("else:", "try:", "return", "pass", "continue", "break", ")", "]", "}", "),", "],", "})", "])"):
            continue
        if s.startswith(("import ", "from ")):
            continue
        out.append((i, s))
    return out


windows: dict[tuple, list[tuple[str, int, int]]] = defaultdict(list)
for p, src in sources.items():
    norm = normalised(src, trees[p])
    for k in range(len(norm) - DUP_WINDOW + 1):
        key = tuple(s for _i, s in norm[k:k + DUP_WINDOW])
        if sum(len(s) for s in key) < 120:
            continue
        windows[key].append((rel(p), norm[k][0], norm[k + DUP_WINDOW - 1][0]))

def report_blocks(title: str, wins: dict, source_lines: dict, min_len: int) -> None:
    """Windows that appear in two or more places, chained into blocks: a window is in a block when the
    next window of every place starts one line further on."""
    dups = {key: locs for key, locs in wins.items() if len({(f, a) for f, a, _b in locs}) > 1}
    # index by (file, start line) of the first place
    by_start = {}
    for key, locs in dups.items():
        locs = sorted(set(locs))
        by_start[(locs[0][0], locs[0][1])] = (key, locs)
    used = set()
    blocks = []
    for start in sorted(by_start):
        if start in used:
            continue
        key, locs = by_start[start]
        places = list(locs)
        _ends = [b for _f, _a, b in locs]
        nxt = start
        while True:
            used.add(nxt)
            # the window one normalised line further, in every place
            cand = None
            for s in by_start:
                if s[0] == nxt[0] and s[1] > nxt[1] and s not in used:
                    k2, l2 = by_start[s]
                    if len(l2) == len(places) and all(f2 == f and a < a2 <= b + 1 for (f, a, b), (f2, a2, b2) in zip(places, l2, strict=False)):
                        cand = s
                        break
            if cand is None:
                break
            k2, l2 = by_start[cand]
            _ends = [b for _f, _a, b in l2]
            places = [(f, a, b2) for (f, a, _b), (_f2, _a2, b2) in zip(places, l2, strict=False)]
            nxt = cand
        length = places[0][2] - places[0][1] + 1
        blocks.append((length, places, key))
    blocks.sort(key=lambda b: (-b[0] * len(b[1]), b[1][0]))
    say(f"{title}: finestre doppie {len(dups)}, blocchi {len(blocks)}, di cui mostrati quelli di almeno {min_len} righe")
    shown = 0
    for length, places, _key in blocks:
        if length < min_len:
            continue
        shown += 1
        if shown > 45:
            say("  ...")
            break
        where = "; ".join(f"{f}:{a}-{b}" for f, a, b in places)
        f0, a0, _b0 = places[0]
        first = source_lines[f0][a0 - 1].strip()
        say(f"  ~{length} righe in {len(places)} posti: {where}")
        say(f"      {first[:110]}")


source_lines = {rel(p): src.splitlines() for p, src in sources.items()}
say("5. DUPLICAZIONI")
report_blocks(f"5a. Blocchi identici (finestre di {DUP_WINDOW} righe di codice normalizzate, spazi a parte)", windows,
              source_lines, DUP_WINDOW + 1)

# type-2 clones: the same shape of tokens (names, numbers and strings replaced by placeholders)
import keyword  # noqa: E402

KEEP = {"self", "_", "np", "pd", "Qt"}


def shapes(src: str, tree: ast.AST) -> list[tuple[int, str]]:
    docs = docstring_lines(tree)
    out = {}
    try:
        for tok in tokenize.generate_tokens(iter(src.splitlines(keepends=True)).__next__):
            line = tok.start[0]
            if line in docs or tok.type in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
                                           tokenize.DEDENT, tokenize.ENCODING, tokenize.ENDMARKER):
                continue
            if tok.type == tokenize.NAME:
                s = tok.string if keyword.iskeyword(tok.string) or tok.string in KEEP else "N"
            elif tok.type == tokenize.NUMBER:
                s = "0"
            elif tok.type == tokenize.STRING:
                s = "S"
            else:
                s = tok.string
            out.setdefault(line, []).append(s)
    except (tokenize.TokenError, IndentationError):
        pass
    rows = []
    for line in sorted(out):
        s = " ".join(out[line])
        if s in ("else :", "try :", "return", "pass", "continue", "break", ")", "]", "}", ") ,", "] ,", "} )", "] )",
                 "finally :") or s.startswith(("import ", "from ")) or s in ("N", "N = N"):
            continue
        rows.append((line, s))
    return rows


shape_windows: dict[tuple, list[tuple[str, int, int]]] = defaultdict(list)
W2 = 4
for p, src in sources.items():
    rows = shapes(src, trees[p])
    for k in range(len(rows) - W2 + 1):
        key = tuple(s for _i, s in rows[k:k + W2])
        if sum(len(s) for s in key) < 100 or sum(s.count("N") for s in key) < 8:
            continue
        shape_windows[key].append((rel(p), rows[k][0], rows[k + W2 - 1][0]))
report_blocks(f"5b. Blocchi della stessa forma (nomi, numeri e stringhe sostituiti; finestre di {W2} righe)",
              shape_windows, source_lines, W2 + 1)
say()


# 6. user-facing strings

def po_msgids(path: Path) -> set[str]:
    out, current, inside = set(), None, False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("msgid "):
            current = ast.literal_eval(line[6:].strip())
            inside = True
        elif line.startswith('"') and inside and current is not None:
            current += ast.literal_eval(line.strip())
        elif line.startswith("msgstr") or line.startswith("msgid_plural"):
            if current is not None:
                out.add(current)
            inside = line.startswith("msgid_plural")
            if inside:
                current = ast.literal_eval(line[len("msgid_plural "):].strip())
            else:
                current = None
        elif not line.strip():
            if current is not None:
                out.add(current)
            current, inside = None, False
    if current is not None:
        out.add(current)
    return out


msgids = po_msgids(PO)
say(f"6. TESTI. Voci msgid in po/it.po: {len(msgids)}")

GETTEXT = {"_", "ngettext", "pgettext"}
WIDGET_FUNCS = {"QLabel", "QPushButton", "QCheckBox", "QGroupBox", "QRadioButton", "QAction", "QMenu", "QToolButton",
                "QLineEdit", "QTreeWidgetItem", "QTableWidgetItem", "QListWidgetItem", "QDockWidget", "combo", "Tile",
                "Tiles", "Chart", "Item", "Quantity", "Step", "Source", "Check"}
WIDGET_METHODS = {"setText", "setToolTip", "setStatusTip", "setWindowTitle", "setPlaceholderText", "setTitle", "addTab",
                  "addItem", "addAction", "addMenu", "addRow", "insertRow", "setHeaderLabels", "setHorizontalHeaderLabels",
                  "setVerticalHeaderLabels", "showMessage", "setSpecialValueText", "setSuffix", "setPrefix", "setHtml",
                  "information", "warning", "question", "critical", "about", "getText", "getDouble", "getItem",
                  "getOpenFileName", "getSaveFileName", "setItemText", "setTabText", "setLabel", "set", "message",
                  "setDisplayFormat"}
SKIP = re.compile(r"^(<[^>]*>|[\W\d_]*|[A-Za-z]|F[123]|kWh?p?|kW|m|km|cm|mm|W|V|A|%|°|€|kWh/kWp|€/kWh|kWh/h|kW AC|IT\d+E\d+)$")


def literal_parts(node: ast.AST) -> list[str]:
    """String literals under `node` that are not inside a gettext call and look like words."""
    out = []
    stack = [node]
    while stack:
        n = stack.pop()
        if isinstance(n, ast.Call):
            fname = ast.unparse(n.func)
            if fname in GETTEXT or fname.endswith("._") or fname.endswith("ngettext") or fname.endswith("pgettext"):
                continue
            if fname.endswith(".format"):
                stack.append(n.func.value)
                stack.extend(n.args)
                stack.extend(k.value for k in n.keywords)
                continue
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.append(n.value)
        elif isinstance(n, ast.JoinedStr):
            for v in n.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    out.append(v.value)
                else:
                    stack.append(v)
            continue
        for child in ast.iter_child_nodes(n):
            stack.append(child)
    return [s for s in out if re.search(r"[A-Za-z]{2,}", s) and " " in s.strip() and not SKIP.match(s.strip())
            and not re.fullmatch(r"[A-Za-z]+(\s[A-Z][A-Za-z]*)?", s.strip()) and "font-family" not in s
            and not s.strip().startswith(("<style", "#", "QToolButton", "QPushButton", "text-align", "color:"))]


untranslated = []
for p, tree in trees.items():
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fname = ast.unparse(node.func)
        base = fname.split(".")[-1]
        if not (fname in WIDGET_FUNCS or base in WIDGET_METHODS):
            continue
        for arg in list(node.args) + [k.value for k in node.keywords]:
            for s in literal_parts(arg):
                untranslated.append((rel(p), node.lineno, base, s.strip()))
say(f"6a. STRINGHE PASSATE AI WIDGET SENZA _() (euristica: lettere e uno spazio; file:riga, metodo, testo): {len(untranslated)}")
for f, line, base, s in sorted(set(untranslated)):
    say(f"  {f}:{line}  {base}  {s[:100]!r}")
say()

# gettext literals in the sources against the catalogue
literals = []
for p, tree in trees.items():
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fname = ast.unparse(node.func)
            if fname in ("_", "ngettext", "pgettext") and node.args:
                idx = 1 if fname == "pgettext" else 0
                a = node.args[idx] if len(node.args) > idx else None
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    literals.append((rel(p), node.lineno, a.value))
                else:
                    literals.append((rel(p), node.lineno, None))
missing = [(f, l, s) for f, l, s in literals if s is not None and s not in msgids]
dynamic = [(f, l) for f, l, s in literals if s is None]
say(f"6b. CHIAMATE _()/ngettext/pgettext nei sorgenti: {len(literals)}; con testo non presente in po/it.po "
    f"(restano in inglese nella finestra italiana): {len(missing)}; con argomento non letterale (xgettext non le "
    f"estrae): {len(dynamic)}")
for f, l, s in sorted(missing):
    say(f"  {f}:{l}  {s[:100]!r}")
say("  argomento non letterale:")
for f, l in sorted(dynamic):
    say(f"  {f}:{l}")
say()

# messages raised in the core with literal text
say("6c. ECCEZIONI DEL NUCLEO CON TESTO LETTERALE NON TRADOTTO (raise X('...')), che la finestra mostra come sono")
for p, tree in trees.items():
    if "ui" in p.relative_to(SRC).parts:
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call) and node.exc.args:
            a = node.exc.args[0]
            if isinstance(a, (ast.Constant, ast.JoinedStr)):
                text = ast.unparse(a)
                if re.search(r"[A-Za-z]{3,} [A-Za-z]{2,}", text):
                    say(f"  {rel(p)}:{node.lineno}  {ast.unparse(node.exc)[:110]}")
say()


# 7. type hints in the core

say("7. TYPE HINTS: funzioni e metodi pubblici del nucleo (fuori da ui/) senza annotazione del ritorno o di un parametro")
missing_hints = []
public_total = 0
for p, tree in trees.items():
    if "ui" in p.relative_to(SRC).parts:
        continue
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            public_total += 1
            args = [a for a in node.args.args + node.args.kwonlyargs if a.arg not in ("self", "cls")]
            problems = []
            if node.returns is None and node.name != "__init__":
                problems.append("ritorno")
            problems += [a.arg for a in args if a.annotation is None]
            if problems:
                missing_hints.append((rel(p), node.lineno, getattr(node, "_qualname", node.name), ", ".join(problems)))
say(f"  pubbliche nel nucleo: {public_total}; senza qualche annotazione: {len(missing_hints)}")
for f, l, name, what in sorted(missing_hints):
    say(f"  {f}:{l}  {name}: {what}")
say()

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
print(f"written {OUT} ({len(lines_out)} lines)")
print(f"files {len(files)}, lines {tot['total']}, long functions {len(long_functions)}, excepts {len(handlers)}, "
      f"untranslated widget strings {len(set(untranslated))}, gettext literals missing in po {len(missing)}, "
      f"lazy imports {len(lazy)} (fragile {len(fragile)}), cycles {len(cycles)}")
