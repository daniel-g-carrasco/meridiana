"""Serializable electrical observations for QML, without recomputing physics."""
import re

from meridiana.energy import plant, optimizers, system
from meridiana.i18n import number, ngettext
from .plant_i18n import _


def checks(plan):
    return [dict(key=c.key, label=c.label, detail=c.detail, level=c.level, source=c.source)
            for c in (plan.checks if plan is not None else [])]


def figures(s):
    p = s.plan
    if p is None or isinstance(p, optimizers.OptimizedPlan):
        return dict(voc='', vmpp='', isc='', bars=[])
    bars = []
    if p.uoc_max and p.v_limit:
        fraction = p.uoc_max / p.v_limit
        bars.append(dict(label='Uoc', text=f'{number(p.uoc_max, 0)} / {number(p.v_limit, 0)} V',
                         low=0., high=min(1., fraction), state='ok' if fraction <= 1 else 'fail'))
    low, high = p.window
    if p.vmp_hot and high:
        good = (not low or p.vmp_hot >= low) and p.vmp_cold <= high
        bars.append(dict(label='Umpp', text=f'{number(p.vmp_hot, 0)}-{number(p.vmp_cold, 0)} V',
                         low=min(1., p.vmp_hot / high), high=min(1., p.vmp_cold / high),
                         state='ok' if good else 'fail'))
    current_check = next((c for c in p.checks if c.key.startswith('isc') and c.detail
                          and not c.key.startswith('isc_')), None)
    current = current_check.detail if current_check else ''
    values = [float(f.replace(',', '.')) for f in re.findall(r'\d+(?:[.,]\d+)?', current)][:2]
    if len(values) == 2 and values[1] > 0:
        bars.append(dict(label='I', text=f'{number(values[0], 1)} / {number(values[1], 1)} A',
                         low=0., high=min(values[0]/values[1], 1.),
                         state={'ok': 'ok', 'info': 'ok', 'warn': 'check', 'fail': 'fail'}.get(current_check.level, 'check')))
    return dict(voc=number(p.uoc_max, 1), vmpp=f'{number(p.vmp_hot, 1)}-{number(p.vmp_cold, 1)}',
                isc=current, bars=bars)


def unit_lines(state, unit):
    """The same three observations as the Widgets card, from the checked plant."""
    spec = unit.spec
    model = f'{spec.manufacturer} {spec.model}'.strip()
    if unit.fixed is not None:
        what = _('{model} · {kw} kW · strings at {v} V, with power optimizers').format(
            model=model, kw=number(spec.pac/1000, 1), v=number(unit.fixed.v_string, 0))
    else:
        what = _('{model} · {kw} kW · {n} MPPT').format(
            model=model, kw=number(spec.pac/1000, 1), n=int(spec.mppt_count or 1))
    runs = [s for s in state.strings if s.inverter == unit.number and s.modules]
    if not runs:
        return [what, _('no strings'), '']
    inputs = len({s.mppt for s in runs})
    modules = sum(len(s.modules) for s in runs)
    power = sum(slot.power_w for (n, _k), slot in state.inputs.items() if n == unit.number)
    line = (ngettext('{n} string', '{n} strings', len(runs)).format(n=len(runs)) + ' ' +
            ngettext('on {n} input', 'on {n} inputs', inputs).format(n=inputs) + ' · ' +
            ngettext('{n} module', '{n} modules', modules).format(n=modules) + ' · ' +
            _('{kwp} kWp').format(kwp=number(power/1000, 1)))
    if spec.pac > 0 and power > 0:
        line += ' · ' + _('DC/AC {r}').format(r=number(power/spec.pac, 2))
    reasons = [f'{plant.input_name(unit, k)}: {slot.why}' for (n, k), slot in sorted(state.inputs.items())
               if n == unit.number and slot.strings and slot.level != 'ok' and slot.why]
    return [what, line, reasons[0] if reasons else '']


def rows_of(s):
    """The checks of a string chosen: state and words (ui/plant_page.string_figures)."""
    levels = {'ok': 'ok', 'info': 'ok', 'warn': 'check', 'fail': 'fail'}
    rows = [dict(level=levels.get(c.level, 'check'), text=f'{c.label}: {c.detail}' if c.detail else c.label)
            for c in (s.plan.checks if s.plan is not None else [])]
    if not rows and s.why:
        rows.append(dict(level='check', text=s.why))
    return rows or [dict(level='', text=_('No check yet: the strings are being laid.'))]


