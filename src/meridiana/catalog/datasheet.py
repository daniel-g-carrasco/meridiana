"""Reading a manufacturer's datasheet into catalogue records, with no model behind it: text and tables, nothing else.

A datasheet is untrusted data: it is read with pypdf (pure Python, already a dependency), never executed, and what
it says only ever fills the review window. Nothing here saves anything.

What comes back is a `Reading`: one `Proposal` per product family found, each field with where it was read (page,
the line of the sheet) and how sure the reader is:
- "high": the value is in a row whose label the reader knows and the checks of its table pass (a module's class:
  Vmp x Imp within 3 % of Pmax, Voc above Vmp, Isc above Imp);
- "medium": the label is known, no cross-check exists for that field;
- "low": the row was understood only in part (a value shared by columns, a table whose checks fail).

A value the sheet does not print stays absent: the reader never scales, averages or completes. A module's power
classes each take their own column of the table; a class whose column cannot be read is named in `unread_classes`,
never worked out from its neighbours.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..i18n import _

MAX_PAGES = 40
MAX_BYTES = 32 * 1024 * 1024
HIGH, MEDIUM, LOW = "high", "medium", "low"

NUMBER = re.compile(r"(?<![\w.,])[-+±]?\d{1,3}(?:,\d{3})+(?:\.\d+)?(?![\d])|(?<![\w.,])[-+±]?\d+(?:[.,]\d+)?(?![\d])")
_SPACES = re.compile(r"\s{2,}")
# the words that may stand between the numbers of one row of a table
_UNITS = re.compile(r"^(?:w|wp|kw|kwp|va|kva|v|vdc|vac|a|adc|aac|%|mm|kg|kwh|wh|hz|mv|ma|/|~|-|–|\u2014|to|x|×|pcs|max\.?|min\.?)$",
                    re.IGNORECASE)


# conditions printed inside a label: «(at 230 V, 50 Hz)», «@ 40 °C», «at 25 °C»: never the row's values
_CONDITIONS = re.compile(r"\([^()]*[A-Za-z°][^()]*\)(?!\s*\d)|(?:\bat\b|@|\bbei\b)\s*[-+]?\d+(?:[.,]\d+)?\s*(?:°\s*C|V|Hz|K)\b|\b\d+(?:[.,]\d+)?\s*Hz\b", re.IGNORECASE)


def to_number(text: str) -> float | None:
    """A number as a datasheet prints it: «1,500» is 1500, «31,11» is 31.11, «1.100» stays 1.1 only when it has not
    three decimals after a short integer (European thousands)."""
    text = text.strip().replace("±", "").replace("+", "")
    if re.fullmatch(r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?", text):
        return float(text.replace(",", ""))
    if re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+", text):
        return float(text.replace(".", ""))
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


@dataclass
class Anchor:
    page: int
    text: str
    confidence: str

    def as_source(self, source: str) -> dict:
        return {"source": source, "page": self.page, "text": self.text[:160], "confidence": self.confidence}


@dataclass
class Proposal:
    """A family of one datasheet, in the catalogue's terms (metres, %/K): the fields read and where each was read."""
    kind: str
    record: dict = field(default_factory=dict)
    anchors: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)
    unread_classes: list = field(default_factory=list)

    def put(self, key: str, value, page: int, line: str, confidence: str = MEDIUM) -> None:
        if value is None or value == "" or key in self.record:
            return
        self.record[key] = value
        self.anchors[key] = Anchor(page, line.strip(), confidence)

    def sources(self, source: str) -> dict:
        return {key: anchor.as_source(source) for key, anchor in self.anchors.items()}


@dataclass
class Reading:
    file: str
    kind: str = ""
    proposals: list = field(default_factory=list)
    pages: int = 0
    scanned: bool = False
    notes: list = field(default_factory=list)


def _positioned_lines(page) -> list[str]:
    """A page's lines rebuilt from where each piece of text is printed: pypdf's layout mode glues neighbouring cells
    of dense tables (Trina's «798705», Canadian's «A10.12»), positions do not. Rotated text is left out."""
    runs = []

    def visitor(text, cm, tm, _font, size):
        if not text or not text.strip() or abs(tm[1]) > 1e-3 or abs(cm[1]) > 1e-3:
            return
        scale = abs(tm[0] * cm[0]) or 1.0
        runs.append((tm[5] * cm[3] + cm[5], tm[4] * cm[0] + cm[4], " ".join(text.split()), (size or 8.0) * scale))

    page.extract_text(visitor_text=visitor)
    runs.sort(key=lambda run: (-run[0], run[1]))
    rows: list[list] = []
    for run in runs:
        if rows and abs(rows[-1][0][0] - run[0]) <= max(2.5, 0.4 * run[3]):
            rows[-1].append(run)
        else:
            rows.append([run])
    lines = []
    for row in rows:
        line = ""
        for _y, x, text, _size in sorted(row, key=lambda run: run[1]):
            column = max(0, int(x / 2.6))
            line += " " * max(column - len(line), 2 if line else 0) + text
        lines.append(line)
    return lines


def _pdf_pages(path):
    import logging

    from pypdf import PdfReader
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    reader = PdfReader(str(path))
    if reader.is_encrypted and reader.decrypt("") == 0:
        raise ValueError("encrypted PDF")
    return reader.pages[:MAX_PAGES]


def pages_of(path, *, layout: bool = False) -> list[list[str]]:
    """The lines of each page with their columns kept: from the positions of the text or, with `layout`, from pypdf's
    layout mode (some sheets read better one way, some the other). ValueError for a file that cannot be read."""
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("file too large")
    suffix = path.suffix.lower()
    if suffix in (".txt", ".md", ".csv"):
        return [path.read_text(encoding="utf-8-sig", errors="replace").splitlines()]
    if suffix != ".pdf":
        raise ValueError("not a PDF or a text file")
    try:
        out = []
        for page in _pdf_pages(path):
            try:
                lines = (page.extract_text(extraction_mode="layout", layout_mode_space_vertically=False).splitlines()
                         if layout else _positioned_lines(page))
            except Exception:  # noqa: BLE001 - a page pypdf cannot walk: its plain reading is still worth having
                lines = (page.extract_text() or "").splitlines()
            out.append([line.replace("ﬃ", "ffi").replace("ﬁ", "fi").replace("ﬂ", "fl") for line in lines if line.strip()])
        return out
    except ValueError:
        raise
    except Exception as error:  # noqa: BLE001 - whatever a malformed PDF raises is one failure for the caller
        raise ValueError(f"unreadable PDF: {type(error).__name__}") from error


