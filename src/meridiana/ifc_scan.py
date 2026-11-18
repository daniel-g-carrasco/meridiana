"""The fast reading of a large IFC file, without IfcOpenShell (R400): the file split into pieces read by several
processes at once, the solids of its elements made by NumPy, and of each element only what a photovoltaic design, or a
viewer, asks first: its class, name, group, storey, its points' box and the outline of its plan. Without Qt.

Why: IfcOpenShell 0.9.0.post1 on the IFC of the large test IFC (1.6 GB, 31 million entities, 8.3 million faces of
faceted Breps, 13 301 proxies) takes 56 s and 4.7 GB to open the file lazily, 222 s and 7.3 GB to open it whole, and
its iterator with 16 threads had not made 1000 shapes after another 275 s (docs/quick/stato/r21-ifc.md). BIM Vision
takes 268 s and 8.3 GB. A STEP file is one record per entity, `#id=TYPE(args);`: the records that are most of a large
model (points, loops, bounds, faces, shells) are read here by regular expressions into arrays, in parallel, and the
few others (hundreds of thousands at most) are kept as text and parsed when asked.

What is read as geometry, in the model's world frame and in metres:
- faceted Breps (with voids), closed and open shells, connected face sets, shell and face based surface models;
- triangulated and polygonal face sets (IFC4);
- extrusions of a rectangle, a circle, a polyline, an indexed poly curve, the parametric profiles (I, T, L, U, C, Z,
  as their bounding rectangle);
- mapped items (the instances of a representation map), booleans and clippings (their first operand: a solid with a
  hole is read without it), bounding boxes.
Anything else (curved Breps, sweeps along curves, revolutions, CSG) is counted as left out: `ifc_read`, through
IfcOpenShell, reads those models as before. A face's inner bounds (holes) are left out: the outline and the heights
do not need them.

The interface: `scan(path, progress, workers)` gives a `Scan` (`elements`, `listing()`), `Scan.triangles(id)` the
triangles of one element for a viewer (docs/studio/40-visualizzatore-ifc.md)."""

from __future__ import annotations

import math
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

PIECE = 16 << 20                    # bytes a process reads at a time (16 workers: about 3 GB at the peak)
SMALL_FILE = 48 << 20               # under this the file is read by this process alone: starting processes costs more
CIRCLE_SIDES = 16
CONCAVE_FROM = 2.0                  # m2: an element's convex hull larger than this is looked at for a concave one
CONCAVE_RATIO = 0.1
CONCAVE_GAIN = 0.7                  # the concave hull kept when it is less than this share of the convex one
REDUCE_FROM = 20000                  # points: under this a shape keeps its points, over it the vertices of its hull
NUM = rb"([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)"
REC = re.compile(rb"\n#(\d+)\s*=\s*([A-Z0-9_]+)\s*\(")
POINT = re.compile(rb"\n#(\d+)\s*=\s*IFCCARTESIANPOINT\s*\(\s*\(\s*" + NUM + rb"\s*,\s*" + NUM
                   + rb"\s*(?:,\s*" + NUM + rb"\s*)?\)\s*\)")
LOOP3 = re.compile(rb"\n#(\d+)\s*=\s*IFCPOLYLOOP\s*\(\s*\(\s*#(\d+)\s*,\s*#(\d+)\s*,\s*#(\d+)\s*\)\s*\)")
LOOPN = re.compile(rb"\n#(\d+)\s*=\s*IFCPOLYLOOP\s*\(\s*\(([^)]*)\)\s*\)")
BOUND = re.compile(rb"\n#(\d+)\s*=\s*IFCFACE(OUTER)?BOUND\s*\(\s*#(\d+)\s*,\s*\.([TF])\.\s*\)")
FACE1 = re.compile(rb"\n#(\d+)\s*=\s*IFCFACE\s*\(\s*\(\s*#(\d+)\s*\)\s*\)")
FACEN = re.compile(rb"\n#(\d+)\s*=\s*IFCFACE\s*\(\s*\(([^)]*)\)\s*\)")
SHELL = re.compile(rb"\n#(\d+)\s*=\s*IFC(?:CLOSEDSHELL|OPENSHELL|CONNECTEDFACESET)\s*\(\s*\(([^)]*)\)\s*\)")
OTHER = re.compile(rb"\n#(\d+)\s*=\s*(?!(?:IFCCARTESIANPOINT|IFCPOLYLOOP|IFCFACEOUTERBOUND|IFCFACEBOUND|IFCFACE|"
                   rb"IFCCLOSEDSHELL|IFCOPENSHELL|IFCCONNECTEDFACESET)\s*\()([A-Z0-9_]+)\s*\(")
ROOT = re.compile(rb"\s*'[^']{22}'\s*,")          # an IfcRoot's record starts with its GlobalId
BULK = {b"IFCCARTESIANPOINT", b"IFCPOLYLOOP", b"IFCFACEOUTERBOUND", b"IFCFACEBOUND", b"IFCFACE", b"IFCCLOSEDSHELL",
        b"IFCOPENSHELL", b"IFCCONNECTEDFACESET"}
SPATIAL = {"IFCPROJECT", "IFCSITE", "IFCBUILDING", "IFCBUILDINGSTOREY", "IFCSPACE", "IFCFACILITY", "IFCFACILITYPART",
           "IFCBRIDGE", "IFCROAD", "IFCRAILWAY", "IFCMARINEFACILITY", "IFCSPATIALZONE", "IFCEXTERNALSPATIALELEMENT"}
NOT_SOLIDS = {"IFCOPENINGELEMENT", "IFCSPACE", "IFCANNOTATION", "IFCGRID", "IFCVIRTUALELEMENT", "IFCSITE",
              "IFCBUILDING", "IFCBUILDINGSTOREY", "IFCOPENINGSTANDARDCASE", "IFCSPATIALZONE", "IFCPROJECT"}
BODY_NAMES = ("Body", "Facetation", "body", "BODY", "Mesh")
SKIP_NAMES = {"Axis", "FootPrint", "Annotation", "Profile", "Plan", "Clearance", "Lighting", "Reference", "CoG",
              "Box", "Surface", "Point", "Label"}
SI_PREFIX = {"EXA": 1e18, "PETA": 1e15, "TERA": 1e12, "GIGA": 1e9, "MEGA": 1e6, "KILO": 1e3, "HECTO": 1e2,
             "DECA": 1e1, "DECI": 1e-1, "CENTI": 1e-2, "MILLI": 1e-3, "MICRO": 1e-6, "NANO": 1e-9}


