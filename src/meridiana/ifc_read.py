"""Reading an IFC model for what a photovoltaic design needs, and nothing more (study 20): where the site is and
where north is, the buildings with the planes of their roofs, their heights, what stands on the roofs. Without Qt;
the window runs it in a process of its own (ifc_worker.py), which it can stop at any moment: a model that makes
IfcOpenShell loop, crash or eat the memory never freezes the window (study 20, section 4).

What is read, and only that:
- the roofs: IfcRoof and its parts, IfcSlab ROOF, IfcCovering ROOFING; a building without any, its slabs; one
  without slabs either, its walls (the outline and the top); on a building with roofs, also the slabs left under the
  open sky that stand on walls (a stair tower's top, a terrace);
- what stands on a roof: chimneys, proxies, the equipment of the installations, railings and walls above the roof,
  skylights, trees; only the elements whose placement is not below the lowest roof, so the thousands of pipes of
  the floors below are never looked at;
- the site (IfcSite RefLatitude, RefLongitude, RefElevation), the true north of the model's context, the map
  conversion (IfcMapConversion in IFC4, the ePSet_MapConversion of the IFC2x3 guide), the length unit.

The geometry comes two ways (study 20, way «c then b»):
- read directly where the representation is simple: an extrusion of a polygon, a rectangle or a circle, a faceted
  Brep, a face set, through mapped items: the faces as the file has them, nothing tessellated;
- tessellated by IfcOpenShell's iterator for the rest (booleans, clippings, curves), only those elements, without
  the openings, in world coordinates, one thread: the iterator's threads crash on a file opened lazily (IfcOpenShell
  0.9.0.post1, study 20, 3.4).
The file is opened lazily (`lazy`): one quick pass indexes it and an entity is parsed only when read, so a model of
50 MB of which the roofs are 1 % costs a third of a full open.

Everything comes out as plain data (JSON), in metres, in the model's world frame (x, y as the model has them, z up):
ifc_import.py turns it into Meridiana's frame with the georeferencing read here. Pitches are planes with their plan
outline; an obstacle is a plan outline with a bottom and a top."""

from __future__ import annotations

import math
import re
import time
from collections.abc import Callable

import numpy as np

# the classes of the roof surfaces, and those that may be parts of an IfcRoof
ROOF_PARTS = ("IfcSlab", "IfcPlate", "IfcCovering", "IfcBuildingElementPart", "IfcBuildingElementProxy", "IfcRoof")
# what may stand on a roof: tested by the height of its placement first
OBSTACLE_CLASSES = ("IfcChimney", "IfcBuildingElementProxy", "IfcDistributionElement", "IfcRailing", "IfcWall",
                    "IfcWindow", "IfcGeographicElement", "IfcSolarDevice", "IfcFurnishingElement", "IfcColumn",
                    "IfcStair", "IfcMember")
UP = math.cos(math.radians(80.0))         # a face whose normal is steeper than this looks up
PLANE_ANGLE = math.radians(1.0)           # faces within 1 degree and 5 cm are one plane
PLANE_OFFSET = 0.05
MIN_PITCH_AREA = 1.0                      # m2 in plan: less is no place for a module
MIN_PITCH_WIDTH = 0.5                     # m: a strip narrower than this is the edge of a slab
SIMPLIFY = 0.02                           # m
OBSTACLE_MIN_HEIGHT = 0.10                # m above the roof
OBSTACLE_MIN_AREA = 0.01                  # m2 in plan
# a slab left under the open sky on a building that has roofs elsewhere (a stair tower's top, a terrace: a designer calls
# them roofs, the model calls them floors): high enough, large enough, and standing on walls (a balcony does not)
TERRACE_MIN_HEIGHT = 2.0                  # m above the ground
TERRACE_MIN_AREA = 8.0                    # m2
TERRACE_MAX_TILT = 30.0                   # degrees
TERRACE_WALLS = 0.35                      # the share of its outline with a wall under it
MAX_ROOF_FACES = 20000                    # faces looking up, the largest, that one roof's planes are looked for in
TESSELLATE_LOT = 150                      # elements at a time through IfcOpenShell's iterator
WALLS_TIME = 15.0                         # s: looking at every wall of a very large model is given up after this
LATE_TIME = 15.0                          # s: the same for what is placed below the roofs
LATE_CLASSES = ("IfcChimney", "IfcBuildingElementProxy", "IfcWall", "IfcColumn")     # what rises from far below a roof
# "simple": way c alone, without the iterator: what the window asks again when IfcOpenShell's iterator crashed or got
# stuck on a file (ui/ifc_import.py), the shapes it would have made left out and counted
MODES = ("all", "filtered", "direct", "boxes", "simple")


def _polygon(ring):
    """A plan polygon that shapely can work with: rounding can make a ring cross itself by a hair, and a model in map
    coordinates (millions of metres) is where it happens; the largest piece of what it means when it does."""
    from shapely.geometry import Polygon
    p = Polygon(ring)
    if p.is_valid:
        return p
    fixed = p.buffer(0)
    if fixed.geom_type == "Polygon" or fixed.is_empty:
        return fixed
    return max(fixed.geoms, key=lambda g: g.area)


class IfcError(ValueError):
    """A file that cannot be read as IFC: said in words."""


def available() -> str:
    """The version of IfcOpenShell, or "" when it is not installed (the import and the export need it)."""
    try:
        import ifcopenshell
    except ImportError:
        return ""
    return str(getattr(ifcopenshell, "version", "?"))


# the file

_UNZIPPED: list = []                # the folders of the .ifczip read in this process: gone when it ends


def _unzipped(path) -> str:
    """The .ifc inside a .ifczip, extracted to a folder of this process: IfcOpenShell opens a zip without `lazy`
    (study 20, 3.2), and a lazy model reads its file until the end, so the file stays until the process ends."""
    import atexit
    import shutil
    import tempfile
    import zipfile
    from pathlib import Path
    try:
        with zipfile.ZipFile(path) as zf:
            name = next((n for n in zf.namelist() if Path(n).suffix.lower() == ".ifc"), None)
            if name is None:
                raise IfcError("no .ifc file inside the .ifczip")
            folder = tempfile.mkdtemp(prefix="meridiana-ifc-")
            if not _UNZIPPED:
                atexit.register(lambda: [shutil.rmtree(d, ignore_errors=True) for d in _UNZIPPED])
            _UNZIPPED.append(folder)
            return zf.extract(name, folder)
    except (zipfile.BadZipFile, OSError) as error:
        raise IfcError(f"not a readable .ifczip: {error}") from None


def open_model(path, lazy: bool = True):
    """The model of a .ifc or .ifczip file; IfcError with the reason when it is not one."""
    import ifcopenshell
    if str(path).lower().endswith(".ifczip"):
        path = _unzipped(path)
    try:
        return ifcopenshell.open(str(path), lazy=lazy)
    except FileNotFoundError as error:
        raise IfcError(str(error)) from None
    except (RuntimeError, OSError, LookupError, ifcopenshell.Error) as error:
        raise IfcError(f"not a readable IFC file: {error}") from None


def _by_type(f, name: str) -> list:
    """The entities of a class and its subclasses; none when the schema does not have the class (IfcChimney is not
    in IFC2X3)."""
    try:
        return list(f.by_type(name))
    except RuntimeError:
        return []


def unit_scale(f) -> float:
    import ifcopenshell.util.unit
    try:
        return float(ifcopenshell.util.unit.calculate_unit_scale(f))
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return 1.0


def _dms(value) -> float | None:
    """An IfcCompoundPlaneAngleMeasure (degrees, minutes, seconds[, millionths]) as decimal degrees."""
    if not value:
        return None
    parts = [float(v) for v in value] + [0.0] * (4 - len(value))
    return parts[0] + parts[1] / 60.0 + parts[2] / 3600.0 + parts[3] / 3.6e9


def _map_conversion(f, scale: float) -> dict | None:
    """The map conversion: IfcMapConversion (IFC4), else the property sets ePSet_MapConversion and ePSet_ProjectedCRS
    on the project (the buildingSMART guide for IFC2X3). Eastings, northings and height in the map's unit as written
    (metres in practice), the X axis of the model in the map, the scale (model units to map units) and the CRS."""
    for m in _by_type(f, "IfcMapConversion"):
        crs = m.TargetCRS
        # the map's unit: its own (IfcProjectedCRS.MapUnit), else the project's (IFC4, 8.18.3.6): Revit 2020 writes
        # the eastings in millimetres without one
        map_unit = scale
        if getattr(crs, "MapUnit", None) is not None:
            import ifcopenshell.util.unit
            try:
                map_unit = float(ifcopenshell.util.unit.get_unit_scale(crs.MapUnit))
            except (AttributeError, TypeError, ValueError):
                map_unit = scale
        return {"crs": getattr(crs, "Name", None) or "", "eastings": float(m.Eastings or 0.0),
                "northings": float(m.Northings or 0.0), "height": float(m.OrthogonalHeight or 0.0),
                "x_axis": [float(m.XAxisAbscissa if m.XAxisAbscissa is not None else 1.0),
                           float(m.XAxisOrdinate if m.XAxisOrdinate is not None else 0.0)],
                "scale": float(m.Scale) if m.Scale else 1.0, "unit_m": scale, "map_unit_m": map_unit,
                "description": getattr(crs, "Description", None) or ""}
    try:
        import ifcopenshell.util.element
        project = f.by_type("IfcProject")[0]
        psets = ifcopenshell.util.element.get_psets(project)
    except (IndexError, RuntimeError, AttributeError):
        return None
    conv = psets.get("ePSet_MapConversion")
    if not conv:
        return None
    crs = psets.get("ePSet_ProjectedCRS") or {}
    return {"crs": str(crs.get("Name") or ""), "eastings": float(conv.get("Eastings") or 0.0),
            "northings": float(conv.get("Northings") or 0.0), "height": float(conv.get("OrthogonalHeight") or 0.0),
            "x_axis": [float(conv.get("XAxisAbscissa", 1.0) or 1.0), float(conv.get("XAxisOrdinate", 0.0) or 0.0)],
            "scale": float(conv.get("Scale") or 1.0), "unit_m": scale, "map_unit_m": 1.0,
            "description": str(crs.get("Description") or "")}


