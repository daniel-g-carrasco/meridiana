"""The summary of the Plant in the area at the right of its bar (R419, Daniel 05/11/2026: «un gruppo [...] che contenga in
tempo reale quanti moduli ho messo in totale e a quale potenza di picco corrisponde, + dati inverter messi, quale potenza,
quale collegata, quale scollegati, ottimizzatori [...] e ovviamente in stessa area si vedono i dati di quelli selezionati»).

Nothing is computed here that the session or the plant's job has not already: the modules laid are counted from the
layouts in hand, so they follow a layout at once; what is connected comes from the plant, which its job has built off the
main thread. All of it is a count over lists, under a millisecond for a plant and for a selection of thousands of modules
a few milliseconds (tests/quick/impianto/test_plant_summary.py), and the selection is read at most once a turn."""
from collections import Counter
import math

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from meridiana.energy import optimizers, plant as core
from meridiana.i18n import ngettext, number

from .plant_i18n import _


def row(label, value, tone='text', strong=False, mark=''):
    return dict(label=label, value=value, tone=tone, strong=strong, mark=mark)


def amount(modules, watts):
    return f"{number(modules, 0)} · {_('{kwp} kWp').format(kwp=number(watts / 1000, 1))}"


def column_tip(title, rows):
    lines = [title] if title else []
    lines += [f"{r['label']}: {r['value']}" if r['label'] else r['value'] for r in rows]
    return '\n'.join(lines)


def column(key, rows, title=''):
    return dict(key=key, title=title, rows=rows, tip=column_tip(title, rows))


def watts_by_subfield(project):
    """Each sub-field's module power, by id."""
    return {sf.id: project.module_of(sf).power_kw * 1000 for sf in project.subfields}


def laid_now(project, results):
    """The modules laid and their power, from the layouts in hand (as energy/plant.groups_of counts them)."""
    powers = watts_by_subfield(project)
    modules = watts = 0
    for sf in project.subfields:
        result = results.get(sf.id)
        if not sf.filled or result is None or isinstance(result, Exception) or not result.modules:
            continue
        # A module taken out counts at once, before the layout's job brings the new layout.
        count = len(result.modules) - (sum(1 for m in result.modules if m.key in set(sf.removed)) if sf.removed else 0)
        modules += count
        watts += count * powers[sf.id]
    return modules, watts


class Connected:
    """What a built plant connects: the count and power of its strings, the modules in them, once for each plant."""

    def __init__(self, state, project):
        self.powers = watts_by_subfield(project)
        self.keys = set()
        self.modules, self.watts = 0, 0.0
        self.by_string = []
        for s in (state.strings if state is not None else []):
            watts = sum(self.powers.get(m[0], 0.0) for m in s.modules)
            self.keys.update((m[0], m[1]) for m in s.modules)
            self.modules += len(s.modules)
            self.watts += watts
            self.by_string.append(watts)


def optimizers_in(state):
    """How many optimizers and which, on the inverters that have them: none, and it says nothing."""
    units = [u for u in state.units if u.optimized and u.choice is not None]
    if not units:
        return None
    count = 0
    for s in state.strings:
        unit = state.unit(s.inverter)
        if unit is not None and unit.choice is not None:
            count += len(s.optimizer_group_sizes) or math.ceil(len(s.modules) / max(1, unit.choice.per))
    names = list(dict.fromkeys(u.choice.optimizer.name for u in units))
    return f"{number(count, 0)} · {names[0]}" + (f" +{len(names) - 1}" if len(names) > 1 else '')