class ScanError(ValueError):
    """Not a readable IFC file: the reason."""


# --- reading the file in pieces -------------------------------------------------------------------------------------

def _pieces(path: str, size: int, piece: int) -> list[tuple[int, int]]:
    """Byte ranges of the file, each starting at the newline before a record (`\\n#`), together the whole data."""
    cuts = [0]
    with open(path, "rb") as fh:
        at = piece
        while at < size:
            fh.seek(at)
            buf = fh.read(1 << 20)
            i = buf.find(b"\n#")
            if i < 0:
                at += 1 << 20
                continue
            cuts.append(at + i)
            at = at + i + piece
    cuts.append(size)
    return [(a, b) for a, b in zip(cuts, cuts[1:], strict=False) if b > a]


def _ints(text: bytes) -> np.ndarray:
    return np.array(text.replace(b"#", b" ").replace(b",", b" ").split(), dtype=np.int64)


def _flat(lists: list) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """ids, offsets and the references of records holding a list of references, without a Python loop per
    reference."""
    if not lists:
        return np.zeros(0, np.int64), np.zeros(1, np.int64), np.zeros(0, np.int64)
    ids = np.array([a for a, _b in lists], dtype="S20").astype(np.int64)
    counts = np.fromiter((b.count(b"#") for _a, b in lists), dtype=np.int64, count=len(lists))
    off = np.zeros(len(lists) + 1, np.int64)
    off[1:] = np.cumsum(counts)
    return ids, off, _ints(b",".join(b for _a, b in lists))


def read_piece(path: str, start: int, end: int) -> dict:
    """One piece of the file: its records counted by type, the bulk ones as arrays, the others as text. The regular
    expressions run in C over the whole piece; Python sees only the records that are not bulk."""
    with open(path, "rb") as fh:
        fh.seek(start)
        data = fh.read(end - start)
    if start == 0:
        data = b"\n" + data
    stop = data.rfind(b"\nENDSEC") if end >= os.path.getsize(path) else -1      # the DATA's, not the HEADER's
    if stop > 0:
        data = data[:stop]
    counts: dict = {}
    small: list = []
    for m in OTHER.finditer(data):
        t = m.group(2).decode()
        counts[t] = counts.get(t, 0) + 1
        nxt = data.find(b"\n#", m.end())
        small.append((int(m.group(1)), t, data[m.end():nxt if nxt >= 0 else len(data)]))
    out: dict = {"small": small, "bytes": end - start}
    pts = POINT.findall(data)
    counts["IFCCARTESIANPOINT"] = len(pts)
    if pts:
        a = np.array(pts, dtype="S32")
        a[:, 3][a[:, 3] == b""] = b"0"
        out["pt_id"], out["pt_xyz"] = a[:, 0].astype(np.int64), a[:, 1:].astype(np.float64)
    ids, off, ref = _flat(LOOPN.findall(data))
    counts["IFCPOLYLOOP"] = len(ids)
    n = np.diff(off)
    three = n == 3
    if three.any():
        k = off[:-1][three]
        out["l3_id"], out["l3"] = ids[three], np.stack([ref[k], ref[k + 1], ref[k + 2]], axis=1)
    if (~three).any():
        keep = np.repeat(~three, n)
        out["ln_id"], out["ln_ref"] = ids[~three], ref[keep]
        out["ln_off"] = np.r_[0, np.cumsum(n[~three])]
    bounds = BOUND.findall(data)
    counts["IFCFACEBOUND"] = len(bounds)
    if bounds:
        a = np.array([(x[0], x[2]) for x in bounds], dtype="S20").astype(np.int64)
        out["b_id"], out["b_loop"] = a[:, 0], a[:, 1]
    ids, off, ref = _flat(FACEN.findall(data))
    counts["IFCFACE"] = len(ids)
    n = np.diff(off)
    one = n == 1
    out["f_id"], out["f_bound"] = ids[one], ref[off[:-1][one]]
    if (~one).any():
        keep = np.repeat(~one, n)
        out["fn_id"], out["fn_ref"] = ids[~one], ref[keep]
        out["fn_off"] = np.r_[0, np.cumsum(n[~one])]
    out["s_id"], out["s_off"], out["s_ref"] = _flat(SHELL.findall(data))
    counts["IFCCLOSEDSHELL"] = len(out["s_id"])
    out["counts"] = {k: v for k, v in counts.items() if v}
    return out


# --- the parsing of the records kept as text -----------------------------------------------------------------------

class Ref(int):
    """A reference to another record, #id."""


@dataclass
class Typed:
    """A typed value, as IFCLABEL('x')."""
    name: str
    value: object


TOKEN = re.compile(rb"\s*(?:(#\d+)|('(?:[^']|'')*')|(\.[A-Za-z0-9_]+\.)|" + NUM + rb"|(\$)|(\*)|(\()|(\))|(,)|"
                   rb"([A-Za-z0-9_]+)\s*\(|(\"[0-9A-Fa-f]*\"))")
_X2 = re.compile(r"\\X2\\([0-9A-Fa-f]+)\\X0\\")
_X = re.compile(r"\\X\\([0-9A-Fa-f]{2})")


def text_of(raw: str) -> str:
    """An IFC string decoded: \\X2\\...\\X0\\ (UTF-16), \\X\\hh (ISO 8859-1), \\S\\c."""
    if "\\" not in raw:
        return raw
    raw = _X2.sub(lambda m: bytes.fromhex(m.group(1)).decode("utf-16-be", "replace"), raw)
    raw = _X.sub(lambda m: bytes.fromhex(m.group(1)).decode("latin-1"), raw)
    raw = re.sub(r"\\S\\(.)", lambda m: chr(ord(m.group(1)) + 128), raw)
    return raw.replace("\\\\", "\\")


