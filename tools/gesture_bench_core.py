"""Versioned gesture streams and analysis. Standard library only, no Qt or application imports."""
from __future__ import annotations

import json
import math
from pathlib import Path
import random
import re
import statistics

VERSION = 2
GESTURES = ('wheel', 'hires', 'scroll', 'pinch', 'pinch-fast', 'drag', 'orbit', 'keys', 'mixed', 'bursts', 'random')
UI_CASES = ('phases', 'cards', 'report-scroll', 'table-scroll', 'resize', 'resize-meridio', 'zoom-measures', 'meridio')


def parse_qsg_message(message):
    gpu = re.search(r'GPU frame time was ([0-9.]+) ms', message)
    if gpu:
        return {'gpu_ms': float(gpu[1])}
    gui = re.search(r'polish=(\d+) ms, lock=(\d+) ms, blockedForSync=(\d+) ms, animations=(\d+) ms', message)
    if gui:
        return dict(polish_ms=float(gui[1]), gui_lock_ms=float(gui[2]), gui_blocked_sync_ms=float(gui[3]), animation_ms=float(gui[4]))
    return {}


def percentile(values, q):
    if not values:
        return None
    values = sorted(values)
    at = (len(values)-1)*q
    low = int(at)
    return values[low] + (values[min(low+1, len(values)-1)]-values[low])*(at-low)


def describe(values):
    values = [v for v in values if v is not None and math.isfinite(v)]
    return dict(count=len(values), median_ms=percentile(values, .5), p95_ms=percentile(values, .95),
                p99_ms=percentile(values, .99), worst_ms=max(values, default=None))


def frame_stats(intervals, refresh_hz):
    if refresh_hz <= 0:
        raise ValueError('refresh rate must be positive')
    period = 1000/refresh_hz
    result = describe(intervals)
    result.update(period_ms=period, over_1_period=sum(v > period*1.01 for v in intervals),
                  over_1_5_periods=sum(v > period*1.5 for v in intervals),
                  over_2_periods=sum(v > period*2 for v in intervals),
                  missed_frames=sum(max(0, math.ceil(v/period-.05)-1) for v in intervals),
                  jitter_index=statistics.pstdev(intervals)/period if intervals else None)
    edges = [0, .5, 1.01, 1.5, 2, 3, 5, float('inf')]
    result['histogram'] = [dict(from_period=a, to_period=b if math.isfinite(b) else None,
                                count=sum(a <= v/period < b for v in intervals))
                           for a, b in zip(edges, edges[1:], strict=False)]
    return result


def requested(camera):
    if not camera:
        return None
    goal = camera.get('goal')
    if goal:
        return dict(panX=goal['x'], panY=goal['y'], zoom=goal['zoom'],
                    **({'bearing': camera['bearing']} if camera.get('bearing') is not None else {}))
    return {k: v for k, v in camera.items() if k != 'goal' and v is not None}


def same_state(a, b):
    # A pending goal is not the state that was drawn at synchronization.
    a = {k: v for k, v in (a or {}).items() if k != 'goal' and v is not None}
    b = {k: v for k, v in (b or {}).items() if k != 'goal' and v is not None}
    if not a or not b:
        return False
    return all(k in b and isinstance(v, (int, float)) and abs(v-b[k]) <= 1e-5*max(1, abs(v))
               for k, v in a.items())


