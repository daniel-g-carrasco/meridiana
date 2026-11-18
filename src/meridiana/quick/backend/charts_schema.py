"""Result inspectors: the fields and defaults of ui/energy_pages, without Widgets."""
from meridiana.energy import consumption as cons, system
from meridiana.energy.economics import Settings
from meridiana.energy.simulate import Losses, thermal_names
from meridiana.i18n import _, number
from .properties_schema import Schema


def production(editor):
    s, p = Schema(), editor.session.project
    e = p.energy
    losses = Losses.from_dict(e.get('losses'))
    s.section('arrays', _('Arrays (the modules laid, by orientation)'))
    arrays = system.arrays_of(p, editor.session.good_results())
    if not arrays:
        s.note('no_modules', _('No module laid yet.'))
    for i, a in enumerate(arrays):
        s.note(f'array_{i}', a.name + '\n' + _('{n} modules · {kwp} kWp · tilt {tilt}° · azimuth {az}°').format(
            n=a.modules, kwp=number(a.p_stc / 1000, 2), tilt=number(a.tilt, 1), az=number(a.azimuth, 1)))
    s.note('thermal_intro', _("Cooling of the modules' back (thermal model):"))
    seen = set()
    for a in arrays:
        sfid = a.key.split('.')[0]
        if sfid not in seen:
            seen.add(sfid)
            s.choice('thermal.' + sfid, a.name, a.thermal, thermal_names())
    s.section('inverter', _('Inverter'), framed=False)
    # window.py installs LazyReference: the legacy fields are hidden in the real window.
    s.note('inverters', _('Plant: {what}').format(what=system.describe(e)))
    s.action('phase_plant', _('Go to the Plant'))
    s.section('losses', _('Losses'), 'production.losses')
    s.choice('losses.transposition', _('Transposition model'), losses.transposition,
             [('perez', 'Perez 1990'), ('haydavies', 'Hay e Davies'), ('isotropic', _('isotropic'))])
    for key, label, lo, hi, dec, unit in (
        ('albedo', _('Ground reflectance (albedo)'), 0, 1, 2, ''),
        ('soiling', _('Soiling'), 0, 20, 1, '%'), ('quality', _('Module quality'), -5, 5, 1, '%'),
        ('mismatch', _('Mismatch'), 0, 10, 1, '%'), ('dc_wiring', _('DC wiring at STC'), 0, 10, 1, '%'),
        ('ac_wiring', _('AC wiring at nominal power'), 0, 10, 1, '%'),
        ('unavailability', _('Unavailability'), 0, 20, 1, '%'),
        ('iam_b0', _('ASHRAE b0 (reflection)'), 0, .2, 3, ''),
    ):
        s.num('losses.' + key, label, getattr(losses, key), lo, hi, unit, dec, .1 if dec <= 1 else .01)
    s.check('lid_auto', _("LID from the module's datasheet"), losses.lid is None)
    s.num('losses.lid', _('Light-induced degradation'), losses.lid if losses.lid is not None else 1,
          0, 10, '%', 1, .1, enabled=losses.lid is not None)
    s.check('losses.use_horizon', _('Shading of the far horizon'), losses.use_horizon)
    s.check('losses.use_near', _('Shading of the obstacles of the scene'), losses.use_near)
    return s


def consumption(editor):
    s = Schema()
    c = cons.Consumption.from_dict(editor.session.project.consumption)
    g = cons.guess(editor.session.energy.get('context') or cons.Context())
    names = {'domestic': _('Domestic'), 'other_lv': _('Other uses, low voltage'), 'mv': _('Medium voltage')}
    s.section('pod', _('Supply point (POD)'))
    s.field('pod', _('POD code'), c.pod)
    if c.pod and not cons.valid_pod(c.pod):
        s.note('pod_invalid', _('A POD is IT, three digits, E and eight digits: check it on the bill.'))
    s.choice('supply', _('Supply'), c.supply, [('auto', _('Automatic: {name}').format(name=names[g.supply])), *names.items()])
    s.num('contract_kw', _('Contracted power'), c.contract_kw or 0, 0, 10000, 'kW', 1, .5,
          special=_('automatic: {kw} kW').format(kw=number(g.contract_kw, 1)))
    s.section('consumption', _('Consumption'))
    s.choice('profile', _('Typical profile'), c.profile,
             [('auto', _('Automatic: {name}').format(name=cons.profile_names()[g.profile])), *cons.profile_names().items()])
    if c.profile == 'auto' or not c.has_data():
        s.note('guess', _('What is automatic is guessed from the project: {why}. Enter the bills or the '
                         'curve of the POD for a real result.').format(why=g.why))
    s.choice('mode', '', editor.mode, [('annual', _('Yearly total')), ('bands', _('Yearly, by band')),
             ('bills', _('Month by month and band (bills)')), ('measured', _('Measured curve (CSV)'))])
    if editor.mode == 'annual':
        s.num('annual_kwh', _('Yearly consumption'), c.annual_kwh or 0, 0, 1e9, 'kWh', 0, 100,
              special=_('automatic: {kwh} kWh').format(kwh=number(g.annual_kwh, 0, grouping=True)))
    elif editor.mode == 'bands':
        for band in ('F1', 'F2', 'F3'):
            s.num('bands_kwh.' + band, band, (c.bands_kwh or {}).get(band) or 0, 0, 1e9, 'kWh', 0, 100)
    elif editor.mode == 'measured':
        s.note('measured_count', _('{n} values imported.').format(n=len(c.measured)) if c.measured else _('No curve imported.'))
        s.choice('curve_unit', '', editor.curveUnit,
                 [('kWh', _('energy per interval (kWh)')), ('kW', _('average power (kW)'))])
        s.action('import_consumption', _('Import a CSV…'))
    return s


