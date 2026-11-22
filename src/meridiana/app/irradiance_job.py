"""The sun map as a job of the common mechanism (study 45, package 4; study 48, chapter 3): `KIND` and `run`, the
function that runs in the job's processes. Without Qt.

Every process gets the same request (the project's photo, the folder of the weather, the store's folder, the finest
step, the day, the keys the window has already) and its place among the processes (`ctx.share`). Each one prepares the
project, the weather and the light of the site by itself, makes the plan (every surface with its key and what draws it
in plan) and sends it first; then it takes its own surfaces (`work.job.mine`, by weight: the lightest first) from the
coarse to the fine: a surface whose key is in the store is sent at once, the others are cast once and read at 2 m,
and only once every one of its surfaces has its preview it reads them at the finest step, sends them and keeps them
in the store. One process (the last) also gives the figures of the modules laid. What costs (the project, the
layouts, the light, the casts, the readers) stays in `ctx.kept` with its key: the next request on a warm process does
not make it again (another day reads again without casting).

To the window go small dicts and 32 bit vectors: the levels of the tiles (year, loss, hours), the masks of the grid,
the figures of the modules."""

from __future__ import annotations

import hashlib
import pickle
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from meridiana.app import jobs, pipeline, sun_map_image, weather_job
from meridiana.app.platform import log
from meridiana.app.work import store
from meridiana.app.work.job import GIB, Kind, Refused, mine
from meridiana.core.compute import resources
from meridiana.core.energy import irradiance_map as im
from meridiana.core.energy import meteo, system
from meridiana.i18n import N_

COARSE = 2.0            # m: the first pass, the preview (study 45, decision 5)
FINE = 0.5              # m: the finest step by default (the settings may say 1 or 0,25)
STORE = "sun_map"       # the store's folder under the program's caches
CAST_UNITS = 1.0        # progress: a cast counts this for each solid that reaches its surface (about a coarse tile)
PLAN = "plan"           # the keys of the results on the way that are not a surface's
FREE = "free"
MODULES = "modules"
PREVIEW = N_("preview")        # what the bar says of each pass (msgids), after the job's title: «Sun map  preview»
FIGURES = N_("modules")
FINEST = N_("finest tiles")

# What the map is made of (study 48, rule 7): the shapes and the obstacles, the sub-fields and their layouts, the
# site, what makes the light (the losses, the horizon: project:energy), the variant in hand; not the names.
KIND = Kind(name="sun_map", title=N_("Sun map"), run="meridiana.app.irradiance_job:run", where="process", processes=3,
            memory=2 * GIB, keep_warm=60.0, low_priority=True, on_change="restart",
            topics=("project:geometry", "project:subfields", "project:site", "project:energy", "project:variants",
                    "layout"))


WEATHER = "weather"     # what a result says is missing: {"missing": WEATHER, "site": (lat, lon)}


class NoWeather(Refused):
    """The weather of the site is not on this PC and may not be fetched (app/weather_job.refusal)."""


class _Missing(Exception):
    """The weather of the site is not on this PC and may be fetched: the job ends at once and says so, the owner
    fetches it (app/weather_job.py) and asks for the map again."""


def request_of(photo: dict, weather: Path | str, store_folder: Path | str | None, *, step: float = FINE,
               day: tuple = im.DAY, have=(), modules: bool = True, network: bool = False) -> dict:
    """The request of a map: `photo` the project as data (session.photo()), `weather` the folder of the weather's
    cache, `store_folder` where the levels are kept (None: nowhere), `step` the finest step, `day` (month, day) of the
    hours of sun, `have` the keys the receiver already holds at the finest step (skipped), `modules` whether to give
    the figures of the modules laid, `network` the settings' switch of PVGIS (whether a weather not on this PC may be
    fetched: the job only says it is missing, the owner fetches it)."""
    return {"photo": photo, "weather": str(weather), "store": str(store_folder) if store_folder else "",
            "step": float(step), "day": (int(day[0]), int(day[1])), "have": frozenset(have), "modules": bool(modules),
            "network": bool(network)}


