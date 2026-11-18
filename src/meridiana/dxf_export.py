"""The plan of the plant as a DXF (R513), for AutoCAD and the free CAD programs: to lie on the architect's drawing, to
hand to the installer, to go on with in a CAD. Without Qt; the window runs it in a job with its bar.

What the file holds, each thing on a layer of its own (LAYERS: the name, the colour, the line, the weight):
- the buildings' outlines (FV-EDIFICI), the pitches with their slope and the side they face (FV-FALDE), the ridges and
  hips (FV-COLMI) and the valleys (FV-COMPLUVI), the inner line of the parapets (FV-PARAPETTI), the canopies' columns
  and beams (FV-PENSILINE);
- the obstacles that rise, with their height in a text (FV-OSTACOLI), the areas kept free and the clearances
  (FV-ESCLUSIONI);
- the modules, each a block reference whose block is the module's outline on the plan, a closed polyline, with its data
  as attributes (model, power, sub-field, string, key) (FV-MODULI); the outline of the sub-fields made by their modules
  (FV-SOTTOCAMPI);
- the strings as polylines through the middles of their modules in the order they run, dashed where they jump, each in
  the colour the plan gives it, with its name at its first module (FV-STRINGHE, FV-STRINGHE-NOMI); each string a
  named group, so that one click takes it whole; the power optimizers, a block each with its model (FV-OTTIMIZZATORI);
- the inverters and their inputs as a list beside the plan (FV-INVERTER): the project says which strings go to which
  input, not where an inverter stands;
- the main dimensions, the sides of each building (FV-QUOTE), the names and the heights (FV-TESTI), the legend, the
  north and a simple title block with the project, the date and the scale (FV-CARTIGLIO).

One layer for all the strings, the colour on each string: a plant has tens or hundreds of strings, a layer each would
bury the layer list, and the plan's colours (string_paths.colours, two strings side by side never alike) say which is
which; the group of each string selects it whole, the attribute STRINGA of the modules lets AutoCAD count them.

The coordinates (`frame`): "local", the project's own in metres (x East, y the true North, the site's point at the
origin); "utm", WGS 84 / UTM of the site's zone in metres, turned by the meridian's convergence as the IFC's map
conversion is (ifc_export, scale 1); "imported", the frame of the file the buildings came from: an IFC model
(ifc_import.reference, the same frame the IFC export writes in: ifc_export.frame_of), or a drawing whose frame the
project keeps in resources["drawing_reference"] ({"file", "unit": "m", "cm" or "mm", "origin": the drawing's point at
the project's origin, "turn": degrees anticlockwise from the project's x to the drawing's, "anchor": {"building",
"footprint"} as it was}): moved or turned since, the buildings take the frame with them. The unit is in the header
($INSUNITS) and the dimensions read in metres whatever it is.

The modules are read from the layouts (layout.Result.modules), never from the sub-fields' shapes: what is laid is what
is drawn. ezdxf (MIT) is imported only here and only when exporting: without it the program runs and says what is
missing. The file is written next to the target and renamed when whole: a stop half way leaves the old file as it was."""

from __future__ import annotations

import math
import os
import time
import zlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import geo
from .i18n import N_, _, number

FRAMES = ("local", "utm", "imported")
PARTS = ("buildings", "obstacles", "modules", "strings", "inverters", "dimensions", "sheet")
UNITS = {"m": (1.0, 6), "cm": (100.0, 5), "mm": (1000.0, 4)}        # per metre, and the $INSUNITS code
VERSION = "R2010"               # AutoCAD 2010 and later, LibreCAD, QCAD, FreeCAD, LibreOffice: true colours, UTF-8
FONT = "arial.ttf"              # a font every CAD has or replaces
SCALES = (50, 100, 200, 250, 500, 1000, 2000, 5000, 10000)
SHEET = (780.0, 520.0)          # mm of an A1 sheet for the plan, the legend beside it

# name, colour (AutoCAD's index), line type, line weight (hundredths of a mm), what it holds (the layer's description)
LAYERS = (
    ("FV-EDIFICI", 7, "Continuous", 50, N_("Building outlines")),
    ("FV-FALDE", 8, "Continuous", 18, N_("Roof pitches, with their slope and the side they face")),
    ("FV-COLMI", 30, "DASHDOT", 25, N_("Ridges and hips")),
    ("FV-COMPLUVI", 150, "DASHDOT", 25, N_("Valleys")),
    ("FV-PARAPETTI", 252, "Continuous", 25, N_("Parapets, inner line")),
    ("FV-PENSILINE", 9, "Continuous", 25, N_("Canopies: columns and beams")),
    ("FV-OSTACOLI", 1, "Continuous", 25, N_("Obstacles that rise, with their height")),
    ("FV-ESCLUSIONI", 6, "DASHED", 18, N_("Areas kept free and clearances")),
    ("FV-SOTTOCAMPI", 3, "DASHED", 35, N_("Sub-fields, outlined by their modules")),
    ("FV-MODULI", 5, "Continuous", 13, N_("PV modules (block with model, power, string)")),
    ("FV-STRINGHE", 2, "Continuous", 35, N_("Strings, through the modules in their order (dashed: a jump)")),
    ("FV-STRINGHE-NOMI", 2, "Continuous", 18, N_("String names: inverter.input.string")),
    ("FV-OTTIMIZZATORI", 40, "Continuous", 18, N_("Power optimizers")),
    ("FV-INVERTER", 211, "Continuous", 18, N_("Inverters and their inputs")),
    ("FV-QUOTE", 4, "Continuous", 13, N_("Dimensions, in metres")),
    ("FV-TESTI", 7, "Continuous", 18, N_("Names and heights")),
    ("FV-CARTIGLIO", 7, "Continuous", 25, N_("Legend, north and title block")),
)
LAYER_NAMES = tuple(name for name, *_rest in LAYERS)
MODULE_TAGS = ("MODELLO", "POTENZA_W", "SOTTOCAMPO", "STRINGA", "CHIAVE")


