"""Importing an IFC model (study 20): the reading in a process of its own that the window watches (IfcReading), then
what was found, where it goes and what is left out, before anything is added (IfcImportDialog). The buildings come in
as one change, undone with Ctrl+Z (window._import_ifc)."""

from __future__ import annotations

import html
import json
import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, QProcess, QProcessEnvironment, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (QButtonGroup, QDialog, QDialogButtonBox, QLabel, QRadioButton, QScrollArea, QVBoxLayout,
                               QWidget)

from .. import ifc_import, log, procmem
from ..i18n import _, number
from .design import Space, Text, strong, text_font

BUDGET_S = 180                  # a reading that takes longer is stopped: the file is said too heavy (study 20, 4.2)
MEMORY = procmem.limit()        # half the PC's memory, 8 GiB at most
WATCH_MS = 500


def worker_command(path: str, mode: str = "direct") -> tuple[str, list[str], dict]:
    """The program, the arguments and the environment of the worker: this Python (its pythonw on Windows, no console
    window) with the folder of the package on its path, as the window was started from a checkout."""
    exe = Path(sys.executable)
    if os.name == "nt" and exe.name.lower() == "python.exe" and exe.with_name("pythonw.exe").is_file():
        exe = exe.with_name("pythonw.exe")
    src = str(Path(__file__).resolve().parents[2])
    env = {"PYTHONPATH": os.pathsep.join(x for x in (src, os.environ.get("PYTHONPATH", "")) if x),
           "PYTHONIOENCODING": "utf-8"}
    return str(exe), ["-m", "meridiana.ifc_worker", path, "--mode", mode], env


SECOND_TRY_S = 60               # the reading again without IfcOpenShell's iterator, after it crashed or got stuck


