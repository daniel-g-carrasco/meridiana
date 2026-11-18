"""Plant page controller. Project changes belong to ProjectSession, physics to energy."""
from __future__ import annotations

import copy
import json
import time
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot, QThreadPool, QTimer, QUrl

from meridiana.energy import plant as core, sizing as sizing_core, system
from meridiana.energy.storage import check_storage, operating_battery
from meridiana.i18n import number
from meridiana.session import ProjectSession, set_path
from .plant_jobs import PlantJob
from .plant_presenter import draft_words, present
from .plant_i18n import _

PAGE_URL = QUrl.fromLocalFile(str(Path(__file__).parents[1] / 'qml/Meridiana/Plant/PlantPage.qml'))


class PlantBackend(QObject):
    # One signal for each family of properties, so that QML recomputes only what moved (06/11/2026, the Quick's
    # slowness: `changed` served fifteen properties and fired four or five times for one edit, each time making
    # every binding read the lists again). `changed` still fires once, after the others, for whoever hangs on it.
    changed = Signal()
    dataChanged = Signal()          # data, units, strings, inputs: the strings laid, once per build
    stateChanged = Signal()         # busy, searching, calculateDirty, layoutDirty, canUndo, canRedo
    projectChanged = Signal()       # settings, storage, subfields: what the project says
    makersChanged = Signal()        # makers and their favourites
    sizingChanged = Signal()        # sizingChoice
    _FAMILIES = ('dataChanged', 'stateChanged', 'projectChanged', 'makersChanged', 'sizingChanged')
    messageChanged = Signal()
    selectionChanged = Signal()
    appearanceChanged = Signal()
    wiringChanged = Signal(object)
    drawRequested = Signal(int, int, int)
    showStringRequested = Signal(int)
    calculateRequested = Signal()
    layoutRequested = Signal()
    catalogRequested = Signal(str, int)
    favouritesChanged = Signal('QStringList')
    searchProgressChanged = Signal()

    def __init__(self, session=None, parent=None):
        super().__init__(parent)
        self.session = session or ProjectSession()
        self.pool = QThreadPool.globalInstance()
        self.state = None
        self._data = dict(units=[], strings=[], inputs=[], total=_('The inverters are being checked…'), totalTip='',
                          summary=_('The strings are being laid…'), conditionsText='', left=0, notes=[], corrections=[])
        self._message = ''
        self._makers = []
        self._favourites = []
        self._selected, self._working = -1, 0
        self._chosen_input, self._unit_chosen = [], False      # what the summary shows of what was clicked (R419)
        self._colours, self._draft_input, self._draft_card = {}, [], {}
        self._jobs, self._build, self._search = set(), None, None
        self._closed = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._rebuild)
        self._clock = QTimer(self)              # R522: the seconds of the search for the modules in no string
        self._clock.setInterval(250)
        self._clock.timeout.connect(self.searchProgressChanged)
        self._pending = set()
        self._notifier = QTimer(self)
        self._notifier.setSingleShot(True)
        self._notifier.timeout.connect(self._flush)
        self.session.subscribe(self._on_change)
        self._schedule()

    def notify(self, *families):
        """The signals of `families` (all of them when none is named) emitted once, at the next turn of the event
        loop, however many times they are asked for in this one; `changed` after them."""
        self._pending.update(families or self._FAMILIES)
        if not self._notifier.isActive():
            self._notifier.start(0)

    @Slot()
    def _flush(self):
        pending, self._pending = self._pending, set()
        if self._closed or not pending:
            return
        for name in self._FAMILIES:
            if name in pending:
                getattr(self, name).emit()
        self.changed.emit()

    @Property('QVariantMap', notify=dataChanged)
    def data(self):
        return self._data

    @Property('QVariantMap', notify=sizingChanged)
    def sizingChoice(self):
        """Why the last automatic sizing chose what it chose, and what else was valid (R420)."""
        result = getattr(self, '_sizing_result', None)
        if result is None:
            return {}

        def row(item, n):
            line = sizing_core.free_line(item) if item.mode else ''
            return dict(index=n, names=sizing_core.alternative_row(item)['names'], ratio=number(item.ratio, 2), units=item.units,
                        line=line, left=item.left,
                        ac=number(item.ac_w / 1000.0, 1), dc=number(item.dc_max_w / 1000.0, 1) if item.dc_max_w else '–',
                        why=item.why, oversized=item.standing == sizing_core.UNDER_ONE,
                        byUnit=' · '.join(number(r, 2) for r in item.unit_ratios))
        return dict(why=result.why, chosen=row(result, -1), alternatives=[row(a, n) for n, a in enumerate(result.alternatives)])

    @Slot(int)
    def useSizingAlternative(self, index):
        """Another of the valid combinations of the last sizing, in place of the one taken; the search is not run again."""
        result = getattr(self, '_sizing_result', None)
        if result is None or not 0 <= index < len(result.alternatives):
            return
        other = result.alternatives[index]

        def put(p):
            if other.mode:
                self._put_free(p, other, self._sizing_maker)
                return
            p.energy.update(inverter_maker=self._sizing_maker, inverters=other.entries)
            p.energy['strings'] = core.touched(p.energy.get('strings'), other.runs)
            p.energy.pop('inverter', None)
            p.energy.pop('inverter_count', None)
        self.session.edit(_('Size the inverters by themselves'), put)
        others = [a for n, a in enumerate(result.alternatives) if n != index] + [result]
        result.alternatives = []
        other.alternatives = others[:sizing_core.MAX_ALTERNATIVES]
        self._sizing_result = other
        self.tell(other.why)
        self.notify('sizingChanged')

    @Slot()
    def dismissSizing(self):
        self._sizing_result = None
        self.notify('sizingChanged')

    @Property(int, notify=dataChanged)
    def freeModules(self):
        """R522: the modules laid in no string when some are in strings already (0 otherwise): what «Only the modules in
        no string» works on."""
        state = self.state
        return len(state.left) if state is not None and state.strings and state.left else 0

    @Property('QVariantList', notify=dataChanged)
    def units(self):
        return self._data['units']

    @Property('QVariantList', notify=dataChanged)
    def strings(self):
        return self._data['strings']

    @Property('QVariantList', notify=dataChanged)
    def inputs(self):
        return self._data['inputs']

    stringColours = Property('QVariantMap', lambda self: self._colours, notify=appearanceChanged)
    draftInput = Property('QVariantList', lambda self: self._draft_input, notify=appearanceChanged)
    draftCard = Property('QVariantMap', lambda self: self._draft_card, notify=appearanceChanged)
    chosenInput = Property('QVariantList', lambda self: self._chosen_input, notify=selectionChanged)
    unitChosen = Property(bool, lambda self: self._unit_chosen, notify=selectionChanged)

    def show_appearance(self, colours, draft, card=None):
        card = card or {}
        if colours != self._colours or draft != self._draft_input or card != self._draft_card:
            self._colours, self._draft_input, self._draft_card = colours, draft, card
            self.appearanceChanged.emit()

    @Property('QVariantList', notify=makersChanged)
    def makers(self):
        preferred = self.preferred_makers()
        return sorted([dict(m, favourite=m['label'] in self._favourites, preferred=m['label'] in preferred)
                       for m in self._makers],
                      key=lambda m: (not m['favourite'], not m['sizable'], m['label'].casefold()))

    def preferred_makers(self) -> set:
        """R522 (Daniel 07/11/2026 «solo marche preferite»): the makers the proposal for the modules in no string
        searches among, the preferred ones of catalog/data/preferred_makers.json and the profile's favourites."""
        path = Path(sizing_core.__file__).parents[1] / 'catalog' / 'data' / 'preferred_makers.json'
        try:
            listed = json.loads(path.read_text(encoding='utf-8')).get('kinds', {}).get('inverters', [])
        except (OSError, ValueError):
            listed = []
        wanted = {str(n).casefold() for n in [*listed, *self._favourites]}
        return {m['label'] for m in self._makers if m['label'].casefold() in wanted}

    @Property(float, notify=searchProgressChanged)
    def searchSeconds(self):
        """Seconds since the search for the modules in no string began, -1 when none runs (R522)."""
        job = self._search
        return time.monotonic() - job.started if job is not None and job.kind == 'sizing_free' else -1.0

    @Property(float, constant=True)
    def searchLimit(self):
        return float(sizing_core.FREE_SECONDS)

    @Slot('QStringList')
    def setFavourites(self, values):
        self._favourites = list(dict.fromkeys(values))
        self.notify('makersChanged')

    @Slot(str)
    def toggleFavourite(self, maker):
        if maker in self._favourites:
            self._favourites.remove(maker)
        else:
            self._favourites.append(maker)
        self.favouritesChanged.emit(self._favourites)
        self.notify('makersChanged')

    @Property('QVariantList', notify=projectChanged)
    def subfields(self):
        return [dict(id=sf.id, name=sf.name, inverter=sf.params.get('inverter', 0),
                     mppt=sf.params.get('mppt', 0)) for sf in self.session.project.subfields]

    @Slot('QVariantMap', result='QVariantList')
    def recordDetails(self, record):
        from .catalog import labels, display_field
        from .catalog_i18n import field_label
        names = labels()
        return [dict(label=field_label(k, names), value=display_field(record, k))
                for k in record if k != 'id']

    @Slot()
    def loadMakers(self):
        if not self._makers and not any(job.kind == 'makers' for job in self._jobs):
            self.pool.start(self._job('makers'))

    @Property('QVariantList', constant=True)
    def strategies(self):
        return [dict(key=k, label=v) for k, v in core.strategy_names().items()]

    @Property('QVariantMap', constant=True)
    def statusColors(self):
        from meridiana.theme_colors import STATUS
        return dict(ok=STATUS['good'], check=STATUS['warning'], fail=STATUS['critical'],
                    warn=STATUS['warning'], info=STATUS['good'])

    @Property('QVariantMap', notify=projectChanged)
    def settings(self):
        e = self.session.project.energy
        s = e.get('strings') or {}
        return dict(strategy=s.get('strategy', 'serpentine'), n_series=s.get('n_series') or 0,
                    dc_ac=e.get('dc_ac_ratio') or 1.1, maker=e.get('inverter_maker', ''), t_min=e.get('t_min', -10),
                    across=bool(s.get(core.ACROSS)))

    @Property('QVariantMap', notify=projectChanged)
    def storage(self):
        return copy.deepcopy(self.session.project.economics)

    @Property(bool, notify=stateChanged)
    def busy(self):
        return self._timer.isActive() or self._build is not None or self._search is not None

    @Property(bool, notify=stateChanged)
    def searching(self):
        return self._search is not None

    @Property(bool, notify=stateChanged)
    def calculateDirty(self):
        return self.session.energy_outdated()

    @Property(bool, notify=stateChanged)
    def layoutDirty(self):
        return any(sf.filled and self.session.layout_state(sf) == 'stale'
                   for sf in self.session.project.subfields)

    @Property(bool, notify=stateChanged)
    def canUndo(self):
        return self.session.undo.can_undo()

    @Property(bool, notify=stateChanged)
    def canRedo(self):
        return self.session.undo.can_redo()

    @Property(str, notify=messageChanged)
    def message(self):
        return self._message

    @Property(int, notify=selectionChanged)
    def selected(self):
        return self._selected

    @Property(int, notify=selectionChanged)
    def working(self):
        return self._working

    @Property('QVariantMap', notify=selectionChanged)
    def chosen(self):
        return self.strings[self._selected] if 0 <= self._selected < len(self.strings) else {}

    @Slot(str, result=str)
    def tr(self, text):
        return _(text)

    @Slot(float, int, result=str)
    def formatNumber(self, value, places):
        return number(value, places)

    def draft_card(self, target, modules, colour):
        return draft_words(self.state, target, modules, colour)

    def tell(self, message):
        self._message = str(message)
        self.messageChanged.emit()

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._timer.stop()
        self._notifier.stop()
        if self._on_change in self.session.listeners:
            self.session.listeners.remove(self._on_change)
        for job in self._jobs:
            job.interrupt()

    def _on_change(self, topics):
        if self._closed:
            return
        relevant = {'project:energy', 'project:subfields', 'project:geometry', 'project:site',
                    'project:variants', 'file', 'energy'}
        if topics & relevant or any(t.startswith('layout:') for t in topics):
            # A change that waits for its layout (a module taken out, a sub-field moved) is built when the layout comes
            # (its topics start the timer again at once): built now, on the layouts of before, it was thrown away and
            # its cards drawn for nothing in the middle of the gesture (study 41). Not come within the wait, it goes.
            self._schedule(0 if self.session.layouts_answer() else self.LAYOUT_WAIT_MS)
        elif 'project:text' in topics and self._build is not None:
            self._schedule()
        # A selection changes nothing of the plant (R419: thousands of modules selected with a window must not
        # rebuild the cards); the lists of the strings move only when a build is done (`_done`).
        if topics != {'selection'}:
            self.notify('projectChanged', 'stateChanged')

    LAYOUT_WAIT_MS = 600

    def _schedule(self, wait=0):
        if self._closed:
            return
        if not (wait and self._timer.isActive() and self._timer.remainingTime() <= wait):
            self._timer.start(wait)
        self.notify('stateChanged')

    def _year(self):
        sim = (self.session.energy or {}).get('sim')
        return (max(a['t_cell_max'] for a in sim.arrays), sim.hourly.p_dc.to_numpy()) if sim is not None else (None, None)

    def settled(self):
        return all(self.session.layout_state(sf) not in ('stale', 'missing', 'error')
                   for sf in self.session.project.subfields if sf.filled)

    def _job(self, kind, **options):
        job = PlantJob(kind, self.session.snapshot(), self.session.good_results(),
                       self.session.state_key(), self.session.layout_keys, **options)
        self._jobs.add(job)
        job.signals.done.connect(self._done)
        return job

    @Slot()
    def _rebuild(self):
        hot, power = self._year()
        from meridiana.energy import faces
        self._build = self._job('build', t_cell_max_year=hot, p_dc_hourly=power,
                                exposure=faces.year_of((self.session.energy or {}).get('sim')))
        self.pool.start(self._build)
        self.notify('stateChanged')

    @Slot(object, object)
    def _done(self, job, result):
        self._jobs.discard(job)
        if self._closed:
            return
        if job.kind == 'makers':
            if isinstance(result, Exception):
                self.tell(str(result))
            else:
                self._makers = [dict(m, reason=m['reason'] or (_('No datasheet data for sizing.') if not m['sizable'] else ''))
                                for m in result]
            self.notify('makersChanged')
            return
        if job.kind == 'build':
            if job is not self._build:
                return
            self._build = None
        else:
            if job is not self._search:
                return
            self._search = None
            self._clock.stop()
            self.searchProgressChanged.emit()
        current = job.key == self.session.state_key() and job.layout_keys == self.session.layout_keys
        if job.cancelled.is_set() or not current:
            if job.kind != 'build':
                self.tell(_('The project changed during string search. No old proposal was applied.'))
            self.notify('stateChanged')
            return
        if isinstance(result, Exception):
            self.tell(_('The strings could not be laid: {error}').format(error=result))
        elif job.kind == 'build':
            self.state = result
            self._data = present(result, self.session.project)
            if self._selected >= len(result.strings):
                self._selected = -1
            if not any(u.number == self._working for u in result.units):
                self._working = result.units[0].number if result.units else 0
            self.selectionChanged.emit()
            self.wiringChanged.emit(result)
            if result.auto and result.search_complete and self.settled():
                def adopt(p):
                    if result.entries is not None:
                        p.energy['inverters'] = result.entries
                    p.energy['strings'] = core.touched(p.energy.get('strings'), core.runs_of(result))
                self.session.amend(adopt)
        elif not self.settled():
            self.tell(_('Wait for the current module layout before proposing strings.'))
        elif job.kind == 'sizing_free':
            if not result.ok or not result.search_complete:
                self.tell(result.reason)
            else:
                strings = (self.session.project.energy.get('strings') or {}).get('runs') or []
                self._free_base = (copy.deepcopy(self.session.project.energy.get('inverters')), copy.deepcopy(strings))
                self.session.edit(_('Propose inverters and strings for the modules in no string'),
                                  lambda p: self._put_free(p, result, job.options['maker']))
                self._sizing_result, self._sizing_maker = result, job.options['maker']
                self.tell(result.why + ('\n' + '\n'.join(result.notes) if result.notes else ''))
        elif job.kind == 'sizing':
            if not result.ok or not result.search_complete:
                self.tell(result.reason)
            else:
                def put(p):
                    p.energy.update(inverter_maker=job.options['maker'], inverters=result.entries)
                    p.energy['strings'] = core.touched(p.energy.get('strings'), result.runs)
                    p.energy.pop('inverter', None)
                    p.energy.pop('inverter_count', None)
                self.session.edit(_('Size the inverters by themselves'), put)
                self._sizing_result, self._sizing_maker = result, job.options['maker']
                self.tell(result.why + ('\n' + '\n'.join(result.notes) if result.notes else ''))
        else:
            self._apply_proposal(job, result)
        self.notify(*(('dataChanged', 'stateChanged', 'sizingChanged') if job.kind == 'build' else ('stateChanged', 'sizingChanged')))

    def _put_free(self, p, result, maker):
        """R522: the designer's inverters and strings as they were when the proposal was applied (`_free_base`), the
        inverters added after them and the strings added after his: nothing of his is written again."""
        entries, runs = getattr(self, '_free_base', (None, None))
        if entries is None and runs is None:
            entries, runs = p.energy.get('inverters'), (p.energy.get('strings') or {}).get('runs') or []
        entries, runs = copy.deepcopy(entries), copy.deepcopy(runs or [])
        if result.added:
            if not entries:
                entries = system.inverter_entries(p.energy)
                p.energy.pop('inverter', None)
                p.energy.pop('inverter_count', None)
            p.energy['inverters'] = list(entries) + copy.deepcopy(result.added)
            if not p.energy.get('inverter_maker'):
                p.energy['inverter_maker'] = maker
        elif entries is not None:
            p.energy['inverters'] = entries
        s = {k: v for k, v in (p.energy.get('strings') or {}).items() if k != 'auto'}
        s['runs'] = runs + copy.deepcopy(result.new_runs)
        p.energy['strings'] = s

    def _apply_proposal(self, job, result):
        failed = [s.why for s in result.strings if not core.acceptable(s)]
        failed += [c.detail for values in result.checks.values() for c in values
                   if c.level == 'fail' or c.key == 'imp_total' and c.level == 'warn']
        if not result.search_complete or failed:
            self.tell(_('No complete string proposal was applied: {why}').format(
                why=result.search_reason or failed[0] if failed else result.search_reason))
            return
        runs = core.runs_of(result)
        keep = job.options.get('keep')
        if not runs or keep is not None and len(runs) <= len(keep):
            self.tell(_('No new strings were needed; the existing strings have been kept.'))
            return
        strategy = job.options.get('strategy', '')
        title = _('Complete the strings') if keep is not None else _('Propose the strings: {strategy}').format(
            strategy=core.strategy_names().get(strategy, strategy).lower())
        self._put_runs(title, runs, {'strategy': strategy} if strategy else {}, result.entries)
        self.tell(_('Plant > Strings: {n} strings assigned; {m} modules remain unconnected. '
                    'Choose the working inverter and review its inputs. Undo restores the previous wiring.').format(
                        n=len(runs), m=len(result.left)) + '\n' + '\n'.join(core.conditions_of(result.strings)))

    def runs(self):
        result = copy.deepcopy((self.session.project.energy.get('strings') or {}).get('runs') or [])
        return core.materialize_optimizer_groups(result, self.state) if self.state is not None else result

    def _put_runs(self, text, runs, extra=None, entries=None):
        def put(p):
            if entries is not None:
                p.energy['inverters'] = copy.deepcopy(entries)
            s = dict(p.energy.get('strings') or {})
            s.update(extra or {})
            p.energy['strings'] = core.touched(s, runs)
        self.session.edit(text, put)

    def _entries(self, text, change):
        def put(p):
            before = core.unit_keys(p.energy)
            entries = system.inverter_entries(p.energy)
            for i, entry in enumerate(entries):
                entry['_was'] = i
            change(entries)
            moved = {e.pop('_was'): j for j, e in enumerate(entries) if '_was' in e}
            p.energy.pop('inverter', None)
            p.energy.pop('inverter_count', None)
            if entries:
                p.energy['inverters'] = entries
            else:
                p.energy.pop('inverters', None)
            s = p.energy.get('strings') or {}
            if s.get('runs'):
                p.energy['strings'] = {**s, 'runs': core.renumber(s['runs'], before, core.unit_keys(p.energy), moved)}
        self.session.edit(text, put)

    @Slot('QVariantMap')
    def addInverter(self, record):
        rec = copy.deepcopy(record)
        def add(entries):
            same = next((e for e in entries if e['record'] == rec), None)
            if same is not None:
                same['count'] += 1
            else:
                entries.append(dict(record=rec, count=1, name=''))
        self._entries(_('Add an inverter from the catalogue'), add)

    def _put_units(self, text, entries, mapping=None, runs=None):
        def put(p):
            p.energy.pop('inverter', None)
            p.energy.pop('inverter_count', None)
            p.energy['inverters'] = entries
            s = dict(p.energy.get('strings') or {})
            if runs is not None:
                p.energy['strings'] = core.touched(s, runs)
            elif mapping and s.get('runs'):
                p.energy['strings'] = {**s, 'runs': core.renumber_runs(s['runs'], mapping)}
        self.session.edit(text, put)

    @Slot(int, str)
    def renameUnit(self, unit, name):
        entries = core.rename_unit(self.session.project.energy, unit, name)
        if entries is not None:
            self._put_units(_('Rename inverter {n}').format(n=unit), entries)

    @Slot(int, int)
    def moveUnit(self, unit, position):
        entries, mapping = core.move_unit(self.session.project.energy, unit, position)
        if entries is not None:
            self._put_units(_('Move inverter {a} to place {b}').format(a=unit, b=position + 1), entries, mapping)
            self._working = mapping.get(self._working, self._working)

    @Slot(int, bool)
    def removeUnit(self, unit, strings=False):
        entries, runs = core.remove_unit(self.session.project.energy, self.runs(), unit, strings)
        if entries is not None:
            text = _('Delete inverter {n} and its strings') if strings else _('Take inverter {n} out')
            self._put_units(text.format(n=unit), entries, runs=runs)

    @Slot(int)
    def emptyUnit(self, unit):
        self._put_runs(_('Empty the strings of inverter {n}').format(n=unit),
                       [r for r in self.runs() if r.get('inverter') != unit])

    @Slot(int, int)
    def setCount(self, entry, count):
        if 0 <= entry < len(system.inverter_entries(self.session.project.energy)) and count > 0:
            self._entries(_('Change how many inverters'), lambda e: e[entry].update(count=int(count)))

    @Slot(int, 'QVariantMap', int)
    def setOptimizer(self, entry, record, per):
        if not 0 <= entry < len(system.inverter_entries(self.session.project.energy)):
            return
        def put(entries):
            if record:
                entries[entry].update(optimizer=copy.deepcopy(record), per_optimizer=2 if per == 2 else 1)
            else:
                entries[entry].pop('optimizer', None)
                entries[entry].pop('per_optimizer', None)
        self._entries(_('Choose the power optimizers') if record else
                      _('Back to the optimizers Meridiana proposes'), put)

    @Slot(int, int)
    def setOptimizerPer(self, entry, per):
        if 0 <= entry < len(system.inverter_entries(self.session.project.energy)) and per in (1, 2):
            self._entries(_('Change the modules on each optimizer'),
                          lambda entries: entries[entry].update(per_optimizer=per))

    def _connection(self, unit, mppt):
        u = self.state.unit(unit) if self.state else None
        if u is None or not 1 <= mppt <= u.inputs:
            self.tell(_('Without an input'))
            return False
        return True

    @Slot(int, int, 'QVariantList', int, result=bool)
    def commitString(self, unit, mppt, keys, index=-1):
        if not self._connection(unit, mppt):
            return False
        runs = self.runs()
        if index < 0:
            if not keys:
                return False
            runs, chosen = core.new_run(runs, unit, mppt, list(keys))
            text = _('New string on input {k} of inverter {n}').format(k=mppt, n=unit)
        elif index < len(runs):
            if not keys:
                self.deleteString(index)
                return True
            if list(keys) == runs[index]['modules']:
                self.selectString(index)
                return True
            text = _('Draw string {name} again').format(name=core.run_label(runs, index))
            runs, _taken = core.set_run(runs, index, list(keys))
            chosen = index
        else:
            return False
        kept = [i for i, r in enumerate(runs) if r.get('modules')]
        self._selected = kept.index(chosen) if chosen in kept else -1
        self._put_runs(text, runs)
        return True

    @Slot(int, int, int, result=bool)
    def moveString(self, index, unit, mppt):
        runs = self.runs()
        if not 0 <= index < len(runs) or not self._connection(unit, mppt):
            return False
        name = core.run_label(runs, index)
        moved = dict(runs.pop(index), inverter=unit, mppt=mppt)
        runs.append(moved)
        self._selected = len(runs) - 1
        self._put_runs(_('Move string {name} to input {k} of inverter {n}').format(name=name, k=mppt, n=unit), runs)
        return True

    @Slot(int)
    def deleteString(self, index):
        runs = self.runs()
        if 0 <= index < len(runs):
            name = core.run_label(runs, index)
            self._selected = -1
            self._put_runs(_('Delete string {name}').format(name=name), core.delete_run(runs, index))

    @Slot(int)
    def reverseString(self, index):
        runs = self.runs()
        if 0 <= index < len(runs):
            self._put_runs(_('Reverse the string'), core.reversed_run(runs, index))

    @Slot()
    def clearStrings(self):
        self._selected = -1
        self._put_runs(_('Delete all the strings'), [])

    @Slot(int, 'QVariantList', result=bool)
    def setOptimizerGroups(self, index, sizes):
        runs = self.runs()
        if not 0 <= index < len(runs):
            return False
        unit = self.state.unit(runs[index].get('inverter', 0)) if self.state else None
        # SolarEdge's optimizers, or those of an inverter with MPPT (Huawei MERC, Tigo TS4-A-2F: R456)
        per = unit.choice.per if unit is not None and unit.choice is not None else (
            unit.mlpe.per if unit is not None and unit.mlpe is not None else 0)
        if not per:
            return False
        if any(type(n) is not int or not 1 <= n <= per for n in sizes) or sum(sizes) != len(runs[index]['modules']):
            self.tell(_('The groups must contain all modules.'))
            return False
        runs[index]['optimizer_group_sizes'] = list(sizes)
        self._put_runs(_('Change modules on each optimizer'), runs)
        return True

    @Slot(str, int, int)
    def assignSubfield(self, sfid, inverter, mppt):
        def put(p):
            sf = next((s for s in p.subfields if s.id == sfid), None)
            if sf is not None:
                for key, value in (('inverter', inverter), ('mppt', mppt if inverter else 0)):
                    if value:
                        sf.params[key] = int(value)
                    else:
                        sf.params.pop(key, None)
        self.session.edit(_("Send a sub-field's strings to an inverter"), put)

    @Slot(str, 'QVariant')
    def setEnergy(self, path, value):
        self.session.edit(_('Change energy settings'), lambda p: set_path(p.energy, path, value))

    @Slot(int)
    def selectString(self, index):
        self._selected = index if 0 <= index < len(self.strings) else -1
        if self._selected >= 0:
            self._working = self.strings[self._selected]['inverter']
            self._chosen_input, self._unit_chosen = [], False
        self.selectionChanged.emit()
        self.showStringRequested.emit(self._selected)

    @Slot(int)
    def selectUnit(self, unit):
        """The Strings show this inverter; a string chosen on another one is no longer chosen (ui/plant_page._unit_activated)."""
        if unit != self._working and self._selected >= 0:
            self._selected = -1
            self.showStringRequested.emit(-1)
        self._working = unit
        self._chosen_input, self._unit_chosen = [], True
        self.selectionChanged.emit()

    @Slot(int, int)
    def selectInput(self, unit, mppt):
        """An input clicked: it is the one the summary tells about (R419). A string chosen is no longer."""
        if self._selected >= 0:
            self._selected = -1
            self.showStringRequested.emit(-1)
        self._chosen_input, self._unit_chosen = [unit, mppt], False
        self.selectionChanged.emit()

    def clear_choice(self):
        """Something else was selected: no input and no inverter stand for the selection any more."""
        if self._chosen_input or self._unit_chosen:
            self._chosen_input, self._unit_chosen = [], False
            self.selectionChanged.emit()

    @Slot(int, int, int)
    def draw(self, unit, mppt, index=-1):
        if self._connection(unit, mppt):
            self.drawRequested.emit(unit, mppt, index)

    @Slot('QVariantMap')
    def propose(self, options):
        if self._search is not None:
            return
        if not self.settled() or not self.session.good_results():
            self.tell(_('Lay the modules first: the strings are proposed on the modules laid.'))
            return
        strategy = options.get('strategy') or self.settings['strategy']
        if strategy not in core.strategy_names():
            self.tell(_('Choose a string strategy.'))
            return
        runs = self.runs()
        keep = None if options.get('replace', True) else runs
        only = set(options['only']) if options.get('only') else None
        if only is not None:
            if keep is not None:
                only -= {m for r in runs for m in r['modules']}
            else:
                keep = [r for r in runs if not only.intersection(r['modules'])]
            if not only:
                self.tell(_('The modules selected are all in a string already: nothing to complete.'))
                return
        elif options.get('unit') and keep is None:
            keep = [r for r in runs if r.get('inverter') != int(options['unit'])]
        hot, _power = self._year()
        self._search = self._job('proposal', strategy=strategy, keep=keep, only=only, t_cell_max_year=hot)
        self.pool.start(self._search)
        self.tell(_('Assigning strings to the available inputs…'))
        self.notify('stateChanged')

    @Slot('QVariantMap')
    def proposeConfigured(self, options):
        for path, value in (('strings.strategy', options.get('strategy')),
                            ('strings.n_series', options.get('n_series')),
                            ('dc_ac_ratio', options.get('dc_ac', 1.1))):
            self.setEnergy(path, value)
        if 'across' in options and bool(options['across']) != self.settings['across']:
            # R433: without optimizers a string goes on over another face only when the designer says so (written
            # only when true: an optional field)
            def put(p, on=bool(options['across'])):
                s = dict(p.energy.get('strings') or {})
                if on:
                    s[core.ACROSS] = True
                else:
                    s.pop(core.ACROSS, None)
                p.energy['strings'] = s
            self.session.edit(_('Change energy settings'), put)
        self.propose(options)

    @Slot(str)
    def sizeInverters(self, maker):
        if self._search is not None or not self.settled():
            self.tell(_('Wait for the current module layout before sizing the inverters.'))
            return
        self.startSizing(maker, None)

    @Slot(str, bool)
    def sizeInvertersFor(self, maker, only_free):
        """The sizing of the window's «Choose automatically»: on the whole plant, or (R522) on the modules in no string
        only, the designer's strings and inverters kept."""
        if not only_free:
            self.sizeInverters(maker)
            return
        if self._makers and maker not in self.preferred_makers():
            self.tell(_('The proposal for the modules in no string searches among the preferred manufacturers '
                        'only: {maker} is not one of them.').format(maker=maker))
            return
        self.startSizingFree(maker, None)

    def startSizingFree(self, maker, candidates):
        if self._search is not None or not self.settled():
            self.tell(_('Wait for the current module layout before sizing the inverters.'))
            return
        if not self.freeModules and not (self.state is not None and self.state.left):
            self.tell(_('Every module laid is in a string already: there are no modules in no string.'))
            return
        self._search = self._job('sizing_free', maker=maker, candidates=copy.deepcopy(candidates), ratio=self.settings['dc_ac'],
                                 keep=self.runs())
        self._search.started = time.monotonic()
        self._clock.start()
        self.pool.start(self._search)
        self.tell(_('Searching inverter and string combinations…'))
        self.notify('stateChanged')

    def startSizing(self, maker, candidates):
        if self._search is not None or not self.settled() or candidates == []:
            self.tell(_('There is no inverter in the catalogue to size.'))
            return
        self._search = self._job('sizing', maker=maker, candidates=copy.deepcopy(candidates), ratio=self.settings['dc_ac'])
        self.pool.start(self._search)
        self.tell(_('Searching inverter and string combinations…'))
        self.notify('stateChanged')

    @Slot()
    def stopSearch(self):
        """R522 «Stop»: the search for the modules in no string ends now and gives the best proposal found."""
        if self._search is not None and self._search.kind == 'sizing_free':
            self._search.enough.set()
            self.tell(_('Search stopped: the best proposal found until then is being given…'))

    @Slot()
    def cancelSearch(self):
        if self._search is not None:
            self._search.interrupt()
            self._search = None
            self._clock.stop()
            self.searchProgressChanged.emit()
            self.tell(_('String search cancelled; the existing strings have been kept.'))
            self.notify('stateChanged')

    @Slot('QVariantMap', result='QVariantMap')
    def checkStorage(self, patch):
        result = check_storage(patch.get('battery') or {}, patch.get('storage_inverter') or {},
                               patch.get('storage_coupling', 'ac'), patch.get('battery_units', 1))
        messages = [*result.messages, *result.sources]
        valid = bool(patch.get('battery'))
        try:
            operating_battery(patch)
        except ValueError as error:
            messages.append(str(error))
            valid = False
        states = dict(compatible=_('Model pairing documented'), incompatible=_('Incompatible configuration'),
                      unknown=_('Compatibility unknown'))
        return dict(valid=valid, status=result.status, text='\n'.join([states[result.status], *messages]))

    @Slot('QVariantMap', result=bool)
    def applyStorage(self, patch):
        result = self.checkStorage(patch)
        self.tell(result['text'])
        if not result['valid']:
            return False
        allowed = {'battery', 'battery_units', 'storage_coupling', 'storage_inverter', 'storage_efficiency_pct'}
        self.session.edit(_('Configure storage'), lambda p: p.economics.update(
            copy.deepcopy({k: v for k, v in patch.items() if k in allowed})))
        return True

    @Slot()
    def removeStorage(self):
        self.session.edit(_('Configure storage'), lambda p: p.economics.update(
            battery={}, storage_coupling='', storage_inverter={}))

    @Slot()
    def undo(self):
        self.session.undo.undo()
        self.notify('stateChanged')

    @Slot()
    def redo(self):
        self.session.undo.redo()
        self.notify('stateChanged')


def create_page(engine, session=None):
    from .controls import install_controls
    install_controls(engine)
    backend = PlantBackend(session, engine)
    engine.rootContext().setContextProperty('plantBackend', backend)
    engine._plant_backend = backend
    from .catalog import create_page as create_catalog
    if not hasattr(engine, '_catalog_backend'):
        engine._catalog_backend = create_catalog(engine, backend.session)
    engine.destroyed.connect(backend.close)
    return backend
