"""Physical and declared-data fields for the generic calculation profile."""
from dataclasses import dataclass
from meridiana.i18n import _
from meridiana.core.rules import registry


@dataclass(frozen=True)
class GenericGuiProfile:
    id: str = "generic"
    revision: int = 1

    def append_fields(self, section, schema, project, obj, session):
        if section != "site": return
        n, s = project.network, schema
        s.section('network', _('Grid connection (optional)'), 'site.network')
        s.field('network.distributor', _('Distributor'), n.distributor)
        s.field('network.pod', _('Supply identifier'), n.pod)
        s.num('network.voltage_v', _('Supply voltage'), n.voltage_v, 0, 1000000, 'V', 0, 1, special=_('not stated'))
        s.choice('network.phases', _('Phases'), n.phases, [('', _('not stated')), ('1', _('Single phase')), ('3', _('Three phase'))])
        s.num('network.available_kw', _('Available or contracted power'), n.available_kw, 0, 1e9, 'kW', 1, .5, special=_('not stated'))
        s.num('network.requested_kw', _('Power requested for the new plant'), n.requested_kw, 0, 1e9, 'kW', 1, .5, special=_('not stated'))

    def bill_columns(self, project): return registry.get(self.id).calendar().codes

    def bill_row(self, row):
        return {**row, "ALL": row.get("ALL", sum(row.values()))}
    def activity_note(self, fire): return ""

    def append_chart_fields(self, kind, editor):
        {"consumption": self._consumption, "economics": self._economics}[kind](editor.editor, editor.schema)

    def _consumption(self, editor, s):
        from meridiana.core.energy.consumption import Consumption
        policy = registry.get(self.id).consumption()
        c = policy.prepare(Consumption.from_dict(editor.session.project.consumption, profile_id=self.id))
        s.section('pod', _('Supply identifier'))
        s.field('pod', _('Supply identifier'), c.pod)
        s.num('contract_kw', _('Contracted power'), c.contract_kw or 0, 0, 10000, 'kW', 1, .5, special=_('not stated'))
        s.section('consumption', _('Consumption'))
        s.note('profile', _('Uniform declared consumption'))
        if not policy.has_data(c): s.note('missing', _('No consumption data supplied; consumption is zero'))
        s.choice('mode', '', editor.mode, [('annual', _('Yearly total')), ('bands', _('Yearly total')),
                                         ('bills', _('Month by month')), ('measured', _('Measured curve (CSV)'))])
        if editor.mode == 'annual':
            s.num('annual_kwh', _('Yearly consumption'), c.annual_kwh or 0, 0, 1e9, 'kWh', 0, 100)
        elif editor.mode == 'bands':
            s.num('bands_kwh.ALL', _('Total'), c.bands_kwh.get('ALL') or 0, 0, 1e9, 'kWh', 0, 100)
        elif editor.mode == 'measured':
            s.note('measured_count', _('{n} values imported.').format(n=len(c.measured)) if c.measured else _('No curve imported.'))
            s.choice('curve_unit', '', editor.curveUnit, [('kWh', _('energy per interval (kWh)')), ('kW', _('average power (kW)'))])
            s.action('import_consumption', _('Import a CSV…'))

    def _economics(self, editor, s):
        from meridiana.core.energy.economics import Settings
        d = Settings.from_dict(editor.session.project.economics, profile_id=self.id)
        def group(key, label, rows):
            s.section(key, label)
            for name, title, lo, hi, decimals, unit, step in rows:
                s.num(name, title, getattr(d, name), lo, hi, unit, decimals, step)
        group('bought', _('Energy bought (every variable cost, taxes included)'), [('buy_f1', _('Purchase price'), 0, 2, 3, '€/kWh', .01)])
        group('fed', _('Energy fed in'), [('sell', _('Sale price'), 0, 1, 3, '€/kWh', .005)])
        s.num('export_limit_kw', _('Export limit (0: zero export)'), d.export_limit_kw, -1, 100000, 'kW', 1, 1, special=_('no limit'))
        s.section('storage', _('Storage'))
        b = d.battery or {}
        s.note('battery', str(b.get('model', '')) if b else _('No battery.'))
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
            ('degradation', _('Module degradation (-1: datasheet)'), -1, 5, 2, '%/a', .05)])
        s.note('scope', registry.get(self.id).text('scope'))
        s.note('indicative', _('Undeclared prices and costs are zero; enter the bill and offer. Financial duration and discount defaults are program assumptions.'))

    def fire_bands_notice(self, count):
        return registry.get(self.id).text("scope")
