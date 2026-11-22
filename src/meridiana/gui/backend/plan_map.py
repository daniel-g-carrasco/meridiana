"""The sun map in the plan (study 45, package 5): the one Qt bridge between the map's state (app/sun_map.SunMap, without
Qt, shared with the 3D) and the plan's QML (Plan/SunMapLayer.qml, Plan/SunMapPanel.qml, Controls/MapLegend.qml).

What it gives the QML, all bound, never written into it (rule 7):
- `on`, `busy`, `quantity`, `colour`, `day`: the state, with the slots of the button and of the panel;
- `surfaces`: a list model, one row per surface of the plan: its image (an image://sunmap/ url, painted here from the
  classes of the quantity chosen with the scale's colours, cut on the surface's contour so that the tiles of the border
  never leave it, the tiles under an obstacle hatched: the same picture on every renderer, the software one of the
  captures off screen too), the matrix that lays the image's pixels on the plan, the contour (the veil of a map to be
  updated), and the number written on it (its irradiance without the shadows, decision 1). A surface that changes is
  one row changed: the others are not drawn again;
- `modulePaths`: the modules laid, coloured by class (decision 2), joined in a few paths for the plan's ModuleBatch;
- `legend`: the title, the shades, the limits and the notes of the legend;
- `pointerText`: the figures under the pointer (SunMap.value_at, or the module's own).

Every call comes on the window's thread; what SunMap tells comes inside Center.pump and is only queued there: it is
drawn a piece per turn of the events (the rows' plan, one surface, the modules, the legend), each piece and each gesture
timed by the jobs' Center (Center.timed), so that the guard of the window (study 48, chapter 5) sees them. What a
picture owes to the geometry (the cut on the contour, the hatch) comes made from the job's process with its level
(app/sun_map_image.py): here only the colours are laid, with NumPy. Colours: theme_colors.SUN_MAP, the one place of the
scales (Theme.colors.sun_map in the QML)."""

from __future__ import annotations

import threading

import numpy as np
from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, QObject, QPointF, QTimer, Property, Qt, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider

from meridiana.app import irradiance_job as job
from meridiana.app import sun_map as sm
from meridiana.app.interface import theme_colors, view_colours
from meridiana.core.energy import irradiance_map as im
from meridiana.i18n import _, number

from .parts import Part

PROVIDER = 'sunmap'                     # image://sunmap/<key>
DAYS = (((12, 21), 'december'), ((6, 21), 'june'), ((3, 20), 'equinox'))
CHUNK = 1000                            # module paths joined in one native path at most (plan_paths.batches)
LINE = 253                              # the index of the hatch's lines in the table (im.UNDER is its ground)


def _argb(colour: str) -> int:
    h = colour.lstrip('#')
    alpha = int(h[6:8], 16) if len(h) == 8 else 255
    return (alpha << 24) | int(h[0:6], 16)


def palette(scale: str, quantity: str, classes: int) -> list[str]:
    """The colour of each class of the quantity, in order (theme_colors.sun_tones)."""
    tones = theme_colors.sun_tones(classes, quantity != 'loss')
    return [theme_colors.SUN_MAP[f'{scale}_{t}'] for t in tones]


def lut(colours: list[str]) -> np.ndarray:
    """256 colours as QImage's ARGB32 words: index i < len(colours) its class's colour, im.UNDER the ground of the
    hatch, LINE its lines; the rest (im.OUTSIDE) transparent."""
    out = np.zeros(256, dtype=np.uint32)
    for i, colour in enumerate(colours):
        out[i] = _argb(colour)
    out[im.UNDER] = _argb(theme_colors.SUN_MAP['under'])
    out[LINE] = _argb(theme_colors.SUN_MAP['under_line'])
    return out


def image_of(classes: np.ndarray, table: np.ndarray, raster: dict) -> tuple[QImage, np.ndarray]:
    """The picture of a level: its tiles in their colours, `k` pixels a side each, cut on the contour and hatched
    under the obstacles as the job's raster says (app/sun_map_image.py: the geometry is made there, never here). Only
    NumPy on the window's thread: the classes spread over their pixels, the table, the raster's indices. (QImage, the
    words it reads: they live as long as the image is in use.)"""
    k = raster['k']
    flat = classes.repeat(k, 0).repeat(k, 1).reshape(-1)
    flat[raster['lines']] = LINE
    words = table[flat]
    words[raster['clear']] = 0
    words.view(np.uint8).reshape(-1, 4)[raster['edge'], 3] = raster['alpha']
    height, width = raster['size']
    return QImage(words.data, width, height, width * 4, QImage.Format.Format_ARGB32), words


