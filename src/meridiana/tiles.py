"""Background imagery for the plan: the map sources (R36), where each has imagery, which one is best for a site,
which tiles a view needs, from which address, at which zoom, and where they go on the plan. Plain Python: the network
side is in ui/tileloader.py, the reading of a server's capabilities in capabilities.py.

A source is data (`Source`): an XYZ template, a WMTS (its tile matrices on the Web Mercator grid, by key-value pairs
or by a REST template) or a WMS (a GetMap for each tile, in EPSG:3857 or, where the server has not it, in degrees:
the tile's corners are exact and inside a tile at zoom 10 or more the rows differ from Mercator by less than 0,2
pixel). Each says its name, the area it covers (an outline of mapcoverage.py, a box, or the world), its zooms, the
attribution to show on the plan, its licence with the address where it was read and the date, and whether it needs a
key. The program's own need none; a source the designer adds (Preferences > Maps) may carry `{key}` in its address,
and the key stays in the system's keyring, never in the settings (ui/tileloader.py asks it there).

The program's own sources were chosen on 25/10/2026 reading each licence on its official page and asking a few tiles
of each with Meridiana's User-Agent (docs/compiti/21-mappe.md has the addresses, the dates, the trials and the
sources left out with the reason: Esri, Google, Bing and Azure want an account and a key and forbid the cache; EOX's
Sentinel-2 mosaics after 2016 are non-commercial; Denmark, Norway, Sweden and Finland want a token). In short:
- Italy: the national orthophoto (PCN, AGEA 2012, 50 cm), a WMS that declares no access constraints and no fees,
  HTTP only, its server at times failing to read its own archive (requests are retried); the open orthophotos of
  South Tyrol (2023, CC BY 4.0), Trentino (2015, CC BY 2.5 IT), Tuscany (2023, CC BY 4.0) and Friuli Venezia Giulia
  (2017-2020, IODL 2.0). The newer AGEA orthophotos of the other regions are AGEA's, lent for institutional use: not
  here (study 18, F 1.2);
- France (IGN, Licence Ouverte), Spain (PNOA, CC BY 4.0), Portugal (DGT, a viewing service, Airbus satellite
  imagery), the Netherlands (PDOK, CC BY 4.0), Flanders, Wallonia and Brussels, Luxembourg (CC0), Switzerland
  (swisstopo, free with the source), Austria (basemap.at, CC BY 4.0), Czechia, Poland, Slovenia, thirteen German
  Länder (dl-de/zero, dl-de/by or CC BY 4.0), the United States (USGS, public domain);
- the world: EOX's Sentinel-2 cloudless of 2016 (CC BY 4.0, 10 m, a reasonable traffic), and the maps:
  OpenStreetMap with its policy (an identifying User-Agent, at least a week of cache, no bulk download, the
  attribution on screen), OpenTopoMap (CC-BY-SA, a volunteer's server, a light use), basemap.de for Germany.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from datetime import date
from functools import cache
from urllib.parse import quote, urlsplit

from . import geo

WEB_MERCATOR_RES0 = 2 * math.pi * geo.MERCATOR_R / 256      # metres per pixel at zoom 0, at the equator
KINDS = ("xyz", "wmts", "wms")
IMAGERY = ("photo", "map")
WMS_CRS = ("EPSG:3857", "EPSG:900913", "CRS:84", "EPSG:4326")      # the boxes Meridiana can ask a WMS in
AUTO, NONE = "auto", "none"          # the choices of the background besides a source: the best for the site, none
MARGIN_KM = 3.0                      # a source is offered this far past its outline: orthophotos go past borders
CUSTOM_PREFIX = "user-"              # the keys of the sources added by the designer
MAX_ZOOM = 24


def _ids(fmt: str, last: int, shift: int = 0, first: int = 0) -> tuple[str, ...]:
    """The TileMatrix identifiers of a WMTS for each zoom up to `last`: `fmt` with n = z - shift, "" below `first`."""
    return tuple("" if z < first else fmt.format(n=z - shift) for z in range(last + 1))


_FIELD = re.compile(r"\{(-?[A-Za-z]+)(?::0?(\d+)d)?\}")


def _fill(template: str, values: dict) -> str:
    """The placeholders of an address replaced: {z}, {x}, {y}, {-y} (TMS), {key}, the WMTS ones ({TileMatrix},
    {TileCol}, {TileRow}, {TileMatrixSet}, {Style}); a width ({z:02d}) pads with zeros. Never str.format on a
    template the designer wrote: an unknown name stays as it is."""
    def one(m: re.Match) -> str:
        name, width = m.group(1), m.group(2)
        if name not in values:
            return m.group(0)
        text = str(values[name])
        return text.zfill(int(width)) if width else text
    return _FIELD.sub(one, template)


def _join(url: str, params: list) -> str:
    query = "&".join(f"{k}={quote(str(v), safe=':/,')}" for k, v in params)
    if "?" not in url:
        return f"{url}?{query}"
    return url + ("" if url.endswith(("?", "&")) else "&") + query


@dataclass(frozen=True)
class Source:
    key: str
    name: str                      # English; display_name() gives the program's own in the language in use
    kind: str                      # "xyz", "wmts" or "wms"
    url: str                       # xyz: the template; wmts: the GetTile address or a REST template; wms: the address
    attribution: str               # on the plan, always; "{year}" is the year of the retrieval (the German Länder)
    licence: str = ""              # the terms in a line, for the menu and the preferences
    licence_url: str = ""          # where they were read
    checked: str = ""              # when (ISO date); for the designer's, when it was added
    area: str = ""                 # an outline of mapcoverage.AREAS; "" and no box: the world
    bbox: tuple = ()               # (W, S, E, N) in degrees, for a source read from its capabilities
    imagery: str = "photo"         # "photo" or "map"
    rank: int = 0                  # the best where several cover a site: the higher
    min_zoom: int = 0
    max_zoom: int = 19
    layer: str = ""                # wms LAYERS, wmts LAYER
    style: str = ""                # wms STYLES, wmts STYLE
    matrix_set: str = ""           # wmts TileMatrixSet
    matrices: tuple = ()           # wmts: the TileMatrix of each zoom (index = z), "" where it has none
    format: str = "image/jpeg"
    version: str = "1.3.0"         # wms
    crs: str = "EPSG:3857"         # wms: one of WMS_CRS
    max_age_days: int = 30         # how long a tile of the cache is good
    sample: tuple = ()             # (lat, lon) of a public square in its area: the trial (tools/try_map_sources.py)
    custom: bool = False           # added by the designer
    capabilities: str = ""         # the capabilities address it was read from (a designer's source)

    @property
    def is_wms(self) -> bool:
        return self.kind == "wms"

    @property
    def needs_key(self) -> bool:
        return "{key}" in self.url

    @property
    def cache_name(self) -> str:
        """The folder of its tiles in the cache: the key for the program's own (as before R36), with a digest of
        the address for the designer's, whose address can change under the same key."""
        if not self.custom:
            return self.key
        what = "|".join((self.kind, self.url, self.layer, self.style, self.matrix_set, self.format, self.crs))
        return f"{self.key}-{hashlib.sha1(what.encode()).hexdigest()[:8]}"

    def credit(self, year: int | None = None) -> str:
        return self.attribution.replace("{year}", str(year or date.today().year))

    def tile_url(self, z: int, x: int, y: int, key: str = "") -> str:
        if self.kind == "wms":
            return self._getmap(z, x, y, key)
        if self.kind == "wmts":
            matrix = self.matrices[z] if 0 <= z < len(self.matrices) else str(z)
            values = {"TileMatrix": matrix, "TileCol": x, "TileRow": y, "TileMatrixSet": self.matrix_set,
                      "Style": self.style, "key": key}
            if "{TileMatrix}" in self.url:
                return _fill(self.url, values)
            return _join(_fill(self.url, {"key": key}), [
                ("SERVICE", "WMTS"), ("REQUEST", "GetTile"), ("VERSION", "1.0.0"), ("LAYER", self.layer),
                ("STYLE", self.style), ("TILEMATRIXSET", self.matrix_set), ("TILEMATRIX", matrix), ("TILEROW", y),
                ("TILECOL", x), ("FORMAT", self.format)])
        return _fill(self.url, {"z": z, "x": x, "y": y, "-y": 2 ** z - 1 - y, "key": key})

    def _getmap(self, z: int, x: int, y: int, key: str) -> str:
        w, s, e, n = geo.tile_bounds(x, y, z)
        if self.crs in ("EPSG:3857", "EPSG:900913"):
            box = f"{w:.3f},{s:.3f},{e:.3f},{n:.3f}"
        else:
            lon_w, lat_s = geo.mercator_to_lonlat(w, s)
            lon_e, lat_n = geo.mercator_to_lonlat(e, n)
            # WMS 1.3.0 reads EPSG:4326 latitude first, as the EPSG register orders it; CRS:84 and 1.1.1 longitude first
            lat_first = self.crs == "EPSG:4326" and self.version.startswith("1.3")
            box = (f"{lat_s:.8f},{lon_w:.8f},{lat_n:.8f},{lon_e:.8f}" if lat_first else
                   f"{lon_w:.8f},{lat_s:.8f},{lon_e:.8f},{lat_n:.8f}")
        styles = self.style if self.style else "," * self.layer.count(",")
        return _join(_fill(self.url, {"key": key}), [
            ("SERVICE", "WMS"), ("VERSION", self.version), ("REQUEST", "GetMap"), ("LAYERS", self.layer),
            ("STYLES", styles), ("CRS" if self.version.startswith("1.3") else "SRS", self.crs), ("BBOX", box),
            ("WIDTH", 256), ("HEIGHT", 256), ("FORMAT", self.format)])

    # where it covers

    def inside(self, lon: float, lat: float) -> bool:
        """The site inside its area itself (no margin); the world's sources are inside everywhere."""
        if self.area:
            a = _area(self.area)
            return a is not None and _in_box(a.bbox, lon, lat, 0.0) and _even_odd(a.rings, lon, lat)
        if self.bbox:
            return _in_box(self.bbox, lon, lat, 0.0)
        return True

    def covers(self, lon: float, lat: float, margin_km: float = MARGIN_KM) -> bool:
        """It has imagery at the site, or at most `margin_km` from its outline."""
        if self.inside(lon, lat):
            return True
        if self.area:
            a = _area(self.area)
            if a is None or not _in_box(a.bbox, lon, lat, margin_km):
                return False
            return _distance_km(a.rings, lon, lat) <= margin_km
        return bool(self.bbox) and _in_box(self.bbox, lon, lat, margin_km)


