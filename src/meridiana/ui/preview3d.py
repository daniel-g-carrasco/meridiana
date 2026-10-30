"""A small 3D preview for the dialogs (R282, study 22, 3.8): an axonometric view drawn with QPainter of a few
faces (walls, roofs, planes, structure), dashed guides and pills on the sides that speak («③ 12,00 m»). A drag
turns the view; a click on a pill or on its side opens a field in the pill: Enter sends the value (`edited`), Esc
gives up. No Qt Quick 3D: a scene per dialog would cost hundreds of milliseconds, this one draws in about a
millisecond and is tested offscreen.

The widget knows nothing of the program: the caller gives the scene (`show_scene`), the texts (`hint`), how a
number is written (`number`) and read (`parse`). It depends on the design system (`design`) and on the theme's
`mark_problem`; the colours are its palette's, so light and dark follow the application. Columns and beams of a
structure are `box()` faces.

World axes: x East, y North, z up, metres. The camera looks from `azimuth` (degrees clockwise from North: 225 is
from the South-West) and `elevation` degrees above the horizon; the projection is parallel."""

from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFontMetricsF, QPainter, QPalette, QPen, QPolygonF
from PySide6.QtWidgets import QLineEdit, QWidget

from . import design
from .theme import mark_problem

HIT = 6.0               # a side is clicked within this many pixels of its drawing (study 22, 3.10)
DRAG = 4.0              # a press that moves more than this turns the view instead of clicking
PILL_H = design.Button.SMALL[0]
EDITOR_W = 96


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


class _Editor(QLineEdit):
    """The field in a pill: Enter and Esc are its own, so that the dialog neither closes nor accepts."""

    def __init__(self, owner: "Preview3D"):
        super().__init__(owner)
        self.owner = owner
        self.hide()

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            event.accept()
            self.owner.commit()
            return
        if event.key() == Qt.Key.Key_Escape:
            event.accept()
            self.owner.close_editor()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        if event.reason() != Qt.FocusReason.PopupFocusReason and self.isVisible():
            self.owner.close_editor()       # a click elsewhere gives up, as Esc