def parse_args(raw: bytes) -> list:
    """The arguments of a record, `args` of `#id=TYPE(args);`, as Python values: Ref, str, float, int, enums as
    '.X.', None for $ and *, lists, Typed."""
    raw = raw.rstrip()
    if raw.endswith(b";"):
        raw = raw[:-1].rstrip()
    if raw.endswith(b")"):
        raw = raw[:-1]
    stack: list = [[]]
    typed: list = []                # the names of the typed values open, in stack order (None for a list)
    pos = 0
    n = len(raw)
    while pos < n:
        m = TOKEN.match(raw, pos)
        if m is None:
            if raw[pos:].strip() == b"":
                break
            raise ScanError(f"unreadable arguments near {raw[pos:pos + 40]!r}")
        pos = m.end()
        ref, s, enum, num, dollar, star, opn, cls, _comma, tname, binary = m.groups()
        top = stack[-1]
        if ref:
            top.append(Ref(int(ref[1:])))
        elif s is not None:
            top.append(text_of(s[1:-1].replace(b"''", b"'").decode("utf-8", "replace")))
        elif enum:
            top.append(enum.decode())
        elif num:
            top.append(float(num) if (b"." in num or b"e" in num or b"E" in num) else int(num))
        elif dollar or star:
            top.append(None)
        elif opn:
            stack.append([])
            typed.append(None)
        elif tname:
            stack.append([])
            typed.append(tname.decode())
        elif cls:
            if len(stack) == 1:
                break
            done = stack.pop()
            name = typed.pop()
            stack[-1].append(done if name is None else Typed(name, done[0] if len(done) == 1 else done))
        elif binary:
            top.append(binary.decode())
    return stack[0]


# --- geometry -------------------------------------------------------------------------------------------------------

def _unit(v) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v


@dataclass
class Element:
    """What the scan says of one element with a shape."""
    id: int
    cls: str
    name: str
    guid: str
    group: int                      # the record of its top assembly (IfcElementAssembly...), itself when none
    group_name: str
    storey: str
    storey_z: float | None
    building: int | None
    lo: tuple                       # its points' box, world metres
    hi: tuple
    hull: list                      # the convex hull of its plan, [[x, y]...]
    triangles: int
    mapped: int                     # how many of its items are instances of a representation map
    left_out: int = 0               # items of a kind not read here


@dataclass
class Scan:
    path: str
    schema: str
    size: int
    counts: dict
    unit_m: float
    elements: list = field(default_factory=list)
    times: dict = field(default_factory=dict)
    left_out: dict = field(default_factory=dict)        # kind -> items
    site: dict = field(default_factory=dict)
    buildings: dict = field(default_factory=dict)       # record -> name
    storeys: dict = field(default_factory=dict)         # record -> (name, elevation m)
    maps: int = 0                                       # representation maps
    instances: int = 0                                  # their instances
    workers: int = 1
    peak_mb: int = 0
    _model: object = None

    def listing(self) -> dict:
        """What is in the file, for the window and for the result (plain data)."""
        by_class: dict = {}
        for e in self.elements:
            c = by_class.setdefault(e.cls, [0, 0])
            c[0] += 1
            c[1] += e.triangles
        groups = {e.group for e in self.elements}
        return {"schema": self.schema, "size_mb": round(self.size / 2 ** 20, 1),
                "entities": int(sum(self.counts.values())), "unit_m": self.unit_m,
                "types": dict(sorted(self.counts.items(), key=lambda kv: -kv[1])[:40]),
                "classes": {k: {"elements": v[0], "triangles": v[1]} for k, v in
                            sorted(by_class.items(), key=lambda kv: -kv[1][0])},
                "elements": len(self.elements), "groups": len(groups),
                "triangles": int(sum(e.triangles for e in self.elements)),
                "maps": self.maps, "instances": self.instances,
                "storeys": [{"name": n, "z": z} for n, z in self.storeys.values()],
                "buildings": list(self.buildings.values()), "left_out": dict(self.left_out),
                "times": {k: round(v, 3) for k, v in self.times.items()}, "workers": self.workers,
                "site": self.site}

    def triangles(self, eid: int) -> np.ndarray:
        """The triangles of one element, world metres, (n, 3, 3): what a viewer draws."""
        return self._model.element_triangles(eid)[0]


