"""What ifc_read found in an IFC model, made Meridiana's: buildings with their roofs and the exclusions on them, placed
around the project's site, as one change the designer can undo (study 20, section 6). Without Qt.

Where the model goes (`placing`):
- the model's place: from its IfcMapConversion when its coordinate system is a UTM one Meridiana converts (study 15:
  the map wins over the latitude and longitude, which FreeCAD truncates to the second), else from the IfcSite's
  RefLatitude and RefLongitude (at the site's placement), else none;
- the north: the map's (the model's X axis in the grid, and the meridian's convergence) when there is a map, else the
  context's TrueNorth; when both are there and differ by more than a degree, the designer chooses;
- three ways (`HOW`): "origin", the model's buildings centred on the project's plan, always the first proposal; "file",
  the model where the file says, around the project's site; "site", the project's site moved to the model's place.
- the project's site never changes unless the designer chooses "site" (Daniel, 05/11/2026: a project ended 500 km from
  where it was started, through an IfcSite called «Default»): `default_how` never answers it, and the place of a
  file is offered only when it can be trusted (`Place.trust`, `offers`).

The roofs (`plan`): a building of the model is split into bodies, the pitches that meet without a step (`_bodies`): a low
wing, a raised strip and a hall each stand on their own outline, with their own walls down to the ground. A piece too
small to be a roof is an obstacle when it rises above the roofs around it (a chimney's cap), else left out and said. Of
each body, a flat roof is a flat building; one plane a mono-pitch; planes of one slope and one eave height that
the straight skeleton of the outline makes again (roofs.pitched) a gable or a hip roof with its sides; anything else
free pitches, each with the side nearest to its fall as its eave. Heights are above the building's ground (the storey
at its zero, ifc_read.Structure.ground). Parapets along a flat roof's outline become its parapet; the other obstacles
exclusions with their height above the roof."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, replace

from . import geo, model, roofs, skeleton
from .i18n import _, ngettext, number

HOW = ("file", "site", "origin", "hand")    # "hand": as "origin", then placed on the plan (ifc_place, R454)
FAR_KM = 5.0                    # beyond this the site is better moved to the model than the model to the site
FLAT = 0.5                      # degrees: a plane flatter than this is flat
SAME_TILT = 1.0                 # degrees: pitches of one roof
SAME_EAVE = 0.10                # m
LEVEL = 0.30                    # m: flat planes closer than this are one roof (a covering, a curb), farther two
SMALL_ROOF = 8.0                # m2: a roof at a height of its own smaller than this (a balcony, a canopy) is left out
PARAPET_BAND = 0.6              # m from the outline: a wall there is the parapet
RAISED = 1.0                    # m above the ground: a body whose walls start higher stands on something else
STEP = 0.30                     # m: pitches closer than this along what they share are one roof
STEP_SHARE = 0.8                # of the length they share
NAME_CHARS = 28                 # a name longer than this reads the same on all the bodies in a list of buildings
STOREY_CHARS = 24               # of a storey's name, in the name of a body
EXCLUSION_KINDS = {"chimney": "chimney", "skylight": "skylight", "tree": "tree", "vent": "vent", "plant": "plant"}
# the names programs give a site nobody named: its latitude and longitude are then the template's, not the project's
# (seen: an IfcSite «Default» 500 km from the building; see `trust_of`)
PLACEHOLDER_SITES = {"", "default", "default site", "site", "sito", "ifcsite", "surface", "terrain", "terreno",
                     "my site", "unnamed", "senza nome", "standard"}


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


@dataclass
class Place:
    """Where the model's origin is on the Earth and where its north is."""
    lat: float | None = None
    lon: float | None = None
    origin: tuple = (0.0, 0.0)      # the model's point (world metres) at that latitude and longitude
    source: str = "none"            # "map", "site", "none"
    north_map: float | None = None  # degrees, counter-clockwise from the model's +Y, by the map
    north_context: float = 0.0      # the same by the context's TrueNorth
    north: str = "context"          # the one used: "map" or "context"
    crs: str = ""
    notes: list = field(default_factory=list)
    trust: str = "none"             # "map", "site": may be proposed; "default": a template's place; "none"
    site_name: str = ""

    @property
    def angle(self) -> float:
        return self.north_map if self.north == "map" and self.north_map is not None else self.north_context

    def reliable(self) -> bool:
        """A place that may be proposed to the designer: a map conversion, or a site somebody set."""
        return self.trust in ("map", "site") and self.lat is not None

    def disagree(self) -> bool:
        if self.north_map is None:
            return False
        return abs((self.north_map - self.north_context + 180.0) % 360.0 - 180.0) > 1.0


def place_of(found: dict) -> Place:
    """The model's place and north (the module's docstring)."""
    out = Place(north_context=float(found.get("true_north") or 0.0))
    m = found.get("map")
    utm = geo.utm_of_crs(m["crs"]) if m else None
    if m:
        out.crs = m.get("crs") or ""
        a, o = m.get("x_axis") or (1.0, 0.0)
        alpha = math.degrees(math.atan2(o, a)) if math.hypot(a, o) > 1e-12 else 0.0
        gamma = 0.0
        unit = float(m.get("map_unit_m") or 1.0)
        east, north = float(m["eastings"]) * unit, float(m["northings"]) * unit
        if abs(east) > 1e7 or abs(north) > 1e8:
            # beyond the Earth in metres: millimetres written under a metre (Revit 2020 does, study 20, 3.6)
            east, north = east / 1000.0, north / 1000.0
            out.notes.append(_("The map's eastings and northings were in millimetres, though the file says metres: "
                               "read as millimetres."))
        if utm is not None and math.hypot(east, north) < 1.0:
            # a conversion written with no coordinates (a program's default) says nothing of the place
            out.notes.append(_("The map conversion has no coordinates: it says nothing of the model's place."))
        elif utm is not None:
            zone, south = utm
            out.lat, out.lon = geo.from_utm(zone, east, north, south)
            gamma = geo.to_utm(out.lat, out.lon, zone)[3]
            out.source = "map"
        else:
            out.notes.append(_("The map's coordinate system ({crs}) is not one Meridiana converts: the site's latitude "
                               "and longitude are used, and its north without the convergence.").format(
                                   crs=out.crs or "?"))
        out.north_map = (gamma - alpha + 180.0) % 360.0 - 180.0
        out.north = "map"
    if out.source == "none" and found.get("site"):
        s = found["site"]
        out.lat, out.lon, out.source = float(s["lat"]), float(s["lon"]), "site"
        out.origin = tuple(float(v) for v in (s.get("placement") or (0.0, 0.0))[:2])
        out.site_name = " ".join(str(s.get("name") or "").split())
    out.trust = trust_of(out)
    if out.trust == "default":
        out.notes.append(_("The file's site ({name}, {lat}, {lon}) looks like the template's, not the project's: its place "
                           "is not used. Its sun would be wrong without saying so.").format(
                               name=f"«{out.site_name}»" if out.site_name else _("without a name"),
                               lat=number(out.lat, 4), lon=number(out.lon, 4)))
    if out.disagree():
        out.notes.append(_("The model's TrueNorth says {a}°, its map conversion {b}°: check where north is.").format(
            a=number(out.north_context, 1), b=number(out.north_map, 1)))
    return out


