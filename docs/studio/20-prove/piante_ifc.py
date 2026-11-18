"""Study 20: what Meridiana gets from each sample, drawn from above (way c, the program's): the buildings with the planes
of their roofs coloured by slope, the exclusions in grey, the roof type and the eave height written on each building.

    python piante_ifc.py campioni.json CACHE OUT_FOLDER [--only NAME ...]

GPL-3.0-or-later, as Meridiana."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "src"))

SHOWN = ("meridiana-misto", "bs-architecture", "location", "duplex", "clinic-arch", "esplanades", "schependomlaan")


def draw(name: str, path: Path, out: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as Patch

    from meridiana import ifc_import, ifc_read, model
    found = ifc_read.read(path)
    plan = ifc_import.plan(found, model.Project(), "origin", "context")
    fig, ax = plt.subplots(figsize=(7, 6), dpi=110)
    cmap = plt.get_cmap("viridis")
    for b in plan.buildings:
        for p in b.pitches():
            ax.add_patch(Patch(p.ring, closed=True, facecolor=cmap(min(p.tilt, 60.0) / 60.0), edgecolor="white",
                               linewidth=0.6, alpha=0.9))
        ax.add_patch(Patch(b.footprint, closed=True, fill=False, edgecolor="black", linewidth=1.2))
        xs, ys = [q[0] for q in b.footprint], [q[1] for q in b.footprint]
        ax.text(sum(xs) / len(xs), sum(ys) / len(ys), f"{b.roof.type}\n{b.height:.1f} m", ha="center", va="center",
                fontsize=7)
    for e, _host in plan.exclusions:
        ax.add_patch(Patch(e.ring, closed=True, facecolor="#9a9a9a", edgecolor="#444444", linewidth=0.5))
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.set_title(f"{name}: {len(plan.buildings)} edifici, {sum(len(b.pitches()) for b in plan.buildings)} falde, "
                 f"{len(plan.exclusions)} esclusioni", fontsize=9)
    ax.set_xlabel("m, est")
    ax.set_ylabel("m, nord")
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 60))
    fig.colorbar(sm, ax=ax, shrink=0.7, label="inclinazione, gradi")
    fig.tight_layout()
    target = out / f"{name}.png"
    fig.savefig(target)
    plt.close(fig)
    return str(target)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("samples")
    ap.add_argument("cache")
    ap.add_argument("out")
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()
    samples = {s["name"]: s for s in json.loads(Path(args.samples).read_text(encoding="utf-8"))["campioni"]}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name in args.only or SHOWN:
        print(draw(name, Path(args.cache) / samples[name]["file"], out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
