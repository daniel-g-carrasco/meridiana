"""What a map server says of itself (R36): the GetCapabilities document of a WMS (1.1.1 or 1.3.0) or of a WMTS
(1.0.0), read for what Meridiana needs to make a source the designer adds in Preferences > Maps: the layers with
their titles, boxes and systems, the WMTS tile matrices on the Web Mercator grid, the address of GetMap or GetTile,
the attribution and the terms (Fees, AccessConstraints) to show before the source is saved. Plain Python, no Qt, no
network: the window fetches the document (ui/map_sources.py) and the tests give recorded ones.

A WMTS layer is usable when one of its matrix sets is Google's grid (EPSG:3857, 256-pixel tiles, the top left
corner at -20037508,34 20037508,34, scale 559082264,03 / 2^z): its TileMatrix identifiers are taken for each zoom,
whatever their names ("0", "05", "EPSG:3857:12", or NRW's "00" at zoom 5). A WMS layer is usable when it offers
EPSG:3857, or CRS:84 or EPSG:4326 (tiles.Source asks the box in degrees)."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from . import tiles

GOOGLE_SCALE0 = 559082264.0287178          # the scale denominator of zoom 0 on Google's grid (0,28 mm pixels)
ORIGIN = 20037508.342789244                # half the side of the Web Mercator square, metres
MERCATOR_CRS = ("3857", "900913", "102100", "102113", "3785")
XLINK = "{http://www.w3.org/1999/xlink}href"
MAX_BYTES = 50_000_000                     # a capabilities document larger than this is not read


@dataclass(frozen=True)
class Layer:
    name: str                              # LAYERS (WMS) or LAYER (WMTS)
    title: str
    abstract: str = ""
    bbox: tuple = ()                       # (W, S, E, N) in degrees, () when not said
    crs: tuple = ()                        # WMS: the systems offered (inherited from the parents)
    styles: tuple = ()
    formats: tuple = ()
    attribution: str = ""
    matrix_set: str = ""                   # WMTS: the Web Mercator set, "" when it has none
    matrices: tuple = ()                   # WMTS: the TileMatrix of each zoom, "" where none
    template: str = ""                     # WMTS: the REST address, the style and the dimensions in it

    def problem(self, kind: str) -> str:
        """Why Meridiana cannot use it, "" when it can."""
        from .i18n import _
        if kind == "wmts" and not self.matrix_set:
            return _("The layer has no tile matrix set on the Web Mercator grid (EPSG:3857, 256-pixel tiles).")
        if kind == "wms" and not choose_crs(self.crs):
            return _("The layer offers neither EPSG:3857 nor CRS:84 nor EPSG:4326.")
        return ""


@dataclass(frozen=True)
class Capabilities:
    kind: str                              # "wms" or "wmts"
    version: str
    title: str
    abstract: str
    fees: str
    constraints: str
    provider: str
    url: str                               # where GetMap or GetTile (key-value pairs) are asked
    layers: tuple

    def layer(self, name: str) -> Layer | None:
        return next((la for la in self.layers if la.name == name), None)

    def terms(self) -> str:
        """Fees and AccessConstraints in a line, as the server writes them."""
        parts = [p for p in (self.fees, self.constraints) if p and p.strip().lower() not in ("none", "-")]
        return " | ".join(" ".join(p.split()) for p in parts)


def _local(tag) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _kids(el, name: str) -> list:
    return [c for c in el if _local(c.tag) == name] if el is not None else []


def _kid(el, name: str):
    found = _kids(el, name)
    return found[0] if found else None


def _text(el, name: str) -> str:
    c = _kid(el, name)
    return (c.text or "").strip() if c is not None else ""


def _path(el, *names):
    for n in names:
        el = _kid(el, n)
        if el is None:
            return None
    return el


def capabilities_url(url: str, kind: str) -> str:
    """The GetCapabilities address from what the designer pasted: as it is when it already asks for them (or is
    a WMTS capabilities file), else with SERVICE and REQUEST added."""
    url = url.strip()
    query = {k.lower(): v for k, v in parse_qsl(urlsplit(url).query)}
    if query.get("request", "").lower() == "getcapabilities" or urlsplit(url).path.lower().endswith(".xml"):
        return url
    params = [("SERVICE", kind.upper()), ("REQUEST", "GetCapabilities")]
    if kind == "wms":
        params.append(("VERSION", "1.3.0"))
    return tiles._join(url, params)


def read(data: bytes) -> Capabilities:
    """The capabilities in `data`; ValueError with the reason when they are not a WMS's or a WMTS's (an error of
    the server is said with its own words)."""
    if len(data) > MAX_BYTES:
        raise ValueError(f"the document is larger than {MAX_BYTES // 1_000_000} MB")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        raise ValueError(f"not XML ({error})") from error
    name = _local(root.tag)
    if name in ("ServiceExceptionReport", "ExceptionReport"):
        words = " ".join(" ".join((e.text or "").split()) for e in root.iter() if (e.text or "").strip())
        raise ValueError(f"the server answered with an error: {words[:300]}")
    if name == "Capabilities":
        return _wmts(root)
    if name in ("WMS_Capabilities", "WMT_MS_Capabilities"):
        return _wms(root)
    raise ValueError(f"not the capabilities of a WMS or a WMTS (<{name}>)")


# WMTS

def _wmts(root) -> Capabilities:
    ident = _kid(root, "ServiceIdentification")
    provider = _text(_kid(root, "ServiceProvider"), "ProviderName")
    url = ""
    for op in _kids(_kid(root, "OperationsMetadata"), "Operation"):
        if op.get("name") != "GetTile":
            continue
        for get in (g for dcp in _kids(op, "DCP") for h in _kids(dcp, "HTTP") for g in _kids(h, "Get")):
            values = [v.text or "" for c in _kids(get, "Constraint") for a in _kids(c, "AllowedValues")
                      for v in _kids(a, "Value")]
            if not values or "KVP" in values:
                url = get.get(XLINK, "")
                break
    contents = _kid(root, "Contents")
    sets = {_text(s, "Identifier"): _mercator(s) for s in _kids(contents, "TileMatrixSet")}
    layers = []
    for la in _kids(contents, "Layer"):
        bbox = ()
        box = _kid(la, "WGS84BoundingBox")
        if box is not None:
            try:
                w, s = (float(v) for v in _text(box, "LowerCorner").split())
                e, n = (float(v) for v in _text(box, "UpperCorner").split())
                bbox = (w, s, e, n)
            except ValueError:
                bbox = ()
        styles = [st for st in _kids(la, "Style")]
        default = next((st for st in styles if st.get("isDefault") == "true"), styles[0] if styles else None)
        style = _text(default, "Identifier") if default is not None else ""
        linked = [_text(link, "TileMatrixSet") for link in _kids(la, "TileMatrixSetLink")]
        matrix_set = next((m for m in linked if sets.get(m)), "")
        formats = tuple(f.text.strip() for f in _kids(la, "Format") if f.text)
        template = ""
        for res in _kids(la, "ResourceURL"):
            if res.get("resourceType") == "tile" and res.get("template"):
                template = res.get("template")
                if "jpeg" in (res.get("format") or "") or "jpg" in (res.get("format") or ""):
                    break
        if template:
            template = template.replace("{Style}", style)
            for dim in _kids(la, "Dimension"):
                template = template.replace("{" + _text(dim, "Identifier") + "}", _text(dim, "Default"))
        layers.append(Layer(_text(la, "Identifier"), _text(la, "Title") or _text(la, "Identifier"),
                            " ".join(_text(la, "Abstract").split()), bbox, (), (style,) if style else (), formats,
                            "", matrix_set, sets.get(matrix_set, ()), template))
    return Capabilities("wmts", root.get("version", "1.0.0"), _text(ident, "Title"), _text(ident, "Abstract"),
                        _text(ident, "Fees"), " ".join(c.text or "" for c in _kids(ident, "AccessConstraints")),
                        provider, url, tuple(layers))


def _mercator(matrix_set) -> tuple:
    """The TileMatrix of each zoom when the set is Google's grid, () when it is not."""
    crs = _text(matrix_set, "SupportedCRS")
    if not any(code in crs for code in MERCATOR_CRS):
        return ()
    ids: dict[int, str] = {}
    for m in _kids(matrix_set, "TileMatrix"):
        try:
            scale = float(_text(m, "ScaleDenominator"))
            x, y = (float(v) for v in _text(m, "TopLeftCorner").split())
            size = (int(_text(m, "TileWidth")), int(_text(m, "TileHeight")))
        except ValueError:
            return ()
        z = math.log2(GOOGLE_SCALE0 / scale) if scale > 0 else -1
        if size != (256, 256) or abs(z - round(z)) > 0.01 or abs(x + ORIGIN) > 2 or abs(y - ORIGIN) > 2:
            continue                       # another grid: not one of Google's zooms
        ids[round(z)] = _text(m, "Identifier")
    if not ids or min(ids) < 0 or max(ids) > tiles.MAX_ZOOM:
        return ()
    return tuple(ids.get(z, "") for z in range(max(ids) + 1))


