"""Storage setup preserves drafts and delegates project mutation."""
import unittest
from PySide6.QtWidgets import QApplication
import _setup
from meridiana.ui.storage_page import StoragePage

setUpModule = _setup.keep_global_state


class StoragePageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_draft_is_not_saved_until_apply(self):
        changes = []
        settings = dict(battery=dict(manufacturer='Test', model='AC unit', coupling='ac',
                        usable_energy_kwh=10, max_charge_power_w=5000, max_discharge_power_w=5000,
                        max_parallel_units=2),
                        storage_coupling='ac', storage_efficiency_pct=90)
        page = StoragePage(settings, [], changes.append)
        page.units.setValue(2)
        self.assertEqual(changes, [])
        self.assertNotIn('battery_units', settings)
        self.assertTrue(page.apply_button.isEnabled())
        page.apply_button.click()
        self.assertEqual(changes[0]['battery_units'], 2)
        page.deleteLater()

    def test_unknown_pairing_cannot_start_calculation(self):
        page = StoragePage(dict(battery={'model': 'unknown'}), [], lambda patch: None)
        self.assertFalse(page.apply_button.isEnabled())
        page.deleteLater()
