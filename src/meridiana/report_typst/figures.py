"""What the report draws as files, without Qt: the plan of the modules as SVG (vector in the PDF, fonts of the program),
the carpet of the hours as a small PNG, the formulas as SVG through matplotlib's mathtext (no TeX needed)."""

from __future__ import annotations

import functools
import io
import math
import struct
import zlib
from xml.sax.saxutils import escape, quoteattr

from ..i18n import number

INK = "#1a1a1a"
PLAN = {"building": "#f7f7f4", "building_edge": "#6e6a66", "subfield": "#2a7fc4", "exclusion": "#f7d3e3",
        "exclusion_edge": "#c4467f", "module": "#1c6e8c", "module_edge": "#ffffff", "label": "#24211d",
        "free": "#c9c5bd"}
STRING_HUES = ("#2a7fc4", "#d9822b", "#3a9a5b", "#c4467f", "#7b5fb4", "#8a6d3b", "#1f9aa6", "#b8a31f",
               "#5a6b7d", "#d1495b")
PT_PER_MM = 72 / 25.4


def _nice(length: float) -> float:
    """A round length for the scale bar, about `length`: 1, 2 or 5 times a power of ten."""
    if length <= 0:
        return 1.0
    p = 10 ** math.floor(math.log10(length))
    return max(s * p for s in (1, 2, 5) if s * p <= length) if length >= p else p


def plan_extent(project) -> tuple[float, float, float, float] | None:
    """The plan's box: (x0, x1, y0, y1) of the buildings, the sub-fields and the exclusions."""
    pts = [p for b in project.buildings for p in b.footprint] + [p for sf in project.subfields for p in sf.ring] + \
        [p for e in project.exclusions for p in e.ring]
    if not pts:
        return None
    xs, ys = [float(p[0]) for p in pts], [float(p[1]) for p in pts]
    return min(xs), max(xs), min(ys), max(ys)


