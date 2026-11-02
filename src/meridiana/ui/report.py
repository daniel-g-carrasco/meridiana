"""The report as a PDF: what the designer hands over, with every number's pedigree (R61, then R314: study 24, sketch V1
«Cornice», laid out by Typst).

The document is made without Qt by meridiana.report_typst (the chapters as data, the look in its template, the
compilation in a temporary folder); this module is what the Qt window adds: the 3D pictures of the layout
(ui/report_3d.py), the attachments it reads and draws with Qt's PDF module when pypdf cannot, the steps the window runs
one per turn of its event loop (`export_steps`, `preview_steps`, study 16 F4), and the preview drawn from the PDF itself
by QtPdf, so what is shown is what is written.

The attachments (PDF files the designer adds, reports.py) follow the last chapter, each behind a page that names it
and in the contents with its page; the pages are numbered as the merged PDF has them. pypdf (BSD) puts them in; a
file pypdf cannot read without the cryptography package (encrypted against changes with AES, as many datasheets
are) goes in drawn page by page by Qt's PDF module. On request the register of the calculations goes beside the
report (`register_steps`): the hours of the typical year as a CSV file and «How it is computed» as a PDF of its
own."""

from __future__ import annotations

import io
import os
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QMarginsF, QRectF, QSizeF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPageLayout, QPainter, QPdfWriter

from .. import __version__, log, reports
from ..i18n import _, ngettext
from ..report_typst.compose import Picture, compose, with_notes
from ..report_typst.chapters import keys_text as _keys_text  # noqa: F401  (the tests and the notes import it here)
from ..report_typst.chapters import plant_parts
from ..report_typst.engine import Build, image_format

IMAGES_SHARE = 0.8         # of the way, the images (what takes the time); the pages the rest
RASTER_DPI = 200           # a protected attachment's pages, drawn at this density
A4 = QSizeF(210 / 25.4 * 96, 297 / 25.4 * 96)      # a page of the preview's own messages, in pixels at 96 dpi
MUTED = "#58616c"

_with_notes = with_notes


# the attachments: PDF files of the designer after the last chapter (reports.py)

@dataclass(frozen=True)
class Attachment:
    path: str
    title: str
    pages: int = 0               # 0 when it cannot be read
    protected: bool = False      # pypdf cannot read it (encrypted with AES): its pages go in as images
    problem: str = ""            # why it is left out; "" when it goes in


_READ: dict = {}                 # (path, size, time) -> (pages, protected, problem): a file read once


def _read(path: str) -> tuple[int, bool, str]:
    """The pages of a PDF file, whether only Qt's PDF module reads it, and the problem that keeps it out."""
    p = Path(path)
    try:
        st = p.stat()
    except OSError:
        return 0, False, _("not found: {path}").format(path=path)
    key = (path, st.st_size, st.st_mtime_ns)
    if key in _READ:
        return _READ[key]
    try:
        from pypdf import PdfReader
        from pypdf.errors import DependencyError, PdfReadError
    except ImportError:
        return 0, False, _("the pypdf library is missing: install the program's requirements")
    import logging
    logging.getLogger("pypdf").setLevel(logging.ERROR)     # what it forgives in a file is not the designer's news
    out: tuple[int, bool, str]
    try:
        reader = PdfReader(path)
        if reader.is_encrypted and not reader.decrypt(""):
            out = (0, False, _("protected by a password"))
        else:
            out = (len(reader.pages), False, "")
    except DependencyError:
        # encrypted against changes with AES, which pypdf opens only with the cryptography package: Qt's PDF module
        # (PDFium) reads it, and its pages go in drawn
        from PySide6.QtPdf import QPdfDocument
        doc = QPdfDocument()
        doc.load(path)
        n = doc.pageCount()
        out = (n, True, "") if n > 0 else (0, False, _("protected by a password"))
        doc.close()
    except (PdfReadError, OSError, ValueError, KeyError) as error:
        out = (0, False, _("not a PDF that can be read: {error}").format(error=error))
    if not out[2] and out[0] == 0:
        out = (0, False, _("it has no pages"))
    _READ[key] = out
    return out


