"""The ground of an imported IFC model (R602): the height its zero takes in Meridiana, and where the lawn opens.

Meridiana's lawn is a flat plane at the height 0 of the 3D; an imported model stands on it at one height of its own,
the model's zero. That zero was the ground floor (ifc_read.Structure.ground): on a site whose ground is not at the
ground floor, the pavings and the parking places of the model flew over the lawn or sank under it (Daniel 14/11/2026,
a model whose terrain is 0.47 m under its ground floor at the foot of the building and slopes there by 1.4 m).

The model's zero, one for the whole model (the bodies, the solids and the true geometry), comes in this order:
a. the model's terrain (ifc_terrain): the prevailing height of its top at the foot of the buildings, the median by
   area of its faces looking up in a band GROUND_BAND wide, EDGE outside the outline of the buildings and of their
   basements (the faces under them are the dig of the basement); at least MIN_AREA of them;
b. else the pavings at the ground: the slabs (and the paving classes of IFC4X3) standing mostly outside the outline,
   in the same band, whose top is within PAVING_REACH of the ground floor: the median of their tops by area, when it
   is not above the ground floor (ABOVE): the flat lawn at a zero over it would bury the ground floor (two models of the
   bench took a terrace 1 m over their ground floor for their ground);
c. else the ground floor, as before.
No terrain is made up where the file has none.

No single flat lawn puts a sloping site flush (model A: its pavings from -0.43 to +1.34 m over its ground floor), so
inside the site the lawn is the model's terrain itself (`top_surface`, `lawn_surface`): its top faces, and the walls of
its dig, a little under their true height (DROP: a paving flush with the terrain is not hidden by it). With the model's
terrain drawn, the model draws it and the lawn leaves its place. Around the site a slope (`RAMP_MIN`, `RAMP_SLOPE`)
joins the edge of the terrain to the flat lawn at the zero. The basements and half basements stay out of it: the
terrain is dug for them in the model; outside the terrain the lawn opens on the plan of the parts reaching BELOW under
the zero and not rising TOP over the ground floor (`openings`), never buried in the lawn. Only while the model's true
geometry is shown; a project imported before keeps its flat lawn. Without Qt."""

from __future__ import annotations

import numpy as np

GROUND_BAND = 5.0           # m outside the outline of the buildings: the foot of the buildings
MIN_AREA = 10.0             # m2 of terrain or paving in the band for its height to count
SLOPE = 0.5                 # m between the 10th and the 90th percentile: the ground slopes at the foot
PAVING_REACH = 2.0          # m: a paving's top this near the ground floor is at the ground
EDGE = 0.5                  # m: the band starts this far from the outline (the dig's edge, a wall's thickness)
ABOVE = 0.05                # m: pavings whose median top is higher over the ground floor do not give the zero (b)
TRUST = 5.0                 # m: a terrain or paving farther than this from the ground floor is not the ground of it
OUTSIDE = 0.5               # share of a paving's plan outside the outline: «mostly outside»
UP = 0.5                    # a face looks up when its normal is within 60 degrees of the vertical
BELOW = 1.0                 # m under the zero: a part reaching deeper is a basement or a half basement and opens the lawn
TOP = 1.0                   # m above the ground floor: a part rising higher stands on the ground (a neighbour's mass on a
                            # lower ground), it is no basement
OPEN_MIN = 2.0              # m2: a smaller opening (a plinth, a pit) is left closed
CLOSE = 0.5                 # m: openings this near are one (the strips of a foundation make one plan)
SIMPLIFY = 0.2              # m
SURFACE_MAX = 20000         # faces of the terrain's top kept for the lawn; a terrain with more keeps the flat lawn
DROP = 0.03                 # m: the lawn on the terrain this much under it (a paving flush with it stays on top)
SIDE = 0.3                  # m from the edge of the terrain's plan: a steep face there is its outer side, not a dig
RAMP_MIN = 8.0              # m: the shortest slope from the terrain's edge to the flat lawn around it
RAMP_SLOPE = 5.0            # its run over its rise at least (20 %)
MITRE = 3.0                 # at a sharp corner of the terrain the slope reaches out at most this many times its run
PAVING = ("IFCSLAB", "IFCSLABSTANDARDCASE", "IFCSLABELEMENTEDCASE", "IFCPAVEMENT", "IFCCOURSE")
OUTLINE = ("IFCWALL", "IFCWALLSTANDARDCASE", "IFCWALLELEMENTEDCASE", "IFCCURTAINWALL", "IFCCOLUMN",
           "IFCCOLUMNSTANDARDCASE", "IFCROOF")


