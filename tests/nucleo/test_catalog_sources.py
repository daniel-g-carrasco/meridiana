"""The source audit rejects drift and distinguishes rounding from exact values."""
import gzip
import importlib.util
import json
import os
from pathlib import Path
import unittest

import _setup

from meridiana.catalog import DATA, KINDS
from meridiana.catalog.audit import audit_record


spec = importlib.util.spec_from_file_location("audit_catalog_sources", _setup.ROOT / "tools/audit_catalog_sources.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

# the pinned CEC CSVs (commit cba319de, SAM libraries of 2026): on Daniel's PC under the catalogue archive, elsewhere
# where MERIDIANA_CEC_REFERENCE says; without them the comparison with the source is skipped, not faked
REFERENCE = Path(os.environ.get("MERIDIANA_CEC_REFERENCE")
                 or r"C:\Users\Grasso\Elettrico\reference\catalogs\CEC-SAM\audit-20261029-R01")
# the four CEC rows whose Imp is above Isc in the source itself (audit R238): kept as the source has them,
# refused by the catalogue dialog, never mended by hand
INCONSISTENT_CEC_MODULES = {
    "cec:LENERGY POWER INC LP-505-144M-B", "cec:LENERGY POWER INC LP-505-144M-W",
    "cec:Sonali Energees USA LLC SS-505-144M-B", "cec:Sonali Energees USA LLC SS-505-144M-W",
}


class SourceComparison(unittest.TestCase):
    def test_inventory_reports_missing_extra_and_duplicate_records(self):
        before = [{"id": "a", "power": 10}, {"id": "b", "power": 20}]
        after = [{"id": "a", "power": 11}, {"id": "c"}, {"id": "c"}]
        result = audit.compare_records(before, after)
        self.assertEqual(result["missing"], ["b"])
        self.assertEqual(result["extra"], ["c"])
        self.assertEqual(result["duplicate_ids"], ["c"])
        self.assertEqual(result["differences"], [{"id": "a", "field": "power", "expected": 10, "actual": 11}])
        self.assertFalse(result["matches"])

    def test_nested_coefficient_and_version_drift_are_not_ignored(self):
        expected = [{"id": "a", "sandia": {"C0": 1e-6}, "list_version": "2026"}]
        actual = [{"id": "a", "sandia": {"C0": 2e-6}, "list_version": "2025"}]
        result = audit.compare_records(expected, actual)
        self.assertEqual({d["field"] for d in result["differences"]}, {"sandia.C0", "list_version"})

    def test_nan_from_source_stays_missing_not_zero(self):
        self.assertIsNone(audit.source_number("NaN", 3))
        self.assertIsNone(audit.source_number("", 3))
        self.assertEqual(audit.source_number("18.1674", 3), 18.167)
        self.assertEqual(audit.source_number("-8.03947e-06"), -8.03947e-6)

    def test_changed_payload_does_not_pass_pinned_hash(self):
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            audit.verify_payload(b"changed", "0" * 64)


class BundledData(unittest.TestCase):
    """What the audit of 30/10/2026 found in the files shipped, fixed so that a rebuild says when it changes."""

    def test_the_four_cec_inconsistencies_are_kept_and_flagged(self):
        with gzip.open(DATA / "modules_cec.json.gz", "rt", encoding="utf-8") as handle:
            modules = json.load(handle)
        self.assertEqual(len(modules), 21640)
        wrong = {r["id"]: (r["imp"], r["isc"]) for r in modules if r["imp"] > r["isc"]}
        self.assertEqual(set(wrong), INCONSISTENT_CEC_MODULES)
        self.assertEqual(set(wrong.values()), {(12.46, 12.27)})
        for record in modules:
            if record["id"] in INCONSISTENT_CEC_MODULES:
                result = audit_record(record, "modules", "modules_cec.json.gz")
                self.assertEqual(result["status"], "inconsistent")
                self.assertIn("imp > isc", result["issues"])

    def test_the_verified_fields_are_the_34_huawei_ones_with_page_and_revision(self):
        verified = []
        for kind in KINDS:
            for path in sorted(DATA.glob(f"{kind}_curated.json")):
                for record in json.loads(path.read_text(encoding="utf-8")):
                    for field, evidence in (record.get("field_sources") or {}).items():
                        verified.append((record["manufacturer"], record["model"], field, evidence))
                        self.assertEqual(audit_record(record, kind, path.name)["fields"][field], "verified_field")
        self.assertEqual(len(verified), 34)
        self.assertEqual({v[0] for v in verified}, {"Huawei"})
        self.assertEqual({v[1] for v in verified}, {"LUNA2000-5-S1", "LUNA2000-7-S1", "LUNA2000-10-S1",
                                                   "LUNA2000-14-S1", "LUNA2000-15-S1", "LUNA2000-21-S1",
                                                   "SUN2000-20K-MB0"})
        for _maker, _model, _field, evidence in verified:
            self.assertEqual(evidence["page"], 2)
            self.assertIn(evidence["revision"], ("01-202509", "01-202504"))
            self.assertTrue(evidence["source"].startswith("https://solar.huawei.com/"))
            self.assertEqual(evidence["verified"], "2026-10-29")

    def test_bundle_matches_the_pinned_source_when_it_is_on_the_disk(self):
        if not (REFERENCE / "CEC Modules.csv").exists():
            self.skipTest(f"the pinned CEC CSVs are not at {REFERENCE} (MERIDIANA_CEC_REFERENCE)")
        result = audit.audit(REFERENCE)
        self.assertTrue(result["comparisons"]["modules"]["matches"])
        self.assertTrue(result["comparisons"]["inverters"]["matches"])
        self.assertEqual(result["comparisons"]["modules"]["expected_records"], 21640)
        self.assertEqual(result["comparisons"]["inverters"]["expected_records"], 2343)
        self.assertEqual({r["id"] for r in result["inconsistent_modules"]}, INCONSISTENT_CEC_MODULES)
        self.assertEqual(result["module_versions"], [("2026.7.3", "2026-06-23")])
