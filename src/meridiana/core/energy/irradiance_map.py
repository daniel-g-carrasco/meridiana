"""The irradiance map of the surfaces (study 45, R588): for every tile of a grid on a roof pitch or a placement surface,
the year's irradiance with the near shading, its loss against the same tile without the obstacles, and the hours of
sun on a chosen day; for every module laid, the same figures. Without Qt and without the network.

No second calculation. A tile enters the engine as a module does: the shadows of its plane are cast once
(nearshade.cast) and its shaded share is read for every cell of the sun grid (nearshade.shares). The light on the
plane is the year's: simulate.plane_light for a surface without modules, the parts _ArrayPass keeps (beam_rows,
sky_rows, ground_rows) for the modules. The tables are read with the year's own weights: the bilinear reading of the
grid at the hours (nearshade._weights, as nearshade.at reads it) for the direct light, the dome's weights of
nearshade.diffuse_factor for the sky.

How the pieces go together, each one callable by itself (the work in processes builds on them):
1. prepare(): the light of the site, once (the sun of the year and of the day, the weights, the key);
2. surfaces_of(): what is coloured, with the solids that can shade each surface;
3. grid_of(): the tiles of a surface at a step (nested: the tile of 2 m holds 4 x 4 tiles of 0,5 m);
4. cast_surface(): the shadows of a surface, once, for every step and every day;
5. surface_reader() and read(): the figures of the tiles, a group at a time;
6. key_of(), classes(), module_values().
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from meridiana.core.compute import resources
from . import nearshade
from .meteo import Horizon, Meteo
from .simulate import REFERENCE_YEAR, Losses, SunPath, _active_horizon, plane_light, sun_path

VERSION = 1                     # of the computation: a change of the numbers changes every key
DAY = (12, 21)                  # the day of the hours of sun, (month, day): the shortest
MINUTES = 10                    # the sun on the day, and through the year for the cells to cast
MAX_TILES = 20_000              # tiles of a surface at most: beyond, the step doubles (Grid.step says which)
LOSS_CLASSES = (0.0, 2.0, 5.0, 10.0, 20.0, 40.0, 100.0)    # % of loss, decided (study 45, chapter 9, decision 4)
OUTSIDE, UNDER = 255, 254       # the classes of a tile off the surface and of one under an obstacle
UNDER_TOUCH = 1e-3              # m: a solid that comes this close to the plane stands on it...
UNDER_RISE = 0.05               # ...and rises this much above it covers the tiles under its section (not coloured);
                                # a slab of the model lying on the surface itself (its top within millimetres) does not


# ---------------------------------------------------------------------------------------------------------------------
# 1. the light of the site

@dataclass
class Light:
    """What the map reads every surface with, made once for a site (prepare): the weather, the losses that make the
    light, the horizon in use, the sun of the year (simulate.sun_path), the weights that read a table at its hours
    (cells x hours), the cells of the sun grid to cast (the sun's path through the year every MINUTES, so that one
    cast serves every day), the cells the year itself reads, the day's sun and its weights, and the key of the light."""
    meteo: Meteo
    losses: Losses
    horizon: Horizon | None
    sun: SunPath
    weights: object                 # scipy.sparse, (cells, hours)
    needed: np.ndarray              # (ELEVATIONS, AZIMUTHS) bool: the cells a cast computes
    year_cells: np.ndarray          # the cells of the year's own tables (nearshade.needed_cells of its sun)
    day: tuple
    minutes: int
    day_azimuth: np.ndarray
    day_elevation: np.ndarray       # -1 where the horizon hides the sun
    day_weights: object             # scipy.sparse, (cells, positions)
    key: bytes = b""


def _sun_positions(meteo: Meteo, times) -> tuple[np.ndarray, np.ndarray]:
    from .dependencies import load_pvlib
    pvlib = load_pvlib()
    sp = pvlib.solarposition.get_solarposition(times, meteo.latitude, meteo.longitude, altitude=meteo.elevation)
    return sp.azimuth.to_numpy(), 90.0 - sp.apparent_zenith.to_numpy()


