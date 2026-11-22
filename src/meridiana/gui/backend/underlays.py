"""The images under the drawing in the window (underlay.py says where their pixels go): read from a file, a PNG, a
JPEG or the first page of a PDF (with Qt's own PDF module, part of PySide6: PyMuPDF is not among Meridiana's
libraries), kept small enough for the project, drawn on the plan with their transparency.

Study 56, point 4: the plan shows them through the image provider `underlay` (`image://underlay/<key>/<side>`),
never as a `data:` URL. Before, the QML's Image decoded the whole picture on the window's thread when its delegate
was made (650 ms for 4096 px) and the map's records carried its base64 (25 MB) to the QML at each change of the map.
Now the image is decoded on Qt's loading threads, at the side the view needs (a pyramid: SIDES, the long side in
pixels, a JPEG decoded straight at that size), the smallest shown at once under the right one, every level kept in
the budget's images (a resources.Cache: it gives memory back with the others)."""

from __future__ import annotations

import base64
import binascii
import threading
import time
import zlib
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QSize, Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter
from PySide6.QtQuick import QQuickImageProvider

from meridiana.core.compute import resources
from meridiana.core.model import underlay
from meridiana.i18n import _

PDF_DPI = 200                   # a page of a PDF drawn at this density, then kept within underlay.MAX_SIDE
PROVIDER = "underlay"           # image://underlay/<key>/<side>
SIDES = (256, 512, 1024, 2048, 4096)    # the pyramid's levels, the long side in pixels (the first one shown at once)
SOURCES_MOST = 64               # underlays whose data the provider can find (the project's, and a few just gone)


def pdf_available() -> bool:
    try:
        from PySide6.QtPdf import QPdfDocument  # noqa: F401
    except ImportError:
        return False
    return True


def file_filter() -> str:
    images = _("Images (*.png *.jpg *.jpeg)")
    if not pdf_available():
        return images
    return _("Images and PDF (*.png *.jpg *.jpeg *.pdf)") + ";;" + images + ";;" + _("PDF, the first page (*.pdf)")


def _encoded(image: QImage, kind: str) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, kind, 90 if kind == "JPG" else -1)
    buffer.close()
    return bytes(data)


def _pdf_page(path: Path) -> QImage:
    from PySide6.QtPdf import QPdfDocument
    doc = QPdfDocument()
    if doc.load(str(path)) != QPdfDocument.Error.None_ or doc.pageCount() < 1:
        raise ValueError(_("The PDF could not be read (damaged, or with a password)."))
    points = doc.pagePointSize(0)
    w, h = underlay.fitted_size(round(points.width() * PDF_DPI / 72), round(points.height() * PDF_DPI / 72))
    page = doc.render(0, QSize(w, h))
    out = QImage(page.size(), QImage.Format.Format_RGB32)       # on white: a PDF page has no background
    out.fill(QColor("white"))
    painter = QPainter(out)
    painter.drawImage(0, 0, page)
    painter.end()
    doc.close()
    return out