class Model:
    """The arrays of the bulk records and the text of the others, and the geometry made from them."""

    def __init__(self, parts: list):
        def cat(key, dtype, shape=(0,)):
            arrays = [p[key] for p in parts if key in p]
            return np.concatenate(arrays) if arrays else np.zeros(shape, dtype)
        self.small: dict = {}
        for p in parts:
            for rid, t, raw in p["small"]:
                self.small[rid] = (t, raw)
        self.parsed: dict = {}
        self.pt_id, self.pt_xyz = cat("pt_id", np.int64), cat("pt_xyz", np.float64, (0, 3))
        # loops: the triangles, with the polygons made fans
        l3_id, l3 = cat("l3_id", np.int64), cat("l3", np.int64, (0, 3))
        loop_ids, loop_start, loop_count, tris = [l3_id], [np.arange(len(l3_id), dtype=np.int64)],             [np.ones(len(l3_id), np.int64)], [l3]
        at = len(l3_id)
        for p in parts:
            if "ln_id" not in p or not len(p["ln_id"]):
                continue
            ids, off, ref = p["ln_id"], p["ln_off"], p["ln_ref"]
            start, n = off[:-1], np.diff(off)
            m = np.maximum(n - 2, 0)                    # a polygon of n points is a fan of n - 2 triangles
            total = int(m.sum())
            j = np.arange(total) - np.repeat(np.cumsum(m) - m, m)
            first = np.repeat(start, m)
            tris.append(np.stack([ref[first], ref[first + 1 + j], ref[first + 2 + j]], axis=1))
            loop_ids.append(ids)
            loop_start.append(at + np.cumsum(m) - m)
            loop_count.append(m)
            at += total
        self.loop_id = np.concatenate(loop_ids)
        self.loop_start = np.concatenate(loop_start)
        self.loop_count = np.concatenate(loop_count)
        self.tri_pts = np.concatenate(tris) if tris else np.zeros((0, 3), np.int64)
        self.b_id, self.b_loop = cat("b_id", np.int64), cat("b_loop", np.int64)
        # faces: the first bound of each (the outer one, as the exporters write them; the holes are left out)
        f_id, f_bound = [cat("f_id", np.int64)], [cat("f_bound", np.int64)]
        for p in parts:
            if "fn_id" in p and len(p["fn_id"]):
                ids, off, ref = p["fn_id"], p["fn_off"], p["fn_ref"]
                keep = np.diff(off) > 0
                f_id.append(ids[keep])
                f_bound.append(ref[off[:-1][keep]])
        self.f_id, self.f_bound = np.concatenate(f_id), np.concatenate(f_bound)
        sh = [(p["s_id"], p["s_off"], p["s_ref"]) for p in parts if len(p["s_id"])]
        self.s_id = np.concatenate([s[0] for s in sh]) if sh else np.zeros(0, np.int64)
        offs, refs, base = [np.zeros(1, np.int64)], [], 0
        for _ids, off, ref in sh:
            offs.append(off[1:] + base)
            refs.append(ref)
            base += len(ref)
        self.s_off = np.concatenate(offs)
        self.s_ref = np.concatenate(refs) if refs else np.zeros(0, np.int64)
        top = max([int(a.max()) for a in (self.pt_id, self.loop_id, self.b_id, self.f_id, self.s_id) if len(a)]
                  + [max(self.small, default=0)])
        self.row = np.full(top + 1, -1, dtype=np.int32)
        for ids in (self.pt_id, self.loop_id, self.b_id, self.f_id, self.s_id):
            self.row[ids] = np.arange(len(ids), dtype=np.int32)
        self.kind = np.zeros(top + 1, dtype=np.uint8)            # 1 point, 2 loop, 3 bound, 4 face, 5 shell
        for k, ids in enumerate((self.pt_id, self.loop_id, self.b_id, self.f_id, self.s_id), start=1):
            self.kind[ids] = k
        self.left_out: dict = {}
        self.map_points: dict = {}
        self.maps: set = set()
        self.instances = 0

    # records
    def get(self, rid: int):
        """(TYPE, args) of a record kept as text; None for a bulk one or a missing one."""
        hit = self.parsed.get(rid)
        if hit is None:
            raw = self.small.get(rid)
            if raw is None:
                return None
            hit = (raw[0], parse_args(raw[1]))
            self.parsed[rid] = hit
        return hit

    def type_of(self, rid) -> str:
        if rid is None:
            return ""
        if rid in self.small:
            return self.small[rid][0]
        k = int(self.kind[rid]) if 0 <= rid < len(self.kind) else 0
        return ("", "IFCCARTESIANPOINT", "IFCPOLYLOOP", "IFCFACEBOUND", "IFCFACE", "IFCCLOSEDSHELL")[k]

    def point(self, rid) -> np.ndarray:
        if rid is None:
            return np.zeros(3)
        r = int(self.row[rid])
        if r < 0 or self.kind[rid] != 1:
            raise ScanError(f"#{rid} is not a point")
        return self.pt_xyz[r].copy()

    def direction(self, rid, default) -> np.ndarray:
        if rid is None:
            return np.asarray(default, float)
        rec = self.get(rid)
        if rec is None:
            return np.asarray(default, float)
        v = list(rec[1][0]) + [0.0] * 3
        return _unit(v[:3])

    def axis2(self, rid) -> np.ndarray:
        """IfcAxis2Placement3D or 2D as a 4x4 matrix (file units)."""
        m = np.eye(4)
        if rid is None:
            return m
        t, a = self.get(rid)
        loc = self.point(a[0])
        if t == "IFCAXIS2PLACEMENT2D":
            x = self.direction(a[1] if len(a) > 1 else None, (1, 0, 0))
            z = np.array([0.0, 0.0, 1.0])
        else:
            z = self.direction(a[1] if len(a) > 1 else None, (0, 0, 1))
            x = self.direction(a[2] if len(a) > 2 else None, (1, 0, 0))
        x = _unit(x - np.dot(x, z) * z)
        if not np.any(x):
            x = _unit(np.cross([0.0, 1.0, 0.0], z)) if abs(z[1]) < 0.9 else _unit(np.cross(z, [1.0, 0.0, 0.0]))
        y = np.cross(z, x)
        m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, y, z, loc
        return m

    def placement(self, rid, cache: dict) -> np.ndarray:
        if rid is None:
            return np.eye(4)
        hit = cache.get(rid)
        if hit is not None:
            return hit
        rec = self.get(rid)
        if rec is None or rec[0] != "IFCLOCALPLACEMENT":
            m = np.eye(4)
        else:
            rel, local = rec[1][0], rec[1][1]
            m = self.placement(rel, cache) @ self.axis2(local) if rel is not None else self.axis2(local)
        cache[rid] = m
        return m

    def operator(self, rid) -> np.ndarray:
        """IfcCartesianTransformationOperator3D (and its non uniform kind) as a 4x4 matrix."""
        t, a = self.get(rid)
        x = self.direction(a[0], (1, 0, 0))
        y = self.direction(a[1], (0, 1, 0))
        o = self.point(a[2])
        s = float(a[3]) if len(a) > 3 and a[3] is not None else 1.0
        z = self.direction(a[4] if len(a) > 4 else None, np.cross(x, y))
        sy = float(a[5]) if t.endswith("NONUNIFORM") and len(a) > 5 and a[5] is not None else s
        sz = float(a[6]) if t.endswith("NONUNIFORM") and len(a) > 6 and a[6] is not None else s
        m = np.eye(4)
        m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x * s, y * sy, z * sz, o
        return m

    # faces
    def shell_triangles(self, sid: int) -> np.ndarray:
        """The point records of the triangles of a shell, (n, 3)."""
        r = int(self.row[sid])
        faces = self.s_ref[self.s_off[r]:self.s_off[r + 1]]
        fr = self.row[faces]
        fr = fr[fr >= 0]
        br = self.row[self.f_bound[fr]]
        br = br[br >= 0]
        lr = self.row[self.b_loop[br]]
        lr = lr[lr >= 0]
        starts, counts = self.loop_start[lr], self.loop_count[lr]
        if not len(counts):
            return np.zeros((0, 3), np.int64)
        if int(counts.max()) == 1 and int(counts.min()) == 1:
            return self.tri_pts[starts]
        idx = np.repeat(starts - np.cumsum(np.r_[0, counts[:-1]]), counts) + np.arange(int(counts.sum()))
        return self.tri_pts[idx]

    def _xyz(self, point_records: np.ndarray) -> np.ndarray:
        r = self.row[point_records.ravel()]
        ok = r >= 0
        out = np.zeros((len(r), 3))
        out[ok] = self.pt_xyz[r[ok]]
        return out.reshape(point_records.shape + (3,))

    def _profile(self, rid) -> np.ndarray | None:
        """The outline of a profile, (n, 2) in its own frame placed (file units); None when not read here."""
        t, a = self.get(rid)
        if t in ("IFCARBITRARYCLOSEDPROFILEDEF", "IFCARBITRARYPROFILEDEFWITHVOIDS"):
            return self._curve(a[2])
        if t == "IFCRECTANGLEPROFILEDEF" or t == "IFCROUNDEDRECTANGLEPROFILEDEF" or t == "IFCRECTANGLEHOLLOWPROFILEDEF":
            w, h = float(a[3]) / 2, float(a[4]) / 2
            ring = np.array([[-w, -h], [w, -h], [w, h], [-w, h]])
        elif t in ("IFCCIRCLEPROFILEDEF", "IFCCIRCLEHOLLOWPROFILEDEF"):
            r = float(a[3])
            k = np.linspace(0, 2 * math.pi, CIRCLE_SIDES, endpoint=False)
            ring = np.stack([r * np.cos(k), r * np.sin(k)], axis=1)
        elif t == "IFCELLIPSEPROFILEDEF":
            k = np.linspace(0, 2 * math.pi, CIRCLE_SIDES, endpoint=False)
            ring = np.stack([float(a[3]) * np.cos(k), float(a[4]) * np.sin(k)], axis=1)
        elif t in ("IFCISHAPEPROFILEDEF", "IFCASYMMETRICISHAPEPROFILEDEF"):
            w, h = float(a[3]) / 2, float(a[4]) / 2
            ring = np.array([[-w, -h], [w, -h], [w, h], [-w, h]])
        elif t in ("IFCTSHAPEPROFILEDEF", "IFCLSHAPEPROFILEDEF", "IFCUSHAPEPROFILEDEF", "IFCCSHAPEPROFILEDEF",
                   "IFCZSHAPEPROFILEDEF"):
            # Depth then Width (T, U, C, Z) or Depth then Width (L): the bounding rectangle, centred
            d = float(a[3])
            w = float(a[4]) if len(a) > 4 and isinstance(a[4], float) else d
            ring = np.array([[-w / 2, -d / 2], [w / 2, -d / 2], [w / 2, d / 2], [-w / 2, d / 2]])
        else:
            self.left_out[t] = self.left_out.get(t, 0) + 1
            return None
        if len(a) > 2 and isinstance(a[2], Ref):
            m = self.axis2(a[2])
            ring = ring @ m[:2, :2].T + m[:2, 3]
        return ring

    def _curve(self, rid) -> np.ndarray | None:
        t, a = self.get(rid)
        if t == "IFCPOLYLINE":
            return np.array([self.point(p)[:2] for p in a[0]])
        if t == "IFCINDEXEDPOLYCURVE":
            rec = self.get(a[0])
            return np.array([list(p)[:2] for p in rec[1][0]], dtype=float) if rec else None
        if t == "IFCCOMPOSITECURVE":
            pts = []
            for seg in a[0]:
                st, sa = self.get(seg)
                c = self._curve(sa[2]) if st.startswith("IFCCOMPOSITECURVESEGMENT") else None
                if c is None:
                    return None
                pts.extend(c.tolist())
            return np.array(pts) if pts else None
        if t == "IFCTRIMMEDCURVE":
            return self._curve(a[0])
        if t == "IFCCIRCLE":
            m = self.axis2(a[0])
            r = float(a[1])
            k = np.linspace(0, 2 * math.pi, CIRCLE_SIDES, endpoint=False)
            ring = np.stack([r * np.cos(k), r * np.sin(k)], axis=1)
            return ring @ m[:2, :2].T + m[:2, 3]
        self.left_out[t] = self.left_out.get(t, 0) + 1
        return None

    def _extrusion(self, a) -> np.ndarray | None:
        """The triangles (coordinates) of an extruded area solid: the prism of its outline."""
        ring = self._profile(a[0])
        if ring is None or len(ring) < 3:
            return None
        if np.allclose(ring[0], ring[-1]):
            ring = ring[:-1]
        m = self.axis2(a[1])
        d = self.direction(a[2], (0, 0, 1)) * float(a[3])
        n = len(ring)
        bottom = np.c_[ring, np.zeros(n)]
        top = bottom + d
        k = np.arange(n)
        k1 = (k + 1) % n
        sides = np.concatenate([np.stack([bottom[k], bottom[k1], top[k1]], 1), np.stack([bottom[k], top[k1], top[k]], 1)])
        fan = np.arange(1, n - 1)
        caps = np.concatenate([np.stack([bottom[np.zeros_like(fan)], bottom[fan + 1], bottom[fan]], 1),
                               np.stack([top[np.zeros_like(fan)], top[fan], top[fan + 1]], 1)])
        tris = np.concatenate([sides, caps])
        return tris @ m[:3, :3].T + m[:3, 3]

    def item_triangles(self, rid, depth: int = 0) -> tuple[np.ndarray, int, int]:
        """The triangles of a representation item (file units, the item's frame), the instances of maps in it and the
        items left out."""
        empty = np.zeros((0, 3, 3))
        if depth > 12 or rid is None:
            return empty, 0, 0
        k = int(self.kind[rid]) if rid < len(self.kind) else 0
        if k == 5:
            return self._xyz(self.shell_triangles(rid)), 0, 0
        rec = self.get(rid)
        if rec is None:
            return empty, 0, 1
        t, a = rec
        if t in ("IFCFACETEDBREP", "IFCFACETEDBREPWITHVOIDS", "IFCMANIFOLDSOLIDBREP"):
            return self.item_triangles(a[0], depth + 1)
        if t in ("IFCSHELLBASEDSURFACEMODEL", "IFCFACEBASEDSURFACEMODEL"):
            parts = [self.item_triangles(s, depth + 1) for s in a[0]]
            return (np.concatenate([p[0] for p in parts]) if parts else empty, sum(p[1] for p in parts),
                    sum(p[2] for p in parts))
        if t == "IFCMAPPEDITEM":
            source = self.get(a[0])
            if source is None:
                return empty, 0, 1
            origin, rep = source[1][0], source[1][1]
            self.maps.add(int(a[0]))
            self.instances += 1
            tris, inner, left = self.items_of_representation(rep, depth + 1)
            m = self.operator(a[1]) @ (self.axis2(origin) if self.type_of(origin).startswith("IFCAXIS2") else np.eye(4))
            if len(tris):
                tris = tris @ m[:3, :3].T + m[:3, 3]
            return tris, inner + 1, left
        if t == "IFCEXTRUDEDAREASOLID" or t == "IFCEXTRUDEDAREASOLIDTAPERED":
            tris = self._extrusion(a)
            return (empty, 0, 1) if tris is None else (tris, 0, 0)
        if t in ("IFCBOOLEANRESULT", "IFCBOOLEANCLIPPINGRESULT"):
            first = self.item_triangles(a[1], depth + 1)
            if a[0] == ".UNION.":
                second = self.item_triangles(a[2], depth + 1)
                return np.concatenate([first[0], second[0]]), first[1] + second[1], first[2] + second[2]
            return first
        if t == "IFCBOUNDINGBOX":
            c = self.point(a[0])
            lo, hi = c, c + np.array([float(a[1]), float(a[2]), float(a[3])])
            return _box(lo, hi), 0, 0
        if t in ("IFCTRIANGULATEDFACESET", "IFCPOLYGONALFACESET", "IFCTRIANGULATEDIRREGULARNETWORK"):
            return self._face_set(t, a), 0, 0
        if t == "IFCSTYLEDITEM":
            return empty, 0, 0
        self.left_out[t] = self.left_out.get(t, 0) + 1
        return empty, 0, 1

    def _face_set(self, t, a) -> np.ndarray:
        rec = self.get(a[0])
        if rec is None:
            return np.zeros((0, 3, 3))
        xyz = np.array([list(p) + [0.0] * (3 - len(p)) for p in rec[1][0]], dtype=float)
        if t == "IFCPOLYGONALFACESET":
            tris = []
            for fref in a[2]:
                fr = self.get(fref)
                ring = [int(i) - 1 for i in fr[1][0]]
                for k in range(1, len(ring) - 1):
                    tris.append((ring[0], ring[k], ring[k + 1]))
            idx = np.array(tris, dtype=np.int64).reshape(-1, 3)
        else:
            # the index list: the first argument after the coordinates that is a list of triples of integers
            idx = next((np.array(v, dtype=np.int64) - 1 for v in a[1:] if isinstance(v, list) and v
                        and isinstance(v[0], list) and len(v[0]) == 3 and isinstance(v[0][0], int)), None)
            if idx is None:
                return np.zeros((0, 3, 3))
        idx = idx[(idx >= 0).all(axis=1) & (idx < len(xyz)).all(axis=1)]
        return xyz[idx]

    def items_of_representation(self, rid, depth: int = 0) -> tuple[np.ndarray, int, int]:
        rec = self.get(rid)
        if rec is None:
            return np.zeros((0, 3, 3)), 0, 1
        parts = [self.item_triangles(i, depth + 1) for i in (rec[1][3] or [])]
        if not parts:
            return np.zeros((0, 3, 3)), 0, 0
        return np.concatenate([p[0] for p in parts]), sum(p[1] for p in parts), sum(p[2] for p in parts)

    def body_of(self, product_shape) -> int | None:
        """The representation that is the body of a product shape: «Body» first, else the first that is not an axis,
        a footprint or an annotation, else its bounding box."""
        rec = self.get(product_shape)
        if rec is None or rec[0] != "IFCPRODUCTDEFINITIONSHAPE":
            return None
        reps = [r for r in (rec[1][2] or []) if self.get(r) is not None]
        named = [(r, self.get(r)[1][1] or "") for r in reps]
        for r, n in named:
            if n in BODY_NAMES:
                return r
        for r, n in named:
            if n not in SKIP_NAMES:
                return r
        for r, n in named:
            if n == "Box":
                return r
        return None

    def item_points(self, rid, depth: int = 0) -> tuple[np.ndarray, int, int, int]:
        """The points of an item that its box and the hull of its plan need, whatever transform follows (the vertices
        of its convex hull in space), its triangles, the instances of maps and the items left out. A representation
        map is made once and its instances only moved: 13 301 instances of 3519 maps in the large test IFC's model."""
        rec = self.get(rid)
        if rec is not None and rec[0] == "IFCMAPPEDITEM":
            a = rec[1]
            hit = self.map_points.get(int(a[0]))
            if hit is None:
                source = self.get(a[0])
                if source is None:
                    return np.zeros((0, 3)), 0, 0, 1
                origin, rep = source[1][0], source[1][1]
                parts = [self.item_points(i, depth + 1) for i in (self.get(rep)[1][3] or [])] if self.get(rep) else []
                pts = np.concatenate([p[0] for p in parts]) if parts else np.zeros((0, 3))
                if len(pts) and self.type_of(origin).startswith("IFCAXIS2"):
                    m = self.axis2(origin)
                    pts = pts @ m[:3, :3].T + m[:3, 3]
                hit = (_reduce(pts) if len(parts) > 1 else pts, sum(p[1] for p in parts), sum(p[2] for p in parts), sum(p[3] for p in parts))
                self.map_points[int(a[0])] = hit
                self.maps.add(int(a[0]))
            self.instances += 1
            pts, tris, inner, left = hit
            if len(pts):
                m = self.operator(a[1])
                pts = pts @ m[:3, :3].T + m[:3, 3]
            return pts, tris, inner + 1, left
        shell = rid
        if rec is not None and rec[0] in ("IFCFACETEDBREP", "IFCFACETEDBREPWITHVOIDS", "IFCMANIFOLDSOLIDBREP"):
            shell = rec[1][0]
        if shell is not None and shell < len(self.kind) and self.kind[shell] == 5:
            # a shell: its points once each (a point is the corner of six triangles), not its triangles
            ids = self.shell_triangles(shell)
            return _reduce(self._xyz(np.unique(ids))), len(ids), 0, 0
        tris, inner, left = self.item_triangles(rid, depth)
        return _reduce(tris.reshape(-1, 3)), len(tris), inner, left

    def element_points(self, eid: int, cache: dict) -> tuple[np.ndarray, int, int, int]:
        """The points of an element (as `item_points`) in the world frame, file units."""
        t, a = self.get(eid)
        body = self.body_of(a[6])
        if body is None:
            return np.zeros((0, 3)), 0, 0, 0
        parts = [self.item_points(i) for i in (self.get(body)[1][3] or [])]
        if not parts:
            return np.zeros((0, 3)), 0, 0, 0
        pts = np.concatenate([p[0] for p in parts])
        if len(pts):
            m = self.placement(a[5], cache)
            pts = pts @ m[:3, :3].T + m[:3, 3]
        return pts, sum(p[1] for p in parts), sum(p[2] for p in parts), sum(p[3] for p in parts)

    def element_triangles(self, eid: int, cache: dict | None = None) -> tuple[np.ndarray, int, int]:
        """The triangles of an element in the world frame, file units: what a viewer draws (not cached)."""
        cache = {} if cache is None else cache
        t, a = self.get(eid)
        body = self.body_of(a[6])
        if body is None:
            return np.zeros((0, 3, 3)), 0, 0
        tris, mapped, left = self.items_of_representation(body)
        if len(tris):
            m = self.placement(a[5], cache)
            tris = tris @ m[:3, :3].T + m[:3, 3]
        return tris, mapped, left


