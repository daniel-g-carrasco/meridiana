"""Install File, settings, report and modal drafts on the workbench's session."""
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Property, QTimer, QUrl, Signal, Slot
from PySide6.QtQml import QQmlComponent

from meridiana import config, model, reports, templates, updates
import subprocess
from meridiana.i18n import _
from meridiana.paths import Paths
from meridiana.registry import Registry

from .dialogs import DialogsBackend
from .files import FilesBackend
from .files_actions import FileActions
from .files_catalog import BrowseCatalog
from .parts import Part, QML
from .report import ReportBackend
from .settings import SettingsBackend


class FilePart(QObject):
    changed = Signal()
    exportRequested = Signal()
    logoRequested = Signal()

    def __init__(self, engine, session, cache, host):
        super().__init__()
        self.engine, self.session, self.host = engine, session, host
        self.root = None
        self._dialog_visible = False
        self._catalog_visible = False
        self._template = None
        self._closed = False
        # The Quick preview has its own state. Never read/write the Widgets profile.
        base = Path(cache) / 'quick-profile'
        assistant = engine.rootContext().contextProperty('assistantHostBackend')
        self.paths = getattr(host, 'paths', None) or getattr(assistant, 'paths', None) or Paths(*(base / p for p in ('config', 'state', 'data', 'cache')))
        self.paths.data.mkdir(parents=True, exist_ok=True)
        self.cfg = getattr(host, 'cfg', None) or getattr(assistant, 'cfg', None) or config.load(self.paths.config_file)
        if not self.cfg.extra.get('quick_appearance_initialized'):
            options = host.theme.options
            for key in ('theme', 'accent', 'backgrounds', 'font'):
                setattr(self.cfg, key, options[key])
            self.cfg.text_size = options['textSize']
            self.cfg.extra['reduced_motion'] = options['reducedMotion']
            self.cfg.extra['quick_appearance_initialized'] = True
        host.cfg, host.paths = self.cfg, self.paths
        self.actions = FileActions(self)
        self.catalog = BrowseCatalog(session, self)
        self.registry = Registry(self.paths.data / 'registry.sqlite3')
        self.files = FilesBackend(session, self.cfg, self.paths, registry=self.registry)
        if getattr(host, 'bridge', None) is not None:
            self.files.weather_cache = host.bridge.cache
        self.settings = SettingsBackend(self.cfg, self.paths.config_file, host.theme)
        self.settings.setDataDirectory(self.paths.data)
        self.report = ReportBackend(session, self.cfg, self.paths)
        self.dialogs = DialogsBackend(session, self.cfg, self.paths)
        self.dialogs.set_registry(self.registry)
        self.dialogs.created.connect(self.files.createProject)
        self.dialogs.projectReady.connect(self.files.replaceProject)
        self.dialogs.placementRequested.connect(self.place)
        self.dialogs.closed.connect(self.dismissDialog)
        self.dialogs.shortcutsChanged.connect(self.shortcuts_changed)
        self.dialogs.changed.connect(self.dialog_changed)
        self.dialogs.installerReady.connect(self.install_update)
        self.dialogs.commandRequested.connect(self.dispatch)
        self.dialogs.modelPlaced.connect(self.model_placed)
        self.files.commandRequested.connect(self.dispatch)
        self.files.opened.connect(self.project_opened)
        # R537: the saves and the opens of the window on a thread of their own, told in the status bar
        self.files.background = True
        self._work_token = None
        self.files.workStarted.connect(self.work_started)
        self.files.workEnded.connect(self.work_ended)
        self.files.saved.connect(self.work_saved)
        self.files.closed.connect(self.closeFile)
        self.files.sectionChanged.connect(self.section_changed)
        self.settings.commandRequested.connect(self.dispatch)
        self.settings.changed.connect(self.settings_changed)
        self.report.commandRequested.connect(self.dispatch)
        context = engine.rootContext()
        for name, value in dict(filesBackend=self.files, filesSettingsBackend=self.settings,
                                reportBackend=self.report, filesDialogsBackend=self.dialogs, filePart=self,
                                filesActions=self.actions, fileCatalogBackend=self.catalog).items():
            context.setContextProperty(name, value)

    dialogVisible = Property(bool, lambda self: self._dialog_visible, notify=changed)
    catalogVisible = Property(bool, lambda self: self._catalog_visible, notify=changed)

    @Slot()
    def closeCatalog(self):
        self._catalog_visible = False
        self.changed.emit()

    def bind(self, root):
        self.root = root
        self.settings_changed('toolbar', self.cfg.toolbar)
        self.settings_changed('toolbar_place', self.cfg.toolbar_place)
        self.settings_changed('shortcuts', self.cfg.shortcuts)
        for key in ('navigation', 'orbit', 'pivot', 'pivot_hint'):
            self.settings_changed(key, getattr(self.cfg, key))
        self.component = QQmlComponent(self.engine, QUrl.fromLocalFile(str(QML / 'Dialogs/DialogLayer.qml')))
        # R23 F6 (docs/studio/39, section 3): made once and handed to the window, never kept (a wrapper outlives its item)
        overlay = self.component.createWithInitialProperties({'parent': root.contentItem()}, self.engine.rootContext())
        if overlay is None:
            raise RuntimeError('\n'.join(e.toString() for e in self.component.errors()))
        overlay.setParent(root)
        if self.host.plan is not None:
            self.host.plan.pointsPicked.connect(self.points_picked)
            self.host.plan.setNavigation(self.cfg.navigation)
        from .update_check import UpdateCheck
        self.update_check = UpdateCheck(self)        # r28: the check by itself of the Windows package
        self.update_check.start()

    @Slot()
    def closeFile(self):
        self.settings.flushPending()
        if self.root is not None:
            self.host.shell.fileOpenRequested.emit(False)

    def show_file(self, section='open'):
        self.files.selectSection(section)
        self.files.refresh()
        if self.root is not None:
            self.host.shell.fileOpenRequested.emit(True)

    def section_changed(self):
        section = self.files.section
        if section.startswith('preferences'):
            site = self.session.project.site
            self.settings.site = (site.lat, site.lon)
            self.settings.metadataChanged.emit()
            self.settings.showSection(section.partition(':')[2] or 'appearance')
        elif section in ('new', 'registry'):
            self.dialogs.open(section)

    # R537 (Daniel 07/11/2026: «da rendere più chiara l'esecuzione del salvataggio quando premo Ctrl+S»), study 38:
    # as Office and Blender, in the status bar. Past 300 ms «Saving name…» (a quick save does not flash), at the end
    # «Saved at 02:41» for a few seconds, fading; an error stays, with the reason and what to do, until closed.
    WAIT_MS = 300
    DONE_MS = 4000

    def work_started(self, kind, name):
        token = self._work_token = object()
        text = (_('Saving {file}…') if kind == 'save' else _('Opening {file}…')).format(file=name)

        def say():
            if self._work_token is token and self.files.busy:
                self.host.shell.show_notice(text, 0, 'busy')
        QTimer.singleShot(self.WAIT_MS, self, say)

    def work_ended(self, kind, name, reason):
        self._work_token = None
        shell = self.host.shell
        if reason and kind == 'save':
            shell.show_notice(_('{file} is not saved: {reason}. Save it elsewhere with «Save as…» or free the folder '
                                'and try again.').format(file=name, reason=reason), 0, 'error')
        elif reason:
            shell.show_notice(_('{file} could not be opened: {error}').format(file=name, error=reason), 0, 'error-open')
        elif kind == 'open':
            shell.show_notice(_('Opened: {name}').format(name=name), self.DONE_MS, 'done')
        elif shell.noticeKind == 'busy':
            shell.show_notice('', 1, '')

    def work_saved(self, path):
        """Every save of the window ends here, in the background or not (the confirmation before quitting)."""
        self._work_token = None
        self.host.shell.show_notice(_('Saved at {time}: {file}').format(
            time=datetime.now().strftime('%H:%M'), file=Path(path).name), self.DONE_MS, 'done')

    def project_opened(self, _path):
        self.dismissDialog()
        self.closeFile()
        self.host.bridge.stateChanged.emit()

    def dialog_changed(self):
        if self.root is not None and self.dialogs.kind == 'site' and not self._dialog_visible:
            self._dialog_visible = True
            self.changed.emit()

    def shortcuts_changed(self, bindings):
        self.settings.refresh()
        self.settings_changed('shortcuts', bindings)

    def settings_changed(self, key, _value):
        if self.root is not None:
            # R23 F6 (docs/studio/39): asked of the window with the shell's signals (Workbench.qml applies them); Meridio's
            # settings reach him through assistant_part (layerSettings: the old `layer` here was gone since r21-f6c)
            if key == 'toolbar':
                self.host.shell.toolbarModeRequested.emit({'text': 'under', 'beside': 'beside', 'icons': 'icons'}.get(self.cfg.toolbar, 'auto'))
            elif key == 'toolbar_place':
                self.host.shell.toolbarPositionRequested.emit(self.cfg.toolbar_place)
            elif key == 'menu_bar':
                self.host.shell.menuBarRequested.emit(bool(self.cfg.menu_bar), None)
            elif key == 'shortcuts':
                self.host.shell.set_bindings(self.cfg.shortcuts)
        if self.root is not None and key in ('navigation', 'orbit', 'pivot', 'pivot_hint'):
            scene = self.host.parts.controllers.get('sceneControls')
            if scene is not None:                       # the 3D view binds sceneControls (View3DHost.qml)
                scene.configure()
        if key == 'navigation' and self.host.plan is not None:
            self.host.plan.setNavigation(self.cfg.navigation)
        if key in ('report_profiles', 'report_profile'):
            self.report.refresh()
        if key == 'memory_mode':                       # R548: at once for this process and what it starts next
            from meridiana import resources
            resources.configure(self.cfg.memory_mode)
            self.report.preload_changed()

    @Slot(str)
    def openDialog(self, kind):
        self.closeFile()
        self.dialogs.open(kind)
        self._dialog_visible = True
        self.changed.emit()

    @Slot()
    def dismissDialog(self):
        self._dialog_visible = False
        self.changed.emit()

    def file_command(self, command):
        # Ctrl+S on a project with its file writes it where it is, as the Widgets window: no page, no question.
        # A write that fails opens the page, where its error is said.
        # R537: on a thread of its own, its end and its errors told in the status bar (work_ended), the page stays shut.
        if command == 'save' and self.files.session.path is not None:
            self.files.write()
            return
        # Keep the confirmation and native picker owned by File visible.
        self.show_file('save' if command.startswith('save') else 'open')
        self.files.request(command)

    @Slot(str)
    def dispatch(self, command):
        kinds = {'import_ifc': 'ifc', 'import_pvsyst': 'pvsyst', 'carport': 'canopy',
                 'canopy_layout': 'canopy-layout', 'building_template': 'template',
                 'shortcuts': 'shortcuts', 'about': 'about', 'report_bug': 'report_bug', 'check_updates': 'update', 'update': 'update', 'site': 'site'}
        if command in kinds:
            self.openDialog(kinds[command])
        elif command in ('new', 'open', 'save', 'save_as', 'save_revision'):
            self.file_command(command)
        elif command == 'report_logo':
            self.logoRequested.emit()
        elif command in ('preferences', 'report_profile') or command.startswith('settings:'):
            section = command.partition(':')[2] if ':' in command else 'appearance' if command == 'preferences' else 'report'
            self.show_file('preferences:' + section)
        elif command.startswith('catalog_'):
            kinds = {'catalog_module': 'modules', 'catalog_inverter': 'inverters', 'catalog_microinverters': 'microinverters',
                     'catalog_optimizers': 'optimizers', 'catalog_battery': 'batteries'}
            self.closeFile()
            self.catalog.setKind(kinds[command])
            self._catalog_visible = True
            self.changed.emit()
        elif command == 'copy_notes':
            self.actions.copyNotes()
        elif command == 'export_ifc':
            self.actions.exportIfcRequested.emit()
        elif command == 'export_dxf':
            self.actions.exportDxfRequested.emit()
        elif command == 'export_report':
            self.closeFile()
            self.root.showPhase('report')
            if self.report.ready:
                self.exportRequested.emit()
            else:
                self.report.requestPreview()
        elif command == 'quit':
            self.root.close()
        else:
            self.closeFile()
            if not self.host.shell.trigger(command):
                self.show_file('help')
                self.files._fail(_('This command is provided by the application window: {command}').format(command=command))

    def model_imported(self, ids):
        """R454: the model laid by hand or by coordinates, selected: M and R move and turn it, Ctrl+Z takes it back."""
        if not ids:
            return
        self.session.select('building', ids[0])
        if self.root is not None:
            shell = self.host.shell
            shell._notice = _('The model is laid: M moves it, R turns it, Ctrl+Z takes back the whole import.')
            shell.changed.emit()

    def model_placed(self):
        """The model has just come in, selected: the plan shows it and Move is in hand. Nothing is asked: it stands at the
        middle of the plan until it is moved, and Ctrl+Z takes it all back."""
        self.dismissDialog()
        if self.root is not None:
            self.root.showPhase('model')
            shell = self.host.shell
            shell.trigger('tool_move')
            shell.trigger('fit')
            shell._notice = _('The model is at the middle of the plan: drag it where it belongs, R turns it, Ctrl+Z takes '
                              'it back.')
            shell.changed.emit()

    def install_update(self, path):
        self.dismissDialog()
        def start():
            try:
                subprocess.Popen(updates.installer_command(Path(path), restart=True), close_fds=True)
            except OSError as error:
                self.files._fail(_('Cannot start the installer: {error}').format(error=error.strerror or error))
            else:
                # r28: the project is saved (_guard); the window goes at once, so that Setup finds no file of the
                # program in use, and Setup starts it again when it has finished (/RESTARTAPP=1)
                self.closeFile()
                from PySide6.QtGui import QGuiApplication
                QTimer.singleShot(0, QGuiApplication.quit)
        self.show_file('save')
        self.files._guard('callback', start)

    @Slot(str)
    def putReportLogo(self, value):
        from .files import local_path
        from meridiana.ui.report import logo_problem
        path = local_path(value)
        problem = logo_problem(path)
        if problem:
            self.show_file('preferences:report')
            self.settings._fail(problem)
            return
        profiles = self.cfg.report_profiles
        signed = reports.signature(self.session.project, profiles, self.cfg.report_profile)
        target = signed['name'] if signed['profile'] else reports.default_profile(profiles, self.cfg.report_profile)
        made = not profiles
        if made:
            target = _('My profile')
            if not self.settings.setValue('report_profiles', [dict.fromkeys(reports.PROFILE_KEYS, '') | {'name': target}]):
                return
            self.settings.setValue('report_profile', target)
        elif not target:
            self.show_file('preferences:report')
            self.settings._fail(_('Several profiles and none signs this project: choose one in «Signed by», then the logo.'))
            return
        index = next(i for i, profile in enumerate(self.cfg.report_profiles) if profile['name'] == target)
        self.settings.editProfile(index, 'logo', str(path))
        if made:
            self.show_file('preferences:report')

    def place(self, kind, data):
        self.root.showPhase('model')
        plan = self.host.plan
        if plan is None:
            self.files._fail(_('The plan is not available.'))
            self.show_file('open')
        elif kind == 'canopy':
            plan.activateTool('canopy', {'spec': data})
        elif kind == 'ifc':
            if not getattr(self, '_placing_wired', False):
                plan.modelImported.connect(self.model_imported)
                self._placing_wired = True
            plan.placeModel(data['plan'], data.get('place'), data.get('follow', True), data.get('name', ''))
        elif kind == 'template':
            self._template = data
            plan.pickPoints('file-template', [_('Click where the South-West corner of the building goes; Esc gives up')])

    def points_picked(self, purpose, points):
        if purpose != 'file-template' or not points or self._template is None:
            return
        pending, self._template = self._template, None
        project = self.session.project
        building = model.Building(id=project.new_id('b'), name=_('Building {n}').format(n=len(project.buildings) + 1),
                                  footprint=templates.placed(pending['ring'], points[0], pending['turn']), height=6.0)
        self.session.edit(_('Building from a template'), lambda p: p.buildings.append(building))
        self.session.select('building', building.id)

    def close(self):
        if self._closed:
            return
        self._closed = True
        if getattr(self, 'update_check', None) is not None:
            self.update_check.close()
        self.catalog.dispose()
        for provider in (self.actions, self.settings, self.report, self.dialogs, self.files):
            provider.close()
        self.registry.close()


def install(engine, session, cache, window):
    controller = FilePart(engine, session, cache, window)
    commands = ('new', 'open', 'save', 'save_as', 'save_revision', 'preferences', 'import_ifc', 'import_pvsyst',
                'shortcuts', 'check_updates', 'report_profile', 'report_logo', 'carport', 'canopy_layout',
                'building_template', 'export_report', 'about', 'report_bug', 'copy_notes', 'export_ifc', 'export_dxf')
    return Part('files', sources={'file': QML / 'File/WorkbenchFile.qml', 'report': QML / 'Report/WorkbenchReport.qml',
                                    'reportInspector': QML / 'Report/WorkbenchReportInspector.qml'},
                controllers={'files': controller.files, 'settings': controller.settings,
                             'dialogs': controller.dialogs, 'report': controller.report, 'filePart': controller},
                commands={name: lambda cmd=name: controller.dispatch(cmd) for name in commands},
                bind=controller.bind, close=controller.close)
