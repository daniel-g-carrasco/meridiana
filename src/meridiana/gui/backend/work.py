"""The heavy jobs in the window (R598, docs/studio/48-lavori-pesanti.md, chapters 3 and 4): the one bridge between
the jobs' center (app/work/center.py, without Qt) and the Quick. It owns the Center, follows the session's changes
for it, wakes Center.pump() on the window's thread with a queued signal (PUMP_MS of work in a turn; a turn at most
every PERIOD_MS for what comes in, and while something is left waiting the next one as soon as the window has had
as long as the turn took, REST_MS at least), and gives the one bar of the status bar (Shell/WorkBar.qml) its rows,
already worded, and Cancel.

The year still runs where it ran (shell_compute.py) and only shows here: its progress is adopted (Center.adopt), so
the status bar has one bar for every job. Installed by the window for every workbench (application.QuickWindow) as a
part (parts.py): `install`."""

import time

from PySide6.QtCore import Property, QObject, Qt, QTimer, Signal, Slot

from meridiana.app.exchange import ifc_cache
from meridiana.app.platform import disk_cap
from meridiana.app.work.center import Center
from meridiana.i18n import N_, _, number

from .parts import Part

PERIOD_MS = 50          # one turn of the pump at most this often for what comes in: the window draws in between
PUMP_MS = 3             # what one turn may take of the window's thread
# What is left waiting after a turn (the pieces of a result, the views told one by one) does not wait a period each:
# seventeen pieces of a layout came 50 ms apart and the deletion ended 0,56 s later than before (measured on screen,
# 14/11/2026). The window has between two turns as long as the last one took, and never less than this.
REST_MS = 4
ERROR_MS = 30000        # a failed job's sentence stays this long in the status bar (as an error nobody caught)
YEAR_TITLE = N_("Production")       # the year on its way: its steps are the phase («Production  the sun (2 of 8)»)
WAIT_TITLE = N_("Computing…")       # the bridge busy without the year: the wait before a year (the checks are a
                                    # job of their own, app/checks_job.py, with their own row)
YEAR_SLOT = "year"
YEAR_STEP = N_("Production: {what} ({n} of {total})")      # shell_compute's words for a step, the title in front


def left_text(seconds) -> str:
    """The time left as the bar says it: «about 40 s», «about 3 min»; "" when not known."""
    if seconds is None:
        return ""
    if seconds < 60:
        step = 1 if seconds < 10 else 5
        return _("about {n} s").format(n=number(max(1, round(seconds / step) * step), 0))
    return _("about {n} min").format(n=number(round(seconds / 60), 0))


def year_phase(text: str) -> str:
    """The year's step without the title in front: «the sun (2 of 8)» of «Production: the sun (2 of 8)», in the
    language in use (shell_compute words its steps whole, as the status bar showed them before the jobs' bar)."""
    head = _(YEAR_STEP).split('{what}')[0]
    return text[len(head):] if head and text.startswith(head) else text


def rest_after(spent_ms: float) -> int:
    """The milliseconds the window has for itself after a turn of `spent_ms` that left something waiting: as long
    as the turn took, REST_MS at least, a period at most."""
    return int(min(PERIOD_MS, max(REST_MS, spent_ms)))


