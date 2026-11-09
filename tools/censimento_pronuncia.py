"""Censimento delle parole che Meridio può dire e che non sono italiane, o sono sigle (R512, 06/11/2026).

Legge i testi che Meridio dice o legge ad alta voce: le traduzioni del programma (po/it.po: Meridio, verifiche,
impostazioni, relazione), il manuale (docs/manuale) e i nomi delle marche del catalogo (catalog/data/*_curated.json,
preferred_makers.json). Ne estrae le parole straniere e le sigle e per ognuna scrive la lettura che Meridio ne dà
(assistant/reading.py con le regole di reading_it.json) e i fonemi che Kokoro riceve (espeak-ng, italiano), prima e
dopo le regole: il segno ˈ precede la sillaba con l'accento.

    python tools/censimento_pronuncia.py            aggiorna docs/meridio/censimento-pronuncia.json
    python tools/censimento_pronuncia.py --elenco   stampa le parole ancora da decidere

Le decisioni prese a mano («va bene», «italiana», «lasciata», con la nota) restano da una corsa all'altra; le altre si ricavano
dalle regole: «riscritta» (tabella della pronuncia), «sigla» (tabella delle sigle), «compitata» (lettera per lettera,
la regola delle sigle fino a quattro lettere), «unità»."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from meridiana.assistant import reading  # noqa: E402

OUT = ROOT / "docs" / "meridio" / "censimento-pronuncia.json"
CATALOG = ROOT / "src" / "meridiana" / "catalog" / "data"
WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?![A-Za-zÀ-ÖØ-öø-ÿ'’])")
ENGLISH = re.compile(r"[kwyjx]|sh|th|ck|oo|ee|ea|ay|ey|oy|ow|aw|ph|wh|ou(?![nrl]?[aeio])")
# le parole italiane che finiscono per consonante (articoli, preposizioni, troncamenti, punti cardinali)
ITALIAN_CONSONANT = set("""il un in con per non del al dal nel sul col tra fra est ovest nord sud quel bel buon nessun
alcun ciascun qual fin pur ben mal or son han far dir aver esser gas bar tram sport film lux volt watt ohm hertz
kelvin ampere joule newton bit byte euro ok""".split())


def po_texts(path: Path):
    """(riga, testo) di ogni msgstr di it.po."""
    text, start, inside = [], 0, False
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("msgstr"):
            inside, start = True, n
            text = [line.split(" ", 1)[1] if " " in line else '""']
        elif inside and line.startswith('"'):
            text.append(line)
        else:
            if inside and text:
                joined = "".join(json.loads(t) if t.startswith('"') else "" for t in text)
                if joined:
                    yield start, joined
            inside, text = False, []


def sources():
    """(fonte, testo) dei testi letti."""
    po = ROOT / "po" / "it.po"
    for n, text in po_texts(po):
        yield f"po/it.po:{n}", text
    for f in sorted((ROOT / "docs" / "manuale").glob("*.md")):
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            yield f"docs/manuale/{f.name}:{n}", line
    for name in ("modules_curated.json", "inverters_curated.json", "optimizers_curated.json",
                 "microinverters_curated.json", "batteries_curated.json"):
        records = json.loads((CATALOG / name).read_text(encoding="utf-8"))
        records = records.get("records", records) if isinstance(records, dict) else records
        for rec in records:
            if isinstance(rec, dict) and rec.get("manufacturer"):
                yield f"catalog/data/{name} (manufacturer)", str(rec["manufacturer"])
    makers = json.loads((CATALOG / "preferred_makers.json").read_text(encoding="utf-8"))
    for kind, names in makers["kinds"].items():
        for maker in names:
            yield f"catalog/data/preferred_makers.json ({kind})", maker


# the words Daniel named (R512, 06/11/2026) and the trade's words Meridio says in his answers, also when the program's
# texts do not hold them (they come from the model): read as whole terms
SPOKEN = ("inverter", "string", "stringa", "MPPT", "datasheet", "cloud", "layout", "report", "software", "hardware",
          "backup", "offset", "Wp", "bypass", "buffer", "tracker", "carport", "smart", "power optimizer",
          "combiner box", "string box", "cluster", "file", "download", "upload", "DC/AC", "AC/DC", "MT/BT", "kWh/kWp",
          "string inverter", "microinverter", "optimizer", "mismatch", "clipping", "shading", "layer", "derating",
          "backtracking", "tilt", "storage", "performance ratio", "monitoring", "default", "export", "zoom", "link",
          "online", "offline", "plugin", "feedback", "setup", "step", "kit", "design", "BESS", "SolarEdge", "Huawei",
          "Fronius", "Sungrow", "GoodWe", "Tigo", "Enphase", "Hoymiles", "APsystems", "Jinko Solar", "LONGi",
          "Trina Solar", "JA Solar", "Canadian Solar", "SMA", "BYD", "Pylontech", "PVsyst", "PVGIS")
SPOKEN_SOURCE = "docs/richieste.md R512 (Daniel, 06/11/2026) e parole del mestiere nelle risposte di Meridio"


def clean(text: str) -> str:
    text = re.sub(r"\{[^}]*\}|%\(\w+\)[sd]|%[sd]|https?://\S+|`[^`]*\.[a-z]{2,4}`", " ", text)
    return re.sub(r"[A-Za-z]:\\\S+|\S+/\S+\.\w+", " ", text)


def kind_of(word: str, units: set, sigle: dict) -> str | None:
    if word in units:
        return "unità"
    if sum(ch.isupper() for ch in word) >= 2:
        return "sigla"
    low = word.lower()
    if len(low) <= 2 or low in ITALIAN_CONSONANT:
        return None
    if ENGLISH.search(low) or (low[-1] not in "aeiouàèéìòù" and low not in ITALIAN_CONSONANT):
        return "straniera"
    return None


def phonemes(words: list[str]) -> list[str]:
    from kokoro_onnx.tokenizer import Tokenizer
    import phonemizer
    Tokenizer()                                     # the espeak-ng of kokoro-onnx, as the voice has it
    return [p.strip() for p in phonemizer.phonemize(words, "it", preserve_punctuation=True, with_stress=True)]


def final_stress(word: str, ph: str) -> bool:
    """Whether espeak puts the accent on the last syllable of a word that has no written accent there."""
    if not ph or word[-1].lower() in "àèéìòù" or " " in ph.strip():
        return False
    last = ph.rfind("ˈ")
    return last >= 0 and not re.search(r"[aeiouɛɔəɪʊ].*[^ːˌ]*[aeiouɛɔəɪʊ]", ph[last + 1:])


def census() -> list[dict]:
    r = reading.rules()
    units = {u["simbolo"] for u in r["unita"]}
    found: dict = defaultdict(list)
    count: Counter = Counter()
    for where, text in sources():
        for word in WORD.findall(clean(text)):
            kind = kind_of(word, units, r["sigle"])
            if kind:
                count[word] += 1
                if len(found[word]) < 3 and where not in found[word]:
                    found[word].append(where)
    for term in SPOKEN:
        count[term] += 0
        if term.lower() in found and term not in found:
            term = term.lower()
        found.setdefault(term, []).append(SPOKEN_SOURCE)
    # the foreign words once, whatever the case ("Inverter", "inverter"); the acronyms as written
    merged: dict = {}
    for word in sorted(found, key=lambda w: (-count[w], w)):
        key = word if kind_of(word, units, r["sigle"]) == "sigla" else word.lower()
        if key in merged:
            merged[key]["occorrenze"] += count[word]
            merged[key]["fonti"] = (merged[key]["fonti"] + [f for f in found[word] if f not in merged[key]["fonti"]])[:3]
        else:
            merged[key] = {"parola": key, "tipo": kind_of(word, units, r["sigle"]) or "del mestiere", "occorrenze": count[word],
                           "fonti": found[word]}
    rows = sorted(merged.values(), key=lambda e: (-e["occorrenze"], e["parola"].lower()))
    said = [reading.normalize(e["parola"]) for e in rows]
    before = phonemes([e["parola"] for e in rows])
    after = phonemes(said)
    for e, s, b, a in zip(rows, said, before, after, strict=True):
        e["lettura"], e["fonemi_prima"], e["fonemi_dopo"] = s, b, a
    return rows


def decide(e: dict, old: dict) -> None:
    r = reading.rules()
    low = e["parola"].lower()
    words = set(re.findall(r"\w+", low))
    rewrites = {k.lower() for k in r.get("pronuncia", {})}
    in_context = {c["parola"].lower() for c in r.get("pronuncia_contesto", [])}
    sigle = {k.lower() for k in r["sigle"]}
    abbreviations = {k.lower().rstrip(".") for k in r["abbreviazioni"]} | {"lgs"}
    if e["tipo"] == "unità":
        e["decisione"] = "unità"
    elif low in rewrites or (" " in low and words & rewrites):
        e["decisione"] = "riscritta"
    elif low in in_context:
        e["decisione"] = "riscritta nel contesto"
    elif low in sigle or (" " in low and words <= sigle | rewrites) or (
            "/" in low and all(p in sigle for p in low.split("/"))):
        e["decisione"] = "sigla"
    elif low in abbreviations:
        e["decisione"] = "abbreviazione"
    elif (e["tipo"] == "sigla" and e["parola"].isupper() and " " not in e["fonemi_prima"]
          and e["fonemi_prima"].count("ˌ") + e["fonemi_prima"].count("ˈ") >= 2):
        e["decisione"] = "compitata"         # espeak says the letters one by one, as the designer does
    elif old.get("decisione") in ("va bene", "italiana", "lasciata"):
        e["decisione"] = old["decisione"]
    else:
        e["decisione"] = "da decidere"
    if old.get("nota"):
        e["nota"] = old["nota"]
    e["accento_finale_prima"] = final_stress(e["parola"], e["fonemi_prima"])


def main(argv: list[str]) -> int:
    old = {}
    if OUT.exists():
        old = {e["parola"]: e for e in json.loads(OUT.read_text(encoding="utf-8"))["parole"]}
    rows = census()
    for e in rows:
        decide(e, old.get(e["parola"], {}))
    if "--elenco" in argv:
        for e in rows:
            if e["decisione"] == "da decidere":
                print(f"{e['occorrenze']:4} {e['tipo'][:3]} {e['parola']:<22} {e['fonemi_prima']:<24} -> {e['lettura']}")
        return 0
    tally = Counter(e["decisione"] for e in rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = {"_nota": __doc__.split("\n\n")[0] + " Generato da tools/censimento_pronuncia.py; le decisioni «va bene», "
                     "«italiana» e «lasciata» sono prese a mano e restano.",
            "fonti": ["po/it.po (msgstr)", "docs/manuale/*.md", "catalog/data/*_curated.json (manufacturer)",
                      "catalog/data/preferred_makers.json"],
            "conteggi": {"parole": len(rows), **dict(sorted(tally.items()))},
            "parole": rows}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(len(rows), dict(tally))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
