"""The purposes of the report's templates keep their technical checks (the report's tables, rows and pages are
tested on the PDF itself: widget/test_report.py, nucleo/test_report_typst.py)."""
import unittest


class Documents(unittest.TestCase):
    def test_purpose_presets_keep_technical_checks_visible(self):
        from meridiana import reports
        for key in ('client', 'electrical', 'energy'):
            self.assertIn('checks', reports.templates()[key].chapters)
