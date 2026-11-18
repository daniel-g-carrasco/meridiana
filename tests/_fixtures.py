"""The projects and the data the tests share (study 18, D 7.1), one for each use, built here and nowhere else:

- `capannone()`: a shed of 40 x 20 m at Rho, 9,5 m high, a sub-field "Sud" on its flat roof, tilted rows at 15
  degrees, laid (the project of the window's tests);
- `capannone_rho()`: the same shed subject to the fire brigade, with a parapet, a smoke vent and a plant that casts
  shade, the rows two modules high (the project of the file's tests);
- `tetto_con_lucernario()`: a flat roof of 60 x 30 m with a sub-field facing South and a skylight in it (the rows by
  hand);
- `casa_a_falde()`: a house of 12 x 8 m with a gable roof at 30 degrees and a sub-field on its southern pitch;
- `generated(...)`: many buildings in a grid, for the tests of speed (docs/studio/18-prove/A-architettura-prove.py);
- `clear_sky_meteo()` and `write_cache()`: a weather year made without the network, put in the cache as PVGIS's;
- `inverter_record()`: a datasheet of an inverter of 20 kW with two inputs;
- `PAN` and `OND`: a module and an inverter in PVsyst's text format, written by hand, and `written()` to put them in
  a file;
- the tests' own minisign key and two payloads signed with it;
- `flat()`: the tokens of a theme in one level;
- `view3d()` and `plan_view()`: the 3D view and the plan alone, showing a project as the window shows it (Qt)."""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

import _setup  # noqa: F401

from meridiana import model
from meridiana.energy.meteo import Meteo
from meridiana.energy.pedigree import Source

RHO = {"lat": 45.5226, "lon": 9.0300, "address": "Rho (MI)"}


def capannone(name: str = "Prova") -> model.Project:
    """A shed of 40 x 20 m, 9,5 m high, with a sub-field "Sud" on its flat roof (tilted rows at 15 degrees), laid."""
    p = model.Project(name=name)
    p.site = model.Site(**RHO)
    b = model.Building(id=p.new_id("b"), name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]], height=9.5)
    p.buildings.append(b)
    p.subfields.append(model.SubField(id=p.new_id("s"), name="Sud", ring=[[1, 1], [39, 1], [39, 19], [1, 19]],
                                      building=b.id, params={"tilt": 15.0}, filled=True))
    return p


def capannone_rho() -> model.Project:
    """The shed subject to the fire brigade (category B), with a parapet of 0,8 m, a smoke vent and a plant 2,2 m
    high on its roof, the rows two modules high; not laid."""
    p = model.Project(name="Capannone Rho")
    p.site = model.Site(**RHO)
    b = model.Building(id=p.new_id("b"), name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]], height=9.5)
    b.fire = model.Fire(subject=True, category="B")
    p.buildings.append(b)
    p.subfields.append(model.SubField(id=p.new_id("s"), name="Sud", ring=[[1, 1], [39, 1], [39, 19], [1, 19]],
                                      building=b.id, params={"tilt": 15.0, "stack": 2}))
    p.exclusions.append(model.ExclusionItem(id=p.new_id("e"), ring=[[18, 8], [20, 8], [20, 10], [18, 10]],
                                            kind="vent", building=b.id))
    p.exclusions.append(model.ExclusionItem(id=p.new_id("e"), ring=[[30, 12], [31, 12], [31, 13], [30, 13]],
                                            kind="plant", building=b.id, height=2.2))
    b.parapet = 0.8
    return p


