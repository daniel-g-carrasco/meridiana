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
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, Property, QRunnable, QSize, QThreadPool, Signal, Slot
from PySide6.QtGui import QColor, QGuiApplication, QImage
from PySide6.QtQuick import QQuickImageProvider

from meridiana.core.compute import resources

NAME = 'reportpage'
KEPT = 12                       # pages drawn and not yet taken by their Image: a zoom asks again for those shown

_lock = threading.Lock()
_rows: dict[str, dict] = {}
_data: dict[str, bytes] = {}
_tokens = itertools.count(1)
_generation = 0
# pages drawn and not yet taken, within the budget's images (study 56: 12 pages of 2055 px were 290 MB outside it); the
# last one drawn stays whatever its size until its Image takes it
_ready = resources.Kept(lambda: resources.cache_limit('images'), lambda image: image.sizeInBytes() + 256, most=KEPT)
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
    global _generation
    token = next(_tokens)
    shown = []
    with _lock:
        _generation = token
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
        generation = _generation
    if found is None:
        found = Path(path).read_bytes()
        with _lock:
            if generation == _generation:
                _data[path] = found
    return found


def render(key, width):
    """The page `key` as an image `width` pixels wide (its height from the page's ratio), on white."""
    from meridiana.gui.paper import report
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
            from meridiana.app.platform import log
            log.complain('report preview page', error)
            image = QImage()
        with _lock:
            _pending.discard(self.want)
            _ready.put(self.want, image, force=True)
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
        engine._report_text = PageText(engine)
        engine.rootContext().setContextProperty('reportText', engine._report_text)


def extract_text(key):
    """Extract on the calling worker, with a document and buffer owned by that thread."""
    from PySide6.QtPdf import QPdfDocument
    with _lock:
        row = _rows.get(key)
    if row is None:
        return ''
    if row.get('note'):
        return row['note']
    buffer = QBuffer()
    buffer.setData(QByteArray(_bytes(row['path'])))
    buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    document = QPdfDocument()
    try:
        document.load(buffer)
        if document.status() != QPdfDocument.Status.Ready:
            raise ValueError(f'PDF text: {document.error()}')
        return document.getAllText(row['index']).text()
    finally:
        document.close()
        buffer.close()


class _TextSignals(QObject):
    done = Signal(int, str, str, str)


class _Extract(QRunnable):
    def __init__(self, token, key):
        super().__init__()
        self.token, self.key = token, key
        self.signals = _TextSignals()

    def run(self):
        text, error = '', ''
        try:
            text = extract_text(self.key)
        except (OSError, ValueError, RuntimeError) as failure:
            from meridiana.app.platform import log
            log.complain('report page text', failure)
            error = str(failure)
        self.signals.done.emit(self.token, self.key, text, error)


class PageText(QObject):
    """One cancellable request per view. Only the GUI thread may change the clipboard."""
    changed = Signal()
    readReady = Signal()
    errorOccurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._token, self._busy, self._text, self._error = 0, False, '', ''
        self._copy, self._empty = False, set()
        self._jobs = {}

    @Property(bool, notify=changed)
    def busy(self):
        return self._busy

    @Property(str, notify=changed)
    def text(self):
        return self._text

    @Property(str, notify=changed)
    def error(self):
        return self._error

    @Slot(str, result=bool)
    def canCopy(self, key):
        with _lock:
            return key in _rows and key not in self._empty and not self._busy

    @Slot()
    def cancel(self):
        self._token += 1
        self._busy = False
        self.changed.emit()

    @Slot(str, bool)
    def request(self, key, copy):
        self.cancel()
        self._copy, self._busy, self._text, self._error = copy, True, '', ''
        worker = _Extract(self._token, key)
        self._jobs[self._token] = worker
        worker.signals.done.connect(self._finish)
        self.changed.emit()
        QThreadPool.globalInstance().start(worker)

    @Slot(int, str, str, str)
    def _finish(self, token, key, text, error):
        self._jobs.pop(token, None)
        if token != self._token:
            return
        self._busy = False
        with _lock:
            valid = key in _rows
        if not valid:
            self.changed.emit()
            return
        self._text, self._error = text, error
        if not text and not error:
            self._empty.add(key)
        self.changed.emit()
        if error:
            self.errorOccurred.emit(error)
        elif self._copy:
            if text:
                QGuiApplication.clipboard().setText(text)
        else:
            self.readReady.emit()