# WMS

def _wms(root) -> Capabilities:
    version = root.get("version", "1.3.0")
    service = _kid(root, "Service")
    capability = _kid(root, "Capability")
    getmap = _path(capability, "Request", "GetMap")
    formats = tuple(f.text.strip() for f in _kids(getmap, "Format") if f.text)
    online = _path(getmap, "DCPType", "HTTP", "Get", "OnlineResource")
    url = online.get(XLINK, "") if online is not None else ""
    layers: list[Layer] = []

    def walk(el, crs: tuple, bbox: tuple, attribution: str) -> None:
        own = []
        for tag in ("CRS", "SRS"):
            for c in _kids(el, tag):
                own += (c.text or "").split()
        crs = tuple(dict.fromkeys(crs + tuple(own)))
        geo_box = _kid(el, "EX_GeographicBoundingBox")
        try:
            if geo_box is not None:
                bbox = tuple(float(_text(geo_box, k)) for k in ("westBoundLongitude", "southBoundLatitude",
                                                                 "eastBoundLongitude", "northBoundLatitude"))
            elif _kid(el, "LatLonBoundingBox") is not None:
                b = _kid(el, "LatLonBoundingBox")
                bbox = tuple(float(b.get(k)) for k in ("minx", "miny", "maxx", "maxy"))
        except (TypeError, ValueError):
            pass
        attribution = _text(_kid(el, "Attribution"), "Title") or attribution
        name = _text(el, "Name")
        if name:
            layers.append(Layer(name, _text(el, "Title") or name, " ".join(_text(el, "Abstract").split()), bbox,
                                crs, tuple(_text(s, "Name") for s in _kids(el, "Style")), formats, attribution))
        for child in _kids(el, "Layer"):
            walk(child, crs, bbox, attribution)

    for top in _kids(capability, "Layer"):
        walk(top, (), (), "")
    provider = _text(_path(service, "ContactInformation", "ContactPersonPrimary"), "ContactOrganization")
    return Capabilities("wms", version, _text(service, "Title"), _text(service, "Abstract"), _text(service, "Fees"),
                        _text(service, "AccessConstraints"), provider, url, tuple(layers))