class Interrupted(Exception):
    """The designer stopped the export: nothing written."""


class Missing(RuntimeError):
    """ezdxf is not installed."""


def available() -> bool:
    import importlib.util
    return importlib.util.find_spec("ezdxf") is not None


@dataclass(frozen=True)
class Frame:
    """How a point of the plan (metres, x East, y North) becomes a point of the file: scale * R(turn) p + move."""
    key: str = "local"
    turn: float = 0.0               # radians, anticlockwise
    move: tuple = (0.0, 0.0)
    scale: float = 1.0              # the file's units in a metre
    unit: str = "m"
    label: str = ""                 # what the coordinates are, in words (the title block)

    def __call__(self, x: float, y: float) -> tuple[float, float]:
        c, s = math.cos(self.turn), math.sin(self.turn)
        return (self.move[0] + self.scale * (c * x - s * y), self.move[1] + self.scale * (s * x + c * y))

    def back(self, x: float, y: float) -> tuple[float, float]:
        """The point of the plan a point of the file comes from."""
        c, s = math.cos(self.turn), math.sin(self.turn)
        dx, dy = (x - self.move[0]) / self.scale, (y - self.move[1]) / self.scale
        return (c * dx + s * dy, -s * dx + c * dy)

    def degrees(self, angle: float) -> float:
        return angle + math.degrees(self.turn)


def _rotate(v, a: float) -> tuple[float, float]:
    c, s = math.cos(a), math.sin(a)
    return (c * v[0] - s * v[1], s * v[0] + c * v[1])


def _drawing(project, ref: dict) -> tuple[Frame | None, str]:
    from .ifc_export import _rigid
    unit = str(ref.get("unit") or "m")
    if unit not in UNITS:
        return None, _("the drawing's unit «{unit}» is not one Meridiana knows").format(unit=unit)
    scale = UNITS[unit][0]
    turn = math.radians(float(ref.get("turn") or 0.0))
    ox, oy = (list(ref.get("origin") or [0.0, 0.0]) + [0.0, 0.0])[:2]
    a, tx, ty = 0.0, 0.0, 0.0
    anchor = ref.get("anchor") or {}
    if anchor:
        b = next((b for b in project.buildings if b.id == anchor.get("building")), None)
        moved = _rigid(anchor.get("footprint") or [], b.footprint) if b is not None else None
        if moved is None:
            return None, _("the buildings were reshaped since they came from {file}: its coordinates no longer "
                           "hold").format(file=ref.get("file") or _("the drawing"))
        a, tx, ty = moved
    phi = turn - a                    # drawing = origin + s R(turn) R(-a) (p - t)
    rx, ry = _rotate((tx, ty), phi)
    label = _("the coordinates of the drawing {file}").format(file=ref.get("file") or "")
    return Frame("imported", phi, (float(ox) - scale * rx, float(oy) - scale * ry), scale, unit, label.strip()), ""


def frame_of(project, key: str = "local") -> tuple[Frame | None, str]:
    """The frame `key` for `project`: (the Frame, "") or (None, why it cannot be used)."""
    if key == "local":
        return Frame("local", 0.0, (0.0, 0.0), 1.0, "m", _("the project's own coordinates, metres from the site's "
                                                             "point, y to the true North")), ""
    if key == "utm":
        zone, east, north, gamma, _k = geo.to_utm(project.site.lat, project.site.lon)
        south = project.site.lat < 0
        code = (32700 if south else 32600) + zone
        return Frame("utm", math.radians(gamma), (east, north), 1.0, "m",
                     _("WGS 84 / UTM zone {zone} (EPSG:{code}), metres").format(
                         zone=f"{zone}{'S' if south else 'N'}", code=code)), ""
    if key != "imported":
        raise ValueError(f"frame: {key!r}")
    from . import ifc_export
    ref, note = ifc_export.frame_of(project)
    if ref is not None:
        mx, my = ref["move"]
        return Frame("imported", float(ref["turn"]), (float(mx), float(my)), 1.0, "m",
                     _("the coordinates of the IFC model {file}").format(file=ref.get("file") or "").strip()), ""
    if note == "changed":
        return None, _("the buildings were reshaped since they came from the IFC model: its coordinates no longer hold")
    drawing = (getattr(project, "resources", None) or {}).get("drawing_reference")
    if isinstance(drawing, dict):
        return _drawing(project, drawing)
    return None, _("the buildings did not come from a file")


def frame_choices(project) -> list[dict]:
    """The three frames for the export's options: {"key", "text", "enabled", "why"}."""
    texts = {"local": _("Local coordinates of the project (m)"), "utm": _("UTM coordinates of the site (m)"),
             "imported": _("Coordinates of the file the buildings came from")}
    out = []
    for key in FRAMES:
        frame, why = frame_of(project, key)
        text = texts[key] if frame is None or key != "imported" else f"{texts[key]}: {frame.label}"
        out.append({"key": key, "text": text, "enabled": frame is not None, "why": why})
    return out


