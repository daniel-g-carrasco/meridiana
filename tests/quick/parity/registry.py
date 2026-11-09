"""Source-derived compatibility inventories, without importing the Widgets UI.

The snapshots are a backlog, never proof that a Quick implementation works.
Explicit request references are kept separate from inferred routing suggestions.
"""

from __future__ import annotations

import ast
import csv
import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from meridiana import config, phases, shortcuts

ROOT = Path(__file__).resolve().parents[3]
DESTINATION = ROOT / "docs/quick/compat"
STATES = {"da fare", "in corso", "fatto", "differenza voluta"}
PHASE_IDS = tuple(phases.ids())
REQUEST_RE = re.compile(r"\bR(\d+)\b")

# Editorial routing read against the numbered requests, including short follow-ups
# whose object cannot be recovered from keywords alone. These are plans, not proof.
REQUEST_ROUTES = [
    ("10 25", "plant", "Cataloghi / CatalogDialog: filtri e tutte le righe del catalogo"),
    ("17 20 33 34 47 54 82 88 94 105 106 108 155 156 203 221 258 259 260 288 320 327 332 361 362 363 369 371 386",
     "*", "Meridio / personaggio, fumetto, conversazione e configurazione dei fornitori"),
    ("23 247 285", "production consumption economics", "Risultati / linguette dei grafici, hover e tabelle delle tre pagine"),
    ("24 43 44 68 76 102 206 273 382 383", "*", "Aiuto contestuale / pulsante ?, campo interessato e fumetto di Meridio (R383)"),
    ("28 31 32 37 107 211", "*", "Processo di sviluppo / nessun controllo utente specifico; conservare il vincolo nel lavoro Quick"),
    ("45 59 302 303 354 355 356 357 365", "model plant", "Vista 3D / gizmo, prese dei vertici e modifica numerica delle quote"),
    ("46 73 101", "*", "Barra delle varianti / selettore, nuova variante e confronto"),
    ("50 138 152 154 219 330 384", "*", "Icone e simboli / catalogo centralizzato, pittura e pulsanti di conferma"),
    ("53", "*", "Finestra / Alt apre e richiude la barra dei menu"),
    ("55 100 272 339", "*", "Contenitori scorrevoli / velatura dei bordi e comparsa della barra senza salto"),
    ("30 56 207 256 328 335", "*", "Albero Progetto e Verifiche / simboli, conteggi, filtri e intestazioni"),
    ("69 80 201", "*", "Superfici delle schede / fondi, sfumature, margini e raccordi"),
    ("74 113 253 294 312 317", "*", "Schede laterali / ridimensionamento, trascinamento, aggancio e ripristino"),
    ("83 85 97 159 179 180 277 306 333 364 380 381", "*", "Fasi e barra strumenti / gruppi, pulsanti divisi, linguette e transizioni"),
    ("87 93 135 213 235 241", "*", "Distribuzione / avvio dei pacchetti, piattaforme e aggiornamento della UI Quick"),
    ("90 91 231", "model report", "Modellazione e Relazione / importazione ed esportazione IFC, avanzamento e annullamento"),
    ("110 270 271 290 385", "*", "Ciclo della finestra / apertura, recupero, modifiche pendenti e chiusura"),
    ("96 103 111 112 232 263", "model plant", "Vista 3D / barra del sole, data, calendario e campo angolo"),
    ("116", "plant", "Impianto / annulla e rifai dopo la stringatura manuale"),
    ("122 137 163 214 316 397", "*", "Modello grafico Qt / trasferimento e manutenzione dei componenti condivisi, fuori da un singolo controllo"),
    ("140 166 190", "model plant", "Pianta e 3D / pan, zoom, touchpad e profili di navigazione"),
    ("143 324 336 358", "model plant", "Pianta / etichette delle misure, campi numerici e maniglie di spostamento"),
    ("147 300 344", "plant", "Pianta dell'Impianto / selezione di moduli, file, riquadro e forma libera"),
    ("148 150 198 199 200", "*", "File / Nuovo progetto, anagrafica, indirizzo, coordinate e campi facoltativi"),
    ("165 366 390 395", "*", "Impostazioni Aspetto / carattere Plex, scelta font e applicazione a ogni controllo"),
    ("196 266 309", "production", "Produzione / acquisizione meteo, stato del calcolo e riquadri dei risultati"),
    ("202 261", "model plant", "Pianta / bussola: centro, lettera N, ingombro e ricollocazione"),
    ("209", "*", "Controlli di scelta / elenco popup, dimensione, angoli e bordo"),
    ("212", "*", "File / lettura e scrittura del progetto .mer, risorse e integrità"),
    ("268 307", "plant", "Impianto / scelta automatica inverter, selettore marche e preferiti"),
    ("264 265 293 318 319", "*", "Tour / fumetto di Meridio, salto al passo, sospensione e controllo evidenziato"),
    ("301 326", "model plant", "Pianta / stato dello strumento: Allinea e ritorno a Seleziona con Esc"),
    ("334", "*", "Finestra / disposizione a larghezza ridotta, scala elevata e caratteri grandi"),
    ("348 349 350 351 368 373 374 375 376", "model plant", "Modellazione / selezione, anteprima, posa e geometria degli oggetti 3D"),
    ("372 393", "*", "Prestazioni / cambi fase, ridimensionamento, grafici e gesti continui"),
    ("387", "*", "Integrazione continua / suite Quick e suite dei formati, nessun controllo utente"),
    ("388", "*", "Fascia in basso / testo e combinazioni di tasti per lo strumento corrente"),
    ("389", "*", "Intera applicazione / avvio Quick e confronto di tutte le fasi con Widgets"),
    ("391", "*", "Impostazioni Aspetto / valori predefiniti grey e indigo; conservare le scelte disponibili"),
    ("394", "production consumption economics plant report", "Tabelle / intestazioni, unità, scrollbar, totale fisso e stato vuoto con comando"),
    ("396", "plant production economics", "Barre strumenti / Posa e Calcola senza accento permanente, puntino solo se risultati obsoleti"),
    ("398", "consumption report", "Consumi e Verifiche / import_curve e copy_notes attraverso la pagina caricata pigramente"),
]
REQUEST_DESTINATIONS = {
    f"R{number}": (list(PHASE_IDS) if pids == "*" else pids.split(), page)
    for numbers, pids, page in REQUEST_ROUTES for number in numbers.split()
}

