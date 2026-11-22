"""An exact, decreasing debt list and counterexamples for its scanner."""

import json
import hashlib
from pathlib import Path
import tempfile
import unittest

from profili import leaks

REFERENCE = Path(__file__).parent / "riferimenti"


class NationalReferences(unittest.TestCase):
    def test_calendar_service_calls_do_not_authorize_national_data(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "calls.py").write_text(
                "def days(calendar):\n    return calendar.holidays(2023)\n"
                "def bad(calendar):\n    return calendar.holidays(2023), 'ARERA'\n"
                "def holidays(year):\n    return {1, 6}\n", encoding="utf-8")
            rows = leaks.scan(root)
            self.assertEqual(len(rows), 2)
            self.assertEqual({r['symbol'] for r in rows}, {'bad', 'holidays'})

    def test_calendar_protocol_does_not_choose_a_national_calendar(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "contract.py").write_text(
                "from typing import Protocol\nclass Calendar(Protocol):\n"
                "    def holidays(self, year: int) -> set: ...\n"
                "SOURCE = 'ARERA'\n", encoding="utf-8")
            rows = leaks.scan(root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["text"], "SOURCE = 'ARERA'")

    def test_no_new_or_stale_debt(self):
        debts = json.loads((REFERENCE / "debiti.json").read_text(encoding="utf-8"))
        added, stale = leaks.compare(leaks.scan(), debts)
        self.assertFalse(added, f"New national references: {sorted(added)}")
        self.assertFalse(stale, f"Paid debts still listed: {sorted(stale)}")
        original = json.loads((REFERENCE / "debiti-iniziali.json").read_text(encoding="utf-8"))
        self.assertTrue(leaks.within_initial(debts, original))
        self.assertTrue(all(r.get("reason") for r in debts))

    def test_only_registries_import_concrete_profiles(self):
        self.assertEqual(leaks.imports(), [])
        self.assertEqual(leaks.core_profile_imports(), [])

    def test_new_python_qml_json_and_removed_debt_are_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, source in (("policy.py", 'LIMIT = "CEI 0-21"\n'),
                                 ("view.qml", 'Text { text: "VVF" }\n'),
                                 ("data.json", '{"CER": "new national input"}')):
                (root / name).write_text(source, encoding="utf-8")
            rows = leaks.scan(root)
            self.assertEqual({r["path"] for r in rows}, {"policy.py", "view.qml", "data.json"})
            self.assertEqual(leaks.compare(rows, [])[0], {leaks.key(r) for r in rows})
            self.assertEqual(leaks.compare([], rows)[1], {leaks.key(r) for r in rows})
            paid = root / "core/rules/profiles/it"
            paid.mkdir(parents=True)
            (paid / "policy.py").write_text('LIMIT = "CEI 64-8"', encoding="utf-8")
            self.assertEqual(leaks.scan(root), rows)

    def test_italian_import_cannot_hide_outside_registry(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "caller.py").write_text("from meridiana.core.rules.profiles.it import profile\n", encoding="utf-8")
            self.assertEqual(leaks.imports(root), ["caller.py:1"])
            (root / "registry.py").write_text("import meridiana.core.rules.profiles.it.profile\n", encoding="utf-8")
            self.assertEqual(leaks.imports(root), ["caller.py:1", "registry.py:1"])

    def test_initial_manifest_is_frozen(self):
        # Git's normal checkout conversion must not count as an edited manifest.
        raw = (REFERENCE / "debiti-iniziali.json").read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         "8a33a074f5bdd5fe7bf0eea7f18cdc8823481862b43405238154c16036745b15")

    def test_occurrences_can_be_subtracted_but_never_added(self):
        row = {"path": "core/policy.py", "symbol": "policy", "text": '"CEI 0-21"', "count": 2}
        self.assertTrue(leaks.within_initial([{**row, "count": 1}], [row]))
        self.assertFalse(leaks.within_initial([{**row, "count": 3}], [row]))
        self.assertFalse(leaks.within_initial([{**row, "text": '"CEI 0-16"'}], [row]))


class CompatibilityDefaults(unittest.TestCase):
    def test_persisted_name_is_not_a_policy_or_a_source(self):
        import tempfile
        from pathlib import Path
        from profili.leaks import scan
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.py"
            path.write_text("trase: float = field(default_factory=lambda: registry.legacy_default('economics', 'trase'))\n", encoding="utf-8")
            self.assertEqual(scan(Path(folder)), [])
            path.write_text(path.read_text(encoding="utf-8").rstrip() + " # ARERA\n", encoding="utf-8")
            self.assertEqual(len(scan(Path(folder))), 1)
            path.write_text("trase: float = 0.008\n", encoding="utf-8")
            self.assertEqual(len(scan(Path(folder))), 1)


class EmptyCalendar(unittest.TestCase):
    def test_empty_calendar_does_not_authorize_national_dates_or_comments(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "calendar.py"
            path.write_text("def holidays(year):\n    return set()\n", encoding="utf-8")
            self.assertEqual(leaks.scan(root), [])
            path.write_text("def holidays(year): # ARERA\n    return set()\n", encoding="utf-8")
            self.assertEqual(len(leaks.scan(root)), 1)
            path.write_text("def holidays(year):\n    return {date(year, 4, 25)}\n", encoding="utf-8")
            self.assertEqual(len(leaks.scan(root)), 1)
