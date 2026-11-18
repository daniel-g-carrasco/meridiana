"""Capture actual Widgets and Quick pages side by side on the native platform.

Run separately for QT_SCALE_FACTOR=1 and 2. QTest sends events to our own windows;
the physical pointer and keyboard are never touched.
"""
import argparse
import json
import unittest

import _setup
from PySide6.QtCore import QSize
from PySide6.QtGui import QImage, QPainter
from PySide6.QtTest import QTest

from meridiana import config, i18n
from meridiana.quick.backend.files_page import build_page
from quick.parity.geometry import capture_quick


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--theme', choices=['light', 'dark'], default='light')
    parser.add_argument('--width', type=int, default=1600)
    parser.add_argument('--height', type=int, default=960)
    parser.add_argument('--run', default='R01')
    parser.add_argument('--sections', nargs='*', default=['open', 'save', 'export', 'catalogues', 'help', 'new',
        'registry', 'preferences:appearance', 'preferences:navigation', 'preferences:keyboard',
        'preferences:assistant', 'preferences:report', 'preferences:maps', 'preferences:privacy'])
    args = parser.parse_args()
    app = _setup.qt_or_skip()
    if app.platformName() != 'windows':
        raise RuntimeError('This capture requires the authorized native Windows desktop')
    i18n.setup('it')
    case = unittest.TestCase()
    cfg = config.Config(theme=args.theme, accent='indigo', backgrounds='grey', font='plex',
                        background='none', network_pvgis=False, network_geocoding=False, network_tiles=False,
                        assistant=False, check_updates=False)
    win = _setup.window(case, cfg=cfg, size=(args.width, args.height))
    win.open_file_page('open')
    QTest.qWait(400)
    native = win.file_page
    scale = native.devicePixelRatioF()
    folder = _setup.ROOT / f'build/quick-foto/pagine/{args.theme}-s{scale:g}-{args.width}x{args.height}-{args.run}'
    folder.mkdir(parents=True, exist_ok=True)
    quick = build_page('file', folder=folder / 'profile', options={'theme': args.theme},
                       width=native.width() + 16, height=native.height() + 16)
    try:
        for section in args.sections:
            win.open_file_page(section)
            quick.files.selectSection(section)
            QTest.qWait(350)
            _setup.wait_settled(app, lambda: (native.width(), native.height()))
            quick.window.resize(native.width() + 16, native.height() + 16)
            quick.window.update()
            QTest.qWait(150)
            legacy = native.grab().toImage()
            current = quick.window.grabWindow()
            inset = round(8 * current.devicePixelRatio())
            current = current.copy(inset, inset, legacy.width(), legacy.height())
            current.setDevicePixelRatio(scale)
            stem = section.replace(':', '-')
            legacy.save(str(folder / (stem + '-widgets.png')))
            current.save(str(folder / (stem + '-quick.png')))
            # Store native pixels without resampling. The HTML can display at logical size.
            paired = QImage(QSize(legacy.width() + current.width(), max(legacy.height(), current.height())),
                            QImage.Format.Format_RGB32)
            paired.fill('#888888')
            legacy.setDevicePixelRatio(1)
            current.setDevicePixelRatio(1)
            painter = QPainter(paired)
            painter.drawImage(0, 0, legacy)
            painter.drawImage(legacy.width(), 0, current)
            painter.end()
            paired.save(str(folder / (stem + '-pair.png')))
            geometry = capture_quick(quick.window, scenario=section)
            (folder / (stem + '.json')).write_text(json.dumps(geometry, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f'{section}: {legacy.width()}x{legacy.height()}, D3D={quick.window.rendererInterface().graphicsApi().name}, warnings={len(quick.warnings)}', flush=True)
        (folder / 'warnings.json').write_text(json.dumps(quick.warnings, indent=2), encoding='utf-8')
        if quick.warnings:
            raise AssertionError('\n'.join(quick.warnings))
    finally:
        quick.close()
        case.doCleanups()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
