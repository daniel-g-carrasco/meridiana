"""R700: results, File and Settings in dark theme, scale 1."""
import unittest
from quick.sistema.test_allineamenti import run_case, setUpModule  # noqa: F401


class DarkPageAlignment(unittest.TestCase):
    def test_pages_dark_at_one(self):
        run_case(self, 'dark', '1', 'pages')