# the outlines (mapcoverage.py, from tools/map_coverage.py): decoded once each, when first asked

@dataclass(frozen=True)
class _Area:
    rings: tuple
    bbox: tuple


def _decode(text: str) -> list[tuple[float, float]]:
    """A ring in Google's encoded polyline format, three decimals, latitude first: (lon, lat) pairs."""
    values, v, shift = [], 0, 0
    for ch in text:
        b = ord(ch) - 63
        v |= (b & 0x1F) << shift
        shift += 5
        if b < 0x20:
            values.append(~(v >> 1) if v & 1 else v >> 1)
            v, shift = 0, 0
    out, lat, lon = [], 0, 0
    for i in range(0, len(values) - 1, 2):
        lat += values[i]
        lon += values[i + 1]
        out.append((lon / 1000, lat / 1000))
    return out


@cache
def _area(name: str) -> _Area | None:
    from .mapcoverage import AREAS
    if name not in AREAS:
        return None
    rings = tuple(tuple(_decode(r)) for r in AREAS[name])
    lons = [p[0] for r in rings for p in r]
    lats = [p[1] for r in rings for p in r]
    return _Area(rings, (min(lons), min(lats), max(lons), max(lats)))


def _in_box(bbox, lon: float, lat: float, margin_km: float) -> bool:
    w, s, e, n = bbox
    dlat = margin_km / 110.57
    dlon = margin_km / max(1e-6, 111.32 * math.cos(math.radians(lat)))
    return w - dlon <= lon <= e + dlon and s - dlat <= lat <= n + dlat


