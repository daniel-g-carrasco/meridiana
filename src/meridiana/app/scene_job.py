"""The 3D scene of the project as a job of the mechanism (R598, docs/studio/48-lavori-pesanti.md, chapter 6, step 5):
mesh.project_scene in a process for every size of project, from the session's photo, only the last request counting;
before, the window made it on its own thread under 600 points and in a QRunnable above, which held the interpreter
while the other views took a change (Rho: 16-23 ms of the window in each gesture; model A: the views told of a change
waited 100-470 ms for the thread of the pool).

The job runs in the layout's process (`Kind.home`), as the plant (app/plant_job.py): the layouts it reads are those that
process keeps (`ctx.kept`, by sub-field and key, app/layout_job.py), so they never travel; one it does not keep it lays
out itself when its key is that of the photo's project, and what it cannot have so (a layout of before) it asks for
(`missing`), and the window sends it with the next request. The props the window shows as models stay the window's
(SceneBackend._decorated): the request names the indices of those the scene draws itself. The answer is the arrays of
mesh.project_scene (the triangles, the modules' table, the owners of the triangles) and the file of the modules'
instances, written here (`instance_file`) instead of on the window's thread. The strings of the Plant in the 3D
(viewaids.string_segments, 10-17 ms of each gesture on Rho with the 3D on show) are a kind of their own (`STRINGS`),
in the same process: they change without the scene (a string drawn) and the scene without them.

`Scenes` is the job's one owner on the window's thread (no Qt): `ask()` after a change; a job on its way goes to its end
and the next one comes after it (one stopped late would keep the layout's process busy, and the layouts wait for it);
an answer is taken (its `pieces`, Center.piece, each timed under its name) only when nothing the scene is made of has
changed since it was asked (`generation`, which the owner moves at every such change); otherwise it is dropped, and the
change that made it old has asked for the next one. A process that fails leaves the scene of before, with its sentence
in the status bar (Center.tell)."""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path

import numpy as np

from meridiana.app import layout_job
from meridiana.app.platform import log
from meridiana.app.work.job import Kind
from meridiana.i18n import N_

SLOT = "scene"
STRINGS_SLOT = "scene_strings"
TRIES = 3                       # answers «missing» in a row before the job is said to have failed

KIND = Kind(name="scene", title=N_("3D view"), run="meridiana.app.scene_job:run", where="process", processes=1,
            keep_warm=layout_job.SESSION, low_priority=layout_job.KIND.low_priority, topics=(), settle=0.0,
            cancellable=False, home=layout_job.KIND.name)
STRINGS = Kind(name="scene_strings", title=N_("3D view"), run="meridiana.app.scene_job:run_strings", where="process",
               processes=1, keep_warm=layout_job.SESSION, low_priority=layout_job.KIND.low_priority, topics=(),
               settle=0.0, cancellable=False, home=layout_job.KIND.name)


def instance_file(directory: Path, table: np.ndarray) -> Path:
    """Qt 6.12 FileInstancing v1, exact mesh.module_table layout (20 float32 per instance).

    Header verified against qt/qtquick3d 6.12 src/quick3d/qquick3dinstancing.cpp.
    Content-addressed files stay alive with the scene: Qt memory-maps them on its render thread.
    """
    table = np.asarray(table, dtype='<f4')
    if table.ndim != 2 or table.shape[1] != 20 or not np.isfinite(table).all():
        raise ValueError('An instance table must contain finite rows of 20 floats')
    payload = struct.pack('<4sHHIII', b'QtIR', 1, 0, 80, 20, len(table)) + table.tobytes()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (hashlib.sha256(payload).hexdigest() + '.bin')
    if not path.exists():
        path.write_bytes(payload)
    return path


def ribbons(segments) -> tuple:
    """Square tubes as in mesh.ribbons for the 3D's ribbon geometry (gui/backend/scene_geometry.RibbonGeometry): the
    endpoints, the unit-width displacements (expanded in the vertex shader in screen pixels), the colours and the
    bounds, 5 m wider ((low, high) as floats, None without a segment)."""
    from meridiana.core.geometry import mesh
    segs = np.asarray(segments, dtype=np.float64).reshape(-1, 2, 3)
    segs = segs[np.linalg.norm(segs[:, 1]-segs[:, 0], axis=1) > 1e-9]
    positions, _, colours = mesh.ribbons(segs, 1., (1., 1., 1.))
    endpoints = np.concatenate([
        segs[:, [0, 1, 1]].reshape(-1, 3), segs[:, [0, 1, 0]].reshape(-1, 3)
    ]) if len(segs) else np.zeros((0, 3))
    endpoints = np.tile(endpoints, (4, 1))
    bounds = ((tuple(map(float, positions.min(0)-5)), tuple(map(float, positions.max(0)+5)))
              if len(positions) else None)
    return endpoints, positions-endpoints, colours, bounds


def made(project, results: dict, props=None, cache=None) -> dict:
    """The scene of `project` on these layouts: mesh.project_scene, the props of `props` (indices) alone when given,
    and the modules' instance file under `cache` when given (its path as text, "" without)."""
    from meridiana.core.geometry import mesh
    if props is not None:
        project.props = [project.props[i] for i in props]
    owners = []
    triangles, table, _edges = mesh.project_scene(project, results, owners=owners)
    path = str(instance_file(Path(cache), table)) if cache else ""
    return {"triangles": triangles, "table": table, "owners": owners, "modules": path}


