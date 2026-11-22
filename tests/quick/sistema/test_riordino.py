"""Guard of the reordering of the Quick (docs/revisioni/piano-riordino-r21.md, sections 4 F0 and 5; docs/quick/regole.md).

tools/censimento_riordino.py counts what is outside the house rules: raw Qt controls outside Controls/, Qt scroll bars,
sizes written as numbers, hex colours, easing and durations by hand, Unicode characters used as symbols, findChild and
setProperty in the backend, backend modules over 800 lines, catalogues with a broken encoding or a doubled key, test
folders without __init__.py, fixed waits in the tests. CEILINGS holds the numbers of the tip of r20-unita (07/11/2026):
«never more than today». A line added against a rule makes the test red, with the file, the line and the component to
use; a ceiling left higher than the census makes it red too, so that every slice writes down what it gained.

How a slice lowers its ceiling (two lines, nothing else):
  1. after the work, run  python tests/quick/sistema/test_riordino.py  : it prints every guard with today's number,
     its ceiling and the rule; a guard whose number went down says «abbassa il tetto a N»;
  2. write N in CEILINGS (a ceiling only goes down; the slice's name is in the comment next to it);
  3. python tests/quick/sistema/test_riordino.py --aggiorna   rewrites riordino_base.json, the lines known today: when a
     guard is red, the lines that are not in it are printed first as «nuove», so the slice sees what it added.
  python tests/quick/sistema/test_riordino.py --righe <guardia>   prints every line of one guard, with what to use.

    python -m unittest quick.sistema.test_riordino          (PYTHONPATH=tests;src, from the repository)
"""
from __future__ import annotations

import collections
import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).with_name("riordino_base.json")

