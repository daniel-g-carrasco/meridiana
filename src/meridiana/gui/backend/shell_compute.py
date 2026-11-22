"""Cancellable computation for the workbench, isolated from the UI's lifetime.

The internal worker receives a trusted snapshot written by this process, never a
user-supplied pickle. The core and its output types are the same as in Bridge.
A QProcess can be stopped even during a NumPy/native call without killing a Qt
thread or waiting for the entire simulated year at application shutdown.
"""
import os
import pickle
import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QProcess, QTimer, Signal, Slot

from meridiana.app.platform import log
from meridiana.app import year_key, year_read
from meridiana.data import frames, year_store
from meridiana.core.compute import resources
from meridiana.i18n import _

from meridiana.gui.bridge import Bridge

WORKER = 'meridiana.gui.backend.shell_compute'    # this module, the computation's process (`-m`): a name, never put together
UNREADABLE = (OSError, EOFError, ValueError, TypeError, pickle.UnpicklingError, AttributeError, ImportError, MemoryError)


def frame_of(path):
    """The object of a frame the year's process wrote (data/frames.py), read here: the trials' one process for each
    year (Worker); the window's years read theirs on a thread (LiveWorker)."""
    blob = frames.read(path)
    if blob is None:
        raise ValueError(f'{Path(path).name} is not a frame')
    return frames.loads(blob)


class Worker(QObject):
    """One computation in one process: `spare` is a process already warm, or None to start one cold. `photo` is the
    session's (session.photo()): pickled as it is, made a project in the process (worker)."""
    layout = Signal(int, object, object)
    step = Signal(int, float, int, str)
    finished = Signal(int, object, object, object)

    def __init__(self, generation, photo, known, cache, parent, spare=None, fingerprint='', year=True, options=None):
        super().__init__(parent)
        self.generation = generation
        self.year = year
        self.options = dict(options or {})      # R461 {'workers': n, 'low': True}: a year in the background
        self.cancelled = False
        self.delivered = False
        self.buffer = b''
        self.temporary = tempfile.TemporaryDirectory(prefix='compute-', dir=cache, ignore_cleanup_errors=True)
        self.folder = Path(self.temporary.name)
        (self.folder / 'input.bin').write_bytes(pickle.dumps((photo, known, Path(cache), fingerprint, year, self.options),
                                                                 protocol=5))
        self.process = spare if spare is not None else start_process(self)
        self.process.setParent(self)
        self.process.readyReadStandardOutput.connect(self.read)
        self.process.finished.connect(self.done)
        self.process.errorOccurred.connect(self.error)

    def start(self):
        # Waits in stdin if the process is still importing; the pipe closed, it ends with this program.
        self.process.write((str(self.folder) + '\n').encode('utf-8'))
        self.process.closeWriteChannel()

    def read(self):
        self.buffer += bytes(self.process.readAllStandardOutput())
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            if self.cancelled:
                continue
            if line.strip() == b'layout':
                results, keys = frame_of(self.folder / 'layout.bin')
                self.layout.emit(self.generation, results, keys)
            elif line.startswith(b'step '):
                done, total, what = line.decode('utf-8', 'replace').strip().split(' ', 3)[1:]
                self.step.emit(self.generation, float(done), int(total), what)

    def done(self, code, _status):
        self.read()
        if self.cancelled:
            self.temporary.cleanup()
            self.deleteLater()
            return
        if not self.delivered:
            self.delivered = True
            result = self.folder / 'result.bin'
            try:
                if code == 0 and result.exists():
                    energy, metrics = frame_of(result)
                else:
                    energy, metrics = {}, {'error': bytes(self.process.readAllStandardError()).decode('utf-8', 'replace')
                                           or f'Computation exited with code {code}'}
            except UNREADABLE as error:
                energy, metrics = {}, {'error': str(error)}
            self.finished.emit(self.generation, energy, [], metrics)
        self.temporary.cleanup()

    def error(self, error):
        if error == QProcess.ProcessError.FailedToStart and not self.cancelled and not self.delivered:
            self.delivered = True
            self.finished.emit(self.generation, {}, [], {'error': self.process.errorString()})
            self.temporary.cleanup()

    def cancel(self, wait=False):
        """Stop without making the window wait: the process is killed, and its folder goes when it has gone."""
        self.cancelled = True
        if self.process.state() == QProcess.ProcessState.NotRunning:
            self.temporary.cleanup()
            self.deleteLater()
            return
        self.process.kill()
        if wait:
            if not self.process.waitForFinished(500):
                raise RuntimeError('The computation process did not stop')
            self.temporary.cleanup()


