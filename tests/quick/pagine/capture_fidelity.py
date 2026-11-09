"""Native whole-window File matrix, same Rho project and settings in both engines."""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PySide6.QtCore import QCoreApplication, QEvent, QThreadPool, Qt
from PySide6.QtTest import QTest
import _setup

from meridiana import config, i18n, model
from meridiana.quick.sample import recorded_weather
from quick.pagine.test_fidelity import find_item


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', choices=('widgets', 'quick'), required=True)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=Path('build/quick-foto/r13-file/matrix'))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    case = unittest.TestCase()
    with TemporaryDirectory(dir=args.out) as temporary:
        cache = Path(temporary)
        project = model.Project.load(args.project)[0]
        recorded_weather(project, cache)
        if args.engine == 'quick':
            from meridiana.quick.app import create_app, QuickWindow
            app = create_app()
            host = QuickWindow(project, cache, real_views=True)
            win, cfg = host.window, host.cfg
            win.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
            cfg.network_tiles = cfg.network_geocoding = cfg.network_pvgis = cfg.check_updates = False
            cfg.background = "none"
        else:
            app = _setup.qt_or_skip()
            i18n.setup('it')
            cfg = config.Config(theme='light', accent='indigo', backgrounds='grey', font='plex', background='none',
                                network_tiles=False, network_geocoding=False, network_pvgis=False, check_updates=False)
            win = _setup.window(case, project, cfg, size=(1600, 960))
            win.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        win.show()
        try:
            for mode in ('light', 'dark'):
                cfg.theme = mode
                if args.engine == 'quick':
                    host.parts.controllers['settings']._apply_theme()
                else:
                    win.theme.apply()
                for size in ((1366, 900), (1600, 960), (1920, 1080)):
                    win.resize(*size)
                    sections = ['preferences:appearance']
                    if size == (1600, 960):
                        sections += ['preferences:' + s for s in ('navigation', 'keyboard', 'assistant', 'report', 'maps', 'privacy')]
                        sections += ['open', 'save', 'export', 'catalogues', 'help', 'new', 'registry']
                    for section in sections:
                        if args.engine == 'quick':
                            host.parts.controllers['filePart'].show_file(section)
                            right = find_item(win.contentItem(), 'fileRight')
                            _setup.wait_until(app, lambda right=right: not right.parentItem().property('changing') and right.opacity() == 1)
                            if section == 'preferences:assistant':
                                assert _setup.wait_until(app, lambda: not host.parts.controllers['settings'].services.localBusy, seconds=30)
                        else:
                            if win.file_page.isVisible():
                                win.file_page.show_section(section)
                            else:
                                win.open_file_page(section)
                        QTest.qWait(450)
                        image = win.grabWindow() if args.engine == 'quick' else win.grab().toImage()
                        dpr = image.devicePixelRatio()
                        name = f'{args.engine}-{mode}-{dpr:g}-{size[0]}x{size[1]}-{section.replace(":", "-")}'
                        assert image.width() == round(size[0] * dpr), (name, image.size())
                        assert image.save(str(args.out / (name + '.png')))
                        (args.out / (name + '.json')).write_text(json.dumps(dict(
                            size=size, dpr=dpr, platform=app.platformName(), section=section, theme=mode,
                            warnings=host.warnings if args.engine == 'quick' else []), ensure_ascii=False), encoding='utf8')
                        print(name, flush=True)
            if args.engine == 'quick':
                assert not host.warnings, host.warnings
        finally:
            if args.engine == 'quick':
                host.close()
            else:
                case.doCleanups()
            QThreadPool.globalInstance().waitForDone(10000)
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            app.processEvents()


if __name__ == '__main__':
    main()