def _even_odd(rings, lon: float, lat: float) -> bool:
    inside = False
    for ring in rings:
        j = len(ring) - 1
        for i in range(len(ring)):
            xi, yi = ring[i]
            xj, yj = ring[j]
            if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
    return inside


def _distance_km(rings, lon: float, lat: float) -> float:
    """From the site to the nearest side of the outline, on a plane tangent at the site (a few kilometres matter)."""
    kx, ky = 111.32 * math.cos(math.radians(lat)), 110.57
    best = math.inf
    for ring in rings:
        for (x0, y0), (x1, y1) in zip(ring, ring[1:], strict=False):
            ax, ay = (x0 - lon) * kx, (y0 - lat) * ky
            dx, dy = (x1 - x0) * kx, (y1 - y0) * ky
            length = dx * dx + dy * dy
            t = 0.0 if length == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / length))
            best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    return best


# the program's own sources, read and tried on 25/10/2026 (docs/compiti/21-mappe.md)

CHECKED = "2026-10-25"
_SOURCES = [
    # Italy
    Source("pcn", "Italy: orthophoto 2012 (Geoportale Nazionale)", "wms",
           "http://wms.pcn.minambiente.it/ogc?map=/ms_ogc/WMS_v1.3/raster/ortofoto_colore_12.map",
           "Ortofoto 2012: Geoportale Nazionale (MASE)",
           "Geoportale Nazionale (MASE): no access constraints, no fees",
           "http://wms.pcn.minambiente.it/ogc?map=/ms_ogc/WMS_v1.3/raster/ortofoto_colore_12.map&service=WMS"
           "&request=GetCapabilities&version=1.3.0", "2026-10-23", area="it", rank=40, max_zoom=20,
           layer="OI.ORTOIMMAGINI.2012.32,OI.ORTOIMMAGINI.2012.33", sample=(45.4641, 9.1900)),
    Source("it-bz", "South Tyrol: orthophoto 2023", "xyz",
           "https://geoservices.buergernetz.bz.it/mapproxy/root/wmts/p_bz-Orthoimagery:Aerial-2023-RGB/EPSG_3857/"
           "{z:02d}/{x}/{y}.png",
           "Ortofoto 2023 © Provincia autonoma di Bolzano - Alto Adige, CC BY 4.0", "CC BY 4.0",
           "https://geonetwork1.civis.bz.it/geonetwork/srv/api/records/p_bz:Orthoimagery:Aerial-2023-RGB", CHECKED,
           area="it-bz", rank=55, max_zoom=20, sample=(46.4983, 11.3548)),
    Source("it-tn", "Trentino: orthophoto 2015", "wms", "https://siat.provincia.tn.it/geoserver/stem/ecw-rgb-2015/wms",
           "Ortofoto Digitale 2015 - PAT, Provincia Autonoma di Trento (Ufficio Sistemi Informativi, Servizio "
           "Geologico), CC BY 2.5 IT", "CC BY 2.5 IT", "https://pctrento.it/PORTALE/OFD2015/licenza_ofd_2015.pdf",
           CHECKED, area="it-tn", rank=45, max_zoom=20, layer="ecw-rgb-2015", sample=(46.0670, 11.1211)),
    Source("it-toscana", "Tuscany: orthophoto 2023", "wms",
           "https://www502.regione.toscana.it/ows_ofc/com.rt.wms.RTmap/wms?map=owsofc_rt",
           "Ortofoto 2023 © Regione Toscana, CC BY 4.0", "CC BY 4.0",
           "https://www502.regione.toscana.it/geonetwork/srv/api/records/r_toscan:66ca3807-815a-4bd1-b626-98ca240d72a2",
           CHECKED, area="it-toscana", rank=55, max_zoom=20, layer="rt_ofc.5k23.32bit", sample=(43.3183, 11.3314)),
    Source("it-fvg", "Friuli Venezia Giulia: true orthophoto 2017-2020", "wms",
           "https://irdat-ortofoto.regione.fvg.it/geoserver/ows",
           "Ortofoto 2017-2020 © Regione Autonoma Friuli Venezia Giulia, IODL 2.0", "IODL 2.0",
           "https://www.regione.fvg.it/rafvg/cms/RAFVG/ambiente-territorio/conoscere-ambiente-territorio/FOGLIA4/",
           CHECKED, area="it-fvg", rank=50, max_zoom=21, layer="ortofoto:trueorto_FVG_1720",
           sample=(45.6503, 13.7676)),
    # Europe
    Source("fr-ign", "France: IGN orthophotos", "wmts", "https://data.geopf.fr/wmts",
           "© IGN, BD ORTHO, Licence Ouverte Etalab 2.0", "Licence Ouverte 2.0 (Etalab)", "https://cartes.gouv.fr/cgu",
           CHECKED, area="fr", rank=45, max_zoom=19, layer="ORTHOIMAGERY.ORTHOPHOTOS", style="normal",
           matrix_set="PM_0_19", matrices=_ids("{n}", 19), sample=(48.8566, 2.3522)),
    Source("es-pnoa", "Spain: PNOA orthophotos", "wmts", "https://www.ign.es/wmts/pnoa-ma",
           "PNOA máxima actualidad, CC BY 4.0 scne.es", "CC BY 4.0",
           "https://www.ign.es/resources/licencia/Condiciones_licenciaUso_IGN.pdf", CHECKED, area="es", rank=45,
           max_zoom=20, layer="OI.OrthoimageCoverage", style="default", matrix_set="GoogleMapsCompatible",
           matrices=_ids("{n}", 20), sample=(40.4155, -3.7074)),
    Source("pt-dgt", "Portugal: OrtoSat 2023 (satellite)", "wms", "https://ortos.dgterritorio.gov.pt/wms/ortosat2023",
           "Informação geográfica cedida pela Direção-Geral do Território, OrtoSat2023 (Pléiades Neo © Airbus DS)",
           "DGT viewing service, without restrictions",
           "https://snig.dgterritorio.gov.pt/rndg/srv/por/catalog.search#/metadata/b2a1ca02-779b-4189-b895-85d10fff610f", CHECKED,
           area="pt", rank=40, max_zoom=20, layer="ortoSat2023-CorVerdadeira", sample=(38.7076, -9.1365)),
    Source("nl-pdok", "Netherlands: PDOK aerial photo", "xyz",
           "https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0/Actueel_orthoHR/EPSG:3857/{z:02d}/{x}/{y}.jpeg",
           "Luchtfoto © Beeldmateriaal.nl, CC BY 4.0, via PDOK", "CC BY 4.0",
           "https://www.pdok.nl/introductie/-/article/pdok-luchtfoto-rgb-open-", CHECKED, area="nl", rank=50,
           max_zoom=21, sample=(52.3731, 4.8926)),
    Source("be-vlaanderen", "Flanders: orthophoto", "wmts", "https://geo.api.vlaanderen.be/OMWRGBMRVL/wmts",
           "Bron: Luchtopnamen Digitaal Vlaanderen", "Modellicentie gratis hergebruik",
           "https://data.vlaanderen.be/id/licentie/modellicentie-gratis-hergebruik/v1.0", CHECKED,
           area="be-vlaanderen", rank=50, max_zoom=21, layer="omwrgbmrvl", matrix_set="GoogleMapsVL",
           matrices=_ids("{n}", 21), format="image/png", sample=(51.2213, 4.3997)),
    Source("be-wallonie", "Wallonia: orthophoto", "wms",
           "https://geoservices.wallonie.be/arcgis/services/IMAGERIE/ORTHO_LAST/MapServer/WMSServer",
           "Source : Service public de Wallonie (SPW), Orthophotos, CC BY 4.0", "CC BY 4.0",
           "https://geoportail.wallonie.be/files/documents/ConditionsSPW/LicServicesSPW.pdf", CHECKED,
           area="be-wallonie", rank=50, max_zoom=20, layer="0", sample=(50.6456, 5.5753)),
    Source("be-bruxelles", "Brussels: UrbIS orthophoto", "wmts",
           "https://geoservices-grid.irisnet.be/geowebcache/service/wmts", "Orthophoto UrbIS, paradigm.brussels, CC0",
           "CC0", "https://geobru-geonetwork.irisnet.be/geonetwork/srv/api/records/da181eac-0756-11f1-8373-900f0cda5d5b",
           CHECKED, area="be-bruxelles", rank=60, max_zoom=21, layer="Ortho", matrix_set="EPSG:900913",
           matrices=_ids("EPSG:900913:{n}", 21), sample=(50.8469, 4.3525)),
    Source("lu-act", "Luxembourg: orthophoto", "xyz",
           "https://wmts1.geoportail.lu/opendata/wmts/ortho_latest/GLOBAL_WEBMERCATOR_4_V3/{z:02d}/{x}/{y}.jpeg",
           "Orthophoto © ACT, geoportail.lu, CC0", "CC0",
           "https://data.public.lu/en/datasets/inspire-annex-ii-theme-orthoimagery-orthoimagecoverage-2025-summer/",
           CHECKED, area="lu", rank=50, max_zoom=21, sample=(49.6108, 6.1305)),
    Source("ch-swisstopo", "Switzerland: SWISSIMAGE", "xyz",
           "https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swissimage/default/current/3857/{z}/{x}/{y}.jpeg",
           "© swisstopo", "swisstopo free geodata (OGD, the source cited)",
           "https://www.swisstopo.admin.ch/en/terms-of-use-free-geodata-and-geoservices", CHECKED, area="ch", rank=50,
           max_zoom=20, sample=(46.9467, 7.4440)),
    Source("at-basemap", "Austria: basemap.at orthophoto", "xyz",
           "https://mapsneu.wien.gv.at/basemap/bmaporthofoto30cm/normal/google3857/{z}/{y}/{x}.jpeg",
           "Datenquelle: basemap.at", "CC BY 4.0", "https://basemap.at/", CHECKED, area="at", rank=45, max_zoom=20,
           sample=(48.2085, 16.3731)),
    Source("cz-cuzk", "Czechia: ČÚZK orthophoto", "xyz",
           "https://ags.cuzk.gov.cz/arcgis1/rest/services/ORTOFOTO_WM/MapServer/WMTS/tile/1.0.0/ORTOFOTO_WM/default/"
           "default028mm/{z}/{y}/{x}", "ČÚZK – on-line, Ortofoto ČR: ČÚZK, {year}", "CC BY 4.0",
           "https://cuzk.gov.cz/Predpisy/Podminky-poskytovani-prostor-dat-a-sitovych-sluzeb/"
           "Podminky-poskytovani-sitovych-sluzeb-CUZK.aspx", CHECKED, area="cz", rank=45, max_zoom=20,
           sample=(50.0875, 14.4213)),
    # Poland: the WMTS, a little softer than the WMS at the highest zooms (GUGiK says so), because the WMS answered 404
    # to six requests out of eight on 25/10/2026 while the WMTS answered every one
    Source("pl-gugik", "Poland: Geoportal orthophoto", "wmts",
           "https://mapy.geoportal.gov.pl/wss/service/PZGIK/ORTO/WMTS/StandardResolution",
           "Ortofotomapa: Geoportal.gov.pl © GUGiK", "free for any use, no harvesting",
           "https://www.geoportal.gov.pl/en/data/orthophotomap-orto/", CHECKED, area="pl", rank=45, max_zoom=19,
           layer="ORTOFOTOMAPA", style="default", matrix_set="EPSG:3857", matrices=_ids("EPSG:3857:{n}", 19),
           sample=(52.2477, 21.0137)),
    Source("si-gurs", "Slovenia: GURS orthophoto", "wms", "https://ipi.eprostor.gov.si/wms-si-gurs-dts/wms",
           "Geodetska uprava Republike Slovenije, ortofoto DOF025, stanje {year}", "CC BY 4.0",
           "https://www.e-prostor.gov.si/dostopi/javni-dostop/?acitem=1821-1822", CHECKED, area="si", rank=45,
           max_zoom=20, layer="SI.GURS.ZPDZ:DOF025", sample=(46.0514, 14.5060)),
    # Germany: the Länder whose orthophotos are open (Baden-Württemberg, Niedersachsen and Sachsen-Anhalt did not
    # answer on 25/10/2026: to be tried again); NRW's matrices start at zoom 5 with "00"
    Source("de-nw", "North Rhine-Westphalia: DOP", "wmts",
           "https://www.wmts.nrw.de/geobasis/wmts_nw_dop/tiles/nw_dop/EPSG_3857_16/{TileMatrix}/{TileCol}/{TileRow}",
           "Geobasis NRW, dl-de/zero-2-0", "dl-de/zero-2-0",
           "https://ckan.open.nrw/dataset/56fb584b-10cf-4009-a405-0bef06bb3e00", CHECKED, area="de-nw", rank=50,
           min_zoom=5, max_zoom=21, matrix_set="EPSG_3857_16", matrices=_ids("{n:02d}", 21, shift=5, first=5),
           sample=(51.2260, 6.7727)),
    Source("de-by", "Bavaria: DOP", "xyz", "https://wmtsod1.bayernwolke.de/wmts/by_dop/smerc/{z}/{x}/{y}",
           "© Datenquellen: Bayerische Vermessungsverwaltung, Europäische Union, enthält Copernicus Sentinel-2 Daten "
           "2018, verarbeitet durch das Bundesamt für Kartographie und Geodäsie (BKG)", "CC BY 4.0",
           "https://geodaten.bayern.de/odd/m/3/html/nutzungsbedingungen.html", CHECKED, area="de-by", rank=50,
           max_zoom=19, sample=(48.1374, 11.5755)),
    Source("de-he", "Hesse: DOP20", "wms", "https://www.gds-srv.hessen.de/cgi-bin/lika-services/ogc-free-images.ows",
           "Geobasisdaten © Hessische Verwaltung für Bodenmanagement und Geoinformation", "§ 18 HVGG, free use",
           "https://hvbg.hessen.de/geoinformation/open-data", CHECKED, area="de-he", rank=50, max_zoom=20,
           layer="he_dop_rgb", sample=(50.0819, 8.2424)),
    Source("de-sn", "Saxony: DOP20", "wms", "https://geodienste.sachsen.de/wms_geosn_dop-rgb/guest",
           "Quelle: GeoSN, dl-de/by-2-0", "dl-de/by-2-0",
           "https://www.landesvermessung.sachsen.de/allgemeine-nutzungsbedingungen-8954.html", CHECKED, area="de-sn",
           rank=50, max_zoom=20, layer="sn_dop_020", sample=(51.0498, 13.7385)),
    Source("de-be", "Berlin: TrueDOP20 2025", "wms", "https://gdi.berlin.de/services/wms/truedop_2025_sommer",
           "Geoportal Berlin, TrueDOP20 Sommer 2025, dl-de/zero-2-0", "dl-de/zero-2-0",
           "https://gdi.berlin.de/geonetwork/srv/api/records/488857c4-d13f-410e-bf3b-569ca73af5d2", CHECKED,
           area="de-be", rank=55, max_zoom=20, layer="truedop_2025_sommer_rgb", sample=(52.5137, 13.3928)),
    Source("de-bb", "Brandenburg: DOP20", "wms", "https://isk.geobasis-bb.de/mapproxy/dop20c/service/wms",
           "© GeoBasis-DE/LGB ({year}), dl-de/by-2-0; © Geoportal Berlin, dl-de/by-2-0", "dl-de/by-2-0",
           "https://geobasis-bb.de/lgb/de/agnb/", CHECKED, area="de-bb", rank=50, max_zoom=20, layer="bebb_dop20c",
           sample=(52.3954, 13.0601)),
    Source("de-hh", "Hamburg: DOP 2024", "wms", "https://geodienste.hamburg.de/wms_dop_zeitreihe_belaubt?TIME=2024",
           "Freie und Hansestadt Hamburg, Landesbetrieb Geoinformation und Vermessung (LGV), dl-de/by-2-0",
           "dl-de/by-2-0", "https://suche.transparenz.hamburg.de/dataset/digitale-orthophotos-belaubt-hamburg8",
           CHECKED, area="de-hh", rank=50, max_zoom=20, layer="dop_zeitreihe_belaubt", sample=(53.5505, 9.9922)),
    Source("de-sh", "Schleswig-Holstein: DOP20", "wms", "https://dienste.gdi-sh.de/WMS_SH_DOP20col_OpenGBD",
           "© GeoBasis-DE/LVermGeo SH/CC BY 4.0", "CC BY 4.0",
           "https://geodaten.schleswig-holstein.de/gaialight-sh/_apps/dladownload/lizenz.html", CHECKED,
           area="de-sh", rank=50, max_zoom=20, layer="sh_dop20_rgb", sample=(54.3227, 10.1378)),
    Source("de-rp", "Rhineland-Palatinate: DOP20", "wms", "https://geo4.service24.rlp.de/wms/rp_dop20.fcgi",
           "©GeoBasis-DE / LVermGeoRP ({year}), dl-de/by-2-0, www.lvermgeo.rlp.de", "dl-de/by-2-0",
           "https://lvermgeo.rlp.de/geodaten-geoshop/open-data", CHECKED, area="de-rp", rank=50, max_zoom=20,
           layer="rp_dop20", sample=(49.9996, 8.2741)),
    Source("de-th", "Thuringia: DOP20", "wms", "https://www.geoproxy.geoportal-th.de/geoproxy/services/DOP20",
           "© GDI-Th, CC BY 4.0", "CC BY 4.0",
           "https://geomis.geoportal-th.de/geonetwork/srv/api/records/3940ce6d-a2fc-44cf-9b30-916f999750ae", CHECKED,
           area="de-th", rank=50, max_zoom=20, layer="th_dop", sample=(50.9764, 11.0235)),
    Source("de-mv", "Mecklenburg-Western Pomerania: DOP20", "wms", "https://www.geodaten-mv.de/dienste/adv_dop",
           "© GeoBasis-DE/M-V {year}, CC BY 4.0", "CC BY 4.0",
           "https://www.laiv-mv.de/static/LAIV/Geoinformation/Dateien/Geobasisdaten/Kurzbeschreibung_WMS_DOP.pdf",
           CHECKED, area="de-mv", rank=50, max_zoom=20, layer="mv_dop", sample=(53.6283, 11.4133)),
    Source("de-sl", "Saarland: DOP20 2025", "wms", "https://geoportal.saarland.de/freewms/dop2025",
           "© GeoBasis DE/LVGL-SL ({year}), dl-de/by-2-0", "dl-de/by-2-0",
           "https://www.shop.lvgl.saarland.de/index.php?id=18&option=com_content&view=article", CHECKED, area="de-sl",
           rank=50, max_zoom=20, layer="sl_dop20_rgb", sample=(49.2324, 6.9965)),
    Source("de-hb", "Bremen: DOP10 2025", "wms", "https://geodienste.bremen.de/wms_dop_lb",
           "© GeoBasis-DE / Landesamt GeoInformation Bremen ({year}), CC BY 4.0", "CC BY 4.0",
           "https://www.geo.bremen.de/sixcms/detail.php?gsid=bremen04.c.15613.de", CHECKED, area="de-hb", rank=55,
           max_zoom=21, layer="dop10_2025_HB,dop10_2025_BHV", sample=(53.0758, 8.8072)),
    # elsewhere
    Source("us-usgs", "United States: USGS imagery", "xyz",
           "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}",
           "USGS The National Map: Orthoimagery (USDA, USGS), public domain", "public domain",
           "https://www.usgs.gov/faqs/what-are-terms-uselicensing-map-services-and-data-national-map", CHECKED,
           area="us", rank=30, max_zoom=16, sample=(40.7308, -73.9973)),
    Source("eox-2016", "World: Sentinel-2 cloudless 2016 (10 m)", "xyz",
           "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/GoogleMapsCompatible/{z}/{y}/{x}.jpg",
           "Sentinel-2 cloudless 2016 by EOX IT Services GmbH (contains modified Copernicus Sentinel data 2016), "
           "CC BY 4.0", "CC BY 4.0, a reasonable traffic", "https://cloudless.eox.at/documentation/faq", CHECKED,
           rank=5, max_zoom=14, max_age_days=60, sample=(-34.6083, -58.3723)),
    # maps
    Source("osm", "OpenStreetMap", "xyz", "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
           "© OpenStreetMap contributors", "ODbL data; OpenStreetMap's tile usage policy",
           "https://operations.osmfoundation.org/policies/tiles/", CHECKED, imagery="map", rank=20, max_zoom=19,
           sample=(43.3183, 11.3314)),
    Source("opentopomap", "OpenTopoMap", "xyz", "https://tile.opentopomap.org/{z}/{x}/{y}.png",
           "© OpenStreetMap contributors, SRTM | © OpenTopoMap (CC-BY-SA)", "CC-BY-SA 3.0, with the attribution; a "
           "light use", "https://opentopomap.org/about", CHECKED, imagery="map", rank=10, max_zoom=17,
           sample=(43.3183, 11.3314)),
    Source("de-basemap", "Germany: basemap.de map", "xyz",
           "https://sgx.geodatenzentrum.de/wmts_basemapde/tile/1.0.0/de_basemapde_web_raster_farbe/default/"
           "GLOBAL_WEBMERCATOR/{z}/{y}/{x}.png", "© GeoBasis-DE / BKG ({year}) CC BY 4.0", "CC BY 4.0",
           "https://basemap.de/", CHECKED, area="de", imagery="map", rank=30, max_zoom=19, sample=(50.1109, 8.6821)),
]
SOURCES: dict[str, Source] = {s.key: s for s in _SOURCES}


