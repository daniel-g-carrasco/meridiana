"""The 3D view's side of the measuring tool (study 46, state of r34-righello section 2.6): its probe registered with the
window's MeasureBridge (gui/backend/measure.py) as the view "3d", the scene's triangles taken again when the scene
changes, the 3D view's gestures sent to the bridge.

The view calls here only at a click and when the pointer has stopped (Viewport.qml): never at a step of the pointer.
It gives the pointer's ray (origin and unit direction, its own axes) and how many metres a pixel is along it
(`fixed` + `spread` * distance); the probe itself is app/view/scene_probe.py (no Qt), built at the first ask after a
change of the scene.
"""
from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from meridiana.app.view.measure_tool import IGNORED
from meridiana.app.view.scene_probe import SceneProbe

VIEW = "3d"


class SceneMeasure(QObject):
    annotationChanged = Signal()
    annotationPendingChanged = Signal()

    def __init__(self, scene, bridge, parent=None):
        super().__init__(parent)
        self.scene, self._bridge = scene, bridge
        self._probe_made = None
        self._aim = None                # (origin, direction, (fixed, spread)) of the last click or pointer at rest
        self.asked = 0                  # the probes made: the light-work tests count them
        self._annotation = dict(segments={}, points={})
        self._annotation_pending = False
        self._annotation_serial = 0
        self._scene_serial = 0
        self._annotation_snapshot = None
        self._annotation_sent = None
        self._annotation_camera = None
        bridge.register(VIEW, self._probe)
        scene.sceneChanged.connect(self._forget)

    def _forget(self):
        self._probe_made = None
        self._scene_serial += 1
        self._annotation_snapshot = None
        self._annotation_camera = None
        self._annotation_serial += 1
        self._annotation = dict(segments={}, points={})
        self._annotation_pending = False
        self.annotationChanged.emit()
        self.annotationPendingChanged.emit()

    annotationData = Property('QVariantMap', lambda self: self._annotation, notify=annotationChanged)
    annotationPending = Property(bool, lambda self: self._annotation_pending, notify=annotationPendingChanged)

    @Slot()
    def invalidateVisibility(self):
        """Reject in-flight answers, keeping the last world-space clipping while moving."""
        self._annotation_serial += 1
        self._annotation_camera = None
        self._annotation_pending = False
        self.annotationPendingChanged.emit()

    @Slot('QVariantMap')
    def visibility(self, request):
        """Exact triangle clipping in the existing job process; never cast rays on the GUI thread."""
        from meridiana.app.view import annotation_visibility as visibility
        request = dict(request)
        self._annotation_serial += 1
        serial = self._annotation_serial
        key = f'{id(self)}:{self._scene_serial}'
        if request['camera'] != self._annotation_camera:
            self._annotation_camera = request['camera']
        self._annotation_pending = True
        self.annotationPendingChanged.emit()
        center = self.scene.scenes.center if self.scene.scenes is not None else None
        if center is None:              # isolated scene hosts, as the scene builder's synchronous fallback
            self._annotation = visibility.calculate(self.scene.triangles[0], request)
            self._annotation_pending = False
            self.annotationChanged.emit()
            self.annotationPendingChanged.emit()
            return
        if self._annotation_snapshot is None:
            from meridiana.gui.backend import scene_context
            session = self.scene.session
            context = None
            models = self.scene.contextModels
            ref = scene_context.reference(session.project)
            if models and ref:
                context = dict(path=ref['context']['mesh'], skip=ref['context'].get('skip') or [],
                               hidden=list(scene_context.derived(session.project, ref)),
                               position=models[0]['position'], turn=models[0]['turn'])
            self._annotation_snapshot = dict(photo=session.photo(), context=context,
                                            keys={sid: session.layout_keys.get(sid) for sid in session.good_results()})
        payload = request | dict(scene_key=key)
        if self._annotation_sent != key:
            payload.update(self._annotation_snapshot)

        def done(answer, stale):
            if stale or serial != self._annotation_serial:
                return
            if answer.get('missing_scene'):
                self._annotation_sent = None
                self.visibility(request)
                return
            self._annotation_sent = key
            self._annotation = answer
            self._annotation_pending = False
            self.annotationChanged.emit()
            self.annotationPendingChanged.emit()

        def failed(_kind, _message):
            if serial == self._annotation_serial:
                self._annotation_pending = False
                self.annotationPendingChanged.emit()

        center.submit(visibility.KIND, payload, slot=f'annotations:{id(self)}',
                      on_done=done, on_failed=failed, settle=True)

    def geometry(self) -> SceneProbe:
        if self._probe_made is None:
            triangles = getattr(self.scene, "triangles", None)
            self._probe_made = SceneProbe(triangles[0] if triangles is not None else ())
        return self._probe_made

    def _probe(self, _x, _y, _scale, wanted):
        if self._aim is None:
            return None
        self.asked += 1
        origin, direction, pixel = self._aim
        return self.geometry().probe(origin, direction, pixel, wanted, ground=not self.scene.context_slots.shown())

    def _aimed(self, origin, direction, fixed, spread):
        self._aim = (tuple(origin), tuple(direction), (float(fixed), float(spread)))

    bridge = Property(QObject, lambda self: self._bridge, constant=True)

    # the 3D view's gestures with the tool Measure in hand

    @Slot('QVariantList', 'QVariantList', float, float, int)
    def pointer(self, origin, direction, fixed, spread, bits):
        """The pointer has stopped: the point under it found, the span to it with its numbers."""
        self._aimed(origin, direction, fixed, spread)
        self._bridge.move(VIEW, 0.0, 0.0, bits, 1.0)

    @Slot('QVariantList', 'QVariantList', float, float, int)
    def click(self, origin, direction, fixed, spread, bits):
        self._aimed(origin, direction, fixed, spread)
        self._bridge.click(VIEW, 0.0, 0.0, bits, 1.0)

    @Slot(int)
    def doubleClick(self, bits):
        self._bridge.doubleClick(VIEW, 0.0, 0.0, bits, 1.0)

    @Slot(str, str, int, result=bool)
    def key(self, key, text, bits):
        """True when the key was the tool's (or it left the tool), False when the view may use it."""
        return self._bridge.key(key, text, bits) != IGNORED