def start_process(parent):
    """A worker that imports everything and then waits for its folder on stdin."""
    process = QProcess(parent)
    process.setProgram(sys.executable)
    process.setArguments(['-m', WORKER, '--warm'])
    process.start()
    return process


class Calculator(QObject):
    """The process of the computation kept alive for the session of the project (R478, `serve`): its caches (shading,
    the inverters' parts of the network, the weather, the pool's processes) stay from one year to the next, so that a
    year after a small change pays for what changed. One year at a time: a year asked while another is on its way
    waits for it; a cancel asks the process to stop at its next step, and one not answered within GRACE_MS is killed
    and started again. A process that ended by itself is started again and said in the log; the year it was
    computing is sent again once."""

    GRACE_MS = 30000           # a year waiting for its pool to start (Windows, a loaded machine) checks for a stop late
    RESTARTS = 3                # within a minute: then the years are told the error instead of starting it again

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self.ready = False
        self.current = None
        self.waiting = []
        self.buffer = b''
        self.closing = False
        self.deaths = []
        self.restarts = 0       # said in the log each time (R478)
        self.grace = QTimer(self)
        self.grace.setSingleShot(True)
        self.grace.timeout.connect(self._unanswered)
        self.start()

    def start(self):
        self.ready, self.buffer = False, b''
        process = QProcess(self)
        process.setProgram(sys.executable)
        process.setArguments(['-m', WORKER, '--serve', '--parent', str(os.getpid())])
        process.readyReadStandardOutput.connect(lambda p=process: self._read(p))
        process.finished.connect(lambda code, _status, p=process: self._ended(p, code))
        process.errorOccurred.connect(lambda error, p=process: self._failed_to_start(p, error))
        self.process = process
        process.start()

    def submit(self, job):
        if self.closing:
            job._failed('The computation is closed')
            return
        if self.process is None:
            self.start()
        self.waiting.append(job)
        self._next()

    def cancel(self, job):
        if job in self.waiting:
            self.waiting.remove(job)
            job._cleanup()
            job.deleteLater()
        elif job is self.current and self.process is not None:
            self.process.write(b'cancel\n')
            self.grace.start(self.GRACE_MS)

    def _next(self):
        if self.closing or not self.ready or self.current is not None or not self.waiting:
            return
        self.current = self.waiting.pop(0)
        self.process.write(f'job {self.current.folder}\n'.encode('utf-8'))

    def _read(self, process):
        if process is not self.process:
            return
        try:
            self.buffer += bytes(process.readAllStandardOutput())
        except RuntimeError:            # the window going: the process went with its owner
            return
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            word = line.strip().split(b' ', 1)[0]
            if word == b'ready':
                self.ready = True
                self._next()
            elif word == b'done':
                self.grace.stop()
                job, self.current = self.current, None
                if job is not None:
                    job._done()
                self._next()
            elif self.current is not None:
                self.current._line(line)

    def _ended(self, process, code):
        if process is not self.process or self.closing:
            return
        try:
            error = bytes(process.readAllStandardError()).decode('utf-8', 'replace').strip()
        except RuntimeError:            # the window going: the process went with its owner
            return
        now = time.monotonic()
        self.deaths = [t for t in self.deaths if now - t < 60] + [now]
        self.grace.stop()
        job, self.current = self.current, None
        self.process = None
        process.deleteLater()
        if job is not None and not job.cancelled and not job.retried:
            job.retried = True
            self.waiting.insert(0, job)
        elif job is not None:
            job._failed(error or f'Computation exited with code {code}')
        if len(self.deaths) > self.RESTARTS:
            log.complain('The process of the computation ended again; not started again until the next year',
                         RuntimeError(f'exit code {code}: {error[-2000:]}'))
            for waiting in self.waiting:
                waiting._failed(error or f'Computation exited with code {code}')
            self.waiting, self.deaths = [], []
            return
        self.restarts += 1
        log.complain('The process of the computation ended by itself; started again',
                     RuntimeError(f'exit code {code}: {error[-2000:]}'))
        self.start()

    def _failed_to_start(self, process, error):
        if error == QProcess.ProcessError.FailedToStart and process is self.process:
            self._ended(process, -1)

    def _unanswered(self):
        """A stop not answered in time: the process is killed (its caches with it) and a new one started."""
        if self.process is None or self.current is None:
            return
        self.restarts += 1
        log.complain('The process of the computation did not stop when asked; started again',
                     RuntimeError(f'no answer within {self.GRACE_MS} ms'))
        process, job = self.process, self.current
        self.process, self.current = None, None
        process.kill()
        job._cleanup()
        job.deleteLater()
        self.start()

    def close(self):
        """The end of the session: the end of the pipe tells the process to go (with its pool); killed if it has not
        gone within a moment."""
        if self.closing:
            return
        self.closing = True
        self.grace.stop()
        for job in [self.current, *self.waiting]:
            if job is not None:
                job.cancelled = True
                job._cleanup()
        self.current, self.waiting = None, []
        process = self.process
        if process is not None and process.state() != QProcess.ProcessState.NotRunning:
            process.write(b'quit\n')
            process.waitForBytesWritten(100)
            process.closeWriteChannel()
            if not process.waitForFinished(300):
                process.kill()
                process.waitForFinished(500)