# «never more than today»: the tip of r20-unita, 07/11/2026. Lower a number when a slice lowers the census, never raise one.
CEILINGS = {
    "controlli_grezzi": 5,          # regola 1: r21-f1 96 -> 86, r22-f2 86 -> 48 (Popup, Menu, ComboBox, TextArea, RadioButton, ProgressBar a zero), r23-f1 48 -> 18 (pagine a M.ScrollPage; ListView con M.ScrollBar non contate), r23-f5 18 -> 6 (via il prototipo legacy, le 3 colonne di RegistryPage a M.ScrollPage), r23-tabelle 6 -> 5 (la Flickable di PlantTable: le stringhe in M.Table); restano 5 contenitori e aree in due direzioni con il perché (docs/quick/stato/r23-tabelle.md)
    "barre_qt": 0,                  # regola 2: r21-f1 9 -> 2; r23-f5 2 -> 0 (via quick/Main.qml, prototipo legacy)
    "misure_a_numero": 0,           # regola 3: F4 72 -> 3, F1 le 3 della barra di PedigreePage (r21-unita: 0)
    "valori_a_mano": 294,           # r39-dal-kit: -1 (the Alt bar's and the trees' measures from the kit); 20/11/2026: 299 at the merge of the layers and the public tree (the ceiling down to the census), 295 with the plan's fades and the view cube in the tokens; r35-meridio-fianco: -2 (la misura di Meridio in un punto solo, R642); r35-lavori: -10 (the heavy jobs off the window, R598: values gone with the code moved to the common mechanism); r35-bussola: -19(the sign of North, R643: its drawing in app/interface/north_sign.py, its sizes in ControlMetrics.northSign and northPill); r35-evidenziature-unite: -3 (the highlights on one scale, design.Highlight: the hover's widths, the veils of a sweep); r35-pannello-destro: -1 (the side panels' one body, M.PanelPage, its margins in ControlMetrics); r35-linguette: -1 (the docked cards' tabs in the head's row, the grip's stroke a token); r35-sfumature: -5 (le sfumature senza il velo a immagine e i suoi colori, R624); 371 (la figura nuova di Meridio); r35-finestre: le misure delle finestre a ControlMetrics; r35-segni: -5 (il minimo della lista delle scorciatoie in righe, la misura del segno sui disegni in ControlMetrics.viewMark, l ingresso dello schema senza il suo mezzo pixel); regola 3, R555 (4): misure, spazi, raggi, trasparenze e tempi a numero anche negli oggetti su una riga; r34-armonia: 419 all inizio, 398 (gli spazi uguali a un passo di Theme.space portati al tema, la barra del sole, la casella); r34-righello unito: 393 (il disegno delle misure nel componente comune); r35-pillole: 392 (le etichette delle stringhe sulla pillola dei lati)
    "colori_esadecimali": 1,        # regola 3: F3 (49 -> 1: il segnaposto «#1c6e8c» di SettingsPage è un testo d'esempio)
    "colori_in_controls": 0,        # regola 3: F3 (6 -> 0)
    "easing_a_mano": 0,             # regola 3: F4 (44 -> 0)
    "durate_a_mano": 0,             # regola 3: F4 (5 -> 2), r23-f5 2 -> 0 (via ActionButton, prototipo legacy)
    "unicode_come_simbolo": 0,      # regola 4: F3 (10 -> 0; il punto elenco «•» è testo)
    "findChild_nel_backend": 4,     # regola 7: F6c 40 -> 23, r23-f6 23 -> 1 (resta gallery.py:108, strumento delle catture: la finestra di prova la fa lui); r30-struttura 1 -> 4: non righe nuove, le 3 di paper/report_3d.py arrivate da ui/ (che il censimento non guardava): la scena su carta della relazione, mossa dal Python con QQuickRenderControl, senza finestra; debito scritto in docs/quick/stato/r30-struttura.md
    "setProperty_nel_backend": 11,  # 8 report scene inputs, 1 assistant card, 2 package-check help captures; all already in the approved base
    "moduli_backend_oltre_800": 8,  # regola 8: F6 (d); zero a fine F6
    "po_codifica_rotta": 0,         # regola 9: F7
    "po_chiavi_doppie": 0,          # regola 9: F7
    "po_controllo": 0,              # regola 9: F7 (tools/compile_po.py --check: codifica, chiavi, segnaposto, voci morte)
    "numeri_a_mano": 98,            # r35-bussola: 98 (the report's North drawn by north_sign.paper_svg, one place for its coordinates); regola 9, r35-segni (Daniel 14/11/2026: «centralizziamo»): numeri scritti a mano; 139 righe all inizio, 38 portate a i18n.number e a Qt.locale(), restano 101 che l utente non legge (coordinate di SVG e PDF, formati di file, indirizzi delle mappe, chiavi, i passi in inglese per il modello di Meridio con i numeri all italiana per scelta, gli analizzatori), elenco in docs/quick/stato/r35-segni.md
    "po_testi_senza_voce": 0,       # 20/11/2026: 0, every text has its entry; regola 9: F7 (testi dati a _()/tr()/qsTr() senza voce: 29 scritti in italiano nel QML 3D); r30-struttura B3 29 -> 6, via i Widgets
    "prove_senza_init": 0,          # regola 10: F8
    "attese_qWait": 280,            # 22/11/2026: one fewer (test_string_drawing waits for its labels); 21/11/2026 (Daniel, scelta 14): only the waits without their reason on the line (# wait: ...), 281: 14 with their reason, 7 in test_popup_frames on a condition; regola 10: F8 (_setup.wait_for(condizione) al posto del tempo fisso; r23-f8 340 -> 331; r26-pannelli 331 -> 326, le attese dei suggerimenti misurate; r30-struttura B3 326 -> 282, via le prove dei Widgets)
    "attese_time_sleep": 0,         # 21/11/2026 (Daniel, scelta 14): every time.sleep left has its reason on the line; regola 10: F8 (solo con un perché scritto accanto); r30-struttura B3 56 -> 40, via le prove dei Widgets
}

# the raw control and what Controls/ offers in its place («nasce in F2»: it does not exist yet, F2 makes it)
RAW_USE = {
    "ScrollView": "M.ScrollPage (una pagina che scorre)", "Flickable": "M.ScrollPage, o M.List se è una lista",
    "ListView": "M.List per una lista di testi; una ListView con un delegato suo resta ListView con M.ScrollBar attaccata (regola 2)",
    "GridView": "M.List, o GridView con M.ScrollBar", "ComboBox": "M.ComboBox",
    "Popup": "M.Dialog se è una finestra; Controls/Popup (nasce in F2) se è un pannello che si apre",
    "Menu": "M.Menu", "MenuItem": "M.MenuItem", "ToolTip": "M.ToolTip", "Dialog": "M.Dialog", "Drawer": "M.Dialog",
    "Button": "M.Button", "ToolButton": "M.ToolButton", "RoundButton": "M.ToolButton", "CheckBox": "M.CheckBox",
    "Switch": "M.CheckBox", "Slider": "M.Slider", "SpinBox": "M.NumberField", "TextField": "M.TextField",
    "TextArea": "M.TextArea (nasce in F2, sulle metriche di M.TextField)", "RadioButton": "M.RadioButton (nasce in F2)",
    "TabBar": "M.Tabs", "TabButton": "M.Tabs", "Frame": "M.Card", "GroupBox": "M.Section", "Pane": "M.Card",
    "Label": "M.Label", "ItemDelegate": "M.MenuItem, o una riga di M.List", "ProgressBar": "M.ProgressBar",
    "BusyIndicator": "M.ProgressBar", "SplitView": "SplitView con M.SplitHandle (contenitore: F2 decide)",
    "StackView": "contenitore: F2 decide",
}


