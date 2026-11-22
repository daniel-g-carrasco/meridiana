"""Report choices and the report made as jobs of the window's jobs' center (R598, study 48 chapter 6, step 3).

The preview and the export run as jobs (app/report_job.py) in a process of the jobs, which starts the report's own
process (report_worker.py: the existing Qt/Typst pipeline on its own GUI thread) and keeps one warm for the next. The
window sends the session's photo and the options; the year is read by the job from the store of the years (or, when
it is not there, written here once by the pool). The pages come one by one as results on the way and are shown a
piece per turn of the window; the progress is the one row of the jobs (`work.slots.report`, M.WorkRow).
"""
from __future__ import annotations

import copy
import datetime
import itertools
import json
import os
from pathlib import Path
import pickle
import shutil
import tempfile

from PySide6.QtCore import QObject, Property, QRunnable, QThreadPool, QTimer, QUrl, Signal, Slot

from meridiana import i18n
from meridiana.app import report_job
from meridiana.app.report import reports
from meridiana.app.platform.config import Config
# with the window, not at the first report's request on its thread (16 ms)
from meridiana.gui.paper.report import kind_of, register_paths
from meridiana.i18n import _, ngettext
from . import report_pages       # imported with the page: never for the first time on a delivery (30 ms)
from .report_ahead import AheadPreview
from .report_attachments import AttachmentRead as _AttachmentRead, AttachmentSignals as _AttachmentSignals


class _RequestSignals(QObject):
    written = Signal(int, str)