def grid_outline(surface: sm.SurfaceMap, level: dict) -> np.ndarray:
    """The surface's contour on the columns and rows of a level's grid."""
    return np.asarray(surface.outline, dtype=float) / level['step'] - (level['iu'], level['iv'])


def plan_matrix(surface: sm.SurfaceMap, level: dict, k: int = 1) -> list[float]:
    """[a, b, tx, c, d, ty]: the item's point (x, -y) of the plan of the pixel (px, py) of the level's image, `k`
    pixels a tile, is (a px + b py + tx, c px + d py + ty) (SurfaceMap.transform, North made down as the plan draws
    it)."""
    x0, y0, ax, ay, bx, by = surface.transform(level)
    return [ax / k, bx / k, x0, -ay / k, -by / k, -y0]


class SunMapImages(QQuickImageProvider):
    """The surfaces' images by key; the QML asks image://sunmap/<key>. Written on the window's thread, read where Qt
    asks (under a lock: an asynchronous image would be read elsewhere)."""

    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._images: dict[str, QImage] = {}
        self._lock = threading.Lock()

    def put(self, key: str, image: QImage, old: str = '') -> None:
        with self._lock:
            self._images[key] = image
            if old and old != key:
                self._images.pop(old, None)

    def drop(self, keep: set) -> None:
        with self._lock:
            for key in [k for k in self._images if k not in keep]:
                del self._images[key]

    def requestImage(self, identifier, size, requestedSize):
        with self._lock:
            image = self._images.get(identifier)
        if image is None:
            image = QImage(1, 1, QImage.Format.Format_RGBA8888)
            image.fill(Qt.GlobalColor.transparent)
        size.setWidth(image.width())
        size.setHeight(image.height())
        return image.copy()         # Qt keeps it after the words of the bridge's picture are gone (image_of)


ROLES = ('sid', 'source', 'ring', 'matrix', 'cols', 'rows', 'scale', 'coloured', 'under', 'stale', 'label', 'cx', 'cy')


