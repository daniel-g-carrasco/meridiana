"""Capture the real Quick shell using an isolated fixture project and no native input."""
import argparse
import json
import tempfile
from pathlib import Path
from PySide6.QtCore import QCoreApplication, QEvent, QObject, Qt

from _fixtures import capannone
from meridiana import jobs
from meridiana.quick.app import QuickWindow, create_app
from meridiana.quick.capture import grab
from quick.gestures import pump, wait_for


def capture(args, app):
    with tempfile.TemporaryDirectory() as temporary:
        host = QuickWindow(capannone(), Path(temporary), theme={'theme': args.theme})
        results, keys, _ = jobs.layout_of(host.bridge.session.project)
        host.bridge.accept_layout(0, results, keys)
        host.bridge._request_checks()
        wait_for(lambda: not host.bridge._check_jobs)
        # A captioned HWND is limited to this isolated desktop's work area.
        # Capture the same client area without its native caption, at the exact
        # requested logical size even when it exceeds the desktop at DPR 2.
        host.window.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        host.window.show()
        pump(80)
        host.window.resize(args.width, args.height)
        pump(80)
        host.window.findChild(QObject, 'plan').fit()
        if args.state == 'selection':
            host.bridge.select('building', 'b1', '')
        elif args.state == 'file':
            host.window.setProperty('fileOpen', True)
        elif args.state == 'menu':
            host.window.setProperty('menuOpen', True)
        elif args.state == 'help':
            host.window.setProperty('helpOpen', True)
        elif args.state == 'large':
            host.theme.configure({'textSize': 'large'})
        elif args.state == 'closed':
            host.window.runCommand('panel_project')
        elif args.state == 'grouped':
            project = host.window.findChild(QObject, 'leftPanel')
            project.setProperty('zone', 'right')
            workspace = host.window.findChild(QObject, 'workspace')
            workspace.selectPanel('properties')
        pump(450)
        image = grab(host.window)
        args.out.mkdir(parents=True, exist_ok=True)
        name = f'quick-{args.theme}-{image.devicePixelRatio():g}-{args.width}x{args.height}-{args.state}'
        image.save(str(args.out / (name + '.png')))
        report = dict(width=host.window.width(), height=host.window.height(), dpr=image.devicePixelRatio(),
                      fixture='capannone', modules=host.bridge.moduleCount, state=args.state, theme=args.theme,
                      pixelWidth=image.width(), pixelHeight=image.height(),
                      platform=app.platformName(), backend=str(host.window.rendererInterface().graphicsApi()),
                      warnings=host.warnings)
        (args.out / (name+'.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2))
        host.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
        if report['warnings']:
            raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--theme', default='light')
    parser.add_argument('--width', type=int, default=1600)
    parser.add_argument('--height', type=int, default=960)
    parser.add_argument('--state', default='normal')
    parser.add_argument('--out', type=Path, default=Path('build/quick-foto/sistema'))
    parser.add_argument('--matrix', action='store_true')
    parser.add_argument('--states', default='normal,selection,menu,file,help,large,closed,grouped')
    args = parser.parse_args()
    app = create_app()
    if args.matrix:
        for width, height in ((1366,900),(1600,960),(1920,1080)):
            for state in args.states.split(','):
                args.width, args.height, args.state = width, height, state
                capture(args, app)
    else:
        capture(args, app)


if __name__ == '__main__':
    main()
