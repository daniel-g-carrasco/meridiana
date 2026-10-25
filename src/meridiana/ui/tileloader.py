"""Fetching background tiles without stopping the window: QNetworkAccessManager, at most six requests at a
time, a disk cache (paths.cache, a folder for each source: Source.cache_name) written whole or not at all, an
identifying User-Agent as OpenStreetMap's policy asks (the same for every server), and a few retries for the
national orthophoto, whose server at times answers with an error document instead of the image. A tile that never
comes leaves the plan usable, only without that piece of background.

The sources are those of the plan (`sources`, the program's and the designer's, tiles.catalogue). A designer's
source with `{key}` in its address gets the key from the system's keyring when its first tile is asked; the key is
never written in the cache's names, in the log or in what is said of a failure."""

from __future__ import annotations

import os
import tempfile
import time
from collections import deque
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, QUrl, Signal
from PySide6.QtGui import QImage
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from .. import SLUG, __version__, log, tiles
from . import tell

USER_AGENT = f"Meridiana/{__version__} (+https://github.com/daniel-g-carrasco/meridiana)".encode()
MAX_IN_FLIGHT = 6
RETRIES = (1.0, 3.0)
DECODERS = 2                    # threads that read and decode the cached tiles
KEYS = f"{SLUG}-maps"           # the keyring's service of the designer's map keys (assistant/keys.py)


class _DecodeSignals(QObject):
    done = Signal(object, QImage)   # the tile (key, z, x, y), its image (null when the file is not one)


class _Decode(QRunnable):
    """A tile of the cache read and decoded away from the window's thread (a QImage may be made off the GUI
    thread, a QPixmap may not): the 15 tiles of an opening cost it 75-113 ms, one by one (task 18c, step 9)."""

    def __init__(self, tile: tuple, path: Path):
        super().__init__()
        self.tile, self.path = tile, path
        self.signals = _DecodeSignals()

    def run(self):
        tell(self.signals.done, self.tile, QImage(str(self.path)))


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
        self.decoders = QThreadPool(self)
        self.decoders.setMaxThreadCount(DECODERS)
        self.offline = False            # Preferences > Privacy: the cache only, nothing asked to the servers

    def _path(self, key: str, z: int, x: int, y: int) -> Path:
        source = self.sources.get(key)
        return self.cache_dir / (source.cache_name if source else key) / str(z) / str(x) / f"{y}.img"

    def request(self, key: str, z: int, x: int, y: int) -> None:
        tile = (key, z, x, y)
        if tile in self.queued or tile in self.in_flight.values() or tile in self.decoding:
            return
        source = self.sources.get(key)
        if source is None:
            return
        path = self._path(*tile)
        try:
            fresh = path.exists() and time.time() - path.stat().st_mtime < source.max_age_days * 86400
        except OSError:
            fresh = False
        if fresh or (self.offline and path.exists()):
            self.decoding.add(tile)
            job = _Decode(tile, path)
            job.signals.done.connect(self._decoded)
            self.decoders.start(job)
            return
        if self.offline:
            return
        self.queue.append(tile)
        self.queued.add(tile)
        self._pump()

    def _decoded(self, tile: tuple, image: QImage) -> None:
        """A tile of the cache read: shown; a file that is not an image is asked to the server, as before."""
        tile = tuple(tile)
        self.decoding.discard(tile)
        if not image.isNull():
            self.tileReady.emit(*tile, image)
        elif not self.offline and tile not in self.queued and tile not in self.in_flight.values():
            self.queue.append(tile)
            self.queued.add(tile)
            self._pump()

    def keep_only(self, wanted: set) -> None:
        """Forget queued tiles the view no longer needs (it moved on)."""
        self.queue = deque(t for t in self.queue if t in wanted)
        self.queued = set(self.queue)

    def _pump(self) -> None:
        while self.queue and len(self.in_flight) < MAX_IN_FLIGHT:
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
            req = QNetworkRequest(QUrl(source.tile_url(z, x, y, key=secret)))
            req.setRawHeader(b"User-Agent", USER_AGENT)
            req.setTransferTimeout(20000)
            reply = self.net.get(req)
            self.in_flight[reply] = tile
            reply.finished.connect(lambda r=reply: self._done(r))

    def _done(self, reply: QNetworkReply) -> None:
        tile = self.in_flight.pop(reply, None)
        data = bytes(reply.readAll())
        mime = str(reply.header(QNetworkRequest.KnownHeaders.ContentTypeHeader) or "")
        error = reply.error()
        reply.deleteLater()
        if tile is None:
            return
        image = QImage.fromData(data) if error == QNetworkReply.NetworkError.NoError and mime.startswith("image/") else QImage()
        if not image.isNull():
            self._store(tile, data)
            self.attempts.pop(tile, None)
            self.tileReady.emit(*tile, image)
        else:
            n = self.attempts.get(tile, 0)
            if n < len(RETRIES):
                self.attempts[tile] = n + 1
                QTimer.singleShot(int(RETRIES[n] * 1000), self,
                                  lambda t=tile: (self.queue.append(t), self.queued.add(t), self._pump()))
            else:
                self.attempts.pop(tile, None)
                why = reply.errorString() if error != QNetworkReply.NetworkError.NoError else f"not an image ({mime})"
                self.tileFailed.emit(*tile, self._masked(tile[0], why))
        self._pump()

    def _key(self, source) -> str:
        """The designer's key of a source that needs one, from the keyring (asked once); "" when there is none or
        no keyring."""
        if not source.needs_key:
            return ""
        if source.key not in self.keys:
            from ..assistant import keys
            try:
                self.keys[source.key] = keys.get(source.key, service=KEYS)
            except keys.KeyringMissing as error:
                log.complain("map key", error)
                self.keys[source.key] = ""
        return self.keys[source.key]

    def _masked(self, key: str, text: str) -> str:
        """What is said of a failure without the key in it (Qt's message carries the address)."""
        from ..assistant.keys import masked
        secret = self.keys.get(key, "")
        return text.replace(secret, masked(secret)) if secret else text

    def _store(self, tile, data: bytes) -> None:
        path = self._path(*tile)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.replace(tmp, path)
        except OSError as error:
            # a full disk or a read-only cache: the tile is shown anyway, only not kept
            log.complain("tile cache", error)