def _numbers_after(line: str, start: int) -> list[tuple[float, int]]:
    """The numbers of a table row after its label, each with its column (the character it starts at), stopping at
    the first word that is neither a number nor a unit, once a number has been seen."""
    out = []
    line = _CONDITIONS.sub(lambda m: " " * len(m.group()), line[:start].rjust(start) + line[start:]) if start == 0 else (
        line[:start] + _CONDITIONS.sub(lambda m: " " * len(m.group()), line[start:]))
    for token in re.finditer(r"[^\s)\]]+[)\]]*", line[start:]):
        word = token.group()
        offset = start + token.start()
        if re.fullmatch(r"\(?\d\)|\[\d\]", word):       # a footnote: «(1)», «1)», «[2]»
            continue
        cleaned = word.strip("()[]*,;:≤≥≈~")
        number = None
        if NUMBER.fullmatch(cleaned):
            number = to_number(cleaned)
        else:
            glued = re.fullmatch(r"([-+±]?\d[\d.,]*)\s*(w|wp|kw|kwp|va|kva|v|vdc|a|adc|%|mm|kg|kwh|mv|ma|g)", cleaned, re.IGNORECASE)
            if glued:
                number = to_number(glued.group(1))
        if number is not None:
            out.append((number, offset))
        elif not _UNITS.match(cleaned) and out:
            break
    # a footnote printed as a small number right after the label, before the real values far to the right
    if len(out) >= 2 and out[0][0] in range(1, 10) and out[0][1] - start <= 3 and out[1][1] - out[0][1] > 6:
        out = out[1:]
    return out


_MODULE_ROWS = (
    ("pmax", r"(?:maximum|max\.?|rated|nominal|peak|module)\s*(?:rated\s*|peak\s*|nominal\s*)?power(?!\s*(?:voltage|current|tolerance|sorting|temperature))"
             r"|\bpmax\b(?!\s*(?:voltage|current))|\bpmpp\b|\bp\s?mpp\b|peak\s*power\s*watts|power\s*output|potenza\s*(?:massima|nominale|di\s*picco)|nennleistung"),
    ("vmp", r"(?:maximum\s*power|max\.?\s*power|optimum\s*(?:operating|power)|mpp|rated|operating)\s*(?:point\s*)?voltage|voltage\s*at\s*(?:maximum|max\.?|mpp|pmax|rated)"
            r"|\bv\s?mp+\b|\bu\s?mpp\b|tensione\s*(?:alla\s*)?(?:massima\s*potenza|mpp|di\s*massima)"),
    ("imp", r"(?:maximum\s*power|max\.?\s*power|optimum\s*(?:operating|power)|mpp|rated|operating)\s*(?:point\s*)?current|current\s*at\s*(?:maximum|max\.?|mpp|pmax|rated)"
            r"|\bi\s?mp+\b|corrente\s*(?:alla\s*)?(?:massima\s*potenza|mpp|di\s*massima)"),
    ("voc", r"open[\s-]*circuit\s*voltage|\bv\s?oc\b|\bu\s?oc\b|tensione\s*(?:a\s*vuoto|di\s*circuito\s*aperto|circuito\s*aperto)"),
    ("isc", r"short[\s-]*circuit\s*current|\bi\s?sc\b|\bi\s?k\b|corrente\s*di\s*corto\s*circuito|corrente\s*di\s*cortocircuito"),
    ("efficiency_pct", r"module\s*efficiency|\beta\s*m\b|\bη\s*m\b|panel\s*efficiency|efficienza\s*(?:del\s*)?modulo|efficiency\s*(?:stc|at\s*stc)?\s*(?:\[?%\]?)"),
)
# the voltage and the current first: their labels hold the words of the power («voltage at maximum power»)
_MODULE_ROWS = tuple((key, re.compile(pattern, re.IGNORECASE)) for key, pattern in (*_MODULE_ROWS[1:], _MODULE_ROWS[0]))
_COLD_TABLE = re.compile(r"\b(?:noct|nmot|nmost|ntc|800\s*w)\b", re.IGNORECASE)


def _module_rows(page_lines: list[list[str]]) -> list[dict]:
    """Every line that looks like a row of a module's electrical table, in order of reading."""
    rows = []
    for number, lines in enumerate(page_lines, 1):
        for index, line in enumerate(lines):
            if len(line) > 900:
                continue
            for key, pattern in _MODULE_ROWS:
                found = pattern.search(line)
                if not found:
                    continue
                values = _numbers_after(line, found.end())
                if values:
                    rows.append({"key": key, "values": [v for v, _o in values], "columns": [o for _v, o in values],
                                 "page": number, "index": index, "line": line})
                break
    return rows


def _strictly_rising(values) -> bool:
    return all(b > a for a, b in zip(values, values[1:], strict=False))


def _stride(values: list[float]) -> int:
    """How many columns of the table make one class: 1 for plain classes, 2 for the standard and NOCT columns in turn
    (605 452 610 456...), 3 or 4 when a bifacial column is added (650 520 685 655 524 690...). The standard column
    comes first in the sheets read so far (Aiko, Jinko, Trina)."""
    if _strictly_rising(values):
        return 1
    for stride in (2, 3, 4):
        if len(values) >= 2 * stride and len(values) % stride == 0 and all(
                _strictly_rising(values[start::stride]) for start in range(stride)):
            return stride
    return 0


