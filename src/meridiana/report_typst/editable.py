"""The report as an editable file: ODT (odt.py, odfpy) and DOCX (word.py, python-docx) with the content of the PDF that
Typst lays out. This module is the shared part: the content model walked in order (headings numbered as Typst numbers
them, blocks flattened), the tables as neutral specifications both writers draw, the pictures (what Typst draws, the
charts and the cards, goes in as PNG at 300 dpi rendered by Typst itself from the same template, block by block), the
formulas (TeX to MathML with latex2mathml, to OMML with omml.py) and the look (look.py: fonts, greys, rules and the
vertical scale, the same as the PDF's).

    stats = export(document, root, target, "odt")     # or "docx"

`document` is what compose.py makes; `root` the folder of a Build (the images the PDF would use, the mitex package);
the stats: formulas, images, tables, fonts embedded, seconds. The libraries of the exports (odfpy, python-docx, lxml,
latex2mathml) are imported only here inside functions: without them the PDF works as always and the export says which
one to install.

The texts of the user are written as they are: characters that XML cannot hold are dropped, nothing is read as markup."""

from __future__ import annotations

import copy
import io
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

from .. import log, symbol_shapes
from ..i18n import _
from . import engine, look
from .blocks import plain

DRAWN = {"bars", "waterfall", "balance", "cash", "carpet", "dash", "tiles", "badge", "chips"}
CUT = "// ---- the document ----"
DATA = "editable-data.json"
NUMBER = re.compile(r"^(-?[0-9][0-9.]*)(,[0-9]+)?( .*)?$")
BAD_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff￾￿]")
PAGE_MM = 174.0          # the text's width: A4 less 20 mm on the left and 16 mm on the right
DPI = 300
DECIMAL_SHARE = 0.58     # where the comma falls in a cell of numbers, as in the template's decimal-cell
CHAR_CM = 0.148          # a character of the tables (Plex Sans Condensed, 8.4 pt), about: the width of an «auto» column
SUB_CM = 0.105           # a character of a symbol's subscript, about

# the fonts of the files: the name each font file carries (name ID 1, what Word and LibreOffice look a family up by)
FONT_FILES = {
    "light": ("IBM Plex Sans Light", "IBMPlexSans-Light.ttf"),
    "regular": ("IBM Plex Sans", "IBMPlexSans-Regular.ttf"),
    "medium": ("IBM Plex Sans Medm", "IBMPlexSans-Medium.ttf"),
    "strong": ("IBM Plex Sans SmBld", "IBMPlexSans-SemiBold.ttf"),
    "table": ("IBM Plex Sans Cond", "IBMPlexSansCondensed-Regular.ttf"),
    "table_strong": ("IBM Plex Sans Cond SmBld", "IBMPlexSansCondensed-SemiBold.ttf"),
    "mono": ("IBM Plex Mono", "IBMPlexMono-Regular.ttf"),
}
# the italic of the body's families: the symbols written as text are Plex Sans in its real italic
ITALIC_FILES = {"IBM Plex Sans": "IBMPlexSans-Italic.ttf", "IBM Plex Sans Light": "IBMPlexSans-LightItalic.ttf"}
GUTTER_MM = 6.0          # between the two columns of a «two», as the template's grid


class EditableMissing(RuntimeError):
    """A library of the editable exports is not installed."""


NEEDS = {"odt": [("odf", "odfpy"), ("latex2mathml", "latex2mathml")],
         "docx": [("docx", "python-docx"), ("lxml", "lxml"), ("latex2mathml", "latex2mathml")]}


def missing_libraries(kind: str) -> list[str]:
    import importlib.util
    return [package for module, package in NEEDS[kind] if importlib.util.find_spec(module) is None]


def require(kind: str) -> None:
    if kind not in NEEDS:
        raise ValueError(f"not an editable format: {kind!r}")
    absent = missing_libraries(kind)
    if absent:
        raise EditableMissing(_("The {kind} export needs a library that is not installed: {libraries}. "
                                "Install it with pip install {libraries}").format(
                                    kind=kind.upper(), libraries=" ".join(absent)))


def clean(text) -> str:
    """The text with the characters XML cannot hold dropped; everything else untouched."""
    return BAD_XML.sub("", str(text))


LETTERS = re.compile(r'<mrow>((?:<mi(?: mathvariant="normal")?>[^<&]</mi>){2,})</mrow>')
# a number on the decimal comma as TeX writes it, «30{,}0»: latex2mathml makes it three pieces, the comma an operator
# the other programs space out after
DECIMALS = re.compile(r'<mn( mathvariant="bold")?>([0-9.,]+)</mn><mrow><mo(?: mathvariant="bold")?>&#x0002C;</mo>'
                      r'</mrow><mn(?: mathvariant="bold")?>([0-9.,]+)</mn>')


