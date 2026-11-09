"""The reading of an IFC model in a process of its own (study 20, section 4): the window starts it, reads its lines and
kills it at Cancel, past the time allowed or past the memory allowed. IfcOpenShell's C++ can loop or crash on a broken
model; here that ends this process, never the window.

    python -m meridiana.ifc_worker FILE [--mode direct|filtered|all|boxes]

stdout, one JSON object per line:
    {"progress": 0.42, "what": "roofs"}        while reading
    {"result": {...}}                          at the end: what ifc_read.read found
    {"error": "...", "kind": "file"}           a file that is not IFC (exit code 2), or another failure (exit code 3)
"""

from __future__ import annotations

import argparse
import json
import sys


def say(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, default=float) + "\n")
    sys.stdout.flush()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="meridiana.ifc_worker")
    ap.add_argument("file")
    ap.add_argument("--mode", default="direct")
    ap.add_argument("--budget", type=float, default=None, help="seconds after which the shapes left are given up")
    ap.add_argument("--context", default=None, help="folder for the true geometry of the model (ifc_mesh, the 3D)")
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    from . import ifc_read, resources
    resources.contain_children()        # the scan's processes end with this one, killed or not
    resources.raise_priority()          # the designer waits for this: before the year the project computes meanwhile
    last = [-1.0, ""]

    def progress(fraction: float, what: str) -> None:
        if fraction - last[0] >= 0.01 or fraction >= 1.0 or what != last[1]:
            last[0], last[1] = fraction, what
            say({"progress": round(float(fraction), 3), "what": what})
    try:
        result = read(args.file, args.mode, progress, args.budget, args.context)
    except ifc_read.IfcError as error:
        say({"error": str(error), "kind": "file"})
        return 2
    except Exception as error:          # noqa: BLE001  the process's boundary: a damaged file is said, not a crash
        say({"error": f"{type(error).__name__}: {error}", "kind": "read"})
        return 3
    text = json.dumps(result, ensure_ascii=False, default=float)
    if len(text) > RESULT_FILE:
        # R400: a large result (the solids of a big model) through a file the window reads and removes
        import tempfile
        fd, path = tempfile.mkstemp(prefix="meridiana-ifc-", suffix=".json")
        with open(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        say({"result_file": path})
    else:
        sys.stdout.write('{"result": ' + text + "}\n")
        sys.stdout.flush()
    return 0


RESULT_FILE = 1 << 20           # characters: a result larger than this goes through a file


ROOF_TYPES = ("IFCROOF", "IFCSLAB", "IFCSLABSTANDARDCASE", "IFCWALL", "IFCWALLSTANDARDCASE", "IFCCOVERING")
IFCOS_LIMIT = 400 << 20     # bytes: past this the roofs are not looked for through IfcOpenShell (R400: 56 s and 4.7 GB
                            # only to open the large test IFC's 1.6 GB lazily), the model comes in as solids


def compact(e) -> dict:
    """One element of the scan as the window needs it (JSON)."""
    return {"id": e.id, "cls": e.cls, "name": e.name, "group": e.group, "gname": e.group_name, "storey": e.storey,
            "z0": e.lo[2], "z1": e.hi[2], "hull": e.hull}


def context_file(folder: str, path: str) -> str:
    """Where the true geometry of the IFC at `path` is kept: one file for each file, size and date."""
    import hashlib
    import os
    st = os.stat(path)
    key = hashlib.sha1(f"{os.path.abspath(path)}|{st.st_size}|{st.st_mtime_ns}".encode()).hexdigest()[:20]
    return os.path.join(folder, f"ifc-{key}.npz")


def context(scanned, path: str, folder: str, progress) -> dict:
    """The true geometry of the model (ifc_mesh) for the 3D, written once in `folder`: {"mesh": file, "triangles",
    "vertices", "seconds"}; {} when it cannot be written."""
    import os

    from . import ifc_mesh
    target = context_file(folder, path)
    if not os.path.exists(target):
        mesh = ifc_mesh.build(scanned, lambda f: progress(f, "context"))
        os.makedirs(folder, exist_ok=True)
        part = target + ".part.npz"
        ifc_mesh.save(part, mesh)
        os.replace(part, target)
        info = {"triangles": int(len(mesh["faces"])), "vertices": int(len(mesh["vertices"])),
                "seconds": round(float(mesh["seconds"]), 3), "pieces": int(len(mesh["pieces"]))}
        del mesh
    else:
        import numpy as np
        with np.load(target) as z:
            info = {"triangles": int(z["faces"].shape[0]), "vertices": int(z["vertices"].shape[0]), "seconds": 0.0,
                    "pieces": int(z["pieces"].shape[0])}
    return {"mesh": target, **info}


def result_file(folder: str, path: str) -> str:
    """Where the whole answer for the model at `path` is kept (next to its geometry), for the scan alone: one file for
    each file, size, date and version of the code that reads it."""
    import hashlib
    from pathlib import Path
    src = Path(__file__).parent
    code = hashlib.sha1(b"".join((src / name).read_bytes() for name in ("ifc_scan.py", "ifc_mesh.py", "ifc_worker.py"))
                        ).hexdigest()[:8]
    return context_file(folder, path).replace(".npz", f".read-{code}.json")


def cached_result(path: str, context_folder: str | None) -> dict | None:
    """The answer kept by an earlier reading of the same model (r24: the second reading of the large test IFC's 1.6 GB took 23 s
    for the file read again), when its geometry is still there; None otherwise."""
    import json
    import os
    if not context_folder or not os.path.exists(path):
        return None
    try:
        if os.path.getsize(path) <= IFCOS_LIMIT or str(path).lower().endswith(".ifczip"):
            return None
        with open(result_file(context_folder, path), encoding="utf-8") as fh:
            result = json.load(fh)
        if not os.path.exists((result.get("context") or {}).get("mesh", "")):
            return None
        return result
    except (OSError, ValueError, KeyError):
        return None


def keep_result(result: dict, path: str, context_folder: str | None) -> None:
    """Keep the answer of a model read by the scan alone with its geometry, for `cached_result`."""
    import json
    import os
    if not context_folder or result.get("mode") != "scan" or not result.get("context") or result.get("errors"):
        return
    try:
        target = result_file(context_folder, path)
        part = target + ".part"
        with open(part, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, default=float)
        os.replace(part, target)
    except (OSError, TypeError, ValueError):
        pass


def read(path: str, mode: str, progress, budget: float | None, context_folder: str | None = None) -> dict:
    """R400: first the fast scan (ifc_scan, several processes, the bytes read as the progress), then, when the model
    has roofs, slabs or walls and is not too large, ifc_read through IfcOpenShell as before; the solids of the scan
    always go with the result (`solids`, `listing`), for the window's simplified import."""
    import os
    import time

    from . import ifc_read, ifc_scan
    t0 = time.perf_counter()
    kept = cached_result(path, context_folder)
    if kept is not None:
        kept.setdefault("times", {})["cached"] = round(time.perf_counter() - t0, 3)
        progress(1.0, "done")
        return kept
    scanned = None
    if not str(path).lower().endswith(".ifczip"):
        try:
            # a model beyond IFCOS_LIMIT is the scan alone: its bytes are the whole bar
            share = 1.0 if os.path.getsize(path) > IFCOS_LIMIT else 0.3
            scanned = ifc_scan.scan(path, lambda f, w: progress(share * f, w))
        except ifc_scan.ScanError as error:
            raise ifc_read.IfcError(str(error)) from None
        except (MemoryError, OSError, ValueError, IndexError, KeyError, TypeError) as error:
            progress(0.3, "scan_failed")
            scanned = None
            failed = f"{type(error).__name__}: {error}"
        else:
            failed = ""
    else:
        failed = ""
    roofs = scanned is None or any(scanned.counts.get(t) for t in ROOF_TYPES)
    if roofs and (scanned is None or os.path.getsize(path) <= IFCOS_LIMIT):
        left = None if budget is None else max(10.0, budget - (time.perf_counter() - t0))
        result = ifc_read.read(path, mode=mode, progress=lambda f, w: progress(0.3 + 0.7 * f, w), budget_s=left)
    else:
        result = {"schema": scanned.schema, "unit_m": scanned.unit_m, "mode": "scan", "application": "",
                  "buildings": [], "obstacles": [], "supports": [], "notes": [], "counts": {}, "errors": [],
                  "storeys": {}, "address": "", "site": None, "true_north": 0.0, "map": None, "sites": 0}
        site = scanned.site or {}
        if site.get("lat") is not None and site.get("lon") is not None:
            result["site"] = {"lat": site["lat"], "lon": site["lon"], "elevation": site.get("elevation") or 0.0,
                              "name": site.get("name") or "", "placement": [0.0, 0.0, 0.0]}
            result["sites"] = 1
        if roofs:
            result["notes"].append("large")
    if scanned is not None:
        listing = scanned.listing()
        result["listing"] = listing
        result["solids"] = [compact(e) for e in scanned.elements]
        levels = [z for _n, z in scanned.storeys.values() if z is not None]
        result["solids_ground"] = min(levels) if levels and min(levels) <= 0.5 else 0.0
        result.setdefault("times", {})["scan"] = round(listing["times"].get("total", 0.0), 3)
        if context_folder:
            # r21-ifc-vista: the triangles the scan has read, for the 3D (the bodies stay for the calculation)
            t = time.perf_counter()
            try:
                result["context"] = context(scanned, path, context_folder, progress)
            except (MemoryError, OSError, ValueError, IndexError) as error:
                result.setdefault("errors", []).append(f"context: {type(error).__name__}: {error}")
            result["times"]["context"] = round(time.perf_counter() - t, 3)
    if failed:
        result.setdefault("errors", []).append(f"scan: {failed}")
    result.setdefault("times", {})["worker"] = round(time.perf_counter() - t0, 3)
    keep_result(result, path, context_folder)
    progress(1.0, "done")
    return result


if __name__ == "__main__":
    sys.exit(main())
