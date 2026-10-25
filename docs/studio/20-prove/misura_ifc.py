"""Study 20: the ways of reading an IFC model for the PV design, measured on public samples (time, peak memory, what
Meridiana gets). Each run is a process of its own, killed past the time allowed: as the program does (ifc_worker.py).

    python misura_ifc.py campioni.json CACHE --out risultati.json [--repeat 3] [--timeout 300] [--only NAME]
    python misura_ifc.py --sintetico CACHE         the synthetic files: the Clinic's plumbing four times, a truncated
                                                    Duplex, a text that is not IFC, an empty file

CACHE is the folder of the samples (outside the repository: they are not committed). The ways (study 20, 2):
    open-normal, open-lazy     opening only (the cost of the parser)
    a                          the iterator on every product, openings subtracted, 8 threads (the baseline)
    b8                         the iterator on what the PV needs only, no openings, 8 threads, full open
    b1                         the same with a lazy open and one thread (the threads crash on a lazy file)
    c                          the simple shapes read directly, the rest through the iterator (b1): the program's way
    d                          the points of the bodies only, no faces

GPL-3.0-or-later, as Meridiana."""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[2] / "src"
WAYS = {"open-normal": ("open", False, 1), "open-lazy": ("open", True, 1), "a": ("all", False, 8),
        "b8": ("filtered", False, 8), "b1": ("filtered", True, 1), "c": ("direct", True, 1), "d": ("boxes", True, 1)}


def one(path: str, way: str) -> dict:
    """In the child: one way on one file, its summary as one JSON line."""
    sys.path.insert(0, str(SRC))
    from meridiana import ifc_read, procmem
    mode, lazy, threads = WAYS[way]
    t = time.perf_counter()
    if mode == "open":
        f = ifc_read.open_model(path, lazy=lazy)
        n = len(f.by_type("IfcProduct"))
        out = {"products": n}
    else:
        r = ifc_read.read(path, mode=mode, lazy=lazy, threads=threads)
        pitches = [p for b in r["buildings"] for p in b["pitches"]]
        sloped = [p for p in pitches if p["normal"][2] < math.cos(math.radians(0.5))]
        out = {"buildings": len(r["buildings"]), "pitches": len(pitches), "sloped": len(sloped),
               "pitch_area": round(sum(p["area"] for p in pitches), 1),
               "tilts": sorted({round(math.degrees(math.acos(min(1.0, p["normal"][2])))) for p in sloped})[:8],
               "obstacles": len(r["obstacles"]), "kinds": sorted({o["kind"] for o in r["obstacles"]}),
               "heights": sorted({round(max(p["point"][2] for p in b["pitches"]) - b["ground"], 1)
                                  for b in r["buildings"]})[:8],
               "sources": sorted({b["source"] for b in r["buildings"]}), "site": r["site"] is not None,
               "map": (r["map"] or {}).get("crs"), "north": round(r["true_north"], 2), "unit_m": r["unit_m"],
               "schema": r["schema"], "application": r["application"], "counts": r["counts"], "times": r["times"],
               "errors": r["errors"][:3]}
    out["seconds"] = round(time.perf_counter() - t, 3)
    out["peak_mb"] = round((procmem.peak() or 0) / 2 ** 20, 1)
    return out


MEMORY_GB = 8.0


def run(path: Path, way: str, timeout: float) -> dict:
    """In the parent: the child for one way, watched: its time, its exit, the most memory seen; stopped past `timeout`
    seconds or MEMORY_GB, as the program stops its worker."""
    sys.path.insert(0, str(SRC))
    from meridiana import procmem
    cmd = [sys.executable, "-I", "-X", "faulthandler", str(Path(__file__).resolve()), "--one", str(path), way]
    t = time.perf_counter()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                         errors="replace")
    seen = 0
    killed = False
    while p.poll() is None:
        seen = max(seen, procmem.rss(p.pid, tree=True) or 0)     # the venv's launcher and its interpreter
        if time.perf_counter() - t > timeout or seen > MEMORY_GB * 2 ** 30:
            p.kill()
            killed = "time" if time.perf_counter() - t > timeout else "memory"
            break
        time.sleep(0.1)
    out_text, err_text = p.communicate()
    wall = time.perf_counter() - t
    row = {"way": way, "wall": round(wall, 3), "exit": p.returncode, "rss_seen_mb": round(seen / 2 ** 20, 1)}
    if killed:
        row["status"] = f"stopped after {timeout:.0f} s" if killed == "time" else f"stopped at {MEMORY_GB:.0f} GB"
        return row
    lines = [ln for ln in out_text.splitlines() if ln.startswith("{")]
    if p.returncode == 0 and lines:
        row.update(json.loads(lines[-1]))
        row["status"] = "ok"
    else:
        tail = [ln for ln in err_text.splitlines() if ln.strip()][-3:]
        row["status"] = "error" if p.returncode in (1, 2, 3) else f"crash (exit {p.returncode})"
        row["stderr"] = tail
    return row


