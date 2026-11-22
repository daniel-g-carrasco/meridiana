"""What a zoom costs the plan, and what the plan looks like while it zooms.

A real window on the secondary screen (MERIDIANA_TEST_SCREEN), a temporary profile, a project never written.

- The default pass (`--run wheel pinch`) is the whole travel without a pause: from the framed site down to a few
  modules on screen and back, with real wheel or pinch events. It gives the gaps between swaps (median, p95,
  worst, over 50 and 100 ms), the scale at which each long gap fell and the stalls of the two seconds after the
  hand stops.
- `--sequence` is the gesture of every day: a few zooms in and out in a row from a middle scale with short rests;
  every gap counts, the rests' too, and the longest one is the result.
- `--frames` repeats the way in and saves what the window shows at some scales, each beside the same view once
  settled, with their sharpness compared.
- `--redraw` measures what drawing the geometry again costs at each scale, a redraw at a time.
- `--timeline` sends isolated steps and lists every stall after each.

The swaps are read on the GUI thread (queued): no Python runs on the threaded renderer, where it could wait for
the GUI thread for ever (R702); a stall of the GUI thread therefore shows as one long gap. `--qsg` adds Qt's own
timings of each frame, `--hide` takes layers away by their object names (what a layer costs is what its absence
saves), `--source-root` measures an exported commit with the same events. The passes never run together: a grab
waits for the render thread.
"""
import argparse
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
# where the zoom holds still: the middle of a run of modules in the middle of the list, inside a field
# (the scene's y points down)
ANCHOR = ('(function(){ var n=modules.length, from=n>>1, to=Math.min(n, from+Math.max(1, n>>3)), x=0, y=0;'
          ' for (var i=from; i<to; ++i) { var m=modules[i].points; x+=(m[0].x+m[2].x)/2; y+=(m[0].y+m[2].y)/2 }'
          ' var p=n ? screen(x/(to-from), -y/(to-from)) : Qt.point(width/2, height/2)')


def machine_times():
    """Idle and total processor time of the whole machine, in 100 ns: what else was running during a measure."""
    if os.name != 'nt':
        with open('/proc/stat', encoding='ascii') as stream:
            values = [int(v) for v in stream.readline().split()[1:8]]
        return values[3]+values[4], sum(values)
    import ctypes
    idle, kernel, user = ctypes.c_ulonglong(), ctypes.c_ulonglong(), ctypes.c_ulonglong()
    ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user))
    return idle.value, kernel.value+user.value          # the kernel's time includes the idle time


def machine_busy(before, after):
    total = after[1]-before[1]
    return round(100*(1-(after[0]-before[0])/total), 1) if total else None


class NativeLog:
    """Qt's own frame timings (QSG_RENDER_TIMING): a diagnostic pass, its callbacks slow the frames a little."""
    FIELDS = ('polish', 'lock', 'blockedForSync', 'animations', 'sync', 'render', 'swap',
              'preprocess', 'updates', 'rendering')

    def __init__(self, slow=0):
        from PySide6.QtCore import QLoggingCategory, qInstallMessageHandler
        self.rows, self.gpu, self.slow = [], [], slow
        self.previous = qInstallMessageHandler(self.message)
        QLoggingCategory.setFilterRules('\n'.join(('qt.scenegraph.time.*=false', 'qt.scenegraph.time.renderloop=true',
                                                   'qt.scenegraph.time.renderer=true')))

    def message(self, kind, context, message):
        if 'GPU frame time was' in message:
            self.gpu.append((time.perf_counter_ns(), float(message.split('GPU frame time was')[1].split('ms')[0])))
        elif (context.category or '').startswith('qt.scenegraph.time.'):
            self.rows.append((time.perf_counter_ns(), message))
        elif self.previous:
            self.previous(kind, context, message)

    def summary(self, first, last):
        import re
        from gesture_bench_core import percentile
        values = {name: [] for name in self.FIELDS}
        for at, message in self.rows:
            if first <= at <= last:
                if self.slow and any(int(v) >= self.slow for v in re.findall(r'=(\d+)', message)):
                    print(f'    slow at {(at-first)/1e6:.0f} ms: {message}', flush=True)
                for name, value in re.findall(r'(\w+)=(\d+)', message):
                    if name in values:
                        values[name].append(int(value))
        self.rows.clear()
        return {name: dict(median=percentile(v, .5), p95=percentile(v, .95), worst=max(v), count=len(v))
                for name, v in values.items() if v}


