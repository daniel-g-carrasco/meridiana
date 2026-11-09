"""Layout-only scheduling for the isolated Quick 3D window, using the shared session.

The application shell already owns its calculation scheduler. Install this only
in a standalone scene host, then call begin() after connecting error reporting.
"""
from __future__ import annotations

import copy

from PySide6.QtCore import QObject, Property, QRunnable, QThreadPool, QTimer, Qt, Signal, Slot

from meridiana import jobs
from meridiana.session import ProjectSession, needs_layout


class _LayoutSignals(QObject):
    finished = Signal(int, object, object, str)


class _LayoutJob(QRunnable):
    """One copied project and a private cache mapping, never the live session."""

    def __init__(self, generation, project, known):
        super().__init__()
        self.generation, self.project, self.known = generation, project, known
        # No parent tied to the window: run() retains the signal object even if
        # the host closes or its QObject receiver is destroyed during work.
        self.signals = _LayoutSignals()

    def run(self):
        signals = self.signals
        try:
            results, keys, _ = jobs.layout_of(self.project, self.known)
            failure = "\n".join(f"{sid}: {result}" for sid, result in results.items()
                                if isinstance(result, Exception))
        except Exception as error:  # The worker boundary reports its failure to the host.
            results, keys, failure = None, None, str(error)
        signals.finished.emit(self.generation, results, keys, failure)


class SceneLayouts(QObject):
    """Debounce layout changes, reject stale snapshots and return on the GUI thread.

    Construction subscribes without launching work. begin() is idempotent;
    request() explicitly schedules or reschedules a layout. close() is idempotent
    and never waits for a worker. All public methods are called on this object's
    thread, the same thread that owns and edits the ProjectSession.
    """

    busyChanged = Signal()
    error = Signal(str)

    def __init__(self, session: ProjectSession, parent=None):
        super().__init__(parent)
        self.session = session
        self._started = False
        self._closed = False
        self._busy = False
        self._pending = False
        self._job = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self._launch)
        self.session.subscribe(self._changed)

    @Property(bool, notify=busyChanged)
    def busy(self):
        return self._busy

    def _set_busy(self, busy):
        if self._busy != busy:
            self._busy = busy
            self.busyChanged.emit()

    @Slot()
    def begin(self):
        if not self._started and not self._closed:
            self.request()

    @Slot()
    def request(self):
        if self._closed:
            return
        self._started = True
        # Invalidate immediately, before the debounce: an older worker must not
        # publish a layout during the pause after a new geometry edit.
        self.session.generation += 1
        self._pending = True
        self._timer.start()
        self._set_busy(True)

    def _changed(self, topics):
        if self._closed or not self._started:
            return
        if "file" in topics or needs_layout(topics) or topics == {"restored"}:
            self.request()

    @Slot()
    def _launch(self):
        if self._closed or not self._pending or self._job is not None:
            return
        self._pending = False
        try:
            project = copy.deepcopy(self.session.project)
            # Results in this cache are read-only and jobs.layout_of returns an
            # unchanged result by identity. Copying the mapping isolates edits
            # while preserving that cache contract and avoiding array copies.
            known = dict(self.session.known_layouts())
            job = _LayoutJob(self.session.generation, project, known)
        except Exception as failure:  # Snapshot failures must also leave busy state.
            self._set_busy(False)
            self.error.emit(str(failure))
            return
        self._job = job
        job.signals.finished.connect(self._finished, Qt.ConnectionType.QueuedConnection)
        QThreadPool.globalInstance().start(job)

    @Slot(int, object, object, str)
    def _finished(self, generation, results, keys, failure):
        self._job = None
        if self._closed:
            return
        if generation == self.session.generation:
            if results is not None:
                self.session.layout_done(generation, results, keys)
            if failure:
                self.error.emit(failure)
        if self._pending:
            if not self._timer.isActive():
                # A worker may have outlasted the debounce. Run only the latest
                # snapshot now; intermediate edits never form a queue of jobs.
                self._launch()
        else:
            self._set_busy(False)

    @Slot()
    def close(self):
        if self._closed:
            return
        self._closed = True
        self._timer.stop()
        self._pending = False
        if self._changed in self.session.listeners:
            self.session.listeners.remove(self._changed)
        self._set_busy(False)
        # An active QRunnable completes with its copied data. The queued QObject
        # slot ignores it after close; Qt disconnects it if the host is deleted.
