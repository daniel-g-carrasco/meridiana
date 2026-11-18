"""Local runtime discovery, selection and tool-call probe, without visual widgets."""
from dataclasses import replace

from PySide6.QtCore import QObject, Property, QThreadPool, Signal, Slot
from ...assistant import local, providers
from ...i18n import _, number


class LocalModels(QObject):
    changed = Signal()
    chosen = Signal(str, str, str)
    surveyed = Signal(object)
    tested = Signal(object)

    def __init__(self, survey=None, current=lambda: ("", "", ""), parent=None, check=None):
        super().__init__(parent)
        self.survey, self.check = survey or local.survey, check or local.check
        self.current = current
        self.found = None
        self.jobs = []
        self._models, self._guide, self._runtimes = [], [], []
        self._status, self._test_status, self._machine = "", "", ""
        self._busy, self._testing = False, False
        self._index, self._testing_model = -1, ""
        self._pairs = []
        self._test_provider = None

    models = Property("QVariantList", lambda self: self._models, notify=changed)
    runtimes = Property("QVariantList", lambda self: self._runtimes, notify=changed)
    guide = Property("QVariantList", lambda self: self._guide, notify=changed)
    status = Property(str, lambda self: self._status, notify=changed)
    testStatus = Property(str, lambda self: self._test_status, notify=changed)
    machine = Property(str, lambda self: self._machine, notify=changed)
    busy = Property(bool, lambda self: self._busy, notify=changed)
    testing = Property(bool, lambda self: self._testing, notify=changed)
    selectedIndex = Property(int, lambda self: self._index, notify=changed)
    needsRam = Property(bool, lambda self: self.found is not None and not self.found.machine.ram_gb, notify=changed)

    @Slot()
    def start(self):
        if self._busy:
            return
        from .assistant_chat import Work, port_of
        self._busy = True
        self._status = _("Looking for the local models on this PC…")
        self.changed.emit()
        url = self.current()[0]
        extra = (port_of(url),) if url else ()
        job = Work(lambda: self.survey(extra=extra), local.Survey)
        job.signals.done.connect(self.show_survey)
        self._run(job)

    def _run(self, job):
        self.jobs = [j for j in self.jobs if not j.over] + [job]
        QThreadPool.globalInstance().start(job)

    @Slot(object)
    def show_survey(self, found):
        self.found, self._busy = found, False
        self._runtimes = [{"name": rt.name, "url": rt.url, "running": rt.running, "installed": rt.installed,
                           "version": rt.version, "note": rt.note, "start": rt.start(), "count": len(rt.models)}
                          for rt in found.runtimes]
        self._pairs = [(rt, model) for rt in found.running for model in rt.models]
        self._models = []
        best = found.choice
        self._index = 0 if self._pairs else -1
        for index, (runtime, model) in enumerate(self._pairs):
            fits = not model.size or not found.machine.budget_gb or local.need_gb(model.gb) <= found.machine.budget_gb
            choice = local.Choice(runtime, model, local.match(model.name), fits)
            recommended = best is not None and best.model is model
            if recommended:
                self._index = index
            self._models.append({"name": model.name, "runtime": runtime.name, "url": runtime.url,
                                 "sizeGb": model.gb, "reason": choice.reason(found.machine),
                                 "enabled": model.tools is not False and not runtime.locked,
                                 "recommended": recommended})
        self._status = "\n".join(rt.name + ": " + (rt.url if rt.running else rt.start())
                                 for rt in found.runtimes)
        if not self._status:
            self._status = _("No program of local models on this PC (Ollama, LM Studio, llama.cpp, Jan, Lemonade, Docker Model Runner): none answers and none is on the disk.")
        pc = found.machine
        gpu = _(", {gpu} with {vram} GB").format(gpu=pc.gpu, vram=number(pc.vram_gb, 0)) if pc.vram_gb else ""
        self._machine = _("This PC: {ram} GB of RAM{gpu}; about {budget} GB for a model.").format(
            ram=number(pc.ram_gb, 0), gpu=gpu, budget=number(pc.budget_gb, 0)) if pc.ram_gb else ""
        self._guide = []
        if best is None and pc.ram_gb:
            candidate, steps = local.guide(pc, have_ollama=any(rt.kind == "ollama" for rt in found.runtimes))
            self._guide = [{"text": step.text, "command": step.command} for step in steps]
            self._guide.insert(0, {"text": candidate.title + ": " + candidate.why(), "command": "",
                                   "url": "https://ollama.com/library/" + candidate.ollama})
        self.changed.emit()
        self.surveyed.emit(found)

    @Slot(float)
    def setRam(self, ram):
        if self.found is not None and 1 <= ram <= 2048:
            self.found.machine = replace(self.found.machine, ram_gb=ram)
            self.show_survey(self.found)

    @Slot(int)
    def select(self, index):
        if 0 <= index < len(self._pairs):
            self._index = index
            self.changed.emit()

    @Slot()
    def useSelected(self):
        if not 0 <= self._index < len(self._pairs) or not self._models[self._index]["enabled"]:
            return
        rt, model = self._pairs[self._index]
        self.chosen.emit(rt.url, model.name, "ollama" if rt.api == "ollama" else "")

    def provider(self):
        url, model, api = self.current()
        if api == "ollama":
            provider = providers.Ollama(model=model, base_url=url or "http://127.0.0.1:11434")
        else:
            provider = providers.OpenAICompatible(model=model, base_url=url or "http://127.0.0.1:9931/v1")
        provider.max_tokens = 256
        return provider

    @Slot()
    def probe(self):
        if self._testing:
            return
        from .assistant_chat import Work
        provider = self.provider()
        self._test_provider = provider
        self._testing_model = provider.model or _("the one the server serves")
        self._testing = True
        self._test_status = _("Trying {model}… The first time the server loads it from the disk: it can take a minute.").format(model=self._testing_model)
        self.changed.emit()
        job = Work(lambda: self.check(provider), lambda: local.Check(False, error="bad"))
        job.signals.done.connect(self._tested)
        self._run(job)

    @Slot(object)
    def _tested(self, result):
        self._testing = False
        self._test_provider = None
        self._test_status = local.said(result, self._testing_model)
        self.changed.emit()
        self.tested.emit(result)

    @Slot()
    def cancelProbe(self):
        if self._test_provider is not None:
            self._test_provider.cancel()