def display_name(source: Source) -> str:
    """The name in the language in use: the program's own are translated, the designer's are as written."""
    if source.custom:
        return source.name
    return _names().get(source.key, source.name)


def display_licence(source: Source) -> str:
    """The licence in a line in the language in use: the program's own that are words, not a licence's name, are
    translated; the designer's are as written."""
    if source.custom:
        return source.licence
    return _licences().get(source.key, source.licence)


def _licences() -> dict[str, str]:
    from .i18n import _
    return {
        "pcn": _("Geoportale Nazionale (MASE): no access constraints, no fees"),
        "pt-dgt": _("DGT viewing service, without restrictions"),
        "ch-swisstopo": _("swisstopo free geodata (OGD, the source cited)"),
        "pl-gugik": _("free for any use, no harvesting"), "de-he": _("§ 18 HVGG, free use"),
        "us-usgs": _("public domain"), "eox-2016": _("CC BY 4.0, a reasonable traffic"),
        "osm": _("ODbL data; OpenStreetMap's tile usage policy"),
        "opentopomap": _("CC-BY-SA 3.0, with the attribution; a light use"),
    }


def _names() -> dict[str, str]:
    from .i18n import _
    return {
        "pcn": _("Italy: orthophoto 2012 (Geoportale Nazionale)"), "it-bz": _("South Tyrol: orthophoto 2023"),
        "it-tn": _("Trentino: orthophoto 2015"), "it-toscana": _("Tuscany: orthophoto 2023"),
        "it-fvg": _("Friuli Venezia Giulia: true orthophoto 2017-2020"), "fr-ign": _("France: IGN orthophotos"),
        "es-pnoa": _("Spain: PNOA orthophotos"), "pt-dgt": _("Portugal: OrtoSat 2023 (satellite)"),
        "nl-pdok": _("Netherlands: PDOK aerial photo"), "be-vlaanderen": _("Flanders: orthophoto"),
        "be-wallonie": _("Wallonia: orthophoto"), "be-bruxelles": _("Brussels: UrbIS orthophoto"),
        "lu-act": _("Luxembourg: orthophoto"), "ch-swisstopo": _("Switzerland: SWISSIMAGE"),
        "at-basemap": _("Austria: basemap.at orthophoto"), "cz-cuzk": _("Czechia: ČÚZK orthophoto"),
        "pl-gugik": _("Poland: Geoportal orthophoto"), "si-gurs": _("Slovenia: GURS orthophoto"),
        "de-nw": _("North Rhine-Westphalia: DOP"), "de-by": _("Bavaria: DOP"), "de-he": _("Hesse: DOP20"),
        "de-sn": _("Saxony: DOP20"), "de-be": _("Berlin: TrueDOP20 2025"), "de-bb": _("Brandenburg: DOP20"),
        "de-hh": _("Hamburg: DOP 2024"), "de-sh": _("Schleswig-Holstein: DOP20"),
        "de-rp": _("Rhineland-Palatinate: DOP20"), "de-th": _("Thuringia: DOP20"),
        "de-mv": _("Mecklenburg-Western Pomerania: DOP20"), "de-sl": _("Saarland: DOP20 2025"),
        "de-hb": _("Bremen: DOP10 2025"), "us-usgs": _("United States: USGS imagery"),
        "eox-2016": _("World: Sentinel-2 cloudless 2016 (10 m)"), "osm": _("OpenStreetMap"),
        "opentopomap": _("OpenTopoMap"), "de-basemap": _("Germany: basemap.de map"),
    }