def store_of(cache: Path | str) -> Path:
    """The store's folder under the program's caches (paths.cache)."""
    return Path(cache) / STORE


@dataclass
class Part:
    """A surface of the plan, as the process works on it."""
    surface: im.MapSurface
    cast_grid: im.Grid              # the coarsest grid: its box is cast once, for every step and day
    coarse: im.Grid | None          # None when the finest step is already this coarse (the cap raised it)
    fine: im.Grid
    key: bytes                      # of the figures at the finest step, with the day (im.key_of)
    cast_key: bytes                 # of the cast: the same without the day
    reach: int                      # the solids that reach it
    weight: float                   # what it costs, roughly: the order of the work


# ---------------------------------------------------------------------------------------------------------------------
# what the process keeps

def _digest(data) -> bytes:
    return hashlib.blake2b(pickle.dumps(data, protocol=5), digest_size=20).digest()


def _kept(kept: dict, name: str, key, make):
    """kept[name], made again with make() when its key is not `key`."""
    found = kept.get(name)
    if found is not None and found[0] == key:
        return found[1]
    kept.pop(name, None)            # the old one goes before the new one is made: never both in memory
    value = make()
    kept[name] = (key, value)
    return value


def _project(request: dict, kept: dict):
    """(project, layouts) of the photo: made again only for another photo; a layout whose inputs did not change is
    kept (jobs.layout_of with the layouts of the photo before)."""
    from meridiana.core.model import model

    def make():
        project = model.Project.from_json(request["photo"], check=False)
        before = kept.get("layouts") or {}
        results, keys, _laid = jobs.layout_of(project, before)
        kept["layouts"] = {k: (keys[k], r) for k, r in results.items() if k in keys}
        return project, {k: r for k, r in results.items() if not isinstance(r, Exception)}
    return _kept(kept, "project", _digest(request["photo"]), make)


def _weather(project, folder: Path, kept: dict, network: bool = False):
    """(Meteo, Horizon or None) of the site, without the network: _Missing when it is not on this PC and may be
    fetched, NoWeather when it may not (the year's rule, weather_job.refusal). The horizon as the year takes it
    (pipeline.horizon_of): a horizon that cannot be read is left out, as the year leaves it."""
    losses = system.losses_of(project)
    _climate, embedded = pipeline._embedded(project)
    key = (project.site.lat, project.site.lon, str(folder), losses.use_horizon,
           None if embedded is None else _digest(embedded))

    def make():
        if not pipeline.weather_at_hand(project, folder):
            why = weather_job.refusal(project, network)
            if why:
                raise NoWeather(why)
            raise _Missing()
        m = pipeline.weather_of(project, folder)
        hor = None
        if losses.use_horizon:
            try:
                hor = pipeline.horizon_of(project, folder, fetch=False)
            except meteo.MeteoError as error:
                log.complain("The sun map goes on without the horizon", error)
        return m, hor
    return _kept(kept, "weather", key, make)


def _light(project, folder: Path, day: tuple, kept: dict, network: bool = False) -> tuple[im.Light, im.Light]:
    """(the light of the site with the default day, the light of `day`): prepare() once for a weather and its losses,
    with_day() for another day."""
    m, hor = _weather(project, folder, kept, network)
    losses = system.losses_of(project)
    key = (kept["weather"][0], losses.albedo, losses.transposition, losses.use_horizon, losses.use_near)
    base = _kept(kept, "light", key, lambda: im.prepare(m, losses, hor))
    if tuple(day) == base.day:
        return base, base
    return base, _kept(kept, "day", (base.key, tuple(day)), lambda: im.with_day(base, day))


# ---------------------------------------------------------------------------------------------------------------------
# the plan