def plan_svg(project, results: dict, plant=None, width_mm: float = 174.0, colours: dict | None = None) -> bytes:
    """The plan of the project: buildings, sub-fields with their names, exclusions, the modules laid; with `plant`,
    every string in a hue of its own with its path and its label. North up, the scale bar under the bottom left corner.
    In the plan's metres, so nothing is scaled twice: what must have a size on paper is given for `width_mm` wide."""
    box = plan_extent(project)
    if box is None:
        return b""
    colours = {**PLAN, **(colours or {})}
    x0, x1, y0, y1 = box
    span = max(x1 - x0, y1 - y0, 1.0)
    pad = 0.025 * span
    left, right = x0 - pad, x1 + 3.0 * pad
    bottom, top = y0 - 3.2 * pad, y1 + pad
    width, height = right - left, top - bottom
    pt = width / (width_mm * PT_PER_MM)                       # a point of the paper in metres of the plan

    def px(x: float) -> str:
        return f"{x - left:.3f}"

    def py(y: float) -> str:
        return f"{top - y:.3f}"

    def path(points) -> str:
        return "M" + "L".join(f"{px(float(x))} {py(float(y))}" for x, y in points) + "Z"

    def rings(items, fill, stroke, thick, dash="") -> str:
        d = "".join(path(r) for r in items if len(r) >= 3)
        if not d:
            return ""
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{thick:.3f}"{extra}/>'

    def label(x: float, y: float, text: str, size: float = 7.0, colour: str | None = None) -> str:
        fs = size * pt
        w, h = 0.56 * fs * len(text) + 1.1 * fs, 1.5 * fs
        return (f'<rect x="{float(px(x)) - w / 2:.3f}" y="{float(py(y)) - h / 2:.3f}" width="{w:.3f}" height="{h:.3f}" '
                f'rx="{0.4 * fs:.3f}" fill="#ffffff" fill-opacity="0.88"/>'
                f'<text x="{px(x)}" y="{float(py(y)) + 0.35 * fs:.3f}" font-family="Titillium Web" font-size="{fs:.3f}" '
                f'font-weight="600" text-anchor="middle" fill={quoteattr(colour or colours["label"])}>{escape(text)}</text>')

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.3f} {height:.3f}" '
             f'width="{width_mm:.2f}mm" height="{width_mm * height / width:.2f}mm">']
    parts.append(rings([b.footprint for b in project.buildings], colours["building"], colours["building_edge"], 0.7 * pt))
    parts.append(rings([e.ring for e in project.exclusions], colours["exclusion"], colours["exclusion_edge"], 0.5 * pt))
    hue_of: dict = {}
    ordered = sorted(plant.strings, key=lambda s: (s.inverter, s.mppt, s.index)) if plant is not None else []
    for n, s in enumerate(ordered):
        for sf, key, _c in s.modules:
            hue_of[(sf, key)] = STRING_HUES[n % len(STRING_HUES)]
    by_colour: dict = {}
    for sf in project.subfields:
        r = results.get(sf.id)
        for pm in (getattr(r, "modules", None) or []):
            colour = hue_of.get((sf.id, pm.key), colours["module"] if plant is None else colours["free"])
            by_colour.setdefault(colour, []).append(pm.corners)
    for colour, polygons in by_colour.items():
        parts.append(rings(polygons, colour, colours["module_edge"], 0.15 * pt))
    parts.append(rings([sf.ring for sf in project.subfields], "none", colours["subfield"], 0.8 * pt,
                       f"{4 * pt:.3f} {2 * pt:.3f}"))
    if plant is not None:
        for n, s in enumerate(ordered):
            pts = [c for _sf, _k, c in s.modules if c]
            if not pts:
                continue
            hue = STRING_HUES[n % len(STRING_HUES)]
            d = "M" + "L".join(f"{px(float(p[0]))} {py(float(p[1]))}" for p in pts)
            parts.append(f'<path d="{d}" fill="none" stroke="{hue}" stroke-width="{0.6 * pt:.3f}"/>')
            parts.append(label(float(pts[0][0]), float(pts[0][1]), str(s.label), 5.8, hue))
    else:
        for sf in project.subfields:
            if len(sf.ring) >= 3:
                cx = sum(float(p[0]) for p in sf.ring) / len(sf.ring)
                cy = sum(float(p[1]) for p in sf.ring) / len(sf.ring)
                parts.append(label(cx, cy, str(sf.name)))
    # the scale bar at the bottom left, the north at the top right
    bar = _nice((x1 - x0) / 5 if x1 > x0 else span / 5)
    by = y0 - 1.8 * pad
    ink = colours["label"]
    parts.append(f'<path d="M{px(x0)} {py(by)}H{float(px(x0)) + bar:.3f}M{px(x0)} {float(py(by)) - 2 * pt:.3f}v{4 * pt:.3f}'
                 f'M{float(px(x0)) + bar:.3f} {float(py(by)) - 2 * pt:.3f}v{4 * pt:.3f}" stroke="{ink}" '
                 f'stroke-width="{0.9 * pt:.3f}" fill="none"/>')
    parts.append(f'<text x="{float(px(x0)) + bar + 3 * pt:.3f}" y="{float(py(by)) + 2.4 * pt:.3f}" '
                 f'font-family="Titillium Web" font-size="{7 * pt:.3f}" fill="{ink}">{escape(number(bar, 0))} m</text>')
    nx, ny = x1 + 1.7 * pad, y1
    tip = float(py(ny)) + 9 * pt
    parts.append(f'<path d="M{px(nx)} {tip + 22 * pt:.3f}V{tip:.3f}" stroke="{ink}" stroke-width="{0.9 * pt:.3f}"/>'
                 f'<path d="M{px(nx)} {tip - 1 * pt:.3f}l{-3 * pt:.3f} {7 * pt:.3f}h{6 * pt:.3f}Z" fill="{ink}"/>')
    parts.append(f'<text x="{px(nx)}" y="{tip - 3 * pt:.3f}" font-family="Titillium Web" font-weight="700" '
                 f'font-size="{8 * pt:.3f}" text-anchor="middle" fill="{ink}">N</text>')
    parts.append("</svg>")
    return "".join(parts).encode("utf-8")


def _png(rows: list[bytes], width: int) -> bytes:
    """An RGB PNG from its rows of bytes."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    raw = b"".join(b"\x00" + r for r in rows)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, len(rows), 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def carpet_png(grid, accent: str = "#1c6e8c") -> bytes:
    """The year as a picture: a column of pixels for each day, the hours from the bottom up; from white to the accent."""
    import numpy as np
    values = np.asarray(grid, dtype=float)
    top = float(values.max()) if values.size else 0.0
    share = (values / top if top > 0 else values)[::-1, :]
    rgb = np.array([int(accent[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)
    pixels = (255.0 + (rgb - 255.0) * share[:, :, None]).round().astype("uint8")
    return _png([row.tobytes() for row in pixels], pixels.shape[1])


@functools.lru_cache(maxsize=1024)
def formula_svg(tex: str, size: float = 11.0) -> bytes:
    """A formula as SVG, its letters as outlines, `size` points; kept by its text: the same come back at every report,
    and drawing one costs tens of milliseconds."""
    import matplotlib
    from matplotlib.font_manager import FontProperties
    from matplotlib.mathtext import math_to_image
    buf = io.BytesIO()
    with matplotlib.rc_context({"svg.fonttype": "path", "savefig.transparent": True}):
        math_to_image(f"${tex}$", buf, prop=FontProperties(size=size), dpi=72, format="svg", color=INK)
    return buf.getvalue()
