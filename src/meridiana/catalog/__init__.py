"""The product catalogue: PV modules, inverters, microinverters, optimizers and batteries, ready to choose.

Two layers, kept apart because they are worth different trust:
- "curated": models read from the manufacturers' datasheets (the brands most used in Italy, Europe and the
  world), each with the datasheet's address and the date it was read;
- "cec": the California Energy Commission's lists as NREL publishes them with SAM (BSD-3, notice in
  src/meridiana/catalog/data/LICENSE-NREL-SAM.txt, and in ATTRIBUTIONS.md): twenty-one thousand modules with
  their single-diode parameters (rebuilt from NREL's list by tools/update_cec.py, each record saying which
  version of the list it comes from: `list_version`, `list_date`), two thousand inverters with their measured
  efficiency (Sandia model). US-market models: the inverters are for 60 Hz and American voltages, useful for
  their curves more than for an Italian design.

What a module record says beyond its datasheet is marked as such: `cell_family` is the datasheet's (curated)
or read from its words (CEC), `efficiency_derived` says the efficiency was worked out from power and size.

A record chosen for a project is copied into the project file: the project stays as it was designed even
when the catalogue changes.

Two things the catalogue says about a product beyond its datasheet (05/11/2026, R415 and R416):
- `lifecycle`: {"state": current, phasing_out, discontinued or unknown, "checked": date, "url", "text": the words read,
  "replacement": a model, "note"}. A record without it is unknown, as every CEC row is: only a written source makes it
  anything else (docs/studio/34-catalogo-marche-fonti.md). Out of production is not the same as not sold in Italy, and
  the warehouse is not something a catalogue knows.
- `classes`: a module's power classes as the datasheet's table prints them, each with its own Vmp, Imp, Voc and Isc. One
  row per class is made at loading, sharing `family_id`; a class is never scaled from its neighbours, and a class in
  `power_classes_w` without its values is not a row: `unread_classes` names it and its reason.
"""

from __future__ import annotations

import gzip
import json
import re
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
KINDS = ("modules", "inverters", "microinverters", "optimizers", "batteries")
CURRENT, PHASING_OUT, DISCONTINUED, UNKNOWN = "current", "phasing_out", "discontinued", "unknown"
LIFECYCLE_STATES = (CURRENT, PHASING_OUT, DISCONTINUED, UNKNOWN)


def _read(name: str) -> list:
    path = DATA / name
    if not path.exists():
        return []
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, list) else []


def _num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


# The family of the cell, from the words a datasheet or a listing uses (study 16, theme E; the rule and its
# counts are proved in docs/studio/16-prove/catalogo_filtri.py). The first family whose words appear in the
# technology, model, series or notes wins, so the specific cells (TOPCon, HJT, back contact, PERC) come before
# the material (thin film, polycrystalline, monocrystalline): a record that says «Mono-c-Si» and, in its notes,
# «TOPCon» is a TOPCon one. «mono» and «poly» alone mean the material is known and the cell is not stated.
# A clause that says a thing is not stated («the cell architecture is not named (TOPCon is not printed)») names
# no family: seven datasheets read for Meridiana say so, and the study's first count took them for TOPCon.
# The words of the material are whole words: «mono-facial», «mono-glass», «monoassiali», «multilayer» and
# «polymer» say nothing of the silicon (the study's bare «mono», «multi» and «poly» made monocrystalline and
# polycrystalline modules of them).
FAMILIES = (
    ("topcon", r"topcon"),
    ("hjt", r"\bhjt\b|heterojunction|\bhit\b"),
    ("back_contact", r"back.?contact|\babc\b|\bhpbc\b|\bibc\b|\bbc\b"),
    ("perc", r"\bperc\b"),
    ("thin_film", r"cdte|cigs|\ba-si\b|thin.?film|amorph"),
    ("poly", r"multi-?c-?si|multi-?crystalline|poly-?c-?si|poly-?crystalline|poly-?si(?:licon)?\b|\bpoly\b"),
    ("mono", r"\bmono(?:-?c-?si|-?si|crystalline)?\b(?![ -]?(?:facial|glass))"),
)
UNKNOWN_FAMILY = "unknown"
# The bifaciality (%) of a bifacial module whose datasheet gives none, by family: an estimate, never a datasheet
# value, and kept apart from `bifaciality` so that nothing takes one for the other (Daniel, 23/10/2026: estimated
# values enter the catalogue, marked as estimated). Sources of the figures: PV*SOL's «usually 70-80 %» for the
# factor of a bifacial module, pvlib's default of 0.8 for the factor of `infinite_sheds.get_irradiance` (study 16,
# E.3 and E.5). The other families (back contact, thin film, polycrystalline, monocrystalline and the unstated)
# have no figure: the study gave none, and a bifacial module of those is shown without one.
BIFACIALITY_ESTIMATE = {"perc": 70.0, "topcon": 80.0, "hjt": 80.0}
# one pass over the text for the cells and one for the material, instead of seven searches, and the technology
# (a handful of distinct words in 17,000 records) read once: the whole catalogue is classified in about 50 ms
_CELLS = re.compile("|".join(f"(?P<{key}>{pattern})" for key, pattern in FAMILIES[:4]))
_MATERIALS = re.compile("|".join(f"(?P<{key}>{pattern})" for key, pattern in FAMILIES[4:]))
_ANY = re.compile("|".join(pattern for _key, pattern in FAMILIES))
_NOT_SAID = re.compile(r"\bnot\s+(?:printed|stated|named|given|declared|specified|mentioned)\b")
_CLAUSES = re.compile(r"[.;]")


