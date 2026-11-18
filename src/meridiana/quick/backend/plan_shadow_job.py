"""Latest-only shadow projection off the GUI thread."""
from __future__ import annotations

import copy

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal

from .plan_shadows import shadow_paths


class ShadowSignals(QObject):
    done = Signal(int, object, str)


class ShadowTask(QRunnable):
    def __init__(self, serial, project, options):
        super().__init__()
        self.serial, self.project, self.options = serial, project, options
        self.signals = ShadowSignals()

    def run(self):
        try:
            self.signals.done.emit(self.serial, shadow_paths(self.project, **self.options), '')
        except Exception as error:  # Thread boundary: delivered visibly by the controller.
            self.signals.done.emit(self.serial, [], str(error))


class ShadowScheduler(QObject):
    ready = Signal(object)
    failed = Signal(str)

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session, self.serial, self.closed = session, 0, False
        self.tasks, self.options = {}, None
        self.timer = QTimer(self, singleShot=True, interval=60)
        self.timer.timeout.connect(self.launch)
        self.pool = QThreadPool.globalInstance()

    def request(self, options):
        self.serial += 1
        self.options = dict(options) if options is not None else None
        self.timer.stop()
        if self.options is None:
            self.ready.emit([])
        else:
            self.timer.start()

    def launch(self):
        if self.closed or self.options is None:
            return
        task = ShadowTask(self.serial, copy.deepcopy(self.session.project), self.options)
        task.signals.done.connect(self.accept)
        self.tasks[self.serial] = task
        self.pool.start(task)

    def accept(self, serial, paths, error):
        self.tasks.pop(serial, None)
        if not self.closed and serial == self.serial:
            if error:
                self.failed.emit(error)
            else:
                self.ready.emit(paths)

    def close(self):
        self.closed = True
        self.timer.stop()
        if self.tasks:
            self.pool.waitForDone()