def part_names() -> dict:
    return {"buildings": _("Buildings, pitches, ridges and parapets"), "obstacles": _("Obstacles and areas kept free"),
            "modules": _("Modules and sub-fields"), "strings": _("Strings and optimizers"),
            "inverters": _("Inverters and their inputs"), "dimensions": _("Main dimensions"),
            "sheet": _("Legend, north and title block")}


def part_list() -> list[dict]:
    return [{"key": k, "text": v} for k, v in part_names().items()]


def words() -> dict:
    """The words of the export's dialogs, the same in both interfaces."""
    return {"dxfTitle": _("Export the plan as DXF"), "dxfPlan": _("DXF, the plan of the plant (*.dxf)"),
            "dxfCoordinates": _("Coordinates"), "dxfWhat": _("What goes in the plan"),
            "dxfUnits": _("The unit is written in the file: metres, or the drawing's own. The dimensions read in "
                          "metres."),
            "dxfExport": _("Export"), "cancel": _("Cancel")}


def _nearest_aci(rgb) -> int:
    from ezdxf.colors import DXF_DEFAULT_COLORS, int2rgb
    best, index = None, 7
    for i in range(1, 256):
        r, g, b = int2rgb(DXF_DEFAULT_COLORS[i])
        d = (r - rgb[0]) ** 2 + (g - rgb[1]) ** 2 + (b - rgb[2]) ** 2
        if best is None or d < best:
            best, index = d, i
    return index


def _hex(colour: str) -> tuple[int, int, int]:
    c = colour.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


