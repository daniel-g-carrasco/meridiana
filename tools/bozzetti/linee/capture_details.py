"""Native C/D plan details, using a read-only orthophoto cache."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from capture import (QuickWindow, Project, QObject, QUrl, QImage, QColor, QPainter,
                     QFont, QQmlApplicationEngine, create_app, install_theme,
                     _qt_colors, view_colours, grab, save, settle, wait)


def background(app, args):
    project_path = args.out / 'Rho.meridiana'
    digest = hashlib.sha256(project_path.read_bytes()).hexdigest()
    project, _ = Project.load(project_path)
    host = QuickWindow(project, args.out / 'profile-ortho-details', real_views=True,
                       theme={'theme': 'light', 'reducedMotion': True})
    host.plan.configureMaps({'offline': True, 'source': 'pcn', 'veil': 0})
    host.plan.maps.loader.cache_dir = args.cache / 'tiles'
    host.window.resize(1920, 1080)
    host.window.show()
    settle(app, 2)
    host.window.resize(1920, 1080)
    host.shell.trigger('phase_model')
    host.shell.trigger('view_plan')
    settle(app, 1)
    plan = host.window.findChild(QObject, 'plan')
    plan.fit()
    wait(app, lambda: len(host.plan.maps.state.loaded) > 0, 20)
    settle(app, 4)
    full_path = args.out / 'ortofoto-Rho-programma-R04.png'
    if not full_path.exists():
        save(grab(app, plan, 1), full_path)
    layer = next(item for item in plan.findChildren(QObject)
                 if item.metaObject().className().startswith('MapLayer_'))
    layer.setProperty('showOverlays', False)
    layer.setProperty('showSite', False)
    zoom, pan_x, pan_y = (plan.property(name) for name in ('zoom', 'panX', 'panY'))
    metadata = {'source': 'Real program MapLayer, national orthophoto PCN/MASE',
                'cache_read_only': str(args.cache / 'tiles'), 'project_sha256': digest,
                'crops': {}}
    for tone, (x, y) in (('chiaro', (780, 107)), ('scuro', (112, 80))):
        plan.setProperty('fitted', False)
        plan.setProperty('zoom', zoom*6)
        plan.setProperty('panX', plan.width()/2-(x-pan_x)*6)
        plan.setProperty('panY', plan.height()/2-(y-pan_y)*6)
        settle(app, 5)
        shot = grab(app, layer, 1)
        crop = shot.copy((shot.width()-500)//2, (shot.height()-610)//2, 500, 610)
        save(crop, args.out / f'ortofoto-Rho-{tone}-R03.png')
        metadata['crops'][tone] = {'fit_screen_center': [x, y], 'zoom_factor': 6,
                                   'loaded_tiles': len(host.plan.maps.state.loaded)}
    (args.out / 'orthophoto-source-R03.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print('Loaded tiles:', len(host.plan.maps.state.loaded))
    print('Plan size:', plan.width(), plan.height())
    if hashlib.sha256(project_path.read_bytes()).hexdigest() != digest:
        raise RuntimeError('Project changed')
    host.close()


def luminance(c):
    values = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055)**2.4
              for v in (c.redF(), c.greenF(), c.blueF())]
    return sum(a*b for a, b in zip(values, (.2126, .7152, .0722), strict=True))


def local_halo(image, lines):
    result = []
    ink = luminance(QColor(view_colours.PHOTO['draw']))
    for a, b in lines:
        count = max(1, round(((b[0]-a[0])**2 + (b[1]-a[1])**2)**.5 / 6))
        start = None
        for n in range(count+1):
            t = min(1, (n+.5)/count)
            x, y = [a[j]+(b[j]-a[j])*t for j in (0, 1)]
            light = luminance(image.pixelColor(round(x), round(y)))
            low = (max(ink, light)+.05)/(min(ink, light)+.05) < 3
            if low and start is None and n < count:
                start = n
            if start is not None and (not low or n == count):
                result.append([a[0]+(b[0]-a[0])*start/count, a[1]+(b[1]-a[1])*start/count,
                               a[0]+(b[0]-a[0])*n/count, a[1]+(b[1]-a[1])*n/count])
                start = None
    return result


def details(app, args):
    engine = QQmlApplicationEngine()
    install_theme(engine, {'theme': 'light', 'reducedMotion': True})
    engine.rootContext().setContextProperty('viewPaint', _qt_colors(view_colours.PHOTO))
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name('Details.qml'))))
    if not engine.rootObjects():
        raise RuntimeError('\n'.join(warnings))
    window = engine.rootObjects()[0]
    points = ((42, 52), (242, 136.895), (390, 139.2), (390, 213))
    report = {'scale': args.scale, 'warnings': warnings, 'halo_intervals': {}}
    for tone in ('chiaro', 'scuro'):
        path = args.out / f'ortofoto-Rho-{tone}-R03.png'
        image = QImage(str(path))
        if image.isNull() or (image.width(), image.height()) != (500, 610):
            raise RuntimeError(f'Expected a 500 x 610 orthophoto crop: {path}')
        parts = local_halo(image, list(zip(points, points[1:], strict=False)))
        report['halo_intervals'][tone] = len(parts)
        window.setProperty('backgroundSource', QUrl.fromLocalFile(str(path)))
        window.setProperty('haloParts', parts)
        for variant in ('C', 'D'):
            window.setProperty('variant', variant)
            settle(app, .5)
            shot = grab(app, window.contentItem(), args.scale)
            if (shot.width(), shot.height()) != (round(500*args.scale), round(610*args.scale)):
                raise RuntimeError('Incorrect device-pixel capture size')
            save(shot, args.out / f'{variant}-plan-ortofoto-{tone}-{args.scale:g}-R03.png')
    if warnings:
        raise RuntimeError('\n'.join(warnings))
    window.close()
    board(args)
    (args.out / f'details-{args.scale:g}-R03.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


def board(args):
    scale = args.scale
    width, header, gap = round(500*scale), 64, 16
    # All image copies are in device pixels. Never resize a captured detail.
    rows = ((0, 250, 'Misura: tre tratti e totale'),
            (250, 245, 'Edificio: lati numerati e stringa'),
            (495, 60, 'Contatori: 1, 2, 15'),
            (555, 55, 'Tratteggio obliquo e orizzontale'))
    height = header + sum(34 + round(h*scale) for _, h, _ in rows)*2 + 48
    image = QImage(2*width+3*gap, height, QImage.Format.Format_RGB32)
    image.fill(QColor('#f4f3f0'))
    painter = QPainter(image)
    painter.setPen(QColor('#252525'))
    painter.setFont(QFont('IBM Plex Sans', 11))
    painter.drawText(gap, 24, f'C: fuori linea     |     D: alone locale     |     scala {scale:g}, pixel nativi, tema chiaro')
    for column, variant in enumerate(('C', 'D')):
        painter.drawText(gap+column*(width+gap), 51, variant)
    y = header
    for tone in ('chiaro', 'scuro'):
        sources = [QImage(str(args.out / f'{v}-plan-ortofoto-{tone}-{scale:g}-R03.png')) for v in ('C', 'D')]
        for top, h, title in rows:
            row_height = round((top+h)*scale)-round(top*scale)
            painter.drawText(gap, y+24, f'Fondo {tone} / {title}')
            y += 34
            for column, source in enumerate(sources):
                crop = source.copy(0, round(top*scale), width, row_height)
                crop.setDevicePixelRatio(1)
                painter.drawImage(gap+column*(width+gap), y, crop)
            y += row_height
    painter.end()
    if image.width() > 2600:
        raise RuntimeError('Board exceeds 2600 pixels')
    save(image, args.out / f'dettagli-C-D-ortofoto-scala-{scale:g}.png')
    print('Native board:', image.width(), image.height())


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('stage', choices=('background', 'details'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--cache', type=Path)
    parser.add_argument('--scale', type=float, choices=(1, 2.5), default=1)
    args = parser.parse_args()
    app = create_app()
    if app.platformName() != 'offscreen':
        raise RuntimeError('Offscreen only')
    (background if args.stage == 'background' else details)(app, args)


if __name__ == '__main__':
    main()
