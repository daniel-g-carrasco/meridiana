"""Coordinates and angles.

The model lives in a local frame: metres East (x) and North (y) on the plane tangent to the WGS84 ellipsoid
at the site origin, heights in metres above the ground (z). The projection is orthographic through ECEF:
over the few kilometres of a site the error stays below a millimetre, where the usual equirectangular
shortcut (one cosine for the whole site, a mean Earth radius) is off by 0.3% East-West at 45 degrees.

Angles follow CEI 82-25/1:2026, 3.2.1.5-6, the same as PVGIS ("aspect"): tilt beta from the horizontal;
azimuth alpha from South, negative towards East, positive towards West. A bearing, the direction of a line
on the plan, is measured from North clockwise, as a compass reads it. Web Mercator (EPSG:3857) is only
for map tiles.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

WGS84_A = 6378137.0
WGS84_F = 1 / 298.257223563
WGS84_E2 = WGS84_F * (2 - WGS84_F)
MERCATOR_R = 6378137.0
MERCATOR_MAX_LAT = 85.0511287798066


def geodetic_to_ecef(lat: float, lon: float, h: float = 0.0) -> tuple[float, float, float]:
    phi, lam = math.radians(lat), math.radians(lon)
    n = WGS84_A / math.sqrt(1 - WGS84_E2 * math.sin(phi) ** 2)
    return ((n + h) * math.cos(phi) * math.cos(lam),
            (n + h) * math.cos(phi) * math.sin(lam),
            (n * (1 - WGS84_E2) + h) * math.sin(phi))


def ecef_to_geodetic(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Latitude and longitude in degrees, height in metres (iterated to below a micrometre)."""
    lon = math.atan2(y, x)
    p = math.hypot(x, y)
    lat = math.atan2(z, p * (1 - WGS84_E2))
    h = 0.0
    for _ in range(8):
        n = WGS84_A / math.sqrt(1 - WGS84_E2 * math.sin(lat) ** 2)
        h = p / math.cos(lat) - n if abs(lat) < math.radians(89.9) else abs(z) / math.sin(abs(lat)) - n * (1 - WGS84_E2)
        lat = math.atan2(z, p * (1 - WGS84_E2 * n / (n + h)))
    return math.degrees(lat), math.degrees(lon), h


@dataclass(frozen=True)
class Origin:
    """The site origin: where the local frame touches the ellipsoid."""
    lat: float
    lon: float

    def _basis(self):
        phi, lam = math.radians(self.lat), math.radians(self.lon)
        east = (-math.sin(lam), math.cos(lam), 0.0)
        north = (-math.sin(phi) * math.cos(lam), -math.sin(phi) * math.sin(lam), math.cos(phi))
        up = (math.cos(phi) * math.cos(lam), math.cos(phi) * math.sin(lam), math.sin(phi))
        return east, north, up

    def to_local(self, lon: float, lat: float) -> tuple[float, float]:
        """A ground point (height 0 on the ellipsoid) to metres East and North of the origin."""
        ox, oy, oz = geodetic_to_ecef(self.lat, self.lon)
        px, py, pz = geodetic_to_ecef(lat, lon)
        d = (px - ox, py - oy, pz - oz)
        east, north, _up = self._basis()
        return (sum(a * b for a, b in zip(d, east, strict=True)), sum(a * b for a, b in zip(d, north, strict=True)))

    def to_lonlat(self, x: float, y: float) -> tuple[float, float]:
        """Back from the plane to the ground point under it: the height along the local vertical is found
        so that the point lies on the ellipsoid (a few iterations reach a micrometre)."""
        ox, oy, oz = geodetic_to_ecef(self.lat, self.lon)
        east, north, up = self._basis()
        u = -(x * x + y * y) / (2 * WGS84_A)
        lat = lon = 0.0
        for _ in range(4):
            px = ox + x * east[0] + y * north[0] + u * up[0]
            py = oy + x * east[1] + y * north[1] + u * up[1]
            pz = oz + x * east[2] + y * north[2] + u * up[2]
            lat, lon, h = ecef_to_geodetic(px, py, pz)
            u -= h
        return lon, lat

    def ring_to_local(self, ring) -> list[tuple[float, float]]:
        return [self.to_local(lon, lat) for lon, lat in ring]

    def ring_to_lonlat(self, ring) -> list[tuple[float, float]]:
        return [self.to_lonlat(x, y) for x, y in ring]


def bearing(dx: float, dy: float) -> float:
    """Direction of a plan vector, degrees from North clockwise, in [0, 360)."""
    return math.degrees(math.atan2(dx, dy)) % 360.0