class Writer:
    """One export: the drawing in the making. `results` maps a sub-field's id to its layout.Result; `plant`
    (energy.plant.Plant) gives the strings, the optimizers and the inverters."""

    def __init__(self, project, results: dict, plant=None, frame: str = "local", parts=PARTS,
                 progress: Callable[[float, str], None] | None = None):
        try:
            import ezdxf
        except ImportError as error:
            raise Missing(_("ezdxf is not installed: the DXF export needs it (pip install ezdxf)")) from error
        self.ezdxf = ezdxf
        self.p = project
        self.results = {k: v for k, v in (results or {}).items() if not isinstance(v, Exception)}
        self.plant = plant
        self.parts = set(parts)
        unknown = self.parts - set(PARTS)
        if unknown:
            raise ValueError(f"parts: {sorted(unknown)}")
        self.frame, why = frame_of(project, frame)
        if self.frame is None:
            raise ValueError(why)
        self.tell = progress or (lambda _f, _w: None)
        self.counts: dict[str, int] = {}
        self.modules_drawn = 0
        self.strings_drawn = 0

    # small things

    def u(self, metres: float) -> float:
        """A length of the plan in the file's units."""
        return metres * self.frame.scale

    def paper(self, mm: float) -> float:
        """A size on the printed sheet at the drawing's scale, in the file's units."""
        return self.u(mm / 1000.0 * self.ratio)

    def count(self, layer: str, n: int = 1) -> None:
        self.counts[layer] = self.counts.get(layer, 0) + n

    def ring(self, pts, layer: str, closed: bool = True, attribs: dict | None = None):
        pts = [self.frame(float(x), float(y)) for x, y in pts]
        if len(pts) < 2:
            return None
        e = self.msp.add_lwpolyline(pts, close=closed, dxfattribs={"layer": layer, **(attribs or {})})
        self.count(layer)
        return e

    def text(self, words: str, at, height: float, layer: str, angle: float = 0.0, attribs: dict | None = None,
             align: str = "MIDDLE_CENTER", plan: bool = True):
        from ezdxf.enums import TextEntityAlignment
        # the place follows the plan, the words stay level in the file's axes: they read in the drawing as it is
        where = self.frame(*at) if plan else at
        e = self.msp.add_text(words, height=height, rotation=angle,
                              dxfattribs={"layer": layer, "style": "MERIDIANA", **(attribs or {})})
        e.set_placement(where, align=getattr(TextEntityAlignment, align))
        self.count(layer)
        return e

    # the drawing

    def setup(self) -> None:
        ezdxf = self.ezdxf
        self.doc = ezdxf.new(VERSION, setup=["linetypes"])
        doc = self.doc
        scale, insunits = UNITS[self.frame.unit]
        doc.units = insunits
        doc.header["$INSUNITS"] = insunits
        doc.header["$MEASUREMENT"] = 1            # metric
        doc.header["$LUNITS"] = 2                 # decimal
        doc.header["$LUPREC"] = 3 if self.frame.unit == "m" else 0
        doc.header["$LTSCALE"] = float(scale)
        doc.header["$PROJECTNAME"] = str(self.p.name)
        doc.styles.add("MERIDIANA", font=FONT)
        for name, colour, ltype, weight, description in LAYERS:
            layer = doc.layers.add(name, color=colour, linetype=ltype, lineweight=weight)
            layer.description = _(description)
        self.msp = doc.modelspace()
        # the plan's size gives the scale of the sheet: the texts, the dimensions, the title block follow it
        xs, ys = [], []
        for b in self.p.buildings:
            xs += [float(q[0]) for q in b.footprint]
            ys += [float(q[1]) for q in b.footprint]
        for r in self.results.values():
            for m in r.modules:
                xs += [q[0] for q in m.corners]
                ys += [q[1] for q in m.corners]
        width = (max(xs) - min(xs)) if xs else 10.0
        height = (max(ys) - min(ys)) if ys else 10.0
        self.ratio = next((s for s in SCALES if width * 1000.0 / s <= SHEET[0] and height * 1000.0 / s <= SHEET[1]),
                          SCALES[-1])
        style = doc.dimstyles.new("MERIDIANA")
        style.dxf.dimtxsty = "MERIDIANA"
        style.dxf.dimtxt = self.paper(2.5)
        style.dxf.dimasz = self.paper(2.5)
        style.dxf.dimexo = self.paper(1.0)
        style.dxf.dimexe = self.paper(1.5)
        style.dxf.dimgap = self.paper(0.8)
        style.dxf.dimtad = 1                      # the text above the line
        style.dxf.dimdec = 2
        style.dxf.dimdsep = ord(",")
        style.dxf.dimlfac = 1.0 / scale           # the dimensions read in metres in any unit
        style.dxf.dimtih = 0
        style.dxf.dimtoh = 0
        style.dxf.dimzin = 8

    def buildings(self) -> None:
        import shapely
        from shapely.geometry import Polygon
        from . import model, roofs
        n = max(1, len(self.p.buildings))
        for i, b in enumerate(self.p.buildings):
            self.tell(0.05 + 0.2 * i / n, b.name)
            self.ring(b.footprint, "FV-EDIFICI")
            centre = Polygon(b.footprint).representative_point()
            self.text(f"{b.name}", (centre.x, centre.y), self.paper(3.5), "FV-TESTI")
            said = _("h {h} m").format(h=number(b.height, 2))
            if b.base > 0:                      # R453: a body standing above the ground
                said += " " + _("from {h} m").format(h=number(b.base, 2))
            self.text(said, (centre.x, centre.y - self.paper(5.0) / self.frame.scale), self.paper(2.0), "FV-TESTI")
            pitches = b.pitches()
            sloped = [pt for pt in pitches if pt.tilt > 0]
            if sloped or len(pitches) > 1:
                for pt in pitches:
                    self.ring(pt.ring, "FV-FALDE")
                    if pt.tilt > 0 and len(pt.ring) >= 3:
                        c = Polygon(pt.ring).representative_point()
                        fx, fy = geo.facing_vector(pt.azimuth)
                        arrow = self.paper(8.0) / self.frame.scale
                        self.msp.add_lwpolyline([self.frame(c.x - fx * arrow / 2, c.y - fy * arrow / 2),
                                                 self.frame(c.x + fx * arrow / 2, c.y + fy * arrow / 2)],
                                                dxfattribs={"layer": "FV-FALDE"})
                        head = arrow * 0.25
                        tip = (c.x + fx * arrow / 2, c.y + fy * arrow / 2)
                        left, right = _rotate((-fx, -fy), math.radians(25)), _rotate((-fx, -fy), math.radians(-25))
                        self.msp.add_lwpolyline([self.frame(tip[0] + left[0] * head, tip[1] + left[1] * head),
                                                 self.frame(*tip),
                                                 self.frame(tip[0] + right[0] * head, tip[1] + right[1] * head)],
                                                dxfattribs={"layer": "FV-FALDE"})
                        self.count("FV-FALDE", 2)
                        self.text(_("{tilt}°, az. {azimuth}°").format(tilt=number(pt.tilt, 1),
                                                                     azimuth=number(pt.azimuth, 1)),
                                  (c.x, c.y - arrow * 0.6), self.paper(1.8), "FV-TESTI")
            for a, z in roofs.ridges(pitches, b.height):
                self.ring([a, z], "FV-COLMI", closed=False)
            self._hips_and_valleys(b, pitches, shapely)
            if b.parapet > 0 and b.roof.type == "flat":
                quads = [Polygon(q) for q in model.parapet_quads(b.footprint)]
                band = shapely.unary_union(quads) if quads else None
                if band is not None and not band.is_empty:
                    for poly in getattr(band, "geoms", [band]):
                        for hole in poly.interiors:
                            self.ring(list(hole.coords)[:-1], "FV-PARAPETTI")
                    self.text(_("parapet h {h} m").format(h=number(b.parapet, 2)),
                              (centre.x, centre.y - 2 * self.paper(5.0) / self.frame.scale), self.paper(1.8),
                              "FV-TESTI")
            if b.canopy is not None:
                from . import canopies
                for o in canopies.structure(b):
                    self.ring(o["ring"], "FV-PENSILINE")

    def _hips_and_valleys(self, b, pitches, shapely) -> None:
        """The sloping lines two pitches share: a hip where both go down from it, a valley where both come down to
        it. The level ones are the ridges (roofs.ridges)."""
        from shapely.geometry import LineString, Polygon
        polys = [Polygon(pt.ring) for pt in pitches]
        for i in range(len(pitches)):
            for j in range(i + 1, len(pitches)):
                shared = polys[i].boundary.intersection(polys[j].boundary)
                for part in getattr(shared, "geoms", [shared]):
                    if not isinstance(part, LineString) or part.length < 0.05:
                        continue
                    (ax, ay), (zx, zy) = part.coords[0], part.coords[-1]
                    a, z = pitches[i], pitches[j]
                    if abs(a.z(ax, ay) - a.z(zx, zy)) < 1e-6:
                        continue                    # level: a ridge, drawn as such
                    mx, my = (ax + zx) / 2, (ay + zy) / 2
                    downs = []
                    for pt, poly in ((a, polys[i]), (z, polys[j])):
                        inside = poly.representative_point()
                        dx, dy = inside.x - mx, inside.y - my
                        fx, fy = geo.facing_vector(pt.azimuth)
                        downs.append(dx * fx + dy * fy > 0)
                    self.ring([(ax, ay), (zx, zy)], "FV-COLMI" if all(downs) else "FV-COMPLUVI", closed=False)

    def obstacles(self) -> None:
        from shapely.geometry import Polygon
        from . import model
        names = model.exclusion_names()
        for e in self.p.exclusions:
            if len(e.ring) < 3:
                continue
            h = e.obstacle_height()
            layer = "FV-OSTACOLI" if h > 0 else "FV-ESCLUSIONI"
            self.ring(e.ring, layer)
            if e.clearance > 0:
                grown = Polygon(e.ring).buffer(e.clearance, join_style="mitre")
                if not grown.is_empty and grown.geom_type == "Polygon":
                    self.ring(list(grown.exterior.coords)[:-1], "FV-ESCLUSIONI")
            c = Polygon(e.ring).representative_point()
            words = names.get(e.kind, e.kind)
            if h > 0:
                words = _("{what} h {h} m").format(what=words, h=number(h, 2))
            self.text(words, (c.x, c.y), self.paper(1.8), "FV-TESTI")
        for x in self.p.props:
            if not x.casts_shadow():
                continue
            try:
                ring, height = x.footprint(), x.measures()["height"]
            except ValueError:
                continue
            self.ring(ring, "FV-OSTACOLI")
            self.text(_("{what} h {h} m").format(what=self.p.prop_label(x), h=number(height, 2)),
                      (float(x.at[0]), float(x.at[1])), self.paper(1.8), "FV-TESTI")

    # the modules and the strings

    def _laid(self):
        """The modules laid, in the plan's order: [(sub-field, result, module)]."""
        out = []
        for sf in self.p.subfields:
            r = self.results.get(sf.id)
            if r is None:
                continue
            out.extend((sf, r, m) for m in r.modules)
        return out

    def _module_block(self, w: float, h: float) -> str:
        key = (round(w, 4), round(h, 4))
        name = self.blocks.get(key)
        if name is None:
            from ezdxf import const
            name = f"FV_MODULO_{len(self.blocks) + 1}"
            block = self.doc.blocks.new(name=name)
            sw, sh = self.u(w) / 2, self.u(h) / 2
            block.add_lwpolyline([(-sw, -sh), (sw, -sh), (sw, sh), (-sw, sh)], close=True,
                                 dxfattribs={"layer": "0", "color": 0})
            for k, tag in enumerate(MODULE_TAGS):
                block.add_attdef(tag, insert=(-sw, sh - (k + 1) * self.u(h) / 8), height=self.u(h) / 10,
                                 dxfattribs={"layer": "0", "color": 0, "flags": const.ATTRIB_INVISIBLE,
                                             "style": "MERIDIANA"})
            self.blocks[key] = name
        return name

    def modules(self) -> None:
        from shapely import unary_union
        from shapely.geometry import Polygon
        laid = self._laid()
        self.blocks: dict = {}
        total = max(1, len(laid))
        by_sf: dict = {}
        for n, (sf, r, m) in enumerate(laid):
            if n % 200 == 0:
                self.tell(0.3 + 0.4 * n / total, sf.name)
            data = self.p.modules.get(sf.module) or {}
            mod = self.p.module_of(sf)
            c = [tuple(map(float, q)) for q in m.corners]
            e1 = (c[1][0] - c[0][0], c[1][1] - c[0][1])
            e2 = (c[2][0] - c[1][0], c[2][1] - c[1][1])
            w, h = math.hypot(*e1), math.hypot(*e2)
            square = w > 0 and h > 0 and abs(e1[0] * e2[0] + e1[1] * e2[1]) <= 1e-6 * w * h
            values = {"MODELLO": f"{data.get('manufacturer', '')} {data.get('model', sf.module)}".strip(),
                      "POTENZA_W": number(float(mod.power_kw) * 1000.0, 0),
                      "SOTTOCAMPO": sf.name, "STRINGA": self.labels.get((sf.id, m.key), ""), "CHIAVE": m.key}
            if square:
                cx, cy = sum(q[0] for q in c) / 4, sum(q[1] for q in c) / 4
                ref = self.msp.add_blockref(self._module_block(w, h), self.frame(cx, cy),
                                            dxfattribs={"layer": "FV-MODULI",
                                                        "rotation": self.frame.degrees(math.degrees(math.atan2(*e1[::-1])))})
                ref.add_auto_attribs(values)
                self.count("FV-MODULI")
            else:                       # a module on a row that does not run level: its outline as it is
                self.ring(c, "FV-MODULI")
            self.modules_drawn += 1
            by_sf.setdefault(sf.id, (sf, r, mod, []))[3].append(Polygon(c))
        for sf, r, mod, polys in by_sf.values():
            gap = max(0.3, float(getattr(r, "pitch", 0.0) or 0.0) * 0.6, max(mod.length, mod.width) * 0.6)
            outline = unary_union([q.buffer(gap, join_style="mitre") for q in polys]).buffer(-gap, join_style="mitre")
            for poly in getattr(outline, "geoms", [outline]):
                if poly.is_empty:
                    continue
                self.ring(list(poly.exterior.coords)[:-1], "FV-SOTTOCAMPI")
            # the name above the outline's top left corner, in the file's axes: off the modules and the building's name
            corners = [self.frame(x, y) for x, y in outline.envelope.exterior.coords] if not outline.is_empty else []
            if corners:
                kwp = len(polys) * float(mod.power_kw)
                spot = (min(c[0] for c in corners), max(c[1] for c in corners) + self.paper(2.0))
                self.text(_("{name}: {n} modules, {kwp} kWp").format(name=sf.name, n=len(polys), kwp=number(kwp, 2)),
                          spot, self.paper(2.5), "FV-TESTI", attribs={"color": 3}, align="BOTTOM_LEFT", plan=False)

    def strings(self) -> None:
        import numpy as np
        from . import string_paths, theme_colors
        from .energy import optimizers
        laid = self._laid()
        if not laid or self.plant is None or not getattr(self.plant, "strings", None):
            return
        index = {(sf.id, m.key): i for i, (sf, _r, m) in enumerate(laid)}
        router = string_paths.Router(np.asarray([m.corners for _sf, _r, m in laid], dtype=float))
        strings = [s for s in self.plant.strings if s.modules]
        orders = [[index[(sf, key)] for sf, key, _c in s.modules if (sf, key) in index] for s in strings]
        tints = theme_colors.string_tints(theme_colors.PRESETS["indigo"])
        seeds = [zlib.crc32(s.keys[0].encode()) for s in strings]
        colours = [tints[c] for c in string_paths.colours(orders, router, len(tints), seeds)]
        units = {u.number: u for u in getattr(self.plant, "units", []) or []}
        from .energy import faces
        face_of = faces.faces_of(self.p)
        size = router.size
        names: set = set()
        for n, (s, order, colour) in enumerate(zip(strings, orders, colours, strict=True)):
            if not order:
                continue
            if n % 20 == 0:
                self.tell(0.7 + 0.15 * n / max(1, len(strings)), s.label)
            rgb = _hex(colour)
            look = {"true_color": (rgb[0] << 16) | (rgb[1] << 8) | rgb[2], "color": _nearest_aci(rgb)}
            made = []
            unit = units.get(s.inverter)
            # the optimizers of an inverter with MPPT too (R456); on some modules only, the string drawn as a plain one
            # and an optimizer on each module that has one
            mlpe = unit is not None and getattr(unit, "mlpe", None) is not None and unit.mlpe.family.function == "optimizer"
            some = getattr(s, "optimized", None)
            if unit is not None and ((unit.optimized and unit.choice is not None) or (mlpe and some is None)):
                made += self._optimizers(s, order, unit, router, look, optimizers, string_paths)
            else:
                run: list = []
                for points, jump in router.legs(order) if len(order) > 1 else []:
                    if jump:
                        if len(run) > 1:
                            made.append(self.ring(run, "FV-STRINGHE", closed=False, attribs=look))
                        made.append(self.ring(points, "FV-STRINGHE", closed=False,
                                              attribs={**look, "linetype": "DASHED"}))
                        run = []
                    else:
                        run = run + list(points) if not run else run + list(points[1:])
                if len(run) > 1:
                    made.append(self.ring(run, "FV-STRINGHE", closed=False, attribs=look))
                if mlpe and some:
                    made += self._optimizers(s, order, unit, router, look, optimizers, string_paths, only=set(some))
            # R433: the polyline goes on over the faces; where it changes face, a diamond on the string's layer
            pairs = [(index[(sf, key)], sf) for sf, key, _c in s.modules if (sf, key) in index]
            for (at, a), (bt, b) in zip(pairs, pairs[1:], strict=False):
                fa, fb = face_of.get(a), face_of.get(b)
                if fa is None or fb is None or faces.same_face(fa, fb):
                    continue
                (ax, ay), (bx, by) = map(float, router.centres[at]), map(float, router.centres[bt])
                mx, my, r = (ax + bx) / 2, (ay + by) / 2, size * 0.15
                made.append(self.ring([(mx, my + r), (mx + r, my), (mx, my - r), (mx - r, my)], "FV-STRINGHE",
                                      attribs=look))
            x0, y0 = map(float, router.centres[order[0]])
            start = self.msp.add_circle(self.frame(x0, y0), self.u(size * 0.18),
                                        dxfattribs={"layer": "FV-STRINGHE", **look})
            self.count("FV-STRINGHE")
            made.append(start)
            made.append(self.text(s.label, (x0, y0), self.u(min(size * 0.32, self.paper(1.8) / self.frame.scale)),
                                  "FV-STRINGHE-NOMI", attribs=look))
            name = "STRINGA_" + s.label.replace(".", "-").replace("?", "X")
            while name in names:
                name += "_"
            names.add(name)
            group = self.doc.groups.new(name, description=_("String {label}").format(label=s.label))
            group.extend([e for e in made if e is not None])
            self.strings_drawn += 1

    def _optimizers(self, s, order, unit, router, look, optimizers, string_paths, only=None) -> list:
        """With power optimizers the string runs from unit to unit, a thin line from each unit to its modules (as the
        plan draws it, R424); with `only` (R456: on some modules only) an optimizer on each of those modules, the string
        drawn by the caller."""
        from ezdxf import const
        choice = unit.choice if unit.optimized else unit.mlpe
        if only is not None:
            refs = [f"{sf}/{key}" for sf, key, _c in s.modules]
            groups = [[at] for at, ref in zip(order, refs, strict=False) if ref in only]
        else:
            try:
                groups = optimizers.module_groups(order, choice.per, s.optimizer_group_sizes or None)
            except ValueError:
                groups = optimizers.module_groups(order, choice.per)
        placed = string_paths.optimizer_units(router.quads, groups)
        if "FV_OTTIMIZZATORE" not in self.doc.blocks:
            block = self.doc.blocks.new(name="FV_OTTIMIZZATORE")
            block.add_lwpolyline([(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)], close=True,
                                 dxfattribs={"layer": "0", "color": 0})
            block.add_line((-0.5, -0.5), (0.5, 0.5), dxfattribs={"layer": "0", "color": 0})
            for k, tag in enumerate(("MODELLO", "STRINGA")):
                block.add_attdef(tag, insert=(-0.5, -0.5 - 0.3 * (k + 1)), height=0.2,
                                 dxfattribs={"layer": "0", "color": 0, "flags": const.ATTRIB_INVISIBLE,
                                             "style": "MERIDIANA"})
        made = []
        name = getattr(choice.optimizer, "name", "") or ""
        for (x, y, ux, uy, side), group in zip(placed, groups, strict=True):
            ref = self.msp.add_blockref("FV_OTTIMIZZATORE", self.frame(x, y), dxfattribs={
                "layer": "FV-OTTIMIZZATORI", "xscale": self.u(side), "yscale": self.u(side),
                "rotation": self.frame.degrees(math.degrees(math.atan2(uy, ux)))})
            ref.add_auto_attribs({"MODELLO": name, "STRINGA": s.label})
            self.count("FV-OTTIMIZZATORI")
            made.append(ref)
            for at in group:
                made.append(self.ring([(x, y), tuple(map(float, router.centres[at]))], "FV-OTTIMIZZATORI",
                                      closed=False))
        points = [(float(u[0]), float(u[1])) for u in placed]
        if len(points) > 1 and only is None:
            made.append(self.ring(points, "FV-STRINGHE", closed=False, attribs=look))
        return made

    def dimensions(self) -> None:
        from . import mesh
        for b in self.p.buildings:
            ring = [tuple(map(float, q)) for q in b.footprint]
            if len(ring) < 3:
                continue
            if mesh.signed_area(ring) < 0:
                ring.reverse()
            sides = list(zip(ring, ring[1:] + ring[:1], strict=True))
            longest = sorted(sides, key=lambda s: -math.dist(*s))[:8]
            for a, z in sides:
                if (a, z) not in longest or math.dist(a, z) < 2.0:
                    continue
                p1, p2 = self.frame(*a), self.frame(*z)
                out = (p2[1] - p1[1], p1[0] - p2[0])          # outwards: the ring runs anticlockwise
                if not -90.0 < math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0])) <= 90.0:
                    p1, p2 = p2, p1                             # the text reads from the left or from below
                left = (p1[1] - p2[1], p2[0] - p1[0])
                side = 1.0 if left[0] * out[0] + left[1] * out[1] > 0 else -1.0
                dim = self.msp.add_aligned_dim(p1=p1, p2=p2, distance=side * self.paper(8.0),
                                               dimstyle="MERIDIANA", dxfattribs={"layer": "FV-QUOTE"})
                dim.render()
                self.count("FV-QUOTE")

    # beside the plan

    def sheet(self, inverters: bool, legend: bool) -> None:
        from ezdxf import bbox
        box = bbox.extents(self.msp, fast=True)
        if not box.has_data:
            return
        x0, y1 = box.extmax.x + self.paper(20.0), box.extmax.y
        line = self.paper(5.0)
        y = y1
        if legend:
            self.text(_("Legend"), (x0, y), self.paper(3.5), "FV-CARTIGLIO", align="LEFT", plan=False)
            y -= line * 1.6
            for name, _colour, _ltype, _weight, description in LAYERS:
                if not self.counts.get(name) or name == "FV-CARTIGLIO":
                    continue
                self.msp.add_line((x0, y + line * 0.3), (x0 + self.paper(12.0), y + line * 0.3),
                                  dxfattribs={"layer": name})
                self.text(f"{name}: {_(description)}", (x0 + self.paper(15.0), y), self.paper(2.0), "FV-CARTIGLIO",
                          align="LEFT", plan=False)
                y -= line
            y -= line
        if inverters and self.plant is not None and getattr(self.plant, "units", None):
            self.text(_("Inverters and their inputs"), (x0, y), self.paper(3.5), "FV-INVERTER", align="LEFT",
                      plan=False)
            y -= line * 1.6
            by_input: dict = {}
            for s in self.plant.strings:
                by_input.setdefault((s.inverter, s.mppt), []).append(s)
            for u in self.plant.units:
                self.text(_("Inverter {n}: {name}").format(n=u.number, name=u.name), (x0, y), self.paper(2.5),
                          "FV-INVERTER", align="LEFT", plan=False)
                y -= line
                for k in range(1, u.inputs + 1):
                    found = by_input.get((u.number, k), [])
                    words = ", ".join(_("{label} ({n} modules)").format(label=s.label, n=len(s.modules)) for s in found)
                    self.text(_("Input {k}: {strings}").format(k=k, strings=words or _("free")),
                              (x0 + self.paper(5.0), y), self.paper(2.0), "FV-INVERTER", align="LEFT", plan=False)
                    y -= line
                y -= line * 0.4
            y -= line
        if legend:
            self._north(x0 + self.paper(10.0), y - self.paper(15.0))
            self._title(x0, y - self.paper(40.0))

    def _north(self, x: float, y: float) -> None:
        """An arrow to the true North (the plan's +y) at (x, y) of the file."""
        length = self.paper(20.0)
        nx, ny = _rotate((0.0, 1.0), self.frame.turn)
        tip = (x + nx * length / 2, y + ny * length / 2)
        tail = (x - nx * length / 2, y - ny * length / 2)
        side = _rotate((nx, ny), math.radians(90))
        self.msp.add_lwpolyline([tail, (tip[0], tip[1])], dxfattribs={"layer": "FV-CARTIGLIO"})
        head = length * 0.3
        self.msp.add_lwpolyline([(tip[0] - nx * head + side[0] * head * 0.4, tip[1] - ny * head + side[1] * head * 0.4),
                                 tip,
                                 (tip[0] - nx * head - side[0] * head * 0.4, tip[1] - ny * head - side[1] * head * 0.4)],
                                close=True, dxfattribs={"layer": "FV-CARTIGLIO"})
        self.text("N", (tip[0] + nx * self.paper(4.0), tip[1] + ny * self.paper(4.0)), self.paper(4.0),
                  "FV-CARTIGLIO", angle=0.0, plan=False)
        self.count("FV-CARTIGLIO", 2)

    def _title(self, x: float, top: float) -> None:
        from . import __version__
        w, h = self.paper(180.0), self.paper(56.0)
        self.msp.add_lwpolyline([(x, top), (x + w, top), (x + w, top - h), (x, top - h)], close=True,
                                dxfattribs={"layer": "FV-CARTIGLIO"})
        self.count("FV-CARTIGLIO")
        laid = self._laid()
        kwp = sum(float(self.p.module_of(sf).power_kw) for sf, _r, _m in laid)
        rows = [(self.p.name, 5.0),
                (_("Plan of the photovoltaic plant"), 3.5),
                (_("{n} modules, {kwp} kWp").format(n=len(laid), kwp=number(kwp, 2)), 2.5),
                (_("Date: {date}").format(date=time.strftime("%d/%m/%Y")) + "    " +
                 _("Scale 1:{n} (A1)").format(n=self.ratio), 2.5),
                (_("Coordinates: {what}").format(what=self.frame.label), 2.0),
                (_("Drawn with Meridiana {version}").format(version=__version__), 2.0)]
        if getattr(self.p, "job_id", ""):
            rows.insert(1, (_("Job {job}").format(job=self.p.job_id), 2.5))
        y = top - self.paper(8.0)
        for words, size in rows:
            self.text(words, (x + self.paper(5.0), y), self.paper(size), "FV-CARTIGLIO", align="LEFT", plan=False)
            y -= self.paper(size * 1.9)

    def write(self, path: Path) -> dict:
        self.tell(0.0, "project")
        self.setup()
        self.labels = {}
        for s in getattr(self.plant, "strings", None) or []:
            for sf, key, _c in s.modules:
                self.labels[(sf, key)] = s.label
        if "buildings" in self.parts:
            self.buildings()
        if "obstacles" in self.parts:
            self.obstacles()
        if "modules" in self.parts:
            self.modules()
        if "strings" in self.parts:
            self.strings()
        if "dimensions" in self.parts:
            self.tell(0.86, "dimensions")
            self.dimensions()
        if "sheet" in self.parts or "inverters" in self.parts:
            self.sheet("inverters" in self.parts, "sheet" in self.parts)
        from ezdxf import bbox
        box = bbox.extents(self.msp, fast=True)
        if box.has_data:
            self.doc.header["$EXTMIN"] = (box.extmin.x, box.extmin.y, 0.0)
            self.doc.header["$EXTMAX"] = (box.extmax.x, box.extmax.y, 0.0)
            self.doc.set_modelspace_vport(max(box.size.y, box.size.x * 0.6) * 1.1, center=(box.center.x, box.center.y))
        self.tell(0.92, "file")
        path = Path(path)
        part = path.with_name(path.name + ".part")
        try:
            self.doc.saveas(str(part), encoding="utf-8")
            os.replace(part, path)
        finally:
            if part.exists():
                part.unlink()
        self.tell(1.0, "done")
        return {"file": str(path), "version": VERSION, "frame": self.frame.key, "unit": self.frame.unit,
                "label": self.frame.label, "modules": self.modules_drawn, "strings": self.strings_drawn,
                "buildings": len(self.p.buildings) if "buildings" in self.parts else 0, "layers": dict(self.counts),
                "scale": self.ratio, "bytes": path.stat().st_size}


