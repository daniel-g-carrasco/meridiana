"""Reproducible gesture benchmark, trace analyzer and alternating source comparison."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys

from gesture_bench_core import GESTURES, UI_CASES, VERSION, load_rows, markdown, paired_comparison, scenario_key, trace_cases

ROOT = Path(__file__).resolve().parents[1]


def isolate_profile(setup):
    """Keep worker defaults and logs in the temporary home of the test helpers."""
    profile = Path(setup._TEST_HOME.name)
    for key, leaf in dict(APPDATA='roaming', LOCALAPPDATA='local', XDG_CONFIG_HOME='config',
                          XDG_DATA_HOME='data', XDG_STATE_HOME='state', XDG_CACHE_HOME='cache').items():
        os.environ[key] = str(profile/leaf)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('project', nargs='?', type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--source-root', type=Path, default=ROOT)
    p.add_argument('--compare-root', type=Path)
    p.add_argument('--analyze', type=Path, help='Read v1/v2 JSONL without importing Qt')
    p.add_argument('--scenarios', type=Path, help='JSON list of scenario overrides or {scenarios: [...]}')
    p.add_argument('--phase', default='plant', choices=('model', 'plant', 'production', 'consumption', 'economics', 'report'))
    p.add_argument('--views', nargs='+', default=['plan', '3d'], choices=('plan', '3d', 'split'))
    p.add_argument('--only', nargs='*', choices=GESTURES+UI_CASES)
    p.add_argument('--seed', type=int, default=1)
    p.add_argument('--seeds', type=int, nargs='+')
    p.add_argument('--repetitions', type=int, default=1)
    p.add_argument('--rate', type=int, choices=(60, 120, 240), default=120)
    p.add_argument('--refresh-hz', type=float)
    p.add_argument('--duration', type=float, default=1)
    p.add_argument('--tail-ms', type=int, default=800)
    p.add_argument('--size', type=int, nargs=2, default=[1434, 839])
    p.add_argument('--scale', type=float)
    p.add_argument('--theme', choices=('light', 'dark'), default='light')
    p.add_argument('--maps', action='store_true')
    p.add_argument('--fixture-tiles', action='store_true')
    p.add_argument('--live', action='store_true')
    p.add_argument('--allow-primary-screen', action='store_true', help='Explicit laptop use on Linux only; refused on Windows')
    p.add_argument('--platform', choices=('offscreen', 'windows', 'wayland', 'xcb'))
    p.add_argument('--api', choices=('d3d11', 'opengl', 'vulkan', 'metal'), default='d3d11' if os.name == 'nt' else 'opengl')
    p.add_argument('--backend', choices=('rhi', 'software'), default='rhi')
    p.add_argument('--visuals', action='store_true', help='Separate pixel pass, never counted in frame timings')
    p.add_argument('--profile', action='store_true')
    p.add_argument('--year', action='store_true', help='Compute a complete year from the recorded weather, never network')
    p.add_argument('--year-cache-from', type=Path, help='Read-only copy of a previous benchmark cache; fingerprint is validated by the app')
    p.add_argument('--qml-profile', action='store_true', help='Enable QML profiler connector on localhost:3768')
    p.add_argument('--qsg', action='store_true', help='Native QSG GUI/GPU timing fallback (separate diagnostic pass)')
    p.add_argument('--modules', type=int, default=100)
    p.add_argument('--threshold', type=float, default=10)
    p.add_argument('--label', default='trial')
    p.add_argument('--render-control', action='store_true', help='D3D11 plan render target (legacy diagnostic)')
    p.add_argument('--layer-samples', type=int)
    p.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    return p


def scenarios(args):
    overrides = [{}]
    if args.scenarios:
        content = json.loads(args.scenarios.read_text(encoding='utf-8-sig'))
        overrides = content['scenarios'] if isinstance(content, dict) else content
        if not isinstance(overrides, list) or not overrides:
            raise ValueError('scenarios must be a nonempty list')
    result = []
    for override in overrides:
        unknown = set(override)-set(vars(args))
        if unknown:
            raise ValueError(f'unknown scenario fields: {sorted(unknown)}')
        base = vars(args) | override
        for view, seed, repetition in itertools.product(base['views'], base['seeds'] or [base['seed']],
                                                       range(base['repetitions'])):
            result.append(base | dict(view=view, seed=seed, repetition=repetition))
    return result


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\r\n') as stream:
        stream.write(value)


def compare(args):
    """AB/BA paired passes, fresh process and profile for every source and seed."""
    runs = []
    seeds = args.seeds or [args.seed]
    for rep in range(args.repetitions):
        for index, seed in enumerate(seeds):
            order = [('base', args.compare_root), ('trial', args.source_root)]
            if (index+rep) % 2:
                order.reverse()
            for label, source in order:
                output = args.out.with_name(f'{args.out.stem}-{rep}-{seed}-{label}.json')
                command = [sys.executable, str(Path(__file__).resolve()), '--out', str(output),
                           '--source-root', str(source), '--label', label, '--seed', str(seed), '--worker']
                if args.project:
                    command.append(str(args.project.resolve()))
                # Pass explicit values, not inherited Qt state, so both versions get identical inputs.
                for key in ('phase', 'rate', 'duration', 'tail_ms', 'theme', 'api', 'backend', 'modules'):
                    command.extend(['--'+key.replace('_', '-'), str(getattr(args, key))])
                command.extend(['--views', *args.views, '--size', *map(str, args.size)])
                for key in ('refresh_hz', 'scale', 'platform', 'scenarios', 'year_cache_from'):
                    if getattr(args, key) is not None:
                        command.extend(['--'+key.replace('_', '-'), str(getattr(args, key))])
                for key in ('maps', 'fixture_tiles', 'live', 'visuals', 'profile', 'render_control', 'year', 'qml_profile', 'qsg', 'allow_primary_screen'):
                    if getattr(args, key):
                        command.append('--'+key.replace('_', '-'))
                if args.only:
                    command.extend(['--only', *args.only])
                log = output.with_suffix('.log')
                failure = None
                with log.open('x', encoding='utf-8') as stream:
                    try:
                        completed = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=600,
                                                   env=dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8'))
                        if completed.returncode:
                            failure = f'worker exit {completed.returncode}; see {log.name}'
                    except subprocess.TimeoutExpired:
                        failure = f'worker exceeded 600 seconds; see {log.name}'
                if failure:
                    runs.append(dict(label=label, seed=seed, repetition=rep, file=str(output), error=failure))
                    print(f'{label} seed={seed}: {failure}', flush=True)
                    continue
                runs.append(dict(label=label, seed=seed, repetition=rep, file=str(output),
                                 result=json.loads(output.read_text(encoding='utf-8'))))
                print(f'{label} seed={seed} complete', flush=True)
    groups = {}
    for run in runs:
        if 'result' not in run:
            continue
        for case in run['result']['cases']:
            # Case key excludes run label and seed, pairing is explicit below.
            key = scenario_key(case, dict(duration_s=args.duration, tail_ms=args.tail_ms))
            pair = (run['repetition'], run['seed'], case.get('seed'), case.get('repetition'))
            groups.setdefault(key, {}).setdefault(pair, {})[run['label']] = case
    comparisons = []
    for key, pairs in groups.items():
        for metric, field in [('cadence', 'median_ms'), ('cadence', 'p95_ms'), ('handle', 'p95_ms'),
                              ('gpu', 'p95_ms'), ('latency', 'p95_ms')]:
            valid = [p for p in pairs.values() if set(p) == {'base', 'trial'} and
                     all(p[l]['analysis']['valid_motion'] and p[l]['analysis'][metric][field] is not None and p[l]['analysis'][metric][field] > 0
                         for l in ('base', 'trial'))]
            if valid:
                comparisons.append(dict(phase=key[0], view=key[1], gesture=key[2], project_sha256=key[3],
                    scenario=json.loads(key[4]), metric=metric+'.'+field,
                    **paired_comparison([p['base']['analysis'][metric][field] for p in valid],
                                        [p['trial']['analysis'][metric][field] for p in valid], threshold=args.threshold)))
    return dict(version=VERSION, runs=[{k: v for k, v in r.items() if k != 'result'} for r in runs],
                comparisons=comparisons, cases=[])


def matrix(args):
    content = json.loads(args.scenarios.read_text(encoding='utf-8-sig'))
    overrides = content['scenarios'] if isinstance(content, dict) else content
    report = dict(version=VERSION, cases=[], environment={'isolated_scenarios': True}, runs=[])
    for index, override in enumerate(overrides):
        out = args.out.with_name(f'{args.out.stem}-scenario{index}.json')
        values = vars(args) | override | dict(out=out, worker=True, scenarios=None)
        command = [sys.executable, str(Path(__file__).resolve())]
        for key, value in values.items():
            if value is None or value is False or key == 'compare_root':
                continue
            if key == 'project':
                command.append(str(value))
            elif value is True:
                command.append('--'+key.replace('_', '-'))
            elif isinstance(value, list):
                command.extend(['--'+key.replace('_', '-'), *map(str, value)])
            else:
                command.extend(['--'+key.replace('_', '-'), str(value)])
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=600,
                                       env=dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8'))
        except subprocess.TimeoutExpired:
            completed = None
        log = out.with_suffix('.log')
        write_new(log, completed.stdout+completed.stderr if completed else 'worker exceeded 600 seconds')
        if completed is None or completed.returncode:
            report['runs'].append(dict(file=out.name, error='worker failed; see '+log.name))
            print(f'scenario {index}: failed; see {log.name}', flush=True)
            continue
        run = json.loads(out.read_text(encoding='utf-8'))
        report['cases'].extend(run['cases'])
        report['runs'].append(dict(file=out.name, environment=run['environment']))
    return report


def main(argv=None):
    args = parser().parse_args(argv)
    outputs = [args.out, args.out.with_suffix('.md')]
    if any(p.exists() for p in outputs):
        raise FileExistsError('output exists: choose a new revision')
    if args.repetitions < 1 or args.duration <= 0 or args.tail_ms < 0 or any(n <= 0 for n in args.size):
        raise ValueError('invalid repetition, duration, tail or size')
    if args.analyze:
        rows = load_rows(args.analyze)
        report = dict(version=VERSION, cases=trace_cases(rows, args.refresh_hz))
    elif args.compare_root:
        report = compare(args)
    elif args.scenarios:
        scenarios(args)  # validate unknown fields before starting any window
        report = matrix(args)
    else:
        # Imported lazily: analysis and --help work without Qt, numpy, or Meridiana installed.
        if args.project and not args.project.is_file():
            raise FileNotFoundError(args.project)
        import faulthandler
        faulthandler.dump_traceback_later(90, repeat=True)
        from gesture_bench_qt import run
        try:
            report = run(args, scenarios(args))
        finally:
            faulthandler.cancel_dump_traceback_later()
    write_new(args.out, json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))
    write_new(args.out.with_suffix('.md'), markdown(report))
    print(str(args.out), flush=True)
    return report


def legacy(kind):
    argv = sys.argv[1:]
    if kind == 'zoom' and '--only' not in argv:
        argv += ['--only', 'wheel']
    return main(argv)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


if __name__ == '__main__':
    main()
