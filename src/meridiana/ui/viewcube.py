"""The view cube at the top right of the 3D view (study 12, T1; study 15, 2.5), in the same corner as the plan's
north arrow: faces Top, N, E, S, W, edges and corners to click, four arrows that turn the view by 45 degrees,
the compass ring with its letters, Home, and a menu (perspective or parallel, fit, set this view as Home). Half
transparent until the pointer is on it. The geometry is navicube.py's; this draws it and passes the clicks to the
backend of the view, which moves the camera."""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QAction, QColor, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QMenu, QWidget

from .. import navicube, theme_colors
from ..i18n import _

SIZE = 150
CUBE = 64                   # the cube across, pixels
RING = 50                   # the compass ring's radius, pixels


def qcolour(token: str) -> QColor:
    return QColor(theme_colors.qt_hex(token))


class ViewCube(QWidget):
    fitRequested = Signal()

    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.setFixedSize(SIZE, SIZE)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.hover = None                 # ("part", part) | ("arrow", name) | ("letter", "N") | ("home",) | ("menu",)
        self.inside = False
        from .cards import default_tokens
        self.set_colours(default_tokens())
        self.picture: QPixmap | None = None     # the cube as last drawn, and what it was drawn for (R120)
        self.drawn_for = None
        backend.cameraChanged.connect(self.update)

    def set_colours(self, t: dict) -> None:
        # under the pointer the selection's grey and the text's ink, not the accent (R104)
        self.colours = {"face": t["panel"], "edge": t["line_soft"], "line": t["muted"], "text": t["text"],
                        "hot": t["select_bg"], "hot_ink": t["text"], "ring": t["muted"]}
        self.update()

    # geometry, in pixels of the widget

    def centre(self) -> QPointF:
        return QPointF(SIZE / 2, SIZE / 2 + 4)

    def arrows(self) -> dict:
        c, d, s = self.centre(), CUBE * 0.62 + 14, 7.0
        tips = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
        out = {}
        for name, (dx, dy) in tips.items():
            tip = QPointF(c.x() + dx * (d + s), c.y() + dy * (d + s))
            base = QPointF(c.x() + dx * d, c.y() + dy * d)
            side = QPointF(-dy * s, dx * s)
            out[name] = QPolygonF([tip, base + side, base - side])
        return out

    def letters(self) -> dict:
        """Where N, E, S, W of the compass ring are drawn: the horizontal ring round the cube, seen from the camera."""
        cam = self.backend.camera
        right, up = cam.right(), cam.up()
        c = self.centre()
        out = {}
        for letter, (x, z) in (("N", (0, -1)), ("S", (0, 1)), ("E", (1, 0)), ("W", (-1, 0))):
            v = np.array([x, -0.35, z], dtype=float)
            out[letter] = QPointF(c.x() + RING * float(np.dot(v, right)), c.y() - RING * float(np.dot(v, up)))
        return out

    def home_rect(self) -> QRectF:
        return QRectF(4, 4, 20, 18)

    def menu_rect(self) -> QRectF:
        return QRectF(SIZE - 22, SIZE - 20, 18, 16)

    def at(self, pos: QPointF):
        if self.home_rect().contains(pos):
            return ("home",)
        if self.menu_rect().contains(pos):
            return ("menu",)
        for name, poly in self.arrows().items():
            if poly.containsPoint(pos, Qt.FillRule.OddEvenFill):
                return ("arrow", name)
        for letter, p in self.letters().items():
            if math.hypot(pos.x() - p.x(), pos.y() - p.y()) < 9:
                return ("letter", letter)
        c = self.centre()
        part = navicube.pick(self.backend.camera, CUBE, pos.x() - c.x(), pos.y() - c.y())
        return ("part", part) if part is not None else None

    # drawing

    def paintEvent(self, _event) -> None:
        """The cube drawn again only when the view turned, the pointer moved on it or the colours changed: the 3D view
        under it paints every frame, and drawing the cube from scratch cost 8 ms of each (R120, 25/10/2026)."""
        ratio = self.devicePixelRatioF()
        key = (tuple(np.round(self.backend.camera.rotation, 6)), self.hover, self.inside,
               tuple(self.colours.values()), ratio)
        if self.picture is None or key != self.drawn_for:
            picture = QPixmap(round(SIZE * ratio), round(SIZE * ratio))
            picture.setDevicePixelRatio(ratio)
            picture.fill(Qt.GlobalColor.transparent)
            p = QPainter(picture)
            self._draw(p)
            p.end()
            self.picture, self.drawn_for = picture, key
        QPainter(self).drawPixmap(0, 0, self.picture)

    def _draw(self, p: QPainter) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        faint = 1.0 if self.inside else 0.55              # the cube recessive until the pointer comes near
        p.setOpacity(faint)
        col = self.colours
        cam = self.backend.camera
        c = self.centre()
        # the compass ring
        p.setPen(QPen(qcolour(col["ring"]), 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        ring = QPolygonF()
        for k in range(49):
            a = 2 * math.pi * k / 48
            v = np.array([math.sin(a), -0.35, -math.cos(a)])
            ring.append(QPointF(c.x() + RING * float(np.dot(v, cam.right())), c.y() - RING * float(np.dot(v, cam.up()))))
        p.drawPolyline(ring)
        from .design import Text, text_font
        p.setFont(text_font(Text.LABEL, self.font()))
        # the words never faint: see-through letters on the sky read as blurred (Daniel, 24/10/2026: «il rendering
        # dei font è molto pessimo»)
        p.setOpacity(1.0)
        names = navicube.face_names()
        cardinal = {"N": names["north"], "S": names["south"], "E": names["east"], "W": names["west"]}
        for letter, q in self.letters().items():
            hot = self.hover == ("letter", letter)
            p.setPen(qcolour(col["hot_ink"] if hot else col["text"]))
            p.drawText(QRectF(q.x() - 9, q.y() - 9, 18, 18), Qt.AlignmentFlag.AlignCenter, cardinal[letter])
        # the cube, its cells farthest first; computed once a frame (it was seven times, about 5 ms)
        p.setOpacity(faint)
        p.translate(c)
        cells = navicube.faces(cam, CUBE)
        for part, poly, _depth in cells:
            hot = self.hover == ("part", part)
            fill = col["hot"] if hot else col["face"] if navicube.kind(part) == "face" else col["edge"]
            p.setBrush(qcolour(fill))
            p.setPen(QPen(qcolour(col["line"]), 0.8))
            p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in poly]))
        for normal, name in navicube.FACES.items():
            face = [poly for part, poly, _d in cells if part == normal]
            if not face:
                continue
            xs, ys = [x for x, _y in face[0]], [y for _x, y in face[0]]
            box = QRectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
            if box.width() < 10 or box.height() < 8:
                continue                                    # seen edge-on
            p.setPen(qcolour(col["text"]))
            p.setOpacity(1.0)
            p.drawText(box.adjusted(-6, -4, 6, 4), Qt.AlignmentFlag.AlignCenter, names[name])
            p.setOpacity(faint)
        p.resetTransform()
        # arrows, Home, the menu's button
        for name, poly in self.arrows().items():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(qcolour(col["hot_ink"] if self.hover == ("arrow", name) else col["line"]))
            p.drawPolygon(poly)
        h = self.home_rect()
        house = QPainterPath(QPointF(h.center().x(), h.top() + 2))
        house.lineTo(h.right() - 2, h.center().y())
        house.lineTo(h.right() - 5, h.center().y())
        house.lineTo(h.right() - 5, h.bottom() - 2)
        house.lineTo(h.left() + 5, h.bottom() - 2)
        house.lineTo(h.left() + 5, h.center().y())
        house.lineTo(h.left() + 2, h.center().y())
        house.closeSubpath()
        p.setPen(QPen(qcolour(col["hot_ink"] if self.hover == ("home",) else col["line"]), 1.4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(house)
        m = self.menu_rect()
        p.setPen(QPen(qcolour(col["hot_ink"] if self.hover == ("menu",) else col["line"]), 1.4))
        p.drawPolyline(QPolygonF([QPointF(m.left() + 4, m.top() + 5), QPointF(m.center().x(), m.bottom() - 4),
                                  QPointF(m.right() - 4, m.top() + 5)]))

    # the pointer

    def enterEvent(self, event) -> None:
        self.inside = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.inside, self.hover = False, None
        self.update()
        super().leaveEvent(event)

    def mouseMoveEvent(self, event) -> None:
        hover = self.at(event.position())
        if hover != self.hover:
            self.hover = hover
            self.setToolTip(self._tip(hover))
            self.update()

    def _tip(self, hover) -> str:
        if hover is None:
            return ""
        return {"home": _("Home: the starting view, or the one set as Home"),
                "menu": _("Perspective or parallel, fit, set this view as Home")}.get(hover[0], "")

    def mousePressEvent(self, event) -> None:
        self.click(self.at(event.position()), double=False)

    def mouseDoubleClickEvent(self, event) -> None:
        self.click(self.at(event.position()), double=True)

    def click(self, what, double: bool = False) -> None:
        """What a click on the cube does: a part looks from its side (a double click frames the scene too), an arrow
        turns the view by 45 degrees, a letter looks from that side, Home goes back, the button opens the menu."""
        b = self.backend
        if what is None:
            return
        if what[0] == "part":
            b.orient(*navicube.looking_from(what[1], b.camera), fit=double)
        elif what[0] == "arrow":
            b.orient(*navicube.turned(b.camera, what[1]))
        elif what[0] == "letter":
            b.orient(*navicube.compass_view(what[1], b.camera))
        elif what[0] == "home":
            b.go_home()
        elif what[0] == "menu":
            self.menu().popup(self.mapToGlobal(self.menu_rect().bottomLeft().toPoint()))

    def menu(self) -> QMenu:
        menu = QMenu(self)
        parallel = QAction(_("Parallel projection"), menu, checkable=True)
        parallel.setChecked(self.backend.camera.ortho)
        parallel.toggled.connect(self.backend.set_ortho)
        menu.addAction(parallel)
        fit = QAction(_("Fit to the drawing"), menu)
        fit.triggered.connect(self.fitRequested.emit)
        menu.addAction(fit)
        home = QAction(_("Set this view as Home"), menu)
        home.triggered.connect(self.backend.set_home)
        menu.addAction(home)
        return menu
