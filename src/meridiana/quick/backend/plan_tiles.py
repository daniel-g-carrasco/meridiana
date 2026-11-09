"""Fetching background tiles without stopping the window: QNetworkAccessManager, at most six requests at a
time, a disk cache (paths.cache, a folder for each source: Source.cache_name) written whole or not at all, an
identifying User-Agent as OpenStreetMap's policy asks (the same for every server), and a few retries for the
national orthophoto, whose server at times answers with an error document instead of the image. A tile that never
comes leaves the plan usable, only without that piece of background.

The sources are those of the plan (`sources`, the program's and the designer's, tiles.catalogue). A designer's
source with `{key}` in its address gets the key from the system's keyring when its first tile is asked; the key is
never written in the cache's names, in the log or in what is said of a failure.

R516, an orthophoto that stays: a WMS asked again is asked under another address (Source.tile_url's `attempt`: the
national orthophoto's server keeps the error of an exact address); a tile on disk is shown whatever its age and only
renewed in background when its source says it ages (a failed renewal leaves it); a tile that arrives after the view
moved on is kept on disk all the same; the tiles on show leave the memory last and, if they left it, are read again
from the disk instead of coming back empty; the area of a project is kept ahead (plan_offline.py)."""

from __future__ import annotations

import itertools
import os
import tempfile
import time
from collections import deque
from pathlib import Path
from threading import RLock
from uuid import uuid4

from PySide6.QtCore import (QAbstractListModel, QByteArray, QModelIndex, QObject, Property, QRunnable, QThreadPool,
                            QTimer, QUrl, Qt, Signal, Slot)
from PySide6.QtGui import QImage
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtQuick import QQuickImageProvider

from ... import SLUG, __version__, log, resources, tiles
from ...i18n import _
from .plan_maps import PlanMaps, underlay_record


USER_AGENT = f"Meridiana/{__version__} (+https://github.com/daniel-g-carrasco/meridiana)".encode()
MAX_IN_FLIGHT = 6
RETRIES = (0.25, 2.0)           # under another address each time (R516): the first one need not wait
DECODERS = 2                    # threads that read and decode the cached tiles
# r23-unita: one tile decoded at a time in the whole process. A run of tests/quick/pianta stopped for good (1 in 13,
# 08/11/2026) with the window's thread in AreaDownload._finished (QImage.fromData) and both decoders in _Decode.run
# (QImage(path), then the emit): PySide's QImage.fromData keeps the GIL for most of a decode (measured: another Python
# thread ran about 20 % of the call; QImage(path) lets it go for all of it), so a decode on the window's thread that
# waits inside Qt for a decoder, while the decoders wait for the GIL, never ends. Under this lock no two decodes meet;
# waiting for it lets the GIL go. Decoding stays off the window's thread for the cache (the reason of the pool).
DECODE_LOCK = RLock()
KEYS = f"{SLUG}-maps"           # the keyring's service of the designer's map keys (assistant/keys.py)


def decode(data: bytes) -> QImage:
    """A tile arrived from the network, decoded on this thread under DECODE_LOCK (never beside a decoder)."""
    with DECODE_LOCK:
        return QImage.fromData(data)


PREMULTIPLIED = QImage.Format.Format_ARGB32_Premultiplied


def ready(image: QImage) -> QImage:
    """r24-fasi: an image in the format the scene graph uploads (premultiplied ARGB), converted on the thread that
    decoded it, not when the Image takes it on the window's thread."""
    if image.isNull() or image.format() == PREMULTIPLIED:
        return image
    return image.convertToFormat(PREMULTIPLIED)


