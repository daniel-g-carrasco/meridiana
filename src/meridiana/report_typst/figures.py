"""What the report draws as files, without Qt: the plan of the modules as SVG (vector in the PDF, fonts of the program),
the carpet of the hours as a small PNG, the formulas as SVG through matplotlib's mathtext (no TeX needed)."""

from __future__ import annotations

import functools
import io
import math
import struct
import zlib
from dataclasses import dataclass, field
from xml.sax.saxutils import escape, quoteattr

from ..i18n import number

INK = "#1a1a1a"
# R460: the report's palette has no blue (look.py): the sub-fields' outline a warm grey, the modules anthracite, and
# among the strings' hues the blue, violet, teal and slate of before become anthracite, stone, oxblood and grey
PLAN = {"building": "#f7f7f4", "building_edge": "#6e6a66", "subfield": "#8f8a80", "exclusion": "#f7d3e3",
        "exclusion_edge": "#c4467f", "module": "#3b3a37", "module_edge": "#ffffff", "label": "#24211d",
        "free": "#c9c5bd"}
STRING_HUES = ("#3b3a37", "#d9822b", "#3a9a5b", "#c4467f", "#a39e95", "#8a6d3b", "#7a2e2e", "#b8a31f",
               "#77736c", "#d1495b")
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
                f'<text x="{px(x)}" y="{float(py(y)) + 0.35 * fs:.3f}" font-family="IBM Plex Sans" font-size="{fs:.3f}" '
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
                 f'font-family="IBM Plex Sans" font-size="{7 * pt:.3f}" fill="{ink}">{escape(number(bar, 0))} m</text>')
    nx, ny = x1 + 1.7 * pad, y1
    tip = float(py(ny)) + 9 * pt
    parts.append(f'<path d="M{px(nx)} {tip + 22 * pt:.3f}V{tip:.3f}" stroke="{ink}" stroke-width="{0.9 * pt:.3f}"/>'
                 f'<path d="M{px(nx)} {tip - 1 * pt:.3f}l{-3 * pt:.3f} {7 * pt:.3f}h{6 * pt:.3f}Z" fill="{ink}"/>')
    parts.append(f'<text x="{px(nx)}" y="{tip - 3 * pt:.3f}" font-family="IBM Plex Sans" font-weight="700" '
                 f'font-size="{8 * pt:.3f}" text-anchor="middle" fill="{ink}">N</text>')
    parts.append("</svg>")
    return "".join(parts).encode("utf-8")


# R436: the plan of the plant, the strings with their names, where they go and the optimizers

MIN_MODULE_MM = 2.2             # a module's short side on A4 below this: a sheet for each sub-field
OPTIMIZER = "#3a3631"             # the optimizers: near black, not the ink of the labels


@dataclass
class Sheet:
    """A sheet of the plant's plan: its sub-fields' names ("" for all), its SVG, its strings (plant.String), how many
    optimizers and how many modules in no string it shows."""
    title: str
    svg: bytes
    strings: list = field(default_factory=list)
    optimizers: int = 0
    free: int = 0


