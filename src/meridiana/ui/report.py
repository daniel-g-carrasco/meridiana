"""The report as a PDF: what the designer hands over, with every number's pedigree (R61, docs/compiti/19r-relazione.md).

One HTML document laid out by Qt (QTextDocument) and printed to A4 (QPdfWriter). Its chapters come from the
template the project chose (reports.py: «Complete», the default, or «Compact»), each written by its function in
ui/report_chapters.py when its data are there. The author is a profile of the preferences, chosen for the project:
the cover, the header and the footer say it; without one, the report says only the project and the date (no name
is in the program). The complete template has the contents with the chapters' pages: the document is laid out
once with the pages left blank, the pages of the chapters read from the layout, and laid out again with them (the
numbers take the room of the blanks, so nothing moves).

The PDF and the preview of the Report phase are made a step at a time (`export_steps`, `preview_steps`, study 16
F4): the HTML with the places of its images, each image (a chart, a plan or a formula, drawn by matplotlib, which
is not for threads; the 3D pictures of the layout, ui/report_3d.py), then each page; the window runs one step per
turn of its event loop, shows how far it is and can stop between two steps.

The attachments (PDF files the designer adds, reports.py) follow the last chapter, each behind a page that names it
and in the contents with its page; the pages are numbered as the merged PDF has them. pypdf (BSD) puts them in; a
file pypdf cannot read without the cryptography package (encrypted against changes with AES, as many datasheets
are) goes in drawn page by page by Qt's PDF module. On request the register of the calculations goes beside the
report (`register_steps`): the hours of the typical year as a CSV file and «How it is computed» as a PDF of its
own."""

from __future__ import annotations

import html
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PySide6.QtCore import QMarginsF, QPointF, QRectF, QSizeF, Qt, QUrl
from PySide6.QtGui import (QAbstractTextDocumentLayout, QColor, QFont, QFontMetricsF, QGuiApplication, QImage,
                           QPageLayout, QPageSize, QPainter, QPalette, QPdfWriter, QPen, QTextDocument)

from .. import __version__, reports
from ..i18n import _, ngettext, number
from .report_chapters import BUILDERS, INK, MUTED, Context, _keys_text, facts, para, plant_parts  # noqa: F401

IMAGES_SHARE = 0.8         # of the way, the images (what takes the time); the pages the rest
MARGIN_CM = 2.0
POINT_SIZE = 9.5
RULE = "#d9d4ca"           # the lines of the tables and of the header
HEAD = "#f1eee8"           # the ground of a table's header
BLANK = "00"               # a page of the contents before the layout says it


def _style() -> str:
    return (f"<style>body {{ color: {INK}; }} "
            "h1 { font-size: 24pt; font-weight: 600; margin-top: 0; margin-bottom: 6pt; } "
            "h2 { font-size: 15pt; font-weight: 600; margin-top: 18pt; margin-bottom: 8pt; } "
            "h3 { font-size: 11.5pt; font-weight: 600; margin-top: 14pt; margin-bottom: 5pt; } "
            "h4 { font-size: 10pt; font-weight: 600; margin-top: 10pt; margin-bottom: 3pt; } "
            "p { margin-top: 0; margin-bottom: 6pt; } "
            f"table.grid {{ border-collapse: collapse; margin-bottom: 6pt; }} "
            f"table.grid th {{ background-color: {HEAD}; font-weight: 600; border-bottom: 1px solid {RULE}; }} "
            f"table.grid td {{ border-bottom: 1px solid {RULE}; vertical-align: top; }} "
            "table.facts { margin-bottom: 8pt; } "
            f"td.label {{ color: {MUTED}; }} "
            f".muted {{ color: {MUTED}; }} "
            f".caption {{ color: {MUTED}; font-size: 8pt; }} "
            f".kicker {{ color: {MUTED}; font-size: 10pt; font-weight: 600; }} "
            f".lead {{ font-size: 13pt; }} "
            "td.toc { padding: 3pt 0; } "
            "</style>")


