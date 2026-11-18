"""Shared icon source and installation of the Quick control library."""
from __future__ import annotations

from urllib.parse import unquote

from PySide6.QtCore import QByteArray, QPointF, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtSvg import QSvgRenderer

from meridiana.quick.backend.tokens import install_theme
from meridiana.ui.icons import svg
from meridiana.ui import symbols


class IconProvider(QQuickImageProvider):
    """Render the Widgets' authoritative SVGs at the requested physical size."""

    def __init__(self, theme=None):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._theme = theme
        self._progress_style = None
        self._rendered = {}

    def requestImage(self, identifier, size, requestedSize):
        # The same icon at the same size is asked again whenever its item is made or laid out again (45 renders at
        # each resize, 06/11/2026): rendered once, kept (a few hundred small images at most).
        key = (identifier, requestedSize.width(), requestedSize.height())
        found = self._rendered.get(key)
        if found is None:
            if len(self._rendered) > 2048:
                self._rendered.clear()
            image = self._render(identifier, size, requestedSize)
            found = self._rendered[key] = (image, QSize(size))
        else:
            size.setWidth(found[1].width())
            size.setHeight(found[1].height())
        return found[0]

    def _render(self, identifier, size, requestedSize):
        parts = identifier.split('/')
        name = parts[0]
        color = QColor(unquote(parts[1])) if len(parts) > 1 else QColor('black')
        dimensions = requestedSize if requestedSize.isValid() else QSize(24, 24)
        dimensions = QSize(max(1, dimensions.width()), max(1, dimensions.height()))
        if name.startswith('progress:'):
            ratio = float(parts[2])
            dimensions = QSize(round(32 * ratio), round(6 * ratio))
        image = QImage(dimensions, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        if name.startswith('fade:'):
            from meridiana.ui.design import Radius
            from meridiana.ui.fades import PAGE_STOPS, STOPS
            ratio = float(parts[2])
            image.setDevicePixelRatio(ratio)
            width, height = dimensions.width() / ratio, dimensions.height() / ratio
            top, flat = name == 'fade:top', parts[3] in ('page', 'table')
            painter = QPainter(image)
            gradient = QLinearGradient(0, 0.5 if flat else 0, 0, height - 0.5 if flat else height)
            # R489: a page's veil, a line tall, nearly opaque over the half line next to the edge, then gone
            page_stops = ((0.0, 1.0), (0.4, 0.85), (0.75, 0.35), (1.0, 0.0))
            for at, alpha in page_stops if parts[3] == 'page' else STOPS:
                stop = QColor(color)
                stop.setAlphaF(alpha)
                gradient.setColorAt(at if top else 1 - at, stop)
            rect = QRectF(0, 0, width, height)
            if flat:
                painter.fillRect(rect, color if height <= 1 else gradient)
            else:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                rect.adjust(1, 1 if top else 0, -1, 0 if top else -1)
                radius = Radius.CARD - 1
                outline = QRectF(rect.x(), rect.y() if top else rect.y() - radius,
                                 rect.width(), rect.height() + radius)
                path = QPainterPath()
                path.addRoundedRect(outline, radius, radius)
                painter.setClipRect(rect)
                painter.fillPath(path, gradient)
            painter.end()
            size.setWidth(dimensions.width())
            size.setHeight(dimensions.height())
            return image
        if name.startswith('progress:'):
            # Fusion is the Widgets' base style. Cache only its two static skins;
            # Quick stretches their middle and animates geometry without Python.
            from PySide6.QtGui import QPalette
            from PySide6.QtWidgets import QStyle, QStyleFactory, QStyleOptionProgressBar
            from meridiana import theme_colors
            from meridiana.ui.theme import qpalette
            if self._progress_style is None:
                self._progress_style = QStyleFactory.create('Fusion')
            image.setDevicePixelRatio(dimensions.height() / 6)
            option = QStyleOptionProgressBar()
            option.rect = QRect(0, 0, 32, 6)
            option.minimum, option.maximum, option.progress = 0, 100, 100
            option.textVisible = False
            option.state = QStyle.StateFlag.State_Horizontal
            enabled = parts[-1] != 'off'
            if enabled:
                option.state |= QStyle.StateFlag.State_Enabled
            option.palette = qpalette(theme_colors.palette(self._theme.colors, self._theme.dark))
            option.palette.setCurrentColorGroup(QPalette.ColorGroup.Active if enabled else QPalette.ColorGroup.Disabled)
            painter = QPainter(image)
            element = (QStyle.ControlElement.CE_ProgressBarGroove if name.startswith('progress:groove')
                       else QStyle.ControlElement.CE_ProgressBarContents)
            self._progress_style.drawControl(element, option, painter)
            painter.end()
            # BorderImage treats provider pixels as logical pixels. Split the
            # caps explicitly so high-DPI skins keep their six logical rows.
            cap = round(3 * ratio)
            if name.endswith('-left'):
                image = image.copy(0, 0, cap, dimensions.height())
            elif name.endswith('-right'):
                image = image.copy(dimensions.width() - cap, 0, cap, dimensions.height())
            elif name.endswith('-middle'):
                image = image.copy(cap, 0, dimensions.width() - 2 * cap, dimensions.height())
            dimensions = image.size()
            size.setWidth(dimensions.width())
            size.setHeight(dimensions.height())
            return image
        painter = QPainter(image)
        rect = QRectF(0, 0, dimensions.width(), dimensions.height())
        if name.startswith('sign:'):
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.fillPath(symbols.sign(name.removeprefix('sign:'), rect), color)
        elif name == 'control:close':
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.scale(dimensions.width() / 20, dimensions.height() / 20)
            painter.setPen(QPen(color, 1.5))
            painter.drawLine(QPointF(6.5, 6.5), QPointF(13.5, 13.5))
            painter.drawLine(QPointF(6.5, 13.5), QPointF(13.5, 6.5))
        elif name in ('control:star', 'control:star-full'):
            # R518: the favourite's star, drawn: «★» and «☆» are not in the program's font and came out as an empty box
            # wherever Qt finds no other font with them (offscreen, a Linux without symbol fonts)
            import math
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.scale(dimensions.width() / 20, dimensions.height() / 20)
            star = QPainterPath()
            for k in range(10):
                r = 7 if k % 2 == 0 else 3
                a = -math.pi / 2 + k * math.pi / 5
                p = QPointF(10 + r * math.cos(a), 10.6 + r * math.sin(a))
                star.moveTo(p) if k == 0 else star.lineTo(p)
            star.closeSubpath()
            pen = QPen(color, 1.3)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            if name == 'control:star-full':
                painter.setBrush(color)
            painter.drawPath(star)
        elif name == 'control:chevron-down':
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.scale(dimensions.width() / 20, dimensions.height() / 20)
            pen = QPen(color, 1.5)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPolyline([QPointF(6, 8.5), QPointF(10, 12.5), QPointF(14, 8.5)])
        elif name in ('control:chevron-right', 'control:minus', 'control:plus', 'control:more'):
            # R21-F3: the signs that were characters in a text («›», «−», «+», «⋮»), on the grid of chevron-down (20
            # units, line 1.5, round ends): no symbol font needed, the same drawing at every scale and on every system
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.scale(dimensions.width() / 20, dimensions.height() / 20)
            if name == 'control:more':
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                for y in (5, 10, 15):
                    painter.drawEllipse(QPointF(10, y), 1.4, 1.4)
            else:
                pen = QPen(color, 1.5)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                if name == 'control:chevron-right':
                    painter.drawPolyline([QPointF(8.5, 6), QPointF(12.5, 10), QPointF(8.5, 14)])
                else:
                    painter.drawLine(QPointF(5.5, 10), QPointF(14.5, 10))
                    if name == 'control:plus':
                        painter.drawLine(QPointF(10, 5.5), QPointF(10, 14.5))
        elif name.startswith('field:'):
            from meridiana.ui.theme import ARROWS
            path, w, h = ARROWS[name.removeprefix('field:')]
            data = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">'
                    f'<path d="{path}" fill="none" stroke="{color.name()}" stroke-width="2" '
                    'stroke-linecap="round" stroke-linejoin="round"/></svg>')
            renderer = QSvgRenderer(QByteArray(data.encode()))
            renderer.render(painter, rect)
        elif name.startswith('mark:'):
            # R464: a mark on the views (the plan, the 3D view), the symbol with its sign cut out in a disc of the
            # plan's pills; the second part the pills' colour. The same drawing as the Widgets (marks.paint).
            symbol = name.removeprefix('mark:')
            symbol = symbols.LEVEL.get(symbol, symbol)
            if symbol in symbols.NAMES:
                symbols.paint_pill(painter, rect, symbol, color)
        elif name.startswith('symbol:'):
            symbol = name.removeprefix('symbol:')
            symbol = symbols.LEVEL.get(symbol, symbol)
            if symbol in symbols.NAMES:
                symbols.paint(painter, rect, symbol, dark=len(parts) > 2 and parts[2] == 'dark',
                              off=len(parts) > 3 and parts[3] == 'off', round_=len(parts) > 4 and parts[4] == 'round')
        else:
            renderer = QSvgRenderer(QByteArray(svg(name).replace(
                b'currentColor', color.name().encode('ascii'))))
            if renderer.isValid():
                painter.setOpacity(color.alphaF())
                renderer.render(painter, rect)
        painter.end()
        size.setWidth(dimensions.width())
        size.setHeight(dimensions.height())
        return image


def install_controls(engine, theme=None):
    """Idempotently install Theme and icons; return this engine's ThemeTokens."""
    tokens = install_theme(engine, theme)
    if not getattr(engine, '_meridiana_icons', None):
        provider = IconProvider(tokens)
        engine.addImageProvider('meridiana', provider)
        engine._meridiana_icons = provider
    from . import report_pages
    report_pages.install(engine)                # the report's preview, drawn at the size shown (R509)
    return tokens
