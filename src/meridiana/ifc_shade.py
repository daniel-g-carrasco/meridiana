"""The shadows of an imported IFC model's true geometry on the modules (r22-ifc, R400 and R453). Without Qt.

The import makes simple bodies (an outline and two heights) and keeps the model's triangles for the 3D (`ifc_mesh`, the
file in `ifc_reference.context.mesh`). With the option on (`ifc_reference.shade`, chosen in the import window: «the
shapes of the model cast shadows»), the calculation takes the model's elements as its shading solids instead of the
import's bodies: for each element the convex hull of its points, which holds the element whole (never less shadow than
the true one); a hull of more than MAX_CORNERS corners becomes the 26-sided box around it (the planes of the 13
directions of the axes, of the faces' and of the body's diagonals, each pushed to the hull's farthest point: it holds
the hull, so the element). A non-convex element (an L of pipes) casts more than its own shadow: on the safe side.

Only the elements that can matter go to a sub-field: their top above the lowest point of the sub-field's surface and
their plan box within `reach` metres of the sub-field's (None: the whole model). The hulls are made once for each mesh
file and kept next to it (`<mesh>-shade-<VERSION>.npz`), in the model's world metres: a move or a turn of the import
only changes where they are put (`ifc_export.frame_of`, the anchor body), as the 3D does (quick/backend/scene_context).

    hulls = of_mesh(mesh)                 # {"ids", "start", "corners", "lo", "hi"}
    solids = solids_for(project, sf)     # nearshade.Solid, in the plan, [] when the option is off

The model's elements are what a viewer would pick too (study 40): the same `elements` rows of the mesh."""

from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np

VERSION = 1
MAX_CORNERS = 48               # a 26-sided box has at most 48 corners: above that the box is the lighter
REACHES = (20.0, 50.0)         # the window's choices, metres around the sub-field (and the whole model)
GROW = 0.001                   # m: the hull pushed outwards, for the float32 of the mesh's vertices
MAX_SOLIDS = 400               # solids for one sub-field: beyond, the elements go together by cells (_grouped)
GROUP_CELL = 2.0               # m, the smallest cell
_DIRECTIONS = np.array([d for d in ((1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, -1, 0), (1, 0, 1), (1, 0, -1),
                                    (0, 1, 1), (0, 1, -1), (1, 1, 1), (1, 1, -1), (1, -1, 1), (-1, 1, 1))], float)
_DIRECTIONS /= np.linalg.norm(_DIRECTIONS, axis=1)[:, None]
_LOADED: dict = {}              # mesh file -> (stamp, hulls): the calculation asks once for each sub-field


def option(project) -> dict | None:
    """The import's shading option, {"reach": metres or None}, when it is on and the import has its true geometry."""
    ref = (getattr(project, "resources", None) or {}).get("ifc_reference")
    if not isinstance(ref, dict) or not isinstance(ref.get("context"), dict):
        return None
    shade = ref.get("shade")
    if not isinstance(shade, dict) or not shade.get("on"):
        return None
    reach = shade.get("reach")
    return {"reach": float(reach) if isinstance(reach, (int, float)) and reach > 0 else None}


def _hull_corners(points: np.ndarray) -> np.ndarray:
    """The corners of a convex solid that holds all `points` (n, 3): their hull, or the 26-sided box around it."""
    from scipy.spatial import ConvexHull, HalfspaceIntersection, QhullError
    pts = np.unique(np.round(points, 6), axis=0)
    lo, hi = pts.min(0), pts.max(0)
    box = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    if len(pts) < 4 or float(np.min(hi - lo)) < 1e-4:
        return _grow(box)               # flat or a line: its box (a flat plate's box is the plate)
    try:
        hull = ConvexHull(pts)
    except QhullError:
        return _grow(box)
    corners = pts[hull.vertices]
    if len(corners) <= MAX_CORNERS:
        return _grow(corners)
    reach = corners @ _DIRECTIONS.T                                      # (k, 13)
    upper, lower = reach.max(0), reach.min(0)
    halfspaces = np.vstack([np.column_stack([_DIRECTIONS, -upper]), np.column_stack([-_DIRECTIONS, lower])])
    try:
        cut = HalfspaceIntersection(halfspaces, corners.mean(0))
        dop = np.unique(np.round(cut.intersections, 6), axis=0)
    except (QhullError, ValueError):
        return _grow(box)
    return _grow(dop if len(dop) <= MAX_CORNERS and np.all(np.isfinite(dop)) else box)


def _grow(corners: np.ndarray) -> np.ndarray:
    middle = corners.mean(0)
    away = corners - middle
    length = np.linalg.norm(away, axis=1)
    return corners + away / np.where(length > 0, length, 1.0)[:, None] * GROW


