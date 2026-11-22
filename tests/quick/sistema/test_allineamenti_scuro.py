"""R700: dark theme, scale 1, in its own process and isolated profile."""
import unittest
from quick.sistema.test_allineamenti import run_case, setUpModule  # noqa: F401


class DarkAlignment(unittest.TestCase):
    def test_dark_at_one(self):
        run_case(self, 'dark', '1')
