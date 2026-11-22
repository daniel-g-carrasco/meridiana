"""R700: results, File and Settings in dark theme, scale 2.5."""
import unittest
from quick.sistema.test_allineamenti import run_case, setUpModule  # noqa: F401


class ScaledDarkPageAlignment(unittest.TestCase):
    def test_pages_dark_at_two_and_a_half(self):
        run_case(self, 'dark', '2.5', 'pages')
