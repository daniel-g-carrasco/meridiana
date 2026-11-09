"""Publish lossless pairs, 200% details and their native acquisition metadata."""
import argparse
import html
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[3]
PHOTOS = ROOT / 'build/quick-foto/r13-fasi'
CASES = {
    'chiaro-100': ('matrice-r01/light-s1', 'finale-r01/light-s1'),
    'scuro-100': ('matrice-r01/dark-s1', 'matrice-r02/dark-s1'),
    'chiaro-200': ('matrice-r03/light-s2', 'matrice-r03/light-s2'),
    'scuro-200': ('matrice-r03/dark-s2', 'matrice-r03/dark-s2'),
}


def pair(left, right):
    canvas = Image.new('RGB', (left.width+right.width, max(left.height, right.height)), '#777777')
    canvas.paste(left, (0, 0))
    canvas.paste(right, (left.width, 0))
    return canvas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--update', action='store_true', help='Regenerate only this tool\'s published gallery')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=args.update)
    contacts = PHOTOS / 'review-contacts'
    contacts.mkdir(exist_ok=args.update)
    manifest, body = [], []
    for case, (old, new) in CASES.items():
        body.append(f'<section id="{case}"><h2>{case}</h2>')
        thumbs = []
        for index in range(31):
            old_base = PHOTOS / old / f'{index:02}-widgets'
            new_base = PHOTOS / new / f'{index:02}-quick'
            a = json.loads(old_base.with_suffix('.json').read_text(encoding='utf8'))
            b = json.loads(new_base.with_suffix('.json').read_text(encoding='utf8'))
            assert a['phase'] == b['phase'] and a['size'] == b['size'] and a['dpr'] == b['dpr'], (case, index)
            assert not b['warnings'], b['warnings']
            image = pair(Image.open(old_base.with_suffix('.png')), Image.open(new_base.with_suffix('.png')))
            name = f'{case}-{index:02}.webp'
            image.save(args.output / name, lossless=True)
            step = b['step']
            label = f'{index:02} · {b["phase"]} · {step.get("target", step.get("key", step.get("size", "")))}'
            row = dict(case=case, index=index, phase=b['phase'], size=b['size'], dpr=b['dpr'],
                       graphics=b['graphics'], warnings=b['warnings'], theme=b['theme'],
                       source_widgets=str(old_base.relative_to(ROOT)), source_quick=str(new_base.relative_to(ROOT)),
                       step=step, file=name)
            manifest.append(row)
            body.append(f'<figure><figcaption>{html.escape(label)}</figcaption><div class="imagebox">'
                        f'<img loading="lazy" src="{name}" data-logical="{image.width/b["dpr"]}" '
                        f'alt="{html.escape(label)}: Widgets a sinistra, Quick a destra"></div></figure>')
            thumb = image.copy()
            thumb.thumbnail((1600, 480))
            titled = Image.new('RGB', (1600, thumb.height+24), '#eeeeee')
            ImageDraw.Draw(titled).text((10, 5), label, fill='black')
            titled.paste(thumb, (0, 24))
            thumbs.append(titled)
        for start in range(0, len(thumbs), 4):
            pages = thumbs[start:start+4]
            contact = Image.new('RGB', (1600, sum(p.height for p in pages)), 'white')
            y = 0
            for page in pages:
                contact.paste(page, (0, y))
                y += page.height
            contact.save(contacts / f'{case}-{start//4:02}.png')
        body.append('</section>')
    body.append('<section id="grafici"><h2>Grafici e particolari al 200%</h2>')
    for theme, source in (('chiaro', 'grafici-r06-chiaro'), ('scuro', 'grafici-r07-scuro')):
        for name in ('barre', 'impilate', 'perdite', 'giorno', 'mappa', 'settimana', 'anno', 'cassa', 'confronti', 'flussi'):
            image = Image.open(PHOTOS / source / f'{name}.png')
            dest = f'grafico-{theme}-{name}.webp'
            image.save(args.output / dest, lossless=True)
            body.append(f'<figure><figcaption>{theme}: {name}</figcaption><div class="imagebox">'
                        f'<img loading="lazy" src="{dest}" data-logical="1800"></div></figure>')
        image = Image.open(PHOTOS / source / 'confronti.png')
        dpr = 1 if theme == 'chiaro' else 2
        # Same physical plot point in each half, including the line and its marker.
        crops = [image.crop(tuple(int(v*dpr) for v in (x+390, 210, x+490, 350))) for x in (0, 900)]
        detail = pair(*crops)
        detail = detail.resize((400, 280), Image.Resampling.NEAREST)
        dest = f'particolare-{theme}-200.png'
        detail.save(args.output / dest)
        body.append(f'<figure><figcaption>{theme}: linea e marcatori al 200%</figcaption><img src="{dest}"></figure>')
    body.append('</section>')
    body.append('<section id="formule"><h2>05/11: formule e quantità dopo la correzione</h2>'
                '<p>Queste tre coppie aggiornano le schede Come è calcolato della matrice precedente.</p>')
    for index in (1, 3, 5):
        old = PHOTOS / 'formule-r01' / f'{index:02}-widgets'
        new = PHOTOS / 'formule-r02' / f'{index:02}-quick'
        a, b = (json.loads(p.with_suffix('.json').read_text(encoding='utf8')) for p in (old, new))
        assert a['phase'] == b['phase'] and a['size'] == b['size'] and a['dpr'] == b['dpr']
        assert not b['warnings'], b['warnings']
        combined = pair(Image.open(old.with_suffix('.png')), Image.open(new.with_suffix('.png')))
        name = f'formule-{b["phase"]}.webp'
        combined.save(args.output / name, lossless=True)
        body.append(f'<figure><figcaption>{b["phase"]}</figcaption><div class="imagebox">'
                    f'<img loading="lazy" src="{name}" data-logical="3200"></div></figure>')
        manifest.append(dict(case='formule-05-11', phase=b['phase'], file=name,
                             source_widgets=str(old.relative_to(ROOT)), source_quick=str(new.relative_to(ROOT)),
                             graphics=b['graphics'], warnings=b['warnings'], dpr=b['dpr']))
    body.append('</section><section id="comandi"><h2>05/11: gesti nella finestra Quick</h2>'
                '<p>Progetto di test con due inverter. Sono prove dei comandi, non coppie Widgets/Quick.</p>')
    source = PHOTOS / 'comandi-8968'
    for shot in sorted(source.glob('*.png')):
        image = Image.open(shot)
        name = 'comando-' + shot.stem + '.webp'
        image.save(args.output / name, lossless=True)
        body.append(f'<figure><figcaption>{html.escape(shot.stem)}</figcaption><div class="imagebox">'
                    f'<img loading="lazy" src="{name}" data-logical="1600"></div></figure>')
    body.append('</section>')
    body.append('<section id="calcolo"><h2>Calcolo reale da F5</h2>'
                '<p>Risultato assente all’avvio. F5 avvia il worker: 8.760 ore, 425.566,385 kWh, '
                'poi le tre pagine ricevono lo stesso anno. Meteo registrato, progetto originale invariato. '
                '<a href="calcolo-f5.json">Dati e tempi</a>.</p>')
    source = PHOTOS / 'calcolo-f5-r01'
    payload = json.loads((source / 'result.json').read_text(encoding='utf8'))
    assert payload['hours'] == 8760 and not payload['warnings']
    (args.output / 'calcolo-f5.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf8')
    for phase in ('production', 'consumption', 'economics'):
        image = Image.open(source / (phase+'.png'))
        name = f'calcolo-f5-{phase}.webp'
        image.save(args.output / name, lossless=True)
        body.append(f'<figure><figcaption>{phase}</figcaption><div class="imagebox">'
                    f'<img loading="lazy" src="{name}" data-logical="1600"></div></figure>')
    body.append('</section>')
    (args.output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf8')
    document = '''<!doctype html><html lang="it"><meta charset="utf-8"><title>r13-fasi: confronto Widgets e Quick</title>
<style>body{margin:0;background:#f1f1f1;color:#222;font:15px system-ui}header,section{padding:20px;max-width:1640px;margin:auto}
nav{position:sticky;top:0;background:#eee;padding:12px;z-index:2;border-bottom:1px solid #aaa}a,button{margin-right:16px}
figure{margin:20px 0;background:white;padding:12px;border:1px solid #ccc;border-radius:6px}figcaption{margin-bottom:10px}
.imagebox{overflow:auto}img{max-width:100%;height:auto;display:block}button{padding:6px 12px}</style>
<header><h1>Impianto e risultati: Widgets a sinistra, Quick a destra</h1>
<p>04-05/11/2026. Rho, anno calcolato dal nucleo con meteo registrato: 425.566 kWh, 358,56 kWp,
702 moduli collegati su 778, 7 inverter. Acquisizioni native Windows, Direct3D 11 sul desktop separato.</p>
<p>124 coppie della matrice, 20 coppie dei grafici, tre confronti aggiornati delle formule e il percorso dei comandi.
Le immagini WebP sono senza perdita. I metadati originali e le cartelle di acquisizione sono nel manifest.
La matrice documenta la revisione precedente alle ultime correzioni di formule e altezza minima dei grafici;
le sezioni Formule e Comandi mostrano le correzioni successive. I grafici isolati sono gli ultimi.</p>
<p><strong>Esito con riserve:</strong> disposizione della finestra e alcuni margini differiscono ancora.
Il bordo destro in Consumi supera 30 ms. Consultare <a href="../../r13-fasi-fedelta.md">il resoconto</a>.
Le coppie confrontano lo stesso stato, non certificano da sole la fedeltà di ogni pixel.</p></header>
<nav><a href="#chiaro-100">Chiaro 100%</a><a href="#scuro-100">Scuro 100%</a><a href="#chiaro-200">Chiaro 200%</a>
<a href="#scuro-200">Scuro 200%</a><a href="#grafici">Grafici</a>
<a href="#formule">Formule aggiornate</a><a href="#comandi">Comandi</a><a href="#calcolo">Calcolo da F5</a>
<button onclick="scale(0)">Adatta</button><button onclick="scale(1)">100%</button><button onclick="scale(2)">200%</button></nav>
<script>function scale(n){document.querySelectorAll('[data-logical]').forEach(i=>{i.style.maxWidth=n?'none':'100%';i.style.width=n?(Number(i.dataset.logical)*n)+'px':''})}</script>
'''+''.join(body)+'</html>'
    (args.output / 'index.html').write_text(document, encoding='utf8')
    print(f'{len(manifest)} window pairs, 20 chart pairs, 2 details: {args.output}')


if __name__ == '__main__':
    main()
