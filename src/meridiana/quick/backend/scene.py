"""Native Quick 3D boundary: immutable scene data, coarse edits and the existing project session."""
from __future__ import annotations

import copy
import json
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from shapely.geometry import Point, Polygon

from meridiana import camera, hit3d, log, mesh, move, navigation, props, roof_vertices, sun, viewaids, view_colours
from meridiana.i18n import _, number
from meridiana.session import ProjectSession

from .scene_context import GHOST, IfcContext, ghost_ranges, members, reference
from .scene_geometry import DotGeometry, RibbonGeometry, SceneGeometry, instance_file
from .scene_slots import DecorationSlots

from . import models3d
from .models3d import ASSET_FOR_KIND      # R374: the kinds' models live in models3d (kept here for who imports it)


def navigation_styles():
    return {key: {**{k: [[sorted(b), sorted(m)] for b, m in getattr(style, k)]
                     for k in ('pan', 'orbit', 'zoom', 'select')},
                  **{k: getattr(style, k) for k in ('middle_click', 'middle_double', 'right_click')}}
            for key, style in navigation.STYLES.items()}


class SceneBackend(QObject):
    sceneChanged = Signal()
    selectionChanged = Signal()
    sunChanged = Signal()
    errorChanged = Signal()
    layoutRequested = Signal()
    commandRequested = Signal(str)
    hoverChanged = Signal()

    def __init__(self, session: ProjectSession, cache: Path, parent=None):
        super().__init__(parent)
        self.session, self.cache = session, Path(cache)
        self.geometry = SceneGeometry()
        self.geometry.setParent(self)
        # r21-ifc-vista: the true geometry of an imported IFC as context, its bodies faint
        self.ghost_geometry = SceneGeometry()
        self.ghost_geometry.setParent(self)
        self.context = IfcContext(self)
        self._context = []
        self.outline_geometry = RibbonGeometry()
        self.outline_geometry.setParent(self)
        # the strings and the optimizers in the Plant (R433, R456)
        self.string_geometry = RibbonGeometry()
        self.string_geometry.setParent(self)
        self.optimizer_geometry = RibbonGeometry()
        self.optimizer_geometry.setParent(self)
        self._phase, self._strings_shown, self._strings_key = '', False, None
        self.hover_geometry = RibbonGeometry()
        self.hover_geometry.setParent(self)
        self._hot_vertex = -1
        self.vertex_geometry = DotGeometry()
        self.vertex_geometry.setParent(self)
        self.selectionChanged.connect(self._vertex_marks)
        self._hover = ('', '', '')
        self._hover_data = {'edges': [], 'color': view_colours.HOVER}
        self._selection_colour = view_colours.SELECT
        self._handle_geometry = None
        self.rebuilds = 0
        self.calls = Counter()
        self.triangles = tuple(np.zeros((0, 3), np.float32) for _ in range(3))
        self._owners, self._hits = [], None
        self.module_table = np.zeros((0, 20), np.float32)
        self._modules = QUrl()
        self._bounds = {'centre': [0., 0., 0.], 'radius': 20., 'groundHalf': 100.}
        self._sun = {}
        self._error = ''
        self._handles, self._chosen = [], []
        self._segments = []
        self._edit = None
        self._trial = None
        self._transform = None
        self._transform_motion = (0., 0., 0.)
        self._gizmo = {'on': False, 'centre': [0., 0., 0.]}
        self._weld_from = None
        self._module_keys = []
        self._decorations = []
        self._asset_geometry = {}
        # R554: the decorative models as rows that stay, so their Models and shared meshes stay in the scene
        self.decoration_slots = DecorationSlots(self, QUrl.fromLocalFile(str(instance_file(self.cache, np.zeros((0, 20))))))
        self.asset_overrides = {}
        self.decorative_models = True
        self.session.subscribe(self._changed, at_once=True)     # R547: the modules shown as they are at once
        self._site = (session.project.site.lat, session.project.site.lon)
        self.designSun()
        self.rebuild()

    def close(self):
        if self._changed in self.session.listeners:
            self.session.listeners.remove(self._changed)

    @Property(QObject, constant=True)
    def buildingGeometry(self):
        self.calls['read:buildingGeometry'] += 1
        return self.geometry

    @Property(QObject, constant=True)
    def outlineGeometry(self):
        return self.outline_geometry

    stringsChanged = Signal()

    @Property(QObject, constant=True)
    def stringGeometry(self):
        return self.string_geometry

    @Property(QObject, constant=True)
    def optimizerGeometry(self):
        return self.optimizer_geometry

    @Property(bool, notify=stringsChanged)
    def stringsShown(self):
        return self._strings_shown

    @Slot(str)
    def setPhase(self, phase):
        """The strings are drawn in the Plant only (as on the plan)."""
        if phase != self._phase:
            self._phase = phase
            self._strings()

    def _strings(self):
        import json
        p = self.session.project
        results = self.session.good_results()
        if self._phase != 'plant':
            shown = False
        else:
            s = (p.energy or {}).get('strings') or {}
            key = (json.dumps(s, sort_keys=True, default=str), tuple(sorted((k, id(v)) for k, v in results.items())),
                   json.dumps([e.get('optimizer') is not None for e in (p.energy or {}).get('inverters') or []]))
            if key != self._strings_key:
                self._strings_key = key
                lines, crosses = viewaids.string_segments(p, results)
                self.string_geometry.set_segments(lines)
                self.optimizer_geometry.set_segments(crosses)
                self._string_count = len(lines) + len(crosses)
            shown = bool(getattr(self, '_string_count', 0))
        if shown != self._strings_shown:
            self._strings_shown = shown
            self.stringsChanged.emit()

    @Property(str, notify=selectionChanged)
    def selectionColor(self):
        return self._selection_colour

    @Property('QVariantMap', constant=True)
    def handleGeometry(self):
        if self._handle_geometry is None:
            from meridiana import gizmo
            halo, (radius, width, thick) = mesh.GIZMO_HALO, mesh.GIZMO_RING
            shapes = dict(pivot=mesh.rings(.18, mesh.rgb(view_colours.D3['pivot'])),
                          pivotHalo=mesh.ring_bands(.8, mesh.rgb(view_colours.D3['pivot_halo'])),
                          x=mesh.arrow(gizmo.EAST), y=mesh.arrow(gizmo.NORTH), z=mesh.arrow(gizmo.UP),
                          xy=mesh.square(*mesh.GIZMO_PLANE), rz=mesh.annulus(radius,width,thick),
                          xHalo=mesh.arrow(gizmo.EAST,halo), yHalo=mesh.arrow(gizmo.NORTH,halo),
                          rzHalo=mesh.annulus(radius,width+halo,thick+halo/2))
            self._handle_geometry = {}
            for key, shape in shapes.items():
                geometry = SceneGeometry()
                geometry.setParent(self)
                geometry.set_mesh(*shape)
                self._handle_geometry[key] = geometry
        return self._handle_geometry

    @Property(QUrl, notify=sceneChanged)
    def modulesSource(self):
        self.calls['read:modulesSource'] += 1
        return self._modules

    @Property(int, notify=sceneChanged)
    def moduleCount(self):
        self.calls['read:moduleCount'] += 1
        return len(self.module_table)

    @Property('QVariantMap', notify=sceneChanged)
    def bounds(self):
        self.calls['read:bounds'] += 1
        return self._bounds

    @Property(QObject, constant=True)
    def ghostGeometry(self):
        return self.ghost_geometry

    @Property(float, constant=True)
    def ghostOpacity(self):
        return GHOST

    @Property('QVariantList', notify=sceneChanged)
    def contextModels(self):
        return self._context

    @Property('QVariantList', notify=sceneChanged)
    def decorations(self):
        self.calls['read:decorations'] += 1
        return self._decorations

    @Property(QObject, constant=True)
    def decorationSlots(self):
        """R554: what the 3D view draws the decorations with (scene_slots.DecorationSlots)."""
        return self.decoration_slots

    @Property('QVariantMap', constant=True)
    def navigationStyles(self):
        self.calls['read:navigationStyles'] += 1
        return navigation_styles()

    @Property('QVariantMap', constant=True)
    def sceneColors(self):
        self.calls['read:sceneColors'] += 1
        return view_colours.D3

    @Property('QVariantMap', notify=sunChanged)
    def sunData(self):
        self.calls['read:sunData'] += 1
        return self._sun

    @Property('QVariantList', notify=selectionChanged)
    def vertices(self):
        self.calls['read:vertices'] += 1
        return [{'point': list(mesh.to_qt(h.x, h.y, h.z)), 'selected': i in self._chosen}
                for i, h in enumerate(self._handles)]

    # The nested lists as one string: a QVariantList of lists or maps is fetched again from Python for every element
    # QML touches (129 reads of selectionEdges for one row, 06/11/2026, R465); a string crosses once.
    @Property(str, notify=selectionChanged)
    def verticesJson(self):
        return json.dumps(self.vertices)

    @Property(str, notify=selectionChanged)
    def selectionEdgesJson(self):
        return json.dumps(self._segments)

    @Property(str, notify=hoverChanged)
    def hoverDataJson(self):
        return json.dumps(self._hover_data)

    @Property(QObject, constant=True)
    def hoverGeometry(self):
        return self.hover_geometry

    @Property(QObject, constant=True)
    def vertexGeometry(self):
        return self.vertex_geometry

    def _vertex_marks(self):
        """The corners as ui/view3d.py vertexMarks: white, the chosen in the selection's colour, a dark edge."""
        rgb = lambda name: mesh.rgb(view_colours.D3[name])
        marks = view_colours.VERTEX_MARK

        def state(i):
            return 'on' if i in self._chosen else 'hot' if i == self._hot_vertex else 'idle'
        names = {'on': 'vertex_on', 'hot': 'vertex_hot', 'idle': 'vertex'}
        self.vertex_geometry.set_dots([(mesh.to_qt(h.x, h.y, h.z), marks[state(i)], rgb(names[state(i)]), rgb('vertex_edge'))
                                       for i, h in enumerate(self._handles)])

    @Slot(int)
    def hoverVertex(self, index):
        """The corner under the resting pointer, a little larger and yellow; Python only when it changes."""
        if index != self._hot_vertex:
            self._hot_vertex = index
            self._vertex_marks()

    @Property('QVariantMap', constant=True)
    def viewTips(self):
        return dict(fit=_('Fit'), zoomIn=_('Zoom in'), zoomOut=_('Zoom out'))

    @Property('QVariantMap', constant=True)
    def overlayColors(self):
        """What the scene writes over itself (the corner's field, the sign of Ctrl) in the plan's colours (R534)."""
        if not hasattr(self, '_overlay_colors'):
            from meridiana import theme_colors
            self._overlay_colors = {k: theme_colors.qt_hex(v) for k, v in view_colours.PHOTO.items()}
        return self._overlay_colors

    @Property('QVariantMap', constant=True)
    def vertexFieldText(self):
        """The word before the corner's value: what it is (R534, Daniel: the field said 11,66 and nothing else)."""
        return dict(height=_('Height above the ground'), heights=_('Height above the ground of {n} corners'),
                    shift=_('Raise or lower by'))

    @Property(str, constant=True)
    def vertexHelp(self):
        return _('Corner: drag it up or down, click to write its height. Ctrl: more than one. Right button: what else it can do.')

    @Property('QVariantMap', notify=hoverChanged)
    def hoverData(self):
        return self._hover_data

    @Slot(str, int, float, float, float)
    def hover(self, name, index, x, y, z):
        """Update only when the resting pointer crosses an object, never during orbit."""
        self.calls['hover'] += 1
        if name == 'modules' and 0 <= index < len(self._module_keys):
            sfid, key = self._module_keys[index]
            target = ('module', sfid, key)
        elif name.startswith('prop:'):
            ids = next((d['ids'] for d in self._decorations if d['name'] == name), [])
            target = ('prop', ids[index], '') if 0 <= index < len(ids) else ('', '', '')
        else:
            target = self._point_target(name, x, y, z) if name else ('', '', '')
        if target == self._hover:
            return
        self._hover = target
        kind, oid, key = target
        segments = viewaids.outline(self.session.project, self.session.good_results(), kind, oid, key)
        self.hover_geometry.set_segments(segments)
        self._hover_data = {'edges': np.asarray(segments).reshape(-1, 2, 3).tolist(),
                            'color': view_colours.kind_colour(kind, hover=True)}
        self.hoverChanged.emit()

    @Slot(str, float, float)
    def placePreview(self, kind, east, north):
        """R554: where the object of the tool «3D object» would go from the 3D view, its box at the plan's point
        (the plan's own rules: on the roof under the point, else on the ground), drawn as the outline under the
        pointer; an empty `kind` takes it away."""
        if not kind or kind in props.PATH_KINDS:
            if self._hover[0] == 'preview':
                self.hover('', -1, 0, 0, 0)
            return
        from meridiana import model as core
        p = self.session.project
        try:
            probe = core.Prop(id='', kind=kind, at=[east, north], building=p.prop_host((east, north)))
            ring, base, top = probe.footprint(), p.prop_base(probe), probe.measures()['height']
        except (ValueError, KeyError):
            return
        segments = []
        for (ax, ay), (bx, by) in zip(ring, list(ring[1:]) + list(ring[:1])):
            if (ax, ay) == (bx, by):
                continue
            for za, zb in ((base, base), (base + top, base + top)):
                segments.append((mesh.to_qt(ax, ay, za), mesh.to_qt(bx, by, zb)))
            segments.append((mesh.to_qt(ax, ay, base), mesh.to_qt(ax, ay, base + top)))
        segments = np.asarray(segments, dtype=float).reshape(-1, 2, 3)
        self._hover = ('preview', kind, f'{east:.3f},{north:.3f}')
        self.hover_geometry.set_segments(segments)
        self._hover_data = {'edges': segments.tolist(), 'color': view_colours.kind_colour('prop', hover=True)}
        self.hoverChanged.emit()

    @Property('QVariantList', notify=selectionChanged)
    def selectionEdges(self):
        self.calls['read:selectionEdges'] += 1
        return self._segments

    @Property('QVariantMap', notify=selectionChanged)
    def gizmo(self):
        self.calls['read:gizmo'] += 1
        return self._gizmo

    @Property(str, notify=errorChanged)
    def error(self):
        self.calls['read:error'] += 1
        return self._error

    @Property('QVariantList', notify=selectionChanged)
    def contextActions(self):
        """The same object menu as MainWindow.context_actions, using core edits."""
        from meridiana import manual
        kind, oid = self.session.selection
        sfid, key = self.session.selected_module
        out = [('properties', _('Properties')), ('frame', _('Frame it'))]
        if kind == 'row' or (kind == 'subfield' and key):
            sfid = oid.partition('/')[0] if kind == 'row' else oid
            result = self.session.good_results().get(sfid)
            rid = oid.partition('/')[2] if kind == 'row' else manual.row_of(result, key)
            row = next((r for r in getattr(result, 'rows', []) if r.id == rid), None)
            if row is not None:
                out.append(('', ''))
                if kind != 'row':
                    out.append(('select_row', _('Select the row')))
                out += [('remove_row', _('Take the row away')), ('append', _('Add a row at the back')),
                        ('resize_row', _('Shorten or lengthen…'))]
                out.append(('explode_row', _('Explode the row')) if row.count > 1 else ('turn_row', _('Turn by 90°')))
                out.append(('', ''))
        if kind == 'subfield':
            sf = next((s for s in self.session.project.subfields if s.id == oid), None)
            if key:
                out.append(('delete', _('Take this module out')))
            if sf is not None:
                out.append(('relayout' if sf.manual else 'fill', _('Lay again automatically') if sf.manual else
                            _('Lay again') if sf.filled else _('Lay the modules')))
                if sf.filled:
                    out += [('explode', _('Explode the rows')), ('empty', _('Take the modules out'))]
        if kind == 'building':
            out.append(('subfields', _('A sub-field on each pitch')))
        if kind in ('building','subfield','exclusion','prop'):
            out.append(('', ''))
            if kind in ('building','subfield'):
                out.append(('rename', _('Rename…')))
            out.append(('duplicate', _('Duplicate')))
            if kind != 'prop':
                out.append(('square', _('Square the corners')))
            out += [('', ''), ('delete', _('Delete'))]
        return [dict(key=key, text=text) for key, text in out]

    @Property(str, notify=selectionChanged)
    def selectionName(self):
        kind, oid = self.session.selection
        if kind == 'building':
            return self.session.project.building(oid).name
        if kind == 'subfield':
            return next((s.name for s in self.session.project.subfields if s.id == oid), '')
        return ''

    @Slot(result='QVariantMap')
    def frameBounds(self):
        """MainWindow._fit: the selected footprint about its roof base."""
        p = self.session.project
        kind, oid = self.session.selection
        thing = viewaids._thing(p, kind, oid)
        if kind == 'pitch':
            bid, _sep, index = oid.partition(':')
            building = p.building(bid)
            pitches = building.pitches() if building else []
            ring = pitches[int(index)].ring if index.isdigit() and int(index) < len(pitches) else []
        elif thing is not None:
            ring = viewaids._ring(thing, kind)
        else:
            return self._bounds
        ring = np.asarray(ring, dtype=float)
        if not len(ring):
            return self._bounds
        x, y = ring.mean(axis=0)
        building = thing if kind == 'building' else p.building(thing.building) if kind == 'subfield' else None
        z = p.prop_base(thing) if kind == 'prop' else building.height if building else 0.
        # R554: plain floats; numpy's reached QML as '' and the 3D view framed the origin instead of the object
        return {'centre': [float(v) for v in mesh.to_qt(x, y, z)], 'radius': float(np.ptp(ring, axis=0).max() * .6 + 2)}

    @Property('QVariantList', notify=selectionChanged)
    def selectionCentre(self):
        return self.frameBounds()['centre'] if self.session.selection[0] in ('building','pitch','subfield','exclusion','prop') else []

    @Slot(str, str)
    def contextCommand(self, command, value=''):
        from meridiana import manual
        from .plan_edit import PlanEditor
        kind, oid = self.session.selection
        editor = PlanEditor(self.session)
        editor.set_results(self.session.good_results())
        try:
            if command in ('properties','frame','resize_row'):
                if command == 'resize_row':
                    self.contextCommand('select_row', '')
                self.commandRequested.emit(command)
            elif command == 'rename' and value.strip() and kind in ('building','subfield'):
                def rename(p):
                    thing = p.building(oid) if kind == 'building' else next(s for s in p.subfields if s.id == oid)
                    thing.name = value.strip()
                self.session.edit(_('Rename'), rename)
            elif command == 'duplicate':
                made = []
                self.session.edit(_('Duplicate'), lambda p: made.append(p.duplicate(kind,oid)))
                self.session.select(kind, made[0])
            elif command == 'delete':
                editor._delete()
            elif command == 'square':
                editor.apply_command({'type':'square'})
            elif command == 'subfields':
                for pitch in self.session.project.building(oid).pitches():
                    if Polygon(pitch.ring).area >= .5:
                        editor.apply_command({'type':'polygon', 'tool':'subfield', 'ring':[list(p) for p in pitch.ring]})
            elif command in ('fill','empty','relayout') and kind == 'subfield':
                def fill(p):
                    sf=next(s for s in p.subfields if s.id==oid)
                    sf.filled=command != 'empty'
                    if command == 'fill' and not sf.manual:
                        sf.removed=[]
                change = manual.relayout(self.session.project, oid) if command == 'relayout' else fill
                self.session.edit(_('Lay the modules') if command != 'empty' else _('Take the modules out'), change)
            elif command in ('select_row','remove_row','append','explode_row','turn_row'):
                sfid, key = self.session.selected_module
                if kind == 'row':
                    sfid, _sep, rid = oid.partition('/')
                else:
                    rid = manual.row_of(self.session.good_results().get(sfid),key)
                if command == 'select_row':
                    self.session.select('row',f'{sfid}/{rid}')
                else:
                    fn={'remove_row':manual.remove,'append':manual.append,'explode_row':manual.explode,'turn_row':manual.turn}[command]
                    change=fn(self.session.project,sfid,rid,self.session.good_results().get(sfid))
                    self.session.edit(_('Change a row'),change)
            elif command == 'explode':
                self.session.edit(_('Explode the rows'), manual.explode(self.session.project,oid,None,self.session.good_results().get(oid)))
            if editor.last_error:
                self._say(editor.last_error)
            else:
                self._say()
        except (ValueError, KeyError, StopIteration) as error:
            self._say(error)

    def _say(self, error=''):
        self._error = str(error)
        self.errorChanged.emit()

    def _changed(self, topics):
        if {'project:site', 'file', 'restored'} & topics:
            site = self.session.project.site
            if (site.lat, site.lon) != self._site:
                self._site = (site.lat, site.lon)
                self.designSun()
            else:
                s = self._sun
                self.setSun(s['year'], s['month'], s['day'], s['hour'])
        if {'restored', 'file', 'project:geometry', 'project:subfields', 'project:variants'} & topics:
            self._edit = self._trial = self._transform = None
            self._chosen = []
            self.rebuild()
        elif any(t.startswith('layout:') for t in topics):
            self.rebuild()
        if self._phase == 'plant' and ({'energy', 'file', 'restored'} & topics
                                       or any(t.startswith(('layout:', 'project:')) for t in topics)):
            self._strings()
        if 'selection' in topics:
            self._chosen = []
            if self._edit is not None or self._transform is not None or self._weld_from is not None:
                self.cancelEdit()
            else:
                self._selection()

    def rebuild(self, project=None):
        self.hover('', -1, 0, 0, 0)
        p = project or self.session.project
        results = self.session.good_results()
        visual = self._decorated(p) if self.decorative_models else p
        if not self.decorative_models:
            self._decorations = []
        self.decoration_slots.show(self._decorations)
        self._owners, self._hits = [], None
        self.triangles, self.module_table, _ = mesh.project_scene(visual, results, owners=self._owners)
        self._module_keys = [(sf.id, m.key) for sf in p.subfields if sf.filled
                             for m in getattr(results.get(sf.id), 'modules', [])]
        if project is not None and self._transform is not None:
            kind, oid = self._transform[1]
            centre = self._transform[2]
            east, north, degrees = self._transform_motion
            angle = np.radians(degrees)
            co, si = np.cos(angle), np.sin(angle)
            rotation = np.array([[co, 0, si], [0, 1, 0], [-si, 0, co]])
            pivot = np.asarray(mesh.to_qt(*centre, 0))
            original = self.session.project
            affected = {sf.id for sf in original.subfields
                        if (kind == 'building' and sf.building == oid) or (kind == 'subfield' and sf.id == oid)}
            row_sf, _, row_id = oid.partition('/') if kind == 'row' else ('', '', '')
            row_keys = {m.key for m in getattr(results.get(row_sf), 'modules', []) if m.rid == row_id}
            for i, (sfid, key) in enumerate(self._module_keys):
                if sfid in affected or (sfid == row_sf and key in row_keys):
                    matrix = self.module_table[i, :12].reshape(3, 4)
                    matrix[:, 3] = rotation @ (matrix[:, 3]-pivot)+pivot+mesh.to_qt(east,north,0)
                    matrix[:, :3] = rotation @ matrix[:, :3]
        self._context = self.context.entries(p)
        self._upload_bodies(p)
        self._modules = QUrl.fromLocalFile(str(instance_file(self.cache, self.module_table)))
        positions = self.triangles[0]
        if len(self.module_table):
            transforms = self.module_table[:, :12].reshape(-1, 3, 4)
            centres = transforms[:, :, 3]
            half = np.abs(transforms[:, :, :3]).sum(axis=2) * 50
            positions = np.concatenate((positions, centres-half, centres+half))
        if self._decorations:
            corners = np.asarray([q for group in self._decorations for q in group['bounds']], np.float32)
            positions = np.concatenate((positions, corners))
        if self._context:
            corners = np.asarray([q for piece in self._context for q in piece['bounds']], np.float32)
            positions = np.concatenate((positions, corners))
        if len(positions):
            low, high = positions.min(0), positions.max(0)
            self._bounds = {'centre': ((low + high) / 2).tolist(),
                            'radius': float(np.linalg.norm(high - low) / 2 + 2),
                            'groundHalf': max(100., float(max(high[0]-low[0], high[2]-low[2]) / 2 + 60))}
        else:
            self._bounds = {'centre': [0., 0., 0.], 'radius': 20., 'groundHalf': 100.}
        self.rebuilds += 1
        self._selection(p)
        self.sceneChanged.emit()

    def _upload_bodies(self, project):
        """The bodies to the GPU: with an IFC context, the import's bodies go to the faint geometry (still picked)."""
        ranges = ghost_ranges(self._owners, members(project, reference(project))) if self._context else []
        if not ranges:
            self.geometry.set_mesh(*self.triangles)
            self.ghost_geometry.set_mesh(*(a[:0] for a in self.triangles))
            return
        faint = np.zeros(len(self.triangles[0]) // 3, bool)
        for first, n in ranges:
            faint[first:first + n] = True
        faint = np.repeat(faint, 3)
        self.geometry.set_mesh(*(a[~faint] for a in self.triangles))
        self.ghost_geometry.set_mesh(*(a[faint] for a in self.triangles))

    def _decorated(self, project):
        """Replace only visual props. The original project and shadow_solid never see an asset key."""
        from .scene_assets import load_model
        visual = copy.copy(project)
        visual.props = []
        groups = {}
        for prop in project.props:
            key = self.asset_overrides.get(prop.id) or models3d.asset_for(prop)
            if key is None or (prop.path is not None and prop.kind != 'fence'):
                visual.props.append(prop)
                continue
            p, n, c = load_model(key)
            if key not in self._asset_geometry:
                geometry = SceneGeometry()
                geometry.setParent(self)
                geometry.set_mesh(p, n, c, indexed=True)
                self._asset_geometry[key] = geometry
            low, high = p.min(0), p.max(0)
            extents = np.maximum(high-low, 1e-6)
            dims = prop.measures()
            z0 = project.prop_base(prop)
            if prop.path is not None:
                # R374: the fence along its path, one copy of the model per FENCE_MODULE metres of each segment,
                # scaled along it to fit the segment whole (the model's length is its local X, as the core's)
                placements = []
                for (ax, ay), (bx, by) in zip(prop.path, prop.path[1:]):
                    run = float(np.hypot(bx - ax, by - ay))
                    if run < 1e-6:
                        continue
                    pieces = max(1, round(run / props.FENCE_MODULE))
                    scale = np.asarray([run / pieces, dims['height'], dims['width']]) / extents
                    bearing = float(np.degrees(np.arctan2(by - ay, bx - ax)))
                    for i in range(pieces):
                        t = (i + .5) / pieces
                        placements.append((bearing, scale, np.eye(3), (ax + (bx - ax) * t, ay + (by - ay) * t)))
            # People retain native proportions and the common standing/walking scale.
            elif props.family(prop.kind) == 'person':
                placements = [(prop.rotation, np.repeat(dims['height'], 3), np.eye(3), prop.at)]
            elif props.family(prop.kind) == 'car':
                # Downloaded vehicles face local Z; the core's length is local East (X).
                scale = np.asarray([dims['width'], dims['height'], dims['length']]) / extents
                placements = [(prop.rotation, scale, np.array([[0., 0., 1.], [0., 1., 0.], [-1., 0., 0.]]), prop.at)]
            else:
                xsize, zsize = props.plan_size(prop.kind, prop.height, prop.width, prop.length)
                placements = [(prop.rotation, np.asarray([xsize, dims['height'], zsize]) / extents, np.eye(3), prop.at)]
            group = groups.setdefault(key, {'table': [], 'ids': [], 'bounds': []})
            for rotation, scale, axes, at in placements:
                angle = np.radians(rotation)
                co, si = np.cos(angle), np.sin(angle)
                transform = np.array([[co, 0, si], [0, 1, 0], [-si, 0, co]]) @ axes @ np.diag(scale)
                offset = np.asarray(mesh.to_qt(float(at[0]), float(at[1]), z0))
                entry = np.zeros(20, np.float32)
                entry[:12] = np.column_stack((transform, offset)).reshape(-1)
                entry[12:16] = 1
                group['table'].append(entry); group['ids'].append(prop.id)
                corners = np.array([[x,y,z] for x in (low[0],high[0]) for y in (low[1],high[1])
                                    for z in (low[2],high[2])]) @ transform.T + offset
                group['bounds'].extend(corners.tolist())
        self._decorations = [{'name': 'prop:'+key, 'key': key, 'geometry': self._asset_geometry[key],
                              'source': QUrl.fromLocalFile(str(instance_file(self.cache, np.asarray(g['table'])))),
                              'ids': g['ids'], 'count': len(g['ids']), 'bounds': g['bounds']}
                             for key, g in groups.items()]
        return visual

    def _selection(self, project=None):
        p = project or self.session.project
        kind, oid = self.session.selection
        self._handles = roof_vertices.handles_of(p, kind, oid)
        sfid, key = self.session.selected_module
        if sfid:
            segments = viewaids.outline(p, self.session.good_results(), 'module', sfid, key)
        elif kind != 'site':
            segments = viewaids.outline(p, self.session.good_results(), kind, oid)
        else:
            segments = np.zeros((0, 2, 3))
        self._segments = np.asarray(segments).reshape(-1, 2, 3).tolist()
        self.outline_geometry.set_segments(segments)
        self._selection_colour = view_colours.kind_colour('module' if sfid else kind)
        centre = move.centre(p, kind, oid) if kind in move.KINDS else None
        self._gizmo = {'on': centre is not None,
                       'centre': list(mesh.to_qt(*centre, move.height(p, kind, oid, centre))) if centre else [0., 0., 0.]}
        self.selectionChanged.emit()

    @Slot(int, int, int, float)
    def setSun(self, year, month, day, hour):
        self.calls['sun'] += 1
        try:
            minutes = min(1430, max(0, round(hour * 6) * 10))
            h = minutes / 60
            when = datetime(year, month, day, tzinfo=ZoneInfo('Europe/Rome')) + timedelta(minutes=minutes)
            pos = sun.position(self.session.project.site.lat, self.session.project.site.lon, when)
        except (ValueError, OverflowError) as error:
            self._say(error)
            return
        clock = when.strftime('%H:%M')
        legal = _('summer time') if when.dst() else _('standard time')
        if pos.apparent <= 0:
            short = _('sun below the horizon')
            description = _('At {time} ({clock}) the sun is below the horizon.').format(time=clock, clock=legal)
        else:
            values = dict(elevation=number(pos.apparent, 1), azimuth=number(pos.azimuth, 1, sign=True))
            short = _('h {elevation}° · az {azimuth}°').format(**values)
            description = _('At {time} ({clock}) the sun is {elevation}° above the horizon, azimuth {azimuth}° '
                            '(from South, + West).').format(time=clock, clock=legal, **values)
        self._sun = {'elevation': pos.apparent, 'bearing': pos.bearing, 'hour': h,
                     'year': year, 'month': month, 'day': day, 'clock': clock,
                     'short': short, 'description': description}
        self._say()
        self.sunChanged.emit()

    @Slot()
    def designSun(self):
        """SunBar.to_design_day, on the same ten-minute clock grid."""
        window = sun.DesignWindow(**self.session.project.sun_window)
        d = date(2026, window.month, window.day)
        noon = sun.utc_at_solar_time(self.session.project.site.lon, d, 12).astimezone(ZoneInfo('Europe/Rome'))
        self.setSun(d.year, d.month, d.day, round((noon.hour * 60 + noon.minute) / 10) / 6)

    @Slot(int)
    def shiftSunDay(self, days):
        s = self._sun
        d = date(s['year'], s['month'], s['day']) + timedelta(days=days)
        self.setSun(d.year, d.month, d.day, s['hour'])

    @Slot(bool)
    def playSun(self, playing):
        if playing and self._sun['elevation'] <= 0:
            self._sunrise()

    @Slot()
    def stepSun(self):
        s = self._sun
        self.setSun(s['year'], s['month'], s['day'], ((round(s['hour'] * 6) + 1) % 144) / 6)
        if self._sun['elevation'] <= 0:
            self._sunrise()

    def _sunrise(self):
        s, site = self._sun, self.session.project.site
        day = datetime(s['year'], s['month'], s['day'], tzinfo=ZoneInfo('Europe/Rome'))
        for step in range(144):
            if sun.position(site.lat, site.lon, day + timedelta(minutes=step * 10)).apparent > 0:
                break
        self.setSun(s['year'], s['month'], s['day'], step / 6)

    @Slot(str, int, float, float, float)
    def pick(self, name, index, x, y, z):
        self.calls['pick'] += 1
        if name == 'modules' and 0 <= index < len(self._module_keys):
            sfid, key = self._module_keys[index]
            self._pick_module(sfid, key)
            return
        if name.startswith('prop:'):
            ids = next((d['ids'] for d in self._decorations if d['name'] == name), [])
            if 0 <= index < len(ids):
                self.session.select('prop', ids[index])
                return
        kind, oid, key = self._point_target(name, x, y, z) if name else ('site', '', '')
        if kind == 'module':
            self._pick_module(oid, key)
        else:
            self.session.select(kind, oid)

    def _pick_module(self, sfid, key):
        """As the plan (R529): another click on the module selected takes its row; the row's next click takes a module.
        A click on another module of the row takes that module."""
        result = self.session.good_results().get(sfid)
        modules = getattr(result, 'modules', [])
        rid = next((m.rid for m in modules if m.key == key), '')
        if rid and tuple(self.session.selected_module) == (sfid, key) and self.session.selection == ('subfield', sfid):
            self.session.select('row', f'{sfid}/{rid}')
        else:
            self.session.select('subfield', sfid, (sfid, key))

    def _point_target(self, name, x, y, z):
        """What the ray met at (x, y, z), Qt axes (R488): the face it lies on says whose it is. A wall, a parapet,
        a canopy's column is the building's even under a sub-field as wide as its roof; a roof is its sub-field's
        (or its module's) only where the sub-field lies; an obstacle, an object, a support their own. A point on no
        face of the scene (another model's, or one a test wrote) goes to the plan under it, as before."""
        hit = self._hit_at(x, y, z) if name in ('buildings', 'buildingsFaint') else None
        if hit is None:
            return self._pick_point(x, -z, name in ('buildings', 'buildingsFaint'))
        part, oid, wall = hit
        if part in ('prop', 'exclusion'):
            return part, oid, ''
        if part == 'support':
            return 'subfield', oid, ''
        if part == 'building_part' or wall:
            return 'building', oid, ''
        return self._pick_point(x, -z, True, host=oid)

    def _hit_at(self, x, y, z):
        if self._hits is None:
            try:
                self._hits = hit3d.Hits(self.triangles[0], self._owners)
            except ValueError as error:
                log.complain('3D pick', error)
                self._hits = False
        return self._hits.at((x, y, z)) if self._hits else None

    def _pick_point(self, east, north, building_hit=False, host=None):
        """PlanView._pick priority, using core footprints, layout corners and roof pitches.

        The Widgets window promotes a picked pitch to its building. A wall hit
        gets its nearest outline within 0.5 m only when the plan found nothing.
        `host`, the building whose roof the ray met: only what lies on that roof, then the building itself.
        """
        if not np.isfinite([east, north]).all():
            return 'site', '', ''
        p, point = self.session.project, Point(east, north)
        on = (lambda obj: True) if host is None else (lambda obj: obj.building == host)
        for kind, objects, ring in (('prop', p.props if host is None else [], lambda a: a.footprint()),
                                    ('exclusion', p.exclusions, lambda a: a.ring)):
            for obj in reversed(objects):
                if on(obj) and Polygon(ring(obj)).covers(point):
                    return kind, obj.id, ''
        results = self.session.good_results()
        for sf in reversed(p.subfields):
            if sf.filled and on(sf):
                for module in getattr(results.get(sf.id), 'modules', []):
                    if Polygon(module.corners).covers(point):
                        return 'module', sf.id, module.key
        for sf in reversed(p.subfields):
            if on(sf) and Polygon(sf.ring).covers(point):
                return 'subfield', sf.id, ''
        if host is not None:
            return 'building', host, ''
        for building in reversed(p.buildings):
            if any(pitch.tilt > 0 and Polygon(pitch.ring).covers(point) for pitch in building.pitches()):
                return 'building', building.id, ''
        for building in reversed(p.buildings):
            if Polygon(building.footprint).covers(point):
                return 'building', building.id, ''
        if building_hit:
            best, found = 0.5, ''
            for building in p.buildings:
                distance = Polygon(building.footprint).boundary.distance(point)
                if distance <= best:
                    best, found = distance, building.id
            if found:
                return 'building', found, ''
        return 'site', '', ''

    @Slot(result=str)
    @Slot(bool, result=str)
    def escapeSelection(self, move_mode=False):
        """Consume one Esc level; QML clears local drags and leaves Move on the 'tool' result."""
        if any(value is not None for value in (self._edit, self._trial, self._transform, self._weld_from)):
            # Widgets' vertexLeft also releases the corners when their drag is cancelled.
            if self._edit is not None or self._weld_from is not None:
                self._chosen = []
            self.cancelEdit()
            return 'edit'
        if self._chosen:
            self._chosen = []
            self.selectionChanged.emit()
            return 'vertices'
        if move_mode:
            return 'tool'
        kind, oid = self.session.selection
        sfid, _key = self.session.selected_module
        if kind == 'row':
            target = ('subfield', oid.partition('/')[0])
        elif sfid:
            target = ('subfield', sfid)
        elif kind in ('subfield', 'exclusion', 'prop'):
            p = self.session.project
            things = {'subfield': p.subfields, 'exclusion': p.exclusions, 'prop': p.props}[kind]
            thing = next((obj for obj in things if obj.id == oid), None)
            target = ('building', thing.building) if thing is not None and thing.building else ('site', '')
        elif kind == 'pitch':
            target = ('building', oid.partition(':')[0])
        elif kind == 'building':
            target = ('site', '')
        else:
            return ''
        self.session.select(*target)
        return 'selection'

    @Slot(int, bool)
    @Slot(int, bool, bool)
    def beginVertex(self, index, additive=False, add=False):
        self.calls['begin'] += 1
        if not 0 <= index < len(self._handles):
            return
        if self._weld_from is not None:
            source, self._weld_from = self._weld_from, None
            target = self._handles[index].corners[0]
            bid = roof_vertices.owner_of(*self.session.selection)
            try:
                self.session.edit(_('Make corners one'), lambda p: roof_vertices.weld(p, bid, source, target))
            except ValueError as error:
                self._say(error)
            self.layoutRequested.emit()
            return
        if additive:                            # R529: Ctrl adds or takes away
            self._chosen = sorted(set(self._chosen) ^ {index})
        elif add:                               # Shift adds (R356)
            self._chosen = sorted(set(self._chosen) | {index})
        elif index not in self._chosen:
            self._chosen = [index]
        self._edit = (self.session.snapshot(), self.session.selection,
                      [self._handles[i] for i in self._chosen])
        self._say()
        self.selectionChanged.emit()

    def _put(self, project, delta):
        _snapshot, (kind, oid), handles = self._edit
        if not handles:
            return
        if handles[0].obstacle:
            roof_vertices.set_obstacle_height(project, oid, handles[0].z + delta)
        else:
            roof_vertices.set_heights(project, roof_vertices.owner_of(kind, oid),
                                     [(h.corners[0], h.z + delta) for h in handles])

    @Slot(float)
    def previewVertex(self, delta):
        self.calls['preview'] += 1
        if self._edit is None:
            return
        from meridiana.model import Project
        trial = Project.from_json(copy.deepcopy(self._edit[0]), check=False)
        try:
            self._put(trial, delta)
        except ValueError as error:
            self._say(error)
            return
        self._trial = trial
        self.rebuild(trial)
        self._say()

    @Slot(float)
    def commitVertex(self, delta):
        self.calls['commit'] += 1
        if self._edit is None:
            return
        try:
            self.session.edit(_('Height of a corner'), lambda p: self._put(p, delta))
        except ValueError as error:
            self._say(error)
        finally:
            self._edit = self._trial = None
            self.rebuild()
        self.layoutRequested.emit()

    @Slot()
    def cancelEdit(self):
        self._edit = self._trial = self._transform = self._weld_from = None
        self.rebuild()

    @Slot('QVariantList', bool)
    @Slot('QVariantList', bool, bool)
    def selectVertices(self, indices, remove=False, again=False):
        """R529: the corners of a window; `again` (a plain window) starts the selection again, `remove` (Ctrl) takes
        them away, else they are added."""
        valid = {int(i) for i in indices if 0 <= int(i) < len(self._handles)}
        self._chosen = sorted(set(self._chosen) - valid if remove else valid if again else set(self._chosen) | valid)
        self.selectionChanged.emit()

    @Slot(str)
    def vertexAction(self, action):
        if not self._chosen:
            return
        kind, oid = self.session.selection
        bid = roof_vertices.owner_of(kind, oid)
        hand = self._handles[self._chosen[0]]
        corner = hand.corners[0]
        if action == 'all':
            self.selectVertices(list(range(len(self._handles))), False)
            return
        if hand.obstacle or hand.base:          # an obstacle's top, a body's base: they move whole
            return
        if action == 'weld':
            self._weld_from = corner
            return
        functions = {'pitched': lambda p: roof_vertices.to_manual(p, p.building(bid)),
                     'detach': lambda p: roof_vertices.detach(p, bid, corner),
                     'unfold': lambda p: roof_vertices.unfold(p, bid, corner)}
        if action in functions:
            try:
                self.session.edit(_('Edit roof corners'), functions[action])
            except ValueError as error:
                self._say(error)
            self.layoutRequested.emit()

    @Slot()
    def beginTransform(self):
        if self._gizmo['on']:
            self._transform = (self.session.snapshot(), self.session.selection,
                               move.centre(self.session.project, *self.session.selection))

    def _transform_change(self, project, east, north, degrees, duplicate=False):
        _snapshot, (kind, oid), centre = self._transform
        if duplicate:
            return move.copy(project, kind, oid, east, north, centre, degrees)
        if degrees:
            return move.rotate(project, kind, oid, *centre, degrees)
        return move.translate(project, kind, oid, east, north)

    @Slot(float, float, float)
    def previewTransform(self, east, north, degrees):
        self.calls['transformPreview'] += 1
        if self._transform is None:
            return
        from meridiana.model import Project
        trial = Project.from_json(copy.deepcopy(self._transform[0]), check=False)
        try:
            self._transform_change(trial, east, north, degrees)(trial)
        except ValueError as error:
            self._say(error)
            return
        self._trial = trial
        self._transform_motion = (east, north, degrees)
        self.rebuild(trial)
        self._say()

    @Slot(float, float, float, bool)
    def commitTransform(self, east, north, degrees, duplicate=False):
        if self._transform is None:
            return
        try:
            change = self._transform_change(self.session.project, east, north, degrees, duplicate)
            self.session.edit(_('Move and rotate'), change)
        except ValueError as error:
            self._say(error)
        finally:
            self._transform = self._trial = None
            self.rebuild()
        self.layoutRequested.emit()

    @Slot(str, str)
    def transformTyped(self, handle, text):
        value = move.parse(text)
        if value is None:
            self._say(_('Write a number'))
            return
        self.beginTransform()
        self.commitTransform(value if handle == 'x' else 0., value if handle == 'y' else 0.,
                             value if handle == 'rz' else 0., False)

    @Slot(float, float)
    def nudge(self, east, north):
        self.beginTransform()
        self.commitTransform(east, north, 0., False)

    @Slot(str)
    def vertexHeight(self, text):
        written = roof_vertices.parse_height(text)
        if written is None or not self._edit or not self._edit[2]:
            self._say(_('Write a height, or +5 or -10 to move it by that much'))
            return
        _snapshot, (kind, oid), handles = self._edit
        def change(project):
            if handles[0].obstacle:
                roof_vertices.set_obstacle_height(project, oid, roof_vertices.height_written(handles[0].z, written))
            else:
                roof_vertices.set_heights(project, roof_vertices.owner_of(kind, oid),
                    [(h.corners[0], roof_vertices.height_written(h.z, written)) for h in handles])
        try:
            self.session.edit(_('Height of a corner'), change)
        except ValueError as error:
            self._say(error)
        finally:
            self._edit = self._trial = None
            self.rebuild()
        self.layoutRequested.emit()

    @Slot()
    def undo(self):
        if self._edit is not None:
            self.cancelEdit()
        self.session.undo.undo()

    @Slot()
    def redo(self):
        self.session.undo.redo()

    def initial_camera(self, width=800, height=600):
        cam = camera.Camera()
        cam.fit(self._bounds['centre'], self._bounds['radius'], width / max(height, 1))
        return {'position': cam.position.tolist(), 'rotation': cam.rotation.tolist(),
                'target': cam.target.tolist(), 'fov': cam.fov, 'ortho': cam.ortho}
