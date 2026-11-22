"""R700: results, File and Settings in light theme, scale 2.5."""
import unittest
from quick.sistema.test_allineamenti import run_case, setUpModule  # noqa: F401


class ScaledPageAlignment(unittest.TestCase):
    def test_pages_light_at_two_and_a_half(self):
        run_case(self, 'light', '2.5', 'pages')
