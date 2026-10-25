"""Preferences > Assistant, the local models of this PC (R105, 25/10/2026; study 14a): what is running and what is
only installed, the models found with the one to use and why, «Use it» to fill the fields with one click, «Test»
to try the connection with a question that must come back as a call of a tool; when nothing is there, the steps
with their commands to copy (Ollama and the model that fits this PC).

The survey (assistant/local.survey) runs on the thread pool the first time the page is shown and again with
«Search again»: the dialog opens at once and never waits for the ports of this PC. Nothing is installed or
downloaded from here."""

from __future__ import annotations

from PySide6.QtCore import Qt, QThreadPool, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QToolButton,
                               QVBoxLayout, QWidget)

from .. import assistant
from ..assistant import local, providers
from ..i18n import _, ngettext, number
from . import icons
from .design import Space, semibold
from .style import Group

DOWNLOAD = "https://ollama.com/download"


def _escape(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class LocalModels(Group):
    """The group of the local models. `survey` is local.survey (a stand-in in the tests); `current()` gives the
    fields of the page (url, model, api) for «Test»; «Use it» says the model chosen with `chosen`."""

    chosen = Signal(str, str, str)          # url, model, api ("" OpenAI-compatible, "ollama")
    surveyed = Signal(object)               # local.Survey, shown
    tested = Signal(object)                 # local.Check

    def __init__(self, survey=None, current=lambda: ("", "", ""), parent=None):
        super().__init__(_("Local models on this PC"), parent)
        self.survey = survey or local.survey
        self.current = current
        self.found: local.Survey | None = None
        self.started = False
        self.jobs: list = []                # kept until they tell (a QRunnable's signals die with it)
        self.testing = ""                   # the model being tried
        box = QVBoxLayout(self)
        box.setSpacing(Space.S)
        self.state = QLabel(_("Looking for the local models on this PC…"))
        self.state.setWordWrap(True)
        box.addWidget(self.state)
        self.pc = QLabel()
        self.pc.setWordWrap(True)
        self.pc.hide()
        box.addWidget(self.pc)
        row = QHBoxLayout()
        self.models = QComboBox()
        self.models.currentIndexChanged.connect(self._show_why)
        row.addWidget(self.models, 1)
        self.use = QPushButton(_("Use it"))
        self.use.setToolTip(_("Fill the server, the model and its kind with this one (OK keeps it)"))
        self.use.clicked.connect(self._use)
        row.addWidget(self.use)
        self.models_row = QWidget()
        self.models_row.setLayout(row)
        row.setContentsMargins(0, 0, 0, 0)
        self.models_row.hide()
        box.addWidget(self.models_row)
        self.why = QLabel()
        self.why.setWordWrap(True)
        self.why.hide()
        box.addWidget(self.why)
        self.guide = QWidget()
        self.guide_box = QVBoxLayout(self.guide)
        self.guide_box.setContentsMargins(0, 0, 0, 0)
        self.guide_box.setSpacing(Space.XS)
        self.guide.hide()
        box.addWidget(self.guide)
        buttons = QHBoxLayout()
        self.again = QPushButton(_("Search again"))
        self.again.clicked.connect(self.start)
        buttons.addWidget(self.again)
        self.test = QPushButton(_("Test"))
        self.test.setToolTip(_("A short question to the server and the model above: it must come back as a call of a "
                               "tool, as Meridio's do"))
        self.test.clicked.connect(self._test)
        buttons.addWidget(self.test)
        buttons.addStretch(1)
        box.addLayout(buttons)
        self.test_state = QLabel()
        self.test_state.setWordWrap(True)
        self.test_state.hide()
        box.addWidget(self.test_state)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self.started:
            self.start()

    # the survey

    def start(self) -> None:
        """The survey on the pool; its result comes back to `show_survey`."""
        from .assistant_chat import Work, port_of
        self.started = True
        self.again.setEnabled(False)
        self.state.setText(_("Looking for the local models on this PC…"))
        url = self.current()[0]
        extra = (port_of(url),) if url else ()
        job = Work(lambda: self.survey(extra=extra), local.Survey)
        job.signals.done.connect(self.show_survey)
        self._run(job)

    def _run(self, job) -> None:
        """On the pool, kept until it is over (its signals live with it); bound methods only as receivers, so a
        page closed before the job tells is simply not told."""
        self.jobs = [j for j in self.jobs if not j.over] + [job]
        QThreadPool.globalInstance().start(job)

    def show_survey(self, found) -> None:
        self.found = found
        self.again.setEnabled(True)
        n = {rt.kind: len(rt.models) for rt in found.runtimes}
        lines = []
        for rt in found.running:
            text = ngettext("<b>{name}</b> {version} running at {url}: {n} model",
                            "<b>{name}</b> {version} running at {url}: {n} models", n[rt.kind]).format(
                name=_escape(rt.name), version=_escape(rt.version), url=_escape(rt.url), n=n[rt.kind])
            if rt.note:
                text += " (" + _escape(rt.note) + ")"
            lines.append(text)
        for rt in found.idle:
            text = _("<b>{name}</b> is installed, not running").format(name=_escape(rt.name))
            if rt.models:
                text += ", " + ngettext("{n} model on the disk", "{n} models on the disk", len(rt.models)).format(
                    n=len(rt.models))
            if rt.start():
                text += ": " + _escape(rt.start())
            elif rt.note:
                text += ": " + _escape(rt.note)
            lines.append(text)
        if not lines:
            lines.append(_("No program of local models on this PC (Ollama, LM Studio, llama.cpp, Jan, Lemonade, "
                           "Docker Model Runner): none answers and none is on the disk."))
        self.state.setText(semibold("<br>".join(lines)))         # the bold the semibold (R121)
        pc = found.machine
        if pc.ram_gb:
            gpu = _(", {gpu} with {vram} GB").format(gpu=pc.gpu, vram=number(pc.vram_gb, 0)) if pc.vram_gb else ""
            self.pc.setText(_("This PC: {ram} GB of RAM{gpu}; about {budget} GB for a model.").format(
                ram=number(pc.ram_gb, 0), gpu=gpu, budget=number(pc.budget_gb, 0)))
            self.pc.show()
        self.models.blockSignals(True)
        self.models.clear()
        best = found.choice
        for rt in found.running:
            for m in rt.models:
                size = _(" · {gb} GB").format(gb=number(m.gb, 1)) if m.size else ""
                text = f"{m.name} · {rt.name}{size}"
                if m.tools is False:
                    text += " · " + _("does not call tools")
                if best is not None and best.model is m:
                    text += " · " + _("recommended")
                self.models.addItem(text, (rt, m))
        if best is not None:
            for i in range(self.models.count()):
                if self.models.itemData(i)[1] is best.model:
                    self.models.setCurrentIndex(i)
        self.models.blockSignals(False)
        self.models_row.setVisible(self.models.count() > 0)
        self._show_why()
        self._show_guide(found)
        self.surveyed.emit(found)

    def _show_why(self, _index: int = -1) -> None:
        data = self.models.currentData()
        if not data or self.found is None:
            self.why.hide()
            self.use.setEnabled(False)
            return
        rt, m = data
        c = local.match(m.name)
        fits = not m.size or not self.found.machine.budget_gb or local.need_gb(m.gb) <= self.found.machine.budget_gb
        self.why.setText(local.Choice(rt, m, c, fits).reason(self.found.machine))
        self.why.show()
        self.use.setEnabled(m.tools is not False and not rt.locked)

    def _show_guide(self, found) -> None:
        """The steps when no running server has a model to use: install Ollama (unless it is there), download the
        model that fits this PC, back here."""
        while self.guide_box.count():
            item = self.guide_box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
            elif item.layout() is not None:
                lay = item.layout()
                while lay.count():
                    sub = lay.takeAt(0).widget()
                    if sub is not None:
                        sub.deleteLater()
        if found.choice is not None:
            self.guide.hide()
            return
        have = any(rt.kind == "ollama" for rt in found.runtimes)
        c, steps = local.guide(found.machine, have_ollama=have)
        title = QLabel(semibold(_("<b>How to give {name} a model of his own</b>: {model}, {why}.").format(
            name=assistant.NAME, model=_escape(c.title), why=_escape(c.why()))))
        title.setWordWrap(True)
        self.guide_box.addWidget(title)
        for n, step in enumerate(steps, 1):
            label = QLabel(f"{n}. {_escape(step.text)}")
            label.setWordWrap(True)
            self.guide_box.addWidget(label)
            if step.command:
                row = QHBoxLayout()
                row.setContentsMargins(Space.L, 0, 0, 0)
                field = QLineEdit(step.command)
                field.setReadOnly(True)
                field.setObjectName("command")
                row.addWidget(field, 1)
                copy = QToolButton()
                copy.setIcon(icons.icon("clipboard-copy"))
                copy.setToolTip(_("Copy the command"))
                copy.setAutoRaise(True)
                copy.clicked.connect(lambda _c=False, t=step.command: QApplication.clipboard().setText(t))
                row.addWidget(copy)
                self.guide_box.addLayout(row)
        if not have:
            page = QPushButton(_("Open Ollama's download page"))
            page.setIcon(icons.icon("external-link"))
            page.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DOWNLOAD)))
            self.guide_box.addWidget(page, 0, Qt.AlignmentFlag.AlignLeft)
        self.guide.show()

    def _use(self) -> None:
        data = self.models.currentData()
        if not data:
            return
        rt, m = data
        self.chosen.emit(rt.url, m.name, rt.api if rt.api == "ollama" else "")
        self.test_state.setText(_("Chosen: {model} on {runtime}. OK keeps it; «Test» tries it now.").format(
            model=m.name, runtime=rt.name))
        self.test_state.show()

    # the test

    def provider(self):
        url, model, api = self.current()
        if api == "ollama":
            p = providers.Ollama(model=model, base_url=url or "http://127.0.0.1:11434")
        else:
            p = providers.OpenAICompatible(model=model, base_url=url or "http://127.0.0.1:9931/v1")
        p.max_tokens = 256
        return p

    def _test(self) -> None:
        from .assistant_chat import Work
        provider = self.provider()
        model = provider.model or _("the one the server serves")
        self.test.setEnabled(False)
        self.test_state.setText(_("Trying {model}… The first time the server loads it from the disk: it can take a "
                                  "minute.").format(model=model))
        self.test_state.show()
        self.testing = model
        job = Work(lambda: local.check(provider), lambda: local.Check(False, error="bad"))
        job.signals.done.connect(self._tested)
        self._run(job)

    def _tested(self, result) -> None:
        self.test.setEnabled(True)
        self.test_state.setText(local.said(result, self.testing))
        self.test_state.show()
        self.tested.emit(result)
