"""PVsyst's compact hourly records: one line per day, "Day_DDMM=+v1+v2+...+v24", each value a sign followed by
base-62 digits (0-9, A-Z, a-z, the most significant first), divided by the variable's WRFactor to give PVsyst's
internal unit (MJ/m² an hour for irradiation, MJ for energy, °C, m/s, radians, fractions). Decoded and checked
in docs/studio/10-pvsyst-formati-file.md (2.4): the monthly sums equal the values PVsyst writes next to them."""

from __future__ import annotations

import numpy as np

from .pvobject import Node, numbers

DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
VALUE = {c: i for i, c in enumerate(DIGITS)}
MJ_HOUR_TO_W = 1e6 / 3600.0          # MJ/m² in an hour, as a mean power in W/m²


def token(t: str) -> int:
    sign = -1 if t[0] == "-" else 1
    v = 0
    for c in t[1:] if t[0] in "+-" else t:
        v = v * 62 + VALUE[c]
    return sign * v


def day(line: str) -> list[int]:
    """The integers of one Day_ record: "+0+w+RE-1C" gives [0, 32, 1714, -100]."""
    out, cur = [], ""
    for c in line:
        if c in "+-":
            if cur:
                out.append(token(cur))
            cur = c
        else:
            cur += c
    if cur:
        out.append(token(cur))
    return out


def series(var: Node, per_day: int = 24) -> np.ndarray:
    """The values of a variable block (VarSimul_i=... or a TVarSimul record) in its internal unit, day after
    day in the file's order (January 1st first). Days with a wrong count of values are refused."""
    factor = float(var.get("WRFactor") or 1.0)
    days = [(k, v) for k, v in var.attrs if k.startswith("Day_")]
    out = np.empty(len(days) * per_day)
    for i, (k, v) in enumerate(days):
        vals = day(v)
        if len(vals) != per_day:
            raise ValueError(f"{k}: {len(vals)} values instead of {per_day}")
        out[i * per_day:(i + 1) * per_day] = vals
    return out / factor


def monthly(var: Node) -> list[float]:
    """The twelve monthly values PVsyst wrote next to the records (ValMonth), when there."""
    return numbers(var.get("ValMonth"))[:12]


def variables(parent: Node) -> dict[str, Node]:
    """The variable blocks under a node, by their Varident (GlobHor, DiffHor, T_Amb, E_Grid...)."""
    out = {}
    for n in parent.walk():
        if n.kind == "var" or n.type == "TVarSimul":
            name = n.get("Varident") or n.type
            out.setdefault(name, n)
    return out