def _said(text: str) -> str:
    """The text without the clauses that say something is not stated."""
    if "not " not in text:
        return text
    return ". ".join(c for c in _CLAUSES.split(text) if not _NOT_SAID.search(c))


def _named_in(text: str) -> frozenset:
    """The families whose words appear in a casefolded text."""
    return frozenset(m.lastgroup for regex in (_CELLS, _MATERIALS) for m in regex.finditer(text))


@lru_cache(maxsize=512)
def _named_in_technology(technology: str) -> frozenset:
    return _named_in(technology.casefold())


def _first_of(named) -> str:
    return next((key for key, _pattern in FAMILIES if key in named), UNKNOWN_FAMILY)


def family_of(rec: dict) -> str:
    """The family of a module's cell (a key of FAMILIES, or UNKNOWN_FAMILY when the words do not say), read from
    its technology, model, series and notes: the rule alone, whatever `cell_family` the record may already
    carry. The technology is the datasheet's label and counts as it is; in the free text (model, series, notes) a
    clause that says a thing is not stated names nothing."""
    technology = _named_in_technology(rec.get("technology") or "")
    model, series, notes = rec.get("model") or "", rec.get("series"), rec.get("notes")
    rest = _said((f"{model} {series or ''} {notes or ''}" if series or notes else model).casefold())
    return _first_of(technology | _named_in(rest) if _ANY.search(rest) else technology)


def enrich_module(r: dict) -> dict:
    """What a module record needs to be filtered, added in place once, at loading: `cell_family` (the one a
    record carries, written from its datasheet, or the rule's), `bifacial` always true or false, the
    efficiency worked out from power and size when the record has none (`efficiency_derived` says so), and the
    typical bifaciality of its family for a bifacial module whose datasheet gives none (`bifaciality_estimated`,
    in %; `bifaciality` stays what the datasheet says, empty if it says nothing)."""
    if not r.get("cell_family"):
        r["cell_family"] = family_of(r)
    r["bifacial"] = bool(r.get("bifacial"))
    pmax, length, width = r.get("pmax"), r.get("length"), r.get("width")
    if not r.get("efficiency_pct") and pmax and length and width:
        r["efficiency_pct"] = round(100.0 * pmax / (1000.0 * length * width), 2)
        r["efficiency_derived"] = True
    if r["bifacial"] and not r.get("bifaciality"):
        typical = BIFACIALITY_ESTIMATE.get(r["cell_family"])
        if typical:
            r["bifaciality_estimated"] = typical
    return r


