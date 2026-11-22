"""The index of the projects registered (R151), kept up to date by the Qt Quick window: what MainWindow._refresh_index
did in the Widgets one. A scan in the background when the window starts, after a project is opened or saved and after
a change in Clients and jobs; Meridio and the searches of the archive read it (registry.list_index). The scan itself is
app/project/project_index.refresh, without Qt; here only the job, one at a time, and what to say when it fails."""
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from meridiana.app.platform import log
from meridiana.app.project import project_index
from meridiana.i18n import _


class _Signals(QObject):
    done = Signal(int, object)          # the generation, the error (None when it went well)


class _Scan(QRunnable):
    """Scan and write the index with the worker's own SQLite connections."""

    def __init__(self, generation, folders, database):
        super().__init__()
        self.generation, self.folders, self.database = generation, folders, database
        self.signals = _Signals()

    def run(self):
        try:
            project_index.refresh(self.database, self.folders)
        except Exception as error:  # noqa: BLE001  the worker's boundary: the window says what failed
            failure = error
        else:
            failure = None
        try:
            self.signals.done.emit(self.generation, failure)
        except RuntimeError as error:           # the window was closed while the scan ran
            if "deleted" not in str(error):
                raise


class IndexRefresh(QObject):
    """One scan at a time; asked again while one runs, it runs once more at its end with what is registered then (a
    slower, older result never comes after a newer one). `tell(text)` says a failure in the status bar."""

    def __init__(self, registry, tell, parent=None):
        super().__init__(parent)
        self.registry, self.tell = registry, tell
        self.generation = 0
        self.job = None
        self._closed = False
        self.pool = QThreadPool(self)          # its own: closing waits for its scan, not for the window's other jobs
        self.pool.setMaxThreadCount(1)

    @property
    def running(self):
        return self.job is not None

    def refresh(self):
        if self._closed or self.registry.connection is None:
            return
        self.generation += 1
        if self.job is not None:
            return                              # coalesced: _done starts the next one
        folders = project_index.sources(self.registry)
        if not folders and not self.registry.list_index():
            return                              # nothing registered, nothing indexed: no job for nothing
        job = self.job = _Scan(self.generation, folders, self.registry.path)
        job.signals.done.connect(self._done)
        self.pool.start(job)

    def _done(self, generation, error):
        self.job = None
        if self._closed or self.registry.connection is None:
            return
        if generation != self.generation:
            self.refresh()
            return
        if error is not None:
            log.complain('project index', error)
            self.tell(_('The project index could not be updated: {error}').format(error=error))

    def close(self, wait_ms=5000):
        """No more scans; the one running may end its transaction (the profile may be removed right after)."""
        self._closed = True
        self.pool.waitForDone(wait_ms)