def _polygon(ring):
    from shapely.geometry import Polygon
    return Polygon([(float(x), float(y)) for x, y in ring]).buffer(0)


def outline(buildings: list, solids: list, floor: float | None = None):
    """The outline of the buildings in the model's world plan (shapely), None without any: the union of the footprints
    of the bodies read (ifc_read), else of the plans of the walls, columns and roofs of the solids (closed by 1 m);
    with the plan of its basement (`_below` the ground floor `floor`: a basement reaching past the roofs, where the
    terrain is dug; model A's dig at -3.2 m stood in the band of the roofs' outline)."""
    import shapely
    rings = [b["footprint"] for b in buildings or [] if len(b.get("footprint") or []) >= 3]
    if rings:
        parts = [_polygon(r) for r in rings]
    else:
        parts = [_polygon(s["hull"]) for s in solids or [] if not s.get("terrain")
                 and str(s.get("cls") or "").upper() in OUTLINE and len(s.get("hull") or []) >= 3]
        if not parts:
            return None
        parts = [shapely.union_all(parts).buffer(1.0).buffer(-1.0)]
    if floor is not None:
        parts += _below(solids, floor, floor)
    union = _filled(shapely.union_all(parts).buffer(CLOSE).buffer(-CLOSE))
    return None if union.is_empty or union.area <= 0 else union


def _filled(geometry):
    """`geometry` without its holes (a courtyard is inside the buildings)."""
    import shapely
    from shapely.geometry import Polygon
    parts = [g for g in getattr(geometry, "geoms", [geometry]) if g.geom_type == "Polygon" and not g.is_empty]
    return shapely.union_all([Polygon(g.exterior) for g in parts]) if parts else geometry


def weighted(values, weights, share: float) -> float:
    """The value under which `share` of the weight lies."""
    v, w = np.asarray(values, float), np.asarray(weights, float)
    order = np.argsort(v)
    cumulative = np.cumsum(w[order])
    return float(v[order][min(len(v) - 1, int(np.searchsorted(cumulative, share * cumulative[-1])))])


def _summary(z, w, source: str) -> dict | None:
    if not len(z) or float(np.sum(w)) < MIN_AREA:
        return None
    return {"height": weighted(z, w, 0.5), "from": source, "low": weighted(z, w, 0.1), "high": weighted(z, w, 0.9),
            "area": round(float(np.sum(w)), 1)}


def from_terrain(triangles: list, band) -> dict | None:
    """The height of the terrain's top within `band`: its triangles (each element's (n, 3, 3) in world metres) that look
    up, cut by the band, their height at the middle of the part inside, weighted by its plan area."""
    import shapely
    z_all, w_all = [], []
    for tri in triangles:
        tri = np.asarray(tri, float).reshape(-1, 3, 3)
        if not len(tri):
            continue
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        length = np.linalg.norm(n, axis=1)
        up = (length > 1e-12) & (n[:, 2] > UP * np.maximum(length, 1e-12))
        tri, n = tri[up], n[up]
        if not len(tri):
            continue
        plans = shapely.polygons(np.concatenate([tri[:, :, :2], tri[:, :1, :2]], axis=1))
        inside = shapely.intersection(plans, band)
        area = shapely.area(inside)
        keep = area > 1e-6
        if not keep.any():
            continue
        middle = shapely.get_coordinates(shapely.centroid(inside[keep]))
        t, nk = tri[keep], n[keep]
        # the plane of each face: n . (p - p0) = 0
        z = t[:, 0, 2] - (nk[:, 0] * (middle[:, 0] - t[:, 0, 0]) + nk[:, 1] * (middle[:, 1] - t[:, 0, 1])) / nk[:, 2]
        z_all.append(z)
        w_all.append(area[keep])
    if not z_all:
        return None
    return _summary(np.concatenate(z_all), np.concatenate(w_all), "terrain")