def join_numbers(ml: str) -> str:
    """«30{,}0» as one number, «30,0», in MathML (R479: the lines with the numbers)."""
    while True:     # «1{,}234{,}567» joins one comma at a time
        joined = DECIMALS.sub(lambda m: f"<mn{m.group(1) or ''}>{m.group(2)},{m.group(3)}</mn>", ml)
        if joined == ml:
            return ml
        ml = joined


def join_letters(ml: str) -> str:
    """A name written as separate letters (eff, IAM) as one identifier: the other programs space the letters out."""
    def one(m):
        letters = re.findall(r'<mi( mathvariant="normal")?>([^<&])</mi>', m.group(1))
        variant = ' mathvariant="normal"' if all(v for v, _c in letters) else ""
        return f"<mi{variant}>" + "".join(c for _v, c in letters) + "</mi>"
    return LETTERS.sub(one, ml)


# ---- the look ----

class Look:
    """The look of the PDF (look.py) as the files need it: font names, sizes, colours, the vertical scale."""

    def __init__(self, style: dict):
        self.style = style
        f = style["font"]
        self.light = f.get("weight", 400) <= 300
        self.body = FONT_FILES["light" if self.light else "regular"][0]
        self.strong = FONT_FILES["strong"][0]
        self.medium = FONT_FILES["medium"][0]
        self.table = FONT_FILES["table"][0]
        self.table_strong = FONT_FILES["table_strong"][0]
        self.mono = FONT_FILES["mono"][0]
        self.symbol = FONT_FILES["regular"][0]      # the symbols written as text
        self.size = float(style.get("size", 9.5))
        self.table_size = float(style.get("table_size", 8.4))
        self.pad = float(style.get("table_pad", 3.6))
        self.ink = style["ink"]
        self.txt2 = style["txt2"]
        self.faint = style["faint"]
        self.accent = style["accent"]
        self.tint = style["tint"]
        self.head_fill = style["head_fill"]
        self.grid = style["grid"]
        self.rule = style["rule"]
        self.hf_colour = style["hf_colour"]
        self.hf_rule = float(style.get("hf_rule", 0.5))
        self.head_text = "#3a3a37"
        self.justify = bool(style.get("justify", True))
        self.hyphenate = bool(style.get("hyphenate", True))
        self.spacing = style["spacing"]
        self.margin_left = float(style.get("margin_left", 20))

    def sp(self, key: str) -> float:
        """A space of the vertical scale, in points."""
        return float(self.spacing[key])

    def cm(self, key: str) -> float:
        return look.points_to_cm(self.sp(key))

    def families(self) -> list[str]:
        used = ["light" if self.light else "regular", "strong", "medium", "table", "table_strong", "mono"]
        if self.light:
            used.append("regular")
        return [FONT_FILES[k][0] for k in used]


def font_files(look_: Look) -> dict:
    """{family: [(file, weight, style)]} for embed_fonts, only the files that exist."""
    folder = engine.font_folder()
    out = {}
    if folder is None:
        return out
    by_name = {name: file for name, file in FONT_FILES.values()}
    for family in look_.families():
        path = folder / "ibm-plex" / by_name[family]
        if path.is_file():
            out[family] = [(path, "normal", "normal")]
            italic = folder / "ibm-plex" / ITALIC_FILES.get(family, "-")
            if italic.is_file():
                out[family].append((italic, "normal", "italic"))
    return out


def hex_rgb(colour: str) -> str:
    """"#3b3a37" as "3B3A37"."""
    return colour.lstrip("#").upper()


# ---- the content, in order ----

@dataclass
class Item:
    kind: str
    block: dict
    width: float          # mm: the width the block has on the page
    text: str = ""        # a heading's text, numbered the way the PDF numbers it: «1.2<tab>Title»
    level: int = 0
    columns: list | None = None   # a «two»: [(width mm, [Item]), (width mm, [Item])], the left and the right column


