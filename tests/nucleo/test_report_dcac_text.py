"""The energy the inverters cut is already a percentage (stringing.overload_loss): the report prints it as it is."""
import unittest
from unittest import mock

from meridiana import i18n
from meridiana.report_typst import chapters


class CutEnergy(unittest.TestCase):
    def test_the_cut_is_printed_as_the_percentage_it_is(self):
        i18n.setup("en")
        with mock.patch("meridiana.energy.plant.dcac", return_value=(1.35, 0.726)):
            text = chapters._dcac_text(object())
        self.assertIn("0.7 %", text)
        self.assertNotIn("72.6", text)


if __name__ == "__main__":
    unittest.main()