def trust_of(place: Place) -> str:
    """How far the model's place can be believed: "map" from a map conversion with coordinates; "default" from an
    IfcSite that nobody set, by its name or by coordinates that are no place (the Gulf of Guinea); "site" from an
    IfcSite somebody named; "none" without a place."""
    if place.lat is None:
        return "none"
    if place.source == "map":
        return "map"
    if place.site_name.casefold() in PLACEHOLDER_SITES or (abs(place.lat) < 1e-6 and abs(place.lon) < 1e-6):
        return "default"
    return "site"


def offers(place: Place, project: model.Project) -> tuple[str, ...]:
    """The ways the designer may choose for this model: always "origin"; with a place that can be trusted "file", and
    "site" while nothing is drawn (the drawing is measured from the site)."""
    if not place.reliable():
        return ("origin",)
    if project.buildings or project.subfields:
        return ("origin", "file")
    return ("origin", "file", "site")


def distance_km(place: Place, site: model.Site) -> float | None:
    if place.lat is None:
        return None
    x, y = geo.Origin(site.lat, site.lon).to_local(place.lon, place.lat)
    return math.hypot(x, y) / 1000.0


def default_how(place: Place, project: model.Project) -> str:
    """Always by hand on the plan (R454: «li inserisca direttamente al centro della mappa non mi piace molto»): the
    model follows the pointer over what is already drawn and the map. A place in the file is a proposal the designer
    accepts, with the distance in front of him (also as the first choice of the coordinates, ifc_place.proposal), never
    what happens by itself; and on an empty project too."""
    return "hand"


class Frame:
    """From the model's world metres to the project's plan: turned to the true north, then moved."""

    def __init__(self, found: dict, place: Place, how: str, site: model.Site, at: tuple = (0.0, 0.0)):
        self.theta = math.radians(place.angle)
        self.c, self.s = math.cos(-self.theta), math.sin(-self.theta)
        self.ox, self.oy = place.origin
        self.dx = self.dy = 0.0
        if how == "file" and place.lat is not None:
            self.dx, self.dy = geo.Origin(site.lat, site.lon).to_local(place.lon, place.lat)
        elif how in ("origin", "hand"):
            pts = [self.turn(x, y) for b in found.get("buildings") or [] for x, y in b["footprint"]]
            pts += [self.turn(x, y) for s in found.get("supports") or [] for x, y in s["ring"]]
            if pts:
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                self.dx, self.dy = at[0] - (min(xs) + max(xs)) / 2, at[1] - (min(ys) + max(ys)) / 2

    def turn(self, x: float, y: float) -> tuple[float, float]:
        x, y = x - self.ox, y - self.oy
        return self.c * x - self.s * y, self.s * x + self.c * y

    def point(self, x: float, y: float) -> list[float]:
        u, v = self.turn(x, y)
        return [round(u + self.dx, 3), round(v + self.dy, 3)]

    def ring(self, ring) -> list[list[float]]:
        out = [self.point(x, y) for x, y in ring]
        area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(out, out[1:] + out[:1], strict=True))
        return out if area > 0 else out[::-1]

    def normal(self, n) -> tuple[float, float, float]:
        return self.c * n[0] - self.s * n[1], self.s * n[0] + self.c * n[1], n[2]


@dataclass
class Plan:
    """What the import adds: buildings and exclusions without their ids yet (`apply` gives them), the site when it is
    moved, and the lists of the summary."""
    buildings: list = field(default_factory=list)       # model.Building, id ""
    exclusions: list = field(default_factory=list)      # (model.ExclusionItem, index of its building or None)
    supports: list = field(default_factory=list)        # (unfilled model.SubField, index of its building)
    site: model.Site | None = None
    taken: list = field(default_factory=list)
    approximated: list = field(default_factory=list)
    left_out: list = field(default_factory=list)
    moved_area: float = 0.0                             # m2 of pitches that became obstacles
    # for each of `buildings`, where its body really stands: {"base": m above the ground or None, "from": "walls" or
    # "storey" or "", "storey": name}. Today every building rises from the ground (R352 will use this)
    bases: list = field(default_factory=list)
    # R453: where the model's world is in the plan, for an export that lies on the model it came from (`reference`)
    reference: dict = field(default_factory=dict)
    grounds: list = field(default_factory=list)          # for each of `buildings`, its ground in the model's world
    # R400: for each of `buildings`, the index of the body it is a part of (the first body of its group), None alone
    parts: list = field(default_factory=list)
    zone_rings: list = field(default_factory=list)       # the solids left out by the zone, plan rings (the preview)


def reference(found: dict, place: Place, frame: Frame, how: str, source_name: str | None) -> dict:
    """What an export needs to lie on the model it came from (R453): the frame from the model's world to the plan
    (`Frame`: turned by `theta` degrees about the model's `origin`, then moved by `shift`), the model's site, true north
    and map conversion as the file has them, in metres. Plain data, kept in the project (Project.resources)."""
    m = found.get("map")
    out = {"file": source_name or "", "how": how, "theta": round(math.degrees(frame.theta), 9),
           "origin": [float(frame.ox), float(frame.oy)], "shift": [float(frame.dx), float(frame.dy)],
           "true_north": float(found.get("true_north") or 0.0), "site": None, "map": None}
    ctx = found.get("context")
    if isinstance(ctx, dict) and ctx.get("mesh"):
        # r21-ifc-vista: the model's true geometry (ifc_mesh) for the 3D, its ground the bodies' ground
        out["context"] = {"mesh": str(ctx["mesh"]), "triangles": int(ctx.get("triangles") or 0),
                          "ground": float(found.get("solids_ground") or 0.0)}
    s = found.get("site")
    if s:
        out["site"] = {"lat": float(s["lat"]), "lon": float(s["lon"]), "elevation": float(s.get("elevation") or 0.0),
                       "name": str(s.get("name") or ""),
                       "placement": [float(v) for v in (s.get("placement") or [0.0, 0.0, 0.0])][:3]}
    if m:
        unit = float(m.get("map_unit_m") or 1.0)
        east, north = float(m.get("eastings") or 0.0) * unit, float(m.get("northings") or 0.0) * unit
        if abs(east) > 1e7 or abs(north) > 1e8:          # millimetres written under a metre, as place_of reads them
            east, north, unit = east / 1000.0, north / 1000.0, unit / 1000.0
        model_unit = float(m.get("unit_m") or 1.0)
        out["map"] = {"crs": str(m.get("crs") or ""), "description": str(m.get("description") or ""),
                      "eastings": east, "northings": north, "height": float(m.get("height") or 0.0) * unit,
                      "x_axis": [float(v) for v in (m.get("x_axis") or [1.0, 0.0])][:2],
                      "scale": float(m.get("scale") or 1.0) * unit / model_unit if model_unit else 1.0}
    return out


def _tilt_azimuth(n) -> tuple[float, float]:
    tilt = math.degrees(math.acos(max(-1.0, min(1.0, n[2]))))
    if tilt < FLAT:
        return 0.0, 0.0
    return tilt, geo.bearing_to_azimuth(geo.bearing(n[0], n[1]))


