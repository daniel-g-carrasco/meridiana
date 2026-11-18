"""Quantities typed in a field (study 15, 3.2): units and arithmetic, the comma and the point, and errors said
clearly; never Python's eval."""

import unittest

import _setup  # noqa: F401

from meridiana import quantity
from meridiana.quantity import QuantityError, parse


class GoodCases(unittest.TestCase):
    def test_lengths_with_units_and_arithmetic(self):
        for text, metres in (("2 m + 30 cm", 2.3), ("150 mm", 0.15), ("1,5", 1.5), ("1.5", 1.5), ("2*1,134", 2.268),
                             ("2 m 30 cm", 2.3), ("0,8*3 m", 2.4), ("(1 + 2) * 50 cm", 1.5), ("3 m / 2", 1.5),
                             ("-2 m", -2.0), ("2 m - 30 cm", 1.7), ("0,02 km", 20.0), (",5", 0.5), ("2 M", 2.0)):
            with self.subTest(text):
                self.assertAlmostEqual(parse(text, "length", "m"), metres)

    def test_a_number_without_a_unit_takes_the_fields_unit(self):
        self.assertAlmostEqual(parse("150", "length", "mm"), 150.0)
        self.assertAlmostEqual(parse("2 m + 30", "length", "cm"), 230.0)     # 200 cm + 30 cm
        self.assertAlmostEqual(parse("1 m", "length", "mm"), 1000.0)

    def test_angles_powers_and_percentages(self):
        self.assertAlmostEqual(parse("17°", "angle"), 17.0)
        self.assertAlmostEqual(parse("17 deg", "angle"), 17.0)
        self.assertAlmostEqual(parse("0,5 rad", "angle"), 28.6478897565)
        self.assertAlmostEqual(parse("30° + 15", "angle"), 45.0)
        self.assertAlmostEqual(parse("1 kW + 500 W", "power", "kW"), 1.5)
        self.assertAlmostEqual(parse("6 kWp", "power", "W"), 6000.0)
        self.assertAlmostEqual(parse("12,5 %", "percent"), 12.5)
        self.assertAlmostEqual(parse("2,5", "number"), 2.5)


class WrongCases(unittest.TestCase):
    def wrong(self, text, kind="length", unit="m") -> str:
        with self.assertRaises(QuantityError) as caught:
            parse(text, kind, unit)
        return str(caught.exception)

    def test_a_separator_is_never_dropped_in_silence(self):
        self.assertIn("ambiguous", self.wrong("1.300,5"))
        self.assertIn("decimal separator", self.wrong("1.30,5"))
        self.assertIn("decimal separator", self.wrong("1 300"))

    def test_a_unit_of_another_kind_says_which_units_the_field_takes(self):
        self.assertIn("mm, cm, m, km", self.wrong("3 kg"))
        self.assertIn("mm, cm, m, km", self.wrong("2 m + 3°"))
        self.assertIn("°", self.wrong("2 m", "angle", ""))
        self.assertIn("without a unit", self.wrong("2 m", "number", ""))

    def test_an_area_is_not_a_length(self):
        self.assertIn("not a length", self.wrong("2 m * 3 m"))

    def test_what_is_missing_or_out_of_place(self):
        self.assertIn("Nothing", self.wrong(""))
        self.assertIn("Nothing", self.wrong("   "))
        self.assertIn("missing", self.wrong("2 +"))
        self.assertIn("parenthesis", self.wrong("(2 + 3"))
        self.assertIn("«)»", self.wrong("2)"))
        self.assertIn("«*»", self.wrong("* 3"))
        self.assertIn("zero", self.wrong("1 / 0"))

    def test_python_is_never_evaluated(self):
        for text in ("__import__('os').system('echo no')", "import os", "1 if 1 else 2", "2**10", "abs(-1)"):
            with self.subTest(text):
                self.wrong(text)

    def test_a_point_before_three_digits_is_not_guessed(self):
        message = self.wrong("1.500")                       # 1500 for an Italian, 1,5 for an English reader
        self.assertIn("1500", message)
        self.assertIn("1,5", message)
        self.wrong("12.345")
        self.wrong("2 m + 1.500 m")
        self.assertAlmostEqual(parse("1,500", "length", "m"), 1.5)      # the comma is a decimal one
        for text, value in (("1.5", 1.5), ("1.50", 1.5), ("1.5000", 1.5), ("0.500", 0.5), (".500", 0.5),
                            ("1500", 1500.0)):
            with self.subTest(text):
                self.assertAlmostEqual(parse(text, "length", "m"), value)

    def test_what_is_not_a_finite_number_is_refused(self):
        for text in ("9" * 400, "9" * 400 + " - " + "9" * 400, "1" + "0" * 200 + " * 1" + "0" * 200):
            with self.subTest(text[:12]):
                self.assertIn("large", self.wrong(text))

    def test_too_many_parentheses_or_signs_are_an_error_not_a_crash(self):
        self.assertIn("parenthes", self.wrong("(" * 400 + "1" + ")" * 400))
        self.assertIn("sign", self.wrong("-" * 400 + "1"))
        self.assertAlmostEqual(parse("((((1 + 2))))", "length", "m"), 3.0)

    def test_the_unicode_minus_is_a_minus(self):
        self.assertAlmostEqual(parse("\u22122 m", "length", "m"), -2.0)
        self.assertAlmostEqual(parse("3 m \u2212 50 cm", "length", "m"), 2.5)

    def test_an_unknown_kind_is_a_programming_error(self):
        with self.assertRaises(ValueError):
            parse("1", "mass")
        self.assertEqual(set(quantity.kind_names()), set(quantity.UNITS))


if __name__ == "__main__":
    unittest.main()
