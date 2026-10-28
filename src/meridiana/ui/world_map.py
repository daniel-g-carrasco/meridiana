"""Natural Earth under the local plan, then the whole world in Equal Earth beyond regional scale."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsRectItem, QGraphicsSimpleTextItem

from .. import tiles, view_colours, worldmap
from .design import Text, text_font

FAR_MPP = 2000.0
NEAR_MPP = 1500.0


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
        self.label_anchors = {}
        self.country_items = {}
        self.metres_per_pixel = 0.0
        self.equal_earth = False
        self._build()

    def _add(self, item):
        self.scene.addItem(item)
        self.items.append(item)
        return item

    def _point(self, lon: float, lat: float) -> QPointF:
        if self.equal_earth:
            x, y = worldmap.equal_earth(lon, lat, self.origin.lon, self.origin.lat)
        else:
            x, y = self.origin.to_local(lon, lat)
        return QPointF(x, -y)

    def _relative(self, lon: float) -> float:
        return (lon - self.origin.lon + 180) % 360 - 180

    def _rings(self, ring):
        if not self.equal_earth:
            return [[self._point(lon, lat) for lon, lat in ring
                     if tiles.angular_distance(self.origin, lon, lat) <= tiles.HEMISPHERE_DEGREES]]
        segments, points, previous = [], [], None
        for lon, lat in ring:
            relative = self._relative(lon)
            if previous is not None and abs(relative - previous) > 180:
                if len(points) >= 3:
                    segments.append(points)
                points = []
            points.append(self._point(lon, lat))
            previous = relative
        if len(points) >= 3:
            segments.append(points)
        return segments

    def _build(self):
        colours = view_colours.WORLD
        ocean = self._add(QGraphicsRectItem(self.rect))
        ocean.setPen(QPen(Qt.PenStyle.NoPen))
        ocean.setBrush(QBrush(QColor(colours["ocean"])))
        ocean.setZValue(self.OCEAN_Z)
        for index, country in enumerate(worldmap.countries()):
            if not self.equal_earth and tiles.angular_distance(self.origin, *country.label) > 100:
                continue
            path = QPainterPath()
            path.setFillRule(Qt.FillRule.OddEvenFill)
            for polygon in country.polygons:
                for ring in polygon:
                    for points in self._rings(ring):
                        path.addPolygon(points)
                        path.closeSubpath()
            if path.isEmpty():
                continue
            item = self._add(QGraphicsPathItem(path))
            item.setPen(QPen(QColor(colours["border"]), 0.8))
            item.setBrush(QBrush(QColor(colours["land"][index % len(colours["land"])])))
            item.setZValue(self.LAND_Z)
            self.country_items[country.name] = item
            if country.label_rank <= 6 and (self.equal_earth or
                                            tiles.angular_distance(self.origin, *country.label) <= 80):
                label = QGraphicsSimpleTextItem(country.italian_name)
                label.setFont(text_font(Text.SECONDARY, QFont()))
                label.setBrush(QBrush(QColor(colours["label"])))
                label.setFlag(label.GraphicsItemFlag.ItemIgnoresTransformations)
                centre = self._point(*country.label)
                from PySide6.QtGui import QTransform
                label.setTransform(QTransform().translate(-label.boundingRect().width() / 2,
                                                          -label.boundingRect().height() / 2))
                label.setPos(centre)
                label.setZValue(self.LABEL_Z)
                self._add(label)
                self.labels.append(label)
                self.label_ranks[label] = country.label_rank
                self.label_anchors[label] = centre
        for longitude in range(-180, 181, 30):
            self._graticule([(longitude, latitude) for latitude in range(-80, 81, 2)])
        for latitude in range(-60, 61, 30):
            self._graticule([(longitude, latitude) for longitude in range(-180, 181, 2)])

    def _graticule(self, coordinates):
        path = QPainterPath()
        drawing = False
        previous = None
        for lon, lat in coordinates:
            relative = self._relative(lon)
            if (not self.equal_earth and tiles.angular_distance(self.origin, lon, lat) > tiles.HEMISPHERE_DEGREES) or \
                    (self.equal_earth and previous is not None and abs(relative - previous) > 180):
                drawing = False
                previous = relative
                continue
            point = self._point(lon, lat)
            if drawing:
                path.lineTo(point)
            else:
                path.moveTo(point)
                drawing = True
            previous = relative
        item = self._add(QGraphicsPathItem(path))
        item.setPen(QPen(QColor(view_colours.WORLD["graticule"]), 0.6))
        item.setZValue(self.LAND_Z + 0.2)

    def _clear(self) -> None:
        for item in self.items:
            self.scene.removeItem(item)
        self.items.clear()
        self.labels.clear()
        self.label_ranks.clear()
        self.label_anchors.clear()
        self.country_items.clear()

    def set_scale(self, metres_per_pixel: float) -> None:
        far = metres_per_pixel >= (NEAR_MPP if self.equal_earth else FAR_MPP)
        if far != self.equal_earth:
            self.equal_earth = far
            self._clear()
            self._build()
        self.metres_per_pixel = metres_per_pixel
        visible = metres_per_pixel >= 250.0
        for item in self.items:
            item.setVisible(visible)
        rank = 3 if metres_per_pixel >= 5000.0 else 6
        occupied = []
        views = self.scene.views()
        view = views[0] if views else None
        for label in sorted(self.labels, key=lambda item: self.label_ranks[item]):
            show = visible and (self.equal_earth or metres_per_pixel >= 1500.0) and self.label_ranks[label] <= rank
            rect = label.boundingRect()
            centre = view.mapFromScene(self.label_anchors[label]) if view is not None else self.label_anchors[label]
            rect.moveCenter(centre)
            rect.adjust(-3, -2, 3, 2)
            if show and any(rect.intersects(other) for other in occupied):
                show = False
            label.setVisible(show)
            if show:
                occupied.append(rect)

    def set_origin(self, origin) -> None:
        self._clear()
        self.origin = origin
        self._build()
        self.set_scale(self.metres_per_pixel)