# Each replacement below is stated by Daniel, not inferred from a newer date.
SUPERSESSIONS = {
    "R74": ("R113", "R113 chiede di togliere le linee tratteggiate proposte in R74; resta la cura del ridimensionamento"),
    "R328": ("R335", "La scelta P5 dei conteggi è cambiata in P3 da R335; restano leggibilità e simboli condivisi"),
    "R382": ("R383", "Il pannello Aiuto viene sostituito dal fumetto di Meridio; resta il requisito di non coprire Proprietà"),
}
INTENDED_DIFFERENCES = {
    "preference:font": ("R390", "Il valore iniziale passa da Inter a Plex; la barra usa Plex Condensed. Tutte le scelte restano disponibili."),
    "preference:backgrounds": ("R391", "Il fondo iniziale del tema chiaro passa da meridiana a grey; restano tutti i fondi."),
    "preference:accent": ("R391", "L'accento iniziale passa da bronze a indigo; restano tutti gli accenti."),
    "phase_command:plant/modules/fill": ("R396", "Posa perde l'accento permanente; puntino solo con uno stato obsoleto accertato."),
    "phase_command:production/compute/compute": ("R396", "Calcola perde l'accento permanente; puntino solo con uno stato obsoleto accertato."),
    "phase_command:economics/compute/compute": ("R396", "Calcola perde l'accento permanente; puntino solo con uno stato obsoleto accertato."),
}
# Widgets commands added after the native references in docs/quick/compat/riferimento were captured (tools/quick_rif.py
# opens real Direct3D windows: never on Daniel's desktop while he works). Not hidden: each is named here with its
# reason, validate_runtime_commands fails when the command leaves window.py, and test_registry when a recorded capture
# has it (the entry must then go). The next capture run brings them in.
CAPTURED_BEFORE = {
    "export_dxf": "R513 (r20-dxf, 07/11/2026): the plan as DXF, after the captures of 04/11/2026",
}


def source(path: Path) -> tuple[str, ast.Module]:
    text = path.read_text(encoding="utf-8-sig")
    return text, ast.parse(text)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def reference(path: Path, node: ast.AST) -> str:
    return f"{path.relative_to(ROOT).as_posix()}:{node.lineno}"


def leaf(node: ast.AST) -> str:
    return node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else ""


def expr(node: ast.AST | None) -> str:
    return ast.unparse(node) if node is not None else ""


