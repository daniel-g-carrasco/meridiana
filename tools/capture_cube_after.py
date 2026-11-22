"""Capture the production view cube and toolbar offscreen with an isolated profile."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PySide6.QtCore import QEvent, QPointF, QSize, Qt
from PySide6.QtQml import QQmlEngine, QQmlExpression

from meridiana.core.model.model import Building, Project
from meridiana.gui.application import QuickWindow, create_app
from quick.gestures import item, mouse, pump, wait_for


def evaluate(obj, expression):
    expr = QQmlExpression(QQmlEngine.contextForObject(obj), obj, expression)
    value, _ = expr.evaluate()
    if expr.hasError():
        raise RuntimeError(expr.error().toString())
    return value


def save(image, path):
    if path.exists():
        raise FileExistsError(path)
    if image.isNull() or not image.save(str(path)):
        raise RuntimeError(f'Could not save {path}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--theme', choices=('light', 'dark'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    app = create_app()
    project = Project()
    project.buildings = [Building('b1', 'Example', [[0, 0], [40, 0], [40, 20], [0, 20]], height=8)]
    with tempfile.TemporaryDirectory(prefix='cube-after-', ignore_cleanup_errors=True) as folder:
        host = QuickWindow(project, Path(folder), real_views=True,
                           theme={'theme': args.theme, 'reducedMotion': True})
        try:
            host.plan.configureMaps({'offline': True})
            win = host.window
            win.resize(1400, 960)
            win.setProperty('viewMode', '3d')
            win.show()
            pump(1400)
            # The shell applies its initial geometry after it is first exposed.
            win.resize(1400, 960)
            pump(400)
            cube = item(win, 'viewCube')
            viewport = item(win, 'viewport3d')
            assert cube.width() == 76
            assert host.warnings == [], host.warnings
            dpr = win.devicePixelRatio()
            scale = f'{dpr:g}'
            evidence = []
            for state in ('rest', 'face'):
                mouse(app, win, QEvent.MouseMove, QPointF(12, win.height()-12), Qt.NoButton, Qt.NoButton)
                if state == 'face':
                    target = json.loads(evaluate(cube, '''JSON.stringify((function() {
                        let c = projectedCells.filter(c => c.face)[0];
                        return [width/2+c.polygon.reduce((s,p)=>s+p[0],0)/4,
                                height/2+c.polygon.reduce((s,p)=>s+p[1],0)/4];
                    })())'''))
                    mouse(app, win, QEvent.MouseMove, cube.mapToScene(QPointF(*target)), Qt.NoButton, Qt.NoButton)
                    assert cube.property('hoverTarget').startswith('part:')
                pump(150)
                result = win.contentItem().grabToImage(QSize(round(win.width()), round(win.height())))
                ready = []
                result.ready.connect(lambda ready=ready: ready.append(True))
                wait_for(lambda ready=ready: bool(ready), 15)
                image = result.image()
                assert image.width() == round(win.width()*dpr)
                prefix = f'after-{args.theme}-x{scale}-{state}'
                save(image, args.output / f'{prefix}-context.png')
                pos = cube.mapToScene(QPointF())
                save(image.copy(round((pos.x()-8)*dpr), round((pos.y()-6)*dpr),
                                round(92*dpr), round(144*dpr)), args.output / f'{prefix}-cube.png')
                origin = viewport.mapToScene(QPointF())
                save(image.copy(round(origin.x()*dpr), round(origin.y()*dpr),
                                round(viewport.width()*dpr), round(155*dpr)), args.output / f'{prefix}-strip.png')
                evidence.append({'state': state, 'hoverTarget': cube.property('hoverTarget'),
                                 'size': [image.width(), image.height()], 'dpr': dpr})
            path = args.output / f'after-{args.theme}-x{scale}.json'
            if path.exists():
                raise FileExistsError(path)
            path.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
            assert host.warnings == [], host.warnings
            print(f'{args.theme}, x{scale}: rest and face captured, no QML warnings', flush=True)
        finally:
            host.close()
            pump(50)


if __name__ == '__main__':
    main()