def _parts(project, results: dict, base: im.Light, step: float) -> list[Part]:
    """The parts of the surfaces with the light of the default day (`key` is then that day's: see _of_day)."""
    out = []
    for s in im.surfaces_of(project, results):
        fine = im.grid_of(s, step)
        coarse = im.grid_of(s, COARSE) if fine.step < COARSE else None
        cast_grid = coarse if coarse is not None else fine
        reach = len(im.reaching(base, s, cast_grid.bounds)) if len(fine.rects) else 0
        # the cast grows with the solids that reach, the reading with the tiles (study 45, chapter 10)
        weight = (1.0 + reach) * (1.0 + len(cast_grid.rects)) if len(fine.rects) else 0.0
        out.append(Part(s, cast_grid, coarse, fine, im.key_of(base, s, fine), im.key_of(base, s, cast_grid), reach,
                        weight))
    return out


def _of_day(parts: list[Part], base: im.Light, light: im.Light) -> list[Part]:
    """The parts with the keys of the day of `light` (the grids and the casts stay)."""
    if light.day == base.day:
        return parts
    return [replace(p, key=im.key_of(light, p.surface, p.fine)) for p in parts]


def _axes(s: im.MapSurface):
    from meridiana.core.energy import nearshade
    n, e1, e2 = nearshade.plane_axes(s.tilt, s.azimuth)
    return n, e1, e2


def plan_of(parts: list[Part], step: float, day: tuple, modules: bytes | None = None) -> dict:
    """What the window needs to draw every surface before its figures come: the surface, its key, its plane (normal,
    axes u and v, distance: a point of the plan (x, y) is on the surface at z = (d - n0 x - n1 y) / n2, and its tile is
    (floor(v / step) - iv, floor(u / step) - iu) with u = p.e1, v = p.e2), its finest grid, its contour on the plan and
    on the axes; `modules` the key of the modules' figures (None: no module laid). `id` changes with any key."""
    surfaces = []
    for p in parts:
        s, g = p.surface, p.fine
        n, e1, e2 = _axes(s)
        surfaces.append({"id": s.id, "name": s.name, "building": s.building, "modules": bool(s.modules),
                         "key": p.key, "tilt": s.tilt, "azimuth": s.azimuth, "d": s.d, "normal": tuple(map(float, n)),
                         "u": tuple(map(float, e1)), "v": tuple(map(float, e2)),
                         "ring": [tuple(q) for q in s.ring], "outline": np.asarray(s.outline, dtype=np.float32),
                         "area": s.area, "grid": _grid_head(g)})
    return {"id": _digest([[p.key for p in parts], modules]), "step": float(step), "day": tuple(day),
            "modules": modules, "surfaces": surfaces}


def _grid_head(g: im.Grid) -> dict:
    return {"step": float(g.step), "iu": int(g.iu), "iv": int(g.iv), "shape": tuple(int(x) for x in g.shape),
            "tiles": int(len(g.rects))}


def _level(p: Part, grid: im.Grid, level: im.Level | dict, fine: bool, stored: bool) -> dict:
    """A level as it goes to the window, with the raster of its picture (app/sun_map_image.py): what the picture owes
    to the geometry is made here, in the job's process, never on the window's thread."""
    get = level.get if isinstance(level, dict) else lambda name: getattr(level, name)
    outline = np.asarray(p.surface.outline, dtype=float) / grid.step - (grid.iu, grid.iv)
    return {"surface": p.surface.id, "key": p.key, "fine": fine, "stored": stored, **_grid_head(grid),
            "year": np.asarray(get("year"), dtype=np.float32), "loss": np.asarray(get("loss"), dtype=np.float32),
            "hours": np.asarray(get("hours"), dtype=np.float32), "inside": grid.inside, "under": grid.under,
            "free": float(get("free")), "day_free": float(get("day_free")),
            "raster": sun_map_image.raster(outline, grid.shape, grid.inside, grid.under)}


