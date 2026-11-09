"""Report choices and isolated rendering for the Quick report page.

The worker runs the existing Qt/Typst report pipeline on its own GUI thread.
No report rendering, chart drawing or PDF compilation holds the window's thread.
"""
from __future__ import annotations

import copy
import datetime
import json
import os
from pathlib import Path
import pickle
import sys
import tempfile

from PySide6.QtCore import QObject, Property, QProcess, QProcessEnvironment, QRunnable, QThreadPool, QTimer, QUrl, Signal, Slot

from meridiana import atomic, i18n, reports
from meridiana.config import Config
from meridiana.i18n import _, ngettext
from .report_ahead import AheadPreview


class _AttachmentSignals(QObject):
    done = Signal(int, object)


class _AttachmentRead(QRunnable):
    def __init__(self, generation, project, signals):
        super().__init__()
        self.generation, self.project, self.signals = generation, project, signals

    def run(self):
        from meridiana.ui.report import attachments
        try:
            rows = [vars(a) for a in attachments(self.project)]
        except Exception as error:  # the page displays the reason, including unexpected PDF failures
            rows = [{**a, "pages": 0, "problem": str(error)}
                    for a in reports.settings(self.project)["attachments"]]
        self.signals.done.emit(self.generation, rows)


class _RequestSignals(QObject):
    written = Signal(int, str)