def from_paving(solids: list, shape, band, floor: float) -> dict | None:
    """The height of the pavings at the ground: the solids (ifc_worker.compact) of a paving class, mostly outside the
    outline `shape`, reaching into `band`, with their top within PAVING_REACH of the ground floor `floor`: their tops,
    weighted by their plan area in the band."""
    z, w = [], []
    for s in solids or []:
        if s.get("terrain") or str(s.get("cls") or "").upper() not in PAVING or len(s.get("hull") or []) < 3:
            continue
        top = float(s["z1"])
        if abs(top - floor) > PAVING_REACH:
            continue
        plan = _polygon(s["hull"])
        if plan.area <= 0 or plan.difference(shape).area < OUTSIDE * plan.area:
            continue
        a = plan.intersection(band).area
        if a > 0:
            z.append(top)
            w.append(a)
    return _summary(np.asarray(z), np.asarray(w), "paving")


def zero(floor: float, buildings: list, solids: list, terrain: list) -> dict | None:
    """The model's zero from its site (a, then b of the module's rule), None when neither gives one (c: the ground
    floor `floor` stays). `buildings` the bodies read (ifc_read), `solids` the scan's elements (ifc_worker.compact),
    `terrain` the triangles of each terrain element in world metres. {"height", "from": "terrain" or "paving", "low",
    "high" (10th and 90th percentile), "area" m2, "floor"}. The reading's `site_ground` (ifc_worker.site_ground) adds
    "outline", the terrain's plan (`terrain_outline`), also when it has no height."""
    shape = outline(buildings, solids, floor)
    if shape is None:
        return None
    band = shape.buffer(EDGE + GROUND_BAND).difference(shape.buffer(EDGE))
    for found in (from_terrain(terrain, band) if terrain else None, from_paving(solids, shape, band, floor)):
        if found is not None and found["from"] == "paving" and found["height"] > floor + ABOVE:
            continue                    # a terrace or a podium over the ground floor, not the ground
        if found is not None and abs(found["height"] - floor) <= TRUST:
            return {**{k: round(v, 3) if isinstance(v, float) else v for k, v in found.items()},
                    "floor": round(float(floor), 3)}
    return None


def grounded(found: dict) -> dict:
    """`found` (ifc_worker.read) with the model's zero of its site (`site_ground`) as the ground of every body, support
    and solid; `found` itself without it (a reading made before, or a site that gives none)."""
    site = found.get("site_ground")
    if not isinstance(site, dict) or site.get("height") is None or site.get("from") not in ("terrain", "paving"):
        return found
    h = float(site["height"])
    return {**found, "solids_ground": h,
            "buildings": [{**b, "ground": h} for b in found.get("buildings") or []],
            "supports": [{**s, "ground": h} for s in found.get("supports") or []]}


def _below(solids: list, level: float, floor: float, skip=()) -> list:
    """The plans of the basement: the parts (not the terrain, not in `skip`) whose lowest point is more than BELOW under
    `level` and whose top is not more than TOP above the ground floor `floor`. On model A (studio R602) a rule of 0.3 m
    without the top opened 11 592 m2 of lawn, 8 871 outside the roofs: the masses of the neighbours standing on the
    lower side of the slope and the pavings there; with the top 4 444 m2 (1 728 outside), with 1 m 2 990 m2 (342)."""
    skip = {int(i) for i in skip or ()}
    parts = [_polygon(s["hull"]) for s in solids or []
             if not s.get("terrain") and int(s.get("id", -1)) not in skip and len(s.get("hull") or []) >= 3
             and float(s["z0"]) < level - BELOW and float(s["z1"]) <= floor + TOP]
    return [p for p in parts if p.area > 0]


