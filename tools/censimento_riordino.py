"""Census of the disorder in the Quick interface, for docs/revisioni/piano-riordino-r21.md (07/11/2026).

Read only. Prints, for the QML, the backend, the two interfaces, the tests and the catalogues, the numbers the plan
quotes; `--json` prints them as one object, so a guard can compare them with a ceiling («never more than today»).

    python tools/censimento_riordino.py
    python tools/censimento_riordino.py --json
    python tools/censimento_riordino.py --lines ScrollView      (the lines of one raw control)
"""
from __future__ import annotations

import ast
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUICK = ROOT / "src" / "meridiana" / "quick"
QML = QUICK / "qml" / "Meridiana"
BACKEND = QUICK / "backend"
UI = ROOT / "src" / "meridiana" / "ui"
TESTS = ROOT / "tests"

# Qt Quick controls that have an M. counterpart in Controls/, or should: outside Controls/ they are the raw ones
RAW_CONTROLS = ["ScrollView", "Flickable", "ListView", "GridView", "ComboBox", "Popup", "Menu", "MenuItem", "ToolTip",
                "Dialog", "Button", "ToolButton", "RoundButton", "CheckBox", "Switch", "Slider", "SpinBox", "TextField",
                "TextArea", "TabBar", "TabButton", "Frame", "GroupBox", "Pane", "Label", "ItemDelegate", "RadioButton",
                "SplitView", "Drawer", "BusyIndicator", "ProgressBar", "StackView"]
RAW_RE = re.compile(r"^\s*(?:(?:QQC|QC|QQ|C|T)\.)?(" + "|".join(RAW_CONTROLS) + r")\s*\{")
QT_BAR_RE = re.compile(r"ScrollBar\.vertical:\s*(?:C\.|QQ\.|T\.)?ScrollBar\s*\{")
# a size, a gap or a radius written as a number instead of Theme.space / Theme.size / Theme.radius / ControlMetrics
NUMBER_RE = re.compile(r"^\s*(anchors\.(?:margins|leftMargin|rightMargin|topMargin|bottomMargin)|(?:left|right|top|bottom)?[pP]adding"
                       r"|spacing|radius|implicitHeight|implicitWidth|height|width|font\.pixelSize|border\.width)\s*:\s*(\d+(?:\.\d+)?)\s*$")
HEX_RE = re.compile(r'"#[0-9a-fA-F]{6,8}"')
# an easing written by hand (Easing.OutCubic); easing.type: Theme.motion.EASE is the theme's (F4)
EASING_RE = re.compile(r"easing\.type:.*\bEasing\.")
DURATION_RE = re.compile(r"duration:\s*\d+")
STRING_RE = re.compile(r'"([^"]*)"')
# «•» is not in it: the bullet of a list is typography, text like the «–» of a missing value (regola 4, R21-F3)
ICON_CHARS = set("★☆⌄▾▸▴▿▯✓✔✕✖×⋯⋮⌃⏷⏵➜←→↑↓›‹●○◆◇■□▲▼▶◀⚠ⓘ−")


def qml_files():
    return sorted(set(QML.rglob("*.qml")) | set(QUICK.glob("*.qml")))


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


# r23-f1: a ListView is a raw control only without the program's bar. M.List is the list of texts (MenuItem rows); a
# ListView with a delegate of its own (results, catalogue, checks, tree, plant) stays a ListView with M.ScrollBar
# attached (lane, fades, rebound), or with `interactive: false` when another view moves it (a table's header and totals).
LIST_OK_RE = re.compile(r"ScrollBar\.vertical\s*:\s*(?:M|MC|Controls)\.ScrollBar\b|^\s*interactive:\s*false\b|;\s*interactive:\s*false\b",
                        re.MULTILINE)


def _block(lines: list[str], start: int) -> str:
    """The text of the QML object opened at lines[start], up to its closing brace, without its children's children."""
    depth, out = 0, []
    for line in lines[start:]:
        before = depth
        depth += line.count("{") - line.count("}")
        if before <= 1:
            out.append(line)
        if depth <= 0 and out:
            break
    return "\n".join(out)