def literal(node: ast.AST, env: dict | None = None):
    """Evaluate only the data expressions used by window._actions, never UI code."""
    env = env or {}
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.Tuple, ast.List)):
        return [literal(part, env) for part in node.elts]
    if isinstance(node, ast.Name):
        return env.get(node.id)
    if isinstance(node, ast.Attribute):
        value = literal(node.value, env)
        return getattr(value, node.attr, None) if value is not None else None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = literal(node.left, env), literal(node.right, env)
        return left + right if isinstance(left, str) and isinstance(right, str) else None
    if isinstance(node, ast.JoinedStr):
        values = [literal(v.value, env) if isinstance(v, ast.FormattedValue) else literal(v, env)
                  for v in node.values]
        return "".join(map(str, values)) if None not in values else None
    if isinstance(node, ast.Call):
        if leaf(node.func) == "_" and node.args:
            return literal(node.args[0], env)
        if expr(node.func) == "phases.phases":
            return phases.phases()
    return None


def window_commands() -> dict[str, dict]:
    """Expand the literal loops that register MainWindow.commands.

    An unhandled dynamic registration raises rather than silently disappearing.
    The separate runtime parity test may compare this set to window.commands.
    """
    path = ROOT / "src/meridiana/ui/window.py"
    _text, tree = source(path)
    method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_actions")
    result = {}

    def bind(target, value, env):
        if isinstance(target, ast.Name):
            env[target.id] = value
        elif isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (list, tuple)):
            for part, item in zip(target.elts, value, strict=True):
                bind(part, item, env)

    def walk(node, env):
        if isinstance(node, (ast.FunctionDef, ast.Lambda)):
            return
        if isinstance(node, ast.For) and any(isinstance(n, ast.Call) and leaf(n.func) == "act"
                                            for n in ast.walk(node)):
            values = literal(node.iter, env)
            if values is None:
                raise ValueError(f"Unresolved command loop: {reference(path, node)}")
            for value in values:
                nested = dict(env)
                bind(node.target, value, nested)
                for child in node.body:
                    walk(child, nested)
            return
        if isinstance(node, ast.Call) and leaf(node.func) == "act":
            command = literal(node.args[1], env)
            if not isinstance(command, str):
                raise ValueError(f"Unresolved command: {reference(path, node)}")
            result[command] = {"source": reference(path, node), "menu": expr(node.args[0]),
                               "handler": expr(node.args[2])}
        for child in ast.iter_child_nodes(node):
            walk(child, env)

    for statement in method.body:
        walk(statement, {})
    return result


def route(text: str) -> tuple[list[str], str]:
    """Conservative, explicitly inferred routing for the migration backlog."""
    text = text.casefold()
    rules = [
        (("meridio", "assistent", "assistant", "fumetto", "voce", "llama", "kokoro"), PHASE_IDS, "Meridio / conversazione e impostazioni"),
        (("relazione", "report", "firma", "typst", "pdf"), ("report",), "Relazione / anteprima, firma ed esportazione"),
        (("consum", "load_curve", "load curve"), ("consumption",), "Consumi / profilo, curva e grafici"),
        (("econom", "cash", "payback", "bollett", "balance"), ("economics",), "Bilancio ed economia / risultati e grafici"),
        (("inverter", "string", "impianto", "plant", "storage", "accumulo", "battery", "optimizer", "ottimizz"), ("plant",), "Impianto / moduli, inverter, stringhe e accumulo"),
        (("energi", "energy", "production", "produzione", "calcol", "pvgis", "irradi", "losses"), ("production",), "Produzione / calcolo, meteo e risultati"),
        (("propriet", "properties", "inspector"), ("model", "plant"), "Proprietà / scheda dell'oggetto selezionato"),
        (("verific", "checks"), PHASE_IDS, "Verifiche / elenco, raggruppamento e correzioni"),
        (("file", "salva", "save", "revision", "apertura", "backstage"), PHASE_IDS, "File / apertura, salvataggio e revisioni"),
        (("impostaz", "preferen", "font", "caratter", "tema", "theme", "appearance", "colore"), PHASE_IDS, "Impostazioni / aspetto e preferenze"),
        (("3d", "orbita", "cubo", "camera", "pivot", "sole", "sun"), ("model", "plant"), "Viste / 3D, sole e navigazione"),
        (("pianta", "plan", "tett", "roof", "building", "edific", "canop", "pensilin", "map", "snap", "orto", "disegn"), ("model", "plant"), "Modellazione e Impianto / pianta e strumenti"),
        (("tooltip", "pulsant", "button", "toolbar", "barr", "sched", "dock", "menu", "shortcut", "scorciato", "phase", "fasi", "transizion", "linguett", "simbol", "icone"), PHASE_IDS, "Finestra / fasi, barre, pannelli e controlli"),
    ]
    for words, pids, page in rules:
        if any(word in text for word in words):
            return list(pids), page
    return list(PHASE_IDS), "Trasversale / integrazione, distribuzione o processo: verificare la richiesta originale"


