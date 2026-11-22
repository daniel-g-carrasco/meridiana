"""Opt-in input and scene graph timings. No observer exists unless explicitly requested."""
from collections import deque
import json
import os
from pathlib import Path
import threading
import time

from PySide6.QtCore import QCoreApplication, QEvent, QObject, Qt, QTimer, Slot


def install(window):
    path = os.environ.get('MERIDIANA_TRACE_GESTURES')
    if not path:
        return None
    try:
        return GestureTrace(window, Path(path))
    except OSError as error:
        from meridiana.app.platform import log
        log.note(f'gesture trace could not open its output: {error}')
        return None


class GestureTrace(QObject):
    """Observe a threaded window only through queued GUI callbacks.

    Times are monotonic CPU clocks, not GPU execution or input-to-photon latency. Input
    delivery is timed synchronously with a guarded resend, preserving Qt's accepted flag.
    """

    def __init__(self, window, path, *, render_control=False):
        super().__init__(window)
        self.window = window
        self.stream = path.open('x', encoding='utf8', newline='\n')
        self.rows = deque()
        self.lock = threading.Lock()
        self.seq = 0
        self.sending = False
        self.closed = False
        self.close_pending = False
        self.frame_count = 0
        self.times = {}
        self.gui_work_ms = 0.
        self.frame_gui_ms = 0.
        self.camera = None
        # A direct Python callback can wait for the GIL while synchronous mouse
        # delivery holds it and waits for scene graph sync. RenderControl and the
        # basic loop render on the GUI thread and can safely expose CPU timings.
        self.direct_timing = render_control or os.environ.get('QSG_RENDER_LOOP') == 'basic'
        # the plan the window names (Workbench.planItem, its PlanHost's view), not looked for in its tree (rule 7)
        host = window.property('planItem')
        self.plan = host.property('view') if host is not None else None
        if self.plan is None:
            # RenderControl and embedded components may have visual parents without QObject ownership.
            pending = [window.contentItem()]
            while pending:
                item = pending.pop()
                if item.objectName() == 'plan':
                    self.plan = item
                    break
                pending.extend(item.childItems())
        self.links = [(window.beforeFrameBegin, self.begin), (window.beforeSynchronizing, self.before_sync),
                      (window.afterSynchronizing, self.after_sync), (window.beforeRendering, self.before_render),
                      (window.afterRendering, self.after_render), (window.afterFrameEnd, self.end),
                      (window.afterAnimating, self.snapshot)] if self.direct_timing else []
        for signal, slot in self.links:
            signal.connect(slot, Qt.DirectConnection)
        window.frameSwapped.connect(self.swapped, Qt.QueuedConnection)
        self.links.append((window.frameSwapped, self.swapped))
        window.installEventFilter(self)
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.flush)
        self.timer.start()
        self.add('session', clock='perf_counter_ns', timing='CPU; not GPU time',
                 render_cpu_timing_available=self.direct_timing,
                 swap_clock='gui_delivery',
                 graphics_api=str(window.rendererInterface().graphicsApi()),
                 dpr=window.devicePixelRatio(), size=[window.width(), window.height()],
                 refresh_hz=window.screen().refreshRate() or 60., screen=window.screen().name(),
                 screen_on=None, screen_on_reason='Qt does not expose panel power; verify before measuring')

    def add(self, record, **fields):
        with self.lock:
            self.rows.append(dict(version=1, seq=self.seq, t_ns=time.perf_counter_ns(), record=record, **fields))
            self.seq += 1

    def camera_state(self):
        if self.window.property('viewMode') == '3d':
            view = self.window.property('sceneItem')      # the 3D view the window names (Workbench.sceneItem, rule 7)
            state = view.property('cameraState') if view is not None else None
            state = state.toVariant() if hasattr(state, 'toVariant') else state
            result = {}
            for key, value in (state or {}).items():
                if isinstance(value, (int, float)):
                    result[key] = value
                elif isinstance(value, list):
                    result.update({f'{key}{i}': v for i, v in enumerate(value) if isinstance(v, (int, float))})
            return result or None
        if self.plan is None:
            return None
        result = {name: self.plan.property(name) for name in ('panX', 'panY', 'zoom', 'bearing')}
        goal = self.plan.property('pendingMotion')
        result['goal'] = goal.toVariant() if hasattr(goal, 'toVariant') else goal
        return result

    def eventFilter(self, watched, event):
        if self.sending or self.closed:
            return False
        kind = event.type()
        if kind == QEvent.Wheel:
            fields = dict(gesture='scroll' if event.phase() != Qt.NoScrollPhase else 'wheel',
                          phase=event.phase().name, pixel_delta=[event.pixelDelta().x(), event.pixelDelta().y()],
                          angle_delta=[event.angleDelta().x(), event.angleDelta().y()])
        elif kind == QEvent.NativeGesture:
            fields = dict(gesture='pinch', native_type=event.gestureType().name, value=event.value(),
                          delta=[event.delta().x(), event.delta().y()])
        elif kind in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease) or (
                kind == QEvent.MouseMove and event.buttons() != Qt.NoButton):
            fields = dict(gesture='drag', buttons=event.buttons().value, button=event.button().name)
        elif kind in (QEvent.TouchBegin, QEvent.TouchUpdate, QEvent.TouchEnd, QEvent.TouchCancel):
            fields = dict(gesture='touch', points=[[p.position().x(), p.position().y()] for p in event.points()])
        else:
            return False
        if hasattr(event, 'position'):
            fields['position'] = [event.position().x(), event.position().y()]
        fields.update(event_type=kind.name, device_timestamp_ms=event.timestamp(), camera_before=self.camera_state())
        start = time.perf_counter_ns()
        self.sending = True
        try:
            QCoreApplication.sendEvent(watched, event)
        finally:
            self.sending = False
        elapsed = (time.perf_counter_ns()-start)/1e6
        self.gui_work_ms += elapsed
        self.add('event', **fields, started_ns=start, gui_ms=elapsed,
                 accepted=event.isAccepted(), camera_after=self.camera_state())
        if self.close_pending:
            self.close()
        return True

    @Slot()
    def begin(self):
        self.times = {'begin': time.perf_counter_ns()}

    @Slot()
    def snapshot(self):
        # QJSValue conversion belongs to the GUI thread, even while sync blocks that thread.
        self.camera = self.camera_state()

    @Slot()
    def before_sync(self):
        self.times['sync'] = time.perf_counter_ns()
        self.frame_gui_ms, self.gui_work_ms = self.gui_work_ms, 0.

    @Slot()
    def after_sync(self):
        self.times['synced'] = time.perf_counter_ns()

    @Slot()
    def before_render(self):
        self.times['render'] = time.perf_counter_ns()

    @Slot()
    def after_render(self):
        self.times['rendered'] = time.perf_counter_ns()

    @Slot()
    def end(self):
        end = time.perf_counter_ns()
        times = self.times
        if not all(key in times for key in ('begin', 'sync', 'synced', 'render', 'rendered')):
            return
        self.frame_count += 1
        self.add('frame', frame=self.frame_count, sync_ms=(times['synced']-times['sync'])/1e6,
                 sync_ns=times['sync'],
                 render_ms=(times['rendered']-times['render'])/1e6,
                 render_frame_ms=(end-times['begin'])/1e6, camera=self.camera,
                 gui_events_ms=self.frame_gui_ms, gpu_ms=None, timing_available=True,
                 render_thread=threading.get_ident())

    @Slot()
    def swapped(self):
        if self.closed:
            return
        # A threaded window reports GUI receipt, never fabricated render durations.
        if not self.direct_timing or self.window.rendererInterface().graphicsApi().name == 'Software':
            self.frame_count += 1
            self.add('frame', frame=self.frame_count, sync_ms=None, render_ms=None, render_frame_ms=None,
                     gui_events_ms=self.gui_work_ms, gpu_ms=None,
                     timing_available=False, camera=self.camera_state(), render_thread=None,
                     camera_clock='gui_delivery')
            self.gui_work_ms = 0.
        self.add('swap')

    @Slot()
    def flush(self):
        with self.lock:
            rows = list(self.rows)
            self.rows.clear()
        self.stream.writelines(json.dumps(row, separators=(',', ':'))+'\n' for row in rows)
        self.stream.flush()

    def close(self):
        if self.closed:
            return
        if self.sending:
            self.close_pending = True
            return
        self.closed = True
        self.timer.stop()
        self.window.removeEventFilter(self)
        for signal, slot in self.links:
            signal.disconnect(slot)
        self.flush()
        self.stream.close()
