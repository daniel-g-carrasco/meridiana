"""The true geometry of an imported IFC model in the 3D, as context (r21-ifc-vista).

The import makes simple bodies (an outline and two heights) for the calculation; they do not look like the model.
The reader has the model's triangles (`ifc_mesh`, written once by the import's worker next to the cache): this shows
them where the bodies are, moved and turned with them (`ifc_export.frame_of`: the anchor building of the import),
not pickable, casting the sun's shadow and receiving none (R603). The bodies stay, unseen and casting nothing
(`ghost_ranges`, GHOST), and remain what is selected,
moved and computed. One `Model` for each colour of the model (`ifc_mesh` pieces); the vertices are uploaded once in
the Qt axes around the model's middle, a move only changes the `Model`'s position and turn.

Memory, on the large test IFC (23.8 M triangles, 11.8 M vertices): 12 bytes a vertex and 12 a triangle, 426 MB, held once by Qt;
docs/quick/stato/r21-ifc-vista.md has the measures."""
from __future__ import annotations

import math
import os
import threading
import time
from pathlib import Path

import numpy as np
from PySide6.QtCore import QByteArray, QObject, Qt, Signal, Slot
from PySide6.QtGui import QVector3D
from PySide6.QtQuick3D import QQuick3DGeometry

from meridiana.core.compute import resources

GHOST = 0.0                 # the import's bodies while its true geometry is shown: not seen (Daniel 07/11: drawn faint
                            # they read as ghosts over the model), still picked; the selection's outline shows one


def plain(value):
    """`value` with every NumPy number and array made Python's (lists, floats, ints, bools), the rest as it is. What
    goes to QML as a list or a map passes here: a numpy.float64 reaches QML as '' (R575 D1: the model's position came
    as ['', '', ''] and the model was drawn about the scene's origin, 26 m from its bodies)."""
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


class ContextGeometry(QQuick3DGeometry):
    """Positions and 32 bit indices only: the normals come from the screen derivatives in View3D/context.frag, so a
    vertex is shared by all its faces and nothing is doubled."""

    def set_indexed(self, positions: np.ndarray, faces: np.ndarray) -> None:
        self.set_bytes(*_bytes_of(positions, faces))

    def set_bytes(self, vertices: QByteArray, faces: QByteArray, low, high) -> None:
        """The data as `_bytes_of` gives it (R548: made ahead in a thread, Qt only takes the arrays here)."""
        self.clear()
        self.setVertexData(vertices)
        self.setIndexData(faces)
        self.setStride(12)
        self.setPrimitiveType(self.PrimitiveType.Triangles)
        a = self.Attribute
        self.addAttribute(a.Semantic.PositionSemantic, 0, a.ComponentType.F32Type)
        self.addAttribute(a.Semantic.IndexSemantic, 0, a.ComponentType.U32Type)
        self.setBounds(QVector3D(*map(float, low)), QVector3D(*map(float, high)))
        self.update()


def _bytes_of(positions, faces):
    """(vertices, faces, low, high): float32 positions and uint32 indices as Qt's arrays, and the box. No Qt object:
    it runs in any thread."""
    p = np.ascontiguousarray(positions, dtype='<f4')
    f = np.ascontiguousarray(faces, dtype='<u4')
    low, high = (p.min(0), p.max(0)) if len(p) else (np.zeros(3), np.zeros(3))
    return QByteArray(p.tobytes()), QByteArray(f.tobytes()), low, high


def prepared(mesh: dict, skip=(), check=None) -> tuple:
    """(centre, pieces, info) of a mesh (ifc_mesh.load) without the elements in `skip` (r22-ifc: the storeys left out):
    each piece (vertices, faces, colour, low, high), in the Qt axes around the model's middle. No Qt object: it runs
    in any thread (R548: in the one that reads ahead). `check(i)` before each piece (r27: the reading ahead stops
    there when the window closes)."""
    from meridiana.app.exchange import ifc_mesh
    pieces = []
    for i in range(len(mesh['pieces'])):
        if check is not None:
            check(i)
        v, f, colour = ifc_mesh.piece(mesh, i, skip)
        if not len(f):
            continue
        q = np.empty_like(v)                        # mesh.to_qt: x east, y up, z south
        q[:, 0], q[:, 1], q[:, 2] = v[:, 0], v[:, 2], -v[:, 1]
        vertices, faces, low, high = _bytes_of(q, f)
        pieces.append((vertices, faces, colour, low, high))
    info = {'triangles': int(len(mesh['faces'])), 'vertices': int(len(mesh['vertices'])), 'pieces': len(pieces),
            'bytes': int(mesh['vertices'].nbytes + mesh['faces'].nbytes)}
    return np.asarray(mesh['centre'], float), pieces, info