def validate_runtime_commands(manifest: dict) -> list[str]:
    """Compare actual captured QActions with both independent source definitions."""
    actual = set(manifest.get("commands", {}))
    expected = set(window_commands())
    errors = [f"Runtime commands missing: {key}" for key in sorted(expected - actual - set(CAPTURED_BEFORE))]
    errors.extend(f"Captured before, no longer a window command: {key}" for key in sorted(set(CAPTURED_BEFORE) - expected))
    errors.extend(f"Runtime commands not inventoried: {key}" for key in sorted(actual - expected))
    declared = {c.id for c in shortcuts.commands()}
    errors.extend(f"Shortcut command not registered in window: {key}" for key in sorted(declared - expected))
    errors.extend(f"Window command missing shortcut definition: {key}" for key in sorted(expected - declared))
    for command in shortcuts.commands():
        if command.id in actual:
            keys = manifest["commands"][command.id].get("shortcuts", [])
            if set(keys) != set(command.keys):
                errors.append(f"Runtime shortcut differs: {command.id}: {keys!r} != {list(command.keys)!r}")
    return errors


def runtime_manifests() -> list[tuple[Path, dict]]:
    return [(path, json.loads(gzip.decompress(path.read_bytes())))
            for path in sorted((DESTINATION / "riferimento").rglob("manifest.json.gz"))]


def inventory() -> list[dict]:
    rows = []

    def add(kind, key, title, sources, pids=None, **details):
        rows.append({"id": f"{kind}:{key}", "kind": kind, "title": title,
                     "phases": list(pids) if pids is not None else route(title + " " + key)[0],
                     "sources": sources, **details})

    registered = window_commands()
    commands = {command.id: command for command in shortcuts.commands()}
    for key in sorted(set(registered) | set(commands)):
        command = commands.get(key)
        pids = [p.id for p in phases.phases() if key in p.commands()]
        info = registered.get(key, {})
        add("command", key, command.text if command else key,
            [info["source"]] if info else ["src/meridiana/shortcuts.py"], pids or PHASE_IDS,
            registered_in_window=key in registered, **{k: v for k, v in info.items() if k != "source"})
        if command:
            add("shortcut", key, command.text, ["src/meridiana/shortcuts.py"], pids or PHASE_IDS,
                keys=list(command.keys), command=key, group=command.group)
    for phase in phases.phases():
        add("phase", phase.id, phase.title, ["src/meridiana/phases.py"], [phase.id], inspector=phase.inspector)
        for group in phase.groups:
            add("section", f"phase/{phase.id}/{group.id}", group.title,
                ["src/meridiana/phases.py"], [phase.id])
            for tool in group.every():
                add("phase_command", f"{phase.id}/{group.id}/{tool.command}", tool.label or tool.command,
                    ["src/meridiana/phases.py"], [phase.id], command=tool.command, planned=tool.planned,
                    primary=tool.primary, fixed=tool.fixed, danger=tool.danger)

    defaults = config.Config().to_json()
    for key, value in defaults.items():
        if key != "version":
            add("preference", key, key, ["src/meridiana/config.py"], default=value)

    for path in sorted((ROOT / "src/meridiana/ui").glob("*.py")):
        text, tree = source(path)
        counts = Counter()

        def visit(node, scope="module", *, path=path, counts=counts):
            if isinstance(node, ast.ClassDef):
                scope = node.name
                bases = [leaf(b) for b in node.bases]
                kind = "dialog" if any("Dialog" in b for b in bases) else (
                    "page" if "Page" in node.name or any("Page" in b for b in bases) or
                    node.name in {"Properties", "Preferences", "Inspector", "PlantInspector", "StorageInspector",
                                  "ReportInspector", "Appearance", "ProjectTree", "Assistant"} else None)
                if kind:
                    add(kind, f"{path.stem}/{node.name}", node.name, [reference(path, node)],
                        description=ast.get_docstring(node) or "", bases=bases)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                scope = f"{scope}.{node.name}"
                if path.stem == "properties" and node.name.startswith("show_") and scope.startswith("Properties."):
                    add("page", f"properties/{scope}", scope, [reference(path, node)],
                        description=ast.get_docstring(node) or "")
            if isinstance(node, ast.Call):
                name = leaf(node.func)
                kind = None
                if name in {"QMenu", "addMenu", "plain_action", "addAction"}:
                    kind = "menu"
                elif name in {"Section", "Group", "ResultCard", "PlantSection", "section", "addTab", "_page"}:
                    kind = "section"
                elif name in {"QShortcut", "setShortcut", "setShortcuts"}:
                    kind = "local_shortcut"
                elif isinstance(node.func, ast.Attribute) and leaf(node.func.value) in {
                        "QFileDialog", "QMessageBox", "QInputDialog", "QColorDialog", "QFontDialog"}:
                    kind = "dialog_call"
                if kind:
                    # Scope plus occurrence stays stable when unrelated lines are inserted.
                    counts[(scope, name)] += 1
                    key = f"{path.stem}/{scope}/{name}/{counts[(scope, name)]}"
                    label = next((literal(a) for a in node.args if isinstance(literal(a), str)), expr(node))
                    add(kind, key, label, [reference(path, node)], expression=expr(node),
                        source_hash=digest(ast.dump(node, include_attributes=False)))
            if isinstance(node, ast.Attribute) and node.attr.startswith("Key_"):
                key = f"{path.stem}/{scope}/{node.attr}"
                if not any(row["id"] == f"key_handler:{key}" for row in rows):
                    add("key_handler", key, expr(node), [reference(path, node)],
                        context=scope, note="Tasto gestito localmente; verificare contesto, focus e conflitti nel nuovo controllo")
            for child in ast.iter_child_nodes(node):
                visit(child, scope)

        visit(tree)
        if path.name == "preferences.py":
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and any(leaf(t) == "SECTIONS" for t in node.targets):
                    for key, values in zip(node.value.keys, node.value.values, strict=True):
                        add("section", f"preferences/{literal(key)}", literal(key), [reference(path, node)],
                            fields=literal(values))
    return sorted(rows, key=lambda row: row["id"])


