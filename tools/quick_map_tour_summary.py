"""What tools/quick_map_tour.py wrote, in numbers: python tools/quick_map_tour_summary.py <out dir>"""
import collections
import json
import sys
from pathlib import Path

folder = Path(sys.argv[1])
ev = [json.loads(line) for line in (folder / 'tiles.jsonl').open(encoding='utf8')]
print('events', dict(collections.Counter(e['event'] for e in ev)))
ans = [e for e in ev if e['event'] == 'answered']
ok = [e for e in ans if e['ok']]
print(f'answered {len(ans)}: ok {len(ok)}, errors {len(ans) - len(ok)}; ms ok median '
      f'{sorted(e["ms"] for e in ok)[len(ok) // 2] if ok else None}, max {max((e["ms"] for e in ans), default=None)}')
print('errors by words', collections.Counter((e['attempt'], e['words'][:70]) for e in ans if not e['ok']).most_common(5))
print('asked by source/zoom/disk', sorted(collections.Counter((e['tile'][0], e['tile'][1], e['disk'])
                                                              for e in ev if e['event'] == 'asked').items()))
print('ready by source/disk', collections.Counter((e['tile'][0], e['disk']) for e in ev if e['event'] == 'ready'))
for e in ev:
    if e['event'] in ('failover', 'gave-up'):
        print(' ', e)
print('evicted', sum(e['event'] == 'evicted' for e in ev), 'pinned among them',
      sum(e.get('pinned', False) for e in ev if e['event'] == 'evicted'))
rows = [json.loads(line) for line in (folder / 'gestures.jsonl').open(encoding='utf8')]
for r in rows:
    if 'gesture' in r:
        print(f"{r['gesture']:28s} {r['source']:6s} fps {r.get('fps')} frames {r['frames']:3d} worst {r['worst_frame_ms']:7.1f} >50ms "
              f"{r['frames_over_50']:2d} | during {r['frames_during']:3d} mean {r['mean_during_ms']} | blocks "
              f"{r['blocks']:2d} worst {r['worst_block_ms']:6.1f} total {r['blocked_ms']:7.1f} in-gesture {r.get('blocked_during_ms')} | holes {r['holes']}")
