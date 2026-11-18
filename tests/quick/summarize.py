"""Build the Italian evidence appendix from recorded measurements, without Qt."""
import hashlib
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT/'docs/prestazioni/2026-11-04/quick'


def number(value, digits=3):
    return f'{value:.{digits}f}'.replace('.', ',')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def read_log(path):
    raw = path.read_bytes()
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')


def main():
    final = read(DATA/'offscreen-03-final.json')
    mismatches = [name for name, digest in final['source_sha256'].items()
                  if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest]
    harness_matches = hashlib.sha256((ROOT/'tools/quick_fluidity.py').read_bytes()).hexdigest() == final['harness_sha256']
    lines = [
        '# R389: registro delle misure e delle prove', '',
        '04/11/2026. Generato con `python -m quick.summarize` dai JSON conservati nel repository.', '',
        '**Tutte le serie sono offscreen. I tempi del giro eventi includono attese imposte e renderer software: '
        'non misurano fluidità GPU. Il lavoro Python al confine e il numero di callback sono la misura utile qui.**', '',
        '## Serie Shapes 03, prima dell’alternativa Canvas', '',
        f"[V] `offscreen-03-final.json`, Qt {final['qt']}, {final['platform']}, {final['graphics_api']}, "
        f"scala 1, render loop basic. Anno pronto in {number(final['opened']['year_ms']/1000, 2)} s; "
        f"worker {number(final['metrics']['worker_ms']/1000, 2)} s; trasferimento scena "
        f"{number(final['metrics']['scene_transfer_ms'])} ms.", '',
        '[V] 778 moduli, 787 delegati, 8.760 ore, 366 punti giornalieri, 14 verifiche, nessun avviso QML. '
        'Ogni riga contiene gli stati prima/dopo e una verifica del gesto. Nei quattro gesti concorrenti '
        'il calcolo era attivo prima e dopo.', '',
        f"[V] Hash dei sorgenti attuali: {'coincidono' if not mismatches else 'differiscono: '+str(mismatches)}; "
        f"hash misuratore: {'coincide' if harness_matches else 'differisce'}. "
        'Il commit registrato è la base del worktree, non include i nuovi file non committati.', '',
        '| Gesto | Passi | Giro eventi offscreen, ms/passo | Python CPU, ms/passo | Confine Python trascorso, ms/passo | Callback/passo | Peggiore intervallo battito, ms |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ]
    for row in final['results']:
        lines.append(f"| {row['gesture']} | {row['steps']} | {number(row['action_ms_per_step'])} | "
                     f"{number(row['python_boundary_cpu_ms_per_step'])} | "
                     f"{number(row['python_boundary_wall_ms_per_step'])} | "
                     f"{number(row['qml_python_calls_per_step'], 2)} | {number(row['worst_ms'], 2)} |")
    typed = next(r for r in final['results'] if r['gesture'].startswith('a field'))
    lines += ['', '[V] La digitazione comprende quattro caratteri e Invio, non dodici caratteri. '
              'Il costo per passo divide anche la conferma per quattro. Il costo Python comprende '
              'le chiamate native e le emissioni sincrone; il profilatore stesso aggiunge costo. '
              'I passaggi di fase misurano il comando e la quiete del battito Python, non il completamento '
              'visivo della dissolvenza da 180 ms.', '',
              'Callback effettivi della digitazione: `' + json.dumps(typed['qml_python_calls'], ensure_ascii=False) + '`.', '',
              'Segnali emessi: `' + json.dumps(typed['python_signals'], ensure_ascii=False) + '`.', '',
              '## Grafico, confronto A/B al 200 %', '',
              '[V] `offscreen-02-200.json`, testo grande. Tre coppie alternate sullo stesso anno e sugli stessi '
              '366 punti. Le mediane sotto sono su sei gesti per versione: tre allargamenti e tre ritorni. '
              'Serie precedente alla revisione del bridge; non è una misura del sorgente finale.', '',
              '| Versione | Gesti | Mediana ms/passo offscreen | Minimo | Massimo | Callback Python |',
              '|---|---:|---:|---:|---:|---:|']
    second = read(DATA/'offscreen-02-200.json')
    for mode in ('resampled', 'retained'):
        rows = [r for r in second['results'] if r['gesture'].startswith('production-'+mode)]
        values = [r['action_ms_per_step'] for r in rows]
        lines.append(f"| {mode} | {len(rows)} | {number(statistics.median(values))} | "
                     f"{number(min(values))} | {number(max(values))} | "
                     f"{sum(sum(r['qml_python_calls'].values()) for r in rows)} |")
    lines += ['', '[V] La versione conservata non migliora questa serie software. Non si attribuisce '
              'il risultato al renderer GPU, che non è stato eseguito. Tutte le durate individuali '
              'e i controlli sui punti sono nel JSON.', '', '## Serie e immagini conservate', '',
              '| Serie | Scopo | Worker, s | Avvisi QML |', '|---|---|---:|---:|']
    for stem, purpose in [('offscreen-01', 'Prima implementazione completa, prima della revisione'),
                          ('offscreen-02-200', 'Scala 200 %, testo grande, A/B grafici, prima della revisione'),
                          ('offscreen-03-final', 'Bridge dopo la revisione, scala 100 %')]:
        doc = read(DATA/(stem+'.json'))
        assert all(r['verified'] and r['after']['modules'] == 778 for r in doc['results'])
        assert doc['project_sha256'] == final['project_sha256']
        lines.append(f"| {stem}.json | {purpose} | {number(doc['metrics']['worker_ms']/1000, 2)} | {len(doc['qml_warnings'])} |")
    lines += ['', '[V] Progetto originale, SHA-256: `' + final['project_sha256'] + '`. '
              'Ogni misuratore verifica che il file abbia lo stesso hash al termine.', '',
              '[V] Le immagini `*-model.png` e `*-production.png` mostrano la pianta completa e la curva annuale. '
              'Le immagini `*-narrow.png` documentano anche un difetto reale della cattura software: '
              'residui di moduli fuori dalla pianta dopo la lunga sequenza di ridimensionamenti. '
              'Non è nascosto né dichiarato risolto: il nuovo test della fixture riproduce 5.098 pixel '
              'fuori riquadro al 200 %. Le alternative provate sono state scartate; dettagli nell’esito. '
              '[NV] Verifica equivalente con backend GPU.', '',
              '## Comandi di verifica', '',
              'Ambiente: Python della `.venv` autorizzata, `PYTHONUTF8=1`, `PYTHONPATH=tests;src`, '
              '`QT_QPA_PLATFORM=offscreen`, PySide6 nel `PATH`. Nessun input nativo o finestra sul desktop. '
              '`quick-200` aggiunge `QT_SCALE_FACTOR=2`; gli altri gruppi usano scala 1.', '',
              'Comando per gruppo: `python -W default -m unittest discover -s tests/<gruppo> -t tests`.', '',
              '| Gruppo | Exit code | Secondi | Esito riportato da unittest |', '|---|---:|---:|---|']
    records = read(DATA/'validation.json')
    if (DATA/'validation-extra.json').exists():
        records += read(DATA/'validation-extra.json')
    if (DATA/'validation-final.json').exists():
        records += read(DATA/'validation-final.json')
    if (DATA/'validation-release.json').exists():
        records += read(DATA/'validation-release.json')
    for record in records:
        log = read_log(ROOT/record['log'])
        summary = re.findall(r'Ran .*? tests? in .*?s|^OK[^\r\n]*|^FAILED[^\r\n]*', log, re.M)
        lines.append(f"| {record['group']} | {record['exit_code']} | {number(record['seconds'], 2)} | "
                     + ('; '.join(summary) or 'Nessun riepilogo unittest: vedere log e codice di uscita') + ' |')
    canvas_path = DATA/'offscreen-04-canvas.json'
    if canvas_path.exists():
        canvas = read(canvas_path)
        changed = [name for name, digest in canvas['source_sha256'].items()
                   if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest]
        harness_changed = hashlib.sha256((ROOT/'tools/quick_fluidity.py').read_bytes()).hexdigest() != canvas['harness_sha256']
        extra = ['## Alternativa Canvas, serie 04', '',
                 '[V] Stessi 778 moduli e anno vero; 787 primitive percorse nel paint, non 787 delegati QML. '
                 'La sequenza `base` copre pianta, bordi, finestra, fasi e digitazione. Il grafico è popolato '
                 'ma non si ripete il suo A/B. La serie è stata eseguita mentre proseguivano le suite esistenti: '
                 'il carico della macchina non è controllato, quindi niente rapporto di velocità tra renderer.', '',
                 f"[V] Worker {number(canvas['metrics']['worker_ms']/1000, 2)} s. "
                 f"Sorgenti diversi rispetto alla misura: {changed or 'nessuno'}; "
                 f"misuratore diverso: {'sì' if harness_changed else 'no'}.", '',
                 '| Gesto Canvas | Passi | Giro eventi offscreen, ms/passo | Confine Python, ms/passo | Callback/passo |',
                 '|---|---:|---:|---:|---:|']
        for row in canvas['results']:
            assert row['verified'] and row['after']['painted_modules'] == 778
            extra.append(f"| {row['gesture']} | {row['steps']} | {number(row['action_ms_per_step'])} | "
                         f"{number(row['python_boundary_wall_ms_per_step'])} | {number(row['qml_python_calls_per_step'], 2)} |")
        extra += ['', '[V] Anche Canvas riproduce il test dei residui al 200 %; non è una correzione dichiarata. '
                  'La suite alternativa ha 25 test: scala 1 tutti passati, scala 2 un fallimento. '
                  'Log `validation-quick-canvas-1.log` e `validation-quick-canvas-2.log`.', '']
        at = lines.index('## Comandi di verifica')
        lines[at:at] = extra
    lines += ['', 'Le prime righe Quick si riferiscono a 21 test; le righe `quick-delivery` sono la consegna '
              'con 25 test e includono il nuovo controllo dei residui. Le righe `quick-current` provano '
              'il renderer esplicito nel log. Le righe `quick-release` sono l’ultima verifica locale '
              'con 26 test, dopo la correzione dell’avvio: il nome del gruppo non indica una release. '
              'Il fallimento al 200 % resta visibile.', '',
              'I log completi sono in `build/quick/validation-*.log` nel worktree e le copie di consegna '
              'in `docs/prestazioni/2026-11-04/quick/logs/`. '
              'Le limitazioni e gli eventuali fallimenti sono discussi nell’esito principale.', '']
    (ROOT/'docs/revisioni/quick-prova-misure.md').write_text('\n'.join(lines), encoding='utf-8')
    print('Written quick-prova-misure.md; source mismatches:', mismatches)


if __name__ == '__main__':
    main()