def _class_table(rows: list[dict]) -> dict | None:
    """The best set of five rows that read as one electrical table: {"classes": [...], "rows": {...}, "checked"}.
    Rows are taken near a power row of the same page, with the same number of columns; the table in which the most
    classes pass the checks wins, the first in the sheet on a tie (the standard conditions come first)."""
    best = None
    for position, head in enumerate(rows):
        if head["key"] != "pmax":
            continue
        stride = _stride(head["values"])
        if not stride:
            continue
        powers = head["values"][0::stride]
        if not all(20 <= p <= 1200 for p in powers):
            continue
        nearby = [r for r in rows if r["page"] == head["page"] and abs(r["index"] - head["index"]) <= 24]
        table = {"pmax": head}
        for key in ("vmp", "imp", "voc", "isc", "efficiency_pct"):
            # after the power row first; a row may have more numbers than columns (a drawing's dimension to its right)
            candidates = sorted((r for r in nearby if r["key"] == key and len(r["values"]) >= len(powers)),
                                key=lambda r: (r["index"] < head["index"], abs(r["index"] - head["index"])))
            if candidates:
                table[key] = candidates[0]
        if not all(k in table for k in ("vmp", "imp", "voc", "isc")):
            continue
        classes, checked = [], 0
        for column, power in enumerate(powers):
            entry = {"pmax": power}
            for key in ("vmp", "imp", "voc", "isc", "efficiency_pct"):
                row = table.get(key)
                if row is None:
                    continue
                step = stride if len(row["values"]) >= len(head["values"]) else 1
                if column * step < len(row["values"]):
                    entry[key] = row["values"][column * step]
            classes.append(entry)
            if _class_ok(entry):
                checked += 1
        if checked == 0:
            continue
        cold = sum(1 for r in table.values() if _COLD_TABLE.search(r["line"]))
        score = (checked / len(classes) >= 0.99, checked, -cold, -position)
        if best is None or score > best[0]:
            best = (score, {"classes": classes, "rows": table, "checked": checked})
    return best[1] if best else None


def _class_ok(entry: dict) -> bool:
    try:
        return (abs(entry["vmp"] * entry["imp"] - entry["pmax"]) <= 0.03 * entry["pmax"]
                and entry["voc"] > entry["vmp"] and entry["isc"] > entry["imp"])
    except KeyError:
        return False


def _first_line(page_lines, pattern, flags=re.IGNORECASE):
    regex = re.compile(pattern, flags)
    for number, lines in enumerate(page_lines, 1):
        for line in lines:
            found = regex.search(line)
            if found:
                yield number, line, found


_COEFFICIENT = (
    ("gamma_pmax", r"(?:temperature\s*coe\S*\s*(?:of|for)?\s*(?:pmax|pmpp|p\s?mp+|power|maximum\s*power)|(?:pmax|pmpp|power)\s*temperature\s*coe\S*|coefficiente\s*(?:di\s*temperatura\s*)?(?:di\s*)?(?:pmax|potenza)|\bγ\b|\bα\s*\(?pm|tk\s*\(?pm)"),
    ("beta_voc", r"(?:temperature\s*coe\S*\s*(?:of|for)?\s*(?:voc|open[\s-]*circuit)|voc\s*temperature\s*coe\S*|coefficiente\s*(?:di\s*temperatura\s*)?(?:di\s*)?voc|tk\s*\(?[uv]oc)"),
    ("alpha_isc", r"(?:temperature\s*coe\S*\s*(?:of|for)?\s*(?:isc|short[\s-]*circuit)|isc\s*temperature\s*coe\S*|coefficiente\s*(?:di\s*temperatura\s*)?(?:di\s*)?isc|tk\s*\(?isc)"),
)
_DIMENSIONS = re.compile(r"(\d{3,4}(?:[.,]\d+)?)\s*(?:mm)?\s*[x×*]\s*(\d{3,4}(?:[.,]\d+)?)\s*(?:mm)?\s*[x×*]\s*(\d{1,3}(?:[.,]\d+)?)\s*(?:mm)?")
_WEIGHT = re.compile(r"(?:weight|peso|gewicht)\D{0,40}?(\d{1,3}(?:[.,]\d+)?)\s*kg", re.IGNORECASE)
_CELLS = re.compile(r"(?:no\.?\s*of\s*cells|number\s*of\s*cells|cells?\s*(?:number|quantity|count|configuration|arrangement)|numero\s*(?:di\s*)?celle|cell\s*no)\D{0,40}?(\d{2,3})", re.IGNORECASE)
_SYSTEM_VOLTAGE = re.compile(r"(?:max(?:imum|\.)?\s*system\s*voltage|system\s*voltage|tensione\s*(?:massima\s*)?(?:di\s*)?sistema)\D{0,30}?(\d[\d.,]{2,5})", re.IGNORECASE)
_FUSE = re.compile(r"(?:series\s*fuse|fuse\s*rating|reverse\s*current|fusibile)\D{0,40}?(\d{1,3})\s*A", re.IGNORECASE)
_BIFACIAL = re.compile(r"(?:bifacial(?:ity)?\s*(?:factor|coefficient|coeff\.?)|bifaciality|φ\s*pmax|phi\s*pmax|φ)\D{0,30}?(\d{2})\s*(?:±\s*\d+\s*)?%", re.IGNORECASE)
_WARRANTY_PRODUCT = re.compile(r"(?:(\d{1,2})\s*[- ]?\s*(?:year|years|anni|yr)s?\s*(?:\S+\s*){0,2}?(?:product|prodotto|material|workmanship))|(?:(?:product|prodotto)\s*(?:warranty|garanzia)\D{0,20}?(\d{1,2})\s*(?:year|anni))", re.IGNORECASE)
_WARRANTY_POWER = re.compile(r"(?:(\d{1,2})\s*[- ]?\s*(?:year|years|anni|yr)s?\s*(?:\S+\s*){0,2}?(?:linear|power|performance|potenza|output))|(?:(?:linear\s*)?(?:power|performance)\s*(?:warranty|garanzia)\D{0,20}?(\d{1,2})\s*(?:year|anni))", re.IGNORECASE)


