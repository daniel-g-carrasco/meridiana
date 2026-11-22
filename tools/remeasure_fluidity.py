"""Repeat the UI audit with the gesture recorder on Windows or inside a Wayland Flatpak."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from gesture_bench import write_new
from gesture_bench_core import UI_CASES, analyze, load_rows

CAUSES = {
    'phases': 'creazione/impaginazione delle pagine e dissolvenza; verificare sync e campioni GUI',
    'cards': 'ricomposizione delle schede e viste; confrontare sync, render e GPU',
    'report-scroll': 'composizione delle pagine e caricamento delle immagini della relazione',
    'table-scroll': 'creazione e impaginazione dei delegati della tabella',
    'resize': 'ricalcolo delle dimensioni, impaginazione e nuovo bersaglio grafico',
    'resize-meridio': 'impaginazione e ridisegno del personaggio durante il resize',
    'zoom-measures': 'scena 3D e proiezione delle annotazioni, eventuale risposta differita',
    'meridio': 'ridisegno del personaggio e della conversazione durante il trascinamento',
}


def verdict(analysis):
    cadence = analysis['cadence']
    count = cadence['count']
    if not count or not analysis['valid_motion']:
        return 'non valutabile'
    latency = analysis['latency']['p95_ms']
    return 'regge' if (cadence['p95_ms'] <= cadence['period_ms']*1.5 and
                       cadence['over_2_periods']/count <= .01 and latency is not None and
                       latency <= cadence['period_ms']*3) else 'non regge'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('project', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--live', action='store_true')
    p.add_argument('--allow-primary-screen', action='store_true', help='Linux laptop only')
    p.add_argument('--api', default='d3d11' if os.name == 'nt' else 'opengl')
    p.add_argument('--seed', type=int, default=703)
    p.add_argument('--only', nargs='+', choices=UI_CASES, default=list(UI_CASES))
    p.add_argument('--duration', type=float, default=2)
    p.add_argument('--visuals', action='store_true')
    p.add_argument('--year-cache-from', type=Path)
    args = p.parse_args()
    if args.out.exists() or args.out.with_suffix('.md').exists():
        raise FileExistsError(args.out)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    cases = []
    for kind in args.only:
        out = args.out.with_name(args.out.stem+'-'+kind+'.json')
        command = [sys.executable, str(Path(__file__).with_name('gesture_bench.py')), str(args.project.resolve()),
                   '--out', str(out), '--phase', 'plant', '--views', '3d' if kind == 'zoom-measures' else 'plan',
                   '--only', kind, '--seed', str(args.seed), '--year', '--profile', '--qsg', '--api', args.api,
                   '--duration', str(args.duration), '--tail-ms', '1000']
        if args.live:
            command.append('--live')
        if args.allow_primary_screen:
            command.append('--allow-primary-screen')
        if args.visuals:
            command.append('--visuals')
        if args.year_cache_from:
            command.extend(['--year-cache-from', str(args.year_cache_from)])
        with out.with_suffix('.log').open('x', encoding='utf-8') as stream:
            try:
                result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=600,
                                        env=dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8'))
            except subprocess.TimeoutExpired:
                result = None
        if result is None or result.returncode:
            cases.append(dict(gesture=kind, error='benchmark failed; see '+out.with_suffix('.log').name))
        else:
            report = json.loads(out.read_text(encoding='utf-8'))
            for case in report['cases']:
                rows = load_rows(out.parent/case['raw'])
                budgets = {str(hz): analyze(rows, hz) for hz in (60, 120)}
                cases.append(dict(gesture=kind, file=out.name, environment=report['environment'],
                                  budgets=budgets, pixels=case['pixel_pass']))
        print(kind+': complete', flush=True)
    write_new(args.out, json.dumps(dict(version=2, cases=cases), indent=2))
    lines = ['# Rimisura della fluidita', '',
             '[V] Swap Qt e input sintetici sulla finestra completa. Il budget a 120 Hz e ricalcolato',
             'sugli stessi intervalli: se lo schermo e a 60 Hz non e una prova fisica a 120 Hz.', '',
             '| Scenario | Hz | Esito | Intervalli | Mancanti stimati | >1,5T / >2T | p95 / max ms | Ritardo p95 ms | Cambi dopo il gesto |',
             '|---|---:|---|---:|---:|---|---|---:|---:|']
    def fmt(value):
        return 'n/d' if value is None else f'{value:.2f}'
    for case in cases:
        if 'error' in case:
            lines.append(f"| {case['gesture']} | | non valutabile | | | | | | |")
            continue
        for hz, a in case['budgets'].items():
            c = a['cadence']
            lines.append(f"| {case['gesture']} | {hz} | {verdict(a)} | {c['count']} | {c['missed_frames']} | "
                         f"{c['over_1_5_periods']} / {c['over_2_periods']} | {fmt(c['p95_ms'])} / {fmt(c['worst_ms'])} | "
                         f"{fmt(a['latency']['p95_ms'])} | {a['settlement']['camera_changes']} |")
    lines += ['', '[I] Cause da verificare con un profilo nativo, senza applicare correzioni:']
    for case in cases:
        kind = case['gesture']
        if 'error' in case:
            lines += ['- '+kind+': '+case['error']]
        elif any(verdict(a) != 'regge' for a in case['budgets'].values()):
            lines += ['- '+kind+': '+CAUSES[kind]+'.']
    lines += ['', 'Gli stati che cambiano durante una dissolvenza o un trascinamento sono intenzionali;',
              'i conteggi non li trasformano automaticamente in salti errati. I pixel sono una passata separata.',
              'Le latenze non riconosciute restano nei dati, senza attribuire loro zero millisecondi.', '']
    write_new(args.out.with_suffix('.md'), '\n'.join(lines))


if __name__ == '__main__':
    main()
