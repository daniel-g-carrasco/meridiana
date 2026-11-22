"""A small 3D preview for the dialogs (R282, study 22, 3.8): an axonometric view drawn with QPainter of a few
faces (walls, roofs, planes, structure), dashed guides and pills on the sides that speak («③ 12,00 m»). A drag
turns the view; a click on a pill or on its side opens a field in the pill. No Qt Quick 3D: a scene per dialog would cost hundreds of milliseconds, this one draws in about a
millisecond and is tested offscreen.

`Preview3D` holds the drawing and the projection; the Quick item of the dialogs (dialogs_preview.DialogPreview)
takes its methods and gives it the scene, the size, the font and the palette (the Widgets dialog it served first
was removed with the Widgets window, R542). It depends on the design system (`design`); the colours are its
palette's, so light and dark follow the application. Columns and beams of a
structure are `box()` faces.

World axes: x East, y North, z up, metres. The camera looks from `azimuth` (degrees clockwise from North: 225 is
from the South-West) and `elevation` degrees above the horizon; the projection is parallel."""

from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFontMetricsF, QPalette, QPen, QPolygonF

from meridiana.core.model import canopies
from meridiana.core.geometry import templates
from meridiana.i18n import _, number

from meridiana.gui.style import design

HIT = 6.0               # a side is clicked within this many pixels of its drawing (study 22, 3.10)
DRAG = 4.0              # a press that moves more than this turns the view instead of clicking
PILL_H = design.Button.SMALL[0]
HINT_FLAGS = int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap)


@dataclass
class Face:
    """A flat polygon in 3D: "wall" and "structure" are seen from their outer side only (their points run
    counter-clockwise seen from outside); "roof" and "plane" from both."""
    points: list
    kind: str = "wall"


@dataclass
class Guide:
    """A line that is not a surface: "ground" and "dashed" are dashed, "ridge" is drawn as an edge."""
    points: list
    kind: str = "dashed"


@dataclass
class Pill:
    """A measure on a side (a polyline in 3D): `text` as shown, `value` where the field starts, `number` the side's
    number (None for a measure that is not a side: a height, a slope)."""
    key: object
    points: list
    value: float
    text: str
    number: int | None = None
    unit: str = "m"
    editable: bool = True
    out: tuple | None = None            # the side's outer direction in 3D: the pill stands that way from it;
                                        # None, away from the middle of the drawing


def _ccw(ring) -> list:
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1], strict=True))
    return list(ring) if area >= 0 else list(reversed(ring))


def prism(ring, z0: float, z1: float, top: str = "roof") -> list[Face]:
    """The walls of a footprint from z0 to z1 and its flat top (`top` its kind)."""
    ring = _ccw([(float(p[0]), float(p[1])) for p in ring])
    faces = [Face([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)])
             for a, b in zip(ring, ring[1:] + ring[:1], strict=True)]
    faces.append(Face([(x, y, z1) for x, y in ring], top))
    return faces


def box(centre, size, z0: float = 0.0, turn: float = 0.0) -> list[Face]:
    """A column or a beam: a box of `size` (along x, along y, high) centred on `centre` in plan, from z0, turned
    `turn` degrees counter-clockwise."""
    c, s = math.cos(math.radians(turn)), math.sin(math.radians(turn))
    hx, hy = size[0] / 2, size[1] / 2
    ring = [(centre[0] + x * c - y * s, centre[1] + x * s + y * c) for x, y in ((-hx, -hy), (hx, -hy), (hx, hy),
                                                                              (-hx, hy))]
    return [Face(f.points, "structure") for f in prism(ring, z0, z0 + size[2])]


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def normal(points) -> tuple:
    """Newell's normal of a polygon (not unit)."""
    nx = ny = nz = 0.0
    for a, b in zip(points, points[1:] + points[:1], strict=True):
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    return (nx, ny, nz)


def _mix(a: QColor, b: QColor, t: float) -> QColor:
    return QColor.fromRgbF(a.redF() + (b.redF() - a.redF()) * t, a.greenF() + (b.greenF() - a.greenF()) * t,
                           a.blueF() + (b.blueF() - a.blueF()) * t)