class SurfaceModel(QAbstractListModel):
    """One row per surface of the plan, in the plan's order (rows: dicts with ROLES)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows: list[dict] = []

    def roleNames(self):
        return {Qt.ItemDataRole.UserRole + i: QByteArray(name.encode()) for i, name in enumerate(ROLES)}

    def rowCount(self, parent=None):
        return 0 if parent is not None and parent.isValid() else len(self.rows)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.rows):
            return None
        name = ROLES[role - Qt.ItemDataRole.UserRole] if 0 <= role - Qt.ItemDataRole.UserRole < len(ROLES) else None
        return self.rows[index.row()].get(name) if name else None

    def reset(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def insert(self, i: int, row: dict) -> None:
        self.beginInsertRows(QModelIndex(), i, i)
        self.rows.insert(i, row)
        self.endInsertRows()

    def remove(self, i: int) -> None:
        self.beginRemoveRows(QModelIndex(), i, i)
        del self.rows[i]
        self.endRemoveRows()

    def change(self, i: int, row: dict) -> None:
        """The row again, told with the roles that changed only: each role told has its delegates' bindings evaluated
        again (the contour's box on screen, the image's matrix), and a new picture or new words must not cost the
        others."""
        old = self.rows[i]
        roles = [Qt.ItemDataRole.UserRole + k for k, name in enumerate(ROLES) if old.get(name) != row.get(name)]
        if roles:
            self.rows[i] = row
            at = self.index(i, 0)
            self.dataChanged.emit(at, at, roles)

    @Slot(int, result='QVariantMap')
    def get(self, i):
        return self.rows[i] if 0 <= i < len(self.rows) else {}


class PlanMapBackend(QObject):
    """The sun map's bridge for the plan: see the module's text. `sun` the SunMap, `center` its jobs' Center (the
    bar's rows tell when the job ends or is cancelled from the bar)."""
    changed = Signal()
    modulesChanged = Signal()
    legendChanged = Signal()
    pointerChanged = Signal()

    def __init__(self, sun: sm.SunMap, center=None, parent=None):
        super().__init__(parent)
        self.sun, self.center = sun, center
        self.images = SunMapImages()
        self.model = SurfaceModel(self)
        self._keys: dict[str, str] = {}             # surface id -> the key of its image now
        self._made: dict[str, tuple] = {}           # surface id -> (what its image shows, the row's part of it)
        self._rings: dict[str, tuple] = {}          # surface id -> (its SurfaceMap, its contour for the QML, centre)
        self._serial = 0
        self._order: list[str] = []
        self._edges = None
        self._legend: dict = {'visible': False}
        self._module_paths: list = []
        self._outlines: dict = {}                   # (sub-field, module key) -> its path on the plan, once per scene
        self._pointer = ''
        self.last = (0.0, 0.0)                      # the plan's point the pointer was last at
        self._busy = sun.busy
        self._shown = None                          # the state `changed` last told (_state_again)
        self._closed = False
        self.plan = None
        self._queue: list[tuple] = []               # what is still to draw, a piece per turn (_turn)
        self._queued: set = set()
        self._turns = QTimer(self)
        self._turns.setSingleShot(True)
        self._turns.setInterval(0)
        self._turns.timeout.connect(self._turn)
        sun.subscribe(self._told)
        if center is not None:
            center.subscribe(self._rows)

    # what the QML binds

    @Property(bool, notify=changed)
    def on(self):
        return self.sun.on

    @Property(bool, notify=changed)
    def busy(self):
        return self._busy

    @Property(str, notify=changed)
    def quantity(self):
        return self.sun.quantity

    @Property(str, notify=changed)
    def colour(self):
        return self.sun.colour

    @Property(str, notify=changed)
    def day(self):
        return f'{self.sun.day[0]:02d}-{self.sun.day[1]:02d}'

    @Property(str, notify=changed)
    def scale(self):
        return self.sun.scale

    @Property(QObject, constant=True)
    def surfaces(self):
        return self.model

    @Property('QVariantList', notify=modulesChanged)
    def modulePaths(self):
        return self._module_paths

    @Property('QVariantMap', notify=legendChanged)
    def legend(self):
        return self._legend

    @Property(str, notify=pointerChanged)
    def pointerText(self):
        return self._pointer

    @Property('QVariantMap', constant=True)
    def texts(self):
        if not hasattr(self, '_texts'):
            self._texts = {
                'button': _('Sun map'), 'title': _('Sun map'), 'quantity': _('Show'), 'colour': _('Colour'),
                'day': _('Day of the hours of sun'), 'stale': _('to be updated'),
                'tip': _('Sun map: the loss to the shadows on the roofs and on the modules'),
                'quantities': [{'value': 'loss', 'text': _('Loss %')}, {'value': 'year', 'text': _('kWh/m²')},
                               {'value': 'hours', 'text': _('Hours of sun')}],
                'colours': [{'value': 'auto', 'text': _('Automatic')}, {'value': 'surfaces', 'text': _('Roofs')},
                            {'value': 'modules', 'text': _('Modules')}],
                'days': [{'value': f'{d[0]:02d}-{d[1]:02d}', 'label': sm.day_text(d) if name != 'equinox'
                          else _('Equinoxes ({day})').format(day=sm.day_text(d))} for d, name in DAYS],
            }
        return self._texts

    # the gestures

    @Slot()
    def toggle(self):
        self.setOn(not self.sun.on)

    @Slot(bool)
    def setOn(self, on):
        self._timed('sun_map.on', self._turn_on, bool(on))

    def _turn_on(self, on):
        self.sun.set_on(on)
        if not on:
            self._set_pointer('')
        self._state()

    @Slot(str)
    def setQuantity(self, quantity):
        self._timed('sun_map.quantity', self.sun.set_quantity, quantity)

    @Slot(str)
    def setColour(self, colour):
        self._timed('sun_map.colour', self.sun.set_colour, colour)

    @Slot(str)
    def setScale(self, scale):
        self._timed('sun_map.scale', self.sun.set_scale, scale)

    @Slot(str)
    def setDay(self, day):
        self._timed('sun_map.day', self.sun.set_day, sm.day_of(day))
        self._timed('sun_map.state', self._state)

    @Slot(float, float, str, str)
    def point(self, x, y, subfield='', key=''):
        """The pointer at the plan's (x, y) (North up), over the module `key` of `subfield` when there is one."""
        self._timed('sun_map.pointer', self._point, x, y, subfield, key)

    def _point(self, x, y, subfield, key):
        self.last = (x, y)
        if not self.sun.on:
            return self._set_pointer('')
        found = self.sun.module_at(subfield, key) if subfield and self.sun.modules else None
        if found is None:
            found = self.sun.value_at(x, y)
        self._set_pointer(self._figures(found) if found else '')

    @Slot()
    def leave(self):
        self._set_pointer('')

    def _figures(self, found: dict) -> str:
        """«loss 3,2 % · 1412 kWh/m² · 6,5 h on 21 December»."""
        return _('loss {loss} %  ·  {year} kWh/m² a year  ·  {hours} h on {day}').format(
            loss=number(found['loss'], 1), year=number(found['year'], 0), hours=number(found['hours'], 1),
            day=sm.day_text(self.sun.day))

    def _set_pointer(self, text):
        if text != self._pointer:
            self._pointer = text
            self.pointerChanged.emit()

    # what SunMap tells, inside Center.pump: noted, drawn a piece per turn of the events, each piece timed

    def _rows(self):
        if not self._closed:
            self._timed('sun_map.state', self._state)

    def _timed(self, name, function, *args):
        """A piece of the bridge's work on the window's thread, timed by the jobs' Center under `name`, so that the
        guard of the window (Center.stats) sees it as it sees a delivery."""
        if self.center is None:
            return function(*args)
        return self.center.timed(name, function, *args)

    def _state(self):
        """The state at once; the legend, when the job began or ended, on a turn of its own (shown inside the gesture
        it made sun_map.on 1,2-1,4 ms longer, off screen, 14/11/2026)."""
        busy = self.sun.busy
        if busy != self._busy:
            self._busy = busy
            if not self._closed:
                self._queue_add(('legend',))
                if not self._turns.isActive():
                    self._turns.start()
        self._state_again()

    def _state_again(self):
        """`changed` only when what it notifies changed: each emit has the QML evaluate again every binding on the
        state (on, busy, quantity, colour, day, scale), and a turn that changed none of them must cost the window
        nothing (sun_map.legend 5,5-6,4 ms on screen, model A and Rho, 14/11/2026, with an emit at every turn)."""
        state = (self.sun.on, self._busy, self.sun.quantity, self.sun.colour, self.sun.day, self.sun.scale)
        if state != self._shown:
            self._shown = state
            self.changed.emit()

    def _told(self, what: set):
        """SunMap's word, often inside Center.pump: only queued here. Each piece of what it asks (the plan of the
        rows, one surface, the modules, the legend) is done on a turn of its own (_turn), so that no turn of the
        window's thread holds more than one surface's picture."""
        if self._closed or not what:
            return
        everything = sm.EVERYTHING in what
        if everything or list(self.sun.surfaces) != self._order:
            self._queue_add(('plan',))
            for sid in self.sun.surfaces:
                self._queue_add(('surface', sid))
        else:
            for sid in what:
                if sid in self.sun.surfaces:
                    self._queue_add(('surface', sid))
        if everything or sm.MODULES in what:
            self._queue_add(('modules',))
        self._queue_add(('legend',))
        if not self._turns.isActive():
            self._turns.start()

    def _queue_add(self, task: tuple) -> None:
        if task not in self._queued:
            self._queued.add(task)
            self._queue.append(task)

    @property
    def drawing(self) -> bool:
        """Whether what SunMap told is still being drawn."""
        return bool(self._queue)

    def _turn(self):
        if self._closed or not self._queue:
            return
        task = self._queue.pop(0)
        self._queued.discard(task)
        work = {'plan': self._plan, 'surface': self._surface, 'modules': self._paint_modules,
                'legend': self._legend_and_state}[task[0]]
        self._timed(f'sun_map.{task[0]}', work, *task[1:])
        if self._queue:
            self._turns.start()

    def _plan(self):
        """The rows follow the plan's surfaces: those gone are taken out, the new ones come one per turn (_surface);
        the others keep their picture meanwhile (nothing blinks)."""
        order = list(self.sun.surfaces)
        if order == self._order:
            return
        self._order = order
        for i in reversed(range(len(self.model.rows))):
            if self.model.rows[i]['sid'] not in self.sun.surfaces:
                self.model.remove(i)
        self._made = {k: v for k, v in self._made.items() if k in self.sun.surfaces}
        self._rings = {k: v for k, v in self._rings.items() if k in self.sun.surfaces}
        self.images.drop({self._keys[k] for k in self._made if k in self._keys})

    def _surface(self, sid: str):
        """One surface, in at most three turns of the window, each one piece: a new picture is painted on its turn and
        given to the QML on the next; a new row is born without its words, which come on the next turn (its pill is
        made then). Painting, the row and the pill together held the window's thread 5-8,6 ms off screen
        (sun_map.surface, test_sun_map, 14/11/2026: image_of 1-3 ms, a new row with its pill 2,3-8,6 ms)."""
        if sid not in self.sun.surfaces:
            return
        if self._paint(sid):
            self._queue_add(('surface', sid))
            return
        row = self._row(sid)
        at = next((i for i, r in enumerate(self.model.rows) if r['sid'] == sid), None)
        if at is not None:
            self.model.change(at, row)
            return
        place = self._order.index(sid) if sid in self._order else len(self._order)
        before = sum(1 for r in self.model.rows if r['sid'] in self._order and self._order.index(r['sid']) < place)
        self.model.insert(before, dict(row, label=''))
        if row['label']:
            self._queue_add(('surface', sid))

    def _legend_and_state(self):
        """The legend, and the rows again when the limits of the classes moved (kWh/m² and hours: they follow the
        figures shown, SunMap.edges)."""
        edges = self.sun.edges() if self.sun.surfaces else None
        if edges != self._edges:
            moved = self._edges is not None
            self._edges = edges
            if moved:
                for sid in self.sun.surfaces:
                    self._queue_add(('surface', sid))
                if self.sun.modules:
                    self._queue_add(('modules',))
        self._legend_again()
        self._busy = self.sun.busy
        self._state_again()

    def _sign(self, sid: str) -> tuple:
        """(the level, what the surface's picture shows: the level, the quantity, the scale, the limits), or (None,
        None) when it shows none."""
        sun, s = self.sun, self.sun.surfaces[sid]
        level = sun.level_of(sid)
        if level is None or not (sun.on and sun.layers(sid)[0]):
            return None, None
        return level, (s.shown, s.fine, sun.quantity, sun.scale, tuple(sun.edges()))

    def _paint(self, sid: str) -> bool:
        """The surface's picture painted again (a new key, so the QML loads it) only when what it shows changed:
        whether it was."""
        level, sign = self._sign(sid)
        made = self._made.get(sid)
        if sign is None or (made is not None and made[0] == sign):
            return False
        sun, s = self.sun, self.sun.surfaces[sid]
        classes = sun.classes_of(sid)
        raster = level.get('raster')
        if classes is None or raster is None:
            return False
        image, _words = image_of(classes, lut(palette(sun.scale, sun.quantity, len(sign[4]) - 1)), raster)
        self._serial += 1
        key = f'{self._serial}'
        self.images.put(key, image, self._keys.get(sid, ''))
        self._keys[sid] = key
        height, width = raster['size']
        self._made[sid] = (sign, dict(source=f'image://{PROVIDER}/{key}', matrix=plan_matrix(s, level, raster['k']),
                                      cols=width, rows=height, scale=raster['k'], coloured=True,
                                      under=bool((classes == im.UNDER).any())))
        return True

    def _row(self, sid: str) -> dict:
        """The row of a surface, with the picture _paint made for what it shows now (none while it is not made)."""
        sun, s = self.sun, self.sun.surfaces[sid]
        found = self._rings.get(sid)
        if found is None or found[0] is not s:          # the contour made once for each surface of the plan
            xy = s.xy if s.xy is not None else np.asarray(s.ring, dtype=float).reshape(-1, 2)
            found = self._rings[sid] = (s, [QPointF(float(x), -float(y)) for x, y in xy],
                                        *((float(v) for v in xy.mean(axis=0)) if len(xy) else (0.0, 0.0)))
        _s, ring, cx, cy = found
        row = dict(sid=sid, source='', ring=ring, matrix=[1.0, 0.0, 0.0, 0.0, 1.0, 0.0], cols=1, rows=1, scale=1,
                   coloured=False, under=False, stale=s.stale or sun.changing, label=self._label(s), cx=cx, cy=cy)
        _level, sign = self._sign(sid)
        made = self._made.get(sid)
        if sign is not None and made is not None and made[0] == sign:
            row.update(made[1])
        return row

    def _label(self, s: sm.SurfaceMap) -> str:
        """What is written on a surface: its irradiance without the shadows (decision 1) and, with modules on it,
        theirs on their own plane; «to be updated» under them when it shows an old map."""
        free = s.free
        if free is None and s.shown is not None:            # to be updated: the number of the map it still shows
            level = self.sun.levels.get(s.shown)
            free = level.get('free') if level else None
        if not self.sun.on or free is None:
            return ''
        lines = [_('{value} kWh/m² a year without shadows').format(value=number(free, 0))]
        arrays = self.sun.modules.get(s.id, ())
        if arrays and self.sun.layers(s.id)[1]:
            a = arrays[0]
            # R564 point 9: without shadows as the line above, said in its words (the value is `free`)
            lines.append(_('modules ({tilt}°): {value} kWh/m² a year without shadows').format(
                tilt=number(a['tilt'], 0), value=number(a['free'], 0)))
        if s.stale or self.sun.changing:
            lines.append(self.texts['stale'])
        return '\n'.join(lines)

    def _legend_again(self):
        sun = self.sun
        if not sun.on or not sun.surfaces:
            legend = {'visible': False}
        else:
            data = sun.legend()
            edges = data['edges']
            digits = 0 if all(float(e).is_integer() for e in edges) else 1
            legend = {'visible': True, 'title': f"{data['title']} ({data['unit']})",
                      'tones': theme_colors.sun_tones(len(edges) - 1, sun.quantity != 'loss'),
                      'scale': sun.scale, 'limits': [number(e, digits) for e in edges],
                      'notes': [', '.join(data['planes'])] if data['planes'] else []}
        if legend != self._legend:
            self._legend = legend
            self.legendChanged.emit()

    # the modules

    def follow_plan(self, plan) -> None:
        """The plan's controller: its modules' outlines, taken once per scene (their keys are SunMap's)."""
        self.plan = plan
        plan.modulesChanged.connect(self._scene)      # R598: only when the modules changed
        self._scene()

    def _scene(self):
        if self._closed or self.plan is None:
            return
        out = {}
        for m in self.plan.modules:
            points = [(p.x(), p.y()) for p in m['points']]
            if points:
                out[(str(m['oid']), str(m['key']))] = 'M' + ' L'.join(f'{x:.8g},{y:.8g}' for x, y in points) + ' Z'
        self._outlines = out
        self._timed('sun_map.modules', self._paint_modules)

    def _paint_modules(self):
        sun, paths = self.sun, []
        if sun.on and sun.modules and self._outlines:
            edges = sun.edges()
            colours = palette(sun.scale, sun.quantity, len(edges) - 1)
            if sun.modules_stale or sun.changing:
                veil = theme_colors.SUN_MAP['stale']
                colours = [theme_colors.mix(c, veil[:7], int(veil[7:9], 16) / 255) for c in colours]
            groups: dict[int, list] = {}
            for sid, arrays in sun.modules.items():
                if sid in sun.surfaces and not sun.layers(sid)[1]:
                    continue
                for a in arrays:
                    classes = sun.module_classes(a)
                    for key, k in zip(a['keys'], classes.tolist(), strict=True):
                        path = self._outlines.get((a['subfield'], key))
                        if path is not None and k < len(colours):
                            groups.setdefault(k, []).append(path)
            stroke = theme_colors.qt_hex(theme_colors.OVERLAY['module_line'])
            width = view_colours.WIDTHS['module_line']
            for k, found in sorted(groups.items()):
                for start in range(0, len(found), CHUNK):
                    paths.append(dict(fill=colours[k], stroke=stroke, width=width, dashed=False,
                                      path=' '.join(found[start:start + CHUNK])))
        if paths != self._module_paths:
            self._module_paths = paths
            self.modulesChanged.emit()

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._turns.stop()
        if self.plan is not None:
            try:
                self.plan.modulesChanged.disconnect(self._scene)
            except (RuntimeError, TypeError):
                pass            # the plan already gone with its window: nothing left connected
        self.sun.close()


def install(engine, session, cache, window):
    """The sun map of the window (`sunMap` for the QML), on the jobs' Center of the window (work.py): its weather is
    the cache's, its levels kept in the cache's store; the plan's modules followed once the plan is there."""
    work = window.parts.controllers.get('work') if getattr(window, 'parts', None) else None
    center = work.center if work is not None else None
    sun = sm.SunMap(center, session, cache, job.store_of(cache), getattr(window, 'cfg', None))
    backend = PlanMapBackend(sun, center)
    engine.addImageProvider(PROVIDER, backend.images)
    engine.rootContext().setContextProperty('sunMap', backend)

    def bind(_root):
        plan = getattr(window, 'plan', None)
        if plan is not None:
            backend.follow_plan(plan)
    return Part('sun-map', controllers={'sunMap': backend}, bind=bind, close=backend.close)