# the designer's sources, as the settings keep them (config.map_sources)

def new_key() -> str:
    import uuid
    return CUSTOM_PREFIX + uuid.uuid4().hex[:8]


def problems(d) -> list[str]:
    """What keeps a source of the designer from being used, in words; [] when it can be."""
    from .i18n import _
    try:
        s = _from_dict(d)
    except (TypeError, ValueError) as error:
        return [_("The source is not readable: {why}").format(why=error)]
    out = []
    if not s.name.strip():
        out.append(_("It needs a name."))
    if not s.attribution.strip():
        out.append(_("It needs the attribution its licence asks for: it is shown on the plan."))
    if urlsplit(s.url).scheme not in ("http", "https") or not urlsplit(s.url).netloc:
        out.append(_("The address must start with http:// or https://."))
    if s.kind == "xyz" and not (re.search(r"\{z\b", s.url) and re.search(r"\{x\b", s.url)
                                and re.search(r"\{-?y\b", s.url)):
        out.append(_("An XYZ address has {z}, {x} and {y} (or {-y}) where the tile goes."))
    if s.kind == "wmts" and (not s.matrix_set or not any(s.matrices)):
        out.append(_("A WMTS source is made from its capabilities, with a Web Mercator tile matrix set."))
    if s.kind in ("wmts", "wms") and not s.layer and "{TileMatrix}" not in s.url:
        out.append(_("Choose the layer."))
    if s.kind == "wms" and s.crs not in WMS_CRS:
        out.append(_("The WMS must offer EPSG:3857, CRS:84 or EPSG:4326."))
    return out


