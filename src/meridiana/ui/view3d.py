"""The 3D view: Qt Quick 3D drawn into a picture (ui/quick_image.py: not a QQuickWidget, which made the whole window
slow on a 4K screen, R120). Two Python types feed it: one geometry with every building
(walls and pitches, colours per vertex) and one instance table with every module; mesh.py makes both.
A change of parameters uploads new data into the same objects: the scene is not rebuilt and the camera
stays where the designer left it. "Fit" moves it only when asked, or the first time there is something
to see.

The camera is camera.py's, moved by navigation.py from the mouse events QML passes on (the style chosen in the
preferences), with the point under the cursor as the pivot; QML binds to it. The pivot is shown as a cross-hair
of three rings (task 16g, study 16 G): the backend says where it stands and when it shows.

The sun is a directional light placed from sun.py (the same position the row pitch is computed with),
casting shadows; the orthophoto of the site lies on the ground when there is one.

With Move active and something to move selected, the gizmo of Move and Rotate stands on its middle (task 16b,
study 16 B): arrows East and North, the square of the plane, the ring about the vertical, in a view of their own
laid over the scene, as the pivot's cross-hair. Which handle is under the pointer and what a drag gives are
gizmo.py's sums on the pixels; while the drag goes on a copy of the outline moves (the preview), and at the
release the window applies it as one step. A value can be typed in the field next to the gizmo (GizmoField).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import Property, QByteArray, QEvent, QObject, Qt, QTimer, QUrl, QVariantAnimation, Signal, Slot
from PySide6.QtGui import QGuiApplication, QQuaternion, QVector3D
from PySide6.QtQml import QmlElement, QQmlComponent
from PySide6.QtQuick3D import QQuick3DGeometry, QQuick3DInstancing
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit

from .. import camera, gizmo, mesh, move, navigation, view_colours
from ..i18n import _, number
from .cards import round_corners
from .quick_image import QuickImage


QML_IMPORT_NAME = "Meridiana"
QML_IMPORT_MAJOR_VERSION = 1
QML_FILE = Path(__file__).resolve().parent / "qml" / "Scene.qml"

# the pivot's cross-hair: its rings are one unit in radius (mesh.rings) and the scene scales them to PIVOT_PX
# on the screen, wherever the pivot is; the tube, the halo's bands and the dot in units of that radius
PIVOT_PX = 16.0                     # Daniel, 24/10/2026: the cross-hair of the orbit was too small (it was 8)
PIVOT_TUBE = 0.18
PIVOT_BAND = 0.80
PIVOT_DOT = 0.26
SPHERE_RADIUS = 50.0                # Qt Quick 3D's built-in "#Sphere" is 100 units across
KEY_POLL_MS = 100                   # how often the keyboard is asked while the cross-hair shows for a key held
FLASH_MS = 1000                     # how long the cross-hair stays on the point a middle click recentred the view on


@QmlElement
class BuildingsGeometry(QQuick3DGeometry):
    """Every building in one mesh: position, normal and colour per vertex."""

    def set_mesh(self, pos: np.ndarray, nor: np.ndarray, col: np.ndarray) -> None:
        self.clear()
        n = len(pos)
        if n == 0:
            data = np.zeros((3, 10), dtype=np.float32)          # an empty triangle keeps Qt happy
            lo = hi = QVector3D(0, 0, 0)
        else:
            rgba = np.hstack([col, np.ones((n, 1), dtype=np.float32)])
            data = np.hstack([pos, nor, rgba]).astype(np.float32)
            lo = QVector3D(*map(float, pos.min(axis=0)))
            hi = QVector3D(*map(float, pos.max(axis=0)))
        self.setVertexData(QByteArray(data.tobytes()))
        self.setStride(40)
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
        A = QQuick3DGeometry.Attribute
        self.addAttribute(A.Semantic.PositionSemantic, 0, A.ComponentType.F32Type)
        self.addAttribute(A.Semantic.NormalSemantic, 12, A.ComponentType.F32Type)
        self.addAttribute(A.Semantic.ColorSemantic, 24, A.ComponentType.F32Type)
        self.setBounds(lo, hi)
        self.update()


@QmlElement
class OutlineGeometry(BuildingsGeometry):
    """The outline of what is selected and of what is under the pointer: ribbons (mesh.ribbons), unlit."""


@QmlElement
class RingGeometry(BuildingsGeometry):
    """The pivot's cross-hair: three rings of radius one (mesh.rings) and the flat bands of their halo
    (mesh.ring_bands), scaled on the screen by the model. Theme B's rotation handles are the same circle."""


@QmlElement
class GizmoGeometry(BuildingsGeometry):
    """A handle of Move and Rotate's gizmo or its halo (mesh.arrow, mesh.annulus, mesh.square): one unit long, white,
    coloured by its material."""


