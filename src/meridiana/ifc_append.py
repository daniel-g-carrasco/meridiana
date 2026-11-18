"""The plant added to the architect's own IFC (r22-ifc; the study in docs/revisioni/r17-relazione-ifc). Without Qt.

The export of the plant alone (ifc_export, what="plant") is a file of its own, to lie on the architect's model in a
federated model. This writes one file instead: the architect's IFC as it is, byte for byte, with the plant added at the
end of its data: the modules (one type for each module and orientation, its shape once), the canopies' columns and
beams, a group for each sub-field, the strings as circuits of the plant's system, the inverters. Nothing of the file is
changed: the new entities refer to its project, its owner history, its geometric context and its spatial structure
(the storey under the modules, else the building, else the site) by their ids; the new ids start after the file's
highest. The coordinates are the file's: its world, in its length unit, through the frame the import kept
(`ifc_export.frame_of`: the anchor body, moved or not since); the GlobalIds are stable (uuid5 of the project, the
same keys as ifc_export, so a module has one GlobalId in both deliveries).

Large files (the large test IFC, 1.6 GB): the file is read once in chunks for what is needed (its schema, its highest id, a few
records: project, owner history, contexts, site, building, storeys, units), never loaded; the result is the original
copied in blocks with the new records written before its last ENDSEC. The new entities are made with ifcopenshell in a
small file of the original's schema (IFC2X3: IfcEnergyConversionDevice and IfcTypeProduct for the modules,
IfcElectricalCircuit and IfcSystem for the strings and the plant; IFC4 and later: IfcSolarDevice, IfcDistributionCircuit,
IfcDistributionSystem, IfcTransformer) around stand-ins for the original's entities, then renumbered.

A file that already holds a plant of Meridiana's (its Pset Meridiana_Modulo) is refused: the plant goes into the
architect's original, not into a file it was added to before."""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import uuid
from collections.abc import Callable
from pathlib import Path

import numpy as np

from . import geo, mesh
from .i18n import _
from .ifc_export import MODULE_THICKNESS, frame_of

CHUNK = 64 << 20
WANTED = (b"IFCPROJECT", b"IFCOWNERHISTORY", b"IFCGEOMETRICREPRESENTATIONCONTEXT",
          b"IFCGEOMETRICREPRESENTATIONSUBCONTEXT", b"IFCSITE", b"IFCBUILDING", b"IFCBUILDINGSTOREY", b"IFCSIUNIT",
          b"IFCCONVERSIONBASEDUNIT")
_RECORD = re.compile(rb"#(\d+)\s*=\s*([A-Za-z0-9_]+)\s*\(")
_ID = re.compile(rb"#(\d+)\s*=")
_MARK = b"Meridiana_Modulo"
_PREFIX = {"EXA": 1e18, "PETA": 1e15, "TERA": 1e12, "GIGA": 1e9, "MEGA": 1e6, "KILO": 1e3, "HECTO": 1e2, "DECA": 1e1,
           "DECI": 1e-1, "CENTI": 1e-2, "MILLI": 1e-3, "MICRO": 1e-6, "NANO": 1e-9}


class AppendError(Exception):
    """Why the plant cannot be added to that file, in words."""


def _end(buf: bytes, start: int) -> int:
    """The index just past the `;` that closes the record starting at `start`, -1 when the buffer ends first."""
    i, n, quoted = start, len(buf), False
    while i < n:
        c = buf[i]
        if c == 39:                     # '
            quoted = not quoted
        elif c == 59 and not quoted:    # ;
            return i + 1
        i += 1
    return -1


