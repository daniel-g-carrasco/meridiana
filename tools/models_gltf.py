"""Decode untrusted GLB, glTF and OBJ into position, normal and sRGB vertex-colour arrays. Adapted from docs/studio/30-modelli-liberi/prove/gltf_a_mesh.py on r10-persone. Images are decoded as data only. Large textures use a 9 by 9 neighbourhood at each vertex UV, small palettes use one sample."""

from __future__ import annotations
import io
import json
import math
import struct
from pathlib import Path
import numpy as np
from PIL import Image

_COMP = {
    5120: np.int8,
    5121: np.uint8,
    5122: np.int16,
    5123: np.uint16,
    5125: np.uint32,
    5126: np.float32,
}
_NCOMP = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT2": 4,
    "MAT3": 9,
    "MAT4": 16,
}


class Unsupported(Exception):
    """The minimal reader cannot handle this file feature."""


def _srgb_to_lin(c):
    c = np.asarray(c, dtype=np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _lin_to_srgb(c):
    c = np.clip(np.asarray(c, dtype=np.float32), 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


class Gltf:
    def __init__(self, path: Path):
        path = Path(path)
        self.dir = path.parent
        raw = path.read_bytes()
        self.bin = None
        if raw[:4] == b"glTF":
            _, version, length = struct.unpack_from("<III", raw, 0)
            if version != 2 or length != len(raw):
                raise Unsupported("invalid GLB header")
            off = 12
            while off < len(raw):
                size, kind = struct.unpack_from("<II", raw, off)
                body = raw[off + 8 : off + 8 + size]
                if kind == 1313821514:
                    self.j = json.loads(body.decode("utf8"))
                elif kind == 5130562 and self.bin is None:
                    self.bin = body
                off += 8 + size + -size % 4
        else:
            self.j = json.loads(raw.decode("utf8"))
        bad = {
            "KHR_draco_mesh_compression",
            "EXT_meshopt_compression",
            "KHR_mesh_quantization",
        }
        used = set(self.j.get("extensionsRequired", [])) & bad
        if used:
            raise Unsupported(
                "unsupported required extensions: " + ", ".join(sorted(used))
            )
        self._buffers = {}
        self._images = {}
        self.stats = dict(
            textures=[],
            transparent=False,
            skinned=False,
            animated=bool(self.j.get("animations")),
            materials=len(self.j.get("materials", [])),
            file_bytes=len(raw),
        )

    def _buffer(self, index):
        if index not in self._buffers:
            b = self.j["buffers"][index]
            if "uri" not in b:
                self._buffers[index] = self.bin
            elif b["uri"].startswith("data:"):
                import base64

                self._buffers[index] = base64.b64decode(b["uri"].split(",", 1)[1])
            else:
                p = (self.dir / b["uri"].replace("%20", " ")).resolve()
                if self.dir.resolve() not in p.parents:
                    raise Unsupported("path outside asset folder: " + b["uri"])
                self._buffers[index] = p.read_bytes()
        return self._buffers[index]

    def accessor(self, index):
        a = self.j["accessors"][index]
        if "sparse" in a:
            raise Unsupported("sparse accessor")
        dtype = np.dtype(_COMP[a["componentType"]])
        n = _NCOMP[a["type"]]
        count = a["count"]
        if "bufferView" not in a:
            out = np.zeros((count, n), dtype=dtype)
        else:
            bv = self.j["bufferViews"][a["bufferView"]]
            buf = self._buffer(bv["buffer"])
            start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
            stride = bv.get("byteStride") or dtype.itemsize * n
            if stride == dtype.itemsize * n:
                out = np.frombuffer(
                    buf, dtype=dtype, count=count * n, offset=start
                ).reshape(count, n)
            else:
                out = np.empty((count, n), dtype=dtype)
                for i in range(count):
                    out[i] = np.frombuffer(
                        buf, dtype=dtype, count=n, offset=start + i * stride
                    )
        if a.get("normalized"):
            info = np.iinfo(dtype)
            out = np.maximum(out.astype(np.float32) / info.max, -1.0)
        return out

    def image(self, index):
        if index not in self._images:
            im = self.j["images"][index]
            if "bufferView" in im:
                bv = self.j["bufferViews"][im["bufferView"]]
                buf = self._buffer(bv["buffer"])
                data = buf[
                    bv.get("byteOffset", 0) : bv.get("byteOffset", 0) + bv["byteLength"]
                ]
                img = Image.open(io.BytesIO(data))
            elif im["uri"].startswith("data:"):
                import base64

                img = Image.open(
                    io.BytesIO(base64.b64decode(im["uri"].split(",", 1)[1]))
                )
            else:
                p = (self.dir / im["uri"].replace("%20", " ")).resolve()
                if self.dir.resolve() not in p.parents:
                    raise Unsupported("path outside asset folder: " + im["uri"])
                img = Image.open(p)
            img.load()
            self._images[index] = np.asarray(img.convert("RGBA"), dtype=np.uint8)
        return self._images[index]

    def _material(self, index):
        """Return sRGB factor, texture image index, UV set and transparency."""
        if index is None:
            return (np.array([0.8, 0.8, 0.8], np.float32), None, 0, False)
        m = self.j["materials"][index]
        pbr = m.get("pbrMetallicRoughness", {})
        f = np.asarray(pbr.get("baseColorFactor", [1, 1, 1, 1]), np.float32)
        tex = pbr.get("baseColorTexture")
        ti = None
        uvset = 0
        if tex is not None:
            src = self.j["textures"][tex["index"]]
            ti = src.get("source")
            uvset = tex.get("texCoord", 0)
        transparent = m.get("alphaMode") == "BLEND" or f[3] < 0.999
        return (_lin_to_srgb(f[:3]), ti, uvset, transparent)

    def _sample(self, image_index, uv):
        """Sample UV colours, weighting opaque pixels and falling back to the mean opaque colour."""
        img = self.image(image_index)
        h, w = img.shape[:2]
        rgb = img[:, :, :3].astype(np.float32) / 255.0
        al = (img[:, :, 3].astype(np.float32) / 255.0 > 0.5).astype(np.float32)
        full = (
            (rgb * al[..., None]).sum(axis=(0, 1)) / max(al.sum(), 1.0)
            if al.any()
            else np.array([0.5, 0.5, 0.5], np.float32)
        )
        u = np.mod(uv[:, 0], 1.0) * w
        v = np.mod(uv[:, 1], 1.0) * h
        x = np.clip(u.astype(int), 0, w - 1)
        y = np.clip(v.astype(int), 0, h - 1)
        r = 0 if w * h <= 64 * 64 else 4
        acc = np.zeros((len(uv), 3), np.float32)
        wt = np.zeros(len(uv), np.float32)
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                yy, xx = (np.clip(y + dy, 0, h - 1), np.clip(x + dx, 0, w - 1))
                a = al[yy, xx]
                acc += rgb[yy, xx] * a[:, None]
                wt += a
        px = np.where(
            wt[:, None] > 0, acc / np.maximum(wt, 1e-06)[:, None], full[None, :]
        )
        return (px, (w, h))

    @staticmethod
    def _local(node):
        if "matrix" in node:
            return np.asarray(node["matrix"], np.float64).reshape(4, 4).T
        t = np.asarray(node.get("translation", [0, 0, 0]), np.float64)
        q = np.asarray(node.get("rotation", [0, 0, 0, 1]), np.float64)
        s = np.asarray(node.get("scale", [1, 1, 1]), np.float64)
        x, y, z, w = q
        r = np.array(
            [
                [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
            ]
        )
        m = np.eye(4)
        m[:3, :3] = r * s
        m[:3, 3] = t
        return m

    def to_mesh(self):
        j = self.j
        scene = (
            j["scenes"][j.get("scene", 0)]
            if j.get("scenes")
            else {"nodes": list(range(len(j["nodes"])))}
        )
        P, N, C = ([], [], [])

        def walk(i, parent):
            node = j["nodes"][i]
            world = parent @ self._local(node)
            if "skin" in node:
                self.stats["skinned"] = True
            if "mesh" in node:
                for prim in j["meshes"][node["mesh"]]["primitives"]:
                    self._primitive(prim, world, P, N, C)
            for c in node.get("children", []):
                walk(c, world)

        for i in scene["nodes"]:
            walk(i, np.eye(4))
        if not P:
            raise Unsupported("no triangles")
        return (np.concatenate(P), np.concatenate(N), np.concatenate(C))

    def _primitive(self, prim, world, P, N, C):
        if prim.get("mode", 4) != 4:
            raise Unsupported("non-triangle primitive")
        if "KHR_draco_mesh_compression" in prim.get("extensions", {}):
            raise Unsupported("Draco")
        attr = prim["attributes"]
        pos = self.accessor(attr["POSITION"]).astype(np.float64)
        idx = (
            self.accessor(prim["indices"]).reshape(-1).astype(np.int64)
            if "indices" in prim
            else np.arange(len(pos))
        )
        nrm = (
            self.accessor(attr["NORMAL"]).astype(np.float64)
            if "NORMAL" in attr
            else None
        )
        factor, tex, uvset, transparent = self._material(prim.get("material"))
        if transparent:
            self.stats["transparent"] = True
        col = np.tile(factor, (len(pos), 1))
        uvname = f"TEXCOORD_{uvset}"
        if tex is not None and uvname in attr:
            uv = self.accessor(attr[uvname]).astype(np.float64)
            px, size = self._sample(tex, uv)
            self.stats["textures"].append(size)
            col = _lin_to_srgb(_srgb_to_lin(px) * _srgb_to_lin(factor))
        elif tex is not None:
            self.stats["textures"].append(None)
        if "COLOR_0" in attr:
            vc = self.accessor(attr["COLOR_0"]).astype(np.float32)[:, :3]
            col = _lin_to_srgb(_srgb_to_lin(col) * vc)
        p4 = np.hstack([pos, np.ones((len(pos), 1))]) @ world.T
        pos_w = p4[:, :3]
        tri = idx.reshape(-1, 3)
        if nrm is None:
            a, b, c = (pos_w[tri[:, 0]], pos_w[tri[:, 1]], pos_w[tri[:, 2]])
            fn = np.cross(b - a, c - a)
            fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
            P.append(pos_w[tri].reshape(-1, 3).astype(np.float32))
            N.append(np.repeat(fn, 3, axis=0).astype(np.float32))
            C.append(col[tri].reshape(-1, 3).astype(np.float32))
            return
        inv = np.linalg.inv(world[:3, :3]).T
        nw = nrm @ inv.T
        nw /= np.maximum(np.linalg.norm(nw, axis=1, keepdims=True), 1e-12)
        if np.linalg.det(world[:3, :3]) < 0:
            tri = tri[:, ::-1]
        P.append(pos_w[tri].reshape(-1, 3).astype(np.float32))
        N.append(nw[tri].reshape(-1, 3).astype(np.float32))
        C.append(col[tri].reshape(-1, 3).astype(np.float32))


def read_obj(path: Path):
    """Read OBJ plus optional MTL. Use diffuse colours and optional diffuse textures."""
    path = Path(path)
    lines = path.read_text(encoding="utf8", errors="replace").splitlines()
    v, vt, vn = ([], [], [])
    mtl_path = None
    cur = None
    faces = []
    for ln in lines:
        s = ln.split()
        if not s:
            continue
        if s[0] == "v":
            v.append([float(x) for x in s[1:4]])
        elif s[0] == "vt":
            vt.append([float(x) for x in s[1:3]])
        elif s[0] == "vn":
            vn.append([float(x) for x in s[1:4]])
        elif s[0] == "mtllib":
            mtl_path = (path.parent / " ".join(s[1:])).resolve()
            if path.parent.resolve() not in mtl_path.parents:
                raise Unsupported("MTL outside asset folder")
        elif s[0] == "usemtl":
            cur = " ".join(s[1:])
        elif s[0] == "f":
            faces.append(
                (
                    cur,
                    [
                        tuple(
                            (int(x) if x else 0 for x in (t.split("/") + ["", ""])[:3])
                        )
                        for t in s[1:]
                    ],
                )
            )
    mats = {}
    if mtl_path and mtl_path.exists():
        name = None
        for ln in mtl_path.read_text(encoding="utf8", errors="replace").splitlines():
            s = ln.split()
            if not s:
                continue
            if s[0] == "newmtl":
                name = " ".join(s[1:])
                mats[name] = {"kd": (0.8, 0.8, 0.8), "map": None, "d": 1.0}
            elif s[0] == "Kd" and name:
                mats[name]["kd"] = tuple((float(x) for x in s[1:4]))
            elif s[0] == "map_Kd" and name:
                mats[name]["map"] = " ".join(s[1:])
            elif s[0] in ("d",) and name:
                mats[name]["d"] = float(s[1])
    v, vt, vn = (
        np.asarray(a, np.float64)
        for a in (v, vt if vt else np.zeros((1, 2)), vn if vn else np.zeros((1, 3)))
    )
    stats = dict(
        textures=[],
        transparent=any((m["d"] < 0.999 for m in mats.values())),
        skinned=False,
        animated=False,
        materials=len(mats),
        file_bytes=path.stat().st_size,
    )
    P, N, C = ([], [], [])
    imgs = {}
    for mat, poly in faces:
        m = mats.get(mat, {"kd": (0.8, 0.8, 0.8), "map": None})
        kd = np.asarray(m["kd"], np.float32)
        for k in range(1, len(poly) - 1):
            tri = [poly[0], poly[k], poly[k + 1]]
            pts = np.array([v[t[0] - 1 if t[0] > 0 else t[0]] for t in tri])
            if all((t[2] for t in tri)):
                nn = np.array([vn[t[2] - 1 if t[2] > 0 else t[2]] for t in tri])
            else:
                fn = np.cross(pts[1] - pts[0], pts[2] - pts[0])
                fn /= max(np.linalg.norm(fn), 1e-12)
                nn = np.tile(fn, (3, 1))
            c = np.tile(kd, (3, 1))
            if m.get("map") and all((t[1] for t in tri)):
                f = path.parent / m["map"]
                if m["map"] not in imgs:
                    p = f.resolve()
                    if path.parent.resolve() not in p.parents:
                        raise Unsupported("texture outside asset folder")
                    imgs[m["map"]] = (
                        np.asarray(Image.open(p).convert("RGB"), np.uint8)
                        if p.exists()
                        else None
                    )
                im = imgs[m["map"]]
                if im is not None:
                    h, w = im.shape[:2]
                    for q, t in enumerate(tri):
                        u, vv = vt[t[1] - 1]
                        c[q] = (
                            im[
                                min(int((1 - vv) % 1.0 * h), h - 1),
                                min(int(u % 1.0 * w), w - 1),
                            ]
                            / 255.0
                        )
                    stats["textures"].append((w, h))
            P.append(pts)
            N.append(nn)
            C.append(c)
    return (
        np.concatenate(P).astype(np.float32),
        np.concatenate(N).astype(np.float32),
        np.concatenate(C).astype(np.float32),
        stats,
    )


def load(path: Path):
    """Return position, normal, colour and statistics, retaining native units and axes."""
    path = Path(path)
    if path.suffix.lower() == ".obj":
        return read_obj(path)
    g = Gltf(path)
    pos, nor, col = g.to_mesh()
    return (pos, nor, col, g.stats)


def describe(pos, col, stats):
    n = len(pos) // 3
    lo, hi = (pos.min(axis=0), pos.max(axis=0))
    q = np.round(col * 255).astype(np.int32)
    ncol = len(np.unique(q[:, 0] * 65536 + q[:, 1] * 256 + q[:, 2]))
    tex = [t for t in stats["textures"] if t]
    return dict(
        triangles=n,
        colours=ncol,
        textured=bool(stats["textures"]),
        texture_sizes=sorted({f"{w}x{h}" for w, h in tex}),
        transparent=stats["transparent"],
        skinned=stats["skinned"],
        animated=stats["animated"],
        materials=stats["materials"],
        native_size=[round(float(x), 3) for x in hi - lo],
    )


def fitted(
    pos,
    nor,
    col,
    *,
    height=None,
    length=None,
    width=None,
    yaw_deg=0.0,
    long_axis_x=None,
):
    """Scale uniformly, rotate around the vertical axis, ground and centre the mesh."""
    pos = pos.astype(np.float64).copy()
    nor = nor.astype(np.float64).copy()
    if long_axis_x is None:
        long_axis_x = bool(length)
    if long_axis_x:
        ext = pos.max(axis=0) - pos.min(axis=0)
        if ext[2] > ext[0]:
            yaw_deg += 90.0
    if yaw_deg:
        a = math.radians(yaw_deg)
        r = np.array(
            [[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]]
        )
        pos = pos @ r.T
        nor = nor @ r.T
    lo, hi = (pos.min(axis=0), pos.max(axis=0))
    ext = hi - lo
    if height:
        s = height / ext[1]
    elif length:
        s = length / ext[0]
    elif width:
        s = width / ext[2]
    else:
        s = 1.0
    pos = (pos - np.array([(lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2])) * s
    return (pos.astype(np.float32), nor.astype(np.float32), col.astype(np.float32), s)
