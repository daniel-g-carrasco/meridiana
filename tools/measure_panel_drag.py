"""The panels' edges dragged on the real window, phase by phase (R37, Daniel 21/11/2026: «il ridimensionamento delle
schede è molto scattante in qualsiasi fase»).

    python tools/measure_panel_drag.py <project> [--phases model:plan,model:3d,plant,production,consumption,economics,report]
                                       [--handles left,right,bottom] [--profile] [--out <file.json>]

A real window on MERIDIANA_TEST_SCREEN (a temporary profile, the project never written, its year computed offline from
the recorded weather), then for each phase and each edge a drag of 240 logical px out and back, one move every 8 ms as a
mouse gives them, and the intervals between the frames shown while it lasts. `--profile` adds what Python did on the
window's thread during the drags of each phase (the functions that took the most of it)."""
from __future__ import annotations

import argparse
import cProfile
import io
import json
import pstats
import statistics
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_zoom_probe as probe  # noqa: E402

PHASES = ('model:plan', 'model:3d', 'plant', 'production', 'consumption', 'economics', 'report')
HANDLES = ('left', 'right', 'bottom')
SPAN = 240.0            # logical px, out and back
STEP_MS = 8


def percentile(values, q):
    ordered = sorted(values)
    return ordered[min(len(ordered)-1, int(q*(len(ordered)-1)+.5))] if ordered else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project', type=Path)
    parser.add_argument('--phases', default=','.join(PHASES))
    parser.add_argument('--handles', default=','.join(HANDLES))
    parser.add_argument('--profile', action='store_true')
    parser.add_argument('--source-root', type=Path, default=probe.ROOT)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--no-year', action='store_true', help='skip the year (the plan and the 3D need none)')
    parser.add_argument('--close', default='', help='cards closed while dragging, to find what costs (diagnosis)')
    parser.add_argument('--hide', default='', help='object names hidden while dragging, to find what costs (diagnosis)')
    options = parser.parse_args()
    args = SimpleNamespace(project=options.project, source_root=options.source_root, theme='light', tiles=True,
                           phase='plant', qsg=False, hide=[], image_samples=None, image_scale=None, size=(3000, 1700))
    rows = []
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        setup, app, host, plan = probe.open_window(args, Path(folder))
        from PySide6.QtCore import QEvent, QMetaObject, QObject, QPointF, Qt
        from PySide6.QtGui import QMouseEvent
        from meridiana.app import jobs, pipeline
        from meridiana.gui.sample import recorded_weather
        window = host.window
        session = host.bridge.session

        def pump(ms):
            setup.turn_events(app, ms)

        def find(name):
            found = window.findChild(QObject, name)
            if found is None:
                pending = [window.contentItem()]
                while pending and found is None:
                    obj = pending.pop()
                    if obj.objectName() == name:
                        found = obj
                    pending.extend(obj.childItems())
            return found

        def mouse(kind, pos, button, buttons):
            app.sendEvent(window, QMouseEvent(kind, pos, pos, QPointF(window.mapToGlobal(pos.toPoint())),
                                              button, buttons, Qt.KeyboardModifier.NoModifier))

        started = time.perf_counter()
        report = host.parts.controllers['report']
        if not options.no_year:
            print('YEAR', recorded_weather(session.project, Path(folder)), flush=True)
            layouts, keys, _laid = jobs.layout_of(session.project)
            energy = pipeline.compute(session.project, layouts, Path(folder), fetch=False).as_dict()
            session.take_year(layouts, keys, energy)
            setup.wait_until(app, lambda: not host.parts.controllers['results'].busy, 180)
            print('YEAR READY %.0f s' % (time.perf_counter()-started), flush=True)
        window.showMaximized()
        pump(1500)
        host.shell.trigger('default_layout')
        pump(500)
        for entry in options.phases.split(','):
            phase, _, view = entry.partition(':')
            host.shell.trigger('phase_' + phase)
            pump(800)
            if view:
                window.setProperty('viewMode', view)
            if phase == 'report':
                report.requestPreview()
                setup.wait_until(app, lambda: not report.busy and bool(report.pages), 240)
            workspace = find('workspace')
            workspace.setProperty('leftExtent', 320)
            workspace.setProperty('rightExtent', 380)
            workspace.setProperty('bottomExtent', 240)
            for closed in filter(None, options.close.split(',')):
                find(closed).setProperty('opened', False)
                QMetaObject.invokeMethod(workspace, 'arrangementChanged')
            for hidden in filter(None, options.hide.split(',')):
                # every item of that name: a loader unloaded (its bindings gone too), anything else hidden
                pending = [window.contentItem()]
                while pending:
                    obj = pending.pop()
                    pending.extend(obj.childItems())
                    if obj.objectName() == hidden:
                        if obj.metaObject().indexOfProperty('active') >= 0:
                            obj.setProperty('active', False)
                        else:
                            obj.setVisible(False)
            pump(2500)
            profiler = cProfile.Profile() if options.profile else None
            for name in options.handles.split(','):
                handle = find(name + 'ResizeHandle')
                if handle is None or not handle.isVisible():
                    print(json.dumps(dict(phase=entry, handle=name, shown=False)), flush=True)
                    continue
                at = handle.mapToScene(QPointF(handle.width()/2, handle.height()/2))
                # each panel made wider (taller) and back: left to the right, right to the left, bottom upwards
                direction = {'left': QPointF(1, 0), 'right': QPointF(-1, 0), 'bottom': QPointF(0, -1)}[name]
                mouse(QEvent.Type.MouseMove, at, Qt.MouseButton.NoButton, Qt.MouseButton.NoButton)
                pump(200)
                stamps = []

                def frame(stamps=stamps):
                    stamps.append(time.perf_counter())
                window.frameSwapped.connect(frame)
                mouse(QEvent.Type.MouseButtonPress, at, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
                grabbed = bool(handle.property('pressed'))
                if profiler:
                    profiler.enable()
                begin = time.perf_counter()
                moves = 0
                in_event = in_loop = 0.
                last = at
                while True:
                    t = (time.perf_counter()-begin)/2.0          # one second out, one back
                    if t >= 1:
                        break
                    shift = SPAN*(t*2 if t < .5 else 2-t*2)
                    last = at + direction*shift
                    tick = time.perf_counter()
                    mouse(QEvent.Type.MouseMove, last, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
                    tock = time.perf_counter()
                    moves += 1
                    pump(STEP_MS)
                    in_event += tock-tick
                    in_loop += time.perf_counter()-tock
                mouse(QEvent.Type.MouseButtonRelease, last, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)
                if profiler:
                    profiler.disable()
                pump(600)
                window.frameSwapped.disconnect(frame)
                inside = [s for s in stamps if s <= begin+2.0]
                gaps = [(b-a)*1000 for a, b in zip(inside, inside[1:], strict=False)]
                after = [(b-a)*1000 for a, b in zip(stamps, stamps[1:], strict=False) if a > begin+2.0]
                row = dict(phase=entry, handle=name, grabbed=grabbed, moves=moves, frames=len(inside),
                           median=round(statistics.median(gaps), 1) if gaps else None,
                           p95=round(percentile(gaps, .95), 1) if gaps else None,
                           worst=round(max(gaps), 1) if gaps else None,
                           worst_at=round((inside[gaps.index(max(gaps))]-begin)*1000) if gaps else None,
                           over33=sum(g > 33 for g in gaps),
                           event_ms=round(in_event*1000/max(1, moves), 1), loop_ms=round(in_loop*1000/max(1, moves), 1), after_worst=round(max(after), 1) if after else None)
                rows.append(row)
                print(json.dumps(row), flush=True)
            if profiler:
                text = io.StringIO()
                pstats.Stats(profiler, stream=text).sort_stats('tottime').print_stats(14)
                lines = [line for line in text.getvalue().splitlines() if line.strip()][:26]
                print('PROFILE', entry, *lines[-16:], sep='\n', flush=True)
        host.close()
        pump(200)
    if options.out:
        options.out.write_text(json.dumps(dict(screen=window_screen_note(app), rows=rows), indent=1), encoding='utf-8')


def window_screen_note(app):
    import os
    screen = app.screens()[int(os.environ.get('MERIDIANA_TEST_SCREEN', '0'))]
    size = screen.size()
    return f'{screen.name()} {size.width()}x{size.height()} dpr {screen.devicePixelRatio()}'


if __name__ == '__main__':
    main()
