"""Where the energy job's time goes, split between C code (numpy, pandas, shapely) and Python frames (Meridiana's
own, pvlib's, pandas'). Measured on Daniel's PC on 23/10/2026 (register R31): 3.55 s for 188 modules, 2.3 s of them
in economics.dispatch (8760 hours times 156 calls, pure Python), 0.95 s in C.

Needs a project file and a PVGIS cache: MERIDIANA_SAMPLE (default: Daniel's "Prova capannone Rho") and
MERIDIANA_CACHE (default: %LOCALAPPDATA%/Meridiana/cache). In the cloud make a project and a synthetic year with
tests/_energy.py instead. Run with QT_QPA_PLATFORM=offscreen."""
import cProfile
import os
import pstats
import shutil
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

REPO = Path(os.environ.get("PROBE_REPO", Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(REPO / "src"))

from meridiana import model  # noqa: E402
from meridiana.energy import pipeline  # noqa: E402

SAMPLE = Path(os.environ.get("MERIDIANA_SAMPLE", r"C:\Users\utente\dev\meridiana-prove\Prova capannone Rho.meridiana"))
CACHE = Path(os.environ.get("MERIDIANA_CACHE") or Path(os.environ.get("LOCALAPPDATA", "")) / "Meridiana" / "cache")

root = Path(tempfile.mkdtemp(prefix="meridiana-energy-"))
shutil.copytree(CACHE / "pvgis", root / "cache" / "pvgis")
p, _n = model.Project.load(SAMPLE)
results = {sf.id: p.fill(sf) for sf in p.subfields if sf.filled}
print("moduli:", sum(len(r.modules) for r in results.values()) if results else 0)


def compute() -> dict:                           # the energy job's work (energy/pipeline.py since task 18b)
    return pipeline.compute_or_say(p, results, root / "cache", False).as_dict()


compute()                                        # imports and caches warmed up
pr = cProfile.Profile()
t = time.perf_counter()
pr.enable()
compute()
pr.disable()
print(f"calcolo: {time.perf_counter() - t:.2f} s")
st = pstats.Stats(pr)
by = Counter()
own = Counter()
src = str(REPO / "src")
for (file, _line, name), (_calls, _ncalls, tt, _cum, _callers) in st.stats.items():
    if file.startswith("~") or file == "<built-in>" or "built-in" in name or "method" in name:
        by["C (numpy, pandas, shapely, interprete)"] += tt
    elif src in file:
        by["Python di Meridiana"] += tt
        own[Path(file).name] += tt
    elif "pvlib" in file:
        by["Python di pvlib"] += tt
    elif "pandas" in file or "numpy" in file:
        by["Python di numpy/pandas"] += tt
    else:
        by["altro Python"] += tt
total = sum(by.values())
for k, v in by.most_common():
    print(f"  {k:40} {v:6.2f} s  {100 * v / total:4.0f} %")
print("file di Meridiana per tempo proprio:")
for k, v in own.most_common(8):
    print(f"  {k:28} {v:6.2f} s")
print("funzioni di Meridiana per tempo proprio:")
rows = sorted(((tt, ncalls, Path(f).name, n) for (f, _l, n), (_c, ncalls, tt, _ct, _cl) in st.stats.items() if src in f),
              reverse=True)
for tt, ncalls, f, n in rows[:8]:
    print(f"  {f:16} {n:36} {tt:5.2f} s  {ncalls:8d} chiamate")