def analyze(rows, refresh_hz=60):
    """Accept R702 v1 and benchmark v2. A swap is a Qt swap, never optical presentation."""
    rows = list(rows)
    graphics_errors = [r.get('message', 'graphics error') for r in rows if r['record'] == 'graphics_error']
    events = sorted((r for r in rows if r['record'] == 'event'), key=lambda r: r.get('started_ns', r['t_ns']))
    frames = sorted((r for r in rows if r['record'] == 'frame'), key=lambda r: r['t_ns'])
    swaps = sorted(r['t_ns'] for r in rows if r['record'] == 'swap')
    # Separate active cadence from the long idle tail, which would otherwise look like dropped frames.
    start = events[0].get('started_ns', events[0]['t_ns']) if events else 0
    end = events[-1]['t_ns'] if events else float('inf')
    active = [r for r in frames if start <= r['t_ns'] <= end+50_000_000]
    times = [t for t in swaps if start <= t <= end+50_000_000] if swaps else [r['t_ns'] for r in active]
    intervals = [(b-a)/1e6 for a, b in zip(times, times[1:], strict=False)]
    latencies, unmatched, superseded, inert, estimated = [], 0, 0, 0, 0
    for i, event in enumerate(events):
        state = requested(event.get('camera_after'))
        deferred = event.get('deferred_state', False)
        if not state or (not deferred and same_state(requested(event.get('camera_before')), state)):
            inert += 1
            continue
        earliest = event.get('started_ns', event['t_ns'])
        if deferred:
            initial = event['camera_before']['contentY']
            direction = event['expected_direction']
            deadline = events[i+1].get('started_ns', events[i+1]['t_ns']) if i+1 < len(events) else float('inf')
            shown = next((f for f in frames if earliest <= f.get('sync_ns', f['t_ns']) < deadline
                          and (f.get('camera', {}).get('contentY', initial)-initial)*direction > .1), None)
        else:
            shown = next((f for f in frames if f.get('sync_ns', f['t_ns']) >= earliest
                          and same_state(state, f.get('camera'))), None)
        if shown:
            # Qt emits frameSwapped before afterFrameEnd. Looking after the end
            # would incorrectly add a whole display period to every matched event.
            frame_start = shown.get('sync_ns', shown['t_ns']-shown.get('render_frame_ms', 0)*1e6)
            swap = next((t for t in swaps if t >= frame_start), shown['t_ns'])
            latencies.append((swap-earliest)/1e6)
            estimated += bool(deferred)
        elif deferred:
            # A later wheel must not become evidence that an ignored touchpad event was shown.
            unmatched += 1
        elif any(same_state(state, e.get('camera_after')) for e in events[i+1:]):
            unmatched += 1
        elif i+1 < len(events) and events[i+1].get('started_ns', events[i+1]['t_ns']) < next(
                (f.get('sync_ns', f['t_ns']) for f in frames if f.get('sync_ns', f['t_ns']) >= earliest), float('inf')):
            superseded += 1
        else:
            unmatched += 1
    tail = [r for r in frames if r['t_ns'] > end]
    changes = sum(not same_state(a.get('camera'), b.get('camera')) for a, b in zip(tail, tail[1:], strict=False)
                  if a.get('camera') and b.get('camera'))
    def metric(key):
        return describe([r.get(key) for r in active])
    return dict(events=len(events), frames=len(frames), active_frames=len(active), cadence=frame_stats(intervals, refresh_hz),
                handle=describe([r.get('gui_ms') for r in events]), gpu=metric('gpu_ms'), sync=metric('sync_ms'),
                render=metric('render_ms'), render_frame=metric('render_frame_ms'), gui_events=metric('gui_events_ms'),
                animation=metric('animation_ms'), polish=metric('polish_ms'), latency=describe(latencies),
                latency_unmatched=unmatched, latency_superseded=superseded, inert_events=inert,
                latency_estimated=estimated,
                settlement=dict(frames=len(tail), camera_changes=changes),
                graphics_errors=graphics_errors,
                valid_motion=bool(len(active) >= 2 and latencies and not graphics_errors))


def pixel_difference(before, after, threshold=20):
    if len(before) != len(after) or not len(before):
        raise ValueError('pixel samples must be nonempty and the same size')
    delta = [abs(float(a)-float(b)) for a, b in zip(before, after, strict=False)]
    return dict(mean_absolute=sum(delta)/len(delta), changed_fraction=sum(v > threshold for v in delta)/len(delta))


