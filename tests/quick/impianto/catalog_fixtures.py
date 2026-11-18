"""Catalogue fixtures and event-loop waits shared by backend and Quick tests."""
import time

import _setup

APP = _setup.qt_or_skip()


def settle(backend):
    deadline = time.monotonic() + 10
    while backend.busy and time.monotonic() < deadline:
        APP.processEvents()
        time.sleep(.002)
    APP.processEvents()
    assert not backend.busy, backend.error


def module(n=0, **values):
    row = dict(id=str(n), manufacturer='Example', model=f'Panel {n}', source='curated',
               pmax=450, vmp=35, imp=12, voc=42, isc=13, length=1.9, width=1.1,
               efficiency_pct=21, cell_family='topcon', bifacial=True, gamma_pmax=-0.3, beta_voc=-0.25, alpha_isc=0.05,
               cells=108, max_system_voltage_v=1500, max_series_fuse_a=25,
               datasheet_url='https://example.org/panel.pdf')
    row.update(values)
    return row


def required_values(kind):
    """Every field the calculations need for a kind, with a value that passes the window's checks."""
    from meridiana.catalog import schema
    values = dict(manufacturer='Maker', model=kind, datasheet_url='https://example.org/sheet.pdf')
    special = dict(voc=42, vmp=35, isc=13, imp=12, pmax=420, gamma_pmax=-0.3, beta_voc=-0.25, alpha_isc=0.05, length=1.9, width=1.1,
                   mppt_voltage_min_v=180, mppt_voltage_max_v=800, dc_voltage_max_v=1000, phases=3, coupling='dc',
                   compatible_inverters='any', mppt_count=2)
    for field in schema.fields(kind):
        if field.required and field.key not in values and schema.visible(field, {}):
            values[field.key] = special.get(field.key, field.low if field.low else 1)
    return values