class IfcReading(QObject):
    """One reading: the worker started, its lines read, its time and memory watched. `progress(fraction, what)` while it
    reads; at the end `done(found)` or `failed(why)`, once. `cancel` kills it.

    A worker that crashes, or passes the time allowed, is asked once more in the «simple» way (ifc_read.MODES): the
    shapes read from the file alone, never the iterator, where IfcOpenShell crashes or loops on a broken element
    (study 20, 3.5); what is left out is said in the dialog. Past the memory allowed there is no second try. `command`
    stands in for the worker in the tests: a program with its arguments, or a function of the way giving them."""

    progress = Signal(float, str)
    done = Signal(dict)
    failed = Signal(str)

    def __init__(self, path: str, budget_s: float = BUDGET_S, memory: int = MEMORY, command=None, parent=None):
        super().__init__(parent)
        self.path, self.budget_s, self.memory = path, budget_s, memory
        self.command = command
        self.process: QProcess | None = None
        self.mode = "direct"
        self.first_failure = ""         # why the first way stopped, when the second one runs
        self.buffer = bytearray()
        self.result: dict | None = None
        self.error = ""
        self.ended = False
        self.started_at = 0.0
        self.budget = budget_s
        self.peak = 0
        self.watch = QTimer(self)
        self.watch.setInterval(WATCH_MS)
        self.watch.timeout.connect(self._watch)

    def start(self) -> None:
        self._launch("direct", self.budget_s)

    def _launch(self, mode: str, budget: float) -> None:
        program, args, env = worker_command(self.path, mode)
        if self.command is not None:
            given = self.command(mode) if callable(self.command) else self.command
            program, args = given[0], list(given[1:])
        p = QProcess(self)
        environment = QProcessEnvironment.systemEnvironment()
        for k, v in env.items():
            environment.insert(k, v)
        p.setProcessEnvironment(environment)
        p.setProgram(program)
        p.setArguments(args)
        p.readyReadStandardOutput.connect(self._out)
        p.finished.connect(self._finished)
        p.errorOccurred.connect(self._error)
        self.process, self.mode, self.budget = p, mode, budget
        self.buffer, self.result, self.error = bytearray(), None, ""
        self.started_at = self.started_at or time.monotonic()
        self.launched_at = time.monotonic()
        p.start()
        self.watch.start()

    def running(self) -> bool:
        return self.process is not None and not self.ended

    def cancel(self) -> None:
        """Stop at once: the worker killed, nothing said (the designer asked)."""
        self._end()

    def _kill(self) -> None:
        p = self.process
        if p is not None and p.state() != QProcess.ProcessState.NotRunning:
            p.finished.disconnect(self._finished)
            p.kill()
            p.waitForFinished(2000)

    def _end(self, why: str = "") -> None:
        if self.ended:
            return
        self.ended = True
        self.watch.stop()
        self._kill()
        if why:
            self.failed.emit(why)

    def _again(self, why: str) -> bool:
        """The second try in the simple way, once, after the first one crashed or got stuck: True when it started."""
        if self.mode != "direct" or self.ended or (self.command is not None and not callable(self.command)):
            return False                    # a fixed command (a fake worker of the tests) has no simple way
        self.watch.stop()
        self._kill()
        self.first_failure = why
        self.progress.emit(0.0, "again")
        self._launch("simple", SECOND_TRY_S)
        return True

    def _watch(self) -> None:
        if self.ended or self.process is None:
            return
        if time.monotonic() - self.launched_at > self.budget:
            why = _("The reading took more than {s} s and was stopped: the model is too heavy or IfcOpenShell is "
                    "stuck on it. Export from the architect's program only the building (no furniture, no "
                    "installations) and try again.").format(s=round(self.budget))
            if not self._again(why):
                self._end(why)
            return
        pid = self.process.processId()
        used = procmem.rss(pid, tree=True) if pid else None     # the venv's launcher and its interpreter
        if used:
            self.peak = max(self.peak, used)
            if used > self.memory:
                self._end(_("The reading took more than {gb} GB of memory and was stopped. Export from the "
                            "architect's program only the building and try again.").format(
                                gb=number(self.memory / procmem.GIB, 1)))

    def _out(self) -> None:
        self.buffer += bytes(self.process.readAllStandardOutput())
        while b"\n" in self.buffer:
            line, _sep, rest = bytes(self.buffer).partition(b"\n")
            self.buffer = bytearray(rest)
            try:
                msg = json.loads(line.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            if "progress" in msg:
                self.progress.emit(float(msg["progress"]), str(msg.get("what", "")))
            elif "result" in msg:
                self.result = msg["result"]
            elif "error" in msg:
                self.error = str(msg["error"])

    def _error(self, error) -> None:
        if error == QProcess.ProcessError.FailedToStart and not self.ended:
            self._end(_("The reader did not start: {why}").format(why=self.process.errorString()))

    def _finished(self, code: int, _status) -> None:
        if self.ended:
            return
        self._out()
        if self.result is None and not self.error:
            tail = bytes(self.process.readAllStandardError()).decode("utf-8", "replace").strip().splitlines()[-3:]
            if tail:
                log.complain("ifc reading", RuntimeError(" | ".join(tail)))
            why = _("IfcOpenShell stopped while reading {file} (exit code {code}): the file has something it cannot "
                    "read. The window is fine; nothing was added.").format(file=Path(self.path).name, code=code)
            if self._again(why):
                return
            self.ended = True
            self.watch.stop()
            self.failed.emit(why)
            return
        self.ended = True
        self.watch.stop()
        if self.result is not None:
            self.result["read_seconds"] = round(time.monotonic() - self.started_at, 2)
            self.result["read_peak_mb"] = round(self.peak / 2 ** 20)
            if self.first_failure:
                self.result["second_try"] = self.first_failure
            self.done.emit(self.result)
        else:
            self.failed.emit(_("{file} could not be read: {why}").format(file=Path(self.path).name, why=self.error))


class Preview(QWidget):
    """The buildings of the plan seen from above, north up: their outlines, the planes of their roofs, the exclusions;
    the site's origin as a cross."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plan: ifc_import.Plan | None = None
        self.setMinimumSize(320, 220)

    def show_plan(self, plan) -> None:
        self.plan = plan
        self.update()

    def paintEvent(self, _event) -> None:
        if self.plan is None or not self.plan.buildings:
            return
        rings = [b.footprint for b in self.plan.buildings] + [e.ring for e, _h in self.plan.exclusions]
        xs = [p[0] for r in rings for p in r] + [0.0]
        ys = [p[1] for r in rings for p in r] + [0.0]
        w, h = max(xs) - min(xs) or 1.0, max(ys) - min(ys) or 1.0
        margin = float(Space.XL)
        k = min((self.width() - 2 * margin) / w, (self.height() - 2 * margin) / h)
        ox = (self.width() - w * k) / 2
        oy = (self.height() - h * k) / 2

        def at(x, y):
            return QPointF(ox + (x - min(xs)) * k, self.height() - oy - (y - min(ys)) * k)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self.palette().text().color()
        faint = QColor(ink)
        faint.setAlphaF(0.45)
        for b in self.plan.buildings:
            painter.setPen(QPen(faint, 1.0))
            for p in b.pitches():
                painter.drawPolygon(QPolygonF([at(x, y) for x, y in p.ring]))
            painter.setPen(QPen(ink, 1.6))
            painter.drawPolygon(QPolygonF([at(x, y) for x, y in b.footprint]))
        painter.setPen(QPen(faint, 1.2))
        for e, _h in self.plan.exclusions:
            painter.drawPolygon(QPolygonF([at(x, y) for x, y in e.ring]))
        c = at(0.0, 0.0)
        painter.setPen(QPen(ink, 1.0))
        painter.drawLine(c + QPointF(-6, 0), c + QPointF(6, 0))
        painter.drawLine(c + QPointF(0, -6), c + QPointF(0, 6))
        painter.end()


def _list(title: str, items: list) -> QLabel:
    label = QLabel(f"{strong(html.escape(title))}<ul style='margin-left:-18px'>"
                   + "".join(f"<li>{html.escape(x)}</li>" for x in items) + "</ul>")
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.RichText)
    return label


class IfcImportDialog(QDialog):
    """What was found and where it goes: the place (the file's, the site moved there, the site's origin), the north
    when the file says two things, a preview from above, what is taken, approximated and left out. `plan()` is the plan
    of the choices made."""

    def __init__(self, found: dict, project, file_name: str, parent=None):
        super().__init__(parent)
        self.found, self.project = found, project
        self.name = Path(file_name).stem or "IFC"         # a building without a name takes the file's
        self.place = ifc_import.place_of(found)
        self.setWindowTitle(_("Import an IFC model"))
        box = QVBoxLayout(self)
        box.setSpacing(Space.M)
        head = QLabel(_("{file}: {schema}, from {app}; read in {s} s.").format(
            file=file_name, schema=found.get("schema", "?"), app=found.get("application") or _("an unknown program"),
            s=number(float(found.get("read_seconds", 0.0)), 1)))
        head.setWordWrap(True)
        head.setFont(text_font(Text.BODY))
        box.addWidget(head)
        if found.get("second_try"):
            again = QLabel(_("The first reading stopped ({why}); this is the second, with the simple shapes only.").format(
                why=found["second_try"]))
            again.setWordWrap(True)
            box.addWidget(again)
        where = QLabel(_("Where the buildings go").upper())
        where.setFont(text_font(Text.LABEL))
        box.addWidget(where)
        self.how = QButtonGroup(self)
        km = ifc_import.distance_km(self.place, project.site)
        choices = []
        if self.place.lat is not None:
            choices.append(("file", _("Where the file places them, around the project's site ({km} km from its "
                                      "origin)").format(km=number(km or 0.0, 2))))
            choices.append(("site", _("Move the project's site to the model's place ({lat}, {lon})").format(
                lat=number(self.place.lat, 6), lon=number(self.place.lon, 6))))
        choices.append(("origin", _("At the site's origin: the file's place is not used")))
        chosen = ifc_import.default_how(self.place, project)
        for key, text in choices:
            b = QRadioButton(text)
            b.setProperty("how", key)
            b.setChecked(key == chosen)
            self.how.addButton(b)
            box.addWidget(b)
        self.north = QButtonGroup(self)
        if self.place.disagree():
            n = QLabel(_("Where north is").upper())
            n.setFont(text_font(Text.LABEL))
            box.addWidget(n)
            for key, text in (("map", _("By the map conversion: {deg}° from the model's Y axis").format(
                    deg=number(self.place.north_map, 1))),
                              ("context", _("By the TrueNorth: {deg}°").format(deg=number(self.place.north_context, 1)))):
                b = QRadioButton(text)
                b.setProperty("north", key)
                b.setChecked(key == "map")
                self.north.addButton(b)
                box.addWidget(b)
        self.preview = Preview(self)
        box.addWidget(self.preview, 1)
        self.lists = QWidget()
        self.lists_box = QVBoxLayout(self.lists)
        self.lists_box.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self.lists)
        box.addWidget(scroll, 1)
        self.problem = QLabel()
        self.problem.setWordWrap(True)
        box.addWidget(self.problem)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText(_("Add the buildings"))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        box.addWidget(self.buttons)
        self.how.buttonToggled.connect(lambda *_a: self._refresh())
        self.north.buttonToggled.connect(lambda *_a: self._refresh())
        self._plan = None
        self._refresh()
        self.resize(620, 720)

    def choice(self) -> tuple[str, str | None]:
        how = self.how.checkedButton().property("how") if self.how.checkedButton() else "origin"
        north = self.north.checkedButton().property("north") if self.north.checkedButton() else None
        return how, north

    def _refresh(self) -> None:
        how, north = self.choice()
        self._plan = ifc_import.plan(self.found, self.project, how, north, name=self.name)
        self.preview.show_plan(self._plan)
        while self.lists_box.count():
            item = self.lists_box.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        for title, items in ((_("Taken"), self._plan.taken), (_("Approximated"), self._plan.approximated),
                             (_("Left out"), self._plan.left_out)):
            if items:
                self.lists_box.addWidget(_list(title, items))
        self.lists_box.addStretch(1)
        why = ifc_import.problem(self._plan) or ("" if self._plan.buildings else _("Nothing to add."))
        self.problem.setText(why)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(not why)

    def plan(self):
        return self._plan
