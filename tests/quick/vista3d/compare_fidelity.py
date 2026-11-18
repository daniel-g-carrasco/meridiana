"""Build the reviewable 100% pictures and 200% crops from real D3D11 captures."""
import argparse
import html
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=Path('build/quick-foto/r13-vista3d'))
    parser.add_argument('--out', type=Path, default=Path('docs/quick/confronto/r13-vista3d'))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    blocks, metrics = [], {}
    for folder in sorted(args.source.glob('detail-*')):
        if not (folder/'quick-calendar.png').exists():
            continue
        name = folder.name
        scale = int(name.split('-')[2])
        a = Image.open(folder/'widgets-normal.png').convert('RGB')
        b = Image.open(folder/'quick-normal.png').convert('RGB')
        w, h = a.width//scale, a.height//scale
        blocks.append(f'<section><h2>{html.escape(name)}</h2><p>{w} × {h} logici, scala {scale}. '
                      'Stessa camera, geometria e posizione solare.</p>')
        for state in ('normal', 'selected', 'gizmo'):
            images = []
            for engine in ('widgets','quick'):
                target = f'{name}-{engine}-{state}.png'
                shutil.copyfile(folder/f'{engine}-{state}.png',args.out/target)
                images.append(f'<figure><figcaption>{engine}: {state}</figcaption><a href="{target}">'
                              f'<img src="{target}" style="width:{w}px" alt="{engine}, {state}"></a></figure>')
            blocks.append('<div class="pair">'+''.join(images)+'</div>')
        for zone, state, rect in [('barra','normal',(0,0,120,48)), ('cubo','normal',(w-120,0,w,125)),
                                  ('sole','normal',(0,h-40,w,h)), ('contorno','selected',(w*.15,h*.25,w*.82,h*.82)),
                                  ('maniglie','gizmo',(w*.35,h*.23,w*.64,h*.5))]:
            images = []
            for engine in ('widgets','quick'):
                original = Image.open(folder/f'{engine}-{state}.png').convert('RGB')
                crop = original.crop(tuple(round(n*scale) for n in rect))
                crop = crop.resize((round(crop.width*2/scale),round(crop.height*2/scale)),Image.Resampling.NEAREST)
                target = f'{name}-{engine}-{zone}-200.png'
                crop.save(args.out/target)
                images.append(f'<figure><figcaption>{engine}</figcaption><img src="{target}" alt="{zone}, {engine}"></figure>')
            blocks.append(f'<h3>{zone}: 200 %</h3><div class="pair">'+''.join(images)+'</div>')
        images = []
        for engine in ('widgets','quick'):
            crop = Image.open(folder/f'{engine}-calendar.png')
            crop = crop.resize((round(crop.width*2/scale),round(crop.height*2/scale)),Image.Resampling.NEAREST)
            target = f'{name}-{engine}-calendario-200.png'
            crop.save(args.out/target)
            images.append(f'<figure><figcaption>{engine}</figcaption><img src="{target}" alt="Calendario {engine}"></figure>')
        blocks.append('<h3>Calendario: 200 %</h3><div class="pair">'+''.join(images)+'</div></section>')
        for file in ('reference.json','widgets.json','quick.json'):
            shutil.copyfile(folder/file,args.out/f'{name}-{file}')
        # Roof/walls and their shadow, excluding the intentionally different horizon.
        rect = (round(w*.15*scale),round(h*.25*scale),round(w*.82*scale),round(h*.82*scale))
        diff = np.abs(np.asarray(a.crop(rect),int)-np.asarray(b.crop(rect),int))
        metrics[name] = {'logical_size':[w,h], 'scale':scale,
                         'scene_crop_mean_channel_difference':round(float(diff.mean()),4),
                         'scene_crop_pixels_over_8_percent':round(float((diff.max(2)>8).mean()*100),4)}
    journey = args.source/'pilot-final-light-1'
    if journey.exists():
        blocks.append('<section><h2>Rho: finestra completa, gesti reali</h2><p>Le altre parti della finestra '
                      'appartengono ai rispettivi rami. Il confronto della camera congelata è sopra.</p>')
        for step, title in [(1,'Vista 3D'),(5,'Menu contestuale'),(9,'Menu del cubo'),
                            (11,'Calendario'),(17,'1366 × 900'),(20,'1920 × 1080')]:
            images=[]
            for engine in ('widgets','quick'):
                name=f'{step:02}-{engine}'
                for suffix in ('.png','.json'):
                    shutil.copyfile(journey/(name+suffix),args.out/('rho-'+name+suffix))
                target=f'rho-{name}.png'
                images.append(f'<figure><figcaption>{engine}</figcaption><a href="{target}">'
                              f'<img src="{target}" alt="{title}, {engine}"></a></figure>')
            blocks.append(f'<h3>{title}</h3><div class="pair">'+''.join(images)+'</div>')
        blocks.append('</section>')
    if (args.source/'ground-before.png').exists():
        blocks.append('<section><h2>Terreno: regressione prima e dopo</h2><div class="pair">')
        for state in ('before','after'):
            target=f'ground-{state}.png'
            shutil.copyfile(args.source/target,args.out/target)
            blocks.append(f'<figure><figcaption>{state}</figcaption><img src="{target}" alt="Terreno {state}"></figure>')
        blocks.append('</div></section>')
    css = 'body{font:14px system-ui;margin:24px;color:#222;background:#eee}h2{margin-top:48px}.pair{display:flex;gap:20px;overflow:auto;padding:8px;background:#ddd}figure{margin:0;flex:none}figcaption{padding:6px}img{display:block}a{color:#334c91}section{border-top:1px solid #bbb}'
    intro = ('<h1>Vista 3D: Widgets e Quick</h1><p>Foto native Direct3D 11, 4 e 5 novembre 2026. '
             'Le immagini intere sono mostrate al 100 % della misura logica; clic per i pixel originali. '
             'I ritagli sono al 200 %, senza interpolazione. '
             '<a href="../../r13-vista3d-fedelta.md">Rapporto e limiti</a>. '
             'Log e tempi completi nella cartella verifiche. Nelle foto Rho l’animazione di Meridio '
             'è disabilitata in entrambi i programmi; nelle prove della finestra rimane attiva.</p><p>Il terreno Quick arriva all’orizzonte, '
             'come richiesto: il riferimento Widgets di questa base mantiene il rettangolo finito. '
             'Questa differenza è deliberata. Calendario nativo Quick: stessa misura e comandi, '
             'con piccole differenze nella distribuzione delle celle e nel campo dell’anno.</p>')
    (args.out/'index.html').write_text('<!doctype html><html lang="it"><meta charset="utf-8"><title>Fedeltà vista 3D</title>'
                                     f'<style>{css}</style>'+intro+''.join(blocks)+'</html>',encoding='utf-8')
    (args.out/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    print(json.dumps(metrics,indent=2))


if __name__ == '__main__':
    main()
