"""Native import and update dialogs with recorded files and an offline release fixture."""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QThreadPool
from PySide6.QtTest import QTest
import _setup
from meridiana import config, i18n, ifc_read, model, updates
from meridiana.pvsyst import project as pvproject, mapping


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', choices=('widgets', 'quick'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    project = model.Project.load('C:/Users/Grasso/dev/meridiana-prove/Prova capannone Rho.meridiana')[0]
    data = _setup.HERE / 'data'
    ifc_path = data / 'ifc/Building-Architecture.ifc'
    pv_path = data / 'pvsyst/Prova Rho_Project.PRJ'
    prj = pvproject.read_project(pv_path)
    found = ifc_read.read(ifc_path)
    release = updates.Release('99.0.0', 'https://example.org/release', 'Versione di prova offline. Nessun download.')
    case = unittest.TestCase()
    with TemporaryDirectory(dir=args.out) as temporary:
        if args.engine == 'quick':
            from meridiana.quick.app import create_app, QuickWindow
            app = create_app()
            host = QuickWindow(project, Path(temporary), real_views=True)
            win, cfg = host.window, host.cfg
            part = host.parts.controllers['filePart']
        else:
            app = _setup.qt_or_skip()
            i18n.setup('it')
            cfg = config.Config(theme='light', accent='indigo', backgrounds='grey', font='plex', background='none',
                                network_geocoding=False, network_tiles=False, network_pvgis=False, check_updates=False)
            win = _setup.window(case, project, cfg, size=(1600, 960))
        win.resize(1600, 960)
        win.show()
        try:
            for mode in ('light', 'dark'):
                cfg.theme = mode
                if args.engine == 'quick':
                    part.settings._apply_theme()
                else:
                    win.theme.apply()
                for kind in ('ifc', 'pvsyst', 'pvsyst-summary', 'update'):
                    if args.engine == 'quick':
                        part.openDialog('pvsyst' if kind.startswith('pvsyst') else kind)
                        backend = part.dialogs
                        if kind == 'ifc':
                            backend._state['fileName'] = ifc_path.name
                            backend._ifc_done(backend._generation, found)
                        elif kind.startswith('pvsyst'):
                            backend.readFile(str(pv_path))
                            assert _setup.wait_until(app, lambda backend=backend: not backend.busy)
                            if kind == 'pvsyst-summary':
                                backend.readVariants()
                        else:
                            with patch.object(updates, 'latest_release', return_value=release):
                                backend.checkUpdate()
                                assert _setup.wait_until(app, lambda backend=backend: not backend.busy)
                        assert _setup.wait_until(app, lambda backend=backend: not backend.busy, seconds=60)
                        QTest.qWait(250)
                        popup = win.findChild(QObject, 'fileDialogOverlay')
                        image = win.grabWindow()
                        dpr = image.devicePixelRatio()
                        image = image.copy(*(round(popup.property(k)*dpr) for k in ('x', 'y', 'width', 'height')))
                    else:
                        from meridiana.ui.ifc_import import IfcImportDialog
                        from meridiana.ui.pvsyst_import import VariantsChoice, ImportSummary
                        from meridiana.ui.update_dialog import UpdateDialog
                        if kind == 'ifc':
                            dialog = IfcImportDialog(found, project, ifc_path.name, win)
                        elif kind == 'pvsyst':
                            dialog = VariantsChoice(prj, win)
                        elif kind == 'pvsyst-summary':
                            selected = prj.variants if len(prj.variants) <= 4 else prj.variants[:1]
                            _, report = mapping.to_project(prj, [pvproject.read_variant(v.path) for v in selected])
                            dialog = ImportSummary(prj.name, report, win)
                        else:
                            dialog = UpdateDialog(release, win)
                        dialog.show()
                        QTest.qWait(250)
                        image = dialog.grab().toImage()
                        dpr = image.devicePixelRatio()
                    name = f'{args.engine}-{mode}-{dpr:g}-{kind}'
                    assert image.save(str(args.out / (name + '.png')))
                    print(name, flush=True)
                    if args.engine == 'quick':
                        backend.cancel()
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
