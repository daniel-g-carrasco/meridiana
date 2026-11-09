"""Offline Natural Earth preview and existing, consent-aware tile loader."""

import math
import json
from PySide6.QtCore import (
    QByteArray,
    QBuffer,
    QIODevice,
    QObject,
    Property,
    Signal,
    Slot,
)
from ... import view_colours, worldmap


def point(lon, lat):
    lat = max(-85.0511, min(85.0511, lat))
    return (
        (lon + 180) / 360,
        (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2,
    )


class DialogMap(QObject):
    changed = Signal()

    def __init__(self, backend):
        super().__init__(backend)
        self.backend = backend
        self._allowed = False
        self._tiles = {}
        self._wanted = []
        self._center = list(point(12.5, 41.5))
        self._zoom = 6
        self._width, self._height = 640, 480
        self._marker = []
        self._countries = []
        for index, country in enumerate(worldmap.countries()):
            for polygon in country.polygons:
                self._countries.append(
                    dict(ring=[list(point(lon, lat)) for lon, lat in polygon[0]],
                         color=view_colours.WORLD['land'][index % len(view_colours.WORLD['land'])])
                )
        self.loader = None
        if backend.paths is not None:
            from ...ui.tileloader import TileLoader

            self.loader = TileLoader(backend.paths.cache, self)
            self.loader.offline = True
            self.loader.tileReady.connect(self._ready)
            self.loader.tileFailed.connect(self._failed)

    @Property(str, constant=True)
    def countriesJson(self):
        return json.dumps(self._countries)

    @Property('QVariantMap', constant=True)
    def colours(self):
        return view_colours.WORLD

    @Property('QVariantList', constant=True)
    def labels(self):
        return [dict(text=c.italian_name, anchor=list(point(*c.label)), rank=c.label_rank)
                for c in sorted(worldmap.countries(), key=lambda c: c.label_rank) if c.label_rank <= 6]

    def reset(self):
        self.set_allowed(False)
        self._center = list(point(12.5, 41.5))
        self._zoom, self._marker = 6, []
        self.changed.emit()

    @Property("QVariantList", notify=changed)
    def center(self):
        return self._center

    @Property("QVariantList", notify=changed)
    def marker(self):
        return self._marker

    @Property(int, notify=changed)
    def zoom(self):
        return self._zoom

    @Property(bool, notify=changed)
    def allowed(self):
        return self._allowed

    @Property("QVariantList", notify=changed)
    def tiles(self):
        return [
            dict(x=x, y=y, z=z, url=self._tiles.get((z, x, y), ""))
            for z, x, y in self._wanted
        ]

    def set_allowed(self, allowed):
        changed = self._allowed != allowed
        self._allowed = allowed
        if self.loader:
            self.loader.offline = not allowed
        if changed:
            if not allowed:
                self._wanted = []
            else:
                self.viewport(*self._center, self._zoom, self._width, self._height)
            self.changed.emit()

    def set_point(self, lat, lon):
        self._center = list(point(lon, lat))
        self._marker = list(self._center)
        self._zoom = 17 if self._allowed else 7
        self.viewport(*self._center, self._zoom, self._width, self._height)
        self.changed.emit()

    def pause(self):
        if self.loader:
            self.loader.offline = True
        self._wanted = []

    @Slot(float, float, int, float, float)
    def viewport(self, cx, cy, zoom, width, height):
        self._width, self._height = width, height
        self._center = [cx % 1, max(0, min(1, cy))]
        self._zoom = max(2, min(19, zoom))
        if not self.loader or not self._allowed:
            return
        count = 2**self._zoom
        px, py = cx * count, cy * count
        dx, dy = width / 512, height / 512
        self._wanted = [
            (self._zoom, x, y)
            for x in range(max(0, math.floor(px - dx)), min(count, math.ceil(px + dx)))
            for y in range(max(0, math.floor(py - dy)), min(count, math.ceil(py + dy)))
        ]
        self.loader.keep_only({("osm", z, x, y) for z, x, y in self._wanted})
        for z, x, y in self._wanted:
            self.loader.request("osm", z, x, y)
        self.changed.emit()

    def _ready(self, key, z, x, y, image):
        if not self._allowed or (z, x, y) not in self._wanted:
            return
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        self._tiles[z, x, y] = "data:image/png;base64," + bytes(data.toBase64()).decode(
            "ascii"
        )
        if len(self._tiles) > 100:
            self._tiles = {k: v for k, v in self._tiles.items() if k in self._wanted}
        self.changed.emit()

    def _failed(self, key, z, x, y, error):
        self.backend._status = error
        self.backend.changed.emit()