def _empty(grid: im.Grid, reader: im.Reader) -> im.Level:
    nan = np.full(grid.shape, np.nan, dtype=np.float32)
    return im.Level(grid.step, nan, nan.copy(), nan.copy(), reader.free, reader.day_free)


# ---------------------------------------------------------------------------------------------------------------------
# the job

class _Progress:
    """Units of work done over those to do, told to the bar: a cast counts CAST_UNITS for each solid that reaches,
    a reading one for each tile, the modules one each."""

    def __init__(self, ctx):
        self.ctx, self.done, self.total, self.phase = ctx, 0.0, 0.0, PREVIEW

    def tell(self):
        self.ctx.progress(self.done, max(self.total, self.done), self.phase)

    def add(self, units: float):
        self.done += units
        self.tell()


def run(request: dict, ctx):
    """The map of the photo's surfaces that fall to this process (see the module's text). The result: the counts of
    what this process did ({"cast", "read", "stored", "skipped", "modules"}); without the weather of the site, when it
    may be fetched, {"missing": WEATHER, "site": (lat, lon)} at once (nothing sent: the owner fetches it and asks
    again)."""
    kept = ctx.kept
    counts = {"cast": 0, "read": 0, "stored": 0, "skipped": 0, "modules": 0}
    project, results = _project(request, kept)
    ctx.checkpoint()
    folder = Path(request["weather"])
    try:
        base, light = _light(project, folder, request["day"], kept, request.get("network", False))
    except _Missing:
        return {"missing": WEATHER, "site": (float(project.site.lat), float(project.site.lon))}
    ctx.checkpoint()
    step = float(request["step"])
    parts = _kept(kept, "parts", (kept["project"][0], base.key, step), lambda: _parts(project, results, base, step))
    parts = _kept(kept, "parts_of_day", (kept["parts"][0], light.day), lambda: _of_day(parts, base, light))
    arrays = system.arrays_of(project, results) if request["modules"] else []
    figures = modules_key(light, arrays) if arrays else None
    ctx.partial(PLAN, plan_of(parts, step, light.day, figures))
    ctx.checkpoint()
    # what is cast or read for parts no longer in the plan is let go
    casts = kept.setdefault("casts", {})
    for k in set(casts) - {p.cast_key for p in parts}:
        del casts[k]
    readers = kept.setdefault("readers", {})
    for k in set(readers) - {(light.key, light.day, p.surface.tilt, p.surface.azimuth) for p in parts}:
        del readers[k]
    have = request["have"]
    folder_store = Path(request["store"]) if request["store"] else None
    index, count = ctx.share
    own = mine(parts, ctx.share, weight=lambda p: p.weight)
    progress = _Progress(ctx)
    todo = [p for p in own if p.key not in have]
    counts["skipped"] = len(own) - len(todo)
    # the store first: what is kept is sent at once and costs nothing more
    waiting = []
    for p in todo:
        found = store.read(folder_store, p.key) if folder_store is not None else None
        if found is not None and np.shape(found.get("year")) == p.fine.shape:
            ctx.partial(p.surface.id, _level(p, p.fine, found, fine=True, stored=True))
            counts["stored"] += 1
        else:
            waiting.append(p)
    if index != count - 1:
        arrays = []                 # the modules are the last process's
    progress.total = (sum(CAST_UNITS * p.reach for p in waiting if p.cast_key not in casts)
                      + sum(len(p.coarse.rects) for p in waiting if p.coarse is not None)
                      + sum(len(p.fine.rects) for p in waiting) + sum(a.modules for a in arrays))
    progress.tell()
    # the free numbers of this process's surfaces, as soon as they are known
    free = {}
    for p in waiting:
        ctx.checkpoint()
        reader = _reader(light, p.surface, readers)
        free[p.surface.id] = (reader.free, reader.day_free)
    if free:
        ctx.partial(f"{FREE}:{index}", free)
    # 1. the coarse pass: cast once, read at 2 m, sent (a surface whose finest step the cap raised to 2 m or more is
    # read at that step here, once)
    for p in waiting:
        ctx.checkpoint()
        shadows = _cast(base, p, casts, progress, counts)
        reader = _reader(light, p.surface, readers)
        if p.coarse is None:
            _fine(light, reader, shadows, p, folder_store, progress, counts, ctx)
            continue
        level = _read(light, reader, shadows, p.coarse, progress)
        ctx.partial(p.surface.id, _level(p, p.coarse, level, fine=False, stored=False))
    # 2. the modules laid, by one process
    if arrays:
        ctx.checkpoint()
        progress.phase = FIGURES
        counts["modules"] = _modules(project, arrays, figures, light, request, folder_store, progress, ctx)
    # 3. the fine pass: read, sent, kept in the store
    progress.phase = FINEST
    for p in waiting:
        if p.coarse is not None:
            ctx.checkpoint()
            _fine(light, _reader(light, p.surface, readers), casts.get(p.cast_key), p, folder_store, progress, counts,
                  ctx)
    progress.tell()
    return counts


