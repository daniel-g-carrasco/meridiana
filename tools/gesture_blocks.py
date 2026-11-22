"""Frame gaps of gesture_bench raw traces: median, p95, worst and the blocks over 50 and 100 ms.

Standard library only. The gaps are those between Qt swaps while the gesture's events arrive
(up to 50 ms after the last one), as in gesture_bench_core.analyze.
"""
import argparse
import json
from pathlib import Path

from gesture_bench_core import percentile


def read(path):
    rows = [json.loads(line) for line in Path(path).read_text(encoding='utf8').splitlines() if line]
    events = [r for r in rows if r['record'] == 'event']
    frames = [r for r in rows if r['record'] == 'frame']
    swaps = sorted(r['t_ns'] for r in rows if r['record'] == 'swap')
    start, end = events[0].get('started_ns', events[0]['t_ns']), events[-1]['t_ns']+50_000_000
    times = [t for t in swaps if start <= t <= end]
    gaps = [(b-a)/1e6 for a, b in zip(times, times[1:], strict=False)]
    active = [f for f in frames if start <= f['t_ns'] <= end]

    def column(name, source=active):
        return [f[name] for f in source if f.get(name) is not None]
    return dict(gaps=gaps, event=column('gui_ms', events), sync=column('sync_ms'), render=column('render_ms'),
                gpu=column('gpu_ms'), prepare=column('gui_prepare_ms'), late=column('lateness_ms', events),
                blocks=[(round((a-start)/1e6), round((b-a)/1e6, 1)) for a, b in zip(times, times[1:], strict=False)
                        if b-a > 50_000_000])


def row(name, data):
    gaps = data['gaps']

    def p(values, q):
        value = percentile(values, q)
        return '   n/a' if value is None else f'{value:6.1f}'
    return (f"{name:<44} {len(gaps):4d} {p(gaps, .5)} {p(gaps, .95)} {max(gaps, default=0):7.1f} "
            f"{sum(g > 50 for g in gaps):4d} {sum(g > 100 for g in gaps):4d}  "
            f"{p(data['event'], .95)} {max(data['event'], default=0):7.1f} {p(data['sync'], .95)} "
            f"{max(data['sync'], default=0):7.1f} {p(data['render'], .95)} {p(data['gpu'], .95)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('traces', nargs='+', type=Path, help='JSONL traces, or summaries whose cases name them')
    parser.add_argument('--blocks', action='store_true', help='list each gap over 50 ms with its time in the gesture')
    args = parser.parse_args()
    paths = []
    for path in args.traces:
        if path.suffix == '.json':
            paths += [path.with_name(case['raw']) for case in json.loads(path.read_text(encoding='utf8'))['cases']]
        else:
            paths.append(path)
    print(f"{'trace':<44} gaps median    p95   worst  >50 >100  ev.p95  ev.max syn.p95 syn.max ren.p95 gpu.p95")
    for path in paths:
        data = read(path)
        print(row(path.stem[-44:], data))
        if args.blocks:
            for at, gap in data['blocks']:
                print(f'    at {at} ms: {gap} ms')


if __name__ == '__main__':
    main()
