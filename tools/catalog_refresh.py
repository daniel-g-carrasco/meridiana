"""Check what the catalogue says about itself, without changing anything: python tools/catalog_refresh.py [options].

- rows whose datasheet was read, or whose state was checked, more than N months ago;
- lifecycle rules that no row uses, or whose address is not answered (with --online, public pages only, no login);
- for each maker, the ladder of AC power of its inverters and the jumps that are too wide (R420);
- rows of the preferred makers with no written state.

Nothing is rewritten: a person reads the sheet and changes the data. Exit code 1 when something is to be looked at.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def months_since(text: str, today: dt.date) -> int | None:
    try:
        when = dt.date.fromisoformat(str(text)[:10])
    except ValueError:
        return None
    return (today.year - when.year) * 12 + today.month - when.month


def old_rows(months: int, today: dt.date) -> list[str]:
    from meridiana import catalog
    out = []
    for kind in catalog.KINDS:
        for rec in catalog.load(kind):
            if rec.get("source") != "curated" or rec.get("class_of"):
                continue
            age = months_since(rec.get("retrieved", ""), today)
            if age is None or age > months:
                out.append(f"{kind}: {rec.get('manufacturer')} {rec.get('model')}: datasheet read {rec.get('retrieved') or 'at no date'}")
            life = rec.get("lifecycle") or {}
            age = months_since(life.get("checked", ""), today)
            if life and (age is None or age > months):
                out.append(f"{kind}: {rec.get('manufacturer')} {rec.get('model')}: state checked {life.get('checked') or 'at no date'}")
    return out


def rule_problems() -> list[str]:
    from meridiana import catalog
    import re
    out = []
    for rule in catalog.lifecycle_rules():
        rows = [r for r in catalog.load(rule["kind"]) if r.get("manufacturer") == rule["manufacturer"] and re.search(rule["match"], str(r.get("model")))]
        if not rows:
            out.append(f"no row for the rule {rule['manufacturer']} {rule['match']} (a product to add?)")
    return out


def source_problems() -> list[str]:
    from meridiana import catalog
    out = []
    addresses = sorted({r["url"] for r in catalog.lifecycle_rules()} | {
        rec["datasheet_url"] for kind in catalog.KINDS for rec in catalog.load(kind)
        if rec.get("source") == "curated" and str(rec.get("datasheet_url", "")).startswith("http")})
    for url in addresses:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=30) as response:
                response.read(1024)
        except urllib.error.HTTPError as error:
            out.append(f"{error.code}: {url}" + (" (the site refuses a program: read it by hand)" if error.code in (403, 429) else ""))
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            out.append(f"{type(error).__name__}: {url}")
    return out


def ladders(ratio: float) -> tuple[dict, list[str]]:
    """The AC powers (kW) of each maker's inverters for Europe, by phases, and the jumps above `ratio` times the size before
    them; below 1 kW and above 125 kW a jump is not looked at."""
    from meridiana import catalog
    powers: dict = {}
    for rec in catalog.load("inverters"):
        if rec.get("source") != "curated" or not set(rec.get("markets") or []) & {"EU", "IT", "global"}:
            continue
        kw = float(rec.get("ac_power_nominal_w") or 0) / 1000.0
        if kw:
            powers.setdefault((rec["manufacturer"], rec.get("phases")), set()).add(round(kw, 2))
    out, jumps = {}, []
    for key, values in sorted(powers.items(), key=lambda item: (item[0][0], str(item[0][1]))):
        ordered = sorted(values)
        out[f"{key[0]} {key[1]}ph"] = ordered
        for low, high in zip(ordered, ordered[1:], strict=False):
            if high / low > ratio and high <= 125:
                jumps.append(f"{key[0]} {key[1]}ph: from {low:g} to {high:g} kW")
    return out, jumps


def without_state(preferred: dict) -> dict:
    from meridiana import catalog
    out = {}
    for kind, makers in preferred.items():
        for maker in makers:
            rows = [r for r in catalog.load(kind) if r.get("manufacturer") == maker and r.get("source") == "curated" and not r.get("class_of")]
            unknown = [r["model"] for r in rows if catalog.lifecycle_state(r) == catalog.UNKNOWN]
            out[f"{kind}/{maker}"] = (len(rows), unknown)
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--months", type=int, default=12, help="how old a reading may be, 12 by default")
    parser.add_argument("--jump", type=float, default=1.6, help="a size this many times the one before it is a hole, 1.6 by default")
    parser.add_argument("--online", action="store_true", help="also ask whether the addresses still answer")
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args(argv)
    from meridiana import catalog
    preferred = json.loads((catalog.DATA / "preferred_makers.json").read_text(encoding="utf-8"))["kinds"]
    today = dt.date.today()
    ladder, jumps = ladders(args.jump)
    states = without_state(preferred)
    report = {"old": old_rows(args.months, today), "rules": rule_problems(), "ladders": ladder, "jumps": jumps,
              "states": {k: {"rows": n, "unknown": len(u), "models": u} for k, (n, u) in states.items()},
              "sources": source_problems() if args.online else []}
    if args.as_json:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=1)
    else:
        for title, key in (("Old readings", "old"), ("Rules without rows", "rules"), ("Holes in the ladders", "jumps"), ("Addresses", "sources")):
            print(f"{title}: {len(report[key])}")
            for line in report[key]:
                print("  " + line)
        print("Rows of the preferred makers without a written state:")
        for key, value in report["states"].items():
            print(f"  {key}: {value['unknown']} of {value['rows']}")
    return 1 if report["old"] or report["jumps"] or report["sources"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
