"""A measured, coarse-grained QML boundary over the unchanged project session."""
from __future__ import annotations

import copy
import math
import time
from collections import Counter
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, Property, QRunnable, QThreadPool, QTimer, Signal, Slot

from meridiana import checks, jobs, log, model
from meridiana.energy import pipeline
from meridiana.i18n import _, number
from meridiana.session import ProjectSession


class Signals(QObject):
    layout = Signal(int, object, object)
    finished = Signal(int, object, object, object)


class Compute(QRunnable):
    """One snapshot, no access to a live QObject from the worker."""
    def __init__(self, generation, project, known, cache):
        super().__init__()
        self.generation, self.project = generation, project
        self.known, self.cache = known, cache
        self.signals = Signals()

    def run(self):
        start = time.perf_counter()
        try:
            results, keys, _laid = jobs.layout_of(self.project, self.known)
            self.signals.layout.emit(self.generation, results, keys)
            good = {k: v for k, v in results.items() if not isinstance(v, Exception)}
            energy = pipeline.compute(self.project, good, self.cache, fetch=False).as_dict()
            self.signals.finished.emit(self.generation, energy, [],
                                       {'worker_ms': (time.perf_counter() - start) * 1000})
        except Exception as error:  # Worker boundary: the window displays the failure.
            self.signals.finished.emit(self.generation, {}, [], {'error': str(error)})


class LayoutSignals(QObject):
    layout = Signal(int, object, object)


class Layout(QRunnable):
    """The layouts alone, after a change of the plant (R443): the year is not computed again, it is marked out of
    date until the designer asks for it."""
    def __init__(self, generation, project, known):
        super().__init__()
        self.generation, self.project, self.known = generation, project, known
        self.signals = LayoutSignals()

    def run(self):
        try:
            results, keys, _laid = jobs.layout_of(self.project, self.known)
        except Exception as error:  # noqa: BLE001 (a thread's boundary: said, not lost)
            log.complain('layout', error)
            return
        self.signals.layout.emit(self.generation, results, keys)


class CheckSignals(QObject):
    finished = Signal(int, object, str)


class CheckJob(QRunnable):
    """Checks use the current names and retain layout failures, without recomputing energy."""
    def __init__(self, serial, project, results, energy):
        super().__init__()
        self.serial, self.project, self.results, self.energy = serial, project, results, energy
        self.signals = CheckSignals()

    def run(self):
        try:
            rows = [vars(item) for item in checks.gather(self.project, self.results, self.energy)]
            self.signals.finished.emit(self.serial, rows, '')
        except Exception as error:  # Worker boundary: surfaced in the window.
            self.signals.finished.emit(self.serial, [], str(error))