def survey(path, progress: Callable[[float], None] | None = None) -> dict:
    """What the file is, read once in chunks: {"schema", "top" (the highest id), "records" {id: (type, text)} of the
    WANTED types, "newline", "marked" (a plant of Meridiana's already in it), "size"}."""
    path = Path(path)
    size = path.stat().st_size
    top, records, marked, newline, schema = 0, {}, False, b"\n", ""
    carry = b""
    done = 0
    with open(path, "rb") as fh:
        head = fh.read(1 << 16)
        m = re.search(rb"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'", head)
        if m is None or not head.lstrip().startswith(b"ISO-10303-21"):
            raise AppendError(_("not an IFC file (ISO-10303-21)"))
        schema = m.group(1).decode("ascii", "replace").upper()
        newline = b"\r\n" if b"\r\n" in head else b"\n"
        fh.seek(0)
        while True:
            chunk = fh.read(CHUNK)
            last = not chunk
            buf = carry + chunk
            cut = len(buf) if last else buf.rfind(b"\n") + 1
            if cut <= 0 and not last:
                carry = buf
                continue
            marked = marked or _MARK in buf
            for rec in _RECORD.finditer(buf, 0, cut):
                kind = rec.group(2).upper()
                if kind in WANTED:
                    stop = _end(buf, rec.start())
                    if stop < 0:
                        if last:
                            break
                        cut = rec.start()
                        break
                    records[int(rec.group(1))] = (kind.decode("ascii"), buf[rec.start():stop].decode("latin-1"))
            ids = _ID.findall(buf, 0, cut)
            if ids:
                top = max(top, max(map(int, ids)))
            carry = buf[cut:]
            done += len(chunk)
            if progress is not None:
                progress(min(1.0, done / max(1, size)))
            if last:
                break
    return {"schema": schema, "top": top, "records": records, "newline": newline.decode(), "marked": marked,
            "size": size}


def _args(text: str) -> list:
    """The top-level attributes of a record's text, as strings ('' for $), without parsing their insides."""
    body = text[text.index("(") + 1:text.rindex(")")]
    out, depth, cur, quoted = [], 0, [], False
    for ch in body:
        if ch == "'":
            quoted = not quoted
        if not quoted:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 0:
                out.append("".join(cur).strip())
                cur = []
                continue
        cur.append(ch)
    out.append("".join(cur).strip())
    return out


def _text(value: str) -> str:
    return value[1:-1].replace("''", "'") if value.startswith("'") else ""


def units(records: dict) -> tuple[float, bool]:
    """(metres in the file's length unit, angles in degrees) from its units."""
    metre, degrees = 1.0, False
    for kind, text in records.values():
        a = _args(text)
        if kind == "IFCSIUNIT" and len(a) >= 4:
            if a[1] == ".LENGTHUNIT." and a[3] == ".METRE.":
                metre = _PREFIX.get(a[2].strip("."), 1.0)
        elif kind == "IFCCONVERSIONBASEDUNIT" and len(a) >= 3:
            name = _text(a[2]).upper()
            if a[1] == ".PLANEANGLEUNIT." and "DEG" in name:
                degrees = True
            elif a[1] == ".LENGTHUNIT.":
                metre = 0.3048 if "FOOT" in name or "FEET" in name else 0.0254 if "INCH" in name else metre
    return metre, degrees


def hosts(survey_: dict) -> dict:
    """The original's entities the plant refers to: {"project", "owner", "context", "site", "building", "storeys"
    [(id, name, elevation in file units)]} as ids (None when missing)."""
    recs = survey_["records"]
    of = {}
    for rid, (kind, _t) in sorted(recs.items()):
        of.setdefault(kind, []).append(rid)
    context = None
    for rid in of.get("IFCGEOMETRICREPRESENTATIONSUBCONTEXT", []):
        a = _args(recs[rid][1])
        if _text(a[0]).lower() == "body":
            context = rid
            break
    if context is None:
        for rid in of.get("IFCGEOMETRICREPRESENTATIONCONTEXT", []):
            a = _args(recs[rid][1])
            if _text(a[1]).lower() in ("model", ""):
                context = rid
                break
    storeys = []
    for rid in of.get("IFCBUILDINGSTOREY", []):
        a = _args(recs[rid][1])
        try:
            z = float(a[9]) if len(a) > 9 and a[9] not in ("", "$") else 0.0
        except ValueError:
            z = 0.0
        storeys.append((rid, _text(a[2]), z))
    first = lambda k: (of.get(k) or [None])[0]          # noqa: E731
    return {"project": first("IFCPROJECT"), "owner": first("IFCOWNERHISTORY"), "context": context,
            "site": first("IFCSITE"), "building": first("IFCBUILDING"), "storeys": storeys}


