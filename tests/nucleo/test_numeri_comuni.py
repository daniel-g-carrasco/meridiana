"""The numbers of the texts for the user, written in one place (r35-segni, Daniel 14/11/2026: «La nota dei Consumi dice
ancora "358.6 kWp" con il punto... centralizziamo»): meridiana.i18n.number, the decimal comma in Italian and the point
in English, from the texts of the program as they are made. The guard that no number is written by hand again is
numeri_a_mano in tests/quick/sistema/test_riordino.py."""
import unittest

import _setup

from meridiana import i18n

setUpModule = _setup.keep_global_state

CATALOGUE = _setup.ROOT / "locale" / "it" / "LC_MESSAGES" / "meridiana.mo"


@unittest.skipUnless(CATALOGUE.exists(), "tools/compile_po.py first")
class CommonNumbers(unittest.TestCase):
    def speak(self, language):
        before = i18n._translation
        self.addCleanup(setattr, i18n, "_translation", before)
        i18n.setup(language)

    def test_the_consumption_note_writes_the_power_with_the_comma_in_italian(self):
        from meridiana.core.energy.consumption import Context
        from meridiana.core.rules.profiles.it import consumption
        self.speak("it")
        note = consumption.guess(Context(p_stc_kw=358.6)).why
        self.assertIn("358,6 kWp", note)
        self.assertIn("1200 kWh/kWp", note)
        self.assertNotIn("358.6", note)
        self.speak("en")
        self.assertIn("358.6 kWp", consumption.guess(Context(p_stc_kw=358.6)).why)

    def test_a_height_said_back_by_a_roof_has_the_comma(self):
        from meridiana.core.geometry import roofs
        self.speak("it")
        with self.assertRaises(ValueError) as said:
            roofs.eave_keeping_ridge(2.5, 10.0, 30.0)
        self.assertIn("2,50 m", str(said.exception))

    def test_a_value_said_as_it_was_written(self):
        self.speak("it")
        self.assertEqual([i18n.number(v, None) for v in (450.0, 13.5, 0.045)], ["450", "13,5", "0,045"])
        self.assertEqual(i18n.number(1.0, None, sign=True), "+1")
        self.speak("en")
        self.assertEqual(i18n.number(13.5, None), "13.5")


if __name__ == "__main__":
    unittest.main()