class LiveWorker(QObject):
    """A year computed by the Calculator: the same signals as Worker, the same input.bin. Its layouts and its year
    (layout.bin, result.bin: frames, data/frames.py) are read on a thread of the window's jobs (app/year_read.py, on
    `center`) and given on the window's turns, a piece each (R598, study 48 chapter 6 step 4): before, the year's 80 MB
    were read and unpickled here, 0,8-1,6 s of the window on Rho. The layouts first, then the year."""
    layout = Signal(int, object, object)
    step = Signal(int, float, int, str)
    finished = Signal(int, object, object, object)

    def __init__(self, generation, photo, known, cache, calculator, fingerprint='', options=None, center=None):
        super().__init__(calculator)
        self.generation = generation
        self.calculator = calculator
        self.center = center
        self.options = dict(options or {})
        self.cancelled = False
        self.delivered = False
        self.retried = False
        self._reads = 0                 # reads of its files on their way
        self._ended = False             # the process said `done`: the year is read after the layouts
        self.temporary = tempfile.TemporaryDirectory(prefix='compute-', dir=cache, ignore_cleanup_errors=True)
        self.folder = Path(self.temporary.name)
        (self.folder / 'input.bin').write_bytes(pickle.dumps((photo, known, Path(cache), fingerprint, True,
                                                                  self.options), protocol=5))

    @property
    def process(self):
        return self.calculator.process

    def start(self):
        self.calculator.submit(self)

    def _line(self, line):
        if self.cancelled:
            return
        if line.strip() == b'layout':
            self._read('layout', self._layout_came)
        elif line.startswith(b'step '):
            done, total, what = line.decode('utf-8', 'replace').strip().split(' ', 3)[1:]
            # timed with the jobs' calls: the bar and the status bar told of the step (the guard of the window)
            self.center.timed('year.step', self.step.emit, self.generation, float(done), int(total), what)

    def _read(self, name, came):
        """`came(blob, error)` with the bytes of the file `name`.bin read on a thread of the jobs, on the window's
        thread (a delivery of the center, timed as year_read.on_done)."""
        self._reads += 1

        def done(blob, _stale):
            self._reads -= 1
            came(blob, '')

        def failed(_kind, text):
            self._reads -= 1
            came(None, text)
        self.center.submit(year_read.KIND, year_read.file_request(self.folder / f'{name}.bin'),
                           slot=f'{year_read.KIND.name}:{id(self)}:{name}', on_done=done, on_failed=failed)

    def _layout_came(self, blob, _error):
        if not self.cancelled and blob is not None:
            try:
                results, keys = frames.loads(blob)
            except UNREADABLE:          # as before: a layout that cannot be read is not given, the year still is
                results = keys = None
            if results is not None:
                self.center.piece('year.layout', self._give_layout, results, keys)
        self._next()

    def _give_layout(self, results, keys):
        if not self.cancelled:
            self.layout.emit(self.generation, results, keys)

    def _done(self):
        if self.cancelled or self.delivered:
            self._gone()
            return
        self.delivered = True
        self._ended = True
        self._next()

    def _next(self):
        """The year read once the process has ended and its layouts have been read (they come first, as before)."""
        if self.cancelled:
            self._gone()
        elif self._ended and not self._reads:
            self._ended = False
            self._read('result', self._result_came)

    def _result_came(self, blob, error):
        energy, metrics = {}, {'error': error}
        if blob is not None:
            try:
                energy, metrics = frames.loads(blob)
            except UNREADABLE as failure:
                energy, metrics = {}, {'error': str(failure)}
        if self.cancelled:
            self._gone()
            return
        self._cleanup()
        if metrics.get('cancelled'):
            return
        self.center.piece('year.finished', self._give, energy, metrics)

    def _give(self, energy, metrics):
        if self.cancelled:              # cancelled while its piece waited: nothing to give
            self.deleteLater()
            return
        self.finished.emit(self.generation, energy, [], metrics)

    def _gone(self):
        """The folder taken away and, once cancelled, this job: when no read of its files is on its way any more."""
        if self._reads:
            return
        self._cleanup()
        if self.cancelled:
            self.deleteLater()

    def _failed(self, text):
        if not self.cancelled and not self.delivered:
            self.delivered = True
            self.finished.emit(self.generation, {}, [], {'error': text})
        self._cleanup()

    def _cleanup(self):
        self.temporary.cleanup()

    def cancel(self, wait=False):
        """Stop without making the window wait: the process stops at its next step and keeps its caches."""
        if self.cancelled:
            return
        self.cancelled = True
        self.calculator.cancel(self)