def _cover_rows(project, settings: dict, profile: dict | None) -> list[tuple[str, str]]:
    rows = []
    variants = getattr(project, "variants", [])
    if len(variants) > 1:
        here = project.current_variant()
        rows.append((_("Variant"), here["name"] + (f" · {here['note']}" if here.get("note") else "")))
    if settings.get("client"):
        rows.append((_("Client"), settings["client"]))
    s = project.site
    where = f"{number(s.lat, 5)}°, {number(s.lon, 5)}°"
    if settings.get("address", True) and s.address:
        where = f"{s.address} ({where})"
    rows.append((_("Site"), where))
    if profile and profile.get("signer"):
        rows.append((_("Designer"), profile["signer"]))
    rows.append((_("Date"), date.today().strftime("%d/%m/%Y")))
    if settings.get("revision"):
        rows.append((_("Revision"), settings["revision"]))
    return rows


def _cover_data(project, data: dict, settings: dict, profile: dict | None) -> dict:
    """What the cover of the complete template says, painted on its page (_paint_cover)."""
    sim = data.get("sim")
    what = _("Photovoltaic system")
    if sim is not None:
        what += f", {number(sim.p_stc_kw, 2)} kWp"
    logo = QImage()
    path = (profile or {}).get("logo") or ""
    if path and Path(path).is_file():
        logo = QImage(path)
    firm = [x for x in ((profile or {}).get("firm"), (profile or {}).get("signer"), (profile or {}).get("register"))
            if x]
    contacts = " · ".join(x for x in ((profile or {}).get(k) for k in ("address", "phone", "email", "web")) if x)
    return {"kicker": _("TECHNICAL REPORT"), "title": project.name, "what": what,
            "rows": _cover_rows(project, settings, profile), "firm": firm, "contacts": contacts, "logo": logo,
            "made": _("Report made by Meridiana {v}").format(v=__version__)}