def summary(state):
    """The strings in a line: how many, on how many inputs, the modules left out (ui/plant_page.summary)."""
    used = sum(1 for slot in state.inputs.values() if slot.used) or len({(s.inverter, s.mppt) for s in state.strings})
    parts = [ngettext('{n} string on {m} inputs', '{n} strings on {m} inputs', len(state.strings)).format(
        n=len(state.strings), m=used)]
    if state.left:
        parts.append(ngettext('{n} module in no string', '{n} modules in no string', len(state.left)).format(n=len(state.left)))
    return ' · '.join(parts)


def totals(state):
    """The inverters in a line, at the head of the Inverter section (ui/plant_page.plant_totals)."""
    units = [u for u in state.units if u.entry >= 0 and u.spec.pac > 0]
    if not units:
        return _('No inverter chosen: Meridiana sizes one by itself for the checks.')
    ac = sum(u.spec.pac for u in units)
    parts = [ngettext('{n} inverter', '{n} inverters', len(units)).format(n=len(units)),
             _('{kw} kW AC').format(kw=number(ac / 1000, 1)), _('{kwp} kWp').format(kwp=number(state.p_stc_w / 1000, 1))]
    if ac > 0 and state.p_stc_w > 0:
        parts.append(_('DC/AC {r}').format(r=number(state.p_stc_w / ac, 2)))
    return ' · '.join(parts)


def conditions(state):
    """Which temperatures the strings are checked at (ui/plant_page.PlantInspector.show_plant)."""
    text = (_('Checked at the hottest cell of the typical year, {t} °C, and at {c} °C.').format(
        t=number(state.t_cell_max, 0), c=number(state.t_cell_cold, 0)) if state.year else
        _("Checked at PVsyst's design conditions until the production is computed: {hot} and {warm} °C of cell, "
          'Uoc at {cold} °C.').format(hot=number(state.t_cell_max, 0), warm=number(state.t_cell_cold, 0),
                                      cold=number(state.t_min, 0)))
    if state.optimized:
        only = _("The strings checked by SolarEdge's tables, the modules' Voc at {t} °C.").format(t=number(state.t_min, 0))
        text = only if all(u.optimized for u in state.units) else f'{text} {only}'
    return text


def working_summary(state, unit):
    """What stands beside the inverter shown: its strings and power, the tooltip with the limits."""
    count = sum(1 for s in state.strings if s.inverter == unit.number)
    power = sum(slot.power_w for (n, _k), slot in state.inputs.items() if n == unit.number)
    text = ngettext('{n} string', '{n} strings', count).format(n=count)
    if power:
        text += ' · ' + _('{kwp} kWp').format(kwp=number(power / 1000, 1))
    tip = _('{name}: {kw} kW AC').format(name=unit.name, kw=number(unit.spec.pac / 1000, 1))
    if unit.spec.imax_total is not None:
        tip += '\n' + _('Shared inverter DC current limit: {a} A').format(a=number(unit.spec.imax_total, 1))
    return text, tip


def optimizer_text(unit):
    """The optimizers of an inverter: chosen, proposed by Meridiana, or none that fits."""
    choice = unit.choice
    if choice is None:
        return _("Optimizers: none of SolarEdge's in the catalogue takes this module; choose one")
    text = ngettext('Optimizers: {name}, {n} module each', 'Optimizers: {name}, {n} modules each', choice.per).format(
        name=choice.optimizer.name, n=choice.per)
    if choice.suggested:
        text += ' ' + _('(proposed by Meridiana)')
    if choice.rules is None:
        text += '. ' + choice.why
    return text


def optimized_takes(unit, slot):
    """What an input of an inverter with optimizers takes: the strings' optimizers and power by SolarEdge's table."""
    choice = unit.choice
    if choice is None or choice.rules is None:
        return _('its optimizers are not known')
    rules = choice.rules
    cap = optimizers.connected_limit(rules, max(1, len(slot.strings)) if slot is not None else 1, 0.0)[0]
    text = _('strings of {lo} to {hi} optimizers').format(lo=rules.opt_min, hi=rules.opt_max)
    if cap != float('inf'):
        text += ', ' + _('up to {p} kW each, {c} kW carried').format(p=number(cap / 1000, 2), c=number(rules.p_cont / 1000, 2))
    if slot is not None and slot.allowed:
        text += ', ' + ngettext('{n} input pair', '{n} input pairs', slot.allowed).format(n=slot.allowed)
    return text