def open_window(args, cache):
    from gesture_bench_qt import find, initialize
    if args.qsg:
        os.environ['QSG_RENDER_TIMING'] = '1'
    setup_args = SimpleNamespace(source_root=args.source_root, live=True, platform=None, backend='rhi', api='d3d11',
                                 scale=None, qsg=False, qml_profile=False, allow_primary_screen=False)
    _, setup, app, graphics = initialize(setup_args)
    args.native = NativeLog(getattr(args, 'slow', 0)) if args.qsg else None
    from meridiana.app.platform import config
    from meridiana.core.model.model import Project
    from meridiana.gui.application import QuickWindow
    project, _ = Project.load(args.project, cache)
    config.save(config.Config(network_tiles=False, network_pvgis=False), cache/'quick-profile/config/config.json')
    host = QuickWindow(project, cache, real_views=True, theme={'theme': args.theme, 'reducedMotion': False})
    host.keep_on_screen = lambda: None
    window = host.window
    window.setGraphicsConfiguration(graphics)        # the GPU's own frame times, where the driver gives them
    host.bridge.configure_background(enabled=False)
    host.plan.configureMaps({'offline': True})
    screen = app.screens()[int(os.environ['MERIDIANA_TEST_SCREEN'])]
    window.setScreen(screen)
    area = screen.availableGeometry()
    window.setGeometry(area.x()+10, area.y()+10, min(args.size[0], area.width()-20), min(args.size[1], area.height()-20))
    window.show()
    if not setup.wait_until(app, lambda: find(window, 'plan') is not None, 60):
        raise TimeoutError('plan did not load')
    host.bridge._ask_layout()
    if not setup.wait_until(app, lambda: host.bridge._layout is None and not host.bridge.session.telling()
                            and host.bridge.session.layout_keys == host.bridge.session.expected_layout_keys(), 180):
        raise TimeoutError('layout did not settle')
    window.showPhase(args.phase)
    window.setProperty('viewMode', 'plan')
    if args.tiles:
        from PySide6.QtGui import QColor, QImage, QPainter
        # a drawn tile, never the network: its lines every 32 px tell a sharp background from a stretched one,
        # and every tile the view asks for on the way is answered at once, as a full cache would
        tile = QImage(256, 256, QImage.Format_RGB32)
        tile.fill(QColor('#506149'))
        painter = QPainter(tile)
        painter.setPen(QColor('#d8e0c8'))
        for at in range(0, 256, 32):
            painter.drawLine(at, 0, at, 255)
            painter.drawLine(0, at, 255, at)
        painter.end()
        host.plan.configureMaps({'source': 'osm'})
        maps = host.plan.maps

        def feed():
            for key in list(maps.state.wanted | maps.state.backdrop):
                if key not in maps.state.loaded:
                    maps._ready(*key, tile)
        maps.changed.connect(feed)
        setup.turn_events(app, 600)
        feed()
    for name in args.hide:
        item = find(window, name)
        if item is None:
            raise ValueError('no item named '+name)
        item.setProperty('visible', False)      # a diagnosis: what a layer costs is what its absence saves
    image = find(window, 'motionSnapshot')
    if args.image_samples is not None:           # diagnoses: what the samples and the pixels of the image cost
        image.setProperty('samples', args.image_samples)
    if args.image_scale is not None:
        from PySide6.QtCore import QSize
        ratio = window.devicePixelRatio()*args.image_scale
        image.setProperty('textureSize', QSize(round(image.width()*ratio), round(image.height()*ratio)))
    setup.turn_events(app, 2500)
    if window.screen() is not screen or screen is app.primaryScreen():
        raise RuntimeError('the probe window is not on the secondary screen')
    return setup, app, host, find(window, 'plan')


def watch(app, window, act, span_ms, setup):
    """Run `act` and return the GUI stalls and the swap gaps of the following `span_ms`."""
    from PySide6.QtCore import QTimer, Qt
    beats, swaps = [], []
    heart, paint = QTimer(), QTimer()
    heart.setTimerType(Qt.PreciseTimer)
    heart.setInterval(1)
    heart.timeout.connect(lambda: beats.append(time.perf_counter_ns()))
    paint.setInterval(1)
    paint.timeout.connect(window.requestUpdate)

    def swapped():
        swaps.append(time.perf_counter_ns())
    window.frameSwapped.connect(swapped, Qt.QueuedConnection)
    heart.start()
    paint.start()
    setup.turn_events(app, 300)
    start = time.perf_counter_ns()
    act()
    beats.append(time.perf_counter_ns())
    setup.turn_events(app, span_ms)
    heart.stop()
    paint.stop()
    window.frameSwapped.disconnect(swapped)

    def gaps(stamps, least):
        return [dict(at_ms=round((a-start)/1e6), ms=round((b-a)/1e6, 1))
                for a, b in zip(stamps, stamps[1:], strict=False) if b > start and b-a > least*1e6]
    return dict(gui_stalls=gaps(beats, 40), swap_gaps=gaps(swaps, 40), swaps=sum(t >= start for t in swaps))


