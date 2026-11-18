"""Calendar days respond to the real viewport's pointer without changing selection."""
import unittest

import _setup
from PySide6.QtCore import QDate, QEvent, QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QAbstractItemView

from meridiana import config
from meridiana.ui.day_picker import DayPicker
from meridiana.ui.theme import Theme

setUpModule = _setup.keep_global_state


class RecordedPicker(DayPicker):
    def __init__(self):
        self.cells = {}
        super().__init__()

    def paintCell(self, painter, rect, day):
        self.cells[day] = QRect(rect)
        super().paintCell(painter, rect, day)


class CalendarHover(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.theme = Theme(config.Config(theme="light", background="none"), app=self.app)
        self.addCleanup(self.theme.deleteLater)
        self.picker = RecordedPicker()
        self.addCleanup(_setup.dispose, self.picker)
        self.picker.setMinimumDate(QDate(2026, 10, 3))
        self.picker.setMaximumDate(QDate(2026, 10, 31))
        self.picker.setSelectedDate(QDate(2026, 10, 10))
        self.picker.setCurrentPage(2026, 10)
        self.picker.show()
        self.app.processEvents()
        self.view = self.picker.findChild(QAbstractItemView, "qt_calendar_calendarview")

    def move(self, day):
        position = self.picker.cells[day].center()
        event = QMouseEvent(QEvent.Type.MouseMove, QPointF(position),
                            QPointF(self.view.viewport().mapToGlobal(position)), Qt.MouseButton.NoButton,
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
        self.app.sendEvent(self.view.viewport(), event)
        self.app.processEvents()

    def cell(self, day):
        image = self.view.viewport().grab().toImage()
        rect, scale = self.picker.cells[day], image.devicePixelRatio()
        return image.copy(round(rect.x() * scale), round(rect.y() * scale),
                          round(rect.width() * scale), round(rect.height() * scale))

    def test_hover_marks_normal_and_selected_days_in_both_themes_without_selecting_them(self):
        for mode in ("light", "dark"):
            self.theme.cfg.theme = mode
            self.theme.apply()
            self.app.processEvents()
            for day in (QDate(2026, 10, 20), self.picker.selectedDate()):
                self.move(QDate(2026, 10, 25))
                before = self.cell(day)
                self.move(day)
                self.assertNotEqual(self.cell(day), before, (mode, day))
                self.assertEqual(self.picker.selectedDate(), QDate(2026, 10, 10))

    def test_disabled_dates_have_no_hover_and_leaving_clears_the_hover(self):
        day = QDate(2026, 10, 1)
        before = self.cell(day)
        self.move(day)
        self.assertEqual(before, self.cell(day))
        day = QDate(2026, 10, 20)
        before = self.cell(day)
        self.move(day)
        self.assertNotEqual(before, self.cell(day))
        self.app.sendEvent(self.view.viewport(), QEvent(QEvent.Type.Leave))
        self.app.processEvents()
        self.assertEqual(before, self.cell(day))
        self.picker.setEnabled(False)
        self.app.processEvents()
        before = self.cell(day)
        self.move(day)
        self.assertEqual(before, self.cell(day), "A disabled calendar has no hover")

    def test_today_keeps_its_ring_while_hovered(self):
        from PySide6.QtGui import QPalette
        today = QDate.currentDate()
        self.picker.setMinimumDate(today.addMonths(-1))
        self.picker.setMaximumDate(today.addMonths(1))
        self.picker.setSelectedDate(today.addDays(1))
        self.picker.setCurrentPage(today.year(), today.month())
        self.app.processEvents()
        before = self.cell(today)
        self.move(today)
        after = self.cell(today)
        self.assertNotEqual(before, after)
        ring = self.picker.palette().color(QPalette.ColorRole.Mid)
        for image in (before, after):
            self.assertTrue(any(image.pixelColor(x, y) == ring for x in range(image.width())
                                for y in range(image.height())), "Today's ring remains visible")