def economics(editor):
    s = Schema()
    d = Settings.from_dict(editor.session.project.economics)

    def group(key, title, rows, enabled=True):
        s.section(key, title)
        for name, label, lo, hi, dec, unit, step in rows:
            s.num(name, label, getattr(d, name), lo, hi, unit, dec, step, enabled=enabled)

    group('bought', _('Energy bought (every variable cost, taxes included)'),
          [(f'buy_{b.lower()}', b, 0, 2, 3, '€/kWh', .01) for b in ('F1', 'F2', 'F3')])
    group('fed', _('Energy fed in'), [('sell', _('Value (dedicated withdrawal)'), 0, 1, 3, '€/kWh', .005)])
    s.num('export_limit_kw', _('Export limit (0: zero export)'), d.export_limit_kw, -1, 100000, 'kW', 1, 1,
          special=_('no limit'))
    s.section('community', _('Renewable energy community'))
    s.check('community', _('The system is in a community (CER)'), d.community)
    for key, label, hi, dec, unit, step in (
        ('shared_pct', _('Share of the energy fed in that is shared'), 100, 0, '%', 5),
        ('pz', _('Zonal price expected'), 1000, 0, '€/MWh', 5),
        ('trase', _('TRASE of the year (ARERA)'), .1, 4, '€/kWh', .0005),
        ('grant_pct', _('Capital grant'), 40, 0, '%', 5),
    ):
        s.num(key, label, getattr(d, key), 0, hi, unit, dec, step, enabled=bool(d.community))
    s.choice('zone', _('Zone for the PV correction'), d.zone,
             [('', _("from the site's address")), ('north', _('North (+10 €/MWh)')),
              ('centre', _('Centre (+4 €/MWh)')), ('other', _('South and islands'))], enabled=bool(d.community))
    s.section('storage', _('Storage'))
    b = d.battery or {}
    s.note('battery', _('{maker} {model}: {kwh} kWh usable').format(maker=b.get('manufacturer', ''),
           model=b.get('model', ''), kwh=number(float(b.get('usable_energy_kwh') or b.get('nominal_energy_kwh') or 0), 1))
           if b else _('No battery.'))
    s.action('battery_catalog', _('Choose a battery from the catalogue…'))
    s.action('remove_battery', _('No battery'))
    s.num('battery_units', _('How many'), d.battery_units or 1, 1, 50, decimals=0, step=1)
    s.num('battery_cost_per_kwh', _('Installed cost per usable kWh'), d.battery_cost_per_kwh, 0, 5000, '€/kWh', 0, 10)
    group('investment', _('Investment and running costs'), [
        ('capex_per_kwp', _('Cost per kWp, turnkey'), 0, 10000, 0, '€/kWp', 50),
        ('capex_total', _('Or the total of the offer'), 0, 1e9, 0, '€', 100),
        ('opex_per_kwp', _('Running costs'), 0, 500, 0, '€/kWp/a', 1),
        ('inverter_year', _('Inverter replaced in year'), 0, 40, 0, '', 1),
        ('inverter_per_kw', _('Its cost'), 0, 2000, 0, '€/kW', 10)])
    group('finance', _('Financial parameters'), [
        ('years', _('Years'), 1, 40, 0, '', 1), ('discount', _('Discount rate'), 0, 20, 1, '%', .5),
        ('escalation', _('Energy price growth'), -10, 20, 1, '%/a', .5),
        ('opex_escalation', _('Running cost growth'), -10, 20, 1, '%/a', .5),
        ('degradation', _('Module degradation (-1: datasheet)'), -1, 5, 2, '%/a', .05),
        ('deduction_pct', _('Tax deduction over 10 years'), 0, 110, 0, '%', 1)])
    s.note('indicative', _('Prices and costs start from indicative values, marked as such in "How it is computed": '
                         'replace them with the bill and the offer.'))
    return s


def build(editor):
    schema = {'production': production, 'consumption': consumption, 'economics': economics}[editor.phase](editor)
    schema.section('compute', '', framed=False)
    schema.action('compute', _('Compute'))
    return schema.sections
