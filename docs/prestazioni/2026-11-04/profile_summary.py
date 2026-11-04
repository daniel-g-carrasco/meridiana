"""Summarise scoped timers and Qt event timings from repeated instrumented probes.

Times are inclusive: parent/child events and wrapped functions must not be added.
Sampling sees Python stacks, including calls waiting in native Qt, not C++ internals.
"""

from collections import defaultdict
import json
from pathlib import Path
from statistics import median
import sys


HERE = Path(__file__).resolve().parent
prefix = sys.argv[1] if len(sys.argv) > 1 else "it-screen-events-all"
paths = sorted(HERE.glob(f"{prefix}-[123].json"))
groups = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
for path in paths:
    probe = json.loads(path.read_text(encoding="utf-8"))["probe"]
    for section in ("calls", "events"):
        for gesture, items in probe[section].items():
            for key, values in items.items():
                groups[section][gesture][key].append(values)
summary = {"files": [p.name for p in paths], "sections": {}}
for section, gestures in groups.items():
    summary["sections"][section] = {}
    for gesture, items in gestures.items():
        summary["sections"][section][gesture] = {
            key: {metric: {"values": [r[metric] for r in rows],
                           "median": round(median(r[metric] for r in rows), 2),
                           "min": min(r[metric] for r in rows), "max": max(r[metric] for r in rows)}
                  for metric in ("count", "total_ms", "max_ms")} for key, rows in items.items()}
out = HERE / f"{prefix}-profile-summary.json"
out.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
for gesture in ("phase plant #1", "phase production #1", "phase consumption #1", "File: close (Esc) #1",
                "right panel: edge dragged #1", "window: resized, 15 steps #1",
                "consumption: right edge dragged #1", "between gestures", "startup"):
    print("\n", gesture)
    for section in ("calls", "events"):
        items = summary["sections"].get(section, {}).get(gesture, {})
        for key, values in sorted(items.items(), key=lambda pair: -pair[1]["total_ms"]["median"])[:8]:
            print(section, key, "n", len(values["total_ms"]["values"]),
                  "ms", values["total_ms"], "calls", values["count"]["values"])
