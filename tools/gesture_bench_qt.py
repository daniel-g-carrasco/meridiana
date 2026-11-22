"""Qt adapter of gesture_bench. Input, frame observation and pixels have distinct passes."""
from collections import Counter
import gc
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace

from gesture_bench_core import GESTURES, VERSION, analyze, gesture_steps


def initialize(args):
    root = args.source_root.resolve()
    sys.path[:0] = [str(root/'src'), str(root/'tests')]
    os.environ['PYTHONPATH'] = os.pathsep.join(sys.path[:2])
    os.environ['QT_QPA_PLATFORM'] = args.platform or (('windows' if os.name == 'nt' else 'wayland') if args.live else 'offscreen')
    os.environ['QT_QUICK_BACKEND'] = args.backend
    os.environ['QSG_RHI_BACKEND'] = args.api
    os.environ['MERIDIANA_PRELOAD'] = '0'
    os.environ['MERIDIANA_TRACE_GESTURES'] = ''
    if args.scale:
        os.environ['QT_SCALE_FACTOR'] = str(args.scale)
    import _setup
    from gesture_bench import isolate_profile
    isolate_profile(_setup)
    if getattr(args, 'qsg', False):
        os.environ['QSG_RENDER_TIMING'] = '1'
    from PySide6.QtQuick import QQuickGraphicsConfiguration, QQuickWindow
    if getattr(args, 'qml_profile', False):
        from PySide6.QtQml import QQmlDebuggingEnabler
        QQmlDebuggingEnabler.enableDebugging(True)
        if not QQmlDebuggingEnabler.startTcpDebugServer(3768, QQmlDebuggingEnabler.DoNotWaitForClient, '127.0.0.1'):
            raise RuntimeError('this Qt build cannot start the QML profiler connector')
    config = QQuickGraphicsConfiguration()
    config.setTimestamps(True)
    QQuickWindow.setDefaultAlphaBuffer(True)
    from meridiana.gui.application import create_app
    app = create_app()
    # Refuse the main screen, including a missing requested secondary screen.
    if app.platformName() != 'offscreen':
        allow_primary = getattr(args, 'allow_primary_screen', False)
        if allow_primary and os.name == 'nt':
            raise ValueError('the Windows benchmark never uses the primary screen')
        wanted = os.environ.get('MERIDIANA_TEST_SCREEN', '0' if allow_primary else '')
        if not wanted.isdigit() or int(wanted) >= len(app.screens()) or (not allow_primary and app.screens()[int(wanted)] == app.primaryScreen()):
            raise RuntimeError('live benchmarks require an existing non-primary MERIDIANA_TEST_SCREEN')
        os.environ['MERIDIANA_TEST_SCREEN'] = wanted
    return root, _setup, app, config


def variant(value):
    return value.toVariant() if hasattr(value, 'toVariant') else value


def find(window, name):
    from PySide6.QtCore import QObject
    found = window.findChild(QObject, name)
    if found is not None:
        return found
    pending = [window.contentItem()]
    while pending:
        item = pending.pop()
        if item.objectName() == name:
            return item
        pending.extend(item.childItems())
    return None


def camera(view):
    if view is None:
        return None
    if view.objectName() == 'viewport3d':
        state = variant(view.property('cameraState')) or {}
        result = {}
        for key, value in state.items():
            if isinstance(value, (int, float)):
                result[key] = value
            elif isinstance(value, list):
                result.update({f'{key}{i}': v for i, v in enumerate(value) if isinstance(v, (int, float))})
        return result
    return {key: variant(view.property(key)) for key in ('panX', 'panY', 'zoom', 'bearing')
            if view.property(key) is not None} | {'goal': variant(view.property('pendingMotion'))}


