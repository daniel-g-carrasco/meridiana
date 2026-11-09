"""The true geometry of an imported IFC model in the 3D, as context (r21-ifc-vista).

The import makes simple bodies (an outline and two heights) for the calculation; they do not look like the model.
The reader has the model's triangles (`ifc_mesh`, written once by the import's worker next to the cache): this shows
them where the bodies are, moved and turned with them (`ifc_export.frame_of`: the anchor building of the import),
not pickable and casting no shadow. The bodies stay, unseen (`ghost_ranges`, GHOST), and remain what is selected,
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
from PySide6.QtCore import QByteArray, QObject
from PySide6.QtGui import QVector3D
from PySide6.QtQuick3D import QQuick3DGeometry

GHOST = 0.0                 # the import's bodies while its true geometry is shown: not seen (Daniel 07/11: drawn faint
                            # they read as ghosts over the model), still picked; the selection's outline shows one


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
    from meridiana import ifc_mesh
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
_READY: dict = {}          # ((path, size, mtime), skip) -> prepared(...)
_LOADING: dict = {}        # ((path, size, mtime), skip) -> threading.Event set when made
_URGENT: set = set()       # the keys the 3D is waiting for: their thread back at normal priority
_SHOWN: set = set()        # the files (path, size, mtime) the 3D shows now (IfcContext), whatever their skip
_THREADS: list = []
_STOP = [threading.Event()]
_LOCK = threading.Lock()


class _Stopped(Exception):
    """The window closing: the reading ahead ends where it is."""


def _key(path, skip=()):
    try:
        st = os.stat(path)
    except (OSError, TypeError, ValueError):
        return None
    return (os.path.normcase(os.path.abspath(path)), st.st_size, st.st_mtime_ns), tuple(int(x) for x in skip or ())


def _thread_priority(normal: bool) -> None:
    from meridiana import resources
    if not normal:
        resources._lower_thread()
    elif os.name == 'nt':
        import ctypes
        ctypes.windll.kernel32.SetThreadPriority(ctypes.windll.kernel32.GetCurrentThread(), 0)


def preload(path, skip=()) -> bool:
    """The mesh file at `path` read and prepared now in background for the 3D that will ask for it (R548); whether
    it started."""
    from meridiana import resources
    key = _key(path, skip) if path else None
    if key is None or not resources.preload():
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
        _thread_priority(False)
        made = None
        try:
            from meridiana import ifc_mesh
            mesh = ifc_mesh.load(path)
            check()
            made = prepared(mesh, key[1], check)
        except _Stopped:
            made = None
        except Exception as error:          # never left half: the 3D makes its own
            from meridiana import log
            log.complain('IFC geometry read ahead', error)
            made = None
        finally:
            with _LOCK:
                _LOADING.pop(key, None)
                _URGENT.discard(key)
                if made is not None and not stop.is_set() and key[0] not in _SHOWN:
                    _READY.clear()
                    _READY[key] = made
            done.set()
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
    from meridiana import ifc_mesh
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


def ghost_ranges(owners: list, ids: set) -> list:
    """(first triangle, triangles) of the runs of `mesh.project_scene`'s owners that are bodies in `ids`."""
    out, at = [], 0
    for part, oid, n in owners:
        if part == 'building' and oid in ids and n:
            out.append((at, n))
        at += n
    return out


class IfcContext:
    """The pieces of the context, made once for each mesh file, placed for each project state."""

    def __init__(self, parent: QObject):
        self.parent = parent
        self._file = None
        self._pieces: list = []         # (geometry, colour, bounds low, high), Qt axes around the model's middle
        self._centre = np.zeros(3)
        self.error = ''
        self.info: dict = {}

    def _load(self, path: str, skip=()) -> None:
        skip = tuple(int(x) for x in skip or ())
        if (path, skip) == self._file:
            return
        for g, *_rest in self._pieces:
            g.deleteLater()
        self._pieces, self._file, self.error = [], (path, skip), ''
        try:
            self._centre, pieces, self.info = _prepared(path, skip)
            shown(path, skip)               # r27: not read ahead again while it is shown
        except (OSError, ValueError, KeyError) as error:
            self.error = f'{type(error).__name__}: {error}'
            return
        for vertices, faces, colour, low, high in pieces:
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
        from meridiana import ifc_export
        frame, why = ifc_export.frame_of(project)
        path = ref['context'].get('mesh') or ''
        if frame is None or not Path(path).is_file():
            self.error = why or ('' if Path(path).is_file() else 'missing')
            return []
        self._load(path, ref['context'].get('skip') or ())
        if not self._pieces:
            return []
        # world = R(phi) plan + move, so plan = R(-phi) (world - move); world = vertex + centre
        phi = float(frame['turn'])
        mx, my = frame['move']
        a, b = math.cos(phi), math.sin(phi)
        wx, wy = self._centre[0] - mx, self._centre[1] - my
        tx, ty = a * wx + b * wy, -b * wx + a * wy
        tz = self._centre[2] - float(ref['context'].get('ground') or 0.0)
        position = [tx, tz, -ty]
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
            out.append({'name': f'ifc-context:{k}', 'geometry': g, 'colour': list(colour), 'position': position,
                        'turn': turn, 'bounds': box.tolist()})
        return out