def _coefficient_near(lines: list[str], index: int, end: int) -> tuple[float, str] | None:
    """A temperature coefficient on its label's line, or alone on the line next to it (a tall row prints its value a
    little above or below the label: Jinko). «- 0.26%/ °C» is -0.26."""
    pattern = re.compile(r"([-−–+]?)\s*(\d[.,]\d{1,3})\s*%\s*/")
    found = pattern.search(lines[index], end) or pattern.search(lines[index])
    line = lines[index]
    if not found:
        for near in (index - 1, index + 1, index - 2, index + 2):
            if 0 <= near < len(lines) and not re.search(r"(?i)coe", lines[near]):
                found = pattern.search(lines[near])
                if found:
                    line = lines[near]
                    break
    if not found:
        return None
    value = to_number(found.group(2))
    return (-value if found.group(1) in ("-", "−", "–") else value), line


def _read_module_extras(prop: Proposal, page_lines) -> None:
    for key, pattern in _COEFFICIENT:
        regex = re.compile(pattern, re.IGNORECASE)
        done = False
        for number, lines in enumerate(page_lines, 1):
            for index, line in enumerate(lines):
                found = regex.search(line)
                if found:
                    near = _coefficient_near(lines, index, found.end())
                    if near is not None and abs(near[0]) < 1:
                        prop.put(key, near[0], number, near[1], MEDIUM)
                        done = True
                        break
            if done:
                break
    # the same three coefficients in a table written the other way round: «Temperature coefficient  Pmax -0.29»
    for page, line, _found in _first_line(page_lines, r"\b(pmax|pmpp)\b.{0,60}?[-−]0[.,]\d+\s*%"):
        found = re.search(r"[-−](0[.,]\d+)\s*%", line)
        if found and "gamma_pmax" not in prop.record:
            prop.put("gamma_pmax", -to_number(found.group(1)), page, line, LOW)
        break
    for page, line, found in _first_line(page_lines, _DIMENSIONS.pattern):
        a, b, c = (to_number(found.group(n)) for n in (1, 2, 3))
        if a and b and c and 500 <= min(a, b) and max(a, b) <= 3500 and c <= 80:
            prop.put("length", max(a, b) / 1000.0, page, line, MEDIUM)
            prop.put("width", min(a, b) / 1000.0, page, line, MEDIUM)
            prop.put("thickness_mm", c, page, line, MEDIUM)
            break
    for regex, key, low, high in ((_WEIGHT, "weight_kg", 3, 80), (_CELLS, "cells", 30, 300),
                                  (_SYSTEM_VOLTAGE, "max_system_voltage_v", 500, 2000), (_FUSE, "max_series_fuse_a", 5, 80),
                                  (_BIFACIAL, "bifaciality", 50, 100)):
        for page, line, found in _first_line(page_lines, regex.pattern):
            value = to_number(found.group(1))
            if value is not None and low <= value <= high:
                prop.put(key, int(value) if key == "cells" else value, page, line, MEDIUM)
                break
    for regex, key in ((_WARRANTY_PRODUCT, "warranty_product_years"), (_WARRANTY_POWER, "warranty_power_years")):
        for page, line, found in _first_line(page_lines, regex.pattern):
            value = to_number(found.group(1) or found.group(2))
            if value and 5 <= value <= 40:
                prop.put(key, value, page, line, LOW)
                break
    text = " ".join(" ".join(lines) for lines in page_lines).casefold()
    if "bifaciality" in prop.record or re.search(r"\bbifacial\b", text) and not re.search(r"mono[- ]?facial", text):
        prop.record.setdefault("bifacial", True)
    technology = next((word for pattern, word in (
        (r"topcon|tiger\s*neo|n[- ]type\s*topcon", "n-type TOPCon"), (r"heterojunction|\bhjt\b", "HJT"),
        (r"back[- ]contact|\babc\b|\bhpbc\b|\bibc\b", "Back contact"), (r"\bperc\b", "PERC"),
        (r"n[- ]type", "n-type")) if re.search(pattern, text)), "")
    if technology:
        prop.record.setdefault("technology", technology)


MODEL_PATTERN = re.compile(r"\b[A-Z][A-Za-z0-9]{1,}(?:[-_./][A-Za-z0-9.]+){1,6}\b")


