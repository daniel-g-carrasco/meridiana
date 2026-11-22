"""Bounded IFC import measurements, using Meridiana's process reader, no client identity in output."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tests')]
import _setup  # noqa: E402,F401
from ifc_banco import read  # noqa: E402
from gesture_bench import isolate_profile, write_new  # noqa: E402

isolate_profile(_setup)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--files', nargs='+', type=Path, required=True)
    p.add_argument('--budget', type=float, default=180)
    p.add_argument('--memory-gb', type=float, default=6)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--save-reference', action='store_true', help='Synthetic inputs only: preserve raw viewer geometry')
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    reports = []
    for index, path in enumerate(args.files):
        started = time.perf_counter()
        context = tempfile.TemporaryDirectory(prefix='meridiana-stress-context-')
        found, outcome, _reason, peak = read(path, 'fast', args.budget, int(args.memory_gb*1e9),
                                           context=Path(context.name) if args.save_reference else None)
        listing = (found or {}).get('listing', {})
        row = dict(case=index+1, size_bytes=path.stat().st_size, outcome=outcome,
                   seconds=time.perf_counter()-started, peak_rss_bytes=peak,
                   elements=listing.get('elements'), triangles=listing.get('triangles'),
                   buildings=len((found or {}).get('buildings') or []),
                   display='not measured: importer did not produce a benchmark project')
        if _reason:
            row['reason'] = _reason.replace(str(path), '<input>').replace(path.name, '<input>')
        if args.save_reference and found and found.get('context'):
            from gesture_projects import viewer_project
            project = viewer_project(found)
            output = args.out.with_name(args.out.stem+f'-reference-{index+1}.meridiana')
            if output.exists():
                raise FileExistsError(output)
            from gesture_projects import preserve_mesh
            preserve_mesh(project, output)
            project.save(output)
            row['viewer_project'] = output.name
            row['display'] = 'raw geometry reference only, no editable roofs imported'
        reports.append(row)
        print(json.dumps(row), flush=True)
        context.cleanup()
    write_new(args.out, json.dumps(reports, indent=2))


if __name__ == '__main__':
    # Nothing persists in a real profile, even if a subprocess consults platform paths.
    os.environ['MERIDIANA_PRELOAD'] = '0'
    main()
