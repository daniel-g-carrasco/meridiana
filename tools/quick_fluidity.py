"""Quick gestures, compatible fluidity JSON, explicit offscreen/on-screen separation.

Default: offscreen, Python-boundary work only; action times are NOT GPU measurements.
--on-screen must be run only on an idle, authorised machine. No native pointer is moved.
All project changes stay in memory and all weather caches are temporary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class BoundaryTime:
    """Inclusive main-thread CPU inside bridge callbacks, without double counting.

    Includes native callees and Python profiling overhead; excludes render-thread CPU,
    worker CPU and the synthetic input driver. It is not a bytecode-only measurement.
    """
    def __init__(self):
        self.depth = 0
        self.started = 0
        self.ns = 0
        self.wall_started = 0
        self.wall_ns = 0

    def profile(self, frame, event, _arg):
        source = frame.f_code.co_filename.replace('\\', '/')
        if not (source.endswith('/quick/bridge.py') or '/quick/backend/plan' in source):
            return
        if event == 'call':
            if not self.depth:
                self.started = time.thread_time_ns()
                self.wall_started = time.perf_counter_ns()
            self.depth += 1
        elif event == 'return':
            self.depth -= 1
            if not self.depth:
                self.ns += time.thread_time_ns()-self.started
                self.wall_ns += time.perf_counter_ns()-self.wall_started


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--project', type=Path, default=Path.home()/'dev/meridiana-prove/Prova capannone Rho.meridiana')
    parser.add_argument('--on-screen', action='store_true')
    parser.add_argument('--screen', type=int, help='Screen index for --on-screen; fail if the requested monitor is absent')
    parser.add_argument('--native-window', action='store_true', help='Native GPU window on the sandbox desktop, not monitor timings')
    parser.add_argument('--render-loop', choices=('threaded', 'basic'), default='threaded')
    parser.add_argument('--sequence', choices=('all', 'edges', 'base', 'charts', 'plan'), default='all')
    parser.add_argument('--during-compute', action='store_true', help='Measure both edges during the first real, cold year')
    parser.add_argument('--large-text', action='store_true')
    parser.add_argument('--compare-charts', action='store_true', help='A/B the same chart with rebuilt or retained geometry')
    parser.add_argument('--plan-renderer', choices=('canvas', 'shapes', 'geometry', 'batched', 'triangles'), default='batched')
    parser.add_argument('--real-views', action='store_true', help='The real plan and 3D of the merged branches in the shell')
    parser.add_argument('--layout-only', action='store_true', help='Plan sequence with real layouts, without computing an energy year')
    parser.add_argument('--profile-python', action='store_true', help='Profile bridge callbacks; adds overhead to native timings (offscreen always does)')
    parser.add_argument('--expect-modules', type=int, default=778)
    parser.add_argument('--background', choices=('none', 'auto'), default='none', help='Match the Widgets benchmark background; auto is a separate map workload')
    parser.add_argument('--timeout', type=float, default=1200)
    parser.add_argument('--no-vsync', action='store_true')
    args = parser.parse_args()
    if args.layout_only and args.sequence != 'plan':
        parser.error('--layout-only is only valid with --sequence plan')
    if args.screen is not None and not args.on_screen:
        parser.error('--screen requires --on-screen')
    # Match the unprofiled Widgets harness for both kinds of native window.
    # sys.setprofile sees every Python call, including map coverage and Qt input.
    profile_python = not (args.on_screen or args.native_window) or args.profile_python
    if args.out.exists():
        parser.error('Output already exists; choose a new revision')
    os.environ['QSG_RENDER_LOOP'] = args.render_loop
    if args.on_screen or args.native_window:
        if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
            os.environ.pop('QT_QPA_PLATFORM')
    else:
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tests')]
    from PySide6.QtCore import QPointF, QTimer, Qt
    from PySide6.QtGui import QSurfaceFormat
    from meridiana import model
    from meridiana.quick.app import QuickWindow, create_app
    from meridiana.quick.sample import recorded_weather
    from quick.gestures import click, drag, item, key, point, pump, wait_for, wheel
    if args.no_vsync:
        fmt = QSurfaceFormat.defaultFormat()
        fmt.setSwapInterval(0)
        QSurfaceFormat.setDefaultFormat(fmt)
    app = create_app()
    if args.on_screen and app.platformName() in ('offscreen', 'minimal'):
        raise RuntimeError('--on-screen requires a real window platform')
    target_screen = app.primaryScreen()
    if args.screen is not None:
        if not 0 <= args.screen < len(app.screens()):
            parser.error(f'Screen {args.screen} is absent; available: {[s.name() for s in app.screens()]}')
        target_screen = app.screens()[args.screen]
    project_hash = hashlib.sha256(args.project.read_bytes()).hexdigest()
    source_hashes = {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest()
                     for f in sorted((ROOT/'src/meridiana/quick').rglob('*'))
                     if f.is_file() and f.suffix in {'.py', '.qml', '.js', '.frag', '.vert', '.qsb'}}
    harness_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    rows = []
    beat = [time.perf_counter()]
    active = [None]

    def tick():
        now = time.perf_counter()
        gap = (now-beat[0])*1000
        if active[0] is not None and gap > 30:
            active[0].append(round(gap, 2))
        beat[0] = now

    heart = QTimer()
    heart.setInterval(2)
    heart.timeout.connect(tick)
    heart.start()
    with tempfile.TemporaryDirectory(prefix='meridiana-quick-fluidity-') as tmp:
        p, notice = model.Project.load(args.project)
        cache = Path(tmp)
        recorded = recorded_weather(p, cache)
        started = time.perf_counter()
        host = QuickWindow(p, cache, large=args.large_text, real_views=args.real_views)
        if host.plan:
            host.plan.configureMaps({'source': args.background})
        win, bridge = host.window, host.bridge
        item(win, 'plan').setProperty('renderer', args.plan_renderer)
        built = (time.perf_counter()-started)*1000
        if args.on_screen:
            win.setScreen(target_screen)
            origin = target_screen.availableGeometry().topLeft()
            win.setPosition(origin.x()+80, origin.y()+40)
        win.show()
        if args.layout_only:
            from meridiana.jobs import layout_of
            results, keys, _ = layout_of(p)
            bridge.accept_layout(bridge.session.generation, results, keys)
        else:
            bridge.recompute()
        wait_for(lambda: bridge.moduleCount == args.expect_modules, args.timeout)
        plan, chart = item(win, 'plan'), item(win, 'yearChart')
        pump(100)
        plan.fit()
        opened = {'window_built_ms': round(built, 2), 'first_paint_ms': None, 'year_ms': None}

        def state():
            return {'modules': bridge.moduleCount, 'delegates': plan.property('polygonCount'),
                    'rendered_modules': plan.property('renderedModules'),
                    'painted_modules': plan.property('paintedModules'),
                    'year_hours': bridge.year.get('hours', 0), 'chart_points': chart.property('pointCount'),
                    'checks': len(bridge.checkRows), 'busy': bridge.busy, 'phase': win.property('phase'),
                    'window_size': [win.width(), win.height()],
                    'left_width': item(win, 'leftPanel').width(), 'right_width': item(win, 'rightPanel').width(),
                    'zoom': plan.property('zoom'), 'pan': [plan.property('panX'), plan.property('panY')]}

        def measure(name, steps, action, verify):
            before = state()
            bridge.calls.clear()
            bridge.emissions.clear()
            if host.plan:
                host.plan.calls.clear()
            timing = BoundaryTime()
            stalls = []
            beat[0] = time.perf_counter()
            active[0] = stalls
            begin = time.perf_counter()
            if profile_python:
                sys.setprofile(timing.profile)
            action()
            acted = (time.perf_counter()-begin)*1000
            # Match fluidity's 150 ms quiet interval and 8 s cap.
            quiet = time.perf_counter()
            seen = len(stalls)
            limit = quiet+8
            while time.perf_counter()<limit:
                pump(10)
                if seen != len(stalls):
                    seen, quiet = len(stalls), time.perf_counter()
                if time.perf_counter()-quiet >= .15:
                    break
            sys.setprofile(None)
            total = (time.perf_counter()-begin)*1000-150
            active[0] = None
            calls, signals = dict(bridge.calls), dict(bridge.emissions)
            if host.plan:
                calls.update({'plan.'+k: v for k, v in host.plan.calls.items()})
            after = state()
            assert after['modules'] == after['rendered_modules'] == args.expect_modules
            assert after['painted_modules'] == args.expect_modules
            assert after['delegates'] >= args.expect_modules
            verify(before, after)
            if host.warnings:
                raise AssertionError(host.warnings[:4])
            row = {'gesture': name, 'action_ms': round(acted, 2), 'until_idle_ms': round(total, 2),
                   'blocks': len(stalls), 'worst_ms': max(stalls, default=0), 'blocked_ms': round(sum(stalls), 2),
                   'steps': steps, 'action_ms_per_step': round(acted/steps, 3),
                   'python_boundary_cpu_ms': round(timing.ns/1e6, 4) if profile_python else None,
                   'python_boundary_cpu_ms_per_step': round(timing.ns/1e6/steps, 5) if profile_python else None,
                   'python_boundary_wall_ms': round(timing.wall_ns/1e6, 4) if profile_python else None,
                   'python_boundary_wall_ms_per_step': round(timing.wall_ns/1e6/steps, 5) if profile_python else None,
                   'qml_python_calls': calls, 'qml_python_calls_per_step': sum(calls.values())/steps,
                   'python_signals': signals, 'before': before, 'after': after, 'verified': True}
            rows.append(row)
            boundary = f'bridge {timing.ns/1e6:.3f} ms' if profile_python else 'profiling disabled'
            print(f"{name}: {acted/steps:.3f} ms/step, {boundary}, {sum(calls.values())} calls", flush=True)

        def changed(key):
            def check(a, b):
                if a[key] == b[key]:
                    raise AssertionError(f'{key} did not change: the gesture is empty')
            return check

        def edge(side, label):
            panel = item(win, side+'Panel')
            direction = 160 if side == 'left' else -160
            start = point(panel, panel.width()+4 if side=='left' else -4, panel.height()/2)
            end = start+QPointF(direction, 0)
            measure(label+': '+side+' edge dragged', 40,
                    lambda: drag(app, win, start, end), changed(side+'_width'))
            measure(label+': '+side+' edge back', 40,
                    lambda: drag(app, win, end, start), changed(side+'_width'))

        def resize():
            for i in range(15):
                win.resize(1600-20*i, 960)
                pump(16)

        if args.during_compute:
            if not bridge.busy:
                raise RuntimeError('Cold calculation already finished; no concurrent measurement was made')
            edge('left', 'computing model')
            edge('right', 'computing model')
            if not all(row['before']['busy'] and row['after']['busy'] for row in rows):
                raise RuntimeError('The calculation ended during the concurrent gestures; inspect partial overlap')
        if not args.layout_only:
            print('Waiting for the complete energy year', flush=True)
            wait_for(lambda: not bridge.busy, args.timeout)
            if bridge.error or bridge.year.get('hours') != 8760:
                raise RuntimeError('A real energy year is required: '+bridge.error)
            opened['year_ms'] = round((time.perf_counter()-started)*1000, 2)
        pump(200)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        for phase in (('model',) if args.layout_only else ('model', 'production')):
            win.setProperty('phase', phase)
            pump(250)
            shot = win.grabWindow()
            if shot.isNull():
                raise RuntimeError('Empty Quick screenshot')
            shot.save(str(args.out.with_name(args.out.stem+'-'+phase+'.png')))
        win.setProperty('phase', 'model')
        pump(250)
        if args.sequence in ('all', 'base', 'edges'):
            edge('left', 'model')
            edge('right', 'model')
            measure('model: window resized, 15 steps', 15, resize, changed('window_size'))
            win.resize(1600, 960)
            pump(100)
        if args.sequence in ('all', 'base', 'plan'):
            pos = point(plan)
            measure('plan: wheel 10', 10, lambda: wheel(app, win, pos), changed('zoom'))
            measure('plan: pan, 40 steps', 40,
                    lambda: drag(app, win, pos, pos+QPointF(-150, 40), button=Qt.MouseButton.MiddleButton), changed('pan'))
        if args.sequence in ('all', 'base'):
            for phase in ('production', 'model'):
                measure('phase '+phase, 1, lambda phase=phase: click(app, win, point(item(win, phase+'Tab'))), changed('phase'))
            bridge.select('building', p.buildings[0].id, '')
            field = item(win, 'nameField')
            click(app, win, point(field))
            old_name = bridge.selection['name']
            key(app, win, Qt.Key.Key_A, modifiers=Qt.KeyboardModifier.ControlModifier)

            def typing():
                # fluidity says "12 keys" but actually types exactly these four characters.
                for c in '12,5':
                    key(app, win, ord(c), c)
                    pump(40)
                key(app, win, Qt.Key.Key_Return)

            def typed(_a, _b):
                assert bridge.selection['name'] == '12,5' and old_name != '12,5'

            measure('a field: 12 keys', 4, typing, typed)
            bridge.undo()
            pump(100)
        if args.sequence in ('all', 'charts', 'edges'):
            win.setProperty('phase', 'production')
            pump(300)
            assert chart.isVisible() and chart.property('pointCount') >= 365
            edge('right', 'production')
            measure('production: window resized, 15 steps', 15, resize, changed('window_size'))
            win.resize(1600, 960)
            pump(100)
            if args.compare_charts:
                for repeat in range(3):
                    for retained in (False, True):
                        chart.setProperty('retained', retained)
                        pump(250)
                        edge('right', f"production-{'retained' if retained else 'resampled'}-{repeat+1}")
                chart.setProperty('retained', True)
        win.setProperty('phase', 'model')
        win.resize(900, 640)
        pump(250)
        plan.fit()
        win.grabWindow().save(str(args.out.with_name(args.out.stem+'-narrow.png')))
        win.resize(1600, 960)
        pump(100)
        assert project_hash == hashlib.sha256(args.project.read_bytes()).hexdigest()
        screen = win.screen()
        result = {'when': time.strftime('%Y-%m-%d %H:%M'),
                  'commit': subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip(),
                  'on_screen': args.on_screen, 'native_window': args.native_window, 'real_views': args.real_views,
                  'no_3d': not args.real_views, 'no_vsync': args.no_vsync, 'maximized': False,
                  'platform': app.platformName(), 'sequence': args.sequence,
                  'graphics_api': str(win.rendererInterface().graphicsApi()),
                  'plan_renderer': args.plan_renderer,
                  'background': args.background,
                  'layout_only': args.layout_only,
                  'screen': f'{screen.name()} {screen.size().width()}x{screen.size().height()} @ {screen.devicePixelRatio():g}',
                  'requested_screen': args.screen,
                  'machine': platform.processor() or platform.machine(), 'qt': __import__('PySide6').__version__,
                  'opened': opened, 'stall_ms': 30,
                  'environment': {k:v for k,v in os.environ.items() if k.startswith(('QT_', 'QSG_'))},
                  'measurement_scope': ('screen_event_loop_and_python' if args.on_screen else
                                        'native_sandbox_without_monitor' if args.native_window else 'offscreen_python_only'),
                  'results': rows, 'project_sha256': project_hash, 'recorded_rho_weather': recorded,
                  'harness_sha256': harness_hash, 'source_sha256': source_hashes,
                  'profile_python': profile_python,
                  'notice': notice, 'metrics': bridge.metrics, 'final_state': state(), 'qml_warnings': host.warnings,
                  'skipped': ['3D (not part of this spike)', 'File', 'plant', 'consumption', 'economics', 'report',
                              'chart tabs (only one chart)', 'chart wheel/hover (not implemented)'],
                  'profiling_note': 'Inclusive bridge main-thread CPU, including native callees and profiler overhead; '
                                    'action times include pacing, Qt work and rendering and are not GPU evidence offscreen.'}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print('Written', args.out, flush=True)
        host.close()
        from PySide6.QtCore import QCoreApplication, QEvent
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
