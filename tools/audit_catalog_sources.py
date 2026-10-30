"""Compare bundled CEC data with pinned official CSVs, offline and without rewriting data.

Usage: python tools/audit_catalog_sources.py --reference PATH --output NEW.json
The reference folder holds CEC Modules.csv and CEC Inverters.csv from the commit
below. Matching a published dataset is not a verification of manufacturer ratings.
Inverter precision rules describe the existing import, not tolerances on new data.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import gzip
import hashlib
import io
import json
from math import isfinite
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from tools import update_cec
from meridiana.catalog.audit import audit_catalogue

COMMIT = "cba319ded1c32a7f5b3ac76545a29e1f7181d238"
HASHES = {
    "CEC Modules.csv": "a28cf8956a839ed98bb941809b439e4907f5b4c237bd9299bc123fb502c29aff",
    "CEC Inverters.csv": "0c1b2188415dad6928f91f1a4c9a820dadc80962549f903d57d9282ba3753760",
}
DATA = ROOT / "src/meridiana/catalog/data"


def verify_payload(payload, expected):
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch: expected {expected}, received {actual}")
    return actual


def source_number(value, digits=None):
    if not value or value.casefold() == "nan":
        return None
    number = float(value)
    if not isfinite(number):
        raise ValueError(f"Non-finite source number: {value}")
    return number if digits is None else round(number, digits)


def flatten(record, prefix=""):
    for key, value in record.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            yield from flatten(value, path)
        else:
            yield path, value


def compare_records(expected, actual):
    before, after = {r["id"]: r for r in expected}, {r["id"]: r for r in actual}
    differences = []
    for identity in sorted(before.keys() & after.keys()):
        source, bundled = dict(flatten(before[identity])), dict(flatten(after[identity]))
        for field in sorted(source.keys() | bundled.keys()):
            if field not in source or field not in bundled or source[field] != bundled[field]:
                differences.append({"id": identity, "field": field,
                                    "expected": source.get(field), "actual": bundled.get(field)})
    duplicate_ids = sorted(k for k, count in Counter(r["id"] for r in actual).items() if count > 1)
    source_duplicates = sorted(k for k, count in Counter(r["id"] for r in expected).items() if count > 1)
    missing, extra = sorted(before.keys() - after.keys()), sorted(after.keys() - before.keys())
    return {"expected_records": len(expected), "bundled_records": len(actual),
            "missing": missing, "extra": extra, "duplicate_ids": duplicate_ids,
            "source_duplicate_ids": source_duplicates, "differences": differences,
            "matches": not (missing or extra or duplicate_ids or source_duplicates or differences)}


def inverter_records(text):
    rows = list(csv.reader(io.StringIO(text)))
    if rows[0][:3] != ["Name", "Vac", "Pso"]:
        raise ValueError("Not a SAM CEC Inverters.csv")
    records = []
    for values in rows[3:]:
        if not any(values):
            continue
        row = dict(zip(rows[0], values, strict=True))
        name = row["Name"]
        maker, separator, model = name.partition(": ")
        if not separator:
            raise ValueError(f"Missing manufacturer separator: {name}")
        number = lambda key, digits=None, row=row: source_number(row[key], digits)
        records.append({
            "id": "cec:" + name, "source": "cec", "manufacturer": maker, "model": model,
            "ac_power_nominal_w": number("Paco", 1), "ac_voltage_nominal_v": number("Vac", 1),
            "dc_power_nominal_w": number("Pdco", 1), "dc_voltage_max_v": number("Vdcmax", 1),
            "dc_current_max_a": number("Idcmax", 2), "mppt_voltage_min_v": number("Mppt_low", 1),
            "mppt_voltage_max_v": number("Mppt_high", 1), "efficiency_cec_pct": None,
            "listed": "nan" if row["CEC_Date"].casefold() == "nan" else row["CEC_Date"],
            "hybrid": row["CEC_hybrid"] == "Y",
            "sandia": {key: number(key, digits) for key, digits in
                       (("Paco", 1), ("Pdco", 1), ("Vdco", 1), ("Pso", 3),
                        ("C0", None), ("C1", None), ("C2", None), ("C3", None), ("Pnt", 3))},
            "markets": ["US"],
        })
    return records


def audit(reference, data_dir=DATA):
    sources, texts = {}, {}
    for name, digest in HASHES.items():
        payload = (Path(reference) / name).read_bytes()
        sources[name] = {"sha256": verify_payload(payload, digest), "bytes": len(payload),
                         "commit": COMMIT, "url": "https://raw.githubusercontent.com/NatLabRockies/SAM/"
                         + COMMIT + "/deploy/libraries/" + name.replace(" ", "%20")}
        texts[name] = payload.decode("utf-8-sig")
    modules, exclusions = update_cec.parse(texts["CEC Modules.csv"])
    inverters = inverter_records(texts["CEC Inverters.csv"])
    comparisons = {}
    for name, expected in (("modules", modules), ("inverters", inverters)):
        path = Path(data_dir) / f"{name}_cec.json.gz"
        actual = json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))
        comparisons[name] = compare_records(expected, actual)
        comparisons[name]["bundled_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    rows = list(audit_catalogue(data_dir))
    return {
        "scope": "Dataset provenance and existing import precision; not datasheet verification",
        "sources": sources, "comparisons": comparisons, "module_exclusions": exclusions,
        "module_versions": sorted({(r["list_version"], r["list_date"]) for r in modules}),
        "inverter_precision": {"power_and_voltage_decimal_places": 1, "current_decimal_places": 2,
                               "Pso_Pnt_decimal_places": 3, "C0_C1_C2_C3": "exact",
                               "NaN_numeric": None, "markets": "US classification, not present in CSV",
                               "efficiency_cec_pct": "unknown; absent from CSV"},
        "structure": {"records": len(rows), "kinds": dict(Counter(r["kind"] for r in rows)),
                      "states": dict(Counter(r["status"] for r in rows)),
                      "field_states": dict(Counter(s for r in rows for s in r["fields"].values()))},
        "inconsistent_modules": [{k: r[k] for k in ("id", "manufacturer", "model", "imp", "isc")}
                                 for r in modules if r["imp"] > r["isc"]],
        "inverters_missing_sandia_parameters": [{"id": r["id"], "fields": [k for k, v in r["sandia"].items()
                                                                                   if v is None]}
                                               for r in inverters if None in r["sandia"].values()],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.reference)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({k: v["matches"] for k, v in result["comparisons"].items()}))
    return 0 if all(v["matches"] for v in result["comparisons"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