def flatten(document: dict) -> list[Item]:
    """The blocks in the order they are written: keeps flattened, two columns kept side by side (an item «two» with
    the items of each column, as the template's grid), chapters and sections numbered as Typst numbers them (1, 1.1;
    the attachments and the sub-headings not) with a tab between the number and the title, a page break before a
    chapter dropped."""
    items: list[Item] = []
    state = {"chapter": 0, "section": 0, "numbered": False}

    def add(blocks, width, into):
        for b in blocks:
            k = b.get("k", "")
            if k == "two":
                ratio = b.get("ratio") or [1, 1]
                room = width - GUTTER_MM
                columns = []
                for side, share in (("left", ratio[0]), ("right", ratio[1])):
                    mine: list[Item] = []
                    w = room * share / sum(ratio)
                    add(b.get(side, []), w, mine)
                    columns.append((w, mine))
                if columns[0][1] and columns[1][1]:
                    into.append(Item("two", b, width, columns=columns))
                else:                        # one column with nothing: the other one at the whole width
                    for _w, mine in columns:
                        into.extend(mine)
            elif k in ("keep", "float"):
                add(b.get("items", []), width, into)
            elif k == "chapter":
                title = clean(b.get("title", ""))
                if str(b.get("id", "")).startswith("attachment"):
                    state["numbered"] = False
                    into.append(Item("chapter", b, width, title, 1))
                else:
                    state["chapter"] += 1
                    state["section"] = 0
                    state["numbered"] = True
                    into.append(Item("chapter", b, width, f"{state['chapter']}\t" + re.sub(r"^[0-9]+\.\s+", "", title), 1))
            elif k == "section":
                state["section"] += 1
                title = clean(plain(b.get("t")))
                number = f"{state['chapter']}.{state['section']}\t" if state["numbered"] else ""
                into.append(Item("section", b, width, number + title, 2))
            elif k == "sub":
                into.append(Item("sub", b, width, clean(plain(b.get("t"))), int(b.get("level", 3))))
            elif k == "attachment":
                state["numbered"] = False
                into.append(Item("attachment", b, width, clean(b.get("title", "")), 1))
                add(b.get("items", []), width, into)
            else:
                into.append(Item(k, b, width))

    add(document.get("body", []), PAGE_MM, items)
    out = []
    for i, item in enumerate(items):
        if item.kind == "pagebreak" and (i + 1 == len(items) or items[i + 1].kind in ("chapter", "attachment")):
            continue
        out.append(item)
    return out


def walk(items: list[Item]):
    """Every item, those inside the columns of a «two» too, in the order they are written."""
    for item in items:
        yield item
        for _w, column in item.columns or []:
            yield from walk(column)


# ---- a symbol as text (R506): a letter, its subscript and its superscript, Greek, a bar, as the PDF sets them ----

GREEK = {"alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ϵ", "varepsilon": "ε", "zeta": "ζ",
         "eta": "η", "theta": "θ", "vartheta": "ϑ", "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν",
         "xi": "ξ", "pi": "π", "varpi": "ϖ", "rho": "ρ", "varrho": "ϱ", "sigma": "σ", "varsigma": "ς", "tau": "τ",
         "upsilon": "υ", "phi": "ϕ", "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω", "Gamma": "Γ", "Delta": "Δ",
         "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π", "Sigma": "Σ", "Upsilon": "Υ", "Phi": "Φ", "Psi": "Ψ",
         "Omega": "Ω"}
SIGNS = {"cdot": "·", "times": "×", "sum": "∑ ", "prod": "∏ ", "int": "∫ ", "infty": "∞", "pm": "±", "le": "≤",
         "leq": "≤", "ge": "≥", "geq": "≥", "ne": "≠", "neq": "≠", "approx": "≈", "prime": "′", "circ": "°",
         "degree": "°", "partial": "∂", "to": "→", "rightarrow": "→", "ldots": "…", "cdots": "⋯", "%": "%", "_": "_",
         "{": "{", "}": "}", "#": "#", "&": "&", "$": "$", "lbrace": "{", "rbrace": "}", "vert": "|", "mid": "|"}
SPACES = {",": " ", ";": " ", ":": " ", ">": " ", " ": " ", "quad": " ", "qquad": "  ", "!": ""}
ACCENT_MARKS = {"bar": "̄", "overline": "̄", "hat": "̂", "widehat": "̂", "tilde": "̃", "widetilde": "̃", "dot": "̇",
                "ddot": "̈", "vec": "⃗"}
UPRIGHT = {"mathrm", "text", "textrm", "operatorname", "mathsf", "textnormal", "mathbf", "textbf", "boldsymbol"}
SYMBOL_TOKEN = re.compile(r"\\([A-Za-z]+|.)|([{}_^'])|(\s+)|(.)", re.S)


@dataclass
class Piece:
    text: str
    italic: bool = False
    pos: str = ""         # "", "sub" or "sup"