def _reduce(pts: np.ndarray) -> np.ndarray:
    """The vertices of the convex hull in space of points (qhull), the points themselves when not so many that the hull
    pays (SciPy's qhull opens a temporary file at each call: 9000 calls cost 3 s on the large test IFC's model) or flat."""
    if len(pts) <= REDUCE_FROM:
        return pts
    from scipy.spatial import ConvexHull, QhullError
    try:
        return pts[ConvexHull(pts).vertices]
    except (QhullError, ValueError):
        try:
            return pts[ConvexHull(pts, qhull_options="QJ").vertices]
        except (QhullError, ValueError):
            return pts


def _box(lo, hi) -> np.ndarray:
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    c = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6),
         (3, 0, 4), (3, 4, 7)]
    return c[np.array(f)]


def _outline2d(pts: np.ndarray) -> list:
    """The outline of points in plan: their convex hull, or for a large and sparse element (a pipe run in L, a rack)
    their concave hull (GEOS, a share of the longest edge), when it is much smaller."""
    ring = _hull2d(pts)
    if len(ring) < 3 or len(pts) < 8:
        return ring
    import shapely
    hull = shapely.Polygon(ring)
    if hull.area < CONCAVE_FROM:
        return ring
    try:
        c = shapely.concave_hull(shapely.multipoints(pts[:, :2]), ratio=CONCAVE_RATIO)
    except (shapely.errors.GEOSException, ValueError):
        return ring
    if c.geom_type != "Polygon" or not c.is_valid or c.area < 1e-3 or c.area > CONCAVE_GAIN * hull.area:
        return ring
    c = shapely.geometry.polygon.orient(c.simplify(0.02))
    if c.geom_type != "Polygon":
        return ring
    return [[round(x, 3), round(y, 3)] for x, y in list(c.exterior.coords)[:-1]]


