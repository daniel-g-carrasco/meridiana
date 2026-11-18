"""A long checkbox goes onto two lines rather than widen its card (Daniel, 02/11/2026, the Settings > Assistant
page at about 1000 px: «Meridio animato: i raggi girano, gli occhi battono e guardano in giro, una smorfia ogni tanto»
kept the page 51 px wider than its scroll area, a horizontal bar and the corner square between the two bars, the
texts cut on the right and the arrow of the list «Disegno» out of sight). A QCheckBox never wraps: its minimum width
is its whole text. `ui/style.wrap_check` gives it the rule of the wrapped labels; the shared style applies it to
every long checkbox the application polishes. PySide6 and a display (offscreen will do)."""

import unittest

import _setup

setUpModule = _setup.keep_global_state

LONG = ("Meridio animato: i raggi girano, gli occhi battono e guardano in giro, una smorfia ogni tanto, "
        "e il fumetto si apre e si chiude con calma")


class WrappedChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        _setup.meridiana_look()

    def card(self, text, kind=None):
        from PySide6.QtWidgets import QCheckBox, QScrollArea, QVBoxLayout, QWidget
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        page = QWidget()
        box = QVBoxLayout(page)
        check = (kind or QCheckBox)(text)
        box.addWidget(check)
        box.addStretch(1)
        scroll.setWidget(page)
        scroll.resize(320, 300)
        scroll.show()
        self.addCleanup(scroll.deleteLater)
        _setup.turn_events(self.app, 50)
        return scroll, check

    def test_a_long_checkbox_wraps_inside_its_card(self):
        from meridiana.ui.design import Size
        scroll, check = self.card(LONG)
        self.assertFalse(scroll.horizontalScrollBar().isVisible())
        self.assertLessEqual(scroll.widget().width(), scroll.viewport().width())
        self.assertLessEqual(check.width(), scroll.viewport().width())
        self.assertGreater(check.height(), Size.CONTROL)              # two lines or more, all of them seen
        self.assertGreaterEqual(check.height(), check.heightForWidth(check.width()))
        self.assertEqual(check.text(), LONG)                         # the text, its name and its key stay
        # wide again: one line, as tall as every control
        scroll.resize(1400, 300)
        _setup.turn_events(self.app, 50)
        self.assertEqual(check.height(), Size.CONTROL)

    def test_a_long_radio_button_wraps_as_well(self):
        """The Consumption's «Mese per mese e per fascia (bollette)» held its column 37 px wider than the card."""
        from PySide6.QtWidgets import QRadioButton

        from meridiana.ui.design import Size
        scroll, radio = self.card(LONG, QRadioButton)
        self.assertLessEqual(scroll.widget().width(), scroll.viewport().width())
        self.assertGreater(radio.height(), Size.CONTROL)

    def test_the_whole_text_toggles_it_and_a_new_text_is_measured(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        scroll, check = self.card(LONG)
        before = check.isChecked()
        from PySide6.QtWidgets import QStyle, QStyleOptionButton
        opt = QStyleOptionButton()
        check.initStyleOption(opt)
        left = check.style().subElementRect(QStyle.SubElement.SE_CheckBoxContents, opt, check).left()
        QTest.mouseClick(check, Qt.MouseButton.LeftButton, pos=QPoint(left + 10, check.height() - 10))
        self.assertNotEqual(check.isChecked(), before)                # a click on the second line
        check.setText("Una voce di trenta caratteri, corta")          # one line, short: the empty width beyond it
        _setup.turn_events(self.app, 50)
        now = check.isChecked()
        QTest.mouseClick(check, Qt.MouseButton.LeftButton, pos=QPoint(check.width() - 4, check.height() - 10))
        self.assertEqual(check.isChecked(), now)
        check.setText("Breve")
        _setup.turn_events(self.app, 50)
        from meridiana.ui.design import Size
        self.assertEqual(check.height(), Size.CONTROL)

    def test_the_picture_holds_the_square_and_the_lines(self):
        """The square drawn by the shared style at the first line, the text beside it, not under it."""
        from PySide6.QtWidgets import QStyle, QStyleOptionButton
        scroll, check = self.card(LONG)
        opt = QStyleOptionButton()
        check.initStyleOption(opt)
        from meridiana.ui.design import Size
        opt.rect.setHeight(Size.CONTROL)                              # the band of the first line
        square = check.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, opt, check)
        image = check.grab().toImage()
        background = image.pixelColor(2, check.height() - 2)
        inked_right = any(image.pixelColor(x, y) != background
                          for x in range(square.right() + 6, check.width()) for y in range(check.height() // 2,
                                                                                          check.height()))
        self.assertTrue(inked_right)                                  # the second line is drawn
        inked_under = any(image.pixelColor(x, y) != background
                          for x in range(0, square.right()) for y in range(square.bottom() + 8, check.height()))
        self.assertFalse(inked_under)                                 # nothing under the square


if __name__ == "__main__":
    unittest.main()
