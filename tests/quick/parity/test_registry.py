"""The parity ledger must expose omissions instead of reporting false completion."""

import copy
import unittest

from quick.parity import registry


class RegistryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = registry.load_registry()
        cls.inventory = registry.inventory()

    def test_committed_inventory_has_every_current_source_item(self):
        self.assertEqual([], registry.validate(self.document, self.inventory))

    def test_disappearing_and_new_commands_are_reported(self):
        current = copy.deepcopy(self.inventory)
        command = next(row for row in current if row["kind"] == "command")
        current.remove(command)
        current.append({**command, "id": "command:new_regression_command"})
        errors = "\n".join(registry.validate(self.document, current))
        self.assertIn(command["id"], errors)
        self.assertIn("command:new_regression_command", errors)

    def test_done_requires_real_behavior_and_visual_evidence(self):
        document = copy.deepcopy(self.document)
        row = document["items"][0]
        row["status"] = "fatto"
        row["evidence"] = []
        self.assertIn(row["id"], "\n".join(registry.validate(document, self.inventory)))
        row["evidence"] = [{"kind": "test", "path": "tests/quick/parity/test_registry.py",
                            "symbol": "RegistryTest.test_done_requires_real_behavior_and_visual_evidence"}]
        self.assertTrue(registry.validate(document, self.inventory))

    def test_fake_evidence_and_unapproved_difference_are_rejected(self):
        document = copy.deepcopy(self.document)
        row = document["items"][0]
        row.update(status="fatto", evidence=[{"kind": "test", "path": "missing.py",
                                            "symbol": "Missing.test_missing", "result": "passed"}])
        self.assertTrue(registry.validate(document, self.inventory))
        row.update(status="differenza voluta", reason="", decision="")
        self.assertTrue(registry.validate(document, self.inventory))

    def test_all_requests_and_test_methods_have_exact_inventory_rows(self):
        self.assertEqual([], registry.validate_csv_inventories())
        requests = registry.request_rows()
        self.assertEqual(400, len(requests))
        self.assertEqual({f"R{i}" for i in range(1, 399)}, {row["request"] for row in requests})
        self.assertEqual(400, len({row["row_id"] for row in requests}))
        self.assertEqual(2, sum(row["request"] == "R30" for row in requests))
        self.assertEqual(2, sum(row["request"] == "R31" for row in requests))
        self.assertEqual(1203, len(registry.test_rows()))     # 1196 until r20 (DXF, symbols, voice: 07/11/2026); r21-recuperi R398

    def test_completion_counts_only_proven_done(self):
        document = {"items": [
            {"id": "a", "phases": ["model"], "status": "da fare"},
            {"id": "b", "phases": ["model"], "status": "in corso"},
            {"id": "c", "phases": ["model"], "status": "differenza voluta"},
        ]}
        summary = registry.completion(document)["model"]
        self.assertEqual(0, summary["percent"])
        self.assertEqual(3, summary["total"])

    def test_source_table_variants_keep_the_actual_request(self):
        rows = {row["row_id"]: row for row in registry.request_rows()}
        self.assertIn("--tour [passo|nuovo]", rows["R318/1"]["request_summary"])
        self.assertTrue(rows["R322/1"]["request_summary"].startswith("«continuano"))
        self.assertTrue(rows["R328/1"]["request_summary"].startswith("«non era"))

    def test_runtime_commands_detect_an_action_lost_in_the_real_window(self):
        commands = {c.id: {"shortcuts": list(c.keys)} for c in registry.shortcuts.commands()}
        self.assertEqual([], registry.validate_runtime_commands({"commands": commands}))
        del commands["import_curve"]
        self.assertIn("import_curve", "\n".join(registry.validate_runtime_commands({"commands": commands})))

    def test_runtime_shortcut_cannot_disappear_while_its_command_survives(self):
        commands = {c.id: {"shortcuts": list(c.keys)} for c in registry.shortcuts.commands()}
        commands["save"]["shortcuts"] = []
        self.assertIn("Runtime shortcut differs: save", "\n".join(
            registry.validate_runtime_commands({"commands": commands})))

    def test_captured_windows_register_all_inventoried_commands(self):
        manifests = registry.runtime_manifests()
        self.assertTrue(manifests, "Capture one real Widgets reference before claiming runtime parity")
        for path, manifest in manifests:
            with self.subTest(manifest=str(path)):
                self.assertEqual([], registry.validate_runtime_commands(manifest))
                # a command named as captured before must really be absent: a new capture that has it drops the entry
                self.assertEqual([], sorted(set(registry.CAPTURED_BEFORE) & set(manifest.get("commands", {}))))


if __name__ == "__main__":
    unittest.main()
