"""Build one offline HTML comparison from matching Widgets and Quick PNG captures.

No image is scaled or rewritten. PNG headers and metadata must agree with the
requested logical dimensions and DPR. Missing or mismatched evidence fails by
default; --allow-missing produces a visibly incomplete work-in-progress report.
"""
import argparse
import base64
import hashlib
import html
import json
import struct
from datetime import datetime
from pathlib import Path

STATES = ('normal', 'selection', 'menu', 'file', 'help', 'large', 'closed', 'grouped')
SIZES = ((1366, 900), (1600, 960), (1920, 1080))
LABELS = dict(normal='Modellazione', selection='Edificio selezionato', menu='Barra menu visibile',
              file='File: Impostazioni > Aspetto', help='Aiuto della modellazione', large='Testo grande',
              closed='Progetto chiuso', grouped='Progetto e Proprietà raggruppati')
DIFFERENCES = {
    'normal': 'Il riferimento Widgets include la vista 3D, le proprietà del sito e le verifiche complete. '
              'La shell Quick mostra i punti di integrazione dei rami: la sola presenza delle schede '
              'non prova l’equivalenza dei loro contenuti. Confrontare soprattutto fasi, strumenti, '
              'superfici, margini e proporzioni.',
    'selection': 'Entrambe le catture selezionano l’edificio b1, Capannone. Nei Widgets sono disponibili '
                 'tetto, lati, prevenzione incendi e selezione 3D. La scheda Quick di questo traguardo '
                 'è ridotta ai campi implementati: i campi mancanti restano lavoro aperto.',
    'menu': 'È aperta la barra dei menu sopra le fasi, senza menu a tendina. La cattura confronta '
            'la fascia aggiunta e la disposizione risultante; non certifica la disponibilità '
            'di tutti i comandi dei menu.',
    'file': 'Entrambe mostrano Aspetto. I Widgets hanno l’intera pagina Impostazioni e la navigazione '
            'tra categorie; Quick mostra il pannello Aspetto del primo traguardo. Impaginazione, '
            'anteprima e disponibilità delle altre sezioni differiscono.',
    'help': 'Differenza voluta da R383: nei Widgets l’aiuto della fase è nel pannello Aiuto; '
            'in Quick è nel fumetto di Meridio. Testo, collocazione e spazio lasciato alle Proprietà '
            'vanno giudicati separatamente: le due aree non sono sovrapponibili al pixel.',
    'large': 'Testo grande, corpo a 14 pixel logici in entrambi. La cattura permette di cercare '
             'troncamenti e sovrapposizioni; non basta il solo valore della dimensione. '
             'Restano le differenze di contenuto già dichiarate per Modellazione.',
    'closed': 'Il pannello Progetto è chiuso in entrambi. Confrontare lo spazio restituito alle viste '
              'e il mantenimento di Proprietà e Verifiche. Le viste centrali hanno contenuti '
              'diversi fino all’integrazione degli altri rami.',
    'grouped': 'Progetto e Proprietà sono raggruppati a destra, con Proprietà davanti. '
               'Nei Widgets il gruppo usa QDockWidget; in Quick usa il contenitore QML. '
               'Confrontare linguette, margini, titolo e spazio liberato a sinistra.',
}


