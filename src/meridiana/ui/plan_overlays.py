"""What stays put on the plan while it moves: the north arrow at the top right (the same corner as the 3D view's cube,
study 12, section 6), the scale bar at the bottom left with round lengths 1-2-5 (viewaids.scale_bar), the source
of the background at the bottom right. Widgets over the viewport, not drawn in drawForeground: once the plan
stops repainting itself whole, what drawForeground draws in screen pixels would leave trails while panning. They
are children of the view, not of the viewport, which carries its children along when it scrolls."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from .. import theme_colors, viewaids
from ..i18n import _
from .design import Radius, Size, Space, Text, text_font

MARGIN = Space.M         # from the view's edges, as the view's bar (ui/viewbar.py)


def qcolour(token: str) -> QColor:
    return QColor(theme_colors.qt_hex(token))


SEE_THROUGH = 0.55                  # the boxes over the plan: the drawing shows through (Daniel, 24/10/2026)


def box(p: QPainter, rect: QRectF, colours: dict) -> None:
    """The see-through box of a label over the plan, a control's corners."""
    fill = qcolour(colours["label_bg"])
    fill.setAlphaF(SEE_THROUGH)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(fill)
    p.drawRoundedRect(rect, Radius.CONTROL, Radius.CONTROL)


def shade(colours: dict) -> QColor:
    """The dark edge around the lines inside a box: they read on a light photo through the box."""
    halo = qcolour(colours["label_bg"])
    halo.setAlphaF(0.6)
    return halo


class Overlay(QWidget):
    def __init__(self, parent, mouse: bool = False):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, not mouse)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFont(text_font(Text.SECONDARY, self.font()))      # the words over the plan: 12 px (R121)
        self.colours = {"label_bg": "#14161ac8", "label_fg": "#f2efe6"}

    def set_colours(self, colours: dict) -> None:
        self.colours = colours
        self.update()


