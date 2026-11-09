"""How Meridio reads a sentence aloud in Italian (R493, Daniel 06/11/2026: «al posto di cappa vu quando c'è kW devono
dire chilowatt»): units, numbers written the Italian way, the trade's acronyms, standards, dates and hours, signs,
codes of jobs and models, all turned into the words a designer would say, before the voice (Kokoro or the system's)
gets the sentence. The rules are data, in reading_it.json next to this module; here is only how they are applied
and the grammar of Italian numbers. No Qt.

    >>> normalize("Il tuo impianto da 45 kWp produce circa 58.000 kWh all'anno.")
    "Il tuo impianto da quarantacinque chilowatt picco produce circa cinquantottomila chilowattora all'anno."
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

RULES = Path(__file__).with_name("reading_it.json")

_UNITS = ("zero", "uno", "due", "tre", "quattro", "cinque", "sei", "sette", "otto", "nove", "dieci", "undici",
          "dodici", "tredici", "quattordici", "quindici", "sedici", "diciassette", "diciotto", "diciannove")
_TENS = {2: "venti", 3: "trenta", 4: "quaranta", 5: "cinquanta", 6: "sessanta", 7: "settanta", 8: "ottanta",
         9: "novanta"}

# a number written the Italian way: 58.000 · 1.043,5 · 0,85 · 45 (the thousands' points are optional)
NUM = r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?"
_NUM_FULL = re.compile(rf"(?:{NUM})\Z")
_THOUSANDS = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?\Z")


def _below_1000(n: int) -> str:
    hundreds, rest = divmod(n, 100)
    head = "" if not hundreds else "cento" if hundreds == 1 else _UNITS[hundreds] + "cento"
    if not rest:
        return head
    if rest < 20:
        tail = _UNITS[rest]
    else:
        tens, unit = divmod(rest, 10)
        tail = _TENS[tens]
        if unit in (1, 8):
            tail = tail[:-1]                    # ventuno, trentotto
        tail += _UNITS[unit] if unit else ""
    if head and tail[0] == "o":                 # centotto, centottanta
        head = head[:-1]
    return head + tail


def cardinal(n: int) -> str:
    """An integer in Italian words: 45 «quarantacinque», 58000 «cinquantottomila», 2026 «duemilaventisei»."""
    if n < 0:
        return "meno " + cardinal(-n)
    if n == 0:
        return "zero"
    parts = []
    for size, one, many in ((10 ** 9, "un miliardo", "miliardi"), (10 ** 6, "un milione", "milioni")):
        count, n = divmod(n, size)
        if count:
            parts.append(one if count == 1 else f"{cardinal(count)} {many}")
    thousands, n = divmod(n, 1000)
    words = ""
    if thousands:
        lead = _below_1000(thousands) if thousands < 1000 else cardinal(thousands)
        words = "mille" if thousands == 1 else (lead[:-1] if lead.endswith("uno") else lead) + "mila"
    words += _below_1000(n) if n else ""
    if words:
        parts.append(words)
    out = " ".join(parts)
    return out[:-3] + "tré" if out.endswith("tre") and len(out) > 3 else out


def digits(s: str) -> str:
    """Each digit by itself: «02» «zero due»."""
    return " ".join(_UNITS[int(d)] for d in s if d.isdigit())


def _decimals(s: str) -> str:
    zeros = len(s) - len(s.lstrip("0"))
    rest = s[zeros:]
    said = ["zero"] * zeros
    if rest:
        said.append(cardinal(int(rest)) if len(rest) <= 3 else digits(rest))
    return " ".join(said)


def number(s: str) -> str:
    """A number as Meridiana writes it (58.000, 1.043,5, 0,85; a point and one or two digits after it, the English
    way, is a decimal too) in words."""
    s = s.strip()
    if re.fullmatch(r"\d+\.\d{1,2}", s):
        s = s.replace(".", ",")
    whole, _, frac = s.partition(",")
    out = cardinal(int(whole.replace(".", "") or "0"))
    return f"{out} virgola {_decimals(frac)}" if frac else out


def _is_one(s: str) -> bool:
    return s.strip() == "1"


@lru_cache(maxsize=1)
def rules() -> dict:
    with open(RULES, encoding="utf-8") as f:
        return json.load(f)


def _alternation(keys) -> str:
    return "|".join(re.escape(k) for k in sorted(keys, key=len, reverse=True))


def _letters(run: str, r: dict) -> str:
    if run in r["sigle"]:
        return r["sigle"][run]
    if run.isupper() and len(run) <= 4:
        return " ".join(r["lettere"].get(ch, ch) for ch in run)
    return run


def _code(token: str, r: dict) -> str:
    """A code of letters and digits, read in pieces: «SUN2000-10KTL-M1», «R02», «IFC4», «IP65»."""
    out = []
    for piece in re.split(r"[-_/]+", token):
        for run in re.findall(r"\d+(?:\.\d+)*|[A-Za-z]+", piece):
            if run[0].isdigit():
                if "." in run:
                    out.append(" punto ".join(_digit_run(p) for p in run.split(".")))
                else:
                    out.append(_digit_run(run))
            else:
                out.append(_letters(run, r))
    return " ".join(out)


def _digit_run(run: str) -> str:
    return digits(run) if (run.startswith("0") and len(run) > 1) or len(run) > 4 else cardinal(int(run))


def _norm_number(num: str, edition_year: str | None, edition_month: str | None, r: dict) -> str:
    """The number of a standard: «0-21» «zero ventuno», «64-8/7» «sessantaquattro otto parte sette»,
    «61853-1» «sessantuno ottocentocinquantatré parte uno», «1991-1-3» «millenovecentonovantuno parte uno tre», an
    edition «:2026-07» «edizione luglio duemilaventisei». A CEI number of two pieces (0-21, 64-8) is one name; after
    an EN or IEC number of four digits or more the dash opens the part; a slash always does (64-8/7)."""
    pieces = re.split(r"([-/])", num)
    first = pieces[0]
    if len(first) >= 5:
        rest = first[2:]
        said = [cardinal(int(first[:2])), _decimals(rest) if rest.startswith("0") else cardinal(int(rest))]
    else:
        said = [cardinal(int(first))]
    long_first = len(first) >= 4
    dashes = 0
    for sep, part in zip(pieces[1::2], pieces[2::2], strict=True):
        opens = sep == "/" or (long_first and dashes == 0) or (not long_first and dashes == 1)
        said += [r["norme"]["parte"], cardinal(int(part))] if opens else [cardinal(int(part))]
        dashes += sep == "-"
    out = " ".join(said)
    if edition_year:
        month = r["mesi"][int(edition_month) - 1] + " " if edition_month and 1 <= int(edition_month) <= 12 else ""
        out += f", {r['norme']['edizione']} {month}{cardinal(int(edition_year))},"
    return out


def _date(day: str, month: str, year: str | None, r: dict) -> str | None:
    d, m = int(day), int(month)
    if not (1 <= d <= 31 and 1 <= m <= 12):
        return None
    out = ("primo" if d == 1 else cardinal(d)) + " " + r["mesi"][m - 1]
    if year:
        y = int(year)
        out += " " + cardinal(y + 2000 if len(year) == 2 else y)
    return out


def _one(word_after: str) -> str:
    """«1» before a word: «una» before a feminine one (it ends in a), «un» before the others; «uno» alone."""
    if not word_after or word_after.lower() in _NOT_NOUNS:
        return "uno"
    return "una" if word_after.lower().endswith("a") else "un"


_NOT_NOUNS = {"e", "ed", "o", "od", "a", "ad", "di", "da", "in", "con", "su", "per", "tra", "fra", "al", "del", "dal",
              "nel", "sul", "è", "sono", "solo", "soltanto", "contro", "oppure"}
_ROMAN = {"I": 1, "V": 5, "X": 10}


def _roman(s: str) -> int:
    total = 0
    for ch, nxt in zip(s, s[1:] + " ", strict=True):
        value = _ROMAN[ch]
        total += -value if nxt in _ROMAN and _ROMAN[nxt] > value else value
    return total


def _sounds(t: str, r: dict) -> str:
    """The rewrites of `pronuncia` (any case, the whole word) and of `pronuncia_contesto` (only after the words of
    `dopo` or before those of `prima`)."""
    for c in r.get("pronuncia_contesto", []):
        word, said = re.escape(c["parola"]), c["lettura"]
        if c.get("dopo"):
            t = re.sub(rf"(?i)(?<![\w])({_alternation(c['dopo'])})(\s+){word}(?![\w])",
                       lambda m, s=said: m.group(1) + m.group(2) + s, t)
        if c.get("prima"):
            t = re.sub(rf"(?i)(?<![\w]){word}(\s+(?:{_alternation(c['prima'])}))(?![\w])",
                       lambda m, s=said: s + m.group(1), t)
    sounds = r.get("pronuncia", {})
    if sounds:
        folded = {k.casefold(): v for k, v in sounds.items()}
        t = re.sub(rf"(?i)(?<![\w])({_alternation(sounds)})(?![\w])", lambda m: folded[m.group(1).casefold()], t)
    return t


def normalize(text: str) -> str:
    """`text` as it is to be said in Italian."""
    r = rules()
    t = text.replace("\u00a0", " ").replace("\u202f", " ")

    # abbreviations with points first (D.Lgs., art., par., c.c.): their points are not decimals nor stops
    abbreviations = {**r["abbreviazioni"], **{k: v for k, v in r["sigle"].items() if "." in k}}
    t = re.sub(rf"(?<![\w.])({_alternation(abbreviations)})", lambda m: abbreviations[m.group(1)], t)
    t = re.sub(r"(?<![\w])n°", "numero", t)
    # Roman numbers of annexes and sections: «All. III» «allegato tre»; «1° gennaio» «primo gennaio»
    t = re.sub(r"\b(allegato|titolo|capo|sezione|Allegato|Titolo|Capo|Sezione)\s+([IVX]{1,5})\b",
               lambda m: f"{m.group(1)} {cardinal(_roman(m.group(2)))}", t)
    t = re.sub(rf"(?<![\w])1°\s+(?=(?:{'|'.join(r['mesi'])}|piano)\b)", "primo ", t)

    # standards with their numbers and edition: CEI 0-21:2026-07, CEI 64-8/7, IEC 61853-1, CEI EN 62446-1
    prefixes = r["norme"]["prefissi"]
    t = re.sub(rf"(?<![\w])({_alternation(prefixes)})\s+(\d+(?:[-/]\d+)*)(?::(\d{{4}})(?:-(\d{{2}}))?)?(?![\w])",
               lambda m: prefixes[m.group(1)] + " " + _norm_number(m.group(2), m.group(3), m.group(4), r), t)

    # a job's code, the year and the number: «commessa 26116» «commessa ventisei centosedici»
    job = r["commessa"]
    sizes = job["gruppi"]

    def job_code(m):
        code, at, said = m.group(2), 0, []
        for size in sizes:
            said.append(_digit_run(code[at:at + size]) if code[at:at + size].lstrip("0") else digits(code[at:at + size]))
            at += size
        return m.group(1) + " " + " ".join(said)
    t = re.sub(rf"\b({_alternation(job['parole'])})\s+(\d{{{sum(sizes)}}})\b", job_code, t)

    # dates and hours: 06/11/2026, 2026-11-06, «il 30/10», 14:30, the scale 1:100
    t = re.sub(r"(?<![\w/.,])(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})(?![\w/])",
               lambda m: _date(m.group(1), m.group(2), m.group(3), r) or m.group(0), t)
    t = re.sub(r"(?<![\w/.,-])(\d{4})-(\d{2})-(\d{2})(?![\w-])",
               lambda m: _date(m.group(3), m.group(2), m.group(1), r) or m.group(0), t)
    t = re.sub(r"\b(il|del|dal|al|entro il|fino al|dell')\s?(\d{1,2})/(\d{1,2})(?![\w/])",
               lambda m: (m.group(1) + " " + (_date(m.group(2), m.group(3), None, r) or f"{m.group(2)}/{m.group(3)}")), t)
    t = re.sub(r"\bscala\s+(\d+):(\d+)\b", lambda m: f"scala {cardinal(int(m.group(1)))} a {cardinal(int(m.group(2)))}", t)

    def hour(m):
        h, mins = int(m.group(1)), int(m.group(2))
        return cardinal(h) + (f" e {cardinal(mins)}" if mins else "")
    t = re.sub(r"(?<![\w:.,])([01]?\d|2[0-3]):([0-5]\d)(?![\w:])", hour, t)

    # a number and a year: DPR 151/2011, DCPREV 14030/2025, ARERA 385/2025/R/eel
    t = re.sub(r"(?<![\w/.,])(\d{1,5})/((?:19|20)\d{2})(?!\d)",
               lambda m: f"{cardinal(int(m.group(1)))} {r['parole']['del']} {cardinal(int(m.group(2)))}", t)

    # times: 2x6 mm², 4 × 10
    t = re.sub(r"(\d)\s*[x×]\s*(?=\d)", r"\1 per ", t)

    # codes of letters and digits (models, revisions, rules): SUN2000-10KTL-M1, R02, N24, IFC4; not «45kWp»
    units = {u["simbolo"]: u for u in r["unita"]}
    joined = [s for s, u in units.items() if not u.get("dopo_numero") and s[0].isalpha()]
    attached = re.compile(rf"(?:{NUM})(?:{_alternation(joined)})\Z")

    def code(m):
        token = m.group(0)
        return token if attached.match(token) else _code(token, r)
    t = re.sub(r"(?<![\w.,])(?=[\w.-]*[A-Za-z])(?=[\w.-]*\d)[A-Za-z0-9]+(?:[-_.][A-Za-z0-9]+)*(?![\w])", code, t)

    # signs: «-10 °C» «meno dieci gradi», «+10%» «più dieci per cento» (a hyphen inside a word is not a sign)
    t = re.sub(r"(^|[\s(\[,;:/])([-+−])(?=\d)", lambda m: m.group(1) + ("più " if m.group(2) == "+" else "meno "), t)
    t = t.replace("−", " meno ")

    # ranges: 10-15 kW «da dieci a quindici chilowatt», 96-99%, 10÷15
    t = re.sub(rf"(?<![\w.,])({NUM})(?:-|\s?[–÷]\s?)({NUM})(?!\w|[.,]\d)",
               lambda m: f"da {m.group(1)} a {m.group(2)}", t)

    # fractions: 1/2 «un mezzo», 3/4 «tre quarti»; another pair of numbers with a slash, 230/400 V, said one after the other
    fractions = r["frazioni"]

    def fraction(m):
        a, b = int(m.group(1)), m.group(2)
        if b in fractions and 0 < a < int(b):
            return ("un " + fractions[b][0]) if a == 1 else f"{cardinal(a)} {fractions[b][1]}"
        return f"{m.group(1)} {m.group(2)}"
    t = re.sub(r"(?<![\w/.,])(\d{1,4})/(\d{1,4})(?![\w/]|,\d)", fraction, t)

    # the euro before the number: «€ 1.200» as «1.200 €»
    t = re.sub(rf"€\s?({NUM})", r"\1 €", t)

    # a number and its unit: 45 kWp, 58.000 kWh, 0,25 €/kWh, -10 °C, 16 A (a unit of one letter wants a space)
    spaced = _alternation(s for s, u in units.items() if u.get("dopo_numero"))
    free = _alternation(s for s, u in units.items() if not u.get("dopo_numero"))
    decimal_en = r"\d+\.\d{1,2}(?!\d)"

    def with_unit(m):
        value, symbol = m.group(1), m.group(2) or m.group(3)
        unit = units[symbol]
        return unit["uno"] if _is_one(value) else f"{number(value)} {unit['molti']}"
    t = re.sub(rf"(?<![\w.,])({decimal_en}|{NUM})(?:\s?({free})|\s({spaced}))(?![\w²³]|/\w|\.\d)", with_unit, t)
    # a unit by itself: «in kWh», «la resa in kWh/kWp»
    alone = _alternation(s for s, u in units.items() if not u.get("dopo_numero") and len(s) > 1 and s[0].isalpha())
    t = re.sub(rf"(?<![\w/])({alone})(?![\w²³/])", lambda m: units[m.group(1)]["molti"], t)

    # numbers of sections and versions: 8.2.2.4 «otto punto due punto due punto quattro», 4.0
    def dotted(m):
        s = m.group(0)
        return number(s) if _THOUSANDS.match(s) else " punto ".join(cardinal(int(p)) for p in s.split("."))
    t = re.sub(r"(?<![\w.,])\d+(?:\.\d+)+(?![\w]|,\d)", dotted, t)

    # the other numbers
    def plain(m):
        value, after = m.group(1), m.group(2)
        if _is_one(value):
            return _one(after) + (" " + after if after else "")
        return number(value) + (" " + after if after else "")
    t = re.sub(rf"(?<![\w.,])({NUM})(?!\w|[.,]\d)(?:\s([^\W\d_]+))?", plain, t)

    # the foreign words of the trade as Italian designers say them, the accent written where the voice would miss it
    # (R512, Daniel 06/11/2026: «inverter» with the accent on the last «e»): «invèrter», «clàud»; «file» a computer's
    # file only after an article of the masculine or before a format («il file», «i file IFC»): «le file» are rows
    t = _sounds(t, r)
    # two acronyms with a slash: «DC/AC» «di ci barra a ci», «MT/BT» (a ratio of units, kWh/kWp, said above with «per»)
    t = re.sub(r"(?<![\w/])([A-Z][A-Za-z]*[A-Z])/([A-Z][A-Za-z]*[A-Z])(?![\w/])",
               lambda m: f"{m.group(1)} {r['parole']['barra']} {m.group(2)}" if m.group(0) not in r["sigle"]
               else m.group(0), t)

    # the trade's acronyms (case as written): PR, MPPT, STC, PVGIS, GSE, VVF, ARERA
    sigle = {k: v for k, v in r["sigle"].items() if "." not in k}
    t = re.sub(rf"(?<![\w])({_alternation(sigle)})(?![\w])", lambda m: sigle[m.group(1)], t)

    # signs and marks: ≤ ± × →, the quotes «», brackets; a slash between words is a pause
    t = t.replace("->", ", ").replace(" – ", ", ").replace(" \u2014 ", ", ")
    for sign, words in sorted(r["simboli"].items(), key=lambda kv: -len(kv[0])):
        t = t.replace(sign, words)
    t = re.sub(r"(?<=\w)/(?=\w)", " ", t)

    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    t = re.sub(r"([,;:])(?:\s*[,;:])+", r"\1", t)
    t = re.sub(r",(?=[.!?])", "", t)
    return t.strip(" ,")