def census_qml() -> dict:
    out = {"files": 0, "lines": 0, "controls": 0, "raw": collections.Counter(), "raw_lines": collections.defaultdict(list),
           "qt_bars": [], "numbers": [], "hex": [], "hex_in_controls": [], "easing": [], "duration": [], "unicode": [],
           "shapepath_outside": collections.Counter(), "theme_uses": 0, "metrics_uses": 0, "qstr": 0, "tr": 0, "labels": 0, "texts": 0}
    for path in qml_files():
        r = rel(path)
        in_controls = "/Controls/" in r
        lines = path.read_text(encoding="utf-8").splitlines()
        out["files"] += 1
        out["lines"] += len(lines)
        if in_controls and path.name != "qmldir":
            out["controls"] += 1
        for n, line in enumerate(lines, 1):
            code = line.split("//")[0] if not line.lstrip().startswith("//") else ""
            m = RAW_RE.match(code)
            if m and m.group(1) == "ListView" and LIST_OK_RE.search(_block(lines, n - 1)):
                m = None    # r23-f1, regola 2: a ListView with its own delegate and M.ScrollBar, or moved by another view
            if m and not in_controls:
                out["raw"][m.group(1)] += 1
                out["raw_lines"][m.group(1)].append(f"{r}:{n}")
            if QT_BAR_RE.search(code) and not in_controls:
                out["qt_bars"].append(f"{r}:{n}")
            m = NUMBER_RE.match(code)
            if m and m.group(2) not in ("0", "1"):
                out["numbers"].append(f"{r}:{n}:{m.group(1)} {m.group(2)}")
            if HEX_RE.search(code) and "/Theme/" not in r:
                (out["hex_in_controls"] if in_controls else out["hex"]).append(f"{r}:{n}")
            if EASING_RE.search(code):
                out["easing"].append(f"{r}:{n}")
            if DURATION_RE.search(code):
                out["duration"].append(f"{r}:{n}")
            if "ShapePath" in code and not in_controls:
                out["shapepath_outside"][r] += 1
            for s in STRING_RE.finditer(code):
                text = re.sub(r"\\u([0-9A-Fa-f]{4})", lambda x: chr(int(x.group(1), 16)), s.group(1))
                hit = ICON_CHARS & set(text)
                if hit:
                    out["unicode"].append(f"{r}:{n}:{''.join(sorted(hit))}")
            out["theme_uses"] += code.count("Theme.")
            out["metrics_uses"] += code.count("ControlMetrics.")
            out["qstr"] += code.count("qsTr(")
            out["tr"] += code.count(".tr(")
            out["labels"] += len(re.findall(r"\bL\.\w+", code))
            out["texts"] += len(re.findall(r"\btexts\.\w+", code))
    return out


