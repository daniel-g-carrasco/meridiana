"""Report and modal comparisons on the real Rho workbench, without external services."""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QThreadPool, Qt
from PySide6.QtTest import QTest
import _setup
from meridiana import config, i18n, model, shortcuts
from meridiana.quick.sample import recorded_weather


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', choices=('widgets', 'quick'), required=True)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--compute', action='store_true')
    parser.add_argument('--reference-fixture', action='store_true')
    parser.add_argument('--reports-only', action='store_true')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=args.out) as temporary:
        cache = Path(temporary)
        project = model.Project.load(args.project)[0]
        if args.reference_fixture:
            from quick.parity.differential import connected_fixture
            from _fixtures import clear_sky_meteo, write_cache
            project = connected_fixture()
            project.report['template'] = 'compact'
            write_cache(clear_sky_meteo(), cache)
        else:
            recorded_weather(project, cache)
        case = unittest.TestCase()
        if args.engine == 'quick':
            from meridiana.quick.app import create_app, QuickWindow
            app = create_app()
            host = QuickWindow(project, cache, real_views=True)
            window, cfg = host.window, host.cfg
            part = host.parts.controllers['filePart']
            window.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        else:
            from meridiana.paths import Paths
            app = _setup.qt_or_skip()
            i18n.setup('it')
            cfg = config.Config(theme='light', accent='indigo', backgrounds='grey', font='plex', background='none',
                                network_geocoding=False, network_tiles=False, network_pvgis=False, check_updates=False)
            paths = Paths(config=cache/'config', state=cache/'state', data=cache/'data', cache=cache)
            window = _setup.window(case, project, cfg, size=(1600, 960), paths=paths)
            window.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        cfg.network_geocoding = cfg.network_tiles = cfg.network_pvgis = cfg.check_updates = False
        window.resize(1600, 960)
        window.show()
        try:
            if args.compute:
                if args.reference_fixture:
                    from meridiana import jobs
                    from meridiana.energy import pipeline
                    results, keys, _ = jobs.layout_of(project)
                    energy = pipeline.compute(project, results, cache, fetch=False).as_dict()
                    session = host.bridge.session if args.engine == 'quick' else window.session
                    (args.out / f'{args.engine}-project.json').write_text(json.dumps(session.project.to_json(), ensure_ascii=False, indent=2), encoding='utf8')
                    session.results, session.layout_keys = results, keys
                    if args.engine == 'quick':
                        host.bridge.timer.stop()
                        host.bridge._enabled = False
                        host.bridge._finished(session.generation, energy, [], {})
                    else:
                        window.energy_timer.stop()
                        window._energy_done(session.energy_asked(), energy)
                elif args.engine == 'quick':
                    host.bridge.recompute()
                    assert _setup.wait_until(app, lambda: host.bridge.session.energy.get('sim') is not None, seconds=120), host.bridge._error
                else:
                    window._compute_energy(fetch=False)
                    assert _setup.wait_until(app, lambda: window.session.energy.get('sim') is not None, seconds=120), window.session.energy
            for mode in ('light', 'dark'):
                cfg.theme = mode
                if args.engine == 'quick':
                    part.settings._apply_theme()
                    window.showPhase('report')
                    if part.report.ready:
                        part.report.requestPreview()
                        QTest.qWait(150)
                        assert window.grabWindow().save(str(args.out / f'quick-{mode}-progress.png'))
                        assert _setup.wait_until(app, lambda: not part.report.busy, seconds=90), part.report.error
                else:
                    window.theme.apply()
                    window.show_phase('report')
                    if args.compute:
                        assert _setup.wait_until(app, lambda: bool(window.report_page.preview.images), seconds=60)
                QTest.qWait(1500)
                image = window.grabWindow() if args.engine == 'quick' else window.grab().toImage()
                scale = image.devicePixelRatio()
                assert image.save(str(args.out / f'{args.engine}-{mode}-{scale:g}-report.png'))
                kinds = () if args.reports_only else ('template', 'canopy', 'canopy-layout', 'shortcuts', 'site')
                for kind in kinds:
                    if args.engine == 'quick':
                        part.openDialog(kind)
                        QTest.qWait(250)
                        popup = window.findChild(QObject, 'fileDialogOverlay')
                        image = window.grabWindow()
                        image = image.copy(*(round(popup.property(k) * scale) for k in ('x', 'y', 'width', 'height')))
                    else:
                        from meridiana.ui.template_dialog import TemplateDialog
                        from meridiana.ui.canopy_dialog import CanopyDialog, CanopyLayoutDialog
                        from meridiana.ui.shortcuts_dialog import ShortcutsDialog
                        from meridiana.ui.site_dialog import SiteDialog
                        factories = dict(template=lambda: TemplateDialog(window), canopy=lambda: CanopyDialog(window),
                                         shortcuts=lambda: ShortcutsDialog(shortcuts.bindings(cfg.shortcuts), window),
                                         site=lambda: SiteDialog(project.site, window, network=False))
                        factories['canopy-layout'] = lambda: CanopyLayoutDialog(project, parent=window)
                        dialog = factories[kind]()
                        dialog.show()
                        QTest.qWait(250)
                        image = dialog.grab().toImage()
                    name = f'{args.engine}-{mode}-{scale:g}-{kind}'
                    assert image.save(str(args.out / (name + '.png')))
                    (args.out / (name + '.json')).write_text(json.dumps(dict(
                        size=[image.width()/scale, image.height()/scale], dpr=scale, platform=app.platformName(),
                        warnings=host.warnings if args.engine == 'quick' else [])), encoding='utf8')
                    print(name, flush=True)
                    if args.engine == 'quick':
                        part.dialogs.cancel()
                    else:
                        dialog.reject()
                        dialog.deleteLater()
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
