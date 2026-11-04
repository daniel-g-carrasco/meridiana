"""Summarise repeated R372 probes; never merge different experiments or gesture visits."""

from collections import defaultdict
import json
from pathlib import Path
from statistics import median


HERE = Path(__file__).resolve().parent
groups = defaultdict(list)
for path in sorted(HERE.glob("it-screen-*.json")):
    name, repeat = path.stem.rsplit("-", 1)
    if repeat.isdigit():
        groups[name].append(path)
summary = {}
for name, paths in groups.items():
    rows = defaultdict(lambda: defaultdict(list))
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["platform"] == "windows", path
        visits = defaultdict(int)
        for row in data["results"]:
            gesture = row["gesture"]
            visits[gesture] += 1
            key = f"{gesture} #{visits[gesture]}"
            for metric in ("action_ms", "until_idle_ms", "blocks", "worst_ms", "blocked_ms"):
                rows[key][metric].append(row[metric])
    summary[name] = {"n": len(paths), "files": [path.name for path in paths], "gestures": {
        gesture: {metric: {"values": values, "median": round(median(values), 2),
                           "min": min(values), "max": max(values),
                           "spread": round(max(values) - min(values), 2)} for metric, values in metrics.items()}
        for gesture, metrics in rows.items()}}
(HERE / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
for name, group in summary.items():
    print(name, "n=", group["n"])
    for gesture in ("phase plant #1", "phase production #1", "phase consumption #1", "File: close (Esc) #1",
                    "right panel: edge dragged #1", "window: resized, 15 steps #1",
                    "model: right edge dragged #1", "consumption: right edge dragged #1",
                    "consumption: window resized, 15 steps #1"):
        if gesture in group["gestures"]:
            metrics = group["gestures"][gesture]
            print(" ", gesture, " ".join(f"{key}={metrics[key]['median']} "
                                          f"[{metrics[key]['min']};{metrics[key]['max']}]"
                                          for key in ("action_ms", "blocked_ms")))