def bearing_to_azimuth(b: float) -> float:
    """Compass bearing to the CEI 82-25 azimuth: from South, positive towards West, in (-180, 180]."""
    a = (b - 180.0) % 360.0
    return a - 360.0 if a > 180.0 else a


def azimuth_to_bearing(alpha: float) -> float:
    return (alpha + 180.0) % 360.0


def facing_vector(alpha: float) -> tuple[float, float]:
    """Unit plan vector a surface with azimuth alpha faces (East, North)."""
    b = math.radians(azimuth_to_bearing(alpha))
    return math.sin(b), math.cos(b)


# UTM on WGS84 (and on GRS80, the same within a millimetre): the IFC files' map conversions (ifc_export, ifc_import).
# Krüger's series to n^4, as in Karney (2011), «Transverse Mercator with an accuracy of a few nanometres», eq. 35-36:
# well below a millimetre within a zone.

UTM_K0 = 0.9996
_N = WGS84_F / (2 - WGS84_F)
_A = WGS84_A / (1 + _N) * (1 + _N ** 2 / 4 + _N ** 4 / 64)
_ALPHA = (_N / 2 - 2 * _N ** 2 / 3 + 5 * _N ** 3 / 16 + 41 * _N ** 4 / 180,
          13 * _N ** 2 / 48 - 3 * _N ** 3 / 5 + 557 * _N ** 4 / 1440,
          61 * _N ** 3 / 240 - 103 * _N ** 4 / 140,
          49561 * _N ** 4 / 161280)
_BETA = (_N / 2 - 2 * _N ** 2 / 3 + 37 * _N ** 3 / 96 - _N ** 4 / 360,
         _N ** 2 / 48 + _N ** 3 / 15 - 437 * _N ** 4 / 1440,
         17 * _N ** 3 / 480 - 37 * _N ** 4 / 840,
         4397 * _N ** 4 / 161280)
_DELTA = (2 * _N - 2 * _N ** 2 / 3 - 2 * _N ** 3 + 116 * _N ** 4 / 45,
          7 * _N ** 2 / 3 - 8 * _N ** 3 / 5 - 227 * _N ** 4 / 45,
          56 * _N ** 3 / 15 - 136 * _N ** 4 / 35,
          4279 * _N ** 4 / 630)


