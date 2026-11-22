"""Repeatable catalogue audit. Source presence is not datasheet verification.

Audit raw rows as well as the searchable catalogue: invalid module rows must not
silently disappear through normalization. Explicit field evidence is retained.
"""
import csv
import gzip
import json
from collections import Counter
from math import isfinite
from pathlib import Path

from . import DATA, KINDS


def unit_of(field):
    for suffix, unit in (("_kwh", "kWh"), ("_w", "W"), ("_va", "VA"), ("_v", "V"),
                         ("_a", "A"), ("_pct", "%"), ("_mm", "mm"), ("_kg", "kg")):
        if field.endswith(suffix):
            return unit
    return {"pmax": "W", "voc": "V", "vmp": "V", "isc": "A", "imp": "A",
            "length": "m", "width": "m"}.get(field, "")


def audit_record(record, kind, origin=""):
    """Classify each field, retain provenance and report numerical contradictions."""
    dataset = record.get("source") == "cec" or "_cec.json" in origin
    source = record.get("datasheet_url") or ("NREL SAM CEC dataset; ATTRIBUTIONS.md; " + origin if dataset else "")
    evidence = record.get("field_sources") or {}
    fields, issues = {}, []
    for key, value in record.items():
        if value is None or value == "" or value == [] or (isinstance(value, str) and value.lower() == "nan"):
            state = "unknown"
        elif key in evidence and all(evidence[key].get(k) for k in ("source", "page", "verified")):
            state = "verified_field"
        elif key.endswith("_estimated") or key.endswith("_derived"):
            state = "derived_or_estimated"
        else:
            state = "provenance_dataset" if dataset else ("source_declared" if source else "source_missing")
        fields[key] = state
        if isinstance(value, (float, int)) and not isinstance(value, bool):
            if not isfinite(value):
                issues.append(f"{key}: non-finite")
            elif unit_of(key) in ("W", "VA", "V", "A", "kWh", "mm", "kg") and value < 0:
                issues.append(f"{key}: negative rating")
            elif unit_of(key) == "%" and (value < 0 or value > 100) and "coeff" not in key:
                issues.append(f"{key}: outside 0..100")
    def less(a, b):
        av, bv = record.get(a), record.get(b)
        if isinstance(av, (int, float)) and isinstance(bv, (int, float)) and av > bv:
            issues.append(f"{a} > {b}")
    for a, b in (("usable_energy_kwh", "nominal_energy_kwh"), ("modules_min", "modules_max"),
                 ("mppt_voltage_min_v", "mppt_voltage_max_v"), ("mppt_voltage_max_v", "dc_voltage_max_v"),
                 ("vmp", "voc"), ("imp", "isc"), ("vmp_v", "voc_v"), ("imp_a", "isc_a")):
        less(a, b)
    if record.get("efficiency_derived"):
        fields["efficiency_pct"] = "derived_or_estimated"
    if kind == "batteries":
        for key in ("usable_energy_kwh", "max_charge_power_w", "max_discharge_power_w", "efficiency_basis", "coupling"):
            fields.setdefault(key, "unknown")
    if kind == "inverters" and record.get("type") == "hybrid":
        for key in ("storage_compatibility", "battery_current_max_a", "battery_voltage_range_v"):
            fields.setdefault(key, "unknown")
    return {"kind": kind, "origin": origin, "manufacturer": record.get("manufacturer", ""),
            "model": record.get("model", ""), "source": source,
            "revision": record.get("datasheet_revision") or record.get("list_version") or "",
            "retrieved": record.get("retrieved") or record.get("list_date") or "",
            "status": "inconsistent" if issues else "structurally_checked",
            "issues": issues, "fields": fields, "field_sources": evidence,
            "units": {k: unit_of(k) for k in fields if unit_of(k)}}


def audit_catalogue(data_dir=DATA):
    for kind in KINDS:
        for path in sorted(Path(data_dir).glob(f"{kind}_*.json*")):
            opener = gzip.open if path.suffix == ".gz" else open
            with opener(path, "rt", encoding="utf-8") as handle:
                records = json.load(handle)
            if isinstance(records, list):
                for record in records:
                    yield audit_record(record, kind, path.name)


def export_audit(destination, data_dir=DATA):
    """Write a complete compressed JSON ledger, row CSV and small JSON summary."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    records = list(audit_catalogue(data_dir))
    summary = {"scope": "Structural audit of all bundled raw records; no global datasheet re-verification",
               "records": len(records), "kinds": dict(Counter(r["kind"] for r in records)),
               "states": dict(Counter(r["status"] for r in records)),
               "field_states": dict(Counter(s for r in records for s in r["fields"].values()))}
    with gzip.open(destination / "catalog-audit-20261029-R01.json.gz", "wt", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, separators=(",", ":"))
    (destination / "catalog-audit-summary-20261029-R01.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (destination / "catalog-audit-20261029-R01.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["kind", "origin", "manufacturer", "model", "source", "revision", "status", "issues", "unknown_fields"])
        for r in records:
            writer.writerow([r[k] for k in ("kind", "origin", "manufacturer", "model", "source", "revision", "status")]
                            + ["; ".join(r["issues"]), "; ".join(k for k, s in r["fields"].items() if s == "unknown")])
    return summary
