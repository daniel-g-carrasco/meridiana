"""The offline Natural Earth layer under the plan's tiles at continental scale."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsRectItem, QGraphicsSimpleTextItem

from .. import tiles, view_colours, worldmap
from .design import Text, text_font


def _point(origin, lon, lat):
    x, y = origin.to_local(lon, lat)
    return QPointF(x, -y)


class WorldLayer:
    OCEAN_Z = -3.0
    LAND_Z = -2.0
    LABEL_Z = -1.5

    def __init__(self, scene, origin, rect: QRectF):
        self.scene = scene
        self.origin = origin
        self.rect = rect
        self.items = []
        self.labels = []
        self.label_ranks = {}
        self.country_items = {}
        self.metres_per_pixel = 0.0
        self._build()

    def _add(self, item):
        self.scene.addItem(item)
        self.items.append(item)
        return item

    def _build(self):
        colours = view_colours.WORLD
        ocean = self._add(QGraphicsRectItem(self.rect))
        ocean.setPen(QPen(Qt.PenStyle.NoPen))
        ocean.setBrush(QBrush(QColor(colours["ocean"])))
        ocean.setZValue(self.OCEAN_Z)
        for index, country in enumerate(worldmap.countries()):
            if tiles.angular_distance(self.origin, *country.label) > 100:
                continue
            path = QPainterPath()
            path.setFillRule(Qt.FillRule.OddEvenFill)
            for polygon in country.polygons:
                for ring in polygon:
                    points = [_point(self.origin, lon, lat) for lon, lat in ring
                              if tiles.angular_distance(self.origin, lon, lat) <= tiles.HEMISPHERE_DEGREES]
                    if len(points) >= 3:
                        path.addPolygon(points)
                        path.closeSubpath()
            if path.isEmpty():
                continue
            item = self._add(QGraphicsPathItem(path))
            item.setPen(QPen(QColor(colours["border"]), 0.8))
            item.setBrush(QBrush(QColor(colours["land"][index % len(colours["land"])])))
            item.setZValue(self.LAND_Z)
            self.country_items[country.name] = item
            if country.label_rank <= 6 and tiles.angular_distance(self.origin, *country.label) <= 80:
                label = QGraphicsSimpleTextItem(country.italian_name)
                label.setFont(text_font(Text.SECONDARY, QFont()))
                label.setBrush(QBrush(QColor(colours["label"])))
                label.setFlag(label.GraphicsItemFlag.ItemIgnoresTransformations)
                centre = _point(self.origin, *country.label)
                label.setPos(centre - label.boundingRect().center())
                label.setZValue(self.LABEL_Z)
                self._add(label)
                self.labels.append(label)
                self.label_ranks[label] = country.label_rank
        for longitude in range(-180, 181, 30):
            self._graticule([(longitude, latitude) for latitude in range(-80, 81, 2)])
        for latitude in range(-60, 61, 30):
            self._graticule([(longitude, latitude) for longitude in range(-180, 181, 2)])

    def _graticule(self, coordinates):
        path = QPainterPath()
        drawing = False
        for lon, lat in coordinates:
            if tiles.angular_distance(self.origin, lon, lat) > tiles.HEMISPHERE_DEGREES:
                drawing = False
                continue
            point = _point(self.origin, lon, lat)
            if drawing:
                path.lineTo(point)
            else:
                path.moveTo(point)
                drawing = True
        item = self._add(QGraphicsPathItem(path))
        item.setPen(QPen(QColor(view_colours.WORLD["graticule"]), 0.6))
        item.setZValue(self.LAND_Z + 0.2)

    def set_scale(self, metres_per_pixel: float) -> None:
        self.metres_per_pixel = metres_per_pixel
        visible = metres_per_pixel >= 250.0
        for item in self.items:
            item.setVisible(visible)
        rank = 4 if metres_per_pixel >= 5000.0 else 6
        occupied = []
        for label in sorted(self.labels, key=lambda item: self.label_ranks[item]):
            show = visible and metres_per_pixel >= 1500.0 and self.label_ranks[label] <= rank
            rect = label.sceneBoundingRect().adjusted(-3, -2, 3, 2)
            if show and any(rect.intersects(other) for other in occupied):
                show = False
            label.setVisible(show)
            if show:
                occupied.append(rect)

    def set_origin(self, origin) -> None:
        for item in self.items:
            self.scene.removeItem(item)
        self.items.clear()
        self.labels.clear()
        self.label_ranks.clear()
        self.country_items.clear()
        self.origin = origin
        self._build()
        self.set_scale(self.metres_per_pixel)
