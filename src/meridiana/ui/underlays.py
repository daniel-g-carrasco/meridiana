"""The images under the drawing in the window (underlay.py says where their pixels go): read from a file, a PNG, a
JPEG or the first page of a PDF (with Qt's own PDF module, part of PySide6: PyMuPDF is not among Meridiana's
libraries), kept small enough for the project, drawn on the plan with their transparency."""

from __future__ import annotations

import base64
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap, QTransform

from .. import underlay
from ..i18n import _

PDF_DPI = 200                   # a page of a PDF drawn at this density, then kept within underlay.MAX_SIDE
_PIXMAPS: dict = {}             # (id, size of the data, its ends) -> QPixmap: decoded once, not at each redraw


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


def pixmap(u: underlay.Underlay) -> QPixmap:
    """The image of an underlay, decoded once."""
    key = (u.id, len(u.image), u.image[:64], u.image[-64:])
    if key not in _PIXMAPS:
        pix = QPixmap()
        pix.loadFromData(base64.b64decode(u.image.encode("ascii"), validate=False))
        if len(_PIXMAPS) > 16:
            _PIXMAPS.clear()
        _PIXMAPS[key] = pix
    return _PIXMAPS[key]


def transform(u: underlay.Underlay) -> QTransform:
    """From the image's pixels to the plan's scene (x East, y down: plan.to_scene)."""
    import math
    c, s = math.cos(math.radians(u.rotation)), math.sin(math.radians(u.rotation))
    k = u.scale
    return QTransform(k * c, -k * s, k * s, k * c, u.x, -u.y)