def read_capture(folder, prefix, theme, dpr, width, height, state):
    name = f'{prefix}-{theme}-{dpr}-{width}x{height}-{state}'
    png, metadata = folder / (name + '.png'), folder / (name + '.json')
    if not png.exists() or not metadata.exists():
        raise FileNotFoundError(f'{name}: PNG o metadati mancanti in {folder}')
    content = png.read_bytes()
    if content[:8] != b'\x89PNG\r\n\x1a\n' or content[12:16] != b'IHDR':
        raise ValueError(f'{png}: formato PNG non valido')
    pixels = struct.unpack('>II', content[16:24])
    data = json.loads(metadata.read_text(encoding='utf-8'))
    if (data['width'], data['height'], data['dpr']) != (width, height, dpr):
        raise ValueError(f'{name}: dimensioni logiche o DPR diversi dal caso richiesto')
    if pixels != (width * dpr, height * dpr):
        raise ValueError(f'{name}: PNG {pixels}, atteso {(width*dpr, height*dpr)}')
    if data.get('warnings'):
        raise ValueError(f'{name}: avvisi QML {data["warnings"]}')
    if data.get('fixture') != 'capannone':
        raise ValueError(f'{name}: fixture diversa da capannone')
    if data.get('modules') != 128:
        raise ValueError(f'{name}: conteggio moduli diverso dalla fixture posata (128)')
    if data.get('state') != state or data.get('theme') != theme:
        raise ValueError(f'{name}: stato o tema dei metadati non corrispondenti')
    if (data.get('pixelWidth'), data.get('pixelHeight')) != pixels:
        raise ValueError(f'{name}: dimensioni fisiche dei metadati diverse dal PNG')
    return dict(name=name, source=str(png), metadata=data, pixels=pixels,
                sha256=hashlib.sha256(content).hexdigest(),
                image='data:image/png;base64,' + base64.b64encode(content).decode('ascii'))


def collect(widgets, quick, allow_missing=False):
    rows, missing = [], []
    for theme in ('light', 'dark'):
        for dpr in (1, 2):
            for width, height in SIZES:
                for state in STATES:
                    row = dict(theme=theme, dpr=dpr, width=width, height=height, state=state,
                               label=LABELS[state], difference=DIFFERENCES[state])
                    if theme == 'dark' and dpr == 1 and width == 1366 and state not in ('selection', 'file'):
                        row['difference'] += (
                            ' Difetto residuo lieve del prototipo: in questa combinazione i lati verticali '
                            'del contorno esterno dell’edificio non sono visibili, mentre i lati orizzontali '
                            'e il rettangolo interno restano visibili. Il renderer dedicato della pianta '
                            'deve sostituire quello del prototipo; la foto conserva il difetto.')
                    for key, folder, prefix in (('widgets', widgets, 'widgets'), ('quick', quick, 'quick')):
                        try:
                            row[key] = read_capture(folder, prefix, theme, dpr, width, height, state)
                        except FileNotFoundError as error:
                            if not allow_missing:
                                raise
                            row[key] = None
                            missing.append(str(error))
                    rows.append(row)
    return rows, missing