def _paint_cover(painter: QPainter, page: QSizeF, margin: int, cover: dict, base: QFont) -> None:
    """The cover on the first page, in the page's pixels: the author at the top, the project a third of the way
    down under a short rule, the facts near the bottom, what made it at the foot."""
    pt = page.width() / 8.27 / 72                        # a point in the page's pixels

    def font(size: float, bold: bool = False) -> QFont:
        f = QFont(base)
        f.setPixelSize(max(6, round(size * pt)))
        f.setWeight(QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
        return f
    left, right = float(margin), page.width() - margin
    painter.save()
    y = float(margin)
    if not cover["logo"].isNull():
        h = 16 * 2.8 * pt
        w = cover["logo"].width() * h / max(1, cover["logo"].height())
        painter.drawImage(QRectF(left, y, min(w, (right - left) / 2), h), cover["logo"])
    f = font(9.5)
    painter.setFont(f)
    m = QFontMetricsF(f)
    yy = y + m.ascent()
    for i, line in enumerate(cover["firm"]):
        painter.setPen(QColor(INK))
        painter.setFont(font(9.5, i == 0))
        mm = QFontMetricsF(painter.font())
        painter.drawText(QPointF(right - mm.horizontalAdvance(line), yy), line)
        yy += m.height() * 1.15
    if cover["contacts"]:
        painter.setFont(font(8))
        painter.setPen(QColor(MUTED))
        mm = QFontMetricsF(painter.font())
        text = mm.elidedText(cover["contacts"], Qt.TextElideMode.ElideLeft, right - left)
        painter.drawText(QPointF(right - mm.horizontalAdvance(text), yy), text)
    y = page.height() * 0.36
    painter.setPen(QPen(QColor(INK), 2.2 * pt))
    painter.drawLine(QPointF(left, y), QPointF(left + 40 * 2.83 * pt, y))
    y += 20 * pt
    painter.setFont(font(10, True))
    painter.setPen(QColor(MUTED))
    painter.drawText(QPointF(left, y), cover["kicker"])
    painter.setPen(QColor(INK))
    title = font(28, True)
    painter.setFont(title)
    rect = QRectF(left, y + 8 * pt, right - left, page.height() * 0.25)
    used = painter.boundingRect(rect, int(Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap), cover["title"])
    painter.drawText(rect, int(Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap), cover["title"])
    y = used.bottom() + 22 * pt
    painter.setFont(font(14))
    painter.drawText(QPointF(left, y), cover["what"])
    y = page.height() * 0.66
    label, value = font(9.5), font(10.5)
    for a, b in cover["rows"]:
        painter.setFont(label)
        painter.setPen(QColor(MUTED))
        painter.drawText(QPointF(left, y), a)
        painter.setFont(value)
        painter.setPen(QColor(INK))
        painter.drawText(QRectF(left + 32 * 2.83 * pt, y - QFontMetricsF(value).ascent(), right - left - 32 * 2.83 * pt,
                                3 * QFontMetricsF(value).height()),
                         int(Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap), b)
        y += QFontMetricsF(value).height() * 1.7
    painter.setFont(font(7.5))
    painter.setPen(QColor(MUTED))
    painter.drawText(QPointF(left, page.height() - margin * 0.45), cover["made"])
    painter.restore()


def _cover(project, data: dict, settings: dict, profile: dict | None, template, image) -> list[str]:
    """The first page (complete: painted by _paint_cover, the text only leaves it free) or the first block
    (compact): the author, the project, the site, the date."""
    if template.contents:
        return ["<p>&nbsp;</p>"]                     # the contents start the next page
    parts = []
    if profile:
        lines = [x for x in (profile.get("firm"), profile.get("signer"), profile.get("register")) if x]
        contacts = " · ".join(x for x in (profile.get("address"), profile.get("phone"), profile.get("email"),
                                          profile.get("web")) if x)
        right = "<br>".join(html.escape(x) for x in lines)
        if contacts:
            right += f"<br><span class='muted'>{html.escape(contacts)}</span>"
        logo = ""
        path = profile.get("logo") or ""
        if path and Path(path).is_file():
            logo = f"<img src='{image('logo', lambda: Path(path).read_bytes())}' height='56'>"
        parts.append("<table width='100%' cellspacing='0' cellpadding='0'><tr>"
                     f"<td valign='top'>{logo}</td><td align='right' valign='top'>{right}</td></tr></table>")
    sim = data.get("sim")
    parts.append(f"<p class='kicker' style='margin-top: 18pt'>{html.escape(_('TECHNICAL REPORT'))}</p>")
    parts.append(f"<h1>{html.escape(project.name)}</h1>")
    what = _("Photovoltaic system")
    if sim is not None:
        what += f", {number(sim.p_stc_kw, 2)} kWp"
    parts.append(f"<p class='lead'>{html.escape(what)}</p>")
    rows = _cover_rows(project, settings, profile)
    body = "".join(f"<tr><td class='label' width='22%'>{html.escape(a)}</td><td>{html.escape(b)}</td></tr>"
                   for a, b in rows)
    parts.append(f"<table cellspacing='0' cellpadding='3' style='margin-top: 14pt'>{body}</table>")
    parts.append(f"<p class='caption' style='margin-top: 18pt'>"
                 f"{html.escape(_('Report made by Meridiana {v}').format(v=__version__))}</p>")
    return parts


def _contents(chosen: list, pages: dict | None, attached: list) -> list[str]:
    rows = "".join(f"<tr><td class='toc'>{n}. {html.escape(c.title)}</td>"
                   f"<td class='toc' align='right'>{(pages or {}).get(c.id, BLANK)}</td></tr>"
                   for n, c in enumerate(chosen, 1))
    rows += "".join(f"<tr><td class='toc'>{html.escape(_attached_head(k, a))}</td>"
                    f"<td class='toc' align='right'>{(pages or {}).get(f'attachment:{k}', BLANK)}</td></tr>"
                    for k, a in enumerate(attached, 1))
    return [f"<h2 style='page-break-before: always'>{html.escape(_('Contents'))}</h2>",
            f"<table width='100%' cellspacing='0' cellpadding='0'>{rows}</table>"]


def _with_notes(data: dict) -> dict:
    """The data with the notes of the rules worked out once, for the chapter of the checks and for its presence."""
    if data.get("rules_facts") is not None and "rules_notes" not in data:
        from .. import rules
        data = {**data, "rules_notes": rules.notes(data["rules_facts"])}
    return data


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


def _attached_head(k: int, a: Attachment) -> str:
    return _("Attachment {n}: {title}").format(n=k, title=a.title)


def _separator(k: int, a: Attachment) -> list[str]:
    """The page before an attachment: what it is, its file, its pages."""
    parts = [f"<h2 style='page-break-before: always'>{html.escape(_attached_head(k, a))}</h2>",
             facts([(_("File"), Path(a.path).name), (_("Pages"), str(a.pages))]),
             para(_("The pages that follow are the file as it was given, without the report's header and footer."),
                  "muted")]
    if a.protected:
        parts.append(para(_("The file is protected against changes: its pages follow as images at {dpi} dpi.").format(
            dpi=RASTER_DPI), "muted"))
    return parts


def _compose(project, data: dict, image, profile: dict | None = None, pages: dict | None = None,
             only: str = "", attached: list | None = None) -> tuple[str, list]:
    """The report's HTML and the chapters written; image(name, make, ratio=1.0) places the image whose bytes
    `make()` gives, now (build_html) or later (the steps), and returns its URL; `pages`: chapter id (and
    "attachment:k") -> its page, for the contents (None: blanks); `attached`: the attachments that go in, each
    behind a page of its own after the last chapter. With `only` a chapter alone, under a title of its own (the
    «How it is computed» of the register of the calculations), without cover, contents and attachments."""
    data = _with_notes(data)
    settings = reports.settings(project)
    template = reports.templates()[settings["template"]]
    ctx = Context(project, data, image, settings)
    parts = [_style()]
    if only:
        chapter = reports.chapters()[only]
        chosen = [] if reports.missing(chapter, data) else [chapter]
        parts.append(f"<p class='kicker'>{html.escape(_('REGISTER OF THE CALCULATIONS'))}</p>")
        parts.append(f"<h1>{html.escape(project.name)}</h1>")
        parts.append(para(_("How each number of the report is computed: the models, the losses and the thresholds, "
                            "with their sources and formulas. The values hour by hour are in the CSV file of the "
                            "register.")))
        for c in chosen:
            parts.append(f"<h2>{html.escape(c.title)}</h2>")
            parts += [x for x in BUILDERS[c.id](ctx) if x]
        return "".join(parts), chosen
    attached = attached or []
    chosen = reports.plan(project, data)
    parts += _cover(project, data, settings, profile, template, image)
    if template.contents and (chosen or attached):
        parts += _contents(chosen, pages, attached)
    for n, chapter in enumerate(chosen, 1):
        brk = " style='page-break-before: always'" if template.contents else ""
        parts.append(f"<h2{brk}>{n}. {html.escape(chapter.title)}</h2>")
        parts += [x for x in BUILDERS[chapter.id](ctx) if x]
    for k, a in enumerate(attached, 1):
        parts += _separator(k, a)
    return "".join(parts), chosen


def build_html(project, energy: dict, add_image, profile: dict | None = None) -> str:
    """The report's HTML; add_image(name, data, ratio) registers an image and returns its URL."""
    attached = [a for a in attachments(project) if not a.problem]
    return _compose(project, energy, lambda name, make, ratio=1.0: add_image(name, make(), ratio), profile,
                    attached=attached)[0]


def plant_html(project, plant) -> list[str]:
    """The strings of the plant as the report writes them (ui/report_chapters.plant_parts)."""
    return plant_parts(project, plant)


# the document, laid out and painted

def _document(project, energy: dict, profile: dict | None, only: str = ""):
    """The report as a QTextDocument laid out on A4 at the screen's dots per inch, a step at a time: yields
    (fraction of the images, what) after each image; returns (doc, page size, margin, chrome) once laid out. The
    chrome has what the pages' header and footer say, the cover, and the attachments that go in with the page each
    follows (`inserted`: the document's page -> the pages put after it)."""
    makers: dict = {}

    def later(name: str, make, ratio: float = 1.0) -> str:
        makers.setdefault(name, (make, ratio))
        return QUrl(f"report://{name}").toString()

    attached = [] if only else [a for a in attachments(project) if not a.problem]
    text, chosen = _compose(project, energy, later, profile, only=only, attached=attached)
    images: dict = {}
    for n, (name, (make, ratio)) in enumerate(makers.items(), 1):
        image = QImage.fromData(make())
        image.setDevicePixelRatio(ratio)
        images[name] = image
        yield n / len(makers), _("charts and formulas, {n} of {total}").format(n=n, total=len(makers))
    doc = QTextDocument()
    font = doc.defaultFont()
    font.setPointSizeF(POINT_SIZE)
    doc.setDefaultFont(font)

    def fill(html_text: str) -> None:
        for name, image in images.items():
            doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(f"report://{name}"), image)
        doc.setHtml(html_text)
        for name, image in images.items():
            doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(f"report://{name}"), image)

    fill(text)
    page, margin = _layout(doc)
    settings = reports.settings(project)
    contents = not only and reports.templates()[settings["template"]].contents and (chosen or attached)
    if contents:
        found = _chapter_pages(doc, page, chosen, attached)
        text, _again = _compose(project, energy, later, profile, _final_pages(found, attached), attached=attached)
        fill(text)
        page, margin = _layout(doc)
    found = _chapter_pages(doc, page, [], attached)
    after = [found.get(f"attachment:{k}", doc.pageCount()) - 1 for k in range(1, len(attached) + 1)]   # the last
    inserted: dict = {}
    for d, a in zip(after, attached, strict=True):
        inserted[d] = inserted.get(d, 0) + a.pages
    foot = _("Register of the calculations") if only else _("Technical report")
    chrome = {"left": (profile or {}).get("firm") or (profile or {}).get("signer") or "",
              "right": project.name, "foot": foot + " · " + date.today().strftime("%d/%m/%Y"),
              "cover": (_cover_data(project, _with_notes(energy), settings, profile)
                        if not only and reports.templates()[settings["template"]].contents else None),
              "inserted": inserted, "attached": list(zip(after, attached, strict=True))}
    return doc, page, margin, chrome