class Frames:
    def __init__(self, window, state):
        from PySide6.QtCore import Qt
        self.window, self.state = window, state
        self.rows, self.times, self.links = [], {}, []
        self.gui_ms = 0.
        self.frame_gui_ms = 0.
        self.frame_state = None
        self.gui_state = None
        self.swapchain = None
        self.gpu_error = None
        self.gpu_info = {}
        self.anim_ns = None
        for signal, callback in ((window.beforeFrameBegin, self.begin), (window.beforeSynchronizing, self.sync),
                                 (window.afterSynchronizing, self.synced), (window.beforeRendering, self.render),
                                 (window.afterRendering, self.rendered), (window.afterFrameEnd, self.end),
                                 (window.frameSwapped, self.swapped), (window.afterAnimating, self.animated)):
            signal.connect(callback, Qt.DirectConnection)
            self.links.append((signal, callback))

    def animated(self):
        self.anim_ns = time.perf_counter_ns()
        # Never convert a QJSValue on the render thread: it belongs to the GUI engine.
        self.gui_state = self.state()

    def begin(self):
        self.times = {'begin': time.perf_counter_ns()}

    def sync(self):
        self.times['sync'] = time.perf_counter_ns()
        self.frame_state = self.gui_state
        self.frame_gui_ms, self.gui_ms = self.gui_ms, 0.

    def synced(self):
        self.times['synced'] = time.perf_counter_ns()

    def render(self):
        self.times['render'] = time.perf_counter_ns()

    def rendered(self):
        self.times['rendered'] = time.perf_counter_ns()
        self.gpu_ms = None
        try:
            from PySide6.QtQuick import QSGRendererInterface
            from PySide6.QtGui import QRhiSwapChain
            import shiboken6
            if self.swapchain is None:
                ptr = self.window.rendererInterface().getResource(self.window, QSGRendererInterface.RhiSwapchainResource)
                self.gpu_info = dict(swapchain_exposed=bool(ptr), timestamps_requested=self.window.graphicsConfiguration().timestampsEnabled())
                if ptr:
                    self.swapchain = shiboken6.wrapInstance(int(ptr), QRhiSwapChain)
                else:
                    self.gpu_error = 'Qt did not expose the window swapchain'
            if self.swapchain:
                value = self.swapchain.currentFrameCommandBuffer().lastCompletedGpuTime()*1000
                self.gpu_ms = value if value > 0 else None
        except (TypeError, AttributeError, RuntimeError) as error:
            self.gpu_error = str(error)

    def end(self):
        t = self.times
        if not all(k in t for k in ('begin', 'sync', 'synced', 'render', 'rendered')):
            return
        self.rows.append(dict(version=VERSION, record='frame', t_ns=time.perf_counter_ns(), sync_ns=t['sync'],
                              camera=self.frame_state, gui_events_ms=self.frame_gui_ms,
                              sync_ms=(t['synced']-t['sync'])/1e6, render_ms=(t['rendered']-t['render'])/1e6,
                              render_frame_ms=(time.perf_counter_ns()-t['begin'])/1e6,
                              gui_prepare_ms=(t['sync']-self.anim_ns)/1e6 if self.anim_ns else None,
                              animation_ms=None, polish_ms=None, gpu_ms=getattr(self, 'gpu_ms', None)))

    def swapped(self):
        now = time.perf_counter_ns()
        if self.window.rendererInterface().graphicsApi().name == 'Software':
            self.rows.append(dict(version=VERSION, record='frame', t_ns=now, camera=self.state(),
                                  gui_events_ms=self.gui_ms, sync_ms=None, render_ms=None, gpu_ms=None))
            self.gui_ms = 0.
        self.rows.append(dict(version=VERSION, record='swap', t_ns=now))

    def close(self):
        for signal, callback in self.links:
            signal.disconnect(callback)