def _names(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()
    return {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not n.name.startswith("__")}


def _bodies(path: Path) -> dict[str, str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return {}
    return {n.name: ast.dump(ast.Module(body=n.body, type_ignores=[])) for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and len(n.body) >= 4}


def census_backend() -> dict:
    files = sorted(BACKEND.glob("*.py"))
    sizes = {rel(p): len(p.read_text(encoding="utf-8").splitlines()) for p in files}
    text = "".join(p.read_text(encoding="utf-8") for p in files)
    quick_py = sorted(QUICK.rglob("*.py"))
    patterns = {"findChild": r"findChild\w*\(", "setProperty": r"\.setProperty\(", "property_read": r"\.property\(",
                "shiboken": r"shiboken", "isValid": r"isValid\(", "singleShot": r"singleShot\(", "except_exception": r"except Exception",
                "childItems": r"childItems\(\)", "ui_imports": r"(?:from|import)\s+(?:meridiana\.ui|\.\.\.?ui)\b"}
    counts = {}
    for name, rx in patterns.items():
        c = collections.Counter()
        for p in quick_py:
            for line in p.read_text(encoding="utf-8").splitlines():
                if re.search(rx, line):
                    c[rel(p)] += 1
        counts[name] = {"total": sum(c.values()), "files": len(c), "top": c.most_common(4)}
    ui_modules = set()
    for p in quick_py:
        for m in re.finditer(r"(?:from|import)\s+(?:meridiana\.ui|\.\.\.?ui)(?:\.(\w+))?", p.read_text(encoding="utf-8")):
            ui_modules.add(m.group(1) or "(package)")
    # duplicates with the old interface
    ui_bodies = {}
    for p in UI.glob("*.py"):
        for k, v in _bodies(p).items():
            ui_bodies.setdefault((k, v), []).append(p.name)
    identical = []
    for p in files:
        for k, v in _bodies(p).items():
            if (k, v) in ui_bodies:
                identical.append((p.name, ui_bodies[(k, v)][0], k))
    pairs = {}
    for b, u in [("assistant_chat.py", "assistant_chat.py"), ("plan_edit.py", "plan.py"), ("assistant_local.py", "assistant_local.py"),
                 ("checks.py", "checks_page.py"), ("charts_data.py", "charts.py"), ("catalog.py", "catalog_dialog.py")]:
        nb, nu = _names(BACKEND / b), _names(UI / u)
        pairs[f"{b} ~ ui/{u}"] = f"{len(nb & nu)}/{len(nb)}"
    return {"modules": len(files), "lines": sum(sizes.values()), "quick_py_lines": sum(len(p.read_text(encoding='utf-8').splitlines()) for p in quick_py),
            "biggest": sorted(sizes.items(), key=lambda kv: -kv[1])[:12], "classes": len(re.findall(r"^class ", text, re.M)),
            "signals": len(re.findall(r"\bSignal\(", text)), "slots": len(re.findall(r"@Slot\(", text)), "properties": len(re.findall(r"\bProperty\(", text)),
            "patterns": counts, "ui_modules_imported": sorted(ui_modules), "identical_with_ui": identical, "shared_names": pairs}


def census_interfaces() -> dict:
    ui_files = sorted(UI.glob("*.py"))
    ui_lines = {p.stem: len(p.read_text(encoding="utf-8").splitlines()) for p in ui_files}
    needed = set(census_backend()["ui_modules_imported"]) - {"(package)"}
    ui_qml = sorted((UI / "qml").rglob("*.qml")) if (UI / "qml").is_dir() else []
    tools = sorted((ROOT / "tools").glob("*.py"))
    widget_tools = [t.name for t in tools if re.search(r"meridiana\.ui\.(window|view3d|plan)\b|from meridiana\.ui import", t.read_text(encoding="utf-8"))]
    return {"ui_modules": len(ui_files), "ui_lines": sum(ui_lines.values()), "ui_qml_files": len(ui_qml),
            "ui_qml_lines": sum(len(p.read_text(encoding="utf-8").splitlines()) for p in ui_qml),
            "needed_by_quick": len(needed), "needed_lines": sum(ui_lines.get(m, 0) for m in needed),
            "needed_sizes": sorted(((m, ui_lines.get(m, 0)) for m in needed), key=lambda kv: -kv[1]),
            "tools": len(tools), "tools_widgets": len(widget_tools), "tools_quick": sum(1 for t in tools if "quick" in t.name or "meridiana.quick" in t.read_text(encoding="utf-8"))}


def census_tests() -> dict:
    files = sorted(p for p in TESTS.rglob("*.py") if "__pycache__" not in p.parts)
    per = collections.Counter(); perl = collections.Counter(); tests = collections.Counter()
    for p in files:
        r = rel(p).split("/")
        key = "/".join(r[1:3]) if r[1] == "quick" and len(r) > 3 else r[1]
        text = p.read_text(encoding="utf-8")
        per[key] += 1
        perl[key] += len(text.splitlines())
        tests[key] += len(re.findall(r"^\s*def test_", text, re.M))
    patterns = {"qWait": r"qWait\(", "time.sleep": r"time\.sleep\(", "processEvents": r"processEvents\(", "grab": r"\.grab(?:Window|ToImage|Image)?\(",
                "pixel": r"pixel(?:Color)?\(", "keep_global_state": r"keep_global_state", "findChild": r"findChild", "childItems": r"childItems\(\)",
                "skip": r"skip(?:Test|If|Unless)\(", "QT_QPA_PLATFORM": r"QT_QPA_PLATFORM"}
    counts = {}
    for name, rx in patterns.items():
        c = collections.Counter()
        for p in files:
            for line in p.read_text(encoding="utf-8").splitlines():
                if re.search(rx, line):
                    c[rel(p)] += 1
        counts[name] = {"total": sum(c.values()), "files": len(c)}
    no_init = [rel(d) for d in {p.parent for p in files if p.name.startswith("test_")} if not (d / "__init__.py").exists()]
    widget_tests = tests["widget"] + tests["finestra"]
    return {"files": len(files), "lines": sum(perl.values()), "tests": sum(tests.values()), "per_folder": {k: (per[k], perl[k], tests[k]) for k in sorted(per)},
            "widgets_only": {"files": per["widget"] + per["finestra"], "lines": perl["widget"] + perl["finestra"], "tests": widget_tests},
            "quick": {"files": sum(v for k, v in per.items() if k.startswith("quick")), "tests": sum(v for k, v in tests.items() if k.startswith("quick"))},
            "patterns": counts, "dirs_without_init": sorted(no_init),
            "native_files": sum(1 for p in (TESTS / "quick" / "percorsi").glob("*.py") if "native" in p.name)}


def parse_po(path: Path) -> list[dict]:
    entries, cur, field = [], None, None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#~"):
            continue
        if not line.strip():
            if cur:
                entries.append(cur)
            cur = None
            continue
        if cur is None:
            cur = {"msgid": "", "msgstr": "", "msgctxt": None, "refs": [], "flags": []}
        if line.startswith("#:"):
            cur["refs"] += line[2:].split()
            continue
        if line.startswith("#,"):
            cur["flags"] += [f.strip() for f in line[2:].split(",")]
            continue
        if line.startswith("#"):
            continue
        m = re.match(r'^(msgctxt|msgid|msgstr|msgid_plural|msgstr\[\d\]) "(.*)"$', line)
        if m:
            field = {"msgstr[0]": "msgstr", "msgid_plural": "ignore"}.get(m.group(1), m.group(1))
            if field.startswith("msgstr["):
                field = "ignore"
            if field != "ignore":
                cur[field] = (cur.get(field) or "") + m.group(2)
            continue
        m = re.match(r'^"(.*)"$', line)
        if m and field and field != "ignore":
            cur[field] += m.group(1)
    if cur:
        entries.append(cur)
    return [e for e in entries if e["msgid"] or e["msgctxt"]]


def census_po() -> dict:
    out = {}
    for po in sorted((ROOT / "po").rglob("*.po")):     # one catalogue since F7 (po/quick-plan joined po/it.po)
        es = parse_po(po)
        text = po.read_text(encoding="utf-8")
        keys = collections.Counter((e["msgctxt"], e["msgid"]) for e in es)
        out[rel(po)] = {"entries": len(es), "untranslated": sum(1 for e in es if not e["msgstr"]), "fuzzy": sum(1 for e in es if "fuzzy" in e["flags"]),
                        "same_as_msgid": sum(1 for e in es if e["msgstr"] == e["msgid"] and len(e["msgid"]) > 3),
                        "duplicate_keys": sum(1 for v in keys.values() if v > 1), "without_reference": sum(1 for e in es if not e["refs"]),
                        "quick_references": sum(1 for e in es if any("quick" in r for r in e["refs"])),
                        "obsolete": len(re.findall(r"^#~ msgid", text, re.M)),
                        "odd_encoding_lines": sum(1 for l in text.splitlines() if re.search(r"Ã.|â€|Â|�", l))}
        if po.parent == ROOT / "po":
            out[rel(po)].update(check_problems=0, calls_without_entry=0)
    first = rel(ROOT / "po" / "it.po")
    if first in out:
        out[first]["check_problems"] = len(_compile_po().check_all(ROOT))
        out[first]["calls_without_entry"] = len(calls_without_entry(ROOT / "po" / "it.po"))
    return out


def _compile_po():
    import importlib.util
    spec = importlib.util.spec_from_file_location("compile_po", ROOT / "tools" / "compile_po.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def calls_without_entry(po: Path) -> list[str]:
    """The texts src hands to a translation (_, N_, ngettext, pgettext, tr, qsTr) that the catalogue has no entry
    for: in the Italian interface they stay as written (English, or Italian written in the code)."""
    import ast
    ids = {e["msgid"] for e in _compile_po().parse(po.read_text(encoding="utf-8"))}
    out = []
    for p in sorted((ROOT / "src").rglob("*")):
        if p.suffix == ".py":
            for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Call) and node.args:
                    f = node.func
                    name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
                    if name in {"_", "N_", "tr", "ngettext", "pgettext"}:
                        arg = node.args[1] if name == "pgettext" and len(node.args) > 1 else node.args[0]
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            out.append((arg.value, f"{rel(p)}:{node.lineno}"))
        elif p.suffix in (".qml", ".js"):
            text = p.read_text(encoding="utf-8")
            for m in re.finditer(r'\b(?:tr|qsTr)\(\s*(?:"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\')', text):
                s = m.group(1) if m.group(1) is not None else m.group(2)
                if "\\" in s:
                    s = s.encode("utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8")
                out.append((s, f"{rel(p)}:{text.count(chr(10), 0, m.start()) + 1}"))
    return sorted({f"{w}  {s[:70]}" for s, w in out if s not in ids and re.search(r"[A-Za-z]{2}", s)})


def main(argv: list[str]) -> int:
    q = census_qml()
    if "--lines" in argv:
        kind = argv[argv.index("--lines") + 1]
        print("\n".join(q["raw_lines"].get(kind, [])) or "none")
        return 0
    b = census_backend()
    i = census_interfaces()
    t = census_tests()
    p = census_po()
    if "--json" in argv:
        q = dict(q, raw=dict(q["raw"]), raw_lines={k: len(v) for k, v in q["raw_lines"].items()}, shapepath_outside=dict(q["shapepath_outside"]))
        for key in ("numbers", "hex", "hex_in_controls", "easing", "duration", "unicode", "qt_bars"):
            q[key] = len(q[key])
        print(json.dumps({"qml": q, "backend": b, "interfaces": i, "tests": t, "po": p}, indent=1, ensure_ascii=False, default=str))
        return 0
    print(f"QML: {q['files']} file, {q['lines']} righe, {q['controls']} componenti in Controls/")
    print(f"  controlli grezzi di Qt fuori da Controls/: {sum(q['raw'].values())} in {len(set(x.split(':')[0] for v in q['raw_lines'].values() for x in v))} file")
    for k, v in q["raw"].most_common():
        print(f"    {k:12} {v:3}")
    print(f"  barre di scorrimento di Qt (non M.ScrollBar): {len(q['qt_bars'])}")
    print(f"  numeri scritti a mano (misure, spazi, raggi): {len(q['numbers'])} in {len(set(x.split(':')[0] for x in q['numbers']))} file")
    print(f"  colori esadecimali fuori da Theme: {len(q['hex'])} nelle pagine, {len(q['hex_in_controls'])} in Controls/")
    print(f"  easing scritti a mano: {len(q['easing'])}; durate scritte a mano: {len(q['duration'])}")
    print(f"  caratteri Unicode usati come simboli: {len(q['unicode'])}")
    for u in q["unicode"]:
        print(f"    {u}")
    print(f"  ShapePath fuori da Controls/: {sum(q['shapepath_outside'].values())} in {len(q['shapepath_outside'])} file")
    print(f"  usi di Theme.: {q['theme_uses']}, di ControlMetrics.: {q['metrics_uses']}")
    print(f"  testi: backend.tr( {q['tr']}, qsTr( {q['qstr']}, L. {q['labels']}, texts. {q['texts']}")
    print(f"\nBackend: {b['modules']} moduli, {b['lines']} righe (quick/*.py in tutto {b['quick_py_lines']}); {b['classes']} classi, "
          f"{b['signals']} Signal, {b['slots']} Slot, {b['properties']} Property")
    print("  più grandi:", ", ".join(f"{Path(k).name} {v}" for k, v in b["biggest"]))
    for k, v in b["patterns"].items():
        print(f"  {k:16} {v['total']:4} in {v['files']:3} file  {v['top'][:3]}")
    print(f"  moduli di ui importati dalla Quick: {len(b['ui_modules_imported'])}: {', '.join(b['ui_modules_imported'])}")
    print(f"  funzioni identiche backend/ui (4+ istruzioni): {len(b['identical_with_ui'])} {[x[2] for x in b['identical_with_ui']]}")
    print(f"  nomi in comune: {b['shared_names']}")
    print(f"\nInterfacce: ui/ {i['ui_modules']} moduli, {i['ui_lines']} righe + {i['ui_qml_files']} QML ({i['ui_qml_lines']} righe); "
          f"la Quick ne usa {i['needed_by_quick']} moduli, {i['needed_lines']} righe ({round(100 * i['needed_lines'] / i['ui_lines'])} %)")
    print(f"  tools/: {i['tools']} script, {i['tools_widgets']} sui Widgets, {i['tools_quick']} sulla Quick")
    print(f"\nProve: {t['files']} file, {t['lines']} righe, {t['tests']} prove; Widgets (widget + finestra): {t['widgets_only']['files']} file, "
          f"{t['widgets_only']['lines']} righe, {t['widgets_only']['tests']} prove; Quick: {t['quick']['files']} file, {t['quick']['tests']} prove")
    for k, v in t["patterns"].items():
        print(f"  {k:18} {v['total']:4} in {v['files']:3} file")
    print(f"  cartelle di prove senza __init__.py: {t['dirs_without_init'] or 'nessuna'}; file di prove native in percorsi: {t['native_files']}")
    print("\nCataloghi:")
    for k, v in p.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
