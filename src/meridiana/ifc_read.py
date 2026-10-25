"""Reading an IFC model for what a photovoltaic design needs, and nothing more (study 20): where the site is and
where north is, the buildings with the planes of their roofs, their heights, what stands on the roofs. Without Qt;
the window runs it in a process of its own (ifc_worker.py), which it can stop at any moment: a model that makes
IfcOpenShell loop, crash or eat the memory never freezes the window (study 20, section 4).

What is read, and only that:
- the roofs: IfcRoof and its parts, IfcSlab ROOF, IfcCovering ROOFING; a building without any, its slabs; one
  without slabs either, its walls (the outline and the top);
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
# "simple": way c alone, without the iterator: what the window asks again when IfcOpenShell's iterator crashed or got
# stuck on a file (ui/ifc_import.py), the shapes it would have made left out and counted
MODES = ("all", "filtered", "direct", "boxes", "simple")


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


def _curve_points(c) -> list:
    """The points of a closed 2D curve made of straight segments; Unsupported for arcs and splines."""
    if c.is_a("IfcPolyline"):
        pts = [tuple(p.Coordinates[:2]) for p in c.Points]
    elif c.is_a("IfcIndexedPolyCurve"):
        if c.Segments and any(not s.is_a("IfcLineIndex") for s in c.Segments):
            raise Unsupported("arc in a curve")
        coords = [tuple(p[:2]) for p in c.Points.CoordList]
        if c.Segments:
            idx = []
            for s in c.Segments:
                for i in s.wrappedValue:
                    if not idx or idx[-1] != i:
                        idx.append(i)
            pts = [coords[i - 1] for i in idx]
        else:
            pts = coords
    else:
        raise Unsupported(c.is_a())
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


def box_points(element, cache: dict, scale: float) -> np.ndarray | None:
    """Way d: the points of an element's body without making any face (the extrusions' profiles at both ends, every
    point of a Brep or a face set), in world metres; None when it has none or they cannot be found."""
    try:
        faces = direct_faces(element, cache, scale)
    except Unsupported:
        r = body(element)
        if r is None:
            return None
        pts = [np.array(p.Coordinates, dtype=float) for item in r.Items for p in element.file.traverse(item)
               if p.is_a("IfcCartesianPoint") and len(p.Coordinates) == 3]
        if not pts:
            return None
        m = _placement(element.ObjectPlacement, cache, scale)
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
        self.f = f
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
    from shapely.geometry import Polygon
    p = Polygon(poly[:, :2])
    if not p.is_valid:
        p = p.buffer(0)
    return p


def _pieces(geom) -> list:
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    return [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon" and not g.is_empty]


def roof_planes(faces: list, owners: list) -> tuple[list, dict]:
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
    from shapely.geometry import Polygon
    shapes = [Polygon(p["ring"]).buffer(0.05) for p in pitches]
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

def _roofs_of(bid, elements: list, source: str, shapes: dict, structure: Structure, mode: str, counts: dict) -> list:
    """The roofs made by some elements of one building, one for each group of pitches that touch in plan: its name,
    its ground, its outline and its pitches. From walls (and in way d from anything) the outline and a flat top."""
    from shapely.geometry import MultiPoint, Polygon
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
                "area": float(Polygon(ring).area), "holes": 0, "owners": sorted(set(owners))}
        return [{**base, "source": "boxes" if mode == "boxes" else source, "footprint": ring, "pitches": [flat]}]
    pitches, small = roof_planes(faces, owners)
    counts["small_faces"] = counts.get("small_faces", 0) + small["small"]
    counts["small_area"] = round(counts.get("small_area", 0.0) + small["small_area"], 3)
    if source == "slabs":
        # the tops of the slabs above the ground floor: a slab at the ground is a floor, not a roof
        level = math.cos(math.radians(1.0))
        pitches = [p for p in pitches if p["normal"][2] > level and p["point"][2] > ground + 0.5]
    out = []
    for group in _components(pitches):
        members = [pitches[i] for i in group]
        ring = _outline([Polygon(p["ring"]) for p in members])
        if ring is not None:
            storeys = [structure.storey_of(o) for p in members for o in p["owners"]]
            storey = max(set(storeys), key=storeys.count) if storeys else ""
            out.append({**base, "footprint": ring, "pitches": members, "storey": storey})
    return out


def _adopt(orphans: list, roofless: list, f, structure: Structure, cache: dict, scale: float) -> None:
    """Roofs in no building given to the building without a roof whose walls and slabs they cover most (more than
    a third of the roof): the outline of those walls and slabs from their points alone (way d), cheap."""
    from shapely.geometry import MultiPoint, Polygon
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
        roof = Polygon(b["footprint"])
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


# reading

def read(path, mode: str = "direct", lazy: bool = True, threads: int = 1,
         progress: Callable[[float, str], None] | None = None) -> dict:
    """What `path` holds for a photovoltaic design, as plain data (the module's docstring). `mode` is the way of study
    20: "direct" (the program's: read the simple shapes, tessellate the rest), "filtered" (tessellate only what is
    needed), "all" (tessellate everything, the baseline), "boxes" (the points only, no faces), "simple" (the simple
    shapes only, never the iterator: the second try after a crash). IfcError for a file that is not IFC."""
    if mode not in MODES:
        raise ValueError(f"mode: {mode!r}")
    tell = progress or (lambda _f, _w: None)
    times: dict = {}
    t0 = time.perf_counter()
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
    tell(0.05, "structure")
    structure = Structure(f, scale, cache)
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
            for e in todo:
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
            tris, errs = tessellate(f, rest, threads, progress=lambda x: tell(lo + (hi - lo) * x, "tessellate"))
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
        buildings += _roofs_of(bid, elements, "roof", shapes, structure, mode, out["counts"])
    # a roof in no building (hung on the site, as in buildingSMART's sample) goes to the building without a roof
    # whose walls and slabs it covers most
    roofless = [bid for bid in structure.buildings if bid not in candidates]
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
            found = _roofs_of(bid, slabs, "slabs", shapes, structure, mode, out["counts"])
            out["counts"]["slab_elements"] = out["counts"].get("slab_elements", 0) + len(slabs)
        if not found:
            walls = [e for e in _by_type(f, "IfcWall") if structure.building_of(e.id()) == bid and body(e) is not None]
            if walls:
                geometry(walls, (0.45, 0.55))
                found = _roofs_of(bid, walls, "walls", shapes, structure, mode, out["counts"])
                out["counts"]["wall_elements"] = out["counts"].get("wall_elements", 0) + len(walls)
        buildings += found
    times["planes"] = time.perf_counter() - t
    for b in buildings:
        b["ifc"] = structure.buildings[b["ifc"]].GlobalId if b["ifc"] in structure.buildings else ""

    tell(0.65, "obstacles")
    t = time.perf_counter()
    out["obstacles"], left = _obstacles(f, structure, buildings, shapes, cache, scale, mode, geometry, products)
    times["obstacles"] = time.perf_counter() - t
    out["counts"].update(left)
    out["buildings"] = buildings
    out["counts"]["direct"] = len(direct_ids)
    out["counts"]["shapes"] = len(shapes)
    out["counts"]["errors"] = len(errors)
    out["errors"] = errors[:20]
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
    from shapely.geometry import Polygon
    left = {"modules": 0, "off_roof": 0, "obstacle_candidates": 0}
    roofs = []
    for k, b in enumerate(buildings):
        for p in b["pitches"]:
            roofs.append((k, Polygon(p["ring"]), p))
    if roofs:
        floor = min(plane_z(p, *p["point"][:2]) for _k, _s, p in roofs) - 1.0
        x0, y0, x1, y1 = shapely.union_all([s for _k, s, _p in roofs]).buffer(2.0).bounds
    roof_ids = {o for b in buildings for p in b["pitches"] for o in p["owners"]}
    picked = []
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
        if kind == "skylight":
            if z1 < base - 0.05:
                left["off_roof"] += 1           # a window of a wall under the roof's edge
                continue
        elif z1 - base < OBSTACLE_MIN_HEIGHT:
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