def _final_pages(found: dict, attached: list) -> dict:
    """The pages of the contents as the merged PDF numbers them: an attachment's page is its separator's, after
    the pages of the attachments before it."""
    out = dict(found)
    before = 0
    for k, a in enumerate(attached, 1):
        key = f"attachment:{k}"
        if key in out:
            out[key] += before
        before += a.pages
    return out


def _layout(doc: QTextDocument) -> tuple[QSizeF, int]:
    """`doc` on A4 at the screen's dots per inch (as Qt prints a paginated document), the margins in the root
    frame: the page's size and the margin in those pixels."""
    screen = QGuiApplication.primaryScreen()
    dpi = screen.logicalDotsPerInchY() if screen is not None else 96.0
    size = QPageSize(QPageSize.PageSizeId.A4).size(QPageSize.Unit.Inch)
    page = QSizeF(size.width() * dpi, size.height() * dpi)
    margin = int(MARGIN_CM / 2.54 * dpi)
    frame = doc.rootFrame().frameFormat()
    frame.setMargin(margin)
    doc.rootFrame().setFrameFormat(frame)
    doc.setPageSize(page)
    doc.pageCount()                                 # laid out now
    return page, margin


def _chapter_pages(doc: QTextDocument, page: QSizeF, chosen: list, attached: list | None = None) -> dict:
    """chapter id (and "attachment:k" for the page before each attachment) -> the page of the document its heading
    falls on, from the layout."""
    heads = {f"{n}. {c.title}": c.id for n, c in enumerate(chosen, 1)}
    heads.update({_attached_head(k, a): f"attachment:{k}" for k, a in enumerate(attached or [], 1)})
    out: dict = {}
    layout = doc.documentLayout()
    block = doc.begin()
    while block.isValid():
        if block.blockFormat().headingLevel() == 2 and block.text().strip() in heads:
            top = layout.blockBoundingRect(block).top()
            out.setdefault(heads[block.text().strip()], int(top // page.height()) + 1)
        block = block.next()
    return out


def _numbers(chrome: dict, i: int, pages: int) -> tuple[int, int]:
    """The number page `i` of the document has in the PDF, and the PDF's pages: the attachments' come between."""
    inserted = chrome.get("inserted") or {}
    return i + 1 + sum(n for d, n in inserted.items() if d < i), pages + sum(inserted.values())


def _draw_page(doc: QTextDocument, painter: QPainter, i: int, pages: int, page: QSizeF, margin: int,
               chrome: dict) -> None:
    """Page `i` of `doc` in the page's pixels (the caller scales the painter to its device): the text, and from
    the second page on the header (the author, the project) and the footer (what it is, the page of the pages)."""
    top = i * page.height()
    view = QRectF(0, top, page.width(), page.height())
    ctx = QAbstractTextDocumentLayout.PaintContext()
    palette = QPalette(ctx.palette)
    palette.setColor(QPalette.ColorRole.Text, QColor("black"))       # the system's text may be white: not on paper
    ctx.palette = palette
    painter.save()
    painter.translate(0, -top)
    painter.setClipRect(view)
    ctx.clip = view
    doc.documentLayout().draw(painter, ctx)
    painter.setClipping(False)
    painter.restore()
    if i == 0:
        if chrome.get("cover"):
            _paint_cover(painter, page, margin, chrome["cover"], doc.defaultFont())
        return
    _paint_chrome(painter, page, margin, chrome, doc.defaultFont(), *_numbers(chrome, i, pages))


def _paint_chrome(painter: QPainter, page: QSizeF, margin: int, chrome: dict, base: QFont, n: int, total: int) -> None:
    """The header (the author, the project) and the footer (what it is, the page of the pages) on a page."""
    font = QFont(base)
    font.setPixelSize(max(8, round(7.5 * page.width() / 8.27 / 72)))     # 7.5 pt on the page's pixels
    metrics = QFontMetricsF(font)
    painter.save()
    painter.setFont(font)
    painter.setPen(QColor(MUTED))
    left, right = float(margin), page.width() - margin
    head = margin * 0.55
    painter.drawText(QPointF(left, head), metrics.elidedText(chrome["left"], Qt.TextElideMode.ElideRight,
                                                             (right - left) / 2 - 8))
    title = metrics.elidedText(chrome["right"], Qt.TextElideMode.ElideRight, (right - left) / 2 - 8)
    painter.drawText(QPointF(right - metrics.horizontalAdvance(title), head), title)
    painter.setPen(QPen(QColor(RULE), 0.8))
    painter.drawLine(QPointF(left, head + 5), QPointF(right, head + 5))
    painter.setPen(QColor(MUTED))
    foot = page.height() - margin * 0.45
    painter.drawText(QPointF(left, foot), chrome["foot"])
    count = _("page {n} of {total}").format(n=n, total=total)
    painter.drawText(QPointF(right - metrics.horizontalAdvance(count), foot), count)
    painter.restore()


# the PDF

def export_pdf(project, energy: dict, path: Path, profile: dict | None = None, only: str = "") -> None:
    """The report at once (export_steps run to the end)."""
    for _done in export_steps(project, energy, path, profile, only):
        pass


def export_steps(project, energy: dict, path: Path, profile: dict | None = None, only: str = ""):
    """The report a step at a time, on the thread that calls it: (fraction of the way, what is being done) after
    each image, each page and each attachment. Qt lays the document out at the screen's dots per inch and it is
    scaled to the paper, with 2 cm margins; the charts are given 620 px (about 16 cm), the formulas carry their
    pixel ratio. The attachments are put after the page that names each (pypdf), a protected one drawn page by
    page. The file is written beside `path` and put in its place at the end: a report stopped half way (the
    generator closed, Cancel) leaves nothing, and an older report under the same name stays as it was. `only`: a
    chapter alone (`_compose`)."""
    steps = _document(project, energy, profile, only)
    while True:
        try:
            fraction, what = next(steps)
        except StopIteration as done:
            doc, page, margin, chrome = done.value
            break
        yield IMAGES_SHARE * fraction, what
    attached = chrome["attached"]
    share = (1 - IMAGES_SHARE) * (0.5 if attached else 1.0)          # the pages; the attachments the rest
    part = path.with_name(path.name + ".part")
    merged = path.with_name(path.name + ".merge")
    drawn: list[Path] = []
    writer = QPdfWriter(str(part))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
    writer.setResolution(300)
    writer.setTitle(project.name)
    writer.setCreator(f"Meridiana {__version__}")
    if profile and profile.get("signer"):
        writer.setAuthor(profile["signer"])
    painter = QPainter()
    try:
        if not painter.begin(writer):
            raise OSError(_("{file} cannot be written").format(file=part))
        pages = doc.pageCount()
        scale = writer.width() / page.width()
        for i in range(pages):
            if i:
                writer.newPage()
            painter.save()
            painter.scale(scale, scale)
            _draw_page(doc, painter, i, pages, page, margin, chrome)
            painter.restore()
            yield (IMAGES_SHARE + share * (i + 1) / pages, _("page {n} of {total}").format(n=i + 1, total=pages))
        painter.end()
        del writer
        if not attached:
            os.replace(part, path)
            return
        from pypdf import PdfReader, PdfWriter
        out = PdfWriter()
        after: dict = {}
        for d, a in attached:
            after.setdefault(d, []).append(a)
        report = PdfReader(str(part))
        done = 0
        for i, pg in enumerate(report.pages):
            out.add_page(pg)
            for a in after.get(i, []):
                source = a.path
                if a.protected:
                    source = str(path.with_name(f"{path.name}.{done}.drawn"))
                    drawn.append(Path(source))
                    _drawn_pdf(a.path, source)
                reader = PdfReader(source)
                if reader.is_encrypted:
                    reader.decrypt("")
                for p in reader.pages:
                    out.add_page(p)
                done += 1
                yield (IMAGES_SHARE + share * (1 + done / len(attached)),
                       _("attachment {n} of {total}").format(n=done, total=len(attached)))
        out.add_metadata({"/Title": project.name, "/Creator": f"Meridiana {__version__}",
                          **({"/Author": profile["signer"]} if profile and profile.get("signer") else {})})
        with open(merged, "wb") as f:
            out.write(f)
        os.replace(merged, path)
    finally:
        if painter.isActive():
            painter.end()
        for f in (part, merged, *drawn):
            if f.exists():
                f.unlink()


RASTER_DPI = 200                 # a protected attachment's pages, drawn at this density


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
    known = {c.id: c for c in register.columns()}
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
    """The pages as images `width` pixels wide (the device's pixels: the caller sets their pixel ratio), appended
    to `out` one at a time, each with its number in the PDF as its text "page"; the attachments' pages after the
    page that names each, drawn by Qt's PDF module (the first PREVIEW_ATTACHMENT_PAGES, then a page that says how
    many more there are). Yields (fraction of the way, what) as export_steps does; returns the PDF's pages."""
    steps = _document(project, energy, profile)
    while True:
        try:
            fraction, what = next(steps)
        except StopIteration as done:
            doc, page, margin, chrome = done.value
            break
        yield IMAGES_SHARE * fraction, what
    pages = doc.pageCount()
    total = _numbers(chrome, pages - 1, pages)[1]
    after: dict = {}
    for d, a in chrome["attached"]:
        after.setdefault(d, []).append(a)
    scale = width / page.width()
    for i in range(pages):
        image = QImage(width, round(page.height() * scale), QImage.Format.Format_RGB32)
        image.fill(QColor("white"))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.scale(scale, scale)
        _draw_page(doc, painter, i, pages, page, margin, chrome)
        painter.end()
        n = _numbers(chrome, i, pages)[0]
        image.setText("page", str(n))
        out.append(image)
        yield (IMAGES_SHARE + (1 - IMAGES_SHARE) * (i + 1) / pages, _("page {n} of {total}").format(n=n, total=total))
        for a in after.get(i, []):
            for k, shown in enumerate(_attachment_images(a, width, page, margin, doc.defaultFont())):
                shown.setText("page", str(n + 1 + k))
                out.append(shown)
                yield (IMAGES_SHARE + (1 - IMAGES_SHARE) * (i + 1) / pages,
                       _("{title}, page {n}").format(title=a.title, n=k + 1))
            n += a.pages
    return total


def _attachment_images(a: Attachment, width: int, page: QSizeF, margin: int, base: QFont):
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
        scale = width / page.width()
        image = QImage(width, round(page.height() * scale), QImage.Format.Format_RGB32)
        image.fill(QColor("white"))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(scale, scale)
        f = QFont(base)
        f.setPixelSize(round(11 * page.width() / 8.27 / 72))
        painter.setFont(f)
        painter.setPen(QColor(MUTED))
        painter.drawText(QRectF(margin, margin, page.width() - 2 * margin, page.height() - 2 * margin),
                         int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
                         ngettext("{n} more page of «{title}»: it is in the PDF, not in the preview.",
                                  "{n} more pages of «{title}»: they are in the PDF, not in the preview.",
                                  more).format(n=more, title=a.title))
        painter.end()
        yield image
