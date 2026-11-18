"""Repeatable D3D renderer comparison and genuine window captures, never personal settings.

Run separately per renderer/count/scale to isolate scene graph allocations and caches.
These timings include grabWindow readback; they do not measure presentation on a monitor.
"""
import argparse
import json
import math
import os
import statistics
import time
from pathlib import Path

os.environ.setdefault('QSG_RENDER_LOOP', 'threaded')
os.environ.setdefault('QSG_RHI_BACKEND', 'd3d11')
os.environ['QML_DISABLE_DISK_CACHE'] = '1'

from PySide6.QtCore import QObject, QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from meridiana import i18n, jobs, model  # noqa: E402
from meridiana.quick.backend.plan import PlanController, qml_objects  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--renderer', choices=['batched', 'triangles', 'geometry', 'shapes', 'canvas'], default='batched')
    parser.add_argument('--count', type=int, default=778)
    parser.add_argument('--width', type=int, default=1366)
    parser.add_argument('--height', type=int, default=900)
    parser.add_argument('--dark', action='store_true')
    parser.add_argument('--frames', type=int, default=30)
    parser.add_argument('--rho', action='store_true')
    args = parser.parse_args()
    app = QGuiApplication([])
    i18n.setup('it')
    project = (model.Project.load(ROOT/'docs/quick/compat/fixtures/rho.meridiana')[0] if args.rho
               else model.Project(name='Renderer fixture'))
    backend = PlanController(project, manage_layout=False)
    if args.rho:
        results, keys, _ = jobs.layout_of(project)
        backend.session.layout_done(backend.session.generation, results, keys)
    engine = QQmlApplicationEngine()
    errors = []
    engine.warnings.connect(lambda values: errors.extend(x.toString() for x in values))
    backend.install(engine)
    from meridiana.quick.backend.tokens import install_theme
    install_theme(engine).configure({'theme': 'dark' if args.dark else 'light'})
    columns = math.ceil(math.sqrt(args.count * .6))
    raw = [dict(kind='module', oid='s1', key=str(i), rid=str(i//columns),
                points=[[i%columns*1.3, i//columns*2.5], [i%columns*1.3+1.13, i//columns*2.5],
                        [i%columns*1.3+1.13, i//columns*2.5+2.27], [i%columns*1.3, i//columns*2.5+2.27]])
           for i in range(args.count)]
    if args.rho:
        raw = backend._scene['modules']
        args.count = len(raw)
    else:
        backend._modules = qml_objects(raw)
        backend._bounds = [0., 0., columns*1.3, math.ceil(args.count/columns)*2.5]
    engine.rootContext().setContextProperty('planBackend', backend)
    start = time.perf_counter()
    engine.load(QUrl.fromLocalFile(str(ROOT/'src/meridiana/quick/qml/Meridiana/Plan/PlanWindow.qml')))
    if not engine.rootObjects():
        raise RuntimeError(errors)
    window = engine.rootObjects()[0]
    window.resize(args.width,args.height)
    plan = window.findChild(QObject, 'plan')
    plan.setProperty('renderer', args.renderer)
    window.show()
    QTest.qWaitForWindowExposed(window)
    QTest.qWait(300)
    deadline=time.monotonic()+60
    while plan.property('renderedModules') != args.count and time.monotonic()<deadline:
        QTest.qWait(20)
    if plan.property('renderedModules') != args.count:
        raise AssertionError('Native paths did not finish preparing')
    QTest.qWait(50)
    startup_ms = (time.perf_counter()-start)*1000
    frames = []
    out = ROOT/'build/quick-foto/pianta/renderers'
    out.mkdir(parents=True,exist_ok=True)
    name = ('rho-' if args.rho else '') + f'{args.renderer}-{args.count}-s{window.devicePixelRatio():g}-{args.width}-{args.height}-' + ('dark' if args.dark else 'light')
    image = window.grabWindow()
    image.save(str(out/(name+'.png')))
    # A status strip or compass is not evidence that the module geometry exists.
    for index in (0, args.count//4, args.count//2, args.count-1):
        corners=raw[index]['points']
        x=sum(p[0] for p in corners)/4*plan.property('zoom')+plan.property('panX')
        y=sum(p[1] for p in corners)/4*plan.property('zoom')+plan.property('panY')
        dpr=window.devicePixelRatio()
        colour=image.pixelColor(int(x*dpr),int(y*dpr))
        if colour == image.pixelColor(0,0):
            raise AssertionError(f'Module {index} is absent at {x},{y}')
    image.save(str(out/(name+'.png')))
    geometry = window.findChild(QObject, 'moduleGeometry')
    uploads = geometry.uploads
    backend.calls.clear()
    pan = plan.property('panX')
    cpu_frames=[]
    for i in range(args.frames):
        tick=time.perf_counter()
        plan.setProperty('panX',pan + math.sin(i/8)*70)
        plan.setProperty('zoom',plan.property('zoom')*(1.005 if i<15 else 1/1.005))
        app.processEvents()
        cpu_frames.append((time.perf_counter()-tick)*1000)
        frame=window.grabWindow()
        if frame.isNull():
            raise AssertionError('An empty frame is not a fast frame')
        frames.append((time.perf_counter()-tick)*1000)
    # Pixels inside and outside representative module centres prove the fixture rendered.
    non_background=0
    ground=image.pixelColor(0,0)
    for y in range(0,image.height(),8):
        for x in range(0,image.width(),8):
            non_background += image.pixelColor(x,y) != ground
    result=dict(renderer=args.renderer,count=args.count,dpr=window.devicePixelRatio(),size=[args.width,args.height],
                graphics_api=str(window.rendererInterface().graphicsApi()), startup_ms=startup_ms,
                median_ms=statistics.median(frames),p95_ms=sorted(frames)[math.ceil(.95*len(frames))-1],
                max_ms=max(frames),frames_ms=frames,backend_calls=dict(backend.calls),
                cpu_process_events_ms=cpu_frames, cpu_median_ms=statistics.median(cpu_frames),
                cpu_max_ms=max(cpu_frames), fixture='rho' if args.rho else 'synthetic',
                geometry_uploads_during_navigation=geometry.uploads-uploads,
                non_background_samples=non_background,warnings=errors)
    (out/(name+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:(list(dict.fromkeys(v)) if k=='warnings' else v) for k,v in result.items() if k!='frames_ms'}),flush=True)
    window.close(); backend.close(); engine.deleteLater(); app.processEvents()
    if errors or non_background<100 or backend.calls.get('pointer',0) or result['geometry_uploads_during_navigation']:
        raise SystemExit(1)


if __name__=='__main__':
    main()
