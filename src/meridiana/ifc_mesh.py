"""The true geometry of an IFC model, for the 3D view as context (r21-ifc-vista) and, later, for the IFC viewer
(docs/studio/40-visualizzatore-ifc.md, points 2, 3 and 9). Without Qt.

The import keeps its simplified bodies (an outline and two heights) for the calculation: they are what modules lie on
and what casts shadows. They do not look like the model (docs/quick/stato/r21-ifc-vista.md: the plan they cover is
the model's plan grown by a half, a pipe is 12 cm high at least, an assembly is one block). This module gives what the
3D shows next to them: the triangles the scan already reads (`ifc_scan.Model`), as shared vertices and faces, one piece
for each colour of the model (its `IfcStyledItem` colours, else a colour for its IFC class), the vertices in float32
around the model's middle so that a georeferenced model keeps its millimetres.

    mesh = build(scan)                  # dict of arrays, `save` / `load` as one .npz
    mesh["pieces"]                      # [(rgb, first vertex, vertices, first face, faces)...]

A representation map used more than once is still copied once per instance: on the large test IFC each of the 3519 maps has
one instance only, so instancing would not save anything there; it is the next step for a model that repeats its
shapes (study 40, point 3)."""

from __future__ import annotations

import time
from collections.abc import Callable

import numpy as np

from . import ifc_scan

QUANTUM = 1 / 24                    # colours closer than this are one piece
CLASS_COLOURS = {                   # sRGB 0..1, for the elements without a colour of their own
    "IfcWall": (0.86, 0.84, 0.80), "IfcWallStandardCase": (0.86, 0.84, 0.80), "IfcSlab": (0.72, 0.72, 0.72),
    "IfcRoof": (0.70, 0.45, 0.38), "IfcCovering": (0.70, 0.45, 0.38), "IfcBeam": (0.60, 0.62, 0.66),
    "IfcColumn": (0.60, 0.62, 0.66), "IfcMember": (0.60, 0.62, 0.66), "IfcPlate": (0.66, 0.68, 0.70),
    "IfcWindow": (0.55, 0.70, 0.85), "IfcDoor": (0.62, 0.48, 0.34), "IfcRailing": (0.50, 0.50, 0.52),
    "IfcStair": (0.68, 0.68, 0.66), "IfcPipeSegment": (0.40, 0.60, 0.40), "IfcPipeFitting": (0.40, 0.60, 0.40),
    "IfcFlowSegment": (0.40, 0.60, 0.40), "IfcFlowFitting": (0.40, 0.60, 0.40), "IfcDuctSegment": (0.55, 0.62, 0.70),
    "IfcBuildingElementProxy": (0.74, 0.74, 0.76)}
OTHER_COLOUR = (0.70, 0.70, 0.72)


def _colour_of(model: ifc_scan.Model, rid, depth: int = 0):
    """The surface colour of a style (IfcPresentationStyleAssignment, IfcSurfaceStyle, its shading or rendering),
    (r, g, b, opacity) or None."""
    if rid is None or depth > 6:
        return None
    rec = model.get(rid)
    if rec is None:
        return None
    t, a = rec
    if t == "IFCPRESENTATIONSTYLEASSIGNMENT":
        for s in a[0] or []:
            c = _colour_of(model, s, depth + 1)
            if c is not None:
                return c
    elif t == "IFCSURFACESTYLE":
        for s in a[2] or []:
            c = _colour_of(model, s, depth + 1)
            if c is not None:
                return c
    elif t in ("IFCSURFACESTYLESHADING", "IFCSURFACESTYLERENDERING"):
        c = model.get(a[0])
        if c is not None and c[0] == "IFCCOLOURRGB":
            try:
                rgb = tuple(min(1.0, max(0.0, float(v))) for v in c[1][1:4])
                clear = a[1] if t == "IFCSURFACESTYLERENDERING" and len(a) > 1 else None
                clear = clear.value if isinstance(clear, ifc_scan.Typed) else clear
                return rgb + (1.0 - min(1.0, max(0.0, float(clear))) if isinstance(clear, (int, float)) else 1.0,)
            except (TypeError, ValueError):
                return None
    return None