class Preview3D:
    """The drawing of the preview, without a widget: the methods the Quick item takes (dialogs_preview)."""

    def pills(self) -> list[Pill]:
        return list(self._pills)

    def pill(self, key) -> Pill | None:
        return next((p for p in self._pills if p.key == key), None)


    # the projection

    def _axes(self):
        az, el = math.radians(self.azimuth), math.radians(self.elevation)
        d = (math.cos(el) * math.sin(az), math.cos(el) * math.cos(az), math.sin(el))       # towards the camera
        r = (-math.cos(az), math.sin(az), 0.0)
        u = (-math.sin(el) * math.sin(az), -math.sin(el) * math.cos(az), math.cos(el))
        return d, r, u

    def _all_points(self) -> list:
        pts = [p for f in self.faces for p in f.points] + [p for g in self.guides for p in g.points]
        return pts + [p for pill in self._pills for p in pill.points]

    def _fit(self):
        pts = self._all_points()
        if not pts:
            return (0.0, 0.0, 0.0), 1.0, QPointF(self.width() / 2, self.height() / 2)
        lo = [min(p[i] for p in pts) for i in range(3)]
        hi = [max(p[i] for p in pts) for i in range(3)]
        centre = tuple((a + b) / 2 for a, b in zip(lo, hi, strict=True))
        radius = max(math.dist(centre, p) for p in pts) or 1.0      # the same scale whichever way it is turned
        room = self._room()
        # room for the pills around the drawing: wider at the sides, where they are wider than tall
        scale = max(1.0, min(room.width() / 2 - 3.2 * PILL_H, room.height() / 2 - 1.4 * PILL_H)) / radius
        return centre, scale, room.center()

    def hint_rect(self) -> QRectF:
        """Where the text under the drawing goes: as many lines as the width of the preview asks for, its words never
        cut (R305: «non si leggono le scritte sotto»). Empty without a text."""
        if not self.hint:
            return QRectF()
        font = design.text_font(design.Text.CAPTION, self.font())
        width = max(1.0, self.width() - 2.0 * design.Space.M)
        high = QFontMetricsF(font).boundingRect(QRectF(0, 0, width, 1000.0), HINT_FLAGS, self.hint).height()
        return QRectF(design.Space.M, self.height() - high - design.Space.XS, width, high)

    def _room(self) -> QRectF:
        bottom = self.hint_rect().height() + design.Space.S if self.hint else 0
        return QRectF(0, 0, self.width(), self.height() - bottom)

    def project(self, point) -> QPointF:
        """Where a point of the world is drawn, in the widget's pixels."""
        centre, scale, mid = self._fit()
        _d, r, u = self._axes()
        p = _sub(point, centre)
        return QPointF(mid.x() + _dot(p, r) * scale, mid.y() - _dot(p, u) * scale)

    def _projector(self):
        centre, scale, mid = self._fit()
        d, r, u = self._axes()

        def at(point):
            p = _sub(point, centre)
            return QPointF(mid.x() + _dot(p, r) * scale, mid.y() - _dot(p, u) * scale)

        def depth(point):
            return _dot(_sub(point, centre), d)
        return at, depth, d, mid

    # drawing

    def _colours(self) -> dict:
        pal = self.palette()
        base, ink = pal.color(QPalette.ColorRole.Base), pal.color(QPalette.ColorRole.Text)
        accent = pal.color(QPalette.ColorRole.Accent)
        return {"base": base, "ink": ink, "line": pal.color(QPalette.ColorRole.Mid), "accent": accent,
                "muted": pal.color(QPalette.ColorRole.PlaceholderText), "edge": _mix(ink, base, 0.2),
                "wall": _mix(base, ink, 0.07), "wall2": _mix(base, ink, 0.16), "roof": _mix(base, accent, 0.22),
                "under": _mix(base, accent, 0.10), "structure": _mix(base, ink, 0.45)}

    def drawn(self) -> list:
        """The faces in the order they are painted, (layer, depth, face, normal, facing) each: by layers, the far
        first within each. The backs of walls and boxes are left out; a plane seen from under hides nothing under
        it, so it goes before the columns and beams (R281), and over them when seen from above."""
        _at, depth, d, _mid = self._projector()
        order = {"structure": 0, "wall": 1, "roof": 2, "plane": 2}
        out = []
        for face in self.faces:
            n = normal(face.points)
            facing = _dot(n, d)
            if face.kind in ("wall", "structure") and facing <= 1e-9:
                continue                        # its back: hidden by the faces in front
            layer = order.get(face.kind, 1)
            if face.kind in ("roof", "plane") and (facing if n[2] >= 0 else -facing) < 0:
                layer = -1
            out.append((layer, sum(depth(p) for p in face.points) / len(face.points), face, n, facing))
        return sorted(out, key=lambda item: (item[0], item[1]))


    @staticmethod
    def _polyline(painter, pts, pen) -> None:
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolyline(QPolygonF(pts))

    @staticmethod
    def _anchor(pill: Pill) -> tuple:
        """The middle of the side by its length, in 3D."""
        pts = pill.points
        lengths = [math.dist(a, b) for a, b in zip(pts, pts[1:], strict=False)]
        half = sum(lengths) / 2
        for (a, b), length in zip(zip(pts, pts[1:], strict=False), lengths, strict=True):
            if half <= length and length > 0:
                t = half / length
                return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
            half -= length
        return tuple(pts[0])

    @staticmethod
    def pill_size(pill: Pill, font) -> tuple[float, float]:
        """The size of the pill as M.LengthPill lays it out (Controls/PillPlace.js, width and height): the side's
        number in a disc as high as the line less its margins, or the margin; the text; the margin (R555 12: the
        measures of the preview are the plan's sides' pills, drawn by the QML over the drawing)."""
        metrics = QFontMetricsF(font)
        line = metrics.height() + 2 * design.Annotation.LABEL_PAD
        start = design.Space.XXS + (line - 2 * design.Space.XXS) + design.Space.XS if pill.number is not None             else design.Space.S
        return start + metrics.horizontalAdvance(pill.text) + design.Space.S, line

    def _layout_pills(self, at, mid, font) -> dict:
        rects: dict = {}
        for pill in self._pills:
            middle = self._anchor(pill)
            anchor = at(middle)
            away = (at(tuple(m + o for m, o in zip(middle, pill.out, strict=True))) - anchor
                    if pill.out is not None else anchor - mid)
            length = math.hypot(away.x(), away.y())
            away = QPointF(away.x() / length, away.y() / length) if length > 1 else QPointF(-1, 0)
            width, high = self.pill_size(pill, font)
            rect = QRectF(0, 0, width, high)
            push = design.Space.S + 0.5 * (abs(away.x()) * width + abs(away.y()) * high)
            room = self._room().adjusted(design.Space.XS, design.Space.XS, -design.Space.XS, -design.Space.XS)
            across = QPointF(-away.y(), away.x())
            # off the pills already placed, inside the view: further out first, then aside
            tries = [away * (push + k * high * 0.75) for k in range(4)]
            tries += [away * push + across * (sign * k * high) for k in (1, 2, 3) for sign in (1, -1)]
            for shift in tries:
                rect.moveCenter(anchor + shift)
                rect.moveLeft(min(max(rect.left(), room.left()), room.right() - rect.width()))
                rect.moveTop(min(max(rect.top(), room.top()), room.bottom() - rect.height()))
                if not any(rect.intersects(other) for other in rects.values()):
                    break
            else:
                rect.moveCenter(anchor + tries[0])    # nowhere free: on its side, over the others
            rects[pill.key] = QRectF(rect)
        return rects

    def _place_pills(self, at, mid, lit) -> list[dict]:
        """Where the QML draws the pills (M.LengthPill), as records: the key (a string), the box, the text, the side's
        number, the unit and the value of the field that opens in it, whether it is lit."""
        self._rects = self._layout_pills(at, mid, design.text_font(design.Text.CAPTION, self.font()))
        out = []
        for pill in self._pills:
            rect = self._rects[pill.key]
            out.append({"key": str(pill.key), "x": rect.x(), "y": rect.y(), "width": rect.width(),
                        "height": rect.height(), "text": pill.text,
                        "badge": "" if pill.number is None else str(pill.number), "unit": pill.unit,
                        "value": number(pill.value, 1 if pill.unit == "°" else 2), "editable": pill.editable,
                        "lit": pill.key in lit})
        return out

    def _draw_north(self, painter, c) -> None:
        """A small arrow towards North in the top right corner: the shape goes on the plan as it stands here, with
        its turn, and North is what says which way it will lie there (the plan has North up), whichever way the
        preview was dragged. Kept for that (R305), and the dialogs' text says so."""
        if not self.faces and not self.guides:
            return
        _d, r, u = self._axes()
        x, y = r[1], -u[1]                      # North (0, 1, 0) on the screen
        length = math.hypot(x, y) or 1.0
        x, y = x / length, y / length
        centre = QPointF(self.width() - design.Space.XL - design.Space.XS, design.Space.XL + design.Space.XS)
        tip = centre + QPointF(x, y) * 9
        tail = centre - QPointF(x, y) * 9
        painter.setPen(QPen(c["muted"], design.Line.HAIR))
        painter.drawLine(tail, tip)
        side = QPointF(-y, x) * 3
        painter.drawLine(tip, tip - QPointF(x, y) * 4 + side)
        painter.drawLine(tip, tip - QPointF(x, y) * 4 - side)
        painter.setFont(design.text_font(design.Text.CAPTION, self.font()))
        label = tip + QPointF(x, y) * 8
        painter.drawText(QRectF(label.x() - 8, label.y() - 8, 16, 16), Qt.AlignmentFlag.AlignCenter, "N")

    # pointing

    def key_at(self, pos: QPointF):
        """The key of the pill, or of the side, under `pos` (pills first), or None."""
        if not self._rects:
            at, _depth, _d, mid = self._projector()
            self._rects = self._layout_pills(at, mid, design.text_font(design.Text.CAPTION, self.font()))
        for pill in reversed(self._pills):
            rect = self._rects.get(pill.key)
            if rect is not None and rect.contains(pos):
                return pill.key
        at = self._projector()[0]
        best, near = None, HIT
        for pill in self._pills:
            pts = [at(p) for p in pill.points]
            for a, b in zip(pts, pts[1:], strict=False):
                gap = _distance(pos, a, b)
                if gap <= near:
                    best, near = pill.key, gap
        return best


    # the field in the pill


