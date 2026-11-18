"""Calendar inline editors and popup surfaces at the actual font and theme."""
import unittest

import _setup
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QFont
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDateEdit, QSpinBox, QToolButton, QWidget

from meridiana.ui.day_picker import DayPicker

setUpModule = _setup.keep_global_state


class CalendarGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_year_editor_fits_navigation_bar_in_light_dark_and_large_text(self):
        for mode in ("light", "dark"):
            _setup.meridiana_look(mode)
            for size in (13, 18):
                picker = DayPicker()
                self.addCleanup(_setup.dispose, picker)
                font = QFont(picker.font())
                font.setPixelSize(size)
                picker.setFont(font)
                picker.show()
                self.app.processEvents()
                year = picker.findChild(QToolButton, "qt_calendar_yearbutton")
                year.click()
                self.app.processEvents()
                edit = picker.findChild(QSpinBox, "qt_calendar_yearedit")
                bar = picker.findChild(QWidget, "qt_calendar_navigationbar")
                self.assertTrue(edit.isVisible())
                self.assertTrue(bar.rect().contains(edit.geometry()), (mode, size, bar.rect(), edit.geometry()))
                self.assertGreaterEqual(edit.lineEdit().width(), edit.fontMetrics().horizontalAdvance("8888"))
                self.assertGreaterEqual(edit.lineEdit().height(), edit.fontMetrics().height())
                picker.close()

    def test_month_list_has_a_transparent_surface_outside_rounded_corners(self):
        _setup.meridiana_look()
        picker = DayPicker()
        self.addCleanup(_setup.dispose, picker)
        menu = picker.findChild(QToolButton, "qt_calendar_monthbutton").menu()
        menu.popup(QPoint(80, 80))
        self.app.processEvents()
        image = menu.grab().toImage()
        self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
        self.assertEqual(image.pixelColor(image.width() // 2, image.height() // 2).alpha(), 255)
        menu.hide()

    def test_calendar_popup_uses_the_same_rounded_surface_as_the_month_list(self):
        _setup.meridiana_look()
        day = QDateEdit()
        self.addCleanup(_setup.dispose, day)
        day.setCalendarPopup(True)
        picker = DayPicker()
        day.setCalendarWidget(picker)
        day.show()
        self.app.processEvents()
        QTest.mouseClick(day, Qt.MouseButton.LeftButton, pos=QPoint(day.width() - 10, day.height() // 2))
        self.app.processEvents()
        self.assertTrue(picker.isVisible())
        image = picker.window().grab().toImage()
        self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
        self.assertEqual(image.pixelColor(image.width() - 1, image.height() - 1).alpha(), 0)
        self.assertEqual(image.pixelColor(image.width() // 2, image.height() // 2).alpha(), 255)
        picker.window().hide()