def normalise_module(r: dict) -> dict | None:
    """A curated datasheet record (the fields of the collection: pmax_w, vmp_v...) in the catalogue's terms."""
    pmax = _num(r.get("pmax_w", r.get("pmax")))
    vmp, imp = _num(r.get("vmp_v", r.get("vmp"))), _num(r.get("imp_a", r.get("imp")))
    voc, isc = _num(r.get("voc_v", r.get("voc"))), _num(r.get("isc_a", r.get("isc")))
    if not all((pmax, vmp, imp, voc, isc)):
        return None
    length = _num(r.get("length_mm"))
    width = _num(r.get("width_mm"))
    out = {
        "id": f"cur:{r.get('manufacturer', '')}:{r.get('model', '')}", "source": "curated",
        "manufacturer": r.get("manufacturer", ""), "model": r.get("model", ""), "series": r.get("series", ""),
        "technology": r.get("technology", ""), "cell_family": r.get("cell_family", ""),
        "bifacial": bool(r.get("bifacial")), "bifaciality": _num(r.get("bifaciality_pct")), "pmax": pmax,
        "vmp": vmp, "imp": imp, "voc": voc, "isc": isc,
        "gamma_pmax": _num(r.get("temp_coeff_pmax_pct_c", r.get("gamma_pmax"))),
        "beta_voc": _num(r.get("temp_coeff_voc_pct_c", r.get("beta_voc"))),
        "alpha_isc": _num(r.get("temp_coeff_isc_pct_c", r.get("alpha_isc"))),
        "cells": int(_num(r.get("cells")) or 0), "length": length / 1000.0 if length else None,
        "width": width / 1000.0 if width else None, "thickness_mm": _num(r.get("thickness_mm")),
        "weight_kg": _num(r.get("weight_kg")), "efficiency_pct": _num(r.get("efficiency_pct")),
        "noct": _num(r.get("nmot_c", r.get("noct_c"))), "max_system_voltage_v": _num(r.get("max_system_voltage_v")),
        "max_series_fuse_a": _num(r.get("max_series_fuse_a")), "fire_rating": r.get("fire_rating"),
        "first_year_loss": _num(r.get("degradation_first_year_pct")),
        "yearly_loss": _num(r.get("degradation_annual_pct")), "power_classes_w": r.get("power_classes_w") or [],
        "warranty_power_years": _num(r.get("warranty_power_years")),
        "warranty_product_years": _num(r.get("warranty_product_years")), "markets": r.get("markets") or [],
        "datasheet_url": r.get("datasheet_url", ""), "datasheet_revision": r.get("datasheet_revision"),
        "retrieved": r.get("retrieved", ""), "notes": r.get("notes", ""),
    }
    if r.get("lifecycle"):
        out["lifecycle"] = r["lifecycle"]
    if r.get("classes"):
        out["classes"] = [{"pmax": _num(c.get("pmax_w", c.get("pmax"))), "vmp": _num(c.get("vmp_v", c.get("vmp"))),
                           "imp": _num(c.get("imp_a", c.get("imp"))), "voc": _num(c.get("voc_v", c.get("voc"))),
                           "isc": _num(c.get("isc_a", c.get("isc"))),
                           "efficiency_pct": _num(c.get("efficiency_pct"))} for c in r["classes"]]
    return out


def class_model(rec: dict, power: float) -> str:
    """The name of a module of a family at another power class: the power in the model's name replaced when it appears
    there once (JKM475N-48QL6-DV at 480 W is JKM480N-48QL6-DV, the manufacturer's rule), the class added otherwise."""
    model, own = str(rec.get("model") or ""), f"{rec.get('pmax', 0):g}"
    target = f"{power:g}"
    found = re.findall(rf"(?<!\d){re.escape(own)}(?!\d)", model)
    if len(found) == 1:
        return re.sub(rf"(?<!\d){re.escape(own)}(?!\d)", target, model)
    return f"{model} {target} W"


UNREAD_CLASS = "the table of this class could not be read on the datasheet: choose it only after adding its values"