def _fine(light: im.Light, reader: im.Reader, shadows, p: Part, folder_store: Path | None, progress: _Progress,
          counts: dict, ctx) -> None:
    """A part read at its finest step, sent, and kept in the store."""
    level = _read(light, reader, shadows, p.fine, progress)
    ctx.partial(p.surface.id, _level(p, p.fine, level, fine=True, stored=False))
    counts["read"] += 1
    if folder_store is None:
        return
    try:
        store.write(folder_store, p.key, {"year": level.year, "loss": level.loss, "hours": level.hours,
                                          "free": np.float64(level.free), "day_free": np.float64(level.day_free),
                                          "step": np.float64(level.step)})
    except OSError as error:        # the map is still right: it is computed again next time
        log.complain("A level of the sun map could not be kept", error)


def _reader(light: im.Light, s: im.MapSurface, readers: dict) -> im.Reader:
    key = (light.key, light.day, s.tilt, s.azimuth)
    if key not in readers:
        readers[key] = im.surface_reader(light, s)
    return readers[key]


def _cast(base: im.Light, p: Part, casts: dict, progress: _Progress, counts: dict):
    """The shadows of a part, cast once for every step and day (kept by the cast's key); None for a part without
    tiles."""
    if not len(p.fine.rects):
        return None
    if p.cast_key not in casts:
        casts[p.cast_key] = im.cast_surface(base, p.surface, p.cast_grid)
        counts["cast"] += 1
        progress.add(CAST_UNITS * p.reach)
    return casts[p.cast_key]


def _read(light: im.Light, reader: im.Reader, shadows, grid: im.Grid, progress: _Progress) -> im.Level:
    if shadows is None or not len(grid.rects):
        return _empty(grid, reader)
    start = progress.done

    def told(done, _total):
        progress.done = start + done
        progress.tell()
    level = im.read(light, reader, shadows, grid, progress=told)
    progress.done = start + len(grid.rects)
    return level


# ---------------------------------------------------------------------------------------------------------------------
# the modules

def _surface_id(project, sfid: str) -> str:
    """The id of the map's surface a sub-field's modules lie on (im.surfaces_of)."""
    sf = next((s for s in project.subfields if s.id == sfid), None)
    if sf is None:
        return ""
    if sf.support is not None and sf.support.enabled:
        return sf.id
    b = next((x for x in project.buildings if x.id == sf.building), None)
    if b is None:
        return ""
    i = b.pitch_index(sf.pitch)
    return f"{b.id}:{b.pitch_ref(i if i is not None else 0)}"