class _Symbol:
    def __init__(self, tex: str):
        self.tokens = [(m.group(1), m.group(2), m.group(3), m.group(4)) for m in SYMBOL_TOKEN.finditer(tex)]
        self.i = 0

    def peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def take(self):
        token = self.peek()
        self.i += 1
        return token

    def group(self, upright: bool, pos: str) -> list[Piece]:
        """What follows: a {group} or one token, as pieces."""
        token = self.peek()
        if token is None:
            return []
        if token[1] == "{":
            self.take()
            out = self.sequence(upright, pos, until="}")
            self.take()
            return out
        return self.atom(upright, pos)

    def sequence(self, upright: bool, pos: str, until: str | None = None) -> list[Piece]:
        out: list[Piece] = []
        while self.peek() is not None and not (until and self.peek()[1] == until):
            token = self.peek()
            if token[1] in ("_", "^"):
                self.take()
                out += self.group(upright, "sub" if token[1] == "_" else "sup") if not pos else \
                    self.group(upright, pos)          # a script of a script: one level, as text can
            elif token[1] == "'":
                self.take()
                out.append(Piece("′", False, pos))
            else:
                out += self.atom(upright, pos)
        return out

    def atom(self, upright: bool, pos: str) -> list[Piece]:
        command, brace, space, char = self.take()
        if space is not None:
            return []
        if brace == "{":
            out = self.sequence(upright, pos, until="}")
            self.take()
            return out
        if brace == "}":
            raise ValueError("unbalanced")
        if command is not None:
            if command in GREEK:
                return [Piece(GREEK[command], not upright, pos)]
            if command in SIGNS:
                return [Piece(SIGNS[command], False, pos)]
            if command in SPACES:
                return [Piece(SPACES[command], False, pos)] if SPACES[command] else []
            if command in ("left", "right", "big", "Big", "bigl", "bigr", "Bigl", "Bigr"):
                return []
            if command in UPRIGHT:
                return self.group(True, pos)
            if command == "mathit":
                return self.group(False, pos)
            if command in ACCENT_MARKS:
                inner = self.group(upright, pos)
                first = next((p for p in inner if p.pos == pos and p.text.strip()), None)
                if first is None:
                    return inner
                first.text = first.text + ACCENT_MARKS[command]
                return inner
            raise ValueError("not a symbol: \\" + command)
        if char.isalpha() and char.isascii():
            return [Piece(char, not upright, pos)]
        return [Piece("−" if char == "-" else char, False, pos)]


def symbol_pieces(tex: str) -> list[Piece] | None:
    """A symbol's TeX (P_{STC}, \\eta_{200}/\\eta_{STC}, \\bar{f_s}, U_{OC\\,MAX}) as pieces of text: the letters in
    italic as the PDF's math sets them, the words of \\mathrm and \\text upright, subscripts and superscripts, the Greek
    letters, an accent as its combining mark; None for what text cannot be (a fraction, a root): that stays a formula."""
    tex = (tex or "").strip()
    if not tex:
        return []
    try:
        parser = _Symbol(tex)
        pieces = parser.sequence(False, "")
        if parser.peek() is not None:
            return None
    except (ValueError, IndexError, TypeError):
        return None
    out: list[Piece] = []
    for p in pieces:
        if out and out[-1].italic == p.italic and out[-1].pos == p.pos:
            out[-1].text += p.text
        elif p.text:
            out.append(Piece(p.text, p.italic, p.pos))
    return out


@dataclass
class Run:
    text: str
    kind: str = ""        # "" plain, "b" bold, "m" muted, "mark" (text: the level), "formula" (text: the name)


def runs(c) -> list[Run]:
    """A piece of text (a string, a run or a list of them) as flat runs."""
    if c is None:
        return []
    if isinstance(c, str):
        return [Run(clean(c))] if c else []
    if isinstance(c, (list, tuple)):
        return [r for x in c for r in runs(x)]
    if isinstance(c, dict):
        if "b" in c or "bb" in c:
            return [Run(clean(c.get("b") or c.get("bb") or ""), "b")]
        if "m" in c:
            return [Run(clean(c["m"]), "m")]
        if "mark" in c:
            return [Run(str(c["mark"]), "mark")]
        if "formula" in c:
            return [Run(str(c["formula"]), "formula")]
    return []


def number_parts(value: str) -> tuple[str, str]:
    """A value as its whole part and the rest (the decimals and the unit), as the template splits it; ("", "") for
    anything that is not a number."""
    m = NUMBER.match(value or "")
    if m is None:
        return "", ""
    return m.group(1), (m.group(2) or "") + (m.group(3) or "")


# ---- tables, as neutral specifications ----