def store_and_decode(path: Path, data: bytes) -> QImage:
    """r24-fasi (studio 41, S3): a tile arrived from the network, written next to its place, decoded from the file and
    put in its place only when it is an image (an old one on disk stays when the server answers junk); on a decoders'
    thread. QImage(path) lets the GIL go for all of the decode, QImage.fromData does not (DECODE_LOCK): the window's
    thread is not stopped by the tiles of a pan. A disk that refuses (full, read-only): decoded from the bytes, not
    kept, as before."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        with os.fdopen(fd, "wb") as f:
            f.write(data)
    except OSError as error:
        log.complain("tile cache", error)
        return decode(data)
    with DECODE_LOCK:
        image = ready(QImage(tmp))
    try:
        if image.isNull():
            os.unlink(tmp)
        else:
            os.replace(tmp, path)
    except OSError as error:
        log.complain("tile cache", error)
    return image


def tile_path(cache_dir: Path, source, z: int, x: int, y: int) -> Path:
    """Where a tile of `source` (a Source, or a key) is kept under the cache folder (paths.cache)."""
    name = source.cache_name if hasattr(source, 'cache_name') else str(source)
    return Path(cache_dir) / "tiles" / name / str(z) / str(x) / f"{y}.img"


def store_tile(path: Path, data: bytes) -> bool:
    """Written whole or not at all; False when the disk refused (a full disk, a read-only cache)."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
        return True
    except OSError as error:
        log.complain("tile cache", error)
        return False


class _DecodeHub(QObject):
    """Where the decoders hand their images back, one for the process, on the window's thread, never destroyed while
    the program runs; it gives each image to the loader that asked it, if that loader is still there.

    r21-unita: each loader had its QThreadPool and each job its signals object, connected to the loader. A loader
    destroyed without close() (a test that leaves it to Python's collector, a parent deleted) destroyed its pool
    with the GIL held: ~QThreadPool waits for its jobs, a job needs the GIL to emit, so the window's thread stopped
    for ever (the hang of tests/quick/pianta in the whole folder), or the job emitted to a loader half destroyed
    (an access violation): of ten runs of a probe that drops loaders while they decode, eight crashed and one
    stopped. Now the pool and the
    hub outlive every loader, and a job knows its loader only by a number."""

    done = Signal(int, object, QImage)      # the loader's number, the tile (key, z, x, y), its image (null if none)
    arrived = Signal(int, object, QImage)   # the same for a tile come from the network (_Arrived)

    def __init__(self):
        super().__init__()
        import weakref
        self.loaders = weakref.WeakValueDictionary()
        self.done.connect(self._deliver)
        self.arrived.connect(self._deliver_arrived)

    @Slot(int, object, QImage)
    def _deliver(self, number, tile, image):
        loader = self.loaders.get(number)
        if loader is None:
            return
        import shiboken6
        if shiboken6.isValid(loader):
            loader._decoded(tile, image)

    @Slot(int, object, QImage)
    def _deliver_arrived(self, number, tile, image):
        loader = self.loaders.get(number)
        if loader is None:
            return
        import shiboken6
        if shiboken6.isValid(loader):
            loader._arrived(tile, image)


_HUB = None
_POOL = None
_NUMBERS = itertools.count(1)     # a loader's number, never given twice


def _decoders():
    """The hub and the decoders' pool of the process, made on the window's thread at the first tile read."""
    global _HUB, _POOL
    if _HUB is None:
        _HUB = _DecodeHub()
        _POOL = QThreadPool()
        _POOL.setMaxThreadCount(DECODERS)
        import atexit
        atexit.register(_drain)
    return _HUB, _POOL


def _drain():
    """At the interpreter's end, before the module lets the hub and the pool go: the jobs not started are dropped,
    those running end (waitForDone lets the GIL go). Without it a job still queued met a hub already deleted, and the
    pool destroyed with the GIL held stopped the end of the process."""
    if _POOL is not None:
        _POOL.clear()
        _POOL.waitForDone()


class _Decode(QRunnable):
    """A tile of the cache read and decoded away from the window's thread (a QImage may be made off the GUI
    thread, a QPixmap may not): the 15 tiles of an opening cost it 75-113 ms, one by one (task 18c, step 9)."""

    def __init__(self, number: int, tile: tuple, path: Path):
        super().__init__()
        self.number, self.tile, self.path = number, tile, path

    def run(self):
        with DECODE_LOCK:
            image = ready(QImage(str(self.path)))
        _HUB.done.emit(self.number, self.tile, image)


class _Arrived(QRunnable):
    """r24-fasi (studio 41, S3): a tile come from the network written to the cache and decoded on a decoders' thread
    (store_and_decode); before, both were done in TileLoader._done on the window's thread, 6-27 ms at each reply,
    the worst frame of a pan 83 ms on the Dell."""

    def __init__(self, number: int, tile: tuple, path: Path, data: bytes):
        super().__init__()
        self.number, self.tile, self.path, self.data = number, tile, path, data

    def run(self):
        image = store_and_decode(self.path, self.data)
        self.data = b""
        _HUB.arrived.emit(self.number, self.tile, image)


