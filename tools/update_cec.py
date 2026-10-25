#!/usr/bin/env python3
"""Rebuild the catalogue's list of CEC modules from the one NREL publishes with the System Advisor Model.

  python tools/update_cec.py                      download «CEC Modules.csv» from NREL's repository and rebuild
  python tools/update_cec.py --file "CEC Modules.csv"     from a copy already on the disk (no network)
  python tools/update_cec.py --dry-run            say what would change and write nothing

The source is https://raw.githubusercontent.com/NREL/SAM/develop/deploy/libraries/CEC%20Modules.csv (BSD-3-Clause,
the notice is in src/meridiana/catalog/data/LICENSE-NREL-SAM.txt and in ATTRIBUTIONS.md). It has the one-diode
parameters the energy model fits, the long and the short side of the module, and a bifacial flag; every row
carries the version of the list and its date («2026.7.3», «6/23/2026»), which the records keep as `list_version`
and `list_date` so that a report can say which list a number comes from. It has no cell type and no
bifaciality factor: the catalogue works those out from the text (catalog.family_of) and says so.

The file written is src/meridiana/catalog/data/modules_cec.json.gz, one record for each row, in the order of the
list; the old file stays in git. Rows that cannot be read are listed and left out, never mended."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "src" / "meridiana" / "catalog" / "data"
OUTPUT = DATA / "modules_cec.json.gz"
LICENCE = DATA / "LICENSE-NREL-SAM.txt"
URL = "https://raw.githubusercontent.com/NREL/SAM/develop/deploy/libraries/CEC%20Modules.csv"
HEADER_ROWS = 3             # the column names, the units, SAM's names for the variables
REQUIRED = ("STC", "V_mp_ref", "I_mp_ref", "V_oc_ref", "I_sc_ref", "alpha_sc", "beta_oc", "gamma_pmp", "N_s",
            "a_ref", "I_L_ref", "I_o_ref", "R_s", "R_sh_ref", "Adjust")
KEPT_APART = ("list_version", "list_date")     # what changes with the list, not with the module


def _number(row: dict, key: str, required: bool = True):
    text = (row.get(key) or "").strip()
    if not text:
        if required:
            raise ValueError(f"{key} is empty")
        return None
    try:
        value = float(text)
    except ValueError:
        raise ValueError(f"{key} is not a number: {text!r}") from None
    if value != value:
        raise ValueError(f"{key} is not a number")
    return value


def _date(text: str) -> str:
    """«6/23/2026» (month/day/year, as the list writes it) as 2026-06-23."""
    try:
        return datetime.strptime(text.strip(), "%m/%d/%Y").date().isoformat()
    except ValueError:
        raise ValueError(f"Date is not month/day/year: {text!r}") from None


def convert(row: dict) -> dict:
    """One row of the list as a catalogue record. ValueError says what is wrong with the row."""
    raw_name = row.get("Name") or ""
    name, maker = raw_name.strip(), (row.get("Manufacturer") or "").strip()
    if not name:
        raise ValueError("no Name")
    for key in REQUIRED:
        _number(row, key)
    pmax, vmp, imp = _number(row, "STC"), _number(row, "V_mp_ref"), _number(row, "I_mp_ref")
    voc, isc = _number(row, "V_oc_ref"), _number(row, "I_sc_ref")
    if not all(v > 0 for v in (pmax, vmp, imp, voc, isc, _number(row, "N_s"))):
        raise ValueError("power, voltages, currents and cells in series must be above zero")
    length, width = _number(row, "Length", False), _number(row, "Width", False)
    version = (row.get("Version") or "").strip()
    if not version:
        raise ValueError("no Version")
    return {
        "id": f"cec:{raw_name}",        # the name as the list writes it, with its stray spaces: the ids stay what they were
        "source": "cec", "manufacturer": maker,
        "model": name[len(maker):].strip() if maker and name.startswith(maker) else name,
        "technology": (row.get("Technology") or "").strip(), "bifacial": (row.get("Bifacial") or "").strip() == "1",
        "pmax": pmax, "vmp": vmp, "imp": imp, "voc": voc, "isc": isc,
        "gamma_pmax": _number(row, "gamma_pmp"),
        # the list gives the coefficients of voltage and current in V/K and A/K; the catalogue keeps %/K
        "beta_voc": round(_number(row, "beta_oc") / voc * 100.0, 4),
        "alpha_isc": round(_number(row, "alpha_sc") / isc * 100.0, 4),
        "cells_in_series": int(_number(row, "N_s")),
        "length": length if length and length > 0 else None, "width": width if width and width > 0 else None,
        "noct": _number(row, "T_NOCT", False), "bipv": (row.get("BIPV") or "").strip().upper() == "Y",
        "sdm": {"I_L_ref": round(_number(row, "I_L_ref"), 6), "I_o_ref": _number(row, "I_o_ref"),
                "R_s": round(_number(row, "R_s"), 6), "R_sh_ref": round(_number(row, "R_sh_ref"), 3),
                "a_ref": round(_number(row, "a_ref"), 6), "Adjust": round(_number(row, "Adjust"), 4)},
        "list_version": version, "list_date": _date(row.get("Date") or ""),
    }


def parse(text: str) -> tuple[list[dict], list[tuple[str, str]]]:
    """The records of a «CEC Modules.csv», and the rows left out as (name, why). A name that comes twice is kept
    once, with the figures of its last row, which is what the file in use did (a module already chosen keeps
    the figures it had); the report says whether the two rows differed."""
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if len(rows) <= HEADER_ROWS or rows[0][:3] != ["Name", "Manufacturer", "Technology"]:
        raise ValueError("this is not NREL's «CEC Modules.csv»: the first columns should be Name, Manufacturer, "
                         "Technology")
    header = rows[0]
    records, left_out, where = [], [], {}
    for values in rows[HEADER_ROWS:]:
        if not any(v.strip() for v in values):
            continue
        row = dict(zip(header, values, strict=False))
        try:
            record = convert(row)
        except ValueError as error:
            left_out.append(((row.get("Name") or "").strip() or "(no name)", str(error)))
            continue
        if record["id"] in where:
            earlier = records[where[record["id"]]]
            left_out.append((row["Name"].strip(), "the name comes twice, " + (
                "with the same figures" if earlier == record else "with different figures") + ": the last row is kept"))
            records[where[record["id"]]] = record
            continue
        where[record["id"]] = len(records)
        records.append(record)
    return records, left_out


def compare(old: list[dict], new: list[dict]) -> dict:
    """What a rebuild changes: names added, names gone, names whose figures differ."""
    before, after = {r["id"]: r for r in old}, {r["id"]: r for r in new}

    def figures(r):
        return {k: v for k, v in r.items() if k not in KEPT_APART}
    return {"added": sorted(after.keys() - before.keys()), "removed": sorted(before.keys() - after.keys()),
            "changed": sorted(i for i in before.keys() & after.keys() if figures(before[i]) != figures(after[i]))}


def write(records: list[dict], path: Path) -> None:
    """The records as compact JSON in a gzip file that does not change when the records do not (no date in
    the header), put in place whole or not at all."""
    payload = json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    temp = path.with_name(path.name + ".part")
    with open(temp, "wb") as fh, gzip.GzipFile(filename="", mode="wb", fileobj=fh, compresslevel=9, mtime=0) as gz:
        gz.write(payload)
    temp.replace(path)


def read_existing(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def download(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Meridiana update_cec (github.com/daniel-g-carrasco)"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read().decode("utf-8-sig")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--file", type=Path, help="a copy of «CEC Modules.csv» on the disk, instead of the download")
    parser.add_argument("--url", default=URL)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--dry-run", action="store_true", help="say what would change, write nothing")
    args = parser.parse_args(argv)
    if not LICENCE.exists():
        print(f"{LICENCE} is missing: the notice of NREL's licence must go with the list", file=sys.stderr)
        return 1
    text = args.file.read_text(encoding="utf-8-sig") if args.file else download(args.url)
    try:
        records, left_out = parse(text)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    old = read_existing(args.output)
    changes = compare(old, records)
    versions = sorted({(r["list_version"], r["list_date"]) for r in records})
    print(f"{len(records)} modules, list {', '.join(f'{v} of {d}' for v, d in versions)}"
          f" (the file in use has {len(old)})")
    print(f"added {len(changes['added'])}, gone {len(changes['removed'])}, figures changed {len(changes['changed'])}")
    print(f"with a size {sum(1 for r in records if r['length'] and r['width'])}, bifacial {sum(r['bifacial'] for r in records)}")
    for name, why in left_out:
        print(f"left out: {name}: {why}")
    if not records:
        print("no module read: nothing written", file=sys.stderr)
        return 1
    if args.dry_run:
        print("dry run: nothing written")
        return 0
    write(records, args.output)
    print(f"written {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
