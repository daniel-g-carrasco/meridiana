"""Attach the native view's controls to the shell, plan tools and preferences.

R23 F6, on the backend-QML contract (docs/studio/39-contratto-backend-qml.md): the 3D view (Shell/View3DHost.qml, made
by a Loader) binds the properties of `sceneControls` (navigation, tools, the view selector), answers its requests
(fitRequested, zoomRequested) and calls its slots with plain values (viewButton, viewWanted, viewTool, viewSnaps);
it writes back whether it has the keyboard (viewFocused). The backend never holds the view nor writes its properties:
a wrapper of an item made by a Loader outlives it (the crashes of r20/r21). Meridio's home (the 3D view in Modelling,
else the central panel) is chosen by Assistant/AssistantHost.qml."""
from PySide6.QtCore import Property, QObject, Signal, Slot

from meridiana import config
from .parts import Part
from .plan import PLACE_TOOLS       # R554: the plan's tools that place 3D objects, fed by the 3D view's clicks too


class SceneControls(QObject):
    navigationChanged = Signal()
    toolChanged = Signal()
    viewSelectorChanged = Signal()
    viewFocusedChanged = Signal()
    fitRequested = Signal()
    zoomRequested = Signal(int)

    def __init__(self, engine, host):
        super().__init__(engine)
        self.host = host
        self.root = None
        self.settings = None
        self._tool_sync = False
        self._move = False
        self._placing = False
        self._snaps = True
        self._selector = False
        self._focused = False

    def bind(self, root):
        self.root = root
        self.settings = self.host.parts.controllers.get('settings')
        if self.settings is not None:
            self.settings.stateChanged.connect(self.configure)
        self.configure()
        self.host.scene.commandRequested.connect(self.context_command)
        root.viewModeChanged.connect(self.view_mode)
        root.phaseChanged.connect(lambda: self.host.scene.setPhase(str(self.root.property('phase'))))
        self.host.scene.setPhase(str(self.root.property('phase')))
        if self.host.plan is not None:
            self.host.plan.stateChanged.connect(self.plan_tool)
            self.plan_tool()
        self.view_mode()

    def _cfg(self):
        return self.settings.cfg if self.settings is not None else getattr(self.host, 'cfg', None) or config.Config()

    navigationStyle = Property(str, lambda self: self._cfg().navigation, notify=navigationChanged)
    orbitMode = Property(str, lambda self: self._cfg().orbit, notify=navigationChanged)
    pivotMode = Property(str, lambda self: self._cfg().pivot, notify=navigationChanged)
    pivotHint = Property(bool, lambda self: bool(self._cfg().pivot_hint), notify=navigationChanged)
    # the 3D's edges (study 41, slice E): "full", "moving" (lighter while the view moves), "low"
    edgeQuality = Property(str, lambda self: self._cfg().edges_3d, notify=navigationChanged)
    moveMode = Property(bool, lambda self: self._move, notify=toolChanged)
    placing = Property(bool, lambda self: self._placing, notify=toolChanged)
    snaps = Property(bool, lambda self: self._snaps, notify=toolChanged)
    viewSelector = Property(bool, lambda self: self._selector, notify=viewSelectorChanged)

    def _focused_get(self):
        return self._focused

    def _focused_set(self, value):
        if self._focused != bool(value):
            self._focused = bool(value)
            self.viewFocusedChanged.emit()

    # QML -> Python: the 3D view is shown and has the keyboard (Shell/View3DHost.qml writes it)
    viewFocused = Property(bool, _focused_get, _focused_set, notify=viewFocusedChanged)

    @Slot()
    def configure(self):
        self.navigationChanged.emit()

    @Slot()
    def view_mode(self):
        selector = self.root is not None and self.root.property('viewMode') == '3d'
        if selector != self._selector:
            self._selector = selector
            self.viewSelectorChanged.emit()

    @Slot()
    def plan_tool(self):
        if self._tool_sync:
            return
        self._tool_sync = True
        try:
            self._move = self.host.plan.tool in ('move', 'rotate')
            placing = self.host.plan.tool in PLACE_TOOLS
            if self._placing and not placing and getattr(self.host, 'scene', None) is not None:
                self.host.scene.placePreview('', 0., 0.)
            self._placing = placing
            self._snaps = bool(self.host.plan.snapsEnabled)
            self.toolChanged.emit()
        finally:
            self._tool_sync = False

    @Slot(bool)
    def viewTool(self, on):
        """The view's move or vertex mode changed by the user."""
        if self._tool_sync or self.host.plan is None:
            return
        self._tool_sync = True
        try:
            self.host.plan.setTool('move' if on else 'select')
        finally:
            self._tool_sync = False

    @Slot(str, float, float, float, int, float)
    def viewPlace(self, how, x, y, z, bits, mpp):
        """R554 (Daniel 08/11/2026, «dovrebbero potersi inserire anche sul 3d»): the 3D view's pointer and clicks
        given to the plan's tool «3D object» at the point the ray met (a roof, a wall, an object) or, where it met
        nothing, at the ground under the pointer (Qt axes: east x, north -z). The plan's machine places it: the same
        snaps, the same building under the point, the same repeat, row and family; `how` is move, click, double,
        enter or escape; `mpp` the metres of a pixel at that point, for the snaps' reach."""
        plan = self.host.plan
        if plan is None or plan.tool not in PLACE_TOOLS:
            return
        if how in ('escape', 'enter'):
            plan.key('Escape' if how == 'escape' else 'Return', '', 0)
        else:
            east, north = float(x), -float(z)
            plan.pointer(east, north, int(bits), float(mpp) if mpp > 0 else .05)
            if how == 'click':
                plan.click(east, north, int(bits))
            elif how == 'double':
                plan.doubleClick(east, north, int(bits))
        scene = getattr(self.host, 'scene', None)
        if scene is None:
            return
        point = plan.drawing.pointer if plan.tool in PLACE_TOOLS else None
        if point is None:
            scene.placePreview('', 0., 0.)
        else:
            scene.placePreview(str(plan.drawing.options.get('kind', '')), float(point[0]), float(point[1]))

    @Slot(bool)
    def viewSnaps(self, snaps):
        if not self._tool_sync and self.host.plan is not None and snaps != self.host.plan.snapsEnabled:
            self.host.plan.viewAction('snaps')

    @Slot(str)
    def viewWanted(self, mode):
        """The view's own selector (plan, 3D, both)."""
        self.host.shell.viewModeRequested.emit(mode)

    # R538: the 3D view's Fit, + and - act on the 3D view alone (they went through the window's commands, which
    # zoomed the plan, and the plan's zoom came back to the 3D view)
    def fit(self):
        self.fitRequested.emit()

    def zoom(self, direction):
        self.zoomRequested.emit(direction)

    @Slot(str)
    def viewButton(self, command):
        if command == 'fit':
            self.fit()
        elif command in ('zoom_in', 'zoom_out'):
            self.zoom(1 if command == 'zoom_in' else -1)
        else:
            self.host.shell.trigger(command)

    @Slot(str)
    def context_command(self, command):
        if command == 'frame':
            self.fit()
        elif command == 'properties':
            inspectors = self.host.parts.controllers.get('inspectors')
            if inspectors is not None:
                inspectors.show_panel('properties')
        elif command == 'resize_row' and self.host.plan is not None:
            self.host.plan.setTool('select')
            self.host.shell.viewModeRequested.emit('both')


def install(engine, session, cache, window):
    # install_scene already owns the backend and the source slot. Add only its
    # bindings so discovery cannot install a second scene on the same session.
    controller = SceneControls(engine, window)
    engine.rootContext().setContextProperty('sceneControls', controller)
    return Part('scene-controls', controllers={'sceneControls':controller}, bind=controller.bind,
                commands={'fit':controller.fit, 'zoom_in':lambda: controller.zoom(1),
                          'zoom_out':lambda: controller.zoom(-1)})