class TileLoader(QObject):
    tileReady = Signal(str, int, int, int, QImage)       # source key, z, x, y, image
    tileFailed = Signal(str, int, int, int, str)

    def __init__(self, cache_dir: Path, parent=None, sources: dict | None = None):
        super().__init__(parent)
        self.cache_dir = Path(cache_dir) / "tiles"
        self.sources = sources if sources is not None else dict(tiles.SOURCES)
        self.keys: dict[str, str] = {}  # the designer's keys asked to the keyring, by source
        self.net = QNetworkAccessManager(self)
        self.queue: deque = deque()
        self.queued: set = set()
        self.in_flight: dict = {}
        self.attempts: dict = {}
        self.decoding: set = set()      # tiles of the cache being read in the decoders' threads
        self.arriving: dict = {}        # tiles come from the network being kept and decoded there: tile -> mime
        hub, self.decoders = _decoders()          # the process's: they outlive the loader (_DecodeHub)
        self.number = next(_NUMBERS)
        hub.loaders[self.number] = self
        self._offline = False           # Preferences and project privacy: the cache only, nothing asked to servers
        self.retrying = set()
        self.renewing = set()           # shown from the disk, asked again because their source ages them (R516)
        self.wanted = None
        self.closed = False

    @property
    def offline(self) -> bool:
        return self._offline

    @offline.setter
    def offline(self, value: bool) -> None:
        self._offline = bool(value)
        if self._offline:
            for reply in list(self.in_flight):
                reply.abort()

    def _path(self, key: str, z: int, x: int, y: int) -> Path:
        return tile_path(self.cache_dir.parent, self.sources.get(key) or key, z, x, y)

    def read(self, tile) -> QImage:
        """A tile read from the disk now, on this thread (MapImages, for a tile on show the memory let go)."""
        try:
            with DECODE_LOCK:
                return ready(QImage(str(self._path(*tile))))
        except (TypeError, ValueError):
            return QImage()

    def request(self, key: str, z: int, x: int, y: int, ahead: bool = False) -> None:
        """`ahead`: a tile the view does not show yet (R466), queued behind those it does."""
        tile = (key, z, x, y)
        if (self.closed or tile in self.retrying or tile in self.in_flight.values() or tile in self.decoding
                or tile in self.arriving):
            return
        if tile in self.queued:
            if not ahead and self.queue and self.queue[0] != tile:
                self.queue.remove(tile)
                self.queue.appendleft(tile)
            return
        source = self.sources.get(key)
        if source is None:
            return
        path = self._path(*tile)
        try:
            age = time.time() - path.stat().st_mtime
        except OSError:
            age = None
        if age is not None:
            # R516: what is on disk is shown at once, whatever its age; an old one is renewed after it is shown
            if not self.offline and not source.fresh(age):
                self.renewing.add(tile)
            self.decoding.add(tile)
            self.decoders.start(_Decode(self.number, tile, path), 0 if ahead else 1)
            return
        if self.offline:
            return
        if ahead:
            self.queue.append(tile)
        else:
            self.queue.appendleft(tile)
        self.queued.add(tile)
        self._pump()

    def _decoded(self, tile: tuple, image: QImage) -> None:
        """A tile of the cache read: shown; a file that is not an image is asked to the server, as before."""
        tile = tuple(tile)
        self.decoding.discard(tile)
        if self.closed or (self.wanted is not None and tile not in self.wanted):
            return
        if not image.isNull():
            self.tileReady.emit(*tile, image)
            if tile in self.renewing and not self.offline and tile not in self.queued:
                self.queue.append(tile)         # behind the tiles still missing
                self.queued.add(tile)
                self._pump()
        elif not self.offline and tile not in self.queued and tile not in self.in_flight.values():
            self.renewing.discard(tile)
            self.queue.append(tile)
            self.queued.add(tile)
            self._pump()

    def keep_only(self, wanted: set) -> None:
        """Forget queued tiles the view no longer needs (it moved on)."""
        self.wanted = set(wanted)
        self.queue = deque(t for t in self.queue if t in wanted)
        self.queued = set(self.queue)

    def _pump(self) -> None:
        while not self.closed and not self.offline and self.queue and len(self.in_flight) < MAX_IN_FLIGHT:
            tile = self.queue.popleft()
            self.queued.discard(tile)
            key, z, x, y = tile
            source = self.sources.get(key)
            if source is None:
                continue
            secret = self._key(source)
            if source.needs_key and not secret:
                self.tileFailed.emit(*tile, "no key for this source in the system's keyring")
                continue
            req = QNetworkRequest(QUrl(source.tile_url(z, x, y, key=secret, attempt=self.attempts.get(tile, 0))))
            req.setRawHeader(b"User-Agent", USER_AGENT)
            req.setTransferTimeout(20000)
            reply = self.net.get(req)
            self.in_flight[reply] = tile
            reply.finished.connect(self._finished)

    @Slot()
    def _finished(self):
        # A bound QObject slot has a receiver context. A closure owning the loader can release
        # its last Python reference inside the reply's deferred destructor, destroying its parent.
        self._done(self.sender())

    def _done(self, reply: QNetworkReply) -> None:
        tile = self.in_flight.pop(reply, None)
        data = bytes(reply.readAll())
        mime = str(reply.header(QNetworkRequest.KnownHeaders.ContentTypeHeader) or "")
        error = reply.error()
        why = reply.errorString() if error != QNetworkReply.NetworkError.NoError else f"not an image ({mime})"
        reply.deleteLater()
        if tile is None:
            return
        if error == QNetworkReply.NetworkError.NoError and mime.startswith("image/") and not self.closed:
            # kept on disk and decoded on a decoders' thread (_Arrived), the rest in _arrived; a tile the view
            # no longer wants is kept on disk all the same (R516), it was paid for
            self.arriving[tile] = why
            self.decoders.start(_Arrived(self.number, tile, self._path(*tile), data), 1)
        else:
            self._settle(tile, QImage(), why)
        self._pump()

    def _arrived(self, tile: tuple, image: QImage) -> None:
        tile = tuple(tile)
        why = self.arriving.pop(tile, None)
        if why is None:
            return
        self._settle(tile, image, why)
        self._pump()

    def _settle(self, tile: tuple, image: QImage, why: str) -> None:
        """A tile come from the network, decoded (stored already when it is an image): shown, or asked again."""
        if self.closed or self.offline or (self.wanted is not None and tile not in self.wanted):
            self.attempts.pop(tile, None)
            self.renewing.discard(tile)
            return
        if not image.isNull():
            self.attempts.pop(tile, None)
            self.renewing.discard(tile)
            self.tileReady.emit(*tile, image)
            return
        n = self.attempts.get(tile, 0)
        if n < len(RETRIES):
            self.attempts[tile] = n + 1
            self.retrying.add(tile)
            QTimer.singleShot(int(RETRIES[n] * 1000), self, lambda t=tile: self._retry(t))
        else:
            self.attempts.pop(tile, None)
            if tile in self.renewing:
                # an old tile is on show: it stays, and is asked again the next time it is wanted
                self.renewing.discard(tile)
            else:
                self.tileFailed.emit(*tile, self._masked(tile[0], why))

    def _retry(self, tile):
        self.retrying.discard(tile)
        if self.closed or self.offline or (self.wanted is not None and tile not in self.wanted):
            self.attempts.pop(tile, None)
            self.renewing.discard(tile)
            return
        if tile not in self.queued and tile not in self.in_flight.values():
            self.queue.append(tile)
            self.queued.add(tile)
        self._pump()

    def close(self):
        """Stop requests before destroying an engine; no queued retry can revive them."""
        self.closed = True
        self.keep_only(set())
        self.offline = True
        self.decoders.waitForDone()

    def _key(self, source) -> str:
        """The designer's key of a source that needs one, from the keyring (asked once); "" when there is none or
        no keyring."""
        if not source.needs_key:
            return ""
        if source.key not in self.keys:
            from ...assistant import keys
            try:
                self.keys[source.key] = keys.get(source.key, service=KEYS)
            except keys.KeyringMissing as error:
                log.complain("map key", error)
                self.keys[source.key] = ""
        return self.keys[source.key]

    def _masked(self, key: str, text: str) -> str:
        """What is said of a failure without the key in it (Qt's message carries the address)."""
        from ...assistant.keys import masked
        secret = self.keys.get(key, "")
        return text.replace(secret, masked(secret)) if secret else text

