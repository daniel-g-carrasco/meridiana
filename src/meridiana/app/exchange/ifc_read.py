"""Reading an IFC model for what a photovoltaic design needs, and nothing more (study 20): where the site is and
where north is, the buildings with the planes of their roofs, their heights, what stands on the roofs. Without Qt;
the window runs it in a process of its own (ifc_worker.py), which it can stop at any moment: a model that makes
IfcOpenShell loop, crash or eat the memory never freezes the window (study 20, section 4).

What is read, and only that:
- the roofs: IfcRoof and its parts, IfcSlab ROOF, IfcCovering ROOFING, the sloping plates of a curtain wall above the
  ground (a shed's glazing); a building without any, its slabs; one
  without slabs either, its walls (the outline and the top); on a building with roofs, also the slabs left under the
  open sky that stand on walls (a stair tower's top, a terrace); a slab under the building (a ceiling, another floor)
  is a floor, never a roof, and one with a storey of walls on it and no roof over them is that storey's body, its top
  flat at the walls' top (Above); a grating (ifc_grating) is never a roof nor covers one;
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

import itertools
import math
import re
import time
from collections.abc import Callable

import numpy as np

from . import ifc_grating, ifc_terrain

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
BASE_MIN = 0.5                            # m: an obstacle whose lowest point is higher above its roof stands raised
#                                           (its base); lower, it stands on the roof (feet, a plinth)
SIDE_FILL = 0.5                           # share of its box, seen from its side, a raised element fills at least: a
#                                           band climbing a stair fills about its height over the rise and is left out
SLENDER = 8.0                             # longest extent over the middle one: a rod, not a plate
LEAN = (15.0, 75.0)                       # degrees from the vertical: a slender element between them leans
OBSTACLE_MIN_AREA = 0.01                  # m2 in plan
# a slab left under the open sky on a building that has roofs elsewhere (a stair tower's top, a terrace: a designer calls
# them roofs, the model calls them floors): high enough, large enough, and standing on walls (a balcony does not)
TERRACE_MIN_HEIGHT = 2.0                  # m above the ground
TERRACE_MIN_AREA = 8.0                    # m2
TERRACE_MAX_TILT = 30.0                   # degrees
TERRACE_WALLS = 0.35                      # the share of its outline with a wall under it
# R34: «a roof is only what has no other building over it». A pitch guessed from slabs (a building without roofs, a
# terrace) is a floor when the building goes on above it (Above): covered, or a storey of walls standing on it
STOREY_CLEAR = 1.8                        # m: a slab, a roof or a covering this far above a pitch, or more, covers it
COVERED_SHARE = 0.5                       # the share of the pitch's plan under them that makes it a floor
STOREY_RISE = 2.0                         # m: a wall rising this far above the pitch is a storey's
STOREY_FOOT = 0.5                         # m: its foot no higher than this above the pitch
STOREY_EDGE = 0.6                         # m: standing inside the pitch beyond this from its outline (on the edge: a
#                                           parapet, or the facade of a body beside it)
STOREY_WALLS = 2.0                        # their length together over the side of the square of the pitch's area
COVER_CLASSES = ("IfcSlab", "IfcCovering")  # with the roofs' elements: what may cover a pitch
MAX_ROOF_FACES = 20000                    # faces looking up, the largest, that one roof's planes are looked for in
TESSELLATE_LOT = 150                      # elements at a time through IfcOpenShell's iterator
# R34: limits of quantity, in the file's order, never of time: the same file gives the same answer on every PC
MAX_SLOW_POINTS = 5000                    # elements whose points are read the slow way (Points), in one reading
MAX_CANDIDATES = 20000                    # elements that may stand on a roof whose shape is made (_obstacles): wide,
#                                           no model of the bench reaches it (5220 at most, R34)
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


def _item_faces(item, depth: int = 0, cache: dict | None = None) -> list:
    """The faces of a representation item in its own frame (file units); Unsupported when it is not simple. `cache` (the
    reading's, as for `_placement`) keeps the faces of a mapped representation, read once for all its instances; None
    reads them again every time."""
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
        # the indices of all the faces as one array, then split: an array for each face cost a third of the obstacles'
        # time on model A (r32-lentezze)
        lists = [face.CoordIndex for face in item.Faces]
        sizes = [len(x) for x in lists]
        if not lists:
            return []
        if min(sizes) == 0:
            raise IndexError("a face without indices")
        idx = np.fromiter(itertools.chain.from_iterable(lists), dtype=np.int64, count=sum(sizes))
        if pn:
            idx = np.asarray(pn, dtype=np.int64)[idx - 1]
        out = _split(coords[idx - 1], sizes)
        return out if getattr(item, "Closed", None) else [_upwards(f) for f in out]
    if kind == "IfcMappedItem" and depth < 4:
        source = item.MappingSource
        m = _operator(item.MappingTarget) @ _axis2(source.MappingOrigin)
        rot, move = m[:3, :3], m[:3, 3]
        out = []
        for points, sizes in _source_parts(source, depth, cache):
            out += _split(points @ rot.T + move, sizes)
        return out
    raise Unsupported(kind)


def _source_parts(source, depth: int, cache: dict | None) -> list:
    """The faces of an IfcRepresentationMap's items in the map's own frame, for each item with faces its points in
    one read-only array and the number of points of each face: what `_moved` makes of them before turning them, done
    once. A Revit family placed hundreds of times read the same Brep again for every instance, through IfcOpenShell's
    slow attribute access: 44 % of the reading of a 214 MB model (r33). The key carries the depth, which decides how
    deep a mapping inside it is still read; an Unsupported is kept and raised again for every instance."""
    key = ("map", source.id(), depth)
    if cache is not None and key in cache:
        hit = cache[key]
        if isinstance(hit, Unsupported):
            raise Unsupported(*hit.args)
        return hit
    parts = []
    try:
        for sub in source.MappedRepresentation.Items:
            faces = _item_faces(sub, depth + 1, cache)
            if not faces:
                continue
            arrays = [np.asarray(f, dtype=float) for f in faces]
            points = np.concatenate(arrays)
            points.flags.writeable = False          # shared by every instance: never changed in place
            parts.append((points, [len(a) for a in arrays]))
    except Unsupported as error:
        if cache is not None:
            cache[key] = error
        raise
    if cache is not None:
        cache[key] = parts
    return parts


def _moved(faces: list, rot: np.ndarray, move: np.ndarray, scale: float | None = None) -> list:
    """The faces (n_i, 3) scaled, turned and moved all at once, then split again: one product for each face cost a
    third of the obstacles' time on model A, of thousands of small faces (r32-lentezze)."""
    if not faces:
        return []
    arrays = [np.asarray(f, dtype=float) for f in faces]
    points = np.concatenate(arrays)
    if scale is not None:
        points = points * scale
    return _split(points @ rot.T + move, [len(a) for a in arrays])


def _split(points: np.ndarray, sizes: list) -> list:
    """`points` cut in consecutive pieces of `sizes` rows (views)."""
    out, at = [], 0
    for n in sizes:
        out.append(points[at:at + n])
        at += n
    return out


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
        faces += _item_faces(item, 0, cache)
    m = _placement(element.ObjectPlacement, cache, scale)
    return _moved(faces, m[:3, :3], m[:3, 3], scale)


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
            whole = [f for item in r.Items for f in _item_faces(_first_operand(item), 0, cache)]
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


class Points:
    """The one place that says where the points of an element come from (R34), for the walls, what is placed below the
    roofs, the slabs looked at for terraces and the outlines `_adopt` compares: from `given(element_id)` (the scan's,
    world metres) when it has them, else `box_points`, the slow way (each face read through IfcOpenShell from Python:
    94 s of a 180 MB model). The slow way is read for at most MAX_SLOW_POINTS elements in one reading, in the order they
    are asked (the file's): those after it are counted by what they are (`skipped`, "walls", "late", "slabs") and said.
    A limit of quantity gives the same answer on every PC; a limit of time did not."""

    def __init__(self, given, cache: dict, scale: float):
        self.given, self.cache, self.scale = given, cache, scale
        self.slow = 0                                   # elements read the slow way
        self.kept: dict = {}                            # id -> what the slow way gave: an element asked twice is read once
        self.skipped: dict = {}                         # what -> {ids}

    def of(self, e, what: str) -> np.ndarray | None:
        """The points of `e` (n, 3) in world metres, None when it has none or is past the limit (then counted)."""
        eid = e.id()
        if self.given is not None:
            pts = self.given(eid)
            if pts is not None and len(pts):
                return pts
        if eid in self.kept:
            return self.kept[eid]
        if self.slow >= MAX_SLOW_POINTS:
            self.skipped.setdefault(what, set()).add(eid)
            return None
        self.slow += 1
        pts = box_points(e, self.cache, self.scale)
        self.kept[eid] = pts
        return pts

    def count(self, counts: dict) -> None:
        """The elements left out by the limit, written in `counts` ("walls_skipped", "late_skipped", "slabs_skipped")."""
        for what, ids in self.skipped.items():
            if ids:
                counts[f"{what}_skipped"] = len(ids)
                counts["slow_limit"] = MAX_SLOW_POINTS
        counts["slow_points"] = self.slow


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


def _leaning(plates: list, shapes: dict, structure: Structure) -> list:
    """The plates of curtain walls that are roof glazing: their largest face looks up (UP), not flat, and they stand
    TERRACE_MIN_HEIGHT above their building's ground. A shed's glazing made as a curtain wall, not as an IfcRoof: its
    plates were no roof and each of its mullions became an obstacle as tall as the shed (a 5 cm mullion leaning from
    the roof to 4 m was a wall of 4 m). As roof pitches the glazing casts its shadow as the shed does (energy.system,
    the solid under a pitch) and the mullions lie in its plane (the rise of _obstacles). An upright facade, a flat plate
    and a canopy at the ground stay as they were (r32-montanti)."""
    level = math.cos(PLANE_ANGLE)
    out = []
    for e in plates:
        faces = shapes.get(e.id())
        if not faces:
            continue
        best, area = None, 0.0
        for face in faces:
            n, a = _normal(np.asarray(face, float))
            if a > area:
                best, area = n, a
        if best is None or not UP < abs(float(best[2])) < level:
            continue
        ground, _storey = structure.ground(structure.building_of(e.id()))
        if float(min(np.asarray(face, float)[:, 2].min() for face in faces)) >= ground + TERRACE_MIN_HEIGHT:
            out.append(e)
    return out


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


def roof_planes(faces: list, owners: list, deadline: float = math.inf, checkpoint=None) -> tuple[list, dict]:
    """The planes of a roof from its faces (world metres) and who owns each face: the faces looking up grouped by plane
    (1 degree, 5 cm); each plane's plan cut where another plane stands above it (the covering over the slab, the
    dormer over the pitch); what is left, wide enough and larger than MIN_PITCH_AREA, is a pitch. Returns the pitches
    ({"ring", "normal", "point", "area", "owners"}) and what was left out.

    A face joins a plane when its middle is within 5 cm of that plane, measured there, and the work is done about a
    point of the roof itself (R575): a model in a national grid stands millions of metres from its origin, where a
    normal off by the file's millimetres moves a plane's offset by hundreds of metres, and the faces of one plane (a
    flat roof's fan of triangles) each stood alone as a sliver.

    `deadline` (perf_counter): past it the planes left are not cut, counted as "uncut". `checkpoint`: called for every
    plane cut and every 256 faces grouped; what it raises goes out of here (a reading stopped on request)."""
    import shapely
    from shapely.strtree import STRtree
    check = checkpoint or (lambda: None)
    left = {"small": 0, "small_area": 0.0}
    here = next((np.array([float(p[0][0]), float(p[0][1]), 0.0]) for p in faces if len(p) >= 3), np.zeros(3))
    up = []
    for poly, owner in zip(faces, owners, strict=True):
        if len(poly) < 3:
            continue
        poly = np.asarray(poly, dtype=float) - here
        n, a = _normal(poly)
        if a < 1e-4 or n[2] < UP:
            continue
        up.append((a, n, poly.mean(axis=0), poly, owner))
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
    for at, (_a, n, middle, poly, owner) in enumerate(up):
        if at % 256 == 0:
            check()
        k = -1
        if len(normals):
            ok = np.nonzero((normals @ n > cos) & (np.abs(normals @ middle - offsets) < PLANE_OFFSET))[0]
            if len(ok):
                k = int(ok[0])
        if k < 0:
            normals = np.vstack((normals, n))
            offsets = np.append(offsets, float(n @ middle))
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
        check()
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
            ring = [[round(float(x + here[0]), 4), round(float(y + here[1]), 4)]
                    for x, y in list(piece.exterior.coords)[:-1]]
            out.append({"ring": ring, "normal": [float(v) for v in p["normal"]],
                        "point": [float(c.x + here[0]), float(c.y + here[1]), float(z_at(p, c.x, c.y))],
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

class Above:
    """What stands over the pitches the reader guesses from slabs (R34): «a roof is only what has no other building
    over it». One rule for the slabs of a building without roofs and for the terraces, never for the pitches of an
    IfcRoof (there the modeller said it is a roof).
    - A pitch COVERED is a floor and left out: COVERED_SHARE of its plan or more lies under the slabs, roofs and
      coverings that are not its own and whose lowest point is STOREY_CLEAR or more above it, measured there (a
      ceiling, another floor).
    - A pitch with A STOREY ON IT and nothing over it is the floor of a storey the model gives no roof to: it stays a
      body with its own outline, its top flat at the highest top of those walls (as the walls' rule of _roofs_of
      does), so the building keeps its mass and the partitions stand under its top. The walls of a storey: their
      foot within STOREY_FOOT of the pitch, their top STOREY_RISE or more above it, standing inside it beyond
      STOREY_EDGE from its outline, long together STOREY_WALLS times the side of the square of its area (the length
      of a wall: half the perimeter of the smallest rectangle of its plan inside the pitch); a terrace with a wall on
      it is not one (0.26 on a real one), an interior model's first floor is (4.7).
    The share is of the true plan of what covers it (the faces seen from above, _footprint_of), never of the hull:
    the hull of a U slab covered a slab in its recess, under the open sky beside the higher body. The points filter
    first (`source`, the scan's or the slow way): the shapes are made only of what touches the pitch, and only when
    their hulls together reach the share (the plan lies inside the hull). The walls come from `walls()` (_wall_hulls,
    read once for the whole reading); the covers' points are read on the first pitch looked at."""

    def __init__(self, f, source: Points, roof_elements: list, shapes: dict, geometry, walls, errors: list,
                 check=None, fraction: tuple[float, float] = (0.45, 0.55), gratings: set = frozenset()):
        self.f, self.source, self.roof_elements, self.shapes = f, source, roof_elements, shapes
        self.gratings = gratings        # R608: a grating covers nothing (ifc_grating)
        self.geometry, self.walls, self.fraction, self.errors = geometry, walls, fraction, errors
        self.check = check or (lambda: None)
        self._covers = None             # ([(element, hull, lowest z)], tree)
        self._wall_tree = None          # (hulls, tree)
        self._plans: dict = {}          # id -> the true plan of a cover, made once

    def floors(self, pitches: list, counts: dict) -> list:
        """The pitches that stay: those covered left out, counted in `counts` ("floors", "floors_area"); those with a
        storey on them raised to its top, flat, counted ("storeys_topped", "storeys_topped_area"). A pitch whose test
        fails on the model's geometry stays as it was, as before the rule, and the error is kept in `self.errors`."""
        kept = []
        for p in pitches:
            self.check()
            try:
                covered = self._covered(p)
                top = None if covered else self._storey_top(p)
            except _STEP_ERRORS as error:
                said = f"floors: {type(error).__name__}: {error}"
                if said not in self.errors:
                    self.errors.append(said)
                covered, top = False, None
            if covered:
                counts["floors"] = counts.get("floors", 0) + 1
                counts["floors_area"] = round(counts.get("floors_area", 0.0) + float(p["area"]), 3)
            elif top is not None:
                counts["storeys_topped"] = counts.get("storeys_topped", 0) + 1
                counts["storeys_topped_area"] = round(counts.get("storeys_topped_area", 0.0) + float(p["area"]), 3)
                kept.append({**p, "normal": [0.0, 0.0, 1.0], "point": [p["point"][0], p["point"][1], top]})
            else:
                kept.append(p)
        return kept

    def _storey_top(self, p: dict) -> float | None:
        """The highest top of the walls of a storey standing on `p`, None when they are not one (the class's rule)."""
        import shapely
        if self._wall_tree is None:
            hulls = self.walls()
            self._wall_tree = (hulls, shapely.STRtree([h[1] for h in hulls]) if hulls else None)
        hulls, tree = self._wall_tree
        ring = _polygon(p["ring"])
        inner = ring.buffer(-STOREY_EDGE)
        if tree is None or inner.is_empty:
            return None
        length, highest = 0.0, None
        for i in tree.query(ring, predicate="intersects"):
            _bid, hull, top, foot = hulls[int(i)]
            part = hull.intersection(ring)
            if part.is_empty:
                continue
            q = part.representative_point()
            z = plane_z(p, q.x, q.y)
            if foot > z + STOREY_FOOT or top < z + STOREY_RISE:
                continue
            piece = hull.intersection(inner)
            if not piece.is_empty:
                length += piece.minimum_rotated_rectangle.length / 2
                highest = top if highest is None else max(highest, top)
        return highest if length >= STOREY_WALLS * math.sqrt(max(ring.area, 1e-9)) else None

    def _cover_list(self) -> tuple[list, object]:
        import shapely
        if self._covers is None:
            items, met = [], set()
            others = (e for cls in COVER_CLASSES for e in _by_type(self.f, cls))
            for e in itertools.chain(self.roof_elements, others):
                if e.id() in met or e.id() in self.gratings:
                    continue
                met.add(e.id())
                self.check()
                faces = self.shapes.get(e.id())
                if faces:
                    pts = np.concatenate(faces)
                elif body(e) is None:
                    continue
                else:
                    pts = self.source.of(e, "covers")
                if pts is None or not len(pts):
                    continue
                items.append((e, _hull(pts), float(pts[:, 2].min())))
            self._covers = (items, shapely.STRtree([h for _e, h, _z in items]) if items else None)
        return self._covers

    def _covered(self, p: dict) -> bool:
        import shapely
        items, tree = self._cover_list()
        if tree is None:
            return False
        ring = _polygon(p["ring"])
        own = set(p.get("owners") or ())
        over, parts = [], []
        for i in tree.query(ring, predicate="intersects"):
            e, hull, low = items[int(i)]
            if e.id() in own:
                continue
            part = hull.intersection(ring)
            if part.is_empty or part.area <= 0.01:
                continue
            q = part.representative_point()
            if low < plane_z(p, q.x, q.y) + STOREY_CLEAR:
                continue
            over.append(e)
            parts.append(part)
        # the true plan lies inside the hull: when the hulls do not reach the share, the plans cannot either
        if not over or shapely.union_all(parts).area < COVERED_SHARE * ring.area:
            return False
        self.geometry(over, self.fraction)
        plans = []
        for e in over:
            if e.id() not in self._plans:
                faces = self.shapes.get(e.id())
                self._plans[e.id()] = _footprint_of(faces) if faces else None
            plan = self._plans[e.id()]
            if plan is not None:
                plans.append(plan.intersection(ring))
        return bool(plans) and shapely.union_all(plans).area >= COVERED_SHARE * ring.area


def _roofs_of(bid, elements: list, source: str, shapes: dict, structure: Structure, mode: str, counts: dict,
              deadline: float = math.inf, checkpoint=None, above: Above | None = None) -> list:
    """The roofs made by some elements of one building, one for each group of pitches that touch in plan: its name,
    its ground, its outline and its pitches. From walls (and in way d from anything) the outline and a flat top. From
    slabs, the pitches with the building over them are floors (`above`, Above.floors): left out when covered, raised
    to the top of the storey standing on them."""
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
    pitches, small = roof_planes(faces, owners, deadline, checkpoint)
    counts["fine_faces"] = counts.get("fine_faces", 0) + small.get("fine_faces", 0)
    if small.get("uncut"):
        # the planes not cut where another stands above them, the reading past its time (R34: counted and said)
        counts["uncut"] = counts.get("uncut", 0) + small["uncut"]
    counts["small_faces"] = counts.get("small_faces", 0) + small["small"]
    counts["small_area"] = round(counts.get("small_area", 0.0) + small["small_area"], 3)
    if source == "slabs":
        # the tops of the slabs above the ground floor: a slab at the ground is a floor, not a roof
        level = math.cos(math.radians(1.0))
        pitches = [p for p in pitches if p["normal"][2] > level and p["point"][2] > ground + 0.5]
        if above is not None:
            pitches = above.floors(pitches, counts)
    out = []
    for group in _components(pitches):
        members = [pitches[i] for i in group]
        ring = _outline([_polygon(p["ring"]) for p in members])
        if ring is not None:
            storeys = [structure.storey_of(o) for p in members for o in p["owners"]]
            # the storey most of its elements are in; of two as frequent the first met: a set gave one or the other
            # from a reading to the next (the order of a set of strings changes with every process)
            storey = max(dict.fromkeys(storeys), key=storeys.count) if storeys else ""
            out.append({**base, "footprint": ring, "pitches": members, "storey": storey})
    return out


def _adopt(orphans: list, roofless: list, f, structure: Structure, source: Points, check=None) -> None:
    """Roofs in no building given to the building without a roof whose walls and slabs they cover most (more than
    a third of the roof): the outline of those walls and slabs from their points alone (`source`), cheap."""
    from shapely.geometry import MultiPoint
    check = check or (lambda: None)
    points: dict = {}
    for cls, what in (("IfcWall", "walls"), ("IfcSlab", "slabs")):
        for e in _by_type(f, cls):
            bid = structure.building_of(e.id())
            if bid not in roofless:
                continue
            check()
            pts = source.of(e, what)
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


def _wall_hulls(f, structure: Structure, source: Points, check=None, tell=None) -> list:
    """Each wall as (building, plan hull, top, foot): from its points alone (`source`: the scan's, else the slow way
    up to its limit, the walls past it counted there as "walls" and said by the import)."""
    check = check or (lambda: None)
    out = []
    walls = _by_type(f, "IfcWall")
    for at, e in enumerate(walls):
        check()
        if tell is not None and at % 200 == 0:
            tell(0.55 + 0.02 * at / len(walls), "terraces")
        if body(e) is None:
            continue
        pts = source.of(e, "walls")
        if pts is not None and len(pts):
            out.append((structure.building_of(e.id()), _hull(pts), float(pts[:, 2].max()), float(pts[:, 2].min())))
    return out


def _bases(buildings: list, hulls: list, structure: Structure) -> dict:
    """Where each pitch's body stands, written on the pitch as "base" (world metres) with "base_from": the foot of the
    walls that rise along its outline up to it, followed down through the walls under them (a wall per storey); without
    walls, the level of its storey. A tower on a roof, a strip over a hall, a canopy on a first floor stand above the
    ground: the model does not have a base height yet (R352), so what is read is kept here for when it does.
    Returned: those walls of each pitch, {id(pitch): plan shape}, the outline of its body where its roof stops short
    of its facade (_obstacles)."""
    import shapely
    from shapely.strtree import STRtree
    tree = STRtree([h[1] for h in hulls]) if hulls else None
    walls: dict = {}
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
                    stack = list(reach)
                    for _i in range(12):
                        lower = [h for h in near if h[2] >= base - 0.5 and h[3] < base - 0.01]
                        if not lower:
                            break
                        stack += lower
                        base = min(h[3] for h in lower)
                    walls[id(p)] = shapely.union_all([h[1] for h in stack])
            if base is None:
                levels = [z for z in (structure.storey_level(o) for o in p["owners"]) if z is not None]
                if levels:
                    base, source = min(levels), "storey"
            p["base"] = base
            p["base_from"] = source
    return walls


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


def _terraces(bid, buildings: list, f, structure: Structure, source: Points, geometry, shapes: dict,
              seen: set, hulls: list, counts: dict, check=None, above: Above | None = None) -> list:
    """The slabs of a building with roofs that are left under the open sky: what the model calls a floor and the
    designer sees as a roof (a stair tower's top, a terrace over a lower wing). Faces are read only for the slabs that
    reach outside the roofs; each piece must stand on walls, or it is a balcony; covered it is a floor, with a storey
    on it it is raised to that storey's top (`above`, Above.floors)."""
    import shapely
    ground = structure.ground(bid)[0]
    own = [_polygon(p["ring"]) for b in buildings if b["ifc"] == bid for p in b["pitches"]]
    if not own:
        return []
    covered = shapely.union_all([s.buffer(0.1) for s in own])
    check = check or (lambda: None)
    todo = []
    for e in _by_type(f, "IfcSlab"):
        if e.id() in seen or structure.building_of(e.id()) != bid or body(e) is None:
            continue
        if str(getattr(e, "PredefinedType", "") or "") in ("LANDING", "BASESLAB"):
            continue
        check()
        pts = source.of(e, "slabs")
        if pts is None or not len(pts) or float(pts[:, 2].max()) < ground + TERRACE_MIN_HEIGHT:
            continue
        if _hull(pts).difference(covered).area >= 1.0:
            todo.append(e)
    if not todo:
        return []
    geometry(todo, (0.57, 0.62))
    faces, owners = [], []
    for e in todo:
        for face in shapes.get(e.id(), []):
            faces.append(face)
            owners.append(e.id())
    if not faces:
        return []
    planes, _left = roof_planes(faces, owners, checkpoint=check)
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
    if above is not None:
        kept = above.floors(kept, counts)
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
    span = _span(pts, pitches)
    return None if span is None else span[0]


def _span(pts: np.ndarray, pitches: list) -> tuple[float, float] | None:
    """How far some points stand above the roof under each of them (`pitches`: (plan shape, pitch)): the highest and
    the lowest, in one pass; None when no point has a roof under it."""
    import shapely
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
    roof = np.full(len(pts), -np.inf)
    if not pitches or not len(pts):
        return None
    # only the pitches whose box meets the points' box can have a point on them (r32-lentezze: 28 s of model A
    # went in this loop, every point against every pitch)
    box = shapely.bounds(np.array([shape for shape, _p in pitches], dtype=object))
    near = ((box[:, 0] <= x.max()) & (box[:, 2] >= x.min()) & (box[:, 1] <= y.max()) & (box[:, 3] >= y.min()))
    for i in np.flatnonzero(near):
        shape, p = pitches[i]
        inside = shapely.contains_xy(shape, x, y)
        if inside.any():
            n, (px, py, pz) = p["normal"], p["point"]
            here = pz - (n[0] * (x - px) + n[1] * (y - py)) / n[2]
            roof[inside] = np.maximum(roof[inside], here[inside])
    under = roof > -np.inf
    if not under.any():
        return None
    above = z[under] - roof[under]
    return float(above.max()), float(above.min())


def _leans(pts: np.ndarray) -> bool:
    """A slender element leaning over a roof (a tie rod, a brace): its longest extent along its principal axes at least
    SLENDER times the middle one, that axis between LEAN degrees from the vertical. As an obstacle (an upright prism of
    its plan outline) it would be a wall that does not exist; a leaning plate is not slender."""
    p = np.unique(np.round(pts, 4), axis=0)
    if len(p) < 4:
        return False
    centred = p - p.mean(axis=0)
    _values, axes = np.linalg.eigh(np.cov(centred.T))         # ascending: the last axis is the longest
    extent = np.ptp(centred @ axes, axis=0)
    l1, l2 = extent[2], extent[1]
    if l1 < SLENDER * l2:
        return False
    angle = math.degrees(math.acos(min(1.0, abs(float(axes[2, 2])))))
    return LEAN[0] <= angle <= LEAN[1]


def _side_fill(pts: np.ndarray) -> float:
    """How much of its box an element fills seen from its side: the convex hull of its points projected on the upright
    plane along its longest horizontal axis, over that box (its length by its height). 1 for a box, a pole, a railing
    lying level (its rail and its posts); about the band's height over the whole rise for a band climbing a stair,
    whose upright prism from its underside would be a wall that does not exist."""
    import shapely
    p = np.asarray(pts, float)
    if len(p) < 3 or np.ptp(p[:, 2]) < 1e-6:
        return 1.0
    xy = p[:, :2] - p[:, :2].mean(axis=0)
    _values, axes = np.linalg.eigh(np.cov(xy.T))
    side = np.column_stack((xy @ axes[:, 1], p[:, 2]))       # along the longest horizontal axis
    box = float(np.ptp(side[:, 0]) * np.ptp(side[:, 1]))
    if box < 1e-9:
        return 1.0
    hull = shapely.MultiPoint([tuple(q) for q in np.unique(np.round(side, 4), axis=0)]).convex_hull
    return float(hull.area) / box


# reading

def _step_errors() -> tuple:
    from shapely.errors import GEOSException
    return (GEOSException, ValueError, TypeError, AttributeError, IndexError, RuntimeError)


_STEP_ERRORS = _step_errors()


def read(path, mode: str = "direct", lazy: bool = True, threads: int = 1,
         progress: Callable[[float, str], None] | None = None, budget_s: float | None = None,
         points: Callable[[int], np.ndarray | None] | None = None, checkpoint: Callable[[], None] | None = None) -> dict:
    """What `path` holds for a photovoltaic design, as plain data (the module's docstring). `mode` is the way of study
    20: "direct" (the program's: read the simple shapes, tessellate the rest), "filtered" (tessellate only what is
    needed), "all" (tessellate everything, the baseline), "boxes" (the points only, no faces), "simple" (the simple
    shapes only, never the iterator: the second try after a crash). IfcError for a file that is not IFC.

    The limits are of quantity, in the file's order (MAX_SLOW_POINTS, MAX_CANDIDATES): the same file gives the same
    answer on every PC. `budget_s` (None: no limit of time, the jobs' case): past this many seconds the shapes still to
    make are left out and the planes still to cut are not cut, both counted ("over_budget", "uncut"), so that a model too
    rich in details still gives its roofs in the time the caller gives on its PC. `points(element_id)`: the points of an
    element in world metres, or None (the scan's, ifc_scan.Scan.points): what is read the slow way otherwise
    (Points). `checkpoint()`: called at every element or lot of the long loops; what it raises (resources.Stopped)
    goes out of here as it is."""
    if mode not in MODES:
        raise ValueError(f"mode: {mode!r}")
    tell = progress or (lambda _f, _w: None)
    check = checkpoint or (lambda: None)
    times: dict = {}
    t0 = time.perf_counter()
    deadline = t0 + budget_s if budget_s else math.inf
    tell(0.0, "open")
    f = open_model(path, lazy=lazy and mode != "all")
    times["open"] = time.perf_counter() - t0
    check()
    scale = unit_scale(f)
    cache: dict = {}
    source = Points(points, cache, scale)
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
    check()
    products = None
    if mode == "all":
        products = [e for e in _by_type(f, "IfcProduct") if getattr(e, "Representation", None) is not None
                    and not e.is_a("IfcOpeningElement") and not e.is_a("IfcSpace")]
    roofs = {r.id() for r in _by_type(f, "IfcRoof")}
    # R608: a grating lets the sun through (ifc_grating): never a roof, a terrace, a cover or a base for obstacles
    gratings = ifc_grating.of_file(f)
    if gratings:
        out["counts"]["gratings"] = len(gratings)
    candidates: dict = {}           # building -> [elements of the roof]
    for r in _by_type(f, "IfcRoof"):
        parts = [f.by_id(i) for i in structure.parts.get(r.id(), [])]
        parts = [p for p in parts if body(p) is not None and any(p.is_a(c) for c in ROOF_PARTS)
                 and p.id() not in gratings]
        use = parts or ([r] if body(r) is not None else [])
        for e in use:
            candidates.setdefault(structure.building_of(e.id()), []).append(e)
    # the gratings among those met: the slabs, coverings and plates after this, and the terraces, pass them by
    seen = {e.id() for es in candidates.values() for e in es} | gratings
    for cls in ("IfcSlab", "IfcCovering"):
        for e in _by_type(f, cls):
            if e.id() not in seen and _is_roof_part(e, structure, roofs) and body(e) is not None:
                candidates.setdefault(structure.building_of(e.id()), []).append(e)
                seen.add(e.id())
    # the plates of the curtain walls: those laid on a slope above the ground are roof glazing (_leaning, below)
    glazing = [p for cw in _by_type(f, "IfcCurtainWall") for p in (f.by_id(i) for i in structure.parts.get(cw.id(), []))
               if p.is_a("IfcPlate") and p.id() not in seen and body(p) is not None] if mode != "boxes" else []
    out["counts"]["roof_elements"] = sum(len(v) for v in candidates.values())
    tell(0.10, "roofs")

    shapes: dict = {}               # id -> list of faces (world metres)
    direct_ids: set = set()
    errors: list = []

    def geometry(elements: list, fraction: tuple[float, float]) -> None:
        todo = [e for e in elements if e.id() not in shapes]
        if mode == "boxes":
            for e in todo:
                check()
                pts = box_points(e, cache, scale)
                if pts is not None:
                    shapes[e.id()] = [pts]
            return
        rest = todo
        if mode in ("direct", "simple"):
            rest = []
            for k, e in enumerate(todo):
                check()
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
                check()                     # between the lots: the iterator is never left half way
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
        check()
        tris, errs = tessellate(f, products, threads, openings=True,
                                progress=lambda x: tell(0.10 + 0.6 * x, "tessellate"))
        errors.extend(errs)
        for eid, tri in tris.items():
            shapes[eid] = list(tri)
        times["tessellate_all"] = time.perf_counter() - t
        out["counts"]["tessellated"] = len(tris)
        out["counts"]["triangles"] = int(sum(len(v) for v in tris.values()))
    t = time.perf_counter()
    geometry([e for es in candidates.values() for e in es] + glazing, (0.10, 0.45))
    for e in _leaning(glazing, shapes, structure):
        candidates.setdefault(structure.building_of(e.id()), []).append(e)
        seen.add(e.id())
        out["counts"]["roof_elements"] += 1
        out["counts"]["glazing"] = out["counts"].get("glazing", 0) + 1
    times["roofs"] = time.perf_counter() - t

    tell(0.45, "planes")
    t = time.perf_counter()
    buildings: list = []
    for bid, elements in candidates.items():
        buildings += _roofs_of(bid, elements, "roof", shapes, structure, mode, out["counts"], deadline, check)
    # a roof in no building (hung on the site, as in buildingSMART's sample) goes to the building without a roof
    # whose walls and slabs it covers most
    # (and a building whose «roofs» gave no pitch, only strips and slats, is one without a roof)
    roofless = [bid for bid in structure.buildings if not any(b["ifc"] == bid for b in buildings)]
    orphans = [b for b in buildings if b["ifc"] is None]
    if roofless and orphans:
        _adopt(orphans, roofless, f, structure, source, check)
        roofless = [bid for bid in roofless if not any(b["ifc"] == bid for b in orphans)]
    kept_walls: list = []           # the walls' hulls, read once for the floors (Above) and the terraces

    def wall_hulls() -> list:
        if not kept_walls:
            try:
                kept_walls.append(_wall_hulls(f, structure, source, check, tell))
            except _STEP_ERRORS as error:
                kept_walls.append(error)
        if isinstance(kept_walls[0], BaseException):
            raise kept_walls[0]
        return kept_walls[0]
    # R34: a slab under the building (a ceiling, another floor) is a floor; one with a storey on it, that storey's body
    above = Above(f, source, [e for es in candidates.values() for e in es], shapes, geometry, wall_hulls, errors,
                  check, gratings=gratings) if mode != "boxes" else None
    # a building without a roof: the tops of its slabs above the ground that are not floors, else its walls
    for bid in roofless + ([None] if not structure.buildings and not buildings else []):
        slabs = [e for e in _by_type(f, "IfcSlab") if structure.building_of(e.id()) == bid and body(e) is not None
                 and str(getattr(e, "PredefinedType", "") or "") != "LANDING" and e.id() not in gratings]
        found: list = []
        if slabs:
            geometry(slabs, (0.45, 0.55))
            found = _roofs_of(bid, slabs, "slabs", shapes, structure, mode, out["counts"], deadline, check, above)
            out["counts"]["slab_elements"] = out["counts"].get("slab_elements", 0) + len(slabs)
        if not found:
            walls = [e for e in _by_type(f, "IfcWall") if structure.building_of(e.id()) == bid and body(e) is not None]
            if walls:
                geometry(walls, (0.45, 0.55))
                found = _roofs_of(bid, walls, "walls", shapes, structure, mode, out["counts"], deadline, check)
                out["counts"]["wall_elements"] = out["counts"].get("wall_elements", 0) + len(walls)
        buildings += found
    walls: dict = {}                # id(pitch) -> the walls of its body (_bases)
    if mode not in ("boxes", "all"):
        tell(0.55, "terraces")
        try:
            hulls = wall_hulls()
            for bid in list(candidates):
                if bid in structure.buildings:
                    buildings += _terraces(bid, buildings, f, structure, source, geometry, shapes, seen, hulls,
                                           out["counts"], check, above)
            out["counts"]["walls_outside"] = _walls_outside(hulls, buildings, structure)
            walls = _bases(buildings, hulls, structure)
        except _STEP_ERRORS as error:       # what is looked at beyond the roofs never costs the roofs
            errors.append(f"terraces: {type(error).__name__}: {error}")
    times["planes"] = time.perf_counter() - t
    out["counts"]["no_shape"] = sum(1 for es in candidates.values() for e in es if not shapes.get(e.id()))
    for b in buildings:
        b["ifc"] = structure.buildings[b["ifc"]].GlobalId if b["ifc"] in structure.buildings else ""

    tell(0.65, "obstacles")
    t = time.perf_counter()
    try:
        out["obstacles"], left = _obstacles(f, structure, buildings, shapes, cache, scale, mode, geometry, products,
                                              walls, source, check, tell, gratings)
        out["counts"].update(left)
    except _STEP_ERRORS as error:
        errors.append(f"obstacles: {type(error).__name__}: {error}")
        out["counts"]["obstacles_failed"] = 1
    times["obstacles"] = time.perf_counter() - t
    out["buildings"] = buildings
    source.count(out["counts"])
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


PLAN_FACES = 20000                        # faces: beyond this an obstacle's plan is the hull of its points (time)
PLAN_SIMPLIFY = 0.05                      # m
FACADE_BAND = 0.25                        # m: an element this close to a higher body (its roof and the walls under its
#                                           edge), under its roof, is its facade


def _plan_pieces(faces: list, pts: np.ndarray) -> list:
    """The plan of an element as it is (R575 D6): the union of its faces seen from above, simplified to 5 cm, concave
    where it is (a wall in U, a railing around a roof), in pieces without holes (a ring around a roof is cut in two
    across its hole: an obstacle has one outline). The hull of the points for an element without faces that have an
    area in plan (a pane upright), or with too many of them."""
    import shapely
    polys = [np.asarray(f, float)[:, :2] for f in faces if len(f) >= 3]
    if not polys or len(polys) > PLAN_FACES:
        return [_hull(pts)]
    by_size: dict = {}
    for f in polys:
        by_size.setdefault(len(f), []).append(f)
    shapes = np.concatenate([shapely.polygons(np.stack(group)) for group in by_size.values()])
    shapes = shapes[shapely.area(shapes) > 1e-6]
    bad = ~shapely.is_valid(shapes)
    if bad.any():
        shapes[bad] = shapely.make_valid(shapes[bad])
    try:
        plan = shapely.union_all(shapes).simplify(PLAN_SIMPLIFY) if len(shapes) else None
    except shapely.errors.GEOSException:
        plan = None
    if plan is None or plan.is_empty or plan.area < OBSTACLE_MIN_AREA:
        return [_hull(pts)]
    out = [g for g in _holeless(plan) if g.area >= OBSTACLE_MIN_AREA]
    return out or [_hull(pts)]


def _holeless(geom, depth: int = 0) -> list:
    """The polygons of a shape without holes: one with a hole is cut by the line across it, upright through the hole."""
    import shapely
    from shapely.ops import split
    out = []
    for g in getattr(geom, "geoms", [geom]):
        if g.geom_type != "Polygon" or g.is_empty:
            out += _holeless(g, depth + 1) if g.geom_type in ("MultiPolygon", "GeometryCollection") and depth < 8 else []
            continue
        if not g.interiors or depth >= 8:
            out.append(shapely.Polygon(g.exterior) if g.interiors else g)
            continue
        x = shapely.Polygon(g.interiors[0]).representative_point().x
        _x0, y0, _x1, y1 = g.bounds
        try:
            parts = split(g, shapely.LineString([(x, y0 - 1.0), (x, y1 + 1.0)]))
        except (ValueError, shapely.errors.GEOSException):
            out.append(shapely.Polygon(g.exterior))
            continue
        out += _holeless(parts, depth + 1)
    return out


def _ring_of(poly) -> list:
    return [[round(float(x), 4), round(float(y), 4)] for x, y in list(poly.simplify(SIMPLIFY).exterior.coords)[:-1]]


def _obstacles(f, structure, buildings, shapes, cache, scale, mode, geometry, products,
               walls: dict | None = None, source: Points | None = None, check=None, tell=None,
               gratings: set = frozenset()) -> tuple[list, dict]:
    """What stands on the roofs. The candidates (OBSTACLE_CLASSES) whose placement is above the lowest eave less a
    metre and within the roofs' extent, read (way c, else b); kept when the middle of their points falls on a roof and
    their top rises above it by OBSTACLE_MIN_HEIGHT (a skylight when it reaches the roof's surface), and not when they
    are the facade of a higher body beside that roof; their plan the union of their faces from above (R575 D6: the
    convex hull made a wall in U the whole roof), in pieces without holes. Those of one kind that touch on one roof and
    are compact together are one, their hull (the 175 panels of a row are one plant). Trees anywhere, as the hull of
    their points; never the model's terrain (ifc_terrain). Solar modules already in the model are counted and left
    out, and so are slender elements leaning over a roof (_leans: a tie rod would be a wall).

    Every obstacle has its base ("base"): how far its lowest point stands above the roof under it, when that is
    BASE_MIN or more, else 0 (it stands on the roof); for one made of several elements, the least of theirs (the
    segments of a mullion stacked from the roof up stand on it). What hangs above a roof (a stair's railing over a roof
    the stair is not on) comes in raised, from its underside to its top, where from the roof it was a wall that does
    not exist; "raised" counts the elements of the raised obstacles. A raised element that fills less than SIDE_FILL of
    its box seen from its side (_side_fill: a railing climbing along a stair) is left out, counted as "sloping": its
    prism would be a wall of the whole rise. "z0" and "z1" are its lowest and highest point.

    R34: the shapes are made for the first MAX_CANDIDATES candidates in the file's order, the others counted
    ("candidates_skipped"); the points of what is placed below the roofs come from `source` (its own limit)."""
    import shapely
    source = source or Points(None, cache, scale)
    check = check or (lambda: None)
    left = {"modules": 0, "off_roof": 0, "obstacle_candidates": 0, "under_roof": 0}
    roofs = []
    for k, b in enumerate(buildings):
        for p in b["pitches"]:
            roofs.append((k, _polygon(p["ring"]), p))
    if roofs:
        floor = min(plane_z(p, *p["point"][:2]) for _k, _s, p in roofs) - 1.0
        x0, y0, x1, y1 = shapely.union_all([s for _k, s, _p in roofs]).buffer(2.0).bounds
    roof_ids = {o for b in buildings for p in b["pitches"] for o in p["owners"]}
    # the roofs grown by 10 cm and by the facade band made once and prepared: made again for every roof at every
    # element they took 64 s of model A's 95 s of obstacles (r32-lentezze)
    grown = [(poly.buffer(0.1), p) for _k, poly, p in roofs]
    # the band of a facade from the outline of the body, its roof and the walls under its edge (_bases): a roof that stops
    # 0.6 m behind its facade left the windows of that facade as walls 5.6 m tall on the lower roof (r32-montanti)
    walls = walls or {}
    band = [(shapely.union_all([poly, walls[id(p)]]) if id(p) in walls else poly).buffer(FACADE_BAND)
            for _k, poly, p in roofs]
    for shape in [g for g, _p in grown] + band:
        shapely.prepare(shape)
    picked = []
    late = []                       # placed below the roofs or away from them: their points say whether they reach them
    seen: set = set()
    for cls in OBSTACLE_CLASSES:
        for e in _by_type(f, cls):
            if e.id() in seen or e.id() in roof_ids or e.id() in gratings or body(e) is None:
                continue
            seen.add(e.id())
            if len(seen) % 256 == 0:
                check()
            if e.is_a("IfcSolarDevice"):
                left["modules"] += 1
                continue
            if (e.is_a("IfcGeographicElement") or e.is_a("IfcBuildingElementProxy")) and ifc_terrain.of_entity(e, cache):
                left["terrain"] = left.get("terrain", 0) + 1        # R575 D4: never an obstacle
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
    for at, e in enumerate(late):
        check()
        if tell is not None and at % 200 == 0:
            tell(0.65 + 0.03 * at / len(late), "obstacles")
        pts = source.of(e, "late")
        if pts is None or not len(pts) or float(pts[:, 2].max()) < floor:
            continue
        rise = _rise(pts, grown)            # most of them stay under the roofs: nothing to tessellate
        if rise is not None and rise >= OBSTACLE_MIN_HEIGHT:
            picked.append(e)
    if len(picked) > MAX_CANDIDATES:
        # the first in the file's order (their ids), whatever the PC; the order they are looked at stays as it was
        keep = set(sorted(e.id() for e in picked)[:MAX_CANDIDATES])
        left["candidates_skipped"] = len(picked) - MAX_CANDIDATES
        left["candidates_limit"] = MAX_CANDIDATES
        picked = [e for e in picked if e.id() in keep]
    left["obstacle_candidates"] = len(picked)
    if mode != "all":
        geometry(picked, (0.68, 0.95))
    found = []                      # (building, kind, hull, z0, z1, element, its base over the roof)
    for e in picked:
        check()
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
        on = [(k, p) for (k, _poly, p), (g, _p) in zip(roofs, grown, strict=True) if shapely.contains_xy(g, cx, cy)]
        if not on:
            if kind == "tree":
                found.append((None, "tree", _hull(pts), z0, z1, e, 0.0))
            else:
                left["off_roof"] += 1
            continue
        low = min(plane_z(p, cx, cy) for _k, p in on)
        if kind != "tree" and any(plane_z(p, cx, cy) > max(z1 + 0.2, low + 1.0) and shapely.contains_xy(wide, cx, cy)
                                  for (_k, _poly, p), wide in zip(roofs, band, strict=True)):
            # R575 D6: a window or a panel of the facade of a higher body, above a lower roof beside it: the higher body
            # casts that shadow, the element was a «pole» 11.6 m tall on the lower roof
            left["facade"] = left.get("facade", 0) + 1
            continue
        k, pitch = max(on, key=lambda kp: plane_z(kp[1], cx, cy))
        base = plane_z(pitch, cx, cy)
        span = _span(pts, grown)
        # how far its top rises above the roof under it, and how far its lowest point hangs above it
        rise, gap = (z1 - base, z0 - base) if span is None else span
        if kind == "skylight":
            if rise < -0.05:
                left["off_roof"] += 1           # a window of a wall under the roof's edge
                continue
        elif rise < OBSTACLE_MIN_HEIGHT:
            left["under_roof"] += 1
            continue
        if kind not in ("tree", "skylight") and _leans(pts):
            left["leaning"] = left.get("leaning", 0) + 1        # a tie rod: a blade from the roof as an obstacle
            continue
        if z0 < base - 3.0 and kind != "parapet":
            kind = "other"                      # a shaft or a tower from the floors below
        # its base: what hangs above the roof stands raised, from its underside (a stair's railing over a roof the
        # stair is not on was a wall from the roof to its top); feet and plinths stand on it
        lift = gap if kind != "tree" and gap >= BASE_MIN else 0.0
        if lift > 0 and _side_fill(pts) < SIDE_FILL:
            # a band climbing a stair above a roof the stair is not on: raised from its underside to its top it would
            # be a wall of the whole rise (m20: 6.8 x 5.7 m for a railing about 1 m tall)
            left["sloping"] = left.get("sloping", 0) + 1
            continue
        for piece in (_plan_pieces(faces, pts) if kind != "tree" else [_hull(pts)]):
            found.append((k, kind, piece, max(z0, base) if kind != "tree" else z0, z1, e, lift))
    # one kind on one roof, touching: one obstacle
    out = []
    raised: set = set()
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
            # one element keeps its own plan (R575 D6); several, compact together, their hull
            hull = members[0][2] if len(members) == 1 else shapely.union_all([it[2] for it in members]).convex_hull
            if hull.geom_type != "Polygon":
                hull = hull.buffer(0.05)
            names = sorted({it[5].Name or "" for it in members} - {""})
            # several together stand where the lowest of them does (a mullion's segments stacked from the roof up)
            lift = min(it[6] for it in members)
            if lift > 0:
                raised |= {it[5].id() for it in members}
            out.append({"ring": _ring_of(hull), "z0": min(it[3] for it in members), "z1": max(it[4] for it in members),
                        "base": round(lift, 4), "kind": kind, "name": names[0] if names else "",
                        "class": members[0][5].is_a(), "elements": len(members), "building": k})
    left["raised"] = len(raised)
    return out, left
