"""A step of a calculation as the report and the window show it (R460): one source for both. The step of a record
(energy/pedigree.py) becomes its title with its code, the explanation, the formula's TeX with its number («(9.1)»),
the symbols with their values split on the decimal comma (so the digits line up), their sources, the result; then
the hour of the example and the same formula with the numbers in place of the symbols, ending in the result in
evidence (R479, energy/worked.py), and the reference. No Qt here: the Typst template draws
it (block "step"), the editable exports write it (odt.py, word.py), the Quick window's «How it is computed» lays it
out with the same parts (quick/qml/Meridiana/Charts/Pedigree.qml)."""

from __future__ import annotations

import re

from ..energy.pedigree import kind_names
from .blocks import bold, muted

NUMBER = re.compile(r"^(-?[0-9][0-9.]*)(,[0-9]+)?( .*)?$")


def parts(value: str) -> tuple[str, str]:
    """A value in two parts: the whole number and the rest (decimals and unit); ("", "") when it is no number."""
    m = NUMBER.match(value or "")
    if m is None:
        return "", ""
    return m.group(1), (m.group(2) or "") + (m.group(3) or "")


def source_runs(source, kinds: dict | None = None) -> list:
    """Where a value comes from, as runs: the kind in bold, the label, the reference muted."""
    if source is None:
        return []
    kinds = kind_names() if kinds is None else kinds
    out: list = [bold(kinds.get(source.kind, source.kind))]
    if source.label:
        out.append(f": {source.label}")
    if source.ref:
        out.append(muted(f" ({source.ref})"))
    return out


def source_text(source, kinds: dict | None = None) -> str:
    from .blocks import plain
    return plain(source_runs(source, kinds))


def quantity(q, kinds: dict | None = None) -> dict:
    value = q.text()
    whole, rest = parts(value)
    return {"symbol": q.symbol or "", "label": q.label, "value": value, "int": whole, "rest": rest,
            "source": source_runs(q.source, kinds)}


def step_block(step, eq: str, code: str = "", kinds: dict | None = None) -> dict:
    """The block of a step: what template.typ's `step` draws."""
    kinds = kind_names() if kinds is None else kinds
    inputs = [quantity(q, kinds) for q in step.inputs]
    result = quantity(step.result, kinds) if step.result is not None else None
    if result is not None:
        result["source"] = []
    worked = list(getattr(step, "worked", None) or []) if step.formula else []
    return {"k": "step", "code": code, "title": step.title, "explanation": step.explanation or "",
            "tex": step.formula or "", "eq": eq if step.formula else "", "inputs": inputs, "result": result,
            "worked": worked, "example": (getattr(step, "example", "") or "") if worked else "",
            "reference": step.reference or ""}


def records_from(plain: list) -> list:
    """Records from their plain form (dictionaries, as the Quick window holds them) back into pedigree objects."""
    from ..energy.pedigree import KINDS, Quantity, Record, Source, Step

    def quantity_of(d):
        if not d:
            return None
        src = d.get("source")
        kind = src.get("kind", "") if src else ""
        source = Source(kind if kind in KINDS else "computed", src.get("label") or "", src.get("ref") or "") if src else None
        return Quantity(d.get("symbol") or "", d.get("label") or "", d.get("value", ""), d.get("unit") or "",
                        source, d.get("decimals", 2) if d.get("decimals") is not None else 2)
    out = []
    for r in plain or []:
        steps = [Step(s.get("key", ""), s.get("title") or "", s.get("formula") or "", s.get("explanation") or "",
                      [quantity_of(q) for q in s.get("inputs") or [] if q], quantity_of(s.get("result")),
                      s.get("reference") or "", list(s.get("worked") or []), s.get("example") or "",
                      list(s.get("proof") or [])) for s in r.get("steps") or []]
        out.append(Record(r.get("title") or "", steps))
    return out


def for_window(plain: list, kinds: dict | None = None) -> list[list[dict]]:
    """The steps of the records as the window lays them out (Pedigree.qml): the same blocks as the report's, the
    sources as plain text, the result's source kept (the window shows where it is computed)."""
    from .blocks import plain as words
    kinds = kind_names() if kinds is None else kinds
    records = records_from(plain)
    views = numbered(records)
    for record, mine in zip(records, views, strict=True):
        for step, view in zip(record.steps, mine, strict=True):
            for q, item in zip(step.inputs, view["inputs"], strict=True):
                item["source"] = words(source_runs(q.source, kinds))
            if view["result"] is not None:
                view["result"]["source"] = words(source_runs(step.result.source, kinds))
            view["explanation"] = words(view["explanation"])
    return views


def numbered(records, chapter: int | str = "", codes=None) -> list[list[dict]]:
    """The steps of each record, the formulas numbered on from one record to the next («chapter.k», or «k» alone);
    `codes(key)` the code of a step in the register, or None."""
    kinds = kind_names()
    out, k = [], 0
    for record in records:
        mine = []
        for step in record.steps:
            if step.formula:
                k += 1
            eq = f"{chapter}.{k}" if chapter != "" else str(k)
            code = codes(step.key) if codes is not None else None
            mine.append(step_block(step, eq, code or "", kinds))
        out.append(mine)
    return out
