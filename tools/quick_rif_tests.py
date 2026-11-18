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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true')
    args = parser.parse_args()
    env = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONPATH': os.pathsep.join([str(ROOT / 'tests'), str(ROOT / 'src'), str(ROOT)])}
    failures = []
    for name, command in groups():
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