def _distance(p: QPointF, a: QPointF, b: QPointF) -> float:
    dx, dy = b.x() - a.x(), b.y() - a.y()
    span = dx * dx + dy * dy
    t = 0.0 if span == 0 else max(0.0, min(1.0, ((p.x() - a.x()) * dx + (p.y() - a.y()) * dy) / span))
    return math.hypot(p.x() - a.x() - t * dx, p.y() - a.y() - t * dy)


# the scenes of the dialogs: the building from a template and the parking canopy (they were the Widgets dialogs'
# own, template_dialog.py and canopy_dialog.py, until R542)

TEMPLATE_HEIGHT = 6.0       # the height the building from a template is given (m): drawn, not asked


def side_measure(kind: str, side: int, value: float, m: dict) -> tuple[str, float]:
    """The measure of the template `kind` to set, and its value, so that its side `side` (from 1, as numbered on
    the outline) is `value` long, the other measures `m` kept. ValueError, said in words, when no value of that
    measure makes the side so long."""
    if kind == "rectangle":
        return ("width" if side in (1, 3) else "depth"), value
    if kind == "L":
        a, b = m["arm_south"], m["arm_west"]
        return {1: ("width", value), 2: ("arm_south", value), 3: ("width", b + value), 4: ("depth", a + value),
                5: ("arm_west", value), 6: ("depth", value)}[side]
    if kind == "T":
        a, b = m["bar"], m["stem"]
        return {1: ("width", value), 2: ("bar", value), 3: ("width", b + 2 * value), 4: ("depth", a + value),
                5: ("stem", value), 6: ("depth", a + value), 7: ("width", b + 2 * value), 8: ("bar", value)}[side]
    if kind == "U":
        a, b = m["base"], m["arm"]
        return {1: ("width", value), 2: ("depth", value), 3: ("arm", value), 4: ("depth", a + value),
                5: ("width", 2 * b + value), 6: ("depth", a + value), 7: ("arm", value), 8: ("depth", value)}[side]
    if kind == "trapezoid":
        if side in (1, 3):
            return ("base" if side == 1 else "top"), value
        run = (m["offset"] + m["top"] - m["base"]) if side == 2 else m["offset"]    # the slanted side's run
        if value <= abs(run):
            raise ValueError(_("A slanted side must be longer than its run along the base, {run} m").format(
                run=number(abs(run))))
        return "depth", math.sqrt(value * value - run * run)
    raise ValueError(f"no template {kind!r}")


