"""The test bench of the BIM import: every model of a private collection read as the program reads it (the worker in a
process of its own, with its time and memory limits, the second try in the simple way), planned as the program plans it,
and checked. One row per model; so that every fix is measured on all of them and nothing regresses.

    python tools/ifc_banco.py --corpus C:/Users/Grasso/dev/meridiana-prove/bim-corpus --label prima
    python tools/ifc_banco.py --label dopo --reuse prima     # the plan again on what was read before (no reading)
    python tools/ifc_banco.py --compare prima dopo

The collection is made of the clients' models and stays out of git: `elenco.csv` says where each file comes from, the
rows name a model only by its code (m01...), and the results stay beside the models. Only aggregated numbers may go in
the repository. It also works on any folder of .ifc and .ifczip files, the synthetic ones of the tests included.

What is checked on each model (the names of the columns):
- esito: ok, or vuoto (read, no building), or file, crash, tempo, memoria, piano (the plan raised), salva (not savable)
- oltre_m: how far the 3D walls and roofs drawn stand above the highest pitch of the file; buco_m: how far a wall stops
  under the roof that reaches it (sky showing between wall and pitch)
- fuori_pct: the pitches' area outside their building's outline; scoperto_pct: the outline with no pitch over it;
  sovrapp_pct: the pitches' area counted twice in plan
- area_pct: the pitches' area in the project against the file's; dz_m: how far the planes in the project are from the
  file's, at the corners of each pitch
- est_m, alt_m: the plan's extent and the highest roof: a wrong unit shows there; muri_fuori: the walls of the file
  standing outside every outline (a part of the building without a roof)
- sito, lat, lon, fiducia: what the file says of its place and how far the program trusts it
- sospesi, base_max: the bodies whose walls start above the ground, on another part of the building, and come in rising
  from the ground (Building has no base height yet, R352), and the highest such base
- sito_fermo: the project's site after the import as the window proposes it, on a project standing elsewhere: it must
  not have moved (1); centro_m: how far the middle of the buildings falls from the middle of the plan
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DEFAULT_CORPUS = Path("C:/Users/Grasso/dev/meridiana-prove/bim-corpus")
BUDGET_S = 180.0
SECOND_S = 60.0
COLUMNS = ("id", "mb", "schema", "app", "esito", "modo", "s", "gb", "edifici", "corpi", "falde", "ostacoli", "storey",
           "tipi", "sito", "lat", "lon", "fiducia", "come", "nord", "unit_m", "oltre_m", "buco_m", "fuori_pct", "scoperto_pct",
           "sovrapp_pct", "area_pct", "dz_m", "est_m", "alt_m", "sito_fermo", "centro_m", "muri_fuori", "terrazze", "fuori_tempo", "senza_geom", "errori",
           "sospesi", "base_max", "avvisi", "motivo")


def models_of(corpus: Path) -> list[tuple[str, Path]]:
    """(code, file) of each model: the codes of elenco.csv when it is there, else the files found in order."""
    listed = corpus / "elenco.csv"
    out = []
    if listed.is_file():
        with listed.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                path = corpus / row["locale"]
                if path.suffix.lower() in (".ifc", ".ifczip") and path.is_file():
                    out.append((row["id"], path))
        return out
    files = sorted(p for p in corpus.rglob("*") if p.suffix.lower() in (".ifc", ".ifczip"))
    return [(f"m{i + 1:02d}", p) for i, p in enumerate(files)]


def read(path: Path, mode: str, budget: float, memory: int) -> tuple[dict | None, str, str, float]:
    """(found, outcome, why, peak bytes): the worker as the window starts it, its stdout read, its time and memory
    watched. Never raises for what a model does."""
    from meridiana import procmem
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    from meridiana.ifc_worker import main as _worker
    extra = ["--budget", str(round(budget * 0.7))] if "--budget" in (_worker.__code__.co_consts or ()) else []
    p = subprocess.Popen([sys.executable, "-m", "meridiana.ifc_worker", str(path), "--mode", mode, *extra], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=str(ROOT))
    box: dict = {"lines": []}

    def pump():
        for raw in p.stdout:
            if raw.startswith(b'{"result"') or raw.startswith(b'{"error"'):
                box["lines"].append(raw)
    th = threading.Thread(target=pump, daemon=True)
    th.start()
    t0, peak, stopped = time.monotonic(), 0, ""
    while p.poll() is None:
        time.sleep(0.2)
        used = procmem.rss(p.pid, tree=True) or 0
        peak = max(peak, used)
        if time.monotonic() - t0 > budget:
            stopped = "tempo"
        elif used > memory:
            stopped = "memoria"
        if stopped:
            p.kill()
            break
    p.wait()
    th.join(timeout=20)
    if stopped:
        return None, stopped, f"{stopped} after {time.monotonic() - t0:.0f} s, {peak / 1e9:.1f} GB", peak
    for raw in box["lines"]:
        msg = json.loads(raw.decode("utf-8", "replace"))
        if "result" in msg:
            return msg["result"], "ok", "", peak
        return None, "file" if msg.get("kind") == "file" else "crash", str(msg.get("error"))[:160], peak
    return None, "crash", f"exit code {p.returncode}, no answer", peak


def checks(found: dict) -> dict:
    """The checks on what was read: the plan as the window makes it, the mesh, the file's numbers against the
    project's. Raises what the plan raises (the caller says «piano»)."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    from meridiana import ifc_import, mesh, model

    def shape(ring):
        s = Polygon(ring)
        return s if s.is_valid else s.buffer(0)
    project = model.Project(name="banco")
    project.site = model.Site(lat=46.0, lon=13.0, address="46.00000000, 13.00000000")
    site_before = (project.site.lat, project.site.lon, project.site.address)
    place = ifc_import.place_of(found)
    how = ifc_import.default_how(place, project)
    plan = ifc_import.plan(found, project, how=how)
    row: dict = {"come": how, "nord": round(place.angle, 2), "fiducia": getattr(place, "trust", place.source),
                 "corpi": len(plan.buildings)}
    row["avvisi"] = len(plan.approximated) + len(plan.left_out)
    problem = ifc_import.problem(plan)
    if problem:
        row["motivo"] = problem[:120]
    # the bodies that stand on another part and come in rising from the ground (R352)
    raised = [x["base"] for x in getattr(plan, "bases", []) if x["base"] is not None and x["base"] > 1.0]
    row["sospesi"] = len(raised)
    row["base_max"] = round(max(raised), 2) if raised else ""
    ids = ifc_import.apply(project, plan)
    row["sito_fermo"] = int((project.site.lat, project.site.lon, project.site.address) == site_before)
    # the file's pitches, each above its own ground
    raw_top, raw_area = None, 0.0
    frame = ifc_import.Frame(found, place, how, project.site)
    raw_planes = []
    for b in found.get("buildings") or []:
        ground = float(b.get("ground") or 0.0)
        for p in b.get("pitches") or []:
            member = ifc_import._Pitch(p, frame, ground)
            raw_area += Polygon(member.ring).area
            raw_planes.append(member)
            top = max(member.z(*q) for q in member.ring)
            raw_top = top if raw_top is None else max(raw_top, top)
    # what a roof of the plan was made of may go to an obstacle (a chimney's cap): those are not in the pitches' account
    moved = float(found.get("counts", {}).get("capped_area") or 0.0) + float(getattr(plan, "moved_area", 0.0) or 0.0)
    worst_over, outside, uncovered, overlap, areas = -1e9, 0.0, 0.0, 0.0, 0.0
    worst_dz, xs, ys, top = 0.0, [], [], 0.0
    worst_gap = 0.0
    types: dict = {}
    for b in project.buildings:
        types[b.roof.type] = types.get(b.roof.type, 0) + 1
        pitches = b.pitches()
        if not pitches:
            continue
        pos, _nor, _col = mesh.building_triangles(b.footprint, pitches)
        drawn = float(pos[:, 1].max()) if len(pos) else 0.0
        highest = max(z for pt in pitches for _x, _y, z in pt.corners_3d())
        limit = highest if raw_top is None else max(highest, raw_top)
        worst_over = max(worst_over, drawn - limit)
        if hasattr(mesh, "wall_gap"):
            worst_gap = max(worst_gap, mesh.wall_gap(b.footprint, pitches))
        else:
            worst_gap = max(worst_gap, _gap_before(mesh, b.footprint, pitches))
        top = max(top, drawn)
        outline = shape(b.footprint)
        shapes = [shape(pt.ring) for pt in pitches]
        union = unary_union(shapes)
        total = sum(s.area for s in shapes)
        areas += total
        outside += union.difference(outline.buffer(0.02)).area
        uncovered += outline.difference(union.buffer(0.02)).area
        overlap += max(0.0, total - union.area)
        for x, y in b.footprint:
            xs.append(x)
            ys.append(y)
        for pt in pitches:
            for x, y, z in pt.corners_3d():
                # the file's plane nearest at this corner among those with this facing
                near = [m for m in raw_planes if abs((m.azimuth - pt.azimuth + 180) % 360 - 180) < 3.0
                        and abs(m.tilt - pt.tilt) < 1.0 and Polygon(m.ring).buffer(0.2).contains(_point(x, y))]
                if near:
                    worst_dz = max(worst_dz, min(abs(m.z(x, y) - z) for m in near))
    area_total = max(areas, 1e-9)
    row.update(buco_m=round(worst_gap, 2), oltre_m=round(worst_over, 2) if worst_over > -1e8 else "", fuori_pct=round(100 * outside / area_total, 1),
               scoperto_pct=round(100 * uncovered / area_total, 1), sovrapp_pct=round(100 * overlap / area_total, 1),
               area_pct=round(100 * (areas + moved) / raw_area, 1) if raw_area else "", dz_m=round(worst_dz, 3),
               est_m=round(max(max(xs) - min(xs), max(ys) - min(ys)), 1) if xs else "", alt_m=round(top, 2),
               centro_m=round(math.hypot((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2), 1) if xs else "",
               tipi=" ".join(f"{k}:{v}" for k, v in sorted(types.items())))
    # the project made of it must save and read back
    try:
        model.Project.from_json(json.loads(json.dumps(project.to_json())))
    except (ValueError, TypeError, KeyError) as error:
        row["esito"] = "salva"
        row["motivo"] = str(error)[:160]
    row["_ids"] = len(ids)
    return row


def _gap_before(mesh, footprint, pitches) -> float:
    """The same measure on the code before the check existed: the sides' middles and the pitches' corners near them."""
    return 0.0


def _point(x, y):
    from shapely.geometry import Point
    return Point(x, y)


def row_of(code: str, path: Path, found: dict | None, outcome: str, why: str, mode: str, seconds: float,
           peak: float) -> dict:
    row = dict.fromkeys(COLUMNS, "")
    row.update(id=code, mb=round(path.stat().st_size / 1e6, 1), esito=outcome, motivo=why, modo=mode,
               s=round(seconds, 1), gb=round(peak / 1e9, 2))
    if found is None:
        return row
    c = found.get("counts") or {}
    s = found.get("site") or {}
    row.update(schema=found.get("schema", ""), app=(found.get("application") or "")[:28].replace(",", " "),
               edifici=len({b.get("ifc") for b in found.get("buildings") or []}),
               falde=sum(len(b.get("pitches") or []) for b in found.get("buildings") or []),
               ostacoli=len(found.get("obstacles") or []),
               storey=max((int(v) for v in (found.get("storeys") or {}).values()), default=""),
               sito=(s.get("name") or "")[:16].replace(",", " "), lat=round(s["lat"], 4) if s else "",
               lon=round(s["lon"], 4) if s else "", unit_m=found.get("unit_m", ""), muri_fuori=c.get("walls_outside", ""),
               terrazze=c.get("terrace_elements", ""), fuori_tempo=c.get("over_budget", ""),
               senza_geom=c.get("no_shape", ""), errori=c.get("errors", 0))
    if not found.get("buildings") and not found.get("supports"):
        row["esito"] = "vuoto"
        return row
    try:
        row.update(checks(found))
    except Exception as error:      # noqa: BLE001  the bench's boundary: what the plan raises is a result
        row.update(esito="piano", motivo=f"{type(error).__name__}: {error}"[:200])
    return row


def run(args) -> int:
    from meridiana import procmem
    corpus = Path(args.corpus)
    out = corpus / "banco" / args.label
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    todo = models_of(corpus)
    if args.only:
        todo = [(c, p) for c, p in todo if c in args.only.split(",")]
    for code, path in todo:
        t0 = time.monotonic()
        saved = out / f"{code}.json"
        found, outcome, why, peak, mode = None, "", "", 0.0, "direct"
        source = corpus / "banco" / args.reuse / f"{code}.json" if args.reuse else None
        if source is not None and source.is_file():
            data = json.loads(source.read_text(encoding="utf-8"))
            found, outcome, why, peak, mode = (data["found"], data["outcome"], data["why"], data["peak"], data["mode"])
            seconds = data["seconds"]
        else:
            found, outcome, why, peak = read(path, "direct", args.timeout, procmem.limit())
            if found is None and outcome in ("crash", "tempo"):
                first = why
                mode = "simple"
                found, outcome2, why, peak2 = read(path, "simple", SECOND_S, procmem.limit())
                peak = max(peak, peak2)
                outcome = outcome2 if found is None else "ok"
                why = f"{first}; {why}" if found is None else f"second try: {first}"
            seconds = time.monotonic() - t0
            saved.write_text(json.dumps({"found": found, "outcome": outcome, "why": why, "peak": peak, "mode": mode,
                                         "seconds": seconds}, ensure_ascii=False, default=float), encoding="utf-8")
        row = row_of(code, path, found, outcome, why, mode, seconds, peak)
        rows.append(row)
        print(" ".join(f"{k}={row[k]}" for k in ("id", "mb", "schema", "esito", "s", "gb", "corpi", "falde", "ostacoli",
                                                  "oltre_m", "fiducia", "come", "motivo")), flush=True)
        write(corpus / "banco" / f"{args.label}.csv", rows)
    summary(rows)
    return 0


def write(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _num(v) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def summary(rows: list[dict]) -> dict:
    """The aggregated numbers (no name of any model): what may be written in the repository."""
    n = len(rows)
    out = {"modelli": n}
    for key in ("ok", "vuoto", "file", "crash", "tempo", "memoria", "piano", "salva"):
        out[key] = sum(1 for r in rows if r["esito"] == key)
    good = [r for r in rows if r["esito"] == "ok"]

    def count(key, limit):
        return sum(1 for r in good if (_num(r[key]) or 0.0) > limit)
    out.update(sito_mosso=sum(1 for r in good if str(r["sito_fermo"]) == "0"), buco_30cm=count("buco_m", 0.3),
               oltre_1m=count("oltre_m", 1.0), fuori_5pct=count("fuori_pct", 5.0), scoperto_5pct=count("scoperto_pct", 5.0),
               sovrapp_5pct=count("sovrapp_pct", 5.0), dz_10cm=count("dz_m", 0.1),
               area_fuori_5pct=sum(1 for r in good if _num(r["area_pct"]) is not None
                                   and abs(_num(r["area_pct"]) - 100.0) > 5.0),
               muri_fuori=count("muri_fuori", 0.0), sito_inaffidabile=sum(1 for r in good if r["fiducia"] in ("default",)),
               come_origin=sum(1 for r in good if r["come"] == "origin"),
               con_sospesi=count("sospesi", 0.0), sospesi=int(sum(_num(r["sospesi"]) or 0 for r in good)), s_max=max((_num(r["s"]) or 0 for r in rows), default=0),
               gb_max=max((_num(r["gb"]) or 0 for r in rows), default=0))
    print(json.dumps(out, ensure_ascii=False))
    return out


def compare(corpus: Path, a: str, b: str) -> int:
    def load(label):
        with (corpus / "banco" / f"{label}.csv").open(encoding="utf-8", newline="") as fh:
            return {r["id"]: r for r in csv.DictReader(fh)}
    ra, rb = load(a), load(b)
    print("aggregato", a)
    summary(list(ra.values()))
    print("aggregato", b)
    summary(list(rb.values()))
    keys = ("esito", "corpi", "falde", "ostacoli", "oltre_m", "buco_m", "fuori_pct", "scoperto_pct", "sovrapp_pct", "area_pct", "dz_m",
            "alt_m", "come", "fiducia")
    for code in sorted(set(ra) | set(rb)):
        x, y = ra.get(code, {}), rb.get(code, {})
        diff = [f"{k}: {x.get(k)} > {y.get(k)}" for k in keys if x.get(k) != y.get(k)]
        if diff:
            print(code, "; ".join(diff))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    ap.add_argument("--label", default="ultimo")
    ap.add_argument("--reuse", default="", help="the label of a run whose readings are used again (no reading)")
    ap.add_argument("--only", default="", help="codes, separated by commas")
    ap.add_argument("--timeout", type=float, default=BUDGET_S)
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"))
    args = ap.parse_args(argv)
    if args.compare:
        return compare(Path(args.corpus), *args.compare)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