def styles(model: ifc_scan.Model) -> dict:
    """Representation item -> its colour, from every IfcStyledItem of the file."""
    out: dict = {}
    for rid, (t, _raw) in model.small.items():
        if t != "IFCSTYLEDITEM":
            continue
        a = model.get(rid)[1]
        if a[0] is None:
            continue
        for s in a[1] or []:
            c = _colour_of(model, s)
            if c is not None:
                out[int(a[0])] = c
                break
    return out


class _Builder:
    """The indexed triangles of the elements of one scan: the points of a shell once each, the map of a mapped item
    made once and moved for each instance."""

    def __init__(self, model: ifc_scan.Model, colours: dict):
        self.m = model
        self.colours = colours
        self.maps: dict = {}

    def item(self, rid, depth: int = 0) -> tuple[np.ndarray, np.ndarray, tuple | None]:
        """(vertices float64 (n, 3), faces int64 (m, 3), colour or None) of a representation item, its own frame."""
        m = self.m
        empty = (np.zeros((0, 3)), np.zeros((0, 3), np.int64), None)
        if rid is None or depth > 12:
            return empty
        colour = self.colours.get(int(rid))
        k = int(m.kind[rid]) if rid < len(m.kind) else 0
        if k == 5:
            ids = m.shell_triangles(rid)
            if not len(ids):
                return empty
            uniq, inv = np.unique(ids, return_inverse=True)
            return m._xyz(uniq), inv.reshape(-1, 3), colour
        rec = m.get(rid)
        if rec is None:
            return empty
        t, a = rec
        if t in ("IFCFACETEDBREP", "IFCFACETEDBREPWITHVOIDS", "IFCMANIFOLDSOLIDBREP"):
            v, f, c = self.item(a[0], depth + 1)
            return v, f, colour or c
        if t in ("IFCSHELLBASEDSURFACEMODEL", "IFCFACEBASEDSURFACEMODEL"):
            v, f, c = _join([self.item(s, depth + 1) for s in a[0] or []])
            return v, f, colour or c
        if t == "IFCMAPPEDITEM":
            hit = self.maps.get(int(a[0]))
            if hit is None:
                source = m.get(a[0])
                if source is None:
                    return empty
                origin, rep = source[1][0], source[1][1]
                r = m.get(rep)
                hit = _join([self.item(i, depth + 1) for i in (r[1][3] or [])]) if r else empty
                if len(hit[0]) and m.type_of(origin).startswith("IFCAXIS2"):
                    o = m.axis2(origin)
                    hit = (hit[0] @ o[:3, :3].T + o[:3, 3], hit[1], hit[2])
                self.maps[int(a[0])] = hit
            v, f, c = hit
            if len(v):
                op = m.operator(a[1])
                v = v @ op[:3, :3].T + op[:3, 3]
            return v, f, colour or c
        tris, _inner, _left = m.item_triangles(rid, depth)
        if not len(tris):
            return empty
        return tris.reshape(-1, 3), np.arange(len(tris) * 3, dtype=np.int64).reshape(-1, 3), colour

    def element(self, eid: int, cache: dict) -> tuple[np.ndarray, np.ndarray, tuple | None]:
        """An element's vertices in the world frame (file units), its faces and its colour."""
        m = self.m
        _t, a = m.get(eid)
        body = m.body_of(a[6])
        if body is None:
            return np.zeros((0, 3)), np.zeros((0, 3), np.int64), None
        v, f, c = _join([self.item(i) for i in (m.get(body)[1][3] or [])])
        if len(v):
            p = m.placement(a[5], cache)
            v = v @ p[:3, :3].T + p[:3, 3]
        return v, f, c


def _join(parts: list) -> tuple[np.ndarray, np.ndarray, tuple | None]:
    parts = [p for p in parts if len(p[1])]
    if not parts:
        return np.zeros((0, 3)), np.zeros((0, 3), np.int64), None
    if len(parts) == 1:
        return parts[0]
    base = np.cumsum([0] + [len(p[0]) for p in parts[:-1]])
    colour = next((p[2] for p in parts if p[2] is not None), None)
    return (np.concatenate([p[0] for p in parts]), np.concatenate([p[1] + b for p, b in zip(parts, base, strict=True)]),
            colour)