# R548: the model's true geometry read from the disk and made into Qt's arrays ahead, in a thread below the window,
# when the memory allows it (resources.preload): at the window's start while the QML is made, and as soon as the
# import's reading ends while the designer looks at what it found. One model kept, given once to the 3D that asks.
# Measured on the large test IFC (23.8 M triangles): the window's thread from 1.3 s to 0.1 s (docs/quick/stato/r25-memoria.md).
# r27 (docs/prestazioni/2026-11-08/confronto-r27-dell.md): the thread is stopped and waited for when the window
# closes (`shutdown`), it always says that it ended (an error of any kind included: the 3D waiting for it never
# waits for ever), it is raised to the window's priority when the 3D waits for it, and nothing is read ahead for the
# model the 3D already shows (the import of the same file again: 0.4-0.5 GB kept for the session in r25, never taken).
# What the 3D does not take is let go when it shows its model: the geometry read ahead by the import's dialog is made
# without the storeys left out (it is read before they are chosen), the 3D asks with them (`skip`), and in r25 the
# 0.4 GB made ahead for the large test IFC stayed in memory for the session, never given (measured in the window, r27).
def _prepared_bytes(made) -> int:
    """The bytes of prepared(...): the pieces' arrays for Qt (426 MB for 23,8 M triangles)."""
    return sum(piece[0].size() + piece[1].size() + 128 for piece in made[1]) + 1024


# ((path, size, mtime), skip) -> prepared(...), within the budget's models (study 56); what the 3D waits for is kept
# whatever its size until it takes it
_READY = resources.Kept(lambda: resources.cache_limit('models'), _prepared_bytes, most=1)
_LOADING: dict = {}        # ((path, size, mtime), skip) -> threading.Event set when made
_URGENT: set = set()       # the keys the 3D is waiting for: their thread back at normal priority
_SHOWN: set = set()        # the files (path, size, mtime) the 3D shows now (IfcContext), whatever their skip
_THREADS: list = []
_STOP = [threading.Event()]
_LOCK = threading.Lock()
# passo 2 (R598): the 3D never waits for the reading. It asks (request) and is told when the reading ends, on the
# window's thread: the readings' waiters, and what a reading that failed said
_WAITERS: dict = {}        # ((path, size, mtime), skip) -> [_Arrivals]
_FAILED: dict = {}         # ((path, size, mtime), skip) -> the error, for the 3D that asked


class _Arrivals(QObject):
    """An IfcContext's ear: the reading's thread emits `ended`, Qt delivers it on the window's thread (the object
    lives there), where `call(key)` runs."""
    ended = Signal(object)

    def __init__(self, parent, call):
        super().__init__(parent)
        self._call = call
        self.ended.connect(self._ended, Qt.ConnectionType.QueuedConnection)

    @Slot(object)
    def _ended(self, key):
        self._call(key)


class _Stopped(Exception):
    """The window closing: the reading ahead ends where it is."""


def _key(path, skip=()):
    try:
        st = os.stat(path)
    except (OSError, TypeError, ValueError):
        return None
    return (os.path.normcase(os.path.abspath(path)), st.st_size, st.st_mtime_ns), tuple(int(x) for x in skip or ())


def _thread_priority(normal: bool) -> None:
    from meridiana.core.compute import resources
    if not normal:
        resources._lower_thread()
    elif os.name == 'nt':
        import ctypes
        ctypes.windll.kernel32.SetThreadPriority(ctypes.windll.kernel32.GetCurrentThread(), 0)


