"""Meridio's installation in the shared workbench; no separate project or window.

The contract with the QML (docs/studio/39-contratto-backend-qml.md): this backend never looks for an item of the window
by name and never writes an item's property. It exposes `layerSettings` (what the configuration says about the
character), `capturing` (the overlay hidden while a picture is taken) and request signals (a phase, File, the checks,
a help page, a tour target by name); AssistantHost.qml binds and answers them, and writes back here the little state
Python needs (the phase shown, File open, the conversation open, the rectangle of the central panel). The window's
root, handed over by bind(), is used only to take a picture of it and to filter its keys.
"""
import copy
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QRect, QRectF, Qt, QUrl, Property, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtQml import QQmlComponent

from meridiana import assistant as core, atomic, checks, config, phases, rules, shortcuts, tour
from meridiana.i18n import _
from meridiana.paths import Paths

from .assistant import install_assistant
from .assistant_chat import AssistantChat
from .assistant_help import AssistantHelp
from .parts import Part, QML

LAYER_FIELDS = {'assistant': 'assistantEnabled', 'assistant_animated': 'animated', 'assistant_style': 'characterStyle',
                'assistant_docked': 'docked', 'assistant_width': 'bubbleWidth', 'assistant_height': 'bubbleHeight'}


class AssistantHost(QObject):
    """The assistant.tools protocol reads and edits the shell's ProjectSession."""
    layerSettingsChanged = Signal()
    placesChanged = Signal()
    capturingChanged = Signal()
    phaseChanged = Signal()
    fileOpenChanged = Signal()
    openedChanged = Signal()
    viewRectChanged = Signal()
    # requests to the QML (AssistantHost.qml answers each one)
    phaseRequested = Signal(str)
    fileOpenRequested = Signal()
    checksOpenRequested = Signal()
    propertiesSectionRequested = Signal(str)
    computationTabRequested = Signal(str)
    tourTargetRequested = Signal('QVariantList')
    helpRequested = Signal(str)
    toggleRequested = Signal()
    focusHelpRequested = Signal()
    dismissRequested = Signal()

    def __init__(self, session, cache, window):
        super().__init__(window.engine)
        self.session, self.cache, self.owner = session, Path(cache), window
        self.root = None
        self._phase, self._file_open, self._opened, self._capturing = 'model', False, False, False
        self._view_rect, self._attached = QRectF(), False
        base = self.cache / 'quick-profile'
        self.paths = getattr(window, 'paths', None) or Paths(*(base / name for name in ('config', 'state', 'data', 'cache')))
        self.cfg = getattr(window, 'cfg', None) or config.load(self.paths.config_file)
        window.cfg, window.paths = self.cfg, self.paths
        self.help = AssistantHelp(self, cfg=self.cfg, save=self.save_config)
        self.chat = AssistantChat(self, self.cfg, self.save_config, self)
        self.help.navigateRequested.connect(self.go_to)
        self.help.howRequested.connect(self.show_computation)
        self.chat.preferencesRequested.connect(lambda: self.go_to(['settings', 'assistant']))
        self.chat.catalogReviewRequested.connect(self.review_catalog)
        self.places = {}
        self.state_file = self.paths.state / 'quick-meridio.json'
        if self.state_file.exists():
            try:
                data, notice = atomic.read_json(self.state_file)
                self.places = {key: list(anchor) for key, value in data.items()
                               if key in core.TABS and (anchor := core.valid_anchor(value))}
                if notice:
                    self.set_status(notice)
            except (OSError, ValueError, AttributeError) as error:
                self.set_status(str(error))

    # ---- what the QML binds (Python -> QML) ----
    def _layer_settings(self):
        return {field: getattr(self.cfg, key) for key, field in LAYER_FIELDS.items()}

    layerSettings = Property('QVariantMap', _layer_settings, notify=layerSettingsChanged)

    def _get_places(self):
        return {key: list(anchor) for key, anchor in self.places.items()}

    places_by_phase = Property('QVariantMap', _get_places, notify=placesChanged)

    def _get_capturing(self):
        return self._capturing

    capturing = Property(bool, _get_capturing, notify=capturingChanged)

    # ---- what the QML writes back (QML -> Python), little and plain ----
    def _get_phase(self):
        return self._phase

    def _set_phase(self, value):
        if value != self._phase:
            self._phase = str(value)
            self.phaseChanged.emit()
            self.chat.view.fill_questions()

    phaseShown = Property(str, _get_phase, _set_phase, notify=phaseChanged)

    def _get_file_open(self):
        return self._file_open

    def _set_file_open(self, value):
        if bool(value) != self._file_open:
            self._file_open = bool(value)
            self.fileOpenChanged.emit()

    fileOpen = Property(bool, _get_file_open, _set_file_open, notify=fileOpenChanged)

    def _get_opened(self):
        return self._opened

    def _set_opened(self, value):
        if bool(value) != self._opened:
            self._opened = bool(value)
            self.openedChanged.emit()

    opened = Property(bool, _get_opened, _set_opened, notify=openedChanged)

    def _get_view_rect(self):
        return self._view_rect

    def _set_view_rect(self, value):
        if value != self._view_rect:
            self._view_rect = QRectF(value)
            self.viewRectChanged.emit()

    viewRect = Property(QRectF, _get_view_rect, _set_view_rect, notify=viewRectChanged)

    @property
    def project(self):
        return self.session.project

    def prepare_catalog_record(self, kind, record):
        """assistant.tools' propose_catalog_record: a card in the conversation, the review window behind its button."""
        return self.chat.prepare_catalog_record(kind, record)

    def review_catalog(self, identifier, kind, record):
        """The button of that card: the catalogue's own review window, on the plant's catalogue."""
        actions = self.owner.parts.controllers.get('plantActions')
        if actions is None:
            self.set_status(_('The catalogue is not available in this window.'))
            return
        actions.reviewProposal(identifier, kind, dict(record), self.chat)

    def save_config(self):
        save = getattr(self.owner, 'save_config', None)
        if save:
            save()
        else:
            config.save(self.cfg, self.paths.config_file)

    def selection(self):
        return self.session.selection

    def phase(self):
        return self._phase

    def phase_title(self):
        return next((p.title for p in phases.phases() if p.id == self.phase()), self.phase())

    def path(self):
        return self.session.path

    def checks(self):
        controller = self.owner.parts.controllers.get('checks')
        return list(controller.items) if controller else [checks.Item(**row) for row in self.owner.bridge._checks]

    def layouts(self):
        return self.session.results

    def energy(self):
        return self.session.energy

    def plant(self):
        controller = self.owner.parts.controllers.get('plant')
        return controller.state if controller else None

    def rules_facts(self):
        return rules.facts(self.project, self.layouts(), self.energy())

    def index_rows(self):
        part = self.owner.parts.controllers.get('filePart')
        if not part:
            return []
        jobs = {row['id']: row for row in part.registry.list_jobs(include_archived=True)}
        return [{**row, 'reserved': bool(row.get('reserved') or jobs.get(row.get('job_id'), {}).get('reserved'))}
                for row in part.registry.list_index()]

    def task_rows(self):
        return self.owner.parts.controllers['filePart'].registry.list_tasks(include_done=True)

    def apply_task(self, item):
        registry = self.owner.parts.controllers['filePart'].registry
        if item['action'] == 'create':
            return registry.create_task(item['text'], item['due'], item['job_id'], item['project_id'])
        return registry.update_task(item['task_id'], done=True)

    def dirty(self):
        return self.session.dirty()

    def open_project(self, path):
        self.owner.parts.controllers['files'].openChosen(str(path))
        return self.session.path == Path(path)

    def bindings(self):
        return shortcuts.bindings(self.cfg.shortcuts)

    def navigation_targets(self):
        from meridiana.ui.navigation_targets import catalogue
        return catalogue()

    def navigation_settings(self):
        from meridiana import navigation
        style = self.cfg.navigation if self.cfg.navigation in navigation.STYLES else navigation.DEFAULT_STYLE
        return dict(style=style, style_name=navigation.STYLES[style].name,
                    orbit=self.cfg.orbit, pivot=self.cfg.pivot, gestures=navigation.table(style), bindings=self.bindings())

    def edit(self, title, change):
        return self.session.edit(title, change)

    def history(self, action):
        getattr(self.session.undo, action)()

    def history_text(self, action):
        return getattr(self.session.undo, action + '_text')()

    def fix(self, item):
        controller = self.owner.parts.controllers.get('checks')
        if controller and item in controller.items:
            controller.requestFix(controller.items.index(item))
            self.go_to(['checks'])

    def set_status(self, text):
        self.owner.shell._notice = text
        self.owner.shell.changed.emit()

    def view_image(self):
        """Capture the actual phase view, leaving Meridio and popups out (R320): the overlay hides itself while
        `capturing` is set, the central panel's rectangle is the one the QML wrote in `viewRect`."""
        if self.root is None or self._file_open or self._view_rect.isEmpty():
            return QImage()
        self._capturing = True
        self.capturingChanged.emit()
        try:
            image = self.root.grabWindow()
            dpr = image.devicePixelRatio()
            r = self._view_rect
            return image.copy(QRect(round(r.x()*dpr), round(r.y()*dpr), round(r.width()*dpr), round(r.height()*dpr)))
        finally:
            self._capturing = False
            self.capturingChanged.emit()

    @Slot()
    def toggle(self):
        """Ctrl+L: always shows him (R503): docked, his tab chosen and the conversation open, or closed if it was."""
        self.toggleRequested.emit()

    @Slot()
    def context_help(self):
        self.focusHelpRequested.emit()

    @Slot()
    def properties_help(self):
        kind = self.selection()[0]
        key = {'site': 'site', 'building': 'building', 'subfield': 'subfield', 'exclusion': 'exclusion'}.get(kind, 'phase.' + self.phase())
        self.helpRequested.emit(key)

    def local_assistant_command(self, text):
        command = tour.local_command(text)
        if command == 'tour':
            self.help.startTour(False)
            return True
        if command == 'navigation':
            from meridiana.assistant.navigation_help import explain
            self.chat.view.answer(explain(self))
            return True
        return False

    @Slot(str)
    def show_computation(self, reference):
        phase, _, step = reference.partition(':')
        self.phaseRequested.emit(phase)
        self.computationTabRequested.emit(step)

    @Slot(str)
    def computationUnavailable(self, step):
        """AssistantHost.qml: no results page with a tab of records under the phase shown."""
        self.set_status(_('How it is computed') + (': ' + step if step else ''))

    @Slot()
    def attached(self):
        """AssistantHost.qml, once made by the registry's Loader: bind() then makes no overlay of its own."""
        self._attached = True

    @Slot()
    def tourTargetMissing(self):
        """AssistantHost.qml: none of the names asked is an item of the window (the highlight is already off, R474)."""
        self.set_status(_('The requested control is not available in this view.'))

    @Slot('QVariantList')
    def go_to(self, target):
        """Bring the window to a target: the phase, File, the checks or a property, then the tour's highlight on the
        control, named here and found in QML."""
        if not self.root or not target:
            return False
        kind, value = target[0], target[1] if len(target) > 1 else ''
        names = []
        if kind == 'phase':
            self.phaseRequested.emit(value)
            names = [value + 'Tab', 'phaseBar']
        elif kind == 'property' and value.startswith('site.'):
            self.phaseRequested.emit('model')
            self.session.select('site', '')
            fields = {'voltage': 'voltage_v', 'available_power': 'available_kw', 'requested_power': 'requested_kw'}
            key = value.partition('.')[2]
            self.propertiesSectionRequested.emit('network')
            names = ['editor:network.' + fields.get(key, key), 'rightPanel']
        elif kind in ('site', 'building', 'subfield', 'exclusion'):
            self.phaseRequested.emit('model')
            self.session.select(kind, value)
            names = ['rightPanel']
        elif kind == 'views':
            self.phaseRequested.emit('model')
            names = ['centralPanel']
        elif kind == 'checks':
            self.checksOpenRequested.emit()
            names = ['checksPanel']
        elif kind == 'assistant':
            names = ['assistantCharacter']
        elif kind in ('file', 'new', 'settings', 'setting'):
            self.fileOpenRequested.emit()
            controllers = self.owner.parts.controllers
            files = controllers.get('files') or controllers.get('file')
            if files and hasattr(files, 'selectSection'):
                section = value.partition('.')[0] if kind == 'setting' else value
                files.selectSection('new' if kind == 'new' else 'preferences:' + section if kind in ('settings', 'setting') else 'open')
            names = ['settingsPage' if kind in ('setting', 'settings') else 'fileNavigation', 'filePage']
        self.tourTargetRequested.emit(names)
        return bool(names)

    def bind(self, root):
        self.root = root
        # The registry's Loader owns the overlay once a Workbench with partSources is there. The early shell contract
        # installs parts but has no Loader: the same component is made here, parented to the window, never to a
        # second window; no wrapper of it is kept.
        if not self._attached:
            component = QQmlComponent(self.owner.engine, QUrl.fromLocalFile(str(QML / 'Assistant/AssistantHost.qml')))
            overlay = component.createWithInitialProperties({'workbench': root})
            if overlay is None:
                raise RuntimeError('\n'.join(e.toString() for e in component.errors()))
            overlay.setParent(root)
            overlay.setParentItem(root.contentItem())
            self._component = component
        root.installEventFilter(self)
        settings = self.owner.parts.controllers.get('settings')
        self._settings_values = copy.deepcopy(vars(self.cfg))
        if settings:
            settings.changed.connect(self._settings_changed)
        for controller in self.owner.parts.controllers.values():
            if controller is not self.chat and hasattr(controller, 'helpRequested'):
                controller.helpRequested.connect(self._help_requested)

    def _settings_changed(self, key, value):
        if key in LAYER_FIELDS:
            self.layerSettingsChanged.emit()
        elif key.startswith('assistant_'):
            # Settings already wrote the new value. Restore the old one only for
            # the chat's change detector, which must cancel a changed destination.
            if key in self._settings_values:
                setattr(self.cfg, key, self._settings_values[key])
            self.chat.apply_preferences({key: value})
            setattr(self.cfg, key, value)
        self._settings_values = copy.deepcopy(vars(self.cfg))

    def _help_requested(self, key):
        self.helpRequested.emit(key)

    @Slot(float, float, float, float, bool, float, float, bool)
    def placement(self, x, y, width, height, docked, layer_width, layer_height, temporary):
        """AssistantLayer.placementSaved, with the layer's size and whether he is only passing by."""
        self.cfg.assistant_width, self.cfg.assistant_height = round(width), round(height)
        self.cfg.assistant_docked = docked
        self.save_config()
        if not temporary:
            # R155, R500: where Daniel drags him is his place in every phase
            anchor = list(core.anchor_of((x, y), (46, 46), (layer_width, layer_height)))
            self.places = {phase: list(anchor) for phase in
                           set(self.places) | {self.phase(), 'model', 'plant', 'production', 'consumption', 'economics', 'report'}}
            atomic.write_json(self.state_file, self.places)
            self.placesChanged.emit()

    def eventFilter(self, obj, event):
        if obj is self.root and event.type() in (QEvent.Type.ShortcutOverride, QEvent.Type.KeyPress):
            if event.key() == Qt.Key.Key_Escape and self._opened:
                event.accept()
                if event.type() == QEvent.Type.KeyPress:
                    self.dismissRequested.emit()
                return True
        return False


def install(engine, session, cache, window):
    host = AssistantHost(session, cache, window)
    install_assistant(engine, chat=host.chat, help_service=host.help)
    engine.rootContext().setContextProperty('assistantHostBackend', host)
    return Part('assistant', sources={'assistant': QML / 'Assistant/AssistantHost.qml'},
                controllers={'assistant': host.chat, 'assistant_help': host.help},
                commands={'assistant': host.toggle, 'context_help': host.context_help,
                          'manual': lambda: host.help.openManual('README.md'),
                          'guided_tour': lambda: host.help.startTour(False)},
                bind=host.bind, close=host.chat.close)
