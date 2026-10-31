"""The project as an IFC4 model (study 15, 5.2; the prototype of 22/10/2026 that FreeCAD 1.1.4 opens), for the architect,
the BIM coordinator, a colleague with FreeCAD or BlenderBIM. Without Qt; the window runs it in a job with its bar.

What the file holds:
- IfcProject in metres, degrees and watts; the Model context with its TrueNorth (+Y: Meridiana's frame is the true
  north's);
- IfcSite with RefLatitude and RefLongitude to the millionth of a second (FreeCAD truncates to the second: 30 m) and,
  unless asked not to, an IfcMapConversion to WGS 84 / UTM of the site's zone with the meridian's convergence;
- one IfcBuilding with a storey for each building: its walls (each side of the outline up to the roof, 30 cm inwards),
  IfcRoof with an IfcSlab ROOF for each pitch (20 cm under the pitch's plane), the parapets IfcWall PARAPET;
- the obstacles: IfcChimney, IfcWindow SKYLIGHT, IfcGeographicElement (trees), IfcBuildingElementProxy (the rest);
- the modules: an IfcSolarDeviceType SOLARPANEL for each module and orientation, with its shape once
  (IfcRepresentationMap), one IfcSolarDevice for each module laid, placed by an IfcMappedItem, with its Pset; an
  IfcGroup for each sub-field and for each string.

The property sets keep the names of the prototype that FreeCAD read (study 15, 5.2): Meridiana_Edificio, Meridiana_Falda,
Meridiana_Ostacolo, Meridiana_DatiModulo, Meridiana_Modulo, Meridiana_Sottocampo, Meridiana_Stringa; the azimuth both by
CEI 82-25 (from the south, west positive) and from the north. ifcopenshell (LGPL-3.0-or-later) is imported only here and
only when exporting: without it the program runs and says what is missing.

The modules are written as entities directly, not through ifcopenshell.api: about 25 entities each. On 25 sheds with
2.900 modules the export takes about 3 s, the whole run 3,5 s against 11,3 s of the prototype that called the api for
each module (study 20, 6). The file is written next to the target and renamed when whole: a stop half way leaves the
old file as it was."""

from __future__ import annotations

import math
import os
import json
import uuid
from collections.abc import Callable
from pathlib import Path

import numpy as np

from . import geo, mesh

SLAB = 0.20                     # m under the pitch
WALL = 0.30                     # m inwards
ROOF_KINDS = {"flat": "FLAT_ROOF", "gable": "GABLE_ROOF", "hip": "HIP_ROOF", "mono": "SHED_ROOF", "free": "FREEFORM"}
OBSTACLES = {"parapet": ("IfcWall", "PARAPET", None),
             "chimney": ("IfcChimney", "NOTDEFINED", None),
             "skylight": ("IfcWindow", "SKYLIGHT", None),
             "tree": ("IfcGeographicElement", "USERDEFINED", "Albero"),
             "vent": ("IfcBuildingElementProxy", "USERDEFINED", "Evacuatore di fumo e calore"),
             "plant": ("IfcBuildingElementProxy", "USERDEFINED", "Impianto in copertura"),
             "other": ("IfcBuildingElementProxy", "USERDEFINED", "Ostacolo"),
             # R281: a canopy's structure (canopies.structure), indicative sizes
             "column": ("IfcColumn", "COLUMN", None),
             "beam": ("IfcBeam", "BEAM", None)}
CANOPY_SLAB = 0.05              # m, a canopy's roof sheet: it lies on the beams
MODULE_THICKNESS = 0.035        # m, when the module's record does not say


class Interrupted(Exception):
    """The designer stopped the export: nothing written."""


def dms(degrees: float) -> tuple[int, int, int, int]:
    """Decimal degrees as an IfcCompoundPlaneAngleMeasure: degrees, minutes, seconds, millionths of a second, all of the
    sign of the angle (IFC4, 8.11.3.1)."""
    sign = -1 if degrees < 0 else 1
    us = round(abs(degrees) * 3_600_000_000)
    d, us = divmod(us, 3_600_000_000)
    m, us = divmod(us, 60_000_000)
    s, us = divmod(us, 1_000_000)
    return sign * d, sign * m, sign * s, sign * us