def _hull2d(pts: np.ndarray) -> list:
    """The convex hull of points in plan, counter-clockwise, rounded to the millimetre (GEOS: the points are many)."""
    import shapely
    if not len(pts):
        return []
    xy = pts[:, :2]
    if len(xy) > 64:
        # the points inside the octagon of the extreme ones are not on the hull (Akl and Toussaint)
        d = np.stack([xy[:, 0], xy[:, 1], xy[:, 0] + xy[:, 1], xy[:, 0] - xy[:, 1]], axis=1)
        idx = np.unique(np.r_[d.argmin(axis=0), d.argmax(axis=0)])
        oct_ = shapely.Polygon(xy[idx]).convex_hull if len(idx) >= 3 else None
        if oct_ is not None and oct_.geom_type == "Polygon" and oct_.area > 0:
            inside = shapely.contains_xy(oct_.buffer(-1e-6), xy[:, 0], xy[:, 1])
            xy = xy[~inside]
    h = shapely.convex_hull(shapely.multipoints(xy))
    if h.geom_type != "Polygon" or h.area < 1e-6:
        lo, hi = pts[:, :2].min(axis=0), pts[:, :2].max(axis=0) + 0.01
        return [[round(float(lo[0]), 3), round(float(lo[1]), 3)], [round(float(hi[0]), 3), round(float(lo[1]), 3)],
                [round(float(hi[0]), 3), round(float(hi[1]), 3)], [round(float(lo[0]), 3), round(float(hi[1]), 3)]]
    return [[round(x, 3), round(y, 3)] for x, y in list(h.exterior.coords)[:-1]]