@dataclass
class Cell:
    content: object = ""
    tex: str = ""             # a symbol, shown as a formula
    align: str = "left"       # left, right, decimal (the digits on the comma)
    kind: str = "cell"        # cell, head, label (the grey of facts), source (the register's code), small
    strong: bool = False
    fill: str | None = None
    span: int = 1


@dataclass
class TableSpec:
    widths: list              # cm
    rows: list                # lists of Cell
    head_rows: int = 0        # how many of the first rows are the header (repeated on each page)
    share: float = DECIMAL_SHARE   # where the comma falls in a decimal cell, as a share of its width


def fit(widths, total: float, fixed: float = 0.0) -> list[float]:
    """Relative widths as cm filling `total`, the last one kept at `fixed` cm when asked."""
    if fixed:
        rest = fit(widths[:-1], total - fixed)
        return rest + [fixed]
    s = float(sum(widths)) or 1.0
    return [round(total * w / s, 3) for w in widths]


def table_spec(b: dict, width_mm: float) -> TableSpec:
    total = width_mm / 10.0
    n = len(b["widths"])
    source = bool(b.get("source"))
    widths = fit(b["widths"], total, 1.5 if source and n > 1 else 0.0)
    right = set(b.get("right") or [])
    rows_in = b.get("rows") or []
    decimal = [i in right and any(isinstance(r, list) and len(r) > i and isinstance(r[i], str) and "," in r[i]
                                  for r in rows_in) for i in range(n)]
    rows = []
    head_rows = 0
    if b.get("head"):
        head_rows = 1
        rows.append([Cell(h, align="right" if i in right else "left", kind="head", fill=None) for i, h in enumerate(b["head"])])
    for r, row in enumerate(rows_in):
        if isinstance(row, dict):
            rows.append([Cell(row.get("group", ""), strong=True, span=n)])
            continue
        result = r == b.get("result", -1)
        cells = []
        for i, c in enumerate(row):
            kind = "source" if source and i == n - 1 else "cell"
            if kind == "cell" and decimal[i] and isinstance(c, str):
                align = "decimal"
            else:
                align = "right" if i in right else "left"
            cells.append(Cell(c, align=align, kind=kind, strong=result, fill="tint" if result else None))
        rows.append(cells)
    return TableSpec(widths, rows, head_rows)


def facts_spec(b: dict, width_mm: float) -> TableSpec:
    total = width_mm / 10.0
    rows_in = b.get("rows") or []
    with_source = any(len(r) > 2 for r in rows_in)
    ratio = b.get("ratio") or [5, 6]
    widths = fit(list(ratio) + ([1] if with_source else []), total, 1.6 if with_source else 0.0)
    rows = []
    for r in rows_in:
        value = r[1]
        align = "left" if isinstance(value, str) and len(value) > 44 else "right"
        cells = [Cell(r[0], kind="label"), Cell(value, align=align, strong=bool(b.get("strong")))]
        if with_source:
            cells.append(Cell(r[2] if len(r) > 2 else "", align="right", kind="source"))
        rows.append(cells)
    return TableSpec(widths, rows, 0)


def step_spec(b: dict, texts: dict, width_mm: float) -> TableSpec:
    """The «where:» table of a step: symbol, quantity, value (digits on the comma), source."""
    total = width_mm / 10.0
    quantities = list(b.get("inputs") or []) + ([b["result"]] if b.get("result") else [])
    # the template's columns: 13 mm for the symbol, the value as wide as its widest (the whole part right, the rest
    # left, the comma between), what is left to the quantity and the source as 1 to 0.9
    wholes = [len(q.get("int") or number_parts(q.get("value", ""))[0]) for q in quantities] or [0]
    rests = [len(q.get("rest") or number_parts(q.get("value", ""))[1]) if (q.get("int") or number_parts(q.get("value", ""))[0])
             else len(q.get("value", "")) for q in quantities] or [0]
    whole_cm = max(wholes) * CHAR_CM
    value = min(5.6, max(len(texts["value"]) * CHAR_CM * 0.92, whole_cm + max(rests) * CHAR_CM) + 0.3)
    # the symbol's column: the template's 13 mm, wider for a long symbol (η200/ηSTC, PSTC,campo) that Typst lets run
    # over and a cell of the editable files would break
    symbol = max([sum(len(p.text) * (SUB_CM if p.pos else CHAR_CM * 1.1) for p in (symbol_pieces(q.get("symbol")) or []))
                  for q in quantities] or [0.0]) + 0.55
    symbol = round(min(2.6, max(1.3, symbol)), 3)
    rest = total - symbol - value
    widths = [symbol, round(rest / 1.9, 3), round(value, 3), round(rest * 0.9 / 1.9, 3)]
    rows = [[Cell(texts["symbol"], kind="head"), Cell(texts["quantity"], kind="head"),
             Cell(texts["value"], kind="head", align="right"), Cell(texts["source"], kind="head")]]
    for q in quantities:
        result = q is b.get("result")
        whole = q.get("int")
        if whole is None:
            whole = number_parts(q.get("value", ""))[0]
        rows.append([Cell(tex=q.get("symbol") or "", strong=result, fill="tint" if result else None),
                     Cell(q.get("label", ""), strong=result, fill="tint" if result else None),
                     Cell(q.get("value", ""), align="decimal" if whole else "right", strong=result,
                          fill="tint" if result else None),
                     Cell(q.get("source", ""), kind="small", fill="tint" if result else None)])
    share = min(0.85, max(0.2, (whole_cm + 0.05) / max(0.5, value - 0.28))) if whole_cm else 0.5
    return TableSpec(widths, rows, 1, share=share)