def _day_sun(meteo: Meteo, horizon: Horizon | None, day: tuple, minutes: int):
    """The sun in the middle of every `minutes` of a day (UTC) of the reference year; behind the horizon, below it."""
    import pandas as pd
    month, d = day
    times = pd.date_range(f"{REFERENCE_YEAR}-{month:02d}-{d:02d} 00:00", periods=24 * 60 // minutes,
                          freq=f"{minutes}min", tz="UTC") + pd.Timedelta(minutes=minutes / 2.0)
    az, el = _sun_positions(meteo, times)
    if horizon is not None:
        el = np.where(horizon.at(az) > el, -1.0, el)
    return az, el


def prepare(meteo: Meteo, losses: Losses | None = None, horizon: Horizon | None = None, *, day: tuple = DAY,
            minutes: int = MINUTES, sun: SunPath | None = None) -> Light:
    """The light of a site for the map: `losses` and `horizon` as the year takes them (the horizon only when the
    losses use it); `sun` the year's step 1 when the caller has it already (simulate.sun_path)."""
    import pandas as pd
    losses = losses or Losses()
    hor = _active_horizon(horizon, losses)
    if sun is None:
        sun = sun_path(meteo, hor)
    weights = nearshade._weights(nearshade._corners(sun.azimuth, sun.elevation))
    year_cells = nearshade.needed_cells(sun.azimuth, sun.elevation)
    every = pd.date_range(f"{REFERENCE_YEAR}-01-01 00:00", periods=365 * 24 * 60 // minutes, freq=f"{minutes}min",
                          tz="UTC")
    az, el = _sun_positions(meteo, every)
    needed = year_cells | nearshade.needed_cells(az, el)
    d = meteo.data
    key = resources.fingerprint(np.ascontiguousarray(d.to_numpy(dtype=float)), list(d.columns), meteo.latitude,
                                meteo.longitude, meteo.elevation, meteo.time_offset_h,
                                None if hor is None else (np.asarray(hor.azimuth, float), np.asarray(hor.elevation, float)),
                                losses.albedo, losses.transposition, losses.use_horizon)
    light = Light(meteo, losses, hor, sun, weights, needed, year_cells, tuple(day), int(minutes), np.zeros(0),
                  np.zeros(0), None, key)
    return with_day(light, day)


def with_day(light: Light, day: tuple) -> Light:
    """The same light with the hours of sun of another day: the casts stay good (their cells cover the year)."""
    from dataclasses import replace
    az, el = _day_sun(light.meteo, light.horizon, tuple(day), light.minutes)
    return replace(light, day=tuple(day), day_azimuth=az, day_elevation=el,
                   day_weights=nearshade._weights(nearshade._corners(az, el)))


# ---------------------------------------------------------------------------------------------------------------------
# 2. the surfaces

@dataclass
class MapSurface:
    """A surface to colour: a pitch of a building drawn in the project, or a placement surface of an imported model
    (its own plane; the model's bodies and faces are not coloured). `outline` is the contour on the plane's axes
    (nearshade.plane_axes: u level, v up the slope), `d` the plane's distance n.x, `under` where the solids standing
    on it cover the surface (on the same axes), `weight` a rough cost to order the surfaces by, lightest first."""
    id: str
    name: str
    building: str | None
    tilt: float
    azimuth: float
    d: float
    ring: list                      # the contour on the plan, (x, y)
    outline: np.ndarray             # (k, 2)
    solids: list = field(repr=False, default_factory=list)
    under: object = field(repr=False, default=None)
    modules: bool = False
    area: float = 0.0               # m² on the plane
    weight: float = 0.0


def _sections(solids: list, n: np.ndarray, d: float, axes: np.ndarray):
    """Where the solids standing on the plane n.x = d cover it, on its axes: the union of their sections, or None."""
    import shapely
    pieces = []
    for s in solids:
        v = s.corners
        dist = v @ n - d
        if dist.min() > UNDER_TOUCH or dist.max() <= UNDER_RISE:
            continue
        on, above, below = np.abs(dist) <= UNDER_TOUCH, dist > UNDER_TOUCH, dist < -UNDER_TOUCH
        pts = [v[on]]
        if above.any() and below.any():
            va, da, vb, db = v[above], dist[above], v[below], dist[below]
            t = da[:, None] / (da[:, None] - db[None, :])
            pts.append((va[:, None, :] + (vb[None, :, :] - va[:, None, :]) * t[..., None]).reshape(-1, 3))
        uv = np.concatenate(pts) @ axes.T
        if len(uv) >= 3:
            hull = shapely.convex_hull(shapely.multipoints(uv))
            if hull.area > 1e-6:
                pieces.append(hull)
    return shapely.union_all(np.array(pieces, dtype=object)) if pieces else None