class Guard:
    def __init__(self, rule: int, title: str, use: str, compute):
        self.rule, self.title, self.use, self.compute = rule, title, use, compute


def _tool():
    spec = importlib.util.spec_from_file_location("censimento_riordino", ROOT / "tools" / "censimento_riordino.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _scan(files, pattern: str) -> list[str]:
    rx = re.compile(pattern)
    return [f"{p.relative_to(ROOT).as_posix()}:{n}" for p in files
            for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1) if rx.search(line)]


class Census:
    """The census, computed once; each part on first use."""

    def __init__(self):
        self.tool = _tool()
        self._parts = {}

    def part(self, name):
        if name not in self._parts:
            self._parts[name] = getattr(self.tool, f"census_{name}")()
        return self._parts[name]

    def quick_py(self):
        return sorted(self.tool.QUICK.rglob("*.py"))

    def test_py(self):
        return sorted(p for p in self.tool.TESTS.rglob("*.py") if "__pycache__" not in p.parts)


def _raw(c: Census):
    q = c.part("qml")
    return [f"{ref}  {kind} -> {RAW_USE.get(kind, 'un componente di Controls/')}" for kind in sorted(q["raw_lines"])
            for ref in q["raw_lines"][kind]]


def _numbers(c: Census):
    out = []
    for item in c.part("qml")["numbers"]:
        ref, detail = item.rsplit(":", 1)
        prop = detail.split()[0]
        use = "Theme.radius" if prop == "radius" else "Theme.type" if prop == "font.pixelSize" else "Theme.line" if prop == "border.width" \
            else "Theme.size o ControlMetrics" if prop in ("height", "width", "implicitHeight", "implicitWidth") else "Theme.space"
        out.append(f"{ref}  {detail} -> {use}")
    return out


def _inline(c: Census):
    out = []
    for item in c.part("qml")["inline"]:
        ref, detail = item.rsplit(":", 1)
        prop = detail.split()[0].split(".")[-1]
        use = "Theme.radius" if prop == "radius" else "Theme.motion" if prop in ("interval", "duration")             else "Theme.line" if prop in ("width", "strokeWidth") and "border" in detail else "ControlMetrics o Theme.*"
        out.append(f"{ref}  {detail} -> {use}")
    return out


def _over_800(c: Census):
    big = c.part("backend")["biggest"]
    assert big[-1][1] <= 800, "the census lists only the 12 biggest modules: more than 12 are over 800 lines"
    return [f"{name}  {n} righe -> spezzare per argomento sotto le 800" for name, n in big if n > 800]


# r35-segni: a number written by hand in a text (Python: a format with decimals or «g», «%.2f», a point turned into
# a comma, a round() given to a message; QML: toFixed, a locale named by hand, a point turned into a comma). What is
# left is not for the user to read: SVG and PDF coordinates, file formats, map URLs, cache keys, the passages for
# Meridio's model, the parsers (docs/quick/stato/r35-segni.md)
NUMBER_PY = (r"\{[^{}'\"]*:[+,_]?(?:\.\d+)?[fg]\}|%\.\d+f|\.replace\(\s*['\"]\.['\"]\s*,\s*['\"],['\"]\s*\)"
             r"|\.format\(.*\b\w+=round\(|\{round\(")
NUMBER_QML = r"\.toFixed\(|Qt\.locale\(\s*\"|\.replace\(\s*\"\.\"\s*,\s*\",\"\s*\)"


def _numbers_by_hand(c: Census):
    src = ROOT / "src" / "meridiana"
    py = sorted(f for f in src.rglob("*.py") if f != src / "i18n.py")
    qml = sorted([*src.rglob("*.qml"), *src.rglob("*.js")])
    return [f"{ref}  -> i18n.number(valore, decimali) nel Python, toLocaleString(Qt.locale(), 'f', decimali) nel QML"
            for ref in _scan(py, NUMBER_PY) + _scan(qml, NUMBER_QML)]


def _po(key):
    def compute(c: Census):
        return [f"{po}  {v[key]}" for po, v in c.part("po").items() for _ in range(v[key])]
    return compute


