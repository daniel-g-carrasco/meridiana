"""Verify current controls against a frozen shell snapshot without changing Git."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--theme', choices=('light', 'dark'))
    parser.add_argument('--scale', type=int, choices=(1, 2))
    parser.add_argument('--label', default='pilot')
    args = parser.parse_args()
    root = Path.cwd()
    base = root / 'build/quick-foto/r13-controlli'
    revision = subprocess.check_output(['git', 'rev-parse', 'r13-shell'], text=True).strip()
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    snapshot = base / ('integration-' + revision[:12] + '-' + stamp)
    snapshot.mkdir(exist_ok=False)
    archive = snapshot.with_suffix('.tar')
    with archive.open('wb') as stream:
        subprocess.run(['git', 'archive', revision, 'src', 'data', 'po', 'tests', 'tools', 'pyproject.toml'], stdout=stream, check=True)
    with tarfile.open(archive) as bundle:
        bundle.extractall(snapshot, filter='data')
    # File's Widgets page is hidden before its departing picture disappears.
    # Wait for that real animation, not just fileOpen=False, before photographing.
    pilot = snapshot / 'tools/quick_pilot.py'
    source = pilot.read_text(encoding='utf-8')
    marker = "                pump(step.get('wait', 400))\n"
    assert source.count(marker) == 1
    source = source.replace(marker, marker + '''                if args.engine == 'widgets':
                    for attempt in range(500):
                        page = window.file_page
                        if page.entrance is None and page.exit is None:
                            break
                        pump(20)
                    else:
                        raise AssertionError('File animation did not settle')
                    pump(32)
''')
    pilot.write_text(source, encoding='utf-8')
    paths = ['src/meridiana/quick/qml/Meridiana/Controls',
             'src/meridiana/quick/qml/Meridiana/Theme',
             'src/meridiana/quick/backend/controls.py',
             'src/meridiana/quick/backend/tokens.py']
    hashes = {}
    for name in paths:
        source, target = root / name, snapshot / name
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)
        for file in source.rglob('*') if source.is_dir() else [source]:
            if file.is_file():
                hashes[str(file.relative_to(root))] = hashlib.sha256(file.read_bytes()).hexdigest()
    (base / f'integration-{stamp}.json').write_text(json.dumps(dict(
        revision=revision, overlay=hashes,
        pilotAdapter='Wait for the Widgets File entrance/exit veil before capture',
        pilotSha256=hashlib.sha256(pilot.read_bytes()).hexdigest()), indent=2), encoding='utf-8')
    env = dict(os.environ, PYTHONPATH=str(snapshot / 'tests') + ';' + str(snapshot / 'src'), PYTHONUTF8='1')
    subprocess.run([sys.executable, 'tools/compile_po.py', '--python'], cwd=snapshot, env=env, check=True)
    journey = root / 'tests/quick/percorsi/controlli.json'
    for scale in (args.scale,) if args.scale else (1, 2):
        for theme in (args.theme,) if args.theme else ('light', 'dark'):
            output = base / f'{args.label}-{theme}-s{scale}'
            subprocess.run([sys.executable, str(snapshot / 'tools/quick_pilot.py'), str(journey),
                            '--engine', 'both', '--theme', theme, '--out', str(output),
                            '--project', r'C:\Users\Grasso\dev\meridiana-prove\Prova capannone Rho.meridiana'],
                           cwd=snapshot, env=dict(env, QT_SCALE_FACTOR=str(scale)), check=True)


if __name__ == '__main__':
    main()