def load_registry(path: Path | None = None) -> dict:
    return json.loads((path or DESTINATION / "parita.json").read_text(encoding="utf-8"))


def _safe_file(value: str) -> Path:
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError(f"Missing or external evidence: {value}")
    return path


def validate_evidence(row: dict) -> list[str]:
    errors, kinds = [], set()
    for proof in row.get("evidence", []):
        try:
            path = _safe_file(proof.get("path", ""))
            if proof.get("sha256") != hashlib.sha256(path.read_bytes()).hexdigest():
                raise ValueError("Evidence hash is missing or stale")
            kind = proof.get("kind")
            if kind == "test":
                if "registry" in path.stem:
                    raise ValueError("Inventory tests do not prove UI parity")
                _text, tree = source(path)
                symbol = proof.get("symbol", "")
                found = [method for cls in tree.body if isinstance(cls, ast.ClassDef)
                         for method in cls.body if isinstance(method, ast.FunctionDef)
                         and f"{cls.name}.{method.name}" == symbol and method.name.startswith("test_")]
                if not found or not any(isinstance(n, ast.Assert) or isinstance(n, ast.Call)
                                        and leaf(n.func).startswith("assert") for n in ast.walk(found[0])):
                    raise ValueError("Evidence is not an asserting test method")
                report = json.loads(_safe_file(proof.get("run", "")).read_text(encoding="utf-8"))
                case = next((c for c in report.get("cases", []) if c.get("symbol") == symbol
                             and c.get("path") == proof["path"]), None)
                if not case or case.get("result") != "passed" or case.get("sha256") != proof["sha256"]:
                    raise ValueError("No passing run for this exact test source")
                if row["id"] not in case.get("parity_ids", []):
                    raise ValueError("Run does not identify the behavior it proves")
            elif kind == "visual":
                if path.suffix.lower() not in {".png", ".jpg", ".webp"} or not proof.get("reviewed_by"):
                    raise ValueError("A reviewed screenshot is required")
                _safe_file(proof.get("comparison", ""))
            else:
                raise ValueError("Unknown evidence kind")
            kinds.add(kind)
        except (OSError, ValueError, KeyError, TypeError) as error:
            errors.append(f"{row['id']}: {error}")
    if row.get("status") == "fatto" and not {"test", "visual"} <= kinds:
        errors.append(f"{row['id']}: fatto requires a passing behavior test and reviewed visual comparison")
    return errors


