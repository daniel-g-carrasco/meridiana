"""Coarse Qt boundary for the pure plan machines and the shared project session."""
from __future__ import annotations

import math
import re
import time
from collections import Counter
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, Property, Signal, Slot
from shapely.geometry import Polygon

from meridiana import config, geo, model, move, navigation, sides, theme_colors, view_colours
from meridiana.i18n import number
from meridiana.session import ProjectSession
from meridiana.snapping import Snapper

from .plan_edit import VERTEX_PX, PlanEditor, nearest_vertex
from .plan_locale import _
from .plan_collect import Collector
from .plan_place import Placer
from .plan_paths import drawing_bounds, register_paths
from .plan_scene import scene_of, side_labels
from .plan_tools import DrawingMachine
from .plan_shadow_job import ShadowScheduler

EDIT_TOOLS = {'select', 'move', 'rotate', 'string', 'draw_string', 'square', 'erase_string', 'erase_inverter_strings', 'erase_inverter',
              'paste', 'side'}


# the tools that place 3D objects at a point (R375); a click on an object already placed takes it (R554)
PLACE_TOOLS = ('prop', 'prop_group', 'prop_series', 'prop_line')


def modifiers(bits):
    return {name for bit, name in ((1, 'ctrl'), (2, 'shift'), (4, 'alt')) if bits & bit}


def qml_objects(items):
    result = []
    for item in items:
        row = dict(item)
        row['points'] = [QPointF(float(p[0]), float(p[1])) for p in row['points']]
        for field in ('fill', 'stroke'):
            value = row.get(field, '')
            if isinstance(value, str) and len(value) == 9 and value.startswith('#'):
                row[field] = theme_colors.qt_hex(value)
        result.append(row)
    return result


SCALE_SETTLE_MS = 300        # the strings' layers made again this long after the last zoom step (R541)

def _moved(before, after) -> bool:
    """R547: whether a module that is in both drawings is somewhere else (a layout that answers a change and moves
    modules: they fade in at their new place instead of jumping). Modules only taken out or added are not moved."""
    was = {(m['oid'], m['key']): m['points'][0] if m['points'] else None for m in before}
    return any(was.get((m['oid'], m['key']), at) != at
               for m in after for at in [m['points'][0] if m['points'] else None])


