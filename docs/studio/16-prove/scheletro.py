"""Prova per lo studio 16, tema A: lo scheletro dritto (straight skeleton) come generatore dei tetti a
padiglione e a due falde su piante qualsiasi.

Che cosa prova:
- lo scheletro di polyskel (Felkel e Obdržálek 1998, LGPL-3, github.com/Botffy/polyskel) su sei piante:
  rettangolo, L, T, U, trapezio, rettangolo con un lato corto storto;
- le facce del tetto ricavate dallo scheletro con shapely (polygonize): una faccia per lato di gronda, tutte
  insieme coprono la pianta, ogni nodo dello scheletro è equidistante dai lati che lo generano (il tetto a
  padiglione con pendenze uguali);
- le due falde con le testate: i lati scelti come testata vengono spinti lontano prima dello scheletro e le
  facce vengono poi ritagliate sulla pianta (lo stesso effetto di un peso infinito sul lato);
- il tempo di calcolo.

Lancio (polyskel non è nel repository: si clona a parte):
    git clone https://github.com/Botffy/polyskel /tmp/polyskel && pip install euclid3
    python docs/studio/16-prove/scheletro.py --polyskel /tmp/polyskel [--png docs/studio/16-prove/scheletro.png]
"""

from __future__ import annotations

import argparse
import math
import sys
import time

from shapely.geometry import LineString, MultiLineString, Polygon
from shapely.ops import polygonize, unary_union

PLANS = {
    "rettangolo": [(0, 0), (20, 0), (20, 10), (0, 10)],
    "L": [(0, 0), (20, 0), (20, 8), (8, 8), (8, 18), (0, 18)],
    "T": [(0, 0), (24, 0), (24, 8), (16, 8), (16, 20), (8, 20), (8, 8), (0, 8)],
    "U": [(0, 0), (24, 0), (24, 16), (16, 16), (16, 7), (8, 7), (8, 16), (0, 16)],
    "trapezio": [(0, 0), (22, 0), (18, 10), (3, 10)],
    "lato storto": [(0, 0), (20, 0), (21.5, 10), (0, 10)],
}
# per le due falde con le testate: quali lati (indice del lato da vertice i a i+1) sono testate
GABLE_ENDS = {"rettangolo": [1, 3], "L": [1, 4], "T": [1, 4, 7], "U": [2, 6], "trapezio": [1, 3], "lato storto": [1, 3]}


def for_polyskel(ring):
    """polyskel ragiona con l'asse y verso il basso: nel nostro sistema (y verso Nord) vuole il contorno orario."""
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1], strict=True))
    return list(ring) if area < 0 else list(reversed(ring))


def skeleton_arcs(polyskel, ring):
    """Gli archi dello scheletro come segmenti, e i nodi con la loro altezza (distanza dai lati)."""
    subtrees = polyskel.skeletonize(for_polyskel(ring), [])
    arcs, nodes = [], []
    for st in subtrees:
        s = (float(st.source.x), float(st.source.y))
        nodes.append((s, float(st.height)))
        for k in st.sinks:
            arcs.append((s, (float(k.x), float(k.y))))
    return arcs, nodes


def faces_of(ring, arcs):
    """Le facce del tetto: le regioni chiuse tra il contorno e gli archi dello scheletro."""
    edges = [LineString([a, b]) for a, b in zip(ring, ring[1:] + ring[:1], strict=True)]
    edges += [LineString([a, b]) for a, b in arcs if a != b]
    merged = unary_union(MultiLineString([e for e in edges if e.length > 1e-9]))
    return [f for f in polygonize(merged) if f.area > 1e-6]


def supporting_edge(face, ring, tol=1e-6):
    """Il lato della pianta che la faccia contiene (la sua gronda), o None."""
    found = []
    for i, (a, b) in enumerate(zip(ring, ring[1:] + ring[:1], strict=True)):
        seg = LineString([a, b])
        if face.boundary.buffer(tol).contains(seg) or seg.intersection(face.boundary).length > seg.length - 1e-3:
            found.append(i)
    return found


