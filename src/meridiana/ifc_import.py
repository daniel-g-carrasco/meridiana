"""What ifc_read found in an IFC model, made Meridiana's: buildings with their roofs and the exclusions on them, placed
around the project's site, as one change the designer can undo (study 20, section 6). Without Qt.

Where the model goes (`placing`):
- the model's place: from its IfcMapConversion when its coordinate system is a UTM one Meridiana converts (study 15:
  the map wins over the latitude and longitude, which FreeCAD truncates to the second), else from the IfcSite's
  RefLatitude and RefLongitude (at the site's placement), else none;
- the north: the map's (the model's X axis in the grid, and the meridian's convergence) when there is a map, else the
  context's TrueNorth; when both are there and differ by more than a degree, the designer chooses;
- three ways (`HOW`): "file", the model where the file says, around the project's site; "site", the project's site moved
  to the model's place; "origin", the model's buildings centred on the site's origin (the only way without a place).

The roofs (`plan`): a flat roof is a flat building; one plane a mono-pitch; planes of one slope and one eave height that
the straight skeleton of the outline makes again (roofs.pitched) a gable or a hip roof with its sides; anything else
free pitches, each with the side nearest to its fall as its eave. Heights are above the building's ground (the storey
at its zero, ifc_read.Structure.ground). Parapets along a flat roof's outline become its parapet; the other obstacles
exclusions with their height above the roof."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import geo, model, roofs, skeleton
from .i18n import _, ngettext, number

HOW = ("file", "site", "origin")
FAR_KM = 5.0                    # beyond this the site is better moved to the model than the model to the site
FLAT = 0.5                      # degrees: a plane flatter than this is flat
SAME_TILT = 1.0                 # degrees: pitches of one roof
SAME_EAVE = 0.10                # m
LEVEL = 0.30                    # m: flat planes closer than this are one roof (a covering, a curb), farther two
SMALL_ROOF = 8.0                # m2: a roof at a height of its own smaller than this (a balcony, a canopy) is left out
PARAPET_BAND = 0.6              # m from the outline: a wall there is the parapet
EXCLUSION_KINDS = {"chimney": "chimney", "skylight": "skylight", "tree": "tree", "vent": "vent", "plant": "plant"}


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

    @property
    def angle(self) -> float:
        return self.north_map if self.north == "map" and self.north_map is not None else self.north_context

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
        if utm is not None:
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
    if out.disagree():
        out.notes.append(_("The model's TrueNorth says {a}°, its map conversion {b}°: check where north is.").format(
            a=number(out.north_context, 1), b=number(out.north_map, 1)))
    return out


def distance_km(place: Place, site: model.Site) -> float | None:
    if place.lat is None:
        return None
    x, y = geo.Origin(site.lat, site.lon).to_local(place.lon, place.lat)
    return math.hypot(x, y) / 1000.0


def default_how(place: Place, project: model.Project) -> str:
    """"file" when the model has a place near the project's site; "site" when it is far, or when the project has
    nothing on its map yet; "origin" without a place."""
    if place.lat is None:
        return "origin"
    km = distance_km(place, project.site)
    if not project.buildings and not project.subfields and (km is None or km > 0.05):
        return "site"
    return "site" if km is not None and km > FAR_KM else "file"


class Frame:
    """From the model's world metres to the project's plan: turned to the true north, then moved."""

    def __init__(self, found: dict, place: Place, how: str, site: model.Site):
        self.theta = math.radians(place.angle)
        self.c, self.s = math.cos(-self.theta), math.sin(-self.theta)
        self.ox, self.oy = place.origin
        self.dx = self.dy = 0.0
        if how == "file" and place.lat is not None:
            self.dx, self.dy = geo.Origin(site.lat, site.lon).to_local(place.lon, place.lat)
        elif how == "origin":
            pts = [self.turn(x, y) for b in found.get("buildings") or [] for x, y in b["footprint"]]
            if pts:
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                self.dx, self.dy = -(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2

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
    site: model.Site | None = None
    taken: list = field(default_factory=list)
    approximated: list = field(default_factory=list)
    left_out: list = field(default_factory=list)


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
    from shapely.geometry import Polygon
    p = Polygon(ring).representative_point()
    return p.x, p.y


def _matches(found: list[_Pitch], made: list[roofs.Pitch]) -> bool:
    """The planes a roof type makes are the planes of the model: as many, each facing as one of them (2 degrees)
    with its area (5 %, and 0,5 m2)."""
    if len(found) != len(made):
        return False
    from shapely.geometry import Polygon
    free = list(found)
    for p in made:
        area = Polygon(p.ring).area
        hit = next((f for f in free if _angle(f.azimuth, p.azimuth) < 2.0
                    and abs(Polygon(f.ring).area - area) <= max(0.05 * area, 0.5)), None)
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
    return min(f["eave"] for f in free), model.Roof(type="free", free_pitches=free)


def _near(ring, point, tol: float = 0.05) -> bool:
    from shapely.geometry import Point, Polygon
    return Polygon(ring).buffer(tol).contains(Point(point))


def _levels(pitches: list[_Pitch]) -> list[list[_Pitch]]:
    """A roof all flat but at several heights: one group for each height, the heights within LEVEL of the lowest of
    the group together (Esplanades: the sheets of a roof 2 cm apart are one roof, the stair tower 0,9 m above it
    another), each a building."""
    out: list = []
    for p in sorted(pitches, key=lambda q: q.pz):
        if out and p.pz - out[-1][0].pz < LEVEL:
            out[-1].append(p)
        else:
            out.append([p])
    return out


def plan(found: dict, project: model.Project, how: str = "file", north: str | None = None,
         name: str = "IFC") -> Plan:
    """The buildings and the exclusions of `found` (ifc_read.read) for `project`, placed the way `how` says, with the
    north `north` ("map" or "context"; None: the map's when there is one). Nothing of the project is changed."""
    from shapely.geometry import Point, Polygon
    place = place_of(found)
    if north in ("map", "context") and (north == "context" or place.north_map is not None):
        place.north = north
    if how not in HOW or (how != "origin" and place.lat is None):
        how = "origin"
    out = Plan()
    site = project.site
    if how == "site":
        site = model.Site(lat=round(place.lat, 7), lon=round(place.lon, 7), address=project.site.address)
        out.site = site
    frame = Frame(found, place, how, site)
    notes: dict = {}
    made: list = []                 # (index in found["buildings"], model.Building, its pitches)
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
        groups = [pitches]
        if all(p.tilt == 0.0 for p in pitches):
            groups = _levels(pitches)
        for group in groups:
            if len(groups) > 1:
                import shapely
                union = shapely.union_all([Polygon(p.ring).buffer(0.05) for p in group]).buffer(-0.05)
                parts = [g for g in getattr(union, "geoms", [union]) if g.geom_type == "Polygon" and g.area > 0.5]
                small = [g for g in parts if g.area < SMALL_ROOF]
                if small:
                    notes["small_roofs"] = notes.get("small_roofs", 0) + len(small)
                    notes["small_roofs_area"] = notes.get("small_roofs_area", 0.0) + sum(g.area for g in small)
                    parts = [g for g in parts if g.area >= SMALL_ROOF]
            else:
                parts = [None]
            for part in parts:
                if part is None:
                    footprint = frame.ring(raw["footprint"])
                    members = group
                else:
                    footprint = [[round(x, 4), round(y, 4)] for x, y in list(part.simplify(0.02).exterior.coords)[:-1]]
                    members = [p for p in group if Polygon(p.ring).intersects(part)]
                if len(footprint) < 3:
                    continue
                eave, roof = _roof(footprint, members, notes)
                label = ((raw.get("storey") if raw.get("ifc") in storey_names else raw.get("name"))
                         or raw.get("storey") or name)
                if raw.get("source") == "boxes":
                    notes["boxes"] = notes.get("boxes", 0) + 1
                names[label] = names.get(label, 0) + 1
                b = model.Building(id="", name=label, footprint=footprint, height=round(max(eave, 0.1), 3), roof=roof)
                if eave < 0.1:
                    notes["low"] = notes.get("low", 0) + 1
                notes["holes"] = notes.get("holes", 0) + sum(p.holes for p in members)
                made.append((k, b, members))
    # «Name», «Name 2»... when one name is several buildings
    seen: dict = {}
    for _k, b, _p in made:
        if names[b.name] > 1:
            seen[b.name] = seen.get(b.name, 0) + 1
            if seen[b.name] > 1:
                b.name = f"{b.name} {seen[b.name]}"
    out.buildings = [b for _k, b, _p in made]

    # obstacles: on the building whose roof holds their middle, parapets of a flat roof as its parapet
    kinds: dict = {}
    for o in found.get("obstacles") or []:
        ring = frame.ring(o["ring"])
        if len(ring) < 3:
            continue
        middle = Polygon(ring).representative_point()
        host = None
        if o.get("building") is not None:
            # of the buildings made of the roof it stands on, the one under it, or the nearest
            mine = [(Polygon(b.footprint).distance(Point(middle.x, middle.y)), i) for i, (k, b, _p) in enumerate(made)
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
            if kind == "parapet":
                outline = Polygon(b.footprint).exterior
                if b.roof.type == "flat" and outline.distance(Polygon(ring)) <= PARAPET_BAND \
                        and Polygon(ring).buffer(0.05).intersects(outline.buffer(PARAPET_BAND)):
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
    return out


def _summary(out: Plan, found: dict, place: Place, how: str, notes: dict, kinds: dict, made: list, project) -> None:
    t, a, left = out.taken, out.approximated, out.left_out
    n = len(out.buildings)
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
    else:
        left.append(_("No roof, slab or wall the buildings could be made of."))
    names = {"chimney": _("chimneys"), "skylight": _("skylights"), "tree": _("trees"), "vent": _("smoke vents"),
             "plant": _("roof plants"), "other": _("other obstacles"), "parapet": _("parapet walls")}
    if kinds:
        t.append(_("On the roofs: {list}").format(list=", ".join(f"{names.get(k, k)} {v}" for k, v in kinds.items())))
    where = {"map": _("its map conversion ({crs})").format(crs=place.crs), "site": _("the site's latitude and longitude"),
             "none": _("nowhere: the file has no georeferencing")}[place.source]
    t.append(_("The model's place from {where}; north {angle}° from the model's Y axis, from {source}.").format(
        where=where, angle=number(place.angle, 1),
        source=_("the map") if place.north == "map" and place.north_map is not None else _("the TrueNorth")))
    if how == "site" and out.site is not None:
        t.append(_("The project's site moved to the model's place: {lat}, {lon}.").format(
            lat=number(out.site.lat, 6), lon=number(out.site.lon, 6)))
    elif how == "origin":
        t.append(_("The buildings centred on the site's origin: move them where they belong (M)."))
    a += place.notes
    if notes.get("slope"):
        a.append(_("Some planes fall towards no side of their outline: their slope runs towards the nearest side "
                   "(up to {deg}° off).").format(deg=number(notes["slope"], 1)))
    if notes.get("holes"):
        a.append(ngettext("{n} hole in a roof plane left out (courtyards and openings are not in Meridiana yet)",
                          "{n} holes in roof planes left out (courtyards and openings are not in Meridiana yet)",
                          notes["holes"]).format(n=notes["holes"]))
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
    if c.get("skipped"):
        left.append(ngettext("{n} element left out: its shape needs IfcOpenShell's iterator, which stopped on this file",
                             "{n} elements left out: their shapes need IfcOpenShell's iterator, which stopped on this "
                             "file", c["skipped"]).format(n=c["skipped"]))
    if c.get("errors"):
        left.append(ngettext("{n} element whose shape could not be made", "{n} elements whose shape could not be made",
                             c["errors"]).format(n=c["errors"]))


def apply(project: model.Project, p: Plan) -> list[str]:
    """Add the plan to the project (inside the window's edit: one undo step); the ids of the new buildings."""
    if p.site is not None:
        project.site = model.Site(lat=p.site.lat, lon=p.site.lon, address=p.site.address)
    ids = []
    for b in p.buildings:
        new = model.Building(id=project.new_id("b"), name=b.name, footprint=[list(q) for q in b.footprint],
                             height=b.height, roof=model.Roof(**{**b.roof.__dict__}), parapet=b.parapet)
        new.roof.free_pitches = [{**f, "ring": [list(q) for q in f["ring"]]} for f in b.roof.free_pitches]
        new.roof.edges = list(b.roof.edges)
        project.buildings.append(new)
        ids.append(new.id)
    for e, host in p.exclusions:
        project.exclusions.append(model.ExclusionItem(id=project.new_id("e"), ring=[list(q) for q in e.ring],
                                                      kind=e.kind, building=ids[host] if host is not None else None,
                                                      height=e.height))
    return ids


def problem(p: Plan) -> str:
    """What keeps the plan from being added, in words: a building beyond the plan's limits (a place read wrong)."""
    for b in p.buildings:
        if any(abs(c) > model.COORD_LIMIT for q in b.footprint for c in q):
            return _("The buildings would fall more than {km} km from the site: place them at the site's origin, or "
                     "move the site to the model.").format(km=number(model.COORD_LIMIT / 1000, 0))
        if b.height > model.HEIGHT_LIMIT:
            return _("A roof would stand {m} m high: the model's ground was not found.").format(m=number(b.height, 0))
    return ""
