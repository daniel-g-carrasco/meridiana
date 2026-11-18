"""A check of scalabilita.py's numbers for the 5,000-module project, without tracemalloc: the near-shading table
of each array on its own (nearshade.shading, uncached), the whole energy job cold and warm, three times each, and
the process' working set; also the plane count of each array (one plane per row of tilted tables), which drives
the shading's cost."""

import os
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(r"C:\Users\utente\dev\meridiana-lavoro")
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "docs" / "studio" / "18-prove"))
from scalabilita import project_for, working_set_mb  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pvlib  # noqa: E402

from meridiana.energy import nearshade, system  # noqa: E402
from meridiana.ui import window  # noqa: E402

CACHE = Path(os.environ.get("LOCALAPPDATA", "")) / "Meridiana" / "cache"
root = Path(tempfile.mkdtemp(prefix="meridiana-shade-"))
shutil.copytree(CACHE / "pvgis", root / "cache" / "pvgis")
target = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
p = project_for(target)
results = {sf.id: p.fill(sf) for sf in p.subfields}
arrays = system.arrays_of(p, results)
idx = pd.date_range("1990-01-01", periods=8760, freq="h", tz="UTC")
pos = pvlib.solarposition.get_solarposition(idx, p.site.lat, p.site.lon)
needed = nearshade.needed_cells(pos.azimuth.to_numpy(), 90.0 - pos.apparent_zenith.to_numpy())
print(f"project {target}: {sum(r.count for r in results.values())} modules; working set {working_set_mb():.0f} MB")
for a in arrays:
    n, e1, e2 = nearshade.plane_axes(a.tilt, a.azimuth)
    planes = {round(float(nearshade.module_corners(pm).mean(axis=0) @ n), 3) for pm in a.placed}
    lit = int(((nearshade.sun_vectors(*[x.ravel() for x in np.meshgrid(nearshade.AZIMUTHS, nearshade.ELEVATIONS)]) @ n) > 1e-6).sum())
    times = []
    for _ in range(3):
        t = time.perf_counter()
        sh = nearshade.shading(a.placed, a.obstacles, a.tilt, a.azimuth, needed,
                               nearshade.blocks_of(a.module.cells, a.module.diodes, a.module.twin))
        times.append(time.perf_counter() - t)
    print(f"  array {a.key}: {a.modules} modules, {len(planes)} planes, {len(a.obstacles)} solids, {lit} lit cells of "
          f"{int(needed.sum())} needed: shading {statistics.median(times):.2f} s (samples {[round(x, 2) for x in times]}); "
          f"tables {sh.modules.nbytes / 2 ** 20:.0f} MB x 2; working set {working_set_mb():.0f} MB")
job = window.EnergyJob(1, p.to_json(), results, root / "cache", False)
for kind in ("cold", "warm", "cold", "warm", "cold", "warm"):
    if kind == "cold":
        with nearshade._CACHE_LOCK:
            nearshade._CACHE.clear()
    t = time.perf_counter()
    out = job._compute()
    print(f"  EnergyJob._compute {kind}: {time.perf_counter() - t:.2f} s; working set {working_set_mb():.0f} MB"
          + (f"; error {out['error_sim']}" if out.get("error_sim") else ""))
