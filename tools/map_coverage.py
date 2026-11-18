#!/usr/bin/env python3
"""Rebuild src/meridiana/mapcoverage.py, the outlines of the areas the map sources cover (tiles.py, R36).

  python tools/map_coverage.py FOLDER          FOLDER holds the three files of Natural Earth below

The outlines come from Natural Earth 1:10m, public domain (https://www.naturalearthdata.com/about/terms-of-use/),
in its GeoJSON copy at https://github.com/nvkelso/natural-earth-vector/tree/master/geojson:
ne_10m_admin_0_countries.geojson (the countries), ne_10m_admin_1_states_provinces.geojson (the Italian provinces
and regions, the Belgian provinces, the German Länder) and ne_10m_minor_islands.geojson (the small islands the
countries leave out, Capri and Procida among them: each goes with the nearest country and province within 30 km).
Natural Earth draws the borders to a few hundred metres (the centre of Gorizia falls 700 m inside Slovenia): in a town
on a border the automatic choice can take the neighbour's source, and the menu offers both.

Each area is the union of its pieces, simplified to about 800 m, then pushed about 2 km out over the sea but never
into the land of another country or province (SEA): a harbour, a lagoon or a pier stays inside its own country,
while a land border stays where it is (a source is offered a few kilometres past it, tiles.MARGIN_KM, and the
choice of the best source prefers the one whose area holds the site). The pieces smaller than about 2 km² are left
out. The rings are written in Google's encoded polyline format with three decimals (about 100 m), some 70 KB for
every area together.

The areas are named here (AREAS) and by the sources of tiles.py (Source.area); a new area is a new entry here and a
run of this script. The file written is generated: do not edit it by hand."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "meridiana" / "mapcoverage.py"
PRECISION = 1000                      # three decimals of a degree
TOLERANCE = 0.008                     # the simplification, in degrees (about 800 m of latitude)
SEA = 0.02                            # how far over the sea an area reaches, in degrees (about 2 km)
SMALLEST = 0.0002                     # pieces below this, in square degrees (about 2 km²), are left out
ISLANDS = 0.3                         # a small island goes with the country nearest to it within this (about 30 km)

# area -> what it is made of: countries by Natural Earth's ADM0_A3, provinces and states by ISO 3166-2, regions as
# (country, region); "within" keeps only the pieces inside a box (W, S, E, N), for a source that covers part of a
# country (mainland Portugal, the European Netherlands)
AREAS = {
    "it": {"countries": ["ITA", "SMR", "VAT"]},
    "it-bz": {"provinces": ["IT-BZ"]},
    "it-tn": {"provinces": ["IT-TN"]},
    "it-toscana": {"regions": [("ITA", "Toscana")]},
    "it-fvg": {"regions": [("ITA", "Friuli-Venezia Giulia")]},
    "fr": {"countries": ["FRA"]},
    "es": {"countries": ["ESP"]},
    "pt": {"countries": ["PRT"], "within": (-10.0, 36.5, -6.0, 42.5)},
    "nl": {"countries": ["NLD"], "within": (2.5, 50.5, 7.5, 54.0)},
    "be-vlaanderen": {"provinces": ["BE-VWV", "BE-VOV", "BE-VAN", "BE-VLI", "BE-VBR", "BE-BRU"]},
    "be-wallonie": {"provinces": ["BE-WHT", "BE-WNA", "BE-WLX", "BE-WLG", "BE-WBR"]},
    "be-bruxelles": {"provinces": ["BE-BRU"]},
    "lu": {"countries": ["LUX"]},
    "ch": {"countries": ["CHE"]},
    "at": {"countries": ["AUT"]},
    "cz": {"countries": ["CZE"]},
    "pl": {"countries": ["POL"]},
    "si": {"countries": ["SVN"]},
    "de": {"countries": ["DEU"]},
    "de-nw": {"provinces": ["DE-NW"]},
    "de-by": {"provinces": ["DE-BY"]},
    "de-he": {"provinces": ["DE-HE"]},
    "de-sn": {"provinces": ["DE-SN"]},
    "de-be": {"provinces": ["DE-BE"]},
    "de-bb": {"provinces": ["DE-BB", "DE-BE"]},          # Brandenburg's orthophoto covers Berlin too
    "de-hh": {"provinces": ["DE-HH"]},
    "de-sh": {"provinces": ["DE-SH"]},
    "de-rp": {"provinces": ["DE-RP"]},
    "de-th": {"provinces": ["DE-TH"]},
    "de-mv": {"provinces": ["DE-MV"]},
    "de-sl": {"provinces": ["DE-SL"]},
    "de-hb": {"provinces": ["DE-HB"]},
    # the United States are big and Alaska is mostly islands: coarser, the small islands left out
    "us": {"countries": ["USA", "PRI"], "tolerance": 0.02, "smallest": 0.01},
}


def encode(values: list[int]) -> str:
    """Google's polyline encoding of a list of integers (already the differences)."""
    out = []
    for v in values:
        v = ~(v << 1) if v < 0 else v << 1
        while v >= 0x20:
            out.append(chr((0x20 | (v & 0x1F)) + 63))
            v >>= 5
        out.append(chr(v + 63))
    return "".join(out)


