"""File page commands over the existing session, archive and configuration formats.

The shell connects commandRequested for phase commands and dialogs. File selection
is a request to a native QtQuick.Dialogs FileDialog, never a hidden QWidget.
"""
from __future__ import annotations

import copy
import errno
import threading
import uuid
from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot

from meridiana import config, model, portability, recovery, reports
from meridiana.i18n import _
from meridiana.ui.design import Layout


def local_path(value: str) -> Path:
    url = QUrl(value)
    if url.isLocalFile():
        return Path(url.toLocalFile())
    if '://' in value:
        raise ValueError(_('Choose a local file.'))
    if not value.strip():
        raise ValueError(_('Choose a file.'))
    return Path(value)


def save_reason(error) -> str:
    """Why a file could not be written, in the designer's words (R537): the system's own sentence otherwise."""
    if isinstance(error, PermissionError):
        return _('read-only file or folder, or the file is open in another program')
    if isinstance(error, FileNotFoundError):
        return _('the folder is not there any more')
    if getattr(error, 'errno', None) == errno.ENOSPC:
        return _('the disk is full')
    return str(error)


def page_sections():
    def tile(action, icon, title, description, button, formats='', group='Project'):
        return dict(action=action, icon=icon, title=_(title), description=_(description) if description else '',
                    button=_(button), formats=formats, group=_(group))

    return {
        'open': dict(title=_('Open'), description=_('A Meridiana project from a file, or one of the last ones.'),
                     tiles=[tile('open', 'folder-open', 'A project', 'A .mer file with the project and its resources.',
                                 'Choose the file…', '.mer · .meridiana'),
                            tile('import_pvsyst', 'file-input', 'PVsyst project',
                                 'The project and the variants next to it, opened as a new project: Meridiana says what it approximated.',
                                 'Choose the file…', '.PRJ')]),
        'save': dict(title=_('Save and revisions'),
                     description=_('Keep the current project, create a copy or preserve a revision.'), tiles=[
                         tile('save', 'save', 'Save', 'Update the current project file.', 'Save'),
                         tile('save_as', 'copy-plus', 'Save as', 'Choose another name or location for the project.',
                              'Save as…', '.mer · .meridiana'),
                         tile('save_revision', 'copy-plus', 'Save a revision',
                              'Keep this version in a new numbered file next to the project.', 'Save a revision',
                              '_R01 · _R02')]),
        'export': dict(title=_('Export'),
                       description=_('What leaves the project for the client, the authorities or a colleague.'), tiles=[
                           tile('export_report', 'file-text', 'Report',
                                'Production, strings, consumption and economics with every calculation.',
                                'Export…', 'PDF', 'Documents'),
                           tile('copy_notes', 'clipboard-copy', 'Notes for the report',
                                'The paragraphs of the rules that apply, with their sources, to paste into the technical report.',
                                'Copy', _('text'), 'Documents'),
                           tile('save_revision', 'copy-plus', 'A revision',
                                'A new file next to this one, with the suffix _R01, _R02...: the previous one stays as it was.',
                                'Save', '.mer', 'Documents'),
                           tile('export_ifc', 'export_ifc', 'IFC4 model',
                                'Buildings, roofs, obstacles and every module with its string, georeferenced: for the architect, the BIM coordinator, FreeCAD.',
                                'Export…', '.ifc', 'Models'),
                           tile('export_dxf', 'export_dxf', 'Plan as DXF',
                                "Buildings, pitches, obstacles, every module with its data and the strings in their order, on named layers: for AutoCAD and the free CAD programs, local, UTM or the imported file's coordinates.",
                                'Export…', '.dxf', 'Models')]),
        'catalogues': dict(title=_('Catalogues'), description=_(
            'The modules, the inverters and the batteries Meridiana knows, with their data sheets: look, filter, add your own.'),
            tiles=[tile('catalog_module', 'library', 'PV modules', '', 'Open…', group='Catalogues'),
                   tile('catalog_inverter', 'library', 'Inverters', '', 'Open…', group='Catalogues'),
                   tile('catalog_microinverters', 'library', 'Microinverters', '', 'Open…', group='Catalogues'),
                   tile('catalog_optimizers', 'library', 'Optimizers', '', 'Open…', group='Catalogues'),
                   tile('catalog_battery', 'library', 'Batteries', '', 'Open…', group='Catalogues')]),
        'help': dict(title=_('Help and manual'),
                     description=_('How Meridiana works and how it computes, inside the program.'), tiles=[
                         tile('manual', 'book-open', 'Manual', 'The manual, at the chapter of the phase open.',
                              'Open', group='Help'),
                         tile('shortcuts', 'keyboard', 'Keyboard shortcuts',
                              'Every key of the window, with a search; change them in the same place.', 'Open', group='Help'),
                         tile('guided_tour', 'book-open', 'Guided tour',
                              'Let Meridio show the phases, tools and settings.', 'Start', group='Help'),
                         tile('report_bug', 'message-circle', 'Report a problem',
                              'Prepare a draft, review its contents and choose what to share.', 'Prepare', group='Help'),
                         tile('about', 'info', 'About Meridiana',
                              'The version, the licences, the data and where they come from.', 'Open', group='Help')]),
    }