def _text(d: dict, name: str, default: str = "") -> str:
    v = d.get(name, default)
    if v.__class__ is not str:
        raise ValueError(f"{name} is not text")
    return v


def _int(d: dict, name: str, default: int, low: int, high: int) -> int:
    v = d.get(name, default)
    if v.__class__ is not int or not low <= v <= high:
        raise ValueError(f"{name} is not a whole number from {low} to {high}")
    return v


def _from_dict(d) -> Source:
    if not isinstance(d, dict):
        raise ValueError("not a table")
    key = _text(d, "key")
    if not key.startswith(CUSTOM_PREFIX):
        raise ValueError(f"key {key!r}")
    kind = _text(d, "kind", "xyz")
    if kind not in KINDS:
        raise ValueError(f"kind {kind!r}")
    imagery = _text(d, "imagery", "photo")
    if imagery not in IMAGERY:
        raise ValueError(f"imagery {imagery!r}")
    bbox = d.get("bbox", [])
    if not isinstance(bbox, list) or bbox and (len(bbox) != 4 or any(
            v.__class__ not in (int, float) or not math.isfinite(v) for v in bbox)):
        raise ValueError("bbox is not four numbers")
    matrices = d.get("matrices", [])
    if not isinstance(matrices, list) or any(m.__class__ is not str for m in matrices):
        raise ValueError("matrices is not a list of text")
    min_zoom = _int(d, "min_zoom", 0, 0, MAX_ZOOM)
    return Source(key, _text(d, "name"), kind, _text(d, "url").strip(), _text(d, "attribution"),
                  _text(d, "licence"), _text(d, "licence_url"), _text(d, "added"), bbox=tuple(float(v) for v in bbox),
                  imagery=imagery, min_zoom=min_zoom, max_zoom=_int(d, "max_zoom", 19, min_zoom, MAX_ZOOM),
                  layer=_text(d, "layer"), style=_text(d, "style"), matrix_set=_text(d, "matrix_set"),
                  matrices=tuple(matrices), format=_text(d, "format", "image/jpeg") or "image/jpeg",
                  version=_text(d, "version", "1.3.0") or "1.3.0", crs=_text(d, "crs", "EPSG:3857") or "EPSG:3857",
                  custom=True, capabilities=_text(d, "capabilities"))


