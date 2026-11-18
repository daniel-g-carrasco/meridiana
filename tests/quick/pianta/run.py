"""Run the plan tests in isolated Qt processes, including Widgets parity modules."""
import os
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]


def main():
    folder = ROOT / 'build/r13-tests'
    folder.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(ROOT/'tests'), str(ROOT/'src')]),
               PYTHONUTF8='1', QSG_RENDER_LOOP='threaded')
    failed = []
    results = []
    for test in sorted(Path(__file__).parent.glob('test_*.py')):
        if test.stem.endswith('_mapping'):
            continue  # Evidence tables, not unittest modules.
        with (folder/(test.stem+'.log')).open('w', encoding='utf-8') as log:
            try:
                result = subprocess.run([sys.executable, '-m', 'unittest', 'quick.pianta.'+test.stem],
                                        cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
                code = result.returncode
            except subprocess.TimeoutExpired:
                code = 'timeout'
        print(test.stem, code, flush=True)
        results.append({'module': test.stem, 'exit': code})
        if code:
            failed.append(test.stem)
    # Keep the opt-in source editor isolated from the other engines in its module.
    with (folder/'source_window.log').open('w', encoding='utf-8') as log:
        result = subprocess.run([sys.executable, '-m', 'unittest', 'quick.pianta.test_sources.SourceWindowTests'],
                                cwd=ROOT, env=dict(env, MERIDIANA_QUICK_SOURCE_WINDOW='1'),
                                stdout=log, stderr=subprocess.STDOUT, timeout=180)
    results.append({'module': 'source_window', 'exit': result.returncode})
    if result.returncode:
        failed.append('source_window')
    (folder/'result.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print('Failed:', failed, flush=True)
    return bool(failed)


if __name__ == '__main__':
    raise SystemExit(main())