class NorthArrow(Overlay):
    """A round compass: the arrow points to true North when the view turns, and the N with it, at its tip, upright to
    be read (R174, Daniel 26/10/2026: «la N di nord non segue la freccia ... la N dovrebbe poter ruotare»); the line
    below says the view's bearing and its nearest compass point; a click brings North up again («anche un modo per
    riportarlo a nord ci vuole»). The project itself never turns."""

    clicked = Signal()
    CENTRE = QPointF(28, 28)        # the disc's middle
    LETTER = 18.0                   # the N's distance from it, on the arrow's line past its tip

    def __init__(self, parent):
        super().__init__(parent, mouse=True)
        self.angle = 0.0
        self.rotation = 0.0
        self.setFixedSize(56, 78)
        self.set_rotation(0.0)

    def set_rotation(self, degrees: float) -> None:
        self.rotation = degrees % 360.0
        self.angle = -self.rotation
        tip = _("View orientation: {heading}. The arrow points to true North. Project azimuths: from South, positive "
                "towards West, as PVsyst and PVGIS write them.").format(heading=self.heading_text())
        turned = round(self.rotation, 1) % 360.0 != 0.0
        if turned:
            tip += "\n" + _("Click: North up again (N)")
        self.setToolTip(tip)
        self.setCursor(Qt.CursorShape.PointingHandCursor if turned else Qt.CursorShape.ArrowCursor)
        self.update()

    def letter_centre(self) -> QPointF:
        """Where the N is drawn: on the arrow's line, past its tip, wherever the arrow points."""
        import math
        a = math.radians(self.angle)
        return QPointF(self.CENTRE.x() + self.LETTER * math.sin(a), self.CENTRE.y() - self.LETTER * math.cos(a))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def heading_text(self) -> str:
        from ..i18n import number
        points = (_("N"), _("NE"), _("E"), _("SE"), _("S"), _("SW"), _("W"), _("NW"))
        return _("{angle}° {point}").format(angle=number(self.rotation, 0),
                                            point=points[int((self.rotation + 22.5) // 45) % 8])

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink, halo = qcolour(self.colours["label_fg"]), shade(self.colours)
        fill = qcolour(self.colours["label_bg"])
        fill.setAlphaF(SEE_THROUGH)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(fill)
        p.drawEllipse(QRectF(2, 2, 52, 52))
        p.setFont(text_font(Text.LABEL))
        p.setPen(ink)
        n = self.letter_centre()
        p.drawText(QRectF(n.x() - 8, n.y() - 7, 16, 14), Qt.AlignmentFlag.AlignCenter, _("N"))
        p.drawText(QRectF(0, 58, self.width(), 18), Qt.AlignmentFlag.AlignCenter, self.heading_text())
        p.translate(self.CENTRE)
        p.rotate(self.angle)
        head = QPainterPath(QPointF(0, -10))
        head.lineTo(5, -1)
        head.lineTo(-5, -1)
        head.closeSubpath()
        for pen, width in ((halo, 3.6), (ink, 1.6)):
            p.setPen(QPen(pen, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(0, -1), QPointF(0, 12))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(ink)
        p.drawPath(head)


class ScaleBar(Overlay):
    """A bar of a round length, 1, 2 or 5 times a power of ten, at most LONGEST pixels: a line with its ends and
    the length at its right (Daniel's choice B of 24/10/2026), in a box that wraps them with the same margin."""

    LONGEST = 120.0
    PAD = Space.M                   # around the bar and its length, on every side

    def __init__(self, parent):
        super().__init__(parent)
        self.length, self.pixels = 10.0, 100.0
        self._fit()

    def set_scale(self, metres_per_pixel: float) -> None:
        length, pixels = viewaids.scale_bar(metres_per_pixel, self.LONGEST)
        if (length, round(pixels, 1)) != (self.length, round(self.pixels, 1)):
            self.length, self.pixels = length, pixels
            self._fit()
            self.update()

    def text(self) -> str:
        return viewaids.length_text(self.length)

    def _fit(self) -> None:
        """As wide as the bar and its length, the margin on both sides: the box centred on what it holds."""
        text = QFontMetrics(self.font()).horizontalAdvance(self.text())
        self.setFixedSize(int(round(2 * self.PAD + self.pixels + Space.S + text)), Size.CONTROL)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        box(p, QRectF(self.rect()), self.colours)
        ink, halo = qcolour(self.colours["label_fg"]), shade(self.colours)
        y = self.height() / 2 + 3
        x0, x1 = float(self.PAD), self.PAD + self.pixels
        for pen, width in ((halo, 3.6), (ink, 1.6)):
            p.setPen(QPen(pen, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            p.drawLine(QPointF(x0, y), QPointF(x1, y))
            for x in (x0, x1):
                p.drawLine(QPointF(x, y - 6), QPointF(x, y + 0.8))
        p.setPen(ink)
        p.drawText(QRectF(x1 + Space.S, 0, self.width() - x1 - Space.S, self.height()),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.text())


class Attribution(Overlay):
    """The source of the background: OpenStreetMap's licence asks for it, the national orthophoto asks to cite it.
    A label as the scale bar's (24/10/2026), in the room the scale bar leaves: shortened in the middle when the
    plan is narrow, never over the bar."""

    def __init__(self, parent):
        super().__init__(parent)
        self.text = ""
        self.full = ""
        self.setToolTip("")

    def set_text(self, text: str, width: int) -> None:
        fm = QFontMetrics(self.font())
        scale = ScaleBar.LONGEST + 2 * ScaleBar.PAD + Space.S + 40      # the scale bar at its widest
        room = width - scale - 3 * MARGIN - 2 * Space.M                  # beside it, MARGIN apart
        self.full = text
        self.text = fm.elidedText(text, Qt.TextElideMode.ElideMiddle, int(max(40, room)))
        self.setToolTip(text if self.text != text else "")
        self.setFixedSize(fm.horizontalAdvance(self.text) + 2 * Space.M, Size.CONTROL)
        self.setVisible(bool(text))
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        box(p, QRectF(self.rect()), self.colours)
        p.setPen(qcolour(self.colours["label_fg"]))
        p.drawText(QRectF(self.rect()), Qt.AlignmentFlag.AlignCenter, self.text)


class FallbackStrip(QWidget):
    """A temporary map failure, said in plain words, with a retry and the ordinary background menu."""

    chooseBackground = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("card")
        row = QHBoxLayout(self)
        row.setContentsMargins(Space.M, Space.S, Space.S, Space.S)
        row.setSpacing(Space.S)
        self.message = QLabel(self)
        self.message.setWordWrap(True)
        self.retry = QPushButton(_("Retry"), self)
        self.choose = QPushButton(_("Choose the background"), self)
        row.addWidget(self.message, 1)
        row.addWidget(self.retry)
        row.addWidget(self.choose)
        self.choose.clicked.connect(self.chooseBackground)
        self.hide()

    def show_failure(self, failed: str, replacement: str) -> None:
        self.message.setText(_("{failed} is not reachable: using {replacement}.").format(
            failed=failed, replacement=replacement))
        self.show()


def place(view) -> None:
    """The overlays in their corners of the viewport (they are children of the view, which has its frame and its
    scroll bars around the viewport)."""
    r = view.viewport().geometry()
    view.north.move(r.right() + 1 - view.north.width() - MARGIN, r.top() + MARGIN)
    view.scale_bar.move(r.left() + MARGIN, r.bottom() + 1 - view.scale_bar.height() - MARGIN)
    view.attribution.move(r.right() + 1 - view.attribution.width() - MARGIN,
                          r.bottom() + 1 - view.attribution.height() - MARGIN)
    if getattr(view, "viewbar", None) is not None:
        view.viewbar.place(r, [view.north.geometry()])
    strip = view.fallback_strip
    strip.setMaximumWidth(max(280, r.width() - 2 * MARGIN))
    strip.adjustSize()
    top = r.top() + MARGIN
    if getattr(view, "viewbar", None) is not None:
        top = max(top, view.viewbar.geometry().bottom() + 1 + Space.S)
    strip.move(r.left() + MARGIN, top)
    for overlay in (view.north, view.scale_bar, view.attribution, strip):
        overlay.raise_()
