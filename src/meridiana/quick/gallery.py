"""Interactive shared controls gallery, also usable for deterministic captures."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QSize, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from meridiana.i18n import _, setup
from meridiana.quick.backend.controls import install_controls
from meridiana.quick.capture import grab


def texts():
    # Gallery-only Italian fallbacks until the normal catalogue update on Linux.
    def tr(source, italian):
        translated = _(source)
        return italian if translated == source else translated
    return dict(title=tr('Controls gallery', 'Galleria dei controlli'),
                commands=tr('Commands', 'Comandi'), fields=tr('Fields', 'Campi'),
                normal=tr('Normal', 'Normale'), active=tr('Active', 'Attivo'),
                disabled=tr('Disabled', 'Disabilitato'), save=tr('Save', 'Salva'),
                draw=tr('Building', 'Edificio'), measure=tr('Measure', 'Misura'),
                menu=tr('More commands', 'Altri comandi'),
                tip=tr('Save the project and keep the previous copy.', 'Salva il progetto e conserva la copia precedente.'),
                name=tr('Project name', 'Nome del progetto'),
                check=tr('Show shadows', 'Mostra le ombre'), ready=tr('Ready', 'Pronto'),
                cards=tr('Cards and sections', 'Schede e sezioni'),
                section=tr('Properties', 'Proprieta'),
                description=tr('Shared colours, fonts and measures.', 'Colori, caratteri e misure condivisi.'),
                close=tr('Close', 'Chiudi'), unit='kW',
                navigation=tr('Navigation', 'Navigazione'), data=tr('Data', 'Dati'),
                tree=tr('Project tree', 'Albero del progetto'), listing=tr('List', 'Elenco'),
                status=tr('Status', 'Stato'), dialog=tr('Open dialog', 'Apri dialogo'),
                confirm=tr('Confirm', 'Conferma'), cancel=tr('Cancel', 'Annulla'),
                dialogTitle=tr('Project properties', 'Proprieta del progetto'),
                emptyTitle=tr('No results yet', 'Nessun risultato disponibile'),
                emptyDescription=tr('Calculate the project to display the results.', 'Calcola il progetto per visualizzare i risultati.'),
                compute=tr('Calculate', 'Calcola'),
                columns=[dict(title=tr('Building', 'Edificio'), key='name', weight=2),
                         dict(title=tr('Power', 'Potenza'), unit='kW', key='power', numeric=True),
                         dict(title=tr('Energy', 'Energia'), unit='kWh', key='energy', numeric=True)],
                rows=[dict(name=tr('Building', 'Edificio') + f' {i+1:02}', power=f'{12+i},50', energy=f'{17500+i*500:,}'.replace(',', '.')) for i in range(32)],
                total=dict(name=tr('Total', 'Totale'), power='896,00', energy='808.000'),
                segments=[dict(text=tr('Plan', 'Pianta'), id='plan'), dict(text=tr('3D view', 'Vista 3D'), id='3d'), dict(text=tr('Both', 'Entrambe'), id='both')],
                items=[dict(text=tr('Building', 'Edificio'), icon='building'), dict(text=tr('Roof', 'Copertura'), icon='ridge'), dict(text=tr('Modules', 'Moduli'), icon='subfield')],
                nodes=[dict(text=tr('Project', 'Progetto'), id='project', children=[
                    dict(text=tr('Building', 'Edificio'), id='building', children=[
                        dict(text=tr('Roof', 'Copertura'), id='roof'), dict(text=tr('Modules', 'Moduli'), id='modules')]),
                    dict(text=tr('Inverter', 'Inverter'), id='inverter')])])


def build_gallery(options=None, state='normal', width=1366, height=900):
    engine = QQmlApplicationEngine()
    theme = install_controls(engine, options)
    engine.rootContext().setContextProperty('galleryText', texts())
    engine.rootContext().setContextProperty('galleryState', state)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / 'qml/Meridiana/Controls/Gallery.qml')))
    if not engine.rootObjects():
        raise RuntimeError('The control gallery could not be loaded')
    window = engine.rootObjects()[0]
    window.resize(width, height)
    return engine, window, theme


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shot', type=Path)
    parser.add_argument('--theme', choices=('light', 'dark'), default='light')
    parser.add_argument('--state', choices=('normal', 'hover', 'pressed', 'focus', 'tooltip', 'menu', 'dialog', 'empty', 'disabled', 'collapsed'), default='normal')
    parser.add_argument('--matrix', type=Path, help='Capture all themes, scales, states and target sizes')
    parser.add_argument('--large-text', action='store_true')
    parser.add_argument('--width', type=int, default=1366)
    parser.add_argument('--height', type=int, default=900)
    args = parser.parse_args(argv)
    if args.matrix:
        for scale in (1, 2):
            env = dict(os.environ, QT_SCALE_FACTOR=str(scale))
            for theme in ('light', 'dark'):
                cases = [(1366, 900, state) for state in ('normal', 'hover', 'pressed', 'focus', 'tooltip', 'menu', 'dialog', 'empty', 'disabled', 'collapsed')]
                cases += [(1600, 960, 'normal'), (1920, 1080, 'normal')]
                for width, height, state in cases:
                    name = f'{theme}-s{scale}-{width}x{height}-{state}.png'
                    command = [sys.executable, '-m', 'meridiana.quick.gallery', '--theme', theme,
                               '--state', state, '--width', str(width), '--height', str(height),
                               '--shot', str(args.matrix / name)]
                    if scale == 2:
                        command.append('--large-text')
                    subprocess.run(command, env=env, check=True)
        return 0
    app = QGuiApplication.instance() or QGuiApplication(['meridiana-controls'])
    setup('it')
    engine, window, theme = build_gallery(dict(theme=args.theme, textSize='large' if args.large_text else 'medium'),
                                          args.state, args.width, args.height)
    if args.shot:
        # Windows may otherwise reduce an oversized window to the work area's size.
        window.setMinimumSize(QSize(args.width, args.height))
        window.resize(args.width, args.height)
        def prepare():
            from PySide6.QtCore import QMetaObject, Qt
            from PySide6.QtQuick import QQuickItem
            from PySide6.QtTest import QTest
            button = window.findChild(QQuickItem, 'normalButton')
            point = button.mapToScene(button.boundingRect().center()).toPoint()
            if args.state in ('hover', 'tooltip', 'pressed'):
                QTest.mouseMove(window, point)
                if args.state == 'pressed':
                    QTest.mousePress(window, Qt.MouseButton.LeftButton, pos=point)
            elif args.state == 'focus':
                button.forceActiveFocus(Qt.FocusReason.TabFocusReason)
            elif args.state in ('menu', 'dialog'):
                QMetaObject.invokeMethod(window, 'showMenu' if args.state == 'menu' else 'showDialog')
            QTimer.singleShot(900 if args.state == 'tooltip' else 180, capture)

        def capture():
            if (window.width(), window.height()) != (args.width, args.height):
                print('The window manager changed the requested capture size', file=sys.stderr)
                app.exit(1)
                return
            args.shot.parent.mkdir(parents=True, exist_ok=True)
            if not grab(window).save(str(args.shot)):
                raise RuntimeError(f'Could not save {args.shot}')
            print(f'{args.shot}: {window.rendererInterface().graphicsApi()}, DPR={window.effectiveDevicePixelRatio()}')
            app.quit()
        QTimer.singleShot(400, prepare)
    result = app.exec()
    window.close()
    # Keep the engine and providers alive until every QML consumer is gone.
    from shiboken6 import delete
    delete(engine)
    return result


if __name__ == '__main__':
    raise SystemExit(main())