def _surface(sid, name, building, plane, ring, solids, modules) -> MapSurface:
    import shapely
    n, e1, e2 = nearshade.plane_axes(plane.tilt, plane.azimuth)
    axes = np.stack([e1, e2])
    xy = np.array(ring, dtype=float)
    outline = np.column_stack([xy, plane.z_of(xy[:, 0], xy[:, 1])]) @ axes.T
    d = float(n @ np.array([plane.x0, plane.y0, plane.z0]))
    area = float(shapely.Polygon(outline).buffer(0).area)
    return MapSurface(sid, name, building, float(plane.tilt), float(plane.azimuth), d, [tuple(map(float, q)) for q in ring],
                      outline, solids, _sections(solids, n, d, axes), modules, area, area * (1 + len(solids)))


def surfaces_of(project, results: dict | None = None, prisms: list | None = None) -> list[MapSurface]:
    """The surfaces of `project` to colour, in the project's order: the pitches of its buildings (not those of the
    bodies an imported model brought, Building.group) and the placement surfaces of its sub-fields (SubField.support).
    `results`: the layouts (sub-field id -> layout.Result), to say which surfaces have modules laid. `prisms`:
    project.obstacle_prisms(), when the caller has it."""
    from meridiana.core.layout import layout
    from meridiana.core.model import model
    from . import system
    results = results or {}
    prisms = project.obstacle_prisms() if prisms is None else prisms

    def laid(sf) -> bool:
        r = results.get(sf.id)
        return bool(sf.filled and r is not None and not isinstance(r, Exception) and getattr(r, "modules", None))

    out = []
    for b in project.buildings:
        if b.group:
            continue
        for i, pt in enumerate(b.pitches()):
            ref = b.pitch_ref(i)
            probe = model.SubField(id=f"_map.{b.id}.{ref}", name="", ring=list(pt.ring), building=b.id, pitch=ref)
            modules = any(laid(sf) for sf in project.subfields if sf.building == b.id
                          and not (sf.support is not None and sf.support.enabled)
                          and (b.pitch_index(sf.pitch) if b.pitch_index(sf.pitch) is not None else 0) == i)
            plane = layout.Surface(tilt=pt.tilt, azimuth=pt.azimuth, z0=pt.z0, x0=pt.x0, y0=pt.y0)
            name = f"{project.shown_name(b)} {pt.name}".strip()
            out.append(_surface(f"{b.id}:{ref}", name, b.id, plane, pt.ring, system.obstacles_of(project, probe, prisms),
                                modules))
    for sf in project.subfields:
        if sf.support is None or not sf.support.enabled or len(sf.ring) < 3:
            continue
        from meridiana.core.model import imported
        out.append(_surface(sf.id, imported.subfield_name(project, sf), sf.building, project.surface_of(sf), sf.ring,
                            system.obstacles_of(project, sf, prisms), laid(sf)))
    return out


# ---------------------------------------------------------------------------------------------------------------------
# 3. the tiles

@dataclass
class Grid:
    """The tiles of a surface at `step` (m), squares on the plane's axes from the origin of the axes, so that the grids
    of steps that divide each other nest. `shape` (rows along v, columns along u); `inside` the tiles that meet the
    surface (the border ones are cut by the drawing); `under` those whose centre a standing solid covers; the tiles
    computed are inside and not under: their flat indices into the shape (`index`) and rectangles (`rects`, umin,
    vmin, umax, vmax), and the box they fill (`bounds`)."""
    step: float
    iu: int                         # the first column and row, in steps from the origin of the axes
    iv: int
    shape: tuple
    inside: np.ndarray
    under: np.ndarray
    index: np.ndarray
    rects: np.ndarray
    bounds: tuple


