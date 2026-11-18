"""Export paired native inspector crops and a readable 100/200 percent index."""
import argparse
import html
import json
import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    groups, metadata = [], []
    for meta in sorted(args.source.glob('quick-*-site.json')):
        info = json.loads(meta.read_text(encoding='utf-8'))
        stem = meta.stem.removeprefix('quick-').removesuffix('-site')
        scale = float(stem.rpartition('-x')[2])
        for subject in ('site', 'building', 'subfield', 'exclusion', 'prop'):
            for engine in ('widgets', 'quick'):
                name = f'{engine}-{stem}-{subject}.json'
                record = json.loads((args.source / name).read_text(encoding='utf-8'))
                assert not record['warnings'], name
                metadata.append(dict(capture=name, **record))
        cells, thumbs = [], []
        for subject, panel in [('site', 'properties'), ('building', 'properties'), ('subfield', 'properties'),
                               ('exclusion', 'properties'), ('prop', 'properties'), ('subfield', 'project'), ('site', 'checks')]:
            pair, images = [], []
            for engine in ('widgets', 'quick'):
                name = f'{engine}-{stem}-{subject}-{panel}.png'
                source = args.source / name
                shutil.copyfile(source, args.out / name)
                image = QImage(str(source))
                assert not image.isNull(), source
                images.append(image)
                logical = image.width() / scale
                pair.append(f'<figure><figcaption>{engine}</figcaption><img src="{name}" style="width:{logical}px" '
                            f'data-width="{logical}" alt="{engine}: {subject}, {panel}"></figure>')
            captions = {'site': 'Sito', 'building': 'Edificio', 'subfield': 'Sottocampo',
                        'exclusion': 'Esclusione', 'prop': 'Oggetto 3D', 'properties': 'Proprietà',
                        'project': 'Progetto', 'checks': 'Verifiche'}
            cells.append(f'<h3>{captions[subject]}: {captions[panel]}</h3><div class="pair">'+''.join(pair)+'</div>')
            if len(images) == 2:
                widths = [round(image.width() / scale) for image in images]
                height = min(550, max(round(image.height()/scale) for image in images))
                thumb = QImage(sum(widths), height, QImage.Format.Format_RGB32)
                thumb.fill(Qt.GlobalColor.white)
                paint = QPainter(thumb)
                x = 0
                for image, width in zip(images, widths, strict=True):
                    image.setDevicePixelRatio(1)
                    logical = image.scaledToWidth(width)
                    paint.drawImage(x, 0, logical)
                    x += width
                paint.end()
                thumbs.append(thumb)
        # The contact sheet is only an overview. The HTML retains original pixels.
        if thumbs:
            width = max(im.width() for im in thumbs)
            height = sum(im.height() for im in thumbs)
            contact = QImage(width, height, QImage.Format.Format_RGB32)
            contact.fill(Qt.GlobalColor.white)
            paint = QPainter(contact)
            y = 0
            for im in thumbs:
                paint.drawImage(0, y, im)
                y += im.height()
            paint.end()
            contact.save(str(args.out / f'overview-{stem}.png'))
        groups.append(f'<details><summary>{html.escape(stem)}: {html.escape(info["graphics"])}</summary>'+''.join(cells)+'</details>')
    (args.out / 'metadata.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
    (args.out / 'index.html').write_text('''<!doctype html><meta charset="utf-8"><title>Proprietà: confronto Widgets e Quick</title>
<style>body{font:16px system-ui;margin:24px;background:#f4f4f4;color:#222}summary{padding:12px;cursor:pointer;font-weight:600}.pair{display:flex;gap:16px;overflow:auto}figure{margin:0}figcaption{padding:6px}img{max-width:none;display:block}button{padding:8px;margin:8px}</style>
<h1>Proprietà, Verifiche, Progetto</h1><p>Widgets a sinistra, Quick a destra. Catture Windows native, stessa configurazione e stesso progetto in memoria. I pannelli possono avere altezze diverse: la disposizione della finestra appartiene a Shell. Le differenze rimaste sono nel rapporto r13-proprieta-fedelta.md.</p>
<p><a href="percorso/index.html">17 passi sul progetto reale di Rho</a> · <a href="dettagli/index.html">Schede e vuoto delle Verifiche</a> · <a href="r377/index.html">30 fotogrammi R377</a> · <a href="../../r13-proprieta-fedelta.md">Rapporto</a></p>
<button onclick="zoom(1)">100 % logico</button><button onclick="zoom(2)">200 % logico</button>
<script>function zoom(n){document.querySelectorAll('img[data-width]').forEach(i=>i.style.width=(Number(i.dataset.width)*n)+'px')}</script>
'''+''.join(groups), encoding='utf-8')
    print(f'{len(groups)} paired configurations exported to {args.out}')


if __name__ == '__main__':
    main()
