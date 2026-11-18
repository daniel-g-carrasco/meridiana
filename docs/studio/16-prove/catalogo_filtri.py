"""Prova per lo studio 16, tema E: che cosa c'è davvero nei dati del catalogo dei moduli e quanto costa
filtrarli.

Che cosa prova:
1. per ogni campo delle schede lette (curated) e della lista CEC, quante schede lo hanno compilato;
2. i valori del campo «tecnologia» nelle due origini, e quanti moduli sono dichiarati bifacciali;
3. una classificazione ricavata dal testo (famiglia della cella: TOPCon, HJT, back contact, PERC, mono, poli,
   film sottile; bifacciale; vetro-vetro) e quanti moduli restano «non detto»;
4. il tempo di un filtro a faccette (tecnologia + bifacciale + potenza + testo) su tutti i record.

Lancio, dalla radice del repository:
    python docs/studio/16-prove/catalogo_filtri.py
"""

from __future__ import annotations

import collections
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from meridiana import catalog  # noqa: E402

# the cell family from the words a datasheet or a listing uses; first match wins, so the specific ones come first
FAMILIES = [
    ("TOPCon", r"topcon"),
    ("HJT", r"\bhjt\b|heterojunction|\bhit\b"),
    ("back contact", r"back.?contact|\babc\b|\bhpbc\b|\bibc\b|\bbc\b"),
    ("PERC", r"\bperc\b"),
    ("film sottile", r"cdte|cigs|a-si|thin film|amorph"),
    ("policristallino", r"multi-c-si|poly|multi"),
    ("monocristallino", r"mono"),
]


def family_of(rec: dict) -> str:
    text = " ".join(str(rec.get(k) or "") for k in ("technology", "model", "series", "notes")).casefold()
    for name, pattern in FAMILIES:
        if re.search(pattern, text):
            return name
    return "non detto"


def fill_table(records, name: str) -> None:
    keys, filled = collections.Counter(), collections.Counter()
    for r in records:
        for k, v in r.items():
            keys[k] += 1
            if v not in (None, "", [], False):
                filled[k] += 1
    print(f"\n== {name}: {len(records)} schede; campo: compilato/presente")
    row = []
    for k, n in sorted(keys.items()):
        row.append(f"{k} {filled[k]}/{n}")
    print("  " + "; ".join(row))


def main() -> int:
    mods = catalog.load("modules")
    curated = [m for m in mods if m.get("source") == "curated"]
    cec = [m for m in mods if m.get("source") == "cec"]
    fill_table(curated, "schede lette per Meridiana")
    fill_table(cec, "lista CEC (come la distribuisce SAM)")

    for name, recs in (("schede lette", curated), ("CEC", cec)):
        tech = collections.Counter(str(r.get("technology") or "") for r in recs)
        bif = collections.Counter(bool(r.get("bifacial")) for r in recs)
        print(f"\n{name}: tecnologia dichiarata: " + "; ".join(f"{k or '(vuoto)'} {n}" for k, n in tech.most_common()))
        print(f"{name}: bifacciale sì {bif[True]}, no o non detto {bif[False]}; "
              f"bifaccialità data in {sum(1 for r in recs if r.get('bifaciality'))} schede")
        fam = collections.Counter(family_of(r) for r in recs)
        print(f"{name}: famiglia della cella ricavata dal testo: " + "; ".join(f"{k} {n}" for k, n in fam.most_common()))
        sizes = sum(1 for r in recs if r.get("length") and r.get("width"))
        eff = sum(1 for r in recs if r.get("efficiency_pct"))
        print(f"{name}: con dimensioni {sizes}, con efficienza dichiarata {eff} "
              f"(ricavabile da potenza e dimensioni per {sizes})")

    # a faceted filter over everything, the way a dialog would run it at every keystroke
    def facets(records, family="", bifacial=None, low=0.0, high=0.0, text=""):
        words = text.casefold().split()
        out = []
        for r in records:
            if family and family_of(r) != family:
                continue
            if bifacial is not None and bool(r.get("bifacial")) != bifacial:
                continue
            p = float(r.get("pmax") or 0)
            if (low and p < low) or (high and p > high):
                continue
            hay = f"{r.get('manufacturer', '')} {r.get('model', '')} {r.get('series', '')}".casefold()
            if all(w in hay for w in words):
                out.append(r)
        return out

    t = time.perf_counter()
    found = facets(mods, "monocristallino", True, 400, 600, "jinko")
    once = time.perf_counter() - t
    t = time.perf_counter()
    fams = collections.Counter(family_of(r) for r in mods)
    classify = time.perf_counter() - t
    known = {id(r): family_of(r) for r in mods}
    cached = [dict(r, family=known[id(r)]) for r in mods]
    t = time.perf_counter()
    found2 = [r for r in facets(cached, "", True, 400, 600, "jinko") if r["family"] == "monocristallino"]
    twice = time.perf_counter() - t
    print(f"\nfiltro a faccette su {len(mods)} record: {len(found)} trovati in {once * 1000:.1f} ms classificando al volo; "
          f"classificare tutti i record una volta costa {classify * 1000:.0f} ms (si fa al caricamento, poi è un campo) "
          f"e il filtro scende a {twice * 1000:.1f} ms ({len(found2)} trovati)")
    print("famiglie su tutto il catalogo: " + "; ".join(f"{k} {n}" for k, n in fams.most_common()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