class MapImages(QQuickImageProvider):
    """Decoded images shared with QML without re-reading or re-encoding a tile on the GUI thread. They stay in
    memory within the tiles' share of the memory budget (resources.Cache, R466): a zoom or a place seen before comes
    back from here, not from the disk or the server.

    R516: the tiles on show (`pin`) leave the memory last, and a tile on show that left it is read again from the
    disk (`reread`) when Qt asks it again (an Image made again, the scene graph rebuilt): before, it came back empty
    and stayed so, since the plan believed it loaded. An identifier made older by the same tile come again (the ring
    around, a renewal) still gives the tile."""

    KEEP_IDS = 4096                     # identifiers remembered beyond the memory's tiles and the pinned ones

    def __init__(self, reread=None):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self.cache = resources.Cache(self._limit, lambda entry: entry[1].sizeInBytes() + 512)
        self._limit_at = (-1e9, 0)
        self.reread = reread
        self.by_id = {}                 # identifier -> tile
        self.lock = RLock()

    LIMIT_EVERY = 2.0                   # seconds a reading of the memory's budget is good for

    def _limit(self):
        """The tiles' share of the memory, read again at most every LIMIT_EVERY seconds: read at each tile put
        (resources.system_memory) it cost 20 ms to a pan of 96 tiles on the window's thread (studio 41, S3)."""
        now = time.monotonic()
        at, limit = self._limit_at
        if now - at > self.LIMIT_EVERY:
            limit = resources.cache_limit('tiles')
            self._limit_at = (now, limit)
        return limit

    def requestImage(self, identifier, size, requested_size):
        with self.lock:
            tile = self.by_id.get(identifier)
            entry = self.cache.get(tile) if tile is not None else None
            image = entry[1] if entry is not None else QImage()
        if image.isNull() and tile is not None and self.reread is not None:
            image = self.reread(tile)
            if not image.isNull():
                with self.lock:
                    self.cache.put(tile, (identifier, image))
        size.setWidth(image.width())
        size.setHeight(image.height())
        return image

    def pin(self, tiles):
        """The tiles on show: the last to leave the memory."""
        self.cache.pinned = set(tiles)

    def put(self, identifier, tile, image, cost=1.0):
        with self.lock:
            self.cache.put(tile, (identifier, image), cost)
            self.by_id[identifier] = tile
            if len(self.by_id) > 2 * len(self.cache) + self.KEEP_IDS:
                keep, items = self.cache.pinned, list(self.by_id.items())
                self.by_id = {i: t for i, t in items if t in keep or t in self.cache}
                self.by_id.update(items[-self.KEEP_IDS:])

    def url_of(self, tile):
        """The image's address when the tile is in memory, else None."""
        with self.lock:
            entry = self.cache.get(tile)
            return entry[0] if entry is not None else None

    def __contains__(self, tile):
        with self.lock:
            return self.cache.get(tile) is not None


