"""R700: dark theme at fractional scale, in its own process and isolated profile."""
import unittest
from quick.sistema.test_allineamenti import run_case, setUpModule  # noqa: F401


class ScaledDarkAlignment(unittest.TestCase):
    def test_dark_at_two_and_a_half(self):
        run_case(self, 'dark', '2.5')