def openings(solids: list, zero_height: float, floor: float, skip=()) -> list:
    """Where the lawn opens: the plan of the basement under the model's zero (`_below`), closed by CLOSE, without holes
    and simplified, the pieces under OPEN_MIN left out. Rings in the model's world plan, metres."""
    import shapely
    parts = _below(solids, zero_height, floor, skip)
    if not parts:
        return []
    union = _filled(shapely.union_all(parts).buffer(CLOSE).buffer(-CLOSE))
    return _rings(union, OPEN_MIN)


def terrain_outline(triangles: list) -> list:
    """The plan of the model's terrain: its faces looking up (each element's (n, 3, 3) triangles in world metres)
    together, without holes. Rings in the model's world plan. (The scan's plan of an element is the hull of its points,
    a star for a terrain of a few corners.)"""
    import shapely
    plans = []
    for tri in triangles or []:
        tri = np.asarray(tri, float).reshape(-1, 3, 3)
        if not len(tri):
            continue
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        up = n[:, 2] > UP * np.maximum(np.linalg.norm(n, axis=1), 1e-12)
        if up.any():
            t = tri[up][:, :, :2]
            plans.append(shapely.polygons(np.concatenate([t, t[:, :1]], axis=1)))
    if not plans:
        return []
    union = shapely.union_all(np.concatenate(plans)).buffer(0.05).buffer(-0.05)
    return _rings(_filled(union), OPEN_MIN)


