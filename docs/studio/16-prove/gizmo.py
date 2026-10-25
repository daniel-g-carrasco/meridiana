"""Prova per lo studio 16, tema B: i pezzi di Qt Quick 3D che servono a un gizmo «sposta e ruota» come quello di
DIALux evo, nella configurazione di Meridiana (QQuickWidget, camera di camera.py legata in QML, offscreen).

Che cosa prova:
1. le frecce del gizmo si scelgono con View3D.pick: un clic sul pixel della freccia x dice «x», e così y e z;
   quanto costa un pick. Offscreen, senza GPU, Qt Quick 3D non disegna e il pick non risponde («The View3D
   item is not going to display anything»): questa parte va provata sul PC. In più la scelta fatta in Python
   sullo schermo, proiettando le maniglie e misurando la distanza in pixel come fa la pianta con i lati
   (plan.py, _side_near): non dipende dalla GPU e si prova anche qui;
2. le maniglie restano della stessa grandezza sullo schermo a qualunque distanza, legando la scala alla
   distanza della camera (come l'indicatore del perno di Scene.qml);
3. il trascinamento vincolato a un asse: dal pixel del mouse al punto dell'asse più vicino al raggio della
   camera (due rette sghembe), in Python con camera.Camera.ray; e la rotazione: dal pixel al punto sul piano
   dell'anello, quindi l'angolo; con l'errore rispetto allo spostamento atteso;
4. la proiezione nei due versi (mapFrom3DScene e mapTo3DScene) coincide con camera.Camera.project.

Lancio, dalla radice del repository:
    QT_QPA_PLATFORM=offscreen python docs/studio/16-prove/gizmo.py
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import Property, QObject, QUrl, Signal  # noqa: E402
from PySide6.QtGui import QQuaternion, QVector3D  # noqa: E402
from PySide6.QtQuickWidgets import QQuickWidget  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from meridiana import camera  # noqa: E402

QML = """
import QtQuick
import QtQuick3D

Item {
    id: root
    function pickAt(x, y) {
        const r = view.pick(x, y)
        return r.objectHit ? r.objectHit.objectName : ""
    }
    function project(x, y, z) { return view.mapFrom3DScene(Qt.vector3d(x, y, z)) }
    function unproject(x, y, z) { return view.mapTo3DScene(Qt.vector3d(x, y, z)) }
    View3D {
        id: view
        anchors.fill: parent
        environment: SceneEnvironment { backgroundMode: SceneEnvironment.Color; clearColor: "#ddd" }
        camera: cam
        PerspectiveCamera { id: cam; position: backend.cameraPosition; rotation: backend.cameraRotation
                            clipNear: 0.3; clipFar: 20000 }
        DirectionalLight { eulerRotation: Qt.vector3d(-40, 30, 0) }
        // the object: a 4 m box at the origin
        Model { objectName: "box"; source: "#Cube"; pickable: true; scale: Qt.vector3d(0.04, 0.04, 0.04)
                materials: PrincipledMaterial { baseColor: "#8aa" } }
        // the gizmo: three arrows, the same size on screen (scale from the camera's distance)
        Node {
            id: gizmo
            scale: Qt.vector3d(backend.gizmoScale, backend.gizmoScale, backend.gizmoScale)
            Model { objectName: "x"; source: "#Cylinder"; pickable: true; eulerRotation.z: -90
                    position: Qt.vector3d(50, 0, 0); scale: Qt.vector3d(0.08, 1, 0.08)
                    materials: PrincipledMaterial { baseColor: "#d33"; lighting: PrincipledMaterial.NoLighting } }
            Model { objectName: "y"; source: "#Cylinder"; pickable: true
                    position: Qt.vector3d(0, 50, 0); scale: Qt.vector3d(0.08, 1, 0.08)
                    materials: PrincipledMaterial { baseColor: "#3a3"; lighting: PrincipledMaterial.NoLighting } }
            Model { objectName: "z"; source: "#Cylinder"; pickable: true; eulerRotation.x: 90
                    position: Qt.vector3d(0, 0, 50); scale: Qt.vector3d(0.08, 1, 0.08)
                    materials: PrincipledMaterial { baseColor: "#33d"; lighting: PrincipledMaterial.NoLighting } }
        }
    }
}
"""

PIXELS = 120.0          # how long an arrow should be on the screen, whatever the distance


class Backend(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.camera = camera.Camera()
        self.size = (800.0, 600.0)

    @Property(QVector3D, notify=changed)
    def cameraPosition(self):
        return QVector3D(*map(float, self.camera.position))

    @Property(QQuaternion, notify=changed)
    def cameraRotation(self):
        w, x, y, z = map(float, self.camera.rotation)
        return QQuaternion(w, x, y, z)

    @Property(float, notify=changed)
    def gizmoScale(self):
        """An arrow is 100 units long in its node; this makes it PIXELS long at the gizmo's depth."""
        d = max(camera.MIN_DISTANCE, float(np.dot(-self.camera.position, self.camera.forward())))
        per_pixel = 2 * d * math.tan(math.radians(self.camera.fov) / 2) / self.size[1]      # metres per pixel
        return PIXELS * per_pixel / 100.0


