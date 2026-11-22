"""Where the sun is, and how far apart tilted rows must be so that they do not shade each other.

The position comes from the NOAA solar calculator (Meeus' low-precision algorithm): about 0.01 degrees
against NREL's SPA between 1800 and 2100, checked in tests/test_sun.py against values pvlib 0.16.1 gave.
Refraction follows the NOAA spreadsheet too. Times are UTC; "solar time" is true solar time, the one in
which the sun crosses the meridian at 12:00, which is how a design window ("no shade on 21 December
between 10 and 14") is usually stated.

Row spacing: CEI 82-25/3:2026 6.2 (Fig. 1) gives the limit angle alpha_L = atan(h/d) and, for a sun
direction at an angle gamma from the rows' normal, d' = d / cos(gamma). The design sun positions are the
designer's choice: the standards do not fix them, so the criterion is a parameter of the project.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone


@dataclass(frozen=True)
class SunPosition:
    elevation: float        # degrees above the horizon, geometric
    apparent: float         # with atmospheric refraction
    bearing: float          # degrees from North clockwise

    @property
    def azimuth(self) -> float:
        """The CEI 82-25 azimuth: from South, positive towards West."""
        a = (self.bearing - 180.0) % 360.0
        return a - 360.0 if a > 180.0 else a


def _julian_century(when: datetime) -> float:
    if when.tzinfo is None:
        raise ValueError("a time without a time zone: give UTC")
    jd = 2440587.5 + when.timestamp() / 86400.0
    return (jd - 2451545.0) / 36525.0


def _sun_terms(jc: float) -> tuple[float, float]:
    """Declination (degrees) and equation of time (minutes) for a Julian century."""
    l0 = (280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360.0
    m = 357.52911 + jc * (35999.05029 - 0.0001537 * jc)
    e = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)
    mr = math.radians(m)
    c = (math.sin(mr) * (1.914602 - jc * (0.004817 + 0.000014 * jc))
         + math.sin(2 * mr) * (0.019993 - 0.000101 * jc) + math.sin(3 * mr) * 0.000289)
    omega = math.radians(125.04 - 1934.136 * jc)
    app_long = l0 + c - 0.00569 - 0.00478 * math.sin(omega)
    mean_obliq = 23 + (26 + (21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813))) / 60) / 60
    obliq = mean_obliq + 0.00256 * math.cos(omega)
    decl = math.degrees(math.asin(math.sin(math.radians(obliq)) * math.sin(math.radians(app_long))))
    y = math.tan(math.radians(obliq / 2)) ** 2
    l0r = math.radians(l0)
    eqt = 4 * math.degrees(y * math.sin(2 * l0r) - 2 * e * math.sin(mr) + 4 * e * y * math.sin(mr) * math.cos(2 * l0r)
                           - 0.5 * y * y * math.sin(4 * l0r) - 1.25 * e * e * math.sin(2 * mr))
    return decl, eqt


def _refraction(elev: float) -> float:
    if elev > 85.0:
        return 0.0
    t = math.tan(math.radians(elev))
    if elev > 5.0:
        r = 58.1 / t - 0.07 / t ** 3 + 0.000086 / t ** 5
    elif elev > -0.575:
        r = 1735 + elev * (-518.2 + elev * (103.4 + elev * (-12.79 + elev * 0.711)))
    else:
        r = -20.772 / t
    return r / 3600.0


def position(lat: float, lon: float, when: datetime) -> SunPosition:
    decl, eqt = _sun_terms(_julian_century(when))
    utc = when.astimezone(timezone.utc)
    minutes = utc.hour * 60 + utc.minute + utc.second / 60 + utc.microsecond / 6e7
    tst = (minutes + eqt + 4 * lon) % 1440.0
    ha = tst / 4 + 180 if tst / 4 < 0 else tst / 4 - 180
    phi, dr, har = math.radians(lat), math.radians(decl), math.radians(ha)
    cos_z = math.sin(phi) * math.sin(dr) + math.cos(phi) * math.cos(dr) * math.cos(har)
    zen = math.degrees(math.acos(max(-1.0, min(1.0, cos_z))))
    elev = 90.0 - zen
    denom = math.cos(phi) * math.sin(math.radians(zen))
    if abs(denom) < 1e-12:
        bearing = 180.0 if lat > decl else 0.0
    else:
        x = max(-1.0, min(1.0, (math.sin(phi) * math.cos(math.radians(zen)) - math.sin(dr)) / denom))
        a = math.degrees(math.acos(x))
        bearing = (a + 180.0) % 360.0 if ha > 0 else (540.0 - a) % 360.0
    return SunPosition(elevation=elev, apparent=elev + _refraction(elev), bearing=bearing)


def utc_at_solar_time(lon: float, day: date, solar_hours: float) -> datetime:
    """The UTC instant at which true solar time is `solar_hours` on `day` at longitude `lon`."""
    base = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    guess = base + timedelta(hours=solar_hours)
    for _ in range(2):          # the equation of time barely moves within the day
        _decl, eqt = _sun_terms(_julian_century(guess))
        guess = base + timedelta(minutes=solar_hours * 60 - eqt - 4 * lon)
    return guess


@dataclass(frozen=True)
class DesignWindow:
    """No inter-row shade on `day` between two solar times: the usual way to choose the row pitch."""
    month: int = 12
    day: int = 21
    start: float = 10.0
    end: float = 14.0
    step_minutes: int = 10

    def positions(self, lat: float, lon: float, year: int = 2026) -> list[SunPosition]:
        d = date(year, self.month, self.day)
        out = []
        t = self.start
        while t <= self.end + 1e-9:
            out.append(position(lat, lon, utc_at_solar_time(lon, d, t)))
            t += self.step_minutes / 60
        return out


def row_clearance(rise: float, facing_bearing: float, positions: list[SunPosition]) -> float:
    """Plan clearance needed behind a row whose top edge stands `rise` metres above its front edge, so that
    its shadow does not reach the next row for any of `positions` (CEI 82-25/3 6.2: d' = d / cos gamma).
    The rows face `facing_bearing`; a sun behind them throws the shadow forward and needs nothing."""
    gap = 0.0
    for p in positions:
        if p.elevation <= 0.5:
            continue
        cos_g = math.cos(math.radians(p.bearing - facing_bearing))
        if cos_g <= 0:
            continue
        gap = max(gap, rise / math.tan(math.radians(p.elevation)) * cos_g)
    return gap


def limit_angle(rise: float, clearance: float) -> float:
    """The limit angle alpha_L = atan(h / d) of CEI 82-25/3 Fig. 1, in degrees, for a clearance d."""
    return 90.0 if clearance <= 0 else math.degrees(math.atan(rise / clearance))


def noon_elevation(lat: float, lon: float, day: date) -> float:
    return position(lat, lon, utc_at_solar_time(lon, day, 12.0)).elevation


def sun_path(lat: float, lon: float, day: date, step_minutes: int = 15) -> list[tuple[float, SunPosition]]:
    """(solar hour, position) from 0 to 24 h solar time on `day`, above the horizon only."""
    out = []
    minutes = 0
    while minutes <= 1440:
        h = minutes / 60
        p = position(lat, lon, utc_at_solar_time(lon, day, h))
        if p.elevation > 0:
            out.append((h, p))
        minutes += step_minutes
    return out
