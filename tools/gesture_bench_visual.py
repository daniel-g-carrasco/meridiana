"""Pixel comparison of a separate replay. Captures never enter the timing pass."""
from gesture_bench_core import describe, same_state


def analyze_pixels(captures, last_event_ns):
    import numpy as np
    if len(captures) < 2:
        return dict(available=False, reason='fewer than two captures')
    if all(float(np.std(row[1])) < .5 for row in captures):
        return dict(available=False, reason='empty or uniform render target')
    rows = []
    for before, after in zip(captures, captures[1:], strict=False):
        if before[1].shape != after[1].shape:
            rows.append(dict(t_ns=after[0], resized=True))
            continue
        # Use signed arithmetic: unsigned uint8 subtraction would wrap.
        diff = np.abs(before[1].astype(np.int16)-after[1].astype(np.int16))
        changed = float(np.mean(np.max(diff, axis=2) > 20))
        stable = same_state(before[2], after[2])
        rows.append(dict(t_ns=after[0], changed_fraction=changed, mean_absolute=float(diff.mean()),
                         stable_state=stable, after_last_event=before[0] > last_event_ns,
                         capture_interval_ms=(after[0]-before[0])/1e6))
    tail = [r for r in rows if r.get('after_last_event') and r.get('stable_state')]
    return dict(available=True, sample_stride_physical_px=4, captures=len(captures),
                grab_scale_xy=captures[-1][3], samples=rows,
                settlement_changed_fraction_max=max((r['changed_fraction'] for r in tail), default=None),
                capture_intervals=describe([r['capture_interval_ms'] for r in rows if 'capture_interval_ms' in r]))