class _YearWrite(QRunnable):
    """The year in hand written into its own file off the window's thread, for the reports' job, when the store of
    the years has not got it (a year never computed here, or a full disk); the older files of the folder taken away."""

    def __init__(self, serial, path, year, signals):
        super().__init__()
        self.serial, self.path, self.year, self.signals = serial, path, year, signals

    def run(self):
        error = ""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            for old in self.path.parent.glob("year-*.pickle"):
                try:
                    old.unlink()        # a report reading it keeps its handle on Linux; on Windows it is left
                except OSError:
                    continue
            part = self.path.with_name(f"{self.path.name}.part")
            with part.open("wb") as stream:
                pickle.dump(self.year, stream, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(part, self.path)
        except Exception as problem:  # said by the page, as a report that could not be made
            error = str(problem) or type(problem).__name__
        self.year = None
        self.signals.written.emit(self.serial, error)


WORKER = "meridiana.gui.backend.report_worker"
SLOT = "report"                 # the slot of the report's jobs: `work.slots.report` in the page
_roots = itertools.count(1)


class ReportBackend(AheadPreview, QObject):
    changed = Signal()
    contentChanged = Signal()
    commandRequested = Signal(str)
    completed = Signal(str)
    recomputeAsked = Signal()
    pageTextCancelled = Signal()
    pageDrawn = Signal(str)          # a page of the preview drawn at the size asked (R509, report_pages)
    pagesChanged = Signal()          # the pages of the preview, all of them (a new project, the end of a swap)
    pagesReplacing = Signal()        # preserve the chapter before the first page changes its geometry
    pageSet = Signal(int, 'QVariantMap')     # one page of a new preview in its place, a piece per turn (R598)
    failed = Signal(str)
    pageAsked = Signal(int)          # a chapter chosen in the contents (ReportContents.qml): the preview goes there
    shownPageChanged = Signal()      # the page in the middle of the preview
    replacingChanged = Signal()      # a new preview is coming in: the contents hold their row

    def __init__(self, session, cfg=None, paths=None, parent=None, center=None, year_cache=None):
        """`center`: the window's jobs' center (bridge.work.center); without one (a page alone, the tests) the
        backend makes its own jobs' bridge. `year_cache`: the cache of the years computed (the bridge's), where the
        report's job reads the year in hand."""
        super().__init__(parent)
        self.session, self.cfg, self.paths = session, cfg or Config(), paths
        self.year_cache = year_cache
        self._own_work = None
        if center is None:
            from .work import WorkBackend
            self._own_work = WorkBackend(session)
            center = self._own_work.center
        self.center = center
        self.center.subscribe(self._rows_changed)
        self._root_name = f"report-{os.getpid()}-{next(_roots)}"
        self._export_waiting, self._export_after_year = "", False
        self._export_queued = ""      # asked while another report was being made: it goes when that one ends
        self._state = None              # exportState, made again after a change or an export
        self._records = {}              # project -> the export the jobs remembered in this session (R437)
        self._queued_note = ""
        self._closed = False
        self._data = {}
        self._settings = {}
        self._chapters, self._profiles, self._attachments, self._pages = [], [], [], []
        self._busy, self._status, self._error = False, "", ""
        self._count = 0
        self._handle = None             # the report's job in hand (Center.submit)
        self._mode, self._target = "preview", None
        self._incoming = {}             # n -> the row of a page of the preview on its way
        self._incoming_outline, self._outline = [], []      # the chapters: title, level, page (report_worker.outline)
        self._swap = None               # (rows, next index, total, folder): the pages of a new preview going in
        self._held = []                 # pages asked to be drawn while the new ones were going in
        self._shown_folder = None       # the folder the pages shown are drawn from
        self._drop = []                 # folders of previews no longer shown, for the job to take away
        self._store_miss = None         # (energy, results) whose year the store has not: written here
        self._year_mark, self._year_count, self._year_writing = None, 0, None
        self._attachment_key = None
        self._attachment_generation = 0
        self._drawing = False
        self._attachment_signals = _AttachmentSignals()
        self._attachment_signals.done.connect(self._attachments_done)
        self._serial = 0
        self._request_signals = _RequestSignals()
        self._request_signals.written.connect(self._written)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(int(report_job.SETTLE * 1000))
        self._timer.timeout.connect(self.requestPreview)
        self._active = False
        self._init_ahead()                # R548 (report_ahead.py)
        self.session.subscribe(self._session_changed)
        self.refresh()

    @Property('QVariantMap', notify=contentChanged)
    def settings(self):
        return copy.deepcopy(self._settings)

    @Property('QVariantList', notify=contentChanged)
    def templates(self):
        return [{"id": t.id, "name": t.name, "note": t.note} for t in reports.templates().values()]

    @Property('QVariantList', notify=contentChanged)
    def profiles(self):
        return self._profiles

    @Property('QVariantList', notify=contentChanged)
    def chapters(self):
        return self._chapters

    @Property('QVariantList', notify=contentChanged)
    def attachments(self):
        return self._attachments

    @Property('QVariantList', notify=pagesChanged)
    def pages(self):
        return self._pages

    @Property('QVariantList', notify=pagesChanged)
    def outline(self):
        """The chapters of the preview shown: title, level (1 a chapter) and the page each starts on."""
        return self._outline

    @Property(int, notify=shownPageChanged)
    def shownPage(self):
        return getattr(self, "_shown_page", 1)

    @Slot(int)
    def setShownPage(self, page):
        if page != self.shownPage:
            self._shown_page = page
            self.shownPageChanged.emit()

    @Property(bool, notify=replacingChanged)
    def replacingPages(self):
        return getattr(self, "_replacing_pages", False)

    @Slot(bool)
    def setReplacingPages(self, replacing):
        if replacing != self.replacingPages:
            self._replacing_pages = replacing
            self.replacingChanged.emit()

    @Slot(int)
    def askPage(self, page):
        self.pageAsked.emit(page)

    @Property(bool, notify=changed)
    def outlineOpen(self):
        return self.cfg.report_outline_open

    @Slot(bool)
    def setOutlineOpen(self, opened):
        if self.cfg.report_outline_open == opened:
            return
        from meridiana.app.platform import config
        candidate = copy.deepcopy(self.cfg)
        candidate.report_outline_open = opened
        try:
            path = self._path("config_file")
            if path is not None:
                config.save(candidate, path)
        except OSError as error:
            self._fail(str(error))
            return
        config.adopt(self.cfg, candidate)
        self.changed.emit()

    @Property(bool, notify=contentChanged)
    def ready(self):
        return self.report_data().get("sim") is not None

    @Property(bool, notify=changed)
    def busy(self):
        return self._busy

    @Property(str, notify=changed)
    def status(self):
        if self._export_queued:     # the progress of the preview goes on under the promise
            return f"{self._queued_note} ({self._status})" if self._status else self._queued_note
        return self._status

    @Property(str, notify=changed)
    def error(self):
        return self._error

    @Property(int, notify=changed)
    def pageCount(self):
        return self._count

    @Property('QVariantMap', notify=contentChanged)
    def labels(self):
        return {key: _(text) for key, text in {
            "title": "Technical report", "section": "Report", "template": "Template", "profile": "Signed by",
            "clientHint": "as the cover will say it", "revisionHint": "for example Rev. 0",
            "profiles": "Profiles…", "client": "Client", "revision": "Revision", "address": "The site's address",
            "register": "Export the register of the calculations too", "chapters": "Chapters",
            "attachments": "Attachments", "add": "Add PDF files…", "remove": "Remove", "up": "Move up", "down": "Move down",
            "preview": "Preview", "export": "Technical report (PDF, ODT, DOCX)", "cancel": "Cancel",
            "contents": "Contents", "closeContents": "Close contents",
            "contentsEmpty": "The contents appear with the preview", "goToPage": "Go to page",
            "compute": "Compute", "pageOf": "Page {n} of {total}", "zoomIn": "Zoom in", "zoomOut": "Zoom out",
            "pdfFilter": "PDF (*.pdf)", "odtFilter": "OpenDocument text, editable (*.odt)",
            "docxFilter": "Word document, editable (*.docx)", "exportAnyway": "Export with these numbers",
            "staleTitle": "Numbers not up to date", "computeExport": "Compute and then export", "exportCancel": "Cancel",
            "staleBody": "The project changed after this computation: the report would carry the numbers of before.",
            "empty": "Compute the production to see the report: its chapters are made of the results.",
            "attachmentNote": "PDF files after the last chapter, each behind a page that names it: the datasheets "
                              "of the modules and of the inverters, the certificates.",
        }.items()}

    def report_data(self):
        return {**self.session.energy, "results": self.session.good_results(), **self._data}

    @Slot('QVariantMap')
    def setReportData(self, data):
        self._data = dict(data)
        self.refresh()
        self._schedule()

    def _path(self, name):
        value = self.paths.get(name) if isinstance(self.paths, dict) else getattr(self.paths, name, None)
        return Path(value) if value else None

    def profile(self):
        signed = reports.signature(self.session.project, self.cfg.report_profiles, self.cfg.report_profile)
        p = signed["profile"]
        if p is None and signed["source"] == "embedded":
            # Materializing a logo belongs to the worker, not to a read of the page's settings.
            return None
        if p and p.get("logo") and self._path("data"):
            p = {**p, "logo": str(self._path("data") / "logos" / p["logo"])}
        return p

    @Slot()
    def refresh(self):
        if self._closed:
            return
        project = self.session.project
        self._settings = reports.settings(project)
        settings = self._settings
        signed = reports.signature(project, self.cfg.report_profiles, self.cfg.report_profile)
        default = reports.default_profile(self.cfg.report_profiles, self.cfg.report_profile) or _("nobody")
        first = (_("As saved: {name}").format(name=signed["name"]) if signed["source"] == "embedded"
                 and settings["profile"] is None else _("Default: {name}").format(name=default))
        names = [p["name"] for p in (reports.clean_profile(p) for p in self.cfg.report_profiles) if p]
        self._profiles = [{"name": first, "id": None}, {"name": _("Nobody: only the project and the date"), "id": ""}]
        self._profiles += [{"name": n, "id": n} for n in names]
        if settings["profile"] and settings["profile"] not in names:
            self._profiles.append({"name": _("{name} (not in the Settings)").format(name=settings["profile"]),
                                   "id": settings["profile"]})
        self._chapters = []
        labels = {"sim": _("the production"), "results": _("modules laid"), "plant": _("inverters"),
                  "load": _("the consumption"), "econ": _("the economics"), "checks": _("checks")}
        for n, cid in enumerate(reports.templates()[settings["template"]].chapters, 1):
            c = reports.chapters(profile_id=self.session.project.regulatory_profile)[cid]
            missing = reports.missing(c, self.report_data())
            reason = _("Left out: it needs {what}.").format(what=", ".join(labels.get(k, k) for k in missing)) if missing else ""
            self._chapters.append({"id": cid, "title": f"{n}. {c.title}", "checked": cid not in settings["off"],
                                   "enabled": not missing, "note": c.note, "reason": reason})
        key = json.dumps(settings["attachments"], sort_keys=True)
        if key != self._attachment_key:
            self._attachment_key = key
            self._attachment_generation += 1
            self._attachments = [{**a, "pages": 0, "problem": "", "title": reports.attachment_title(a)}
                                 for a in settings["attachments"]]
            if self._attachments:
                QThreadPool.globalInstance().start(_AttachmentRead(self._attachment_generation, self.session.photo(),
                                                                  self._attachment_signals))
        self.contentChanged.emit()
        self.changed.emit()

    @Slot(int, object)
    def _attachments_done(self, generation, rows):
        if not self._closed and generation == self._attachment_generation:
            for a in rows:
                a["detail"] = (_("Left out: {why}").format(why=a["problem"]) if a["problem"] else
                               ngettext("{file}, {n} page", "{file}, {n} pages", a["pages"]).format(
                                   file=Path(a["path"]).name, n=a["pages"]))
                if a.get("protected"):
                    a["detail"] += " · " + _("protected: its pages go in as images")
            self._attachments = rows
            self.contentChanged.emit()

    def _session_changed(self, topics):
        if topics == {"selection"}:
            return
        if self._export_after_year and not self.session.year_outdated():
            path, self._export_waiting, self._export_after_year = self._export_waiting, "", False
            if path:
                # Through exportPdf: a preview still running (cancelled just below) ends first, then the PDF goes, from
                # the queue. Started at once, the killed preview's end was taken for the PDF's: PDF lost, and the PDF's
                # process read with none in hand (AttributeError in _read_output, Rho in r17-unita, 06/11/2026).
                QTimer.singleShot(0, self, lambda p=path: self.exportPdf(p))
        if "file" in topics:
            self._data = {}
            self._pages, self._count, self._swap, self._outline = [], 0, None, []
            if self._handle is None:
                self._busy = False      # a swap of the pages of the project before, dropped
            self.pagesChanged.emit()
        self._stale, self._ahead_failed, self._state = True, False, None
        self.refresh()
        self._schedule(topics)
        self._plan_ahead()

    def _restarting(self, topics=None):
        """Whether the preview of the page in hand is made again by the jobs' center after its quiet (the kind's
        restart on these topics), as the page's own timer did before."""
        handle = self._handle
        return (handle is not None and handle.active and handle.kind is report_job.PREVIEW
                and (topics is None or handle.kind.follows(topics)))

    def _schedule(self, topics=None):
        if self._active:
            if self._busy and self._mode == "preview":
                if self._restarting(topics):
                    if not self.ready:      # nothing to make the report of: not made again (the page's rule)
                        self.cancel()
                    return
                if not self._stale:     # R548: the preview on its way (made ahead) answers for the project: it ends
                    return
                self.cancel()
            if self.ready and not self._fresh():
                self._timer.start()

    @Slot(bool)
    def setActive(self, active):
        self._active = bool(active)
        if active:
            self._ahead_entered()
            self.center.warm(report_job.PREVIEW)        # its process ready, its imports done (study 41)
            self._schedule()
        else:
            self._timer.stop()
            if self._busy and self._mode == "preview":
                self.cancel()
            self._plan_ahead()

    def _fail(self, message):
        self._error = str(message)
        self.failed.emit(self._error)
        self.changed.emit()

    @Slot(str, 'QVariant')
    def setSetting(self, key, value):
        if hasattr(value, "toVariant"):
            value = value.toVariant()
        valid = (key in self._settings and
                 (key != "template" or isinstance(value, str) and value in reports.templates()) and
                 (key != "off" or isinstance(value, list) and all(isinstance(c, str) and c in reports.chapters(profile_id=self.session.project.regulatory_profile) for c in value)) and
                 (key not in ("address", "register") or isinstance(value, bool)) and
                 (key not in ("client", "revision") or isinstance(value, str)) and
                 (key != "profile" or value is None or isinstance(value, str)) and
                 (key != "attachments" or isinstance(value, list) and reports.clean_attachments(value) == value))
        if not valid:
            self._fail(_("Invalid value") + ": " + key)
            return
        if self._settings.get(key) == value and key in (self.session.project.report or {}):
            return
        self._error = ""
        self.session.edit(_("Change the report"), lambda p: setattr(p, "report", {**(p.report or {}), key: copy.deepcopy(value)}))

    @Slot(str, bool)
    def setChapter(self, cid, on):
        if cid not in reports.chapters(profile_id=self.session.project.regulatory_profile):
            self._fail(_("Invalid value") + ": " + cid)
            return
        self.setSetting("off", [c for c in self._settings["off"] if c != cid] + ([] if on else [cid]))

    @Slot('QVariantList')
    def addAttachments(self, paths):
        items = copy.deepcopy(self._settings["attachments"])
        known = {os.path.normcase(str(Path(a["path"]).absolute())) for a in items}
        for raw in paths:
            path = raw.toLocalFile() if isinstance(raw, QUrl) else str(raw)
            if path.startswith("file:"):
                path = QUrl(path).toLocalFile()
            if not path:
                continue
            key = os.path.normcase(str(Path(path).absolute()))
            if key not in known:
                items.append({"path": str(Path(path)), "title": ""})
                known.add(key)
        self.setSetting("attachments", items)

    @Slot(int, str)
    def retitleAttachment(self, index, title):
        items = copy.deepcopy(self._settings["attachments"])
        if 0 <= index < len(items):
            items[index]["title"] = title.strip()
            self.setSetting("attachments", items)

    @Slot(int, int)
    def moveAttachment(self, index, step):
        items = copy.deepcopy(self._settings["attachments"])
        other = index + step
        if 0 <= index < len(items) and 0 <= other < len(items):
            items[index], items[other] = items[other], items[index]
            self.setSetting("attachments", items)

    @Slot(int)
    def removeAttachment(self, index):
        self.setSetting("attachments", [a for k, a in enumerate(self._settings["attachments"]) if k != index])

    @Slot(str)
    def command(self, name):
        self.commandRequested.emit(name)

    @Slot()
    def requestPreview(self):
        self.pageTextCancelled.emit()
        if self._busy:
            if self._active:
                self._timer.start()
            return
        self._timer.stop()  # A manual request consumes the pending automatic preview.
        self._start("preview")

    @Slot(str, int)
    def exportReport(self, path, kind=0):
        """The report as the file dialog's filter says (0 PDF, 1 ODT, 2 DOCX, R460): the extension put right."""
        from meridiana.gui.paper.report import KINDS
        if path.startswith("file:"):
            path = QUrl(path).toLocalFile()
        if not path:
            return
        suffix = KINDS[kind] if 0 <= kind < len(KINDS) else "pdf"
        target = Path(path)
        if target.suffix.lower() != "." + suffix:
            target = target.with_name(target.name + "." + suffix) if target.suffix.lower() not in (
                ".pdf", ".odt", ".docx") else target.with_suffix("." + suffix)
        if suffix != "pdf":
            from meridiana.app.report import editable
            missing = editable.missing_libraries(suffix)
            if missing:
                self._fail(_("The {kind} export needs a library that is not installed: {libraries}.").format(
                    kind=suffix.upper(), libraries=", ".join(missing)))
                return
        self.exportPdf(str(target))

    @Slot(str)
    def exportPdf(self, path):
        if path.startswith("file:"):
            path = QUrl(path).toLocalFile()
        if path and self._busy:
            # Asked while the preview (or another PDF) is being made: kept, said, and written when that one ends.
            self._export_queued = path
            self._queued_note = (_("The PDF will be written as soon as the preview is ready") if self._mode == "preview"
                                 else _("The PDF will be written after the one in progress"))
            self.changed.emit()
            return
        if path:
            if not Path(path).parent.is_dir():      # said at once: the job would say it only after the report
                self._fail(_("{file} cannot be written").format(file=Path(path)))
                return
            if self.session.year_outdated():      # R437: asked first, it does not go out with old numbers unawares
                self._export_waiting = path
                self.recomputeAsked.emit()
                return
            self._start("export", Path(path))

    @Slot()
    def recomputeThenExport(self):
        """«Compute and then export»: the file goes when the year answers for the project."""
        if self._export_waiting:
            self._export_after_year, self._state = True, None
            self.commandRequested.emit("compute")
            self.changed.emit()

    @Slot()
    def exportAsItIs(self):
        path, self._export_waiting = self._export_waiting, ""
        if path:
            self._start("export", Path(path))

    @Slot()
    def dropExport(self):
        self._export_waiting, self._export_after_year, self._state = "", False, None
        self.changed.emit()

    @Property('QVariantMap', notify=changed)
    def exportState(self):
        """R437: whether the numbers are up to date, and whether the report exported last still answers for the
        project. Made again after a change of the project or an export, not at every word of the page (R598: the
        year's key and the file of the exports read at each `changed`, 10-40 ms on Rho)."""
        if self._state is None:
            self._state = self._export_state()
        return self._state

    def _export_state(self):
        fingerprint = self.session.year_fingerprint() if self.session.energy else ""
        record = self._export_record()
        waiting = self._export_after_year
        if not self.session.energy:
            numbers, stale = _("Nothing computed yet: the report needs the production."), True
        elif self.session.year_outdated():
            numbers, stale = _("Numbers not up to date: compute before exporting."), True
        else:
            numbers, stale = _("Numbers up to date."), False
        exported = ""
        behind = False
        if record:
            behind = record.get("fingerprint") != fingerprint
            exported = (_("Report exported on {date}: it no longer answers for the project.") if behind
                        else _("Report exported on {date}: it answers for the project.")).format(date=record.get("date", ""))
        return dict(numbers=numbers, stale=stale, exported=exported, behind=behind, waiting=waiting,
                    file=record.get("file", "") if record else "")

    def _exports_path(self):
        folder = self._path("state")
        return Path(folder) / "quick-report-exports.json" if folder is not None else None

    def _export_record(self):
        path = self._exports_path()
        name = str(self.session.path) if self.session.path else ""
        if name and name in self._records:      # what the export's job wrote just now: not read again
            return self._records[name]
        if path is None or not name or not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8")).get(name)
        except (OSError, ValueError, AttributeError):
            return None

    # the jobs

    def _root(self):
        """The folder of this backend's reports, under the cache: every folder of its jobs, the year written here,
        the pause of a preview made ahead; taken away when the backend closes."""
        base = self._path("cache") or Path(tempfile.gettempdir())
        # report_job.make and _YearWrite create their folders in their workers.
        return Path(base) / self._root_name

    def _year_spec(self, mark=None, good=None):
        """Where the job finds the year: the store of the years, unless it said it has not this year (then the file
        written here by the pool, once for every report of this year and these layouts)."""
        mark = mark if mark is not None else (self.session.energy, self.session.results)
        missed = self._store_miss is not None and all(a is b for a, b in zip(self._store_miss, mark, strict=True))
        spec = None if missed else report_job.year_spec(self.session, self.year_cache)
        if spec is not None:
            return spec
        if self._year_mark is None or any(a is not b for a, b in zip(self._year_mark, mark, strict=True)):
            self._year_mark, self._year_writing = mark, None
            self._year_count += 1
        path = self._root() / "window-years" / f"year-{self._year_count}.pickle"
        if self._year_writing != path:
            self._year_writing = path
            self._serial += 1
            year = {**mark[0], "results": self.session.good_results() if good is None else good}
            QThreadPool.globalInstance().start(_YearWrite(self._serial, path, year, self._request_signals))
        return {"file": str(path)}

    def _request(self):
        """The job's request, small: the photo (a reference), the options, where the year is. Made again by the
        jobs' center at each restart of the page's preview (the kind's restart calls it), so the pages it makes
        are those of the project as it is."""
        signed = reports.signature(self.session.project, self.cfg.report_profiles, self.cfg.report_profile)
        preview = self._mode == "preview"
        ahead = preview and self._ahead_run
        targets = [] if preview else [str(self._target)] + (
            [str(t) for t in register_paths(self._target)] if self._settings["register"] else [])
        root = self._root()
        drop, self._drop = self._drop, []
        exports = self._exports_path()
        remember = None
        if not preview and exports is not None and self.session.path:
            remember = {"path": str(exports), "name": str(self.session.path)}
        request = {"worker": WORKER, "mode": self._mode, "photo": self.session.photo(), "year": self._year_spec(),
                   "extra": dict(self._data), "profile": self.profile(),
                   "embedded": signed["source"] == "embedded" and signed["profile"] is None,
                   "language": i18n.language(), "width": 1240,
                   "kind": kind_of(self._target) if not preview else "pdf",
                   "register": self._settings["register"], "date": datetime.date.today().strftime("%d/%m/%Y"),
                   "root": str(root), "targets": targets, "pause": str(root / "pause") if ahead else None,
                   "low": ahead, "spare": self._active and not ahead, "drop": drop, "remember": remember}
        if preview:
            self._stale, self._made = False, self._key()
        self._asked_project = str(self.session.path) if self.session.path else ""
        self._asked_request = request
        self._asked_year = (self.session.energy, self.session.results, self.session.good_results())
        return request

    def _start(self, mode, target=None, ahead=False, request=None):
        if self._closed:
            return
        self._ahead.stop()          # R548: a preview made ahead runs below the window (report_job.AHEAD)
        self._mode, self._target, self._ahead_run = mode, target, ahead
        kind = report_job.AHEAD if ahead else report_job.PREVIEW if mode == "preview" else report_job.EXPORT
        try:
            request = self._request() if request is None else request
            build = self._request if kind is report_job.PREVIEW else None
            self._handle = self.center.submit(kind, request, build=build, slot=SLOT, on_partial=self._partial,
                                              on_done=self._done, on_failed=self._failed)
        except Exception as error:      # a request that cannot be made: said on the page
            self._handle = None
            self._fail(error)
            return
        self._incoming, self._incoming_outline = {}, []
        self._busy, self._error = True, ""
        self._status = ""               # the job's row says what is being done
        self.changed.emit()

    def _partial(self, key, row):
        """A page of the preview on its way (report_job: "page:<n>"), kept until the preview is whole."""
        if key.startswith("page:"):
            self._incoming[int(key[5:])] = row
        elif key == "outline":
            self._incoming_outline = row

    def _done(self, result, stale):
        self._handle, self._busy = None, False
        self._went_on()
        if self._closed:
            return
        if "missing" in result:         # the year is not in the store as asked: written here, and asked again
            if stale:
                self._stale = True
                self._status = _("cancelled")
                self.changed.emit()
                self._next()
                return
            mark = self._asked_year[:2]
            self._store_miss = mark
            request = dict(self._asked_request, year=self._year_spec(mark, self._asked_year[2]))
            self._start(self._mode, self._target, self._ahead_run, request=request)
            return
        if "failed" in result:          # made ahead: not made ahead again until a change; the page makes its own
            self._stale = self._ahead_failed = True
            if self._active:
                self._fail(result["failed"])
            self._next()
            return
        if self._mode == "preview":
            # busy until the pages are shown: a piece per turn of the window, then what follows (_swap_step)
            self._busy = True
            self._swap = (report_pages.publish(result["pages"]), 0, result["total"], result["folder"])
            self.center.piece("report.pages", self._swap_step)
            return
        self._status, self._state = str(self._target), None
        if self._asked_project and result.get("written"):
            self._records[self._asked_project] = dict(file=result["written"][0], fingerprint=result["fingerprint"],
                                                         date=result["date"])
        self.completed.emit(str(self._target))
        self.changed.emit()
        self._next()

    def _swap_step(self):
        """One page of the new preview in its place (pageSet), on a turn of the window: the old pages stay shown
        until the new ones take their places. The last step leaves as many pages as the new preview has."""
        if self._swap is None or self._closed:
            return
        rows, at, total, folder = self._swap
        if at == 0:
            self.pagesReplacing.emit()
        if at < len(rows):
            if at < len(self._pages):
                self._pages[at] = rows[at]
            else:
                self._pages.append(rows[at])
            self.pageSet.emit(at, rows[at])
            self._swap = (rows, at + 1, total, folder)
            self.center.piece("report.pages", self._swap_step)
            return
        self._swap = None
        self._pages, self._count, self._outline = rows, total, self._incoming_outline
        if self._shown_folder and self._shown_folder != folder:
            self._drop.append(self._shown_folder)
        self._shown_folder = folder
        self._status = _("{n} pages, as the PDF will have them").format(n=self._count)
        self._busy = False
        self.pagesChanged.emit()
        self.changed.emit()
        held, self._held = self._held, []
        for want in dict.fromkeys(held):
            QTimer.singleShot(0, self, lambda w=want: self.drawPage(w))
        self._next()

    def _failed(self, _kind, text):
        self._handle, self._busy = None, False
        self._went_on()
        if self._closed:
            return
        if self._mode == "preview":
            self._stale = self._ahead_failed = True     # R548: not made ahead again until a change
        self._fail(text)
        self._next()

    def _rows_changed(self):
        """The jobs' rows changed: a job of ours dropped without an answer (Cancel from its row, a change that
        discards a preview made ahead, another job in its slot) is over here too."""
        handle = self._handle
        if handle is None or handle.active or self._closed:
            return
        if handle.state == "cancelled":
            self._handle, self._busy = None, False
            self._went_on()
            self._status = _("cancelled")
            self._stale = self._stale or self._mode == "preview"
            self.changed.emit()
            self._next()

    def _next(self):
        """What follows a report's end: a PDF asked meanwhile, or the preview made ahead planned."""
        if self._closed:
            return
        if self._export_queued:
            path, self._export_queued = self._export_queued, ""
            QTimer.singleShot(0, self, lambda p=path: self.exportPdf(p))
        elif not self._active:
            self._plan_ahead()

    @Slot(int, str)
    def _written(self, serial, error):
        if error and not self._closed and self._busy:
            self.cancel()
            self._fail(_("The preview could not be made: {error}").format(error=error))

    @Slot()
    def cancel(self):
        self.pageTextCancelled.emit()
        self._timer.stop()
        if self._handle is not None and self._handle.active:
            self.center.cancel(self._handle)            # its row goes at once: _rows_changed

    @Slot(str)
    def pageTextError(self, message):
        self._fail(message)

    @Slot(str)
    def drawPage(self, want):
        """A page of the preview at a width in device pixels («key/width»): drawn on the pool, then pageDrawn."""
        if not self._drawing:
            report_pages._signals().done.connect(self.pageDrawn)
            self._drawing = True
        if self._swap is not None:
            self._held.append(want)     # asked once the new pages are in (the drawings hold the interpreter)
            return
        self.center.timed("report.draw", report_pages.ask, want)

    def close(self):
        self.pageTextCancelled.emit()
        if self._closed:
            return
        self.cancel()
        self._closed = True
        self._active = False
        self._timer.stop()
        self._ahead.stop()
        self._went_on()
        if self._own_work is not None:
            self._own_work.close()
        if self._session_changed in self.session.listeners:
            self.session.listeners.remove(self._session_changed)
        base = self._path("cache") or Path(tempfile.gettempdir())
        shutil.rmtree(Path(base) / self._root_name, ignore_errors=True)     # its processes went with the center
