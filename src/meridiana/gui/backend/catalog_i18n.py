"""The catalogue's words that are not in a _() call: the titles of its kinds and the labels of its technical fields.

The texts are English, marked with N_ for the extraction; their translations are in po/it.po with every other one
(R593: no dictionary of translations in the code; tools/compile_po.py --check refuses one).
"""
from meridiana.i18n import N_, _


def kind_titles() -> dict:
    return {"modules": _("PV modules"), "inverters": _("Inverters"), "microinverters": _("Microinverters"),
            "optimizers": _("Optimizers"), "batteries": _("Batteries")}


# the technical fields a record may have beyond the ones the editor names (catalog.labels)
FIELDS = {
    'ac_current_max_a': N_('Maximum AC current (A)'),
    'ac_power_max_va': N_('Maximum AC power (VA)'),
    'ac_voltage_nominal_v': N_('Nominal AC voltage (V)'),
    'afci': N_('AFCI arc detection'),
    'backup_or_eps': N_('EPS backup output'),
    'battery_charge_power_max_w': N_('Maximum battery charge power (W)'),
    'battery_current_max_a': N_('Maximum battery current (A)'),
    'battery_discharge_power_max_w': N_('Maximum battery discharge power (W)'),
    'battery_power_max_w': N_('Maximum battery power (W)'),
    'battery_voltage_range_v': N_('Battery voltage range (V)'),
    'bifaciality_estimated': N_('Estimated bifaciality (%)'),
    'bipv': N_('BIPV integrated'),
    'cells': N_('Cells'),
    'cells_in_series': N_('Cells in series'),
    'certifications': N_('Certifications'),
    'compatible_inverters': N_('Compatible inverters'),
    'coupling': N_('AC/DC coupling'),
    'cycles_warranted': N_('Warranted cycles'),
    'datasheet_revision': N_('Datasheet revision'),
    'dc_architecture': N_('DC architecture'),
    'dc_current_max_a': N_('Maximum DC current (A)'),
    'dc_current_max_per_input_a': N_('Maximum current per DC input (A)'),
    'dc_current_max_per_mppt_a': N_('Maximum current per MPPT (A)'),
    'dc_current_max_per_mppt_by_strings_a': N_('Maximum MPPT current by number of strings (A)'),
    'dc_input_limits_source': N_('Source of the DC input limits'),
    'dc_input_pairs': N_('DC input pairs'),
    'dc_isc_max_per_input_a': N_('Maximum Isc per input (A)'),
    'dc_isc_max_per_mppt_a': N_('Maximum Isc per MPPT (A)'),
    'dc_power_max_per_input_w': N_('Maximum power per DC input (W)'),
    'dc_power_max_w': N_('Maximum DC power (W)'),
    'dc_power_nominal_w': N_('Nominal DC power (W)'),
    'dc_voltage_nominal_v': N_('Nominal DC voltage (V)'),
    'dimensions_mm': N_('Dimensions (mm)'),
    'efficiency_cec_pct': N_('CEC efficiency (%)'),
    'efficiency_euro_pct': N_('European efficiency (%)'),
    'efficiency_max_pct': N_('Maximum efficiency (%)'),
    'efficiency_peak_pct': N_('Peak efficiency (%)'),
    'efficiency_weighted_pct': N_('Weighted efficiency (%)'),
    'efficiency_derived': N_('Derived efficiency'),
    'efficiency_basis': N_('Basis of the efficiency'),
    'end_of_warranty_capacity_pct': N_('Capacity at the end of the warranty (%)'),
    'energy_per_module_kwh': N_('Energy per module (kWh)'),
    'field_sources': N_('Sources of the single values'),
    'fire_rating': N_('Fire rating'),
    'first_year_loss': N_('First year degradation (%)'),
    'yearly_loss': N_('Yearly degradation (%)'),
    'full_power_mppt_min_v': N_('Minimum MPPT voltage at full power (V)'),
    'glass': N_('Glass'),
    'hybrid': N_('Hybrid'),
    'ip_rating': N_('IP rating'),
    'list_date': N_('List date'),
    'list_version': N_('List version'),
    'listed': N_('In the list'),
    'markets': N_('Markets'),
    'max_input_current_a': N_('Maximum input current (A)'),
    'max_input_isc_home_hub_a': N_('Maximum Home Hub input Isc (A)'),
    'max_output_voltage_v': N_('Maximum output voltage (V)'),
    'max_series_fuse_a': N_('Maximum series fuse (A)'),
    'max_system_voltage_v': N_('Maximum system voltage (V)'),
    'modules_max': N_('Modules, up to'),
    'modules_min': N_('Modules, from'),
    'noct': N_('NOCT (°C)'),
    'nominal_voltage_v': N_('Nominal voltage (V)'),
    'operating_temp_c': N_('Operating temperature (°C)'),
    'optimizer_grid': N_('Optimizer grid'),
    'optimizer_unit_model': N_('Optimizer model'),
    'power_after_25_or_30_years_pct': N_('Power after 25 or 30 years (%)'),
    'power_after_years': N_('Power after years'),
    'power_classes_w': N_('Power classes (W)'),
    'rapid_shutdown': N_('Rapid shutdown'),
    'sandia': N_('Sandia parameters'),
    'sdm': N_('Single diode model parameters'),
    'startup_voltage_v': N_('Start-up voltage (V)'),
    'storage_compatibility': N_('Storage compatibility stated'),
    'storage_limit_notes': N_('Notes on the storage limits'),
    'string_voltage_v': N_('String voltage (V)'),
    'strings_per_mppt': N_('Strings per MPPT'),
    'synergy_units': N_('Synergy units'),
    'thickness_mm': N_('Thickness (mm)'),
    'tolerance': N_('Tolerance'),
    'type': N_('Type'),
    'voltage_range_by_phases_v': N_('Voltage range by phases (V)'),
    'warranty_power_years': N_('Power warranty (years)'),
    'warranty_product_years': N_('Product warranty (years)'),
    'voltage_range_v': N_('Voltage range (V)'),
    'max_charge_current_a': N_('Maximum charge current (A)'),
    'max_discharge_current_a': N_('Maximum discharge current (A)'),
    'max_parallel_units': N_('Maximum units in parallel'),
}


def field_label(key, known):
    """The name of a record's field: the editor's, else the table above, else the schema's, else the key itself."""
    if key in known:
        return known[key]
    if key in FIELDS:
        return _(FIELDS[key])
    from meridiana.data.catalog import schema
    for kind in schema.KINDS:
        for field in schema.fields(kind):
            if field.key == key:
                return _(field.label)
    return _('Additional technical field') + ': ' + key