@QmlElement
class ModulesInstancing(QQuick3DInstancing):
    """Every module of every filled sub-field, as Qt's instance table (mesh.module_table)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = QByteArray()
        self._count = 0

    def set_table(self, table: np.ndarray) -> None:
        self._data = QByteArray(table.astype(np.float32).tobytes())
        self._count = int(len(table))
        self.markDirty()

    def getInstanceBuffer(self):
        # PySide6 6.12: no argument, (data, count) back (tried on 21/10/2026)
        return self._data, self._count


BUTTONS = {1: "left", 2: "right", 4: "middle"}            # Qt.MouseButton values as QML gives them


def modifiers(flags: int) -> set:
    """Qt.KeyboardModifier flags, as QML gives them, as the names navigation.py uses."""
    return {name for bit, name in ((0x04000000, "ctrl"), (0x02000000, "shift"), (0x08000000, "alt")) if flags & bit}


class Backend(QObject):
    """What QML reads (sun, ground, sky, the camera) and the way back (the mouse, the picks). The camera is
    camera.Camera, moved by the actions of navigation.Navigator; QML binds its camera to cameraPosition and
    cameraRotation and never moves it by itself."""
    changed = Signal()
    cameraChanged = Signal()
    markerChanged = Signal()                               # the pivot's cross-hair: where, how big, shown or not
    picked = Signal(str, int, float, float, float, bool)   # object name, instance index, the point hit (Qt axes)
    hovered = Signal(str, int, float, float, float, bool)  # the same, for what is under the pointer
    menuRequested = Signal(float, float)                   # a right click held still, where
    gizmoChanged = Signal()                                # the gizmo of Move: where, how big, which handle is hot
    gizmoBegan = Signal()                                  # a handle pressed: the preview's outline is made now
    gizmoMoving = Signal(str, float, float, float)         # the handle dragged and its value: East, North, degrees
    gizmoDone = Signal(float, float, float, bool)          # released: East, North (m), degrees, Ctrl held (a copy)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sun_elev = 45.0
        self._sun_bearing = 180.0
        self._ground = ""
        self._ground_half = 100.0
        self._ground_x = self._ground_z = 0.0      # the ground's centre, under the scene (R66)
        self._shadow_far = 400.0
        # the view's own colours, the same in both themes (view_colours): the day sky, the ground of before
        self._colours = {k: view_colours.D3[k] for k in ("sky_top", "sky_bottom", "ground", "pivot")}
        self.camera = camera.Camera()
        self.navigator = navigation.Navigator()
        self.orbit_mode = "turntable"
        self.pivot_mode = "cursor"                         # "cursor", "selection", "centre"
        self.pivot_hint = True                             # the preference: show the pivot with the orbit's key held
        self.selection_centre = None                       # Qt axes, for the pivot on the selection
        self.reduced_motion = False
        self.size = (800.0, 600.0)
        self.scene = None                                  # (centre, radius) of what is drawn, Qt axes
        self.user_moved = False                            # moved by hand: a resize keeps the camera
        self._pivot = np.zeros(3)
        self._orbiting = False
        self._hint = None                                  # where the pivot would be, with the orbit's key held
        self._keys = QTimer(self)                          # asks the keyboard while the cross-hair shows for a key
        self._keys.setInterval(KEY_POLL_MS)
        self._keys.timeout.connect(self._poll_keys)
        self.key_modifiers = QGuiApplication.queryKeyboardModifiers     # a test puts its own here
        self._flash_point = None                           # the point of the last recentre, shown for FLASH_MS
        self._flash = QTimer(self)
        self._flash.setSingleShot(True)
        self._flash.setInterval(FLASH_MS)
        self._flash.timeout.connect(self._flash_over)
        self._press = None                                 # (hit point or None, object name, instance) at the press
        self._depth = None
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(camera.ANIMATION_MS)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.valueChanged.connect(self._animate)
        self._from = self._to = None
        self.home: camera.Camera | None = None             # «Set this view as Home» (the cube's menu)
        self.cameraChanged.connect(self.markerChanged)     # the cross-hair's size follows the camera
        # the gizmo of Move and Rotate (task 16b): where it stands (Qt axes), the snaps of the plan (F3), the handle
        # under the pointer or dragged, the drag going on
        self.gizmo_centre: np.ndarray | None = None
        self.gizmo_snaps = True
        self.gizmo_hot = ""
        self.gizmo_last = "x"                              # the last handle taken: the field typed opens on it
        self._gizmo: gizmo.Drag | None = None
        self.cameraChanged.connect(self.gizmoChanged)      # its size follows the camera

    @Property(str, notify=changed)
    def skyTop(self):
        return self._colours["sky_top"]

    @Property(str, notify=changed)
    def skyBottom(self):
        return self._colours["sky_bottom"]

    @Property(str, notify=changed)
    def groundColor(self):
        return self._colours["ground"]

    def set_sun(self, elevation: float, bearing: float) -> None:
        self._sun_elev, self._sun_bearing = elevation, bearing
        self.changed.emit()

    def set_reach(self, radius: float) -> None:
        """How far the shadows are drawn: the whole scene seen from where the camera frames it."""
        self._shadow_far = max(100.0, 6.0 * radius)
        self.changed.emit()

    @Property(float, notify=changed)
    def shadowFar(self):
        return self._shadow_far

    def set_ground(self, url: str, half: float) -> None:
        self._ground, self._ground_half = url, half
        self.changed.emit()

    GROUND_MARGIN = 60.0                # metres of ground beyond what the scene holds, on every side
    GROUND_LEAST = 100.0                # half the side of the smallest ground

    def set_ground_area(self, x: float, z: float, half: float) -> None:
        """The ground under the scene (R66): centred at (x, z) in Qt's axes, `half` the half side of what it holds;
        the margin is added here."""
        half = max(self.GROUND_LEAST, half + self.GROUND_MARGIN)
        if (round(x, 1), round(z, 1), round(half, 1)) != (round(self._ground_x, 1), round(self._ground_z, 1),
                                                         round(self._ground_half, 1)):
            self._ground_x, self._ground_z, self._ground_half = x, z, half
            self.changed.emit()

    @Property(float, notify=changed)
    def groundX(self):
        return self._ground_x

    @Property(float, notify=changed)
    def groundZ(self):
        return self._ground_z

    @Property(float, notify=changed)
    def sunPower(self):
        """The sun's brightness: none once it has set."""
        return 1.25 if self._sun_elev > 0 else 0.0

    @Property(float, notify=changed)
    def sunPitch(self):
        # a directional light shines along its -z: rotated by (-elevation, 180 - bearing) it comes from the sun
        return -max(self._sun_elev, 2.0)

    @Property(float, notify=changed)
    def sunYaw(self):
        return 180.0 - self._sun_bearing

    @Property(str, notify=changed)
    def ground(self):
        return self._ground

    @Property(float, notify=changed)
    def groundHalf(self):
        return self._ground_half

    # the camera, as QML binds it

    @Property(QVector3D, notify=cameraChanged)
    def cameraPosition(self):
        return QVector3D(*map(float, self.camera.position))

    @Property(QQuaternion, notify=cameraChanged)
    def cameraRotation(self):
        w, x, y, z = map(float, self.camera.rotation)
        return QQuaternion(w, x, y, z)

    @Property(bool, notify=cameraChanged)
    def orbiting(self):
        return self._orbiting

    # the pivot's cross-hair (task 16g): where it stands, whether it shows, how big a unit ring is

    def marker(self) -> np.ndarray | None:
        """Where the cross-hair stands, None while it is not shown: on the pivot of the orbit going on; else where
        the pivot of the next one would be while the orbit's key is held; else, for a second, on the point a middle
        click recentred the view on; else, when the pivot is the middle of the view, on that middle, which is the
        pivot always. With the pivot under the cursor it does not stay at rest: it would say where the next orbit
        turns, and it turns where the pointer is."""
        if self._orbiting:
            return self._pivot
        if self._hint is not None:
            return self._hint
        if self._flash_point is not None:
            return self._flash_point
        if self.pivot_mode == "centre":
            return self.camera.target
        return None

    @Property(bool, notify=markerChanged)
    def pivotVisible(self):
        return self.marker() is not None

    @Property(QVector3D, notify=markerChanged)
    def pivot(self):
        p = self.marker()
        return QVector3D(*map(float, p)) if p is not None else QVector3D(0.0, 0.0, 0.0)

    @Property(float, notify=markerChanged)
    def pivotScale(self):
        """The radius of the cross-hair's rings, in metres: PIVOT_PX pixels wherever the pivot is."""
        p = self.marker()
        if p is None:
            return 0.001
        return max(0.001, PIVOT_PX * self.camera.pixel_size(p, self.size[1]))

    @Property(float, constant=True)
    def pivotDotScale(self):
        """The scale of the built-in sphere that is the cross-hair's dot, in the units of the rings."""
        return PIVOT_DOT / SPHERE_RADIUS

    @Property(str, notify=changed)
    def pivotColor(self):
        return self._colours["pivot"]

    @Property(float, constant=True)
    def pivotHaloOpacity(self):
        return view_colours.PIVOT_HALO_OPACITY

    # the gizmo of Move and Rotate (task 16b)

    def set_gizmo(self, centre) -> None:
        """Where the gizmo stands (Qt axes), or None: not shown (Move not active, nothing to move). Somewhere else, a
        drag going on is dropped; in the same place (the scene drawn again for a layout come back) it goes on."""
        new = None if centre is None else np.asarray(centre, dtype=float)
        old = self.gizmo_centre
        if new is None or old is None or not np.allclose(new, old, rtol=0.0, atol=1e-9):
            self._gizmo = None
            self.gizmo_hot = ""
        self.gizmo_centre = new
        self.gizmoChanged.emit()

    @property
    def gizmo_on(self) -> bool:
        return self.gizmo_centre is not None

    def gizmo_size(self) -> float:
        """The metres an arrow is long where the gizmo stands: gizmo.PIXELS on the screen."""
        return gizmo.length(self.camera, self.gizmo_centre, self.size[1]) if self.gizmo_on else 1.0

    def gizmo_dragging(self) -> bool:
        return self._gizmo is not None

    def cancel_gizmo(self) -> bool:
        """Esc during a drag: the gizmo back where it was, nothing done. Whether there was one."""
        if self._gizmo is None:
            return False
        self._gizmo = None
        self.gizmo_hot = ""
        self.gizmoChanged.emit()
        return True

    @Property(bool, notify=gizmoChanged)
    def gizmoVisible(self):
        return self.gizmo_on

    @Property(QVector3D, notify=gizmoChanged)
    def gizmoPosition(self):
        if not self.gizmo_on:
            return QVector3D(0.0, 0.0, 0.0)
        p = self.gizmo_centre + (self._gizmo.offset() if self._gizmo is not None else 0.0)
        return QVector3D(*map(float, p))

    @Property(float, notify=gizmoChanged)
    def gizmoScale(self):
        return max(0.001, self.gizmo_size())

    @Property(str, notify=gizmoChanged)
    def gizmoHot(self):
        return self.gizmo_hot

    @Property(bool, notify=gizmoChanged)
    def previewVisible(self):
        return self._gizmo is not None and any(abs(v) > 1e-12 for v in self._gizmo.value)

    @Property(QVector3D, notify=gizmoChanged)
    def previewPosition(self):
        if self._gizmo is None:
            return QVector3D(0.0, 0.0, 0.0)
        return QVector3D(*map(float, self._gizmo.centre + self._gizmo.offset()))

    @Property(QQuaternion, notify=gizmoChanged)
    def previewRotation(self):
        w, x, y, z = gizmo.rotation(self._gizmo.value[2] if self._gizmo is not None else 0.0)
        return QQuaternion(w, x, y, z)

    @Property(QVector3D, notify=gizmoChanged)
    def previewBack(self):
        c = self._gizmo.centre if self._gizmo is not None else np.zeros(3)
        return QVector3D(*map(float, -c))

    @Property("QVariantMap", constant=True)
    def gizmoColors(self):
        d3 = view_colours.D3
        return {"x": d3["gizmo_x"], "y": d3["gizmo_y"], "z": d3["gizmo_z"], "hot": d3["gizmo_hot"],
                "halo": d3["gizmo_halo"]}

    @Property(float, constant=True)
    def gizmoHaloOpacity(self):
        return view_colours.GIZMO_HALO_OPACITY

    def _gizmo_press(self, button: int, mods: int, x: float, y: float) -> bool:
        """A left press on a handle begins its drag; anywhere else the press is the navigation's (a click on the body
        selects, as before)."""
        if BUTTONS.get(button) != "left" or not self.gizmo_on or self.navigator.held:
            return False
        w, h = self.size
        handle = gizmo.pick(self.camera, x, y, w, h, self.gizmo_centre, self.gizmo_size())
        drag = gizmo.Drag.begin(handle, self.camera, x, y, w, h, self.gizmo_centre) if handle else None
        if drag is None:
            return False
        self._gizmo, self.gizmo_hot, self.gizmo_last = drag, handle, handle
        self.gizmoBegan.emit()
        self.gizmoChanged.emit()
        return True

    def _gizmo_move(self, mods: int, x: float, y: float) -> bool:
        """The pointer moved: the drag follows it; with no drag, the handle under it is lit."""
        w, h = self.size
        if self._gizmo is not None:
            value = self._gizmo.update(self.camera, x, y, w, h, modifiers(mods), self.gizmo_snaps)
            self.gizmoMoving.emit(self._gizmo.handle, *value)
            self.gizmoChanged.emit()
            return True
        if self.gizmo_on and not self.navigator.held:
            hot = gizmo.pick(self.camera, x, y, w, h, self.gizmo_centre, self.gizmo_size())
            if hot != self.gizmo_hot:
                self.gizmo_hot = hot
                self.gizmoChanged.emit()
        return False

    def _gizmo_release(self, button: int, mods: int, x: float, y: float) -> bool:
        """The release of a drag: the window applies it (gizmoDone), Ctrl held makes a copy."""
        if self._gizmo is None or BUTTONS.get(button) != "left":
            return False
        w, h = self.size
        east, north, degrees = self._gizmo.update(self.camera, x, y, w, h, modifiers(mods), self.gizmo_snaps)
        self._gizmo = None
        self.gizmo_hot = ""
        self.gizmoChanged.emit()
        if abs(east) > 1e-12 or abs(north) > 1e-12 or abs(degrees) > 1e-12:
            self.gizmoDone.emit(east, north, degrees, "ctrl" in modifiers(mods))
        return True

    def go(self, target: camera.Camera, animate: bool = True) -> None:
        """To another camera, in ANIMATION_MS with an ease-out, at once when the system asks for less motion."""
        self._animation.stop()
        if not animate or self.reduced_motion:
            self.camera = target
            self.cameraChanged.emit()
            return
        self._from, self._to = self.camera.copy(), target
        self._animation.start()

    def _animate(self, t) -> None:
        if self._from is None:
            return
        self.camera = camera.between(self._from, self._to, float(t))
        self.cameraChanged.emit()

    @Property(bool, notify=cameraChanged)
    def ortho(self):
        return self.camera.ortho

    @Property(float, notify=cameraChanged)
    def orthoMagnification(self):
        """Pixels per metre of the parallel camera: what the perspective one shows at the depth of the target."""
        return self.size[1] / (2 * self.camera.half_height())

    def set_ortho(self, on: bool) -> None:
        self.camera.ortho = on
        self.cameraChanged.emit()

    def orient(self, bearing: float, elevation: float, fit: bool = False) -> None:
        """Look from `bearing`, `elevation` at the same target and distance (the cube); with `fit`, the scene
        framed too (a double click)."""
        target = self.camera.copy()
        d = float(np.linalg.norm(self.camera.target - self.camera.position))
        target.rotation = camera.look(bearing, elevation)
        target.position = target.target - target.forward() * d
        if fit and self.scene is not None:
            w, h = self.size
            target.fit(*self.scene, w / h)
        self.user_moved = True
        self.go(target)

    def set_home(self) -> None:
        self.home = self.camera.copy()

    def go_home(self) -> None:
        if self.home is not None:
            self.user_moved = True
            self.go(self.home.copy())
        elif self.scene is not None:
            self.user_moved = False
            self.frame(*self.scene, animate=True, view="home")

    def frame_part(self, centre, radius: float) -> None:
        """A part of the scene framed from where the camera looks now (the eye of a check, R127), gliding there; the
        scene's own frame stays for Home, and a resize keeps this view."""
        target = self.camera.copy()
        w, h = self.size
        target.fit(np.asarray(centre, dtype=float), float(radius), w / h)
        self.user_moved = True
        self.go(target, True)

    def frame(self, centre, radius: float, animate: bool = False, view: str = "") -> None:
        """The scene (Qt axes) framed, from where the camera looks now or from a standard view."""
        self.scene = (np.asarray(centre, dtype=float), float(radius))
        target = self.camera.copy()
        w, h = self.size
        if view:
            target.view(view, centre, radius, w / h)
        else:
            target.fit(centre, radius, w / h)
        self.go(target, animate)

    @Slot(float, float)
    def resized(self, w: float, h: float) -> None:
        if w < 1 or h < 1:
            return
        self.size = (w, h)
        self.markerChanged.emit()                          # a pixel is not the same number of metres
        if self.scene is not None and not self.user_moved:
            self.frame(*self.scene)                        # still framed: a resize frames it again

    # the mouse, from QML: what the press hit comes with it

    def _hit(self, hit: bool, hx: float, hy: float, hz: float):
        return np.array([hx, hy, hz]) if hit else None

    @Slot(int, int, float, float, bool, float, float, float, str, int)
    def press(self, button, mods, x, y, hit, hx, hy, hz, name, index) -> None:
        if self._gizmo_press(button, mods, x, y):
            return
        self._press = (self._hit(hit, hx, hy, hz), name, index)
        self._do(self.navigator.press(BUTTONS.get(button, ""), modifiers(mods), x, y))

    @Slot(int, float, float)
    def move(self, mods, x, y) -> None:
        if self._gizmo_move(mods, x, y):
            return
        self._do(self.navigator.move(x, y, modifiers(mods)))

    @Slot(int, int, float, float)
    def release(self, button, mods, x, y) -> None:
        if self._gizmo_release(button, mods, x, y):
            return
        self._do(self.navigator.release(BUTTONS.get(button, ""), modifiers(mods), x, y))

    @Slot(int, int, float, float)
    def doubleClick(self, button, mods, x, y) -> None:
        self._do(self.navigator.double(BUTTONS.get(button, ""), modifiers(mods), x, y))

    @Slot(bool, float, float, float, str, int)
    def hover(self, hit, hx, hy, hz, name, index) -> None:
        """What is under the pointer, while no button is held (QML asks a few times a second, not at each move)."""
        if not self.navigator.held:
            self.hovered.emit(name, index, hx, hy, hz, hit)

    # the pivot shown on passing over (task 16g, study 16 G2): with the key of the orbit held and the pointer moving,
    # the cross-hair goes to where an orbit begun there would turn, and stops on the pivot when the button goes down

    def set_pivot(self, mode: str, hint: bool) -> None:
        """The centre of the orbit ("cursor", "selection", "centre") and the preference to show the pivot on passing
        over: what was shown for the old ones goes."""
        self.pivot_mode, self.pivot_hint = mode, bool(hint)
        self._set_hint(None)
        self._flash.stop()
        self._flash_point = None
        self.markerChanged.emit()

    def _flash_start(self, point) -> None:
        """«Fix the pivot here»: a short middle click recentres the view on the point, and the cross-hair stays on
        it for FLASH_MS, with no fading: nothing moves, so «less motion» has nothing to take away."""
        self._flash_point = np.array(point, dtype=float)
        self._flash.start()
        self.markerChanged.emit()

    def _flash_over(self) -> None:
        self._flash_point = None
        self.markerChanged.emit()

    def _previewing(self, flags: int) -> bool:
        return self.pivot_hint and not self._orbiting and self.navigator.previews_orbit(modifiers(flags))

    def _needs_hit(self) -> bool:
        """Only the pivot under the cursor depends on what the pointer is over: with the selection's centre (when
        there is one) or the middle of the view the pointer does not choose it."""
        return self.pivot_mode == "cursor" or (self.pivot_mode == "selection" and self.selection_centre is None)

    @Slot(int, result=bool)
    def pivotPick(self, mods) -> bool:
        """Whether QML should pick under the pointer for pivotHover: with the key held, and only then."""
        return self._previewing(mods) and self._needs_hit()

    @Slot(int, float, float, bool, float, float, float)
    def pivotHover(self, mods, x, y, hit, hx, hy, hz) -> None:
        """The pointer moved with no button held, `mods` held (and the pick under it, when pivotPick asked for one).
        Without the orbit's key, or with the preference off, the cross-hair goes away."""
        if self._previewing(mods):
            self._set_hint(self._pivot_at(x, y, self._hit(hit, hx, hy, hz)))
        else:
            self._set_hint(None)

    def _set_hint(self, point) -> None:
        old = self._hint
        new = None if point is None else np.array(point, dtype=float)
        if old is None and new is None:
            return
        if old is not None and new is not None and np.allclose(old, new, rtol=0.0, atol=1e-9):
            return
        self._hint = new
        if new is None:
            self._keys.stop()
        elif not self._keys.isActive():
            self._keys.start()
        self.markerChanged.emit()

    def _poll_keys(self) -> None:
        """The key was let go with the pointer still: no event says so, and the cross-hair would stay until the next
        move. While it shows for a key the keyboard is asked a few times a second. A button held keeps it, the key
        still down: the press is not yet an orbit."""
        keys = navigation.orbit_keys(self.navigator.style)
        if not self.pivot_hint or frozenset(modifiers(int(self.key_modifiers().value))) not in keys:
            self._set_hint(None)

    @Slot(float, int, float, float, bool, float, float, float)
    def wheel(self, steps, mods, x, y, hit, hx, hy, hz) -> None:
        self._press = (self._hit(hit, hx, hy, hz), "", -1)
        self._do(self.navigator.wheel(steps, modifiers(mods), x, y))

    def touch_pan(self, dx: float, dy: float, x: float, y: float) -> None:
        self._animation.stop()
        self.user_moved = True
        w, h = self.size
        depth = self.camera.zoom_point(x, y, w, h)
        self.camera.pan(dx, dy, w, h, depth)
        self.cameraChanged.emit()

    def touch_zoom(self, steps: float, x: float, y: float) -> None:
        self._animation.stop()
        self.user_moved = True
        w, h = self.size
        self.camera.zoom(steps, self.camera.zoom_point(x, y, w, h))
        self.cameraChanged.emit()

    def touch_orbit(self, dx: float, dy: float = 0.0) -> None:
        self._animation.stop()
        self.user_moved = True
        self.camera.orbit(dx, dy, self.camera.target, self.orbit_mode)
        self.cameraChanged.emit()

    def _pivot_at(self, x: float, y: float, hit) -> np.ndarray:
        """Where an orbit begun with the pointer at (x, y), over `hit` (the model point there, or None), turns: the
        centre the preferences ask for, brought back to the middle of the view at its depth if it left the view
        (the middle of a selection scrolled away: study 16, G5)."""
        w, h = self.size
        if self.pivot_mode == "selection" and self.selection_centre is not None:
            p = np.asarray(self.selection_centre, dtype=float)
        elif self.pivot_mode == "centre":
            p = self.camera.target.copy()
        else:
            p = self.camera.pivot(x, y, w, h, hit)
        return self.camera.keep_in_view(p, w, h)

    def _do(self, actions) -> None:
        w, h = self.size
        hit = self._press[0] if self._press else None
        # a drag begins a few pixels after the press: its pivot is where the button went down, as what was hit
        sx, sy = self.navigator.start or (None, None)
        for a in actions:
            if a.kind in ("orbit", "pan", "zoom", "wheel", "recentre"):
                self._animation.stop()
                self.user_moved = True
                if a.kind != "orbit":
                    self._set_hint(None)                   # the pivot under a pointer that has not moved changed
                if self._flash_point is not None:
                    self._flash.stop()                     # and the point of the recentre is not the target any more
                    self._flash_point = None
            if a.kind == "orbit":
                if a.phase == "begin":
                    self._pivot = self._pivot_at(a.x if sx is None else sx, a.y if sy is None else sy, hit)
                    self._orbiting = True
                    self._set_hint(None)                   # the cross-hair stops on the pivot of the orbit
                elif a.phase == "move":
                    self.camera.orbit(a.dx, a.dy, self._pivot, self.orbit_mode)
                else:
                    self._orbiting = False
            elif a.kind == "pan":
                if a.phase == "begin":
                    self._depth = hit if hit is not None else self.camera.zoom_point(
                        a.x if sx is None else sx, a.y if sy is None else sy, w, h)
                elif a.phase == "move":
                    self.camera.pan(a.dx, a.dy, w, h, self._depth)
            elif a.kind == "zoom" and a.phase == "move":
                self.camera.zoom(-a.dy / 40.0, self.camera.target)
            elif a.kind == "wheel":
                self.camera.zoom(a.dy, self.camera.zoom_point(a.x, a.y, w, h, hit))
            elif a.kind == "recentre":
                point = hit if hit is not None else self.camera.ground(a.x, a.y, w, h)
                if point is not None:
                    target = self.camera.copy()
                    target.recentre(point)
                    self.go(target)
                    self._flash_start(point)
                continue
            elif a.kind == "fit":
                if self.scene is not None:
                    self.user_moved = False
                    self.frame(*self.scene, animate=True)
                continue
            elif a.kind == "select":
                point, name, index = self._press or (None, "", -1)
                p = point if point is not None else np.zeros(3)
                self.picked.emit(name, index, float(p[0]), float(p[1]), float(p[2]), point is not None)
                continue
            elif a.kind == "menu":
                self.menuRequested.emit(a.x, a.y)
                continue
            self.cameraChanged.emit()