def expand_classes(rec: dict) -> list[dict]:
    """A module record and one more row for each other class of its table, with that class's own values; `family_id` is
    the same for all and the row as it was written keeps its id, so that a project that names it finds the same thing.
    A class of `power_classes_w` that the table does not give is named in `unread_classes`, and it is no row."""
    classes = rec.get("classes") or []
    if not classes:
        return [rec]
    family = rec.get("id") or f"cur:{rec.get('manufacturer', '')}:{rec.get('model', '')}"
    out, read = [], set()
    for entry in classes:
        if not all(entry.get(k) for k in ("pmax", "vmp", "imp", "voc", "isc")):
            continue
        read.add(float(entry["pmax"]))
        if float(entry["pmax"]) == float(rec.get("pmax") or 0):
            continue
        row = dict(rec)
        row.update({k: entry[k] for k in ("pmax", "vmp", "imp", "voc", "isc")})
        row["efficiency_pct"] = entry.get("efficiency_pct")
        row["efficiency_derived"] = False
        row["model"] = class_model(rec, float(entry["pmax"]))
        row["id"] = f"{family.rpartition(':')[0]}:{row['model']}" if ":" in family else f"{family}:{row['model']}"
        row["family_id"], row["class_of"] = family, rec.get("model")
        out.append(row)
    base = dict(rec)
    base["family_id"] = family
    unread = [float(p) for p in rec.get("power_classes_w") or [] if float(p) not in read and float(p) != float(rec.get("pmax") or 0)]
    for row in (base, *out):
        row["unread_classes"] = unread
    return sorted([base, *out], key=lambda r: float(r.get("pmax") or 0))


@lru_cache(maxsize=1)
def lifecycle_rules() -> tuple:
    """What written sources say of the state of the products of a maker (data/lifecycle.json): the first rule whose
    `match` finds the record's model applies. Every rule has its address and the words read there."""
    path = DATA / "lifecycle.json"
    rules = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    for rule in rules:
        rule["_match"] = re.compile(rule["match"])
    return tuple(rules)


def apply_lifecycle(rec: dict, kind: str) -> dict:
    """The record with the `lifecycle` a rule gives it; a state already on the record stands, and nothing else changes."""
    if rec.get("lifecycle") or rec.get("source") != "curated":
        return rec
    for rule in lifecycle_rules():
        if rule["kind"] == kind and rule["manufacturer"] == rec.get("manufacturer") and rule["_match"].search(str(rec.get("model") or "")):
            rec["lifecycle"] = {k: rule[k] for k in ("state", "checked", "url", "text", "replacement", "note") if rule.get(k)}
            break
    return rec


def lifecycle_state(rec: dict) -> str:
    """The state a record's written source gives it; unknown when there is none (every CEC row)."""
    life = rec.get("lifecycle")
    state = life.get("state") if isinstance(life, dict) else None
    return state if state in LIFECYCLE_STATES else UNKNOWN


def family_key(rec: dict, kind: str) -> str:
    """What makes rows one family in the list: a module's class table; the inverters, microinverters and optimizers of
    one datasheet of one maker, with the same phases and type. Nothing for batteries (their sizes are modules in a
    stack, each with its own limits), for the CEC's rows (nothing certain says what goes together) or when the
    datasheet is not known."""
    if rec.get("family_id"):
        return str(rec["family_id"])
    if kind not in ("inverters", "microinverters", "optimizers") or rec.get("source") != "curated":
        return ""
    url = rec.get("datasheet_url")
    if not url:
        return ""
    return f"{rec.get('manufacturer', '')}|{url}|{rec.get('phases', '')}|{rec.get('type', '')}"


