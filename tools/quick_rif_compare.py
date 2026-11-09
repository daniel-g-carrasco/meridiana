"""Generate a self-contained Widgets/Quick comparison without approving differences."""
import argparse
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))

from PySide6.QtGui import QImage  # noqa: E402

from quick.parity.geometry import compare_snapshots, write_comparison  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--widgets-json', type=Path, required=True)
    parser.add_argument('--quick-json', type=Path, required=True)
    parser.add_argument('--widgets-image', type=Path, required=True)
    parser.add_argument('--quick-image', type=Path, required=True)
    parser.add_argument('--mapping', type=Path, required=True, help='JSON dict: Widgets ID -> named QML item')
    parser.add_argument('--differences', type=Path, default=ROOT / 'docs/quick/compat/differenze.json')
    parser.add_argument('--output', type=Path, required=True, help='New HTML path; existing files are refused')
    parser.add_argument('--title', default='Confronto Widgets / Qt Quick')
    args = parser.parse_args(argv)
    def load(path):
        raw = gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes()
        return json.loads(raw)
    reference, actual, mapping = load(args.widgets_json), load(args.quick_json), load(args.mapping)
    differences = compare_snapshots(reference, actual, mapping, load(args.differences)['differences'])
    images = [QImage(str(path)) for path in (args.widgets_image, args.quick_image)]
    for image, snapshot in zip(images, (reference, actual), strict=True):
        meta = snapshot['meta']
        if 'dpr' not in meta and 'device_pixel_ratio' not in meta:
            raise ValueError('Snapshot must record screenshot device pixel ratio')
        image.setDevicePixelRatio(float(meta.get('dpr', meta.get('device_pixel_ratio'))))
    report = write_comparison(*images, args.output,
                              title=args.title, differences=differences,
                              metadata={'widgets': reference['meta'], 'quick': actual['meta'],
                                        'mapping': mapping, 'intentional_differences': str(args.differences)})
    print(json.dumps(dict(report, unapproved_differences=len(differences), output=str(args.output)), indent=2))
    return 1 if differences else 0


if __name__ == '__main__':
    raise SystemExit(main())