def _normals(tri: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    return n, np.maximum(np.linalg.norm(n, axis=1), 1e-12)


def _site(up: np.ndarray):
    """The plan of the faces looking up (n, 3, 3), together and without holes (shapely), None without any."""
    import shapely
    if not len(up):
        return None
    t = up[:, :, :2]
    union = _filled(shapely.union_all(shapely.polygons(np.concatenate([t, t[:, :1]], axis=1))).buffer(0.05)
                    .buffer(-0.05))
    return None if union.is_empty else union


def top_surface(triangles: list) -> dict | None:
    """The faces of the model's terrain the lawn is made of (each element's (n, 3, 3) triangles in world metres): those
    looking up, and the steep ones inside its plan (the walls of the dig of a basement); not those looking down nor its
    outer sides. {"triangles": [[x1, y1, z1, x2, ... z3]...] to the mm} or, past SURFACE_MAX, {"faces": n}; None without
    a terrain."""
    tri = [np.asarray(t, float).reshape(-1, 3, 3) for t in triangles or [] if len(t)]
    if not tri:
        return None
    tri = np.concatenate(tri)
    n, length = _normals(tri)
    up = n[:, 2] > UP * length
    site = _site(tri[up])
    if site is None:
        return None
    import shapely
    steep = (np.abs(n[:, 2]) <= UP * length) & (length > 1e-9)
    if steep.any():
        middle = shapely.points(tri[steep].mean(axis=1)[:, :2])
        inner = shapely.distance(middle, site.boundary) > SIDE
        steep[np.flatnonzero(steep)[~inner]] = False
    keep = tri[up | steep]
    # once each (model A's terrain gave 349 of its 1 430 faces looking up twice: its outer edge was then met twice and
    # read as inside, and no slope was made)
    canon = np.sort(np.round(keep * 1000).astype(np.int64).reshape(-1, 3, 3).view(
        [("x", np.int64), ("y", np.int64), ("z", np.int64)]).reshape(-1, 3), axis=1)
    _u, first = np.unique(canon.view(np.int64).reshape(len(keep), -1), axis=0, return_index=True)
    keep = keep[np.sort(first)]
    if len(keep) > SURFACE_MAX:
        return {"faces": int(len(keep))}
    return {"triangles": np.round(keep.reshape(-1, 9), 3).tolist()}


def lawn_surface(surface: dict, zero_height: float) -> dict | None:
    """The lawn on the site from the terrain's top (`top_surface`) for the model's zero `zero_height`: {"drape": its
    faces DROP under them, "ramp": the slope from its outer edge down (or up) to the zero, "hole": the plan of both,
    where the flat lawn opens (rings)}, faces as `top_surface`'s, all in the model's world. The slope runs out from each
    outer edge of the faces looking up, RAMP_SLOPE times its greatest rise and at least RAMP_MIN long."""
    import shapely
    from shapely.geometry import Polygon
    tri = np.asarray((surface or {}).get("triangles") or [], float).reshape(-1, 3, 3)
    if not len(tri):
        return None
    n, length = _normals(tri)
    up = tri[n[:, 2] > UP * length]
    site = _site(up)
    if site is None:
        return None
    # the edges of the faces looking up met once, on the edge of the site: the terrain's outer edge
    keys = np.round(up * 1000).astype(np.int64)
    count: dict = {}
    for k in range(len(up)):
        for i, j in ((0, 1), (1, 2), (2, 0)):
            a, b = tuple(keys[k, i]), tuple(keys[k, j])
            edge = (a, b) if a <= b else (b, a)
            count[edge] = count.get(edge, 0) + 1
    edges, outward = [], {}
    boundary = site.boundary
    for k in range(len(up)):
        for i, j, o in ((0, 1, 2), (1, 2, 0), (2, 0, 1)):
            a, b = tuple(keys[k, i]), tuple(keys[k, j])
            if count[(a, b) if a <= b else (b, a)] != 1:
                continue
            pa, pb, pc = up[k, i], up[k, j], up[k, o]
            if boundary.distance(shapely.Point((pa[:2] + pb[:2]) / 2)) > SIDE:
                continue
            d = pb[:2] - pa[:2]
            normal = np.array([d[1], -d[0]])
            if np.dot(normal, pc[:2] - pa[:2]) > 0:
                normal = -normal
            size = np.linalg.norm(normal)
            if size < 1e-9:
                continue
            normal /= size
            edges.append((a, b, pa, pb))
            for key in (a, b):
                outward.setdefault(key, []).append(normal)
    drape = tri.copy()
    drape[:, :, 2] -= DROP
    ramp, plans = [], []
    if edges:
        rise = max(abs(float(p[2]) - zero_height) for _a, _b, pa, pb in edges for p in (pa, pb))
        run = max(RAMP_MIN, RAMP_SLOPE * rise)

        def out(key, p):
            # mitred: `run` square to each edge at the vertex, at most MITRE times along a sharp corner
            normals = outward[key]
            v = np.sum(normals, axis=0)
            v = v / max(np.linalg.norm(v), 1e-9)
            reach = run / max(min(float(np.dot(v, n)) for n in normals), 1.0 / MITRE)
            return np.array([p[0] + reach * v[0], p[1] + reach * v[1], zero_height])
        for a, b, pa, pb in edges:
            qa, qb = pa - (0, 0, DROP), pb - (0, 0, DROP)
            ra, rb = out(a, pa), out(b, pb)
            ramp += [[qa, qb, rb], [qa, rb, ra]]
            plans.append(Polygon([qa[:2], qb[:2], rb[:2], ra[:2]]).buffer(0))
    hole = _filled(shapely.union_all([site] + [p for p in plans if p.area > 0]).buffer(0.05).buffer(-0.05))
    flat = (lambda a: np.round(np.asarray(a, float).reshape(-1, 9), 3).tolist())
    return {"drape": flat(drape), "ramp": flat(ramp) if ramp else [], "hole": _rings(hole, OPEN_MIN, 0.02)}


def _rings(geometry, smallest: float, simplify: float = SIMPLIFY) -> list:
    out = []
    for g in getattr(geometry, "geoms", [geometry]):
        if g.geom_type != "Polygon" or g.area < smallest:
            continue
        ring = list(g.simplify(simplify).exterior.coords)[:-1]
        if len(ring) >= 3:
            out.append([[round(float(x), 3), round(float(y), 3)] for x, y in ring])
    return out


def _drawn(ctx: dict) -> bool:
    """Whether the model's terrain is drawn by the model itself (asked at the import: not among the elements left out)."""
    terrain = {int(i) for i in ctx.get("terrain") or []}
    return bool(terrain) and not terrain <= {int(i) for i in ctx.get("skip") or []}


def _to_plan(points: np.ndarray, turn: float, move) -> np.ndarray:
    """Points (..., 2+) of the model's world brought to the plan by the import's frame (world = R(turn) plan + move)."""
    import math
    c, s = math.cos(turn), math.sin(turn)
    p = np.array(points, float)
    x, y = p[..., 0] - move[0], p[..., 1] - move[1]
    p[..., 0], p[..., 1] = c * x + s * y, -s * x + c * y
    return p


def lawn(ref: dict, turn: float, move, centre, half: float):
    """The flat lawn of the 3D in the plan (shapely), None when it is the plain square: the square of `half` about
    `centre` (east, north) less the openings of the import's reference `ref` (ifc_import.reference: `context["open"]`,
    the site's lawn `context["lawn"]["hole"]`, or `context["terrain_outline"]` when the terrain is drawn and has no
    lawn of its own), brought from the model's world to the plan by the frame of the import as the bodies are now
    (ifc_export.frame_of: world = R(turn) plan + move)."""
    import shapely
    from shapely.geometry import Polygon, box
    ctx = (ref or {}).get("context") or {}
    rings = list(ctx.get("open") or [])
    site = ctx.get("lawn") if isinstance(ctx.get("lawn"), dict) else None
    if site:
        rings += list(site.get("hole") or [])
    elif _drawn(ctx):
        rings += list(ctx.get("terrain_outline") or [])
    if not rings:
        return None
    holes = []
    for ring in rings:
        g = Polygon(_to_plan(np.asarray(ring, float), turn, move)).buffer(0)
        if g.area > 0:
            holes.append(g)
    square = box(centre[0] - half, centre[1] - half, centre[0] + half, centre[1] + half)
    if not holes:
        return None
    out = square.difference(shapely.union_all(holes))
    return None if out.equals(square) else out


def lawn_triangles(project, centre, half: float) -> np.ndarray | None:
    """The lawn of the 3D for the project as it is now, as triangles (n, 3, 3) in the plan (east, north, height over
    the zero): the flat lawn of `lawn` at 0, and the site's lawn (`lawn_surface`: its slope, and the terrain itself
    unless the model draws it). None for the plain square (no import, an import without openings nor site, or its
    frame lost)."""
    import shapely
    from . import ifc_export
    ref = (getattr(project, "resources", None) or {}).get("ifc_reference")
    if not isinstance(ref, dict) or not isinstance(ref.get("context"), dict):
        return None
    ctx = ref["context"]
    site = ctx.get("lawn") if isinstance(ctx.get("lawn"), dict) else None
    if not ctx.get("open") and not ctx.get("terrain_outline") and not site:
        return None
    frame, _why = ifc_export.frame_of(project)
    if frame is None:
        return None
    turn, move = float(frame["turn"]), frame["move"]
    parts = []
    shape = lawn(ref, turn, move, centre, half)
    if shape is None and site:
        from shapely.geometry import box
        shape = box(centre[0] - half, centre[1] - half, centre[0] + half, centre[1] + half)
    if shape is not None and not shape.is_empty:
        pieces = shapely.constrained_delaunay_triangles(shape)
        tris = [np.asarray(g.exterior.coords)[:3] for g in getattr(pieces, "geoms", [pieces])
                if g.geom_type == "Polygon" and not g.is_empty]
        if tris:
            flat = np.zeros((len(tris), 3, 3))
            flat[:, :, :2] = np.asarray(tris, float)
            parts.append(flat)
    if site:
        zero_height = ifc_export.context_ground(ref)
        for key in ("ramp",) if _drawn(ctx) else ("ramp", "drape"):
            t = np.asarray(site.get(key) or [], float).reshape(-1, 3, 3)
            if len(t):
                t = _to_plan(t, turn, move)
                t[:, :, 2] -= zero_height
                parts.append(t)
    return np.concatenate(parts) if parts else None