DOCUMENT = '''<!doctype html>
<html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Meridiana: confronto Modellazione Widgets / Quick</title>
<style>
:root{color-scheme:light;--ink:#24232b;--muted:#605e6d;--accent:#5b4bb0;--line:#dbd9e1}
*{box-sizing:border-box}body{margin:0;background:#f1f0f4;color:var(--ink);font:15px/1.5 system-ui,sans-serif}
header,main{max-width:2000px;margin:auto;padding:24px}header{padding-bottom:8px}h1{font-size:28px;margin:0 0 8px}
h2{font-size:20px;margin:0}p{margin:8px 0}.muted{color:var(--muted)}.notice{padding:14px 18px;background:#fff5dd;border-left:4px solid #bd8d25}
.filters{display:flex;gap:16px;flex-wrap:wrap;align-items:end;padding:16px 0;position:sticky;top:0;background:#f1f0f4;z-index:1}
label{display:flex;flex-direction:column;font-size:13px;gap:4px}select,button{font:inherit;color:inherit;border:1px solid var(--line);border-radius:6px;padding:8px 12px;background:white}
button{cursor:pointer}button:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}figure{margin:0;min-width:0;background:white;border:1px solid var(--line);border-radius:8px;overflow:hidden}
figcaption{padding:10px 14px;font-weight:600;border-bottom:1px solid var(--line)}.picture{overflow:auto;min-height:150px;background:#e2e1e7}
img{display:block;width:100%;height:auto}.native img{width:auto;max-width:none}.meta{padding:10px 14px;color:var(--muted);font-size:12px;overflow-wrap:anywhere}
.difference{border:1px solid var(--line);border-radius:8px;background:white;padding:14px 18px;margin-top:16px}
details{margin-top:16px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;padding:16px;background:white;border:1px solid var(--line)}
.empty{padding:40px 16px;color:#8d251d;font-weight:600}footer{padding:24px;color:var(--muted);border-top:1px solid var(--line);font-size:13px}
@media(max-width:900px){.pair{grid-template-columns:1fr}header,main{padding:16px}.filters{position:static}}
</style>
<header><h1>Modellazione: Widgets e Qt Quick</h1>
<p>Stesso capannone di prova, stessi temi, dimensioni e stati. Immagini originali incorporate: questo file funziona senza rete.</p>
<p class="muted">Generato il __DATE__. __SUMMARY__</p>
<p class="notice">Confronto visivo del traguardo r12-sistema. Non è una dichiarazione di parità completa: proprietà, verifiche, vista 3D e pagine File hanno differenze o integrazioni ancora aperte. Non sono stati applicati ritagli, riallineamenti o correzioni alle immagini.</p></header>
<main><nav class="filters" aria-label="Scegli una coppia di catture">
<label>Tema<select id="theme"><option value="light">Chiaro</option><option value="dark">Scuro</option></select></label>
<label>Scala<select id="dpr"><option value="1">100 %</option><option value="2">200 %</option></select></label>
<label>Finestra, pixel logici<select id="size"><option>1366x900</option><option selected>1600x960</option><option>1920x1080</option></select></label>
<label>Stato<select id="state">__STATES__</select></label>
<button id="previous" type="button">Stato precedente</button><button id="next" type="button">Stato successivo</button>
<button id="zoom" type="button" aria-pressed="false">Vedi pixel originali</button></nav>
<h2 id="title"></h2><p id="counter" class="muted" aria-live="polite"></p>
<section class="pair" aria-label="Catture affiancate"><figure><figcaption>Widgets: riferimento esistente</figcaption><div class="picture" id="widgets-picture"></div><div class="meta" id="widgets-meta"></div></figure>
<figure><figcaption>Qt Quick: nuovo sistema</figcaption><div class="picture" id="quick-picture"></div><div class="meta" id="quick-meta"></div></figure></section>
<section class="difference"><strong>Differenze e limiti di questo stato</strong><p id="difference"></p></section>
<details><summary>Metadati e provenienza della coppia</summary><pre id="metadata"></pre></details>
<details><summary>Metodo e matrice</summary><p>96 coppie: 2 temi × 2 scale × 3 dimensioni × 8 stati. Fixture tests/_fixtures.py, capannone(): edificio b1 di 40 × 20 m, altezza 9,5 m, sottocampo Sud, 128 moduli dopo la posa. Configurazione isolata, Plex con condensato nella barra, fondi grey e accento indigo. Le finestre sono senza cornice soltanto per le catture: la barra del titolo di Windows non fa parte del confronto.</p>
<p>Widgets: win.grab() sul desktop separato; Quick: cattura della finestra sul desktop separato. Le dimensioni fisiche del PNG sono verificate dal generatore contro dimensioni logiche e DPR. Per gli stati vengono invocati i servizi della finestra: questi scatti non sostituiscono le prove di eventi Qt.</p>
<p>Le larghezze iniziali dei pannelli Widgets dipendono dallo schermo: nel desktop isolato sono 320/380 pixel a scala 1 e 240/300 a scala 2. I metadati conservano queste misure reali. Non sono state modificate per farle coincidere con Quick; una differenza nella larghezza del pannello va distinta da una differenza nei margini interni.</p>
<p>La baseline del ramo r12-compat usa fixture empty e capannone_rho, diverse da questa. Non è stata impiegata per fingere coppie equivalenti. Nessun risultato di fluidità è dedotto da immagini statiche.</p></details>
__MISSING__</main><footer>Riferimenti: docs/quick/CONTESTO.md, docs/quick/sistema-piano.md. Generatori: tools/quick_widgets_reference.py, tools/quick_shell_capture.py, tools/quick_comparison.py.</footer>
<script id="evidence" type="application/json">__DATA__</script>
<script>
const rows=JSON.parse(document.getElementById('evidence').textContent);
const states=__STATE_KEYS__;
const byId=id=>document.getElementById(id);
function render(){
  const dimensions=byId('size').value.split('x').map(Number);
  const row=rows.find(r=>r.theme===byId('theme').value&&r.dpr===Number(byId('dpr').value)&&r.width===dimensions[0]&&r.height===dimensions[1]&&r.state===byId('state').value);
  byId('title').textContent=row.label;
  byId('counter').textContent=`${row.theme==='light'?'Chiaro':'Scuro'} · scala ${row.dpr*100} % · ${row.width} × ${row.height} pixel logici · ${row.width*row.dpr} × ${row.height*row.dpr} pixel del PNG`;
  byId('difference').textContent=row.difference;
  for(const side of ['widgets','quick']){
    const shot=row[side], frame=byId(side+'-picture');frame.replaceChildren();
    if(shot){const img=document.createElement('img');img.src=shot.image;img.alt=`${side==='widgets'?'Widgets':'Qt Quick'}: ${row.label}, ${row.theme}, scala ${row.dpr}`;frame.append(img);byId(side+'-meta').textContent=`${shot.name}.png · ${shot.pixels.join(' × ')} pixel · SHA-256 ${shot.sha256.slice(0,16)}…`;}
    else{const missing=document.createElement('p');missing.className='empty';missing.textContent='Cattura mancante: confronto incompleto';frame.append(missing);byId(side+'-meta').textContent='Nessuna immagine sostitutiva';}
  }
  const meta={...row};for(const side of ['widgets','quick']){if(meta[side]){meta[side]={...meta[side]};delete meta[side].image;}}
  byId('metadata').textContent=JSON.stringify(meta,null,2);
}
for(const id of ['theme','dpr','size','state'])byId(id).addEventListener('change',render);
for(const [id,step]of [['previous',-1],['next',1]])byId(id).addEventListener('click',()=>{const n=states.indexOf(byId('state').value);byId('state').value=states[(n+step+states.length)%states.length];render();});
byId('zoom').addEventListener('click',()=>{const on=document.querySelector('.pair').classList.toggle('native');byId('zoom').setAttribute('aria-pressed',String(on));byId('zoom').textContent=on?'Adatta alla pagina':'Vedi pixel originali';});
render();
</script></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--widgets', type=Path, default=Path('build/quick-foto/riferimento'))
    parser.add_argument('--quick', type=Path, default=Path('build/quick-foto/sistema'))
    parser.add_argument('--out', type=Path, default=Path('docs/quick/confronto/modellazione.html'))
    parser.add_argument('--allow-missing', action='store_true')
    args = parser.parse_args()
    rows, missing = collect(args.widgets, args.quick, args.allow_missing)
    complete = sum(row['widgets'] is not None and row['quick'] is not None for row in rows)
    substitutions = {
        '__DATE__': datetime.now().strftime('%d/%m/%Y %H:%M'),
        '__SUMMARY__': f'{complete} coppie complete su {len(rows)}.' + (' BOZZA INCOMPLETA.' if missing else ''),
        '__STATES__': ''.join(f'<option value="{key}">{html.escape(LABELS[key])}</option>' for key in STATES),
        '__MISSING__': ('<details open><summary>Catture mancanti</summary><pre>' + html.escape('\n'.join(missing))
                        + '</pre></details>') if missing else '',
        '__DATA__': json.dumps(rows, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c'),
        '__STATE_KEYS__': json.dumps(STATES),
    }
    document = DOCUMENT
    for key, value in substitutions.items():
        document = document.replace(key, value)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(document, encoding='utf-8')
    print(json.dumps(dict(output=str(args.out), pairs=complete, expected=len(rows), missing=len(missing),
                          bytes=args.out.stat().st_size)))


if __name__ == '__main__':
    main()