def export(project, results: dict, path, plant=None, frame: str = "local", parts=PARTS,
           progress: Callable[[float, str], None] | None = None) -> dict:
    """Write the plan of `project` with the layouts `results` (sub-field id -> layout.Result) to `path` as a DXF, in the
    coordinates `frame` ("local", "utm", "imported": the module's docstring), with the `parts` asked (PARTS);
    `plant` (energy.plant.Plant) gives the strings, the optimizers and the inverters. `progress(fraction, what)` is told
    along the way and may raise Interrupted to stop: nothing is written then. A summary comes back."""
    return Writer(project, results, plant, frame, parts, progress).write(Path(path))


def export_project(project, path, known: dict | None = None, frame: str = "local", parts=PARTS,
                   progress: Callable[[float, str], None] | None = None) -> dict:
    """The layouts of `project` (those in `known`, id -> (key, result), kept), its plant (the strings proposed or the
    designer's), then the plan at `path`: what both interfaces run, the window in a job, the Quick one in its process."""
    from . import jobs, log
    from .energy import plant as plant_model
    results, _keys, _laid = jobs.layout_of(project, known or {})
    plant = None
    try:
        plant = plant_model.build(project, results, check=False)
    except Exception as error:              # noqa: BLE001  the strings are a part: the plan goes without them
        log.complain("dxf strings", error)
    return export(project, results, path, plant=plant, frame=frame, parts=parts, progress=progress)


def audit(path) -> list[str]:
    """What ezdxf's audit finds wrong in the file at `path`: [] for a clean file."""
    import ezdxf
    doc = ezdxf.readfile(str(path))
    auditor = doc.audit()
    return [f"{e.code}: {e.message}" for e in auditor.errors]
