"""Reproduce the fidelity matrix, keeping real full windows and 200% bubble crops."""
import argparse
import html
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--scale', type=int, choices=(1, 2))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    cases = [(width, height, theme, scale, 'conversation', [])
             for (width, height), theme, scale in itertools.product(
                 [(1366, 900), (1600, 960), (1920, 1080)], ['light', 'dark'], [1, 2])]
    cases += [(1366, 900, 'dark', 2, 'conversation', ['--large', '--docked']),
              (1600, 960, 'light', 1, 'setup', []), (1366, 900, 'dark', 2, 'rich', []),
              (1366, 900, 'light', 1, 'help', []), (1600, 960, 'dark', 2, 'tour', []),
              (1366, 900, 'dark', 2, 'table', []), (1366, 900, 'dark', 2, 'provider', [])]
    for width, height, theme, scale, page, extra in cases:
        if args.scale and scale != args.scale:
            continue
        name = f'{page}-{theme}-{width}x{height}-dpr{scale}' + ('-large' if '--large' in extra else '') + '-full' + ('-docked' if '--docked' in extra else '')
        if args.resume and (args.out/(name+'.json')).exists():
            continue
        cmd = [sys.executable, '-u', '-m', 'quick.meridio.capture', '--full', '--width', str(width), '--height', str(height),
               '--theme', theme, '--page', page, '--out', str(args.out), *extra]
        env = {**os.environ, 'QT_SCALE_FACTOR': str(scale), 'QSG_RENDER_LOOP': 'basic', 'QT_QUICK_CONTROLS_STYLE': 'Basic'}
        subprocess.run(cmd, env=env, check=True, timeout=180)
    if not args.scale:
        gallery(args.out)


def gallery(folder):
    from PySide6.QtCore import QRect, Qt
    from PySide6.QtGui import QGuiApplication, QImage, QPainter, QColor
    app = QGuiApplication.instance() or QGuiApplication(['meridio-gallery'])
    entries = []
    for source in sorted(folder.glob('*.json')):
        data = json.loads(source.read_text(encoding='utf-8'))
        name = source.stem
        title = html.escape(name)
        pictures = [QImage(str(folder/(name+'-'+kind+'.png'))).scaledToWidth(900, Qt.SmoothTransformation) for kind in ('quick', 'widgets')]
        for picture in pictures:
            picture.setDevicePixelRatio(1)
        pair = QImage(1800, max(pic.height() for pic in pictures)+32, QImage.Format_RGB32)
        pair.fill(QColor('#dedede'))
        pen = QPainter(pair)
        pen.setPen(QColor('#111111'))
        for x, label, picture in zip((0, 900), ('Quick', 'Widgets'), pictures, strict=True):
            pen.drawText(QRect(x+12, 0, 880, 30), Qt.AlignVCenter, label+': '+name)
            pen.drawImage(x, 32, picture)
        pen.end()
        pair.save(str(folder/(name+'-comparison.png')))
        app.processEvents()
        entries.append(f'<article><h2>{title}</h2><a href="{name}-comparison.png"><img class="pair" src="{name}-comparison.png"></a>'
                       f'<p>{html.escape(data["api"])}. Richieste al fornitore finto: {data["fakeRequests"]}. '
                       f'<a href="{source.name}">Misure e avvertenze</a>.</p>'
                       f'<details><summary>Fumetti al 100% e ritagli al 200%</summary>'
                       f'<div class="crops"><div>Widgets<img src="{name}-widgets-bubble.png"></div>'
                       f'<div>Quick<img src="{name}-quick-bubble.png"></div></div>'
                       f'<div class="crops"><img src="{name}-widgets-200.png"><img src="{name}-quick-200.png"></div>'
                       '</details></article>')
    (folder/'index.html').write_text('<!doctype html><html lang="it"><meta charset="utf-8"><title>Meridio: confronto</title>'
        '<style>body{font:16px system-ui;max-width:1600px;margin:32px auto;padding:0 20px;background:#eee;color:#222}'
        'article{background:white;padding:20px;margin:24px 0;border-radius:8px}h2{font-size:18px}.pair{width:100%}'
        '.crops{display:flex;gap:20px;align-items:flex-start;overflow:auto;margin:16px 0}.crops img{display:block;max-width:none}</style>'
        '<h1>Meridio: Widgets e Qt Quick</h1><p>Finestre vere, Direct3D11, progetto Rho sintetico, risposte finte identiche. '
        'La coppia mostra Quick a sinistra e Widgets a destra. I ritagli riportano entrambi i nomi. '
        'Nessuna richiesta a pagamento. L’aiuto segue R383: nel nuovo sostituisce la conversazione durante la visita.</p>'
        + ''.join(entries) + '</html>', encoding='utf-8')


if __name__ == '__main__':
    main()
