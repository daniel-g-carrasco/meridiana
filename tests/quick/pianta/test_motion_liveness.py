"""Mixed middle drags and touchpad gestures must finish even on a threaded renderer (R702)."""
import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import _setup

setUpModule = _setup.keep_global_state


def exercise(observer):
    from PySide6.QtCore import QObject, QPointF, QTimer, QUrl
    from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
    from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
    from PySide6.QtTest import QTest
    from meridiana.app import jobs
    from meridiana.gui.application import create_app
    from meridiana.gui.backend.plan import PlanController
    from _fixtures import generated

    sys.path.insert(0, str(_setup.ROOT/'tools'))
    from measure_plan_motion import gestures, measure

    app = create_app()
    _setup._windows_on_screen(app)
    if app.platformName() != 'offscreen':
        screen = int(os.environ.get('MERIDIANA_TEST_SCREEN', '1'))
        if screen >= len(app.screens()):
            raise RuntimeError('the required test screen is absent')
    # Software has no render thread or retained texture: exercise the same input
    # protocol on a small scene without turning raster throughput into a timeout.
    # graphicsApi() is the requested RHI API, even when the platform falls back
    # to software. Constructing a window selects the actual scene graph backend.
    renderer = QQuickWindow()
    software = renderer.rendererInterface().graphicsApi() == QSGRendererInterface.Software
    renderer.deleteLater()
    buildings = 1 if software else 7
    project = generated(buildings, 1, 0)
    results, keys, _ = jobs.layout_of(project)
    controller = PlanController(project, manage_layout=False)
    controller.session.layout_done(controller.session.generation, results, keys)
    controller.setPhase('plant')
    controller.setNavigation('autocad')
    controller.configureMaps({'offline': True})
    engine = QQmlApplicationEngine()
    controller.install(engine)
    component = QQmlComponent(engine)
    component.setData(b'''import QtQuick
import Meridiana.Plan
Window {
    id: host
    width: 1000; height: 740
    required property var backend
    Plan { anchors.fill: parent; backend: host.backend }
}''', QUrl())
    window = component.createWithInitialProperties({'backend': controller})
    assert window is not None, [e.toString() for e in component.errors()]
    if app.platformName() != 'offscreen':
        window.setScreen(app.screens()[screen])
    window.show()
    plan = window.findChild(QObject, 'plan')
    trace = None
    folder = tempfile.TemporaryDirectory(prefix='meridiana-motion-trace-')
    try:
        assert _setup.wait_until(app, lambda: not plan.property('startingUp'), 10)
        assert plan.property('paintedModules') >= 124*buildings
        print('READY', app.platformName(), window.rendererInterface().graphicsApi(),
              f'buildings={buildings}', flush=True)
        if observer == 'trace':
            from meridiana.gui.backend.gesture_trace import GestureTrace
            trace = GestureTrace(window, Path(folder.name)/'trace.jsonl')
        # Both settled reuse and recapture beyond the 192-point margin are exercised.
        orders = [('drag', 'pinch', 'wheel', 'scroll', 'drag'),
                  ('wheel', 'drag', 'scroll', 'pinch', 'drag'),
                  ('pinch', 'scroll', 'drag', 'wheel', 'drag')]
        for repetition, order in enumerate(orders, 1):
            for name in order:
                centre = plan.mapToScene(QPointF(plan.width()/2, plan.height()/2)).toPoint()
                QTest.mouseMove(window, centre, 0)
                before = tuple(plan.property(k) for k in ('panX', 'panY', 'zoom'))
                print('START', repetition, name, flush=True)
                steps = gestures(window, plan)[name]
                if software and name != 'wheel':
                    # Keep begin/end and pan/zoom reversals, with fewer
                    # intermediate software frames. Hardware uses every event.
                    steps = [steps[0], *steps[1:-1:4], steps[-1]]
                if observer == 'benchmark':
                    result = measure(app, window, steps, plan)
                    assert result['camera_events'] >= (result['events']-2)*.8, result
                    assert result['frame_clock'] == 'gui_delivery', result
                    assert result['sync_cpu_ms'] is None, result
                    print('DONE', repetition, name, flush=True)
                    continue
                moved = False
                for delay, send in steps:
                    QTest.qWait(delay)  # wait: the gesture's own rhythm, the thing measured
                    send()
                    moved |= tuple(plan.property(k) for k in ('panX', 'panY', 'zoom')) != before
                assert _setup.wait_until(app, lambda: plan.property('pendingMotion') is None, 5)
                assert moved, (name, before)
                assert _setup.wait_until(app, lambda: not plan.property('motionActive'), 5)
                camera = tuple(plan.property(k) for k in ('panX', 'panY', 'zoom'))
                QTest.qWait(160)  # wait: the plan must stay still for this long after the motion
                assert tuple(plan.property(k) for k in ('panX', 'panY', 'zoom')) == camera
                print('DONE', repetition, name, flush=True)
        if trace:
            trace.flush()
            rows = [json.loads(line) for line in (Path(folder.name)/'trace.jsonl').read_text().splitlines()]
            frames = [row for row in rows if row['record'] == 'frame']
            assert frames, rows
            if not trace.direct_timing:
                assert all(not row['timing_available'] and row['sync_ms'] is None
                           and row['render_thread'] is None for row in frames), frames
    finally:
        if trace:
            trace.close()
        folder.cleanup()
        window.close()
        controller.close()
        window.deleteLater()
        engine.deleteLater()
        # Deferred deletion of a threaded window also needs an event loop which
        # releases the GIL, rather than synchronous sendPostedEvents from Python.
        QTimer.singleShot(100, app.quit)
        app.exec()


