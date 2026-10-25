"""The marks of the checks on the views (study 12, C1; study 13, rule 3.1): each level has a shape and a sign as well
as a colour, so that it reads without the colour (WCAG 1.4.1). Since R138 (25/10/2026) they are the window's symbols
(ui/symbols.py, from Spola): what to fix the stop, what to check the warning, what to know the info, what passed
the check; a number beside it when the object has more than one.
The same drawing on the plan (an item that keeps its size at every zoom), over the 3D view and in the tree. Drawn by
the painter, never an image enlarged: sharp at the screen's density (Daniel, R30: «piccolissimi e renderizzati male»).
In the tree it is as tall as the text of the row, with its number beside it in the row's font."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QIconEngine, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QGraphicsItem, QStyledItemDelegate, QWidget

from .. import theme_colors

FILL = {"fail": theme_colors.STATUS["critical"], "warn": theme_colors.STATUS["warning"], "info": "#2e4a6b",
        "ok": theme_colors.STATUS["good"]}
SIZE = 18.0


def paint(p: QPainter, centre: QPointF, level: str, count: int = 1, size: float = SIZE, views: bool = False) -> None:
    """A mark of `level` centred at `centre`, `size` pixels across, with its number when `count` > 1; on the `views`
    (the plan, the 3D view) in the light theme's colours, which keep theirs in both themes (R16)."""
    from . import symbols
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r = size / 2
    symbols.paint(p, QRectF(centre.x() - r, centre.y() - r, size, size), symbols.LEVEL.get(level, "info"),
                  dark=False if views else None)
    font = QFont()
    font.setBold(True)
    if count > 1:
        badge = QRectF(centre.x() + r * 0.45, centre.y() - r * 1.25, size * 0.72, size * 0.62)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#1e1c19"))
        p.drawRoundedRect(badge, 4, 4)
        font.setPixelSize(int(size * 0.48))
        p.setFont(font)
        p.setPen(QColor("#ffffff"))
        p.drawText(badge, Qt.AlignmentFlag.AlignCenter, str(count))
    p.restore()


