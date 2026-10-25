"""Tema H della revisione completa: i minuti del CI per giorno e per job, da runs.json e jobs.txt scritti da
H-ci-minuti.sh. Ogni job e' arrotondato per eccesso al minuto, come fattura GitHub (docs.github.com, prezzi dei
runner: "GitHub rounds the minutes and partial minutes each job uses up to the nearest whole minute").

    python H-ci-minuti.py <cartella con runs.json e jobs.txt>

I run rifiutati per la fatturazione (durata di pochi secondi, nessun job partito) non hanno righe in jobs.txt
con secondi sopra lo zero e non contano."""

import collections
import json
import math
import sys
from pathlib import Path

folder = Path(sys.argv[1])
runs = {str(r["databaseId"]): r for r in json.loads((folder / "runs.json").read_text(encoding="utf-8"))}
run_min = collections.defaultdict(lambda: collections.defaultdict(float))
billed = collections.defaultdict(lambda: collections.defaultdict(int))
count = collections.defaultdict(lambda: collections.defaultdict(int))
for line in (folder / "jobs.txt").read_text(encoding="utf-8").splitlines():
    parts = line.split()
    if len(parts) < 4 or float(parts[2]) <= 0:
        continue
    rid, name, sec = parts[0], parts[1], float(parts[2])
    day = runs.get(rid, {}).get("createdAt", "?")[:10]
    run_min[day][name] += sec / 60
    billed[day][name] += math.ceil(sec / 60)
    count[day][name] += 1
total = collections.defaultdict(int)
for day in sorted(run_min):
    cells = ", ".join(f"{n}: {count[day][n]} job, {run_min[day][n]:.0f} min di esecuzione, {billed[day][n]} fatturati"
                      for n in sorted(run_min[day]))
    print(day, cells)
    for n in billed[day]:
        total[n] += billed[day][n]
lin, win = total.get("core-linux", 0), total.get("core-windows", 0)
print(f"totale fatturato: linux {lin}, windows {win}; con Windows contato doppio {lin + 2 * win} minuti;"
      f" a 0,006/0,010 USD {lin * 0.006 + win * 0.010:.2f} USD; a 0,008/0,016 USD {lin * 0.008 + win * 0.016:.2f} USD")
refused = sum(1 for r in runs.values() if r["conclusion"] == "failure")
print(f"run elencati: {len(runs)}; falliti (compresi quelli rifiutati per la fatturazione): {refused}")
