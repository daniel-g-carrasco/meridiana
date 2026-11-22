"""The reading of an IFC model in a process of its own (study 20, section 4): the window starts it, reads its lines and
kills it at Cancel, past the time allowed or past the memory allowed. IfcOpenShell's C++ can loop or crash on a broken
model; here that ends this process, never the window.

    python -m meridiana.app.exchange.ifc_worker FILE [--mode direct|filtered|all|boxes]

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
    ap = argparse.ArgumentParser(prog="meridiana.app.exchange.ifc_worker")
    ap.add_argument("file")
    ap.add_argument("--mode", default="direct")
    ap.add_argument("--budget", type=float, default=None, help="seconds after which the shapes left are given up")
    ap.add_argument("--context", default=None, help="folder for the true geometry of the model (ifc_mesh, the 3D)")
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    import faulthandler
    faulthandler.enable()               # a crash of IfcOpenShell says where on stderr: the window keeps its last lines
    from . import ifc_read
    from meridiana.core.compute import resources
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
GIB = 1 << 30
# R34: whether the whole reading (the roofs through IfcOpenShell) is tried depends on the memory, not on a size fixed once
ROOFS_MEMORY = 6.5          # its peak over the file's size: 5.0 to 6.2 measured (471 MB: 2.2 GiB, 1359 MB: 7.86 GiB)
MEMORY_GUARD = 0.9          # share of procmem.limit() past which the whole reading is left for the scan's solids
TIME_GUARD = 1.2            # share of --budget past which the same (the window kills at budget / 0.7: time to answer)
GUARD_EVERY = 0.5           # s between two looks at the memory


def allowed_memory() -> int:
    """The memory the whole reading may take, bytes: the lower of the worker's limit (procmem.limit, what the window
    kills it at) and the program's budget of memory now (resources.budget: free less the reserve of the designer's
    choice, MERIDIANA_MEMORY_MODE)."""
    from meridiana.core.compute import procmem, resources
    return min(procmem.limit(), resources.budget().bytes())


def fits(path: str) -> tuple[bool, int, int]:
    """(whether the whole reading of the model at `path` is tried, the memory it is reckoned to take, the memory
    allowed), bytes: the file's size times ROOFS_MEMORY within `allowed_memory`. The one rule: the progress, the kept
    answer and the reading ask it here."""
    import os
    need = int(os.path.getsize(path) * ROOFS_MEMORY)
    allowed = allowed_memory()
    return need <= allowed, need, allowed


class Leave(Exception):
    """The whole reading left by the guard ("memory" or "time"): the scan's solids answer instead. Not a RuntimeError
    nor any of the errors ifc_read takes as a step that failed: it goes out of ifc_read as it is."""

    def __init__(self, why: str):
        super().__init__(why)
        self.why = why


class Guard:
    """The guard of the whole reading (R34): a thread looks at the memory of this process and its children every
    GUARD_EVERY s (what the window measures) and raises a signal past MEMORY_GUARD of procmem.limit(); the checkpoint
    given to ifc_read raises Leave when the signal is up, or past `deadline` (perf_counter, None: no limit of time).
    IfcOpenShell holds the interpreter while it opens the file: the guard sees what happened at its next look, and a
    jump past the window's limit during the opening is still the window's to stop."""

    def __init__(self, deadline: float | None):
        import threading

        from meridiana.core.compute import procmem
        self.deadline = deadline
        self.limit = int(MEMORY_GUARD * procmem.limit())
        self.peak = 0
        self.over = threading.Event()
        self.done = threading.Event()
        self.check_memory()             # once before the thread: a reading shorter than its first look is guarded too
        self.thread = threading.Thread(target=self._watch, name="ifc-guard", daemon=True)
        self.thread.start()

    def check_memory(self) -> None:
        import os

        from meridiana.core.compute import procmem
        used = procmem.rss(os.getpid(), tree=True)
        if used is not None:
            self.peak = max(self.peak, used)
            if used > self.limit:
                self.over.set()

    def _watch(self) -> None:
        while not self.done.wait(GUARD_EVERY):
            self.check_memory()
            if self.over.is_set():
                return

    def checkpoint(self, outer):
        """The checkpoint for ifc_read: the caller's first (what it raises goes out), then the guard's."""
        import time

        def check() -> None:
            outer()
            if self.over.is_set():
                raise Leave("memory")
            if self.deadline is not None and time.perf_counter() > self.deadline:
                raise Leave("time")
        return check

    def stop(self) -> None:
        self.done.set()


def compact(e) -> dict:
    """One element of the scan as the window needs it (JSON)."""
    return {"id": e.id, "cls": e.cls, "name": e.name, "group": e.group, "gname": e.group_name, "storey": e.storey,
            "z0": e.lo[2], "z1": e.hi[2], "hull": e.hull, **({"terrain": True} if e.terrain else {}),
            **({"grating": True} if e.grating else {})}


MESH_VERSION = 6       # R575 D5: the faces closed in their plane; D9: openings and clippings cut; R608 (4): each item
#                       in its own colour; R608 (5): the gratings named (ifc_grating); (6) the gratings opaque, so that
#                       they cast their shadow in the 3D. A geometry written before is made again on import


def context_file(folder: str, path: str) -> str:
    """Where the true geometry of the IFC at `path` is kept: one file for each file, size, date and way of making it
    (a project imported before keeps the file it names)."""
    import hashlib
    import os
    st = os.stat(path)
    key = hashlib.sha1(f"{os.path.abspath(path)}|{st.st_size}|{st.st_mtime_ns}".encode()).hexdigest()[:20]
    return os.path.join(folder, f"ifc-{key}-m{MESH_VERSION}.npz")


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
    code = hashlib.sha1(b"".join((src / name).read_bytes() for name in ("ifc_scan.py", "ifc_mesh.py", "ifc_worker.py",
                                                                         "ifc_terrain.py", "ifc_ground.py",
                                                                         "ifc_grating.py"))
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
        if str(path).lower().endswith(".ifczip"):
            return None
        fit, need, allowed = fits(path)
        if fit:
            return None             # the whole reading is tried: what was kept by the scan alone is not the answer
        with open(result_file(context_folder, path), encoding="utf-8") as fh:
            result = json.load(fh)
        if not os.path.exists((result.get("context") or {}).get("mesh", "")):
            return None
        counts = result.setdefault("counts", {})
        if counts.get("roofs_skipped") == "memory":
            # the numbers of now, not those of the reading that kept it
            counts.update(memory_need_gb=round(need / GIB, 1), memory_allowed_gb=round(allowed / GIB, 1))
        return result
    except (OSError, ValueError, KeyError):
        return None


def keep_result(result: dict, path: str, context_folder: str | None) -> None:
    """Keep the answer of a model read by the scan alone with its geometry, for `cached_result`: not when the scan
    alone came from the guard or from the time (R34: an answer of a busy moment, not the model's)."""
    import json
    import os
    if not context_folder or result.get("mode") != "scan" or not result.get("context") or result.get("errors"):
        return
    counts = result.get("counts") or {}
    if counts.get("roofs_stopped") or counts.get("roofs_skipped") == "time":
        return
    try:
        target = result_file(context_folder, path)
        part = target + ".part"
        with open(part, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, default=float)
        os.replace(part, target)
    except (OSError, TypeError, ValueError):
        pass


def model_ground(result: dict, scanned) -> tuple[float, str]:
    """(height, storey) of the model's zero in its world, in metres: what the solids and the true geometry stand on
    above Meridiana's ground (R575 D2). The ground of the buildings read from the roofs when there are some (ifc_read:
    the ground floor of the first building), else the storey at the building's zero or just below it by its placement
    (its Elevation attribute is measured from the building, which a model may place high: 0.26 m against 84.67 m in
    the world), else the lowest one, else the lowest point of the solids."""
    for raw in result.get("buildings") or []:
        if raw.get("ground") is not None:
            return float(raw["ground"]), str(raw.get("ground_storey") or "")
    storeys = [(level, *scanned.storeys.get(rid, ("", None))) for rid, level in scanned.levels.items()]
    if storeys:
        # the Elevation attribute says which storey is the ground floor, the placement where it is
        floor = [s for s in storeys if s[2] is not None and s[2] <= 0.05]
        level, name, _attribute = max(floor, key=lambda s: s[2]) if floor else min(storeys, key=lambda s: s[0])
        return float(level), str(name or "")
    lows = [float(e.lo[2]) for e in scanned.elements]
    return (min(lows) if lows else 0.0), ""


def site_ground(result: dict, scanned) -> dict | None:
    """R602: the model's zero from its site (ifc_ground.zero: its terrain at the foot of the buildings, else its pavings
    at the ground), with the plan of its terrain ("outline") and the faces of its top ("surface",
    ifc_ground.top_surface); None when the site gives none of them and the ground floor stays (`solids_ground`). The
    answer's key `site_ground`; ifc_import.plan takes it (ifc_ground.grounded), a reader that ignores it keeps the
    ground floor."""
    from . import ifc_ground
    try:
        # the scan's triangles are in the file's units (ifc_scan.Model.element_triangles)
        terrain = [scanned.triangles(e.id) * scanned.unit_m for e in scanned.elements if e.terrain]
        out = ifc_ground.zero(float(result["solids_ground"]), result.get("buildings") or [],
                              result.get("solids") or [], terrain) or {}
        outline = ifc_ground.terrain_outline(terrain)       # where the lawn opens when the terrain is drawn
        if outline:
            out["outline"] = outline
        surface = ifc_ground.top_surface(terrain)           # the lawn on the site, made of the terrain's top
        if surface:
            out["surface"] = surface
        return out or None
    except (MemoryError, ValueError, IndexError, KeyError, TypeError) as error:
        result.setdefault("errors", []).append(f"site ground: {type(error).__name__}: {error}")
        return None


def read(path: str, mode: str, progress, budget: float | None, context_folder: str | None = None,
         checkpoint=None) -> dict:
    """R400: first the fast scan (ifc_scan, several processes, the bytes read as the progress), then, when the model
    has roofs, slabs or walls and its whole reading fits the memory (`fits`), ifc_read through IfcOpenShell as before,
    with the points of the scan (R34: the walls and what is placed below the roofs are not read again through
    IfcOpenShell); the solids of the scan always go with the result (`solids`, `listing`), for the window's simplified
    import. A model whose whole reading is not tried, or is left by the guard (`Guard`: the memory, and the time when
    `budget` is given), comes in as those solids, and `counts` says why ("roofs_skipped", "roofs_stopped").
    `checkpoint()`: called between the phases and inside ifc_read's long loops; what it raises (resources.Stopped)
    goes out of here."""
    import gc
    import time

    from . import ifc_read, ifc_scan
    check = checkpoint or (lambda: None)
    t0 = time.perf_counter()
    kept = cached_result(path, context_folder)
    if kept is not None:
        kept.setdefault("times", {})["cached"] = round(time.perf_counter() - t0, 3)
        progress(1.0, "done")
        return kept
    scanned = None
    failed = ""
    fit, need, allowed = True, 0, 0
    if not str(path).lower().endswith(".ifczip"):
        try:
            fit, need, allowed = fits(path)
            # a model whose whole reading is not tried is the scan alone: its bytes are the whole bar
            share = 0.3 if fit else 1.0
            scanned = ifc_scan.scan(path, lambda f, w: progress(share * f, w))
        except ifc_scan.ScanError as error:
            raise ifc_read.IfcError(str(error)) from None
        except (MemoryError, OSError, ValueError, IndexError, KeyError, TypeError) as error:
            progress(0.3, "scan_failed")
            scanned = None
            failed = f"{type(error).__name__}: {error}"
    check()
    roofs = scanned is None or any(scanned.counts.get(t) for t in ROOF_TYPES)
    why: dict = {}                  # why the roofs were not read, for `counts` (ifc_import says it)
    if roofs and scanned is not None:
        if not fit:
            why = {"roofs_skipped": "memory", "memory_need_gb": round(need / GIB, 1),
                   "memory_allowed_gb": round(allowed / GIB, 1)}
        elif budget is not None and time.perf_counter() - t0 > budget / 2:
            # the scan alone took more than half the time: the whole reading would not end in the rest
            why = {"roofs_skipped": "time", "scan_s": round(time.perf_counter() - t0, 1), "budget_s": budget}
    result = None
    if roofs and not why:
        left = None if budget is None else max(10.0, budget - (time.perf_counter() - t0))
        # the guard only where the scan's solids can answer instead: without them there is nothing to fall back on
        guard = Guard(t0 + budget * TIME_GUARD if budget is not None else None) if scanned is not None else None
        try:
            result = ifc_read.read(path, mode=mode, progress=lambda f, w: progress(0.3 + 0.7 * f, w), budget_s=left,
                                   points=scanned.points if scanned is not None else None,
                                   checkpoint=guard.checkpoint(check) if guard is not None else check)
        except Leave as stop:
            why = {"roofs_stopped": stop.why, "stopped_s": round(time.perf_counter() - t0, 1),
                   "memory_peak_gb": round(guard.peak / GIB, 1), "memory_limit_gb": round(guard.limit / GIB, 1)}
            result = None
        finally:
            if guard is not None:
                guard.stop()
        if result is None:
            gc.collect()            # what the whole reading held, before the solids are made
    if result is None:
        result = {"schema": scanned.schema, "unit_m": scanned.unit_m, "mode": "scan", "application": "",
                  "buildings": [], "obstacles": [], "supports": [], "notes": [], "counts": dict(why), "errors": [],
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
        result["solids_ground"], result["ground_from"] = model_ground(result, scanned)
        result["site_ground"] = site_ground(result, scanned)
        result.setdefault("times", {})["scan"] = round(listing["times"].get("total", 0.0), 3)
        check()
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