def _dump(data, path):
    """Pickled beside and then put in its place: a worker never reads half a file."""
    part = path.with_name(f"{path.name}.{os.getpid()}.{id(data)}.part")
    with part.open("wb") as stream:
        pickle.dump(data, stream, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(part, path)


class _RequestWrite(QRunnable):
    """The request of a preview written into its folder off the window's thread, and the year, when it is not written
    yet, into its own file kept for the next previews (study 41: 83 MB of the hourly year on Rho, 55 ms of pickle each
    time the page was entered, holding the window's thread or, from the pool, its interpreter)."""

    def __init__(self, serial, path, request, signals, year=None, year_path=None):
        super().__init__()
        self.serial, self.path, self.request, self.signals = serial, path, request, signals
        self.year, self.year_path = year, year_path

    def run(self):
        error = ""
        try:
            if self.year is not None and not self.year_path.is_file():
                _dump(self.year, self.year_path)
            if self.path is not None:
                _dump(self.request, self.path)
        except Exception as problem:  # said by the page, as a request that could not be made
            error = str(problem) or type(problem).__name__
        self.request = self.year = None
        self.signals.written.emit(self.serial, error)


WORKER = "meridiana.quick.backend.report_worker"


class ReportBackend(AheadPreview, QObject):
    changed = Signal()
    contentChanged = Signal()
    commandRequested = Signal(str)
    completed = Signal(str)
    recomputeAsked = Signal()
    pageDrawn = Signal(str)          # a page of the preview drawn at the size asked (R509, report_pages)
    failed = Signal(str)

    def __init__(self, session, cfg=None, paths=None, parent=None):
        super().__init__(parent)
        self.session, self.cfg, self.paths = session, cfg or Config(), paths
        self._export_waiting, self._export_after_year, self._export_mark = "", False, ("", "")
        self._export_queued = ""      # asked while another report was being made: it goes when that one ends
        self._queued_note = ""
        self._closed = False
        self._data = {}
        self._settings = {}
        self._chapters, self._profiles, self._attachments, self._pages = [], [], [], []
        self._busy, self._progress, self._status, self._error = False, 0., "", ""
        self._count = 0
        self._process = None
        self._run = None
        self._preview_dir = None
        self._cancelled = False
        self._attachment_key = None
        self._attachment_generation = 0
        self._drawing = False
        self._attachment_signals = _AttachmentSignals()
        self._attachment_signals.done.connect(self._attachments_done)
        self._spare = None              # (process, folder) of a worker started ahead, waiting for its request
        self._pending = None            # (serial, process) of a preview whose request is being written
        self._serial = 0
        self._request_signals = _RequestSignals()
        self._request_signals.written.connect(self._written)
        self._years = None              # the folder of the year written for the previews, and which year it is
        self._year_mark, self._year_count = None, 0
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(180)
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

    @Property('QVariantList', notify=changed)
    def pages(self):
        return self._pages

    @Property(bool, notify=contentChanged)
    def ready(self):
        return self.report_data().get("sim") is not None

    @Property(bool, notify=changed)
    def busy(self):
        return self._busy

    @Property(float, notify=changed)
    def progress(self):
        return self._progress

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
            "compute": "Compute", "pageOf": "Page {n} of {total}", "zoomIn": "Zoom in", "zoomOut": "Zoom out",
            "pdfFilter": "PDF (*.pdf)", "odtFilter": "OpenDocument text, editable (*.odt)",
            "docxFilter": "Word document, editable (*.docx)",
            "staleTitle": "Numbers not up to date", "computeExport": "Compute and then export", "exportCancel": "Cancel",
            "exportAnyway": "Export with these numbers",
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
            c = reports.chapters()[cid]
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
                QThreadPool.globalInstance().start(_AttachmentRead(self._attachment_generation, copy.deepcopy(project),
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
            self._pages, self._count = [], 0
        self._stale, self._ahead_failed = True, False
        self.refresh()
        self._schedule()
        self._plan_ahead()

    def _schedule(self):
        if self._active:
            if self._busy and self._mode == "preview":
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
            self._warm()
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
                 (key != "off" or isinstance(value, list) and all(isinstance(c, str) and c in reports.chapters() for c in value)) and
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
        if cid not in reports.chapters():
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
        if self._busy:
            if self._active:
                self._timer.start()
            return
        self._timer.stop()  # A manual request consumes the pending automatic preview.
        self._start("preview")

    @Slot(str, int)
    def exportReport(self, path, kind=0):
        """The report as the file dialog's filter says (0 PDF, 1 ODT, 2 DOCX, R460): the extension put right."""
        from meridiana.ui.report import KINDS
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
            from meridiana.report_typst import editable
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
            if self.session.year_outdated():      # R437: asked first, it does not go out with old numbers unawares
                self._export_waiting = path
                self.recomputeAsked.emit()
                return
            self._start("export", Path(path))

    @Slot()
    def recomputeThenExport(self):
        """«Compute and then export»: the file goes when the year answers for the project."""
        if self._export_waiting:
            self._export_after_year = True
            self.commandRequested.emit("compute")
            self.changed.emit()

    @Slot()
    def exportAsItIs(self):
        path, self._export_waiting = self._export_waiting, ""
        if path:
            self._start("export", Path(path))

    @Slot()
    def dropExport(self):
        self._export_waiting, self._export_after_year = "", False
        self.changed.emit()

    @Property('QVariantMap', notify=changed)
    def exportState(self):
        """R437: whether the numbers are up to date, and whether the report exported last still answers for the project."""
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
        if path is None or not name or not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8")).get(name)
        except (OSError, ValueError, AttributeError):
            return None

    def _remember_export(self, target, fingerprint, date):
        path = self._exports_path()
        if path is None or not self.session.path:
            return
        try:
            records = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        except (OSError, ValueError):
            records = {}
        records[str(self.session.path)] = dict(file=str(target), fingerprint=fingerprint, date=date)
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic.write_json(path, records)

    def _new_run(self, target=None):
        # Export's staging directory is beside its destination: atomic replace also on other volumes.
        if target is None and self._path('cache') is not None:
            self._path('cache').mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(prefix="meridiana-report-", dir=target.parent if target else self._path("cache"),
                                           ignore_cleanup_errors=True)

    def _new_process(self, folder, low=False):
        process = QProcess(self)
        environment = QProcessEnvironment.systemEnvironment()
        source = str(Path(__file__).resolve().parents[3])
        environment.insert("PYTHONPATH", source + os.pathsep + os.environ.get("PYTHONPATH", ""))
        environment.insert("PYTHONUTF8", "1")
        if low:
            environment.insert("MERIDIANA_REPORT_LOW", "1")         # R548: the preview made ahead
        for name in ("TMP", "TEMP", "TMPDIR", "MPLCONFIGDIR"):
            environment.insert(name, str(folder))
        process.setProcessEnvironment(environment)
        return process

    def _year_file(self):
        """The year of the session and its layouts in a file of their own, the same for every preview until another
        year or another layout comes: (what to write, None when it is written already; its path)."""
        mark = (self.session.energy, self.session.results)
        if self._years is None:
            self._years = self._new_run()
        if self._year_mark is None or any(a is not b for a, b in zip(self._year_mark, mark, strict=True)):
            self._year_mark = mark
            self._year_count += 1
            for old in Path(self._years.name).glob("year-*.pickle"):
                try:
                    old.unlink()        # a worker reading it keeps its handle on Linux; on Windows it is left
                except OSError:
                    pass
        path = Path(self._years.name) / f"year-{self._year_count}.pickle"
        if path.is_file():
            return None, path
        return {**self.session.energy, "results": self.session.good_results()}, path

    def _warm(self):
        """A worker started ahead, its imports done, waiting on stdin for its request (study 41): the preview does not
        wait for them. One at a time; made when the page is entered and again after each preview."""
        if self._closed or self._spare is not None:
            return
        try:
            run = self._new_run()
        except OSError:
            return              # no folder for it: the preview starts its worker cold, as before
        process = self._new_process(Path(run.name))
        process.finished.connect(self._spare_ended)
        process.start(sys.executable, ["-m", WORKER, "--warm", run.name])
        self._spare = (process, run)

    @Slot(int, QProcess.ExitStatus)
    def _spare_ended(self, _code, _status):
        """The worker kept warm ended by itself, before it was asked anything: its folder goes, another comes later."""
        if self._spare is not None and self._spare[0] is self.sender():
            process, run = self._spare
            self._spare = None
            run.cleanup()
            process.deleteLater()

    def _take_spare(self):
        spare, self._spare = self._spare, None
        if spare is None:
            return None
        spare[0].finished.disconnect(self._spare_ended)
        if spare[0].state() == QProcess.ProcessState.NotRunning:
            spare[0].deleteLater()
            spare[1].cleanup()
            return None
        return spare

    def _start(self, mode, target=None, ahead=False):
        if self._closed:
            return
        from meridiana.ui.report import kind_of
        self._ahead.stop()          # R548: a preview made ahead starts its own worker at low priority
        spare = self._take_spare() if mode == "preview" and not ahead else None
        try:
            self._run = spare[1] if spare else self._new_run(target)
            folder = Path(self._run.name)
            signed = reports.signature(self.session.project, self.cfg.report_profiles, self.cfg.report_profile)
            year = year_path = None
            if mode == "preview":
                year, year_path = self._year_file()
                energy = {"year_file": str(year_path), "extra": dict(self._data)}
            else:
                energy = self.report_data()
            request = {"project": self.session.snapshot(), "energy": energy, "profile": self.profile(),
                       "embedded": signed["source"] == "embedded" and signed["profile"] is None,
                       "mode": mode, "language": i18n.language(), "width": 1240,
                       "kind": kind_of(target) if target is not None else "pdf",
                       "register": self._settings["register"],
                       "fingerprint": self.session.year_fingerprint(), "date": datetime.date.today().strftime("%d/%m/%Y")}
            self._export_mark = (request["fingerprint"], request["date"])
            if mode == "preview":
                self._stale, self._made, self._ahead_run = False, self._key(), ahead
            self._serial += 1
            name = f"request-{self._serial}.pickle"
            if mode != "preview":
                with (folder / name).open("wb") as stream:
                    pickle.dump(request, stream, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as error:
            if spare:
                spare[0].kill()
            if self._run:
                self._run.cleanup()
                self._run = None
            self._fail(error)
            return
        self._mode, self._target = mode, target
        self._cancelled = False
        self._busy, self._progress, self._error = True, 0., ""
        self._stdout = b""
        self._stderr = b""
        if mode == "preview":
            # The request written by the pool and the worker, already warm, told to go: the window is free at once,
            # and the page says that the preview is on its way (the line of the progress and these words).
            self._status = _("Preparing the preview…")
            self._pending = (self._serial, spare[0] if spare else None)
            QThreadPool.globalInstance().start(_RequestWrite(self._serial, folder / name, request, self._request_signals,
                                                             year, year_path))
        else:
            self._status = _("Report")
            self._launch(folder, name)
        self.changed.emit()

    def _launch(self, folder, name, process=None):
        """The worker told to make what the request in `folder` asks: the warm one given (`process`), or one started."""
        cold = process is None
        if cold:
            process = self._new_process(folder, low=self._ahead_run and self._mode == "preview")
        self._process = process
        process.readyReadStandardOutput.connect(self._read_output)
        process.readyReadStandardError.connect(self._read_error)
        process.finished.connect(self._finished)
        process.errorOccurred.connect(self._process_error)
        if cold:
            process.start(sys.executable, ["-m", WORKER, str(folder), name])
        else:
            process.write(f"go {name}\n".encode("utf-8"))
            process.closeWriteChannel()

    @Slot(int, str)
    def _written(self, serial, error):
        if self._pending is None or self._pending[0] != serial or self._closed:
            return              # cancelled while it was being written: its worker went back to wait (cancel)
        _serial, process = self._pending
        self._pending = None
        if error:
            if process is not None:
                process.kill()
            self._busy = False
            if self._run:
                self._run.cleanup()
                self._run = None
            self._fail(_("The preview could not be made: {error}").format(error=error))
            return
        if process is not None and process.state() == QProcess.ProcessState.NotRunning:
            process.deleteLater()
            process = None      # the warm one is gone: a worker started now
        self._launch(Path(self._run.name), f"request-{serial}.pickle", process)
        self.changed.emit()

    @Slot()
    def _read_output(self):
        self._stdout += bytes(self._process.readAllStandardOutput())
        while b"\n" in self._stdout:
            line, self._stdout = self._stdout.split(b"\n", 1)
            try:
                data = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                continue
            if data.get("event") == "progress" and not self._closed:
                self._progress, self._status = data["fraction"], data["what"]
                self.changed.emit()

    @Slot()
    def _read_error(self):
        self._stderr = (self._stderr + bytes(self._process.readAllStandardError()))[-12000:]

    @Slot(QProcess.ProcessError)
    def _process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self._finished(-1, QProcess.ExitStatus.CrashExit)

    @Slot(int, QProcess.ExitStatus)
    def _finished(self, code, exit_status):
        if self._process is None:
            return
        self._read_output()
        self._read_error()
        process, run = self._process, self._run
        self._process, self._run = None, None
        self._busy = False
        try:
            if self._cancelled or self._closed:
                self._status = _("cancelled")
                self._stale = self._stale or self._mode == "preview"
                return
            folder = Path(run.name)
            manifest = folder / "result.json"
            if code or exit_status != QProcess.ExitStatus.NormalExit or not manifest.is_file():
                message = self._stderr.decode("utf-8", errors="replace") or _("The report could not be made")
                if self._mode == "preview":
                    self._stale = self._ahead_failed = True     # R548: not made ahead again until a change
                    if self._ahead_run and not self._active:    # made ahead: the page makes its own when entered
                        return
                self._fail(message)
                return
            result = json.loads(manifest.read_text(encoding="utf-8"))
            if self._mode == "preview":
                previous = self._preview_dir
                self._preview_dir, run = run, None
                from . import report_pages
                self._pages, self._count = report_pages.publish(result["pages"]), result["total"]
                self._status = _("{n} pages, as the PDF will have them").format(n=self._count)
                self.changed.emit()
                if previous:
                    previous.cleanup()
            else:
                from meridiana.ui.report import kind_of, register_paths
                made = folder / f"report.{kind_of(self._target)}"
                outputs = [(made, self._target)]
                if result.get("register"):
                    outputs += list(zip(register_paths(made), register_paths(self._target), strict=True))
                for source, target in outputs:
                    os.replace(source, target)
                self._status = str(self._target)
                self._remember_export(self._target, *self._export_mark)
                self.completed.emit(str(self._target))
            self._progress = 1.
        except Exception as error:
            if not self._closed:
                self._fail(error)
        finally:
            if run:
                run.cleanup()
            process.deleteLater()
            if not self._closed:
                self.changed.emit()
                if self._export_queued:
                    path, self._export_queued = self._export_queued, ""
                    QTimer.singleShot(0, self, lambda p=path: self.exportPdf(p))
                elif self._mode == "preview" and self._active:
                    QTimer.singleShot(0, self, self._warm)      # the next preview finds its worker ready
                elif not self._active:
                    self._plan_ahead()

    @Slot()
    def cancel(self):
        self._timer.stop()
        if self._pending is not None:
            # Its request still being written: dropped; its warm worker, which has not started, waits for the next one.
            _serial, process = self._pending
            self._pending = None
            run, self._run = self._run, None
            self._busy, self._status = False, _("cancelled")
            self._stale = True
            if process is not None and self._spare is None and process.state() != QProcess.ProcessState.NotRunning:
                process.finished.connect(self._spare_ended)
                self._spare = (process, run)
            else:
                if process is not None:
                    process.kill()
                run.cleanup()
            if not self._closed:
                self.changed.emit()
            return
        if self._process is not None:
            self._cancelled = True
            self._process.kill()

    @Slot()
    @Slot(str)
    def drawPage(self, want):
        """A page of the preview at a width in device pixels («key/width»): drawn on the pool, then pageDrawn."""
        from . import report_pages
        if not self._drawing:
            report_pages._signals().done.connect(self.pageDrawn)
            self._drawing = True
        report_pages.ask(want)

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._active = False
        self.cancel()
        if self._spare is not None:
            process, run = self._spare
            self._spare = None
            process.kill()
            process.waitForFinished(1000)
            run.cleanup()
        if self._years is not None:
            self._years.cleanup()
            self._years = None
        if self._session_changed in self.session.listeners:
            self.session.listeners.remove(self._session_changed)
        if self._preview_dir:
            self._preview_dir.cleanup()
            self._preview_dir = None