def input_words(state, unit, k, slot):
    """The level, tooltips and room of an input's card (ui/plant_page.InputsGrid.show_plant)."""
    mine = list(slot.strings) if slot is not None else []
    words = {'ok': _('correct'), 'warn': _('to be checked'), 'fail': _('out of limit')}
    takes = (optimized_takes(unit, slot) if unit.optimized else
             _('takes {n} strings of {lo} to {hi} modules').format(n=slot.allowed, lo=slot.series[0], hi=slot.series[1])
             if slot is not None and slot.series[1] else _('its window is not known'))
    level = slot.level if slot is not None and mine else 'info'
    reasons = [words.get(level, '') if mine else _('empty'), takes]
    reasons += [slot.why] if slot is not None and slot.why else []
    reasons += [state.strings[i].why for i in mine if state.strings[i].why]
    return dict(level=level, tip='\n'.join(dict.fromkeys(r for r in reasons if r)),
                room=slot is None or not slot.allowed or len(mine) < slot.allowed,
                place=f'{plant.unit_label(unit)} · {plant.input_name(unit, k)}',
                addTip=_('Activate input {k} of inverter {n}: draw a string, or another equal string in parallel, by '
                         'clicking its modules on the plan in order ({takes})').format(k=k, n=unit.number, takes=takes))


def draft_words(state, target, modules, colour):
    """The string being drawn, in the corner of the strip (R181; ui/window._show_draft): what and where, its modules
    against what the input takes, with the state's symbol, and the keys."""
    unit, mppt, index = target
    n = len(modules)
    slot = state.inputs.get((unit, mppt)) if state is not None else None
    lo, hi = slot.series if slot is not None else (0, 0)
    what = (_('string {name} again').format(name=state.strings[index].label)
            if state is not None and 0 <= index < len(state.strings) else _('new string {n}.{k}').format(n=unit, k=mppt))
    count = ngettext('{n} module', '{n} modules', n).format(n=n)
    inverter = state.unit(unit) if state is not None else None
    mark = ''
    if hi and not (inverter and inverter.optimized):
        if n < lo:
            count += ', ' + ngettext('{k} short ({lo} to {hi})', '{k} short ({lo} to {hi})', lo - n).format(k=lo - n, lo=lo, hi=hi)
            mark = 'warning'
        elif n > hi:
            count += ', ' + ngettext('{k} too many ({lo} to {hi})', '{k} too many ({lo} to {hi})', n - hi).format(k=n - hi, lo=lo, hi=hi)
            mark = 'stop'
        else:
            count += ', ' + _('fine ({lo} to {hi})').format(lo=lo, hi=hi)
            mark = 'check'
    elif hi:
        count += ' ' + _('({lo} to {hi})').format(lo=lo, hi=hi)
    model = f'{inverter.spec.manufacturer} {inverter.spec.model}'.strip() if inverter else ''
    where = _('Inverter {n} · {model} · Input {k}').format(n=unit, model=model or _('not chosen'), k=mppt)
    return dict(title=f'{what[:1].upper()}{what[1:]} · {where}', count=count, mark=mark, colour=colour,
                keys=_('Enter or double click: finish\nBackspace: the last one back · Esc: give up'))


def optimizer_line(unit):
    """The optimizers of an inverter in words, for each inverter that has them, chosen or proposed (R428: the same words as
    the Widgets' row)."""
    if not unit.optimized:
        return ''
    ch = unit.choice
    if ch is None:
        return _("Optimizers: none of SolarEdge's in the catalogue takes this module; choose one")
    text = ngettext("Optimizers: {name}, {n} module each", "Optimizers: {name}, {n} modules each", ch.per).format(
        name=ch.optimizer.name, n=ch.per)
    return text + ' ' + _("(proposed by Meridiana)") if ch.suggested else text