def _ink(hue: str, share: float = 0.45) -> str:
    """`hue` darkened by `share` towards black: the line and the name of a string over its own modules."""
    rgb = [int(hue[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(c * (1 - share)):02x}" for c in rgb)


def string_hues(plant, results: dict) -> dict:
    """A hue for each string of `plant` (by its label), as the plan of Impianto gives them (string_paths.colours: its
    own from its first module, unless a string touching it has it), from the hues that read on white paper."""
    from .. import string_paths
    index: dict = {}
    quads = []
    for sfid, r in results.items():
        for pm in (getattr(r, "modules", None) or []):
            index[(sfid, pm.key)] = len(quads)
            quads.append(pm.corners)
    strings = list(getattr(plant, "strings", None) or [])
    if not quads or not strings:
        return {}
    router = string_paths.Router(quads)
    orders = [[index[(sf, k)] for sf, k, _c in s.modules if (sf, k) in index] for s in strings]
    seeds = [zlib.crc32(f"{s.modules[0][0]}/{s.modules[0][1]}".encode()) if s.modules else i
             for i, s in enumerate(strings)]
    chosen = string_paths.colours(orders, router, len(STRING_HUES), seeds)
    return {s.label: STRING_HUES[c] for s, c in zip(strings, chosen, strict=True)}


def plant_sheets(project, results: dict, plant, width_mm: float = 174.0, colours: dict | None = None) -> list[Sheet]:
    """The plan of the plant on one sheet, or one sheet for each sub-field when on one the modules would be too small to
    read on A4 (MIN_MODULE_MM); printed on A3 a sheet is the same drawing, larger."""
    laid = [sf for sf in project.subfields if getattr(results.get(sf.id), "modules", None)]
    if not laid or plant is None or not getattr(plant, "strings", None):
        return []
    hues = string_hues(plant, results)
    whole = _sheet(project, results, plant, laid, hues, width_mm, colours)
    if whole is None:
        return []
    if len(laid) == 1 or whole[1] >= MIN_MODULE_MM:
        return [whole[0]]
    return [made[0] for made in (_sheet(project, results, plant, [sf], hues, width_mm, colours) for sf in laid)
            if made is not None]


def _sheet(project, results, plant, laid, hues, width_mm, colours):
    """One sheet for the sub-fields `laid`: (Sheet, a module's short side on the paper in mm), None without modules."""
    from .. import string_paths
    colours = {**PLAN, **(colours or {})}
    mine = {sf.id for sf in laid}
    modules = [(sf.id, pm) for sf in laid for pm in results[sf.id].modules]
    if not modules:
        return None
    pts = [p for _s, pm in modules for p in pm.corners] + [p for sf in laid for p in sf.ring]
    xs, ys = [float(p[0]) for p in pts], [float(p[1]) for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    span = max(x1 - x0, y1 - y0, 1.0)
    pad = 0.04 * span
    left, right = x0 - pad, x1 + 3.0 * pad
    bottom, top = y0 - 3.2 * pad, y1 + pad
    width, height = right - left, top - bottom
    pt = width / (width_mm * PT_PER_MM)                     # a point of the paper in metres of the plan
    index = {(sf, pm.key): n for n, (sf, pm) in enumerate(modules)}
    quads = [pm.corners for _s, pm in modules]
    router = string_paths.Router(quads)
    side_mm = router.size / pt / PT_PER_MM

    def px(x: float) -> float:
        return float(x) - left

    def py(y: float) -> float:
        return top - float(y)

    def path(points, close: bool = True) -> str:
        return "M" + "L".join(f"{px(x):.3f} {py(y):.3f}" for x, y in points) + ("Z" if close else "")

    def rings(items, fill, stroke, thick, dash="") -> str:
        d = "".join(path(r) for r in items if len(r) >= 3)
        if not d:
            return ""
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{thick:.3f}"{extra}/>'

    strings = [s for s in sorted(plant.strings, key=lambda s: (s.inverter, s.mppt, s.index))
               if any(sf in mine for sf, _k, _c in s.modules)]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.3f} {height:.3f}" '
             f'width="{width_mm:.2f}mm" height="{width_mm * height / width:.2f}mm">']
    parts.append(rings([b.footprint for b in project.buildings], colours["building"], colours["building_edge"], 0.7 * pt))
    parts.append(rings([e.ring for e in project.exclusions], colours["exclusion"], colours["exclusion_edge"], 0.5 * pt))
    hue_of = {(sf, k): hues.get(s.label, STRING_HUES[0]) for s in strings for sf, k, _c in s.modules}
    by_colour: dict = {}
    free = 0
    for sf, pm in modules:
        colour = hue_of.get((sf, pm.key))
        if colour is None:
            colour, free = colours["free"], free + 1
        by_colour.setdefault(colour, []).append(pm.corners)
    for colour, polygons in by_colour.items():
        parts.append(rings(polygons, colour, colours["module_edge"], 0.15 * pt))
    parts.append(rings([sf.ring for sf in laid], "none", colours["subfield"], 0.8 * pt, f"{4 * pt:.3f} {2 * pt:.3f}"))
    # the line of each string over its modules (dashed where it jumps) and its two ends, where the cables to its input
    # start: the first end full, the last one hollow
    ends: list = []
    for s in strings:
        order = [index[(sf, k)] for sf, k, _c in s.modules if (sf, k) in index]
        if not order:
            continue
        ink = _ink(hues.get(s.label, STRING_HUES[0]))
        solid, jumped = [], []
        for points, jump in router.legs(order):
            (jumped if jump else solid).append(path(points, close=False))
        if solid:
            parts.append(f'<path d="{"".join(solid)}" fill="none" stroke="{ink}" stroke-width="{0.55 * pt:.3f}" '
                         f'stroke-linecap="round"/>')
        if jumped:
            parts.append(f'<path d="{"".join(jumped)}" fill="none" stroke="{ink}" stroke-width="{0.55 * pt:.3f}" '
                         f'stroke-dasharray="{2 * pt:.3f} {1.2 * pt:.3f}"/>')
        a, b = router.centres[order[0]], router.centres[order[-1]]
        r = 1.1 * pt
        parts.append(f'<circle cx="{px(a[0]):.3f}" cy="{py(a[1]):.3f}" r="{r:.3f}" fill="{ink}"/>'
                     f'<circle cx="{px(b[0]):.3f}" cy="{py(b[1]):.3f}" r="{r:.3f}" fill="#ffffff" stroke="{ink}" '
                     f'stroke-width="{0.5 * pt:.3f}"/>')
        ends.append((s, order, ink))
    # the optimizers (R424): one on each group of modules, where the plan of Impianto draws them
    from ..energy import optimizers as opt
    optimizers = 0
    units = {u.number: u for u in getattr(plant, "units", None) or []}
    for s in strings:
        u = units.get(s.inverter)
        choice = getattr(u, "choice", None) if u is not None and getattr(u, "optimized", False) else None
        if choice is None:
            continue
        order = [index.get((sf, k), -1) for sf, k, _c in s.modules]
        try:
            groups = opt.module_groups(order, choice.per, list(s.optimizer_group_sizes or []) or None)
        except ValueError:
            continue
        groups = [g for g in ([i for i in g if i >= 0] for g in groups) if g]
        for x, y, ux, uy, size in string_paths.optimizer_units(quads, groups):
            h = max(size, 1.4 * pt) / 2
            w = 1.6 * h
            corners = [(x + ux * w - uy * h, y + uy * w + ux * h), (x - ux * w - uy * h, y - uy * w + ux * h),
                       (x - ux * w + uy * h, y - uy * w - ux * h), (x + ux * w + uy * h, y + uy * w - ux * h)]
            parts.append(f'<path d="{path(corners)}" fill="{OPTIMIZER}" stroke="#ffffff" '
                         f'stroke-width="{0.25 * pt:.3f}"/>')
            optimizers += 1
    # the names, each where it covers no other: over its first module, else its last, else half way
    placed: list = []
    fs = max(4.6, min(6.2, 2.2 * side_mm)) * pt
    for s, order, ink in ends:
        text = str(s.label)
        w, h = 0.56 * fs * len(text) + 1.0 * fs, 1.45 * fs
        spots = [(float(router.centres[i][0]), float(router.centres[i][1]))
                 for i in (order[0], order[-1], order[len(order) // 2])]
        boxes = [(px(cx) - w / 2, py(cy) - h - 1.2 * pt, w, h) for cx, cy in spots]
        box = next((c for c in boxes if not any(_overlap(c, other) for other in placed)), boxes[0])
        placed.append(box)
        bx, by, bw, bh = box
        parts.append(f'<rect x="{bx:.3f}" y="{by:.3f}" width="{bw:.3f}" height="{bh:.3f}" rx="{0.4 * fs:.3f}" '
                     f'fill="#ffffff" fill-opacity="0.92" stroke="{ink}" stroke-width="{0.35 * pt:.3f}"/>'
                     f'<text x="{bx + bw / 2:.3f}" y="{by + bh / 2 + 0.36 * fs:.3f}" font-family="IBM Plex Sans" '
                     f'font-size="{fs:.3f}" font-weight="700" text-anchor="middle" fill="{ink}">{escape(text)}</text>')
    _scale_and_north(parts, (x0, x1, y0, y1), pad, pt, span, px, py, colours["label"])
    parts.append("</svg>")
    title = laid[0].name if len(laid) == 1 and len(project.subfields) > 1 else ""
    return Sheet(title, "".join(parts).encode("utf-8"), strings, optimizers, free), side_mm


def _overlap(a, b) -> bool:
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def _scale_and_north(parts, box, pad, pt, span, px, py, ink) -> None:
    """The scale bar under the bottom left corner of `box` (x0, x1, y0, y1), the north at its top right."""
    x0, x1, y0, y1 = box
    bar = _nice((x1 - x0) / 5 if x1 > x0 else span / 5)
    by = y0 - 1.8 * pad
    parts.append(f'<path d="M{px(x0):.3f} {py(by):.3f}H{px(x0) + bar:.3f}M{px(x0):.3f} {py(by) - 2 * pt:.3f}'
                 f'v{4 * pt:.3f}M{px(x0) + bar:.3f} {py(by) - 2 * pt:.3f}v{4 * pt:.3f}" stroke="{ink}" '
                 f'stroke-width="{0.9 * pt:.3f}" fill="none"/>')
    parts.append(f'<text x="{px(x0) + bar + 3 * pt:.3f}" y="{py(by) + 2.4 * pt:.3f}" font-family="IBM Plex Sans" '
                 f'font-size="{7 * pt:.3f}" fill="{ink}">{escape(number(bar, 0))} m</text>')
    nx = x1 + 1.7 * pad
    tip = py(y1) + 9 * pt
    parts.append(f'<path d="M{px(nx):.3f} {tip + 22 * pt:.3f}V{tip:.3f}" stroke="{ink}" stroke-width="{0.9 * pt:.3f}"/>'
                 f'<path d="M{px(nx):.3f} {tip - 1 * pt:.3f}l{-3 * pt:.3f} {7 * pt:.3f}h{6 * pt:.3f}Z" fill="{ink}"/>')
    parts.append(f'<text x="{px(nx):.3f}" y="{tip - 3 * pt:.3f}" font-family="IBM Plex Sans" font-weight="700" '
                 f'font-size="{8 * pt:.3f}" text-anchor="middle" fill="{ink}">N</text>')


def _png(rows: list[bytes], width: int) -> bytes:
    """An RGB PNG from its rows of bytes."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    raw = b"".join(b"\x00" + r for r in rows)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, len(rows), 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def carpet_png(grid, accent: str = "#3b3a37") -> bytes:
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