def attachments(project) -> list[Attachment]:
    """The project's attachments in their order, each read now (its pages; why it is left out, if it is)."""
    out = []
    for a in reports.settings(project)["attachments"]:
        pages, protected, problem = _read(a["path"])
        out.append(Attachment(a["path"], reports.attachment_title(a), pages, protected, problem))
    return out


def plant_html(project, plant) -> list:
    """The strings of the plant as the report writes them (report_typst.chapters.plant_parts), as data."""
    return plant_parts(project, plant)


# the document

def _pictures(project, data: dict) -> dict:
    """The 3D views the report can have here: none when nothing is laid or when Qt Quick 3D cannot draw."""
    results = data.get("results") or {}
    if not any(getattr(r, "modules", None) for r in results.values()):
        return {}
    from . import report_3d
    if not report_3d.available():
        return {}
    return {vid: Picture(caption, lambda vid=vid: report_3d.picture(project, results, vid, report_3d.PRINT_SIZE))
            for vid, (_bearing, _elevation, caption) in report_3d.views().items()}


def _logo(build: Build, profile: dict | None) -> str | None:
    """The profile's logo copied into the report's folder, if it is an image Typst reads; None otherwise (said in the
    log: the header closes up without it)."""
    path = (profile or {}).get("logo") or ""
    if not path:
        return None
    try:
        data = Path(path).read_bytes()
    except OSError as error:
        log.complain("report logo", error)
        return None
    ext = image_format(data)
    if ext is None:
        log.complain("report logo", ValueError(f"{path}: not an image the report can show"))
        return None
    name = f"logo.{ext}"
    build.add(name, data)
    return name if build.usable_image(name) else None


def _build(project, energy: dict, profile: dict | None, only: str = ""):
    """The report in its folder, a step at a time: yields (fraction of the images, what) after each image; returns
    (build, compiled result, attachments that go in). The caller closes the build."""
    from .theme import matplotlib_fonts
    matplotlib_fonts()                               # the formulas' fonts, as the window's charts have them
    attached = [] if only else [a for a in attachments(project) if not a.problem]
    made = compose(project, energy, profile=profile, only=only, attached=attached,
                            pictures={} if only else _pictures(project, energy), raster_dpi=RASTER_DPI)
    build = Build()
    try:
        document = made.document
        for n, (name, make) in enumerate(made.makers.items(), 1):
            data = make()
            if data:
                build.add(name, data)
            else:
                document["missing"].append(name)
            yield n / max(1, len(made.makers)), _("charts and formulas, {n} of {total}").format(
                n=n, total=len(made.makers))
        document["doc"]["logo"] = _logo(build, profile)
        yield 1.0, _("laying out the pages")
        result = build.compile(document)
    except BaseException:
        build.close()
        raise
    return build, result, attached


def _scaled(steps, share: float):
    """The steps of a generator passed on with their fraction times `share`; its value returned (for `yield from`)."""
    while True:
        try:
            fraction, what = next(steps)
        except StopIteration as done:
            return done.value
        yield share * fraction, what


# the PDF

def export_pdf(project, energy: dict, path: Path, profile: dict | None = None, only: str = "") -> None:
    """The report at once (export_steps run to the end)."""
    for _done in export_steps(project, energy, path, profile, only):
        pass


def export_steps(project, energy: dict, path: Path, profile: dict | None = None, only: str = ""):
    """The report a step at a time, on the thread that calls it: (fraction of the way, what is being done) after
    each image, the laying out and each attachment. The attachments are put after the page that names each (pypdf),
    a protected one drawn page by page. The file is written beside `path` and put in its place at the end: a report
    stopped half way (the generator closed, Cancel) leaves nothing, and an older report under the same name stays as
    it was. `only`: a chapter alone (report_typst.compose)."""
    part = path.with_name(path.name + ".part")
    drawn: list[Path] = []
    build = None
    try:
        try:
            part.write_bytes(b"")                    # the place is there and writable before anything is made
        except OSError as error:
            raise OSError(_("{file} cannot be written").format(file=part)) from error
        build, result, attached = yield from _scaled(_build(project, energy, profile, only), IMAGES_SHARE)
        from pypdf import PdfReader, PdfWriter
        out = PdfWriter(clone_from=io.BytesIO(result.pdf))
        share = 1 - IMAGES_SHARE
        order = sorted(((result.after.get(k), k, a) for k, a in enumerate(attached, 1) if result.after.get(k)),
                       reverse=True)                 # from the last: the earlier places stay where they are
        for done, (page, k, a) in enumerate(order, 1):
            source = a.path
            if a.protected:
                source = str(path.with_name(f"{path.name}.{k}.drawn"))
                drawn.append(Path(source))
                _drawn_pdf(a.path, source)
            reader = PdfReader(source)
            if reader.is_encrypted:
                reader.decrypt("")
            out.merge(page, reader, import_outline=False)
            yield (IMAGES_SHARE + share * done / max(1, len(order)),
                   _("attachment {n} of {total}").format(n=done, total=len(order)))
        out.add_metadata({"/Title": project.name, "/Creator": f"Meridiana {__version__}",
                          **({"/Author": profile["signer"]} if profile and profile.get("signer") else {})})
        with open(part, "wb") as f:
            out.write(f)
        os.replace(part, path)
    finally:
        if build is not None:
            build.close()
        for f in (part, *drawn):
            if f.exists():
                f.unlink()