def _angle(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


class _Pitch:
    """A pitch of the model in the project's plan: its ring, tilt, azimuth and plane."""

    def __init__(self, raw: dict, frame: Frame, ground: float):
        self.ring = frame.ring(raw["ring"])
        n = frame.normal(raw["normal"])
        self.tilt, self.azimuth = _tilt_azimuth(n)
        self.n = n
        px, py = frame.point(*raw["point"][:2])
        self.px, self.py, self.pz = px, py, float(raw["point"][2]) - ground
        self.area = float(raw.get("area") or 0.0)
        self.holes = int(raw.get("holes") or 0)
        self.owners = list(raw.get("owners") or [])
        # where its body stands, above the ground (ifc_read._bases); None not known. Kept for R352: Building has no base
        self.base = None if raw.get("base") is None else float(raw["base"]) - ground
        self.base_from = raw.get("base_from") or ""

    def z(self, x: float, y: float) -> float:
        if self.tilt == 0.0:
            return self.pz
        return self.pz - (self.n[0] * (x - self.px) + self.n[1] * (y - self.py)) / self.n[2]

    def eave_side(self) -> tuple[int, float]:
        """The side the plane falls to: of the sides facing within 20 degrees of its azimuth the lowest, else the one
        facing nearest; and how far its facing is from the plane's azimuth."""
        ring = self.ring
        inside = _inside(ring)
        sides = []
        for i in range(len(ring)):
            a, b = ring[i], ring[(i + 1) % len(ring)]
            if math.dist(a, b) < 1e-6:
                continue
            off = _angle(roofs._outward_azimuth(a, b, inside), self.azimuth)
            z = (self.z(*a) + self.z(*b)) / 2
            sides.append((off, z, math.dist(a, b), i))
        if not sides:
            return 0, 0.0
        near = [s for s in sides if s[0] < 20.0]
        best = min(near, key=lambda s: (round(s[1], 2), -s[2])) if near else min(sides)
        return best[3], best[0]


def _inside(ring) -> tuple[float, float]:
    p = _polygon(ring).representative_point()
    return p.x, p.y


def _matches(found: list[_Pitch], made: list[roofs.Pitch]) -> bool:
    """The planes a roof type makes are the planes of the model: as many, each facing as one of them (2 degrees)
    with its area (5 %, and 0,5 m2)."""
    if len(found) != len(made):
        return False
    free = list(found)
    for p in made:
        area = _polygon(p.ring).area
        hit = next((f for f in free if _angle(f.azimuth, p.azimuth) < 2.0
                    and abs(_polygon(f.ring).area - area) <= max(0.05 * area, 0.5)), None)
        if hit is None:
            return False
        free.remove(hit)
    return True


def _roof(footprint: list, pitches: list[_Pitch], notes: dict) -> tuple[float, model.Roof]:
    """The eave height and the roof of a building from its pitches (the module's docstring)."""
    flat = all(p.tilt == 0.0 for p in pitches)
    if flat and max(p.pz for p in pitches) - min(p.pz for p in pitches) < LEVEL:
        return max(pitches, key=lambda p: p.area).pz, model.Roof(type="flat")
    if len(pitches) == 1:
        p = pitches[0]
        side, off = p.eave_side()
        if off > SAME_TILT:
            notes["slope"] = max(notes.get("slope", 0.0), off)
        a = p.ring[side]
        return p.z(*a), model.Roof(type="mono", eave_side=side, tilt=round(p.tilt, 2))
    tilts = [p.tilt for p in pitches]
    eaves = [min(p.z(x, y) for x, y in p.ring) for p in pitches]
    if not flat and max(tilts) - min(tilts) <= SAME_TILT and max(eaves) - min(eaves) <= SAME_EAVE:
        eave = min(eaves)
        tilt = sum(tilts) / len(tilts)
        n = len(footprint)
        gables = set()
        for i in range(n):
            a, b = footprint[i], footprint[(i + 1) % n]
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            top = max((p.z(*mid) for p in pitches if _near(p.ring, mid)), default=eave)
            if top > eave + 0.3:
                gables.add(i)
        try:
            made, dropped = roofs.pitched(footprint, eave, tilt, gables)
        except skeleton.SkeletonError:
            made, dropped = [], set()
        if made and not dropped and _matches(pitches, made):
            kind = "gable" if gables else "hip"
            edges = ["gable" if i in gables else "eave" for i in range(n)]
            return eave, model.Roof(type=kind, tilt=round(tilt, 2), edges=edges)
    free = []
    for k, p in enumerate(pitches):
        side, off = p.eave_side()
        if p.tilt > 0 and off > SAME_TILT:
            notes["slope"] = max(notes.get("slope", 0.0), off)
        a = p.ring[side]
        free.append({"id": f"p{k + 1}", "ring": p.ring, "eave_side": side, "eave": round(p.z(*a), 3),
                     "tilt": round(p.tilt, 2)})
    # joined=False: the planes the model has, measured, stay as they are (R304 joins what is drawn by hand)
    return min(f["eave"] for f in free), model.Roof(type="free", free_pitches=free, joined=False)


def _near(ring, point, tol: float = 0.05) -> bool:
    from shapely.geometry import Point
    return _polygon(ring).buffer(tol).contains(Point(point))


def _meet(a: _Pitch, b: _Pitch) -> bool:
    """Two pitches of one roof: they touch in plan and, along nearly all of what they share, stand within STEP of each
    other. A strip raised over a slope touches it along its whole length and meets its height only somewhere: two
    roofs. Within STEP, the sheets of a roof 2 cm apart, or a hall built in two parts: one."""
    pa, pb = _polygon(a.ring), _polygon(b.ring)
    if not pa.is_valid or not pb.is_valid or pa.distance(pb) > 0.1:
        return False
    shared = pa.boundary.intersection(pb.buffer(0.1))
    length = shared.length
    if length < 0.2:
        return False
    steps = max(4, int(length / 0.5))
    met = 0
    parts = list(getattr(shared, "geoms", [shared]))
    total = 0
    for part in parts:
        n = max(1, round(steps * part.length / length))
        for i in range(n):
            q = part.interpolate((i + 0.5) / n, normalized=True)
            total += 1
            met += abs(a.z(q.x, q.y) - b.z(q.x, q.y)) < STEP
    return total > 0 and met / total >= STEP_SHARE


def _bodies(pitches: list[_Pitch]) -> list[list[_Pitch]]:
    """The pitches of a roof grouped into the bodies that meet (`_meet`), the largest first."""
    seen: set = set()
    out = []
    for i in range(len(pitches)):
        if i in seen:
            continue
        seen.add(i)
        group, todo = [], [i]
        while todo:
            k = todo.pop()
            group.append(pitches[k])
            for j in range(len(pitches)):
                if j not in seen and _meet(pitches[k], pitches[j]):
                    seen.add(j)
                    todo.append(j)
        out.append(group)
    return sorted(out, key=lambda g: -sum(p.area for p in g))


def _clean_name(text) -> str:
    """A name as Revit's long lines write it, with its runs of spaces closed."""
    return " ".join(str(text or "").split())


def _short_storey(text) -> str:
    """A storey's name fit for a list: without the code in front of it and what comes after a dash («XY - Top floor -
    As built» is «Top floor»), cut to STOREY_CHARS."""
    parts = [p for p in re.split(r"\s*-\s+", _clean_name(text or "")) if p]
    if len(parts) > 1 and " " not in parts[0]:
        parts = parts[1:]
    return parts[0][:STOREY_CHARS].rstrip() if parts else ""


def plan(found: dict, project: model.Project, how: str = "origin", north: str | None = None,
         name: str = "IFC", source_name: str | None = None, at: tuple = (0.0, 0.0), solids: str | None = None,
         kinds: str = "all", zone: tuple | None = None, storeys=None, shade: str = "off") -> Plan:
    """The buildings and the exclusions of `found` (ifc_read.read) for `project`, placed the way `how` says (`at`: the
    middle of the buildings in the plan, for "origin"), with the north `north` ("map" or "context"; None: the map's when
    there is one). `storeys`: the names of the storeys to take (`storeys_of`), None all of them. `shade` (r22-ifc,
    SHADE): whether the model's true shapes cast the shadows of the calculation (ifc_shade), and how far. Nothing of the
    project is changed."""
    from shapely.geometry import Point
    unfiltered, found = found, by_storeys(found, storeys)
    place = place_of(found)
    if north in ("map", "context") and (north == "context" or place.north_map is not None):
        place.north = north
    if how not in HOW or (how not in ("origin", "hand") and place.lat is None):
        how = "origin"
    out = Plan()
    site = project.site
    if how == "site":
        site = model.Site(lat=round(place.lat, 7), lon=round(place.lon, 7), address=project.site.address)
        out.site = site
    frame = Frame(found, place, how, site, at)
    notes: dict = {}
    # R400: the solids of the model chosen (the way, the kinds, the zone in the plan), as buildings of a flat top
    solids = default_solids(found) if solids is None else solids
    extra, zoned = solid_raws(found, solids, kinds, zone, frame)
    if extra:
        found = {**found, "buildings": list(found.get("buildings") or []) + extra}
    first_solid = len(found.get("buildings") or []) - len(extra)
    made: list = []                 # (index in found["buildings"], model.Building, its pitches)
    small: list = []                # (ring, top above the ground, index in found["buildings"]): pitches made obstacles
    names: dict = {}
    # an IFC building in several pieces, each on a storey of its own: the storeys' names (Meridiana's export writes a
    # storey for each building)
    by_ifc: dict = {}
    for raw in found.get("buildings") or []:
        by_ifc.setdefault(raw.get("ifc"), []).append(raw.get("storey") or "")
    storey_names = {k for k, v in by_ifc.items() if len(v) > 1 and all(v) and len(set(v)) == len(v)}
    for k, raw in enumerate(found.get("buildings") or []):
        ground = float(raw.get("ground") or 0.0)
        pitches = [_Pitch(p, frame, ground) for p in raw["pitches"]]
        if not pitches:
            continue
        groups = _bodies(pitches)
        area_of = [sum(p.area for p in g) for g in groups]
        for g_index, group in enumerate(groups):
            if len(groups) > 1 and area_of[g_index] < SMALL_ROOF:
                others = [p for q, g in enumerate(groups) if q != g_index for p in g]
                _small_body(group, others, k, small, notes)
                continue
            if len(groups) > 1:
                import shapely
                union = shapely.union_all([_polygon(p.ring).buffer(0.08) for p in group]).buffer(-0.08)
                parts = [g for g in getattr(union, "geoms", [union]) if g.geom_type == "Polygon" and g.area > 0.5]
                part = max(parts, key=lambda g: g.area) if parts else None
                if part is None:
                    continue
                footprint = [[round(x, 4), round(y, 4)] for x, y in list(part.simplify(0.02).exterior.coords)[:-1]]
                footprint = footprint if _area2(footprint) > 0 else footprint[::-1]
            else:
                footprint = frame.ring(raw["footprint"])
            if len(footprint) < 3:
                continue
            eave, roof = _roof(footprint, group, notes)
            label = _clean_name((raw.get("storey") if raw.get("ifc") in storey_names else raw.get("name"))
                                or raw.get("storey") or name)
            if raw.get("source") == "boxes":
                notes["boxes"] = notes.get("boxes", 0) + 1
            if raw.get("source") == "terrace":
                notes["terraces"] = notes.get("terraces", 0) + 1
            names[label] = names.get(label, 0) + 1
            b = model.Building(id="", name=label, footprint=footprint, height=round(max(eave, 0.1), 3), roof=roof)
            if eave < 0.1:
                notes["low"] = notes.get("low", 0) + 1
            notes["holes"] = notes.get("holes", 0) + sum(p.holes for p in group)
            made.append((k, b, group))
            out.grounds.append(ground)
            known = [p for p in group if p.base is not None]
            lowest = min(known, key=lambda p: p.base) if known else None
            out.bases.append({"base": round(lowest.base, 3) if lowest else None, "from": lowest.base_from if lowest else "",
                              "storey": raw.get("storey") or ""})
            if lowest is not None and lowest.base > RAISED:
                notes["raised"] = notes.get("raised", []) + [round(lowest.base, 2)]
    # «Name», «Name 2»... when one name is several buildings; a name too long for a list would read the same on all of
    # them, so these go by their number and storey (r15-subito 8e562139, recovered in r21-recuperi)
    seen: dict = {}
    bodies = 0
    for k, b, _p in made:
        if names[b.name] > 1 and len(b.name) > NAME_CHARS:
            bodies += 1
            storey = _short_storey(found["buildings"][k].get("storey"))
            b.name = (_("Body {n}, {storey}").format(n=bodies, storey=storey) if storey
                      else _("Body {n}").format(n=bodies))
        elif names[b.name] > 1:
            seen[b.name] = seen.get(b.name, 0) + 1
            if seen[b.name] > 1:
                b.name = f"{b.name} {seen[b.name]}"
    out.buildings = [b for _k, b, _p in made]
    out.zone_rings = zoned
    made_of = {k: i for i, (k, _b, _p) in enumerate(made)}
    out.parts = []
    for i, (k, _b, _p) in enumerate(made):
        whole = found["buildings"][k].get("whole") if k >= first_solid else None
        whole = made_of.get(first_solid + whole) if whole is not None else None
        out.parts.append(whole if whole is not None and whole != i else None)
    if extra:
        notes["solids"] = (len(extra), solids)

    for raw in found.get("supports") or []:
        candidates = [i for i, (k, _b, _members) in enumerate(made)
                      if found["buildings"][k].get("ifc") == raw.get("ifc")
                      and found["buildings"][k].get("storey") == raw.get("storey")]
        member = _Pitch(raw, frame, float(raw.get("ground") or 0.0))
        host = min(candidates, key=lambda i: _polygon(out.buildings[i].footprint).distance(_polygon(member.ring))) \
            if candidates else None
        _offer_support(out, member, host, project, source_name or name)

    # A roof whose fall is not perpendicular to an outline edge cannot be reproduced by Roof's eave model.
    # Offer the actual IFC plane as an unfilled, independent placement area in the confirmed import plan.
    for host, (_k, b, members) in enumerate(made):
        reproduced = b.pitches()
        for member in members:
            if member.holes or not reproduced:
                continue
            nearest = min(range(len(reproduced)), key=lambda i: _angle(member.azimuth, reproduced[i].azimuth))
            # any pitch of the roof: two parallel planes at different levels both face the same way
            if any(abs(member.tilt - pitch.tilt) < 0.05
                   and (member.tilt == 0.0 or _angle(member.azimuth, pitch.azimuth) < 0.05)
                   and all(abs(member.z(x, y) - pitch.z(x, y)) < 0.01 for x, y in member.ring)
                   for pitch in reproduced):
                continue
            _offer_support(out, member, host, project, source_name or name, b.pitch_ref(nearest))

    # obstacles: on the building whose roof holds their middle, parapets of a flat roof as its parapet
    kinds: dict = {}
    for ring, top, k in small:
        middle = _polygon(ring).representative_point()
        mine = [(_polygon(b.footprint).distance(Point(middle.x, middle.y)), i) for i, (kk, b, _p) in enumerate(made)
                if kk == k]
        host = min(mine)[1] if mine else None
        if host is None:
            continue
        b, pitches = made[host][1], made[host][2]
        base = max((p.z(x, y) for x, y in ring for p in pitches if _near(p.ring, (x, y), 0.2)), default=b.height)
        e = model.ExclusionItem(id="", ring=ring, kind="other", building=None, height=round(max(0.0, top - base), 3))
        out.exclusions.append((e, host))
        out.moved_area += _polygon(ring).area
        kinds["other"] = kinds.get("other", 0) + 1
    for o in found.get("obstacles") or []:
        ring = frame.ring(o["ring"])
        if len(ring) < 3:
            continue
        middle = _polygon(ring).representative_point()
        host = None
        if o.get("building") is not None:
            # of the buildings made of the roof it stands on, the one under it, or the nearest
            mine = [(_polygon(b.footprint).distance(Point(middle.x, middle.y)), i) for i, (k, b, _p) in enumerate(made)
                    if k == o["building"]]
            host = min(mine)[1] if mine else None
        kind = o.get("kind") or "other"
        if host is not None:
            b, pitches = made[host][1], made[host][2]
            ground = float(found["buildings"][made[host][0]].get("ground") or 0.0)
            # above the highest point of the roof under it, as model.obstacle_prisms raises an exclusion
            base = max((p.z(x, y) for x, y in ring for p in pitches if _near(p.ring, (x, y), 0.2)),
                       default=b.height)
            height = max(0.0, float(o["z1"]) - ground - base)
            if height < 0.05 and kind != "skylight":
                continue                    # it rises over a lower roof beside it, not over the one that holds it
            if kind == "parapet":
                outline = _polygon(b.footprint).exterior
                if b.roof.type == "flat" and outline.distance(_polygon(ring)) <= PARAPET_BAND \
                        and _polygon(ring).buffer(0.05).intersects(outline.buffer(PARAPET_BAND)):
                    b.parapet = round(max(b.parapet, height), 3)
                    kinds["parapet"] = kinds.get("parapet", 0) + 1
                    continue
                kind = "other"
            e = model.ExclusionItem(id="", ring=ring, kind=EXCLUSION_KINDS.get(kind, "other"),
                                    building=None, height=round(height, 3))
            out.exclusions.append((e, host))
        elif kind == "tree":
            ground = float(found["buildings"][0].get("ground") or 0.0) if found.get("buildings") else 0.0
            e = model.ExclusionItem(id="", ring=ring, kind="tree", building=None,
                                    height=round(max(0.0, float(o["z1"]) - ground), 3))
            out.exclusions.append((e, None))
        else:
            continue
        kinds[e.kind] = kinds.get(e.kind, 0) + 1
    _summary(out, found, place, how, notes, kinds, made, project)
    out.reference = reference(found, place, frame, how, source_name)
    if shade in SHADE and shade != "off" and out.reference.get("context"):
        out.reference["shade"] = {"on": True, "reach": None if shade == "all" else float(shade)}
    if storeys is not None and out.reference.get("context"):
        # the elements of the storeys left out: neither the 3D nor the shadows take them (ifc_shade)
        keep = set(storeys)
        out.reference["context"]["skip"] = sorted(int(s["id"]) for s in unfiltered.get("solids") or []
                                                  if (s.get("storey") or "") not in keep)
    return out


def _area2(ring) -> float:
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1], strict=True))