def tetto_con_lucernario(fire: bool = False) -> model.Project:
    """A flat roof of 60 x 30 m with a sub-field on most of it (rows facing South), a skylight in it."""
    p = model.Project(name="Prova")
    p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[[0, 0], [60, 0], [60, 30], [0, 30]],
                                      height=8.0, fire=model.Fire(subject=fire)))
    p.subfields.append(model.SubField(id="s1", name="Sud", ring=[[1, 1], [59, 1], [59, 29], [1, 29]], building="b1",
                                      pitch=0, params={"tilt": 10.0, "azimuth": 0.0}))
    p.exclusions.append(model.ExclusionItem(id="e1", ring=[[30, 14], [32, 14], [32, 16], [30, 16]], kind="skylight",
                                            building="b1"))
    return p


def laid(p: model.Project, sfid: str = "s1"):
    """The layout of a sub-field of `p`, computed here (no thread)."""
    return p.fill(next(s for s in p.subfields if s.id == sfid))


def casa_a_falde() -> model.Project:
    """A house of 12 x 8 m, eaves at 6 m, a gable roof at 30 degrees with its eaves on the long sides and a sub-field
    on the southern pitch (side 0), modules flat on it."""
    p = model.Project(name="Casa")
    p.site = model.Site(**RHO)
    b = model.Building(id="b1", name="Casa", footprint=[[0, 0], [12, 0], [12, 8], [0, 8]], height=6.0,
                       roof=model.Roof(type="gable", tilt=30.0))
    p.buildings.append(b)
    p.subfields.append(model.SubField(id="s1", name="Falda sud", ring=[[0.5, 0.5], [11.5, 0.5], [11.5, 3.5], [0.5, 3.5]],
                                      building="b1", pitch=0, params={"mounting": "coplanar"}, filled=True))
    return p