def encode_ring(coords) -> str:
    deltas, last = [], (0, 0)
    for lon, lat in coords:
        p = (round(lat * PRECISION), round(lon * PRECISION))
        if p == last and deltas:
            continue
        deltas += [p[0] - last[0], p[1] - last[1]]
        last = p
    return encode(deltas)


def build(folder: Path) -> dict[str, list[str]]:
    from shapely.geometry import Polygon, box, shape
    from shapely.ops import unary_union
    countries = json.loads((folder / "ne_10m_admin_0_countries.geojson").read_text(encoding="utf-8"))["features"]
    states = json.loads((folder / "ne_10m_admin_1_states_provinces.geojson").read_text(encoding="utf-8"))["features"]
    shapes = {}                           # every piece of land, countries and provinces, as Natural Earth draws them
    for f in countries:
        shapes[("country", f["properties"]["ADM0_A3"])] = shape(f["geometry"]).buffer(0)
    for f in states:
        p = f["properties"]
        shapes[("state", p.get("iso_3166_2"), p.get("adm0_a3"), p.get("region"))] = shape(f["geometry"]).buffer(0)
    # the small islands, each with the country and the province nearest to it, if within ISLANDS degrees
    islands = json.loads((folder / "ne_10m_minor_islands.geojson").read_text(encoding="utf-8"))["features"]
    for i, f in enumerate(islands):
        g = shape(f["geometry"]).buffer(0)
        owners = []
        for kind in ("country", "state"):
            near = [(shapes[k].distance(g), k) for k in shapes if k[0] == kind
                    and shapes[k].bounds[0] - ISLANDS <= g.bounds[2] and g.bounds[0] <= shapes[k].bounds[2] + ISLANDS
                    and shapes[k].bounds[1] - ISLANDS <= g.bounds[3] and g.bounds[1] <= shapes[k].bounds[3] + ISLANDS]
            near = [n for n in near if n[0] <= ISLANDS]
            if near:
                owners.append(min(near)[1])
        if owners:
            shapes[("island", i, tuple(owners))] = g
    out = {}
    for name, spec in AREAS.items():
        mine = [k for k in shapes if k[0] == "country" and k[1] in spec.get("countries", ())]
        mine += [k for k in shapes if k[0] == "state" and k[1] in spec.get("provinces", ())]
        mine += [k for k in shapes if k[0] == "state" and (k[2], k[3]) in spec.get("regions", ())]
        own = set(mine)
        mine += [k for k in shapes if k[0] == "island" and own & set(k[2])]
        wanted = len(spec.get("countries", ())) + len(spec.get("provinces", ()))
        if not own or (wanted and len(own) < wanted):
            sys.exit(f"{name}: {len(mine)} pieces found, {wanted} named")
        area = unary_union([shapes[k] for k in mine])
        if "within" in spec:
            area = area.intersection(box(*spec["within"]))
        tolerance = spec.get("tolerance", TOLERANCE)
        area = area.simplify(tolerance, preserve_topology=True)
        # over the sea, not over the neighbours: the land near the area that is not the area's own
        w, s, e, n = area.bounds
        near = box(w - 2 * SEA, s - 2 * SEA, e + 2 * SEA, n + 2 * SEA)
        # not the area's own pieces, nor the country they are in (a province's), nor the provinces inside them
        points = [shapes[m].representative_point() for m in mine]
        neighbours = unary_union([g for k, g in shapes.items() if k not in mine and g.intersects(near)
                                  and not any(g.contains(p) for p in points)
                                  and not any(shapes[m].contains(g.representative_point()) for m in mine)])
        grown = area.buffer(SEA, quad_segs=2).difference(neighbours.buffer(0))
        grown = grown.simplify(tolerance, preserve_topology=True)
        smallest = spec.get("smallest", SMALLEST)
        rings = []
        for p in getattr(grown, "geoms", [grown]):
            if p.geom_type != "Polygon" or p.area < smallest:   # rocks: the margin takes the coast near them
                continue
            rings.append(encode_ring(p.exterior.coords))
            rings += [encode_ring(h.coords) for h in p.interiors if Polygon(h).area >= smallest]
        out[name] = rings
    return out


def write(areas: dict[str, list[str]]) -> None:
    lines = ['"""Where the map sources have imagery: the outline of each area of tiles.py, generated by',
             'tools/map_coverage.py from Natural Earth 1:10m (public domain), simplified to about a kilometre and pushed',
             "about 2 km out over the sea. Each area is a list of rings (outer outlines and holes, read with the even-odd",
             "rule) in Google's encoded polyline format with three decimals, latitude first. Generated: do not edit by",
             'hand, run the tool."""', "",
             "AREAS: dict[str, tuple[str, ...]] = {"]
    for name, rings in areas.items():
        lines.append(f"    {name!r}: (")
        for r in rings:
            lines.append(f"        {r!r},")
        lines.append("    ),")
    lines.append("}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path, help="the folder with the two GeoJSON files of Natural Earth")
    args = parser.parse_args()
    areas = build(args.folder)
    write(areas)
    size = OUT.stat().st_size
    print(f"{OUT.relative_to(ROOT)}: {len(areas)} areas, {sum(len(r) for r in areas.values())} rings, {size} bytes")


if __name__ == "__main__":
    main()