def _small_body(group: list[_Pitch], others: list[_Pitch], k: int, small: list, notes: dict) -> None:
    """A piece too small to be a roof: what stands up from the roofs around it is an obstacle (a chimney's cap, and it
    casts its shadow); what does not (a balcony, a canopy) is left out and counted."""
    top = max(p.z(x, y) for p in group for x, y in p.ring)
    area = sum(p.area for p in group)
    near = [o for o in others if _polygon(o.ring).distance(_polygon(group[0].ring)) < 1.0]
    if near and all(top > max(o.z(x, y) for x, y in group[0].ring) + STEP for o in near):
        for p in group:
            small.append((p.ring, top, k))
        return
    notes["small_roofs"] = notes.get("small_roofs", 0) + 1
    notes["small_roofs_area"] = notes.get("small_roofs_area", 0.0) + area


def _offer_support(out: Plan, member: _Pitch, host, project, name: str, pitch=None) -> None:
    source = ", ".join(f"#{oid}" for oid in member.owners) or name
    if host is not None and pitch is None:
        b = out.buildings[host]
        pitches = b.pitches()
        if pitches:
            pitch = b.pitch_ref(min(range(len(pitches)), key=lambda i: _angle(member.azimuth, pitches[i].azimuth)))
    sf = model.SubField(id="", name=f"{name}: {source}", ring=member.ring,
                        pitch=pitch, module=next(iter(project.modules), "generic-450"),
                        params={"mounting": "coplanar"}, filled=False,
                        support=model.SupportPlane(enabled=True, tilt=member.tilt, azimuth=member.azimuth,
                                                   z0=member.pz, x0=member.px, y0=member.py))
    out.supports.append((sf, host))
    out.taken.append(_("Independent placement area from {file}, IFC {source}: normal ({nx}, {ny}, {nz}), "
                       "tilt {tilt}°, azimuth {azimuth}°, local elevation {z} m. Enabled, with no modules; "
                       "building and pitch retained as references.").format(
                           file=name, source=source, nx=number(member.n[0], 6), ny=number(member.n[1], 6),
                           nz=number(member.n[2], 6), tilt=number(member.tilt, 3),
                           azimuth=number(member.azimuth, 3), z=number(member.pz, 3)))


