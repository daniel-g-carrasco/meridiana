"""Window commands with cancellable, isolated work and same-window dialogs."""
import copy
import pickle
import platform
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, Property, QProcess, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication

from meridiana import __version__, compare, dxf_export, feedback
from meridiana.i18n import _


class ShellTasks(QObject):
    changed = Signal()
    showDialog = Signal(str)
    exportRequested = Signal(str)
    variantDialog = Signal(str, str)

    def __init__(self, host):
        super().__init__(host.engine)
        self.host = host
        self.process = None
        self.temporary = None
        self._busy, self._message, self._rows, self._columns = False, '', [], []
        self.figures = []
        self.names = []
        self._job = ''
        self._closed = False
        self._export_stage = self._export_target = None

    busy = Property(bool, lambda self: self._busy, notify=changed)
    message = Property(str, lambda self: self._message, notify=changed)
    rows = Property('QVariantList', lambda self: self._rows, notify=changed)
    columns = Property('QVariantList', lambda self: self._columns, notify=changed)
    labels = Property('QVariantMap', lambda self: {k: _(v).replace('&', '') for k, v in dict(
        compare='&Compare the variants…', close='Close', cancel='Cancel', copy='Copy the table',
        about='About Meridiana', feedback='Report a problem', title='Title', description='Description',
        openDraft='Open GitHub draft', copyDraft='Copy draft', environment='Include application and system versions',
        preview='Preview of the shared text',
        intro='Review this draft before sharing it. The browser opens a GitHub draft; you decide whether to submit it. Reports there are public.',
        csv='Export the hourly series', ifc='Export the model as IFC4',
        ifcAll='IFC4, the whole model (*.ifc)', ifcPlant='IFC4, the plant alone (*.ifc)',
        ifcOriginal="IFC, the plant added to the architect's model it came from (*.ifc)",
        newVariant='&New variant from this one…', renameVariant='&Rename the variant…', deleteVariant='&Delete a variant…',
        name='Name:', chooseVariant='Which variant? (to delete the one in hand, switch to another first)',
        apply='Apply',
    ).items()} | dxf_export.words(), constant=True)

    def bind(self):
        self.host.shell.variantRequested.connect(self.variantAction)
        if 'files' in self.host.parts.installed:
            self.host.shell.register_command('new_variant', lambda: self.variantAction('new'))
        for command, handler in {
            'compare_variants': self.compare,
            'fetch_pvgis': self.fetch,
            'export_csv': lambda: self.export('csv'),
            'export_ifc': lambda: self.export('ifc'),
            'export_dxf': lambda: self.export('dxf'),
            'about': lambda: self.showDialog.emit('about'),
            'report_bug': lambda: self.showDialog.emit('feedback'),
        }.items():
            if command in ('about', 'report_bug') and self.host.shell.available(command):
                continue
            self.host.shell.register_command(command, handler)

    @Slot(str)
    def variantAction(self, action):
        project = self.host.bridge.session.project
        if action == 'delete' and len(project.variants) == 1:
            self.tell(_('There is only the variant in hand: nothing to delete.'))
            self.showDialog.emit('message')
            return
        name = _('Variant {n}').format(n=len(project.variants)+1) if action == 'new' else project.current_variant()['name']
        self.variantDialog.emit(action, name)

    @Slot(str, str)
    def commitVariant(self, action, value):
        session = self.host.bridge.session
        value = value.strip()
        if not value:
            return
        if action == 'new':
            session.edit(_('New variant'), lambda p: p.add_variant(value))
        elif action == 'rename':
            session.edit(_('Rename the variant'), lambda p: p.current_variant().update(name=value))
        elif action == 'delete' and value != session.project.variant:
            session.edit(_('Delete a variant'), lambda p: p.remove_variant(value))

    @Slot(result=str)
    def about(self):
        return _('Photovoltaic design: map, building model, sun path, module layout and Italian standards.') + '\n\n' + __version__ + '\nGPL-3.0-or-later'

    def tell(self, message):
        self._message = message
        self.host.shell._notice = message
        self.host.shell.changed.emit()
        self.changed.emit()

    def compare(self):
        variants = self.host.bridge.session.project.variants
        self.names = [v['name'] for v in variants]
        self.figures, self._rows = [], []
        self._columns = [dict(title='', key='label', weight=2)] + [dict(title=n, key=str(i), numeric=True) for i, n in enumerate(self.names)]
        self.showDialog.emit('compare')
        self.start('compare')

    def export(self, kind):
        if kind == 'csv' and self.host.bridge.session.energy.get('sim') is None:
            self.tell(_('Compute the production first (the Production page): the series is its year.'))
            self.showDialog.emit('message')
            return
        self.exportRequested.emit(kind)

    @Slot(result='QVariantList')
    def dxfFrames(self):
        return dxf_export.frame_choices(self.host.bridge.session.project)

    @Property('QVariantList', constant=True)
    def dxfParts(self):
        return dxf_export.part_list()

    @Slot(str, str, 'QVariantList')
    def exportDxf(self, url, frame, parts):
        import json
        self.exportTo('dxf', url, json.dumps({'frame': frame, 'parts': list(parts)}))

    @Slot(str, str)
    @Slot(str, str, str)
    def exportTo(self, kind, url, what='all'):
        path = Path(QUrl(url).toLocalFile() if url.startswith('file:') else url)
        if kind not in ('csv', 'ifc', 'dxf'):
            raise ValueError(kind)
        if path.suffix.lower() != '.' + kind:
            path = path.with_suffix('.' + kind)
        # R453: the plant alone, for the federated model; R513: the plan's coordinates and parts, as JSON
        self._what = what if kind == 'dxf' else what if what in ('plant', 'original') else 'all'
        self.start(kind, str(path))

    def fetch(self):
        project = self.host.bridge.session.project
        if not project.online_allowed('pvgis', self.host.cfg.network_pvgis):
            self.tell(_('PVGIS is off in Settings > Privacy: computing with the weather already in the cache.'))
            self.showDialog.emit('message')
            return
        self.start('climate')

    def start(self, kind, target=''):
        if self._busy:
            self.tell(_('Computing…'))
            return
        self._job, self._busy = kind, True
        if kind in ('csv', 'ifc', 'dxf'):
            self._export_target = Path(target)
            try:
                with tempfile.NamedTemporaryFile(prefix='.'+self._export_target.name+'-', suffix='.part',
                                                 dir=self._export_target.parent, delete=False) as stream:
                    self._export_stage = Path(stream.name)
                target = str(self._export_stage)
            except OSError as error:
                self._busy = False
                self.tell(str(error))
                return
        session = self.host.bridge.session
        self._generation = session.generation
        self.temporary = tempfile.TemporaryDirectory(prefix='shell-job-', dir=self.host.bridge.cache)
        folder = Path(self.temporary.name)
        payload = (kind, copy.deepcopy(session.project), session.known_layouts(), session.energy,
                   self.host.bridge.cache, target, getattr(self, '_what', 'all'))
        (folder / 'input.bin').write_bytes(pickle.dumps(payload, protocol=5))
        self.process = QProcess(self)
        self.process.setProgram(sys.executable)
        self.process.setArguments(['-m', 'meridiana.quick.backend.shell_tasks', str(folder)])
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.process_error)
        self.tell(_('Computing…'))
        self.process.start()

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self._busy = False
            self.tell(self.process.errorString())
            self.temporary.cleanup()
            self.discard_stage()

    def finished(self, code, _status):
        if self._closed or not self._busy:
            return
        self._busy = False
        path = Path(self.temporary.name) / 'output.bin'
        result = pickle.loads(path.read_bytes()) if code == 0 and path.exists() else {
            'error': bytes(self.process.readAllStandardError()).decode('utf-8', 'replace') or str(code)}
        self.temporary.cleanup()
        if 'error' in result:
            self.discard_stage()
            self.tell(result['error'])
            return
        if self._job == 'compare':
            self.figures = result['figures']
            self._rows = [dict(label=label, best=compare.best(self.figures, key, better), **{str(i): s.get('error') or compare.cell(s, key, digits)
                                             for i, s in enumerate(self.figures)})
                          for key, label, digits, better in compare.rows()]
            self.tell(_('All the variants are computed.'))
        elif self._job == 'climate':
            session = self.host.bridge.session
            if session.generation == self._generation:
                session.edit(_('Weather from PVGIS'), lambda p: setattr(p, 'climate', result['climate']))
                self.host.bridge.recompute()
            self.tell(_('Compute'))
        else:
            try:
                self._export_stage.replace(self._export_target)
                self.tell(str(self._export_target))
            except OSError as error:
                self.tell(str(error))
            finally:
                self.discard_stage()

    def discard_stage(self):
        if self._export_stage:
            self._export_stage.unlink(missing_ok=True)
            self._export_stage = None

    @Slot()
    def cancel(self):
        self._busy = False
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(500)
        if self.temporary:
            self.temporary.cleanup()
        self.discard_stage()
        self.changed.emit()

    @Slot()
    def copyComparison(self):
        QGuiApplication.clipboard().setText(compare.table_text(self.names, self.figures))

    def draft(self, title, description, environment):
        return feedback.Draft(title, description, __version__, platform.system(), platform.python_version(),
                              include_environment=environment)

    @Slot(str, str, bool, result=str)
    def preview(self, title, description, environment):
        return self.draft(title, description, environment).body()

    @Slot(str, str, bool, bool)
    def shareDraft(self, title, description, environment, browser):
        draft = self.draft(title, description, environment)
        if browser:
            try:
                QDesktopServices.openUrl(QUrl(draft.issue_url()))
            except ValueError as error:
                self.tell(str(error))
        else:
            QGuiApplication.clipboard().setText(draft.body())

    def close(self):
        self._closed = True
        self.cancel()