def read_image(path: Path) -> tuple[str, int, int]:
    """The image of a file as the project keeps it: (base64 of a PNG or JPEG file, width, height). ValueError, said
    in words, when it cannot be read."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        if not pdf_available():
            raise ValueError(_("This installation cannot read PDF files: import the page as an image."))
        image = _pdf_page(path)
        return base64.b64encode(_encoded(image, "PNG")).decode("ascii"), image.width(), image.height()
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ValueError(_("The file could not be read: {why}").format(why=error.strerror or error)) from error
    image = QImage()
    if not image.loadFromData(raw):
        raise ValueError(_("This is not an image Meridiana can read (PNG or JPEG)."))
    w, h = underlay.fitted_size(image.width(), image.height())
    if (w, h) != (image.width(), image.height()):
        image = image.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    # always re-encoded, never the file as it is: a photo carries EXIF (where and when it was taken, the
    # camera), and the project file travels (study 18, G 6.2)
    data = _encoded(image, "JPG" if suffix in (".jpg", ".jpeg") else "PNG")
    return base64.b64encode(data).decode("ascii"), w, h


# The pyramid (study 56, point 4)

_LOCK = threading.Lock()
_SOURCES: dict = {}             # key -> the underlay's base64, the same string the project holds (not a copy)
# (key, side) -> QImage, within the budget's images; a level costs the seconds it took to decode
_LEVELS = resources.Cache(lambda: resources.cache_limit("images"), lambda image: image.sizeInBytes() + 256)
# key -> the picture's file (the base64 decoded once), for the next levels of the same picture
_RAW = resources.Kept(lambda: resources.cache_limit("images"), len, most=8)
B64_PIECE = 1 << 20             # base64 decoded this much at a time: the interpreter goes back to the window between
decoded: list = []              # (key, side, on the window's thread) of the last decodings, for the tests and probes


def key_of(u: underlay.Underlay) -> str:
    """A name of the underlay's picture that changes with it: its id, the length and a digest of its two ends (the
    whole 25 MB of a 4096 px picture took 7 ms at each record, on the window's thread)."""
    ends = (u.image[:4096] + u.image[-4096:]).encode("ascii")
    return f"{u.id}-{len(u.image)}-{zlib.crc32(ends) & 0xFFFFFFFF:08x}"


def levels(u: underlay.Underlay) -> list[int]:
    """The pyramid's sides for an underlay: those of SIDES under its long side, then the long side itself."""
    longest = max(1, u.width, u.height)
    return [s for s in SIDES if s < longest] + [longest]


def source_of(u: underlay.Underlay) -> dict:
    """What the plan's QML needs to show an underlay: the provider's address of its picture (without the side),
    its pyramid's sides, its long side in metres (for the side the view needs). The data stays here."""
    key = key_of(u)
    with _LOCK:
        _SOURCES.pop(key, None)
        _SOURCES[key] = u.image
        while len(_SOURCES) > SOURCES_MOST:
            _SOURCES.pop(next(iter(_SOURCES)))
    return dict(source=f"image://{PROVIDER}/{key}", levels=levels(u),
                metres=max(u.width, u.height) * max(u.scale, 1e-9))


def level(key: str, side: int) -> QImage:
    """The picture `key` with its long side at `side` pixels (at most its own): kept, or decoded now (a JPEG straight
    at that size). A null image when the key is unknown or the data cannot be read."""
    found = _LEVELS.get((key, side))
    if found is not None:
        return found
    began = time.perf_counter()
    raw = _RAW.get(key)
    if raw is None:
        with _LOCK:
            data = _SOURCES.get(key)
        if data is None:
            return QImage()
        # in pieces: the whole 25 MB at once held the interpreter, and so the window's Python, for 20-60 ms
        raw = b"".join(binascii.a2b_base64(data[at:at + B64_PIECE]) for at in range(0, len(data), B64_PIECE))
        _RAW[key] = raw
    reader = QImageReader()
    buffer = QBuffer()
    buffer.setData(QByteArray(raw))
    buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    reader.setDevice(buffer)
    size = reader.size()
    if size.isValid() and max(size.width(), size.height()) > side:
        k = side / max(size.width(), size.height())
        reader.setScaledSize(QSize(max(1, round(size.width() * k)), max(1, round(size.height() * k))))
    image = reader.read()
    buffer.close()
    if image.isNull():
        return image
    _LEVELS.put((key, side), image, cost=time.perf_counter() - began)
    with _LOCK:
        decoded.append((key, side, threading.current_thread() is threading.main_thread()))
        del decoded[:-64]
    return image


class UnderlayImages(QQuickImageProvider):
    """`image://underlay/<key>/<side>`: a level of the pyramid, asked by Qt on its loading threads (the Images are
    asynchronous: the window's thread never decodes)."""

    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image,
                         QQuickImageProvider.Flag.ForceAsynchronousImageLoading)

    def requestImage(self, identifier, size, requested_size):
        key, _sep, side = identifier.rpartition("/")
        image = level(key, int(side)) if side.isdigit() else QImage()
        size.setWidth(image.width())
        size.setHeight(image.height())
        return image