def georeference(f, scale: float) -> dict:
    """Site, true north, map conversion. The true north is the angle of the north from the model's +Y, counter-clockwise
    positive (the convention of ifcopenshell.api.georeference.edit_true_north and of FreeCAD's Declination)."""
    out: dict = {"site": None, "true_north": 0.0, "map": _map_conversion(f, scale), "sites": 0}
    sites = _by_type(f, "IfcSite")
    out["sites"] = len(sites)
    for s in sites:
        lat, lon = _dms(s.RefLatitude), _dms(s.RefLongitude)
        if lat is None or lon is None:
            continue
        out["site"] = {"lat": lat, "lon": lon, "elevation": float(s.RefElevation or 0.0) * scale,
                       "name": s.Name or "", "placement": _placement(s.ObjectPlacement, {}, scale)[:3, 3].tolist()}
        break
    for ctx in _by_type(f, "IfcGeometricRepresentationContext"):
        if ctx.is_a("IfcGeometricRepresentationSubContext") or ctx.ContextType not in ("Model", None):
            continue
        if ctx.TrueNorth is not None:
            x, y = (list(ctx.TrueNorth.DirectionRatios) + [0.0, 0.0])[:2]
            if math.hypot(x, y) > 1e-12:
                out["true_north"] = math.degrees(math.atan2(-x, y)) + 0.0      # never -0.0
        break
    return out


# placements: 4 x 4 matrices in metres

def _coordinates(point) -> list:
    """The coordinates of an IfcCartesianPoint; the origin when it is missing (a file cut short, study 20, 4)."""
    found = getattr(point, "Coordinates", None)
    return [float(c) for c in found] if found else [0.0, 0.0, 0.0]


def _axis2(p) -> np.ndarray:
    m = np.eye(4)
    if p is None:
        return m
    if p.is_a("IfcAxis2Placement2D"):
        o = _coordinates(p.Location)[:2] + [0.0]
        x = np.array((list(p.RefDirection.DirectionRatios) + [0.0])[:3] if p.RefDirection else (1.0, 0.0, 0.0))
        z = np.array((0.0, 0.0, 1.0))
    else:
        o = _coordinates(p.Location)
        z = np.array(p.Axis.DirectionRatios if getattr(p, "Axis", None) else (0.0, 0.0, 1.0), dtype=float)
        x = np.array(p.RefDirection.DirectionRatios if getattr(p, "RefDirection", None) else (1.0, 0.0, 0.0),
                     dtype=float)
    z = z / (np.linalg.norm(z) or 1.0)
    x = x - z * float(x @ z)
    if np.linalg.norm(x) < 1e-9:
        x = np.array((1.0, 0.0, 0.0)) if abs(z[0]) < 0.9 else np.array((0.0, 1.0, 0.0))
        x = x - z * float(x @ z)
    x = x / np.linalg.norm(x)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, np.cross(z, x), z, (o + [0.0, 0.0, 0.0])[:3]
    return m


def _placement(pl, cache: dict, scale: float) -> np.ndarray:
    """The world matrix of an IfcLocalPlacement, its translation in metres; the identity for anything else (a grid
    placement: rare, and said by the geometry that follows)."""
    if pl is None:
        return np.eye(4)
    key = pl.id()
    if key in cache:
        return cache[key]
    if not pl.is_a("IfcLocalPlacement"):
        m = np.eye(4)
    else:
        try:
            rel = _axis2(pl.RelativePlacement)
        except (AttributeError, TypeError, ValueError, IndexError):
            rel = np.eye(4)                     # a placement that refers to what the file does not have
        rel[:3, 3] *= scale
        m = _placement(pl.PlacementRelTo, cache, scale) @ rel
    cache[key] = m
    return m


def _operator(op) -> np.ndarray:
    """An IfcCartesianTransformationOperator3D(nonUniform) as a matrix, in file units."""
    m = np.eye(4)
    x = np.array(op.Axis1.DirectionRatios if op.Axis1 else (1.0, 0.0, 0.0), dtype=float)
    y = np.array(op.Axis2.DirectionRatios if op.Axis2 else (0.0, 1.0, 0.0), dtype=float)
    z = np.array(op.Axis3.DirectionRatios if getattr(op, "Axis3", None) else (0.0, 0.0, 1.0), dtype=float)
    x, y, z = (v / (np.linalg.norm(v) or 1.0) for v in (x, y, z))
    s = float(op.Scale) if op.Scale is not None else 1.0
    s2 = float(getattr(op, "Scale2", None) or s)
    s3 = float(getattr(op, "Scale3", None) or s)
    m[:3, 0], m[:3, 1], m[:3, 2] = x * s, y * s2, z * s3
    m[:3, 3] = list(op.LocalOrigin.Coordinates) + [0.0] * (3 - len(op.LocalOrigin.Coordinates))
    return m


# the geometry read directly (way c)

class Unsupported(Exception):
    """A representation the direct reading does not take: the element goes to the iterator."""


CIRCLE_SEGMENTS = 16


ARC_STEP = math.radians(15.0)             # an arc read directly becomes straight pieces of this angle at most


def _arc_through(p0, p1, p2) -> list:
    """The points of the arc from p0 through p1 to p2, p0 and p2 included; straight when they are in line."""
    (ax, ay), (bx, by), (cx, cy) = p0, p1, p2
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return [p0, p2]
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    r = math.hypot(ax - ux, ay - uy)
    start = math.atan2(ay - uy, ax - ux)
    mid = (math.atan2(by - uy, bx - ux) - start) % (2 * math.pi)
    end = (math.atan2(cy - uy, cx - ux) - start) % (2 * math.pi)
    sweep = end if mid <= end else end - 2 * math.pi        # the way that passes through p1
    n = max(1, int(abs(sweep) / ARC_STEP) + 1)
    return [(ux + r * math.cos(start + sweep * k / n), uy + r * math.sin(start + sweep * k / n)) for k in range(n)] + [p2]


_ANGLE_UNIT: dict = {}                    # the file's plane angle unit in radians, by the file


def _angle_unit(entity) -> float:
    """The plane angle unit of the file an entity is in, in radians: a trimmed circle's parameters are in it (Revit's
    IFC2X3 writes degrees)."""
    f = entity.file
    key = id(f)
    if key not in _ANGLE_UNIT:
        unit = 1.0
        for u in _by_type(f, "IfcConversionBasedUnit"):
            if u.UnitType == "PLANEANGLEUNIT":
                unit = float(u.ConversionFactor.ValueComponent.wrappedValue)
        _ANGLE_UNIT[key] = unit
    return _ANGLE_UNIT[key]


def _trim_of(trims):
    """The first of a trim's selects: ("point", xy) or ("value", t); the point when it has both (IFC prefers neither,
    and the points are in length units)."""
    point = next((t for t in trims if hasattr(t, "is_a") and t.is_a("IfcCartesianPoint")), None)
    if point is not None:
        return "point", tuple(float(v) for v in point.Coordinates[:2])
    for t in trims:
        value = getattr(t, "wrappedValue", t)
        if isinstance(value, (int, float)):
            return "value", float(value)
    raise Unsupported("a trim of neither a point nor a parameter")


