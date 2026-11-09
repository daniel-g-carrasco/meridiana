"""Install the three inspectors on the workbench's one project session."""
from PySide6.QtCore import QObject, QTimer, Slot, Property, Signal

from meridiana import checks, mesh, viewaids
from meridiana.i18n import _
from .parts import Part, QML
from .properties import PropertiesBackend
from .checks import ChecksBackend
from .project_tree import ProjectTreeBackend


class Inspectors(QObject):
    sideChanged = Signal()
    marksChanged = Signal()
    # R23 F6 (docs/studio/39): the plan frames these bounds (Shell/PlanHost.qml answers); the overlays on the plan and
    # on the 3D view (SideHighlight, SceneMarks) are made in QML (PlanHost, View3DHost) and bind this object
    fitBoundsRequested = Signal('QVariant')

    def __init__(self, engine, session, window):
        super().__init__(engine)
        self.host, self.session = window, session
        self.properties = PropertiesBackend(session, self)
        self.checks = ChecksBackend(session, self)
        self.tree = ProjectTreeBackend(session, self)
        self._published = None
        self._phase, self._before_delivery = 'model', 'level'
        self.root = None
        self._side, self._side_segment = None, []
        self._marks3d = []
        session.subscribe(self.session_changed)
        self.properties.actionRequested.connect(self.action)
        self.properties.helpRequested.connect(self.help)
        self.tree.propertiesRequested.connect(self.show_properties)
        self.tree.frameRequested.connect(self.frame)
        self.tree.checksRequested.connect(self.show_checks)
        self.checks.changed.connect(self.publish)
        self.checks.focusRequested.connect(self.focus)
        self.checks.computeRequested.connect(window.bridge.recompute)
        self.checks.commandRequested.connect(window.shell.trigger)
        self.checks.askRequested.connect(self.ask)
        for controller in (self.properties, self.checks, self.tree):
            controller.errorOccurred.connect(self.notice)

    def bind(self, root):
        self.root = root
        if 'assistant_help' in self.host.parts.controllers:
            # Assistant's adapter handles both the content and placement once.
            self.properties.helpRequested.disconnect(self.help)
        root.phaseChanged.connect(self.phase_changed)
        if self.host.plan is not None:
            self.host.plan.edgePicked.connect(self.edge_picked)
            self.host.plan.pointsPicked.connect(self.points_picked)
            self.host.plan.markClicked.connect(lambda kind, oid: self.show_checks(kind, oid, ''))
        self.phase_changed()
        self.publish()

    @Property('QVariantList', notify=sideChanged)
    def sideSegment(self):
        return self._side_segment

    @Property('QVariantList', notify=marksChanged)
    def marks3d(self):
        return self._marks3d

    def session_changed(self, topics):
        if 'selection' in topics or 'file' in topics:
            self._side = None
            self._side_segment = []
            self.sideChanged.emit()
        elif self._side and any(t == 'project:geometry' or t.startswith('layout:') for t in topics):
            self.highlight_side(*self._side)

    def highlight_side(self, kind, oid, side):
        self._side = (kind, oid, side) if side >= 0 else None
        self._side_segment = []
        objects = {'building': self.session.project.buildings, 'subfield': self.session.project.subfields,
                   'exclusion': self.session.project.exclusions}
        obj = next((x for x in objects.get(kind, []) if x.id == oid), None)
        ring = getattr(obj, 'footprint', getattr(obj, 'ring', []))
        if 0 <= side < len(ring):
            self._side_segment = [list(ring[side]), list(ring[(side + 1) % len(ring)])]
        self.sideChanged.emit()

    @Slot()
    def phase_changed(self):
        phase = self.root.property('phase')
        # Modelling has the small contextual help on each C3 group, as in Widgets: the card's help button is hidden
        # there by Workbench.qml (propertiesHelp), the other phases keep it
        self.checks.setPhase(phase)
        if phase == 'report' and self._phase != 'report':
            self._before_delivery = self.checks.view
            self.checks.setView('delivery')
        elif self._phase == 'report' and self.checks.view == 'delivery':
            self.checks.setView(self._before_delivery)
        self._phase = phase

    @Slot()
    def publish(self):
        # Changing a filter or keyboard row does not rebuild the project tree.
        if self._published is self.checks.items:
            return
        self._published = self.checks.items
        self.tree.set_checks(self.checks.items)
        marks, self._marks3d = [], []
        for (kind, oid), mark in checks.marks(self.checks.items).items():
            anchor = viewaids.anchor(self.session.project, kind, oid)
            if anchor is not None:
                x, y, z = anchor
                marks.append((x, y, mark.level, mark.count, (kind, oid)))
                self._marks3d.append(dict(point=list(mesh.to_qt(x, y, z + 0.6)), level=mark.level,
                                          count=mark.count, kind=kind, oid=oid))
        self.marksChanged.emit()
        if self.host.plan is not None:
            self.host.plan.setMarks(marks)

    def show_panel(self, name):
        if self.root is None:
            return
        self.host.shell.panelRequested.emit(name)       # opened and brought forward by Workbench.qml

    @Slot(str, str)
    def show_properties(self, kind, oid):
        self.session.select(kind, oid)
        self.root.showPhase('model')
        self.show_panel('properties')

    @Slot(str, str, str)
    def show_checks(self, kind, oid, _name=''):
        self.checks.showSubset([kind, oid])
        self.show_panel('checks')

    @Slot('QVariantList')
    def focus(self, target):
        if target and target[0] == 'site':
            self.frame('site', '')
            return
        if len(target) < 2:
            return
        kind, oid = target[:2]
        if kind == 'phase':
            self.root.showPhase(oid)
        else:
            self.frame(kind, oid)

    @Slot(str, str)
    def frame(self, kind, oid):
        self.session.select(kind, oid)
        if self.root.property('phase') not in ('model', 'plant'):
            self.root.showPhase('model')
        if self.host.plan is not None:
            self.fitBoundsRequested.emit(self.host.plan.targetBounds)
        else:
            self.host.shell.trigger('fit')

    @Slot(str)
    def help(self, key):
        service = self.host.engine.rootContext().contextProperty('assistantHelp')
        if service is not None:
            service.request(key)
        else:
            self.notice(_('Help') + ': ' + key)

    @Slot(object)
    def ask(self, item):
        chat = self.host.engine.rootContext().contextProperty('assistantChat')
        if chat is not None:
            chat.ask_about(item)
        else:
            self.notice(_('Ask {name}').format(name='Meridio') + ': ' + item.text)

    @Slot(str)
    def notice(self, text):
        self.host.bridge._error = text
        self.host.bridge.stateChanged.emit()

    @Slot(str, str, str)
    def action(self, action, kind, oid):
        if action.startswith('pick_') and self.host.plan is not None:
            building = self.session.project.building(oid)
            if building is None:
                return
            purpose = action[5:]
            ring = building.footprint
            if purpose.startswith('free_eave:'):
                ring = building.roof.free_pitches[int(purpose.split(':')[1])]['ring']
            self.root.showPhase('model')
            self.host.plan.pickEdge(purpose, kind, oid, ring)
        elif action == 'trace_saddles' and self.host.plan is not None and self.session.project.building(oid):
            self.root.showPhase('model')
            self.host.plan.pickPoints('saddles:' + oid, [_('Click where the line of the bands starts; Esc gives up'),
                                                         _('Click where it ends: the bands run along it')])
        elif action.startswith('light_side:'):
            side = action.partition(':')[2]
            self.highlight_side(kind, oid, int(side) if side else -1)
        elif action == 'site':
            files = self.host.parts.controllers.get('filePart')
            if files is not None:
                files.openDialog('site')
            else:
                self.host.shell.trigger('site')
        elif action == 'catalog_module' and 'plantActions' in self.host.parts.controllers:
            # Plant's adapter listens to this signal and opens its catalogue.
            return
        else:
            self.host.shell.trigger(action)

    @Slot(str, str, str, int)
    def points_picked(self, purpose, points):
        """The line of the bands of a saddle roof traced on the plan (two clicks): its bearing is their direction."""
        if not purpose.startswith('saddles:') or len(points) < 2:
            return
        from meridiana import roofs
        oid = purpose.partition(':')[2]
        if self.session.project.building(oid) is None:
            return
        try:
            bearing = roofs.axis_bearing(points[0], points[1])
        except ValueError as error:
            self.properties._refuse(str(error))
            return
        self.session.select('building', oid)
        self.properties.commit('saddles.direction', bearing)

    def edge_picked(self, purpose, kind, oid, side):
        building = self.session.project.building(oid)
        if kind != 'building' or building is None or side < 0:
            return
        self.session.select(kind, oid)
        if purpose == 'eave':
            self.properties.commit('roof.eave_side', side + 1)
        elif purpose == 'gable':
            value = 'gable' if building.sides_kind()[side] == 'eave' else 'eave'
            self.properties.commit(f'edge.{side}', value)
        elif purpose.startswith('free_eave:'):
            self.properties.commit(f'free.{int(purpose.split(":")[1])}.eave_side', side + 1)

    def close(self):
        if self.session_changed in self.session.listeners:
            self.session.listeners.remove(self.session_changed)
        for controller in (self.properties, self.checks, self.tree):
            controller.close()


def install(engine, session, cache, window):
    inspectors = Inspectors(engine, session, window)
    context = engine.rootContext()
    for name, controller in [('propertiesBackend', inspectors.properties), ('checksBackend', inspectors.checks),
                             ('projectTreeBackend', inspectors.tree), ('inspectors', inspectors)]:
        context.setContextProperty(name, controller)
    # The forms of the first building and sub-field built while the window is idle after the opening (R465); soon,
    # so that the first selection costs little even in the first second (R499: none over 100 ms).
    QTimer.singleShot(600, inspectors.properties.warmForms)
    return Part('inspectors', sources={'properties': QML / 'Properties/PropertiesHost.qml',
                                      'checks': QML / 'Checks/ChecksHost.qml',
                                      'project': QML / 'ProjectTree/ProjectTreeHost.qml'},
                controllers={'properties': inspectors.properties, 'checks': inspectors.checks,
                             'project_tree': inspectors.tree, 'inspectors': inspectors},
                bind=inspectors.bind, close=inspectors.close)
