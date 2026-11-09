"""Capture the capannone fixture in Widgets with isolated config and exact client sizes.

The compatibility baseline uses other fixtures. These images deliberately use the
same project as quick_shell_capture.py; this is an aesthetic reference, not a
claim of functional or pixel parity. No native mouse or keyboard is used.
"""
import argparse
import json
import os
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget

import _setup
from _fixtures import capannone
from meridiana import config, i18n

STATES = ('normal', 'selection', 'menu', 'file', 'help', 'large', 'closed', 'grouped')
SIZES = ((1366, 900), (1600, 960), (1920, 1080))


def capture(app, theme, width, height, states, out):
    from meridiana.ui import design
    from meridiana.ui.theme import load_fonts
    design.set_text_size('medium')
    load_fonts('plex')
    case = unittest.TestCase()
    cfg = config.Config(theme=theme, accent='indigo', backgrounds='grey', font='plex',
                        background='none', network_pvgis=False, check_updates=False,
                        assistant_animated=False)
    win = _setup.window(case, capannone(), cfg, size=(width, height))
    try:
        # Frameless is a capture-only choice: a captioned HWND is constrained by
        # the isolated desktop work area at DPR 2. Keep the real client size.
        win.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        win.show()
        win.resize(width, height)
        _setup.turn_events(app, 500)
        baseline = win.saveState()
        selection = tuple(win.selection)
        for state in states:
            if win.file_page.isVisible():
                win.file_page.close_page()
            win.alt_menus.set_always(False)
            win._text_size('medium')
            win.restoreState(baseline)
            win._select(*selection)
            _setup.turn_events(app, 250)
            if state == 'selection':
                win._select('building', 'b1')
            elif state == 'menu':
                win.alt_menus.set_always(True)
            elif state == 'file':
                win.open_file_page('preferences:appearance')
            elif state == 'help':
                win.help_dock.show()
                win.help_box.show_help('phase.model')
            elif state == 'large':
                win._text_size('large')
            elif state == 'closed':
                win.docks[0].hide()
            elif state == 'grouped':
                left, right = win.docks
                win.tabifyDockWidget(right, left)
                right.raise_()
            _setup.turn_events(app, 500)
            win._fit()
            _setup.turn_events(app, 250)
            image = win.grab().toImage()
            dpr = image.devicePixelRatio()
            expected = (round(width * dpr), round(height * dpr))
            actual = (image.width(), image.height())
            if (win.width(), win.height()) != (width, height) or actual != expected:
                raise RuntimeError(f'Wrong capture size: client {win.size()}, PNG {actual}, expected {expected}')
            if image.isNull():
                raise RuntimeError('Empty Widgets capture')
            name = f'widgets-{theme}-{dpr:g}-{width}x{height}-{state}'
            if not image.save(str(out / (name + '.png'))):
                raise OSError(f'Could not save {name}')
            report = dict(fixture='capannone', theme=theme, state=state, width=win.width(), height=win.height(),
                          pixelWidth=image.width(), pixelHeight=image.height(), dpr=dpr, platform=app.platformName(),
                          font=app.font().family(), textSize=cfg.text_size, selection=list(win.selection),
                          modules=sum(len(result.modules) for result in win.session.good_results().values()),
                          fileSection=win.file_page.current_key if win.file_page.isVisible() else '',
                          panels={w.objectName(): dict(rect=[w.x(), w.y(), w.width(), w.height()],
                                                       visible=w.isVisible(), hidden=w.isHidden())
                                  for w in win.findChildren(QDockWidget)},
                          grouped=win.docks[0] in win.tabifiedDockWidgets(win.docks[1]),
                          menuVisible=win.menuBar().isVisible(), dialogs=case.dialogs)
            (out / (name + '.json')).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
            print(name, actual, flush=True)
    finally:
        case.doCleanups()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--theme', default='light', choices=('light', 'dark'))
    parser.add_argument('--width', type=int, default=1600)
    parser.add_argument('--height', type=int, default=960)
    parser.add_argument('--state', default='normal', choices=(*STATES, 'all'))
    parser.add_argument('--matrix', action='store_true', help='All themes, sizes and states at the process DPR')
    parser.add_argument('--out', type=Path, default=Path('build/quick-foto/riferimento'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    scratch = root / 'build' / 'quick-reference-tmp'
    scratch.mkdir(parents=True, exist_ok=True)
    tempfile.tempdir = str(scratch)
    os.environ['QML_DISABLE_DISK_CACHE'] = '1'
    os.environ['QT_DISABLE_SHADER_DISK_CACHE'] = '1'
    os.environ['TEMP'] = os.environ['TMP'] = str(scratch)
    args.out.mkdir(parents=True, exist_ok=True)
    app = _setup.qt_or_skip()
    i18n.setup('it')
    themes = ('light', 'dark') if args.matrix else (args.theme,)
    sizes = SIZES if args.matrix else ((args.width, args.height),)
    states = STATES if args.matrix or args.state == 'all' else (args.state,)
    for theme in themes:
        for width, height in sizes:
            capture(app, theme, width, height, states, args.out)


if __name__ == '__main__':
    main()