def timeline(args, setup, app, host, plan):
    from gesture_bench_ui import evaluate
    window = host.window
    actions = dict(
        idle=lambda: None,
        relabel=lambda: evaluate(plan, 'settledZoom = settledZoom*1.2'),
        relabel_back=lambda: evaluate(plan, 'settledZoom = zoom'),
        notch_in=lambda: evaluate(plan, 'zoomAt(1.2, width/2, height/2)'),
        notch_out=lambda: evaluate(plan, 'zoomAt(1/1.2, width/2, height/2)'),
        pan=lambda: evaluate(plan, '(function(){ panBy(40, 25); applyMotion() })()'),
    )
    report = dict(project=args.project.name, modules=host.bridge.moduleCount, size=[window.width(), window.height()],
                  dpr=window.devicePixelRatio(), screen=window.screen().name(),
                  graphics_api=str(window.rendererInterface().graphicsApi()), tiles=args.tiles, actions=[])
    if args.at:                     # the steps near the modules, where the labels and the dashes are the most
        evaluate(plan, ANCHOR+'; zoomAt(%r/zoom, p.x, p.y) })()' % (args.at/evaluate(plan, 'backend.moduleSize')))
        setup.turn_events(app, 4000)
        report['module_px'] = args.at
    for repetition in range(args.repetitions):
        for name, act in actions.items():
            setup.turn_events(app, 1500)
            result = watch(app, window, act, 2000, setup)
            result.update(action=name, repetition=repetition)
            report['actions'].append(result)
            stalls = ', '.join(f"{g['ms']}@{g['at_ms']}" for g in result['gui_stalls']) or 'none'
            swaps = ', '.join(f"{g['ms']}@{g['at_ms']}" for g in result['swap_gaps']) or 'none'
            print(f'{name:<13} GUI stalls ms@ms: {stalls} | swap gaps: {swaps}', flush=True)
    return report


def redraw(args, setup, app, host, plan):
    """What drawing the geometry again costs at each scale: a few redraws, one at a time, each a pixel aside.

    It stops at the first scale whose redraw passes 400 ms: more of them would hold the whole desktop."""
    from gesture_bench_core import percentile
    from gesture_bench_ui import evaluate
    window = host.window
    module = evaluate(plan, 'backend.moduleSize')
    report = dict(project=args.project.name, modules=host.bridge.moduleCount, dpr=window.devicePixelRatio(),
                  tiles=args.tiles, hidden=args.hide, scales=[])
    if args.renderer:
        evaluate(plan, 'renderer = %r' % args.renderer)
        setup.turn_events(app, 1500)
    for pixels in args.scales:
        evaluate(plan, 'fit()')
        setup.turn_events(app, 800)
        evaluate(plan, ANCHOR+'; zoomAt(%r/zoom, p.x, p.y) })()' % (pixels/module))
        setup.turn_events(app, 2000)
        if args.settled:
            # the dashes built for another zoom than the view's: what the settled scale itself costs a redraw
            evaluate(plan, 'settledZoom = %r' % args.settled)
            setup.turn_events(app, 1500)
        from PySide6.QtCore import Qt
        swaps = []

        def swapped(swaps=swaps):
            swaps.append(time.perf_counter_ns())
        window.frameSwapped.connect(swapped, Qt.QueuedConnection)
        from PySide6.QtCore import QTimer
        paint = QTimer()
        paint.setInterval(1)
        paint.timeout.connect(window.requestUpdate)      # frames keep coming: the wait below counts swaps
        paint.start()
        costs, gpu = [], []
        for turn in range(args.redraws):
            start = time.perf_counter_ns()
            # a pixel aside, or 1,44 times nearer and back: a redraw at a new scale builds more than one at the same
            evaluate(plan, 'panX += 1' if args.step == 'pan' else
                     'zoomAt(%s, width/2, height/2)' % (1.44 if turn % 2 == 0 else 1/1.44))
            window.requestUpdate()
            setup.wait_until(app, lambda start=start, swaps=swaps: sum(t > start for t in swaps) >= 2, 8)
            shown = [t for t in swaps if t > start]
            # the second swap: the first may be a frame already on its way when the camera moved
            costs.append((shown[1]-start)/1e6 if len(shown) > 1 else 8000.)
            setup.turn_events(app, 400)
            if args.native:
                gpu.append(max((ms for at, ms in args.native.gpu if at > start), default=0.))
        paint.stop()
        window.frameSwapped.disconnect(swapped)
        result = dict(module_px=pixels, redraws=len(costs), median_ms=round(percentile(costs, .5), 1),
                      worst_ms=round(max(costs), 1), costs_ms=[round(v) for v in costs],
                      gpu_ms=[round(v, 1) for v in gpu])
        report['scales'].append(result)
        print(f"module {pixels:>5} px: redraw median {result['median_ms']} worst {result['worst_ms']} ms, each {result['costs_ms']}", flush=True)
        if result['worst_ms'] > 400 or max(gpu, default=0) > 250:
            print('stopped: a redraw over 400 ms', flush=True)
            break
    return report


