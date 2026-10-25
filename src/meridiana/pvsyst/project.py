"""A PVsyst project as data: the site and settings of its .PRJ, the variants found next to it (<project>.VC0,
.VC1...), and, for a variant, its orientations, sub-arrays, losses, circuit, system, the PV fields of its 3D
scene and its monthly results. Units are converted here, key by key, as PVsyst's dialogs and reports show
them (docs/studio/10-pvsyst-formati-file.md, 3.2 and 3.3): SoilingLoss is a fraction, LIDLoss a percentage,
RSCablagePC a percentage at STC. PVsyst does not write a key whose value is the default: the defaults of
the keys read here are in DEFAULTS."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import pvobject, records
from .pvobject import Node, number, numbers

DEFAULTS = {"AzimPlR": 0.0, "FieldAzim": 0.0, "UVFactor": 0.0, "PMismString": 0.0, "SoilingLoss": 0.0,
            "LIDLoss": 0.0, "PQualityModP": 0.0, "PMismMPP": 0.0, "RSCablagePC": 0.0, "NInverter": 1.0,
            "NElements": 1.0, "BaseSlope": 0.0, "ModSpacingX": 0.0, "ModSpacingY": 0.0, "NModInHeight": 1.0}
# the results summed for the comparison: irradiations in MJ/m² and energies in MJ, an hour at a time
RESULTS = ("GlobHor", "DiffHor", "T_Amb", "GlobInc", "GlobEff", "EArray", "E_Grid")
MONTH_HOURS = np.cumsum([0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]) * 24


@dataclass
class Site:
    name: str = ""
    country: str = ""
    lat: float = 0.0
    lon: float = 0.0
    altitude: float = 0.0
    timezone: float = 0.0
    source: str = ""
    ghi: list = field(default_factory=list)          # kWh/m² by month
    dhi: list = field(default_factory=list)
    t_amb: list = field(default_factory=list)


@dataclass
class VariantHead:
    path: Path
    comment: str = ""
    version: str = ""
    system_kind: str = ""
    computed: str = ""


@dataclass
class ProjectFile:
    path: Path
    name: str = ""
    version: str = ""
    site: Site = field(default_factory=Site)
    albedo: list = field(default_factory=list)       # 12 months
    design_t_min: float | None = None
    met_file: str = ""
    transposition: str = ""
    variants: list = field(default_factory=list)


@dataclass
class Orientation:
    number: int
    kind: str                       # FixedPlane, Sheds, TrackHorizNSAxis...
    tilt: float = 0.0
    azimuth: float = 0.0            # PVsyst's: from South, + towards West (CEI 82-25's as well)
    name: str = ""
    sheds: int = 0
    pitch: float = 0.0
    width: float = 0.0              # collector width (slant)


@dataclass
class SubArray:
    name: str
    module_file: str = ""
    inverter_file: str = ""
    optimizer: str = ""
    n_series: int = 0
    n_strings: int = 0
    n_inverters: float = 1.0
    orientation: int = 1
    quality: float = 0.0            # %, negative for a gain
    mismatch: float = 0.0           # %, at MPP
    string_mismatch: float = 0.0    # %
    lid: float = 0.0                # %
    dc_wiring: float = 0.0          # % at STC
    iam_mode: str = ""
    iam_b0: float | None = None
    iam_points: list = field(default_factory=list)    # [(angle, iam)]
    absent: list = field(default_factory=list)        # loss keys the file leaves out (PVsyst writes no default)

    @property
    def modules(self) -> int:
        return self.n_series * self.n_strings


@dataclass
class Field:
    """A PV object of the 3D scene: a table, a rectangular field or a field of sheds."""
    kind: str                       # pvShdArrayTable, pvShdArrayRect, pvShdArrayShed, pvShdArrayTracking
    name: str
    origin: tuple = (0.0, 0.0, 0.0)  # scene frame: X West, Y South, Z up (northern hemisphere)
    tilt: float = 0.0
    azimuth: float = 0.0
    length: float = 0.0             # along the row
    width: float = 0.0              # up the slope
    rows: int = 1
    pitch: float = 0.0
    orientation: int = -1
    module: str = ""
    module_size: tuple = ()         # (width, height) m, as PanneauPVName gives them
    n_height: int = 1
    n_width: int = 0
    portrait: bool = True
    gap_x: float = 0.0
    gap_y: float = 0.0


@dataclass
class Variant:
    path: Path
    comment: str = ""
    version: str = ""
    system_kind: str = ""
    site: Site = field(default_factory=Site)
    transposition: str = ""
    orientations: list = field(default_factory=list)
    sub_arrays: list = field(default_factory=list)
    uc: float | None = None
    uv: float = 0.0
    soiling: float = 0.0            # %
    inverters: list = field(default_factory=list)     # one list per inverter: strings on each of its inputs
    system_type: str = ""
    grid_limit_kw: float | None = None
    unavailability_days: float = 0.0
    ageing_pct_year: float | None = None
    fields: list = field(default_factory=list)
    scene_others: list = field(default_factory=list)  # (type, name) of the scene's objects that are not PV
    electrical_fraction: float | None = None          # FracOmbreMod
    bifacial: bool = False
    results: dict = field(default_factory=dict)       # name -> 12 monthly values (kWh/m², kWh, °C)
    not_understood: list = field(default_factory=list)

    @property
    def modules(self) -> int:
        return sum(s.modules for s in self.sub_arrays)


def _f(node: Node | None, key: str) -> float | None:
    if node is None:
        return None
    v = node.get(key)
    return number(v) if v is not None else DEFAULTS.get(key)


def _site(node: Node | None) -> Site:
    if node is None:
        return Site()
    return Site(name=node.get("Site") or node.get("NomF") or "", country=node.get("Country") or "",
                lat=_f(node, "Latitude") or 0.0, lon=_f(node, "Longitude") or 0.0,
                altitude=_f(node, "Altitude") or 0.0, timezone=_f(node, "TimeZone") or 0.0,
                source=node.get("Source") or node.get("SourceType") or "",
                ghi=numbers(node.get("GlobalH"))[:12], dhi=numbers(node.get("DiffuseH"))[:12],
                t_amb=numbers(node.get("TAmb"))[:12])


def variant_files(prj: Path) -> list[Path]:
    """The variants of a project: the files next to it with its name and an extension V + two characters,
    in PVsyst's order (VC0...VC9, VCA...VCZ, then VD0...)."""
    prj = Path(prj)
    pattern = re.compile(re.escape(prj.stem) + r"\.V[C-Z][0-9A-Z]$", re.IGNORECASE)
    found = [p for p in prj.parent.iterdir() if p.is_file() and pattern.match(p.name)]

    def order(p: Path):
        ext = p.suffix.upper()
        return (ext[2], "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(ext[3]))
    return sorted(found, key=order)


def _head(path: Path) -> VariantHead:
    """The first lines of a variant, enough for the list to choose from (a variant can weigh 1.7 MB)."""
    out = VariantHead(path)
    with open(path, "rb") as f:
        text, _enc = pvobject.decode(f.read(4096))
    for line in text.splitlines()[:40]:
        k, sep, v = line.strip().partition("=")
        if not sep:
            continue
        if k == "Comment" and not out.comment:
            out.comment = v
        elif k == "Version" and not out.version:
            out.version = v
        elif k == "SystemKind":
            out.system_kind = v
        elif k == "DateCalcul":
            out.computed = v
    return out


def read_project(path: Path) -> ProjectFile:
    doc = pvobject.read(path)
    top = doc.top
    if top is None or top.type != "pvProject":
        raise pvobject.FormatError(f"{Path(path).name}: not a PVsyst project")
    out = ProjectFile(Path(path), name=top.get("Comment") or Path(path).stem, version=top.get("Version") or "")
    out.site = _site(top.find(type="pvSite"))
    out.albedo = numbers(top.get("Albedo"))[:12]
    out.design_t_min = _f(top, "DesignTempMin")
    out.met_file = top.get("MeteoFileName") or ""
    out.transposition = top.get("TranspositionAlgorithm") or ""
    out.variants = [_head(p) for p in variant_files(path)]
    return out


def read_variant(path: Path) -> Variant:
    doc = pvobject.read(path)
    top = doc.top
    if top is None or top.type != "pvVCalcul":
        raise pvobject.FormatError(f"{Path(path).name}: not a PVsyst variant")
    v = Variant(Path(path), comment=top.get("Comment") or "", version=top.get("Version") or "",
                system_kind=top.get("SystemKind") or "", transposition=top.get("TranspositionAlgorithm") or "")
    v.site = _site(top.find(type="pvSite", name="SiteSimul") or top.find(type="pvSite"))
    _orientations(v, top)
    main = top.find(type="pvMainArray")
    if main is not None:
        v.uc = _f(main, "UFactor")
        v.uv = _f(main, "UVFactor") or 0.0
        v.soiling = 100.0 * (_f(main, "SoilingLoss") or 0.0)
        ageing = main.find(type="pvAgeing")
        if ageing is not None:
            v.ageing_pct_year = _f(ageing, "ModuleDegradFactor")
        v.bifacial = main.find(type="pvBiFacial") is not None or top.find(type="pvBiFacial") is not None
    v.sub_arrays = [_sub_array(n) for n in top.findall(type="pvSubArray")]
    circuit = top.find(type="pvCircuit")
    if circuit is not None:
        v.inverters = _circuit(circuit)
    system = top.find(type="pvSystem")
    if system is not None:
        v.system_type = system.get("SystemType") or ""
        v.grid_limit_kw = _f(system, "PLimGrid")
        v.unavailability_days = _f(system, "UnavTotDuration") or 0.0
        if system.get("BatteryFile") or system.find(type="pvGridStorage"):
            v.not_understood.append("storage")
    scene = top.find(type="pvShading")
    if scene is not None:
        v.electrical_fraction = _f(scene, "FracOmbreMod")
        for obj in scene.children:
            if obj.kind != "list":
                continue
            for item in obj.children:
                if item.kind != "object":
                    continue
                if item.type in ("pvShdArrayTable", "pvShdArrayRect", "pvShdArrayShed", "pvShdArrayTracking"):
                    v.fields.append(_field(item))
                else:
                    v.scene_others.append((item.type, item.get("Comment") or ""))
    v.results = _results(top)
    if top.find(type="TEcoEvaluation") is not None:
        v.not_understood.append("economics")
    return v


def _orientations(v: Variant, top: Node) -> None:
    orients = top.findall(type="pvOrient")
    if orients:                                     # PVsyst 8: one pvOrient per orientation
        for k, o in enumerate(orients, start=1):
            v.orientations.append(Orientation(int(_f(o, "NoOrient") or k), o.get("FieldType") or "",
                                              _f(o, "FieldTilt") or 0.0, _f(o, "FieldAzim") or 0.0,
                                              o.get("Comment") or "", int(_f(o, "NSheds") or 0),
                                              _f(o, "Pitch") or 0.0, _f(o, "CollectorWidth") or 0.0))
        return
    plane = top.find(type="pvCollPlane")            # PVsyst 7: one plane
    if plane is not None:
        v.orientations.append(Orientation(1, plane.get("FieldType") or "", _f(plane, "InclPlR") or 0.0,
                                          _f(plane, "AzimPlR") or 0.0, "", int(_f(plane, "NSheds") or 0),
                                          _f(plane, "Pitch") or 0.0, _f(plane, "LargCapt") or 0.0))


def _sub_array(n: Node) -> SubArray:
    s = SubArray(n.get("Comment") or "", n.get("PVModule") or "", n.get("GInverter") or "", n.get("Optimizer") or "",
                 int(_f(n, "NModSerie") or 0), int(_f(n, "NStringCh") or 0), _f(n, "NInverter") or 1.0,
                 int(_f(n, "NoOrientation") or 1), _f(n, "PQualityModP") or 0.0, _f(n, "PMismMPP") or 0.0,
                 _f(n, "PMismString") or 0.0, _f(n, "LIDLoss") or 0.0, _f(n, "RSCablagePC") or 0.0)
    s.absent = [k for k in ("PQualityModP", "PMismMPP", "LIDLoss", "RSCablagePC") if n.get(k) is None]
    iam = n.find(type="pvIAM")
    if iam is not None:
        s.iam_mode = iam.get("IAMMode") or "Default"
        s.iam_b0 = _f(iam, "B0_IAM") if s.iam_mode == "Default" else None
        profile = iam.find(type="TCubicProfile")
        if profile is not None:
            pts = [tuple(numbers(v)[:2]) for k, v in profile.attrs if k.startswith("Point_")]
            s.iam_points = [p for p in pts if len(p) == 2]
    return s


def _circuit(node: Node) -> list[list[int]]:
    """The strings on each input of each inverter, from the single-line diagram: an inverter node holds MPPT
    nodes or strings directly; NElements repeats a node (omitted when 1)."""
    out = []
    for inv in node.walk():
        if inv.kind != "circuit" or inv.name != "InverterNode":
            continue
        copies = int(_f(inv, "NElements") or 1)
        mppts = [m for m in inv.walk() if m.kind == "circuit" and m.name == "MPPTNode"]
        if mppts:
            inputs = []
            for m in mppts:
                strings = sum(int(_f(s, "NElements") or 1) for s in m.walk()
                              if s.kind == "circuit" and s.name == "StringNode")
                inputs += [strings] * int(_f(m, "NElements") or 1)
        else:
            inputs = [sum(int(_f(s, "NElements") or 1) for s in inv.walk()
                          if s.kind == "circuit" and s.name == "StringNode")]
        out += [inputs] * copies
    return out


def _field(n: Node) -> Field:
    x, y, z = (numbers(n.get("DOrigine")) + [0.0, 0.0, 0.0])[:3]
    name, size = (n.get("PanneauPVName") or ";;").split(";")[0], numbers(";".join((n.get("PanneauPVName") or "").split(";")[1:]).replace(";", ","))
    rect = n.type == "pvShdArrayRect"
    length, width = _f(n, "LongA" if rect else "LongShed") or 0.0, _f(n, "LargA" if rect else "LargShed") or 0.0
    pitch = _f(n, "PitchNS") or 0.0
    if n.type == "pvShdArrayTracking":
        # a tracker: LongShed is its width across the axis, LargShed its length along it, the trackers
        # spaced East-West; as a field: along the axis, the width up the (horizontal) "slope"
        length, width, pitch = width, length, _f(n, "PitchEW") or pitch
    return Field(n.type, n.get("Comment") or "", (x, y, z), _f(n, "DInclin") or 0.0, _f(n, "DAzimut") or 0.0,
                 length, width, int(_f(n, "NElemChamps") or 1), pitch, int(_f(n, "NoOrient") or -1), name,
                 tuple(size[:2]), int(_f(n, "NModInHeight") or 1), int(_f(n, "NModInWidth") or 0),
                 (n.get("ModuleOrient") or "moPortrait") == "moPortrait", _f(n, "ModSpacingX") or 0.0,
                 _f(n, "ModSpacingY") or 0.0)


def _results(top: Node) -> dict:
    """The monthly values of the main results, summed from the hourly records (kWh/m², kWh; °C as means)."""
    found = {}
    for name, var in records.variables(top).items():
        if name not in RESULTS:
            continue
        try:
            hourly = records.series(var)
        except (ValueError, KeyError):
            continue
        if len(hourly) != 8760:
            continue
        months = [hourly[MONTH_HOURS[k]:MONTH_HOURS[k + 1]] for k in range(12)]
        found[name] = [float(m.mean()) if name == "T_Amb" else float(m.sum() / 3.6) for m in months]
    return found


def read_met(path: Path) -> dict:
    """The hourly weather of a .MET: {"site", "source", "ghi", "dhi", "t_amb", "wind"} in W/m², °C, m/s, in
    the file's order (the year of the data, standard time of the site, label at the start of the hour)."""
    doc = pvobject.read(path)
    top = doc.top
    if top is None or top.type != "pvMeteo":
        raise pvobject.FormatError(f"{Path(path).name}: not a PVsyst weather file")
    v = records.variables(top)
    out = {"site": _site(top.find(type="pvSite")), "source": top.get("SourceM") or "",
           "source_type": (top.find(type="pvSite") or top).get("SourceType") or ""}
    for key, name, scale in (("ghi", "GlobHor", records.MJ_HOUR_TO_W), ("dhi", "DiffHor", records.MJ_HOUR_TO_W),
                             ("t_amb", "T_Amb", 1.0), ("wind", "WindVel", 1.0)):
        if name in v:
            out[key] = records.series(v[name]) * scale
    return out
