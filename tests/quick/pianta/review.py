"""Capture paired plan journeys on native windows, with separate isolated processes."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
PROJECT = Path.home()/'dev/meridiana-prove/Prova capannone Rho.meridiana'


def main():
    original = hashlib.sha256(PROJECT.read_bytes()).hexdigest()
    failures = []
    for theme, scale, journey, large in (
            ('light', '1', 'pianta', False), ('dark', '2', 'pianta', False),
            ('dark', '1', 'pianta-aspetto', False), ('light', '2', 'pianta-aspetto', True)):
        label = theme+scale+('-large' if large else '')
        out = ROOT/'build/r13-review'/label
        out.mkdir(parents=True, exist_ok=True)
        for engine in (('quick',) if '--quick-only' in sys.argv else ('widgets', 'quick')):
            command = [sys.executable, str(Path(__file__).with_name('pilot.py')),
                       f'tests/quick/percorsi/{journey}.json', '--engine', engine,
                       '--project', str(PROJECT), '--theme', theme, '--out', str(out)]
            if large:
                command.append('--large-text')
            env = dict(os.environ, PYTHONUTF8='1', PYTHONPATH='tests;src',
                       QT_SCALE_FACTOR=scale, QSG_RENDER_LOOP='threaded')
            with (out/(engine+'.log')).open('w', encoding='utf-8') as log:
                result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=420)
            print(label, engine, result.returncode, flush=True)
            if result.returncode:
                failures.append((label, engine))
    unchanged = original == hashlib.sha256(PROJECT.read_bytes()).hexdigest()
    assert unchanged, 'The reference project must remain unchanged'
    (ROOT/'build/r13-review/result.json').write_text(json.dumps(
        dict(failures=failures, project_sha256=original, project_unchanged=unchanged), indent=2), encoding='utf-8')
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