def live_compute() -> bool:
    """The process of the computation kept for the session (R478), on every system; MERIDIANA_LIVE_COMPUTE=0 goes
    back to one process for each year (the trials, a comparison). On Windows since r20: in r19 the years stood still
    there, the pool's workers sharing the commands' pipe (`_own_stdin`, tests/quick/shell/test_live_pipe.py)."""
    return os.environ.get('MERIDIANA_LIVE_COMPUTE', '1') != '0'


class ShellBridge(Bridge):
    progressChanged = Signal()
    noticed = Signal(str)       # a line for the status bar: what the program did by itself (R442)

    def __init__(self, project, cache, parent=None):
        self._closed = False
        self._spare = None
        self._calculator = None
        self._store_read = None         # the year of the store on its way: (key, generation) it was asked at
        self._progress = {}
        self._force = False
        Path(cache).mkdir(parents=True, exist_ok=True)
        super().__init__(project, cache, parent)
        # R461: the year computed again by itself when the changes stop, low and with few processes; all the power
        # when a phase that shows it opens or Calcola is pressed (yearWanted, recompute)
        self._background = False
        self._next_background = False
        self.background = dict(enabled=True, wait_s=5.0, workers=2, battery_factor=3.0)
        self.background_timer = QTimer(self)
        self.background_timer.setSingleShot(True)
        self.background_timer.timeout.connect(self._background_start)

    def configure_background(self, enabled=True, wait_s=5.0, workers=2, battery_factor=3.0):
        """The preferences of the year in the background (config.background_year*)."""
        self.background = dict(enabled=bool(enabled), wait_s=max(.5, float(wait_s)), workers=max(1, int(workers)),
                               battery_factor=max(0.0, float(battery_factor)))
        if not self.background['enabled']:
            self.background_timer.stop()

    @Property(bool, notify=progressChanged)
    def updating(self):
        """A year in the background on its way (R461): the numbers in hand are those of before."""
        return self._busy and self._background

    def _changed(self, topics):
        generation = self.session.generation
        super()._changed(topics)
        if self.session.generation != generation and 'file' not in topics:
            self._background_restart()

    def _background_restart(self):
        """A change: the year in the background on its way is out of date, stopped; it starts again after the wait
        without changes (on battery longer, or never)."""
        if self._background and self._busy and self._job is not None:
            self._job.cancel()
            self._job = None
            self._busy, self._background, self._progress = False, False, {}
            self.progressChanged.emit()
            self.stateChanged.emit()
        settings = self.background
        if self._closed or not settings['enabled']:
            return
        wait = settings['wait_s']
        if resources.on_battery():
            if settings['battery_factor'] <= 0:
                return
            wait *= settings['battery_factor']
        self.background_timer.start(int(wait * 1000))

    def _background_start(self):
        if self._closed or self._busy or not self._enabled:
            return
        if self.session.energy and not self.session.year_outdated():
            return
        self._next_background = True
        self._launch()

    @Slot()
    def yearWanted(self):
        """A phase that shows the year opened (Production, Consumption, Economics, Report): all the power (R461). A
        year in the background on its way gives way to a full one; a full one goes on; one up to date stays."""
        self.background_timer.stop()
        if self._busy and not self._background:
            return
        if self._busy or not self.session.energy or self.session.year_outdated():
            self.recompute()

    @Slot()
    def recompute(self):
        if not self._closed:
            # Asked again on a year that answers for the project: the designer wants it made, not found.
            session = self.session
            self._force = bool(session.energy) and not session.year_outdated()
            super().recompute()

    def _take_spare(self):
        spare, self._spare = self._spare, None
        if spare is not None and spare.state() == QProcess.ProcessState.NotRunning:
            spare.deleteLater()
            return None
        return spare

    def _launch(self):
        """A change stops the computation in hand: its layout and year are already out of date (M12), and the next
        one starts from a process kept warm, so the modules on the plan do not wait for imports nor for a year."""
        if self._closed:
            return
        self._pending = False
        if self._job is not None:
            if self._busy:
                self._job.cancel()
            else:
                self._job.deleteLater()
            self._job = None
        self._store_read = None                 # a year of the store on its way is not awaited any more
        force, self._force = self._force, False
        if not force and self._nothing_to_do():
            self._busy, self._error, self._progress = False, '', {}
            self.progressChanged.emit()
            self.stateChanged.emit()
            return
        self._busy, self._error, self._progress = True, '', {}
        self.progressChanged.emit()
        self.stateChanged.emit()
        if not force and self._from_store():
            return
        self._compute()

    def _compute(self):
        """The year computed: in the process kept for the session (Calculator), or one process for this year."""
        self._background, self._next_background = self._next_background, False
        options = None
        if self._background:
            options = {'low': True, 'workers': 1 if resources.on_battery() else self.background['workers']}
        try:
            self._asked_year()
            if live_compute():
                if self._calculator is None:
                    self._calculator = Calculator(self)
                self._job = LiveWorker(self.session.generation, self.session.photo(),
                                       self.session.known_layouts(), self.cache, self._calculator,
                                       self.session.year_fingerprint(), options=options, center=self.work.center)
            else:
                self._job = Worker(self.session.generation, self.session.photo(),
                                   self.session.known_layouts(), self.cache, self, self._take_spare(),
                                   self.session.year_fingerprint(), options=options)
        except (OSError, TypeError, ValueError, AttributeError, pickle.PicklingError) as error:
            # Said, and not left «computing» for ever (D26).
            self._busy, self._error = False, str(error)
            self.stateChanged.emit()
            return
        self._job.layout.connect(self.accept_layout)
        self._job.step.connect(self._step)
        self._job.finished.connect(self._finished)
        self._job.start()
        if self._spare is None and not live_compute():      # the next year's process, one for each year
            self._spare = start_process(self)

    def _ask_layout(self):
        if not self._closed:
            super()._ask_layout()

    @Slot(int, object, object)
    def accept_layout(self, generation, results, keys, realigned=False, photo=None):
        """Through a pickle every layout is a new object: a sub-field whose inputs did not change keeps its own,
        so that only the ones really changed are told to the views (the year's layouts; the jobs' layout sends
        only those changed, layout_job.results_of)."""
        known, old = self.session.results, self.session.layout_keys
        kept = {sid: known[sid] if sid in known and sid in old and old[sid] == keys.get(sid) else result
                for sid, result in results.items()}
        taken = super().accept_layout(generation, kept, keys, realigned, photo)
        if taken and self.session.realigned:
            text = self.session.realigned_text(self.session.realigned)
            self._piece('bridge.notice', lambda: self.noticed.emit(text))
        return taken

    def _nothing_to_do(self):
        """An undo back to the state computed, with the layouts of that state still in hand."""
        session = self.session
        return (bool(session.energy) and not session.year_outdated()
                and all(session.layout_keys.get(k) == v for k, v in session.expected_layout_keys().items()))

    def _from_store(self):
        """The year of exactly these inputs, kept from before: a project opened again, an undo back to a state computed
        (R437). Nothing to compute: read on a thread of the jobs (app/year_read.py, the light year of the store) and
        taken when it comes (_store_came), a piece of the window's turns each; True while it is on its way. Before, the
        store was read here, 0,2-0,9 s of the window on Rho (R598)."""
        session = self.session
        key = session.expected_key()
        fingerprint = year_key.fingerprint(key)
        if not year_store.path_of(self.cache, fingerprint).is_file():
            return False
        asked = self._store_read = (key, session.generation)
        self.work.center.submit(year_read.KIND, year_read.store_request(self.cache, fingerprint),
                                slot=f'{year_read.KIND.name}:store', on_done=lambda blob, _stale: self._store_came(asked, blob),
                                on_failed=lambda _kind, _text: self._store_came(asked, None))
        return True

    def _store_came(self, asked, blob):
        """The store's answer (a delivery of the jobs, timed as year_read.on_done): the year made of its bytes, taken
        in the next piece. One no longer awaited (another year asked, Cancel, the window closed) is dropped."""
        if asked is not self._store_read or self._closed:
            return
        data = year_store.light_of(blob, asked[0])
        self._piece('year.take', self._take_stored, asked, data)

    def _take_stored(self, asked, data):
        """The year read from the store, taken when the project is still the one it was asked for; computed when the
        store had not that year after all (another version, damaged: as when there is no file, also if the project
        changed meanwhile); a year read but of a project changed meanwhile is left, as any year after a change (the
        change asks for its layouts; the year in the background comes after the quiet)."""
        if asked is not self._store_read or self._closed:
            return
        self._store_read = None
        session = self.session
        if data is None or session.generation != asked[1] or session.expected_key() != asked[0]:
            if data is None:            # as before, when the store had nothing: computed (a store of version 2 too)
                self._compute()
            else:
                self._busy, self._progress = False, {}
                self.progressChanged.emit()
                self.stateChanged.emit()
            return
        self._busy, self._progress = False, {}
        session.generation += 1
        session.take_year(data['results'], data['layout_keys'], data['energy'], pieces=True)
        self._error, self._year_note = '', data['energy'].get('error_sim', '') or ''
        self._piece('bridge.scene', self._rebuild_scene)   # the checks' job hears the year taken by itself
        self._piece('bridge.yearChanged', self.yearChanged.emit)
        self._piece('bridge.progress', self.progressChanged.emit)        # what the QML binds to them, a turn each
        self._piece('bridge.state', self.stateChanged.emit)

    def _step(self, generation, done, total, what):
        """A step of the year awaited: the bar moves (ui/window.py _energy_step)."""
        if generation == self.session.generation:
            self._progress = {'fraction': done / max(1, total),
                              'text': _('Production: {what} ({n} of {total})').format(what=what, n=int(done) + 1, total=total)}
            self.progressChanged.emit()

    @Property(bool, notify=progressChanged)
    def computing(self):
        """The year itself on its way, not the checks that follow it."""
        return self._busy

    @Property('QVariantMap', notify=progressChanged)
    def progress(self):
        return self._progress

    @Slot()
    def cancelCompute(self):
        """Cancel, in the status bar: the year on its way is awaited no longer; the next change asks for it again."""
        self.timer.stop()
        self._store_read = None
        if self._job is not None and self._busy:
            self._job.cancel()
            self._job = None
        self._busy, self._progress = False, {}
        self.progressChanged.emit()
        self.stateChanged.emit()

    def _finished(self, *args):
        self._background = False
        if not self._closed:
            self._progress = {}
            if args[-1].get('kept_error'):
                log.complain('The year could not be kept', OSError(args[-1]['kept_error']))
            super()._finished(*args)
            self._piece('bridge.progress', self.progressChanged.emit)    # what the QML binds to it, a turn of its own

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.timer.stop()
        self._store_read = None
        self._enabled = self._pending = self._busy = False
        if self._changed in self.session.listeners:
            self.session.listeners.remove(self._changed)
        if self._job is not None:
            self._job.cancel(wait=True)
        if self._calculator is not None:
            self._calculator.close()
        self.checks_feed.close()
        if self._work is not None:          # the layout's process (and the checks') with the other jobs' (R598)
            self._work.close()
        if self._spare is not None:
            self._spare.kill()
            self._spare.waitForFinished(500)
        self.pool.clear()                   # nothing of the shell's runs there (its year is a process)
        self.pool.waitForDone()


