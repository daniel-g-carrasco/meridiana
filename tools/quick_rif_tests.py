"""Run every Quick subgroup in a fresh process, including the prototype tests.

This automatically includes sistema, pianta, grafici and vista3d when merged.
The root prototype modules run individually: discovering tests/quick would run
the parity subgroup twice and mix QApplication/QGuiApplication lifetimes.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
# seconds each subgroup took on Linux offscreen (WSL, 21/11/2026): the CI splits them in shards of about the same
# length (--shard); a subgroup not listed weighs DEFAULT_WEIGHT, and the list needs no care to stay right
WEIGHTS = {'quick/shell': 1200, 'quick/sistema': 880, 'quick/pagine': 440, 'quick/meridio': 355, 'quick/pianta': 320,
           'quick/vista3d': 300, 'quick/impianto': 250, 'quick/controlli': 85, 'quick/grafici': 55,
           'quick/proprieta': 50}
DEFAULT_WEIGHT = 10


def shard(result, index, count):
    """The subgroups of shard `index` of `count`: the heaviest first, each to the lightest shard so far; the same
    split on every runner, so that together the shards run every subgroup once."""
    loads, mine = [0] * count, []
    for position, (name, command) in sorted(enumerate(result), key=lambda e: (-WEIGHTS.get(e[1][0], DEFAULT_WEIGHT), e[0])):
        lightest = loads.index(min(loads))
        loads[lightest] += WEIGHTS.get(name, DEFAULT_WEIGHT)
        if lightest == index:
            mine.append((position, (name, command)))
    return [entry for _, entry in sorted(mine)]


def groups(root=ROOT):
    folder = root / 'tests/quick'
    result = [(f'quick.{path.stem}', [sys.executable, '-m', 'unittest', f'quick.{path.stem}'])
              for path in sorted(folder.glob('test_*.py'))]
    for path in sorted(folder.iterdir()):
        if path.is_dir() and path.name != '__pycache__' and list(path.rglob('test_*.py')):
            if not (path / '__init__.py').is_file():
                raise ValueError(f'Quick subgroup is not an importable package: {path}')
            result.append((f'quick/{path.name}', [sys.executable, 'tools/run_tests.py', f'tests/quick/{path.name}']))
    if not result:
        raise ValueError('No Quick tests found')
    return result


def timed_modules(root=ROOT):
    """The modules of tests/quick/aiuti/tempi.py TIMED, read from the file: importing it would import the Quick's
    package, and its QApplication, in this process."""
    import ast
    tree = ast.parse((root / 'tests/quick/aiuti/tempi.py').read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', '') == 'TIMED' for t in node.targets):
            return list(ast.literal_eval(node.value))
    raise ValueError('TIMED not found in tests/quick/aiuti/tempi.py')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--shard', metavar='I/N', help='run only shard I (from 0) of N, of about the same length')
    parser.add_argument('--timed', action='store_true',
                        help='run only the modules with a timed test (tests/quick/aiuti/tempi.py), with their thresholds')
    args = parser.parse_args()
    env = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONPATH': os.pathsep.join([str(ROOT / 'tests'), str(ROOT / 'src'), str(ROOT)])}
    failures = []
    chosen = groups()
    if args.timed:
        env.pop('MERIDIANA_TIMED', None)
        chosen = [(name, [sys.executable, '-m', 'unittest', name]) for name in timed_modules()]
    elif args.shard:
        index, count = (int(part) for part in args.shard.split('/'))
        chosen = shard(chosen, index, count)
    for name, command in chosen:
        print(f'::group::{name}', flush=True)
        if args.list:
            print(' '.join(command), flush=True)
        else:
            code = subprocess.run(command, cwd=ROOT, env=env, check=False).returncode
            if code:
                failures.append((name, code))
        print('::endgroup::', flush=True)
    if failures:
        print('Failed Quick subgroups: ' + repr(failures), file=sys.stderr)
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
