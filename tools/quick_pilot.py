"""Replay one JSON journey on the Quick window with local Qt events, never OS input.

PYTHONPATH=tests;src python tools/quick_pilot.py tests/quick/percorsi/shell.json
Every step saves pixels and project state. (Once on the Widgets window too, side by side: only the Quick is left.)
"""
import argparse
import json
import os
from pathlib import Path
import tempfile

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPoint, QPointF, QSize, Qt
from PySide6.QtGui import QKeySequence, QMouseEvent
from PySide6.QtTest import QTest

from quick.gestures import pump, wait_for


def normal(text):
    return str(text or '').replace('&', '').strip()


def quick_items(window):
    pending = [window.contentItem()]
    while pending:
        obj = pending.pop(0)
        pending.extend(obj.childItems())
        yield obj


def find_target(window, text, engine):
    """Find rendered controls by their label, including custom phase tabs."""
    for obj in quick_items(window):
        if obj.isVisible() and obj.width() > 0 and obj.height() > 0:
            if obj.objectName() == text or normal(obj.property('text')) == text:
                return window, obj.mapToScene(QPointF(obj.width()/2, obj.height()/2))
    raise AssertionError(f'{engine}: no visible control with label {text!r}')


def send_mouse(app, target, pos, kind, button=Qt.MouseButton.NoButton, buttons=Qt.MouseButton.NoButton):
    global_pos = QPointF(target.mapToGlobal(pos.toPoint()))
    app.sendEvent(target, QMouseEvent(kind, pos, pos, global_pos, button, buttons, Qt.KeyboardModifier.NoModifier))


def perform(app, window, engine, step, last):
    action = step['action']
    if action in ('hover', 'click', 'right_click', 'double_click'):
        target, pos = find_target(window, step['target'], engine)
        start = QPointF(target.mapFromGlobal(last))
        for i in range(1, 13):
            send_mouse(app, target, start+(pos-start)*(i/12), QEvent.Type.MouseMove)
            pump(12)
        if action != 'hover':
            button = Qt.MouseButton.RightButton if action == 'right_click' else Qt.MouseButton.LeftButton
            send_mouse(app, target, pos, QEvent.Type.MouseButtonPress, button, button)
            send_mouse(app, target, pos, QEvent.Type.MouseButtonRelease, button)
            if action == 'double_click':
                send_mouse(app, target, pos, QEvent.Type.MouseButtonDblClick, button, button)
                send_mouse(app, target, pos, QEvent.Type.MouseButtonRelease, button)
        return target.mapToGlobal(pos.toPoint())
    if action == 'key':
        sequence = QKeySequence(step['key'])[0]
        target = window
        QTest.keyClick(target, sequence.key(), sequence.keyboardModifiers())
    elif action == 'resize':
        window.setMinimumSize(QSize(*step['size']))
        window.resize(*step['size'])
    elif action != 'snapshot':
        raise ValueError('Unknown pilot action: ' + action)
    return last


def run(args, journey):
    from _fixtures import capannone
    from meridiana.app import jobs
    from meridiana.core.model import model
    from meridiana.gui.sample import recorded_weather
    project = model.Project.load(args.project)[0] if args.project else capannone()
    with tempfile.TemporaryDirectory(dir=args.out) as temporary:
        cache = Path(temporary)
        recorded_weather(project, cache)
        from meridiana.gui.application import QuickWindow, create_app
        app = create_app()
        host = QuickWindow(project, cache, real_views=True,
                           theme={'theme': args.theme, 'accent': 'indigo', 'backgrounds': 'grey', 'font': 'plex',
                                  'textSize': 'large' if args.large_text else 'medium'})
        host.plan.configureMaps({'source': 'none'})
        for name, value in [('toolbar', args.toolbar), ('toolbar_place', args.toolbar_place)]:
            if not host.parts.controllers['settings'].setValue(name, value):
                raise AssertionError(f'Quick rejected the initial setting {name}={value}')
        window, session = host.window, host.bridge.session
        results, keys, _ = jobs.layout_of(project)
        host.bridge.accept_layout(session.generation, results, keys)
        host.bridge.request_checks()
        cleanup = host.close
        try:
            window.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
            window.show()
            window.requestActivate()
            window.setMinimumSize(QSize(*journey.get('size', [1600, 960])))
            window.resize(*journey.get('size', [1600, 960]))
            pump(500)
            assistant = window.findChild(QObject, 'assistantLayer')
            if assistant is not None:
                wait_for(lambda: not assistant.property('relocating'), seconds=10)
            last = window.mapToGlobal(QPoint(5, 5))
            for index, step in enumerate(journey['steps']):
                last = perform(app, window, args.engine, step, last)
                pump(step.get('wait', 400))
                image = window.grabWindow()
                if image.isNull():
                    raise AssertionError('Empty capture')
                base = args.out / f'{index:02}-{args.engine}'
                image.save(str(base.with_suffix('.png')))
                phase = window.property('phase')
                opened = window.property('fileOpen')
                state = dict(step=step, phase=phase, fileOpen=opened, project=session.project.to_json(),
                             size=[window.width(), window.height()], dpr=image.devicePixelRatio(),
                             platform=app.platformName(), menuOpen=bool(window.property('menuOpen')))
                state.update(warnings=host.warnings, graphics=str(window.rendererInterface().graphicsApi()),
                             theme=host.theme.options)
                state['tools'] = {obj.objectName().removeprefix('tool_'): [obj.width(), obj.height()]
                                  for obj in quick_items(window)
                                  if obj.objectName().startswith('tool_') and hasattr(obj, 'isVisible') and obj.isVisible()
                                  and not obj.objectName().endswith('Arrow')}
                base.with_suffix('.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
                if host.warnings:
                    raise AssertionError('\n'.join(host.warnings))
                for key, expected in step.get('expect', {}).items():
                    if state[key] != expected:
                        raise AssertionError(f'{args.engine} step {index}: {key}={state[key]!r}, expected {expected!r}')
                print(f'{args.engine}: {index:02} {step}', flush=True)
        finally:
            cleanup()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            app.processEvents()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journey', type=Path)
    parser.add_argument('--engine', choices=('quick',), default='quick')   # the only window left
    parser.add_argument('--project', type=Path)
    parser.add_argument('--theme', choices=('light', 'dark'), default='light')
    parser.add_argument('--large-text', action='store_true')
    parser.add_argument('--toolbar', choices=('text', 'icons'), default='text')
    parser.add_argument('--toolbar-place', choices=('top', 'left'), default='top')
    parser.add_argument('--out', type=Path, default=Path('build/quick-foto/pilot'))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    journey = json.loads(args.journey.read_text(encoding='utf-8'))
    os.environ['QML_DISABLE_DISK_CACHE'] = '1'
    os.environ['QT_DISABLE_SHADER_DISK_CACHE'] = '1'
    run(args, journey)

if __name__ == '__main__':
    main()