class GizmoField(QFrame):
    """The field next to the gizmo (task 16b; DIALux's manipulators have their input fields): East and North in
    metres and the angle in degrees, Tab from one to the next, Enter applies what is written, Esc closes. While a
    handle is dragged it shows the value reached."""
    typed = Signal(object, object, object)      # East, North (m), degrees: a number, or None for a field left empty
    closed = Signal()
    NAMES = ("x", "y", "rz")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("gizmoField")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)      # its rounded card from the sheet (R60)
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 6, 8, 6)              # a little window as the others (R60)
        row.setSpacing(6)
        self.edits: dict[str, QLineEdit] = {}
        for name, label, unit in (("x", "E", "m"), ("y", "N", "m"), ("rz", "", "°")):
            if label:
                row.addWidget(QLabel(label))
            edit = QLineEdit()
            edit.setFixedWidth(64)
            edit.setAlignment(Qt.AlignmentFlag.AlignRight)
            edit.setPlaceholderText(unit)
            edit.setToolTip({"x": _("Metres East (negative: West)"), "y": _("Metres North (negative: South)"),
                             "rz": _("Degrees, anticlockwise")}[name])
            edit.installEventFilter(self)
            row.addWidget(edit)
            if unit == "°":
                row.addWidget(QLabel("°"))
            self.edits[name] = edit
        self.live = False                       # showing a drag, not written in
        self.hide()

    def open(self, handle: str, text: str = "") -> None:
        """Writing begins: the field of the handle taken last (the square and the arrow up: East), with `text`."""
        name = handle if handle in self.edits else "x"
        self.live = False
        for e in self.edits.values():
            e.setReadOnly(False)
            e.clear()
        self.show()
        self.raise_()
        self.edits[name].setFocus()
        self.edits[name].setText(text)

    def show_value(self, east: float, north: float, degrees: float) -> None:
        """A drag going on: the value it has reached."""
        self.live = True
        for name, value, decimals in (("x", east, 2), ("y", north, 2), ("rz", degrees, 1)):
            self.edits[name].setReadOnly(True)
            self.edits[name].setText(number(value, decimals))
        self.show()
        self.raise_()

    def done(self) -> None:
        if self.live:
            self.live = False
            self.hide()

    def values(self) -> tuple:
        return tuple(move.parse(self.edits[n].text()) for n in self.NAMES)

    def eventFilter(self, obj, event) -> bool:
        from PySide6.QtCore import QEvent
        if event.type() != QEvent.Type.KeyPress or self.live:
            return False
        key = event.key()
        if key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            names = list(self.NAMES)
            here = next((n for n, e in self.edits.items() if e is obj), "x")
            step = -1 if key == Qt.Key.Key_Backtab else 1
            self.edits[names[(names.index(here) + step) % len(names)]].setFocus()
            return True
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            values = self.values()
            self.hide()
            self.closed.emit()
            if any(v is not None for v in values):
                self.typed.emit(*values)
            return True
        if key == Qt.Key.Key_Escape:
            self.hide()
            self.closed.emit()
            return True
        return False