def _summary(out: Plan, found: dict, place: Place, how: str, notes: dict, kinds: dict, made: list, project) -> None:
    t, a, left = out.taken, out.approximated, out.left_out
    n = len(out.buildings)
    if notes.get("solids"):
        count, way = notes["solids"]
        a.append(ngettext("{n} body made of the model's solids, its outline in plan with its lowest and highest point "
                          "({way})", "{n} bodies made of the model's solids, their outlines in plan with their lowest "
                          "and highest points ({way})", count).format(
                              n=count, way=_("one for each group of the model") if way == "groups"
                              else _("one for each element")))
    over = (found.get("counts") or {}).get("solids_over")
    if over:
        left.append(_("{n} smaller bodies beyond the {m} largest: choose a zone or one body for each group").format(
            n=over, m=MAX_SOLIDS))
    if n:
        t.append(ngettext("{n} building: {names}", "{n} buildings: {names}", n).format(
            n=n, names=", ".join(b.name for b in out.buildings[:8]) + (", ..." if n > 8 else "")))
        types = {"flat": _("flat"), "mono": _("mono-pitch"), "gable": _("gable"), "hip": _("hip"),
                 "free": _("free pitches")}
        count: dict = {}
        for b in out.buildings:
            count[b.roof.type] = count.get(b.roof.type, 0) + 1
        t.append(_("Roofs: {list}").format(list=", ".join(f"{types[k]} {v}" for k, v in count.items())))
        pitches = sum(len(p) for _k, _b, p in made)
        t.append(ngettext("{n} roof plane", "{n} roof planes", pitches).format(n=pitches))
    elif not out.supports:
        contents = (found.get("counts") or {}).get("contents") or {}
        if contents.get("structure") or contents.get("plant"):
            left.append(_("No roof, slab or wall: this is a model of the structure or of the installations ({s} structural "
                          "elements, {p} components). The architectural model is what is needed.").format(
                              s=contents.get("structure", 0), p=contents.get("plant", 0)))
        else:
            left.append(_("No roof, slab or wall the buildings could be made of."))
    names = {"chimney": _("chimneys"), "skylight": _("skylights"), "tree": _("trees"), "vent": _("smoke vents"),
             "plant": _("roof plants"), "other": _("other obstacles"), "parapet": _("parapet walls")}
    if kinds:
        t.append(_("On the roofs: {list}").format(list=", ".join(f"{names.get(k, k)} {v}" for k, v in kinds.items())))
    angle = number(place.angle, 1)
    source = _("the map") if place.north == "map" and place.north_map is not None else _("the TrueNorth")
    if how == "origin":
        t.append(_("The buildings at the middle of the project's plan, the project's site unchanged: move and turn them "
                   "on the plan where they belong."))
    elif how == "site" and out.site is not None:
        t.append(_("The project's site moved to the model's place: {lat}, {lon}.").format(
            lat=number(out.site.lat, 6), lon=number(out.site.lon, 6)))
    else:
        t.append(_("The buildings where the file places them, around the project's site."))
    if place.reliable():
        where = {"map": _("its map conversion ({crs})").format(crs=place.crs),
                 "site": _("the site's latitude and longitude ({name})").format(name=place.site_name)}[place.source]
        t.append(_("The file places the model by {where}; north {angle}° from the model's Y axis, from {source}.").format(
            where=where, angle=angle, source=source))
    else:
        a.append(_("North {angle}° from the model's Y axis, from {source}: the file has no place to back it, check it "
                   "against the map.").format(angle=angle, source=source))
    if found.get("address"):
        t.append(_("The file gives the address: {address}").format(address=found["address"]))
    a += place.notes
    if notes.get("slope"):
        a.append(_("Some planes fall towards no side of their outline: their slope runs towards the nearest side "
                   "(up to {deg}° off).").format(deg=number(notes["slope"], 1)))
    if notes.get("holes"):
        a.append(ngettext("{n} hole in a roof plane left out (courtyards and openings are not in Meridiana yet)",
                          "{n} holes in roof planes left out (courtyards and openings are not in Meridiana yet)",
                          notes["holes"]).format(n=notes["holes"]))
    if notes.get("raised"):
        a.append(ngettext("{n} body stands on another part, from {h} m: it comes in with its walls from that height "
                          "(its base), on the body under it",
                          "{n} bodies stand on other parts, from {h} m: they come in with their walls from those heights "
                          "(their bases), on the bodies under them", len(notes["raised"])).format(
                              n=len(notes["raised"]), h=", ".join(number(h, 1) for h in sorted(set(notes["raised"]))[:4])))
    if notes.get("terraces"):
        a.append(ngettext("{n} body from slabs under the open sky, which the model does not call a roof (a stair tower's "
                          "top, a terrace): check it",
                          "{n} bodies from slabs under the open sky, which the model does not call roofs (stair towers' "
                          "tops, terraces): check them", notes["terraces"]).format(n=notes["terraces"]))
    if notes.get("boxes"):
        a.append(_("Buildings from their walls alone: outline and height, the roof flat."))
    if notes.get("low"):
        a.append(_("Roofs at the ground or below it: their height set to 10 cm, check the ground of the model."))
    c = found.get("counts") or {}
    if notes.get("small_roofs"):
        left.append(ngettext("{n} small roof at a height of its own, a balcony or a canopy ({area} m2)",
                             "{n} small roofs at heights of their own, balconies or canopies ({area} m2)",
                             notes["small_roofs"]).format(n=notes["small_roofs"],
                                                          area=number(notes["small_roofs_area"], 1)))
    if c.get("small_faces"):
        left.append(ngettext("{n} roof surface too small or narrow for a module ({area} m2)",
                             "{n} roof surfaces too small or narrow for a module ({area} m2)",
                             c["small_faces"]).format(n=c["small_faces"], area=number(c.get("small_area", 0.0), 1)))
    if c.get("modules"):
        left.append(ngettext("{n} solar module already in the model: Meridiana lays its own",
                             "{n} solar modules already in the model: Meridiana lays their own",
                             c["modules"]).format(n=c["modules"]))
    if c.get("off_roof"):
        left.append(ngettext("{n} element not on a roof", "{n} elements not on a roof", c["off_roof"]).format(
            n=c["off_roof"]))
    if c.get("fine_faces"):
        a.append(_("Very finely modelled roofs: the planes come from their largest faces, {n} smaller ones not looked at. "
                   "Check them.").format(n=c["fine_faces"]))
    if c.get("obstacles_failed"):
        left.append(_("What stands on the roofs could not be read on this model: they come in without obstacles."))
    if c.get("over_budget"):
        left.append(ngettext("{n} element left out because the model takes too long: the roofs are read, what stands on "
                             "them may be missing",
                             "{n} elements left out because the model takes too long: the roofs are read, what stands on "
                             "them may be missing", c["over_budget"]).format(n=c["over_budget"]))
    if c.get("skipped"):
        left.append(ngettext("{n} element left out: its shape needs IfcOpenShell's iterator, which stopped on this file",
                             "{n} elements left out: their shapes need IfcOpenShell's iterator, which stopped on this "
                             "file", c["skipped"]).format(n=c["skipped"]))
    if c.get("balconies"):
        left.append(ngettext("{n} slab under the open sky with no walls under it, a balcony or a canopy",
                             "{n} slabs under the open sky with no walls under them, balconies or canopies",
                             c["balconies"]).format(n=c["balconies"]))
    if c.get("walls_outside"):
        left.append(ngettext("{n} wall stands outside the roofs: a part of the building the model gives no roof to",
                             "{n} walls stand outside the roofs: parts of the building the model gives no roof to",
                             c["walls_outside"]).format(n=c["walls_outside"]))
    if c.get("errors"):
        left.append(ngettext("{n} element whose shape could not be made", "{n} elements whose shape could not be made",
                             c["errors"]).format(n=c["errors"]))