def _trimmed_points(c) -> list:
    """An IfcTrimmedCurve, from its first trim to its second: a line, or a circle's arc the way its sense says."""
    base = c.BasisCurve
    (kind1, t1), (kind2, t2) = _trim_of(c.Trim1 or ()), _trim_of(c.Trim2 or ())
    if base.is_a("IfcLine"):
        origin = tuple(float(v) for v in base.Pnt.Coordinates[:2])
        ratios = base.Dir.Orientation.DirectionRatios
        length = math.hypot(float(ratios[0]), float(ratios[1])) or 1.0
        dx = float(ratios[0]) / length * float(base.Dir.Magnitude)
        dy = float(ratios[1]) / length * float(base.Dir.Magnitude)

        def on_line(kind, t):
            return t if kind == "point" else (origin[0] + t * dx, origin[1] + t * dy)
        return [on_line(kind1, t1), on_line(kind2, t2)]
    if not base.is_a("IfcCircle"):
        raise Unsupported(base.is_a())
    m = _axis2(base.Position)
    r = float(base.Radius)
    unit = _angle_unit(c)

    def angle(kind, t):
        if kind == "value":
            return t * unit
        x, y = t[0] - m[0, 3], t[1] - m[1, 3]
        return math.atan2(x * m[0, 1] + y * m[1, 1], x * m[0, 0] + y * m[1, 0])
    start, stop = angle(kind1, t1), angle(kind2, t2)
    sweep = (stop - start) % (2 * math.pi) if c.SenseAgreement else -((start - stop) % (2 * math.pi))
    n = max(1, int(abs(sweep) / ARC_STEP) + 1)
    out = []
    for k in range(n + 1):
        u = start + sweep * k / n
        lx, ly = r * math.cos(u), r * math.sin(u)
        out.append((m[0, 3] + lx * m[0, 0] + ly * m[0, 1], m[1, 3] + lx * m[1, 0] + ly * m[1, 1]))
    return out


def _segment_points(c) -> list:
    """The points of a curve not closed by itself, straight or a circle's arc; Unsupported for anything else."""
    if c.is_a("IfcPolyline"):
        return [tuple(p.Coordinates[:2]) for p in c.Points]
    if c.is_a("IfcTrimmedCurve"):
        return _trimmed_points(c)
    if c.is_a("IfcCompositeCurve"):
        pts: list = []
        for seg in c.Segments:
            part = _segment_points(seg.ParentCurve)
            if not seg.SameSense:
                part = part[::-1]
            pts += part[1:] if pts and math.dist(pts[-1], part[0]) < 1e-6 else part
        return pts
    if c.is_a("IfcIndexedPolyCurve"):
        coords = [tuple(p[:2]) for p in c.Points.CoordList]
        if not c.Segments:
            return coords
        pts = []
        for seg in c.Segments:
            idx = [int(i) for i in seg.wrappedValue]
            if seg.is_a("IfcArcIndex"):
                part = _arc_through(coords[idx[0] - 1], coords[idx[1] - 1], coords[idx[2] - 1])
            else:
                part = [coords[i - 1] for i in idx]
            pts += part[1:] if pts and math.dist(pts[-1], part[0]) < 1e-9 else part
        return pts
    raise Unsupported(c.is_a())


def _curve_points(c) -> list:
    """The points of a closed 2D curve, its arcs as short straight pieces; Unsupported for splines and the like."""
    pts = _segment_points(c)
    if len(pts) > 1 and math.dist(pts[0], pts[-1]) < 1e-9:
        pts = pts[:-1]
    if len(pts) < 3:
        raise Unsupported("a curve of fewer than three points")
    return pts


def _profile(p) -> list:
    """The outer outline of a profile as 2D points in its own frame (its Position applied); the holes are left out."""
    if p.is_a("IfcArbitraryClosedProfileDef"):
        pts = _curve_points(p.OuterCurve)
        pos = None
    elif p.is_a("IfcRectangleProfileDef"):
        a, b = float(p.XDim) / 2, float(p.YDim) / 2
        pts = [(-a, -b), (a, -b), (a, b), (-a, b)]
        pos = p.Position
    elif p.is_a("IfcCircleProfileDef"):
        r = float(p.Radius)
        pts = [(r * math.cos(2 * math.pi * k / CIRCLE_SEGMENTS), r * math.sin(2 * math.pi * k / CIRCLE_SEGMENTS))
               for k in range(CIRCLE_SEGMENTS)]
        pos = p.Position
    else:
        raise Unsupported(p.is_a())
    if pos is not None:
        m = _axis2(pos)
        pts = [tuple((m @ np.array((x, y, 0.0, 1.0)))[:2]) for x, y in pts]
    return pts


def _extrusion(item) -> list:
    """The faces of an IfcExtrudedAreaSolid in the item's frame (file units): the two caps and the sides."""
    pts = _profile(item.SweptArea)
    base = np.array([(x, y, 0.0) for x, y in pts], dtype=float)
    d = np.array(item.ExtrudedDirection.DirectionRatios, dtype=float)
    d = d / (np.linalg.norm(d) or 1.0) * float(item.Depth)
    top = base + d
    # the caps facing out: the base against the extrusion, the end along it (a profile drawn clockwise turns both)
    area = 0.5 * float(np.sum(base[:, 0] * np.roll(base[:, 1], -1) - np.roll(base[:, 0], -1) * base[:, 1]))
    along = area * d[2] > 0
    faces = [base[::-1] if along else base, top if along else top[::-1]]
    n = len(base)
    faces += [np.array([base[i], base[(i + 1) % n], top[(i + 1) % n], top[i]]) for i in range(n)]
    m = _axis2(item.Position) if item.Position is not None else np.eye(4)
    return [f @ m[:3, :3].T + m[:3, 3] for f in faces]


def _loops(faces) -> list:
    out = []
    for face in faces:
        bound = next((b for b in face.Bounds if b.is_a("IfcFaceOuterBound")), None) or (face.Bounds or [None])[0]
        loop = bound.Bound if bound is not None else None
        if loop is None or not loop.is_a("IfcPolyLoop"):
            raise Unsupported("a face that is not a polygon")
        pts = np.array([p.Coordinates for p in loop.Polygon], dtype=float)
        if not bound.Orientation:
            pts = pts[::-1]
        out.append(pts)
    return out


def _upwards(face: np.ndarray) -> np.ndarray:
    """A face of a surface (no inside, so no outside either) turned to look up: a roof drawn as a sheet is a roof
    whichever way its faces were written."""
    n, _a = _normal(np.asarray(face, dtype=float))
    return face[::-1] if n[2] < 0 else face


def _item_faces(item, depth: int = 0) -> list:
    """The faces of a representation item in its own frame (file units); Unsupported when it is not simple."""
    kind = item.is_a()
    if kind == "IfcExtrudedAreaSolid":
        return _extrusion(item)
    if kind in ("IfcFacetedBrep", "IfcFacetedBrepWithVoids"):
        return _loops(item.Outer.CfsFaces)
    if kind in ("IfcShellBasedSurfaceModel", "IfcFaceBasedSurfaceModel"):
        shells = item.SbsmBoundary if kind == "IfcShellBasedSurfaceModel" else item.FbsmFaces
        return [_upwards(f) for shell in shells for f in _loops(shell.CfsFaces)]
    if kind == "IfcTriangulatedFaceSet":
        coords = np.array(item.Coordinates.CoordList, dtype=float)
        idx = np.array(item.CoordIndex, dtype=int) - 1
        faces = list(coords[idx])
        return faces if getattr(item, "Closed", None) else [_upwards(f) for f in faces]
    if kind == "IfcPolygonalFaceSet":
        coords = np.array(item.Coordinates.CoordList, dtype=float)
        pn = item.PnIndex
        out = []
        for face in item.Faces:
            idx = [int(i) for i in face.CoordIndex]
            if pn:
                idx = [int(pn[i - 1]) for i in idx]
            out.append(coords[np.array(idx) - 1])
        return out if getattr(item, "Closed", None) else [_upwards(f) for f in out]
    if kind == "IfcMappedItem" and depth < 4:
        source = item.MappingSource
        m = _operator(item.MappingTarget) @ _axis2(source.MappingOrigin)
        out = []
        for sub in source.MappedRepresentation.Items:
            out += [f @ m[:3, :3].T + m[:3, 3] for f in _item_faces(sub, depth + 1)]
        return out
    raise Unsupported(kind)


BODY_TYPES = {"SweptSolid", "Brep", "Tessellation", "SurfaceModel", "MappedRepresentation", "AdvancedSweptSolid",
              "Clipping", "CSG", "AdvancedBrep", "BoundingBox", None}


def body(element):
    """The representation of an element's body: «Body» first, then any of a solid kind in a model context."""
    rep = getattr(element, "Representation", None)
    if rep is None:
        return None
    found = None
    for r in rep.Representations:
        ctx = r.ContextOfItems
        if ctx is not None and getattr(ctx, "ContextType", "Model") not in ("Model", None):
            continue
        if r.RepresentationIdentifier == "Body":
            return r
        if found is None and r.RepresentationType in BODY_TYPES and r.RepresentationIdentifier not in (
                "Axis", "FootPrint", "Box", "Annotation", "Profile", "Reference", "Surface"):
            found = r
    return found


def direct_faces(element, cache: dict, scale: float) -> list:
    """The faces of an element in world coordinates, in metres, read from the file; Unsupported when its body is not
    simple (the iterator does it)."""
    r = body(element)
    if r is None:
        return []
    faces = []
    for item in r.Items:
        faces += _item_faces(item)
    m = _placement(element.ObjectPlacement, cache, scale)
    rot, move = m[:3, :3], m[:3, 3]
    return [(np.asarray(f, dtype=float) * scale) @ rot.T + move for f in faces]