class MarkIcon(QIconEngine):
    """A mark as an icon, painted at the size and the density asked, not an image of 22 x 20 points enlarged."""

    def __init__(self, level: str, count: int = 1):
        super().__init__()
        self.level, self.count = level, count

    def paint(self, painter: QPainter, rect, mode, state) -> None:
        size = min(rect.width(), rect.height()) * (0.82 if self.count > 1 else 0.9)
        paint(painter, QPointF(rect.x() + rect.width() / 2 - (size * 0.12 if self.count > 1 else 0),
                               rect.y() + rect.height() / 2 + (size * 0.08 if self.count > 1 else 0)),
              self.level, self.count, size)

    def pixmap(self, size: QSize, mode, state) -> QPixmap:
        pix = QPixmap(size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        self.paint(p, pix.rect(), mode, state)
        p.end()
        return pix

    def scaledPixmap(self, size: QSize, mode, state, scale: float) -> QPixmap:
        pix = self.pixmap(QSize(round(size.width() * scale), round(size.height() * scale)), mode, state)
        pix.setDevicePixelRatio(scale)
        return pix

    def clone(self) -> "MarkIcon":
        return MarkIcon(self.level, self.count)


def icon(level: str, count: int = 1) -> QIcon:
    return QIcon(MarkIcon(level, count))


MARK_ROLE = Qt.ItemDataRole.UserRole + 1           # (level, count) of the mark of a row of the tree


class MarkDelegate(QStyledItemDelegate):
    """The column of the marks in the project's tree, as a pill (study 17, T2; the target of 24/10/2026): a pill
    full of the level's colour with its sign and the number of items in it (the sign keeps the level readable
    without the colour, WCAG 1.4.1). On a section's header the pill sits with the header's text, below the air
    above it. The row's selection is the pill of sections.row_pill, across the columns."""

    GAP = 4
    INSET = 4           # inside the pill, around the mark and the number
    EDGE = 10           # from the row's right end: inside the selection's pill, off its edge

    @classmethod
    def column_width(cls, metrics) -> int:
        """The width of a column of marks whose numbers reach two figures, for a fixed column (the tree does not
        measure every row again at each change)."""
        size = float(metrics.height())
        return round(cls.GAP + size * 0.92 + 3 + metrics.horizontalAdvance("99") + cls.GAP)

    def _size(self, option) -> float:
        return float(option.fontMetrics.height())

    def paint(self, painter: QPainter, option, index) -> None:
        mark = index.data(MARK_ROLE)
        if not mark:
            from .sections import is_section, row_pill
            if not is_section(index):
                row_pill(painter, option)
            super().paint(painter, option, index)
            return
        from .sections import AIR, is_section, row_pill
        level, count = mark
        if not is_section(index):                   # a section is never selected nor hovered (T2)
            row_pill(painter, option)
        r = QRectF(option.rect)
        if is_section(index):
            r.adjust(0, AIR, 0, 0)
        from .design import Text, text_font
        font = text_font(Text.LABEL, option.font)          # the count: the catalogue's label (R121)
        text = str(count)
        from PySide6.QtGui import QFontMetricsF

        from . import symbols
        height = round(option.fontMetrics.height() * 0.85)
        mark = height * 0.8                                     # the sign alone, the symbols' (R138)
        width = mark + 3 + QFontMetricsF(font).horizontalAdvance(text)
        pill = QRectF(r.right() - self.EDGE - width - 2 * self.INSET - 2, r.center().y() - height / 2,
                      width + 2 * self.INSET + 2, height)
        dark = option.palette.color(option.palette.ColorRole.Window).lightnessF() < 0.5
        ground, ink = pill_colours(level, dark, option)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(ground)
        painter.drawRoundedRect(pill, pill.height() / 2, pill.height() / 2)
        x = pill.x() + self.INSET + 1
        painter.fillPath(symbols.sign(symbols.LEVEL.get(level, "info"),
                                      QRectF(x - mark * 0.06, pill.center().y() - mark / 2, mark, mark)), ink)
        painter.setPen(ink)
        painter.setFont(font)
        painter.drawText(QRectF(x + mark + 3, pill.y(), pill.right() - x, pill.height()),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        mark = index.data(MARK_ROLE)
        if not mark:
            return super().sizeHint(option, index)
        size = self._size(option)
        width = self.GAP + size * 0.92 + 3 + option.fontMetrics.horizontalAdvance(str(mark[1])) + 2 * self.INSET
        return QSize(round(width + self.GAP), round(size + self.INSET))


def pill_colours(level: str, dark: bool, option) -> tuple[QColor, QColor]:
    """The ground and the ink of a mark's pill in the tree (the mockups' .mark): the level's colour full, white
    on it; the warning's ochre in the light theme (its yellow is too light for white), the yellow with dark ink in
    the dark one; what to know in the muted colour."""
    if level == "warn":
        return (QColor(theme_colors.STATUS["warning"]), QColor("#1e1c19")) if dark else \
            (QColor(theme_colors.WARNING_INK), QColor("#ffffff"))
    if level == "info":
        muted = QColor(option.palette.color(option.palette.ColorRole.PlaceholderText))
        return muted, QColor("#151515") if dark else QColor("#ffffff")
    return QColor(FILL.get(level, FILL["info"])), QColor("#ffffff")


class MarkItem(QGraphicsItem):
    """A mark on the plan, the same size at every zoom; data(0) "mark", data(1) the object (kind, id)."""

    def __init__(self, level: str, count: int, target: tuple):
        super().__init__()
        self.level, self.count = level, count
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setData(0, "mark")
        self.setData(1, target)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def boundingRect(self) -> QRectF:
        return QRectF(-SIZE, -SIZE, 2 * SIZE + 6, 2 * SIZE)

    def shape(self):
        path = QPainterPath()
        path.addEllipse(QPointF(0, 0), SIZE / 2 + 2, SIZE / 2 + 2)
        return path

    def paint(self, painter, _option, _widget=None) -> None:
        paint(painter, QPointF(0, 0), self.level, self.count, views=True)


class MarksOverlay(QWidget):
    """The marks over the 3D view, where the camera shows their objects; the pointer goes through to the view."""

    def __init__(self, backend, parent):
        super().__init__(parent)
        self.backend = backend
        self.marks: list = []            # (point in Qt axes, level, count, target)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        backend.cameraChanged.connect(self.update)

    def set_marks(self, marks: list) -> None:
        self.marks = marks
        self.update()

    def where(self) -> list:
        """The marks on screen: (x, y, level, count, target); behind the camera, none."""
        out = []
        w, h = max(1, self.width()), max(1, self.height())
        for point, level, count, target in self.marks:
            xy = self.backend.camera.project(point, w, h)
            if xy is not None and -SIZE <= xy[0] <= w + SIZE and -SIZE <= xy[1] <= h + SIZE:
                out.append((xy[0], xy[1], level, count, target))
        return out

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        for x, y, level, count, _target in self.where():
            paint(p, QPointF(x, y - SIZE * 0.7), level, count, views=True)