ARROWS = {Qt.Key.Key_Left: "left", Qt.Key.Key_Right: "right", Qt.Key.Key_Up: "up", Qt.Key.Key_Down: "down"}


class View3D(QuickImage):
    modulePicked = Signal(int)          # index into the last table set
    buildingPicked = Signal()
    pointPicked = Signal(float, float)  # a click on a building or the ground: the plan's point (x East, y North)
    hoverPicked = Signal(tuple)         # under the pointer: ("module", index), ("point", x, y) or ("",)
    failed = Signal(str)                # the graphics could not start: why
    # Move in the 3D view (task 16b): values typed in the field (East, North, degrees), an arrow of the keyboard (East,
    # North in metres); Esc leaves Move, or the current selection level when Move is not active
    gizmoTyped = Signal(object, object, object)
    nudged = Signal(float, float)
    escaped = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sceneGraphError.connect(lambda _e, message: self.failed.emit(message))
        self.backend = Backend(self)
        self.backend.picked.connect(self._picked)
        self.rootContext().setContextProperty("backend", self.backend)
        self.setSource(QUrl.fromLocalFile(str(QML_FILE)))
        if self.status() != QQmlComponent.Status.Ready:
            raise RuntimeError("3D scene: " + "; ".join(e.toString() for e in self.errors()))
        root = self.rootObject()
        self.geometry_ = root.findChild(QObject, "buildingsGeometry")
        self.instancing = root.findChild(QObject, "modulesTable")
        self.outline_geometry = root.findChild(QObject, "outlineGeometry")
        self.pivot_rings = root.findChild(QObject, "pivotRingsGeometry")
        self.pivot_halo = root.findChild(QObject, "pivotHaloGeometry")
        self.pivot_rings.set_mesh(*mesh.rings(PIVOT_TUBE, mesh.rgb(view_colours.D3["pivot"])))
        self.pivot_halo.set_mesh(*mesh.ring_bands(PIVOT_BAND, mesh.rgb(view_colours.D3["pivot_halo"])))
        # the gizmo of Move (task 16b): its shapes once, one unit long; the scene scales and colours them
        halo, (radius, width, thick) = mesh.GIZMO_HALO, mesh.GIZMO_RING
        for name, shape in (("gizmoXGeometry", mesh.arrow(gizmo.EAST)), ("gizmoYGeometry", mesh.arrow(gizmo.NORTH)),
                            ("gizmoZGeometry", mesh.arrow(gizmo.UP)), ("gizmoPlaneGeometry", mesh.square(*mesh.GIZMO_PLANE)),
                            ("gizmoRingGeometry", mesh.annulus(radius, width, thick)),
                            ("gizmoHaloXGeometry", mesh.arrow(gizmo.EAST, halo)),
                            ("gizmoHaloYGeometry", mesh.arrow(gizmo.NORTH, halo)),
                            ("gizmoHaloRingGeometry", mesh.annulus(radius, width + halo, thick + halo / 2))):
            root.findChild(QObject, name).set_mesh(*shape)
        self.preview_geometry = root.findChild(QObject, "previewGeometry")
        self.preview = np.zeros((0, 2, 3))   # the outline of what Move moves, Qt axes
        self.field = GizmoField(self)
        self.field.typed.connect(self.gizmoTyped)
        self.field.closed.connect(lambda: self.setFocus())
        self.backend.gizmoBegan.connect(self._draw_preview)
        self.backend.gizmoMoving.connect(self._dragging)
        self.backend.gizmoChanged.connect(self._gizmo_changed)
        self.viewbar = None                 # the bar of the view's commands (ui/viewbar.py), set by the window
        round_corners(self)                  # its four corners, inside its card (design 3.2)
        self.outline = {"select": np.zeros((0, 2, 3)), "hover": np.zeros((0, 2, 3))}    # segments, Qt axes
        self.outline_pixel = 0.0             # the metres a pixel was when the ribbons were made
        self.backend.cameraChanged.connect(self._outline_zoomed)
        self.backend.hovered.connect(self._hovered)
        self.fitted = False
        from .marks import MarksOverlay
        from .viewcube import ViewCube
        self.marks = MarksOverlay(self.backend, self)
        self.cube = ViewCube(self.backend, self)
        self.cube.fitRequested.connect(self.frame_scene)

    def event(self, event) -> bool:
        if event.type() == QEvent.Type.NativeGesture:
            kind = event.gestureType()
            at = event.position()
            if kind == Qt.NativeGestureType.ZoomNativeGesture:
                self.backend.touch_zoom(float(np.log(max(0.05, 1.0 + event.value())) /
                                              np.log(1.0 / camera.ZOOM_STEP)),
                                        at.x(), at.y())
            elif kind == Qt.NativeGestureType.RotateNativeGesture:
                self.backend.touch_orbit(event.value() / camera.DEGREES_PER_PIXEL)
            elif kind not in (Qt.NativeGestureType.BeginNativeGesture, Qt.NativeGestureType.EndNativeGesture):
                return super().event(event)
            event.accept()
            return True
        return super().event(event)

    def wheelEvent(self, event) -> None:
        pixel = event.pixelDelta()
        at = event.position()
        modifiers = event.modifiers()
        ctrl = modifiers & Qt.KeyboardModifier.ControlModifier and not modifiers & Qt.KeyboardModifier.AltModifier
        if not pixel.isNull() and ctrl:
            self.backend.touch_zoom(pixel.y() / 60.0, at.x(), at.y())
        elif not pixel.isNull() and modifiers & Qt.KeyboardModifier.ShiftModifier:
            self.backend.touch_orbit(pixel.x(), pixel.y())
        elif not pixel.isNull():
            self.backend.touch_pan(pixel.x(), pixel.y(), at.x(), at.y())
        else:
            self.backend.wheel(event.angleDelta().y() / 120.0, int(modifiers.value), at.x(), at.y(),
                               False, 0.0, 0.0, 0.0)
        event.accept()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.marks.setGeometry(0, 0, self.width(), self.height())
        self.cube.move(self.width() - self.cube.width() - 6, 6)
        self.cube.raise_()
        if self.viewbar is not None:
            self.viewbar.place(self.rect(), [self.cube.geometry()])

    # Move (task 16b): the preview, the field, the keys

    def set_preview(self, segments) -> None:
        """The outline of what moves with the selection (Qt axes): drawn while a handle is dragged."""
        self.preview = np.asarray(segments, dtype=float).reshape(-1, 2, 3)

    def _draw_preview(self) -> None:
        b = self.backend
        if b.gizmo_centre is None or self.preview_geometry is None:
            return
        pixel = b.camera.pixel_size(b.gizmo_centre, b.size[1])
        self.preview_geometry.set_mesh(*mesh.ribbons(self.preview, self.WIDTHS["select"] * pixel,
                                                     mesh.rgb(view_colours.D3["select"])))

    def _dragging(self, handle: str, east: float, north: float, degrees: float) -> None:
        self.field.show_value(east, north, degrees)
        self._place_field()

    def _gizmo_changed(self) -> None:
        b = self.backend
        if not b.gizmo_dragging():
            self.field.done()
        if not b.gizmo_on and self.field.isVisible():
            self.field.hide()

    def _place_field(self) -> None:
        """Next to the gizmo, below and to the right of its middle, inside the view."""
        b = self.backend
        if b.gizmo_centre is None:
            return
        self.field.adjustSize()
        w, h = b.size
        at = b.camera.project(b.gizmo_centre, w, h) or (w / 2, h / 2)
        x = int(min(max(4, at[0] + 28), self.width() - self.field.width() - 4))
        y = int(min(max(4, at[1] + 28), self.height() - self.field.height() - 4))
        self.field.move(x, y)

    def keyPressEvent(self, event) -> None:
        if self._gizmo_key(event):
            return
        if event.key() == Qt.Key.Key_Escape:
            self.escaped.emit()
            return
        super().keyPressEvent(event)

    def _gizmo_key(self, event) -> bool:
        """The keys of Move in the 3D view: a number opens the field on the last handle taken, the arrows nudge
        (10 cm, 1 m with Shift, 1 cm with Ctrl), Esc ends a drag or leaves Move."""
        b = self.backend
        if not b.gizmo_on:
            return False
        key, text = event.key(), event.text()
        if key == Qt.Key.Key_Escape:
            if not b.cancel_gizmo():
                self.escaped.emit()
            self.field.hide()
            return True
        if key in ARROWS and not b.gizmo_dragging():
            mods = {name for flag, name in ((Qt.KeyboardModifier.ControlModifier, "ctrl"),
                                            (Qt.KeyboardModifier.ShiftModifier, "shift")) if event.modifiers() & flag}
            dx, dy = move.nudge(ARROWS[key], mods)
            self.nudged.emit(dx, dy)
            return True
        if text and all(c.isdigit() or c in ",.-" for c in text) and not b.gizmo_dragging():
            self.field.open(b.gizmo_last, text)
            self._place_field()
            return True
        return False

    def frame_scene(self) -> None:
        if self.backend.scene is not None:
            self.backend.user_moved = False
            self.backend.frame(*self.backend.scene, animate=True)

    def show_scene(self, building_mesh, module_table: np.ndarray, fit: bool = False) -> None:
        pos, nor, col = building_mesh
        self.geometry_.set_mesh(pos, nor, col)
        self.instancing.set_table(module_table)
        if len(pos):                                # the ground under what is there, whatever its place (R66)
            lo, hi = pos.min(axis=0), pos.max(axis=0)
            self.backend.set_ground_area(float(lo[0] + hi[0]) / 2, float(lo[2] + hi[2]) / 2,
                                         float(max(hi[0] - lo[0], hi[2] - lo[2])) / 2)
        if (fit or not self.fitted) and len(pos):
            lo, hi = pos.min(axis=0), pos.max(axis=0)
            centre = (lo + hi) / 2
            radius = float(np.linalg.norm(hi - lo)) / 2 + 2.0
            self.backend.set_reach(radius)
            self.backend.user_moved = False
            self.backend.frame(centre, radius, animate=self.fitted)
            self.fitted = True

    def fit(self) -> None:
        self.fitted = False

    def set_navigation(self, style: str, orbit: str, pivot: str, hint: bool = True) -> None:
        """The style of the mouse, the orbit, the pivot's centre, and whether the cross-hair shows on passing over
        with the orbit's key held (Preferences > Navigation)."""
        self.backend.navigator.set_style(style)
        self.backend.orbit_mode = orbit if orbit in ("turntable", "arcball") else "turntable"
        self.backend.set_pivot(pivot if pivot in ("cursor", "selection", "centre") else "cursor", hint)

    def set_sun(self, elevation: float, bearing: float) -> None:
        self.backend.set_sun(elevation, bearing)

    # the outline of the selection and of what is under the pointer (Daniel, 23/10/2026: «andrebbero evidenziati
    # i bordi esterni»): ribbons a few pixels wide, made again when a zoom changes the size of a pixel much

    WIDTHS = view_colours.RIBBONS               # pixels (R35: «un buono spessore a tutto»)

    def set_outline(self, select, hover, select_colour: str = "", hover_colour: str = "") -> None:
        """The outlines of the selection and of what is under the pointer, in their kinds' colours (R67)."""
        self.outline = {"select": np.asarray(select, dtype=float).reshape(-1, 2, 3),
                        "hover": np.asarray(hover, dtype=float).reshape(-1, 2, 3)}
        self.outline_colours = {"select": select_colour or view_colours.D3["select"],
                                "hover": hover_colour or view_colours.D3["hover"]}
        self._draw_outline()

    def _pixel(self) -> float:
        """The metres a pixel is where the outline stands (its middle), as the camera sees it now."""
        segs = np.concatenate([self.outline["select"], self.outline["hover"]])
        if not len(segs):
            return 0.0
        cam, (_w, h) = self.backend.camera, self.backend.size
        if cam.ortho:
            return 2 * cam.half_height() / max(h, 1.0)
        centre = segs.reshape(-1, 3).mean(axis=0)
        depth = max(camera.MIN_DISTANCE, float(np.dot(centre - cam.position, cam.forward())))
        return 2 * depth * np.tan(np.radians(cam.fov) / 2) / max(h, 1.0)

    def _draw_outline(self) -> None:
        if self.outline_geometry is None:
            return
        self.outline_pixel = pixel = self._pixel()
        colours = getattr(self, "outline_colours", {})
        parts = [mesh.ribbons(self.outline[k], self.WIDTHS[k] * pixel, mesh.rgb(colours.get(k, view_colours.D3[k])))
                 for k in ("hover", "select")]
        pos, nor, col = (np.concatenate([part[i] for part in parts]) for i in range(3))
        self.outline_geometry.set_mesh(pos, nor, col)

    def _outline_zoomed(self) -> None:
        old, new = self.outline_pixel, self._pixel()
        if new and (not old or not 0.85 < new / old < 1.18):
            self._draw_outline()

    def _hovered(self, name: str, index: int, x: float, y: float, z: float, hit: bool) -> None:
        """What is under the pointer: a module by its index, anything else by the point of the plan under it."""
        if name == "modules" and index >= 0:
            self.hoverPicked.emit(("module", index))
        elif hit:
            self.hoverPicked.emit(("point", x, -z))
        else:
            self.hoverPicked.emit(("",))

    def _picked(self, name: str, index: int, x: float, y: float, z: float, hit: bool) -> None:
        """A click: a module by its index, anything else by the point of the plan under it (the plan knows what
        lies there), the ground under the cursor when nothing was hit."""
        if name == "modules" and index >= 0:
            self.modulePicked.emit(index)
            return
        if name == "buildings":
            self.buildingPicked.emit()
        if hit:
            self.pointPicked.emit(x, -z)
        else:
            self.pointPicked.emit(float("nan"), float("nan"))