def dist_to_line(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    return abs(dy * (p[0] - ax) - dx * (p[1] - ay)) / math.hypot(dx, dy)


def check_equidistant(ring, faces, nodes):
    """Ogni nodo dello scheletro deve stare alla stessa distanza dai lati delle facce che lo toccano, e quella
    distanza è la sua altezza: con pendenze uguali, il tetto è una sola superficie continua."""
    from shapely.geometry import Point
    worst = 0.0
    for p, h in nodes:
        here = Point(p)
        ds = [dist_to_line(p, ring[i], ring[(i + 1) % len(ring)])
              for f in faces if f.exterior.distance(here) < 1e-6 for i in supporting_edge(f, ring)]
        if len(ds) >= 2:
            worst = max(worst, max(ds) - min(ds), abs(h - sum(ds) / len(ds)))
    return worst


def hip_polyskel(polyskel, ring):
    arcs, nodes = skeleton_arcs(polyskel, ring)
    return arcs, nodes, faces_of(ring, arcs)


def hip_bpypolyskel(bpy, ring):
    """bpypolyskel (GPL-3, prochitecture): polygonize dà direttamente le facce, con l'altezza nei vertici."""
    from mathutils import Vector
    ring = for_polyskel(ring)[::-1]              # bpypolyskel vuole il contorno antiorario con y verso Nord
    verts = [Vector((x, y, 0.0)) for x, y in ring]
    faces_idx = bpy.polygonize(verts, 0, len(ring), None, 0.0, 1.0)
    faces = [Polygon([(verts[i].x, verts[i].y) for i in f]) for f in faces_idx]
    nodes = [((v.x, v.y), v.z) for v in verts[len(ring):]]
    arcs = []
    for f in faces_idx:
        for a, b in zip(f, f[1:] + f[:1], strict=True):
            if a >= len(ring) or b >= len(ring):
                arcs.append(((verts[a].x, verts[a].y), (verts[b].x, verts[b].y)))
    return arcs, nodes, faces


def hip_cgal(binary, ring):
    """Il programma C++ accanto (scheletro_cgal.cpp): le facce con l'altezza di ogni vertice."""
    import subprocess
    text = f"{len(ring)}\n" + "".join(f"{x} {y}\n" for x, y in ring)
    out = subprocess.run([binary], input=text, capture_output=True, text=True, check=True).stdout
    faces, nodes, arcs = [], [], []
    for line in out.splitlines():
        parts = line.split()
        if parts[0] != "face":
            raise RuntimeError(out.strip())
        vals = [float(v) for v in parts[1:]]
        pts = [(vals[i], vals[i + 1], vals[i + 2]) for i in range(0, len(vals), 3)]
        faces.append(Polygon([(x, y) for x, y, _z in pts]))
        nodes += [((x, y), z) for x, y, z in pts if z > 1e-9]
        arcs += [((a[0], a[1]), (b[0], b[1])) for a, b in zip(pts, pts[1:] + pts[:1], strict=True) if a[2] > 1e-9 or b[2] > 1e-9]
    return arcs, nodes, faces


BACKEND = {}


def hip(_unused, ring):
    return BACKEND["hip"](ring)


def extended_for_gables(ring, ends, far=1000.0):
    """La pianta con i lati di testata spinti lontano lungo le gronde che li toccano: la faccia della testata
    finisce fuori dalla pianta e le due falde accanto si allungano sulle loro linee di gronda (l'effetto di un
    peso infinito sul lato, come nello scheletro pesato)."""
    pts = list(ring)
    n = len(pts)
    out = list(pts)
    for i in ends:
        a, b = pts[i], pts[(i + 1) % n]
        prev_a = pts[(i - 1) % n]
        next_b = pts[(i + 2) % n]
        da = (a[0] - prev_a[0], a[1] - prev_a[1])
        db = (b[0] - next_b[0], b[1] - next_b[1])
        la, lb = math.hypot(*da), math.hypot(*db)
        out[i] = (out[i][0] + da[0] / la * far, out[i][1] + da[1] / la * far)
        out[(i + 1) % n] = (out[(i + 1) % n][0] + db[0] / lb * far, out[(i + 1) % n][1] + db[1] / lb * far)
    return out


def gable(polyskel, ring, ends):
    big = extended_for_gables(ring, ends)
    arcs, nodes, big_faces = hip(polyskel, big)
    footprint = Polygon(ring)
    faces = []
    for f in big_faces:
        if any(i in ends for i in supporting_edge(f, big)):
            continue                       # la faccia della testata: un muro, non una falda
        clipped = f.intersection(footprint)
        parts = getattr(clipped, "geoms", [clipped])
        faces += [g for g in parts if g.geom_type == "Polygon" and g.area > 1e-6]
    return arcs, nodes, faces


def random_plan(rng):
    """Una pianta rettilinea a caso: un rettangolo con 1-3 rientranze o sporgenze sui lati, quote in metri."""
    w, h = rng.uniform(8, 40), rng.uniform(6, 30)
    poly = Polygon([(0, 0), (w, 0), (w, h), (0, h)])
    for _k in range(rng.randint(1, 3)):
        bw, bh = rng.uniform(2, w / 2), rng.uniform(2, h / 2)
        x, y = rng.uniform(0, w - bw), rng.choice([-bh + 0.0, h - 0.0])
        bump = Polygon([(x, y), (x + bw, y), (x + bw, y + bh), (x, y + bh)])
        poly = poly.union(bump) if rng.random() < 0.5 else poly.difference(bump)
        if poly.geom_type != "Polygon" or poly.area < 20:
            return None
    poly = poly.simplify(0)                      # senza vertici allineati: polyskel li toglie da sé
    ring = [(round(x, 3), round(y, 3)) for x, y in poly.exterior.coords[:-1]]
    return ring if len(ring) >= 4 else None


def stress(polyskel, n):
    """Piante rettilinee a caso: quante vengono esatte (una faccia per lato, nodi equidistanti a 1e-6), quante
    solo approssimate (copertura intera, nodi fuori posto fino a 5 cm: facce fuse, come fa bpypolyskel per i
    tetti di OSM) e quante sbagliate o fallite."""
    import random
    rng = random.Random(16)
    tried = exact = near = 0
    failures = []
    t = time.perf_counter()
    while tried < n:
        ring = random_plan(rng)
        if ring is None:
            continue
        tried += 1
        try:
            arcs, nodes, faces = hip(polyskel, ring)
            area = Polygon(ring).area
            covered = abs(unary_union(faces).area - area) < 1e-3 * area
            one_each = len(faces) == len(ring) and all(len(supporting_edge(f, ring)) == 1 for f in faces)
            worst = check_equidistant(ring, faces, nodes)
        except Exception as error:      # noqa: BLE001
            failures.append((ring, f"{type(error).__name__}: {error}"))
            continue
        if covered and one_each and worst < 1e-6:
            exact += 1
        elif covered and worst < 0.05:
            near += 1
        else:
            failures.append((ring, f"{len(faces)} facce per {len(ring)} lati, nodi fuori di {worst:.3f} m"))
    print(f"piante casuali: {tried}, esatte {exact}, approssimate {near}, sbagliate o fallite {len(failures)} "
          f"({(time.perf_counter() - t) * 1000 / tried:.1f} ms l'una)")
    for ring, why in failures[:3]:
        print("  sbagliata:", why, "pianta", ring)


def report(name, ring, arcs, nodes, faces, seconds, kind):
    area = Polygon(ring).area
    covered = unary_union(faces).area
    supported = [supporting_edge(f, ring) for f in faces]
    one_each = all(len(s) == 1 for s in supported)
    worst = check_equidistant(ring, faces, nodes) if kind == "padiglione" else float("nan")
    print(f"{name:12s} {kind:10s} facce {len(faces):2d}  archi {len(arcs):2d}  copertura {covered / area * 100:6.2f}%  "
          f"una gronda per faccia: {'sì' if one_each else 'NO'}  equidistanza max {worst:.2e}  {seconds * 1000:.1f} ms")
    return {"faces": len(faces), "coverage": covered / area, "one_each": one_each, "worst": worst}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="polyskel", choices=("polyskel", "bpypolyskel", "cgal"))
    ap.add_argument("--polyskel", default="", help="directory of the polyskel clone")
    ap.add_argument("--bpypolyskel", default="", help="directory of the bpypolyskel clone (needs mathutils)")
    ap.add_argument("--cgal", default="", help="the compiled scheletro_cgal.cpp")
    ap.add_argument("--png", default="", help="where to draw the six cases")
    ap.add_argument("--stress", type=int, default=0, help="also try this many random rectilinear plans")
    args = ap.parse_args()
    polyskel = None
    if args.backend == "polyskel":
        sys.path.insert(0, args.polyskel)
        import logging

        import polyskel  # noqa: E402
        polyskel.log.setLevel(logging.ERROR)
        BACKEND["hip"] = lambda ring: hip_polyskel(polyskel, ring)
    elif args.backend == "bpypolyskel":
        sys.path.insert(0, args.bpypolyskel)
        from bpypolyskel import bpypolyskel  # noqa: E402
        BACKEND["hip"] = lambda ring: hip_bpypolyskel(bpypolyskel, ring)
    else:
        BACKEND["hip"] = lambda ring: hip_cgal(args.cgal, ring)
    print("backend:", args.backend)

    drawings = []
    for name, ring in PLANS.items():
        ring = [(float(x), float(y)) for x, y in ring]
        for kind in ("padiglione", "due falde"):
            t = time.perf_counter()
            try:
                if kind == "padiglione":
                    arcs, nodes, faces = hip(polyskel, ring)
                else:
                    arcs, nodes, faces = gable(polyskel, ring, GABLE_ENDS[name])
            except Exception as error:      # noqa: BLE001 (la prova dice che cosa è andato storto)
                print(f"{name:12s} {kind:10s} ERRORE {type(error).__name__}: {error}")
                continue
            report(name, ring, arcs, nodes, faces, time.perf_counter() - t, kind)
            drawings.append((f"{name}, {kind}", ring, faces))

    if args.stress:
        stress(polyskel, args.stress)

    if args.png:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        rows = (len(drawings) + 3) // 4
        fig, axes = plt.subplots(rows, 4, figsize=(14, 3.2 * rows))
        for ax in axes.flat:
            ax.set_axis_off()
        for ax, (title, ring, faces) in zip(axes.flat, drawings, strict=False):
            for f in faces:
                xs, ys = f.exterior.xy
                ax.fill(xs, ys, alpha=0.5)
                ax.plot(xs, ys, color="#333", linewidth=0.8)
            xs, ys = zip(*(ring + ring[:1]), strict=True)
            ax.plot(xs, ys, color="black", linewidth=1.5)
            ax.set_aspect("equal")
            ax.set_title(title, fontsize=9)
        fig.tight_layout()
        fig.savefig(args.png, dpi=90)
        print("disegno in", args.png)


if __name__ == "__main__":
    main()