def worker(folder, live=False):
    """One computation of the folder's input.bin into its result.bin. `live`: in the process kept for the session
    (R478, `serve`): the priority and the processes of a year in the background are this year's only, and a stop
    asked (resources.STOP) ends it at the next step, with the caches of what it finished."""
    from meridiana.app import jobs
    from meridiana.data import year_store
    from meridiana.core.compute import resources
    from meridiana.core.energy import electrical_network, nearshade
    from meridiana.app import pipeline
    from meridiana.app import year_key
    start = time.perf_counter()
    restore = None
    before = (dict(electrical_network._STATS), nearshade._CACHE.hits, nearshade._CACHE.misses)
    try:
        project, known, cache, fingerprint, *rest = pickle.loads((folder / 'input.bin').read_bytes())
        if isinstance(project, dict):       # the session's photo (R598); a Project from the measures' scripts
            from meridiana.app.session import project_from
            project = project_from(project)
        year = rest[0] if rest else True
        options = rest[1] if len(rest) > 1 else {}
        if options.get('low'):
            # R461, a year in the background: below the window and the other programs, with few processes; set
            # before the pool starts, so that its processes inherit both
            if live:
                restore = resources.background(True, options.get('workers'))
            else:
                resources.lower_priority()
                if options.get('workers'):
                    os.environ['MERIDIANA_WORKERS'] = str(max(1, int(options['workers'])))
        elif live:
            restore = resources.background(False, None)
        if year:
            # the processes of the electrical network started now, while the layouts and the first pass run:
            # they have imported everything by the time the network needs them (R435)
            from meridiana.core.compute import resources
            resources.warm()
        results, keys, _unused = jobs.layout_of(project, known)
        frames.write(folder / 'layout.bin', (results, keys))       # read on a thread of the window (LiveWorker)
        print('layout', flush=True)
        if not year:
            frames.write(folder / 'result.bin', ({}, {'layout_only': True}))
            return
        good = {key: result for key, result in results.items() if not isinstance(result, Exception)}
        laid = time.perf_counter()
        phases = {}                 # the first time each step was told, from the start (R478, the measures)

        def progress(done, total, what):
            if resources.STOP.is_set():
                raise pipeline.Interrupted()
            phases.setdefault(f'{int(done)} {what}', round((time.perf_counter() - start) * 1000))
            print(f'step {done} {total} {what}', flush=True)
        energy = pipeline.compute(project, good, cache, fetch=False, progress=progress).as_dict()
        metrics = {'worker_ms': (time.perf_counter()-start)*1000, 'layout_ms': (laid - start) * 1000,
                   'live': live, 'pid': os.getpid(),
                   'network_parts_kept': electrical_network._STATS['kept'] - before[0]['kept'],
                   'network_parts_made': electrical_network._STATS['made'] - before[0]['made'],
                   'shading_kept': nearshade._CACHE.hits - before[1],
                   'shading_made': nearshade._CACHE.misses - before[2], 'phases_ms': phases,
                   'network': {k: round(v - before[0].get(k, 0), 3) for k, v in electrical_network._STATS.items()}}
        if fingerprint and energy.get('sim') is not None:
            # Here, not in the window: a year is some megabytes to write. The key the window will compare it with.
            try:
                year_store.write(cache, fingerprint, year_key.expected(project), energy, results, keys)
            except OSError as error:        # a full disk costs the copy, not the year in hand
                metrics['kept_error'] = str(error)
    except (pipeline.Interrupted, resources.Stopped):
        energy, metrics = {}, {'cancelled': True}
    except Exception as error:
        energy, metrics = {}, {'error': str(error)}
    finally:
        if restore is not None:
            restore()
    # the year as the window reads it (year_store.split: the near shading of the first pass stays here and in the
    # store, 76 of 80 MB on Rho), as a frame: read on a thread of the window and made there in milliseconds (R598)
    frames.write(folder / 'result.bin', (year_store.split(energy)[0], metrics))