def sides_of(kind: str, key: str) -> set:
    """The sides of the template whose length the measure `key` sets (lit when its field is pointed)."""
    m = templates.defaults(kind)
    out = set()
    for side in range(1, len(templates.footprint(kind)) + 1):
        try:
            if side_measure(kind, side, 1.0, m)[0] == key:
                out.add(side)
        except ValueError:
            continue                        # a slanted side shorter than its run: it still sets the depth
    if kind == "trapezoid" and key == "depth":
        out |= {2, 4}
    return out


def template_scene(preview, turn: float, ring) -> None:
    """The building as it will be: the outline turned, TEMPLATE_HEIGHT high, with a pill on each side of its top."""
    if ring is None:
        preview.show_scene()
        return
    placed = templates.placed(ring, (0.0, 0.0), turn)
    n = len(placed)
    pills = []
    for i in range(n):
        (ax, ay), (bx, by) = placed[i], placed[(i + 1) % n]
        length = math.hypot(bx - ax, by - ay)
        out = ((by - ay) / length, (ax - bx) / length, 0.0) if length else None   # outward: the ring is CCW
        pills.append(Pill(i + 1, [(ax, ay, TEMPLATE_HEIGHT), (bx, by, TEMPLATE_HEIGHT)], length,
                          f"{number(length)} m", i + 1, out=out))
    preview.show_scene(prism(placed, 0.0, TEMPLATE_HEIGHT), (), pills)


