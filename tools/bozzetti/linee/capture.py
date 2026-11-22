"""Reproduce the line study without changing the application or user profiles."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QSG_RHI_BACKEND', 'd3d11')
os.environ['QT_QUICK_BACKEND'] = 'rhi'
os.environ.setdefault('QSG_RENDER_LOOP', 'basic')
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

from PySide6.QtCore import QObject, QSize, QUrl, Qt
from PySide6.QtGui import QImage, QPainter, QColor, QFont
from PySide6.QtQml import QQmlApplicationEngine

from meridiana.gui.application import QuickWindow, create_app
from meridiana.gui.backend.tokens import install_theme, _qt_colors
from meridiana.app.interface import view_colours
from meridiana.core.model.model import Project


def wait(app, predicate, seconds=30):
    end = time.monotonic() + seconds
    while not predicate():
        if time.monotonic() > end:
            raise TimeoutError('Capture did not become ready')
        app.processEvents()
        time.sleep(.01)


def settle(app, seconds=1):
    end = time.monotonic() + seconds
    wait(app, lambda: time.monotonic() > end, seconds + 2)


def save(image, path):
    if path.exists():
        raise FileExistsError(path)
    if image.isNull() or not image.save(str(path)):
        raise RuntimeError(f'Cannot save {path}')


def grab(app, item, scale):
    dpr = item.window().devicePixelRatio()
    result = item.grabToImage(QSize(round(item.width()*scale/dpr), round(item.height()*scale/dpr)))
    done = []
    result.ready.connect(lambda: done.append(True))
    wait(app, lambda: bool(done))
    return result.image()


def census():
    paths = []
    base = ROOT / 'src/meridiana/gui/qml/Meridiana'
    for folder in ('Plan', 'View3D', 'Measure', 'Checks'):
        paths.extend((base / folder).glob('*'))
    paths.extend((base / 'Controls').glob('*Pill*'))
    paths.extend(base / 'Controls' / name for name in ('SpanLabel.qml', 'CheckMark.qml', 'ControlMetrics.qml'))
    paths.extend((ROOT / 'src/meridiana/gui/backend').glob('plan*'))
    paths.extend((ROOT / 'src/meridiana/gui/backend').glob('scene*'))
    paths.append(ROOT / 'src/meridiana/app/interface/view_colours.py')
    pattern = re.compile(r'strokeWidth|lineWidth|dashPattern|setLineDash|antialias|cosmeticStroke|preferredRenderer|ribbonWidth|font\.(?:weight|bold|pixelSize)|radius:|WIDTHS|measureLine|measureHalo|measureMark|outlinePixel|smooth:')
    rows = ['\n## Appendice: dichiarazioni locali [V]\n', '| File:riga | Dichiarazione |', '|---|---|']
    for path in sorted(set(paths)):
        if not path.is_file() or path.suffix not in ('.py', '.qml', '.js', '.vert', '.frag'):
            continue
        for n, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if pattern.search(line) and not line.lstrip().startswith(('//', '#')):
                shown = line.strip().replace('|', '&#124;').replace('`', '')
                rows.append(f'| `{path.relative_to(ROOT).as_posix()}:{n}` | `{shown}` |')
    target = ROOT / 'docs/studio/52-linee-e-pillole.md'
    with target.open('a', encoding='utf-8') as stream:
        stream.write('\n'.join(rows) + '\n')
    print(f'Census: {len(rows)-3} declarations')


def backgrounds(app, args):
    project_path = args.out / 'Rho.meridiana'
    digest = hashlib.sha256(project_path.read_bytes()).hexdigest()
    project, notice = Project.load(project_path)
    if notice:
        print(f'Project notice: {notice}')
    host = QuickWindow(project, args.out / f'profile-render-{args.theme}-{args.scale}',
                       real_views=True, theme={'theme': args.theme, 'reducedMotion': True})
    host.plan.configureMaps({'offline': True})
    host.window.show()
    host.window.resize(1920, 1080)
    settle(app, 4)
    host.shell.trigger('phase_model')
    host.window.setProperty('viewMode', 'plan')
    settle(app, 2)
    plan = host.window.findChild(QObject, 'plan')
    plan.fit()
    settle(app, 2)
    revision = '-R01' if args.scale > 1 else ''
    save(grab(app, plan, args.scale), args.out / f'background-real-plan-{args.theme}-{args.scale:g}{revision}.png')
    host.window.setProperty('viewMode', '3d')
    settle(app, 5)
    scene = host.window.findChild(QObject, 'viewport3d')
    if scene is None:
        raise RuntimeError('Real 3D viewport missing')
    scene.fitScene()
    settle(app, 3)
    save(grab(app, scene, args.scale), args.out / f'background-real-3d-{args.theme}-{args.scale:g}{revision}.png')
    report = {'platform': app.platformName(), 'api': str(host.window.rendererInterface().graphicsApi()),
              'theme': args.theme, 'scale': args.scale, 'project_sha256': digest,
              'plan': [plan.width(), plan.height()], 'scene': [scene.width(), scene.height()],
              'warnings': host.warnings}
    (args.out / f'background-real-{args.theme}-{args.scale:g}{revision}.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if hashlib.sha256(project_path.read_bytes()).hexdigest() != digest:
        raise RuntimeError('Project changed during capture')
    print(json.dumps(report, indent=2))
    host.close()


def drafts(app, args):
    engine = QQmlApplicationEngine()
    install_theme(engine, {'theme': args.theme, 'reducedMotion': True})
    engine.rootContext().setContextProperty('viewPaint', _qt_colors(view_colours.PHOTO))
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name('Draft.qml'))))
    if not engine.rootObjects():
        raise RuntimeError('\n'.join(warnings))
    window = engine.rootObjects()[0]
    for view in ('plan', '3d'):
        revision = '-R01' if args.scale > 1 else ''
        background = args.out / f'background-real-{view}-{args.theme}-{args.scale:g}{revision}.png'
        window.setProperty('backgroundSource', QUrl.fromLocalFile(str(background)))
        window.setProperty('haloParts', halo_parts(background))
        window.setProperty('viewName', 'Pianta' if view == 'plan' else '3D')
        for variant in 'ABCD':
            window.setProperty('variant', variant)
            settle(app, .6)
            image = grab(app, window.contentItem(), args.scale)
            expected = (round(1920*args.scale), round(1080*args.scale))
            if (image.width(), image.height()) != expected:
                raise RuntimeError(f'Unexpected capture size {image.size()}, expected {expected}')
            save(image, args.out / f'{variant}-{view}-{args.theme}-{args.scale:g}-R02.png')
    if warnings:
        raise RuntimeError('\n'.join(warnings))
    report = dict(platform=app.platformName(), api=str(window.rendererInterface().graphicsApi()),
                  scale=args.scale, theme=args.theme, warnings=warnings, count=8,
                  pixels=[round(1920*args.scale), round(1080*args.scale)])
    (args.out / f'drafts-{args.theme}-{args.scale:g}-R02.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('8 QML captures, no QML warnings')
    window.close()


def halo_parts(path):
    """Mark short intervals whose orange/background contrast is below 3:1.

    Static study only: a future live view must avoid reading back the GPU.
    """
    expanded = QImage(str(path)).scaled(1920, 700, Qt.AspectRatioMode.KeepAspectRatioByExpanding)
    image = expanded.copy((expanded.width()-1920)//2, (expanded.height()-700)//2, 1920, 700)
    def luminance(color):
        channels = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4
                    for v in (color.redF(), color.greenF(), color.blueF())]
        return sum(a*b for a, b in zip(channels, (.2126, .7152, .0722), strict=True))
    ink = luminance(QColor('#ffb000'))
    points = ((260, 190), (760, 402.2374), (1250, 410), (1250, 670))
    out = []
    for a, b in zip(points, points[1:], strict=False):
        count = max(1, round(((b[0]-a[0])**2+(b[1]-a[1])**2)**.5 / 12))
        start = None
        for n in range(count+1):
            t = min(1, (n+.5)/count)
            x, y = (a[j]+(b[j]-a[j])*t for j in (0, 1))
            light = luminance(image.pixelColor(round(x), round(y)))
            low = (max(ink, light)+.05)/(min(ink, light)+.05) < 3
            if low and start is None and n < count:
                start = n/count
            if start is not None and (not low or n == count):
                end = n/count
                out.append([a[0]+(b[0]-a[0])*start, a[1]+(b[1]-a[1])*start,
                            a[0]+(b[0]-a[0])*end, a[1]+(b[1]-a[1])*end])
                start = None
    return out


def boards(args):
    dark = args.theme == 'dark'
    board = QImage(1800, 1480, QImage.Format.Format_RGB32)
    board.fill(QColor('#17191d' if dark else '#f4f3f0'))
    painter = QPainter(board)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.setPen(QColor('#efefec' if dark else '#252525'))
    font = QFont('IBM Plex Sans', 12)
    painter.setFont(font)
    titles = ('A / oggi', 'B / sottile', 'C / fuori linea', 'D / alone locale')
    painter.drawText(16, 30, f'Linee e pillole | {args.theme} | scala {args.scale:g} | catture 1920 x 1080 logici')
    for column, variant in enumerate('ABCD'):
        x = 12 + column*448
        painter.drawText(x, 65, titles[column])
        for row, view in enumerate(('plan', '3d')):
            source = QImage(str(args.out / f'{variant}-{view}-{args.theme}-{args.scale:g}-R02.png'))
            if source.isNull():
                raise FileNotFoundError(f'Missing draft {variant}/{view}')
            y = 85 + row*282
            painter.drawImage(x, y, source.scaled(432, 243))
            painter.drawText(x, y+265, 'Pianta' if view == 'plan' else '3D')
        # Device-pixel crop enlarged for scale 1, native pixels for scale 2.5.
        source = QImage(str(args.out / f'{variant}-3d-{args.theme}-{args.scale:g}-R02.png'))
        for row, (cx, cy, cw, ch, title) in enumerate(((420, 290, 250, 155, 'Misura obliqua / dettaglio'),
                                                       (1340, 820, 450, 160, 'Contatori / dettaglio'))):
            crop = source.copy(round(cx*args.scale), round(cy*args.scale), round(cw*args.scale), round(ch*args.scale))
            y = 675 + row*392
            painter.drawText(x, y-12, title)
            painter.drawImage(x, y, crop.scaled(432, round(432*ch/cw)))
    painter.end()
    save(board, args.out / f'tavola-{args.theme}-{args.scale:g}.png')
    print('Board: 1800 x 1480')


def verify(args):
    records = []
    for theme in ('light', 'dark'):
        for scale in (1, 2.5):
            detail = QImage(1760, 660, QImage.Format.Format_RGB32)
            detail.fill(QColor('#202020' if theme == 'dark' else '#f4f4f4'))
            painter = QPainter(detail)
            painter.setPen(QColor('white' if theme == 'dark' else 'black'))
            for column, variant in enumerate('ABCD'):
                for view in ('plan', '3d'):
                    path = args.out / f'{variant}-{view}-{theme}-{scale:g}-R02.png'
                    image = QImage(str(path))
                    expected = (round(1920*scale), round(1080*scale))
                    if (image.width(), image.height()) != expected:
                        raise RuntimeError(f'Wrong size or missing image: {path}')
                    if image.pixelColor(0, 0).alpha() != 255:
                        raise RuntimeError(f'Transparent ground: {path}')
                    records.append(dict(name=path.name, pixels=expected,
                                        sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
                painter.drawText(column*440+8, 24, variant + ': stroke x4 / dash x2')
                for y, (cx, cy, cw, ch, factor) in ((40, (340, 290, 100, 60, 4)),
                                                  (330, (560, 850, 210, 140, 2))):
                    crop = image.copy(round(cx*scale), round(cy*scale), round(cw*scale), round(ch*scale))
                    painter.drawImage(column*440, y, crop.scaled(cw*factor, ch*factor))
            painter.end()
            save(detail, args.out / f'qa-{theme}-{scale:g}.png')
            path = args.out / f'tavola-{theme}-{scale:g}.png'
            board = QImage(str(path))
            if board.isNull() or board.width() > 1800:
                raise RuntimeError(f'Missing or too wide board: {path}')
            records.append(dict(name=path.name, pixels=[board.width(), board.height()],
                                sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    target = args.out / 'manifest-R02.json'
    if target.exists():
        raise FileExistsError(target)
    target.write_text(json.dumps(records, indent=2), encoding='utf-8')
    print('Verified: 32 opaque drafts at native dimensions, 4 boards <= 1800 px; SHA-256 manifest saved')


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('stage', choices=('census', 'backgrounds', 'drafts', 'boards', 'verify'))
    parser.add_argument('--out', type=Path)
    parser.add_argument('--theme', choices=('light', 'dark'), default='light')
    parser.add_argument('--scale', type=float, default=1)
    args = parser.parse_args()
    if args.stage == 'census':
        census()
        return
    if not args.out or not args.out.is_dir():
        parser.error('--out must be an existing proof directory')
    if args.stage in ('boards', 'verify'):
        app = create_app()
        (boards if args.stage == 'boards' else verify)(args)
        return
    app = create_app()
    if app.platformName() != 'offscreen':
        raise RuntimeError('Only offscreen captures are permitted')
    (backgrounds if args.stage == 'backgrounds' else drafts)(app, args)


if __name__ == '__main__':
    main()
