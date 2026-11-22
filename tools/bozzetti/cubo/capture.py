"""Capture the real cube, then isolated QML proposals, without desktop windows."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PySide6.QtCore import QEvent, QPointF, QSize, Qt, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlEngine, QQmlExpression

from meridiana.core.model.model import Project
from meridiana.gui.application import QuickWindow, create_app
from meridiana.gui.backend.controls import install_controls
from quick.gestures import item, mouse, pump, wait_for


def evaluate(obj, expression):
    expr = QQmlExpression(QQmlEngine.contextForObject(obj), obj, expression)
    value, _ = expr.evaluate()
    if expr.hasError():
        raise RuntimeError(expr.error().toString())
    return value


def grab(item, path, scale):
    if path.exists():
        raise FileExistsError(path)
    # Qt applies the window DPR itself. Multiplying here would apply it twice.
    result = item.grabToImage(QSize(round(item.width()), round(item.height())))
    ready = []
    result.ready.connect(lambda: ready.append(True))
    wait_for(lambda: bool(ready), 15)
    image = result.image()
    if image.isNull() or not image.save(str(path)):
        raise RuntimeError(f'Capture failed: {path}')
    return image


def target(cube, kind):
    return evaluate(cube, '''JSON.stringify((function() {
        let cells = projectedCells.filter(c => c.part.filter(v => v !== 0).length === %d);
        let c = cells[Math.floor(cells.length/2)];
        return [width/2+c.polygon.reduce((s,p)=>s+p[0],0)/4,
                height/2+c.polygon.reduce((s,p)=>s+p[1],0)/4];
    })())''' % {'face': 1, 'edge': 2, 'corner': 3}[kind])


def real(app, args):
    project, notice = Project.load(args.project)
    if notice:
        raise RuntimeError(notice)
    with tempfile.TemporaryDirectory(prefix='cube-study-', ignore_cleanup_errors=True) as folder:
        host = QuickWindow(project, Path(folder), real_views=True,
                           theme={'theme': args.theme, 'reducedMotion': True})
        host.plan.configureMaps({'offline': True})
        win = host.window
        win.resize(1400, 960)
        win.setProperty('viewMode', '3d')
        win.show()
        pump(1600)
        win.resize(1400, 960)
        pump(100)
        cube = item(win, 'viewCube')
        evaluate(cube, 'compact = true')
        pump(100)
        assert cube.property('compact') and cube.width() == 76
        evidence = []
        for state in ('rest', 'face', 'edge', 'corner', 'arrow', 'menu'):
            mouse(app, win, QEvent.MouseMove, QPointF(10, win.height()-10), Qt.NoButton, Qt.NoButton)
            if state in ('face', 'edge', 'corner'):
                point = QPointF(*json.loads(target(cube, state)))
            else:
                point = QPointF(cube.width()-9, cube.height()-8)
            if state != 'rest':
                mouse(app, win, QEvent.MouseMove, cube.mapToScene(point), Qt.NoButton, Qt.NoButton)
            if state == 'menu':
                evaluate(cube, 'activate("menu", false)')
            pump(160)
            prefix = f'real-{args.theme}-x{args.scale}-{state}'
            image = grab(win.contentItem(), args.output / f'{prefix}-context.png', args.scale)
            pos = cube.mapToScene(QPointF())
            # Include the popup below and to the left of its right edge.
            box = [max(0, pos.x()-260), max(0, pos.y()-12), 590, 250]
            crop = image.copy(*[round(v*args.scale) for v in box])
            crop.save(str(args.output / f'{prefix}.png'))
            evidence.append({'state': state, 'hoverTarget': cube.property('hoverTarget'),
                             'cube': [pos.x(), pos.y(), cube.width(), cube.height()],
                             'image': [image.width(), image.height()]})
        (args.output / f'real-{args.theme}-x{args.scale}.json').write_text(
            json.dumps(evidence, indent=2), encoding='utf-8')
        if host.warnings:
            raise RuntimeError('\n'.join(host.warnings))
        host.close()
        pump(100)


def proposals(app, args):
    engine = QQmlApplicationEngine()
    theme = install_controls(engine, {'theme': args.theme, 'reducedMotion': True})
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name('Study.qml'))))
    assert engine.rootObjects(), warnings
    win = engine.rootObjects()[0]
    win.show()
    pump(300)
    for variant in ('A', 'B', 'C'):
        win.setProperty('variant', variant)
        for state in ('rest', 'face', 'edge', 'corner', 'arrow', 'menu'):
            if variant == 'C' and state in ('arrow', 'menu'):
                continue
            win.setProperty('stateName', state)
            cube = item(win, 'viewCube')
            from PySide6.QtCore import QObject
            evaluate(cube.findChild(QObject, 'viewCubeMenu'), 'close()')
            mouse(app, win, QEvent.MouseMove, QPointF(12, 240), Qt.NoButton, Qt.NoButton)
            if variant == 'A' and state != 'rest':
                point = QPointF(*json.loads(target(cube, state))) if state in ('face', 'edge', 'corner') else QPointF(67, 68)
                mouse(app, win, QEvent.MouseMove, cube.mapToScene(point), Qt.NoButton, Qt.NoButton)
                if state == 'menu':
                    evaluate(cube, 'activate("menu", false)')
            pump(150)
            grab(win.contentItem(), args.output / f'{variant}-{args.theme}-x{args.scale}-{state}.png', args.scale)
    if warnings:
        raise RuntimeError('\n'.join(warnings))
    win.close()
    del theme


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('real', 'proposals'))
    parser.add_argument('--theme', choices=('light', 'dark'), required=True)
    parser.add_argument('--scale', type=float, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--project', type=Path)
    args = parser.parse_args()
    assert os.environ.get('QT_QPA_PLATFORM') == 'offscreen'
    args.output.mkdir(parents=True, exist_ok=True)
    app = create_app()
    (real if args.mode == 'real' else proposals)(app, args)
    print(f'{args.mode}: {args.theme}, x{args.scale}, complete', flush=True)


if __name__ == '__main__':
    main()