def build(scan: ifc_scan.Scan, progress: Callable[[float], None] | None = None, cancelled=None,
          only: set | None = None) -> dict:
    """The context mesh of a scan (the module's docstring): `vertices` float32 (n, 3) metres around `centre` (float64,
    the model's world), `faces` uint32 (m, 3) indices into the piece's own vertices, `pieces` int64 (k, 4): first
    vertex, vertices, first face, faces; `colours` float32 (k, 3); `elements` int64 (e, 3): id, first face, faces (of
    the element's piece, for picking later); `piece_of` the piece of each element; `colours` (k, 4) sRGB and opacity. `only`: the element ids to keep."""
    model = scan._model
    t0 = time.perf_counter()
    k = scan.unit_m
    builder = _Builder(model, styles(model))
    cache: dict = {}
    by_colour: dict = {}
    todo = [e for e in scan.elements if only is None or e.id in only]
    lo = np.array([min((e.lo[i] for e in todo), default=0.0) for i in range(3)])
    hi = np.array([max((e.hi[i] for e in todo), default=0.0) for i in range(3)])
    centre = (lo + hi) / 2
    for n, e in enumerate(todo):
        if cancelled is not None and n % 256 == 0 and cancelled():
            break
        if progress is not None and n % 500 == 0:
            progress(n / max(1, len(todo)))
        try:
            v, f, c = builder.element(e.id, cache)
        except (ifc_scan.ScanError, IndexError, TypeError, ValueError, KeyError, AttributeError):
            continue
        if not len(f):
            continue
        rgba = c if c is not None else CLASS_COLOURS.get(e.cls, OTHER_COLOUR) + (1.0,)
        key = tuple(int(round(x / QUANTUM)) for x in rgba)
        by_colour.setdefault(key, []).append((e.id, (v * k - centre).astype(np.float32), f))
    vertices, faces, pieces, colours, elements, piece_of = [], [], [], [], [], []
    at_v = at_f = 0
    for key in sorted(by_colour):
        items = by_colour.pop(key)
        first_v, first_f, local = at_v, at_f, 0
        for eid, v, f in items:
            elements.append((eid, at_f - first_f, len(f)))
            piece_of.append(len(pieces))
            vertices.append(v)
            faces.append((f + local).astype(np.uint32))
            local += len(v)
            at_v += len(v)
            at_f += len(f)
        pieces.append((first_v, at_v - first_v, first_f, at_f - first_f))
        colours.append([min(1.0, x * QUANTUM) for x in key])
    out = {"vertices": np.concatenate(vertices) if vertices else np.zeros((0, 3), np.float32),
           "faces": np.concatenate(faces) if faces else np.zeros((0, 3), np.uint32),
           "pieces": np.array(pieces, np.int64).reshape(-1, 4), "colours": np.array(colours, np.float32).reshape(-1, 4),
           "elements": np.array(elements, np.int64).reshape(-1, 3), "piece_of": np.array(piece_of, np.int64),
           "centre": centre.astype(np.float64), "seconds": np.float64(time.perf_counter() - t0)}
    if progress is not None:
        progress(1.0)
    return out


def save(path, mesh: dict) -> None:
    """One .npz, not compressed: it is read back whole by the 3D view."""
    np.savez(path, **mesh)


def load(path) -> dict:
    with np.load(path) as z:
        return {key: z[key] for key in z.files}


def piece(mesh: dict, i: int, skip=None) -> tuple[np.ndarray, np.ndarray, tuple]:
    """(vertices, faces, colour) of one piece; `skip`: element ids whose faces are left out (r22-ifc: the storeys not
    imported)."""
    v0, nv, f0, nf = (int(x) for x in mesh["pieces"][i])
    faces = mesh["faces"][f0:f0 + nf]
    if skip is not None and len(skip):
        rows = mesh["elements"][(mesh["piece_of"] == i) & np.isin(mesh["elements"][:, 0], np.asarray(skip, np.int64))]
        if len(rows):
            keep = np.ones(len(faces), bool)
            for _eid, first, n in rows:
                keep[int(first):int(first) + int(n)] = False
            faces = faces[keep]
    return mesh["vertices"][v0:v0 + nv], faces, tuple(float(c) for c in mesh["colours"][i])
