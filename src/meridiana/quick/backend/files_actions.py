"""File exports and the editable support draft, using the existing core services."""
from pathlib import Path
import platform

from PySide6.QtCore import QObject, Property, QThreadPool, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication

from meridiana import __version__, dxf_export, feedback, rules
from meridiana.i18n import _


class FileActions(QObject):
    changed = Signal()
    exportIfcRequested = Signal()
    exportDxfRequested = Signal()

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.job = None
        self._closed = False
        self.values = dict(title='', description='', diagnostics='', environment=True, context=False, include_diagnostics=False)
        self._status = ''

    @Property('QVariantMap', constant=True)
    def labels(self):
        return {key: _(value) for key, value in dict(
            intro='Review this draft before sharing it. The browser opens a GitHub draft; you decide whether to submit it. Reports there are public.',
            title='Title', description='Description', environment='Include application and system versions',
            context='Include the current phase and object counts', diagnostics='Include a selected diagnostic excerpt',
            preview='Preview of the shared text', copy='Copy draft', save='Save draft…', open='Open GitHub draft',
            note='Project files, paths, logs and the conversation are not attached. You can add selected files yourself on GitHub.',
            cancel='Cancel', exporting='Export the model as IFC4',
            ifcAll='IFC4, the whole model (*.ifc)', ifcPlant='IFC4, the plant alone (*.ifc)',
            ifcOriginal="IFC, the plant added to the architect's model it came from (*.ifc)").items()} | dxf_export.words()

    @Property(str, notify=changed)
    def status(self):
        return self._status

    @Property(bool, notify=changed)
    def busy(self):
        return self.job is not None

    def draft(self):
        v, p = self.values, self.owner.session.project
        context = 'Phase: ' + str(self.owner.root.property('phase')) + '\nSubfields: ' + str(len(p.subfields))
        return feedback.Draft(v['title'], v['description'], __version__, platform.system(), platform.python_version(),
                              context if v['context'] else '', v['diagnostics'] if v['include_diagnostics'] else '',
                              include_environment=v['environment'])

    @Property(str, notify=changed)
    def preview(self):
        return self.draft().body()

    @Property(bool, notify=changed)
    def canShare(self):
        return bool(self.values['title'].strip() and self.values['description'].strip())

    @Slot(str, 'QVariant')
    def setDraft(self, key, value):
        if key in self.values:
            self.values[key] = str(value)[:180] if key == 'title' else value
            self.changed.emit()

    @Slot()
    def copyDraft(self):
        QGuiApplication.clipboard().setText(self.preview)

    @Slot(str)
    def saveDraft(self, url):
        path = QUrl(url).toLocalFile() if url.startswith('file:') else url
        try:
            with Path(path).open('x', encoding='utf-8') as stream:
                stream.write(self.values['title'] + '\n\n' + self.preview)
        except OSError as error:
            self._status = _('The draft could not be saved: {error}').format(error=error)
            self.changed.emit()

    @Slot()
    def openDraft(self):
        try:
            url = self.draft().issue_url()
        except ValueError:
            self._status = _('This draft is too long for a browser link. Copy or save it, then paste it into a new issue.')
        else:
            if not QDesktopServices.openUrl(QUrl(url)):
                self._status = _('The browser could not be opened. Copy or save the draft to keep it.')
        self.changed.emit()

    def copyNotes(self):
        session = self.owner.session
        QGuiApplication.clipboard().setText(rules.notes_text(rules.facts(session.project, session.results, session.energy)))

    @Slot(str)
    @Slot(str, str)
    def exportIfc(self, url, what='all'):
        if self.job is not None:
            return
        from meridiana.ui.window import ExportIfcJob
        path = QUrl(url).toLocalFile() if url.startswith('file:') else url
        if not path.lower().endswith('.ifc'):
            path += '.ifc'
        session = self.owner.session
        self.job = ExportIfcJob(session.project.to_json(), session.known_layouts(), Path(path), session.state_key(),
                                what if what in ('plant', 'original') else 'all')
        self.job.signals.step.connect(self._export_step)
        self.job.signals.done.connect(self._export_done)
        self._status = _('IFC4: {file}').format(file=Path(path).name)
        self.changed.emit()
        QThreadPool.globalInstance().start(self.job)

    @Slot(result='QVariantList')
    def dxfFrames(self):
        return dxf_export.frame_choices(self.owner.session.project)

    @Property('QVariantList', constant=True)
    def dxfParts(self):
        return dxf_export.part_list()

    @Slot(str, str, 'QVariantList')
    def exportDxf(self, url, frame, parts):
        """The plan as a DXF (R513), in a job of the pool as the IFC: the same bar of words and Cancel."""
        if self.job is not None:
            return
        if not dxf_export.available():
            self._status = _('The DXF export needs ezdxf (MIT), which is not installed: «pip install ezdxf» in '
                             "Meridiana's Python.")
            self.changed.emit()
            return
        from meridiana.ui.window import ExportDxfJob
        path = QUrl(url).toLocalFile() if url.startswith('file:') else url
        if not path.lower().endswith('.dxf'):
            path += '.dxf'
        session = self.owner.session
        self.job = ExportDxfJob(session.project.to_json(), session.known_layouts(), Path(path), session.state_key(),
                                frame if frame in dxf_export.FRAMES else 'local',
                                tuple(p for p in parts if p in dxf_export.PARTS) or dxf_export.PARTS)
        self.job.signals.step.connect(self._export_step)
        self.job.signals.done.connect(self._export_done)
        self._status = _('DXF: {file}').format(file=Path(path).name)
        self.changed.emit()
        QThreadPool.globalInstance().start(self.job)

    @Slot(float, str)
    def _export_step(self, _fraction, what):
        if not self._closed:
            kind = 'DXF' if self.job is not None and self.job.path.suffix.lower() == '.dxf' else 'IFC4'
            self._status = _('{kind}: {what}').format(kind=kind, what=what)
            self.changed.emit()

    @Slot(object)
    def _export_done(self, result):
        job, self.job = self.job, None
        if self._closed:
            return
        if isinstance(result, Exception):
            self._status = _('The model could not be written: {error}').format(error=result)
        elif result is None:
            self._status = (_('DXF export stopped: nothing written.') if job.path.suffix.lower() == '.dxf' else
                            _('IFC export stopped: nothing written.'))
        else:
            kind = 'DXF' if job.path.suffix.lower() == '.dxf' else 'IFC4'
            self._status = _('{kind}: {file}').format(kind=kind, file=job.path)
        self.changed.emit()

    @Slot()
    def cancelExport(self):
        if self.job is not None:
            self.job.interrupt()

    def close(self):
        self._closed = True
        self.cancelExport()
