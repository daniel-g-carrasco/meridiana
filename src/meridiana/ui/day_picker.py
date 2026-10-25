"""The month of a day field (the sun's day, R103 and Daniel's note of 25/10/2026: «il calendario non ha un bordino
esterno come il resto del programma più radius armonizzato»): the card of the little windows, its border and its
8 px corners, the days drawn as the rows of a list are (the one chosen on a neutral ground with the 4 px corners
of an item, today in a thin ring, the days of the other months faded), the months turned with Lucide's chevrons.
No accent: the choice is told by the ground, as in the menus."""

from __future__ import annotations

from PySide6.QtCore import QDate, QRectF, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QPalette, QPen, QTextCharFormat
from PySide6.QtWidgets import QCalendarWidget, QToolButton

from . import icons
from .design import Icon, Line, Radius, Size, Space


class DayPicker(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("day-picker")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)     # one ground, the card's, as a menu
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
        self.setGridVisible(False)
        for name, icon in (("qt_calendar_prevmonth", "chevron-left"), ("qt_calendar_nextmonth", "chevron-right")):
            button = self.findChild(QToolButton, name)
            if button is not None:
                button.setIcon(icons.icon(icon))
                button.setIconSize(QSize(Icon.CONTROL, Icon.CONTROL))
        self.restyle()

    def restyle(self) -> None:
        """The names of the days in the muted colour on the card's ground, the weekend as the other days (the days
        themselves are drawn by `paintCell`). As large as a month needs: a day as wide as «mer» or «30» with the
        room of an item around, as high as a row of a list."""
        pal = self.palette()
        names = QTextCharFormat()
        names.setForeground(pal.color(QPalette.ColorRole.PlaceholderText))
        names.setBackground(QBrush(QColor(0, 0, 0, 0)))
        self.setHeaderTextFormat(names)
        for day in (Qt.DayOfWeek.Saturday, Qt.DayOfWeek.Sunday):
            self.setWeekdayTextFormat(day, QTextCharFormat())          # not red
        m = self.fontMetrics()
        widest = max(m.horizontalAdvance(self.locale().dayName(d, self.locale().FormatType.ShortFormat))
                     for d in range(1, 8))
        cell = max(widest, m.horizontalAdvance("30")) + 2 * Space.M
        self.setMinimumSize(QSize(7 * cell + 2 * Space.XS, Size.CONTROL + Space.XS + 7 * Size.CHIP + 2 * Space.XS))

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in (event.Type.PaletteChange, event.Type.StyleChange):
            self.restyle()

    def paintCell(self, painter, rect, day: QDate) -> None:
        pal = self.palette()
        cell = QRectF(rect).adjusted(Space.XXS, Space.XXS, -Space.XXS, -Space.XXS)
        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        shown = day.month() == self.monthShown() and day.year() == self.yearShown()
        if day == self.selectedDate():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(pal.color(QPalette.ColorRole.Mid))
            painter.drawRoundedRect(cell, Radius.INNER, Radius.INNER)
        elif day == QDate.currentDate():
            painter.setPen(QPen(pal.color(QPalette.ColorRole.Mid), Line.HAIR))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            half = Line.HAIR / 2
            painter.drawRoundedRect(cell.adjusted(half, half, -half, -half), Radius.INNER, Radius.INNER)
        painter.setPen(pal.color(QPalette.ColorRole.Text if shown else QPalette.ColorRole.PlaceholderText))
        painter.drawText(QRectF(rect), Qt.AlignmentFlag.AlignCenter, str(day.day()))
        painter.restore()