# ---- the pictures ----

@dataclass
class Picture:
    data: bytes
    mime: str
    width: float          # cm
    height: float         # cm


def image_size(data: bytes) -> tuple[int, int]:
    from PIL import Image
    with Image.open(io.BytesIO(data)) as im:
        return im.size


class Drawer:
    """Typst draws a block of the report to a PNG: the template cut at «the document», one page as wide as the block and
    as tall as it needs, the block's JSON beside it. One compiler for all the blocks."""

    def __init__(self, root: Path, document: dict):
        import typst
        self.typst = typst
        self.root = Path(root)
        data = {"style": look.style(), "tex": {}, **document, "marks": symbol_shapes.report_marks()}
        (self.root / DATA).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        template = engine.TEMPLATE.read_text(encoding="utf-8")
        self.head = template[:template.index(CUT)].replace('json("data.json")', f'json("{DATA}")')
        self.compiler = typst.Compiler(root=str(self.root), font_paths=engine.fonts())
        self.count = 0

    def compile(self, source: str, ppi: int = DPI) -> bytes:
        path = self.root / "editable-block.typ"
        path.write_text(source, encoding="utf-8")
        out = self.compiler.compile(str(path), format="png", ppi=ppi)
        self.count += 1
        return out[0] if isinstance(out, list) else out

    def block(self, block: dict, width_mm: float) -> bytes:
        (self.root / "editable-block.json").write_text(json.dumps(block, ensure_ascii=False), encoding="utf-8")
        return self.compile(self.head + f'\n#set page(width: {width_mm + 2:.2f}mm, height: auto, margin: 1mm, '
                            'header: none, footer: none)\n#render(json("editable-block.json"))\n')

    def snippet(self, code: str, ppi: int = DPI) -> bytes:
        return self.compile(self.head + '\n#set page(width: auto, height: auto, margin: 0pt, header: none, footer: none)\n'
                            + code + "\n", ppi)