class TileModel(QAbstractListModel):
    """The parts of the tiles on show, as a model that adds and removes only what changes: a Repeater over a plain
    list made every Image again at each tile that arrived (R466)."""

    ROLES = ('url', 'clipRect', 'quad', 'key', 'zoom')          # names free of Item's and Image's own
    FIELDS = dict(url='source', clipRect='clip', quad='matrix', key='key', zoom='zoom')

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def roleNames(self):
        return {Qt.ItemDataRole.UserRole + i: QByteArray(name.encode()) for i, name in enumerate(self.ROLES)}

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        name = self.ROLES[role - Qt.ItemDataRole.UserRole] if 0 <= role - Qt.ItemDataRole.UserRole < len(self.ROLES) else None
        return self._rows[index.row()].get(self.FIELDS[name]) if name else None

    @staticmethod
    def _identity(record):
        return record['source'], tuple(record['clip'])

    def set_records(self, records):
        wanted = {self._identity(r) for r in records}
        # removed, from the end so the rows above keep their numbers
        for row in range(len(self._rows) - 1, -1, -1):
            if self._identity(self._rows[row]) not in wanted:
                self.beginRemoveRows(QModelIndex(), row, row)
                del self._rows[row]
                self.endRemoveRows()
        present = {self._identity(r) for r in self._rows}
        new = [r for r in records if self._identity(r) not in present]
        if new:
            self.beginInsertRows(QModelIndex(), len(self._rows), len(self._rows) + len(new) - 1)
            self._rows.extend(new)
            self.endInsertRows()

    @property
    def records(self):
        return list(self._rows)