# R400: the solids of a model (ifc_scan), the simple way: of each body its outline in plan and its heights

SOLID_WAYS = ("none", "groups", "elements")
SOLID_KINDS = ("all", "building", "plant")
BUILDING_CLASSES = {"IfcWall", "IfcWallStandardCase", "IfcWallElementedCase", "IfcSlab", "IfcSlabStandardCase",
                    "IfcSlabElementedCase", "IfcRoof", "IfcCovering", "IfcColumn", "IfcColumnStandardCase", "IfcBeam",
                    "IfcBeamStandardCase", "IfcStair", "IfcStairFlight", "IfcRamp", "IfcRampFlight", "IfcRailing",
                    "IfcWindow", "IfcWindowStandardCase", "IfcDoor", "IfcDoorStandardCase", "IfcCurtainWall",
                    "IfcPlate", "IfcPlateStandardCase", "IfcMember", "IfcMemberStandardCase", "IfcFooting", "IfcPile",
                    "IfcBuildingElementPart", "IfcChimney", "IfcShadingDevice"}
FURNITURE = {"IfcFurnishingElement", "IfcFurniture", "IfcSystemFurnitureElement"}
SOLID_MIN_HEIGHT = 0.2          # m: a top lower than this above the ground is a curb, no shadow worth a body
SOLID_THIN = 0.12               # m: the least thickness of a body
SOLID_MIN_AREA = 0.05           # m2 in plan
SOLID_JOIN = 0.05               # m: the elements of a group closer than this are one outline
SOLID_SIMPLIFY = 0.05           # m
MAX_SOLIDS = 3000               # bodies at most from one import: the largest kept, the others said


