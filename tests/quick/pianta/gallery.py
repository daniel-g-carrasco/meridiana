"""Publish paired, reproducible plan crops from the native-window review matrix."""
import hashlib
import html
import json
from pathlib import Path
import shutil

from PySide6.QtGui import QImage

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'build/r13-review'
DEST = ROOT / 'docs/quick/confronto/r13-pianta'
CASES = (
    ('light1', 13, 'Modellazione dopo il passaggio da Impianto'),
    ('light1', 12, 'Impianto: colori e nomi delle stringhe'),
    ('light1', 17, 'Edificio selezionato e inquadrato'),
    ('light1', 18, 'Lato in hover e prese dei vertici'),
    ('light1', 19, 'Doppio clic: campo della lunghezza aperto'),
    ('light1', 21, 'Menu contestuale dell’edificio'),
    ('light1', 14, 'Finestra ridotta a 1366 × 900'),
    ('light1', 25, 'Finestra ingrandita a 1920 × 1080'),
    ('dark2', 19, 'Tema scuro, scala 2: campo della lunghezza'),
    ('dark2', 21, 'Tema scuro, scala 2: menu contestuale'),
    ('dark1', 6, 'Tema scuro, scala 1: campo della lunghezza'),
    ('light2-large', 6, 'Tema chiaro, scala 2 e testo grande'),
)


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    manifest, sections = [], []
    for label, step, title in CASES:
        key = f'{label}-{step:02}'
        records, pictures = {}, {}
        for engine in ('widgets', 'quick'):
            prefix = SOURCE / label / f'{step:02}-{engine}'
            metadata = json.loads(prefix.with_name(prefix.name+'-plan.json').read_text(encoding='utf-8'))
            path = prefix.with_name(prefix.name+'-plan.png')
            image = QImage(str(path))
            assert not image.isNull(), path
            ratio = image.width() / metadata['rect'][2]
            zones = {'plan': (0, 0, *metadata['rect'][2:]), 'bar': (0, 0, 430, 100)}
            camera = metadata['camera']
            cx, cy = camera['panX'] + 161*camera['zoom'], camera['panY'] - 8.2177*camera['zoom']
            zones['side'] = (max(0, cx-180), max(0, cy-90), 360, 180)
            w, h = metadata['rect'][2:]
            for name, x, y in (('tl', 0, 0), ('tr', w-32, 0), ('bl', 0, h-32), ('br', w-32, h-32)):
                zones['corner-'+name] = (x, y, 32, 32)
            for zone, rect in zones.items():
                crop = image.copy(*(round(value*ratio) for value in rect))
                # PNG stores device pixels. CSS dimensions below express the requested logical zoom.
                filename = f'{key}-{engine}-{zone}.png'
                assert crop.save(str(DEST / filename))
                pictures[engine, zone] = (filename, round(rect[2]), round(rect[3]))
            records[engine] = dict(source=str(path.relative_to(ROOT)),
                                   source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                   metadata=metadata, device_pixel_ratio=ratio)
        manifest.append(dict(case=key, title=title, **records))
        lines = [f'<section id="{key}"><h2>{html.escape(title)}</h2>',
                 f'<p>{label}, passo {step:02}. Stesso progetto e copione. '
                 'Le larghezze delle viste dipendono dai pannelli della shell.</p>']
        for zone, caption, zoom in (('plan', 'Pianta, 100 %', 1), ('bar', 'Barra, 200 %', 2),
                                    ('side', 'Zona del lato, 200 %', 2),
                                    ('corner-tl', 'Angolo alto sinistro, 200 %', 2),
                                    ('corner-tr', 'Angolo alto destro, 200 %', 2),
                                    ('corner-bl', 'Angolo basso sinistro, 200 %', 2),
                                    ('corner-br', 'Angolo basso destro, 200 %', 2)):
            lines.append(f'<details {"open" if zone == "plan" else ""}><summary>{caption}</summary><div class="pair">')
            for engine in ('widgets', 'quick'):
                filename, width, height = pictures[engine, zone]
                lines.append(f'<figure><figcaption>{engine.title()}</figcaption><div class="scroll">'
                             f'<img loading="lazy" src="{filename}" width="{width*zoom}" '
                             f'height="{height*zoom}" alt="{engine}: {html.escape(title)}"></div></figure>')
            lines.append('</div></details>')
        lines.append('</section>')
        sections.append('\n'.join(lines))
    result = json.loads((SOURCE / 'result.json').read_text(encoding='utf-8'))
    (DEST / 'manifest.json').write_text(json.dumps(dict(review=result, cases=manifest), ensure_ascii=False, indent=2),
                                       encoding='utf-8')
    evidence = DEST/'misure'
    evidence.mkdir(exist_ok=True)
    for path in sorted((ROOT/'build').glob('r13-fluidity-*.json')):
        shutil.copyfile(path, evidence/path.name)
    for path in sorted((ROOT/'build/quick-foto/pianta/renderers').glob('*.json')):
        shutil.copyfile(path, evidence/path.name)
    for path in sorted((ROOT/'build/quick-foto/pianta/contracts').glob('*-card.png')):
        shutil.copyfile(path, DEST/path.name)
    for path in (ROOT/'build/r13-tests').glob('*.log'):
        shutil.copyfile(path, evidence/path.name)
    if (ROOT/'build/r13-tests/result.json').exists():
        shutil.copyfile(ROOT/'build/r13-tests/result.json', evidence/'plan-suite.json')
    page = '''<!doctype html><html lang="it"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>r13-pianta: confronto Widgets / Quick</title>
<style>body{font:16px system-ui;margin:24px;background:#eceef2;color:#20232b}
section{background:white;padding:16px;margin:24px 0;border:1px solid #c3c7d0}
h1,h2{font-weight:600}.pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}
figure{margin:12px 0;min-width:0}.scroll{overflow:auto;border:1px solid #aaa}
figcaption{font-weight:600;padding:6px}img{display:block;max-width:none}
summary{cursor:pointer;padding:8px}a{color:#2639a3}p{max-width:1000px;line-height:1.5}</style>
<h1>Pianta: Widgets e Quick</h1>
<p>Finestre native Direct3D 11, desktop separato, stesso progetto di Rho e stessi eventi Qt.
Le immagini non sono misure dei tempi di presentazione al monitor. Ogni coppia conserva il proprio
stato e le coordinate della camera in <a href="manifest.json">manifest.json</a>.
Aprire i dettagli per i ritagli al 200 %; le barre di scorrimento mantengono la scala reale.</p>
<p>Differenze dichiarate: dimensioni dei pannelli e quindi della vista; menu condiviso ancora
arrotondato; posizione di Meridio; piccole differenze di font e antialiasing. La Modellazione
è fotografata dopo il ritorno da Impianto: all’avvio i Widgets mostrano stringhe benché
il relativo comando sia spento. Il Quick segue lo stato del comando.</p>
<p>Prove aggiuntive: <a href="rotate-card.png">scheda Ruota</a>,
<a href="move-card.png">scheda Sposta</a>. I JSON delle misure sono conservati nella cartella misure.</p>
'''
    (DEST / 'index.html').write_text(page+'\n'.join(sections)+'</html>\n', encoding='utf-8')
    print(f'{len(CASES)} pairs, {len(CASES)*14} crops: {DEST}')


if __name__ == '__main__':
    main()