def generated(n_buildings: int, subfields_per_building: int, exclusions_per_building: int) -> model.Project:
    """`n_buildings` rectangles 40 x 20 m in a grid of five, 8 m high, each with `subfields_per_building`
    sub-fields side by side (tilted rows at 15 degrees, filled) and `exclusions_per_building` skylights. The same
    generator as docs/studio/18-prove/A-architettura-prove.py, so that the numbers of the tests and of the proofs on
    Daniel's PC are about the same project."""
    p = model.Project(name="Generated")
    p.site = model.Site(lat=45.5226, lon=9.0300, address="Rho (MI), Lombardia")
    for k in range(n_buildings):
        x0, y0 = (k % 5) * 50.0, (k // 5) * 30.0
        b = model.Building(id=p.new_id("b"), name=f"Building {k + 1}",
                           footprint=[[x0, y0], [x0 + 40, y0], [x0 + 40, y0 + 20], [x0, y0 + 20]], height=8.0)
        p.buildings.append(b)
        width = 38.0 / subfields_per_building
        for j in range(subfields_per_building):
            sx = x0 + 1 + j * width
            p.subfields.append(model.SubField(id=p.new_id("s"), name=f"Sub-field {k + 1}.{j + 1}",
                                              ring=[[sx, y0 + 1], [sx + width - 0.5, y0 + 1],
                                                    [sx + width - 0.5, y0 + 19], [sx, y0 + 19]],
                                              building=b.id, pitch=0, params={"tilt": 15.0}, filled=True))
        for j in range(exclusions_per_building):
            ex = x0 + 5 + j * 6
            p.exclusions.append(model.ExclusionItem(id=p.new_id("e"), ring=[[ex, y0 + 9], [ex + 1.5, y0 + 9],
                                                                          [ex + 1.5, y0 + 10.5], [ex, y0 + 10.5]],
                                                    kind="skylight", building=b.id))
    return p


def mixed() -> model.Project:
    """The shed of Rho (flat, parapet, smoke vent, plant), a gable house with a chimney and a sub-field, a hip villa, a
    mono-pitch shelter, a tree on the ground; three inverters, so that the modules have strings (the IFC tests)."""
    p = capannone_rho()
    p.subfields[0].filled = True
    p.buildings.append(model.Building(id="b9", name="Casa", footprint=[[60, 0], [72, 0], [72, 8], [60, 8]], height=6.0,
                                      roof=model.Roof(type="gable", tilt=30.0)))
    p.buildings.append(model.Building(id="b10", name="Villa", footprint=[[80, 0], [95, 0], [95, 10], [80, 10]],
                                      height=7.0, roof=model.Roof(type="hip", tilt=25.0)))
    p.buildings.append(model.Building(id="b11", name="Tettoia", footprint=[[60, 20], [70, 20], [70, 26], [60, 26]],
                                      height=4.0, roof=model.Roof(type="mono", tilt=10.0, eave_side=0)))
    p.subfields.append(model.SubField(id="s9", name="Falda sud", ring=[[60.5, 0.5], [71.5, 0.5], [71.5, 3.5],
                                                                        [60.5, 3.5]], building="b9", pitch=0,
                                      params={"mounting": "coplanar"}, filled=True))
    p.exclusions.append(model.ExclusionItem(id="e9", ring=[[50, 30], [52, 30], [52, 32], [50, 32]], kind="tree"))
    p.exclusions.append(model.ExclusionItem(id="e10", ring=[[64, 5], [64.6, 5], [64.6, 5.6], [64, 5.6]],
                                            kind="chimney", building="b9"))
    p.energy["inverters"] = [{"record": inverter_record(), "count": 3, "name": ""}]
    p.energy["strings"] = {"auto": True}            # Meridiana's proposal, as a project of before format 14 had it
    return p


def exported(project: model.Project, folder: Path, name: str = "misto.ifc", **more) -> tuple[Path, dict, dict]:
    """`project` laid out and written as IFC4 in `folder`, its strings proposed: the file, the export's summary and
    the layouts (needs ifcopenshell)."""
    from meridiana import ifc_export, jobs
    from meridiana.energy import plant
    results, _keys, _laid = jobs.layout_of(project)
    strings = {(sf, key): s.label for s in plant.build(project, results, check=False).strings
               for sf, key, _c in s.modules}
    path = folder / name
    return path, ifc_export.export(project, results, path, strings=strings, **more), results


def view3d(test, project=None, size=(800, 600)):
    """The 3D view alone (ui/view3d.py), shown at `size`, with the buildings, the obstacles and the modules of
    `project` (the shed by default) framed as the window frames them at the start (MainWindow._show_3d), AutoCAD's
    navigation, no animation; disposed of at the end of `test`. (view, results)."""
    from meridiana import jobs, mesh
    from meridiana.ui.view3d import View3D
    app = _setup.qt_or_skip()
    project = project or capannone()
    results, _keys, _laid = jobs.layout_of(project)
    view = View3D()
    test.addCleanup(_setup.dispose, view)
    view.resize(*size)
    view.show()
    parts = [mesh.building_triangles(b.footprint, b.pitches(), None) for b in project.buildings]
    parts += [mesh.prism_triangles(o["ring"], o["z0"], o["z1"], mesh.OBSTACLE) for o in project.obstacle_prisms()]
    cat = tuple(np.concatenate([p[i] for p in parts]) if parts else np.zeros((0, 3), np.float32) for i in range(3))
    tables = [r.table for sf in project.subfields if sf.filled and not isinstance(r := results.get(sf.id), Exception)
              and r is not None]
    view.set_navigation("autocad", "turntable", "cursor", True)
    view.backend.reduced_motion = True                  # the moves at once, to look at them
    _setup.wait_until(app, lambda: view.backend.size[0] > 0, 5)
    view.show_scene(cat, np.concatenate(tables) if tables else np.zeros((0, 20), np.float32), fit=True)
    app.processEvents()
    return view, results


def plan_view(test, project=None, size=(800, 600)):
    """The plan alone (ui/plan.py), no background, shown at `size` with `project` (the shed by default) and its
    layouts, fitted; disposed of at the end of `test`. (plan, results)."""
    from meridiana import jobs
    from meridiana.ui.plan import PlanView
    app = _setup.qt_or_skip()
    project = project or capannone()
    results, _keys, _laid = jobs.layout_of(project)
    plan = PlanView(Path(tempfile.mkdtemp()))
    test.addCleanup(_setup.dispose, plan)
    plan.set_source("none")
    plan.set_tool("select")                             # as the window starts it
    plan.resize(*size)
    plan.show()
    plan.show_project(project, results)
    plan.fit()
    app.processEvents()
    return plan, results


def inverter_record(**more) -> dict:
    """The datasheet of an inverter of 20 kW, two inputs of 26 A, as the catalogue gives one."""
    rec = {"manufacturer": "Acme", "model": "AC-20K", "ac_power_nominal_w": 20000, "efficiency_euro_pct": 97.5,
           "dc_voltage_max_v": 1100, "mppt_voltage_min_v": 180, "mppt_voltage_max_v": 1000, "mppt_count": 2,
           "dc_current_max_per_mppt_a": [26, 26], "dc_isc_max_per_mppt_a": [40, 40]}
    rec.update(more)
    return rec


def write_cache(m: Meteo, cache_dir) -> None:
    """Put a weather year in the cache as PVGIS's would be, so that the window computes without the network."""
    from meridiana import atomic
    from meridiana.energy import meteo
    raw = {"fetched": m.fetched,
           "meta": {"inputs": {"location": {"latitude": m.latitude, "longitude": m.longitude,
                                            "elevation": m.elevation, "irradiance_time_offset": m.time_offset_h},
                               "meteo_data": {"radiation_db": "synthetic", "meteo_db": "synthetic",
                                              "year_min": 2026, "year_max": 2026}}},
           "columns": {c: [float(v) for v in m.data[c].to_numpy()] for c in meteo.COLUMNS}}
    atomic.write_json(meteo._cache_file(cache_dir, "tmy", m.latitude, m.longitude), raw, keep_backup=False)


_SKIES: dict = {}


def clear_sky_meteo(lat: float = 45.5226, lon: float = 9.03, elevation: float = 150.0) -> Meteo:
    """A weather year for the tests, made without the network: a clear sky (pvlib's simplified Solis model) dimmed to
    a plausible Po valley year, a seasonal temperature, a light wind. Not a real climate: the tests check the physics
    and the bookkeeping, not the numbers of a site. Made once for each place (pvlib's clear sky costs 0,1-0,2 s) and
    given as a copy, so that a test that changes it changes only its own."""
    key = (lat, lon, elevation)
    if key not in _SKIES:
        import pvlib
        index = pd.date_range("1990-01-01 00:00", periods=8760, freq="h", tz="UTC")
        loc = pvlib.location.Location(lat, lon, altitude=elevation)
        cs = loc.get_clearsky(index + pd.Timedelta(minutes=10), model="simplified_solis")
        day = index.dayofyear.to_numpy()
        hour = index.hour.to_numpy()
        temp = 13.0 - 10.0 * np.cos(2 * np.pi * (day - 15) / 365.0) + 4.0 * np.sin(2 * np.pi * (hour - 9) / 24.0)
        k = 0.72                                   # a year with clouds, on average
        _SKIES[key] = pd.DataFrame({"ghi": cs.ghi.to_numpy() * k, "dni": cs.dni.to_numpy() * k, "dhi": cs.dhi.to_numpy(),
                                    "temp_air": temp, "wind_speed": np.full(8760, 1.5),
                                    "pressure": np.full(8760, 101325.0 * np.exp(-elevation / 8434.0)),
                                    "relative_humidity": np.full(8760, 65.0)}, index=index).fillna(0.0)
    return Meteo(data=_SKIES[key].copy(), latitude=lat, longitude=lon, elevation=elevation, time_offset_h=0.1767,
                 source=Source("data", "synthetic clear sky for the tests"), fetched="2026-10-21")

# a module and an inverter in PVsyst's text format, written by hand for the tests (tests/data/pvsyst/README.md)
PAN = """PVObject_=pvModule
  Version=7.2
  Flags=$00508003

  PVObject_Commercial=pvCommercial
    Comment=www.example.com
    Flags=$0041
    Manufacturer=Acme Solar
    Model=AS-54-415
    DataSource=Manufacturer 2025
    YearBeg=2025
    Width=1.134
    Height=1.722
    Depth=0.030
    Weight=21.500
  End of PVObject pvCommercial

  Technol=mtSiMono
  NCelS=54
  NCelP=2
  NDiode=3
  GRef=1000
  TRef=25.0
  PNom=415.0
  Isc=13.900
  Voc=37.070
  Imp=13.150
  Vmp=31.560
  muISC=6.12
  muVocSpec=-101.0
  muPmpReq=-0.350
  RShunt=300
  RSerie=0.155
  VMaxIEC=1500
  BifacialityFactor=0.700
End of PVObject pvModule
"""

OND = """PVObject_=pvGInverter
  Comment=Acme 50K
  Version=7.2

  PVObject_Commercial=pvCommercial
    Manufacturer=Acme Power
    Model=AP-50K
  End of PVObject pvCommercial

  Converter=TConverter
    PNomConv=50.000
    PMaxOUT=55.000
    VOutConv=400.0
    VMppMin=200
    VMPPMax=1000
    VAbsMax=1100
    EfficMax=98.70
    EfficEuro=98.40
    MonoTri=Tri
    NbMPPT=4
    IMaxDC=128.0
  End of TConverter
End of PVObject pvGInverter
"""


def written(text: str, name: str) -> Path:
    """`text` in a file called `name`, in a folder of its own."""
    path = Path(tempfile.mkdtemp()) / name
    path.write_text(text, encoding="utf-8")
    return path


# a key of the tests' own (minisign -G -W), never the project's
PUBLIC_KEY = "RWR7SJiRpYyOYfMs5NsaotSrG3B4wGxiTvXOWkzu4JCT3e240QSuHElq"
PAYLOAD = b"installer" * 1000
# minisign -S -m payload -t "timestamp:1792398099 file:spola-setup-v9-windows-x64.exe hashed" (and v8)
SIGNED_V9 = (
    "untrusted comment: signature from minisign secret key\n"
    "RUR7SJiRpYyOYTjY8y9f5xQs4K0f1/VnY5nfhx92xYh0ROEhmhIgOa2L0LoAiY/j94qPDaF0/iYheQNA+394mJGnMBXICA7BTA0=\n"
    "trusted comment: timestamp:1792398099 file:spola-setup-v9-windows-x64.exe hashed\n"
    "Qs+9uJ0rlFwspS9yeKoD/xfGxiBTlMs0BIzyXEVY+tRp+oh26MKy3J3MmQuZMaRh4seA9ImGsaGouHgIzgYfDg==\n")
SIGNED_V8 = (
    "untrusted comment: signature from minisign secret key\n"
    "RUR7SJiRpYyOYTjY8y9f5xQs4K0f1/VnY5nfhx92xYh0ROEhmhIgOa2L0LoAiY/j94qPDaF0/iYheQNA+394mJGnMBXICA7BTA0=\n"
    "trusted comment: timestamp:1792398099 file:spola-setup-v8-windows-x64.exe hashed\n"
    "VMcRAgf4XsA2FSeekO08xvUjl0zYLCU+vpe9mCCJ/KfpgB9pAAOnQhZFMVowHAmE16JaTXRW+jA1dRWK+y3BAw==\n")



def flat(tokens: dict) -> dict:
    """The tokens of a theme in one level: "d3.module" for d3["module"]."""
    out = {}
    for k, v in tokens.items():
        if isinstance(v, dict):
            out.update({f"{k}.{kk}": vv for kk, vv in v.items()})
        else:
            out[k] = v
    return out