def of_mesh(mesh: dict, cancelled=None) -> dict:
    """The shading hulls of a context mesh (ifc_mesh.build): `ids` (e,) the elements, `start` (e + 1,) where each one's
    corners begin in `corners` (n, 3, world metres), `lo` and `hi` (e, 3) their boxes."""
    ids, start, corners, lo, hi = [], [0], [], [], []
    centre = np.asarray(mesh["centre"], float)
    pieces, vertices, faces = mesh["pieces"], mesh["vertices"], mesh["faces"]
    for row, piece in zip(mesh["elements"], mesh["piece_of"], strict=True):
        if cancelled is not None and len(ids) % 256 == 0 and cancelled():
            break
        v0, _nv, f0, _nf = (int(x) for x in pieces[int(piece)])
        first, n = int(row[1]), int(row[2])
        if n <= 0:
            continue
        used = np.unique(faces[f0 + first:f0 + first + n].ravel()).astype(np.int64)
        pts = vertices[v0 + used].astype(np.float64) + centre
        c = _hull_corners(pts)
        ids.append(int(row[0]))
        corners.append(c)
        start.append(start[-1] + len(c))
        lo.append(pts.min(0))
        hi.append(pts.max(0))
    return {"version": np.int64(VERSION), "ids": np.array(ids, np.int64), "start": np.array(start, np.int64),
            "corners": np.concatenate(corners) if corners else np.zeros((0, 3)),
            "lo": np.array(lo, float).reshape(-1, 3), "hi": np.array(hi, float).reshape(-1, 3)}


def file_of(mesh_path) -> Path:
    p = Path(mesh_path)
    return p.with_name(f"{p.stem}-shade-{VERSION}.npz")


def load(mesh_path) -> dict | None:
    """The hulls of a mesh file, made and written next to it the first time (in memory after); None without it."""
    path = Path(mesh_path)
    try:
        st = path.stat()
    except OSError:
        return None
    stamp = (st.st_size, st.st_mtime_ns)
    hit = _LOADED.get(str(path))
    if hit is not None and hit[0] == stamp:
        return hit[1]
    target = file_of(path)
    hulls = None
    if target.is_file() and target.stat().st_mtime_ns >= st.st_mtime_ns:
        try:
            with np.load(target) as z:
                hulls = {k: z[k] for k in z.files}
        except (OSError, ValueError, KeyError):
            hulls = None
    if hulls is None:
        from . import ifc_mesh
        hulls = of_mesh(ifc_mesh.load(path))
        part = target.with_name(target.name + ".part.npz")
        try:
            np.savez(part, **hulls)
            os.replace(part, target)
        except OSError:
            pass                        # a folder not writable: made again next time
        finally:
            if part.exists():
                part.unlink()
    _LOADED.clear()                     # one model at a time: The large test IFC's hulls are a few MB
    _LOADED[str(path)] = (stamp, hulls)
    return hulls


def members(project) -> set:
    """The ids of the import's bodies (the anchor's group, Building.group): with the option on they cast no shadow of
    their own, the model's elements cast it."""
    ref = (getattr(project, "resources", None) or {}).get("ifc_reference") or {}
    anchor = next((b for b in project.buildings if b.id == (ref.get("anchor") or {}).get("building")), None)
    if anchor is None:
        return set()
    if not anchor.group:
        return {anchor.id}
    return {b.id for b in project.buildings if b.group == anchor.group}


def placed(project) -> tuple[dict, np.ndarray, np.ndarray, np.ndarray] | None:
    """The hulls in the plan, with the option on and the frame found: (hulls, corners (n, 3) in the plan, lo, hi of each
    element in the plan); None otherwise (then the import's bodies cast the shadows, as before)."""
    if option(project) is None:
        return None
    from . import ifc_export
    ref = project.resources["ifc_reference"]
    frame, _why = ifc_export.frame_of(project)
    path = ref["context"].get("mesh") or ""
    if frame is None or not path:
        return None
    hulls = load(path)
    if hulls is None or not len(hulls["ids"]):
        return None
    # world = R(phi) plan + move, so plan = R(-phi) (world - move); z from the model's ground (scene_context)
    phi = float(frame["turn"])
    mx, my = frame["move"]
    ground = float(ref["context"].get("ground") or 0.0)
    c, s = math.cos(phi), math.sin(phi)
    w = hulls["corners"]
    dx, dy = w[:, 0] - mx, w[:, 1] - my
    plan = np.column_stack([c * dx + s * dy, -s * dx + c * dy, w[:, 2] - ground])
    starts = hulls["start"][:-1]
    lo = np.minimum.reduceat(plan, starts, axis=0)
    hi = np.maximum.reduceat(plan, starts, axis=0)
    return hulls, plan, lo, hi