class Input:
    def __init__(self, app, host, view):
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QInputDevice, QPointingDevice
        self.app, self.host, self.window, self.view = app, host, host.window, view
        self.device = QPointingDevice('benchmark touchpad', 9001, QInputDevice.TouchPad, QPointingDevice.Finger,
                                      QInputDevice.Position | QInputDevice.Scroll, 5, 0)
        self.center = view.mapToScene(QPointF(view.width()/2, view.height()/2))

    def send(self, step):
        from PySide6.QtCore import QCoreApplication, QEvent, QPoint, QPointF, Qt
        from PySide6.QtGui import QKeyEvent, QMouseEvent, QNativeGestureEvent, QPointingDevice, QWheelEvent
        local = self.center+QPointF(step.get('x', 0), step.get('y', 0))
        glob = QPointF(self.window.mapToGlobal(local.toPoint()))
        action = step['action']
        if action in ('wheel', 'scroll'):
            phase = {'begin': Qt.ScrollBegin, 'update': Qt.ScrollUpdate, 'momentum': Qt.ScrollMomentum,
                     'end': Qt.ScrollEnd}.get(step.get('phase'), Qt.NoScrollPhase)
            pixels = QPoint(step.get('dx', 0), step.get('dy', 0))
            angle = QPoint(0, step.get('angle', 0))
            event = QWheelEvent(local, glob, pixels, angle, Qt.NoButton, Qt.NoModifier, phase, False,
                                Qt.MouseEventNotSynthesized, self.device if action == 'scroll' else QPointingDevice.primaryPointingDevice())
            QCoreApplication.sendEvent(self.window, event)
        elif action == 'native':
            kind = {'begin': Qt.BeginNativeGesture, 'update': Qt.ZoomNativeGesture, 'end': Qt.EndNativeGesture}[step['phase']]
            event = QNativeGestureEvent(kind, self.device, 2, local, local, glob, step['value'], QPointF(), 0)
            QCoreApplication.sendEvent(self.window, event)
        elif action in ('press', 'move', 'release'):
            button = {'left': Qt.LeftButton, 'right': Qt.RightButton, 'middle': Qt.MiddleButton}[step['button']]
            mods = Qt.ShiftModifier if step.get('orbit') else Qt.NoModifier
            if action == 'press':
                # QTest can turn the event loop while retaining the GIL, blocking render callbacks.
                QCoreApplication.sendEvent(self.window, QMouseEvent(QEvent.MouseMove, local, local, glob,
                                                                  Qt.NoButton, Qt.NoButton, mods))
                QCoreApplication.sendEvent(self.window, QMouseEvent(QEvent.MouseButtonPress, local, local, glob,
                                                                  button, button, mods))
            elif action == 'release':
                QCoreApplication.sendEvent(self.window, QMouseEvent(QEvent.MouseButtonRelease, local, local, glob,
                                                                  button, Qt.NoButton, mods))
            else:
                QCoreApplication.sendEvent(self.window, QMouseEvent(QEvent.MouseMove, local, local, glob,
                                                                  Qt.NoButton, button, mods))
        elif action == 'key':
            keys = {'+': Qt.Key_Plus, '-': Qt.Key_Minus, 'Right': Qt.Key_Right, 'Left': Qt.Key_Left,
                    'Up': Qt.Key_Up, 'Down': Qt.Key_Down}
            self.view.forceActiveFocus()
            for kind in (QEvent.KeyPress, QEvent.KeyRelease):
                QCoreApplication.sendEvent(self.window, QKeyEvent(kind, keys[step['key']], Qt.NoModifier, step['key']))
        else:
            raise ValueError(f'unsupported action: {action}')


