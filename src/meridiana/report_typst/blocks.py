"""The pieces of the report as data: what template.typ draws. A block is a dictionary with its kind in "k"; a piece of text
is a string, a run ({"b": bold}, {"bb": bolder}, {"m": muted}, {"mark": level}, {"formula": image}) or a list of them.
All JSON: no markup is ever written here, and the texts of the user go through as they are."""

from __future__ import annotations

import re
from collections.abc import Iterable


def bold(text: str) -> dict:
    return {"b": str(text)}


def muted(text: str) -> dict:
    return {"m": str(text)}


def mark(level: str) -> dict:
    """A result's mark, drawn by the template: "ok", "warn", "fail" or "info"."""
    return {"mark": level}


def formula(image: str) -> dict:
    return {"formula": image}


def plain(c) -> str:
    """A piece of text as plain words: what a test reads, and what a row of the register says."""
    if c is None:
        return ""
    if isinstance(c, (list, tuple)):
        return "".join(plain(x) for x in c)
    if isinstance(c, dict):
        return str(c.get("b") or c.get("bb") or c.get("m") or "")
    return str(c)


def section(title: str, colour: str = "acc") -> dict:
    """A heading with its coloured square: "acc" the plant, "sun" the energy, "leaf" the money, "slate" the rest."""
    return {"k": "section", "t": title, "c": colour}


def sub(title, level: int = 3) -> dict:
    return {"k": "sub", "t": title, "level": level}


def para(text, style: str = "") -> dict:
    """A paragraph; style "muted", "caption", "source" or "lead" for the small and the large ones."""
    return {"k": "p", "t": text, "style": style}


def two(left: list, right: list, ratio: tuple[float, float] = (1, 1)) -> dict:
    """Two columns side by side, kept on one page."""
    return {"k": "two", "left": [x for x in left if x], "right": [x for x in right if x], "ratio": list(ratio)}


def keep(*items) -> dict:
    return {"k": "keep", "items": [x for x in items if x]}


def floating(*items) -> dict:
    """Blocks that go to the top or the bottom of a page, whole: the text that follows fills the page they would have
    left half empty."""
    return {"k": "float", "items": [x for x in items if x]}


def figure(image: str, caption, *, max_h: float = 118.0, tint: bool = False, inset: float = 0.0,
           chips: list | None = None) -> dict:
    """An image at the whole width in its rounded frame, up to `max_h` mm tall; `tint`: on the filled card."""
    return {"k": "figure", "image": image, "caption": caption, "max_h": max_h, "tint": tint, "inset": inset,
            "chips": chips}


def _longest_word(text: str) -> int:
    return max((len(w) for w in re.split(r"[\s,/-]+", text)), default=0)


def auto_widths(head, rows, right: Iterable[int] = ()) -> list[float]:
    """Relative widths of a table's columns from what they hold: wide enough for the longest word of each and, within
    reason, for the longest line."""
    right = set(right)
    columns = len(head) if head else max((len(r) for r in rows if not isinstance(r, (str, dict))), default=1)
    widths = [3.0] * columns
    for row in ([head] if head else []) + [r for r in rows if not isinstance(r, (str, dict))]:
        for i, c in enumerate(row):
            text = plain(c)
            if isinstance(c, dict) and "mark" in c:
                continue
            need = min(len(text), 14 if i in right else 42)
            widths[i] = max(widths[i], float(need), float(_longest_word(text)) + 1.5)
    return [round(w + 2.0, 1) for w in widths]


def table(rows, head=None, right=(), widths=None, mark_row: int | None = None, codes: list | None = None,
          source_head: str = "") -> dict:
    """A table: `head` its header row (repeated on each page), `right` the indexes of the columns of numbers, a row that
    is a string a group row naming the rows that follow, `mark_row` the index of the row drawn as the result, `widths`
    relative or as "14%", `codes` the code of each row in the register in a last column."""
    head = list(head) if head else None
    numeric = list(right)
    body = [{"group": r} if isinstance(r, str) else [c for c in r] for r in rows]
    w = ([float(str(x).rstrip("%")) for x in widths] if widths else
         auto_widths(head, [r for r in body], numeric))
    source = codes is not None
    if source:
        k = 0
        for r in body:
            if isinstance(r, dict):
                continue
            r.append(codes[k])
            k += 1
        if head:
            head.append(source_head)
        scale = sum(w) / 100.0
        w.append(round(11.0 * scale, 1))
    return {"k": "table", "head": head, "rows": body, "right": numeric, "widths": w,
            "result": -1 if mark_row is None else mark_row, "source": source}


def facts(rows, strong: bool = False, ratio: tuple[float, float] = (5, 6)) -> dict:
    """Label and value on a card; a third element in a row is its code in the register."""
    return {"k": "facts", "rows": [list(r) for r in rows], "strong": strong, "ratio": list(ratio)}