def validate(document: dict, current: list[dict] | None = None) -> list[str]:
    current = inventory() if current is None else current
    expected = {row["id"]: row for row in current}
    rows = document.get("items", [])
    actual = {row["id"]: row for row in rows}
    errors = []
    if len(actual) != len(rows):
        errors.append("Duplicate parity identifiers")
    errors.extend(f"New source item missing from registry: {key}" for key in sorted(expected.keys() - actual.keys()))
    errors.extend(f"Registered source item disappeared: {key}" for key in sorted(actual.keys() - expected.keys()))
    for key in expected.keys() & actual.keys():
        row = actual[key]
        for field, value in expected[key].items():
            if row.get(field) != value:
                errors.append(f"{key}: source field changed: {field}")
        if row.get("status") not in STATES:
            errors.append(f"{key}: invalid status")
        if row.get("status") == "differenza voluta":
            if not (row.get("reason") and row.get("decision")):
                errors.append(f"{key}: intended difference needs a reason and a decision reference")
            else:
                try:
                    decision_path, marker = row["decision"].split("#", 1)
                    if not marker or marker not in _safe_file(decision_path).read_text(encoding="utf-8"):
                        raise ValueError("Decision marker missing from the cited source")
                except (OSError, ValueError) as error:
                    errors.append(f"{key}: invalid decision reference: {error}")
        errors.extend(validate_evidence(row))
    if "completion" in document and document["completion"] != completion(document):
        errors.append("Completion summary is stale: refresh the derived percentages")
    return errors


def completion(document: dict) -> dict:
    result = {}
    for pid in PHASE_IDS:
        relevant = [r for r in document["items"] if pid in r["phases"]]
        done = sum(r["status"] == "fatto" and not validate_evidence(r) for r in relevant)
        states = dict(Counter(r["status"] for r in relevant))
        result[pid] = {"total": len(relevant), "done": done, "percent": round(100 * done / len(relevant), 2)
                       if relevant else 0, "states": states}
    return result


def request_sources() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    refs = defaultdict(list)
    controls = defaultdict(list)
    for base in (ROOT / "src/meridiana", ROOT / "tests/widget", ROOT / "tests/finestra"):
        for path in sorted(base.rglob("*.py")):
            text, tree = source(path)
            contexts = []

            def context(node, prefix="", *, contexts=contexts):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    prefix = f"{prefix}.{node.name}".strip(".")
                    contexts.append((node.lineno, node.end_lineno, prefix))
                for child in ast.iter_child_nodes(node):
                    context(child, prefix)

            context(tree)
            for number, line in enumerate(text.splitlines(), 1):
                for value in REQUEST_RE.findall(line):
                    rid = f"R{value}"
                    ref = f"{path.relative_to(ROOT).as_posix()}:{number}"
                    refs[rid].append(ref)
                    containing = [(end - start, name) for start, end, name in contexts if start <= number <= end]
                    symbol = min(containing)[1] if containing else "module"
                    controls[rid].append(f"{ref}#{symbol}")
    return refs, controls


def request_rows() -> list[dict]:
    (refs, controls), rows = request_sources(), []
    occurrences = Counter()
    path = ROOT / "docs/richieste.md"
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not re.match(r"\| R\d+ \|", line):
            continue
        # The later table has no date. An inline code pipe (`--tour [step|new]`)
        # is content, not a cell delimiter; extra editorial columns are preserved.
        parts = [part.strip() for part in line.strip().strip("|").split(" | ")]
        if re.fullmatch(r"\d{1,2}/\d{1,2}(?:/\d{2,4})?", parts[1]):
            rid, date, request, state = parts[:4]
            where = " | ".join(parts[4:])
        else:
            rid, request, state = parts[:3]
            date, where = "", " | ".join(parts[3:])
        occurrences[rid] += 1
        pids, page = REQUEST_DESTINATIONS.get(rid, route(request))
        explicit = refs.get(rid, [])
        superseded = re.findall(r"(?:superat[oaie]|sostituit[oaie])[^.;]{0,180}?\b(R\d+)\b", state, re.I)
        applies = "superata" if superseded else "resta valida"
        if any(word in state.casefold() for word in ("superato", "superata", "sostituita")) and not superseded:
            applies = "da verificare: stato storico indica superamento senza R univoca"
        applicability_note = "[I] il requisito resta nel perimetro salvo sostituzioni esplicite; verificare i dettagli nel test Quick"
        if rid in SUPERSESSIONS:
            superseded = [SUPERSESSIONS[rid][0]]
            applies = "parzialmente superata"
            applicability_note = "[V] " + SUPERSESSIONS[rid][1]
        if rid in {"R28", "R31", "R32", "R37", "R107", "R211"}:
            applies = "resta valida come vincolo di processo, nessun controllo Quick dedicato"
            applicability_note = "[V] la richiesta riguarda strumenti, metodo o decisioni di sviluppo"
        behavior = re.sub(r"\s+", " ", request).strip()
        rows.append({"row_id": f"{rid}/{occurrences[rid]}", "request": rid, "date": date,
                     "source": f"docs/richieste.md:{number}",
                     "source_hash": digest(line), "request_summary": behavior,
                     "page_control": page, "phases": ";".join(pids),
                     "mapping_basis": ("[I] destinazione assegnata leggendo la richiesta e i suoi seguiti; non prova di implementazione"
                                       if rid in REQUEST_DESTINATIONS else
                                       "[I] destinazione proposta dal contenuto; riferimenti R espliciti separati"),
                     "applies": applies, "superseded_by": ";".join(dict.fromkeys(superseded)),
                     "applicability_note": applicability_note,
                     "widgets_status": state, "widgets_references": where,
                     "explicit_source_references": ";".join(explicit),
                     "explicit_source_controls": ";".join(dict.fromkeys(controls.get(rid, []))),
                     "quick_status": "da fare", "quick_test": "", "parity_ids": "",
                     "quick_verification_plan": (
                         f"{rid}: riprodurre il comportamento «{behavior}» in {page}; "
                         "stessa fixture e stessi gesti su Widgets e Quick; confrontare stato, undo e output pertinenti; "
                         "foto chiaro/scuro a scala 1 e 2 per gli aspetti visivi. Il test Quick specifico resta da scrivere."),
                     "notes": "[V] riga e riferimenti espliciti censiti; [I] destinazione e applicabilità da revisione semantica, non prova di parità."})
    return rows