def serve():
    """The process of the computation kept for the session (R478): it imports once, keeps in memory what the years
    made (shading, the inverters' parts of the network, the weather, the pool's processes) within the memory budget,
    and computes one folder after the other. Lines on stdin: `job <folder>`, `cancel` (the year in hand stops at its
    next step), the end of the file (the window has gone: so does this process, with its pool). On stdout: `ready
    <pid>` once, then for each job its `layout`, `step` lines and `done`."""
    # first of all, before any thread or process: the window's commands for this process alone (R478, Windows)
    channel = _own_stdin()
    import threading
    from meridiana import i18n  # noqa: F401
    from meridiana.app import jobs  # noqa: F401
    from meridiana.core.compute import resources  # noqa: F401
    from meridiana.app import pipeline  # noqa: F401
    if os.environ.get('MERIDIANA_SERVE_TRACE'):
        # every N seconds where each thread is, on stderr (the window's log keeps the end of it): a year that stalls
        import faulthandler
        faulthandler.dump_traceback_later(float(os.environ['MERIDIANA_SERVE_TRACE']), repeat=True, file=sys.stderr)
    resources.contain_children()
    # what the years keep gives memory back when the machine gets short, not only at the next year (study 56)
    from meridiana.app.platform import log
    resources.watch(complain=log.complain)
    # the window gone, killed or crashed: this process goes too. The window says who it is: on Windows the parent of
    # this interpreter is the launcher of the virtual environment, which outlives the window waiting for its child
    parent = int(sys.argv[sys.argv.index('--parent') + 1]) if '--parent' in sys.argv else os.getppid()
    resources.watch_parent(parent)
    # the solar library and what it brings (SciPy, pandas) here, once, on the main thread, before the first year: the
    # years do not pay for it. (In the year's thread it took minutes on Windows in r19: loading NumPy's library waited
    # for the main thread's read of the pipe, the cause `_own_stdin` removes, R478 r20.)
    from meridiana.core.energy import dependencies
    dependencies.load_pvlib()
    import pvlib.bifacial.infinite_sheds  # noqa: F401
    import pvlib.bifacial.utils  # noqa: F401
    i18n.setup_as_window()
    lock = threading.Lock()
    waiting = []
    running = []

    def run(folder):
        try:
            worker(Path(folder), live=True)
        finally:
            print('done', flush=True)
            with lock:
                running.clear()
                if waiting:
                    start(waiting.pop(0))

    def start(folder):
        # cleared here, before the year's thread starts: a cancel read just after the job is this job's (cleared in
        # the thread, it was lost, and the year went on to its end)
        resources.STOP.clear()
        # each year on a thread of its own: a year in the background lowers its thread, not the process (R461)
        thread = threading.Thread(target=run, args=(folder,), name='meridiana-year', daemon=True)
        running.append(thread)
        thread.start()

    print('ready', os.getpid(), flush=True)
    for line in commands(channel):
        word, _sep, rest = line.strip().partition(' ')
        if word == 'quit':
            break
        if word == 'job' and rest:
            with lock:
                if running:
                    waiting.append(rest)
                else:
                    start(rest)
        elif word == 'cancel':
            resources.STOP.set()
        elif word == 'warm':
            # the pool started ahead (the window opens a project); its processes said, for the trials of R478
            import concurrent.futures
            concurrent.futures.wait(resources.warm(), timeout=120)
            found = getattr(resources._POOL, '_processes', None) or {}
            print('warm', *sorted(found), flush=True)
    # the window has gone, said so or closed this pipe: nothing more to compute; the pool goes with this process
    resources.STOP.set()
    resources.shutdown()
    sys.stdout.flush()
    os._exit(0)