OWN_PARAMS = {"service", "request", "version", "layers", "styles", "crs", "srs", "bbox", "width", "height", "format",
              "layer", "style", "tilematrixset", "tilematrix", "tilerow", "tilecol", "transparent"}


def base_url(url: str) -> str:
    """An address of GetMap or GetTile without the parameters tiles.Source adds to each request (a server's own,
    such as MapServer's map=, stay)."""
    parts = urlsplit(url)
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in OWN_PARAMS]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept, safe=":/,"), ""))


def choose_crs(offered) -> str:
    """The system Meridiana asks a WMS's tiles in: Web Mercator when there, else degrees."""
    for crs in tiles.WMS_CRS:
        if crs in offered:
            return crs
    return ""


def choose_format(formats) -> str:
    """JPEG for photos when offered (a third of PNG's weight), else PNG, else the first."""
    for f in ("image/jpeg", "image/jpg", "image/png"):
        if f in formats:
            return f
    return formats[0] if formats else "image/jpeg"


def source_dict(caps: Capabilities, layer: Layer, key: str, name: str, address: str, added: str) -> dict:
    """The designer's source (the settings' form, tiles.to_dict) for a layer of the capabilities read from
    `address`: the attribution and the terms as the server gives them, to be checked and completed in the form."""
    terms = caps.terms()
    d = {"key": key, "name": name or layer.title, "kind": caps.kind, "layer": layer.name, "style": "",
         "matrix_set": "", "matrices": [], "format": choose_format(layer.formats), "version": caps.version,
         "crs": "EPSG:3857", "attribution": layer.attribution or caps.provider,
         "licence": terms[:400], "licence_url": address, "bbox": list(layer.bbox), "imagery": "photo",
         "min_zoom": 0, "max_zoom": 20, "capabilities": address, "added": added}
    if caps.kind == "wmts":
        first = next((z for z, m in enumerate(layer.matrices) if m), 0)
        d.update(url=layer.template or base_url(caps.url or address), style=layer.styles[0] if layer.styles else "",
                 matrix_set=layer.matrix_set, matrices=list(layer.matrices), min_zoom=first,
                 max_zoom=max(first, len(layer.matrices) - 1), version="1.0.0")
    else:
        d.update(url=base_url(caps.url or address), crs=choose_crs(layer.crs) or "EPSG:3857")
    return d
