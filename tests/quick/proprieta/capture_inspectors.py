"""Capture the inspectors in both real applications, without touching user state."""
import argparse
import json
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QPointF, Qt
from quick.gestures import pump, wait_for


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', choices=('quick', 'widgets'), required=True)
    parser.add_argument('--theme', default='light')
    parser.add_argument('--width', type=int, default=1600)
    parser.add_argument('--height', type=int, default=960)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--project', type=Path)
    parser.add_argument('--large', action='store_true')
    parser.add_argument('--extended', action='store_true')
    parser.add_argument('--matrix', action='store_true')
    parser.add_argument('--empty', action='store_true')
    parser.add_argument('--cards', action='store_true', help='Explicit visual fixture for joined rows and scroll fades')
    args = parser.parse_args()
    from _fixtures import capannone_rho
    from meridiana import config, i18n, jobs, model
    from meridiana.quick.sample import recorded_weather
    args.out.mkdir(parents=True, exist_ok=True)
    project = model.Project.load(args.project)[0] if args.project else capannone_rho()
    if args.extended and not project.props:
        project.props.append(model.Prop(id='capture-tree', kind='hedge'))
    case = unittest.TestCase()
    with tempfile.TemporaryDirectory(dir=args.out, delete=False) as temporary:
        cache = Path(temporary)
        recorded_weather(project, cache)
        if args.engine == 'quick':
            from meridiana.quick.app import create_app, QuickWindow
            app = create_app()
            host = QuickWindow(project, cache, real_views=True, theme=dict(theme=args.theme, textSize='large' if args.large else 'medium'))
            host.theme.configure(dict(theme=args.theme, accent='indigo', backgrounds='grey', font='plex',
                                      textSize='large' if args.large else 'medium'))
            win = host.window
            session = host.bridge.session
            results, keys, _ = jobs.layout_of(project)
            assert host.bridge.accept_layout(session.generation, results, keys)
            wait_for(lambda: not host.parts.controllers['checks'].busy)
            select = lambda kind, oid: session.select(kind, oid)
            win.setFlags(Qt.Window | Qt.FramelessWindowHint)
            cleanup = host.close
        else:
            import _setup
            from meridiana.ui.theme import load_fonts
            app = _setup.qt_or_skip()
            i18n.setup('it')
            load_fonts('plex')
            cfg = config.Config(theme=args.theme, font='plex', accent='indigo', backgrounds='grey',
                                text_size='large' if args.large else 'medium', network_pvgis=False,
                                check_updates=False, assistant_animated=False, background='none')
            win = _setup.window(case, project, cfg, size=(args.width, args.height))
            session = win.session
            select = win._select
            win.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
            cleanup = case.doCleanups
        try:
            win.show()
            configurations = [(args.width, args.height, args.theme, args.large)]
            if args.matrix:
                configurations = [(w, h, tone, False) for tone in ('light', 'dark')
                                  for w, h in ((1366, 900), (1600, 960), (1920, 1080))]
                configurations.append((1366, 900, 'light', True))
            for width, height, tone, large in configurations:
                if args.engine == 'quick':
                    host.theme.configure(dict(theme=tone, accent='indigo', backgrounds='grey', font='plex',
                                              textSize='large' if large else 'medium'))
                else:
                    cfg.theme, cfg.text_size = tone, 'large' if large else 'medium'
                    win.theme.applied = None
                    win.theme.apply()
                win.resize(width, height)
                pump(800)
                choices = [('site', '')]
                choices += [] if args.empty or args.cards else [(kind, objects[0].id) for kind, objects in [('building', project.buildings),
                             ('subfield', project.subfields), ('exclusion', project.exclusions), ('prop', project.props)] if objects]
                for kind, oid in choices:
                    select(kind, oid)
                    if args.empty:
                        (host.parts.controllers['checks'] if args.engine == 'quick' else win.checks_page).show_items([])
                    if args.cards:
                        from meridiana.checks import Item
                        target = ('building', project.buildings[0].id)
                        items = [Item('fail', 'layout', 'Prima verifica: dettaglio aperto', 'Dati del progetto', target,
                                      detail='Esempio visivo per confrontare il contorno continuo delle righe e la sfumatura allo scorrimento.'),
                                 Item('fail', 'layout', 'Seconda verifica nella stessa scheda', 'Dati del progetto', target)]
                        items += [Item('info', 'layout', f'Nota di confronto {n+1}', target=target) for n in range(18)]
                        check_page = host.parts.controllers['checks'] if args.engine == 'quick' else win.checks_page
                        check_page.show_items(items)
                        if args.engine == 'quick':
                            check_page.toggleDetail(0)
                        else:
                            check_page.rows[0].setExpanded(True)
                    # Pump several real frames: a grab alone can sample a half-finished
                    # animation on the isolated desktop.
                    for _ in range(15):
                        pump(40)
                        if args.engine == 'quick':
                            win.grabWindow()
                    image = win.grabWindow() if args.engine == 'quick' else win.grab().toImage()
                    dpr = win.devicePixelRatio()
                    label = tone + ('-large' if large else '') + ('-empty' if args.empty else '') + ('-cards' if args.cards else '')
                    stem = f'{args.engine}-{label}-{width}x{height}-x{dpr:g}-{kind}'
                    image.save(str(args.out / (stem + '.png')))
                    if args.engine == 'quick':
                        panels = {name: win.findChild(QObject, object_name) for name, object_name in
                                  [('properties', 'rightPanel'), ('checks', 'checksPanel'), ('project', 'leftPanel')]}
                        rectangles = {name: [panel.mapToScene(QPointF()).x(), panel.mapToScene(QPointF()).y(), panel.width(), panel.height()]
                                      for name, panel in panels.items()}
                        warnings = host.warnings
                    else:
                        panels = dict(properties=win.docks[1], project=win.docks[0], checks=win.checks_dock)
                        rectangles = {name: [panel.mapTo(win, QPoint()).x(), panel.mapTo(win, QPoint()).y(), panel.width(), panel.height()]
                                      for name, panel in panels.items()}
                        warnings = []
                    for name, rect in rectangles.items():
                        crop = image.copy(*[round(v*dpr) for v in rect])
                        crop.save(str(args.out / (stem + '-' + name + '.png')))
                    (args.out / (stem + '.json')).write_text(json.dumps(dict(platform=app.platformName(),
                        graphics=str(win.rendererInterface().graphicsApi()) if args.engine == 'quick' else 'Widgets',
                        panels=rectangles, warnings=warnings, selection=[kind, oid],
                        theme=host.theme.options if args.engine == 'quick' else dict(theme=cfg.theme, backgrounds=cfg.backgrounds,
                            accent=cfg.accent, font=cfg.font, textSize=cfg.text_size)), indent=2), encoding='utf-8')
                    print(stem, warnings, flush=True)
        finally:
            cleanup()


if __name__ == '__main__':
    main()