def execute(app, window, observer, sender, steps, tail_ms, profile=False, pixels=False, grab=None, render=None,
            pixels_after_input=False):
    from PySide6.QtCore import QEventLoop, QTimer, Qt
    from PySide6.QtGui import QImage
    loop, timer, paint = QEventLoop(), QTimer(), QTimer()
    timer.setSingleShot(True)
    timer.setTimerType(Qt.PreciseTimer)
    # Request updates without inventing frame timestamps or using a device-rate render timer.
    paint.setInterval(1)
    paint.timeout.connect(render or window.requestUpdate)
    if render:
        paint.setInterval(8)
    stop, samples = threading.Event(), Counter()
    gui_thread = threading.get_ident()
    def sample():
        while not stop.wait(.005):
            frame = sys._current_frames().get(gui_thread)
            if frame:
                samples[f'{Path(frame.f_code.co_filename).name}:{frame.f_lineno}:{frame.f_code.co_name}'] += 1
    sampler = threading.Thread(target=sample, daemon=True)
    if profile:
        sampler.start()
    captured, pixel_timer = [], QTimer()
    pixel_timer.setInterval(20)
    def capture():
        start = time.perf_counter_ns()
        image = (grab() if grab else window.grabWindow()).convertToFormat(QImage.Format_RGBA8888)
        # Preserve independent X/Y grab scale: grabWindow DPR can be 1 at window DPR 2.5.
        if not image.isNull():
            import numpy as np
            rgba = np.frombuffer(image.bits(), dtype=np.uint8).reshape(image.height(), image.bytesPerLine())
            rgb = rgba[:, :image.width()*4].reshape(image.height(), image.width(), 4)[:, :, :3]
            captured.append((start, rgb[::4, ::4].copy(), observer.state(),
                             [image.width()/window.width(), image.height()/window.height()]))
    if pixels:
        pixel_timer.timeout.connect(capture)
        if not pixels_after_input:
            pixel_timer.start()
    start = time.perf_counter_ns()
    index, error = 0, []
    def tick():
        nonlocal index
        if window.property('benchmarkScreenLost'):
            error.append(RuntimeError('secondary screen disappeared; benchmark window was hidden'))
            loop.quit()
            return
        step = steps[index]
        before = observer.state()
        began = time.perf_counter_ns()
        try:
            sender.send(step)
        except Exception as exc:
            error.append(exc)
            loop.quit()
            return
        ended = time.perf_counter_ns()
        observer.gui_ms += (ended-began)/1e6
        delta = step.get('dy', 0) or step.get('angle', 0)
        deferred = getattr(sender, 'kind', '') in ('report-scroll', 'table-scroll') and bool(delta)
        observer.rows.append(dict(version=VERSION, record='event', t_ns=ended, started_ns=began,
                                  gesture=step['action'], requested=step, gui_ms=(ended-began)/1e6,
                                  lateness_ms=max(0, (began-start)/1e6-step['at_ms']),
                                  camera_before=before, camera_after=observer.state(),
                                  deferred_state=deferred, expected_direction=-1 if delta > 0 else 1))
        index += 1
        if index == len(steps):
            if pixels and pixels_after_input:
                pixel_timer.start()
            QTimer.singleShot(tail_ms, loop.quit)
        else:
            timer.start(max(0, math.ceil(steps[index]['at_ms']-(time.perf_counter_ns()-start)/1e6)))
    timer.timeout.connect(tick)
    timer.start(max(0, math.ceil(steps[0]['at_ms'])))
    paint.start()
    try:
        loop.exec()
    finally:
        timer.stop()
        paint.stop()
        pixel_timer.stop()
        stop.set()
        if profile:
            sampler.join()
    if error:
        raise error[0]
    return samples.most_common(30), captured


def memory(window=None):
    from meridiana.core.compute import procmem
    from PySide6.QtCore import QObject
    return dict(rss_bytes=procmem.rss(os.getpid(), tree=True), python_objects=len(gc.get_objects()),
                qt_objects=len(window.findChildren(QObject)) if window else None)