class Bridge(QObject):
    sceneChanged = Signal()
    objectsChanged = Signal()
    selectionChanged = Signal()
    checksChanged = Signal()
    yearChanged = Signal()
    stateChanged = Signal()

    def __init__(self, project, cache: Path, parent=None):
        super().__init__(parent)
        self.session = ProjectSession(project)
        self.cache = cache
        self.calls = Counter()
        self.emissions = Counter()
        self._scene, self._objects, self._checks, self._year = [], [], [], {}
        self._rings, self._module_count = [], 0
        self._selection, self._bounds = {}, [0., 0., 100., 100.]
        self._error, self._busy = '', False
        self._year_note = ''
        self._filter = 'all'
        self._enabled = False
        self._pending = False
        self._job = None
        self._layout_job = None
        self._year_generation = None            # the session's generation the year on its way was asked at
        self._year_energy_generation = None     # and the session's energy generation it will answer
        self._check_serial = 0
        self._check_jobs = {}
        self.metrics = {}
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(120)
        self.timer.timeout.connect(self._launch)
        self.layout_timer = QTimer(self)
        self.layout_timer.setSingleShot(True)
        self.layout_timer.setInterval(120)
        self.layout_timer.timeout.connect(self._launch_layout)
        self.session.subscribe(self._changed)
        self._rebuild_objects()
        self._rebuild_scene()
        self._refresh_selection()

    def _get(self, name, value):
        self.calls['get:' + name] += 1
        return value

    def _emit(self, name):
        self.emissions[name] += 1
        getattr(self, name).emit()

    @Property('QVariantList', notify=sceneChanged)
    def scene(self):
        if self._scene is None:         # made when read: no view of the window reads it (study 41)
            self._scene = [{'kind': kind, 'oid': oid, 'key': key, 'points': self._points(ring)}
                           for kind, oid, key, ring in self._rings]
        return self._get('scene', self._scene)

    @Property('QVariantList', notify=sceneChanged)
    def bounds(self):
        return self._get('bounds', self._bounds)

    @Property(int, notify=sceneChanged)
    def moduleCount(self):
        return self._get('moduleCount', self._module_count)

    @Property('QVariantList', notify=objectsChanged)
    def objects(self):
        return self._get('objects', self._objects)

    @Property('QVariantMap', notify=selectionChanged)
    def selection(self):
        return self._get('selection', self._selection)

    @Property('QVariantList', notify=checksChanged)
    def checkRows(self):
        return self._get('checkRows', [r for r in self._checks if self._filter == 'all' or r['level'] == self._filter])

    @Property('QVariantMap', notify=yearChanged)
    def year(self):
        return self._get('year', self._year)

    @Property(bool, notify=stateChanged)
    def busy(self):
        return self._get('busy', self._busy or self.timer.isActive() or bool(self._check_jobs))

    @Property(str, notify=stateChanged)
    def error(self):
        return self._get('error', self._error)

    @Property(str, notify=stateChanged)
    def yearNote(self):
        """What the year has to say for itself («Lay the modules first»): for the result pages, not an error (M15)."""
        return self._year_note

    @Property(bool, notify=stateChanged)
    def canUndo(self):
        return self._get('canUndo', self.session.undo.can_undo())

    def selected_object(self):
        kind, oid = self.session.selection
        seq = self.session.project.buildings if kind == 'building' else self.session.project.subfields
        return next((obj for obj in seq if obj.id == oid), None)

    def _refresh_selection(self):
        obj = self.selected_object()
        kind, oid = self.session.selection
        ring = getattr(obj, 'footprint', getattr(obj, 'ring', []))
        self._selection = {'kind': kind, 'oid': oid, 'key': self.session.selected_module[1],
                           'name': obj.name if obj else self.session.project.name,
                           'height': getattr(obj, 'height', 0.), 'points': self._points(ring),
                           'rectangle': kind == 'building' and self._axis_aligned(ring),
                           'editable': obj is not None}
        self._emit('selectionChanged')

    def _rebuild_objects(self):
        p = self.session.project
        self._objects = [{'kind': kind, 'oid': obj.id, 'name': obj.name}
                         for kind, seq in [('building', p.buildings), ('subfield', p.subfields)] for obj in seq]
        self._emit('objectsChanged')

    @staticmethod
    def _points(ring):
        return [QPointF(float(x), -float(y)) for x, y in ring] + ([QPointF(float(ring[0][0]), -float(ring[0][1]))]
                                                               if len(ring) else [])

    def _rebuild_scene(self):
        start = time.perf_counter()
        p = self.session.project
        # Flat: the rings as they are, the QPointF of `scene` made only when somebody reads it (study 41: 15 000 points
        # made at every change, 97 ms of a Del, for a list no view of the window reads).
        rings = [(kind, obj.id, '', getattr(obj, attr))
                 for kind, seq, attr in [('building', p.buildings, 'footprint'), ('subfield', p.subfields, 'ring'),
                                         ('exclusion', p.exclusions, 'ring')] for obj in seq]
        modules = [('module', sid, module.key, module.corners)
                   for sid, result in self.session.good_results().items() for module in result.modules]
        self._rings, self._module_count, self._scene = rings + modules, len(modules), None
        xs = [float(x) for _kind, _oid, _key, ring in self._rings for x, _y in ring]
        if xs:
            ys = [-float(y) for _kind, _oid, _key, ring in self._rings for _x, y in ring]
            xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
            self._bounds = [xmin, ymin, max(1., xmax-xmin), max(1., ymax-ymin)]
        self.metrics['scene_transfer_ms'] = (time.perf_counter() - start) * 1000
        self._emit('sceneChanged')

    def _changed(self, topics):
        if topics == {'selection'}:
            self._refresh_selection()
            return
        if 'file' in topics and self._enabled:      # another project in hand: its year, kept or to compute
            self.session.generation += 1
            self._year_note, self._year = '', {}
            self.timer.start()
        if not any(t.startswith('project:') for t in topics) and 'restored' not in topics:
            return
        self._refresh_selection()
        self._rebuild_objects()
        self._check_serial += 1
        self._emit('stateChanged')
        if topics - {'project:text', 'checks', 'restored'}:
            # A change of the plant lays the modules out again, and that is all (R443): the year in hand stays,
            # out of date (R437, the shell's yearState says what changed), until the designer asks for it again
            # or opens the project again. A year on its way goes on (R458, 12): it will answer for the plant as it
            # was asked, and be out of date the same way.
            self.session.generation += 1
            self._emit('yearChanged')
            self._checks = []
            self._emit('checksChanged')
            # Keep existing modules until the replacement snapshot is ready.
            self._rebuild_scene()
            if self._enabled and self.session.layouts_answer():
                # Nothing to lay out again: the strings realigned on the layout just come (R442), a choice of the
                # strings. Before, a second process laid out the same modules and every view and the checks went round
                # once more (study 41); now the checks of what changed, and a layout asked before is no longer needed.
                self.layout_timer.stop()
                self._request_checks()
            elif self._enabled:
                self.layout_timer.start()
        elif self._enabled:
            self._request_checks()

    def _request_checks(self):
        self._check_serial += 1
        job = CheckJob(self._check_serial, copy.deepcopy(self.session.project),
                       dict(self.session.results), self.session.energy)
        self._check_jobs[self._check_serial] = job
        job.signals.finished.connect(self._checks_finished)
        self.pool.start(job)
        self._emit('stateChanged')

    @Slot(int, object, str)
    def _checks_finished(self, serial, rows, error):
        self._check_jobs.pop(serial, None)
        if serial == self._check_serial:
            self._checks = rows
            if error:
                self._error = error
            self._emit('checksChanged')
        self._emit('stateChanged')

    @Slot(str, str, str)
    def select(self, kind, oid, key=''):
        self.calls['slot:select'] += 1
        if kind == 'module':
            self.session.select('subfield', oid, (oid, key))
        else:
            self.session.select(kind, oid)

    @Slot(str)
    def rename(self, value):
        self.calls['slot:rename'] += 1
        obj = self.selected_object()
        value = value.strip()
        if obj is not None and value and value != obj.name:
            self.session.edit(_('Rename'), lambda _p: setattr(obj, 'name', value))

    @Slot(float)
    def setHeight(self, value):
        self.calls['slot:setHeight'] += 1
        obj = self.selected_object()
        if self.session.selection[0] != 'building' or obj is None:
            return
        if not math.isfinite(value) or not 0 < value <= 500:
            self._error = _('Height must be between 0 and 500 m.')
            self._emit('stateChanged')
            return
        self.session.edit(_('Height'), lambda _p: setattr(obj, 'height', value))

    @staticmethod
    def _axis_aligned(ring):
        return len(ring) == 4 and model._is_rectangle(ring) and all(
            abs(a[0]-b[0]) < 1e-8 or abs(a[1]-b[1]) < 1e-8 for a, b in zip(ring, ring[1:]+ring[:1], strict=True))

    @staticmethod
    def _rectangle(x1, y1, x2, y2):
        if not all(math.isfinite(v) for v in (x1, y1, x2, y2)) or min(abs(x2-x1), abs(y2-y1)) < .1:
            raise ValueError(_('The rectangle must have two sides of at least 0.1 m.'))
        a, b = sorted((x1, x2)), sorted((y1, y2))
        return [[a[0], b[0]], [a[1], b[0]], [a[1], b[1]], [a[0], b[1]]]

    @Slot(float, float, float, float)
    def rectangle(self, x1, y1, x2, y2):
        self.calls['slot:rectangle'] += 1
        try:
            ring = self._rectangle(x1, y1, x2, y2)
            oid = self.session.project.new_id('b')
            self.session.edit(_('Draw a building'), lambda p: p.buildings.append(
                model.Building(id=oid, name=_('Building'), footprint=ring, height=6.)))
            self.session.select('building', oid)
        except ValueError as error:
            self._error = str(error)
            self._emit('stateChanged')

    @Slot(str, float, float, float, float)
    def resizeRectangle(self, oid, x1, y1, x2, y2):
        self.calls['slot:resizeRectangle'] += 1
        try:
            ring = self._rectangle(x1, y1, x2, y2)
            obj = next(b for b in self.session.project.buildings if b.id == oid)
            if not self._axis_aligned(obj.footprint):
                raise ValueError(_('The handles work on rectangles parallel to the axes.'))
            self.session.edit(_('Resize a building'), lambda _p: setattr(obj, 'footprint', ring))
        except (ValueError, StopIteration) as error:
            self._error = str(error) or _('The building no longer exists.')
            self._emit('stateChanged')

    @Slot()
    def undo(self):
        self.calls['slot:undo'] += 1
        self.session.undo.undo()

    @Slot()
    def redo(self):
        self.calls['slot:redo'] += 1
        self.session.undo.redo()

    @Slot(str)
    def filterChecks(self, level):
        self.calls['slot:filterChecks'] += 1
        self._filter = level
        self._emit('checksChanged')

    @Slot()
    def recompute(self):
        self.calls['slot:recompute'] += 1
        self._enabled = True
        self.session.generation += 1
        self._launch()

    def _launch(self):
        if self._busy:
            self._pending = True
            return
        self._pending = False
        self._busy, self._error = True, ''
        self._emit('stateChanged')
        self._asked_year()
        self._job = Compute(self.session.generation, copy.deepcopy(self.session.project),
                            self.session.known_layouts(), self.cache)
        self._job.signals.layout.connect(self.accept_layout)
        self._job.signals.finished.connect(self._finished)
        self.pool.start(self._job)

    def _asked_year(self):
        """The year about to be launched: the generation it is asked at, and the inputs it will answer for (the
        plant of now, not of when it ends: edits meanwhile leave it out of date, R437)."""
        self._year_generation = self.session.generation
        # the job lays out by itself: the year answers for the layouts of the project now, not those in hand
        self._year_energy_generation = self.session.energy_asked(self.session._expected_keys())

    def _launch_layout(self):
        """The layouts alone, in the pool, after a change (R443)."""
        self._layout_job = Layout(self.session.generation, copy.deepcopy(self.session.project),
                                  self.session.known_layouts())
        self._layout_job.signals.layout.connect(self.accept_layout)
        self.pool.start(self._layout_job)

    @Slot(int, object, object)
    def accept_layout(self, generation, results, keys):
        if not self.session.layout_done(generation, results, keys):
            return False
        self._rebuild_scene()
        if self._enabled:
            self._request_checks()
        return True

    @Slot(int, object, object, object)
    def _finished(self, generation, energy, items, metrics):
        self._busy = False
        # the year asked last, even after edits (then out of date, said as such), or one of this very generation
        if generation == self._year_generation or generation == self.session.generation:
            self.metrics.update(metrics)
            self._error = metrics.get('error', '') or ''
            self._year_note = energy.get('error_sim', '') or ''
            asked = (self._year_energy_generation if generation == self._year_generation
                     and self._year_energy_generation is not None else self.session.energy_asked())
            self.session.energy_done(asked, energy)
            self._request_checks()
            sim = energy.get('sim')
            if sim is not None:
                values = sim.hourly.e_kwh.to_numpy()
                daily = sim.hourly.e_kwh.resample('D').sum()
                maximum = max(1., float(daily.max()))
                self._year = {'hours': len(values), 'total': number(sim.energy_kwh, 0),
                              'totalValue': sim.energy_kwh, 'daily': daily.tolist(),
                              'maximum': maximum, 'maximumText': number(maximum, 0),
                              'points': [QPointF(i / max(1, len(daily)-1), 1-float(v)/maximum)
                                         for i, v in enumerate(daily)],
                              'source': _('Daily energy from the hourly computation')}
            else:
                self._year = {}
            self._emit('yearChanged')
        self._emit('stateChanged')
        if self._pending:
            self.timer.start()

    def close(self):
        """Only used after the event loop exits; no thread outlives its signal receiver."""
        self.timer.stop()
        self.pool.waitForDone()
