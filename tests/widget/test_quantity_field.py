"""The field that takes a quantity with its unit: Enter computes the calculation, what cannot be read is said
and leaves the value, the wheel changes it only with the keyboard on it. PySide6 and a display (offscreen
will do)."""

import unittest

import _setup

from meridiana.i18n import number

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class Field(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from meridiana.ui import wheel
        from meridiana.ui.quantity_field import QuantityField
        wheel.guard(self.app)
        self.field = QuantityField("length", "m", 0.0, 100.0, 9.5)
        self.changes, self.refusals = [], []
        self.field.valueChanged.connect(self.changes.append)
        self.field.refused.connect(self.refusals.append)
        self.field.show()

    def tearDown(self):
        self.field.close()

    def type(self, text: str) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.field.setFocus()
        self.field.selectAll()
        QTest.keyClicks(self.field, text)
        QTest.keyClick(self.field, Qt.Key.Key_Return)

    def test_enter_computes_the_calculation_and_shows_it_with_its_unit(self):
        self.type("2 m + 30 cm")
        self.assertAlmostEqual(self.field.value(), 2.3)
        self.assertEqual(self.changes, [self.field.value()])
        self.assertEqual(self.field.text(), number(2.3) + " m")
        self.type("150 mm*3")
        self.assertAlmostEqual(self.field.value(), 0.45)

    def test_what_cannot_be_read_is_said_and_the_value_stays(self):
        self.type("3 kg")
        self.assertEqual(self.field.value(), 9.5)
        self.assertEqual(self.changes, [])
        self.assertTrue(self.refusals and "mm, cm, m, km" in self.refusals[-1])
        self.type("1 km")                                   # out of the field's range
        self.assertEqual(self.field.value(), 9.5)
        self.assertIn("range", self.refusals[-1])

    def test_the_value_is_written_as_the_language_writes_it(self):
        self.field.setValue(12.25)
        self.assertEqual(self.field.cleanText(), number(12.25) + " m")
        angle = type(self.field)("angle", "°", 0, 80, 17.0, 1, 1)
        self.assertEqual(angle.text(), number(17.0, 1) + "°")

    def test_the_wheel_changes_it_only_with_the_keyboard_on_it(self):
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtWidgets import QApplication, QLineEdit

        def wheel():
            e = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, 120), Qt.MouseButton.NoButton,
                            Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
            QApplication.sendEvent(self.field, e)
        other = QLineEdit()
        self.addCleanup(other.deleteLater)
        self.addCleanup(other.close)
        other.show()
        other.setFocus()
        wheel()
        self.assertEqual(self.field.value(), 9.5)
        _setup.keyboard_or_skip(self, self.field)           # said when the desktop gives no keyboard, not passed
        wheel()
        self.assertAlmostEqual(self.field.value(), 9.6)


if __name__ == "__main__":
    unittest.main()