def run(args, cases):
    from gesture_bench import sha256, write_new
    root, setup, app, graphics_config = initialize(args)
    print('Qt initialized: '+app.platformName(), flush=True)
    if args.render_control:
        from gesture_bench_render import run as render_run
        return render_run(args, cases, app, setup)
    from meridiana.core.model.model import Project
    from meridiana.gui.application import QuickWindow
    digest = sha256(args.project) if args.project else None
    report = dict(version=VERSION, cases=[], environment=dict(platform=app.platformName(), screen_on=None,
                  screen_on_reason='display power state not available', backend=args.backend, api_requested=args.api,
                  source_root=str(root), label=args.label))
    native = None
    if args.qsg:
        from gesture_bench_qsg import NativeTimings
        native = NativeTimings()
    with tempfile.TemporaryDirectory(prefix='meridiana-gesture-cache-') as folder:
        cache = Path(folder)
        if args.year_cache_from:
            import shutil
            source = args.year_cache_from/'years'
            if not source.is_dir():
                raise ValueError('year-cache-from must contain a years directory')
            shutil.copytree(source, cache/'years')
        if args.project:
            project, notice = Project.load(args.project, cache)
            context = (project.resources.get('ifc_reference') or {}).get('context') or {}
            if context.get('mesh') and not Path(context['mesh']).exists():
                sidecar = args.project.with_suffix('.mesh.npz')
                if not sidecar.exists():
                    raise FileNotFoundError('IFC context mesh missing; regenerate this benchmark project')
                context['mesh'] = str(sidecar.resolve())
        else:
            from gesture_projects import generate
            project = generate(args.modules, args.seed)
            notice = None
        report.update(project_sha256=digest, notice=notice)
        from meridiana.app.platform import config
        isolated_config = config.Config(network_tiles=bool(args.maps and not args.fixture_tiles), network_pvgis=False)
        config.save(isolated_config, cache/'quick-profile/config/config.json')
        host = QuickWindow(project, cache, real_views=True, theme={'theme': args.theme, 'reducedMotion': False})
        # The application's normal recovery moves a lost window onto the primary screen.
        # A benchmark must instead hide immediately and fail, preserving the screen contract.
        host.keep_on_screen = lambda: None
        window = host.window
        window.setGraphicsConfiguration(graphics_config)
        try:
            host.bridge.configure_background(enabled=False)
            host.plan.configureMaps({'offline': not args.maps or args.fixture_tiles})
            if app.platformName() != 'offscreen':
                screen = app.screens()[int(os.environ['MERIDIANA_TEST_SCREEN'])]
                expected_screen = screen.name()
                window.screenChanged.connect(lambda screen: enforce_screen(window, expected_screen, app, screen, args.allow_primary_screen))
                window.setScreen(screen)
                area = screen.availableGeometry()
                window.setGeometry(area.x()+10, area.y()+10, min(args.size[0], area.width()-20), min(args.size[1], area.height()-20))
            else:
                window.resize(*args.size)
            window.show()
            if not setup.wait_until(app, lambda: find(window, 'plan') is not None, 60):
                raise TimeoutError('plan did not load')
            if not setup.wait_until(app, lambda: not host.bridge.busy and host.bridge._layout is None, 180):
                raise TimeoutError('layout did not settle')
            if args.year:
                from meridiana.gui.sample import recorded_weather
                if not recorded_weather(project, cache, root/'tests/calcoli/riferimenti/pvgis53-tmy-rho.json.gz'):
                    raise ValueError('no matching recorded weather: year benchmark refuses network access')
                from meridiana.core.energy import meteo
                horizon_source = root/'tests/calcoli/riferimenti/pvgis53-printhorizon-rho.json'
                horizon = json.loads(horizon_source.read_text(encoding='utf-8'))['outputs']['horizon_profile']
                selected = [r for r in horizon if r['A']+180 < 360]
                horizon_path = meteo._cache_file(cache, 'horizon', project.site.lat, project.site.lon)
                horizon_path.write_text(json.dumps(dict(fetched='2026-10-21', azimuth=[r['A']+180 for r in selected],
                                                        elevation=[r['H_hor'] for r in selected])), encoding='utf-8')
                print('Computing recorded year after layout', flush=True)
                host.bridge.recompute()
                if not setup.wait_until(app, lambda: not host.bridge.busy and host.bridge._layout is None
                                        and not host.bridge.session.telling(), 300):
                    raise TimeoutError('recorded computation did not settle: '+str(host.bridge.error))
                if not host.bridge.session.energy.get('sim'):
                    host.bridge.recompute()
                if not setup.wait_until(app, lambda: not host.bridge.busy and bool(host.bridge.session.energy.get('sim')), 300):
                    raise TimeoutError('recorded year did not finish: '+str(host.bridge.error))
                report['hours'] = len(host.bridge.session.energy['sim'].hourly)
            else:
                # QuickWindow's normal launcher asks for the first computation after show().
                # A layout-only benchmark must ask too; an idle fresh bridge has no modules.
                host.bridge._ask_layout()
                if not setup.wait_until(app, lambda: host.bridge._layout is None
                                        and host.bridge.session.layout_keys == host.bridge.session.expected_layout_keys()
                                        and not host.bridge.session.telling(), 180):
                    raise TimeoutError('initial benchmark layout did not settle: '+str(host.bridge.error))
            setup.turn_events(app, 1200)
            print('Layout ready; reading display power', flush=True)
            report['environment'].update(display_power(window))
            print('Display power query complete', flush=True)
            if args.fixture_tiles:
                from PySide6.QtGui import QColor, QImage
                tile = QImage(256, 256, QImage.Format_RGB32)
                tile.fill(QColor('#506149'))
                host.plan.configureMaps({'source': 'osm'})
                for key in list(host.plan.maps.state.wanted | host.plan.maps.state.backdrop):
                    host.plan.maps._ready(*key, tile)
                setup.turn_events(app, 400)
            report['environment'].update(graphics_api=str(window.rendererInterface().graphicsApi()),
                size=[window.width(), window.height()], dpr=window.devicePixelRatio(),
                screen=window.screen().name(), screen_refresh_hz=window.screen().refreshRate(),
                refresh_hz=args.refresh_hz or window.screen().refreshRate() or 60,
                screen_geometry=[window.screen().geometry().width(), window.screen().geometry().height()])
            report['modules'] = host.bridge.moduleCount
            for scenario in cases:
                window.showPhase(scenario['phase'])
                window.setProperty('viewMode', 'both' if scenario['view'] == 'split' else scenario['view'])
                name = 'viewport3d' if scenario['view'] == '3d' else 'plan'
                if not setup.wait_until(app, lambda name=name: find(window, name) is not None, 60):
                    raise TimeoutError(f'{name} did not load')
                view = find(window, name)
                if scenario['view'] == '3d':
                    if not setup.wait_until(app, lambda: not host.scene.drawing, 120):
                        raise TimeoutError('3D did not settle')
                    if (project.resources.get('ifc_reference') or {}).get('context'):
                        if not setup.wait_until(app, lambda: bool(host.scene.contextModels) or bool(host.scene.context.error), 180):
                            raise TimeoutError('IFC context did not reach the 3D viewer')
                        if host.scene.context.error:
                            raise RuntimeError('IFC context: '+host.scene.context.error)
                        report['ifc_context'] = dict(host.scene.context.info)
                setup.turn_events(app, 800)
                gestures = scenario['only'] or GESTURES
                for gesture in gestures:
                    window.showPhase(scenario['phase'])
                    window.setProperty('viewMode', 'both' if scenario['view'] == 'split' else scenario['view'])
                    setup.turn_events(app, 150)
                    view = find(window, name)
                    if gesture == 'orbit' and scenario['view'] == 'plan':
                        continue
                    from gesture_bench_core import UI_CASES
                    from gesture_bench_ui import evaluate, prepare
                    if gesture in UI_CASES:
                        sender, steps, state = prepare(app, host, view, gesture, scenario['seed'], scenario['rate'], scenario['duration'], setup)
                    else:
                        evaluate(view, 'fitScene()' if scenario['view'] == '3d' else 'fit()')
                        setup.turn_events(app, 300)
                        steps = gesture_steps(gesture, scenario['seed'], scenario['rate'], scenario['duration'])
                        sender = Input(app, host, view)
                        state = lambda view=view: camera(view)
                    initial = {k: variant(view.property(k)) for k in ('panX', 'panY', 'zoom', 'cameraState') if view.property(k) is not None}
                    observer = Frames(window, state)
                    before = memory(window)
                    try:
                        samples, _ = execute(app, window, observer, sender, steps, scenario['tail_ms'], args.profile)
                    finally:
                        observer.close()
                    if native:
                        native.merge(observer.rows)
                    ident = f"{scenario['phase']}-{scenario['view']}-{gesture}-s{scenario['seed']}-r{scenario['repetition']}"
                    raw = args.out.with_name(args.out.stem+'-'+ident+'.jsonl')
                    for seq, row in enumerate(observer.rows):
                        row['seq'] = seq+1
                    session = dict(version=VERSION, seq=0, record='session', t_ns=0, environment=report['environment'],
                                   case=ident, device_hz=args.rate, seed=scenario['seed'])
                    write_new(raw, '\n'.join(json.dumps(row, separators=(',', ':'), allow_nan=False)
                                            for row in [session, *observer.rows])+'\n')
                    analysis = analyze(observer.rows, report['environment']['refresh_hz'])
                    case = dict(id=ident, phase=scenario['phase'], view=scenario['view'], gesture=gesture,
                                seed=scenario['seed'], repetition=scenario['repetition'], raw=raw.name, analysis=analysis,
                                theme=args.theme, maps=args.maps, device_hz=args.rate, input_unchanged=True,
                                modules=host.bridge.moduleCount, duration_s=scenario['duration'], tail_ms=scenario['tail_ms'],
                                plan_modules=len(host.plan.modules), scene_modules=host.scene.moduleCount,
                                memory_before=before, memory_after=memory(window), gui_samples=samples,
                                gpu_error=observer.gpu_error, gpu_info=observer.gpu_info, pixel_pass=None)
                    case['project_sha256'] = digest
                    case['scenario'] = dict(theme=args.theme, maps=args.maps, scale=window.devicePixelRatio(),
                                            size=[window.width(), window.height()], device_hz=args.rate)
                    map_state = host.plan.maps.state
                    case['map_tiles'] = len(map_state.loaded)+len(map_state.under)
                    case['map_source'] = map_state.source
                    if args.visuals:
                        if native:
                            native.suspend()
                        from gesture_bench_visual import analyze_pixels
                        if gesture in UI_CASES:
                            window.showPhase(scenario['phase'])
                            sender, steps, state = prepare(app, host, view, gesture, scenario['seed'], scenario['rate'], scenario['duration'], setup)
                        else:
                            for key, value in initial.items():
                                evaluate(view, key+' = '+json.dumps(value))
                        setup.turn_events(app, 400)
                        # grabWindow waits for the render thread while PySide retains the GIL.
                        # A Python direct render callback would wait for that same GIL: deadlock.
                        # The pixel replay records input/state only, with no Python render callbacks.
                        pixel_observer = SimpleNamespace(state=state, rows=[], gui_ms=0.)
                        quiet_pixels = os.name == 'nt' and gesture in ('resize', 'resize-meridio')
                        _, captures = execute(app, window, pixel_observer, sender, steps, scenario['tail_ms'],
                                              pixels=True, pixels_after_input=quiet_pixels)
                        last = max((r['t_ns'] for r in pixel_observer.rows if r['record'] == 'event'), default=0)
                        case['pixel_pass'] = analyze_pixels(captures, last)
                        case['pixel_pass']['scope'] = 'settlement_only' if quiet_pixels else 'gesture_and_settlement'
                        if native:
                            native.resume()
                    report['cases'].append(case)
                    print(f"{ident}: {analysis['frames']} frames, p95={analysis['cadence']['p95_ms']}", flush=True)
                    setup.turn_events(app, 150)
            report['warnings'] = host.warnings[-30:]
        finally:
            if native:
                native.close()
            host.close()
            app.processEvents()
    if args.project and sha256(args.project) != digest:
        raise AssertionError('input project changed')
    return report