class WorkBackend(QObject):
    rowsChanged = Signal()
    noticed = Signal(str)           # a job failed: its sentence, for the status bar
    _woken = Signal()               # from any thread: the window's thread pumps soon

    def __init__(self, session, bridge=None, parent=None):
        super().__init__(parent)
        self.session, self.bridge = session, bridge
        self._closed = False
        self._rows = []
        self._slots = {}
        self._last = 0.0
        self.year = None                # the year's progress, adopted while the bridge says it is busy
        self.center = Center(self._post, tell=self._tell)
        self.center.subscribe(self._refresh)
        # told with the change itself (R547 `at_once`, 0,1 ms): a job's quiet counts from the gesture, not from its turn
        # in the views told a piece each after the frame (the layout of an addition started 0,4 s later, 14/11/2026)
        session.subscribe(self.center.changed, at_once=True)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        # the rest after a turn is a few ms (rest_after): a coarse timer makes it 16 ms on Windows, and a round of the
        # views told a piece each (R547, 25 views) ended 0,9-1,4 s later than the round told at once (14/11/2026)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self._turn)
        self._woken.connect(self._wake, Qt.ConnectionType.QueuedConnection)
        if bridge is not None and hasattr(bridge, 'progressChanged'):
            bridge.progressChanged.connect(self._follow_year)
            bridge.stateChanged.connect(self._follow_year)

    # the center's thread contract

    def _post(self):
        if not self._closed:
            self._woken.emit()

    @Slot()
    def _wake(self):
        if self._closed or self.timer.isActive():
            return
        since = (time.perf_counter() - self._last) * 1000
        self.timer.start(int(max(0, PERIOD_MS - since)))

    def _turn(self):
        if self._closed:
            return
        self._last = start = time.perf_counter()
        if self.center.pump(PUMP_MS / 1000):
            self.timer.start(rest_after((time.perf_counter() - start) * 1000))

    def _tell(self, text):
        self.noticed.emit(text)

    # what the bar shows

    def _refresh(self):
        """The rows as M.WorkRow lays them out, worded here and only here: what the job is (`title`), the phase in
        hand without the title (`phase`, "" when the job says none), the bar, the percentage, the time left ("" while
        it is not known), Cancel."""
        rows = []
        for row in self.center.rows():
            fraction = row['fraction']
            title, phase = _(row['title']), _(row['phase']) if row['phase'] else ''
            if phase == title:
                phase = ''
            rows.append({'id': row['id'], 'slot': row['slot'], 'title': title, 'phase': phase,
                         'determinate': fraction is not None, 'fraction': fraction or 0.0,
                         'percent': f"{number(100 * (fraction or 0), 0)} %",
                         'left': left_text(row['left']), 'cancellable': bool(row['cancellable']),
                         'state': row['state']})
        if rows != self._rows:
            self._rows = rows
            self._slots = {r['slot']: r for r in rows if r['slot']}
            self.rowsChanged.emit()

    @Property('QVariantList', notify=rowsChanged)
    def rows(self):
        return self._rows

    @Property('QVariantMap', notify=rowsChanged)
    def slots(self):
        """The row of each job by its slot (Center.submit's `slot`, the kind's name by default): what a page or a
        dialog shows of its own job, `M.WorkRow { row: work.slots.ifc_read }`; no key while the job is not there."""
        return self._slots

    @Property('QVariantMap', constant=True)
    def texts(self):
        # leftWidest: the widest time left the row may show, for the width of its column (R607: nothing moves)
        return {'cancel': _('Cancel'), 'others': _('The other jobs in progress'), 'leftWidest': left_text(99 * 60)}

    @Slot(int)
    def cancel(self, job_id):
        handle = self.center.find(job_id)
        if handle is not None:
            self.center.cancel(handle)

    # the year, adopted

    def _follow_year(self):
        if self._closed:
            return
        bridge = self.bridge
        busy = bool(bridge.busy)
        if busy and self.year is None:
            cancel = getattr(bridge, 'cancelCompute', None)
            self.year = self.center.adopt(YEAR_TITLE, cancel=cancel, slot=YEAR_SLOT)
        elif not busy and self.year is not None:
            year, self.year = self.year, None
            year.end()
            return
        if self.year is not None:
            if not self.year.active:            # cancelled from the bar: the bridge's next busy adopts a new one
                self.year = None
                return
            self.year.title = YEAR_TITLE if getattr(bridge, 'computing', True) else WAIT_TITLE
            progress = getattr(bridge, 'progress', None) or {}
            fraction, phase = progress.get('fraction'), year_phase(progress.get('text', ''))
            if fraction is None:
                self.year.progress(0, 0, phase)
            else:
                self.year.progress(float(fraction), 1.0, phase)

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.timer.stop()
        if self.center.changed in self.session.listeners:
            self.session.listeners.remove(self.center.changed)
        if self.bridge is not None and hasattr(self.bridge, 'progressChanged'):
            for signal in (self.bridge.progressChanged, self.bridge.stateChanged):
                try:
                    signal.disconnect(self._follow_year)
                except (RuntimeError, TypeError):
                    pass            # the bridge already gone with its window: nothing left connected
        self.center.close()


def install(engine, session, cache, window):
    """The jobs' bridge for the window's QML (`work`), its failures in the status bar; the one ceiling of the stores
    on disk under the caches (app/platform/disk_cap.py): a pass at the start, in a thread, and the open project's IFC
    geometry declared in use."""
    bridge = getattr(window, 'bridge', None)
    # the bridge's own: the layout of a change is one of its jobs, on this same center (one center per window)
    backend = bridge.work if hasattr(bridge, 'work') else WorkBackend(session, bridge)
    shell = getattr(window, 'shell', None)
    if shell is not None:
        backend.noticed.connect(lambda text: shell.show_notice(text, ERROR_MS, 'error'))
    engine.rootContext().setContextProperty('work', backend)
    closes = [backend.close]
    if cache is not None:
        # the IFC reader writes under the window's own caches (DialogsBackend.paths.cache), inside this root
        paths = getattr(window, 'paths', None)
        ifc = ifc_cache.folder_of(paths.cache if paths is not None else cache)
        follow = ifc_cache.Follow(session, ifc, cache)
        closes.append(follow.close)
        disk_cap.clean_soon(cache, register_too=(ifc,))
    return Part('work', controllers={'work': backend}, close=lambda: [close() for close in closes])
