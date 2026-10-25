"""Quantities typed in a field, with units and arithmetic: «2 m + 30 cm», «1,5», «17°», «150 mm», «2*1,134»,
as FreeCAD's unit fields take them (study 15, 3.2), for the fields of the properties (study 12, I1-I4).

- The decimal separator is the comma or the point, both, in any language. A separator is never dropped in
  silence (FreeCAD's open bug #22558 turns «0.5» into 5): «1.300,5» is refused, not read as 1300,5.
- A number without a unit takes the field's unit: «1,5» in a length field in metres is 1,5 m, and so is
  «2 m + 1,5»; «2*1,134» is 2,268 in the field's unit. Quantities written one after the other are added:
  «2 m 30 cm» is 2,3 m.
- Each kind of field has its units; a unit of another kind is an error that says which units it takes.
- A point before exactly three digits («1.500») is refused: 1500 for an Italian, 1,5 for an English reader.
- + - * / and parentheses. A product of two lengths is an area and is refused in a length field. The minus
  sign U+2212 (copied from a document) is a minus.
- A small parser of its own: never Python's eval. What is not a finite number, and more than MAX_DEPTH
  parentheses or signs one inside the other, are errors said, not a crash.

No Qt here: ui/quantity_field.py is the field that uses it."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from .i18n import _

# kind -> {unit as typed, lower case: factor to the kind's base unit}; the base is m, °, kW, %
UNITS = {
    "length": {"mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0},
    "angle": {"°": 1.0, "deg": 1.0, "rad": 180.0 / math.pi},
    "power": {"w": 0.001, "kw": 1.0, "kwp": 1.0},
    "percent": {"%": 1.0},
    "number": {},
}
# how each unit is written back, for the messages
SHOWN = {"mm": "mm", "cm": "cm", "m": "m", "km": "km", "°": "°", "deg": "deg", "rad": "rad", "w": "W", "kw": "kW",
         "kwp": "kWp", "%": "%"}

MAX_DEPTH = 50
_AMBIGUOUS = re.compile(r"[1-9]\d{0,2}\.\d{3}")
_TOKEN = re.compile(r"\s*(?:(?P<number>\d+(?:[.,]\d*)?|[.,]\d+)|(?P<unit>[A-Za-z]+|°|%)|(?P<op>[-+*/()]))")


class QuantityError(ValueError):
    """What is wrong with what was typed, said so that it can be shown as it is."""


def kind_names() -> dict:
    return {"length": _("a length"), "angle": _("an angle"), "power": _("a power"), "percent": _("a percentage"),
            "number": _("a number")}


@dataclass
class _Q:
    value: float        # in the kind's base unit when dim is 1, a pure number when dim is 0
    dim: int            # 0 a number, 1 a quantity of the field's kind, 2 or -1 something else


def _tokens(text: str, kind: str) -> list[tuple[str, object]]:
    out, i = [], 0
    text = text.replace("\u2212", "-").rstrip()
    while i < len(text):
        m = _TOKEN.match(text, i)
        if m is None or m.end() == i:
            raise QuantityError(_("«{what}» is not understood").format(what=text[i:].strip()))
        if m.group("number") is not None:
            raw = m.group("number")
            if _AMBIGUOUS.fullmatch(raw):
                raise QuantityError(_("«{what}» is ambiguous: write {whole} for the whole number, or {decimal} with "
                                      "the comma").format(what=raw, whole=raw.replace(".", ""),
                                                          decimal=raw.replace(".", ",").rstrip("0").rstrip(",")))
            value = float(raw.replace(",", "."))
            if not math.isfinite(value):
                raise QuantityError(_("The number is too large"))
            out.append(("number", value, raw))
        elif m.group("unit") is not None:
            unit = m.group("unit").lower()
            units = UNITS[kind]
            if unit not in units:
                if units:
                    raise QuantityError(_("«{unit}» is not a unit for {kind}: use {units}").format(
                        unit=m.group("unit"), kind=kind_names()[kind],
                        units=", ".join(SHOWN[u] for u in units if u != "deg")))
                raise QuantityError(_("«{unit}»: this field takes a number without a unit").format(
                    unit=m.group("unit")))
            out.append(("unit", units[unit], m.group("unit")))
        else:
            out.append(("op", m.group("op"), m.group("op")))
        i = m.end()
    # two numbers in a row with no unit between them: a thousands separator or a typo, never guessed
    for a, b in zip(out, out[1:], strict=False):
        if a[0] == b[0] == "number":
            raise QuantityError(_("Two numbers in a row: write one decimal separator, without thousands "
                                  "separators"))
    return out


class _Parser:
    """expr := term (('+'|'-') term)* ; term := factor (('*'|'/') factor)* ;
    factor := ('-'|'+') factor | atom ; atom := quantity+ | '(' expr ')' ; quantity := number unit?"""

    def __init__(self, tokens, kind: str, field_factor: float):
        self.t, self.i, self.kind, self.field = tokens, 0, kind, field_factor
        self.depth = 0

    def peek(self) -> tuple:
        """(kind, value) of the next token; (None, None) at the end."""
        return self.t[self.i][:2] if self.i < len(self.t) else (None, None)

    def take(self) -> tuple:
        tok = self.peek()
        self.i += 1
        return tok

    def raw(self) -> str:
        return self.t[self.i][2] if self.i < len(self.t) else ""

    def promote(self, q: _Q) -> _Q:
        """A pure number beside a quantity takes the field's unit."""
        return _Q(q.value * self.field, 1) if q.dim == 0 else q

    def expr(self) -> _Q:
        q = self.term()
        while self.peek() in (("op", "+"), ("op", "-")):
            op = self.take()[1]
            r = self.term()
            if q.dim != r.dim:
                q, r = self.promote(q), self.promote(r)
                if q.dim != r.dim:
                    raise QuantityError(_("Quantities of different kinds cannot be added"))
            q = _Q(q.value + r.value if op == "+" else q.value - r.value, q.dim)
        return q

    def term(self) -> _Q:
        q = self.factor()
        while self.peek() in (("op", "*"), ("op", "/")):
            op = self.take()[1]
            r = self.factor()
            if op == "*":
                q = _Q(q.value * r.value, q.dim + r.dim)
            else:
                if r.value == 0:
                    raise QuantityError(_("Division by zero"))
                q = _Q(q.value / r.value, q.dim - r.dim)
        return q

    def deeper(self, why: str) -> None:
        """One more level of parentheses or signs: past MAX_DEPTH, an error instead of Python's recursion limit."""
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise QuantityError(why)

    def factor(self) -> _Q:
        if self.peek() in (("op", "-"), ("op", "+")):
            sign = -1.0 if self.take()[1] == "-" else 1.0
            self.deeper(_("Too many signs in a row"))
            q = self.factor()
            self.depth -= 1
            return _Q(sign * q.value, q.dim)
        return self.atom()

    def atom(self) -> _Q:
        kind, value = self.peek()
        if kind == "op" and value == "(":
            self.take()
            self.deeper(_("Too many parentheses one inside the other"))
            q = self.expr()
            if self.take() != ("op", ")"):
                raise QuantityError(_("A parenthesis is not closed"))
            self.depth -= 1
            return q
        if kind != "number":
            if kind is None:
                raise QuantityError(_("Something is missing at the end"))
            raise QuantityError(_("«{what}» is out of place").format(what=self.raw()))
        total: _Q | None = None
        while self.peek()[0] == "number":                       # «2 m 30 cm»: quantities one after the other
            number = self.take()[1]
            if self.peek()[0] == "unit":
                q = _Q(number * self.take()[1], 1)
            else:
                q = _Q(number, 0)
            if total is None:
                total = q
            elif total.dim == 1 and q.dim == 1:
                total = _Q(total.value + q.value, 1)
            else:
                raise QuantityError(_("Two numbers in a row: write one decimal separator, without thousands "
                                      "separators"))
        return total


def parse(text: str, kind: str = "length", unit: str = "") -> float:
    """The value of `text` in the field's `unit` (the kind's base unit when not given: m, °, kW, %).
    QuantityError says what is wrong."""
    if kind not in UNITS:
        raise ValueError(f"unknown kind {kind!r}")
    units = UNITS[kind]
    factor = units[unit.lower()] if unit else 1.0
    tokens = _tokens(text, kind)
    if not tokens:
        raise QuantityError(_("Nothing written"))
    parser = _Parser(tokens, kind, factor)
    q = parser.expr()
    if parser.i < len(tokens):
        raise QuantityError(_("«{what}» is out of place").format(what=tokens[parser.i][2]))
    if not math.isfinite(q.value):
        raise QuantityError(_("The number is too large"))
    if q.dim == 0:
        return q.value
    if q.dim != 1:
        raise QuantityError(_("The result is not {kind}").format(kind=kind_names()[kind]))
    return q.value / factor
