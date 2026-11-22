"""R700: light theme at fractional scale, in its own process and isolated profile."""
import unittest
from quick.sistema.test_allineamenti import run_case, setUpModule  # noqa: F401


class ScaledAlignment(unittest.TestCase):
    def test_light_at_two_and_a_half(self):
        run_case(self, 'light', '2.5')