class Writer:
    """One export: the file in the making and its parts. `strings` maps (sub-field id, module key) to the label of
    the module's string («1.2.3», plant.String.label)."""

    def __init__(self, project, results: dict, strings: dict | None = None, map_conversion: bool = True,
                 progress: Callable[[float, str], None] | None = None):
        import ifcopenshell
        import ifcopenshell.api
        import ifcopenshell.guid
        self.ios = ifcopenshell
        self.api = ifcopenshell.api
        self.guid = ifcopenshell.guid.new
        self.namespace = uuid.UUID(project.bim_id)
        self.p = project
        self.results = {k: v for k, v in (results or {}).items() if not isinstance(v, Exception)}
        self.strings = strings or {}
        self.map_conversion = map_conversion
        self.tell = progress or (lambda _f, _w: None)
        self.f = ifcopenshell.api.run("project.create_file", version="IFC4")
        self.counts: dict[str, int] = {}
        self.storeys: dict = {}
        self.contained: dict = {}

    def stable(self, *key) -> str:
        return self.ios.guid.compress(uuid.uuid5(self.namespace, json.dumps(key, ensure_ascii=False)).hex)

    # small things

    def point2(self, x, y):
        return self.f.createIfcCartesianPoint((float(x), float(y)))

    def point3(self, x, y, z):
        return self.f.createIfcCartesianPoint((float(x), float(y), float(z)))

    def direction(self, v):
        v = np.asarray(v, dtype=float)
        v = v / np.linalg.norm(v)
        return self.f.createIfcDirection(tuple(float(c) for c in v))

    def profile(self, pts2d):
        pts = [self.point2(x, y) for x, y in pts2d]
        pts.append(pts[0])
        return self.f.createIfcArbitraryClosedProfileDef("AREA", None, self.f.createIfcPolyline(pts))

    def extrusion(self, pts2d, depth: float, down: bool = False):
        """A profile in the local XY plane extruded along local +Z (or -Z)."""
        origin = self.f.createIfcAxis2Placement3D(self.point3(0, 0, 0), None, None)
        return self.f.createIfcExtrudedAreaSolid(self.profile(pts2d), origin,
                                                 self.direction((0, 0, -1 if down else 1)), float(depth))

    def body(self, items):
        return self.f.createIfcShapeRepresentation(self.ctx_body, "Body", "SweptSolid", list(items))

    def axes(self, origin, zdir, xdir):
        z = np.asarray(zdir, float) / np.linalg.norm(zdir)
        x = np.asarray(xdir, float)
        x = x - z * float(x @ z)
        x = x / np.linalg.norm(x)
        return self.f.createIfcAxis2Placement3D(self.point3(*origin), self.direction(z), self.direction(x))

    def place(self, product, origin=(0.0, 0.0, 0.0), zdir=(0.0, 0.0, 1.0), xdir=(1.0, 0.0, 0.0), relative=None):
        product.ObjectPlacement = self.f.createIfcLocalPlacement(relative, self.axes(origin, zdir, xdir))

    def element(self, ifc_class: str, name: str, predefined: str | None = None, object_type: str | None = None,
                identity: tuple | None = None):
        el = self.api.run("root.create_entity", self.f, ifc_class=ifc_class, name=name, predefined_type=predefined)
        el.GlobalId = self.stable(*(identity or (ifc_class, name)))
        if object_type:
            el.ObjectType = object_type
        self.counts[ifc_class] = self.counts.get(ifc_class, 0) + 1
        return el

    def value(self, kind: str, value):
        return self.f.create_entity(kind, value)

    def pset(self, products, name: str, props: dict):
        """A property set on one or more products, made directly: a single value for each property (IfcLabel for
        text, IfcBoolean, IfcInteger, IfcReal, or the measure given)."""
        values = []
        for key, v in props.items():
            if v is None:
                continue
            if not isinstance(v, self.ios.entity_instance):
                v = (self.value("IfcBoolean", v) if isinstance(v, bool) else
                     self.value("IfcInteger", v) if isinstance(v, int) else
                     self.value("IfcReal", float(v)) if isinstance(v, float) else self.value("IfcLabel", str(v)))
            values.append(self.f.createIfcPropertySingleValue(key, None, v, None))
        targets = products if isinstance(products, list) else [products]
        ps = self.f.createIfcPropertySet(self.stable("properties", name, sorted(p.GlobalId for p in targets)),
                                         None, name, None, values)
        self.f.createIfcRelDefinesByProperties(self.guid(), None, None, None,
                                               products if isinstance(products, list) else [products], ps)
        return ps

    def contain(self, products: list, structure) -> None:
        if products:
            self.contained.setdefault(structure.id(), (structure, []))[1].extend(products)

    def relationships(self) -> None:
        """One containment per spatial container; deterministic relationship identities survive membership edits."""
        for holder, products in self.contained.values():
            self.f.createIfcRelContainedInSpatialStructure(self.stable("contains", holder.GlobalId), None,
                                                          None, None, list(dict.fromkeys(products)), holder)
        for rel in self.f.by_type("IfcRelationship"):
            for attribute in ("RelatingObject", "RelatingStructure", "RelatingGroup", "RelatingType",
                              "RelatingPropertyDefinition", "RelatingContext"):
                target = getattr(rel, attribute, None)
                if target is not None and getattr(target, "GlobalId", None):
                    extra = sorted(x.GlobalId for x in rel.RelatedDefinitions) if rel.is_a("IfcRelDeclares") else []
                    rel.GlobalId = self.stable("relationship", rel.is_a(), target.GlobalId, extra)
                    break

    # the project, the site, the buildings

    def setup(self) -> None:
        api, f, p = self.api, self.f, self.p
        self.project = api.run("root.create_entity", f, ifc_class="IfcProject", name=p.name)
        self.project.GlobalId = self.stable("project")
        units = [api.run("unit.add_si_unit", f, unit_type="LENGTHUNIT"),
                 api.run("unit.add_si_unit", f, unit_type="AREAUNIT"),
                 api.run("unit.add_si_unit", f, unit_type="VOLUMEUNIT"),
                 api.run("unit.add_conversion_based_unit", f, name="degree"),
                 api.run("unit.add_si_unit", f, unit_type="POWERUNIT"),
                 api.run("unit.add_si_unit", f, unit_type="ELECTRICVOLTAGEUNIT"),
                 api.run("unit.add_si_unit", f, unit_type="ELECTRICCURRENTUNIT")]
        api.run("unit.assign_unit", f, units=units)
        self.ctx_model = api.run("context.add_context", f, context_type="Model")
        self.ctx_body = api.run("context.add_context", f, context_type="Model", context_identifier="Body",
                                target_view="MODEL_VIEW", parent=self.ctx_model)
        api.run("georeference.edit_true_north", f, true_north=0.0)       # +Y is the true north
        self.site = self.element("IfcSite", p.site.address or p.name, identity=("site",))
        self.site.RefLatitude = dms(p.site.lat)
        self.site.RefLongitude = dms(p.site.lon)
        self.site.RefElevation = 0.0
        if p.site.address:
            self.site.Description = p.site.address
        api.run("aggregate.assign_object", f, products=[self.site], relating_object=self.project)
        self.place(self.site)
        if self.map_conversion:
            zone, east, north, gamma, k = geo.to_utm(p.site.lat, p.site.lon)
            south = p.site.lat < 0
            code = (32700 if south else 32600) + zone
            ang = math.radians(gamma)          # the model's X (East of the true north) in the grid
            api.run("georeference.add_georeferencing", f, ifc_class="IfcMapConversion", name=f"EPSG:{code}")
            api.run("georeference.edit_georeferencing", f,
                    projected_crs={"Name": f"EPSG:{code}", "Description": f"WGS 84 / UTM zone {zone}{'S' if south else 'N'}",
                                   "GeodeticDatum": "WGS84", "MapProjection": "UTM",
                                   "MapZone": f"{zone}{'S' if south else 'N'}"},
                    coordinate_operation={"Eastings": east, "Northings": north, "OrthogonalHeight": 0.0,
                                          "XAxisAbscissa": math.cos(ang), "XAxisOrdinate": math.sin(ang),
                                          "Scale": 1.0})
            self.utm = {"epsg": code, "east": east, "north": north, "convergence": gamma, "k": k}
        self.storeys = {}
        self.building = self.element("IfcBuilding", p.name, identity=("building-container",))
        api.run("aggregate.assign_object", f, products=[self.building], relating_object=self.site)
        self.place(self.building, relative=self.site.ObjectPlacement)
        for b in p.buildings:
            st = self.element("IfcBuildingStorey", b.name, identity=("storey", b.id))
            st.Elevation = 0.0
            api.run("aggregate.assign_object", f, products=[st], relating_object=self.building)
            self.place(st, relative=self.building.ObjectPlacement)
            self.storeys[b.id] = st
        if any(sf.building is None for sf in p.subfields) or any(e.building is None for e in p.exclusions):
            self.ground = self.element("IfcBuildingStorey", "Terreno", identity=("ground",))
            self.ground.Elevation = 0.0
            api.run("aggregate.assign_object", f, products=[self.ground], relating_object=self.building)
            self.place(self.ground, relative=self.building.ObjectPlacement)
        else:
            self.ground = None

    def container(self, building_id):
        return self.storeys.get(building_id) or self.ground or self.building

    # the buildings

    def buildings(self) -> None:
        n = max(1, len(self.p.buildings))
        for i, b in enumerate(self.p.buildings):
            self.tell(0.05 + 0.25 * i / n, b.name)
            self._building(b)

    def _building(self, b) -> None:
        pitches = b.pitches()
        ring = [tuple(map(float, q)) for q in b.footprint]
        if mesh.signed_area(ring) < 0:
            ring.reverse()
        corners = {tuple(map(float, q)) for pt in pitches for q in pt.ring}

        def roof_z(x, y):
            best = None
            for pt in pitches:
                pr = pt.ring
                for a, c in zip(pr, pr[1:] + pr[:1], strict=True):
                    if mesh._on_segment((x, y), a, c):
                        z = pt.z(x, y)
                        best = z if best is None else max(best, z)
            if best is None:
                best = max(pt.z(x, y) for pt in pitches) if pitches else b.height
            return best

        storey = self.storeys[b.id]
        walls = []
        # R281: a canopy has no walls; its columns and beams are exported with the obstacles (IfcColumn, IfcBeam)
        for i, (a, c) in enumerate(zip(ring, ring[1:] + ring[:1], strict=True) if b.canopy is None else ()):
            dx, dy = c[0] - a[0], c[1] - a[1]
            length = math.hypot(dx, dy)
            if length < 1e-6:
                continue
            between = sorted((q for q in corners if q not in (a, c) and mesh._on_segment(q, a, c)),
                             key=lambda q: math.dist(a, q))
            top = [a, *between, c]
            prof = [(0.0, 0.0), (length, 0.0)] + [(math.dist(a, q), roof_z(*q)) for q in reversed(top)]
            wall = self.element("IfcWall", f"{b.name}, parete {i + 1}", predefined="SOLIDWALL",
                                identity=("wall", b.id, i))
            wall.Representation = self.f.createIfcProductDefinitionShape(None, None, [
                self.body([self.extrusion(prof, WALL, down=True)])])
            d = (dx / length, dy / length, 0.0)
            out = (dy / length, -dx / length, 0.0)
            self.place(wall, (a[0], a[1], 0.0), out, d, storey.ObjectPlacement)
            walls.append(wall)
        self.contain(walls, storey)

        roof = self.element("IfcRoof", f"{b.name}, copertura", predefined=ROOF_KINDS.get(b.roof.type, "FREEFORM"),
                            identity=("roof", b.id))
        if b.canopy is not None:                # R281: what the canopy is, beside the roof's own data
            self.pset(roof, "Meridiana_Pensilina", {"Posti": int(b.canopy.bays) * int(b.canopy.rows),
                                                    "File": int(b.canopy.rows), "Pilastri": b.canopy.pillars})
        self.place(roof, relative=storey.ObjectPlacement)
        self.contain([roof], storey)
        slabs = []
        for k, pt in enumerate(pitches):
            beta = math.radians(pt.tilt)
            if pt.tilt == 0:
                n, x = np.array([0.0, 0.0, 1.0]), np.array([1.0, 0.0, 0.0])
            else:
                fx, fy = geo.facing_vector(pt.azimuth)
                n = np.array([math.sin(beta) * fx, math.sin(beta) * fy, math.cos(beta)])
                x = np.array([-fy, fx, 0.0])
            y = np.cross(n, x)
            pts3 = [np.array([qx, qy, pt.z(qx, qy)]) for qx, qy in pt.ring]
            o = pts3[0]
            local = [(float((q - o) @ x), float((q - o) @ y)) for q in pts3]
            if mesh.signed_area(local) < 0:
                local.reverse()
            pitch_id = (b.roof.free_pitches[k].get("id", k) if b.roof.type == "free" else
                        pt.side if pt.side is not None else k)
            slab = self.element("IfcSlab", f"{b.name}, {pt.name or f'falda {k + 1}'}", predefined="ROOF",
                                identity=("pitch", b.id, pitch_id))
            slab.Representation = self.f.createIfcProductDefinitionShape(None, None, [
                self.body([self.extrusion(local, SLAB if b.canopy is None else CANOPY_SLAB, down=True)])])
            self.place(slab, tuple(o), n, x, roof.ObjectPlacement)
            self.pset(slab, "Pset_SlabCommon", {"PitchAngle": self.value("IfcPlaneAngleMeasure", float(pt.tilt)),
                                                "IsExternal": True})
            self.pset(slab, "Meridiana_Falda", {
                "Inclinazione": self.value("IfcPlaneAngleMeasure", float(pt.tilt)),
                "AzimutCEI": self.value("IfcPlaneAngleMeasure", float(pt.azimuth)),
                "AzimutDaNord": self.value("IfcPlaneAngleMeasure", float(geo.azimuth_to_bearing(pt.azimuth))),
                "ConvenzioneAzimut": "CEI 82-25: da sud, positivo verso ovest", "IdEdificio": b.id, "IndiceFalda": k})
            slabs.append(slab)
        if slabs:
            self.f.createIfcRelAggregates(self.guid(), None, None, None, roof, slabs)
        self.pset(roof, "Meridiana_Edificio", {
            "IdEdificio": b.id, "TipoTetto": b.roof.type,
            "AltezzaGronda": self.value("IfcPositiveLengthMeasure", max(float(b.height), 1e-6)),
            "AltezzaColmo": self.value("IfcPositiveLengthMeasure", max(float(b.ridge()), 1e-6)),
            "Parapetto": self.value("IfcLengthMeasure", float(b.parapet))})

    # obstacles and parapets

    def obstacles(self) -> None:
        names = {}
        parts = {}
        by_container: dict = {}
        prisms = self.p.obstacle_prisms()
        for i, o in enumerate(prisms):
            if i % 50 == 0:
                self.tell(0.30 + 0.05 * i / max(1, len(prisms)), "obstacles")
            cls, pre, otype = OBSTACLES.get(o["kind"], OBSTACLES["other"])
            names[o["kind"]] = names.get(o["kind"], 0) + 1
            label = {"parapet": "Parapetto", "chimney": "Camino", "skylight": "Lucernario", "tree": "Albero",
                     "vent": "Evacuatore", "plant": "Impianto", "column": "Pilastro",
                     "beam": "Trave"}.get(o["kind"], "Ostacolo")       # R281: a canopy's columns and beams
            key = (o["kind"], o["id"])
            part = parts.get(key, 0)
            parts[key] = part + 1
            el = self.element(cls, f"{label} {names[o['kind']]}", predefined=pre, object_type=otype,
                              identity=("obstacle", *key, part))
            ring = o["ring"]
            cx = sum(q[0] for q in ring) / len(ring)
            cy = sum(q[1] for q in ring) / len(ring)
            local = [(q[0] - cx, q[1] - cy) for q in ring]
            if mesh.signed_area(local) < 0:
                local.reverse()
            el.Representation = self.f.createIfcProductDefinitionShape(None, None, [
                self.body([self.extrusion(local, max(o["z1"] - o["z0"], 1e-3))])])
            holder = self.container(o["building"])
            self.place(el, (cx, cy, o["z0"]), relative=holder.ObjectPlacement)
            self.pset(el, "Meridiana_Ostacolo", {"Tipo": o["kind"], "Id": o["id"],
                                                 "Altezza": self.value("IfcPositiveLengthMeasure",
                                                                       max(float(o["z1"] - o["z0"]), 1e-6))})
            by_container.setdefault(id(holder), (holder, []))[1].append(el)
        from . import props
        for x in self.p.props:
            # R269: the 3D objects as proxies, their outline raised to their height (people stay out, as in the shadows)
            if not x.casts_shadow():
                continue
            try:
                ring, height = x.footprint(), x.measures()["height"]
            except ValueError:
                continue
            z0 = self.p.prop_base(x)
            cx, cy = float(x.at[0]), float(x.at[1])
            local = [(q[0] - cx, q[1] - cy) for q in ring]
            if mesh.signed_area(local) < 0:
                local.reverse()
            el = self.element("IfcBuildingElementProxy", self.p.prop_label(x), predefined="USERDEFINED",
                              object_type=props.family(x.kind), identity=("prop", x.id))
            el.Representation = self.f.createIfcProductDefinitionShape(None, None, [
                self.body([self.extrusion(local, max(height, 1e-3))])])
            holder = self.container(x.building)
            self.place(el, (cx, cy, z0), relative=holder.ObjectPlacement)
            self.pset(el, "Meridiana_Oggetto3D", {"Tipo": x.kind, "Id": x.id,
                                                  "Altezza": self.value("IfcPositiveLengthMeasure", max(height, 1e-6))})
            by_container.setdefault(id(holder), (holder, []))[1].append(el)
        for holder, els in by_container.values():
            self.contain(els, holder)

    # the modules

    def supports(self) -> None:
        """Enabled auxiliary planes are virtual reference surfaces, also before any module is laid."""
        for sf in self.p.subfields:
            if sf.support is None or not sf.support.enabled or len(sf.ring) < 3:
                continue
            support = sf.support
            surface = support.surface()
            beta = math.radians(surface.tilt)
            fx, fy = geo.facing_vector(surface.azimuth)
            normal = np.array([math.sin(beta) * fx, math.sin(beta) * fy, math.cos(beta)])
            xdir = np.array([-fy, fx, 0.0])
            ydir = np.cross(normal, xdir)
            points = [np.array([x, y, surface.z(x, y)]) for x, y in sf.ring]
            origin = points[0]
            local = [(float((q - origin) @ xdir), float((q - origin) @ ydir)) for q in points]
            boundary = self.profile(local).OuterCurve
            plane = self.f.createIfcPlane(self.f.createIfcAxis2Placement3D(self.point3(0, 0, 0), None, None))
            bounded = self.f.createIfcCurveBoundedPlane(plane, boundary, [])
            geometry = self.f.createIfcGeometricSet([bounded])
            annotation = self.element("IfcAnnotation", sf.name, object_type="MERIDIANA_PLACEMENT_SURFACE",
                                      identity=("support", self.p.variant, sf.id))
            annotation.Description = "Virtual placement reference; not a constructed building element."
            annotation.Representation = self.f.createIfcProductDefinitionShape(None, None, [
                self.f.createIfcShapeRepresentation(self.ctx_body, "Annotation", "GeometricSet", [geometry])])
            holder = self.container(sf.building)
            self.place(annotation, origin, normal, xdir, holder.ObjectPlacement)
            self.contain([annotation], holder)
            self.pset(annotation, "Meridiana_Supporto", {
                "IdProgettoBIM": self.p.bim_id, "IdVariante": self.p.variant, "IdSottocampo": sf.id,
                "IdEdificio": sf.building, "IndiceFalda": sf.pitch, "Attivo": True,
                "Inclinazione": self.value("IfcPlaneAngleMeasure", support.tilt),
                "AzimutCEI": self.value("IfcPlaneAngleMeasure", support.azimuth),
                "Quota": self.value("IfcLengthMeasure", support.z0),
                "EstRiferimento": self.value("IfcLengthMeasure", support.x0),
                "NordRiferimento": self.value("IfcLengthMeasure", support.y0)})

    def modules(self) -> int:
        f = self.f
        types: dict = {}
        total = 0
        laid = [(sf, self.results[sf.id]) for sf in self.p.subfields if sf.id in self.results]
        count = max(1, sum(len(r.modules) for _sf, r in laid))
        identity = f.createIfcCartesianTransformationOperator3D(None, None, self.point3(0, 0, 0), None, None)
        by_string: dict = {}
        of_type: dict = {}              # one IfcRelDefinesByType for each type (its inverse is SET [0:1])
        all_modules = []
        for sf, result in laid:
            if not result.modules:
                continue
            data = self.p.modules.get(sf.module) or {}
            mod = self.p.module_of(sf)
            params = sf.layout_params()
            along, across = (mod.width, mod.length) if params.portrait else (mod.length, mod.width)
            thick = float(data.get("thickness_mm") or MODULE_THICKNESS * 1000) / 1000.0
            key = (sf.module, bool(params.portrait))
            if key not in types:
                types[key] = self._module_type(sf, data, mod, along, across, thick, params.portrait)
            ptype, repmap = types[key]
            holder = self.container(sf.building)
            occs = []
            power = self.value("IfcPowerMeasure", float(mod.power_kw) * 1000.0)
            for pm in result.modules:
                b = math.radians(geo.azimuth_to_bearing(pm.azimuth))
                fe, fn = math.sin(b), math.cos(b)
                beta = math.radians(pm.tilt)
                n = np.array([math.sin(beta) * fe, math.sin(beta) * fn, math.cos(beta)])
                # along the row; turned by 90 degrees (layout.Row.turned) the type's long side goes up the slope
                u = np.array([-fn, fe, 0.0])
                spin = math.radians(getattr(pm, "spin", 0.0))
                if spin:                    # a row on a pitch that does not run level (R278, R280)
                    u = u * math.cos(spin) + np.cross(n, u) * math.sin(spin)
                if getattr(pm, "turned", False):
                    u = np.cross(n, u)
                origin = np.array([pm.centre[0], pm.centre[1], pm.z]) - n * thick / 2
                occ = f.createIfcSolarDevice(self.stable("module", self.p.variant, sf.id, pm.key),
                                             None, f"{sf.name} {pm.key}", None, None,
                                             f.createIfcLocalPlacement(holder.ObjectPlacement,
                                                                       self.axes(origin, n, u)),
                                             f.createIfcProductDefinitionShape(None, None, [
                                                 f.createIfcShapeRepresentation(self.ctx_body, "Body",
                                                                                "MappedRepresentation",
                                                                                [f.createIfcMappedItem(repmap, identity)])]),
                                             None, "SOLARPANEL")
                label = self.strings.get((sf.id, pm.key), "")
                self.pset(occ, "Meridiana_Modulo", {
                    "IdProgettoBIM": self.p.bim_id, "IdVariante": self.p.variant,
                    "IdModuloCatalogo": sf.module, "IdEdificio": sf.building,
                    "IndiceFalda": sf.pitch,
                    "IdSottocampo": sf.id, "Sottocampo": sf.name, "Chiave": pm.key, "Fila": int(pm.row),
                    "Posto": int(pm.slot), "Livello": int(pm.level), "Stringa": label or None,
                    "Inclinazione": self.value("IfcPlaneAngleMeasure", float(pm.tilt)),
                    "AzimutCEI": self.value("IfcPlaneAngleMeasure", float(pm.azimuth)),
                    "AzimutDaNord": self.value("IfcPlaneAngleMeasure", float(geo.azimuth_to_bearing(pm.azimuth))),
                    "PotenzaNominale": power})
                if label:
                    by_string.setdefault(label, []).append(occ)
                occs.append(occ)
                total += 1
                if total % 200 == 0:
                    self.tell(0.35 + 0.55 * total / count, sf.name)
            self.counts["IfcSolarDevice"] = self.counts.get("IfcSolarDevice", 0) + len(occs)
            of_type.setdefault(key, []).extend(occs)
            self.contain(occs, holder)
            all_modules.extend(occs)
            grp = f.createIfcGroup(self.stable("subfield", self.p.variant, sf.id),
                                    None, f"Sottocampo {sf.name}", None, None)
            f.createIfcRelAssignsToGroup(self.guid(), None, None, None, occs, None, grp)
            self.pset(grp, "Meridiana_Sottocampo", {
                "IdSottocampo": sf.id, "Montaggio": params.mounting, "Moduli": len(occs),
                "PotenzaPicco": self.value("IfcPowerMeasure", len(occs) * float(mod.power_kw) * 1000.0),
                "InclinazioneModuli": self.value("IfcPlaneAngleMeasure", float(result.tilt)),
                "AzimutCEI": self.value("IfcPlaneAngleMeasure", float(result.azimuth)),
                "PassoFile": self.value("IfcLengthMeasure", float(result.pitch))})
            if sf.support is not None:
                self.pset(grp, "Meridiana_Supporto", {
                    "Attivo": sf.support.enabled, "Inclinazione": sf.support.tilt,
                    "AzimutCEI": sf.support.azimuth, "Quota": self.value("IfcLengthMeasure", sf.support.z0),
                    "EstRiferimento": self.value("IfcLengthMeasure", sf.support.x0),
                    "NordRiferimento": self.value("IfcLengthMeasure", sf.support.y0)})
        for key, occs in of_type.items():
            f.createIfcRelDefinesByType(self.guid(), None, None, None, occs, types[key][0])
        for label, occs in sorted(by_string.items()):
            grp = f.createIfcGroup(self.stable("string", self.p.variant, label), None, f"Stringa {label}", None, None)
            f.createIfcRelAssignsToGroup(self.guid(), None, None, None, occs, None, grp)
            self.pset(grp, "Meridiana_Stringa", {"Stringa": label, "Moduli": len(occs)})
        self.counts["strings"] = len(by_string)
        if all_modules:
            system = self.element("IfcSystem", "Impianto fotovoltaico", identity=("pv-system", self.p.variant))
            f.createIfcRelAssignsToGroup(self.guid(), None, None, None, all_modules, None, system)
            self.pset(system, "Meridiana_Impianto", {"IdProgettoBIM": self.p.bim_id,
                      "IdVariante": self.p.variant, "Variante": self.p.current_variant().get("name", ""),
                      "ModuliPosati": len(all_modules)})
        return total

    def _module_type(self, sf, data: dict, mod, along: float, across: float, thick: float, portrait: bool):
        f = self.f
        label = f"{data.get('manufacturer', '')} {data.get('model', sf.module)}".strip()
        t = self.element("IfcSolarDeviceType", f"{label} ({'verticale' if portrait else 'orizzontale'})",
                         predefined="SOLARPANEL", identity=("module-type", sf.module, portrait))
        prof = f.createIfcRectangleProfileDef("AREA", None, f.createIfcAxis2Placement2D(self.point2(0, 0), None),
                                              float(along), float(across))
        solid = f.createIfcExtrudedAreaSolid(prof, f.createIfcAxis2Placement3D(self.point3(0, 0, 0), None, None),
                                             self.direction((0, 0, 1)), thick)
        repmap = f.createIfcRepresentationMap(f.createIfcAxis2Placement3D(self.point3(0, 0, 0), None, None),
                                              self.body([solid]))
        t.RepresentationMaps = [repmap]
        self.pset(t, "Pset_ManufacturerTypeInformation", {
            "Manufacturer": str(data.get("manufacturer", "")), "ModelLabel": str(data.get("model", sf.module)),
            "ModelReference": str(data.get("id", sf.module))})
        dati = {"PotenzaNominale": self.value("IfcPowerMeasure", float(mod.power_kw) * 1000.0),
                "Lunghezza": self.value("IfcPositiveLengthMeasure", float(mod.length)),
                "Larghezza": self.value("IfcPositiveLengthMeasure", float(mod.width)),
                "Spessore": self.value("IfcPositiveLengthMeasure", thick)}
        for k_json, k_ifc, kind in (("voc", "Voc", "IfcElectricVoltageMeasure"),
                                    ("isc", "Isc", "IfcElectricCurrentMeasure"),
                                    ("vmp", "Vmp", "IfcElectricVoltageMeasure"),
                                    ("imp", "Imp", "IfcElectricCurrentMeasure")):
            if isinstance(data.get(k_json), (int, float)):
                dati[k_ifc] = self.value(kind, float(data[k_json]))
        if isinstance(data.get("efficiency_pct"), (int, float)):
            dati["Efficienza"] = self.value("IfcPositiveRatioMeasure", float(data["efficiency_pct"]) / 100.0)
        if isinstance(data.get("gamma_pmax"), (int, float)):
            dati["CoeffTemperaturaPmax_percento_per_K"] = float(data["gamma_pmax"])
        if isinstance(data.get("cells"), int):
            dati["Celle"] = int(data["cells"])
        if data.get("technology"):
            dati["Tecnologia"] = str(data["technology"])
        self.pset(t, "Meridiana_DatiModulo", dati)
        self.f.createIfcRelDeclares(self.guid(), None, None, None, self.project, [t])
        return t, repmap

    def write(self, path: Path) -> dict:
        self.tell(0.0, "project")
        self.setup()
        self.buildings()
        self.obstacles()
        self.supports()
        n = self.modules()
        self.relationships()
        self.tell(0.92, "file")
        path = Path(path)
        part = path.with_name(path.name + ".part")
        try:
            self.f.write(str(part))
            os.replace(part, path)
        finally:
            if part.exists():
                part.unlink()
        self.tell(1.0, "done")
        return {"file": str(path), "schema": self.f.schema, "modules": n, "classes": dict(self.counts),
                "bytes": path.stat().st_size, "map": getattr(self, "utm", None)}


def export(project, results: dict, path, strings: dict | None = None, map_conversion: bool = True,
           progress: Callable[[float, str], None] | None = None) -> dict:
    """Write `project` with the layouts `results` (sub-field id -> layout.Result) to `path` as IFC4. `progress(fraction,
    what)` is told along the way and may raise Interrupted to stop: nothing is written then. A summary comes back."""
    return Writer(project, results, strings, map_conversion, progress).write(Path(path))


def validate(path) -> list[str]:
    """What ifcopenshell.validate finds wrong in a file (the schema, the types, the inverses; not the EXPRESS rules):
    empty when it is right."""
    import logging

    import ifcopenshell
    import ifcopenshell.validate
    found: list[str] = []

    class Collect(logging.Handler):
        def emit(self, record):
            found.append(record.getMessage())
    logger = logging.getLogger("meridiana.ifc.validate")
    logger.propagate = False
    logger.handlers = [Collect()]
    logger.setLevel(logging.WARNING)
    ifcopenshell.validate.validate(ifcopenshell.open(str(path)), logger, express_rules=False)
    return found
