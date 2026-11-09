"""Nonblocking map capabilities and local-model discovery for the settings page."""
from copy import deepcopy
from datetime import date
from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, Property, QRunnable, QThreadPool, QUrl, Signal, Slot
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from meridiana import capabilities
from .settings_text import _


class _SurveySignals(QObject):
    finished = Signal(object, str)


class _SurveyJob(QRunnable):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.signals = _SurveySignals()

    def run(self):
        from meridiana.assistant import local
        try:
            result = local.survey(extra=(self.url,))
        except Exception as error:  # worker boundary: every failure is displayed
            self.signals.finished.emit(None, str(error))
        else:
            self.signals.finished.emit(result, '')


class _TaskJob(QRunnable):
    def __init__(self, work):
        super().__init__()
        self.work = work
        self.signals = _SurveySignals()

    def run(self):
        try:
            result = self.work()
        except Exception as error:  # worker boundary: errors are reported on the page
            self.signals.finished.emit(None, str(error))
        else:
            self.signals.finished.emit(result, '')


class SettingsServices(QObject):
    changed = Signal()
    downloadProgress = Signal(int, int)

    def __init__(self, backend):
        super().__init__(backend)
        self.backend = backend
        self.net = QNetworkAccessManager(self)
        self._reply = None
        self._caps = {}
        self._layers = {}
        self._map_status = ''
        self._local_status = ''
        self._models = []
        self._local_guide = {}
        self._survey = None
        self._closed = False
        self._test = None
        self._test_status = ''
        self._provider = None
        self._download = None
        self._download_status = ''
        self._download_fraction = 0.0
        self._stop_download = Event()
        self.downloadProgress.connect(self._progress)
        backend.changed.connect(self._settings_changed)

    @Property(bool, notify=changed)
    def testBusy(self):
        return self._test is not None

    @Property(str, notify=changed)
    def testStatus(self):
        return self._test_status

    @Property(bool, notify=changed)
    def downloadBusy(self):
        return self._download is not None

    @Property(str, notify=changed)
    def downloadStatus(self):
        return self._download_status

    @Property(float, notify=changed)
    def downloadFraction(self):
        return self._download_fraction

    @Property(str, notify=changed)
    def mapStatus(self):
        return self._map_status

    @Property(bool, notify=changed)
    def mapBusy(self):
        return self._reply is not None

    @Property('QVariantMap', notify=changed)
    def layers(self):
        return deepcopy(self._layers)

    @Property(bool, notify=changed)
    def localBusy(self):
        return self._survey is not None

    @Property(str, notify=changed)
    def localStatus(self):
        return self._local_status

    @Property('QVariantMap', notify=changed)
    def localGuide(self):
        return self._local_guide

    @Slot(str)
    def copyCommand(self, text):
        from PySide6.QtGui import QGuiApplication
        QGuiApplication.clipboard().setText(text)

    @Property('QVariantList', notify=changed)
    def localModels(self):
        return deepcopy(self._models)

    def _settings_changed(self, key, value):
        if key == 'network_tiles' and not value and self._reply is not None:
            self._reply.abort()
        if key == 'map_sources':
            addresses = {source.get('key'): source.get('capabilities') or source.get('url') for source in value}
            obsolete = [source for source, (address, _caps) in self._caps.items() if addresses.get(source) != address]
            for source in obsolete:
                self._caps.pop(source)
                self._layers.pop(source, None)
            if obsolete:
                self.changed.emit()

    @Slot(int, result=bool)
    def readCapabilities(self, index):
        if self._closed:
            return False
        if not self.backend.cfg.network_tiles:
            self._map_status = _('The map servers are switched off in Settings > Privacy.')
            self.changed.emit()
            return False
        if self._reply is not None or not 0 <= index < len(self.backend.cfg.map_sources):
            return False
        source = self.backend.cfg.map_sources[index]
        address = source.get('capabilities') or source.get('url', '')
        if source.get('kind') not in ('wmts', 'wms'):
            self._map_status = _('Choose WMS or WMTS first.')
            self.changed.emit()
            return False
        url = QUrl(capabilities.capabilities_url(address, source['kind']))
        if url.scheme() not in ('https', 'http') or not url.host():
            self._map_status = _('Paste the address of the service first.')
            self.changed.emit()
            return False
        request = QNetworkRequest(url)
        request.setRawHeader(b'User-Agent', b'Meridiana/Quick')
        request.setTransferTimeout(30000)
        reply = self.net.get(request)
        self._reply = reply
        self._map_status = _('Reading…')
        reply.downloadProgress.connect(lambda done, _total: reply.abort() if done > capabilities.MAX_BYTES else None)
        reply.finished.connect(lambda: self._map_finished(reply, source['key'], address))
        self.changed.emit()
        return True

    def _map_finished(self, reply, key, address):
        self._reply = None
        if self._closed:
            reply.deleteLater()
            return
        if reply.error() == QNetworkReply.NetworkError.NoError:
            self.accept_capabilities(key, address, bytes(reply.readAll()))
        else:
            self._map_status = _('The server did not answer: {error}').format(error=reply.errorString())
        reply.deleteLater()
        self.changed.emit()

    def accept_capabilities(self, key, address, data):
        """Recorded replies and live replies follow the same parser and source matching."""
        current = next((s for s in self.backend.cfg.map_sources if s.get('key') == key), None)
        if current is None or (current.get('capabilities') or current.get('url')) != address:
            self._map_status = _('The source changed while its capabilities were being read. Read them again.')
            self.changed.emit()
            return False
        try:
            caps = capabilities.read(data)
        except ValueError as error:
            self._map_status = _('Not readable: {why}').format(why=error)
            self.changed.emit()
            return False
        self._caps[key] = (address, caps)
        self._layers[key] = [dict(value=layer.name, label=layer.title) for layer in caps.layers if not layer.problem(caps.kind)]
        self._map_status = _('{title}: {n} layers usable on the plan.').format(title=caps.title or caps.kind.upper(), n=len(self._layers[key]))
        self.changed.emit()
        return True

    @Slot(int, str, result=bool)
    def chooseLayer(self, index, name):
        sources = deepcopy(self.backend.cfg.map_sources)
        if not 0 <= index < len(sources) or sources[index]['key'] not in self._caps:
            return False
        previous = sources[index]
        address, caps = self._caps[previous['key']]
        if (previous.get('capabilities') or previous.get('url')) != address:
            return False
        layer = caps.layer(name)
        if layer is None or layer.problem(caps.kind):
            return False
        new = capabilities.source_dict(caps, layer, previous['key'], previous.get('name', ''), address,
                                       previous.get('added') or date.today().isoformat())
        for key in ('name', 'attribution', 'licence', 'licence_url', 'imagery'):
            if previous.get(key):
                new[key] = previous[key]
        sources[index] = previous | new
        return self.backend.setValue('map_sources', sources)

    @Slot(result=bool)
    def searchLocal(self):
        if self._closed or self._survey is not None:
            return False
        job = _SurveyJob(self.backend.cfg.assistant_local_url)
        self._survey = job
        job.signals.finished.connect(self._local_finished)
        self._local_status = _('Looking for the local models on this PC…')
        self.changed.emit()
        QThreadPool.globalInstance().start(job)
        return True

    @Slot(object, str)
    def _local_finished(self, survey, error):
        self._survey = None
        if self._closed:
            return
        self._models = []
        self._local_guide = {}
        if error:
            self._local_status = _('Could not search for local models: {reason}').format(reason=error)
        else:
            for runtime in survey.runtimes:
                for model in runtime.models:
                    self._models.append(dict(name=model.name, runtime=runtime.name, url=runtime.url,
                                             api='ollama' if runtime.api == 'ollama' else '',
                                             usable=runtime.running and not runtime.locked,
                                             note=runtime.note or (runtime.start() if not runtime.running else '')))
            if survey.choice:
                self._local_status = survey.choice.reason(survey.machine)
            else:
                from meridiana.assistant import local
                candidate, steps = local.guide(survey.machine, have_ollama=any(r.kind == 'ollama' for r in survey.runtimes))
                from meridiana.i18n import number
                pc = survey.machine
                gpu = _(', {gpu} with {vram} GB').format(gpu=pc.gpu, vram=number(pc.vram_gb, 0)) if pc.vram_gb else ''
                self._local_status = _('No program of local models on this PC (Ollama, LM Studio, llama.cpp, Jan, Lemonade, Docker Model Runner): none answers and none is on the disk.') if not survey.runtimes else '\n'.join(r.name + ': ' + r.note for r in survey.runtimes)
                self._local_guide = dict(
                    machine=_('This PC: {ram} GB of RAM{gpu}; about {budget} GB for a model.').format(ram=number(pc.ram_gb, 0), gpu=gpu, budget=number(pc.budget_gb, 0)),
                    title=_('<b>How to give {name} a model of his own</b>: {model}, {why}.').format(name='Meridio', model=candidate.title, why=candidate.why()),
                    licence=_('The suggested Qwen and Gemma 4 weights use Apache-2.0. Download size is approximate; leave extra RAM for the project and other applications. Nothing downloads automatically.'),
                    card=_('Read the model card and licence'), url='https://ollama.com/library/' + candidate.ollama,
                    steps=[dict(text=step.text, command=step.command) for step in steps])
        self.changed.emit()

    @Slot(int, result=bool)
    def useLocal(self, index):
        if not 0 <= index < len(self._models) or not self._models[index]['usable']:
            return False
        model = self._models[index]
        return self.backend._commit(dict(assistant_provider='local', assistant_local_url=model['url'],
                                         assistant_local_model=model['name'], assistant_local_runtime=model['api']))

    @Slot(result=bool)
    def testLocal(self):
        from meridiana.assistant import local, providers
        if self._closed or self._test is not None:
            return False
        cfg = self.backend.cfg
        cls = providers.Ollama if cfg.assistant_local_runtime == 'ollama' else providers.OpenAICompatible
        provider = cls(model=cfg.assistant_local_model, base_url=cfg.assistant_local_url)
        provider.max_tokens = 256
        self._provider = provider
        self.destroyed.connect(provider.cancel)
        job = _TaskJob(lambda: local.check(provider))
        self._test = job
        self._testing_model = provider.model or _('the one the server serves')
        self._test_status = _('Trying {model}… The first time the server loads it from the disk: it can take a minute.').format(model=self._testing_model)
        job.signals.finished.connect(self._test_finished)
        self.changed.emit()
        QThreadPool.globalInstance().start(job)
        return True

    @Slot()
    def cancelTest(self):
        if self._provider is not None:
            self._provider.cancel()

    @Slot(object, str)
    def _test_finished(self, result, error):
        from meridiana.assistant import local
        self._test = None
        self._provider = None
        if self._closed:
            return
        self._test_status = error or local.said(result, self._testing_model)
        self.changed.emit()

    @Slot(result=bool)
    def downloadVoice(self):
        from meridiana.assistant import speech
        if self._closed or self._download is not None:
            return False
        folder = self.backend.cfg.assistant_kokoro_dir.strip()
        if not folder:
            self._download_status = _('Choose the folder for the natural voice first.')
            self.changed.emit()
            return False
        self._stop_download.clear()
        stopped = self._stop_download
        self.destroyed.connect(stopped.set)
        destination = Path(folder).expanduser()

        def download():
            try:
                speech.download_model(destination, self.downloadProgress.emit, stopped.is_set)
            except speech.Stopped:
                return False
            return True

        job = _TaskJob(download)
        self._download = job
        self._download_status = _('Downloading the natural voice…')
        self._download_fraction = 0.0
        job.signals.finished.connect(self._download_finished)
        self.changed.emit()
        QThreadPool.globalInstance().start(job)
        return True

    @Slot()
    def cancelDownload(self):
        self._stop_download.set()

    @Slot(int, int)
    def _progress(self, done, total):
        if self._closed:
            return
        self._download_fraction = done / max(1, total)
        self._download_status = _('Downloading the natural voice: {done} of {total} MB').format(done=done // 1_000_000, total=total // 1_000_000)
        self.changed.emit()

    @Slot(object, str)
    def _download_finished(self, result, error):
        self._download = None
        if self._closed:
            return
        self._download_status = error or (_('Natural voice: the model is in {folder}.').format(folder=self.backend.cfg.assistant_kokoro_dir)
                                         if result else _('Download cancelled.'))
        self.changed.emit()

    @Slot()
    def close(self):
        if self._closed:
            return
        self._closed = True
        self.cancelTest()
        self.cancelDownload()
        if self._reply is not None:
            self._reply.abort()
        for job, receiver in ((self._survey, self._local_finished), (self._test, self._test_finished),
                              (self._download, self._download_finished)):
            if job is not None:
                job.signals.finished.disconnect(receiver)