class MapController(QObject):
    """Qt transport for PlanMaps. updateView is called when a gesture settles, never at each move."""

    changed = Signal()
    error = Signal(str)

    def __init__(self, cache_dir: Path, parent=None, *, origin=None, sources=None, offline=False):
        super().__init__(parent)
        self.state = PlanMaps(origin, sources=sources)
        self.loader = TileLoader(cache_dir, self, sources=self.state.sources)
        self.loader.offline = offline
        self.loader.tileReady.connect(self._ready)
        self.loader.tileFailed.connect(self._failed)
        self.provider = MapImages(reread=self.loader.read)
        self.state.memory = self._memory_url        # the stand-ins of the tiles on their way (R540)
        self.provider_name = 'planmaps' + uuid4().hex
        self._tiles, self._underlays, self._world = [], [], {}
        self._model = TileModel(self)
        self._ahead = QTimer(self)
        self._ahead.setSingleShot(True)
        self._ahead.setInterval(250)
        self._ahead.timeout.connect(self._ask_ahead)
        self._world_key = None
        self._generation = 0
        self._published = None
        self.cache_dir = Path(cache_dir)
        self.area = None                # the area of the project kept ahead (plan_offline.AreaDownload), R516
        self._area_key = None
        self._offline_text = ''

    def _memory_url(self, tile):
        identifier = self.provider.url_of(tile)
        return None if identifier is None else f'image://{self.provider_name}/{identifier}'

    def install(self, engine):
        engine.addImageProvider(self.provider_name, self.provider)

    def configure(self, *, origin=None, custom_sources=None, offline=None, underlays=None):
        if origin is not None and origin != self.state.origin:
            self.state.origin = origin
            self.state.loaded.clear()
            self.state.unavailable.clear()
        if custom_sources is not None:
            self.state.set_catalogue(custom_sources)
            self.loader.sources = self.state.sources
            self.loader.keys.clear()
        if offline is not None:
            self.loader.offline = offline
            if offline and self.area is not None and not self.area.finished:
                self.area.stop()
        if underlays is not None:
            self._underlays = [underlay_record(item) for item in underlays]
        self.state.choose()
        self._refresh()
        self._fetch_ahead()

    @Slot(float, float, float, float, float, float)
    def updateView(self, west, south, east, north, mpp, dpr=1):
        self.state.set_view((west, south, east, north), mpp, dpr)
        self._refresh()
        self._fetch_ahead()

    @Slot(str)
    def setSource(self, choice):
        self.state.set_source(choice)
        self._refresh()
        self._fetch_ahead()

    @Slot()
    def retryBackground(self):
        self.state.retry()
        self._refresh()
        self._fetch_ahead()

    def _fetch_ahead(self):
        """The tiles around the view and one zoom out, asked once per view, behind those on show (R466): a moment
        after the view settles, so their 100-200 looks at the disk cache never delay the tiles on show."""
        self._ahead.start()

    def _ask_ahead(self):
        for tile in self.state.around:
            if tile not in self.provider:
                self.loader.request(*tile, ahead=True)

    @Slot(float)
    def setVeil(self, strength):
        self.state.veil = min(1.0, max(0.0, strength))
        self.changed.emit()

    @Slot()
    def close(self):
        if self.area is not None:
            self.area.stop()
        self.loader.close()

    def keepArea(self, bounds):
        """R516: the area of the project (`bounds`, west, south, east, north in metres of the plan around the
        site's origin) kept on disk once, in background, at every useful zoom of the orthophoto the plan shows
        near: from then on the plan works without network. Only for a source whose licence allows it
        (Source.bulk), never with the network off; a run cut short goes on from where it was next time."""
        from . import plan_offline
        source = self.sources_photo()
        if source is None or not source.bulk or self.loader.offline:
            return
        area = plan_offline.area_tiles(source, self.state.origin, bounds)
        key = (source.cache_name, frozenset(area))
        if key == self._area_key and self.area is not None:
            return
        if self.area is not None:
            self.area.stop()
        self._area_key = key
        self.area = plan_offline.AreaDownload(self.cache_dir, source, area, self)
        self.area.progress.connect(self._area_progress)
        # a moment after the plan opened: the tiles on show come first
        QTimer.singleShot(int(plan_offline.START_DELAY * 1000), self.area, self.area.start)

    def sources_photo(self):
        """The orthophoto the plan shows near the site for the designer's choice."""
        key = tiles.effective(self.state.choice, self.state.sources, self.state.origin.lon, self.state.origin.lat, .3)
        source = self.state.sources.get(key)
        return source if source is not None and source.imagery == 'photo' else None

    def _area_progress(self, done, total):
        text = '' if done >= total else _('Keeping the orthophoto for use without network: {percent} %').format(
            percent=int(100 * done / max(1, total)))
        if text != self._offline_text:
            self._offline_text = text
            self.changed.emit()

    def _refresh(self):
        state = self.state
        self.loader.keep_only(state.wanted | state.around | state.backdrop)
        # What the memory already holds is on show at once: nothing is read or asked again (R466).
        for tile in state.wanted - state.loaded.keys():
            identifier = self.provider.url_of(tile)
            if identifier is not None:
                state.ready(tile, f'image://{self.provider_name}/{identifier}')
        for tile in state.backdrop - state.under.keys():
            identifier = self.provider.url_of(tile)
            if identifier is not None:
                state.ready(tile, f'image://{self.provider_name}/{identifier}')
        self._tiles = state.records()
        self.provider.pin(set(state.loaded) | set(state.under))
        self._model.set_records(self._tiles)
        if state.mpp >= 250:
            world_key = (state.origin, state.equal_earth)
            if world_key != self._world_key:
                self._world = state.world()
                self._world_key = world_key
        # A camera movement transforms retained QML items. Notify only when their
        # data changes, otherwise the underlay delegates are recreated.
        published = (self._underlays, self._world, self.attribution,
                     self.fallbackMessage, self.equalEarth, self.worldVisible,
                     self.veil, self.sourceKey, self.choice, self.retryText, self._offline_text)
        if published != self._published:
            self._published = published
            self.changed.emit()
        for tile in state.wanted - state.loaded.keys():
            self.loader.request(*tile)
        # asked last, so first in the queue: the few coarse tiles that keep the bands away (R540)
        for tile in state.backdrop - state.under.keys():
            self.loader.request(*tile)

    def _ready(self, key, z, x, y, image):
        tile = (key, z, x, y)
        if tile not in self.state.wanted and tile not in self.state.around and tile not in self.state.backdrop:
            return
        self._generation += 1
        identifier = str(self._generation)
        self.provider.put(identifier, tile, image)
        if tile not in self.state.wanted and tile not in self.state.backdrop:
            return
        self.state.ready(tile, f'image://{self.provider_name}/{identifier}')
        self._refresh()

    def _failed(self, key, z, x, y, why):
        if self.state.failed((key, z, x, y)):
            self._refresh()
        self.error.emit(why)

    tileParts = Property('QVariantList', lambda self: self._tiles, notify=changed)
    tileModel = Property(QObject, lambda self: self._model, constant=True)
    underlays = Property('QVariantList', lambda self: self._underlays, notify=changed)
    world = Property('QVariantMap', lambda self: self._world, notify=changed)
    attribution = Property(str, lambda self: self.state.attribution, notify=changed)
    fallbackMessage = Property(str, lambda self: self.state.fallback_message, notify=changed)
    equalEarth = Property(bool, lambda self: self.state.equal_earth, notify=changed)
    worldVisible = Property(bool, lambda self: self.state.mpp >= 250, notify=changed)
    veil = Property(float, lambda self: self.state.veil if self.state.veil_visible else 0, notify=changed)
    sourceKey = Property(str, lambda self: self.state.source, notify=changed)
    choice = Property(str, lambda self: self.state.choice, notify=changed)
    retryText = Property(str, lambda self: _('Retry'), notify=changed)
    offlineText = Property(str, lambda self: self._offline_text, notify=changed)