def custom_source(d) -> Source | None:
    """A source of the designer from the settings; None when it is not usable (damaged, or incomplete): the
    preferences say why with problems()."""
    if problems(d):
        return None
    return _from_dict(d)


def to_dict(s: Source) -> dict:
    return {"key": s.key, "name": s.name, "kind": s.kind, "url": s.url, "layer": s.layer, "style": s.style,
            "matrix_set": s.matrix_set, "matrices": list(s.matrices), "format": s.format, "version": s.version,
            "crs": s.crs, "attribution": s.attribution, "licence": s.licence, "licence_url": s.licence_url,
            "bbox": list(s.bbox), "imagery": s.imagery, "min_zoom": s.min_zoom, "max_zoom": s.max_zoom,
            "capabilities": s.capabilities, "added": s.checked}


def catalogue(custom=()) -> dict[str, Source]:
    """The program's sources and the designer's usable ones (the settings' map_sources), by key."""
    out = dict(SOURCES)
    for d in custom:
        s = custom_source(d)
        if s is not None and s.key not in out:
            out[s.key] = s
    return out


# which source for a site

def covering(sources: dict, lon: float, lat: float) -> list[Source]:
    """The sources with imagery at the site: the photos first, the ones whose own area holds the site before those
    that reach it past their border, the best first; then the maps."""
    found = [s for s in sources.values() if s.covers(lon, lat)]
    return sorted(found, key=lambda s: (s.imagery != "photo", not s.inside(lon, lat), -s.rank, display_name(s)))