def _support_surfaces(f, structure, cache: dict, scale: float) -> list:
    """Read our explicitly tagged virtual planes, without treating generic annotations as roofs."""
    out = []
    for e in _by_type(f, "IfcAnnotation"):
        if e.ObjectType != "MERIDIANA_PLACEMENT_SURFACE" or e.Representation is None:
            continue
        try:
            placement = _placement(e.ObjectPlacement, cache, scale)
            for rep in e.Representation.Representations:
                for item in rep.Items:
                    if not item.is_a("IfcGeometricSet"):
                        continue
                    for surface in item.Elements:
                        if not surface.is_a("IfcCurveBoundedPlane") or surface.InnerBoundaries:
                            continue
                        xy = _curve_points(surface.OuterBoundary)
                        points = np.array([(x, y, 0.0) for x, y in xy])
                        axes = _axis2(surface.BasisSurface.Position)
                        points = (points @ axes[:3, :3].T + axes[:3, 3]) * scale
                        points = points @ placement[:3, :3].T + placement[:3, 3]
                        normal, area = _normal(points)
                        if normal[2] < 0:
                            normal = -normal
                        if area < 1e-4 or normal[2] < math.cos(math.radians(89)):
                            continue
                        bid = structure.building_of(e.id())
                        ground = structure.ground(bid)[0]
                        out.append({"ring": points[:, :2].tolist(), "normal": normal.tolist(),
                                    "point": points.mean(axis=0).tolist(), "area": area, "holes": 0,
                                    "owners": [e.id()], "ground": ground, "name": e.Name or "",
                                    "ifc": structure.buildings[bid].GlobalId if bid in structure.buildings else "",
                                    "storey": structure.storey_of(e.id())})
        except (Unsupported, AttributeError, TypeError, ValueError, IndexError):
            continue
    return out


def _first_operand(item):
    """The solid a boolean result starts from."""
    for _i in range(32):
        if not item.is_a("IfcBooleanResult"):
            return item
        item = item.FirstOperand
    raise Unsupported("booleans too deep")


def box_points(element, cache: dict, scale: float) -> np.ndarray | None:
    """Way d: the points of an element's body without making any face (the extrusions' profiles at both ends, every
    point of a Brep or a face set), in world metres; None when it has none or they cannot be found."""
    try:
        faces = direct_faces(element, cache, scale)
    except Unsupported:
        r = body(element)
        if r is None:
            return None
        m = _placement(element.ObjectPlacement, cache, scale)
        # what is cut by a clipping is inside what it cuts: its points are the extent, a little larger
        try:
            whole = [f for item in r.Items for f in _item_faces(_first_operand(item))]
            if whole:
                return (np.concatenate(whole) * scale) @ m[:3, :3].T + m[:3, 3]
        except (Unsupported, AttributeError, TypeError, ValueError, IndexError):
            pass
        pts = [np.array(p.Coordinates, dtype=float) for item in r.Items for p in element.file.traverse(item)
               if p.is_a("IfcCartesianPoint") and len(p.Coordinates) == 3]
        if not pts:
            return None
        return (np.array(pts) * scale) @ m[:3, :3].T + m[:3, 3]
    except (AttributeError, TypeError, ValueError, IndexError):
        return None
    return np.concatenate(faces) if faces else None


# the geometry tessellated by IfcOpenShell (way b)

def tessellate(f, elements: list, threads: int = 1, openings: bool = False, progress=None) -> tuple[dict, list]:
    """The triangles of `elements` in world metres ({id: array (n, 3, 3)}) and the errors. The iterator is always run
    to its end: one dropped half way crashes when it is destroyed (IfcOpenShell 0.9.0.post1 with several threads,
    study 20, 3.4)."""
    import ifcopenshell.geom
    out: dict = {}
    errors: list = []
    if not elements:
        return out, errors
    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)
    s.set("disable-opening-subtractions", not openings)
    s.set("apply-default-materials", False)
    it = ifcopenshell.geom.iterator(s, f, max(1, threads), include=elements)
    total = len(elements)
    done = 0
    if not it.initialize():
        return out, ["the iterator found nothing to make"]
    while True:
        shape = it.get()
        v = np.asarray(shape.geometry.verts, dtype=float).reshape(-1, 3)
        idx = np.asarray(shape.geometry.faces, dtype=int).reshape(-1, 3)
        if len(idx):
            out[int(shape.id)] = v[idx]
        done += 1
        if progress is not None and done % 25 == 0:
            progress(done / total)
        if not it.next():
            break
    missing = total - len(out)
    if missing > 0:
        errors.append(f"{missing} elements without a shape from the iterator")
    return out, errors


# what is in the model: buildings, storeys, who contains whom

class Structure:
    """The spatial tree read from the relations (not from the inverse attributes: they cost the whole file on a lazy
    open): the container of each element, the parts of each aggregate, the buildings and their storeys."""

    def __init__(self, f, scale: float, cache: dict):
        self.f, self.cache, self.scale = f, cache, scale
        self.parent: dict = {}          # id -> the id of the aggregate or of the container
        self.parts: dict = {}           # id -> [ids of the parts]
        for rel in _by_type(f, "IfcRelAggregates"):
            whole = rel.RelatingObject.id()
            for part in rel.RelatedObjects:
                self.parent[part.id()] = whole
                self.parts.setdefault(whole, []).append(part.id())
        for rel in _by_type(f, "IfcRelContainedInSpatialStructure"):
            holder = rel.RelatingStructure.id()
            for e in rel.RelatedElements:
                self.parent.setdefault(e.id(), holder)
        self.buildings = {b.id(): b for b in _by_type(f, "IfcBuilding")}
        # the zero of each building in world metres (its placement): the storeys are measured from there
        self.zero = {bid: float(_placement(b.ObjectPlacement, cache, scale)[2, 3]) for bid, b in self.buildings.items()}
        self._building: dict = {}       # id -> its building, as found
        self.storeys: dict = {}         # building id -> [(world z of the storey, name)]
        for s in _by_type(f, "IfcBuildingStorey"):
            b = self.building_of(s.id())
            z = float(_placement(s.ObjectPlacement, cache, scale)[2, 3])
            if s.ObjectPlacement is None and s.Elevation is not None:
                z = float(s.Elevation) * scale
            self.storeys.setdefault(b, []).append((z, s.Name or ""))

    def building_of(self, eid: int):
        """The id of the IfcBuilding an element is in, None when it is in none."""
        seen = []
        cur = eid
        out = None
        for _i in range(64):
            if cur in self._building:
                out = self._building[cur]
                break
            if cur in self.buildings:
                out = cur
                break
            seen.append(cur)
            cur = self.parent.get(cur)
            if cur is None:
                break
        for s in seen:
            self._building[s] = out
        return out

    def storey_of(self, eid: int) -> str:
        """The name of the storey an element is in (through its aggregates), "" when none."""
        cur = eid
        for _i in range(64):
            cur = self.parent.get(cur)
            if cur is None:
                return ""
            e = self.f.by_id(cur)
            if e.is_a("IfcBuildingStorey"):
                return e.Name or ""
        return ""

    def storey_level(self, eid: int) -> float | None:
        """The world height of the storey an element is in (through its aggregates), None when none."""
        cur = eid
        for _i in range(64):
            cur = self.parent.get(cur)
            if cur is None:
                return None
            e = self.f.by_id(cur)
            if e.is_a("IfcBuildingStorey"):
                return float(_placement(e.ObjectPlacement, self.cache, self.scale)[2, 3])
        return None

    def ground(self, bid) -> tuple[float, str]:
        """The height of the ground of a building in world metres and the storey it comes from: the storey at the
        building's zero or just below it (the ground floor, ±0.00), else the lowest one; the building's zero without
        storeys."""
        levels = sorted(self.storeys.get(bid) or [])
        zero = self.zero.get(bid, 0.0)
        if not levels:
            return zero, ""
        below = [lv for lv in levels if lv[0] <= zero + 0.05]
        return below[-1] if below else levels[0]


def _is_roof_part(e, structure: Structure, roofs: set) -> bool:
    kind = e.is_a()
    pre = str(getattr(e, "PredefinedType", "") or "")
    if kind == "IfcSlab" and pre == "ROOF":
        return True
    if kind == "IfcCovering" and pre == "ROOFING":
        return True
    return structure.parent.get(e.id()) in roofs


# the analysis: faces to roof planes

def _normal(poly: np.ndarray) -> tuple[np.ndarray, float]:
    """Newell's normal of a polygon (unit) and its area."""
    x, y, z = poly[:, 0], poly[:, 1], poly[:, 2]
    xn, yn, zn = np.roll(x, -1), np.roll(y, -1), np.roll(z, -1)
    n = np.array((((y - yn) * (z + zn)).sum(), ((z - zn) * (x + xn)).sum(), ((x - xn) * (y + yn)).sum())) / 2
    a = float(np.linalg.norm(n))
    return (n / a if a > 0 else n), a


def _plan(poly: np.ndarray):
    return _polygon(poly[:, :2])


