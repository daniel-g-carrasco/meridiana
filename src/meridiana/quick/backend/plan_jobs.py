"""Asynchronous layout scheduling for a standalone plan, using the shared core jobs."""
from __future__ import annotations

import copy

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal

from meridiana import jobs
from meridiana.session import needs_layout


class LayoutSignals(QObject):
    done = Signal(int, object, object, str)


class LayoutTask(QRunnable):
    def __init__(self, generation, project, known):
        super().__init__()
        self.generation, self.project, self.known = generation, project, known
        self.signals = LayoutSignals()

    def run(self):
        try:
            results, keys, _laid = jobs.layout_of(self.project, self.known)
            self.signals.done.emit(self.generation, results, keys, '')
        except Exception as error:  # Worker boundary; the controller displays the diagnostic.
            self.signals.done.emit(self.generation, {}, {}, str(error))


class LayoutScheduler(QObject):
    changed = Signal()
    failed = Signal(str)

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.tasks = {}
        self.closed = False
        self.pool = QThreadPool.globalInstance()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.launch)
        session.subscribe(self.on_change)

    @property
    def busy(self):
        return bool(self.tasks) or self.timer.isActive()

    def on_change(self, topics):
        if not self.closed and needs_layout(topics):
            self.request()

    def request(self):
        self.session.generation += 1
        self.timer.start()
        self.changed.emit()

    def launch(self):
        serial = self.session.generation
        task = LayoutTask(serial, copy.deepcopy(self.session.project), self.session.known_layouts())
        task.signals.done.connect(self.accept)
        self.tasks[serial] = task
        self.pool.start(task)

    def accept(self, serial, results, keys, error):
        self.tasks.pop(serial, None)
        if self.closed:
            return
        if serial == self.session.generation:
            if error:
                self.failed.emit(error)
            else:
                self.session.layout_done(serial, results, keys)
        self.changed.emit()

    def close(self):
        self.closed = True
        self.timer.stop()
        if self.on_change in self.session.listeners:
            self.session.listeners.remove(self.on_change)
        if self.tasks:
            self.pool.waitForDone()