def best(sources: dict, lon: float, lat: float) -> str:
    """The program's photo that is best at the site (the designer's own sources are used when chosen, never by
    themselves); Sentinel-2 of 2016 covers the world, so there is always one."""
    for s in covering(sources, lon, lat):
        if s.imagery == "photo" and not s.custom:
            return s.key
    return "osm" if "osm" in sources else NONE


AUTO_PHOTO_MPP = 2.0            # a 40 m roof is about 20 screen pixels at this transition


def automatic(sources: dict, lon: float, lat: float, metres_per_pixel: float) -> str:
    """The street map to orient yourself from afar, the best local orthophoto near enough to draw."""
    if metres_per_pixel > AUTO_PHOTO_MPP and "osm" in sources:
        return "osm"
    return best(sources, lon, lat)


def effective(choice: str, sources: dict, lon: float, lat: float, metres_per_pixel: float = 0.0) -> str:
    """The source the plan shows for the designer's choice: none, the source chosen where it covers the site, else
    the automatic source for this zoom (a source chosen for a French project is not used on an Italian one, and comes
    back on the next French one)."""
    if choice == NONE:
        return NONE
    if choice == AUTO:
        return automatic(sources, lon, lat, metres_per_pixel)
    s = sources.get(choice)
    if s is not None and s.covers(lon, lat):
        return choice
    return automatic(sources, lon, lat, metres_per_pixel)


def fallbacks(sources: dict, failed: str, lon: float, lat: float, detailed: bool = True) -> list[str]:
    """Other sources for the same place, best first. Near a roof another photo comes first, then a street map;
    Sentinel-2 is only a distant-view fallback, never a substitute for detail that it cannot provide."""
    found = covering(sources, lon, lat)
    photos = [s.key for s in found if s.imagery == "photo" and s.key != failed
              and (not detailed or s.key != "eox-2016")]
    maps = [s.key for s in found if s.imagery == "map" and s.key != failed]
    return photos + maps


# the tiles of a view

def zoom_for(metres_per_pixel: float, lat: float, max_zoom: int) -> int:
    """The coarsest zoom whose tiles are at least as sharp as the screen."""
    if metres_per_pixel <= 0:
        return max_zoom
    z = math.ceil(math.log2(WEB_MERCATOR_RES0 * math.cos(math.radians(lat)) / metres_per_pixel))
    return max(0, min(max_zoom, z))


def tiles_for(lon_w: float, lat_s: float, lon_e: float, lat_n: float, z: int, limit: int = 400):
    """The tiles covering a lon/lat box at zoom z, nearest the centre first (at most `limit`)."""
    x0, y0 = geo.tile_of(lon_w, lat_n, z)
    x1, y1 = geo.tile_of(lon_e, lat_s, z)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    out = [(x, y) for x in range(min(x0, x1), max(x0, x1) + 1) for y in range(min(y0, y1), max(y0, y1) + 1)]
    out.sort(key=lambda t: (t[0] - cx) ** 2 + (t[1] - cy) ** 2)
    return out[:limit]


def tile_quad(origin: geo.Origin, z: int, x: int, y: int) -> list[tuple[float, float]]:
    """The four corners of a tile on the plan (local metres), north-west first, clockwise: a tile is a
    square in Web Mercator, and very nearly one on the plan, but the corners are placed exactly."""
    w, s, e, n = geo.tile_bounds(x, y, z)
    corners = [(w, n), (e, n), (e, s), (w, s)]
    out = []
    for mx, my in corners:
        lon, lat = geo.mercator_to_lonlat(mx, my)
        out.append(origin.to_local(lon, lat))
    return out


HEMISPHERE_DEGREES = 80.0


def angular_distance(origin: geo.Origin, lon: float, lat: float) -> float:
    """Great-circle distance from the site, used to keep the far side off its local tangent plane."""
    p0, p1 = math.radians(origin.lat), math.radians(lat)
    dp, dl = p1 - p0, math.radians(lon - origin.lon)
    a = math.sin(dp / 2) ** 2 + math.cos(p0) * math.cos(p1) * math.sin(dl / 2) ** 2
    return math.degrees(2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a))))


def tile_in_hemisphere(origin: geo.Origin, z: int, x: int, y: int) -> bool:
    """Whether any of a 3 by 3 sample of a tile lies within the site's visible hemisphere."""
    w, s, e, n = geo.tile_bounds(x, y, z)
    for row in range(3):
        for col in range(3):
            lon, lat = geo.mercator_to_lonlat(w + (e - w) * col / 2, n - (n - s) * row / 2)
            if angular_distance(origin, lon, lat) <= HEMISPHERE_DEGREES:
                return True
    return False


def tile_mesh(origin: geo.Origin, z: int, x: int, y: int):
    """Texture rectangles and exact local quads. Low zooms are bent in small pieces, with identical points on
    neighbouring edges; pieces centred beyond 80 degrees from the site are not drawn."""
    n = 2 ** max(0, min(3, (7 - z) // 2))
    world = 2 * math.pi * geo.MERCATOR_R

    def point(u, v):
        return geo.mercator_to_lonlat(-world / 2 + world * (x + u) / 2 ** z,
                                      world / 2 - world * (y + v) / 2 ** z)

    out = []
    for row in range(n):
        for col in range(n):
            u0, u1 = col / n, (col + 1) / n
            v0, v1 = row / n, (row + 1) / n
            corners = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
            quad = []
            for u, v in corners:
                lon, lat = point(u, v)
                quad.append(origin.to_local(lon, lat))
            lon, lat = point((u0 + u1) / 2, (v0 + v1) / 2)
            if angular_distance(origin, lon, lat) <= HEMISPHERE_DEGREES:
                out.append((u0, v0, u1, v1, quad))
    return out
