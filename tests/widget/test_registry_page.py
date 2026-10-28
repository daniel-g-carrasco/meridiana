"""Clients and jobs in the File page's three-column registry (R150)."""

import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