class _Plant:
    """The plant's entities in a small file of the original's schema, around stand-ins for the original's."""

    def __init__(self, project, results: dict, strings: dict, plant, schema: str, host: dict, metre: float,
                 degrees: bool, frame: dict):
        import ifcopenshell
        import ifcopenshell.guid
        self.ios = ifcopenshell
        self.p = project
        self.results = {k: v for k, v in (results or {}).items() if not isinstance(v, Exception)}
        self.strings = strings or {}
        self.plant = plant
        self.old = schema.startswith("IFC2X")
        self.f = ifcopenshell.file(schema="IFC2X3" if self.old else ("IFC4" if schema == "IFC4" else schema))
        self.namespace = uuid.UUID(project.bim_id)
        self.k = 1.0 / metre                    # file units in a metre
        self.angle = 1.0 if degrees or not self.old else math.pi / 180.0
        self.frame = frame
        self.counts: dict = {}
        self.stand: dict = {}                   # stand-in -> original id
        f = self.f
        guid = self.stable("stand-in")
        self.project = self._stand(f.create_entity("IfcProject", GlobalId=guid), host["project"])
        self.owner = self._stand(f.create_entity("IfcOwnerHistory"), host["owner"]) if host["owner"] else None
        self.context = self._stand(f.create_entity("IfcGeometricRepresentationContext"), host["context"])
        self.storeys = [(self._stand(f.create_entity("IfcBuildingStorey", GlobalId=guid), rid), z)
                        for rid, _n, z in host["storeys"]]
        top = host["building"] or host["site"]
        self.top = self._stand(f.create_entity("IfcBuilding" if host["building"] else "IfcSite", GlobalId=guid), top) \
            if top else None
        self.contained: dict = {}

    def _stand(self, entity, original):
        self.stand[entity.id()] = original
        return entity

    def stable(self, *key) -> str:
        return self.ios.guid.compress(uuid.uuid5(self.namespace, json.dumps(key, ensure_ascii=False)).hex)

    def root(self, cls: str, key: tuple, **kw):
        el = self.f.create_entity(cls, GlobalId=self.stable(*key), OwnerHistory=self.owner, **kw)
        self.counts[cls] = self.counts.get(cls, 0) + 1
        return el

    def point(self, *xyz):
        return self.f.create_entity("IfcCartesianPoint", Coordinates=[float(c) for c in xyz])

    def direction(self, v):
        v = np.asarray(v, float)
        return self.f.create_entity("IfcDirection", DirectionRatios=[float(c) for c in v / np.linalg.norm(v)])

    def axes(self, origin, zdir=(0, 0, 1), xdir=(1, 0, 0)):
        z = np.asarray(zdir, float) / np.linalg.norm(zdir)
        x = np.asarray(xdir, float)
        x = x - z * float(x @ z)
        return self.f.create_entity("IfcAxis2Placement3D", Location=self.point(*origin), Axis=self.direction(z),
                                    RefDirection=self.direction(x))

    def value(self, kind: str, v):
        return self.f.create_entity(kind, v)

    def pset(self, product, name: str, props: dict) -> None:
        values = []
        for key, v in props.items():
            if v is None:
                continue
            if not isinstance(v, self.ios.entity_instance):
                v = (self.value("IfcBoolean", v) if isinstance(v, bool) else
                     self.value("IfcInteger", v) if isinstance(v, int) else
                     self.value("IfcReal", float(v)) if isinstance(v, float) else self.value("IfcLabel", str(v)))
            values.append(self.f.create_entity("IfcPropertySingleValue", Name=key, NominalValue=v))
        ps = self.f.create_entity("IfcPropertySet", GlobalId=self.stable("properties", name, product.GlobalId),
                                  OwnerHistory=self.owner, Name=name, HasProperties=values)
        if product.is_a("IfcTypeObject"):           # a type holds its sets itself (IFC2X3: only objects are defined)
            product.HasPropertySets = list(product.HasPropertySets or []) + [ps]
            return
        self.f.create_entity("IfcRelDefinesByProperties", GlobalId=self.stable("defines", name, product.GlobalId),
                             OwnerHistory=self.owner, RelatedObjects=[product], RelatingPropertyDefinition=ps)

    def holder(self, z_world: float):
        """The storey under a height of the world (file units): the highest at or below it, else the lowest; the
        building (or the site) when the file has no storeys."""
        if not self.storeys:
            return self.top
        under = [s for s in self.storeys if s[1] <= z_world + 1e-6]
        return max(under, key=lambda s: s[1])[0] if under else min(self.storeys, key=lambda s: s[1])[0]

    def contain(self, product, z_world: float) -> None:
        h = self.holder(z_world)
        if h is not None:
            self.contained.setdefault(h.id(), (h, []))[1].append(product)

    def ground(self, building_id) -> float:
        """The ground of a building in the model's world, metres (ifc_export.Writer.setup)."""
        grounds = self.frame.get("buildings") or {}
        base = float(grounds.get((self.frame.get("anchor") or {}).get("building"), 0.0))
        return float(grounds.get(building_id, base))

    def build(self) -> int:
        self.structures()
        return self.modules()

    def place(self, origin_m, zdir=(0, 0, 1), xdir=(1, 0, 0)):
        """A placement of its own in the file's world (IFC2X3 wants one product for each placement): the plan's point
        and axes turned and moved by the import's frame, world = R(turn) plan + move, in the file's unit."""
        mx, my = self.frame["move"]
        c, s = math.cos(float(self.frame["turn"])), math.sin(float(self.frame["turn"]))
        r = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
        at = r @ np.asarray(origin_m, float) + np.array([mx, my, 0.0])
        return self.f.create_entity("IfcLocalPlacement", PlacementRelTo=None,
                                    RelativePlacement=self.axes(at * self.k, r @ np.asarray(zdir, float),
                                                                r @ np.asarray(xdir, float)))

    def body(self, items, kind="SweptSolid"):
        return self.f.create_entity("IfcShapeRepresentation", ContextOfItems=self.context, RepresentationIdentifier="Body",
                                    RepresentationType=kind, Items=list(items))

    def extrusion(self, ring_m, depth_m):
        pts = [self.point(x * self.k, y * self.k) for x, y in ring_m]
        profile = self.f.create_entity("IfcArbitraryClosedProfileDef", ProfileType="AREA",
                                       OuterCurve=self.f.create_entity("IfcPolyline", Points=pts + [pts[0]]))
        return self.f.create_entity("IfcExtrudedAreaSolid", SweptArea=profile, Position=self.axes((0, 0, 0)),
                                    ExtrudedDirection=self.direction((0, 0, 1)), Depth=float(depth_m * self.k))

    def structures(self) -> None:
        """The canopies' columns and beams (canopies.structure through obstacle_prisms), as ifc_export writes them."""
        parts: dict = {}
        for o in self.p.obstacle_prisms():
            if o["kind"] not in ("column", "beam"):
                continue
            key = (o["kind"], o["id"])
            part = parts.get(key, 0)
            parts[key] = part + 1
            ring = o["ring"]
            cx, cy = sum(q[0] for q in ring) / len(ring), sum(q[1] for q in ring) / len(ring)
            local = [(q[0] - cx, q[1] - cy) for q in ring]
            if mesh.signed_area(local) < 0:
                local.reverse()
            z = self.ground(o["building"]) + float(o["z0"])
            cls = "IfcColumn" if o["kind"] == "column" else "IfcBeam"
            label = "Pilastro" if o["kind"] == "column" else "Trave"
            el = self.root(cls, ("obstacle", *key, part), Name=f"{label} {sum(parts.values())}",
                           ObjectPlacement=self.place((cx, cy, z)),
                           Representation=self.f.create_entity("IfcProductDefinitionShape", Representations=[
                               self.body([self.extrusion(local, max(float(o["z1"] - o["z0"]), 1e-3))])]))
            self.pset(el, "Meridiana_Ostacolo", {"Tipo": o["kind"], "Id": o["id"]})
            self.contain(el, z * self.k)

    def _type(self, sf, data, mod, along, across, thick, portrait):
        f = self.f
        label = f"{data.get('manufacturer', '')} {data.get('model', sf.module)}".strip()
        name = f"{label} ({'verticale' if portrait else 'orizzontale'})"
        prof = f.create_entity("IfcRectangleProfileDef", ProfileType="AREA",
                               Position=f.create_entity("IfcAxis2Placement2D", Location=self.point(0.0, 0.0)),
                               XDim=float(along * self.k), YDim=float(across * self.k))
        solid = f.create_entity("IfcExtrudedAreaSolid", SweptArea=prof, Position=self.axes((0, 0, 0)),
                                ExtrudedDirection=self.direction((0, 0, 1)), Depth=float(thick * self.k))
        repmap = f.create_entity("IfcRepresentationMap", MappingOrigin=self.axes((0, 0, 0)),
                                 MappedRepresentation=self.body([solid]))
        key = ("module-type", sf.module, portrait)
        if self.old:
            t = self.root("IfcTypeProduct", key, Name=name, RepresentationMaps=[repmap], Tag="SOLARPANEL")
        else:
            t = self.root("IfcSolarDeviceType", key, Name=name, RepresentationMaps=[repmap], PredefinedType="SOLARPANEL")
        self.pset(t, "Meridiana_DatiModulo", {
            "PotenzaNominale": self.value("IfcPowerMeasure", float(mod.power_kw) * 1000.0),
            "Lunghezza": self.value("IfcPositiveLengthMeasure", float(mod.length) * self.k),
            "Larghezza": self.value("IfcPositiveLengthMeasure", float(mod.width) * self.k),
            "Spessore": self.value("IfcPositiveLengthMeasure", thick * self.k),
            "Produttore": str(data.get("manufacturer", "")) or None, "Modello": str(data.get("model", sf.module))})
        return t, repmap

    def modules(self) -> int:
        f, p = self.f, self.p
        types: dict = {}
        of_type: dict = {}
        by_string: dict = {}
        everything = []
        identity = f.create_entity("IfcCartesianTransformationOperator3D", LocalOrigin=self.point(0.0, 0.0, 0.0))
        for sf in p.subfields:
            result = self.results.get(sf.id)
            if result is None or not result.modules:
                continue
            data = p.modules.get(sf.module) or {}
            mod = p.module_of(sf)
            params = sf.layout_params()
            along, across = (mod.width, mod.length) if params.portrait else (mod.length, mod.width)
            thick = float(data.get("thickness_mm") or MODULE_THICKNESS * 1000) / 1000.0
            key = (sf.module, bool(params.portrait))
            if key not in types:
                types[key] = self._type(sf, data, mod, along, across, thick, params.portrait)
            ptype, repmap = types[key]
            ground = self.ground(sf.building)
            power = self.value("IfcPowerMeasure", float(mod.power_kw) * 1000.0)
            mine = []
            for pm in result.modules:
                b = math.radians(geo.azimuth_to_bearing(pm.azimuth))
                fe, fn = math.sin(b), math.cos(b)
                beta = math.radians(pm.tilt)
                n = np.array([math.sin(beta) * fe, math.sin(beta) * fn, math.cos(beta)])
                u = np.array([-fn, fe, 0.0])
                spin = math.radians(getattr(pm, "spin", 0.0))
                if spin:
                    u = u * math.cos(spin) + np.cross(n, u) * math.sin(spin)
                if getattr(pm, "turned", False):
                    u = np.cross(n, u)
                origin = np.array([pm.centre[0], pm.centre[1], ground + pm.z]) - n * thick / 2
                shape = f.create_entity("IfcProductDefinitionShape", Representations=[
                    self.body([f.create_entity("IfcMappedItem", MappingSource=repmap, MappingTarget=identity)],
                              "MappedRepresentation")])
                kw = dict(Name=f"{sf.name} {pm.key}", ObjectPlacement=self.place(origin, n, u), Representation=shape)
                if self.old:
                    occ = self.root("IfcEnergyConversionDevice", ("module", p.variant, sf.id, pm.key),
                                    ObjectType="SOLARPANEL", **kw)
                else:
                    occ = self.root("IfcSolarDevice", ("module", p.variant, sf.id, pm.key), PredefinedType="SOLARPANEL",
                                    **kw)
                label = self.strings.get((sf.id, pm.key), "")
                self.pset(occ, "Meridiana_Modulo", {
                    "IdProgettoBIM": p.bim_id, "IdVariante": p.variant, "IdModuloCatalogo": sf.module,
                    "IdEdificio": sf.building, "IdSottocampo": sf.id, "Sottocampo": sf.name, "Chiave": pm.key,
                    "Fila": int(pm.row), "Posto": int(pm.slot), "Stringa": label or None,
                    "Inclinazione": self.value("IfcPlaneAngleMeasure", float(pm.tilt) * self.angle),
                    "AzimutCEI": self.value("IfcPlaneAngleMeasure", float(pm.azimuth) * self.angle),
                    "PotenzaNominale": power})
                if label:
                    by_string.setdefault(label, []).append(occ)
                self.contain(occ, origin[2] * self.k)
                mine.append(occ)
            of_type.setdefault(key, []).extend(mine)
            everything += mine
            group = self.root("IfcGroup", ("subfield", p.variant, sf.id), Name=f"Sottocampo {sf.name}")
            f.create_entity("IfcRelAssignsToGroup", GlobalId=self.stable("grouped", "subfield", sf.id),
                            OwnerHistory=self.owner, RelatedObjects=mine, RelatingGroup=group)
            self.pset(group, "Meridiana_Sottocampo", {"IdSottocampo": sf.id, "Moduli": len(mine)})
        for key, occs in of_type.items():
            f.create_entity("IfcRelDefinesByType", GlobalId=self.stable("typed", *key), OwnerHistory=self.owner,
                            RelatedObjects=occs, RelatingType=types[key][0])
        circuits = []
        for label, occs in sorted(by_string.items()):
            if self.old:
                c = self.root("IfcElectricalCircuit", ("string", p.variant, label), Name=f"Stringa {label}")
            else:
                c = self.root("IfcDistributionCircuit", ("string", p.variant, label), Name=f"Stringa {label}",
                              PredefinedType="ELECTRICAL")
            f.create_entity("IfcRelAssignsToGroup", GlobalId=self.stable("grouped", "string", label),
                            OwnerHistory=self.owner, RelatedObjects=occs, RelatingGroup=c)
            self.pset(c, "Meridiana_Stringa", {"Stringa": label, "Moduli": len(occs)})
            circuits.append(c)
        self.counts["strings"] = len(circuits)
        if everything:
            name = "Impianto fotovoltaico"
            if self.old:
                system = self.root("IfcSystem", ("pv-system", p.variant), Name=name)
            else:
                system = self.root("IfcDistributionSystem", ("pv-system", p.variant), Name=name,
                                   PredefinedType="POWERGENERATION")
            inverters = self.inverters()
            f.create_entity("IfcRelAssignsToGroup", GlobalId=self.stable("grouped", "system"), OwnerHistory=self.owner,
                            RelatedObjects=everything + inverters, RelatingGroup=system)
            if circuits:
                f.create_entity("IfcRelAggregates", GlobalId=self.stable("aggregates", "system"), OwnerHistory=self.owner,
                                RelatingObject=system, RelatedObjects=circuits)
            self.pset(system, "Meridiana_Impianto", {"IdProgettoBIM": p.bim_id, "IdVariante": p.variant,
                                                     "ModuliPosati": len(everything), "Inverter": len(inverters)})
        for h, products in self.contained.values():
            f.create_entity("IfcRelContainedInSpatialStructure", GlobalId=self.stable("contains", h.id()),
                            OwnerHistory=self.owner, RelatedElements=products, RelatingStructure=h)
        return len(everything)

    def inverters(self) -> list:
        out = []
        for unit in getattr(self.plant, "units", None) or []:
            spec = unit.spec
            label = " ".join(x for x in (getattr(spec, "manufacturer", ""), getattr(spec, "model", "")) if x) or unit.name
            key = ("inverter", self.p.variant, unit.number)
            name = f"Inverter {unit.number}: {unit.name}"
            if self.old:
                el = self.root("IfcEnergyConversionDevice", key, Name=name, ObjectType="INVERTER", Description=label)
            else:
                el = self.root("IfcTransformer", key, Name=name, ObjectType=label, PredefinedType="INVERTER")
            self.pset(el, "Meridiana_Inverter", {"Numero": int(unit.number), "Modello": label,
                                                 "Ingressi": int(unit.inputs)})
            self.contain(el, self.ground(None) * self.k)
            out.append(el)
        self.counts["inverters"] = len(out)
        return out

    def lines(self, first: int, newline: str) -> str:
        """The new records, renumbered from `first`, the stand-ins dropped and their references the original's."""
        new: dict = {}
        at = first
        for e in sorted(self.f, key=lambda e: e.id()):
            if e.id() not in self.stand:
                new[e.id()] = at
                at += 1
        ids = {**{k: v for k, v in self.stand.items() if v is not None}, **new}
        text = self.f.to_string() if hasattr(self.f, "to_string") else self.f.wrapped_data.to_string()
        body = text[text.index("DATA;") + 5:text.rindex("ENDSEC;")]
        out = []
        for line in body.splitlines():
            line = line.strip()
            m = re.match(r"#(\d+)\s*=", line)
            if m is None or int(m.group(1)) in self.stand:
                continue
            out.append(_renumber(line, ids))
        return newline.join(out) + newline