def paired_comparison(base, trial, *, seed=1, threshold=10, bootstrap=2000):
    if len(base) != len(trial) or not base or any(v <= 0 for v in base):
        raise ValueError('comparison needs positive, paired baseline values')
    changes = [(b/a-1)*100 for a, b in zip(base, trial, strict=False)]
    rng = random.Random(seed)
    draws = [statistics.median(rng.choices(changes, k=len(changes))) for _ in range(bootstrap)]
    ci = [percentile(draws, .025), percentile(draws, .975)]
    return dict(pairs=len(base), base=describe(base), trial=describe(trial), change_pct=statistics.median(changes),
                ci95_pct=ci, regression=ci[0] > threshold, threshold_pct=threshold)


def scenario_key(case, defaults=None):
    controls = dict(defaults or {}) | case.get('scenario', {})
    for key in ('modules', 'duration_s', 'tail_ms'):
        if key in case:
            controls[key] = case[key]
    return (case['phase'], case['view'], case['gesture'], case.get('project_sha256'),
            json.dumps(controls, sort_keys=True))


def gesture_steps(kind, seed=1, rate=120, duration=1):
    """Absolute requested offsets avoid accumulating timer rounding. Units are logical pixels."""
    if rate <= 0 or duration <= 0:
        raise ValueError('device rate and duration must be positive')
    rng = random.Random(seed)
    if kind in ('random', 'bursts'):
        parts, at = [], 0.
        choices = list(GESTURES[:9])
        for _ in range(4 if kind == 'random' else 3):
            selected = rng.choice(choices) if kind == 'random' else 'pinch'
            seq = gesture_steps(selected, rng.randrange(2**31), rate, duration/2)
            for step in seq:
                parts.append(dict(step, at_ms=step['at_ms']+at))
            at = parts[-1]['at_ms']+rng.uniform(80, 450)
        return parts
    if kind == 'wheel':
        at, steps = 0., []
        for i in range(10):
            at += rng.uniform(45, 160)*duration
            steps.append(dict(at_ms=at, action='wheel', angle=120 if i < 5 else -120))
        return steps
    if kind == 'keys':
        return [dict(at_ms=i*duration*120, action='key', key=k)
                for i, k in enumerate(('+', '+', 'Right', 'Down', '-', '-', 'Left', 'Up'))]
    if kind in UI_CASES:
        return [dict(at_ms=i*1000/rate, action=kind, progress=i/max(1, int(rate*duration)-1))
                for i in range(max(2, int(rate*duration)))]
    count = max(4, int(rate*duration*(.5 if kind == 'pinch-fast' else 1)))
    steps = []
    if kind in ('pinch', 'pinch-fast', 'mixed'):
        steps.append(dict(at_ms=0, action='native', phase='begin', value=0))
    if kind == 'scroll':
        steps.append(dict(at_ms=0, action='scroll', phase='begin', dx=0, dy=0))
    if kind in ('drag', 'orbit', 'mixed'):
        steps.append(dict(at_ms=0, action='press', button='right' if kind == 'orbit' else 'middle', x=0, y=0))
    x = y = 0.
    for i in range(count):
        t = i/(count-1)
        speed = math.sin(math.pi*t)**2*(1 if t < .55 else -.7)*rng.uniform(.8, 1.2)
        at = (i+1)*1000/rate
        if kind in ('pinch', 'pinch-fast', 'mixed'):
            steps.append(dict(at_ms=at, action='native', phase='update', value=speed*(.025 if kind == 'pinch-fast' else .012)))
        if kind == 'hires':
            steps.append(dict(at_ms=at, action='wheel', angle=round(speed*35)))
        if kind == 'scroll':
            steps.append(dict(at_ms=at, action='scroll', phase='momentum' if t > .8 else 'update',
                              dx=round(speed*13), dy=round(speed*7)))
        if kind in ('drag', 'orbit', 'mixed'):
            x += speed*4
            y += speed*2
            steps.append(dict(at_ms=at, action='move', button='right' if kind == 'orbit' else 'middle', x=x, y=y))
            if kind == 'mixed' and i % 12 == 0:
                steps.append(dict(at_ms=at, action='wheel', angle=30 if t < .5 else -30))
    at = (count+1)*1000/rate
    if kind in ('pinch', 'pinch-fast', 'mixed'):
        steps.append(dict(at_ms=at, action='native', phase='end', value=0))
    if kind == 'scroll':
        steps.append(dict(at_ms=at, action='scroll', phase='end', dx=0, dy=0))
    if kind in ('drag', 'orbit', 'mixed'):
        steps.append(dict(at_ms=at, action='release', button='right' if kind == 'orbit' else 'middle', x=x, y=y))
    if not steps:
        raise ValueError(f'unknown gesture: {kind}')
    return steps