def enforce_screen(window, expected_name, app, screen, allow_primary=False):
    if screen is None or (not allow_primary and screen == app.primaryScreen()) or screen.name() != expected_name:
        window.setProperty('benchmarkScreenLost', True)
        window.hide()


def display_power(window):
    """DDC/CI power mode when the physical monitor exposes it; otherwise explicitly unknown."""
    if os.name != 'nt':
        return dict(screen_on=None, screen_on_reason='compositor does not expose panel power through Qt')
    import ctypes
    from ctypes import wintypes
    class Monitor(ctypes.Structure):
        _fields_ = [('handle', wintypes.HANDLE), ('description', wintypes.WCHAR*128)]
    user = ctypes.WinDLL('user32')
    dx = ctypes.WinDLL('dxva2')
    user.MonitorFromWindow.argtypes = (wintypes.HWND, wintypes.DWORD)
    user.MonitorFromWindow.restype = wintypes.HANDLE
    monitor = user.MonitorFromWindow(int(window.winId()), 2)
    count = wintypes.DWORD()
    dx.GetNumberOfPhysicalMonitorsFromHMONITOR.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    dx.GetPhysicalMonitorsFromHMONITOR.argtypes = (wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(Monitor))
    dx.GetVCPFeatureAndVCPFeatureReply.argtypes = (wintypes.HANDLE, ctypes.c_ubyte, ctypes.c_void_p,
                                                 ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD))
    if not dx.GetNumberOfPhysicalMonitorsFromHMONITOR(monitor, ctypes.byref(count)) or not count.value:
        return dict(screen_on=None, screen_on_reason='Windows DDC/CI physical monitor unavailable')
    handles = (Monitor*count.value)()
    if not dx.GetPhysicalMonitorsFromHMONITOR(monitor, count, handles):
        return dict(screen_on=None, screen_on_reason='Windows physical monitor query failed')
    states = []
    try:
        for item in handles:
            current, maximum = wintypes.DWORD(), wintypes.DWORD()
            if dx.GetVCPFeatureAndVCPFeatureReply(item.handle, 0xD6, None, ctypes.byref(current), ctypes.byref(maximum)):
                states.append(current.value)
    finally:
        dx.DestroyPhysicalMonitors(count, handles)
    return dict(screen_on=all(v == 1 for v in states) if states else None,
                screen_on_reason='Windows DDC/CI VCP D6: '+str(states) if states else 'Windows DDC/CI power mode unavailable')
