"""Clients and jobs in the File page's three-column registry (R150)."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QFileDialog, QMessageBox

import _setup

from meridiana import registry

setUpModule = _setup.keep_global_state


class RegistryPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.meridiana_look()
        self.reg = registry.Registry(Path(tempfile.mkdtemp()) / "registry.sqlite3")
        self.addCleanup(self.reg.close)
        from meridiana.ui.registry_page import RegistryPage
        self.page = RegistryPage(self.reg)
        self.addCleanup(_setup.dispose, self.page)

    def test_client_and_job_are_created_and_chosen_in_the_page(self):
        self.page.new_client.click()
        self.page.client_name.setText("Example client")
        self.page.save_client.click()
        self.assertEqual(self.page.client_list.count(), 1)
        self.page.new_job.click()
        self.page.job_code.setText("00125")
        self.page.job_name.setText("Example job")
        self.page.job_reserved.setChecked(True)
        self.page.save_job.click()
        self.assertEqual(self.page.job_list.count(), 1)
        job = self.reg.list_jobs()[0]
        self.assertEqual((job["code"], job["name"], job["reserved"]), ("00125", "Example job", True))
        self.page.job_list.setCurrentRow(0)
        self.assertIn("00125", self.page.detail.text())
        self.assertIn("Example client", self.page.detail.text())
        self.assertIn("In progress", self.page.detail.text())
        self.assertIn("Preliminary", self.page.detail.text())
        self.assertNotIn("in_progress", self.page.detail.text())

    def test_validation_and_duplicate_codes_have_clear_messages(self):
        self.page.new_client.click()
        self.page.save_client.click()
        self.assertEqual(self.page.error.text(), "A client needs a name.")
        client = self.reg.create_client("Example client")
        self.reg.create_job("00125", "Example job", client["id"])
        self.page.new_job.click()
        self.page.job_code.setText("00125")
        self.page.job_name.setText("Another example")
        self.page.save_job.click()
        self.assertIn("already used", self.page.error.text())
        self.assertNotIn("UNIQUE", self.page.error.text())

    def test_a_linked_folder_writes_its_manifest_only_after_the_checkbox(self):
        client = self.reg.create_client("Example client")
        job = self.reg.create_job("00125", "Example job", client["id"])
        self.page.refresh()
        self.page.job_list.setCurrentRow(0)
        folder = Path(tempfile.mkdtemp())
        with patch.object(QFileDialog, "getExistingDirectory", return_value=str(folder)):
            self.page.link_folder.click()
        self.assertEqual(self.page.folder_box.count(), 1)
        consent = self.page.folder_box.itemAt(0).widget()
        manifest = folder / registry.MANIFEST_NAME
        self.assertFalse(manifest.exists())
        consent.setChecked(True)
        self.assertTrue(manifest.is_file())
        self.assertEqual(registry.read_exchange(manifest, manifest=True)["job"]["id"], job["id"])
        consent.setChecked(False)
        self.assertFalse(manifest.exists())

    def test_an_unwritable_folder_is_named_after_the_consent_commits(self):
        client = self.reg.create_client("Example client")
        self.reg.create_job("00125", "Example job", client["id"])
        self.page.refresh()
        self.page.job_list.setCurrentRow(0)
        folder = Path(tempfile.mkdtemp())
        with patch.object(QFileDialog, "getExistingDirectory", return_value=str(folder)):
            self.page.link_folder.click()
        consent = self.page.folder_box.itemAt(0).widget()
        with patch.object(registry.atomic, "write_json", side_effect=OSError("invented unavailable folder")):
            consent.setChecked(True)
        self.assertTrue(self.reg.list_folders()[0]["manifest_consent"])
        self.assertIn("unavailable folder", self.page.error.text())

    def test_import_is_previewed_before_it_changes_the_registry_and_export_round_trips(self):
        source = registry.Registry(Path(tempfile.mkdtemp()) / "source.sqlite3")
        self.addCleanup(source.close)
        source.create_client("Example client")
        incoming = Path(tempfile.mkdtemp()) / "registry.json"
        source.export(incoming)
        with patch.object(QFileDialog, "getOpenFileName", return_value=(str(incoming), "JSON")):
            self.page.import_registry.click()
        self.assertEqual(self.reg.list_clients(), [])
        self.assertFalse(self.page.apply_import.isHidden())
        self.assertIn("1", self.page.import_preview.text())
        self.page.apply_import.click()
        self.assertEqual(len(self.reg.list_clients()), 1)
        outgoing = Path(tempfile.mkdtemp()) / "exported.json"
        with patch.object(QFileDialog, "getSaveFileName", return_value=(str(outgoing), "JSON")):
            self.page.export_registry.click()
        self.assertEqual(registry.read_exchange(outgoing)["clients"][0]["name"], "Example client")

    def test_exporting_reserved_jobs_requires_an_explicit_yes(self):
        client = self.reg.create_client("Example client")
        self.reg.create_job("00125", "Reserved example", client["id"], reserved=True)
        target = Path(tempfile.mkdtemp()) / "registry.json"
        with (patch.object(QFileDialog, "getSaveFileName", return_value=(str(target), "JSON")),
              patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Cancel) as warning):
            self.page.export_registry.click()
        warning.assert_called_once()
        self.assertFalse(target.exists())
        with (patch.object(QFileDialog, "getSaveFileName", return_value=(str(target), "JSON")),
              patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Yes)):
            self.page.export_registry.click()
        self.assertTrue(target.is_file())


if __name__ == "__main__":
    unittest.main()
