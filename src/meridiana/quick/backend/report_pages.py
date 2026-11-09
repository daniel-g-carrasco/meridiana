"""R509: the pages of the report's preview, drawn from the PDF at the size they are shown, in device pixels.

The worker (report_worker.py, ui/report.preview_pages) writes the report's PDF and says, for each page, the PDF and
the page it comes from. A page shown asks for itself at its width times the screen's pixel ratio (`want`: its key and
that width), again after a zoom: each is a fresh render of the vector page, never a fixed picture scaled up (the
preview was a 1240 px image shown 822 points wide, 2055 device pixels on a screen at 2,5: soft, 06/11/2026).

The render runs as a job on Qt's pool and the page's Image takes it from here, on the window's thread, when it is done:
Python never runs on Qt Quick's image reader thread (an asynchronous Image on a Python provider locked the window
when the pages far from the view let go of their requests, 38 pages, 06/11/2026). Each job opens its own
QPdfDocument on the PDF's bytes, read once and kept: no file stays open (Windows would refuse to delete the
preview's folder) and no Qt object crosses threads."""
from __future__ import annotations

import itertools
import threading
from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, QRunnable, QSize, QThreadPool, Signal
from PySide6.QtGui import QColor, QImage
from PySide6.QtQuick import QQuickImageProvider

NAME = 'reportpage'
KEPT = 12                       # pages drawn and not yet taken by their Image: a zoom asks again for those shown

_lock = threading.Lock()
_rows: dict[str, dict] = {}
_data: dict[str, bytes] = {}
_tokens = itertools.count(1)
_ready: OrderedDict[str, QImage] = OrderedDict()
_pending: set[str] = set()
drawn: list[tuple[str, int, int]] = []     # (key, width, height) of the last renders, for the tests


class _Signals(QObject):
    done = Signal(str)


signals = None


def _signals():
    global signals
    if signals is None:
        signals = _Signals()
    return signals


def publish(rows):
    """The rows of a new preview, each with its key; the pages of the previous ones are forgotten."""
    token = next(_tokens)
    shown = []
    with _lock:
        _rows.clear()
        _data.clear()
        _ready.clear()
        for n, row in enumerate(rows):
            key = f'{token}/{n}'
            _rows[key] = dict(row)
            shown.append({**row, 'source': key})
    return shown


def _bytes(path):
    with _lock:
        found = _data.get(path)
    if found is None:
        found = Path(path).read_bytes()
        with _lock:
            _data[path] = found
    return found


def render(key, width):
    """The page `key` as an image `width` pixels wide (its height from the page's ratio), on white."""
    from meridiana.ui import report
    with _lock:
        row = _rows.get(key)
    width = max(1, int(width))
    if row is None:
        image = QImage(width, max(1, round(width * 297 / 210)), QImage.Format.Format_RGB32)
        image.fill(QColor('white'))
        return image
    if row.get('note'):
        image = report.note_page(row['note'], width)
    else:
        from PySide6.QtPdf import QPdfDocument
        buffer = QBuffer()
        buffer.setData(QByteArray(_bytes(row['path'])))
        buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        pdf = QPdfDocument()
        try:
            pdf.load(buffer)
            image = report._on_white(pdf.render(row['index'], QSize(width, round(width * row['ratio']))))
        finally:
            pdf.close()
            buffer.close()
    with _lock:
        drawn.append((key, image.width(), image.height()))
        del drawn[:-64]
    return image


class _Draw(QRunnable):
    def __init__(self, want):
        super().__init__()
        self.want = want

    def run(self):
        key, _sep, width = self.want.rpartition('/')
        try:
            image = render(key, int(width))
        except (OSError, ValueError) as error:
            from meridiana import log
            log.complain('report preview page', error)
            image = QImage()
        with _lock:
            _pending.discard(self.want)
            _ready[self.want] = image
            while len(_ready) > KEPT:
                _ready.popitem(last=False)
        _signals().done.emit(self.want)


def ask(want):
    """`want` («key/width»): drawn on the pool unless it is already drawn or on its way; `signals.done` says it."""
    with _lock:
        if want in _ready:
            done = True
        elif want in _pending:
            return
        else:
            done = False
            _pending.add(want)
    if done:
        _signals().done.emit(want)
        return
    QThreadPool.globalInstance().start(_Draw(want))


def take(want):
    """The image drawn for `want`, handed over once (its Image keeps it); a white page if it is not there."""
    with _lock:
        image = _ready.pop(want, None)
    if image is None or image.isNull():
        key, _sep, width = want.rpartition('/')
        with _lock:
            row = _rows.get(key)
        width = max(1, int(width) if width.isdigit() else 1)
        image = QImage(width, max(1, round(width * (row['ratio'] if row else 297 / 210))), QImage.Format.Format_RGB32)
        image.fill(QColor('white'))
    return image


class PageProvider(QQuickImageProvider):
    """Synchronous on purpose (the Image is not asynchronous): it only hands over what a job drew."""

    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)

    def requestImage(self, identifier, size, requestedSize):
        image = take(identifier)
        size.setWidth(image.width())
        size.setHeight(image.height())
        return image


def install(engine):
    """Idempotently give `engine` the provider of the preview's pages."""
    if not getattr(engine, '_meridiana_report_pages', None):
        provider = PageProvider()
        engine.addImageProvider(NAME, provider)
        engine._meridiana_report_pages = provider
