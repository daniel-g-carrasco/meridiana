"""Compatibility hardware-texture mode. This is a render-cost diagnostic, not display cadence."""
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace

from gesture_bench_core import GESTURES, VERSION, analyze
from gesture_bench_qt import Input, camera, execute, memory


def run(args, cases, app, setup):
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlProperty
    from meridiana.app import jobs
    from meridiana.core.model.model import Project
    from meridiana.gui.backend.plan import PlanController
    from gesture_bench import sha256, write_new
    from gesture_bench_core import gesture_steps
    from gesture_bench_ui import evaluate
    from gesture_bench_visual import analyze_pixels
    from plan_render_probe import PlanRenderProbe
    if any(s['view'] != 'plan' for s in cases) or not args.project:
        raise ValueError('--render-control requires a project and --views plan')
    digest = sha256(args.project)
    report = dict(version=VERSION, project_sha256=digest, cases=[], environment=dict(
        platform='render-control', graphics_api='Direct3D11', screen_on=None,
        timing='externally paced render target, not compositor cadence', refresh_hz=args.refresh_hz or 120))
    with tempfile.TemporaryDirectory(prefix='meridiana-gesture-rhi-') as folder:
        project, _ = Project.load(args.project, Path(folder))
        results, keys, _ = jobs.layout_of(project)
        controller = PlanController(project, manage_layout=False, cache=Path(folder))
        controller.session.layout_done(controller.session.generation, results, keys)
        controller.setPhase(args.phase)
        controller.setNavigation('autocad')
        controller.configureMaps({'offline': not args.maps or args.fixture_tiles})
        engine = QQmlApplicationEngine()
        controller.install(engine)
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(
            args.source_root/'src/meridiana/gui/qml/Meridiana/Plan/Plan.qml')))
        view = component.createWithInitialProperties({'backend': controller})
        if view is None:
            raise RuntimeError([e.toString() for e in component.errors()])
        probe = PlanRenderProbe(view, size=tuple(args.size), dpr=args.scale or 2)
        if args.layer_samples is not None:
            # the geometry's one image holds the samples since R706 (it was the surface's own layer)
            surface = view.findChild(__import__('PySide6.QtCore', fromlist=['QObject']).QObject, 'motionSnapshot')
            QQmlProperty.write(surface, 'samples', args.layer_samples)
        try:
            for _ in range(10):
                evaluate(view, 'fit()')
                probe.render()
                setup.turn_events(app, 30)
            if args.fixture_tiles:
                from PySide6.QtGui import QColor, QImage
                tile = QImage(256, 256, QImage.Format_RGB32)
                tile.fill(QColor('#506149'))
                controller.configureMaps({'source': 'osm'})
                for key in list(controller.maps.state.wanted | controller.maps.state.backdrop):
                    controller.maps._ready(*key, tile)
            for scenario in cases:
                for gesture in scenario['only'] or GESTURES[:6]:
                    evaluate(view, 'fit()')
                    for _ in range(5):
                        probe.render()
                        setup.turn_events(app, 25)
                    initial = {k: view.property(k) for k in ('panX', 'panY', 'zoom')}
                    observer = SimpleNamespace(state=lambda: camera(view), rows=[], gui_ms=0.)
                    steps = gesture_steps(gesture, scenario['seed'], args.rate, args.duration)
                    sender = Input(app, SimpleNamespace(window=probe.window), view)
                    def render(observer=observer):
                        started = time.perf_counter_ns()
                        sample = probe.render()
                        observer.rows.append(dict(version=VERSION, record='frame', t_ns=time.perf_counter_ns(),
                            sync_ns=started, camera=observer.state(), gpu_ms=sample['gpu_ms'],
                            polish_ms=sample['polish_ms'], sync_ms=sample['sync_ms'], render_ms=sample['render_ms'],
                            render_frame_ms=sample['draw_ms'], gui_events_ms=observer.gui_ms))
                        observer.gui_ms = 0.
                    samples, _ = execute(app, probe.window, observer, sender, steps, args.tail_ms, args.profile, render=render)
                    ident = f"{args.phase}-plan-{gesture}-s{scenario['seed']}-r{scenario['repetition']}"
                    raw = args.out.with_name(args.out.stem+'-'+ident+'.jsonl')
                    for seq, row in enumerate(observer.rows, 1):
                        row['seq'] = seq
                    session = dict(version=VERSION, record='session', seq=0, t_ns=0, case=ident,
                                   environment=report['environment'])
                    write_new(raw, '\n'.join(json.dumps(r) for r in [session, *observer.rows])+'\n')
                    case = dict(id=ident, phase=args.phase, view='plan', gesture=gesture, seed=scenario['seed'],
                                analysis=analyze(observer.rows, args.refresh_hz or 120), raw=raw.name,
                                theme=args.theme, input_unchanged=True, memory_after=memory(), gui_samples=samples)
                    if args.visuals:
                        for key, value in initial.items():
                            evaluate(view, key+' = '+json.dumps(value))
                        pixel = SimpleNamespace(state=lambda: camera(view), rows=[], gui_ms=0.)
                        _, captures = execute(app, probe.window, pixel, sender, steps, args.tail_ms,
                            pixels=True, grab=lambda: probe.render(readback=True), render=probe.render)
                        last = max(r['t_ns'] for r in pixel.rows if r['record'] == 'event')
                        case['pixel_pass'] = analyze_pixels(captures, last)
                    report['cases'].append(case)
                    print(ident, flush=True)
            driver = probe.rhi.driverInfo()
            report['environment']['driver'] = bytes(driver.deviceName).decode('utf-8', errors='replace')
        finally:
            probe.close()
            controller.close()
            engine.deleteLater()
            app.processEvents()
    if sha256(args.project) != digest:
        raise AssertionError('input changed')
    return report