class Context:
    """One export: the document, its look and its content in order, the pictures made once, the formulas converted
    once."""

    def __init__(self, document: dict, root: Path):
        self.document = document
        self.root = Path(root)
        self.look = Look(document.get("style") or look.style())
        self.doc = document.get("doc") or {}
        self.texts = document.get("texts") or {}
        self.tex = document.get("tex") or {}
        self.lang = document.get("lang") or "en"
        self.items = flatten(document)
        self.stats = {"formulas": 0, "images": 0, "tables": 0, "fonts": 0, "seconds": 0.0}
        self._drawer = None
        self._marks: dict = {}
        self._mathml: dict = {}
        self._omml: dict = {}
        self._symbols: dict = {}
        self._logo = False

    # words: the translated ones of the document, a fallback for a document made by hand
    def word(self, key: str) -> str:
        if self.texts.get(key):
            return clean(self.texts[key])
        fallback = {"symbol": _("Symbol"), "quantity": _("Quantity"), "value": _("Value"), "source": _("Source"),
                    "where": _("where:"), "with_values": _("With the values:"), "result": _("result"),
                    "reference": _("Reference"), "contents": _("Contents"), "attachment": _("Attachment"),
                    "report": _("Technical report"), "plant": _("Plant"), "page_of": _("page {n} of {total}")}
        return fallback.get(key, key)

    def step_words(self) -> dict:
        return {k: self.word(k) for k in ("symbol", "quantity", "value", "source")}

    @property
    def drawer(self) -> Drawer:
        if self._drawer is None:
            self._drawer = Drawer(self.root, self.document)
        return self._drawer

    def safe(self, what: str, make):
        """make() or None: a picture that cannot be drawn leaves a gap, never a failed export."""
        try:
            return make()
        except Exception as error:   # noqa: BLE001  Typst, PIL or the file: whichever, the rest of the report goes on
            log.complain("report export: " + what, error)
            return None

    # pictures
    def sized(self, data: bytes, mime: str, width_mm: float, max_h_mm: float | None = None, dpi: int | None = DPI) -> Picture:
        """A picture at its natural size when it was drawn at `dpi`, or at the block's width; never wider than the
        block, never taller than `max_h_mm`."""
        px_w, px_h = image_size(data)
        w = px_w * 25.4 / dpi if dpi else width_mm
        w = min(w, width_mm) if dpi else w      # the drawing's 1 mm margins inside the text's width, not past it
        h = w * px_h / px_w
        if max_h_mm and h > max_h_mm:
            w, h = w * max_h_mm / h, max_h_mm
        return Picture(data, mime, round(w / 10, 3), round(h / 10, 3))

    def shown(self, name) -> bool:
        return bool(name) and name not in (self.document.get("missing") or []) and (self.root / str(name)).is_file()

    def drawn(self, item: Item) -> Picture | None:
        return self.safe(item.kind, lambda: self.sized(self.drawer.block(item.block, item.width), "image/png", item.width))

    def figure(self, b: dict, width_mm: float, max_h: float = 118.0) -> Picture | None:
        """A figure of the report without its caption (the writers write that): a 3D view as it is, anything else as the
        template frames it (its chips, its tint)."""
        name = b.get("image")
        if not self.shown(name):
            return None
        max_h = float(b.get("max_h") or max_h)

        def make():
            path = self.root / name
            data = path.read_bytes()
            kind = engine.image_format(data)
            if str(name).startswith("view_") and kind in ("png", "jpg"):
                return self.sized(data, "image/png" if kind == "png" else "image/jpeg", width_mm, max_h, dpi=None)
            block = {"k": "figure", "image": name, "caption": None, "max_h": max_h, "tint": bool(b.get("tint")),
                     "inset": b.get("inset", 0), "chips": b.get("chips")}
            return self.sized(self.drawer.block(block, width_mm), "image/png", width_mm, max_h + 25.0)
        return self.safe("figure " + str(name), make)

    def mark(self, level: str) -> Picture | None:
        if level not in self._marks:
            self._marks[level] = self.safe("mark", lambda: Picture(self.drawer.snippet(f'#mark("{level}")', 600), "image/png",
                                                                 0.29, 0.29))
        return self._marks[level]

    def logo(self, height_mm: float = 10.0, room_mm: float = 40.0) -> Picture | None:
        """The logo of the header, as PNG or JPEG, inside the room it has; None when the document has none."""
        name = self.doc.get("logo")
        if not self.shown(name):
            return None

        def make():
            data = (self.root / name).read_bytes()
            kind = engine.image_format(data)
            if kind not in ("png", "jpg"):
                data, kind = self.drawer.snippet(f'#image("{name}")', 600), "png"
            px_w, px_h = image_size(data)
            h = height_mm
            w = h * px_w / px_h
            if w > room_mm:
                w, h = room_mm, room_mm * px_h / px_w
            return Picture(data, "image/png" if kind == "png" else "image/jpeg", round(w / 10, 3), round(h / 10, 3))
        return self.safe("logo", make)

    # formulas
    def tex_of(self, name: str) -> str:
        return clean(self.tex.get(name) or "")

    def mathml(self, tex: str) -> str | None:
        if tex not in self._mathml:
            try:
                import latex2mathml.converter
                self._mathml[tex] = join_numbers(join_letters(latex2mathml.converter.convert(tex)))
            except Exception as error:   # noqa: BLE001  a TeX the converter cannot read stays as text
                log.complain("report export: formula", error)
                self._mathml[tex] = None
        return self._mathml[tex]

    def symbol(self, tex: str) -> list[Piece] | None:
        """A symbol as pieces of text (symbol_pieces), None when it has to stay a formula."""
        if tex not in self._symbols:
            self._symbols[tex] = symbol_pieces(tex)
        return copy.deepcopy(self._symbols[tex])

    def formula_sizes(self, formulas: list[tuple[str, float, str]]) -> list[tuple[float, float] | None]:
        """The size (cm) each formula takes in the PDF, (TeX, text size in points, "display" or "numbers"), all of them
        laid out by Typst in one go, a page each: what an ODT frame needs when no LibreOffice measures them."""
        if not formulas:
            return []
        name = "editable-formulas.json"

        def make():
            (self.root / name).write_text(json.dumps([{"tex": t, "size": s, "kind": k} for t, s, k in formulas],
                                                     ensure_ascii=False), encoding="utf-8")
            source = (self.drawer.head + f'\n#set page(width: auto, height: auto, margin: 0pt, header: none, footer: none)\n'
                      f'#for f in json("{name}") {{ page({{ set text(f.size * 1pt); '
                      'if f.kind == "numbers" { numbers-line(f.tex) } else { mitex(f.tex) } }) }\n')
            path = self.root / "editable-formulas.typ"
            path.write_text(source, encoding="utf-8")
            out = self.drawer.compiler.compile(str(path), format="png", ppi=144)
            pages = out if isinstance(out, list) else [out]
            if len(pages) != len(formulas):
                raise RuntimeError(f"{len(pages)} pages for {len(formulas)} formulas")
            sizes = []
            for data in pages:
                w, h = image_size(data)
                sizes.append((round(w * 2.54 / 144, 3), round(h * 2.54 / 144, 3)))
            return sizes
        return self.safe("formula sizes", make) or [None] * len(formulas)

    def omml(self, tex: str):
        """The OMML element of a formula (lxml, a fresh copy), None when it cannot be made."""
        if tex not in self._omml:
            try:
                from .omml import omml as convert
                ml = self.mathml(tex)
                self._omml[tex] = convert(ml, inline=True) if ml else None
            except Exception as error:   # noqa: BLE001
                log.complain("report export: formula", error)
                self._omml[tex] = None
        return copy.deepcopy(self._omml[tex])

    # the head of the document
    def toc_entries(self) -> list[tuple[int, str]]:
        return [(it.level, it.text) for it in walk(self.items) if it.kind in ("chapter", "section", "attachment")
                and it.level <= int(self.look.style.get("toc_levels", 2))]

    def has_contents(self) -> bool:
        return bool(self.toc_entries()) and (self.document.get("cover") is not None or self.document.get("toc") == "page")

    def header_lines(self) -> list[tuple[str, str]]:
        """The three lines of the header's right side: (text, "strong" or "muted")."""
        d = self.doc
        short = d.get("doc_short") or self.word("report")
        sub = d.get("head_sub") or ""
        rev = d.get("revision") or ""
        return [(clean(short + " · " + (d.get("head_title") or "")), "strong"), (clean(sub), "muted"),
                (clean(rev + (" · " if rev else "") + (d.get("date") or "")), "muted")]

    def footer_cells(self) -> list[list[tuple[str, str]]]:
        """The footer's three columns, each a list of (text, "strong" or "plain"); the page line is the writer's."""
        d = self.doc
        return [[(clean(d.get("foot_left", "")), "strong"), (clean(d.get("foot_left2", "")), "plain")],
                [(clean(d.get("foot_centre", "")), "plain"), (clean(d.get("foot_centre2", "")), "plain")],
                [("", "page"), (clean(d.get("foot_right2", "")), "plain")]]

    def page_line(self) -> list[str]:
        """The page line split around {n} and {total}: strings, with "{n}" and "{total}" kept as their own parts."""
        return [p for p in re.split(r"(\{n\}|\{total\})", self.word("page_of")) if p]

    def wants_logo_placeholder(self) -> bool:
        return bool(self.doc.get("logo_placeholder")) and not self.shown(self.doc.get("logo"))


def export(document: dict, root: Path, target: Path, kind: str, measure: bool = True) -> dict:
    """Writes `document` as an ODT (kind "odt") or a DOCX (kind "docx") at `target`. `root` is the folder of a Build
    (the images the PDF would use). With `measure`, a LibreOffice found on the computer lays the file out once, hidden
    (office.py): the ODT gets each formula's frame at the size LibreOffice gives it and both files the contents with
    their page numbers; without one the frames have the size Typst gives the formulas and the contents no numbers
    until they are updated. Returns the stats: formulas, images, tables, fonts embedded, measured (by LibreOffice),
    seconds."""
    require(kind)
    start = time.time()
    ctx = Context(document, Path(root))
    ctx.stats["measured"] = False
    if kind == "odt":
        from . import odt
        odt.write(ctx, Path(target))
    else:
        from . import word
        word.write(ctx, Path(target))
    if measure:
        from . import office
        found = office.measure(Path(target))
        if found:
            if kind == "odt":
                odt.apply(Path(target), found)
            else:
                word.apply(Path(target), found)
            ctx.stats["measured"] = True
    ctx.stats["seconds"] = round(time.time() - start, 2)
    return ctx.stats