def _own_stdin() -> int:
    """The window's commands on a descriptor of this process alone, and the null device in place of the standard
    input (descriptor 0 and the process's handle). On Windows a child that shares the console gets a copy of its
    parent's standard handles even when it inherits nothing else: the pool's workers got the commands' pipe. With the
    main thread in a synchronous read of that pipe for the whole year, what touched the same pipe from elsewhere
    waited for that read to end, that is for the window's next line: the workers starting up (the pool never ready,
    the year never ended: hours on the PC on 06/11/2026), the loading of NumPy's library in the year's thread, and the
    reads came back empty while a worker started (R478, r20; tests/quick/shell/test_live_pipe.py). Elsewhere it changes
    nothing but this: the workers read nothing of the window's. The private descriptor is not inherited (PEP 446)."""
    try:
        private = os.dup(0)
    except OSError:                     # no stdin at all: nothing to keep, nothing for the children to share
        return 0
    null = os.open(os.devnull, os.O_RDONLY)
    os.dup2(null, 0)
    os.close(null)
    if sys.platform == 'win32':
        import ctypes
        import msvcrt
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.SetStdHandle.argtypes = (ctypes.c_uint32, ctypes.c_void_p)
        kernel.SetStdHandle(0xFFFFFFF6, msvcrt.get_osfhandle(0))      # STD_INPUT_HANDLE (-10): what children get
    return private