def preload(path, skip=()) -> bool:
    """The mesh file at `path` read and prepared now in background for the 3D that will ask for it (R548); whether
    it started."""
    from meridiana.core.compute import resources
    key = _key(path, skip) if path else None
    if key is None or not resources.preload():
        return False
    if key[0][1] > resources.cache_limit('models'):
        # study 56: the arrays made are about as large as the file: a model the models' share cannot keep is not
        # read ahead (on 8 GB with 3 free, 4 M triangles were read for 1,5 s and thrown away)
        return False
    stop = _STOP[0]                 # this window's: a later shutdown sets it, the next window has a new one
    with _LOCK:
        if key in _READY or key in _LOADING or key[0] in _SHOWN:
            return False
        done = _LOADING[key] = threading.Event()

    def check(_i=None):
        if stop.is_set():
            raise _Stopped
        if key in _URGENT:
            _thread_priority(True)

    def work():
        made, failed = None, ''
        try:
            _thread_priority(False)         # in the try: a failure here too says that the reading ended
            from meridiana.app.exchange import ifc_mesh
            mesh = ifc_mesh.load(path)
            check()
            made = prepared(mesh, key[1], check)
        except _Stopped:
            made = None
        except Exception as error:          # never left half: the 3D that asks is told what went wrong
            from meridiana.app.platform import log
            log.complain('IFC geometry read ahead', error)
            made, failed = None, f'{type(error).__name__}: {error}'
        finally:
            with _LOCK:
                _LOADING.pop(key, None)
                _URGENT.discard(key)
                waiters = [] if stop.is_set() else _WAITERS.pop(key, [])
                if waiters and failed:
                    _FAILED[key] = failed
                if made is not None and not stop.is_set() and (waiters or key[0] not in _SHOWN):
                    _READY.clear()
                    _READY.put(key, made, force=bool(waiters))     # read ahead and too large: made when asked
            done.set()
            for ear in waiters:
                try:
                    ear.ended.emit(key)
                except RuntimeError:        # its window is gone (the object deleted): nobody to tell
                    continue
    thread = threading.Thread(target=work, name='meridiana-ifc-preload', daemon=True)
    with _LOCK:
        _THREADS[:] = [t for t in _THREADS if t.is_alive()] + [thread]
    thread.start()
    return True


def preload_project(project) -> bool:
    """The true geometry of the project's IFC model, when it has one, read ahead (R548)."""
    ref = reference(project)
    return bool(ref) and preload(ref['context'].get('mesh') or '', ref['context'].get('skip') or ())


def _prepared(path, skip=()):
    """prepared(...) of the mesh at `path`: the one made ahead (waited for if on its way, and given once), else made
    now."""
    from meridiana.app.exchange import ifc_mesh
    key = _key(path, skip)
    with _LOCK:
        waiting = _LOADING.get(key)
        if waiting is not None:
            _URGENT.add(key)
    if waiting is not None:
        waiting.wait()
    with _LOCK:
        made = _READY.pop(key, None)
        _READY.clear()                  # made for another skip of the storeys: the 3D shows one model, this one
    return made if made is not None else prepared(ifc_mesh.load(path), key[1] if key else ())


def request(path, skip, asked) -> tuple | None:
    """prepared(...) of the mesh at `path`: the one made ahead (given once); None while the reading ahead is on its
    way, `asked` (an _Arrivals) told when it ends, the 3D never waiting for it (passo 2, R598: _prepared waited on
    the window's thread, 126-296 ms after «Add the model» on model A, and the thread was raised to the window's
    priority); made now, as before, when nothing reads it ahead. Reading that one in a thread too was measured and
    left out: the thread holds the interpreter (docs of passo 2), and a process is a later step's."""
    key = _key(path, skip)
    if key is None:
        raise OSError(f'{path} cannot be read')
    with _LOCK:
        made = _READY.pop(key, None)
        if made is not None:
            _READY.clear()
            return made
        if key in _LOADING:
            _WAITERS.setdefault(key, []).append(asked)
            return None
    return _prepared(path, skip)


def taken(key) -> tuple:
    """(prepared(...) or None, the error) of the reading of `key` just ended, for the 3D that asked it."""
    with _LOCK:
        made = _READY.pop(key, None)
        if made is not None:
            _READY.clear()
        return made, _FAILED.pop(key, '')