def _renumber(line: str, ids: dict) -> str:
    """`#n` -> `#ids[n]` outside the quoted strings."""
    parts = re.split(r"('(?:[^']|'')*')", line)
    for i in range(0, len(parts), 2):
        parts[i] = re.sub(r"#(\d+)", lambda m: f"#{ids[int(m.group(1))]}", parts[i])
    return "".join(parts)


def _data_end(path: Path) -> int:
    """The offset of the last ENDSEC; before END-ISO-10303-21: where the new records go."""
    size = path.stat().st_size
    with open(path, "rb") as fh:
        back = min(size, 1 << 20)
        fh.seek(size - back)
        tail = fh.read()
    end = tail.rfind(b"END-ISO-10303-21")
    at = tail.rfind(b"ENDSEC", 0, end if end >= 0 else len(tail))
    if at < 0:
        raise AppendError(_("the file has no end of its data (ENDSEC)"))
    return size - back + at


def original_of(project) -> Path:
    """The IFC the buildings were imported from (ifc_import.reference: the path the window read); AppendError when the
    project has none or the file is not there any more."""
    ref = (getattr(project, "resources", None) or {}).get("ifc_reference") or {}
    path = Path(str(ref.get("file") or ""))
    if not ref:
        raise AppendError(_("the project's buildings did not come from an IFC"))
    if not path.is_absolute() or not path.is_file():
        raise AppendError(_("the IFC the buildings came from is not where it was: {file}").format(file=path))
    return path


