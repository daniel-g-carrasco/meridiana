"""Natural Earth's small offline world map: countries, borders and label anchors, without Qt or network."""

from __future__ import annotations

import gzip
import json
import math
from dataclasses import dataclass
from functools import cache

from . import paths

DATA = "natural_earth", "ne_110m_admin_0_countries.geojson.gz"
DECLARED_BYTES = 209310
EQUAL_EARTH_RADIUS = 6_371_007.2
A1, A2, A3, A4 = 1.340264, -0.081106, 0.000893, 0.003796


def _parallel(phi: float) -> tuple[float, float]:
    theta = math.asin(math.sqrt(3) * math.sin(phi) / 2)
    return theta, theta * (A1 + A2 * theta ** 2 + A3 * theta ** 6 + A4 * theta ** 8)


def equal_earth(lon: float, lat: float, central_lon: float = 0.0, origin_lat: float = 0.0) -> tuple[float, float]:
    """Metres east and north in the Equal Earth projection, centred on the site's meridian and latitude.

    The coefficients and equations are Šavrič, Patterson and Jenny's (2018), also used by PROJ's eqearth.
    """
    difference = lon - central_lon
    relative = (difference + 180) % 360 - 180
    if relative == -180 and difference > 0:
        relative = 180
    lam, phi = math.radians(relative), math.radians(lat)
    theta, y = _parallel(phi)
    denominator = A1 + 3 * A2 * theta ** 2 + 7 * A3 * theta ** 6 + 9 * A4 * theta ** 8
    x = 2 * math.sqrt(3) * lam * math.cos(theta) / (3 * denominator)
    return x * EQUAL_EARTH_RADIUS, (y - _parallel(math.radians(origin_lat))[1]) * EQUAL_EARTH_RADIUS


def from_equal_earth(x: float, y: float, central_lon: float = 0.0, origin_lat: float = 0.0) -> tuple[float, float]:
    """Longitude and latitude of a map point; reject clicks outside the projected globe."""
    target = y / EQUAL_EARTH_RADIUS + _parallel(math.radians(origin_lat))[1]
    theta = target / A1
    for _ in range(12):
        derivative = A1 + 3 * A2 * theta ** 2 + 7 * A3 * theta ** 6 + 9 * A4 * theta ** 8
        step = (theta * (A1 + A2 * theta ** 2 + A3 * theta ** 6 + A4 * theta ** 8) - target) / derivative
        theta -= step
        if abs(step) < 1e-12:
            break
    sine = 2 * math.sin(theta) / math.sqrt(3)
    if abs(theta) > math.pi / 3 + 1e-10 or abs(sine) > 1 + 1e-10:
        raise ValueError("outside the Equal Earth map")
    lat = math.degrees(math.asin(max(-1.0, min(1.0, sine))))
    derivative = A1 + 3 * A2 * theta ** 2 + 7 * A3 * theta ** 6 + 9 * A4 * theta ** 8
    relative = math.degrees(3 * x * derivative / (2 * math.sqrt(3) * EQUAL_EARTH_RADIUS * math.cos(theta)))
    if abs(relative) > 180 + 1e-8:
        raise ValueError("outside the Equal Earth map")
    return (relative + central_lon + 180) % 360 - 180, lat


@dataclass(frozen=True)
class Country:
    name: str
    italian_name: str
    polygons: tuple
    label: tuple[float, float]
    label_rank: float


@cache
def countries() -> tuple[Country, ...]:
    path = paths.shipped(*DATA)
    if path is None:
        raise FileNotFoundError("Natural Earth 1:110m countries are missing from the package")
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        document = json.load(stream)
    out = []
    for feature in document["features"]:
        properties = feature["properties"]
        geometry = feature["geometry"]
        polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
        shapes = []
        for polygon in polygons:
            shapes.append(tuple(tuple(tuple(point) for point in ring) for ring in polygon))
        label = (properties["LABEL_X"], properties["LABEL_Y"])
        out.append(Country(properties["NAME_EN"], properties.get("NAME_IT") or properties["NAME_EN"],
                           shapes, label, properties["LABELRANK"]))
    return tuple(out)


def _inside(ring, lon: float, lat: float) -> bool:
    inside = False
    previous = ring[-1]
    for point in ring:
        (x0, y0), (x1, y1) = previous, point
        if (y0 > lat) != (y1 > lat) and lon < (x1 - x0) * (lat - y0) / (y1 - y0) + x0:
            inside = not inside
        previous = point
    return inside


def country_at(lon: float, lat: float) -> str:
    """The English country name at a known geographic point, or an empty string over the ocean."""
    for country in countries():
        for polygon in country.polygons:
            if _inside(polygon[0], lon, lat) and not any(_inside(hole, lon, lat) for hole in polygon[1:]):
                return country.name
    return ""
