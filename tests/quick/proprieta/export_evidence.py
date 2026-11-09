"""Publish original native frames and audit equal project states without user data JSON."""
import argparse
import hashlib
import html
import json
import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter


def page(folder, title, body):
    folder.mkdir(parents=True, exist_ok=True)
    document = '''<!doctype html><meta charset="utf-8"><style>
body{font:16px system-ui;margin:24px;background:#f4f4f4;color:#222}figure{margin:20px 0;overflow:auto}
img{display:block;max-width:none}button{padding:8px;margin:8px}summary{cursor:pointer;padding:12px}</style>
<p><a href="../index.html">Tutti i confronti</a></p><h1>'''+html.escape(title)+'''</h1>
<button onclick="zoom(1)">100 %</button><button onclick="zoom(2)">200 %</button>
<script>function zoom(n){document.querySelectorAll('img[data-width]').forEach(i=>i.style.width=(Number(i.dataset.width)*n)+'px')}</script>'''
    (folder/'index.html').write_text(document+body, encoding='utf-8')


def picture(name, width):
    return f'<figure><img src="{name}" data-width="{width}" style="width:{width}px" alt="{name}"></figure>'


def pair(a, b, destination):
    images = [QImage(str(path)) for path in (a, b)]
    if any(im.isNull() for im in images):
        raise ValueError(f'Missing source image: {a}, {b}')
    image = QImage(sum(im.width() for im in images), max(im.height() for im in images), QImage.Format_RGB32)
    image.fill(Qt.gray)
    painter = QPainter(image)
    painter.drawImage(0, 0, images[0]); painter.drawImage(images[0].width(), 0, images[1])
    painter.end()
    assert image.save(str(destination))
    return image.width()


def main():
    parser = argparse.ArgumentParser()
    for name in ('out', 'pilot', 'frames', 'cards', 'cards_reference', 'empty', 'empty_reference'):
        parser.add_argument('--'+name.replace('_', '-'), type=Path, required=True)
    args = parser.parse_args()
    journey = args.out/'percorso'; journey.mkdir(parents=True, exist_ok=True)
    rows, audit = [], []
    for path in sorted(args.pilot.glob('*-quick.json')):
        quick = json.loads(path.read_text(encoding='utf-8'))
        widget = json.loads(path.with_name(path.name.replace('-quick', '-widgets')).read_text(encoding='utf-8'))
        for data in (quick, widget):
            data['project'].pop('modified', None)
        assert quick['project'] == widget['project'], path.name
        assert quick['phase'] == widget['phase'], path.name
        assert not quick['warnings'], path.name
        stem = path.stem.removesuffix('-quick')
        digest = hashlib.sha256(json.dumps(quick['project'], sort_keys=True).encode()).hexdigest()
        audit.append(dict(step=quick['step'], project_equal=True, project_sha256=digest,
                          phase=quick['phase'], warnings=quick['warnings']))
        name = stem+'-pair.png'
        width = pair(path.with_name(stem+'-widgets.png'), path.with_suffix('.png'), journey/name)
        rows.append(f'<details><summary>Passo {stem}: {html.escape(str(quick["step"]))}</summary>'+picture(name, width)+'</details>')
    assert len(audit) == 17
    (journey/'audit.json').write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding='utf-8')
    page(journey, 'Rho: stessi gesti nei due programmi', '<p>Widgets a sinistra, Quick a destra. Dati del progetto identici dopo ogni passo, escluso solo modified. Stati assestati; le transizioni sono nella pagina R377.</p>'+''.join(rows))
    frames = args.out/'r377'; frames.mkdir(parents=True, exist_ok=True)
    info = json.loads((args.frames/'frames.json').read_text(encoding='utf-8'))
    assert not info['errors'] and not info['unexpected_windows'] and info['frames'] >= 30
    shutil.copyfile(args.frames/'frames.json', frames/'frames.json')
    rows = []
    for record in info['records']:
        name = record['image']; source = args.frames/name
        shutil.copyfile(source, frames/name)
        width = QImage(str(source)).width()/info['dpr']
        rows.append(f'<details><summary>Fotogramma {record["index"]}</summary>'+picture(name, width)+'</details>')
    page(frames, 'R377: ogni fotogramma conserva contenuto', '<p>30 fotogrammi nativi, Direct3D 11, scala 2. Le sovrapposizioni di testo sono i passaggi della dissolvenza 180 ms OutCubic. Le letture dei pixel non misurano la presentazione al monitor.</p>'+''.join(rows))
    examples = args.out/'dettagli'; examples.mkdir(parents=True, exist_ok=True)
    rows = []
    for folder, reference in ((args.cards, args.cards_reference), (args.empty, args.empty_reference)):
        for source in sorted(folder.glob('quick-*-site-checks.png')):
            old = reference/source.name.replace('quick-', 'widgets-', 1)
            name = source.name.replace('quick-', 'pair-', 1)
            width = pair(old, source, examples/name)/2
            rows.append('<h2>'+html.escape(name)+'</h2>'+picture(name, width))
    page(examples, 'Verifiche: righe unite, sfumatura e vuoto', '<p>Widgets a sinistra, Quick a destra. La coppia cards usa una fixture visiva dichiarata, con due errori e note per far scorrere la lista. La coppia empty svuota esplicitamente i risultati. Non sono esiti del calcolo di Rho.</p>'+''.join(rows))
    print('Exported 17 audited steps, 30 frames and Checks detail pairs')


if __name__ == '__main__':
    main()