class Preview3D(QWidget):
    edited = Signal(object, float)      # a pill's key and the value written in it
    hovered = Signal(object)            # the key of the pill or side under the pointer, None off them

    def __init__(self, parent=None, number=None, parse=None):
        super().__init__(parent)
        self.number = number or (lambda value, decimals=2: f"{value:.{decimals}f}")
        self.parse = parse or (lambda text, unit: float(text.replace(unit, "").replace(",", ".").strip()))
        self.faces: list[Face] = []
        self.guides: list[Guide] = []
        self._pills: list[Pill] = []
        self.azimuth, self.elevation = 225.0, 30.0
        self.hint = ""
        self.highlight: set = set()             # keys lit from outside (the field under the pointer)
        self.hover = None
        self.editing = None                     # the key of the pill whose field is open
        self._refusal: str | None = None
        self._press: QPointF | None = None
        self._dragging = False
        self._rects: dict = {}                  # key: the pill's rectangle as last drawn
        self.editor = _Editor(self)
        self.setMouseTracking(True)
        self.setMinimumSize(260, 200)

    # the scene

    def show_scene(self, faces=(), guides=(), pills=()) -> None:
        """What to draw; a field open on a pill that is still there stays open."""
        self.faces, self.guides, self._pills = list(faces), list(guides), list(pills)
        if self.editing is not None and self.pill(self.editing) is None:
            self.close_editor()
        self.update()
        if self.editing is not None:
            self._place_editor()

    def pills(self) -> list[Pill]:
        return list(self._pills)

    def pill(self, key) -> Pill | None:
        return next((p for p in self._pills if p.key == key), None)

    def set_highlight(self, keys) -> None:
        keys = set(keys or ())
        if keys != self.highlight:
            self.highlight = keys
            self.update()

    def turn(self, azimuth: float, elevation: float | None = None) -> None:
        self.azimuth = azimuth % 360
        if elevation is not None:
            self.elevation = min(80.0, max(10.0, elevation))
        self.update()
        if self.editing is not None:
            self._place_editor()

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

    def _room(self) -> QRectF:
        bottom = design.Space.XL if self.hint else 0
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

    def paintEvent(self, _event) -> None:
        c = self._colours()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        frame = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(c["line"], design.Line.HAIR))
        painter.setBrush(c["base"])
        painter.drawRoundedRect(frame, design.Radius.VIEW, design.Radius.VIEW)
        at, depth, d, mid = self._projector()
        lit = self.highlight | {k for k in (self.hover, self.editing) if k is not None}
        for guide in self.guides:
            if guide.kind in ("ground", "dashed"):
                self._polyline(painter, [at(p) for p in guide.points], QPen(c["muted"], 1, Qt.PenStyle.DashLine))
        order = {"structure": 0, "wall": 1, "roof": 2, "plane": 2}
        drawn = []
        for face in self.faces:
            n = normal(face.points)
            facing = _dot(n, d)
            if face.kind in ("wall", "structure") and facing <= 1e-9:
                continue                        # its back: hidden by the faces in front
            drawn.append((order.get(face.kind, 1), sum(depth(p) for p in face.points) / len(face.points), face, n,
                          facing))
        for _layer, _depth, face, n, facing in sorted(drawn, key=lambda item: (item[0], item[1])):
            if face.kind in ("wall", "structure"):
                length = math.hypot(n[0], n[1]) or 1.0
                light = (n[0] * -0.6 + n[1] * -0.8) / length      # the faces turned South-West are the lighter
                fill = c["structure"] if face.kind == "structure" else _mix(c["wall"], c["wall2"], 0.5 - light / 2)
            else:
                fill = c["roof"] if (facing if n[2] >= 0 else -facing) >= 0 else c["under"]     # its top or under
            painter.setPen(QPen(c["edge"], design.Line.HAIR))
            painter.setBrush(fill)
            painter.drawPolygon(QPolygonF([at(p) for p in face.points]))
        for guide in self.guides:
            if guide.kind == "ridge":
                self._polyline(painter, [at(p) for p in guide.points], QPen(c["edge"], design.Line.FOCUS))
        for pill in self._pills:
            if pill.key in lit:
                self._polyline(painter, [at(p) for p in pill.points], QPen(c["accent"], design.Line.FOCUS))
        self._draw_pills(painter, at, mid, c, lit)
        self._draw_north(painter, c)
        if self.hint:
            painter.setFont(design.text_font(design.Text.CAPTION, self.font()))
            painter.setPen(c["muted"])
            painter.drawText(QRectF(0, self.height() - design.Space.XL - design.Space.XS, self.width(),
                                    design.Space.XL), Qt.AlignmentFlag.AlignCenter, self.hint)
        painter.end()

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

    def _layout_pills(self, at, mid, font) -> dict:
        metrics = QFontMetricsF(font)
        rects: dict = {}
        for pill in self._pills:
            middle = self._anchor(pill)
            anchor = at(middle)
            away = (at(tuple(m + o for m, o in zip(middle, pill.out, strict=True))) - anchor
                    if pill.out is not None else anchor - mid)
            length = math.hypot(away.x(), away.y())
            away = QPointF(away.x() / length, away.y() / length) if length > 1 else QPointF(-1, 0)
            width = metrics.horizontalAdvance(pill.text) + 2 * design.Space.M
            if pill.number is not None:
                width += PILL_H - design.Space.XS
            rect = QRectF(0, 0, width, PILL_H)
            push = design.Space.S + 0.5 * (abs(away.x()) * width + abs(away.y()) * PILL_H)
            room = self._room().adjusted(design.Space.XS, design.Space.XS, -design.Space.XS, -design.Space.XS)
            across = QPointF(-away.y(), away.x())
            # off the pills already placed, inside the view: further out first, then aside
            tries = [away * (push + k * PILL_H * 0.75) for k in range(4)]
            tries += [away * push + across * (sign * k * PILL_H) for k in (1, 2, 3) for sign in (1, -1)]
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

    def _draw_pills(self, painter, at, mid, c, lit) -> None:
        font = design.text_font(design.Text.SECONDARY, self.font())
        painter.setFont(font)
        self._rects = self._layout_pills(at, mid, font)
        for pill in self._pills:
            if pill.key == self.editing:
                continue                        # the field stands there
            rect = self._rects[pill.key]
            on = pill.key in lit
            painter.setPen(QPen(c["accent"] if on else c["line"], design.Line.HAIR))
            painter.setBrush(c["base"])
            painter.drawRoundedRect(rect, PILL_H / 2, PILL_H / 2)
            text_rect = QRectF(rect).adjusted(design.Space.M, 0, -design.Space.M, 0)
            if pill.number is not None:
                disc = QRectF(rect.left() + 3, rect.top() + 3, PILL_H - 6, PILL_H - 6)
                painter.setPen(QPen(c["accent"] if on else c["muted"], design.Line.HAIR))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(disc)
                small = design.text_font(design.Text.CAPTION, self.font())
                painter.setFont(small)
                painter.drawText(disc, Qt.AlignmentFlag.AlignCenter, str(pill.number))
                painter.setFont(font)
                text_rect.setLeft(disc.right() + design.Space.XS)
            painter.setPen(c["ink"] if pill.editable else c["muted"])
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, pill.text)

    def _draw_north(self, painter, c) -> None:
        """A small arrow towards North in the top right corner: the view turns, North stays known."""
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
            self._rects = self._layout_pills(at, mid, design.text_font(design.Text.SECONDARY, self.font()))
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

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press, self._dragging = event.position(), False
            self._view_at_press = (self.azimuth, self.elevation)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()
        if self._press is not None and event.buttons() & Qt.MouseButton.LeftButton:
            moved = pos - self._press
            if self._dragging or math.hypot(moved.x(), moved.y()) > DRAG:
                self._dragging = True
                az, el = self._view_at_press
                self.turn(az - moved.x() * 0.5, el + moved.y() * 0.4)
                return
        key = self.key_at(pos)
        pill = self.pill(key) if key is not None else None
        self.setCursor(Qt.CursorShape.PointingHandCursor if pill is not None and pill.editable
                       else Qt.CursorShape.OpenHandCursor if self.faces else Qt.CursorShape.ArrowCursor)
        if key != self.hover:
            self.hover = key
            self.hovered.emit(key)
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._press is not None:
            if not self._dragging:
                key = self.key_at(event.position())
                if key is not None:
                    self.open_editor(key)
            self._press, self._dragging = None, False
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event) -> None:
        if self.hover is not None:
            self.hover = None
            self.hovered.emit(None)
            self.update()
        super().leaveEvent(event)

    # the field in the pill

    def open_editor(self, key) -> bool:
        pill = self.pill(key)
        if pill is None or not pill.editable:
            return False
        self.editing = key
        decimals = 1 if pill.unit == "°" else 2
        self.editor.setText(self.number(pill.value, decimals))
        self.editor.setToolTip("")
        mark_problem(self.editor, False)
        self.update()
        self._place_editor()
        self.editor.show()
        self.editor.setFocus(Qt.FocusReason.MouseFocusReason)
        self.editor.selectAll()
        return True

    def _place_editor(self) -> None:
        if self.editing is None:
            return
        at, _depth, _d, mid = self._projector()
        self._rects = self._layout_pills(at, mid, design.text_font(design.Text.SECONDARY, self.font()))
        centre = self._rects[self.editing].center()
        height = design.Size.CONTROL
        x = min(max(centre.x() - EDITOR_W / 2, 0), self.width() - EDITOR_W)
        y = min(max(centre.y() - height / 2, 0), self.height() - height)
        self.editor.setGeometry(int(x), int(y), EDITOR_W, height)

    def refuse(self, reason: str) -> None:
        """Called by a slot of `edited`: the value is not taken; the field stays open and says why."""
        self._refusal = reason or " "

    def commit(self) -> bool:
        """The value written sent; the field closes when it is taken."""
        pill = self.pill(self.editing)
        if pill is None:
            self.close_editor()
            return False
        try:
            value = float(self.parse(self.editor.text(), pill.unit))
            if not math.isfinite(value):
                raise ValueError(self.editor.text())
        except ValueError as error:
            self._refuse_now(str(error))
            return False
        self._refusal = None
        self.edited.emit(pill.key, value)
        if self._refusal is not None:
            self._refuse_now(self._refusal)
            self._refusal = None
            return False
        self.close_editor()
        return True

    def _refuse_now(self, reason: str) -> None:
        mark_problem(self.editor, True)
        self.editor.setToolTip(reason.strip())

    def close_editor(self) -> None:
        if self.editing is None and not self.editor.isVisible():
            return
        self.editing = None
        self.editor.hide()
        mark_problem(self.editor, False)
        self.update()


def _distance(p: QPointF, a: QPointF, b: QPointF) -> float:
    dx, dy = b.x() - a.x(), b.y() - a.y()
    span = dx * dx + dy * dy
    t = 0.0 if span == 0 else max(0.0, min(1.0, ((p.x() - a.x()) * dx + (p.y() - a.y()) * dy) / span))
    return math.hypot(p.x() - a.x() - t * dx, p.y() - a.y() - t * dy)