def _module_proposal(page_lines, name: str, other=None) -> Proposal | None:
    """`other`: the sheet's pages read the other way; the table with more classes that pass the checks is taken."""
    table = _class_table(_module_rows(page_lines))
    if (table is None or table["checked"] < len(table["classes"])) and other is not None:
        second = _class_table(_module_rows(other()))
        if second is not None and (table is None or second["checked"] > table["checked"]):
            table = second
    if table is None:
        return None
    prop = Proposal("modules")
    classes = table["classes"]
    usable = [c for c in classes if _class_ok(c)]
    head = table["rows"]["pmax"]
    middle = usable[len(usable) // 2]
    for key in ("pmax", "vmp", "imp", "voc", "isc", "efficiency_pct"):
        row = table["rows"].get(key)
        if row is not None and key in middle:
            prop.put(key, middle[key], row["page"], row["line"], HIGH)
    prop.record["classes"] = usable
    prop.record["power_classes_w"] = [c["pmax"] for c in classes]
    prop.anchors["classes"] = Anchor(head["page"], head["line"], HIGH)
    prop.anchors["power_classes_w"] = Anchor(head["page"], head["line"], HIGH)
    prop.unread_classes = [c["pmax"] for c in classes if not _class_ok(c)]
    if prop.unread_classes:
        prop.notes.append(_("Classes whose checks fail, left out: {which}.").format(which=", ".join(f"{p:g} W" for p in prop.unread_classes)))
    _read_module_extras(prop, page_lines)
    return prop


# the other kinds: one row of a table per field; the same patterns serve inverters and microinverters
_TABLE_FIELDS = {
    "inverters": (
        ("ac_power_nominal_w", r"(?:nominal|rated)\s*(?:ac\s*)?(?:active\s*)?(?:output\s*)?power|potenza\s*(?:attiva\s*)?(?:nominale|ac\s*nominale)|ac\s*(?:nominal|rated)\s*(?:active\s*)?power|nominal\s*active\s*power|rated\s*active\s*power|nominal\s*ac\s*power"),
        ("ac_power_max_va", r"max(?:imum|\.)?\s*(?:ac\s*)?(?:apparent|output)\s*power|apparent\s*(?:ac\s*)?power|max(?:imum|\.)?\s*ac\s*power|potenza\s*apparente"),
        ("dc_power_max_w", r"(?:recommended\s*)?max(?:imum|\.)?\s*(?:pv|dc|input)\s*(?:input\s*)?power|max(?:imum|\.)?\s*(?:pv|dc)\s*(?:array\s*)?(?:generator\s*)?power|potenza\s*(?:dc|cc|fv)\s*massima|max\.?\s*dc\s*input\s*power"),
        ("dc_voltage_max_v", r"max(?:imum|\.)?\s*(?:dc\s*|pv\s*|array\s*|system\s*)?(?:input\s*)?voltage|absolute\s*max\S*\s*(?:input\s*)?voltage|tensione\s*(?:massima|max\.?)\s*(?:di\s*ingresso|cc|dc)?"),
        ("mppt_range", r"mpp\w*\s*(?:operating\s*|operation\s*)?voltage\s*range|mpp\w*\s*range|mpp\s*voltage|operating\s*voltage\s*range\s*\(?mpp|intervallo\s*(?:di\s*)?(?:tensione\s*)?mppt|voltage\s*range\s*mpp"),
        ("full_power_mppt_min_v", r"(?:full[\s-]*(?:load|power)|nominal\s*power)\s*mpp\w*\s*(?:voltage\s*)?(?:range)?|mpp\w*\s*(?:voltage\s*)?range\s*(?:for|at)\s*(?:nominal|rated|full)"),
        ("startup_voltage_v", r"start[\s-]*(?:up|ing)\s*(?:input\s*)?voltage|tensione\s*di\s*avvio"),
        ("dc_voltage_nominal_v", r"(?:nominal|rated)\s*(?:dc\s*|pv\s*)?input\s*voltage|nominal\s*dc\s*voltage|tensione\s*nominale\s*(?:di\s*ingresso|cc|dc)"),
        ("mppt_count", r"(?:number|no\.?|numero)\s*(?:of\s*|di\s*)?(?:independent\s*)?mpp\w*(?:\s*trackers?)?|mpp\s*trackers?|independent\s*mpp\w*"),
        ("strings_per_mppt", r"(?:strings?|inputs?)\s*per\s*mpp\w*|(?:number|no\.?)\s*of\s*(?:dc\s*)?(?:inputs?|strings?)\s*per|max(?:imum|\.)?\s*number\s*of\s*inputs|stringhe\s*per\s*mppt"),
        ("dc_current_max_per_mppt_a", r"max(?:imum|\.)?\s*(?:dc\s*|pv\s*)?(?:input\s*|operating\s*)?current\s*(?:per\s*|/\s*|of\s*)?(?:each\s*)?mpp\w*|max(?:imum|\.)?\s*input\s*current|corrente\s*(?:massima|max\.?)\s*(?:di\s*ingresso)?\s*(?:per\s*)?mppt?"),
        ("dc_isc_max_per_mppt_a", r"max(?:imum|\.)?\s*(?:dc\s*|pv\s*|input\s*)?(?:short[\s-]*circuit\s*current|isc)|(?:short[\s-]*circuit\s*current)\s*(?:per\s*mpp\w*)?|corrente\s*di\s*corto\s*circuito"),
        ("ac_voltage_nominal_v", r"(?:nominal|rated)\s*(?:ac\s*|output\s*|grid\s*)?voltage|tensione\s*nominale\s*(?:ac|ca)"),
        ("ac_current_max_a", r"max(?:imum|\.)?\s*(?:ac\s*|output\s*)+current|corrente\s*(?:massima|max\.?)\s*(?:di\s*uscita|ac|ca)"),
        ("efficiency_max_pct", r"max(?:imum|\.)?\s*efficiency|efficienza\s*massima|peak\s*efficiency|rendimento\s*massimo"),
        ("efficiency_euro_pct", r"europ\w*\s*(?:weighted\s*)?efficiency|efficiency\s*\(?\s*eu\w*|euro\s*eta|rendimento\s*europeo|efficienza\s*europea|\beu[\s-]*efficiency"),
        ("weight_kg", r"\bweight\b|\bpeso\b"),
        ("dimensions_mm", r"dimensions?|dimensioni"),
        ("warranty_years", r"(?:standard\s*)?warranty|garanzia"),
    ),
    "optimizers": (
        ("rated_input_power_w", r"rated\s*(?:input\s*)?(?:dc\s*)?power|rated\s*input\s*dc\s*power|potenza\s*(?:cc\s*)?nominale|max(?:imum|\.)?\s*input\s*power"),
        ("max_input_voltage_v", r"absolute\s*max\S*\s*input\s*voltage|max(?:imum|\.)?\s*(?:pv\s*|dc\s*)?input\s*voltage|tensione\s*(?:di\s*ingresso\s*)?massima"),
        ("mppt_range", r"mpp\w*\s*(?:operating\s*|operation\s*)?(?:voltage\s*)?range|intervallo\s*(?:operativo\s*)?mppt"),
        ("max_input_isc_a", r"max(?:imum|\.)?\s*(?:short[\s-]*circuit\s*current|input\s*short[\s-]*circuit\s*current|isc)|corrente\s*(?:massima\s*)?di\s*corto\s*circuito"),
        ("max_input_current_a", r"max(?:imum|\.)?\s*(?:dc\s*)?input\s*current"),
        ("max_output_current_a", r"max(?:imum|\.)?\s*output\s*current|corrente\s*(?:massima\s*)?di\s*uscita"),
        ("max_output_voltage_v", r"max(?:imum|\.)?\s*output\s*voltage|tensione\s*(?:massima\s*)?di\s*uscita"),
        ("efficiency_peak_pct", r"max(?:imum|\.)?\s*efficiency|peak\s*efficiency|efficienza\s*massima"),
        ("efficiency_weighted_pct", r"weighted\s*efficiency|efficienza\s*ponderata"),
        ("weight_kg", r"\bweight\b|\bpeso\b"),
        ("warranty_years", r"(?:product\s*)?warranty|garanzia"),
    ),
    "batteries": (
        ("usable_energy_kwh", r"usable\s*(?:energy|capacity)|energia\s*utilizzabile|capacit\S*\s*utilizzabile"),
        ("nominal_energy_kwh", r"(?:nominal|rated|total)\s*(?:energy|capacity)|energia\s*nominale|capacit\S*\s*nominale"),
        ("nominal_voltage_v", r"(?:nominal|rated)\s*voltage|tensione\s*nominale"),
        ("max_charge_power_w", r"(?:max(?:imum|\.)?|rated|nominal)\s*charg\w*\s*power|potenza\s*(?:massima\s*)?di\s*carica"),
        ("max_discharge_power_w", r"(?:max(?:imum|\.)?|rated|nominal)\s*discharg\w*\s*power|potenza\s*(?:massima\s*)?di\s*scarica"),
        ("round_trip_efficiency_pct", r"round[\s-]*trip\s*efficiency|efficienza\s*(?:di\s*)?(?:ciclo|round)"),
        ("depth_of_discharge_pct", r"depth\s*of\s*discharge|\bdod\b|profondit\S*\s*di\s*scarica"),
        ("cycles_warranted", r"cycle\s*life|cycles?\b"),
        ("weight_kg", r"\bweight\b|\bpeso\b"),
        ("warranty_years", r"(?:product\s*)?warranty|garanzia"),
    ),
}
_TABLE_FIELDS["microinverters"] = (
    ("ac_power_nominal_w", r"(?:nominal|rated|continuous)\s*(?:ac\s*)?(?:output\s*)?power|potenza\s*(?:di\s*uscita\s*)?nominale|nominal\s*output\s*power"),
    ("ac_power_max_va", r"(?:peak|max(?:imum|\.)?)\s*(?:continuous\s*)?(?:ac\s*)?(?:output\s*)?(?:apparent\s*)?power"),
    ("dc_power_max_per_input_w", r"(?:commonly\s*used\s*module|module\s*power|recommended\s*(?:pv|input|module)\s*power|max(?:imum|\.)?\s*(?:input|pv)\s*power|pv\s*power)"),
    ("dc_voltage_max_v", r"(?:peak\s*power\s*tracking\s*)?max(?:imum|\.)?\s*(?:dc\s*|pv\s*)?input\s*voltage|maximum\s*dc\s*voltage"),
    ("mppt_range", r"mpp\w*\s*(?:operating\s*|tracking\s*)?(?:voltage\s*)?range|peak\s*power\s*tracking\s*voltage|mppt\s*voltage"),
    ("dc_current_max_per_input_a", r"max(?:imum|\.)?\s*(?:dc\s*)?(?:input\s*)?current"),
    ("dc_isc_max_per_input_a", r"(?:max(?:imum|\.)?\s*)?(?:input\s*)?(?:short[\s-]*circuit\s*current|isc)"),
    ("efficiency_peak_pct", r"(?:peak|max(?:imum|\.)?)\s*(?:inverter\s*)?efficiency|efficienza\s*massima"),
    ("efficiency_weighted_pct", r"(?:cec|weighted|nominal\s*mppt|european)\s*(?:weighted\s*)?efficiency|efficienza\s*ponderata"),
    ("weight_kg", r"\bweight\b|\bpeso\b"),
    ("warranty_years", r"(?:standard\s*)?warranty|garanzia"),
)
_TABLE_FIELDS = {kind: tuple((key, re.compile(pattern, re.IGNORECASE)) for key, pattern in fields)
                 for kind, fields in _TABLE_FIELDS.items()}
_KILO = {"ac_power_nominal_w", "ac_power_max_va", "dc_power_max_w", "max_charge_power_w", "max_discharge_power_w"}


def _cells(line: str) -> list[dict]:
    return [{"name": m.group().strip(), "start": m.start(), "end": m.end()} for m in re.finditer(r"\S+(?: \S+)*", line)]


def _model_columns(kind: str, page_lines) -> tuple[list[dict], int, int]:
    """The header of a table of several models: on the page with the most rows of known fields, the number of columns
    most of those rows have; then the nearest line above with that many cells, each with a letter or a digit in it
    and none a plain measure (a name like «SUN2000-12K-», «Sunny Boy 3.0», «HVM 8.3»). A name broken over two lines
    is joined with the next line. Nothing when the sheet has no such table: its numbers are then not split by model."""
    best: tuple = ([], 0, 0)
    best_rows = 0
    for number, lines in enumerate(page_lines, 1):
        counts: dict = {}
        first_row: dict = {}
        for index, line in enumerate(lines):
            for _key, pattern in _TABLE_FIELDS[kind]:
                found = pattern.search(line)
                if found and found.start() <= 60:
                    values = _numbers_after(line, found.end())
                    if len(values) >= 2:
                        counts[len(values)] = counts.get(len(values), 0) + 1
                        first_row.setdefault(len(values), index)
                    break
        if not counts:
            continue
        columns = max(counts, key=lambda n: (counts[n], n))
        if counts[columns] < 2 or counts[columns] <= best_rows:
            continue
        for index in range(first_row[columns] - 1, max(-1, first_row[columns] - 40), -1):
            cells = _cells(lines[index])
            named = [c for c in cells if re.search(r"\d", c["name"]) and not re.fullmatch(
                r"[-+]?\d+(?:[.,]\d+)?\s*(?:v|a|w|kw|kva|kg|mm|hz|%|°c)?", c["name"], re.IGNORECASE)]
            if len(named) == columns and len(named) >= len(cells) - 1:
                best, best_rows = (named, number, index), counts[columns]
                break
    cells, page, index = best
    # a name printed on two lines: «SUN2000-12K-» over «MB0», or «SUN2000» over «-3KTL-M1»
    if cells and index >= 1 and all(c["name"].startswith("-") or len(c["name"]) <= 4 for c in cells):
        above = _cells(page_lines[page - 1][index - 1])
        for cell in cells:
            if above:
                near = min(above, key=lambda c: abs((c["start"] + c["end"]) - (cell["start"] + cell["end"])))
                if near["name"].endswith("-") or cell["name"].startswith("-"):
                    cell["name"] = near["name"] + cell["name"]
    if cells and all(c["name"].endswith("-") for c in cells) and index + 1 < len(page_lines[page - 1]):
        following = page_lines[page - 1][index + 1]
        for cell in cells:
            piece = re.search(r"\S+", following[max(0, cell["start"] - 3):cell["end"] + 6])
            if piece:
                cell["name"] += piece.group()
    return cells, page, index


def _nearest_column(columns, offset: int) -> int:
    return min(range(len(columns)), key=lambda n: abs((columns[n]["start"] + columns[n]["end"]) / 2 - offset))


def _table_proposals(kind: str, page_lines, name: str) -> list[Proposal]:
    """One proposal per model column of the table (one if the sheet has no such header). A row with one value applies
    to every column and is marked so; a row with other counts is matched to the columns by where it is printed."""
    columns, header_page, header_index = _model_columns(kind, page_lines)
    proposals = [Proposal(kind) for _c in columns] or [Proposal(kind)]
    for prop, column in zip(proposals, columns, strict=False):
        prop.record["model"] = column["name"]
        prop.anchors["model"] = Anchor(header_page, page_lines[header_page - 1][header_index], MEDIUM)
    for number, lines in enumerate(page_lines, 1):
        if columns and number < header_page:
            continue
        for index, line in enumerate(lines):
            if len(line) > 900 or (number == header_page and index <= header_index):
                continue
            for key, pattern in _TABLE_FIELDS[kind]:
                found = pattern.search(line)
                if not found or found.start() > 60:
                    continue
                values = _numbers_after(line, found.end())
                if not values:
                    continue
                _apply_row(proposals, columns, key, values, number, line, found.end())
                break
    for prop in proposals:
        _finish_row_fields(prop, page_lines, kind)
    return proposals


def _apply_row(proposals, columns, key, values, page, line, label_end) -> None:
    tail = line[label_end:].casefold()
    kilo = key in _KILO and bool(re.search(r"\bkw|\bkva", tail)) or (key in _KILO and bool(re.search(r"\(kw|\[kw|kw\)|kva\)", line.casefold())))
    # a total is not a limit per tracker: without «per MPPT» the printed current is not the tracker's
    if key in ("dc_current_max_per_mppt_a", "dc_isc_max_per_mppt_a") and not re.search(r"(?i)per\s*mpp|/\s*mpp|each\s*mpp|mppt?\s*[a-z]?\b.*\d", line):
        for prop in proposals:
            note = _("«{row}» does not say per tracker: left to you.").format(row=line.strip()[:70])
            if note not in prop.notes:
                prop.notes.append(note)
        return
    grams = key == "weight_kg" and bool(re.search(r"\d\s*g\b", tail))

    def scaled(v):
        if grams:
            return v / 1000.0
        return v * 1000.0 if kilo and v < 2000 else v
    if key == "mppt_count" and re.search(r"\d\s*/\s*\d", tail):
        return                      # «2 / 2+2»: trackers and strings in one cell, left for the designer
    if key in ("mppt_range", "full_power_mppt_min_v") or key == "dimensions_mm":
        width = 2 if key != "dimensions_mm" else 3
        groups = [values[i:i + width] for i in range(0, len(values), width)]
        groups = [g for g in groups if len(g) == width]
        if not groups:
            return
        for n, prop in enumerate(proposals):
            group = groups[0] if len(groups) == 1 else groups[n] if len(groups) == len(proposals) and n < len(groups) else None
            if group is None:
                continue
            confidence = MEDIUM
            if key == "mppt_range":
                low, high = group[0][0], group[1][0]
                if 0 < low < high:
                    prop.put("mppt_voltage_min_v", low, page, line, confidence)
                    prop.put("mppt_voltage_max_v", high, page, line, confidence)
            elif key == "full_power_mppt_min_v":
                prop.put(key, group[0][0], page, line, confidence)
            elif all(v[0] > 0 for v in group):
                prop.put(key, [v[0] for v in group], page, line, confidence)
        return
    if len(values) == 1:
        for prop in proposals:
            prop.put(key, scaled(values[0][0]), page, line, MEDIUM)
        return
    if not columns:
        for prop in proposals:
            prop.put(key, scaled(values[0][0]), page, line, LOW)
            note = _("A table with several columns and no model names: its first column was taken.")
            if note not in prop.notes:
                prop.notes.append(note)
        return
    if len(values) == len(columns):
        for prop, value in zip(proposals, values, strict=True):
            prop.put(key, scaled(value[0]), page, line, MEDIUM)
        return
    # other counts: by position, and only a value that falls in a column's own place
    taken = {}
    for value, offset in values:
        taken.setdefault(_nearest_column(columns, offset), value)
    if len(taken) == len(columns):
        for n, prop in enumerate(proposals):
            prop.put(key, scaled(taken[n]), page, line, LOW)


def _finish_row_fields(prop: Proposal, page_lines, kind: str) -> None:
    record = prop.record
    if kind in ("inverters", "microinverters"):
        text = " ".join(" ".join(lines) for lines in page_lines).casefold()
        if kind == "inverters":
            if re.search(r"three[\s-]*phase|3\s*/?\s*n\s*/?\s*pe|3w\s*\+|trifase|400\s*v\s*/?\s*230|3l\+|3\s*x\s*400", text):
                prop.put("phases", 3, 1, "three-phase in the sheet's words", LOW)
            elif re.search(r"single[\s-]*phase|1\s*/?\s*n\s*/?\s*pe|monofase|l\s*/\s*n\s*/\s*pe", text):
                prop.put("phases", 1, 1, "single-phase in the sheet's words", LOW)
            record.setdefault("type", "hybrid" if re.search(r"hybrid|ibrid|battery\s*(?:input|voltage|terminal|ready)", text) else "string")
    for key in ("mppt_count", "strings_per_mppt", "modules_per_unit", "phases"):
        if isinstance(record.get(key), float) and record[key].is_integer():
            record[key] = int(record[key])
    # a per-tracker limit is a list in the catalogue: one number for each tracker, when the tracker count is known
    if kind == "inverters" and isinstance(record.get("mppt_count"), int):
        for key in ("dc_current_max_per_mppt_a", "dc_isc_max_per_mppt_a"):
            value = record.get(key)
            if isinstance(value, (int, float)):
                record[key] = [float(value)] * record["mppt_count"]


_KIND_WORDS = (
    ("optimizers", r"power\s*optimi[sz]er|ottimizzatore\s*di\s*potenza|\boptimi[sz]er\b|\bts4\b"),
    ("microinverters", r"micro[\s-]*inverter|microinverter"),
    ("batteries", r"\bbattery\s*(?:pack|module|system|storage)|batteria|\bkwh\b.*\b(?:usable|capacity)\b|usable\s*(?:energy|capacity)|energy\s*storage\s*system"),
    ("modules", r"open[\s-]*circuit\s*voltage|\bvoc\b.*\bisc\b|\bisc\b|\bvmp"),
    ("inverters", r"\binverter\b|mppt?\b|\bsmart\s*energy\s*controller|\bgrid\s*(?:connected|tied)"),
)


def guess_kind(page_lines) -> str:
    """The kind of product a sheet is about, from the words that do not occur in the others; the first page weighs
    most (a module's sheet may name inverters, an inverter's may name batteries)."""
    first = " ".join(" ".join(lines) for lines in page_lines[:1]).casefold()
    whole = " ".join(" ".join(lines) for lines in page_lines[:6]).casefold()
    for text in (first, whole):
        for kind, pattern in _KIND_WORDS:
            if kind == "modules":
                if re.search(r"open[\s-]*circuit\s*voltage", text) and re.search(r"short[\s-]*circuit\s*current", text) and re.search(r"maximum\s*power|pmax|rated\s*power", text) and not re.search(r"\bmppt?\b", text):
                    return kind
            elif re.search(pattern, text):
                if kind == "batteries" and re.search(r"\bmppt?\b.*\bmppt?\b", text):
                    continue
                return kind
    return ""


def _manufacturer(page_lines, path_name: str, known=None) -> tuple[str, int, str]:
    """A maker the catalogue knows, printed in the sheet or in its file name, else nothing: the reader never guesses
    a name that is not there."""
    from . import KINDS, brands
    names = set(known or [])
    if not names:
        for kind in KINDS:
            names.update(n for n in brands(kind, "curated") if len(n) >= 3)
    ordered = sorted(names, key=len, reverse=True)
    for number, lines in enumerate(page_lines, 1):
        for line in lines:
            for name in ordered:
                if re.search(rf"(?<![A-Za-z]){re.escape(name)}(?![A-Za-z])", line, re.IGNORECASE):
                    return name, number, line
    for name in ordered:
        if re.search(rf"(?<![A-Za-z]){re.escape(name)}(?![A-Za-z])", path_name, re.IGNORECASE):
            return name, 0, path_name
    return "", 0, ""


def _family_code(page_lines, proposal: Proposal) -> tuple[str, int, str]:
    """The code of a module family, as the sheet prints it most often: a code naming the range of its classes
    (JKM460-485N-48QL6-DV) before any other."""
    powers = proposal.record.get("power_classes_w") or []
    if powers:
        low, high = int(min(powers)), int(max(powers))
        for number, lines in enumerate(page_lines, 1):
            for line in lines:
                found = re.search(rf"\b[A-Z0-9][A-Za-z0-9.\-_]*{low}\s*[-~/]\s*{high}[A-Za-z0-9.\-_]*", line)
                if found:
                    return re.sub(r"-F\d+\w*(?:-\w+)?$", "", found.group()), number, line
    counts: dict = {}
    seen: dict = {}
    for number, lines in enumerate(page_lines, 1):
        for line in lines:
            for found in MODEL_PATTERN.finditer(line):
                word = found.group()
                if re.search(r"\d", word) and not re.match(r"(?:IEC|ISO|EN|UL|CE|VDE|CEI|IP|MC4|PV\d|www|http)", word, re.IGNORECASE):
                    counts[word] = counts.get(word, 0) + 1
                    seen.setdefault(word, (number, line))
    if not counts:
        return "", 0, ""
    best = max(counts, key=lambda w: (counts[w], len(w)))
    return best, seen[best][0], seen[best][1]


def read(path, kind: str = "", *, known_makers=None) -> Reading:
    """Read a sheet. `kind` may be left to the reader. A sheet with no text at all is said to be scanned."""
    path = Path(path)
    page_lines = pages_of(path)
    reading = Reading(path.name, pages=len(page_lines))
    if not any(lines for lines in page_lines):
        reading.scanned = True
        reading.notes.append(_("No text in the file: a scanned sheet."))
        return reading
    reading.kind = kind or guess_kind(page_lines)
    if reading.kind == "modules":
        found = _module_proposal(page_lines, path.name, (lambda: pages_of(path, layout=True)) if path.suffix.lower() == ".pdf" else None)
        reading.proposals = [found] if found else []
        if found is None:
            reading.notes.append(_("No table of module classes passes Vmp × Imp = Pmax."))
    elif reading.kind in _TABLE_FIELDS:
        reading.proposals = [p for p in _table_proposals(reading.kind, page_lines, path.name) if len(p.record) > 1]
    else:
        reading.notes.append(_("The kind of product could not be told from the text."))
    maker, page, line = _manufacturer(page_lines, path.name, known_makers)
    for prop in reading.proposals:
        if maker:
            prop.put("manufacturer", maker, page, line, MEDIUM if page else LOW)
        if "model" not in prop.record:
            code, code_page, code_line = _family_code(page_lines, prop)
            if code:
                prop.put("model", code, code_page, code_line, LOW)
        prop.record["datasheet_url"] = path.name
        prop.anchors["datasheet_url"] = Anchor(0, path.name, HIGH)
    return reading