def canopy_scene(preview, ring, spec, b) -> None:
    """The parking canopy as canopies.structure makes it: its planes, columns and beams, the ground's outline, the
    ridge of a double row; pills on the four sides, the height under the low edge and the slope."""
    pitches = b.pitches()
    faces = [Face(p.corners_3d(), "plane") for p in pitches]
    for s in canopies.structure(b):
        faces += [Face(f.points, "structure") for f in prism(s["ring"], s["z0"], s["z1"])]
    ring = [tuple(q) for q in ring]
    f0, f1, f2, f3 = ((x, y, canopies.roof_at(pitches, x, y)) for x, y in ring)
    guides = [Guide([(x, y, 0.0) for x, y in ring + ring[:1]], "ground")]
    east, west = [f1, f2], [f3, f0]
    high_mid = tuple((f3[i] + f2[i]) / 2 for i in range(3))
    if spec.rows == 2 and spec.tilt > 0:
        ridge = [(x, y, canopies.roof_at(pitches, x, y)) for x, y in
                 (((f1[0] + f2[0]) / 2, (f1[1] + f2[1]) / 2), ((f0[0] + f3[0]) / 2, (f0[1] + f3[1]) / 2))]
        guides.append(Guide(ridge, "ridge"))
        east, west = [f1, ridge[0], f2], [f3, ridge[1], f0]
        high_mid = tuple((ridge[0][i] + ridge[1][i]) / 2 for i in range(3))
    length, depth = spec.stalls * spec.bay_width, spec.rows * spec.depth
    low_mid = tuple((f0[i] + f1[i]) / 2 for i in range(3))
    text_m = f"{number(length)} m"
    pills = [Pill(1, [f0, f1], length, text_m, 1), Pill(2, east, depth, f"{number(depth)} m", 2),
             Pill(3, [f2, f3], length, text_m, 3), Pill(4, west, depth, f"{number(depth)} m", 4),
             Pill('clearance', [(f0[0], f0[1], 0.0), f0], spec.clearance, f"{number(spec.clearance)} m"),
             Pill('tilt', [low_mid, high_mid], spec.tilt, f"{number(spec.tilt, 1)}°", unit="°")]
    preview.show_scene(faces, guides, pills)
