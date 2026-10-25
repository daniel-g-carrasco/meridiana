"""The sun of the 3D view: a day and an hour on the site's clock, where the sun is, and the day played in a few
seconds to watch the shadows move over the modules (as PVsyst's shadow animation and Aurora's sun slider do). It
starts on the design day of the project at solar noon, the sun the row pitch is computed with. One row, as the
mockups (the target of 24/10/2026): the height and the azimuth short beside the hour, the whole sentence in their
tooltip."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from PySide6.QtCore import QDate, QLocale, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QDateEdit, QHBoxLayout, QLabel, QSizePolicy, QSlider, QToolButton, QWidget

from .. import sun
from ..i18n import _, number
from . import icons
from .day_picker import DayPicker
from .design import Line, Size

CLOCK = ZoneInfo("Europe/Rome")      # the site's clock: the program works on Italian sites
YEAR = 2026
STEP = 10                            # minutes per step of the slider and of the animation
DAY_FRAME_MS = 80


class SteadyLabel(QLabel):
    """A label as wide as the widest of its texts (`widest`), shortened with «…» when the bar is narrower: the slider
    beside it keeps its width while the text changes (R96)."""

    def __init__(self, widest: list[str], parent=None):
        super().__init__(parent)
        self.widest = widest

    def sizeHint(self) -> QSize:
        m = self.fontMetrics()
        return QSize(max(m.horizontalAdvance(t) for t in self.widest) + 4, super().sizeHint().height())

    def minimumSizeHint(self) -> QSize:
        return QSize(0, super().minimumSizeHint().height())

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setPen(self.palette().color(self.foregroundRole()))
        text = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, self.width())
        p.drawText(self.rect(), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), text)


class SunBar(QWidget):
    sunChanged = Signal(float, float)          # elevation (apparent), bearing

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lat: float | None = None
        self.lon: float | None = None
        self.design_window = sun.DesignWindow()
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 3, 8, 3)
        row.setSpacing(8)
        self.play = QToolButton()
        self.play.setCheckable(True)
        self.play.setIcon(icons.icon("play"))
        self.play.setToolTip(_("Play the day: the sun from dawn to sunset, ten minutes a step"))
        self.play.toggled.connect(self._toggle)
        self.day = QDateEdit(QDate(YEAR, 12, 21))
        self.day.setDisplayFormat("d MMM")
        self.day.setCalendarPopup(True)
        # as wide as its longest day (R103: «21 dic» was cut), the arrow's room and the text's insets with it
        locale = self.day.locale()
        longest = max(self.day.fontMetrics().horizontalAdvance(f"28 {locale.monthName(m, QLocale.FormatType.ShortFormat)}")
                      for m in range(1, 13))
        self.day.setMinimumWidth(longest + 2 * Line.TEXT_INSET + Size.COMPACT + 4)
        self.day.setCalendarWidget(DayPicker())         # the month in the theme (ui/day_picker.py)
        self.day.setToolTip(_("The day of the year"))
        self.day.dateChanged.connect(lambda _d: self._update())
        self.hour = QSlider(Qt.Orientation.Horizontal)
        self.hour.setRange(0, 24 * 60 // STEP - 1)
        self.hour.setPageStep(60 // STEP)
        self.hour.setToolTip(_("The hour on the site's clock"))
        self.hour.valueChanged.connect(lambda _v: self._update())
        self.hour.setMinimumWidth(80)
        self.clock = QLabel()
        self.clock.setFixedWidth(self.clock.fontMetrics().horizontalAdvance("00:00") + 4)
        # «h 21,1° · az −0,5°», the sentence in its tooltip: always as wide as its widest, shortened when the 3D view
        # is narrow (the plan beside it keeps its room)
        self.short = SteadyLabel([_("h {elevation}° · az {azimuth}°").format(elevation="88,8", azimuth="-188,8"),
                                  _("sun below the horizon")])
        self.short.setObjectName("sun-short")
        self.short.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.design = QToolButton()
        self.design.setAutoRaise(True)
        self.design.setText(_("Design day"))
        self.design.setIcon(icons.icon("sun"))
        self.design.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.design.setToolTip(_("Design day") + ": " + _("Back to the day and the solar noon the row pitch is computed with"))
        self.design.clicked.connect(self.to_design_day)
        row.addWidget(self.play)
        row.addWidget(self.day)
        row.addWidget(self.hour, 1)
        row.addWidget(self.clock)
        row.addWidget(self.short)
        row.addWidget(self.design)
        self.words = QLabel(self)               # the whole sentence, for the tooltip (and a reader of the screen)
        self.words.hide()
        self.timer = QTimer(self)
        self.timer.setInterval(DAY_FRAME_MS)
        self.timer.timeout.connect(self._tick)

    # the site and the design day

    def set_site(self, lat: float, lon: float, window: dict | None = None) -> None:
        """A new site (a project opened) starts on its design day; the same site keeps the hour chosen."""
        if window:
            self.design_window = sun.DesignWindow(**window)
        if (lat, lon) != (self.lat, self.lon):
            self.lat, self.lon = lat, lon
            self.to_design_day()

    def to_design_day(self) -> None:
        if self.lon is None:
            return
        d = date(YEAR, self.design_window.month, self.design_window.day)
        noon = sun.utc_at_solar_time(self.lon, d, 12.0).astimezone(CLOCK)
        self.day.blockSignals(True)
        self.day.setDate(QDate(YEAR, self.design_window.month, self.design_window.day))
        self.day.blockSignals(False)
        self.hour.setValue(round((noon.hour * 60 + noon.minute) / STEP))
        self._update()

    # the sun

    def when(self) -> datetime:
        d = self.day.date()
        local = datetime(YEAR, d.month(), d.day(), tzinfo=CLOCK) + timedelta(minutes=self.hour.value() * STEP)
        return local.astimezone(timezone.utc)

    def position(self) -> sun.SunPosition | None:
        if self.lat is None:
            return None
        return sun.position(self.lat, self.lon, self.when())

    def _update(self) -> None:
        pos = self.position()
        local = self.when().astimezone(CLOCK)
        self.clock.setText(local.strftime("%H:%M"))
        if pos is None:
            return
        legal = _("summer time") if local.dst() else _("standard time")
        if pos.apparent <= 0:
            self.words.setText(_("At {time} ({clock}) the sun is below the horizon.").format(
                time=local.strftime("%H:%M"), clock=legal))
            self.short.setText(_("sun below the horizon"))
        else:
            self.words.setText(_("At {time} ({clock}) the sun is {elevation}° above the horizon, azimuth {azimuth}° "
                                 "(from South, + West).").format(
                time=local.strftime("%H:%M"), clock=legal, elevation=number(pos.apparent, 1),
                azimuth=number(pos.azimuth, 1, sign=True)))
            self.short.setText(_("h {elevation}° · az {azimuth}°").format(
                elevation=number(pos.apparent, 1), azimuth=number(pos.azimuth, 1, sign=True)))
        self.short.setToolTip(self.words.text())
        self.sunChanged.emit(pos.apparent, pos.bearing)

    # the day played

    def _toggle(self, on: bool) -> None:
        self.play.setIcon(icons.icon("pause" if on else "play"))
        if on:
            pos = self.position()
            if pos is not None and pos.apparent <= 0:
                self._to_dawn(0)
            self.timer.start()
        else:
            self.timer.stop()

    def _tick(self) -> None:
        nxt = self.hour.value() + 1
        if nxt > self.hour.maximum():
            nxt = 0
        self.hour.setValue(nxt)
        pos = self.position()
        if pos is not None and pos.apparent <= 0:
            self._to_dawn(0)

    def _to_dawn(self, start: int) -> None:
        """The first step of the day, from `start`, with the sun up: after sunset the day starts again."""
        for k in range(start, self.hour.maximum() + 1):
            self.hour.blockSignals(True)
            self.hour.setValue(k)
            self.hour.blockSignals(False)
            pos = self.position()
            if pos is not None and pos.apparent > 0:
                break
        self._update()