def screen_pick(cam: camera.Camera, px, py, w, h, handles: dict, tolerance_px: float = 8.0) -> str:
    """The handle (name -> (a, b) segment in the scene) nearest the pixel, within the tolerance, or ""."""
    best, where = tolerance_px, ""
    for name, (a, b) in handles.items():
        pa, pb = cam.project(a, w, h), cam.project(b, w, h)
        if pa is None or pb is None:
            continue
        dx, dy = pb[0] - pa[0], pb[1] - pa[1]
        n2 = dx * dx + dy * dy
        t = 0.0 if n2 < 1e-9 else max(0.0, min(1.0, ((px - pa[0]) * dx + (py - pa[1]) * dy) / n2))
        d = math.hypot(px - (pa[0] + t * dx), py - (pa[1] + t * dy))
        if d < best:
            best, where = d, name
    return where


def axis_drag(cam: camera.Camera, px, py, w, h, origin, axis):
    """Where the point of the axis line (origin + t axis) closest to the ray through the pixel is: t."""
    o, d = cam.ray(px, py, w, h)
    a = np.asarray(axis, dtype=float)
    p = np.asarray(origin, dtype=float)
    # closest points of two lines p + t a and o + s d
    n = np.cross(a, d)
    if np.linalg.norm(n) < 1e-9:
        return 0.0
    n2 = np.cross(d, n)
    t = float(np.dot(o - p, n2) / np.dot(a, n2))
    return t