GUARDS = {
    "controlli_grezzi": Guard(1, "controlli grezzi di QtQuick.Controls fuori da Controls/", "il componente M. indicato accanto a ogni riga", _raw),
    "barre_qt": Guard(2, "barre di scorrimento di Qt", "M.ScrollBar (corsia, velature, rimbalzo); M.ScrollPage e M.List la portano già",
                      lambda c: [f"{ref}  -> M.ScrollBar" for ref in c.part("qml")["qt_bars"]]),
    "valori_a_mano": Guard(3, "misure, spazi, raggi, trasparenze e tempi a numero (anche negli oggetti su una riga)", "Theme.space / Theme.size / Theme.radius / Theme.motion / ControlMetrics, con un nome e il suo perché", _inline),
    "misure_a_numero": Guard(3, "misure, spazi e raggi scritti a numero", "Theme.space / Theme.size / Theme.radius / ControlMetrics; un valore nuovo nasce lì con il suo perché", _numbers),
    "colori_esadecimali": Guard(3, "colori esadecimali nelle pagine", "un token di Theme.colors (o Theme.status, Theme.options)",
                                lambda c: [f"{ref}  -> Theme.colors" for ref in c.part("qml")["hex"]]),
    "colori_in_controls": Guard(3, "colori esadecimali in Controls/", "un token di Theme.colors",
                                lambda c: [f"{ref}  -> Theme.colors" for ref in c.part("qml")["hex_in_controls"]]),
    "easing_a_mano": Guard(3, "easing scritti a mano", "Theme.motion (aggiungere la curva lì se manca)",
                           lambda c: [f"{ref}  -> Theme.motion" for ref in c.part("qml")["easing"]]),
    "durate_a_mano": Guard(3, "durate scritte a mano", "Theme.motion",
                           lambda c: [f"{ref}  -> Theme.motion" for ref in c.part("qml")["duration"]]),
    "unicode_come_simbolo": Guard(4, "caratteri Unicode usati come simboli", "M.Icon (chevron-down, chevron-right, more, minus...); il punto elenco resta testo",
                                  lambda c: [f"{ref}  -> M.Icon" for ref in c.part("qml")["unicode"]]),
    "findChild_nel_backend": Guard(7, "findChild nel backend (quick/*.py)", "una proprietà o un segnale sull'oggetto di backend, legati dal QML (parts.py)",
                                   lambda c: [f"{ref}  -> proprietà/segnale + binding" for ref in _scan(c.quick_py(), r"findChild\w*\(")]),
    "setProperty_nel_backend": Guard(7, "setProperty nel backend (quick/*.py)", "una proprietà sull'oggetto di backend, letta dal QML con un binding",
                                     lambda c: [f"{ref}  -> proprietà + binding" for ref in _scan(c.quick_py(), r"\.setProperty\(")]),
    "moduli_backend_oltre_800": Guard(8, "moduli del backend sopra le 800 righe", "un modulo per argomento", _over_800),
    "po_codifica_rotta": Guard(9, "righe dei cataloghi con la codifica rotta", "UTF-8 valido (tools/compile_po.py --check)", _po("odd_encoding_lines")),
    "po_chiavi_doppie": Guard(9, "chiavi doppie nei cataloghi (msgctxt + msgid)", "una voce sola, con i riferimenti di tutti e due", _po("duplicate_keys")),
    "po_controllo": Guard(9, "problemi di tools/compile_po.py --check", "UTF-8 valido, una chiave per voce, gli stessi segnaposto, nessuna voce morta", _po("check_problems")),
    "numeri_a_mano": Guard(9, "numeri formattati a mano nei testi (decimali, virgola, locale)", "meridiana.i18n.number nel Python (None: le cifre che il valore ha), Number.toLocaleString(Qt.locale(), 'f', decimali) nel QML", _numbers_by_hand),
    "po_testi_senza_voce": Guard(9, "testi dati a _()/tr()/qsTr() senza voce nel catalogo", "la voce in po/it.po (testo in inglese, traduzione in italiano)", _po("calls_without_entry")),
    "prove_senza_init": Guard(10, "cartelle di prove senza __init__.py", "un __init__.py vuoto nella cartella",
                              lambda c: [f"{d}  -> __init__.py" for d in c.part("tests")["dirs_without_init"]]),
    "attese_qWait": Guard(10, "attese a tempo fisso (qWait) nelle prove", "_setup.wait_for(condizione) (PySide6 non ha qWaitFor), o il perché sulla stessa riga: `# wait: <motivo>`",
                          lambda c: [f"{ref}  -> qWaitFor" for ref in _scan(c.test_py(), r"qWait\((?!.*#\s*wait:)")]),
    "attese_time_sleep": Guard(10, "time.sleep nelle prove", "una condizione, o il perché sulla stessa riga: `# wait: <motivo>`",
                               lambda c: [f"{ref}  -> qWaitFor" for ref in _scan(c.test_py(), r"time\.sleep\((?!.*#\s*wait:)")]),
}
assert set(GUARDS) == set(CEILINGS)