def shown(path, skip=()) -> None:
    """The 3D shows the model at `path` now (None: no model): not read ahead again while it is shown."""
    key = _key(path, skip) if path else None
    with _LOCK:
        _SHOWN.clear()
        if key is not None:
            _SHOWN.add(key[0])
            for other in [k for k in _READY if k[0] == key[0]]:
                _READY.pop(other)


def shutdown(timeout: float = 3.0) -> bool:
    """The window closing: the reading ahead stopped and waited for (at most `timeout` seconds), what it made let
    go. Whether no thread is left (r27: a thread still working when the process ends can keep it from ending)."""
    with _LOCK:
        stop, _STOP[0] = _STOP[0], threading.Event()
        threads = list(_THREADS)
    stop.set()
    with _LOCK:
        _WAITERS.clear()
    end = time.monotonic() + timeout
    for thread in threads:
        thread.join(max(0.0, end - time.monotonic()))
    with _LOCK:
        _READY.clear()
        _SHOWN.clear()
        left = [t for t in _THREADS if t.is_alive()]
        _THREADS[:] = left
    return not left


def reference(project) -> dict | None:
    """The import's reference with its context (ifc_import.reference, R453), None when there is none."""
    ref = (getattr(project, 'resources', None) or {}).get('ifc_reference')
    if not isinstance(ref, dict) or not isinstance(ref.get('context'), dict):
        return None
    return ref


def members(project, ref: dict) -> set:
    """The ids of the bodies of the import the context belongs to: the anchor's group (Building.group)."""
    anchor = next((b for b in project.buildings if b.id == (ref.get('anchor') or {}).get('building')), None)
    if anchor is None:
        return set()
    if not anchor.group:
        return {anchor.id}
    return {b.id for b in project.buildings if b.group == anchor.group}


def derived(project, ref: dict) -> set:
    """The (part, id) of `mesh.project_scene`'s owners that the import made of the model whose true geometry is shown:
    its bodies and their parts (parapets), the obstacles and the placement planes it read (R575). The model draws
    them already, so their faces are not drawn again over it: a placement plane on the model's roof is the roof's own
    plane and flickered with it, an obstacle is the upright prism of an element's outline (a sloping mullion of 5 cm
    drawn as a wall 4 m high). They stay in the calculations and are still picked (the selection draws an outline).
    The obstacles and the planes the designer adds on those bodies are drawn; a project imported before the import
    listed what it made (`ref["derived"]`) takes all of those on the bodies as the model's."""
    ids = members(project, ref)
    out = {(part, i) for i in ids for part in ('building', 'building_part')}
    made = ref.get('derived')
    if isinstance(made, dict):
        out |= {('exclusion', i) for i in made.get('exclusions') or []}
        out |= {('support', i) for i in made.get('supports') or []}
    else:
        out |= {('exclusion', e.id) for e in project.exclusions if e.building in ids}
        out |= {('support', sf.id) for sf in project.subfields if sf.building in ids and sf.support is not None}
    return out


def ghost_ranges(owners: list, hidden: set) -> list:
    """(first triangle, triangles) of the runs of `mesh.project_scene`'s owners whose (part, id) is in `hidden`."""
    out, at = [], 0
    for part, oid, n in owners:
        if (part, oid) in hidden and n:
            out.append((at, n))
        at += n
    return out