def ring_angle(cam: camera.Camera, px, py, w, h, centre, normal, zero):
    """The angle of the hit of the ray through the pixel with the ring's plane, from the direction `zero`."""
    o, d = cam.ray(px, py, w, h)
    n = np.asarray(normal, dtype=float)
    c = np.asarray(centre, dtype=float)
    s = float(np.dot(c - o, n) / np.dot(d, n))
    hit = o + s * d
    v = hit - c
    u = np.asarray(zero, dtype=float)
    return math.degrees(math.atan2(float(np.dot(np.cross(u, v), n)), float(np.dot(u, v))))


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    backend = Backend()
    w, h = 800, 600
    backend.size = (float(w), float(h))
    cam = backend.camera
    cam.position = np.array([12.0, 9.0, 16.0])
    cam.rotation = camera.look(cam.bearing(), 0.0)
    cam.target = np.zeros(3)
    cam.rotation = camera.look(math.degrees(math.atan2(-cam.position[0], cam.position[2])) % 360.0,
                               -math.degrees(math.atan2(cam.position[1], math.hypot(cam.position[0], cam.position[2]))))
    widget = QQuickWidget()
    widget.rootContext().setContextProperty("backend", backend)
    widget.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
    qml = Path(__file__).with_suffix(".qml")
    qml.write_text(QML)
    widget.setSource(QUrl.fromLocalFile(str(qml)))
    if widget.status() != QQuickWidget.Status.Ready:
        print("QML:", "; ".join(e.toString() for e in widget.errors()))
        return 1
    widget.resize(w, h)
    widget.show()
    for _i in range(5):
        app.processEvents()
    root = widget.rootObject()
    widget.grab()                                   # a first frame, so that the picking has a scene
    app.processEvents()

    def project(p):
        v = root.project(float(p[0]), float(p[1]), float(p[2]))
        return v.x(), v.y(), v.z()

    # 4. projection agrees with camera.py
    worst = 0.0
    for p in ((0, 0, 0), (3, 1, -2), (-4, 2, 5)):
        qx, qy, _ = project(p)
        mx, my = cam.project(p, w, h)
        worst = max(worst, math.hypot(qx - mx, qy - my))
    print(f"proiezione QML contro camera.project: scarto massimo {worst:.3f} px")
    back = root.unproject(400.0, 300.0, 20.0)
    print(f"mapTo3DScene(400, 300, profondità 20) = ({back.x():.2f}, {back.y():.2f}, {back.z():.2f})")

    # 1. picking the arrows
    scale = backend.gizmoScale
    hits = {}
    times = []
    for name, axis in (("x", (1, 0, 0)), ("y", (0, 1, 0)), ("z", (0, 0, 1))):
        mid = np.array(axis, dtype=float) * 50 * scale
        px, py, _ = project(mid)
        t = time.perf_counter()
        hits[name] = root.pickAt(px, py)
        times.append(time.perf_counter() - t)
    t = time.perf_counter()
    nothing = root.pickAt(5.0, 5.0)
    times.append(time.perf_counter() - t)
    print(f"View3D.pick sulle frecce: {hits}  (vuoto in un angolo: {nothing!r}); "
          f"un pick costa {min(times) * 1000:.2f}-{max(times) * 1000:.2f} ms"
          + ("  [senza GPU il pick non vede nulla: da provare sul PC]" if not any(hits.values()) else ""))
    handles = {n: ((0, 0, 0), tuple(c * 100 * scale for c in a)) for n, a in
               (("x", (1, 0, 0)), ("y", (0, 1, 0)), ("z", (0, 0, 1)))}
    own = {}
    times = []
    for name, axis in (("x", (1, 0, 0)), ("y", (0, 1, 0)), ("z", (0, 0, 1))):
        mid = np.array(axis, dtype=float) * 50 * scale
        px, py, _ = project(mid)
        t = time.perf_counter()
        own[name] = screen_pick(cam, px + 5, py - 3, w, h, handles)         # 6 px off the arrow
        times.append(time.perf_counter() - t)
    print(f"scelta in Python sullo schermo (6 px accanto alla freccia): {own}  (in un angolo: "
          f"{screen_pick(cam, 5, 5, w, h, handles)!r}); costa {max(times) * 1000:.3f} ms")

    # 2. the same size on the screen at two distances
    lengths = []
    for factor in (1.0, 3.0):
        cam.position = np.array([12.0, 9.0, 16.0]) * factor
        backend.changed.emit()
        app.processEvents()
        s = backend.gizmoScale
        a, b = project((0, 0, 0)), project((100 * s, 0, 0))
        lengths.append(math.hypot(a[0] - b[0], a[1] - b[1]))
    print(f"freccia x sullo schermo a distanza 1 e 3: {lengths[0]:.1f} e {lengths[1]:.1f} px (chiesti {PIXELS:.0f}, "
          "meno lo scorcio della prospettiva)")
    cam.position = np.array([12.0, 9.0, 16.0])
    backend.changed.emit()
    app.processEvents()

    # 3. constrained drag along x: the pixel of the point (2.5, 0, 0) must give t = 2.5 on the x axis
    worst = 0.0
    for want in (0.5, 2.5, -3.0):
        for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            p = np.array(axis, dtype=float) * want
            px, py, _ = project(p)
            got = axis_drag(cam, px, py, w, h, (0, 0, 0), axis)
            worst = max(worst, abs(got - want))
    print(f"trascinamento vincolato a un asse: errore massimo {worst:.2e} m su spostamenti di 0,5, 2,5 e -3 m")
    # the rotation ring in the horizontal plane (normal y): the pixel of a point at 30° must give 30°
    worst = 0.0
    for want in (30.0, 120.0, -45.0):
        r = math.radians(want)
        p = (3 * math.cos(r), 0.0, -3 * math.sin(r))           # from +x towards -z: counter-clockwise seen from above
        px, py, _ = project(p)
        got = ring_angle(cam, px, py, w, h, (0, 0, 0), (0, 1, 0), (1, 0, 0))
        worst = max(worst, abs(got - want))
    print(f"rotazione sull'anello orizzontale: errore massimo {worst:.2e}° su 30°, 120° e -45°")
    qml.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())
