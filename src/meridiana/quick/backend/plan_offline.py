"""The orthophoto of a project kept for the plan without network (R516). Once a project has its site, the plan keeps
on disk the area of the drawing and RADIUS metres around it (1 km), at every zoom from ZOOMS_OUT levels above the
detail of the orthophoto down to that detail (Source.last_zoom: the national orthophoto's 50 cm is zoom 18 in
Italy; further would be the same pixels enlarged), in background, two requests at a time, with Meridiana's
User-Agent. A tile already on disk is not asked again: a run cut short (the program closed, the network gone) goes
on from where it was the next time the project is opened.

Only for the sources whose licence allows it (Source.bulk: the open orthophotos of Italy); never OpenStreetMap,
whose tile policy forbids the bulk download and the offline use, or a volunteer's server.

Where: the common cache of the tiles (paths.cache/tiles, the folder the plan reads), the simplest and the one the
plan already uses; the orthophotos of a year never expire there (Source.max_age_days 0). A copy inside the project
file would open offline on another PC, but it changes the format and makes every file 10-20 MB heavier: not now.
Measured on 07/11/2026 over Rho with the real server (17-22 KB a tile at zooms 16-18): 1 km around a 100 m drawing
is 601 tiles from zoom 12 to 18 (420 of them at 18), about 11 MB; a 1 km site with 1 km around, 1154 tiles, about
20 MB."""

from __future__ import annotations

import os

from PySide6.QtCore import QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from ... import tiles
from . import plan_tiles
from .plan_tiles import USER_AGENT, tile_path

RADIUS = 1000.0         # metres around the drawing; MERIDIANA_OFFLINE_RADIUS in the environment changes it
ZOOMS_OUT = 6           # the zooms kept above the detail: at zoom 12 a tile is about 7 km, the whole area
IN_FLIGHT = 2           # a polite pace for a public server
START_DELAY = 3.0       # seconds after the plan asked it: the tiles on show come first
RETRIES = (0.5, 3.0)    # each under another address (Source.tile_url's `attempt`)


def radius() -> float:
    try:
        return max(0.0, float(os.environ.get('MERIDIANA_OFFLINE_RADIUS', RADIUS)))
    except ValueError:
        return RADIUS


def area_tiles(source, origin, bounds, radius=None) -> list[tuple[int, int, int]]:
    """The tiles (z, x, y) of `bounds` (west, south, east, north in metres East and North of `origin`) and `radius`
    metres around, coarsest first, at the zooms of `source` from ZOOMS_OUT above its detail to its detail."""
    pad = globals()['radius']() if radius is None else radius
    w, s, e, n = bounds
    corners = [origin.to_lonlat(x, y) for x, y in ((w - pad, s - pad), (e + pad, n + pad))]
    (west, south), (east, north) = corners
    last = source.last_zoom
    out = []
    for z in range(max(source.min_zoom, last - ZOOMS_OUT), last + 1):
        out += [(z, x, y) for x, y in tiles.tiles_for(west, south, east, north, z, limit=1 << 20)]
    return out


class AreaDownload(QObject):
    """Keeps `area` (area_tiles) of `source` under `cache_dir`. `progress(done, total)`; `finished` when every
    tile is on disk or was given up (`failed` of them)."""

    progress = Signal(int, int)

    def __init__(self, cache_dir, source, area, parent=None):
        super().__init__(parent)
        if not source.bulk:
            raise ValueError(f'{source.key}: its licence does not allow keeping an area ahead')
        self.cache_dir, self.source = cache_dir, source
        self.area = list(area)
        self.todo = [t for t in self.area if not tile_path(cache_dir, source, *t).exists()]
        self.total, self.done, self.failed = len(self.area), len(self.area) - len(self.todo), 0
        self.attempts = {}
        self.in_flight = {}
        self.arriving = set()               # kept and checked on a decoders' thread (plan_tiles._Arrived, r24-fasi)
        hub, self.decoders = plan_tiles._decoders()
        self.number = next(plan_tiles._NUMBERS)
        hub.loaders[self.number] = self
        self.net = None
        self.finished = False
        self.stopped = False

    def start(self):
        if self.stopped:
            return
        self.todo.reverse()                 # popped from the end: the coarsest first
        self.progress.emit(self.done, self.total)
        if not self.todo:
            self.finished = True
            return
        self.net = QNetworkAccessManager(self)
        self._pump()

    def stop(self):
        """The network turned off, the project closed: what is on disk stays, the rest comes next time."""
        self.stopped = True
        for reply in list(self.in_flight):
            reply.abort()

    def _pump(self):
        while not self.stopped and self.todo and len(self.in_flight) < IN_FLIGHT:
            tile = self.todo.pop()
            req = QNetworkRequest(QUrl(self.source.tile_url(*tile, attempt=self.attempts.get(tile, 0))))
            req.setRawHeader(b"User-Agent", USER_AGENT)
            req.setTransferTimeout(30000)
            reply = self.net.get(req)
            self.in_flight[reply] = tile
            reply.finished.connect(self._finished)
        if not self.in_flight and not self.arriving and (not self.todo or self.stopped) and not self.finished:
            self.finished = not self.stopped and not self.todo and not self._waiting()
            if self.finished:
                self.progress.emit(self.done, self.total)

    def _waiting(self):
        return any(n for n in self.attempts.values())

    @Slot()
    def _finished(self):
        reply = self.sender()
        tile = self.in_flight.pop(reply, None)
        data = bytes(reply.readAll())
        mime = str(reply.header(QNetworkRequest.KnownHeaders.ContentTypeHeader) or "")
        error = reply.error()
        reply.deleteLater()
        if tile is None or self.stopped:
            return
        if error == QNetworkReply.NetworkError.NoError and mime.startswith("image/"):
            # r24-fasi (studio 41, S3): kept and checked away from the window's thread (before: QImage.fromData and the
            # write here, at every reply, under the pan); the end in _arrived
            self.arriving.add(tile)
            path = tile_path(self.cache_dir, self.source, *tile)
            self.decoders.start(plan_tiles._Arrived(self.number, tile, path, data), 0)
        else:
            self._settle(tile, False)
        self._pump()

    def _arrived(self, tile, image):
        tile = tuple(tile)
        if tile not in self.arriving:
            return
        self.arriving.discard(tile)
        if not self.stopped:
            self._settle(tile, not image.isNull() and tile_path(self.cache_dir, self.source, *tile).exists())
        self._pump()

    def _settle(self, tile, good):
        if good:
            self.attempts.pop(tile, None)
            self.done += 1
            self.progress.emit(self.done, self.total)
        else:
            n = self.attempts.get(tile, 0)
            if n < len(RETRIES):
                self.attempts[tile] = n + 1
                QTimer.singleShot(int(RETRIES[n] * 1000), self, lambda t=tile: self._again(t))
            else:
                self.attempts.pop(tile, None)
                self.failed += 1
                self.done += 1              # given up for this run: asked again next time
                self.progress.emit(self.done, self.total)

    def _again(self, tile):
        if self.stopped:
            return
        self.todo.append(tile)
        self.attempts[tile] = self.attempts.get(tile, 0)
        self._pump()