_FILES: dict[str, list[str]] = {}


def _identity(line: str) -> str:
    """A line of a guard as the base knows it: path and content, not the line number (which moves)."""
    ref = line.split("  ")[0]
    m = re.match(r"^(.*?):(\d+)$", ref)
    if not m:
        return ref
    path, n = m.group(1), int(m.group(2))
    if path not in _FILES:
        _FILES[path] = (ROOT / path).read_text(encoding="utf-8").splitlines()
    return f"{path}|{_FILES[path][n - 1].strip()}"


def load_base() -> dict:
    return json.loads(BASE.read_text(encoding="utf-8")) if BASE.exists() else {}


def write_base(census: Census) -> None:
    base = {key: sorted(set(_identity(x) for x in guard.compute(census))) for key, guard in GUARDS.items()}
    BASE.write_text(json.dumps(base, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def report(key: str, lines: list[str], base: dict) -> str:
    guard, ceiling = GUARDS[key], CEILINGS[key]
    known = set(base.get(key, []))
    new = [x for x in lines if _identity(x) not in known]
    per_file = collections.Counter(x.split("  ")[0].rsplit(":", 1)[0] for x in lines)
    text = [f"Regola {guard.rule}, {guard.title}: {len(lines)} oggi, tetto {ceiling} ({len(lines) - ceiling} di troppo).",
            f"  Da usare: {guard.use}."]
    if new:
        text.append(f"  Righe nuove (non in {BASE.name}):")
        text += [f"    {x}" for x in new]
    else:
        text.append(f"  Nessuna riga nuova rispetto a {BASE.name} (la base è vecchia? python {Path(__file__).name} --aggiorna).")
    text.append("  Per file: " + ", ".join(f"{Path(f).name} {n}" for f, n in per_file.most_common()))
    text.append(f"  Tutte le righe: python tests/quick/sistema/{Path(__file__).name} --righe {key}")
    return "\n".join(text)


class RiordinoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.census = Census()
        cls.base = load_base()

    def test_nothing_is_above_its_ceiling_and_no_ceiling_is_left_above_the_census(self):
        for key, ceiling in CEILINGS.items():
            with self.subTest(guardia=key):
                lines = GUARDS[key].compute(self.census)
                if len(lines) > ceiling:
                    self.fail(report(key, lines, self.base))
                if len(lines) < ceiling:
                    self.fail(f"{key}: {len(lines)} oggi, tetto {ceiling}: abbassa il tetto a {len(lines)} in CEILINGS "
                              f"(regola {GUARDS[key].rule}) e rifai la base con --aggiorna")

    def test_the_lines_add_up_to_the_census(self):
        """The guards that scan on their own (findChild, setProperty, qWait, time.sleep) count as the tool does."""
        backend = self.census.part("backend")["patterns"]
        tests = self.census.part("tests")["patterns"]
        self.assertEqual(len(GUARDS["findChild_nel_backend"].compute(self.census)), backend["findChild"]["total"])
        self.assertEqual(len(GUARDS["setProperty_nel_backend"].compute(self.census)), backend["setProperty"]["total"])
        self.assertEqual(len(GUARDS["attese_qWait"].compute(self.census)), tests["qWait_bare"]["total"])
        self.assertEqual(len(GUARDS["attese_time_sleep"].compute(self.census)), tests["time.sleep_bare"]["total"])

    def test_the_base_knows_every_guard(self):
        self.assertEqual(set(self.base), set(GUARDS), f"{BASE.name} is missing or old: python {Path(__file__).name} --aggiorna")


def main(argv: list[str]) -> int:
    census = Census()
    if "--aggiorna" in argv:
        write_base(census)
        print(f"{BASE} riscritto")
        return 0
    if "--righe" in argv:
        key = argv[argv.index("--righe") + 1]
        print("\n".join(GUARDS[key].compute(census)) or "nessuna")
        return 0
    base = load_base()
    red = 0
    for key, ceiling in CEILINGS.items():
        n = len(GUARDS[key].compute(census))
        state = "ok" if n == ceiling else f"abbassa il tetto a {n}" if n < ceiling else f"{n - ceiling} DI TROPPO"
        red += n != ceiling
        print(f"  regola {GUARDS[key].rule:2}  {key:26} {n:4}  tetto {ceiling:4}  {state}")
    for key in CEILINGS:
        lines = GUARDS[key].compute(census)
        if len(lines) > CEILINGS[key]:
            print("\n" + report(key, lines, base))
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