def test_rows() -> list[dict]:
    rows = []
    for group in ("widget", "finestra"):
        for path in sorted((ROOT / "tests" / group).glob("test*.py")):
            text, tree = source(path)
            module_doc = ast.get_docstring(tree) or ""
            for cls in tree.body:
                if not isinstance(cls, ast.ClassDef):
                    continue
                for method in cls.body:
                    if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) or not method.name.startswith("test"):
                        continue
                    segment = ast.get_source_segment(text, method) or ""
                    assertions = [expr(n) for n in ast.walk(method) if isinstance(n, ast.Assert)
                                  or isinstance(n, ast.Call) and leaf(n.func).startswith("assert")]
                    interactions = sorted({leaf(n.func) for n in ast.walk(method) if isinstance(n, ast.Call)
                                           and leaf(n.func) in {"mouseClick", "mouseMove", "mousePress", "mouseRelease",
                                                                "keyClick", "keyClicks", "sendEvent", "grab", "pixelColor",
                                                                "trigger", "setValue", "setCurrentIndex"}})
                    refs = sorted({f"R{r}" for r in REQUEST_RE.findall(segment)}, key=lambda s: int(s[1:]))
                    pids, page = route(f"{path.stem} {cls.name} {method.name} {ast.get_docstring(method) or ''}")
                    visual = any(word in segment for word in (".grab(", "pixelColor", "QImage", "screenshot"))
                    portability = ("adattare i gesti al QQuickWindow e i selettori agli objectName" if group == "finestra"
                                   else "sostituire il widget con il controllo QML, conservare il contratto osservabile")
                    if visual:
                        portability += "; rifare la misura in pixel logici e mantenere la soglia motivata"
                    if any(word in segment for word in ("read_text(", "getsource(", "ast.parse(")):
                        portability = "riscrivere il controllo statico sui sorgenti Quick pertinenti; conservare il vincolo architetturale, non i nomi Widgets"
                    rows.append({"test": f"{group}.{path.stem}.{cls.name}.{method.name}", "source": reference(path, method),
                                 "source_hash": digest(segment), "group": group, "class": cls.name,
                                 "behavior": ast.get_docstring(method) or method.name.removeprefix("test_").replace("_", " "),
                                 "module_contract": " ".join(module_doc.split()), "assertions": " ; ".join(assertions),
                                 "interactions": ";".join(interactions), "requests_explicit": ";".join(refs),
                                 "page_control": page, "phases": ";".join(pids),
                                 "portability": portability, "quick_replacement": "", "parity_ids": "", "status": "da fare",
                                 "verification_plan": f"Portare {cls.name}.{method.name}; conservare gli assert sul comportamento, "
                                 "sostituire solo dettagli Widgets. Confrontare con il riferimento sulla medesima fixture.",
                                 "notes": "[V] metodo e assert letti da AST; [I] strategia di portabilità, non ancora provata."})
    return rows