def grid_of(surface: MapSurface, step: float, cap: int = MAX_TILES) -> Grid:
    """The tiles of `surface` at `step`, or at the step doubled until no more than `cap` tiles meet the surface."""
    import shapely
    poly = shapely.Polygon(surface.outline)
    if not poly.is_valid:
        poly = poly.buffer(0)
    shapely.prepare(poly)
    u0, v0, u1, v1 = poly.bounds
    step = float(step)
    while poly.area / (step * step) > cap:
        step *= 2.0
    while True:
        iu, iv = math.floor(u0 / step), math.floor(v0 / step)
        cols, rows = max(1, math.ceil(u1 / step - iu)), max(1, math.ceil(v1 / step - iv))
        jj, ii = np.meshgrid(np.arange(cols), np.arange(rows))
        lo_u, lo_v = (iu + jj.ravel()) * step, (iv + ii.ravel()) * step
        boxes = shapely.box(lo_u, lo_v, lo_u + step, lo_v + step)
        inside = shapely.intersects(boxes, poly) & ~shapely.touches(boxes, poly)
        if int(inside.sum()) <= cap:
            break
        step *= 2.0
    under = np.zeros(rows * cols, dtype=bool)
    if surface.under is not None:
        under = shapely.contains_xy(surface.under, lo_u + step / 2.0, lo_v + step / 2.0) & inside
    index = np.flatnonzero(inside & ~under)
    rects = np.column_stack([lo_u[index], lo_v[index], lo_u[index] + step, lo_v[index] + step])
    bounds = ((float(rects[:, 0].min()), float(rects[:, 1].min()), float(rects[:, 2].max()), float(rects[:, 3].max()))
              if len(rects) else (0.0, 0.0, 0.0, 0.0))
    return Grid(step, iu, iv, (rows, cols), inside.reshape(rows, cols), under.reshape(rows, cols), index, rects, bounds)


# ---------------------------------------------------------------------------------------------------------------------
# 4. the cast

def reaching(light: Light, surface: MapSurface, bounds) -> list:
    """The solids of `surface` whose shadow can reach the box `bounds` of its plane for a sun the cast computes: in
    front of the plane, and not farther from the box than the longest shadow of their highest corner. Exact: a solid
    left out has no hull that meets the box, so the shadows are the same."""
    n, e1, e2 = nearshade.plane_axes(surface.tilt, surface.azimuth)
    axes = np.stack([e1, e2])
    suns_all, lit = nearshade._lit_suns(n, light.needed)
    ns = suns_all[lit] @ n
    k = float(np.max(np.sqrt(np.clip(1.0 - ns ** 2, 0.0, None)) / ns)) if len(ns) else 0.0
    d = round(surface.d, 3)
    u0, v0, u1, v1 = bounds
    out = []
    for s in surface.solids:
        h = float((s.corners @ n - d).max())
        if h <= 1e-9:
            continue
        uv = s.corners @ axes.T
        r = h * k
        if uv[:, 0].max() + r < u0 or uv[:, 0].min() - r > u1 or uv[:, 1].max() + r < v0 or uv[:, 1].min() - r > v1:
            continue
        out.append(s)
    return out


def cast_surface(light: Light, surface: MapSurface, grid: Grid) -> nearshade.Cast:
    """The shadows of `surface` cast once, within the box of `grid`: give the coarsest grid, and the cast serves every
    finer grid nested in it (its tiles lie in the coarse ones) and every day (the cells cover the year's sun)."""
    return nearshade.cast(reaching(light, surface, grid.bounds), surface.tilt, surface.azimuth, surface.d, grid.bounds,
                          light.needed)


# ---------------------------------------------------------------------------------------------------------------------
# 5. the reading