def travel(kind, plan, near_px, seconds):
    """The steps of the whole travel, in and back, anchored on the modules, for Input.send."""
    from gesture_bench_ui import evaluate
    anchor = evaluate(plan, ANCHOR+'; return [p.x-width/2, p.y-height/2] })()')
    x, y = float(anchor[0]), float(anchor[1])
    depth = max(2., near_px/(evaluate(plan, 'backend.moduleSize')*plan.property('zoom')))
    steps = []
    if kind == 'wheel':
        notches = math.ceil(math.log(depth)/math.log(1.2))
        gap = 1000*seconds/notches
        for i in range(2*notches):
            steps.append(dict(at_ms=(i+1)*gap, action='wheel', angle=120 if i < notches else -120, x=x, y=y))
    else:
        count = int(120*seconds)
        value = depth**(1/count)-1
        steps.append(dict(at_ms=0, action='native', phase='begin', value=0, x=x, y=y))
        for i in range(2*count):
            steps.append(dict(at_ms=(i+1)*1000/120, action='native', phase='update',
                              value=value if i < count else 1/(1+value)-1, x=x, y=y))
        steps.append(dict(at_ms=(2*count+1)*1000/120, action='native', phase='end', value=0, x=x, y=y))
    return steps, depth, (x, y)


WATCHED = ('motionActive', 'geometryDraws', 'strokeZoom', 'settledZoom', 'scene')


def play(window, plan, sender, steps, tail_ms, on_step=None, observe=True, trace=False, after=None, whole=False):
    """Send the steps on their clock. Returns the swaps, the heartbeats and (time, zoom) at every step.

    `after`, a dict, receives what happens once the hand has stopped: `changes`, the plan's states that changed
    (when a stall falls beside one, that is its cause), and `python`, where the GUI thread's Python was, sampled
    every 5 ms from another thread (nothing there: the stall is Qt's or QML's)."""
    import threading
    from collections import Counter
    from PySide6.QtCore import QEventLoop, QTimer, Qt
    loop, timer, heart, paint = QEventLoop(), QTimer(), QTimer(), QTimer()
    timer.setSingleShot(True)
    timer.setTimerType(Qt.PreciseTimer)
    heart.setTimerType(Qt.PreciseTimer)
    heart.setInterval(2)
    paint.setInterval(1)
    paint.timeout.connect(window.requestUpdate)
    swaps, beats, zooms, sent = [], [], [], []
    state, changes, samples, done = {}, [], Counter(), threading.Event()
    backend = plan.property('backend')
    gui = threading.get_ident()

    def beat():
        now = time.perf_counter_ns()
        beats.append(now)
        if after is not None and (whole or len(sent) == len(steps)):
            for name in WATCHED:
                # `scene`: the strings' scene of the backend, another one when the layers of a new scale arrive
                value = plan.property(name) if name != 'scene' else id(getattr(backend, '_wiring_seen', None)) % 100000
                if state.get(name, value) != value:
                    changes.append((now, name, value))
                state[name] = value
    heart.timeout.connect(beat)

    def sample():
        while not done.wait(.005):
            frame = sys._current_frames().get(gui)
            if (frame is not None and (whole or len(sent) == len(steps))
                    and frame.f_code.co_name not in ('play', 'beat', 'tick', 'send')):
                samples[f'{Path(frame.f_code.co_filename).name}:{frame.f_lineno} {frame.f_code.co_name}'] += 1
    sampler = threading.Thread(target=sample, daemon=True)
    if after is not None:
        sampler.start()

    def swapped():
        swaps.append(time.perf_counter_ns())
    if observe:
        window.frameSwapped.connect(swapped, Qt.QueuedConnection)
        heart.start()
    start = time.perf_counter_ns()
    index = [0]

    def tick():
        sender.send(steps[index[0]])
        now = time.perf_counter_ns()
        sent.append(now)
        goal = plan.property('pendingMotion')
        goal = goal.toVariant() if hasattr(goal, 'toVariant') else goal
        zooms.append((now, (goal or {}).get('zoom') or plan.property('zoom')))
        if trace:
            camera = plan.property('renderCamera')
            camera = camera.toVariant() if hasattr(camera, 'toVariant') else camera
            print(f"    step {index[0]} at {(now-start)/1e6:.0f} ms: zoom {plan.property('zoom'):.2f} goal {zooms[-1][1]:.2f}"
                  f" drawn at {(camera or {}).get('zoom', 0):.2f} draws {plan.property('geometryDraws')}"
                  f" moving {plan.property('motionActive')}", flush=True)
        index[0] += 1
        if on_step:
            on_step(index[0])
        if index[0] == len(steps):
            QTimer.singleShot(tail_ms, loop.quit)
        else:
            timer.start(max(0, round(steps[index[0]]['at_ms']-(time.perf_counter_ns()-start)/1e6)))
    timer.timeout.connect(tick)
    timer.start(round(steps[0]['at_ms']))
    paint.start()
    loop.exec()
    paint.stop()
    heart.stop()
    done.set()
    if observe:
        window.frameSwapped.disconnect(swapped)
    if after is not None:
        sampler.join()
        origin = sent[0] if whole else sent[-1]
        after.update(changes=[dict(at_ms=round((at-origin)/1e6), name=name, value=value) for at, name, value in changes],
                     python=[dict(where=where, ms=5*count) for where, count in samples.most_common(8)])
    return swaps, beats, zooms, sent


