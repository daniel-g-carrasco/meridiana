"""Replay every result tab and viewport, on both applications, at both scales."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from meridiana import i18n
from meridiana.quick.backend.charts_data import _spec


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('fixture', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--project', required=True)
    parser.add_argument('--scales', type=int, nargs='+', default=[1, 2])
    args = parser.parse_args()
    i18n.setup('it')
    steps = []
    for phase, key in (('plant', 'Ctrl+2'), ('production', 'Ctrl+3'), ('consumption', 'Ctrl+4'), ('economics', 'Ctrl+5')):
        steps.append(dict(action='key', key=key, wait=1500, expect=dict(phase=phase)))
        for size in ([1366, 900], [1920, 1080], [1600, 960]):
            steps.append(dict(action='resize', size=size, wait=650))
        if phase != 'plant':
            for label, _members in _spec(phase)[2][1:]:
                steps.append(dict(action='click', target=label, wait=800))
            steps.append(dict(action='click', target=i18n._('How it is computed'), wait=1000))
    journey = args.output / 'journey.json'
    args.output.mkdir(parents=True, exist_ok=False)
    journey.write_text(json.dumps(dict(size=[1600, 960], steps=steps), ensure_ascii=False, indent=2), encoding='utf8')
    for scale in args.scales:
        for theme in ('light', 'dark'):
            env = dict(os.environ, QT_SCALE_FACTOR=str(scale), MERIDIANA_PHOTO_YEAR=str(args.fixture.resolve()))
            subprocess.run([sys.executable, '-m', 'quick.grafici.run_pilot', str(journey), '--project', args.project,
                            '--theme', theme, '--out', str(args.output / f'{theme}-s{scale}')], env=env, check=True)


if __name__ == '__main__':
    main()
