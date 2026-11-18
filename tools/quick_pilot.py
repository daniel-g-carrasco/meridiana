"""Replay one JSON journey on Widgets and Quick with local Qt events, never OS input.

PYTHONPATH=tests;src python tools/quick_pilot.py tests/quick/percorsi/shell.json
Each engine runs in its own process. Every step saves pixels and project state.
"""
import argparse
import html
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPoint, QPointF, QSize, Qt
from PySide6.QtGui import QImage, QKeySequence, QMouseEvent, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QTabBar, QWidget

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
    if engine == 'widgets':
        for tab in window.findChildren(QTabBar):
            if tab.isVisible():
                for i in range(tab.count()):
                    label = normal(tab.tabText(i))
                    if label == text or label.partition(' ')[2] == text:
                        return tab, QPointF(tab.tabRect(i).center())
        for obj in window.findChildren(QWidget):
            label = getattr(obj, 'text', '')
            label = label() if callable(label) else label
            if obj.isVisible() and (obj.objectName() == text or
                                   normal(label) == text):
                return obj, QPointF(obj.rect().center())
    else:
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
        target = (app.focusWidget() or window) if engine == 'widgets' else window
        QTest.keyClick(target, sequence.key(), sequence.keyboardModifiers())
    elif action == 'resize':
        window.setMinimumSize(QSize(*step['size']))
        window.resize(*step['size'])
    elif action != 'snapshot':
        raise ValueError('Unknown pilot action: ' + action)
    return last