class FilesBackend(QObject):
    stateChanged = Signal()
    sectionChanged = Signal()
    commandRequested = Signal(str)
    fileDialogRequested = Signal(str, str, str, list)
    failed = Signal(str)
    opened = Signal(str)
    saved = Signal(str)
    closed = Signal()
    # R537: a save or an open in the background, begun (kind 'save' or 'open', the file's name) and ended (the
    # file's name, or the project's once opened; the reason when it failed, empty when it went well)
    workStarted = Signal(str, str)
    workEnded = Signal(str, str, str)
    _workDone = Signal(object)          # from the worker's thread, queued to this object's

    def __init__(self, session, cfg=None, paths=None, parent=None, *, registry=None):
        super().__init__(parent)
        self.session = session
        self.cfg = cfg if cfg is not None else config.Config()
        self.paths = paths
        # Where the weather is kept: the shell gives its computation's folder, or a save finds none (M04).
        self.weather_cache = paths.cache if paths else None
        self.registry = registry
        self._section = 'open'
        self._error = self._status = ''
        self._pending = None
        self._confirmation = False
        self._save_then = False
        self._new_authorized = None
        self._trail = []
        self._sections = page_sections()
        self._disposed = False
        # R537: the shell writes and reads the files on a thread of their own, so a large project does not stop the
        # window (a copy of a large project: 0.6-1.0 s); alone (the tests of this class) everything is done at once.
        self.background = False
        self._work = self._again = self._thread = None
        self._workDone.connect(self._work_done)
        session.subscribe(self._session_changed)

    def _session_changed(self, topics):
        if not self._disposed and ('file' in topics or 'project:text' in topics or 'project' in topics):
            self.stateChanged.emit()

    def close(self):
        self.finish_work()
        self._disposed = True
        if self._session_changed in self.session.listeners:
            self.session.listeners.remove(self._session_changed)

    section = Property(str, lambda self: self._section, notify=sectionChanged)
    sections = Property('QVariantMap', lambda self: self._sections, constant=True)
    metrics = Property('QVariantMap', lambda self: dict(pageX=Layout.PAGE[0], pageY=Layout.PAGE[1]), constant=True)
    error = Property(str, lambda self: self._error, notify=stateChanged)
    busy = Property(bool, lambda self: self._work is not None, notify=stateChanged)
    status = Property(str, lambda self: self._status, notify=stateChanged)
    confirmation = Property(bool, lambda self: self._confirmation, notify=stateChanged)
    projectName = Property(str, lambda self: self.session.project.name, notify=stateChanged)
    projectPath = Property(str, lambda self: str(self.session.path or ''), notify=stateChanged)
    recent = Property('QVariantList', lambda self: [dict(path=p, name=Path(p).stem, folder=str(Path(p).parent))
                      for p in self.cfg.recent if isinstance(p, str) and p and Path(p).is_file()], notify=stateChanged)

    @Property('QVariantMap', constant=True)
    def words(self):
        return dict(back=_('Back to the project'), new=_('New'), open=_('Open'), save=_('Save and revisions'),
                    registry=_('Clients and jobs'), export=_('Export'), catalogues=_('Catalogues'),
                    preferences=_('Settings'), help=_('Help and manual'), quit=_('Quit'),
                    settingsBack=_('Back to File'), appearance=_('Appearance'), navigation=_('Navigation'),
                    settingsLead=_('Every choice applies and is saved at once. Undo the last change or restore the defaults of one section.'),
                    keyboard=_('Keyboard'), assistant=_('Assistant'), report=_('Report'), maps=_('Maps'),
                    performance=_('Performance'), privacy=_('Privacy'), recent=_('Opened recently'), noRecent=_('No project opened yet.'),
                    unsaved=_('Unsaved changes'), saveFirst=_('Save the changes to the project first?'),
                    saveChanges=_('Save'), discard=_('Discard'), cancel=_('Cancel'),
                    elsewhere=_('The other imports stand where they are used: the IFC model in {model}, the PVsyst '
                                'modules and inverters in the catalogues of {plant}, PVGIS in {production}, the load '
                                'curve in {consumption}.').format(model=_('Modelling'), plant=_('Plant'),
                                                                 production=_('Production'), consumption=_('Consumption')))

    @Slot()
    def refresh(self):
        self.stateChanged.emit()

    def _fail(self, error):
        self._error = str(error)
        self.failed.emit(self._error)
        self.stateChanged.emit()
        return False

    @Slot(str)
    def selectSection(self, key):
        allowed = {'new', 'registry', 'preferences', *self._sections}
        if key.partition(':')[0] not in allowed:
            self._fail(_('Unknown page: {page}').format(page=key))
            return
        if key != self._section:
            self._trail.append(self._section)
            self._section = key
            self.sectionChanged.emit()

    @Slot()
    def back(self):
        if self._trail:
            self._section = self._trail.pop()
            self.sectionChanged.emit()
        else:
            self.closed.emit()

    def _guard(self, action, data=None):
        if self.session.dirty():
            self._pending = (action, data)
            self._confirmation = True
            self.stateChanged.emit()
            return
        self._continue(action, data)

    def _continue(self, action, data=None):
        if action == 'callback':
            data()
        elif action == 'open':
            if self.background:
                self._open_in_background(data)
            else:
                self.openPath(data)
        elif action == 'new':
            self._new_authorized = self.session.state_key()
            self.selectSection('new')
        elif action == 'replace':
            self.session.take(data, None, saved=False)
            self.opened.emit('')
        elif action == 'quit':
            self.commandRequested.emit('quit')

    @Slot(str)
    def resolveChanges(self, choice):
        if not self._confirmation:
            return
        self._confirmation = False
        if choice == 'discard':
            pending, self._pending = self._pending, None
            if pending:
                self._continue(*pending)
        elif choice == 'save':
            if self.session.path is None:
                self._save_then = True
                self._choose_save()
            elif self.save():
                pending, self._pending = self._pending, None
                if pending:
                    self._continue(*pending)
            else:
                self._pending = None
        else:
            self._pending = None
        self.stateChanged.emit()

    @Slot()
    def cancelFileDialog(self):
        self._pending = None
        self._save_then = False
        self._confirmation = False
        self.stateChanged.emit()

    @Slot(str)
    def request(self, action):
        self._error = ''
        if action in ('new', 'quit'):
            self._guard(action)
        elif action == 'back':
            self.closed.emit()
        elif action == 'open':
            self.fileDialogRequested.emit('open', _('Open a project'), self.cfg.last_folder,
                                          [_('Meridiana projects (*.mer *.meridiana)')])
        elif action == 'save':
            self.write()
        elif action == 'save_as':
            self._choose_save()
        elif action == 'save_revision':
            self.write(revision=True)
        else:
            self.commandRequested.emit(action)
        self.stateChanged.emit()

    def _choose_save(self):
        start = str(self.session.path or Path(self.cfg.last_folder or '.') / (self.session.project.name + '.mer'))
        self.fileDialogRequested.emit('save', _('Save the project'), start,
                                      [_('Meridiana projects (*.mer *.meridiana)')])

    @Slot(str)
    def openChosen(self, value):
        if value:
            self._guard('open', value)

    @Slot(str, str)
    def fileChosen(self, kind, value):
        if not value:
            self.cancelFileDialog()
        elif kind == 'open':
            self.openChosen(value)
        elif kind == 'save':
            onward = self._save_then
            self._save_then = False
            if not onward:
                self.write(value)
            elif self.saveAs(value):
                pending, self._pending = self._pending, None
                if pending:
                    self._continue(*pending)
            else:
                self._pending = None

    def _remember(self, target):
        self.cfg.last_folder, self.cfg.last_project = str(target.parent), str(target)
        self.cfg.recent = [str(target), *[p for p in self.cfg.recent
                                        if isinstance(p, str) and p != str(target)]][:8]
        if self.paths is not None:
            try:
                config.save(self.cfg, self.paths.config_file)
            except OSError as error:
                self._fail(_('The settings could not be saved: {error}').format(error=error))

    def _profile(self):
        signed = reports.signature(self.session.project, self.cfg.report_profiles, self.cfg.report_profile)
        profile = signed['profile']
        if profile is None and signed['source'] == 'embedded' and self.paths:
            return portability.profile(self.session.project, self.paths.cache)
        if profile and profile.get('logo') and self.paths:
            return {**profile, 'logo': str(self.paths.data / 'logos' / profile['logo'])}
        return profile

    @Slot(str, result=bool)
    def openPath(self, value):
        """Already-authorized open, also the entry point for the shell's startup loader."""
        try:
            path = local_path(value)
            notice = self.session.open(path, self.weather_cache)
        except Exception as error:  # Slot boundary: malformed archives must not escape into QML.
            return self._fail(_('{file} could not be opened: {error}').format(file=value, error=error))
        self._error = ''
        self._status = notice or ''
        self._link(path)
        self._remember(path)
        self.stateChanged.emit()
        self.opened.emit(str(path))
        return True

    def _link(self, path):
        if self.registry:
            linked = self.registry.project_at(path)
            if linked:
                self.session.project.job_id = self.session.project.job_id or linked['job_id']
                self.session.project.series_id = self.session.project.series_id or linked['id']
                self.session.mark_saved()

    def adopt(self, value):
        """The project in hand was read from `value` before the window was made (the launcher's argument): its file
        for Ctrl+S and the title, its link in the registry, its place among the recent projects, as openPath does
        without reading the file again."""
        path = local_path(value)
        self.session.path = path
        self.session.mark_saved()
        self._link(path)
        self._remember(path)
        self.stateChanged.emit()

    def _saved(self, path, clean=True):
        self._error = ''
        self._status = _('Saved {file}').format(file=path.name)
        if self.registry and self.session.project.job_id:
            try:
                project = self.session.project
                revision = path.stem.rsplit('_R', 1)[-1] if '_R' in path.stem else ''
                linked = self.registry.link_project(project.job_id, path, project.name,
                                                     project_id=project.series_id or None, revision=revision)
                project.series_id = linked['id']
                if clean:
                    self.session.mark_saved()
            except (OSError, ValueError) as error:
                self._fail(_('The project is saved, but its registry link could not be written: {error}').format(error=error))
        self._remember(path)
        self.stateChanged.emit()
        self.saved.emit(str(path))
        return True

    @Slot(result=bool)
    def save(self):
        if self.session.path is None:
            self._choose_save()
            return False
        return self.saveAs(str(self.session.path))

    @staticmethod
    def _target(value):
        path = local_path(value)
        if path.suffix.casefold() not in ('.mer', '.meridiana'):
            path = Path(str(path) + '.mer')
        return path

    @Slot(str, result=bool)
    def saveAs(self, value):
        try:
            path = self._target(value)
            self.session.save(path, self.weather_cache, self._profile())
        except (OSError, ValueError) as error:
            return self._fail(_('The project could not be saved: {error}').format(error=error))
        return self._saved(path)

    @Slot(result=bool)
    def saveRevision(self):
        if self.session.path is None:
            self._choose_save()
            return False
        try:
            target = self.session.save_revision(self.weather_cache, self._profile())
        except (OSError, ValueError) as error:
            return self._fail(_('The project could not be saved: {error}').format(error=error))
        return self._saved(target)

    # R537: saves and opens on a thread of their own

    def write(self, value=None, revision=False):
        """Ctrl+S, Save as (`value`) and a revision with the window free: the project as it is now, copied, is
        written on a thread of its own; the window says it past 300 ms (FilePart) and «Saved at» at the end. A
        second Ctrl+S while one is writing comes after it. True when the save began (or was done, alone)."""
        if not self.background:
            return self.saveRevision() if revision else self.save() if value is None else self.saveAs(value)
        if self.session.path is None and value is None:
            self._choose_save()
            return False
        if self._work is not None:
            self._again = lambda: self.write(value, revision)
            return True
        try:
            path = (recovery.next_revision(self.session.path) if revision
                    else self._target(value or str(self.session.path)))
        except (OSError, ValueError) as error:
            return self._fail(_('The project could not be saved: {error}').format(error=error))
        project, key = self.session.project, self.session.state_key()
        written = copy.deepcopy(project)
        cache, profile = self.weather_cache, self._profile()

        def finish(_result, error):
            if error is not None:
                self._fail(_('The project could not be saved: {error}').format(error=error))
                self.workEnded.emit('save', path.name, save_reason(error))
                return
            clean = self.session.adopt_save(project, written, path, key)
            if self.session.project is project:
                self._saved(path, clean)
            self.workEnded.emit('save', path.name, '')
        self._begin('save', path, lambda: written.save(path, cache, profile), finish)
        return True

    def _open_in_background(self, value):
        try:
            path = local_path(value)
        except ValueError as error:
            return self._fail(_('{file} could not be opened: {error}').format(file=value, error=error))
        if self._work is not None:
            self._again = lambda: self._open_in_background(value)
            return True
        cache = self.weather_cache

        def finish(result, error):
            if error is not None:
                self._fail(_('{file} could not be opened: {error}').format(file=value, error=error))
                self.workEnded.emit('open', path.name, str(error))
                return
            project, notice = result
            self.session.take(project, path, saved=True)
            self._error = ''
            self._status = notice or ''
            self._link(path)
            self._remember(path)
            self.stateChanged.emit()
            self.opened.emit(str(path))
            self.workEnded.emit('open', project.name, '')
        self._begin('open', path, lambda: model.Project.load(path, cache), finish)
        return True

    def _begin(self, kind, path, job, finish):
        self._work = finish
        # no stateChanged here: it measures the project again for the title (43 ms on a copy of a large project) for nothing
        self.workStarted.emit(kind, path.name)

        def run():
            try:
                result = (job(), None)
            except Exception as error:  # Worker boundary: said in the window, never lost on the thread.
                result = (None, error)
            self._workDone.emit(result)
        self._thread = threading.Thread(target=run, name='meridiana-' + kind)
        self._thread.start()

    @Slot(object)
    def _work_done(self, result):
        finish, self._work = self._work, None
        if finish is not None:
            finish(*result)
        self.stateChanged.emit()
        if self._again is not None and self._work is None:
            again, self._again = self._again, None
            again()

    def finish_work(self, timeout=60.0):
        """The write in course ended before the window goes (the file is written whole or not at all anyway)."""
        if self._thread is not None:
            self._thread.join(timeout)

    @Slot(dict)
    def createProject(self, data):
        project = model.Project()
        project.name = data.get('name') or project.name
        project.site = data.get('site', model.Site())
        project.reserved = bool(data.get('reserved', False))
        project.network = data.get('network', model.Network())
        project.network_consent = copy.deepcopy(data.get('network_consent', {}))
        project.job_id = data.get('job_id', '')
        project.series_id = uuid.uuid4().hex if project.job_id else ''
        if self.registry and data.get('client_id'):
            client = self.registry.client(data['client_id'])
            if client:
                project.report['client'] = client['name']
        project.sync_network()
        model.start_from_profile(project, self.cfg.layout_defaults)      # R523: the profile's layout
        if self._new_authorized == self.session.state_key():
            self._continue('replace', project)
        else:
            self._guard('replace', project)
        self._new_authorized = None

    @Slot(object)
    def replaceProject(self, project):
        self._guard('replace', project)
