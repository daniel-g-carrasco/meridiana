"""Offscreen evidence for the checks and view bar refinements."""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]

import _setup
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtQml import QQmlEngine, QQmlExpression
from meridiana.app import jobs
from meridiana.gui.application import QuickWindow, create_app
from quick.aiuti.differential import connected_fixture
from quick.gestures import mouse, pump, wait_for


def items(root):
    result = [root]
    for node in result:
        result.extend(node.childItems())
    return result


def grab(win):
    result = win.contentItem().grabToImage()
    ready = []
    result.ready.connect(lambda: ready.append(True))
    wait_for(lambda: bool(ready), 10)
    return result.image()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage')
    parser.add_argument('theme', choices=('light', 'dark'))
    parser.add_argument('--part', choices=('checks', 'bars'), default='checks')
    parser.add_argument('--buttons', nargs='+', default=['tool_tool_measure', 'planView-background', 'planView-sun_map'])
    parser.add_argument('--states', nargs='+', default=['rest', 'hover-command', 'hover-arrow', 'press-command', 'press-arrow', 'on', 'on-hover-command', 'on-hover-arrow', 'menu'])
    args = parser.parse_args()
    app = _setup.qt_or_skip()
    create_app()
    folder = tempfile.mkdtemp(prefix='meridiana-ritocchi-')
    host = QuickWindow(connected_fixture(), Path(folder), real_views=True,
                       theme={'theme': args.theme, 'reducedMotion': True})
    host.plan.configureMaps({'offline': True})
    results, keys, _ = jobs.layout_of(host.bridge.session.project)
    host.bridge.accept_layout(host.bridge.session.generation, results, keys)
    win = host.window
    win.show()
    pump(100)
    win.resize(1600, 1100)
    pump(800)
    out = Path(__file__).resolve().parents[1] / 'build' / 'ritocchi'
    out.mkdir(parents=True, exist_ok=True)
    prefix = f'{args.stage}-{args.part}-{args.theme}-x{os.environ.get("QT_SCALE_FACTOR", "1")}'
    geometry = {}
    if args.part == 'checks':
        host.bridge.request_checks()
        wait_for(lambda: not host.bridge.checks_feed.busy())
        host.shell.trigger('phase_plant')
        pump(800)
        win.runCommand('focus_checks')
        pump(500)
        host.plan.markClicked.emit('site', '')
        wait_for(lambda: any(i.objectName() == 'checkOpened' and i.isVisible() for i in items(win.contentItem())))
        pump(200)
        image = grab(win)
        target = out / f'{prefix}.png'
        if target.exists():
            raise FileExistsError(target)
        image.save(str(target))
        selected = next(i for i in items(win.contentItem()) if i.objectName() == 'checkOpened' and i.isVisible())
        row = selected
        while not row.objectName().startswith('checks-row-'):
            row = row.parentItem()
        p = row.mapToScene(QPointF(0, 0))
        ratio = image.width() / win.width()
        for name, x, y in [('tl', 0, 0), ('tr', row.width()-16, 0),
                           ('bl', 0, row.height()-16), ('br', row.width()-16, row.height()-16)]:
            image.copy(round((p.x()+x)*ratio), round((p.y()+y)*ratio), round(16*ratio), round(16*ratio)).scaled(
                256, 256, Qt.IgnoreAspectRatio, Qt.FastTransformation).save(str(out / f'{prefix}-{name}.png'))
    else:
        host.shell.trigger('phase_model')
        host.shell.trigger('view_plan')
        pump(500)
        def find(name):
            return next(i for i in items(win.contentItem()) if i.objectName() == name and i.isVisible())
        for name in args.buttons:
            button = find(name)
            ground = find(name + 'Ground')
            split = ground.property('split')
            for state in args.states:
                button = find(name)
                mouse(app, win, QEvent.MouseMove, QPointF(5, win.height()-5), Qt.NoButton, Qt.NoButton)
                button.setProperty('active' if name.startswith('tool_') else 'checked', state.startswith('on'))
                at = button.mapToScene(QPointF(split/2 if state.endswith('command') else (split+button.width())/2, button.height()/2))
                if 'hover' in state or 'press' in state:
                    mouse(app, win, QEvent.MouseMove, at, Qt.NoButton, Qt.NoButton)
                if state.startswith('press'):
                    mouse(app, win, QEvent.MouseButtonPress, at, Qt.LeftButton, Qt.LeftButton)
                if state == 'menu':
                    QQmlExpression(QQmlEngine.contextForObject(button), button, 'children.filter(c => c.objectName.endsWith("Arrow"))[0].openMenu()').evaluate()
                pump(80)
                image = grab(win)
                target = out / f'{prefix}-{name}-{state}.png'
                if target.exists():
                    raise FileExistsError(target)
                image.save(str(target))
                at_button = button.mapToScene(QPointF())
                geometry[name] = [at_button.x(), at_button.y(), button.width(), button.height()]
                ratio = image.width() / win.width()
                image.copy(*[round(v*ratio) for v in geometry[name]]).scaled(
                    round(button.width()*4), round(button.height()*4),
                    Qt.IgnoreAspectRatio, Qt.FastTransformation).save(str(out / f'{prefix}-{name}-{state}-button.png'))
                if state.startswith('press'):
                    mouse(app, win, QEvent.MouseMove, QPointF(5, win.height()-5), Qt.NoButton, Qt.LeftButton)
                    mouse(app, win, QEvent.MouseButtonRelease, QPointF(5, win.height()-5), Qt.LeftButton, Qt.NoButton)
                button = find(name)
                QQmlExpression(QQmlEngine.contextForObject(button), button, 'menu.close()').evaluate()
    (out / f'{prefix}-geometry.json').write_text(json.dumps(geometry), encoding='utf-8')
    print(f'{prefix}: {out}; temporary cache: {folder}', flush=True)
    host.close()
    app.processEvents()


if __name__ == '__main__':
    main()