def central_class(rows: list[dict], kind: str) -> dict:
    """The default class of a family: the middle one by power, the upper of the two middle ones when they are even."""
    ordered = sorted(rows, key=lambda r: power_of(r, kind))
    return ordered[len(ordered) // 2]


def family_name(rows: list[dict]) -> str:
    """A family's name for its row: the part its models share, with the range of powers of a module family as the
    datasheet writes it (JKM460-485N-48QL6-DV); the series when the models share too little."""
    models = [str(r.get("model") or "") for r in rows]
    powers = sorted(float(r.get("pmax") or 0) for r in rows)
    if powers and powers[-1] and len(rows) > 1:
        own = f"{rows[0].get('pmax', 0):g}"
        found = re.findall(rf"(?<!\d){re.escape(own)}(?!\d)", models[0])
        if len(found) == 1:
            return re.sub(rf"(?<!\d){re.escape(own)}(?!\d)", f"{powers[0]:g}-{powers[-1]:g}", models[0])
    prefix = models[0] if models else ""
    for model in models[1:]:
        while prefix and not model.startswith(prefix):
            prefix = prefix[:-1]
    series = str(rows[0].get("series") or "") if rows else ""
    shortest = min((len(model) for model in models), default=0)
    if len(prefix) >= 4 and len(prefix) >= 0.6 * shortest:
        return prefix.partition(" (")[0].rstrip(" -_/")
    if series:
        return series
    # nothing shared worth saying: their names, never one of them alone, which would look like that model
    return " / ".join(models[:3]) + (" …" if len(models) > 3 else "")


def normalise_other(r: dict, kind: str) -> dict:
    out = dict(r)
    out["id"] = f"cur:{r.get('manufacturer', '')}:{r.get('model', '')}"
    out["source"] = "curated"
    out["kind"] = kind
    return out


@lru_cache(maxsize=None)
def load(kind: str) -> tuple:
    """Every record of a kind, curated first; a tuple, so that the cache cannot be changed by a caller."""
    if kind not in KINDS:
        raise ValueError(kind)
    from .personal import load as personal_load
    personal = personal_load(kind)
    if kind == "modules":
        curated = [apply_lifecycle(m, kind) for m in (normalise_module(r) for r in _read("modules_curated.json")) if m]
        rows = [row for m in personal + curated for row in expand_classes(m)]
        return tuple(enrich_module(m) for m in rows + _read("modules_cec.json.gz"))
    if kind == "inverters":
        curated = [apply_lifecycle(normalise_other(r, kind), kind) for r in _read("inverters_curated.json")]
        return tuple(personal + curated + _read("inverters_cec.json.gz"))
    return tuple(personal + [apply_lifecycle(normalise_other(r, kind), kind) for r in _read(f"{kind}_curated.json")])


def power_of(rec: dict, kind: str) -> float:
    if kind == "modules":
        return float(rec.get("pmax") or 0.0)
    for key in ("ac_power_nominal_w", "ac_power_max_va", "rated_input_power_w", "usable_energy_kwh"):
        if rec.get(key):
            return float(rec[key])
    return 0.0


_ORDERED: dict = {}


def _ordered(kind: str) -> tuple:
    """The records of a kind in the catalogue's order (curated first, then by maker and power) with the words
    each is found by (maker, model, series, any case), worked out once for each loading: a search only filters
    them, in the order they already have."""
    records = load(kind)
    kept = _ORDERED.get(kind)
    if kept is None or kept[0] is not records:
        ordered = tuple(sorted(records, key=lambda r: (r.get("source") != "curated",
                                                       str(r.get("manufacturer", "")).casefold(),
                                                       power_of(r, kind))))
        words = tuple(f"{r.get('manufacturer') or ''} {r.get('model') or ''} {r.get('series') or ''}".casefold()
                      for r in ordered)
        kept = _ORDERED[kind] = (records, ordered, words)
    return kept[1], kept[2]


def ready(kind: str) -> bool:
    """Whether the records of a kind are read and in order: a search is then a matter of milliseconds. The first
    reading unpacks the files (16,959 modules), which the catalogue's window does away from its thread (study 16,
    F3)."""
    return kind in _ORDERED


def prepare(kind: str) -> None:
    """Read and order the records of a kind, as the first search would: callable from a worker."""
    _ordered(kind)


def search(kind: str, text: str = "", source: str = "", low: float = 0.0, high: float = 0.0,
           market: str = "", limit: int | None = 500, *, family: str = "", bifacial: bool | None = None,
           manufacturer: str = "", efficiency_min: float = 0.0, length_max: float = 0.0, sort: str = "",
           descending: bool = False, states: tuple = ()) -> list:
    """The records whose maker, model and series contain every word of `text` (any case), within the power
    range (W; kWh for batteries) and of the source and market asked; curated first, then by maker and power, or
    by the field `sort` (a record without it last either way).

    Modules also by `family` (a key of FAMILIES, or UNKNOWN_FAMILY), `bifacial` (None: either), `manufacturer`
    (the whole name, any case), `efficiency_min` (%) and `length_max` (m): a module without the efficiency or the
    size is left out when that filter is on, because it cannot be said to satisfy it. `states`: only the records in
    these lifecycle states (all, when empty)."""
    records, haystacks = _ordered(kind)
    words = text.casefold().split()
    if words:
        first = words[0]
        records = [r for r, h in zip(records, haystacks, strict=True) if first in h and all(w in h for w in words)]
    if source:
        records = [r for r in records if r.get("source") == source]
    if market:
        records = [r for r in records if market in (r.get("markets") or [])]
    if low or high:
        records = [r for r in records
                   if not ((low and power_of(r, kind) < low) or (high and power_of(r, kind) > high))]
    if family:
        records = [r for r in records if r.get("cell_family") == family]
    if bifacial is not None:
        records = [r for r in records if bool(r.get("bifacial")) is bifacial]
    if manufacturer:
        wanted = manufacturer.casefold()
        records = [r for r in records if str(r.get("manufacturer", "")).casefold() == wanted]
    if efficiency_min:
        records = [r for r in records if (r.get("efficiency_pct") or 0.0) >= efficiency_min]
    if length_max:
        records = [r for r in records if r.get("length") and r["length"] <= length_max]
    if states:
        records = [r for r in records if lifecycle_state(r) in states]
    if sort:
        records = sorted_by(records, sort, descending)
    return list(records) if limit is None else list(records[:limit])


def family_rank(rec: dict):
    """Where a module's family stands in FAMILIES (the order of the filter and of a click on the column): the
    newest cells first; None when the words do not say, which sorts last either way."""
    for n, (key, _pattern) in enumerate(FAMILIES):
        if rec.get("cell_family") == key:
            return n
    return None


def sorted_by(records, key, descending: bool = False) -> list:
    """The records ordered by a field (or by what `key`, a function of the record, gives), as a click on a column
    of the catalogue asks: numbers by value, words without case; a record without the field last either way."""
    def value(r):
        v = key(r) if callable(key) else r.get(key)
        if v is None or v == "":
            return (1, 0, "")
        if isinstance(v, bool):
            return (0, int(v), "")
        if isinstance(v, (int, float)):
            return (0, float(v), "")
        return (0, 0, str(v).casefold())
    keyed = [(value(r), r) for r in records]
    present = sorted((kr for kr in keyed if kr[0][0] == 0), key=lambda kr: kr[0], reverse=descending)
    return [r for _k, r in present] + [r for k, r in keyed if k[0] == 1]


def brands(kind: str, source: str = "") -> list[str]:
    """The makers of a kind (of one source, if asked) in alphabetical order; a maker written in two ways that
    differ only by case ('Axitec', 'AXITEC') is listed once, as the datasheets read for Meridiana write it."""
    names: dict[str, str] = {}
    for r in load(kind):
        if not source or r.get("source") == source:
            name = str(r.get("manufacturer", ""))
            names.setdefault(name.casefold(), name)
    return sorted(names.values(), key=str.casefold)


def for_project(rec: dict) -> dict:
    """A module record as the project keeps it: the catalogue's fields plus what the layout reads."""
    out = dict(rec)
    out["length"] = float(rec.get("length") or 2.278)
    out["width"] = float(rec.get("width") or 1.134)
    out["power_kw"] = float(rec.get("pmax") or 450.0) / 1000.0
    return out


def counts() -> dict:
    return {k: {"curated": sum(1 for r in load(k) if r.get("source") == "curated"),
                "cec": sum(1 for r in load(k) if r.get("source") == "cec")} for k in KINDS}