def _drawn_pdf(source: str, target: str) -> None:
    """A PDF of the pages of `source` drawn as images by Qt's PDF module, each page its own size: an attachment
    pypdf cannot read (encrypted with AES) goes in so."""
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QPageSize as Size
    from PySide6.QtPdf import QPdfDocument
    pdf = QPdfDocument()
    pdf.load(source)
    writer = QPdfWriter(target)
    writer.setResolution(RASTER_DPI)
    writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
    painter = QPainter()
    try:
        for i in range(pdf.pageCount()):
            pt = pdf.pagePointSize(i)
            writer.setPageSize(Size(QSizeF(pt.width(), pt.height()), Size.Unit.Point, "", Size.SizeMatchPolicy.ExactMatch))
            if i:
                writer.newPage()
            elif not painter.begin(writer):
                raise OSError(_("{file} cannot be written").format(file=target))
            size = QSize(round(pt.width() / 72 * RASTER_DPI), round(pt.height() / 72 * RASTER_DPI))
            painter.drawImage(QRectF(0, 0, writer.width(), writer.height()), _on_white(pdf.render(i, size)))
    finally:
        if painter.isActive():
            painter.end()
        pdf.close()


def _on_white(image: QImage) -> QImage:
    """A page drawn by Qt's PDF module (transparent where the page is empty) on white paper."""
    out = QImage(image.size(), QImage.Format.Format_RGB32)
    out.fill(QColor("white"))
    p = QPainter(out)
    p.drawImage(0, 0, image)
    p.end()
    return out


# the register of the calculations, beside the report

def register_paths(path: Path) -> tuple[Path, Path]:
    """The register's two files beside the report at `path`: the hours as a CSV file, «How it is computed» as a
    PDF."""
    stem = Path(path).with_suffix("")
    return (stem.with_name(f"{stem.name} - {_('register of the calculations')}.csv"),
            stem.with_name(f"{stem.name} - {_('how it is computed')}.pdf"))


def write_register_csv(project, energy: dict, path: Path) -> None:
    """The hours of the typical year as a CSV file at `path`, with the header that says what, where from and each
    column (energy/register.py); nothing when the year is not computed."""
    from ..energy import register
    sim = energy.get("sim")
    if sim is None:
        return
    table = register.frame(sim, energy.get("load"), energy.get("econ"))
    known = {c.id: c for c in register.columns(table.attrs.get("inverters", ()))}
    sources = [(_("Weather"), energy.get("meteo_text") or "")]
    if energy.get("load") is not None:
        sources.append((_("Consumption"), energy["load"].basis))
    lines = register.header(project.name, project.current_variant()["name"], __version__, sources,
                            [known[k] for k in table.columns if k in known], len(table))
    register.write_csv(path, table, lines)


def register_steps(project, energy: dict, path: Path, profile: dict | None = None):
    """The register of the calculations beside the report at `path` (register_paths), a step at a time: the hours
    of the typical year as a CSV file (energy/register.py), then the chapter «Parameters and methods» alone as a
    PDF, with its formulas."""
    csv, pdf = register_paths(path)
    if energy.get("sim") is None:
        return
    write_register_csv(project, energy, csv)
    yield 0.1, _("the hours of the year")
    for fraction, what in export_steps(project, energy, pdf, profile, only="methods"):
        yield 0.1 + 0.9 * fraction, what


