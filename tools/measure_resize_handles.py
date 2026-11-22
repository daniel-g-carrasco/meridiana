"""A one-second, 300 logical-pixel drag, with real frame signals and system load."""
import ctypes
import json
import os
import statistics
import tempfile
import time
from collections import Counter
from pathlib import Path

import _setup  # noqa: F401
from PySide6.QtCore import QEvent, QPointF, Qt
from meridiana.app import jobs, pipeline
from meridiana.gui.sample import recorded_weather
from probe_resize_handles import PHASES, hover, prepare, window
from quick.gestures import item, mouse, point, pump, wait_for


def cpu_times():
    values = [ctypes.c_ulonglong() for _ in range(3)]
    if not ctypes.windll.kernel32.GetSystemTimes(*(ctypes.byref(v) for v in values)):
        raise ctypes.WinError()
    return [v.value for v in values]


def cpu_percent(before, after):
    idle, kernel, user = [b-a for a, b in zip(before, after, strict=True)]
    return round(100*(1-idle/(kernel+user)), 1) if kernel+user else None


def walk(node):
    yield node
    for child in node.childItems():
        yield from walk(child)


def measure(app, host):
    out = []
    win = host.window
    results = host.parts.controllers['results']
    for phase in PHASES:
        ws = prepare(host, phase)
        ws.setProperty('rightExtent', 600)
        if phase == 'report':
            report = host.parts.controllers['report']
            wait_for(lambda report=report: not report.busy and bool(report.pages), 180)
        pump(600)
        stamps, render_starts, render_costs = [], [], []
        counts = Counter()
        bindings = []

        def connect(signal, name, counts=counts, bindings=bindings):
            def count():
                counts[name] += 1
            signal.connect(count)
            bindings.append((signal, count))

        for obj in list(walk(win.contentItem())):
            if obj.metaObject().indexOfProperty('chartData') >= 0:
                connect(obj.widthChanged, 'chart_width')
                connect(obj.heightChanged, 'chart_height')
                connect(obj.chartDataChanged, 'chart_data')
                connect(obj.geometryChanged, 'chart_geometry')
            if obj.metaObject().indexOfProperty('viewName') >= 0:
                connect(obj.widthChanged, 'table_width')
                connect(obj.modelChanged, 'table_model')
            if obj.objectName() == 'reportPreview':
                connect(obj.pageWidthChanged, 'paper_width')
                connect(obj.drawnWidthChanged, 'paper_raster_width')
        report = host.parts.controllers['report']
        connect(report.pagesChanged, 'report_pages')
        connect(report.changed, 'report_state')
        for name in ('productionChanged', 'consumptionChanged', 'economicsChanged'):
            connect(getattr(results, name), name)

        def frame(stamps=stamps):
            stamps.append(time.perf_counter())

        def rendering(render_starts=render_starts):
            render_starts.append(time.perf_counter())

        def rendered(render_starts=render_starts, render_costs=render_costs):
            if render_starts:
                render_costs.append((time.perf_counter()-render_starts[-1])*1000)

        win.frameSwapped.connect(frame)
        win.beforeRendering.connect(rendering)
        win.afterRendering.connect(rendered)
        handle = item(win, 'rightResizeHandle')
        pos = point(handle)
        hover(app, win, pos)
        before_width = item(win, 'rightPanel').width()
        load_before = cpu_times()
        started = time.perf_counter()
        mouse(app, win, QEvent.Type.MouseButtonPress, pos, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
        grabbed = bool(handle.property('pressed'))
        steps = 0
        while True:
            fraction = min(1, time.perf_counter()-started)
            target = pos+QPointF(300*fraction, 0)
            mouse(app, win, QEvent.Type.MouseMove, target, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
            steps += 1
            win.requestUpdate()
            if fraction >= 1:
                break
            pump(max(1, min(16, int((1-fraction)*1000))))
        mouse(app, win, QEvent.Type.MouseButtonRelease, pos+QPointF(300, 0),
              Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)
        elapsed = time.perf_counter()-started
        load_after = cpu_times()
        win.frameSwapped.disconnect(frame)
        win.beforeRendering.disconnect(rendering)
        win.afterRendering.disconnect(rendered)
        for signal, callback in bindings:
            signal.disconnect(callback)
        intervals = [(b-a)*1000 for a, b in zip(stamps, stamps[1:], strict=False)]
        row = dict(phase=phase, seconds=round(elapsed, 3), input_steps=steps, grabbed=grabbed,
                   delta=round(item(win, 'rightPanel').width()-before_width, 1),
                   frames=len(stamps), median_ms=round(statistics.median(intervals), 2) if intervals else None,
                   worst_ms=round(max(intervals), 2) if intervals else None,
                   render_median_ms=round(statistics.median(render_costs), 2) if render_costs else None,
                   render_worst_ms=round(max(render_costs), 2) if render_costs else None,
                   cpu_percent=cpu_percent(load_before, load_after), changes=dict(counts))
        out.append(row)
        print(json.dumps(row), flush=True)
    return out


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
        folder = Path(temporary)
        app, host = window(folder)
        try:
            # Real Rho geometry and a computed year using the repository's recorded weather, offline.
            project = host.bridge.session.project
            print('PREPARING YEAR', recorded_weather(project, folder), flush=True)
            layouts, keys, _laid = jobs.layout_of(project)
            energy = pipeline.compute(project, layouts, folder, fetch=False).as_dict()
            host.bridge.session.take_year(layouts, keys, energy)
            wait_for(lambda: not host.parts.controllers['results'].busy, 120)
            report = host.parts.controllers['report']
            report.requestPreview()
            wait_for(lambda: not report.busy, 180)
            if not report.pages:
                raise RuntimeError('Report preview has no pages: ' + report.error)
            pump(1500)
            before = cpu_times()
            pump(1000)
            quiet = cpu_percent(before, cpu_times())
            data = dict(cpu_count=os.cpu_count(), idle_sample_cpu_percent=quiet,
                        renderer=host.window.rendererInterface().graphicsApi().name,
                        energy_simulation=bool(energy.get('sim')), report_preview_pages=len(report.pages),
                        rows=measure(app, host))
            Path('docs/revisioni/maniglie-prestazioni.json').write_bytes(
                json.dumps(data, indent=2).replace('\n', '\r\n').encode())
        finally:
            host.close()
            pump(100)