SHADE = ("off", "20", "50", "all")     # r22-ifc: the import window's choice for ifc_shade (metres around a sub-field)


def storeys_of(found: dict) -> list[str]:
    """The storeys of a read model (r22-ifc), for the window's choice: by their elevation as the scan lists them, then
    the others the elements name; "" last when some element is on none."""
    listed = sorted(((s.get("z") if s.get("z") is not None else math.inf, s.get("name") or "")
                     for s in (found.get("listing") or {}).get("storeys") or []), key=lambda zn: zn[0])
    out = list(dict.fromkeys(n for _z, n in listed if n))
    loose = False
    for group in ("buildings", "solids", "supports"):
        for x in found.get(group) or []:
            name = x.get("storey") or ""
            if name and name not in out:
                out.append(name)
            loose = loose or not name
    return out + ([""] if loose and out else [])


def by_storeys(found: dict, keep) -> dict:
    """`found` with only what stands on the storeys `keep` (names, "" for what is on none): the roofs read through
    IfcOpenShell, their obstacles (renumbered), the placement surfaces, the scan's solids; None keeps everything."""
    if keep is None:
        return found
    keep = set(keep)
    buildings = found.get("buildings") or []
    kept = [i for i, b in enumerate(buildings) if (b.get("storey") or "") in keep]
    renumber = {old: new for new, old in enumerate(kept)}
    obstacles = []
    for o in found.get("obstacles") or []:
        if o.get("building") is not None:
            if o["building"] not in renumber:
                continue
            o = {**o, "building": renumber[o["building"]]}
        elif "storey" in o and (o.get("storey") or "") not in keep:
            continue
        obstacles.append(o)
    return {**found, "buildings": [buildings[i] for i in kept], "obstacles": obstacles,
            "supports": [s for s in found.get("supports") or [] if (s.get("storey") or "") in keep],
            "solids": [s for s in found.get("solids") or [] if (s.get("storey") or "") in keep]}


def default_solids(found: dict) -> str:
    """The way proposed: the solids by group when the model has no roof Meridiana reads (a plant, a layout of
    machines), none when it has buildings with roofs (they come in as before)."""
    return "groups" if found.get("solids") and not found.get("buildings") else "none"


def _kind_ok(cls: str, kinds: str) -> bool:
    if kinds == "building":
        return cls in BUILDING_CLASSES
    if kinds == "plant":
        return cls not in BUILDING_CLASSES and cls not in FURNITURE
    return True