def run(args, setup, app, host, plan):
    from gesture_bench_core import percentile
    from gesture_bench_qt import Input
    from gesture_bench_ui import evaluate
    window = host.window
    module = evaluate(plan, 'backend.moduleSize')
    report = dict(project=args.project.name, modules=host.bridge.moduleCount, size=[window.width(), window.height()],
                  dpr=window.devicePixelRatio(), screen=window.screen().name(), refresh_hz=window.screen().refreshRate(),
                  graphics_api=str(window.rendererInterface().graphicsApi()), tiles=args.tiles, theme=args.theme,
                  phase=args.phase, strings=len(evaluate(plan, 'backend.stringLabels')), runs=[])
    for kind in args.run:
        for repetition in range(args.repetitions):
            evaluate(plan, 'fit()')
            setup.turn_events(app, 2500)
            steps, depth, _ = travel(kind, plan, args.near_px, args.seconds)
            if args.way == 'in':            # the hand stops near the modules: what the plan does there once it rests
                steps = steps[:len(steps)//2]
            far = plan.property('zoom')
            what, load = {}, machine_times()
            swaps, beats, zooms, sent = play(window, plan, Input(app, host, plan), steps, 2500, trace=args.trace,
                                             after=what)
            busy = machine_busy(load, machine_times())
            first, last, turn = sent[0], sent[-1], sent[len(sent)//2]

            def zoom_at(t, zooms=zooms):
                return next((z for at, z in reversed(zooms) if at <= t), zooms[0][1])
            active = [t for t in swaps if first <= t <= last+50_000_000]
            pairs = list(zip(active, active[1:], strict=False))
            gaps = [(b-a)/1e6 for a, b in pairs]
            long = [dict(at_ms=round((a-first)/1e6), ms=round((b-a)/1e6, 1), way='in' if a < turn else 'out',
                         zoom=round(zoom_at(a), 3), module_px=round(zoom_at(a)*module, 1))
                    for a, b in pairs if b-a > 33_400_000]
            after = [dict(at_ms=round((a-last)/1e6), ms=round((b-a)/1e6, 1))
                     for a, b in zip(beats, beats[1:], strict=False) if a >= last and b-a > 33_400_000]
            result = dict(kind=kind, repetition=repetition, far_zoom=far, depth=round(depth, 1), events=len(steps),
                          span_ms=round((last-first)/1e6), frames=len(active),
                          median_ms=round(percentile(gaps, .5), 1), p95_ms=round(percentile(gaps, .95), 1),
                          p99_ms=round(percentile(gaps, .99), 1), worst_ms=round(max(gaps), 1),
                          over_20=sum(g > 20 for g in gaps), over_50=sum(g > 50 for g in gaps),
                          over_100=sum(g > 100 for g in gaps), long_gaps=long, stalls_after=after,
                          after_changes=what['changes'], after_python=what['python'], machine_busy_percent=busy,
                          way=args.way, returned=abs(plan.property('zoom')/far-1) < .02)
            if args.native:
                result['native_ms'] = args.native.summary(first, last)
                print('    Qt, median/p95/worst ms: '+'  '.join(f"{k} {v['median']:.0f}/{v['p95']:.0f}/{v['worst']}"
                                                              for k, v in result['native_ms'].items()), flush=True)
            report['runs'].append(result)
            print(f"{kind} {repetition}: depth x{result['depth']} frames {result['frames']} median {result['median_ms']}"
                  f" p95 {result['p95_ms']} worst {result['worst_ms']} >50: {result['over_50']} >100: {result['over_100']}"
                  f" | after the hand: {', '.join(str(s['ms'])+'@'+str(s['at_ms']) for s in after) or 'none'}"
                  f" | machine busy {busy} %", flush=True)
            if args.trace:
                print('    after the hand, states: '+', '.join(f"{c['name']}={c['value']:.4g}@{c['at_ms']}"
                                                              for c in what['changes']), flush=True)
                print('    after the hand, Python: '+', '.join(f"{c['where']} {c['ms']} ms" for c in what['python']),
                      flush=True)
            for gap in long:
                if gap['ms'] > 50:
                    print(f"    {gap['ms']} ms at {gap['at_ms']} ms, {gap['way']}, module {gap['module_px']} px", flush=True)
    return report


def sequence(args, setup, app, host, plan):
    """Daniel's gesture (20/11/2026: «un blocco da mezzo secondo circa, immancabile quando faccio un paio di zoom in
    e zoom out»): a few zooms in and out in a row from a middle scale, a short rest between one and the next, as a
    hand does. Every gap counts, those of the rests too: the stall that comes while the hand rests is the one felt
    when it starts again. Passed when no gap is over 50 ms."""
    from gesture_bench_core import percentile
    from gesture_bench_qt import Input
    from gesture_bench_ui import evaluate
    window = host.window
    module = evaluate(plan, 'backend.moduleSize')
    report = dict(project=args.project.name, modules=host.bridge.moduleCount, size=[window.width(), window.height()],
                  dpr=window.devicePixelRatio(), screen=window.screen().name(), tiles=args.tiles,
                  graphics_api=str(window.rendererInterface().graphicsApi()), start_px=args.at or 12,
                  factor=args.factor, trips=args.trips, rest_ms=args.rest, runs=[])
    for kind in args.run:
        for repetition in range(args.repetitions):
            evaluate(plan, 'fit()')
            setup.turn_events(app, 1000)
            evaluate(plan, ANCHOR+'; zoomAt(%r/zoom, p.x, p.y) })()' % ((args.at or 12)/module))
            setup.turn_events(app, 4000)
            anchor = evaluate(plan, ANCHOR+'; return [p.x-width/2, p.y-height/2] })()')
            x, y = float(anchor[0]), float(anchor[1])
            steps, at = [], 0.
            if kind == 'pinch':
                steps.append(dict(at_ms=0, action='native', phase='begin', value=0, x=x, y=y))
            for stroke in range(2*args.trips):
                way = 1 if stroke % 2 == 0 else -1
                if kind == 'wheel':
                    notches = max(1, round(math.log(args.factor)/math.log(1.2)))
                    for _ in range(notches):
                        at += 45
                        steps.append(dict(at_ms=at, action='wheel', angle=120*way, x=x, y=y))
                else:
                    count = 48                           # 0,4 s at 120 Hz
                    value = args.factor**(1/count)-1
                    for _ in range(count):
                        at += 1000/120
                        steps.append(dict(at_ms=at, action='native', phase='update',
                                          value=value if way > 0 else 1/(1+value)-1, x=x, y=y))
                at += args.rest
            if kind == 'pinch':
                steps.append(dict(at_ms=at, action='native', phase='end', value=0, x=x, y=y))
            what, load = {}, machine_times()
            swaps, beats, zooms, sent = play(window, plan, Input(app, host, plan), steps, 1500, after=what, whole=True)
            busy = machine_busy(load, machine_times())
            first, end = sent[0], sent[-1]+1_500_000_000
            times = [t for t in swaps if first <= t <= end]
            pairs = list(zip(times, times[1:], strict=False))
            gaps = [(b-a)/1e6 for a, b in pairs]

            def resting(t, sent=sent):
                last = max((e for e in sent if e <= t), default=sent[0])
                return t-last > 60_000_000
            long = [dict(at_ms=round((a-first)/1e6), ms=round((b-a)/1e6, 1), hand='rests' if resting(a) else 'moves',
                         module_px=round(next((z for at_, z in reversed(zooms) if at_ <= a), zooms[0][1])*module, 1))
                    for a, b in pairs if b-a > 50_000_000]
            stalls = [round((b-a)/1e6, 1) for a, b in zip(beats, beats[1:], strict=False) if b-a > 50_000_000 and a >= first]
            result = dict(kind=kind, repetition=repetition, events=len(steps), frames=len(times),
                          median_ms=round(percentile(gaps, .5), 1), p95_ms=round(percentile(gaps, .95), 1),
                          worst_ms=round(max(gaps), 1), over_50=len(long), over_100=sum(g['ms'] > 100 for g in long),
                          gaps_over_50=long, gui_stalls_over_50=stalls, machine_busy_percent=busy,
                          after_changes=what['changes'], after_python=what['python'])
            report['runs'].append(result)
            print(f"{kind} {repetition}: {args.trips} trips x{args.factor:g} from {args.at or 12:g} px, rest {args.rest} ms:"
                  f" median {result['median_ms']} p95 {result['p95_ms']} WORST {result['worst_ms']} ms,"
                  f" over 50 ms: {result['over_50']}, over 100 ms: {result['over_100']} | machine busy {busy} %", flush=True)
            for gap in long:
                near = [f"{c['name']}@{c['at_ms']}" for c in what['changes'] if gap['at_ms']-20 <= c['at_ms'] <= gap['at_ms']+gap['ms']+20]
                gap['with'] = near
                print(f"    {gap['ms']} ms at {gap['at_ms']} ms, hand {gap['hand']}, module {gap['module_px']} px"
                      f"{'  <- '+', '.join(near) if near else ''}", flush=True)
            if args.trace:
                print('    Python on the window thread: '+', '.join(f"{c['where']} {c['ms']} ms" for c in what['python']),
                      flush=True)
    return report


def sharpness(image, box):
    """Mean absolute second difference of the luminance in the box: what a stretched image loses first."""
    import numpy as np
    from PySide6.QtGui import QImage
    image = image.convertToFormat(QImage.Format_Grayscale8)
    pixels = np.frombuffer(image.constBits(), dtype=np.uint8).reshape(image.height(), image.bytesPerLine())
    x, y, w, h = box
    area = pixels[y:y+h, x:x+w].astype(np.int32)
    return float(np.abs(area[1:-1, 1:-1]*4-area[:-2, 1:-1]-area[2:, 1:-1]-area[1:-1, :-2]-area[1:-1, 2:]).mean())


def frames(args, setup, app, host, plan):
    """The way in, grabbed at some scales while the hand moves, each beside the same view settled."""
    from gesture_bench_qt import Input
    from gesture_bench_ui import evaluate
    window = host.window
    stem = args.out.with_suffix('')
    module = evaluate(plan, 'backend.moduleSize')
    report = dict(project=args.project.name, modules=host.bridge.moduleCount, dpr=window.devicePixelRatio(),
                  tiles=args.tiles, theme=args.theme, frames=[])
    for kind in args.run:
        evaluate(plan, 'fit()')
        setup.turn_events(app, 2500)
        steps, _, anchor = travel(kind, plan, args.near_px, args.seconds)
        steps = steps[:len(steps)//2]
        wanted = {round(len(steps)*part) for part in (.2, .4, .6, .8, .97)}
        grabbed = []

        def on_step(done, wanted=wanted, grabbed=grabbed):
            if done in wanted:
                # the frame that shows this step, then the grab: the hand has not stopped
                setup.turn_events(app, 25)
                grabbed.append((window.grabWindow(), {k: plan.property(k) for k in ('zoom', 'panX', 'panY')}))
        play(window, plan, Input(app, host, plan), steps, 100, on_step, observe=False)
        origin = plan.mapToScene(plan.boundingRect().topLeft())
        for index, (moving, camera) in enumerate(grabbed):
            evaluate(plan, "(function(){ pendingMotion={x:%r,y:%r,zoom:%r}; applyMotion() })()"
                     % (camera['panX'], camera['panY'], camera['zoom']))
            setup.turn_events(app, 2500)
            still = window.grabWindow()
            ratio = moving.width()/window.width()
            # around the point the zoom holds still, where the modules are; clear of the bars over the plan
            left = min(max(plan.width()*.08, plan.width()/2+anchor[0]-plan.width()*.2), plan.width()*.52)
            top = min(max(plan.height()*.15, plan.height()/2+anchor[1]-plan.height()*.25), plan.height()*.4)
            box = [int((origin.x()+left)*ratio), int((origin.y()+top)*ratio),
                   int(plan.width()*.4*ratio), int(plan.height()*.5*ratio)]
            row = dict(kind=kind, zoom=camera['zoom'], module_px=round(camera['zoom']*module, 1),
                       sharpness_moving=round(sharpness(moving, box), 2), sharpness_settled=round(sharpness(still, box), 2))
            row['kept'] = round(row['sharpness_moving']/row['sharpness_settled'], 2) if row['sharpness_settled'] else None
            for name, image in (('gesto', moving), ('fermo', still)):
                path = stem.with_name(f'{stem.name}-{kind}-{index+1}-{name}.png')
                if path.exists():
                    raise FileExistsError(path)
                # the middle of the plan at full resolution: what the eye sees, small enough to keep
                image.copy(*box).save(str(path))
                row[name] = path.name
            report['frames'].append(row)
            print(f"{kind} module {row['module_px']} px: sharpness kept while moving {row['kept']}", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('--source-root', type=Path, default=ROOT, help='the sources measured (an exported commit)')
    parser.add_argument('--out', type=Path, required=True, help='new JSON summary; the frames are saved beside it')
    parser.add_argument('--size', type=int, nargs=2, default=(1500, 840))
    parser.add_argument('--theme', choices=('light', 'dark'), default='light')
    parser.add_argument('--tiles', action='store_true', help='a drawn map under the plan, without network')
    parser.add_argument('--phase', choices=('model', 'plant'), default='plant')
    parser.add_argument('--qsg', action='store_true', help="Qt's own frame timings beside each run (diagnostic)")
    parser.add_argument('--timeline', action='store_true')
    parser.add_argument('--sequence', action='store_true', help='a few zooms in and out in a row, rests included')
    parser.add_argument('--trips', type=int, default=3, help='zooms in and back of the sequence')
    parser.add_argument('--factor', type=float, default=4., help='how much each zoom of the sequence goes in')
    parser.add_argument('--rest', type=int, default=400, help='the rest between two zooms of the sequence, ms')
    parser.add_argument('--at', type=float, help='the module size, in pixels, the timeline is taken at')
    parser.add_argument('--frames', action='store_true')
    parser.add_argument('--redraw', action='store_true', help='the cost of drawing the geometry again, by scale')
    parser.add_argument('--scales', type=float, nargs='+', default=[2, 6, 14, 40, 120, 300], help='module sizes in pixels')
    parser.add_argument('--hide', nargs='*', default=[], help='object names hidden, to find what a layer costs')
    parser.add_argument('--redraws', type=int, default=3)
    parser.add_argument('--image-samples', type=int, help="the samples of the geometry's image (diagnostic)")
    parser.add_argument('--image-scale', type=float, help="the image's pixels, as a share of the screen's (diagnostic)")
    parser.add_argument('--settled', type=float, help='the zoom the dashes are held at in the redraw pass')
    parser.add_argument('--slow', type=int, default=0, help='with --qsg, print the frames with a phase this long, ms')
    parser.add_argument('--trace', action='store_true', help='print the camera and the drawn camera at every step')
    parser.add_argument('--step', choices=('pan', 'zoom'), default='pan', help='what moves between two redraws')
    parser.add_argument('--renderer', choices=('batched', 'triangles'), help='the plan renderer of the redraw pass')
    parser.add_argument('--run', nargs='+', choices=('wheel', 'pinch'), default=['wheel', 'pinch'])
    parser.add_argument('--way', choices=('both', 'in'), default='both', help='the whole travel, or only the way in')
    parser.add_argument('--near-px', type=float, default=300, help='a module on screen at the near end, in pixels')
    parser.add_argument('--seconds', type=float, default=1.5, help='the way in; the way back takes as long')
    parser.add_argument('--repetitions', type=int, default=2)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    with tempfile.TemporaryDirectory(prefix='meridiana-zoom-probe-') as folder:
        setup, app, host, plan = open_window(args, Path(folder))
        try:
            report = (timeline if args.timeline else sequence if args.sequence else frames if args.frames
                      else redraw if args.redraw else run)(
                args, setup, app, host, plan)
        finally:
            host.close()
            app.processEvents()
    args.out.write_text(json.dumps(report, indent=2), encoding='utf8')
    print(args.out)


if __name__ == '__main__':
    main()