@dataclass
class Reader:
    """A plane's light, ready to read tables (tiles or modules) at once: the direct light each cell of the sun grid
    carries over the year (Wh/m²), the year's sums of the three parts (kWh/m²), the dome's weights of the sky, the
    hours of the day each cell takes from the plane."""
    tilt: float
    azimuth: float
    b_cells: np.ndarray
    beam: float
    sky: float
    ground: float
    free: float                     # kWh/m² a year without the near shading
    dome: np.ndarray
    dome_total: float
    day_cells: np.ndarray
    day_free: float                 # hours of sun on the plane that day, without the near shading

    def read(self, tables: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """(kWh/m² a year, loss %, hours of sun on the day) of each table (n, ELEVATIONS, AZIMUTHS)."""
        t = tables.reshape(len(tables), -1).astype(np.float64)
        lost = t @ self.b_cells / 1000.0
        sky = (1.0 - (tables[:, ::2, ::2] * self.dome).sum(axis=(1, 2)) / self.dome_total if self.dome_total > 0
               else np.ones(len(t)))
        year = self.beam - lost + sky * self.sky + self.ground
        loss = 100.0 * (1.0 - year / self.free) if self.free > 0 else np.zeros(len(t))
        return year, loss, self.day_free - t @ self.day_cells


def reader_of(light: Light, tilt: float, azimuth: float, beam: np.ndarray, sky: np.ndarray, ground: np.ndarray) -> Reader:
    """The reader of a plane from its hourly light before the near shading (W/m²): plane_light's parts for a surface,
    _ArrayPass's beam_rows, sky_rows, ground_rows for an array."""
    n, _e1, _e2 = nearshade.plane_axes(tilt, azimuth)
    ee, aa = np.meshgrid(nearshade.ELEVATIONS, nearshade.AZIMUTHS, indexing="ij")
    ee, aa = ee[::2, ::2], aa[::2, ::2]
    dome = np.clip(nearshade.sun_vectors(aa, ee) @ n, 0.0, None) * np.cos(np.radians(ee))      # as diffuse_factor
    dt = light.minutes / 60.0
    up = (light.day_elevation > 0) & (nearshade.sun_vectors(light.day_azimuth, light.day_elevation) @ n > 1e-6)
    beam_sum, sky_sum, ground_sum = (float(np.asarray(x).sum()) / 1000.0 for x in (beam, sky, ground))
    return Reader(float(tilt), float(azimuth), np.asarray(light.weights @ np.asarray(beam, float)).ravel(), beam_sum,
                  sky_sum, ground_sum, beam_sum + sky_sum + ground_sum, dome, float(dome.sum()),
                  np.asarray(light.day_weights @ (up * dt)).ravel(), float(up.sum() * dt))


def surface_reader(light: Light, surface: MapSurface) -> Reader:
    """The reader of a surface without modules: the light on its plane after the horizon (simulate.plane_light)."""
    pl = plane_light(light.meteo, surface.tilt, surface.azimuth, light.losses, light.horizon, sun=light.sun)
    return reader_of(light, surface.tilt, surface.azimuth, pl.beam, pl.sky, pl.ground)


@dataclass
class Level:
    """The figures of a grid's tiles, float32 with the grid's shape; NaN for a tile not computed (off the surface,
    under an obstacle). `free`: the surface's irradiance without the near shading, kWh/m² a year, the number written
    on it (study 45, decision 1); `day_free` its hours of sun that day."""
    step: float
    year: np.ndarray                # kWh/m² a year, with the near shading
    loss: np.ndarray                # % of the year's irradiance the obstacles take
    hours: np.ndarray               # hours of sun on the day
    free: float
    day_free: float


def _check_cells(light: Light, shadows: nearshade.Cast, n: np.ndarray) -> None:
    _suns, front = nearshade._lit_suns(n, None)
    if (light.needed.ravel() & front & ~shadows.lit).any():
        raise ValueError("the cast does not hold every cell this light reads: cast the surface again")


def read(light: Light, reader: Reader, shadows: nearshade.Cast, grid: Grid, *, chunk: int = nearshade.SHARE_CHUNK,
         progress=None) -> Level:
    """The figures of the tiles of `grid`, `chunk` tiles at a time: each group's tables are reduced to their figures
    at once and dropped. `progress(done, total)` after each group; resources.checkpoint() between groups."""
    n, _e1, _e2 = nearshade.plane_axes(reader.tilt, reader.azimuth)
    _check_cells(light, shadows, n)
    size = grid.shape[0] * grid.shape[1]
    year, loss, hours = (np.full(size, np.nan, dtype=np.float32) for _ in range(3))
    total = len(grid.rects)
    for start, tables in nearshade.shares(shadows, grid.rects, chunk):
        at = grid.index[start:start + len(tables)]
        year[at], loss[at], hours[at] = reader.read(tables)
        if progress is not None:
            progress(start + len(tables), total)
    return Level(grid.step, year.reshape(grid.shape), loss.reshape(grid.shape), hours.reshape(grid.shape),
                 reader.free, reader.day_free)


# ---------------------------------------------------------------------------------------------------------------------
# 6. the key, the classes, the modules

def key_of(light: Light, surface: MapSurface, grid: Grid) -> bytes:
    """What a surface's figures at a grid are made of (resources.fingerprint): the computation's version, the light,
    the plane (tilt, azimuth, distance to the millimetre), the contour, the corners of the solids that can reach the
    grid, the step, the day. A solid that cannot reach leaves the key as it is."""
    return resources.fingerprint(VERSION, light.key, surface.tilt, surface.azimuth, round(surface.d, 3),
                                 np.asarray(surface.ring, dtype=float),
                                 [np.asarray(s.corners, dtype=float) for s in reaching(light, surface, grid.bounds)],
                                 grid.step, light.day, light.minutes)


def classes(loss: np.ndarray, inside: np.ndarray | None = None, under: np.ndarray | None = None,
            edges: tuple = LOSS_CLASSES) -> np.ndarray:
    """The class of each loss (uint8): i for edges[i] <= loss < edges[i + 1] (the last one up to its edge included);
    OUTSIDE off the surface (and for a loss not computed), UNDER under an obstacle."""
    loss = np.asarray(loss, dtype=float)
    out = np.searchsorted(np.asarray(edges[1:-1], dtype=float), np.clip(loss, edges[0], edges[-1]), side="right")
    out = out.astype(np.uint8)
    out[np.isnan(loss)] = OUTSIDE
    if inside is not None:
        out[~np.asarray(inside, dtype=bool)] = OUTSIDE
    if under is not None:
        out[np.asarray(under, dtype=bool)] = UNDER
    return out


@dataclass
class ModuleValues:
    """The figures of an array's modules, in the order of `keys`, in double precision (a few thousand values: their
    mean is the year's to its last digits); `free` the array's irradiance without the near
    shading (its parts after the rows), kWh/m² a year; `cast` whether the tables were cast here rather than read from
    the year's."""
    keys: list
    year: np.ndarray
    loss: np.ndarray
    hours: np.ndarray
    free: float
    day_free: float
    cast: bool


def _day_cells(light: Light) -> np.ndarray:
    return (np.asarray(light.day_weights.sum(axis=1)).ravel() > 0).reshape(light.needed.shape)


def module_values(light: Light, array_pass, *, chunk: int = nearshade.SHARE_CHUNK) -> ModuleValues:
    """The figures of the modules of an array of the year's first pass (simulate._ArrayPass), with the year's formula
    on its light after the rows: from the year's own tables (Shading.modules) when they hold the cells of the day,
    else cast here on the modules' planes (nearshade.module_planes), the same tables where the year has them."""
    a = array_pass.a
    reader = reader_of(light, a.tilt, a.azimuth, array_pass.beam_rows, array_pass.sky_rows, array_pass.ground_rows)
    near = array_pass.near
    placed = [pm for pm in a.placed if pm.key in a.connected] if a.connected else list(a.placed)
    shape = (len(nearshade.ELEVATIONS), len(nearshade.AZIMUTHS))
    if near is not None and near.modules is not None and not (_day_cells(light) & ~light.year_cells).any():
        keys, out, cast = list(near.keys), [], False
        for start in range(0, len(keys), chunk):
            resources.checkpoint()
            out.append(reader.read(near.modules[start:start + chunk]))
        parts = [np.concatenate(x) for x in zip(*out, strict=True)] if out else [np.zeros(0)] * 3
    elif a.obstacles and placed:
        by_key = {pm.key: pm for pm in placed}
        if near is not None:
            placed = [by_key[k] for k in near.keys if k in by_key]
        keys, cast = [pm.key for pm in placed], True
        parts = [np.zeros(len(placed)) for _ in range(3)]
        for plane in nearshade.module_planes(placed, a.tilt, a.azimuth):
            shadows = nearshade.cast(a.obstacles, a.tilt, a.azimuth, plane.d, plane.bounds, light.needed)
            for start, tables in nearshade.shares(shadows, plane.rects, chunk):
                at = plane.index[start:start + len(tables)]
                for p, v in zip(parts, reader.read(tables), strict=True):
                    p[at] = v
    else:
        keys, cast = [pm.key for pm in placed], False
        parts = reader.read(np.zeros((len(placed), *shape), dtype=np.float32))
    year, loss, hours = (np.asarray(p, dtype=np.float64) for p in parts)
    return ModuleValues(keys, year, loss, hours, reader.free, reader.day_free, cast)