def load_rows(path):
    with Path(path).open(encoding='utf-8-sig') as stream:
        rows = [json.loads(line) for line in stream if line.strip()]
    if any(r.get('version', 1) not in (1, VERSION) for r in rows):
        raise ValueError('unsupported stream version')
    return rows


def trace_cases(rows, refresh_hz=None):
    session = next((r for r in rows if r['record'] == 'session'), {})
    refresh = refresh_hz or session.get('refresh_hz') or session.get('environment', {}).get('refresh_hz') or 60
    if session.get('case'):
        return [dict(id=session['case'], analysis=analyze(rows, refresh))]
    events = sorted((r for r in rows if r['record'] == 'event'), key=lambda r: r['t_ns'])
    groups = []
    for event in events:
        if (not groups or event.get('gesture') != groups[-1][-1].get('gesture')
                or event['t_ns']-groups[-1][-1]['t_ns'] > 350_000_000):
            groups.append([])
        groups[-1].append(event)
    if not groups:
        return [dict(id='trace-no-input', analysis=analyze(rows, refresh))]
    result = []
    for i, group in enumerate(groups):
        start = group[0].get('started_ns', group[0]['t_ns'])
        end = min(group[-1]['t_ns']+800_000_000, groups[i+1][0]['t_ns'] if i+1 < len(groups) else float('inf'))
        active = [r for r in rows if r['record'] in ('frame', 'swap') and start <= r['t_ns'] < end]
        result.append(dict(id=f"trace-{i}-{group[0].get('gesture', 'unknown')}", analysis=analyze(group+active, refresh)))
    return result


def markdown(report):
    lines = ['# Misura dei gesti', '', 'Gli swap Qt non certificano la presentazione fisica sul pannello.', '',
             '| Scenario | Eventi | Frame | mediana / p95 / p99 / max ms | >1,5 periodi | Ritardo p95 ms | GPU p95 ms |',
             '|---|---:|---:|---|---:|---:|---:|']
    def fmt(v):
        return 'n/d' if v is None else f'{v:.2f}'
    for case in report.get('cases', []):
        a = case['analysis']
        c = a['cadence']
        values = ' / '.join(fmt(c[k]) for k in ('median_ms', 'p95_ms', 'p99_ms', 'worst_ms'))
        lines.append(f"| {case['id']} | {a['events']} | {a['frames']} | {values} | {c['over_1_5_periods']} | "
                     f"{fmt(a['latency']['p95_ms'])} | {fmt(a['gpu']['p95_ms'])} |")
    lines.extend(['', 'Ambiente: '+json.dumps(report.get('environment', {}), ensure_ascii=False), ''])
    if 'comparisons' in report:
        lines += ['| Scenario | Misura | Coppie | Base ms | Prova ms | Variazione % | IC 95% % | Peggiora |',
                  '|---|---|---:|---:|---:|---:|---|---|']
        for row in report['comparisons']:
            lines.append(f"| {row['phase']}/{row['view']}/{row['gesture']} | {row['metric']} | {row['pairs']} | "
                         f"{fmt(row['base']['median_ms'])} | {fmt(row['trial']['median_ms'])} | {row['change_pct']:.1f} | "
                         f"{row['ci95_pct'][0]:.1f} / {row['ci95_pct'][1]:.1f} | {'si' if row['regression'] else 'no'} |")
        errors = [r for r in report.get('runs', []) if 'error' in r]
        if errors:
            lines += ['', 'Esecuzioni fallite, escluse dal confronto:']
            lines += [f"- {r['label']}, seme {r['seed']}: {r['error']}" for r in errors]
    return '\n'.join(lines)
