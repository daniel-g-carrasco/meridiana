"""Publish 200 percent shell crops from the common pilot, preserving both originals."""
import argparse
import html
import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter


def build(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    entries = []
    for folder in sorted(source.glob('matrix-*')):
        sections = []
        for step in (0, 1, 3, 4, 5, 6, 7, 9, 11, 12, 13):
            images, states = [], []
            for engine in ('widgets', 'quick'):
                filename = folder / f'{step:02}-{engine}'
                if not filename.with_suffix('.json').exists():
                    break
                states.append(json.loads(filename.with_suffix('.json').read_text(encoding='utf-8')))
                images.append(QImage(str(filename.with_suffix('.png'))))
            if len(images) != 2:
                continue
            for key in ('phase','fileOpen','size','dpr','menuOpen'):
                if key in states[0] and key in states[1] and states[0][key] != states[1][key]:
                    raise ValueError(f'Different {key}: {folder.name}, step {step}: {states[0][key]} != {states[1][key]}')
            if any(i.isNull() for i in images):
                raise ValueError(f'Empty capture: {folder}, {step}')
            width, height = states[0]['size']
            zones = {'fasi': (0, 0, min(width, 950), 38), 'strumenti': (0, 34, min(width, 1050), 84)}
            if step in (0, 9, 12):
                zones.update(scheda=(0, 115, 330, 100), stato=(0, height-40, width, 40))
            for name, (x, y, w, h) in zones.items():
                crops = []
                for picture, state in zip(images, states, strict=True):
                    dpr = state['dpr']
                    crop = picture.copy(round(x*dpr), round(y*dpr), round(w*dpr), round(h*dpr))
                    crop.setDevicePixelRatio(1)
                    crops.append(crop.scaled(w*2, h*2, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation))
                pair = QImage(w*2, h*4, QImage.Format.Format_RGB32)
                painter = QPainter(pair)
                painter.drawImage(0, 0, crops[0]); painter.drawImage(0, h*2, crops[1]); painter.end()
                filename = f'{folder.name}-{step:02}-{name}.png'
                pair.save(str(destination / filename))
                sections.append(f'<h3>{step:02}: {name}, {width} × {height}</h3><div class="crop"><img src="{filename}"></div>')
        entries.append(f'<section><h2>{html.escape(folder.name)}</h2>'+''.join(sections)+'</section>')
    page = '''<!doctype html><html lang="it"><meta charset="utf-8"><title>r13-shell: confronto al 200%</title>
<style>body{font:15px system-ui;margin:24px;background:#eee;color:#222}section{margin:24px 0}h3{margin:20px 0 8px}.crop{overflow:auto;border:1px solid #999;background:white}img{display:block;max-width:none}p{max-width:900px}</style>
<h1>Widgets sopra, Quick sotto: ritagli al 200 %</h1>
<p>Stesso copione, progetto di prova di Rho, tema, scala e dimensioni. I PNG del pilot e lo stato JSON restano in build/quick-foto/r13-shell.
Le immagini non attestano la parità dei risultati numerici: il percorso non attende il calcolo annuale.
Le differenze ancora presenti e quelle richieste da Daniel sono descritte in r13-shell-fedelta.md.</p>'''+''.join(entries)+'</html>'
    (destination / 'index.html').write_text(page, encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('build/quick-foto/r13-shell'))
    parser.add_argument('--out', type=Path, default=Path('docs/quick/confronto/r13-shell'))
    args = parser.parse_args()
    build(args.source, args.out)