class PlanController(QObject):
    sceneChanged = Signal()
    modulesMoved = Signal()             # R547: a layout came back with modules in other places: they fade in there
    stateChanged = Signal()
    overlayChanged = Signal()
    cornersChanged = Signal()           # R356: the corners chosen of what is selected
    wiringChanged = Signal()            # the finished strings' layers (R496): only when they change
    draftChanged = Signal()             # the string being drawn by hand: at each module added
    bandChanged = Signal()              # the elastic band to the pointer: at each move
    unwiredChanged = Signal()           # the modules in no string: at each module the draft takes
    tipsChanged = Signal()
    navigationChanged = Signal()
    mapChanged = Signal()
    edgePicked = Signal(str, str, str, int)
    pointsPicked = Signal(str, 'QVariantList')
    alignRequested = Signal(float)
    shadowsChanged = Signal()
    markClicked = Signal(str, str)
    sourcesApplied = Signal(str, 'QVariantList')
    mapPreferencesChanged = Signal('QVariantMap')
    viewCommand = Signal(str)
    relayoutRequested = Signal(str, str)
    notice = Signal(str)            # a short sentence for the status bar (R487)
    placingChanged = Signal()       # R454: the «Place» mode of an imported IFC model began, ended, or its question
    placeAsked = Signal(str, str)   # the model falls on buildings already drawn: the window asks what to do
    coordinatesAsked = Signal()     # C while placing: the window of the coordinates
    modelImported = Signal('QVariantList')     # the ids of the bodies just laid

    def __init__(self, session=None, parent=None, *, cache=None, manage_layout=True):
        super().__init__(parent)
        self.session = session if isinstance(session, ProjectSession) else ProjectSession(session)
        self.editor = PlanEditor(self.session)
        self.overlayChanged.connect(self.cornersChanged)   # another thing selected: its corners, none chosen
        self.drawing = DrawingMachine(self.session.project)
        self.collector = Collector()
        self.placer = Placer()
        self.calls = Counter()
        self._tool, self._error = 'select', ''
        self._objects, self._modules = [], []
        self._highlights, self._wires, self._draft, self._labels, self._grips = [], [], [], [], []
        self._dots = []
        self._wire_quads = []
        self._wiring_seen = None            # the wiring scene's objects last split into layers (R496)
        self._wiring_finished, self._unwired = None, []
        self._draft_wires, self._draft_quads, self._draft_dots, self._draft_labels = [], [], [], []
        self._string_labels, self._band, self._draft_colour = [], [], ''
        self._wiring_level, self._module_size = 'near', 1.0
        self._string_states = {}            # run index -> "ok" / "check" / "fail", from the plant
        self._moving = False                # inside the pointer's move slot (R496)
        self._overlay_key = self._state_key = None
        self._module_highlights = []
        self._module_highlight_paths = []
        self._lit = []                      # the modules lit, and how: (keys, width, alpha)
        self._memo = {}                     # the overlay getters' answers, kept until the next _overlays (R465)
        self._optimizer_paths = []          # the optimizers' symbols and cables, as native paths (R424)
        self._module_tips, self._module_tip_default, self._module_tips_revision = {}, '', 0
        self._module_paths = {}             # (sub-field, key) -> its path, once per layout
        self._running = False
        self._marks = []
        self._shadows = []
        self.shadow_scheduler = ShadowScheduler(self.session, self)
        self.shadow_scheduler.ready.connect(self._shadows_ready)
        self.shadow_scheduler.failed.connect(self._layout_error)
        self._move_snapper = Snapper()
        self._bounds = [-20., -20., 40., 40.]
        self._side, self._side_value = None, ''
        self._mpp = .02
        self._maps = None
        self._source_editor = None
        self._nav = []
        self._closed = False
        self._context_side = None
        self._context_host = None
        self._view_bearing = 0.
        self._show_strings = False
        self._map_covering = None
        self._scale_settle = None
        from .plan_underlays import Underlays
        self._underlays = Underlays(self)
        self.scheduler = None
        if manage_layout:
            from .plan_jobs import LayoutScheduler
            self.scheduler = LayoutScheduler(self.session, self)
            self.scheduler.changed.connect(self.stateChanged)
            self.scheduler.failed.connect(self._layout_error)
        self.setNavigation('autocad')
        if cache is not None:
            from .plan_tiles import MapController
            site = self.session.project.site
            self._maps = MapController(Path(cache), origin=geo.Origin(site.lat, site.lon), offline=True)
            self._maps.configure(underlays=self.session.project.underlays)
            from .plan_sources import MapSourcesController
            self._source_editor = MapSourcesController(config.Config(), site=(site.lat, site.lon),
                                                       network=lambda: not self._maps.loader.offline, parent=self)
            self._source_editor.applied.connect(self._sources_applied)
        self.session.subscribe(self._changed, at_once=True)     # R547: the modules shown as they are at once
        self.refresh()

    def _layout_error(self, error):
        self._error = error
        self.stateChanged.emit()

    @Slot(QObject, str)
    def setGripCursor(self, item, kind):
        """Set a native cursor once on the GUI thread; Qt handles later pointer moves."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QCursor
        if kind == 'rotate':
            from meridiana.ui.plan import rotate_cursor
            item.setCursor(rotate_cursor())
        else:
            item.setCursor(QCursor(Qt.SizeAllCursor))

    def _shadows_ready(self, paths):
        self._shadows = paths
        self.shadowsChanged.emit()

    @Property('QVariantList', notify=shadowsChanged)
    def shadows(self):
        return self._shadows

    @Slot('QVariantMap')
    def setShadows(self, options):
        self.shadow_scheduler.request({k: float(v) for k, v in options.items()
                                       if k in ('azimuth', 'elevation', 'height')}
                                      if options.get('enabled', True) else None)

    @Property(bool, notify=stateChanged)
    def busy(self):
        return self.scheduler.busy if self.scheduler else False

    @Property(bool, notify=stateChanged)
    def hotGrip(self):
        return bool(self.editor.gesture and self.editor.gesture.grip)

    @Property('QVariantList', notify=overlayChanged)
    def transformGrips(self):
        if self._tool not in ('move', 'rotate') or not self.editor._movable():
            return []
        kind, oid = self.editor._target()
        if kind == 'module':
            sfid, _, key = oid.partition('/')
            module = next((m for m in self._scene['modules'] if (m['oid'], m['key']) == (sfid, key)), None)
            ring = [[x, -y] for x, y in module['points']] if module else []
            centre = tuple(map(lambda i: sum(p[i] for p in ring)/len(ring), (0, 1))) if ring else None
        else:
            rings = move.moving(self.session.project, kind, oid)
            ring = rings[0] if rings else []
            centre = move.centre(self.session.project, kind, oid)
        if not ring or centre is None:
            return []
        a, b = max(zip(ring, ring[1:] + ring[:1], strict=True), key=lambda s: (s[0][1]+s[1][1], -s[0][0]-s[1][0]))
        g = self.editor.gesture
        free = g is None or (g.mode == 'move' and g.base is None and not g.typing)
        return [dict(grip=name, x=p[0], y=p[1], free=free,
                     hot=bool(g and g.grip and (name == 'rotate') == (g.mode == 'rotate')))
                for name, p in [('move', centre), ('rotate', ((a[0]+b[0])/2, (a[1]+b[1])/2))]]

    @Property('QVariantList', constant=True)
    def compassPoints(self):
        return [_('N'), _('NE'), _('E'), _('SE'), _('S'), _('SW'), _('W'), _('NW')]

    @Property(str, constant=True)
    def compassText(self):
        return _('View orientation: {heading}. The arrow points to true North. Project azimuths: from South, positive '
                 'towards West, as PVsyst and PVGIS write them.')

    @Property('QVariantList', notify=sceneChanged)
    def objects(self):
        return self._objects

    @Property('QVariantList', notify=sceneChanged)
    def modules(self):
        return self._modules

    @Property('QVariantList', notify=sceneChanged)
    def bounds(self):
        return self._bounds

    @Property('QVariantList', notify=overlayChanged)
    def highlights(self):
        return self._highlights

    @Property('QVariantList', notify=wiringChanged)
    def wires(self):
        return self._wires

    @Property('QVariantList', notify=wiringChanged)
    def wireFills(self):
        return self._wire_quads

    @Property('QVariantList', notify=unwiredChanged)
    def unwiredPaths(self):
        """The modules in no string, outlined red, apart from the strings' fills (R496)."""
        return self._unwired

    @Property('QVariantList', notify=draftChanged)
    def draftWires(self):
        return self._draft_wires

    @Property('QVariantList', notify=draftChanged)
    def draftFills(self):
        return self._draft_quads

    @Property('QVariantList', notify=draftChanged)
    def draftDots(self):
        return self._draft_dots

    @Property('QVariantList', notify=draftChanged)
    def draftLabels(self):
        return self._draft_labels

    @Property(str, notify=draftChanged)
    def draftColour(self):
        return self._draft_colour

    @Property('QVariantList', notify=bandChanged)
    def draftBand(self):
        """[x0, y0, x1, y1] scene: from the draft's last module to the pointer; empty without a draft (R496)."""
        return self._band

    @Property('QVariantList', notify=wiringChanged)
    def stringLabels(self):
        """Names and numbers of the finished strings (the draft's numbers are in draftLabels)."""
        return self._string_labels

    @Property(str, notify=wiringChanged)
    def wiringLevel(self):
        """near, mid or far: how much the strings say at the scale of the last overlay (R496)."""
        return self._wiring_level

    @Property(float, notify=wiringChanged)
    def moduleSize(self):
        return self._module_size

    @Property('QVariantList', notify=overlayChanged)
    def moduleHighlights(self):
        """The modules lit, one by one: what the tests read. The plan draws moduleHighlightPaths."""
        if self._module_highlights is None:
            self._module_highlights = qml_objects(self._lit_objects())
        return self._module_highlights

    @Property('QVariantList', notify=overlayChanged)
    def moduleHighlightPaths(self):
        return self._module_highlight_paths

    @Property('QVariantList', notify=wiringChanged)
    def optimizerPaths(self):
        return self._optimizer_paths

    @Property('QVariantList', constant=True)
    def optimizerLegendWords(self):
        from .plant_i18n import _ as words
        return [words('Power optimizer'), words('String'), words('Cable to the module')]

    @Property(int, notify=tipsChanged)
    def moduleTipsRevision(self):
        return self._module_tips_revision

    @Slot(str, str, result=str)
    def moduleTip(self, sfid, key):
        """What the tooltip says of a module (R425): asked when the module under the pointer changes, not at each step."""
        return self._module_tips.get((sfid, key), self._module_tip_default)

    def set_string_details(self, tips, default, fitted, states=None, partial=None):
        """From the plant, when it is built: the words of each module, the optimizers per inverter, the state of
        each string by hand (its traffic light on the plan, R496) and the inverters whose optimizers are on some modules
        only (R456: inverter -> the modules with one)."""
        self._module_tips, self._module_tip_default = tips, default
        self._module_tips_revision += 1
        self.tipsChanged.emit()
        changed = states is not None and states != self._string_states
        if changed:
            self._string_states = dict(states)
        if fitted != self.editor.string_optimizers:
            self.editor.string_optimizers = fitted
            changed = True
        partial = dict(partial or {})
        if partial != getattr(self.editor, 'string_partial', {}):
            self.editor.string_partial = partial
            changed = True
        if changed:
            self._overlays()

    @Property('QVariantList', notify=overlayChanged)
    def draftObjects(self):
        return self._draft

    @Property('QVariantList', notify=overlayChanged)
    def labels(self):
        return self._labels

    @Property('QVariantList', notify=overlayChanged)
    def grips(self):
        return self._grips

    @Property('QVariantList', notify=wiringChanged)
    def dots(self):
        return self._dots

    @Property('QVariantList', notify=overlayChanged)
    def marks(self):
        return self._marks

    @Slot('QVariantList')
    def setMarks(self, marks):
        from .plan_marks import marks_scene
        self._marks = marks_scene(marks)
        self.overlayChanged.emit()

    @Slot(str, str)
    def selectMark(self, kind, oid):
        self.editor.select(kind, oid)
        self._overlays()
        self.markClicked.emit(kind, oid)

    @Slot(str, str, float, float)
    def markClick(self, kind, oid, x, y):
        """A click on a check's mark at (x, y). A mark of a sub-field lies on its modules, and the hover shows the module
        under it (R529): the click takes that module, as anywhere else; the first time it also shows the sub-field's
        checks, as the mark did. A mark on anything else selects what it marks."""
        hit = self.editor.pick((x, y))
        if self._tool == 'select' and kind == 'subfield' and hit[0] == 'module' and hit[1] == oid:
            found = self.editor.anchor()
            known = found is not None and found[:2] == ('subfield', oid)
            self.click(x, y, 0)
            if not known:
                self.markClicked.emit(kind, oid)
            return
        self.selectMark(kind, oid)

    @Property('QVariantList', notify=stateChanged)
    def clickKinds(self):
        """What a click or a hover can light in this phase: the editor's rule, for the overlay's own quick index. A
        pitch comes with Tab, a row with a second click."""
        return sorted(self.editor.selectable() - {'pitch', 'row'})

    @Property('QVariantMap', notify=overlayChanged)
    def anchor(self):
        """The outline the clicks stay on (R427 c), in scene metres: the hover shows what a click would do."""
        return self._memoised('anchor', self._anchor)

    def _anchor(self):
        found = self.editor.anchor()
        if found is None:
            return {'oid': '', 'ring': []}
        return {'oid': found[1], 'ring': [[float(x), -float(y)] for x, y in found[2]]}

    @Slot(float, float, float, result=int)
    def vertexAt(self, x, y, mpp):
        """The corner of what is selected the pointer is on, within R427's reach in logical pixels, or -1."""
        return nearest_vertex([(g['x'], g['y']) for g in self._grips], (x, y), VERTEX_PX*mpp)

    @Property('QVariantMap', notify=overlayChanged)
    def rowHandle(self):
        return self._memoised('rowHandle', lambda: (self.editor.row_handle() or {}) if self._tool == 'select' else {})

    @Property('QVariantList', notify=overlayChanged)
    def selectedRing(self):
        return self._memoised('selectedRing', self._selected_ring_shown)

    def _selected_ring_shown(self):
        if self.session.selected_many():
            return []
        return self._selected_ring() if self._tool == 'select' and not self.editor.selected_module[0] else []

    @Property(str, notify=stateChanged)
    def phase(self):
        return self.editor.phase

    @Property(int, notify=overlayChanged)
    def chosenString(self):
        return self.editor.chosen_string

    @Property('QVariantMap', constant=True)
    def statusSymbols(self):
        from .plan_marks import symbol_catalogue
        return symbol_catalogue(True)

    @Slot(int)
    def chooseString(self, index):
        self.editor.chosen_string = index if 0 <= index < len(self.editor.runs()) else -1
        self._overlays()

    @Property('QVariantMap', notify=overlayChanged)
    def selectionState(self):
        return dict(kind=self.editor.selection[0], oid=self.editor.selection[1], key=self.editor.selected_module[1],
                    swept=[list(x) for x in self.editor.swept], sweptThings=[list(x) for x in self.editor.swept_things])

    @Slot(str, float, float)
    def resizeRow(self, oid, x, y):
        self._run(lambda: self.editor.resize_row(oid, (x, y)))

    @Property('QVariantMap', notify=stateChanged)
    def preview(self):
        return self.drawing.preview if self._tool not in EDIT_TOOLS else self.editor.preview

    @Property(str, notify=stateChanged)
    def tool(self):
        return self._tool

    @Property(str, notify=stateChanged)
    def hint(self):
        if self._side is not None:
            return _('Enter: apply length · Esc: cancel')
        if self.placer.active:
            card = self.placer.card() if not self.placer.error else ''
            return self.placer.hint + (' · ' + card if card else '')
        if self.collector.active:
            return self.collector.hint
        return self.editor.hint if self._tool in EDIT_TOOLS else self.drawing.hint

    @Property(bool, notify=stateChanged)
    def collecting(self):
        return self.collector.active or self.placer.active

    @Property(str, notify=overlayChanged)
    def collectBadge(self):
        """R497: the icon beside the pointer while «Align the view to a side» waits and the pointer is on a side it
        takes (the side itself is lit in the overlay); '' otherwise, as the + and - of the selection."""
        c = self.collector
        return 'view_align' if c.mode == 'edge' and c.purpose == 'align' and c.hover else ''

    @Slot(str, 'QVariantList')
    def pickPoints(self, purpose, hints):
        self.collector.points(purpose, hints)
        self.stateChanged.emit()

    @Slot(str, str, str, 'QVariantList')
    def pickEdge(self, purpose, kind, oid, ring):
        self.collector.edges(purpose, [(kind, oid, ring)])
        self.stateChanged.emit()

    @Slot(str)
    def pickAnyEdge(self, purpose):
        """R505: only the sides of buildings, pitches and sub-fields, those of the selected object first."""
        self.collector.edges(purpose, [(o['kind'], o['oid'], [[x, -y] for x, y in o['points']])
                                      for o in self._scene['objects']
                                      if o['kind'] in ('subfield', 'pitch', 'building')], self.editor.selection)
        self.stateChanged.emit()

    @Property(str, notify=stateChanged)
    def error(self):
        return self._error

    @Property(bool, notify=stateChanged)
    def sideEditing(self):
        return self._side is not None

    @Slot(result=bool)
    def sideTyped(self):
        """A measure is being typed while a side is held (R473): the release keeps the drag however short it was."""
        side = self.editor.side
        return bool(side and side.get('typed'))

    @Property(str, notify=stateChanged)
    def sideValue(self):
        return self._side_value

    @Property(int, notify=stateChanged)
    def sideIndex(self):
        return self._side if self._side is not None else -1

    @Property(QObject, notify=mapChanged)
    def maps(self):
        return self._maps

    @Property(QObject, notify=mapChanged)
    def sourceEditor(self):
        return self._source_editor

    @Property(QObject, constant=True)
    def underlays(self):
        return self._underlays

    def _sources_applied(self, choice, sources):
        self.chooseMapOptions({'sources': sources, 'source': choice})
        self.sourcesApplied.emit(choice, sources)

    @Property('QVariantList', notify=navigationChanged)
    def navigation(self):
        return self._nav

    @Property('QVariantMap', notify=navigationChanged)
    def navigationStyle(self):
        return self._navigation_style

    @Property('QVariantMap', constant=True)
    def planColors(self):
        # Constant for QML, yet read at every overlay by the items that use it: built once (R465).
        if not hasattr(self, '_plan_colors'):
            self._plan_colors = {k: theme_colors.qt_hex(v) for k, v in view_colours.PHOTO.items()}
        return self._plan_colors

    @Property(str, constant=True)
    def hatchSource(self):
        # Decode once on the GUI thread; the native Shape samples the texture thereafter.
        from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt
        from PySide6.QtGui import QBrush, QColor, QImage, QPainter
        image = QImage(8, 8, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.fillRect(image.rect(), QBrush(QColor(view_colours.PHOTO['exclusion']), Qt.BDiagPattern))
        painter.end()
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.WriteOnly)
        image.save(buffer, 'PNG')
        return 'data:image/png;base64,'+bytes(data.toBase64()).decode('ascii')

    @Property('QVariantMap', constant=True)
    def texts(self):
        # Read 16-32 times inside one overlayChanged (06/11/2026): forty translations each time, now once.
        if not hasattr(self, '_texts'):
            self._texts = self._make_texts()
        return self._texts

    def _make_texts(self):
        return {'select': _('Select'), 'move': _('Move'), 'rotate': _('Rotate'), 'remove': _('Delete'),
                'undo': _('Undo'), 'fit': _('Fit to the drawing'), 'draw': _('Draw'), 'background': _('Background'),
                'sources': _('Map sources'), 'otherSources': _('Other sources…'), 'otherSourcesTip': _('Every source with its area and its licence, the default choice and your own sources (WMS, WMTS, XYZ): Settings > Maps'), 'importImage': _('Import an image…'), 'importImageTip': _('A PNG, a JPEG or the first page of a PDF, under the drawing: then in scale with two points'), 'rename': _('Rename'), 'name': _('Name:'), 'cancel': _('Cancel'),
                'chooseBackground': _('Choose the background'),
                'apply': _('Apply'), 'closeWindow': _('Close'), 'north': _('North up'), 'align': _('Align the view to a side'),
                'northClick': _('Click: North up again (N)'), 'yes': _('Yes'), 'no': _('No'),
                'close': _('Close the outline'), 'back': _('Remove the last point (Backspace)'),
                'cancelDrawing': _('Cancel the drawing (Esc)'), 'duplicate': _('Duplicate'),
                'append': _('Add a row at the back'), 'explode': _('Separate the modules'), 'turn': _('Turn the row'),
                'lay': _('Lay modules'), 'darken': _('Darken the imagery'), 'strings': _('Strings'),
                'vertex': _('Drag the corner; it snaps to the other outlines, Ctrl drags it free.'),
                'corners': _('Click: this corner only · Shift+click: add · Ctrl+click: add or take away · a window: the corners in it. Drag one of them, the arrows or a measure typed move them together.'),
                'cornersField': _('Move {n} corners by (East; North)'),
                'gripMove': _('Move: drag it where it goes, or click it and then click the place. Ctrl held at the end makes a '
                              'copy; Enter or Space pass to Rotate.'),
                'gripRotate': _('Rotate about the middle: drag it, or click it and then click the direction. Steps of 15°, 5° '
                                'with Ctrl, 90° with Shift; Ctrl held at the end makes a copy; Enter or Space pass to Move.')}

    @Property('QVariantList', constant=True)
    def viewTools(self):
        from meridiana.shortcuts import commands
        known = {c.id: c for c in commands()}
        groups = [('view_plan', 'view_3d', 'view_both'), ('fit', 'zoom_in', 'zoom_out'),
                  ('view_align',), ('snaps', 'ortho'), ('background',)]
        return [dict(command=key, icon={'view_plan': 'plan', 'view_3d': '3d', 'view_both': 'both'}.get(key, key), group=i,
                     tip=(_('Background') if key == 'background' else known[key].text.replace('&', '')
                          + (' ('+known[key].keys[0]+')' if known[key].keys else '')))
                for i, group in enumerate(groups) for key in group]

    @Property('QVariant', notify=mapChanged)
    def mapChoices(self):
        """The Background menu for the site in hand (R36, ui/window.py _fill_sources): Automatic with the name of the
        best, the photos and the maps that cover the site, None. A choice that does not cover it shows as Automatic."""
        from meridiana import tiles
        automatic = dict(key=tiles.AUTO, text=_('Automatic'), tip=_('The best source for the site of the project, chosen by Meridiana'))
        none = dict(key=tiles.NONE, text=_('None'), tip=_('The plan alone, on its light ground'))
        if not self._maps:
            return dict(automatic=automatic, photos=[], maps=[], none=none, checked=tiles.AUTO)
        sources, site = self._maps.state.sources, self.session.project.site
        # Asked at every change of the plan's state, and looking through every outline of the catalogue: once per site.
        key = (site.lon, site.lat, tuple(sources))
        if self._map_covering is None or self._map_covering[0] != key:
            self._map_covering = (key, sources.get(tiles.best(sources, site.lon, site.lat)), tiles.covering(sources, site.lon, site.lat))
        best, found = self._map_covering[1:]
        if best:
            automatic['text'] = _('Automatic: {name}').format(name=tiles.display_name(best))
        row = lambda s: dict(key=s.key, text=tiles.display_name(s), tip='\n'.join(t for t in (s.credit(), tiles.display_licence(s)) if t))
        listed = {tiles.AUTO, tiles.NONE, *(s.key for s in found)}
        return dict(automatic=automatic, none=none, checked=self._maps.choice if self._maps.choice in listed else tiles.AUTO,
                    photos=[row(s) for s in found if s.imagery == 'photo'],
                    maps=[row(s) for s in found if s.imagery != 'photo'])

    preferencesRequested = Signal(str)

    @Slot()
    def refreshMapChoices(self):
        """Made again each time the menu opens: the site may have moved."""
        self.mapChanged.emit()

    @Property('QVariantList', constant=True)
    def veilChoices(self):
        return [dict(value=v, text=_('{n} %').format(n=round(100*v)) if v else _('Not darkened'))
                for v in view_colours.VEILS]

    @Property('QVariantList', constant=True)
    def tools(self):
        return [dict(key=k, name=_(name)) for k, name in [('select', 'Select'), ('building', 'Building'),
                ('pitch', 'Free pitch'), ('ridge', 'Ridge'), ('subfield', 'Sub-field'), ('exclusion', 'Exclusion'),
                ('row', 'Row'), ('east_west', 'East-west'), ('prop', '3D object'), ('prop_line', 'Linear 3D object'),
                ('canopy', 'Parking canopy'), ('measure', 'Measure'), ('square', 'Square the corners'),
                ('string', 'Draw a string'), ('erase_string', 'Delete a string'),
                ('erase_inverter_strings', 'Delete an inverter and its strings'), ('erase_inverter', 'Delete an inverter')]]

    @Property(str, notify=overlayChanged)
    def measureText(self):
        """Length, area and the rest of what is selected, as the status bar of the Widgets says it."""
        return self._memoised('measureText', self._measure_text)

    def _measure_text(self):
        kind, oid = self.editor.selection
        if not kind or kind == 'site':
            return ''
        from meridiana import viewaids
        return viewaids.measure_text(viewaids.measure(self.session.project, self.session.good_results(), kind, oid))

    @Property(str, notify=overlayChanged)
    def selectionName(self):
        kind, oid = self.editor.selection
        thing = self.session.project.building(oid) if kind == 'building' else self.session.subfield(oid)
        return thing.name if thing else ''

    @Property('QVariantList', notify=overlayChanged)
    def targetBounds(self):
        return self._memoised('targetBounds', self._target_bounds)

    def _target_bounds(self):
        ring = self._selected_ring()
        if not ring:
            return self._bounds
        xs, ys = zip(*ring, strict=True)
        return [min(xs), -max(ys), max(xs)-min(xs), max(ys)-min(ys)]

    @Slot(float, float)
    def contextAt(self, x, y):
        self._context_coords = (float(x), float(y))     # «Copy the coordinates» (R487), with every tool
        if self._tool != 'select':
            self._overlays()
            return
        kind, oid, key = self.editor._anchored((x, y)) or self.editor.pick((x, y))
        if kind == 'pitch' and self.editor.selection != ('pitch', oid):
            kind, oid = 'building', oid.partition(':')[0]
        self.editor.select(kind or 'site', oid, key)
        from .plan_menu import building_under, near_side
        self.pointer(x, y, 0, self._mpp)
        self._context_side = near_side(self, (x, y))
        self._context_host = building_under(self, (x, y))
        self._context_point = (float(x), float(y))      # where «Add a module» puts it
        self._overlays()

    @Property('QVariantList', notify=overlayChanged)
    def contextItems(self):
        from .plan_menu import entries
        return self._memoised('contextItems', lambda: entries(self))

    @Slot(float, float)
    def pointerScale(self, mpp, bearing):
        self._mpp = mpp
        self._view_bearing = bearing
        self.editor.pick_reach = 6*mpp
        self.drawing.metres_per_pixel = mpp

    @Slot(str)
    def contextCommand(self, name):
        kind, oid = self.editor.selection
        if name == 'relayout' and kind == 'subfield' and self.session.subfield(oid).manual:
            self._relayout_target = oid
            self.relayoutRequested.emit(_('Lay again automatically'),
                _('The rows by hand give way to the automatic layout, and the modules taken '
                  'out by hand come back. Undo brings them back. Go on?'))
        elif name in ('append', 'explode', 'turn') and kind == 'row':
            self._run(lambda: self.editor.apply_command(dict(type='row_'+name, oid=oid)))
        elif name == 'duplicate':
            made = []
            self.session.edit(_('Duplicate'), lambda p: made.append(p.duplicate(kind, oid)))
            if made:
                self.editor.select(kind, made[0])
                self._overlays()
        else:
            from .plan_menu import execute
            self._run(lambda: execute(self, name))

    @Slot(bool)
    def confirmRelayout(self, accepted):
        oid = getattr(self, '_relayout_target', '')
        self._relayout_target = ''
        if accepted and self.session.subfield(oid) is not None:
            from meridiana import manual
            self._run(lambda: self.session.edit(_('Lay again automatically'), manual.relayout(self.session.project, oid)))

    @Slot(str)
    def rename(self, name):
        kind, oid = self.editor.selection
        if name.strip() and kind in ('building', 'subfield'):
            def change(project):
                thing = project.building(oid) if kind == 'building' else next(s for s in project.subfields if s.id == oid)
                thing.name = name.strip()
            self.session.edit(_('Rename'), change)

    @Slot(str)
    def setNavigation(self, style):
        chosen = navigation.STYLES.get(style, navigation.STYLES['autocad'])
        buttons, mods = {'left': 1, 'right': 2, 'middle': 4}, {'ctrl': 1, 'shift': 2, 'alt': 4}
        self._nav = [dict(action=action, buttons=sum(buttons[b] for b in bs), mods=sum(mods.get(m, 0) for m in ms))
                     for action in ('pan', 'orbit', 'zoom') for bs, ms in getattr(chosen, action)]
        self._navigation_style = {
            name: [[sorted(bs), sorted(ms)] for bs, ms in getattr(chosen, name)]
            for name in ('pan', 'orbit', 'zoom', 'select')}
        self._navigation_style.update({name: getattr(chosen, name)
                                       for name in ('middle_click', 'middle_double', 'right_click')})
        self.navigationChanged.emit()

    def _changed(self, topics):
        if self._closed:
            return
        if any(t.startswith('layout:') for t in topics) or topics & {
                'project:geometry', 'project:subfields', 'project:site', 'project:underlays', 'project:variants', 'restored', 'file'}:
            self.refresh(overlays=not self._answering())
            if self.shadow_scheduler.options is not None and topics & {'project:geometry', 'restored', 'file'}:
                self.shadow_scheduler.request(self.shadow_scheduler.options)
        elif not (self._running and topics == {'selection'}):      # _run draws them once at its end
            self._overlays()

    def _light_modules(self, chosen, width, alpha):
        """The modules lit as native paths, joined from the path each module has once per layout: a selection of thousands
        costs a join, not a list of thousands of objects there and back through QML (R419)."""
        if not self._module_paths and self._scene['modules']:
            for module in self._scene['modules']:
                points = module['points']
                self._module_paths[(module['oid'], module['key'])] = (
                    'M' + ' L'.join(f'{float(x):.8g},{float(y):.8g}' for x, y in points) + ' Z')
        paths = [self._module_paths[key] for key in chosen if key in self._module_paths]
        self._lit = [key for key in chosen if key in self._module_paths], width, alpha
        self._module_highlights = None
        colour = view_colours.kind_colour('module')
        halo = dict(fill=theme_colors.qt_hex(colour + f'{alpha:02x}'), stroke=view_colours.PHOTO['halo'],
                    width=width + view_colours.WIDTHS['select_halo'], dashed=False)
        line = dict(fill='transparent', stroke=colour, width=width, dashed=False)
        self._module_highlight_paths = [dict(style, path=' '.join(paths[start:start + 1000]))
                                        for style in (halo, line) for start in range(0, len(paths), 1000)]

    def _lit_objects(self):
        keys, width, alpha = self._lit if self._lit else ([], 0, 0)
        by = {(m['oid'], m['key']): m for m in self._scene['modules']} if keys else {}
        colour = view_colours.kind_colour('module')
        out = []
        for key in keys:
            module = by[key]
            out += [{**module, 'closed': True, 'stroke': view_colours.PHOTO['halo'], 'dashed': False,
                     'width': width + view_colours.WIDTHS['select_halo'], 'fill': colour + f'{alpha:02x}'},
                    {**module, 'closed': True, 'stroke': colour, 'width': width, 'fill': 'transparent', 'dashed': False}]
        return out

    def _answering(self):
        """R547: a change of the modules is being shown first (session._answer_first): the overlays (strings, wiring,
        grips: 100 ms on Rho) are drawn after the frame that shows the modules, with the other views."""
        if self.session.later is None or getattr(self.session, '_waiting', None) is None:
            return False
        self.session.later(lambda: None if self._closed else self._overlays())
        return True

    def refresh(self, overlays=True):
        self._module_paths = {}
        self.editor.set_results(self.session.good_results())
        self.drawing.set_project(self.session.project)
        self.drawing.set_results(self.session.good_results())
        before = self._scene.get('modules') if isinstance(getattr(self, '_scene', None), dict) else None
        self._scene = scene_of(self.session.project, self.session.good_results())
        if before and _moved(before, self._scene['modules']):
            self.modulesMoved.emit()
        self._objects = qml_objects(self._scene['objects'])
        self._modules = qml_objects(self._scene['modules'])
        self._bounds = drawing_bounds(self._scene)
        self._move_snapper.set_references(self._scene['segments'])
        if self._maps:
            site = self.session.project.site
            self._maps.configure(origin=geo.Origin(site.lat, site.lon), underlays=self.session.project.underlays)
            self._keep_area()
        self.sceneChanged.emit()
        if overlays:
            self._overlays()

    def _keep_area(self):
        """R516: once the project has its site, the orthophoto of the drawing and around it kept for the plan
        without network (MapController.keepArea; the drawing's bounds are in the scene's metres, minus North)."""
        site = self.session.project.site
        if not self._maps or not (site.address or (site.lat, site.lon) != (model.Site.lat, model.Site.lon)):
            return
        x, y, w, h = self._bounds
        self._maps.keepArea((x, -(y + h), x + w, -y))

    def _run(self, operation):
        self._error = ''
        self._running = True
        try:
            commands = operation() or []
            if self._tool not in EDIT_TOOLS:
                for command in commands:
                    if command.get('type') == 'tool':
                        self.setTool(command['tool'])
                    else:
                        self.editor.apply_command(command)
                        if self.editor.last_error:
                            raise ValueError(self.editor.last_error)
            machine = self.editor if self._tool in EDIT_TOOLS else self.drawing
            self._error = getattr(machine, 'last_error', getattr(machine, 'error', ''))
            if machine is self.editor:      # a double click closing a string, a gesture that ends: Select again
                self._tool = self.editor.tool
        except (ValueError, KeyError, IndexError, TypeError) as error:
            self._error = str(error)
        finally:
            self._running = False
        self._overlays()
        state = (self._tool, self._error, self.hint, self.preview, self.hotGrip, getattr(self.editor, 'notice', ''),
                 self.editor.swept_things, self.editor.chosen_string)
        if not self._moving or state != self._state_key:
            self._state_key = state
            self.stateChanged.emit()

    @Slot(str)
    def setTool(self, tool):
        self.calls['tool'] += 1
        self._side = None
        self._tool = tool
        self._error = ''
        self.editor.set_tool(tool if tool in EDIT_TOOLS else 'select')
        self.drawing.set_tool(tool if tool not in EDIT_TOOLS else 'select')
        if tool in EDIT_TOOLS:
            self._tool = self.editor.tool
        self._overlays()
        self.stateChanged.emit()

    @Slot(str, 'QVariantMap')
    def activateTool(self, tool, options):
        """The shell's split buttons supply prop kinds and canopy dimensions here."""
        self.setTool(tool)
        if tool not in EDIT_TOOLS:
            self.drawing.set_tool(tool, **options)
            self._overlays()
            self.stateChanged.emit()

    @Slot(str, float, float)
    def startGrip(self, grip, x, y):
        self.editor.start_grip(grip, (x, y))
        self._tool = self.editor.tool
        self._overlays()
        self.stateChanged.emit()

    @Slot(str)
    def setPhase(self, phase):
        self.editor.set_phase(phase)
        self.setTool('select')

    @Property(bool, notify=stateChanged)
    def stringsVisible(self):
        return self.editor.phase == 'plant' or self._show_strings

    @Property(bool, notify=stateChanged)
    def snapsEnabled(self):
        return self.editor.snaps_on

    @Property(bool, notify=stateChanged)
    def orthoEnabled(self):
        return self.drawing.orthogonal

    @Slot(str)
    def viewAction(self, action):
        if action == 'strings':
            self._show_strings = not self._show_strings
            self._overlays()
        elif action == 'snaps':
            self.editor.snaps_on = self.drawing.snaps_on = not self.editor.snaps_on
        elif action == 'ortho':
            self.drawing.orthogonal = not self.drawing.orthogonal
        elif action == 'view_align':
            self.pickAnyEdge('align')
        else:
            self.viewCommand.emit(action)
        self.stateChanged.emit()

    @Slot(bool)
    def setRectangle(self, on):
        self.drawing.set_rectangle(on)
        self.stateChanged.emit()

    @Slot(float, float, int)
    def click(self, x, y, bits=0):
        self.calls['click'] += 1
        if self.placer.active:
            if not self.placer.asking:
                self.placer.move((x, y), modifiers(bits), self._mpp, self.session.project)
                self._lay()
            return
        if self.collector.active:
            result = self.collector.click((x, y), self._mpp)
            if result:
                if result['type'] == 'points':
                    self.pointsPicked.emit(result['purpose'], result['points'])
                else:
                    self.edgePicked.emit(result['purpose'], result['kind'], result['oid'], result['side'])
                    if result['purpose'] == 'align':
                        self.alignRequested.emit(result['angle'])
            self._overlays()
            self.stateChanged.emit()
            return
        if self._tool == 'select' and not bits:
            # A cosmetic outline remains clickable just outside the polygon.
            # Preserve its selection before the following double click opens a side.
            ring = self.selectedRing
            if (ring and sides.nearest(ring, (x, y), 6*self._mpp) is not None
                    and self.editor.pick((x, y))[0] in ('', 'site')):
                return
        if self._tool in PLACE_TOOLS and not self.drawing.points:
            # R554 (Daniel 08/11): with the tool «3D object» a click on an object already placed takes it instead of
            # placing another one on it; the tool stays, Esc ends it. A row or a line already started goes on.
            hit = next(self.editor._hits((x, y), frozenset({'prop'})), None)
            if hit is not None:
                self.editor.select('prop', hit[1])
                self._overlays()
                self.stateChanged.emit()
                return
        machine = self.editor if self._tool in EDIT_TOOLS else self.drawing
        p = self._snapped_move((x, y), modifiers(bits)) if self._tool in ('move', 'rotate') else (x, y)
        self._run(lambda: machine.click(p, modifiers(bits)))
        if machine is self.editor and self._tool != self.editor.tool:     # a paste done gives Select back
            self._tool = self.editor.tool
            self._overlays()
            self.stateChanged.emit()

    @Slot(float, float, int)
    def doubleClick(self, x, y, bits=0):
        self.calls['doubleClick'] += 1
        if self._tool == 'select' and self.editor.pick((x, y))[0] == 'module':
            self._run(lambda: self.editor.double_click((x, y), modifiers(bits)))
            return
        ring = self.selectedRing
        side = sides.nearest(ring, (x, y), 14*self._mpp) if ring else None
        if side is not None and self._tool == 'select':
            self.editSide(side)
            return
        if self._tool not in EDIT_TOOLS:
            self._run(lambda: self.drawing.double_click((x, y), modifiers(bits)))
        else:
            self._run(lambda: self.editor.double_click((x, y), modifiers(bits)))

    @Slot(float, float, int, float)
    def pointer(self, x, y, bits, mpp):
        self.calls['pointer'] += 1
        self._mpp = mpp
        self.drawing.metres_per_pixel = mpp
        self.editor.pick_reach = 6*mpp
        if self.placer.active:
            self.placer.snaps_on = self.editor.snaps_on
            if self.placer.move((x, y), modifiers(bits), mpp, self.session.project):
                self._overlays()
                self.stateChanged.emit()
            return
        if self.collector.active:
            def lit(hover):
                return hover and (hover[0], hover[1], hover[3])
            before = lit(self.collector.hover)
            self.collector.move((x, y), mpp)
            if lit(self.collector.hover) != before:
                self._overlays()            # the lit side changed: not at every step of the pointer
            return
        machine = self.editor if self._tool in EDIT_TOOLS else self.drawing
        p = self._snapped_move((x, y), modifiers(bits)) if self._tool in ('move', 'rotate') else (x, y)
        self._moving = True          # R496: a move that changes nothing the plan draws stays silent
        try:
            self._run(lambda: machine.move(p, modifiers(bits)))
        finally:
            self._moving = False

    def _snapped_move(self, point, mods):
        gesture = self.editor.gesture
        if gesture is not None and gesture.mode == 'rotate':
            return point
        chain = [gesture.base] if gesture is not None and gesture.base is not None else []
        return self._move_snapper.snap(point, chain, self._mpp,
                                      free=not self.editor.snaps_on).point

    @Slot(float, float, int)
    def drag(self, x, y, bits):
        self.calls['drag'] += 1
        self._run(lambda: self.editor.drag((x, y), modifiers(bits)))

    @Slot('QVariantMap')
    def configureMaps(self, options):
        if not self._maps:
            return
        if 'offline' in options:
            self._maps.configure(offline=bool(options['offline']))
            self._keep_area()
        if 'sources' in options:
            self._maps.configure(custom_sources=options['sources'])
        if 'source' in options:
            self._maps.setSource(options['source'])
            self._keep_area()
        if 'veil' in options:
            self._maps.setVeil(float(options['veil']))
        if 'sources' in options or 'source' in options:
            if self._source_editor:
                self._source_editor.load_preferences(self._maps.choice, options.get('sources', self._source_editor._custom))
            self.mapChanged.emit()

    @Slot('QVariantMap')
    def chooseMapOptions(self, options):
        self.configureMaps(options)
        self.mapPreferencesChanged.emit(options)

    @Slot(str, str, int)
    def key(self, key, text='', bits=0):
        self.calls['key'] += 1
        mods = modifiers(bits)
        if key in ('F3', 'F8') or key == 'W' and not mods:
            self.viewAction({'F3': 'snaps', 'F8': 'ortho', 'W': 'strings'}[key])
            return
        if self.placer.active:
            self._placing_key(key, mods)
            return
        if self.collector.active:
            self.collector.key(key)
            self._overlays()
            self.stateChanged.emit()
            return
        if key == 'A' and not mods:
            self.pickAnyEdge('align')
            return
        if 'ctrl' in mods and key in ('Z', 'Y'):
            undo = self.session.undo
            (undo.redo if key == 'Y' or 'shift' in mods else undo.undo)()
            return
        keys = {'V': 'select', 'B': 'building', 'P': 'pitch', 'C': 'ridge', 'S': 'subfield',
                'X': 'exclusion', 'O': 'prop', 'L': 'row', 'M': 'move', 'D': 'measure', 'Q': 'square'}
        if not mods and self._tool == 'select' and key in keys:
            self.setTool(keys[key])
            return
        machine = self.editor if self._tool in EDIT_TOOLS else self.drawing
        self._run(lambda: machine.key(key, text, mods))
        if machine is self.editor:
            self._tool = self.editor.tool
            self._overlays()
            self.stateChanged.emit()
        if getattr(machine, 'tool', self._tool) == 'select' and self._tool != 'select':
            self.setTool('select')

    # R454: the «Place» mode of an imported IFC model (plan_place.Placer, meridiana.ifc_place)

    def placeModel(self, plan, place=None, follow=True, name=''):
        """Begin placing the model `plan` (ifc_import.Plan, not yet in the project): its outlines follow the pointer
        (`follow`) or stand where the import put them until Enter."""
        self.collector.cancel()
        self.setTool('select')
        self.placer.start(plan, place, follow, name)
        self._error = ''
        self._overlays()
        self.stateChanged.emit()
        self.placingChanged.emit()

    def _placing_key(self, key, mods):
        placer = self.placer
        placer.error = ''
        if placer.asking:
            if key == 'Escape':
                placer.asking = []
        elif key == 'Escape':
            placer.cancel()
            self.notice.emit(_('The IFC model was not imported.'))
        elif key == 'Enter':
            self._lay()
            return
        elif key == 'R':
            placer.turn(1, mods)
        elif key == 'M' and not mods:
            placer.follow = not placer.follow
        elif key == 'C' and not mods:
            self.placingChanged.emit()
            self.coordinatesAsked.emit()
            return
        elif key in ('Left', 'Right', 'Up', 'Down'):
            placer.nudge(key, mods)
        else:
            return
        self._overlays()
        self.stateChanged.emit()
        self.placingChanged.emit()

    @Slot(float, int)
    def placeWheel(self, steps, bits=0):
        """The wheel held with Shift while placing: a notch turns the model by a step (15 degrees, 5 with Ctrl)."""
        if not self.placer.active or self.placer.asking or not steps:
            return
        self.placer.turn(1 if steps > 0 else -1, modifiers(bits) - {'shift'})
        self._overlays()
        self.stateChanged.emit()

    def _lay(self):
        """Click or Enter while placing: laid at once, or the question when it falls on buildings already drawn."""
        from meridiana import ifc_import, ifc_place
        placer = self.placer
        out = placer.placed()
        why = ifc_import.problem(out)
        if why:
            placer.error = why
            self.stateChanged.emit()
            return
        under = ifc_place.overlaps(self.session.project, out)
        if under:
            placer.asking = under
            names = ', '.join(f'«{self.session.project.building(i).name}»' for i in under)
            self.placeAsked.emit(_('The model falls on a building'), _(
                "The model falls on {names}. Replace: the building drawn goes, the sub-fields drawn on it go to the "
                "model's roof under them. Keep both: the model is added over it. Beside: the model is laid next to it. "
                "Ctrl+Z takes back the whole import.").format(names=names))
            self.stateChanged.emit()
            self.placingChanged.emit()
            return
        self._commit_placing(())

    @Slot(str)
    def placeAnswer(self, choice):
        """«replace», «keep», «beside» or «back» (go on placing)."""
        from meridiana import ifc_place
        placer = self.placer
        if not placer.active or not placer.asking:
            return
        under, placer.asking = placer.asking, []
        if choice == 'replace':
            self._commit_placing(under)
        elif choice == 'keep':
            self._commit_placing(())
        elif choice == 'beside':
            placer.pl = ifc_place.beside(self.session.project, placer.plan, placer.pl, under)
            placer.follow = False
            self._commit_placing(())
        else:
            self._overlays()
            self.stateChanged.emit()
            self.placingChanged.emit()

    def _commit_placing(self, replace):
        from meridiana import ifc_place
        placer = self.placer
        plan, pl, ids = placer.plan, placer.pl, []
        try:
            self.session.edit(_('Import an IFC model'),
                              lambda p: ids.extend(ifc_place.apply(p, plan, pl, replace=replace)))
        except ValueError as error:
            placer.error = str(error)
            self.stateChanged.emit()
            return
        placer.cancel()
        if ids:
            self.editor.select('building', ids[0])
        self._overlays()
        self.stateChanged.emit()
        self.placingChanged.emit()
        self.modelImported.emit(list(ids))

    @Property('QVariantMap', notify=placingChanged)
    def placing(self):
        """What the window shows while placing: whether, the question, the coordinates now in each system, the file's
        proposal and the words of the window of the coordinates."""
        from meridiana import ifc_place
        placer = self.placer
        if not placer.active:
            return {'active': False}
        project = self.session.project
        values = {k: ifc_place.values(project, placer.pl, placer.plan, k, placer.place) for k in ifc_place.SYSTEMS}
        offer = ifc_place.proposal(project, placer.place)

        def shown(system, v):
            places = 8 if system == 'latlon' else 3
            return {'a': number(v['a'], places), 'b': number(v['b'], places), 'turn': number(v['turn'], 3),
                    'zone': v.get('zone', '')}
        return {
            'active': True, 'follow': placer.follow, 'asking': bool(placer.asking), 'name': placer.name,
            'values': {k: shown(k, v) for k, v in values.items()},
            'proposal': None if offer is None else {'system': offer['system'], 'text': offer['text'],
                                                    **shown(offer['system'], offer)},
            'systems': [{'value': 'utm', 'text': _('UTM, zone {zone} (m)').format(zone=values['utm']['zone'])},
                        {'value': 'latlon', 'text': _('Latitude and longitude (degrees)')},
                        {'value': 'local', 'text': _('Metres East and North of the site')}],
            'labels': {'utm': [_('East'), _('North')], 'latlon': [_('Latitude'), _('Longitude')],
                       'local': [_('East'), _('North')]},
            'texts': {'title': _('Coordinates of the model'),
                      'turn': _("Turn from the file's axes to the north (degrees, anticlockwise)"),
                      'point': _("The point is the origin of the IFC file (its 0, 0), as its georeferencing gives it."),
                      'useFile': _("Use the file's place"), 'place': _('Put it there'), 'cancel': _('Cancel'),
                      'replace': _('Replace'), 'keep': _('Keep both'), 'beside': _('Beside'),
                      'back': _('Go on placing')},
        }

    def _coordinates(self, system, a, b, turn):
        from meridiana import ifc_place
        from .plan_tools import parse_length
        values = [parse_length(str(v).replace('°', '')) for v in (a, b, turn)]
        if any(v is None for v in values):
            raise ValueError(_('Write a number in each field.'))
        placer = self.placer
        return ifc_place.from_values(self.session.project, placer.plan, placer.pl, system, *values, place=placer.place)

    @Slot(str, str, str, str, result='QVariantMap')
    def checkCoordinates(self, system, a, b, turn):
        """What the window of the coordinates says under its fields: the distance from the site, the warning beyond
        FAR_KM, or what is wrong."""
        from meridiana import ifc_place
        if not self.placer.active:
            return {'ok': False, 'text': '', 'warning': False}
        try:
            pl = self._coordinates(system, a, b, turn)
        except ValueError as error:
            return {'ok': False, 'text': str(error), 'warning': True}
        far = ifc_place.far(self.placer.plan, pl)
        km = ifc_place.distance_km(self.placer.plan, pl)
        return {'ok': True, 'warning': bool(far),
                'text': far or _("The model would stand {km} km from the project's site.").format(
                    km=number(km, 3 if km < 1 else 2))}

    @Slot(str, str, str, str, result=bool)
    def placeCoordinates(self, system, a, b, turn):
        """The model moved to the coordinates: it stands there, the mouse no longer moves it, Enter lays it."""
        if not self.placer.active:
            return False
        try:
            self.placer.pl = self._coordinates(system, a, b, turn)
        except ValueError as error:
            self.placer.error = str(error)
            self.stateChanged.emit()
            return False
        self.placer.follow = False
        self.placer.error = ''
        self._overlays()
        self.stateChanged.emit()
        self.placingChanged.emit()
        return True

    @Slot(str)
    def releaseKey(self, key):
        if key == 'Shift':
            self.drawing.lock_direction = None

    @Slot('QVariantList', str, int)
    def sweep(self, ring, kind, bits):
        self.calls['sweep'] += 1
        self._run(lambda: self.editor.select_area(ring, kind, modifiers(bits)))

    @Slot(int, float, float)
    def vertex(self, index, x, y):
        self.calls['vertex'] += 1
        self._run(lambda: self.editor.move_vertex(index, (x, y)))

    # R356 (Daniel 08/11/2026): more corners of a building, a sub-field or an exclusion chosen and moved together, by
    # the rule of the selection (R529): a click starts again, Shift adds, Ctrl adds or takes away, a window takes them

    def _corner_key(self):
        kind, oid = self.editor.selection
        return kind, oid, len(self._grips)

    def _corner_pick(self) -> list:
        key, chosen = getattr(self, '_corners', (None, []))
        return list(chosen) if key == self._corner_key() and self._tool == 'select' else []

    def _set_corners(self, chosen):
        self._corners = (self._corner_key(), sorted({int(i) for i in chosen if 0 <= int(i) < len(self._grips)}))
        self.cornersChanged.emit()

    @Property('QVariantList', notify=cornersChanged)
    def chosenCorners(self):
        return self._corner_pick()

    @Slot(int, int, result=bool)
    def chooseCorner(self, index, bits):
        """A click on corner `index` with the modifiers `bits` (1 Ctrl, 2 Shift): False when it is a plain click on the
        only corner chosen, which then goes to what lies there (R529: the module in the corner of a sub-field)."""
        chosen = self._corner_pick()
        if bits & 1:
            chosen = sorted(set(chosen) ^ {index})
        elif bits & 2:
            chosen = sorted(set(chosen) | {index})
        elif chosen == [index]:
            return False
        else:
            chosen = [index]
        self._set_corners(chosen)
        return True

    @Slot('QVariantList', int)
    def chooseCorners(self, indices, bits):
        """The corners a window took: a plain window starts again, Shift adds, Ctrl takes away."""
        taken = {int(i) for i in indices}
        chosen = set(self._corner_pick())
        self._set_corners(chosen - taken if bits & 1 else chosen | taken if bits & 2 else taken)

    @Slot(float, float)
    def moveCorners(self, dx, dy):
        """Move the corners chosen by (dx, dy) metres, East and North: one undoable change."""
        chosen = self._corner_pick()
        if not chosen or not (dx or dy):
            return
        self.calls['vertex'] += 1
        self._last_corner_step = (dx, dy)
        self._run(lambda: self.editor.apply_command({'type': 'vertices', 'indices': chosen, 'delta': [dx, dy]}))
        self._set_corners(chosen)

    @Slot(str, result=bool)
    def cornersTyped(self, text):
        """The measure written for the corners chosen: «East; North» in metres, or one length along the last move
        (East when there is none). False when it is not a measure."""
        parts = [p for p in re.split(r'[;\s]+', text.strip()) if p]
        values = [move.parse(p) for p in parts]
        if not values or None in values or len(values) > 2:
            self._error = _('Write East; North in metres, or one length along the last move')
            self.stateChanged.emit()
            return False
        if len(values) == 2:
            dx, dy = values
        else:
            ex, ey = getattr(self, '_last_corner_step', (1.0, 0.0))
            norm = math.hypot(ex, ey) or 1.0
            dx, dy = values[0] * ex / norm, values[0] * ey / norm
        self.moveCorners(dx, dy)
        return True

    @Slot(float, float, int, float, result=QPointF)
    def snapVertex(self, x, y, bits, mpp):
        p = self._move_snapper.snap((x, y), [], mpp, free=bool(bits & 1) or not self.editor.snaps_on).point
        return QPointF(*p)

    @Slot(int, float, float, int, float, result=QPointF)
    def snapCorner(self, index, x, y, bits, mpp):
        """Where a corner being dragged goes: to a snap, but not to one that makes its own outline cross itself (a side
        of its own a few pixels away would refuse the drag at the release)."""
        point = self.snapVertex(x, y, bits, mpp)
        ring = [(g['x'], g['y']) for g in self._grips]
        if self.editor.selection[0] != 'prop' and 0 <= index < len(ring):
            ring[index] = (point.x(), point.y())
            if not Polygon(ring).is_valid:
                return QPointF(x, y)
        return point

    # a side dragged parallel to itself (R473; R445 phase B)

    @Slot(float, float, float, result=int)
    def sideAt(self, x, y, mpp):
        """The side of what is selected under the pointer, to drag; -1 where a corner is nearer or there is none."""
        if self._side is not None or self.collector.active:
            return -1
        return self.editor.side_at((x, y), 8 * mpp)

    @Slot(int, float, float)
    def beginSide(self, index, x, y):
        self.calls['beginSide'] = self.calls.get('beginSide', 0) + 1
        # a second press on the same side within the double-click time is the double click of R276: its length
        # and at the same place (R529: two clicks on two modules along the same side are two clicks)
        now = time.monotonic()
        last = getattr(self, '_side_press', None)
        self._side_press = (now, index, x, y)
        if (last is not None and last[1] == index and now - last[0] < 0.4
                and math.hypot(x - last[2], y - last[3]) <= 6 * self._mpp):
            self._side_press = None
            self._run(self.editor.cancel_side)
            self.doubleClick(x, y, 0)
            return
        self._run(lambda: self.editor.start_side(index, (x, y)))
        self._tool = self.editor.tool
        self._overlays()
        self.stateChanged.emit()

    @Slot(float, float, int)
    def dragSide(self, x, y, bits):
        p = (x, y) if bits & 1 or not self.editor.snaps_on else self._move_snapper.snap((x, y), [], self._mpp).point
        self._run(lambda: self.editor.move(p, modifiers(bits)))

    @Slot(float, float, int)
    def endSide(self, x, y, bits):
        p = (x, y) if bits & 1 or not self.editor.snaps_on else self._move_snapper.snap((x, y), [], self._mpp).point
        self._run(lambda: self.editor.end_side(p))
        self._tool = self.editor.tool
        self._overlays()
        self.stateChanged.emit()

    @Slot()
    def cancelSideDrag(self):
        if self.editor.side is None:
            return
        self._run(self.editor.cancel_side)
        self._tool = self.editor.tool
        self._overlays()
        self.stateChanged.emit()

    @Slot(int)
    def editSide(self, side):
        self._side = side
        ring = self._selected_ring()
        self._side_value = number(math.dist(ring[side], ring[(side + 1) % len(ring)])) if ring else ''
        self.stateChanged.emit()

    @Slot(str, result=bool)
    def commitSide(self, text):
        try:
            try:
                value = float(text.replace(',', '.'))
            except ValueError:
                raise ValueError(_('«{text}» is not a length in metres').format(text=text)) from None
            if not math.isfinite(value) or value <= 0:
                raise ValueError(_('Enter a positive length.'))
            self._run(lambda: self.editor.set_side_length(self._side, value))
            if not self._error:
                self._side = None
        except ValueError as error:
            self._error = str(error)
        self.stateChanged.emit()
        return self._side is None

    @Slot()
    def cancelSide(self):
        self._side = None
        self._error = ''
        self.stateChanged.emit()

    @Slot(float, float, float, float, float, float)
    def viewSettled(self, west, south, east, north, mpp, dpr):
        self.calls['viewSettled'] += 1
        scale_changed = mpp != self._mpp
        self._mpp = mpp
        self.drawing.metres_per_pixel = mpp
        self.editor.pick_reach = 6*mpp
        if self._maps:
            self._maps.updateView(west, south, east, north, mpp, dpr)
        if scale_changed and self.stringsVisible and self.editor.runs():
            # R541: the strings' lines and names are made again once the wheel stops (90-130 ms on Rho), not at
            # every notch a hand turns: the plan scales them meanwhile
            if self._scale_settle is None:
                from PySide6.QtCore import QTimer
                self._scale_settle = QTimer(self)
                self._scale_settle.setSingleShot(True)
                self._scale_settle.setInterval(SCALE_SETTLE_MS)
                self._scale_settle.timeout.connect(self._scale_settled)
            self._scale_settle.start()

    def _scale_settled(self):
        if not self._closed and self.stringsVisible:
            self._overlays()

    def _selected_ring(self):
        # Asked up to five times per overlay (the highlight, the labels, the grips, the bounds, the ring shown): a
        # row's ring is the rotated hull of its modules' corners, found once (R465).
        return self._memoised('_selected_ring', self._find_selected_ring)

    def _find_selected_ring(self):
        kind, oid = self.editor.selection[:2]
        if kind == 'row':
            from shapely.geometry import MultiPoint
            sfid, _, rid = oid.partition('/')
            points = [(x, -y) for m in self._scene['modules'] if m['oid'] == sfid and m['rid'] == rid
                      for x, y in m['points']]
            hull = MultiPoint(points).minimum_rotated_rectangle if points else None
            return list(hull.exterior.coords)[:-1] if hull is not None and hull.geom_type == 'Polygon' else []
        row = next((x for x in self._scene['objects'] if x['kind'] == kind and x['oid'] == oid), None)
        return [[x, -y] for x, y in row['points']] if row else []

    def _grip_ring(self):
        """The corners that can be dragged: of what the phase can take, the path of a linear object, the outline of a
        pitch drawn by hand. What was chosen elsewhere (the tree, a check's mark) has none: it is changed in its phase."""
        kind, oid = self.editor.selection[:2]
        if kind not in self.editor.selectable() or self.session.selected_many():
            return []
        if kind == 'prop':
            thing = self.session.project.prop(oid)
            return (thing.path or []) if thing is not None else []
        if kind == 'pitch':
            found = move._free_pitch(self.session.project, oid)
            return found[1]['ring'] if found else []
        return self._selected_ring() if kind in ('building', 'subfield', 'exclusion') else []

    def _memoised(self, name, make):
        memo = self._memo
        if name not in memo:
            memo[name] = make()
        return memo[name]

    def _overlays(self):
        if not hasattr(self, '_scene'):
            return
        self._memo = {}
        self._highlights, self._draft, self._labels, self._grips = [], [], [], []
        kind, oid = self.editor.selection[:2]
        widths = view_colours.WIDTHS

        def light(target, obj, colour, width, alpha):
            target.extend([{**obj, 'stroke': view_colours.PHOTO['halo'], 'width': width + widths['select_halo'],
                            'fill': colour + f'{alpha:02x}', 'dashed': False},
                           {**obj, 'stroke': colour, 'width': width, 'fill': 'transparent', 'dashed': False}])

        many = self.session.selected_many()
        for obj in self._scene['objects']:
            if ((obj['kind'], obj['oid']) == (kind, oid) or (obj['kind'], obj['oid']) in self.editor.swept_things
                    or (obj['kind'] == kind and obj['oid'] in many)):
                light(self._highlights, obj, view_colours.kind_colour(obj['kind']), widths['select'], 30)
        chosen = set(self.editor.swept)
        if kind == 'row':
            ring = self._selected_ring()
            if ring:
                light(self._highlights, dict(points=[[x, -y] for x, y in ring], closed=True),
                      view_colours.kind_colour('module'), widths['select_module'], 110)
        # R483: the strings' layers are built whatever the phase and only hidden by the plan (`stringsVisible`), so
        # coming back to Plant shows them again instead of making their seven hundred items anew.
        wiring = self.editor.wiring_scene(self._mpp, wiring_on=True, states=self._string_states)
        chosen.update(tuple(x) for x in wiring.get('highlights', []))
        if self.editor.selected_module[0]:
            chosen.add(tuple(self.editor.selected_module))
        self._light_modules(chosen, widths['select_module'], 150 if self.editor.swept else 110)
        ring = self._selected_ring()
        if ring and not self.editor.selected_module[0] and self._tool == 'select' and not many:
            self._labels = [{**p, 'y': -p['y'], 'side': p['index']} for p in side_labels(ring)]
        if self._tool == 'select':
            self._grips = [dict(index=i, x=float(x), y=float(y)) for i, (x, y) in enumerate(self._grip_ring())]
        wiring_changed, draft_changed = self._split_wiring(wiring)
        self._labels.extend(self._string_labels)
        self._labels.extend(self._draft_labels)
        band = wiring.get('band', [])
        band_changed = band != self._band
        self._band = band
        self.drawing.selected_subfield = oid if kind == 'subfield' else ''
        preview = self.preview
        rings = []
        if self._tool in EDIT_TOOLS:
            rings.extend((r, True) for r in preview.get('rings', []))
        colours = view_colours.PHOTO
        for index, (points, closed) in enumerate(rings):
            width = widths['draw'] if index == 0 else 1.2
            path = dict(kind='draft', oid='', points=[[x, -y] for x, y in points],
                        fill='transparent', closed=closed)
            ink = colours['sweep_remove'] if preview.get('refused') else colours['sel']
            self._draft.extend(({**path, 'stroke': colours['halo'], 'width': width+widths['halo']},
                                {**path, 'stroke': ink, 'width': width, 'dashed': True}))
        def guide(a, b, colour, width, dashed=False):
            self._draft.append(dict(points=[[a[0], -a[1]], [b[0], -b[1]]], stroke=colour,
                                    fill='transparent', width=width, dashed=dashed, closed=False))
        if preview.get('type') == 'side':
            # R445 phase B: the modules that would come (green) and go (red) while a side is dragged
            for corners, colour in ((preview.get('add', []), colours['sweep_crossing']),
                                    (preview.get('remove', []), colours['sweep_remove'])):
                for quad in corners:
                    self._draft.append(dict(kind='ghost', oid='', points=[[x, -y] for x, y in quad],
                                            stroke=colour, fill=colour + '66', width=1.2, dashed=False, closed=True))
        if preview.get('type') == 'transform':
            if preview.get('mode') == 'rotate':
                centre = preview['pivot']
                if preview.get('start') is not None:
                    guide(centre, preview['start'], colours['guide'], 1, True)
                guide(centre, preview['pointer'], colours['draw'], widths['draw'])
            elif preview.get('base') is not None:
                a = preview['base']
                b = [a[0]+preview['dx'], a[1]+preview['dy']]
                guide(a, b, colours['halo'], widths['draw']+widths['halo'])
                guide(a, b, colours['draw'], widths['draw'], True)
        if self.placer.active:
            self._ghost(colours, widths)
        if self.collector.hover:
            _kind, _oid, ring, side = self.collector.hover
            self._draft.append(dict(points=[[x, -y] for x, y in [ring[side], ring[(side+1) % len(ring)]]],
                                    stroke='#ffb000', fill='transparent', width=3, closed=False))
        key = (self._highlights, self._draft, self._labels, self._grips, self._lit, kind, oid, self._tool)
        if self._moving and key == self._overlay_key and not wiring_changed and not draft_changed:
            # the pointer moved over nothing new: the band alone (R496), the rest of the plan is left in peace
            if band_changed:
                self.bandChanged.emit()
            return
        self._overlay_key = key
        self._highlights, self._draft = qml_objects(self._highlights), qml_objects(self._draft)
        self.overlayChanged.emit()
        if wiring_changed:
            self.wiringChanged.emit()
        if draft_changed:
            self.draftChanged.emit()
        if band_changed:
            self.bandChanged.emit()

    def _ghost(self, colours, widths):
        """R454: the model being placed, as the plan will have it: the bodies' outlines (red over a building already
        drawn), their roof planes, obstacles and supports; the corner or side that took it."""
        from meridiana import ifc_place
        placer = self.placer
        rings = placer.outlines()
        over = bool(ifc_place.overlaps_rings(self.session.project, [r for k, r in rings if k == 'building']))
        ink = colours['sweep_remove'] if over else colours['sel']
        for kind, ring in rings:
            path = dict(kind='ghost', oid='', points=[[x, -y] for x, y in ring], closed=True)
            if kind == 'building':
                self._draft.extend(({**path, 'stroke': colours['halo'], 'fill': 'transparent',
                                     'width': widths['draw'] + widths['halo'], 'dashed': False},
                                    {**path, 'stroke': ink, 'fill': ink + '26', 'width': widths['draw'], 'dashed': False}))
            else:
                self._draft.append({**path, 'stroke': ink, 'fill': 'transparent', 'width': 1.0, 'dashed': kind == 'roof'})
        if placer.snap.point is not None:
            x, y = placer.snap.point
            r = 5 * self._mpp
            self._draft.append(dict(kind='ghost', oid='', points=[[x - r, -y - r], [x + r, -y - r], [x + r, -y + r],
                                                                  [x - r, -y + r]],
                                    stroke=colours['draw'], fill='transparent', width=2.0, dashed=False, closed=True))

    def _split_wiring(self, wiring):
        """The wiring scene into the plan's layers: the finished strings (lines, fills, dots, names, optimizers), the
        modules in no string (red) and the draft (what the hand is drawing). A layer is converted again only when
        its content changed, so a module added to the draft leaves the finished strings' native paths as they are,
        and a move of the pointer leaves everything (R496). Returns (finished changed, draft changed)."""
        objects = wiring.get('objects', [])
        if objects is self._wiring_seen:
            return False, False
        self._wiring_seen = objects
        dots, labels = wiring.get('dots', []), wiring.get('labels', [])
        layers = {
            'wires': [o for o in objects if not o.get('draft') and o['kind'] not in ('string_fill', 'unwired')],
            'wireFills': [o for o in objects if not o.get('draft') and o['kind'] == 'string_fill'],
            'unwired': [o for o in objects if o['kind'] == 'unwired'],
            'dots': [d for d in dots if not d.get('draft')],
            'stringLabels': [p for p in labels if not p.get('draft')],
            'optimizerPaths': wiring.get('optimizers', []),
            'level': (wiring.get('level', 'near'), float(wiring.get('size', 1.0) or 1.0)),
            'draftWires': [o for o in objects if o.get('draft') and o['kind'] != 'string_fill'],
            'draftFills': [o for o in objects if o.get('draft') and o['kind'] == 'string_fill'],
            'draftDots': [d for d in dots if d.get('draft')],
            'draftLabels': [p for p in labels if p.get('draft')],
            'draftColour': wiring.get('draftColour', ''),
        }
        seen = self._wiring_finished or {}
        changed = {name for name, value in layers.items() if value != seen.get(name)}
        self._wiring_finished = layers
        if 'wires' in changed:
            self._wires = qml_objects(layers['wires'])
        if 'wireFills' in changed:
            self._wire_quads = qml_objects(layers['wireFills'])
        if 'unwired' in changed:
            self._unwired = qml_objects(layers['unwired'])
        if 'dots' in changed:
            self._dots = layers['dots']
        if 'stringLabels' in changed:
            self._string_labels = layers['stringLabels']
        if 'optimizerPaths' in changed:
            self._optimizer_paths = layers['optimizerPaths']
        if 'level' in changed:
            self._wiring_level, self._module_size = layers['level']
        if 'draftWires' in changed:
            self._draft_wires = qml_objects(layers['draftWires'])
        if 'draftFills' in changed:
            self._draft_quads = qml_objects(layers['draftFills'])
        self._draft_dots, self._draft_labels, self._draft_colour = layers['draftDots'], layers['draftLabels'], layers['draftColour']
        draft_changed = bool(changed & {'draftWires', 'draftFills', 'draftDots', 'draftLabels', 'draftColour'})
        unwired_changed = 'unwired' in changed
        if unwired_changed:
            self.unwiredChanged.emit()
        return bool(changed - {'draftWires', 'draftFills', 'draftDots', 'draftLabels', 'draftColour', 'unwired'}), draft_changed

    def install(self, engine):
        from .controls import install_controls
        install_controls(engine)
        register_paths()
        engine.addImportPath(str(Path(__file__).parents[1] / 'qml'))
        if self._maps:
            self._maps.install(engine)
        if self.scheduler and not self.session.results and any(s.filled for s in self.session.project.subfields):
            self.scheduler.request()

    def close(self):
        self._closed = True
        self.shadow_scheduler.close()
        if self._source_editor:
            self._source_editor.close()
        if self._changed in self.session.listeners:
            self.session.listeners.remove(self._changed)
        if self.scheduler:
            self.scheduler.close()
        if self._maps:
            self._maps.close()
