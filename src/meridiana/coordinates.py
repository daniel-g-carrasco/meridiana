"""Read coordinates without Qt or network. Historical datums use the EPSG transformations
published in the CRS definitions; their result is WGS84 for Meridiana's site."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlsplit

WGS84_A = 6378137.0
WGS84_F = 1 / 298.257223563
INTL_A = 6378388.0
INTL_F = 1 / 297.0


class CoordinateError(ValueError):
    """The text is not an unambiguous point, with the reason in plain language."""


@dataclass(frozen=True)
class CoordinateReading:
    lat: float
    lon: float
    format: str
    datum: str = "WGS84"
    zone: str = ""
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _TM:
    a: float
    f: float

    def __post_init__(self):
        n = self.f / (2 - self.f)
        object.__setattr__(self, "n", n)
        object.__setattr__(self, "A", self.a / (1 + n) * (1 + n ** 2 / 4 + n ** 4 / 64))
        object.__setattr__(self, "alpha", (
            n / 2 - 2 * n ** 2 / 3 + 5 * n ** 3 / 16 + 41 * n ** 4 / 180,
            13 * n ** 2 / 48 - 3 * n ** 3 / 5 + 557 * n ** 4 / 1440,
            61 * n ** 3 / 240 - 103 * n ** 4 / 140,
            49561 * n ** 4 / 161280))
        object.__setattr__(self, "beta", (
            n / 2 - 2 * n ** 2 / 3 + 37 * n ** 3 / 96 - n ** 4 / 360,
            n ** 2 / 48 + n ** 3 / 15 - 437 * n ** 4 / 1440,
            17 * n ** 3 / 480 - 37 * n ** 4 / 840,
            4397 * n ** 4 / 161280))
        object.__setattr__(self, "delta", (
            2 * n - 2 * n ** 2 / 3 - 2 * n ** 3 + 116 * n ** 4 / 45,
            7 * n ** 2 / 3 - 8 * n ** 3 / 5 - 227 * n ** 4 / 45,
            56 * n ** 3 / 15 - 136 * n ** 4 / 35,
            4279 * n ** 4 / 630))

    def reverse(self, east: float, north: float, lon0: float, south: bool, k0: float,
                false_east: float) -> tuple[float, float]:
        xi = (north - (10_000_000.0 if south else 0.0)) / (k0 * self.A)
        eta = (east - false_east) / (k0 * self.A)
        xi_p = xi - sum(b * math.sin(2 * j * xi) * math.cosh(2 * j * eta)
                        for j, b in enumerate(self.beta, 1))
        eta_p = eta - sum(b * math.cos(2 * j * xi) * math.sinh(2 * j * eta)
                          for j, b in enumerate(self.beta, 1))
        chi = math.asin(math.sin(xi_p) / math.cosh(eta_p))
        phi = chi + sum(d * math.sin(2 * j * chi) for j, d in enumerate(self.delta, 1))
        return math.degrees(phi), lon0 + math.degrees(math.atan2(math.sinh(eta_p), math.cos(xi_p)))


WGS_TM = _TM(WGS84_A, WGS84_F)
INTL_TM = _TM(INTL_A, INTL_F)


def _to_ecef(lat: float, lon: float, a: float, f: float) -> tuple[float, float, float]:
    phi, lam = math.radians(lat), math.radians(lon)
    e2 = f * (2 - f)
    n = a / math.sqrt(1 - e2 * math.sin(phi) ** 2)
    return n * math.cos(phi) * math.cos(lam), n * math.cos(phi) * math.sin(lam), n * (1 - e2) * math.sin(phi)


def _from_ecef(x: float, y: float, z: float) -> tuple[float, float]:
    lon = math.atan2(y, x)
    p = math.hypot(x, y)
    lat = math.atan2(z, p * (1 - WGS84_F * (2 - WGS84_F)))
    e2 = WGS84_F * (2 - WGS84_F)
    h = 0.0
    for _ in range(8):
        n = WGS84_A / math.sqrt(1 - e2 * math.sin(lat) ** 2)
        h = p / math.cos(lat) - n if abs(lat) < math.radians(89.9) else abs(z) / math.sin(abs(lat)) - n * (1 - e2)
        lat = math.atan2(z, p * (1 - e2 * n / (n + h)))
    return math.degrees(lat), math.degrees(lon)


def _datum_to_wgs(lat: float, lon: float, datum: str) -> tuple[float, float]:
    if datum == "WGS84":
        return lat, lon
    x, y, z = _to_ecef(lat, lon, INTL_A, INTL_F)
    if datum == "ED50":
        return _from_ecef(x - 87.0, y - 98.0, z - 121.0)
    dx, dy, dz = -104.1, -49.1, -9.9
    rx, ry, rz = (math.radians(v / 3600) for v in (0.971, -2.917, 0.714))
    scale = 1 - 11.68e-6
    return _from_ecef(dx + scale * (x - rz * y + ry * z),
                      dy + scale * (y + rz * x - rx * z),
                      dz + scale * (z - ry * x + rx * y))


def _number(text: str) -> float:
    try:
        value = float(text.strip().replace(",", "."))
    except ValueError:
        raise CoordinateError(f"not a number: {text!r}") from None
    if not math.isfinite(value):
        raise CoordinateError("coordinates must be finite numbers")
    return value


def _decimal_pair(text: str) -> tuple[float, float]:
    text = text.strip()
    if ";" in text:
        parts = [part.strip().replace(",", ".") for part in text.split(";")]
    elif text.count(",") == 1:
        parts = [part.strip() for part in text.split(",")]
    else:
        parts = text.replace(",", ".").split()
    if len(parts) != 2:
        raise CoordinateError("write exactly two coordinates, latitude and longitude")
    lat, lon = (_number(part) for part in parts)
    if not -90 <= lat <= 90:
        raise CoordinateError("latitude must be between -90 and 90 degrees")
    if not -180 <= lon <= 180:
        raise CoordinateError("longitude must be between -180 and 180 degrees")
    return lat, lon


def _angles(text: str) -> CoordinateReading:
    if "°" not in text and "º" not in text:
        raise CoordinateError("not degrees and minutes")
    normalized = text.replace("º", "°").replace("’", "'").replace("′", "'").replace("″", '"')
    pattern = re.compile(
        r"([+-]?\d+(?:[.,]\d+)?)°\s*(?:(\d+(?:[.,]\d+)?)'\s*(?:(\d+(?:[.,]\d+)?)\"\s*)?)?([NSEW])",
        re.IGNORECASE)
    matches = list(pattern.finditer(normalized))
    rest = pattern.sub("", normalized).strip()
    if len(matches) != 2 or rest:
        if not re.search(r"[NSEW]", normalized, re.IGNORECASE):
            raise CoordinateError("declare the hemisphere N/S for latitude and E/W for longitude")
        raise CoordinateError("write two complete angles with their hemisphere")
    values = {}
    seconds_present = False
    for match in matches:
        degrees, minutes, seconds, hemisphere = match.groups()
        hemisphere = hemisphere.upper()
        axis = "lat" if hemisphere in "NS" else "lon"
        if axis in values:
            raise CoordinateError("one angle must be latitude and the other longitude")
        minute = _number(minutes or "0")
        second = _number(seconds or "0")
        seconds_present |= seconds is not None
        if not 0 <= minute < 60 or not 0 <= second < 60:
            raise CoordinateError("minutes and seconds must be smaller than 60")
        value = abs(_number(degrees)) + minute / 60 + second / 3600
        if hemisphere in "SW":
            value = -value
        values[axis] = value
    if not -90 <= values["lat"] <= 90 or not -180 <= values["lon"] <= 180:
        raise CoordinateError("latitude or longitude is outside its geographic limits")
    return CoordinateReading(values["lat"], values["lon"], "dms" if seconds_present else "ddm")


def _link(text: str) -> CoordinateReading:
    url = urlsplit(text)
    host = url.hostname or ""
    query = parse_qs(url.query)
    candidate = ""
    if "mlat" in query and "mlon" in query:
        candidate = query["mlat"][0] + "," + query["mlon"][0]
    else:
        for key in ("query", "q", "ll"):
            if key in query:
                candidate = query[key][0]
                break
    if not candidate and "@" in url.path:
        parts = url.path.split("@", 1)[1].split(",")
        if len(parts) >= 2:
            candidate = ",".join(parts[:2])
    if not candidate and "openstreetmap.org" in host and url.fragment.startswith("map="):
        parts = unquote(url.fragment[4:]).split("/")
        if len(parts) == 3:
            candidate = parts[1] + "," + parts[2]
    if not candidate:
        raise CoordinateError("the map link does not contain explicit coordinates")
    try:
        lat, lon = _decimal_pair(candidate)
    except CoordinateError:
        raise CoordinateError("the map link does not contain two readable coordinates") from None
    return CoordinateReading(lat, lon, "link")


def _projected(text: str) -> CoordinateReading:
    epsg = re.fullmatch(r"EPSG:(\d+)\s+(.+)", text, re.IGNORECASE)
    if epsg:
        code = int(epsg.group(1))
        values = epsg.group(2).replace(",", " ").split()
        if len(values) != 2:
            raise CoordinateError("write easting and northing after the EPSG code")
        east, north = (_number(value) for value in values)
        if 32601 <= code <= 32660 or 32701 <= code <= 32760:
            datum = "WGS84"
            zone = code % 100
            south = 32701 <= code <= 32760
            lon0, false_east, tm = (zone - 1) * 6 - 180 + 3, 500000.0, WGS_TM
        elif 23001 <= code <= 23060:
            datum, zone, south = "ED50", code % 100, False
            lon0, false_east, tm = (zone - 1) * 6 - 180 + 3, 500000.0, INTL_TM
        elif code in (3003, 3004):
            datum, zone, south = "Roma40", "Ovest" if code == 3003 else "Est", False
            lon0, false_east, tm = (9.0, 1500000.0, INTL_TM) if code == 3003 else (15.0, 2520000.0, INTL_TM)
        else:
            raise CoordinateError(f"EPSG:{code} is not a supported projected coordinate system")
        return _grid(east, north, datum, zone, south, lon0, false_east, tm, f"{zone}{'S' if south else 'N'}"
                     if code not in (3003, 3004) else zone)

    gauss = re.fullmatch(r"(?:Gauss[- ]?Boaga|GB)\s+(?:Roma40\s+)?(Ovest|Est|West|East)\s+(.+)", text, re.IGNORECASE)
    if gauss:
        values = gauss.group(2).replace(",", " ").split()
        if len(values) != 2:
            raise CoordinateError("write easting and northing for Gauss-Boaga")
        zone = gauss.group(1).capitalize()
        zone = {"West": "Ovest", "East": "Est"}.get(zone, zone)
        east, north = (_number(value) for value in values)
        lon0, false_east = (9.0, 1500000.0) if zone == "Ovest" else (15.0, 2520000.0)
        return _grid(east, north, "Roma40", zone, False, lon0, false_east, INTL_TM, zone)

    utm = re.fullmatch(r"(?:UTM\s+)?(?:(WGS84|ED50)\s+)?(\d{1,2})([NS])\s+(.+)", text, re.IGNORECASE)
    band = re.fullmatch(r"(\d{1,2})([C-HJ-NP-X])\s+(.+)", text, re.IGNORECASE)
    if utm and utm.group(1) is None:
        raise CoordinateError("declare the datum, WGS84 or ED50, before the UTM zone")
    if not utm and band:
        datum, zone_text, hemisphere, raw = "WGS84", band.group(1), band.group(2), band.group(3)
        south = hemisphere.upper() < "N"
    elif utm:
        datum, zone_text, hemisphere, raw = utm.groups()
        south = hemisphere.upper() == "S"
    else:
        raise CoordinateError("not a supported projected coordinate text")
    values = raw.replace(",", " ").split()
    if len(values) != 2:
        raise CoordinateError("write easting and northing after the UTM zone")
    zone = int(zone_text)
    if not 1 <= zone <= 60:
        raise CoordinateError("the UTM zone must be between 1 and 60")
    east, north = (_number(value) for value in values)
    datum = datum.upper()
    return _grid(east, north, datum, zone, south, (zone - 1) * 6 - 180 + 3, 500000.0,
                 WGS_TM if datum == "WGS84" else INTL_TM, f"{zone}{'S' if south else 'N'}")


def _grid(east: float, north: float, datum: str, zone: int | str, south: bool, lon0: float,
          false_east: float, tm: _TM, label: str) -> CoordinateReading:
    if not 0 <= east <= 3_500_000 or not 0 <= north <= 10_000_000:
        raise CoordinateError("easting or northing is outside the projection's plausible limits")
    lat, lon = tm.reverse(east, north, lon0, south, 0.9996, false_east)
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise CoordinateError("the projected coordinates do not give a geographic point")
    if datum != "Roma40" and not -80 <= lat <= 84:
        raise CoordinateError("UTM is defined between 80 degrees south and 84 degrees north")
    lat, lon = _datum_to_wgs(lat, lon, datum)
    warning = ("historical datum transformed with its EPSG parameters; verify the point on the map"
               if datum != "WGS84" else "")
    return CoordinateReading(lat, lon, "grid", datum, label, (warning,) if warning else ())


def read_coordinates(text: str) -> CoordinateReading:
    """Read decimal, DMS, degrees and decimal minutes, map links, UTM or Gauss-Boaga.
    Raise CoordinateError for an address, an ambiguous text or an impossible point."""
    text = text.strip()
    if not text:
        raise CoordinateError("write two coordinates")
    if re.match(r"https?://", text, re.IGNORECASE):
        return _link(text)
    if "°" in text or "º" in text:
        return _angles(text)
    if re.match(r"(?:EPSG:|Gauss[- ]?Boaga|GB\s|UTM\s|\d{1,2}[NSC-HJ-NP-X]\s)", text, re.IGNORECASE):
        return _projected(text)
    lat, lon = _decimal_pair(text)
    return CoordinateReading(lat, lon, "decimal")
