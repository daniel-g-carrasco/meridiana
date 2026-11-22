"""Asynchronous layout scheduling for a standalone plan, using the shared core jobs, and the strings' scene of a
new scale made off the window's thread."""
from __future__ import annotations

import gc
import queue
import sys
import threading

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal

from meridiana.app import jobs
from meridiana.app.platform import log
from meridiana.app.session import needs_layout, project_from
from meridiana.app.view import plan_wiring


class LayoutSignals(QObject):
    done = Signal(int, object, object, str)


class LayoutTask(QRunnable):
    def __init__(self, generation, photo, known):
        super().__init__()
        self.generation, self.photo, self.known = generation, photo, known
        self.signals = LayoutSignals()

    def run(self):
        try:
            results, keys, _laid = jobs.layout_of(project_from(self.photo), self.known)
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
        task = LayoutTask(serial, self.session.photo(), self.session.known_layouts())
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


_holds = 0
_collecting = False
_turns = 0
_turn = 0.005
TURN = 0.0005               # seconds: Python's turn between threads while a thread of the plan works


def still(on: bool) -> None:
    """Python's collector held, and let go when the last who held it lets go: called on the window's thread only.
    R706: a whole collection stops the window for as long as the program's memory is large (125-165 ms with a
    plant of 10 000 modules, 380 000 objects to look at), and it fell where it happened to, in a zoom of the plan
    too. The plan holds it while the view moves and for a moment after (PlanController.viewMoving); the collection
    then comes as often as before, at rest."""
    global _holds, _collecting
    if on:
        if _holds == 0:
            _collecting = gc.isenabled()
            gc.disable()
        _holds += 1
    else:
        _holds = max(0, _holds - 1)
        if _holds == 0 and _collecting:
            gc.enable()


def hold(on: bool) -> None:
    """Python's collector held while a thread of the plan works (`still`), and let go when the last one has
    answered: called on the window's thread only. Meanwhile the threads take turns at Python ten times as often
    (R706): the window asks for its turn at every value the QML reads from Python, and each time it waited for the
    thread's whole turn, 5 ms: a frame of the plan while a scene was being made lasted 110-180 ms."""
    global _turns, _turn
    still(on)
    if on:
        if _turns == 0:
            _turn = sys.getswitchinterval()
            sys.setswitchinterval(min(_turn, TURN))
        _turns += 1
    else:
        _turns = max(0, _turns - 1)
        if _turns == 0:
            sys.setswitchinterval(_turn)


def make_wiring(answers, serial, photo, results, keys, options, scene, turn):
    """The strings' scene made in a thread of its own, its answer left in `answers` (WiringScheduler). `scene`: the
    scheduler's WiringScene, one thread at a time (`turn`): what it found for a scale serves the next (R706)."""
    try:
        with turn:
            answers.put((serial, plan_wiring.made_with(project_from(photo), results, keys, options, scene), ''))
    except Exception as error:  # Worker boundary; the plan makes the scene itself and the log says why.
        answers.put((serial, None, str(error)))


class WiringScheduler(QObject):
    """R706: the strings' scene of a new scale (lines, lanes, arrows, dots and names for the zoom the view settled
    on) is made off the window's thread and offered to the plan as the layout's job offers its own (R598,
    session.wiring_offer): made on the window it stopped it for 90-140 ms at 2000 modules and five times that at
    10 000, each time the hand rested at a new scale. Only the last request counts: a view that moved on while
    a scene was being made takes the next one.

    The thread holds no Qt object, not even this one: it is given the data and a queue, where it leaves its answer
    for a timer of the window's thread to read. And Python's collector waits while a scene is being made (`hold`):
    a collection that falls on the thread, which makes tens of thousands of objects, destroys there whatever Qt
    objects were garbage, away from the window's thread, and their timers go on firing for objects that are no
    more (an access violation in QCoreApplication::notifyInternal2, sendTimerEvent: two runs of the plan's tests
    in three, found with the native stack)."""
    made = Signal()

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.pending = set()
        self.answers = queue.SimpleQueue()
        self.serial = 0
        self.closed = False
        self.threads = []
        # R706: one maker of scenes for all the scales asked (it was a new one each time, which found the strings'
        # ways and made every module's fill again: 190-530 ms at 2000 modules, for a scene equal to the last but
        # for its arrowheads). It keeps what does not follow the scale; the scenes themselves are kept by the plan.
        self.scene = plan_wiring.WiringScene(limit=lambda: 0)
        self.turn = threading.Lock()
        self.timer = QTimer(self)
        self.timer.setInterval(10)
        self.timer.timeout.connect(self.collect)

    @property
    def busy(self):
        return self.serial in self.pending

    def request(self, options):
        self.serial += 1
        self.pending.add(self.serial)
        if len(self.pending) == 1:
            hold(True)
        # the layouts by reference, in a dict of their own: a layout that comes meanwhile replaces entries of the
        # session's, never the results themselves; the photo is never changed by who receives it
        thread = threading.Thread(target=make_wiring, name='meridiana-wiring-scene', daemon=True, args=(
            self.answers, self.serial, self.session.photo(), dict(self.session.results),
            dict(self.session.layout_keys), options, self.scene, self.turn))
        self.threads = [t for t in self.threads if t.is_alive()] + [thread]
        thread.start()
        self.timer.start()

    def collect(self):
        while True:
            try:
                serial, offer, error = self.answers.get_nowait()
            except queue.Empty:
                break
            self.pending.discard(serial)
            if self.closed or serial != self.serial:
                continue
            if error:
                log.note(f"The strings' scene could not be made off the window: {error}")
            elif offer is not None:
                self.session.wiring_offer = offer       # taken only if it is still the scene asked for (its key)
            self.made.emit()
        if not self.pending:
            self.timer.stop()
            hold(False)

    def close(self):
        self.closed = True
        self.timer.stop()
        for thread in self.threads:         # a scene on its way is waited for: the collector is held for it
            thread.join(10)
        if self.pending:
            self.pending.clear()
            hold(False)