def _inputs(request: dict, ctx):
    """The photo's project and the layouts the window holds (by their keys), from those the layout's process keeps;
    (project, results, missing)."""
    from meridiana.app.session import project_from
    kept = ctx.kept.setdefault("layouts", {})          # layout_job's: (sub-field, key) -> result
    keys = request["keys"]
    results, missing = layout_job.from_kept(kept, keys, sent=request.get("layouts"))
    ctx.checkpoint()
    project = project_from(request["photo"])
    if missing:
        layout_job.lay_missing(project, kept, keys, results, missing)
    ctx.checkpoint()
    return project, {sid: results[sid] for sid in keys if sid in results}, missing


def run(request: dict, ctx) -> dict:
    """In the layout's process: the scene of the photo's project on the layouts the window holds (by their keys), or
    what is missing to make it."""
    project, results, missing = _inputs(request, ctx)
    if missing:
        return {"missing": missing}
    return made(project, results, request.get("props"), request.get("cache"))


def run_strings(request: dict, ctx) -> dict:
    """In the layout's process: the strings of the Plant in 3D (viewaids.string_segments: the segments between the
    modules of each string and the crosses of the optimizers) and their tubes for the GPU (`ribbons`), or what is
    missing to make them."""
    from meridiana.app.view import viewaids
    project, results, missing = _inputs(request, ctx)
    if missing:
        return {"missing": missing}
    lines, crosses = viewaids.string_segments(project, results)
    return {"lines": lines, "crosses": crosses, "ribbons": (ribbons(lines), ribbons(crosses))}


class Scenes:
    """The scene of one session for its 3D view. `center` is the window's jobs' Center, or a callable that gives it.
    `extra()` gives what the window adds to a request (the props it draws itself, the folder of the instance files),
    called when the job starts. An answer still current is taken by `pieces`, (name, call(answer)) one after the other
    on the window's turns (Center.piece), as long as the owner is open and nothing changed meanwhile. `changed()` is
    told whenever `busy()` may have changed. `kind` and `slot`: the scene's (KIND), or the strings' (STRINGS)."""

    def __init__(self, session, center, pieces, extra=None, changed=None, kind=KIND, slot=SLOT):
        self.session, self._center, self._centre = session, center, None
        self.kind, self.slot = kind, slot
        self._pieces, self._extra, self._told = tuple(pieces), extra, changed
        self.generation = 0                     # moved by the owner at every change the scene is made of
        self._taking = 0                        # the generation whose pieces are still to come, 0 for none
        self._handle = None
        self._asked = None                      # the generation the job on its way was asked at
        self._again = False                     # asked while a job was on its way: one more after it
        self._send: set = set()                 # the layouts the process asked for, sent with the next request
        self._tries = 0
        self._closed = False

    @property
    def center(self):
        if self._centre is None:
            self._centre = self._center() if callable(self._center) else self._center
        return self._centre

    def busy(self) -> bool:
        """Whether a scene is on its way, about to be asked again, or being taken."""
        return bool(self._again or self._taking or (self._handle is not None and self._handle.active))

    def ask(self) -> None:
        """The scene of the project in hand: now, or after the job on its way (only the last request counting)."""
        if self._closed:
            return
        was = self.busy()
        if self._handle is not None and self._handle.active:
            self._again = self._again or self._handle.state != "settling"    # not started: asked when it starts
        else:
            self._again = False
            self._handle = self.center.submit(self.kind, build=self._request, on_done=self._done,
                                              on_failed=self._failed, slot=self.slot, settle=True)
        if not was:
            self._changed()

    def current(self, generation) -> bool:
        return not self._closed and generation == self.generation

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        handle, self._handle, self._again, self._taking = self._handle, None, False, 0
        if handle is not None and handle.active:
            handle.cancel()

    # inside

    def _changed(self) -> None:
        if self._told is not None and not self._closed:
            self._told()

    def _request(self) -> dict:
        """Made when the job starts (Center.build): the photo of now and the keys of the layouts in hand."""
        s = self.session
        good = s.good_results()
        request = {"photo": s.photo(), "keys": {sid: s.layout_keys.get(sid) for sid in good}}
        if self._extra is not None:
            request.update(self._extra())
        send, self._send = self._send, set()
        if send:
            request["layouts"] = {sid: good[sid] for sid in send if sid in good}
        self._asked = self.generation
        return request

    def _done(self, answer, _stale) -> None:
        self._handle = None
        asked, self._asked = self._asked, None
        missing = answer.get("missing")
        if missing is not None:
            self._tries += 1
            if self._tries >= TRIES:
                self._tries = 0
                log.complain(f"The 3D could not be made ({self.kind.name})", RuntimeError(f"still missing: {missing}"))
            else:
                self._send = set(missing)
                self._again = True
        else:
            self._tries = 0
            if asked is not None and self.current(asked) and self._pieces:
                self._taking = asked
                for n, (name, call) in enumerate(self._pieces):
                    self.center.piece(name, self._take, call, answer, asked, n == len(self._pieces) - 1)
        if self._again:
            self._again = False
            self.ask()
        self._changed()

    def _take(self, call, answer, generation, last: bool) -> None:
        if last and self._taking == generation:
            self._taking = 0
        if self.current(generation):
            call(answer)
        if last:
            self._changed()

    def _failed(self, _kind, _sentence) -> None:
        """The sentence is in the status bar already (Center.tell); the scene of before stays."""
        self._handle, self._asked = None, None
        if self._again:
            self._again = False
            self.ask()
        self._changed()