def solid_raws(found: dict, way: str, kinds: str = "all", zone: tuple | None = None, frame=None) -> tuple[list, list]:
    """The solids of `found["solids"]` (ifc_worker, from ifc_scan) as raw buildings of ifc_read's kind: an outline, a
    flat top at the highest point, a base at the lowest (above the model's ground, `solids_ground`). `way`: "groups"
    the outline of the elements of each group of the model (an assembly, a skid), one body for each piece apart, the
    pieces parts of the first ("whole", an index in the list); "elements" one body for each element. `zone`: (x0, y0,
    x1, y1) in the plan (`frame`): only what has its middle inside. Also the plan rings of what the zone left out."""
    import shapely
    from shapely.geometry.polygon import orient
    from shapely.strtree import STRtree
    items = [s for s in found.get("solids") or [] if _kind_ok(s.get("cls", ""), kinds) and len(s.get("hull") or []) >= 3]
    if way not in ("groups", "elements") or not items:
        return [], []
    ground = float(found.get("solids_ground") or 0.0)
    zoned: list = []
    if zone is not None and frame is not None:
        x0, y0, x1, y1 = min(zone[0], zone[2]), min(zone[1], zone[3]), max(zone[0], zone[2]), max(zone[1], zone[3])
        kept = []
        for s in items:
            xs = [q[0] for q in s["hull"]]
            ys = [q[1] for q in s["hull"]]
            cx, cy = frame.point((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
            (kept if x0 <= cx <= x1 and y0 <= cy <= y1 else zoned).append(s)
        items = kept
        zoned = [frame.ring(s["hull"]) for s in zoned[:2000]]

    def body(ring, z0, z1, name, storey, members):
        base = max(0.0, z0 - ground)
        top = z1 - ground
        if top < SOLID_MIN_HEIGHT:
            return None
        # a thin body (a pipe, a plate) stands SOLID_THIN thick under its top, so that its base holds (apply: a base
        # under the top by more than 0.1 m)
        base = max(0.0, min(base, top - SOLID_THIN))
        flat = {"ring": ring, "normal": [0.0, 0.0, 1.0], "point": [ring[0][0], ring[0][1], z1],
                "area": float(_polygon(ring).area), "holes": 0, "owners": members, "base": ground + base,
                "base_from": "solid"}
        return {"name": name, "ifc": "", "ground": ground, "ground_storey": "", "source": "solid",
                "footprint": ring, "pitches": [flat], "storey": storey}
    out: list = []
    if way == "elements":
        for s in items:
            b = body([list(q) for q in s["hull"]], s["z0"], s["z1"], s.get("name") or s.get("cls", ""),
                     s.get("storey", ""), [s["id"]])
            if b is not None and abs(_area2(b["footprint"])) / 2 >= SOLID_MIN_AREA:
                out.append(b)
    else:
        groups: dict = {}
        for s in items:
            groups.setdefault(s.get("group"), []).append(s)
        for members in groups.values():
            polys = [shapely.Polygon(s["hull"]) for s in members]
            union = shapely.union_all([p.buffer(SOLID_JOIN) for p in polys if p.is_valid]).buffer(-SOLID_JOIN)
            pieces = [g for g in getattr(union, "geoms", [union]) if g.geom_type == "Polygon" and g.area >= SOLID_MIN_AREA]
            tree = STRtree(polys)
            first = None
            name = members[0].get("gname") or members[0].get("name") or members[0].get("cls", "")
            for piece in sorted(pieces, key=lambda g: -g.area):
                inside = [members[int(i)] for i in tree.query(piece, predicate="intersects")]
                if not inside:
                    continue
                simple = piece.simplify(SOLID_SIMPLIFY)
                if simple.geom_type != "Polygon" or simple.area < SOLID_MIN_AREA:
                    simple = piece
                ring = [[round(x, 3), round(y, 3)] for x, y in list(orient(simple).exterior.coords)[:-1]]
                b = body(ring, min(s["z0"] for s in inside), max(s["z1"] for s in inside), name,
                         inside[0].get("storey", ""), [s["id"] for s in inside])
                if b is None:
                    continue
                if first is None:
                    first = len(out)
                else:
                    b["whole"] = first
                out.append(b)
    if len(out) > MAX_SOLIDS:
        weight = [b["pitches"][0]["area"] * (b["pitches"][0]["point"][2] - b["pitches"][0]["base"]) for b in out]
        keep = sorted(sorted(range(len(out)), key=lambda i: -weight[i])[:MAX_SOLIDS])
        renum = {old: new for new, old in enumerate(keep)}
        found.setdefault("counts", {})["solids_over"] = len(out) - MAX_SOLIDS
        out = [out[i] for i in keep]
        for b in out:
            if "whole" in b:
                b["whole"] = renum.get(b["whole"])
                if b["whole"] is None:
                    del b["whole"]
    return out, zoned


def apply(project: model.Project, p: Plan) -> list[str]:
    """Add the plan to the project (inside the window's edit: one undo step); the ids of the new buildings."""
    if p.site is not None:
        project.site = model.Site(lat=p.site.lat, lon=p.site.lon, address=p.site.address)
    ids = []
    # the bodies of one model are placed together: moved and turned as one on the plan (move.members)
    group = ""
    if len(p.buildings) > 1:
        taken = {b.group for b in project.buildings}
        group = next(f"ifc{n}" for n in range(1, len(taken) + 2) if f"ifc{n}" not in taken)
    from shapely.geometry import Polygon
    bases = p.bases if len(p.bases) == len(p.buildings) else [{} for _b in p.buildings]
    from shapely.strtree import STRtree
    tree = outlines = None
    for b, where in zip(p.buildings, bases, strict=True):
        new = model.Building(id=project.new_id("b"), name=b.name, footprint=[list(q) for q in b.footprint],
                             height=b.height, roof=model.Roof(**{**b.roof.__dict__}), parapet=b.parapet, group=group)
        new.roof.free_pitches = [{**f, "ring": [list(q) for q in f["ring"]]} for f in b.roof.free_pitches]
        new.roof.edges = list(b.roof.edges)
        # R453 (format 28): a body whose walls start above the ground stands at that height, on the body of the
        # model under its middle when there is one (R352: Building.on); a body on the ground from the ground
        base = where.get("base")
        if base is not None and base > RAISED and base < b.wall_top() - 0.1:
            new.base = round(float(base), 3)
            middle = Polygon(new.footprint).representative_point()
            if tree is None:            # R400: the outlines once, in a tree (800 bodies of a plant took 8 s one by one)
                outlines = [Polygon(other.footprint).buffer(1e-6) for other in p.buildings]
                tree = STRtree(outlines)
            near = sorted(int(k) for k in tree.query(middle))
            hosts = [(p.buildings[k], k) for k in near if p.buildings[k] is not b and
                     (bases[k].get("base") or 0.0) < base and outlines[k].contains(middle)]
            if hosts:
                new.on = f"host:{hosts[0][1]}"      # the id of that body, once it has one (below)
        project.buildings.append(new)
        ids.append(new.id)
    for new in project.buildings[-len(ids):] if ids else []:
        if new.on.startswith("host:"):
            new.on = ids[int(new.on[5:])]
    # R400: the pieces of one group of the model are parts of its first body (R440: Building.part_of)
    for i, whole in enumerate(p.parts if len(p.parts) == len(ids) else []):
        if whole is not None:
            project.buildings[-len(ids) + i].part_of = ids[whole]
    if ids and p.reference:
        # R453: the model's frame, with the buildings as they were laid: an export finds them again, moved or not
        first = project.buildings[-len(ids)]
        grounds = p.grounds if len(p.grounds) == len(ids) else [0.0] * len(ids)
        project.resources = {**(project.resources or {}), "ifc_reference": {
            **p.reference, "buildings": {i: float(g) for i, g in zip(ids, grounds, strict=True)},
            "anchor": {"building": first.id, "footprint": [list(q) for q in first.footprint]}}}
    for e, host in p.exclusions:
        project.exclusions.append(model.ExclusionItem(id=project.new_id("e"), ring=[list(q) for q in e.ring],
                                                      kind=e.kind, building=ids[host] if host is not None else None,
                                                      height=e.height))
    for sf, host in p.supports:
        project.subfields.append(model.SubField(id=project.new_id("s"), name=sf.name,
                                                ring=[list(q) for q in sf.ring],
                                                building=ids[host] if host is not None else None, pitch=sf.pitch,
                                                module=sf.module, params=dict(sf.params), filled=False,
                                                support=replace(sf.support)))
    return ids


def problem(p: Plan) -> str:
    """What keeps the plan from being added, in words: a building beyond the plan's limits (a place read wrong)."""
    for b in p.buildings:
        if any(abs(c) > model.COORD_LIMIT for q in b.footprint for c in q):
            return _("The buildings would fall more than {km} km from the site: place them at the site's origin, or "
                     "move the site to the model.").format(km=number(model.COORD_LIMIT / 1000, 0))
        if b.height > model.HEIGHT_LIMIT:
            return _("A roof would stand {m} m high: the model's ground was not found.").format(m=number(b.height, 0))
    for sf, _host in p.supports:
        if any(not math.isfinite(c) or abs(c) > model.COORD_LIMIT for q in sf.ring for c in q):
            return _("The buildings would fall more than {km} km from the site: place them at the site's origin, or "
                     "move the site to the model.").format(km=number(model.COORD_LIMIT / 1000, 0))
        if not math.isfinite(sf.support.z0) or abs(sf.support.z0) > model.HEIGHT_LIMIT:
            return _("A roof would stand {m} m high: the model's ground was not found.").format(
                m=number(sf.support.z0, 0))
    return ""