# --- the scan --------------------------------------------------------------------------------------------------------

def _schema(path: str) -> str:
    with open(path, "rb") as fh:
        head = fh.read(1 << 16)
    if not head.lstrip().startswith(b"ISO-10303-21"):
        raise ScanError("not an IFC file (no ISO-10303-21 header)")
    m = re.search(rb"FILE_SCHEMA\s*\(\s*\(\s*'([^']*)'", head)
    return m.group(1).decode().upper() if m else ""


def _init_piece_worker(parent: int) -> None:
    from . import resources
    resources.watch_parent(parent)
    resources.raise_priority()      # not inherited from the worker: the designer waits for the pieces


def read_pieces(path: str, workers: int, progress: Callable[[float], None], cancelled=None) -> tuple[list, int]:
    """Every piece of the file read, by `workers` processes (1: this one), with the share of bytes done."""
    size = os.path.getsize(path)
    piece = PIECE if size > SMALL_FILE else size + 1
    ranges = _pieces(path, size, piece)
    parts: list = []
    done = 0
    if workers <= 1 or len(ranges) == 1:
        for a, b in ranges:
            parts.append(read_piece(path, a, b))
            done += b - a
            progress(done / size)
            if cancelled is not None and cancelled():
                break
        return parts, 1
    import concurrent.futures
    import multiprocessing
    workers = min(workers, len(ranges))
    ctx = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(workers, mp_context=ctx, initializer=_init_piece_worker,
                                                initargs=(os.getpid(),)) as pool:
        futures = [pool.submit(read_piece, path, a, b) for a, b in ranges]
        order = {f: k for k, f in enumerate(futures)}
        got: dict = {}
        for fut in concurrent.futures.as_completed(futures):
            r = fut.result()
            got[order[fut]] = r
            done += r["bytes"]
            progress(done / size)
        parts = [got[k] for k in range(len(futures))]
    return parts, workers


def _unit_scale(model: Model) -> float:
    for rid, (t, _raw) in model.small.items():
        if t != "IFCUNITASSIGNMENT":
            continue
        for u in model.get(rid)[1][0]:
            rec = model.get(u)
            if rec is None:
                continue
            ut, ua = rec
            if ut == "IFCSIUNIT" and ua[1] == ".LENGTHUNIT.":
                return SI_PREFIX.get((ua[2] or "").strip("."), 1.0)
            if ut == "IFCCONVERSIONBASEDUNIT" and ua[1] == ".LENGTHUNIT.":
                mw = model.get(ua[3])
                if mw is not None:
                    value = mw[1][0]
                    value = value.value if isinstance(value, Typed) else value
                    inner = model.get(mw[1][1])
                    k = 1.0
                    if inner is not None and inner[0] == "IFCSIUNIT":
                        k = SI_PREFIX.get((inner[1][2] or "").strip("."), 1.0)
                    return float(value) * k
    return 1.0


def _dms(v) -> float | None:
    if not isinstance(v, list) or len(v) < 2:
        return None
    sign = -1.0 if any(float(x) < 0 for x in v) else 1.0
    parts = [abs(float(x)) for x in v] + [0, 0, 0]
    return sign * (parts[0] + parts[1] / 60 + parts[2] / 3600 + parts[3] / 3.6e9)