def append(project, results: dict, source, target, strings: dict | None = None, plant=None,
           progress: Callable[[float, str], None] | None = None) -> dict:
    """Write `target`: the IFC `source` (the architect's, the one the buildings were imported from) with the plant of
    `project` (`results`: sub-field id -> layout.Result) added, as the module's docstring says. A summary comes back;
    AppendError says why it cannot be done (no import reference, its frame lost, a plant already there)."""
    tell = progress or (lambda _f, _w: None)
    source, target = Path(source), Path(target)
    if source.resolve() == target.resolve():
        raise AppendError(_("the original is never written over: choose another file"))
    frame, why = frame_of(project)
    if frame is None:
        raise AppendError(_("the buildings were reshaped since the import: the model's frame is lost") if why == "changed"
                          else _("the project's buildings did not come from an IFC"))
    found = survey(source, lambda f: tell(0.6 * f, "survey"))
    if found["marked"]:
        raise AppendError(_("the file already holds a plant of Meridiana's: add the plant to the architect's original"))
    host = hosts(found)
    if host["project"] is None or host["context"] is None or (host["building"] is None and host["site"] is None
                                                               and not host["storeys"]):
        raise AppendError(_("the file has no project, geometric context or spatial structure to hold the plant"))
    if found["schema"].startswith("IFC2X") and host["owner"] is None:
        raise AppendError(_("an IFC2X3 file without an owner history: its new entities could not be valid"))
    metre, degrees = units(found["records"])
    tell(0.6, "plant")
    maker = _Plant(project, results, strings or {}, plant, found["schema"], host, metre, degrees, frame)
    n = maker.build()
    text = maker.lines(found["top"] + 1, found["newline"]).encode("ascii")
    at = _data_end(source)
    part = target.with_name(target.name + ".part")
    try:
        with open(source, "rb") as src, open(part, "wb") as out:
            left = at
            while left > 0:
                block = src.read(min(CHUNK, left))
                if not block:
                    break
                out.write(block)
                left -= len(block)
                tell(0.65 + 0.3 * (1 - left / max(1, at)), "copy")
            out.seek(0, 2)
            src.seek(at - 2)
            before = src.read(2)
            if not before.endswith(b"\n"):
                out.write(found["newline"].encode())
            out.write(text)
            src.seek(at)
            shutil.copyfileobj(src, out, CHUNK)
        os.replace(part, target)
    finally:
        if part.exists():
            part.unlink()
    tell(1.0, "done")
    return {"file": str(target), "schema": found["schema"], "modules": n, "classes": dict(maker.counts),
            "first_id": found["top"] + 1, "added_bytes": len(text), "insert_at": at, "bytes": target.stat().st_size,
            "unit_m": metre, "source": str(source)}
