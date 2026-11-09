"""Keep native File comparisons and exact 200% crops in the repository."""
import html
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'build/quick-foto/r13-file'
DEST = ROOT / 'docs/quick/confronto/r13-file'


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    rows = []

    def pair(key, left, right, dpr, zones=()):
        assert left.is_file() and right.is_file(), (left, right)
        images = [Image.open(p).convert('RGB') for p in (left, right)]
        files = []
        for engine, im in zip(('widgets', 'quick'), images, strict=True):
            target = f'{key}-{engine}.webp'
            im.save(DEST / target, lossless=True)
            files.append(target)
        crops = []
        for name, box in zones:
            paths = []
            for engine, im in zip(('widgets', 'quick'), images, strict=True):
                crop = im.crop(tuple(round(n*dpr) for n in box))
                crop = crop.resize((round(crop.width*2/dpr), round(crop.height*2/dpr)), Image.Resampling.NEAREST)
                target = f'{key}-{name}-{engine}-200.webp'
                crop.save(DEST / target, lossless=True)
                paths.append(target)
            crops.append(dict(name=name, images=paths))
        rows.append(dict(key=key, images=files, crops=crops, dpr=dpr,
                         sources=[p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else p.as_posix() for p in (left, right)]))

    for right in sorted((SOURCE / 'review-r8').glob('quick-*.png')):
        key = right.stem.removeprefix('quick-')
        dpr = int(key.split('-')[1])
        left = SOURCE / ('matrix-r2' if dpr == 1 else 'final') / ('widgets-' + key + '.png')
        zones = [('ritorno', (20, 50, 265, 160)), ('titolo-campi', (300, 70, 1070, 310)),
                 ('piede', (300, 860, 1070, 906))] if '1600x960' in key else []
        pair(key, left, right, dpr, zones)
    reference = ROOT.parent / 'meridiana-wt-r12-sistema/build/quick-foto/riferimento'
    for left in sorted(reference.glob('widgets-*-file.png')):
        key = left.stem.removeprefix('widgets-').removesuffix('-file')
        right = SOURCE / 'review-r8' / ('quick-' + key + '-preferences-appearance.png')
        pair('r12-' + key, left, right, int(key.split('-')[1]))
    for right in sorted((SOURCE / 'workflows-r9').glob('quick-*.png')):
        key = right.stem.removeprefix('quick-')
        dpr = int(key.split('-')[1])
        left = SOURCE / ('workflows-r4' if dpr == 1 else 'workflows-r6') / ('widgets-' + key + '.png')
        pair('finestre-' + key, left, right, dpr,
             [('controlli', (1225, 165, 1580, 470))] if key.endswith('report') else [])
    for right in sorted((SOURCE / 'imports-r4').glob('quick-*.png')):
        key = right.stem.removeprefix('quick-')
        pair('importazioni-' + key, SOURCE / 'imports' / ('widgets-' + key + '.png'), right, 1)
    for right in sorted((SOURCE / 'report-fixture-r5').glob('quick-*-1-report.png')):
        key = right.stem.removeprefix('quick-')
        pair('relazione-calcolata-' + key, SOURCE / 'report-fixture-r4' / ('widgets-' + key + '.png'), right, 1)
    for left in sorted((SOURCE / 'pilot-final-r3').glob('*-widgets.png')):
        right = left.with_name(left.name.replace('-widgets', '-quick'))
        pair('percorso-' + left.stem.removesuffix('-widgets'), left, right, 1)
    (DEST / 'manifest.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf8')
    body = []
    for row in rows:
        images = ''.join(f'<figure><figcaption>{name}</figcaption><a href="{p}"><img loading="lazy" src="{p}"></a></figure>'
                         for name, p in zip(('Widgets', 'Quick'), row['images'], strict=True))
        crops = ''.join('<details><summary>' + html.escape(c['name']) + ' al 200%</summary><div class="crop">' +
                        ''.join(f'<figure><figcaption>{n}</figcaption><img loading="lazy" src="{p}"></figure>'
                                for n, p in zip(('Widgets', 'Quick'), c['images'], strict=True)) + '</div></details>'
                        for c in row['crops'])
        body.append(f'<section id="{row["key"]}"><h2>{row["key"]}</h2><div class="pair">{images}</div>{crops}</section>')
    progress = []
    for mode in ('light', 'dark'):
        name = f'relazione-avanzamento-{mode}.webp'
        Image.open(SOURCE / 'report-fixture-r5' / f'quick-{mode}-progress.png').convert('RGB').save(DEST / name, lossless=True)
        progress.append(f'<figure><figcaption>Quick, {mode}</figcaption><a href="{name}"><img src="{name}" loading="lazy"></a></figure>')
    body.append('<section id="relazione-avanzamento"><h2>Avanzamento della Relazione</h2><p>Due stati Quick durante la compilazione. Questa sezione non è una coppia di confronto con i Widgets.</p><div class="pair">' + ''.join(progress) + '</div></section>')
    page = '''<!doctype html><html lang="it"><meta charset="utf-8"><title>r13-file: confronto nativo</title>
<style>body{font:15px system-ui;margin:24px;background:#e8e8e8;color:#222}h1{font-size:26px}h2{font-size:18px}
section{background:#fff;padding:16px;margin:20px 0;border-radius:8px}figure{margin:0;min-width:0}figcaption{padding:6px;font-weight:600}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}.pair img{width:100%;height:auto}.crop{display:flex;gap:16px;overflow:auto}.crop img{max-width:none}
details{margin-top:12px}summary{cursor:pointer}input{padding:9px;width:min(600px,90%)}p{max-width:1000px;line-height:1.5}</style>
<h1>File, Impostazioni, Relazione e finestre</h1>
<p>Widgets a sinistra, Quick a destra. Foto native Direct3D 11: File e percorso sul progetto di prova di Rho,
relazione calcolata su una fixture identica con meteo sintetico e rete disattivata, importazioni sui file delle prove.
L'aggiornamento usa la release simulata offline 99.0.0: nessun installer eseguito. Temi chiaro/scuro, scale 1 e 2,
1366×900, 1600×960 e 1920×1080. Le finestre sono ritagli della finestra vera. Clic sull'immagine per i pixel originali.
I ritagli al 200% usano pixel logici: nessun allineamento o ritocco per nascondere differenze.</p>
<p><strong>Non è una certificazione di indistinguibilità.</strong> Le differenze, le semplificazioni e i limiti delle prove
sono elencati in <a href="../../r13-file-fedelta.md">r13-file-fedelta.md</a>. Matrice File acquisita dopo le ultime correzioni;
finestre e percorso mantengono le sorgenti indicate nel manifest. Il cursore del sistema e la fluidità del monitor non sono misurati.</p>
<input placeholder="Filtra: appearance, maps, report, finestre, percorso..." oninput="for(const s of document.querySelectorAll('section'))s.hidden=!s.id.includes(this.value.toLowerCase())">
''' + '\n'.join(body) + '</html>'
    (DEST / 'index.html').write_text(page, encoding='utf8')
    print(f'{len(rows)} pairs, {sum(len(r["crops"]) for r in rows)} crop pairs')


if __name__ == '__main__':
    main()
