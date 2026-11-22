"""How smooth the views are under the gestures a user makes: python tools/measure_plan_motion.py PROJECT --out FILE.

Daniel 17/11/2026, on the Linux laptop: zoom in and out and moving inside the views are slow, «in particolar modo in
Impianto nel 2D, in particolar modo quando ci sono molti moduli». A real window (on the session's own platform when
QT_QPA_PLATFORM is set, offscreen otherwise), large, in the phase and the view asked, with the map when `--maps`; then
the gestures one after the other, each at the pace of the device that makes it:

- wheel: ten notches of a mouse wheel, 100 ms apart, in and out;
- pinch: a touchpad's pinch, in and out, 60 steps at 8 ms (the zoom gesture of a touchpad);
- scroll: two fingers on a touchpad, 60 steps at 8 ms with their scroll phases (the pan of a touchpad);
- drag: the middle button held and moved for a second, a move every 8 ms.

For each: the frames drawn and the time between them (median, 95th percentile, worst), how long the window took to
handle each event, and where the window's thread was (sampled every 5 ms). Frame times are Qt's frameSwapped,
not the screen's latency. The project file is read only (its SHA-256 is checked before and after).
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
os.environ['PYTHONPATH'] = os.pathsep.join(sys.path[:2])   # the year's own process finds the program too
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import _setup  # noqa: E402  (the paths and the isolated profile, before Qt)
from PySide6.QtCore import QObject, QPoint, QPointF, Qt, QTimer  # noqa: E402
from PySide6.QtGui import (QInputDevice, QMouseEvent, QNativeGestureEvent, QPointingDevice,  # noqa: E402
                           QWheelEvent)
from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from meridiana.core.model.model import Project  # noqa: E402
from meridiana.gui.application import QuickWindow, create_app  # noqa: E402

TOUCHPAD = None


def touchpad():
    global TOUCHPAD
    if TOUCHPAD is None:
        TOUCHPAD = QPointingDevice('measure touchpad', 9001, QInputDevice.DeviceType.TouchPad,
                                   QPointingDevice.PointerType.Finger,
                                   QInputDevice.Capability.Position | QInputDevice.Capability.Scroll, 5, 0)
    return TOUCHPAD


def gestures(window, view):
    """Each gesture as a list of (delay in ms before it, a function sending one event)."""
    middle = view.mapToScene(QPointF(view.width() / 2, view.height() / 2))
    glob = QPointF(window.mapToGlobal(middle.toPoint()))

    def wheel(delta):
        return lambda: QCoreApplication.sendEvent(window, QWheelEvent(
            middle, glob, QPoint(), QPoint(0, delta), Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False))

    def scroll(dx, dy, phase):
        return lambda: QCoreApplication.sendEvent(window, QWheelEvent(
            middle, glob, QPoint(dx, dy), QPoint(dx * 2, dy * 2), Qt.NoButton, Qt.NoModifier, phase, False,
            Qt.MouseEventNotSynthesized, touchpad()))

    def pinch(kind, value):
        return lambda: QCoreApplication.sendEvent(window, QNativeGestureEvent(
            kind, touchpad(), 2, middle, middle, glob, value, QPointF(), 0))

    def mouse(kind, at, buttons):
        point = QPointF(middle.x() + at[0], middle.y() + at[1])
        if kind == QMouseEvent.Type.MouseButtonPress:
            return lambda: QTest.mousePress(window, Qt.MiddleButton, Qt.NoModifier, point.toPoint(), 0)
        if kind == QMouseEvent.Type.MouseButtonRelease:
            return lambda: QTest.mouseRelease(window, Qt.MiddleButton, Qt.NoModifier, point.toPoint(), 0)
        return lambda: QCoreApplication.sendEvent(window, QMouseEvent(
            kind, point, point, QPointF(window.mapToGlobal(point.toPoint())), Qt.NoButton, buttons, Qt.NoModifier))

    plan = dict(
        wheel=[(100, wheel(120 if i < 5 else -120)) for i in range(10)],
        pinch=[(8, pinch(Qt.NativeGestureType.BeginNativeGesture, 0))]
        + [(8, pinch(Qt.NativeGestureType.ZoomNativeGesture, 0.02 if i < 30 else -0.02)) for i in range(60)]
        + [(8, pinch(Qt.NativeGestureType.EndNativeGesture, 0))],
        scroll=[(8, scroll(0, 0, Qt.ScrollBegin))]
        + [(8, scroll(6 if i < 30 else -6, 4 if i < 30 else -4, Qt.ScrollUpdate)) for i in range(60)]
        + [(8, scroll(0, 0, Qt.ScrollEnd))],
        drag=[(8, mouse(QMouseEvent.Type.MouseButtonPress, (0, 0), Qt.MiddleButton))]
        + [(8, mouse(QMouseEvent.Type.MouseMove, (4 * i if i < 60 else 4 * (120 - i), 2 * i if i < 60 else 2 * (120 - i)),
                     Qt.MiddleButton)) for i in range(120)]
        + [(8, mouse(QMouseEvent.Type.MouseButtonRelease, (0, 0), Qt.NoButton))],
    )
    return plan


def measure(app, window, steps, view=None, probe=None):
    stamps, handled, sent = [], [], []
    samples = Counter()
    stopped = threading.Event()
    gui_thread = threading.get_ident()

    def sample_gui():
        while not stopped.wait(.005):
            frame = sys._current_frames().get(gui_thread)
            if frame:
                samples[f'{Path(frame.f_code.co_filename).name}:{frame.f_lineno}:{frame.f_code.co_name}'] += 1

    def frame():
        stamps.append(time.perf_counter())

    # Python must not run on the threaded renderer: synchronous mouse delivery can
    # wait for it while holding the GIL. Only RenderControl runs these clocks on
    # this thread. Queued callbacks cannot stand in for render-thread timings.
    render_stamps, render_frames = {}, []
    links = []
    def mark(name):
        def callback():
            render_stamps[name] = time.perf_counter()
        return callback
    for signal, name in (((window.beforeFrameBegin, 'begin'), (window.beforeSynchronizing, 'sync'),
                         (window.afterSynchronizing, 'synced'), (window.beforeRendering, 'render'),
                         (window.afterRendering, 'rendered')) if probe else ()):
        callback = mark(name)
        signal.connect(callback, Qt.DirectConnection)
        links.append((signal, callback))
    def ended():
        end = time.perf_counter()
        if all(k in render_stamps for k in ('begin', 'sync', 'synced', 'render', 'rendered')):
            render_frames.append(dict(time=end,
                sync_cpu_ms=(render_stamps['synced']-render_stamps['sync'])*1000,
                render_cpu_ms=(render_stamps['rendered']-render_stamps['render'])*1000,
                render_frame_cpu_ms=(end-render_stamps['begin'])*1000))
    if probe:
        window.afterFrameEnd.connect(ended, Qt.DirectConnection)
        links.append((window.afterFrameEnd, ended))

    pending = list(steps)
    moved = 0

    def camera():
        if view is None:
            return None
        goal = view.property('pendingMotion')
        if hasattr(goal, 'toVariant'):
            goal = goal.toVariant()
        return tuple(goal[name] for name in ('x', 'y', 'zoom')) if goal else tuple(
            view.property(name) for name in ('panX', 'panY', 'zoom'))

    def next_step():
        nonlocal moved
        if not pending:
            return
        _, send = pending.pop(0)
        before = camera()
        start = time.perf_counter()
        sent.append(start)
        send()
        handled.append((time.perf_counter() - start) * 1000)
        if view is not None and camera() != before:
            moved += 1
        if pending:
            timer.start(pending[0][0])

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(next_step)
    window.frameSwapped.connect(frame, Qt.QueuedConnection)
    render_timer = QTimer()
    render_timer.setTimerType(Qt.PreciseTimer)
    def draw():
        probe.render()
        frame()
    if probe:
        probe.samples.clear()
        render_timer.timeout.connect(draw)
        render_timer.start(8)
    sampler = threading.Thread(target=sample_gui, daemon=True)
    sampler.start()
    timer.start(steps[0][0])
    try:
        if not _setup.wait_until(app, lambda: not pending and not timer.isActive(), 120):
            raise TimeoutError('the gesture did not finish')
        _setup.turn_events(app, 700)
    finally:
        timer.stop()
        render_timer.stop()
        stopped.set()
        sampler.join()
        window.frameSwapped.disconnect(frame)
        for signal, callback in links:
            signal.disconnect(callback)
    span = (sent[-1] - sent[0]) * 1000
    stamps = [t for t in stamps if sent[0] <= t <= sent[-1] + .1]
    intervals = sorted((b - a) * 1000 for a, b in zip(stamps, stamps[1:], strict=False))
    result = dict(events=len(sent), camera_events=moved if view is not None else None,
                frame_clock='render_control' if probe else 'gui_delivery',
                span_ms=round(span, 1), frames=len(stamps),
                frame_median_ms=round(statistics.median(intervals), 1) if intervals else None,
                frame_p95_ms=round(intervals[int(.95 * (len(intervals) - 1))], 1) if intervals else None,
                frame_worst_ms=round(intervals[-1], 1) if intervals else None,
                handle_median_ms=round(statistics.median(handled), 2), handle_worst_ms=round(max(handled), 2),
                gui_samples=samples.most_common(12))
    if probe:
        active_samples = [s for s in probe.samples if sent[0] <= s['time'] <= sent[-1]]
        for key in ('polish_ms', 'sync_ms', 'render_ms', 'submit_ms', 'draw_ms', 'gpu_ms'):
            values = sorted(s[key] for s in active_samples if s[key] is not None)
            result[key] = dict(median=round(statistics.median(values), 3),
                               p95=round(values[int(.95*(len(values)-1))], 3),
                               worst=round(max(values), 3)) if values else None
    else:
        for key in ('sync_cpu_ms', 'render_cpu_ms', 'render_frame_cpu_ms'):
            values = sorted(s[key] for s in render_frames if sent[0] <= s['time'] <= sent[-1])
            result[key] = dict(median=round(statistics.median(values), 3),
                               p95=round(values[int(.95*(len(values)-1))], 3),
                               worst=round(max(values), 3)) if values else None
    return result


def run(args):
    if args.render_control:
        return run_render_control(args)
    from meridiana.gui.sample import recorded_weather
    digest = hashlib.sha256(args.project.read_bytes()).hexdigest()
    app = create_app()
    if app.platformName() != 'offscreen':
        screen = os.environ.get('MERIDIANA_TEST_SCREEN', '')
        if not screen.isdigit() or int(screen) >= len(app.screens()):
            raise RuntimeError('set MERIDIANA_TEST_SCREEN to an available test screen')
        _setup._windows_on_screen(app)
    print(f'Loaded Qt on {app.platformName()}', flush=True)
    with tempfile.TemporaryDirectory(prefix='meridiana-motion-') as folder:
        cache = Path(folder)
        project, notice = Project.load(args.project, cache)
        report = dict(project=args.project.name, project_sha256=digest, notice=notice, platform=app.platformName(),
                      phase=args.phase, maps=args.maps, cases=[],
                      render_cpu_timing_available=False)
        # laid out and computed as the user has it (the strings and the inverters on the plan), with recorded weather
        recorded_weather(project, cache, ROOT / 'tests/calcoli/riferimenti/pvgis53-tmy-rho.json.gz')
        host = QuickWindow(project, cache, real_views=True, theme={'reducedMotion': True})
        print('Created the benchmark window and isolated profile', flush=True)
        try:
            host.bridge.recompute()
            if not _setup.wait_until(app, lambda: not host.bridge.busy and host.bridge._layout is None
                                     and bool(host.bridge.session.energy.get('sim')), 600):
                raise TimeoutError(f'the year was not computed: {host.bridge.error}')
            if not args.maps:
                host.plan.configureMaps({'offline': True})
            window = host.window
            if app.platformName() != 'offscreen':
                window.setScreen(app.screens()[int(screen)])
                window.setGeometry(app.screens()[int(screen)].availableGeometry())
            if app.platformName() == 'offscreen':
                window.resize(1600, 1000)
                window.show()
            else:
                window.showMaximized()
            _setup.turn_events(app, 3000)
            window.showPhase(args.phase)
            _setup.turn_events(app, 2000)
            for mode in args.views:
                window.setProperty('viewMode', mode)
                name = 'viewport3d' if mode == '3d' else 'plan'
                _setup.wait_until(app, lambda name=name: window.findChild(QObject, name) is not None, 30)
                view = window.findChild(QObject, name)
                if mode == '3d':
                    _setup.wait_until(app, lambda: not host.scene.drawing, 90)
                def laid():   # what the plan draws (its `paintedModules`), which the 3D shares
                    plan = window.findChild(QObject, 'plan')
                    return int(plan.property('paintedModules') or 0) if plan is not None else 0
                # the modules laid before anything is measured: a plan without them is not what the user moves
                if not _setup.wait_until(app, lambda: laid() > 0 and not host.bridge.busy, 180):
                    raise TimeoutError('the modules were not laid')
                _setup.turn_events(app, 4000 if args.maps else 2000)   # the tiles arrive
                modules = laid()
                for gesture, steps in gestures(window, view).items():
                    if args.only and gesture not in args.only:
                        continue
                    for repetition in range(args.repetitions):
                        if gesture == 'drag':
                            # Initialise Qt's mouse position after native gestures; an uninitialised first drag can
                            # otherwise deliver moves without moving the camera and look spuriously inexpensive.
                            centre = view.mapToScene(QPointF(view.width()/2, view.height()/2)).toPoint()
                            QTest.mouseMove(window, centre)
                            app.processEvents()
                        case = measure(app, window, steps, view if mode == 'plan' else None)
                        if mode == 'plan' and case['camera_events'] < len(steps)*.8:
                            raise AssertionError(f"{gesture}: only {case['camera_events']}/{len(steps)} events moved the plan")
                        case.update(view=mode, gesture=gesture, repetition=repetition + 1, modules=modules,
                                    size=[window.width(), window.height()], dpr=window.devicePixelRatio())
                        report['cases'].append(case)
                        print(f"{mode:5} {gesture:6} #{repetition + 1}: frames {case['frames']:4}  median "
                              f"{case['frame_median_ms']} ms  p95 {case['frame_p95_ms']} ms  worst {case['frame_worst_ms']} "
                              f"ms  event {case['handle_median_ms']}/{case['handle_worst_ms']} ms", flush=True)
                        _setup.turn_events(app, 1000)
            report['graphics_api'] = str(window.rendererInterface().graphicsApi())
            report['screen'] = window.screen().name()
            report['window_position'] = [window.x(), window.y()]
            report['warnings'] = host.warnings[-20:]
        finally:
            host.close()
    if hashlib.sha256(args.project.read_bytes()).hexdigest() != digest:
        raise AssertionError('the project file changed')
    return report


def run_render_control(args):
    """The actual Plan component and saved wiring, without computing an unrelated energy year."""
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
    from meridiana.app import jobs
    from meridiana.gui.backend.plan import PlanController
    from plan_render_probe import PlanRenderProbe
    if args.views != ['plan']:
        raise ValueError('--render-control requires --views plan')
    digest = hashlib.sha256(args.project.read_bytes()).hexdigest()
    app = create_app()
    with tempfile.TemporaryDirectory(prefix='meridiana-gpu-motion-') as folder:
        project, notice = Project.load(args.project, Path(folder))
        results, keys, _ = jobs.layout_of(project)
        controller = PlanController(project, manage_layout=False, cache=Path(folder))
        controller.session.layout_done(controller.session.generation, results, keys)
        controller.setPhase(args.phase)
        controller.setNavigation('autocad')
        controller.configureMaps({'offline': not args.maps or args.fixture_tiles})
        if args.fixture_tiles:
            controller.configureMaps({'source': 'osm'})
        engine = QQmlApplicationEngine()
        controller.install(engine)
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(
            ROOT / 'src/meridiana/gui/qml/Meridiana/Plan/Plan.qml')))
        view = component.createWithInitialProperties({'backend': controller})
        if view is None:
            raise RuntimeError([e.toString() for e in component.errors()])
        probe = PlanRenderProbe(view)
        if args.layer_samples is not None:
            from PySide6.QtQml import QQmlProperty
            # the geometry's one image holds the samples since R706 (it was the surface's own layer)
            surface = view.findChild(QObject, 'motionSnapshot')
            QQmlProperty.write(surface, 'samples', args.layer_samples)
        timer = QTimer()
        timer.timeout.connect(probe.render)
        timer.start(8)
        try:
            view.fit()
            _setup.turn_events(app, 2500)
            view.fit()
            _setup.turn_events(app, 600)
            if args.maps:
                _setup.turn_events(app, 4000)
            if args.fixture_tiles:
                from PySide6.QtGui import QColor, QImage, QPainter
                tile = QImage(256, 256, QImage.Format_RGB32)
                tile.fill(QColor('#506149'))
                painter = QPainter(tile)
                painter.setPen(QColor('#a8a397'))
                for at in range(0, 256, 16):
                    painter.drawLine(at, 0, 255, 255-at)
                painter.end()
                for key in list(controller.maps.state.wanted | controller.maps.state.backdrop):
                    controller.maps._ready(*key, tile)
                _setup.turn_events(app, 1400)
            timer.stop()
            picture = probe.render(readback=True)
            if picture.isNull():
                raise RuntimeError('the hardware target returned no pixels')
            picture.save(str(args.out.with_suffix('.png')))
            driver_info = probe.rhi.driverInfo()
            report = dict(project=args.project.name, project_sha256=digest, notice=notice,
                          platform=app.platformName(), phase=args.phase, maps=args.maps or args.fixture_tiles,
                          graphics_api=str(probe.window.rendererInterface().graphicsApi()),
                          render_control=True, driver=bytes(driver_info.deviceName).decode(), cases=[])
            report['map_tiles'] = controller.maps.tileModel.rowCount() if controller.maps is not None else 0
            report['map_tile_keys'] = len(controller.maps.state.loaded.keys() | controller.maps.state.under.keys()) \
                if controller.maps is not None else 0
            report['fixture_tiles'] = args.fixture_tiles
            for gesture, steps in gestures(probe.window, view).items():
                if args.only and gesture not in args.only:
                    continue
                for repetition in range(args.repetitions):
                    if gesture == 'drag':
                        centre = view.mapToScene(QPointF(view.width()/2, view.height()/2)).toPoint()
                        QTest.mouseMove(probe.window, centre, 0)
                        app.processEvents()
                    case = measure(app, probe.window, steps, view, probe)
                    case.update(view='plan', gesture=gesture, repetition=repetition+1,
                                modules=view.property('paintedModules'), size=[1434, 839], dpr=2)
                    if case['camera_events'] < len(steps)*.8:
                        raise AssertionError(f'{gesture}: inactive benchmark: {case}')
                    report['cases'].append(case)
                    print(f'{gesture}: draw {case["draw_ms"]}, GPU {case["gpu_ms"]}', flush=True)
                    timer.start(8)
                    _setup.turn_events(app, 1500)
                    timer.stop()
            if args.visuals:
                report['visuals'] = visual_probe(app, view, probe)
        finally:
            timer.stop()
            probe.close()
            controller.close()
            engine.deleteLater()
            app.processEvents()
    if hashlib.sha256(args.project.read_bytes()).hexdigest() != digest:
        raise AssertionError('the project file changed')
    return report


def visual_probe(app, view, probe):
    from plan_render_probe import image_motion
    camera = lambda: tuple(view.property(name) for name in ('panX', 'panY', 'zoom'))
    previous, old = probe.render(readback=True), camera()
    frames = []
    for step in range(12):
        view.zoomBy(1.015 if step < 6 else 1/1.015, 700., 400.)
        _setup.turn_events(app, 20)
        probe.render()
        current, now = probe.render(readback=True), camera()
        frames.append(image_motion(previous, current, old, now))
        previous, old = current, now
    # Keep rendering during the fade. Pixel registration is computed afterwards so
    # its CPU cost cannot turn a continuous transition into a single late screenshot.
    early, early_camera = probe.render(readback=True), camera()
    captures = [(early, early_camera)]
    for _ in range(50):
        _setup.turn_events(app, 20)
        captures.append((probe.render(readback=True), camera()))
    late, late_camera = captures[-1]
    transitions = [image_motion(a[0], b[0], a[1], b[1])
                   for a, b in zip(captures, captures[1:], strict=False)]
    return dict(frames=frames, settlement_frames=transitions,
                settled=image_motion(early, late, early_camera, late_camera),
                settled_camera_drift=[b-a for a, b in zip(early_camera, late_camera, strict=True)])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('project', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--phase', default='plant', choices=('model', 'plant'))
    parser.add_argument('--views', nargs='+', default=['plan', '3d'], choices=('plan', '3d'))
    parser.add_argument('--only', nargs='*', choices=('wheel', 'pinch', 'scroll', 'drag'))
    parser.add_argument('--maps', action='store_true', help='the map tiles from the network, as in daily use')
    parser.add_argument('--render-control', action='store_true', help='hardware D3D11 texture at 1434x839, DPR 2, no window')
    parser.add_argument('--visuals', action='store_true', help='separate pixel registration pass, requires --render-control')
    parser.add_argument('--layer-samples', type=int, help='diagnostic override of plan MSAA samples')
    parser.add_argument('--fixture-tiles', action='store_true', help='deterministic decoded map tiles, no network')
    parser.add_argument('--repetitions', type=int, default=2)
    arguments = parser.parse_args()
    if arguments.out.exists():
        raise FileExistsError(arguments.out)
    answer = run(arguments)
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    with arguments.out.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(answer, stream, indent=2)