def scan(path, progress: Callable[[float, str], None] | None = None, workers: int | None = None,
         cancelled=None) -> Scan:
    """The elements with a shape of the file at `path`, read the fast way (the module's docstring). `progress(fraction,
    what)`: "scan" while the pieces are read (to 0.7), "solids" while the elements are made. ScanError for a file that
    is not IFC."""
    tell = progress or (lambda _f, _w: None)
    path = str(path)
    t0 = time.perf_counter()
    try:
        size = os.path.getsize(path)
    except OSError as error:
        raise ScanError(str(error)) from None
    schema = _schema(path)
    if workers is None:
        from . import resources
        workers = 1 if size <= SMALL_FILE else resources.workers_for(max(1, size // PIECE), per_worker=600 << 20)
    tell(0.0, "scan")
    parts, used = read_pieces(path, workers, lambda x: tell(0.7 * x, "scan"), cancelled)
    times = {"pieces": time.perf_counter() - t0}
    counts: dict = {}
    for p in parts:
        for k, v in p["counts"].items():
            counts[k] = counts.get(k, 0) + v
    t = time.perf_counter()
    model = Model(parts)
    del parts
    times["index"] = time.perf_counter() - t
    out = Scan(path=path, schema=schema, size=size, counts=counts, unit_m=_unit_scale(model), workers=used)
    out._model = model
    k = out.unit_m
    # the spatial structure: who aggregates and who contains whom
    parent: dict = {}
    container: dict = {}
    for rid, (t_, _raw) in model.small.items():
        if t_ == "IFCRELAGGREGATES" or t_ == "IFCRELNESTS":
            a = model.get(rid)[1]
            for child in a[5] or []:
                parent[int(child)] = int(a[4])
        elif t_ == "IFCRELCONTAINEDINSPATIALSTRUCTURE":
            a = model.get(rid)[1]
            for child in a[4] or []:
                container[int(child)] = int(a[5])
    for rid, (t_, _raw) in model.small.items():
        if t_ == "IFCBUILDING":
            out.buildings[rid] = model.get(rid)[1][2] or f"#{rid}"
        elif t_ == "IFCBUILDINGSTOREY":
            a = model.get(rid)[1]
            z = a[9] if len(a) > 9 and isinstance(a[9], (int, float)) else None
            out.storeys[rid] = (a[2] or f"#{rid}", round(float(z) * k, 3) if z is not None else None)
        elif t_ == "IFCSITE" and not out.site:
            a = model.get(rid)[1]
            lat, lon = _dms(a[9] if len(a) > 9 else None), _dms(a[10] if len(a) > 10 else None)
            elev = a[11] if len(a) > 11 and isinstance(a[11], (int, float)) else None
            out.site = {"name": a[2] or "", "lat": lat, "lon": lon,
                        "elevation": float(elev) * k if elev is not None else None}

    def top_group(eid: int) -> int:
        g, seen = eid, 0
        while g in parent and model.type_of(parent[g]) not in SPATIAL and seen < 50:
            g, seen = parent[g], seen + 1
        return g

    def spatial_of(eid: int):
        """The storey and the building of an element (through its group and the aggregations)."""
        g, storey, building, seen = eid, None, None, 0
        while seen < 60:
            seen += 1
            up = container.get(g, parent.get(g))
            if up is None:
                break
            ty = model.type_of(up)
            if ty == "IFCBUILDINGSTOREY" and storey is None:
                storey = up
            elif ty == "IFCBUILDING" and building is None:
                building = up
            g = up
        return storey, building
    # the products with a shape: a placement and a product definition shape where IfcProduct has them
    cache: dict = {}
    products = []
    for rid, (t_, raw) in model.small.items():
        if t_ in NOT_SOLIDS or t_ in SPATIAL or not t_.startswith("IFC"):
            continue
        if not ROOT.match(raw):
            continue
        a = model.get(rid)[1]
        if len(a) >= 7 and isinstance(a[5], Ref) and isinstance(a[6], Ref) \
                and model.type_of(a[6]) == "IFCPRODUCTDEFINITIONSHAPE" and model.type_of(a[5]) == "IFCLOCALPLACEMENT":
            products.append(rid)
    times["structure"] = time.perf_counter() - t - times["index"]
    t = time.perf_counter()
    total = len(products)
    names: dict = {}
    for n, rid in enumerate(products):
        if cancelled is not None and n % 256 == 0 and cancelled():
            break
        if n % 200 == 0:
            tell(0.7 + 0.3 * n / max(1, total), "solids")
        try:
            pts, ntris, mapped, left = model.element_points(rid, cache)
        except (ScanError, IndexError, TypeError, ValueError, KeyError, AttributeError) as error:
            out.left_out[f"error {type(error).__name__}"] = out.left_out.get(f"error {type(error).__name__}", 0) + 1
            continue
        if not len(pts):
            continue
        pts = pts * k
        ty, a = model.get(rid)
        g = top_group(rid)
        if g not in names:
            ga = model.get(g)
            names[g] = (ga[1][2] or "") if ga is not None and len(ga[1]) > 2 and isinstance(ga[1][2], str) else ""
        storey, building = spatial_of(g)
        st = out.storeys.get(storey, (None, None))
        out.elements.append(Element(
            id=rid, cls=_class_name(ty), name=a[2] if isinstance(a[2], str) else "", guid=a[0] if isinstance(a[0], str) else "",
            group=g, group_name=names[g], storey=st[0] or "", storey_z=st[1], building=building,
            lo=tuple(round(float(v), 3) for v in pts.min(axis=0)), hi=tuple(round(float(v), 3) for v in pts.max(axis=0)),
            hull=_outline2d(pts), triangles=ntris, mapped=mapped, left_out=left))
    for key, v in model.left_out.items():
        out.left_out[key] = out.left_out.get(key, 0) + v
    out.maps, out.instances = len(model.maps), model.instances
    times["solids"] = time.perf_counter() - t
    times["total"] = time.perf_counter() - t0
    out.times = times
    tell(1.0, "solids")
    return out


_CLASS_CASE: dict = {}


def _class_name(upper: str) -> str:
    """IFCBUILDINGELEMENTPROXY as IfcBuildingElementProxy, through IfcOpenShell's schema when it is there."""
    hit = _CLASS_CASE.get(upper)
    if hit is None:
        hit = upper
        try:
            import ifcopenshell.ifcopenshell_wrapper as w
            for name in ("IFC4", "IFC2X3", "IFC4X3_ADD2"):
                try:
                    hit = w.schema_by_name(name).declaration_by_name(upper).name()
                    break
                except (RuntimeError, ValueError, AttributeError):
                    continue
        except ImportError:
            pass
        _CLASS_CASE[upper] = hit
    return hit