def modules_key(light: im.Light, arrays: list) -> bytes:
    """What the figures of the modules are made of: the computation, the light and its day, every loss (the rows'
    light is the year's), and for each array its plane, its rows, its modules and its obstacles."""
    return resources.fingerprint(im.VERSION, light.key, light.day, light.minutes, light.losses, [
        (a.key, a.tilt, a.azimuth, a.rows, a.pitch, a.slant, a.stack, a.stand_off, a.upright, a.thermal,
         sorted(a.connected or ()), [(pm.key, pm.corners, pm.z, pm.tilt, pm.azimuth) for pm in a.placed],
         [np.asarray(o.corners, dtype=float) for o in a.obstacles]) for a in arrays])


def _modules(project, arrays: list, key: bytes, light: im.Light, request: dict, folder_store: Path | None,
             progress: _Progress, ctx) -> int:
    """The figures of the modules laid, sent as one result on the way ("modules"): read from the store when their key
    is there, else computed (the year's first pass without the near shading, which the map casts the light way) and
    kept."""
    from meridiana.core.energy.simulate import _first_pass
    from meridiana.core.rules import registry
    losses = light.losses
    total = sum(a.modules for a in arrays)
    if key in request["have"]:
        progress.add(total)
        return 0
    found = store.read(folder_store, key) if folder_store is not None else None
    if found is not None:
        out = _modules_from(found)
        if out is not None:
            ctx.partial(MODULES, {"key": key, "arrays": out, "stored": True})
            progress.add(total)
            return len(out)
    first = _first_pass(light.meteo, arrays, None, replace(losses, use_near=False), light.horizon,
                        timezone=registry.effective_timezone(project), profile_id=project.regulatory_profile)
    out, kept = [], {}
    for i, ap in enumerate(first.per_array):
        ctx.checkpoint()
        values = im.module_values(light, ap)
        sfid = ap.a.key.split(".")[0]
        out.append({"array": ap.a.key, "subfield": sfid, "surface": _surface_id(project, sfid),
                    "tilt": float(ap.a.tilt), "azimuth": float(ap.a.azimuth), "keys": [str(k) for k in values.keys],
                    "year": values.year.astype(np.float32), "loss": values.loss.astype(np.float32),
                    "hours": values.hours.astype(np.float32), "free": float(values.free),
                    "day_free": float(values.day_free)})
        for name in ("year", "loss", "hours"):
            kept[f"{i}.{name}"] = out[-1][name]
        kept[f"{i}.keys"] = np.array(out[-1]["keys"], dtype=str)
        kept[f"{i}.head"] = np.array([out[-1]["array"], out[-1]["subfield"], out[-1]["surface"]], dtype=str)
        kept[f"{i}.figures"] = np.array([out[-1]["tilt"], out[-1]["azimuth"], out[-1]["free"], out[-1]["day_free"]])
        progress.add(ap.a.modules)
    ctx.partial(MODULES, {"key": key, "arrays": out, "stored": False})
    if folder_store is not None:
        kept["count"] = np.array(len(out))
        try:
            store.write(folder_store, key, kept)
        except OSError as error:
            log.complain("The modules of the sun map could not be kept", error)
    return len(out)


def _modules_from(found: dict) -> list | None:
    try:
        out = []
        for i in range(int(found["count"])):
            array, subfield, surface = (str(x) for x in found[f"{i}.head"])
            tilt, azimuth, free, day_free = (float(x) for x in found[f"{i}.figures"])
            out.append({"array": array, "subfield": subfield, "surface": surface, "tilt": tilt, "azimuth": azimuth,
                        "keys": [str(k) for k in found[f"{i}.keys"]], "year": found[f"{i}.year"].astype(np.float32),
                        "loss": found[f"{i}.loss"].astype(np.float32), "hours": found[f"{i}.hours"].astype(np.float32),
                        "free": free, "day_free": day_free})
        return out
    except (KeyError, ValueError, TypeError) as error:
        log.complain("The modules of the sun map kept in the store could not be read", error)
        return None