def _lowest(project, sf) -> float | None:
    """The lowest point of a sub-field's surface over its outline, plan metres; None without an outline."""
    if len(sf.ring) < 3:
        return None
    from .energy import nearshade
    surf = project.surface_of(sf)
    n, _e1, _e2 = nearshade.plane_axes(surf.tilt, surf.azimuth)
    d = float(n @ np.array([surf.x0, surf.y0, surf.z0]))
    return min((d - n[0] * x - n[1] * y) / n[2] for x, y in sf.ring)


def chosen(project, sf, where=None) -> np.ndarray:
    """The indices of the elements that may shade `sf`: their top above its lowest point, their plan box within the
    option's reach of its outline; all of them for a receiver without an outline (the plan's shadows)."""
    where = placed(project) if where is None else where
    if where is None:
        return np.zeros(0, np.int64)
    _hulls, _plan, lo, hi = where
    keep = np.ones(len(lo), bool)
    skip = (project.resources["ifc_reference"]["context"].get("skip") or [])
    if len(skip):                       # the storeys left out at the import
        keep &= ~np.isin(_hulls["ids"], np.asarray(skip, np.int64))
    low = _lowest(project, sf)
    if low is not None:
        keep &= hi[:, 2] > low + 1e-3
        reach = option(project)["reach"]
        if reach is not None:
            ring = np.asarray(sf.ring, float)
            (x0, y0), (x1, y1) = ring.min(0) - reach, ring.max(0) + reach
            keep &= (hi[:, 0] >= x0) & (lo[:, 0] <= x1) & (hi[:, 1] >= y0) & (lo[:, 1] <= y1)
    return np.flatnonzero(keep)


def shading(project, sf) -> tuple[list, set]:
    """What energy/system.obstacles_of takes: the model's solids for `sf` and the import's bodies they stand for (which
    cast no shadow then); ([], set()) when the option is off or the import's frame is lost."""
    where = placed(project)
    if where is None:
        return [], set()
    return solids_for(project, sf, where=where), members(project)


def solids_for(project, sf, name: str = "", where=None) -> list:
    """The model's shading solids for `sf` (nearshade.Solid, plan metres): [] when the option is off."""
    where = placed(project) if where is None else where
    if where is None:
        return []
    from .energy import nearshade
    hulls, plan, lo, hi = where
    ref = project.resources["ifc_reference"]
    label = name or (Path(str(ref.get("file") or "IFC")).stem or "IFC")
    start = hulls["start"]
    picked = chosen(project, sf, where)
    if len(picked) <= MAX_SOLIDS:
        return [nearshade.Solid(plan[start[i]:start[i + 1]].copy(), label) for i in picked]
    return [nearshade.Solid(c, label) for c in _grouped(plan, start, lo, hi, picked)]


def _grouped(plan, start, lo, hi, picked) -> list:
    """Too many elements for the calculation (each a shadow at each sun): the elements of a cell of the plan, and of a
    band of height, as the hull of all their corners, which holds each of them (still never less shadow); the cells
    grow until the solids are at most MAX_SOLIDS."""
    middle = (lo[picked] + hi[picked]) / 2
    top = hi[picked, 2]
    span = float(max(np.ptp(middle[:, 0]), np.ptp(middle[:, 1]), 1.0))
    cell = max(GROUP_CELL, span / 64)
    while True:
        keys = np.column_stack([np.floor(middle[:, :2] / cell), np.floor(top / (cell / 2))]).astype(np.int64)
        _u, group = np.unique(keys, axis=0, return_inverse=True)
        if group.max() + 1 <= MAX_SOLIDS:
            break
        cell *= 1.5
    out = []
    for g in range(int(group.max()) + 1):
        members = picked[group.ravel() == g]
        pts = np.concatenate([plan[start[i]:start[i + 1]] for i in members])
        out.append(_hull_corners(pts))
    return out


def key(project) -> dict | None:
    """What the year's key holds of the option (session._energy_inputs): None when it is off, so the keys of before stay."""
    opt = option(project)
    if opt is None:
        return None
    ctx = project.resources["ifc_reference"]["context"]
    path = ctx.get("mesh") or ""
    try:
        st = os.stat(path)
        stamp = [st.st_size, st.st_mtime_ns]
    except OSError:
        stamp = None
    return {"reach": opt["reach"], "mesh": path, "stamp": stamp, "version": VERSION}
