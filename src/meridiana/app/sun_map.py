"""The sun map as the views see it (study 45, package 4): `SunMap`, without Qt. It asks the common mechanism
(app/work) for the map's job (app/irradiance_job.py), takes its plan and its results on the way, and keeps for every
surface what the plan and the 3D draw: its key, the level received (2 m or the finest step), the free number, whether
it is to be updated. The views ask it for classes (8 bit, for the quantity chosen), the legend, the value under the
pointer; changing the quantity or the classes computes nothing again.

A surface is `stale` when the level it shows is not of the key of the current plan (the project changed) and the new
one has not come yet: it keeps its old level, which the views dim, until the new one comes. A surface the change did
not touch keeps its level with its key: nothing is computed again for it.

From the tiles to the plan: a level has its grid (step, iu, iv, shape); the tile of row i and column j is the square
u in [(iu + j) step, (iu + j + 1) step], v in [(iv + i) step, (iv + i + 1) step] on the axes of the surface's plane; a
point (u, v) of the plane is u e1 + v e2 + d n in space, and its plan's (x, y) are the first two coordinates.
`SurfaceMap.transform(level)` gives the affine map from (column, row) to the plan's (x, y): the image of a level drawn
with it lies on the surface."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from meridiana.app import irradiance_job as job
from meridiana.app import weather_job
from meridiana.app.platform import disk_cap, log
from meridiana.app.work import store as work_store
from meridiana.core.compute import resources
from meridiana.core.energy import irradiance_map as im
from meridiana.i18n import _, number

QUANTITIES = ("loss", "year", "hours")      # % of the year's irradiance the obstacles take, kWh/m² a year, h of sun
COLOURS = ("auto", "surfaces", "modules")   # what is coloured (study 45, decision 2)
STEPS = (1.0, 0.5, 0.25)                    # the finest step the settings offer (decision 5)
SCALES = ("amber", "viridis", "cividis")    # the colour scales (decision 3; the colours are the style's)
EVERYTHING = "*"                            # what the listeners are told when every surface changed
MODULES = "modules"                         # ...and when the modules' figures changed

# The classes of kWh/m² and of the hours of sun: round steps, chosen here and nowhere else (a choice for Daniel: the
# loss has its decided limits, im.LOSS_CLASSES). As many classes as the loss's at most, a step of 1, 2, 2,5 or 5 times
# a power of ten, the limits multiples of the step around the figures shown.
ROUND_STEPS = (1.0, 2.0, 2.5, 5.0)
CLASSES = len(im.LOSS_CLASSES) - 1


def round_edges(low: float, high: float, classes: int = CLASSES) -> tuple:
    """The limits of at most `classes` classes of a round step that hold low..high."""
    if not (math.isfinite(low) and math.isfinite(high)):
        return (0.0, 1.0)
    if high <= low:
        high = low + 1.0
    span = (high - low) / classes
    power = 10.0 ** math.floor(math.log10(span))
    for factor in ROUND_STEPS + (10.0,):
        step = factor * power
        start = math.floor(low / step) * step
        count = math.ceil((high - start) / step - 1e-9)
        if count <= classes:
            return tuple(round(start + k * step, 6) for k in range(max(1, count) + 1))
    return tuple(round(low + k * span, 6) for k in range(classes + 1))      # never reached: 10 x power always fits


@dataclass
class SurfaceMap:
    """A surface of the plan: what draws it (its plane, its contour, its finest grid) and what it shows: `shown` the
    key of the level held (in SunMap's cache), `free` and `day_free` its irradiance without the near shading and
    its hours of sun that day (the number written on it)."""
    id: str
    name: str
    building: str | None
    modules: bool
    key: bytes
    tilt: float
    azimuth: float
    d: float
    normal: tuple
    u: tuple
    v: tuple
    ring: list
    outline: np.ndarray
    grid: dict
    shown: bytes | None = None
    fine: bool = False
    free: float | None = None
    day_free: float | None = None
    box: tuple = field(default=(0.0, 0.0, 0.0, 0.0), repr=False)
    xy: np.ndarray = field(default=None, repr=False)

    @property
    def stale(self) -> bool:
        """It shows a level of another key than the plan's: to be updated."""
        return self.shown is not None and self.shown != self.key

    def transform(self, level: dict) -> tuple:
        """(x0, y0, ax, ay, bx, by): the plan's point of the corner (column c, row r) of the level's grid is
        (x0 + c ax + r bx, y0 + c ay + r by)."""
        s = level["step"]
        u0, v0 = level["iu"] * s, level["iv"] * s
        o = [u0 * self.u[k] + v0 * self.v[k] + self.d * self.normal[k] for k in range(2)]
        return (o[0], o[1], s * self.u[0], s * self.u[1], s * self.v[0], s * self.v[1])

    def contains(self, x: float, y: float) -> bool:
        x0, y0, x1, y1 = self.box
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            return False
        px, py = self.xy[:, 0], self.xy[:, 1]
        qx, qy = np.roll(px, -1), np.roll(py, -1)
        crosses = (py > y) != (qy > y)
        with np.errstate(divide="ignore", invalid="ignore"):
            at = px + (y - py) * (qx - px) / (qy - py)
        return bool(np.count_nonzero(crosses & (x < at)) % 2)

    def height_at(self, x: float, y: float) -> float:
        n = self.normal
        return (self.d - n[0] * x - n[1] * y) / n[2] if abs(n[2]) > 1e-9 else -math.inf


def _size(level: dict) -> int:
    return sum(v.nbytes for v in level.values() if isinstance(v, np.ndarray)) + 512


class SunMap:
    """The map's state for the views. `center` the jobs' Center, `session` the ProjectSession, `weather` the folder
    of the weather's cache, `store` the store's folder (job.store_of(paths.cache); None: nothing kept on disk),
    `settings` the Config (the sun_map_* fields, network_pvgis) or None for the defaults (and no network). Every
    method runs on the window's thread; `subscribe(listener)`: listener(what) with the set of the surfaces' ids that
    changed, EVERYTHING or MODULES.

    Without the weather of the site (decided by Daniel on 14/11/2026): the map's job finds it missing in its process
    (nothing is read from the disk on the window's thread) and ends at once; the map then asks the Center for the
    weather's job (app/weather_job.py: the bar's row, Cancel, the year's consent to the network) and, once it is done,
    for the map again. A weather that cannot be fetched is one sentence (`error`, and the status bar from the Center);
    Cancel during the fetch leaves the map without its job."""

    def __init__(self, center, session, weather: Path, store: Path | None = None, settings=None, *,
                 cache_limit=None):
        self.center, self.session, self.settings = center, session, settings
        self.weather, self.store = Path(weather), (Path(store) if store else None)
        self.on = False
        self.weather_handle = None                          # the weather's job, while the map waits for it
        self._fetched: tuple | None = None                  # the site whose weather that job fetched last
        self.quantity = _choice(getattr(settings, "sun_map_quantity", "loss"), QUANTITIES)
        self.colour = _choice(getattr(settings, "sun_map_colour", "auto"), COLOURS)
        self.step = float(getattr(settings, "sun_map_step", job.FINE))
        if self.step not in STEPS:
            self.step = job.FINE
        self.day = day_of(getattr(settings, "sun_map_day", ""))
        self.scale = _choice(getattr(settings, "sun_map_scale", "amber"), SCALES)
        self.handle = None
        self.plan_id: bytes | None = None
        self.surfaces: dict[str, SurfaceMap] = {}           # in the plan's order
        self.modules: dict[str, list] = {}                  # surface id -> the arrays laid on it (job._modules)
        self.modules_key: bytes | None = None               # of the modules' figures in hand
        self.modules_wanted: bytes | None = None            # of those of the current plan
        self.error = ""
        self.done = False
        # the project changed in what the map is made of and the new plan has not come: every surface may be old, the
        # views dim them at once (the plan, when it comes, says which keep their map)
        self.changing = False
        self.counts: list = []                              # what each process of the last job did (job.run)
        self.levels = resources.Cache(cache_limit or (lambda: resources.cache_limit("shading") // 4), _size)
        self._fine: set = set()                             # the keys of the finest levels received
        self._classes: dict = {}
        self._edges: dict = {}
        self._module_index: dict | None = None
        self._listeners: list = []
        session.subscribe(self._changed)

    # what the views do

    def subscribe(self, listener) -> None:
        self._listeners.append(listener)

    def set_on(self, on: bool) -> None:
        """On: the map asked for (what is kept comes at once); off: its job cancelled, what came is kept for the next
        time."""
        on = bool(on)
        if on == self.on:
            return
        self.on = on
        if on:
            self._fetched = None                            # a new gesture: the weather may be fetched again
            self.request()
        else:
            self._cancel()
            self.changing = False
        self._tell({EVERYTHING})

    def set_quantity(self, quantity: str) -> None:
        """loss, year or hours: only the classes change, nothing is computed."""
        quantity = _choice(quantity, QUANTITIES)
        if quantity != self.quantity:
            self.quantity = quantity
            self._tell({EVERYTHING})

    def set_colour(self, colour: str) -> None:
        colour = _choice(colour, COLOURS)
        if colour != self.colour:
            self.colour = colour
            self._tell({EVERYTHING})

    def set_scale(self, scale: str) -> None:
        scale = _choice(scale, SCALES)
        if scale != self.scale:
            self.scale = scale
            self._tell({EVERYTHING})

    def set_day(self, day: tuple) -> None:
        """Another day of the hours of sun: read again (the shadows cast are kept by the warm processes)."""
        day = (int(day[0]), int(day[1]))
        if day != self.day:
            self.day = day
            if self.on:
                self.request()

    def set_step(self, step: float) -> None:
        step = float(step)
        if step in STEPS and step != self.step:
            self.step = step
            if self.on:
                self.request()

    def request(self, settle: bool = False):
        """The map's job sent to the Center (only the last one counts); `settle`: after the kind's quiet (a change
        of the project). The Handle. While the weather's job runs the map waits for it: asked when it is done."""
        self.error, self.done, self.counts = "", False, []
        if self.weather_handle is not None and self.weather_handle.active:
            return self.handle
        self.handle = self.center.submit(job.KIND, build=self._build, on_partial=self._partial, on_done=self._done,
                                         on_failed=self._failed, settle=settle)
        return self.handle

    def close(self) -> None:
        self._cancel()
        if self._changed in self.session.listeners:
            self.session.listeners.remove(self._changed)
        if self.store is not None:
            disk_cap.protect_soon(self.store, job.STORE, ())        # nothing of the store in use any more

    def _protect(self) -> None:
        """The levels of the plan in hand (each surface's key, the modules') declared in use: the ceiling of the stores
        on disk never takes them while this map is open (disk_cap; written off the window's thread)."""
        if self.store is None:
            return
        keys = [s.key for s in self.surfaces.values()] + ([self.modules_wanted] if self.modules_wanted else [])
        disk_cap.protect_soon(self.store, job.STORE, {work_store.name(k) for k in keys if k})

    # what the views read

    @property
    def busy(self) -> bool:
        """The map's job, or the weather's it waits for, in hand."""
        return any(h is not None and h.active for h in (self.handle, self.weather_handle))

    def level_of(self, sid: str) -> dict | None:
        """The level a surface shows (its key may be an old one: SurfaceMap.stale), or None."""
        s = self.surfaces.get(sid)
        return None if s is None or s.shown is None else self.levels.get(s.shown)

    def layers(self, sid: str) -> tuple[bool, bool]:
        """(the surface coloured, its modules coloured) for what to colour and the quantity (study 45, decision 2:
        for the kWh/m², where the modules are tilted on the surface only the modules)."""
        s = self.surfaces.get(sid)
        if s is None:
            return (False, False)
        laid = bool(self.modules.get(sid)) or s.modules
        if self.colour == "surfaces":
            return (True, False)
        if self.colour == "modules":
            return (False, laid)
        if not laid:
            return (True, False)
        tilted = any(abs(a["tilt"] - s.tilt) > 0.5 or abs(_turn(a["azimuth"] - s.azimuth)) > 0.5
                     for a in self.modules.get(sid, ()))
        return (not (self.quantity == "year" and tilted), True)

    def edges(self) -> tuple:
        """The limits of the classes of the quantity chosen: the decided ones for the loss, round steps around the
        figures shown for the others (round_edges)."""
        if self.quantity == "loss":
            return im.LOSS_CLASSES
        found = self._edges.get(self.quantity)
        if found is None:
            low, high = math.inf, -math.inf
            for sid in self.surfaces:
                level = self.level_of(sid)
                if level is not None and np.isfinite(level[self.quantity]).any():
                    values = level[self.quantity]
                    low, high = min(low, float(np.nanmin(values))), max(high, float(np.nanmax(values)))
                for a in self.modules.get(sid, ()):
                    if len(a[self.quantity]):
                        low, high = min(low, float(a[self.quantity].min())), max(high, float(a[self.quantity].max()))
            found = self._edges[self.quantity] = round_edges(low, high)
        return found

    def classes_of(self, sid: str) -> np.ndarray | None:
        """The class of each tile of the level a surface shows (uint8, the level's shape; im.OUTSIDE off the
        surface, im.UNDER under an obstacle), for the quantity chosen; None without a level."""
        s = self.surfaces.get(sid)
        level = self.level_of(sid)
        if s is None or level is None:
            return None
        edges = self.edges()
        key = (sid, s.shown, level["fine"], self.quantity, edges)
        found = self._classes.get(sid)
        if found is not None and found[0] == key:
            return found[1]
        out = im.classes(level[self.quantity], level["inside"], level["under"], edges=edges)
        self._classes[sid] = (key, out)
        return out

    def module_classes(self, array: dict) -> np.ndarray:
        """The class of each module of an array (one of self.modules[surface])."""
        return im.classes(array[self.quantity], edges=self.edges())

    def legend(self) -> dict:
        """What the legend says: the quantity, its unit, the limits and the rows of the classes, the scale, the planes
        the figures are on (study 45, decision 6), and whether something is still to come."""
        edges = self.edges()
        unit = {"loss": "%", "year": "kWh/m²", "hours": "h"}[self.quantity]        # the same in every language
        title = {"loss": _("Loss to the shadows"), "year": _("Irradiance in the year"),
                 "hours": _("Hours of sun on {day}").format(day=day_text(self.day))}[self.quantity]
        digits = 0 if self.quantity != "hours" or all(float(e).is_integer() for e in edges) else 1
        rows = [_("from {low} to {high} {unit}").format(low=number(lo, digits), high=number(hi, digits), unit=unit)
                for lo, hi in zip(edges[:-1], edges[1:], strict=True)]
        surfaces = modules = False
        for sid in self.surfaces:
            a, b = self.layers(sid)
            surfaces, modules = surfaces or a, modules or b
        planes = ([_("plane of the pitch")] if surfaces else []) + ([_("plane of the modules")] if modules else [])
        return {"quantity": self.quantity, "title": title, "unit": unit, "edges": tuple(edges), "rows": rows,
                "scale": self.scale, "planes": planes, "stale": self.changing or any(s.stale for s in self.surfaces.values()),
                "partial": any(s.shown is None or not s.fine for s in self.surfaces.values()) or self.busy}

    def value_at(self, x: float, y: float) -> dict | None:
        """The figures under the pointer at the plan's (x, y): the highest surface there with a level ({surface,
        name, year, loss, hours, step, stale}), None elsewhere."""
        best, top = None, -math.inf
        for s in self.surfaces.values():
            if s.shown is None or not s.contains(x, y):
                continue
            z = s.height_at(x, y)
            if z > top:
                best, top = s, z
        if best is None:
            return None
        level = self.levels.get(best.shown)
        if level is None:
            return None
        p = (x, y, top)
        u = sum(p[k] * best.u[k] for k in range(3))
        v = sum(p[k] * best.v[k] for k in range(3))
        step = level["step"]
        i, j = math.floor(v / step) - level["iv"], math.floor(u / step) - level["iu"]
        rows, cols = level["shape"]
        if not (0 <= i < rows and 0 <= j < cols) or not math.isfinite(float(level["year"][i, j])):
            return None
        return {"surface": best.id, "name": best.name, "year": float(level["year"][i, j]),
                "loss": float(level["loss"][i, j]), "hours": float(level["hours"][i, j]), "step": step,
                "stale": best.stale}

    def module_at(self, subfield: str, key: str) -> dict | None:
        """The figures of one module laid ({year, loss, hours}), or None."""
        if self._module_index is None:
            self._module_index = {}
            for arrays in self.modules.values():
                for a in arrays:
                    for n, k in enumerate(a["keys"]):
                        self._module_index[(a["subfield"], k)] = (a, n)
        found = self._module_index.get((subfield, str(key)))
        if found is None:
            return None
        a, n = found
        return {"year": float(a["year"][n]), "loss": float(a["loss"][n]), "hours": float(a["hours"][n])}

    # the job

    def have(self) -> frozenset:
        """The keys whose finest level (and the modules') is in hand: the job skips them."""
        self._fine = {k for k in self._fine if k in self.levels}
        return frozenset(self._fine | ({self.modules_key} if self.modules_key else set()))

    def _network(self) -> bool:
        """The settings' switch of PVGIS (read at each request: a change in the settings counts from the next)."""
        return bool(getattr(self.settings, "network_pvgis", False))

    def _build(self) -> dict:
        return job.request_of(self.session.photo(), self.weather, self.store, step=self.step, day=self.day,
                              have=self.have(), network=self._network())

    # the weather, when the map's job found it missing

    def _fetch(self, site: tuple) -> None:
        """The weather's job, then the map again (_fetched_weather). Once per site and gesture: a map that still
        finds missing the weather just fetched for its site says so instead of fetching it again."""
        if self._fetched is not None and tuple(site) == self._fetched:
            self._failed(None, _("The weather of the site was fetched but the sun map could not read it: see the "
                                 "log."))
            log.complain("The sun map", RuntimeError(f"the weather fetched for {site} is still missing in {self.weather}"))
            if getattr(self.center, "tell", None) is not None:
                self.center.tell(self.error)
            return
        self.weather_handle = self.center.submit(weather_job.KIND, build=self._weather_build,
                                                 on_done=self._fetched_weather, on_failed=self._failed)

    def _weather_build(self) -> dict:
        return weather_job.request_of(self.session.photo(), self.weather, self._network())

    def _fetched_weather(self, result, _stale: bool) -> None:
        self._fetched = tuple(result["site"])
        if self.on:
            self.request()

    def _partial(self, key: str, data) -> None:
        if key == job.PLAN:
            self._plan(data)
        elif key.startswith(job.FREE):
            changed = set()
            for sid, (free, day_free) in data.items():
                s = self.surfaces.get(sid)
                if s is not None:
                    s.free, s.day_free = free, day_free
                    changed.add(sid)
            self._tell(changed)
        elif key == job.MODULES:
            if self.modules_wanted is not None and data["key"] != self.modules_wanted:
                return                                  # of a plan that is no longer the one in hand
            self.modules = {}
            for a in data["arrays"]:
                self.modules.setdefault(a["surface"], []).append(a)
            self.modules_key, self._module_index = data["key"], None
            self._edges.clear()
            self._tell({MODULES})
        else:
            self._level(data)

    def _plan(self, plan: dict) -> None:
        if plan["id"] == self.plan_id:
            if self.changing:                           # the change touched no surface's figures
                self.changing = False
                self._tell({EVERYTHING})
            return
        self.changing = False
        before = self.surfaces
        self.plan_id, self.surfaces = plan["id"], {}
        for item in plan["surfaces"]:
            s = SurfaceMap(item["id"], item["name"], item["building"], item["modules"], item["key"], item["tilt"],
                           item["azimuth"], item["d"], item["normal"], item["u"], item["v"], item["ring"],
                           item["outline"], item["grid"])
            xy = np.asarray(s.ring, dtype=float).reshape(-1, 2)
            s.xy = xy
            s.box = (float(xy[:, 0].min()), float(xy[:, 1].min()), float(xy[:, 0].max()), float(xy[:, 1].max()))
            old = before.get(s.id)
            if s.key in self.levels:                    # the same figures, held already (unchanged, or undone)
                s.shown, s.fine = s.key, bool(self.levels.get(s.key)["fine"])
            elif old is not None and old.shown is not None:
                s.shown, s.fine = old.shown, old.fine   # stale until the new one comes
            if old is not None and old.key == s.key:
                s.free, s.day_free = old.free, old.day_free
            self.surfaces[s.id] = s
        self.modules_wanted = plan.get("modules")
        if self.modules_wanted is None:                 # no module laid any more
            self.modules, self.modules_key, self._module_index = {}, None, None
        self._classes.clear()
        self._edges.clear()
        self._protect()
        self._tell({EVERYTHING})

    @property
    def modules_stale(self) -> bool:
        """The modules' figures in hand are not those of the current plan, and the new ones have not come."""
        return self.modules_key is not None and self.modules_key != self.modules_wanted

    def _level(self, data: dict) -> None:
        s = self.surfaces.get(data["surface"])
        if s is None or data["key"] != s.key:
            return                                      # of a plan that is no longer the one in hand
        held = self.levels.get(s.key)
        if held is not None and held["fine"] and not data["fine"]:
            return                                      # the finest is here already
        self.levels.put(s.key, data, cost=float(data["tiles"]))
        if data["fine"]:
            self._fine.add(s.key)
        s.shown, s.fine, s.free, s.day_free = s.key, bool(data["fine"]), data["free"], data["day_free"]
        self._edges.clear()                             # the round limits follow the figures shown
        self._tell({s.id})

    def _done(self, result, _stale: bool) -> None:
        results = result if isinstance(result, list) else [result]
        missing = next((r for r in results if isinstance(r, dict) and r.get("missing") == job.WEATHER), None)
        if missing is not None:
            self._fetch(missing["site"])
            return
        self._fetched = None
        self.done, self.changing = True, False
        self.counts = results
        self._tell({EVERYTHING})

    def _failed(self, _kind, message: str) -> None:
        self.error, self.changing = message, False
        self._tell({EVERYTHING})

    def _cancel(self) -> None:
        for handle in (self.handle, self.weather_handle):
            if handle is not None and handle.active:
                self.center.cancel(handle)

    def _changed(self, topics: set) -> None:
        """The session's listener: another project forgets the plan; a change of what the map is made of, while
        no job is in hand, asks for it again after the quiet (one in hand is restarted by the Center)."""
        if "file" in topics:
            self.plan_id, self.surfaces, self.modules, self.modules_key = None, {}, {}, None
            self.modules_wanted = None
            self._module_index = None
            self._classes.clear()
            self._edges.clear()
            self._tell({EVERYTHING})
        if self.on and job.KIND.follows(topics):
            if not self.changing and self.surfaces:
                self.changing = True
                self._tell({EVERYTHING})
            if not self.busy:
                self.request(settle=True)

    def _tell(self, what: set) -> None:
        if not what:
            return
        for listener in list(self._listeners):
            try:
                listener(what)
            except Exception as error:      # a view's mistake: said, and the others are told
                log.complain("A view of the sun map failed", error)


def _choice(value, allowed: tuple):
    return value if value in allowed else allowed[0]


def _turn(angle: float) -> float:
    return (angle + 180.0) % 360.0 - 180.0


def day_of(text: str) -> tuple:
    """(month, day) of a setting "MM-DD"; the map's default day (im.DAY) for anything else."""
    try:
        month, day = (int(x) for x in str(text).split("-"))
        time.strptime(f"2026-{month:02d}-{day:02d}", "%Y-%m-%d")
        return (month, day)
    except ValueError:
        return im.DAY


def day_text(day: tuple) -> str:
    """«21 December» («21 dicembre»), with a no-break space: a date never goes to the next line in the middle (R564,
    the figures at the pointer)."""
    from meridiana.core.energy.worked import months
    return f"{day[1]} {months()[day[0] - 1]}"
