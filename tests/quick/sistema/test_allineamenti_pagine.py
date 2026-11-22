"""R700: results, File and Settings in light theme, scale 1."""
import unittest
from quick.sistema.test_allineamenti import run_case, setUpModule  # noqa: F401


class PageAlignment(unittest.TestCase):
    def test_pages_light_at_one(self):
        run_case(self, 'light', '1', 'pages')
