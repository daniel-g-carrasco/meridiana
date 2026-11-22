"""Manual comparisons of declared electrical data, without inferred design factors."""
from meridiana.i18n import _, number
from .pedigree import Record, Source, Step, Quantity, computed


def missing_check(profile_id, data):
    from .stringing import Check
    from meridiana.core.rules import registry
    return Check('generic_missing_data', _('Missing declared electrical data'), False,
                 registry.get(profile_id).text('missing_data').format(data=data), 'info')


def declared_optimizer_checks(module, optimizer, checks, profile_id):
    """Keep comparisons whose two operands are declared; unknown limits are not zero limits."""
    from meridiana.core.rules import registry
    if registry.get(profile_id).electrical().voc_fallback is not None:
        return checks
    declared = getattr(module, 'declared_inputs', None)
    def given(key): return declared is None or key in declared
    known = {
        'power': given('pmax') and optimizer.rated_w > 0,
        'voc': given('voc') and given('beta_voc') and optimizer.voc_max > 0,
        'isc': given('isc') and bool(optimizer.isc_max or optimizer.isc_max_hub),
        'imp': given('imp') and bool(optimizer.i_in_max or optimizer.i_out_max),
    }
    kept = [check for check in checks if known.get(check.key.split('_', 1)[-1], True)]
    if not all(known.values()):
        kept.append(missing_check(profile_id, _('module or optimizer declared ratings')))
    return kept


def manual_plan(module, inverter, n_series, strings_per_mppt, t_min, t_cell_max, ki, t_cell_cold, policy, profile):
    from .stringing import StringPlan, Check, vmp_at
    out = StringPlan(n_series, list(strings_per_mppt), record=Record(policy.text('title')),
                     power_w=n_series * sum(strings_per_mppt) * module.pmax)
    missing = []
    declared = getattr(module, 'declared_inputs', None)
    def given(key): return declared is None or key in declared
    def lack(key):
        if key not in missing: missing.append(key)
    def add(key, label, ok, detail):
        out.checks.append(Check(key, label, bool(ok), detail))
    uoc = None
    if t_min is None: lack(_('minimum temperature'))
    if module.beta_voc is None or not given('beta_voc'): lack(_('module voltage temperature coefficient'))
    if not given('voc'): lack(_('module open-circuit voltage'))
    if t_min is not None and module.beta_voc is not None and given('beta_voc') and given('voc'):
        factor = 1 + module.beta_voc / 100 * (t_min - 25)
        uoc = factor * module.voc * n_series
        out.uoc_max = uoc
        out.record.add(Step('uocmax', _('Maximum open-circuit voltage of the string'),
                            r'U_{OC,max}=N_s U_{OC,STC}(1+\beta(T_{min}-25)/100)',
                            _('Computed from the declared module coefficient and minimum temperature.'), [],
                            Quantity('Uoc', _('maximum open-circuit voltage'), uoc, 'V', computed(''), 1), ''))
    limits = []
    for key, label, value in (('inverter_voltage', 'inverter maximum DC voltage', inverter.vdc_max),
                               ('module_voltage', 'module maximum system voltage', module.max_system_voltage)):
        if value is None or value <= 0: lack(_(label))
        else:
            limits.append(float(value))
            if uoc is not None: add(key, _('Declared voltage limit'), uoc <= value, f'{number(uoc, 2)} V / {number(value, 1)} V')
    if limits: out.v_limit = min(limits)
    cold = t_cell_cold if t_cell_cold is not None else t_min
    needed = ('vmp', 'voc', 'imp', 'isc', 'beta_voc', 'alpha_isc', 'gamma_pmax')
    can_mpp = all(given(key) and getattr(module, key) is not None for key in needed)
    if not can_mpp: lack(_('module data for the MPP temperature model'))
    for key, temperature, limit, lower in (('mppt_low', t_cell_max, inverter.vmppt_min, True),
                                            ('mppt_high', cold, inverter.vmppt_max, False)):
        if temperature is None: lack(_('hot cell temperature') if lower else _('cold cell temperature'))
        if not limit: lack(_('minimum MPPT voltage') if lower else _('maximum MPPT voltage'))
        if can_mpp and temperature is not None and limit:
            value = n_series * vmp_at(module, temperature)
            if lower: out.vmp_hot = value
            else: out.vmp_cold = value
            add(key, _('Declared MPPT window'), value >= limit if lower else value <= limit, f'{number(value, 2)} V / {number(limit, 1)} V')
    out.window = (float(inverter.vmppt_min or 0), float(inverter.vmppt_max or 0))
    isc = None
    if ki is None: lack(_('explicit design current factor'))
    if not given('isc'): lack(_('module short-circuit current'))
    if ki is not None and given('isc'):
        isc = ki * module.isc
        source = Source('input', _('given by the designer'))
        out.record.add(Step('iscmax', _('Maximum short-circuit current of a string'), policy.text('isc_formula'),
                            policy.text('isc_explanation'),
                            [Quantity('KI', policy.text('ki_label'), ki, '', source, 2)],
                            Quantity('Isc', _('maximum short-circuit current'), isc, 'A', computed(''), 2), ''))
    for k, count in enumerate(strings_per_mppt):
        if count <= 0: continue
        limit = inverter.current_limit(k, count)
        if limit is None: lack(_('input {n} operating-current limit').format(n=k+1))
        elif not given('imp'): lack(_('module operating current'))
        else: add(f'imp{k}', _('Declared operating-current limit'), count * module.imp <= limit, f'{number(count * module.imp, 2)} A / {number(limit, 2)} A')
        limit = inverter._limit(inverter.iscmax_per_mppt, k)
        if limit is None: lack(_('input {n} short-circuit current limit').format(n=k+1))
        elif isc is not None: add(f'isc{k}', _('Declared short-circuit current limit'), count * isc <= limit, f'{number(count * isc, 2)} A / {number(limit, 2)} A')
        for suffix, limit, current in (('imp', inverter.connector_current_limit(k), module.imp if given('imp') else None),
                                       ('isc', inverter.connector_isc_limit(k), isc)):
            if limit is None: lack(_('input {n} connector {kind} limit').format(n=k+1, kind=suffix))
            elif current is not None: add(f'connector_{suffix}{k}', _('Declared connector limit'), current <= limit, f'{number(current, 2)} A / {number(limit, 2)} A')
    if n_series <= 0 or sum(strings_per_mppt) <= 0:
        add('strings', _('At least one string'), False, _('no string on any input'))
    if missing:
        out.checks.append(Check('generic_missing_data', _('Missing declared electrical data'), False,
                                profile.text('missing_data').format(data=', '.join(missing)), 'info'))
    out.checks.append(Check('generic_scope', policy.text('scope'), False, policy.text('scope'), 'info'))
    return out
