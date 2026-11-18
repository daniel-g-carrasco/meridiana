"""Check the complete crop matrix and the recorded integrated journeys."""
import json
from pathlib import Path

from PIL import Image, ImageChops

from quick.controlli.capture_pairs import CASES, STATE_CASES, STATES


def main():
    folder = Path('docs/quick/confronto/controlli')
    rows = [row for file in folder.glob('manifest-*.json') for row in json.loads(file.read_text(encoding='utf-8'))]
    indexed = {(r['control'], r['theme'], r['scale'], r['state'], r['large']) for r in rows}
    expected = {(name, theme, scale, state, large)
                for name in CASES for theme in ('light', 'dark') for scale in (1, 2)
                for large in (False, True)
                for state in (('normal',) if large else STATE_CASES.get(name, STATES))}
    assert expected <= indexed, sorted(expected - indexed)
    assert len(indexed) == len(rows), 'Duplicate capture keys'
    for row in rows:
        assert row['api'] == 'GraphicsApi.Direct3D11', row
        for engine in ('widgets', 'quick'):
            with Image.open(folder / f'{row["stem"]}-{engine}.png') as image:
                assert image.size == (round(row['width'] * row['scale']), round(row['height'] * row['scale'])), row
        if row['control'].startswith('fades-'):
            with Image.open(folder / f'{row["stem"]}-widgets.png') as native, Image.open(folder / f'{row["stem"]}-quick.png') as quick:
                difference = ImageChops.difference(native.convert('RGB'), quick.convert('RGB'))
                assert max(channel[1] for channel in difference.getextrema()) <= 1, row
    pilots = []
    base = Path('build/quick-foto/r13-controlli')
    for journey in sorted(base.glob('pilot-*')):
        if not journey.is_dir():
            continue
        count = 0
        for file in sorted(journey.glob('*-widgets.json')):
            native = json.loads(file.read_text(encoding='utf-8'))
            quick = json.loads(file.with_name(file.name.replace('widgets', 'quick')).read_text(encoding='utf-8'))
            # The Widgets test harness saves its temporary project on opening.
            # Match the existing parity convention, excluding only that timestamp.
            for state in (native, quick):
                state['project'].pop('modified', None)
            for key in ('project', 'phase', 'fileOpen', 'size', 'dpr', 'platform'):
                assert native[key] == quick[key], (journey, file.name, key)
            assert not quick['warnings'], quick['warnings']
            assert quick['graphics'] == 'GraphicsApi.Direct3D11'
            assert quick['theme']['accent'] == 'indigo'
            assert quick['theme']['backgrounds'] == 'grey'
            assert quick['theme']['font'] == 'plex'
            count += 1
        assert count == 12, (journey, count)
        pilots.append(dict(folder=str(journey), steps=count,
                           excludedVisualSteps=[] if journey.name.startswith('pilot-settled-') else [8]))
    settled = {Path(j['folder']).name for j in pilots if not j['excludedVisualSteps']}
    assert {f'pilot-settled-{theme}-s{scale}' for theme in ('light', 'dark')
            for scale in (1, 2)} <= settled
    summary = dict(controls=len(CASES), pairs=len(rows), images=2*len(rows), journeys=pilots)
    (folder / 'verifica.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
