"""Natural Earth's small offline world map: countries, borders and label anchors, without Qt or network."""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from functools import cache

from . import paths

DATA = "natural_earth", "ne_110m_admin_0_countries.geojson.gz"
DECLARED_BYTES = 209310


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
