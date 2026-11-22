"""Repeatable offscreen phase benchmark. Timings and profiles are separate passes.

Uses a real window and a complete computed year, with an isolated cache/profile.
Frame intervals are Qt frameSwapped intervals, not physical display latency.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
PHASES = ('model', 'plant', 'production', 'consumption', 'economics', 'report')


class UIProfile:
    """Deterministic call profile restricted explicitly to the window's thread.

    PySide callbacks can enter Python from worker/render threads. Never merge
    those stacks into the GUI stack, even if a binding propagates the hook.
    """
    def __init__(self):
        self.thread = threading.get_ident()
        self.active = False
        self.stack = []
        self.totals = defaultdict(lambda: [0, 0, 0])

    def event(self, frame, event, arg):
        if not self.active or threading.get_ident() != self.thread:
            return
        now = time.perf_counter_ns()
        if event in ('call', 'c_call'):
            code = frame.f_code
            if event == 'call':
                key = code.co_filename, code.co_firstlineno, code.co_name
            else:
                name = getattr(arg, '__qualname__', getattr(arg, '__name__', type(arg).__name__))
                key = code.co_filename, frame.f_lineno, 'C:' + name
            self.stack.append([event, key, now, 0])
        elif event in ('return', 'c_return', 'c_exception') and self.stack:
            kind = 'call' if event == 'return' else 'c_call'
            if self.stack[-1][0] != kind:
                return
            _, key, start, children = self.stack.pop()
            elapsed = now-start
            row = self.totals[key]
            row[0] += 1
            row[1] += max(0, elapsed-children)
            row[2] += elapsed
            if self.stack:
                self.stack[-1][3] += elapsed

    def enable(self):
        self.active = True
        sys.setprofile(self.event)

    def disable(self):
        self.active = False
        sys.setprofile(None)

    def rows(self):
        return sorted([{'file': f.replace('\\', '/'), 'line': line, 'call': name, 'calls': values[0],
                        'self_ms': round(values[1]/1e6, 3), 'total_ms': round(values[2]/1e6, 3)}
                       for (f, line, name), values in self.totals.items()], key=lambda row: -row['total_ms'])[:35]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--label', default='base')
    parser.add_argument('--compare-root', type=Path, help='Alternate this baseline and source-root in fresh processes')
    parser.add_argument('--repetitions', type=int, default=5)
    parser.add_argument('--profile', action='store_true')
    parser.add_argument('--observe-ms', type=int, default=700)
    parser.add_argument('--backend', choices=('rhi', 'software'), default='rhi')
    parser.add_argument('--live', action='store_true',
                        help='the real screen and its GPU (as the user sees it), not offscreen')
    parser.add_argument('--pairs', help='Only these directed edges, comma separated: model:report,report:model')
    args = parser.parse_args()
    pairs = None
    if args.pairs:
        pairs = {tuple(pair.split(':')) for pair in args.pairs.split(',')}
        if any(len(pair) != 2 or any(p not in PHASES for p in pair) or pair[0] == pair[1] for pair in pairs):
            parser.error('Pairs must be distinct known phases, for example model:report')
    if args.out.exists():
        parser.error('Output exists: choose a new revision')
    if args.compare_root:
        runs = []
        import subprocess
        for repetition in range(args.repetitions):
            for label, source in (('base', args.compare_root), ('trial', args.source_root)):
                output = args.out.with_name(f'{args.out.stem}-{repetition+1}-{label}.json')
                command = [sys.executable, str(Path(__file__).resolve()), '--project', str(args.project.resolve()),
                           '--cache', str(args.cache.resolve()), '--out', str(output.resolve()),
                           '--source-root', str(source.resolve()), '--label', label,
                           '--observe-ms', str(args.observe_ms), '--backend', args.backend]
                if args.pairs:
                    command.extend(['--pairs', args.pairs])
                if args.live:
                    command.append('--live')
                if args.profile:
                    command.append('--profile')
                subprocess.run(command, check=True)
                runs.append(json.loads(output.read_text(encoding='utf-8')))
        args.out.write_text(json.dumps({'runs': runs}, indent=2), encoding='utf-8')
        return
    args.cache = args.cache.resolve()
    args.source_root = args.source_root.resolve()
    args.cache.mkdir(parents=True, exist_ok=True)
    for key in ('APPDATA', 'LOCALAPPDATA', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME', 'XDG_CACHE_HOME'):
        os.environ[key] = str(args.cache / 'profile')
    os.environ.update(QT_QUICK_BACKEND=args.backend,
                      QSG_RENDER_LOOP='basic' if args.backend == 'software' else 'threaded', MERIDIANA_PRELOAD='0',
                      PYTHONDONTWRITEBYTECODE='1')
    if not args.live:   # --live keeps the session's platform, GPU API and scale (Wayland on the Linux laptop)
        os.environ.update(QT_QPA_PLATFORM='offscreen', QSG_RHI_BACKEND='d3d11', QT_SCALE_FACTOR='1')
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(args.source_root / 'src'), str(ROOT / 'tests')]
    os.environ['PYTHONPATH'] = os.pathsep.join(sys.path[:2])
    from PySide6.QtCore import QTimer, Qt
    from meridiana.core.model.model import Project
    from meridiana.gui.application import QuickWindow, create_app
    from meridiana.gui.sample import recorded_weather

    app = create_app()
    project, _ = Project.load(args.project, args.cache)
    recorded_weather(project, args.cache, ROOT / 'tests/calcoli/riferimenti/pvgis53-tmy-rho.json.gz')
    host = QuickWindow(project, args.cache, real_views=True, path=args.project,
                       theme={'theme': 'light', 'reducedMotion': False})
    host.keep_on_screen = lambda: None
    host._placement.timeout.disconnect()
    win, bridge = host.window, host.bridge
    bridge.configure_background(enabled=False)
    win.resize(1400, 900)
    win.setPosition(-20000, -20000)
    win.show()

    active_turns = None

    def pump(ms):
        until = time.perf_counter() + ms / 1000
        while time.perf_counter() < until:
            wall, cpu = time.perf_counter(), time.thread_time()
            app.processEvents()
            if active_turns is not None:
                active_turns.append(((time.perf_counter()-wall)*1000, (time.thread_time()-cpu)*1000))
            time.sleep(.001)

    def wait_for(predicate, seconds=1200):
        until = time.perf_counter() + seconds
        while not predicate():
            if time.perf_counter() > until:
                raise TimeoutError(f'Year not ready: {bridge.error}; {bridge.yearNote}')
            pump(10)

    pump(1500)
    print("Preparing the computed year", flush=True)
    bridge.recompute()
    wait_for(lambda: not bridge.busy and bridge._layout is None and not bridge.session.telling())
    if not bridge.session.energy.get('sim'):
        bridge.recompute()
    wait_for(lambda: not bridge.busy and bool(bridge.session.energy.get('sim')) and not bridge.session.telling())
    wait_for(lambda: not host.parts.controllers['results'].busy)
    pump(1500)
    assert not bridge.session.year_outdated(), 'The year must match current inputs'
    ticker = QTimer()
    ticker.setInterval(8)
    ticker.timeout.connect(win.requestUpdate)
    rows, visited = [], {'model'}
    load = {}
    try:
        import psutil
        load = {'cpu_percent': psutil.cpu_percent(interval=1), 'memory_percent': psutil.virtual_memory().percent,
                'logical_cpus': psutil.cpu_count(), 'processes': len(psutil.pids())}
    except ImportError:
        if sys.platform == 'win32':
            import ctypes
            def cpu_times():
                values = [ctypes.c_ulonglong() for _ in range(3)]
                if not ctypes.windll.kernel32.GetSystemTimes(*(ctypes.byref(v) for v in values)):
                    raise OSError('GetSystemTimes failed')
                return [v.value for v in values]
            a = cpu_times()
            pump(1000)
            b = cpu_times()
            idle, kernel, user = [y-x for x, y in zip(a, b, strict=True)]
            load = {'cpu_percent': round(100*(1-idle/(kernel+user)), 1), 'logical_cpus': os.cpu_count(),
                    'source': 'GetSystemTimes, one second before the measurements'}
        else:
            load = {'available': False}
    # Each directed edge once per process; five independent processes make five repetitions.
    for before in PHASES:
        for after in PHASES:
            if before == after or (pairs is not None and (before, after) not in pairs):
                continue
            win.showPhase(before)
            pump(args.observe_ms)
            frames = []
            marker = {'armed': False, 'synced': False}
            def synchronized(marker=marker):
                if marker['armed']:
                    marker['synced'] = True
            def swapped(frames=frames, marker=marker):
                if marker['synced']:
                    frames.append(time.perf_counter())
            # Only Python data and clocks on the render thread, never Qt objects.
            win.afterSynchronizing.connect(synchronized, Qt.ConnectionType.DirectConnection)
            win.frameSwapped.connect(swapped, Qt.ConnectionType.DirectConnection)
            profiler = UIProfile() if args.profile else None
            ticker.start()
            active_turns = []
            start, cpu_start = time.perf_counter(), time.thread_time()
            if profiler:
                profiler.enable()
            win.showPhase(after)
            action_ms = (time.perf_counter() - start) * 1000
            action_cpu_ms = (time.thread_time() - cpu_start) * 1000
            assert win.property('phase') == after
            marker['armed'] = True
            win.requestUpdate()
            pump(args.observe_ms)
            # Close the observation with an actual frame: a slow last event must
            # not disappear merely because it ran past the observation deadline.
            tail = time.perf_counter()
            win.requestUpdate()
            until = tail + 5
            while (not frames or frames[-1] < tail) and time.perf_counter() < until:
                pump(5)
            if not frames or frames[-1] < tail:
                raise RuntimeError(f'No drawn frame for {before}>{after}; no zero timing is valid')
            if profiler:
                profiler.disable()
            ticker.stop()
            win.frameSwapped.disconnect(swapped)
            win.afterSynchronizing.disconnect(synchronized)
            intervals = [(b-a)*1000 for a, b in zip([start]+frames, frames, strict=False)]
            # An idle window need not draw: gaps count only while a frame was requested.
            first = (frames[0]-start)*1000 if frames else None
            row = {'from': before, 'to': after, 'first_entry': after not in visited,
                   'show_ms': round(action_ms, 3), 'show_cpu_ms': round(action_cpu_ms, 3),
                   'worst_event_ms': round(max(t[0] for t in active_turns), 3),
                   'worst_event_cpu_ms': round(max(t[1] for t in active_turns), 3), 'visible_ms': round(first, 3) if first is not None else None,
                   'worst_frame_ms': round(max(intervals), 3) if intervals else None, 'frames': len(frames)}
            if profiler:
                row['profile'] = profiler.rows()
                row['profile_thread'] = 'main'
            active_turns = None
            rows.append(row)
            visited.add(before)
            visited.add(after)
            print(f"{args.label} {before}>{after}: {row['visible_ms']} / {row['worst_frame_ms']} ms", flush=True)
    result = {'label': args.label, 'profiled': args.profile, 'load': load, 'date': time.strftime('%Y-%m-%dT%H:%M:%S'),
              'project_sha256': hashlib.sha256(args.project.read_bytes()).hexdigest(),
              'source_root': str(args.source_root), 'hours': len(bridge.session.energy['sim'].hourly),
              'modules': bridge.moduleCount, 'year_key_sha256': hashlib.sha256(bridge.session.energy_key_computed.encode()).hexdigest(),
              'graphics': str(win.rendererInterface().graphicsApi()), 'rows': rows,
              'warnings': host.warnings}
    args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    host.close()
    app.processEvents()


if __name__ == '__main__':
    main()