def run(args, journey):
    from _fixtures import capannone
    from meridiana import config, i18n, jobs, model
    from meridiana.quick.sample import recorded_weather
    project = model.Project.load(args.project)[0] if args.project else capannone()
    case = unittest.TestCase()
    with tempfile.TemporaryDirectory(dir=args.out) as temporary:
        cache = Path(temporary)
        recorded_weather(project, cache)
        if args.engine == 'quick':
            from meridiana.quick.app import QuickWindow, create_app
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
            host.bridge._request_checks()
            cleanup = host.close
        else:
            import _setup
            from meridiana.ui.theme import load_fonts
            app = _setup.qt_or_skip()
            i18n.setup('it')
            load_fonts('plex')
            cfg = config.Config(theme=args.theme, font='plex', accent='indigo', backgrounds='grey', background='none',
                                text_size='large' if args.large_text else 'medium',
                                toolbar=args.toolbar, toolbar_place=args.toolbar_place,
                                network_pvgis=False, check_updates=False, assistant_animated=False)
            window = _setup.window(case, project, cfg, size=journey.get('size', [1600, 960]))
            recorded_weather(project, case.paths.cache)
            # Seed the same layout and live electrical state as Quick. No
            # annual job is requested by these shell-only gestures.
            window.energy_timer.stop()
            window._abandon_year()
            window.plant_timer.stop()
            window._start_plant(now=True)
            window._show_checks()
            session, cleanup = window.session, case.doCleanups
        try:
            if args.engine == 'quick':
                window.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
            else:
                window.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
            window.show()
            if args.engine == 'quick':
                window.requestActivate()
            else:
                window.activateWindow()
                window.raise_()
            window.setMinimumSize(QSize(*journey.get('size', [1600, 960])))
            window.resize(*journey.get('size', [1600, 960]))
            pump(500)
            if args.engine == 'quick':
                assistant = window.findChild(QObject, 'assistantLayer')
                if assistant is not None:
                    wait_for(lambda: not assistant.property('relocating'), seconds=10)
            last = window.mapToGlobal(QPoint(5, 5))
            for index, step in enumerate(journey['steps']):
                last = perform(app, window, args.engine, step, last)
                pump(step.get('wait', 400))
                image = window.grabWindow() if args.engine == 'quick' else window.grab().toImage()
                if image.isNull():
                    raise AssertionError('Empty capture')
                base = args.out / f'{index:02}-{args.engine}'
                image.save(str(base.with_suffix('.png')))
                phase = window.property('phase') if args.engine == 'quick' else window.phase()
                opened = window.property('fileOpen') if args.engine == 'quick' else window.file_page.isVisible()
                state = dict(step=step, phase=phase, fileOpen=opened, project=session.project.to_json(),
                             size=[window.width(), window.height()], dpr=image.devicePixelRatio(),
                             platform=app.platformName(), menuOpen=bool(window.property('menuOpen')) if args.engine=='quick' else window.menuBar().isVisible())
                if args.engine == 'quick':
                    state.update(warnings=host.warnings, graphics=str(window.rendererInterface().graphicsApi()),
                                 theme=host.theme.options)
                    state['tools'] = {obj.objectName().removeprefix('tool_'): [obj.width(), obj.height()]
                                      for obj in quick_items(window)
                                      if obj.objectName().startswith('tool_') and hasattr(obj, 'isVisible') and obj.isVisible()
                                      and not obj.objectName().endswith('Arrow')}
                else:
                    state['status'] = dict(height=window.statusBar().height())
                    state['side'] = dict(rect=list(window.side_bar.geometry().getRect()),
                                         buttons=[list(obj.geometry().getRect()) for obj in window.side_bar.findChildren(QWidget)
                                                  if obj.isVisible() and hasattr(obj, 'defaultAction')])
                    state['header'] = dict(height=window.tabs.header.height(), tabs=window.tabs.tab_bar.height(),
                                           card=list(window.tabs.header.card.geometry().getRect()),
                                           tabrect=list(window.tabs.tab_bar.geometry().getRect()),
                                           file=list(window.tabs.header.file_button.geometry().getRect()),
                                           tools={key: {'rect': list(button.geometry().getRect()),
                                                        'font': button.font().toString()}
                                                  for key, button in window.bars[phase].buttons().items()})
                base.with_suffix('.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
                if args.engine == 'quick' and host.warnings:
                    raise AssertionError('\n'.join(host.warnings))
                for key, expected in step.get('expect', {}).items():
                    if state[key] != expected:
                        raise AssertionError(f'{args.engine} step {index}: {key}={state[key]!r}, expected {expected!r}')
                print(f'{args.engine}: {index:02} {step}', flush=True)
        finally:
            if args.engine == 'widgets':
                # The reference's closeEvent does not abandon the automatic
                # year. Cancel it through the existing computation action;
                # otherwise Python waits for the global pool after the photos.
                window.energy_timer.stop()
                window._abandon_year()
            cleanup()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            app.processEvents()


def compare(out, journey):
    entries = []
    for index, step in enumerate(journey['steps']):
        a, b = (QImage(str(out / f'{index:02}-{name}.png')) for name in ('widgets', 'quick'))
        if a.isNull() or b.isNull():
            continue
        combined = QImage(a.width()+b.width(), max(a.height(), b.height()), QImage.Format.Format_RGB32)
        combined.fill(Qt.GlobalColor.white)
        painter = QPainter(combined)
        # Draw physical pixels, independent of DPR metadata.
        a.setDevicePixelRatio(1); b.setDevicePixelRatio(1)
        painter.drawImage(0, 0, a); painter.drawImage(a.width(), 0, b); painter.end()
        name = f'{index:02}-pair.png'
        combined.save(str(out / name))
        entries.append(f'<h2>{index:02} {html.escape(str(step))}</h2><img src="{name}" width="100%">')
    (out / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Widgets / Quick</title>'
                                   '<h1>Widgets a sinistra, Quick a destra</h1>'+''.join(entries), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journey', type=Path)
    parser.add_argument('--engine', choices=('both', 'widgets', 'quick'), default='both')
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
    if args.engine != 'both':
        run(args, journey)
        return
    for engine in ('widgets', 'quick'):
        cmd = [sys.executable, __file__, str(args.journey), '--engine', engine, '--theme', args.theme,
               '--out', str(args.out), '--toolbar', args.toolbar, '--toolbar-place', args.toolbar_place]
        if args.project:
            cmd.extend(['--project', str(args.project)])
        if args.large_text:
            cmd.append('--large-text')
        subprocess.run(cmd, check=True)
    compare(args.out, journey)


if __name__ == '__main__':
    main()