class MotionLiveness(unittest.TestCase):
    def test_repeated_middle_drags_alternate_with_pinch_wheel_and_scroll(self):
        self.check_sequence('benchmark')

    def test_the_optional_trace_does_not_block_mixed_gestures(self):
        self.check_sequence('trace')

    def check_sequence(self, observer):
        # A GUI timer cannot interrupt a sendEvent stuck in Qt: the parent owns the deadline.
        with tempfile.TemporaryDirectory(prefix='meridiana-motion-deadline-', ignore_cleanup_errors=True) as name:
            folder = Path(name)
            with (folder/'progress.log').open('w', encoding='utf8') as log:
                child = subprocess.Popen([sys.executable, '-u', str(Path(__file__).resolve()),
                                          '--exercise', observer, str(folder/'pid')],
                                         cwd=_setup.HERE, env=dict(os.environ), stdout=log,
                                         stderr=subprocess.STDOUT)
                timed_out = False
                try:
                    child.wait(timeout=70)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    if os.name == 'nt' and (folder/'pid').exists():
                        # The venv's Windows redirector has a different PID from its interpreter.
                        import ctypes
                        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
                        kernel.OpenProcess.restype = ctypes.c_void_p
                        kernel.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint]
                        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
                        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
                        handle = kernel.OpenProcess(0x100001, False, int((folder/'pid').read_text()))
                        if handle:
                            kernel.TerminateProcess(handle, 124)
                            kernel.WaitForSingleObject(handle, 5000)
                            kernel.CloseHandle(handle)
                    child.kill()
                    child.wait(timeout=5)
            output = (folder/'progress.log').read_text(encoding='utf8', errors='replace')
            self.assertFalse(timed_out, f'mixed gestures blocked for 70 s; progress:\n{output}')
            self.assertEqual(child.returncode, 0, output)
            self.assertEqual(output.count('DONE'), 15, output)


if __name__ == '__main__':
    if '--exercise' in sys.argv:
        import faulthandler
        faulthandler.enable()
        Path(sys.argv[-1]).write_text(str(os.getpid()), encoding='ascii')
        faulthandler.dump_traceback_later(55)
        exercise(sys.argv[-2])
        faulthandler.cancel_dump_traceback_later()
    else:
        unittest.main()
