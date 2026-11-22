"""A measured, coarse-grained QML boundary over the unchanged project session."""
from __future__ import annotations

import math
import time
from collections import Counter
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, Property, QRunnable, QThreadPool, QTimer, Signal, Slot

from meridiana.app import checks_job, jobs, layout_job
from meridiana.core.model import model
from meridiana.app import pipeline
from meridiana.i18n import _, number
from meridiana.app.session import ProjectSession, project_from


# What the bridge's lists are made of: the shapes (scene: the buildings, sub-fields and exclusions with the modules
# in hand), and with the names what the objects and the selection show; a change of anything else (the strings
# realigned on a layout, the energy, the rules) leaves them as they are.
SHAPES = {'project:geometry', 'project:subfields', 'project:variants', 'restored'}
SHOWN = SHAPES | {'project:text'}


class Signals(QObject):
    layout = Signal(int, object, object)
    finished = Signal(int, object, object, object)


class Compute(QRunnable):
    """One photo (session.photo()), made a project here, no access to a live QObject from the worker."""
    def __init__(self, generation, photo, known, cache):
        super().__init__()
        self.generation, self.photo = generation, photo
        self.known, self.cache = known, cache
        self.signals = Signals()

    def run(self):
        start = time.perf_counter()
        try:
            project = project_from(self.photo)
            results, keys, _laid = jobs.layout_of(project, self.known)
            self.signals.layout.emit(self.generation, results, keys)
            good = {k: v for k, v in results.items() if not isinstance(v, Exception)}
            energy = pipeline.compute(project, good, self.cache, fetch=False).as_dict()
            self.signals.finished.emit(self.generation, energy, [],
                                       {'worker_ms': (time.perf_counter() - start) * 1000})
        except Exception as error:  # Worker boundary: the window displays the failure.
            self.signals.finished.emit(self.generation, {}, [], {'error': str(error)})


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
        self._work = None                       # the jobs' bridge (work), made when first asked
        self._layout = None                     # the layout of a change, a job of the center (R598)
        self._layout_asked = None               # its request, the photo it was made on
        self._year_generation = None            # the session's generation the year on its way was asked at
        self._year_energy_generation = None     # and the session's energy generation it will answer
        self.metrics = {}
        self.pool = QThreadPool(self)           # the year of this bridge's own (Compute); the shell's is a process
        self.pool.setMaxThreadCount(1)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(120)
        self.timer.timeout.connect(self._launch)
        self.session.subscribe(self._changed)
        # the checks, the window's one job of them (app/checks_job.py, R598): the panel reads the same answer
        self.checks_feed = checks_job.Feed(self.session, lambda: self.work.center)
        self.checks_feed.join('checks.bridge', self._checks_came, self._checks_failed, wants=lambda: self._enabled)
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
        """The year on its way, or about to be asked; the checks are a job of their own (checks_feed.busy())."""
        return self._get('busy', self._busy or self.timer.isActive())

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
        if 'file' in topics:                        # a layout of the project before is no longer awaited
            self._drop_layout()
        if 'file' in topics and self._enabled:      # another project in hand: its year, kept or to compute
            self.session.generation += 1
            self._year_note, self._year = '', {}
            self.timer.start()
        if not any(t.startswith('project:') for t in topics) and 'restored' not in topics:
            return
        # what they are made of (study 41: rebuilt at every change, the strings realigned on a layout too)
        if topics & SHOWN:
            self._refresh_selection()
            self._rebuild_objects()
        self._emit('stateChanged')
        if topics - {'project:text', 'checks', 'restored'}:
            # A change of the plant lays the modules out again, and that is all (R443): the year in hand stays,
            # out of date (R437, the shell's yearState says what changed), until the designer asks for it again
            # or opens the project again. A year on its way goes on (R458, 12): it will answer for the plant as it
            # was asked, and be out of date the same way.
            self.session.generation += 1
            self._emit('yearChanged')
            # Keep existing modules until the replacement snapshot is ready (and the checks until theirs).
            if topics & SHAPES:
                self._rebuild_scene()
            if self._enabled and self.session.layouts_answer():
                # Nothing to lay out again: the strings realigned on the layout just come (R442), a choice of the
                # strings. Before, a second process laid out the same modules and every view and the checks went round
                # once more (study 41); now only the checks of what changed (their job hears it), and a layout asked
                # before is no longer needed.
                self._drop_layout()
            elif self._enabled:
                self._ask_layout()

    def request_checks(self):
        """The checks of the project in hand asked now, even before the window computes (a capture, a pilot): their
        rows come in `checkRows`; `checks_feed.busy()` says while they are on their way."""
        self.checks_feed.ask(always=True)

    def _checks_came(self, answer):
        """The checks' answer (checks_feed), a piece of the window's turns: told only when the rows changed."""
        if answer['bridge'] != self._checks:
            self._checks = answer['bridge']
            self._emit('checksChanged')

    def _checks_failed(self, sentence):
        self._error = sentence
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
        self.work.center.warm(layout_job.KIND)      # the layout's process ready for the first change (and the checks)
        self.session.generation += 1
        self._launch()
        self.checks_feed.ask()

    def _launch(self):
        if self._busy:
            self._pending = True
            return
        self._pending = False
        self._busy, self._error = True, ''
        self._emit('stateChanged')
        self._asked_year()
        self._job = Compute(self.session.generation, self.session.photo(),
                            self.session.known_layouts(), self.cache)
        self._job.signals.layout.connect(self.accept_layout)
        self._job.signals.finished.connect(self._finished)
        self.pool.start(self._job)

    def _asked_year(self):
        """The year about to be launched: the generation it is asked at, and the inputs it will answer for (the
        plant of now, not of when it ends: edits meanwhile leave it out of date, R437)."""
        self._year_generation = self.session.generation
        # the job lays out by itself: the year answers for the layouts of the project now, not those in hand
        self._year_energy_generation = self.session.energy_asked(self.session.expected_layout_keys())

    # the layout of a change, a job of the mechanism (R598, study 48 chapter 6 step 1; app/layout_job.py)

    @property
    def work(self):
        """The jobs' bridge of this window (gui/backend/work.py), made when first asked: the layout of a change is
        one of its jobs. The window's `work` part is this same one (work.install), so that there is one center."""
        if self._work is None:
            from meridiana.gui.backend.work import WorkBackend
            self._work = WorkBackend(self.session, self, parent=self)
        return self._work

    def _ask_layout(self):
        """The layouts alone after a change (R443), as the jobs' layout: in its process kept warm, after the kind's
        quiet, only the last change counting (the slot); the year on its way, if any, goes on (R458, 12)."""
        self._layout = self.work.center.submit(layout_job.KIND, build=self._layout_request, on_done=self._layout_came,
                                               on_failed=self._layout_failed, settle=True)

    def _layout_request(self):
        """The request of the layout, made when it starts (after the quiet): the photo of now, kept to know whether
        the strings the job realigned are still those of the project in hand."""
        self._layout_asked = layout_job.request_of(self.session)
        return self._layout_asked

    def _drop_layout(self):
        """The layout on its way, if any, no longer needed (nothing moves, another project)."""
        layout, self._layout = self._layout, None
        if layout is not None and layout.active:
            layout.cancel()

    def _layout_came(self, answer, _stale):
        asked, self._layout_asked, self._layout = self._layout_asked, None, None
        if asked is None or answer.get('generation') != asked['generation']:
            return
        # a change of the modules made while the answer came, its views not told yet (R547: the bridge hears it after
        # the frame, and only then a new generation): the answer is of the project before, never taken
        results = None if answer['keys'] != self.session.expected_layout_keys() else \
            layout_job.results_of(answer, self.session)
        if results is None:             # that, or the layouts in hand changed meanwhile (the year's): asked again
            if self._enabled and answer['generation'] == self.session.generation:
                self._ask_layout()
            return
        self.session.wiring_offer = answer.get('wiring')     # the plan's strings made with it (plan_wiring.made_with)
        self.accept_layout(answer['generation'], results, answer['keys'], answer.get('strings'), asked['photo'])

    def _layout_failed(self, _kind, text):
        self._layout = None
        self._error = text
        self._emit('stateChanged')

    @Slot(int, object, object)
    def accept_layout(self, generation, results, keys, realigned=False, photo=None):
        """A layout taken (from the jobs' layout, or the year's job): with the strings realigned by the job on
        `photo` when there are (session.layout_done), the views told a piece each on the window's turns."""
        if not self.session.layout_done(generation, results, keys, realigned, photo, pieces=True):
            return False
        self._piece('bridge.scene', self._rebuild_scene)        # the checks' job hears the layout by itself
        return True

    def _piece(self, name, call, *args):
        """`call(*args)` on a turn of its own when the window spreads its work (session.pieces, R598), now otherwise."""
        if self.session.pieces is not None:
            self.session.pieces(name, call, *args)
        else:
            call(*args)

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
            # told as "energy", the views a piece each on the window's turns (R598): the checks' job hears it
            self.session.energy_done(asked, energy, pieces=True)
            self._piece('bridge.year', self._show_year, energy)
        self._piece('bridge.state', self._emit, 'stateChanged')        # what the QML binds to it, a turn of its own
        if self._pending:
            self.timer.start()

    def _show_year(self, energy):
        """The year's line of this bridge (`year`): its days."""
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

    def close(self):
        """Only used after the event loop exits; no thread outlives its signal receiver."""
        self.timer.stop()
        self.checks_feed.close()
        if self._work is not None:
            self._work.close()
        self.pool.waitForDone()
