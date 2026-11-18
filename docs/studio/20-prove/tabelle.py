"""Study 20: the tables of the study from risultati.json (time and peak memory of each way on each sample, what Meridiana
gets), with the decimal comma.

    python tabelle.py risultati.json campioni.json CACHE

GPL-3.0-or-later, as Meridiana."""

from __future__ import annotations

import json
import sys
from pathlib import Path

WAYS = ("open-normal", "open-lazy", "a", "b8", "b1", "c", "d")


def comma(x, digits=1) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


def mb(size: int) -> str:
    return comma(size / 2 ** 20, 1)


def main() -> int:
    rows = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["righe"]
    samples = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))["campioni"]
    cache = Path(sys.argv[3])
    by = {(r["sample"], r["way"]): r for r in rows}
    print("| Campione | MB | apertura piena | apertura pigra | a | b8 | b1 | c | d |")
    print("|---|---|---|---|---|---|---|---|---|")
    for s in samples:
        name = s["name"]
        if not any((name, w) in by for w in WAYS):
            continue
        cells = []
        for w in WAYS:
            r = by.get((name, w))
            if r is None:
                cells.append("-")
            elif r.get("status") != "ok" and not r.get("seconds_median"):
                cells.append(r.get("status", "?").replace("stopped after", "fermato a").replace("stopped at",
                                                                                                 "fermato a")
                             .replace("crash (exit", "caduto (uscita").replace("error", "errore"))
            else:
                cells.append(f"{comma(r['seconds_median'], 2)} s, {comma(r.get('peak_mb_max', 0), 0)} MB")
        size = (cache / s["file"]).stat().st_size if (cache / s["file"]).exists() else 0
        print(f"| {name} | {mb(size)} | " + " | ".join(cells) + " |")
    print()
    print("| Campione | a | b | c | d |")
    print("|---|---|---|---|---|")
    for s in samples:
        name = s["name"]
        cells = []
        for w in ("a", "b8", "c", "d"):
            r = by.get((name, w))
            if r is None or r.get("buildings") is None:
                cells.append("-")
                continue
            cells.append(f"{r['buildings']} ed., {r['pitches']} falde ({r['sloped']} incl.), {r['obstacles']} ost.")
        if any(c != "-" for c in cells):
            print(f"| {name} | " + " | ".join(cells) + " |")
    print()
    for s in samples:
        r = by.get((s["name"], "c"))
        if r and r.get("buildings") is not None:
            print(s["name"], "| app:", r.get("application"), "| schema", r.get("schema"), "| unit", r.get("unit_m"),
                  "| map", r.get("map"), "| site", r.get("site"), "| north", r.get("north"), "| tilts", r.get("tilts"),
                  "| heights", r.get("heights"), "| sources", r.get("sources"), "| kinds", r.get("kinds"),
                  "| counts", {k: v for k, v in (r.get("counts") or {}).items() if v})
    return 0


if __name__ == "__main__":
    sys.exit(main())