def present(state, project):
    units, strings, inputs = [], [], []
    entries = project.energy.get('inverters', [])
    names = plant.state_names()
    for unit in state.units:
        power = sum(slot.power_w for (n, _k), slot in state.inputs.items() if n == unit.number)
        owned = [s for s in state.strings if s.inverter == unit.number]
        record = entries[unit.entry].get('record', {}) if 0 <= unit.entry < len(entries) else {}
        lines = unit_lines(state, unit)
        beside, beside_tip = working_summary(state, unit)
        units.append(dict(number=unit.number, entry=unit.entry, name=unit.name,
                          label=f'{plant.unit_label(unit)} · {unit.name}', card=unit.entry >= 0 and unit.spec.pac > 0,
                          tip='\n'.join(x for x in (unit.name, *lines) if x),
                          accessible=_('Inverter {n}, {name}: {what}; {strings}').format(
                              n=unit.number, name=unit.name, what=lines[0], strings=lines[1]),
                          summary=beside, summaryTip=beside_tip,
                          optimizerText=optimizer_text(unit) if unit.optimized else '',
                          model=f'{unit.spec.manufacturer} {unit.spec.model}'.strip(),
                          power=number(unit.spec.pac / 1000, 1), inputs=unit.inputs,
                          lines=lines,
                          strings=len(owned), modules=sum(len(s.modules) for s in owned),
                          dc=number(power / 1000, 1), ratio=number(power / unit.spec.pac, 2) if unit.spec.pac else '',
                          optimized=unit.optimized, record=record,
                          optimizer=(unit.choice.record if unit.choice is not None else
                                     entries[unit.entry].get('optimizer', {}) if unit.entry >= 0 else {}),
                          optimizerLine=optimizer_line(unit),
                          per=unit.choice.per if unit.choice else 1,
                          checks=[dict(key=c.key, label=c.label, detail=c.detail, level=c.level, source=c.source)
                                  for c in state.checks.get(unit.number, [])]))
    for index, s in enumerate(state.strings):
        unit = state.unit(s.inverter)
        where = f'{plant.unit_label(unit)} {unit.name} · {plant.input_name(unit, s.mppt)}' if unit else _('Without an input')
        power = sum(m[2] for m in s.modules if len(m) > 2 and isinstance(m[2], (int, float)))
        detail = ngettext('{n} module in series', '{n} modules in series', len(s.modules)).format(n=len(s.modules))
        if power:
            detail += ' · ' + _('{kwp} kWp').format(kwp=number(power/1000, 1))
        detail += ' · ' + plant.state_names().get(s.state, '')
        step = s.plan.record.find('vmp') if s.plan and s.plan.record else None
        cell = next((q for q in (step.inputs if step else []) if q.symbol == r'T_{c,max}'), None)
        values = figures(s)
        rows = rows_of(s)
        strings.append(dict(index=index, run=s.run, label=s.label, inverter=s.inverter, mppt=s.mppt,
                            identity=f'{s.label} · {where}', where=where, detail=detail, rows=rows,
                            optimized=bool(unit and unit.choice is not None),
                            tip=f'{s.label}: {plant.voltages(s)}' + (f'\n{s.why}' if s.why else '') + '\n' + names.get(s.state, ''),
                            source=cell.source.label if cell and cell.source else '',
                            modules=len(s.modules), keys=s.keys, lost=s.lost, state=s.state,
                            stateText=plant.state_names().get(s.state, s.state), why=s.why,
                            voltages=plant.voltages(s), checks=checks(s.plan),
                            groups=s.optimizer_group_sizes, **values))
    for unit in state.units:
        for k in range(1, unit.inputs + 1):
            slot = state.inputs.get((unit.number, k))
            inputs.append(dict(unit=unit.number, mppt=k, label=plant.input_name(unit, k),
                               strings=slot.strings if slot else [], allowed=slot.allowed if slot else 0,
                               series=list(slot.series) if slot else [0, 0],
                               why=slot.why if slot else '',
                               **input_words(state, unit, k, slot),
                               power=number(slot.power_w / 1000, 2) if slot else '0',
                               checks=checks(slot.plan) if slot else []))
    ratio, loss = plant.dcac(state)
    return dict(units=units, strings=strings, inputs=inputs, total=totals(state), totalTip=system.describe(project.energy),
                summary=summary(state), conditionsText=conditions(state), left=len(state.left),
                ratio=number(ratio, 2), clipping=number(loss, 1) + ' %' if loss is not None else '', clippingPct=loss,
                notes=list(state.notes), corrections=list(state.corrections),
                conditions=_('Typical year') if state.year else _('Design conditions'),
                temperatures=f'{number(state.t_min, 1)} / {number(state.t_cell_cold, 1)} / {number(state.t_cell_max, 1)} °C')