def totals(project, results, state, connected):
    """The two columns of the totals: the modules; the inverters."""
    laid, watts = laid_now(project, results)
    left = max(0, laid - connected.modules)
    left_watts = max(0.0, watts - connected.watts)
    modules = [row(_('Modules laid'), amount(laid, watts), strong=True),
               row(_('Connected'), amount(connected.modules, connected.watts)),
               row(_('Not connected'), amount(left, left_watts), tone='text' if left else 'muted', mark='warn' if left else ''),
               row(_('Strings'), number(len(state.strings) if state is not None else 0, 0))]
    units = [u for u in state.units if u.entry >= 0 and u.spec.pac > 0] if state is not None else []
    used = sum(1 for slot in state.inputs.values() if slot.strings) if state is not None else 0
    inputs = sum(u.inputs for u in units)
    if units:
        names = list(dict.fromkeys(f'{u.spec.manufacturer} {u.spec.model}'.strip() for u in units))
        which = f'{len(units)} × {names[0]}' if len(names) == 1 else \
            _('{n} inverters, {m} models').format(n=len(units), m=len(names))
        ac = sum(u.spec.pac for u in units)
        power = _('{kw} kW AC').format(kw=number(ac / 1000, 1))
        if ac > 0 and watts > 0:
            power += ' · ' + _('DC/AC {r}').format(r=number(watts / ac, 2))
        inverter = [row(_('Inverters'), which, strong=True), row(_('Power'), power),
                    row(_('Inputs'), _('{used} used, {free} free').format(used=number(used, 0), free=number(max(0, inputs - used), 0)))]
    else:
        inverter = [row(_('Inverters'), _('none chosen'), tone='muted', strong=True)]
    fitted = optimizers_in(state) if state is not None else None
    if fitted:
        inverter.append(row(_('Optimizers'), fitted))
    elif state is not None and units:
        loss = core.dcac(state)[1]
        if loss is not None:
            inverter.append(row(_('Energy cut'), _('{pct} %').format(pct=number(loss, 1))))
    return [column('modules', modules), column('inverters', inverter)]


def of_modules(title, keys, connected):
    """Any set of modules: how many, their power, how many are in a string."""
    by = Counter(k[0] for k in keys)
    watts = sum(n * connected.powers.get(sf, 0.0) for sf, n in by.items())
    inside = [k for k in keys if (k[0], k[1]) in connected.keys]
    in_watts = sum(connected.powers.get(k[0], 0.0) for k in inside)
    return column('selection', [row(_('Modules'), amount(len(keys), watts), strong=True),
                                row(_('Connected'), amount(len(inside), in_watts)),
                                row(_('Not connected'), amount(len(keys) - len(inside), watts - in_watts),
                                    tone='text' if len(inside) < len(keys) else 'muted',
                                    mark='warn' if len(inside) < len(keys) else '')], title)


def selection(plant, plan, session, results, connected):
    """The column of what is selected, the first of: the string being drawn, the modules swept, a string, an input, an
    inverter, a module, a row, a sub-field; None with nothing selected."""
    card = plant.draftCard
    if card:
        rows = [row('', card['count'], strong=True, mark=card.get('mark', ''))]
        rows += [row('', line, tone='muted') for line in card['keys'].splitlines()]
        return column('selection', rows, card['title'])
    swept = plan.editor.swept if plan is not None else []
    if swept:
        return of_modules(_('Modules selected'), swept, connected)
    if plant.selected >= 0 and plant.chosen:
        s = plant.chosen
        watts = connected.by_string[plant.selected] if plant.selected < len(connected.by_string) else 0.0
        rows = [row(_('Modules'), amount(s['modules'], watts), strong=True), row('', s['where'])]
        rows.append(row('', ' · '.join(f"{b['label']} {b['text']}" for b in s['bars'][:2]) or s['stateText']))
        return column('selection', rows, _('String {name}').format(name=s['label']))
    place = plant.chosenInput
    if place:
        found = next((i for i in plant.inputs if [i['unit'], i['mppt']] == list(place)), None)
        if found:
            rows = [row(_('Strings'), f"{number(len(found['strings']), 0)} / {number(found['allowed'], 0)}", strong=True),
                    row(_('Power'), _('{kwp} kWp').format(kwp=found['power'])),
                    row(_('Series'), f"{found['series'][0]}-{found['series'][1]}")]
            return column('selection', rows, found['place'])
    if plant.unitChosen:
        unit = next((u for u in plant.units if u['number'] == plant.working), None)
        if unit:
            rows = [row(_('Modules'), f"{number(unit['modules'], 0)} · {_('{kwp} kWp').format(kwp=unit['dc'])}", strong=True),
                    row(_('Power'), _('{kw} kW AC').format(kw=unit['power']) + (' · ' + _('DC/AC {r}').format(r=unit['ratio']) if unit['ratio'] else '')),
                    row(_('Strings'), number(unit['strings'], 0))]
            return column('selection', rows, unit['label'])
    kind, oid = session.selection
    sfid = oid.partition('/')[0] if kind == 'row' else oid if kind == 'subfield' else ''
    module = session.selected_module
    if module and module[0] and module[1]:
        return of_modules(_('Module {key}').format(key=module[1]), [tuple(module)], connected)
    result = results.get(sfid)
    if sfid and result is not None and not isinstance(result, Exception):
        sf = session.subfield(sfid)
        placed = result.modules
        title = sf.name if sf is not None else ''
        if kind == 'row':
            rid = oid.partition('/')[2]
            placed = [m for m in placed if m.rid == rid]
            title = _('{name}, a row').format(name=title)
        return of_modules(title, [(sfid, m.key) for m in placed], connected)
    return None