def measure(samples: list, cache: Path, ways: list, repeat: int, timeout: float, only: str = "") -> list:
    rows = []
    for s in samples:
        if only and s["name"] != only:
            continue
        path = cache / s["file"]
        if not path.exists():
            print("missing", path, file=sys.stderr)
            continue
        for way in ways:
            runs = [run(path, way, timeout) for _i in range(repeat if s.get("repeat", True) else 1)]
            good = [r for r in runs if r.get("status") == "ok"]
            best = dict(good[len(good) // 2] if good else runs[-1])
            if good:
                best["seconds_median"] = round(statistics.median(r["seconds"] for r in good), 3)
                best["seconds_all"] = [r["seconds"] for r in good]
                best["peak_mb_max"] = max(r.get("peak_mb", 0) for r in good)
            best["runs"] = len(runs)
            best["statuses"] = [r["status"] for r in runs]
            best["sample"] = s["name"]
            rows.append(best)
            print(s["name"], way, best.get("statuses"), best.get("seconds_median"), best.get("peak_mb_max"),
                  {k: best.get(k) for k in ("buildings", "pitches", "sloped", "obstacles")}, flush=True)
    return rows


def synthetic(cache: Path) -> None:
    """The synthetic files of the robustness trials (none is committed)."""
    import re
    src = cache / "clinic-plumbing" / "Clinic_Plumbing.ifc"
    out_dir = cache / "sintetico"
    out_dir.mkdir(exist_ok=True)
    text = src.read_text(encoding="latin-1")
    head, _sep, rest = text.partition("DATA;")
    data, _sep, _tail = rest.rpartition("ENDSEC;")
    top = max(int(m) for m in re.findall(r"^#(\d+)\s*=", data, re.M))
    ref = re.compile(r"#(\d+)")
    with open(out_dir / "Clinic_Plumbing_x4.ifc", "w", encoding="latin-1", newline="\n") as fh:
        fh.write(head + "DATA;")
        for k in range(4):
            fh.write(ref.sub(lambda m, k=k: f"#{int(m.group(1)) + k * top}", data) if k else data)
        fh.write("ENDSEC;\nEND-ISO-10303-21;\n")
    duplex = (cache / "duplex" / "Duplex_A_20110907.ifc").read_bytes()
    (out_dir / "Duplex_troncato.ifc").write_bytes(duplex[: len(duplex) // 2])
    (out_dir / "non_ifc.ifc").write_text("Questo non è un file IFC.\n" * 100, encoding="utf-8")
    (out_dir / "vuoto.ifc").write_bytes(b"")
    for f in sorted(out_dir.iterdir()):
        print(f.name, f.stat().st_size)


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--one":
        print(json.dumps(one(sys.argv[2], sys.argv[3]), default=float))
        return 0
    ap = argparse.ArgumentParser()
    ap.add_argument("samples", nargs="?")
    ap.add_argument("cache", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--ways", default=",".join(WAYS))
    ap.add_argument("--only", default="")
    ap.add_argument("--sintetico")
    args = ap.parse_args()
    if args.sintetico:
        synthetic(Path(args.sintetico))
        return 0
    samples = json.loads(Path(args.samples).read_text(encoding="utf-8"))["campioni"]
    rows = measure(samples, Path(args.cache), args.ways.split(","), args.repeat, args.timeout, args.only)
    if args.out:
        old = []
        if Path(args.out).exists() and args.only:
            old = [r for r in json.loads(Path(args.out).read_text(encoding="utf-8"))["righe"]
                   if r["sample"] != args.only]
        Path(args.out).write_text(json.dumps({"macchina": machine(), "righe": old + rows}, indent=1,
                                             ensure_ascii=False, default=float), encoding="utf-8")
    return 0


def machine() -> dict:
    import platform
    sys.path.insert(0, str(SRC))
    from meridiana import ifc_read, procmem
    return {"python": platform.python_version(), "system": platform.platform(), "cpus": os.cpu_count(),
            "ram_gb": round((procmem.physical() or 0) / 2 ** 30, 1), "ifcopenshell": ifc_read.available(),
            "date": time.strftime("%Y-%m-%d %H:%M")}


if __name__ == "__main__":
    sys.exit(main())