def _pieces(geom) -> list:
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    return [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon" and not g.is_empty]


def roof_planes(faces: list, owners: list, deadline: float = math.inf) -> tuple[list, dict]:
    """The planes of a roof from its faces (world metres) and who owns each face: the faces looking up grouped by plane
    (1 degree, 5 cm); each plane's plan cut where another plane stands above it (the covering over the slab, the
    dormer over the pitch); what is left, wide enough and larger than MIN_PITCH_AREA, is a pitch. Returns the pitches
    ({"ring", "normal", "point", "area", "owners"}) and what was left out."""
    import shapely
    from shapely.strtree import STRtree
    left = {"small": 0, "small_area": 0.0}
    up = []
    for poly, owner in zip(faces, owners, strict=True):
        if len(poly) < 3:
            continue
        n, a = _normal(poly)
        if a < 1e-4 or n[2] < UP:
            continue
        up.append((a, n, float(n @ poly.mean(axis=0)), poly, owner))
    if not up:
        return [], left
    up.sort(key=lambda t: -t[0])
    if len(up) > MAX_ROOF_FACES:
        # a roof modelled tile by tile (seen: 276 000 faces looking up, 95 % of them under 1 dm2): the largest faces say
        # where its planes are, and the rest would take minutes for nothing
        left["fine_faces"] = len(up) - MAX_ROOF_FACES
        left["fine_area"] = float(sum(t[0] for t in up[MAX_ROOF_FACES:]))
        up = up[:MAX_ROOF_FACES]
    normals = np.zeros((0, 3))
    offsets = np.zeros(0)
    members: list = []
    cos = math.cos(PLANE_ANGLE)
    for _a, n, d, poly, owner in up:
        k = -1
        if len(normals):
            ok = np.nonzero((normals @ n > cos) & (np.abs(offsets - d) < PLANE_OFFSET))[0]
            if len(ok):
                k = int(ok[0])
        if k < 0:
            normals = np.vstack((normals, n))
            offsets = np.append(offsets, d)
            members.append([])
            k = len(members) - 1
        members[k].append((poly, owner))
    pieces = []
    for k, group in enumerate(members):
        plans = [p for p in (_plan(poly) for poly, _o in group) if not p.is_empty and p.area > 1e-8]
        if not plans:
            continue
        merged = shapely.union_all(plans).buffer(0.002).buffer(-0.002)
        who = sorted({o for _p, o in group})
        for piece in _pieces(merged):
            pieces.append({"shape": piece, "normal": normals[k], "d": float(offsets[k]), "owners": who})

    def z_at(p, x, y):
        n = p["normal"]
        return (p["d"] - n[0] * x - n[1] * y) / n[2]
    tree = STRtree([p["shape"] for p in pieces])
    cut = [p["shape"] for p in pieces]
    for i, p in enumerate(pieces):
        if time.perf_counter() > deadline:
            left["uncut"] = len(pieces) - i
            break
        for j in tree.query(p["shape"]):
            j = int(j)
            if j == i:
                continue
            over = p["shape"].intersection(pieces[j]["shape"])
            if over.is_empty or over.area < 0.01:
                continue
            q = over.representative_point()
            if z_at(pieces[j], q.x, q.y) > z_at(p, q.x, q.y) + 0.02:
                cut[i] = cut[i].difference(over.buffer(0.01))
    out = []
    for p, shape in zip(pieces, cut, strict=True):
        for piece in _pieces(shape):
            if piece.area < MIN_PITCH_AREA or piece.buffer(-MIN_PITCH_WIDTH / 2).is_empty:
                if piece.area >= 0.1:           # not the edges of the slabs: surfaces a designer would see
                    left["small"] += 1
                    left["small_area"] += float(piece.area)
                continue
            piece = piece.simplify(SIMPLIFY)
            if piece.is_empty or piece.geom_type != "Polygon":
                continue
            c = piece.representative_point()
            ring = [[round(float(x), 4), round(float(y), 4)] for x, y in list(piece.exterior.coords)[:-1]]
            out.append({"ring": ring, "normal": [float(v) for v in p["normal"]],
                        "point": [float(c.x), float(c.y), float(z_at(p, c.x, c.y))],
                        "area": float(piece.area), "holes": len(piece.interiors), "owners": p["owners"]})
    return out, left


def plane_z(pitch: dict, x: float, y: float) -> float:
    n, (px, py, pz) = pitch["normal"], pitch["point"]
    return pz - (n[0] * (x - px) + n[1] * (y - py)) / n[2]


def _components(pitches: list) -> list[list[int]]:
    """The pitches that touch in plan (within 5 cm), as groups of indices: one roof each."""
    shapes = [_polygon(p["ring"]).buffer(0.05) for p in pitches]
    seen: set = set()
    out = []
    for i in range(len(pitches)):
        if i in seen:
            continue
        group, todo = [], [i]
        seen.add(i)
        while todo:
            k = todo.pop()
            group.append(k)
            for j in range(len(pitches)):
                if j not in seen and shapes[k].intersects(shapes[j]):
                    seen.add(j)
                    todo.append(j)
        out.append(sorted(group))
    return out


def _outline(shapes) -> list | None:
    import shapely
    union = shapely.union_all([s.buffer(0.05) for s in shapes]).buffer(-0.05)
    parts = _pieces(union)
    if not parts:
        return None
    poly = max(parts, key=lambda g: g.area).simplify(SIMPLIFY)
    if poly.is_empty or poly.geom_type != "Polygon":
        return None
    return [[round(float(x), 4), round(float(y), 4)] for x, y in list(poly.exterior.coords)[:-1]]


def _footprint_of(faces: list):
    """The plan outline of some faces (walls, slabs, an obstacle) as one shapely polygon, or None."""
    import shapely
    plans = [p for p in (_plan(f) for f in faces if len(f) >= 3) if not p.is_empty and p.area > 1e-6]
    # the vertical faces of a wall have no area in plan: their edges, thickened by a millimetre, do
    plans += [shapely.LineString(f[:, :2]).buffer(0.001) for f in faces if len(f) >= 2 and _plan(f).area <= 1e-6]
    if not plans:
        return None
    return shapely.union_all(plans)


# obstacles

KIND_OF = (("IfcChimney", "chimney"), ("IfcGeographicElement", "tree"), ("IfcWindow", "skylight"),
           ("IfcRailing", "parapet"), ("IfcWall", "parapet"), ("IfcSolarDevice", "module"),
           ("IfcDistributionElement", "plant"), ("IfcBuildingElementProxy", "plant"))


# words in the names and object types of proxies and equipment, in the languages of the models met (Italian, English,
# German, Dutch, French): what Meridiana's export writes comes back as it was
KIND_WORDS = (("vent", ("evacuator", "efc", "smoke", "rauch", "rook", "fumée", "fumee", "lucernario apribile")),
              ("skylight", ("lucernar", "skylight", "rooflight", "roof light", "lichtkoepel", "lichtkuppel",
                            "dachfenster", "dakraam", "lanterneau", "velux")),
              ("chimney", ("camino", "comignolo", "chimney", "schornstein", "schoorsteen", "cheminée", "cheminee")),
              ("tree", ("albero", "tree", "baum", "boom", "arbre")),
              ("module", ("modulo fotovoltaico", "solar panel", "pv module", "photovoltaic", "päikesepaneel",
                          "solarmodul", "zonnepaneel")))


def obstacle_kind(e) -> str:
    """Meridiana's kind of an obstacle (model.EXCLUSION_KINDS, and «parapet», «module»): by its class, then for
    proxies and equipment by the words of its name and object type."""
    kind = "other"
    for cls, k in KIND_OF:
        try:
            if e.is_a(cls):
                kind = k
                break
        except RuntimeError:
            continue
    if kind in ("plant", "other"):
        text = " ".join(str(x) for x in (e.Name, getattr(e, "ObjectType", None)) if x).lower()
        for k, words in KIND_WORDS:
            if any(w in text for w in words):
                return k
    return kind


# the roofs of a building

def _roofs_of(bid, elements: list, source: str, shapes: dict, structure: Structure, mode: str, counts: dict,
              deadline: float = math.inf) -> list:
    """The roofs made by some elements of one building, one for each group of pitches that touch in plan: its name,
    its ground, its outline and its pitches. From walls (and in way d from anything) the outline and a flat top."""
    from shapely.geometry import MultiPoint
    faces, owners = [], []
    for e in elements:
        for face in shapes.get(e.id(), []):
            faces.append(face)
            owners.append(e.id())
    if not faces:
        return []
    ground, storey = structure.ground(bid)
    b = structure.buildings.get(bid)
    name = (b.Name or getattr(b, "LongName", None) or "") if b is not None else ""
    base = {"name": name, "ifc": bid, "ground": ground, "ground_storey": storey, "source": source}
    if mode == "boxes" or source == "walls":
        pts = np.concatenate(faces)
        if mode == "boxes":
            shape = MultiPoint(pts[:, :2]).minimum_rotated_rectangle
        else:
            # the walls' outline: the union of each wall's hull (a union of their faces costs seconds on a large model)
            import shapely
            by: dict = {}
            for face, owner in zip(faces, owners, strict=True):
                by.setdefault(owner, []).append(face)
            shape = shapely.union_all([_hull(np.concatenate(fs)) for fs in by.values()])
        ring = _outline([shape])
        if ring is None:
            return []
        top = float(pts[:, 2].max())
        flat = {"ring": ring, "normal": [0.0, 0.0, 1.0], "point": [ring[0][0], ring[0][1], top],
                "area": float(_polygon(ring).area), "holes": 0, "owners": sorted(set(owners))}
        return [{**base, "source": "boxes" if mode == "boxes" else source, "footprint": ring, "pitches": [flat]}]
    pitches, small = roof_planes(faces, owners, deadline)
    counts["fine_faces"] = counts.get("fine_faces", 0) + small.get("fine_faces", 0)
    counts["small_faces"] = counts.get("small_faces", 0) + small["small"]
    counts["small_area"] = round(counts.get("small_area", 0.0) + small["small_area"], 3)
    if source == "slabs":
        # the tops of the slabs above the ground floor: a slab at the ground is a floor, not a roof
        level = math.cos(math.radians(1.0))
        pitches = [p for p in pitches if p["normal"][2] > level and p["point"][2] > ground + 0.5]
    out = []
    for group in _components(pitches):
        members = [pitches[i] for i in group]
        ring = _outline([_polygon(p["ring"]) for p in members])
        if ring is not None:
            storeys = [structure.storey_of(o) for p in members for o in p["owners"]]
            storey = max(set(storeys), key=storeys.count) if storeys else ""
            out.append({**base, "footprint": ring, "pitches": members, "storey": storey})
    return out


def _adopt(orphans: list, roofless: list, f, structure: Structure, cache: dict, scale: float) -> None:
    """Roofs in no building given to the building without a roof whose walls and slabs they cover most (more than
    a third of the roof): the outline of those walls and slabs from their points alone (way d), cheap."""
    from shapely.geometry import MultiPoint
    points: dict = {}
    for cls in ("IfcWall", "IfcSlab"):
        for e in _by_type(f, cls):
            bid = structure.building_of(e.id())
            if bid not in roofless:
                continue
            pts = box_points(e, cache, scale)
            if pts is not None:
                points.setdefault(bid, []).append(pts[:, :2])
    hulls = {bid: MultiPoint(np.concatenate(pts)).convex_hull for bid, pts in points.items()}
    for b in orphans:
        roof = _polygon(b["footprint"])
        best, share = None, 0.0
        for bid, hull in hulls.items():
            s = roof.intersection(hull).area / max(roof.area, 1e-9)
            if s > share:
                best, share = bid, s
        if best is not None and share > 1 / 3:
            ground, storey = structure.ground(best)
            bb = structure.buildings[best]
            b.update(ifc=best, name=bb.Name or getattr(bb, "LongName", None) or "", ground=ground,
                     ground_storey=storey)


def _address(f) -> str:
    """What the file says of its address, as one line: IfcBuilding's, else IfcSite's (it says where the project is even
    when the coordinates do not)."""
    for cls, attribute in (("IfcBuilding", "BuildingAddress"), ("IfcSite", "SiteAddress")):
        for e in _by_type(f, cls):
            a = getattr(e, attribute, None)
            if a is None:
                continue
            parts = [*(getattr(a, "AddressLines", None) or ()), getattr(a, "PostalCode", None), getattr(a, "Town", None),
                     getattr(a, "Region", None), getattr(a, "Country", None)]
            line = ", ".join(" ".join(str(x).split()) for x in parts if x and str(x).strip())
            # coordinates some templates write into the address, with a comma for the point
            line = re.sub(r"(,\s*-?\d{1,3}\s*,\s*\d{5,})+", "", line).strip(" ,")
            if line:
                return line[:200]
    return ""


def _wall_hulls(f, structure: Structure, cache: dict, scale: float) -> list:
    """Each wall as (building, plan hull, top): from its points alone (way d). A model with very many walls is cut off
    after WALLS_TIME: what comes from it says less, it never holds the reading."""
    out = []
    start = time.perf_counter()
    for e in _by_type(f, "IfcWall"):
        if time.perf_counter() - start > WALLS_TIME:
            break
        if body(e) is None:
            continue
        pts = box_points(e, cache, scale)
        if pts is not None and len(pts):
            out.append((structure.building_of(e.id()), _hull(pts), float(pts[:, 2].max()), float(pts[:, 2].min())))
    return out


def _bases(buildings: list, hulls: list, structure: Structure) -> None:
    """Where each pitch's body stands, written on the pitch as "base" (world metres) with "base_from": the foot of the
    walls that rise along its outline up to it, followed down through the walls under them (a wall per storey); without
    walls, the level of its storey. A tower on a roof, a strip over a hall, a canopy on a first floor stand above the
    ground: the model does not have a base height yet (R352), so what is read is kept here for when it does."""
    from shapely.strtree import STRtree
    tree = STRtree([h[1] for h in hulls]) if hulls else None
    for b in buildings:
        for p in b["pitches"]:
            base, source = None, ""
            if tree is not None:
                try:
                    ring = _polygon(p["ring"]).exterior.buffer(0.3)
                    near = [hulls[int(i)] for i in tree.query(ring, predicate="intersects")]
                except _STEP_ERRORS:
                    near = []
                near = [h for h in near if h[0] == b["ifc"]]
                top = min(plane_z(p, x, y) for x, y in p["ring"])
                reach = [h for h in near if h[2] >= top - 1.5]
                if reach:
                    base, source = min(h[3] for h in reach), "walls"
                    for _i in range(12):
                        lower = [h[3] for h in near if h[2] >= base - 0.5 and h[3] < base - 0.01]
                        if not lower:
                            break
                        base = min(lower)
            if base is None:
                levels = [z for z in (structure.storey_level(o) for o in p["owners"]) if z is not None]
                if levels:
                    base, source = min(levels), "storey"
            p["base"] = base
            p["base_from"] = source


def _walls_outside(hulls: list, buildings: list, structure: Structure) -> int:
    """The walls standing clearly outside every roof found, tall enough to be a part of the building that came without
    a roof (said to the designer: the model may have more than the import shows)."""
    import shapely
    shapes = [_polygon(b["footprint"]).buffer(0.5) for b in buildings if len(b.get("footprint") or []) >= 3]
    if not shapes or not hulls:
        return 0
    union = shapely.union_all(shapes)
    count = 0
    for bid, hull, top, _foot in hulls:
        if top >= structure.ground(bid)[0] + 2.5 and hull.area > 0.05 and not union.contains(hull.representative_point()):
            count += 1
    return count


def _terraces(bid, buildings: list, f, structure: Structure, cache: dict, scale: float, geometry, shapes: dict,
              seen: set, hulls: list, counts: dict) -> list:
    """The slabs of a building with roofs that are left under the open sky: what the model calls a floor and the
    designer sees as a roof (a stair tower's top, a terrace over a lower wing). Faces are read only for the slabs that
    reach outside the roofs; each piece must stand on walls, or it is a balcony."""
    import shapely
    ground = structure.ground(bid)[0]
    own = [_polygon(p["ring"]) for b in buildings if b["ifc"] == bid for p in b["pitches"]]
    if not own:
        return []
    covered = shapely.union_all([s.buffer(0.1) for s in own])
    todo = []
    for e in _by_type(f, "IfcSlab"):
        if e.id() in seen or structure.building_of(e.id()) != bid or body(e) is None:
            continue
        if str(getattr(e, "PredefinedType", "") or "") in ("LANDING", "BASESLAB"):
            continue
        pts = box_points(e, cache, scale)
        if pts is None or not len(pts) or float(pts[:, 2].max()) < ground + TERRACE_MIN_HEIGHT:
            continue
        if _hull(pts).difference(covered).area >= 1.0:
            todo.append(e)
    if not todo:
        return []
    geometry(todo, (0.55, 0.60))
    faces, owners = [], []
    for e in todo:
        for face in shapes.get(e.id(), []):
            faces.append(face)
            owners.append(e.id())
    if not faces:
        return []
    planes, _left = roof_planes(faces, owners)
    walls = [h for b, h, _top, _foot in hulls if b == bid]
    support = shapely.union_all([h.buffer(0.3) for h in walls]) if walls else None
    level = math.cos(math.radians(TERRACE_MAX_TILT))
    kept = []
    for plane in planes:
        if plane["normal"][2] < level:
            continue
        for piece in _pieces(_polygon(plane["ring"]).difference(covered)):
            centre = piece.representative_point()
            if piece.area < TERRACE_MIN_AREA or piece.buffer(-MIN_PITCH_WIDTH / 2).is_empty \
                    or plane_z(plane, centre.x, centre.y) < ground + TERRACE_MIN_HEIGHT:
                continue
            border = piece.exterior
            share = border.intersection(support).length / max(border.length, 1e-9) if support is not None else 0.0
            if share < TERRACE_WALLS:
                counts["balconies"] = counts.get("balconies", 0) + 1
                continue
            piece = piece.simplify(SIMPLIFY)
            if piece.is_empty or piece.geom_type != "Polygon":
                continue
            ring = [[round(float(x), 4), round(float(y), 4)] for x, y in list(piece.exterior.coords)[:-1]]
            kept.append({"ring": ring, "normal": plane["normal"], "area": float(piece.area), "holes": len(piece.interiors),
                         "point": [float(centre.x), float(centre.y), plane_z(plane, centre.x, centre.y)],
                         "owners": plane["owners"]})
    if not kept:
        return []
    ground, storey = structure.ground(bid)
    b = structure.buildings.get(bid)
    name = (b.Name or getattr(b, "LongName", None) or "") if b is not None else ""
    out = []
    for group in _components(kept):
        members = [kept[i] for i in group]
        ring = _outline([_polygon(p["ring"]) for p in members])
        if ring is not None:
            out.append({"name": name, "ifc": bid, "ground": ground, "ground_storey": storey, "source": "terrace",
                        "footprint": ring, "pitches": members,
                        "storey": structure.storey_of(members[0]["owners"][0])})
    counts["terrace_elements"] = counts.get("terrace_elements", 0) + len(todo)
    return out


def _rise(pts: np.ndarray, pitches: list) -> float | None:
    """How far some points rise above the roof under each of them (`pitches`: (plan shape, pitch)), the highest; None
    when no point has a roof under it. A beam or a wall top under a sloping roof stays under it from end to end, though
    its high end stands above the roof at its middle."""
    import shapely
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
    roof = np.full(len(pts), -np.inf)
    for shape, p in pitches:
        inside = shapely.contains_xy(shape, x, y)
        if inside.any():
            n, (px, py, pz) = p["normal"], p["point"]
            here = pz - (n[0] * (x - px) + n[1] * (y - py)) / n[2]
            roof[inside] = np.maximum(roof[inside], here[inside])
    under = roof > -np.inf
    return float((z[under] - roof[under]).max()) if under.any() else None


# reading

def _step_errors() -> tuple:
    from shapely.errors import GEOSException
    return (GEOSException, ValueError, TypeError, AttributeError, IndexError, RuntimeError)


_STEP_ERRORS = _step_errors()


def read(path, mode: str = "direct", lazy: bool = True, threads: int = 1,
         progress: Callable[[float, str], None] | None = None, budget_s: float | None = None) -> dict:
    """What `path` holds for a photovoltaic design, as plain data (the module's docstring). `mode` is the way of study
    20: "direct" (the program's: read the simple shapes, tessellate the rest), "filtered" (tessellate only what is
    needed), "all" (tessellate everything, the baseline), "boxes" (the points only, no faces), "simple" (the simple
    shapes only, never the iterator: the second try after a crash). `budget_s`: past this many seconds the shapes still
    to make are left out and counted, so that a model too rich in details still gives its roofs. IfcError for a file that
    is not IFC."""
    if mode not in MODES:
        raise ValueError(f"mode: {mode!r}")
    tell = progress or (lambda _f, _w: None)
    times: dict = {}
    t0 = time.perf_counter()
    deadline = t0 + budget_s if budget_s else math.inf
    tell(0.0, "open")
    f = open_model(path, lazy=lazy and mode != "all")
    times["open"] = time.perf_counter() - t0
    scale = unit_scale(f)
    cache: dict = {}
    out: dict = {"schema": f.schema, "unit_m": scale, "mode": mode, "lazy": lazy and mode != "all", "threads": threads,
                 "application": "", "buildings": [], "obstacles": [], "notes": [], "counts": {}}
    apps = _by_type(f, "IfcApplication")
    if apps:
        a = apps[0]
        out["application"] = " ".join(str(x) for x in (a.ApplicationFullName, a.Version) if x)
    out.update(georeference(f, scale))
    out["address"] = _address(f)
    tell(0.05, "structure")
    structure = Structure(f, scale, cache)
    out["storeys"] = {structure.buildings[b].GlobalId: len(v) for b, v in structure.storeys.items()
                      if b in structure.buildings}
    out["supports"] = _support_surfaces(f, structure, cache, scale)
    times["structure"] = time.perf_counter() - t0 - times["open"]
    products = None
    if mode == "all":
        products = [e for e in _by_type(f, "IfcProduct") if getattr(e, "Representation", None) is not None
                    and not e.is_a("IfcOpeningElement") and not e.is_a("IfcSpace")]
    roofs = {r.id() for r in _by_type(f, "IfcRoof")}
    candidates: dict = {}           # building -> [elements of the roof]
    for r in _by_type(f, "IfcRoof"):
        parts = [f.by_id(i) for i in structure.parts.get(r.id(), [])]
        parts = [p for p in parts if body(p) is not None and any(p.is_a(c) for c in ROOF_PARTS)]
        use = parts or ([r] if body(r) is not None else [])
        for e in use:
            candidates.setdefault(structure.building_of(e.id()), []).append(e)
    seen = {e.id() for es in candidates.values() for e in es}
    for cls in ("IfcSlab", "IfcCovering"):
        for e in _by_type(f, cls):
            if e.id() not in seen and _is_roof_part(e, structure, roofs) and body(e) is not None:
                candidates.setdefault(structure.building_of(e.id()), []).append(e)
                seen.add(e.id())
    out["counts"]["roof_elements"] = sum(len(v) for v in candidates.values())
    tell(0.10, "roofs")

    shapes: dict = {}               # id -> list of faces (world metres)
    direct_ids: set = set()
    errors: list = []

    def geometry(elements: list, fraction: tuple[float, float]) -> None:
        todo = [e for e in elements if e.id() not in shapes]
        if mode == "boxes":
            for e in todo:
                pts = box_points(e, cache, scale)
                if pts is not None:
                    shapes[e.id()] = [pts]
            return
        rest = todo
        if mode in ("direct", "simple"):
            rest = []
            for k, e in enumerate(todo):
                if k % 64 == 0 and time.perf_counter() > deadline:
                    left = len(todo) - k
                    out["counts"]["over_budget"] = out["counts"].get("over_budget", 0) + left
                    break
                try:
                    shapes[e.id()] = direct_faces(e, cache, scale)
                    direct_ids.add(e.id())
                except Unsupported:
                    rest.append(e)
                except (AttributeError, TypeError, ValueError, IndexError, RuntimeError) as error:
                    errors.append(f"{e.is_a()} #{e.id()}: {error}")
                    rest.append(e)
        if rest and mode == "simple":
            out["counts"]["skipped"] = out["counts"].get("skipped", 0) + len(rest)
            return
        if rest and mode != "all":
            lo, hi = fraction
            # by small lots: the iterator cannot be stopped half way, and one element can take a minute
            for at in range(0, len(rest), TESSELLATE_LOT):
                if time.perf_counter() > deadline:
                    out["counts"]["over_budget"] = out["counts"].get("over_budget", 0) + len(rest) - at
                    break
                lot = rest[at:at + TESSELLATE_LOT]
                share = (at / len(rest), (at + len(lot)) / len(rest))
                tris, errs = tessellate(f, lot, threads, progress=lambda x, s=share: tell(
                    lo + (hi - lo) * (s[0] + (s[1] - s[0]) * x), "tessellate"))
                errors.extend(errs)
                for eid, tri in tris.items():
                    shapes[eid] = list(tri)

    if mode == "all":
        t = time.perf_counter()
        tris, errs = tessellate(f, products, threads, openings=True,
                                progress=lambda x: tell(0.10 + 0.6 * x, "tessellate"))
        errors.extend(errs)
        for eid, tri in tris.items():
            shapes[eid] = list(tri)
        times["tessellate_all"] = time.perf_counter() - t
        out["counts"]["tessellated"] = len(tris)
        out["counts"]["triangles"] = int(sum(len(v) for v in tris.values()))
    t = time.perf_counter()
    geometry([e for es in candidates.values() for e in es], (0.10, 0.45))
    times["roofs"] = time.perf_counter() - t

    tell(0.45, "planes")
    t = time.perf_counter()
    buildings: list = []
    for bid, elements in candidates.items():
        buildings += _roofs_of(bid, elements, "roof", shapes, structure, mode, out["counts"], deadline)
    # a roof in no building (hung on the site, as in buildingSMART's sample) goes to the building without a roof
    # whose walls and slabs it covers most
    # (and a building whose «roofs» gave no pitch, only strips and slats, is one without a roof)
    roofless = [bid for bid in structure.buildings if not any(b["ifc"] == bid for b in buildings)]
    orphans = [b for b in buildings if b["ifc"] is None]
    if roofless and orphans:
        _adopt(orphans, roofless, f, structure, cache, scale)
        roofless = [bid for bid in roofless if not any(b["ifc"] == bid for b in orphans)]
    # a building without a roof: the tops of its slabs above the ground, else its walls
    for bid in roofless + ([None] if not structure.buildings and not buildings else []):
        slabs = [e for e in _by_type(f, "IfcSlab") if structure.building_of(e.id()) == bid and body(e) is not None
                 and str(getattr(e, "PredefinedType", "") or "") != "LANDING"]
        found: list = []
        if slabs:
            geometry(slabs, (0.45, 0.55))
            found = _roofs_of(bid, slabs, "slabs", shapes, structure, mode, out["counts"], deadline)
            out["counts"]["slab_elements"] = out["counts"].get("slab_elements", 0) + len(slabs)
        if not found:
            walls = [e for e in _by_type(f, "IfcWall") if structure.building_of(e.id()) == bid and body(e) is not None]
            if walls:
                geometry(walls, (0.45, 0.55))
                found = _roofs_of(bid, walls, "walls", shapes, structure, mode, out["counts"], deadline)
                out["counts"]["wall_elements"] = out["counts"].get("wall_elements", 0) + len(walls)
        buildings += found
    if mode not in ("boxes", "all"):
        tell(0.55, "terraces")
        try:
            hulls = _wall_hulls(f, structure, cache, scale)
            for bid in list(candidates):
                if bid in structure.buildings:
                    buildings += _terraces(bid, buildings, f, structure, cache, scale, geometry, shapes, seen, hulls,
                                           out["counts"])
            out["counts"]["walls_outside"] = _walls_outside(hulls, buildings, structure)
            _bases(buildings, hulls, structure)
        except _STEP_ERRORS as error:       # what is looked at beyond the roofs never costs the roofs
            errors.append(f"terraces: {type(error).__name__}: {error}")
    times["planes"] = time.perf_counter() - t
    out["counts"]["no_shape"] = sum(1 for es in candidates.values() for e in es if not shapes.get(e.id()))
    for b in buildings:
        b["ifc"] = structure.buildings[b["ifc"]].GlobalId if b["ifc"] in structure.buildings else ""

    tell(0.65, "obstacles")
    t = time.perf_counter()
    try:
        out["obstacles"], left = _obstacles(f, structure, buildings, shapes, cache, scale, mode, geometry, products)
        out["counts"].update(left)
    except _STEP_ERRORS as error:
        errors.append(f"obstacles: {type(error).__name__}: {error}")
        out["counts"]["obstacles_failed"] = 1
    times["obstacles"] = time.perf_counter() - t
    out["buildings"] = buildings
    out["counts"]["direct"] = len(direct_ids)
    out["counts"]["shapes"] = len(shapes)
    out["counts"]["errors"] = len(errors)
    out["errors"] = errors[:20]
    if not buildings and not out["supports"]:
        out["counts"]["contents"] = {"structure": sum(len(_by_type(f, c)) for c in ("IfcBeam", "IfcColumn", "IfcMember", "IfcPlate")),
                                     "plant": len(_by_type(f, "IfcDistributionElement")) + len(_by_type(f, "IfcBuildingElementProxy"))}
    out["counts"]["products"] = len(products) if products is not None else None
    times["total"] = time.perf_counter() - t0
    out["times"] = {k: round(v, 4) for k, v in times.items()}
    tell(1.0, "done")
    return out


def _hull(pts: np.ndarray):
    """The plan outline of some points: their convex hull, thickened to a polygon when they lie on a line."""
    from shapely.geometry import MultiPoint
    hull = MultiPoint(pts[:, :2]).convex_hull
    if hull.geom_type != "Polygon" or hull.area < OBSTACLE_MIN_AREA:
        hull = hull.buffer(0.05)
    return hull


def _ring_of(poly) -> list:
    return [[round(float(x), 4), round(float(y), 4)] for x, y in list(poly.simplify(SIMPLIFY).exterior.coords)[:-1]]


def _obstacles(f, structure, buildings, shapes, cache, scale, mode, geometry, products) -> tuple[list, dict]:
    """What stands on the roofs. The candidates (OBSTACLE_CLASSES) whose placement is above the lowest eave less a
    metre and within the roofs' extent, read (way c, else b); kept when the middle of their points falls on a roof and
    their top rises above it by OBSTACLE_MIN_HEIGHT (a skylight when it reaches the roof's surface); their plan the
    convex hull of their points (no union of faces: the window's thousands of walls cost seconds that way). Those of
    one kind that touch on one roof are one (the 175 panels of a row are one plant). Trees anywhere. Solar modules
    already in the model are counted and left out."""
    import shapely
    left = {"modules": 0, "off_roof": 0, "obstacle_candidates": 0, "under_roof": 0}
    roofs = []
    for k, b in enumerate(buildings):
        for p in b["pitches"]:
            roofs.append((k, _polygon(p["ring"]), p))
    if roofs:
        floor = min(plane_z(p, *p["point"][:2]) for _k, _s, p in roofs) - 1.0
        x0, y0, x1, y1 = shapely.union_all([s for _k, s, _p in roofs]).buffer(2.0).bounds
    roof_ids = {o for b in buildings for p in b["pitches"] for o in p["owners"]}
    grown = [(poly.buffer(0.1), p) for _k, poly, p in roofs]
    picked = []
    late = []                       # placed below the roofs or away from them: their points say whether they reach them
    seen: set = set()
    for cls in OBSTACLE_CLASSES:
        for e in _by_type(f, cls):
            if e.id() in seen or e.id() in roof_ids or body(e) is None:
                continue
            seen.add(e.id())
            if e.is_a("IfcSolarDevice"):
                left["modules"] += 1
                continue
            if e.is_a("IfcGeographicElement"):
                picked.append(e)
                continue
            if not roofs:
                continue
            x, y, z = _placement(e.ObjectPlacement, cache, scale)[:3, 3]
            if z >= floor and x0 <= x <= x1 and y0 <= y <= y1:
                picked.append(e)
            elif cls in LATE_CLASSES:
                late.append(e)
    # a chimney or a stair tower's wall rising from the ground has its placement down there, and a model may place its
    # elements at the storey's origin: what reaches above the lowest roof, within its extent, is looked at too
    start = time.perf_counter()
    for e in late:
        if time.perf_counter() - start > LATE_TIME:
            left["late_skipped"] = left.get("late_skipped", 0) + 1
            continue
        pts = box_points(e, cache, scale)
        if pts is None or not len(pts) or float(pts[:, 2].max()) < floor:
            continue
        rise = _rise(pts, grown)            # most of them stay under the roofs: nothing to tessellate
        if rise is not None and rise >= OBSTACLE_MIN_HEIGHT:
            picked.append(e)
    left["obstacle_candidates"] = len(picked)
    if mode != "all":
        geometry(picked, (0.65, 0.95))
    found = []                      # (building, kind, hull, z0, z1, element)
    for e in picked:
        faces = shapes.get(e.id())
        if not faces:
            continue
        pts = np.concatenate(faces)
        z0, z1 = float(pts[:, 2].min()), float(pts[:, 2].max())
        cx, cy = (pts[:, 0].min() + pts[:, 0].max()) / 2, (pts[:, 1].min() + pts[:, 1].max()) / 2
        kind = obstacle_kind(e)
        if kind == "module":
            left["modules"] += 1
            continue
        on = [(k, p) for k, poly, p in roofs if shapely.contains_xy(poly.buffer(0.1), cx, cy)]
        if not on:
            if kind == "tree":
                found.append((None, "tree", _hull(pts), z0, z1, e))
            else:
                left["off_roof"] += 1
            continue
        k, pitch = max(on, key=lambda kp: plane_z(kp[1], cx, cy))
        base = plane_z(pitch, cx, cy)
        rise = _rise(pts, grown)
        if rise is None:
            rise = z1 - base
        if kind == "skylight":
            if rise < -0.05:
                left["off_roof"] += 1           # a window of a wall under the roof's edge
                continue
        elif rise < OBSTACLE_MIN_HEIGHT:
            left["under_roof"] += 1
            continue
        if z0 < base - 3.0 and kind != "parapet":
            kind = "other"                      # a shaft or a tower from the floors below
        found.append((k, kind, _hull(pts), max(z0, base) if kind != "tree" else z0, z1, e))
    # one kind on one roof, touching: one obstacle
    out = []
    groups: dict = {}
    for item in found:
        groups.setdefault((item[0], item[1]), []).append(item)
    for (k, kind), items in groups.items():
        clusters = [[it] for it in items]
        if kind not in ("parapet", "tree") and len(items) > 1:
            # touching (15 cm), and compact together: their hull no more than half again their own areas (a row of
            # panels, a block of machines; never the four parapets of a roof, whose hull is the roof)
            merged = _pieces(shapely.union_all([it[2].buffer(0.15) for it in items]))
            clusters = []
            for piece in merged:
                members = [it for it in items if it[2].intersects(piece)]
                hull = shapely.union_all([it[2] for it in members]).convex_hull
                if hull.area <= 1.5 * sum(it[2].area for it in members) + 0.5:
                    clusters.append(members)
                else:
                    clusters += [[it] for it in members]
        for members in clusters:
            hull = shapely.union_all([it[2] for it in members]).convex_hull
            if hull.geom_type != "Polygon":
                hull = hull.buffer(0.05)
            names = sorted({it[5].Name or "" for it in members} - {""})
            out.append({"ring": _ring_of(hull), "z0": min(it[3] for it in members), "z1": max(it[4] for it in members),
                        "kind": kind, "name": names[0] if names else "", "class": members[0][5].is_a(),
                        "elements": len(members), "building": k})
    return out, left