def module_words(state):
    """For the plan, from a built plant: what the tooltip says of each module (R425), what it says of a module in no
    string, and how many modules each inverter has on an optimizer (R424)."""
    tips = {}
    fitted = {u.number: u.choice.per for u in state.units if u.optimized and u.choice is not None}
    for s in state.strings:
        head = _('String {name}: inverter {i}, input {m}, {n} modules').format(name=s.label, i=s.inverter, m=s.mppt, n=len(s.modules))
        if s.why:
            head += f'\n{s.why}'
        total = len(s.modules)
        per = fitted.get(s.inverter)
        groups = {}
        if per:
            try:
                parts = optimizers.module_groups(list(range(total)), per, s.optimizer_group_sizes or None)
            except ValueError:
                parts = optimizers.module_groups(list(range(total)), per)
            groups = {at: (n, len(parts)) for n, part in enumerate(parts, 1) for at in part}
        on = set(getattr(s, 'optimized', None) or ())
        partial = getattr(s, 'optimized', None) is not None
        for at, module in enumerate(s.modules):
            line = _('Module {k} of {n}').format(k=at + 1, n=total)
            if at in groups:
                line += ' · ' + _('optimizer {k} of {n}').format(k=groups[at][0], n=groups[at][1])
            elif partial:
                # R456: optimizers on some modules only
                line += ' · ' + (_('with optimizer') if f'{module[0]}/{module[1]}' in on else _('without optimizer'))
            tips[(module[0], module[1])] = f'{line}\n{head}'
    left = len(state.left)
    default = ngettext('{n} module in no string', '{n} modules in no string', left).format(n=left) if left else ''
    return tips, default, fitted


class PlantSummary(QObject):
    """The totals and the selection for the bar. Told by the session, the plant and the plan; a burst of them is read
    once, on the next turn of the loop."""

    totalsChanged = Signal()
    selectionChanged = Signal()

    def __init__(self, plant, session, plan, parent=None):
        super().__init__(parent)
        self.plant, self.session, self.plan = plant, session, plan
        self._totals, self._selection = [], {}
        self._connected = Connected(None, session.project)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(0)
        self._timer.timeout.connect(self.refresh)
        plant.wiringChanged.connect(self._built)
        plant.selectionChanged.connect(self._timer.start)
        plant.appearanceChanged.connect(self._timer.start)
        session.subscribe(self._session)
        if plan is not None:
            plan.overlayChanged.connect(self._timer.start)
        self.refresh()

    totals = Property('QVariantList', lambda self: self._totals, notify=totalsChanged)
    selection = Property('QVariantMap', lambda self: self._selection, notify=selectionChanged)

    def _session(self, topics):
        if 'selection' in topics:
            self.plant.clear_choice()
        self._timer.start()

    @Slot(object)
    def _built(self, state):
        self._connected = Connected(state, self.session.project)
        self._timer.start()

    @Slot()
    def refresh(self):
        results = self.session.good_results()
        totals_now = totals(self.session.project, results, self.plant.state, self._connected)
        if totals_now != self._totals:
            self._totals = totals_now
            self.totalsChanged.emit()
        chosen = selection(self.plant, self.plan, self.session, results, self._connected) or {}
        if chosen != self._selection:
            self._selection = chosen
            self.selectionChanged.emit()

    def close(self):
        self._timer.stop()
        if self._session in self.session.listeners:
            self.session.listeners.remove(self._session)