def work(folder):
    from meridiana import atomic, i18n, jobs
    i18n.setup_as_window()
    kind, project, known, energy, cache, target, *more = pickle.loads((folder / 'input.bin').read_bytes())
    what = more[0] if more else 'all'
    try:
        if kind == 'compare':
            from meridiana.session import ProjectSession
            session = ProjectSession(project)
            result = {'figures': [session.variant_figures(project.to_json(), v['id'], cache) for v in project.variants]}
        elif kind == 'climate':
            from meridiana.energy import meteo
            lat, lon = project.site.lat, project.site.lon
            meteo.typical_year(lat, lon, cache, refresh=True)
            meteo.horizon(lat, lon, cache, refresh=True)
            result = {'climate': {name: atomic.read_json(meteo._cache_file(cache, name, lat, lon))[0] for name in ('tmy', 'horizon')}}
        else:
            # Export into the private job directory first. A cancelled export
            # never leaves a partial file beside the user's project.
            temporary = folder / ('export.' + kind)
            results = jobs.layout_of(project, known)[0]
            if kind == 'csv':
                from meridiana.ui.report import write_register_csv
                write_register_csv(project, {**energy, 'results': results}, temporary)
            elif kind == 'dxf':
                import json
                from meridiana import dxf_export
                asked = json.loads(what) if what.startswith('{') else {}
                dxf_export.export_project(project, temporary, known, asked.get('frame', 'local'),
                                          tuple(asked.get('parts') or dxf_export.PARTS))
            else:
                from meridiana import ifc_export
                from meridiana.energy import plant
                system = plant.build(project, results, check=False)
                strings = {(sf, key): s.label for s in system.strings for sf, key, _c in s.modules}
                if what == 'original':          # r22-ifc: the plant added to the architect's own file
                    from meridiana import ifc_append
                    ifc_append.append(project, results, ifc_append.original_of(project), temporary, strings, system)
                else:
                    ifc_export.export(project, results, temporary, strings=strings, what=what, plant=system)
            # The owner created this unique staging file and removes it even
            # when this process is killed during the copy. It alone commits it.
            import shutil
            shutil.copyfile(temporary, target)
            result = {'path': target}
    except Exception as error:
        result = {'error': f'{type(error).__name__}: {error}'}
    (folder / 'output.bin').write_bytes(pickle.dumps(result, protocol=5))


if __name__ == '__main__':
    work(Path(sys.argv[1]))