def commands(fd: int = 0):
    """The lines of the commands' pipe (`fd`), until its end. On Windows a read of nothing is not taken for the end:
    in r19 the pipe gave empty reads while a worker of the pool started on the same pipe (`_own_stdin`, R478, the
    process of the computation went at its first year); there the end is `quit`, or the window gone
    (`resources.watch_parent` ends this process anyway)."""
    buffer = b''
    while True:
        try:
            chunk = os.read(fd, 65536)
        except OSError:
            return
        if not chunk:
            if _stdin_gone():
                return
            time.sleep(0.05)
            continue
        buffer += chunk
        while b'\n' in buffer:
            line, buffer = buffer.split(b'\n', 1)
            yield line.decode('utf-8', 'replace')


def _stdin_gone() -> bool:
    """After a read of nothing: whether stdin has really ended. Elsewhere than Windows, yes. On Windows never: in r19
    the pipe gave empty reads while the window was there, and asking the pipe (PeekNamedPipe) answered «gone» too
    while it was not (R478, 06/11/2026: both while the pool's workers shared the pipe, see `_own_stdin`); kept as a
    net: there the end is `quit`, or the window gone (`watch_parent`)."""
    return sys.platform != 'win32'


def warm():
    """Everything imported first, then the folder: an end of file means the program has gone."""
    from meridiana import i18n  # noqa: F401
    from meridiana.app import jobs  # noqa: F401
    from meridiana.app import pipeline  # noqa: F401
    i18n.setup_as_window()
    folder = sys.stdin.readline().strip()
    if folder:
        worker(Path(folder))


if __name__ == '__main__':
    if '--serve' in sys.argv:
        serve()
    else:
        warm()