def with_register(steps, project, energy: dict, path: Path, profile: dict | None = None):
    """The report's steps and then the register's: the way shared, the report the most of it."""
    for fraction, what in steps:
        yield 0.75 * fraction, what
    for fraction, what in register_steps(project, energy, path, profile):
        yield 0.75 + 0.25 * fraction, _("register: {what}").format(what=what)


# the preview of the Report phase

PREVIEW_ATTACHMENT_PAGES = 8     # the pages of an attachment the preview draws; one more says how many follow


def preview_steps(project, energy: dict, width: int, out: list, profile: dict | None = None):
    """The pages as images `width` pixels wide (the device's pixels: the caller sets their pixel ratio), drawn from
    the PDF by Qt's PDF module and appended to `out` one at a time, each with its number in the PDF as its text "page";
    the attachments' pages after the page that names each (the first PREVIEW_ATTACHMENT_PAGES, then a page that says
    how many more there are). Yields (fraction of the way, what) as export_steps does; returns the PDF's pages."""
    from PySide6.QtCore import QSize
    from PySide6.QtPdf import QPdfDocument
    build, result, attached = yield from _scaled(_build(project, energy, profile), IMAGES_SHARE)
    pdf = QPdfDocument()
    try:
        pdf.load(str(build.pdf_path))
        pages = pdf.pageCount()
        after: dict = {}
        for k, a in enumerate(attached, 1):
            if result.after.get(k):
                after.setdefault(result.after[k] - 1, []).append(a)
        total = pages + sum(a.pages for a in attached if result.after.get(attached.index(a) + 1))
        n = 0
        for i in range(pages):
            pt = pdf.pagePointSize(i)
            ratio = pt.height() / pt.width() if pt.width() > 0 else 297 / 210
            image = _on_white(pdf.render(i, QSize(width, round(width * ratio))))
            n += 1
            image.setText("page", str(n))
            out.append(image)
            yield (IMAGES_SHARE + (1 - IMAGES_SHARE) * (i + 1) / pages,
                   _("page {n} of {total}").format(n=n, total=total))
            for a in after.get(i, []):
                for k, shown in enumerate(_attachment_images(a, width)):
                    shown.setText("page", str(n + 1 + k))
                    out.append(shown)
                    yield (IMAGES_SHARE + (1 - IMAGES_SHARE) * (i + 1) / pages,
                           _("{title}, page {n}").format(title=a.title, n=k + 1))
                n += a.pages
    finally:
        pdf.close()
        build.close()
    return total


def _attachment_images(a: Attachment, width: int):
    """The pages of an attachment for the preview, one at a time, `width` pixels wide; after the first
    PREVIEW_ATTACHMENT_PAGES a page that says how many more the PDF has."""
    from PySide6.QtCore import QSize
    from PySide6.QtPdf import QPdfDocument
    pdf = QPdfDocument()
    pdf.load(a.path)
    try:
        shown = min(pdf.pageCount(), PREVIEW_ATTACHMENT_PAGES)
        for i in range(shown):
            pt = pdf.pagePointSize(i)
            ratio = pt.height() / pt.width() if pt.width() > 0 else 297 / 210
            yield _on_white(pdf.render(i, QSize(width, round(width * ratio))))
    finally:
        pdf.close()
    more = a.pages - shown
    if more > 0:
        scale = width / A4.width()
        image = QImage(width, round(A4.height() * scale), QImage.Format.Format_RGB32)
        image.fill(QColor("white"))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(scale, scale)
        f = QFont()
        f.setPixelSize(round(11 * A4.width() / 8.27 / 72))
        painter.setFont(f)
        painter.setPen(QColor(MUTED))
        margin = 2 / 2.54 * 96
        painter.drawText(QRectF(margin, margin, A4.width() - 2 * margin, A4.height() - 2 * margin),
                         int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
                         ngettext("{n} more page of «{title}»: it is in the PDF, not in the preview.",
                                  "{n} more pages of «{title}»: they are in the PDF, not in the preview.",
                                  more).format(n=more, title=a.title))
        painter.end()
        yield image