class IfcContext:
    """The pieces of the context, made once for each mesh file, placed for each project state."""

    def __init__(self, parent: QObject, came=None, spread=None):
        """`came(take)`: the 3D's, given by a window (passo 2, R598): the geometry is asked and never waited for; when
        its reading ends `came` is called on the window's thread with `take`, and each `take()` makes one piece of
        the model: 'more' while some are left, 'done' with the last, None when the model is no longer the one asked
        (or the reading failed). `spread()`: whether to ask without waiting. Without them the geometry is made at
        once, as before."""
        self.parent = parent
        self._file = None
        self._pieces: list = []         # (geometry, colour, bounds low, high), Qt axes around the model's middle
        self._centre = np.zeros(3)
        self.error = ''
        self.info: dict = {}
        self.came = came
        self.spread = spread or (lambda: came is not None)
        self._ear = None
        self._todo: list = []           # the pieces read, still to give Qt (one a turn)
        self._loads = 0                 # a new model asked: the pieces of the one before are no longer made

    def waiting(self) -> bool:
        """The geometry asked is on its way (its reading in its thread): the 3D shows the bodies meanwhile."""
        return self._file is not None and (not self._pieces or bool(self._todo)) and not self.error \
            and self.came is not None

    def _load(self, path: str, skip=()) -> None:
        skip = tuple(int(x) for x in skip or ())
        if (path, skip) == self._file:
            return
        for g, *_rest in self._pieces:
            g.deleteLater()
        self._pieces, self._file, self.error, self._todo = [], (path, skip), '', []
        self._loads += 1
        try:
            if self.came is None or not self.spread():
                made = _prepared(path, skip)
            else:
                shown(None)                 # nothing of the model shown now: its reading is kept for this 3D
                if self._ear is None:
                    self._ear = _Arrivals(self.parent, self._arrived)
                made = request(path, skip, self._ear)
                if made is None:
                    return
        except (OSError, ValueError, KeyError) as error:
            self.error = f'{type(error).__name__}: {error}'
            return
        self._made(path, skip, made)

    def _arrived(self, key) -> None:
        """The reading of `key` ended (on the window's thread): the 3D told, the pieces made when it takes them."""
        if self._file is None or self._pieces or _key(*self._file) != key:
            return                          # another model asked meanwhile (its own reading tells), or made already
        made, error = taken(key)
        if made is None:
            self.error = error or 'the geometry could not be read'
            return
        self._centre, self._todo, self.info = made[0], list(made[1]), made[2]
        shown(*self._file)                  # r27: not read ahead again while it is shown
        loads = self._loads

        def take():
            if loads != self._loads:
                return None                 # another model asked meanwhile: its pieces are its own
            if self._todo:
                self._piece(*self._todo.pop(0))
            return 'more' if self._todo else 'done'
        if self.came is not None:
            self.came(take)

    def _made(self, path, skip, made) -> None:
        self._centre, pieces, self.info = made
        shown(path, skip)                   # r27: not read ahead again while it is shown
        for piece in pieces:
            self._piece(*piece)

    def _piece(self, vertices, faces, colour, low, high) -> None:
        g = ContextGeometry()
        g.setParent(self.parent)
        g.set_bytes(vertices, faces, low, high)
        self._pieces.append((g, colour, low, high))

    def entries(self, project) -> list:
        """What View3D/Viewport.qml draws: for each piece its geometry, colour, position and turn (degrees about the
        vertical), and the corners of its box in the scene (for the scene's bounds). [] without a context or when the
        import's frame is lost (its anchor body removed or reshaped)."""
        ref = reference(project)
        if ref is None:
            return []
        from meridiana.app.exchange import ifc_export
        frame, why = ifc_export.frame_of(project)
        path = ref['context'].get('mesh') or ''
        if frame is None or not Path(path).is_file():
            self.error = why or ('' if Path(path).is_file() else 'missing')
            return []
        self._load(path, ref['context'].get('skip') or ())
        if not self._pieces or self._todo:
            return []                       # nothing yet, or not all of it: the bodies as they are meanwhile
        # world = R(phi) plan + move, so plan = R(-phi) (world - move); world = vertex + centre
        phi = float(frame['turn'])
        mx, my = frame['move']
        a, b = math.cos(phi), math.sin(phi)
        wx, wy = self._centre[0] - mx, self._centre[1] - my
        tx, ty = a * wx + b * wy, -b * wx + a * wy
        tz = self._centre[2] - ifc_export.context_ground(ref)
        position = plain([tx, tz, -ty])
        turn = -math.degrees(phi)
        out = []
        c, s = math.cos(-phi), math.sin(-phi)
        for k, (g, colour, low, high) in enumerate(self._pieces):
            corners = np.array([[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1])
                                for z in (low[2], high[2])])
            # Qt's rotation about y by `turn`: x' = x cos + z sin, z' = -x sin + z cos
            rx = corners[:, 0] * c + corners[:, 2] * s + position[0]
            rz = -corners[:, 0] * s + corners[:, 2] * c + position[2]
            box = np.column_stack((rx, corners[:, 1] + position[1], rz))
            out.append(plain({'name': f'ifc-context:{k}', 'geometry': g, 'colour': list(colour),
                              'position': position, 'turn': turn, 'bounds': box}))
        return out