def utm_zone(lon: float) -> int:
    return min(60, int((lon + 180.0) // 6) + 1)


def to_utm(lat: float, lon: float, zone: int | None = None) -> tuple[int, float, float, float, float]:
    """WGS84 to UTM: (zone, East, North, convergence in degrees, scale factor). North has the false northing of 10 000
    km south of the equator. The convergence is the angle the true north is turned, counter-clockwise, from the grid's
    north (positive east of the central meridian in the northern hemisphere)."""
    zone = zone or utm_zone(lon)
    lam0 = math.radians((zone - 1) * 6 - 180 + 3)
    phi, lam = math.radians(lat), math.radians(lon) - lam0
    e = 2 * math.sqrt(_N) / (1 + _N)
    t = math.sinh(math.atanh(math.sin(phi)) - e * math.atanh(e * math.sin(phi)))
    xi_p = math.atan2(t, math.cos(lam))
    eta_p = math.atanh(math.sin(lam) / math.sqrt(1 + t * t))
    xi = xi_p + sum(a * math.sin(2 * j * xi_p) * math.cosh(2 * j * eta_p) for j, a in enumerate(_ALPHA, 1))
    eta = eta_p + sum(a * math.cos(2 * j * xi_p) * math.sinh(2 * j * eta_p) for j, a in enumerate(_ALPHA, 1))
    east = 500000.0 + UTM_K0 * _A * eta
    north = UTM_K0 * _A * xi + (10_000_000.0 if lat < 0 else 0.0)
    sigma = 1 + sum(2 * j * a * math.cos(2 * j * xi_p) * math.cosh(2 * j * eta_p) for j, a in enumerate(_ALPHA, 1))
    tau = sum(2 * j * a * math.sin(2 * j * xi_p) * math.sinh(2 * j * eta_p) for j, a in enumerate(_ALPHA, 1))
    gamma = math.atan2(tau * math.sqrt(1 + t * t) + sigma * t * math.tan(lam),
                       sigma * math.sqrt(1 + t * t) - tau * t * math.tan(lam))
    k = (UTM_K0 * _A / WGS84_A) * math.sqrt((1 + ((1 - _N) / (1 + _N) * math.tan(phi)) ** 2) * (sigma ** 2 + tau ** 2)
                                            / (t * t + math.cos(lam) ** 2))
    return zone, east, north, math.degrees(gamma), k


def from_utm(zone: int, east: float, north: float, south: bool = False) -> tuple[float, float]:
    """UTM to WGS84: (latitude, longitude) in degrees."""
    xi = (north - (10_000_000.0 if south else 0.0)) / (UTM_K0 * _A)
    eta = (east - 500000.0) / (UTM_K0 * _A)
    xi_p = xi - sum(b * math.sin(2 * j * xi) * math.cosh(2 * j * eta) for j, b in enumerate(_BETA, 1))
    eta_p = eta - sum(b * math.cos(2 * j * xi) * math.sinh(2 * j * eta) for j, b in enumerate(_BETA, 1))
    chi = math.asin(math.sin(xi_p) / math.cosh(eta_p))
    phi = chi + sum(d * math.sin(2 * j * chi) for j, d in enumerate(_DELTA, 1))
    lam0 = (zone - 1) * 6 - 180 + 3
    return math.degrees(phi), lam0 + math.degrees(math.atan2(math.sinh(eta_p), math.cos(xi_p)))


def utm_of_crs(name: str) -> tuple[int, bool] | None:
    """The UTM zone and hemisphere of a coordinate system named «EPSG:n», when it is a UTM one on a datum that is
    WGS84 within a metre (WGS84, ETRS89, RDN2008, IGM95); None for the others (Gauss-Boaga, ED50 and the national
    grids need a change of datum: the file's latitude and longitude are used instead)."""
    digits = "".join(ch for ch in str(name).rsplit(":", 1)[-1] if ch.isdigit())
    if not digits:
        return None
    code = int(digits)
    if 32601 <= code <= 32660:
        return code - 32600, False
    if 32701 <= code <= 32760:
        return code - 32700, True
    if 25828 <= code <= 25838:                  # ETRS89 / UTM zone 28N-38N
        return code - 25800, False
    if code in (6707, 6708, 6709):              # RDN2008 / UTM zone 32N-34N (N-E)
        return code - 6675, False
    if code in (7791, 7792, 7793):              # RDN2008 / UTM zone 32N-34N
        return code - 7759, False
    if code in (3064, 3065):                    # IGM95 / UTM zone 32N, 33N
        return code - 3032, False
    return None


# Web Mercator, for the map tiles only.

def lonlat_to_mercator(lon: float, lat: float) -> tuple[float, float]:
    lat = max(-MERCATOR_MAX_LAT, min(MERCATOR_MAX_LAT, lat))
    return (math.radians(lon) * MERCATOR_R,
            math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * MERCATOR_R)


def mercator_to_lonlat(mx: float, my: float) -> tuple[float, float]:
    return (math.degrees(mx / MERCATOR_R),
            math.degrees(2 * math.atan(math.exp(my / MERCATOR_R)) - math.pi / 2))


def tile_of(lon: float, lat: float, zoom: int) -> tuple[int, int]:
    """The XYZ tile (x from the antimeridian, y from the top) that contains a point."""
    n = 2 ** zoom
    lat = max(-MERCATOR_MAX_LAT, min(MERCATOR_MAX_LAT, lat))
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return min(max(x, 0), n - 1), min(max(y, 0), n - 1)


def tile_bounds(x: int, y: int, zoom: int) -> tuple[float, float, float, float]:
    """West, South, East, North of an XYZ tile, in Web Mercator metres."""
    size = 2 * math.pi * MERCATOR_R / 2 ** zoom
    west = -math.pi * MERCATOR_R + x * size
    north = math.pi * MERCATOR_R - y * size
    return west, north - size, west + size, north


def parse_coordinates(text: str) -> tuple[float, float] | None:
    """Latitude and longitude typed or pasted in decimal degrees: "45.5226, 9.0300" as maps copy them,
    "45,5226; 9,0300" as an Italian writes them (the semicolon separates when the comma is decimal), or
    with a space between them. None when the text is not two numbers in range (then it is an address)."""
    text = text.strip()
    if ";" in text:
        parts = [part.strip().replace(",", ".") for part in text.split(";")]
    elif text.count(",") == 1:
        parts = [part.strip() for part in text.split(",")]
    else:
        parts = text.replace(",", ".").split()
    if len(parts) != 2:
        return None
    try:
        lat, lon = float(parts[0]), float(parts[1])
    except ValueError:
        return None
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon
