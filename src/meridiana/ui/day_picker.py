"""The month of a day field (the sun's day, R103 and Daniel's note of 25/10/2026: «il calendario non ha un bordino
esterno come il resto del programma più radius armonizzato»): the card of the little windows, its border and its
8 px corners, the days drawn as the rows of a list are (the one chosen on a neutral ground with the 4 px corners
of an item, today in a thin ring, the days of the other months faded), the months turned with Lucide's chevrons.
No accent: the choice is told by the ground, as in the menus."""

from __future__ import annotations

from PySide6.QtCore import QDate, QEvent, QModelIndex, QRectF, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QPalette, QPen, QTextCharFormat
from PySide6.QtWidgets import QAbstractItemView, QCalendarWidget, QSpinBox, QToolButton, QWidget

from .. import theme_colors
from . import icons
from .design import Icon, Line, Radius, Size, Space

NAV_TOP = Space.S           # the month's bar from the window's top: clear of the system's rounded corners (R176)


class DayPicker(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("day-picker")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)     # one ground, the card's, as a menu
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
        self.setGridVisible(False)
        self._hovered = QModelIndex()
        self.day_view = self.findChild(QAbstractItemView, "qt_calendar_calendarview")
        self.day_viewport = self.day_view.viewport() if self.day_view is not None else None
        if self.day_view is not None:
            self.day_view.setMouseTracking(True)
            self.day_view.viewport().installEventFilter(self)
        month = self.findChild(QToolButton, "qt_calendar_monthbutton")
        if month is not None and month.menu() is not None:
            menu = month.menu()
            menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            menu.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
            menu.setStyleSheet(f"QMenu {{ border: 1px solid palette(mid); "
                              f"border-radius: {Radius.CARD}px; padding: {Space.XS}px; }}")
        self.setStyleSheet(f"QCalendarWidget#day-picker {{ border: 1px solid palette(mid); "
                          f"border-radius: {Radius.CARD}px; }}")
        for name, icon in (("qt_calendar_prevmonth", "chevron-left"), ("qt_calendar_nextmonth", "chevron-right")):
            button = self.findChild(QToolButton, name)
            if button is not None:
                button.setIcon(icons.icon(icon))
                button.setIconSize(QSize(Icon.CONTROL, Icon.CONTROL))
        # the bar of the month inside the little window's corners (R176, Daniel 26/10/2026: «la sua barra superiore
        # nella quale ci sono le frecce e mese e anno sfora un po' oltre i limiti, e rimane un po' tagliata in alto»):
        # it began at the window's very corner, under the system's rounding; a style sheet's padding does not reach
        # its layout, so the margins are set on it, its sides as the days' (the sheet's XS around them)
        bar = self.findChild(QWidget, "qt_calendar_navigationbar")
        if bar is not None and bar.layout() is not None:
            bar.layout().setContentsMargins(Space.XS, NAV_TOP, Space.XS, Space.XXS)
        self.restyle()

    def event(self, event) -> bool:
        if event.type() == QEvent.Type.ParentChange:
            popup = self.window()
            if popup is not self and popup.windowType() == Qt.WindowType.Popup:
                popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
                popup.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
                popup.setStyleSheet("QWidget#qt_datetimedit_calendar { background: transparent; border: none; }")
        return super().event(event)

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
        bar = self.findChild(QWidget, "qt_calendar_navigationbar")
        # Qt replaces the short year button by a spin box without relaying out the bar. The themed field
        # is taller (including its focus border), so reserve its whole slot before Qt swaps them.
        edit = self.findChild(QSpinBox, "qt_calendar_yearedit")
        year = self.findChild(QToolButton, "qt_calendar_yearbutton")
        if edit is not None and year is not None:
            edit.ensurePolished()
            height = max(Size.CONTROL, edit.sizeHint().height())
            year.setMinimumSize(max(year.minimumSizeHint().width(), edit.sizeHint().width()), height)
            if bar is not None:
                bar.setMinimumHeight(NAV_TOP + height + Space.XXS)
        header = NAV_TOP + max(Size.CHIP, bar.sizeHint().height() if bar is not None else 0) + Space.XXS
        self.setMinimumSize(QSize(7 * cell + 2 * Space.XS, header + Space.XS + 7 * Size.CHIP + 2 * Space.XS))

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in (event.Type.PaletteChange, event.Type.StyleChange, event.Type.FontChange):
            self.restyle()

    def paintCell(self, painter, rect, day: QDate) -> None:
        pal = self.palette()
        cell = QRectF(rect).adjusted(Space.XXS, Space.XXS, -Space.XXS, -Space.XXS)
        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        shown = day.month() == self.monthShown() and day.year() == self.yearShown()
        enabled = self.isEnabled() and self.minimumDate() <= day <= self.maximumDate()
        if day == self.selectedDate():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(pal.color(QPalette.ColorRole.Mid))
            painter.drawRoundedRect(cell, Radius.INNER, Radius.INNER)
        hovered = (self.day_view is not None and self._hovered.isValid()
                   and self.day_view.visualRect(self._hovered).center() == rect.center())
        if hovered and enabled:
            hover = pal.color(QPalette.ColorRole.Text)
            hover.setAlphaF(theme_colors.HOVER)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(hover)
            painter.drawRoundedRect(cell, Radius.INNER, Radius.INNER)
        if day == QDate.currentDate() and day != self.selectedDate():
            painter.setPen(QPen(pal.color(QPalette.ColorRole.Mid), Line.HAIR))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            half = Line.HAIR / 2
            painter.drawRoundedRect(cell.adjusted(half, half, -half, -half), Radius.INNER, Radius.INNER)
        painter.setPen(pal.color(QPalette.ColorGroup.Active if enabled else QPalette.ColorGroup.Disabled,
                                 QPalette.ColorRole.Text if shown else QPalette.ColorRole.PlaceholderText))
        painter.drawText(QRectF(rect), Qt.AlignmentFlag.AlignCenter, str(day.day()))
        painter.restore()

    def eventFilter(self, watched, event) -> bool:
        view = getattr(self, "day_view", None)
        if view is not None and watched is getattr(self, "day_viewport", None):
            kind = event.type()
            if kind in (QEvent.Type.MouseMove, QEvent.Type.Leave):
                index = view.indexAt(event.position().toPoint()) if kind == QEvent.Type.MouseMove else QModelIndex()
                if index != self._hovered:
                    previous, self._hovered = self._hovered, index
                    if previous.isValid():
                        view.viewport().update(view.visualRect(previous))
                    if index.isValid():
                        view.viewport().update(view.visualRect(index))
        return super().eventFilter(watched, event)