def read_csv(name: str) -> list[dict]:
    with (DESTINATION / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_csv_inventories() -> list[str]:
    errors = []
    parity = {row["id"]: row for row in load_registry()["items"]}
    for name, make_rows, key in (("richieste.csv", request_rows, "row_id"), ("prove.csv", test_rows, "test")):
        expected = {row[key]: row for row in make_rows()}
        rows = read_csv(name)
        actual = {row[key]: row for row in rows}
        if len(actual) != len(rows):
            errors.append(f"{name}: duplicate identifiers")
        for missing in sorted(expected.keys() - actual.keys()):
            errors.append(f"{name}: missing {missing}")
        for removed in sorted(actual.keys() - expected.keys()):
            errors.append(f"{name}: disappeared {removed}")
        for item in expected.keys() & actual.keys():
            if actual[item]["source_hash"] != expected[item]["source_hash"]:
                errors.append(f"{name}: source changed for {item}")
            source_fields = ("source", "request_summary", "widgets_status", "widgets_references") if key == "row_id" else (
                "source", "behavior", "assertions")
            for field in source_fields:
                if actual[item].get(field) != expected[item][field]:
                    errors.append(f"{name}: {item}: source content differs in {field}")
            for field in ("page_control", "verification_plan" if key == "test" else "quick_verification_plan"):
                if not actual[item].get(field):
                    errors.append(f"{name}: {item} has no {field}")
            state = actual[item].get("status" if key == "test" else "quick_status")
            if state not in STATES:
                errors.append(f"{name}: {item} has invalid status")
            if state == "fatto":
                ids = [value for value in actual[item].get("parity_ids", "").split(";") if value]
                if not ids or any(pid not in parity or parity[pid]["status"] != "fatto"
                                  or validate_evidence(parity[pid]) for pid in ids):
                    errors.append(f"{name}: {item}: link verified parity IDs before marking this inventory done")
    return errors


def write_initial_or_refresh(*, refresh: bool = False) -> dict:
    """Refresh source snapshots while retaining the separately maintained work states."""
    DESTINATION.mkdir(parents=True, exist_ok=True)
    target = DESTINATION / "parita.json"
    if target.exists() and not refresh:
        raise FileExistsError("Registry exists: inspect changes and use --refresh explicitly")
    previous = {r["id"]: r for r in load_registry()["items"]} if target.exists() else {}
    rows = []
    for row in inventory():
        old = previous.get(row["id"], {})
        updated = {**row, "status": old.get("status", "da fare"), "evidence": old.get("evidence", []),
                   "reason": old.get("reason", ""), "decision": old.get("decision", "")}
        if row["id"] in INTENDED_DIFFERENCES and updated["status"] == "da fare":
            rid, reason = INTENDED_DIFFERENCES[row["id"]]
            updated.update(status="differenza voluta", reason=reason,
                           decision=f"docs/quick/CONTESTO.md#{rid}")
        rows.append(updated)
    # A refresh may add items, but cannot quietly erase a removed behavior.
    current_ids = {row["id"] for row in rows}
    rows.extend(row for key, row in previous.items() if key not in current_ids)
    document = {"schema": 1, "scope": "Parità Quick rispetto ai sorgenti Widgets: inventario statico, non collaudo",
                "completion_rule": "fatto solo con test comportamentale eseguito e confronto visivo rivisto; differenze volute separate",
                "routing": "Fasi ricavate da phases.py per i comandi; destinazioni di superfici e richieste inferite e da affinare",
                "items": rows}
    document["completion"] = completion(document)
    target.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for name, make_rows in (("richieste.csv", request_rows), ("prove.csv", test_rows)):
        output = make_rows()
        csv_path = DESTINATION / name
        if csv_path.exists():
            # CSV routing and migration notes are editorial; preserve them on refresh.
            key = "row_id" if name == "richieste.csv" else "test"
            previous_csv = {r[key]: r for r in read_csv(name)}
            editable = ("page_control", "applies", "superseded_by", "mapping_basis", "quick_test", "quick_status", "parity_ids",
                        "quick_verification_plan", "notes") if key == "row_id" else (
                            "page_control", "portability", "quick_replacement", "parity_ids", "status", "verification_plan", "notes")
            for row in output:
                old = previous_csv.get(row[key], {})
                for field in editable:
                    if field in old:
                        if key == "row_id" and field not in {"quick_status", "quick_test", "parity_ids"} and old.get("mapping_basis", "").startswith("[I]"):
                            continue
                        row[field] = old[field]
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(output[0]))
            writer.writeheader()
            writer.writerows(output)
    return document
